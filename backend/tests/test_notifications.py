import pytest
from datetime import datetime, timezone, timedelta
from fastapi.testclient import TestClient
from backend.app.main import app
from backend.app.core.security import get_current_user, CurrentUser
from backend.app.repositories.notification_repository import NotificationRepository, get_notification_repository
from backend.app.repositories.workout_repository import WorkoutRepository, get_workout_repository
from backend.app.repositories.exercise_repository import ExerciseRepository, get_exercise_repository
from backend.app.repositories.user_repository import UserRepository, get_user_repository
from backend.app.repositories.nutrition_repository import NutritionRepository, get_nutrition_repository
from backend.app.repositories.achievement_repository import AchievementRepository, get_achievement_repository
from backend.app.services.notification_service import NotificationService, get_notification_service
from backend.app.services.workout_service import WorkoutService, get_workout_service
from backend.app.services.achievement_service import AchievementService, get_achievement_service
from backend.app.services.nutrition_service import NutritionService, get_nutrition_service
from backend.app.schemas.workout import WorkoutSessionCreate, WorkoutSessionComplete, WorkoutSetRecord, WorkoutSessionUpdate


@pytest.fixture
def mock_notif_repo():
    return NotificationRepository(db=None)


@pytest.fixture
def mock_wkt_repo():
    return WorkoutRepository(db=None)


@pytest.fixture
def mock_ex_repo():
    return ExerciseRepository(db=None)


@pytest.fixture
def mock_user_repo():
    return UserRepository(db=None)


@pytest.fixture
def mock_nutr_repo():
    return NutritionRepository(db=None)


@pytest.fixture
def mock_ach_repo():
    repo = AchievementRepository(db=None)
    repo.ensure_seeded()
    return repo


@pytest.fixture
def notif_service(mock_notif_repo):
    return NotificationService(repo=mock_notif_repo)


# =============================================================================
# AUTHENTICATION & SECURITY TESTS
# =============================================================================

def test_notifications_missing_auth_header_rejected(client: TestClient):
    """1. Test that GET /api/v1/notifications requires authentication."""
    app.dependency_overrides.clear()
    res = client.get("/api/v1/notifications")
    assert res.status_code == 401
    assert "Missing Bearer" in res.json()["detail"]


def test_notifications_invalid_token_rejected(client: TestClient):
    """2. Test that GET /api/v1/notifications rejects invalid tokens."""
    app.dependency_overrides.clear()
    res = client.get("/api/v1/notifications", headers={"Authorization": "Bearer bad_token"})
    assert res.status_code == 401


def test_unread_count_missing_auth_rejected(client: TestClient):
    """3. Test that GET /api/v1/notifications/unread-count requires authentication."""
    app.dependency_overrides.clear()
    res = client.get("/api/v1/notifications/unread-count")
    assert res.status_code == 401


def test_mark_read_missing_auth_rejected(client: TestClient):
    """4. Test that PATCH /api/v1/notifications/{id}/read requires authentication."""
    app.dependency_overrides.clear()
    res = client.patch("/api/v1/notifications/notif_1/read")
    assert res.status_code == 401


def test_mark_all_read_missing_auth_rejected(client: TestClient):
    """5. Test that POST /api/v1/notifications/read-all requires authentication."""
    app.dependency_overrides.clear()
    res = client.post("/api/v1/notifications/read-all")
    assert res.status_code == 401


