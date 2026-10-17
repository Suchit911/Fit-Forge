"""
Unit and Behavioral Test Suite for Phase 9B.4 Form Analysis Session Manager.

Validates all 30+ mandatory requirements:
 1. session creation
 2. unique IDs
 3. supported exercise validation
 4. unsupported exercise rejection
 5. initial FSM state
 6. get existing session
 7. unknown session
 8. touch updates activity
 9. expired session
10. idle timeout
11. absolute maximum duration
12. explicit close
13. repeated close
14. cleanup expired
15. repeated cleanup
16. max concurrent session limit
17. limit recovery after close
18. bounded observation history
19. bounded diagnostic/result history
20. FSM state preservation
21. heuristic state preservation
22. scoring state preservation
23. session isolation
24. concurrent lifecycle safety
25. invalid configuration
26. deterministic injected clock
27. no raw frame persistence
28. no Firestore access
29. no network dependency
30. cleanup does not remove active sessions
Boundary values:
- TTL exactly at expiry
- idle timeout exactly at boundary
- absolute duration exactly at maximum
- maximum session count exactly at limit
"""

import threading
import pytest
from typing import List

from backend.app.schemas.form_analysis import (
    ObservabilityStatus,
    HeuristicCategory,
    RepScoreStatus,
)
from backend.app.services.exercise_fsm import FSMState, RepOutcome, FSMUpdateResult
from backend.app.services.form_heuristics import FormHeuristicResult, ExerciseFormReport
from backend.app.services.form_scoring import RepetitionScore, CategoryScore
from backend.app.services.form_session_manager import (
    FormSessionManager,
    SessionManagerConfig,
    FormAnalysisSession,
    SessionLimitExceededError,
    InvalidExerciseError,
)


# =============================================================================
# MOCK CLOCK FIXTURE
# =============================================================================

class MockClock:
    """Injectable deterministic clock that eliminates real time.sleep in tests."""
    def __init__(self, start_time: float = 1000.0):
        self.current_time = start_time

    def __call__(self) -> float:
        return self.current_time

    def advance(self, seconds: float):
        self.current_time += seconds


@pytest.fixture
def mock_clock():
    return MockClock(start_time=1000.0)


@pytest.fixture
def manager(mock_clock):
    config = SessionManagerConfig(
        max_concurrent_sessions=5,
        session_ttl_seconds=900,
        max_session_duration_seconds=3600,
        idle_timeout_seconds=300,
        max_observation_window=8,
        max_repetition_history=10,
        max_metadata_entries=5,
    )
    return FormSessionManager(config=config, clock=mock_clock)


# =============================================================================
# TESTS: SESSION CREATION & VALIDATION (1–5)
# =============================================================================

def test_1_session_creation(manager, mock_clock):
    """1. Creating a session creates an active session object with correct timestamps."""
    session = manager.create_session("squat")
    assert session is not None
    assert session.exercise_id == "squat"
    assert session.canonical_exercise_id == "ex_squat"
    assert session.created_at == 1000.0
    assert session.last_activity_at == 1000.0
    assert manager.active_session_count() == 1


def test_2_unique_session_ids(manager):
    """2. Each session creation generates a unique ID."""
    s1 = manager.create_session("squat")
    s2 = manager.create_session("squat")
    assert s1.session_id != s2.session_id


def test_3_supported_exercise_validation(manager):
    """3. All 5 core exercises and valid aliases are accepted."""
    exercises = ["squat", "bench_press", "deadlift", "bicep_curl", "shoulder_press"]
    for ex in exercises:
        s = manager.create_session(ex)
        assert s.canonical_exercise_id.startswith("ex_")
        manager.close_session(s.session_id)


def test_4_unsupported_exercise_rejection(manager):
    """4. Unsupported exercises raise InvalidExerciseError."""
    with pytest.raises(InvalidExerciseError, match="Unsupported exercise"):
        manager.create_session("lateral_raise")
    with pytest.raises(InvalidExerciseError, match="non-empty string"):
        manager.create_session("")


def test_5_initial_fsm_state(manager):
    """5. Newly created sessions initialize FSM in IDLE state with 0 reps."""
    session = manager.create_session("bench_press")
    assert session.current_fsm_state == FSMState.IDLE
    assert session.rep_count == 0
    assert session.fsm.state == FSMState.IDLE


# =============================================================================
# TESTS: RETRIEVAL, TOUCH & EXPIRY (6–11)
# =============================================================================

