# Phase 9B.3 Implementation Report — Deterministic Form Scoring Engine Only

**Phase Status**: COMPLETE — AWAITING APPROVAL  
**Date**: September 13, 2026  
**Module**: AI Form Analysis — Exercise Intelligence & Real-Time Engine (Sub-phase 9B.3)

---

## 1. Executive Summary

Phase 9B.3 implements a deterministic, explainable, mathematically bounded (0–100) form scoring engine. It consumes structured heuristic observations from Phase 9B.2, aggregates category qualities using the approved category weights (ROM=0.40, Technique=0.35, Symmetry=0.15, Stability=0.10), enforces the strict gating observability rule (>= 70% required or status is `INSUFFICIENT_DATA` with null score), applies confidence dampening ($C_{\text{penalty}} = \max(0.60, \min(1.0, c_{\text{rep}}))$), and supports deterministic multi-rep set aggregation without penalizing unobservable repetitions.

In strict compliance with the Phase 9B.3 boundary:
- **No rep counting or FSM logic** was added (Phase 9B.1 remains the sole authoritative source).
- **No session manager or WebSocket streaming** was created (deferred to Phase 9B.4 & 9B.5).
- **No camera integration or frontend canvas overlays** were added (deferred to Phase 9B.6).
- **No Firestore persistence, LLM calls, video recording, or audio coaching** was included (Phase 9C).
- **No medical or injury prevention claims** are made. The score is explicitly described as an engineering *"deterministic form-quality score"*.

---

## 2. Files Created and Modified

### Created Files:
1. `backend/app/services/form_scoring.py`
   - Primary scoring domain service containing:
     - `FormScoringEngine` (repetition-level scoring and multi-rep set aggregation)
     - `CategoryWeights` dataclass (validates $w_{\text{ROM}}=0.40, w_{\text{TECH}}=0.35, w_{\text{SYM}}=0.15, w_{\text{STAB}}=0.10$, summing to exactly 1.0)
     - `ScoringConfig` dataclass (centralized tolerances, penalty bounds, unit scaling)
     - `CategoryScore`, `RepetitionScore`, `SetScoreSummary` dataclasses
     - Deterministic parameterized feedback generator
2. `backend/tests/test_form_scoring.py`
   - 36 comprehensive deterministic unit and behavioral tests covering all 35+ mandatory requirements, numerical safeguards, and boundary conditions
3. `PHASE_9B_3_IMPLEMENTATION_REPORT.md`
   - This implementation report

### Modified Files:
1. `backend/app/schemas/form_analysis.py`
   - Added `RepScoreStatus` enum (`VALID`, `INCOMPLETE`, `INVALID`, `INSUFFICIENT_DATA`)
   - Added `CategoryScoreSchema`
   - Added `RepetitionScoreSchema`
   - Added `SetScoreSummarySchema`

---

## 3. Scoring Architecture & Exact Formulas

### 3.1 Mathematical Scoring Model
For any repetition meeting observability criteria:
$$S(r) = \max\left(0.0, \min\left(100.0, S_{\text{base}} \times C_{\text{penalty}}\right)\right)$$

Where:
- $S_{\text{base}} \in [0.0, 100.0]$ is the weighted category quality across observable categories:
  $$S_{\text{base}} = \sum_{c \in \mathcal{C}_{\text{obs}}} w'_c \times Q_c$$
- $w'_c$ is the re-normalized category weight among observable categories:
  $$w'_c = \frac{w_c}{\sum_{k \in \mathcal{C}_{\text{obs}}} w_k}$$
- $Q_c = 100.0 - P_c$ is the category quality score, bounded in $[0.0, 100.0]$.
- $P_c$ is the average heuristic penalty in category $c$:
  $$P_c = \frac{1}{|\mathcal{H}_{c, \text{obs}}|} \sum_{h \in \mathcal{H}_{c, \text{obs}}} P_h$$
