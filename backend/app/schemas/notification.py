from typing import List, Optional, Literal, Dict
from pydantic import BaseModel


class NotificationItemSchema(BaseModel):
    id: str
    type: Optional[str] = None
    category: Literal["Workout", "AI Coach", "Nutrition", "Achievement", "Progress", "Recovery", "System"]
    title: str
    message: str
    createdAt: Optional[str] = None
    timestamp: str
    dateGroup: Literal["Today", "Yesterday", "Earlier"]
    read: bool = False
    readAt: Optional[str] = None
    important: bool = False
    iconName: str
    actionLabel: Optional[str] = None
    actionRoute: Optional[str] = None
    sourceId: Optional[str] = None


class NotificationCategorySummarySchema(BaseModel):
    category: str
    count: int
    percentage: float
    color: str


class ImportantUpdateItemSchema(BaseModel):
    id: str
    category: str
    title: str
    description: str
    timeAgo: str
    iconName: str


class NotificationsDashboardDataSchema(BaseModel):
    unreadCount: int
    todayCount: int
    weekCount: int
    importantCount: int
    notifications: List[NotificationItemSchema] = []
    insights: List[NotificationCategorySummarySchema] = []
    importantUpdates: List[ImportantUpdateItemSchema] = []
    preferences: Dict[str, bool] = {}


class NotificationUnreadCountResponse(BaseModel):
    unreadCount: int


class NotificationMarkAllReadResponse(BaseModel):
    unreadCount: int
    markedCount: int

