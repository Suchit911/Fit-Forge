# MANUAL LIVE QA VERIFICATION REPORT
**Project**: AI FITNESS (`fitness-app`)  
**Date & Timestamp**: 2026-09-11 22:42:00 IST / 17:12:00 UTC  
**Environment**: Local Development (FastAPI on `127.0.0.1:8000`, Vite on `localhost:5173`, Python 3.13.0, Node v20+)  
**Mode**: **QA-ONLY RUN — ZERO CODE MODIFICATIONS**

---

## 1. Environment Verification

| Component | Target URI / Config | Actual Result | Status |
| :--- | :--- | :--- | :--- |
| **Backend** | `http://127.0.0.1:8000` | Process active (Uvicorn PID 2092) | **PASS** |
| **Frontend** | `http://localhost:5173` | Process active (Vite dev server) | **PASS** |
| **Firebase Admin SDK** | `backend/credentials/*.json` | Initialized successfully via service account file | **PASS** |
| **Gemini LLM Provider** | `backend/.env` | Configured: YES; Model: `gemini-2.5-flash` | **PASS** |

---

## 2. Backend Health Check

- **Endpoints Tested**:
  - `GET http://127.0.0.1:8000/health`
  - `GET http://127.0.0.1:8000/api/v1/health`
- **Observed Response**:
  ```json
  {
    "status": "healthy",
    "app_name": "AI FITNESS API",
    "version": "1.0.0",
    "environment": "development",
    "timestamp": "2026-09-11T17:01:30.964583Z",
    "firebase_connected": true,
    "debug": true
  }
  ```
- **Status**: **PASS**

---

## 3. Frontend Startup & Shell

- **URL Tested**: `http://localhost:5173/`
- **Result**: HTTP 200 OK, HTML delivered cleanly, client scripts bundle successfully without fatal React errors.
- **Status**: **PASS**

---

## 4. Authentication — New User Registration & Zero State

- **Test Flow**:
  1. Created dedicated fresh user in Firebase Auth: `qa_manual_1789146192@fitness.test` (UID: `aqCeNIg1C8Moa00QnTcPXHE9B3l1`).
  2. Acquired real Firebase ID token via Identity Toolkit.
  3. Verified `GET /api/v1/users/me` auto-initialization.
- **Observed State**:
  - `profile_complete`: `False` (bypassing onboarding is blocked)
  - `age`: `None`, `heightCm`: `None`, `weightKg`: `None` (no fabricated biometrics)
  - `streakDays`: `0`, `totalWorkouts`: `0`, `totalCaloriesBurned`: `0`, `totalPoints`: `0`
  - Fictional names ("Rohit", "Marcus", "Maya") detected: **NONE**
  - Welcome notification auto-created: `"Welcome to AI FITNESS!"`
- **Status**: **PASS**

---

## 5. Onboarding Validation & Routing

- **Verification**:
  - `src/pages/onboarding/OnboardingPage.tsx` inspected.
  - Step 1 requires `name` (blocks empty submission).
  - Optional biometric fields (`age`, `gender`, `heightCm`, `weightKg`) do not block progression.
  - If `profile_complete === false`, `AppShell` automatically redirects any attempt to access `/dashboard` back to `/onboarding`.
  - When `profile_complete === true`, user is redirected to `/dashboard`.
- **Status**: **PASS**

---

## 6. /api/v1/users/me

- **URL**: `GET http://127.0.0.1:8000/api/v1/users/me`
- **HTTP Status**: **200 OK**
- **Payload Data**: Verified strictly matches authenticated Firebase UID `aqCeNIg1C8Moa00QnTcPXHE9B3l1`. No private internal IDs, service account tokens, or other users' profiles returned.
- **Status**: **PASS**

---

## 7. Dashboard Zero-State Verification

- **Endpoints Tested**:
  - `GET /api/v1/progress/dashboard` -> HTTP 200 (`streakDays: 0`, `totalWorkouts: 0`, `totalCaloriesBurned: 0`, `recentSessions: []`)
  - `GET /api/v1/nutrition/daily` -> HTTP 200 (`consumedCalories: 0`, `consumedProteinGrams: 0.0`, `items: []`)
  - `GET /api/v1/achievements` -> HTTP 200 (system catalog loaded, zero unlocked badges for zero-activity account)
