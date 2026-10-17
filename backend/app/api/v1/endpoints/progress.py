from typing import List
from fastapi import APIRouter, Depends, Query
from ....core.security import get_current_user, CurrentUser
from ....schemas.progress import (
    ProgressPeriod,
    ProgressSummaryResponse,
    ProgressDashboardResponse,
    StrengthProgressPointSchema,
    ExerciseProgressionResponse,
)
from ....services.progress_service import ProgressService, get_progress_service

router = APIRouter()


@router.get("/summary", response_model=ProgressSummaryResponse, summary="Get high-level progress summary & consistency")
async def get_progress_summary(
    period: ProgressPeriod = Query("30d", description="Time period filter: 7d, 30d, 90d, or all"),
    current_user: CurrentUser = Depends(get_current_user),
    service: ProgressService = Depends(get_progress_service),
):
    """
    Returns aggregated workout statistics, volume, calories, duration,
    and consecutive consistency streak for the authenticated user.
    """
    return service.get_summary(current_user.uid, period=period)


@router.get("/dashboard", response_model=ProgressDashboardResponse, summary="Get full progress dashboard view")
async def get_progress_dashboard(
    period: ProgressPeriod = Query("30d", description="Time period filter: 7d, 30d, 90d, or all"),
    current_user: CurrentUser = Depends(get_current_user),
    service: ProgressService = Depends(get_progress_service),
):
    """
    Returns comprehensive progress dashboard metrics including KPIs, strength progression,
    body composition stats, muscle group changes, personal records, and recent workouts.
    """
    return service.get_dashboard_data(current_user.uid, period=period)


@router.get("/volume", response_model=List[StrengthProgressPointSchema], summary="Get volume and strength progression time series")
async def get_volume_time_series(
    period: ProgressPeriod = Query("30d", description="Time period filter: 7d, 30d, 90d, or all"),
    current_user: CurrentUser = Depends(get_current_user),
    service: ProgressService = Depends(get_progress_service),
):
    """
    Returns daily upper body, lower body, and total volume time-series progression.
    """
    return service.get_volume_time_series(current_user.uid, period=period)


@router.get("/exercises/{exercise_id}", response_model=ExerciseProgressionResponse, summary="Get exercise specific progression & PR history")
async def get_exercise_progression(
    exercise_id: str,
    current_user: CurrentUser = Depends(get_current_user),
    service: ProgressService = Depends(get_progress_service),
):
    """
    Returns historical 1RM, weight, reps, and PR milestones for a single exercise.
    """
    return service.get_exercise_progression(current_user.uid, exercise_id)
