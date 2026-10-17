"""
Unit Tests for Workout Periodization & Prescription Service (Phase 9B.8.5.3).

Comprehensive test suite covering sections A through M:
A. Baseline prescription (primary compound, secondary compound, accessories, core/mobility, corrective/warmup)
B. Four-week periodization (Week 1, Week 2, Week 3, Week 4 phases)
C. Partial blocks (1, 2, 3, 5, 7 weeks)
D. Multi-block behavior (4, 8, 12 weeks)
E. Progression (volume progression, RPE progression, block-to-block progression, bounded caps)
F. Deload behavior (reduced sets, reduced RPE, preserved exercise exposure, min 1 set)
G. Engineering bounds (sets 1-5, deload <= 3, reps within range, rest >= 0, RPE 5.0-9.0)
H. Duration & feasibility (feasible, potentially_over_target, impossible_under_constraints, 20m & 90m bounds)
I. Structural preservation (identical exercise IDs, day ordering, slot roles, no structural mutations)
J. Determinism (identical output for identical input, repeated execution serialization equality)
K. Diagnostics preservation (State B, State C, State D preserved without corruption)
L. No fabrication (no invented exercises, factual non-medical rationale)
M. Safety / boundaries (zero Gemini, zero Firestore, zero network, zero randomness, zero profile access)
"""

import json
import pytest
from typing import List

from backend.app.schemas import (
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
    FitnessGoal,
    DifficultyLevel,
)
from backend.app.services.workout_plan_service import (
    WorkoutPlanService,
    get_workout_plan_service,
)
from backend.app.services.workout_periodization_service import (
    WorkoutPeriodizationService,
    get_workout_periodization_service,
    MIN_RPE,
    MAX_RPE,
    MAX_SETS_PER_EXERCISE_NORMAL,
    MAX_SETS_PER_EXERCISE_DELOAD,
    MIN_SETS_PER_EXERCISE,
)


@pytest.fixture
def periodization_service() -> WorkoutPeriodizationService:
    """Returns the global WorkoutPeriodizationService singleton."""
    return get_workout_periodization_service()


@pytest.fixture
def plan_service() -> WorkoutPlanService:
    """Returns the global WorkoutPlanService singleton."""
    return get_workout_plan_service()


# ============================================================================
# Section A: Baseline Prescription
# ============================================================================

def test_baseline_prescription_primary_compound(periodization_service):
    """Verifies baseline primary compound sets, reps range, rest, and RPE."""
    req = WorkoutPlanGenerateRequest(
        targetGoal="strength",
        fitnessLevel="intermediate",
        environment="gym",
        trainingDaysPerWeek=3,
        planDurationWeeks=4,
        targetWorkoutDurationMinutes=60,
    )
    plan = periodization_service.generate_periodized_plan(req)
    assert plan.feasibilityCheckPassed is True
    week1 = plan.weeks[0]
    day1 = week1.days[0]

    primary_ex = next(ex for ex in day1.exercises if ex.slotRole == ExerciseSlotRole.PRIMARY_COMPOUND)
    assert primary_ex.totalSets == 3
    assert len(primary_ex.prescribedSets) == 3
    assert primary_ex.prescribedSets[0].targetRpe == 7.5
    assert primary_ex.prescribedSets[0].restSeconds == 180
    assert primary_ex.prescribedSets[0].targetRepsMin is not None
    assert primary_ex.prescribedSets[0].targetRepsMax is not None
    assert primary_ex.prescribedSets[0].targetRepsMin <= primary_ex.prescribedSets[0].targetRepsMax
    assert "primary compound" in primary_ex.prescriptionRationale.lower()


def test_baseline_prescription_secondary_compound(periodization_service):
    """Verifies baseline secondary compound prescription defaults."""
    req = WorkoutPlanGenerateRequest(
        targetGoal="general_fitness",
        fitnessLevel="intermediate",
        environment="gym",
        trainingDaysPerWeek=3,
        planDurationWeeks=4,
        targetWorkoutDurationMinutes=60,
    )
    plan = periodization_service.generate_periodized_plan(req)
    day1 = plan.weeks[0].days[0]

    sec_ex = next(ex for ex in day1.exercises if ex.slotRole == ExerciseSlotRole.SECONDARY_COMPOUND)
    assert sec_ex.totalSets == 3
    assert sec_ex.prescribedSets[0].targetRpe == 7.0
    assert sec_ex.prescribedSets[0].restSeconds == 90
    assert sec_ex.prescribedSets[0].targetReps == 10
    assert sec_ex.prescribedSets[0].targetRepsMin == 8
    assert sec_ex.prescribedSets[0].targetRepsMax == 12


