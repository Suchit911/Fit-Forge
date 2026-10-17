import pytest
from datetime import datetime, timezone
from fastapi.testclient import TestClient
from pydantic import ValidationError

from backend.app.main import app
from backend.app.core.config import settings
from backend.app.schemas.coach import (
    CoachSender,
    CoachTone,
    CoachFocus,
    CoachSettingsSchema,
    CoachMessageSchema,
    CoachConversationSchema,
    ConversationSummarySchema,
    CreateConversationRequest,
    SendCoachMessageRequest,
    CoachMessageResponse,
    CoachContext,
    CoachProfileContext,
    CoachRecentActivityContext,
    CoachNutritionContext,
    CoachAchievementsContext,
)
from backend.app.repositories.coach_repository import CoachRepository
from backend.app.services.llm_client import (
    MockLLMClient,
    GeminiLLMClient,
    LLMConfigError,
    LLMTimeoutError,
    LLMRateLimitError,
    LLMUnavailableError,
    LLMResponseError,
)


# =============================================================================
# 1. COACH PYDANTIC SCHEMA TESTS
# =============================================================================

def test_send_coach_message_valid():
    """Verifies valid message text and optional conversationId are accepted."""
    req = SendCoachMessageRequest(conversationId="conv_123", message="How do I improve my squat form?")
    assert req.conversationId == "conv_123"
    assert req.message == "How do I improve my squat form?"


def test_send_coach_message_strips_whitespace():
    """Verifies surrounding whitespace is stripped from message text."""
    req = SendCoachMessageRequest(message="   What should I eat post-workout?   ")
    assert req.message == "What should I eat post-workout?"


def test_send_coach_message_empty_rejected():
    """Verifies completely empty string is rejected with validation error."""
    with pytest.raises(ValidationError) as exc:
        SendCoachMessageRequest(message="")
    assert "Message text cannot be empty or whitespace-only" in str(exc.value)


def test_send_coach_message_whitespace_only_rejected():
    """Verifies whitespace-only string is rejected with validation error."""
    with pytest.raises(ValidationError) as exc:
        SendCoachMessageRequest(message="    \n   \t  ")
    assert "Message text cannot be empty or whitespace-only" in str(exc.value)


def test_send_coach_message_exceeding_1000_chars_rejected():
    """Verifies messages exceeding 1000 characters are rejected cleanly."""
    long_text = "a" * 1001
    with pytest.raises(ValidationError) as exc:
        SendCoachMessageRequest(message=long_text)
    assert "Message text cannot exceed 1000 characters" in str(exc.value)


def test_send_coach_message_invalid_conversation_id_rejected():
    """Verifies invalid conversation ID formats are rejected."""
    with pytest.raises(ValidationError) as exc:
        SendCoachMessageRequest(conversationId="conv/invalid$chars!", message="Valid message")
    assert "Conversation ID contains invalid characters" in str(exc.value)


def test_create_conversation_request_validation():
    """Verifies CreateConversationRequest validates title and initialMessage."""
    req = CreateConversationRequest(title="Hypertrophy Split", initialMessage="  Plan my 4-day split  ")
    assert req.title == "Hypertrophy Split"
    assert req.initialMessage == "Plan my 4-day split"

    # Excessively long message rejected
    with pytest.raises(ValidationError):
        CreateConversationRequest(initialMessage="x" * 1001)


def test_coach_message_schema_sender_validation():
    """Verifies valid senders are accepted and invalid senders rejected."""
    msg_user = CoachMessageSchema(
        id="m1",
        conversationId="c1",
        sender="user",
        text="Hello",
        createdAt=datetime.now(timezone.utc).isoformat(),
    )
    assert msg_user.sender == "user"

    msg_assistant = CoachMessageSchema(
        id="m2",
        conversationId="c1",
        sender="assistant",
        text="Hi, I am your coach",
        createdAt=datetime.now(timezone.utc).isoformat(),
    )
    assert msg_assistant.sender == "assistant"

    with pytest.raises(ValidationError):
        CoachMessageSchema(
            id="m3",
            conversationId="c1",
            sender="admin",  # Invalid sender
            text="Invalid sender",
            createdAt=datetime.now(timezone.utc).isoformat(),
        )


