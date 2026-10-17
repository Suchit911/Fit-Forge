import pytest
from unittest.mock import AsyncMock, MagicMock
from datetime import datetime, timezone

from backend.app.schemas.coach import (
    CoachContext,
    CoachProfileContext,
    CoachSettingsSchema,
    CoachRecentActivityContext,
    CoachNutritionContext,
    CoachAchievementsContext,
)
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
from backend.app.services.coach_service import (
    CoachService,
    CoachRateLimiter,
    generate_deterministic_title,
    format_conversation_summary,
    evaluate_safety,
)


# =============================================================================
# FIXTURES
# =============================================================================

@pytest.fixture
def mock_repo():
    return CoachRepository(db=None)


@pytest.fixture
def mock_context_service():
    service = CoachContextService()

    async def mock_assemble(uid: str) -> CoachContext:
        return CoachContext(
            profile=CoachProfileContext(name="Alex", goal="Muscle Gain", targetCalories=2600),
            preferences=CoachSettingsSchema(tone="encouraging", focus="hypertrophy"),
            recentActivity=CoachRecentActivityContext(activeStreak=4, workoutsCompletedThisWeek=3),
            todayNutrition=CoachNutritionContext(consumedCalories=1900, targetCalories=2600),
            achievements=CoachAchievementsContext(totalPoints=1200, level=5),
        )

    service.assemble_coach_context = AsyncMock(side_effect=mock_assemble)
    return service


@pytest.fixture
def mock_llm():
    return MockLLMClient(default_response="Focus on progressive overload and hitting your protein goal!")


@pytest.fixture
def rate_limiter():
    limiter = CoachRateLimiter(max_per_minute=10, max_per_day=50)
    limiter.reset()
    return limiter


@pytest.fixture
def coach_service(mock_repo, mock_context_service, mock_llm, rate_limiter):
    return CoachService(
        repo=mock_repo,
        context_service=mock_context_service,
        llm_client=mock_llm,
        rate_limiter=rate_limiter,
    )


# =============================================================================
# 1. DETERMINISTIC TITLE GENERATION & SUMMARY FORMATTING
# =============================================================================

def test_generate_deterministic_title_normal():
    title = generate_deterministic_title("How do I structure my 4-day split for hypertrophy?")
    assert "4-day split" in title
    assert len(title) <= 45


def test_generate_deterministic_title_empty_or_whitespace():
    assert generate_deterministic_title("") == "Workout Plan Advice"
    assert generate_deterministic_title("   \n\t  ") == "Workout Plan Advice"


def test_generate_deterministic_title_long_message_truncated():
    long_msg = "This is an extremely long message about fitness that goes on and on and contains way more words than needed"
    title = generate_deterministic_title(long_msg, max_length=30)
    assert len(title) <= 35
    assert title.endswith("...")


def test_format_conversation_summary_today():
    conv = {
        "id": "conv_today",
        "title": "Hypertrophy Push Day",
        "createdAt": datetime.now(timezone.utc).isoformat(),
        "updatedAt": datetime.now(timezone.utc).isoformat(),
        "previewText": "Focus on incline press",
        "messageCount": 2,
    }
    summary = format_conversation_summary(conv)
    assert summary.id == "conv_today"
    assert summary.dateGroup == "TODAY"
    assert summary.previewText == "Focus on incline press"
    assert summary.messageCount == 2


# =============================================================================
# 2. APPLICATION RATE LIMITING
# =============================================================================

@pytest.mark.asyncio
async def test_rate_limiter_allows_up_to_limit():
    limiter = CoachRateLimiter(max_per_minute=3, max_per_day=10)
    uid = "test_user_rate"

    for i in range(3):
        allowed, msg, retry = await limiter.check_and_record(uid)
        assert allowed is True
        assert msg is None

    # 4th message within minute rejected
    allowed, msg, retry = await limiter.check_and_record(uid)
    assert allowed is False
    assert "at most 3 messages per minute" in msg
    assert retry is not None and retry > 0


