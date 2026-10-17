from typing import List, Optional, Literal, Dict
from pydantic import BaseModel, Field

ProgressPeriod = Literal["7d", "30d", "90d", "all"]


class PeriodComparison(BaseModel):
    workoutsChangePct: str = "0%"
    volumeChangePct: str = "0%"
    caloriesChangePct: str = "0%"
    durationChangePct: str = "0%"

    model_config = {"extra": "ignore"}


class ProgressSummaryResponse(BaseModel):
    totalWorkouts: int = 0
    totalVolumeKg: float = 0.0
    totalDurationMinutes: int = 0
    totalCaloriesBurned: int = 0
    avgWorkoutDurationMinutes: int = 0
    currentStreakDays: int = 0
    weeklyConsistencyDays: int = 0
    comparison: Optional[PeriodComparison] = None

    model_config = {"extra": "ignore"}


class StrengthProgressPointSchema(BaseModel):
    date: str
    upperBodyKg: float = 0.0
    lowerBodyKg: float = 0.0
    totalVolumeKg: float = 0.0

    model_config = {"extra": "ignore"}


class ExerciseProgressionPoint(BaseModel):
    date: str
    sessionId: str
    reps: int
    weightKg: float
    volumeKg: float
    estimated1RM: float

    model_config = {"extra": "ignore"}


class ExerciseProgressionResponse(BaseModel):
    exerciseId: str
    exerciseName: str
    prWeightKg: float = 0.0
    prReps: int = 0
    prDate: Optional[str] = None
    bestEstimated1RM: float = 0.0
    totalSessionsCompleted: int = 0
    history: List[ExerciseProgressionPoint] = []

    model_config = {"extra": "ignore"}


class ProgressKpiItemSchema(BaseModel):
    id: str
    title: str
    value: str
    changePct: str
    trendData: List[float] = []
    color: str

    model_config = {"extra": "ignore"}


class BodyCompositionStatsSchema(BaseModel):
    dateCompare: str = ""
    weightKg: float = 0.0
    weightChangeKg: float = 0.0
    bodyFatPct: float = 0.0
    bodyFatChangePct: float = 0.0
    muscleMassKg: float = 0.0
    muscleMassChangeKg: float = 0.0
    bmi: float = 0.0
    bmiChange: float = 0.0
    goalProgressPct: float = 0.0
    goalKgToGo: float = 0.0

    model_config = {"extra": "ignore"}


class MuscleGroupProgressItemSchema(BaseModel):
    name: str
    changePct: str = "0%"
    status: Literal["Excellent", "Good", "Needs Work"] = "Good"

    model_config = {"extra": "ignore"}


class PerformanceTrendItemSchema(BaseModel):
    name: str
    value: str
    status: str
    trendData: List[float] = []
    iconName: str

    model_config = {"extra": "ignore"}


class PersonalRecordItemSchema(BaseModel):
    id: str
    exerciseName: str
    category: str
    date: str
    value: str
    improvement: str

    model_config = {"extra": "ignore"}


class RecentWorkoutItemSchema(BaseModel):
    id: str
    title: str
    date: str
    durationMin: int
    volumeKg: float
    caloriesKcal: int
    scorePct: int

    model_config = {"extra": "ignore"}


class ProgressPhotoItemSchema(BaseModel):
    id: str
    date: str
    imageUrl: str

    model_config = {"extra": "ignore"}


class ProgressDashboardResponse(BaseModel):
    kpis: List[ProgressKpiItemSchema] = []
    strengthProgress: List[StrengthProgressPointSchema] = []
    bodyComposition: BodyCompositionStatsSchema = BodyCompositionStatsSchema()
    muscleGroupProgress: List[MuscleGroupProgressItemSchema] = []
    performanceTrends: List[PerformanceTrendItemSchema] = []
    personalRecords: List[PersonalRecordItemSchema] = []
    recentWorkouts: List[RecentWorkoutItemSchema] = []
    progressPhotos: List[ProgressPhotoItemSchema] = []

    model_config = {"extra": "ignore"}


# Backward compatibility aliases
ProgressSummarySchema = ProgressSummaryResponse
StrengthPRSchema = PersonalRecordItemSchema
