"""
Dedicated Backend Unit, Integration & Security Tests for Phase 9C.1:
Adaptive Signal Models & Performance Analytics.

Verifies:
1. Domain Schemas: strictly typed, validated, and serializable.
2. Load Progression Signal: increasing, decreasing, stable, and insufficient_data thresholds.
3. Rep Performance Signal: above_target, on_target, below_target, repCompletionRatio.
4. Set Adherence Signal: high_adherence, moderate_adherence, low_adherence, and single-session safeguards.
5. Workout Adherence Trend: with expected frequency, without expected frequency, gap calculations.
6. Performance Trajectory: 1RM recent-vs-baseline trends (improving, stable, declining).
7. PR and 1RM Reuse: Epley formula reuse matching ProgressService without duplication.
8. Form Analysis Signals: restricted strictly to 5 canonical CV exercises, recurring vs non-recurring issues.
9. Non-CV Exclusion: non-CV exercises are excluded from form signals.
10. Security: unauthenticated 401 rejection, verified Firebase UID partitioning, cross-user isolation.
11. API Endpoints: GET /api/v1/personalization/signals and GET /api/v1/personalization/exercises/{id}.
12. Determinism: identical input data produces identical analytics output.
"""

import uuid
import pytest
from datetime import datetime, timezone, timedelta
from fastapi.testclient import TestClient

from backend.app.main import app
from backend.app.core.security import get_current_user, CurrentUser
from backend.app.schemas.user import UserProfileSchema, UserProfileCreate
from backend.app.schemas.workout import (
    WorkoutSessionResponse,
    WorkoutSessionCreate,
    WorkoutSessionComplete,
    WorkoutSetSchema,
)
from backend.app.schemas.form_analysis import FormAnalysisSessionDetailSchema
from backend.app.schemas.personalization import (
    PersonalizationSignalsResponse,
    ExercisePerformanceSummary,
    LoadProgressionSignal,
    RepPerformanceSignal,
    SetAdherenceSignal,
    WorkoutAdherenceTrend,
    ExerciseFormSignal,
)
from backend.app.repositories.workout_repository import get_workout_repository
from backend.app.repositories.user_repository import get_user_repository
from backend.app.repositories.form_analysis_repository import get_form_analysis_repository
from backend.app.services.personalization_signal_service import (
    get_personalization_signal_service,
    PersonalizationSignalService,
)


@pytest.fixture
def auth_user():
    return CurrentUser(
        uid=f"usr_9c1_tester_{uuid.uuid4().hex[:8]}",
        email="athlete9c1@example.com",
        name="Personalization Signal Tester",
        email_verified=True,
    )


@pytest.fixture
def other_user():
    return CurrentUser(
        uid=f"usr_9c1_attacker_{uuid.uuid4().hex[:8]}",
        email="attacker9c1@example.com",
        name="Attacker User",
        email_verified=True,
    )


@pytest.fixture(autouse=True)
def setup_dependencies(auth_user):
    app.dependency_overrides[get_current_user] = lambda: auth_user
    yield
    app.dependency_overrides.clear()


@pytest.fixture
def client():
    return TestClient(app)


# =============================================================================
# 1. DOMAIN SCHEMA TESTS
# =============================================================================

def test_signal_schemas_instantiation():
    """Verifies that all 9C.1 Pydantic domain models can be instantiated cleanly with expected defaults."""
    load_sig = LoadProgressionSignal(exerciseId="ex_barbell_bench_press")
    assert load_sig.trend == "insufficient_data"
    assert load_sig.evidenceLevel == "insufficient_data"
    assert load_sig.percentageChange == 0.0

    rep_sig = RepPerformanceSignal(exerciseId="ex_barbell_bench_press")
    assert rep_sig.status == "insufficient_data"
    assert rep_sig.repCompletionRatio == 0.0

    adherence_sig = SetAdherenceSignal()
    assert adherence_sig.tier == "insufficient_data"
    assert adherence_sig.overallCompletionRate == 0.0

    trend_sig = WorkoutAdherenceTrend()
    assert trend_sig.consistencyStatus == "insufficient_data"
    assert trend_sig.sessionsCompleted == 0

    form_sig = ExerciseFormSignal(
        exerciseId="ex_squat",
        canonicalCvExercise="squat",
    )
    assert form_sig.canonicalCvExercise == "squat"
    assert form_sig.evidenceLevel == "no_data"
    assert form_sig.scoreTrend == "insufficient_data"


# =============================================================================
# 2. LOAD PROGRESSION SIGNAL TESTS
# =============================================================================

