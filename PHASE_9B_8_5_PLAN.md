# PHASE 9B.8.5 IMPLEMENTATION PLAN
## Deterministic Personalized Workout Plan Construction Layer (Final Corrected Plan)

**Status**: Plan Approved for Sub-Phase 9B.8.5.1 Implementation  
**Date**: September 15, 2026  
**Scope Boundary**: Deterministic Multi-Day & Multi-Week Workout Plan Generator (Zero Gemini/LLM, Zero Vector DB, Zero ML)  

---

### 1. Objective & Architectural Principles

#### 1.1 Objective
Build the **Deterministic Personalized Workout Plan Construction Layer** (Phase 9B.8.5) that generates multi-day, multi-week workout plans deterministically from:
1. The **100-exercise knowledge catalog** (Phase 9B.8.2)
2. The **exercise relationship graph** (Phase 9B.8.3)
3. The **form corrective guidance mappings** (Phase 9B.8.3)
4. The **exercise recommendation engine** (Phase 9B.8.4)
5. The **existing Phase 3 workout and session data contracts**

#### 1.2 Personalization Boundary
- The planner personalizes **ONLY from values explicitly supplied in `WorkoutPlanGenerateRequest`**.
- It does **NOT** silently read user profile, progress, nutrition, achievements, Firestore user documents, or other user-specific data.
- It does **NOT** invent missing goals, fitness levels, equipment, environment, preferences, or restrictions.
- The planner is a deterministic plan-construction engine, not an adaptive learning system.

#### 1.3 Architectural Hierarchy
```
┌────────────────────────────────────────────────────────────────────────┐
│                   100-Exercise Knowledge Catalog                       │
│                     (Phase 9B.8.2: 10 Patterns)                        │
└───────────────────────────────────┬────────────────────────────────────┘
                                    │
                                    ▼
┌────────────────────────────────────────────────────────────────────────┐
│             Exercise Relationship Graph & Corrective Mappings          │
│            (Phase 9B.8.3: Progressions, Regressions, Correctives)      │
└───────────────────────────────────┬────────────────────────────────────┘
                                    │
                                    ▼
┌────────────────────────────────────────────────────────────────────────┐
│               ExerciseRecommendationService (Phase 9B.8.4)             │
│            (Hard Eligibility Gates + Mathematically Bounded Scoring)   │
└───────────────────────────────────┬────────────────────────────────────┘
                                    │
                                    ▼
┌────────────────────────────────────────────────────────────────────────┐
│           Workout Plan Construction Layer (Phase 9B.8.5)               │
│  - Split Architecture Router (Full Body, Upper/Lower, PPL)            │
│  - Workout Template & Slot Allocator (Primary, Secondary, Accessory)   │
│  - Multi-Day Volume/Frequency Balancer                                 │
│  - Multi-Week Block Periodization (Accumulation, Loading, Peak, Deload)│
│  - Whole-Plan Feasibility Verification (States A, B, C, D)             │
└───────────────────────────────────┬────────────────────────────────────┘
                                    │
                                    ▼
┌────────────────────────────────────────────────────────────────────────┐
│               Deterministic Multi-Day Workout Plan Output              │
│        (Structured Days, Prescribed Sets/Reps/Rest, Feasibility)      │
└────────────────────────────────────────────────────────────────────────┘
```

> [!IMPORTANT]
> **Terminology & Boundary Rule**: This layer is NOT an "AI workout generator". It is the **Deterministic Personalized Workout Plan Construction Layer**. Zero LLMs, Gemini, embeddings, vector databases, or ML may determine exercise eligibility, exercise selection, workout structure, or scoring.

---

### 2. Catalog & Taxonomy Authority

The planner reuses the exact, authoritative domain models and taxonomies already established in Phase 9B.8.1 through Phase 9B.8.4:
- `MovementPattern` (12 patterns)
- `ExerciseCategory` (7 categories)
- `ExerciseType` (`"compound"`, `"isolation"`)
- `Laterality` (`"bilateral"`, `"unilateral"`, `"alternating"`)
- `DifficultyLevel` (`"beginner"`, `"intermediate"`, `"advanced"`)
- `EquipmentType` (15 types)
- `MuscleGroup` (12 groups)
- `FitnessGoal` (5 goals)
- `EnvironmentType` (`"gym"`, `"home"`, `"outdoor"`, `"anywhere"`)
- `CANONICAL_CV_EXERCISES` (exactly 5 exercises)

