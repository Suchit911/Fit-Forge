import pytest
from datetime import datetime, timezone
from fastapi.testclient import TestClient
from backend.app.main import app
from backend.app.core.security import get_current_user, CurrentUser
from backend.app.repositories.achievement_repository import (
    AchievementRepository,
    get_achievement_repository,
)
from backend.app.repositories.workout_repository import (
    WorkoutRepository,
    get_workout_repository,
)
from backend.app.repositories.exercise_repository import (
    ExerciseRepository,
    get_exercise_repository,
)
from backend.app.repositories.nutrition_repository import (
    NutritionRepository,
    get_nutrition_repository,
)
from backend.app.repositories.user_repository import (
    UserRepository,
    get_user_repository,
)
from backend.app.services.progress_service import ProgressService
from backend.app.services.achievement_service import AchievementService, get_achievement_service


@pytest.fixture
def mock_ach_repo() -> AchievementRepository:
    return AchievementRepository(db=None)


@pytest.fixture
def mock_workout_repo() -> WorkoutRepository:
    return WorkoutRepository(db=None)


@pytest.fixture
def mock_exercise_repo() -> ExerciseRepository:
    return ExerciseRepository(db=None)


@pytest.fixture
def mock_nutrition_repo() -> NutritionRepository:
    return NutritionRepository(db=None)


@pytest.fixture
def mock_user_repo() -> UserRepository:
    return UserRepository(db=None)


@pytest.fixture
def achievement_service(
    mock_ach_repo: AchievementRepository,
    mock_workout_repo: WorkoutRepository,
    mock_nutrition_repo: NutritionRepository,
    mock_user_repo: UserRepository,
    mock_exercise_repo: ExerciseRepository,
) -> AchievementService:
    prog_service = ProgressService(
        workout_repo=mock_workout_repo,
        exercise_repo=mock_exercise_repo,
        user_repo=mock_user_repo,
    )
    return AchievementService(
        achievement_repo=mock_ach_repo,
        workout_repo=mock_workout_repo,
        nutrition_repo=mock_nutrition_repo,
        user_repo=mock_user_repo,
        progress_service=prog_service,
    )


# =============================================================================
# 1. AUTHENTICATION ENFORCEMENT & SECURITY
# =============================================================================

def test_achievements_missing_auth_header_rejected(client: TestClient):
    """1. Test that requests without Authorization header return 401."""
    res = client.get("/api/v1/achievements")
    assert res.status_code == 401


def test_achievements_invalid_token_rejected(client: TestClient):
    """2. Test that malformed or forged tokens return 401."""
    res = client.get(
        "/api/v1/achievements",
        headers={"Authorization": "Bearer invalid_fake_token_value"},
    )
    assert res.status_code == 401


def test_cross_user_isolation(
    client: TestClient,
    mock_ach_repo: AchievementRepository,
    mock_workout_repo: WorkoutRepository,
    mock_nutrition_repo: NutritionRepository,
    mock_user_repo: UserRepository,
):
    """3. Test that User A cannot access or mutate User B's achievements."""
    user_a = CurrentUser(uid="user_ach_a", email="a@pulseai.fit", name="User A", email_verified=True)
    user_b = CurrentUser(uid="user_ach_b", email="b@pulseai.fit", name="User B", email_verified=True)

    # User B unlocks an achievement by logging custom milestone
    mock_ach_repo.create_custom_achievement(user_b.uid, "User B Milestone", "Private")

    # Set auth to User A
    app.dependency_overrides[get_current_user] = lambda: user_a
    app.dependency_overrides[get_achievement_repository] = lambda: mock_ach_repo
    app.dependency_overrides[get_workout_repository] = lambda: mock_workout_repo
    app.dependency_overrides[get_nutrition_repository] = lambda: mock_nutrition_repo
    app.dependency_overrides[get_user_repository] = lambda: mock_user_repo

    try:
        res = client.get("/api/v1/achievements")
        assert res.status_code == 200
        data = res.json()
        # User A should have 0 achievements
        assert data["progressSummary"]["achievedCount"] == 0
        assert data["kpis"][0]["value"] == "0"
        assert len(data["recentAchievements"]) == 0
    finally:
        app.dependency_overrides.clear()


# =============================================================================
# 2. EMPTY USER STATE & INITIAL DASHBOARD
# =============================================================================

