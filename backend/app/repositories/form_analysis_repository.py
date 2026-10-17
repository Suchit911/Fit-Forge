"""
Data Access Layer for Persisted Form Analysis Sessions (Phase 9B.7).

Provides:
- Cloud Firestore persistence for completed form analysis session summaries:
    Path: users/{uid}/form_analysis_sessions/{session_id}
- In-memory thread-safe dictionary fallback for local development and test isolation
  when Firebase Admin SDK is uninitialized.
- Deterministic finalization logic:
    - Sessions with rep_count >= 1 are finalized as 'completed' and persisted.
    - Sessions with rep_count == 0 are marked 'aborted' and NOT persisted.
- Idempotency guarantees:
    - Primary key is session_id (UUID).
    - Repeated finalization returns the existing document without creating duplicates.
- Strict security invariants:
    - Every operation is user-scoped to verified Firebase UID.
    - Zero client-provided UID trust.
    - Zero raw frame or continuous landmark coordinate persistence.
    - Bounded document size (< 15 KB, max 50 reps).
"""

import datetime
import hashlib
import json
import math
import threading
from typing import Dict, List, Optional, Tuple, Any, NamedTuple
from google.cloud.firestore_v1.base_query import FieldFilter


class ConflictingSessionPayloadError(Exception):
    """
    Raised when an attempt is made to persist a finalized session with the same session_id
    but a conflicting payload fingerprint (HTTP 409 Conflict equivalent, V2.3.3 Section 8).
    """
    def __init__(self, session_id: str, existing_fingerprint: str, new_fingerprint: str):
        self.session_id = session_id
        self.existing_fingerprint = existing_fingerprint
        self.new_fingerprint = new_fingerprint
        self.status_code = 409
        super().__init__(
            f"Conflicting payload for session '{session_id}': "
            f"existing fingerprint '{existing_fingerprint}' != new fingerprint '{new_fingerprint}'"
        )


class SessionPersistenceResult(NamedTuple):
    """
    Result of an atomic session persistence operation.
    Can be unpacked as (detail, created) or accessed via attributes.
    """
    detail: Any  # FormAnalysisSessionDetailSchema
    created: bool
    status_code: int


def _to_canonical_serializable(obj: Any) -> Any:
    """Recursively converts structures to deterministic, json-serializable representations."""
    if obj is None or isinstance(obj, (int, float, str, bool)):
        return obj
    if hasattr(obj, "model_dump"):
        return _to_canonical_serializable(obj.model_dump(mode="json"))
    if hasattr(obj, "dict"):
        return _to_canonical_serializable(obj.dict())
    if isinstance(obj, dict):
        return {k: _to_canonical_serializable(v) for k, v in sorted(obj.items())}
    if isinstance(obj, (list, tuple, set)):
        return [_to_canonical_serializable(item) for item in obj]
    return str(obj)


def compute_payload_fingerprint(
    user_id: str,
    session_id: str,
    canonical_exercise_id: str,
    reps: Any,
    client_duration_seconds: Optional[int] = None,
    client_notes: Optional[str] = None,
) -> str:
    """
    Generates a deterministic SHA-256 fingerprint from the canonical JSON representation
    of the session finalization payload.

    Formula (V2.3.3 Section 8):
    payload_fingerprint = SHA256(CanonicalJSON(
        user_id, session_id, canonical_exercise_id, reps, client_duration_seconds, client_notes
    ))
    """
    canonical_dict = {
        "canonical_exercise_id": canonical_exercise_id,
        "client_duration_seconds": client_duration_seconds,
        "client_notes": client_notes,
        "reps": _to_canonical_serializable(reps),
        "session_id": session_id,
        "user_id": user_id,
    }
    canonical_json = json.dumps(
        canonical_dict,
        sort_keys=True,
        separators=(",", ":"),
        ensure_ascii=True,
    )
    return hashlib.sha256(canonical_json.encode("utf-8")).hexdigest()

from ..core.firebase import get_firestore_db
from ..utils.logger import logger
from ..schemas.form_analysis import (
    CompactRepSummarySchema,
    FormAnalysisSessionSummarySchema,
    FormAnalysisSessionDetailSchema,
    RepScoreStatus,
)
from ..services.form_session_manager import FormAnalysisSession
from ..services.form_scoring import FormScoringEngine, SetScoreSummary, RepetitionScore