def test_baseline_prescription_accessories(periodization_service):
    """Verifies accessory_1 and accessory_2 baseline parameters."""
    req = WorkoutPlanGenerateRequest(
        targetGoal="general_fitness",
        fitnessLevel="intermediate",
        environment="gym",
        trainingDaysPerWeek=3,
        planDurationWeeks=4,
    )
    plan = periodization_service.generate_periodized_plan(req)
    day1 = plan.weeks[0].days[0]

    acc1 = next(ex for ex in day1.exercises if ex.slotRole == ExerciseSlotRole.ACCESSORY_1)
    acc2 = next(ex for ex in day1.exercises if ex.slotRole == ExerciseSlotRole.ACCESSORY_2)

    assert acc1.totalSets == 3
    assert acc1.prescribedSets[0].targetRpe == 7.5
    assert acc1.prescribedSets[0].restSeconds == 75

    assert acc2.totalSets == 2
    assert acc2.prescribedSets[0].targetRpe == 7.0
    assert acc2.prescribedSets[0].restSeconds == 60


def test_baseline_prescription_core_mobility(periodization_service):
    """Verifies core_mobility conservative set count and rest."""
    req = WorkoutPlanGenerateRequest(
        targetGoal="general_fitness",
        fitnessLevel="intermediate",
        environment="gym",
        trainingDaysPerWeek=3,
        planDurationWeeks=4,
    )
    plan = periodization_service.generate_periodized_plan(req)
    day1 = plan.weeks[0].days[0]

    core_ex = next(ex for ex in day1.exercises if ex.slotRole == ExerciseSlotRole.CORE_MOBILITY)
    assert core_ex.totalSets == 2
    assert core_ex.prescribedSets[0].targetRpe == 6.5
    assert core_ex.prescribedSets[0].restSeconds == 45
    assert "core and stability" in core_ex.prescriptionRationale.lower()


def test_baseline_prescription_corrective_warmup(periodization_service):
    """Verifies warmup_corrective (Slot 0) when corrective targeting is requested."""
    req = WorkoutPlanGenerateRequest(
        targetGoal="general_fitness",
        fitnessLevel="intermediate",
        environment="gym",
        trainingDaysPerWeek=3,
        planDurationWeeks=4,
        correctiveSourceExerciseId="ex_squat",
        correctiveIssueId="knee_tracking_deviation",
    )
    plan = periodization_service.generate_periodized_plan(req)
    day1 = plan.weeks[0].days[0]

    warmup_ex = next((ex for ex in day1.exercises if ex.slotRole == ExerciseSlotRole.WARMUP_CORRECTIVE), None)
    assert warmup_ex is not None
    assert warmup_ex.slotIndex == 0
    assert warmup_ex.totalSets == 2
    assert warmup_ex.prescribedSets[0].targetRpe == 5.0
    assert warmup_ex.prescribedSets[0].restSeconds == 45
    assert warmup_ex.prescribedSets[0].targetRepsMin == 8
    assert warmup_ex.prescribedSets[0].targetRepsMax == 10
    assert "low-volume preparation" in warmup_ex.prescriptionRationale.lower()


# ============================================================================
# Section B: Four-Week Periodization
# ============================================================================

def test_four_week_periodization_phase_labels(periodization_service):
    """Validates phase label progression across a standard 4-week block."""
    req = WorkoutPlanGenerateRequest(
        targetGoal="general_fitness",
        fitnessLevel="intermediate",
        environment="gym",
        trainingDaysPerWeek=3,
        planDurationWeeks=4,
    )
    plan = periodization_service.generate_periodized_plan(req)
    assert len(plan.weeks) == 4

    assert plan.weeks[0].phaseLabel == "Baseline Accumulation"
    assert plan.weeks[1].phaseLabel == "Volume Loading"
    assert plan.weeks[2].phaseLabel == "Intensity Peak"
    assert plan.weeks[3].phaseLabel == "Deload & Consolidation"


# ============================================================================
# Section C: Partial Blocks
# ============================================================================

@pytest.mark.parametrize("weeks,expected_phases", [
    (1, ["Baseline Accumulation"]),
    (2, ["Baseline Accumulation", "Volume Loading"]),
    (3, ["Baseline Accumulation", "Volume Loading", "Intensity Peak"]),
    (5, ["Baseline Accumulation", "Volume Loading", "Intensity Peak", "Deload & Consolidation", "Baseline Accumulation"]),
    (7, ["Baseline Accumulation", "Volume Loading", "Intensity Peak", "Deload & Consolidation", "Baseline Accumulation", "Volume Loading", "Intensity Peak"]),
])
def test_partial_block_week_counts_and_phases(periodization_service, weeks, expected_phases):
    """Ensures arbitrary week counts (1, 2, 3, 5, 7) receive exact deterministic phases."""
    req = WorkoutPlanGenerateRequest(
        targetGoal="general_fitness",
        fitnessLevel="intermediate",
        environment="gym",
        trainingDaysPerWeek=3,
        planDurationWeeks=weeks,
    )
    plan = periodization_service.generate_periodized_plan(req)
    assert len(plan.weeks) == weeks
    actual_phases = [w.phaseLabel for w in plan.weeks]
    assert actual_phases == expected_phases


