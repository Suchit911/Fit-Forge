from typing import List, Optional, Literal, Dict
from pydantic import BaseModel, Field
from .user import DifficultyLevel, Environment, EquipmentType, MuscleGroup


class ExerciseSchema(BaseModel):
    id: str
    name: str
    description: str
    primaryMuscles: List[MuscleGroup]
    secondaryMuscles: List[MuscleGroup] = []
    equipment: List[EquipmentType] = []
    difficulty: DifficultyLevel = "intermediate"
    category: Literal["strength", "hypertrophy", "endurance", "mobility", "activation_warmup", "cardio", "custom"] = "strength"
    instructions: List[str] = []
    commonMistakes: List[str] = []
    safetyNotes: List[str] = []
    supportedFormAnalysis: bool = False
    supportedCameraMode: Optional[Literal["front", "side"]] = None
    imageUrl: Optional[str] = None
    isCustom: bool = False

    model_config = {"extra": "ignore"}


class WorkoutSetSchema(BaseModel):
    setNumber: int
    targetReps: int
    targetWeightKg: Optional[float] = None
    isCompleted: bool = False
    actualReps: Optional[int] = None
    actualWeightKg: Optional[float] = None
    rpe: Optional[float] = None

    model_config = {"extra": "ignore"}


class WorkoutExerciseSchema(BaseModel):
    id: str
    exerciseId: str
    exercise: ExerciseSchema
    sets: List[WorkoutSetSchema] = []
    restSecondsBetweenSets: int = 90
    notes: Optional[str] = None

    model_config = {"extra": "ignore"}


class WorkoutSchema(BaseModel):
    id: str
    title: str
    description: str
    targetEnvironment: Environment = "gym"
    estimatedDurationMinutes: int = 45
    difficulty: DifficultyLevel = "intermediate"
    targetMuscles: List[MuscleGroup] = []
    exercises: List[WorkoutExerciseSchema] = []
    imageUrl: Optional[str] = None
    isSystem: bool = True

    model_config = {"extra": "ignore"}


class WorkoutSummaryItem(BaseModel):
    id: str
    title: str
    description: str
    targetEnvironment: Environment = "gym"
    estimatedDurationMinutes: int = 45
    difficulty: DifficultyLevel = "intermediate"
    targetMuscles: List[MuscleGroup] = []
    exerciseCount: int = 0
    imageUrl: Optional[str] = None

    model_config = {"extra": "ignore"}


class ActiveWorkoutStateSchema(BaseModel):
    workoutId: str
    currentExerciseIndex: int = 0
    currentSetIndex: int = 0
    elapsedSeconds: int = 0
    isPaused: bool = False
    completedSets: Dict[str, List[WorkoutSetSchema]] = {}
    isFinished: bool = False

    model_config = {"extra": "ignore"}


class WorkoutSessionCreate(BaseModel):
    workoutId: Optional[str] = None
    workoutTitle: Optional[str] = None
    totalSetsCount: Optional[int] = None
    notes: Optional[str] = None
    programId: Optional[str] = None
    planId: Optional[str] = None
    weekNumber: Optional[int] = None
    dayNumber: Optional[int] = None

    model_config = {"extra": "ignore"}


class WorkoutSetRecord(BaseModel):
    exerciseId: str
    setNumber: int
    actualReps: int
    actualWeightKg: float
    rpe: Optional[float] = None
    isCompleted: bool = True

    model_config = {"extra": "ignore"}


class WorkoutSessionUpdate(BaseModel):
    currentExerciseIndex: Optional[int] = None
    currentSetIndex: Optional[int] = None
    elapsedSeconds: Optional[int] = None
    isPaused: Optional[bool] = None
    recordedSet: Optional[WorkoutSetRecord] = None
    notes: Optional[str] = None

    model_config = {"extra": "ignore"}


class WorkoutSessionComplete(BaseModel):
    durationSeconds: Optional[int] = None
    notes: Optional[str] = None

    model_config = {"extra": "ignore"}


class WorkoutSessionResponse(BaseModel):
    id: str
    userId: str
    workoutId: str
    workoutTitle: str
    status: Literal["in_progress", "completed", "cancelled"] = "in_progress"
    startedAt: str
    completedAt: Optional[str] = None
    durationSeconds: int = 0
    currentExerciseIndex: int = 0
    currentSetIndex: int = 0
    isPaused: bool = False
    completedSets: Dict[str, List[WorkoutSetSchema]] = {}
    completedSetsCount: int = 0
    totalSetsCount: int = 0
    totalVolumeKg: float = 0.0
    caloriesBurned: int = 0
    notes: Optional[str] = None
    programId: Optional[str] = None
    planId: Optional[str] = None
    weekNumber: Optional[int] = None
    dayNumber: Optional[int] = None

    model_config = {"extra": "ignore"}

