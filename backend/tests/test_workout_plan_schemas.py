"""
Unit Tests for Workout Plan Schemas & Domain Models (Phase 9B.8.5.1).

Validates:
1. Taxonomy integration and enum consistency (WorkoutSplitType, ExerciseSlotRole, BlockPhase).
2. 4-Week Block Periodization helper mappings across 1–12 weeks.
3. PlannedSet bounds, constraints, and camelCase alias serialization.
4. PlannedExercise validation, slot role neutrality, and non-medical language enforcement.
5. PlannedWorkoutDay & PlannedWeek metric auto-population and bounds validation.
6. WorkoutPlanGenerateRequest parameter boundaries (days 1-6, weeks 1-12, duration 20-90m).
7. WorkoutPlanResponse schema integrity and feasibility flags.
8. Deterministic Plan ID generation (reproducibility, canonical hashing, order invariance).
9. Schema export and backward compatibility.
"""

import pytest
from pydantic import ValidationError

from backend.app.schemas import (
    WorkoutSplitType,
    ExerciseSlotRole,
    BlockPhase,
    PlannedSet,
    PlannedExercise,
    PlannedWorkoutDay,
    PlannedWeek,
    WorkoutPlanGenerateRequest,
    WorkoutPlanResponse,
    generate_deterministic_plan_id,
    get_block_phase_label,
    get_block_number,
    MovementPattern,
    ExerciseType,
    DifficultyLevel,
    FitnessGoal,
    EquipmentType,
    MuscleGroup,
)


# ============================================================================
# 1. Enums & Block Periodization Semantics
# ============================================================================

def test_workout_split_types():
    """Verifies all supported split types exist and match specification."""
    assert WorkoutSplitType.FULL_BODY.value == "full_body"
    assert WorkoutSplitType.UPPER_LOWER.value == "upper_lower"
    assert WorkoutSplitType.PUSH_PULL_LEGS.value == "push_pull_legs"
    assert len(WorkoutSplitType) == 3


def test_exercise_slot_roles_neutrality():
    """Verifies slot roles use neutral, objective terminology (no neural-demand claims)."""
    expected_roles = {
        "warmup_corrective",
        "primary_compound",
        "secondary_compound",
        "accessory_1",
        "accessory_2",
        "core_mobility",
    }
    actual_roles = {role.value for role in ExerciseSlotRole}
    assert actual_roles == expected_roles


