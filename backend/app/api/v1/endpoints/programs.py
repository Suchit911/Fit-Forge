"""
Program Lifecycle & Adaptive Prescription API Endpoints (Phases 9C.3 & 9C.4).

Provides authenticated REST endpoints for user-scoped program and mesocycle lifecycle management:
- POST /api/v1/programs/start: Start a persistent program from a generated plan
- GET  /api/v1/programs/active: Get current active program for user
- POST /api/v1/programs/active/sync-session: Synchronize completed workout session
- POST /api/v1/programs/active/abandon: Abandon active program preserving history
- POST /api/v1/programs/active/adaptation: Record adaptation audit decision
- GET  /api/v1/programs/active/prescription/{week}/{day}: Get effective future workout prescription (Phase 9C.4)
- POST /api/v1/programs/active/apply-adaptation: Atomically apply 9C.2 adaptation decision (Phase 9C.4)
- GET  /api/v1/programs/active/versions: Get version and adaptation audit history (Phase 9C.4)
- GET  /api/v1/programs/{program_id}: Get specific program by ID
"""

from typing import Optional, Dict, Any
from fastapi import APIRouter, Depends, HTTPException, status

from ....core.security import get_current_user, CurrentUser
from ....schemas.program import (
    ProgramResponse,
    ProgramStartRequest,
    ProgramSyncSessionRequest,
    ProgramAbandonRequest,
    EffectivePrescriptionResponse,
    ApplyAdaptationRequest,
    ApplyAdaptationResponse,
    ProgramVersionsResponse,
)
from ....services.program_service import (
    ProgramService,
    get_program_service,
)
from ....services.adaptation_application_service import (
    AdaptationApplicationService,
    get_adaptation_application_service,
)
from ....utils.logger import logger

router = APIRouter()


@router.post(
    "/start",
    response_model=ProgramResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Start an Active Program from a Generated Plan",
)
async def start_program(
    request: ProgramStartRequest,
    current_user: CurrentUser = Depends(get_current_user),
    service: ProgramService = Depends(get_program_service),
) -> ProgramResponse:
    """
    Starts a new persistent workout program / mesocycle for the authenticated user.
    Enforces the single-active-program constraint: returns 409 Conflict if an active program exists.
    Stores the full resolved generated plan snapshot immutably under users/{uid}/programs/{program_id}.
    """
    return service.start_program(current_user.uid, request)


@router.get(
    "/active",
    response_model=ProgramResponse,
    status_code=status.HTTP_200_OK,
    summary="Get User's Current Active Program",
)
async def get_active_program(
    current_user: CurrentUser = Depends(get_current_user),
    service: ProgramService = Depends(get_program_service),
) -> ProgramResponse:
    """
    Retrieves the user's currently active workout program.
    Returns 404 if the user has no active program.
    """
    return service.get_active_program(current_user.uid)


@router.post(
    "/active/sync-session",
    response_model=ProgramResponse,
    status_code=status.HTTP_200_OK,
    summary="Synchronize Completed Workout Session to Active Program",
)
async def sync_completed_session(
    request: ProgramSyncSessionRequest,
    current_user: CurrentUser = Depends(get_current_user),
    service: ProgramService = Depends(get_program_service),
) -> ProgramResponse:
    """
    Synchronizes a completed workout session with the active program.
    Idempotent: repeating sync for the same session ID will not duplicate records or re-advance position.
    Deterministic advancement: advances current week and day to the earliest incomplete planned workout.
    Transitions program status to 'completed' when all planned workouts are finished.
    """
    return service.sync_session(current_user.uid, request)


@router.post(
    "/active/abandon",
    response_model=ProgramResponse,
    status_code=status.HTTP_200_OK,
    summary="Abandon Active Program",
)
async def abandon_active_program(
    request: Optional[ProgramAbandonRequest] = None,
    current_user: CurrentUser = Depends(get_current_user),
    service: ProgramService = Depends(get_program_service),
) -> ProgramResponse:
    """
    Transitions the active program to 'abandoned' status without deleting workout history,
    completed sessions, or adaptation audit records.
    """
    return service.abandon_active_program(current_user.uid, request)


@router.post(
    "/active/adaptation",
    response_model=ProgramResponse,
    status_code=status.HTTP_200_OK,
    summary="Record Adaptation Decision into Active Program History",
)
async def record_adaptation_decision(
    decision: Dict[str, Any],
    current_user: CurrentUser = Depends(get_current_user),
    service: ProgramService = Depends(get_program_service),
) -> ProgramResponse:
    """
    Appends an evaluated adaptation decision to the active program's adaptationHistory.
    Idempotent by decisionId. Does NOT alter future workout prescriptions.
    """
    updated = service.record_adaptation_decision(current_user.uid, decision)
    if not updated:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="No active program found to record adaptation decision.",
        )
    return updated


# =============================================================================
# Phase 9C.4: Adaptive Prescription & Plan Versioning Endpoints
# =============================================================================

@router.get(
    "/active/prescription/{week}/{day}",
    response_model=EffectivePrescriptionResponse,
    status_code=status.HTTP_200_OK,
    summary="Get Current Effective Workout Prescription for Week/Day",
)
async def get_effective_prescription(
    week: int,
    day: int,
    current_user: CurrentUser = Depends(get_current_user),
    service: AdaptationApplicationService = Depends(get_adaptation_application_service),
) -> EffectivePrescriptionResponse:
    """
    Returns the current effective prescription for a specified week and day of the active program.
    If adapted, reflects approved adaptations (e.g. +2.5 kg load, -1 set) while preserving
    original planSnapshot and completed history intact.
    """
    return service.get_effective_prescription(current_user.uid, week, day)


@router.post(
    "/active/apply-adaptation",
    response_model=ApplyAdaptationResponse,
    status_code=status.HTTP_200_OK,
    summary="Apply Deterministic Adaptation Decision to Future Workouts",
)
async def apply_adaptation(
    request: ApplyAdaptationRequest,
    current_user: CurrentUser = Depends(get_current_user),
    service: AdaptationApplicationService = Depends(get_adaptation_application_service),
) -> ApplyAdaptationResponse:
    """
    Atomically applies an approved Phase 9C.2 adaptation decision to future workouts
    in the active program.
    Idempotent: repeating the same decisionId returns 'already_applied' with zero mutation.
    Increments planVersion (1 -> 2 -> 3) and records audit trail in adaptationHistory.
    """
    return service.apply_adaptation(current_user.uid, request)


@router.get(
    "/active/versions",
    response_model=ProgramVersionsResponse,
    status_code=status.HTTP_200_OK,
    summary="Get Active Program Versions and Adaptation Audit Trail",
)
async def get_program_versions(
    current_user: CurrentUser = Depends(get_current_user),
    service: AdaptationApplicationService = Depends(get_adaptation_application_service),
) -> ProgramVersionsResponse:
    """
    Returns the current programVersion, planVersion, total applied adaptations,
    and full adaptation audit history.
    """
    return service.get_program_versions(current_user.uid)


@router.get(
    "/{program_id}",
    response_model=ProgramResponse,
    status_code=status.HTTP_200_OK,
    summary="Get Specific Program by ID",
)
async def get_program_by_id(
    program_id: str,
    current_user: CurrentUser = Depends(get_current_user),
    service: ProgramService = Depends(get_program_service),
) -> ProgramResponse:
    """
    Retrieves any program (active, completed, or abandoned) belonging to the authenticated user.
    """
    return service.get_program_by_id(current_user.uid, program_id)

