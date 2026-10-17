"""
Data Repositories Layer
Abstracts Cloud Firestore collections:
- users
- workouts
- exercises
- nutrition_logs
- progress_records
- achievements
- notifications
- form_analysis_sessions (Phase 9B.7)
"""

from .form_analysis_repository import FormAnalysisRepository, get_form_analysis_repository
from .workout_repository import WorkoutRepository, get_workout_repository
from .exercise_repository import ExerciseRepository, get_exercise_repository
from .user_repository import UserRepository, get_user_repository
from .nutrition_repository import NutritionRepository, get_nutrition_repository
from .notification_repository import NotificationRepository, get_notification_repository
from .settings_repository import SettingsRepository, get_settings_repository, PersistenceError

__all__ = [
    "FormAnalysisRepository",
    "get_form_analysis_repository",
    "WorkoutRepository",
    "get_workout_repository",
    "ExerciseRepository",
    "get_exercise_repository",
    "UserRepository",
    "get_user_repository",
    "NutritionRepository",
    "get_nutrition_repository",
    "NotificationRepository",
    "get_notification_repository",
    "SettingsRepository",
    "get_settings_repository",
    "PersistenceError",
]

