from unittest.mock import patch
import pytest
from fastapi.testclient import TestClient
from backend.app.main import app
from backend.app.core.security import CurrentUser, get_current_user
from backend.app.repositories.settings_repository import (
    SettingsRepository,
    get_settings_repository,
    PersistenceError,
)
from backend.app.schemas.settings import UserSettingsSchema, UserSettingsUpdateSchema


@pytest.fixture
def mock_settings_repo():
    """Provides a fresh, isolated in-memory SettingsRepository for testing."""
    return SettingsRepository(db=None)


# ---------------------------------------------------------------------------
# 1. Authentication & Security Tests
# ---------------------------------------------------------------------------
def test_settings_missing_authorization_header(client: TestClient):
    """Requests without Authorization header must be rejected with 401."""
    res_get = client.get("/api/v1/settings")
    assert res_get.status_code == 401
    assert "Missing Bearer authentication token" in res_get.json()["detail"]

    res_patch = client.patch("/api/v1/settings", json={"general": {"language": "Spanish"}})
    assert res_patch.status_code == 401
    assert "Missing Bearer authentication token" in res_patch.json()["detail"]


def test_settings_invalid_firebase_token(client: TestClient):
    """Requests with invalid or expired Firebase token must return 401."""
    with patch("backend.app.core.security.auth.verify_id_token", side_effect=Exception("Tampered token")):
        response = client.get(
            "/api/v1/settings",
            headers={"Authorization": "Bearer invalid_tampered_token"},
        )
        assert response.status_code == 401
        assert "Could not validate credentials." in response.json()["detail"]


# ---------------------------------------------------------------------------
# 2. First-read Defaults & User Identification
# ---------------------------------------------------------------------------
def test_first_read_defaults_for_new_user(client: TestClient, mock_settings_repo: SettingsRepository):
    """First-read of settings returns deterministic defaults with persisted=False."""
    user = CurrentUser(uid="usr_new_athlete_001", email="new@pulseai.fit")
    app.dependency_overrides[get_current_user] = lambda: user
    app.dependency_overrides[get_settings_repository] = lambda: mock_settings_repo

    try:
        res = client.get("/api/v1/settings")
        assert res.status_code == 200
        data = res.json()

        assert data["userId"] == "usr_new_athlete_001"
        assert data["persisted"] is False
        assert data["updatedAt"] is None

        # General defaults
        assert data["general"]["language"] == "English"
        assert data["general"]["units"] == "Metric (kg, cm)"
        assert data["general"]["timeZone"] == "(GMT+05:30) Asia/Kolkata"
        assert data["general"]["weekStartDay"] == "Monday"
        assert data["general"]["defaultWorkoutDurationMin"] == 60

        # Notifications defaults
        assert data["notifications"]["workoutReminders"] is True
        assert data["notifications"]["restTimerAlerts"] is True
        assert data["notifications"]["achievementNotifications"] is True
        assert data["notifications"]["nutritionReminders"] is True
        assert data["notifications"]["aiCoachInsights"] is True
        assert data["notifications"]["weeklyProgressReport"] is True

        # Appearance defaults
        assert data["appearance"]["darkMode"] is True
        assert data["appearance"]["accentColor"] == "Emerald Green"
        assert data["appearance"]["accentIntensity"] == "Medium"
        assert data["appearance"]["uiDensity"] == "Comfortable"
        assert data["appearance"]["animations"] is True
        assert data["appearance"]["reduceMotion"] is False

        # Privacy defaults
        assert data["privacy"]["profileVisibility"] == "Public"
        assert data["privacy"]["workoutDataVisibility"] == "Only You"
        assert data["privacy"]["progressPhotosVisibility"] == "Only You"
        assert data["privacy"]["aiAnalysisData"] is True
        assert data["privacy"]["twoFactorEnabled"] is True

        # AI Coach defaults
        assert data["aiCoach"]["personality"] == "Motivational"
        assert data["aiCoach"]["intensity"] == "High"
        assert data["aiCoach"]["focus"] == "Muscle Gain"
        assert data["aiCoach"]["workoutRecommendations"] == "Advanced"
        assert data["aiCoach"]["nutritionRecommendations"] == "Personalized"
        assert data["aiCoach"]["formAnalysisInsights"] == "Detailed"

        # Devices catalog defaults (unsupported external sync: isConnected=False)
        assert len(data["devices"]) == 5
        for dev in data["devices"]:
            assert dev["isConnected"] is False

        # In-memory store should NOT have stored it as persisted yet
        assert mock_settings_repo.get_by_uid("usr_new_athlete_001") is None
    finally:
        app.dependency_overrides.clear()