def test_cross_user_isolation(
    client: TestClient,
    mock_notif_repo: NotificationRepository,
):
    """6. Test that User B cannot read or mark as read User A's notifications."""
    service = NotificationService(repo=mock_notif_repo)
    user_a = CurrentUser(uid="user_alice", email="alice@test.com", name="Alice", email_verified=True)
    user_b = CurrentUser(uid="user_bob", email="bob@test.com", name="Bob", email_verified=True)

    app.dependency_overrides[get_notification_repository] = lambda: mock_notif_repo
    app.dependency_overrides[get_notification_service] = lambda: service

    # Create notification for User A
    mock_notif_repo.create_or_ignore("user_alice", {
        "id": "notif_alice_1",
        "type": "system_welcome",
        "category": "System",
        "title": "Welcome Alice",
        "message": "Alice's private notification",
        "createdAt": datetime.now(timezone.utc).isoformat(),
        "read": False,
        "important": True,
        "iconName": "shield",
    })

    # User B requests notifications feed
    app.dependency_overrides[get_current_user] = lambda: user_b
    res_b = client.get("/api/v1/notifications")
    assert res_b.status_code == 200
    assert len(res_b.json()["notifications"]) == 0
    assert res_b.json()["unreadCount"] == 0

    # User B attempts to mark User A's notification as read -> 404
    patch_b = client.patch("/api/v1/notifications/notif_alice_1/read")
    assert patch_b.status_code == 404

    # User A requests notifications feed
    app.dependency_overrides[get_current_user] = lambda: user_a
    res_a = client.get("/api/v1/notifications")
    assert res_a.status_code == 200
    assert len(res_a.json()["notifications"]) == 1
    assert res_a.json()["notifications"][0]["id"] == "notif_alice_1"
    assert res_a.json()["unreadCount"] == 1


# =============================================================================
# EMPTY STATE & KPI CALCULATION TESTS
# =============================================================================

def test_notifications_empty_state(
    client: TestClient,
    mock_notif_repo: NotificationRepository,
):
    """7. Test that new user receives clean empty state without synthetic mock data."""
    service = NotificationService(repo=mock_notif_repo)
    user = CurrentUser(uid="clean_user", email="clean@test.com", name="Clean", email_verified=True)

    app.dependency_overrides[get_current_user] = lambda: user
    app.dependency_overrides[get_notification_repository] = lambda: mock_notif_repo
    app.dependency_overrides[get_notification_service] = lambda: service

    res = client.get("/api/v1/notifications")
    assert res.status_code == 200
    data = res.json()
    assert data["unreadCount"] == 0
    assert data["todayCount"] == 0
    assert data["weekCount"] == 0
    assert data["importantCount"] == 0
    assert data["notifications"] == []
    assert data["insights"] == []
    assert data["importantUpdates"] == []
    assert data["preferences"]["workoutReminders"] is True


def test_kpi_counts_across_all_notifications(
    client: TestClient,
    mock_notif_repo: NotificationRepository,
):
    """8. Test that KPIs are calculated across all user notifications even when feed is paginated."""
    service = NotificationService(repo=mock_notif_repo)
    user = CurrentUser(uid="kpi_user", email="kpi@test.com", name="KPI", email_verified=True)

    app.dependency_overrides[get_current_user] = lambda: user
    app.dependency_overrides[get_notification_repository] = lambda: mock_notif_repo
    app.dependency_overrides[get_notification_service] = lambda: service

    now = datetime.now(timezone.utc)
    # Insert 10 notifications: 6 today (3 read, 3 unread, 2 important), 4 earlier this week
    for i in range(10):
        is_today = i < 6
        dt = now - timedelta(minutes=i) if is_today else now - timedelta(days=3)
        mock_notif_repo.create_or_ignore("kpi_user", {
            "id": f"notif_kpi_{i}",
            "type": "workout_completed",
            "category": "Workout" if i % 2 == 0 else "Nutrition",
            "title": f"Update {i}",
            "message": f"Message {i}",
            "createdAt": dt.isoformat(),
            "read": i % 2 == 0,  # 5 read, 5 unread
            "important": i < 2,  # 2 important
            "iconName": "dumbbell",
        })

    # Fetch with limit=3 (paginated feed)
    res = client.get("/api/v1/notifications?limit=3")
    assert res.status_code == 200
    data = res.json()
    assert len(data["notifications"]) == 3  # paginated
    assert data["unreadCount"] == 5  # across ALL 10
    assert data["todayCount"] == 6   # across ALL 10
    assert data["weekCount"] == 10   # across ALL 10
    assert data["importantCount"] == 2


