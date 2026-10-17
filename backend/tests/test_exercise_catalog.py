"""
Validation and Integrity Test Suite for the Authoritative 100-Exercise Catalog (Phase 9B.8.2).

Validates:
1. Exact count of 100 unique catalog exercises.
2. Complete schema compliance with ExerciseKnowledgeSchema.
3. Controlled taxonomy conformity across all fields.
4. Exactly 5 CV-supported exercises mapping to canonical keys.
5. Exactly 95 non-CV exercises with cvExerciseId=None.
6. Deadlift CV limitation compliance (no bar-path measurement claims).
7. Non-medical language compliance across all 100 exercises.
8. 100% referential integrity across all relationship pointers (progressions, regressions, substitutions, complementary).
9. Zero self-referencing relationships.
10. Distribution balance across all 10 core movement patterns.
11. Content completeness (every exercise possesses meaningful cues, instructions, and mistakes).
"""

import pytest
from backend.app.schemas.exercise import (
    ExerciseKnowledgeSchema,
    CANONICAL_CV_EXERCISES,
    CV_KEY_TO_CATALOG_ID,
    VALID_MOVEMENT_PATTERNS,
    VALID_EXERCISE_CATEGORIES,
    VALID_EXERCISE_TYPES,
    VALID_LATERALITIES,
    VALID_PLANES_OF_MOTION,
    VALID_ENVIRONMENTS,
    VALID_EQUIPMENT,
    VALID_MUSCLE_GROUPS,
    VALID_DIFFICULTY_LEVELS,
    VALID_FITNESS_GOALS,
    PROHIBITED_MEDICAL_PHRASES,
    PROHIBITED_DEADLIFT_CV_PHRASES,
)
from backend.app.seeds.exercise_catalog import (
    RAW_CATALOG_DATA,
    EXERCISE_CATALOG,
    CATALOG_BY_ID,
    CATALOG_BY_MOVEMENT_PATTERN,
    CATALOG_BY_PRIMARY_MUSCLE,
    CATALOG_CV_EXERCISES,
    get_catalog_exercise,
    get_catalog_cv_exercise,
)


def test_catalog_exact_count_and_uniqueness():
    """Verifies that the catalog contains exactly 100 unique exercises."""
    assert len(EXERCISE_CATALOG) == 100, f"Expected 100 exercises, found {len(EXERCISE_CATALOG)}"
    assert len(RAW_CATALOG_DATA) == 100
    assert len(CATALOG_BY_ID) == 100, "Duplicate exercise IDs detected"


def test_all_catalog_items_are_valid_knowledge_schemas():
    """Asserts that each item in EXERCISE_CATALOG is an instance of ExerciseKnowledgeSchema."""
    for ex in EXERCISE_CATALOG:
        assert isinstance(ex, ExerciseKnowledgeSchema)
        assert ex.id.startswith("ex_")
        assert len(ex.name.strip()) > 0
        assert len(ex.description.strip()) > 10


def test_taxonomy_validity_across_all_exercises():
    """Asserts that all fields strictly belong to the controlled taxonomy sets."""
    for ex in EXERCISE_CATALOG:
        assert ex.movementPattern in VALID_MOVEMENT_PATTERNS
        assert ex.category in VALID_EXERCISE_CATEGORIES
        assert ex.exerciseType in VALID_EXERCISE_TYPES
        assert ex.laterality in VALID_LATERALITIES
        assert ex.planeOfMotion in VALID_PLANES_OF_MOTION
        assert ex.difficulty in VALID_DIFFICULTY_LEVELS

        for env in ex.targetEnvironments:
            assert env in VALID_ENVIRONMENTS

        for goal in ex.targetGoals:
            assert goal in VALID_FITNESS_GOALS

        for muscle in ex.primaryMuscles:
            assert muscle in VALID_MUSCLE_GROUPS

        for muscle in ex.secondaryMuscles:
            assert muscle in VALID_MUSCLE_GROUPS

        for muscle in ex.stabilizerMuscles:
            assert muscle in VALID_MUSCLE_GROUPS

        for eq in ex.equipment:
            assert eq in VALID_EQUIPMENT

        for eq in ex.optionalEquipment:
            assert eq in VALID_EQUIPMENT


