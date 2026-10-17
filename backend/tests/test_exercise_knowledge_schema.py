"""
Unit tests for Exercise Knowledge Schemas & Taxonomies (Phase 9B.8.1).

Validates:
1. Controlled taxonomy literal validation.
2. Full backward compatibility with Phase 3 ExerciseSchema.
3. Strict Canonical CV exercise mapping (exactly 5 capabilities).
4. MediaPipe Deadlift limitation enforcement (no bar-path tracking claims).
5. Non-medical language enforcement (rejection of pseudo-medical/injury-cure claims).
6. Relationship self-reference prevention.
7. Form corrective guidance and recommendation schemas.
"""

import pytest
from pydantic import ValidationError
from backend.app.schemas.exercise import (
    ExerciseKnowledgeSchema,
    FormCorrectiveGuidance,
    ExerciseRecommendationCandidate,
    ExerciseRecommendationFilter,
    ExerciseRecommendationResponse,
    CANONICAL_CV_EXERCISES,
    CV_KEY_TO_CATALOG_ID,
    get_canonical_cv_exercise_id,
    is_canonical_cv_exercise,
    VALID_MOVEMENT_PATTERNS,
    VALID_EXERCISE_CATEGORIES,
    VALID_CV_EXERCISE_KEYS,
)
from backend.app.schemas.workout import ExerciseSchema


# ============================================================================
# 1. Controlled Taxonomy Validation
# ============================================================================

def test_controlled_taxonomies_constants():
    """Validates the taxonomy sets contain all expected standardized values."""
    assert len(CANONICAL_CV_EXERCISES) == 5
    assert set(CANONICAL_CV_EXERCISES.values()) == {
        "squat", "bench_press", "deadlift", "bicep_curl", "shoulder_press"
    }
    assert "squat" in VALID_MOVEMENT_PATTERNS
    assert "hinge" in VALID_MOVEMENT_PATTERNS
    assert "horizontal_push" in VALID_MOVEMENT_PATTERNS
    assert "horizontal_pull" in VALID_MOVEMENT_PATTERNS
    assert "vertical_push" in VALID_MOVEMENT_PATTERNS
    assert "vertical_pull" in VALID_MOVEMENT_PATTERNS
    assert "lunge" in VALID_MOVEMENT_PATTERNS
    assert "isolation" in VALID_MOVEMENT_PATTERNS
    assert "core_anti_extension" in VALID_MOVEMENT_PATTERNS
    assert "core_anti_rotation" in VALID_MOVEMENT_PATTERNS
    assert "carry" in VALID_MOVEMENT_PATTERNS
    assert "mobility" in VALID_MOVEMENT_PATTERNS

    assert "strength" in VALID_EXERCISE_CATEGORIES
    assert "activation_warmup" in VALID_EXERCISE_CATEGORIES


def test_invalid_movement_pattern_rejected():
    """Rejects invalid movement patterns outside the controlled taxonomy."""
    with pytest.raises(ValidationError) as exc_info:
        ExerciseKnowledgeSchema(
            id="ex_test_invalid",
            name="Invalid Pattern Exercise",
            description="Test description.",
            primaryMuscles=["chest"],
            movementPattern="flying",  # type: ignore
        )
    assert "movementPattern" in str(exc_info.value) or "movement_pattern" in str(exc_info.value)


# ============================================================================
# 2. Backward Compatibility with Phase 3
# ============================================================================