# =============================================================================
# EVENT GENERATION & IDEMPOTENCY TESTS
# =============================================================================

def test_achievement_unlock_notification_creation_and_idempotency(
    client: TestClient,
    mock_notif_repo: NotificationRepository,
    mock_ach_repo: AchievementRepository,
    mock_wkt_repo: WorkoutRepository,
):
    """9. Test that unlocking an achievement generates exactly one notification, idempotent on re-eval."""
    notif_svc = NotificationService(repo=mock_notif_repo)
    ach_svc = AchievementService(
        achievement_repo=mock_ach_repo,
        workout_repo=mock_wkt_repo,
        notification_service=notif_svc,
    )
    user = CurrentUser(uid="ach_user", email="ach@test.com", name="Ach User", email_verified=True)

    app.dependency_overrides[get_current_user] = lambda: user
    app.dependency_overrides[get_notification_repository] = lambda: mock_notif_repo
    app.dependency_overrides[get_notification_service] = lambda: notif_svc

    # Create 1 completed workout session to unlock 'first_workout'
    mock_wkt_repo.create_session("ach_user", WorkoutSessionCreate(workoutId="wkt_upper_push"))
    active = mock_wkt_repo.get_active_session("ach_user")
    mock_wkt_repo.complete_session("ach_user", active.id, WorkoutSessionComplete(durationSeconds=1800))

    # Evaluate achievements (first pass)
    user_achs, newly = ach_svc.evaluate_user_achievements("ach_user")
    assert any(a.id == "first_workout" for a in newly)

    # Check notification was created
    notifs = mock_notif_repo.list_notifications("ach_user")
    first_wk_notifs = [n for n in notifs if n["id"] == "notif_ach_first_workout"]
    assert len(first_wk_notifs) == 1
    assert first_wk_notifs[0]["category"] == "Achievement"
    assert first_wk_notifs[0]["type"] == "achievement_unlocked"
    assert first_wk_notifs[0]["read"] is False

    # Mark the notification as read
    mock_notif_repo.mark_as_read("ach_user", "notif_ach_first_workout")
    assert mock_notif_repo.get_notification("ach_user", "notif_ach_first_workout")["read"] is True

    # Re-evaluate achievements (second pass) - must be idempotent and preserve read state
    user_achs2, newly2 = ach_svc.evaluate_user_achievements("ach_user")
    assert len(newly2) == 0

    notifs2 = mock_notif_repo.list_notifications("ach_user")
    first_wk_notifs2 = [n for n in notifs2 if n["id"] == "notif_ach_first_workout"]
    assert len(first_wk_notifs2) == 1
    assert first_wk_notifs2[0]["read"] is True  # preserved read state!


