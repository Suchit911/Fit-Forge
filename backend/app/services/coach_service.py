import re
import asyncio
from datetime import datetime, timezone
from typing import Optional, List, Dict, Any, Tuple

from ..repositories.coach_repository import CoachRepository, get_coach_repository
from ..services.coach_context_service import CoachContextService, get_coach_context_service
from ..services.llm_client import (
    BaseLLMClient,
    get_llm_client,
    build_coach_prompt,
    DEFAULT_COACH_SYSTEM_INSTRUCTION,
    LLMError,
    LLMConfigError,
    LLMUnavailableError,
    LLMTimeoutError,
    LLMRateLimitError,
    LLMResponseError,
)
from ..schemas.coach import (
    CoachMessageSchema,
    CoachConversationSchema,
    ConversationSummarySchema,
    CoachMessageResponse,
    SendCoachMessageRequest,
    CreateConversationRequest,
)
from ..core.config import settings
from ..utils.logger import logger


# =============================================================================
# DETERMINISTIC TITLE & DISPLAY HELPERS
# =============================================================================

def generate_deterministic_title(message: str, max_length: int = 40) -> str:
    """
    Generates a clean, deterministic conversation title from the initial message.
    Does NOT call the LLM for title generation.
    """
    cleaned = re.sub(r"\s+", " ", message).strip()
    cleaned = cleaned.lstrip("?.,!-_'\"#*")
    if not cleaned:
        return "Workout Plan Advice"

    # Take first sentence if available
    first_sentence = re.split(r"[.!?\n]", cleaned)[0].strip()
    if len(first_sentence) > max_length:
        truncated = first_sentence[:max_length].rsplit(" ", 1)[0].strip()
        return (truncated + "...") if truncated else first_sentence[:max_length]

    return first_sentence or cleaned[:max_length]


def format_conversation_summary(conv: Dict[str, Any]) -> ConversationSummarySchema:
    """
    Transforms a raw conversation record into a ConversationSummarySchema with
    dynamically computed display fields (dateGroup, timestamp) without persisting
    derived display fields to Firestore.
    """
    updated_str = conv.get("updatedAt") or conv.get("createdAt")
    date_group = "RECENT"
    timestamp_disp = ""

    if updated_str:
        try:
            dt = datetime.fromisoformat(updated_str.replace("Z", "+00:00"))
            now = datetime.now(timezone.utc)
            delta = now.date() - dt.date()
            if delta.days == 0:
                date_group = "TODAY"
            elif delta.days == 1:
                date_group = "YESTERDAY"
            else:
                date_group = dt.strftime("%b %d").upper()
            timestamp_disp = dt.strftime("%I:%M %p").lstrip("0")
        except Exception:
            pass

    return ConversationSummarySchema(
        id=conv["id"],
        title=conv.get("title", "Workout Plan Advice"),
        createdAt=conv.get("createdAt", ""),
        updatedAt=conv.get("updatedAt", ""),
        previewText=conv.get("previewText", ""),
        messageCount=conv.get("messageCount", 0),
        dateGroup=date_group,
        timestamp=timestamp_disp,
    )


# =============================================================================
# APPLICATION SAFETY CLASSIFIER
# =============================================================================

# Sensitive patterns that require strict safety directives
EMERGENCY_MEDICAL_PATTERNS = [
    r"\b(sharp|severe|crushing|acute)\s+(chest\s+pain|heart\s+pain)\b",
    r"\b(can'?t\s+breathe|difficulty\s+breathing|shortness\s+of\s+breath)\b",
    r"\b(bone\s+broken|bone\s+sticking|dislocated|torn\s+ligament|torn\s+tendon)\b",
    r"\b(diagnose\s+me|diagnose\s+my\s+condition|do\s+i\s+have\s+(cancer|diabetes|hernia))\b",
    r"\b(vomiting\s+blood|coughing\s+blood|passed\s+out|unconscious)\b",
]

PED_STEROID_PATTERNS = [
    r"\b(tren|trenbolone|dianabol|anadrol|winstrol|deca\s+durabolin|clenbuterol)\b",
    r"\b(how\s+to\s+cycle|cycle\s+dosage|inject\s+testosterone|steroid\s+cycle)\b",
    r"\b(where\s+to\s+buy\s+steroids|buy\s+sarms|sarms\s+dosage)\b",
]