- $C_{\text{penalty}} \in [0.60, 1.0]$ is the confidence dampening multiplier:
  $$C_{\text{penalty}} = \max(0.60, \min(1.0, c_{\text{rep}}))$$
  where $c_{\text{rep}}$ is the arithmetic mean tracking confidence of all evaluated `OBSERVED` heuristics.

### 3.2 Individual Heuristic Penalty Normalization ($P_h$)
- **Invariant**: `MISSING DATA != BAD FORM`.
  If $h.\text{status} \neq \text{OBSERVED}$ (e.g. `NOT_OBSERVABLE`, `INSUFFICIENT_CONFIDENCE`, `INVALID`):
  $$P_h = 0.0$$
- If $h.\text{is\_acceptable} == \text{True}$ (within tolerance):
  $$P_h = 0.0$$
- If $h.\text{is\_acceptable} == \text{False}$ (exceeds tolerance):
  $$P_h = \min\left(100.0, \max\left(0.0, P_{\text{base}} + \text{deviation} \times \text{scale}_{\text{unit}}\right)\right)$$
  Configured defaults:
  - $P_{\text{base}} = 20.0$ points
  - Unit scales:
    - `degrees`: $2.5\text{ pts}/^\circ$
    - `norm_units`: $500.0\text{ pts}/\text{unit}$ ($0.01\text{ drift} = +5.0\text{ pts}$)
    - `ratio`: $160.0\text{ pts}/\text{unit}$ ($0.10\text{ deficit} = +16.0\text{ pts}$)
    - `std_dev` / `degrees/frame`: $10.0\text{ pts}/\text{unit}$
  - Monotonically increasing and strictly bounded in $[0.0, 100.0]$.

### 3.3 Approved Category Weights
| Category | Configured Weight ($w_c$) | Rationale |
|---|---|---|
| **Range of Motion / Depth** | **0.40** | Foundational movement criterion across all strength exercises. |
| **Joint Alignment / Technique** | **0.35** | High-leverage joint alignment (elbow flare, knee tracking, spine posture). |
| **Bilateral Symmetry** | **0.15** | Balanced load distribution across contralateral limbs. |
| **Stability / Tempo** | **0.10** | Frame-to-frame velocity consistency and momentum control. |
| **Total** | **1.00** | Strictly validated with `math.isclose(sum, 1.0, abs_tol=1e-5)`. |

### 3.4 Prevention of Category Dominance
Each category computes the arithmetic mean penalty of its observable heuristics before the top-level category weight is applied. A category with 4 heuristics (e.g., Technique) does **not** dominate a category with 1 heuristic (e.g., ROM); each category contributes strictly according to its approved top-level weight.

---

## 4. Gating Observability Rule (>= 70%)

The system evaluates the observability ratio across all heuristics defined for the repetition:
$$\text{observability\_ratio} = \frac{N_{\text{observed}}}{N_{\text{total}}}$$

- If $\text{observability\_ratio} < 0.70$ (e.g. 69.99% or 6 of 10 heuristics):
  - `status = RepScoreStatus.INSUFFICIENT_DATA`
  - `score = None`
  - `base_score = None`
  - Explanatory feedback: *"Insufficient landmark observability for a reliable score (X/Y heuristics observed, Z% < 70.0% required). Adjust camera view."*
- If $\text{observability\_ratio} \ge 0.70$ (e.g. exactly 70.0% or 100.0%):
  - Scoring proceeds normally.

---

## 5. Repetition Status Lifecycle & Multi-Rep Aggregation

### 5.1 Rep-Level Statuses
- `VALID`: Completed repetition with $\ge 70\%$ observability and valid kinematic trajectory. Receives a numerical score in $[0.0, 100.0]$.
- `INCOMPLETE`: Repetition reset before completing the return phase (e.g., FSM `RepOutcome.INCOMPLETE_REP`). Score is `None`.
- `INVALID`: Repetition invalidated due to landmark occlusion timeout or invalid kinematic values (e.g., FSM `RepOutcome.INVALIDATED_REP`). Score is `None`.
- `INSUFFICIENT_DATA`: Repetition had $< 70\%$ observability. Score is `None`.