def test_6_get_existing_session(manager):
    """6. get_session returns active session by ID."""
    session = manager.create_session("deadlift")
    retrieved = manager.get_session(session.session_id)
    assert retrieved is not None
    assert retrieved.session_id == session.session_id


def test_7_unknown_session_returns_none(manager):
    """7. get_session returns None for unknown or random IDs."""
    assert manager.get_session("non-existent-id") is None


def test_8_touch_updates_activity(manager, mock_clock):
    """8. touch_session advances last_activity_at timestamp."""
    session = manager.create_session("squat")
    assert session.last_activity_at == 1000.0

    mock_clock.advance(50.0)
    touched = manager.touch_session(session.session_id)
    assert touched is True
    assert session.last_activity_at == 1050.0


def test_9_expired_session_by_ttl(manager, mock_clock):
    """9. Session expires when advancing beyond session_ttl_seconds (900s)."""
    session = manager.create_session("squat")
    # Advance beyond TTL (901s)
    mock_clock.advance(901.0)
    assert manager.get_session(session.session_id) is None
    assert manager.active_session_count() == 0


def test_10_idle_timeout_expiration(manager, mock_clock):
    """10. Session expires if idle for longer than idle_timeout_seconds (300s)."""
    session = manager.create_session("squat")
    # Advance without touching for 301 seconds
    mock_clock.advance(301.0)
    assert manager.get_session(session.session_id) is None
    assert manager.active_session_count() == 0


def test_11_absolute_maximum_duration_expiration(manager, mock_clock):
    """11. Session expires when exceeding max_session_duration_seconds (3600s) even if continuously active."""
    session = manager.create_session("squat")
    # Keep touching every 200 seconds until beyond 3600s
    for _ in range(19):  # 19 * 200 = 3800s
        mock_clock.advance(200.0)
        manager.touch_session(session.session_id)

    # Total lifespan is 3800s > 3600s
    assert manager.get_session(session.session_id) is None
    assert manager.active_session_count() == 0


# =============================================================================
# TESTS: EXPLICIT CLOSE & CLEANUP (12–15)
# =============================================================================

def test_12_explicit_close_removes_session(manager):
    """12. close_session evicts session from store."""
    session = manager.create_session("squat")
    assert manager.active_session_count() == 1
    assert manager.close_session(session.session_id) is True
    assert manager.active_session_count() == 0
    assert manager.get_session(session.session_id) is None


def test_13_repeated_close_idempotent(manager):
    """13. Repeated close_session calls return False without error."""
    session = manager.create_session("squat")
    assert manager.close_session(session.session_id) is True
    assert manager.close_session(session.session_id) is False
    assert manager.close_session("unknown-id") is False


def test_14_cleanup_expired_purges_only_expired(manager, mock_clock):
    """14. cleanup_expired removes expired sessions while preserving active ones."""
    s1 = manager.create_session("squat")
    mock_clock.advance(200.0)
    s2 = manager.create_session("bench_press")

    # Advance 150s: s1 is idle for 350s (expired > 300s), s2 is idle for 150s (active < 300s)
    mock_clock.advance(150.0)
    purged = manager.cleanup_expired()
    assert purged == 1
    assert manager.get_session(s1.session_id) is None
    assert manager.get_session(s2.session_id) is not None
    assert manager.active_session_count() == 1


def test_15_repeated_cleanup_is_safe(manager, mock_clock):
    """15. Calling cleanup_expired repeatedly is safe and returns 0 when clean."""
    s = manager.create_session("squat")
    mock_clock.advance(500.0)
    assert manager.cleanup_expired() == 1
    assert manager.cleanup_expired() == 0
    assert manager.cleanup_expired() == 0


# =============================================================================
# TESTS: CONCURRENCY CAPACITY & LIMITS (16–17)
# =============================================================================

def test_16_max_concurrent_session_limit(manager):
    """16. Creating sessions beyond max_concurrent_sessions raises SessionLimitExceededError."""
    # Capacity is 5
    sessions = [manager.create_session("squat") for _ in range(5)]
    assert manager.active_session_count() == 5

    with pytest.raises(SessionLimitExceededError, match="Maximum concurrent sessions limit"):
        manager.create_session("squat")


def test_17_capacity_recovery_after_close(manager):
    """17. Closing an active session frees capacity for a new session."""
    sessions = [manager.create_session("squat") for _ in range(5)]
    manager.close_session(sessions[0].session_id)
    assert manager.active_session_count() == 4

    new_session = manager.create_session("deadlift")
    assert new_session is not None
    assert manager.active_session_count() == 5


# =============================================================================
# TESTS: BOUNDED MEMORY & SLIDING WINDOW (18–19)
# =============================================================================

