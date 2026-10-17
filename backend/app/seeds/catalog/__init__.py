"""
Authoritative Exercise Knowledge Catalog (Phase 9B.8.2).
Aggregates, validates, and indexes all 100 curated exercises across 10 core movement patterns.
"""

from typing import List, Dict, Any, Optional
from backend.app.schemas.exercise import (
    ExerciseKnowledgeSchema,
    CANONICAL_CV_EXERCISES,
    CV_KEY_TO_CATALOG_ID,
    CVExerciseKey,
)

from .squat import SQUAT_EXERCISES
from .hinge import HINGE_EXERCISES
from .horizontal_push import HORIZONTAL_PUSH_EXERCISES
from .horizontal_pull import HORIZONTAL_PULL_EXERCISES
from .vertical_push import VERTICAL_PUSH_EXERCISES
from .vertical_pull import VERTICAL_PULL_EXERCISES
from .lunge import LUNGE_EXERCISES
from .arms import ARM_EXERCISES
from .core import CORE_EXERCISES
from .mobility import MOBILITY_EXERCISES

# Raw dictionary catalog aggregated in deterministic order
RAW_CATALOG_DATA: List[Dict[str, Any]] = (
    SQUAT_EXERCISES             # 12
    + HINGE_EXERCISES           # 12
    + HORIZONTAL_PUSH_EXERCISES # 12
    + HORIZONTAL_PULL_EXERCISES # 11
    + VERTICAL_PUSH_EXERCISES   # 10
    + VERTICAL_PULL_EXERCISES   # 10
    + LUNGE_EXERCISES           # 9
    + ARM_EXERCISES             # 10
    + CORE_EXERCISES            # 10
    + MOBILITY_EXERCISES        # 4
)

# Validate all items through ExerciseKnowledgeSchema
CATALOG_EXERCISES: List[ExerciseKnowledgeSchema] = [
    ExerciseKnowledgeSchema(**item) for item in RAW_CATALOG_DATA
]

# Fast indexed lookups
CATALOG_BY_ID: Dict[str, ExerciseKnowledgeSchema] = {
    ex.id: ex for ex in CATALOG_EXERCISES
}

CATALOG_BY_MOVEMENT_PATTERN: Dict[str, List[ExerciseKnowledgeSchema]] = {}
CATALOG_BY_PRIMARY_MUSCLE: Dict[str, List[ExerciseKnowledgeSchema]] = {}

for ex in CATALOG_EXERCISES:
    # Index by movement pattern
    pat = ex.movementPattern
    CATALOG_BY_MOVEMENT_PATTERN.setdefault(pat, []).append(ex)

    # Index by primary muscles
    for muscle in ex.primaryMuscles:
        CATALOG_BY_PRIMARY_MUSCLE.setdefault(muscle, []).append(ex)

# Exactly 5 CV supported exercises
CATALOG_CV_EXERCISES: Dict[CVExerciseKey, ExerciseKnowledgeSchema] = {
    cv_key: CATALOG_BY_ID[catalog_id]
    for catalog_id, cv_key in CANONICAL_CV_EXERCISES.items()
    if catalog_id in CATALOG_BY_ID
}


def get_catalog_exercise(exercise_id: str) -> Optional[ExerciseKnowledgeSchema]:
    """Retrieve an exercise from the catalog by its canonical ID."""
    return CATALOG_BY_ID.get(exercise_id)


def get_catalog_cv_exercise(cv_key: CVExerciseKey) -> Optional[ExerciseKnowledgeSchema]:
    """Retrieve an exercise by its CV engine key."""
    return CATALOG_CV_EXERCISES.get(cv_key)


# Module-level referential integrity verification
assert len(CATALOG_EXERCISES) == 100, f"Expected exactly 100 exercises, found {len(CATALOG_EXERCISES)}"
assert len(CATALOG_BY_ID) == 100, "Duplicate exercise IDs detected in catalog"

# Validate all relationship pointers resolve cleanly
for ex in CATALOG_EXERCISES:
    for rel_type, targets in [
        ("progressions", ex.progressions),
        ("regressions", ex.regressions),
        ("substitutions", ex.substitutions),
        ("complementaryExercises", ex.complementaryExercises),
    ]:
        for target_id in targets:
            assert target_id in CATALOG_BY_ID, (
                f"Referential integrity failure: Exercise '{ex.id}' references non-existent "
                f"target '{target_id}' in '{rel_type}'."
            )
            assert target_id != ex.id, (
                f"Self-reference failure: Exercise '{ex.id}' references itself in '{rel_type}'."
            )

# Validate CV coverage separation
cv_supported = [ex for ex in CATALOG_EXERCISES if ex.supportedFormAnalysis]
assert len(cv_supported) == 5, f"Expected exactly 5 CV-supported exercises, found {len(cv_supported)}"
assert set(ex.id for ex in cv_supported) == set(CANONICAL_CV_EXERCISES.keys()), (
    f"CV-supported exercises do not match CANONICAL_CV_EXERCISES: {[e.id for e in cv_supported]}"
)
