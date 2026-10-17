from fastapi import APIRouter, Depends, HTTPException, status
from ....core.security import get_current_user, CurrentUser
from ....schemas.settings import (
    UserSettingsSchema,
    UserSettingsUpdateSchema,
)
from ....repositories.settings_repository import (
    SettingsRepository,
    get_settings_repository,
    PersistenceError,
)
from ....utils.logger import logger


router = APIRouter()


@router.get(
    "",
    response_model=UserSettingsSchema,
    summary="Get authenticated user's settings",
)
async def get_settings(
    current_user: CurrentUser = Depends(get_current_user),
    repo: SettingsRepository = Depends(get_settings_repository),
) -> UserSettingsSchema:
    """
    Retrieves the persisted settings for the authenticated Firebase user.
    The user identity is derived strictly from the verified Firebase ID token context.
    If no settings record exists yet, returns deterministic first-read defaults
    with persisted=False without falsely claiming pre-existing persistence.
    """
    try:
        return repo.get_or_default(current_user.uid)
    except PersistenceError as pe:
        logger.error(f"Persistence error fetching settings for user {current_user.uid}: {pe}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to read user settings from storage.",
        )


@router.patch(
    "",
    response_model=UserSettingsSchema,
    summary="Partially update authenticated user's settings",
)
async def update_settings(
    updates: UserSettingsUpdateSchema,
    current_user: CurrentUser = Depends(get_current_user),
    repo: SettingsRepository = Depends(get_settings_repository),
) -> UserSettingsSchema:
    """
    Partially updates the authenticated user's settings.
    - User identity is strictly derived from verified token context.
    - Omitted fields retain their existing persisted values.
    - Unknown or prohibited fields are strictly rejected.
    - Changes are durably persisted to Cloud Firestore.
    """
    try:
        updated = repo.update(current_user.uid, updates)
        return updated
    except PersistenceError as pe:
        logger.error(f"Persistence error updating settings for user {current_user.uid}: {pe}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to persist user settings update.",
        )
    except ValueError as ve:
        logger.warning(f"Validation error updating settings for user {current_user.uid}: {ve}")
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(ve),
        )
