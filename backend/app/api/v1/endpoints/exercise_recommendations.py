"""
Deterministic Exercise Recommendation Endpoints (Phase 9B.8.4).

Exposes the read-only recommendation endpoint:
POST /api/v1/exercises/recommendations

Zero CRUD, zero user writes, zero Firestore persistence, zero Gemini/LLM dependency.
"""

from fastapi import APIRouter, Depends
from backend.app.schemas.exercise import (
    ExerciseRecommendationRequest,
    ExerciseRecommendationResponse,
)
from backend.app.services.exercise_recommendation_service import (
    ExerciseRecommendationService,
    get_exercise_recommendation_service,
)

router = APIRouter()


@router.post(
    "",
    response_model=ExerciseRecommendationResponse,
    summary="Get personalized deterministic exercise recommendations",
    description=(
        "Executes deterministic candidate generation, hard eligibility filtering, "
        "intent-aware scoring, and stable tie-breaking across the 100-exercise catalog "
        "and relationship graph. Read-only: zero database writes, zero Gemini/LLM calls."
    ),
)
@router.post(
    "/",
    response_model=ExerciseRecommendationResponse,
    include_in_schema=False,
)
async def get_recommendations(
    request: ExerciseRecommendationRequest,
    service: ExerciseRecommendationService = Depends(get_exercise_recommendation_service),
) -> ExerciseRecommendationResponse:
    """Computes deterministic exercise recommendations matching the request query."""
    return service.recommend(request)
