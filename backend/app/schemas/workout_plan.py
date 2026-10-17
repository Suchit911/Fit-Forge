"""
Workout Plan Schemas & Domain Models (Phase 9B.8.5).

Provides strongly-typed schemas and domain models for deterministic multi-week,
multi-day workout plan generation built on the catalog, relationship graph,
and recommendation layers.

Strict Requirements:
1. Personalization strictly from explicit request payload (no silent reads from profiles/Firestore).
2. Multi-week block semantics (1–12 weeks; deterministic 4-week blocks).
3. Exact training-day split definitions (Full Body 1-3d, Upper/Lower 4d, UL+PPL 5d, PPL 6d).
4. Non-medical language enforcement in planned exercises and rationales.
5. Deterministic plan ID hashing (no random UUIDs or timestamps).
6. Read-only generation domain models without persistence side-effects.
"""

import hashlib
import json
from enum import Enum
from typing import List, Optional, Dict, Any, Union
from pydantic import BaseModel, Field, model_validator
from .user import DifficultyLevel, EquipmentType, MuscleGroup, FitnessGoal
from .exercise import (
    MovementPattern,
    ExerciseType,
    EnvironmentType,
    PROHIBITED_MEDICAL_PHRASES,
)

PLANNER_VERSION: str = "9B.8.5.1"


# ============================================================================
# Enums & Taxonomies
# ============================================================================

class WorkoutSplitType(str, Enum):
    """Supported deterministic workout splits."""
    FULL_BODY = "full_body"
    UPPER_LOWER = "upper_lower"
    PUSH_PULL_LEGS = "push_pull_legs"


class ExerciseSlotRole(str, Enum):
    """
    Deterministic slot role within a workout day template.
    Uses neutral, objective terminology (replaces any subjective neural-demand claims).
    """
    WARMUP_CORRECTIVE = "warmup_corrective"      # Slot 0 (optional corrective / mobility prep)
    PRIMARY_COMPOUND = "primary_compound"        # Slot 1 (primary compound movement)
    SECONDARY_COMPOUND = "secondary_compound"    # Slot 2 (secondary compound movement)
    ACCESSORY_1 = "accessory_1"                  # Slot 3 (accessory volume / isolation)
    ACCESSORY_2 = "accessory_2"                  # Slot 4 (accessory volume / isolation)
    CORE_MOBILITY = "core_mobility"              # Slot 5 (core / stability / mobility)


class BlockPhase(str, Enum):
    """Deterministic 4-week periodization phases."""
    ACCUMULATION = "Baseline Accumulation"
    VOLUME_LOADING = "Volume Loading"
    INTENSITY_PEAK = "Intensity Peak"
    DELOAD = "Deload & Consolidation"


# Block Phase Mapping Helper
def get_block_phase_label(week_number: int) -> str:
    """
    Returns the deterministic periodization phase label for a 1-indexed week number.
    Deterministic 4-week block structure:
      Week 1, 5, 9: Baseline Accumulation
      Week 2, 6, 10: Volume Loading
      Week 3, 7, 11: Intensity Peak
      Week 4, 8, 12: Deload & Consolidation
    """
    week_in_block = ((week_number - 1) % 4) + 1
    if week_in_block == 1:
        return BlockPhase.ACCUMULATION.value
    elif week_in_block == 2:
        return BlockPhase.VOLUME_LOADING.value
    elif week_in_block == 3:
        return BlockPhase.INTENSITY_PEAK.value
    else:
        return BlockPhase.DELOAD.value


