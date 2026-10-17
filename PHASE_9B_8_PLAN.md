# Phase 9B.8 — Exercise Knowledge & Recommendation Foundation Implementation Plan

## Executive Overview
Phase 9B.8 establishes the foundational domain intelligence for the AI FITNESS platform: a broad, authoritative, structured **Exercise Knowledge Model**, an initial seed catalog of **100 curated exercises**, controlled taxonomies, explicit exercise relationship graphs (progression, regression, substitution, complementary), clear separation between exercise knowledge and computer vision coverage, a deterministic mapping connecting form-analysis heuristic deficiencies to corrective exercise recommendations, and a deterministic recommendation eligibility engine.

This phase deliberately decouples **exercise facts and deterministic eligibility rules** from future Gemini LLM personalization (Phase 9C). Gemini will never be the source of truth for exercise data, user metrics, or physical eligibility.

---

## 1. Current-State Inspection Report

### A. Existing Phase 3 Exercise & Workout Data
- **Exercise Schema (`backend/app/schemas/workout.py`)**:
  - Defines `ExerciseSchema` with fields: `id`, `name`, `description`, `primaryMuscles`, `secondaryMuscles`, `equipment`, `difficulty`, `category` (literal: `"strength"`, `"hypertrophy"`, `"endurance"`, `"mobility"`, `"cardio"`, `"custom"`), `instructions`, `commonMistakes`, `safetyNotes`, `supportedFormAnalysis` (boolean), `supportedCameraMode` (`"front"` | `"side"`), `imageUrl`, `isCustom`.
  - **Limitation**: Lacks movement patterns (push/pull/squat/hinge), laterality (unilateral/bilateral), compound/isolation classification, progression/regression relationship links, setup/execution cues, and fine-grained CV exercise IDs.
- **Seeded Exercises (`backend/app/seeds/seed_data.py`)**:
  - Exactly 10 exercises: `ex_bench_press`, `ex_incline_db_press`, `ex_deadlift`, `ex_squat`, `ex_cable_crossover`, `ex_landmine_press`, `ex_bulgarian_squat`, `ex_face_pull`, `ex_shoulder_press`, `ex_tricep_pushdown`.
  - Inconsistency: `supportedFormAnalysis` is marked `True` for bench press, deadlift, and squat, but `bicep_curl` is missing entirely from the seed catalog, and `ex_shoulder_press` is marked `False` even though the Phase 9B engine authoritatively supports shoulder press.
- **Exercise Repository (`backend/app/repositories/exercise_repository.py`)**:
  - Interacts with Cloud Firestore collection `exercises/{exercise_id}`.
  - Implements `ensure_seeded()` which populates `SEED_EXERCISES` if the collection is empty.
  - In-memory dictionary fallback pre-populated with `SEED_EXERCISES` for offline/test isolation.
  - Filtering supported: `muscle`, `equipment`, `difficulty`, `category`, `search`.
- **Workout Schemas & Repository (`backend/app/schemas/workout.py`, `backend/app/repositories/workout_repository.py`)**:
  - Pre-seeded with 4 routines: Full Body Strength, Upper Body Hypertrophy, Lower Body Blast, Push Power Focus.
  - Manages active workout sessions, set logging (reps, weight, RPE), and completion history.

### B. Existing User Profile & Onboarding
- **User Profile Schema (`backend/app/schemas/user.py`)**:
  - `fitnessLevel`: `"beginner" | "intermediate" | "advanced"`
  - `primaryGoal` & `secondaryGoals`: `"muscle_gain" | "fat_loss" | "strength" | "endurance" | "general_fitness"`
  - `environment`: `"gym" | "home"`
  - `availableEquipment`: List of `"bodyweight" | "dumbbells" | "barbell" | "kettlebell" | "resistance_bands" | "cable_machine" | "smith_machine" | "leg_press" | "pull_up_bar" | "yoga_mat"`
  - `workoutFrequencyDaysPerWeek` (1–7), `workoutDurationMinutes` (15–120), `preferredWorkoutType`, `preferredTrainingTime`
  - Biometrics: `heightCm`, `weightKg`, `targetWeightKg`, `bmi`, `bmr`, `tdee`.

### C. Existing Progress & Performance Context
- **Progress Tracking (`backend/app/schemas/progress.py`, `backend/app/services/progress_service.py`)**:
  - Tracks total workouts, total volume (kg), total calories, duration, consistency streaks.
  - Computes personal records per exercise (`ExerciseProgressionResponse`): `prWeightKg`, `prReps`, `prDate`, `bestEstimated1RM`, session completion history.
