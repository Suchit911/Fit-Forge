"""
Ephemeral In-Memory Form Analysis Session Manager (Phase 9B.4).

Provides:
- Process-local, bounded, ephemeral session manager for real-time form analysis.
- Coordinates:
    1. Session Lifecycle (create, get, touch, update, close, cleanup)
    2. Exercise FSM State (Phase 9B.1 integration)
    3. Bounded Kinematic Observation History (Phase 9B.2 sliding window)
    4. Latest Heuristic Report (Phase 9B.2)
    5. Repetition Scores & Set Summaries (Phase 9B.3)
    6. Multi-tiered TTL / Expiration:
       - FORM_SESSION_TTL_SECONDS (default 900s)
       - FORM_IDLE_TIMEOUT_SECONDS (default 300s)
       - FORM_MAX_SESSION_DURATION_SECONDS (default 3600s)
    7. Concurrency limit (FORM_MAX_CONCURRENT_SESSIONS, default 50)
- Thread-safe store protected by re-entrant locks (RLock).
- Injectable clock mechanism for deterministic, sleep-free testing.
- Strict Security & Architecture Invariants:
    - Zero persistence (no Firestore, no SQLite, no file writes).
    - Zero raw image / video frame caching.
    - Zero user PII stored in session state.
    - Bounded memory on observations, rep history, and metadata.
"""

import math
import time
import uuid
import threading
from collections import deque
from dataclasses import dataclass, field
from typing import Dict, List, Optional, Any, Callable, Deque, Union

from ..core.config import settings
from .exercise_fsm import (
    ExerciseFSM,
    ExerciseFSMConfig,
    FSMState,
    RepOutcome,
    FSMUpdateResult,
    STANDARD_FSM_CONFIGS,
    EXERCISE_ALIASES,
    KinematicObservation,
)
from .form_heuristics import ExerciseFormReport, FormHeuristicResult
from .form_scoring import (
    RepetitionScore,
    SetScoreSummary,
    FormScoringEngine,
    DEFAULT_SCORING_CONFIG,
)


# =============================================================================
# DOMAIN EXCEPTIONS
# =============================================================================

class FormSessionError(Exception):
    """Base exception for form analysis session errors."""
    pass


class SessionLimitExceededError(FormSessionError):
    """Raised when active sessions reach the configured concurrency limit."""
    pass


class SessionNotFoundError(FormSessionError):
    """Raised when a requested session ID does not exist."""
    pass


class InvalidExerciseError(FormSessionError, ValueError):
    """Raised when an unsupported exercise ID is supplied."""
    pass


# =============================================================================
# CONFIGURATION
# =============================================================================

@dataclass(frozen=True)
class SessionManagerConfig:
    """
    Operational limits and timeout parameters for in-memory session management.
    """
    max_concurrent_sessions: int = 50
    session_ttl_seconds: int = 900          # 15 minutes overall TTL
    max_session_duration_seconds: int = 3600 # 60 minutes absolute max duration
    idle_timeout_seconds: int = 300         # 5 minutes idle expiration
    max_observation_window: int = 8         # 8-frame sliding window for heuristics
    max_repetition_history: int = 100       # Max completed rep records preserved
    max_metadata_entries: int = 20          # Max diagnostic metadata items

    def __post_init__(self):
        if self.max_concurrent_sessions <= 0:
            raise ValueError(f"max_concurrent_sessions must be positive, got {self.max_concurrent_sessions}")
        if self.session_ttl_seconds <= 0:
            raise ValueError(f"session_ttl_seconds must be positive, got {self.session_ttl_seconds}")
        if self.max_session_duration_seconds <= 0:
            raise ValueError(f"max_session_duration_seconds must be positive, got {self.max_session_duration_seconds}")
        if self.idle_timeout_seconds <= 0:
            raise ValueError(f"idle_timeout_seconds must be positive, got {self.idle_timeout_seconds}")
        if self.idle_timeout_seconds > self.max_session_duration_seconds:
            raise ValueError(
                f"idle_timeout_seconds ({self.idle_timeout_seconds}) cannot exceed max_session_duration_seconds ({self.max_session_duration_seconds})"
            )
        if self.max_observation_window <= 0:
            raise ValueError(f"max_observation_window must be positive, got {self.max_observation_window}")

    @classmethod
    def from_settings(cls, app_settings=None) -> "SessionManagerConfig":
        """Factory creating configuration from FastAPI application settings."""
        s = app_settings or settings
        return cls(
            max_concurrent_sessions=getattr(s, "FORM_MAX_CONCURRENT_SESSIONS", 50),
            session_ttl_seconds=getattr(s, "FORM_SESSION_TTL_SECONDS", 900),
            max_session_duration_seconds=getattr(s, "FORM_MAX_SESSION_DURATION_SECONDS", 3600),
            idle_timeout_seconds=getattr(s, "FORM_IDLE_TIMEOUT_SECONDS", 300),
        )


