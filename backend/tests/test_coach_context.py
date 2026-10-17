import pytest
from datetime import datetime, timezone, timedelta
from backend.app.services.coach_context_service import CoachContextService, get_today_utc_date
from backend.app.repositories.user_repository import UserRepository
from backend.app.repositories.workout_repository import WorkoutRepository
from backend.app.repositories.nutrition_repository import NutritionRepository
from backend.app.repositories.achievement_repository import AchievementRepository
from backend.app.services.progress_service import ProgressService
from backend.app.services.nutrition_service import NutritionService
from backend.app.services.achievement_service import AchievementService
from backend.app.schemas.user import UserProfileCreate
from backend.app.schemas.workout import WorkoutSessionCreate, WorkoutSetRecord, WorkoutSessionUpdate
from backend.app.schemas.coach import CoachSettingsSchema


@pytest.fixture
def mock_user_repo():
    return UserRepository(db=None)


@pytest.fixture
def mock_wkt_repo():
    return WorkoutRepository(db=None)


@pytest.fixture
def mock_nutr_repo():
    return NutritionRepository(db=None)


@pytest.fixture
def mock_ach_repo():
    repo = AchievementRepository(db=None)
    repo.ensure_seeded()
    return repo


@pytest.fixture
def context_service(mock_user_repo, mock_wkt_repo, mock_nutr_repo, mock_ach_repo):
    prog_svc = ProgressService(workout_repo=mock_wkt_repo, user_repo=mock_user_repo)
    nutr_svc = NutritionService(nutrition_repo=mock_nutr_repo, user_repo=mock_user_repo)
    ach_svc = AchievementService(
        achievement_repo=mock_ach_repo,
        workout_repo=mock_wkt_repo,
        nutrition_repo=mock_nutr_repo,
        user_repo=mock_user_repo,
        progress_service=prog_svc,
    )
    return CoachContextService(
        user_repo=mock_user_repo,
        workout_repo=mock_wkt_repo,
        progress_service=prog_svc,
        nutrition_repo=mock_nutr_repo,
        nutrition_service=nutr_svc,
        achievement_repo=mock_ach_repo,
        achievement_service=ach_svc,
    )


# =============================================================================
# 1. PROFILE CONTEXT TESTS
# =============================================================================

def test_profile_context_retrieval(context_service: CoachContextService, mock_user_repo: UserRepository):
    """Verifies profile context correctly extracts name, goal, experience, and macro targets."""
    uid = "user_prof_01"
    mock_user_repo.create(
        uid=uid,
        email="alex@example.com",
        profile_in=UserProfileCreate(
            name="Alex Lifter",
            fitnessLevel="advanced",
            primaryGoal="muscle_gain",
            targetCalories=2800,
            targetProteinGrams=190,
        ),
    )

    ctx = context_service.build_context(uid)
    assert ctx.profileAvailable is True
    assert ctx.profile.name == "Alex Lifter"
    assert ctx.profile.goal == "Muscle Gain / Hypertrophy"
    assert ctx.profile.experienceLevel == "Advanced"
    assert ctx.profile.targetCalories == 2800
    assert ctx.profile.targetProteinGrams == 190.0


def test_profile_context_missing_profile(context_service: CoachContextService):
    """Verifies that a user with no profile record returns clean defaults without error."""
    uid = "nonexistent_user"
    ctx = context_service.build_context(uid)
    assert ctx.profileAvailable is True
    assert ctx.profile.name is None
    assert ctx.profile.goal is None
    assert ctx.profile.targetCalories is None


# =============================================================================
# 2. PREFERENCES CONTEXT TESTS
# =============================================================================

def test_preferences_explicit_settings(context_service: CoachContextService):
    """Verifies explicit preferences override automatic goal mapping."""
    uid = "user_pref_01"
    custom_prefs = CoachSettingsSchema(tone="strict", focus="strength")
    ctx = context_service.build_context(uid, preferences=custom_prefs)
    assert ctx.preferences.tone == "strict"
    assert ctx.preferences.focus == "strength"


def test_preferences_mapped_from_goal(context_service: CoachContextService, mock_user_repo: UserRepository):
    """Verifies default focus maps intelligently from user's primary goal."""
    uid = "user_pref_02"
    mock_user_repo.create(
        uid=uid,
        email="fatloss@example.com",
        profile_in=UserProfileCreate(name="Sam", primaryGoal="fat_loss"),
    )
    ctx = context_service.build_context(uid)
    assert ctx.preferences.tone == "encouraging"
    assert ctx.preferences.focus == "fat_loss"


# =============================================================================
# 3. RECENT ACTIVITY & PR TESTS
# =============================================================================

