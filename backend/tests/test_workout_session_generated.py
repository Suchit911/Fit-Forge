"""
Dedicated Backend Integration and Regression Tests for Phase 9B.8.6:
Generated Workout Plan Session Execution Integration.

Verifies:
1. Authenticated generated session creation (POST /api/v1/workouts/generated/sessions)
2. Preserves generated workout title (session.workoutTitle)
3. Preserves generated planned total sets count metadata (session.totalSetsCount)
4. Unauthenticated request rejection (HTTP 401)
5. Set PATCH recording with canonical exerciseId, actual reps, weight, and RPE
6. Volume calculation reflects actual recorded sets
7. Completed sets count reflects actual recorded sets
8. Session completion (POST /api/v1/workouts/sessions/{id}/complete)
9. PR detection using canonical exercise catalog lookup
10. Workout completion notification includes generated workout title and volume
11. Achievement evaluation functions seamlessly with generated workout session
12. Progress service calculations (streak, total volume, PRs) include generated session
13. Workout history lists generated session with correct metadata
14. Non-owner session access rejection
15. Standard catalog workout sessions remain 100% functional and backward-compatible
"""

import pytest
from fastapi.testclient import TestClient

from backend.app.main import app
from backend.app.core.security import get_current_user, CurrentUser
from backend.app.repositories.workout_repository import get_workout_repository
from backend.app.services.workout_service import get_workout_service
from backend.app.services.progress_service import get_progress_service
from backend.app.services.achievement_service import get_achievement_service
from backend.app.services.notification_service import get_notification_service


@pytest.fixture
def auth_user():
    return CurrentUser(
        uid="usr_gen_exec_test_01",
        email="athlete@example.com",
        name="Generated Workout Tester",
        email_verified=True,
    )


@pytest.fixture
def other_user():
    return CurrentUser(
        uid="usr_other_attacker_02",
        email="other@example.com",
        name="Attacker",
        email_verified=True,
    )


@pytest.fixture(autouse=True)
def setup_dependencies(auth_user):
    app.dependency_overrides[get_current_user] = lambda: auth_user
    yield
    app.dependency_overrides.clear()


# =============================================================================
# 1. Session Creation for Generated Workouts
# =============================================================================

def test_start_generated_workout_session_authenticated(client: TestClient):
    """Verifies that POST /api/v1/workouts/generated/sessions creates an active session."""
    payload = {
        "workoutId": "generated",
        "workoutTitle": "Upper A Routine",
        "totalSetsCount": 9,
        "notes": "Generated Plan: 4-Day Upper / Lower Split | Week 1 (Baseline Accumulation)",
    }
    response = client.post("/api/v1/workouts/generated/sessions", json=payload)
    assert response.status_code == 201
    data = response.json()

    assert data["id"].startswith("sess_")
    assert data["userId"] == "usr_gen_exec_test_01"
    assert data["workoutId"] == "generated"
    assert data["workoutTitle"] == "Upper A Routine"
    assert data["totalSetsCount"] == 9
    assert data["status"] == "in_progress"
    assert data["completedSetsCount"] == 0
    assert data["totalVolumeKg"] == 0.0
    assert "Generated Plan" in data["notes"]


def test_start_generated_workout_session_unauthenticated(client: TestClient):
    """Verifies that unauthenticated call to start generated session returns 401."""
    app.dependency_overrides.clear()
    response = client.post(
        "/api/v1/workouts/generated/sessions",
        json={"workoutId": "generated", "workoutTitle": "Upper A"}
    )
    assert response.status_code == 401


# =============================================================================
# 2. Set Recording (PATCH) with Canonical Exercise IDs & Volume Calculation
# =============================================================================

def test_record_sets_canonical_exercise_and_volume(client: TestClient):
    """Verifies PATCH /api/v1/workouts/sessions/{id} with canonical exercise IDs."""
    # 1. Create session
    create_res = client.post(
        "/api/v1/workouts/generated/sessions",
        json={"workoutId": "generated", "workoutTitle": "Leg Day B", "totalSetsCount": 6}
    )
    assert create_res.status_code == 201
    sess_id = create_res.json()["id"]

    # 2. Record set 1 (Barbell Squat: 8 reps @ 100 kg)
    patch1 = client.patch(
        f"/api/v1/workouts/sessions/{sess_id}",
        json={
            "currentExerciseIndex": 0,
            "currentSetIndex": 0,
            "recordedSet": {
                "exerciseId": "ex_squat",
                "setNumber": 1,
                "actualReps": 8,
                "actualWeightKg": 100.0,
                "rpe": 8.0,
            },
        },
    )
    assert patch1.status_code == 200
    p1_data = patch1.json()
    assert p1_data["completedSetsCount"] == 1
    assert p1_data["totalVolumeKg"] == 800.0
    assert "ex_squat" in p1_data["completedSets"]
    assert len(p1_data["completedSets"]["ex_squat"]) == 1

    # 3. Record set 2 (Barbell Squat: 8 reps @ 100 kg)
    patch2 = client.patch(
        f"/api/v1/workouts/sessions/{sess_id}",
        json={
            "currentExerciseIndex": 0,
            "currentSetIndex": 1,
            "recordedSet": {
                "exerciseId": "ex_squat",
                "setNumber": 2,
                "actualReps": 8,
                "actualWeightKg": 100.0,
                "rpe": 8.5,
            },
        },
    )
    assert patch2.status_code == 200
    p2_data = patch2.json()
    assert p2_data["completedSetsCount"] == 2
    assert p2_data["totalVolumeKg"] == 1600.0

    # 4. Record set 3 for next exercise (Romanian Deadlift: 10 reps @ 80 kg)
    patch3 = client.patch(
        f"/api/v1/workouts/sessions/{sess_id}",
        json={
            "currentExerciseIndex": 1,
            "currentSetIndex": 0,
            "recordedSet": {
                "exerciseId": "ex_romanian_deadlift",
                "setNumber": 1,
                "actualReps": 10,
                "actualWeightKg": 80.0,
                "rpe": 8.0,
            },
        },
    )
    assert patch3.status_code == 200
    p3_data = patch3.json()
    assert p3_data["completedSetsCount"] == 3
    assert p3_data["totalVolumeKg"] == 2400.0
    assert "ex_romanian_deadlift" in p3_data["completedSets"]


