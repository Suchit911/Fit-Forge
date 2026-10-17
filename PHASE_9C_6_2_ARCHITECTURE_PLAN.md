# Phase 9C.6.2 — Persistent Form Evidence Aggregation Engine
## Version 2.3.3 Targeted Final Consistency Specification

**Document Version**: 2.3.3  
**Document State**: `PHASE 9C.6.2 — ARCHITECTURE CLARIFICATION ONLY — IMPLEMENTATION NOT APPROVED`  
**Phase Target**: Phase 9C.6.2 — Persistent Form Evidence Aggregation Engine  
**Preceding Milestone**: Phase 9C.6.1 — Form Evidence & Issue Normalization Contracts (Status: Complete, Executed Unit Tests Passed: 55/55)  
**Implementation Readiness Verdict**: `ARCHITECTURE CLARIFICATION COMPLETE — IMPLEMENTATION NOT APPROVED — AWAITING EXPLICIT USER AUTHORIZATION`  

---

## 1. Executive Summary & Inviolable Invariants

### 1.1 Executive Summary
Phase 9C.6.2 establishes the persistent, multi-session form evidence aggregation engine for the AI Fitness Platform. Building directly upon the normalized repetition evidence produced by Phase 9C.6.1 (`NormalizedFormIssue`), Phase 9C.6.2 is responsible for:
1. Aggregating repetition-level form evidence within an individual workout session into a deterministic, issue-level summary (`SessionEvidenceRecord`).
2. Persisting session analysis details atomically into Firestore with strict idempotency and payload conflict detection (`FormAnalysisSessionDetailSchema`).
3. Performing longitudinal, multi-session evidence aggregation across a bounded lookback window ($K = 5$ eligible sessions) to identify persistent movement patterns (`ExerciseEvidenceSummary`).
4. Enforcing a strict non-medical safety boundary, snapshot immutability, and deterministic classification hierarchy.

This **Version 2.3.3 Targeted Final Consistency Specification** normalizes all configuration parameter names to their canonical forms, corrects fail-closed terminology across all sections, expands the `PARTIAL_FAILURE` test contract with eight explicit assertions, and completes the final cross-document consistency audit.

### 1.2 Distinct Status & Readiness Declarations
To maintain absolute transparency and eliminate confusion between written architectural completeness and physical code execution:
* **Architecture Clarification Completeness**: `100% COMPLETE (Version 2.3.3 Specification)`
* **Implementation Status**: `NOT STARTED — IMPLEMENTATION NOT APPROVED`
* **Test Specification Coverage**: `100% (34 Formal Test Specifications Defined)`
* **Executed Test Results (Phase 9C.6.2)**: `0 EXECUTED (Awaiting Implementation Authorization)`
* **Production-Readiness Status**: `PENDING IMPLEMENTATION & TEST EXECUTION`

### 1.3 Inviolable Architectural Invariants
The following eight invariants are absolute, non-negotiable architectural boundaries that govern all aspects of this design:

1. **Zero Production Code or Migration Execution**:
   This phase is an architecture clarification only. No production code, database schema migrations, Firestore document modifications, or test changes shall be executed until explicit user authorization is provided.
2. **Zero Direct Plan Mutation**:
   The evidence engine is strictly analytical and read-only. It possesses zero authority to modify active workout plans, change exercise parameters, alter mesocycle progressions, or write to training schedules.
3. **Snapshot Immutability for `planSnapshot` and `effectivePlanSnapshot`**:
   Workout plan snapshots created at session inception are permanent historical records. Neither `planSnapshot` nor `effectivePlanSnapshot` may ever be overwritten, patched, or mutated by form analysis results.
4. **Zero Automatic Exercise Substitution**:
   Strategy D (automatic exercise substitution based on movement defects) is formally and permanently rejected. All corrective recommendations are purely advisory and require explicit, separate user review and consent in downstream phases (Strategy B, Phase 9C.6.6).
5. **Strict Non-Medical Safety Boundary**:
   The engine analyzes biomechanical technique characteristics only. It makes zero medical diagnoses, offers zero clinical rehabilitation advice, issues zero injury risk guarantees, and maintains disclaimers across all exposed payloads.
6. **Zero LLM in the Live MediaPipe WebSocket Loop**:
   All live repetition tracking, kinematic heuristics, normalization, and aggregation are 100% deterministic mathematical calculations. Large Language Models are strictly prohibited from the live frame-processing and WebSocket pipeline.
7. **Missing Data Must Never Be Classified as Bad Form (`MISSING_DATA != BAD_FORM`)**:
   Unobserved, unrecorded, missing landmarks, or malformed inputs must never contribute to defect counts or be penalized as improper technique. Missing or malformed data strictly fails closed to unobserved (`CATEGORY_NOT_OBSERVABLE`).
8. **Occluded and Low-Confidence Observations Must Not Be Treated as Technique Defects**:
   Joint occlusions, camera framing cutoffs, and sensor tracking confidence below the mathematical floor ($0.50$) represent measurement uncertainty, never user error. They strictly fail closed and are excluded from defect numerators.

---

## 2. Architecture Scope and Data Flow

### 2.1 Complete Data Flow Architecture

The data flow spans from normalized Phase 9C.6.1 repetition evidence to persistent longitudinal aggregation:

