"""
Exercise Knowledge & Recommendation Schemas (Phase 9B.8).

Provides:
- Controlled taxonomies: MovementPattern, ExerciseCategory, ExerciseType, Laterality, PlaneOfMotion, CVExerciseKey.
- Canonical CV mapping: Exactly 5 catalog exercises supported by MediaPipe CV.
- ExerciseKnowledgeSchema: Comprehensive domain model extending Phase 3 ExerciseSchema with full backward compatibility.
- Referential integrity, non-medical language, and CV limitation validators.
- Recommendation & Form Corrective models.
"""

from enum import Enum
from typing import List, Optional, Literal, Dict, Any, get_args, Union
from pydantic import BaseModel, Field, model_validator
from .user import DifficultyLevel, Environment, EquipmentType, MuscleGroup, FitnessGoal
from .workout import ExerciseSchema

# Controlled Taxonomies
MovementPattern = Literal[
    "squat",
    "hinge",
    "horizontal_push",
    "horizontal_pull",
    "vertical_push",
    "vertical_pull",
    "lunge",
    "isolation",
    "core_anti_extension",
    "core_anti_rotation",
    "carry",
    "mobility",
]

ExerciseCategory = Literal[
    "strength",
    "hypertrophy",
    "endurance",
    "mobility",
    "activation_warmup",
    "cardio",
    "custom",
]

ExerciseType = Literal["compound", "isolation"]

Laterality = Literal["bilateral", "unilateral", "alternating"]

PlaneOfMotion = Literal["sagittal", "frontal", "transverse", "multi_planar"]

EnvironmentType = Literal["gym", "home", "outdoor", "anywhere"]

CVExerciseKey = Literal[
    "squat",
    "bench_press",
    "deadlift",
    "bicep_curl",
    "shoulder_press",
]

# Sets of valid taxonomy values for runtime reflection and validation
VALID_MOVEMENT_PATTERNS = set(get_args(MovementPattern))
VALID_EXERCISE_CATEGORIES = set(get_args(ExerciseCategory))
VALID_EXERCISE_TYPES = set(get_args(ExerciseType))
VALID_LATERALITIES = set(get_args(Laterality))
VALID_PLANES_OF_MOTION = set(get_args(PlaneOfMotion))
VALID_ENVIRONMENTS = set(get_args(EnvironmentType))
VALID_EQUIPMENT = set(get_args(EquipmentType))
VALID_MUSCLE_GROUPS = set(get_args(MuscleGroup))
VALID_DIFFICULTY_LEVELS = set(get_args(DifficultyLevel))
VALID_FITNESS_GOALS = set(get_args(FitnessGoal))
VALID_CV_EXERCISE_KEYS = set(get_args(CVExerciseKey))

# Canonical Computer-Vision Exercise Mapping
# Exactly 5 canonical exercises in the catalog correspond to the CV capabilities.
CANONICAL_CV_EXERCISES: Dict[str, CVExerciseKey] = {
    "ex_squat": "squat",
    "ex_bench_press": "bench_press",
    "ex_deadlift": "deadlift",
    "ex_bicep_curl": "bicep_curl",
    "ex_shoulder_press": "shoulder_press",
}

CV_KEY_TO_CATALOG_ID: Dict[CVExerciseKey, str] = {
    v: k for k, v in CANONICAL_CV_EXERCISES.items()
}


def get_canonical_cv_exercise_id(catalog_id: str) -> Optional[CVExerciseKey]:
    """Returns the internal CV engine key for a catalog exercise ID, or None if not supported."""
    return CANONICAL_CV_EXERCISES.get(catalog_id)


def is_canonical_cv_exercise(catalog_id: str) -> bool:
    """Returns True if the exercise ID corresponds to one of the 5 canonical CV exercises."""
    return catalog_id in CANONICAL_CV_EXERCISES


# Non-Medical Language Prohibited Phrases
PROHIBITED_MEDICAL_PHRASES = [
    "cures pain",
    "cure pain",
    "cures injury",
    "cure injury",
    "prevents injury",
    "prevent injury",
    "prevents injuries",
    "prevent injuries",
    "treats condition",
    "treats a condition",
    "treats pain",
    "treat pain",
    "diagnoses",
    "safe for herniated",
    "safe for disc herniation",
    "safe for torn",
    "rehabilitates torn",
    "pain-free guarantee",
    "injury-free guarantee",
]