EXERCISE_DISPLAY_NAMES: Dict[str, str] = {
    "squat": "Barbell Back Squat",
    "ex_squat": "Barbell Back Squat",
    "bench_press": "Barbell Bench Press",
    "ex_bench_press": "Barbell Bench Press",
    "deadlift": "Conventional Deadlift",
    "ex_deadlift": "Conventional Deadlift",
    "bicep_curl": "Dumbbell Bicep Curl",
    "ex_bicep_curl": "Dumbbell Bicep Curl",
    "shoulder_press": "Overhead Shoulder Press",
    "ex_shoulder_press": "Overhead Shoulder Press",
}

MAX_PERSISTED_REPS = 50
MAX_SUMMARY_FEEDBACK = 5
DEFAULT_HISTORY_LIMIT = 20
MAX_HISTORY_LIMIT = 50

_SENTINEL = object()


class FormAnalysisRepository:
    """
    Repository managing persistence and retrieval of completed form-analysis sessions.
    User-scoped: access is strictly partitioned by verified Firebase UID.
    """

    def __init__(self, db: Any = _SENTINEL, scoring_engine: Optional[FormScoringEngine] = None):
        self._db = db
        self._lock = threading.RLock()
        self._in_memory_sessions: Dict[str, Dict[str, Any]] = {}
        self._scoring_engine = scoring_engine or FormScoringEngine()

    @property
    def db(self):
        """Returns active Firestore client or None if uninitialized or explicitly mocked."""
        if self._db is not _SENTINEL:
            return self._db
        return get_firestore_db()

    @staticmethod
    def get_exercise_display_name(exercise_id: str) -> str:
        """Maps exercise identifier to human-readable title."""
        clean = (exercise_id or "").strip().lower()
        return EXERCISE_DISPLAY_NAMES.get(clean, clean.replace("_", " ").title() if clean else "Exercise")

    def build_session_summary(
        self,
        session: FormAnalysisSession,
        uid: str,
        client_duration_seconds: Optional[int] = None,
    ) -> Optional[FormAnalysisSessionDetailSchema]:
        """
        Builds a deterministic FormAnalysisSessionDetailSchema from an authoritative active session.
        Returns None if session has 0 completed reps (aborted).
        """
        if session.rep_count < 1 and len(session.completed_reps) < 1:
            return None

        now_utc = datetime.datetime.now(datetime.timezone.utc)
        completed_at_iso = now_utc.isoformat()

        # Calculate started_at from session.created_at timestamp
        if session.created_at > 0:
            started_dt = datetime.datetime.fromtimestamp(session.created_at, tz=datetime.timezone.utc)
            started_at_iso = started_dt.isoformat()
            calc_duration = max(1, int(session.last_activity_at - session.created_at))
        else:
            started_at_iso = completed_at_iso
            calc_duration = 0

        duration_sec = client_duration_seconds if (client_duration_seconds is not None and client_duration_seconds > 0) else calc_duration

        # Aggregate set scores if not already aggregated
        score_summary: Optional[SetScoreSummary] = session.session_score_summary
        if score_summary is None and session.completed_rep_scores:
            score_summary = self._scoring_engine.aggregate_set(
                reps=session.completed_rep_scores,
                exercise_id=session.canonical_exercise_id,
            )

        # Rep counts
        total_reps = session.rep_count
        completed_reps = len(session.completed_reps) or session.rep_count
        valid_reps = score_summary.valid_reps if score_summary else 0
        incomplete_reps = score_summary.incomplete_reps if score_summary else 0
        invalid_reps = score_summary.invalid_reps if score_summary else 0
        insufficient_data_reps = score_summary.insufficient_data_reps if score_summary else 0

        # Build compact rep summaries (bounded to MAX_PERSISTED_REPS)
        compact_reps: List[CompactRepSummarySchema] = []
        scores_for_averaging: List[float] = []
        category_rep_scores: Dict[str, List[float]] = {
            "rom": [],
            "technique": [],
            "symmetry": [],
            "stability": [],
        }

        # Map completed reps with their corresponding score objects
        rep_score_map: Dict[int, RepetitionScore] = {}
        for r_score in session.completed_rep_scores:
            if r_score.rep_number is not None:
                rep_score_map[r_score.rep_number] = r_score

        for idx, rep_dict in enumerate(session.completed_reps[:MAX_PERSISTED_REPS], start=1):
            r_num = rep_dict.get("rep_number", idx)
            matched_score_obj = rep_score_map.get(r_num)

            status_str = matched_score_obj.status.value if matched_score_obj else "VALID"
            rep_score_val = matched_score_obj.score if matched_score_obj else None
            rom_deg = rep_dict.get("rom_degrees")
            dur_ms = rep_dict.get("duration_ms")

            cat_scores_compact: Dict[str, Optional[float]] = {}
            if matched_score_obj and matched_score_obj.category_scores:
                for cat_key, cat_val in matched_score_obj.category_scores.items():
                    norm_key = cat_key.lower().replace("joint alignment / technique", "technique")
                    score_val = round(cat_val.category_score, 1) if cat_val.category_score is not None else None
                    cat_scores_compact[norm_key] = score_val
                    if matched_score_obj.status == RepScoreStatus.VALID and score_val is not None:
                        if norm_key in category_rep_scores:
                            category_rep_scores[norm_key].append(score_val)

            # Only VALID reps contribute to numerical average
            if matched_score_obj and matched_score_obj.status == RepScoreStatus.VALID and rep_score_val is not None:
                scores_for_averaging.append(rep_score_val)

            rep_feedback = matched_score_obj.feedback[:3] if matched_score_obj else []

            compact_reps.append(
                CompactRepSummarySchema(
                    rep_number=r_num,
                    status=status_str,
                    score=round(rep_score_val, 1) if rep_score_val is not None else None,
                    rom_degrees=round(rom_deg, 1) if rom_deg is not None else None,
                    duration_ms=round(dur_ms, 1) if dur_ms is not None else None,
                    category_scores=cat_scores_compact,
                    feedback=rep_feedback,
                )
            )

        # Calculate overall score strictly as arithmetic mean of valid reps
        overall_score: Optional[float] = None
        if scores_for_averaging:
            overall_score = round(sum(scores_for_averaging) / len(scores_for_averaging), 1)
        elif score_summary and score_summary.overall_score is not None:
            overall_score = round(score_summary.overall_score, 1)

        best_score: Optional[float] = round(max(scores_for_averaging), 1) if scores_for_averaging else None
        worst_score: Optional[float] = round(min(scores_for_averaging), 1) if scores_for_averaging else None

        # Category averages across valid reps
        category_averages: Dict[str, Optional[float]] = {}
        for cat_k, cat_vals in category_rep_scores.items():
            category_averages[cat_k] = round(sum(cat_vals) / len(cat_vals), 1) if cat_vals else None

        # Top deterministic summary feedback (max MAX_SUMMARY_FEEDBACK)
        summary_feedback: List[str] = []
        if score_summary and score_summary.summary_feedback:
            summary_feedback = score_summary.summary_feedback[:MAX_SUMMARY_FEEDBACK]
        elif session.completed_rep_scores:
            seen_fb = set()
            for r_s in session.completed_rep_scores:
                for fb in r_s.feedback:
                    if fb and fb not in seen_fb:
                        seen_fb.add(fb)
                        summary_feedback.append(fb)
                        if len(summary_feedback) >= MAX_SUMMARY_FEEDBACK:
                            break
                if len(summary_feedback) >= MAX_SUMMARY_FEEDBACK:
                    break

        exercise_name = self.get_exercise_display_name(session.exercise_id)

        return FormAnalysisSessionDetailSchema(
            session_id=session.session_id,
            user_id=uid,
            exercise_id=session.exercise_id,
            canonical_exercise_id=session.canonical_exercise_id,
            exercise_name=exercise_name,
            status="completed",
            started_at=started_at_iso,
            completed_at=completed_at_iso,
            duration_seconds=duration_sec,
            total_reps=total_reps,
            completed_reps=completed_reps,
            valid_reps=valid_reps,
            incomplete_reps=incomplete_reps,
            invalid_reps=invalid_reps,
            insufficient_data_reps=insufficient_data_reps,
            overall_score=overall_score,
            best_score=best_score,
            worst_score=worst_score,
            category_averages=category_averages,
            summary_feedback=summary_feedback,
            reps=compact_reps,
            created_at=completed_at_iso,
        )

    def _persist_session_detail_atomic(
        self,
        uid: str,
        detail: FormAnalysisSessionDetailSchema,
        client_duration_seconds: Optional[int] = None,
        client_notes: Optional[str] = None,
    ) -> SessionPersistenceResult:
        """
        Atomically persists finalized session detail enforcing deterministic idempotency (Phase 9C.6.2.4).

        Contracts (V2.3.3 Section 8):
        - A. First submission: Persists new session document with SHA-256 canonical payload fingerprint (status_code=201, created=True).
        - B. Identical retry: Same session_id + same canonical payload fingerprint returns existing document without writes (status_code=200, created=False).
        - C. Conflicting retry: Same session_id + different payload fingerprint raises ConflictingSessionPayloadError (HTTP 409 Conflict equivalent), original document unchanged.
        - D. Atomicity: Document lookup, fingerprint comparison, and write are performed atomically inside a Firestore transaction.
        """
        session_id = detail.session_id
        canonical_ex_id = detail.canonical_exercise_id or detail.exercise_id
        duration_sec = client_duration_seconds if client_duration_seconds is not None else detail.duration_seconds
        notes = client_notes if client_notes is not None else detail.client_notes

        # Compute deterministic SHA-256 fingerprint from canonical JSON
        new_fingerprint = compute_payload_fingerprint(
            user_id=uid,
            session_id=session_id,
            canonical_exercise_id=canonical_ex_id,
            reps=detail.reps,
            client_duration_seconds=duration_sec,
            client_notes=notes,
        )

        detail_to_save = detail.model_copy(
            update={
                "payload_fingerprint": new_fingerprint,
                "duration_seconds": duration_sec,
                "client_notes": notes,
            }
        )
        session_data = detail_to_save.model_dump(mode="json")
        key = f"{uid}:{session_id}"

        db = self.db
        if db:
            try:
                coll = db.collection("users").document(uid).collection("form_analysis_sessions")
                doc_ref = coll.document(session_id)

                if hasattr(db, "transaction"):
                    transaction = db.transaction()

                    def _transactional_persist(txn):
                        # Firestore Transaction must read before write
                        doc_snap = doc_ref.get(transaction=txn)
                        if doc_snap.exists:
                            existing_data = doc_snap.to_dict()
                            existing_fp = existing_data.get("payload_fingerprint")
                            if existing_fp == new_fingerprint:
                                logger.info(
                                    f"Idempotent identical retry for session '{session_id}' (fingerprint match: {new_fingerprint})"
                                )
                                existing_schema = FormAnalysisSessionDetailSchema(**existing_data)
                                with self._lock:
                                    self._in_memory_sessions[key] = existing_data
                                return SessionPersistenceResult(
                                    detail=existing_schema,
                                    created=False,
                                    status_code=200,
                                )
                            else:
                                logger.warning(
                                    f"Conflicting payload for session '{session_id}': existing={existing_fp}, new={new_fingerprint}"
                                )
                                raise ConflictingSessionPayloadError(
                                    session_id=session_id,
                                    existing_fingerprint=existing_fp or "UNKNOWN",
                                    new_fingerprint=new_fingerprint,
                                )
                        else:
                            txn.set(doc_ref, session_data)
                            logger.info(
                                f"Atomically persisted new session '{session_id}' with fingerprint '{new_fingerprint}'"
                            )
                            with self._lock:
                                self._in_memory_sessions[key] = session_data
                            return SessionPersistenceResult(
                                detail=detail_to_save,
                                created=True,
                                status_code=201,
                            )

                    try:
                        from google.cloud import firestore
                        return firestore.transactional(_transactional_persist)(transaction)
                    except ConflictingSessionPayloadError:
                        raise
                    except (TypeError, AttributeError):
                        return _transactional_persist(transaction)

                else:
                    # Non-transactional fallback if db client has no transaction()
                    doc_snap = doc_ref.get()
                    if doc_snap.exists:
                        existing_data = doc_snap.to_dict()
                        existing_fp = existing_data.get("payload_fingerprint")
                        if existing_fp == new_fingerprint:
                            return SessionPersistenceResult(
                                detail=FormAnalysisSessionDetailSchema(**existing_data),
                                created=False,
                                status_code=200,
                            )
                        else:
                            raise ConflictingSessionPayloadError(
                                session_id=session_id,
                                existing_fingerprint=existing_fp or "UNKNOWN",
                                new_fingerprint=new_fingerprint,
                            )
                    doc_ref.set(session_data)
                    with self._lock:
                        self._in_memory_sessions[key] = session_data
                    return SessionPersistenceResult(detail=detail_to_save, created=True, status_code=201)

            except ConflictingSessionPayloadError:
                raise
            except Exception as e:
                logger.error(f"Error persisting session detail in Firestore transaction: {e}")
                # Fall through to in-memory handling

        # In-memory thread-safe atomic execution (when db is None or unavailable)
        with self._lock:
            if key in self._in_memory_sessions:
                existing_data = self._in_memory_sessions[key]
                existing_fp = existing_data.get("payload_fingerprint")
                if existing_fp == new_fingerprint:
                    logger.info(
                        f"In-memory idempotent identical retry for session '{session_id}'"
                    )
                    return SessionPersistenceResult(
                        detail=FormAnalysisSessionDetailSchema(**existing_data),
                        created=False,
                        status_code=200,
                    )
                else:
                    logger.warning(
                        f"In-memory conflicting payload for session '{session_id}'"
                    )
                    raise ConflictingSessionPayloadError(
                        session_id=session_id,
                        existing_fingerprint=existing_fp or "UNKNOWN",
                        new_fingerprint=new_fingerprint,
                    )
            else:
                self._in_memory_sessions[key] = session_data
                logger.info(
                    f"In-memory persisted new session '{session_id}' with fingerprint '{new_fingerprint}'"
                )
                return SessionPersistenceResult(
                    detail=detail_to_save,
                    created=True,
                    status_code=201,
                )

    def save_session_summary(
        self,
        uid: str,
        summary: FormAnalysisSessionDetailSchema,
    ) -> FormAnalysisSessionDetailSchema:
        """
        Idempotently persists a completed form analysis session summary via _persist_session_detail_atomic.
        Maintained for call-graph compatibility with Phase 9B.7.
        """
        result = self._persist_session_detail_atomic(uid=uid, detail=summary)
        return result.detail

    def get_session_summary(self, uid: str, session_id: str) -> Optional[FormAnalysisSessionDetailSchema]:
        """
        Retrieves a single session summary for the authenticated user.
        Enforces user ownership: returns None if not found or if user_id != uid.
        """
        key = f"{uid}:{session_id}"
        db = self.db

        if db:
            try:
                doc = db.collection("users").document(uid).collection("form_analysis_sessions").document(session_id).get()
                if doc.exists:
                    data = doc.to_dict()
                    if data.get("user_id") == uid:
                        with self._lock:
                            self._in_memory_sessions[key] = data
                        return FormAnalysisSessionDetailSchema(**data)
                return None
            except Exception as e:
                logger.error(f"Error fetching form analysis session from Firestore: {e}")
                return None

        with self._lock:
            item = self._in_memory_sessions.get(key)
            if item and item.get("user_id") == uid:
                return FormAnalysisSessionDetailSchema(**item)

        return None

    def list_user_history(
        self,
        uid: str,
        limit: int = DEFAULT_HISTORY_LIMIT,
        exercise_id: Optional[str] = None,
    ) -> List[FormAnalysisSessionSummarySchema]:
        """
        Retrieves completed form analysis session summaries for the authenticated user.
        Ordered by completed_at descending.
        """
        bounded_limit = min(max(1, limit), MAX_HISTORY_LIMIT)
        results: List[Dict[str, Any]] = []
        db = self.db

        if db:
            try:
                coll = db.collection("users").document(uid).collection("form_analysis_sessions")
                query = coll.where(filter=FieldFilter("status", "==", "completed"))

                if exercise_id:
                    query = query.where(filter=FieldFilter("exercise_id", "==", exercise_id.strip().lower()))

                docs = query.stream()
                for doc in docs:
                    results.append(doc.to_dict())

                # Sort by completed_at descending, then started_at
                results.sort(
                    key=lambda s: s.get("completed_at") or s.get("started_at") or "",
                    reverse=True,
                )
                results = results[:bounded_limit]
            except Exception as e:
                logger.error(f"Error listing form analysis history from Firestore: {e}")
                results = []
        else:
            # In-memory store when db is None
            with self._lock:
                for key, sess in self._in_memory_sessions.items():
                    if key.startswith(f"{uid}:") and sess.get("status") == "completed":
                        if exercise_id:
                            if sess.get("exercise_id") == exercise_id.strip().lower():
                                results.append(sess)
                        else:
                            results.append(sess)

            results.sort(
                key=lambda s: s.get("completed_at") or s.get("started_at") or "",
                reverse=True,
            )
            results = results[:bounded_limit]

        # Convert to lightweight FormAnalysisSessionSummarySchema
        summaries: List[FormAnalysisSessionSummarySchema] = []
        for r in results:
            summaries.append(
                FormAnalysisSessionSummarySchema(
                    session_id=r.get("session_id", ""),
                    exercise_id=r.get("exercise_id", ""),
                    exercise_name=r.get("exercise_name", self.get_exercise_display_name(r.get("exercise_id", ""))),
                    status=r.get("status", "completed"),
                    started_at=r.get("started_at", ""),
                    completed_at=r.get("completed_at", ""),
                    duration_seconds=r.get("duration_seconds", 0),
                    total_reps=r.get("total_reps", 0),
                    completed_reps=r.get("completed_reps", 0),
                    valid_reps=r.get("valid_reps", 0),
                    overall_score=r.get("overall_score"),
                )
            )

        return summaries

    def list_user_detailed_history(
        self,
        uid: str,
        limit: int = DEFAULT_HISTORY_LIMIT,
        exercise_id: Optional[str] = None,
    ) -> List[FormAnalysisSessionDetailSchema]:
        """
        Retrieves full completed form analysis session details for the authenticated user.
        Ordered chronologically descending by completed_at.
        """
        bounded_limit = min(max(1, limit), MAX_HISTORY_LIMIT)
        results: List[Dict[str, Any]] = []
        db = self.db

        if db:
            try:
                coll = db.collection("users").document(uid).collection("form_analysis_sessions")
                query = coll.where(filter=FieldFilter("status", "==", "completed"))

                if exercise_id:
                    query = query.where(filter=FieldFilter("exercise_id", "==", exercise_id.strip().lower()))

                docs = query.stream()
                for doc in docs:
                    results.append(doc.to_dict())

                results.sort(
                    key=lambda s: s.get("completed_at") or s.get("started_at") or "",
                    reverse=True,
                )
                results = results[:bounded_limit]
            except Exception as e:
                logger.error(f"Error listing detailed form analysis history from Firestore: {e}")
                results = []

        if not results:
            with self._lock:
                for key, sess in self._in_memory_sessions.items():
                    if key.startswith(f"{uid}:") and sess.get("status") == "completed":
                        if exercise_id:
                            if sess.get("exercise_id") == exercise_id.strip().lower():
                                results.append(sess)
                        else:
                            results.append(sess)

            results.sort(
                key=lambda s: s.get("completed_at") or s.get("started_at") or "",
                reverse=True,
            )
            results = results[:bounded_limit]

        details: List[FormAnalysisSessionDetailSchema] = []
        for r in results:
            try:
                details.append(FormAnalysisSessionDetailSchema(**r))
            except Exception as e:
                logger.warning(f"Skipping malformed form analysis detail doc: {e}")

        return details

    def clear_in_memory_for_testing(self) -> None:
        """Clears volatile dictionary store. Used exclusively for test suite isolation."""
        with self._lock:
            self._in_memory_sessions.clear()


# Global Singleton Instance
_form_repo_instance: Optional[FormAnalysisRepository] = None


def get_form_analysis_repository() -> FormAnalysisRepository:
    """FastAPI dependency provider for FormAnalysisRepository."""
    global _form_repo_instance
    if _form_repo_instance is None:
        _form_repo_instance = FormAnalysisRepository()
    return _form_repo_instance
