from typing import Optional, List, Dict, Any, Tuple
from fastapi import Depends
from ..repositories.workout_repository import WorkoutRepository, get_workout_repository
from ..repositories.exercise_repository import ExerciseRepository, get_exercise_repository, EXERCISE_ID_ALIASES
from ..services.notification_service import NotificationService, get_notification_service
from ..services.achievement_service import AchievementService, get_achievement_service
from ..schemas.workout import WorkoutSessionResponse, WorkoutSessionComplete
from ..utils.logger import logger


class WorkoutService:
    """
    Domain service for workout operations, session completion orchestration,
    PR detection, notification dispatch, and achievement evaluation.
    """

    def __init__(
        self,
        workout_repo: Optional[WorkoutRepository] = None,
        exercise_repo: Optional[ExerciseRepository] = None,
        notification_service: Optional[NotificationService] = None,
        achievement_service: Optional[AchievementService] = None,
    ):
        self._workout_repo = workout_repo
        self._exercise_repo = exercise_repo
        self._notification_service = notification_service
        self._achievement_service = achievement_service

    @property
    def workout_repo(self) -> WorkoutRepository:
        return self._workout_repo or get_workout_repository()

    @property
    def exercise_repo(self) -> ExerciseRepository:
        return self._exercise_repo or get_exercise_repository()

    @property
    def notification_service(self) -> NotificationService:
        return self._notification_service or get_notification_service()

    @property
    def achievement_service(self) -> AchievementService:
        if self._achievement_service:
            return self._achievement_service
        return AchievementService(
            workout_repo=self.workout_repo,
        )

    def complete_session(
        self, uid: str, session_id: str, complete_data: WorkoutSessionComplete
    ) -> Optional[WorkoutSessionResponse]:
        """
        Completes a workout session and coordinates secondary events:
        1. Marks session as completed in repository (authoritative).
        2. Detects if any sets established a new personal record (PR) and creates PR notification.
        3. Creates workout completion notification.
        4. Triggers achievement evaluation (which generates achievement notifications for new unlocks).
        5. Secondary notification failures are caught and logged without failing the primary operation.
        """
        # Step 1: Query prior completed sessions for PR baseline calculation
        prior_sessions = [
            s for s in self.workout_repo.list_user_history(uid, limit=100)
            if s.id != session_id and s.status == "completed"
        ]

        prior_bests: Dict[str, float] = {}
        for s in prior_sessions:
            for ex_id, sets in s.completedSets.items():
                canonical_id = EXERCISE_ID_ALIASES.get(ex_id, ex_id)
                for st in sets:
                    wt = st.actualWeightKg or st.targetWeightKg or 0.0
                    if wt > prior_bests.get(canonical_id, 0.0):
                        prior_bests[canonical_id] = wt

        # Step 2: Perform authoritative session completion
        completed = self.workout_repo.complete_session(uid, session_id, complete_data)
        if not completed:
            return None

        workout_title = completed.workoutTitle or "Workout"
        total_vol = completed.totalVolumeKg or 0.0

        # Step 3: Check for newly established Personal Records
        try:
            detected_prs: Dict[str, Tuple[float, int]] = {}
            for ex_id, sets in completed.completedSets.items():
                canonical_id = EXERCISE_ID_ALIASES.get(ex_id, ex_id)
                for st in sets:
                    wt = st.actualWeightKg or st.targetWeightKg or 0.0
                    reps = st.actualReps or st.targetReps or 0
                    if wt > 0 and wt > prior_bests.get(canonical_id, 0.0):
                        # Higher than historical best
                        if canonical_id not in detected_prs or wt > detected_prs[canonical_id][0]:
                            detected_prs[canonical_id] = (wt, reps)

            for ex_id, (best_wt, best_reps) in detected_prs.items():
                ex_obj = self.exercise_repo.get_by_id(ex_id)
                if ex_obj:
                    ex_name = ex_obj.name
                else:
                    logger.warning("PR notification generated for unrecognized exercise ID '%s'", ex_id)
                    ex_name = ex_id

                self.notification_service.create_pr_notification(
                    uid=uid,
                    session_id=session_id,
                    exercise_id=ex_id,
                    exercise_name=ex_name,
                    weight_kg=best_wt,
                    reps=best_reps,
                )
        except Exception as e:
            logger.warning(f"Error generating PR notification for user {uid}, session {session_id}: {e}")

        # Step 4: Create workout completion notification
        try:
            self.notification_service.create_workout_completed_notification(
                uid=uid,
                session_id=session_id,
                workout_title=workout_title,
                volume_kg=total_vol,
            )
        except Exception as e:
            logger.warning(f"Error generating workout notification for user {uid}, session {session_id}: {e}")

        # Step 5: Trigger achievement evaluation
        try:
            self.achievement_service.evaluate_user_achievements(uid)
        except Exception as e:
            logger.warning(f"Error evaluating achievements on workout completion for user {uid}: {e}")

        return completed


def get_workout_service(
    workout_repo: WorkoutRepository = Depends(get_workout_repository),
    exercise_repo: ExerciseRepository = Depends(get_exercise_repository),
    notification_service: NotificationService = Depends(get_notification_service),
    achievement_service: AchievementService = Depends(get_achievement_service),
) -> WorkoutService:
    return WorkoutService(
        workout_repo=workout_repo,
        exercise_repo=exercise_repo,
        notification_service=notification_service,
        achievement_service=achievement_service,
    )

