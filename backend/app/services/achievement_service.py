from datetime import datetime, timezone, timedelta
from typing import Optional, List, Dict, Any, Tuple
from fastapi import Depends
from ..repositories.achievement_repository import AchievementRepository, get_achievement_repository
from ..repositories.workout_repository import WorkoutRepository, get_workout_repository
from ..repositories.nutrition_repository import NutritionRepository, get_nutrition_repository
from ..repositories.user_repository import UserRepository, get_user_repository
from ..services.progress_service import ProgressService, parse_session_datetime
from ..schemas.achievement import (
    AchievementDefinitionSchema,
    UserAchievementSchema,
    AchievementKpiItemSchema,
    RecentAchievementBadgeSchema,
    NextMilestoneSchema,
    AchievementsProgressDataSchema,
    AchievementCategoryItemSchema,
    CurrentChallengeItemSchema,
    LeaderboardUserSchema,
    AchievementsDashboardDataSchema,
    AchievementDetailSchema,
)
from ..utils.logger import logger


def humanize_time_ago(iso_str: Optional[str]) -> str:
    """Formats an ISO timestamp into a user-friendly relative time string."""
    if not iso_str:
        return "Recently"
    try:
        dt = datetime.fromisoformat(iso_str.replace("Z", "+00:00"))
        if dt.tzinfo is None:
            dt = dt.replace(tzinfo=timezone.utc)
        now = datetime.now(timezone.utc)
        diff = now - dt

        seconds = int(diff.total_seconds())
        if seconds < 60:
            return "Just now"
        elif seconds < 3600:
            mins = seconds // 60
            return f"{mins} min{'s' if mins > 1 else ''} ago"
        elif seconds < 86400:
            hours = seconds // 3600
            return f"{hours} hour{'s' if hours > 1 else ''} ago"
        elif seconds < 604800:
            days = seconds // 86400
            return f"{days} day{'s' if days > 1 else ''} ago"
        else:
            weeks = seconds // 604800
            return f"{weeks} week{'s' if weeks > 1 else ''} ago"
    except Exception:
        return "Recently"


