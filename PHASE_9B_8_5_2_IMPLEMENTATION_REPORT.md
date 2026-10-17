# Phase 9B.8.5.2 Implementation Report — Template Allocator & Deterministic Decision Engine

**Date:** September 15, 2026  
**Status:** Complete  
**Sub-Phase:** 9B.8.5.2 (Template Allocator & Deterministic Decision Engine)  
**Final Status Declaration:** `Phase 9B.8.5.2 implementation complete — awaiting explicit approval for Phase 9B.8.5.3.`

---

## 1. Executive Summary

Phase 9B.8.5.2 has implemented `WorkoutPlanService`, the deterministic template allocation and decision engine that converts user request parameters into fully realized, multi-day workout plan structures.

The implementation strictly satisfies all constraints established in the Phase 9B.8.5 specification:
- **Zero AI / Gemini / ML:** Operates strictly as a deterministic construction layer. Zero LLMs, zero vector databases, zero embeddings.
- **Read-Only / Zero Firestore:** Pure in-memory plan construction. Zero Firestore reads, zero Firestore writes.
- **Strict Personalization Boundary:** Uses only values explicitly supplied in `WorkoutPlanGenerateRequest`. Zero reads of user profile, progress history, achievements, or nutrition.
- **Direct Consumption of Recommendation Service:** Reuses `ExerciseRecommendationService` without duplicating equipment subset semantics, relationship traversal, corrective mapping traversal, or recommendation scoring formulas.
- **Deterministic Routing & Templates:** Implements exact routing for 1 to 6 days across Full Body, Upper/Lower, and Push/Pull/Legs splits.
- **Primary Compound Enforcement:** Slot 1 strictly enforces `exercise_type == compound`. Never falls back to isolation movements or fabricated bodyweight replacements.
- **State Model:** Accurately routes and diagnoses State A (Valid Plan), State B (Missing / Invalid Input), State C (Conflicting Hard Constraints), and State D (Catalog Feasibility Shortfall).

---

## 2. Exact Files Created and Modified

### Files Created:
1. `backend/app/services/workout_plan_service.py` (Deterministic template allocator and decision engine):
   - `DayTemplateSpec`, `SlotSpec` domain configurations.
   - Day template generators for Full Body (1–3 days), Upper/Lower (4 days), U/L + PPL Hybrid (5 days), and PPL (6 days).
   - `WorkoutPlanService` class with full pipeline:
     - `_validate_input_state_b`: Boundary checking for days (1–6), weeks (1–12), duration (20–90m), and corrective parameters.
     - `_determine_and_validate_split`: Split determination and preferredSplit conflict detection (State C).
     - `_check_catalog_feasibility`: Probe for mutually conflicting hard gates (State C).
     - `_allocate_day_slots`: Slot allocation with compound enforcement, deduplication, and diversity.
     - `_allocate_corrective_slot_0`: Canonical CV source + authoritative issue mapping integration.
     - `_allocate_primary_compound_slot`: Compound enforcement + inter-day primary diversity.
     - `_allocate_secondary_compound_slot`: Compound enforcement + complementary movement pattern matching.
     - `_allocate_accessory_slot`: Day target volume + unilateral preference.
     - `_allocate_core_mobility_slot`: Core stability / carry / mobility matching.
     - `_verify_whole_plan_feasibility`: Whole-plan validation before returning State A.
     - `_create_planned_exercise` & `_build_structural_sets`: Structural baseline sets, reps, and deterministic duration calculation.
   - `get_workout_plan_service()` singleton factory.