def test_backward_compatibility_with_phase_3_exercise_data():
    """
    Validates that a pure Phase 3 exercise dictionary (with no 9B.8 fields)
    parses cleanly into ExerciseKnowledgeSchema with default values.
    """
    phase_3_data = {
        "id": "ex_incline_db_press",
        "name": "Incline Dumbbell Press",
        "description": "Targets upper chest clavicular head with greater freedom of movement.",
        "primaryMuscles": ["chest"],
        "secondaryMuscles": ["shoulders", "triceps"],
        "equipment": ["dumbbells"],
        "difficulty": "intermediate",
        "category": "hypertrophy",
        "instructions": [
            "Set bench to 30 degrees.",
            "Press dumbbells upward until arms are extended.",
            "Lower under control to chest level.",
        ],
        "commonMistakes": ["Setting bench angle too steep"],
        "safetyNotes": ["Kick dumbbells up into position using knees."],
        "supportedFormAnalysis": False,
        "supportedCameraMode": None,
        "imageUrl": "/assets/workout_lower_body.jpg",
        "isCustom": False,
    }

    exercise = ExerciseKnowledgeSchema(**phase_3_data)

    # Core Phase 3 fields
    assert exercise.id == "ex_incline_db_press"
    assert exercise.name == "Incline Dumbbell Press"
    assert exercise.primaryMuscles == ["chest"]
    assert exercise.secondaryMuscles == ["shoulders", "triceps"]
    assert exercise.equipment == ["dumbbells"]
    assert exercise.difficulty == "intermediate"
    assert exercise.category == "hypertrophy"
    assert exercise.supportedFormAnalysis is False
    assert exercise.isCustom is False

    # Enhanced 9B.8 fields default gracefully
    assert exercise.aliases == []
    assert exercise.movementPattern == "isolation"
    assert exercise.exerciseType == "compound"
    assert exercise.laterality == "bilateral"
    assert exercise.planeOfMotion == "sagittal"
    assert exercise.progressions == []
    assert exercise.regressions == []
    assert exercise.substitutions == []
    assert exercise.complementaryExercises == []
    assert exercise.cvExerciseId is None
    assert exercise.isDeprecated is False

    # Must be an instance of Phase 3 ExerciseSchema
    assert isinstance(exercise, ExerciseSchema)


def test_phase_3_exercise_schema_remains_independent():
    """Verifies that the original ExerciseSchema continues to work unmodified."""
    original = ExerciseSchema(
        id="ex_classic",
        name="Classic Exercise",
        description="Phase 3 model test.",
        primaryMuscles=["quadriceps"],
        difficulty="beginner",
    )
    assert original.id == "ex_classic"
    assert not hasattr(original, "movementPattern")


# ============================================================================
# 3. Canonical CV Exercise Mapping (Exactly 5 Capabilities)
# ============================================================================

@pytest.mark.parametrize(
    "catalog_id,expected_cv_key",
    [
        ("ex_squat", "squat"),
        ("ex_bench_press", "bench_press"),
        ("ex_deadlift", "deadlift"),
        ("ex_bicep_curl", "bicep_curl"),
        ("ex_shoulder_press", "shoulder_press"),
    ],
)
def test_canonical_cv_exercise_helpers(catalog_id: str, expected_cv_key: str):
    """Verifies canonical CV lookup helpers."""
    assert is_canonical_cv_exercise(catalog_id) is True
    assert get_canonical_cv_exercise_id(catalog_id) == expected_cv_key
    assert CV_KEY_TO_CATALOG_ID[expected_cv_key] == catalog_id


def test_non_cv_exercise_helpers():
    """Verifies non-CV exercise helpers return False/None."""
    assert is_canonical_cv_exercise("ex_incline_db_press") is False
    assert get_canonical_cv_exercise_id("ex_incline_db_press") is None
    assert is_canonical_cv_exercise("ex_barbell_back_squat") is False  # Only ex_squat is canonical


def test_cv_exercise_schema_validation_success():
    """Validates that a correctly mapped canonical CV exercise passes validation."""
    squat = ExerciseKnowledgeSchema(
        id="ex_squat",
        name="Barbell Back Squat",
        description="Standard bilateral knee flexion squat.",
        primaryMuscles=["quadriceps", "glutes"],
        secondaryMuscles=["hamstrings", "core"],
        equipment=["barbell"],
        difficulty="intermediate",
        category="strength",
        supportedFormAnalysis=True,
        supportedCameraMode="side",
        cvExerciseId="squat",
        movementPattern="squat",
    )
    assert squat.supportedFormAnalysis is True
    assert squat.cvExerciseId == "squat"


