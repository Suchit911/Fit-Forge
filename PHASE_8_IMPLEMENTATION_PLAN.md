# PHASE 8 IMPLEMENTATION PLAN
## AI Coach + LLM Integration Architecture

**Date:** September 6, 2026  
**Author:** Antigravity AI  
**Scope:** Phase 8 Architecture & Staged Implementation Plan (AI Coach & LLM Integration)  
**Status:** PLANNING ONLY — PENDING USER APPROVAL & CREDENTIAL CONFIGURATION

---

## 1. Current Coach UI Architecture

### 1.1 Route & Layout Hierarchy
- **Route:** `/coach` (`src/pages/app/AICoachPage.tsx`)
- **Layout Container:** Authenticated `AppLayout` with navigation sidebar, responsive header, and fluid content viewport.
- **Visual Design:** Premium dark mode (`bg-slate-900/90`, `border-slate-800`, emerald `#10b981` accents, cyan and amber highlights, smooth hover micro-animations).

### 1.2 Desktop 3-Column Workspace Grid (`lg:grid-cols-12`)
1. **Left Column — Chat History Panel (3 of 12 columns, `ChatHistoryPanel.tsx`):**
   - Header with title "Chats" and `+` new chat button.
   - List of user conversations with date group badge (`TODAY`, `YESTERDAY`, `MAY 11`), relative timestamp, conversation title, and message preview snippet.
   - Active conversation highlight (`border-emerald-500/50 bg-emerald-950/30`).
   - "View All Chats" footer action button.
2. **Center Column — Active Conversation Viewport (5 of 12 columns, `ChatConversationView.tsx`):**
   - Header with active conversation title, AI Coach avatar badge, glowing "Online" pulsing dot, "Share Chat" button, and contextual options menu.
   - Message scroll area with distinct chat bubbles:
     - User messages: right-aligned, emerald tinted (`bg-emerald-950/60 border-emerald-500/40 text-slate-100`).
     - Assistant messages: left-aligned with robot avatar, slate bordered (`bg-slate-950/80 border-slate-800 text-slate-200`), with interaction buttons (thumbs up, thumbs down, copy to clipboard).
   - Suggested prompt chips row (e.g. *"Yes, show me the plan"*, *"How about a push pull legs split?"*, *"Best exercises for chest?"*).
   - Form input bar with input field, send button, and disclaimer text: *"AI Coach can make mistakes. Please verify important information."*
3. **Right Column — Supporting Panels & Widgets (4 of 12 columns):**
   - `CoachStatusCard.tsx`: Displays coach readiness, "Online" status, and glowing AI robot avatar.
   - `WeeklyProgressOverviewCard.tsx`: Shows 4 weekly summary progress bars (Workouts, Calories, Steps, Sleep) with current vs target metrics.
   - `AICoachInsightsCard.tsx`: Cards for workout adaptations, strength improvements, and nutrition reminders.
   - `CoachQuickActionsCard.tsx`: 4 quick action buttons ("Analyze Progress", "Adjust Plan", "Log Feedback", "Book Call").

### 1.3 Bottom Full-Width Section (`SuggestedQuestionsSection.tsx`)
- 5 categorized quick-question cards with colored icons (dumbbell, utensils, heart, activity, file-text).
- Clicking any suggested question dispatches it directly into the active chat conversation.

### 1.4 Header, Tabs, and Settings Modal
- `CoachHeader.tsx`: Contains title, "+ New Chat" button, audio/playlist controls, notification bell, and user profile pill.
- `CoachTabs.tsx`: Tabs for "Chat" and "Insights" plus "Coach Settings" modal trigger.
- `CoachSettingsModal.tsx`: Controls coaching tone (*Encouraging & Supportive*, *Strict & Disciplined*, *Scientific & Data-Driven*) and primary AI focus (*Hypertrophy*, *Fat Loss*, *Strength*, *Recovery*).

### 1.5 Current Frontend State & Data Flow
- `src/services/aiCoachService.ts` currently provides mock data (`mockConversations`, `mockInitialMessages`, `mockAICoachDashboardData`).
- `src/hooks/useAICoach.ts` uses TanStack Query (`useQuery` with `['aiChatHistory']`, `['aiSuggestedPrompts']`, and `useMutation` for `sendMessage`).
- **CRITICAL REQUIREMENT:** **The approved UI must NOT be redesigned.** All existing components, styling, cards, and layouts will remain intact and will be seamlessly connected to real backend services and Firestore persistence.

