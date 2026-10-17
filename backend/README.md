# AI FITNESS — Backend Foundation (Phase 1)

This is the production-grade **FastAPI** backend for the **AI FITNESS** platform. It provides high-performance asynchronous REST APIs, Pydantic data validation, and an architecture ready for **Firebase Authentication** and **Cloud Firestore**.

---

## 1. Architecture Overview

```
backend/
├── app/
│   ├── main.py                     # FastAPI application, CORS, global exception handlers, router mounts
│   ├── api/
│   │   ├── deps.py                 # Dependency injection (get_settings, get_current_user via Firebase token)
│   │   └── v1/
│   │       ├── router.py           # v1 router grouping
│   │       └── endpoints/
│   │           └── health.py       # GET /health, system diagnostics
│   ├── core/
│   │   ├── config.py               # Pydantic-settings Settings class
│   │   ├── security.py             # Firebase ID token validation and security handlers
│   │   └── firebase.py             # Safe, lazy Firebase Admin SDK initialization
│   ├── schemas/                    # Pydantic models aligned with frontend TypeScript interfaces
│   │   ├── common.py               # HealthResponse, ErrorResponse, ApiResponse
│   │   ├── user.py                 # UserProfile, PersonalInformation, FitnessGoal schemas
│   │   ├── workout.py              # Workout, WorkoutExercise, WorkoutSet, Exercise schemas
│   │   ├── nutrition.py            # DailyNutrition, Meal, FoodItem schemas
│   │   ├── progress.py             # ProgressSummary, BodyComposition, StrengthPR schemas
│   │   ├── form_analysis.py        # FormAnalysisSession schemas
│   │   ├── achievement.py          # Achievement, Leaderboard schemas
│   │   └── notification.py         # NotificationItemData, Preferences schemas
│   ├── services/                   # Business logic layer (future modules)
│   ├── repositories/               # Cloud Firestore abstraction layer (future modules)
│   ├── models/                     # Internal domain entities (future modules)
│   └── utils/
│       └── logger.py               # Structured logging configuration
├── tests/
│   ├── conftest.py                 # Pytest fixtures and FastAPI TestClient
│   ├── test_health.py              # Verification of /health & /api/v1/health endpoints
│   └── test_schemas.py             # Schema validation and roundtrip tests
├── requirements.txt                # FastAPI, uvicorn, pydantic, firebase-admin, pytest, httpx
├── .env.example                    # Placeholder environment template with documentation
├── .gitignore                      # Python and environment ignores
└── README.md                       # Complete setup and architecture guide
```

---

## 2. Tech Stack

