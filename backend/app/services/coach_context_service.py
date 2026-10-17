from datetime import datetime, timezone
from typing import Optional, List, Dict, Any, Tuple
from ..repositories.user_repository import UserRepository, get_user_repository
from ..repositories.workout_repository import WorkoutRepository, get_workout_repository
from ..repositories.nutrition_repository import NutritionRepository, get_nutrition_repository
from ..repositories.achievement_repository import AchievementRepository, get_achievement_repository
from ..services.progress_service import ProgressService
from ..services.nutrition_service import NutritionService
from ..services.achievement_service import AchievementService
from ..schemas.coach import (
    CoachContext,
    CoachProfileContext,
    CoachSettingsSchema,
    CoachRecentActivityContext,
    CoachNutritionContext,
    CoachAchievementsContext,
    CoachFocus,
    CoachTone,
)
from ..utils.logger import logger


def get_today_utc_date() -> str:
    """Returns today's date formatted as YYYY-MM-DD in UTC."""
    return datetime.now(timezone.utc).strftime("%Y-%m-%d")


def format_goal_display(goal_key: Optional[str]) -> Optional[str]:
    """Formats raw goal enum into user-friendly display text."""
    if not goal_key:
        return None
    mapping = {
        "muscle_gain": "Muscle Gain / Hypertrophy",
        "fat_loss": "Fat Loss / Conditioning",
        "strength": "Maximum Strength",
        "endurance": "Endurance / Stamina",
        "general_fitness": "General Fitness & Health",
    }
    return mapping.get(goal_key, goal_key.replace("_", " ").title())


def format_experience_display(level_key: Optional[str]) -> Optional[str]:
    """Formats raw experience enum into user-friendly display text."""
    if not level_key:
        return None
    return level_key.title()