---

## 2. Existing Backend Architecture

### 2.1 Technology Stack & Structure
- **Framework:** FastAPI (Python 3.12) with modular APIRouter structure.
- **Router Directory:** `backend/app/api/v1/router.py` (has `# api_router.include_router(coach_router, prefix="/coach", tags=["AI Coach"])` prepared).
- **Authentication & Security:** `backend/app/core/security.py` verifies Firebase Bearer ID tokens via the Firebase Admin SDK (`auth.verify_id_token()`). Clients never supply authoritative UIDs; identity is strictly derived from the decoded token.
- **Configuration Management:** `backend/app/core/config.py` uses Pydantic `BaseSettings` reading from `.env` files.

### 2.2 Domain Services & Authoritative Data Repositories
The platform already possesses robust, deterministic domain services:
- `UserRepository` (`backend/app/repositories/user_repository.py`): Retrieves user profiles, fitness goals, target calories, target macros, and preferences.
- `WorkoutRepository` (`backend/app/repositories/workout_repository.py`): Authoritative store of workout routines and completed workout sessions under `users/{uid}/workout_sessions`.
- `ProgressService` (`backend/app/services/progress_service.py`): Computes streaks, total volume, workout duration, and exercise PRs.
- `NutritionService` (`backend/app/services/nutrition_service.py`): Computes daily calorie intake, macro breakdowns (protein, carbs, fat, fiber), and water logs.
- `AchievementService` (`backend/app/services/achievement_service.py`): Evaluates unlock states and points from completed activity.
- `NotificationService` (`backend/app/services/notification_service.py`): Manages user notifications under `users/{uid}/notifications`.

---

## 3. Recommended AI Architecture

### 3.1 Hybrid Grounding Architecture
The AI Coach will implement a **Deterministic Grounded Architecture**:
1. **Authoritative Deterministic Source of Truth:** All numerical fitness statistics, workout counts, streaks, calories, macros, hydration totals, PR weights, and achievements remain 100% computed by backend services from Cloud Firestore. The LLM is never allowed to invent or alter these metrics.
2. **Contextual Coaching & Reasoning Engine:** The LLM acts as an expert trainer and nutritionist that ingests a curated snapshot of the user's authentic fitness data to deliver personalized advice, routine modifications, motivation, and exercise explanations.

```mermaid
flowchart TD
    Client[React Frontend /coach] -->|1. POST /api/v1/coach/chat + Bearer Token| FastAPI[FastAPI Backend]
    FastAPI -->|2. Verify Token| FirebaseAuth[Firebase Admin Auth]
    FastAPI -->|3. Fetch Authoritative Snapshot| DataServices[Progress, Nutrition, Workout, User Services]
    DataServices -->|4. Query Data| Firestore[(Cloud Firestore)]
    FastAPI -->|5. Build Bounded Prompt + History| ContextBuilder[Coach Context & Prompt Builder]
    ContextBuilder -->|6. Execute LLM Call| Gemini[Google Gemini 1.5/2.5 Flash]
    Gemini -->|7. Return Response| FastAPI
    FastAPI -->|8. Persist User & Assistant Messages| FirestoreConv[users/{uid}/coach_conversations]
    FastAPI -->|9. JSON Response| Client
```

---

## 4. RAG Decision: Vector RAG vs Structured User-Context Retrieval

| Technology | Needed in Phase 8? | Assessment & Rationale |
|---|---|---|
| **Vector Database (Pinecone, Chroma, Qdrant)** | **NO / REJECTED** | User fitness data is structured relational logs (sessions, sets, macros). Converting numerical logs into vector embeddings adds latency, external infrastructure, and indexing errors without benefit. |
| **Document Embeddings** | **NO / REJECTED** | There is no unstructured corpus of documents to search. Exercise catalogues and user logs are structured Firestore documents. |
| **LangChain / LangGraph** | **NO / REJECTED** | Adds unnecessary abstraction layers, heavy dependencies, slow startup times, and debugging complexity for a direct conversational coaching pipeline. |
| **Structured User-Context Retrieval** | **YES / RECOMMENDED** | Directly queries existing FastAPI services (`progress_service`, `nutrition_service`, `user_repo`) and compiles a concise, deterministic Markdown/JSON context object (< 700 tokens). |