```text
+----------------------------------------------------------------------------------------------------+
| STAGE 1: LIVE REPETITION EVIDENCE (Phase 9B & Phase 9C.6.1 - Operational)                          |
| MediaPipe 33 Keypoints (25 FPS) -> PoseLandmarker -> Joint Kinematics                              |
| -> ExerciseFSM (Rep Completed) -> FormHeuristicsEngine                                            |
| -> FormIssueNormalizer -> NormalizedFormIssue Records                                              |
+----------------------------------------------------------------------------------------------------+
                                                  |
                                                  v
+----------------------------------------------------------------------------------------------------+
| STAGE 2: INPUT VALIDATION & CALCULATION STATUS (SessionEvidenceAggregator Entry)                  |
| - Validate ActiveSessionState & Repetition Records                                                 |
| - Strict Numeric Confidence Validation: float/int, NOT bool, finite, [0.0, 1.0]                    |
| - Strict Boolean Acceptability Validation: ONLY True/False, No Type Coercion                       |
| - Incomplete / Malformed Data Fails Closed to CATEGORY_NOT_OBSERVABLE                              |
| - Assign Heuristic-Level CalculationStatus (SUCCESS vs. FAILED)                                     |
| - Determine Initial Session CalculationStatus (SUCCESS, PARTIAL_FAILURE, INSUFFICIENT_INPUT)       |
+----------------------------------------------------------------------------------------------------+
                                                  |
                                                  v
+----------------------------------------------------------------------------------------------------+
| STAGE 3: SINGLE-SESSION AGGREGATION (Pure In-Memory Math)                                          |
| - Cascading 5-Way Repetition Classification Partition (Mutually Exclusive):                        |
|     1. CATEGORY_NOT_OBSERVABLE                                                                     |
|     2. CATEGORY_OCCLUDED                                                                           |
|     3. CATEGORY_LOW_CONFIDENCE                                                                     |
|     4. CATEGORY_OBSERVED_ACCEPTABLE                                                                |
|     5. CATEGORY_OBSERVED_DEFECTIVE                                                                 |
| - Mathematical Partition Invariant: Sum of 5 Categories == target_reps_total                        |
| - Denominator Definition: target_reps_used_for_defect_rate = target_reps_observed                  |
| - Defect Rate Formula: DefectRate(I) = DefectiveReps(I) / ObservedReps(I) (None if observed < 3)   |
| - Single-Session Mean Confidence: Mean across Valid Observed Repetitions Only                      |
| - Emit: SessionEvidenceRecord                                                                      |
+----------------------------------------------------------------------------------------------------+
                                                  |
                                                  v
+----------------------------------------------------------------------------------------------------+
| STAGE 4: SESSION QUALIFICATION GATE                                                                |
| - Criteria: status == "completed" AND valid_reps >= MIN_VALID_REPS_PER_SESSION (3)                 |
|             AND session_observability_ratio >= MIN_SESSION_OBSERVABILITY_RATIO (0.70)             |
| - Ineligible sessions marked is_eligible_for_trends = False (Kept in history, excluded from trends)|
+----------------------------------------------------------------------------------------------------+
                                                  |
                                                  v
+----------------------------------------------------------------------------------------------------+
| STAGE 5: PERSISTENCE BOUNDARY & PROVENANCE GATE                                                    |
| Single Write Path: FormAnalysisRepository._persist_session_detail_atomic                           |
| - Written atomically via Firestore Transaction                                                     |
| - Payload Fingerprint Verification (SHA-256 Canonical JSON)                                        |
|     * Non-existent: Create document (HTTP 201 Created)                                            |
|     * Identical Retry: Match Fingerprint -> Return existing doc (HTTP 200 OK)                      |
|     * Conflicting Payload: Mismatch -> Raise ConflictingSessionPayloadError (HTTP 409 Conflict)    |
| - Enforce Provenance Tier (TIER_1_NORMALIZED, TIER_2_COMPACT_TAGS, TIER_3_DEFECT_STRING)           |
+----------------------------------------------------------------------------------------------------+
                                                  |
                                                  v (Queried On-Demand for Longitudinal Analytics)
+----------------------------------------------------------------------------------------------------+
| STAGE 6: LOOKBACK SELECTION & MULTI-SESSION AGGREGATION (MultiSessionEvidenceAggregator)          |
| Approach B Sequence: Filter All Completed Sessions First -> Take Latest K=5 Eligible Sessions      |
| - Provenance Filter: provenance_tier != TIER_4_UNPROVENANCED                                       |
| - Calculation Status Filter: session.calculation_status != FAILED                                  |
| - Identify N_session_eligible (Lookback window sessions, <= LOOKBACK_SESSIONS_K)                   |
| - Target Issue Isolation: check issue_summary.calculation_status == SUCCESS                        |
| - Identify N_target_eval (Sessions where target issue calculation succeeded & observed reps >= 3) |
| - Identify N_qualifying (Sessions in N_target_eval with defect_rate >= 0.50)                       |
| - Compute RecurrenceRatio(I) = N_qualifying(I) / N_target_eval(I) (Approach B Selected)           |
| - Compute C_qualifying_mean(I) across N_qualifying sessions (None if N_qualifying == 0)            |
+----------------------------------------------------------------------------------------------------+
                                                  |
                                                  v
+----------------------------------------------------------------------------------------------------+
| STAGE 7: EVIDENCE CLASSIFICATION PRECEDENCE DECISION TREE                                          |
| Deterministic 4-Step Precedence:                                                                   |
|   Step 1: N_session_eligible < 3 OR N_target_eval < 3 -> INSUFFICIENT_DATA                         |
|   Step 2: N_qualifying == 0                           -> NO_EVIDENCE                               |
|   Step 3: N_qualifying == 1                           -> EMERGING_OCCURRENCE                       |
|   Step 4: N_qualifying >= 3 AND Dual Confidence Gate Passes -> ACTIONABLE_PATTERN,                 |
|           Else -> REPEATED_PATTERN                                                                 |
| - Emit: Read-Only ExerciseEvidenceSummary with Complete Issue-Level Provenance Metadata            |
+----------------------------------------------------------------------------------------------------+
                                                  |
                                                  v
+----------------------------------------------------------------------------------------------------+
| STAGE 8: DOWNSTREAM ADVISORY CONSUMPTION (Phase 9C.6.3 - 9C.6.6)                                   |
| - CorrectiveGuidanceService queries candidate drills from catalog graph                            |
| - Read-only REST API endpoints (/evidence/{exercise_id}, /correctives/{exercise_id})               |
| - Display in FormTechniqueGuidanceCard & Exercise Detail Technique Tab                             |
| - Strategy B (Phase 9C.6.6): Formulates Advisory Future-Workout Slot 0 Proposal (User Consent Req)|
+----------------------------------------------------------------------------------------------------+
```

