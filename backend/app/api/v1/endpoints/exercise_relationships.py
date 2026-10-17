"""
Deterministic Exercise Relationship & Corrective Guidance Endpoints (Phase 9B.8.3).

Exposes minimal, read-only endpoints under `/api/v1/exercises/relationships/...`.
Zero CRUD, zero user writes, zero Firestore persistence, zero Gemini/LLM dependency.
"""

from typing import List
from fastapi import APIRouter, Depends, HTTPException, status
from backend.app.schemas.exercise import (
    ExerciseRelationshipNode,
    ExerciseRelationshipsResponse,
    CatalogGraphStatistics,
)
from backend.app.services.exercise_relationship_service import (
    ExerciseRelationshipService,
    get_exercise_relationship_service,
)

router = APIRouter()


# 1. Static Route: Topological Graph Statistics (registered FIRST before parameterized paths)
@router.get(
    "/stats",
    response_model=CatalogGraphStatistics,
    summary="Get 100-exercise relationship graph topological statistics",
    description=(
        "Returns deterministic graph metrics including total edges, average degree, "
        "relationship type distribution, orphan count (under strict degree 0 in/out definition), "
        "and corrective mapping counts."
    ),
)
async def get_graph_statistics(
    service: ExerciseRelationshipService = Depends(get_exercise_relationship_service),
) -> CatalogGraphStatistics:
    return service.get_graph_statistics()


# 2. Specific Route: Corrective Exercises for an Exercise & Technique Issue / Heuristic Name
@router.get(
    "/{exercise_id}/correctives/{issue_id}",
    response_model=List[ExerciseRelationshipNode],
    summary="Get corrective exercises for an observed form technique issue",
    description=(
        "Returns deterministic candidate exercises from the catalog addressing a specific "
        "observable technique issue. Supports lookup by normalized issue ID (e.g. 'insufficient_depth') "
        "or Phase 9B.2 heuristic name (e.g. 'squat_depth')."
    ),
)
async def get_corrective_exercises(
    exercise_id: str,
    issue_id: str,
    service: ExerciseRelationshipService = Depends(get_exercise_relationship_service),
) -> List[ExerciseRelationshipNode]:
    try:
        return service.get_corrective_exercises(exercise_id, issue_id)
    except KeyError as exc:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=str(exc).strip("'\""),
        )


# 3. Generic Route: Categorized and Deduplicated Relationships for an Exercise
@router.get(
    "/{exercise_id}",
    response_model=ExerciseRelationshipsResponse,
    summary="Get categorized and deduplicated relationships for an exercise",
    description=(
        "Retrieves progressions, regressions, substitutions, complements, and correctives "
        "for an exercise, alongside deduplicated candidates with deterministic precedence ranking."
    ),
)
async def get_exercise_relationships(
    exercise_id: str,
    service: ExerciseRelationshipService = Depends(get_exercise_relationship_service),
) -> ExerciseRelationshipsResponse:
    try:
        return service.get_related_exercises(exercise_id)
    except KeyError as exc:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=str(exc).strip("'\""),
        )