**Architectural Recommendation:** **DO NOT IMPLEMENT VECTOR RAG.** Use **Structured User-Context Retrieval** directly from existing backend services.

---

## 5. User Context Architecture

To maintain high response speed and low token costs, the LLM will receive a bounded, deterministic snapshot:

### 5.1 Context Payload Components
1. **User Profile:** Name, fitness goal (*muscle gain*, *fat loss*, *strength*, *endurance*), experience level (*beginner*, *intermediate*, *advanced*), daily target calories, daily target protein, daily target water.
2. **Coaching Settings:** Persona/Tone (*encouraging*, *strict*, *scientific*), Focus area (*hypertrophy*, *fat loss*, *strength*, *recovery*).
3. **Activity Snapshot (Past 7 Days):**
   - Active workout streak (e.g., 3 days).
   - Workouts completed this week (e.g., 4 sessions).
   - Total volume lifted (e.g., 14,250 kg).
   - Most recent workout session (date, routine name, duration).
   - Recent Personal Records (top 2 exercises and weights).
4. **Nutrition & Hydration Snapshot (Today):**
   - Consumed vs target calories (e.g., 1,850 / 2,400 kcal).
   - Consumed vs target protein (e.g., 135 / 160 g).
   - Consumed vs target water (e.g., 2.2 / 3.0 L).
5. **Achievements:** Total points, current level tier, latest unlocked badge.

### 5.2 Token Budget
- **User Context Snapshot:** ~350 – 600 tokens.
- **Conversation History (Last 6–8 messages):** ~400 – 800 tokens.
- **System Instructions & Boundaries:** ~400 tokens.
- **Current User Query:** ~50 – 150 tokens.
- **Total Prompt Budget:** < 2,000 tokens (well within the free-tier Gemini limits).

---

## 6. Conversation Architecture

### 6.1 Firestore Collection Structure
Conversations and messages will persist under the authenticated user's scope:

```
users/{uid}/coach_conversations/{conversation_id}
users/{uid}/coach_conversations/{conversation_id}/messages/{message_id}
```

### 6.2 Document Fields
1. **Conversation Document (`users/{uid}/coach_conversations/{id}`):**
   - `id`: string (e.g. `conv_1788697200`)
   - `title`: string (derived from initial prompt or auto-generated, e.g. "Workout Plan Advice")
   - `createdAt`: string (ISO8601 UTC)
   - `updatedAt`: string (ISO8601 UTC)
   - `previewText`: string (snippet of most recent message)
   - `messageCount`: number
2. **Message Document (`users/{uid}/coach_conversations/{id}/messages/{msg_id}`):**
   - `id`: string (e.g. `msg_1788697205_user`)
   - `conversationId`: string
   - `sender`: string (`'user' | 'assistant'`)
   - `text`: string
   - `createdAt`: string (ISO8601 UTC)
   - `tokensUsed`: optional number

### 6.3 Sliding Window & Retention
- **Prompt Window:** The LLM receives only the last 6 to 8 messages of the conversation, maintaining continuity without unbounded context expansion.
- **Retention Cap:** Retain up to 20 conversations per user and up to 50 messages per conversation. Older conversations can be pruned or archived.

---

## 7. LLM Provider Analysis & Recommendation

### 7.1 Provider Comparison

| Criteria | Google Gemini (Gemini 1.5 / 2.5 Flash) | OpenAI (GPT-4o-mini) | Anthropic (Claude 3.5 Haiku) |
|---|---|---|---|
| **Free Tier / Development Access** | **Generous Free Tier** (15 RPM, 1,500 RPD in AI Studio) | No free tier (Prepaid credits required) | No free tier (Prepaid credits required) |
| **Production Cost** | Extremely low ($0.075 / 1M input tokens) | Low ($0.15 / 1M input tokens) | Low ($0.25 / 1M input tokens) |
| **Response Latency** | **Fast (< 1.2s average)** | Fast (~1.5s) | Fast (~1.4s) |
| **Context Window** | 1,000,000+ tokens | 128,000 tokens | 200,000 tokens |
| **SDK / Python Integration** | Native Python SDK / standard REST | Official Python SDK | Official Python SDK |
| **Ecosystem Synergy** | **Matches Firebase / GCP stack** | Separate ecosystem | Separate ecosystem |