# Prohibited Deadlift CV Claims (MediaPipe CV lacks barbell object tracking)
PROHIBITED_DEADLIFT_CV_PHRASES = [
    "bar path tracking",
    "actual bar path",
    "bar trajectory measurement",
    "barbell tracking",
    "actual bar trajectory",
]


class ExerciseKnowledgeSchema(ExerciseSchema):
    """
    Comprehensive domain model extending Phase 3 ExerciseSchema.
    Maintains 100% backward compatibility with all existing ExerciseSchema consumers
    while adding rich biomechanical, relational, and CV metadata.
    """
    aliases: List[str] = Field(default_factory=list)
    category: ExerciseCategory = Field(default="strength")
    movementPattern: MovementPattern = Field(default="isolation", alias="movement_pattern")
    exerciseType: ExerciseType = Field(default="compound", alias="exercise_type")
    laterality: Laterality = Field(default="bilateral")
    planeOfMotion: PlaneOfMotion = Field(default="sagittal", alias="plane_of_motion")
    stabilizerMuscles: List[MuscleGroup] = Field(default_factory=list, alias="stabilizer_muscles")
    optionalEquipment: List[EquipmentType] = Field(default_factory=list, alias="optional_equipment")
    targetEnvironments: List[EnvironmentType] = Field(
        default_factory=lambda: ["gym", "home"], alias="target_environments"
    )
    targetGoals: List[FitnessGoal] = Field(default_factory=list, alias="target_goals")
    setupCues: List[str] = Field(default_factory=list, alias="setup_cues")
    executionCues: List[str] = Field(default_factory=list, alias="execution_cues")
    breathingPattern: Optional[str] = Field(default=None, alias="breathing_pattern")

    # Relationship graph IDs (embedded reference arrays)
    progressions: List[str] = Field(default_factory=list)
    regressions: List[str] = Field(default_factory=list)
    substitutions: List[str] = Field(default_factory=list)
    complementaryExercises: List[str] = Field(default_factory=list, alias="complementary_exercises")

    # Non-medical movement load notices
    movementCautions: List[str] = Field(default_factory=list, alias="movement_cautions")

    # Computer Vision linkage
    cvExerciseId: Optional[CVExerciseKey] = Field(default=None, alias="cv_exercise_id")
    cvSupportedPlanes: List[PlaneOfMotion] = Field(default_factory=list, alias="cv_supported_planes")
    cvLimitationsNote: Optional[str] = Field(default=None, alias="cv_limitations_note")

    # Lifecycle & Deprecation
    isDeprecated: bool = Field(default=False, alias="is_deprecated")
    deprecatedReplacementId: Optional[str] = Field(default=None, alias="deprecated_replacement_id")

    model_config = {
        "extra": "ignore",
        "populate_by_name": True,
    }

    @model_validator(mode="after")
    def validate_exercise_knowledge(self) -> "ExerciseKnowledgeSchema":
        """
        Validates:
        1. Canonical CV mapping integrity (exactly 5 exercises supported, matching CANONICAL_CV_EXERCISES).
        2. Non-medical language enforcement (rejects injury-cure/medical claims).
        3. Deadlift CV limitation (rejects claims of actual bar-path/barbell tracking).
        4. Self-reference prevention in relationship arrays.
        """
        # 1. CV Mapping Integrity
        if self.supportedFormAnalysis:
            if not self.cvExerciseId:
                raise ValueError(
                    f"Exercise '{self.id}' has supportedFormAnalysis=True but cvExerciseId is None. "
                    f"Must specify a valid cvExerciseId from {list(VALID_CV_EXERCISE_KEYS)}."
                )
            if self.id not in CANONICAL_CV_EXERCISES:
                raise ValueError(
                    f"Exercise '{self.id}' is not one of the exactly 5 canonical CV exercises "
                    f"({list(CANONICAL_CV_EXERCISES.keys())}). Only canonical CV exercises may have supportedFormAnalysis=True."
                )
            expected_cv_id = CANONICAL_CV_EXERCISES[self.id]
            if self.cvExerciseId != expected_cv_id:
                raise ValueError(
                    f"Exercise '{self.id}' maps to cvExerciseId '{self.cvExerciseId}', "
                    f"but canonical mapping requires '{expected_cv_id}'."
                )
        else:
            if self.cvExerciseId is not None:
                raise ValueError(
                    f"Exercise '{self.id}' has supportedFormAnalysis=False but cvExerciseId='{self.cvExerciseId}'. "
                    f"Non-CV exercises must have cvExerciseId=None."
                )

        # 2. Deadlift CV Limitation Note & Cues check
        if self.cvExerciseId == "deadlift":
            combined_deadlift_text = " ".join([
                self.description or "",
                self.cvLimitationsNote or "",
                " ".join(self.setupCues or []),
                " ".join(self.executionCues or []),
                " ".join(self.commonMistakes or []),
            ]).lower()
            for phrase in PROHIBITED_DEADLIFT_CV_PHRASES:
                if phrase in combined_deadlift_text:
                    raise ValueError(
                        f"Exercise '{self.id}' contains prohibited deadlift claim '{phrase}'. "
                        "MediaPipe CV lacks barbell object tracking; metadata must not claim actual bar path or trajectory measurement."
                    )

        # 3. Non-Medical Language Enforcement
        combined_text = " ".join([
            self.description or "",
            " ".join(self.instructions or []),
            " ".join(self.commonMistakes or []),
            " ".join(self.safetyNotes or []),
            " ".join(self.setupCues or []),
            " ".join(self.executionCues or []),
            " ".join(self.movementCautions or []),
        ]).lower()
        for phrase in PROHIBITED_MEDICAL_PHRASES:
            if phrase in combined_text:
                raise ValueError(
                    f"Exercise '{self.id}' contains non-compliant medical claim: '{phrase}'. "
                    "Technique guidance must remain practical, biomechanical, and strictly non-clinical."
                )

        # 4. Self-Reference Prevention
        for rel_field, rel_list in [
            ("progressions", self.progressions),
            ("regressions", self.regressions),
            ("substitutions", self.substitutions),
            ("complementaryExercises", self.complementaryExercises),
        ]:
            if self.id in rel_list:
                raise ValueError(
                    f"Exercise '{self.id}' cannot reference itself in '{rel_field}'."
                )

        return self


