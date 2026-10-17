import pytest
from unittest.mock import AsyncMock
from fastapi.testclient import TestClient

from backend.app.main import app
from backend.app.core.security import get_current_user, CurrentUser
from backend.app.repositories.coach_repository import CoachRepository
from backend.app.services.coach_context_service import CoachContextService
from backend.app.services.llm_client import (
    MockLLMClient,
    LLMConfigError,
    LLMTimeoutError,
    LLMRateLimitError,
    LLMUnavailableError,
    LLMResponseError,
)
from backend.app.services.coach_service import CoachService, CoachRateLimiter, get_coach_service
from backend.app.schemas.coach import (
    CoachContext,
    CoachProfileContext,
    CoachSettingsSchema,
    CoachRecentActivityContext,
    CoachNutritionContext,
    CoachAchievementsContext,
)


# =============================================================================
# FIXTURES
# =============================================================================

@pytest.fixture
def mock_coach_repo():
    return CoachRepository(db=None)


@pytest.fixture
def mock_coach_context_service():
    service = CoachContextService()

    async def mock_assemble(uid: str) -> CoachContext:
        return CoachContext(
            profile=CoachProfileContext(name="Jordan", goal="Muscle Gain", targetCalories=2700),
            preferences=CoachSettingsSchema(tone="encouraging", focus="hypertrophy"),
            recentActivity=CoachRecentActivityContext(activeStreak=5, workoutsCompletedThisWeek=4),
            todayNutrition=CoachNutritionContext(consumedCalories=2000, targetCalories=2700),
            achievements=CoachAchievementsContext(totalPoints=1500, level=6),
        )

    service.assemble_coach_context = AsyncMock(side_effect=mock_assemble)
    return service


@pytest.fixture
def mock_coach_llm():
    return MockLLMClient(default_response="Aim for 8-12 reps with 2-3 minutes of rest for compound lifts!")


@pytest.fixture
def test_rate_limiter():
    limiter = CoachRateLimiter(max_per_minute=10, max_per_day=50)
    limiter.reset()
    return limiter


@pytest.fixture
def active_coach_service(mock_coach_repo, mock_coach_context_service, mock_coach_llm, test_rate_limiter):
    return CoachService(
        repo=mock_coach_repo,
        context_service=mock_coach_context_service,
        llm_client=mock_coach_llm,
        rate_limiter=test_rate_limiter,
    )


@pytest.fixture(autouse=True)
def setup_dependencies(active_coach_service):
    app.dependency_overrides.clear()
    app.dependency_overrides[get_coach_service] = lambda: active_coach_service
    app.dependency_overrides[get_current_user] = lambda: CurrentUser(
        uid="test_user_primary",
        email="primary@example.com",
        name="Jordan",
        email_verified=True,
    )
    yield
    app.dependency_overrides.clear()


# =============================================================================
# 1. AUTHENTICATION & SECURITY TESTS
# =============================================================================

def test_coach_conversations_missing_auth_header_rejected(client: TestClient):
    """Verifies GET /api/v1/coach/conversations rejects requests missing Authorization header."""
    app.dependency_overrides.pop(get_current_user, None)
    res = client.get("/api/v1/coach/conversations")
    assert res.status_code == 401
    assert "Missing Bearer" in res.json()["detail"]


def test_coach_conversations_invalid_token_rejected(client: TestClient):
    """Verifies GET /api/v1/coach/conversations rejects invalid tokens."""
    app.dependency_overrides.pop(get_current_user, None)
    res = client.get("/api/v1/coach/conversations", headers={"Authorization": "Bearer bad_token"})
    assert res.status_code == 401


def test_coach_chat_missing_auth_header_rejected(client: TestClient):
    """Verifies POST /api/v1/coach/chat rejects unauthenticated requests."""
    app.dependency_overrides.pop(get_current_user, None)
    res = client.post("/api/v1/coach/chat", json={"message": "Hello Coach!"})
    assert res.status_code == 401


# =============================================================================
# 2. CONVERSATION ENDPOINT TESTS
# =============================================================================

def test_create_conversation_endpoint(client: TestClient):
    """Verifies POST /api/v1/coach/conversations creates a thread with server-generated metadata."""
    res = client.post("/api/v1/coach/conversations", json={"title": "Hypertrophy Push Split"})
    assert res.status_code == 201
    data = res.json()
    assert data["id"].startswith("conv_")
    assert data["title"] == "Hypertrophy Push Split"
    assert data["messageCount"] == 0
    assert data["previewText"] == ""


def test_create_conversation_with_initial_message(client: TestClient):
    """Verifies initialMessage sets deterministic title if title is omitted."""
    res = client.post(
        "/api/v1/coach/conversations",
        json={"initialMessage": "What are the best mobility exercises for hips?"},
    )
    assert res.status_code == 201
    data = res.json()
    assert "mobility exercises" in data["title"].lower() or "what are" in data["title"].lower()