def test_workout_completed_notification(
    client: TestClient,
    mock_notif_repo: NotificationRepository,
    mock_wkt_repo: WorkoutRepository,
    mock_ex_repo: ExerciseRepository,
    mock_ach_repo: AchievementRepository,
):
    """10. Test that completing a workout session creates a workout_completed notification."""
    notif_svc = NotificationService(repo=mock_notif_repo)
    ach_svc = AchievementService(achievement_repo=mock_ach_repo, workout_repo=mock_wkt_repo, notification_service=notif_svc)
    wkt_svc = WorkoutService(
        workout_repo=mock_wkt_repo,
        exercise_repo=mock_ex_repo,
        notification_service=notif_svc,
        achievement_service=ach_svc,
    )
    user = CurrentUser(uid="wkt_user", email="wkt@test.com", name="Workout User", email_verified=True)

    app.dependency_overrides[get_current_user] = lambda: user
    app.dependency_overrides[get_notification_repository] = lambda: mock_notif_repo
    app.dependency_overrides[get_notification_service] = lambda: notif_svc
    app.dependency_overrides[get_workout_service] = lambda: wkt_svc

    # Start session
    sess = mock_wkt_repo.create_session("wkt_user", WorkoutSessionCreate(workoutId="wkt_upper_push"))

    # Complete session via WorkoutService
    completed = wkt_svc.complete_session("wkt_user", sess.id, WorkoutSessionComplete(durationSeconds=2400))
    assert completed is not None

    notifs = mock_notif_repo.list_notifications("wkt_user")
    wkt_notif = next((n for n in notifs if n["id"] == f"notif_wkt_{sess.id}"), None)
    assert wkt_notif is not None
    assert wkt_notif["category"] == "Workout"
    assert wkt_notif["type"] == "workout_completed"
    assert "Workout completed!" in wkt_notif["title"]

    # Repeated completion call is idempotent
    wkt_svc.complete_session("wkt_user", sess.id, WorkoutSessionComplete(durationSeconds=2400))
    matching = [n for n in mock_notif_repo.list_notifications("wkt_user") if n["id"] == f"notif_wkt_{sess.id}"]
    assert len(matching) == 1


def test_personal_record_notification(
    client: TestClient,
    mock_notif_repo: NotificationRepository,
    mock_wkt_repo: WorkoutRepository,
    mock_ex_repo: ExerciseRepository,
    mock_ach_repo: AchievementRepository,
):
    """11. Test that establishing a new personal record creates a personal_record notification."""
    notif_svc = NotificationService(repo=mock_notif_repo)
    ach_svc = AchievementService(achievement_repo=mock_ach_repo, workout_repo=mock_wkt_repo, notification_service=notif_svc)
    wkt_svc = WorkoutService(
        workout_repo=mock_wkt_repo,
        exercise_repo=mock_ex_repo,
        notification_service=notif_svc,
        achievement_service=ach_svc,
    )
    user = CurrentUser(uid="pr_user", email="pr@test.com", name="PR User", email_verified=True)

    # Session 1: Bench Press 80kg
    s1 = mock_wkt_repo.create_session("pr_user", WorkoutSessionCreate(workoutId="wkt_upper_push"))
    mock_wkt_repo.update_session("pr_user", s1.id, WorkoutSessionUpdate(recordedSet=WorkoutSetRecord(exerciseId="ex_bench_press", setNumber=1, actualReps=5, actualWeightKg=80.0)))
    wkt_svc.complete_session("pr_user", s1.id, WorkoutSessionComplete(durationSeconds=1800))

    pr_notifs_1 = [n for n in mock_notif_repo.list_notifications("pr_user") if n["type"] == "personal_record"]
    assert len(pr_notifs_1) == 1
    assert "80" in pr_notifs_1[0]["message"]
    assert pr_notifs_1[0]["important"] is True

    # Session 2: Bench Press 85kg (New PR!)
    s2 = mock_wkt_repo.create_session("pr_user", WorkoutSessionCreate(workoutId="wkt_upper_push"))
    mock_wkt_repo.update_session("pr_user", s2.id, WorkoutSessionUpdate(recordedSet=WorkoutSetRecord(exerciseId="ex_bench_press", setNumber=1, actualReps=5, actualWeightKg=85.0)))
    wkt_svc.complete_session("pr_user", s2.id, WorkoutSessionComplete(durationSeconds=1800))

    pr_notifs_2 = [n for n in mock_notif_repo.list_notifications("pr_user") if n["type"] == "personal_record"]
    assert len(pr_notifs_2) == 2
    assert any("85" in n["message"] for n in pr_notifs_2)

    # Session 3: Bench Press 75kg (No PR established)
    s3 = mock_wkt_repo.create_session("pr_user", WorkoutSessionCreate(workoutId="wkt_upper_push"))
    mock_wkt_repo.update_session("pr_user", s3.id, WorkoutSessionUpdate(recordedSet=WorkoutSetRecord(exerciseId="ex_bench_press", setNumber=1, actualReps=5, actualWeightKg=75.0)))
    wkt_svc.complete_session("pr_user", s3.id, WorkoutSessionComplete(durationSeconds=1800))

    pr_notifs_3 = [n for n in mock_notif_repo.list_notifications("pr_user") if n["type"] == "personal_record"]
    assert len(pr_notifs_3) == 2  # Still 2, no new PR generated!