def test_coach_settings_schema():
    """Verifies CoachSettingsSchema accepts valid tones and focuses."""
    settings_obj = CoachSettingsSchema(tone="scientific", focus="hypertrophy")
    assert settings_obj.tone == "scientific"
    assert settings_obj.focus == "hypertrophy"

    with pytest.raises(ValidationError):
        CoachSettingsSchema(tone="aggressive")  # Invalid tone


def test_coach_context_schema():
    """Verifies bounded user context builds cleanly with defaults and populated data."""
    ctx = CoachContext(
        profile=CoachProfileContext(name="Alex", goal="Muscle Gain", targetCalories=2500),
        preferences=CoachSettingsSchema(tone="encouraging", focus="hypertrophy"),
        recentActivity=CoachRecentActivityContext(
            activeStreak=4,
            workoutsCompletedThisWeek=3,
            totalRecentVolumeKg=12500.0,
            latestWorkoutTitle="Push Day Hypertrophy",
            recentPRs=["Bench Press: 100kg"],
        ),
        todayNutrition=CoachNutritionContext(consumedCalories=1800, targetCalories=2500, consumedProteinGrams=140.0),
        achievements=CoachAchievementsContext(totalPoints=1200, level=5, latestBadge="first_pr"),
    )
    assert ctx.profile.name == "Alex"
    assert ctx.recentActivity.activeStreak == 4
    assert ctx.todayNutrition.consumedProteinGrams == 140.0
    assert ctx.achievements.level == 5


# =============================================================================
# 2. REPOSITORY FOUNDATION & CROSS-USER ISOLATION TESTS
# =============================================================================

@pytest.fixture
def coach_repo():
    return CoachRepository(db=None)


def test_coach_repo_create_and_get_conversation(coach_repo: CoachRepository):
    """Verifies conversation creation and retrieval under user scope."""
    uid = "test_user_alpha"
    conv = coach_repo.create_conversation(uid=uid, title="Push Pull Legs Advice", initial_preview="How to split?")
    assert conv["id"].startswith("conv_")
    assert conv["title"] == "Push Pull Legs Advice"
    assert conv["previewText"] == "How to split?"
    assert conv["messageCount"] == 0

    fetched = coach_repo.get_conversation(uid, conv["id"])
    assert fetched is not None
    assert fetched["id"] == conv["id"]
    assert fetched["title"] == "Push Pull Legs Advice"


def test_coach_repo_list_conversations_ordered(coach_repo: CoachRepository):
    """Verifies conversations are listed ordered by updatedAt descending."""
    uid = "test_user_alpha"
    conv1 = coach_repo.create_conversation(uid, title="First Chat")
    conv2 = coach_repo.create_conversation(uid, title="Second Chat")

    convs = coach_repo.list_conversations(uid)
    assert len(convs) == 2
    # Newest conversation should appear first
    assert convs[0]["id"] == conv2["id"]


def test_coach_repo_create_and_list_messages(coach_repo: CoachRepository):
    """Verifies message creation increments conversation count and lists in chronological order."""
    uid = "test_user_alpha"
    conv = coach_repo.create_conversation(uid, title="Chest Workout")
    cid = conv["id"]

    m1 = coach_repo.create_message(uid, cid, sender="user", text="What is best for upper chest?")
    m2 = coach_repo.create_message(uid, cid, sender="assistant", text="Incline dumbbell press is optimal.")

    messages = coach_repo.list_messages(uid, cid)
    assert len(messages) == 2
    assert messages[0]["id"] == m1["id"]
    assert messages[0]["sender"] == "user"
    assert messages[1]["id"] == m2["id"]
    assert messages[1]["sender"] == "assistant"

    # Verify conversation metadata was updated
    updated_conv = coach_repo.get_conversation(uid, cid)
    assert updated_conv["messageCount"] == 2
    assert "Incline dumbbell press" in updated_conv["previewText"]


