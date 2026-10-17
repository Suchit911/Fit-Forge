"""
Dedicated Router Module for Workout Plans (Phase 9B.8.5.4).

Re-exports the router from backend.app.api.v1.endpoints.workout_plans
to provide a dedicated top-level router location consistent with specification.
"""

from .endpoints.workout_plans import router

__all__ = ["router"]