EXTREME_DIETING_PATTERNS = [
    r"\b(eat\s+zero\s+calories|zero\s+calories\s+for|eat\s+nothing\s+for|starve\s+myself|starvation\s+diet)\b",
    r"\b(water\s*(-|\s+)only\s+fast(ing)?|dry\s+fast(ing)?\s+for|cut\s+water\s+completely|no\s+water\s+for\s+\d+\s+days)\b",
    r"\b(how\s+to\s+purge|throw\s+up\s+after\s+eating|laxatives\s+for\s+weight\s+loss)\b",
]

PRESCRIPTION_PATTERNS = [
    r"\b(ozempic|wegovy|mounjaro|semaglutide)\s+(dose|dosage|prescription)\b",
    r"\b(prescription|prescribed)\s+([a-z\s]{0,20})?(medication|medicine|drugs?|pills?)\b",
    r"\b(dosage\s+of\s+my\s+prescription|what\s+dosage\s+of\s+.*prescription)\b",
    r"\b(substitute\s+my\s+medication|stop\s+taking\s+my\s+blood\s+pressure)\b",
]


def evaluate_safety(message: str) -> Optional[str]:
    """
    Evaluates user message for safety risks and returns an appropriate safety directive
    to reinforce responsible fitness coaching boundaries without aggressive keyword blocking.
    """
    msg_lower = message.lower()

    for pat in EMERGENCY_MEDICAL_PATTERNS:
        if re.search(pat, msg_lower):
            return (
                "SAFETY DIRECTIVE: The user mentions acute pain, severe symptoms, or a request for medical diagnosis. "
                "You are an AI fitness coach, NOT a physician. Do NOT attempt to diagnose. Urge them clearly and calmly "
                "to stop training immediately and consult a qualified healthcare professional or emergency care."
            )

    for pat in PED_STEROID_PATTERNS:
        if re.search(pat, msg_lower):
            return (
                "SAFETY DIRECTIVE: The user is asking about anabolic steroids or performance-enhancing drugs (PEDs). "
                "Politely refuse to provide dosages, cycles, or procurement advice. Reiterate your commitment to safe, "
                "natural, evidence-based training and nutrition methods."
            )

    for pat in EXTREME_DIETING_PATTERNS:
        if re.search(pat, msg_lower):
            return (
                "SAFETY DIRECTIVE: The user mentions extreme caloric restriction, prolonged dry fasting, or dangerous weight loss methods. "
                "Firmly discourage severe deprivation or dehydration. Advocate for safe, moderate, sustainable nutritional habits."
            )

    for pat in PRESCRIPTION_PATTERNS:
        if re.search(pat, msg_lower):
            return (
                "SAFETY DIRECTIVE: The user is inquiring about prescription pharmaceutical medications. "
                "State clearly that prescription medications must be managed exclusively by their prescribing healthcare provider."
            )

    return None


# =============================================================================
# APPLICATION-LEVEL RATE LIMITER
# =============================================================================

class CoachRateLimiter:
    """
    Process-local sliding-window rate limiter enforcing application-level limits:
    - 10 messages per minute per verified user UID
    - 50 messages per 24 hours per verified user UID

    Architecture Note:
    This rate limiter uses in-memory timestamps protected by an asyncio lock.
    It is ideal for development and single-instance FastAPI deployments.
    For horizontal multi-node production clusters, this interface can be backed
    by a Redis sliding-window implementation without altering callers.
    """

    def __init__(
        self,
        max_per_minute: int = 10,
        max_per_day: int = 50,
    ):
        self.max_per_minute = max_per_minute
        self.max_per_day = max_per_day
        self._user_timestamps: Dict[str, List[float]] = {}
        self._lock = asyncio.Lock()

    async def check_and_record(self, uid: str) -> Tuple[bool, Optional[str], Optional[int]]:
        """
        Validates whether a message is allowed under the rate limits.
        Returns (is_allowed, error_message, retry_after_seconds).
        """
        async with self._lock:
            now = datetime.now(timezone.utc).timestamp()
            timestamps = self._user_timestamps.get(uid, [])

            # Prune timestamps older than 24 hours (86,400s)
            day_cutoff = now - 86400.0
            timestamps = [ts for ts in timestamps if ts > day_cutoff]

            # 1. Check minute window (last 60s)
            minute_cutoff = now - 60.0
            minute_count = sum(1 for ts in timestamps if ts > minute_cutoff)
            if minute_count >= self.max_per_minute:
                oldest_in_minute = min(ts for ts in timestamps if ts > minute_cutoff)
                retry_after = max(1, int(60.0 - (now - oldest_in_minute)))
                return (
                    False,
                    f"Application rate limit exceeded: You can send at most {self.max_per_minute} messages per minute. "
                    f"Please try again in {retry_after} seconds.",
                    retry_after,
                )

            # 2. Check 24-hour window
            if len(timestamps) >= self.max_per_day:
                oldest_in_day = min(timestamps)
                retry_after = max(1, int(86400.0 - (now - oldest_in_day)))
                return (
                    False,
                    f"Daily limit exceeded: You have reached your maximum of {self.max_per_day} AI Coach messages "
                    f"per 24 hours. Please try again tomorrow.",
                    retry_after,
                )

            # Record allowed request
            timestamps.append(now)
            self._user_timestamps[uid] = timestamps
            return (True, None, None)

    def reset(self, uid: Optional[str] = None) -> None:
        """Resets rate limiter state (primarily for automated test isolation)."""
        if uid:
            self._user_timestamps.pop(uid, None)
        else:
            self._user_timestamps.clear()