**Strict Rule**: Do NOT introduce new equipment types, muscle groups, movement patterns, difficulty values, exercise IDs, or relationship types.

---

### 3. Split Architectures & Day-Level Routing

The planner deterministically routes `trainingDaysPerWeek` (1 to 6) to proven training splits:

| Days/Wk | Selected Split | Day 1 | Day 2 | Day 3 | Day 4 | Day 5 | Day 6 | Day 7 |
|---|---|---|---|---|---|---|---|---|
| **1 Day** | Full Body | Full Body A | Rest | Rest | Rest | Rest | Rest | Rest |
| **2 Days** | Full Body | Full Body A | Rest | Full Body B | Rest | Rest | Rest | Rest |
| **3 Days** | Full Body | Full Body A | Rest | Full Body B | Rest | Full Body C | Rest | Rest |
| **4 Days** | Upper / Lower | Upper A | Lower A | Rest | Upper B | Lower B | Rest | Rest |
| **5 Days** | U/L + PPL Hybrid | Upper | Lower | Rest | Push | Pull | Legs | Rest |
| **6 Days** | Push / Pull / Legs | Push A | Pull A | Legs A | Push B | Pull B | Legs B | Rest |

#### Template Target Focus & Patterns (Using Only Authoritative Taxonomy):
- **Full Body A**: Focus = Squat & Horizontal Push Primary (`targetPatterns`: `["squat", "horizontal_push", "horizontal_pull", "core_anti_extension"]`).
- **Full Body B**: Focus = Hinge & Vertical Push Primary (`targetPatterns`: `["hinge", "vertical_push", "vertical_pull", "core_anti_rotation"]`).
- **Full Body C**: Focus = Lunge & Push/Pull Secondary (`targetPatterns`: `["lunge", "horizontal_push", "horizontal_pull", "carry"]`).
- **Upper A**: Focus = Horizontal Push & Pull Primary (`targetPatterns`: `["horizontal_push", "horizontal_pull", "vertical_push", "isolation"]`).
- **Lower A**: Focus = Squat Primary & Hinge Secondary (`targetPatterns`: `["squat", "hinge", "lunge", "core_anti_extension"]`).
- **Upper B**: Focus = Vertical Push & Pull Primary (`targetPatterns`: `["vertical_push", "vertical_pull", "horizontal_push", "isolation"]`).
- **Lower B**: Focus = Hinge Primary & Squat Secondary (`targetPatterns`: `["hinge", "squat", "lunge", "core_anti_rotation"]`).
- **Push A / B**: Focus = Horizontal & Vertical Pressing (`targetPatterns`: `["horizontal_push", "vertical_push", "isolation"]`).
- **Pull A / B**: Focus = Horizontal & Vertical Pulling (`targetPatterns`: `["horizontal_pull", "vertical_pull", "isolation"]`).
- **Legs A / B**: Focus = Squat, Hinge, & Unilateral Leg Work (`targetPatterns`: `["squat", "hinge", "lunge", "core_anti_extension"]`).

> [!NOTE]
> **Movement-Pattern Diversity Rule**: Movement-pattern alternation across days is a **diversity preference**, not an absolute hard constraint. It must never override equipment eligibility, environment compatibility, explicit exclusions, catalog membership, corrective mapping validity, or slot feasibility. For Full Body plans, repeated movement patterns across days are expected and valid.

---

### 4. Workout Template & Slot Architecture

Each workout day consists of **5 functional exercise slots** plus an optional **Slot 0** for corrective activation:

| Slot | Role Name | Purpose & Type Requirements |
|---|---|---|
| **Slot 0 (Optional)** | `warmup_corrective` | Populated **ONLY** when a valid corrective issue and canonical CV source exercise are explicitly supplied. Curated low-fatigue primer from Phase 9B.8.3 mappings. |
| **Slot 1** | `primary_compound` | Primary compound movement. Highest scoring multi-joint exercise for the day's primary movement pattern (`exerciseType == "compound"` required). |
| **Slot 2** | `secondary_compound`| Secondary compound movement. Complementary multi-joint exercise (`exerciseType == "compound"` required). |
| **Slot 3** | `accessory_1` | Targeted hypertrophy / endurance movement for primary movers. |
| **Slot 4** | `accessory_2` | Supplemental isolation or unilateral movement targeting synergists or stabilizers. |
| **Slot 5** | `core_mobility` | Trunk stability, carry, or functional core movement (`core_anti_extension`, `core_anti_rotation`, `carry`, `mobility`). |