2. `backend/tests/test_workout_plan_service.py` (28 dedicated unit tests):
   - `test_1_day_split_routing`
   - `test_2_day_split_routing`
   - `test_3_day_split_routing`
   - `test_4_day_split_routing`
   - `test_5_day_split_routing`
   - `test_6_day_split_routing`
   - `test_required_slot_ordering`
   - `test_primary_compound_enforcement`
   - `test_secondary_compound_behavior`
   - `test_intra_day_duplicate_prevention`
   - `test_inter_day_primary_diversity_preference`
   - `test_movement_pattern_preference_not_hard_gate`
   - `test_equipment_subset_semantics`
   - `test_multi_equipment_failure_case`
   - `test_environment_filtering`
   - `test_explicit_exercise_exclusions`
   - `test_corrective_slot_0_valid_case`
   - `test_corrective_slot_0_omitted_case`
   - `test_invalid_corrective_parameters`
   - `test_state_b_missing_required_input`
   - `test_state_c_conflicting_hard_constraints`
   - `test_state_d_catalog_shortfall`
   - `test_deterministic_identical_request_ordering`
   - `test_deterministic_plan_structure`
   - `test_no_fabricated_bodyweight_fallback`
   - `test_no_gemini_network_firestore_dependency`
   - `test_plan_level_feasibility_verification`
   - `test_no_duplicate_exercise_ids_across_workout_day`

### Files Modified:
None. All implementations were self-contained within the service and test modules.

---

## 3. Architecture Implemented

```
WorkoutPlanGenerateRequest
        ↓
Input Validation & State B Guard
        ↓
Split Architecture Routing (1–6 Days) & State C Guard
        ↓
Catalog Feasibility Check & State C Guard
        ↓
Deterministic Day Template Selection
        ↓
For Each Day:
  ├─ Slot 0 (Optional): Corrective Mapping Lookup (via canonical CV source & issue)
  ├─ Slot 1 (Required): Primary Compound (exercise_type == compound; inter-day diversity preference)
  ├─ Slot 2 (Required): Secondary Compound (exercise_type == compound; complementary pattern)
  ├─ Slot 3 (Required): Accessory 1 (day-appropriate target muscles)
  ├─ Slot 4 (Required): Accessory 2 (unilateral / stabilizer preference)
  ├─ Slot 5 (Required): Core / Mobility (core_anti_extension, core_anti_rotation, carry, mobility)
  └─ Intra-day Deduplication (accumulating excludedExerciseIds)
        ↓
Whole-Plan Feasibility Verification
        ↓
Structural Multi-Week Container (1–12 Weeks with 4-Week Block Phases)
        ↓
WorkoutPlanResponse (State A, B, C, or D)
```

---

## 4. Split Routing Verification

| Training Days | Target Split | Days Generated |
| :--- | :--- | :--- |
| **1 Day** | `full_body` | Full Body A |
| **2 Days** | `full_body` | Full Body A, Full Body B |
| **3 Days** | `full_body` | Full Body A, Full Body B, Full Body C |
| **4 Days** | `upper_lower` | Upper A, Lower A, Upper B, Lower B |
| **5 Days** | `upper_lower` | Upper, Lower, Push, Pull, Legs |
| **6 Days** | `push_pull_legs` | Push A, Pull A, Legs A, Push B, Pull B, Legs B |

---

## 5. Slot Allocation & Constraints Behavior

1. **Slot 0 (Warmup / Corrective):**
   - Populated only when both `correctiveSourceExerciseId` and `correctiveIssueId` are provided.
   - Requires canonical CV source (`ex_squat`, `ex_bench_press`, `ex_deadlift`, `ex_bicep_curl`, `ex_shoulder_press`) and authoritative Phase 9B.8.3 mapping.
   - Omitted cleanly when no corrective parameters are provided.

2. **Slot 1 (Primary Compound):**
   - Strictly enforces `exercise_type == compound`.
   - Rejects isolation movements.
   - Enforces inter-day primary diversity: prefers alternating primary compound across consecutive training days when catalog alternatives exist, falling back gracefully to reuse only if constrained.

3. **Slot 2 (Secondary Compound):**
   - Strictly enforces `exercise_type == compound`.
   - Distinct from Slot 1.
   - Aligns with day's complementary movement pattern.

4. **Slots 3 & 4 (Accessories):**
   - Allocates target muscle volume for the day.
   - Slot 4 applies a soft preference for unilateral movements.

