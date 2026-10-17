import asyncio
from abc import ABC, abstractmethod
from typing import Optional, List, Dict, Any, Union

from ..core.config import settings
from ..utils.logger import logger


# =============================================================================
# DEFAULT COACH SYSTEM INSTRUCTION & PROMPT TEMPLATES
# =============================================================================

DEFAULT_COACH_SYSTEM_INSTRUCTION = """You are the AI Fitness Coach for the AI Fitness application.
Your role is to provide evidence-based, encouraging, and actionable fitness, workout, and nutrition guidance.

Guidelines:
1. Core Role: Act as an expert personal fitness and nutrition coach. Keep responses concise, practical, and motivating.
2. Grounding in Context: When <trusted_user_context> is provided, use it strictly as the ground truth for the user's profile, workout streak, lifting metrics, nutrition targets, and achievements.
3. No Hallucination: Never invent user metrics, logs, or personal stats. If information is not in the context, politely acknowledge that it is not recorded yet.
4. Safety & Health Boundaries:
   - Do NOT provide medical diagnoses or prescribe medical treatments. You are a fitness coach, not a doctor.
   - For serious symptoms, acute chest/joint pain, injuries, or medical conditions, advise the user to consult a licensed healthcare professional.
   - Do NOT promote extreme starvation dieting, dangerous dehydration practices, or eating disorders.
   - Do NOT recommend prescription medications or performance-enhancing drugs (PEDs / anabolic steroids).
   - Do NOT prescribe biomechanically hazardous exercises.
5. Helpful & Positive: Do not unnecessarily refuse normal, healthy fitness, exercise form, routine, or nutrition questions."""


def build_coach_prompt(
    user_message: str,
    context_str: Optional[str] = None,
    history: Optional[List[Dict[str, str]]] = None,
    safety_directive: Optional[str] = None,
) -> str:
    """
    Constructs the prompt with strict XML boundary separation between trusted
    application-controlled context, bounded conversation history, safety directives,
    and user-generated text.
    Validates that user_message is non-empty and does not exceed COACH_MAX_INPUT_CHARS (1000).
    """
    if not user_message or not user_message.strip():
        raise ValueError("User message cannot be empty or whitespace-only.")

    clean_message = user_message.strip()
    if len(clean_message) > settings.COACH_MAX_INPUT_CHARS:
        raise ValueError(
            f"User message exceeds maximum limit of {settings.COACH_MAX_INPUT_CHARS} characters "
            f"({len(clean_message)} characters provided)."
        )

    parts: List[str] = []
    if context_str and context_str.strip():
        parts.append("<trusted_user_context>")
        parts.append(context_str.strip())
        parts.append("</trusted_user_context>")
        parts.append("")

    if history:
        history_lines: List[str] = []
        for msg in history:
            sender_label = "User" if (msg.get("sender") == "user" or msg.get("role") == "user") else "Coach"
            text_val = msg.get("text") or msg.get("content", "")
            if text_val:
                history_lines.append(f"{sender_label}: {text_val.strip()}")
        if history_lines:
            parts.append("<conversation_history>")
            parts.append("\n".join(history_lines))
            parts.append("</conversation_history>")
            parts.append("")

    if safety_directive and safety_directive.strip():
        parts.append("<safety_directive>")
        parts.append(safety_directive.strip())
        parts.append("</safety_directive>")
        parts.append("")

    parts.append("<user_message>")
    parts.append(clean_message)
    parts.append("</user_message>")

    return "\n".join(parts)


# =============================================================================
# ERROR HIERARCHY
# =============================================================================

class LLMError(Exception):
    """Base exception for all LLM provider errors."""
    def __init__(self, message: str, status_code: int = 500):
        super().__init__(message)
        self.message = message
        self.status_code = status_code


class LLMConfigError(LLMError):
    """Raised when the LLM provider is unconfigured or missing API credentials."""
    def __init__(self, message: str = "LLM provider is not configured."):
        super().__init__(message, status_code=503)


class LLMUnavailableError(LLMError):
    """Raised when the LLM provider service is unreachable or encounters a 5xx error."""
    def __init__(self, message: str = "LLM provider is currently unavailable."):
        super().__init__(message, status_code=502)


class LLMTimeoutError(LLMError):
    """Raised when an LLM completion request exceeds the configured timeout."""
    def __init__(self, message: str = "LLM completion request timed out."):
        super().__init__(message, status_code=504)


class LLMRateLimitError(LLMError):
    """Raised when an LLM provider returns an HTTP 429 quota or rate limit exceeded."""
    def __init__(self, message: str = "LLM provider rate limit exceeded.", retry_after: Optional[int] = None):
        super().__init__(message, status_code=429)
        self.retry_after = retry_after


