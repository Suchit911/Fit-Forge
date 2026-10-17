import asyncio
import pytest
from unittest.mock import AsyncMock, MagicMock
from google.genai import types, errors

from backend.app.core.config import settings
from backend.app.services.llm_client import (
    GeminiLLMClient,
    BaseLLMClient,
    MockLLMClient,
    DEFAULT_COACH_SYSTEM_INSTRUCTION,
    build_coach_prompt,
    LLMError,
    LLMConfigError,
    LLMUnavailableError,
    LLMTimeoutError,
    LLMRateLimitError,
    LLMResponseError,
)
from backend.app.services.coach_context_service import CoachContextService
from backend.app.schemas.coach import (
    CoachContext,
    CoachProfileContext,
    CoachSettingsSchema,
    CoachRecentActivityContext,
    CoachNutritionContext,
    CoachAchievementsContext,
)


# =============================================================================
# 1. CONFIGURATION TESTS
# =============================================================================

def test_gemini_client_missing_key_unconfigured(monkeypatch):
    """Verifies GeminiLLMClient is not configured when key is None or empty."""
    monkeypatch.setattr(settings, "GEMINI_API_KEY", None)
    client_none = GeminiLLMClient(api_key=None)
    assert client_none.is_configured() is False

    client_empty = GeminiLLMClient(api_key="   ")
    assert client_empty.is_configured() is False


@pytest.mark.asyncio
async def test_gemini_client_unconfigured_raises_config_error(monkeypatch):
    """Verifies generate_response raises LLMConfigError (503) when key is missing."""
    monkeypatch.setattr(settings, "GEMINI_API_KEY", None)
    client = GeminiLLMClient(api_key=None)
    with pytest.raises(LLMConfigError) as exc_info:
        await client.generate_response("Hello Coach!")
    assert exc_info.value.status_code == 503
    assert "Gemini API key is not configured" in exc_info.value.message


def test_gemini_client_configured_key():
    """Verifies is_configured returns True when valid key is provided."""
    client = GeminiLLMClient(api_key="ai-test-key-12345")
    assert client.is_configured() is True


def test_gemini_model_defaults_to_gemini_2_5_flash():
    """Verifies default model dynamically defaults to configured settings.GEMINI_MODEL."""
    client = GeminiLLMClient(api_key="test-key")
    assert client.model_name == settings.GEMINI_MODEL
    assert client.model_name.startswith("gemini-")


def test_gemini_timeout_defaults_to_12_seconds():
    """Verifies default timeout is 12.0 seconds as specified."""
    client = GeminiLLMClient(api_key="test-key")
    assert client.timeout_seconds == 12.0


def test_api_key_not_exposed_in_client_string():
    """Verifies API key is not inadvertently leaked in string representations."""
    secret_key = "sensitive-gemini-key-999"
    client = GeminiLLMClient(api_key=secret_key)
    client_str = str(client)
    # Default object representation should not expose the raw key
    assert secret_key not in client_str


# =============================================================================
# 2. SUCCESSFUL GENERATION TESTS (MOCKED PROVIDER — ZERO NETWORK)
# =============================================================================

@pytest.mark.asyncio
async def test_gemini_client_mocked_success():
    """Verifies successful response extraction from mocked Gemini 2.5 Flash."""
    mock_sdk_client = MagicMock()
    mock_response = MagicMock()
    mock_response.text = "Great job on your 4-day workout streak! Focus on progressive overload today."
    mock_sdk_client.aio.models.generate_content = AsyncMock(return_value=mock_response)

    client = GeminiLLMClient(
        api_key="mock-api-key",
        model_name="gemini-2.5-flash",
        client=mock_sdk_client,
    )

    prompt = "<user_message>What should I focus on today?</user_message>"
    result = await client.generate_response(prompt)

    assert result == "Great job on your 4-day workout streak! Focus on progressive overload today."
    mock_sdk_client.aio.models.generate_content.assert_awaited_once()
    call_kwargs = mock_sdk_client.aio.models.generate_content.call_args.kwargs
    assert call_kwargs["model"] == "gemini-2.5-flash"
    assert call_kwargs["contents"] == prompt
    assert call_kwargs["config"].max_output_tokens == settings.COACH_MAX_OUTPUT_TOKENS
    assert call_kwargs["config"].max_output_tokens == 800
    assert call_kwargs["config"].system_instruction == DEFAULT_COACH_SYSTEM_INSTRUCTION


