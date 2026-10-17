# Phase 9B.2 Implementation Report — Form Heuristics Only

**Phase Status**: COMPLETE — AWAITING APPROVAL  
**Date**: September 13, 2026  
**Module**: AI Form Analysis — Exercise Intelligence & Real-Time Engine (Sub-phase 9B.2)

---

## 1. Executive Summary

Phase 9B.2 implements a deterministic, explainable exercise form heuristic evaluation engine. It strictly consumes structured kinematic observations (joint angles, landmark coordinates, confidence scores) produced by Phase 9A and Phase 9B.1, evaluates four standardized heuristic categories across five core exercises, and enforces an observability model where missing or low-confidence data is never conflated with poor form.

In strict compliance with the Phase 9B.2 boundary:
- **No rep counting or FSM logic** was added (Phase 9B.1 remains the sole authoritative source).
- **No scoring or score aggregation** was implemented (deferred to Phase 9B.3).
- **No WebSockets, streaming, or camera integration** was created (deferred to Phase 9B.4–9B.6).
- **No Firestore persistence, LLM calls, video recording, or audio coaching** was included (Phase 9C).
- **No medical or injury prevention claims** are made.

---

## 2. Files Created and Modified

### Created Files:
1. `backend/app/services/form_heuristics.py`
   - Primary service module containing:
     - `FormHeuristicsService` with exercise-specific evaluation logic
     - Dataclasses: `HeuristicThresholds`, `FormHeuristicResult`, `ExerciseFormReport`
     - Centralized configuration table `STANDARD_HEURISTIC_CONFIGS`
     - Deterministic parameterized feedback generator
     - Jitter-based temporal window stability evaluator
2. `backend/tests/test_form_heuristics.py`
   - 34 comprehensive deterministic test cases covering all 30 mandatory requirements and edge conditions
3. `PHASE_9B_2_IMPLEMENTATION_REPORT.md`
   - This implementation report

### Modified Files:
1. `backend/app/schemas/form_analysis.py`
   - Added `ObservabilityStatus` enum (`OBSERVED`, `INSUFFICIENT_CONFIDENCE`, `NOT_OBSERVABLE`, `INVALID`)
   - Added `HeuristicCategory` enum (`ROM`, `JOINT_ALIGNMENT_TECHNIQUE`, `SYMMETRY`, `STABILITY`)
   - Added Pydantic schema `FormHeuristicResultSchema`
   - Added Pydantic schema `ExerciseFormReportSchema`

---

## 3. Heuristic Architecture & Categories

### 3.1 Four Standard Heuristic Categories
1. **ROM (Range of Motion)**: Evaluates peak joint flexion/extension against biomechanical engineering criteria for the movement.
2. **Joint Alignment / Technique**: Evaluates tracking, planar alignment, torso inclination, and sequencing proxies. Never termed "Safety"; strictly non-diagnostic.
3. **Symmetry**: Evaluates left-vs-right bilateral joint balance when and only when both bilateral sides are observable with sufficient confidence.
4. **Stability**: Evaluates velocity jitter and frame-to-frame landmark centroid/joint displacement across a bounded sliding observation window.

*(Note: Target weights ROM=0.40, Technique=0.35, Symmetry=0.15, Stability=0.10 are reserved for Phase 9B.3; Phase 9B.2 outputs individual heuristic results without weighted aggregation).*

### 3.2 Observability Model & Invariant Rule
- **Invariant**: `MISSING DATA != BAD FORM`.
- Possible observability states:
  - `OBSERVED`: Required landmarks/metrics are present, confidence meets or exceeds `confidence_threshold` (default 0.60), and values are finite. Form deviation is evaluated against reference thresholds.
  - `INSUFFICIENT_CONFIDENCE`: Landmarks or metrics exist, but the associated confidence score falls below the required threshold. Deviation is set to `0.0` with explanatory feedback.
  - `NOT_OBSERVABLE`: Required landmarks/metrics are omitted (e.g., contralateral limb out of frame in a sagittal camera view). Deviation is set to `0.0`.
  - `INVALID`: Non-finite values (`NaN`, `inf`, `-inf`), physically impossible joint angles (< 0° or > 360°), or empty inputs. Form evaluation is rejected safely.

