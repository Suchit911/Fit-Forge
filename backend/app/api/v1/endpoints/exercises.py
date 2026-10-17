from typing import List, Optional, Union
from fastapi import APIRouter, Depends, HTTPException, Query, status
from ....schemas.workout import ExerciseSchema
from ....schemas.exercise import ExerciseKnowledgeSchema
from ....schemas.user import MuscleGroup, EquipmentType, DifficultyLevel
from ....repositories.exercise_repository import ExerciseRepository, get_exercise_repository

router = APIRouter()


@router.get("", response_model=List[ExerciseKnowledgeSchema], summary="List exercises with optional filtering")
async def list_exercises(
    muscle: Optional[MuscleGroup] = Query(None, description="Filter by primary or secondary muscle group"),
    equipment: Optional[EquipmentType] = Query(None, description="Filter by required equipment"),
    difficulty: Optional[DifficultyLevel] = Query(None, description="Filter by difficulty level"),
    category: Optional[str] = Query(None, description="Filter by category (strength, hypertrophy, etc.)"),
    search: Optional[str] = Query(None, description="Search term for name or description"),
    repo: ExerciseRepository = Depends(get_exercise_repository),
):
    """
    Returns exercise library items matching the provided filters.
    Accessible without authentication for public library browsing.
    """
    return repo.list_exercises(
        muscle=muscle,
        equipment=equipment,
        difficulty=difficulty,
        category=category,
        search=search,
    )


@router.get("/{exercise_id}", response_model=ExerciseKnowledgeSchema, summary="Get exercise details by ID")
async def get_exercise(
    exercise_id: str,
    repo: ExerciseRepository = Depends(get_exercise_repository),
):
    """
    Retrieves detailed instructions, cues, and muscle involvement for a single exercise.
    Returns 404 if the exercise does not exist.
    """
    exercise = repo.get_by_id(exercise_id)
    if not exercise:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Exercise with ID '{exercise_id}' was not found in the library.",
        )
    return exercise