### 7.2 Provider Recommendation
**Google Gemini (Gemini 1.5 Flash / 2.5 Flash)** is the recommended provider for Phase 8:
- Generous free tier for development and testing without immediate billing setup.
- Exceptional speed and low latency for chat responses.
- Native alignment with the project's Google Cloud / Firebase foundation.

---

## 8. Secret Management

- **Backend Environment Variable:** `GEMINI_API_KEY`
- **Location:** Defined in `backend/.env` (and loaded by `backend/app/core/config.py`).
- **Security Safeguards:**
  - **Zero Frontend Exposure:** Never prefixed with `VITE_`.
  - **Zero Git Tracking:** `.env` is covered by `.gitignore`.
  - **Graceful Degradation:** If `GEMINI_API_KEY` is not present, backend endpoints return a clean, user-friendly HTTP 503 error (`"AI Coach service is temporarily unconfigured"`). The server does not crash.

---

## 9. API Architecture

### 9.1 Endpoint Specifications

| Endpoint | Method | Auth Required | Request Body | Response Body | Purpose |
|---|---|---|---|---|---|
| `/api/v1/coach/dashboard` | GET | Yes (Bearer) | None | `AICoachDashboardData` | Supplies real weekly metrics, conversation history, and quick insights. |
| `/api/v1/coach/conversations` | GET | Yes (Bearer) | Query: `limit=20` | `List[AIChatConversation]` | Lists user conversation threads. |
| `/api/v1/coach/conversations` | POST | Yes (Bearer) | `{ "title": Optional[str], "initialMessage": Optional[str] }` | `AIChatConversation` | Creates a new conversation thread. |
| `/api/v1/coach/conversations/{id}/messages` | GET | Yes (Bearer) | Query: `limit=50` | `List[AIChatMessage]` | Retrieves messages for an active conversation. |
| `/api/v1/coach/chat` | POST | Yes (Bearer) | `AICoachChatRequest` | `AICoachChatResponse` | Sends user message, generates AI response, persists both, and returns them. |
| `/api/v1/coach/conversations/{id}` | DELETE | Yes (Bearer) | None | `{ "success": True }` | Deletes a conversation thread. |
| `/api/v1/coach/settings` | PATCH | Yes (Bearer) | `AICoachSettingsUpdate` | `AICoachSettingsData` | Updates persona tone and focus preferences. |

### 9.2 Request & Response Schemas
```python
class AICoachChatRequest(BaseModel):
    conversation_id: Optional[str] = None
    message: str = Field(..., min_length=1, max_length=1000)

class AIChatMessageSchema(BaseModel):
    id: str
    conversationId: str
    sender: Literal["user", "assistant"]
    timestamp: str  # e.g. "2:30 PM"
    text: str

class AICoachChatResponse(BaseModel):
    conversation_id: str
    user_message: AIChatMessageSchema
    assistant_message: AIChatMessageSchema
```

---

## 10. AI Response Pipeline

```
1. Client dispatches POST /api/v1/coach/chat with Bearer Token
2. FastAPI security dependency verifies Firebase Token -> resolves authoritative uid
3. Input validation: verify message length is between 1 and 1000 characters
4. Fetch or create conversation in users/{uid}/coach_conversations/{conversation_id}
5. Fetch last 6-8 messages for conversation history
6. Fetch bounded user context:
   - User Profile: goal, experience, calorie/protein targets
   - 7-Day Activity: streak, workout count, volume, recent PRs
   - Today's Nutrition: calories, protein, hydration
   - Coach Settings: tone, focus
7. Compile system prompt + structured context + sliding history + user query
8. Call Gemini API (with 12s timeout and safety filters)
9. Parse & validate AI output text
10. Persist user message to Firestore
11. Persist assistant response message to Firestore
12. Update conversation document (updatedAt, previewText, messageCount)
13. Return AICoachChatResponse JSON to client
14. React UI renders new messages and smoothly scrolls viewport
```

---

## 11. Prompt Architecture