@pytest.mark.asyncio
async def test_rate_limiter_daily_limit_enforced():
    limiter = CoachRateLimiter(max_per_minute=100, max_per_day=3)
    uid = "test_user_daily"

    for i in range(3):
        allowed, msg, retry = await limiter.check_and_record(uid)
        assert allowed is True

    # 4th message reaches daily limit
    allowed, msg, retry = await limiter.check_and_record(uid)
    assert allowed is False
    assert "Daily limit exceeded" in msg


# =============================================================================
# 3. SAFETY EVALUATION
# =============================================================================

def test_evaluate_safety_detects_acute_medical():
    directive = evaluate_safety("I have sharp chest pain and can't breathe.")
    assert directive is not None
    assert "SAFETY DIRECTIVE" in directive
    assert "physician" in directive or "healthcare professional" in directive


def test_evaluate_safety_detects_steroids():
    directive = evaluate_safety("What is the best trenbolone cycle dosage for mass?")
    assert directive is not None
    assert "SAFETY DIRECTIVE" in directive
    assert "anabolic steroids" in directive or "PEDs" in directive


def test_evaluate_safety_detects_extreme_dieting():
    directive = evaluate_safety("I want to eat zero calories for 14 days to lose fat.")
    assert directive is not None
    assert "SAFETY DIRECTIVE" in directive
    assert "caloric restriction" in directive or "starvation" in directive


def test_evaluate_safety_allows_normal_fitness_queries():
    # Normal fitness questions must NOT trigger safety directives
    assert evaluate_safety("My hamstrings are sore after deadlifts, should I foam roll?") is None
    assert evaluate_safety("How much protein should I consume post-workout?") is None
    assert evaluate_safety("Is creatine monohydrate effective for strength?") is None


# =============================================================================
# 4. CONVERSATION CRUD ORCHESTRATION
# =============================================================================

def test_coach_service_create_and_list_conversations(coach_service: CoachService):
    uid = "user_svc_1"
    c1 = coach_service.create_conversation(uid, title="Back & Biceps Split")
    assert c1.id.startswith("conv_")
    assert c1.title == "Back & Biceps Split"
    assert c1.messageCount == 0

    c2 = coach_service.create_conversation(uid, initial_message="What should I eat before morning cardio?")
    assert "morning cardio" in c2.title.lower() or "what should" in c2.title.lower()

    convs = coach_service.list_conversations(uid)
    assert len(convs) == 2


def test_coach_service_get_and_delete_conversation(coach_service: CoachService):
    uid = "user_svc_1"
    c = coach_service.create_conversation(uid, title="To Delete")
    cid = c.id

    fetched = coach_service.get_conversation(uid, cid)
    assert fetched is not None
    assert fetched.id == cid

    deleted = coach_service.delete_conversation(uid, cid)
    assert deleted is True
    assert coach_service.get_conversation(uid, cid) is None


# =============================================================================
# 5. CHAT WORKFLOW ORCHESTRATION
# =============================================================================

@pytest.mark.asyncio
async def test_send_message_creates_new_conversation_when_id_none(coach_service: CoachService, mock_llm: MockLLMClient):
    uid = "user_svc_chat_1"
    response = await coach_service.send_message(
        uid=uid,
        message="How many sets per muscle group per week?",
        conversation_id=None,
    )

    assert response.conversationId.startswith("conv_")
    assert response.userMessage.text == "How many sets per muscle group per week?"
    assert response.assistantMessage.text == mock_llm.default_response
    assert response.userMessage.sender == "user"
    assert response.assistantMessage.sender == "assistant"

    # Verify conversation was persisted with updated message count
    conv = coach_service.get_conversation(uid, response.conversationId)
    assert conv is not None
    assert conv.messageCount == 2

    # Verify messages are in repository
    msgs = coach_service.get_messages(uid, response.conversationId)
    assert len(msgs) == 2
    assert msgs[0].id == response.userMessage.id
    assert msgs[1].id == response.assistantMessage.id


