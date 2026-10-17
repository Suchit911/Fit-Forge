from typing import Optional, List
from fastapi import APIRouter, Depends, HTTPException, Query, status

from ....core.security import get_current_user, CurrentUser
from ....schemas.coach import (
    CoachConversationSchema,
    ConversationSummarySchema,
    CoachMessageSchema,
    CoachMessageResponse,
    CreateConversationRequest,
    SendCoachMessageRequest,
)
from ....services.coach_service import CoachService, get_coach_service
from ....services.llm_client import (
    LLMConfigError,
    LLMTimeoutError,
    LLMRateLimitError,
    LLMUnavailableError,
    LLMResponseError,
)
from ....utils.logger import logger

router = APIRouter()


@router.post(
    "/conversations",
    response_model=CoachConversationSchema,
    status_code=status.HTTP_201_CREATED,
    summary="Create a new conversation thread",
)
async def create_conversation(
    payload: Optional[CreateConversationRequest] = None,
    current_user: CurrentUser = Depends(get_current_user),
    service: CoachService = Depends(get_coach_service),
):
    """
    Creates an empty conversation thread under users/{verified_uid}/coach_conversations.
    Ownership is strictly bound to the verified Firebase token UID.
    """
    title = payload.title if payload else None
    initial_msg = payload.initialMessage if payload else None
    try:
        conv = service.create_conversation(
            uid=current_user.uid,
            title=title,
            initial_message=initial_msg,
        )
        return conv
    except Exception as e:
        logger.error(f"Failed to create conversation for user {current_user.uid}: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to create conversation thread.",
        )


@router.get(
    "/conversations",
    response_model=List[ConversationSummarySchema],
    summary="List conversations for authenticated user",
)
async def list_conversations(
    limit: int = Query(20, ge=1, le=50, description="Max conversations to return"),
    current_user: CurrentUser = Depends(get_current_user),
    service: CoachService = Depends(get_coach_service),
):
    """
    Lists conversations for the authenticated user ordered by updatedAt descending.
    Capped at configured retention limit (default 20).
    """
    return service.list_conversations(current_user.uid, limit=limit)


@router.get(
    "/conversations/{conversation_id}/messages",
    response_model=List[CoachMessageSchema],
    summary="Get message history for a conversation",
)
async def get_messages(
    conversation_id: str,
    limit: int = Query(50, ge=1, le=100, description="Max messages to return"),
    current_user: CurrentUser = Depends(get_current_user),
    service: CoachService = Depends(get_coach_service),
):
    """
    Retrieves chronological message history for a conversation owned by the verified user.
    Returns 404 if the conversation does not exist or belongs to another user.
    """
    conv = service.get_conversation(current_user.uid, conversation_id)
    if not conv:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Conversation with ID '{conversation_id}' not found.",
        )
    return service.get_messages(current_user.uid, conversation_id, limit=limit)


@router.delete(
    "/conversations/{conversation_id}",
    summary="Delete a conversation and its messages",
)
async def delete_conversation(
    conversation_id: str,
    current_user: CurrentUser = Depends(get_current_user),
    service: CoachService = Depends(get_coach_service),
):
    """
    Deletes a conversation and its messages.
    Returns 404 if the conversation does not exist or belongs to another user.
    """
    success = service.delete_conversation(current_user.uid, conversation_id)
    if not success:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Conversation with ID '{conversation_id}' not found.",
        )
    return {"success": True, "id": conversation_id}


@router.post(
    "/chat",
    response_model=CoachMessageResponse,
    summary="Send a message to AI Fitness Coach",
)
async def chat(
    payload: SendCoachMessageRequest,
    current_user: CurrentUser = Depends(get_current_user),
    service: CoachService = Depends(get_coach_service),
):
    """
    Core interactive endpoint for AI Fitness Coach:
    1. Validates message length and content
    2. Enforces application-level rate limits (10/min, 50/day)
    3. Resolves conversation (auto-creates thread if omitted)
    4. Assembles bounded CoachContext from domain repositories
    5. Retrieves recent conversation history
    6. Constructs XML-bounded prompt
    7. Calls Gemini 2.5 Flash provider
    8. Persists user & assistant messages on successful response
    9. Returns CoachMessageResponse with conversation metadata
    """
    target_cid = payload.conversation_id or payload.conversationId
    try:
        return await service.send_message(
            uid=current_user.uid,
            message=payload.message,
            conversation_id=target_cid,
        )
    except KeyError as e:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=str(e).strip("'\""),
        )
    except ValueError as e:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail=str(e),
        )
    except LLMRateLimitError as e:
        logger.warning(f"Rate limit triggered for user {current_user.uid}: {e.message}")
        headers = {}
        if getattr(e, "retry_after", None):
            headers["Retry-After"] = str(int(e.retry_after))
        raise HTTPException(
            status_code=status.HTTP_429_TOO_MANY_REQUESTS,
            detail=e.message,
            headers=headers if headers else None,
        )
    except LLMConfigError as e:
        logger.error(f"LLM configuration error: {e.message}")
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail=e.message,
        )
    except LLMTimeoutError as e:
        logger.error(f"LLM request timed out: {e.message}")
        raise HTTPException(
            status_code=status.HTTP_504_GATEWAY_TIMEOUT,
            detail=e.message,
        )
    except (LLMUnavailableError, LLMResponseError) as e:
        logger.error(f"LLM provider error ({type(e).__name__}): {e.message}")
        raise HTTPException(
            status_code=status.HTTP_502_BAD_GATEWAY,
            detail=e.message,
        )
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Unhandled error in Coach chat endpoint: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="An unexpected error occurred while communicating with the AI Coach.",
        )