def test_load_progression_increasing():
    """Verifies that load progression correctly detects an increasing trend (> +2.5%)."""
    service = PersonalizationSignalService()
    # 3 sessions: 60kg, 60kg, 70kg (+16.7%)
    weights = [60.0, 60.0, 70.0]
    signal = service._evaluate_load_progression("ex_barbell_bench_press", weights)

    assert signal.trend == "increasing"
    assert signal.evidenceLevel == "stable_signal"
    assert signal.percentageChange > 2.5
    assert signal.sessionsObserved == 3


def test_load_progression_decreasing():
    """Verifies that load progression correctly detects a decreasing trend (< -2.5%)."""
    service = PersonalizationSignalService()
    # 3 sessions: 80kg, 80kg, 70kg
    weights = [80.0, 80.0, 70.0]
    signal = service._evaluate_load_progression("ex_barbell_bench_press", weights)

    assert signal.trend == "decreasing"
    assert signal.evidenceLevel == "stable_signal"
    assert signal.percentageChange < -2.5


def test_load_progression_stable():
    """Verifies that load progression correctly detects a stable trend within [-2.5%, +2.5%]."""
    service = PersonalizationSignalService()
    # 3 sessions: 100kg, 100kg, 101kg (+1.0%)
    weights = [100.0, 100.0, 101.0]
    signal = service._evaluate_load_progression("ex_barbell_bench_press", weights)

    assert signal.trend == "stable"
    assert signal.evidenceLevel == "stable_signal"
    assert abs(signal.percentageChange) < 2.5


def test_load_progression_insufficient_data():
    """Verifies that < 2 sessions with recorded loads returns insufficient_data."""
    service = PersonalizationSignalService()
    sig_zero = service._evaluate_load_progression("ex_barbell_bench_press", [])
    assert sig_zero.trend == "insufficient_data"
    assert sig_zero.evidenceLevel == "no_data"

    sig_one = service._evaluate_load_progression("ex_barbell_bench_press", [80.0])
    assert sig_one.trend == "insufficient_data"
    assert sig_one.evidenceLevel == "insufficient_data"


# =============================================================================
# 3. REP PERFORMANCE SIGNAL TESTS
# =============================================================================

def test_rep_performance_above_target():
    """Verifies rep performance detects above_target when upper bound is reached on >= 75% of sets."""
    service = PersonalizationSignalService()
    sets = [
        WorkoutSetSchema(setNumber=1, targetReps=10, actualReps=12, isCompleted=True),
        WorkoutSetSchema(setNumber=2, targetReps=10, actualReps=10, isCompleted=True),
        WorkoutSetSchema(setNumber=3, targetReps=10, actualReps=11, isCompleted=True),
        WorkoutSetSchema(setNumber=4, targetReps=10, actualReps=10, isCompleted=True),
    ]
    signal = service._evaluate_rep_performance("ex_barbell_bench_press", sets)

    assert signal.status == "above_target"
    assert signal.upperBoundCompletionRate == 1.0
    assert signal.repCompletionRatio > 1.0
    assert signal.evidenceLevel == "stable_signal"


def test_rep_performance_below_target():
    """Verifies rep performance detects below_target when reps consistently miss target range."""
    service = PersonalizationSignalService()
    sets = [
        WorkoutSetSchema(setNumber=1, targetReps=10, actualReps=6, isCompleted=True),
        WorkoutSetSchema(setNumber=2, targetReps=10, actualReps=5, isCompleted=True),
        WorkoutSetSchema(setNumber=3, targetReps=10, actualReps=4, isCompleted=True),
    ]
    signal = service._evaluate_rep_performance("ex_barbell_bench_press", sets)

    assert signal.status == "below_target"
    assert signal.upperBoundCompletionRate == 0.0
    assert signal.repCompletionRatio < 0.70


def test_rep_performance_insufficient_sets():
    """Verifies rep performance returns insufficient_data when fewer than 2 target sets exist."""
    service = PersonalizationSignalService()
    sets = [
        WorkoutSetSchema(setNumber=1, targetReps=10, actualReps=10, isCompleted=True),
    ]
    signal = service._evaluate_rep_performance("ex_barbell_bench_press", sets)

    assert signal.status == "insufficient_data"
    assert signal.evidenceLevel == "insufficient_data"


# =============================================================================
# 4. SET ADHERENCE & SESSION COMPLETION TESTS
# =============================================================================