def test_achievements_empty_user_state(
    client: TestClient,
    mock_ach_repo: AchievementRepository,
    mock_workout_repo: WorkoutRepository,
    mock_nutrition_repo: NutritionRepository,
    mock_user_repo: UserRepository,
):
    """4. Test that a user with zero workouts returns a clean zero state with Level 10."""
    user = CurrentUser(uid="fresh_ach_user", email="fresh@pulseai.fit", name="Fresh User", email_verified=True)
    app.dependency_overrides[get_current_user] = lambda: user
    app.dependency_overrides[get_achievement_repository] = lambda: mock_ach_repo
    app.dependency_overrides[get_workout_repository] = lambda: mock_workout_repo
    app.dependency_overrides[get_nutrition_repository] = lambda: mock_nutrition_repo
    app.dependency_overrides[get_user_repository] = lambda: mock_user_repo

    try:
        res = client.get("/api/v1/achievements")
        assert res.status_code == 200
        data = res.json()

        # KPIs
        assert data["kpis"][0]["value"] == "0"  # 0 achievements
        assert data["kpis"][1]["value"] == "0"  # 0 points
        assert "0 Day" in data["kpis"][2]["value"]  # 0 streak

        # Progress summary
        assert data["progressSummary"]["overallPct"] == 0
        assert data["progressSummary"]["achievedCount"] == 0
        assert data["progressSummary"]["nextMilestone"]["currentLevel"] == 1
        assert data["progressSummary"]["nextMilestone"]["level"] == 10
        assert data["progressSummary"]["nextMilestone"]["targetPts"] == 1000
        assert data["progressSummary"]["nextMilestone"]["ptsToGo"] == 1000

        # No fabricated challenges or fake users
        assert data["currentChallenges"] == []
        assert data["leaderboard"] == []
        assert data["recentAchievements"] == []
    finally:
        app.dependency_overrides.clear()


# =============================================================================
# 3. WORKOUT MILESTONES (1, 5, 10 WORKOUTS)
# =============================================================================

def test_first_workout_and_count_milestones(
    client: TestClient,
    mock_ach_repo: AchievementRepository,
    mock_workout_repo: WorkoutRepository,
    mock_nutrition_repo: NutritionRepository,
    mock_user_repo: UserRepository,
):
    """5. Test that completing 1, 5, and 10 workouts unlocks first_workout, workouts_5, and workouts_10."""
    user = CurrentUser(uid="workout_milestone_user", email="m@pulseai.fit", name="Milestone User", email_verified=True)
    app.dependency_overrides[get_current_user] = lambda: user
    app.dependency_overrides[get_achievement_repository] = lambda: mock_ach_repo
    app.dependency_overrides[get_workout_repository] = lambda: mock_workout_repo
    app.dependency_overrides[get_nutrition_repository] = lambda: mock_nutrition_repo
    app.dependency_overrides[get_user_repository] = lambda: mock_user_repo

    try:
        # 1 completed workout
        session_1 = {
            "id": "s_1",
            "userId": user.uid,
            "workoutId": "w_push",
            "workoutTitle": "Push Day",
            "status": "completed",
            "startedAt": "2026-09-01T10:00:00Z",
            "completedAt": "2026-09-01T11:00:00Z",
            "durationSeconds": 3600,
            "caloriesBurned": 0,
            "totalVolumeKg": 0.0,
            "completedSets": {},
        }
        mock_workout_repo._in_memory_sessions[f"{user.uid}:s_1"] = session_1

        res1 = client.get("/api/v1/achievements")
        assert res1.status_code == 200
        data1 = res1.json()

        assert data1["progressSummary"]["achievedCount"] == 1
        assert data1["kpis"][1]["value"] == "100"  # 100 points for first_workout
        recent_titles = [b["title"] for b in data1["recentAchievements"]]
        assert "First Step" in recent_titles

        # Add 4 more completed workouts (total 5)
        for i in range(2, 6):
            mock_workout_repo._in_memory_sessions[f"{user.uid}:s_{i}"] = {
                **session_1,
                "id": f"s_{i}",
            }

        res5 = client.get("/api/v1/achievements")
        data5 = res5.json()
        assert data5["progressSummary"]["achievedCount"] == 2  # first_workout + workouts_5
        assert data5["kpis"][1]["value"] == "350"  # 100 + 250

        # Add 5 more completed workouts (total 10)
        for i in range(6, 11):
            mock_workout_repo._in_memory_sessions[f"{user.uid}:s_{i}"] = {
                **session_1,
                "id": f"s_{i}",
            }

        res10 = client.get("/api/v1/achievements")
        data10 = res10.json()
        assert data10["progressSummary"]["achievedCount"] == 3  # first_workout + workouts_5 + workouts_10
        assert data10["kpis"][1]["value"] == "850"  # 100 + 250 + 500
    finally:
        app.dependency_overrides.clear()


# =============================================================================
# 4. STREAK ACHIEVEMENTS
# =============================================================================