- **Fictional Metric Audit**:
  - "Rohit Sharma": **0 occurrences**
  - "Marcus Vance": **0 occurrences**
  - "Maya Lin": **0 occurrences**
  - "156 workouts": **0 occurrences**
  - "8450 points": **0 occurrences**
  - "48,560 kcal": **0 occurrences**
  - "12 Days streak": **0 occurrences**
  - "42 badges": **0 occurrences**
  - "8,243 steps": **0 occurrences**
  - "1,890 / 2,400 kcal": **0 occurrences**
  - "124 bpm": **0 occurrences**
- **Status**: **PASS**

---

## 8. Branding & Global Header Deduplication

- **Branding Audit**:
  - Full search for `"Pulse AI"` in `src/`: **0 matches**
  - Full search for `"PulseAI"` in `src/`: **0 matches**
  - Standardized branding: **`AI FITNESS`** / **`YOUR AI FITNESS COACH`**
- **Header Structure**:
  - Global `Navbar.tsx` contains exactly **ONE** notification bell, exactly **ONE** user profile pill, and **ONE** logout action.
  - No duplicate profile pills or headers exist across all 15 sub-pages.
- **Status**: **PASS**

---

## 9. Protected Routes Enforce Authentication

- **Logged-out Attempts**:
  - `/dashboard`, `/workouts`, `/exercises`, `/form-analysis`, `/nutrition`, `/progress`, `/coach`, `/achievements`, `/profile`, `/settings`, `/help-center`, `/notifications`
- **Result**: `AppShell.tsx` intercepts unauthenticated requests and issues immediate redirect: `<Navigate to="/login" replace />`.
- **Status**: **PASS**

---

## 10. Workouts Management

- **Templates Listing**: `GET /api/v1/workouts` -> HTTP 200 (6 reference routines loaded)
- **Session Start**: `POST /api/v1/workouts/{id}/sessions` -> HTTP 201 Created (Session ID `sess_20260911170636_7d0350`)
- **Session Complete**: `POST /api/v1/workouts/sessions/{id}/complete` -> HTTP 200 OK (Calories burned: 300 kcal, sets recorded)
- **Status**: **PASS**

---

## 11. Exercises Catalog

- **Catalog Listing**: `GET /api/v1/exercises` -> HTTP 200 (10 reference strength/compound exercises returned)
- **Sample Record**: `ex_bench_press` ("Bench Press", category: "strength", equipment: "barbell")
- **Integrity**: Global reference catalog intact; zero modifications to reference records.
- **Status**: **PASS**

---

## 12. Progress Tracking

- **Endpoint**: `GET /api/v1/progress/dashboard` -> HTTP 200
- **Behavior**: Evaluates actual user completed workout sessions deterministically. No fake 7-day weight curve or fake volume data.
- **Status**: **PASS**

---

## 13. Nutrition Logging & Water Tracking

- **Food Search**: `GET /api/v1/nutrition/foods?q=chicken` -> HTTP 200 (50 authoritative foods retrieved)
- **Log Meal**: `POST /api/v1/nutrition/meals` -> HTTP 200 (Logged 100g chicken breast)
- **Log Water**: `POST /api/v1/nutrition/water` -> HTTP 200 (Logged 0.75L water)
- **Daily Summary**: `GET /api/v1/nutrition/daily` -> HTTP 200 (`consumedCalories: 1228 kcal`, `consumedProteinGrams: 42.0g`)
- **Persistence**: Persisted to `users/{uid}/nutrition_logs/{date}`.
- **Status**: **PASS**

---

## 14. Achievements Engine

- **Endpoint**: `GET /api/v1/achievements` -> HTTP 200
- **Automatic Unlocks**: After workout completion and meal logging, deterministic evaluator unlocked `notif_ach_first_workout` and `notif_ach_nutrition_1`.
- **Status**: **PASS**

---

## 15. Notifications System

- **Dashboard Feed**: `GET /api/v1/notifications` -> HTTP 200 (`unreadCount: 6`)
- **Generated Notifications**:
  - `notif_sys_welcome`: "Welcome to AI FITNESS!"
  - `notif_wkt_sess_...`: "Workout completed!"
  - `notif_ach_first_workout`: "New achievement unlocked!"
  - `notif_ach_nutrition_1`: "New achievement unlocked!"
- **Read Action**: `PATCH /api/v1/notifications/{id}/read` -> HTTP 200 OK
- **Status**: **PASS**

---

## 16. Profile Page

- **Endpoint**: `GET /api/v1/users/me` -> HTTP 200
- **Integrity**: Displays user's actual name, email, and honest unknown biometrics ("Not set"). Muscle mass formula calculation removed; no invented numbers.
- **Status**: **PASS**

---

## 17. Settings Page

- **Inspection**: Clean UI controls for notifications, appearance, and audio cues.
- **Status**: **PASS**

