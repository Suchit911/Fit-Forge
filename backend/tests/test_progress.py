from datetime import datetime, timezone, timedelta
from unittest.mock import patch
from fastapi.testclient import TestClient
from backend.app.main import app
from backend.app.core.security import CurrentUser, get_current_user
from backend.app.repositories.exercise_repository import ExerciseRepository, get_exercise_repository
from backend.app.repositories.workout_repository import WorkoutRepository, get_workout_repository
from backend.app.repositories.user_repository import UserRepository, get_user_repository
import pytest


@pytest.fixture
def mock_wkt_repo():
    """Provides an isolated in-memory WorkoutRepository."""
    return WorkoutRepository(db=None)


@pytest.fixture
def mock_ex_repo():
    """Provides an isolated in-memory ExerciseRepository."""
    return ExerciseRepository(db=None)


@pytest.fixture
def mock_user_repo():
    """Provides an isolated in-memory UserRepository."""
    return UserRepository(db=None)


# =============================================================================
# 1. PROGRESS SUMMARY FOR AUTHENTICATED USER
# =============================================================================

def test_progress_summary_authenticated_user(
    client: TestClient,
    mock_wkt_repo: WorkoutRepository,
    mock_ex_repo: ExerciseRepository,
    mock_user_repo: UserRepository,
):
    """1. Test that GET /api/v1/progress/summary returns correct aggregated stats for completed workouts."""
    user = CurrentUser(uid="user_progress_1", email="p1@pulseai.fit", name="Progress Hero", email_verified=True)
    app.dependency_overrides[get_current_user] = lambda: user
    app.dependency_overrides[get_workout_repository] = lambda: mock_wkt_repo
    app.dependency_overrides[get_exercise_repository] = lambda: mock_ex_repo
    app.dependency_overrides[get_user_repository] = lambda: mock_user_repo

    try:
        # 1. Create and complete session 1
        s1 = client.post("/api/v1/workouts/wkt_upper_push/sessions").json()["id"]
        client.patch(
            f"/api/v1/workouts/sessions/{s1}",
            json={
                "elapsedSeconds": 600,
                "recordedSet": {
                    "exerciseId": "ex_bench_press",
                    "setNumber": 1,
                    "actualReps": 10,
                    "actualWeightKg": 80.0,
                    "rpe": 8.0,
                },
            },
        )
        client.post(f"/api/v1/workouts/sessions/{s1}/complete", json={"durationSeconds": 1800})

        # 2. Check summary
        res = client.get("/api/v1/progress/summary?period=30d")
        assert res.status_code == 200
        data = res.json()
        assert data["totalWorkouts"] == 1
        assert data["totalVolumeKg"] == 800.0  # 10 * 80
        assert data["totalDurationMinutes"] == 30  # 1800s
        assert data["totalCaloriesBurned"] > 0
        assert data["currentStreakDays"] >= 1
    finally:
        app.dependency_overrides.clear()


# =============================================================================
# 2. PROGRESS SUMMARY WITH NO COMPLETED WORKOUTS (ZERO VALUES)
# =============================================================================

def test_progress_summary_empty_state(
    client: TestClient,
    mock_wkt_repo: WorkoutRepository,
    mock_ex_repo: ExerciseRepository,
    mock_user_repo: UserRepository,
):
    """2. Test that an authenticated user with no workouts receives clean zeros and no errors."""
    user = CurrentUser(uid="fresh_athlete", email="fresh@pulseai.fit", name="New Athlete", email_verified=True)
    app.dependency_overrides[get_current_user] = lambda: user
    app.dependency_overrides[get_workout_repository] = lambda: mock_wkt_repo
    app.dependency_overrides[get_exercise_repository] = lambda: mock_ex_repo
    app.dependency_overrides[get_user_repository] = lambda: mock_user_repo

    try:
        res = client.get("/api/v1/progress/summary?period=30d")
        assert res.status_code == 200
        data = res.json()
        assert data["totalWorkouts"] == 0
        assert data["totalVolumeKg"] == 0.0
        assert data["totalDurationMinutes"] == 0
        assert data["totalCaloriesBurned"] == 0
        assert data["avgWorkoutDurationMinutes"] == 0
        assert data["currentStreakDays"] == 0
        assert data["weeklyConsistencyDays"] == 0
        assert "0%" in data["comparison"]["workoutsChangePct"]
    finally:
        app.dependency_overrides.clear()


