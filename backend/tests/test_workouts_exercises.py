from unittest.mock import patch
from fastapi.testclient import TestClient
from backend.app.main import app
from backend.app.core.security import CurrentUser, get_current_user
from backend.app.repositories.exercise_repository import ExerciseRepository, get_exercise_repository
from backend.app.repositories.workout_repository import WorkoutRepository, get_workout_repository
import pytest


@pytest.fixture
def mock_ex_repo():
    """Provides an isolated in-memory ExerciseRepository."""
    return ExerciseRepository(db=None)


@pytest.fixture
def mock_wkt_repo():
    """Provides an isolated in-memory WorkoutRepository."""
    return WorkoutRepository(db=None)


# =============================================================================
# 1. EXERCISE LISTING
# =============================================================================

def test_exercise_listing(client: TestClient, mock_ex_repo: ExerciseRepository):
    """1. Test that GET /api/v1/exercises returns reference exercises and supports filtering."""
    app.dependency_overrides[get_exercise_repository] = lambda: mock_ex_repo
    try:
        # All exercises
        res = client.get("/api/v1/exercises")
        assert res.status_code == 200
        exercises = res.json()
        assert len(exercises) >= 8
        assert any(e["id"] == "ex_bench_press" for e in exercises)

        # Filter by muscle (chest)
        res_chest = client.get("/api/v1/exercises?muscle=chest")
        assert res_chest.status_code == 200
        chest_exercises = res_chest.json()
        assert len(chest_exercises) > 0
        for e in chest_exercises:
            assert "chest" in [m.lower() for m in e["primaryMuscles"] + e["secondaryMuscles"]]

        # Search query
        res_search = client.get("/api/v1/exercises?search=bench")
        assert res_search.status_code == 200
        assert any("bench" in e["name"].lower() for e in res_search.json())
    finally:
        app.dependency_overrides.clear()


# =============================================================================
# 2. EXERCISE DETAIL
# =============================================================================

def test_exercise_detail(client: TestClient, mock_ex_repo: ExerciseRepository):
    """2. Test that GET /api/v1/exercises/{id} returns full exercise detail."""
    app.dependency_overrides[get_exercise_repository] = lambda: mock_ex_repo
    try:
        res = client.get("/api/v1/exercises/ex_bench_press")
        assert res.status_code == 200
        data = res.json()
        assert data["id"] == "ex_bench_press"
        assert data["name"] in ("Bench Press", "Barbell Bench Press")
        assert "chest" in data["primaryMuscles"]
        assert len(data["instructions"]) > 0
    finally:
        app.dependency_overrides.clear()


# =============================================================================
# 3. INVALID EXERCISE ID
# =============================================================================

def test_invalid_exercise_id(client: TestClient, mock_ex_repo: ExerciseRepository):
    """3. Test that GET /api/v1/exercises/{invalid} returns 404."""
    app.dependency_overrides[get_exercise_repository] = lambda: mock_ex_repo
    try:
        res = client.get("/api/v1/exercises/ex_does_not_exist_999")
        assert res.status_code == 404
        assert "not found" in res.json()["detail"].lower()
    finally:
        app.dependency_overrides.clear()


# =============================================================================
# 4. WORKOUT LISTING
# =============================================================================

def test_workout_listing(client: TestClient, mock_wkt_repo: WorkoutRepository):
    """4. Test that GET /api/v1/workouts returns curated workout routines."""
    app.dependency_overrides[get_workout_repository] = lambda: mock_wkt_repo
    try:
        res = client.get("/api/v1/workouts")
        assert res.status_code == 200
        workouts = res.json()
        assert len(workouts) >= 4
        assert any(w["id"] == "wkt_upper_push" for w in workouts)

        # Today's workout
        res_today = client.get("/api/v1/workouts/today")
        assert res_today.status_code == 200
        assert res_today.json()["id"] == "wkt_upper_push"
    finally:
        app.dependency_overrides.clear()


# =============================================================================
# 5. WORKOUT DETAIL
# =============================================================================