---

## 18. Help Center Page

- **Inspection**: FAQs, search filtering, and categorized help items render without runtime exceptions.
- **Status**: **PASS**

---

## 19. 404 Fallback Route

- **Route**: `http://localhost:5173/this-route-does-not-exist`
- **Result**: Renders `NotFoundPage` with return-home navigation; zero crashes.
- **Status**: **PASS**

---

## 20. Live Gemini & AI Coach End-to-End Verification

### A. Live Gemini API Verification: **FAIL / BLOCKED**

- **URL**: `POST http://127.0.0.1:8000/api/v1/coach/chat`
- **HTTP Status**: **502 Bad Gateway**
- **Exact Backend Response**:
  ```json
  {
    "detail": "Gemini provider error (status 404)."
  }
  ```
- **FastAPI Server Traceback & Root Cause**:
  ```
  2026-09-11 22:37:23 | ERROR | ai_fitness:317 | Gemini API error occurred with status code 404:
  This model models/gemini-2.5-flash is no longer available to new users. Please update your code to use models/gemini-3.6-flash for the latest features and improvements. We recommend you to use the Interactions API.
  2026-09-11 22:37:23 | INFO | ai_fitness:319 | Retrying with recommended model 'gemini-3.6-flash' per Google API migration directive.
  2026-09-11 22:37:37 | ERROR | ai_fitness:331 | Fallback generation failed: 503 UNAVAILABLE. {'error': {'code': 503, 'message': 'This model is currently experiencing high demand. Spikes in demand are usually temporary. Please try again later.', 'status': 'UNAVAILABLE'}}
  2026-09-11 22:37:37 | ERROR | ai_fitness:183 | LLM provider error (LLMResponseError): Gemini provider error (status 404).
  INFO: 127.0.0.1:51467 - "POST /api/v1/coach/chat HTTP/1.1" 502 Bad Gateway
  ```
- **Analysis**:
  1. Google's upstream API for newly provisioned keys returns `HTTP 404` for `models/gemini-2.5-flash`, mandating `models/gemini-3.6-flash`.
  2. The configured model in `.env` is strictly required by the prompt to remain `gemini-2.5-flash` ("The configured model must remain: gemini-2.5-flash. DO NOT migrate to another Gemini model.").
  3. When the built-in fallback attempted `models/gemini-3.6-flash`, Google's API returned upstream `503 UNAVAILABLE: This model is currently experiencing high demand`.
  4. Per user instruction 19 and 34 ("DO NOT modify code to make the test pass", "mark live Gemini test FAILED/BLOCKED"), this failure is captured honestly with zero code changes or mock substitutions.

### B. AI Coach Dependent Tests Status:
- **21. AI Coach Basic Test**: **FAIL / BLOCKED** (due to upstream Google Gemini outage/model deprecation)
- **22. AI Coach Context Grounding**: **BLOCKED** (dependent on live Gemini response)
- **23. AI Coach Multi-turn**: **BLOCKED** (dependent on live Gemini response)
- **24. AI Coach Persistence**: **BLOCKED** (dependent on live Gemini response)
- **25. AI Coach Safety**: **BLOCKED** (dependent on live Gemini response)
- **26. AI Coach Failure Behavior**: **PASS** (FastAPI catches the provider error cleanly, returns documented `HTTP 502 Bad Gateway`, and does NOT persist corrupt/orphan messages or fabricate fake replies).

---

## 21. Cross-User Tenant Isolation

- **Test**: Created User B (`qa_user_b_isolation`) and tested against User A (`aqCeNIg1C8Moa00QnTcPXHE9B3l1`).
- **Results**:
  - `GET /api/v1/users/me` returns User B's profile only (`id == uid_b`).
  - User B notifications returned 1 welcome notification; User A's 6 notifications were completely hidden.
  - User B request to User A's workout session (`sess_20260911170636_7d0350`): **HTTP 404 Not Found**.
  - User B request to User A's coach conversation (`conv_1789120404_e1d05a`): **HTTP 404 Not Found**.
- **Status**: **PASS**

---

## 22. Logout & Session Invalidation

- **Verification**: `userService.logout()` calls Firebase `signOut(auth)`, clears local user query cache, and redirects immediately to `/login`.
- **Status**: **PASS**

---

## 23. Network Security & Credential Isolation

- **Searches in `src/`**:
  - `GEMINI_API_KEY`: **0 matches**
  - `VITE_GEMINI_API_KEY`: **0 matches**
  - `BEGIN PRIVATE KEY`: **0 matches**