# ---------------------------------------------------------------------------
# 3. Partial Update Semantics & Value Preservation
# ---------------------------------------------------------------------------
def test_partial_patch_update_preserves_omitted_fields(client: TestClient, mock_settings_repo: SettingsRepository):
    """PATCH updates specified fields while retaining all other values intact."""
    user = CurrentUser(uid="usr_patch_test_101", email="patch@pulseai.fit")
    app.dependency_overrides[get_current_user] = lambda: user
    app.dependency_overrides[get_settings_repository] = lambda: mock_settings_repo

    try:
        # 1. Update only general units
        patch_1 = client.patch(
            "/api/v1/settings",
            json={"general": {"units": "Imperial (lbs, in)"}},
        )
        assert patch_1.status_code == 200
        d1 = patch_1.json()
        assert d1["general"]["units"] == "Imperial (lbs, in)"
        # Unaltered general fields preserved
        assert d1["general"]["language"] == "English"
        assert d1["general"]["defaultWorkoutDurationMin"] == 60
        # Other sections preserved
        assert d1["notifications"]["workoutReminders"] is True
        assert d1["appearance"]["darkMode"] is True
        assert d1["persisted"] is True
        assert d1["updatedAt"] is not None

        # 2. Update notification toggle and appearance
        patch_2 = client.patch(
            "/api/v1/settings",
            json={
                "notifications": {"workoutReminders": False},
                "appearance": {"accentColor": "Sunset Orange", "uiDensity": "Compact"},
            },
        )
        assert patch_2.status_code == 200
        d2 = patch_2.json()
        # Newly updated
        assert d2["notifications"]["workoutReminders"] is False
        assert d2["appearance"]["accentColor"] == "Sunset Orange"
        assert d2["appearance"]["uiDensity"] == "Compact"
        # Previously updated unit is still preserved
        assert d2["general"]["units"] == "Imperial (lbs, in)"
        # Other notification toggles still preserved
        assert d2["notifications"]["restTimerAlerts"] is True
        assert d2["aiCoach"]["personality"] == "Motivational"

        # 3. Read back via GET confirms persistence
        get_res = client.get("/api/v1/settings")
        assert get_res.status_code == 200
        d_get = get_res.json()
        assert d_get["general"]["units"] == "Imperial (lbs, in)"
        assert d_get["notifications"]["workoutReminders"] is False
        assert d_get["appearance"]["accentColor"] == "Sunset Orange"
        assert d_get["persisted"] is True
    finally:
        app.dependency_overrides.clear()


# ---------------------------------------------------------------------------
# 4. Schema Validation & Rejection of Prohibited / Unknown Fields
# ---------------------------------------------------------------------------
def test_reject_unknown_or_prohibited_fields(client: TestClient, mock_settings_repo: SettingsRepository):
    """Extra or unknown fields in request payload must be rejected with 422."""
    user = CurrentUser(uid="usr_strict_val_202", email="val@pulseai.fit")
    app.dependency_overrides[get_current_user] = lambda: user
    app.dependency_overrides[get_settings_repository] = lambda: mock_settings_repo

    try:
        # Unknown top-level key
        res_unknown_root = client.patch(
            "/api/v1/settings",
            json={"forbiddenRootField": "injected_value"},
        )
        assert res_unknown_root.status_code == 422

        # Unknown nested key in general
        res_unknown_nested = client.patch(
            "/api/v1/settings",
            json={"general": {"unknownSubField": 123}},
        )
        assert res_unknown_nested.status_code == 422

        # Client-supplied userId in body should be rejected as unknown field
        res_spoof_id = client.patch(
            "/api/v1/settings",
            json={"userId": "attacker_id"},
        )
        assert res_spoof_id.status_code == 422
    finally:
        app.dependency_overrides.clear()


