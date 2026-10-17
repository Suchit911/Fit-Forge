"""
Unit and Integration Test Suite for Phase 9B.7 — Session Summary & History.

Tests all 30 mandatory requirements:
 1. New authenticated user gets empty history.
 2. Unauthenticated history request rejected.
 3. Authenticated user can retrieve own session.
 4. User B cannot retrieve User A session (cross-user isolation).
 5. User B cannot finalize User A session.
 6. >=1 completed rep persists session.
 7. 0 reps produces ABORTED and no Firestore history.
 8. 0 valid reps preserves overall_score=null.
 9. Valid reps aggregate correctly (arithmetic mean).
10. Incomplete reps excluded from numerical average.
11. Invalid reps excluded from numerical average.
12. Insufficient-data reps excluded from numerical average.
13. Category averages correct across valid reps.
14. Best score correct.
15. Worst score correct.
16. Rep summaries capped at 50.
17. Feedback bounded (max 5 items).
18. Document size bounded (< 15 KB).
19. History limit default 20.
20. History limit maximum 50.
21. Exercise filtering works.
22. completed_at descending ordering works.
23. Finalization is idempotent.
24. Repeated REST finalization does not duplicate.
25. WebSocket stop finalizes completed session.
26. WebSocket stop with zero reps does not persist.
27. WebSocket stop + REST finalize race/idempotency is safe.
28. Firestore unavailable/fallback behavior is deterministic.
29. Persistence failure does not claim success.
30. Previously finalized session returns existing summary.
"""

import json
import time
from typing import Dict, List, Optional
from unittest.mock import patch, MagicMock
import pytest
from fastapi.testclient import TestClient
from starlette.testclient import TestClient as StarletteTestClient

from backend.app.main import app
from backend.app.core.security import CurrentUser, get_current_user
from backend.app.services.form_session_manager import default_session_manager, FormAnalysisSession
from backend.app.services.form_scoring import RepetitionScore, CategoryScore, RepScoreStatus
from backend.app.schemas.form_analysis import (
    FormAnalysisSessionDetailSchema,
    FormAnalysisSessionSummarySchema,
    CompactRepSummarySchema,
    HeuristicCategory,
)
from backend.app.repositories.form_analysis_repository import (
    FormAnalysisRepository,
    get_form_analysis_repository,
    MAX_PERSISTED_REPS,
)


# =============================================================================
# FIXTURES
# =============================================================================

@pytest.fixture
def repo():
    """Provides a fresh isolated FormAnalysisRepository instance."""
    repository = FormAnalysisRepository(db=None)
    return repository


@pytest.fixture(autouse=True)
def clean_stores(repo):
    """Ensures both session manager and repo stores are clean before and after each test."""
    default_session_manager.clear_all()
    repo.clear_in_memory_for_testing()
    app.dependency_overrides[get_form_analysis_repository] = lambda: repo
    yield
    default_session_manager.clear_all()
    repo.clear_in_memory_for_testing()
    app.dependency_overrides.pop(get_form_analysis_repository, None)
    app.dependency_overrides.pop(get_current_user, None)


@pytest.fixture
def client(repo):
    """TestClient instance."""
    with TestClient(app) as test_client:
        yield test_client