---

## 3. Fail-Closed vs. Fail-Open Terminology Clarification

### 3.1 Terminology Governance
To ensure consistent safety posture throughout the entire codebase and documentation:
* **Fail-Closed Security/Safety Posture**: When any input datum is missing, incomplete, non-numeric, or malformed, access to the "observed" population is **denied**. The data strictly fails closed to `CATEGORY_NOT_OBSERVABLE` (or `CATEGORY_OCCLUDED` / `CATEGORY_LOW_CONFIDENCE`). It is completely barred from entering defect numerators, observation denominators, or mean confidence calculations.
* **Prohibition of "Fail-Open" Terminology**: The phrase "fails open" is permanently retired from this specification. Incomplete poses, malformed calculations, and missing landmarks do **not** fail open; they **fail closed** to `CATEGORY_NOT_OBSERVABLE` and are strictly excluded from all valid observation calculations.

### 3.2 Terminology Audit Table

| Term | Operational Context | Meaning in Form Evidence Engine | Approved Architectural Usage |
| :--- | :--- | :--- | :--- |
| **Fail-Closed** | Input validation, landmark checks, confidence verification, acceptability typing | Input fails validation; blocked from passing observation gate; assigned to `CATEGORY_NOT_OBSERVABLE`. | **MANDATORY**: All invalid, missing, or malformed data fails closed. |
| **Fail-Open** | Prohibited | Erroneous legacy phrase implying permissive bypass. | **STRICTLY PROHIBITED**. |
| **Missing Data** | `landmarks is None`, `len < 33`, `confidence is None`, `is_acceptable is None` | Keypoint or measurement absent from stream. Fails closed to `CATEGORY_NOT_OBSERVABLE`. | Supported; never contributes to defect rates (`MISSING_DATA != BAD_FORM`). |
| **Invalid Data** | Boolean confidence, string acceptability, `NaN`, `Inf`, out-of-range float | Corrupted input payload. Fails closed to `CATEGORY_NOT_OBSERVABLE` with explicit data quality flag. | Supported; logged in `data_quality_flags`; blocked from calculation. |
| **Not Observable** | Category 1 in 5-way partition (`CATEGORY_NOT_OBSERVABLE`) | Repetition could not be evaluated due to absence, occlusion of frame, or data malformation. | Authoritative classification category. |
| **Low Confidence** | Category 3 in 5-way partition (`CATEGORY_LOW_CONFIDENCE`) | Sensor produced valid numeric score $c \in [0.0, 1.0]$, but $c < 0.50$. | Isolated category; excluded from observed denominator; never a defect. |
| **Rejected Evidence**| Longitudinal lookback selection | Sessions failing completion, minimum reps, observability, or provenance tiers. | Excluded from lookback window $\mathcal{S}_{\text{session\_eligible}}$. |

---

## 4. Canonical Configuration Parameter Names & Relational Invariants

### 4.1 Canonical Naming Specification
All parameters must be referenced exclusively by their canonical uppercase names. All abbreviations (`ACTIONABLE_SESSION_MIN_CONF`, `ACTIONABLE_MIN_CONF`, `MIN_HEURISTIC_CONF`, `REPEATED_MIN`, `LOOKBACK_K`) are formally removed.

| Canonical Configuration Parameter | Data Type | Min | Max | Boundary | Default | Zero Permitted? | Level | Authoritative Relational Constraints |
| :--- | :---: | :---: | :---: | :---: | :---: | :---: | :---: | :--- |
| `MIN_HEURISTIC_CONFIDENCE` | `float` | 0.10 | 1.00 | Inclusive $[0.10, 1.00]$ | 0.50 | **NO** | Repetition | Must satisfy: $\le \text{ACTIONABLE\_PATTERN\_SESSION\_MIN\_CONFIDENCE}$ |
| `ACTIONABLE_PATTERN_SESSION_MIN_CONFIDENCE` | `float` | 0.10 | 1.00 | Inclusive $[0.10, 1.00]$ | 0.55 | **NO** | Session Floor | Must satisfy: $\ge \text{MIN\_HEURISTIC\_CONFIDENCE} \land \le \text{ACTIONABLE\_PATTERN\_MIN\_CONFIDENCE}$ |
| `ACTIONABLE_PATTERN_MIN_CONFIDENCE` | `float` | 0.10 | 1.00 | Inclusive $[0.10, 1.00]$ | 0.60 | **NO** | Aggregate Mean | Must satisfy: $\ge \text{ACTIONABLE\_PATTERN\_SESSION\_MIN\_CONFIDENCE}$ |
| `MIN_TARGET_HEURISTIC_OBSERVED_REPS` | `int` | 1 | 50 | Inclusive $[1, 50]$ | 3 | **NO** | Issue | Must satisfy: $\le \text{MIN\_VALID\_REPS\_PER\_SESSION}$ |
| `MIN_VALID_REPS_PER_SESSION` | `int` | 1 | 50 | Inclusive $[1, 50]$ | 3 | **NO** | Session | Must satisfy: $\ge \text{MIN\_TARGET\_HEURISTIC\_OBSERVED\_REPS}$ |
| `SESSION_DEFECT_RATE_THRESHOLD` | `float` | 0.01 | 1.00 | Inclusive $[0.01, 1.00]$ | 0.50 | **NO** | Issue (Session)| Strictly bounded in $(0.0, 1.0]$ |
| `REPEATED_PATTERN_MIN_SESSIONS` | `int` | 1 | 20 | Inclusive $[1, 20]$ | 2 | **NO** | Issue (Longitudinal)| Must satisfy: $\le \text{ACTIONABLE\_PATTERN\_MIN\_SESSIONS}$ |
| `ACTIONABLE_PATTERN_MIN_SESSIONS` | `int` | 1 | 20 | Inclusive $[1, 20]$ | 3 | **NO** | Issue (Longitudinal)| Must satisfy: $\ge \text{REPEATED\_PATTERN\_MIN\_SESSIONS} \land \le \text{LOOKBACK\_SESSIONS\_K}$ |
| `LOOKBACK_SESSIONS_K` | `int` | 3 | 20 | Inclusive $[3, 20]$ | 5 | **NO** | Session (Lookback) | Must satisfy: $\ge \text{ACTIONABLE\_PATTERN\_MIN\_SESSIONS}$ |
| `MIN_SESSION_OBSERVABILITY_RATIO` | `float` | 0.10 | 1.00 | Inclusive $[0.10, 1.00]$ | 0.70 | **NO** | Session | Strictly bounded in $(0.0, 1.0]$ |

