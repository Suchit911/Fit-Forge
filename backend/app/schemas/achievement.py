from typing import List, Optional
from pydantic import BaseModel, Field


class AchievementDefinitionSchema(BaseModel):
    id: str
    title: str
    description: str
    category: str
    metricType: str
    threshold: float
    points: int
    iconName: str
    color: str
    tier: str = "bronze"


class UserAchievementSchema(BaseModel):
    id: str
    userId: str
    achievementId: str
    isUnlocked: bool = False
    unlockedAt: Optional[str] = None
    currentValue: float = 0.0
    targetValue: float = 0.0
    progressPercentage: float = 0.0
    isNew: bool = False
    isCustom: bool = False
    customTitle: Optional[str] = None
    customDescription: Optional[str] = None
    customCategory: Optional[str] = None
    points: int = 0
    updatedAt: str


class AchievementKpiItemSchema(BaseModel):
    id: str
    title: str
    value: str
    supportingText: str
    iconName: str
    color: str


class RecentAchievementBadgeSchema(BaseModel):
    id: str
    title: str
    description: str
    timeAgo: str
    isNew: bool = False
    iconName: str
    color: str


class NextMilestoneSchema(BaseModel):
    level: int
    title: str
    description: str
    currentPts: int
    targetPts: int
    ptsToGo: int
    currentLevel: int = 1


class AchievementsProgressDataSchema(BaseModel):
    overallPct: int
    achievedCount: int
    inProgressCount: int
    lockedCount: int
    nextMilestone: NextMilestoneSchema


class AchievementCategoryItemSchema(BaseModel):
    id: str
    title: str
    current: int
    total: int
    pct: int
    iconName: str
    color: str


class CurrentChallengeItemSchema(BaseModel):
    id: str
    title: str
    description: str
    current: float
    target: float
    unit: Optional[str] = None
    daysLeft: int
    iconName: str
    color: str


class LeaderboardUserSchema(BaseModel):
    rank: Optional[int] = None
    name: str
    points: int
    pointsStr: str
    isCurrentUser: bool = False


class AchievementsDashboardDataSchema(BaseModel):
    kpis: List[AchievementKpiItemSchema] = []
    recentAchievements: List[RecentAchievementBadgeSchema] = []
    progressSummary: AchievementsProgressDataSchema
    categories: List[AchievementCategoryItemSchema] = []
    currentChallenges: List[CurrentChallengeItemSchema] = []
    leaderboard: List[LeaderboardUserSchema] = []


class CustomAchievementCreateSchema(BaseModel):
    name: str = Field(..., min_length=2, max_length=100, description="Title of custom achievement")
    description: str = Field(default="", max_length=250, description="Description or note for custom achievement")
    category: str = Field(default="Workout Mastery", description="Category for milestone")


class AchievementDetailSchema(BaseModel):
    id: str
    title: str
    description: str
    category: str
    iconName: str
    color: str
    points: int
    currentValue: float
    targetValue: float
    progressPercentage: float
    isUnlocked: bool
    unlockedAt: Optional[str] = None
    isNew: bool = False
    isCustom: bool = False


# Backwards compatibility alias
AchievementSchema = AchievementDetailSchema