_rate_limiter_instance: Optional[CoachRateLimiter] = None


def get_coach_rate_limiter() -> CoachRateLimiter:
    """Returns the singleton CoachRateLimiter instance."""
    global _rate_limiter_instance
    if _rate_limiter_instance is None:
        _rate_limiter_instance = CoachRateLimiter(
            max_per_minute=settings.COACH_MAX_MESSAGES_PER_MINUTE,
            max_per_day=settings.COACH_MAX_MESSAGES_PER_DAY,
        )
    return _rate_limiter_instance


# =============================================================================
# COACH SERVICE ORCHESTRATION LAYER
# =============================================================================

class CoachService:
    """
    Core orchestration service for AI Fitness Coach interactions.
    Coordinates:
    - User identity & conversation ownership
    - Bounded deterministic CoachContext retrieval
    - Recent conversation history retrieval (6-8 messages window)
    - Structured prompt building (XML boundaries)
    - Application rate limiting (10/min, 50/day)
    - Layered safety evaluation
    - GeminiLLMClient generation
    - Atomic Firestore persistence on successful generation
    - Clean error mapping
    """

    def __init__(
        self,
        repo: Optional[CoachRepository] = None,
        context_service: Optional[CoachContextService] = None,
        llm_client: Optional[BaseLLMClient] = None,
        rate_limiter: Optional[CoachRateLimiter] = None,
    ):
        self._repo = repo
        self._context_service = context_service
        self._llm_client = llm_client
        self._rate_limiter = rate_limiter

    @property
    def repo(self) -> CoachRepository:
        return self._repo or get_coach_repository()

    @property
    def context_service(self) -> CoachContextService:
        return self._context_service or get_coach_context_service()

    @property
    def llm_client(self) -> BaseLLMClient:
        return self._llm_client or get_llm_client()

    @property
    def rate_limiter(self) -> CoachRateLimiter:
        return self._rate_limiter or get_coach_rate_limiter()

    # -------------------------------------------------------------------------
    # Conversation CRUD Operations
    # -------------------------------------------------------------------------

    def create_conversation(
        self,
        uid: str,
        title: Optional[str] = None,
        initial_message: Optional[str] = None,
    ) -> CoachConversationSchema:
        """
        Explicitly creates a new conversation thread for the verified user.
        Enforces maximum conversation retention (COACH_MAX_CONVERSATIONS_PER_USER = 20).
        """
        conv_title = title.strip() if (title and title.strip()) else None
        if not conv_title and initial_message:
            conv_title = generate_deterministic_title(initial_message)
        elif not conv_title:
            conv_title = "Workout Plan Advice"

        preview = initial_message.strip()[:120] if initial_message else ""
        conv_data = self.repo.create_conversation(uid, title=conv_title, initial_preview=preview)
        return CoachConversationSchema(**conv_data)

    def list_conversations(self, uid: str, limit: int = 20) -> List[ConversationSummarySchema]:
        """Lists conversations for the verified user ordered by updatedAt descending."""
        eff_limit = min(limit, settings.COACH_MAX_CONVERSATIONS_PER_USER)
        raw_list = self.repo.list_conversations(uid, limit=eff_limit)
        return [format_conversation_summary(c) for c in raw_list]

    def get_conversation(self, uid: str, conversation_id: str) -> Optional[CoachConversationSchema]:
        """Retrieves a single conversation for the verified user if found."""
        raw = self.repo.get_conversation(uid, conversation_id)
        if not raw:
            return None
        return CoachConversationSchema(**raw)

    def get_messages(self, uid: str, conversation_id: str, limit: int = 50) -> List[CoachMessageSchema]:
        """
        Retrieves chronological message history for a conversation owned by the verified user.
        Returns empty list if conversation does not exist.
        """
        raw_msgs = self.repo.list_messages(uid, conversation_id, limit=limit)
        return [CoachMessageSchema(**m) for m in raw_msgs]

    def delete_conversation(self, uid: str, conversation_id: str) -> bool:
        """Deletes a conversation and its messages for the verified user."""
        return self.repo.delete_conversation(uid, conversation_id)

    # -------------------------------------------------------------------------
    # Chat Generation & Orchestration
    # -------------------------------------------------------------------------

    async def send_message(
        self,
        uid: str,
        message: str,
        conversation_id: Optional[str] = None,
    ) -> CoachMessageResponse:
        """
        Core chat workflow:
        1. Validates user message
        2. Enforces application rate limit
        3. Resolves conversation (creates new if omitted; verifies ownership if provided)
        4. Gathers bounded CoachContext from authoritative domain services
        5. Retrieves bounded recent message window (6-8 messages)
        6. Evaluates layered safety policy
        7. Constructs XML boundary-separated prompt
        8. Invokes LLM provider (Gemini 2.5 Flash)
        9. Atomically persists user message & assistant response on success
        10. Updates conversation metadata (updatedAt, previewText, messageCount)
        """
        # 1. Validate message input
        clean_message = message.strip() if message else ""
        if not clean_message:
            raise ValueError("Message text cannot be empty or whitespace-only.")
        if len(clean_message) > settings.COACH_MAX_INPUT_CHARS:
            raise ValueError(f"Message text cannot exceed {settings.COACH_MAX_INPUT_CHARS} characters.")

        # 2. Application-level rate limiting
        allowed, rate_err_msg, retry_after = await self.rate_limiter.check_and_record(uid)
        if not allowed:
            logger.warning(f"Coach rate limit exceeded for user {uid}")
            raise LLMRateLimitError(rate_err_msg or "Application rate limit exceeded.", retry_after=retry_after)

        # 3. Resolve target conversation
        cid = conversation_id.strip() if conversation_id else None
        if cid:
            existing_conv = self.repo.get_conversation(uid, cid)
            if not existing_conv:
                logger.warning(f"Conversation {cid} not found for user {uid}")
                raise KeyError(f"Conversation with ID '{cid}' does not exist.")
        else:
            # Auto-create conversation with deterministic title
            title = generate_deterministic_title(clean_message)
            new_conv = self.repo.create_conversation(uid, title=title, initial_preview=clean_message)
            cid = new_conv["id"]

        # 4. Retrieve bounded recent conversation history (last 6 messages)
        history_msgs = self.repo.list_messages(uid, cid, limit=settings.COACH_MAX_MESSAGES_PER_CONVERSATION)
        bounded_history = history_msgs[-6:] if history_msgs else []

        # 5. Gather trusted CoachContext
        coach_context = await self.context_service.assemble_coach_context(uid)
        serialized_context = self.context_service.serialize_for_llm(coach_context)

        # 6. Safety evaluation
        safety_directive = evaluate_safety(clean_message)

        # 7. Construct bounded prompt with strict XML separation
        prompt = build_coach_prompt(
            user_message=clean_message,
            context_str=serialized_context,
            history=bounded_history,
            safety_directive=safety_directive,
        )

        # 8. Call GeminiLLMClient
        # Note: If LLM raises an error (Timeout, Unavailable, RateLimit, Malformed),
        # execution halts here and NO partial or fake messages are saved to Firestore.
        logger.info(f"Invoking LLM for user {uid} on conversation {cid}")
        response_text = await self.llm_client.generate_response(
            prompt=prompt,
            system_instruction=DEFAULT_COACH_SYSTEM_INSTRUCTION,
            history=bounded_history,
        )

        # 9. Successful generation: persist user message and assistant message
        user_msg_data = self.repo.create_message(
            uid=uid,
            conversation_id=cid,
            sender="user",
            text=clean_message,
        )
        assistant_msg_data = self.repo.create_message(
            uid=uid,
            conversation_id=cid,
            sender="assistant",
            text=response_text,
        )

        return CoachMessageResponse(
            conversationId=cid,
            userMessage=CoachMessageSchema(**user_msg_data),
            assistantMessage=CoachMessageSchema(**assistant_msg_data),
        )


_coach_service_instance: Optional[CoachService] = None


def get_coach_service() -> CoachService:
    """Returns the singleton CoachService instance."""
    global _coach_service_instance
    if _coach_service_instance is None:
        _coach_service_instance = CoachService()
    return _coach_service_instance


def set_coach_service(service: Optional[CoachService]) -> None:
    """Overrides the active CoachService (primarily for unit test isolation)."""
    global _coach_service_instance
    _coach_service_instance = service