def test_list_conversations_endpoint(client: TestClient):
    """Verifies GET /api/v1/coach/conversations lists user's conversations with display fields."""
    client.post("/api/v1/coach/conversations", json={"title": "First Thread"})
    client.post("/api/v1/coach/conversations", json={"title": "Second Thread"})

    res = client.get("/api/v1/coach/conversations")
    assert res.status_code == 200
    convs = res.json()
    assert len(convs) == 2
    assert convs[0]["dateGroup"] == "TODAY"
    assert "timestamp" in convs[0]


def test_get_messages_endpoint(client: TestClient, active_coach_service: CoachService):
    """Verifies GET /api/v1/coach/conversations/{id}/messages returns chronological history."""
    conv = active_coach_service.create_conversation("test_user_primary", title="Chest Routine")
    cid = conv.id

    # Seed messages
    active_coach_service.repo.create_message("test_user_primary", cid, "user", "How to bench press?")
    active_coach_service.repo.create_message("test_user_primary", cid, "assistant", "Keep your scapula retracted.")

    res = client.get(f"/api/v1/coach/conversations/{cid}/messages")
    assert res.status_code == 200
    msgs = res.json()
    assert len(msgs) == 2
    assert msgs[0]["sender"] == "user"
    assert msgs[1]["sender"] == "assistant"


def test_get_messages_nonexistent_conversation_returns_404(client: TestClient):
    """Verifies GET /api/v1/coach/conversations/{id}/messages returns 404 for unknown conversation."""
    res = client.get("/api/v1/coach/conversations/conv_unknown_123/messages")
    assert res.status_code == 404
    assert "not found" in res.json()["detail"].lower()


def test_delete_conversation_endpoint(client: TestClient, active_coach_service: CoachService):
    """Verifies DELETE /api/v1/coach/conversations/{id} deletes conversation."""
    conv = active_coach_service.create_conversation("test_user_primary", title="To Be Removed")
    cid = conv.id

    res = client.delete(f"/api/v1/coach/conversations/{cid}")
    assert res.status_code == 200
    assert res.json()["success"] is True

    # Subsequent get returns 404
    res_get = client.get(f"/api/v1/coach/conversations/{cid}/messages")
    assert res_get.status_code == 404


def test_delete_nonexistent_conversation_returns_404(client: TestClient):
    """Verifies DELETE on unknown conversation returns 404."""
    res = client.delete("/api/v1/coach/conversations/conv_nonexistent_999")
    assert res.status_code == 404


# =============================================================================
# 3. CHAT ENDPOINT TESTS
# =============================================================================

def test_chat_auto_creates_conversation_when_omitted(client: TestClient):
    """Verifies POST /api/v1/coach/chat creates conversation if conversation_id is not provided."""
    res = client.post("/api/v1/coach/chat", json={"message": "What is the optimal rest time between deadlift sets?"})
    assert res.status_code == 200
    data = res.json()
    assert "conversationId" in data
    assert data["conversationId"].startswith("conv_")
    assert data["userMessage"]["text"] == "What is the optimal rest time between deadlift sets?"
    assert data["assistantMessage"]["sender"] == "assistant"
    assert "reps" in data["assistantMessage"]["text"].lower() or "rest" in data["assistantMessage"]["text"].lower()


def test_chat_with_existing_conversation(client: TestClient, active_coach_service: CoachService):
    """Verifies POST /api/v1/coach/chat appends to existing conversation."""
    conv = active_coach_service.create_conversation("test_user_primary", title="Deadlift Discussion")
    cid = conv.id

    res = client.post("/api/v1/coach/chat", json={"conversation_id": cid, "message": "Should I wear a belt?"})
    assert res.status_code == 200
    data = res.json()
    assert data["conversationId"] == cid

    # Verify message count
    msgs = active_coach_service.get_messages("test_user_primary", cid)
    assert len(msgs) == 2


def test_chat_supports_camel_case_conversation_id(client: TestClient, active_coach_service: CoachService):
    """Verifies POST /api/v1/coach/chat accepts conversationId in addition to conversation_id."""
    conv = active_coach_service.create_conversation("test_user_primary", title="Camel Case Test")
    cid = conv.id

    res = client.post("/api/v1/coach/chat", json={"conversationId": cid, "message": "How to warm up?"})
    assert res.status_code == 200
    assert res.json()["conversationId"] == cid


def test_chat_nonexistent_conversation_returns_404(client: TestClient):
    """Verifies POST /api/v1/coach/chat returns 404 if conversation_id does not exist."""
    res = client.post("/api/v1/coach/chat", json={"conversation_id": "conv_missing_404", "message": "Hello"})
    assert res.status_code == 404