def test_hydration_notification(
    client: TestClient,
    mock_notif_repo: NotificationRepository,
    mock_nutr_repo: NutritionRepository,
    mock_user_repo: UserRepository,
):
    """12. Test that reaching daily water target triggers hydration_milestone notification at most once per day."""
    notif_svc = NotificationService(repo=mock_notif_repo)
    nutr_svc = NutritionService(
        nutrition_repo=mock_nutr_repo,
        user_repo=mock_user_repo,
        notification_service=notif_svc,
    )
    user = CurrentUser(uid="hydro_user", email="hydro@test.com", name="Hydro User", email_verified=True)

    from backend.app.schemas.nutrition import WaterLogCreate

    # Log 1.5L (target is 3.0L) -> target not reached yet
    nutr_svc.log_water("hydro_user", WaterLogCreate(date="2026-09-05", amountLiters=1.5))
    assert len(mock_notif_repo.list_notifications("hydro_user")) == 0

    # Log another 1.5L -> total 3.0L (target reached!)
    nutr_svc.log_water("hydro_user", WaterLogCreate(date="2026-09-05", amountLiters=1.5))
    notifs = mock_notif_repo.list_notifications("hydro_user")
    hydr_notifs = [n for n in notifs if n["id"] == "notif_hydr_2026-09-05"]
    assert len(hydr_notifs) == 1
    assert hydr_notifs[0]["category"] == "Nutrition"
    assert hydr_notifs[0]["type"] == "hydration_milestone"

    # Log another 0.5L same day -> idempotent, no duplicate notification
    nutr_svc.log_water("hydro_user", WaterLogCreate(date="2026-09-05", amountLiters=0.5))
    hydr_notifs2 = [n for n in mock_notif_repo.list_notifications("hydro_user") if n["id"] == "notif_hydr_2026-09-05"]
    assert len(hydr_notifs2) == 1


def test_system_welcome_notification(
    client: TestClient,
    mock_notif_repo: NotificationRepository,
    mock_user_repo: UserRepository,
):
    """13. Test that profile auto-initialization generates exactly one welcome notification."""
    notif_svc = NotificationService(repo=mock_notif_repo)
    user = CurrentUser(uid="newbie_user", email="newbie@test.com", name="Newbie", email_verified=True)

    app.dependency_overrides[get_current_user] = lambda: user
    app.dependency_overrides[get_user_repository] = lambda: mock_user_repo
    app.dependency_overrides[get_notification_repository] = lambda: mock_notif_repo
    app.dependency_overrides[get_notification_service] = lambda: notif_svc

    # First access to /api/v1/users/me triggers profile creation and welcome notification
    res = client.get("/api/v1/users/me")
    assert res.status_code == 200

    notifs = mock_notif_repo.list_notifications("newbie_user")
    welcome_notifs = [n for n in notifs if n["id"] == "notif_sys_welcome"]
    assert len(welcome_notifs) == 1
    assert welcome_notifs[0]["category"] == "System"
    assert welcome_notifs[0]["type"] == "system_welcome"

    # Subsequent access does not duplicate welcome notification
    client.get("/api/v1/users/me")
    welcome_notifs2 = [n for n in mock_notif_repo.list_notifications("newbie_user") if n["id"] == "notif_sys_welcome"]
    assert len(welcome_notifs2) == 1


# =============================================================================
# READ & MARK ALL READ TESTS
# =============================================================================

