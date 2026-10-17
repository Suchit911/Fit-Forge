"""
Integration and Security Tests for Workout Plan HTTP API (Phase 9B.8.5.4).

Verifies the authenticated endpoint:
POST /api/v1/workout-plans/generate

Sections covered:
A. Authentication (missing, malformed, invalid, valid token)
B. Request Validation (invalid days, weeks, durations, invalid enums)
C. Successful Generation (1-6 training days, 1, 4, 8, 12 weeks)
D. Response Correctness (planId, splitType, slot ordering, prescriptions, feasibility)
E. Determinism (identical payload produces identical response and planId)
F. Constraint Behavior (equipment, environment, exclusions, corrective slot 0)
G. Planner Diagnostics (State B, State C, State D returned as 200 with diagnostics)
H. Failure Behavior (safe 500 without stack trace leaks)
I. Scope & Security (stateless, no Firestore, no Gemini, no user impersonation)
"""

import json
from unittest.mock import MagicMock
import pytest
from fastapi.testclient import TestClient

from backend.app.main import app
from backend.app.core.security import get_current_user, CurrentUser
from backend.app.schemas.workout_plan import (
    WorkoutSplitType,
    ExerciseSlotRole,
    DurationFeasibility,
    WorkoutPlanResponse,
)
from backend.app.services.workout_periodization_service import (
    get_workout_periodization_service,
)


@pytest.fixture
def auth_user():
    """Mock CurrentUser payload representing a verified Firebase user."""
    return CurrentUser(
        uid="usr_verified_9b854",
        email="test_user@example.com",
        name="Test Athlete",
        email_verified=True,
    )


@pytest.fixture(autouse=True)
def setup_auth(auth_user):
    """Default autouse fixture setting up verified Firebase user override."""
    app.dependency_overrides[get_current_user] = lambda: auth_user
    yield
    app.dependency_overrides.clear()


# =============================================================================
# Section A: Authentication & Token Verification
# =============================================================================

def test_generate_plan_missing_auth_header_rejected(client: TestClient):
    """POST /api/v1/workout-plans/generate rejects requests missing Authorization header (401)."""
    app.dependency_overrides.pop(get_current_user, None)
    res = client.post("/api/v1/workout-plans/generate", json={"training_days_per_week": 3})
    assert res.status_code == 401
    assert "Missing Bearer authentication token" in res.json()["detail"]


def test_generate_plan_invalid_token_rejected(client: TestClient):
    """POST /api/v1/workout-plans/generate rejects invalid or forged Bearer tokens (401)."""
    app.dependency_overrides.pop(get_current_user, None)
    res = client.post(
        "/api/v1/workout-plans/generate",
        headers={"Authorization": "Bearer invalid_forged_firebase_jwt"},
        json={"training_days_per_week": 3},
    )
    assert res.status_code == 401


def test_generate_plan_malformed_auth_header_rejected(client: TestClient):
    """POST /api/v1/workout-plans/generate rejects non-Bearer Authorization headers (401)."""
    app.dependency_overrides.pop(get_current_user, None)
    res = client.post(
        "/api/v1/workout-plans/generate",
        headers={"Authorization": "Basic dXNlcjpwYXNz"},
        json={"training_days_per_week": 3},
    )
    assert res.status_code == 401


def test_generate_plan_valid_auth_accepted(client: TestClient):
    """POST /api/v1/workout-plans/generate accepts valid authenticated user dependency (200)."""
    payload = {
        "target_goal": "general_fitness",
        "fitness_level": "intermediate",
        "environment": "gym",
        "training_days_per_week": 3,
        "plan_duration_weeks": 4,
        "target_workout_duration_minutes": 45,
    }
    res = client.post("/api/v1/workout-plans/generate", json=payload)
    assert res.status_code == 200
    plan = WorkoutPlanResponse.model_validate(res.json())
    assert plan.feasibilityCheckPassed is True
    assert plan.planId.startswith("plan_")


# =============================================================================
# Section B: Request Schema Validation (422 Unprocessable Entity)
# =============================================================================

def test_validation_invalid_training_days_bounds(client: TestClient):
    """Rejects training days outside 1-6 range with 422."""
    res_0 = client.post("/api/v1/workout-plans/generate", json={"training_days_per_week": 0})
    assert res_0.status_code == 422

    res_7 = client.post("/api/v1/workout-plans/generate", json={"training_days_per_week": 7})
    assert res_7.status_code == 422


def test_validation_invalid_plan_duration_weeks_bounds(client: TestClient):
    """Rejects duration weeks outside 1-12 range with 422."""
    res_0 = client.post("/api/v1/workout-plans/generate", json={"plan_duration_weeks": 0})
    assert res_0.status_code == 422

    res_13 = client.post("/api/v1/workout-plans/generate", json={"plan_duration_weeks": 13})
    assert res_13.status_code == 422


