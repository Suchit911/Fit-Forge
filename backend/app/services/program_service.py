"""
Program Service (Phase 9C.3).

Orchestrates mesocycle lifecycle management for user workout programs:
- Starting active programs with immutable plan snapshots
- Single active program constraint enforcement (409 Conflict)
- Document size threshold verification (< 800 KB)
- Idempotent session synchronization
- Deterministic progression (currentWeek / currentDay advancement)
- Resilient out-of-order session handling without skipping uncompleted days
- Program completion when all planned sessions are finished
- Non-destructive program abandonment preserving full history
- Adaptation audit history logging keyed by decisionId
"""

import json
import uuid
from datetime import datetime, timezone
from typing import Optional, List, Dict, Any, Tuple
from fastapi import HTTPException, status

from ..repositories.program_repository import ProgramRepository, get_program_repository
from ..repositories.workout_repository import WorkoutRepository, get_workout_repository
from ..schemas.program import (
    ProgramDocument,
    ProgramResponse,
    ProgramCompletedWorkout,
    ProgramStartRequest,
    ProgramSyncSessionRequest,
    ProgramAbandonRequest,
    MAX_PROGRAM_DOC_BYTES,
    PROGRAM_VERSION,
    PROGRAM_SCHEMA_VERSION,
)
from ..schemas.workout_plan import (
    WorkoutPlanResponse,
    PLANNER_VERSION,
)
from ..utils.logger import logger


_SENTINEL = object()