@pytest.mark.asyncio
async def test_send_message_existing_conversation(coach_service: CoachService):
    uid = "user_svc_chat_2"
    conv = coach_service.create_conversation(uid, title="Leg Day Optimization")
    cid = conv.id

    res1 = await coach_service.send_message(uid=uid, message="Best quad exercises?", conversation_id=cid)
    assert res1.conversationId == cid

    res2 = await coach_service.send_message(uid=uid, message="Should I do hack squats?", conversation_id=cid)
    assert res2.conversationId == cid

    msgs = coach_service.get_messages(uid, cid)
    assert len(msgs) == 4
    assert msgs[0].sender == "user"
    assert msgs[1].sender == "assistant"
    assert msgs[2].sender == "user"
    assert msgs[3].sender == "assistant"


@pytest.mark.asyncio
async def test_send_message_nonexistent_conversation_raises_keyerror(coach_service: CoachService):
    uid = "user_svc_chat_3"
    with pytest.raises(KeyError) as exc_info:
        await coach_service.send_message(uid=uid, message="Hello", conversation_id="conv_nonexistent_999")
    assert "does not exist" in str(exc_info.value)


@pytest.mark.asyncio
async def test_send_message_input_validation_empty_rejected(coach_service: CoachService):
    uid = "user_svc_chat_4"
    with pytest.raises(ValueError) as exc:
        await coach_service.send_message(uid=uid, message="   ")
    assert "cannot be empty" in str(exc.value)


@pytest.mark.asyncio
async def test_send_message_input_validation_over_1000_chars_rejected(coach_service: CoachService):
    uid = "user_svc_chat_5"
    with pytest.raises(ValueError) as exc:
        await coach_service.send_message(uid=uid, message="a" * 1001)
    assert "cannot exceed 1000 characters" in str(exc.value)


# =============================================================================
# 6. LLM FAILURE CONSISTENCY (ZERO ORPHAN MESSAGES)
# =============================================================================

@pytest.mark.asyncio
async def test_llm_failure_does_not_persist_orphan_user_or_fake_assistant_message(
    coach_service: CoachService, mock_llm: MockLLMClient
):
    uid = "user_svc_failure"
    conv = coach_service.create_conversation(uid, title="Fault Tolerance Test")
    cid = conv.id

    # Inject timeout error into LLM client
    mock_llm.set_error(LLMTimeoutError("Gemini timed out after 12s"))

    with pytest.raises(LLMTimeoutError):
        await coach_service.send_message(uid=uid, message="Will this fail safely?", conversation_id=cid)

    # Verify NO messages were saved to the conversation
    msgs = coach_service.get_messages(uid, cid)
    assert len(msgs) == 0

    # Verify conversation messageCount remains 0
    updated_conv = coach_service.get_conversation(uid, cid)
    assert updated_conv.messageCount == 0


@pytest.mark.asyncio
async def test_rate_limit_exceeded_does_not_call_llm(
    coach_service: CoachService, mock_llm: MockLLMClient, rate_limiter: CoachRateLimiter
):
    uid = "user_rate_limit_llm"
    # Fill up rate limiter
    for _ in range(10):
        await rate_limiter.check_and_record(uid)

    # Call send_message
    with pytest.raises(LLMRateLimitError):
        await coach_service.send_message(uid=uid, message="Should not call LLM")

    # LLM must not have been called
    assert mock_llm.call_count == 0


# =============================================================================
# 7. CROSS-USER SECURITY
# =============================================================================

def test_cross_user_conversation_isolation(coach_service: CoachService):
    uid_a = "user_alpha"
    uid_b = "user_beta"

    conv_a = coach_service.create_conversation(uid_a, title="User A Confidential Chat")
    cid_a = conv_a.id

    # User B cannot see User A's conversation
    assert coach_service.get_conversation(uid_b, cid_a) is None
    assert coach_service.list_conversations(uid_b) == []

    # User B cannot delete User A's conversation
    assert coach_service.delete_conversation(uid_b, cid_a) is False

    # User A's conversation remains intact
    assert coach_service.get_conversation(uid_a, cid_a) is not None