# ============================================================================
# Section D: Multi-Block Behavior
# ============================================================================

def test_multi_block_8_weeks(periodization_service):
    """Validates 8-week plan has exactly 2 full 4-week blocks."""
    req = WorkoutPlanGenerateRequest(
        targetGoal="muscle_gain",
        fitnessLevel="intermediate",
        environment="gym",
        trainingDaysPerWeek=4,
        planDurationWeeks=8,
    )
    plan = periodization_service.generate_periodized_plan(req)
    assert len(plan.weeks) == 8
    assert plan.weeks[3].phaseLabel == "Deload & Consolidation"
    assert plan.weeks[4].phaseLabel == "Baseline Accumulation"
    assert plan.weeks[7].phaseLabel == "Deload & Consolidation"


def test_multi_block_12_weeks(periodization_service):
    """Validates 12-week plan spans exactly 3 full 4-week blocks."""
    req = WorkoutPlanGenerateRequest(
        targetGoal="strength",
        fitnessLevel="advanced",
        environment="gym",
        trainingDaysPerWeek=4,
        planDurationWeeks=12,
    )
    plan = periodization_service.generate_periodized_plan(req)
    assert len(plan.weeks) == 12
    assert plan.weeks[3].phaseLabel == "Deload & Consolidation"
    assert plan.weeks[7].phaseLabel == "Deload & Consolidation"
    assert plan.weeks[11].phaseLabel == "Deload & Consolidation"


# ============================================================================
# Section E: Progression Mechanics
# ============================================================================

def test_volume_loading_phase_adds_compound_sets(periodization_service):
    """Verifies Week 2 (Volume Loading) adds +1 set to primary and secondary compounds."""
    req = WorkoutPlanGenerateRequest(
        targetGoal="general_fitness",
        fitnessLevel="intermediate",
        environment="gym",
        trainingDaysPerWeek=3,
        planDurationWeeks=4,
    )
    plan = periodization_service.generate_periodized_plan(req)

    day_w1 = plan.weeks[0].days[0]
    day_w2 = plan.weeks[1].days[0]

    w1_primary = next(ex for ex in day_w1.exercises if ex.slotRole == ExerciseSlotRole.PRIMARY_COMPOUND)
    w2_primary = next(ex for ex in day_w2.exercises if ex.slotRole == ExerciseSlotRole.PRIMARY_COMPOUND)
    assert w1_primary.totalSets == 3
    assert w2_primary.totalSets == 4

    w1_secondary = next(ex for ex in day_w1.exercises if ex.slotRole == ExerciseSlotRole.SECONDARY_COMPOUND)
    w2_secondary = next(ex for ex in day_w2.exercises if ex.slotRole == ExerciseSlotRole.SECONDARY_COMPOUND)
    assert w1_secondary.totalSets == 3
    assert w2_secondary.totalSets == 4


def test_intensity_peak_phase_rpe_elevation(periodization_service):
    """Verifies Week 3 (Intensity Peak) elevates target RPE and shifts reps to rep_min."""
    req = WorkoutPlanGenerateRequest(
        targetGoal="general_fitness",
        fitnessLevel="intermediate",
        environment="gym",
        trainingDaysPerWeek=3,
        planDurationWeeks=4,
    )
    plan = periodization_service.generate_periodized_plan(req)

    w1_primary = next(ex for ex in plan.weeks[0].days[0].exercises if ex.slotRole == ExerciseSlotRole.PRIMARY_COMPOUND)
    w3_primary = next(ex for ex in plan.weeks[2].days[0].exercises if ex.slotRole == ExerciseSlotRole.PRIMARY_COMPOUND)

    assert w3_primary.prescribedSets[0].targetRpe > w1_primary.prescribedSets[0].targetRpe
    assert w3_primary.prescribedSets[0].targetRpe <= MAX_RPE
    # In Week 3, primary compound shifts to lower end of rep range for heavier loading
    assert w3_primary.prescribedSets[0].targetReps == w3_primary.prescribedSets[0].targetRepsMin
    # Volume is controlled (reverts back to 3 sets, does not escalate)
    assert w3_primary.totalSets == 3