@pytest.mark.asyncio
async def test_gemini_client_with_conversation_history():
    """Verifies conversation history is formatted into multi-turn contents."""
    mock_sdk_client = MagicMock()
    mock_response = MagicMock()
    mock_response.text = "You can substitute dumbbell bench press."
    mock_sdk_client.aio.models.generate_content = AsyncMock(return_value=mock_response)

    client = GeminiLLMClient(
        api_key="mock-api-key",
        client=mock_sdk_client,
    )

    history = [
        {"sender": "user", "text": "I don't have a barbell today."},
        {"sender": "assistant", "text": "No problem, what equipment do you have?"},
    ]

    result = await client.generate_response(prompt="I have dumbbells.", history=history)
    assert result == "You can substitute dumbbell bench press."

    call_kwargs = mock_sdk_client.aio.models.generate_content.call_args.kwargs
    contents = call_kwargs["contents"]
    assert isinstance(contents, list)
    assert len(contents) == 3
    assert contents[0].role == "user"
    assert contents[1].role == "model"
    assert contents[2].role == "user"


@pytest.mark.asyncio
async def test_gemini_client_strips_surrounding_whitespace():
    """Verifies output text is cleanly stripped of leading/trailing whitespace."""
    mock_sdk_client = MagicMock()
    mock_response = MagicMock()
    mock_response.text = "   \n  Hydrate with 500ml water before your session.  \t \n"
    mock_sdk_client.aio.models.generate_content = AsyncMock(return_value=mock_response)

    client = GeminiLLMClient(api_key="mock-api-key", client=mock_sdk_client)
    result = await client.generate_response("Hydration tip")
    assert result == "Hydrate with 500ml water before your session."


# =============================================================================
# 3. PROVIDER ERROR MAPPING TESTS (MOCKED PROVIDER)
# =============================================================================

@pytest.mark.asyncio
async def test_gemini_client_timeout_raises_llm_timeout_error():
    """Verifies request timeout is mapped to LLMTimeoutError (HTTP 504)."""
    mock_sdk_client = MagicMock()

    async def timeout_coroutine(*args, **kwargs):
        raise asyncio.TimeoutError()

    mock_sdk_client.aio.models.generate_content = AsyncMock(side_effect=timeout_coroutine)

    client = GeminiLLMClient(
        api_key="mock-api-key",
        timeout_seconds=0.1,
        client=mock_sdk_client,
    )

    with pytest.raises(LLMTimeoutError) as exc_info:
        await client.generate_response("Test prompt")

    assert exc_info.value.status_code == 504
    assert "timed out after" in exc_info.value.message


@pytest.mark.asyncio
async def test_gemini_client_rate_limit_429_raises_llm_rate_limit_error():
    """Verifies HTTP 429 quota/rate limit error is mapped to LLMRateLimitError (HTTP 429)."""
    mock_sdk_client = MagicMock()
    api_error_429 = errors.APIError(429, {"error": {"message": "Resource has been exhausted"}})
    mock_sdk_client.aio.models.generate_content = AsyncMock(side_effect=api_error_429)

    client = GeminiLLMClient(api_key="mock-api-key", client=mock_sdk_client)

    with pytest.raises(LLMRateLimitError) as exc_info:
        await client.generate_response("Test prompt")

    assert exc_info.value.status_code == 429
    assert "rate limit" in exc_info.value.message.lower() or "quota" in exc_info.value.message.lower()


@pytest.mark.asyncio
async def test_gemini_client_server_error_500_raises_llm_unavailable_error():
    """Verifies provider 500 internal server error is mapped to LLMUnavailableError (HTTP 502)."""
    mock_sdk_client = MagicMock()
    api_error_500 = errors.APIError(500, {"error": {"message": "Internal server error"}})
    mock_sdk_client.aio.models.generate_content = AsyncMock(side_effect=api_error_500)

    client = GeminiLLMClient(api_key="mock-api-key", client=mock_sdk_client)

    with pytest.raises(LLMUnavailableError) as exc_info:
        await client.generate_response("Test prompt")

    assert exc_info.value.status_code == 502
    assert "unavailable" in exc_info.value.message.lower()