# =============================================================================
# 3. PROGRESS DATE FILTERING (7d, 30d, 90d)
# =============================================================================

def test_progress_date_filtering(
    client: TestClient,
    mock_wkt_repo: WorkoutRepository,
    mock_ex_repo: ExerciseRepository,
    mock_user_repo: UserRepository,
):
    """3. Test that time period filters (7d, 30d, 90d) correctly partition completed sessions."""
    user = CurrentUser(uid="filter_user", email="filter@pulseai.fit", name="Filter Pro", email_verified=True)
    app.dependency_overrides[get_current_user] = lambda: user
    app.dependency_overrides[get_workout_repository] = lambda: mock_wkt_repo
    app.dependency_overrides[get_exercise_repository] = lambda: mock_ex_repo
    app.dependency_overrides[get_user_repository] = lambda: mock_user_repo

    try:
        now = datetime.now(timezone.utc)
        # Create session 3 days ago (in 7d, 30d, 90d)
        s1 = client.post("/api/v1/workouts/wkt_upper_push/sessions").json()["id"]
        client.post(f"/api/v1/workouts/sessions/{s1}/complete", json={"durationSeconds": 1800})
        mock_wkt_repo._in_memory_sessions[f"{user.uid}:{s1}"]["startedAt"] = (now - timedelta(days=3)).isoformat()
        mock_wkt_repo._in_memory_sessions[f"{user.uid}:{s1}"]["completedAt"] = (now - timedelta(days=3)).isoformat()
        mock_wkt_repo._in_memory_sessions[f"{user.uid}:{s1}"]["totalVolumeKg"] = 1000.0

        # Create session 20 days ago (in 30d, 90d; NOT in 7d)
        s2 = client.post("/api/v1/workouts/wkt_lower_strength/sessions").json()["id"]
        client.post(f"/api/v1/workouts/sessions/{s2}/complete", json={"durationSeconds": 2400})
        mock_wkt_repo._in_memory_sessions[f"{user.uid}:{s2}"]["startedAt"] = (now - timedelta(days=20)).isoformat()
        mock_wkt_repo._in_memory_sessions[f"{user.uid}:{s2}"]["completedAt"] = (now - timedelta(days=20)).isoformat()
        mock_wkt_repo._in_memory_sessions[f"{user.uid}:{s2}"]["totalVolumeKg"] = 2000.0

        # Create session 60 days ago (in 90d; NOT in 7d, NOT in 30d)
        s3 = client.post("/api/v1/workouts/wkt_upper_pull/sessions").json()["id"]
        client.post(f"/api/v1/workouts/sessions/{s3}/complete", json={"durationSeconds": 3000})
        mock_wkt_repo._in_memory_sessions[f"{user.uid}:{s3}"]["startedAt"] = (now - timedelta(days=60)).isoformat()
        mock_wkt_repo._in_memory_sessions[f"{user.uid}:{s3}"]["completedAt"] = (now - timedelta(days=60)).isoformat()
        mock_wkt_repo._in_memory_sessions[f"{user.uid}:{s3}"]["totalVolumeKg"] = 3000.0

        # Period: 7d -> only s1
        res_7d = client.get("/api/v1/progress/summary?period=7d").json()
        assert res_7d["totalWorkouts"] == 1
        assert res_7d["totalVolumeKg"] == 1000.0

        # Period: 30d -> s1 + s2
        res_30d = client.get("/api/v1/progress/summary?period=30d").json()
        assert res_30d["totalWorkouts"] == 2
        assert res_30d["totalVolumeKg"] == 3000.0

        # Period: 90d -> s1 + s2 + s3
        res_90d = client.get("/api/v1/progress/summary?period=90d").json()
        assert res_90d["totalWorkouts"] == 3
        assert res_90d["totalVolumeKg"] == 6000.0
    finally:
        app.dependency_overrides.clear()