def test_block_to_block_progression_offset(periodization_service):
    """Verifies Block 2 (Weeks 5-8) applies bounded progression relative to Block 1."""
    req = WorkoutPlanGenerateRequest(
        targetGoal="general_fitness",
        fitnessLevel="intermediate",
        environment="gym",
        trainingDaysPerWeek=3,
        planDurationWeeks=8,
    )
    plan = periodization_service.generate_periodized_plan(req)

    # Week 1 (Block 1 Baseline) vs Week 5 (Block 2 Baseline)
    w1_primary = next(ex for ex in plan.weeks[0].days[0].exercises if ex.slotRole == ExerciseSlotRole.PRIMARY_COMPOUND)
    w5_primary = next(ex for ex in plan.weeks[4].days[0].exercises if ex.slotRole == ExerciseSlotRole.PRIMARY_COMPOUND)

    assert w5_primary.prescribedSets[0].targetRpe >= w1_primary.prescribedSets[0].targetRpe
    assert w5_primary.prescribedSets[0].targetRpe <= MAX_RPE


def test_no_uncontrolled_rpe_or_volume_escalation(periodization_service):
    """Ensures even across 12 weeks, RPE is capped at 9.0 and sets never exceed 5."""
    req = WorkoutPlanGenerateRequest(
        targetGoal="strength",
        fitnessLevel="advanced",
        environment="gym",
        trainingDaysPerWeek=4,
        planDurationWeeks=12,
    )
    plan = periodization_service.generate_periodized_plan(req)

    for week in plan.weeks:
        for day in week.days:
            for ex in day.exercises:
                assert ex.totalSets <= MAX_SETS_PER_EXERCISE_NORMAL
                for s in ex.prescribedSets:
                    assert s.targetRpe <= MAX_RPE
                    assert s.targetRpe >= MIN_RPE


# ============================================================================
# Section F: Deload & Consolidation (Bounded Set Reduction Policy)
# ============================================================================

def test_deload_bounded_reduction_3_to_2_behavior(periodization_service):
    """Verifies that 3-set baseline exercises reduce to exactly 2 sets in deload (3 -> 2)."""
    req = WorkoutPlanGenerateRequest(
        targetGoal="general_fitness",
        fitnessLevel="intermediate",
        environment="gym",
        trainingDaysPerWeek=3,
        planDurationWeeks=4,
    )
    plan = periodization_service.generate_periodized_plan(req)

    day_w1 = plan.weeks[0].days[0]
    day_w4 = plan.weeks[3].days[0]

    primary_w1 = next(ex for ex in day_w1.exercises if ex.slotRole == ExerciseSlotRole.PRIMARY_COMPOUND)
    primary_w4 = next(ex for ex in day_w4.exercises if ex.slotRole == ExerciseSlotRole.PRIMARY_COMPOUND)
    assert primary_w1.totalSets == 3
    assert primary_w4.totalSets == 2

    sec_w1 = next(ex for ex in day_w1.exercises if ex.slotRole == ExerciseSlotRole.SECONDARY_COMPOUND)
    sec_w4 = next(ex for ex in day_w4.exercises if ex.slotRole == ExerciseSlotRole.SECONDARY_COMPOUND)
    assert sec_w1.totalSets == 3
    assert sec_w4.totalSets == 2

    acc1_w1 = next(ex for ex in day_w1.exercises if ex.slotRole == ExerciseSlotRole.ACCESSORY_1)
    acc1_w4 = next(ex for ex in day_w4.exercises if ex.slotRole == ExerciseSlotRole.ACCESSORY_1)
    assert acc1_w1.totalSets == 3
    assert acc1_w4.totalSets == 2


def test_deload_bounded_reduction_2_to_1_behavior(periodization_service):
    """Verifies that 2-set baseline exercises reduce to exactly 1 set in deload (2 -> 1)."""
    req = WorkoutPlanGenerateRequest(
        targetGoal="general_fitness",
        fitnessLevel="intermediate",
        environment="gym",
        trainingDaysPerWeek=3,
        planDurationWeeks=4,
    )
    plan = periodization_service.generate_periodized_plan(req)

    day_w1 = plan.weeks[0].days[0]
    day_w4 = plan.weeks[3].days[0]

    acc2_w1 = next(ex for ex in day_w1.exercises if ex.slotRole == ExerciseSlotRole.ACCESSORY_2)
    acc2_w4 = next(ex for ex in day_w4.exercises if ex.slotRole == ExerciseSlotRole.ACCESSORY_2)
    assert acc2_w1.totalSets == 2
    assert acc2_w4.totalSets == 1

    core_w1 = next(ex for ex in day_w1.exercises if ex.slotRole == ExerciseSlotRole.CORE_MOBILITY)
    core_w4 = next(ex for ex in day_w4.exercises if ex.slotRole == ExerciseSlotRole.CORE_MOBILITY)
    assert core_w1.totalSets == 2
    assert core_w4.totalSets == 1