- **Form Analysis History (Phase 9B.7)**:
  - Persisted under `users/{uid}/form_analysis_sessions/{session_id}`.
  - Contains overall score, category scores (ROM, Technique, Symmetry, Stability), rep-by-rep breakdowns, and specific heuristic deficiency findings (e.g. `insufficient_depth`, `valgus_knee`, `elbow_flare`, `lumbar_rounding`).

### D. Existing Coach Context Pipeline
- **`CoachContextService` (`backend/app/services/coach_context_service.py`)**:
  - Assembles deterministic context for user profile, recent activity, nutrition, achievements, and biometrics.
  - Strictly establishes that AI/LLMs are consumers of authoritative data, never generators of raw physical facts.

### E. Existing Frontend Presentation
- **`src/pages/app/ExercisesPage.tsx`**: Search bar, category filter chips (muscle, equipment, difficulty), stats strip, popular exercises, muscle group browsing, newly added list, custom exercise modal.
- **`src/pages/app/ExerciseDetailsPage.tsx`**: Hero card with muscles/equipment/difficulty, instructions card, animation guide, set/rep recommendations, equipment needed, similar exercises panel, personal records panel.
- **`src/components/exercise/SimilarExercisesPanel.tsx`**: Currently renders hardcoded mock cards; ripe for wiring to authoritative relationship graphs.

---

## 2. Exercise Knowledge Model Design

The enhanced `ExerciseKnowledgeSchema` extends and supersedes the basic `ExerciseSchema`, preserving complete backward compatibility while adding rich structured metadata:

### A. Identity & Localization
- `id`: Canonical slugified identifier (e.g., `"ex_barbell_back_squat"`, `"ex_dumbbell_romanian_deadlift"`).
- `name`: Authoritative display title (e.g., `"Barbell Back Squat"`).
- `aliases`: List of common alternative names (e.g., `["Back Squat", "High Bar Squat", "Olympic Squat"]`).
- `description`: Objective biomechanical summary of the movement.

### B. Biomechanical Classification
- `movement_pattern`: Controlled taxonomy (e.g., `"squat"`, `"hinge"`, `"horizontal_push"`, `"horizontal_pull"`, `"vertical_push"`, `"vertical_pull"`, `"lunge"`, `"isolation"`, `"core_anti_extension"`, `"core_anti_rotation"`, `"carry"`).
- `category`: Primary training stimulus (`"strength"`, `"hypertrophy"`, `"endurance"`, `"mobility"`, `"activation_warmup"`, `"cardio"`).
- `exercise_type`: `"compound" | "isolation"`.
- `laterality`: `"bilateral" | "unilateral" | "alternating"`.
- `plane_of_motion`: `"sagittal" | "frontal" | "transverse" | "multi_planar"`.

### C. Anatomy & Muscle Engagement
- `primary_muscles`: Primary prime movers (List of controlled `MuscleGroup`).
- `secondary_muscles`: Synergists and dynamic stabilizers (List of controlled `MuscleGroup`).
- `stabilizer_muscles`: Isometric stabilizers (e.g., core, erectors, rotator cuff).

### D. Equipment & Environmental Compatibility
- `required_equipment`: Minimum necessary gear (List of controlled `EquipmentType`).
- `optional_equipment`: Non-mandatory enhancers (e.g., `"weight_belt"`, `"lifting_straps"`, `"chalk"`).
- `environment_compatibility`: List of environments where executable (`"gym"`, `"home"`, `"outdoor"`, `"anywhere"`).

### E. Execution & Coaching Cues
- `difficulty`: `"beginner" | "intermediate" | "advanced"`.
- `setup_cues`: Step-by-step preparation checkpoints before initiating movement.
- `execution_cues`: Dynamic execution instructions during concentric/eccentric phases.
- `common_mistakes`: Specific mechanical faults with coaching remedies.
- `breathing_pattern`: Biomechanical breathing instruction (e.g., "Inhale and brace intra-abdominal pressure at top, exhale past sticking point on ascent").

### F. Exercise Relationships & Progression Graphs
- `progressions`: List of exercise IDs representing higher mechanical/stability demand.
- `regressions`: List of exercise IDs representing lower skill, lighter load, or higher stability alternatives.
- `substitutions`: List of exercise IDs with identical movement pattern and primary muscle focus for alternate equipment/environments.
- `complementary_exercises`: List of accessory or mobility exercises that prime or counteract the movement.

### G. Conservative Non-Medical Guidance
- `movement_cautions`: Conservative biomechanical stress warnings (e.g., `"High axial spinal compression"`, `"High shear force on anterior patellofemoral joint at deep knee flexion"`).
- **Strict Prohibition**: Never include claims like "cures knee pain", "safe for herniated discs", or "prevents injury". Formatted strictly as non-prescriptive anatomical load notices.

