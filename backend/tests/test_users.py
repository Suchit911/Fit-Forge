from unittest.mock import patch
from fastapi.testclient import TestClient
from backend.app.main import app
from backend.app.core.security import CurrentUser, get_current_user
from backend.app.repositories.user_repository import UserRepository, get_user_repository
import pytest


@pytest.fixture
def mock_repo():
    """Provides a fresh, isolated in-memory UserRepository for testing."""
    repo = UserRepository(db=None)  # None forces in-memory dictionary
    return repo


def test_missing_authorization_header(client: TestClient):
    """1. Test that requests without Authorization header are rejected with 401."""
    response = client.get("/api/v1/users/me")
    assert response.status_code == 401
    assert "Missing Bearer authentication token" in response.json()["detail"]


def test_invalid_firebase_token(client: TestClient):
    """2. Test that requests with an invalid Firebase ID token are rejected with 401."""
    with patch("backend.app.core.security.auth.verify_id_token", side_effect=Exception("Invalid token format")):
        response = client.get(
            "/api/v1/users/me",
            headers={"Authorization": "Bearer invalid_tampered_token_xyz"},
        )
        assert response.status_code == 401
        assert "Could not validate credentials." in response.json()["detail"]


def test_protected_endpoints_rejection(client: TestClient):
    """3. Test that all user profile mutation endpoints reject unauthenticated requests."""
    # POST /me
    post_res = client.post("/api/v1/users/me", json={"name": "Attacker"})
    assert post_res.status_code == 401

    # PATCH /me
    patch_res = client.patch("/api/v1/users/me", json={"name": "Attacker"})
    assert patch_res.status_code == 401

    # PUT /me
    put_res = client.put("/api/v1/users/me", json={"name": "Attacker"})
    assert put_res.status_code == 401


def test_valid_authenticated_user_dependency(client: TestClient):
    """4. Test that verify_firebase_token decodes valid token into CurrentUser."""
    mock_payload = {
        "uid": "firebase_test_uid_123",
        "email": "verified@pulseai.fit",
        "name": "Verified Athlete",
        "email_verified": True,
    }
    with patch("backend.app.core.security.auth.verify_id_token", return_value=mock_payload):
        response = client.get(
            "/api/v1/users/me",
            headers={"Authorization": "Bearer valid_signed_firebase_id_token"},
        )
        assert response.status_code == 200
        data = response.json()
        assert data["id"] == "firebase_test_uid_123"
        assert data["email"] == "verified@pulseai.fit"
        assert data["name"] == "Verified Athlete"


def test_user_profile_creation(client: TestClient, mock_repo: UserRepository):
    """5. Test explicit user profile creation via POST /api/v1/users/me."""
    user_alpha = CurrentUser(
        uid="usr_alpha_999",
        email="alpha@pulseai.fit",
        name="Alpha Athlete",
        email_verified=True,
    )

    app.dependency_overrides[get_current_user] = lambda: user_alpha
    app.dependency_overrides[get_user_repository] = lambda: mock_repo

    try:
        payload = {
            "name": "Alpha Athlete",
            "age": 29,
            "heightCm": 180.0,
            "weightKg": 75.0,
            "fitnessLevel": "intermediate",
            "primaryGoal": "strength",
            "secondaryGoals": ["muscle_gain"],
            "environment": "gym",
            "workoutFrequencyDaysPerWeek": 4,
            "workoutDurationMinutes": 60,
            "dietaryPreference": "high_protein",
            "targetCalories": 2600,
            "targetProteinGrams": 180,
            "targetCarbsGrams": 260,
            "targetFatGrams": 75,
        }
        res = client.post("/api/v1/users/me", json=payload)
        assert res.status_code == 201
        data = res.json()
        assert data["id"] == "usr_alpha_999"
        assert data["name"] == "Alpha Athlete"
        assert data["primaryGoal"] == "strength"
        assert data["weightKg"] == 75.0
        # Check BMI calculation (75 / (1.8^2) = 23.1)
        assert data["bmi"] == 23.1
    finally:
        app.dependency_overrides.clear()


def test_get_current_user_profile(client: TestClient, mock_repo: UserRepository):
    """6. Test retrieving current user profile (including auto-initialization for new users)."""
    user_beta = CurrentUser(
        uid="usr_beta_888",
        email="beta@pulseai.fit",
        name="Beta Lifter",
        email_verified=True,
    )

    app.dependency_overrides[get_current_user] = lambda: user_beta
    app.dependency_overrides[get_user_repository] = lambda: mock_repo

    try:
        # First GET: Auto-initializes
        res1 = client.get("/api/v1/users/me")
        assert res1.status_code == 200
        data1 = res1.json()
        assert data1["id"] == "usr_beta_888"
        assert data1["email"] == "beta@pulseai.fit"
        assert data1["name"] == "Beta Lifter"

        # Second GET: Fetches existing
        res2 = client.get("/api/v1/users/me")
        assert res2.status_code == 200
        assert res2.json()["id"] == "usr_beta_888"
    finally:
        app.dependency_overrides.clear()


