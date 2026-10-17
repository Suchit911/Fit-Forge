"""
Deterministic Workout Periodization & Prescription Service (Phase 9B.8.5.3).

Builds deterministic multi-week workout prescriptions and duration feasibility
evaluations on top of:
- WorkoutPlanService (Phase 9B.8.5.2 structural plan authority)
- 100-exercise knowledge catalog (Phase 9B.8.2)
- Exercise relationship graph & corrective guidance (Phase 9B.8.3)
- ExerciseRecommendationService (Phase 9B.8.4)
- Domain models and taxonomies (Phase 9B.8.5.1)

Core Architectural Rules:
- Pure deterministic engineering layer: Zero Gemini, Zero LLM, Zero ML, Zero Vector DB.
- Read-only execution: Zero Firestore reads, Zero Firestore writes.
- Non-medical engineering language: "default", "planning estimate", "progression target", "deload guidance".
- Respects structural authority: consumes output of WorkoutPlanService; does NOT bypass or duplicate
  exercise selection, equipment filtering, or template allocation.
- Deterministic 4-week block mesocycles (Weeks 1-4, 5-8, 9-12):
    Week 1: Baseline Accumulation
    Week 2: Volume Loading (+1 set to compound movements, reps progressed within bounds)
    Week 3: Intensity Peak (controlled volume, elevated RPE <= 9.0, lower rep target)
    Week 4: Deload & Consolidation (bounded set reduction policy: 3->2, 2->1, 1->1; sets capped <= 3; RPE reduced; exposure preserved)
- Week count handling: 1 to 12 weeks with deterministic support for partial blocks.
- Block-to-block progression: bounded linear RPE offset, strictly capped at RPE <= 9.0, sets <= 5.
- Duration feasibility evaluation:
    - feasible (<= target duration)
    - potentially_over_target (target < est <= target * 1.25)
    - impossible_under_constraints (est > target * 1.25)
"""

from dataclasses import dataclass
from typing import List, Dict, Any, Optional, Tuple

from backend.app.schemas.exercise import (
    MovementPattern,
    ExerciseType,
    PROHIBITED_MEDICAL_PHRASES,
)
from backend.app.schemas.user import (
    FitnessGoal,
    DifficultyLevel,
    EquipmentType,
    MuscleGroup,
)
from backend.app.schemas.workout_plan import (
    WorkoutSplitType,
    ExerciseSlotRole,
    BlockPhase,
    DurationFeasibility,
    PlannedSet,
    PlannedExercise,
    PlannedWorkoutDay,
    PlannedWeek,
    WorkoutPlanGenerateRequest,
    WorkoutPlanResponse,
    generate_deterministic_plan_id,
    get_block_phase_label,
    get_block_number,
)
from backend.app.services.workout_plan_service import (
    WorkoutPlanService,
    get_workout_plan_service,
)


# ============================================================================
# Centralized Engineering Constants & Bounds
# ============================================================================

# Execution & Duration Estimation
EXECUTION_SECONDS_PER_REP: float = 4.0
SETUP_SECONDS_PER_EXERCISE: float = 60.0
TRANSITION_SECONDS_BETWEEN_EXERCISES: float = 60.0
OVER_TARGET_TOLERANCE_RATIO: float = 1.25

# RPE Bounds
MIN_RPE: float = 5.0
MAX_RPE: float = 9.0
DEFAULT_DELOAD_RPE: float = 6.0

# Volume / Set Bounds
MIN_SETS_PER_EXERCISE: int = 1
MAX_SETS_PER_EXERCISE_NORMAL: int = 5
MAX_SETS_PER_EXERCISE_DELOAD: int = 3

# Block-to-Block Progression
BLOCK_RPE_PROGRESSION_STEP: float = 0.25


# ============================================================================
# Baseline Prescription Template Structure
# ============================================================================

@dataclass(frozen=True)
class BaselinePrescription:
    """Deterministic baseline parameters for an exercise slot."""
    base_sets: int
    rep_min: int
    rep_max: int
    base_reps: int
    rest_seconds: int
    base_rpe: float
    rationale: str