### H. Computer Vision & Form Analysis Support Separation
- `form_analysis_supported`: Boolean flag (`True` ONLY for the 5 verified CV exercises).
- `cv_exercise_id`: Internal CV engine exercise key (`"squat" | "bench_press" | "deadlift" | "bicep_curl" | "shoulder_press" | None`).
- `supported_camera_mode`: `"front" | "side" | "both" | None`.
- `cv_supported_planes`: Planes evaluated by heuristics (e.g., `["sagittal"]`).
- `cv_limitations_note`: Transparent notes on what CV cannot observe (e.g., "Front camera angle cannot reliably verify lumbar lordosis in sagittal plane").

---

## 3. Catalog Scope & Justification

### Selected Catalog Size: **100 Curated Exercises**

#### Evaluation of Alternative Options:
- **50 Exercises**: Too small. With 10 distinct movement patterns across 2 environments (`gym` vs `home`) and 3 difficulty levels, 50 exercises yields fewer than 5 exercises per pattern. A user with home-only dumbbells would experience immediate progression dead-ends with zero viable substitutions.
- **200–300 Exercises**: Too large for an initial authoritative, hand-verified seed. At 200+ exercises, relationship graph integrity degrades, cues become generic templates, manual biomechanical validation becomes error-prone, and catalog maintenance overhead explodes.
- **100 Exercises (Recommended)**: The optimal sweet spot. It provides:
  - **7–12 exercises per core movement pattern**.
  - Complete vertical ladders for all primary patterns: Beginner $\to$ Intermediate $\to$ Advanced.
  - Full dual-environment coverage: complete Gym equipment routines alongside 100% Home/Dumbbell/Bodyweight equivalents.
  - 100% referential integrity: every relationship target (`progressions`, `regressions`, `substitutions`) links to an existing, validated exercise in the catalog.
  - Manageable for exhaustive automated verification tests.

#### Movement Pattern Distribution (100 Exercises):
1. **Squat Pattern (12)**: Bodyweight Squat, Goblet Squat, Barbell Back Squat, Front Squat, Box Squat, Dumbbell Split Squat, Bulgarian Split Squat, Leg Press, Hack Squat, Overhead Squat, Wall Sit, Sissy Squat.
2. **Hinge Pattern (12)**: Glute Bridge, Barbell Hip Thrust, Single-Leg Hip Thrust, Kettlebell Deadlift, Conventional Deadlift, Romanian Deadlift (RDL), Dumbbell RDL, Trap Bar Deadlift, Sumo Deadlift, Good Morning, Back Extension, Kettlebell Swing.
3. **Horizontal Push (12)**: Incline Push-Up, Standard Push-Up, Decline Push-Up, Diamond Push-Up, Barbell Bench Press, Incline Barbell Press, Dumbbell Flat Press, Incline Dumbbell Press, Decline Dumbbell Press, Dumbbell Floor Press, Cable Chest Fly, Machine Chest Press.
4. **Horizontal Pull (11)**: Inverted Row, Dumbbell Single-Arm Row, Bent-Over Barbell Row, Chest-Supported T-Bar Row, Seated Cable Row, Face Pull, Band Pull-Apart, Meadows Row, Pendlay Row, Dumbbell Seal Row, Rear Delt Fly.
5. **Vertical Push (10)**: Dumbbell Seated Shoulder Press, Standing Overhead Barbell Press, Push Press, Arnold Press, Pike Push-Up, Handstand Push-Up (Wall), Cable Lateral Raise, Dumbbell Lateral Raise, Machine Shoulder Press, Landmine Angled Press.
6. **Vertical Pull (10)**: Lat Pulldown (Wide Grip), Lat Pulldown (Close Neutral Grip), Pull-Up, Chin-Up, Assisted Pull-Up, Straight-Arm Cable Pulldown, Resistance Band Lat Pulldown, Dumbbell Pullover, Muscle-Up, Neutral Grip Pull-Up.
7. **Lunge / Unilateral Leg (9)**: Walking Lunge, Reverse Lunge, Forward Lunge, Dumbbell Step-Up, Cossack Squat, Lateral Lunge, Curtsy Lunge, Deficit Reverse Lunge, Jumping Lunge.
8. **Arm Isolation (10)**: Standing Barbell Bicep Curl, Incline Dumbbell Curl, Dumbbell Hammer Curl, Concentration Curl, Cable Bicep Curl, Tricep Rope Pushdown, Skull Crusher (Lying Tricep Extension), Overhead Dumbbell Tricep Extension, Close-Grip Bench Press, Bench Dip.
9. **Core & Spinal Stability (10)**: Front Plank, Side Plank, Dead Bug, Bird Dog, Pallof Press, Hanging Leg Raise, Ab Wheel Rollout, Cable Woodchopper, Farmer's Walk, Suitcase Carry.
10. **Mobility & Dynamic Activation (4)**: World's Greatest Stretch, Cat-Cow, 90/90 Hip Flow, Thoracic Spine Foam Roll & Extension.