### 4.2 The Confidence Triad Invariant
The engine enforces the canonical Confidence Triad Invariant:

$$\text{MIN\_HEURISTIC\_CONFIDENCE} \le \text{ACTIONABLE\_PATTERN\_SESSION\_MIN\_CONFIDENCE} \le \text{ACTIONABLE\_PATTERN\_MIN\_CONFIDENCE}$$

With default engineering values:
$$0.50 \le 0.55 \le 0.60$$

* **Violation Behavior**: If any configuration violates this ascending order (e.g. setting per-session floor to $0.65$ while aggregate mean is $0.60$, or setting heuristic floor to $0.55$ while session floor is $0.50$), `EvidenceAggregationConfig.__post_init__` immediately raises a fail-fast `ValueError`, preventing service startup.

```python
from dataclasses import dataclass

@dataclass(frozen=True)
class EvidenceAggregationConfig:
    MIN_HEURISTIC_CONFIDENCE: float = 0.50
    ACTIONABLE_PATTERN_SESSION_MIN_CONFIDENCE: float = 0.55
    ACTIONABLE_PATTERN_MIN_CONFIDENCE: float = 0.60
    MIN_TARGET_HEURISTIC_OBSERVED_REPS: int = 3
    MIN_VALID_REPS_PER_SESSION: int = 3
    SESSION_DEFECT_RATE_THRESHOLD: float = 0.50
    REPEATED_PATTERN_MIN_SESSIONS: int = 2
    ACTIONABLE_PATTERN_MIN_SESSIONS: int = 3
    LOOKBACK_SESSIONS_K: int = 5
    MIN_SESSION_OBSERVABILITY_RATIO: float = 0.70

    def __post_init__(self) -> None:
        # Confidence Triad Invariant validation
        if not (self.MIN_HEURISTIC_CONFIDENCE <= self.ACTIONABLE_PATTERN_SESSION_MIN_CONFIDENCE <= self.ACTIONABLE_PATTERN_MIN_CONFIDENCE):
            raise ValueError(
                f"Confidence Triad Invariant violated: expected MIN_HEURISTIC_CONFIDENCE ({self.MIN_HEURISTIC_CONFIDENCE}) "
                f"<= ACTIONABLE_PATTERN_SESSION_MIN_CONFIDENCE ({self.ACTIONABLE_PATTERN_SESSION_MIN_CONFIDENCE}) "
                f"<= ACTIONABLE_PATTERN_MIN_CONFIDENCE ({self.ACTIONABLE_PATTERN_MIN_CONFIDENCE})"
            )
        # Volume & Session Invariants
        if self.MIN_TARGET_HEURISTIC_OBSERVED_REPS > self.MIN_VALID_REPS_PER_SESSION:
            raise ValueError(
                f"MIN_TARGET_HEURISTIC_OBSERVED_REPS ({self.MIN_TARGET_HEURISTIC_OBSERVED_REPS}) "
                f"cannot exceed MIN_VALID_REPS_PER_SESSION ({self.MIN_VALID_REPS_PER_SESSION})"
            )
        if self.ACTIONABLE_PATTERN_MIN_SESSIONS < self.REPEATED_PATTERN_MIN_SESSIONS:
            raise ValueError(
                f"ACTIONABLE_PATTERN_MIN_SESSIONS ({self.ACTIONABLE_PATTERN_MIN_SESSIONS}) "
                f"cannot be less than REPEATED_PATTERN_MIN_SESSIONS ({self.REPEATED_PATTERN_MIN_SESSIONS})"
            )
        if self.ACTIONABLE_PATTERN_MIN_SESSIONS > self.LOOKBACK_SESSIONS_K:
            raise ValueError(
                f"ACTIONABLE_PATTERN_MIN_SESSIONS ({self.ACTIONABLE_PATTERN_MIN_SESSIONS}) "
                f"cannot exceed LOOKBACK_SESSIONS_K ({self.LOOKBACK_SESSIONS_K})"
            )
```

---

## 5. Expanded `PARTIAL_FAILURE` Contract & Test Specification