def test_cv_exercise_missing_cv_id_rejected():
    """Rejects supportedFormAnalysis=True when cvExerciseId is missing."""
    with pytest.raises(ValidationError) as exc_info:
        ExerciseKnowledgeSchema(
            id="ex_squat",
            name="Squat",
            description="Missing CV id.",
            primaryMuscles=["quadriceps"],
            supportedFormAnalysis=True,
            cvExerciseId=None,
        )
    assert "cvExerciseId is None" in str(exc_info.value)


def test_cv_exercise_non_canonical_id_rejected():
    """Rejects supportedFormAnalysis=True on an exercise ID not in CANONICAL_CV_EXERCISES."""
    with pytest.raises(ValidationError) as exc_info:
        ExerciseKnowledgeSchema(
            id="ex_cable_crossover",
            name="Cable Crossover",
            description="Attempting to mark unsupported exercise as CV supported.",
            primaryMuscles=["chest"],
            supportedFormAnalysis=True,
            cvExerciseId="bench_press",
        )
    assert "not one of the exactly 5 canonical CV exercises" in str(exc_info.value)


def test_cv_exercise_id_mismatch_rejected():
    """Rejects canonical exercise that declares a mismatching CV engine key."""
    with pytest.raises(ValidationError) as exc_info:
        ExerciseKnowledgeSchema(
            id="ex_squat",
            name="Squat",
            description="Mismatching CV key.",
            primaryMuscles=["quadriceps"],
            supportedFormAnalysis=True,
            cvExerciseId="deadlift",  # Mismatch: ex_squat must map to squat
        )
    assert "canonical mapping requires 'squat'" in str(exc_info.value)


def test_non_cv_exercise_with_cv_key_rejected():
    """Rejects non-CV exercise (supportedFormAnalysis=False) that has a cvExerciseId set."""
    with pytest.raises(ValidationError) as exc_info:
        ExerciseKnowledgeSchema(
            id="ex_incline_db_press",
            name="Incline DB Press",
            description="Non-CV exercise with CV ID.",
            primaryMuscles=["chest"],
            supportedFormAnalysis=False,
            cvExerciseId="bench_press",
        )
    assert "Non-CV exercises must have cvExerciseId=None" in str(exc_info.value)


# ============================================================================
# 4. Deadlift CV Limitation (No Bar-Path Tracking Claims)
# ============================================================================

def test_deadlift_valid_metadata():
    """Validates that deadlift metadata describing body-center/sequencing passes cleanly."""
    deadlift = ExerciseKnowledgeSchema(
        id="ex_deadlift",
        name="Conventional Deadlift",
        description="Hip hinge movement driving through the floor.",
        primaryMuscles=["back", "hamstrings"],
        secondaryMuscles=["glutes", "core"],
        equipment=["barbell"],
        difficulty="advanced",
        category="strength",
        supportedFormAnalysis=True,
        supportedCameraMode="side",
        cvExerciseId="deadlift",
        movementPattern="hinge",
        cvLimitationsNote="MediaPipe CV estimates hip/knee sequencing and torso angle proxy; does not track barbell object.",
        executionCues=["Drive floor away with mid-foot pressure", "Maintain stable spinal alignment proxy"],
    )
    assert deadlift.cvExerciseId == "deadlift"


@pytest.mark.parametrize(
    "prohibited_claim",
    [
        "bar path tracking",
        "actual bar path",
        "bar trajectory measurement",
        "barbell tracking",
    ],
)
def test_deadlift_prohibited_bar_path_claim_rejected(prohibited_claim: str):
    """Rejects deadlift metadata claiming actual bar-path or barbell tracking."""
    with pytest.raises(ValidationError) as exc_info:
        ExerciseKnowledgeSchema(
            id="ex_deadlift",
            name="Deadlift",
            description=f"Posterior chain pull with {prohibited_claim}.",
            primaryMuscles=["back"],
            supportedFormAnalysis=True,
            supportedCameraMode="side",
            cvExerciseId="deadlift",
            movementPattern="hinge",
        )
    assert "contains prohibited deadlift claim" in str(exc_info.value)


# ============================================================================
# 5. Non-Medical Language Enforcement
# ============================================================================