Each `ExerciseFormReport` calculates:
- `observable_count`: Number of heuristics evaluated as `OBSERVED`
- `total_heuristics`: Total heuristics defined for the exercise
- `observability_ratio`: `observable_count / total_heuristics`
This explicitly equips Phase 9B.3 with the exact data needed to enforce the `< 70%` insufficient data rule without calculating final scores in Phase 9B.2.

---

## 4. Exercise-Specific Heuristics & Configured Thresholds

All thresholds are centralized in `STANDARD_HEURISTIC_CONFIGS` in `form_heuristics.py`. They are conservative engineering tolerances, not clinical claims.

### 4.1 Squat
| Category | Heuristic Name | Primary Metric | Reference Target | Tolerance | Evaluation Rule |
|---|---|---|---|---|---|
| ROM | `knee_flexion_depth` | `knee_angle` (min) | 90.0° | 15.0° | Must achieve flexion <= 105.0° (90° + 15°) |
| Joint Alignment / Technique | `knee_tracking_alignment` | `knee_tracking_offset` | 0.00 | 0.12 (norm) | |lateral offset| <= 0.12 |
| Joint Alignment / Technique | `torso_inclination` | `torso_inclination` | 35.0° | 20.0° | Deviation from 35° vertical <= 20° (15°–55°) |
| Symmetry | `knee_symmetry` | `left_knee_angle`, `right_knee_angle` | 0.0° | 12.0° | |left - right| <= 12.0° |
| Stability | `rep_stability` | Window jitter (`knee_angle`) | 0.0 | 4.0°/frame | Mean frame-to-frame velocity delta <= 4.0 |

### 4.2 Bench Press
| Category | Heuristic Name | Primary Metric | Reference Target | Tolerance | Evaluation Rule |
|---|---|---|---|---|---|
| ROM | `elbow_press_rom` | `elbow_angle` (min) | 85.0° | 15.0° | Must achieve flexion <= 100.0° |
| Joint Alignment / Technique | `shoulder_elbow_alignment` | `shoulder_elbow_alignment` | 75.0° | 15.0° | Elbow flare angle between 60° and 90° |
| Symmetry | `elbow_symmetry` | `left_elbow_angle`, `right_elbow_angle` | 0.0° | 10.0° | |left - right| <= 10.0° |
| Stability | `bench_stability` | Window jitter (`elbow_angle`) | 0.0 | 3.5°/frame | Mean frame-to-frame velocity delta <= 3.5 |

*(Note: No barbell detection or bar path claims; evaluates only observable body landmarks).*

### 4.3 Deadlift
| Category | Heuristic Name | Primary Metric | Reference Target | Tolerance | Evaluation Rule |
|---|---|---|---|---|---|
| ROM | `lockout_extension` | `hip_angle` (max) | 170.0° | 10.0° | Must achieve hip lockout >= 160.0° |
| Joint Alignment / Technique | `hip_knee_sequencing` | `sequencing_ratio` (hip_delta/knee_delta) | 1.00 | 0.50 | Ratio within [0.50, 1.50] |
| Joint Alignment / Technique | `trunk_neutrality_proxy` | `trunk_angle` | 45.0° | 15.0° | Deviation from neutral angle <= 15.0° |
| Symmetry | `hip_knee_symmetry` | `left_hip_angle`, `right_hip_angle` | 0.0° | 10.0° | |left - right| <= 10.0° |
| Stability | `body_center_stability` | Window jitter (`landmark_centroid_x`) | 0.0 | 0.03 (norm) | Centroid x-coordinate velocity jitter <= 0.03 |

*(Note: Refers strictly to "landmark centroid" or "estimated body center", never "center of mass").*

