import re
from typing import Optional, List, Literal
from pydantic import BaseModel, Field, field_validator


# Controlled types for Coach domain
CoachSender = Literal["user", "assistant"]
CoachTone = Literal["encouraging", "strict", "scientific"]
CoachFocus = Literal["hypertrophy", "fat_loss", "strength", "recovery"]


class CoachSettingsSchema(BaseModel):
    """User coaching personality and focus preferences."""
    tone: CoachTone = Field(default="encouraging", description="Coaching tone: encouraging, strict, or scientific")
    focus: CoachFocus = Field(default="hypertrophy", description="Primary AI focus: hypertrophy, fat_loss, strength, or recovery")


class CoachMessageSchema(BaseModel):
    """Authoritative representation of a single chat message."""
    id: str
    conversationId: str
    sender: CoachSender
    text: str
    createdAt: str


class CoachConversationSchema(BaseModel):
    """Authoritative representation of a chat conversation thread."""
    id: str
    title: str
    createdAt: str
    updatedAt: str
    previewText: str = ""
    messageCount: int = 0


class ConversationSummarySchema(BaseModel):
    """Summary representation of a conversation thread for list displays."""
    id: str
    title: str
    createdAt: str
    updatedAt: str
    previewText: str = ""
    messageCount: int = 0
    dateGroup: Optional[str] = None
    timestamp: Optional[str] = None


class CreateConversationRequest(BaseModel):
    """Request payload for explicitly creating a new conversation thread."""
    title: Optional[str] = Field(default=None, max_length=100)
    initialMessage: Optional[str] = Field(default=None, max_length=1000)

    @field_validator("initialMessage")
    @classmethod
    def validate_initial_message(cls, v: Optional[str]) -> Optional[str]:
        if v is not None:
            v_clean = v.strip()
            if not v_clean:
                return None
            if len(v_clean) > 1000:
                raise ValueError("Initial message text cannot exceed 1000 characters.")
            return v_clean
        return None


class SendCoachMessageRequest(BaseModel):
    """Request payload for sending a user message to the AI Coach."""
    conversation_id: Optional[str] = Field(
        default=None,
        alias="conversationId",
        description="Optional target conversation ID. A new thread is created if omitted."
    )
    message: str = Field(..., description="User message text (1-1000 characters)")

    model_config = {"populate_by_name": True}

    @property
    def conversationId(self) -> Optional[str]:
        return self.conversation_id

    @field_validator("message")
    @classmethod
    def validate_message(cls, v: str) -> str:
        if not isinstance(v, str):
            raise ValueError("Message must be a string.")
        stripped = v.strip()
        if not stripped:
            raise ValueError("Message text cannot be empty or whitespace-only.")
        if len(stripped) > 1000:
            raise ValueError("Message text cannot exceed 1000 characters.")
        return stripped

    @field_validator("conversation_id")
    @classmethod
    def validate_conversation_id(cls, v: Optional[str]) -> Optional[str]:
        if v is not None:
            v_clean = v.strip()
            if not v_clean:
                return None
            if len(v_clean) > 100:
                raise ValueError("Conversation ID cannot exceed 100 characters.")
            if not re.match(r"^[a-zA-Z0-9_\-]+$", v_clean):
                raise ValueError("Conversation ID contains invalid characters.")
            return v_clean
        return None


class CoachMessageResponse(BaseModel):
    """Response payload returning user message confirmation and assistant reply."""
    conversationId: str
    userMessage: CoachMessageSchema
    assistantMessage: CoachMessageSchema


# =============================================================================
# BOUNDED USER CONTEXT SCHEMAS
# =============================================================================

class CoachProfileContext(BaseModel):
    name: Optional[str] = None
    goal: Optional[str] = None
    experienceLevel: Optional[str] = None
    targetCalories: Optional[int] = None
    targetProteinGrams: Optional[float] = None
    targetWaterLiters: Optional[float] = None


class CoachRecentActivityContext(BaseModel):
    activeStreak: int = 0
    workoutsCompletedThisWeek: int = 0
    totalRecentVolumeKg: float = 0.0
    latestWorkoutTitle: Optional[str] = None
    recentPRs: List[str] = []


class CoachNutritionContext(BaseModel):
    isLoggedToday: bool = False
    consumedCalories: Optional[int] = None
    targetCalories: int = 2400
    consumedProteinGrams: Optional[float] = None
    targetProteinGrams: float = 160.0
    consumedWaterLiters: Optional[float] = None
    targetWaterLiters: float = 3.0


class CoachAchievementsContext(BaseModel):
    totalPoints: int = 0
    level: int = 1
    levelTitle: str = "Novice Lifter"
    unlockedCount: int = 0
    latestBadge: Optional[str] = None


class CoachContext(BaseModel):
    """Bounded, deterministic user-context snapshot provided to the LLM."""
    profile: CoachProfileContext = Field(default_factory=CoachProfileContext)
    preferences: CoachSettingsSchema = Field(default_factory=CoachSettingsSchema)
    recentActivity: CoachRecentActivityContext = Field(default_factory=CoachRecentActivityContext)
    todayNutrition: CoachNutritionContext = Field(default_factory=CoachNutritionContext)
    achievements: CoachAchievementsContext = Field(default_factory=CoachAchievementsContext)
    profileAvailable: bool = True
    recentActivityAvailable: bool = True
    todayNutritionAvailable: bool = True
    achievementsAvailable: bool = True
    errors: List[str] = []