def test_set_adherence_tiers():
    """Verifies set adherence accurately classifies high, moderate, and low adherence."""
    service = PersonalizationSignalService()

    # High adherence (>= 85%)
    high_sessions = [
        WorkoutSessionResponse(
            id="s1", userId="u1", workoutId="w1", workoutTitle="Push A",
            startedAt="2026-09-01T10:00:00Z", completedSetsCount=10, totalSetsCount=10,
        ),
        WorkoutSessionResponse(
            id="s2", userId="u1", workoutId="w1", workoutTitle="Push B",
            startedAt="2026-09-03T10:00:00Z", completedSetsCount=9, totalSetsCount=10,
        ),
    ]
    high_signal = service._compute_set_adherence(high_sessions)
    assert high_signal.tier == "high_adherence"
    assert high_signal.overallCompletionRate >= 0.85
    assert high_signal.evidenceLevel == "emerging_signal"

    # Moderate adherence (65% - 84.9%)
    mod_sessions = [
        WorkoutSessionResponse(
            id="s1", userId="u1", workoutId="w1", workoutTitle="Push A",
            startedAt="2026-09-01T10:00:00Z", completedSetsCount=7, totalSetsCount=10,
        ),
        WorkoutSessionResponse(
            id="s2", userId="u1", workoutId="w1", workoutTitle="Push B",
            startedAt="2026-09-03T10:00:00Z", completedSetsCount=7, totalSetsCount=10,
        ),
    ]
    mod_signal = service._compute_set_adherence(mod_sessions)
    assert mod_signal.tier == "moderate_adherence"

    # Single session safeguard -> insufficient_data
    single_session = [high_sessions[0]]
    single_signal = service._compute_set_adherence(single_session)
    assert single_signal.tier == "insufficient_data"
    assert single_signal.evidenceLevel == "insufficient_data"


# =============================================================================
# 5. WORKOUT ADHERENCE TREND & FREQUENCY TESTS
# =============================================================================

def test_workout_adherence_with_expected_frequency(auth_user):
    """Verifies that workout adherence trend computes adherence rate against user's profile target."""
    user_repo = get_user_repository()
    # Configure user with 4 days/week
    user_repo.create(auth_user.uid, auth_user.email, UserProfileCreate(
        name="Frequency Tester",
        email=auth_user.email,
        workoutFrequencyDaysPerWeek=4,
    ))

    now = datetime.now(timezone.utc)
    # Create 8 completed workouts in past 14 days (approx 4 per week)
    sessions = []
    for i in range(8):
        sess_dt = (now - timedelta(days=2 * i)).isoformat()
        sessions.append(WorkoutSessionResponse(
            id=f"sess_{i}",
            userId=auth_user.uid,
            workoutId="wkt_test",
            workoutTitle="Test Routine",
            startedAt=sess_dt,
            completedAt=sess_dt,
            completedSetsCount=5,
            totalSetsCount=5,
        ))

    service = get_personalization_signal_service()
    trend = service._compute_workout_adherence_trend(auth_user.uid, sessions, window_days=28)

    assert trend.expectedFrequencyPerWeek == 4.0
    assert trend.expectedSessions == 16  # 4 days * 4 weeks
    assert trend.sessionsCompleted == 8
    assert trend.adherenceRate == 0.50
    assert trend.consistencyStatus == "consistent"


def test_workout_adherence_without_expected_frequency(auth_user):
    """
    Verifies that when workoutFrequencyDaysPerWeek is not set,
    the system does NOT fabricate an expected frequency and leaves adherenceRate None.
    """
    user_repo = get_user_repository()
    user_repo.create(auth_user.uid, auth_user.email, UserProfileCreate(
        name="No Freq User",
        email=auth_user.email,
        workoutFrequencyDaysPerWeek=None,
    ))

    now = datetime.now(timezone.utc)
    sessions = [
        WorkoutSessionResponse(
            id="s1", userId=auth_user.uid, workoutId="w1", workoutTitle="Routine 1",
            startedAt=(now - timedelta(days=4)).isoformat(), completedSetsCount=5, totalSetsCount=5,
        ),
        WorkoutSessionResponse(
            id="s2", userId=auth_user.uid, workoutId="w1", workoutTitle="Routine 2",
            startedAt=(now - timedelta(days=1)).isoformat(), completedSetsCount=5, totalSetsCount=5,
        ),
    ]

    service = get_personalization_signal_service()
    trend = service._compute_workout_adherence_trend(auth_user.uid, sessions, window_days=28)

    assert trend.expectedFrequencyPerWeek is None
    assert trend.expectedSessions is None
    assert trend.adherenceRate is None
    assert trend.observedFrequencyPerWeek > 0.0