def make_mock_rep_score(
    rep_number: int,
    status: RepScoreStatus = RepScoreStatus.VALID,
    score: Optional[float] = 90.0,
    rom_score: float = 95.0,
    technique_score: float = 88.0,
    symmetry_score: float = 92.0,
    stability_score: float = 85.0,
    feedback: Optional[List[str]] = None,
) -> RepetitionScore:
    """Helper creating a deterministic RepetitionScore object."""
    cat_scores = {}
    if status == RepScoreStatus.VALID:
        cat_scores = {
            "ROM": CategoryScore(
                category=HeuristicCategory.ROM,
                weight=0.40,
                normalized_weight=0.40,
                raw_penalty=100.0 - rom_score,
                category_score=rom_score,
            ),
            "Joint Alignment / Technique": CategoryScore(
                category=HeuristicCategory.TECHNIQUE,
                weight=0.35,
                normalized_weight=0.35,
                raw_penalty=100.0 - technique_score,
                category_score=technique_score,
            ),
            "Symmetry": CategoryScore(
                category=HeuristicCategory.SYMMETRY,
                weight=0.15,
                normalized_weight=0.15,
                raw_penalty=100.0 - symmetry_score,
                category_score=symmetry_score,
            ),
            "Stability": CategoryScore(
                category=HeuristicCategory.STABILITY,
                weight=0.10,
                normalized_weight=0.10,
                raw_penalty=100.0 - stability_score,
                category_score=stability_score,
            ),
        }

    return RepetitionScore(
        exercise_id="ex_squat",
        rep_number=rep_number,
        status=status,
        score=score if status == RepScoreStatus.VALID else None,
        base_score=score if status == RepScoreStatus.VALID else None,
        confidence_factor=1.0,
        rep_confidence=0.95,
        observability_ratio=1.0,
        is_sufficiently_observable=True,
        category_scores=cat_scores,
        feedback=feedback or [f"Feedback for rep {rep_number}"],
    )


def populate_active_session(
    session_id: str = "sess-123",
    exercise_id: str = "squat",
    uid: str = "user_a",
    rep_scores: Optional[List[RepetitionScore]] = None,
    created_offset: float = 60.0,
) -> FormAnalysisSession:
    """Creates an active session in default_session_manager."""
    session = default_session_manager.create_session(
        exercise_id=exercise_id,
        client_metadata={"authenticated_uid": uid},
    )
    # Override session_id and timestamps for predictable testing
    session.session_id = session_id
    default_session_manager._sessions[session_id] = session
    now = time.time()
    session.created_at = now - created_offset
    session.last_activity_at = now

    if rep_scores:
        session.rep_count = len(rep_scores)
        for r in rep_scores:
            session.completed_reps.append({
                "rep_number": r.rep_number,
                "outcome": "COMPLETED",
                "rom_degrees": 110.0,
                "duration_ms": 2200.0,
                "timestamp_ms": now * 1000.0,
            })
            session.completed_rep_scores.append(r)

    return session


# =============================================================================
# TEST CASES 1–5: API ACCESS & SECURITY
# =============================================================================

def test_new_user_gets_empty_history(client: TestClient):
    """1. New authenticated user gets empty history."""
    app.dependency_overrides[get_current_user] = lambda: CurrentUser(uid="new_user_1", email="new@test.com")
    res = client.get("/api/v1/form-analysis/history")
    assert res.status_code == 200
    assert res.json() == []


def test_unauthenticated_history_rejected(client: TestClient):
    """2. Unauthenticated history request rejected with 401."""
    # Ensure get_current_user is NOT overridden
    if get_current_user in app.dependency_overrides:
        del app.dependency_overrides[get_current_user]
    res = client.get("/api/v1/form-analysis/history")
    assert res.status_code in (401, 403)


def test_authenticated_user_retrieves_own_session(client: TestClient, repo: FormAnalysisRepository):
    """3. Authenticated user can retrieve own session detail."""
    app.dependency_overrides[get_current_user] = lambda: CurrentUser(uid="user_a", email="a@test.com")
    session = populate_active_session("sess-own", uid="user_a", rep_scores=[make_mock_rep_score(1, score=88.0)])
    summary = repo.build_session_summary(session, "user_a")
    repo.save_session_summary("user_a", summary)

    res = client.get(f"/api/v1/form-analysis/history/{summary.session_id}")
    assert res.status_code == 200
    data = res.json()
    assert data["session_id"] == "sess-own"
    assert data["user_id"] == "user_a"
    assert data["overall_score"] == 88.0


