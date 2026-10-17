from typing import Optional
from fastapi import APIRouter, Depends, HTTPException, Query, status
from ....core.security import get_current_user, CurrentUser
from ....schemas.notification import (
    NotificationItemSchema,
    NotificationsDashboardDataSchema,
    NotificationUnreadCountResponse,
    NotificationMarkAllReadResponse,
)
from ....services.notification_service import NotificationService, get_notification_service

router = APIRouter()


@router.get("", response_model=NotificationsDashboardDataSchema, summary="Get notifications dashboard")
async def get_notifications_dashboard(
    limit: int = Query(50, ge=1, le=100, description="Max notifications in feed"),
    before: Optional[str] = Query(None, description="Cursor for pagination"),
    current_user: CurrentUser = Depends(get_current_user),
    service: NotificationService = Depends(get_notification_service),
):
    """
    Retrieves full notifications dashboard payload for verified user UID:
    - Accurate unreadCount, todayCount, weekCount, importantCount across all user notifications
    - Paginated feed ordered by createdAt DESC
    - Category insights and important updates
    - Default notification preferences
    """
    return service.get_dashboard_data(current_user.uid, limit=limit, before=before)


@router.get("/unread-count", response_model=NotificationUnreadCountResponse, summary="Get unread notifications count")
async def get_unread_count(
    current_user: CurrentUser = Depends(get_current_user),
    service: NotificationService = Depends(get_notification_service),
):
    """
    Lightweight endpoint for periodic polling of unread notification counter.
    """
    count = service.get_unread_count(current_user.uid)
    return NotificationUnreadCountResponse(unreadCount=count)


@router.patch("/{notification_id}/read", response_model=NotificationItemSchema, summary="Mark notification as read")
async def mark_notification_read(
    notification_id: str,
    current_user: CurrentUser = Depends(get_current_user),
    service: NotificationService = Depends(get_notification_service),
):
    """
    Marks a single notification as read. Idempotent.
    Returns 404 if notification not found or belongs to another user.
    """
    updated = service.mark_as_read(current_user.uid, notification_id)
    if not updated:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Notification with ID '{notification_id}' not found.",
        )
    return updated


@router.post("/read-all", response_model=NotificationMarkAllReadResponse, summary="Mark all notifications as read")
async def mark_all_notifications_read(
    current_user: CurrentUser = Depends(get_current_user),
    service: NotificationService = Depends(get_notification_service),
):
    """
    Marks all notifications for the authenticated user as read. Idempotent.
    """
    unread_count, marked_count = service.mark_all_as_read(current_user.uid)
    return NotificationMarkAllReadResponse(unreadCount=unread_count, markedCount=marked_count)