@pytest.mark.parametrize(
    "medical_phrase",
    [
        "cures pain in lower back",
        "prevents injury completely",
        "prevents injuries for all athletes",
        "treats condition of scoliosis",
        "safe for herniated discs",
        "pain-free guarantee with this movement",
    ],
)
def test_medical_claims_rejected(medical_phrase: str):
    """Rejects pseudo-medical or injury-cure claims across exercise text fields."""
    with pytest.raises(ValidationError) as exc_info:
        ExerciseKnowledgeSchema(
            id="ex_glute_bridge",
            name="Glute Bridge",
            description=f"Hip extension exercise that {medical_phrase}.",
            primaryMuscles=["glutes"],
            difficulty="beginner",
            movementPattern="hinge",
        )
    assert "contains non-compliant medical claim" in str(exc_info.value)


def test_practical_biomechanical_cues_accepted():
    """Confirms practical, non-clinical biomechanical guidance passes validation."""
    ex = ExerciseKnowledgeSchema(
        id="ex_goblet_squat",
        name="Goblet Squat",
        description="Front-loaded squat variation reinforcing upright torso mechanics.",
        primaryMuscles=["quadriceps", "glutes"],
        difficulty="beginner",
        movementPattern="squat",
        setupCues=["Hold dumbbell vertically against chest", "Stance shoulder-width apart"],
        executionCues=["Descend between hips while maintaining stable torso angle", "Drive through mid-foot"],
        movementCautions=["Moderate compressive load on anterior knee flexion"],
    )
    assert ex.id == "ex_goblet_squat"


# ============================================================================
# 6. Self-Reference Prevention
# ============================================================================

@pytest.mark.parametrize("rel_field", ["progressions", "regressions", "substitutions", "complementaryExercises"])
def test_self_reference_rejected(rel_field: str):
    """Rejects exercises listing themselves in their own relationship arrays."""
    kwargs = {
        "id": "ex_push_up",
        "name": "Push-Up",
        "description": "Standard push-up.",
        "primaryMuscles": ["chest"],
        rel_field: ["ex_push_up"],
    }
    with pytest.raises(ValidationError) as exc_info:
        ExerciseKnowledgeSchema(**kwargs)
    assert "cannot reference itself" in str(exc_info.value)


# ============================================================================
# 7. Form Corrective & Recommendation Schemas
# ============================================================================

def test_form_corrective_guidance_schema():
    """Validates FormCorrectiveGuidance model serialization and fields."""
    guidance = FormCorrectiveGuidance(
        finding="valgus_knee",
        cue="Push knees outward over toes during ascent.",
        regressions=["ex_box_squat"],
        accessoryExercises=["ex_glute_bridge", "ex_lateral_band_walk"],
        techniqueDrills=["Tempo pause squats with mini-band around knees"],
    )
    data = guidance.model_dump()
    assert data["finding"] == "valgus_knee"
    assert data["regressions"] == ["ex_box_squat"]
    assert len(data["accessoryExercises"]) == 2


def test_recommendation_schemas():
    """Validates recommendation candidate and response models."""
    exercise = ExerciseKnowledgeSchema(
        id="ex_bench_press",
        name="Bench Press",
        description="Barbell flat bench press.",
        primaryMuscles=["chest"],
        secondaryMuscles=["shoulders", "triceps"],
        equipment=["barbell", "bench"],
        difficulty="intermediate",
        category="strength",
        supportedFormAnalysis=True,
        supportedCameraMode="side",
        cvExerciseId="bench_press",
        movementPattern="horizontal_push",
    )

    candidate = ExerciseRecommendationCandidate(
        exerciseId=exercise.id,
        exercise=exercise,
        score=0.92,
        reasons=["Matches primary chest muscle", "Matches available barbell equipment"],
        isPrimaryMatch=True,
    )

    response = ExerciseRecommendationResponse(
        candidates=[candidate],
        appliedFilters={"environment": "gym", "equipment": ["barbell", "bench"]},
        totalEligible=1,
    )

    dump = response.model_dump()
    assert dump["totalEligible"] == 1
    assert len(dump["candidates"]) == 1
    assert dump["candidates"][0]["exerciseId"] == "ex_bench_press"
    assert dump["candidates"][0]["score"] == 0.92
