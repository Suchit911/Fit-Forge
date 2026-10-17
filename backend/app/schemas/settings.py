from typing import List, Optional, Literal
from pydantic import BaseModel, Field


LanguageOption = Literal["English", "Spanish", "German", "Hindi"]
UnitOption = Literal["Metric (kg, cm)", "Imperial (lbs, in)"]
TimeZoneOption = Literal[
    "(GMT+05:30) Asia/Kolkata",
    "(GMT-05:00) EST (US & Canada)",
    "(GMT+00:00) UTC / London",
]
WeekStartDayOption = Literal["Monday", "Sunday"]
WorkoutDurationOption = Literal[45, 60, 75, 90]

AccentColorOption = Literal[
    "Emerald Green",
    "Ocean Blue",
    "Purple Haze",
    "Sunset Orange",
]
AccentIntensityOption = Literal["Low", "Medium", "High"]
UIDensityOption = Literal["Compact", "Comfortable", "Spacious"]

ProfileVisibilityOption = Literal["Public", "Friends Only", "Private"]
WorkoutDataVisibilityOption = Literal["Only You", "Friends", "Public"]
ProgressPhotosVisibilityOption = Literal["Only You", "Private"]

AICoachPersonalityOption = Literal["Motivational", "Strict & Disciplined", "Scientific"]
AICoachIntensityOption = Literal["Moderate", "High", "Extreme"]
AICoachFocusOption = Literal[
    "Muscle Gain",
    "Strength",
    "Endurance",
    "Fat Loss",
    "General Fitness",
]
WorkoutRecommendationsOption = Literal["Basic", "Standard", "Advanced"]
NutritionRecommendationsOption = Literal["Standard", "Personalized", "Strict Macro-Targeted"]
FormAnalysisInsightsOption = Literal["Summary", "Detailed", "Real-time Telemetry"]


# ---------------------------------------------------------------------------
# General Settings
# ---------------------------------------------------------------------------
class GeneralSettingsSchema(BaseModel):
    language: LanguageOption = "English"
    units: UnitOption = "Metric (kg, cm)"
    timeZone: TimeZoneOption = "(GMT+05:30) Asia/Kolkata"
    weekStartDay: WeekStartDayOption = "Monday"
    defaultWorkoutDurationMin: WorkoutDurationOption = 60

    model_config = {"extra": "forbid"}


class GeneralSettingsUpdate(BaseModel):
    language: Optional[LanguageOption] = None
    units: Optional[UnitOption] = None
    timeZone: Optional[TimeZoneOption] = None
    weekStartDay: Optional[WeekStartDayOption] = None
    defaultWorkoutDurationMin: Optional[WorkoutDurationOption] = None

    model_config = {"extra": "forbid"}


# ---------------------------------------------------------------------------
# Notification Preferences
# ---------------------------------------------------------------------------
class NotificationSettingsSchema(BaseModel):
    workoutReminders: bool = True
    restTimerAlerts: bool = True
    achievementNotifications: bool = True
    nutritionReminders: bool = True
    aiCoachInsights: bool = True
    weeklyProgressReport: bool = True

    model_config = {"extra": "forbid"}


class NotificationSettingsUpdate(BaseModel):
    workoutReminders: Optional[bool] = None
    restTimerAlerts: Optional[bool] = None
    achievementNotifications: Optional[bool] = None
    nutritionReminders: Optional[bool] = None
    aiCoachInsights: Optional[bool] = None
    weeklyProgressReport: Optional[bool] = None

    model_config = {"extra": "forbid"}


# ---------------------------------------------------------------------------
# Appearance Preferences
# ---------------------------------------------------------------------------
class AppearanceSettingsSchema(BaseModel):
    darkMode: bool = True
    accentColor: AccentColorOption = "Emerald Green"
    accentIntensity: AccentIntensityOption = "Medium"
    uiDensity: UIDensityOption = "Comfortable"
    animations: bool = True
    reduceMotion: bool = False

    model_config = {"extra": "forbid"}


class AppearanceSettingsUpdate(BaseModel):
    darkMode: Optional[bool] = None
    accentColor: Optional[AccentColorOption] = None
    accentIntensity: Optional[AccentIntensityOption] = None
    uiDensity: Optional[UIDensityOption] = None
    animations: Optional[bool] = None
    reduceMotion: Optional[bool] = None

    model_config = {"extra": "forbid"}


