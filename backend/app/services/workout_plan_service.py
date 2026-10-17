"""
Deterministic Workout Plan Construction Service (Phase 9B.8.5.2).

Constructs multi-day, multi-week workout plans deterministically from:
- 100-exercise knowledge catalog (Phase 9B.8.2)
- Exercise relationship graph & corrective guidance (Phase 9B.8.3)
- ExerciseRecommendationService (Phase 9B.8.4)
- Domain models and taxonomies (Phase 9B.8.5.1)

Core Architectural Rules:
- Pure deterministic decision layer: Zero Gemini, Zero LLM, Zero ML, Zero Vector DB.
- Read-only execution: Zero Firestore reads, Zero Firestore writes.
- Strict personalization boundary: consumes ONLY explicit parameters in WorkoutPlanGenerateRequest.
- Training split routing:
    - 1 day: Full Body A
    - 2 days: Full Body A, Full Body B
    - 3 days: Full Body A, Full Body B, Full Body C
    - 4 days: Upper A, Lower A, Upper B, Lower B
    - 5 days: Upper, Lower, Push, Pull, Legs
    - 6 days: Push A, Pull A, Legs A, Push B, Pull B, Legs B
- Slot architecture:
    - Slot 0: warmup_corrective (OPTIONAL; only when canonical CV source & valid issue supplied)
    - Slot 1: primary_compound (REQUIRED; compound exercise strictly enforced)
    - Slot 2: secondary_compound (REQUIRED; compound exercise preferred)
    - Slot 3: accessory_1 (REQUIRED; day-appropriate volume)
    - Slot 4: accessory_2 (REQUIRED; unilateral/stabilizer preferred)
    - Slot 5: core_mobility (REQUIRED; existing catalog core/mobility taxonomy)
- Intra-day deduplication: zero duplicate exercise IDs within any single workout day.
- Inter-day primary diversity: avoids repeating same primary compound across consecutive days unless catalog/equipment demands it.
- State handling:
    - State A: Valid plan with all days and slots populated (feasibilityCheckPassed=True).
    - State B: Missing or invalid required input (feasibilityCheckPassed=False, weeks=[]).
    - State C: Conflicting hard constraints (feasibilityCheckPassed=False, weeks=[], conflictingFilters=[...]).
    - State D: Insufficient catalog coverage / slot shortfall (feasibilityCheckPassed=False, weeks=[]).
"""

from dataclasses import dataclass, field
from typing import List, Dict, Any, Optional, Set, Tuple

from backend.app.schemas.exercise import (
    RecommendationIntent,
    ExerciseRecommendationRequest,
    ExerciseRecommendationNode,
    MovementPattern,
    ExerciseType,
    Laterality,
    CANONICAL_CV_EXERCISES,
    is_canonical_cv_exercise,
)
from backend.app.schemas.user import (
    DifficultyLevel,
    EquipmentType,
    MuscleGroup,
    FitnessGoal,
)
from backend.app.schemas.workout_plan import (
    WorkoutSplitType,
    ExerciseSlotRole,
    PlannedSet,
    PlannedExercise,
    PlannedWorkoutDay,
    PlannedWeek,
    WorkoutPlanGenerateRequest,
    WorkoutPlanResponse,
    generate_deterministic_plan_id,
    get_block_phase_label,
)
from backend.app.seeds.catalog import CATALOG_BY_ID
from backend.app.services.exercise_recommendation_service import (
    ExerciseRecommendationService,
    get_exercise_recommendation_service,
)


# ============================================================================
# Day Template & Slot Specifications
# ============================================================================

@dataclass
class SlotSpec:
    """Specification for a single functional slot in a day template."""
    slot_role: ExerciseSlotRole
    slot_index: int
    is_optional: bool = False
    required_exercise_type: Optional[ExerciseType] = None
    preferred_pattern: Optional[MovementPattern] = None
    preferred_muscles: List[MuscleGroup] = field(default_factory=list)
    preferred_laterality: Optional[Laterality] = None


@dataclass
class DayTemplateSpec:
    """Deterministic structural template for a single training day."""
    day_number: int
    day_label: str
    focus: str
    target_patterns: List[MovementPattern]
    target_muscles: List[MuscleGroup]
    slot_specs: List[SlotSpec]


def _build_full_body_templates() -> Dict[int, List[DayTemplateSpec]]:
    """Builds day templates for 1, 2, and 3-day Full Body splits."""
    day_a = DayTemplateSpec(
        day_number=1,
        day_label="Full Body A",
        focus="Squat & Horizontal Push Primary",
        target_patterns=["squat", "horizontal_push", "horizontal_pull", "core_anti_extension"],
        target_muscles=["quadriceps", "chest", "back", "core"],
        slot_specs=[
            SlotSpec(ExerciseSlotRole.WARMUP_CORRECTIVE, 0, is_optional=True),
            SlotSpec(ExerciseSlotRole.PRIMARY_COMPOUND, 1, required_exercise_type="compound", preferred_pattern="squat", preferred_muscles=["quadriceps"]),
            SlotSpec(ExerciseSlotRole.SECONDARY_COMPOUND, 2, required_exercise_type="compound", preferred_pattern="horizontal_push", preferred_muscles=["chest"]),
            SlotSpec(ExerciseSlotRole.ACCESSORY_1, 3, preferred_pattern="horizontal_pull", preferred_muscles=["back"]),
            SlotSpec(ExerciseSlotRole.ACCESSORY_2, 4, preferred_pattern="lunge", preferred_muscles=["quadriceps", "hamstrings"], preferred_laterality="unilateral"),
            SlotSpec(ExerciseSlotRole.CORE_MOBILITY, 5, preferred_pattern="core_anti_extension", preferred_muscles=["core", "abs"]),
        ],
    )

    day_b = DayTemplateSpec(
        day_number=2,
        day_label="Full Body B",
        focus="Hinge & Vertical Push Primary",
        target_patterns=["hinge", "vertical_push", "vertical_pull", "core_anti_rotation"],
        target_muscles=["hamstrings", "glutes", "shoulders", "back", "core"],
        slot_specs=[
            SlotSpec(ExerciseSlotRole.WARMUP_CORRECTIVE, 0, is_optional=True),
            SlotSpec(ExerciseSlotRole.PRIMARY_COMPOUND, 1, required_exercise_type="compound", preferred_pattern="hinge", preferred_muscles=["hamstrings", "glutes"]),
            SlotSpec(ExerciseSlotRole.SECONDARY_COMPOUND, 2, required_exercise_type="compound", preferred_pattern="vertical_push", preferred_muscles=["shoulders"]),
            SlotSpec(ExerciseSlotRole.ACCESSORY_1, 3, preferred_pattern="vertical_pull", preferred_muscles=["back"]),
            SlotSpec(ExerciseSlotRole.ACCESSORY_2, 4, preferred_pattern="isolation", preferred_muscles=["glutes", "biceps"], preferred_laterality="unilateral"),
            SlotSpec(ExerciseSlotRole.CORE_MOBILITY, 5, preferred_pattern="core_anti_rotation", preferred_muscles=["core", "abs"]),
        ],
    )

    day_c = DayTemplateSpec(
        day_number=3,
        day_label="Full Body C",
        focus="Lunge & Push/Pull Secondary",
        target_patterns=["lunge", "horizontal_push", "horizontal_pull", "carry"],
        target_muscles=["quadriceps", "glutes", "chest", "back", "core"],
        slot_specs=[
            SlotSpec(ExerciseSlotRole.WARMUP_CORRECTIVE, 0, is_optional=True),
            SlotSpec(ExerciseSlotRole.PRIMARY_COMPOUND, 1, required_exercise_type="compound", preferred_pattern="lunge", preferred_muscles=["quadriceps", "glutes"]),
            SlotSpec(ExerciseSlotRole.SECONDARY_COMPOUND, 2, required_exercise_type="compound", preferred_pattern="horizontal_push", preferred_muscles=["chest"]),
            SlotSpec(ExerciseSlotRole.ACCESSORY_1, 3, preferred_pattern="horizontal_pull", preferred_muscles=["back"]),
            SlotSpec(ExerciseSlotRole.ACCESSORY_2, 4, preferred_pattern="isolation", preferred_muscles=["calves", "triceps"], preferred_laterality="unilateral"),
            SlotSpec(ExerciseSlotRole.CORE_MOBILITY, 5, preferred_pattern="carry", preferred_muscles=["core"]),
        ],
    )

    return {
        1: [day_a],
        2: [day_a, day_b],
        3: [day_a, day_b, day_c],
    }