def test_streak_achievement_unlock(
    client: TestClient,
    mock_ach_repo: AchievementRepository,
    mock_workout_repo: WorkoutRepository,
    mock_nutrition_repo: NutritionRepository,
    mock_user_repo: UserRepository,
):
    """6. Test that maintaining consecutive workout days unlocks streak milestones."""
    user = CurrentUser(uid="streak_ach_user", email="streak@pulseai.fit", name="Streak User", email_verified=True)
    app.dependency_overrides[get_current_user] = lambda: user
    app.dependency_overrides[get_achievement_repository] = lambda: mock_ach_repo
    app.dependency_overrides[get_workout_repository] = lambda: mock_workout_repo
    app.dependency_overrides[get_nutrition_repository] = lambda: mock_nutrition_repo
    app.dependency_overrides[get_user_repository] = lambda: mock_user_repo

    try:
        # Create consecutive daily workouts for today and past 2 days (3-day streak)
        today = datetime.now(timezone.utc).strftime("%Y-%m-%d")
        d_yesterday = (datetime.now(timezone.utc).replace(hour=10) - (datetime.now(timezone.utc) - datetime.now(timezone.utc))).strftime("%Y-%m-%d")

        dates = ["2026-09-03", "2026-09-04", "2026-09-05"]
        for idx, d_str in enumerate(dates):
            mock_workout_repo._in_memory_sessions[f"{user.uid}:st_{idx}"] = {
                "id": f"st_{idx}",
                "userId": user.uid,
                "workoutId": "w_hiit",
                "workoutTitle": "HIIT",
                "status": "completed",
                "startedAt": f"{d_str}T10:00:00Z",
                "completedAt": f"{d_str}T10:30:00Z",
                "durationSeconds": 1800,
                "caloriesBurned": 300,
                "totalVolumeKg": 500.0,
                "exercises": [],
            }

        res = client.get("/api/v1/achievements")
        assert res.status_code == 200
        data = res.json()
        assert data["progressSummary"]["achievedCount"] >= 1
    finally:
        app.dependency_overrides.clear()


# =============================================================================
# 5. VOLUME & PR THRESHOLDS
# =============================================================================

def test_volume_and_pr_achievement_unlock(
    client: TestClient,
    mock_ach_repo: AchievementRepository,
    mock_workout_repo: WorkoutRepository,
    mock_nutrition_repo: NutritionRepository,
    mock_user_repo: UserRepository,
):
    """7. Test that lifting 5,000 kg volume and recording a PR unlocks respective badges."""
    user = CurrentUser(uid="heavy_user", email="heavy@pulseai.fit", name="Heavy Lifter", email_verified=True)
    app.dependency_overrides[get_current_user] = lambda: user
    app.dependency_overrides[get_achievement_repository] = lambda: mock_ach_repo
    app.dependency_overrides[get_workout_repository] = lambda: mock_workout_repo
    app.dependency_overrides[get_nutrition_repository] = lambda: mock_nutrition_repo
    app.dependency_overrides[get_user_repository] = lambda: mock_user_repo

    try:
        # Session with 6,000 kg volume and a recorded exercise PR set
        session = {
            "id": "s_heavy",
            "userId": user.uid,
            "workoutId": "w_deadlift",
            "workoutTitle": "Heavy Deadlift Day",
            "status": "completed",
            "startedAt": "2026-09-05T14:00:00Z",
            "completedAt": "2026-09-05T15:00:00Z",
            "durationSeconds": 3600,
            "caloriesBurned": 500,
            "totalVolumeKg": 6000.0,  # >= 5000 kg threshold for volume_5k
            "completedSets": {
                "ex_deadlift": [
                    {"setNumber": 1, "targetReps": 5, "targetWeightKg": 180.0, "actualReps": 5, "actualWeightKg": 180.0, "completed": True}
                ]
            },
        }
        mock_workout_repo._in_memory_sessions[f"{user.uid}:s_heavy"] = session

        res = client.get("/api/v1/achievements")
        assert res.status_code == 200
        data = res.json()

        # Should unlock first_workout (100 pts), volume_5k (200 pts), and first_pr (200 pts) = 500 pts
        assert data["progressSummary"]["achievedCount"] >= 3
        recent_titles = [b["title"] for b in data["recentAchievements"]]
        assert "First Step" in recent_titles
        assert "Weight Lifter" in recent_titles
        assert "Breaking Barriers" in recent_titles
    finally:
        app.dependency_overrides.clear()


# =============================================================================
# 6. NUTRITION & HYDRATION THRESHOLDS
# =============================================================================

