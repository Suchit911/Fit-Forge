# AI FITNESS — PRODUCTION ARCHITECTURE & FIRESTORE DATA MODEL

AI FITNESS is a production-grade fitness intelligence platform powered by:
- **Frontend**: React 19, TypeScript, Vite, Tailwind CSS, React Router, TanStack Query, Recharts, Lucide Icons, Firebase Web SDK.
- **Backend**: Python 3.13, FastAPI, Pydantic, Firebase Admin SDK, Cloud Firestore.

---

## 1. Cloud Firestore Data Model

The Firestore database architecture maintains a clean separation between **Global Reference Data** (publicly browsable workout definitions and exercise library) and **User-Scoped Data** (strictly protected by verified Firebase Authentication ID tokens).

```
firestore
├── exercises/                           [Collection: Global Reference]
│   └── {exercise_id}                    [Document: e.g., ex_bench_press]
│
├── workouts/                            [Collection: Global Reference]
│   └── {workout_id}                     [Document: e.g., wkt_upper_push]
│
└── users/                               [Collection: User Profiles]
    └── {firebase_uid}                   [Document: User profile metadata]
        └── workout_sessions/            [Subcollection: User Workout Sessions & History]
            └── {session_id}             [Document: e.g., sess_20260905_12ba88]
```

### 1.1 Global Reference Collections

#### `exercises/{exercise_id}`
Master exercise reference library queried by `/api/v1/exercises`:
- `id`: `string` — Unique identifier (e.g. `ex_bench_press`, `ex_deadlift`, `ex_squat`).
- `name`: `string` — Display title (e.g. "Bench Press").
- `description`: `string` — Detailed biomechanical and anatomical purpose.
- `primaryMuscles`: `string[]` — Primary muscle groups involved (`chest`, `quadriceps`, `back`, etc.).
- `secondaryMuscles`: `string[]` — Secondary synergist muscles.
- `equipment`: `string[]` — Required gear (`barbell`, `dumbbells`, `cable_machine`, etc.).
- `difficulty`: `string` — `beginner` | `intermediate` | `advanced`.
- `category`: `string` — `strength` | `hypertrophy` | `endurance` | `mobility` | `cardio` | `custom`.
- `instructions`: `string[]` — Step-by-step execution cues.
- `commonMistakes`: `string[]` — Form flaws to prevent.
- `safetyNotes`: `string[]` — Spotter, safety pins, or joint precautions.
- `supportedFormAnalysis`: `boolean` — Vision tracking compatibility flag.
- `supportedCameraMode`: `string | null` — `front` | `side`.
- `imageUrl`: `string | null` — Asset preview path.
- `isCustom`: `boolean` — False for system definitions.

#### `workouts/{workout_id}`
Curated workout routines queried by `/api/v1/workouts`:
- `id`: `string` — Routine identifier (e.g. `wkt_upper_push`, `wkt_lower_strength`).
- `title`: `string` — Routine title (e.g. "Upper Body Push").
- `description`: `string` — Focus summary (e.g. "Chest, Shoulders & Triceps").
- `targetEnvironment`: `string` — `gym` | `home`.
- `estimatedDurationMinutes`: `number` — Typical workout length (e.g. `45`).
- `difficulty`: `string` — `beginner` | `intermediate` | `advanced`.
- `targetMuscles`: `string[]` — Primary muscle groups targeted.
- `exercises`: `WorkoutExercise[]` — Array of exercises with target sets:
  - `id`: `string` — Sub-item ID (`we_push_1`).
  - `exerciseId`: `string` — Reference foreign key into `exercises/{exercise_id}`.
  - `exercise`: `Exercise` — Embedded exercise metadata snapshot.
  - `sets`: `WorkoutSet[]` — Target sets array (`setNumber`, `targetReps`, `targetWeightKg`, `isCompleted`).
  - `restSecondsBetweenSets`: `number` — Rest interval in seconds (`60`, `90`, `120`).
  - `notes`: `string` — Guidance notes for the movement.
- `imageUrl`: `string | null` — Hero image banner.
- `isSystem`: `boolean` — True for curated routines.

---

### 1.2 User-Scoped Subcollections

