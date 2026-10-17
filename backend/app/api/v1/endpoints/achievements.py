from typing import Optional, List
from fastapi import APIRouter, Depends, status
from ....core.security import get_current_user, CurrentUser
from ....schemas.achievement import (
    AchievementsDashboardDataSchema,
    AchievementDefinitionSchema,
    CustomAchievementCreateSchema,
    AchievementDetailSchema,
)
from ....services.achievement_service import AchievementService, get_achievement_service
from ....repositories.achievement_repository import AchievementRepository, get_achievement_repository

router = APIRouter()


@router.get(
    "",
    response_model=AchievementsDashboardDataSchema,
    summary="Get user achievements dashboard summary",
    description="Evaluates achievements deterministically and returns complete dashboard data.",
)
async def get_achievements_dashboard(
    current_user: CurrentUser = Depends(get_current_user),
    service: AchievementService = Depends(get_achievement_service),
) -> AchievementsDashboardDataSchema:
    return service.get_dashboard_data(current_user.uid)


@router.post(
    "/evaluate",
    response_model=List[AchievementDefinitionSchema],
    summary="Evaluate achievements and return newly unlocked milestones",
    description="Idempotent evaluation trigger returning newly unlocked badges.",
)
async def evaluate_achievements(
    current_user: CurrentUser = Depends(get_current_user),
    service: AchievementService = Depends(get_achievement_service),
) -> List[AchievementDefinitionSchema]:
    _, newly_unlocked = service.evaluate_user_achievements(current_user.uid)
    return newly_unlocked


@router.post(
    "/custom",
    response_model=AchievementsDashboardDataSchema,
    status_code=status.HTTP_201_CREATED,
    summary="Create custom achievement milestone",
    description="Adds a user-created milestone record and returns updated dashboard data.",
)
async def create_custom_achievement(
    payload: CustomAchievementCreateSchema,
    current_user: CurrentUser = Depends(get_current_user),
    service: AchievementService = Depends(get_achievement_service),
    repo: AchievementRepository = Depends(get_achievement_repository),
) -> AchievementsDashboardDataSchema:
    repo.create_custom_achievement(
        uid=current_user.uid,
        name=payload.name,
        description=payload.description,
        category=payload.category,
    )
    return service.get_dashboard_data(current_user.uid)


@router.get(
    "/list",
    response_model=List[AchievementDetailSchema],
    summary="List all achievements with user progress and unlock state",
    description="Returns detailed list of all system and custom achievements with category filter support.",
)
async def list_all_achievements(
    category: Optional[str] = None,
    current_user: CurrentUser = Depends(get_current_user),
    service: AchievementService = Depends(get_achievement_service),
) -> List[AchievementDetailSchema]:
    return service.list_all_achievement_details(current_user.uid, category=category)


@router.post(
    "/clear-new",
    status_code=status.HTTP_204_NO_CONTENT,
    summary="Acknowledge newly unlocked achievements",
    description="Clears the isNew flag so badges do not remain permanently marked as new.",
)
async def clear_new_achievements(
    current_user: CurrentUser = Depends(get_current_user),
    repo: AchievementRepository = Depends(get_achievement_repository),
) -> None:
    repo.clear_is_new(current_user.uid)