#### Deduplication & Diversity at Slot Level:
1. **Intra-Workout**: `excludedExerciseIds` accumulates all exercises selected in earlier slots of the same day. Guaranteed **zero duplicate exercises** within any single workout.
2. **Inter-Day Primary Diversity**: On Full Body routines, primary exercises from Day 1 are excluded from Day 2 Slot 1 as a diversity preference, falling back gracefully if catalog coverage is narrow.

---

### 5. Multi-Week Block Semantics & Periodization

#### Supported Duration: 1 to 12 Weeks
Plans are organized into deterministic **4-week mesocycle blocks**:
- **Weeks 1–4**: Block 1
- **Weeks 5–8**: Block 2 (repeats the four-phase structure with optional graph-based exercise rotation)
- **Weeks 9–12**: Block 3 (repeats the four-phase structure with peak intensity)

If the requested duration ends before a 4-week block completes (e.g. 6 weeks), the planner generates **only the requested weeks** (Weeks 1–6) and never invents extra phases. The block number is deterministic: $\text{block\_number} = ((\text{week\_number} - 1) // 4) + 1$.

#### The Four Weekly Phases:
- **Phase 1: Baseline Accumulation (Week 1, 5, 9)**:
  - Standard baseline sets and reps from the goal prescription matrix.
  - Target RPE 7–8; establish movement baseline.
- **Phase 2: Volume Loading (Week 2, 6, 10)**:
  - Volume increases deterministically relative to Week 1: Primary and secondary compound lifts add $+1$ set (e.g. 3 sets $\rightarrow$ 4 sets, or 4 sets $\rightarrow$ 5 sets).
  - Target reps maintained.
- **Phase 3: Intensity Peak (Week 3, 7, 11)**:
  - Volume remains at peak; target reps decrease by $1$ to $2$ reps on primary compound lifts.
  - Target RPE increases to 8–8.5.
- **Phase 4: Deload & Consolidation (Week 4, 8, 12)**:
  - Total sets reduced by 30% to 40% across all exercises (e.g. 4 sets $\rightarrow$ 2–3 sets; 3 sets $\rightarrow$ 2 sets).
  - **Rule**: Deloading must **never** produce zero-set planned exercises. Minimum sets per exercise is always 1 (typically 2).
  - Target RPE reduced to 6–7.

#### Progression Between Blocks (Weeks 5+):
When rotating exercises across 4-week blocks, graph progression or substitution relationships from Phase 9B.8.3 may be used. However:
- A graph progression edge alone does **NOT** force advancement.
- The next-block candidate must still satisfy all applicable hard gates and planner constraints.
- Candidate selection is executed deterministically through `ExerciseRecommendationService`.

---

### 6. Deterministic Prescription Matrices

Prescription values are strictly rule-based, bounded, and deterministic:

| Slot Role | Strength Goal | Muscle Gain Goal | Endurance Goal | General Fitness |
|---|---|---|---|---|
| **Warm-Up / Corrective (Slot 0)** | 2 sets × 8–10 reps (60s rest, RPE 5) | 2 sets × 10 reps (60s rest, RPE 5) | 2 sets × 12 reps (45s rest, RPE 5) | 2 sets × 10 reps (60s rest, RPE 5) |
| **Primary Compound (Slot 1)** | 4 sets × 4–6 reps (150s rest, RPE 8) | 4 sets × 8–10 reps (90s rest, RPE 8) | 3 sets × 12–15 reps (60s rest, RPE 7) | 3 sets × 8–10 reps (90s rest, RPE 7) |
| **Secondary Compound (Slot 2)** | 3 sets × 6–8 reps (120s rest, RPE 7.5)| 3 sets × 8–12 reps (90s rest, RPE 8) | 3 sets × 12–15 reps (60s rest, RPE 7) | 3 sets × 10–12 reps (75s rest, RPE 7) |
| **Accessory 1 (Slot 3)** | 3 sets × 8–10 reps (90s rest, RPE 7.5)| 3 sets × 10–12 reps (75s rest, RPE 8) | 3 sets × 15–20 reps (45s rest, RPE 7) | 3 sets × 12 reps (60s rest, RPE 7) |
| **Accessory 2 (Slot 4)** | 2 sets × 10–12 reps (75s rest, RPE 7) | 3 sets × 12–15 reps (60s rest, RPE 8) | 2 sets × 15–20 reps (45s rest, RPE 7) | 2 sets × 12–15 reps (60s rest, RPE 7) |
| **Core / Carry (Slot 5)** | 3 sets × 10–12 reps (60s rest, RPE 7) | 3 sets × 12–15 reps (60s rest, RPE 7) | 3 sets × 20–30s or 15 reps (45s rest) | 2 sets × 12–15 reps (60s rest, RPE 7) |

---

### 7. Whole-Plan Feasibility & Diagnostic States

State A is returned **ONLY after validating the COMPLETE requested plan**:
- Every requested training day is filled.
- Every required slot (Slots 1–5) is successfully populated.
- Optional corrective Slot 0 is populated when applicable.
- All equipment and environment hard gates are respected across every exercise.
- All explicit user exclusions are respected.
- Zero intra-day duplicate exercises exist.

#### The Four Deterministic States:
- **State A: Valid Plan Generated**: Complete `WorkoutPlanResponse` with `feasibilityCheckPassed=True` and all weeks/days/slots populated.
- **State B: Insufficient / Invalid Input**: Returns `feasibilityCheckPassed=False`, `weeks=[]`, and diagnostic detailing invalid input (e.g. `"training_days_per_week must be between 1 and 6; got 0."`).
- **State C: Conflicting Hard Constraints**: Returns `feasibilityCheckPassed=False`, `weeks=[]`, and explicit `conflictingFilters` detailing impossible filter combinations (e.g. `["No catalog exercises match environment 'outdoor' with equipment ['barbell']"]`).
- **State D: Slot Failure / Insufficient Catalog Coverage**:
  - If any required slot cannot be populated:
    - Zero generated plan returned.
    - Exact shortfall diagnostic detailing: affected week, affected day, affected slot role, and relevant active constraints.
    - Zero arbitrary bodyweight substitutions. Zero silent slot removals.

---

### 8. Deterministic Plan ID Generation

Identical normalized requests must produce identical plan IDs:
- Plan ID is generated from a SHA-256 hash of the normalized request parameters and planner version:
  $$\text{plan\_id} = \text{hash}_{\text{sha256}}(\text{canonical\_json}(\text{request}) + \text{"v1.0"})[:16]$$
- No random UUIDs. No timestamps.

---

### 9. Sub-Phase Implementation Breakdown

To ensure disciplined execution, Phase 9B.8.5 is partitioned into 4 distinct sub-phases:

```
┌────────────────────────────────────────────────────────┐
│ Sub-Phase 9B.8.5.1: Plan Schemas & Domain Models       │ ◄── WE ARE HERE
│  - backend/app/schemas/workout_plan.py                 │
│  - Export models in backend/app/schemas/__init__.py    │
│  - Unit tests for schema validation                    │
└───────────────────────────┬────────────────────────────┘
                            │ (verify & STOP for approval)
                            ▼
┌────────────────────────────────────────────────────────┐
│ Sub-Phase 9B.8.5.2: Template Allocator & Decision Engine│
│  - backend/app/services/workout_plan_service.py        │
│  - Split router, slot templates, volume prescriptions  │
│  - Integration with ExerciseRecommendationService      │
└───────────────────────────┬────────────────────────────┘
                            │ (verify & STOP for approval)
                            ▼
┌────────────────────────────────────────────────────────┐
│ Sub-Phase 9B.8.5.3: Multi-Week Periodization & Deload  │
│  - 4-week block periodization logic                    │
│  - Mesocycle progression & relationship integration    │
│  - Feasibility checks & States A, B, C, D              │
└───────────────────────────┬────────────────────────────┘
                            │ (verify & STOP for approval)
                            ▼
┌────────────────────────────────────────────────────────┐
│ Sub-Phase 9B.8.5.4: API Endpoint & Comprehensive Tests │
│  - backend/app/api/v1/endpoints/workout_plans.py       │
│  - Route mounting in backend/app/api/v1/router.py      │
│  - Complete test suite: backend/tests/...              │
│  - Full backend and frontend regression suites         │
└────────────────────────────────────────────────────────┘
```

---

Phase 9B.8.5 planning complete — awaiting explicit review and approval before implementation.