def test_recent_activity_empty_state(context_service: CoachContextService):
    """Verifies clean activity defaults when the user has 0 workouts."""
    uid = "user_no_workouts"
    ctx = context_service.build_context(uid)
    assert ctx.recentActivityAvailable is True
    assert ctx.recentActivity.workoutsCompletedThisWeek == 0
    assert ctx.recentActivity.totalRecentVolumeKg == 0.0
    assert ctx.recentActivity.activeStreak == 0
    assert ctx.recentActivity.latestWorkoutTitle is None
    assert ctx.recentActivity.recentPRs == []


def test_recent_activity_populated(context_service: CoachContextService, mock_wkt_repo: WorkoutRepository):
    """Verifies 7-day workouts, volume, and PR calculation match authoritative ProgressService."""
    uid = "user_active_lifter"
    now_iso = datetime.now(timezone.utc).isoformat()

    # Create and complete a session with sets
    from backend.app.schemas.workout import WorkoutSessionComplete
    sess = mock_wkt_repo.create_session(uid, WorkoutSessionCreate(workoutId="w1", notes="Push Day"))
    mock_wkt_repo.update_session(
        uid,
        sess.id,
        WorkoutSessionUpdate(
            recordedSet=WorkoutSetRecord(
                exerciseId="ex_bench_press",
                setNumber=1,
                actualReps=5,
                actualWeightKg=100.0,
                isCompleted=True,
            )
        ),
    )
    mock_wkt_repo.complete_session(uid, sess.id, WorkoutSessionComplete(durationSeconds=2700))

    ctx = context_service.build_context(uid)
    assert ctx.recentActivityAvailable is True
    assert ctx.recentActivity.workoutsCompletedThisWeek == 1
    assert ctx.recentActivity.totalRecentVolumeKg == 500.0  # 5 * 100
    assert ctx.recentActivity.activeStreak == 1
    assert ctx.recentActivity.latestWorkoutTitle is not None
    assert len(ctx.recentActivity.recentPRs) == 1
    assert "100" in ctx.recentActivity.recentPRs[0]


# =============================================================================
# 4. NUTRITION CONTEXT TESTS
# =============================================================================

def test_nutrition_not_logged_today(context_service: CoachContextService):
    """Verifies that missing today's nutrition log is explicitly identified as not logged."""
    uid = "user_no_nutrition"
    ctx = context_service.build_context(uid)
    assert ctx.todayNutritionAvailable is True
    assert ctx.todayNutrition.isLoggedToday is False
    assert ctx.todayNutrition.consumedCalories is None
    assert ctx.todayNutrition.consumedProteinGrams is None
    assert ctx.todayNutrition.consumedWaterLiters is None
    assert ctx.todayNutrition.targetCalories == 2400  # Default target preserved


def test_nutrition_logged_today(context_service: CoachContextService, mock_nutr_repo: NutritionRepository):
    """Verifies today's logged calories, protein, and water are populated accurately."""
    uid = "user_nutrition_logged"
    today_str = get_today_utc_date()

    mock_nutr_repo.save_daily_log(
        uid=uid,
        date=today_str,
        data={
            "id": today_str,
            "date": today_str,
            "consumedCalories": 1950,
            "targetCalories": 2500,
            "consumedProteinGrams": 145.5,
            "targetProteinGrams": 180.0,
            "consumedCarbsGrams": 220.0,
            "targetCarbsGrams": 260.0,
            "consumedFatGrams": 65.0,
            "targetFatGrams": 75.0,
            "waterIntakeLiters": 2.5,
            "waterTargetLiters": 3.0,
        },
    )

    ctx = context_service.build_context(uid)
    assert ctx.todayNutritionAvailable is True
    assert ctx.todayNutrition.isLoggedToday is True
    assert ctx.todayNutrition.consumedCalories == 1950
    assert ctx.todayNutrition.targetCalories == 2500
    assert ctx.todayNutrition.consumedProteinGrams == 145.5
    assert ctx.todayNutrition.consumedWaterLiters == 2.5


# =============================================================================
# 5. ACHIEVEMENTS CONTEXT TESTS
# =============================================================================

def test_achievements_empty_state(context_service: CoachContextService):
    """Verifies achievements default state when user has unlocked no badges."""
    uid = "user_no_achievements"
    ctx = context_service.build_context(uid)
    assert ctx.achievementsAvailable is True
    assert ctx.achievements.totalPoints == 0
    assert ctx.achievements.level == 1
    assert ctx.achievements.unlockedCount == 0
    assert ctx.achievements.latestBadge is None


def test_achievements_with_unlocked_badges(
    context_service: CoachContextService, mock_ach_repo: AchievementRepository
):
    """Verifies total points and latest badge match authoritative AchievementRepository."""
    uid = "user_achiever"
    now_iso = datetime.now(timezone.utc).isoformat()

    mock_ach_repo.upsert_user_achievement(
        uid=uid,
        data={
            "id": "first_workout",
            "achievementId": "first_workout",
            "isUnlocked": True,
            "unlockedAt": now_iso,
            "points": 100,
        },
    )

    ctx = context_service.build_context(uid)
    assert ctx.achievementsAvailable is True
    assert ctx.achievements.totalPoints == 100
    assert ctx.achievements.unlockedCount == 1
    assert ctx.achievements.latestBadge == "First Step"