def _build_upper_lower_4day_templates() -> List[DayTemplateSpec]:
    """Builds day templates for 4-day Upper/Lower split."""
    upper_a = DayTemplateSpec(
        day_number=1,
        day_label="Upper A",
        focus="Horizontal Push & Pull Primary",
        target_patterns=["horizontal_push", "horizontal_pull", "vertical_push", "isolation"],
        target_muscles=["chest", "back", "shoulders", "triceps", "biceps"],
        slot_specs=[
            SlotSpec(ExerciseSlotRole.WARMUP_CORRECTIVE, 0, is_optional=True),
            SlotSpec(ExerciseSlotRole.PRIMARY_COMPOUND, 1, required_exercise_type="compound", preferred_pattern="horizontal_push", preferred_muscles=["chest"]),
            SlotSpec(ExerciseSlotRole.SECONDARY_COMPOUND, 2, required_exercise_type="compound", preferred_pattern="horizontal_pull", preferred_muscles=["back"]),
            SlotSpec(ExerciseSlotRole.ACCESSORY_1, 3, preferred_pattern="vertical_push", preferred_muscles=["shoulders"]),
            SlotSpec(ExerciseSlotRole.ACCESSORY_2, 4, preferred_pattern="isolation", preferred_muscles=["triceps", "biceps"], preferred_laterality="unilateral"),
            SlotSpec(ExerciseSlotRole.CORE_MOBILITY, 5, preferred_pattern="core_anti_extension", preferred_muscles=["core", "abs"]),
        ],
    )

    lower_a = DayTemplateSpec(
        day_number=2,
        day_label="Lower A",
        focus="Squat Primary & Hinge Secondary",
        target_patterns=["squat", "hinge", "lunge", "core_anti_extension"],
        target_muscles=["quadriceps", "hamstrings", "glutes", "calves", "core"],
        slot_specs=[
            SlotSpec(ExerciseSlotRole.WARMUP_CORRECTIVE, 0, is_optional=True),
            SlotSpec(ExerciseSlotRole.PRIMARY_COMPOUND, 1, required_exercise_type="compound", preferred_pattern="squat", preferred_muscles=["quadriceps"]),
            SlotSpec(ExerciseSlotRole.SECONDARY_COMPOUND, 2, required_exercise_type="compound", preferred_pattern="hinge", preferred_muscles=["hamstrings", "glutes"]),
            SlotSpec(ExerciseSlotRole.ACCESSORY_1, 3, preferred_pattern="lunge", preferred_muscles=["quadriceps"], preferred_laterality="unilateral"),
            SlotSpec(ExerciseSlotRole.ACCESSORY_2, 4, preferred_pattern="isolation", preferred_muscles=["calves", "glutes"]),
            SlotSpec(ExerciseSlotRole.CORE_MOBILITY, 5, preferred_pattern="core_anti_extension", preferred_muscles=["core", "abs"]),
        ],
    )

    upper_b = DayTemplateSpec(
        day_number=3,
        day_label="Upper B",
        focus="Vertical Push & Pull Primary",
        target_patterns=["vertical_push", "vertical_pull", "horizontal_push", "isolation"],
        target_muscles=["shoulders", "back", "chest", "biceps", "triceps"],
        slot_specs=[
            SlotSpec(ExerciseSlotRole.WARMUP_CORRECTIVE, 0, is_optional=True),
            SlotSpec(ExerciseSlotRole.PRIMARY_COMPOUND, 1, required_exercise_type="compound", preferred_pattern="vertical_push", preferred_muscles=["shoulders"]),
            SlotSpec(ExerciseSlotRole.SECONDARY_COMPOUND, 2, required_exercise_type="compound", preferred_pattern="vertical_pull", preferred_muscles=["back"]),
            SlotSpec(ExerciseSlotRole.ACCESSORY_1, 3, preferred_pattern="horizontal_push", preferred_muscles=["chest"]),
            SlotSpec(ExerciseSlotRole.ACCESSORY_2, 4, preferred_pattern="isolation", preferred_muscles=["biceps", "triceps"], preferred_laterality="unilateral"),
            SlotSpec(ExerciseSlotRole.CORE_MOBILITY, 5, preferred_pattern="core_anti_rotation", preferred_muscles=["core", "abs"]),
        ],
    )

    lower_b = DayTemplateSpec(
        day_number=4,
        day_label="Lower B",
        focus="Hinge Primary & Squat Secondary",
        target_patterns=["hinge", "squat", "lunge", "core_anti_rotation"],
        target_muscles=["hamstrings", "glutes", "quadriceps", "calves", "core"],
        slot_specs=[
            SlotSpec(ExerciseSlotRole.WARMUP_CORRECTIVE, 0, is_optional=True),
            SlotSpec(ExerciseSlotRole.PRIMARY_COMPOUND, 1, required_exercise_type="compound", preferred_pattern="hinge", preferred_muscles=["hamstrings", "glutes"]),
            SlotSpec(ExerciseSlotRole.SECONDARY_COMPOUND, 2, required_exercise_type="compound", preferred_pattern="squat", preferred_muscles=["quadriceps"]),
            SlotSpec(ExerciseSlotRole.ACCESSORY_1, 3, preferred_pattern="lunge", preferred_muscles=["glutes", "quadriceps"], preferred_laterality="unilateral"),
            SlotSpec(ExerciseSlotRole.ACCESSORY_2, 4, preferred_pattern="isolation", preferred_muscles=["calves", "hamstrings"]),
            SlotSpec(ExerciseSlotRole.CORE_MOBILITY, 5, preferred_pattern="core_anti_rotation", preferred_muscles=["core", "abs"]),
        ],
    )

    return [upper_a, lower_a, upper_b, lower_b]