# =============================================================================
# IN-MEMORY SESSION MODEL
# =============================================================================

@dataclass
class FormAnalysisSession:
    """
    Process-local ephemeral state for an active user form analysis workout session.
    Guaranteed bounded memory footprint: strictly zero raw image/video storage.
    """
    session_id: str
    exercise_id: str
    canonical_exercise_id: str
    created_at: float
    last_activity_at: float
    expires_at: float
    fsm: ExerciseFSM
    current_fsm_state: FSMState = FSMState.IDLE
    rep_count: int = 0
    recent_observations: Deque[Any] = field(default_factory=deque)
    completed_reps: List[Dict[str, Any]] = field(default_factory=list)
    latest_heuristic_report: Optional[ExerciseFormReport] = None
    latest_rep_score: Optional[RepetitionScore] = None
    completed_rep_scores: List[RepetitionScore] = field(default_factory=list)
    session_score_summary: Optional[SetScoreSummary] = None
    metadata: Dict[str, Any] = field(default_factory=dict)

    def is_expired(self, current_time: float, config: SessionManagerConfig) -> bool:
        """
        Determines whether the session has expired according to any of the 3 timeout rules:
        1. Current time exceeds expires_at boundary
        2. Idle duration exceeds idle_timeout_seconds
        3. Total lifespan exceeds max_session_duration_seconds
        4. Total lifespan exceeds session_ttl_seconds
        """
        if current_time >= self.expires_at:
            return True
        if (current_time - self.last_activity_at) >= config.idle_timeout_seconds:
            return True
        if (current_time - self.created_at) >= config.max_session_duration_seconds:
            return True
        if (current_time - self.created_at) >= config.session_ttl_seconds:
            return True
        return False

    def touch(self, current_time: float, config: SessionManagerConfig) -> None:
        """Updates last_activity_at and extends expires_at within absolute ceiling."""
        self.last_activity_at = current_time
        absolute_limit = self.created_at + config.max_session_duration_seconds
        ttl_limit = self.created_at + config.session_ttl_seconds
        idle_limit = current_time + config.idle_timeout_seconds
        self.expires_at = min(absolute_limit, ttl_limit, idle_limit)

    def to_summary_dict(self) -> Dict[str, Any]:
        """Provides a safe, non-leaking diagnostic summary of session state."""
        return {
            "session_id": self.session_id,
            "exercise_id": self.exercise_id,
            "canonical_exercise_id": self.canonical_exercise_id,
            "created_at": self.created_at,
            "last_activity_at": self.last_activity_at,
            "expires_at": self.expires_at,
            "current_fsm_state": self.current_fsm_state.value if isinstance(self.current_fsm_state, FSMState) else str(self.current_fsm_state),
            "rep_count": self.rep_count,
            "recent_observation_count": len(self.recent_observations),
            "completed_rep_count": len(self.completed_reps),
            "has_latest_heuristic_report": self.latest_heuristic_report is not None,
            "has_latest_rep_score": self.latest_rep_score is not None,
            "set_score": self.session_score_summary.overall_score if self.session_score_summary else None,
        }


# =============================================================================
# EPHEMERAL IN-MEMORY SESSION MANAGER
# =============================================================================

