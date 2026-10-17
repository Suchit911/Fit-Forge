from typing import List, Optional
from fastapi import APIRouter, Depends, HTTPException, Query, status
from ....core.security import get_current_user, CurrentUser
from ....schemas.workout import (
    WorkoutSchema,
    WorkoutSessionCreate,
    WorkoutSessionUpdate,
    WorkoutSessionComplete,
    WorkoutSessionResponse,
)
from ....schemas.user import Environment, DifficultyLevel
from ....repositories.workout_repository import WorkoutRepository, get_workout_repository
from ....services.workout_service import WorkoutService, get_workout_service

router = APIRouter()


# =============================================================================
# GLOBAL / REFERENCE WORKOUTS
# =============================================================================

@router.get("", response_model=List[WorkoutSchema], summary="List available workouts")
async def list_workouts(
    environment: Optional[Environment] = Query(None, description="Filter by environment (gym/home)"),
    difficulty: Optional[DifficultyLevel] = Query(None, description="Filter by difficulty"),
    search: Optional[str] = Query(None, description="Search term for title or description"),
    repo: WorkoutRepository = Depends(get_workout_repository),
):
    """
    Returns workout routines matching the provided filters.
    """
    return repo.list_workouts(environment=environment, difficulty=difficulty, search=search)


@router.get("/today", response_model=WorkoutSchema, summary="Get today's featured workout")
async def get_today_workout(
    repo: WorkoutRepository = Depends(get_workout_repository),
):
    """
    Returns the designated routine for today (defaults to first available workout).
    """
    return repo.get_today_workout("default_user")


# =============================================================================
# USER WORKOUT SESSIONS & HISTORY (AUTHENTICATED)
# =============================================================================

@router.get("/history", response_model=List[WorkoutSessionResponse], summary="Get authenticated user's workout history")
async def get_workout_history(
    limit: int = Query(20, ge=1, le=100, description="Maximum number of historical sessions"),
    current_user: CurrentUser = Depends(get_current_user),
    repo: WorkoutRepository = Depends(get_workout_repository),
):
    """
    Retrieves completed workout sessions for the verified user UID.
    Cross-user access is blocked; only sessions belonging to current_user.uid are returned.
    """
    return repo.list_user_history(current_user.uid, limit=limit)


@router.get("/sessions/active", response_model=Optional[WorkoutSessionResponse], summary="Get current in-progress workout session")
async def get_active_session(
    current_user: CurrentUser = Depends(get_current_user),
    repo: WorkoutRepository = Depends(get_workout_repository),
):
    """
    Retrieves the currently in-progress workout session for the authenticated user, or null if none.
    """
    return repo.get_active_session(current_user.uid)


@router.get("/sessions/{session_id}", response_model=WorkoutSessionResponse, summary="Get workout session by ID")
async def get_session_detail(
    session_id: str,
    current_user: CurrentUser = Depends(get_current_user),
    repo: WorkoutRepository = Depends(get_workout_repository),
):
    """
    Retrieves a specific workout session.
    Returns 404 if not found or if the session does not belong to the authenticated user.
    """
    session = repo.get_session(current_user.uid, session_id)
    if not session:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Workout session not found.",
        )
    return session


@router.patch("/sessions/{session_id}", response_model=WorkoutSessionResponse, summary="Update active workout progress or record sets")
async def update_session_progress(
    session_id: str,
    updates: WorkoutSessionUpdate,
    current_user: CurrentUser = Depends(get_current_user),
    repo: WorkoutRepository = Depends(get_workout_repository),
):
    """
    Updates progress (exercise index, set index, elapsed seconds, completed sets) for an active session.
    Strictly verifies ownership: a user can only update their own session.
    """
    updated = repo.update_session(current_user.uid, session_id, updates)
    if not updated:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Workout session not found or you do not have permission to update it.",
        )
    return updated


@router.post("/sessions/{session_id}/complete", response_model=WorkoutSessionResponse, summary="Complete workout session")
async def complete_workout_session(
    session_id: str,
    complete_data: WorkoutSessionComplete,
    current_user: CurrentUser = Depends(get_current_user),
    service: WorkoutService = Depends(get_workout_service),
):
    """
    Marks a session as completed, records completion timestamp, and coordinates secondary notifications and evaluations.
    """
    completed = service.complete_session(current_user.uid, session_id, complete_data)
    if not completed:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Workout session not found or you do not have permission to complete it.",
        )
    return completed


@router.post("/{workout_id}/sessions", response_model=WorkoutSessionResponse, status_code=status.HTTP_201_CREATED, summary="Start a new workout session")
async def start_workout_session(
    workout_id: str,
    session_in: Optional[WorkoutSessionCreate] = None,
    current_user: CurrentUser = Depends(get_current_user),
    repo: WorkoutRepository = Depends(get_workout_repository),
):
    """
    Creates a new in-progress workout session document under users/{current_user.uid}/workout_sessions.
    The UID is strictly determined from the verified Firebase ID token.
    """
    # Verify workout exists (allow "generated" for ephemeral generated-plan execution)
    workout = repo.get_by_id(workout_id)
    if not workout and workout_id != "generated":
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Workout with ID '{workout_id}' does not exist.",
        )

    payload = session_in or WorkoutSessionCreate(workoutId=workout_id)
    payload.workoutId = workout_id  # Enforce URL param

    return repo.create_session(current_user.uid, payload)


@router.get("/{workout_id}", response_model=WorkoutSchema, summary="Get workout details by ID")
async def get_workout(
    workout_id: str,
    repo: WorkoutRepository = Depends(get_workout_repository),
):
    """
    Retrieves full workout details including embedded exercises and target sets.
    """
    workout = repo.get_by_id(workout_id)
    if not workout:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Workout with ID '{workout_id}' was not found in the library.",
        )
    return workout