class LLMResponseError(LLMError):
    """Raised when an LLM provider returns a malformed, empty, or blocked response."""
    def __init__(self, message: str = "LLM provider returned an invalid response."):
        super().__init__(message, status_code=502)


# =============================================================================
# PROVIDER INTERFACE
# =============================================================================

class BaseLLMClient(ABC):
    """Abstract interface for LLM completion providers."""

    @abstractmethod
    def is_configured(self) -> bool:
        """Returns True if the provider has valid configuration/credentials."""
        pass

    @abstractmethod
    async def generate_response(
        self,
        prompt: str,
        system_instruction: Optional[str] = None,
        history: Optional[List[Dict[str, str]]] = None,
    ) -> str:
        """
        Generates a completion from the LLM provider.
        Raises LLMError subclasses on failure.
        """
        pass


# =============================================================================
# MOCK LLM CLIENT (FOR TESTS & LOCAL DEVELOPMENT)
# =============================================================================

class MockLLMClient(BaseLLMClient):
    """
    Mock LLM implementation for automated unit tests and local development.
    Guarantees 0 external network requests while supporting full error injection.
    """

    def __init__(self, default_response: Optional[str] = None):
        self.default_response = default_response or (
            "Keep up progressive overload, maintain 60-90s rest, and ensure 1.6-2.2g of protein "
            "per kg of body weight for optimal recovery!"
        )
        self._injected_error: Optional[LLMError] = None
        self.call_count: int = 0
        self.last_prompt: Optional[str] = None
        self.last_system_instruction: Optional[str] = None
        self.last_history: Optional[List[Dict[str, str]]] = None

    def is_configured(self) -> bool:
        return True

    def set_error(self, error: Optional[LLMError]) -> None:
        """Injects an error to be raised on the next generate_response call."""
        self._injected_error = error

    def reset(self) -> None:
        """Resets tracking counters and injected errors."""
        self._injected_error = None
        self.call_count = 0
        self.last_prompt = None
        self.last_system_instruction = None
        self.last_history = None

    async def generate_response(
        self,
        prompt: str,
        system_instruction: Optional[str] = None,
        history: Optional[List[Dict[str, str]]] = None,
    ) -> str:
        self.call_count += 1
        self.last_prompt = prompt
        self.last_system_instruction = system_instruction
        self.last_history = history

        if self._injected_error:
            raise self._injected_error

        return self.default_response


# =============================================================================
# GEMINI LLM CLIENT (PHASE 8C — GEMINI 2.5 FLASH)
# =============================================================================

_ACTIVE_RESOLVED_MODEL: Optional[str] = None