### 5.1 The Scenario
A multi-heuristic squat workout session evaluating three distinct kinematic heuristics:
* **Squat Depth (`squat_depth`)**: `CalculationStatus.SUCCESS` (10 reps observed, 6 defective, defect rate = 60%, mean confidence = 0.82).
* **Torso Inclination (`squat_torso_lean`)**: `CalculationStatus.FAILED` (Unhandled mathematical exception in inclination normalizer; caught, error logged, calculation aborted).
* **Knee Valgus (`squat_knee_valgus`)**: `CalculationStatus.SUCCESS` (10 reps observed, 0 defective, defect rate = 0%, mean confidence = 0.78).
* **Composite Session Calculation Status**: `CalculationStatus.PARTIAL_FAILURE`.

### 5.2 Eight Explicit Expected Assertions
Any implementation of Subphase 9C.6.2.2 and 9C.6.2.3 must satisfy all eight formal assertions:

1. **Depth Aggregation Eligibility**: Successful depth evidence remains fully eligible for depth-specific longitudinal aggregation. Session $S$ is included in $\mathcal{S}_{\text{target\_eval}}(\text{insufficient\_depth})$.
2. **Knee Valgus Aggregation Eligibility**: Successful knee valgus evidence remains fully eligible for knee-valgus-specific longitudinal aggregation. Session $S$ is included in $\mathcal{S}_{\text{target\_eval}}(\text{knee\_tracking\_deviation})$.
3. **Torso Inclination Denominator Exclusion**: Failed torso inclination evidence is strictly excluded from its own target-evaluation denominator ($N_{\text{target\_eval}}$). It contributes **$+0$ to numerator ($N_{\text{qualifying}}$)** and **$+0$ to denominator ($N_{\text{target\_eval}}$)**.
4. **No False Clean Technique Attribution**: Failed torso inclination evidence does **not** become valid `NO_EVIDENCE`. If torso inclination was unobserved or failed across all lookback sessions, its longitudinal status evaluates to `INSUFFICIENT_DATA`.
5. **Metadata Traceability & Transparency**: The failed issue is accurately represented on `SessionIssueSummary` with `calculation_status = CalculationStatus.FAILED`, `defect_rate = None`, and `data_quality_flags = ["ERROR_HEURISTIC_CALCULATION_FAILED"]`.
6. **Non-Destructive Session-Level Status**: The session-level `PARTIAL_FAILURE` status does not discard or taint successful issue-level calculations in the same session.
7. **Mathematical Recurrence Ratio Consistency**: Recurrence ratios remain mathematically consistent with the Approach B definition:
   * $\text{RecurrenceRatio}(\text{insufficient\_depth}) = N_{\text{qualifying}} / N_{\text{target\_eval}}$
   * Torso inclination is absent from $N_{\text{target\_eval}}(\text{excessive\_torso\_lean})$.
8. **Persistence Contract & Provenance Integrity**: The persistence layer commits the entire `FormAnalysisSessionDetailSchema` with session status `PARTIAL_FAILURE` and issue-level statuses intact. Provenance tracking identifies which issues succeeded and which experienced errors.

---

## 6. Longitudinal Population Metrics & Predicate Hierarchy

### 6.1 The Three Authoritative Population Counts
1. **$N_{\text{session\_eligible}}$**: Total sessions qualifying for the lookback window ($N_{\text{session\_eligible}} \le \text{LOOKBACK\_SESSIONS\_K} = 5$).
2. **$N_{\text{target\_eval}}(I)$**: Count of sessions in $N_{\text{session\_eligible}}$ where target issue $I$'s calculation succeeded (`calculation_status == SUCCESS`) and observed repetitions $\ge \text{MIN\_TARGET\_HEURISTIC\_OBSERVED\_REPS} (3)$.
3. **$N_{\text{qualifying}}(I)$**: Count of sessions in $N_{\text{target\_eval}}(I)$ where issue $I$'s defect rate $\ge \text{SESSION\_DEFECT\_RATE\_THRESHOLD} (0.50)$.

### 6.2 The Recurrence Ratio (Approach B Confirmed)
$$\text{RecurrenceRatio}(I) = \begin{cases}
\dfrac{N_{\text{qualifying}}(I)}{N_{\text{target\_eval}}(I)} & \text{if } N_{\text{target\_eval}}(I) \ge \text{config.ACTIONABLE\_PATTERN\_MIN\_SESSIONS} (3) \\
0.0 & \text{if } N_{\text{target\_eval}}(I) < 3 \text{ (Fails Step 1 to INSUFFICIENT\_DATA)}
\end{cases}$$

### 6.3 Actionable Confidence Metric ($C_{\text{qualifying\_mean}}$)
$$C_{\text{qualifying\_mean}}(I) = \begin{cases}
\dfrac{1}{N_{\text{qualifying}}(I)} \sum_{S \in \mathcal{S}_{\text{qualifying}}(I)} S.\text{issues}[I].\text{mean\_confidence} & \text{if } N_{\text{qualifying}}(I) \ge 1 \\
\text{None} & \text{if } N_{\text{qualifying}}(I) == 0
\end{cases}$$

---

## 7. Schemas & Data Contracts (`backend/app/schemas/form_evidence.py`)