def test_validation_invalid_target_duration_minutes(client: TestClient):
    """Rejects workout duration outside 20-90 minutes with 422."""
    res_low = client.post("/api/v1/workout-plans/generate", json={"target_workout_duration_minutes": 15})
    assert res_low.status_code == 422

    res_high = client.post("/api/v1/workout-plans/generate", json={"target_workout_duration_minutes": 120})
    assert res_high.status_code == 422


def test_validation_invalid_enum_fields(client: TestClient):
    """Rejects unsupported goal or environment values with 422."""
    res_goal = client.post("/api/v1/workout-plans/generate", json={"target_goal": "become_superhero"})
    assert res_goal.status_code == 422

    res_env = client.post("/api/v1/workout-plans/generate", json={"environment": "underwater"})
    assert res_env.status_code == 422


def test_validation_malformed_json_payload(client: TestClient):
    """Rejects non-JSON body with 422."""
    res = client.post(
        "/api/v1/workout-plans/generate",
        content="not a json string",
        headers={"Content-Type": "application/json"},
    )
    assert res.status_code == 422


# =============================================================================
# Section C: Successful Generation Across Split & Duration Configurations
# =============================================================================

@pytest.mark.parametrize("days,expected_split", [
    (1, WorkoutSplitType.FULL_BODY),
    (2, WorkoutSplitType.FULL_BODY),
    (3, WorkoutSplitType.FULL_BODY),
    (4, WorkoutSplitType.UPPER_LOWER),
    (5, WorkoutSplitType.UPPER_LOWER),
    (6, WorkoutSplitType.PUSH_PULL_LEGS),
])
def test_successful_generation_all_day_splits(client: TestClient, days, expected_split):
    """Verifies generation succeeds for all allowed days (1 to 6) with correct split type."""
    payload = {
        "training_days_per_week": days,
        "environment": "gym",
        "plan_duration_weeks": 4,
    }
    res = client.post("/api/v1/workout-plans/generate", json=payload)
    assert res.status_code == 200
    plan = WorkoutPlanResponse.model_validate(res.json())
    assert plan.feasibilityCheckPassed is True
    assert plan.splitType == expected_split
    assert plan.trainingDaysPerWeek == days
    assert len(plan.weeks[0].days) == days


@pytest.mark.parametrize("weeks", [1, 4, 8, 12])
def test_successful_generation_various_week_durations(client: TestClient, weeks):
    """Verifies multi-week plans generate exact requested week count (1, 4, 8, 12)."""
    payload = {
        "training_days_per_week": 3,
        "environment": "gym",
        "plan_duration_weeks": weeks,
    }
    res = client.post("/api/v1/workout-plans/generate", json=payload)
    assert res.status_code == 200
    plan = WorkoutPlanResponse.model_validate(res.json())
    assert plan.totalWeeks == weeks
    assert len(plan.weeks) == weeks


# =============================================================================
# Section D: Response Schema Correctness
# =============================================================================

def test_response_structure_and_prescriptions(client: TestClient):
    """Validates complete presence of sets, reps, rest, RPE, rationales, and metrics in response."""
    payload = {
        "target_goal": "strength",
        "fitness_level": "intermediate",
        "environment": "gym",
        "training_days_per_week": 3,
        "plan_duration_weeks": 4,
        "target_workout_duration_minutes": 60,
    }
    res = client.post("/api/v1/workout-plans/generate", json=payload)
    assert res.status_code == 200
    plan = WorkoutPlanResponse.model_validate(res.json())

    assert plan.planId.startswith("plan_")
    assert plan.title is not None
    assert plan.description is not None
    assert plan.splitType == WorkoutSplitType.FULL_BODY
    assert plan.totalWeeks == 4
    assert plan.trainingDaysPerWeek == 3
    assert plan.appliedFilters.get("target_workout_duration_minutes") == 60
    assert plan.durationFeasibility in ("feasible", "potentially_over_target", "impossible_under_constraints")

    first_week = plan.weeks[0]
    assert first_week.weekNumber == 1
    assert first_week.phaseLabel is not None
    assert first_week.totalWeeklySets > 0
    assert first_week.totalWorkouts == 3

    first_day = first_week.days[0]
    assert len(first_day.exercises) >= 3
    assert first_day.estimatedDurationMinutes > 0
    assert first_day.totalSets > 0

    for ex in first_day.exercises:
        assert 0 <= ex.slotIndex <= 5
        assert ex.exerciseId is not None
        assert ex.name is not None
        assert ex.slotRole is not None
        assert ex.movementPattern is not None
        assert ex.totalSets >= 1
        assert len(ex.prescribedSets) == ex.totalSets
        for s in ex.prescribedSets:
            assert s.targetReps >= 1
            assert s.restSeconds >= 30
            assert s.targetRpe is not None
        assert ex.prescriptionRationale is not None
        assert len(ex.reasons) > 0