# =============================================================================
# 4. WORKOUT HISTORY ORDERING (MOST RECENT FIRST)
# =============================================================================

def test_workout_history_ordering(
    client: TestClient,
    mock_wkt_repo: WorkoutRepository,
):
    """4. Test that workout history is ordered chronologically descending (most recent first)."""
    user = CurrentUser(uid="history_order_user", email="order@pulseai.fit", name="Order Pro", email_verified=True)
    app.dependency_overrides[get_current_user] = lambda: user
    app.dependency_overrides[get_workout_repository] = lambda: mock_wkt_repo

    try:
        now = datetime.now(timezone.utc)
        # Session A: 5 days ago
        sa = client.post("/api/v1/workouts/wkt_upper_push/sessions").json()["id"]
        client.post(f"/api/v1/workouts/sessions/{sa}/complete", json={"durationSeconds": 1800})
        mock_wkt_repo._in_memory_sessions[f"{user.uid}:{sa}"]["startedAt"] = (now - timedelta(days=5)).isoformat()
        mock_wkt_repo._in_memory_sessions[f"{user.uid}:{sa}"]["completedAt"] = (now - timedelta(days=5)).isoformat()

        # Session B: 1 day ago (more recent)
        sb = client.post("/api/v1/workouts/wkt_lower_strength/sessions").json()["id"]
        client.post(f"/api/v1/workouts/sessions/{sb}/complete", json={"durationSeconds": 1800})
        mock_wkt_repo._in_memory_sessions[f"{user.uid}:{sb}"]["startedAt"] = (now - timedelta(days=1)).isoformat()
        mock_wkt_repo._in_memory_sessions[f"{user.uid}:{sb}"]["completedAt"] = (now - timedelta(days=1)).isoformat()

        # Session C: 10 days ago (oldest)
        sc = client.post("/api/v1/workouts/wkt_upper_pull/sessions").json()["id"]
        client.post(f"/api/v1/workouts/sessions/{sc}/complete", json={"durationSeconds": 1800})
        mock_wkt_repo._in_memory_sessions[f"{user.uid}:{sc}"]["startedAt"] = (now - timedelta(days=10)).isoformat()
        mock_wkt_repo._in_memory_sessions[f"{user.uid}:{sc}"]["completedAt"] = (now - timedelta(days=10)).isoformat()

        history_res = client.get("/api/v1/workouts/history")
        assert history_res.status_code == 200
        history = history_res.json()
        assert len(history) == 3
        # Most recent first: B, then A, then C
        assert history[0]["id"] == sb
        assert history[1]["id"] == sa
        assert history[2]["id"] == sc
    finally:
        app.dependency_overrides.clear()


# =============================================================================
# 5. EXERCISE PROGRESSION
# =============================================================================