@pytest.mark.asyncio
async def test_gemini_client_server_error_503_raises_llm_unavailable_error():
    """Verifies provider 503 service unavailable is mapped to LLMUnavailableError (HTTP 502)."""
    mock_sdk_client = MagicMock()
    api_error_503 = errors.APIError(503, {"error": {"message": "Backend service overloaded"}})
    mock_sdk_client.aio.models.generate_content = AsyncMock(side_effect=api_error_503)

    client = GeminiLLMClient(api_key="mock-api-key", client=mock_sdk_client)

    with pytest.raises(LLMUnavailableError) as exc_info:
        await client.generate_response("Test prompt")

    assert exc_info.value.status_code == 502


@pytest.mark.asyncio
async def test_gemini_client_empty_response_text_raises_llm_response_error():
    """Verifies empty response text is mapped to LLMResponseError (HTTP 502)."""
    mock_sdk_client = MagicMock()
    mock_response = MagicMock()
    mock_response.text = ""
    mock_response.candidates = []
    mock_sdk_client.aio.models.generate_content = AsyncMock(return_value=mock_response)

    client = GeminiLLMClient(api_key="mock-api-key", client=mock_sdk_client)

    with pytest.raises(LLMResponseError) as exc_info:
        await client.generate_response("Test prompt")

    assert exc_info.value.status_code == 502
    assert "empty or blocked" in exc_info.value.message


@pytest.mark.asyncio
async def test_gemini_client_whitespace_response_text_raises_llm_response_error():
    """Verifies whitespace-only response text is mapped to LLMResponseError (HTTP 502)."""
    mock_sdk_client = MagicMock()
    mock_response = MagicMock()
    mock_response.text = "   \n\t   "
    mock_response.candidates = []
    mock_sdk_client.aio.models.generate_content = AsyncMock(return_value=mock_response)

    client = GeminiLLMClient(api_key="mock-api-key", client=mock_sdk_client)

    with pytest.raises(LLMResponseError) as exc_info:
        await client.generate_response("Test prompt")

    assert exc_info.value.status_code == 502


@pytest.mark.asyncio
async def test_gemini_client_null_response_raises_llm_response_error():
    """Verifies None response object is mapped to LLMResponseError (HTTP 502)."""
    mock_sdk_client = MagicMock()
    mock_sdk_client.aio.models.generate_content = AsyncMock(return_value=None)

    client = GeminiLLMClient(api_key="mock-api-key", client=mock_sdk_client)

    with pytest.raises(LLMResponseError) as exc_info:
        await client.generate_response("Test prompt")

    assert exc_info.value.status_code == 502


@pytest.mark.asyncio
async def test_gemini_client_network_exception_raises_llm_unavailable_error():
    """Verifies unexpected network/socket failures are safely mapped to LLMUnavailableError."""
    mock_sdk_client = MagicMock()
    mock_sdk_client.aio.models.generate_content = AsyncMock(side_effect=ConnectionResetError("Socket closed"))

    client = GeminiLLMClient(api_key="mock-api-key", client=mock_sdk_client)

    with pytest.raises(LLMUnavailableError) as exc_info:
        await client.generate_response("Test prompt")

    assert exc_info.value.status_code == 502
    assert "Failed to communicate with Gemini API provider" in exc_info.value.message


# =============================================================================
# 4. INPUT VALIDATION & PROMPT BOUNDARIES
# =============================================================================

def test_build_coach_prompt_valid_with_context():
    """Verifies strict separation between trusted context and user message."""
    user_msg = "How many grams of protein should I eat?"
    context_str = "[USER PROFILE]\nGoal: Muscle Gain\nTarget Protein: 150g"

    prompt = build_coach_prompt(user_message=user_msg, context_str=context_str)

    assert "<trusted_user_context>" in prompt
    assert "</trusted_user_context>" in prompt
    assert "<user_message>" in prompt
    assert "</user_message>" in prompt

    # Context is in trusted section
    assert "[USER PROFILE]" in prompt.split("</trusted_user_context>")[0]
    # Message is inside user section
    assert user_msg in prompt.split("<user_message>")[1]


def test_build_coach_prompt_without_context():
    """Verifies prompt without context contains only user_message tag."""
    user_msg = "Give me a 10-minute warm-up routine."
    prompt = build_coach_prompt(user_message=user_msg, context_str=None)

    assert "<trusted_user_context>" not in prompt
    assert "<user_message>" in prompt
    assert "</user_message>" in prompt
    assert user_msg in prompt


