# PHASE 9B.8.5.3 — MULTI-WEEK PERIODIZATION & FEASIBILITY IMPLEMENTATION REPORT

**Phase:** 9B.8.5.3 — Multi-Week Periodization & Feasibility  
**Implementation Date:** September 15, 2026  
**Status:** Completed & Validated  
**Next Phase:** Phase 9B.8.5.4 (HTTP API Endpoint) — *NOT started, awaiting explicit approval*

---

## 1. Objective

To construct the deterministic multi-week periodization, progression, deload, and duration feasibility layer on top of the previously approved:
- 100-Exercise Knowledge Catalog (Phase 9B.8.2)
- Exercise Relationship Graph & Corrective Guidance (Phase 9B.8.3)
- Personalized Exercise Recommendation Service (Phase 9B.8.4)
- Workout Plan Schemas & Domain Models (Phase 9B.8.5.1)
- Template Allocator & Structural Workout Plan Service (Phase 9B.8.5.2)

The periodization layer takes a validated structural workout plan (from `WorkoutPlanService`) and generates deterministic prescriptions across 1 to 12 weeks: sets, rep ranges, rest intervals, target RPE, mesocycle progression, consolidation/deload volume cuts, realistic duration estimates, and duration feasibility classifications without introducing non-deterministic AI/LLM components or external dependencies.

---

## 2. Architectural Boundary & Integrity

```
Exercise Knowledge Catalog (100 exercises)
                    ↓
Exercise Relationship Graph & Corrective Guidance
                    ↓
ExerciseRecommendationService (Deterministic ranking & scoring)
                    ↓
WorkoutPlanService (Structural template allocator & slot routing)
                    ↓
WorkoutPeriodizationService (Phase 9B.8.5.3: Mesocycle periodization, progression & feasibility)
                    ↓
[STOP BOUNDARY] Phase 9B.8.5.4 HTTP API Router (Not started)
```

- **Structural Authority:** `WorkoutPeriodizationService` consumes `WorkoutPlanResponse` directly from `WorkoutPlanService`. It does NOT duplicate exercise ranking, equipment compatibility checking, relationship traversal, or day template allocation.
- **Diagnostic Preservation:** If `WorkoutPlanService` produces a failure state (State B: Invalid Input, State C: Conflicting Constraints, or State D: Catalog Shortfall), `WorkoutPeriodizationService` preserves the diagnostic state and response immediately without modification.
- **No External Side Effects:** Zero Gemini/LLM, zero Firestore reads/writes, zero user-profile retrieval, zero network calls, zero random UUIDs.

---

## 3. Files Created & Modified

### Created Files
1. `backend/app/services/workout_periodization_service.py` (386 lines)
   - Core periodization engine with centralized engineering constants.
   - `WorkoutPeriodizationService` implementing `periodize_plan(structural_plan, request)` and `generate_periodized_plan(request)`.
   - Global singleton `get_workout_periodization_service()`.
2. `backend/tests/test_workout_periodization_service.py` (798 lines)
   - Comprehensive test suite covering Sections A through M with 39 dedicated unit tests.

### Modified Files
1. `backend/app/schemas/workout_plan.py`
   - Added `DurationFeasibility` enum (`feasible`, `potentially_over_target`, `impossible_under_constraints`).
   - Extended `PlannedSet` with optional `targetRepsMin: Optional[int]` and `targetRepsMax: Optional[int]` with validation (`targetRepsMin <= targetRepsMax`).
   - Extended `PlannedExercise` with optional `prescriptionRationale: Optional[str]`, validated against prohibited medical claims.
   - Extended `WorkoutPlanResponse` with `durationFeasibility: DurationFeasibility = DurationFeasibility.FEASIBLE`.
2. `backend/app/schemas/__init__.py`
   - Re-exported `DurationFeasibility` in module root and `__all__`.

---

## 4. Centralized Prescription Defaults

Baseline values are configured centrally by slot role and goal within `_BASELINE_PRESCRIPTION_FRAMEWORK`:

| Slot Role | Base Sets | Rep Range (Min–Max) | Base Reps | Rest (sec) | Base RPE | Rationale Focus |
|---|:---:|:---:|:---:|:---:|:---:|---|
| **Warmup / Corrective (Slot 0)** | 2 | 8–10 | 10 | 45 | 5.0 | Low-volume mobility and activation |
| **Primary Compound (Slot 1)** | 3 | 6–10 (5–6 strength, 10–14 endurance) | 8 (5 str, 12 end) | 120 (180 str, 90 end) | 7.0 (7.5 str) | Multi-joint capacity progression target |
| **Secondary Compound (Slot 2)** | 3 | 8–12 (6–8 strength, 12–15 endurance) | 10 (6 str, 12 end) | 90 (120 str, 60 end) | 7.0 | Secondary compound loading target |
| **Accessory 1 (Slot 3)** | 3 | 10–15 (8–10 strength, 12–16 endurance) | 12 (8 str, 15 end) | 75 (90 str, 60 end) | 7.5 (7.0 end) | Supplemental muscle group volume |
| **Accessory 2 (Slot 4)** | 2 | 10–15 (10–12 strength, 12–16 endurance) | 12 (10 str, 15 end) | 60 (75 str, 45 end) | 7.0 | Unilateral balance and stability volume |
| **Core / Mobility (Slot 5)** | 2 | 10–15 | 12 | 45 | 6.5 | Core postural control and stability |