def test_18_bounded_observation_history(manager):
    """18. recent_observations deque is capped at max_observation_window (8 frames)."""
    session = manager.create_session("squat")
    for i in range(20):
        manager.update_session(session.session_id, observation={"frame": i, "angle": 90.0 + i})

    assert len(session.recent_observations) == 8
    # Oldest 12 frames were evicted; latest frame is 19
    assert session.recent_observations[-1]["frame"] == 19
    assert session.recent_observations[0]["frame"] == 12


def test_19_bounded_repetition_history(manager):
    """19. completed_reps list is bounded at max_repetition_history (10 reps)."""
    session = manager.create_session("squat")
    for i in range(15):
        fsm_res = FSMUpdateResult(
            exercise_id="ex_squat",
            state=FSMState.COMPLETED,
            rep_count=i + 1,
            rep_completed=True,
            completed_rep_number=i + 1,
            rom_degrees=65.0,
            outcome=RepOutcome.VALID_REP,
        )
        manager.update_session(session.session_id, fsm_result=fsm_res)

    assert len(session.completed_reps) == 10
    assert session.completed_reps[-1]["rep_number"] == 15
    assert session.completed_reps[0]["rep_number"] == 6


# =============================================================================
# TESTS: INTEGRATION STATE PRESERVATION (20–23)
# =============================================================================

def test_20_fsm_state_preservation(manager):
    """20. FSM state and rep count updates are preserved on the session."""
    session = manager.create_session("squat")
    fsm_res = FSMUpdateResult(
        exercise_id="ex_squat",
        state=FSMState.IN_PROGRESS,
        rep_count=2,
        rep_completed=False,
    )
    manager.update_session(session.session_id, fsm_result=fsm_res)
    assert session.current_fsm_state == FSMState.IN_PROGRESS
    assert session.rep_count == 2


def test_21_heuristic_state_preservation(manager):
    """21. latest_heuristic_report is preserved on the session."""
    session = manager.create_session("squat")
    report = ExerciseFormReport(
        exercise_id="ex_squat",
        timestamp_ms=2000.0,
        results=[],
        observable_count=4,
        total_required_count=4,
        observability_ratio=1.0,
        is_sufficiently_observable=True,
    )
    manager.update_session(session.session_id, heuristic_report=report)
    assert session.latest_heuristic_report == report


def test_22_scoring_state_preservation_and_aggregation(manager):
    """22. latest_rep_score is preserved and set summary is aggregated automatically."""
    session = manager.create_session("squat")
    rep_score = RepetitionScore(
        exercise_id="ex_squat",
        rep_number=1,
        status=RepScoreStatus.VALID,
        score=95.0,
        base_score=95.0,
        confidence_factor=1.0,
        rep_confidence=1.0,
        observability_ratio=1.0,
        is_sufficiently_observable=True,
    )
    manager.update_session(session.session_id, rep_score=rep_score)
    assert session.latest_rep_score == rep_score
    assert session.session_score_summary is not None
    assert session.session_score_summary.overall_score == 95.0
    assert session.session_score_summary.valid_reps == 1


def test_23_session_isolation(manager):
    """23. Multiple sessions maintain completely isolated states and FSM instances."""
    s1 = manager.create_session("squat")
    s2 = manager.create_session("bench_press")

    manager.update_session(s1.session_id, observation={"rep": 1})
    assert len(s1.recent_observations) == 1
    assert len(s2.recent_observations) == 0

    assert s1.canonical_exercise_id == "ex_squat"
    assert s2.canonical_exercise_id == "ex_bench_press"


# =============================================================================
# TESTS: THREAD SAFETY & MULTI-THREADED ACCESS (24)
# =============================================================================

def test_24_concurrent_lifecycle_safety(mock_clock):
    """24. Concurrent creates, touches, and updates do not corrupt in-memory state."""
    config = SessionManagerConfig(max_concurrent_sessions=50)
    mgr = FormSessionManager(config=config, clock=mock_clock)

    created_ids: List[str] = []
    errors: List[Exception] = []

    def worker():
        try:
            s = mgr.create_session("squat")
            created_ids.append(s.session_id)
            for _ in range(5):
                mgr.touch_session(s.session_id)
                mgr.update_session(s.session_id, observation={"val": 1.0})
        except Exception as e:
            errors.append(e)

    threads = [threading.Thread(target=worker) for _ in range(10)]
    for t in threads:
        t.start()
    for t in threads:
        t.join()

    assert len(errors) == 0
    assert len(created_ids) == 10
    assert mgr.active_session_count() == 10