def test_workout_detail(client: TestClient, mock_wkt_repo: WorkoutRepository):
    """5. Test that GET /api/v1/workouts/{id} returns exercises and target sets."""
    app.dependency_overrides[get_workout_repository] = lambda: mock_wkt_repo
    try:
        res = client.get("/api/v1/workouts/wkt_upper_push")
        assert res.status_code == 200
        data = res.json()
        assert data["id"] == "wkt_upper_push"
        assert len(data["exercises"]) > 0
        first_ex = data["exercises"][0]
        assert "exercise" in first_ex
        assert len(first_ex["sets"]) > 0
    finally:
        app.dependency_overrides.clear()


# =============================================================================
# 6. MISSING AUTHENTICATION
# =============================================================================

def test_missing_authentication(client: TestClient):
    """6. Test that session operations without Authorization header return 401."""
    res_start = client.post("/api/v1/workouts/wkt_upper_push/sessions")
    assert res_start.status_code == 401
    assert "Missing Bearer authentication token" in res_start.json()["detail"]

    res_active = client.get("/api/v1/workouts/sessions/active")
    assert res_active.status_code == 401

    res_history = client.get("/api/v1/workouts/history")
    assert res_history.status_code == 401


# =============================================================================
# 7. INVALID FIREBASE TOKEN
# =============================================================================

def test_invalid_firebase_token(client: TestClient):
    """7. Test that session operations with invalid token return 401."""
    with patch("backend.app.core.security.auth.verify_id_token", side_effect=Exception("Invalid token signature")):
        res = client.post(
            "/api/v1/workouts/wkt_upper_push/sessions",
            headers={"Authorization": "Bearer invalid_signature_token"},
        )
        assert res.status_code == 401
        assert "Could not validate credentials." in res.json()["detail"]


# =============================================================================
# 8. USER WORKOUT SESSION CREATION
# =============================================================================

def test_user_workout_session_creation(client: TestClient, mock_wkt_repo: WorkoutRepository):
    """8. Test authenticated user starting a workout session."""
    user = CurrentUser(uid="athlete_007", email="athlete@pulseai.fit", name="James Bond", email_verified=True)
    app.dependency_overrides[get_current_user] = lambda: user
    app.dependency_overrides[get_workout_repository] = lambda: mock_wkt_repo

    try:
        res = client.post("/api/v1/workouts/wkt_upper_push/sessions", json={"notes": "Chest focus session"})
        assert res.status_code == 201
        data = res.json()
        assert data["userId"] == "athlete_007"
        assert data["workoutId"] == "wkt_upper_push"
        assert data["status"] == "in_progress"
        assert data["notes"] == "Chest focus session"
        assert data["id"].startswith("sess_")
    finally:
        app.dependency_overrides.clear()


# =============================================================================
# 9. USER WORKOUT SESSION RETRIEVAL
# =============================================================================

def test_user_workout_session_retrieval(client: TestClient, mock_wkt_repo: WorkoutRepository):
    """9. Test active session retrieval and specific session detail."""
    user = CurrentUser(uid="athlete_008_retrieval", email="athlete8@pulseai.fit", name="Serena", email_verified=True)
    app.dependency_overrides[get_current_user] = lambda: user
    app.dependency_overrides[get_workout_repository] = lambda: mock_wkt_repo

    try:
        # 1. Start a session
        create_res = client.post("/api/v1/workouts/wkt_lower_strength/sessions")
        session_id = create_res.json()["id"]

        # 2. Get active session
        active_res = client.get("/api/v1/workouts/sessions/active")
        assert active_res.status_code == 200
        assert active_res.json()["id"] == session_id
        assert active_res.json()["workoutTitle"] == "Lower Body Strength"

        # 3. Get specific session by ID
        detail_res = client.get(f"/api/v1/workouts/sessions/{session_id}")
        assert detail_res.status_code == 200
        assert detail_res.json()["id"] == session_id
    finally:
        app.dependency_overrides.clear()


# =============================================================================
# 10. USER WORKOUT COMPLETION & METRICS
# =============================================================================