---

## 4. Controlled Taxonomies

To prevent free-text inconsistency, all taxonomy fields will use strict Pydantic Literal types / Enums:

```python
MovementPattern = Literal[
    "squat",
    "hinge",
    "horizontal_push",
    "horizontal_pull",
    "vertical_push",
    "vertical_pull",
    "lunge",
    "isolation",
    "core_anti_extension",
    "core_anti_rotation",
    "carry",
    "mobility",
]

ExerciseCategory = Literal[
    "strength",
    "hypertrophy",
    "endurance",
    "mobility",
    "activation_warmup",
    "cardio",
]

ExerciseType = Literal["compound", "isolation"]

Laterality = Literal["bilateral", "unilateral", "alternating"]

PlaneOfMotion = Literal["sagittal", "frontal", "transverse", "multi_planar"]

Environment = Literal["gym", "home", "outdoor", "anywhere"]

DifficultyLevel = Literal["beginner", "intermediate", "advanced"]

FitnessGoal = Literal[
    "muscle_gain",
    "fat_loss",
    "strength",
    "endurance",
    "general_fitness",
]

EquipmentType = Literal[
    "bodyweight",
    "dumbbells",
    "barbell",
    "kettlebell",
    "resistance_bands",
    "cable_machine",
    "smith_machine",
    "leg_press",
    "pull_up_bar",
    "yoga_mat",
    "bench",
    "incline_bench",
    "trap_bar",
    "dip_station",
    "box_platform",
]

MuscleGroup = Literal[
    "chest",
    "shoulders",
    "triceps",
    "biceps",
    "back",
    "quadriceps",
    "hamstrings",
    "glutes",
    "calves",
    "abs",
    "core",
    "full_body",
]
```

---

## 5. Exercise Relationships Model

### Architecture: Embedded ID Arrays with Referential Integrity
Each exercise document embeds 4 explicit ID reference arrays:
1. `progressions: List[str]` — Next step in mechanical or load progression.
2. `regressions: List[str]` — Easier variation for fatigue, skill acquisition, or form breakdown.
3. `substitutions: List[str]` — Drop-in alternatives matching primary muscle + pattern (e.g. Gym Barbell $\to$ Home Dumbbell).
4. `complementary_exercises: List[str]` — Synergistic priming or accessory movements.