def test_chat_empty_message_returns_422(client: TestClient):
    """Verifies empty message is rejected with 422 unprocessable entity."""
    res = client.post("/api/v1/coach/chat", json={"message": "   "})
    assert res.status_code == 422


def test_chat_message_exceeding_1000_chars_returns_422(client: TestClient):
    """Verifies message exceeding 1000 characters is rejected with 422."""
    res = client.post("/api/v1/coach/chat", json={"message": "a" * 1001})
    assert res.status_code == 422


# =============================================================================
# 4. APPLICATION RATE LIMITING (HTTP 429)
# =============================================================================

def test_chat_application_rate_limit_exceeded_returns_429(
    client: TestClient, test_rate_limiter: CoachRateLimiter
):
    """Verifies sending >10 messages in a minute triggers HTTP 429."""
    # Send 10 messages
    for i in range(10):
        res = client.post("/api/v1/coach/chat", json={"message": f"Message number {i}"})
        assert res.status_code == 200

    # 11th message returns 429
    res_11 = client.post("/api/v1/coach/chat", json={"message": "Exceeding message"})
    assert res_11.status_code == 429
    assert "rate limit exceeded" in res_11.json()["detail"].lower()


# =============================================================================
# 5. PROVIDER ERROR MAPPINGS
# =============================================================================

def test_chat_missing_gemini_key_maps_to_503(client: TestClient, mock_coach_llm: MockLLMClient):
    """Verifies LLMConfigError is mapped to HTTP 503."""
    mock_coach_llm.set_error(LLMConfigError("Gemini API key is not configured."))
    res = client.post("/api/v1/coach/chat", json={"message": "Test prompt"})
    assert res.status_code == 503
    assert "not configured" in res.json()["detail"]


def test_chat_provider_timeout_maps_to_504(client: TestClient, mock_coach_llm: MockLLMClient):
    """Verifies LLMTimeoutError is mapped to HTTP 504."""
    mock_coach_llm.set_error(LLMTimeoutError("Gemini API timed out after 12s."))
    res = client.post("/api/v1/coach/chat", json={"message": "Test prompt"})
    assert res.status_code == 504
    assert "timed out" in res.json()["detail"].lower()


def test_chat_provider_rate_limit_maps_to_429(client: TestClient, mock_coach_llm: MockLLMClient):
    """Verifies provider quota 429 is mapped to HTTP 429."""
    mock_coach_llm.set_error(LLMRateLimitError("Gemini API quota exceeded."))
    res = client.post("/api/v1/coach/chat", json={"message": "Test prompt"})
    assert res.status_code == 429
    assert "quota" in res.json()["detail"].lower() or "rate limit" in res.json()["detail"].lower()


def test_chat_provider_unavailable_maps_to_502(client: TestClient, mock_coach_llm: MockLLMClient):
    """Verifies provider 5xx is mapped to HTTP 502."""
    mock_coach_llm.set_error(LLMUnavailableError("Gemini API service unavailable."))
    res = client.post("/api/v1/coach/chat", json={"message": "Test prompt"})
    assert res.status_code == 502
    assert "unavailable" in res.json()["detail"].lower()


def test_chat_malformed_response_maps_to_502(client: TestClient, mock_coach_llm: MockLLMClient):
    """Verifies empty or malformed LLM response is mapped to HTTP 502."""
    mock_coach_llm.set_error(LLMResponseError("Gemini returned an empty or blocked response."))
    res = client.post("/api/v1/coach/chat", json={"message": "Test prompt"})
    assert res.status_code == 502


# =============================================================================
# 6. CROSS-USER SECURITY
# =============================================================================

def test_cross_user_security_access_denied(client: TestClient, active_coach_service: CoachService):
    """Verifies User B cannot access, delete, or send messages to User A's conversation."""
    # User A creates a conversation
    conv_a = active_coach_service.create_conversation("test_user_primary", title="User A Confidential")
    cid_a = conv_a.id
    active_coach_service.repo.create_message("test_user_primary", cid_a, "user", "Private stats")

    # Switch identity to User B
    app.dependency_overrides[get_current_user] = lambda: CurrentUser(
        uid="test_user_secondary",
        email="secondary@example.com",
        name="Taylor",
        email_verified=True,
    )

    # User B cannot list messages of User A's conversation
    res_get = client.get(f"/api/v1/coach/conversations/{cid_a}/messages")
    assert res_get.status_code == 404

    # User B cannot delete User A's conversation
    res_del = client.delete(f"/api/v1/coach/conversations/{cid_a}")
    assert res_del.status_code == 404

    # User B cannot send a message into User A's conversation
    res_chat = client.post("/api/v1/coach/chat", json={"conversation_id": cid_a, "message": "Infiltrating"})
    assert res_chat.status_code == 404

    # User B conversation list does not contain User A's conversation
    res_list = client.get("/api/v1/coach/conversations")
    assert res_list.status_code == 200
    assert len(res_list.json()) == 0