def test_user_workout_completion(client: TestClient, mock_wkt_repo: WorkoutRepository):
    """10. Test recording sets, tracking volume, and completing a workout session."""
    user = CurrentUser(uid="athlete_009", email="athlete9@pulseai.fit", name="Olympian", email_verified=True)
    app.dependency_overrides[get_current_user] = lambda: user
    app.dependency_overrides[get_workout_repository] = lambda: mock_wkt_repo

    try:
        # 1. Start session
        session_id = client.post("/api/v1/workouts/wkt_upper_push/sessions").json()["id"]

        # 2. Record set 1: Bench Press, 10 reps @ 60kg (Volume: 600kg)
        patch1 = {
            "elapsedSeconds": 300,
            "recordedSet": {
                "exerciseId": "ex_bench_press",
                "setNumber": 1,
                "actualReps": 10,
                "actualWeightKg": 60.0,
                "rpe": 8.0,
            },
        }
        res_p1 = client.patch(f"/api/v1/workouts/sessions/{session_id}", json=patch1)
        assert res_p1.status_code == 200
        assert res_p1.json()["totalVolumeKg"] == 600.0
        assert res_p1.json()["completedSetsCount"] == 1

        # 3. Record set 2: Bench Press, 10 reps @ 70kg (Volume: +700kg = 1300kg)
        patch2 = {
            "elapsedSeconds": 600,
            "recordedSet": {
                "exerciseId": "ex_bench_press",
                "setNumber": 2,
                "actualReps": 10,
                "actualWeightKg": 70.0,
                "rpe": 8.5,
            },
        }
        res_p2 = client.patch(f"/api/v1/workouts/sessions/{session_id}", json=patch2)
        assert res_p2.status_code == 200
        assert res_p2.json()["totalVolumeKg"] == 1300.0
        assert res_p2.json()["completedSetsCount"] == 2

        # 4. Complete session (duration 45 mins = 2700s)
        complete_payload = {"durationSeconds": 2700, "notes": "Felt strong throughout"}
        complete_res = client.post(f"/api/v1/workouts/sessions/{session_id}/complete", json=complete_payload)
        assert complete_res.status_code == 200
        comp_data = complete_res.json()
        assert comp_data["status"] == "completed"
        assert comp_data["completedAt"] is not None
        assert comp_data["totalVolumeKg"] == 1300.0
        # Calories burned: ~338 kcal (45 * 7.5)
        assert comp_data["caloriesBurned"] > 300

        # 5. Verify it appears in user's history
        history_res = client.get("/api/v1/workouts/history")
        assert history_res.status_code == 200
        history = history_res.json()
        assert len(history) == 1
        assert history[0]["id"] == session_id
    finally:
        app.dependency_overrides.clear()


# =============================================================================
# 11. CROSS-USER WORKOUT/SESSION ACCESS PROTECTION
# =============================================================================

def test_cross_user_session_access_protection(client: TestClient, mock_wkt_repo: WorkoutRepository):
    """
    11. Verify that User B cannot view or modify User A's workout session,
    and User B's history contains strictly User B's sessions.
    """
    user_a = CurrentUser(uid="user_a_victim", email="victim@pulseai.fit", name="Alice", email_verified=True)
    user_b = CurrentUser(uid="user_b_attacker", email="attacker@pulseai.fit", name="Bob", email_verified=True)

    # 1. User A creates and completes a workout session
    app.dependency_overrides[get_current_user] = lambda: user_a
    app.dependency_overrides[get_workout_repository] = lambda: mock_wkt_repo
    user_a_session_id = client.post("/api/v1/workouts/wkt_upper_push/sessions").json()["id"]
    client.post(f"/api/v1/workouts/sessions/{user_a_session_id}/complete", json={"durationSeconds": 1800})
    app.dependency_overrides.clear()

    # 2. User B logs in and attempts to access User A's session
    app.dependency_overrides[get_current_user] = lambda: user_b
    app.dependency_overrides[get_workout_repository] = lambda: mock_wkt_repo

    try:
        # GET User A's session -> must return 404 (Not Found / No Permission)
        get_res = client.get(f"/api/v1/workouts/sessions/{user_a_session_id}")
        assert get_res.status_code == 404

        # PATCH User A's session -> must return 404
        patch_res = client.patch(
            f"/api/v1/workouts/sessions/{user_a_session_id}",
            json={"notes": "Malicious tampering attempt"},
        )
        assert patch_res.status_code == 404

        # User B's history must NOT show User A's session
        history_res = client.get("/api/v1/workouts/history")
        assert history_res.status_code == 200
        assert len(history_res.json()) == 0
    finally:
        app.dependency_overrides.clear()