def test_nutrition_and_hydration_achievement_unlock(
    client: TestClient,
    mock_ach_repo: AchievementRepository,
    mock_workout_repo: WorkoutRepository,
    mock_nutrition_repo: NutritionRepository,
    mock_user_repo: UserRepository,
):
    """8. Test that logging nutrition and hitting water targets unlocks nutrition achievements."""
    user = CurrentUser(uid="nutrition_ach_user", email="nut@pulseai.fit", name="Nutrition User", email_verified=True)
    app.dependency_overrides[get_current_user] = lambda: user
    app.dependency_overrides[get_achievement_repository] = lambda: mock_ach_repo
    app.dependency_overrides[get_workout_repository] = lambda: mock_workout_repo
    app.dependency_overrides[get_nutrition_repository] = lambda: mock_nutrition_repo
    app.dependency_overrides[get_user_repository] = lambda: mock_user_repo

    try:
        # Log a daily nutrition document with meals and water goal reached
        mock_nutrition_repo.save_daily_log(
            uid=user.uid,
            date="2026-09-05",
            data={
                "date": "2026-09-05",
                "userId": user.uid,
                "consumedCalories": 2100,
                "targetCalories": 2400,
                "consumedProteinGrams": 150.0,
                "targetProteinGrams": 160.0,
                "consumedCarbsGrams": 200.0,
                "targetCarbsGrams": 220.0,
                "consumedFatGrams": 65.0,
                "targetFatGrams": 70.0,
                "waterIntakeLiters": 3.2,
                "waterTargetLiters": 3.0,
                "meals": [
                    {
                        "id": "m1",
                        "time": "12:30",
                        "type": "lunch",
                        "name": "Lunch",
                        "totalCalories": 500,
                        "totalProteinGrams": 40.0,
                        "totalCarbsGrams": 50.0,
                        "totalFatGrams": 15.0,
                        "foods": [],
                    }
                ],
            },
        )

        res = client.get("/api/v1/achievements")
        assert res.status_code == 200
        data = res.json()

        recent_titles = [b["title"] for b in data["recentAchievements"]]
        assert "Fuel Aware" in recent_titles
        assert "Hydrated" in recent_titles
    finally:
        app.dependency_overrides.clear()


# =============================================================================
# 7. EARLY WORKOUT THRESHOLD
# =============================================================================

def test_early_workout_achievement_unlock(
    client: TestClient,
    mock_ach_repo: AchievementRepository,
    mock_workout_repo: WorkoutRepository,
    mock_nutrition_repo: NutritionRepository,
    mock_user_repo: UserRepository,
):
    """9. Test that a workout started before 7:00 AM unlocks the Early Riser badge."""
    user = CurrentUser(uid="early_bird_user", email="early@pulseai.fit", name="Early User", email_verified=True)
    app.dependency_overrides[get_current_user] = lambda: user
    app.dependency_overrides[get_achievement_repository] = lambda: mock_ach_repo
    app.dependency_overrides[get_workout_repository] = lambda: mock_workout_repo
    app.dependency_overrides[get_nutrition_repository] = lambda: mock_nutrition_repo
    app.dependency_overrides[get_user_repository] = lambda: mock_user_repo

    try:
        # Workout started at 6:15 AM
        mock_workout_repo._in_memory_sessions[f"{user.uid}:s_early"] = {
            "id": "s_early",
            "userId": user.uid,
            "workoutId": "w_cardio",
            "workoutTitle": "Morning Run",
            "status": "completed",
            "startedAt": "2026-09-05T06:15:00Z",
            "completedAt": "2026-09-05T07:00:00Z",
            "durationSeconds": 2700,
            "caloriesBurned": 350,
            "totalVolumeKg": 0.0,
            "exercises": [],
        }

        res = client.get("/api/v1/achievements")
        assert res.status_code == 200
        data = res.json()

        recent_titles = [b["title"] for b in data["recentAchievements"]]
        assert "Early Riser" in recent_titles
    finally:
        app.dependency_overrides.clear()


# =============================================================================
# 8. REPEATED EVALUATION IDEMPOTENCY & TIMESTAMP PRESERVATION
# =============================================================================