### 4.4 Bicep Curl
| Category | Heuristic Name | Primary Metric | Reference Target | Tolerance | Evaluation Rule |
|---|---|---|---|---|---|
| ROM | `elbow_flexion_rom` | `elbow_angle` (min) | 45.0° | 15.0° | Peak curl flexion <= 60.0° |
| Joint Alignment / Technique | `upper_arm_stability` | `shoulder_angle` drift | 0.0° | 15.0° | Shoulder angle drift <= 15.0° |
| Joint Alignment / Technique | `torso_compensation_proxy` | `torso_inclination` drift | 0.0° | 10.0° | Torso sway <= 10.0° |
| Symmetry | `elbow_curl_symmetry` | `left_elbow_angle`, `right_elbow_angle` | 0.0° | 12.0° | |left - right| <= 12.0° |
| Stability | `curl_movement_stability` | Window jitter (`elbow_angle`) | 0.0 | 4.0°/frame | Mean frame-to-frame velocity delta <= 4.0 |

### 4.5 Shoulder Press
| Category | Heuristic Name | Primary Metric | Reference Target | Tolerance | Evaluation Rule |
|---|---|---|---|---|---|
| ROM | `overhead_lockout_rom` | `elbow_angle` (max) | 170.0° | 10.0° | Lockout extension >= 160.0° |
| Joint Alignment / Technique | `shoulder_elbow_alignment` | `shoulder_elbow_alignment` | 90.0° | 15.0° | Alignment angle within 75°–105° |
| Symmetry | `press_symmetry` | `left_elbow_angle`, `right_elbow_angle` | 0.0° | 10.0° | |left - right| <= 10.0° |
| Stability | `torso_press_stability` | Window jitter (`torso_inclination`) | 0.0 | 3.5°/frame | Torso frame-to-frame velocity delta <= 3.5 |

---

## 5. Temporal Sliding Window & Single-Frame Noise Immunity

To satisfy the temporal robustness requirement:
- Stability evaluation inspects a sliding window of recent kinematic observations (default window size: 8 frames).
- Frame-to-frame velocity jitter is evaluated:
  $$\text{jitter} = \frac{1}{N-1} \sum_{i=1}^{N-1} |x_i - x_{i-1}|$$
- If an isolated single frame experiences a momentary velocity spike while the remaining window trajectory is smooth, the mean velocity delta remains below the threshold, preventing false form defects.
- When an insufficient number of frames exists in the history (fewer than 3 frames), the stability heuristic reports `ObservabilityStatus.NOT_OBSERVABLE` with feedback: *"Insufficient observation history to evaluate window stability."*

---

## 6. Deterministic Parameterized Feedback

Feedback is generated strictly using static string templates parameterized by observed and reference values:
- **Acceptable Form**:
  - *"Observed knee_flexion_depth (88.0 deg) is within acceptable reference range (90.0 deg ± 15.0 deg)."*
  - *"Bilateral left_knee_angle and right_knee_angle symmetry (difference 4.0 deg) is within acceptable tolerance (12.0 deg)."*
- **Deviation Observed**:
  - *"Knee alignment deviation observed: knee_tracking_alignment deviation 0.16 exceeds tolerance 0.12."*
  - *"Left/right elbow angles differ beyond the configured tolerance: elbow_symmetry difference 16.0 deg exceeds 10.0 deg."*
  - *"Torso inclination exceeded the configured reference range: deviation 25.0 deg exceeds tolerance 20.0 deg."*
- **Observability / Confidence Notice**:
  - *"Insufficient landmark confidence (0.45 < 0.60) to evaluate knee_symmetry."*
  - *"Metric 'right_knee_angle' is not observable in the current camera view."*
  - *"Invalid numerical value (NaN, Inf, or impossible angle) encountered for 'knee_angle'."*

Zero medical, diagnostic, or injury claims are generated.

---

## 7. Verification and Test Results

### 7.1 Phase 9B.2 Heuristic Unit & Behavioral Tests
Command: `py -m pytest backend/tests/test_form_heuristics.py -v`  
Result: **34 passed in 0.10s**

