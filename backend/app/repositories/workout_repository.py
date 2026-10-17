import uuid
from datetime import datetime, timezone
from typing import Optional, List, Dict, Any
from google.cloud.firestore_v1.base_query import FieldFilter
from ..core.firebase import get_firestore_db
from ..schemas.workout import (
    WorkoutSchema,
    WorkoutSessionCreate,
    WorkoutSessionUpdate,
    WorkoutSessionComplete,
    WorkoutSessionResponse,
    WorkoutSetSchema,
)
from ..schemas.user import Environment, DifficultyLevel
from ..seeds.seed_data import SEED_WORKOUTS
from ..utils.logger import logger


_SENTINEL = object()


class WorkoutRepository:
    """
    Data access layer for:
    1. Global Workout definitions: workouts/{workout_id}
    2. User-specific Workout Sessions: users/{uid}/workout_sessions/{session_id}
    """

    def __init__(self, db: Any = _SENTINEL):
        self._db = db
        # In-memory store pre-populated with seed workouts
        self._in_memory_workouts: Dict[str, Dict[str, Any]] = {
            w["id"]: dict(w) for w in SEED_WORKOUTS
        }
        # In-memory sessions store keyed by (uid, session_id)
        self._in_memory_sessions: Dict[str, Dict[str, Any]] = {}

    @property
    def db(self) -> Optional[Any]:
        if self._db is not _SENTINEL:
            return self._db
        return get_firestore_db()

    def ensure_seeded(self) -> None:
        """Idempotently seeds reference workouts into Firestore if empty."""
        db = self.db
        if not db:
            return
        try:
            coll = db.collection("workouts")
            docs = list(coll.limit(1).stream())
            if not docs:
                logger.info("Seeding global workouts reference collection in Firestore...")
                batch = db.batch()
                for wkt_data in SEED_WORKOUTS:
                    doc_ref = coll.document(wkt_data["id"])
                    batch.set(doc_ref, wkt_data)
                batch.commit()
                logger.info(f"Successfully seeded {len(SEED_WORKOUTS)} workouts into Firestore.")
        except Exception as e:
            logger.warning(f"Could not seed workouts in Firestore: {e}")

    # =========================================================================
    # WORKOUT DEFINITIONS
    # =========================================================================

    def list_workouts(
        self,
        environment: Optional[Environment] = None,
        difficulty: Optional[DifficultyLevel] = None,
        search: Optional[str] = None,
    ) -> List[WorkoutSchema]:
        """Lists available workouts with optional filtering."""
        db = self.db
        all_data: List[Dict[str, Any]] = []

        if db:
            try:
                coll = db.collection("workouts")
                docs = coll.stream()
                for doc in docs:
                    all_data.append(doc.to_dict())
            except Exception as e:
                logger.error(f"Error fetching workouts from Firestore: {e}")
                all_data = list(self._in_memory_workouts.values())
        else:
            all_data = list(self._in_memory_workouts.values())

        if not all_data:
            all_data = list(self._in_memory_workouts.values())

        filtered = all_data

        if environment:
            env = str(environment).lower()
            filtered = [w for w in filtered if w.get("targetEnvironment", "").lower() == env]

        if difficulty:
            diff = str(difficulty).lower()
            filtered = [w for w in filtered if w.get("difficulty", "").lower() == diff]

        if search:
            q = search.lower().strip()
            filtered = [
                w for w in filtered
                if q in w.get("title", "").lower()
                or q in w.get("description", "").lower()
            ]

        return [WorkoutSchema(**w) for w in filtered]

    def get_by_id(self, workout_id: str) -> Optional[WorkoutSchema]:
        """Retrieves a single workout definition by ID."""
        db = self.db
        if db:
            try:
                doc = db.collection("workouts").document(workout_id).get()
                if doc.exists:
                    return WorkoutSchema(**doc.to_dict())
            except Exception as e:
                logger.error(f"Error fetching workout {workout_id} from Firestore: {e}")

        item = self._in_memory_workouts.get(workout_id)
        if item:
            return WorkoutSchema(**item)
        return None

    def get_today_workout(self, user_id: str) -> WorkoutSchema:
        """Returns the featured workout for today (defaults to first available workout)."""
        workouts = self.list_workouts()
        if workouts:
            return workouts[0]
        return WorkoutSchema(**SEED_WORKOUTS[0])

    # =========================================================================
    # USER WORKOUT SESSIONS (users/{uid}/workout_sessions/{session_id})
    # =========================================================================

    def create_session(self, uid: str, session_in: WorkoutSessionCreate) -> WorkoutSessionResponse:
        """Starts a new workout session for the authenticated user."""
        workout = self.get_by_id(session_in.workoutId) if session_in.workoutId and session_in.workoutId != "generated" else None
        workout_title = session_in.workoutTitle or (workout.title if workout else "Generated Workout")
        total_sets = session_in.totalSetsCount if session_in.totalSetsCount is not None else (sum(len(ex.sets) for ex in workout.exercises) if workout else 0)

        session_id = f"sess_{datetime.now(timezone.utc).strftime('%Y%m%d%H%M%S')}_{uuid.uuid4().hex[:6]}"
        now_iso = datetime.now(timezone.utc).isoformat()

        session_data: Dict[str, Any] = {
            "id": session_id,
            "userId": uid,
            "workoutId": session_in.workoutId,
            "workoutTitle": workout_title,
            "status": "in_progress",
            "startedAt": now_iso,
            "completedAt": None,
            "durationSeconds": 0,
            "currentExerciseIndex": 0,
            "currentSetIndex": 0,
            "isPaused": False,
            "completedSets": {},
            "completedSetsCount": 0,
            "totalSetsCount": total_sets,
            "totalVolumeKg": 0.0,
            "caloriesBurned": 0,
            "notes": session_in.notes,
            "programId": session_in.programId,
            "planId": session_in.planId,
            "weekNumber": session_in.weekNumber,
            "dayNumber": session_in.dayNumber,
        }

        db = self.db
        if db:
            try:
                doc_ref = db.collection("users").document(uid).collection("workout_sessions").document(session_id)
                doc_ref.set(session_data)
                logger.info(f"Created workout session at users/{uid}/workout_sessions/{session_id}")
            except Exception as e:
                logger.error(f"Error creating session in Firestore: {e}")

        self._in_memory_sessions[f"{uid}:{session_id}"] = session_data
        return WorkoutSessionResponse(**session_data)

    def get_session(self, uid: str, session_id: str) -> Optional[WorkoutSessionResponse]:
        """Retrieves a single session belonging to the authenticated user."""
        db = self.db
        if db:
            try:
                doc = db.collection("users").document(uid).collection("workout_sessions").document(session_id).get()
                if doc.exists:
                    data = doc.to_dict()
                    # Enforce strict user ownership
                    if data.get("userId") == uid:
                        return WorkoutSessionResponse(**data)
            except Exception as e:
                logger.error(f"Error fetching session from Firestore: {e}")

        item = self._in_memory_sessions.get(f"{uid}:{session_id}")
        if item and item.get("userId") == uid:
            return WorkoutSessionResponse(**item)
        return None

    def get_active_session(self, uid: str) -> Optional[WorkoutSessionResponse]:
        """Retrieves the most recent 'in_progress' session for the authenticated user."""
        db = self.db
        if db:
            try:
                coll = db.collection("users").document(uid).collection("workout_sessions")
                docs = list(coll.where(filter=FieldFilter("status", "==", "in_progress")).stream())
                if docs:
                    docs.sort(key=lambda d: d.to_dict().get("startedAt", ""), reverse=True)
                    return WorkoutSessionResponse(**docs[0].to_dict())
            except Exception as e:
                logger.error(f"Error querying active session from Firestore: {e}")

        # Check in-memory store
        active = [
            sess for key, sess in self._in_memory_sessions.items()
            if key.startswith(f"{uid}:") and sess.get("status") == "in_progress"
        ]
        if active:
            active.sort(key=lambda s: s.get("startedAt", ""), reverse=True)
            return WorkoutSessionResponse(**active[0])
        return None

    def update_session(self, uid: str, session_id: str, updates: WorkoutSessionUpdate) -> Optional[WorkoutSessionResponse]:
        """Updates workout progress or records a completed set."""
        session = self.get_session(uid, session_id)
        if not session:
            return None

        current = session.model_dump()

        if updates.currentExerciseIndex is not None:
            current["currentExerciseIndex"] = updates.currentExerciseIndex
        if updates.currentSetIndex is not None:
            current["currentSetIndex"] = updates.currentSetIndex
        if updates.elapsedSeconds is not None:
            current["durationSeconds"] = updates.elapsedSeconds
        if updates.isPaused is not None:
            current["isPaused"] = updates.isPaused
        if updates.notes is not None:
            current["notes"] = updates.notes

        # Handle recording a new set
        if updates.recordedSet:
            rec = updates.recordedSet
            ex_id = rec.exerciseId
            completed_sets = current.setdefault("completedSets", {})
            set_list = completed_sets.setdefault(ex_id, [])

            new_set = {
                "setNumber": rec.setNumber,
                "targetReps": rec.actualReps,
                "targetWeightKg": rec.actualWeightKg,
                "isCompleted": True,
                "actualReps": rec.actualReps,
                "actualWeightKg": rec.actualWeightKg,
                "rpe": rec.rpe,
            }
            set_list.append(new_set)

            # Recalculate metrics
            total_sets = sum(len(sl) for sl in completed_sets.values())
            current["completedSetsCount"] = total_sets

            vol = 0.0
            for sl in completed_sets.values():
                for s in sl:
                    reps = s.get("actualReps") or s.get("targetReps") or 0
                    wt = s.get("actualWeightKg") or s.get("targetWeightKg") or 0.0
                    vol += reps * wt
            current["totalVolumeKg"] = round(vol, 1)

        db = self.db
        if db:
            try:
                doc_ref = db.collection("users").document(uid).collection("workout_sessions").document(session_id)
                doc_ref.set(current, merge=True)
            except Exception as e:
                logger.error(f"Error updating session in Firestore: {e}")

        self._in_memory_sessions[f"{uid}:{session_id}"] = current
        return WorkoutSessionResponse(**current)

    def complete_session(self, uid: str, session_id: str, complete_data: WorkoutSessionComplete) -> Optional[WorkoutSessionResponse]:
        """Marks a session as completed and logs final metrics."""
        session = self.get_session(uid, session_id)
        if not session:
            return None

        current = session.model_dump()
        current["status"] = "completed"
        current["completedAt"] = datetime.now(timezone.utc).isoformat()

        if complete_data.durationSeconds:
            current["durationSeconds"] = complete_data.durationSeconds

        if complete_data.notes:
            current["notes"] = complete_data.notes

        # Estimate calories burned (approx 7.5 kcal/min for strength training)
        dur_mins = current.get("durationSeconds", 0) / 60.0
        current["caloriesBurned"] = round(dur_mins * 7.5)

        db = self.db
        if db:
            try:
                doc_ref = db.collection("users").document(uid).collection("workout_sessions").document(session_id)
                doc_ref.set(current, merge=True)
                logger.info(f"Completed workout session users/{uid}/workout_sessions/{session_id}")
            except Exception as e:
                logger.error(f"Error completing session in Firestore: {e}")

        self._in_memory_sessions[f"{uid}:{session_id}"] = current
        return WorkoutSessionResponse(**current)

    def list_user_history(self, uid: str, limit: int = 20) -> List[WorkoutSessionResponse]:
        """Retrieves completed workout sessions for the authenticated user."""
        db = self.db
        results: List[Dict[str, Any]] = []

        if db:
            try:
                coll = db.collection("users").document(uid).collection("workout_sessions")
                docs = coll.where(filter=FieldFilter("status", "==", "completed")).stream()
                for doc in docs:
                    results.append(doc.to_dict())
                results.sort(key=lambda s: s.get("completedAt") or s.get("startedAt") or "", reverse=True)
                results = results[:limit]
            except Exception as e:
                logger.error(f"Error listing session history from Firestore: {e}")

        if not results:
            # Check in-memory store
            for key, sess in self._in_memory_sessions.items():
                if key.startswith(f"{uid}:") and sess.get("status") == "completed":
                    results.append(sess)
            results.sort(key=lambda s: s.get("startedAt", ""), reverse=True)
            results = results[:limit]

        return [WorkoutSessionResponse(**r) for r in results]


# Global instance
_workout_repo_instance: Optional[WorkoutRepository] = None


def get_workout_repository() -> WorkoutRepository:
    """FastAPI dependency provider for WorkoutRepository."""
    global _workout_repo_instance
    if _workout_repo_instance is None:
        _workout_repo_instance = WorkoutRepository()
        _workout_repo_instance.ensure_seeded()
    return _workout_repo_instance