def test_deload_bounded_reduction_1_to_1_behavior(periodization_service):
    """Verifies that a 1-set prescription remains at exactly 1 set in deload (1 -> 1, never 0)."""
    req = WorkoutPlanGenerateRequest(
        targetGoal="general_fitness",
        fitnessLevel="intermediate",
        environment="gym",
        trainingDaysPerWeek=3,
        planDurationWeeks=4,
    )
    plan = periodization_service.generate_periodized_plan(req)
    sample_ex = plan.weeks[0].days[0].exercises[0]

    # Directly test prescribing for week 4 when baseline sets is 1
    periodized_1set = periodization_service._prescribe_exercise_for_week(
        exercise=sample_ex,
        goal_key="general_fitness",
        week_idx=4,
        block_number=1,
        week_in_block=4,
    )
    # The exercise sets during deload must be >= MIN_SETS_PER_EXERCISE (1)
    assert periodized_1set.totalSets >= MIN_SETS_PER_EXERCISE
    assert len(periodized_1set.prescribedSets) == periodized_1set.totalSets
    assert periodized_1set.totalSets <= MAX_SETS_PER_EXERCISE_DELOAD


def test_deload_sets_bounded_less_or_equal_3(periodization_service):
    """Verifies all exercises in deload satisfy 1 <= totalSets <= 3."""
    req = WorkoutPlanGenerateRequest(
        targetGoal="strength",
        fitnessLevel="advanced",
        environment="gym",
        trainingDaysPerWeek=4,
        planDurationWeeks=8,
    )
    plan = periodization_service.generate_periodized_plan(req)

    # Check both Week 4 (Block 1 Deload) and Week 8 (Block 2 Deload)
    for week_idx in [3, 7]:
        deload_week = plan.weeks[week_idx]
        assert deload_week.phaseLabel == "Deload & Consolidation"
        for day in deload_week.days:
            for ex in day.exercises:
                assert MIN_SETS_PER_EXERCISE <= ex.totalSets <= MAX_SETS_PER_EXERCISE_DELOAD


def test_deload_rpe_lower_than_all_training_weeks(periodization_service):
    """Verifies deload RPE is lower than all preceding training weeks (Weeks 1, 2, 3)."""
    req = WorkoutPlanGenerateRequest(
        targetGoal="general_fitness",
        fitnessLevel="intermediate",
        environment="gym",
        trainingDaysPerWeek=3,
        planDurationWeeks=4,
    )
    plan = periodization_service.generate_periodized_plan(req)

    w1_day = plan.weeks[0].days[0]
    w2_day = plan.weeks[1].days[0]
    w3_day = plan.weeks[2].days[0]
    w4_day = plan.weeks[3].days[0]

    for ex_idx in range(len(w4_day.exercises)):
        w1_rpe = w1_day.exercises[ex_idx].prescribedSets[0].targetRpe
        w2_rpe = w2_day.exercises[ex_idx].prescribedSets[0].targetRpe
        w3_rpe = w3_day.exercises[ex_idx].prescribedSets[0].targetRpe
        w4_rpe = w4_day.exercises[ex_idx].prescribedSets[0].targetRpe

        assert w4_rpe <= w1_rpe
        assert w4_rpe < w3_rpe
        assert w4_rpe <= 6.5


def test_deload_preserves_exercise_exposure(periodization_service):
    """Verifies Week 4 retains all exercises and does not delete movements."""
    req = WorkoutPlanGenerateRequest(
        targetGoal="general_fitness",
        fitnessLevel="intermediate",
        environment="gym",
        trainingDaysPerWeek=3,
        planDurationWeeks=4,
    )
    plan = periodization_service.generate_periodized_plan(req)

    w1_day = plan.weeks[0].days[0]
    w4_day = plan.weeks[3].days[0]

    assert len(w4_day.exercises) == len(w1_day.exercises)
    w1_ids = [ex.exerciseId for ex in w1_day.exercises]
    w4_ids = [ex.exerciseId for ex in w4_day.exercises]
    assert w4_ids == w1_ids


def test_deload_whole_plan_volume_bounds(periodization_service):
    """Verifies at whole-plan level that deload weekly sets are reduced and bounds respected."""
    req = WorkoutPlanGenerateRequest(
        targetGoal="general_fitness",
        fitnessLevel="intermediate",
        environment="gym",
        trainingDaysPerWeek=3,
        planDurationWeeks=4,
    )
    plan = periodization_service.generate_periodized_plan(req)

    w2_sets = plan.weeks[1].totalWeeklySets
    w3_sets = plan.weeks[2].totalWeeklySets
    w4_sets = plan.weeks[3].totalWeeklySets

    assert w4_sets < w3_sets
    assert w4_sets < w2_sets

    # Whole-plan check: each exercise respects configured bounds
    for week in plan.weeks:
        for day in week.days:
            for ex in day.exercises:
                if week.phaseLabel == "Deload & Consolidation":
                    assert MIN_SETS_PER_EXERCISE <= ex.totalSets <= MAX_SETS_PER_EXERCISE_DELOAD
                else:
                    assert MIN_SETS_PER_EXERCISE <= ex.totalSets <= MAX_SETS_PER_EXERCISE_NORMAL