def _build_baseline_framework() -> Dict[Tuple[str, ExerciseSlotRole], BaselinePrescription]:
    """
    Constructs the centralized, goal- and slot-aware baseline prescription matrix.
    Uses conservative planning language without medical claims.
    """
    matrix: Dict[Tuple[str, ExerciseSlotRole], BaselinePrescription] = {}

    # All supported FitnessGoal keys
    goals = ["strength", "muscle_gain", "fat_loss", "endurance", "general_fitness"]

    for goal in goals:
        # 1. Warmup / Corrective (Slot 0) - Conservative low-volume preparation
        matrix[(goal, ExerciseSlotRole.WARMUP_CORRECTIVE)] = BaselinePrescription(
            base_sets=2,
            rep_min=8,
            rep_max=10,
            base_reps=10,
            rest_seconds=45,
            base_rpe=5.0,
            rationale="Conservative low-volume preparation focusing on mobility and activation.",
        )

        # 2. Primary Compound (Slot 1)
        if goal == "strength":
            matrix[(goal, ExerciseSlotRole.PRIMARY_COMPOUND)] = BaselinePrescription(
                base_sets=3,
                rep_min=5,
                rep_max=6,
                base_reps=5,
                rest_seconds=180,
                base_rpe=7.5,
                rationale="Primary compound progression target emphasizing multi-joint capacity.",
            )
        elif goal == "endurance":
            matrix[(goal, ExerciseSlotRole.PRIMARY_COMPOUND)] = BaselinePrescription(
                base_sets=3,
                rep_min=10,
                rep_max=14,
                base_reps=12,
                rest_seconds=90,
                base_rpe=7.0,
                rationale="Primary compound progression target emphasizing sustained mechanical work.",
            )
        else:  # muscle_gain, fat_loss, general_fitness
            matrix[(goal, ExerciseSlotRole.PRIMARY_COMPOUND)] = BaselinePrescription(
                base_sets=3,
                rep_min=6,
                rep_max=10,
                base_reps=8,
                rest_seconds=120,
                base_rpe=7.0,
                rationale="Primary compound progression target emphasizing multi-joint capacity.",
            )

        # 3. Secondary Compound (Slot 2)
        if goal == "strength":
            matrix[(goal, ExerciseSlotRole.SECONDARY_COMPOUND)] = BaselinePrescription(
                base_sets=3,
                rep_min=6,
                rep_max=8,
                base_reps=6,
                rest_seconds=120,
                base_rpe=7.0,
                rationale="Secondary compound loading supporting primary movement patterns.",
            )
        elif goal == "endurance":
            matrix[(goal, ExerciseSlotRole.SECONDARY_COMPOUND)] = BaselinePrescription(
                base_sets=3,
                rep_min=12,
                rep_max=15,
                base_reps=12,
                rest_seconds=60,
                base_rpe=7.0,
                rationale="Secondary compound loading supporting sustained muscle activation.",
            )
        else:
            matrix[(goal, ExerciseSlotRole.SECONDARY_COMPOUND)] = BaselinePrescription(
                base_sets=3,
                rep_min=8,
                rep_max=12,
                base_reps=10,
                rest_seconds=90,
                base_rpe=7.0,
                rationale="Secondary compound loading supporting primary movement patterns.",
            )

        # 4. Accessory 1 (Slot 3)
        if goal == "strength":
            matrix[(goal, ExerciseSlotRole.ACCESSORY_1)] = BaselinePrescription(
                base_sets=3,
                rep_min=8,
                rep_max=10,
                base_reps=8,
                rest_seconds=90,
                base_rpe=7.5,
                rationale="Accessory volume targeting supplemental muscle group development.",
            )
        elif goal == "endurance":
            matrix[(goal, ExerciseSlotRole.ACCESSORY_1)] = BaselinePrescription(
                base_sets=3,
                rep_min=12,
                rep_max=16,
                base_reps=15,
                rest_seconds=60,
                base_rpe=7.0,
                rationale="Accessory volume targeting localized endurance and work capacity.",
            )
        else:
            matrix[(goal, ExerciseSlotRole.ACCESSORY_1)] = BaselinePrescription(
                base_sets=3,
                rep_min=10,
                rep_max=15,
                base_reps=12,
                rest_seconds=75,
                base_rpe=7.5,
                rationale="Accessory volume targeting supplemental muscle group development.",
            )

        # 5. Accessory 2 (Slot 4)
        if goal == "strength":
            matrix[(goal, ExerciseSlotRole.ACCESSORY_2)] = BaselinePrescription(
                base_sets=2,
                rep_min=10,
                rep_max=12,
                base_reps=10,
                rest_seconds=75,
                base_rpe=7.0,
                rationale="Accessory volume supporting unilateral balance and joint integrity.",
            )
        elif goal == "endurance":
            matrix[(goal, ExerciseSlotRole.ACCESSORY_2)] = BaselinePrescription(
                base_sets=2,
                rep_min=12,
                rep_max=16,
                base_reps=15,
                rest_seconds=45,
                base_rpe=7.0,
                rationale="Accessory volume supporting unilateral muscular endurance.",
            )
        else:
            matrix[(goal, ExerciseSlotRole.ACCESSORY_2)] = BaselinePrescription(
                base_sets=2,
                rep_min=10,
                rep_max=15,
                base_reps=12,
                rest_seconds=60,
                base_rpe=7.0,
                rationale="Accessory volume supporting unilateral balance and joint integrity.",
            )

        # 6. Core / Mobility (Slot 5)
        matrix[(goal, ExerciseSlotRole.CORE_MOBILITY)] = BaselinePrescription(
            base_sets=2,
            rep_min=10,
            rep_max=15,
            base_reps=12,
            rest_seconds=45,
            base_rpe=6.5,
            rationale="Core and stability focus maintaining postural alignment and control.",
        )

    return matrix


