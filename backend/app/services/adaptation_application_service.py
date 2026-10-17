"""
Adaptation Application Service (Phase 9C.4).

Orchestrates the safe, bounded, deterministic application of Phase 9C.2 adaptation proposals
to FUTURE workouts inside the active mesocycle created by Phase 9C.3.

Strict Invariants:
1. Original Plan Immutability: program.planSnapshot remains byte-for-byte immutable baseline.
2. Effective Plan Snapshot: Mutations apply exclusively to future workouts in effectivePlanSnapshot.
3. Plan Versioning: planVersion increments deterministically (1 -> 2 -> 3) on each successful application.
4. Historical & In-Progress Immutability: Completed sessions and in-progress workouts are never altered.
5. Absolute 5% Load Ceiling: Prescribed load increase must be <= baseline * 1.05. Never rounds up past 5%.
6. Grounded Weights: Never fabricates weights when no authoritative prior load exists.
7. Set Bounds: Prescribed sets remain bounded between 1 and 5 (minimum 1 set, never deletes exercise).
8. Duration Bound: Effective workout duration must not exceed target * 1.25.
9. RPE Ceiling: Target RPE cannot exceed 9.0.
10. Strict Idempotency: Re-applying the exact same decisionId returns 'already_applied' with zero mutation.
11. Zero AI/ML: No Gemini, no LLM, no ML, no external network calls.
12. Phase Boundaries: No Slot 0 corrective injection (deferred to 9C.6), no UI dashboard (deferred to 9C.5).
"""

import json
import threading
from copy import deepcopy
from datetime import datetime, timezone
from typing import Optional, List, Dict, Any, Tuple
from fastapi import HTTPException, status

from ..repositories.program_repository import ProgramRepository, get_program_repository
from ..repositories.workout_repository import WorkoutRepository, get_workout_repository
from ..schemas.program import (
    ProgramDocument,
    ProgramResponse,
    EffectivePrescriptionResponse,
    ApplyAdaptationRequest,
    ApplyAdaptationResponse,
    ProgramVersionsResponse,
    MAX_PROGRAM_DOC_BYTES,
)
from ..schemas.workout_plan import (
    WorkoutPlanResponse,
    PlannedWorkoutDay,
    PlannedExercise,
    PlannedSet,
)
from ..schemas.adaptation import (
    AdaptationDecision,
    PrescriptionDelta,
    generate_decision_id,
)
from ..seeds.catalog import CATALOG_BY_ID
from ..services.adaptation_engine_service import (
    AdaptationEngineService,
    get_adaptation_engine_service,
    is_lower_compound,
    is_upper_compound,
)
from ..utils.logger import logger

_SENTINEL = object()

UPPER_COMPOUND_INCREMENT: float = 2.5
LOWER_COMPOUND_INCREMENT: float = 5.0
ISOLATION_INCREMENT: float = 1.0
MAX_LOAD_INCREASE_PCT: float = 0.05
MAX_PERMITTED_RPE: float = 9.0
MIN_SETS_BOUND: int = 1
MAX_SETS_BOUND: int = 5
MAX_DURATION_MULTIPLIER: float = 1.25