def test_reject_invalid_enum_values(client: TestClient, mock_settings_repo: SettingsRepository):
    """Invalid enum values for settings options must be rejected with 422."""
    user = CurrentUser(uid="usr_enum_val_303", email="enum@pulseai.fit")
    app.dependency_overrides[get_current_user] = lambda: user
    app.dependency_overrides[get_settings_repository] = lambda: mock_settings_repo

    try:
        # Invalid units string
        res = client.patch(
            "/api/v1/settings",
            json={"general": {"units": "Stone & Furlongs"}},
        )
        assert res.status_code == 422

        # Invalid AI coach personality
        res_ai = client.patch(
            "/api/v1/settings",
            json={"aiCoach": {"personality": "Angry"}},
        )
        assert res_ai.status_code == 422

        # Invalid duration
        res_dur = client.patch(
            "/api/v1/settings",
            json={"general": {"defaultWorkoutDurationMin": 120}},
        )
        assert res_dur.status_code == 422
    finally:
        app.dependency_overrides.clear()


# ---------------------------------------------------------------------------
# 5. User Isolation
# ---------------------------------------------------------------------------
def test_user_isolation_between_authenticated_users(client: TestClient, mock_settings_repo: SettingsRepository):
    """User A's settings mutations must never bleed into or be visible to User B."""
    user_a = CurrentUser(uid="usr_alpha_isol_1", email="alpha@pulseai.fit")
    user_b = CurrentUser(uid="usr_beta_isol_2", email="beta@pulseai.fit")

    app.dependency_overrides[get_settings_repository] = lambda: mock_settings_repo

    try:
        # User A logs in and customizes their settings
        app.dependency_overrides[get_current_user] = lambda: user_a
        patch_a = client.patch(
            "/api/v1/settings",
            json={
                "general": {"language": "Spanish", "units": "Imperial (lbs, in)"},
                "appearance": {"darkMode": False, "accentColor": "Ocean Blue"},
            },
        )
        assert patch_a.status_code == 200

        # User B logs in
        app.dependency_overrides[get_current_user] = lambda: user_b
        get_b = client.get("/api/v1/settings")
        assert get_b.status_code == 200
        db = get_b.json()

        # User B should have defaults, NOT User A's custom settings
        assert db["userId"] == "usr_beta_isol_2"
        assert db["general"]["language"] == "English"
        assert db["general"]["units"] == "Metric (kg, cm)"
        assert db["appearance"]["darkMode"] is True
        assert db["appearance"]["accentColor"] == "Emerald Green"
        assert db["persisted"] is False

        # User B mutates their own settings
        patch_b = client.patch(
            "/api/v1/settings",
            json={"general": {"language": "German"}},
        )
        assert patch_b.status_code == 200

        # User A logs back in and verifies their settings are untouched
        app.dependency_overrides[get_current_user] = lambda: user_a
        get_a = client.get("/api/v1/settings")
        assert get_a.status_code == 200
        da = get_a.json()
        assert da["userId"] == "usr_alpha_isol_1"
        assert da["general"]["language"] == "Spanish"
        assert da["general"]["units"] == "Imperial (lbs, in)"
        assert da["appearance"]["accentColor"] == "Ocean Blue"
    finally:
        app.dependency_overrides.clear()


# ---------------------------------------------------------------------------
# 6. Persistence Failure Handling
# ---------------------------------------------------------------------------
def test_persistence_failure_returns_explicit_500(client: TestClient):
    """Storage failures must return explicit 500 error, never fake success."""
    user = CurrentUser(uid="usr_err_sim_404", email="err@pulseai.fit")
    app.dependency_overrides[get_current_user] = lambda: user

    class FailingSettingsRepo(SettingsRepository):
        def update(self, uid: str, updates: UserSettingsUpdateSchema):
            raise PersistenceError("Firestore connection dropped during write")

        def get_or_default(self, uid: str):
            raise PersistenceError("Firestore read timeout")

    app.dependency_overrides[get_settings_repository] = lambda: FailingSettingsRepo(db=None)

    try:
        # Failed GET
        res_get = client.get("/api/v1/settings")
        assert res_get.status_code == 500
        assert "Failed to read user settings" in res_get.json()["detail"]

        # Failed PATCH
        res_patch = client.patch(
            "/api/v1/settings",
            json={"general": {"language": "Hindi"}},
        )
        assert res_patch.status_code == 500
        assert "Failed to persist user settings update" in res_patch.json()["detail"]
    finally:
        app.dependency_overrides.clear()