def test_mark_single_notification_read(
    client: TestClient,
    mock_notif_repo: NotificationRepository,
):
    """14. Test marking a single notification as read."""
    service = NotificationService(repo=mock_notif_repo)
    user = CurrentUser(uid="read_user", email="read@test.com", name="Read User", email_verified=True)

    app.dependency_overrides[get_current_user] = lambda: user
    app.dependency_overrides[get_notification_repository] = lambda: mock_notif_repo
    app.dependency_overrides[get_notification_service] = lambda: service

    mock_notif_repo.create_or_ignore("read_user", {
        "id": "notif_to_read",
        "type": "workout_completed",
        "category": "Workout",
        "title": "Workout complete",
        "message": "Nice job",
        "createdAt": datetime.now(timezone.utc).isoformat(),
        "read": False,
        "important": False,
        "iconName": "dumbbell",
    })

    assert mock_notif_repo.get_unread_count("read_user") == 1

    res = client.patch("/api/v1/notifications/notif_to_read/read")
    assert res.status_code == 200
    assert res.json()["read"] is True
    assert res.json()["readAt"] is not None
    assert mock_notif_repo.get_unread_count("read_user") == 0

    # Repeated mark-read is safe
    res2 = client.patch("/api/v1/notifications/notif_to_read/read")
    assert res2.status_code == 200
    assert res2.json()["read"] is True


def test_mark_all_read(
    client: TestClient,
    mock_notif_repo: NotificationRepository,
):
    """15. Test marking all notifications as read."""
    service = NotificationService(repo=mock_notif_repo)
    user = CurrentUser(uid="bulk_user", email="bulk@test.com", name="Bulk User", email_verified=True)

    app.dependency_overrides[get_current_user] = lambda: user
    app.dependency_overrides[get_notification_repository] = lambda: mock_notif_repo
    app.dependency_overrides[get_notification_service] = lambda: service

    # Insert 4 unread notifications
    for i in range(4):
        mock_notif_repo.create_or_ignore("bulk_user", {
            "id": f"notif_bulk_{i}",
            "type": "workout_completed",
            "category": "Workout",
            "title": f"Workout {i}",
            "message": f"Message {i}",
            "createdAt": datetime.now(timezone.utc).isoformat(),
            "read": False,
            "important": False,
            "iconName": "dumbbell",
        })

    assert mock_notif_repo.get_unread_count("bulk_user") == 4

    res = client.post("/api/v1/notifications/read-all")
    assert res.status_code == 200
    assert res.json()["unreadCount"] == 0
    assert res.json()["markedCount"] == 4
    assert mock_notif_repo.get_unread_count("bulk_user") == 0

    # Repeated mark-all-read is safe
    res2 = client.post("/api/v1/notifications/read-all")
    assert res2.status_code == 200
    assert res2.json()["unreadCount"] == 0
    assert res2.json()["markedCount"] == 0


# =============================================================================
# PAGINATION & RETENTION TESTS
# =============================================================================

def test_pagination_and_ordering(
    client: TestClient,
    mock_notif_repo: NotificationRepository,
):
    """16. Test pagination with limit and stable cursor ordering."""
    service = NotificationService(repo=mock_notif_repo)
    user = CurrentUser(uid="page_user", email="page@test.com", name="Page User", email_verified=True)

    app.dependency_overrides[get_current_user] = lambda: user
    app.dependency_overrides[get_notification_repository] = lambda: mock_notif_repo
    app.dependency_overrides[get_notification_service] = lambda: service

    now = datetime.now(timezone.utc)
    for i in range(12):
        mock_notif_repo.create_or_ignore("page_user", {
            "id": f"notif_p_{i:02d}",
            "type": "workout_completed",
            "category": "Workout",
            "title": f"Workout {i}",
            "message": f"Message {i}",
            "createdAt": (now - timedelta(minutes=12 - i)).isoformat(),
            "read": False,
            "important": False,
            "iconName": "dumbbell",
        })

    # Page 1 (limit 5)
    p1 = client.get("/api/v1/notifications?limit=5").json()
    assert len(p1["notifications"]) == 5
    # Should be newest first: notif_p_11
    assert p1["notifications"][0]["id"] == "notif_p_11"

    # Page 2 (cursor = last item of page 1)
    last_id = p1["notifications"][-1]["id"]
    p2 = client.get(f"/api/v1/notifications?limit=5&before={last_id}").json()
    assert len(p2["notifications"]) == 5
    assert p2["notifications"][0]["id"] != p1["notifications"][-1]["id"]