def test_update_current_user_profile(client: TestClient, mock_repo: UserRepository):
    """7. Test partial update of current user profile via PATCH /api/v1/users/me."""
    user_gamma = CurrentUser(
        uid="usr_gamma_777",
        email="gamma@pulseai.fit",
        name="Gamma Runner",
        email_verified=True,
    )

    app.dependency_overrides[get_current_user] = lambda: user_gamma
    app.dependency_overrides[get_user_repository] = lambda: mock_repo

    try:
        # Auto-create profile first
        client.get("/api/v1/users/me")

        # Update weight and fitness level
        updates = {
            "weightKg": 68.5,
            "fitnessLevel": "advanced",
            "targetCalories": 2200,
        }
        patch_res = client.patch("/api/v1/users/me", json=updates)
        assert patch_res.status_code == 200
        updated_data = patch_res.json()
        assert updated_data["id"] == "usr_gamma_777"
        assert updated_data["weightKg"] == 68.5
        assert updated_data["fitnessLevel"] == "advanced"
        assert updated_data["targetCalories"] == 2200
        # Unmodified fields should be preserved
        assert updated_data["email"] == "gamma@pulseai.fit"
    finally:
        app.dependency_overrides.clear()


def test_cross_user_access_protection(client: TestClient, mock_repo: UserRepository):
    """
    8. Verify cross-user access protection:
    An attacker cannot read, create, or modify a victim user's document
    by supplying a spoofed UID in the payload. The server strictly enforces
    the UID decoded from the authenticated Firebase ID token.
    """
    victim_user = CurrentUser(
        uid="victim_uid_001",
        email="victim@pulseai.fit",
        name="Victim User",
        email_verified=True,
    )
    attacker_user = CurrentUser(
        uid="attacker_uid_999",
        email="attacker@pulseai.fit",
        name="Malicious Actor",
        email_verified=True,
    )

    # 1. Setup victim profile
    app.dependency_overrides[get_current_user] = lambda: victim_user
    app.dependency_overrides[get_user_repository] = lambda: mock_repo
    client.post("/api/v1/users/me", json={"name": "Victim User", "weightKg": 70.0})
    app.dependency_overrides.clear()

    # Verify victim exists in repository
    victim_doc = mock_repo.get_by_uid("victim_uid_001")
    assert victim_doc is not None
    assert victim_doc.name == "Victim User"

    # 2. Attacker logs in and tries to inject victim's UID in body to overwrite victim's data
    app.dependency_overrides[get_current_user] = lambda: attacker_user
    app.dependency_overrides[get_user_repository] = lambda: mock_repo

    try:
        malicious_payload = {
            "id": "victim_uid_001",  # Spoofed UID
            "name": "Hacked By Attacker",
            "weightKg": 999.0,
        }
        attack_res = client.patch("/api/v1/users/me", json=malicious_payload)
        assert attack_res.status_code == 200

        # The response must belong to the attacker, NOT the victim
        assert attack_res.json()["id"] == "attacker_uid_999"

        # Verify victim's document was NOT modified
        victim_after = mock_repo.get_by_uid("victim_uid_001")
        assert victim_after.name == "Victim User"
        assert victim_after.weightKg == 70.0

        # Attacker's own document was updated
        attacker_doc = mock_repo.get_by_uid("attacker_uid_999")
        assert attacker_doc is not None
        assert attacker_doc.id == "attacker_uid_999"
    finally:
        app.dependency_overrides.clear()


def test_new_user_profile_is_incomplete_and_has_no_fictional_data(client: TestClient, mock_repo: UserRepository):
    """Verifies that a brand-new auto-initialized user has profile_complete=False and NO fictional biometrics."""
    new_user = CurrentUser(
        uid="usr_new_test_001",
        email="newbie@pulsefit.test",
        name="New Athlete",
        email_verified=True,
    )
    app.dependency_overrides[get_current_user] = lambda: new_user
    app.dependency_overrides[get_user_repository] = lambda: mock_repo

    try:
        res = client.get("/api/v1/users/me")
        assert res.status_code == 200
        data = res.json()
        assert data["id"] == "usr_new_test_001"
        assert data["email"] == "newbie@pulsefit.test"
        assert data["name"] == "New Athlete"
        assert data["profile_complete"] is False

        # Must NOT have fictional values like Rohit Sharma / 28 / 72.4kg
        assert data["age"] is None
        assert data["heightCm"] is None
        assert data["weightKg"] is None
        assert data["primaryGoal"] is None
        assert data["targetCalories"] is None
        assert data["streakDays"] == 0
        assert data["totalWorkouts"] == 0
        assert data["totalCaloriesBurned"] == 0
        assert data["totalPoints"] == 0
    finally:
        app.dependency_overrides.clear()