def test_exercise_progression(
    client: TestClient,
    mock_wkt_repo: WorkoutRepository,
    mock_ex_repo: ExerciseRepository,
    mock_user_repo: UserRepository,
):
    """5. Test that GET /api/v1/progress/exercises/{exercise_id} accurately tracks 1RM, weight, and history."""
    user = CurrentUser(uid="bench_king", email="bench@pulseai.fit", name="Bench King", email_verified=True)
    app.dependency_overrides[get_current_user] = lambda: user
    app.dependency_overrides[get_workout_repository] = lambda: mock_wkt_repo
    app.dependency_overrides[get_exercise_repository] = lambda: mock_ex_repo
    app.dependency_overrides[get_user_repository] = lambda: mock_user_repo

    try:
        # Session 1: Bench Press 60kg for 10 reps (1RM ~ 80kg)
        s1 = client.post("/api/v1/workouts/wkt_upper_push/sessions").json()["id"]
        client.patch(
            f"/api/v1/workouts/sessions/{s1}",
            json={
                "elapsedSeconds": 300,
                "recordedSet": {
                    "exerciseId": "ex_bench_press",
                    "setNumber": 1,
                    "actualReps": 10,
                    "actualWeightKg": 60.0,
                },
            },
        )
        client.post(f"/api/v1/workouts/sessions/{s1}/complete", json={"durationSeconds": 1800})

        # Session 2: Bench Press 80kg for 5 reps (1RM ~ 93.3kg)
        s2 = client.post("/api/v1/workouts/wkt_upper_push/sessions").json()["id"]
        client.patch(
            f"/api/v1/workouts/sessions/{s2}",
            json={
                "elapsedSeconds": 400,
                "recordedSet": {
                    "exerciseId": "ex_bench_press",
                    "setNumber": 1,
                    "actualReps": 5,
                    "actualWeightKg": 80.0,
                },
            },
        )
        client.post(f"/api/v1/workouts/sessions/{s2}/complete", json={"durationSeconds": 1800})

        res = client.get("/api/v1/progress/exercises/ex_bench_press")
        assert res.status_code == 200
        prog = res.json()
        assert prog["exerciseId"] == "ex_bench_press"
        assert prog["exerciseName"] in ("Bench Press", "Barbell Bench Press")
        assert prog["totalSessionsCompleted"] == 2
        assert prog["prWeightKg"] == 80.0
        assert prog["prReps"] == 5
        assert prog["bestEstimated1RM"] > 90.0
        assert len(prog["history"]) == 2
    finally:
        app.dependency_overrides.clear()


# =============================================================================
# 6. VOLUME CALCULATION FROM RECORDED SETS
# =============================================================================

def test_volume_calculation(
    client: TestClient,
    mock_wkt_repo: WorkoutRepository,
    mock_ex_repo: ExerciseRepository,
    mock_user_repo: UserRepository,
):
    """6. Test that total volume is calculated strictly from actual recorded sets (reps * weight)."""
    user = CurrentUser(uid="volume_lifter", email="vol@pulseai.fit", name="Vol Lifter", email_verified=True)
    app.dependency_overrides[get_current_user] = lambda: user
    app.dependency_overrides[get_workout_repository] = lambda: mock_wkt_repo
    app.dependency_overrides[get_exercise_repository] = lambda: mock_ex_repo
    app.dependency_overrides[get_user_repository] = lambda: mock_user_repo

    try:
        s = client.post("/api/v1/workouts/wkt_upper_push/sessions").json()["id"]
        # Set 1: 12 reps @ 50kg = 600kg
        client.patch(
            f"/api/v1/workouts/sessions/{s}",
            json={
                "elapsedSeconds": 120,
                "recordedSet": {"exerciseId": "ex_bench_press", "setNumber": 1, "actualReps": 12, "actualWeightKg": 50.0},
            },
        )
        # Set 2: 8 reps @ 100kg = 800kg
        client.patch(
            f"/api/v1/workouts/sessions/{s}",
            json={
                "elapsedSeconds": 240,
                "recordedSet": {"exerciseId": "ex_bench_press", "setNumber": 2, "actualReps": 8, "actualWeightKg": 100.0},
            },
        )
        client.post(f"/api/v1/workouts/sessions/{s}/complete", json={"durationSeconds": 1200})

        vol_res = client.get("/api/v1/progress/volume?period=30d")
        assert vol_res.status_code == 200
        vol_points = vol_res.json()
        assert len(vol_points) >= 1
        today_point = vol_points[-1]
        assert today_point["totalVolumeKg"] == 1400.0  # 600 + 800
        assert today_point["upperBodyKg"] == 1400.0  # bench press is chest/upper body
    finally:
        app.dependency_overrides.clear()


# =============================================================================
# 7. DURATION AND CALORIE AGGREGATION
# =============================================================================