### 11.1 System Instruction Blueprint
```markdown
You are the AI Fitness Coach in the AI FITNESS application.
Your goal is to guide the user toward their health, fitness, and strength goals with evidence-based advice, empathy, and clarity.

[COACHING PERSONA]
- Tone: {{USER_COACHING_TONE}} (Encouraging / Strict / Scientific)
- Focus: {{USER_PRIMARY_FOCUS}} (Hypertrophy / Fat Loss / Strength / Recovery)

[USER CONTEXT]
- Name: {{USER_NAME}}
- Primary Goal: {{USER_GOAL}} | Experience: {{USER_EXPERIENCE}}
- Daily Targets: {{TARGET_CALORIES}} kcal | {{TARGET_PROTEIN}}g protein | {{TARGET_WATER}}L water
- Active Streak: {{ACTIVE_STREAK}} days | Workouts This Week: {{WEEKLY_WORKOUTS}}
- Recent PRs: {{RECENT_PRS}}
- Today's Nutrition: {{CONSUMED_CALORIES}}/{{TARGET_CALORIES}} kcal | {{CONSUMED_PROTEIN}}/{{TARGET_PROTEIN}}g protein | {{CONSUMED_WATER}}/{{TARGET_WATER}}L water

[CORE RULES]
1. GROUNDING: Use the authoritative numbers provided above. Never invent past workouts, calories, or PRs. If data is absent, politely state that it hasn't been logged yet.
2. SCOPE: Focus exclusively on exercise programming, training technique, progressive overload, recovery, and general sports nutrition.
3. FORMAT: Keep responses structured, concise, and actionable using bullet points and bold highlights where appropriate.
```

---

## 12. Safety & Fitness Boundaries

| User Input Scenario | Coach Action | Response Strategy |
|---|---|---|
| **Routine / Exercise Optimization** | **Answer Normally** | Provide split recommendations, rep ranges, rest intervals, exercise form tips. |
| **Macro / Nutrition Queries** | **Answer Normally** | Give protein timing, hydration advice, meal ideas fitting user's remaining calories/protein. |
| **Mild Muscle Soreness (DOMS)** | **Answer with Caution** | Differentiate between normal DOMS and acute injury; recommend active recovery and hydration. |
| **Sharp Joint Pain / Injury** | **Refuse & Redirect** | Explicitly state: *"I cannot diagnose injuries. Please discontinue the movement and consult a physical therapist or doctor."* |
| **Extreme Calorie Restriction / ED** | **Refuse & Guide Safely** | Refuse dangerously low caloric deficits (<1200 kcal for women, <1500 kcal for men) and encourage balanced nutrition. |
| **Prescription Drugs / Anabolics** | **Refuse** | Refuse to recommend or advise on prescription medications or performance-enhancing drugs. |

---

## 13. Deterministic Data vs AI Data Boundaries

| Domain Metric | Source of Truth | Permitted Role of LLM |
|---|---|---|
| **Workout Logs & Sets** | `WorkoutRepository` (Firestore) | Can explain volume trends; cannot invent past workouts. |
| **Calorie & Macro Totals** | `NutritionRepository` (Firestore) | Can suggest meals to fill remaining targets; cannot invent logged meals. |
| **Hydration Intake** | `NutritionRepository` (Firestore) | Can remind user of daily target; cannot fabricate logged water. |
| **Personal Records (PRs)** | `ProgressService` (Firestore) | Can celebrate authentic PRs; cannot fabricate new records. |
| **Streak Days** | `ProgressService` (Firestore) | Can motivate user to maintain streak; cannot change streak counter. |
| **Weekly Overview Progress** | Backend Services (Firestore) | Displayed on UI cards via deterministic API calculations. |

---

## 14. Error and Failure Handling

1. **Missing or Invalid `GEMINI_API_KEY`:**
   - Backend responds with `503 Service Unavailable`: `{"detail": "AI Coach service is unconfigured. Please contact support or check settings."}`
   - Frontend renders a non-crashing alert banner with guidance.
2. **Provider Timeout (> 12s):**
   - Backend cancels request and returns `504 Gateway Timeout`: `{"detail": "AI Coach took too long to respond. Please try again."}`
3. **Provider Rate Limit (HTTP 429):**
   - Backend returns `429 Too Many Requests`: `{"detail": "AI Coach is currently experiencing high demand. Please wait a moment."}`