#### Why Embedded ID Arrays over Separate Collection?
- **Query Performance**: Fetching an exercise by ID retrieves its entire immediate relationship neighborhood in a single read ($O(1)$) with zero joins or Firestore subcollection latency.
- **Maintainability & Size**: Adds $< 200$ bytes per document, keeping total document size $< 3.5\text{ KB}$ (well below Firestore's 1 MB threshold).
- **Referential Integrity Validation**: Automated test suites will assert that every ID in any relationship array resolves to a valid, existing exercise ID within the catalog, preventing dangling pointers.

#### Example Graph Node:
```json
{
  "id": "ex_barbell_back_squat",
  "name": "Barbell Back Squat",
  "movement_pattern": "squat",
  "regressions": ["ex_box_squat", "ex_goblet_squat"],
  "progressions": ["ex_front_squat", "ex_overhead_squat"],
  "substitutions": ["ex_leg_press", "ex_dumbbell_split_squat"],
  "complementary_exercises": ["ex_romanian_deadlift", "ex_cat_cow"]
}
```

---

## 6. Computer Vision Coverage Separation

A strict boundary is maintained between **catalog knowledge coverage** (100 exercises) and **CV form-analysis engine coverage** (exactly 5 supported exercises):

| Exercise ID | Canonical CV Key | Form Analysis Supported | Supported Camera Mode | Evaluated Planes |
| :--- | :--- | :---: | :---: | :--- |
| `ex_squat` / `ex_barbell_back_squat` | `"squat"` | **`True`** | `"side"` | Sagittal (hip/knee depth, torso angle, valgus) |
| `ex_bench_press` / `ex_barbell_bench_press` | `"bench_press"` | **`True`** | `"side"` | Sagittal (elbow flare, touchpoint, lockout) |
| `ex_deadlift` / `ex_conventional_deadlift` | `"deadlift"` | **`True`** | `"side"` | Sagittal (lumbar curve, bar path, lockout) |
| `ex_bicep_curl` / `ex_standing_bicep_curl` | `"bicep_curl"` | **`True`** | `"front"` | Frontal/Sagittal (elbow travel, torso swing) |
| `ex_shoulder_press` / `ex_overhead_shoulder_press` | `"shoulder_press"` | **`True`** | `"front"` | Frontal (press path, lockout symmetry) |
| *All 95 Other Catalog Exercises* | `None` | **`False`** | `None` | `[]` |

- The frontend UI uses `exercise.form_analysis_supported` to render the "Live AI Form Analysis" badge only when genuine CV inference is available.
- Zero fake CV support: no exercise outside the 5 will ever claim form analysis readiness.

---

## 7. Form-Analysis $\to$ Recommendation Connection

When a user completes a live form-analysis session with heuristic penalties or deficiencies, the platform maps those findings to structured corrective recommendations deterministically:

```
[ Form Analysis Findings ]
  - Deficient ROM / Depth
  - Valgus Knee Collapse
  - Excessive Torso Lean
  - Elbow Flare
  - Lumbar Rounding
           │
           ▼
[ Deterministic Corrective Mapping ]
           │
           ├─► Technical Cue ("Focus on pushing knees outward over toes during descent")
           ├─► Movement Regression (e.g. Barbell Squat ─► Box Squat to cue depth)
           └─► Accessory / Mobility Pair (e.g. Band Pull-Apart for bench press stability)
```

### Form Heuristic Mapping Table:
1. **Squat — Insufficient ROM / Depth**:
   - Technical Cue: "Practice pausing at parallel depth with a stable tripod foot."
   - Regression Recommendation: `ex_box_squat` (teaches consistent depth without collapse).
   - Mobility Recommendation: `ex_ankle_mobility_drill` / `ex_goblet_squat`.
2. **Squat — Valgus Knee Deviation**:
   - Technical Cue: "Drive your knees outward in line with your middle toes."
   - Accessory Recommendation: `ex_lateral_band_walk` (strengthens gluteus medius).
3. **Bench Press — Excessive Elbow Flare**:
   - Technical Cue: "Tuck elbows to roughly 45–60 degrees relative to your torso."
   - Regression Recommendation: `ex_dumbbell_floor_press` (constrains shoulder hyperextension).
   - Substitution Recommendation: `ex_dumbbell_flat_press` (allows natural wrist/elbow rotation).
4. **Deadlift — Lumbar Flexion / Rounding**:
   - Technical Cue: "Pull the slack out of the bar and set your lats before initiating drive."
   - Regression Recommendation: `ex_trap_bar_deadlift` (places center of mass closer to body).
   - Accessory Recommendation: `ex_romanian_deadlift` / `ex_bird_dog` (grooves hip hinge and core bracing).
5. **Shoulder Press — Lumbar Hyperextension**:
   - Technical Cue: "Squeeze your glutes and pull your ribcage down to stabilize your spine."
   - Regression Recommendation: `ex_dumbbell_seated_shoulder_press` (eliminates standing axial shear).

**Non-Medical Invariant**: All recommendations are phrased strictly as technique guidance and exercise alternatives, never as clinical diagnoses or medical interventions.

---

## 8. Deterministic Recommendation Architecture

To guarantee reliability, safety, and transparency, exercise recommendations follow a **two-tier architecture**:

```
[ User Profile, Goals, Environment, Equipment, History, Form Analysis ]
                               │
                               ▼
            ┌───────────────────────────────────────┐
            │  Tier 1: Deterministic Eligibility    │
            │  & Multi-Factor Scoring Engine        │
            │  (Pure Python, zero hallucination)    │
            └───────────────────────────────────────┘
                               │
                               ▼
                 [ Ranked Candidate Pool ]
             (Strictly validated exercise IDs)
                               │
                               ▼
            ┌───────────────────────────────────────┐
            │  Tier 2: Future Phase 9C Gemini       │
            │  Natural-Language Personalization     │
            │  (Explains why candidate was chosen)  │
            └───────────────────────────────────────┘
```

- **Tier 1 (Phase 9B.8 Foundation)**: Filters the 100-exercise universe using hard physical constraints and ranks eligible exercises with deterministic scoring weights.
- **Tier 2 (Phase 9C Handoff)**: Gemini receives the deterministic top candidates as context and crafts encouraging, personalized workout advice. Gemini cannot suggest exercises outside the validated catalog or override equipment/difficulty filters.

---

## 9. Recommendation Eligibility: Hard Filters vs Soft Signals

### Hard Eligibility Filters (Binary Pass/Fail)
An exercise is discarded if ANY hard filter fails:
1. **Equipment Availability**: User has all `required_equipment` in their profile (or exercise is `bodyweight`).
2. **Environment Compatibility**: User's active environment (`gym` vs `home`) is in exercise's `environment_compatibility`.
3. **Difficulty Gate**:
   - `beginner` users cannot be prescribed `advanced` exercises as primary movements.
   - `intermediate` users can receive `beginner` and `intermediate`.
   - `advanced` users can receive all levels.
4. **Explicit Exclusions**: Exercises tagged with user's declared physical cautions or omitted muscle groups.

### Soft Ranking Signals (Weighted Scoring 0.0 to 1.0)
Eligible exercises are scored using a normalized multi-factor utility function:

$$\text{Score} = w_{\text{goal}} \cdot S_{\text{goal}} + w_{\text{split}} \cdot S_{\text{split}} + w_{\text{perf}} \cdot S_{\text{perf}} + w_{\text{form}} \cdot S_{\text{form}} - P_{\text{recency}}$$

- **Goal Match ($w_{\text{goal}} = 0.35$)**: Compatibility between user's primary/secondary goals and exercise category (e.g. `strength` goal favors heavy compound movements).
- **Target Muscle Need ($w_{\text{split}} = 0.25$)**: Muscles trained least recently or targeted by the daily workout split.
- **Performance & Progression Readiness ($w_{\text{perf}} = 0.20$)**: Exercises where the user has logged PRs or demonstrated mastery, or the logical next step in an established progression ladder.
- **Form Analysis Corrective Affinity ($w_{\text{form}} = 0.20$)**: Boosted if the exercise addresses a specific observed heuristic flaw from recent form sessions.
- **Recency Penalty ($P_{\text{recency}} \in [0.0, 0.15]$)**: Prevents workout monotony by penalizing exercises completed within the last 48 hours.

---

## 10. Data Storage & Repository Architecture

### Architecture Choice: **Option C (Hybrid — Recommended)**

1. **Authoritative Source of Truth**:
   - A version-controlled, static, strongly validated catalog file: `backend/app/seeds/exercise_catalog_data.py` (or `.json`).
   - Accompanied by a semantic `CATALOG_VERSION = "1.0.0"`.
   - Every commit is reviewed via Git diffs; no unvetted changes can occur in production.
2. **Runtime Serving**:
   - Idempotently seeded into Cloud Firestore collection: `exercises/{exercise_id}`.
   - Allows standard REST querying, fast document lookup by ID, and future admin extensions.
3. **Test Isolation**:
   - `ExerciseRepository` maintains an in-memory dictionary cache initialized directly from the static seed data when `db=None`.
   - Guarantees 100% offline, deterministic unit and integration tests without touching live databases.

### Collection Structure & Document Bounds
- Path: `exercises/{exercise_id}`
- Document size: Average ~2.2 KB, Maximum ~3.8 KB (far below Firestore's 1 MB document limit).
- Indexes: Single-field indexes on `movement_pattern`, `difficulty`, `category` (automatically provided by Firestore). **Zero composite indexes required**, as multi-tag filtering is handled in memory after broad streaming or primary key lookups.

---

## 11. Seeding Strategy & Versioning

- **Deterministic Primary Key**: `id` formatted as `ex_{snake_case_name}` (e.g. `ex_barbell_back_squat`).
- **Idempotent Seeding (`ensure_seeded(force_update: bool = False)`)**:
  - Checks catalog version document at `system_metadata/exercise_catalog`.
  - If unseeded or version differs: writes exercises using Firestore atomic batch operations (`db.batch()`).
  - **Non-Destructive Guarantee**: Exercises are stored in global `exercises/` collection. Seeding never modifies user profiles, workout histories, or form-analysis records (`users/{uid}/...`).
- **Deprecation Policy**: Obsolete exercises are marked `is_deprecated: bool = True` with `deprecated_replacement_id: Optional[str]`, never hard-deleted, preserving historical workout log integrity.

---

## 12. API Contract Specification

Phase 9B.8 will expose clean, authenticated/public endpoints following existing FastAPI patterns:

### 1. `GET /api/v1/exercises` (Enhanced)
- **Query Parameters**:
  - `muscle: Optional[MuscleGroup]`
  - `equipment: Optional[EquipmentType]`
  - `difficulty: Optional[DifficultyLevel]`
  - `movement_pattern: Optional[MovementPattern]`
  - `category: Optional[ExerciseCategory]`
  - `environment: Optional[Environment]`
  - `form_analysis_only: Optional[bool]` (filters for the 5 CV exercises)
  - `search: Optional[str]`
- **Response**: `List[ExerciseSchema]` with complete taxonomy and relationship IDs.

### 2. `GET /api/v1/exercises/{exercise_id}`
- **Response**: Full `ExerciseKnowledgeSchema` including cues, mistakes, progressions, regressions, substitutions, and CV metadata.
- **Error**: `404 Not Found` if non-existent.

### 3. `GET /api/v1/exercises/{exercise_id}/relationships`
- **Response**: Resolved objects for `progressions`, `regressions`, `substitutions`, and `complementary_exercises`.

### 4. `POST /api/v1/exercises/recommendations/candidates`
- **Authentication**: Verified Firebase Bearer Token.
- **Request Body**: Optional overrides (e.g. temporary environment or equipment change).
- **Response**: `RecommendationCandidateResponse` containing ranked candidate exercises with deterministic match scores and explanatory tags.

---

## 13. Frontend Impact & Wire-In Plan

**Visual Language Frozen**: No approved UI cards or layouts will be redesigned. The enhanced knowledge model will be wired behind existing components:

1. **`src/types/index.ts`**:
   - Extend `Exercise` interface with optional Phase 9B.8 fields (`movementPattern`, `laterality`, `progressions`, `regressions`, `substitutions`, `setupCues`, `executionCues`).
2. **`src/components/exercise/SimilarExercisesPanel.tsx`**:
   - Replace hardcoded static exercise array with real dynamic relationships from `exercise.substitutions` and `exercise.progressions`.
3. **`src/components/exercise/HowToPerformCard.tsx`**:
   - Bind `exercise.setupCues` and `exercise.executionCues` alongside general instructions.
4. **`src/pages/app/ExercisesPage.tsx`**:
   - Connect movement pattern and environment filter chips to existing search bar filter logic.

---

## 14. Future Phase 9C Handoff Contract

Phase 9B.8 strictly builds the **deterministic foundation** that Phase 9C will consume:

```python
class ExerciseRecommendationCandidate(BaseModel):
    exercise_id: str
    name: str
    movement_pattern: str
    match_score: float
    eligibility_reasons: List[str]      # e.g. ["Matches Primary Goal: Strength", "Compatible with Home Dumbbells"]
    corrective_reasons: List[str]       # e.g. ["Prescribed to groove depth following squat form session"]
    progression_context: Optional[str]  # e.g. ["Next progression step from Bodyweight Squat"]
```

In Phase 9C:
- Gemini will receive this structured list as input.
- Gemini's prompt will instruct it to craft natural-language encouragement and coaching tips around these specific candidates.
- Gemini is forbidden from inventing unseeded exercises or altering numerical match scores.

---

## 15. Comprehensive Test Strategy

Deterministic testing across the following verification areas:

1. **Catalog Integrity & Taxonomy (Unit)**:
   - Exactly 100 unique exercises seeded.
   - All IDs match canonical prefix format `ex_*`.
   - Every movement pattern, muscle, equipment, and category belongs to the controlled taxonomy.
   - Zero medical claims in safety notes, descriptions, or cues.
2. **Referential Integrity (Graph Traversal)**:
   - Every ID referenced in `progressions`, `regressions`, `substitutions`, and `complementary_exercises` exists in the catalog.
   - No self-referencing relationships (`ex_a` cannot regress to `ex_a`).
   - Bidirectional consistency checks where applicable.
3. **CV Separation Verification**:
   - Exactly 5 exercises have `form_analysis_supported == True`.
   - Exactly 95 exercises have `form_analysis_supported == False`.
   - Only the 5 authorized CV exercises have non-null `cv_exercise_id`.
4. **Seeding Idempotency**:
   - Calling `ensure_seeded()` consecutively does not duplicate documents or overwrite modified user records.
5. **Deterministic Recommendation Filtering**:
   - User with home/dumbbells only receives home/dumbbell-compatible exercises.
   - Beginner users never receive advanced exercises as primary recommendations.
   - Form heuristic flaws correctly trigger mapped corrective accessory candidates.

---

## 16. Security & Privacy Safeguards

- **Zero Credentials**: No new service accounts, client secrets, or private API keys required.
- **Zero PII in Catalog**: Global exercises collection is 100% public reference domain data; no user identities or PII are stored in exercise documents.
- **User Scoping**: Personalization endpoints (`/recommendations/candidates`) require verified Firebase ID tokens (`get_current_user`).
- **No Cloud CV or Storage Leakage**: No raw video or images stored.

---

## 17. Scope Boundaries

| In Scope (Phase 9B.8) | Out of Scope (Forbidden) |
| :--- | :--- |
| Enhanced `ExerciseKnowledgeSchema` with biomechanical taxonomies | Calling Gemini or any external LLM API |
| Curated 100-exercise authoritative seed dataset | Developing new MediaPipe CV detectors or expanding beyond 5 CV exercises |
| Embedded relationship graphs (progression, regression, substitution) | Generating dynamic AI workout plans (Phase 9C) |
| Strict CV separation metadata (`form_analysis_supported`, `cv_exercise_id`) | Redesigning existing approved UI layouts or navigation |
| Deterministic form-analysis corrective heuristic mapping | Storing or training Vector RAG databases |
| Deterministic recommendation eligibility & scoring engine | Adding social, payments, or push notification features |
| Idempotent repository seeder & query APIs | Medical claims or clinical diagnosis features |

---

## 18. Manual Prerequisites & User Actions Checklist

1. **Need to create any credentials?** **NO.**
2. **Need to manually configure Firebase?** **NO.** Existing Firestore and Firebase Auth configurations are reused.
3. **Need to manually provide any data?** **NO.** The 100-exercise catalog will be authored directly into the codebase seed file.
4. **Any external service required?** **NO.** Everything runs locally on FastAPI + Vite + existing Firebase.
5. **Any paid API / service required?** **NO.**
6. **What the user personally needs to do before implementation:** **Review and approve this implementation plan.**
7. **What Antigravity can do automatically:** Implement the schemas, author the validated 100-exercise catalog, build relationship graphs, update repositories, wire endpoints, implement recommendation eligibility logic, update frontend types/panels, and run the automated test suite.

---

## 19. Implementation Sub-Phase Sequence

The future implementation will proceed in 6 discrete, reviewable sub-phases:

```
[ 9B.8.1: Taxonomies & Schemas ]
             │
             ▼
[ 9B.8.2: 100-Exercise Seed Catalog ]
             │
             ▼
[ 9B.8.3: Relationship Graph & Form Correctives ]
             │
             ▼
[ 9B.8.4: Repository, Seeder & Query Endpoints ]
             │
             ▼
[ 9B.8.5: Deterministic Recommendation Engine ]
             │
             ▼
[ 9B.8.6: Frontend Wiring & Full Regression ]
```

### Sub-Phase Breakdown:
1. **Phase 9B.8.1 — Taxonomies & Knowledge Schema**:
   - Files: `backend/app/schemas/exercise.py` (new), `backend/app/schemas/workout.py`, `backend/app/schemas/user.py`.
   - Deliverable: Controlled literal types, `ExerciseKnowledgeSchema`, relationship models.
2. **Phase 9B.8.2 — Authoritative 100-Exercise Catalog**:
   - Files: `backend/app/seeds/exercise_catalog_data.py` (new).
   - Deliverable: 100 fully populated exercises covering 10 movement patterns, cues, equipment, muscles, and difficulty.
3. **Phase 9B.8.3 — Relationship Graph & Corrective Mappings**:
   - Files: `backend/app/services/form_correctives.py` (new), `backend/app/seeds/exercise_catalog_data.py`.
   - Deliverable: Validated progressions, regressions, substitutions, and heuristic $\to$ exercise mappings.
4. **Phase 9B.8.4 — Repository, Seeder & API Endpoints**:
   - Files: `backend/app/repositories/exercise_repository.py`, `backend/app/api/v1/endpoints/exercises.py`.
   - Deliverable: Versioned idempotent seeding, enhanced multi-tag filtering, single exercise detail endpoint.
5. **Phase 9B.8.5 — Deterministic Recommendation Eligibility Engine**:
   - Files: `backend/app/services/exercise_recommendation_service.py` (new), `backend/app/schemas/recommendation.py` (new).
   - Deliverable: Hard eligibility filters, soft scoring weights, candidate generation endpoint.
6. **Phase 9B.8.6 — Frontend Wiring & Full Regression**:
   - Files: `src/types/index.ts`, `src/services/exerciseService.ts`, `src/components/exercise/SimilarExercisesPanel.tsx`, test suites.
   - Deliverable: Dynamic similar exercises, complete pytest (500+ tests) and npm test suites.

---

## 20. Acceptance Criteria

- [ ] All 100 exercises pass strict Pydantic validation against `ExerciseKnowledgeSchema`.
- [ ] 100% referential integrity: zero broken or dangling relationship IDs.
- [ ] Exactly 5 exercises marked with `form_analysis_supported == True`; 95 marked `False`.
- [ ] Seeding is verified idempotent and non-destructive.
- [ ] Recommendation engine enforces hard equipment, environment, and difficulty boundaries.
- [ ] Form heuristic flaws deterministically generate corrective suggestions without medical terminology.
- [ ] Frontend `SimilarExercisesPanel` renders dynamic authoritative substitutions and progressions.
- [ ] Zero regressions across existing Workouts, Form Analysis, Coach, Nutrition, and Auth modules.
- [ ] Phase 9C remains completely unstarted.