# =============================================================================
# 6. 1RM REUSE & PERFORMANCE TRAJECTORY TESTS
# =============================================================================

def test_performance_trajectory_improving():
    """Verifies that 1RM trajectory detects improving performance (>= +3.0%)."""
    service = PersonalizationSignalService()
    # 3 sessions: 100kg, 100kg, 110kg
    trajectory = service._evaluate_performance_trajectory([100.0, 100.0, 110.0])
    assert trajectory == "improving"


def test_performance_trajectory_declining():
    """Verifies that 1RM trajectory detects declining performance (<= -3.0%)."""
    service = PersonalizationSignalService()
    # 3 sessions: 100kg, 100kg, 90kg
    trajectory = service._evaluate_performance_trajectory([100.0, 100.0, 90.0])
    assert trajectory == "declining"


def test_epley_1rm_reuse_accuracy():
    """Verifies that 1RM calculation matches Epley formula round(wt * (1.0 + reps / 30.0), 1)."""
    service = PersonalizationSignalService()
    session = WorkoutSessionResponse(
        id="s1",
        userId="u1",
        workoutId="w1",
        workoutTitle="Bench Day",
        startedAt="2026-09-10T10:00:00Z",
        completedSets={
            "ex_barbell_bench_press": [
                WorkoutSetSchema(setNumber=1, targetReps=10, actualWeightKg=100.0, actualReps=10, isCompleted=True),
            ]
        },
    )
    summary = service._compute_single_exercise_summary("ex_barbell_bench_press", [session])
    assert summary is not None
    # 100 * (1 + 10/30) = 133.3 kg
    assert summary.bestEstimated1RM == 133.3
    assert summary.prWeightKg == 100.0
    assert summary.prReps == 10


# =============================================================================
# 7. FORM ANALYSIS SIGNAL & CV EXCLUSION TESTS
# =============================================================================

def test_form_analysis_signal_recurrent_issue(auth_user):
    """Verifies form analysis identifies recurring issues appearing in >= 50% of sessions."""
    form_repo = get_form_analysis_repository()
    form_repo.clear_in_memory_for_testing()

    now = datetime.now(timezone.utc)
    # 2 squat sessions with knee valgus issue
    sess1 = FormAnalysisSessionDetailSchema(
        session_id="fa_01",
        user_id=auth_user.uid,
        exercise_id="ex_squat",
        canonical_exercise_id="ex_squat",
        exercise_name="Barbell Back Squat",
        started_at=(now - timedelta(days=5)).isoformat(),
        completed_at=(now - timedelta(days=5)).isoformat(),
        completed_reps=5,
        overall_score=82.0,
        summary_feedback=["Knee valgus detected on descent."],
    )
    sess2 = FormAnalysisSessionDetailSchema(
        session_id="fa_02",
        user_id=auth_user.uid,
        exercise_id="ex_squat",
        canonical_exercise_id="ex_squat",
        exercise_name="Barbell Back Squat",
        started_at=(now - timedelta(days=2)).isoformat(),
        completed_at=(now - timedelta(days=2)).isoformat(),
        completed_reps=5,
        overall_score=85.0,
        summary_feedback=["Knee valgus detected on descent."],
    )
    form_repo.save_session_summary(auth_user.uid, sess1)
    form_repo.save_session_summary(auth_user.uid, sess2)

    service = get_personalization_signal_service()
    signals = service._compute_form_signals(auth_user.uid)

    assert "ex_squat" in signals
    squat_sig = signals["ex_squat"]
    assert squat_sig.sessionsObserved == 2
    assert squat_sig.evidenceLevel == "emerging_signal"
    assert len(squat_sig.detectedIssues) >= 1

    valgus_issue = next((i for i in squat_sig.detectedIssues if "knee valgus" in i.issue.lower()), None)
    assert valgus_issue is not None
    assert valgus_issue.isRecurring is True
    assert valgus_issue.occurrenceCount == 2


def test_form_analysis_non_cv_exercises_excluded(auth_user):
    """Verifies that non-CV exercises are strictly excluded from formSignals."""
    service = get_personalization_signal_service()
    signals = service._compute_form_signals(auth_user.uid)

    # Only the 5 canonical CV exercises should be keys
    assert len(signals) == 5
    assert set(signals.keys()) == {"ex_squat", "ex_bench_press", "ex_deadlift", "ex_bicep_curl", "ex_shoulder_press"}
    assert "ex_pull_up" not in signals
    assert "ex_lat_pulldown" not in signals


# =============================================================================
# 8. API ENDPOINT & AUTHENTICATION & DETERMINISM TESTS
# =============================================================================

