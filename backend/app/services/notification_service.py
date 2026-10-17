from datetime import datetime, timezone, timedelta
from typing import Optional, List, Dict, Any, Tuple
from ..repositories.notification_repository import NotificationRepository, get_notification_repository
from ..schemas.notification import (
    NotificationItemSchema,
    NotificationCategorySummarySchema,
    ImportantUpdateItemSchema,
    NotificationsDashboardDataSchema,
)
from ..utils.logger import logger

CATEGORY_COLORS = {
    "Workout": "#10b981",
    "Nutrition": "#06b6d4",
    "Achievement": "#f59e0b",
    "Progress": "#3b82f6",
    "AI Coach": "#a855f7",
    "System": "#64748b",
    "Recovery": "#6366f1",
}

DEFAULT_PREFERENCES = {
    "workoutReminders": True,
    "achievementAlerts": True,
    "nutritionReminders": True,
    "aiCoachInsights": True,
    "progressReports": True,
    "marketingPromotions": False,
}


def parse_iso_datetime(iso_str: Optional[str]) -> Optional[datetime]:
    if not iso_str:
        return None
    try:
        dt = datetime.fromisoformat(iso_str.replace("Z", "+00:00"))
        if dt.tzinfo is None:
            dt = dt.replace(tzinfo=timezone.utc)
        return dt.astimezone(timezone.utc)
    except Exception:
        return None


def derive_date_group_and_timestamp(created_at_iso: Optional[str]) -> Tuple[str, str]:
    """
    Derives (dateGroup, timestamp) from authoritative createdAt timestamp.
    dateGroup: 'Today', 'Yesterday', or 'Earlier'
    timestamp: human-readable display string (e.g. '2:45 PM', 'Yesterday, 8:30 PM', 'May 10')
    """
    dt = parse_iso_datetime(created_at_iso)
    if not dt:
        return "Earlier", "Recently"

    now = datetime.now(timezone.utc)
    today_start = now.replace(hour=0, minute=0, second=0, microsecond=0)
    yesterday_start = today_start - timedelta(days=1)

    time_str = dt.strftime("%I:%M %p").lstrip("0")

    if dt >= today_start:
        return "Today", time_str
    elif dt >= yesterday_start:
        return "Yesterday", f"Yesterday, {time_str}"
    else:
        # e.g. 'May 10' or 'May 10, 2026'
        date_fmt = "%b %d" if dt.year == now.year else "%b %d, %Y"
        return "Earlier", dt.strftime(date_fmt)


def derive_time_ago(created_at_iso: Optional[str]) -> str:
    """Derives compact relative time string (e.g., '1h ago', '3d ago')."""
    dt = parse_iso_datetime(created_at_iso)
    if not dt:
        return "Recently"
    now = datetime.now(timezone.utc)
    diff = now - dt
    total_seconds = int(diff.total_seconds())

    if total_seconds < 60:
        return "Just now"
    elif total_seconds < 3600:
        return f"{total_seconds // 60}m ago"
    elif total_seconds < 86400:
        return f"{total_seconds // 3600}h ago"
    elif total_seconds < 604800:
        return f"{total_seconds // 86400}d ago"
    else:
        return f"{total_seconds // 604800}w ago"