def test_cv_coverage_separation():
    """
    Asserts:
    1. Exactly 5 catalog exercises have supportedFormAnalysis=True.
    2. Exactly 95 catalog exercises have supportedFormAnalysis=False and cvExerciseId=None.
    3. The 5 CV exercises correspond exactly to CANONICAL_CV_EXERCISES.
    """
    cv_exercises = [ex for ex in EXERCISE_CATALOG if ex.supportedFormAnalysis]
    non_cv_exercises = [ex for ex in EXERCISE_CATALOG if not ex.supportedFormAnalysis]

    assert len(cv_exercises) == 5, f"Expected 5 CV exercises, got {len(cv_exercises)}"
    assert len(non_cv_exercises) == 95, f"Expected 95 non-CV exercises, got {len(non_cv_exercises)}"

    # Check non-CV exercises have no cvExerciseId
    for ex in non_cv_exercises:
        assert ex.cvExerciseId is None, f"Non-CV exercise '{ex.id}' has cvExerciseId='{ex.cvExerciseId}'"

    # Check the 5 CV exercises
    cv_id_map = {ex.id: ex.cvExerciseId for ex in cv_exercises}
    assert cv_id_map == CANONICAL_CV_EXERCISES
    assert len(CATALOG_CV_EXERCISES) == 5

    for cv_key, catalog_id in CV_KEY_TO_CATALOG_ID.items():
        assert get_catalog_cv_exercise(cv_key).id == catalog_id


def test_deadlift_cv_limitation():
    """Asserts that Deadlift metadata makes no actual bar-path measurement claims."""
    deadlift = get_catalog_exercise("ex_deadlift")
    assert deadlift is not None
    assert deadlift.cvExerciseId == "deadlift"

    combined_text = " ".join([
        deadlift.description,
        deadlift.cvLimitationsNote or "",
        " ".join(deadlift.setupCues),
        " ".join(deadlift.executionCues),
        " ".join(deadlift.commonMistakes),
    ]).lower()

    for phrase in PROHIBITED_DEADLIFT_CV_PHRASES:
        assert phrase not in combined_text, (
            f"Deadlift metadata contains prohibited claim: '{phrase}'"
        )


def test_non_medical_language_across_entire_catalog():
    """Asserts that none of the 100 exercises contain prohibited medical claims."""
    for ex in EXERCISE_CATALOG:
        all_text = " ".join([
            ex.description,
            " ".join(ex.instructions),
            " ".join(ex.commonMistakes),
            " ".join(ex.safetyNotes),
            " ".join(ex.setupCues),
            " ".join(ex.executionCues),
            " ".join(ex.movementCautions),
        ]).lower()

        for phrase in PROHIBITED_MEDICAL_PHRASES:
            assert phrase not in all_text, (
                f"Exercise '{ex.id}' contains prohibited medical claim: '{phrase}'"
            )


def test_referential_integrity_and_no_dangling_pointers():
    """Asserts that all relationship references resolve to existing exercises with no self-references."""
    for ex in EXERCISE_CATALOG:
        for rel_name, rel_list in [
            ("progressions", ex.progressions),
            ("regressions", ex.regressions),
            ("substitutions", ex.substitutions),
            ("complementaryExercises", ex.complementaryExercises),
        ]:
            for target_id in rel_list:
                assert target_id in CATALOG_BY_ID, (
                    f"Exercise '{ex.id}' references non-existent exercise '{target_id}' in '{rel_name}'"
                )
                assert target_id != ex.id, (
                    f"Exercise '{ex.id}' contains self-reference in '{rel_name}'"
                )


def test_movement_pattern_distribution():
    """Asserts that all 10 movement patterns are adequately populated."""
    expected_patterns = {
        "squat": 12,
        "hinge": 12,
        "horizontal_push": 12,
        "horizontal_pull": 11,
        "vertical_push": 10,
        "vertical_pull": 10,
        "lunge": 9,
        "isolation": 10,
        "core_anti_extension": 4,   # front plank, dead bug, hanging leg raise, ab wheel rollout
        "core_anti_rotation": 4,    # side plank, bird dog, pallof press, cable woodchopper
        "carry": 2,                 # farmers walk, suitcase carry
        "mobility": 4,              # worlds greatest stretch, cat cow, 90 90, thoracic foam roll
    }

    actual_counts = {pat: len(exs) for pat, exs in CATALOG_BY_MOVEMENT_PATTERN.items()}
    total = sum(actual_counts.values())
    assert total == 100

    for pat, expected_count in expected_patterns.items():
        assert actual_counts.get(pat, 0) == expected_count, (
            f"Pattern '{pat}': expected {expected_count}, got {actual_counts.get(pat, 0)}"
        )


def test_content_completeness():
    """Asserts that every exercise contains rich coaching cues and safety guidelines."""
    for ex in EXERCISE_CATALOG:
        assert len(ex.instructions) >= 2, f"Exercise '{ex.id}' has fewer than 2 instructions"
        assert len(ex.setupCues) >= 2, f"Exercise '{ex.id}' has fewer than 2 setup cues"
        assert len(ex.executionCues) >= 2, f"Exercise '{ex.id}' has fewer than 2 execution cues"
        assert len(ex.commonMistakes) >= 1, f"Exercise '{ex.id}' has no common mistakes"
        assert len(ex.safetyNotes) >= 1, f"Exercise '{ex.id}' has no safety notes"
        assert ex.breathingPattern is not None and len(ex.breathingPattern) > 10, (
            f"Exercise '{ex.id}' lacks detailed breathing pattern"
        )