class FormSessionManager:
    """
    Thread-safe in-memory session manager for AI form analysis.
    Manages session lifecycle, enforce resource limits, and coordinates 9B components.
    """

    def __init__(
        self,
        config: Optional[SessionManagerConfig] = None,
        clock: Optional[Callable[[], float]] = None,
    ):
        self.config = config or SessionManagerConfig.from_settings()
        self.clock = clock or time.time
        self._lock = threading.RLock()
        self._sessions: Dict[str, FormAnalysisSession] = {}
        self._scoring_engine = FormScoringEngine()

    # -------------------------------------------------------------------------
    # EXERCISE RESOLUTION
    # -------------------------------------------------------------------------

    @staticmethod
    def resolve_exercise_id(exercise_id: str) -> str:
        """
        Resolves arbitrary exercise string/alias to canonical ID (e.g. 'squat' -> 'ex_squat').
        Raises InvalidExerciseError if unsupported.
        """
        if not exercise_id or not isinstance(exercise_id, str):
            raise InvalidExerciseError(f"Exercise ID must be a non-empty string, got {exercise_id}")
        clean = exercise_id.strip().lower()
        canonical = EXERCISE_ALIASES.get(clean)
        if not canonical or canonical not in STANDARD_FSM_CONFIGS:
            supported = sorted(list(STANDARD_FSM_CONFIGS.keys()))
            raise InvalidExerciseError(
                f"Unsupported exercise '{exercise_id}'. Supported canonical exercises: {supported}"
            )
        return canonical

    # -------------------------------------------------------------------------
    # SESSION LIFECYCLE
    # -------------------------------------------------------------------------

    def create_session(
        self,
        exercise_id: str,
        client_metadata: Optional[Dict[str, Any]] = None,
    ) -> FormAnalysisSession:
        """
        Creates a new in-memory form analysis session.
        
        Validates:
        1. Exercise support.
        2. Proactive expired session cleanup.
        3. Maximum concurrent sessions limit.
        
        Returns:
            Newly created FormAnalysisSession in FSMState.IDLE.
        """
        canonical_id = self.resolve_exercise_id(exercise_id)
        now = self.clock()

        with self._lock:
            # Proactively purge expired sessions before checking capacity
            self._cleanup_expired_locked(now)

            # Check capacity ceiling
            if len(self._sessions) >= self.config.max_concurrent_sessions:
                raise SessionLimitExceededError(
                    f"Maximum concurrent sessions limit ({self.config.max_concurrent_sessions}) reached. "
                    "Please wait for an active session to close or expire."
                )

            session_id = str(uuid.uuid4())
            fsm_config = STANDARD_FSM_CONFIGS[canonical_id]
            fsm = ExerciseFSM(fsm_config)

            # Initial expiration calculation
            expires_at = now + min(
                self.config.session_ttl_seconds,
                self.config.idle_timeout_seconds,
                self.config.max_session_duration_seconds,
            )

            # Bounded metadata copy
            safe_meta: Dict[str, Any] = {}
            if client_metadata and isinstance(client_metadata, dict):
                for k, v in list(client_metadata.items())[:self.config.max_metadata_entries]:
                    # Filter out sensitive keys if any
                    if k.lower() not in ("uid", "email", "password", "token", "firebase_token"):
                        safe_meta[str(k)] = v

            session = FormAnalysisSession(
                session_id=session_id,
                exercise_id=exercise_id,
                canonical_exercise_id=canonical_id,
                created_at=now,
                last_activity_at=now,
                expires_at=expires_at,
                fsm=fsm,
                current_fsm_state=FSMState.IDLE,
                rep_count=0,
                recent_observations=deque(maxlen=self.config.max_observation_window),
                completed_reps=[],
                latest_heuristic_report=None,
                latest_rep_score=None,
                completed_rep_scores=[],
                session_score_summary=None,
                metadata=safe_meta,
            )

            self._sessions[session_id] = session
            return session

    def get_session(
        self,
        session_id: str,
        auto_touch: bool = True,
    ) -> Optional[FormAnalysisSession]:
        """
        Retrieves an active session by ID.
        If expired, automatically purges and returns None.
        If auto_touch is True, extends the session idle expiration.
        """
        now = self.clock()
        with self._lock:
            session = self._sessions.get(session_id)
            if session is None:
                return None

            if session.is_expired(now, self.config):
                del self._sessions[session_id]
                return None

            if auto_touch:
                session.touch(now, self.config)

            return session

    def touch_session(self, session_id: str) -> bool:
        """
        Refreshes session activity timestamp.
        Returns True if session exists and is active; False if not found or expired.
        """
        now = self.clock()
        with self._lock:
            session = self._sessions.get(session_id)
            if session is None:
                return False

            if session.is_expired(now, self.config):
                del self._sessions[session_id]
                return False

            session.touch(now, self.config)
            return True

    def update_session(
        self,
        session_id: str,
        observation: Optional[Any] = None,
        fsm_result: Optional[FSMUpdateResult] = None,
        heuristic_report: Optional[ExerciseFormReport] = None,
        rep_score: Optional[RepetitionScore] = None,
    ) -> Optional[FormAnalysisSession]:
        """
        Updates session state with recent observation, FSM transition, heuristic report, or rep score.
        Refreshes session activity and re-aggregates set summary if a rep score is added.
        """
        now = self.clock()
        with self._lock:
            session = self._sessions.get(session_id)
            if session is None:
                return None

            if session.is_expired(now, self.config):
                del self._sessions[session_id]
                return None

            session.touch(now, self.config)

            # 1. Bounded observation history (Phase 9B.2 sliding window)
            if observation is not None:
                session.recent_observations.append(observation)

            # 2. Exercise FSM state (Phase 9B.1)
            if fsm_result is not None:
                session.current_fsm_state = fsm_result.state
                session.rep_count = fsm_result.rep_count
                if fsm_result.rep_completed:
                    rep_record = {
                        "rep_number": fsm_result.completed_rep_number or fsm_result.rep_count,
                        "outcome": fsm_result.outcome.value if hasattr(fsm_result.outcome, "value") else str(fsm_result.outcome),
                        "rom_degrees": round(fsm_result.rom_degrees, 2) if fsm_result.rom_degrees is not None else None,
                        "duration_ms": round(fsm_result.duration_ms, 1) if fsm_result.duration_ms is not None else None,
                        "timestamp_ms": fsm_result.completion_timestamp_ms,
                    }
                    if len(session.completed_reps) >= self.config.max_repetition_history:
                        session.completed_reps.pop(0)
                    session.completed_reps.append(rep_record)

            # 3. Form Heuristic Report (Phase 9B.2)
            if heuristic_report is not None:
                session.latest_heuristic_report = heuristic_report

            # 4. Repetition Score & Set Aggregation (Phase 9B.3)
            if rep_score is not None:
                session.latest_rep_score = rep_score
                if len(session.completed_rep_scores) >= self.config.max_repetition_history:
                    session.completed_rep_scores.pop(0)
                session.completed_rep_scores.append(rep_score)
                # Re-aggregate set scores deterministically
                session.session_score_summary = self._scoring_engine.aggregate_set(
                    reps=session.completed_rep_scores,
                    exercise_id=session.canonical_exercise_id,
                )

            return session

    def close_session(self, session_id: str) -> bool:
        """
        Explicitly terminates and evicts an active session from in-memory storage.
        Idempotent: returns True if evicted, False if already non-existent.
        """
        with self._lock:
            if session_id in self._sessions:
                del self._sessions[session_id]
                return True
            return False

    def cleanup_expired(self) -> int:
        """
        Purges all expired sessions from memory.
        Safe for concurrent invocation; returns number of purged sessions.
        """
        now = self.clock()
        with self._lock:
            return self._cleanup_expired_locked(now)

    def _cleanup_expired_locked(self, now: float) -> int:
        """Internal helper for cleanup while holding self._lock."""
        expired_ids = [
            sid for sid, s in self._sessions.items()
            if s.is_expired(now, self.config)
        ]
        for sid in expired_ids:
            del self._sessions[sid]
        return len(expired_ids)

    def active_session_count(self) -> int:
        """Returns the number of currently active, non-expired sessions."""
        now = self.clock()
        with self._lock:
            self._cleanup_expired_locked(now)
            return len(self._sessions)

    def list_active_session_ids(self) -> List[str]:
        """Returns list of all active session IDs."""
        now = self.clock()
        with self._lock:
            self._cleanup_expired_locked(now)
            return list(self._sessions.keys())

    def clear_all(self) -> None:
        """Evicts all sessions immediately (used primarily for test isolation)."""
        with self._lock:
            self._sessions.clear()


# Global Singleton Instance for application-wide session management
default_session_manager = FormSessionManager()