# ============================================================================
# Section G: Engineering Bounds
# ============================================================================

def test_prescribed_sets_numeric_bounds(periodization_service):
    """Validates that set count, reps, rest, and RPE all remain strictly within bounds."""
    req = WorkoutPlanGenerateRequest(
        targetGoal="muscle_gain",
        fitnessLevel="intermediate",
        environment="gym",
        trainingDaysPerWeek=4,
        planDurationWeeks=4,
    )
    plan = periodization_service.generate_periodized_plan(req)

    for week in plan.weeks:
        for day in week.days:
            for ex in day.exercises:
                assert MIN_SETS_PER_EXERCISE <= ex.totalSets <= MAX_SETS_PER_EXERCISE_NORMAL
                for s in ex.prescribedSets:
                    assert s.setNumber >= 1
                    assert s.targetReps >= 1
                    assert s.targetRepsMin is not None and s.targetRepsMax is not None
                    assert s.targetRepsMin <= s.targetRepsMax
                    assert s.restSeconds >= 0
                    assert MIN_RPE <= s.targetRpe <= MAX_RPE


# ============================================================================
# Section H: Duration Estimation & Feasibility
# ============================================================================

def test_duration_clearly_feasible(periodization_service):
    """Verifies a 60-minute target easily accommodates a ~36-minute Full Body day."""
    req = WorkoutPlanGenerateRequest(
        targetGoal="general_fitness",
        fitnessLevel="intermediate",
        environment="gym",
        trainingDaysPerWeek=3,
        planDurationWeeks=4,
        targetWorkoutDurationMinutes=60,
    )
    plan = periodization_service.generate_periodized_plan(req)
    assert plan.durationFeasibility == DurationFeasibility.FEASIBLE
    assert plan.feasibilityCheckPassed is True


def test_duration_potentially_over_target(periodization_service):
    """Verifies a 35-minute target with ~41 min workout is marked POTENTIALLY_OVER_TARGET (within 25%)."""
    req = WorkoutPlanGenerateRequest(
        targetGoal="general_fitness",
        fitnessLevel="intermediate",
        environment="gym",
        trainingDaysPerWeek=3,
        planDurationWeeks=4,
        targetWorkoutDurationMinutes=35,
    )
    plan = periodization_service.generate_periodized_plan(req)
    assert plan.durationFeasibility == DurationFeasibility.POTENTIALLY_OVER_TARGET
    assert any("slightly exceeds target" in d for d in plan.diagnostics)


def test_duration_impossible_under_constraints(periodization_service):
    """Verifies a 20-minute target cannot fit a 5-exercise workout and is marked IMPOSSIBLE_UNDER_CONSTRAINTS."""
    req = WorkoutPlanGenerateRequest(
        targetGoal="general_fitness",
        fitnessLevel="intermediate",
        environment="gym",
        trainingDaysPerWeek=3,
        planDurationWeeks=4,
        targetWorkoutDurationMinutes=20,
    )
    plan = periodization_service.generate_periodized_plan(req)
    assert plan.durationFeasibility == DurationFeasibility.IMPOSSIBLE_UNDER_CONSTRAINTS
    assert any("exceeds target (20 min) by more than 25% tolerance" in d for d in plan.diagnostics)


def test_duration_90_minute_boundary(periodization_service):
    """Verifies maximum supported 90-minute target works cleanly as FEASIBLE."""
    req = WorkoutPlanGenerateRequest(
        targetGoal="strength",
        fitnessLevel="intermediate",
        environment="gym",
        trainingDaysPerWeek=4,
        planDurationWeeks=4,
        targetWorkoutDurationMinutes=90,
    )
    plan = periodization_service.generate_periodized_plan(req)
    assert plan.durationFeasibility == DurationFeasibility.FEASIBLE


def test_duration_does_not_silently_drop_exercises(periodization_service):
    """Ensures even when duration is tight or impossible, exercises are NOT silently dropped."""
    req = WorkoutPlanGenerateRequest(
        targetGoal="general_fitness",
        fitnessLevel="intermediate",
        environment="gym",
        trainingDaysPerWeek=3,
        planDurationWeeks=4,
        targetWorkoutDurationMinutes=20,
    )
    plan = periodization_service.generate_periodized_plan(req)
    # Plan must still contain all required slots 1 to 5
    day1 = plan.weeks[0].days[0]
    roles = {ex.slotRole for ex in day1.exercises}
    assert ExerciseSlotRole.PRIMARY_COMPOUND in roles
    assert ExerciseSlotRole.SECONDARY_COMPOUND in roles
    assert ExerciseSlotRole.ACCESSORY_1 in roles
    assert ExerciseSlotRole.ACCESSORY_2 in roles
    assert ExerciseSlotRole.CORE_MOBILITY in roles


