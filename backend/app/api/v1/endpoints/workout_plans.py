"""
Deterministic Workout Plan Generation API (Phase 9B.8.5.4).

Exposes the authenticated, read-only endpoint:
POST /api/v1/workout-plans/generate

Architectural Rules:
- Authenticates via existing Firebase token dependency (get_current_user).
- Pure deterministic execution: Zero Gemini, Zero LLM, Zero Vector DB.
- Read-only execution: Zero Firestore reads, Zero Firestore writes.
- Consumes WorkoutPlanGenerateRequest and returns WorkoutPlanResponse.
- Thin router boundary: delegates directly to WorkoutPeriodizationService.
"""

from fastapi import APIRouter, Body, Depends, HTTPException, status
from backend.app.core.security import get_current_user, CurrentUser
from backend.app.schemas.workout_plan import (
    WorkoutPlanGenerateRequest,
    WorkoutPlanResponse,
)
from backend.app.services.workout_periodization_service import (
    WorkoutPeriodizationService,
    get_workout_periodization_service,
)
from backend.app.utils.logger import logger

router = APIRouter()


@router.post(
    "/generate",
    response_model=WorkoutPlanResponse,
    summary="Generate deterministic multi-week workout plan",
    description=(
        "Generates a deterministic multi-day, multi-week workout plan with periodization, "
        "progression, deload logic, and duration feasibility based strictly on provided parameters. "
        "Stateless and read-only: zero database writes, zero Firestore calls, zero Gemini/LLM dependency."
    ),
    responses={
        200: {
            "description": "Deterministic workout plan generated successfully, or domain diagnostic shortfall (State B/C/D).",
        },
        401: {
            "description": "Unauthorized - Missing or invalid Firebase authentication token.",
        },
        422: {
            "description": "Unprocessable Entity - Request payload failed schema validation.",
        },
        500: {
            "description": "Internal Server Error - Unexpected server failure.",
        },
    },
)
async def generate_workout_plan(
    request: WorkoutPlanGenerateRequest = Body(
        ...,
        openapi_examples={
            "standard_muscle_gain": {
                "summary": "4-Day Muscle Gain Plan",
                "description": "Standard 4-day gym plan focusing on muscle gain with dumbbells and bench.",
                "value": {
                    "target_goal": "muscle_gain",
                    "fitness_level": "intermediate",
                    "environment": "gym",
                    "available_equipment": ["dumbbells", "bench"],
                    "training_days_per_week": 4,
                    "plan_duration_weeks": 4,
                    "target_workout_duration_minutes": 45,
                },
            },
            "general_fitness_full_body": {
                "summary": "3-Day Full Body Plan",
                "description": "Standard 3-day general fitness plan for gym with default equipment.",
                "value": {
                    "target_goal": "general_fitness",
                    "fitness_level": "intermediate",
                    "environment": "gym",
                    "training_days_per_week": 3,
                    "plan_duration_weeks": 4,
                    "target_workout_duration_minutes": 45,
                },
            },
        },
    ),
    current_user: CurrentUser = Depends(get_current_user),
    service: WorkoutPeriodizationService = Depends(get_workout_periodization_service),
) -> WorkoutPlanResponse:
    """
    Generates a deterministic multi-week workout plan for the verified user.
    Personalization is derived strictly from the request body; user profile and Firestore
    are not read or queried.
    """
    try:
        return service.generate_periodized_plan(request)
    except HTTPException:
        raise
    except Exception as exc:
        logger.error(f"Unexpected error in workout plan generation endpoint: {exc}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="An unexpected error occurred during workout plan generation.",
        )