# Form Corrective Guidance Model
class FormCorrectiveGuidance(BaseModel):
    """Deterministic guidance linking a CV heuristic finding to corrective technique cues and exercises."""
    finding: str
    cue: str
    regressions: List[str] = Field(default_factory=list)
    accessoryExercises: List[str] = Field(default_factory=list, alias="accessory_exercises")
    techniqueDrills: List[str] = Field(default_factory=list, alias="technique_drills")

    model_config = {"extra": "ignore", "populate_by_name": True}


# Recommendation Models (Deterministic candidate eligibility)
class ExerciseRecommendationCandidate(BaseModel):
    """Deterministic candidate exercise recommendation with score and human-readable reasons."""
    exerciseId: str = Field(..., alias="exercise_id")
    exercise: ExerciseKnowledgeSchema
    score: float
    reasons: List[str] = Field(default_factory=list)
    isPrimaryMatch: bool = Field(default=True, alias="is_primary_match")

    model_config = {"extra": "ignore", "populate_by_name": True}


class ExerciseRecommendationFilter(BaseModel):
    """
    Filter parameters for deterministic recommendation candidate generation.
    Hard exclusions: unavailable equipment, incompatible environment, deprecated exercises.
    Soft signals: muscle preference, difficulty preference, target goals.
    """
    availableEquipment: Optional[List[EquipmentType]] = Field(default=None, alias="available_equipment")
    environment: Optional[EnvironmentType] = None
    fitnessLevel: Optional[DifficultyLevel] = Field(default=None, alias="fitness_level")
    targetGoal: Optional[FitnessGoal] = Field(default=None, alias="target_goal")
    movementPattern: Optional[MovementPattern] = Field(default=None, alias="movement_pattern")
    targetMuscles: Optional[List[MuscleGroup]] = Field(default=None, alias="target_muscles")
    formAnalysisSupportedOnly: bool = Field(default=False, alias="form_analysis_supported_only")
    excludeExerciseIds: List[str] = Field(default_factory=list, alias="exclude_exercise_ids")
    limit: int = 10

    model_config = {"extra": "ignore", "populate_by_name": True}


# =============================================================================
# EXERCISE RELATIONSHIP GRAPH SCHEMAS (Phase 9B.8.3)
# =============================================================================

ExerciseRelationshipType = Literal[
    "progression",
    "regression",
    "substitution",
    "complement",
    "corrective",
]

VALID_RELATIONSHIP_TYPES = set(get_args(ExerciseRelationshipType))