```python
from enum import Enum
from typing import Dict, List, Optional
from pydantic import BaseModel, Field
from backend.app.schemas.form_analysis import NormalizedFormIssue, FormMeasurementData

class EvidenceLevel(str, Enum):
    NO_EVIDENCE = "NO_EVIDENCE"
    INSUFFICIENT_DATA = "INSUFFICIENT_DATA"
    EMERGING_OCCURRENCE = "EMERGING_OCCURRENCE"
    REPEATED_PATTERN = "REPEATED_PATTERN"
    ACTIONABLE_PATTERN = "ACTIONABLE_PATTERN"

class CalculationStatus(str, Enum):
    SUCCESS = "SUCCESS"
    PARTIAL_FAILURE = "PARTIAL_FAILURE"
    FAILED = "FAILED"
    INSUFFICIENT_INPUT = "INSUFFICIENT_INPUT"

class ProvenanceTier(str, Enum):
    TIER_1_NORMALIZED = "TIER_1_NORMALIZED"
    TIER_2_COMPACT_TAGS = "TIER_2_COMPACT_TAGS"
    TIER_3_DEFECT_STRING = "TIER_3_DEFECT_STRING"
    TIER_4_UNPROVENANCED = "TIER_4_UNPROVENANCED"

class SessionIssueSummary(BaseModel):
    """Technique issue summary within a single session with issue-level calculation status."""
    issue_id: str
    source_heuristic: str
    category: str
    calculation_status: CalculationStatus = CalculationStatus.SUCCESS
    data_quality_flags: List[str] = Field(default_factory=list)
    target_reps_total: int = 0
    target_reps_observed: int = 0
    target_reps_defective: int = 0
    target_reps_occluded: int = 0
    target_reps_low_confidence: int = 0
    target_reps_not_observable: int = 0
    target_reps_used_for_defect_rate: int = 0
    defect_rate: Optional[float] = None
    mean_confidence: Optional[float] = None
    representative_measurement: Optional[FormMeasurementData] = None
    sample_feedback: List[str] = Field(default_factory=list)

class SessionEvidenceRecord(BaseModel):
    """Complete aggregated evidence for an individual session."""
    session_id: str
    user_id: str
    exercise_id: str
    completed_at: str
    total_reps: int
    valid_reps: int
    session_observability_ratio: float
    is_eligible_for_trends: bool
    calculation_status: CalculationStatus = CalculationStatus.SUCCESS
    data_quality_flags: List[str] = Field(default_factory=list)
    provenance_tier: ProvenanceTier = ProvenanceTier.TIER_1_NORMALIZED
    issues: Dict[str, SessionIssueSummary] = Field(default_factory=dict)
    normalized_issues: List[NormalizedFormIssue] = Field(default_factory=list)

class AggregatedIssueEvidence(BaseModel):
    """Longitudinal multi-session evidence for a single technique issue with full provenance."""
    issue_id: str
    source_heuristic: str
    category: str
    session_eligible_count: int
    target_evaluated_sessions_count: int
    qualifying_sessions_count: int
    recurrence_ratio: float
    qualifying_mean_confidence: Optional[float] = None
    evidence_level: EvidenceLevel
    first_observed_at: Optional[str] = None
    latest_observed_at: Optional[str] = None
    source_session_ids: List[str] = Field(default_factory=list)
    qualifying_session_ids: List[str] = Field(default_factory=list)
    provenance_tiers_used: List[str] = Field(default_factory=list)
    aggregation_version: str = "2.3.3"
    config_version: str = "1.0.0"
    data_quality_flags: List[str] = Field(default_factory=list)

class ExerciseEvidenceSummary(BaseModel):
    """Longitudinal technique evaluation across lookback sessions for an exercise."""
    aggregation_version: str = "2.3.3"
    config_version: str = "1.0.0"
    user_id: str
    exercise_id: str
    lookback_sessions_evaluated: int
    eligible_sessions_count: int
    evaluated_at: str
    primary_issue_id: Optional[str] = None
    evidence_level: EvidenceLevel
    status_message: str
    calculation_status: CalculationStatus = CalculationStatus.SUCCESS
    source_session_ids: List[str] = Field(default_factory=list)
    data_quality_flags: List[str] = Field(default_factory=list)
    issues: Dict[str, AggregatedIssueEvidence] = Field(default_factory=dict)
    disclaimer: str = (
        "This movement analysis represents general technique observations. "
        "It is not a medical diagnosis or rehabilitation prescription."
    )
```

---

## 8. Persistence, Idempotency, and Snapshot Immutability

* Path: `users/{user_id}/form_analysis_sessions/{session_id}`
* Governed by **Firestore Transaction with SHA-256 Payload Fingerprinting**:
  $$\text{payload\_fingerprint} = \text{SHA256}\Big(\text{CanonicalJSON}\big( \text{user\_id}, \text{session\_id}, \text{canonical\_exercise\_id}, \text{reps}, \text{client\_duration\_seconds}, \text{client\_notes} \big)\Big)$$
* Identical Retries: Return existing document (HTTP 200 OK, Zero Writes).
* Conflicting Payloads: Raise `ConflictingSessionPayloadError` (HTTP 409 Conflict).
* Call Graph: All persistence flows strictly through `FormAnalysisRepository._persist_session_detail_atomic`. Legacy `save_session_summary` is formally removed from write path.
* **Snapshot Immutability**: Neither `planSnapshot` nor `effectivePlanSnapshot` is ever modified. Strategy D (automatic exercise substitution) is permanently rejected.

---

## 9. Comprehensive Test Specification Matrix (34 Test Specifications)