def test_duration_and_calorie_aggregation(
    client: TestClient,
    mock_wkt_repo: WorkoutRepository,
    mock_ex_repo: ExerciseRepository,
    mock_user_repo: UserRepository,
):
    """7. Test that duration in minutes and calories burned sum properly across sessions."""
    user = CurrentUser(uid="cal_user", email="cal@pulseai.fit", name="Cal Pro", email_verified=True)
    app.dependency_overrides[get_current_user] = lambda: user
    app.dependency_overrides[get_workout_repository] = lambda: mock_wkt_repo
    app.dependency_overrides[get_exercise_repository] = lambda: mock_ex_repo
    app.dependency_overrides[get_user_repository] = lambda: mock_user_repo

    try:
        # Session 1: 30 minutes (1800s) -> ~225 kcal
        s1 = client.post("/api/v1/workouts/wkt_upper_push/sessions").json()["id"]
        client.post(f"/api/v1/workouts/sessions/{s1}/complete", json={"durationSeconds": 1800})

        # Session 2: 40 minutes (2400s) -> ~300 kcal
        s2 = client.post("/api/v1/workouts/wkt_lower_strength/sessions").json()["id"]
        client.post(f"/api/v1/workouts/sessions/{s2}/complete", json={"durationSeconds": 2400})

        summary = client.get("/api/v1/progress/summary?period=30d").json()
        assert summary["totalWorkouts"] == 2
        assert summary["totalDurationMinutes"] == 70  # 30 + 40
        assert summary["avgWorkoutDurationMinutes"] == 35  # 70 / 2
        assert summary["totalCaloriesBurned"] >= 500
    finally:
        app.dependency_overrides.clear()


# =============================================================================
# 8. PERSONAL RECORD CALCULATION FROM SET HISTORY
# =============================================================================

def test_personal_record_calculation(
    client: TestClient,
    mock_wkt_repo: WorkoutRepository,
    mock_ex_repo: ExerciseRepository,
    mock_user_repo: UserRepository,
):
    """8. Test that PRs in dashboard are derived directly from actual recorded max weight per exercise."""
    user = CurrentUser(uid="pr_master", email="pr@pulseai.fit", name="PR Master", email_verified=True)
    app.dependency_overrides[get_current_user] = lambda: user
    app.dependency_overrides[get_workout_repository] = lambda: mock_wkt_repo
    app.dependency_overrides[get_exercise_repository] = lambda: mock_ex_repo
    app.dependency_overrides[get_user_repository] = lambda: mock_user_repo

    try:
        # Workout with Bench Press 120kg and Barbell Squat 160kg
        s = client.post("/api/v1/workouts/wkt_upper_push/sessions").json()["id"]
        client.patch(
            f"/api/v1/workouts/sessions/{s}",
            json={
                "elapsedSeconds": 300,
                "recordedSet": {"exerciseId": "ex_bench_press", "setNumber": 1, "actualReps": 3, "actualWeightKg": 120.0},
            },
        )
        client.patch(
            f"/api/v1/workouts/sessions/{s}",
            json={
                "elapsedSeconds": 600,
                "recordedSet": {"exerciseId": "ex_barbell_squat", "setNumber": 1, "actualReps": 5, "actualWeightKg": 160.0},
            },
        )
        client.post(f"/api/v1/workouts/sessions/{s}/complete", json={"durationSeconds": 2400})

        dash = client.get("/api/v1/progress/dashboard?period=30d").json()
        prs = dash["personalRecords"]
        assert len(prs) >= 2
        bench_pr = next(p for p in prs if "Bench Press" in p["exerciseName"])
        squat_pr = next(p for p in prs if "Squat" in p["exerciseName"])
        assert "120" in bench_pr["value"]
        assert "160" in squat_pr["value"]
    finally:
        app.dependency_overrides.clear()


# =============================================================================
# 9. MISSING AUTHENTICATION REJECTION (401)
# =============================================================================

def test_missing_authentication_rejection(client: TestClient):
    """9. Test that all progress endpoints reject requests without an Authorization header with 401."""
    res_sum = client.get("/api/v1/progress/summary")
    assert res_sum.status_code == 401

    res_dash = client.get("/api/v1/progress/dashboard")
    assert res_dash.status_code == 401

    res_vol = client.get("/api/v1/progress/volume")
    assert res_vol.status_code == 401

    res_ex = client.get("/api/v1/progress/exercises/ex_bench_press")
    assert res_ex.status_code == 401


