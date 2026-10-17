# Phase 9C.6 — Form Analysis & Corrective Integration
## Architecture Assessment, Scope Definition & Implementation Plan

**Document Version**: 2.3.0  
**Phase Target**: Phase 9C.6 — Form Analysis & Corrective Integration  
**Preceding Milestone**: Phase 9C.5.7 — Comprehensive Verification & Regression (Status: PASS, FROZEN)  
**Implementation State**: Architecture Assessment & Planning Only (Zero Production Code Changed)  
**Implementation Readiness Verdict**: `READY FOR FINAL ARCHITECTURE REVIEW — IMPLEMENTATION NOT APPROVED`

---

## 1. Executive Summary

Phase 9C.6 establishes the architectural blueprint for connecting the AI FITNESS platform's Computer Vision Form Analysis subsystem with its Foundational Exercise Knowledge Graph and Adaptive Workout Planning engine.

The platform currently includes:
1. A real-time MediaPipe-based pose estimation and heuristic observation engine supporting **exactly five canonical compound exercises** (`ex_squat`, `ex_bench_press`, `ex_deadlift`, `ex_bicep_curl`, `ex_shoulder_press`).
2. A relational exercise knowledge graph containing **exactly 100 catalog exercises**, with **exactly 25 precomputed heuristic-to-corrective mappings** covering **15 normalized issue IDs**.
3. A multi-week adaptive mesocycle architecture featuring an **immutable original plan snapshot** (`planSnapshot`), dynamic effective prescriptions (`effectivePlanSnapshot`), and an optional **Slot 0 (`warmup_corrective`)** in every daily template.

The primary objective of Phase 9C.6 is to bridge these subsystems into an explainable, non-medical technique guidance layer. This document defines the formal evidence aggregation contracts, issue normalization layer, corrective recommendation pipeline, read-only API schemas, and the user-governed future workout proposal boundary.

### Architectural Invariants
* **Zero Production Code Modified**: This document is an architecture assessment and planning document only. Zero source files, tests, configuration files, or database collections are modified.
* **Strict Non-Medical Boundary**: The system provides general exercise technique guidance and mobility drill suggestions. It does not diagnose injuries, treat medical conditions, or infer physical pathology from pose landmarks.
* **Zero Direct Program Mutation**: Form analysis observations never directly mutate an active workout session or the immutable original `planSnapshot`.
* **Zero Automatic Substitution**: The initial implementation rejects automatic exercise replacement in active programs.
* **Zero LLM in the Live Loop**: The live camera stream operates purely on deterministic MediaPipe heuristics and FSM state machines. Gemini is not used for autonomous prescription or adaptation decisions.
* **No False-Positive Guarantees**: Monocular smartphone computer vision is inherently subject to optical noise, perspective distortion, and occlusion. The architecture mitigates false alerts through multi-set and multi-session evidence thresholds, but does not claim zero false-positive risk.
* **Separation of Architecture from Implementation**: This phase establishes technical designs only. Implementation of subphases (9C.6.1–9C.6.7) and any future application of corrective prescriptions to workout plans require separate, explicit user approvals.

---

## 2. Current Implementation Audit

An exhaustive audit of the active repository was conducted. All referenced files, schemas, and functions were verified on disk.