def test_repeated_evaluation_idempotency(
    client: TestClient,
    mock_ach_repo: AchievementRepository,
    mock_workout_repo: WorkoutRepository,
    mock_nutrition_repo: NutritionRepository,
    mock_user_repo: UserRepository,
):
    """10. Test that repeated evaluation calls do not duplicate points or overwrite unlockedAt."""
    user = CurrentUser(uid="idempotent_user", email="idem@pulseai.fit", name="Idem User", email_verified=True)
    app.dependency_overrides[get_current_user] = lambda: user
    app.dependency_overrides[get_achievement_repository] = lambda: mock_ach_repo
    app.dependency_overrides[get_workout_repository] = lambda: mock_workout_repo
    app.dependency_overrides[get_nutrition_repository] = lambda: mock_nutrition_repo
    app.dependency_overrides[get_user_repository] = lambda: mock_user_repo

    try:
        mock_workout_repo._in_memory_sessions[f"{user.uid}:s_1"] = {
            "id": "s_1",
            "userId": user.uid,
            "workoutId": "w_leg",
            "workoutTitle": "Leg Day",
            "status": "completed",
            "startedAt": "2026-09-05T10:00:00Z",
            "completedAt": "2026-09-05T11:00:00Z",
            "durationSeconds": 3600,
            "caloriesBurned": 450,
            "totalVolumeKg": 1500.0,
            "exercises": [],
        }

        res1 = client.get("/api/v1/achievements")
        data1 = res1.json()
        points1 = data1["kpis"][1]["value"]

        ach_state_1 = mock_ach_repo.get_user_achievement(user.uid, "first_workout")
        assert ach_state_1 is not None
        assert ach_state_1.isUnlocked is True
        first_unlocked_at = ach_state_1.unlockedAt

        # Second request
        res2 = client.get("/api/v1/achievements")
        data2 = res2.json()
        points2 = data2["kpis"][1]["value"]

        # Points MUST be identical
        assert points1 == points2

        ach_state_2 = mock_ach_repo.get_user_achievement(user.uid, "first_workout")
        assert ach_state_2.unlockedAt == first_unlocked_at
    finally:
        app.dependency_overrides.clear()


# =============================================================================
# 9. CUSTOM ACHIEVEMENT MILESTONES (AchievementAddModal)
# =============================================================================

def test_custom_achievement_creation(
    client: TestClient,
    mock_ach_repo: AchievementRepository,
    mock_workout_repo: WorkoutRepository,
    mock_nutrition_repo: NutritionRepository,
    mock_user_repo: UserRepository,
):
    """11. Test that creating a custom milestone persists under user-scope and awards 100 points."""
    user = CurrentUser(uid="custom_milestone_user", email="cust@pulseai.fit", name="Custom User", email_verified=True)
    app.dependency_overrides[get_current_user] = lambda: user
    app.dependency_overrides[get_achievement_repository] = lambda: mock_ach_repo
    app.dependency_overrides[get_workout_repository] = lambda: mock_workout_repo
    app.dependency_overrides[get_nutrition_repository] = lambda: mock_nutrition_repo
    app.dependency_overrides[get_user_repository] = lambda: mock_user_repo

    try:
        res = client.post(
            "/api/v1/achievements/custom",
            json={
                "name": "Ran 5km without stopping",
                "description": "Felt great throughout the run.",
                "category": "Endurance",
            },
        )
        assert res.status_code == 201
        data = res.json()

        assert data["progressSummary"]["achievedCount"] == 1
        assert data["kpis"][1]["value"] == "100"  # 100 points
        recent_titles = [b["title"] for b in data["recentAchievements"]]
        assert "Ran 5km without stopping" in recent_titles

        # Confirm it is NOT placed in the global definitions
        global_defs = mock_ach_repo.list_definitions()
        assert not any(d.title == "Ran 5km without stopping" for d in global_defs)
    finally:
        app.dependency_overrides.clear()


# =============================================================================
# 10. CLEAR NEW ACHIEVEMENTS (isNew LIFECYCLE)
# =============================================================================

def test_clear_is_new_lifecycle(
    client: TestClient,
    mock_ach_repo: AchievementRepository,
    mock_workout_repo: WorkoutRepository,
    mock_nutrition_repo: NutritionRepository,
    mock_user_repo: UserRepository,
):
    """12. Test that isNew can be cleared so it does not remain permanently true."""
    user = CurrentUser(uid="is_new_user", email="new@pulseai.fit", name="New User", email_verified=True)
    app.dependency_overrides[get_current_user] = lambda: user
    app.dependency_overrides[get_achievement_repository] = lambda: mock_ach_repo
    app.dependency_overrides[get_workout_repository] = lambda: mock_workout_repo
    app.dependency_overrides[get_nutrition_repository] = lambda: mock_nutrition_repo
    app.dependency_overrides[get_user_repository] = lambda: mock_user_repo

    try:
        # Create a custom milestone which sets isNew = True
        mock_ach_repo.create_custom_achievement(user.uid, "Milestone 1", "Desc")
        ach = mock_ach_repo.list_user_achievements(user.uid)[0]
        assert ach.isNew is True

        # Clear isNew
        res_clear = client.post("/api/v1/achievements/clear-new")
        assert res_clear.status_code == 204

        # Verify isNew is now False
        ach_after = mock_ach_repo.list_user_achievements(user.uid)[0]
        assert ach_after.isNew is False
    finally:
        app.dependency_overrides.clear()