def _build_hybrid_5day_templates() -> List[DayTemplateSpec]:
    """Builds day templates for 5-day Upper / Lower / Push / Pull / Legs split."""
    upper = DayTemplateSpec(
        day_number=1,
        day_label="Upper",
        focus="Upper Body Compound & Isolation",
        target_patterns=["horizontal_push", "horizontal_pull", "vertical_push", "vertical_pull"],
        target_muscles=["chest", "back", "shoulders", "biceps", "triceps"],
        slot_specs=[
            SlotSpec(ExerciseSlotRole.WARMUP_CORRECTIVE, 0, is_optional=True),
            SlotSpec(ExerciseSlotRole.PRIMARY_COMPOUND, 1, required_exercise_type="compound", preferred_pattern="horizontal_push", preferred_muscles=["chest"]),
            SlotSpec(ExerciseSlotRole.SECONDARY_COMPOUND, 2, required_exercise_type="compound", preferred_pattern="horizontal_pull", preferred_muscles=["back"]),
            SlotSpec(ExerciseSlotRole.ACCESSORY_1, 3, preferred_pattern="vertical_push", preferred_muscles=["shoulders"]),
            SlotSpec(ExerciseSlotRole.ACCESSORY_2, 4, preferred_pattern="isolation", preferred_muscles=["triceps", "biceps"], preferred_laterality="unilateral"),
            SlotSpec(ExerciseSlotRole.CORE_MOBILITY, 5, preferred_pattern="core_anti_extension", preferred_muscles=["core", "abs"]),
        ],
    )

    lower = DayTemplateSpec(
        day_number=2,
        day_label="Lower",
        focus="Lower Body Quad & Hamstring",
        target_patterns=["squat", "hinge", "lunge", "core_anti_extension"],
        target_muscles=["quadriceps", "hamstrings", "glutes", "calves", "core"],
        slot_specs=[
            SlotSpec(ExerciseSlotRole.WARMUP_CORRECTIVE, 0, is_optional=True),
            SlotSpec(ExerciseSlotRole.PRIMARY_COMPOUND, 1, required_exercise_type="compound", preferred_pattern="squat", preferred_muscles=["quadriceps"]),
            SlotSpec(ExerciseSlotRole.SECONDARY_COMPOUND, 2, required_exercise_type="compound", preferred_pattern="hinge", preferred_muscles=["hamstrings", "glutes"]),
            SlotSpec(ExerciseSlotRole.ACCESSORY_1, 3, preferred_pattern="lunge", preferred_muscles=["quadriceps"], preferred_laterality="unilateral"),
            SlotSpec(ExerciseSlotRole.ACCESSORY_2, 4, preferred_pattern="isolation", preferred_muscles=["calves", "glutes"]),
            SlotSpec(ExerciseSlotRole.CORE_MOBILITY, 5, preferred_pattern="core_anti_extension", preferred_muscles=["core", "abs"]),
        ],
    )

    push = DayTemplateSpec(
        day_number=3,
        day_label="Push",
        focus="Chest, Shoulders & Triceps Pressing",
        target_patterns=["horizontal_push", "vertical_push", "isolation"],
        target_muscles=["chest", "shoulders", "triceps"],
        slot_specs=[
            SlotSpec(ExerciseSlotRole.WARMUP_CORRECTIVE, 0, is_optional=True),
            SlotSpec(ExerciseSlotRole.PRIMARY_COMPOUND, 1, required_exercise_type="compound", preferred_pattern="horizontal_push", preferred_muscles=["chest"]),
            SlotSpec(ExerciseSlotRole.SECONDARY_COMPOUND, 2, required_exercise_type="compound", preferred_pattern="vertical_push", preferred_muscles=["shoulders"]),
            SlotSpec(ExerciseSlotRole.ACCESSORY_1, 3, preferred_pattern="horizontal_push", preferred_muscles=["chest"]),
            SlotSpec(ExerciseSlotRole.ACCESSORY_2, 4, preferred_pattern="isolation", preferred_muscles=["triceps"], preferred_laterality="unilateral"),
            SlotSpec(ExerciseSlotRole.CORE_MOBILITY, 5, preferred_pattern="core_anti_extension", preferred_muscles=["core", "abs"]),
        ],
    )

    pull = DayTemplateSpec(
        day_number=4,
        day_label="Pull",
        focus="Back, Rear Delts & Biceps Pulling",
        target_patterns=["horizontal_pull", "vertical_pull", "isolation"],
        target_muscles=["back", "biceps"],
        slot_specs=[
            SlotSpec(ExerciseSlotRole.WARMUP_CORRECTIVE, 0, is_optional=True),
            SlotSpec(ExerciseSlotRole.PRIMARY_COMPOUND, 1, required_exercise_type="compound", preferred_pattern="horizontal_pull", preferred_muscles=["back"]),
            SlotSpec(ExerciseSlotRole.SECONDARY_COMPOUND, 2, required_exercise_type="compound", preferred_pattern="vertical_pull", preferred_muscles=["back"]),
            SlotSpec(ExerciseSlotRole.ACCESSORY_1, 3, preferred_pattern="horizontal_pull", preferred_muscles=["back"]),
            SlotSpec(ExerciseSlotRole.ACCESSORY_2, 4, preferred_pattern="isolation", preferred_muscles=["biceps"], preferred_laterality="unilateral"),
            SlotSpec(ExerciseSlotRole.CORE_MOBILITY, 5, preferred_pattern="core_anti_rotation", preferred_muscles=["core", "abs"]),
        ],
    )

    legs = DayTemplateSpec(
        day_number=5,
        day_label="Legs",
        focus="Squat, Hinge & Calves",
        target_patterns=["squat", "hinge", "lunge", "core_anti_rotation"],
        target_muscles=["quadriceps", "hamstrings", "glutes", "calves", "core"],
        slot_specs=[
            SlotSpec(ExerciseSlotRole.WARMUP_CORRECTIVE, 0, is_optional=True),
            SlotSpec(ExerciseSlotRole.PRIMARY_COMPOUND, 1, required_exercise_type="compound", preferred_pattern="squat", preferred_muscles=["quadriceps"]),
            SlotSpec(ExerciseSlotRole.SECONDARY_COMPOUND, 2, required_exercise_type="compound", preferred_pattern="hinge", preferred_muscles=["hamstrings", "glutes"]),
            SlotSpec(ExerciseSlotRole.ACCESSORY_1, 3, preferred_pattern="lunge", preferred_muscles=["quadriceps"], preferred_laterality="unilateral"),
            SlotSpec(ExerciseSlotRole.ACCESSORY_2, 4, preferred_pattern="isolation", preferred_muscles=["calves"]),
            SlotSpec(ExerciseSlotRole.CORE_MOBILITY, 5, preferred_pattern="core_anti_rotation", preferred_muscles=["core", "abs"]),
        ],
    )

    return [upper, lower, push, pull, legs]


def _build_ppl_6day_templates() -> List[DayTemplateSpec]:
    """Builds day templates for 6-day Push / Pull / Legs split."""
    push_a = DayTemplateSpec(
        day_number=1,
        day_label="Push A",
        focus="Horizontal & Vertical Pressing",
        target_patterns=["horizontal_push", "vertical_push", "isolation"],
        target_muscles=["chest", "shoulders", "triceps"],
        slot_specs=[
            SlotSpec(ExerciseSlotRole.WARMUP_CORRECTIVE, 0, is_optional=True),
            SlotSpec(ExerciseSlotRole.PRIMARY_COMPOUND, 1, required_exercise_type="compound", preferred_pattern="horizontal_push", preferred_muscles=["chest"]),
            SlotSpec(ExerciseSlotRole.SECONDARY_COMPOUND, 2, required_exercise_type="compound", preferred_pattern="vertical_push", preferred_muscles=["shoulders"]),
            SlotSpec(ExerciseSlotRole.ACCESSORY_1, 3, preferred_pattern="horizontal_push", preferred_muscles=["chest"]),
            SlotSpec(ExerciseSlotRole.ACCESSORY_2, 4, preferred_pattern="isolation", preferred_muscles=["triceps"], preferred_laterality="unilateral"),
            SlotSpec(ExerciseSlotRole.CORE_MOBILITY, 5, preferred_pattern="core_anti_extension", preferred_muscles=["core", "abs"]),
        ],
    )

    pull_a = DayTemplateSpec(
        day_number=2,
        day_label="Pull A",
        focus="Horizontal & Vertical Pulling",
        target_patterns=["horizontal_pull", "vertical_pull", "isolation"],
        target_muscles=["back", "biceps"],
        slot_specs=[
            SlotSpec(ExerciseSlotRole.WARMUP_CORRECTIVE, 0, is_optional=True),
            SlotSpec(ExerciseSlotRole.PRIMARY_COMPOUND, 1, required_exercise_type="compound", preferred_pattern="horizontal_pull", preferred_muscles=["back"]),
            SlotSpec(ExerciseSlotRole.SECONDARY_COMPOUND, 2, required_exercise_type="compound", preferred_pattern="vertical_pull", preferred_muscles=["back"]),
            SlotSpec(ExerciseSlotRole.ACCESSORY_1, 3, preferred_pattern="horizontal_pull", preferred_muscles=["back"]),
            SlotSpec(ExerciseSlotRole.ACCESSORY_2, 4, preferred_pattern="isolation", preferred_muscles=["biceps"], preferred_laterality="unilateral"),
            SlotSpec(ExerciseSlotRole.CORE_MOBILITY, 5, preferred_pattern="core_anti_rotation", preferred_muscles=["core", "abs"]),
        ],
    )

    legs_a = DayTemplateSpec(
        day_number=3,
        day_label="Legs A",
        focus="Squat, Hinge & Unilateral Leg Work",
        target_patterns=["squat", "hinge", "lunge", "core_anti_extension"],
        target_muscles=["quadriceps", "hamstrings", "glutes", "calves", "core"],
        slot_specs=[
            SlotSpec(ExerciseSlotRole.WARMUP_CORRECTIVE, 0, is_optional=True),
            SlotSpec(ExerciseSlotRole.PRIMARY_COMPOUND, 1, required_exercise_type="compound", preferred_pattern="squat", preferred_muscles=["quadriceps"]),
            SlotSpec(ExerciseSlotRole.SECONDARY_COMPOUND, 2, required_exercise_type="compound", preferred_pattern="hinge", preferred_muscles=["hamstrings", "glutes"]),
            SlotSpec(ExerciseSlotRole.ACCESSORY_1, 3, preferred_pattern="lunge", preferred_muscles=["quadriceps"], preferred_laterality="unilateral"),
            SlotSpec(ExerciseSlotRole.ACCESSORY_2, 4, preferred_pattern="isolation", preferred_muscles=["calves", "glutes"]),
            SlotSpec(ExerciseSlotRole.CORE_MOBILITY, 5, preferred_pattern="core_anti_extension", preferred_muscles=["core", "abs"]),
        ],
    )

    push_b = DayTemplateSpec(
        day_number=4,
        day_label="Push B",
        focus="Vertical & Horizontal Pressing",
        target_patterns=["vertical_push", "horizontal_push", "isolation"],
        target_muscles=["shoulders", "chest", "triceps"],
        slot_specs=[
            SlotSpec(ExerciseSlotRole.WARMUP_CORRECTIVE, 0, is_optional=True),
            SlotSpec(ExerciseSlotRole.PRIMARY_COMPOUND, 1, required_exercise_type="compound", preferred_pattern="vertical_push", preferred_muscles=["shoulders"]),
            SlotSpec(ExerciseSlotRole.SECONDARY_COMPOUND, 2, required_exercise_type="compound", preferred_pattern="horizontal_push", preferred_muscles=["chest"]),
            SlotSpec(ExerciseSlotRole.ACCESSORY_1, 3, preferred_pattern="horizontal_push", preferred_muscles=["chest"]),
            SlotSpec(ExerciseSlotRole.ACCESSORY_2, 4, preferred_pattern="isolation", preferred_muscles=["triceps"], preferred_laterality="unilateral"),
            SlotSpec(ExerciseSlotRole.CORE_MOBILITY, 5, preferred_pattern="core_anti_rotation", preferred_muscles=["core", "abs"]),
        ],
    )

    pull_b = DayTemplateSpec(
        day_number=5,
        day_label="Pull B",
        focus="Vertical & Horizontal Pulling",
        target_patterns=["vertical_pull", "horizontal_pull", "isolation"],
        target_muscles=["back", "biceps"],
        slot_specs=[
            SlotSpec(ExerciseSlotRole.WARMUP_CORRECTIVE, 0, is_optional=True),
            SlotSpec(ExerciseSlotRole.PRIMARY_COMPOUND, 1, required_exercise_type="compound", preferred_pattern="vertical_pull", preferred_muscles=["back"]),
            SlotSpec(ExerciseSlotRole.SECONDARY_COMPOUND, 2, required_exercise_type="compound", preferred_pattern="horizontal_pull", preferred_muscles=["back"]),
            SlotSpec(ExerciseSlotRole.ACCESSORY_1, 3, preferred_pattern="vertical_pull", preferred_muscles=["back"]),
            SlotSpec(ExerciseSlotRole.ACCESSORY_2, 4, preferred_pattern="isolation", preferred_muscles=["biceps"], preferred_laterality="unilateral"),
            SlotSpec(ExerciseSlotRole.CORE_MOBILITY, 5, preferred_pattern="core_anti_rotation", preferred_muscles=["core", "abs"]),
        ],
    )

    legs_b = DayTemplateSpec(
        day_number=6,
        day_label="Legs B",
        focus="Hinge & Squat Leg Development",
        target_patterns=["hinge", "squat", "lunge", "core_anti_rotation"],
        target_muscles=["hamstrings", "glutes", "quadriceps", "calves", "core"],
        slot_specs=[
            SlotSpec(ExerciseSlotRole.WARMUP_CORRECTIVE, 0, is_optional=True),
            SlotSpec(ExerciseSlotRole.PRIMARY_COMPOUND, 1, required_exercise_type="compound", preferred_pattern="hinge", preferred_muscles=["hamstrings", "glutes"]),
            SlotSpec(ExerciseSlotRole.SECONDARY_COMPOUND, 2, required_exercise_type="compound", preferred_pattern="squat", preferred_muscles=["quadriceps"]),
            SlotSpec(ExerciseSlotRole.ACCESSORY_1, 3, preferred_pattern="lunge", preferred_muscles=["glutes", "quadriceps"], preferred_laterality="unilateral"),
            SlotSpec(ExerciseSlotRole.ACCESSORY_2, 4, preferred_pattern="isolation", preferred_muscles=["calves", "hamstrings"]),
            SlotSpec(ExerciseSlotRole.CORE_MOBILITY, 5, preferred_pattern="core_anti_rotation", preferred_muscles=["core", "abs"]),
        ],
    )

    return [push_a, pull_a, legs_a, push_b, pull_b, legs_b]