### 2.1 Form Analysis & Computer Vision Subsystem (Phases 9A, 9B.1–9B.7)
* **Pose Estimation & Keypoint Detection**:
  * [`backend/app/services/pose_estimator.py`](file:///c:/Users/Suchit/Downloads/Fitness%20App/backend/app/services/pose_estimator.py): Integrates Google MediaPipe Tasks Vision `PoseLandmarker`. Configured with `min_pose_detection_confidence = 0.5`, `min_pose_presence_confidence = 0.5`, and `min_tracking_confidence = 0.5`. Extracts 33 normalized body keypoints (`NormalizedLandmarkSchema`), bounding box (`BoundingBoxSchema`), and an estimated landmark centroid approximation (`EstimatedBodyCenterSchema`).
* **Joint Kinematics & Occlusion**:
  * [`backend/app/services/geometry_utils.py`](file:///c:/Users/Suchit/Downloads/Fitness%20App/backend/app/services/geometry_utils.py): Pure mathematical 2D/3D angle calculations (`calculate_angle_2d`, `calculate_angle_3d`). Uses `confidence_threshold = 0.5`. Evaluates joint occlusion per angle: `is_occluded = joint_conf < 0.5`. Computes overall confidence as the mean of evaluated joint confidences.
* **Repetition Finite State Machine (FSM)**:
  * [`backend/app/services/exercise_fsm.py`](file:///c:/Users/Suchit/Downloads/Fitness%20App/backend/app/services/exercise_fsm.py): Tracks movement phases (`START_POSITION` $\rightarrow$ `ECCENTRIC` $\rightarrow$ `INFLECTION` $\rightarrow$ `CONCENTRIC` $\rightarrow$ `REP_COMPLETED`). Emits repetition outcomes: `RepOutcome.VALID_REP`, `RepOutcome.INCOMPLETE_REP`, and `RepOutcome.INVALIDATED_REP`.
* **Visual Heuristics Engine**:
  * [`backend/app/services/form_heuristics.py`](file:///c:/Users/Suchit/Downloads/Fitness%20App/backend/app/services/form_heuristics.py): Evaluates visual heuristics across **exactly 5 canonical exercises**:
    1. `ex_squat` (5 heuristics): `squat_depth` (angle), `squat_torso_inclination` (angle), `squat_knee_tracking` (ratio), `squat_knee_symmetry` (percent delta), `squat_movement_stability` (stability variance).
    2. `ex_bench_press` (4 heuristics): `bench_elbow_rom` (angle), `bench_elbow_flare` (angle), `bench_elbow_symmetry` (percent delta), `bench_movement_stability` (stability variance).
    3. `ex_deadlift` (6 heuristics): `deadlift_hip_lockout` (angle), `deadlift_hip_knee_sequencing` (timing), `deadlift_torso_angle` (angle), `deadlift_body_center_stability` (centroid drift units), `deadlift_hip_symmetry` (percent delta), `deadlift_movement_stability` (stability variance).
    4. `ex_bicep_curl` (5 heuristics): `curl_elbow_rom` (angle), `curl_upper_arm_drift` (angle), `curl_torso_momentum` (angle), `curl_elbow_symmetry` (percent delta), `curl_movement_stability` (stability variance).
    5. `ex_shoulder_press` (5 heuristics): `shoulder_press_lockout` (angle), `shoulder_press_forearm_verticality` (angle), `shoulder_press_torso_lean` (angle), `shoulder_press_elbow_symmetry` (percent delta), `shoulder_press_movement_stability` (stability variance).
  * **Observability States** ([`backend/app/schemas/form_analysis.py`](file:///c:/Users/Suchit/Downloads/Fitness%20App/backend/app/schemas/form_analysis.py)):
    * `OBSERVED`: Landmarked and measured with joint confidence $\ge 0.50$.
    * `INSUFFICIENT_CONFIDENCE`: Keypoints detected, but confidence $< 0.50$.
    * `NOT_OBSERVABLE`: Required keypoints missing from the frame or camera perspective.
    * `INVALID`: Mathematical anomaly (NaN, division by zero, out-of-bounds).
  * **Critical Architectural Guardrail Verified**: Missing or low-confidence data is NEVER treated as bad form. The technique compliance flag `is_acceptable` is evaluated *strictly* when `status == ObservabilityStatus.OBSERVED`.
* **Deterministic Repetition Scoring**:
  * [`backend/app/services/form_scoring.py`](file:///c:/Users/Suchit/Downloads/Fitness%20App/backend/app/services/form_scoring.py): Computes rep scores (0–100) using category weights: ROM ($0.40$), Joint Alignment / Technique ($0.35$), Symmetry ($0.15$), Stability ($0.10$).
  * Requires $\ge 70\%$ of required heuristics to be `OBSERVED`. If observability $< 70\%$, rep score status is `INSUFFICIENT_DATA` and `score = None`.
  * Derives rep confidence $c_{\text{rep}}$ from observed heuristics. Uses a confidence penalty floor `min_confidence_floor = 0.60` via $C_{\text{penalty}} = \max(0.60, \min(1.0, c_{\text{rep}}))$ to damp penalties on lower-confidence reps without zeroing them out.
* **FPS & Streaming Pipeline**:
  * Backend config ([`backend/app/core/config.py:75`](file:///c:/Users/Suchit/Downloads/Fitness%20App/backend/app/core/config.py)): `FORM_MAX_ACCEPTED_FPS: int = 25`.
  * Backend WebSocket route ([`backend/app/api/routes/form_analysis_ws.py:185`](file:///c:/Users/Suchit/Downloads/Fitness%20App/backend/app/api/routes/form_analysis_ws.py)): `fps_limit = float(getattr(settings, "FORM_MAX_ACCEPTED_FPS", 25))`. Enforces rate limiting with minimum interval `min_interval = 1.0 / 25` (40 ms). Uses latest-frame-wins backpressure.
  * Frontend stream hook ([`src/hooks/useFormAnalysisStream.ts:66-67`](file:///c:/Users/Suchit/Downloads/Fitness%20App/src/hooks/useFormAnalysisStream.ts)): `const TARGET_FPS = 25`, `const FRAME_INTERVAL_MS = 40`. Video capture stream requests `frameRate: { ideal: 25, max: 25 }`. Drops animation frames within $<40\text{ ms}$.
  * UI telemetry ([`src/components/form-analysis/CameraLiveViewport.tsx:322`](file:///c:/Users/Suchit/Downloads/Fitness%20App/src/components/form-analysis/CameraLiveViewport.tsx)): Displays live measured FPS and `Target: 25 FPS`.
* **Session Persistence & Current Gap**:
  * [`backend/app/repositories/form_analysis_repository.py`](file:///c:/Users/Suchit/Downloads/Fitness%20App/backend/app/repositories/form_analysis_repository.py): Persists completed sessions ($\ge 1$ rep) under `users/{uid}/form_analysis_sessions/{session_id}` conforming to `FormAnalysisSessionDetailSchema`.
  * **Identified Architectural Gap**: Persisted documents contain `reps: List[CompactRepSummarySchema]`, which stores `feedback: List[str]` and `category_scores`, but does NOT persist structured, canonical `issue_id` tags. Historical trend analysis currently requires structured issue schema extensions or reliable heuristic provenance.

### 2.2 Exercise Knowledge & Corrective Graph Subsystem (Phase 9B.8)
* **100-Exercise Foundational Catalog**:
  * [`backend/app/seeds/exercise_catalog.py`](file:///c:/Users/Suchit/Downloads/Fitness%20App/backend/app/seeds/exercise_catalog.py) & [`backend/app/seeds/catalog.py`](file:///c:/Users/Suchit/Downloads/Fitness%20App/backend/app/seeds/catalog.py): Exactly 100 canonical exercises.
  * Exactly 5 exercises have `supportedFormAnalysis = True` (`cvExerciseId` in `squat`, `bench_press`, `deadlift`, `bicep_curl`, `shoulder_press`). Exactly 95 exercises have `supportedFormAnalysis = False` and `cvExerciseId = None`.
* **Corrective Guidance Mappings**:
  * [`backend/app/seeds/corrective_mappings.py`](file:///c:/Users/Suchit/Downloads/Fitness%20App/backend/app/seeds/corrective_mappings.py): Contains `RAW_CORRECTIVE_MAPPINGS` with **exactly 25 deterministic mappings** corresponding 1:1 to the 25 visual heuristics across the 5 canonical exercises.
  * Maps to **exactly 15 unique normalized issue IDs**:
    1. `insufficient_depth` (Squat depth, Bench press elbow ROM)
    2. `excessive_torso_lean` (Squat torso inclination, Deadlift torso angle, Shoulder press torso lean)
    3. `knee_tracking_deviation` (Squat knee tracking)
    4. `asymmetrical_movement` (Squat knee symmetry, Deadlift hip symmetry, Curl elbow symmetry)
    5. `unstable_torso` (Squat stability, Deadlift stability, Curl torso momentum, Shoulder press stability)
    6. `excessive_elbow_flare` (Bench press elbow flare)
    7. `poor_press_symmetry` (Bench press elbow symmetry, Shoulder press elbow symmetry)
    8. `unstable_movement` (Bench press stability, Curl movement stability)
    9. `insufficient_lockout` (Deadlift hip lockout)
    10. `early_hip_rise` (Deadlift hip-knee sequencing)
    11. `body_center_drift` (Deadlift landmark centroid drift)
    12. `incomplete_rom` (Bicep curl elbow ROM)
    13. `excessive_arm_movement` (Bicep curl upper arm drift)
    14. `insufficient_overhead_range` (Shoulder press lockout)
    15. `forearm_tilt` (Shoulder press forearm verticality)
  * Precomputed bi-directional lookup dictionaries: `HEURISTIC_NAME_TO_ISSUE_ID` and `ISSUE_ID_TO_HEURISTIC_NAME`.
  * Referential integrity verified: 100% of candidate IDs exist in `CATALOG_BY_ID`. Zero dangling pointers. Zero self-references. Zero prohibited medical phrases.
* **Relational & Recommendation Services**:
  * [`backend/app/services/exercise_relationship_service.py`](file:///c:/Users/Suchit/Downloads/Fitness%20App/backend/app/services/exercise_relationship_service.py): Precomputed relationship indexes, including `get_corrective_exercises(source_exercise_id, issue_id)`.
  * [`backend/app/services/exercise_recommendation_service.py`](file:///c:/Users/Suchit/Downloads/Fitness%20App/backend/app/services/exercise_recommendation_service.py): Fully implements `RecommendationIntent.CORRECTIVE`. Enforces equipment as a hard gate (`exercise.equipment ⊆ available_equipment`), applies deterministic scoring weights (`match: 0.50, pattern: 0.25, difficulty: 0.15, muscle: 0.10`), and returns explainable recommendations.

### 2.3 Adaptive Workout Planning & Mesocycle Architecture (Phase 9C)
* **Slot Architecture & Baseline Prescriptions**:
  * [`backend/app/schemas/workout_plan.py`](file:///c:/Users/Suchit/Downloads/Fitness%20App/backend/app/schemas/workout_plan.py): 6 functional slot roles:
    * Slot 0: `ExerciseSlotRole.WARMUP_CORRECTIVE` (Optional corrective drill / mobility preparation).
    * Slot 1: `ExerciseSlotRole.PRIMARY_COMPOUND`.
    * Slot 2: `ExerciseSlotRole.SECONDARY_COMPOUND`.
    * Slot 3: `ExerciseSlotRole.ACCESSORY_1`.
    * Slot 4: `ExerciseSlotRole.ACCESSORY_2`.
    * Slot 5: `ExerciseSlotRole.CORE_MOBILITY`.
  * [`backend/app/services/workout_plan_service.py:770-860`](file:///c:/Users/Suchit/Downloads/Fitness%20App/backend/app/services/workout_plan_service.py): Day templates declare Slot 0 with `is_optional = True`. Method `_allocate_corrective_slot_0()` allocates a candidate into Slot 0 *only* if `request.correctiveSourceExerciseId` and `request.correctiveIssueId` are provided during plan generation.
  * Baseline prescription for Slot 0 (`workout_plan_service.py:1277-1281`): Exactly 2 sets of 10 reps at target RPE 5.0 with 60 seconds rest.
* **Mesocycle Lifecycle & Plan Immutability**:
  * [`backend/app/schemas/program.py`](file:///c:/Users/Suchit/Downloads/Fitness%20App/backend/app/schemas/program.py) & [`backend/app/services/program_service.py`](file:///c:/Users/Suchit/Downloads/Fitness%20App/backend/app/services/program_service.py): Programs are user-scoped under `users/{uid}/programs/{program_id}`.
  * **Critical Plan Immutability Invariant**: `planSnapshot` represents the original agreed-upon mesocycle plan and remains byte-for-byte immutable across the program's lifecycle. Active adaptations apply *strictly* to `effectivePlanSnapshot` for future unstarted workouts.

---

## 3. Existing Contracts and Reusable Services

Phase 9C.6 avoids redundant code by reusing existing, tested domain services and Pydantic schemas:

| Existing Symbol / Service | File Path | Established Role | Reusability in Phase 9C.6 |
| :--- | :--- | :--- | :--- |
| `ObservabilityStatus` | `backend/app/schemas/form_analysis.py` | 4-state observation enum | Reused directly for issue observability gating. |
| `HEURISTIC_NAME_TO_ISSUE_ID` | `backend/app/seeds/corrective_mappings.py` | O(1) heuristic-to-issue lookup | Reused directly in `FormIssueNormalizer`. |
| `RAW_CORRECTIVE_MAPPINGS` | `backend/app/seeds/corrective_mappings.py` | Authoritative corrective definitions | Reused directly for candidate retrieval. |
| `ExerciseRelationshipService` | `backend/app/services/exercise_relationship_service.py` | Graph queries & corrective edges | Reused directly via `get_corrective_exercises()`. |
| `ExerciseRecommendationService` | `backend/app/services/exercise_recommendation_service.py` | Intent-based candidate ranking | Reused directly with `intent=CORRECTIVE`. |
| `_allocate_corrective_slot_0()` | `backend/app/services/workout_plan_service.py` | Slot 0 generator for corrective drills | Target template integration point for future proposals. |
| `FormAnalysisRepository` | `backend/app/repositories/form_analysis_repository.py` | Firestore session CRUD | Extended with optional structured issue tags. |
| `ProgramService` | `backend/app/services/program_service.py` | Active program lifecycle management | Consulted for user program status and constraints. |

---

## 4. Exact Scope and Non-Goals

### In-Scope for Phase 9C.6 Assessment & Planning
1. **Form Issue Normalization Design**: A deterministic contract mapping raw visual heuristic results (`form_heuristics.py`) to canonical, normalized technique issue IDs (`corrective_mappings.py`).
2. **Multi-Level Evidence Qualification Model**: A statistical evidence qualification specification spanning repetition-level, session-level, and multi-session historical analysis.
3. **Read-Only Corrective Guidance Service Design**: Specification of deterministic retrieval of ranked corrective exercises from the 100-exercise catalog, honoring user equipment, environment, and fitness level.
4. **Authenticated REST Endpoint Specifications**: Read-only APIs exposing aggregated form evidence, detected issue history, and qualified corrective suggestions.
5. **Lightweight Session Schema Extension Design**: An optional `normalized_issues` field added to `FormAnalysisSessionDetailSchema` to record structured issue provenance upon session finalization.
6. **Frontend Technique Guidance Presentation Design**: Accessible, responsive presentation on the Form Analysis results page, Session Detail modal, and Exercise Detail page.
7. **Future-Workout Corrective Proposal Boundary (Strategy B)**: Clear architectural specification of how persistent technique patterns can formulate an advisory proposal for Slot 0 (`warmup_corrective`) in a future workout without modifying active sessions.

### Explicit Non-Goals
* **No Direct Program Mutation**: Form analysis will not write to or alter active program documents.
* **No Automatic Exercise Substitution (Strategy D Rejected)**: Exercises in active workouts will not be replaced automatically.
* **No Live WebSocket Overhead**: Corrective guidance logic will not execute inside the 25 FPS frame stream loop.
* **No Video Upload Processing**: Processing pre-recorded user videos remains out of scope.
* **No New CV Models**: No pose heuristics beyond the 5 canonical exercises.
* **No Catalog Expansion (Phase 9D Deferred)**: Exercise catalog remains bounded at exactly 100 exercises.
* **No AI Video Generation (Phase 9E Deferred)**: No AI demonstration video synthesis.
* **No Autonomous Gemini Adaptation**: Gemini will not make prescription or adaptation decisions.
* **No Medical Claims**: No injury diagnosis, clinical advice, or pathology inference.
* **No Immediate Code Implementation**: No production files or endpoints are modified during Phase 9C.6.

---

## 5. Form Evidence Data Flow

The evidence aggregation architecture operates across four distinct temporal stages, structurally separating high-frequency camera processing from advisory guidance.

```
+---------------------------------------------------------------------------------------+
| STAGE 1: REAL-TIME FRAME STREAM (<= 25 FPS, <= 40 ms/frame target)                    |
| MediaPipe Landmarks -> Geometry Angles -> FSM Rep Tracker -> Visual Heuristics Engine |
+---------------------------------------------------------------------------------------+
                                           | (Rep Completed Event)
                                           v
+---------------------------------------------------------------------------------------+
| STAGE 2: REPETITION-LEVEL NORMALIZATION (Executed at Rep Completion)                  |
| RepetitionScore -> FormIssueNormalizer -> List[NormalizedFormIssue]                   |
| Status: OBSERVED (conf >= 0.50), is_acceptable == False -> Canonical issue_id        |
+---------------------------------------------------------------------------------------+
                                           | (Session Finalized)
                                           v
+---------------------------------------------------------------------------------------+
| STAGE 3: SESSION-LEVEL AGGREGATION (Executed at Session Finalization)                 |
| Gating: Total Valid Reps >= 3                                                        |
| Issue Rate = Defect Count / Valid Reps where Heuristic was OBSERVED                   |
| Persisted to Firestore: users/{uid}/form_analysis_sessions/{session_id}               |
+---------------------------------------------------------------------------------------+
                                           | (On-Demand / REST Request)
                                           v
+---------------------------------------------------------------------------------------+
| STAGE 4: MULTI-SESSION HISTORICAL AGGREGATION & GUIDANCE                              |
| Lookback: Last 5 Eligible Sessions (valid_reps >= 3)                                  |
| Recurrence Ratio = Eligible Sessions with Issue / Total Eligible Sessions            |
| Pattern Qualification: REPEATED_PATTERN (>= 2 sessions, >= 50% recurrence)            |
| -> ExerciseRecommendationService(intent=CORRECTIVE) -> Ranked Guidance Candidates   |
+---------------------------------------------------------------------------------------+
```

### Confidence Threshold Disambiguation
To eliminate ambiguity between existing computer vision rules and proposed evidence rules, the following terminology is strictly enforced:

| Threshold Scope | Threshold Value | Authority / Origin | Architectural Role |
| :--- | :---: | :--- | :--- |
| **Frame Detection Confidence** | $\ge 0.50$ | Existing MediaPipe config (`pose_estimator.py`) | Discards unconfident keypoints at the frame level. |
| **Joint Occlusion Threshold** | $\ge 0.50$ | Existing Geometry rule (`geometry_utils.py`) | Marks joint angle `is_occluded = True` if $< 0.50$. |
| **Heuristic Observability** | $\ge 0.50$ | Existing Heuristics rule (`form_heuristics.py`) | Sets status to `OBSERVED`. Missing data $\ne$ bad form. |
| **Rep Observability Gating** | $\ge 70\%$ | Existing Scoring rule (`form_scoring.py`) | Requires 70% of heuristics `OBSERVED` to score a rep. |
| **Rep Confidence Penalty Floor** | $0.60$ | Existing Scoring rule (`form_scoring.py`) | Dampens score penalties for lower-confidence reps. |
| **Session Evidence Qualification** | $\ge 3$ valid reps | **Proposed Architecture (New)** | Filters out brief camera tests before analyzing patterns. |
| **Session Tracking Quality** | Mean conf $\ge 0.50$ | **Proposed Architecture (New)** | Reuses baseline joint confidence across observed reps. |
| **Multi-Session Recurrence** | $\ge 2$ sessions | **Proposed Architecture (New)** | Minimum distinct sessions showing issue at $\ge 50\%$ rate. |

---

## 6. Issue Normalization Design

### 6.1 Flexible, Type-Safe Contract
Visual heuristics in `form_heuristics.py` produce fundamentally different measurement types. The `NormalizedFormIssueSchema` does not force a universal unit (such as `degrees`) onto non-angular measurements.

The contract supports typed, optional measurements tailored to each heuristic's real output:
* **Angular Deficit**: Used by `squat_depth`, `bench_elbow_rom`, `deadlift_hip_lockout`, `curl_elbow_rom`, `shoulder_press_lockout` (Unit: `degrees`).
* **Alignment Ratio**: Used by `squat_knee_tracking` (Unit: `ratio`, knee-width to ankle-width).
* **Centroid Drift**: Used by `deadlift_body_center_stability` (Unit: `normalized_offset`, X/Z bounding box displacement).
* **Bilateral Symmetry Delta**: Used by knee, hip, and elbow symmetry heuristics (Unit: `percent_difference`, bilateral variation).
* **Stability Variance**: Used by movement stability heuristics (Unit: `variance`, acceleration coefficient of variation).

### 6.2 Proposed Schema Definitions

```python
from typing import Optional, List, Dict, Any, Union, Literal
from pydantic import BaseModel, Field, field_validator
from backend.app.schemas.form_analysis import ObservabilityStatus, HeuristicCategory
from backend.app.schemas.exercise import CANONICAL_CV_EXERCISES, PROHIBITED_MEDICAL_PHRASES
from backend.app.seeds.corrective_mappings import (
    HEURISTIC_NAME_TO_ISSUE_ID,
    RAW_CORRECTIVE_MAPPINGS,
)

# Canonical Issue IDs extracted deterministically from seed mappings
VALID_ISSUE_IDS = set(m["issue_id"] for m in RAW_CORRECTIVE_MAPPINGS)


class FormMeasurementData(BaseModel):
    """Polymorphic measurement payload supporting diverse heuristic dimensions."""
    unit: Literal["degrees", "ratio", "normalized_offset", "percent_difference", "variance", "unitless"]
    observed_value: Optional[float] = None
    reference_value: Optional[Union[float, List[float]]] = None
    deviation: Optional[float] = None


class NormalizedFormIssue(BaseModel):
    """Authoritative normalized form issue record."""
    issue_id: str
    source_heuristic: str
    exercise_id: str
    category: HeuristicCategory
    status: ObservabilityStatus
    is_acceptable: Optional[bool] = None
    confidence: float = Field(..., ge=0.0, le=1.0)
    measurement: Optional[FormMeasurementData] = None
    rep_index: Optional[int] = None
    movement_phase: Optional[str] = None
    feedback: str
    validation_metadata: Dict[str, Any] = Field(default_factory=dict)

    @field_validator("issue_id")
    @classmethod
    def validate_issue_id(cls, v: str) -> str:
        if v not in VALID_ISSUE_IDS:
            raise ValueError(f"Unknown canonical issue_id '{v}'. Must be one of {sorted(VALID_ISSUE_IDS)}")
        return v

    @field_validator("exercise_id")
    @classmethod
    def validate_exercise_id(cls, v: str) -> str:
        if v not in CANONICAL_CV_EXERCISES:
            raise ValueError(f"Exercise '{v}' is not a canonical CV exercise.")
        return v

    @field_validator("source_heuristic")
    @classmethod
    def validate_heuristic_mapping(cls, v: str, info) -> str:
        exercise_id = info.data.get("exercise_id")
        issue_id = info.data.get("issue_id")
        if exercise_id and issue_id:
            expected_issue = HEURISTIC_NAME_TO_ISSUE_ID.get((exercise_id, v))
            if expected_issue is None:
                raise ValueError(f"Heuristic '{v}' is not valid for exercise '{exercise_id}'.")
            if expected_issue != issue_id:
                raise ValueError(
                    f"Heuristic '{v}' maps to issue '{expected_issue}', not '{issue_id}'."
                )
        return v

    @field_validator("feedback")
    @classmethod
    def validate_non_medical_language(cls, v: str) -> str:
        lower_fb = v.lower()
        for phrase in PROHIBITED_MEDICAL_PHRASES:
            if phrase in lower_fb:
                raise ValueError(f"Feedback contains prohibited medical phrase: '{phrase}'")
        return v
```

---

## 7. Corrective Guidance Design

### 7.1 Multi-Level Evidence Qualification Model
To prevent camera jitter or a single bad repetition from triggering corrective exercise interventions, evidence is evaluated hierarchically.

#### Denominator Definitions
* **Repetition Observability Ratio**:
  $$\text{ObsRatio}_{\text{rep}} = \frac{\text{Count of heuristics with status } == \text{OBSERVED}}{\text{Total required heuristics for this canonical exercise}}$$
  *Scoring requires $\text{ObsRatio}_{\text{rep}} \ge 0.70$.*
* **Session-Level Defect Rate**:
  For an issue $I$ originating from heuristic $H$ in session $S$:
  $$\text{DefectRate}_{\text{session}}(I) = \frac{\sum_{r \in \text{ValidReps}} \mathbb{I}(H_r.\text{status} == \text{OBSERVED} \land H_r.\text{is\_acceptable} == \text{False})}{\sum_{r \in \text{ValidReps}} \mathbb{I}(H_r.\text{status} == \text{OBSERVED})}$$
  *The denominator is strictly the count of valid repetitions where heuristic $H$ was observed. Unobserved reps do NOT penalize the user.*
* **Multi-Session Recurrence Ratio**:
  Across the last $K$ sessions for exercise $E$ (lookback $K = 5$):
  $$\text{EligibleSessions} = \{S \in \text{History}(E) \mid S.\text{valid\_reps} \ge 3 \land S.\text{status} == \text{"completed"}\}$$
  $$\text{RecurrenceRatio}(I) = \frac{\text{Count of Eligible Sessions where } \text{DefectRate}_{\text{session}}(I) \ge 0.50}{|\text{EligibleSessions}|}$$

#### Explicit Qualification Criteria Across the 5 Evidence Levels
1. **`NO_EVIDENCE`**:
   * *Evidence Criterion*: Zero qualifying technique defects detected across all evaluated repetitions in the lookback window.
   * *Authoritative Status Description*: "No qualifying technique issue was identified from the available evidence. Continue regular training. This result does not establish that all technique characteristics were observed or validated."
   * *Prescription Eligibility*: **Disqualified**. No corrective drill recommendations are generated.
2. **`INSUFFICIENT_DATA`**:
   * *Evidence Criterion*: Fewer than 3 valid repetitions exist in the session, or the specific heuristic was observed in fewer than 3 valid repetitions.
   * *Authoritative Status Description*: "Insufficient repetition or camera observability data to evaluate technique patterns. Complete at least 3 clean repetitions with clear camera visibility."
   * *Prescription Eligibility*: **Disqualified**. No corrective drill recommendations are generated.
3. **`EMERGING_OCCURRENCE`**:
   * *Evidence Criterion*: Technique defect detected at $\ge 50\%$ rate within a single session, but has not recurred across $\ge 2$ distinct eligible sessions in the lookback window.
   * *Authoritative Status Description*: "Isolated technique deviation observed in latest session. Focus on movement cues during standard sets before adding corrective drills."
   * *Prescription Eligibility*: **Disqualified**. Generates a non-prescriptive observation cue for user awareness only; no corrective exercise recommendations.
4. **`REPEATED_PATTERN`**:
   * *Evidence Criteria*:
     * Technique defect detected at $\ge 50\%$ rate across $\ge 2$ distinct eligible sessions within the lookback window ($K = 5$).
     * Each eligible session contains $\ge 3$ valid repetitions with overall session observability $\ge 70\%$.
   * *Role & Permitted Actions*:
     * **Qualified strictly for read-only educational guidance**.
     * Enables displaying technique focus cues and ranked catalog-backed preparation drills on the Form Analysis summary screen and Exercise Detail page.
     * **Does NOT formulate a future-workout proposal**.
5. **`ACTIONABLE_PATTERN`**:
   * *Additional Evidence & Validation Criteria (Distinguished from REPEATED_PATTERN)*:
     * **Higher Session Recurrence**: Defect detected at $\ge 50\%$ rate across at least $\ge 3$ distinct eligible sessions within the lookback window ($K = 5$).
     * **Elevated Tracking Confidence**: Mean heuristic confidence $\ge 0.60$ across observed repetitions in each qualifying session, confirming stable landmark detection and absence of keypoint jitter.
     * **Full Observability**: Each qualifying session must maintain $\ge 70\%$ overall heuristic observability with zero camera occlusion or framing warnings.
     * **Safety & Constraint Gate**: Confirmed availability of suitable catalog drills matching user equipment (`candidate.equipment ⊆ user.available_equipment`), target environment, and zero user exercise exclusions.
   * *Strict Proposal-Only Boundary*:
     * Enables **eligibility only** for formulating an advisory future-workout Slot 0 proposal (`ProposedCorrectiveSlot`), presented to the user during mesocycle planning or re-generation.
     * It requires passing safety validation and receiving **EXPLICIT USER CONSENT**.
     * **Inviolable Invariant**: An `ACTIONABLE_PATTERN` must **NEVER** directly modify an active workout in progress, never modify the immutable original `planSnapshot`, and never silently alter `effectivePlanSnapshot`.

#### Summary of API Response Behavior by Evidence Level

| Evidence Level | Qualification Status | Corrective Candidates | API Response Status | User Guidance Message |
| :--- | :---: | :---: | :---: | :--- |
| `NO_EVIDENCE` | **Disqualified** | `[]` (Empty) | HTTP 200 (`status = "NO_EVIDENCE"`) | "No qualifying technique issue was identified from the available evidence. Continue regular training. This result does not establish that all technique characteristics were observed or validated." |
| `INSUFFICIENT_DATA` | **Disqualified** | `[]` (Empty) | HTTP 200 (`status = "INSUFFICIENT_DATA"`) | "Insufficient repetition or camera observability data to evaluate technique patterns. Complete at least 3 clean repetitions with clear camera visibility." |
| `EMERGING_OCCURRENCE` | **Disqualified** | `[]` (Empty) | HTTP 200 (`status = "EMERGING_OCCURRENCE"`) | "Isolated technique deviation observed in latest session. Focus on movement cues during standard sets before adding corrective drills." |
| `REPEATED_PATTERN` | **Qualified (Educational)** | Ranked Candidates | HTTP 200 (`status = "REPEATED_PATTERN"`) | Display catalog-backed corrective drill recommendations with educational technique cues. |
| `ACTIONABLE_PATTERN` | **Qualified (Advisory Proposal)** | Ranked Candidates | HTTP 200 (`status = "ACTIONABLE_PATTERN"`) | Display corrective recommendations; indicate eligibility for advisory future-workout Slot 0 proposal (subject to explicit user confirmation). |

*Note: All five states return an HTTP 200 status code with a structured response body. The absence of qualifying evidence is a normal operational domain state, not an exceptional API error.*

### 7.2 Catalog-Backed Corrective Recommendation Pipeline
When an issue qualifies as `REPEATED_PATTERN` or `ACTIONABLE_PATTERN`, candidates are retrieved deterministically:
1. **Edge Retrieval**: `ExerciseRelationshipService.get_corrective_exercises(source_exercise_id, issue_id)` retrieves authoritative catalog candidates from `RAW_CORRECTIVE_MAPPINGS`.
2. **Hard Constraint Filtering**: Candidates are strictly filtered against user constraints:
   * Available equipment: `candidate.equipment ⊆ user.available_equipment`.
   * Target environment: Home vs Gym compatibility.
   * User exclusions: `candidate.exercise_id ∉ user.excluded_exercise_ids`.
3. **Deterministic Scoring**: Soft score computed via `CORRECTIVE_SCORING_WEIGHTS`:
   * Mapping match priority: $0.50$ (Priority 1 vs 2 from seed mappings).
   * Movement pattern alignment: $0.25$.
   * Difficulty level match: $0.15$.
   * Target muscle synergy: $0.10$.
4. **Tie-Breaking**: Score DESC $\rightarrow$ Mapping Priority ASC $\rightarrow$ Compound before Isolation $\rightarrow$ Exercise ID ASC.

---

## 8. API Proposal

All proposed endpoints are **authenticated, user-scoped, and read-only**. They do not write to or mutate active programs or workout sessions.

### 8.1 Summary of Endpoints

| Method | Endpoint Path | Description | Mutation | Idempotency Key Required |
| :--- | :--- | :--- | :---: | :---: |
| `GET` | `/api/v1/form-analysis/evidence/{exercise_id}` | Aggregated multi-session evidence & trends | None (Read-only) | No |
| `GET` | `/api/v1/form-analysis/sessions/{session_id}/issues` | Normalized issues for a finalized session | None (Read-only) | No |
| `GET` | `/api/v1/form-analysis/correctives/{exercise_id}` | Ranked corrective drill recommendations | None (Read-only) | No |

### 8.2 Detailed Endpoint Specifications

#### 1. Multi-Session Evidence Endpoint
* **Path**: `GET /api/v1/form-analysis/evidence/{exercise_id}`
* **Auth**: Bearer token (`uid` injected via `get_current_user`).
* **Path Parameter**: `exercise_id: str` (Must be one of the 5 canonical CV exercises).
* **Query Parameters**: `lookback_sessions: int = 5` (Min 1, Max 20).
* **Response Schema**:
  ```python
  class IssueTrendItem(BaseModel):
      issue_id: str
      evidence_level: Literal[
          "NO_EVIDENCE", "INSUFFICIENT_DATA", "EMERGING_OCCURRENCE",
          "REPEATED_PATTERN", "ACTIONABLE_PATTERN"
      ]
      eligible_sessions_analyzed: int
      sessions_with_issue: int
      recurrence_ratio: float
      latest_session_defect_rate: Optional[float] = None
      representative_cue: str

  class MultiSessionEvidenceResponse(BaseModel):
      exercise_id: str
      canonical_name: str
      lookback_sessions: int
      eligible_sessions_found: int
      trends: List[IssueTrendItem]
      evaluated_at: str
  ```
* **Validation & Errors**:
  * `400 Bad Request`: `exercise_id` is not a canonical CV exercise.
  * `401 Unauthorized`: Missing or invalid Firebase auth token.
  * `404 Not Found`: No completed session history found for user and exercise.

#### 2. Session Normalized Issues Endpoint
* **Path**: `GET /api/v1/form-analysis/sessions/{session_id}/issues`
* **Auth**: Bearer token (`uid` injected).
* **Cross-User Security**: Verifies `session.user_id == current_user.uid`. Returns `404 Not Found` if session belongs to another user (prevents enumeration).
* **Response Schema**:
  ```python
  class SessionIssuesResponse(BaseModel):
      session_id: str
      exercise_id: str
      total_reps: int
      valid_reps: int
      issues_detected: List[NormalizedFormIssue]
      defect_rates_by_issue: Dict[str, float]
  ```

#### 3. Ranked Corrective Guidance Endpoint
* **Path**: `GET /api/v1/form-analysis/correctives/{exercise_id}`
* **Auth**: Bearer token.
* **Query Parameters**:
  * `issue_id: Optional[str] = None` (If omitted, evaluates the top recurring issue).
  * `limit: int = 3` (Min 1, Max 10).
* **Behavior**:
  * Resolves user profile from Firestore (`available_equipment`, `fitness_level`, `environment`).
  * Enforces the 5 evidence qualification levels:
    * If `NO_EVIDENCE`: returns `status = "NO_EVIDENCE"`, `candidates = []`, and message: `"No qualifying technique issue was identified from the available evidence. Continue regular training. This result does not establish that all technique characteristics were observed or validated."`
    * If `INSUFFICIENT_DATA`: returns `status = "INSUFFICIENT_DATA"`, `candidates = []`, and message: `"Insufficient repetition or camera observability data to evaluate technique patterns. Complete at least 3 clean repetitions with clear camera visibility."`
    * If `EMERGING_OCCURRENCE`: returns `status = "EMERGING_OCCURRENCE"`, `candidates = []`, and non-prescriptive observation cue.
    * If `REPEATED_PATTERN`: retrieves and ranks candidate exercises for educational display.
    * If `ACTIONABLE_PATTERN`: retrieves and ranks candidate exercises; indicates advisory proposal eligibility.
* **Response Schema**:
  ```python
  class CorrectiveRecommendationItem(BaseModel):
      exercise_id: str
      name: str
      difficulty: str
      equipment: List[str]
      primary_muscles: List[str]
      score: float
      reasons: List[str]
      educational_cue: str

  class CorrectiveGuidanceResponse(BaseModel):
      source_exercise_id: str
      target_issue_id: Optional[str] = None
      evidence_level: str
      status_message: str
      candidates: List[CorrectiveRecommendationItem] = []
      disclaimer: str = (
          "These exercise suggestions are general movement drills to assist with technique practice. "
          "They are not medical treatments or rehabilitation prescriptions."
      )
  ```

### 8.3 API Idempotency & Mutation Guarantees
* **Read-Only Endpoints**: All three proposed endpoints (`/evidence/{exercise_id}`, `/sessions/{session_id}/issues`, `/correctives/{exercise_id}`) are pure HTTP `GET` requests. They do not write to Firestore or modify application state. Repeated requests are observationally equivalent and safe without requiring an idempotency key.
* **Future Mutating Endpoints**: Any future endpoint introduced to apply a proposal (such as an endpoint to confirm a Slot 0 corrective drill during workout generation) will require a formal idempotency specification prior to implementation. That specification must include:
  * An `Idempotency-Key` HTTP header.
  * Request fingerprinting based on user ID, target workout ID, slot index, and exercise ID.
  * Deterministic conflict handling (HTTP 409) if concurrent mutations are attempted on the same plan target.
  * Replay caching to ensure duplicate requests return identical responses without duplicate mutations.
* **Current State**: Idempotency mechanisms for mutating endpoints are intentionally not implemented in this phase because no mutating endpoints are in scope.

---

## 9. Persistence Assessment

### 9.1 Evaluation of Storage Alternatives
* **Alternative 1: Dedicated New Collection (`form_issue_evidence`)**:
  * *Assessment*: Creates duplicate storage, requires distributed transaction management, and introduces synchronization overhead with `form_analysis_sessions`.
* **Alternative 2: Dynamic On-Demand Calculation from Existing Sessions**:
  * *Assessment*: Requires zero database schema changes, but current `CompactRepSummarySchema` lacks structured `issue_id` tags, requiring text parsing of `feedback` strings.
* **Alternative 3: Lightweight Backward-Compatible Extension (Recommended)**:
  * Extend `FormAnalysisSessionDetailSchema` with an optional field:
    `normalized_issues: Optional[List[NormalizedFormIssue]] = []`.
  * Add a compact summary to `CompactRepSummarySchema`:
    `issue_ids: List[str] = []`.
  * Legacy records are processed via explicit fallback rules.

### 9.2 Legacy Session Fallback Safety Rules
To prevent corrupting multi-session trends with unreliable historical data:
1. **Never Infer Canonical Issue IDs from Vague Text**: The system must never attempt natural-language parsing, regex guessing, or keyword matching on free-form summary feedback strings (e.g. `"Good repetition execution with minor technique adjustments observed."`).
2. **Reliable Provenance Gate**: A legacy session may be included in multi-session evidence aggregation **only if structured issue tags (`issue_ids`) or explicit heuristic evaluation keys (`heuristic_name` with `status == "OBSERVED"`) exist**.
3. **Fallback Classification**: If a legacy session lacks structured issue tags or verified heuristic keys, it must be classified as **`INSUFFICIENT_HISTORICAL_EVIDENCE`**.
4. **Denominator Exclusion**: Sessions classified as `INSUFFICIENT_HISTORICAL_EVIDENCE` are excluded from both the numerator and denominator of multi-session recurrence calculations. They do not count against the user's technique record.

### 9.3 Persistence Contract Specification
* **Collection Path**: `users/{uid}/form_analysis_sessions/{session_id}` (Existing collection).
* **Authoritative Source**: Form analysis session documents are authoritative for technique records.
* **Derived Data**: Multi-session trends and recurrence ratios are **derived on-the-fly** across the last $K$ session documents. They are not stored in separate documents, eliminating cache invalidation complexity.
* **Payload Footprint**: Adding `issue_ids: List[str]` adds estimated $<120$ bytes per repetition. A 10-rep session increases document size by estimated $<1.2\text{ KB}$, well within Firestore's 1 MB document limit.
* **Landmark / Video Exclusion Invariant**: Raw video files, base64 images, and high-frequency continuous 33-landmark streams are **never persisted** to Firestore. Only finalized repetition summaries and normalized issue tags are stored.

---

## 10. Program Integration Strategy Comparison

A neutral, factual evaluation of four potential integration strategies was conducted:

| Evaluation Dimension | Strategy A: Guidance Only | Strategy B: Future-Workout Proposal | Strategy C: Server Adaptation | Strategy D: Auto Substitution |
| :--- | :--- | :--- | :--- | :--- |
| **Description** | Display educational cues & drills on form analysis & exercise detail pages. | Propose adding corrective drill to Slot 0 of next week's workout; user confirms. | Form defects trigger automated adaptation engine rule; updates `effectivePlanSnapshot`. | Form defects automatically replace active compound exercises with regressions. |
| **Technical Complexity** | Low. Read-only services and UI cards. Zero program mutation. | Moderate. Proposal schema, user approval UI, Slot 0 allocation. | High. Extends adaptation rule matrix; requires multi-week validation. | Extreme. Modifies in-flight workouts; breaks mesocycle progression logic. |
| **Safety & Medical Risk** | Lower expected risk due to non-prescriptive educational scope. | Low. Confined to optional warmup drill. User maintains control. | Moderate. Modifies training volume/load automatically. | **High Risk**. Monocular CV optical noise could alter core training unprompted. |
| **User Agency** | Complete. User decides whether to practice suggested drills. | High. User explicitly reviews and authorizes the proposal. | Low. System adapts prescriptions with minimal user input. | **None**. System overrides user program without consent. |
| **Explainability** | High. Cites exact heuristic and session evidence. | High. Shows recurrence history and explains Slot 0 drill. | Moderate. Complex multi-signal interactions. | Low. Sudden exercise swap confuses user. |
| **Architectural Fit** | Proposed fit under read-only boundaries; reuses recommendation engine. | Suitable under stated slot constraints; aligns with `WARMUP_CORRECTIVE` Slot 0. | Moderate. Adaptation engine currently focuses on RPE/load/volume. | **Violates Invariants**. Mutates active workout session. |
| **Reversibility** | Immediate. Read-only display. | Straightforward. User declines proposal or removes Slot 0 drill. | Moderate. Requires adaptation rollback. | Difficult. Disrupts logged history and progression baselines. |
| **Implementation Scope** | **Architecture design in scope for Phase 9C.6 (Subphases 9C.6.1–9C.6.5); implementation requires separate explicit approval.** | **Architecture design in scope for Phase 9C.6 (Subphase 9C.6.6); implementation and plan modification require separate explicit approval.** | **Deferred to Phase 9C.7.** | **Explicitly rejected.** |

### Strategy Trade-Off Analysis
* **Strategy A (Guidance Only)** introduces lower expected coupling and risks no mesocycle disruption. It provides educational value immediately post-session.
* **Strategy B (Future-Workout Proposal)** fits the existing `WARMUP_CORRECTIVE` Slot 0 template architecture without silent mutation. It preserves user agency by requiring explicit user confirmation before modifying a future prescription.
* **Strategy D (Automatic Substitution)** is **strictly rejected**. Computer vision observations from a single smartphone camera carry inherent noise; automatically replacing a user's planned compound exercise disrupts mesocycle periodization and degrades user trust.

---

## 11. Frontend UX Proposal

The frontend integration is designed to be minimal, educational, and responsive.

### 11.1 Component Integration Touchpoints

```
[Form Analysis Session Summary Page]
       |
       +--> <FormTechniqueGuidanceCard />
               |-- Recurrence badge: "Observed in 2 consecutive sessions"
               |-- Plain technique cue: "Knees tracking inward during ascent"
               |-- Educational drill: "Goblet Squat (2 sets x 10 reps)"
               +-- Action: "View Technique Tips" -> Opens Exercise Detail Modal

[Session Detail Modal (History View)]
       |
       +--> Normalized Issue Badges on Repetition Breakdown
               |-- Rep 1: [Valid] [Depth: 94 deg]
               |-- Rep 2: [Deviation] [Knee Tracking Deviation]
               +-- Rep 3: [Valid]

[Exercise Detail Page]
       |
       +--> "Technique & Correctives" Tab (Canonical Exercises Only)
               |-- Shows user's historical technique consistency
               +-- Recommended preparation drills for this exercise
```

### 11.2 Presentation Guidelines & UX Invariants
* **Non-Medical Framing**: UI text uses terms like "Movement Tip", "Technique Focus", and "Preparation Drill". Terms like "Injury Risk", "Deficit", "Dysfunction", or "Pathology" are strictly forbidden.
* **Insufficient-Data State**: When $<3$ valid reps exist or camera confidence was low, the UI displays:
  *"Keep practicing! Complete at least 3 clean reps with a clear camera view to unlock personalized technique guidance."*
* **Zero Disruption to Workout Execution**: Technique guidance cards are displayed on summary and review screens. They never pop up modally during an active timed workout set.

---

## 12. Safety and Non-Medical Boundaries

To protect user safety and ensure regulatory compliance as a general fitness product:

### 12.1 Explicit Guardrails
1. **No Injury Diagnosis or Treatment**: The platform does not diagnose patellofemoral pain, lumbar disc herniation, impingement, or any other medical condition.
2. **No Causality Claims**: The platform never claims that an observed movement pattern will cause injury or that performing a recommended drill will prevent or cure pain.
3. **No Biomechanical Force Calculations**: The platform does not calculate internal joint forces, shear stresses, or spinal compressive loads from 2D landmarks.
4. **Pain-Related User Input**: If a user enters notes mentioning pain, discomfort, or injury, the system displays a standard safety advisory recommending consultation with a qualified medical professional.
5. **Camera Occlusion Safety**: If landmarks are occluded, the system reports `NOT_OBSERVABLE` and advises the user to adjust camera position. It never guesses technique quality from incomplete data.
6. **No Equipment Override**: The system never recommends an exercise requiring equipment the user does not possess.

### 12.2 Standard Educational Disclaimer
Every corrective guidance card and API response includes the mandatory disclaimer:
> *"Technique cues and preparation drills are general educational suggestions for movement practice. They do not constitute medical advice, diagnosis, or physical therapy."*

---

## 13. Performance and Reliability

### 13.1 Decoupling from Live Streaming Loop
* The live WebSocket frame loop processes incoming frames at up to the configured limit of 25 FPS (40 ms target frame interval).
* **Architectural Decoupling vs. Measured Runtime**: The proposed architecture structurally decouples corrective analysis from the live streaming loop: no recommendation ranking, no multi-session Firestore lookups, and no LLM calls execute inside the live frame processing pipeline. However, architectural decoupling must be distinguished from measured runtime performance. Actual CPU/memory overhead and thread contention must be empirically measured during a dedicated benchmarking phase once implementation code exists.
* **Performance Rule**: Corrective guidance queries, multi-session lookups, and catalog recommendations **never run on the WebSocket frame thread**. Normalization occurs only at repetition completion, and evidence aggregation runs asynchronously upon session completion or via REST.

### 13.2 Proposed Design Budgets (Unbenchmarked Engineering Targets)
*No executed production benchmarks for individual pipeline stages (pose estimation, joint kinematics, FSM transitions, and visual heuristics) currently exist in the repository. The following figures represent proposed design budgets and engineering targets, not measured runtime facts:*

| Processing Layer | Proposed Target (Design Budget) | Operational Context |
| :--- | :---: | :--- |
| **In-Memory Issue Normalizer** | $<5\text{ ms}$ per rep (Target) | Synchronous on rep completion event. |
| **Session Evidence Aggregator** | $<15\text{ ms}$ for 10 reps (Target) | Executed during session finalization. |
| **Read-Only Evidence Endpoint** | $<150\text{ ms}$ p95 (Target) | REST API fetching 5 Firestore session summaries. |
| **Corrective Recommendation Endpoint** | $<100\text{ ms}$ p95 (Target) | REST API querying in-memory relationship graph. |
| **Live Streaming Overhead** | Structurally decoupled (Target) | Excluded from frame loop; empirical overhead subject to future benchmarks. |

> [!IMPORTANT]
> **Provisional Engineering Targets Clarification**:
> All performance figures in this section—including $<150\text{ ms}$ p95, $<100\text{ ms}$ p95, $<5\text{ ms}$ per rep, and $<15\text{ ms}$ per session—are **provisional unbenchmarked engineering targets**, not measured results or guaranteed acceptance outcomes. They serve strictly as design goals to guide future implementation. Actual end-to-end latencies, database query times, and streaming overhead must be empirically validated through executed benchmarks in a dedicated verification phase prior to any production release.

---

## 14. Security and Cross-User Isolation

1. **Authentication Enforcement**: All proposed API endpoints require a valid Firebase Authentication JWT passed in the `Authorization: Bearer <token>` header.
2. **Cross-User Data Isolation**:
   * Sessions are stored under `users/{uid}/form_analysis_sessions/{session_id}`.
   * Endpoints explicitly verify that the authenticated `uid` matches the `user_id` of the requested session.
   * Attempts to query another user's session ID return `404 Not Found` (rather than `403 Forbidden`) to prevent resource enumeration attacks.
3. **Input Sanitization**: Path and query parameters (`exercise_id`, `issue_id`, `lookback_sessions`) are strictly validated against allowlists and bounded ranges before processing.
4. **Data Privacy**: No video frames or continuous landmark coordinates are stored in the database, protecting user visual privacy.

---

## 15. Testing Strategy

Implementation of Phase 9C.6 will adhere to a comprehensive test harness across four distinct test categories:

### 15.1 Unit Testing (`pytest tests/unit`)
* **Normalizer Tests**: Verify all 25 visual heuristics map correctly to their canonical issue IDs. Test rejection of unknown heuristics, unknown exercise IDs, and mismatched mappings.
* **Non-Medical Language Enforcement**: Verify that Pydantic validators reject strings containing any of the phrases in `PROHIBITED_MEDICAL_PHRASES`.
* **Evidence Level Evaluator**: Test edge cases for evidence qualification:
  * 0 valid reps $\rightarrow$ `INSUFFICIENT_DATA`.
  * 2 valid reps $\rightarrow$ `INSUFFICIENT_DATA`.
  * 5 reps with 0 qualifying defects detected $\rightarrow$ `NO_EVIDENCE` (evaluates expected diagnostic message: "No qualifying technique issue was identified from the available evidence. Continue regular training. This result does not establish that all technique characteristics were observed or validated.").
  * 5 reps with 3 defects in 1 session $\rightarrow$ `EMERGING_OCCURRENCE`.
  * 5 reps with 3 defects across 2 sessions $\rightarrow$ `REPEATED_PATTERN`.
  * 5 reps with 3 defects across 3 sessions with high confidence $\rightarrow$ `ACTIONABLE_PATTERN`.
* **Corrective Retrieval & Scoring**: Test that `ExerciseRecommendationService` filters candidates by equipment, respects exclusions, and breaks ties deterministically.

### 15.2 Integration Testing (`pytest tests/integration`)
* **API Route Tests**: Test authenticated endpoints with mock user tokens and valid/invalid exercise IDs.
* **Cross-User Security Tests**: Test that User A cannot read User B's session issues or historical trends.
* **End-to-End Serialization**: Test that `NormalizedFormIssue` and `SessionIssuesResponse` serialize and deserialize cleanly across Pydantic v2.

### 15.3 Negative & Edge Case Testing
* Camera occluded for entire session $\rightarrow$ returns clean insufficient data state without division-by-zero errors.
* User has no available equipment matching corrective candidates $\rightarrow$ returns empty candidate list with diagnostic `missing_equipment` reason, without crashing.
* Session with valid reps but zero observed heuristics for a specific issue $\rightarrow$ denominator is 0; defect rate is correctly reported as `None` rather than `0.0`.
* Legacy session with unprovenanced feedback $\rightarrow$ correctly classified as `INSUFFICIENT_HISTORICAL_EVIDENCE` and excluded from recurrence ratios.

### 15.4 Regression Testing
* Full backend suite execution (`pytest tests/`) to ensure all 843 existing tests continue to pass.
* Full frontend test suite execution (`npm run test:run`) to ensure all 287 existing tests continue to pass.
* Production build verification (`npm run build`).

---

## 16. Proposed Subphase Breakdown

Execution of Phase 9C.6 is partitioned into 7 sequential, test-gated subphases. **Phase 9C.6 is strictly an architecture assessment and planning milestone. Subphases 9C.6.1 through 9C.6.7 represent proposed sequential implementation subphases; none of these subphases are authorized or implemented within Phase 9C.6. Commencing implementation on any subphase requires separate explicit user approval.**

```
+---------------------------------------------------------------------------------------+
| Proposed Phase 9C.6.1: Form Evidence and Issue Normalization Contracts               |
| - Implement NormalizedFormIssueSchema and FormMeasurementData                         |
| - Implement FormIssueNormalizer service                                              |
| - Full unit test coverage for 25 heuristics and 15 canonical issue IDs               |
+---------------------------------------------------------------------------------------+
                                           |
                                           v
+---------------------------------------------------------------------------------------+
| Proposed Phase 9C.6.2: Persistent Form Evidence Aggregation Engine                    |
| - Implement SessionEvidenceAggregator and MultiSessionEvidenceAggregator             |
| - Add optional normalized_issues to FormAnalysisSessionDetailSchema                   |
| - Unit tests for 5 evidence levels, denominators, and lookback windows                |
+---------------------------------------------------------------------------------------+
                                           |
                                           v
+---------------------------------------------------------------------------------------+
| Proposed Phase 9C.6.3: Corrective Guidance Service                                    |
| - Implement CorrectiveGuidanceService connecting relationship graph and recommendations|
| - Integrate user equipment and environment constraint filtering                       |
| - Unit tests for candidate ranking, scoring weights, and non-medical phrasing         |
+---------------------------------------------------------------------------------------+
                                           |
                                           v
+---------------------------------------------------------------------------------------+
| Proposed Phase 9C.6.4: Corrective Guidance REST API                                   |
| - Implement 3 authenticated read-only endpoints in FastAPI                            |
| - Cross-user authorization and input validation                                       |
| - Integration tests for endpoints, error codes, and responses                         |
+---------------------------------------------------------------------------------------+
                                           |
                                           v
+---------------------------------------------------------------------------------------+
| Proposed Phase 9C.6.5: Frontend Corrective Guidance Presentation                      |
| - Implement FormTechniqueGuidanceCard on Form Analysis and Session Detail modal       |
| - Integrate Technique tab on Exercise Detail page                                     |
| - Component tests and accessibility verification (WCAG 2.1 AA)                       |
+---------------------------------------------------------------------------------------+
                                           |
                                           v
+---------------------------------------------------------------------------------------+
| Proposed Phase 9C.6.6: Future Program Integration Assessment & Slot 0 Proposal Design |
| - Technical design for advisory ProposedCorrectiveSlot model (warmup_corrective)      |
| - UI design for user proposal review during mesocycle planning                        |
| - Verify plan immutability; implementation requires separate explicit authorization   |
+---------------------------------------------------------------------------------------+
                                           |
                                           v
+---------------------------------------------------------------------------------------+
| Proposed Phase 9C.6.7: Comprehensive Verification & Regression                        |
| - Full backend regression (843+ tests)                                                |
| - Full frontend regression (287+ tests)                                               |
| - Clean production build & multi-device responsive QA                                 |
| - Final implementation report & milestone freeze                                      |
+---------------------------------------------------------------------------------------+
```

---

## 17. Dependencies and Risks

| Risk Description | Severity | Concrete Architectural Mitigation |
| :--- | :---: | :--- |
| **Camera Perspective & Occlusion Noise** | High | Multi-level gating: rep requires status `OBSERVED` ($\ge 0.50$ joint conf) and $\ge 70\%$ observability. Session requires $\ge 3$ valid reps. Missing data is never treated as a defect. |
| **False-Positive Technique Interventions** | High | Multi-session qualification: corrective guidance requires recurrence across $\ge 2$ distinct sessions (`REPEATED_PATTERN`). Single-session occurrences produce educational tips only. |
| **Active Mesocycle Plan Corruption** | Critical | Inviolable architectural boundary: form analysis is strictly read-only and proposal-first. Zero direct write access to active program documents or `planSnapshot`. |
| **Equipment Mismatch for Recommended Drills** | Medium | Hard eligibility filter: `candidate.equipment ⊆ user.available_equipment` enforced prior to soft scoring. |
| **Medical Liability & Diagnostic Claims** | Critical | Pydantic validator rejects prohibited phrases. Mandatory non-medical educational disclaimer on all UI cards and API responses. |
| **Live Stream Latency Impact** | High | Complete process isolation: corrective guidance executes asynchronously outside the 25 FPS frame stream. Overhead subject to empirical benchmark verification. |

---

## 18. Decisions Requiring User Approval

The following architectural decisions require explicit user review and confirmation before implementation begins:

1. **Adoption of Strategy A (Guidance Only) for Initial Scope**:
   * *Decision*: Adopt Strategy A across Subphases 9C.6.1–9C.6.5, delivering read-only guidance on form analysis, history, and exercise detail pages.
   * *Recommendation*: **Approve architecture design**. Delivers immediate educational value with zero risk to active workout programs. Implementation will require separate explicit approval.
2. **Scope of Strategy B (Future-Workout Proposal Design for Slot 0)**:
   * *Decision*: In Subphase 9C.6.6, develop the technical design for an advisory proposal for Slot 0 (`warmup_corrective`). Clarify that applying any proposal to an active workout program requires separate, explicit user approval and does not execute automatically.
   * *Recommendation*: **Approve architecture design**. Preserves complete user agency while utilizing existing Slot 0 architecture.
3. **Explicit Rejection of Strategy D (Automatic Substitution)**:
   * *Decision*: Form analysis will never automatically replace planned exercises in active programs.
   * *Recommendation*: **Approve**. Protects user agency and prevents false-positive disruption.
4. **Evidence Threshold Parameters**:
   * *Decision*: Adopt the proposed engineering design choices: require $\ge 3$ valid reps per session, $\ge 50\%$ defect frequency within a session, and recurrence across $\ge 2$ distinct eligible sessions within a 5-session lookback window before declaring a `REPEATED_PATTERN`. Require $\ge 3$ sessions and $\ge 0.60$ confidence for `ACTIONABLE_PATTERN`.
   * *Recommendation*: **Approve as proposed engineering targets**, subject to operational review during testing.
5. **Session Schema Extension & Legacy Fallback**:
   * *Decision*: Extend `FormAnalysisSessionDetailSchema` with an optional `normalized_issues: Optional[List[NormalizedFormIssue]] = []` field, and strictly enforce that legacy sessions without verified heuristic provenance are classified as `INSUFFICIENT_HISTORICAL_EVIDENCE`.
   * *Recommendation*: **Approve**. Avoids new Firestore collections while preventing historical data corruption.
6. **Separation of Architecture Approval from Implementation Authorization**:
   * *Decision*: Authorizing this architecture assessment does not authorize immediate code changes. Subphases 9C.6.1 through 9C.6.7 will each require separate authorization before source files are modified. Furthermore, applying any corrective prescription to an active workout plan requires an additional explicit user consent and safety review.
   * *Recommendation*: **Approve**. Enforces strict phase gating and milestone discipline.

---

## 19. Deferred Features

The following capabilities are intentionally deferred to future development phases:

* **Phase 9C.7 — Automated Adaptive Program Interventions (Strategy C)**: Automated adaptation engine rules responding to chronic movement patterns across multi-week mesocycles.
* **Phase 9D — Exercise Catalog Expansion**: Expanding the exercise catalog beyond the foundational 100 exercises.
* **Phase 9E — AI Demonstration Video Generation**: Generating synthetic demonstration videos or video intelligence overlays.
* **Additional CV Exercise Models**: Developing pose estimation heuristics for exercises beyond the 5 canonical compound movements (e.g. lunges, rows, pull-ups).
* **Pre-Recorded Video Upload Processing**: Asynchronous ingestion and processing of user-uploaded MP4/MOV video files.
* **Autonomous LLM Prescription**: Using Gemini or other LLMs to autonomously alter exercise prescriptions or mesocycle structures.

---

## 20. Implementation Readiness Verdict

### Implementation Readiness Verdict
**`READY FOR FINAL ARCHITECTURE REVIEW — IMPLEMENTATION NOT APPROVED`**

### Audit & Correction Pass Confirmation
The repository implementation audit is complete. All 25 visual heuristics, 15 normalized issue IDs, 100 catalog exercises, and workout slot architectures have been verified on disk. All corrections across all review passes have been thoroughly incorporated:
1. **NO_EVIDENCE Wording Corrected**: Replaced all references to "consistent technique execution" with the authoritative non-prescriptive wording: *"No qualifying technique issue was identified from the available evidence. Continue regular training. This result does not establish that all technique characteristics were observed or validated."*
2. **Clear Distinction Between REPEATED_PATTERN and ACTIONABLE_PATTERN**: Defined the additional evidence thresholds (recurrence across $\ge 3$ sessions, $\ge 0.60$ tracking confidence, $\ge 70\%$ observability, verified catalog drills) and explicitly bounded `ACTIONABLE_PATTERN` to advisory proposal formulation only. It requires explicit user consent and never directly mutates an active workout or `effectivePlanSnapshot`.
3. **Strategy Scope Wording Revised**: Replaced all instances of "In Scope for Phase 9C.6" with *"Architecture design in scope for Phase 9C.6; implementation requires separate explicit approval."*
4. **Provisional Performance Targets Clarified**: Added an explicit callout confirming that all latency and budget numbers ($<150\text{ ms}$ p95, $<100\text{ ms}$ p95, $<5\text{ ms}$, $<15\text{ ms}$) are provisional unbenchmarked engineering targets, not measured results or guaranteed acceptance outcomes.
5. **No Contradictions**: Ensured complete consistency across all sections: Phase 9C.6 is strictly an architecture assessment and planning milestone. Zero production source code, configuration files, or database schemas were modified, and no production implementation or tests were executed.

Implementation of Phase 9C.6.1 will commence only upon receiving explicit user authorization.