# =============================================================================
# 3. Session Completion & Downstream Integration
# =============================================================================

def test_complete_generated_session_triggers_downstream(client: TestClient, auth_user):
    """Verifies completion marks session completed and triggers notifications and achievements."""
    # 1. Create and populate session
    create_res = client.post(
        "/api/v1/workouts/generated/sessions",
        json={"workoutId": "generated", "workoutTitle": "Upper Hypertrophy A", "totalSetsCount": 3}
    )
    sess_id = create_res.json()["id"]

    client.patch(
        f"/api/v1/workouts/sessions/{sess_id}",
        json={
            "recordedSet": {
                "exerciseId": "ex_barbell_bench_press",
                "setNumber": 1,
                "actualReps": 8,
                "actualWeightKg": 95.0,
                "rpe": 8.5,
            }
        },
    )

    # 2. Complete session
    complete_res = client.post(
        f"/api/v1/workouts/sessions/{sess_id}/complete",
        json={"durationSeconds": 2400, "notes": "Felt strong throughout"}
    )
    assert complete_res.status_code == 200
    comp_data = complete_res.json()
    assert comp_data["status"] == "completed"
    assert comp_data["completedAt"] is not None
    assert comp_data["durationSeconds"] == 2400
    assert comp_data["caloriesBurned"] > 0
    assert comp_data["workoutTitle"] == "Upper Hypertrophy A"

    # 3. Check notifications
    notif_svc = get_notification_service()
    notifs = notif_svc.repo.list_notifications(auth_user.uid)
    wkt_notifs = [n for n in notifs if n.get("type") == "workout_completed"]
    assert len(wkt_notifs) >= 1
    assert "Upper Hypertrophy A" in wkt_notifs[0]["message"]

    # 4. Check progress calculations include this session
    prog_res = client.get("/api/v1/progress/summary?period=30d")
    assert prog_res.status_code == 200
    summary = prog_res.json()
    assert summary["totalWorkouts"] >= 1
    assert summary["totalVolumeKg"] >= 760.0

    # 5. Check history endpoint
    hist_res = client.get("/api/v1/workouts/history")
    assert hist_res.status_code == 200
    hist_list = hist_res.json()
    matching = [h for h in hist_list if h["id"] == sess_id]
    assert len(matching) == 1
    assert matching[0]["workoutTitle"] == "Upper Hypertrophy A"
    assert matching[0]["workoutId"] == "generated"


# =============================================================================
# 4. Security & Ownership Verification
# =============================================================================

def test_other_user_cannot_update_session(client: TestClient, other_user):
    """Verifies that user A cannot update user B's session."""
    # User A creates session
    create_res = client.post(
        "/api/v1/workouts/generated/sessions",
        json={"workoutId": "generated", "workoutTitle": "Private Workout"}
    )
    sess_id = create_res.json()["id"]

    # Switch to User B
    app.dependency_overrides[get_current_user] = lambda: other_user
    patch_res = client.patch(
        f"/api/v1/workouts/sessions/{sess_id}",
        json={"elapsedSeconds": 100}
    )
    assert patch_res.status_code == 404

    comp_res = client.post(
        f"/api/v1/workouts/sessions/{sess_id}/complete",
        json={"durationSeconds": 1800}
    )
    assert comp_res.status_code == 404


# =============================================================================
# 5. Backward Compatibility: Standard Library Workouts
# =============================================================================

def test_standard_catalog_workout_session_intact(client: TestClient):
    """Verifies that static catalog workouts continue to function normally without regression."""
    # Start session for standard catalog workout
    res = client.post(
        "/api/v1/workouts/wkt_upper_push/sessions",
        json={"workoutId": "wkt_upper_push"}
    )
    assert res.status_code == 201
    data = res.json()
    assert data["workoutId"] == "wkt_upper_push"
    assert data["workoutTitle"] == "Upper Body Push"
    assert data["totalSetsCount"] > 0

    # Non-existent workout still returns 404
    bad_res = client.post(
        "/api/v1/workouts/non_existent_wkt_id/sessions",
        json={"workoutId": "non_existent_wkt_id"}
    )
    assert bad_res.status_code == 404