class ProgramService:
    """
    Business logic service for workout program lifecycles.
    """

    def __init__(
        self,
        program_repo: Any = _SENTINEL,
        workout_repo: Any = _SENTINEL,
    ):
        self._program_repo: ProgramRepository = (
            program_repo if program_repo is not _SENTINEL else get_program_repository()
        )
        self._workout_repo: WorkoutRepository = (
            workout_repo if workout_repo is not _SENTINEL else get_workout_repository()
        )

    # =========================================================================
    # START PROGRAM
    # =========================================================================

    def start_program(self, uid: str, request: ProgramStartRequest) -> ProgramResponse:
        """
        Starts a persistent program for the authenticated user from a generated plan.
        Enforces single active program constraint (HTTP 409 Conflict).
        Validates serialized document size against 800 KB bounded threshold.
        """
        if not uid or not uid.strip():
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Authentication required to start a program.",
            )

        # 1. Single active program check
        active = self._program_repo.get_active_program(uid)
        if active and active.status == "active":
            raise HTTPException(
                status_code=status.HTTP_409_CONFLICT,
                detail=(
                    f"An active program ('{active.title}', id: {active.programId}) already exists. "
                    "Complete or abandon the current active program before starting a new one."
                ),
            )

        plan = request.plan
        if not plan or not plan.weeks or plan.totalWeeks < 1:
            raise HTTPException(
                status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
                detail="Invalid generated plan: plan must contain at least 1 week.",
            )

        # 2. Count planned non-rest training days
        total_planned = sum(
            sum(1 for day in week.days if not day.isRestDay)
            for week in plan.weeks
        )
        if total_planned == 0:
            raise HTTPException(
                status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
                detail="Invalid generated plan: plan contains zero training days.",
            )

        # 3. Find initial active week and day (first non-rest training day)
        initial_week = 1
        initial_day = 1
        for week in plan.weeks:
            for day in week.days:
                if not day.isRestDay:
                    initial_week = week.weekNumber
                    initial_day = day.dayNumber
                    break
            break

        now_iso = datetime.now(timezone.utc).isoformat()
        program_id = f"prog_{datetime.now(timezone.utc).strftime('%Y%m%d%H%M%S')}_{uuid.uuid4().hex[:6]}"
        program_title = request.title or plan.title or "Active Mesocycle"

        # 4. Construct candidate program document
        candidate_data: Dict[str, Any] = {
            "programId": program_id,
            "userId": uid,
            "planId": plan.planId,
            "title": program_title,
            "status": "active",
            "splitType": plan.splitType,
            "totalWeeks": plan.totalWeeks,
            "daysPerWeek": plan.trainingDaysPerWeek,
            "currentWeek": initial_week,
            "currentDay": initial_day,
            "startedAt": now_iso,
            "updatedAt": now_iso,
            "completedAt": None,
            "abandonedAt": None,
            "completedWorkouts": [],
            "totalPlannedWorkouts": total_planned,
            "adaptationHistory": [],
            "planSnapshot": plan.model_dump(),
            "effectivePlanSnapshot": plan.model_dump(),
            "planVersion": 1,
            "pendingNextBlockSplit": None,
            "createdFrom": request.createdFrom or "generated_plan",
            "programVersion": PROGRAM_VERSION,
            "programSchemaVersion": PROGRAM_SCHEMA_VERSION,
            "planSchemaVersion": plan.appliedFilters.get("planner_version", PLANNER_VERSION),
        }

        # 5. Document size threshold validation (< 800 KB)
        try:
            serialized = json.dumps(candidate_data, default=str)
            raw_bytes_len = len(serialized.encode("utf-8"))
            if raw_bytes_len > MAX_PROGRAM_DOC_BYTES:
                raise HTTPException(
                    status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
                    detail=(
                        f"Plan snapshot size exceeds maximum allowable document threshold "
                        f"({raw_bytes_len} bytes > {MAX_PROGRAM_DOC_BYTES} bytes limit)."
                    ),
                )
        except (TypeError, ValueError) as e:
            logger.error(f"Serialization check error for candidate program: {e}")

        try:
            created = self._program_repo.create_program(uid, candidate_data)
            logger.info(f"Successfully started program '{program_id}' for user '{uid}'.")
            return created
        except ValueError as e:
            raise HTTPException(
                status_code=status.HTTP_409_CONFLICT,
                detail=str(e),
            )

    # =========================================================================
    # GET ACTIVE PROGRAM
    # =========================================================================

    def get_active_program(self, uid: str) -> ProgramResponse:
        """
        Retrieves the active program for the authenticated user.
        Raises HTTP 404 if no active program exists.
        """
        if not uid or not uid.strip():
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Authentication required.",
            )

        active = self._program_repo.get_active_program(uid)
        if not active or active.status != "active":
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="No active workout program found for this user.",
            )
        return active

    def get_program_by_id(self, uid: str, program_id: str) -> ProgramResponse:
        """
        Retrieves any program (active, completed, or abandoned) belonging to the user.
        """
        if not uid or not uid.strip():
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Authentication required.",
            )

        program = self._program_repo.get_program(uid, program_id)
        if not program:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Program '{program_id}' not found.",
            )
        return program

    # =========================================================================
    # SYNC COMPLETED SESSION
    # =========================================================================

    def sync_session(self, uid: str, request: ProgramSyncSessionRequest) -> ProgramResponse:
        """
        Synchronizes a completed workout session with the active program.
        Requirements:
        - Authenticated user
        - Active program must exist
        - Session must belong to user and be completed
        - Session must match active program / plan if metadata exists
        - Idempotent: repeated sync returns current state without re-advancing pointer
        - Deterministic pointer advancement based on earliest incomplete planned workout
        - Transitions to completed status when all planned workouts are completed
        """
        if not uid or not uid.strip():
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Authentication required.",
            )

        # 1. Retrieve active program
        active = self._program_repo.get_active_program(uid)
        if not active or active.status != "active":
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="No active workout program found to synchronize session with.",
            )

        # 2. Retrieve session and validate ownership
        session = self._workout_repo.get_session(uid, request.sessionId)
        if not session:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Workout session '{request.sessionId}' not found for user.",
            )

        if session.userId != uid:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Workout session does not belong to authenticated user.",
            )

        if session.status != "completed":
            raise HTTPException(
                status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
                detail=(
                    f"Workout session '{request.sessionId}' has status '{session.status}'. "
                    "Only completed sessions can be synchronized to an active program."
                ),
            )

        # 3. Validate unambiguous program session affinity (Behavior A)
        # Session MUST have program affinity: either matching programId or matching planId (or both)
        if not session.programId and not session.planId:
            raise HTTPException(
                status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
                detail=(
                    f"Workout session '{session.id}' lacks program affinity (neither programId nor planId is present). "
                    "Unassociated sessions or standard catalog workouts cannot be synchronized to an active program."
                ),
            )

        if session.programId and session.programId != active.programId:
            raise HTTPException(
                status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
                detail=(
                    f"Session belongs to program '{session.programId}', "
                    f"which does not match active program '{active.programId}'."
                ),
            )

        if session.planId and session.planId != active.planId:
            raise HTTPException(
                status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
                detail=(
                    f"Session was generated for plan '{session.planId}', "
                    f"which does not match active program plan '{active.planId}'."
                ),
            )

        # 4. Idempotency check: if session already synchronized, return program as-is
        for cw in active.completedWorkouts:
            if cw.sessionId == request.sessionId:
                logger.info(
                    f"Session '{request.sessionId}' already synchronized to program '{active.programId}'. "
                    "Returning current program state idempotently."
                )
                return active

        # 5. Authoritative Week/Day Resolution (Order of Authority)
        # 1. Active program's immutable planSnapshot
        # 2. Authoritative workout session metadata (session.weekNumber, session.dayNumber)
        # 3. Derived plan position from session metadata or notes
        # 4. Client weekNumber/dayNumber only as an optional consistency assertion
        auth_week = session.weekNumber
        auth_day = session.dayNumber

        # If not present as direct fields, attempt deterministic extraction from session notes
        if (auth_week is None or auth_day is None) and session.notes:
            import re
            w_match = re.search(r"Week\s*(\d+)", session.notes)
            d_match = re.search(r"Day\s*(\d+)", session.notes)
            if w_match and auth_week is None:
                auth_week = int(w_match.group(1))
            if d_match and auth_day is None:
                auth_day = int(d_match.group(1))

        if auth_week is None or auth_day is None:
            raise HTTPException(
                status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
                detail=(
                    f"Workout session '{session.id}' lacks authoritative weekNumber or dayNumber metadata. "
                    "Client cannot fabricate week/day assignment for an unassigned session."
                ),
            )

        # Validate client consistency assertion if supplied
        if request.weekNumber is not None and request.weekNumber != auth_week:
            raise HTTPException(
                status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
                detail=(
                    f"Client consistency assertion weekNumber ({request.weekNumber}) conflicts with "
                    f"authoritative session weekNumber ({auth_week})."
                ),
            )

        if request.dayNumber is not None and request.dayNumber != auth_day:
            raise HTTPException(
                status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
                detail=(
                    f"Client consistency assertion dayNumber ({request.dayNumber}) conflicts with "
                    f"authoritative session dayNumber ({auth_day})."
                ),
            )

        target_week = auth_week
        target_day = auth_day

        # Validate that (target_week, target_day) exists as a planned non-rest workout in active planSnapshot
        is_valid_planned_workout = any(
            week.weekNumber == target_week and any(
                day.dayNumber == target_day and not day.isRestDay
                for day in week.days
            )
            for week in active.planSnapshot.weeks
        )
        if not is_valid_planned_workout:
            raise HTTPException(
                status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
                detail=(
                    f"Workout Week {target_week} Day {target_day} is not a valid non-rest training day "
                    f"in active program plan '{active.planId}'."
                ),
            )

        now_iso = datetime.now(timezone.utc).isoformat()
        new_cw = ProgramCompletedWorkout(
            sessionId=session.id,
            planId=active.planId,
            weekNumber=target_week,
            dayNumber=target_day,
            completedAt=session.completedAt or now_iso,
            durationSeconds=session.durationSeconds,
            completedSetsCount=session.completedSetsCount,
            totalSetsCount=session.totalSetsCount,
        )

        # 6. Progression calculation: determine all planned non-rest workouts
        all_planned_workouts: List[Tuple[int, int]] = []
        for week in active.planSnapshot.weeks:
            for day in week.days:
                if not day.isRestDay:
                    all_planned_workouts.append((week.weekNumber, day.dayNumber))

        # Completed set of (week, day) pairs including the newly completed one
        completed_pairs = {
            (cw.weekNumber, cw.dayNumber) for cw in active.completedWorkouts
        }
        completed_pairs.add((target_week, target_day))

        # Check if all planned workouts are completed
        all_finished = (
            len(all_planned_workouts) > 0
            and all(pair in completed_pairs for pair in all_planned_workouts)
        )

        new_status = "completed" if all_finished else "active"
        completed_at = now_iso if all_finished else None

        # Determine next pointer: earliest uncompleted planned workout
        next_week = active.currentWeek
        next_day = active.currentDay

        if all_finished:
            # Set to last planned workout coordinates
            if all_planned_workouts:
                next_week, next_day = all_planned_workouts[-1]
        else:
            for pw, pd in all_planned_workouts:
                if (pw, pd) not in completed_pairs:
                    next_week = pw
                    next_day = pd
                    break

        updated_completed_list = [cw.model_dump() for cw in active.completedWorkouts] + [new_cw.model_dump()]

        updates: Dict[str, Any] = {
            "status": new_status,
            "completedAt": completed_at,
            "currentWeek": next_week,
            "currentDay": next_day,
            "completedWorkouts": updated_completed_list,
            "updatedAt": now_iso,
        }

        updated = self._program_repo.update_program(uid, active.programId, updates)
        if not updated:
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail="Failed to update program state during session synchronization.",
            )

        logger.info(
            f"Synchronized session '{request.sessionId}' to program '{active.programId}'. "
            f"Progression: status={new_status}, week={next_week}, day={next_day}."
        )
        return updated

    # =========================================================================
    # ABANDON PROGRAM
    # =========================================================================

    def abandon_active_program(self, uid: str, request: Optional[ProgramAbandonRequest] = None) -> ProgramResponse:
        """
        Abandons the user's active program.
        Does NOT delete workout history, completed sessions, or adaptation history.
        Preserves the program document with status='abandoned'.
        """
        if not uid or not uid.strip():
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Authentication required.",
            )

        active = self._program_repo.get_active_program(uid)
        if not active or active.status != "active":
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="No active workout program found to abandon.",
            )

        now_iso = datetime.now(timezone.utc).isoformat()
        updates: Dict[str, Any] = {
            "status": "abandoned",
            "abandonedAt": now_iso,
            "updatedAt": now_iso,
        }

        updated = self._program_repo.update_program(uid, active.programId, updates)
        if not updated:
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail="Failed to update program state during abandonment.",
            )

        logger.info(f"Program '{active.programId}' successfully abandoned for user '{uid}'.")
        return updated

    # =========================================================================
    # ADAPTATION HISTORY
    # =========================================================================

    def record_adaptation_decision(self, uid: str, decision: Dict[str, Any]) -> Optional[ProgramResponse]:
        """
        Records an evaluated adaptation decision in the active program's audit history.
        Deduplicated by decisionId. Does NOT mutate future prescriptions.
        """
        active = self._program_repo.get_active_program(uid)
        if not active or active.status != "active":
            return None

        return self._program_repo.record_adaptation(uid, active.programId, decision)


# Global Singleton Provider
_program_service_instance: Optional[ProgramService] = None


def get_program_service() -> ProgramService:
    """FastAPI dependency provider for ProgramService."""
    global _program_service_instance
    if _program_service_instance is None:
        _program_service_instance = ProgramService()
    return _program_service_instance