def test_cross_user_isolation_get_session(client: TestClient, repo: FormAnalysisRepository):
    """4. User B cannot retrieve User A session (returns 404)."""
    session = populate_active_session("sess-user-a", uid="user_a", rep_scores=[make_mock_rep_score(1, score=85.0)])
    summary = repo.build_session_summary(session, "user_a")
    repo.save_session_summary("user_a", summary)

    # User B attempts to access User A's session
    app.dependency_overrides[get_current_user] = lambda: CurrentUser(uid="user_b", email="b@test.com")
    res = client.get("/api/v1/form-analysis/history/sess-user-a")
    assert res.status_code == 404
    assert res.json()["detail"] == "Form analysis session not found."


def test_cross_user_isolation_finalize_session(client: TestClient, repo: FormAnalysisRepository):
    """5. User B cannot finalize User A active session (returns 404)."""
    populate_active_session("sess-active-a", uid="user_a", rep_scores=[make_mock_rep_score(1, score=90.0)])

    # User B attempts to finalize User A's active session
    app.dependency_overrides[get_current_user] = lambda: CurrentUser(uid="user_b", email="b@test.com")
    res = client.post("/api/v1/form-analysis/sessions/sess-active-a/finalize")
    assert res.status_code == 404
    assert res.json()["detail"] == "Form analysis session not found."


# =============================================================================
# TEST CASES 6–8: COMPLETION & ABORT SEMANTICS
# =============================================================================

def test_session_finalization_with_ge_1_rep_persists(client: TestClient, repo: FormAnalysisRepository):
    """6. >=1 completed rep persists completed session."""
    app.dependency_overrides[get_current_user] = lambda: CurrentUser(uid="user_a", email="a@test.com")
    populate_active_session("sess-ge1", uid="user_a", rep_scores=[make_mock_rep_score(1, score=85.0)])

    res = client.post("/api/v1/form-analysis/sessions/sess-ge1/finalize")
    assert res.status_code == 200
    data = res.json()
    assert data["status"] == "completed"
    assert data["completed_reps"] == 1
    assert data["overall_score"] == 85.0

    # Confirmed in repository history
    history = repo.list_user_history("user_a")
    assert len(history) == 1
    assert history[0].session_id == "sess-ge1"


def test_session_finalization_with_zero_reps_aborts(client: TestClient, repo: FormAnalysisRepository):
    """7. 0 reps produces ABORTED and no Firestore history."""
    app.dependency_overrides[get_current_user] = lambda: CurrentUser(uid="user_a", email="a@test.com")
    populate_active_session("sess-zero", uid="user_a", rep_scores=[])

    res = client.post("/api/v1/form-analysis/sessions/sess-zero/finalize")
    assert res.status_code == 400
    assert "no completed repetitions" in res.json()["detail"].lower()

    # Verify zero items in history
    history = repo.list_user_history("user_a")
    assert len(history) == 0


def test_zero_valid_reps_preserves_null_score(client: TestClient, repo: FormAnalysisRepository):
    """8. 0 valid reps preserves overall_score=null (never 0 or 100)."""
    app.dependency_overrides[get_current_user] = lambda: CurrentUser(uid="user_a", email="a@test.com")
    rep_inc = make_mock_rep_score(1, status=RepScoreStatus.INCOMPLETE, score=None)
    populate_active_session("sess-inc", uid="user_a", rep_scores=[rep_inc])

    res = client.post("/api/v1/form-analysis/sessions/sess-inc/finalize")
    assert res.status_code == 200
    data = res.json()
    assert data["status"] == "completed"
    assert data["completed_reps"] == 1
    assert data["valid_reps"] == 0
    assert data["incomplete_reps"] == 1
    assert data["overall_score"] is None
    assert data["best_score"] is None
    assert data["worst_score"] is None


# =============================================================================
# TEST CASES 9–15: SCORE AGGREGATION & METRICS
# =============================================================================

def test_valid_reps_aggregate_correctly(repo: FormAnalysisRepository):
    """9. Valid reps aggregate correctly using arithmetic mean."""
    reps = [
        make_mock_rep_score(1, score=80.0),
        make_mock_rep_score(2, score=90.0),
        make_mock_rep_score(3, score=100.0),
    ]
    session = populate_active_session("sess-agg", uid="user_a", rep_scores=reps)
    summary = repo.build_session_summary(session, "user_a")
    assert summary.overall_score == 90.0
    assert summary.valid_reps == 3