class AdaptationApplicationService:
    """
    Business logic service for applying Phase 9C.2 adaptation proposals
    to future workouts in an active program.
    """

    def __init__(
        self,
        program_repo: Any = _SENTINEL,
        workout_repo: Any = _SENTINEL,
        adaptation_engine: Any = _SENTINEL,
        catalog: Optional[Dict[str, Any]] = None,
    ):
        self._program_repo: ProgramRepository = (
            program_repo if program_repo is not _SENTINEL else get_program_repository()
        )
        self._workout_repo: WorkoutRepository = (
            workout_repo if workout_repo is not _SENTINEL else get_workout_repository()
        )
        self._adaptation_engine: AdaptationEngineService = (
            adaptation_engine if adaptation_engine is not _SENTINEL else get_adaptation_engine_service()
        )
        self._catalog = catalog or CATALOG_BY_ID
        self._lock = threading.Lock()

    # =========================================================================
    # GET EFFECTIVE PRESCRIPTION
    # =========================================================================

    def get_effective_prescription(
        self, uid: str, week: int, day: int
    ) -> EffectivePrescriptionResponse:
        """
        Retrieves the current effective prescription for a specified week and day
        in the user's active workout program.
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

        if active.userId != uid:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Access denied.",
            )

        # Use effectivePlanSnapshot if present, otherwise planSnapshot
        plan = active.effectivePlanSnapshot or active.planSnapshot

        target_week = None
        for w in plan.weeks:
            if w.weekNumber == week:
                target_week = w
                break

        if not target_week:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Week {week} not found in active program plan.",
            )

        target_day = None
        for d in target_week.days:
            if d.dayNumber == day:
                target_day = d
                break

        if not target_day:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Day {day} not found in Week {week} of active program plan.",
            )

        # Check completed status
        is_completed = any(
            cw.weekNumber == week and cw.dayNumber == day
            for cw in active.completedWorkouts
        )

        # Check if adapted
        applied_for_day: List[Dict[str, Any]] = []
        for record in active.adaptationHistory:
            if record.get("status") == "applied":
                affected = record.get("affectedDays", [])
                if any(ad.get("weekNumber") == week and ad.get("dayNumber") == day for ad in affected):
                    applied_for_day.append(record)

        is_adapted = len(applied_for_day) > 0

        return EffectivePrescriptionResponse(
            programId=active.programId,
            planId=active.planId,
            planVersion=active.planVersion,
            weekNumber=week,
            dayNumber=day,
            phaseLabel=target_week.phaseLabel,
            isAdapted=is_adapted,
            isCompleted=is_completed,
            day=target_day,
            appliedAdaptations=applied_for_day,
        )

    # =========================================================================
    # GET PROGRAM VERSIONS
    # =========================================================================

    def get_program_versions(self, uid: str) -> ProgramVersionsResponse:
        """
        Retrieves version and adaptation audit history for the active program.
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

        if active.userId != uid:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Access denied.",
            )

        applied_count = sum(
            1 for rec in active.adaptationHistory if rec.get("status") == "applied"
        )

        return ProgramVersionsResponse(
            programId=active.programId,
            programVersion=active.programVersion,
            planVersion=active.planVersion,
            totalAdaptationsApplied=applied_count,
            adaptationHistory=active.adaptationHistory,
            pendingNextBlockSplit=active.pendingNextBlockSplit,
        )

    # =========================================================================
    # DECISION AUTHORITY VALIDATION
    # =========================================================================

    def _validate_decision_authority(
        self,
        uid: str,
        active: ProgramDocument,
        decision: AdaptationDecision,
        request: ApplyAdaptationRequest,
    ) -> Tuple[bool, str, Optional[AdaptationDecision]]:
        """
        Validates that the proposed adaptation decision is authoritative, consistent with
        deterministic Phase 9C.2 evaluation, free from client tampering, and not stale.

        Enforces:
        1. Program context & plan affinity (programId, planId, evidence).
        2. Cryptographic & deterministic decisionId structure (SHA-256 for authenticated uid).
        3. Freshness / stale-decision protection against current effective prescription.
        4. Independent Phase 9C.2 recomputation to verify qualification, rules, loads, sets, and evidence.
        """
        # 1. Program & Plan Context Check
        if request.programId is not None and request.programId != active.programId:
            return False, f"Request programId '{request.programId}' does not match active program '{active.programId}'.", None

        if request.planId is not None and request.planId != active.planId:
            return False, f"Request planId '{request.planId}' does not match active program plan '{active.planId}'.", None

        if isinstance(decision.evidence, dict):
            ev_prog = decision.evidence.get("programId")
            if ev_prog and ev_prog != active.programId:
                return False, f"Decision evidence programId '{ev_prog}' does not match active program '{active.programId}'.", None
            ev_plan = decision.evidence.get("planId")
            if ev_plan and ev_plan != active.planId:
                return False, f"Decision evidence planId '{ev_plan}' does not match active plan '{active.planId}'.", None

        # 2. Decision ID Structural Integrity & User Binding Check
        scope_id = "program_split" if decision.adaptationType == "split_adjustment" else (decision.exerciseId or "")
        expected_id = generate_decision_id(
            user_id=uid,
            scope_id=scope_id,
            rule_code=decision.ruleCode,
            adaptation_type=decision.adaptationType,
            status=decision.status,
            delta_magnitude=decision.deltaMagnitude,
        )
        if decision.decisionId != expected_id:
            return False, f"Decision ID '{decision.decisionId}' is invalid or tampered (expected hash '{expected_id}').", None

        # 3. Split Adjustment Validation
        if decision.adaptationType == "split_adjustment":
            signals = self._adaptation_engine.signal_service.get_personalization_signals(uid, window_days=28)
            auth_split = self._adaptation_engine._evaluate_future_split_adaptation(uid, signals)
            if not auth_split:
                return False, "Authoritative 9C.2 evaluation determined user does not qualify for split adjustment.", None
            if decision.ruleCode != auth_split.ruleCode:
                return False, f"Decision rule code '{decision.ruleCode}' does not match authoritative rule '{auth_split.ruleCode}'.", None
            return True, "Split adjustment authority validated.", None

        # 4. Exercise Adaptation Validation
        target_exercise_id = decision.exerciseId
        if not target_exercise_id:
            return False, "Target exercise ID is missing from adaptation decision.", None

        # Locate upcoming exercise in effective plan snapshot (or base plan snapshot)
        effective_plan = active.effectivePlanSnapshot or active.planSnapshot
        target_planned_ex: Optional[PlannedExercise] = None
        for w in effective_plan.weeks:
            if w.weekNumber < active.currentWeek:
                continue
            for d in w.days:
                if d.isRestDay:
                    continue
                if w.weekNumber == active.currentWeek and d.dayNumber < active.currentDay:
                    continue
                for ex in d.exercises:
                    if ex.exerciseId == target_exercise_id:
                        target_planned_ex = ex
                        break
                if target_planned_ex:
                    break
            if target_planned_ex:
                break

        if not target_planned_ex:
            return False, f"Exercise '{target_exercise_id}' not found in any eligible future workout in active program.", None

        # Stale Decision Protection against current effective prescription
        current_effective_weight = target_planned_ex.targetWeightKg or target_planned_ex.weightKg
        current_effective_sets = len(target_planned_ex.prescribedSets)

        if decision.previousPrescription:
            if decision.previousPrescription.weightKg is not None and current_effective_weight is not None:
                if abs(decision.previousPrescription.weightKg - current_effective_weight) > 0.01:
                    return False, (
                        f"Stale decision: previous prescribed load ({decision.previousPrescription.weightKg} kg) "
                        f"does not match current effective prescription ({current_effective_weight} kg)."
                    ), None
            if decision.previousPrescription.setCount is not None:
                if decision.previousPrescription.setCount != current_effective_sets:
                    return False, (
                        f"Stale decision: previous prescribed sets ({decision.previousPrescription.setCount}) "
                        f"does not match current effective sets ({current_effective_sets})."
                    ), None

        # 5. Independent Phase 9C.2 Recomputation Authority Check
        candidate_presc = PrescriptionDelta(
            exerciseId=target_planned_ex.exerciseId,
            exerciseName=target_planned_ex.name,
            weightKg=current_effective_weight,
            setCount=current_effective_sets,
            targetRepsMin=target_planned_ex.prescribedSets[0].targetRepsMin if target_planned_ex.prescribedSets else None,
            targetRepsMax=target_planned_ex.prescribedSets[0].targetRepsMax if target_planned_ex.prescribedSets else None,
            targetRpe=target_planned_ex.prescribedSets[0].targetRpe if target_planned_ex.prescribedSets else None,
            restSeconds=target_planned_ex.prescribedSets[0].restSeconds if target_planned_ex.prescribedSets else 90,
        )

        target_dur = 60
        if hasattr(active.planSnapshot, "appliedFilters") and active.planSnapshot.appliedFilters:
            target_dur = active.planSnapshot.appliedFilters.get("target_duration_minutes", 60)

        all_completed = self._workout_repo.list_user_history(uid, limit=100)
        chronological_sessions = sorted(
            all_completed,
            key=lambda s: (s.completedAt or s.startedAt or ""),
        )
        signals = self._adaptation_engine.signal_service.get_personalization_signals(uid, window_days=28)

        auth_decision = self._adaptation_engine._evaluate_single_exercise(
            uid=uid,
            exercise_id=target_exercise_id,
            candidate_prescription=candidate_presc,
            sessions=chronological_sessions,
            signals=signals,
            target_duration_minutes=target_dur,
        )

        # Qualification check
        if auth_decision.status not in ("progression_candidate", "volume_reduction_candidate"):
            return False, f"Authoritative 9C.2 evaluation does not qualify for adaptation (status: '{auth_decision.status}', rule: '{auth_decision.ruleCode}').", None

        # Decision ID match
        if decision.decisionId != auth_decision.decisionId:
            return False, f"Decision ID '{decision.decisionId}' does not match authoritative decision ID '{auth_decision.decisionId}'.", None

        # Exercise ID match
        if decision.exerciseId != auth_decision.exerciseId:
            return False, f"Exercise ID '{decision.exerciseId}' does not match authoritative exercise ID '{auth_decision.exerciseId}'.", None

        # Adaptation type match
        if decision.adaptationType != auth_decision.adaptationType:
            return False, f"Adaptation type '{decision.adaptationType}' does not match authoritative type '{auth_decision.adaptationType}'.", None

        # Rule code match
        if decision.ruleCode != auth_decision.ruleCode:
            return False, f"Rule code '{decision.ruleCode}' does not match authoritative rule '{auth_decision.ruleCode}'.", None

        # Proposed prescription consistency check
        if auth_decision.proposedPrescription:
            if not decision.proposedPrescription:
                return False, "Decision is missing proposedPrescription.", None
            if auth_decision.proposedPrescription.weightKg is not None:
                if decision.proposedPrescription.weightKg is None or abs(decision.proposedPrescription.weightKg - auth_decision.proposedPrescription.weightKg) > 0.01:
                    return False, f"Proposed weight {decision.proposedPrescription.weightKg} kg does not match authoritative proposed weight {auth_decision.proposedPrescription.weightKg} kg.", None
            if auth_decision.proposedPrescription.targetRepsMin is not None:
                if decision.proposedPrescription.targetRepsMin != auth_decision.proposedPrescription.targetRepsMin:
                    return False, f"Proposed targetRepsMin {decision.proposedPrescription.targetRepsMin} does not match authoritative {auth_decision.proposedPrescription.targetRepsMin}.", None
            if auth_decision.proposedPrescription.targetRepsMax is not None:
                if decision.proposedPrescription.targetRepsMax != auth_decision.proposedPrescription.targetRepsMax:
                    return False, f"Proposed targetRepsMax {decision.proposedPrescription.targetRepsMax} does not match authoritative {auth_decision.proposedPrescription.targetRepsMax}.", None
            if auth_decision.proposedPrescription.setCount is not None:
                if decision.proposedPrescription.setCount != auth_decision.proposedPrescription.setCount:
                    return False, f"Proposed setCount {decision.proposedPrescription.setCount} does not match authoritative {auth_decision.proposedPrescription.setCount}.", None
            if auth_decision.proposedPrescription.targetRpe is not None:
                if decision.proposedPrescription.targetRpe is not None and decision.proposedPrescription.targetRpe > auth_decision.proposedPrescription.targetRpe:
                    return False, f"Proposed targetRpe {decision.proposedPrescription.targetRpe} exceeds authoritative RPE {auth_decision.proposedPrescription.targetRpe}.", None

        # Evidence consistency check
        if isinstance(decision.evidence, dict) and isinstance(auth_decision.evidence, dict):
            if "consecutiveQualifyingSessions" in auth_decision.evidence:
                if decision.evidence.get("consecutiveQualifyingSessions") != auth_decision.evidence["consecutiveQualifyingSessions"]:
                    return False, "Decision evidence consecutiveQualifyingSessions mismatch.", None
            if "consecutiveVolumeFailures" in auth_decision.evidence:
                if decision.evidence.get("consecutiveVolumeFailures") != auth_decision.evidence["consecutiveVolumeFailures"]:
                    return False, "Decision evidence consecutiveVolumeFailures mismatch.", None

        # Source sessions consistency check
        if auth_decision.sourceSessionIds:
            if set(decision.sourceSessionIds) != set(auth_decision.sourceSessionIds):
                return False, "Decision sourceSessionIds do not match authoritative qualifying sessions.", None

        return True, "Authoritative 9C.2 decision validated successfully.", auth_decision

    # =========================================================================
    # APPLY ADAPTATION
    # =========================================================================

    def apply_adaptation(
        self, uid: str, request: ApplyAdaptationRequest
    ) -> ApplyAdaptationResponse:
        """
        Applies an approved Phase 9C.2 adaptation decision to future workouts
        inside the user's active program.
        """
        if not uid or not uid.strip():
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Authentication required.",
            )

        with self._lock:
            return self._apply_adaptation_locked(uid, request)

    def _apply_adaptation_locked(
        self, uid: str, request: ApplyAdaptationRequest
    ) -> ApplyAdaptationResponse:
        active = self._program_repo.get_active_program(uid)
        if not active:
            # Check if any non-active program exists to provide exact status error
            all_progs = self._program_repo.list_user_programs(uid)
            for p in all_progs:
                if p.status == "abandoned":
                    raise HTTPException(
                        status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
                        detail="Cannot apply adaptations to an abandoned program.",
                    )
                if p.status == "completed":
                    raise HTTPException(
                        status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
                        detail="Cannot apply adaptations to a completed program.",
                    )
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="No active workout program found for this user.",
            )

        if active.userId != uid:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Access denied.",
            )

        if active.status == "abandoned":
            raise HTTPException(
                status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
                detail="Cannot apply adaptations to an abandoned program.",
            )

        if active.status == "completed":
            raise HTTPException(
                status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
                detail="Cannot apply adaptations to a completed program.",
            )

        decision = request.decision
        decision_id = decision.decisionId

        # 1. IDEMPOTENCY CHECK
        for existing in active.adaptationHistory:
            if existing.get("decisionId") == decision_id and existing.get("status") == "applied":
                # Check if caller tampered with payload using an existing decisionId
                if (
                    existing.get("affectedExerciseId") != decision.exerciseId
                    or existing.get("adaptationType") != decision.adaptationType
                    or existing.get("ruleCode") != decision.ruleCode
                ):
                    logger.warning(f"Decision '{decision_id}' matched existing record but payload differs (tampering detected).")
                    return ApplyAdaptationResponse(
                        programId=active.programId,
                        planVersion=active.planVersion,
                        status="rejected",
                        decisionId=decision_id,
                        adaptationType=decision.adaptationType,
                        ruleCode=decision.ruleCode,
                        affectedDaysCount=0,
                        reason="Tampered decision: payload fields do not match previously applied decision.",
                        details="Tampered decision: payload fields do not match previously applied decision.",
                        program=active,
                    )
                applied_p = existing.get("appliedPrescription") or {}
                if decision.proposedPrescription and applied_p:
                    prop_wt = decision.proposedPrescription.weightKg
                    appl_wt = applied_p.get("adaptedWeightKg") if "adaptedWeightKg" in applied_p else applied_p.get("weightKg")
                    if prop_wt is not None and appl_wt is not None and abs(prop_wt - appl_wt) > 0.01:
                        logger.warning(f"Decision '{decision_id}' proposed weight {prop_wt} differs from applied weight {appl_wt}.")
                        return ApplyAdaptationResponse(
                            programId=active.programId,
                            planVersion=active.planVersion,
                            status="rejected",
                            decisionId=decision_id,
                            adaptationType=decision.adaptationType,
                            ruleCode=decision.ruleCode,
                            affectedDaysCount=0,
                            reason="Tampered decision: proposed prescription does not match previously applied decision.",
                            details="Tampered decision: proposed prescription does not match previously applied decision.",
                            program=active,
                        )

                prev_p = existing.get("previousPrescription") or {}
                if decision.previousPrescription and prev_p:
                    p_wt = decision.previousPrescription.weightKg
                    orig_p_wt = prev_p.get("weightKg")
                    if p_wt is not None and orig_p_wt is not None and abs(p_wt - orig_p_wt) > 0.01:
                        logger.warning(f"Decision '{decision_id}' previous weight {p_wt} differs from recorded baseline {orig_p_wt}.")
                        return ApplyAdaptationResponse(
                            programId=active.programId,
                            planVersion=active.planVersion,
                            status="rejected",
                            decisionId=decision_id,
                            adaptationType=decision.adaptationType,
                            ruleCode=decision.ruleCode,
                            affectedDaysCount=0,
                            reason="Stale or tampered decision: previous prescription does not match original baseline.",
                            details="Stale or tampered decision: previous prescription does not match original baseline.",
                            program=active,
                        )

                logger.info(f"Decision '{decision_id}' already applied to program '{active.programId}'. Idempotent return.")
                return ApplyAdaptationResponse(
                    programId=active.programId,
                    planVersion=active.planVersion,
                    status="already_applied",
                    decisionId=decision_id,
                    adaptationType=decision.adaptationType,
                    ruleCode=decision.ruleCode,
                    affectedDaysCount=0,
                    details=f"Decision '{decision_id}' has already been applied.",
                    adaptationRecord=existing,
                    program=active,
                )

        # 2. STATUS & CANDIDATE ELIGIBILITY CHECK
        if decision.status == "constrained_no_change":
            return ApplyAdaptationResponse(
                programId=active.programId,
                planVersion=active.planVersion,
                status="constrained",
                decisionId=decision_id,
                adaptationType=decision.adaptationType,
                ruleCode=decision.ruleCode,
                affectedDaysCount=0,
                details="Decision was constrained in 9C.2 evaluation and cannot be applied.",
                program=active,
            )

        if decision.status in ("insufficient_data", "no_change"):
            return ApplyAdaptationResponse(
                programId=active.programId,
                planVersion=active.planVersion,
                status="rejected",
                decisionId=decision_id,
                adaptationType=decision.adaptationType,
                ruleCode=decision.ruleCode,
                affectedDaysCount=0,
                details=f"Decision status '{decision.status}' does not qualify for adaptation.",
                program=active,
            )

        # 3. DECISION AUTHORITY & TAMPERING VALIDATION (Phase 9C.4 Correction Pass)
        is_valid, reason, auth_dec = self._validate_decision_authority(uid, active, decision, request)
        if not is_valid:
            logger.warning(f"Decision authority validation failed for user '{uid}': {reason}")
            return ApplyAdaptationResponse(
                programId=active.programId,
                planVersion=active.planVersion,
                status="rejected",
                decisionId=decision_id,
                adaptationType=decision.adaptationType,
                ruleCode=decision.ruleCode,
                affectedDaysCount=0,
                details=f"Adaptation rejected: {reason}",
                program=active,
            )

        # 3. SPLIT ADJUSTMENT (NEXT BLOCK MESOCYCLE PROPOSAL)
        if decision.adaptationType == "split_adjustment":
            audit_entry = {
                "decisionId": decision_id,
                "adaptationType": "split_adjustment",
                "ruleCode": decision.ruleCode,
                "programId": active.programId,
                "versionBefore": active.planVersion,
                "versionAfter": active.planVersion,
                "appliedAt": datetime.now(timezone.utc).isoformat(),
                "affectedExerciseId": None,
                "affectedDays": [],
                "previousPrescription": None,
                "appliedPrescription": None,
                "constraints": decision.constraintsApplied,
                "status": "applied",
                "details": "Stored pending split adjustment for next mesocycle block without mutating active program.",
            }
            updates: Dict[str, Any] = {
                "pendingNextBlockSplit": decision.model_dump(),
                "adaptationHistory": [r for r in active.adaptationHistory] + [audit_entry],
                "updatedAt": datetime.now(timezone.utc).isoformat(),
            }
            updated = self._program_repo.update_program(uid, active.programId, updates)
            return ApplyAdaptationResponse(
                programId=active.programId,
                planVersion=active.planVersion,
                status="applied",
                decisionId=decision_id,
                adaptationType=decision.adaptationType,
                ruleCode=decision.ruleCode,
                affectedDaysCount=0,
                details="Adherence split recommendation recorded for next mesocycle block.",
                adaptationRecord=audit_entry,
                program=updated or active,
            )

        # 4. RESOLVE BASE EFFECTIVE PLAN (Deep copy, NEVER touching planSnapshot)
        base_plan_data = (active.effectivePlanSnapshot or active.planSnapshot).model_dump()
        effective_plan = WorkoutPlanResponse(**base_plan_data)

        # 5. DETERMINE FUTURE WORKOUT TARGETS
        completed_pairs = {
            (cw.weekNumber, cw.dayNumber) for cw in active.completedWorkouts
        }

        # Check for in-progress session
        in_progress_pair: Optional[Tuple[int, int]] = None
        try:
            active_session = self._workout_repo.get_active_session(uid)
            if active_session and active_session.status == "in_progress":
                if active_session.weekNumber and active_session.dayNumber:
                    in_progress_pair = (active_session.weekNumber, active_session.dayNumber)
        except Exception as e:
            logger.warning(f"Could not inspect in-progress sessions: {e}")

        # Collect eligible future non-rest days
        eligible_future_days: List[Tuple[int, PlannedWorkoutDay]] = []
        for w in effective_plan.weeks:
            for d in w.days:
                if d.isRestDay:
                    continue
                pair = (w.weekNumber, d.dayNumber)
                # Historical: already in completedWorkouts
                if pair in completed_pairs:
                    continue
                # In-progress: do not silently modify active workout
                if in_progress_pair and pair == in_progress_pair:
                    continue
                # Must be at or beyond current pointer
                if w.weekNumber < active.currentWeek:
                    continue
                if w.weekNumber == active.currentWeek and d.dayNumber < active.currentDay:
                    continue
                eligible_future_days.append((w.weekNumber, d))

        target_exercise_id = decision.exerciseId
        if not target_exercise_id:
            return ApplyAdaptationResponse(
                programId=active.programId,
                planVersion=active.planVersion,
                status="rejected",
                decisionId=decision_id,
                adaptationType=decision.adaptationType,
                ruleCode=decision.ruleCode,
                affectedDaysCount=0,
                details="Target exercise ID is missing from adaptation decision.",
                program=active,
            )

        # Filter to days containing target exercise
        matching_future_days: List[Tuple[int, PlannedWorkoutDay]] = [
            (w_num, d)
            for w_num, d in eligible_future_days
            if any(ex.exerciseId == target_exercise_id for ex in d.exercises)
        ]

        if not matching_future_days:
            return ApplyAdaptationResponse(
                programId=active.programId,
                planVersion=active.planVersion,
                status="rejected",
                decisionId=decision_id,
                adaptationType=decision.adaptationType,
                ruleCode=decision.ruleCode,
                affectedDaysCount=0,
                details=f"No eligible future workouts contain exercise '{target_exercise_id}'.",
                program=active,
            )

        # 6. APPLY SPECIFIC ADAPTATION TYPE
        applied_delta: Dict[str, Any] = {}
        constraints_recorded: List[str] = list(decision.constraintsApplied)

        if decision.adaptationType == "load_progression":
            # Catalog knowledge or planned exercise inspection
            exercise_def = self._catalog.get(target_exercise_id)
            is_lower = is_lower_compound(exercise_def) if exercise_def else False
            is_upper = is_upper_compound(exercise_def) if exercise_def else False

            if not is_lower and not is_upper:
                # Fallback: inspect planned exercise in matching future days
                sample_ex = None
                for _, d in matching_future_days:
                    for e in d.exercises:
                        if e.exerciseId == target_exercise_id:
                            sample_ex = e
                            break
                    if sample_ex:
                        break
                if sample_ex and sample_ex.exerciseType == "compound":
                    lower_patterns = ("squat", "hinge", "lunge")
                    upper_patterns = ("horizontal_push", "horizontal_pull", "vertical_push", "vertical_pull")
                    lower_muscles = {"quadriceps", "hamstrings", "glutes", "calves"}
                    upper_muscles = {"chest", "back", "shoulders"}
                    
                    if sample_ex.movementPattern in lower_patterns or any(m in lower_muscles for m in (sample_ex.primaryMuscles or [])):
                        is_lower = True
                    elif sample_ex.movementPattern in upper_patterns or any(m in upper_muscles for m in (sample_ex.primaryMuscles or [])):
                        is_upper = True

            if is_lower:
                std_increment = LOWER_COMPOUND_INCREMENT
            elif is_upper:
                std_increment = UPPER_COMPOUND_INCREMENT
            else:
                std_increment = ISOLATION_INCREMENT

            # Check baseline load
            baseline_load: Optional[float] = None
            if decision.previousPrescription and decision.previousPrescription.weightKg is not None:
                baseline_load = decision.previousPrescription.weightKg
            else:
                # Look at current prescription in planned exercises
                for _, d in matching_future_days:
                    for ex in d.exercises:
                        if ex.exerciseId == target_exercise_id:
                            if ex.targetWeightKg is not None and ex.targetWeightKg > 0:
                                baseline_load = ex.targetWeightKg
                                break
                            elif ex.weightKg is not None and ex.weightKg > 0:
                                baseline_load = ex.weightKg
                                break
                    if baseline_load is not None:
                        break

            # Fallback: check completed sessions
            if baseline_load is None:
                try:
                    past_sessions = self._workout_repo.list_user_history(uid, limit=50)
                    for sess in sorted(past_sessions, key=lambda s: s.completedAt or s.startedAt or "", reverse=True):
                        if isinstance(sess.completedSets, dict):
                            for ex_id, sets_list in sess.completedSets.items():
                                if ex_id == target_exercise_id:
                                    for s_set in sets_list:
                                        wt = s_set.get("actualWeightKg") or s_set.get("targetWeightKg")
                                        if wt and wt > 0:
                                            baseline_load = float(wt)
                                            break
                                if baseline_load is not None:
                                    break
                        if baseline_load is not None:
                            break
                except Exception as e:
                    logger.warning(f"Could not read past sessions for baseline load: {e}")

            # Grounded weights rule: NEVER fabricate a weight if no baseline exists
            if baseline_load is None or baseline_load <= 0:
                return ApplyAdaptationResponse(
                    programId=active.programId,
                    planVersion=active.planVersion,
                    status="constrained",
                    decisionId=decision_id,
                    adaptationType=decision.adaptationType,
                    ruleCode=decision.ruleCode,
                    affectedDaysCount=0,
                    details="No authoritative baseline load exists. Load progression constrained to prevent fabricated weights.",
                    program=active,
                )

            new_load = round(baseline_load + std_increment, 2)

            # ABSOLUTE 5% CEILING CHECK
            max_permitted_load = round(baseline_load * (1.0 + MAX_LOAD_INCREASE_PCT), 4)
            if new_load > max_permitted_load + 1e-6:
                constraints_recorded.append("LOAD_CEILING_5_PERCENT_EXCEEDED")
                return ApplyAdaptationResponse(
                    programId=active.programId,
                    planVersion=active.planVersion,
                    status="constrained",
                    decisionId=decision_id,
                    adaptationType=decision.adaptationType,
                    ruleCode=decision.ruleCode,
                    affectedDaysCount=0,
                    details=(
                        f"Proposed load {new_load} kg exceeds 5% ceiling "
                        f"({max_permitted_load} kg) over baseline {baseline_load} kg. "
                        "Progression constrained by safety ceiling."
                    ),
                    program=active,
                )

            # Apply to all matching future days
            for _, d in matching_future_days:
                for ex in d.exercises:
                    if ex.exerciseId == target_exercise_id:
                        ex.targetWeightKg = new_load
                        ex.weightKg = new_load
                        ex.progressionNote = f"Adapted (+{std_increment} kg): working load {new_load} kg"
                        for p_set in ex.prescribedSets:
                            p_set.targetWeightKg = new_load
                            p_set.weightKg = new_load
                            if p_set.targetRpe and p_set.targetRpe > MAX_PERMITTED_RPE:
                                p_set.targetRpe = MAX_PERMITTED_RPE

            applied_delta = {
                "exerciseId": target_exercise_id,
                "baselineWeightKg": baseline_load,
                "adaptedWeightKg": new_load,
                "incrementKg": std_increment,
            }

        elif decision.adaptationType == "rep_progression":
            rep_increment = 1
            for _, d in matching_future_days:
                for ex in d.exercises:
                    if ex.exerciseId == target_exercise_id:
                        ex.progressionNote = f"Adapted (+{rep_increment} rep progression)"
                        for p_set in ex.prescribedSets:
                            p_set.targetReps += rep_increment
                            if p_set.targetRepsMin is not None:
                                p_set.targetRepsMin += rep_increment
                            if p_set.targetRepsMax is not None:
                                p_set.targetRepsMax += rep_increment
                            if p_set.targetRpe and p_set.targetRpe > MAX_PERMITTED_RPE:
                                p_set.targetRpe = MAX_PERMITTED_RPE

            applied_delta = {
                "exerciseId": target_exercise_id,
                "repIncrement": rep_increment,
            }

        elif decision.adaptationType == "volume_reduction":
            # Check minimum sets bound across matching days
            for _, d in matching_future_days:
                for ex in d.exercises:
                    if ex.exerciseId == target_exercise_id:
                        if len(ex.prescribedSets) <= MIN_SETS_BOUND:
                            constraints_recorded.append("MINIMUM_SET_BOUND_REACHED")
                            return ApplyAdaptationResponse(
                                programId=active.programId,
                                planVersion=active.planVersion,
                                status="constrained",
                                decisionId=decision_id,
                                adaptationType=decision.adaptationType,
                                ruleCode=decision.ruleCode,
                                affectedDaysCount=0,
                                details="Cannot reduce sets below minimum bound of 1 set (MINIMUM_SET_BOUND_REACHED).",
                                program=active,
                            )

            # Reduce exactly 1 set
            for _, d in matching_future_days:
                for ex in d.exercises:
                    if ex.exerciseId == target_exercise_id:
                        ex.prescribedSets = ex.prescribedSets[:-1]
                        for idx, s in enumerate(ex.prescribedSets, 1):
                            s.setNumber = idx
                        ex.totalSets = len(ex.prescribedSets)
                        ex.progressionNote = "Adapted (-1 set volume fatigue reduction)"

                # Recalculate day sets & estimated duration
                d.totalSets = sum(e.totalSets for e in d.exercises)
                d.estimatedDurationMinutes = max(10, sum(e.totalSets * 3 for e in d.exercises))

            applied_delta = {
                "exerciseId": target_exercise_id,
                "setReduction": -1,
            }

        else:
            return ApplyAdaptationResponse(
                programId=active.programId,
                planVersion=active.planVersion,
                status="rejected",
                decisionId=decision_id,
                adaptationType=decision.adaptationType,
                ruleCode=decision.ruleCode,
                affectedDaysCount=0,
                details=f"Adaptation type '{decision.adaptationType}' is not supported for dynamic prescription mutation.",
                program=active,
            )

        # 7. DURATION BOUND VALIDATION (duration <= target * 1.25)
        target_duration = 60
        if hasattr(active.planSnapshot, "appliedFilters") and active.planSnapshot.appliedFilters:
            target_duration = active.planSnapshot.appliedFilters.get("target_duration_minutes", 60)
        max_duration = target_duration * MAX_DURATION_MULTIPLIER

        for _, d in matching_future_days:
            if d.estimatedDurationMinutes > max_duration:
                constraints_recorded.append("DURATION_EXCEEDS_125_PCT")
                return ApplyAdaptationResponse(
                    programId=active.programId,
                    planVersion=active.planVersion,
                    status="constrained",
                    decisionId=decision_id,
                    adaptationType=decision.adaptationType,
                    ruleCode=decision.ruleCode,
                    affectedDaysCount=0,
                    details=f"Adapted workout duration ({d.estimatedDurationMinutes}m) exceeds 125% of target ({max_duration}m).",
                    program=active,
                )

        # 8. CONSTRUCT DETERMINISTIC AUDIT RECORD & ADVANCE VERSION
        version_before = active.planVersion
        version_after = version_before + 1
        now_iso = datetime.now(timezone.utc).isoformat()

        affected_days_list = [
            {"weekNumber": w_num, "dayNumber": d.dayNumber}
            for w_num, d in matching_future_days
        ]

        audit_record: Dict[str, Any] = {
            "decisionId": decision_id,
            "adaptationType": decision.adaptationType,
            "ruleCode": decision.ruleCode,
            "programId": active.programId,
            "versionBefore": version_before,
            "versionAfter": version_after,
            "appliedAt": now_iso,
            "affectedExerciseId": target_exercise_id,
            "affectedDays": affected_days_list,
            "previousPrescription": decision.previousPrescription.model_dump() if decision.previousPrescription else None,
            "appliedPrescription": applied_delta,
            "constraints": constraints_recorded,
            "status": "applied",
            "details": f"Applied {decision.adaptationType} across {len(matching_future_days)} future workouts.",
        }

        # 9. PERSIST UPDATES ATOMICALLY (< 800 KB validation)
        updates = {
            "planVersion": version_after,
            "effectivePlanSnapshot": effective_plan.model_dump(),
            "adaptationHistory": [rec for rec in active.adaptationHistory] + [audit_record],
            "updatedAt": now_iso,
        }

        try:
            serialized = json.dumps(updates, default=str)
            raw_len = len(serialized.encode("utf-8"))
            if raw_len > MAX_PROGRAM_DOC_BYTES:
                raise HTTPException(
                    status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
                    detail=f"Program document exceeds maximum size threshold ({raw_len} > {MAX_PROGRAM_DOC_BYTES} bytes).",
                )
        except (TypeError, ValueError) as e:
            logger.error(f"Serialization check failed: {e}")

        updated_program = self._program_repo.update_program(uid, active.programId, updates)
        if not updated_program:
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail="Failed to persist program adaptation updates.",
            )

        logger.info(
            f"Successfully applied adaptation '{decision_id}' to program '{active.programId}'. "
            f"planVersion: {version_before} -> {version_after}. Affected days: {len(matching_future_days)}."
        )

        return ApplyAdaptationResponse(
            programId=active.programId,
            planVersion=version_after,
            status="applied",
            decisionId=decision_id,
            adaptationType=decision.adaptationType,
            ruleCode=decision.ruleCode,
            affectedDaysCount=len(matching_future_days),
            details=f"Successfully applied {decision.adaptationType} to {len(matching_future_days)} future workouts.",
            adaptationRecord=audit_record,
            program=updated_program,
        )


# Global Singleton Provider
_adaptation_application_service_instance: Optional[AdaptationApplicationService] = None


def get_adaptation_application_service() -> AdaptationApplicationService:
    """FastAPI dependency provider for AdaptationApplicationService."""
    global _adaptation_application_service_instance
    if _adaptation_application_service_instance is None:
        _adaptation_application_service_instance = AdaptationApplicationService()
    return _adaptation_application_service_instance