def test_retention_pruning_policy(
    mock_notif_repo: NotificationRepository,
):
    """17. Test that pruning removes oldest READ notifications but preserves unread and newly created records."""
    now = datetime.now(timezone.utc)

    # Insert 105 notifications: 60 read, 45 unread
    for i in range(105):
        is_read = i < 60
        mock_notif_repo.create_or_ignore("retention_user", {
            "id": f"notif_ret_{i:03d}",
            "type": "workout_completed",
            "category": "Workout",
            "title": f"Title {i}",
            "message": f"Message {i}",
            "createdAt": (now - timedelta(hours=105 - i)).isoformat(),
            "read": is_read,
            "important": False,
            "iconName": "dumbbell",
        })

    assert len(mock_notif_repo.get_all_user_notifications("retention_user")) == 105

    # Trigger pruning to max 100
    pruned = mock_notif_repo.prune_user_notifications("retention_user", max_keep=100)
    assert pruned == 5
    assert len(mock_notif_repo.get_all_user_notifications("retention_user")) == 100

    # Verify that all 45 unread notifications were preserved
    unread_remaining = mock_notif_repo.get_unread_count("retention_user")
    assert unread_remaining == 45


def test_retention_all_unread_temporarily_exceeds_cap(
    mock_notif_repo: NotificationRepository,
):
    """18. Test that if all notifications are unread, retention never deletes unread items."""
    now = datetime.now(timezone.utc)
    for i in range(105):
        mock_notif_repo.create_or_ignore("unread_cap_user", {
            "id": f"notif_all_un_{i:03d}",
            "type": "workout_completed",
            "category": "Workout",
            "title": f"Title {i}",
            "message": f"Message {i}",
            "createdAt": (now - timedelta(hours=105 - i)).isoformat(),
            "read": False,  # all unread!
            "important": False,
            "iconName": "dumbbell",
        })

    # Pruning should not delete any unread notification
    pruned = mock_notif_repo.prune_user_notifications("unread_cap_user", max_keep=100)
    assert pruned == 0
    assert len(mock_notif_repo.get_all_user_notifications("unread_cap_user")) == 105


# =============================================================================
# FAILURE ISOLATION TEST
# =============================================================================

def test_notification_write_failure_does_not_break_workout_completion(
    mock_wkt_repo: WorkoutRepository,
    mock_ex_repo: ExerciseRepository,
    mock_ach_repo: AchievementRepository,
):
    """19. Test that if notification writing fails, workout completion still succeeds."""
    class BrokenNotificationService(NotificationService):
        def create_workout_completed_notification(self, *args, **kwargs):
            raise RuntimeError("Database connection timed out during notification write")

    broken_notif_svc = BrokenNotificationService()
    ach_svc = AchievementService(achievement_repo=mock_ach_repo, workout_repo=mock_wkt_repo)
    wkt_svc = WorkoutService(
        workout_repo=mock_wkt_repo,
        exercise_repo=mock_ex_repo,
        notification_service=broken_notif_svc,
        achievement_service=ach_svc,
    )

    s = mock_wkt_repo.create_session("fault_user", WorkoutSessionCreate(workoutId="wkt_upper_push"))
    completed = wkt_svc.complete_session("fault_user", s.id, WorkoutSessionComplete(durationSeconds=1800))

    # Workout completion must succeed despite notification failure!
    assert completed is not None
    assert completed.status == "completed"