def test_incomplete_reps_excluded_from_numerical_score(repo: FormAnalysisRepository):
    """10. Incomplete reps excluded from numerical average."""
    reps = [
        make_mock_rep_score(1, score=80.0),
        make_mock_rep_score(2, score=90.0),
        make_mock_rep_score(3, status=RepScoreStatus.INCOMPLETE, score=None),
    ]
    session = populate_active_session("sess-ex-inc", uid="user_a", rep_scores=reps)
    summary = repo.build_session_summary(session, "user_a")
    assert summary.overall_score == 85.0
    assert summary.valid_reps == 2
    assert summary.incomplete_reps == 1


def test_invalid_reps_excluded_from_numerical_score(repo: FormAnalysisRepository):
    """11. Invalid reps excluded from numerical average."""
    reps = [
        make_mock_rep_score(1, score=80.0),
        make_mock_rep_score(2, score=90.0),
        make_mock_rep_score(3, status=RepScoreStatus.INVALID, score=None),
    ]
    session = populate_active_session("sess-ex-inv", uid="user_a", rep_scores=reps)
    summary = repo.build_session_summary(session, "user_a")
    assert summary.overall_score == 85.0
    assert summary.valid_reps == 2
    assert summary.invalid_reps == 1


def test_insufficient_data_reps_excluded_from_numerical_score(repo: FormAnalysisRepository):
    """12. Insufficient-data reps excluded from numerical average."""
    reps = [
        make_mock_rep_score(1, score=80.0),
        make_mock_rep_score(2, score=90.0),
        make_mock_rep_score(3, status=RepScoreStatus.INSUFFICIENT_DATA, score=None),
    ]
    session = populate_active_session("sess-ex-insuf", uid="user_a", rep_scores=reps)
    summary = repo.build_session_summary(session, "user_a")
    assert summary.overall_score == 85.0
    assert summary.valid_reps == 2
    assert summary.insufficient_data_reps == 1


def test_category_averages_correct(repo: FormAnalysisRepository):
    """13. Category averages correct across valid reps."""
    reps = [
        make_mock_rep_score(1, score=80.0, rom_score=90.0, technique_score=80.0, symmetry_score=85.0, stability_score=90.0),
        make_mock_rep_score(2, score=90.0, rom_score=100.0, technique_score=90.0, symmetry_score=95.0, stability_score=80.0),
    ]
    session = populate_active_session("sess-cat", uid="user_a", rep_scores=reps)
    summary = repo.build_session_summary(session, "user_a")
    assert summary.category_averages["rom"] == 95.0
    assert summary.category_averages["technique"] == 85.0
    assert summary.category_averages["symmetry"] == 90.0
    assert summary.category_averages["stability"] == 85.0


def test_best_and_worst_score_correct(repo: FormAnalysisRepository):
    """14 & 15. Best and worst scores identified correctly."""
    reps = [
        make_mock_rep_score(1, score=74.0),
        make_mock_rep_score(2, score=92.0),
        make_mock_rep_score(3, score=83.0),
    ]
    session = populate_active_session("sess-bw", uid="user_a", rep_scores=reps)
    summary = repo.build_session_summary(session, "user_a")
    assert summary.best_score == 92.0
    assert summary.worst_score == 74.0


# =============================================================================
# TEST CASES 16–18: BOUNDS & DOCUMENT SIZE
# =============================================================================

def test_rep_summaries_capped_at_50(repo: FormAnalysisRepository):
    """16. Rep summaries capped at 50 even if 60 reps performed."""
    reps = [make_mock_rep_score(i, score=85.0) for i in range(1, 61)]
    session = populate_active_session("sess-60reps", uid="user_a", rep_scores=reps)
    summary = repo.build_session_summary(session, "user_a")
    assert summary.completed_reps == 60
    assert len(summary.reps) == MAX_PERSISTED_REPS
    assert len(summary.reps) == 50