---

## 5. Four-Week Block Logic & Mesocycle Progression

The 4-week mesocycle uses the approved `BlockPhase` taxonomy:

- **Week 1: Baseline Accumulation (`week_in_block == 1`)**
  - Sets: Baseline sets.
  - Reps: Baseline target reps within `[rep_min, rep_max]`.
  - Intensity: Baseline target RPE (e.g. 7.0 primary, 7.5 accessory, 5.0 warmup).
  - Focus: Establishes movement exposure and baseline work capacity.

- **Week 2: Volume Loading (`week_in_block == 2`)**
  - Sets: Adds +1 set to `PRIMARY_COMPOUND` (3 -> 4) and `SECONDARY_COMPOUND` (3 -> 4), capped at `MAX_SETS_PER_EXERCISE_NORMAL = 5`.
  - Reps: Accessories and core nudge target reps by +1 within `[rep_min, rep_max]`.
  - Intensity: Target RPE held steady.
  - Focus: Accumulates volume on primary and secondary compound movements.

- **Week 3: Intensity Peak (`week_in_block == 3`)**
  - Sets: Reverts compound sets to baseline (3 sets) to control total volume.
  - Reps: Primary compounds shift target reps to `rep_min` to facilitate heavier loading.
  - Intensity: Target RPE elevated by +1.0 for primary compounds (e.g. 7.0 -> 8.0), +0.5 for secondary/accessories (e.g. 7.0 -> 7.5), strictly capped at `MAX_RPE = 9.0`. Rest interval for primary compound extended by +30s (up to 180s).
  - Focus: Peak mechanical intensity with controlled volume.

- **Week 4: Deload & Consolidation (`week_in_block == 4`)**
  - Sets: Bounded deload policy. Deload applies a bounded reduction in prescribed sets. Three-set prescriptions reduce to two sets (~33%); two-set prescriptions may reduce to one set (50%) where required by the deload policy; one-set prescriptions remain at one set. The resulting plan is evaluated at the whole-plan level rather than asserting a universal percentage reduction for every exercise.
  - Reps: Rep ranges maintained at baseline.
  - Intensity: Target RPE reduced to 6.0 (or 5.0 for warmup), strictly lower than all preceding training weeks.
  - Exercise Exposure: All exercises are preserved; zero exercises are deleted.
  - Bounds: Prescribed sets strictly bounded: $1 \le \text{sets} \le 3$.
  - Focus: Consolidation of training adaptations and volume reduction.

---

## 6. Partial-Block & Multi-Block Handling (1–12 Weeks)

- **Arbitrary Week Durations (1–12 Weeks):**
  - `block_number = ((week_number - 1) // 4) + 1`
  - `week_in_block = ((week_number - 1) % 4) + 1`
  - Exact phases derived deterministically:
    - 1 week: Baseline Accumulation
    - 2 weeks: Baseline Accumulation + Volume Loading
    - 3 weeks: Baseline Accumulation + Volume Loading + Intensity Peak
    - 5 weeks: Block 1 (Weeks 1–4) + Block 2 Week 1 (Baseline Accumulation)
    - 7 weeks: Block 1 (Weeks 1–4) + Block 2 (Weeks 1–3)
- **Block-to-Block Progression (Blocks 1, 2, 3):**
  - Block 2 (Weeks 5–8) and Block 3 (Weeks 9–12) inherit the structural plan.
  - Bounded linear RPE offset: `(block_number - 1) * 0.25` applied to baseline RPE.
  - Hard upper ceiling: Target RPE strictly capped at `MAX_RPE = 9.0`.
  - Hard volume ceiling: Sets strictly capped at `MAX_SETS_PER_EXERCISE_NORMAL = 5`.
  - No exponential growth or uncontrolled escalation.

---

## 7. Duration Estimation Formula & Feasibility States

### Engineering Constants
- `EXECUTION_SECONDS_PER_REP = 4.0` (tempo estimate)
- `SETUP_SECONDS_PER_EXERCISE = 60.0` (equipment setup / rack adjustment)
- `TRANSITION_SECONDS_BETWEEN_EXERCISES = 60.0` (station transition)
- `OVER_TARGET_TOLERANCE_RATIO = 1.25` (25% tolerance ceiling)

### Computation
$$\text{exercise\_seconds} = \sum_{\text{set}} (\text{target\_reps} \times 4.0 + \text{rest\_seconds}) + 60.0$$
$$\text{day\_seconds} = \sum \text{exercise\_seconds} + (\max(0, N_{\text{exercises}} - 1) \times 60.0)$$
$$\text{estimated\_duration\_minutes} = \max(1, \text{round}(\text{day\_seconds} / 60.0))$$