### 5.2 Multi-Rep Set Aggregation
`FormScoringEngine.aggregate_set(reps)`:
- Computes the arithmetic mean of all valid completed repetitions:
  $$\text{overall\_score} = \frac{1}{|\mathcal{R}_{\text{valid}}|} \sum_{r \in \mathcal{R}_{\text{valid}}} r.\text{score}$$
- Repetitions with `INSUFFICIENT_DATA`, `INCOMPLETE`, or `INVALID` are **excluded** from the arithmetic mean. Missing data is **never converted to a zero score**.
- Returns a structured `SetScoreSummary` tracking `total_reps`, `valid_reps`, `insufficient_data_reps`, `incomplete_reps`, and `invalid_reps`.

---

## 6. Numerical Safeguards & Deterministic Feedback

- **NaN / Infinity Protection**: Non-finite numbers in joint deviations, confidence values, or weights are caught and sanitized. Invalid numbers never produce penalties.
- **Bounds Clamping**: All penalties are clamped to $[0.0, 100.0]$. Scores are strictly clamped to $[0.0, 100.0]$.
- **Deterministic Parameterized Feedback**:
  - Scores $\ge 90.0$: *"High technique quality observed across evaluated movement criteria."*
  - Scores $75.0\text{--}89.9$: *"Good repetition execution with minor technique adjustments observed."*
  - Category breakdown: *"ROM score: 60.0/100 (penalty deduction: 40.0)."*
  - Specific defect observations: *"Observation: squat_depth: Knee flexion did not reach the configured parallel depth threshold."*
  - Confidence adjustment: *"Score adjusted by tracking confidence factor (0.85). Ensure clear lighting and camera framing."*
  - Zero medical diagnosis, injury prediction, or LLM hallucination.

---

## 7. Verification and Test Results

### 7.1 Phase 9B.3 Scoring Unit & Behavioral Tests
Command: `py -m pytest backend/tests/test_form_scoring.py -v`  
Result: **36 passed in 0.10s**