def test_onboarding_completion_persists_real_values(client: TestClient, mock_repo: UserRepository):
    """Verifies that completing onboarding sets profile_complete=True and persists real values."""
    user = CurrentUser(
        uid="usr_onboarding_002",
        email="onboard@pulsefit.test",
        name="Onboarding User",
        email_verified=True,
    )
    app.dependency_overrides[get_current_user] = lambda: user
    app.dependency_overrides[get_user_repository] = lambda: mock_repo

    try:
        # 1. Initial auto-initialization
        res_init = client.get("/api/v1/users/me")
        assert res_init.json()["profile_complete"] is False

        # 2. Submit onboarding form
        onboarding_payload = {
            "profile_complete": True,
            "age": 29,
            "gender": "male",
            "heightCm": 182.0,
            "weightKg": 80.0,
            "primaryGoal": "fat_loss",
            "targetWeightKg": 75.0,
            "fitnessLevel": "intermediate",
            "workoutFrequencyDaysPerWeek": 4,
            "workoutDurationMinutes": 45,
            "preferredWorkoutType": "Strength Training",
            "preferredTrainingTime": "Morning",
            "dietaryPreference": "Non-Vegetarian",
            "targetCalories": 2200,
            "targetProteinGrams": 160,
            "targetCarbsGrams": 240,
            "targetFatGrams": 65,
            "hydrationGoalLiters": 3.0,
        }
        res_patch = client.patch("/api/v1/users/me", json=onboarding_payload)
        assert res_patch.status_code == 200
        saved = res_patch.json()

        assert saved["profile_complete"] is True
        assert saved["age"] == 29
        assert saved["weightKg"] == 80.0
        assert saved["heightCm"] == 182.0
        assert saved["primaryGoal"] == "fat_loss"
        assert saved["targetCalories"] == 2200
        assert saved["bmi"] == round(80.0 / (1.82 * 1.82), 1)

        # 3. Subsequent GET /me returns completed profile
        res_get = client.get("/api/v1/users/me")
        assert res_get.json()["profile_complete"] is True
        assert res_get.json()["weightKg"] == 80.0
    finally:
        app.dependency_overrides.clear()


def test_existing_valid_user_preservation(client: TestClient, mock_repo: UserRepository):
    """Verifies that an existing profile with real data without explicit profile_complete is treated as complete."""
    # Seed an existing profile directly in repo
    mock_repo._in_memory_store["existing_user_003"] = {
        "id": "existing_user_003",
        "name": "Existing Champion",
        "email": "champion@pulsefit.test",
        "age": 30,
        "heightCm": 175.0,
        "weightKg": 70.0,
        "primaryGoal": "muscle_gain",
        "targetCalories": 2500,
    }

    user = CurrentUser(
        uid="existing_user_003",
        email="champion@pulsefit.test",
        name="Existing Champion",
        email_verified=True,
    )
    app.dependency_overrides[get_current_user] = lambda: user
    app.dependency_overrides[get_user_repository] = lambda: mock_repo

    try:
        res = client.get("/api/v1/users/me")
        assert res.status_code == 200
        assert res.json()["profile_complete"] is True
        assert res.json()["name"] == "Existing Champion"
        assert res.json()["weightKg"] == 70.0
    finally:
        app.dependency_overrides.clear()


def test_bmi_and_bmr_remain_none_when_biometrics_missing(client: TestClient, mock_repo: UserRepository):
    """Verifies that BMI, BMR, and TDEE are NOT calculated when height/weight/age are omitted."""
    user = CurrentUser(
        uid="usr_no_biometrics_004",
        email="minimal@pulsefit.test",
        name="Minimal Athlete",
        email_verified=True,
    )
    app.dependency_overrides[get_current_user] = lambda: user
    app.dependency_overrides[get_user_repository] = lambda: mock_repo

    try:
        # Patch only goals and preferences without height/weight/age
        res = client.patch(
            "/api/v1/users/me",
            json={
                "profile_complete": True,
                "primaryGoal": "general_fitness",
                "workoutFrequencyDaysPerWeek": 3,
            },
        )
        assert res.status_code == 200
        data = res.json()
        assert data["bmi"] is None
        assert data["bmr"] is None
        assert data["tdee"] is None
        assert data["targetCalories"] is None
    finally:
        app.dependency_overrides.clear()


def test_cors_preflight_on_users_me(client: TestClient):
    """Verifies CORS OPTIONS preflight request to /api/v1/users/me returns 200 with appropriate CORS headers."""
    response = client.options(
        "/api/v1/users/me",
        headers={
            "Origin": "http://localhost:5173",
            "Access-Control-Request-Method": "GET",
            "Access-Control-Request-Headers": "Authorization, Content-Type",
        },
    )
    assert response.status_code == 200
    assert response.headers.get("access-control-allow-origin") == "http://localhost:5173"
    assert "GET" in response.headers.get("access-control-allow-methods", "")