# =============================================================================
# Section E: Determinism & Idempotency
# =============================================================================

def test_api_determinism_identical_requests(client: TestClient):
    """Identical requests must yield identical planId and exact identical response body."""
    payload = {
        "training_days_per_week": 4,
        "plan_duration_weeks": 4,
        "target_goal": "muscle_gain",
        "environment": "gym",
        "fitness_level": "intermediate",
        "target_workout_duration_minutes": 45,
    }
    res1 = client.post("/api/v1/workout-plans/generate", json=payload)
    res2 = client.post("/api/v1/workout-plans/generate", json=payload)

    assert res1.status_code == 200
    assert res2.status_code == 200

    plan1 = WorkoutPlanResponse.model_validate(res1.json())
    plan2 = WorkoutPlanResponse.model_validate(res2.json())

    assert plan1.planId == plan2.planId
    assert json.dumps(res1.json(), sort_keys=True) == json.dumps(res2.json(), sort_keys=True)


# =============================================================================
# Section F: Constraint & Corrective Behavior
# =============================================================================

def test_api_equipment_constraint_filtering(client: TestClient):
    """Verifies selected exercises only utilize allowed equipment."""
    available = ["dumbbells", "bench"]
    payload = {
        "environment": "home",
        "available_equipment": available,
        "training_days_per_week": 3,
        "plan_duration_weeks": 4,
    }
    res = client.post("/api/v1/workout-plans/generate", json=payload)
    assert res.status_code == 200
    plan = WorkoutPlanResponse.model_validate(res.json())
    assert plan.feasibilityCheckPassed is True

    for day in plan.weeks[0].days:
        for ex in day.exercises:
            assert all(eq in available or eq == "bodyweight" for eq in ex.equipment)


def test_api_exercise_exclusion_filtering(client: TestClient):
    """Verifies explicitly excluded exercises are not allocated in any workout slot."""
    excluded = ["barbell_bench_press", "barbell_back_squat"]
    payload = {
        "environment": "gym",
        "training_days_per_week": 3,
        "plan_duration_weeks": 1,
        "excluded_exercise_ids": excluded,
    }
    res = client.post("/api/v1/workout-plans/generate", json=payload)
    assert res.status_code == 200
    plan = WorkoutPlanResponse.model_validate(res.json())
    assert plan.feasibilityCheckPassed is True

    for day in plan.weeks[0].days:
        for ex in day.exercises:
            assert ex.exerciseId not in excluded


def test_api_form_analysis_filter(client: TestClient):
    """Verifies form_analysis_supported_only=True generates a valid plan."""
    payload = {
        "environment": "gym",
        "training_days_per_week": 3,
        "plan_duration_weeks": 1,
        "form_analysis_supported_only": True,
    }
    res = client.post("/api/v1/workout-plans/generate", json=payload)
    assert res.status_code == 200
    plan = WorkoutPlanResponse.model_validate(res.json())
    assert plan.feasibilityCheckPassed is True


def test_api_duration_feasibility_values(client: TestClient):
    """Verifies durationFeasibility is correctly calculated and exposed."""
    payload_tight = {
        "environment": "gym",
        "training_days_per_week": 3,
        "plan_duration_weeks": 1,
        "target_workout_duration_minutes": 25,
    }
    res = client.post("/api/v1/workout-plans/generate", json=payload_tight)
    assert res.status_code == 200
    plan = WorkoutPlanResponse.model_validate(res.json())
    assert plan.durationFeasibility in ("feasible", "potentially_over_target", "impossible_under_constraints")
    assert plan.weeks[0].days[0].estimatedDurationMinutes > 0


def test_api_corrective_slot_0_integration(client: TestClient):
    """Verifies corrective source exercise and issue ID populates warmup_corrective at Slot 0."""
    payload = {
        "environment": "gym",
        "training_days_per_week": 3,
        "corrective_source_exercise_id": "ex_squat",
        "corrective_issue_id": "knee_tracking_deviation",
    }
    res = client.post("/api/v1/workout-plans/generate", json=payload)
    assert res.status_code == 200
    plan = WorkoutPlanResponse.model_validate(res.json())
    assert plan.feasibilityCheckPassed is True

    slot0 = plan.weeks[0].days[0].exercises[0]
    assert slot0.slotIndex == 0
    assert slot0.slotRole == ExerciseSlotRole.WARMUP_CORRECTIVE