def test_coach_repo_cross_user_isolation(coach_repo: CoachRepository):
    """Verifies User B cannot access, list, or delete User A's conversations."""
    uid_a = "user_alpha"
    uid_b = "user_beta"

    conv_a = coach_repo.create_conversation(uid_a, title="User A Private Chat")
    cid_a = conv_a["id"]
    coach_repo.create_message(uid_a, cid_a, sender="user", text="Private user A message")

    # User B cannot get User A's conversation
    assert coach_repo.get_conversation(uid_b, cid_a) is None

    # User B cannot list User A's messages
    assert coach_repo.list_messages(uid_b, cid_a) == []

    # User B conversation list is empty
    assert coach_repo.list_conversations(uid_b) == []

    # User B cannot delete User A's conversation
    assert coach_repo.delete_conversation(uid_b, cid_a) is False

    # User A's conversation remains intact
    assert coach_repo.get_conversation(uid_a, cid_a) is not None


def test_coach_repo_delete_conversation(coach_repo: CoachRepository):
    """Verifies conversation and messages are removed on deletion."""
    uid = "user_alpha"
    conv = coach_repo.create_conversation(uid, title="To Be Deleted")
    cid = conv["id"]
    coach_repo.create_message(uid, cid, sender="user", text="Temp message")

    assert coach_repo.delete_conversation(uid, cid) is True
    assert coach_repo.get_conversation(uid, cid) is None
    assert coach_repo.list_messages(uid, cid) == []


# =============================================================================
# 3. LLM PROVIDER ABSTRACTION TESTS
# =============================================================================

@pytest.mark.asyncio
async def test_mock_llm_client_generates_response():
    """Verifies MockLLMClient returns canned response and tracks calls with 0 external network requests."""
    client = MockLLMClient(default_response="Personalized fitness advice")
    assert client.is_configured() is True

    response = await client.generate_response(prompt="How much rest between sets?")
    assert response == "Personalized fitness advice"
    assert client.call_count == 1
    assert client.last_prompt == "How much rest between sets?"


@pytest.mark.asyncio
async def test_mock_llm_client_error_injection():
    """Verifies MockLLMClient properly raises injected errors for fault-tolerance testing."""
    client = MockLLMClient()

    # Timeout injection
    client.set_error(LLMTimeoutError("Request timed out after 12s"))
    with pytest.raises(LLMTimeoutError) as exc:
        await client.generate_response("Test prompt")
    assert exc.value.status_code == 504

    # Rate limit injection
    client.set_error(LLMRateLimitError("Quota exceeded"))
    with pytest.raises(LLMRateLimitError) as exc:
        await client.generate_response("Test prompt")
    assert exc.value.status_code == 429

    # Service unavailable injection
    client.set_error(LLMUnavailableError("Service 503"))
    with pytest.raises(LLMUnavailableError) as exc:
        await client.generate_response("Test prompt")
    assert exc.value.status_code == 502


@pytest.mark.asyncio
async def test_gemini_llm_client_unconfigured_raises_cleanly(monkeypatch):
    """Verifies GeminiLLMClient raises LLMConfigError when api_key is None without crashing."""
    monkeypatch.setattr(settings, "GEMINI_API_KEY", None)
    gemini_client = GeminiLLMClient(api_key=None)
    assert gemini_client.is_configured() is False

    with pytest.raises(LLMConfigError) as exc:
        await gemini_client.generate_response("Test prompt")
    assert exc.value.status_code == 503
    assert "Gemini API key is not configured" in exc.value.message


# =============================================================================
# 4. CONFIGURATION & HEALTH SAFETY TESTS
# =============================================================================

def test_config_coach_settings():
    """Verifies safe defaults for future Gemini integration and Coach limits."""
    assert isinstance(settings.GEMINI_MODEL, str) and settings.GEMINI_MODEL.startswith("gemini-")
    assert settings.COACH_MAX_MESSAGES_PER_MINUTE == 10
    assert settings.COACH_MAX_MESSAGES_PER_DAY == 50
    assert settings.COACH_MAX_CONVERSATIONS_PER_USER == 20
    assert settings.COACH_MAX_MESSAGES_PER_CONVERSATION == 50
    assert settings.COACH_MAX_INPUT_CHARS == 1000
    assert settings.COACH_MAX_OUTPUT_TOKENS == 800
    # Key is either configured string or None
    assert settings.GEMINI_API_KEY is None or isinstance(settings.GEMINI_API_KEY, str)


def test_health_check_remains_functional(client: TestClient):
    """Verifies that adding Phase 8A configuration does not break the core health endpoint."""
    response = client.get("/health")
    assert response.status_code == 200
    data = response.json()
    assert data["status"] == "healthy"
    assert "firebase_connected" in data
