"""
Authoritative 100-Exercise Knowledge Catalog (Phase 9B.8.2).

Exposes:
- RAW_CATALOG_DATA: List[Dict[str, Any]] (100 raw dictionary exercise records)
- EXERCISE_CATALOG: List[ExerciseKnowledgeSchema] (100 validated Pydantic domain models)
- CATALOG_BY_ID: Dict[str, ExerciseKnowledgeSchema] (O(1) canonical ID lookup)
- CATALOG_BY_MOVEMENT_PATTERN: Dict[str, List[ExerciseKnowledgeSchema]] (pattern lookup)
- CATALOG_BY_PRIMARY_MUSCLE: Dict[str, List[ExerciseKnowledgeSchema]] (muscle lookup)
- CATALOG_CV_EXERCISES: Dict[str, ExerciseKnowledgeSchema] (the 5 CV-supported records)
- Query helper functions: get_catalog_exercise(), get_catalog_cv_exercise()
"""

from typing import List, Dict, Any, Optional
from backend.app.schemas.exercise import ExerciseKnowledgeSchema, CVExerciseKey
from .catalog import (
    RAW_CATALOG_DATA,
    CATALOG_EXERCISES as EXERCISE_CATALOG,
    CATALOG_BY_ID,
    CATALOG_BY_MOVEMENT_PATTERN,
    CATALOG_BY_PRIMARY_MUSCLE,
    CATALOG_CV_EXERCISES,
    get_catalog_exercise,
    get_catalog_cv_exercise,
)

__all__ = [
    "RAW_CATALOG_DATA",
    "EXERCISE_CATALOG",
    "CATALOG_BY_ID",
    "CATALOG_BY_MOVEMENT_PATTERN",
    "CATALOG_BY_PRIMARY_MUSCLE",
    "CATALOG_CV_EXERCISES",
    "get_catalog_exercise",
    "get_catalog_cv_exercise",
]