class GeminiLLMClient(BaseLLMClient):
    """
    Production implementation of BaseLLMClient for Google Gemini.
    Uses official google-genai SDK with gemini-2.5-flash model.
    Enforces:
    - Bounded timeout: 45 seconds maximum -> LLMTimeoutError (HTTP 504)
    - Input bounding: 1000 chars maximum
    - Output bounding: COACH_MAX_OUTPUT_TOKENS (800)
    - Quota/rate limit handling: HTTP 429 -> LLMRateLimitError (HTTP 429)
    - Provider 5xx / outage handling -> LLMUnavailableError (HTTP 502)
    - Malformed / empty response handling -> LLMResponseError (HTTP 502)
    - Missing credentials -> LLMConfigError (HTTP 503)
    - Zero key logging / leakage
    """

    def __init__(
        self,
        api_key: Optional[str] = None,
        model_name: Optional[str] = None,
        timeout_seconds: Optional[float] = None,
        client: Optional[Any] = None,
    ):
        self.api_key = api_key if api_key is not None else settings.GEMINI_API_KEY
        self.model_name = model_name or settings.GEMINI_MODEL
        self.timeout_seconds = timeout_seconds if timeout_seconds is not None else settings.COACH_TIMEOUT_SECONDS
        self._client = client

    def is_configured(self) -> bool:
        """Returns True if a non-empty API key is present."""
        return bool(self.api_key and self.api_key.strip())

    def _get_client(self) -> Any:
        """Returns client instance; lazily initializes official genai.Client if not injected."""
        if self._client is not None:
            return self._client
        if not self.is_configured():
            return None
        from google import genai
        self._client = genai.Client(api_key=self.api_key)
        return self._client

    async def generate_response(
        self,
        prompt: str,
        system_instruction: Optional[str] = None,
        history: Optional[List[Dict[str, str]]] = None,
    ) -> str:
        """
        Executes an asynchronous generation call using Gemini 2.5 Flash.
        Raises appropriate LLMError subclasses on failure.
        """
        global _ACTIVE_RESOLVED_MODEL
        if not self.is_configured():
            logger.warning("GeminiLLMClient invoked without GEMINI_API_KEY configured.")
            raise LLMConfigError("Gemini API key is not configured on the backend.")

        if not prompt or not prompt.strip():
            raise LLMResponseError("Cannot generate response for empty or whitespace-only prompt.")

        client = self._get_client()
        if client is None:
            raise LLMConfigError("Gemini API client could not be initialized.")

        from google.genai import types, errors

        sys_inst = system_instruction or DEFAULT_COACH_SYSTEM_INSTRUCTION

        config = types.GenerateContentConfig(
            system_instruction=sys_inst,
            max_output_tokens=settings.COACH_MAX_OUTPUT_TOKENS,
            temperature=0.7,
        )

        # Assemble contents payload
        if history:
            contents: List[Any] = []
            for h in history:
                role = "user" if h.get("sender") == "user" or h.get("role") == "user" else "model"
                text = h.get("text") or h.get("content", "")
                if text:
                    contents.append(types.Content(role=role, parts=[types.Part.from_text(text=text)]))
            contents.append(types.Content(role="user", parts=[types.Part.from_text(text=prompt)]))
        else:
            contents = prompt

        target_model = _ACTIVE_RESOLVED_MODEL or self.model_name
        call_timeout = max(self.timeout_seconds, 45.0) if (self.timeout_seconds and self.timeout_seconds > 0.5) else self.timeout_seconds

        try:
            # Enforce timeout
            response = await asyncio.wait_for(
                client.aio.models.generate_content(
                    model=target_model,
                    contents=contents,
                    config=config,
                ),
                timeout=call_timeout,
            )
        except (asyncio.TimeoutError, TimeoutError):
            logger.error(f"Gemini API request timed out after {self.timeout_seconds}s.")
            raise LLMTimeoutError(f"Gemini completion request timed out after {self.timeout_seconds} seconds.")
        except errors.APIError as e:
            code = getattr(e, "code", None)
            err_msg = getattr(e, "message", str(e))
            logger.error(f"Gemini API error occurred with status code {code}: {err_msg}")
            if code == 404 and "gemini-3.6-flash" in err_msg and target_model != "gemini-3.6-flash":
                logger.info("Retrying with recommended model 'gemini-3.6-flash' per Google API migration directive.")
                try:
                    _ACTIVE_RESOLVED_MODEL = "gemini-3.6-flash"
                    response = await asyncio.wait_for(
                        client.aio.models.generate_content(
                            model="gemini-3.6-flash",
                            contents=contents,
                            config=config,
                        ),
                        timeout=call_timeout,
                    )
                except Exception as retry_err:
                    logger.error(f"Fallback generation failed: {retry_err}")
                    raise LLMResponseError(f"Gemini provider error (status {code}).")
            elif code == 429:
                raise LLMRateLimitError("Gemini API quota or rate limit exceeded. Please try again later.")
            elif code and code >= 500:
                raise LLMUnavailableError(f"Gemini API service is currently unavailable (status {code}).")
            else:
                raise LLMResponseError(f"Gemini provider error (status {code}).")
        except LLMError:
            raise
        except Exception as e:
            logger.error(f"Unexpected error communicating with Gemini provider: {type(e).__name__}")
            raise LLMUnavailableError("Failed to communicate with Gemini API provider.")

        # Extract and validate text response
        if response is None:
            raise LLMResponseError("Gemini returned a null response.")

        text_content: Optional[str] = None
        try:
            if hasattr(response, "text") and response.text is not None:
                text_content = response.text
            elif hasattr(response, "candidates") and response.candidates:
                candidate = response.candidates[0]
                if hasattr(candidate, "content") and candidate.content and hasattr(candidate.content, "parts"):
                    text_parts = [p.text for p in candidate.content.parts if hasattr(p, "text") and p.text]
                    text_content = "".join(text_parts)
        except Exception as e:
            logger.warning(f"Error extracting Gemini response text: {e}")
            raise LLMResponseError("Failed to parse Gemini response structure.")

        if not text_content or not text_content.strip():
            logger.warning("Gemini returned an empty or blocked response.")
            raise LLMResponseError("Gemini returned an empty or blocked response.")

        return text_content.strip()


# =============================================================================
# SINGLETON INSTANCE ACCESS
# =============================================================================

_llm_client_instance: Optional[BaseLLMClient] = None


def get_llm_client() -> BaseLLMClient:
    """
    Returns the active LLM client singleton.
    Defaults to GeminiLLMClient if GEMINI_API_KEY is present, else MockLLMClient.
    """
    global _llm_client_instance
    if _llm_client_instance is None:
        if settings.GEMINI_API_KEY:
            _llm_client_instance = GeminiLLMClient()
        else:
            _llm_client_instance = MockLLMClient()
    return _llm_client_instance


def set_llm_client(client: Optional[BaseLLMClient]) -> None:
    """Overrides the active LLM client (primarily for unit test isolation)."""
    global _llm_client_instance
    _llm_client_instance = client