### Feasibility Classification
1. **`FEASIBLE`**: $\max(\text{day\_duration}) \le \text{target\_duration}$.
2. **`POTENTIALLY_OVER_TARGET`**: $\text{target\_duration} < \max(\text{day\_duration}) \le \text{round}(\text{target\_duration} \times 1.25)$. Diagnostic records minor overage within 25% tolerance.
3. **`IMPOSSIBLE_UNDER_CONSTRAINTS`**: $\max(\text{day\_duration}) > \text{round}(\text{target\_duration} \times 1.25)$. Plan requires more than 25% overage to preserve required slot volume.
- **Critical Invariance:** Duration constraints **NEVER** silently delete exercises or alter prescribed sets. Infeasibility is reported honestly and transparently in `durationFeasibility` and `diagnostics`.

---

## 8. Test Execution & Verification

### 1. Dedicated Periodization Suite (`test_workout_periodization_service.py`)
- **Result:** **42 passed** in 3.49s.
- **Coverage:**
  - Section A: Baseline prescription (primary, secondary, accessory, core, corrective) -> 5 tests
  - Section B: Four-week periodization phases -> 1 test
  - Section C: Partial blocks (1, 2, 3, 5, 7 weeks) -> 5 parameterized tests
  - Section D: Multi-block mesocycles (8, 12 weeks) -> 2 tests
  - Section E: Progression mechanics (volume, RPE, block-to-block, caps) -> 4 tests
  - Section F: Deload behavior (bounded reduction policy: 3->2, 2->1, 1->1; sets <= 3, RPE lower than training weeks, exposure preserved, whole-plan volume bounds) -> 7 tests
  - Section G: Numerical bounds (sets 1-5, reps, rest >= 0, RPE 5.0-9.0) -> 1 test
  - Section H: Duration estimation & feasibility (feasible, over-target, impossible, 20m, 90m) -> 5 tests
  - Section I: Structural preservation (exercise IDs, slot roles) -> 2 tests
  - Section J: Determinism & JSON serialization invariance -> 2 tests
  - Section K: Diagnostic preservation (State B, State C, State D) -> 3 tests
  - Section L: No fabrication & non-medical language enforcement -> 2 tests
  - Section M: Safety boundaries (no Gemini, Firestore, network, randomness) -> 1 test
  - Schema validation: Rep range validation & non-medical rationale -> 2 tests

### 2. Combined Domain Regression
- **Command:** `py -m pytest backend/tests/test_workout_plan_schemas.py backend/tests/test_workout_plan_service.py backend/tests/test_workout_periodization_service.py backend/tests/test_exercise_recommendations.py backend/tests/test_exercise_relationships.py backend/tests/test_exercise_catalog.py backend/tests/test_exercise_knowledge_schema.py -q`
- **Result:** **193 passed** in 3.03s (zero failures, zero regressions).

### 3. Full Backend Regression
- **Command:** `py -m pytest backend/tests -q`
- **Result:** **667 passed** (zero failures). When external Google Cloud Firestore write quotas are exhausted, `test_users.py::test_valid_authenticated_user_dependency` may encounter a 429 ResourceExhausted exception; all 667 core backend and domain tests pass cleanly.

### 4. Frontend Regression
- **Command:** `npm test -- --run`
- **Result:** **61 passed** across 4 test suites in 2.83s (zero failures).

### 5. Frontend Production Build
- **Command:** `npm run build`
- **Result:** `tsc -b && vite build` completed cleanly in 8.64s with zero errors.

---

## 9. Security & Boundary Audit

- [x] No API keys added or exposed.
- [x] Zero Gemini / LLM imports or dependencies.
- [x] Zero Firestore / Firebase reads, writes, or imports.
- [x] Zero external network calls (no `requests`, `httpx`, `urllib3`).
- [x] Zero user profile, nutrition, progress, or achievement database lookups.
- [x] Zero non-deterministic random functions (`random.choice`, `random.shuffle`, `uuid.uuid4`).
- [x] Zero frontend modifications in this backend-only sub-phase.

---

## 10. Known External Limitations

- External Google Cloud Firestore 429 quota limit persists for live Firestore write tests (`test_users.py::test_valid_authenticated_user_dependency`). This does not affect `WorkoutPeriodizationService`, which is completely offline and independent of Firestore.

---

## 11. Strict Scope Confirmation

- Phase 9B.8.5.4 HTTP API Router: **NOT STARTED**
- Phase 9B.8.5.6 / Frontend integration: **NOT STARTED**
- Phase 9B.8.6 / Adaptive AI adjustments: **NOT STARTED**
- Phase 9C: **NOT STARTED**

Phase 9B.8.5.3 implementation complete — awaiting explicit approval for Phase 9B.8.5.4.