Coverage of the 30 specified requirements:
1. `test_valid_squat_technique_observations` (Valid squat form)
2. `test_squat_depth_deviation` (Squat depth deviation)
3. `test_squat_alignment_deviation` (Squat alignment deviation)
4. `test_squat_bilateral_symmetry` (Squat bilateral symmetry)
5. `test_bench_press_rom` (Bench ROM)
6. `test_bench_left_right_asymmetry` (Bench symmetry)
7. `test_bench_stability` (Bench stability)
8. `test_deadlift_hip_knee_sequencing` (Deadlift sequencing)
9. `test_deadlift_torso_angle_deviation` (Deadlift torso deviation)
10. `test_deadlift_symmetry` (Deadlift symmetry)
11. `test_bicep_curl_rom` (Bicep curl ROM)
12. `test_bicep_curl_excessive_upper_arm_movement` (Bicep curl upper-arm drift)
13. `test_shoulder_press_rom` (Shoulder press ROM)
14. `test_shoulder_press_symmetry` (Shoulder press symmetry)
15. `test_shoulder_press_stability` (Shoulder press stability)
16. `test_low_confidence_observations` (Low-confidence does not produce defect)
17. `test_missing_landmarks_not_observable` (Missing landmarks -> NOT_OBSERVABLE)
18. `test_not_observable_behavior_contralateral_limb` (Unseen contralateral limb)
19. `test_invalid_observation_handling` (Impossible angles -> INVALID)
20. `test_nan_infinity_protection` (NaN/Inf protection)
21. `test_temporal_noisy_observations` (Sustained jitter detected)
22. `test_single_frame_noise_does_not_produce_defect` (Single-frame noise immunity)
23. `test_determinism_identical_inputs_identical_outputs` (Identical inputs -> identical outputs)
24. `test_threshold_boundary_exact` (Exact threshold boundary)
25. `test_threshold_boundary_just_inside` (Just inside threshold)
26. `test_threshold_boundary_just_outside` (Just outside threshold)
27. `test_cross_exercise_configuration_isolation` (Cross-exercise configuration isolation)
28. `test_invalid_exercise_id_rejected` (Unknown exercise ID raises ValueError)
29. `test_insufficient_observation_history` (History < 3 frames -> NOT_OBSERVABLE)
30. `test_timestamp_order_validation` (Timestamp regression check)
31. `test_custom_thresholds_override` (Configuration extensibility)
32. `test_insufficient_data_rule_observability_ratio` (Observability ratio calculation)
33. `test_no_rep_counting_logic_in_heuristics` (Strict separation from FSM)
34. `test_pydantic_schema_serialization` (Schema compatibility and serializability)

### 7.2 Combined Phase 9B Test Suite
Command: `py -m pytest backend/tests/test_exercise_fsm.py backend/tests/test_form_heuristics.py -v`  
Result: **66 passed in 0.09s**

### 7.3 Full Backend Regression Suite
Command: `py -m pytest backend/tests/ -v`  
Result: **327 passed, 6 warnings in 25.84s** (0 failures, 0 errors)

### 7.4 Frontend Production Build
Command: `npm run build` (`tsc -b && vite build`)  
Result: **PASS** (2676 modules transformed, built in 1.04s, 0 errors)

---

## 8. Security & Phase Boundary Verification

- **Credentials / Secrets**: Zero credentials, secrets, or API keys added.
- **Firestore**: Zero Firestore read or write operations introduced.
- **Network / External Dependencies**: Completely self-contained; zero network calls or cloud API invocations.
- **Payload & Memory**: Pure mathematical/dictionary transformation; zero raw image decoding or persistence.
- **Phase Boundary Adherence**:
  - Phase 9B.3 (scoring) NOT implemented.
  - Phase 9B.4 (session manager) NOT implemented.
  - Phase 9B.5 (WebSocket streaming) NOT implemented.
  - Phase 9B.6 (frontend camera) NOT implemented.
  - Phase 9B.7 (end-to-end integration) NOT implemented.
  - Phase 9C (persistence, voice coaching, Gemini LLM) NOT implemented.
  - Existing `/form-analysis` UI was preserved intact.

---

## 9. Conclusion & Next Steps

Phase 9B.2 is fully verified and complete. Awaiting user authorization to proceed to Phase 9B.3 (Deterministic Form Scoring Engine).