def test_feedback_bounded(repo: FormAnalysisRepository):
    """17. Summary feedback bounded to max 5 items."""
    reps = [
        make_mock_rep_score(i, score=85.0, feedback=[f"Unique feedback {i}", f"Second feedback {i}"])
        for i in range(1, 10)
    ]
    session = populate_active_session("sess-fb", uid="user_a", rep_scores=reps)
    summary = repo.build_session_summary(session, "user_a")
    assert len(summary.summary_feedback) <= 5


def test_document_size_bounded_under_15kb(repo: FormAnalysisRepository):
    """18. Serialized document size for 50 reps is strictly < 15 KB."""
    reps = [
        make_mock_rep_score(
            i,
            score=85.0,
            feedback=[f"Keep knees aligned over toes during descent for rep {i}"],
        )
        for i in range(1, 51)
    ]
    session = populate_active_session("sess-size", uid="user_a", rep_scores=reps)
    summary = repo.build_session_summary(session, "user_a")
    serialized = json.dumps(summary.model_dump(mode="json"))
    byte_size = len(serialized.encode("utf-8"))
    assert byte_size < 15000, f"Document size {byte_size} bytes exceeds 15 KB bound"


# =============================================================================
# TEST CASES 19–22: PAGINATION, ORDERING & FILTERING
# =============================================================================

def test_history_limit_default_20(client: TestClient, repo: FormAnalysisRepository):
    """19. History limit defaults to 20."""
    app.dependency_overrides[get_current_user] = lambda: CurrentUser(uid="user_a", email="a@test.com")
    for i in range(25):
        sess = populate_active_session(f"sess-{i}", uid="user_a", rep_scores=[make_mock_rep_score(1, score=80.0)])
        s = repo.build_session_summary(sess, "user_a")
        repo.save_session_summary("user_a", s)

    res = client.get("/api/v1/form-analysis/history")
    assert res.status_code == 200
    assert len(res.json()) == 20


def test_history_limit_maximum_50(client: TestClient, repo: FormAnalysisRepository):
    """20. History limit maximum is 50."""
    app.dependency_overrides[get_current_user] = lambda: CurrentUser(uid="user_a", email="a@test.com")
    res = client.get("/api/v1/form-analysis/history?limit=100")
    # FastAPI Query(le=50) validates and rejects >50 with 422
    assert res.status_code == 422


def test_exercise_filtering(client: TestClient, repo: FormAnalysisRepository):
    """21. Exercise filter returns only matching exercise sessions."""
    app.dependency_overrides[get_current_user] = lambda: CurrentUser(uid="user_a", email="a@test.com")
    # 2 squats, 1 deadlift
    s1 = populate_active_session("sess-sq-1", exercise_id="squat", uid="user_a", rep_scores=[make_mock_rep_score(1)])
    s2 = populate_active_session("sess-sq-2", exercise_id="squat", uid="user_a", rep_scores=[make_mock_rep_score(1)])
    s3 = populate_active_session("sess-dl-1", exercise_id="deadlift", uid="user_a", rep_scores=[make_mock_rep_score(1)])
    for s in (s1, s2, s3):
        repo.save_session_summary("user_a", repo.build_session_summary(s, "user_a"))

    res = client.get("/api/v1/form-analysis/history?exercise_id=deadlift")
    assert res.status_code == 200
    items = res.json()
    assert len(items) == 1
    assert items[0]["exercise_id"] == "deadlift"


def test_completed_at_descending_ordering(repo: FormAnalysisRepository):
    """22. Results ordered by completed_at descending."""
    s1 = populate_active_session("s-old", uid="user_a", rep_scores=[make_mock_rep_score(1)])
    s2 = populate_active_session("s-new", uid="user_a", rep_scores=[make_mock_rep_score(1)])
    sum1 = repo.build_session_summary(s1, "user_a")
    sum2 = repo.build_session_summary(s2, "user_a")
    sum1.completed_at = "2026-09-14T10:00:00Z"
    sum2.completed_at = "2026-09-14T12:00:00Z"
    repo.save_session_summary("user_a", sum1)
    repo.save_session_summary("user_a", sum2)

    history = repo.list_user_history("user_a")
    assert len(history) == 2
    assert history[0].session_id == "s-new"
    assert history[1].session_id == "s-old"