# =============================================================================
# 11. LIST ALL ACHIEVEMENTS WITH FILTER
# =============================================================================

def test_list_all_achievements_with_filter(
    client: TestClient,
    mock_ach_repo: AchievementRepository,
    mock_workout_repo: WorkoutRepository,
    mock_nutrition_repo: NutritionRepository,
    mock_user_repo: UserRepository,
):
    """13. Test GET /api/v1/achievements/list returns full definitions with optional category filtering."""
    user = CurrentUser(uid="filter_user", email="filter@pulseai.fit", name="Filter User", email_verified=True)
    app.dependency_overrides[get_current_user] = lambda: user
    app.dependency_overrides[get_achievement_repository] = lambda: mock_ach_repo
    app.dependency_overrides[get_workout_repository] = lambda: mock_workout_repo
    app.dependency_overrides[get_nutrition_repository] = lambda: mock_nutrition_repo
    app.dependency_overrides[get_user_repository] = lambda: mock_user_repo

    try:
        # All achievements
        res_all = client.get("/api/v1/achievements/list")
        assert res_all.status_code == 200
        items_all = res_all.json()
        assert len(items_all) >= 24

        # Filter by category
        res_strength = client.get("/api/v1/achievements/list?category=Strength")
        assert res_strength.status_code == 200
        items_strength = res_strength.json()
        assert len(items_strength) >= 7
        assert all(i["category"] == "Strength" for i in items_strength)
    finally:
        app.dependency_overrides.clear()


# =============================================================================
# 12. SEED IDEMPOTENCY
# =============================================================================

def test_achievements_seeding_is_idempotent(mock_ach_repo: AchievementRepository):
    """14. Test that calling ensure_seeded multiple times does not corrupt or duplicate items."""
    initial_count = len(mock_ach_repo._in_memory_definitions)
    assert initial_count == 24

    mock_ach_repo.ensure_seeded()
    assert len(mock_ach_repo._in_memory_definitions) == 24


# =============================================================================
# 13. EXACT & BELOW THRESHOLD BEHAVIOR
# =============================================================================

def test_exact_and_below_threshold_behavior(
    client: TestClient,
    mock_ach_repo: AchievementRepository,
    mock_workout_repo: WorkoutRepository,
    mock_nutrition_repo: NutritionRepository,
    mock_user_repo: UserRepository,
):
    """15. Test below threshold (4 workouts -> workouts_5 locked at 80%) vs exact threshold (5 workouts -> unlocked at 100%)."""
    user = CurrentUser(uid="threshold_test_user", email="thresh@pulseai.fit", name="Thresh User", email_verified=True)
    app.dependency_overrides[get_current_user] = lambda: user
    app.dependency_overrides[get_achievement_repository] = lambda: mock_ach_repo
    app.dependency_overrides[get_workout_repository] = lambda: mock_workout_repo
    app.dependency_overrides[get_nutrition_repository] = lambda: mock_nutrition_repo
    app.dependency_overrides[get_user_repository] = lambda: mock_user_repo

    try:
        # Create 4 completed workouts on non-consecutive dates (so streak stays 1)
        dates = ["2026-08-01", "2026-08-05", "2026-08-10", "2026-08-15"]
        for i, dt in enumerate(dates, 1):
            mock_workout_repo._in_memory_sessions[f"{user.uid}:s_{i}"] = {
                "id": f"s_{i}",
                "userId": user.uid,
                "workoutId": f"w_{i}",
                "workoutTitle": f"Workout {i}",
                "status": "completed",
                "startedAt": f"{dt}T12:00:00Z",
                "completedAt": f"{dt}T13:00:00Z",
                "durationSeconds": 3600,
                "caloriesBurned": 50,
                "totalVolumeKg": 500.0,
                "exercises": [],
            }

        res = client.get("/api/v1/achievements")
        data = res.json()
        assert data["progressSummary"]["achievedCount"] == 1  # only first_workout
        ach_w5 = mock_ach_repo.get_user_achievement(user.uid, "workouts_5")
        assert ach_w5 is not None
        assert ach_w5.isUnlocked is False
        assert ach_w5.currentValue == 4.0
        assert ach_w5.progressPercentage == 80.0

        # Now add 5th workout (exact threshold reached)
        mock_workout_repo._in_memory_sessions[f"{user.uid}:s_5"] = {
            "id": "s_5",
            "userId": user.uid,
            "workoutId": "w_5",
            "workoutTitle": "Workout 5",
            "status": "completed",
            "startedAt": "2026-08-20T12:00:00Z",
            "completedAt": "2026-08-20T13:00:00Z",
            "durationSeconds": 3600,
            "caloriesBurned": 50,
            "totalVolumeKg": 500.0,
            "exercises": [],
        }

        res2 = client.get("/api/v1/achievements")
        data2 = res2.json()
        assert data2["progressSummary"]["achievedCount"] == 2  # first_workout and workouts_5
        ach_w5_updated = mock_ach_repo.get_user_achievement(user.uid, "workouts_5")
        assert ach_w5_updated.isUnlocked is True
        assert ach_w5_updated.currentValue == 5.0
        assert ach_w5_updated.progressPercentage == 100.0
    finally:
        app.dependency_overrides.clear()