class ExerciseRelationshipNode(BaseModel):
    """Deterministic relationship node describing a related target exercise."""
    exerciseId: str = Field(..., alias="exercise_id")
    name: str
    relationshipType: ExerciseRelationshipType = Field(..., alias="relationship_type")
    movementPattern: MovementPattern = Field(..., alias="movement_pattern")
    difficulty: DifficultyLevel
    equipment: List[EquipmentType] = Field(default_factory=list)
    primaryMuscles: List[MuscleGroup] = Field(default_factory=list, alias="primary_muscles")
    rationale: str
    priority: int = 1
    isCanonicalCv: bool = Field(default=False, alias="is_canonical_cv")

    model_config = {"extra": "ignore", "populate_by_name": True}

    @model_validator(mode="after")
    def validate_node_rationale(self) -> "ExerciseRelationshipNode":
        """Ensures non-medical, factual language in relationship rationales."""
        lower_rationale = (self.rationale or "").lower()
        for phrase in PROHIBITED_MEDICAL_PHRASES:
            if phrase in lower_rationale:
                raise ValueError(
                    f"Relationship rationale for '{self.exerciseId}' contains prohibited medical phrase: '{phrase}'."
                )
        return self


class CorrectiveGuidanceCandidate(BaseModel):
    """
    Deterministic mapping from an observable technique issue to corrective exercise candidates.
    Supports both normalized technique issue ID and underlying Phase 9B.2 heuristic name.
    """
    issueId: str = Field(..., alias="issue_id")
    heuristicName: str = Field(..., alias="heuristic_name")
    sourceExerciseId: str = Field(..., alias="source_exercise_id")
    candidateExercises: List[ExerciseRelationshipNode] = Field(default_factory=list, alias="candidate_exercises")
    reason: str
    priority: int = 1

    model_config = {"extra": "ignore", "populate_by_name": True}

    @model_validator(mode="after")
    def validate_candidate_reason(self) -> "CorrectiveGuidanceCandidate":
        """Ensures non-medical, factual language in corrective guidance reasons."""
        lower_reason = (self.reason or "").lower()
        for phrase in PROHIBITED_MEDICAL_PHRASES:
            if phrase in lower_reason:
                raise ValueError(
                    f"Corrective guidance reason for '{self.issueId}' contains prohibited medical phrase: '{phrase}'."
                )
        return self


class ExerciseRelationshipsResponse(BaseModel):
    """Comprehensive categorization and deduplicated summary of an exercise's relationships."""
    sourceExerciseId: str = Field(..., alias="source_exercise_id")
    sourceExerciseName: str = Field(..., alias="source_exercise_name")
    progressions: List[ExerciseRelationshipNode] = Field(default_factory=list)
    regressions: List[ExerciseRelationshipNode] = Field(default_factory=list)
    substitutions: List[ExerciseRelationshipNode] = Field(default_factory=list)
    complements: List[ExerciseRelationshipNode] = Field(default_factory=list)
    correctives: List[ExerciseRelationshipNode] = Field(default_factory=list)
    deduplicatedCandidates: List[ExerciseRelationshipNode] = Field(
        default_factory=list, alias="deduplicated_candidates"
    )
    totalRelationships: int = Field(default=0, alias="total_relationships")

    model_config = {"extra": "ignore", "populate_by_name": True}


class CatalogGraphStatistics(BaseModel):
    """Deterministic topological metrics for the 100-exercise relationship graph."""
    totalExercises: int = Field(..., alias="total_exercises")
    exercisesWithProgressions: int = Field(..., alias="exercises_with_progressions")
    exercisesWithRegressions: int = Field(..., alias="exercises_with_regressions")
    exercisesWithSubstitutions: int = Field(..., alias="exercises_with_substitutions")
    exercisesWithComplements: int = Field(..., alias="exercises_with_complements")
    totalEdges: int = Field(..., alias="total_edges")
    averageRelationshipsPerExercise: float = Field(..., alias="average_relationships_per_exercise")
    correctiveMappingsCount: int = Field(..., alias="corrective_mappings_count")
    orphanedExerciseCount: int = Field(..., alias="orphaned_exercise_count")
    degreeDistribution: Dict[str, int] = Field(default_factory=dict, alias="degree_distribution")

    model_config = {"extra": "ignore", "populate_by_name": True}


# Recommendation Schemas (Phase 9B.8.4)
class RecommendationIntent(str, Enum):
    GENERAL = "general"                 # Standard goal- and profile-based discovery
    PROGRESSION = "progression"         # Advance from source exercise
    REGRESSION = "regression"           # Regress from source exercise
    SUBSTITUTION = "substitution"       # Alternative for source exercise
    COMPLEMENT = "complement"           # Accessory work for source exercise
    CORRECTIVE = "corrective"           # Address an observed technique issue