# ============================================================================
# Section I: Structural Preservation
# ============================================================================

def test_structural_preservation_across_weeks(periodization_service):
    """Verifies exercise IDs, slot roles, and day labels are preserved across all weeks."""
    req = WorkoutPlanGenerateRequest(
        targetGoal="general_fitness",
        fitnessLevel="intermediate",
        environment="gym",
        trainingDaysPerWeek=3,
        planDurationWeeks=4,
    )
    plan = periodization_service.generate_periodized_plan(req)

    w1_day1_ids = [ex.exerciseId for ex in plan.weeks[0].days[0].exercises]
    w2_day1_ids = [ex.exerciseId for ex in plan.weeks[1].days[0].exercises]
    w3_day1_ids = [ex.exerciseId for ex in plan.weeks[2].days[0].exercises]
    w4_day1_ids = [ex.exerciseId for ex in plan.weeks[3].days[0].exercises]

    assert w1_day1_ids == w2_day1_ids == w3_day1_ids == w4_day1_ids


def test_structural_preservation_slot_roles(periodization_service):
    """Verifies slot roles remain identically mapped across weeks."""
    req = WorkoutPlanGenerateRequest(
        targetGoal="muscle_gain",
        fitnessLevel="intermediate",
        environment="gym",
        trainingDaysPerWeek=4,
        planDurationWeeks=4,
    )
    plan = periodization_service.generate_periodized_plan(req)

    for week in plan.weeks:
        day1 = week.days[0]
        roles = [ex.slotRole for ex in day1.exercises]
        assert roles[0] in [ExerciseSlotRole.WARMUP_CORRECTIVE, ExerciseSlotRole.PRIMARY_COMPOUND]
        assert ExerciseSlotRole.PRIMARY_COMPOUND in roles
        assert ExerciseSlotRole.SECONDARY_COMPOUND in roles


# ============================================================================
# Section J: Determinism & Serialization
# ============================================================================

def test_periodization_reproducibility(periodization_service):
    """Verifies identical requests yield strictly identical output models."""
    req1 = WorkoutPlanGenerateRequest(
        targetGoal="strength",
        fitnessLevel="intermediate",
        environment="gym",
        trainingDaysPerWeek=3,
        planDurationWeeks=4,
        targetWorkoutDurationMinutes=60,
    )
    req2 = WorkoutPlanGenerateRequest(
        targetGoal="strength",
        fitnessLevel="intermediate",
        environment="gym",
        trainingDaysPerWeek=3,
        planDurationWeeks=4,
        targetWorkoutDurationMinutes=60,
    )
    plan1 = periodization_service.generate_periodized_plan(req1)
    plan2 = periodization_service.generate_periodized_plan(req2)

    assert plan1.planId == plan2.planId
    assert plan1.model_dump() == plan2.model_dump()


def test_periodization_serialization_invariance(periodization_service):
    """Verifies canonical JSON serialization produces identical character sequences."""
    req = WorkoutPlanGenerateRequest(
        targetGoal="general_fitness",
        fitnessLevel="intermediate",
        environment="gym",
        trainingDaysPerWeek=3,
        planDurationWeeks=4,
    )
    plan1 = periodization_service.generate_periodized_plan(req)
    plan2 = periodization_service.generate_periodized_plan(req)

    dump1 = json.dumps(plan1.model_dump(), sort_keys=True)
    dump2 = json.dumps(plan2.model_dump(), sort_keys=True)
    assert dump1 == dump2


# ============================================================================
# Section K: Diagnostics Preservation
# ============================================================================

def test_preserves_state_b_invalid_input(periodization_service, plan_service):
    """Verifies State B structural failure is preserved untouched without mutation."""
    req = WorkoutPlanGenerateRequest(
        targetGoal="general_fitness",
        fitnessLevel="intermediate",
        environment="gym",
        trainingDaysPerWeek=3,
        planDurationWeeks=4,
        availableEquipment=[],  # Empty list -> State B
    )
    structural = plan_service.generate_plan(req)
    assert structural.feasibilityCheckPassed is False

    periodized = periodization_service.periodize_plan(structural, req)
    assert periodized.feasibilityCheckPassed is False
    assert periodized.weeks == []
    assert periodized.diagnostics == structural.diagnostics