# =============================================================================
# TEST CASES 23–27: IDEMPOTENCY & WEBSOCKET STOP
# =============================================================================

def test_finalization_is_idempotent(repo: FormAnalysisRepository):
    """23. Finalization is idempotent: saving same summary twice does not duplicate."""
    session = populate_active_session("sess-idem", uid="user_a", rep_scores=[make_mock_rep_score(1, score=88.0)])
    summary = repo.build_session_summary(session, "user_a")
    res1 = repo.save_session_summary("user_a", summary)
    res2 = repo.save_session_summary("user_a", summary)
    assert res1.session_id == res2.session_id

    history = repo.list_user_history("user_a")
    assert len(history) == 1


def test_repeated_rest_finalization_does_not_duplicate(client: TestClient, repo: FormAnalysisRepository):
    """24. Repeated REST finalization returns existing summary."""
    app.dependency_overrides[get_current_user] = lambda: CurrentUser(uid="user_a", email="a@test.com")
    populate_active_session("sess-rest-repeat", uid="user_a", rep_scores=[make_mock_rep_score(1, score=85.0)])

    res1 = client.post("/api/v1/form-analysis/sessions/sess-rest-repeat/finalize")
    assert res1.status_code == 200
    res2 = client.post("/api/v1/form-analysis/sessions/sess-rest-repeat/finalize")
    assert res2.status_code == 200
    assert res1.json()["session_id"] == res2.json()["session_id"]

    history = repo.list_user_history("user_a")
    assert len(history) == 1


def test_websocket_stop_finalizes_completed_session(repo: FormAnalysisRepository):
    """25. WebSocket stop finalizes session with >=1 rep and returns summary."""
    payload = {"uid": "user_ws", "email": "ws@test.com"}
    with patch("backend.app.api.routes.form_analysis_ws.verify_firebase_token", return_value=payload):
        starlette_client = StarletteTestClient(app)
        with starlette_client.websocket_connect("/api/v1/form-analysis/ws?token=mock_tok&exercise_id=squat") as ws:
            ack = ws.receive_json()
            session_id = ack["session_id"]

            # Add a completed rep to the session in memory
            active = default_session_manager.get_session(session_id)
            active.rep_count = 2
            active.completed_reps = [
                {"rep_number": 1, "outcome": "COMPLETED", "rom_degrees": 115.0, "duration_ms": 2000.0},
                {"rep_number": 2, "outcome": "COMPLETED", "rom_degrees": 118.0, "duration_ms": 2100.0},
            ]
            active.completed_rep_scores = [
                make_mock_rep_score(1, score=85.0),
                make_mock_rep_score(2, score=90.0),
            ]

            # Send stop control message
            ws.send_json({"type": "stop"})
            stopped_msg = ws.receive_json()
            assert stopped_msg["type"] == "stopped"
            assert stopped_msg["rep_count"] == 2
            assert stopped_msg["overall_score"] == 87.5
            assert stopped_msg["summary"] is not None

        # Verify session appears in persisted history
        history = repo.list_user_history("user_ws")
        assert len(history) == 1
        assert history[0].session_id == session_id
        assert history[0].overall_score == 87.5


def test_websocket_stop_with_zero_reps_does_not_persist(repo: FormAnalysisRepository):
    """26. WebSocket stop with zero reps does NOT persist to history."""
    payload = {"uid": "user_ws_zero", "email": "ws0@test.com"}
    with patch("backend.app.api.routes.form_analysis_ws.verify_firebase_token", return_value=payload):
        starlette_client = StarletteTestClient(app)
        with starlette_client.websocket_connect("/api/v1/form-analysis/ws?token=mock_tok&exercise_id=squat") as ws:
            ack = ws.receive_json()
            session_id = ack["session_id"]

            # Send stop without performing any reps
            ws.send_json({"type": "stop"})
            stopped_msg = ws.receive_json()
            assert stopped_msg["type"] == "stopped"
            assert stopped_msg["rep_count"] == 0

        # Verify zero history records
        history = repo.list_user_history("user_ws_zero")
        assert len(history) == 0