# ---------------------------------------------------------------------------
# Privacy & Security Settings
# ---------------------------------------------------------------------------
class PrivacySettingsSchema(BaseModel):
    profileVisibility: ProfileVisibilityOption = "Public"
    workoutDataVisibility: WorkoutDataVisibilityOption = "Only You"
    progressPhotosVisibility: ProgressPhotosVisibilityOption = "Only You"
    aiAnalysisData: bool = True
    twoFactorEnabled: bool = True

    model_config = {"extra": "forbid"}


class PrivacySettingsUpdate(BaseModel):
    profileVisibility: Optional[ProfileVisibilityOption] = None
    workoutDataVisibility: Optional[WorkoutDataVisibilityOption] = None
    progressPhotosVisibility: Optional[ProgressPhotosVisibilityOption] = None
    aiAnalysisData: Optional[bool] = None
    twoFactorEnabled: Optional[bool] = None

    model_config = {"extra": "forbid"}


# ---------------------------------------------------------------------------
# AI Coach Settings
# ---------------------------------------------------------------------------
class AICoachSettingsSchema(BaseModel):
    personality: AICoachPersonalityOption = "Motivational"
    intensity: AICoachIntensityOption = "High"
    focus: AICoachFocusOption = "Muscle Gain"
    workoutRecommendations: WorkoutRecommendationsOption = "Advanced"
    nutritionRecommendations: NutritionRecommendationsOption = "Personalized"
    formAnalysisInsights: FormAnalysisInsightsOption = "Detailed"

    model_config = {"extra": "forbid"}


class AICoachSettingsUpdate(BaseModel):
    personality: Optional[AICoachPersonalityOption] = None
    intensity: Optional[AICoachIntensityOption] = None
    focus: Optional[AICoachFocusOption] = None
    workoutRecommendations: Optional[WorkoutRecommendationsOption] = None
    nutritionRecommendations: Optional[NutritionRecommendationsOption] = None
    formAnalysisInsights: Optional[FormAnalysisInsightsOption] = None

    model_config = {"extra": "forbid"}


# ---------------------------------------------------------------------------
# Connected Devices (Integrations)
# Note: External device integrations are not operational in this environment.
# They are represented with isConnected=False and cannot be spoofed as active.
# ---------------------------------------------------------------------------
class ConnectedDeviceSchema(BaseModel):
    id: str
    name: str
    description: str
    isConnected: bool = False
    iconName: str

    model_config = {"extra": "forbid"}


def get_default_devices() -> List[ConnectedDeviceSchema]:
    return [
        ConnectedDeviceSchema(
            id="dev_1",
            name="Apple Watch",
            description="Sync workouts & heart rate",
            isConnected=False,
            iconName="watch",
        ),
        ConnectedDeviceSchema(
            id="dev_2",
            name="Fitbit",
            description="Sync activity & sleep data",
            isConnected=False,
            iconName="activity",
        ),
        ConnectedDeviceSchema(
            id="dev_3",
            name="Google Fit",
            description="Sync health & activity",
            isConnected=False,
            iconName="heart",
        ),
        ConnectedDeviceSchema(
            id="dev_4",
            name="Heart Rate Monitor",
            description="Sync heart rate data",
            isConnected=False,
            iconName="activity",
        ),
        ConnectedDeviceSchema(
            id="dev_5",
            name="Smart Scale",
            description="Track weight & body metrics",
            isConnected=False,
            iconName="scale",
        ),
    ]


# ---------------------------------------------------------------------------
# Root User Settings Schemas
# ---------------------------------------------------------------------------
class UserSettingsSchema(BaseModel):
    userId: str
    general: GeneralSettingsSchema = Field(default_factory=GeneralSettingsSchema)
    notifications: NotificationSettingsSchema = Field(default_factory=NotificationSettingsSchema)
    appearance: AppearanceSettingsSchema = Field(default_factory=AppearanceSettingsSchema)
    privacy: PrivacySettingsSchema = Field(default_factory=PrivacySettingsSchema)
    devices: List[ConnectedDeviceSchema] = Field(default_factory=get_default_devices)
    aiCoach: AICoachSettingsSchema = Field(default_factory=AICoachSettingsSchema)
    updatedAt: Optional[str] = None
    persisted: bool = False

    model_config = {"extra": "ignore"}


class UserSettingsUpdateSchema(BaseModel):
    general: Optional[GeneralSettingsUpdate] = None
    notifications: Optional[NotificationSettingsUpdate] = None
    appearance: Optional[AppearanceSettingsUpdate] = None
    privacy: Optional[PrivacySettingsUpdate] = None
    aiCoach: Optional[AICoachSettingsUpdate] = None

    model_config = {"extra": "forbid"}