class AchievementService:
    """
    Domain service for deterministic achievement evaluation, points calculation,
    and dashboard data construction from authoritative workout and nutrition logs.
    """

    def __init__(
        self,
        achievement_repo: Optional[AchievementRepository] = None,
        workout_repo: Optional[WorkoutRepository] = None,
        nutrition_repo: Optional[NutritionRepository] = None,
        user_repo: Optional[UserRepository] = None,
        progress_service: Optional[ProgressService] = None,
        notification_service: Optional[Any] = None,
    ):
        self._achievement_repo = achievement_repo
        self._workout_repo = workout_repo
        self._nutrition_repo = nutrition_repo
        self._user_repo = user_repo
        self._progress_service = progress_service
        self._notification_service = notification_service

    @property
    def notification_service(self) -> Any:
        if self._notification_service:
            return self._notification_service
        from .notification_service import get_notification_service
        return get_notification_service()

    @property
    def achievement_repo(self) -> AchievementRepository:
        return self._achievement_repo or get_achievement_repository()

    @property
    def workout_repo(self) -> WorkoutRepository:
        return self._workout_repo or get_workout_repository()

    @property
    def nutrition_repo(self) -> NutritionRepository:
        return self._nutrition_repo or get_nutrition_repository()

    @property
    def user_repo(self) -> UserRepository:
        return self._user_repo or get_user_repository()

    @property
    def progress_service(self) -> ProgressService:
        if self._progress_service:
            return self._progress_service
        return ProgressService(
            workout_repo=self.workout_repo,
            user_repo=self.user_repo,
        )

    @staticmethod
    def calculate_level_progression(total_points: int) -> Tuple[int, int, str, int, int]:
        """
        Calculates level progression semantics:
        Level 1: 0 points (starting state)
        Level 10: 1000 points milestone (Novice Lifter)
        Level 20: 2500 points milestone (Apprentice)
        Level 30: 5000 points milestone (Challenger)
        Level 40: 8000 points milestone (Athlete)
        Level 50: 12000 points milestone (Fitness Legend)
        Level 60: 16000+ points / final open-ended tier (Iron Master)

        Returns: (current_level, next_level, next_title, target_pts, pts_to_go)
        """
        if total_points < 1000:
            return (1, 10, "Novice Lifter", 1000, 1000 - total_points)
        elif total_points < 2500:
            return (10, 20, "Apprentice", 2500, 2500 - total_points)
        elif total_points < 5000:
            return (20, 30, "Challenger", 5000, 5000 - total_points)
        elif total_points < 8000:
            return (30, 40, "Athlete", 8000, 8000 - total_points)
        elif total_points < 12000:
            return (40, 50, "Fitness Legend", 12000, 12000 - total_points)
        elif total_points < 16000:
            return (50, 60, "Iron Master", 16000, 16000 - total_points)
        else:
            target = total_points + 5000
            return (60, 70, "Apex Titan", target, 5000)

    # =========================================================================
    # DETERMINISTIC EVALUATION ENGINE
    # =========================================================================

    def evaluate_user_achievements(
        self, uid: str
    ) -> Tuple[List[UserAchievementSchema], List[AchievementDefinitionSchema]]:
        """
        Evaluates all global achievement rules against the user's authoritative activity.
        Updates user-scoped achievement records in Firestore idempotently.
        Returns:
            (all_user_achievements, newly_unlocked_definitions)
        """
        # 1. Authoritative activity metrics
        sessions = self.progress_service._get_completed_sessions(uid)
        streak = self.progress_service.calculate_streak(sessions)
        volume = sum(s.totalVolumeKg for s in sessions)
        calories = sum(s.caloriesBurned for s in sessions)
        pr_records = self.progress_service.calculate_personal_records(sessions)
        pr_count = len(pr_records)

        # Early workouts (started before 7:00 AM local/recorded time)
        early_workouts = 0
        for s in sessions:
            dt = parse_session_datetime(s.startedAt)
            if dt and dt.hour < 7:
                early_workouts += 1

        # Nutrition metrics
        nutrition_logs = self.nutrition_repo.list_all_user_logs(uid)
        nutrition_days = len([
            l for l in nutrition_logs
            if l.consumedCalories > 0 or (l.meals and any(m.foods for m in l.meals))
        ])
        hydration_days = len([
            l for l in nutrition_logs
            if l.waterIntakeLiters >= (l.waterTargetLiters or 3.0) and (l.waterTargetLiters or 3.0) > 0
        ])

        # 2. Global definitions & existing state
        definitions = self.achievement_repo.list_definitions()
        existing_records = {
            a.achievementId: a
            for a in self.achievement_repo.list_user_achievements(uid)
        }

        now_str = datetime.now(timezone.utc).isoformat()
        items_to_persist: List[Dict[str, Any]] = []
        newly_unlocked: List[AchievementDefinitionSchema] = []

        for defn in definitions:
            # Map metric type
            if defn.metricType == "workout_count":
                metric_val = float(len(sessions))
            elif defn.metricType == "streak_days":
                metric_val = float(streak)
            elif defn.metricType == "volume_kg":
                metric_val = float(volume)
            elif defn.metricType == "calories_burned":
                metric_val = float(calories)
            elif defn.metricType == "pr_count":
                metric_val = float(pr_count)
            elif defn.metricType == "nutrition_days":
                metric_val = float(nutrition_days)
            elif defn.metricType == "hydration_days":
                metric_val = float(hydration_days)
            elif defn.metricType == "early_workouts":
                metric_val = float(early_workouts)
            else:
                metric_val = 0.0

            threshold = defn.threshold
            existing = existing_records.get(defn.id)

            if existing and existing.isUnlocked:
                # Already unlocked: preserve unlockedAt and existing isNew status
                cur_val = max(existing.currentValue, metric_val)
                pct = 100.0
                if cur_val != existing.currentValue:
                    items_to_persist.append({
                        "id": defn.id,
                        "userId": uid,
                        "achievementId": defn.id,
                        "isUnlocked": True,
                        "unlockedAt": existing.unlockedAt,
                        "currentValue": cur_val,
                        "targetValue": threshold,
                        "progressPercentage": pct,
                        "isNew": existing.isNew,
                        "isCustom": False,
                        "points": defn.points,
                        "updatedAt": now_str,
                    })
            elif metric_val >= threshold and threshold > 0:
                # Newly unlocked!
                newly_unlocked.append(defn)
                items_to_persist.append({
                    "id": defn.id,
                    "userId": uid,
                    "achievementId": defn.id,
                    "isUnlocked": True,
                    "unlockedAt": now_str,
                    "currentValue": metric_val,
                    "targetValue": threshold,
                    "progressPercentage": 100.0,
                    "isNew": True,
                    "isCustom": False,
                    "points": defn.points,
                    "updatedAt": now_str,
                })
            else:
                # Locked state
                pct = min(100.0, round((metric_val / threshold) * 100.0, 1)) if threshold > 0 else 0.0
                # Only persist if value changed or doesn't exist
                if not existing or existing.currentValue != metric_val or existing.progressPercentage != pct:
                    items_to_persist.append({
                        "id": defn.id,
                        "userId": uid,
                        "achievementId": defn.id,
                        "isUnlocked": False,
                        "unlockedAt": None,
                        "currentValue": metric_val,
                        "targetValue": threshold,
                        "progressPercentage": pct,
                        "isNew": False,
                        "isCustom": False,
                        "points": defn.points,
                        "updatedAt": now_str,
                    })

        # Atomic batch update
        if items_to_persist:
            self.achievement_repo.batch_upsert_user_achievements(uid, items_to_persist)

        # Dispatch secondary notifications for newly unlocked achievements
        if newly_unlocked:
            for defn in newly_unlocked:
                try:
                    self.notification_service.create_achievement_notification(uid, defn)
                except Exception as e:
                    logger.warning(f"Failed to create notification for unlocked achievement {defn.id} for user {uid}: {e}")

        all_user_achs = self.achievement_repo.list_user_achievements(uid)
        return all_user_achs, newly_unlocked

    # =========================================================================
    # DASHBOARD AGGREGATION & DATA CONSTRUCTION
    # =========================================================================

    def get_dashboard_data(self, uid: str) -> AchievementsDashboardDataSchema:
        """
        Evaluates achievements deterministically and returns the complete dashboard payload
        conforming to AchievementsDashboardDataSchema without fabricated data.
        """
        # Ensure seeded definitions exist
        self.achievement_repo.ensure_seeded()

        # Run evaluation
        user_achs, _ = self.evaluate_user_achievements(uid)
        definitions = {d.id: d for d in self.achievement_repo.list_definitions()}

        # 1. Total points: sum of distinct unlocked achievements
        unlocked_system = [a for a in user_achs if a.isUnlocked and not a.isCustom]
        unlocked_custom = [a for a in user_achs if a.isUnlocked and a.isCustom]

        total_system_points = sum(definitions[a.achievementId].points for a in unlocked_system if a.achievementId in definitions)
        total_custom_points = sum(a.points for a in unlocked_custom)
        total_points = total_system_points + total_custom_points

        total_achieved_count = len(unlocked_system) + len(unlocked_custom)

        # 2. Longest and Current Streak
        sessions = self.progress_service._get_completed_sessions(uid)
        current_streak = self.progress_service.calculate_streak(sessions)

        # 3. Next Milestone calculation
        # Authorized progression semantics:
        # Level 1: 0 points (starting state)
        # Level 10: 1000 points milestone (Novice Lifter)
        # Level 20: 2500 points milestone (Apprentice)
        # Level 30: 5000 points milestone (Challenger)
        # Level 40: 8000 points milestone (Athlete)
        # Level 50: 12000 points milestone (Fitness Legend)
        # Level 60: 16000+ points / final open-ended tier (Iron Master)
        current_level, next_level, next_title, target_pts, pts_to_go = self.calculate_level_progression(total_points)

        next_milestone = NextMilestoneSchema(
            level=next_level,
            title=next_title,
            description=f"Earn {target_pts:,} total points",
            currentPts=total_points,
            targetPts=target_pts,
            ptsToGo=pts_to_go,
            currentLevel=current_level,
        )

        # 4. Circular progress breakdown
        total_system_defs = len(definitions)
        locked_system = [a for a in user_achs if not a.isUnlocked and not a.isCustom]
        in_progress_count = len([a for a in locked_system if a.currentValue > 0])
        not_started_count = len([a for a in locked_system if a.currentValue == 0])

        overall_pct = (
            int(round((len(unlocked_system) / total_system_defs) * 100))
            if total_system_defs > 0
            else 0
        )

        progress_summary = AchievementsProgressDataSchema(
            overallPct=min(100, overall_pct),
            achievedCount=total_achieved_count,
            inProgressCount=in_progress_count,
            lockedCount=not_started_count,
            nextMilestone=next_milestone,
        )

        # 5. KPI Strip
        kpis = [
            AchievementKpiItemSchema(
                id="k1",
                title="Total Achievements",
                value=str(total_achieved_count),
                supportingText=f"{len(unlocked_system)} of {total_system_defs} unlocked",
                iconName="trophy",
                color="#10b981",
            ),
            AchievementKpiItemSchema(
                id="k2",
                title="Total Points",
                value=f"{total_points:,}",
                supportingText=f"{pts_to_go:,} pts to Next Level",
                iconName="sun",
                color="#f59e0b",
            ),
            AchievementKpiItemSchema(
                id="k3",
                title="Longest Streak",
                value=f"{current_streak} Day{'s' if current_streak != 1 else ''}",
                supportingText=f"Current: {current_streak} Day{'s' if current_streak != 1 else ''}",
                iconName="flame",
                color="#3b82f6",
            ),
            AchievementKpiItemSchema(
                id="k4",
                title="Challenges Completed",
                value="0",
                supportingText="No active challenges",
                iconName="target",
                color="#a855f7",
            ),
            AchievementKpiItemSchema(
                id="k5",
                title="Rewards Earned",
                value=str(total_achieved_count),
                supportingText="Milestone badges",
                iconName="gift",
                color="#f97316",
            ),
        ]

        # 6. Recent Achievements Section (top 6 unlocked, sorted by unlockedAt desc)
        all_unlocked: List[Tuple[str, str, str, str, bool, str, str]] = []

        for a in user_achs:
            if a.isUnlocked:
                if a.isCustom:
                    all_unlocked.append((
                        a.id,
                        a.customTitle or "Custom Milestone",
                        a.customDescription or "User created achievement",
                        a.unlockedAt or "",
                        a.isNew,
                        "star",
                        "#10b981",
                    ))
                elif a.achievementId in definitions:
                    defn = definitions[a.achievementId]
                    all_unlocked.append((
                        a.id,
                        defn.title,
                        defn.description,
                        a.unlockedAt or "",
                        a.isNew,
                        defn.iconName,
                        defn.color,
                    ))

        # Sort descending by unlockedAt timestamp
        all_unlocked.sort(key=lambda x: x[3], reverse=True)

        recent_badges: List[RecentAchievementBadgeSchema] = []
        for item in all_unlocked[:6]:
            recent_badges.append(
                RecentAchievementBadgeSchema(
                    id=item[0],
                    title=item[1],
                    description=item[2],
                    timeAgo=humanize_time_ago(item[3]),
                    isNew=item[4],
                    iconName=item[5],
                    color=item[6],
                )
            )

        # 7. Achievement Categories
        category_map: Dict[str, Dict[str, Any]] = {}
        for defn in definitions.values():
            if defn.category not in category_map:
                category_map[defn.category] = {
                    "title": defn.category,
                    "total": 0,
                    "current": 0,
                    "iconName": defn.iconName,
                    "color": defn.color,
                }
            category_map[defn.category]["total"] += 1

        for a in unlocked_system:
            if a.achievementId in definitions:
                cat = definitions[a.achievementId].category
                if cat in category_map:
                    category_map[cat]["current"] += 1

        categories: List[AchievementCategoryItemSchema] = []
        for idx, (cat_name, cat_data) in enumerate(category_map.items()):
            tot = cat_data["total"]
            cur = cat_data["current"]
            pct = int(round((cur / tot) * 100)) if tot > 0 else 0
            categories.append(
                AchievementCategoryItemSchema(
                    id=f"c{idx+1}",
                    title=cat_name,
                    current=cur,
                    total=tot,
                    pct=min(100, pct),
                    iconName=cat_data["iconName"],
                    color=cat_data["color"],
                )
            )

        # 8. Leaderboard & Challenges: HONEST DATA ONLY (No fabricated users, no misleading #1 rank)
        # Phase 6 does not build a social cross-user ranking system.
        # Return an honest unranked state without fabricating ranking positions or Top X% stats.
        leaderboard: List[LeaderboardUserSchema] = []

        # Return clean empty challenges (no fake active challenges)
        current_challenges: List[CurrentChallengeItemSchema] = []

        return AchievementsDashboardDataSchema(
            kpis=kpis,
            recentAchievements=recent_badges,
            progressSummary=progress_summary,
            categories=categories,
            currentChallenges=current_challenges,
            leaderboard=leaderboard,
        )

    def list_all_achievement_details(
        self, uid: str, category: Optional[str] = None
    ) -> List[AchievementDetailSchema]:
        """
        Returns all system and custom achievements with user progress and unlocked status.
        Supports category filtering for tabbed browsing.
        """
        self.achievement_repo.ensure_seeded()
        user_achs, _ = self.evaluate_user_achievements(uid)
        user_ach_map = {a.achievementId: a for a in user_achs}
        definitions = self.achievement_repo.list_definitions()

        results: List[AchievementDetailSchema] = []

        # 1. System achievements
        for defn in definitions:
            if category and defn.category.lower() != category.lower():
                continue

            state = user_ach_map.get(defn.id)
            is_unlocked = state.isUnlocked if state else False
            unlocked_at = state.unlockedAt if state else None
            cur_val = state.currentValue if state else 0.0
            pct = state.progressPercentage if state else 0.0
            is_new = state.isNew if state else False

            results.append(
                AchievementDetailSchema(
                    id=defn.id,
                    title=defn.title,
                    description=defn.description,
                    category=defn.category,
                    iconName=defn.iconName,
                    color=defn.color,
                    points=defn.points,
                    currentValue=cur_val,
                    targetValue=defn.threshold,
                    progressPercentage=pct,
                    isUnlocked=is_unlocked,
                    unlockedAt=unlocked_at,
                    isNew=is_new,
                    isCustom=False,
                )
            )

        # 2. Custom milestones
        for a in user_achs:
            if not a.isCustom:
                continue
            if category and (a.customCategory or "").lower() != category.lower():
                continue

            results.append(
                AchievementDetailSchema(
                    id=a.id,
                    title=a.customTitle or "Custom Milestone",
                    description=a.customDescription or "",
                    category=a.customCategory or "Special",
                    iconName="star",
                    color="#10b981",
                    points=a.points,
                    currentValue=a.currentValue,
                    targetValue=a.targetValue,
                    progressPercentage=a.progressPercentage,
                    isUnlocked=a.isUnlocked,
                    unlockedAt=a.unlockedAt,
                    isNew=a.isNew,
                    isCustom=True,
                )
            )

        return results


# FastAPI provider
def get_achievement_service(
    achievement_repo: AchievementRepository = Depends(get_achievement_repository),
    workout_repo: WorkoutRepository = Depends(get_workout_repository),
    nutrition_repo: NutritionRepository = Depends(get_nutrition_repository),
    user_repo: UserRepository = Depends(get_user_repository),
) -> AchievementService:
    """FastAPI dependency injection provider for AchievementService."""
    prog_service = ProgressService(
        workout_repo=workout_repo,
        user_repo=user_repo,
    )
    return AchievementService(
        achievement_repo=achievement_repo,
        workout_repo=workout_repo,
        nutrition_repo=nutrition_repo,
        user_repo=user_repo,
        progress_service=prog_service,
    )