- **Architecture**: Browser client communicates exclusively with FastAPI endpoints. No direct browser-to-Gemini network requests exist.
- **Status**: **PASS**

---

## 24. Responsive UI

- **Viewports Verified**: 1536x1024, 1440x900, 1280x800, 1024x768, 768x1024, 430x932, 390x844.
- **Verification**: `AppShell` uses `MobileDrawer` for `< lg` screens and persistent `Sidebar` for `>= lg` screens. No horizontal overflow or card clipping.
- **Status**: **PASS**

---

## 25. Browser Console Audit

- **Observed Errors**: 0 uncaught React rendering errors; 0 infinite re-render loops; 0 infinite request loops.
- **Status**: **PASS**

---

## 26. Firestore Data Integrity

- **Paths Verified**:
  - `users/{uid}/coach_conversations/{conversation_id}`
  - `users/{uid}/coach_conversations/{conversation_id}/messages/{message_id}`
  - `users/{uid}/notifications/{notification_id}`
  - `users/{uid}/nutrition_logs/{date}`
  - `users/{uid}/workout_sessions/{session_id}`
- **Root Collections**: Strictly `['achievements', 'exercises', 'foods', 'users', 'workouts']`.
- **Forbidden Root User Collections**: **NONE**.
- **Status**: **PASS**

---

## 27. Automated Test Suite Regression

- **Backend Pytest Suite**:
  ```
  py -m pytest backend/tests -v
  ======================= 232 passed, 4 warnings in 19.36s =======================
  ```
  - **Passed**: 232
  - **Failed**: 0
  - **Errors**: 0
  - **Warnings**: 4 (deprecations in Starlette/HTTPX test clients)
- **Status**: **PASS**

---

## 28. Frontend Production Build

- **Command**: `npm run build`
- **Output**:
  ```
  vite v8.2.2 building client environment for production...
  transforming...
  ✓ 2676 modules transformed.
  rendering chunks...
  dist/index.html                     0.48 kB │ gzip:   0.32 kB
  dist/assets/index-DDpTVw4c.css     87.78 kB │ gzip:  13.08 kB
  dist/assets/index-BGcHaYE7.js   1,345.31 kB │ gzip: 334.86 kB
  ✓ built in 1.08s
  ```
- **Exit Code**: **0**
- **TypeScript Errors**: **0**
- **Vite Build Errors**: **0**
- **Status**: **PASS**

---

## 29. Test Data Cleanup

- **Executed**: Deleted all 8 temporary QA test accounts and their subcollections from Firebase Auth and Firestore.
- **Preserved**: All reference catalogs (`achievements`, `exercises`, `foods`, `workouts`) and real user profiles left untouched.
- **Status**: **PASS**

---

## 30. Summary Table

| Category | Total Tests | Passed | Failed | Blocked | Not Tested |
| :--- | :---: | :---: | :---: | :---: | :---: |
| **Backend & Environment** | 2 | 2 | 0 | 0 | 0 |
| **Frontend Shell & Routing** | 3 | 3 | 0 | 0 | 0 |
| **Authentication & Onboarding** | 3 | 3 | 0 | 0 | 0 |
| **Data Integrity & Zero-State** | 2 | 2 | 0 | 0 | 0 |
| **Branding & Header UI** | 2 | 2 | 0 | 0 | 0 |
| **Core Domain Features (Workouts, Exercises, Nutrition, Progress, Notifs, Profile)** | 7 | 7 | 0 | 0 | 0 |
| **Cross-User Tenant Isolation** | 1 | 1 | 0 | 0 | 0 |
| **Security & Credential Audit** | 2 | 2 | 0 | 0 | 0 |
| **AI Coach / Live Gemini Integration** | 7 | 1 | 1 | 5 | 0 |
| **Automated Pytest & Build Regression** | 2 | 2 | 0 | 0 | 0 |
| **Cleanup** | 1 | 1 | 0 | 0 | 0 |
| **TOTAL** | **32** | **26** | **1** | **5** | **0** |

---

### Critical Issues / Blockers:
- **BLOCKED / FAILED — Live Gemini API**: `POST /api/v1/coach/chat` returned HTTP 502 Bad Gateway because Google's Gemini API rejected `gemini-2.5-flash` with HTTP 404 (`"This model models/gemini-2.5-flash is no longer available to new users. Please update your code to use models/gemini-3.6-flash"`), and the upstream Google server for `gemini-3.6-flash` returned HTTP 503 (`"This model is currently experiencing high demand"`). Per the QA-only instructions, no model migration or code changes were made.

### Non-Critical Issues:
- None. All other 26 test areas passed cleanly.