#### `users/{firebase_uid}/workout_sessions/{session_id}`
Lifecycle tracking of active, paused, and completed workout sessions:
- `id`: `string` — Timestamped unique session ID (e.g. `sess_20260905094943_24cb4d`).
- `userId`: `string` — Authenticated Firebase UID (strictly enforced by server-verified token).
- `workoutId`: `string` — Origin workout identifier (`wkt_upper_push`).
- `workoutTitle`: `string` — Workout title at time of session initiation.
- `status`: `string` — `in_progress` | `completed` | `cancelled`.
- `startedAt`: `string` — UTC ISO-8601 timestamp.
- `completedAt`: `string | null` — UTC ISO-8601 completion timestamp.
- `durationSeconds`: `number` — Active workout elapsed time in seconds.
- `currentExerciseIndex`: `number` — Cursor for active exercise navigation.
- `currentSetIndex`: `number` — Cursor for active set navigation.
- `isPaused`: `boolean` — Pause timer status.
- `completedSets`: `Record<string, WorkoutSet[]>` — Map of exercise ID to array of completed sets (`actualReps`, `actualWeightKg`, `rpe`).
- `completedSetsCount`: `number` — Total sets finished in the workout.
- `totalSetsCount`: `number` — Total planned sets for completion percentage.
- `totalVolumeKg`: `number` — Sum of `(actualReps * actualWeightKg)` across all logged sets.
- `caloriesBurned`: `number` — Estimated energy expenditure calculated upon completion.
- `notes`: `string | null` — User or coach notes for the session.

---

## 2. API Endpoints

### 2.1 User Profile (`/api/v1/users`)
- `GET /api/v1/users/me` — Retrieves current user profile; auto-initializes if first login.
- `POST /api/v1/users/me` — Explicit profile creation.
- `PATCH /api/v1/users/me` — Partial profile update with automatic BMI recalculation.
- `PUT /api/v1/users/me` — Full profile update.

### 2.2 Exercises Library (`/api/v1/exercises`)
- `GET /api/v1/exercises` — Public list with filtering (`muscle`, `equipment`, `difficulty`, `category`, `search`).
- `GET /api/v1/exercises/{exercise_id}` — Detailed exercise specifications, cues, and muscle maps.

### 2.3 Workouts & Active Sessions (`/api/v1/workouts`)
- `GET /api/v1/workouts` — Curated routines with optional filtering (`environment`, `difficulty`, `search`).
- `GET /api/v1/workouts/today` — Featured workout routine for the current day.
- `GET /api/v1/workouts/{workout_id}` — Full workout plan including embedded exercises and target sets.
- `POST /api/v1/workouts/{workout_id}/sessions` — *(Auth Required)* Starts a new session under `users/{uid}/workout_sessions`.
- `GET /api/v1/workouts/sessions/active` — *(Auth Required)* Retrieves current in-progress workout session.
- `GET /api/v1/workouts/sessions/{session_id}` — *(Auth Required)* Retrieves specific session details with ownership verification.
- `PATCH /api/v1/workouts/sessions/{session_id}` — *(Auth Required)* Updates workout progress, records set repetitions, weights, and RPE.
- `POST /api/v1/workouts/sessions/{session_id}/complete` — *(Auth Required)* Marks session complete, logs completion time, and computes total volume and calories.
- `GET /api/v1/workouts/history` — *(Auth Required)* Lists authenticated user's completed workout history.

---

## 3. Security Architecture
1. **Bearer Token Authentication**: All user-specific endpoints extract `Authorization: Bearer <Firebase ID Token>`.
2. **Server-Side Token Verification**: Tokens are verified using `firebase_admin.auth.verify_id_token(token, check_revoked=True)`.
3. **No Client-Supplied UID Trust**: The user identity is extracted strictly from the verified token claim (`uid`). Client-provided UIDs in query strings or JSON request bodies are completely ignored.
4. **Cross-User Access Isolation**: Every session query and mutation is strictly anchored to `users/{current_user.uid}`. Automated security tests verify that a user cannot view, alter, or inject data into another user's session.
5. **Zero-Secret Client Footprint**: Backend service account JSON keys remain exclusively on the server in `backend/credentials/` (which is git-ignored). Frontend `.env.local` only receives public Firebase Web SDK client configuration.

---

## 4. Development Seed Strategy
Development seed data is defined in `backend/app/seeds/seed_data.py`.
- **Non-destructive & Idempotent**: `ensure_seeded()` inspects `exercises` and `workouts` collections before writing. If records already exist, no data is overwritten or deleted.
- **Reference Depth**: Includes 10 standard exercises across all major muscle groups and 6 full workout routines with embedded target sets and rest intervals matching the approved application screens.

---

## 5. Verification & Testing
Run backend unit test suite:
```bash
py -m pytest backend/tests/ -v
```

Run frontend production build:
```bash
npm run build
```