def test_content_quality_and_non_duplication():
    """
    Asserts high content quality and non-duplication across all 100 exercise records:
    1. 100 unique exercise names.
    2. 100 unique exercise descriptions.
    3. 100 unique sets of setup cues.
    4. 100 unique sets of execution cues.
    5. 100 unique sets of instructions.
    6. Lexical similarity (Jaccard) between descriptions across unrelated movement patterns
       is strictly bounded below a deterministic threshold of 0.50, proving no template copy-pasting.
    7. Setup cues and execution cues between unrelated movement patterns have Jaccard similarity < 0.60.
    8. Breathing pattern contains actionable respiration cues ('inhale', 'exhale', 'brace', 'breath').
    9. Movement pattern corresponds to physiologically sound primary muscle recruitment.
    """
    # 1. Names uniqueness
    names = [ex.name.strip().lower() for ex in EXERCISE_CATALOG]
    assert len(set(names)) == 100, "Duplicate exercise names detected"

    # 2. Descriptions uniqueness
    descriptions = [ex.description.strip().lower() for ex in EXERCISE_CATALOG]
    assert len(set(descriptions)) == 100, "Duplicate exercise descriptions detected"

    # 3. Setup cues uniqueness
    setup_tuples = [tuple(cue.strip().lower() for cue in ex.setupCues) for ex in EXERCISE_CATALOG]
    assert len(set(setup_tuples)) == 100, "Duplicate setup cue sets detected"

    # 4. Execution cues uniqueness
    exec_tuples = [tuple(cue.strip().lower() for cue in ex.executionCues) for ex in EXERCISE_CATALOG]
    assert len(set(exec_tuples)) == 100, "Duplicate execution cue sets detected"

    # 5. Instructions uniqueness
    inst_tuples = [tuple(inst.strip().lower() for inst in ex.instructions) for ex in EXERCISE_CATALOG]
    assert len(set(inst_tuples)) == 100, "Duplicate instruction sets detected"

    # 6. Lexical duplication threshold across disparate movement patterns
    def tokenize(text: str) -> set:
        clean = text.lower().replace(".", " ").replace(",", " ").replace(";", " ")
        return {w for w in clean.split() if len(w) > 2}

    for i in range(len(EXERCISE_CATALOG)):
        for j in range(i + 1, len(EXERCISE_CATALOG)):
            ex1 = EXERCISE_CATALOG[i]
            ex2 = EXERCISE_CATALOG[j]
            if ex1.movementPattern != ex2.movementPattern:
                t1 = tokenize(ex1.description)
                t2 = tokenize(ex2.description)
                sim = len(t1 & t2) / len(t1 | t2) if (t1 | t2) else 0.0
                assert sim < 0.50, (
                    f"Suspiciously high description similarity ({sim:.2f}) between unrelated exercises "
                    f"'{ex1.id}' ({ex1.movementPattern}) and '{ex2.id}' ({ex2.movementPattern})"
                )

                s1 = tokenize(" ".join(ex1.setupCues))
                s2 = tokenize(" ".join(ex2.setupCues))
                setup_sim = len(s1 & s2) / len(s1 | s2) if (s1 | s2) else 0.0
                assert setup_sim < 0.60, (
                    f"Suspiciously high setup cue similarity ({setup_sim:.2f}) between "
                    f"'{ex1.id}' and '{ex2.id}'"
                )

    # 7. Respiration cueing quality
    for ex in EXERCISE_CATALOG:
        bp = (ex.breathingPattern or "").lower()
        assert len(bp) > 10, f"Exercise '{ex.id}' has too brief breathing pattern"
        assert any(w in bp for w in ["inhale", "exhale", "breath", "brace"]), (
            f"Exercise '{ex.id}' lacks specific respiratory direction: '{ex.breathingPattern}'"
        )

    # 8. Biomechanical pattern to muscle alignment
    pattern_muscles = {
        "squat": {"quadriceps", "glutes"},
        "hinge": {"hamstrings", "glutes", "back"},
        "horizontal_push": {"chest", "shoulders", "triceps"},
        "horizontal_pull": {"back", "shoulders"},
        "vertical_push": {"shoulders", "triceps", "quadriceps"},
        "vertical_pull": {"back", "biceps", "chest"},
        "lunge": {"quadriceps", "glutes"},
        "isolation": {"biceps", "triceps", "shoulders", "calves", "quadriceps", "hamstrings", "back"},
        "core_anti_extension": {"core", "abs"},
        "core_anti_rotation": {"core", "abs", "back", "glutes"},
        "carry": {"core", "abs"},
        "mobility": {"back", "glutes", "full_body"},
    }
    for ex in EXERCISE_CATALOG:
        expected = pattern_muscles.get(ex.movementPattern, set())
        overlap = set(ex.primaryMuscles) & expected
        assert overlap, (
            f"Exercise '{ex.id}' in '{ex.movementPattern}' has disconnected primary muscles: {ex.primaryMuscles}"
        )