def test_four_week_block_phase_progression_12_weeks():
    """
    Validates deterministic 4-week block periodization across all 12 weeks:
    Week 1: Baseline Accumulation
    Week 2: Volume Loading
    Week 3: Intensity Peak
    Week 4: Deload & Consolidation
    Repeated for Block 2 (Weeks 5-8) and Block 3 (Weeks 9-12).
    """
    expected_phases = [
        "Baseline Accumulation",
        "Volume Loading",
        "Intensity Peak",
        "Deload & Consolidation",
    ]

    for week in range(1, 13):
        phase = get_block_phase_label(week)
        expected_phase = expected_phases[(week - 1) % 4]
        assert phase == expected_phase, f"Week {week} phase mismatch: got '{phase}', expected '{expected_phase}'"

        block_num = get_block_number(week)
        expected_block = ((week - 1) // 4) + 1
        assert block_num == expected_block, f"Week {week} block mismatch: got {block_num}, expected {expected_block}"


# ============================================================================
# 2. PlannedSet Validation
# ============================================================================

def test_planned_set_valid_instantiation():
    """Validates PlannedSet parses correctly with snake_case and camelCase aliases."""
    set_obj = PlannedSet(
        set_number=1,
        target_reps=8,
        target_rpe=8.5,
        rest_seconds=90,
        notes="Control eccentric phase",
    )
    assert set_obj.setNumber == 1
    assert set_obj.targetReps == 8
    assert set_obj.targetRpe == 8.5
    assert set_obj.restSeconds == 90
    assert set_obj.notes == "Control eccentric phase"

    # Verify camelCase serialization (default model_dump)
    dumped_camel = set_obj.model_dump()
    assert dumped_camel["setNumber"] == 1
    assert dumped_camel["targetReps"] == 8
    assert dumped_camel["targetRpe"] == 8.5
    assert dumped_camel["restSeconds"] == 90

    # Verify snake_case alias serialization (by_alias=True)
    dumped_snake = set_obj.model_dump(by_alias=True)
    assert dumped_snake["set_number"] == 1
    assert dumped_snake["target_reps"] == 8
    assert dumped_snake["target_rpe"] == 8.5
    assert dumped_snake["rest_seconds"] == 90


def test_planned_set_invalid_bounds():
    """Rejects negative reps, zero setNumber, or out-of-range RPE."""
    with pytest.raises(ValidationError):
        PlannedSet(setNumber=0, targetReps=10, restSeconds=60)

    with pytest.raises(ValidationError):
        PlannedSet(setNumber=1, targetReps=0, restSeconds=60)

    with pytest.raises(ValidationError):
        PlannedSet(setNumber=1, targetReps=10, restSeconds=-1)

    with pytest.raises(ValidationError):
        PlannedSet(setNumber=1, targetReps=10, restSeconds=60, targetRpe=11.0)


# ============================================================================
# 3. PlannedExercise Validation & Non-Medical Language Enforcement
# ============================================================================

def test_planned_exercise_valid_instantiation():
    """Validates PlannedExercise with valid catalog types and automatic totalSets calculation."""
    sets = [
        PlannedSet(setNumber=1, targetReps=8, targetRpe=8.0, restSeconds=120),
        PlannedSet(setNumber=2, targetReps=8, targetRpe=8.0, restSeconds=120),
        PlannedSet(setNumber=3, targetReps=8, targetRpe=8.5, restSeconds=120),
    ]

    exercise = PlannedExercise(
        slot_role=ExerciseSlotRole.PRIMARY_COMPOUND,
        slot_index=1,
        exercise_id="ex_barbell_bench_press",
        name="Barbell Bench Press",
        movement_pattern="horizontal_push",
        exercise_type="compound",
        difficulty="intermediate",
        equipment=["barbell", "bench"],
        primary_muscles=["chest"],
        prescribed_sets=sets,
        estimated_duration_minutes=10,
        score=95.0,
        reasons=["Primary horizontal compound press for upper body development."],
        is_canonical_cv=True,
    )

    assert exercise.slotRole == ExerciseSlotRole.PRIMARY_COMPOUND
    assert exercise.slotIndex == 1
    assert exercise.exerciseId == "ex_barbell_bench_press"
    assert exercise.totalSets == 3  # Auto-populated from prescribedSets
    assert exercise.isCanonicalCv is True


def test_planned_exercise_rejects_medical_claims():
    """Ensures PlannedExercise reasons strictly reject prohibited medical phrases."""
    prohibited_reasons = [
        "This exercise cures pain in the lumbar region.",
        "Guaranteed to prevent injury during squats.",
        "Effectively treats pain in the rotator cuff.",
        "System diagnoses underlying shoulder instability.",
    ]

    for reason in prohibited_reasons:
        with pytest.raises(ValidationError) as exc_info:
            PlannedExercise(
                slotRole=ExerciseSlotRole.WARMUP_CORRECTIVE,
                slotIndex=0,
                exerciseId="ex_glute_bridge",
                name="Glute Bridge",
                movementPattern="hinge",
                exerciseType="isolation",
                difficulty="beginner",
                equipment=["bodyweight"],
                primaryMuscles=["glutes"],
                reasons=[reason],
            )
        assert "prohibited medical phrase" in str(exc_info.value).lower()


# ============================================================================
# 4. PlannedWorkoutDay & PlannedWeek Aggregations
# ============================================================================

def test_planned_workout_day_metric_aggregation():
    """Validates PlannedWorkoutDay aggregates total sets and duration across planned exercises."""
    ex1 = PlannedExercise(
        slotRole=ExerciseSlotRole.PRIMARY_COMPOUND,
        slotIndex=1,
        exerciseId="ex_barbell_squat",
        name="Barbell Squat",
        movementPattern="squat",
        exerciseType="compound",
        difficulty="intermediate",
        prescribedSets=[
            PlannedSet(setNumber=1, targetReps=5, restSeconds=180),
            PlannedSet(setNumber=2, targetReps=5, restSeconds=180),
            PlannedSet(setNumber=3, targetReps=5, restSeconds=180),
        ],
        estimatedDurationMinutes=12,
    )
    ex2 = PlannedExercise(
        slotRole=ExerciseSlotRole.SECONDARY_COMPOUND,
        slotIndex=2,
        exerciseId="ex_romanian_deadlift",
        name="Romanian Deadlift",
        movementPattern="hinge",
        exerciseType="compound",
        difficulty="intermediate",
        prescribedSets=[
            PlannedSet(setNumber=1, targetReps=8, restSeconds=120),
            PlannedSet(setNumber=2, targetReps=8, restSeconds=120),
        ],
        estimatedDurationMinutes=8,
    )

    day = PlannedWorkoutDay(
        day_number=1,
        day_label="Lower Body A",
        focus="Squat & Hinge Development",
        target_patterns=["squat", "hinge"],
        target_muscles=["quadriceps", "hamstrings"],
        exercises=[ex1, ex2],
    )

    assert day.totalSets == 5  # 3 + 2
    assert day.estimatedDurationMinutes == 20  # 12 + 8
    assert day.isRestDay is False


def test_planned_week_metric_aggregation():
    """Validates PlannedWeek aggregates total sets and workouts across non-rest days."""
    day1 = PlannedWorkoutDay(
        dayNumber=1,
        dayLabel="Upper A",
        focus="Upper Push & Pull",
        exercises=[
            PlannedExercise(
                slotRole=ExerciseSlotRole.PRIMARY_COMPOUND,
                slotIndex=1,
                exerciseId="ex_bench_press",
                name="Bench Press",
                movementPattern="horizontal_push",
                exerciseType="compound",
                difficulty="intermediate",
                totalSets=3,
                estimatedDurationMinutes=10,
            )
        ],
    )
    rest_day = PlannedWorkoutDay(
        dayNumber=2,
        dayLabel="Rest Day",
        isRestDay=True,
        focus="Recovery",
    )
    day3 = PlannedWorkoutDay(
        dayNumber=3,
        dayLabel="Lower A",
        focus="Lower Quad & Hamstring",
        exercises=[
            PlannedExercise(
                slotRole=ExerciseSlotRole.PRIMARY_COMPOUND,
                slotIndex=1,
                exerciseId="ex_squat",
                name="Back Squat",
                movementPattern="squat",
                exerciseType="compound",
                difficulty="intermediate",
                totalSets=4,
                estimatedDurationMinutes=15,
            )
        ],
    )

    week = PlannedWeek(
        week_number=1,
        phase_label="Baseline Accumulation",
        days=[day1, rest_day, day3],
    )

    assert week.totalWeeklySets == 7  # 3 + 0 + 4
    assert week.totalWorkouts == 2  # Rest day ignored


# ============================================================================
# 5. WorkoutPlanGenerateRequest Validation
# ============================================================================

def test_workout_plan_generate_request_defaults():
    """Validates default request attributes and types."""
    req = WorkoutPlanGenerateRequest()
    assert req.targetGoal == "general_fitness"
    assert req.fitnessLevel == "intermediate"
    assert req.environment == "gym"
    assert req.availableEquipment is None
    assert req.trainingDaysPerWeek == 3
    assert req.planDurationWeeks == 4
    assert req.targetWorkoutDurationMinutes == 45
    assert req.excludedExerciseIds == []
    assert req.excludedEquipment == []
    assert req.formAnalysisSupportedOnly is False


def test_workout_plan_generate_request_boundary_enforcement():
    """Ensures training days (1-6), duration weeks (1-12), and workout minutes (20-90) are strictly enforced."""
    # Training days per week boundary (1 to 6)
    with pytest.raises(ValidationError):
        WorkoutPlanGenerateRequest(trainingDaysPerWeek=0)
    with pytest.raises(ValidationError):
        WorkoutPlanGenerateRequest(trainingDaysPerWeek=7)

    # Plan duration weeks boundary (1 to 12)
    with pytest.raises(ValidationError):
        WorkoutPlanGenerateRequest(planDurationWeeks=0)
    with pytest.raises(ValidationError):
        WorkoutPlanGenerateRequest(planDurationWeeks=13)

    # Target workout duration boundary (20 to 90 minutes)
    with pytest.raises(ValidationError):
        WorkoutPlanGenerateRequest(targetWorkoutDurationMinutes=15)
    with pytest.raises(ValidationError):
        WorkoutPlanGenerateRequest(targetWorkoutDurationMinutes=95)


def test_workout_plan_generate_request_camelcase_deserialization():
    """Verifies that camelCase payloads sent by clients deserialize accurately."""
    payload = {
        "targetGoal": "strength",
        "fitnessLevel": "advanced",
        "environment": "home",
        "availableEquipment": ["dumbbells", "pull_up_bar"],
        "trainingDaysPerWeek": 4,
        "planDurationWeeks": 8,
        "targetWorkoutDurationMinutes": 60,
        "excludedExerciseIds": ["ex_deadlift"],
        "excludedEquipment": ["barbell"],
        "preferredMovementPatterns": ["vertical_pull", "squat"],
        "targetMuscles": ["back", "biceps"],
        "correctiveSourceExerciseId": "ex_squat",
        "correctiveIssueId": "knee_valgus",
        "formAnalysisSupportedOnly": True,
        "preferredSplit": "upper_lower",
    }
    req = WorkoutPlanGenerateRequest(**payload)
    assert req.targetGoal == "strength"
    assert req.fitnessLevel == "advanced"
    assert req.environment == "home"
    assert req.availableEquipment == ["dumbbells", "pull_up_bar"]
    assert req.trainingDaysPerWeek == 4
    assert req.planDurationWeeks == 8
    assert req.targetWorkoutDurationMinutes == 60
    assert req.excludedExerciseIds == ["ex_deadlift"]
    assert req.preferredSplit == WorkoutSplitType.UPPER_LOWER


# ============================================================================
# 6. Deterministic Plan ID Generation
# ============================================================================

def test_deterministic_plan_id_identical_for_same_request():
    """Ensures identical requests produce byte-for-byte identical plan IDs."""
    req1 = WorkoutPlanGenerateRequest(
        targetGoal="muscle_gain",
        fitnessLevel="intermediate",
        trainingDaysPerWeek=4,
        planDurationWeeks=8,
    )
    req2 = WorkoutPlanGenerateRequest(
        targetGoal="muscle_gain",
        fitnessLevel="intermediate",
        trainingDaysPerWeek=4,
        planDurationWeeks=8,
    )

    plan_id_1 = generate_deterministic_plan_id(req1)
    plan_id_2 = generate_deterministic_plan_id(req2)

    assert plan_id_1.startswith("plan_")
    assert plan_id_1 == plan_id_2


def test_deterministic_plan_id_order_invariant_for_collections():
    """Ensures collection field ordering does not alter the generated plan ID."""
    req1 = WorkoutPlanGenerateRequest(
        availableEquipment=["barbell", "dumbbells", "bench"],
        excludedExerciseIds=["ex_deadlift", "ex_squat"],
        targetMuscles=["chest", "triceps", "shoulders"],
    )
    req2 = WorkoutPlanGenerateRequest(
        availableEquipment=["bench", "dumbbells", "barbell"],  # reordered
        excludedExerciseIds=["ex_squat", "ex_deadlift"],      # reordered
        targetMuscles=["shoulders", "chest", "triceps"],      # reordered
    )

    assert generate_deterministic_plan_id(req1) == generate_deterministic_plan_id(req2)


def test_deterministic_plan_id_differs_on_parameter_change():
    """Ensures changing any single parameter alters the deterministic hash digest."""
    base_req = WorkoutPlanGenerateRequest(targetGoal="strength", trainingDaysPerWeek=3)
    altered_goal = WorkoutPlanGenerateRequest(targetGoal="fat_loss", trainingDaysPerWeek=3)
    altered_days = WorkoutPlanGenerateRequest(targetGoal="strength", trainingDaysPerWeek=4)

    base_id = generate_deterministic_plan_id(base_req)
    goal_id = generate_deterministic_plan_id(altered_goal)
    days_id = generate_deterministic_plan_id(altered_days)

    assert base_id != goal_id
    assert base_id != days_id
    assert goal_id != days_id


# ============================================================================
# 7. WorkoutPlanResponse Schema Validation
# ============================================================================

def test_workout_plan_response_valid():
    """Verifies complete WorkoutPlanResponse structure and camelCase export."""
    response = WorkoutPlanResponse(
        plan_id="plan_12345678abcdef00",
        title="4-Week Upper/Lower Intermediate Program",
        description="A structured 4-week program focusing on upper and lower body balance.",
        target_goal="hypertrophy" if "hypertrophy" in ["muscle_gain", "strength"] else "muscle_gain",
        fitness_level="intermediate",
        split_type=WorkoutSplitType.UPPER_LOWER,
        training_days_per_week=4,
        total_weeks=4,
        weeks=[],
        applied_filters={"environment": "gym"},
        feasibility_check_passed=True,
        diagnostics=["All 4 days successfully populated."],
        conflicting_filters=[],
    )

    assert response.planId == "plan_12345678abcdef00"
    assert response.feasibilityCheckPassed is True
    assert response.splitType == WorkoutSplitType.UPPER_LOWER

    dumped_camel = response.model_dump()
    assert dumped_camel["planId"] == "plan_12345678abcdef00"
    assert dumped_camel["splitType"] == "upper_lower"
    assert dumped_camel["trainingDaysPerWeek"] == 4
    assert dumped_camel["feasibilityCheckPassed"] is True

    dumped_snake = response.model_dump(by_alias=True)
    assert dumped_snake["plan_id"] == "plan_12345678abcdef00"
    assert dumped_snake["split_type"] == "upper_lower"
    assert dumped_snake["training_days_per_week"] == 4
    assert dumped_snake["feasibility_check_passed"] is True