class ExerciseRecommendationRequest(BaseModel):
    """Strongly typed recommendation query payload."""
    intent: RecommendationIntent = Field(default=RecommendationIntent.GENERAL)

    # User Profile / Contextual Inputs
    targetGoal: Optional[FitnessGoal] = Field(default=None, alias="target_goal")
    fitnessLevel: Optional[DifficultyLevel] = Field(default=None, alias="fitness_level")
    environment: Optional[EnvironmentType] = Field(default=None)
    availableEquipment: Optional[List[EquipmentType]] = Field(default=None, alias="available_equipment")

    # Movement & Muscle Preferences (Soft Ranking Signals)
    movementPattern: Optional[MovementPattern] = Field(default=None, alias="movement_pattern")
    targetMuscles: Optional[List[MuscleGroup]] = Field(default=None, alias="target_muscles")
    preferredCategory: Optional[ExerciseCategory] = Field(default=None, alias="preferred_category")
    preferredLaterality: Optional[Laterality] = Field(default=None, alias="preferred_laterality")

    # Hard Exclusions
    excludedEquipment: List[EquipmentType] = Field(default_factory=list, alias="excluded_equipment")
    excludedExerciseIds: List[str] = Field(default_factory=list, alias="excluded_exercise_ids")

    # Relationship & Corrective Targeting
    sourceExerciseId: Optional[str] = Field(default=None, alias="source_exercise_id")
    correctiveIssueId: Optional[str] = Field(default=None, alias="corrective_issue_id")
    formAnalysisSupportedOnly: bool = Field(default=False, alias="form_analysis_supported_only")

    # Pagination & Diversity Options
    limit: int = Field(default=10, ge=1, le=50)
    enableDiversity: bool = Field(default=True, alias="enable_diversity")

    model_config = {"extra": "ignore", "populate_by_name": True}


class ExerciseRecommendationNode(BaseModel):
    """Deterministic candidate recommendation with verified score and explainable reasons."""
    exerciseId: str = Field(..., alias="exercise_id")
    name: str
    movementPattern: MovementPattern = Field(..., alias="movement_pattern")
    exerciseType: ExerciseType = Field(..., alias="exercise_type")
    difficulty: DifficultyLevel
    equipment: List[EquipmentType] = Field(default_factory=list)
    primaryMuscles: List[MuscleGroup] = Field(default_factory=list, alias="primary_muscles")
    score: float = Field(..., ge=0.0, le=100.0)
    reasons: List[str] = Field(default_factory=list)
    relationshipType: Optional[ExerciseRelationshipType] = Field(default=None, alias="relationship_type")
    isCanonicalCv: bool = Field(default=False, alias="is_canonical_cv")

    model_config = {"extra": "ignore", "populate_by_name": True}

    @model_validator(mode="after")
    def validate_node_reasons(self) -> "ExerciseRecommendationNode":
        """Ensures non-medical language in recommendation reasons."""
        for reason in self.reasons:
            lower = reason.lower()
            for phrase in PROHIBITED_MEDICAL_PHRASES:
                if phrase in lower:
                    raise ValueError(
                        f"Recommendation reason contains prohibited medical phrase: '{phrase}'."
                    )
        return self


class ExerciseRecommendationResponse(BaseModel):
    """Response payload containing ranked candidates or clear diagnostics."""
    intent: RecommendationIntent = Field(default=RecommendationIntent.GENERAL)
    totalEvaluated: int = Field(default=0, alias="total_evaluated")
    totalEligible: int = Field(default=0, alias="total_eligible")
    returnedCount: int = Field(default=0, alias="returned_count")
    candidates: List[Union[ExerciseRecommendationNode, ExerciseRecommendationCandidate]] = Field(default_factory=list)
    appliedFilters: Dict[str, Any] = Field(default_factory=dict, alias="applied_filters")
    diagnostics: List[str] = Field(default_factory=list)
    conflictingFilters: List[str] = Field(default_factory=list, alias="conflicting_filters")

    model_config = {"extra": "ignore", "populate_by_name": True}

    @model_validator(mode="after")
    def populate_returned_count(self) -> "ExerciseRecommendationResponse":
        if self.returnedCount == 0 and self.candidates:
            object.__setattr__(self, "returnedCount", len(self.candidates))
        return self