5. **Slot 5 (Core / Mobility):**
   - Targets `core_anti_extension`, `core_anti_rotation`, `carry`, `mobility` patterns or `core`/`abs` primary muscles.

6. **Intra-Day Deduplication:**
   - Every selected exercise is accumulated into `current_excluded_ids`.
   - Zero duplicate exercise IDs on any single training day.

---

## 6. Diagnostic States Verification

- **State A (Valid Plan):** All days and required slots populated. `feasibilityCheckPassed=True`.
- **State B (Missing / Invalid Input):** Missing corrective pair or invalid parameters return `feasibilityCheckPassed=False`, `weeks=[]`, and actionable diagnostic.
- **State C (Conflicting Hard Constraints):** Conflicting split preferences or mutually impossible equipment/environment combinations return `conflictingFilters=[...]`, `feasibilityCheckPassed=False`, `weeks=[]`.
- **State D (Catalog Feasibility Shortfall):** When the catalog cannot satisfy a required slot (e.g. all compounds excluded), returns `feasibilityCheckPassed=False`, `weeks=[]`, and exact shortfall diagnostic detailing the day, slot, and constraints. Never fabricates exercises.

---

## 7. Exact Test Counts & Results

### 1. Dedicated Service Test Suite:
```bash
py -m pytest backend/tests/test_workout_plan_service.py -v
```
- **Results:** **28 passed**, 0 failed (0.79s)

### 2. Combined Exercise, Recommendation & Planner Suite:
```bash
py -m pytest backend/tests/test_workout_plan_schemas.py backend/tests/test_workout_plan_service.py backend/tests/test_exercise_recommendations.py backend/tests/test_exercise_relationships.py backend/tests/test_exercise_catalog.py backend/tests/test_exercise_knowledge_schema.py -q
```
- **Results:** **151 passed**, 0 failed (0.96s)

### 3. Full Backend Regression Suite:
```bash
py -m pytest backend/tests -q
```
- **Results:** **624 passed**, 1 failed, 7 warnings in 34.00s
- **Audit of Single Failure:**
  - `backend/tests/test_users.py::test_valid_authenticated_user_dependency`
  - Cause: External Google Cloud Firestore `429 Quota exceeded` on real network call in unmocked legacy test.
  - Confirmed as the known pre-existing external quota limit, not a planner regression.

### 4. Frontend Test Suite:
```bash
npm test -- --run
```
- **Results:** **61 passed**, 0 failed (2.25s)

### 5. Frontend Production Build:
```bash
npm run build
```
- **Results:** Successful build (`vite v8.2.2`, 0 errors, 1.29s).

---

## 8. Security & Boundary Audit

| Boundary | Compliance Status | Details |
| :--- | :--- | :--- |
| **No Gemini / LLM** | Verified Compliant | Pure Python deterministic construction. No LLM imports or calls. |
| **No Firestore / Database** | Verified Compliant | Zero Firestore reads or writes. Pure in-memory calculation. |
| **No External APIs / Network** | Verified Compliant | Zero HTTP requests or remote socket connections. |
| **No Credentials / Secrets** | Verified Compliant | No API keys, passwords, or tokens added. |
| **No PII / User Data** | Verified Compliant | Operates strictly on the incoming request payload. Zero profile reads. |
| **Frontend Untouched** | Verified Compliant | Zero frontend files modified. |

---

## 9. Scope Enclosure Audit

- **Sub-Phase 9B.8.5.3 (Multi-Week Periodization & Prescription Logic):** NOT started.
- **Sub-Phase 9B.8.5.4 (HTTP API Endpoint):** NOT started.
- **Frontend UI Code:** NOT modified.
- **Phase 9B.8.6 / Phase 9C:** NOT started.

---

## 10. Stop Condition Declaration

Phase 9B.8.5.2 implementation complete — awaiting explicit approval for Phase 9B.8.5.3.