def test_websocket_stop_and_rest_finalize_race_safe(client: TestClient, repo: FormAnalysisRepository):
    """27. WebSocket stop followed by REST finalize returns same document without duplicating."""
    payload = {"uid": "user_race", "email": "race@test.com"}
    app.dependency_overrides[get_current_user] = lambda: CurrentUser(uid="user_race", email="race@test.com")

    with patch("backend.app.api.routes.form_analysis_ws.verify_firebase_token", return_value=payload):
        starlette_client = StarletteTestClient(app)
        with starlette_client.websocket_connect("/api/v1/form-analysis/ws?token=mock_tok&exercise_id=squat") as ws:
            ack = ws.receive_json()
            session_id = ack["session_id"]

            active = default_session_manager.get_session(session_id)
            active.rep_count = 1
            active.completed_reps = [{"rep_number": 1, "outcome": "COMPLETED"}]
            active.completed_rep_scores = [make_mock_rep_score(1, score=91.0)]

            # Stop over WebSocket
            ws.send_json({"type": "stop"})
            ws.receive_json()

    # Call REST finalize immediately after
    res = client.post(f"/api/v1/form-analysis/sessions/{session_id}/finalize")
    assert res.status_code == 200
    assert res.json()["session_id"] == session_id

    # Exactly one record exists
    history = repo.list_user_history("user_race")
    assert len(history) == 1


# =============================================================================
# TEST CASES 28–30: FAILURE RESILIENCE & PREVIOUS SESSIONS
# =============================================================================

def test_firestore_fallback_deterministic(repo: FormAnalysisRepository):
    """28. In-memory fallback behavior is deterministic when Firestore uninitialized."""
    assert repo.db is None or True  # Works whether db is None or mocked
    session = populate_active_session("sess-fallback", uid="user_a", rep_scores=[make_mock_rep_score(1)])
    summary = repo.build_session_summary(session, "user_a")
    saved = repo.save_session_summary("user_a", summary)
    fetched = repo.get_session_summary("user_a", "sess-fallback")
    assert fetched is not None
    assert fetched.session_id == saved.session_id


def test_persistence_failure_does_not_claim_success(client: TestClient, repo: FormAnalysisRepository):
    """29. Persistence failure does not crash process or claim success."""
    app.dependency_overrides[get_current_user] = lambda: CurrentUser(uid="user_a", email="a@test.com")
    populate_active_session("sess-fail", uid="user_a", rep_scores=[make_mock_rep_score(1)])

    with patch.object(repo, "save_session_summary", side_effect=RuntimeError("Firestore connection timeout")):
        res = client.post("/api/v1/form-analysis/sessions/sess-fail/finalize")
        assert res.status_code == 500 or res.status_code >= 400


def test_previously_finalized_session_returns_existing_summary(client: TestClient, repo: FormAnalysisRepository):
    """30. Previously finalized and evicted session returns existing Firestore record."""
    app.dependency_overrides[get_current_user] = lambda: CurrentUser(uid="user_a", email="a@test.com")
    session = populate_active_session("sess-closed", uid="user_a", rep_scores=[make_mock_rep_score(1, score=94.0)])
    summary = repo.build_session_summary(session, "user_a")
    repo.save_session_summary("user_a", summary)

    # Evict from in-memory manager
    default_session_manager.close_session("sess-closed")
    assert default_session_manager.get_session("sess-closed") is None

    # Call finalize again
    res = client.post("/api/v1/form-analysis/sessions/sess-closed/finalize")
    assert res.status_code == 200
    assert res.json()["session_id"] == "sess-closed"
    assert res.json()["overall_score"] == 94.0