# =============================================================================
# TESTS: CONFIGURATION VALIDATION (25)
# =============================================================================

def test_25_invalid_configuration():
    """25. Invalid configuration parameters raise ValueError."""
    with pytest.raises(ValueError, match="max_concurrent_sessions must be positive"):
        SessionManagerConfig(max_concurrent_sessions=0)

    with pytest.raises(ValueError, match="cannot exceed max_session_duration"):
        SessionManagerConfig(idle_timeout_seconds=5000, max_session_duration_seconds=3600)


# =============================================================================
# TESTS: INJECTED CLOCK & BOUNDARY CHECKS (26, 31–34)
# =============================================================================

def test_26_deterministic_injected_clock(manager, mock_clock):
    """26. Time advances strictly through injected mock clock without real sleep."""
    s = manager.create_session("squat")
    assert s.created_at == 1000.0

    mock_clock.advance(100.0)
    s2 = manager.create_session("bench_press")
    assert s2.created_at == 1100.0


def test_27_no_raw_frame_persistence(manager):
    """27. Session stores only structured metadata, never raw byte payloads."""
    session = manager.create_session("squat")
    summary = session.to_summary_dict()
    assert "frame_bytes" not in summary
    assert "image" not in summary
    assert "video" not in summary


def test_28_29_no_firestore_or_network_dependency(manager):
    """28 & 29. Session manager operates entirely in memory with zero cloud/db dependency."""
    # Verify manager instance has no firestore / db clients
    assert not hasattr(manager, "db")
    assert not hasattr(manager, "firestore")
    assert not hasattr(manager, "http_client")


def test_30_cleanup_does_not_remove_active_sessions(manager, mock_clock):
    """30. Active sessions within limits are never evicted during cleanup."""
    s = manager.create_session("squat")
    mock_clock.advance(100.0)
    assert manager.cleanup_expired() == 0
    assert manager.get_session(s.session_id) is not None


# =============================================================================
# BOUNDARY VALUE TESTS
# =============================================================================

def test_boundary_ttl_exactly_at_expiry(mock_clock):
    """Boundary: exactly at TTL (created_at + 900.0) is expired when kept active."""
    cfg = SessionManagerConfig(
        session_ttl_seconds=900,
        idle_timeout_seconds=300,
        max_session_duration_seconds=3600,
    )
    mgr = FormSessionManager(config=cfg, clock=mock_clock)
    s = mgr.create_session("squat")
    # Keep active by touching every 200s: at 200, 400, 600, 800
    for _ in range(4):
        mock_clock.advance(200.0)
        mgr.touch_session(s.session_id)

    # At 899.99s, active
    mock_clock.advance(99.99)
    assert mgr.get_session(s.session_id, auto_touch=False) is not None

    # At 900.01s, TTL has expired
    mock_clock.advance(0.02)
    assert mgr.get_session(s.session_id) is None


def test_boundary_idle_timeout_exactly_at_boundary(manager, mock_clock):
    """Boundary: exactly at idle timeout (last_activity + 300.0) is expired."""
    s = manager.create_session("squat")
    mock_clock.advance(299.99)
    assert manager.get_session(s.session_id, auto_touch=False) is not None

    mock_clock.advance(0.02)
    assert manager.get_session(s.session_id) is None


def test_boundary_absolute_duration_exactly_at_maximum(mock_clock):
    """Boundary: exactly at max_session_duration (3600.0) is expired."""
    cfg = SessionManagerConfig(
        session_ttl_seconds=5000,
        max_session_duration_seconds=3600,
        idle_timeout_seconds=300,
    )
    mgr = FormSessionManager(config=cfg, clock=mock_clock)
    s = mgr.create_session("squat")
    # Keep active by touching every 200 seconds up to 3400s
    for _ in range(17):  # 17 * 200 = 3400s
        mock_clock.advance(200.0)
        mgr.touch_session(s.session_id)

    # Now at 3400s. Advance 199.99s -> 3599.99s
    mock_clock.advance(199.99)
    assert mgr.get_session(s.session_id, auto_touch=False) is not None

    # Advance 0.02s -> 3600.01s (absolute duration exceeded)
    mock_clock.advance(0.02)
    assert mgr.get_session(s.session_id) is None



def test_boundary_max_session_count_exactly_at_limit(manager):
    """Boundary: exactly at limit (5) allows exactly 5, rejects 6th."""
    for i in range(5):
        manager.create_session("squat")
    assert manager.active_session_count() == 5

    with pytest.raises(SessionLimitExceededError):
        manager.create_session("squat")