# ---------------------------------------------------------------------------
# 7. Repository Reconstruction Durability (Simulating Process Restart)
# ---------------------------------------------------------------------------
def test_persistence_survives_repository_reconstruction(client: TestClient):
    """When backed by real/shared storage or persistent instance, state survives client reconstruction."""
    shared_store = {}

    class SharedStoreSettingsRepo(SettingsRepository):
        def __init__(self):
            super().__init__(db=None)
            self._in_memory_store = shared_store

    # Instance 1: write
    repo_1 = SharedStoreSettingsRepo()
    app.dependency_overrides[get_settings_repository] = lambda: repo_1
    user = CurrentUser(uid="usr_restart_505", email="restart@pulseai.fit")
    app.dependency_overrides[get_current_user] = lambda: user

    try:
        res = client.patch(
            "/api/v1/settings",
            json={"privacy": {"profileVisibility": "Private"}},
        )
        assert res.status_code == 200

        # Simulate backend process restart: create a new repository instance pointing to same storage
        repo_2 = SharedStoreSettingsRepo()
        app.dependency_overrides[get_settings_repository] = lambda: repo_2

        res_after = client.get("/api/v1/settings")
        assert res_after.status_code == 200
        assert res_after.json()["privacy"]["profileVisibility"] == "Private"
        assert res_after.json()["persisted"] is True
    finally:
        app.dependency_overrides.clear()


# ---------------------------------------------------------------------------
# 8. Genuine Firestore Backend Durability & Isolation Verification
# ---------------------------------------------------------------------------
def test_live_firestore_durability_and_restart():
    """
    Exercises genuine Cloud Firestore persistence when credentials are valid.
    Verifies:
    1. Settings update writes to users/{uid}/settings/preferences in Cloud Firestore.
    2. Reading back via a completely new SettingsRepository instance recovers the persisted state.
    3. User isolation: a different user UID receives their own isolated defaults or state.
    4. Cleans up test documents to keep the Firestore database pristine.
    """
    from backend.app.core.firebase import is_firebase_available, get_firestore_db, init_firebase

    if not is_firebase_available():
        init_firebase()

    db = get_firestore_db()
    if db is None:
        pytest.skip("Firebase service account credentials not configured for live Firestore test.")

    test_uid_1 = "test_firestore_user_alpha_777"
    test_uid_2 = "test_firestore_user_beta_888"

    # Step 1: Initialize repo 1 with live db
    repo_1 = SettingsRepository(db=db)
    assert repo_1.is_durable is True

    try:
        # Step 2: Apply partial updates for user 1
        updates_1 = UserSettingsUpdateSchema(
            general={"language": "German", "units": "Imperial (lbs, in)"},
            appearance={"darkMode": False, "accentColor": "Ocean Blue"},
        )
        saved_1 = repo_1.update(test_uid_1, updates_1)
        assert saved_1.persisted is True
        assert saved_1.general.language == "German"
        assert saved_1.general.units == "Imperial (lbs, in)"
        assert saved_1.appearance.darkMode is False

        # Step 3: Simulate backend process restart with a completely fresh repo instance
        repo_2 = SettingsRepository(db=db)
        reloaded_1 = repo_2.get_by_uid(test_uid_1)
        assert reloaded_1 is not None
        assert reloaded_1.persisted is True
        assert reloaded_1.general.language == "German"
        assert reloaded_1.general.units == "Imperial (lbs, in)"
        assert reloaded_1.appearance.darkMode is False
        assert reloaded_1.appearance.accentColor == "Ocean Blue"
        # Omitted fields preserved from defaults
        assert reloaded_1.notifications.workoutReminders is True

        # Step 4: Verify user isolation - user 2 must not see user 1's persisted document
        reloaded_2 = repo_2.get_by_uid(test_uid_2)
        assert reloaded_2 is None
        default_2 = repo_2.get_or_default(test_uid_2)
        assert default_2.persisted is False
        assert default_2.general.language == "English"

    finally:
        # Step 5: Clean up created test documents from Cloud Firestore
        try:
            db.collection("users").document(test_uid_1).collection("settings").document("preferences").delete()
            db.collection("users").document(test_uid_2).collection("settings").document("preferences").delete()
        except Exception:
            pass

