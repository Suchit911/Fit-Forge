from typing import List, Optional, Literal
from pydantic import BaseModel, Field

DifficultyLevel = Literal["beginner", "intermediate", "advanced"]
FitnessGoal = Literal["muscle_gain", "fat_loss", "strength", "endurance", "general_fitness"]
Environment = Literal["gym", "home", "outdoor", "anywhere"]
EquipmentType = Literal[
    "bodyweight",
    "dumbbells",
    "barbell",
    "kettlebell",
    "resistance_bands",
    "cable_machine",
    "smith_machine",
    "leg_press",
    "pull_up_bar",
    "yoga_mat",
    "bench",
    "incline_bench",
    "trap_bar",
    "dip_station",
    "box_platform",
]
MuscleGroup = Literal[
    "chest",
    "shoulders",
    "triceps",
    "biceps",
    "back",
    "quadriceps",
    "hamstrings",
    "glutes",
    "calves",
    "abs",
    "core",
    "full_body",
]


class UserProfileSchema(BaseModel):
    id: str
    name: str
    email: str
    profile_complete: bool = False
    gender: Optional[str] = None
    age: Optional[int] = None
    heightCm: Optional[float] = None
    weightKg: Optional[float] = None
    targetWeightKg: Optional[float] = None
    fitnessLevel: Optional[DifficultyLevel] = None
    primaryGoal: Optional[FitnessGoal] = None
    secondaryGoals: List[FitnessGoal] = []
    environment: Optional[Environment] = None
    availableEquipment: List[EquipmentType] = []
    workoutFrequencyDaysPerWeek: Optional[int] = None
    workoutDurationMinutes: Optional[int] = None
    preferredWorkoutType: Optional[str] = None
    preferredTrainingTime: Optional[str] = None
    dietaryPreference: Optional[str] = None
    targetCalories: Optional[int] = None
    targetProteinGrams: Optional[int] = None
    targetCarbsGrams: Optional[int] = None
    targetFatGrams: Optional[int] = None
    hydrationGoalLiters: Optional[float] = None
    bmi: Optional[float] = None
    bmr: Optional[float] = None
    tdee: Optional[float] = None
    streakDays: int = 0
    totalWorkouts: int = 0
    totalCaloriesBurned: int = 0
    totalPoints: int = 0

    model_config = {"extra": "ignore"}


class UserProfileCreate(BaseModel):
    name: str
    email: Optional[str] = None
    profile_complete: bool = False
    gender: Optional[str] = None
    age: Optional[int] = None
    heightCm: Optional[float] = None
    weightKg: Optional[float] = None
    targetWeightKg: Optional[float] = None
    fitnessLevel: Optional[DifficultyLevel] = None
    primaryGoal: Optional[FitnessGoal] = None
    secondaryGoals: List[FitnessGoal] = []
    environment: Optional[Environment] = None
    availableEquipment: List[EquipmentType] = []
    workoutFrequencyDaysPerWeek: Optional[int] = None
    workoutDurationMinutes: Optional[int] = None
    preferredWorkoutType: Optional[str] = None
    preferredTrainingTime: Optional[str] = None
    dietaryPreference: Optional[str] = None
    targetCalories: Optional[int] = None
    targetProteinGrams: Optional[int] = None
    targetCarbsGrams: Optional[int] = None
    targetFatGrams: Optional[int] = None
    hydrationGoalLiters: Optional[float] = None
    bmi: Optional[float] = None
    bmr: Optional[float] = None
    tdee: Optional[float] = None
    streakDays: int = 0
    totalWorkouts: int = 0
    totalCaloriesBurned: int = 0
    totalPoints: int = 0

    model_config = {"extra": "ignore"}


class UserProfileUpdate(BaseModel):
    name: Optional[str] = None
    email: Optional[str] = None
    profile_complete: Optional[bool] = None
    gender: Optional[str] = None
    age: Optional[int] = None
    heightCm: Optional[float] = None
    weightKg: Optional[float] = None
    targetWeightKg: Optional[float] = None
    fitnessLevel: Optional[DifficultyLevel] = None
    primaryGoal: Optional[FitnessGoal] = None
    secondaryGoals: Optional[List[FitnessGoal]] = None
    environment: Optional[Environment] = None
    availableEquipment: Optional[List[EquipmentType]] = None
    workoutFrequencyDaysPerWeek: Optional[int] = None
    workoutDurationMinutes: Optional[int] = None
    preferredWorkoutType: Optional[str] = None
    preferredTrainingTime: Optional[str] = None
    dietaryPreference: Optional[str] = None
    targetCalories: Optional[int] = None
    targetProteinGrams: Optional[int] = None
    targetCarbsGrams: Optional[int] = None
    targetFatGrams: Optional[int] = None
    hydrationGoalLiters: Optional[float] = None
    bmi: Optional[float] = None
    bmr: Optional[float] = None
    tdee: Optional[float] = None
    streakDays: Optional[int] = None
    totalWorkouts: Optional[int] = None
    totalCaloriesBurned: Optional[int] = None
    totalPoints: Optional[int] = None

    model_config = {"extra": "ignore"}



class PersonalInformationSchema(BaseModel):
    age: int
    heightCm: float
    weightKg: float
    fitnessGoal: str
    activityLevel: str


class FitnessGoalSchema(BaseModel):
    primaryGoal: str
    targetWeightKg: float
    weeklyWorkoutTarget: str
    targetDate: str
    progressPct: float
    kgToGo: float


class PersonalStatsSchema(BaseModel):
    currentWeightKg: float
    weightChangeKg: float
    bodyFatPct: float
    bodyFatChangePct: float
    muscleMassKg: float
    muscleMassChangeKg: float
    bmi: float
    bmiStatus: str


class ProfileHeroStatsSchema(BaseModel):
    name: str
    verified: bool = True
    plan: str = "Pro Plan"
    memberSince: str
    location: str
    quote: str
    streakDays: int
    totalWorkouts: int
    totalCaloriesBurned: int
    totalPoints: int
    rankPct: str
    avatarUrl: str