| Test ID | Test Scenario | Preconditions | Input Data | Expected Result | Invariant Verified |
| :---: | :--- | :--- | :--- | :--- | :--- |
| **T01** | Empty Evidence Input | Engine initialized | Repetition list `[]` | `calculation_status = INSUFFICIENT_INPUT` | Missing data handled fail-closed. |
| **T02** | All Repetitions Occluded | 10 reps evaluated | 10 reps with `is_occluded = True` | All in `CATEGORY_OCCLUDED`, `target_reps_observed = 0`, defect rate `None` | `MISSING_DATA != BAD_FORM`. |
| **T03** | Sub-Threshold Confidence | 10 reps evaluated | 10 reps with `confidence = 0.49` | All in `CATEGORY_LOW_CONFIDENCE`, `target_reps_observed = 0`, defect rate `None` | Low confidence isolated. |
| **T04** | Missing Confidence (None) | 5 reps evaluated | `confidence = None` | All in `CATEGORY_NOT_OBSERVABLE`, flag `FLAG_MISSING_CONFIDENCE` | Missing confidence fails closed. |
| **T05** | Boolean Confidence True | 5 reps evaluated | `confidence = True` | All in `CATEGORY_NOT_OBSERVABLE`, flag `FLAG_BOOLEAN_CONFIDENCE_PROHIBITED` | Strict non-boolean validation. |
| **T06** | Boolean Confidence False | 5 reps evaluated | `confidence = False` | All in `CATEGORY_NOT_OBSERVABLE`, flag `FLAG_BOOLEAN_CONFIDENCE_PROHIBITED` | Strict non-boolean validation. |
| **T07** | String Confidence | 5 reps evaluated | `confidence = "0.85"` | All in `CATEGORY_NOT_OBSERVABLE`, flag `FLAG_INVALID_CONFIDENCE_TYPE` | Type corruption fails closed. |
| **T08** | NaN Confidence | 5 reps evaluated | `confidence = float('nan')` | All in `CATEGORY_NOT_OBSERVABLE`, flag `FLAG_NAN_CONFIDENCE` | Mathematical anomaly isolated. |
| **T09** | Infinite Confidence | 5 reps evaluated | `confidence = float('inf')` | All in `CATEGORY_NOT_OBSERVABLE`, flag `FLAG_INFINITE_CONFIDENCE` | Mathematical overflow isolated. |
| **T10** | Out-of-Range Confidence | 5 reps evaluated | `confidence = 1.50` or `-0.20` | All in `CATEGORY_NOT_OBSERVABLE`, flag `FLAG_OUT_OF_RANGE_CONFIDENCE` | Domain $[0.0, 1.0]$ enforced. |
| **T11** | Boundary Confidence 0.0 | 5 reps evaluated | `confidence = 0.0` | All in `CATEGORY_LOW_CONFIDENCE`, flag `FLAG_SUBTHRESHOLD_CONFIDENCE` | Zero valid but sub-threshold. |
| **T12** | Boundary Confidence 0.50| 5 reps evaluated | `confidence = 0.50` | Enters observed evaluation, confidence valid | Exact observation threshold. |
| **T13** | Null `is_acceptable` | 5 reps evaluated | `is_acceptable = None` | All in `CATEGORY_NOT_OBSERVABLE`, flag `FLAG_NULL_ACCEPTABILITY` | Null never defaults to clean. |
| **T14** | Numeric Acceptability (0/1)| 5 reps evaluated | `is_acceptable = 1` or `0` | All in `CATEGORY_NOT_OBSERVABLE`, flag `FLAG_NON_BOOLEAN_ACCEPTABILITY` | Strict boolean acceptability. |
| **T15** | String Acceptability | 5 reps evaluated | `is_acceptable = "True"` | All in `CATEGORY_NOT_OBSERVABLE`, flag `FLAG_NON_BOOLEAN_ACCEPTABILITY` | No string coercion allowed. |
| **T16** | Missing Landmarks | Frame evaluated | Landmarks array length 15 ($< 33$) | Incomplete pose fails closed and is excluded from valid observation calculations (`CATEGORY_NOT_OBSERVABLE`, flag `FLAG_MISSING_LANDMARKS`) | Incomplete pose fails closed. |
| **T17** | Malformed Measurement | Kinematic math | Knee ROM = `float('nan')` | All in `CATEGORY_NOT_OBSERVABLE`, flag `FLAG_KINEMATIC_MATH_ERROR` | Kinematic corruption isolated. |
| **T18** | Five-Way Sum Identity | 10 reps evaluated | 2 unobs, 2 occl, 2 low-conf, 2 acc, 2 def | $\sum \text{Categories} == 10$, `observed = 4`, `defect_rate = 50%` | Partition mutual exclusivity & sum identity. |
| **T19** | Multi-Heuristic Partial Fail | Multi-heuristic run | Depth: SUCCESS (10 reps, 6 def); Torso lean: FAILED (exception); Knee valgus: SUCCESS (10 reps, 0 def) | Session `PARTIAL_FAILURE`. Depth & Knee qualify for longitudinal; Torso excluded from $N_{\text{target\_eval}}$ (+0/+0) | Issue-level isolation (Approach B). |
| **T20** | Complete Calculation Fail | Engine run | Corrupted session state | Session `FAILED`, excluded from longitudinal lookback | Corrupted calculations cannot enter trends. |
| **T21** | Insufficient Reps | Session finalize | Rep count 2 ($< 3$ min reps) | `is_eligible_for_trends = False` | Volume qualification gate. |
| **T22** | Low Observability | Session finalize | 10 reps, observability 65% ($< 70\%$) | `is_eligible_for_trends = False` | Observability qualification gate. |
| **T23** | Legacy `TIER_4` Record | Lookback query | `provenance_tier = TIER_4_UNPROVENANCED` | Excluded from lookback window | Legacy sessions cannot pollute trends. |
| **T24** | Identical Retry | Session exists | Second call with identical payload fingerprint | HTTP 200 with existing doc. Zero writes executed | Idempotent persistence contract. |
| **T25** | Conflicting Payload | Session exists | Second call with modified rep count | Raises `ConflictingSessionPayloadError` (HTTP 409) | Immutability and conflict rejection. |
| **T26** | Concurrent Finalization | 10 threads | Identical session payload | Exactly 1 Firestore document created; 9 return HTTP 200 | Atomic transaction concurrency safety. |
| **T27** | Lookback Boundary $K=5$ | 8 eligible sessions | Query latest sessions | Exactly the latest 5 eligible sessions selected | Bounded lookback window invariant. |
| **T28** | Target Eval $< 3$ | 5 eligible sessions | Target heuristic had observed reps $\ge 3$ in only 2 sessions | $N_{\text{target\_eval}} = 2 \implies$ `INSUFFICIENT_DATA` | Issue-level data sufficiency gate. |
| **T29** | Zero Qualifying Sessions | 5 eligible sessions | Defect rate 0% across all sessions ($N_{\text{qual}} = 0$) | `qualifying_mean_confidence = None`, `NO_EVIDENCE` | Zero-qualifying division by zero safe. |
| **T30** | Actionable Dual-Gate Pass| 3 qualifying sessions | $S_1 = 0.58, S_2 = 0.62, S_3 = 0.66$ (all $\ge 0.55$, mean $0.62 \ge 0.60$) | Classified as `ACTIONABLE_PATTERN` | Dual-level confidence gate pass. |
| **T31** | Actionable Session Floor Fail| 3 qualifying sessions | $S_1 = 0.52 (< 0.55), S_2 = 0.70, S_3 = 0.70$ (mean $0.64 \ge 0.60$) | Classified as `REPEATED_PATTERN` | Per-session floor failure demotion. |
| **T32** | Confidence Triad Invariant | Engine init | `MIN_HEURISTIC_CONFIDENCE (0.58) > ACTIONABLE_PATTERN_SESSION_MIN_CONFIDENCE (0.55)` | Raises `ValueError` at startup | Confidence Triad Invariant enforcement. |
| **T33** | Snapshot Immutability | Finalize session | Verify `planSnapshot` in database | `planSnapshot` and `effectivePlanSnapshot` byte-identical | Zero plan mutation invariant. |
| **T34** | Zero LLM in Live Loop | Live frame stream | Verify execution call stack | Zero LLM client imports or invocations in live loop | Deterministic live loop latency invariant. |