# =============================================================================
# 14. CATEGORY PROGRESS & NEXT MILESTONE CALCULATION
# =============================================================================

def test_category_progress_and_milestone_calculation(
    client: TestClient,
    mock_ach_repo: AchievementRepository,
    mock_workout_repo: WorkoutRepository,
    mock_nutrition_repo: NutritionRepository,
    mock_user_repo: UserRepository,
):
    """16. Test that category stats match actual definitions and next points milestone is calculated."""
    user = CurrentUser(uid="milestone_cat_user", email="cat@pulseai.fit", name="Cat User", email_verified=True)
    app.dependency_overrides[get_current_user] = lambda: user
    app.dependency_overrides[get_achievement_repository] = lambda: mock_ach_repo
    app.dependency_overrides[get_workout_repository] = lambda: mock_workout_repo
    app.dependency_overrides[get_nutrition_repository] = lambda: mock_nutrition_repo
    app.dependency_overrides[get_user_repository] = lambda: mock_user_repo

    try:
        res = client.get("/api/v1/achievements")
        data = res.json()

        # Check categories
        categories = data["categories"]
        cat_names = [c["title"] for c in categories]
        assert "Workout Mastery" in cat_names
        assert "Consistency" in cat_names
        assert "Strength" in cat_names
        assert "Endurance" in cat_names
        assert "Nutrition" in cat_names
        assert "Special" in cat_names

        # Next milestone (nested in progressSummary)
        next_m = data["progressSummary"]["nextMilestone"]
        assert next_m["currentPts"] == 0
        assert next_m["targetPts"] == 1000
        assert next_m["ptsToGo"] == 1000
        assert next_m["level"] == 10
        assert next_m["currentLevel"] == 1
    finally:
        app.dependency_overrides.clear()


# =============================================================================
# 15. HONEST EMPTY CHALLENGE & UNRANKED LEADERBOARD STATES
# =============================================================================

def test_empty_challenge_and_leaderboard_honest_states(
    client: TestClient,
    mock_ach_repo: AchievementRepository,
    mock_workout_repo: WorkoutRepository,
    mock_nutrition_repo: NutritionRepository,
    mock_user_repo: UserRepository,
):
    """17. Verify currentChallenges is empty [] and leaderboard returns honest unranked state (never #1)."""
    user = CurrentUser(uid="honest_user", email="honest@pulseai.fit", name="Honest User", email_verified=True)
    app.dependency_overrides[get_current_user] = lambda: user
    app.dependency_overrides[get_achievement_repository] = lambda: mock_ach_repo
    app.dependency_overrides[get_workout_repository] = lambda: mock_workout_repo
    app.dependency_overrides[get_nutrition_repository] = lambda: mock_nutrition_repo
    app.dependency_overrides[get_user_repository] = lambda: mock_user_repo

    try:
        res = client.get("/api/v1/achievements")
        data = res.json()

        # Challenges must be empty list, not fabricated mock challenges
        assert data["currentChallenges"] == []

        # Leaderboard must be empty list / unranked (no misleading rank #1 or Top X%)
        assert data["leaderboard"] == []
    finally:
        app.dependency_overrides.clear()


# =============================================================================
# 16. RESTORED APPROVED ACHIEVEMENT POINT VALUES (ALL 24)
# =============================================================================

def test_restored_approved_achievement_point_values(mock_ach_repo: AchievementRepository):
    """18. Verify that all 24 achievements have the exact authorized point values."""
    expected_points = {
        # Workout Mastery
        "first_workout": 100,
        "workouts_5": 250,
        "workouts_10": 500,
        "workouts_25": 1000,
        "workouts_50": 2000,
        # Consistency
        "streak_3": 150,
        "streak_7": 500,
        "streak_14": 1000,
        "streak_30": 2500,
        # Strength
        "first_pr": 200,
        "prs_5": 750,
        "prs_10": 1500,
        "volume_5k": 200,
        "volume_25k": 750,
        "volume_50k": 1500,
        "volume_100k": 3000,
        # Endurance
        "calories_1k": 150,
        "calories_5k": 500,
        "calories_10k": 1200,
        # Nutrition
        "nutrition_1": 100,
        "nutrition_7": 500,
        "hydration_1": 100,
        "hydration_7": 500,
        # Special
        "early_bird": 200,
    }

    definitions = mock_ach_repo.list_definitions()
    def_map = {d.id: d.points for d in definitions}

    for ach_id, expected_pts in expected_points.items():
        assert ach_id in def_map, f"Missing achievement definition: {ach_id}"
        assert def_map[ach_id] == expected_pts, (
            f"Point mismatch for {ach_id}: expected {expected_pts}, got {def_map[ach_id]}"
        )