# =============================================================================
# 10. INVALID FIREBASE TOKEN REJECTION (401)
# =============================================================================

def test_invalid_firebase_token_rejection(client: TestClient):
    """10. Test that requests with forged or invalid Firebase ID tokens are rejected with 401."""
    with patch("backend.app.core.security.auth.verify_id_token", side_effect=Exception("Invalid auth token")):
        headers = {"Authorization": "Bearer forged_fake_token_12345"}

        assert client.get("/api/v1/progress/summary", headers=headers).status_code == 401
        assert client.get("/api/v1/progress/dashboard", headers=headers).status_code == 401
        assert client.get("/api/v1/progress/volume", headers=headers).status_code == 401
        assert client.get("/api/v1/progress/exercises/ex_bench_press", headers=headers).status_code == 401


# =============================================================================
# 11. CROSS-USER PROGRESS ISOLATION
# =============================================================================

def test_cross_user_progress_isolation(
    client: TestClient,
    mock_wkt_repo: WorkoutRepository,
    mock_ex_repo: ExerciseRepository,
    mock_user_repo: UserRepository,
):
    """11. Test that User B cannot see User A's progress metrics or volume."""
    user_a = CurrentUser(uid="user_a_active", email="usera@pulseai.fit", name="Alice", email_verified=True)
    user_b = CurrentUser(uid="user_b_idle", email="userb@pulseai.fit", name="Bob", email_verified=True)

    # 1. User A logs a completed workout
    app.dependency_overrides[get_current_user] = lambda: user_a
    app.dependency_overrides[get_workout_repository] = lambda: mock_wkt_repo
    app.dependency_overrides[get_exercise_repository] = lambda: mock_ex_repo
    app.dependency_overrides[get_user_repository] = lambda: mock_user_repo

    s_a = client.post("/api/v1/workouts/wkt_upper_push/sessions").json()["id"]
    client.patch(
        f"/api/v1/workouts/sessions/{s_a}",
        json={
            "elapsedSeconds": 300,
            "recordedSet": {"exerciseId": "ex_bench_press", "setNumber": 1, "actualReps": 10, "actualWeightKg": 100.0},
        },
    )
    client.post(f"/api/v1/workouts/sessions/{s_a}/complete", json={"durationSeconds": 1800})
    app.dependency_overrides.clear()

    # 2. User B logs in and queries progress
    app.dependency_overrides[get_current_user] = lambda: user_b
    app.dependency_overrides[get_workout_repository] = lambda: mock_wkt_repo
    app.dependency_overrides[get_exercise_repository] = lambda: mock_ex_repo
    app.dependency_overrides[get_user_repository] = lambda: mock_user_repo

    try:
        summary_b = client.get("/api/v1/progress/summary").json()
        assert summary_b["totalWorkouts"] == 0
        assert summary_b["totalVolumeKg"] == 0.0

        dash_b = client.get("/api/v1/progress/dashboard").json()
        assert len(dash_b["personalRecords"]) == 0
        assert len(dash_b["recentWorkouts"]) == 0
    finally:
        app.dependency_overrides.clear()


# =============================================================================
# 12. CROSS-USER HISTORY ISOLATION
# =============================================================================