4. **Invalid User Input:**
   - Empty input or input > 1,000 characters returns `422 Unprocessable Entity`.
5. **Firestore Write Failure:**
   - If message persistence fails after LLM generation, the assistant response is returned to the user with a warning logged in the backend.

---

## 15. Rate Limiting and Cost Control

- **User Rate Limit:** Maximum 10 messages per minute and 50 messages per 24-hour rolling window per user.
- **Input Character Limit:** Strictly enforced at 1,000 characters.
- **Output Token Cap:** Capped at 800 output tokens (~600 words) per completion.
- **History Pruning:** Only the most recent 6–8 messages are sent to the model.
- **Cost Impact:** Under Google Gemini Flash free tier, 100% of development and initial user load is free ($0.00).

---

## 16. Streaming vs Non-Streaming Analysis

| Metric | Streaming (SSE / Chunked) | Non-Streaming (Standard REST) |
|---|---|---|
| **Latency to First Token** | ~400ms | N/A |
| **Total Response Time** | ~1.2s | ~1.2s (Gemini Flash is extremely fast) |
| **Frontend Complexity** | High (ReadableStream, custom event listeners, state hydration) | Low (Standard `useMutation` with React Query) |
| **Firestore Persistence** | Complex (Requires accumulating tokens before saving) | Clean & Atomic (Save complete message in one write) |
| **Testing & Mocking** | Complex | Simple, reliable, standard HTTP mocks |

**Recommendation for Phase 8:** **Non-Streaming REST**.
Because Gemini Flash delivers full completions in approximately 1.0 to 1.5 seconds, standard REST with an animated loading skeleton provides a clean, responsive UX with vastly simpler architecture, zero race conditions, and robust automated testability.

---

## 17. Security Model

- **Authentication:** All `/coach` endpoints require `Authorization: Bearer <Firebase_ID_Token>`.
- **Identity Derivation:** User UID is strictly derived from the verified token. Client-supplied UIDs are rejected.
- **Cross-User Data Isolation:** All conversation reads and writes query `users/{uid}/coach_conversations`. User B cannot access User A's conversations.
- **Prompt Injection Defense:** User messages are encapsulated inside strict XML boundary tags (`<user_message>...</user_message>`) in the model prompt. System instructions explicitly state that user inputs cannot alter core persona, system instructions, or safety boundaries.

---

## 18. Testing Strategy

### 18.1 Automated Backend Tests (Pytest)
1. `test_coach_auth_required`: Unauthenticated requests to all `/coach` endpoints return HTTP 401.
2. `test_coach_chat_success`: Mocked Gemini client returns valid completion; verifies response format and Firestore message persistence.
3. `test_coach_context_builder`: Verifies user profile, streak, today's calories, and PRs are accurately embedded into the prompt.
4. `test_coach_input_validation`: Message exceeding 1,000 characters or empty message returns HTTP 422.
5. `test_coach_missing_key_behavior`: Missing `GEMINI_API_KEY` returns HTTP 503 without application crash.
6. `test_coach_provider_timeout`: Provider timeout returns HTTP 504.
7. `test_coach_cross_user_isolation`: User B cannot read or delete User A's conversation.
8. `test_coach_conversation_crud`: Create, list, retrieve, and delete conversation threads.

### 18.2 Frontend & E2E Validation
- Verify chat input sends message, displays user bubble immediately, shows loading indicator, and renders assistant response.
- Verify suggested question clicks dispatch message and update chat history.
- Verify Coach settings modal updates tone and focus.
- Verify responsive viewports (390px mobile to 1536px desktop).

---

## 19. Observability & Logging

- **Logged Fields:** Request ID, user UID (hashed/anonymized in production), endpoint, LLM latency (ms), token count (prompt + completion), HTTP status.
- **Redacted Information:** API keys, raw user credentials, and sensitive conversational text are never logged in plain text.

---

## 20. Deferred Features (Post-Phase 8)