def test_build_coach_prompt_1000_chars_accepted():
    """Verifies exactly 1000-character user message is accepted."""
    long_msg = "a" * 1000
    prompt = build_coach_prompt(user_message=long_msg)
    assert long_msg in prompt


def test_build_coach_prompt_exceeding_1000_chars_rejected():
    """Verifies user message exceeding 1000 characters is rejected with ValueError."""
    over_limit_msg = "b" * 1001
    with pytest.raises(ValueError) as exc_info:
        build_coach_prompt(user_message=over_limit_msg)
    assert "exceeds maximum limit of 1000 characters" in str(exc_info.value)


def test_build_coach_prompt_empty_rejected():
    """Verifies empty or whitespace-only messages are rejected."""
    with pytest.raises(ValueError) as exc_info:
        build_coach_prompt(user_message="")
    assert "cannot be empty" in str(exc_info.value)

    with pytest.raises(ValueError) as exc_info:
        build_coach_prompt(user_message="     \n  \t ")
    assert "cannot be empty" in str(exc_info.value)


@pytest.mark.asyncio
async def test_gemini_client_rejects_empty_prompt():
    """Verifies GeminiLLMClient rejects empty prompt before calling the provider."""
    mock_sdk_client = MagicMock()
    client = GeminiLLMClient(api_key="mock-api-key", client=mock_sdk_client)

    with pytest.raises(LLMResponseError) as exc_info:
        await client.generate_response("   ")

    assert exc_info.value.status_code == 502
    assert "empty or whitespace-only" in exc_info.value.message
    mock_sdk_client.aio.models.generate_content.assert_not_called()


# =============================================================================
# 5. SYSTEM INSTRUCTION & SAFETY COMPLIANCE
# =============================================================================

def test_system_instruction_contains_required_safety_rules():
    """Verifies system instruction contains required fitness coaching and medical safety rules."""
    instruction = DEFAULT_COACH_SYSTEM_INSTRUCTION.lower()

    # Core role
    assert "ai fitness coach" in instruction
    assert "evidence-based" in instruction

    # Grounding & metrics
    assert "trusted_user_context" in instruction
    assert "never invent" in instruction or "no hallucination" in instruction

    # Safety boundaries
    assert "medical" in instruction
    assert "doctor" in instruction
    assert "healthcare professional" in instruction
    assert "extreme" in instruction or "starvation" in instruction
    assert "performance-enhancing" in instruction or "steroids" in instruction or "ped" in instruction
    assert "prescription" in instruction


# =============================================================================
# 6. CONTEXT BOUNDARY & SECURITY CHECKS
# =============================================================================

def test_serialized_context_integration_in_prompt():
    """Verifies CoachContextService.serialize_for_llm integrates cleanly with build_coach_prompt."""
    ctx = CoachContext(
        profile=CoachProfileContext(name="Alex", goal="Muscle Gain", targetCalories=2800),
        preferences=CoachSettingsSchema(tone="scientific", focus="hypertrophy"),
        recentActivity=CoachRecentActivityContext(activeStreak=5, workoutsCompletedThisWeek=4),
        todayNutrition=CoachNutritionContext(consumedCalories=2100, targetCalories=2800),
        achievements=CoachAchievementsContext(totalPoints=1500, level=6),
    )
    service = CoachContextService()
    serialized_context = service.serialize_for_llm(ctx)

    prompt = build_coach_prompt(
        user_message="Should I add another set of lateral raises?",
        context_str=serialized_context,
    )

    # Validate XML boundaries
    assert "<trusted_user_context>" in prompt
    assert "</trusted_user_context>" in prompt
    assert "Alex" in prompt
    assert "Muscle Gain" in prompt
    assert "Active Workout Streak: 5 days" in prompt
    assert "<user_message>\nShould I add another set of lateral raises?\n</user_message>" in prompt

    # Validate privacy: no internal IDs or tokens in prompt
    assert "test_user" not in prompt
    assert "Bearer" not in prompt
    assert "apiKey" not in prompt


def test_gemini_client_has_no_firebase_or_firestore_references():
    """Verifies Gemini client abstraction is completely decoupled from Firebase/Firestore."""
    client = GeminiLLMClient(api_key="test-key")
    attrs = dir(client)
    assert "db" not in attrs
    assert "firestore" not in attrs
    assert "firebase" not in attrs
    assert "credentials" not in attrs