def test_cross_user_history_isolation(
    client: TestClient,
    mock_wkt_repo: WorkoutRepository,
):
    """12. Test that completed workouts in User A's history are never visible in User B's history."""
    user_a = CurrentUser(uid="user_a_history", email="usera2@pulseai.fit", name="Alice2", email_verified=True)
    user_b = CurrentUser(uid="user_b_history", email="userb2@pulseai.fit", name="Bob2", email_verified=True)

    app.dependency_overrides[get_current_user] = lambda: user_a
    app.dependency_overrides[get_workout_repository] = lambda: mock_wkt_repo
    s_a = client.post("/api/v1/workouts/wkt_upper_push/sessions").json()["id"]
    client.post(f"/api/v1/workouts/sessions/{s_a}/complete", json={"durationSeconds": 1500})
    app.dependency_overrides.clear()

    # User B requests history
    app.dependency_overrides[get_current_user] = lambda: user_b
    app.dependency_overrides[get_workout_repository] = lambda: mock_wkt_repo

    try:
        history_b = client.get("/api/v1/workouts/history").json()
        assert len(history_b) == 0
    finally:
        app.dependency_overrides.clear()


# =============================================================================
# 13. COMPLETED WORKOUT APPEARS IN PROGRESS AND HISTORY
# =============================================================================

def test_completed_workout_appears_in_progress(
    client: TestClient,
    mock_wkt_repo: WorkoutRepository,
    mock_ex_repo: ExerciseRepository,
    mock_user_repo: UserRepository,
):
    """13. Test that completing a workout session immediately causes it to appear in progress & history."""
    user = CurrentUser(uid="user_lifecycle", email="life@pulseai.fit", name="Lifecycle User", email_verified=True)
    app.dependency_overrides[get_current_user] = lambda: user
    app.dependency_overrides[get_workout_repository] = lambda: mock_wkt_repo
    app.dependency_overrides[get_exercise_repository] = lambda: mock_ex_repo
    app.dependency_overrides[get_user_repository] = lambda: mock_user_repo

    try:
        # Before completion
        assert client.get("/api/v1/progress/summary").json()["totalWorkouts"] == 0
        assert len(client.get("/api/v1/workouts/history").json()) == 0

        # Start and complete
        s = client.post("/api/v1/workouts/wkt_upper_push/sessions").json()["id"]
        client.post(f"/api/v1/workouts/sessions/{s}/complete", json={"durationSeconds": 1800})

        # After completion
        assert client.get("/api/v1/progress/summary").json()["totalWorkouts"] == 1
        history = client.get("/api/v1/workouts/history").json()
        assert len(history) == 1
        assert history[0]["id"] == s
    finally:
        app.dependency_overrides.clear()


# =============================================================================
# 14. INCOMPLETE/IN-PROGRESS WORKOUT EXCLUDED FROM PROGRESS & HISTORY
# =============================================================================

def test_in_progress_session_excluded(
    client: TestClient,
    mock_wkt_repo: WorkoutRepository,
    mock_ex_repo: ExerciseRepository,
    mock_user_repo: UserRepository,
):
    """14. Test that active (in-progress) workouts are NOT included in completed history or progress statistics."""
    user = CurrentUser(uid="in_prog_user", email="inprog@pulseai.fit", name="Active Lifter", email_verified=True)
    app.dependency_overrides[get_current_user] = lambda: user
    app.dependency_overrides[get_workout_repository] = lambda: mock_wkt_repo
    app.dependency_overrides[get_exercise_repository] = lambda: mock_ex_repo
    app.dependency_overrides[get_user_repository] = lambda: mock_user_repo

    try:
        # Start session but do NOT complete it
        s = client.post("/api/v1/workouts/wkt_upper_push/sessions").json()["id"]
        client.patch(
            f"/api/v1/workouts/sessions/{s}",
            json={
                "elapsedSeconds": 300,
                "recordedSet": {"exerciseId": "ex_bench_press", "setNumber": 1, "actualReps": 10, "actualWeightKg": 100.0},
            },
        )

        # Active session exists
        active_res = client.get("/api/v1/workouts/sessions/active")
        assert active_res.status_code == 200
        assert active_res.json()["id"] == s

        # But history must be empty (only completed sessions)
        history = client.get("/api/v1/workouts/history").json()
        assert len(history) == 0

        # And progress summary must show 0 completed workouts
        summary = client.get("/api/v1/progress/summary").json()
        assert summary["totalWorkouts"] == 0
        assert summary["totalVolumeKg"] == 0.0
    finally:
        app.dependency_overrides.clear()