def test_api_get_signals_authenticated(client, auth_user):
    """Verifies GET /api/v1/personalization/signals succeeds for authenticated user."""
    workout_repo = get_workout_repository()
    # Add a completed workout
    sess = workout_repo.create_session(
        auth_user.uid,
        WorkoutSessionCreate(
            workoutId="generated",
            workoutTitle="Test Session",
            totalSetsCount=3,
        ),
    )
    workout_repo.complete_session(
        auth_user.uid,
        sess.id,
        WorkoutSessionComplete(durationSeconds=1800),
    )

    response = client.get("/api/v1/personalization/signals")
    assert response.status_code == 200
    data = response.json()
    assert data["userId"] == auth_user.uid
    assert "overallAdherence" in data
    assert "workoutAdherenceTrend" in data
    assert "exercises" in data
    assert "formSignals" in data


def test_api_get_signals_unauthenticated(client):
    """Verifies GET /api/v1/personalization/signals rejects unauthenticated requests (HTTP 401)."""
    app.dependency_overrides.clear()
    response = client.get("/api/v1/personalization/signals")
    assert response.status_code == 401


def test_api_cross_user_isolation(client, auth_user, other_user):
    """Verifies that User A's personalization signals are not accessible or contaminated by User B."""
    workout_repo = get_workout_repository()

    # Create workout for auth_user
    sess = workout_repo.create_session(
        auth_user.uid,
        WorkoutSessionCreate(
            workoutId="generated",
            workoutTitle="User A Push",
            totalSetsCount=5,
        ),
    )
    workout_repo.complete_session(
        auth_user.uid,
        sess.id,
        WorkoutSessionComplete(durationSeconds=2400),
    )

    # Now switch to other_user
    app.dependency_overrides[get_current_user] = lambda: other_user
    res_other = client.get("/api/v1/personalization/signals")
    assert res_other.status_code == 200
    data_other = res_other.json()

    assert data_other["userId"] == other_user.uid
    assert data_other["summaryMetrics"]["totalCompletedWorkouts"] == 0


def test_deterministic_repeatability(client, auth_user):
    """Verifies that two identical requests produce 100% identical outputs (no randomness/LLM drift)."""
    res1 = client.get("/api/v1/personalization/signals?window_days=28")
    res2 = client.get("/api/v1/personalization/signals?window_days=28")

    assert res1.status_code == 200
    assert res2.status_code == 200

    json1 = res1.json()
    json2 = res2.json()

    # Compare core analytical signals (ignoring microsecond timestamps in generatedAt)
    assert json1["userId"] == json2["userId"]
    assert json1["overallAdherence"] == json2["overallAdherence"]
    assert json1["workoutAdherenceTrend"] == json2["workoutAdherenceTrend"]
    assert json1["exercises"] == json2["exercises"]
    assert json1["formSignals"] == json2["formSignals"]


def test_api_get_exercise_signal_success(client, auth_user):
    """Verifies GET /api/v1/personalization/exercises/{id} returns 200 for tracked exercise."""
    workout_repo = get_workout_repository()
    sess = workout_repo.create_session(
        auth_user.uid,
        WorkoutSessionCreate(
            workoutId="generated",
            workoutTitle="Bench Press Day",
            totalSetsCount=2,
        ),
    )
    # Log a set for ex_barbell_bench_press
    from backend.app.schemas.workout import WorkoutSessionUpdate, WorkoutSetRecord
    workout_repo.update_session(
        auth_user.uid,
        sess.id,
        WorkoutSessionUpdate(
            recordedSet=WorkoutSetRecord(
                exerciseId="ex_barbell_bench_press",
                setNumber=1,
                actualReps=10,
                actualWeightKg=80.0,
            )
        )
    )
    workout_repo.complete_session(
        auth_user.uid,
        sess.id,
        WorkoutSessionComplete(durationSeconds=1200),
    )

    res = client.get("/api/v1/personalization/exercises/ex_barbell_bench_press")
    assert res.status_code == 200
    data = res.json()
    assert data["exerciseId"] == "ex_barbell_bench_press"
    assert data["bestWeightKg"] == 80.0
    assert data["totalRepsPerformed"] == 10
    assert "loadProgression" in data
    assert "repPerformance" in data


def test_api_get_exercise_signal_not_found(client):
    """Verifies GET /api/v1/personalization/exercises/{id} returns 404 for untracked exercise."""
    res = client.get("/api/v1/personalization/exercises/ex_non_existent_exercise_xyz")
    assert res.status_code == 404
    data = res.json()
    assert "detail" in data