Coverage of all required scenarios:
1. `test_1_perfect_form_scores_100` (Perfect form -> 100.0)
2. `test_2_rom_only_deviation_governed_by_040_weight` (ROM deduction = 0.40 * penalty)
3. `test_3_technique_only_deviation_governed_by_035_weight` (Technique deduction = 0.35 * penalty)
4. `test_4_symmetry_only_deviation_governed_by_015_weight` (Symmetry deduction = 0.15 * penalty)
5. `test_5_stability_only_deviation_governed_by_010_weight` (Stability deduction = 0.10 * penalty)
6. `test_6_multiple_category_deviations_cumulative` (Cumulative deduction across categories)
7. `test_7_8_weight_calculation_and_sum_to_one` (Weight validation and sum to 1.0)
8. `test_9_score_bounded_at_zero` (Score clamped at 0.0)
9. `test_10_score_bounded_at_100` (Score clamped at 100.0)
10. `test_11_confidence_penalty_at_c_1_0` (Confidence factor = 1.0 at c=1.0)
11. `test_12_confidence_penalty_below_0_60` (Confidence factor clamped at 0.60 floor)
12. `test_13_confidence_penalty_between_0_60_and_1_0` (Linear confidence scaling)
13. `test_14_exactly_70_percent_observable_allowed` (Exactly 70% observable allows scoring)
14. `test_15_below_70_percent_observable_insufficient_data` (60% observable -> INSUFFICIENT_DATA, score=null)
15. `test_16_zero_observable_insufficient_data` (0% observable -> INSUFFICIENT_DATA, score=null)
16. `test_17_missing_heuristic_data_no_form_penalty` (Missing data -> 0 penalty)
17. `test_18_low_confidence_heuristic_no_form_penalty` (Low confidence -> 0 penalty)
18. `test_19_not_observable_heuristic_no_form_penalty` (NOT_OBSERVABLE -> 0 penalty)
19. `test_20_invalid_heuristic_no_form_penalty` (INVALID -> 0 penalty)
20. `test_21_nan_protection` (NaN deviation -> 0 penalty)
21. `test_22_infinity_protection` (Inf deviation -> 0 penalty)
22. `test_23_negative_penalty_protection` (Negative deviation -> clamped to 0 penalty)
23. `test_24_excessive_penalty_protection` (Huge deviation -> clamped to 100.0 penalty)
24. `test_25_malformed_category_input` (Graceful handling of unknown categories)
25. `test_26_invalid_confidence_values_clamped` (Negative / >1 confidence clamped)
26. `test_27_incomplete_rep_handling` (Incomplete rep -> INCOMPLETE status, score=null)
27. `test_28_invalid_rep_handling` (Invalid rep -> INVALID status, score=null)
28. `test_29_multi_rep_deterministic_aggregation` (Arithmetic mean across valid reps)
29. `test_30_insufficient_data_reps_in_aggregation_not_zero` (Insufficient data reps excluded from mean, not zeroed)
30. `test_31_determinism_across_identical_calls` (Identical inputs -> identical scores)
31. `test_32_cross_exercise_configuration_isolation` (Custom configurations do not bleed)
32. `test_33_every_category_contributes_according_to_approved_weight` (Weights verified: 40/35/15/10)
33. `test_34_no_category_dominates_due_to_having_more_heuristics` (Category averaging prevents dominance)
34. `test_35_deterministic_feedback_generation` (Feedback strings derive strictly from findings)
35. `test_36_schema_serialization` (RepetitionScore and SetScoreSummary serialize to Pydantic)
36. `test_37_exercise_form_report_direct_input` (Direct scoring of ExerciseFormReport from Phase 9B.2)

### 7.2 Combined Phase 9B Test Suite (9B.1 + 9B.2 + 9B.3)
Command: `py -m pytest backend/tests/test_exercise_fsm.py backend/tests/test_form_heuristics.py backend/tests/test_form_scoring.py -v`  
Result: **102 passed, 1 warning in 0.15s**

### 7.3 Full Backend Regression Suite
Command: `py -m pytest backend/tests/ -v`  
Result: **363 passed, 6 warnings in 27.22s** (0 failures, 0 errors)

### 7.4 Frontend Production Build
Command: `npm run build` (`tsc -b && vite build`)  
Result: **PASS** (2676 modules transformed, built in 787ms, 0 errors)

---

## 8. Security & Phase Boundary Audit

- **Credentials / Secrets**: Zero credentials, secrets, or API keys added.
- **Firestore**: Zero Firestore read or write operations introduced.
- **Network / External Dependencies**: Completely self-contained; pure mathematical evaluation in volatile RAM.
- **Rep-Counting Boundary**: Scoring engine does not count reps or mutate FSM states.
- **Phase Boundary Adherence**:
  - Phase 9B.4 (in-memory session manager) NOT implemented.
  - Phase 9B.5 (WebSocket streaming endpoint) NOT implemented.
  - Phase 9B.6 (frontend camera & canvas skeleton overlay) NOT implemented.
  - Phase 9B.7 (end-to-end integration) NOT implemented.
  - Phase 9C (Firestore session persistence, voice coaching, Gemini LLM) NOT implemented.
  - Existing `/form-analysis` UI was preserved intact.

---

## 9. Conclusion & Next Steps

Phase 9B.3 is fully implemented, rigorously tested, and verified against the complete test regression suite. Awaiting user authorization to proceed to Phase 9B.4 (In-Memory Session Manager).