_BASELINE_PRESCRIPTION_FRAMEWORK = _build_baseline_framework()


# ============================================================================
# WorkoutPeriodizationService
# ============================================================================

class WorkoutPeriodizationService:
    """
    Deterministic Workout Periodization & Prescription Service.

    Consumes structural plans generated by WorkoutPlanService and applies:
    - 4-week mesocycle block structures across 1–12 weeks
    - Progressive set/rep/RPE prescription rules
    - Week 4 deload and consolidation reductions
    - Accurate, non-simulated duration estimation
    - Transparent whole-plan duration feasibility classification
    - Preservation of structural planner diagnostics
    """

    def __init__(
        self,
        workout_plan_service: Optional[WorkoutPlanService] = None,
    ):
        self._workout_plan_service = (
            workout_plan_service
            if workout_plan_service is not None
            else get_workout_plan_service()
        )
        self._prescription_framework = _BASELINE_PRESCRIPTION_FRAMEWORK

    # =========================================================================
    # PUBLIC API
    # =========================================================================

    def generate_periodized_plan(
        self, request: WorkoutPlanGenerateRequest
    ) -> WorkoutPlanResponse:
        """
        Orchestrates full deterministic generation:
        1. Calls WorkoutPlanService to generate the validated structural plan.
        2. Applies multi-week periodization and feasibility evaluation.
        """
        structural_plan = self._workout_plan_service.generate_plan(request)
        return self.periodize_plan(structural_plan, request)

    def periodize_plan(
        self,
        structural_plan: WorkoutPlanResponse,
        request: WorkoutPlanGenerateRequest,
    ) -> WorkoutPlanResponse:
        """
        Consumes an already-generated WorkoutPlanResponse and overlays deterministic
        multi-week periodization, bounded progression, deload logic, and duration feasibility.

        Preserves:
        - Diagnostic failure states (State B, State C, State D) without mutation.
        - Exercise IDs, names, split type, day allocation, movement patterns, and slot roles.
        """
        # 1. State Preservation: if structural plan failed, return as-is
        if not structural_plan.feasibilityCheckPassed or not structural_plan.weeks:
            return structural_plan

        # 2. Extract structural template days from Week 1
        reference_week = structural_plan.weeks[0]
        reference_days = reference_week.days

        goal_key = request.targetGoal if request.targetGoal in ["strength", "muscle_gain", "fat_loss", "endurance", "general_fitness"] else "general_fitness"
        total_weeks = request.planDurationWeeks

        # 3. Construct Deterministic Multi-Week Progression
        periodized_weeks: List[PlannedWeek] = []

        for week_idx in range(1, total_weeks + 1):
            block_number = get_block_number(week_idx)
            week_in_block = ((week_idx - 1) % 4) + 1
            phase_label = get_block_phase_label(week_idx)

            periodized_days: List[PlannedWorkoutDay] = []
            for day in reference_days:
                if day.isRestDay:
                    periodized_days.append(day.model_copy(deep=True))
                    continue

                periodized_exercises: List[PlannedExercise] = []
                for ex in day.exercises:
                    periodized_ex = self._prescribe_exercise_for_week(
                        exercise=ex,
                        goal_key=goal_key,
                        week_idx=week_idx,
                        block_number=block_number,
                        week_in_block=week_in_block,
                    )
                    periodized_exercises.append(periodized_ex)

                # Day Duration & Metrics
                day_total_sets = sum(ex.totalSets for ex in periodized_exercises)
                day_seconds = self._estimate_day_seconds(periodized_exercises)
                day_duration_minutes = max(1, int(round(day_seconds / 60.0)))

                periodized_day = PlannedWorkoutDay(
                    day_number=day.dayNumber,
                    day_label=day.dayLabel,
                    is_rest_day=False,
                    focus=day.focus,
                    target_patterns=list(day.targetPatterns),
                    target_muscles=list(day.targetMuscles),
                    exercises=periodized_exercises,
                    total_sets=day_total_sets,
                    estimated_duration_minutes=day_duration_minutes,
                )
                periodized_days.append(periodized_day)

            # Weekly Metrics
            weekly_sets = sum(d.totalSets for d in periodized_days if not d.isRestDay)
            weekly_workouts = sum(1 for d in periodized_days if not d.isRestDay)

            periodized_week = PlannedWeek(
                week_number=week_idx,
                phase_label=phase_label,
                days=periodized_days,
                total_weekly_sets=weekly_sets,
                total_workouts=weekly_workouts,
            )
            periodized_weeks.append(periodized_week)

        # 4. Whole-Plan Feasibility & Duration Evaluation
        feasibility_status, duration_diagnostics = self._evaluate_duration_feasibility(
            weeks=periodized_weeks,
            target_duration=request.targetWorkoutDurationMinutes,
        )

        all_diagnostics = list(structural_plan.diagnostics)
        if duration_diagnostics:
            all_diagnostics.extend(duration_diagnostics)

        # 5. Return Complete Periodized Plan
        return WorkoutPlanResponse(
            plan_id=structural_plan.planId,
            title=structural_plan.title,
            description=structural_plan.description,
            target_goal=structural_plan.targetGoal,
            fitness_level=structural_plan.fitnessLevel,
            split_type=structural_plan.splitType,
            training_days_per_week=structural_plan.trainingDaysPerWeek,
            total_weeks=total_weeks,
            weeks=periodized_weeks,
            applied_filters=dict(structural_plan.appliedFilters),
            feasibility_check_passed=True,
            duration_feasibility=feasibility_status,
            diagnostics=all_diagnostics,
            conflicting_filters=list(structural_plan.conflictingFilters),
        )

    # =========================================================================
    # EXERCISE PRESCRIPTION MAPPING
    # =========================================================================

    def _prescribe_exercise_for_week(
        self,
        exercise: PlannedExercise,
        goal_key: str,
        week_idx: int,
        block_number: int,
        week_in_block: int,
    ) -> PlannedExercise:
        """
        Derives deterministic sets, reps, rest, and RPE for a specific week.
        Applies block offset, phase progression, and deload rules.
        """
        slot_role = exercise.slotRole
        fallback = BaselinePrescription(
            base_sets=3,
            rep_min=8,
            rep_max=12,
            base_reps=10,
            rest_seconds=90,
            base_rpe=7.0,
            rationale="General-purpose baseline prescription target.",
        )
        baseline = self._prescription_framework.get((goal_key, slot_role), fallback)

        # Block-to-block progression offset (linear RPE bump capped at MAX_RPE)
        block_rpe_offset = min(1.0, (block_number - 1) * BLOCK_RPE_PROGRESSION_STEP)

        # Phase-Specific Prescription Derivation
        if week_in_block == 1:
            # Phase 1: Baseline Accumulation
            prescribed_set_count = baseline.base_sets
            target_reps = baseline.base_reps
            rep_min = baseline.rep_min
            rep_max = baseline.rep_max
            target_rpe = min(MAX_RPE, round(baseline.base_rpe + block_rpe_offset, 2))
            rest_sec = baseline.rest_seconds
            progression_note = "Baseline accumulation phase establishing movement exposure and work capacity."

        elif week_in_block == 2:
            # Phase 2: Volume Loading (+1 set to compound movements)
            if slot_role in [ExerciseSlotRole.PRIMARY_COMPOUND, ExerciseSlotRole.SECONDARY_COMPOUND]:
                prescribed_set_count = min(
                    MAX_SETS_PER_EXERCISE_NORMAL, baseline.base_sets + 1
                )
            else:
                prescribed_set_count = baseline.base_sets

            # Nudge target reps within bounds for accessories
            if slot_role in [ExerciseSlotRole.ACCESSORY_1, ExerciseSlotRole.ACCESSORY_2]:
                target_reps = min(baseline.rep_max, baseline.base_reps + 1)
            else:
                target_reps = baseline.base_reps

            rep_min = baseline.rep_min
            rep_max = baseline.rep_max
            target_rpe = min(MAX_RPE, round(baseline.base_rpe + block_rpe_offset, 2))
            rest_sec = baseline.rest_seconds
            progression_note = "Volume loading phase adding working set volume to primary and secondary movements."

        elif week_in_block == 3:
            # Phase 3: Intensity Peak (hold volume steady, elevate RPE, shift toward rep_min for compounds)
            prescribed_set_count = baseline.base_sets
            if slot_role == ExerciseSlotRole.PRIMARY_COMPOUND:
                target_reps = baseline.rep_min
                target_rpe = min(MAX_RPE, round(baseline.base_rpe + block_rpe_offset + 1.0, 2))
                rest_sec = min(180, baseline.rest_seconds + 30)
            elif slot_role == ExerciseSlotRole.SECONDARY_COMPOUND:
                target_reps = baseline.rep_min
                target_rpe = min(MAX_RPE, round(baseline.base_rpe + block_rpe_offset + 0.5, 2))
                rest_sec = baseline.rest_seconds
            elif slot_role in [ExerciseSlotRole.ACCESSORY_1, ExerciseSlotRole.ACCESSORY_2]:
                target_reps = baseline.base_reps
                target_rpe = min(MAX_RPE, round(baseline.base_rpe + block_rpe_offset + 0.5, 2))
                rest_sec = baseline.rest_seconds
            else:  # WARMUP_CORRECTIVE or CORE_MOBILITY
                target_reps = baseline.base_reps
                target_rpe = min(MAX_RPE, round(baseline.base_rpe + block_rpe_offset, 2))
                rest_sec = baseline.rest_seconds

            rep_min = baseline.rep_min
            rep_max = baseline.rep_max
            progression_note = "Intensity peak phase elevating target RPE and load while holding working volume steady."

        else:
            # Phase 4: Deload & Consolidation (bounded set reduction: 3->2, 2->1, 1->1; RPE reduced; exposure preserved)
            if baseline.base_sets >= 3:
                prescribed_set_count = 2
            elif baseline.base_sets == 2:
                prescribed_set_count = 1
            else:
                prescribed_set_count = MIN_SETS_PER_EXERCISE

            # Enforce deload bounds: never 0 sets, capped <= 3 sets
            prescribed_set_count = max(MIN_SETS_PER_EXERCISE, min(MAX_SETS_PER_EXERCISE_DELOAD, prescribed_set_count))

            target_reps = baseline.base_reps
            rep_min = baseline.rep_min
            rep_max = baseline.rep_max
            target_rpe = max(MIN_RPE, DEFAULT_DELOAD_RPE)
            rest_sec = baseline.rest_seconds
            progression_note = "Deload and consolidation phase applying bounded reduction in working sets and RPE demand to consolidate training."

        # Construct PlannedSet list
        prescribed_sets: List[PlannedSet] = []
        for s_idx in range(1, prescribed_set_count + 1):
            set_obj = PlannedSet(
                set_number=s_idx,
                target_reps=target_reps,
                target_reps_min=rep_min,
                target_reps_max=rep_max,
                target_rpe=target_rpe,
                rest_seconds=rest_sec,
                notes=f"Prescribed set {s_idx} of {prescribed_set_count}",
            )
            prescribed_sets.append(set_obj)

        # Estimate Exercise Duration
        exercise_seconds = sum(
            (s.targetReps * EXECUTION_SECONDS_PER_REP) + s.restSeconds
            for s in prescribed_sets
        ) + SETUP_SECONDS_PER_EXERCISE
        estimated_duration = max(1, int(round(exercise_seconds / 60.0)))

        return PlannedExercise(
            slot_role=exercise.slotRole,
            slot_index=exercise.slotIndex,
            exercise_id=exercise.exerciseId,
            name=exercise.name,
            movement_pattern=exercise.movementPattern,
            exercise_type=exercise.exerciseType,
            difficulty=exercise.difficulty,
            equipment=list(exercise.equipment),
            primary_muscles=list(exercise.primaryMuscles),
            prescribed_sets=prescribed_sets,
            total_sets=len(prescribed_sets),
            estimated_duration_minutes=estimated_duration,
            score=exercise.score,
            reasons=list(exercise.reasons),
            is_canonical_cv=exercise.isCanonicalCv,
            progression_note=progression_note,
            prescription_rationale=baseline.rationale,
        )

    # =========================================================================
    # DURATION ESTIMATION & FEASIBILITY
    # =========================================================================

    def _estimate_day_seconds(self, exercises: List[PlannedExercise]) -> float:
        """
        Calculates deterministic day execution seconds:
        sum(set_execution + rest + exercise_setup) + transitions_between_exercises
        """
        if not exercises:
            return 0.0

        total_exercise_sec = 0.0
        for ex in exercises:
            for s in ex.prescribedSets:
                total_exercise_sec += (s.targetReps * EXECUTION_SECONDS_PER_REP) + s.restSeconds
            total_exercise_sec += SETUP_SECONDS_PER_EXERCISE

        transition_sec = max(0, len(exercises) - 1) * TRANSITION_SECONDS_BETWEEN_EXERCISES
        return total_exercise_sec + transition_sec

    def _evaluate_duration_feasibility(
        self,
        weeks: List[PlannedWeek],
        target_duration: int,
    ) -> Tuple[DurationFeasibility, List[str]]:
        """
        Evaluates whether the prescribed plan fits within the requested target duration.

        Rules:
        - FEASIBLE: max estimated workout <= target_duration
        - POTENTIALLY_OVER_TARGET: target_duration < max estimated workout <= target_duration * 1.25
        - IMPOSSIBLE_UNDER_CONSTRAINTS: max estimated workout > target_duration * 1.25
        """
        diagnostics: List[str] = []
        max_duration = 0
        for w in weeks:
            for d in w.days:
                if not d.isRestDay and d.estimatedDurationMinutes > max_duration:
                    max_duration = d.estimatedDurationMinutes

        tolerance_ceiling = int(round(target_duration * OVER_TARGET_TOLERANCE_RATIO))

        if max_duration <= target_duration:
            return DurationFeasibility.FEASIBLE, diagnostics
        elif max_duration <= tolerance_ceiling:
            diagnostics.append(
                f"Estimated workout duration ({max_duration} min) slightly exceeds target ({target_duration} min) "
                f"but remains within 25% planning tolerance ceiling ({tolerance_ceiling} min)."
            )
            return DurationFeasibility.POTENTIALLY_OVER_TARGET, diagnostics
        else:
            diagnostics.append(
                f"Estimated workout duration ({max_duration} min) exceeds target ({target_duration} min) "
                f"by more than 25% tolerance. Plan requires {max_duration} min to execute all required compound, "
                f"accessory, and core movement slots without omitting prescribed volume."
            )
            return DurationFeasibility.IMPOSSIBLE_UNDER_CONSTRAINTS, diagnostics


# ============================================================================
# Global Singleton
# ============================================================================

_workout_periodization_service_instance: Optional[WorkoutPeriodizationService] = None


def get_workout_periodization_service() -> WorkoutPeriodizationService:
    """Returns the global WorkoutPeriodizationService singleton."""
    global _workout_periodization_service_instance
    if _workout_periodization_service_instance is None:
        _workout_periodization_service_instance = WorkoutPeriodizationService()
    return _workout_periodization_service_instance