The following features are strictly out of scope for Phase 8 and will be considered in future iterations:
1. **Vector RAG & Document Embeddings**: Out of scope (unnecessary for structured user logs).
2. **Audio / Speech-to-Text & Text-to-Speech**: Out of scope (existing UI playlist controls remain cosmetic).
3. **Computer Vision Form Analysis**: Belongs to Phase 9 / dedicated Form Analysis phase.
4. **FCM / External Push Notifications**: Excluded per project guidelines.
5. **Streaming Server-Sent Events (SSE)**: Excluded in favor of fast, atomic non-streaming completions.

---

## 21. Exact Implementation Phases

### Phase 8A — Backend Foundation & Data Schemas
- Define Pydantic schemas in `backend/app/schemas/coach.py` (`AICoachChatRequest`, `AIChatMessageSchema`, `AIChatConversationSchema`, `AICoachDashboardDataSchema`).
- Add `GEMINI_API_KEY` setting to `backend/app/core/config.py`.
- Create `backend/app/repositories/coach_repository.py` for Firestore operations under `users/{uid}/coach_conversations`.

### Phase 8B — User Context & Prompt Engineering
- Create `backend/app/services/coach_context_service.py`: Queries `user_repo`, `workout_repo`, `progress_service`, and `nutrition_service` to build the bounded user snapshot.
- Create system instruction templates and prompt assembler with safety boundaries.

### Phase 8C — Gemini LLM Integration
- Create `backend/app/services/llm_client.py`: Wrapper for Google Gemini API (using `google-genai` SDK or `httpx` async client).
- Implement timeout handling, error translation, rate limiting, and response parsing.

### Phase 8D — Coach Domain Service & API Endpoints
- Create `backend/app/services/coach_service.py`: Orchestrates context building, LLM execution, and Firestore message persistence.
- Create `backend/app/api/v1/endpoints/coach.py`: Implements `/dashboard`, `/conversations`, `/chat`, `/settings`.
- Register router in `backend/app/api/v1/router.py`.

### Phase 8E — Frontend Service & React Hook Integration
- Update `src/services/aiCoachService.ts` to replace mock data with authenticated API calls to `/api/v1/coach/*`.
- Update `src/hooks/useAICoach.ts` to support active conversation switching, message sending, and dashboard state queries.
- Ensure all existing UI components render live data with zero visual breakage.

### Phase 8F — Automated Tests & Build Verification
- Write comprehensive backend test suite in `backend/tests/test_coach.py`.
- Verify 100% test pass rate (`py -m pytest backend/tests/ -v`).
- Execute frontend production build (`npm run build`).

### Phase 8G — Live End-to-End QA
- Audit live running frontend and backend in browser and Firestore.
- Generate Phase 8 QA audit report.

---

## 22. Files Expected to Change During Implementation

### Backend Files to Create:
- `backend/app/schemas/coach.py`
- `backend/app/repositories/coach_repository.py`
- `backend/app/services/coach_service.py`
- `backend/app/services/coach_context_service.py`
- `backend/app/services/llm_client.py`
- `backend/app/api/v1/endpoints/coach.py`
- `backend/tests/test_coach.py`

### Backend Files to Modify:
- `backend/app/core/config.py` (Add `GEMINI_API_KEY: Optional[str] = None`)
- `backend/app/api/v1/router.py` (Uncomment and register `coach_router`)

### Frontend Files to Modify:
- `src/services/aiCoachService.ts` (Connect real API endpoints)
- `src/hooks/useAICoach.ts` (Connect real conversation queries and mutations)
- `src/pages/app/AICoachPage.tsx` (Wire active conversation state to real query data)

---

## 23. Credential Gate

> [!IMPORTANT]
> **STOP AT THE CREDENTIAL GATE.**
> Implementation of Phase 8 will require an external LLM API key.

1. **Provider:** Google AI Studio (Google Gemini)
2. **Exact Credential:** Gemini API Key
3. **Where to Obtain It:** [https://aistudio.google.com/app/apikey](https://aistudio.google.com/app/apikey)
4. **Exact Backend Environment Variable:** `GEMINI_API_KEY`
5. **Billing / Quota Configuration:** The standard free tier (15 requests per minute, 1,500 requests per day) is completely free of charge and requires no credit card for development.
6. **Other Credentials Required:** None. All user authentication and database access continues through the existing Firebase Admin configuration.

**Do not implement the API integration or write placeholder keys into configuration files until authorized.**

---

PHASE 8 PLANNING COMPLETE — AWAITING REVIEW