# =============================================================================
# 17. CORRECT LEVEL PROGRESSION SEMANTICS
# =============================================================================

def test_level_progression_semantics_all_tiers():
    """19. Verify deterministic level progression across 0, 1000, 2500, 5000, 8000, 12000, 16000 points."""
    # Level 1: 0 points (starting state)
    lvl, nxt, title, target, to_go = AchievementService.calculate_level_progression(0)
    assert lvl == 1
    assert nxt == 10
    assert title == "Novice Lifter"
    assert target == 1000
    assert to_go == 1000

    # Exactly 1000 points -> Level 10, next is Level 20 (2500)
    lvl, nxt, title, target, to_go = AchievementService.calculate_level_progression(1000)
    assert lvl == 10
    assert nxt == 20
    assert title == "Apprentice"
    assert target == 2500
    assert to_go == 1500

    # Exactly 2500 points -> Level 20, next is Level 30 (5000)
    lvl, nxt, title, target, to_go = AchievementService.calculate_level_progression(2500)
    assert lvl == 20
    assert nxt == 30
    assert title == "Challenger"
    assert target == 5000
    assert to_go == 2500

    # Exactly 5000 points -> Level 30, next is Level 40 (8000)
    lvl, nxt, title, target, to_go = AchievementService.calculate_level_progression(5000)
    assert lvl == 30
    assert nxt == 40
    assert title == "Athlete"
    assert target == 8000
    assert to_go == 3000

    # Exactly 8000 points -> Level 40, next is Level 50 (12000)
    lvl, nxt, title, target, to_go = AchievementService.calculate_level_progression(8000)
    assert lvl == 40
    assert nxt == 50
    assert title == "Fitness Legend"
    assert target == 12000
    assert to_go == 4000

    # Exactly 12000 points -> Level 50, next is Level 60 (16000)
    lvl, nxt, title, target, to_go = AchievementService.calculate_level_progression(12000)
    assert lvl == 50
    assert nxt == 60
    assert title == "Iron Master"
    assert target == 16000
    assert to_go == 4000

    # Exactly 16000 points -> Level 60 (open-ended tier)
    lvl, nxt, title, target, to_go = AchievementService.calculate_level_progression(16000)
    assert lvl == 60
    assert nxt == 70
    assert title == "Apex Titan"
    assert target == 21000
    assert to_go == 5000


# =============================================================================
# 18. LEADERBOARD UNRANKED HONEST BEHAVIOR (WITH EARNED POINTS)
# =============================================================================

def test_leaderboard_unranked_state_even_with_points(
    client: TestClient,
    mock_ach_repo: AchievementRepository,
    mock_workout_repo: WorkoutRepository,
    mock_nutrition_repo: NutritionRepository,
    mock_user_repo: UserRepository,
):
    """20. Verify that a user with earned points is NOT shown as #1 when no multi-user ranking exists."""
    user = CurrentUser(uid="points_user", email="pts@pulseai.fit", name="Points User", email_verified=True)
    app.dependency_overrides[get_current_user] = lambda: user
    app.dependency_overrides[get_achievement_repository] = lambda: mock_ach_repo
    app.dependency_overrides[get_workout_repository] = lambda: mock_workout_repo
    app.dependency_overrides[get_nutrition_repository] = lambda: mock_nutrition_repo
    app.dependency_overrides[get_user_repository] = lambda: mock_user_repo

    try:
        # Create a custom milestone (awards 100 points)
        mock_ach_repo.create_custom_achievement(user.uid, "100kg Bench", "Strength")

        res = client.get("/api/v1/achievements")
        assert res.status_code == 200
        data = res.json()

        # Total points should be 100
        assert data["kpis"][1]["value"] == "100"
        # Current level should be 1, next level 10
        assert data["progressSummary"]["nextMilestone"]["currentLevel"] == 1
        assert data["progressSummary"]["nextMilestone"]["level"] == 10
        assert data["progressSummary"]["nextMilestone"]["targetPts"] == 1000
        assert data["progressSummary"]["nextMilestone"]["ptsToGo"] == 900

        # Leaderboard must remain honestly unranked/empty, NOT falsely claim rank #1
        assert data["leaderboard"] == []
    finally:
        app.dependency_overrides.clear()