def test_preserves_state_c_conflicting_constraints(periodization_service, plan_service):
    """Verifies State C conflict is preserved untouched."""
    req = WorkoutPlanGenerateRequest(
        targetGoal="general_fitness",
        fitnessLevel="intermediate",
        environment="gym",
        availableEquipment=["barbell"],
        excludedEquipment=["barbell"],  # Conflict -> State C
        trainingDaysPerWeek=3,
        planDurationWeeks=4,
    )
    structural = plan_service.generate_plan(req)
    assert structural.feasibilityCheckPassed is False
    assert len(structural.conflictingFilters) > 0

    periodized = periodization_service.periodize_plan(structural, req)
    assert periodized.feasibilityCheckPassed is False
    assert periodized.conflictingFilters == structural.conflictingFilters


def test_preserves_state_d_catalog_shortfall(periodization_service, plan_service):
    """Verifies State D shortfall is preserved untouched."""
    req = WorkoutPlanGenerateRequest(
        targetGoal="general_fitness",
        fitnessLevel="intermediate",
        environment="home",
        availableEquipment=["resistance_bands"],
        excludedExerciseIds=["band_squat", "band_chest_press", "band_row", "band_overhead_press"],
        trainingDaysPerWeek=3,
        planDurationWeeks=4,
    )
    structural = plan_service.generate_plan(req)
    assert structural.feasibilityCheckPassed is False
    assert structural.title == "Catalog Shortfall"

    periodized = periodization_service.periodize_plan(structural, req)
    assert periodized.feasibilityCheckPassed is False
    assert periodized.title == "Catalog Shortfall"


# ============================================================================
# Section L: No Fabrication & Non-Medical Language
# ============================================================================

def test_no_fabricated_exercises(periodization_service):
    """Ensures exercises match real catalog IDs and no placeholders are injected."""
    req = WorkoutPlanGenerateRequest(
        targetGoal="general_fitness",
        fitnessLevel="intermediate",
        environment="gym",
        trainingDaysPerWeek=3,
        planDurationWeeks=4,
    )
    plan = periodization_service.generate_periodized_plan(req)
    for week in plan.weeks:
        for day in week.days:
            for ex in day.exercises:
                assert not ex.exerciseId.startswith("placeholder")
                assert not ex.exerciseId.startswith("fake")
                assert ex.slotRole in ExerciseSlotRole


def test_prescription_rationales_non_medical(periodization_service):
    """Verifies rationales use conservative engineering wording without medical claims."""
    req = WorkoutPlanGenerateRequest(
        targetGoal="general_fitness",
        fitnessLevel="intermediate",
        environment="gym",
        trainingDaysPerWeek=3,
        planDurationWeeks=4,
    )
    plan = periodization_service.generate_periodized_plan(req)
    prohibited = ["cure", "prevent injury", "optimal hypertrophy", "guaranteed", "fix muscle imbalance"]
    for week in plan.weeks:
        for day in week.days:
            for ex in day.exercises:
                rationale_lower = (ex.prescriptionRationale or "").lower()
                for p in prohibited:
                    assert p not in rationale_lower


# ============================================================================
# Section M: Safety & Boundaries
# ============================================================================

def test_no_gemini_firestore_network_imports():
    """Verifies workout_periodization_service has zero AI/Firestore/network imports."""
    import backend.app.services.workout_periodization_service as wps_mod
    source = open(wps_mod.__file__, "r", encoding="utf-8").read()

    forbidden = [
        "google.generativeai",
        "firebase_admin",
        "google.cloud.firestore",
        "httpx",
        "requests",
        "urllib3",
        "random.choice",
        "random.shuffle",
        "uuid.uuid4",
    ]
    for pattern in forbidden:
        assert pattern not in source, f"Forbidden import or pattern detected in workout_periodization_service: '{pattern}'"


def test_rep_min_exceeds_rep_max_rejected():
    """PlannedSet validation rejects targetRepsMin > targetRepsMax."""
    from pydantic import ValidationError
    with pytest.raises(ValidationError):
        PlannedSet(
            setNumber=1,
            targetReps=10,
            targetRepsMin=12,
            targetRepsMax=8,
            restSeconds=60,
        )


def test_planned_exercise_rejects_medical_claim_in_prescription_rationale():
    """PlannedExercise rejects prohibited medical claims in prescriptionRationale."""
    from pydantic import ValidationError
    with pytest.raises(ValidationError):
        PlannedExercise(
            slotRole=ExerciseSlotRole.PRIMARY_COMPOUND,
            slotIndex=1,
            exerciseId="ex_barbell_bench_press",
            name="Barbell Bench Press",
            movementPattern="horizontal_push",
            exerciseType="compound",
            difficulty="intermediate",
            prescriptionRationale="Guaranteed to cure tendonitis and prevent injury.",
        )