def test_api_openapi_spec_registration():
    """Verifies the endpoint appears in FastAPI OpenAPI schema with correct HTTP method and schema."""
    schema = app.openapi()
    paths = schema.get("paths", {})
    endpoint = "/api/v1/workout-plans/generate"
    assert endpoint in paths, f"Expected {endpoint} in OpenAPI paths"
    assert "post" in paths[endpoint], f"Expected POST method for {endpoint}"
    post_op = paths[endpoint]["post"]
    assert post_op.get("summary") == "Generate deterministic multi-week workout plan"
    assert "Workout Plans" in post_op.get("tags", [])
    assert "200" in post_op.get("responses", {})
    assert "422" in post_op.get("responses", {})


# =============================================================================
# Section G: Domain Planner Diagnostics (State B, C, D as 200 OK)
# =============================================================================

def test_api_state_b_empty_equipment_returns_diagnostic(client: TestClient):
    """State B (empty equipment list) returns 200 OK with feasibilityCheckPassed=False and diagnostics."""
    payload = {
        "environment": "gym",
        "available_equipment": [],
        "training_days_per_week": 3,
    }
    res = client.post("/api/v1/workout-plans/generate", json=payload)
    assert res.status_code == 200
    plan = WorkoutPlanResponse.model_validate(res.json())
    assert plan.feasibilityCheckPassed is False
    assert plan.weeks == []
    assert len(plan.diagnostics) > 0


def test_api_state_c_conflicting_equipment_returns_diagnostic(client: TestClient):
    """State C (available and excluded equipment conflict) returns 200 OK with conflictingFilters."""
    payload = {
        "environment": "gym",
        "available_equipment": ["barbell"],
        "excluded_equipment": ["barbell"],
        "training_days_per_week": 3,
    }
    res = client.post("/api/v1/workout-plans/generate", json=payload)
    assert res.status_code == 200
    plan = WorkoutPlanResponse.model_validate(res.json())
    assert plan.feasibilityCheckPassed is False
    assert len(plan.conflictingFilters) > 0


def test_api_state_d_catalog_shortfall_returns_diagnostic(client: TestClient):
    """State D (heavy exclusions causing slot shortfall) returns 200 OK with Catalog Shortfall diagnostic."""
    payload = {
        "environment": "home",
        "available_equipment": ["resistance_bands"],
        "excluded_exercise_ids": ["band_squat", "band_chest_press", "band_row", "band_overhead_press"],
        "training_days_per_week": 3,
    }
    res = client.post("/api/v1/workout-plans/generate", json=payload)
    assert res.status_code == 200
    plan = WorkoutPlanResponse.model_validate(res.json())
    assert plan.feasibilityCheckPassed is False
    assert plan.title == "Catalog Shortfall"


# =============================================================================
# Section H: Error Handling & Security Boundary
# =============================================================================

def test_unexpected_internal_error_returns_clean_500(client: TestClient):
    """Verifies unexpected internal exceptions return clean 500 without leaking stack traces."""
    mock_service = MagicMock()
    mock_service.generate_periodized_plan.side_effect = RuntimeError("Database timeout / internal secret error at /var/secret")
    app.dependency_overrides[get_workout_periodization_service] = lambda: mock_service

    payload = {"training_days_per_week": 3}
    res = client.post("/api/v1/workout-plans/generate", json=payload)
    assert res.status_code == 500
    detail = res.json()["detail"]
    assert detail == "An unexpected error occurred during workout plan generation."
    assert "Database timeout" not in detail
    assert "/var/secret" not in detail


def test_request_body_user_id_cannot_influence_auth(client: TestClient):
    """Ensures user ID fields in request body are ignored and cannot impersonate other users."""
    payload = {
        "training_days_per_week": 3,
        "uid": "victim_user_123",
        "userId": "impersonated_user_456",
        "firebaseUid": "admin_hacked",
    }
    res = client.post("/api/v1/workout-plans/generate", json=payload)
    assert res.status_code == 200
    plan = WorkoutPlanResponse.model_validate(res.json())
    assert plan.feasibilityCheckPassed is True
    # The response does not reflect the injected user IDs
    assert "victim_user_123" not in json.dumps(res.json())


def test_api_no_gemini_firestore_imports():
    """Verifies endpoint and router have zero imports of Gemini, Firestore, or network libraries."""
    import backend.app.api.v1.endpoints.workout_plans as ep_mod
    import backend.app.api.v1.workout_plans as wp_mod

    for mod in [ep_mod, wp_mod]:
        source = open(mod.__file__, "r", encoding="utf-8").read()
        forbidden = [
            "google.generativeai",
            "firebase_admin.firestore",
            "google.cloud.firestore",
            "requests",
            "httpx",
            "random.choice",
            "uuid.uuid4",
        ]
        for f in forbidden:
            assert f not in source, f"Forbidden import '{f}' detected in {mod.__name__}"