# ============================================================================
# WorkoutPlanService Engine
# ============================================================================

class WorkoutPlanService:
    """
    Deterministic Workout Plan Generation Service.
    Allocates structured multi-day templates, selects candidates via
    ExerciseRecommendationService, enforces compound and deduplication rules,
    and returns State A, B, C, or D.
    """

    def __init__(
        self,
        recommendation_service: Optional[ExerciseRecommendationService] = None,
        catalog_by_id: Optional[Dict[str, Any]] = None,
    ):
        self._recommendation_service = (
            recommendation_service
            if recommendation_service is not None
            else get_exercise_recommendation_service()
        )
        self._catalog_by_id = (
            catalog_by_id if catalog_by_id is not None else CATALOG_BY_ID
        )
        self._full_body_templates = _build_full_body_templates()
        self._upper_lower_templates = _build_upper_lower_4day_templates()
        self._hybrid_5day_templates = _build_hybrid_5day_templates()
        self._ppl_6day_templates = _build_ppl_6day_templates()

    # =========================================================================
    # PUBLIC PLAN GENERATION PIPELINE
    # =========================================================================

    def generate_plan(self, request: WorkoutPlanGenerateRequest) -> WorkoutPlanResponse:
        """
        Main entry point for deterministic workout plan generation.
        Validates inputs (State B), detects conflicting filters (State C),
        allocates day slots (State D on shortfall), and produces a structured plan (State A).
        """
        # 1. Validate Input Boundaries & Required Fields (STATE B)
        state_b_response = self._validate_input_state_b(request)
        if state_b_response:
            return state_b_response

        # 2. Determine Split Type & Verify Split Compatibility (STATE C)
        split_type, split_conflict = self._determine_and_validate_split(request)
        if split_conflict:
            return WorkoutPlanResponse(
                plan_id=generate_deterministic_plan_id(request),
                title="Infeasible Plan Request",
                description="Plan construction halted due to incompatible split preferences.",
                target_goal=request.targetGoal,
                fitness_level=request.fitnessLevel,
                split_type=split_type,
                training_days_per_week=request.trainingDaysPerWeek,
                total_weeks=0,
                weeks=[],
                applied_filters=self._summarize_applied_filters(request),
                feasibility_check_passed=False,
                diagnostics=[split_conflict],
                conflicting_filters=[
                    f"preferred_split: {request.preferredSplit.value if request.preferredSplit else 'none'}",
                    f"training_days_per_week: {request.trainingDaysPerWeek}",
                ],
            )

        # 3. Check Overall Catalog Feasibility (STATE C)
        catalog_conflict = self._check_catalog_feasibility(request)
        if catalog_conflict:
            return WorkoutPlanResponse(
                plan_id=generate_deterministic_plan_id(request),
                title="Infeasible Plan Request",
                description="Zero catalog exercises satisfy the active equipment/environment hard gates.",
                target_goal=request.targetGoal,
                fitness_level=request.fitnessLevel,
                split_type=split_type,
                training_days_per_week=request.trainingDaysPerWeek,
                total_weeks=0,
                weeks=[],
                applied_filters=self._summarize_applied_filters(request),
                feasibility_check_passed=False,
                diagnostics=[catalog_conflict],
                conflicting_filters=[
                    f"environment: {request.environment}",
                    f"available_equipment: {request.availableEquipment}",
                    f"excluded_equipment: {request.excludedEquipment}",
                ],
            )

        # 4. Retrieve Deterministic Day Templates
        day_templates = self._get_day_templates(request.trainingDaysPerWeek)

        # 5. Allocate Slots for Each Day Template (STATE D on Shortfall)
        planned_days: List[PlannedWorkoutDay] = []
        diagnostics: List[str] = []
        previous_primary_id: Optional[str] = None

        for day_spec in day_templates:
            planned_day, shortfall_msg, day_diagnostics = self._allocate_day_slots(
                day_spec=day_spec,
                request=request,
                previous_primary_id=previous_primary_id,
            )

            if shortfall_msg:
                # STATE D: Insufficient catalog coverage / slot failure
                return WorkoutPlanResponse(
                    plan_id=generate_deterministic_plan_id(request),
                    title="Catalog Shortfall",
                    description="Plan construction halted due to insufficient catalog coverage for required slots.",
                    target_goal=request.targetGoal,
                    fitness_level=request.fitnessLevel,
                    split_type=split_type,
                    training_days_per_week=request.trainingDaysPerWeek,
                    total_weeks=0,
                    weeks=[],
                    applied_filters=self._summarize_applied_filters(request),
                    feasibility_check_passed=False,
                    diagnostics=[shortfall_msg],
                    conflicting_filters=[],
                )

            diagnostics.extend(day_diagnostics)
            planned_days.append(planned_day)

            # Track primary compound for inter-day diversity preference
            primary_ex = next(
                (ex for ex in planned_day.exercises if ex.slotRole == ExerciseSlotRole.PRIMARY_COMPOUND),
                None,
            )
            if primary_ex:
                previous_primary_id = primary_ex.exerciseId

        # 6. Validate Whole-Plan Feasibility
        feasibility_error = self._verify_whole_plan_feasibility(planned_days)
        if feasibility_error:
            return WorkoutPlanResponse(
                plan_id=generate_deterministic_plan_id(request),
                title="Plan Validation Failure",
                description="Plan feasibility check failed.",
                target_goal=request.targetGoal,
                fitness_level=request.fitnessLevel,
                split_type=split_type,
                training_days_per_week=request.trainingDaysPerWeek,
                total_weeks=0,
                weeks=[],
                applied_filters=self._summarize_applied_filters(request),
                feasibility_check_passed=False,
                diagnostics=[feasibility_error],
                conflicting_filters=[],
            )

        # 7. Construct Structural Weeks (1 to 12 Weeks)
        planned_weeks: List[PlannedWeek] = []
        for week_idx in range(1, request.planDurationWeeks + 1):
            phase_label = get_block_phase_label(week_idx)
            week_obj = PlannedWeek(
                week_number=week_idx,
                phase_label=phase_label,
                days=planned_days,
            )
            planned_weeks.append(week_obj)

        # 8. STATE A: Valid Plan Construction Complete
        plan_id = generate_deterministic_plan_id(request)
        split_display = split_type.value.replace("_", " ").title()
        title = f"{request.planDurationWeeks}-Week {split_display} Program"
        description = (
            f"Deterministic {request.trainingDaysPerWeek}-day {split_display.lower()} plan "
            f"tailored for {request.targetGoal.replace('_', ' ')} ({request.fitnessLevel} level)."
        )

        return WorkoutPlanResponse(
            plan_id=plan_id,
            title=title,
            description=description,
            target_goal=request.targetGoal,
            fitness_level=request.fitnessLevel,
            split_type=split_type,
            training_days_per_week=request.trainingDaysPerWeek,
            total_weeks=request.planDurationWeeks,
            weeks=planned_weeks,
            applied_filters=self._summarize_applied_filters(request),
            feasibility_check_passed=True,
            diagnostics=diagnostics if diagnostics else ["Plan generation completed successfully with zero shortfalls."],
            conflicting_filters=[],
        )

    # =========================================================================
    # INPUT VALIDATION (STATE B)
    # =========================================================================

    def _validate_input_state_b(
        self, request: WorkoutPlanGenerateRequest
    ) -> Optional[WorkoutPlanResponse]:
        """Validates bounds and required corrective parameters."""
        diagnostics: List[str] = []

        # 1. Training days bounds (1 to 6)
        if not (1 <= request.trainingDaysPerWeek <= 6):
            diagnostics.append(
                f"training_days_per_week must be between 1 and 6; received {request.trainingDaysPerWeek}."
            )

        # 2. Plan duration bounds (1 to 12)
        if not (1 <= request.planDurationWeeks <= 12):
            diagnostics.append(
                f"plan_duration_weeks must be between 1 and 12; received {request.planDurationWeeks}."
            )

        # 3. Target workout duration bounds (20 to 90)
        if not (20 <= request.targetWorkoutDurationMinutes <= 90):
            diagnostics.append(
                f"target_workout_duration_minutes must be between 20 and 90; received {request.targetWorkoutDurationMinutes}."
            )

        # 4. Corrective parameter validation
        has_source = bool(request.correctiveSourceExerciseId and request.correctiveSourceExerciseId.strip())
        has_issue = bool(request.correctiveIssueId and request.correctiveIssueId.strip())

        if has_source and not has_issue:
            diagnostics.append(
                "Corrective intent requires both 'corrective_source_exercise_id' and 'corrective_issue_id'. 'corrective_issue_id' is missing."
            )
        elif has_issue and not has_source:
            diagnostics.append(
                "Corrective intent requires both 'corrective_source_exercise_id' and 'corrective_issue_id'. 'corrective_source_exercise_id' is missing."
            )
        elif has_source and has_issue:
            source_id = request.correctiveSourceExerciseId.strip()
            if not is_canonical_cv_exercise(source_id):
                diagnostics.append(
                    f"Corrective recommendations require a canonical CV source exercise. '{source_id}' is not in canonical CV set: {sorted(list(CANONICAL_CV_EXERCISES.keys()))}."
                )

        if diagnostics:
            # Fallback split for response structure
            split_type = WorkoutSplitType.FULL_BODY
            if 1 <= request.trainingDaysPerWeek <= 3:
                split_type = WorkoutSplitType.FULL_BODY
            elif request.trainingDaysPerWeek in (4, 5):
                split_type = WorkoutSplitType.UPPER_LOWER
            elif request.trainingDaysPerWeek == 6:
                split_type = WorkoutSplitType.PUSH_PULL_LEGS

            return WorkoutPlanResponse(
                plan_id=generate_deterministic_plan_id(request),
                title="Invalid Plan Request",
                description="Plan construction halted due to missing or invalid input parameters.",
                target_goal=request.targetGoal,
                fitness_level=request.fitnessLevel,
                split_type=split_type,
                training_days_per_week=request.trainingDaysPerWeek,
                total_weeks=0,
                weeks=[],
                applied_filters=self._summarize_applied_filters(request),
                feasibility_check_passed=False,
                diagnostics=diagnostics,
                conflictingFilters=[],
            )

        return None

    # =========================================================================
    # SPLIT DETERMINATION & FEASIBILITY (STATE C)
    # =========================================================================

    def _determine_and_validate_split(
        self, request: WorkoutPlanGenerateRequest
    ) -> Tuple[WorkoutSplitType, Optional[str]]:
        """Maps training days to split and validates preferredSplit compatibility."""
        days = request.trainingDaysPerWeek

        if 1 <= days <= 3:
            routed_split = WorkoutSplitType.FULL_BODY
        elif days in (4, 5):
            routed_split = WorkoutSplitType.UPPER_LOWER
        else:
            routed_split = WorkoutSplitType.PUSH_PULL_LEGS

        if request.preferredSplit is not None:
            pref = request.preferredSplit
            # Compatibility matrix
            if days in (1, 2, 3) and pref != WorkoutSplitType.FULL_BODY:
                return routed_split, f"preferred_split '{pref.value}' is incompatible with {days} training day(s). 1–3 days requires 'full_body'."
            if days == 4 and pref != WorkoutSplitType.UPPER_LOWER:
                return routed_split, f"preferred_split '{pref.value}' is incompatible with 4 training days. 4 days requires 'upper_lower'."
            if days == 5 and pref not in (WorkoutSplitType.UPPER_LOWER, WorkoutSplitType.PUSH_PULL_LEGS):
                return routed_split, f"preferred_split '{pref.value}' is incompatible with 5 training days. 5 days requires 'upper_lower' or 'push_pull_legs'."
            if days == 6 and pref != WorkoutSplitType.PUSH_PULL_LEGS:
                return routed_split, f"preferred_split '{pref.value}' is incompatible with 6 training days. 6 days requires 'push_pull_legs'."
            return pref, None

        return routed_split, None

    def _check_catalog_feasibility(
        self, request: WorkoutPlanGenerateRequest
    ) -> Optional[str]:
        """Probes the recommendation service to detect mutually conflicting hard gates."""
        test_rec_req = ExerciseRecommendationRequest(
            intent=RecommendationIntent.GENERAL,
            targetGoal=request.targetGoal,
            fitnessLevel=request.fitnessLevel,
            environment=request.environment,
            availableEquipment=request.availableEquipment,
            excludedEquipment=request.excludedEquipment,
            excludedExerciseIds=request.excludedExerciseIds,
            formAnalysisSupportedOnly=request.formAnalysisSupportedOnly,
            limit=10,
        )
        test_res = self._recommendation_service.recommend(test_rec_req)

        if test_res.totalEligible == 0 and test_res.conflictingFilters:
            return f"Mutually conflicting hard constraints: {'; '.join(test_res.conflictingFilters)}"

        return None

    # =========================================================================
    # TEMPLATE SELECTION
    # =========================================================================

    def _get_day_templates(self, training_days: int) -> List[DayTemplateSpec]:
        """Returns the deterministic DayTemplateSpecs for the requested training days."""
        if training_days in (1, 2, 3):
            return self._full_body_templates[training_days]
        elif training_days == 4:
            return self._upper_lower_templates
        elif training_days == 5:
            return self._hybrid_5day_templates
        else:  # 6 days
            return self._ppl_6day_templates

    # =========================================================================
    # DAY-LEVEL SLOT ALLOCATION (STATE D ON SHORTFALL)
    # =========================================================================

    def _allocate_day_slots(
        self,
        day_spec: DayTemplateSpec,
        request: WorkoutPlanGenerateRequest,
        previous_primary_id: Optional[str] = None,
    ) -> Tuple[Optional[PlannedWorkoutDay], Optional[str], List[str]]:
        """
        Allocates all functional slots for a single day template.
        Enforces:
        - Slot 1 compound requirement
        - Slot 2 secondary compound requirement
        - Intra-day deduplication
        - Inter-day primary diversity
        Returns (planned_day, shortfall_diagnostic, informational_diagnostics).
        """
        allocated_exercises: List[PlannedExercise] = []
        current_excluded_ids: Set[str] = set(request.excludedExerciseIds)
        day_diagnostics: List[str] = []

        for slot_spec in day_spec.slot_specs:
            # Handle Optional Slot 0 (Warmup / Corrective)
            if slot_spec.slot_role == ExerciseSlotRole.WARMUP_CORRECTIVE:
                if request.correctiveSourceExerciseId and request.correctiveIssueId:
                    corrective_ex, corr_diag = self._allocate_corrective_slot_0(
                        request=request,
                        current_excluded_ids=current_excluded_ids,
                    )
                    if corrective_ex:
                        allocated_exercises.append(corrective_ex)
                        current_excluded_ids.add(corrective_ex.exerciseId)
                    elif corr_diag:
                        day_diagnostics.append(corr_diag)
                # Slot 0 is optional, so no failure if omitted
                continue

            # Handle Required Slots 1–5
            planned_ex, shortfall = self._allocate_required_slot(
                slot_spec=slot_spec,
                day_spec=day_spec,
                request=request,
                current_excluded_ids=current_excluded_ids,
                previous_primary_id=previous_primary_id if slot_spec.slot_role == ExerciseSlotRole.PRIMARY_COMPOUND else None,
            )

            if shortfall:
                # STATE D shortfall encountered
                return None, shortfall, day_diagnostics

            allocated_exercises.append(planned_ex)
            current_excluded_ids.add(planned_ex.exerciseId)

        planned_day = PlannedWorkoutDay(
            day_number=day_spec.day_number,
            day_label=day_spec.day_label,
            is_rest_day=False,
            focus=day_spec.focus,
            target_patterns=day_spec.target_patterns,
            target_muscles=day_spec.target_muscles,
            exercises=allocated_exercises,
        )
        return planned_day, None, day_diagnostics

    # =========================================================================
    # SLOT 0: CORRECTIVE ALLOCATION
    # =========================================================================

    def _allocate_corrective_slot_0(
        self,
        request: WorkoutPlanGenerateRequest,
        current_excluded_ids: Set[str],
    ) -> Tuple[Optional[PlannedExercise], Optional[str]]:
        """Allocates Slot 0 strictly from Phase 9B.8.3 corrective mappings."""
        source_id = request.correctiveSourceExerciseId.strip()
        issue_id = request.correctiveIssueId.strip()

        rec_req = ExerciseRecommendationRequest(
            intent=RecommendationIntent.CORRECTIVE,
            sourceExerciseId=source_id,
            correctiveIssueId=issue_id,
            targetGoal=request.targetGoal,
            fitnessLevel=request.fitnessLevel,
            environment=request.environment,
            availableEquipment=request.availableEquipment,
            excludedEquipment=request.excludedEquipment,
            excludedExerciseIds=list(current_excluded_ids),
            formAnalysisSupportedOnly=request.formAnalysisSupportedOnly,
            limit=5,
        )
        rec_res = self._recommendation_service.recommend(rec_req)

        if rec_res.candidates:
            cand = rec_res.candidates[0]
            sets = self._build_structural_sets(ExerciseSlotRole.WARMUP_CORRECTIVE, request.targetGoal)
            estimated_duration = sum(max(1, int((s.restSeconds + 45) / 60)) for s in sets)
            planned = PlannedExercise(
                slot_role=ExerciseSlotRole.WARMUP_CORRECTIVE,
                slot_index=0,
                exercise_id=cand.exerciseId,
                name=cand.name,
                movement_pattern=cand.movementPattern,
                exercise_type=cand.exerciseType,
                difficulty=cand.difficulty,
                equipment=list(cand.equipment),
                primary_muscles=list(cand.primaryMuscles),
                prescribed_sets=sets,
                estimated_duration_minutes=estimated_duration,
                score=cand.score,
                reasons=cand.reasons,
                is_canonical_cv=cand.isCanonicalCv,
            )
            return planned, None

        diag = (
            f"Corrective exercise for '{source_id}' / '{issue_id}' could not be allocated "
            f"due to active equipment/environment hard constraints."
        )
        return None, diag

    # =========================================================================
    # REQUIRED SLOT ALLOCATION (SLOTS 1 TO 5)
    # =========================================================================

    def _allocate_required_slot(
        self,
        slot_spec: SlotSpec,
        day_spec: DayTemplateSpec,
        request: WorkoutPlanGenerateRequest,
        current_excluded_ids: Set[str],
        previous_primary_id: Optional[str] = None,
    ) -> Tuple[Optional[PlannedExercise], Optional[str]]:
        """
        Selects a candidate for a required slot using ExerciseRecommendationService.
        Enforces compound rules for Slots 1 & 2. Never fabricates exercises.
        """
        role = slot_spec.slot_role

        # Handle Slot 1 (Primary Compound) with Inter-Day Diversity Preference
        if role == ExerciseSlotRole.PRIMARY_COMPOUND:
            return self._allocate_primary_compound_slot(
                slot_spec=slot_spec,
                day_spec=day_spec,
                request=request,
                current_excluded_ids=current_excluded_ids,
                previous_primary_id=previous_primary_id,
            )

        # Handle Slot 2 (Secondary Compound)
        if role == ExerciseSlotRole.SECONDARY_COMPOUND:
            return self._allocate_secondary_compound_slot(
                slot_spec=slot_spec,
                day_spec=day_spec,
                request=request,
                current_excluded_ids=current_excluded_ids,
            )

        # Handle Slot 3 (Accessory 1)
        if role == ExerciseSlotRole.ACCESSORY_1:
            return self._allocate_accessory_slot(
                slot_spec=slot_spec,
                day_spec=day_spec,
                request=request,
                current_excluded_ids=current_excluded_ids,
                prefer_unilateral=False,
            )

        # Handle Slot 4 (Accessory 2 with Unilateral Preference)
        if role == ExerciseSlotRole.ACCESSORY_2:
            return self._allocate_accessory_slot(
                slot_spec=slot_spec,
                day_spec=day_spec,
                request=request,
                current_excluded_ids=current_excluded_ids,
                prefer_unilateral=True,
            )

        # Handle Slot 5 (Core / Mobility)
        return self._allocate_core_mobility_slot(
            slot_spec=slot_spec,
            day_spec=day_spec,
            request=request,
            current_excluded_ids=current_excluded_ids,
        )

    # -------------------------------------------------------------------------
    # Slot 1: Primary Compound
    # -------------------------------------------------------------------------
    def _allocate_primary_compound_slot(
        self,
        slot_spec: SlotSpec,
        day_spec: DayTemplateSpec,
        request: WorkoutPlanGenerateRequest,
        current_excluded_ids: Set[str],
        previous_primary_id: Optional[str] = None,
    ) -> Tuple[Optional[PlannedExercise], Optional[str]]:
        """
        Selects a compound exercise for Slot 1.
        Prefers inter-day primary diversity when alternatives exist.
        """
        pattern = slot_spec.preferred_pattern
        muscles = slot_spec.preferred_muscles

        # Step A: Query with previous primary excluded (diversity preference)
        search_exclusions = set(current_excluded_ids)
        if previous_primary_id:
            search_exclusions.add(previous_primary_id)

        candidate = self._query_best_compound(
            pattern=pattern,
            muscles=muscles,
            excluded_ids=search_exclusions,
            request=request,
        )

        # Step B: If no candidate found under diversity exclusion, retry allowing reuse
        if not candidate and previous_primary_id and previous_primary_id not in current_excluded_ids:
            candidate = self._query_best_compound(
                pattern=pattern,
                muscles=muscles,
                excluded_ids=current_excluded_ids,
                request=request,
            )

        # Step C: If still no candidate for preferred pattern, probe day's alternative patterns for compound
        if not candidate:
            for alt_pattern in day_spec.target_patterns:
                if alt_pattern != pattern:
                    candidate = self._query_best_compound(
                        pattern=alt_pattern,
                        muscles=day_spec.target_muscles,
                        excluded_ids=current_excluded_ids,
                        request=request,
                    )
                    if candidate:
                        break

        if not candidate:
            # STATE D Shortfall
            shortfall = (
                f"Catalog feasibility shortfall on Day {day_spec.day_number} ({day_spec.day_label}), "
                f"Slot 1 (primary_compound): Zero eligible compound exercises found in catalog matching "
                f"environment '{request.environment}', available equipment {request.availableEquipment}, "
                f"and active exclusions."
            )
            return None, shortfall

        planned = self._create_planned_exercise(
            slot_role=ExerciseSlotRole.PRIMARY_COMPOUND,
            slot_index=1,
            candidate=candidate,
            goal=request.targetGoal,
        )
        return planned, None

    # -------------------------------------------------------------------------
    # Slot 2: Secondary Compound
    # -------------------------------------------------------------------------
    def _allocate_secondary_compound_slot(
        self,
        slot_spec: SlotSpec,
        day_spec: DayTemplateSpec,
        request: WorkoutPlanGenerateRequest,
        current_excluded_ids: Set[str],
    ) -> Tuple[Optional[PlannedExercise], Optional[str]]:
        """Selects a compound exercise for Slot 2 complementary to Slot 1."""
        pattern = slot_spec.preferred_pattern
        muscles = slot_spec.preferred_muscles

        candidate = self._query_best_compound(
            pattern=pattern,
            muscles=muscles,
            excluded_ids=current_excluded_ids,
            request=request,
        )

        # Probe alternative day patterns if preferred secondary pattern yields no compound
        if not candidate:
            for alt_pattern in day_spec.target_patterns:
                if alt_pattern != pattern:
                    candidate = self._query_best_compound(
                        pattern=alt_pattern,
                        muscles=day_spec.target_muscles,
                        excluded_ids=current_excluded_ids,
                        request=request,
                    )
                    if candidate:
                        break

        if not candidate:
            shortfall = (
                f"Catalog feasibility shortfall on Day {day_spec.day_number} ({day_spec.day_label}), "
                f"Slot 2 (secondary_compound): Zero eligible secondary compound exercises found in catalog matching "
                f"environment '{request.environment}', available equipment {request.availableEquipment}, "
                f"and active exclusions."
            )
            return None, shortfall

        planned = self._create_planned_exercise(
            slot_role=ExerciseSlotRole.SECONDARY_COMPOUND,
            slot_index=2,
            candidate=candidate,
            goal=request.targetGoal,
        )
        return planned, None

    # -------------------------------------------------------------------------
    # Slots 3 & 4: Accessory Exercises
    # -------------------------------------------------------------------------
    def _allocate_accessory_slot(
        self,
        slot_spec: SlotSpec,
        day_spec: DayTemplateSpec,
        request: WorkoutPlanGenerateRequest,
        current_excluded_ids: Set[str],
        prefer_unilateral: bool = False,
    ) -> Tuple[Optional[PlannedExercise], Optional[str]]:
        """Selects an accessory movement for Slot 3 or Slot 4."""
        rec_req = ExerciseRecommendationRequest(
            intent=RecommendationIntent.GENERAL,
            targetGoal=request.targetGoal,
            fitnessLevel=request.fitnessLevel,
            environment=request.environment,
            availableEquipment=request.availableEquipment,
            movementPattern=slot_spec.preferred_pattern,
            targetMuscles=slot_spec.preferred_muscles if slot_spec.preferred_muscles else day_spec.target_muscles,
            preferredLaterality="unilateral" if prefer_unilateral else None,
            excludedEquipment=request.excludedEquipment,
            excludedExerciseIds=list(current_excluded_ids),
            formAnalysisSupportedOnly=request.formAnalysisSupportedOnly,
            limit=20,
            enableDiversity=False,
        )
        rec_res = self._recommendation_service.recommend(rec_req)

        candidate: Optional[ExerciseRecommendationNode] = None

        if prefer_unilateral and rec_res.candidates:
            # Prefer unilateral candidate if available
            for cand in rec_res.candidates:
                catalog_ex = self._catalog_by_id.get(cand.exerciseId)
                if catalog_ex and catalog_ex.laterality == "unilateral":
                    candidate = cand
                    break

        if not candidate and rec_res.candidates:
            candidate = rec_res.candidates[0]

        # Broaden query across day's target muscles if no candidate found for preferred pattern
        if not candidate:
            broad_req = ExerciseRecommendationRequest(
                intent=RecommendationIntent.GENERAL,
                targetGoal=request.targetGoal,
                fitnessLevel=request.fitnessLevel,
                environment=request.environment,
                availableEquipment=request.availableEquipment,
                targetMuscles=day_spec.target_muscles,
                excludedEquipment=request.excludedEquipment,
                excludedExerciseIds=list(current_excluded_ids),
                formAnalysisSupportedOnly=request.formAnalysisSupportedOnly,
                limit=10,
                enableDiversity=False,
            )
            broad_res = self._recommendation_service.recommend(broad_req)
            if broad_res.candidates:
                candidate = broad_res.candidates[0]

        if not candidate:
            shortfall = (
                f"Catalog feasibility shortfall on Day {day_spec.day_number} ({day_spec.day_label}), "
                f"Slot {slot_spec.slot_index} ({slot_spec.slot_role.value}): Zero eligible accessory exercises found in catalog."
            )
            return None, shortfall

        planned = self._create_planned_exercise(
            slot_role=slot_spec.slot_role,
            slot_index=slot_spec.slot_index,
            candidate=candidate,
            goal=request.targetGoal,
        )
        return planned, None

    # -------------------------------------------------------------------------
    # Slot 5: Core / Mobility
    # -------------------------------------------------------------------------
    def _allocate_core_mobility_slot(
        self,
        slot_spec: SlotSpec,
        day_spec: DayTemplateSpec,
        request: WorkoutPlanGenerateRequest,
        current_excluded_ids: Set[str],
    ) -> Tuple[Optional[PlannedExercise], Optional[str]]:
        """Selects a core stability, carry, or mobility exercise for Slot 5."""
        core_patterns: List[MovementPattern] = [
            "core_anti_extension",
            "core_anti_rotation",
            "carry",
            "mobility",
        ]
        preferred = slot_spec.preferred_pattern or "core_anti_extension"

        # Query specifically for core/mobility pattern
        rec_req = ExerciseRecommendationRequest(
            intent=RecommendationIntent.GENERAL,
            targetGoal=request.targetGoal,
            fitnessLevel=request.fitnessLevel,
            environment=request.environment,
            availableEquipment=request.availableEquipment,
            movementPattern=preferred,
            targetMuscles=["core", "abs"],
            excludedEquipment=request.excludedEquipment,
            excludedExerciseIds=list(current_excluded_ids),
            formAnalysisSupportedOnly=request.formAnalysisSupportedOnly,
            limit=20,
            enableDiversity=False,
        )
        rec_res = self._recommendation_service.recommend(rec_req)

        candidate: Optional[ExerciseRecommendationNode] = None

        if rec_res.candidates:
            candidate = rec_res.candidates[0]

        # If preferred pattern yielded 0, query across all core/mobility patterns
        if not candidate:
            broad_req = ExerciseRecommendationRequest(
                intent=RecommendationIntent.GENERAL,
                targetGoal=request.targetGoal,
                fitnessLevel=request.fitnessLevel,
                environment=request.environment,
                availableEquipment=request.availableEquipment,
                targetMuscles=["core", "abs"],
                excludedEquipment=request.excludedEquipment,
                excludedExerciseIds=list(current_excluded_ids),
                formAnalysisSupportedOnly=request.formAnalysisSupportedOnly,
                limit=20,
                enableDiversity=False,
            )
            broad_res = self._recommendation_service.recommend(broad_req)
            for cand in broad_res.candidates:
                if cand.movementPattern in core_patterns or any(m in ("core", "abs") for m in cand.primaryMuscles):
                    candidate = cand
                    break

        if not candidate:
            shortfall = (
                f"Catalog feasibility shortfall on Day {day_spec.day_number} ({day_spec.day_label}), "
                f"Slot 5 (core_mobility): Zero eligible core or mobility exercises found in catalog."
            )
            return None, shortfall

        planned = self._create_planned_exercise(
            slot_role=ExerciseSlotRole.CORE_MOBILITY,
            slot_index=5,
            candidate=candidate,
            goal=request.targetGoal,
        )
        return planned, None

    # =========================================================================
    # HELPER: COMPOUND QUERY
    # =========================================================================

    def _query_best_compound(
        self,
        pattern: Optional[MovementPattern],
        muscles: List[MuscleGroup],
        excluded_ids: Set[str],
        request: WorkoutPlanGenerateRequest,
    ) -> Optional[ExerciseRecommendationNode]:
        """Queries ExerciseRecommendationService and extracts the top compound candidate."""
        rec_req = ExerciseRecommendationRequest(
            intent=RecommendationIntent.GENERAL,
            targetGoal=request.targetGoal,
            fitnessLevel=request.fitnessLevel,
            environment=request.environment,
            availableEquipment=request.availableEquipment,
            movementPattern=pattern,
            targetMuscles=muscles,
            excludedEquipment=request.excludedEquipment,
            excludedExerciseIds=list(excluded_ids),
            formAnalysisSupportedOnly=request.formAnalysisSupportedOnly,
            limit=30,
            enableDiversity=False,
        )
        rec_res = self._recommendation_service.recommend(rec_req)

        for cand in rec_res.candidates:
            if cand.exerciseType == "compound":
                return cand

        return None

    # =========================================================================
    # HELPER: PLANNED EXERCISE FACTORY
    # =========================================================================

    def _create_planned_exercise(
        self,
        slot_role: ExerciseSlotRole,
        slot_index: int,
        candidate: ExerciseRecommendationNode,
        goal: FitnessGoal,
    ) -> PlannedExercise:
        """Constructs a PlannedExercise with deterministic structural sets."""
        sets = self._build_structural_sets(slot_role, goal)
        estimated_duration = sum(max(1, int((s.restSeconds + 45) / 60)) for s in sets)
        return PlannedExercise(
            slot_role=slot_role,
            slot_index=slot_index,
            exercise_id=candidate.exerciseId,
            name=candidate.name,
            movement_pattern=candidate.movementPattern,
            exercise_type=candidate.exerciseType,
            difficulty=candidate.difficulty,
            equipment=list(candidate.equipment),
            primary_muscles=list(candidate.primaryMuscles),
            prescribed_sets=sets,
            estimated_duration_minutes=estimated_duration,
            score=candidate.score,
            reasons=candidate.reasons,
            is_canonical_cv=candidate.isCanonicalCv,
        )

    def _build_structural_sets(
        self, slot_role: ExerciseSlotRole, goal: FitnessGoal
    ) -> List[PlannedSet]:
        """Generates deterministic baseline structural sets for 9B.8.5.2."""
        if slot_role == ExerciseSlotRole.WARMUP_CORRECTIVE:
            return [
                PlannedSet(set_number=1, target_reps=10, target_rpe=5.0, rest_seconds=60),
                PlannedSet(set_number=2, target_reps=10, target_rpe=5.0, rest_seconds=60),
            ]
        elif slot_role == ExerciseSlotRole.PRIMARY_COMPOUND:
            reps = 5 if goal == "strength" else (12 if goal == "endurance" else 8)
            rest = 150 if goal == "strength" else (60 if goal == "endurance" else 90)
            return [
                PlannedSet(set_number=1, target_reps=reps, target_rpe=8.0, rest_seconds=rest),
                PlannedSet(set_number=2, target_reps=reps, target_rpe=8.0, rest_seconds=rest),
                PlannedSet(set_number=3, target_reps=reps, target_rpe=8.0, rest_seconds=rest),
            ]
        elif slot_role == ExerciseSlotRole.SECONDARY_COMPOUND:
            reps = 6 if goal == "strength" else (12 if goal == "endurance" else 10)
            rest = 120 if goal == "strength" else (60 if goal == "endurance" else 90)
            return [
                PlannedSet(set_number=1, target_reps=reps, target_rpe=7.5, rest_seconds=rest),
                PlannedSet(set_number=2, target_reps=reps, target_rpe=7.5, rest_seconds=rest),
                PlannedSet(set_number=3, target_reps=reps, target_rpe=7.5, rest_seconds=rest),
            ]
        elif slot_role == ExerciseSlotRole.ACCESSORY_1:
            reps = 8 if goal == "strength" else (15 if goal == "endurance" else 10)
            rest = 90 if goal == "strength" else (45 if goal == "endurance" else 60)
            return [
                PlannedSet(set_number=1, target_reps=reps, target_rpe=7.5, rest_seconds=rest),
                PlannedSet(set_number=2, target_reps=reps, target_rpe=7.5, rest_seconds=rest),
                PlannedSet(set_number=3, target_reps=reps, target_rpe=7.5, rest_seconds=rest),
            ]
        elif slot_role == ExerciseSlotRole.ACCESSORY_2:
            reps = 10 if goal == "strength" else (15 if goal == "endurance" else 12)
            rest = 75 if goal == "strength" else (45 if goal == "endurance" else 60)
            return [
                PlannedSet(set_number=1, target_reps=reps, target_rpe=7.0, rest_seconds=rest),
                PlannedSet(set_number=2, target_reps=reps, target_rpe=7.0, rest_seconds=rest),
            ]
        else:  # CORE_MOBILITY
            return [
                PlannedSet(set_number=1, target_reps=12, target_rpe=7.0, rest_seconds=60),
                PlannedSet(set_number=2, target_reps=12, target_rpe=7.0, rest_seconds=60),
            ]

    # =========================================================================
    # WHOLE-PLAN FEASIBILITY VERIFICATION
    # =========================================================================

    def _verify_whole_plan_feasibility(
        self, planned_days: List[PlannedWorkoutDay]
    ) -> Optional[str]:
        """Validates the complete plan structure before returning State A."""
        for day in planned_days:
            # 1. Verify all required slots exist (Slots 1 to 5)
            roles_present = {ex.slotRole for ex in day.exercises}
            required_roles = {
                ExerciseSlotRole.PRIMARY_COMPOUND,
                ExerciseSlotRole.SECONDARY_COMPOUND,
                ExerciseSlotRole.ACCESSORY_1,
                ExerciseSlotRole.ACCESSORY_2,
                ExerciseSlotRole.CORE_MOBILITY,
            }
            missing_roles = required_roles - roles_present
            if missing_roles:
                return f"Feasibility failure on Day {day.dayNumber} ({day.dayLabel}): Missing required slots {sorted([r.value for r in missing_roles])}."

            # 2. Verify Primary Compound constraint
            primary_ex = next(
                (ex for ex in day.exercises if ex.slotRole == ExerciseSlotRole.PRIMARY_COMPOUND),
                None,
            )
            if not primary_ex or primary_ex.exerciseType != "compound":
                return f"Feasibility failure on Day {day.dayNumber} ({day.dayLabel}): Primary exercise '{primary_ex.name if primary_ex else 'None'}' is not a compound movement."

            # 3. Verify Intra-Day Deduplication
            exercise_ids = [ex.exerciseId for ex in day.exercises]
            if len(exercise_ids) != len(set(exercise_ids)):
                return f"Feasibility failure on Day {day.dayNumber} ({day.dayLabel}): Duplicate exercise IDs detected within the same day: {exercise_ids}."

        return None

    # =========================================================================
    # FILTER SUMMARY HELPER
    # =========================================================================

    def _summarize_applied_filters(
        self, request: WorkoutPlanGenerateRequest
    ) -> Dict[str, Any]:
        """Summarizes request parameters for transparent response metadata."""
        filters: Dict[str, Any] = {
            "target_goal": request.targetGoal,
            "fitness_level": request.fitnessLevel,
            "environment": request.environment,
            "training_days_per_week": request.trainingDaysPerWeek,
            "plan_duration_weeks": request.planDurationWeeks,
            "target_workout_duration_minutes": request.targetWorkoutDurationMinutes,
        }
        if request.availableEquipment is not None:
            filters["available_equipment"] = [
                eq.value if hasattr(eq, "value") else str(eq) for eq in request.availableEquipment
            ]
        if request.excludedEquipment:
            filters["excluded_equipment"] = [
                eq.value if hasattr(eq, "value") else str(eq) for eq in request.excludedEquipment
            ]
        if request.excludedExerciseIds:
            filters["excluded_exercise_ids"] = list(request.excludedExerciseIds)
        if request.correctiveSourceExerciseId:
            filters["corrective_source_exercise_id"] = request.correctiveSourceExerciseId
        if request.correctiveIssueId:
            filters["corrective_issue_id"] = request.correctiveIssueId
        if request.formAnalysisSupportedOnly:
            filters["form_analysis_supported_only"] = True
        if request.preferredSplit:
            filters["preferred_split"] = request.preferredSplit.value
        return filters


# ============================================================================
# Global Singleton
# ============================================================================

_workout_plan_service_instance: Optional[WorkoutPlanService] = None


def get_workout_plan_service() -> WorkoutPlanService:
    """Returns the global WorkoutPlanService singleton."""
    global _workout_plan_service_instance
    if _workout_plan_service_instance is None:
        _workout_plan_service_instance = WorkoutPlanService()
    return _workout_plan_service_instance