---

## 10. Cross-Document Consistency Audit & Change Log (Version 2.3.2 to 2.3.3)

### 10.1 Targeted Cross-Document Audit Summary
A comprehensive audit of all formulas, decision tables, relational bounds, and schemas confirms that each core concept has exactly one authoritative definition:
1. **Confidence Triad Invariant**: Bounded strictly as $\text{MIN\_HEURISTIC\_CONFIDENCE} \le \text{ACTIONABLE\_PATTERN\_SESSION\_MIN\_CONFIDENCE} \le \text{ACTIONABLE\_PATTERN\_MIN\_CONFIDENCE}$.
2. **Canonical Naming**: 100% normalized across schemas, config dataclass, relational proofs, and test tables. Zero abbreviated aliases remain.
3. **Fail-Closed Terminology**: 100% harmonized. All occurrences of "fail open" permanently purged and replaced with strict fail-closed definitions.
4. **`PARTIAL_FAILURE` Assertions**: Fully detailed across session health, issue status, denominator exclusion ($+0/+0$), and persistence immutability.
5. **Zero-Qualifying Confidence**: Confirmed as `None` (`null` in JSON) with averaging short-circuited.

### 10.2 Change Log (Modifications from Version 2.3.2 to Version 2.3.3)
1. **Configuration Parameter Normalization**: Replaced all abbreviated names (`ACTIONABLE_SESSION_MIN_CONF`, `ACTIONABLE_MIN_CONF`, `MIN_HEURISTIC_CONF`, `REPEATED_MIN`, `LOOKBACK_K`) with their canonical names across all text and code blocks.
2. **Confidence Triad Invariant Formalized**: Explicitly codified the ascending relationship $\text{MIN\_HEURISTIC\_CONFIDENCE} (0.50) \le \text{ACTIONABLE\_PATTERN\_SESSION\_MIN\_CONFIDENCE} (0.55) \le \text{ACTIONABLE\_PATTERN\_MIN\_CONFIDENCE} (0.60)$ and added startup validation raising `ValueError` on breach.
3. **Fail-Closed Safety Terminology Purged & Harmonized**: Corrected Test T16 and invariant statements to state that incomplete pose data and malformed inputs **fail closed** to `CATEGORY_NOT_OBSERVABLE`. Removed all instances of "fails open".
4. **Expanded `PARTIAL_FAILURE` Test Contract**: Expanded Test T19 with eight comprehensive assertions covering session status, issue status, longitudinal denominator isolation ($+0/+0$), and persistence integrity.
5. **Updated Test T32**: Repurposed T32 to explicitly test the Confidence Triad Invariant breach at initialization.

### 10.3 Remaining Unresolved Risks
1. **Environmental Lighting Spikes**: Severe lighting fluctuations mid-workout may cause MediaPipe joint tracking to fall below $0.50$. (Mitigated: Fails closed to `CATEGORY_LOW_CONFIDENCE`; strictly isolated from defect counts).
2. **Rapid WebSocket Finalization Reconnects**: Fast network reconnects during session wrap-up could emit multiple finalization frames. (Mitigated: Firestore transaction with SHA-256 payload fingerprinting safely resolves retries as HTTP 200 idempotent no-ops).

---

**PHASE 9C.6.2 — VERSION 2.3.3 ARCHITECTURE CLARIFICATION COMPLETE — IMPLEMENTATION NOT APPROVED — AWAITING EXPLICIT USER AUTHORIZATION.**
