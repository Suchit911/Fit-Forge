from fastapi import APIRouter, Depends, HTTPException, status
from ....core.security import get_current_user, CurrentUser
from ....schemas.user import UserProfileSchema, UserProfileCreate, UserProfileUpdate
from ....repositories.user_repository import UserRepository, get_user_repository
from ....services.notification_service import NotificationService, get_notification_service
from ....utils.logger import logger

router = APIRouter()


@router.get("/me", response_model=UserProfileSchema, summary="Get current user profile")
async def get_my_profile(
    current_user: CurrentUser = Depends(get_current_user),
    repo: UserRepository = Depends(get_user_repository),
    notification_service: NotificationService = Depends(get_notification_service),
):
    """
    Retrieves the Firestore profile document for the authenticated Firebase user.
    The UID is strictly determined from the verified Firebase ID token.
    If no profile document exists yet, auto-initializes a default profile for the user.
    """
    profile = repo.get_by_uid(current_user.uid)
    if not profile:
        logger.info(f"Auto-initializing default profile for new user UID: {current_user.uid}")
        fallback_name = current_user.name or (
            current_user.email.split("@")[0].title() if current_user.email else "Athlete"
        )
        profile_in = UserProfileCreate(
            name=fallback_name,
            email=current_user.email or "user@example.com",
            profile_complete=False,
        )
        profile = repo.create(
            uid=current_user.uid,
            email=current_user.email or "user@example.com",
            profile_in=profile_in,
        )
        try:
            notification_service.create_welcome_notification(current_user.uid)
        except Exception as e:
            logger.warning(f"Failed to create welcome notification for user {current_user.uid}: {e}")

    return profile


@router.post(
    "/me",
    response_model=UserProfileSchema,
    status_code=status.HTTP_201_CREATED,
    summary="Create or initialize user profile",
)
async def create_my_profile(
    profile_in: UserProfileCreate,
    current_user: CurrentUser = Depends(get_current_user),
    repo: UserRepository = Depends(get_user_repository),
    notification_service: NotificationService = Depends(get_notification_service),
):
    """
    Creates a new user profile document at users/{firebase_uid}.
    Any UID supplied in request body is ignored; the authenticated Firebase UID is enforced.
    """
    # If profile already exists, update it or return existing
    existing = repo.get_by_uid(current_user.uid)
    if existing:
        updates = UserProfileUpdate(**profile_in.model_dump())
        updated = repo.update(current_user.uid, updates)
        return updated or existing

    created = repo.create(
        uid=current_user.uid,
        email=current_user.email or profile_in.email or "user@example.com",
        profile_in=profile_in,
    )
    try:
        notification_service.create_welcome_notification(current_user.uid)
    except Exception as e:
        logger.warning(f"Failed to create welcome notification for user {current_user.uid}: {e}")

    return created


@router.patch("/me", response_model=UserProfileSchema, summary="Partially update current user profile")
async def update_my_profile(
    updates: UserProfileUpdate,
    current_user: CurrentUser = Depends(get_current_user),
    repo: UserRepository = Depends(get_user_repository),
):
    """
    Partially updates the Firestore profile for the authenticated Firebase user.
    Cross-user modification is prevented by design because only current_user.uid is targeted.
    """
    # Ensure profile exists first
    existing = repo.get_by_uid(current_user.uid)
    if not existing:
        # Create initial profile with updates applied
        dump = updates.model_dump(exclude_unset=True, exclude_none=True)
        fallback_name = dump.pop("name", None) or current_user.name or "Athlete"
        dump.pop("email", None)
        profile_complete = dump.pop("profile_complete", False)
        create_payload = UserProfileCreate(
            name=fallback_name,
            email=current_user.email or "user@example.com",
            profile_complete=profile_complete,
            **dump,
        )
        return repo.create(current_user.uid, current_user.email or "user@example.com", create_payload)

    updated = repo.update(current_user.uid, updates)
    if not updated:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="User profile not found.",
        )
    return updated


@router.put("/me", response_model=UserProfileSchema, summary="Update current user profile")
async def replace_my_profile(
    updates: UserProfileUpdate,
    current_user: CurrentUser = Depends(get_current_user),
    repo: UserRepository = Depends(get_user_repository),
):
    """
    Updates the Firestore profile for the authenticated Firebase user.
    """
    return await update_my_profile(updates, current_user, repo)