- **Framework**: [FastAPI](https://fastapi.tiangolo.com/) (Python 3.10+)
- **Validation**: [Pydantic v2](https://docs.pydantic.dev/) & `pydantic-settings`
- **Server**: [Uvicorn](https://www.uvicorn.org/) (ASGI)
- **Identity & Auth**: [Firebase Authentication](https://firebase.google.com/docs/auth) (via `firebase-admin`)
- **Database**: [Cloud Firestore](https://firebase.google.com/docs/firestore) (via `firebase-admin`)
- **Testing**: [pytest](https://docs.pytest.org/) & [HTTPX](https://www.python-httpx.org/)

---

## 3. Quick Start

### 1. Create and activate a virtual environment

```bash
# Windows
py -m venv .venv
.venv\Scripts\activate

# Linux / macOS
python3 -m venv .venv
source .venv/bin/activate
```

### 2. Install dependencies

```bash
pip install -r requirements.txt
```

### 3. Configure environment variables

Copy `.env.example` to `.env`:

```bash
cp .env.example .env
```

*(Note: During Phase 1, you can run the server and test suite without any external credentials. Firebase Admin runs safely in local dev mode until credentials are provided.)*

### 4. Run the development server

```bash
uvicorn backend.app.main:app --reload --port 8000
```

- **Interactive API Docs (Swagger)**: [http://localhost:8000/docs](http://localhost:8000/docs)
- **Alternative Docs (ReDoc)**: [http://localhost:8000/redoc](http://localhost:8000/redoc)
- **Health Check**: [http://localhost:8000/health](http://localhost:8000/health)

---

## 4. Running Tests

```bash
py -m pytest backend/tests/ -v
```

---

## 5. Firebase Configuration Guide (When Ready)

To enable live Firebase Authentication and Cloud Firestore:

1. Go to the [Firebase Console](https://console.firebase.google.com/).
2. Create or select your project.
3. Enable **Firebase Authentication** (Email/Password, Google).
4. Enable **Cloud Firestore** in Production or Test mode.
5. Go to **Project Settings** > **Service accounts** tab.
6. Click **Generate new private key** and download the JSON file.
7. Save the file in a secure local directory (e.g., `backend/credentials/serviceAccountKey.json`).
   - **CRITICAL**: Never commit this file to Git! The backend `.gitignore` automatically ignores `*serviceAccount*.json`.
8. Set the path in `backend/.env`:
   ```env
   FIREBASE_PROJECT_ID="your-project-id"
   FIREBASE_SERVICE_ACCOUNT_PATH="credentials/serviceAccountKey.json"
   FIREBASE_STORAGE_BUCKET="your-project-id.appspot.com"
   ```

---

## 7. Phase 4 — Progress & Analytics Endpoints

The progress analytics module processes completed workout sessions strictly from:
`users/{firebase_uid}/workout_sessions/{session_id}` where `status == "completed"`.

### Endpoints (Authenticated via Bearer ID token)
- `GET /api/v1/progress/summary?period={7d|30d|90d|all}`: Aggregated workouts, volume, duration, calories, consistency streak.
- `GET /api/v1/progress/dashboard?period={7d|30d|90d|all}`: Full dashboard with KPIs, strength progression, body composition, muscle group breakdowns, PRs, and recent workouts.
- `GET /api/v1/progress/volume?period={7d|30d|90d|all}`: Upper body, lower body, and total daily volume time series.
- `GET /api/v1/progress/exercises/{exercise_id}`: Exercise-specific 1RM (Epley formula), PR milestones, and chronological history.

### Analytics & Calculation Methodology
- **Single Source of Truth**: Only completed sessions (`status == "completed"`) are aggregated. In-progress or cancelled sessions are excluded.
- **Volume**: Computed strictly from actual recorded sets: `actualReps * actualWeightKg` (never target values).
- **1RM Estimation**: Calculated using the standard Epley formula: `1RM = weight * (1 + reps / 30)`.
- **Streaks**: Deterministically calculated consecutive days with at least one completed session leading up to today or yesterday. Broken streaks reset cleanly to 0.
- **Zero States**: When no completed workouts exist, endpoints return deterministic zeros (`0`, `0.0`, `"0%"`) without errors.

---

## 8. Phase 5 — Nutrition Architecture

The Nutrition module provides daily food and meal logging, water intake tracking, 7-day weekly history, and curated food catalogue search, with deterministic calculations and insights.

### Firestore Data Model
- **User Nutrition History (Single Source of Truth)**:
  `users/{firebase_uid}/nutrition_logs/{YYYY-MM-DD}`
  Contains:
  - `date`, `userId`, `updatedAt`
  - Targets: `targetCalories`, `targetProteinGrams`, `targetCarbsGrams`, `targetFatGrams`, `targetFiberGrams`, `targetSugarGrams`, `targetSodiumMg`, `waterTargetLiters`
  - Consumed totals: `consumedCalories`, `consumedProteinGrams`, `consumedCarbsGrams`, `consumedFatGrams`, `consumedFiberGrams`, `consumedSugarGrams`, `consumedSodiumMg`, `waterIntakeLiters`
  - `meals`: Array of meals (`breakfast`, `lunch`, `dinner`, `snack`) containing individual `foods` items
  - Client view artifacts: `nutrientTargets`, `calorieFlow`, `weeklySummary`, `insights`
- **Global Food Catalogue**:
  `foods/{food_id}`
  Contains curated fitness staple foods (60+ items). User-created custom foods are stored solely inside the user's logged meals and are NEVER pushed to the global catalogue.

### Endpoints (Authenticated via Bearer ID Token)
- `GET /api/v1/nutrition/daily?date=YYYY-MM-DD`: Retrieves or initializes daily log for explicit calendar date.
- `POST /api/v1/nutrition/meals`: Logs a food item into a meal category (`breakfast`, `lunch`, `dinner`, `snack`).
- `DELETE /api/v1/nutrition/meals/{meal_id}/foods/{food_id}?date=YYYY-MM-DD`: Deletes a food item and recalculates meal and daily totals.
- `POST /api/v1/nutrition/water`: Logs water intake (increments up to safe cap).
- `GET /api/v1/nutrition/weekly?date=YYYY-MM-DD`: Returns exactly 7 days ending on the selected date.
- `GET /api/v1/nutrition/foods?query=text&category=category`: Case-insensitive text and category search over curated catalogue.

### Critical Calorie Rule & Deterministic Calculations
- **Authoritative Calorie Retention**: Food calories supplied by the catalogue or user input are authoritative. They are **never overwritten** with $P \times 4 + C \times 4 + F \times 9$.
  $$consumedCalories = \sum food.calories$$
- **4/4/9 Formula Usage**: The $4/4/9$ formula is used **strictly** for macro caloric contribution and the Macro Breakdown chart:
  $$P_{kcal} = Protein \times 4, \quad C_{kcal} = Carbs \times 4, \quad F_{kcal} = Fat \times 9$$
  $$TotalMacroKcal = P_{kcal} + C_{kcal} + F_{kcal}$$
  $$P\% = \frac{P_{kcal}}{TotalMacroKcal} \times 100, \quad C\% = \frac{C_{kcal}}{TotalMacroKcal} \times 100, \quad F\% = \frac{F_{kcal}}{TotalMacroKcal} \times 100$$
- **Serving Size Scaling**:
  For catalogue foods with nutrition per 100g:
  $$nutrient = \frac{nutrientPer100g}{100} \times servingSizeGrams$$
- **Calorie Flow**:
  $$Remaining = \max(0, targetCalories - consumedCalories)$$
- **Fiber, Sugar, Sodium Totals**:
  Accurately aggregated sums of actual logged food items.
- **Deterministic Rule-Based Insights**:
  Evaluated purely through deterministic thresholds without external AI/LLM APIs.

### Security & UID Isolation
- Every endpoint enforces `get_current_user` dependency.
- Firebase UID is extracted exclusively from the cryptographically verified Bearer ID token. Client-provided UIDs are never accepted or trusted.
- Comprehensive cross-user isolation prevents User A from accessing, mutating, or deleting User B's nutrition logs.

### No New Credentials
Phase 5 introduces NO new external API keys or credentials. No USDA, Nutritionix, Gemini, or third-party nutrition services are required or used. Everything operates deterministically with the existing Firebase setup.

---

## 9. Phase 6 — Achievements & Badges Architecture

The Achievements module provides a deterministic, data-driven gamification and milestone engine. Achievement states are derived directly from authoritative activity logs:
- `users/{uid}/workout_sessions` (completed sessions only)
- `users/{uid}/nutrition_logs` (actual daily logs and water targets)

### Firestore Data Model
- **Global Achievement Definitions**:
  `achievements/{achievement_id}`
  Contains read-only system definitions (24 initial definitions across 6 categories):
  - `id`: Unique identifier (e.g. `first_workout`, `workouts_10`, `streak_7`, `volume_50k`, `calories_5k`, `nutrition_7`, `hydration_7`, `early_bird`)
  - `title`, `description`, `category`, `points`, `metricType`, `threshold`, `unit`, `iconName`, `color`, `order`
- **User Achievement State**:
  `users/{firebase_uid}/achievements/{achievement_id}`
  Contains:
  - `id`: Document ID matches achievement ID (or `custom_{uuid}` for user-created milestones)
  - `userId`: Verified Firebase UID
  - `achievementId`: Reference to global catalogue definition (empty for custom milestones)
  - `currentValue`: Current metric value computed deterministically
  - `targetValue`: Threshold required for unlock
  - `progressPercentage`: `min(100.0, currentValue / targetValue * 100)`
  - `isUnlocked`: Boolean indicating if threshold was achieved
  - `unlockedAt`: ISO 8601 timestamp when first unlocked (preserved across re-evaluations)
  - `isNew`: Boolean flag indicating recent unlock (cleared via `/clear-new`)
  - `isCustom`: Flag indicating user-scoped custom milestone (never placed in global catalogue)
  - `updatedAt`: Timestamp of last evaluation

### Deterministic Evaluation Rules
Activity metrics are computed directly by reusing Phase 4 analytics (`ProgressService`) and Phase 5 repositories (`NutritionRepository`):
1. **Workout Mastery**: Completed workout session count ($1, 5, 10, 25, 50$).
2. **Consistency Streaks**: Consecutive calendar days with completed sessions ($3, 7, 14, 30$).
3. **Strength PRs & Volume**:
   - Distinct personal records achieved ($1, 5, 10$ PRs).
   - Cumulative lifetime volume ($5\text{k}, 25\text{k}, 50\text{k}, 100\text{k}$ kg).
4. **Endurance**: Cumulative calories burned ($1\text{k}, 5\text{k}, 10\text{k}$ kcal).
5. **Nutrition & Hydration**:
   - Days with logged meals ($1, 7$ days).
   - Days reaching hydration target ($1, 7$ days).
6. **Special (Early Riser)**: Completed workout with `startedAt` before 07:00 local time.

### Points, Milestones & Leveling
- **Total Points**: Calculated deterministically as $\sum \text{points}$ for distinct unlocked system achievements + 100 points per custom milestone. Mutable increment counters that can drift are prohibited.
- **Unlock Idempotency**: Once unlocked, an achievement preserves its original `unlockedAt` timestamp and does not award duplicate points upon repeated evaluation.
- **Level Tiers**:
  - Level 10: Novice Lifter ($0 - 499$ pts)
  - Level 20: Apprentice ($500 - 1,499$ pts)
  - Level 30: Challenger ($1,500 - 2,999$ pts)
  - Level 40: Athlete ($3,000 - 4,999$ pts)
  - Level 50: Fitness Legend ($5,000 - 7,999$ pts)
  - Level 60: Iron Master ($8,000 - 11,999$ pts)
  - Level 70: Mythic Champion ($12,000 - 19,999$ pts)
  - Level 80: Apex Titan ($20,000+$ pts)

### Endpoints (Authenticated via Bearer ID Token)
- `GET /api/v1/achievements`: Evaluates and returns full dashboard (KPIs, recent badges, circular progress, category progress, honest user-only rank, and empty challenges).
- `POST /api/v1/achievements/evaluate`: Triggers evaluation pass and returns evaluated achievements list.
- `POST /api/v1/achievements/custom`: Creates user-scoped custom milestone, unlocks it immediately with 100 pts, and returns updated dashboard.
- `GET /api/v1/achievements/list?category={category}`: Returns all 24 definitions with user-specific progress and unlock statuses.
- `POST /api/v1/achievements/clear-new`: Acknowledges and clears `isNew` flags.

### Honest Non-Fabricated Data Policy
- **No Mock Leaderboards**: No fake users, simulated bots, or fabricated "Top 12%" statistics are returned. Only the authenticated user's real points and rank are shown (or clean unranked state).
- **No Mock Challenges**: No fake active challenges, imaginary participant counts, or artificial expiration clocks. Empty array `[]` is returned and gracefully rendered.

### Testing Command
```bash
py -m pytest backend/tests/ -v
```
All 102 tests pass cleanly (19 Phase 7 tests + 83 Phase 1-6 tests).

---

## 10. Phase 7 — Notifications Architecture

The Notifications module provides a deterministic, reliable in-app event notification system. Notification records are generated directly from authoritative domain layer events (workout completions, new personal records, milestone badge unlocks, hydration target completions, and initial user signup).

### Firestore Data Model
Authoritative notification documents are stored strictly under the authenticated user's scoped subcollection:
`users/{firebase_uid}/notifications/{notification_id}`

Persisted fields:
- `id`: Deterministic string ID (e.g., `notif_wkt_{session_id}`, `notif_ach_{achievement_id}`)
- `type`: Notification type enum (`workout_completed`, `personal_record`, `achievement_unlocked`, `hydration_milestone`, `system_welcome`)
- `category`: Category enum (`Workout`, `Nutrition`, `Achievement`, `Progress`, `System`)
- `title`: Short descriptive title string
- `message`: Contextual message body
- `createdAt`: ISO 8601 authoritative event timestamp string
- `read`: Boolean flag (initially `False`)
- `readAt`: Optional ISO 8601 timestamp string when marked read
- `important`: Boolean flag for high-priority updates
- `iconName`: Visual icon identifier matching frontend Lucide icons
- `actionLabel`: Action button label (e.g., "View Summary", "View Badges")
- `actionRoute`: Frontend navigation path (e.g., `/progress`, `/achievements`, `/nutrition`)
- `sourceId`: Optional source document reference (session ID, achievement ID, date string)

**Non-Persisted Derived Fields:**
- `timestamp`: Formatted relative or time display (e.g. "Just now", "10m ago", "09:30 AM")
- `dateGroup`: Temporal grouping ("Today", "Yesterday", "Earlier")
These display fields are never stored in Firestore to prevent stale timestamps and timezone errors. They are derived dynamically at response/UI time from `createdAt` relative to the local calendar day.

### Notification Types & Event Generation
1. **`workout_completed`**:
   - Triggered when `WorkoutService.complete_session()` marks a session COMPLETED.
   - Deterministic ID: `notif_wkt_{session_id}`.
   - Category: `Workout`, actionRoute: `/progress`.
2. **`personal_record`**:
   - Triggered when `WorkoutService.complete_session()` identifies a genuine new 1RM/heaviest set recorded during the session compared against historical sessions via Phase 4 logic.
   - Deterministic ID: `notif_pr_{session_id}_{exercise_id}`.
   - Category: `Progress`, actionRoute: `/progress`.
3. **`achievement_unlocked`**:
   - Triggered inside `AchievementService.evaluate_user_achievements()` whenever a badge transitions to unlocked (`isNew=True`).
   - Deterministic ID: `notif_ach_{achievement_id}`.
   - Category: `Achievement`, actionRoute: `/achievements`.
4. **`hydration_milestone`**:
   - Triggered inside `NutritionService.log_water()` when the day's authoritative cumulative water total first meets or exceeds the user's daily water target (`waterTargetMl`).
   - Deterministic ID: `notif_hydr_{date}`.
   - Category: `Nutrition`, actionRoute: `/nutrition`.
5. **`system_welcome`**:
   - Triggered inside `api/v1/endpoints/users.py` (`create_my_profile` and `get_my_profile`) upon initial profile provisioning.
   - Deterministic ID: `notif_sys_welcome`.
   - Category: `System`, actionRoute: `/workouts`.

### Idempotency & Fault Tolerance
- **Atomic Creation**: `NotificationRepository.create_or_ignore()` uses Firestore atomic transactions / existence checks. If the deterministic document ID already exists, creation is ignored and the existing document (with its original `createdAt` and `read` state) is left untouched.
- **Secondary Operation Decoupling**: Notifications are secondary event logs. If a notification write fails, the primary domain action (workout completion, achievement unlock, water logging, or profile creation) commits successfully and returns HTTP 200, with errors safely logged.

### Read State & Endpoints
- `GET /api/v1/notifications`: Returns paginated notification feed, unread count, today/week/important counts, category insights, and preferences.
- `GET /api/v1/notifications/unread-count`: Lightweight unread counter endpoint polled every 30s by TanStack Query while authenticated.
- `PATCH /api/v1/notifications/{notification_id}/read`: Marks a single notification as read (`read=True`, `readAt=now`). Idempotent.
- `POST /api/v1/notifications/read-all`: Atomically marks all unread notifications as read. Idempotent.

### Pagination & KPI Calculation
- **Feed Pagination**: Default limit of 50 items ordered by `createdAt DESC`. Deterministic cursor-based pagination using ISO timestamps.
- **Authoritative KPIs**: `unreadCount`, `todayCount`, `weekCount`, and `importantCount` are evaluated across the user's complete notification collection (not artificially restricted to the latest 50 feed items).
- **Category Insights**: Aggregated percentages and counts per category across the user's stored notifications.

### Retention Policy
- Maximum target cap: 100 notifications per user.
- Pruning strategy: When count > 100, the oldest **read** notifications are pruned first.
- **Unread Preservation**: Unread notifications are NEVER deleted to satisfy the cap. If all notifications are unread, the total count temporarily exceeds 100.
- Newly created notifications are never deleted.

### Preferences Decision
- In Phase 7, notification preference toggles remain client-side / UI-driven with default state returned in dashboard responses. Full server-side persistent notification preference settings are deferred until multi-channel notification infrastructure is introduced.

### Security & UID Isolation
- Every endpoint requires `Depends(get_current_user)`.
- Verified Firebase UID is extracted exclusively from the cryptographic token.
- No client-supplied UIDs are accepted. User A cannot read, mark read, or access User B's notifications.

### Phase 7 Limitations & Deferred Features
- **FCM / Push Notifications Deferred**: Firebase Cloud Messaging, APNs, Web Push (VAPID), SMS, and Email notifications are deferred. Phase 7 implements high-fidelity in-app notifications only.
- **AI Coach Notifications Deferred**: AI Coach notifications belong to Phase 8 and are not fabricated or generated. The AI Coach filter displays an honest empty state.