def get_block_number(week_number: int) -> int:
    """Returns the 1-indexed 4-week block number for a given week (1-4 -> Block 1, 5-8 -> Block 2, 9-12 -> Block 3)."""
    return ((week_number - 1) // 4) + 1


class DurationFeasibility(str, Enum):
    """Feasibility classification of planned workout duration against user target."""
    FEASIBLE = "feasible"
    POTENTIALLY_OVER_TARGET = "potentially_over_target"
    IMPOSSIBLE_UNDER_CONSTRAINTS = "impossible_under_constraints"


# ============================================================================
# Planned Set & Exercise Models
# ============================================================================

class PlannedSet(BaseModel):
    """Prescribed set parameters with deterministic reps, RPE, rest seconds, and optional target weight."""
    setNumber: int = Field(..., alias="set_number", ge=1)
    targetReps: int = Field(..., alias="target_reps", ge=1)
    targetRepsMin: Optional[int] = Field(default=None, alias="target_reps_min", ge=1)
    targetRepsMax: Optional[int] = Field(default=None, alias="target_reps_max", ge=1)
    targetRpe: Optional[float] = Field(default=None, alias="target_rpe", ge=1.0, le=10.0)
    restSeconds: int = Field(..., alias="rest_seconds", ge=0)
    targetWeightKg: Optional[float] = Field(default=None, alias="target_weight_kg", ge=0.0)
    weightKg: Optional[float] = Field(default=None, alias="weight_kg", ge=0.0)
    notes: Optional[str] = Field(default=None)

    model_config = {"extra": "ignore", "populate_by_name": True}

    @model_validator(mode="after")
    def validate_rep_range(self) -> "PlannedSet":
        """Ensures targetRepsMin <= targetRepsMax if both are specified."""
        if self.targetRepsMin is not None and self.targetRepsMax is not None:
            if self.targetRepsMin > self.targetRepsMax:
                raise ValueError(
                    f"targetRepsMin ({self.targetRepsMin}) cannot exceed targetRepsMax ({self.targetRepsMax})."
                )
        return self


class PlannedExercise(BaseModel):
    """Fully resolved planned exercise with slot allocation, set prescriptions, and rationale."""
    slotRole: ExerciseSlotRole = Field(..., alias="slot_role")
    slotIndex: int = Field(..., alias="slot_index", ge=0)
    exerciseId: str = Field(..., alias="exercise_id")
    name: str
    movementPattern: MovementPattern = Field(..., alias="movement_pattern")
    exerciseType: ExerciseType = Field(..., alias="exercise_type")
    difficulty: DifficultyLevel
    equipment: List[EquipmentType] = Field(default_factory=list)
    primaryMuscles: List[MuscleGroup] = Field(default_factory=list, alias="primary_muscles")
    prescribedSets: List[PlannedSet] = Field(default_factory=list, alias="prescribed_sets")
    totalSets: int = Field(default=0, alias="total_sets")
    estimatedDurationMinutes: int = Field(default=0, alias="estimated_duration_minutes")
    targetWeightKg: Optional[float] = Field(default=None, alias="target_weight_kg", ge=0.0)
    weightKg: Optional[float] = Field(default=None, alias="weight_kg", ge=0.0)
    score: float = Field(default=0.0, ge=0.0, le=100.0)
    reasons: List[str] = Field(default_factory=list)
    isCanonicalCv: bool = Field(default=False, alias="is_canonical_cv")
    progressionNote: Optional[str] = Field(default=None, alias="progression_note")
    prescriptionRationale: Optional[str] = Field(default=None, alias="prescription_rationale")

    model_config = {"extra": "ignore", "populate_by_name": True}

    @model_validator(mode="after")
    def validate_planned_exercise_reasons(self) -> "PlannedExercise":
        """Ensures non-medical, factual language in planned exercise explanations and rationales."""
        for reason in self.reasons:
            lower = reason.lower()
            for phrase in PROHIBITED_MEDICAL_PHRASES:
                if phrase in lower:
                    raise ValueError(
                        f"Planned exercise reason contains prohibited medical phrase: '{phrase}'."
                    )
        if self.prescriptionRationale:
            lower_pr = self.prescriptionRationale.lower()
            for phrase in PROHIBITED_MEDICAL_PHRASES:
                if phrase in lower_pr:
                    raise ValueError(
                        f"Planned exercise prescription rationale contains prohibited medical phrase: '{phrase}'."
                    )
        return self

    @model_validator(mode="after")
    def populate_total_sets(self) -> "PlannedExercise":
        """Automatically synchronizes totalSets from prescribedSets if left 0."""
        if self.totalSets == 0 and self.prescribedSets:
            object.__setattr__(self, "totalSets", len(self.prescribedSets))
        return self


# ============================================================================
# Day & Week Domain Models
# ============================================================================

class PlannedWorkoutDay(BaseModel):
    """Structured training day containing day-level taxonomy targets and planned exercises."""
    dayNumber: int = Field(..., alias="day_number", ge=1, le=7)
    dayLabel: str = Field(..., alias="day_label")
    isRestDay: bool = Field(default=False, alias="is_rest_day")
    focus: str = Field(default="")
    targetPatterns: List[MovementPattern] = Field(default_factory=list, alias="target_patterns")
    targetMuscles: List[MuscleGroup] = Field(default_factory=list, alias="target_muscles")
    exercises: List[PlannedExercise] = Field(default_factory=list)
    totalSets: int = Field(default=0, alias="total_sets")
    estimatedDurationMinutes: int = Field(default=0, alias="estimated_duration_minutes")

    model_config = {"extra": "ignore", "populate_by_name": True}

    @model_validator(mode="after")
    def populate_day_metrics(self) -> "PlannedWorkoutDay":
        """Aggregates total sets and duration across planned exercises if not explicitly set."""
        if self.totalSets == 0 and self.exercises:
            total_s = sum(ex.totalSets for ex in self.exercises)
            object.__setattr__(self, "totalSets", total_s)
        if self.estimatedDurationMinutes == 0 and self.exercises:
            total_dur = sum(ex.estimatedDurationMinutes for ex in self.exercises)
            object.__setattr__(self, "estimatedDurationMinutes", total_dur)
        return self


class PlannedWeek(BaseModel):
    """Multi-day week container representing a single week within a 4-week block."""
    weekNumber: int = Field(..., alias="week_number", ge=1, le=12)
    phaseLabel: str = Field(..., alias="phase_label")
    days: List[PlannedWorkoutDay] = Field(default_factory=list)
    totalWeeklySets: int = Field(default=0, alias="total_weekly_sets")
    totalWorkouts: int = Field(default=0, alias="total_workouts")

    model_config = {"extra": "ignore", "populate_by_name": True}

    @model_validator(mode="after")
    def populate_week_metrics(self) -> "PlannedWeek":
        """Aggregates weekly metrics across non-rest training days."""
        if self.totalWeeklySets == 0 and self.days:
            total_s = sum(d.totalSets for d in self.days if not d.isRestDay)
            object.__setattr__(self, "totalWeeklySets", total_s)
        if self.totalWorkouts == 0 and self.days:
            workout_count = sum(1 for d in self.days if not d.isRestDay)
            object.__setattr__(self, "totalWorkouts", workout_count)
        return self


# ============================================================================
# Plan Generation Request & Response Models
# ============================================================================

class WorkoutPlanGenerateRequest(BaseModel):
    """
    Explicit request payload for deterministic plan generation.
    Strict personal boundary: personalizes ONLY from values provided in this payload.
    No silent reads of user profile, Firestore, progress, nutrition, or achievements.
    """
    targetGoal: FitnessGoal = Field(default="general_fitness", alias="target_goal")
    fitnessLevel: DifficultyLevel = Field(default="intermediate", alias="fitness_level")
    environment: EnvironmentType = Field(default="gym")
    availableEquipment: Optional[List[EquipmentType]] = Field(default=None, alias="available_equipment")
    trainingDaysPerWeek: int = Field(default=3, alias="training_days_per_week", ge=1, le=6)
    planDurationWeeks: int = Field(default=4, alias="plan_duration_weeks", ge=1, le=12)
    targetWorkoutDurationMinutes: int = Field(default=45, alias="target_workout_duration_minutes", ge=20, le=90)

    # Exclusions & Preferences
    excludedExerciseIds: List[str] = Field(default_factory=list, alias="excluded_exercise_ids")
    excludedEquipment: List[EquipmentType] = Field(default_factory=list, alias="excluded_equipment")
    preferredMovementPatterns: List[MovementPattern] = Field(default_factory=list, alias="preferred_movement_patterns")
    targetMuscles: List[MuscleGroup] = Field(default_factory=list, alias="target_muscles")

    # Corrective & Form Analysis Targeting
    correctiveSourceExerciseId: Optional[str] = Field(default=None, alias="corrective_source_exercise_id")
    correctiveIssueId: Optional[str] = Field(default=None, alias="corrective_issue_id")
    formAnalysisSupportedOnly: bool = Field(default=False, alias="form_analysis_supported_only")

    # Split Override (Optional)
    preferredSplit: Optional[WorkoutSplitType] = Field(default=None, alias="preferred_split")

    model_config = {"extra": "ignore", "populate_by_name": True}


class WorkoutPlanResponse(BaseModel):
    """Complete multi-week, multi-day generated workout plan or diagnostic shortfall."""
    planId: str = Field(..., alias="plan_id")
    title: str
    description: str
    targetGoal: FitnessGoal = Field(..., alias="target_goal")
    fitnessLevel: DifficultyLevel = Field(..., alias="fitness_level")
    splitType: WorkoutSplitType = Field(..., alias="split_type")
    trainingDaysPerWeek: int = Field(..., alias="training_days_per_week")
    totalWeeks: int = Field(..., alias="total_weeks")
    weeks: List[PlannedWeek] = Field(default_factory=list)
    appliedFilters: Dict[str, Any] = Field(default_factory=dict, alias="applied_filters")
    feasibilityCheckPassed: bool = Field(default=True, alias="feasibility_check_passed")
    durationFeasibility: DurationFeasibility = Field(default=DurationFeasibility.FEASIBLE, alias="duration_feasibility")
    diagnostics: List[str] = Field(default_factory=list)
    conflictingFilters: List[str] = Field(default_factory=list, alias="conflicting_filters")

    model_config = {"extra": "ignore", "populate_by_name": True}


# ============================================================================
# Deterministic Plan ID Generator
# ============================================================================

def generate_deterministic_plan_id(
    request: WorkoutPlanGenerateRequest,
    planner_version: str = PLANNER_VERSION,
) -> str:
    """
    Computes a deterministic, collision-resistant plan ID from a canonical
    JSON serialization of the normalized request parameters and planner version.
    Identical inputs produce identical plan IDs without timestamps or random UUIDs.
    """
    normalized_dict = {
        "target_goal": request.targetGoal,
        "fitness_level": request.fitnessLevel,
        "environment": request.environment,
        "available_equipment": sorted(request.availableEquipment) if request.availableEquipment else None,
        "training_days_per_week": request.trainingDaysPerWeek,
        "plan_duration_weeks": request.planDurationWeeks,
        "target_workout_duration_minutes": request.targetWorkoutDurationMinutes,
        "excluded_exercise_ids": sorted(request.excludedExerciseIds),
        "excluded_equipment": sorted(request.excludedEquipment),
        "preferred_movement_patterns": sorted(request.preferredMovementPatterns),
        "target_muscles": sorted(request.targetMuscles),
        "corrective_source_exercise_id": request.correctiveSourceExerciseId,
        "corrective_issue_id": request.correctiveIssueId,
        "form_analysis_supported_only": request.formAnalysisSupportedOnly,
        "preferred_split": request.preferredSplit.value if request.preferredSplit else None,
        "planner_version": planner_version,
    }
    serialized = json.dumps(normalized_dict, sort_keys=True, separators=(",", ":"))
    hash_digest = hashlib.sha256(serialized.encode("utf-8")).hexdigest()[:16]
    return f"plan_{hash_digest}"
