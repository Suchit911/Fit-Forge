"""
Personalization Signals & Adaptive Analytics API Endpoints (Phase 9C.1).

Provides read-only, authenticated access to the deterministic personalization signals
and performance analytics computed from completed workout history and form analysis.

Endpoints:
- GET /api/v1/personalization/signals: Comprehensive signals snapshot for authenticated user.
- GET /api/v1/personalization/exercises/{exercise_id}: Specific exercise performance summary.

Strict Invariants:
1. Read-Only: No mutations to user programs, workout plans, or session state.
2. User-Scoped: Strictly isolated to verified Firebase UID (CurrentUser).
3. Grounded: Exposes only signals backed by authoritative completed sessions.
"""

from typing import Optional
from fastapi import APIRouter, Depends, Query, HTTPException, status

from ....core.security import get_current_user, CurrentUser
from ....schemas.personalization import (
    PersonalizationSignalsResponse,
    ExercisePerformanceSummary,
)
from ....schemas.adaptation import (
    AdaptationEvaluationRequest,
    AdaptationEvaluationResponse,
)
from ....services.personalization_signal_service import (
    PersonalizationSignalService,
    get_personalization_signal_service,
)
from ....services.adaptation_engine_service import (
    AdaptationEngineService,
    get_adaptation_engine_service,
)

router = APIRouter()


@router.get(
    "/signals",
    response_model=PersonalizationSignalsResponse,
    summary="Get Authenticated User's Personalization Signals",
)
async def get_personalization_signals(
    window_days: int = Query(28, ge=7, le=90, description="Observation window in days for frequency and adherence (default 28)"),
    current_user: CurrentUser = Depends(get_current_user),
    service: PersonalizationSignalService = Depends(get_personalization_signal_service),
) -> PersonalizationSignalsResponse:
    """
    Returns deterministic personalization signals including load progression,
    rep completion, set adherence, frequency consistency, and CV form findings.
    """
    return service.get_personalization_signals(current_user.uid, window_days=window_days)


@router.get(
    "/exercises/{exercise_id}",
    response_model=ExercisePerformanceSummary,
    summary="Get Specific Exercise Performance Signals",
)
async def get_exercise_performance_signal(
    exercise_id: str,
    current_user: CurrentUser = Depends(get_current_user),
    service: PersonalizationSignalService = Depends(get_personalization_signal_service),
) -> ExercisePerformanceSummary:
    """
    Returns detailed historical performance analytics, load progression trend,
    and rep completion rates for a single canonical exercise.
    """
    summary = service.get_exercise_performance_signal(current_user.uid, exercise_id)
    if not summary:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"No completed workout data found for exercise '{exercise_id}'.",
        )
    return summary


# =============================================================================
# Phase 9C.2: Deterministic Adaptation & Progression Decision Endpoints
# =============================================================================

@router.get(
    "/adaptations",
    response_model=AdaptationEvaluationResponse,
    summary="Get Evaluated Workout Adaptations for Authenticated User",
)
async def get_workout_adaptations(
    window_days: int = Query(28, ge=7, le=90, description="Evaluation observation window in days (default 28)"),
    current_user: CurrentUser = Depends(get_current_user),
    engine_service: AdaptationEngineService = Depends(get_adaptation_engine_service),
) -> AdaptationEvaluationResponse:
    """
    Returns deterministic, bounded adaptation decisions across all tracked exercises
    and mesocycle adherence patterns for the authenticated user. Read-only.
    """
    request = AdaptationEvaluationRequest(windowDays=window_days)
    return engine_service.evaluate_adaptations(current_user.uid, request=request)


@router.post(
    "/adaptations/evaluate",
    response_model=AdaptationEvaluationResponse,
    summary="Evaluate Adaptations for Specific Candidate Workout Context",
)
async def evaluate_workout_adaptations(
    request: AdaptationEvaluationRequest,
    current_user: CurrentUser = Depends(get_current_user),
    engine_service: AdaptationEngineService = Depends(get_adaptation_engine_service),
) -> AdaptationEvaluationResponse:
    """
    Evaluates bounded adaptation decisions against specific candidate exercises or
    workout constraints. Read-only: does NOT mutate active programs or session state.
    """
    return engine_service.evaluate_adaptations(current_user.uid, request=request)