class CoachContextService:
    """
    Domain service for assembling the bounded, deterministic CoachContext.
    Pulls authoritative data from existing Phase 1-7 repositories and services.
    The LLM is NEVER the source of truth for numerical fitness metrics.
    """

    def __init__(
        self,
        user_repo: Optional[UserRepository] = None,
        workout_repo: Optional[WorkoutRepository] = None,
        progress_service: Optional[ProgressService] = None,
        nutrition_repo: Optional[NutritionRepository] = None,
        nutrition_service: Optional[NutritionService] = None,
        achievement_repo: Optional[AchievementRepository] = None,
        achievement_service: Optional[AchievementService] = None,
    ):
        self._user_repo = user_repo
        self._workout_repo = workout_repo
        self._progress_service = progress_service
        self._nutrition_repo = nutrition_repo
        self._nutrition_service = nutrition_service
        self._achievement_repo = achievement_repo
        self._achievement_service = achievement_service

    @property
    def user_repo(self) -> UserRepository:
        return self._user_repo or get_user_repository()

    @property
    def workout_repo(self) -> WorkoutRepository:
        return self._workout_repo or get_workout_repository()

    @property
    def progress_service(self) -> ProgressService:
        if self._progress_service:
            return self._progress_service
        return ProgressService(
            workout_repo=self.workout_repo,
            user_repo=self.user_repo,
        )

    @property
    def nutrition_repo(self) -> NutritionRepository:
        return self._nutrition_repo or get_nutrition_repository()

    @property
    def nutrition_service(self) -> NutritionService:
        if self._nutrition_service:
            return self._nutrition_service
        return NutritionService(
            nutrition_repo=self.nutrition_repo,
            user_repo=self.user_repo,
        )

    @property
    def achievement_repo(self) -> AchievementRepository:
        return self._achievement_repo or get_achievement_repository()

    @property
    def achievement_service(self) -> AchievementService:
        if self._achievement_service:
            return self._achievement_service
        return AchievementService(
            achievement_repo=self.achievement_repo,
            workout_repo=self.workout_repo,
            nutrition_repo=self.nutrition_repo,
            user_repo=self.user_repo,
            progress_service=self.progress_service,
        )

    # =========================================================================
    # SECTION BUILDERS
    # =========================================================================

    def _build_profile_context(self, uid: str) -> Tuple[CoachProfileContext, bool, Optional[str]]:
        """Retrieves and sanitizes user profile without exposing private tokens, email, or UID."""
        try:
            profile = self.user_repo.get_by_uid(uid)
            if not profile:
                return CoachProfileContext(), True, None

            ctx = CoachProfileContext(
                name=profile.name if profile.name else None,
                goal=format_goal_display(profile.primaryGoal),
                experienceLevel=format_experience_display(profile.fitnessLevel),
                targetCalories=profile.targetCalories,
                targetProteinGrams=float(profile.targetProteinGrams) if profile.targetProteinGrams else None,
                targetWaterLiters=3.0,
            )
            return ctx, True, None
        except Exception as e:
            logger.warning(f"Error fetching profile context for user {uid}: {e}")
            return CoachProfileContext(), False, f"Profile retrieval error: {str(e)}"

    def _build_preferences_context(
        self,
        profile_ctx: CoachProfileContext,
        passed_preferences: Optional[CoachSettingsSchema] = None,
    ) -> CoachSettingsSchema:
        """Determines tone and focus preferences from explicit settings or profile goal mapping."""
        if passed_preferences:
            return passed_preferences

        # Default tone
        tone: CoachTone = "encouraging"

        # Map focus from user goal if available
        focus: CoachFocus = "hypertrophy"
        if profile_ctx.goal:
            goal_lower = profile_ctx.goal.lower()
            if "fat loss" in goal_lower or "conditioning" in goal_lower:
                focus = "fat_loss"
            elif "strength" in goal_lower:
                focus = "strength"
            elif "endurance" in goal_lower or "recovery" in goal_lower:
                focus = "recovery"

        return CoachSettingsSchema(tone=tone, focus=focus)

    def _build_recent_activity_context(self, uid: str) -> Tuple[CoachRecentActivityContext, bool, Optional[str]]:
        """Retrieves 7-day workout activity, streak, volume, latest routine, and top recent PRs."""
        try:
            # Reuses authoritative ProgressService logic
            summary = self.progress_service.get_summary(uid, period="7d")
            completed_sessions = self.progress_service._get_completed_sessions(uid)

            # Latest workout title
            latest_title = completed_sessions[0].workoutTitle if completed_sessions else None

            # Calculate PRs from completed sessions using authoritative logic
            all_prs = self.progress_service.calculate_personal_records(completed_sessions)
            # Top 3 most relevant / recent PRs formatted concisely
            recent_pr_strings = [
                f"{pr.exerciseName}: {pr.value}" for pr in all_prs[:3]
            ]

            ctx = CoachRecentActivityContext(
                activeStreak=summary.currentStreakDays,
                workoutsCompletedThisWeek=summary.totalWorkouts,
                totalRecentVolumeKg=round(summary.totalVolumeKg, 1),
                latestWorkoutTitle=latest_title,
                recentPRs=recent_pr_strings,
            )
            return ctx, True, None
        except Exception as e:
            logger.warning(f"Error fetching recent activity context for user {uid}: {e}")
            return CoachRecentActivityContext(), False, f"Recent activity retrieval error: {str(e)}"

    def _build_nutrition_context(self, uid: str) -> Tuple[CoachNutritionContext, bool, Optional[str]]:
        """Retrieves today's authoritative nutrition log and targets, preserving empty status."""
        try:
            today_str = get_today_utc_date()
            try:
                targets = self.nutrition_service._get_user_targets(uid)
            except Exception:
                targets = {"targetCalories": 2400, "targetProteinGrams": 160.0, "waterTargetLiters": 3.0}
            target_cals = targets.get("targetCalories", 2400)
            target_p = targets.get("targetProteinGrams", 160.0)
            target_w = targets.get("waterTargetLiters", 3.0)

            daily_log = self.nutrition_repo.get_daily_log(uid, today_str)
            if not daily_log:
                # Explicit representation of no log today: isLoggedToday=False, consumed=None
                ctx = CoachNutritionContext(
                    isLoggedToday=False,
                    consumedCalories=None,
                    targetCalories=target_cals,
                    consumedProteinGrams=None,
                    targetProteinGrams=target_p,
                    consumedWaterLiters=None,
                    targetWaterLiters=target_w,
                )
                return ctx, True, None

            ctx = CoachNutritionContext(
                isLoggedToday=True,
                consumedCalories=daily_log.consumedCalories,
                targetCalories=daily_log.targetCalories or target_cals,
                consumedProteinGrams=daily_log.consumedProteinGrams,
                targetProteinGrams=daily_log.targetProteinGrams or target_p,
                consumedWaterLiters=round(daily_log.waterIntakeLiters, 1),
                targetWaterLiters=daily_log.waterTargetLiters or target_w,
            )
            return ctx, True, None
        except Exception as e:
            logger.warning(f"Error fetching nutrition context for user {uid}: {e}")
            return CoachNutritionContext(), False, f"Nutrition retrieval error: {str(e)}"

    def _build_achievements_context(self, uid: str) -> Tuple[CoachAchievementsContext, bool, Optional[str]]:
        """Retrieves authoritative achievement points, level, and latest unlocked badge."""
        try:
            self.achievement_repo.ensure_seeded()
            definitions = {d.id: d for d in self.achievement_repo.list_definitions()}
            user_achs = self.achievement_repo.list_user_achievements(uid)

            unlocked_system = [a for a in user_achs if a.isUnlocked and not a.isCustom]
            unlocked_custom = [a for a in user_achs if a.isUnlocked and a.isCustom]

            total_system_points = sum(
                definitions[a.achievementId].points
                for a in unlocked_system
                if a.achievementId in definitions
            )
            total_custom_points = sum(a.points for a in unlocked_custom)
            total_points = total_system_points + total_custom_points
            unlocked_count = len(unlocked_system) + len(unlocked_custom)

            current_level, _, next_title, _, _ = self.achievement_service.calculate_level_progression(total_points)

            # Find latest unlocked badge
            all_unlocked = [a for a in user_achs if a.isUnlocked]
            all_unlocked.sort(key=lambda x: x.unlockedAt or "", reverse=True)
            latest_badge_name = None
            if all_unlocked:
                latest = all_unlocked[0]
                if latest.isCustom:
                    latest_badge_name = latest.customTitle or "Custom Milestone"
                elif latest.achievementId in definitions:
                    latest_badge_name = definitions[latest.achievementId].title

            ctx = CoachAchievementsContext(
                totalPoints=total_points,
                level=current_level,
                levelTitle=next_title if current_level > 1 else "Novice Lifter",
                unlockedCount=unlocked_count,
                latestBadge=latest_badge_name,
            )
            return ctx, True, None
        except Exception as e:
            logger.warning(f"Error fetching achievements context for user {uid}: {e}")
            return CoachAchievementsContext(), False, f"Achievements retrieval error: {str(e)}"

    # =========================================================================
    # MAIN ENTRY POINT
    # =========================================================================

    def build_context(
        self,
        uid: str,
        preferences: Optional[CoachSettingsSchema] = None,
    ) -> CoachContext:
        """
        Assembles the complete bounded CoachContext for the authenticated user.
        Never exposes client UIDs, credentials, or unbounded full database histories.
        """
        errors: List[str] = []

        # 1. Profile
        profile_ctx, profile_ok, profile_err = self._build_profile_context(uid)
        if not profile_ok and profile_err:
            errors.append(profile_err)

        # 2. Preferences
        pref_ctx = self._build_preferences_context(profile_ctx, preferences)

        # 3. Recent Activity (7 Days)
        activity_ctx, activity_ok, activity_err = self._build_recent_activity_context(uid)
        if not activity_ok and activity_err:
            errors.append(activity_err)

        # 4. Nutrition
        nutrition_ctx, nutrition_ok, nutrition_err = self._build_nutrition_context(uid)
        if not nutrition_ok and nutrition_err:
            errors.append(nutrition_err)

        # 5. Achievements
        ach_ctx, ach_ok, ach_err = self._build_achievements_context(uid)
        if not ach_ok and ach_err:
            errors.append(ach_err)

        return CoachContext(
            profile=profile_ctx,
            preferences=pref_ctx,
            recentActivity=activity_ctx,
            todayNutrition=nutrition_ctx,
            achievements=ach_ctx,
            profileAvailable=profile_ok,
            recentActivityAvailable=activity_ok,
            todayNutritionAvailable=nutrition_ok,
            achievementsAvailable=ach_ok,
            errors=errors,
        )

    async def assemble_coach_context(
        self,
        uid: str,
        preferences: Optional[CoachSettingsSchema] = None,
    ) -> CoachContext:
        """
        Asynchronous context assembly wrapper for CoachContextService.
        Delegates to build_context for bounded, authoritative context generation.
        """
        return self.build_context(uid, preferences)

    # =========================================================================
    # SERIALIZATION FOR FUTURE LLM INJECTION
    # =========================================================================

    def serialize_for_llm(self, context: CoachContext) -> str:
        """
        Serializes CoachContext into a deterministic, compact, human-readable
        Markdown format (< 450 tokens) designed for LLM system prompt injection.
        Guaranteed to contain zero user messages and zero sensitive credentials.
        """
        lines: List[str] = []

        # 1. Profile Section
        lines.append("[USER PROFILE]")
        if context.profileAvailable:
            name_str = context.profile.name or "User"
            goal_str = context.profile.goal or "General Fitness"
            exp_str = context.profile.experienceLevel or "Intermediate"
            lines.append(f"Name: {name_str}")
            lines.append(f"Primary Goal: {goal_str}")
            lines.append(f"Experience Level: {exp_str}")
            if context.profile.targetCalories:
                lines.append(f"Daily Target Calories: {context.profile.targetCalories} kcal")
            if context.profile.targetProteinGrams:
                lines.append(f"Daily Target Protein: {context.profile.targetProteinGrams}g")
        else:
            lines.append("Status: Profile information temporarily unavailable")

        lines.append("")

        # 2. Preferences Section
        lines.append("[COACHING PREFERENCES]")
        lines.append(f"Tone: {context.preferences.tone.title()}")
        lines.append(f"Focus: {context.preferences.focus.replace('_', ' ').title()}")

        lines.append("")

        # 3. Recent Activity Section
        lines.append("[RECENT ACTIVITY (LAST 7 DAYS)]")
        if context.recentActivityAvailable:
            lines.append(f"Active Workout Streak: {context.recentActivity.activeStreak} days")
            lines.append(f"Workouts Completed This Week: {context.recentActivity.workoutsCompletedThisWeek}")
            lines.append(f"Total Volume Lifted: {context.recentActivity.totalRecentVolumeKg:,.1f} kg")
            if context.recentActivity.latestWorkoutTitle:
                lines.append(f"Latest Workout: {context.recentActivity.latestWorkoutTitle}")
            else:
                lines.append("Latest Workout: None recorded recently")
            if context.recentActivity.recentPRs:
                lines.append("Recent Personal Records: " + ", ".join(context.recentActivity.recentPRs))
            else:
                lines.append("Recent Personal Records: None recorded yet")
        else:
            lines.append("Status: Workout activity temporarily unavailable")

        lines.append("")

        # 4. Nutrition Section
        lines.append("[TODAY'S NUTRITION]")
        if context.todayNutritionAvailable:
            if context.todayNutrition.isLoggedToday:
                cals = context.todayNutrition.consumedCalories or 0
                tgt_cals = context.todayNutrition.targetCalories
                prot = context.todayNutrition.consumedProteinGrams or 0.0
                tgt_prot = context.todayNutrition.targetProteinGrams
                water = context.todayNutrition.consumedWaterLiters or 0.0
                tgt_water = context.todayNutrition.targetWaterLiters
                lines.append(f"Calories Consumed: {cals:,} / {tgt_cals:,} kcal")
                lines.append(f"Protein Consumed: {prot:.1f} / {tgt_prot:.1f} g")
                lines.append(f"Water Intake: {water:.1f} / {tgt_water:.1f} L")
            else:
                lines.append("Status: No nutrition logged yet today")
                lines.append(f"Daily Target: {context.todayNutrition.targetCalories} kcal | {context.todayNutrition.targetProteinGrams}g protein | {context.todayNutrition.targetWaterLiters}L water")
        else:
            lines.append("Status: Nutrition data temporarily unavailable")

        lines.append("")

        # 5. Achievements Section
        lines.append("[ACHIEVEMENTS]")
        if context.achievementsAvailable:
            lines.append(f"Total Points: {context.achievements.totalPoints:,}")
            lines.append(f"Current Level: Level {context.achievements.level} ({context.achievements.levelTitle})")
            lines.append(f"Unlocked Badges: {context.achievements.unlockedCount}")
            if context.achievements.latestBadge:
                lines.append(f"Latest Badge: {context.achievements.latestBadge}")
            else:
                lines.append("Latest Badge: None yet")
        else:
            lines.append("Status: Achievements data temporarily unavailable")

        return "\n".join(lines)


_context_service_instance: Optional[CoachContextService] = None


def get_coach_context_service() -> CoachContextService:
    """Returns the singleton CoachContextService instance."""
    global _context_service_instance
    if _context_service_instance is None:
        _context_service_instance = CoachContextService()
    return _context_service_instance
