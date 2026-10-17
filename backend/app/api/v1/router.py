from fastapi import APIRouter
from .endpoints.health import router as health_router
from .endpoints.users import router as users_router
from .endpoints.exercise_relationships import router as exercise_relationships_router
from .endpoints.exercise_recommendations import router as exercise_recommendations_router
from .endpoints.exercises import router as exercises_router
from .endpoints.workouts import router as workouts_router
from .endpoints.progress import router as progress_router
from .endpoints.nutrition import router as nutrition_router
from .endpoints.achievements import router as achievements_router
from .endpoints.notifications import router as notifications_router
from .endpoints.coach import router as coach_router
from .endpoints.form_analysis import router as form_analysis_router
from .endpoints.workout_plans import router as workout_plans_router
from .endpoints.personalization import router as personalization_router
from .endpoints.programs import router as programs_router
from .endpoints.settings import router as settings_router

api_router = APIRouter()

# Core health routes
api_router.include_router(health_router)

# User Profile routes (Phase 2)
api_router.include_router(users_router, prefix="/users", tags=["Users"])

# Settings routes (Stage 5)
api_router.include_router(settings_router, prefix="/settings", tags=["Settings"])

# Exercise Relationships routes (Phase 9B.8.3) - registered before /exercises to avoid route shadowing
api_router.include_router(exercise_relationships_router, prefix="/exercises/relationships", tags=["Exercise Relationships"])

# Exercise Recommendations routes (Phase 9B.8.4) - registered before /exercises to avoid route shadowing
api_router.include_router(exercise_recommendations_router, prefix="/exercises/recommendations", tags=["Exercise Recommendations"])

# Exercises routes (Phase 3)
api_router.include_router(exercises_router, prefix="/exercises", tags=["Exercises"])

# Workouts routes (Phase 3)
api_router.include_router(workouts_router, prefix="/workouts", tags=["Workouts"])

# Progress & Analytics routes (Phase 4)
api_router.include_router(progress_router, prefix="/progress", tags=["Progress"])

# Nutrition routes (Phase 5)
api_router.include_router(nutrition_router, prefix="/nutrition", tags=["Nutrition"])

# Achievements & Badges routes (Phase 6)
api_router.include_router(achievements_router, prefix="/achievements", tags=["Achievements"])

# Notifications routes (Phase 7)
api_router.include_router(notifications_router, prefix="/notifications", tags=["Notifications"])

# AI Coach routes (Phase 8D)
api_router.include_router(coach_router, prefix="/coach", tags=["AI Coach"])

# AI Form Analysis routes (Phase 9A)
api_router.include_router(form_analysis_router, prefix="/form-analysis", tags=["Form Analysis"])

# Workout Plans routes (Phase 9B.8.5.4)
api_router.include_router(workout_plans_router, prefix="/workout-plans", tags=["Workout Plans"])

# Personalization Signals & Adaptive Analytics (Phase 9C.1)
api_router.include_router(personalization_router, prefix="/personalization", tags=["Personalization Signals"])

# Active Programs & Mesocycles Lifecycle (Phase 9C.3)
api_router.include_router(programs_router, prefix="/programs", tags=["Programs"])