# =============================================================================
# 6. BOUNDING, PRIVACY & SERIALIZATION TESTS
# =============================================================================

def test_context_serialization_privacy_and_bounding(
    context_service: CoachContextService,
    mock_user_repo: UserRepository,
    mock_wkt_repo: WorkoutRepository,
    mock_nutr_repo: NutritionRepository,
    mock_ach_repo: AchievementRepository,
):
    """Verifies serialization produces compact text without exposing UIDs, emails, or tokens."""
    uid = "user_private_123"
    mock_user_repo.create(
        uid=uid,
        email="private_email@secret.com",
        profile_in=UserProfileCreate(name="Jordan", primaryGoal="strength"),
    )

    ctx = context_service.build_context(uid)
    serialized = context_service.serialize_for_llm(ctx)

    # Privacy assertions: Never expose UID or email in prompt context
    assert uid not in serialized
    assert "private_email@secret.com" not in serialized
    assert "token" not in serialized.lower()

    # Structure assertions
    assert "[USER PROFILE]" in serialized
    assert "Name: Jordan" in serialized
    assert "[COACHING PREFERENCES]" in serialized
    assert "[RECENT ACTIVITY (LAST 7 DAYS)]" in serialized
    assert "[TODAY'S NUTRITION]" in serialized
    assert "[ACHIEVEMENTS]" in serialized

    # Token bounding: Serialized context should be well under 400 words / 500 tokens
    word_count = len(serialized.split())
    assert word_count < 300


# =============================================================================
# 7. FAILURE ISOLATION & FAULT TOLERANCE TESTS
# =============================================================================

def test_failure_isolation_profile_failure(
    context_service: CoachContextService, monkeypatch
):
    """Verifies that an error fetching the user profile is isolated without crashing the context build."""
    def broken_get_by_uid(uid):
        raise RuntimeError("Firestore connection timeout for users collection")

    monkeypatch.setattr(context_service.user_repo, "get_by_uid", broken_get_by_uid)

    ctx = context_service.build_context("user_test_fail")
    # Profile section marked unavailable
    assert ctx.profileAvailable is False
    assert len(ctx.errors) == 1
    assert "Profile retrieval error" in ctx.errors[0]

    # Other sections still build successfully
    assert ctx.recentActivityAvailable is True
    assert ctx.todayNutritionAvailable is True
    assert ctx.achievementsAvailable is True

    # Serialization handles the unavailable section gracefully
    serialized = context_service.serialize_for_llm(ctx)
    assert "Profile information temporarily unavailable" in serialized
    assert "[TODAY'S NUTRITION]" in serialized


def test_failure_isolation_nutrition_failure(
    context_service: CoachContextService, monkeypatch
):
    """Verifies that nutrition failure is isolated and marked unavailable."""
    def broken_get_daily_log(uid, date):
        raise RuntimeError("Firestore document corrupted")

    monkeypatch.setattr(context_service.nutrition_repo, "get_daily_log", broken_get_daily_log)

    ctx = context_service.build_context("user_test_fail_nutr")
    assert ctx.todayNutritionAvailable is False
    assert any("Nutrition retrieval error" in e for e in ctx.errors)
    assert ctx.profileAvailable is True
    assert ctx.recentActivityAvailable is True

    serialized = context_service.serialize_for_llm(ctx)
    assert "Nutrition data temporarily unavailable" in serialized


# =============================================================================
# 8. CROSS-USER ISOLATION TESTS
# =============================================================================

def test_cross_user_context_isolation(
    context_service: CoachContextService,
    mock_user_repo: UserRepository,
    mock_nutr_repo: NutritionRepository,
):
    """Verifies that context built for User A contains none of User B's data."""
    uid_a = "user_alpha"
    uid_b = "user_beta"

    mock_user_repo.create(
        uid=uid_a,
        email="alpha@test.com",
        profile_in=UserProfileCreate(name="Alpha Athlete", primaryGoal="muscle_gain"),
    )
    mock_user_repo.create(
        uid=uid_b,
        email="beta@test.com",
        profile_in=UserProfileCreate(name="Beta Runner", primaryGoal="endurance"),
    )

    ctx_a = context_service.build_context(uid_a)
    ctx_b = context_service.build_context(uid_b)

    assert ctx_a.profile.name == "Alpha Athlete"
    assert ctx_b.profile.name == "Beta Runner"
    assert ctx_a.profile.name != ctx_b.profile.name