class NotificationService:
    """
    Domain service for managing in-app notifications, deriving display projections,
    aggregating dashboard KPIs, and handling event-driven notification generation.
    """

    def __init__(self, repo: Optional[NotificationRepository] = None):
        self._repo = repo

    @property
    def repo(self) -> NotificationRepository:
        return self._repo or get_notification_repository()

    # =========================================================================
    # EVENT GENERATION METHODS
    # =========================================================================

    def create_achievement_notification(self, uid: str, achievement_def: Any) -> Optional[Dict[str, Any]]:
        """
        Creates an achievement unlock notification.
        Deterministic ID: notif_ach_{achievement_id}
        """
        doc_id = f"notif_ach_{achievement_def.id}"
        points = getattr(achievement_def, "points", 100)
        tier = getattr(achievement_def, "tier", "bronze")
        important = tier in ["gold", "platinum", "diamond"] or points >= 1000

        data = {
            "id": doc_id,
            "type": "achievement_unlocked",
            "category": "Achievement",
            "title": "New achievement unlocked!",
            "message": f"You earned the {achievement_def.title} badge (+{points} pts).",
            "createdAt": datetime.now(timezone.utc).isoformat(),
            "read": False,
            "readAt": None,
            "important": important,
            "iconName": "trophy",
            "actionLabel": "View Achievement >",
            "actionRoute": "/achievements",
            "sourceId": achievement_def.id,
        }

        try:
            created, was_new = self.repo.create_or_ignore(uid, data)
            if was_new:
                self.repo.prune_user_notifications(uid, max_keep=100, newly_created_id=doc_id)
            return created
        except Exception as e:
            logger.warning(f"Failed to create achievement notification {doc_id} for user {uid}: {e}")
            return None

    def create_workout_completed_notification(
        self, uid: str, session_id: str, workout_title: str, volume_kg: float
    ) -> Optional[Dict[str, Any]]:
        """
        Creates a workout completed notification.
        Deterministic ID: notif_wkt_{session_id}
        """
        doc_id = f"notif_wkt_{session_id}"
        vol_str = f"{volume_kg:,.0f} kg" if volume_kg > 0 else "N/A"

        data = {
            "id": doc_id,
            "type": "workout_completed",
            "category": "Workout",
            "title": "Workout completed!",
            "message": f"Great work completing {workout_title}. Total volume: {vol_str}.",
            "createdAt": datetime.now(timezone.utc).isoformat(),
            "read": False,
            "readAt": None,
            "important": False,
            "iconName": "dumbbell",
            "actionLabel": "View Workout >",
            "actionRoute": "/workouts",
            "sourceId": session_id,
        }

        try:
            created, was_new = self.repo.create_or_ignore(uid, data)
            if was_new:
                self.repo.prune_user_notifications(uid, max_keep=100, newly_created_id=doc_id)
            return created
        except Exception as e:
            logger.warning(f"Failed to create workout notification {doc_id} for user {uid}: {e}")
            return None

    def create_pr_notification(
        self, uid: str, session_id: str, exercise_id: str, exercise_name: str, weight_kg: float, reps: int
    ) -> Optional[Dict[str, Any]]:
        """
        Creates a personal record notification.
        Deterministic ID: notif_pr_{session_id}_{exercise_id}
        """
        doc_id = f"notif_pr_{session_id}_{exercise_id}"
        rep_label = f"{reps} rep{'s' if reps > 1 else ''}"

        data = {
            "id": doc_id,
            "type": "personal_record",
            "category": "Progress",
            "title": "Personal record achieved!",
            "message": f"New PR on {exercise_name}: {weight_kg:g} kg for {rep_label}.",
            "createdAt": datetime.now(timezone.utc).isoformat(),
            "read": False,
            "readAt": None,
            "important": True,
            "iconName": "trophy",
            "actionLabel": "View Progress >",
            "actionRoute": "/progress",
            "sourceId": f"{session_id}:{exercise_id}",
        }

        try:
            created, was_new = self.repo.create_or_ignore(uid, data)
            if was_new:
                self.repo.prune_user_notifications(uid, max_keep=100, newly_created_id=doc_id)
            return created
        except Exception as e:
            logger.warning(f"Failed to create PR notification {doc_id} for user {uid}: {e}")
            return None

    def create_hydration_notification(self, uid: str, date_str: str) -> Optional[Dict[str, Any]]:
        """
        Creates a hydration goal achieved notification.
        Deterministic ID: notif_hydr_{date_str}
        """
        doc_id = f"notif_hydr_{date_str}"

        data = {
            "id": doc_id,
            "type": "hydration_milestone",
            "category": "Nutrition",
            "title": "Hydration goal reached!",
            "message": f"You hit your daily water intake target for {date_str}.",
            "createdAt": datetime.now(timezone.utc).isoformat(),
            "read": False,
            "readAt": None,
            "important": False,
            "iconName": "utensils",
            "actionLabel": "View Nutrition >",
            "actionRoute": "/nutrition",
            "sourceId": date_str,
        }

        try:
            created, was_new = self.repo.create_or_ignore(uid, data)
            if was_new:
                self.repo.prune_user_notifications(uid, max_keep=100, newly_created_id=doc_id)
            return created
        except Exception as e:
            logger.warning(f"Failed to create hydration notification {doc_id} for user {uid}: {e}")
            return None

    def create_welcome_notification(self, uid: str) -> Optional[Dict[str, Any]]:
        """
        Creates a system welcome notification for new users.
        Deterministic ID: notif_sys_welcome
        """
        doc_id = "notif_sys_welcome"

        data = {
            "id": doc_id,
            "type": "system_welcome",
            "category": "System",
            "title": "Welcome to AI FITNESS!",
            "message": "Your fitness journey begins today. Explore curated workout routines and log your first session!",
            "createdAt": datetime.now(timezone.utc).isoformat(),
            "read": False,
            "readAt": None,
            "important": True,
            "iconName": "shield",
            "actionLabel": "View Dashboard >",
            "actionRoute": "/dashboard",
            "sourceId": "welcome",
        }

        try:
            created, _ = self.repo.create_or_ignore(uid, data)
            return created
        except Exception as e:
            logger.warning(f"Failed to create welcome notification for user {uid}: {e}")
            return None

    # =========================================================================
    # QUERY & READ METHODS
    # =========================================================================

    def _to_schema(self, raw: Dict[str, Any]) -> NotificationItemSchema:
        """Converts raw persisted notification dict into API response schema with derived fields."""
        created_at = raw.get("createdAt")
        date_group, timestamp = derive_date_group_and_timestamp(created_at)

        category = raw.get("category", "System")
        if category not in ["Workout", "AI Coach", "Nutrition", "Achievement", "Progress", "Recovery", "System"]:
            category = "System"

        return NotificationItemSchema(
            id=raw.get("id", ""),
            type=raw.get("type"),
            category=category,
            title=raw.get("title", ""),
            message=raw.get("message", ""),
            createdAt=created_at,
            timestamp=timestamp,
            dateGroup=date_group,
            read=bool(raw.get("read", False)),
            readAt=raw.get("readAt"),
            important=bool(raw.get("important", False)),
            iconName=raw.get("iconName", "shield"),
            actionLabel=raw.get("actionLabel"),
            actionRoute=raw.get("actionRoute"),
            sourceId=raw.get("sourceId"),
        )

    def get_unread_count(self, uid: str) -> int:
        """Returns total unread count for user."""
        return self.repo.get_unread_count(uid)

    def mark_as_read(self, uid: str, notification_id: str) -> Optional[NotificationItemSchema]:
        """Marks a single notification as read."""
        updated = self.repo.mark_as_read(uid, notification_id)
        if not updated:
            return None
        return self._to_schema(updated)

    def mark_all_as_read(self, uid: str) -> Tuple[int, int]:
        """
        Marks all notifications as read.
        Returns: (unread_count, marked_count)
        """
        marked = self.repo.mark_all_as_read(uid)
        return (0, marked)

    def get_dashboard_data(
        self, uid: str, limit: int = 50, before: Optional[str] = None
    ) -> NotificationsDashboardDataSchema:
        """
        Assembles comprehensive notification dashboard payload:
        - Accurately computes unreadCount, todayCount, weekCount, importantCount across ALL user notifications
        - Limits feed to requested page limit with cursor support
        - Computes category insights and priority updates
        """
        all_items = self.repo.get_all_user_notifications(uid)
        now = datetime.now(timezone.utc)
        today_start = now.replace(hour=0, minute=0, second=0, microsecond=0)
        week_start = now - timedelta(days=7)

        unread_count = 0
        today_count = 0
        week_count = 0
        important_count = 0
        category_counts: Dict[str, int] = {}
        important_items: List[Dict[str, Any]] = []

        for item in all_items:
            dt = parse_iso_datetime(item.get("createdAt"))
            is_read = item.get("read", False)
            is_important = item.get("important", False)
            cat = item.get("category", "System")

            if not is_read:
                unread_count += 1

            if dt and dt >= today_start:
                today_count += 1

            if dt and dt >= week_start:
                week_count += 1

            if is_important:
                important_count += 1
                important_items.append(item)

            category_counts[cat] = category_counts.get(cat, 0) + 1

        # Feed pagination
        paginated_raw = self.repo.list_notifications(uid, limit=limit, before=before)
        notifications = [self._to_schema(n) for n in paginated_raw]

        # Category Insights calculation
        total_items = len(all_items)
        insights: List[NotificationCategorySummarySchema] = []
        if total_items > 0:
            # Sort categories by count descending
            sorted_cats = sorted(category_counts.items(), key=lambda x: x[1], reverse=True)
            for cat_name, cnt in sorted_cats:
                pct = round((cnt / total_items) * 100.0, 1)
                color = CATEGORY_COLORS.get(cat_name, "#64748b")
                insights.append(
                    NotificationCategorySummarySchema(
                        category=cat_name,
                        count=cnt,
                        percentage=pct,
                        color=color,
                    )
                )

        # Important Updates (up to 3 latest priority items)
        important_items.sort(key=lambda x: x.get("createdAt", ""), reverse=True)
        top_important = important_items[:3]
        important_updates: List[ImportantUpdateItemSchema] = []
        for imp in top_important:
            created_at = imp.get("createdAt")
            time_ago = derive_time_ago(created_at)
            important_updates.append(
                ImportantUpdateItemSchema(
                    id=f"iu_{imp.get('id', '')}",
                    category=imp.get("category", "System"),
                    title=imp.get("category", "System"),
                    description=imp.get("title", ""),
                    timeAgo=time_ago,
                    iconName=imp.get("iconName", "shield"),
                )
            )

        return NotificationsDashboardDataSchema(
            unreadCount=unread_count,
            todayCount=today_count,
            weekCount=week_count,
            importantCount=important_count,
            notifications=notifications,
            insights=insights,
            importantUpdates=important_updates,
            preferences=DEFAULT_PREFERENCES,
        )


_service_instance: Optional[NotificationService] = None


def get_notification_service() -> NotificationService:
    global _service_instance
    if _service_instance is None:
        _service_instance = NotificationService()
    return _service_instance
