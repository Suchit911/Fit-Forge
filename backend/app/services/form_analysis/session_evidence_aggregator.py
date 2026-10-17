"""
Authoritative Session Evidence Aggregator Service (Phase 9C.6.2.2).

Provides:
- Pure in-memory aggregation of single-session repetition-level technique evidence.
- Strict numeric non-boolean confidence validation conforming to canonical configuration thresholds.
- Strict boolean acceptability enforcement (zero type coercion of None, 0, 1, or strings).
- Deterministic cascading 5-way mutually exclusive repetition classification:
    1. CATEGORY_NOT_OBSERVABLE
    2. CATEGORY_OCCLUDED
    3. CATEGORY_LOW_CONFIDENCE
    4. CATEGORY_OBSERVED_ACCEPTABLE
    5. CATEGORY_OBSERVED_DEFECTIVE
- Strict mathematical partition invariant: sum(all five categories) == target_reps_total.
- Single-session defect rate computation using strictly valid observed repetitions as denominator.
- Issue-level calculation status (SUCCESS, FAILED, INSUFFICIENT_INPUT).
- Session-level calculation status (SUCCESS, PARTIAL_FAILURE, FAILED, INSUFFICIENT_INPUT).
- Multi-heuristic failure isolation (T19 contract): failed heuristics do not corrupt or destroy
  successful issue evidence from the same session.
- Output models from `backend/app/schemas/form_evidence.py` (`SessionIssueSummary`, `SessionEvidenceRecord`).
"""

import math
import uuid
import logging
from datetime import datetime, timezone
from typing import Dict, List, Optional, Tuple, Any, Union, Set

from backend.app.schemas.form_evidence import (
    SessionIssueSummary,
    SessionEvidenceRecord,
    CalculationStatus,
    ObservabilityCategory,
    ProvenanceTier,
    EvidenceAggregationConfig,
)
from backend.app.schemas.form_analysis import (
    FormMeasurementData,
    NormalizedFormIssue,
    ObservabilityStatus,
    HeuristicCategory,
)
from backend.app.seeds.corrective_mappings import (
    HEURISTIC_NAME_TO_ISSUE_ID,
    ISSUE_ID_TO_HEURISTIC_NAME,
    RAW_CORRECTIVE_MAPPINGS,
)
from backend.app.services.form_issue_normalizer import (
    HEURISTIC_TO_CATEGORY,
    FormIssueNormalizer,
)

logger = logging.getLogger(__name__)

# Canonical alias normalizations for test & client compatibility
HEURISTIC_ALIASES: Dict[str, str] = {
    "squat_torso_lean": "squat_torso_inclination",
    "squat_knee_valgus": "squat_knee_tracking",
    "torso_lean": "squat_torso_inclination",
    "knee_valgus": "squat_knee_tracking",
    "depth": "squat_depth",
}


# =============================================================================
# INPUT VALIDATION FUNCTIONS (FAIL-CLOSED)
# =============================================================================

def validate_numeric_confidence(confidence: Any) -> Tuple[bool, Optional[float], Optional[str]]:
    """
    Strict non-boolean numeric confidence validation.

    Rules:
    - Numeric int/float is allowed.
    - bool must NOT be accepted as numeric confidence (issubclass(bool, int) is True in Python).
    - Value must be finite (not NaN, not +Inf, not -Inf).
    - Value must be within inclusive range [0.0, 1.0].

    Returns:
        (is_valid, sanitized_confidence_or_None, failure_flag_or_None)
    """
    if confidence is None:
        return False, None, "FLAG_MISSING_CONFIDENCE"
    if isinstance(confidence, bool):
        return False, None, "FLAG_BOOLEAN_CONFIDENCE_PROHIBITED"
    if not isinstance(confidence, (int, float)):
        return False, None, "FLAG_INVALID_CONFIDENCE_TYPE"
    if math.isnan(confidence):
        return False, None, "FLAG_NAN_CONFIDENCE"
    if math.isinf(confidence):
        return False, None, "FLAG_INFINITE_CONFIDENCE"

    val = float(confidence)
    if val < 0.0 or val > 1.0:
        return False, None, "FLAG_OUT_OF_RANGE_CONFIDENCE"

    return True, val, None


def validate_boolean_acceptability(is_acceptable: Any) -> Tuple[bool, Optional[bool], Optional[str]]:
    """
    Strict boolean acceptability validation.

    Rules:
    - is_acceptable must be an actual boolean (True or False).
    - Do NOT coerce None, 0, 1, or strings such as "True"/"False", [], {}.

    Returns:
        (is_valid, boolean_value_or_None, failure_flag_or_None)
    """
    if is_acceptable is None:
        return False, None, "FLAG_NULL_ACCEPTABILITY"
    if not isinstance(is_acceptable, bool):
        return False, None, "FLAG_NON_BOOLEAN_ACCEPTABILITY"
    return True, is_acceptable, None


def validate_landmarks(landmarks: Any) -> Tuple[bool, Optional[str]]:
    """
    Validates MediaPipe landmark collection.

    Rules:
    - If provided, landmarks must contain at least 33 keypoints.

    Returns:
        (is_valid, failure_flag_or_None)
    """
    if landmarks is None:
        return False, "FLAG_MISSING_LANDMARKS"
    if hasattr(landmarks, "__len__") and len(landmarks) < 33:
        return False, "FLAG_MISSING_LANDMARKS"
    return True, None


def validate_measurement(measurement: Any) -> Tuple[bool, Optional[str]]:
    """
    Validates kinematic measurement payload.

    Rules:
    - observed_value and deviation, if present, must be finite numeric values.

    Returns:
        (is_valid, failure_flag_or_None)
    """
    if measurement is None:
        return True, None
    if isinstance(measurement, (int, float)):
        if isinstance(measurement, bool) or not math.isfinite(measurement):
            return False, "FLAG_KINEMATIC_MATH_ERROR"
        return True, None

    obs_val = getattr(measurement, "observed_value", None)
    if obs_val is None and isinstance(measurement, dict):
        obs_val = measurement.get("observed_value")
    if obs_val is not None:
        if isinstance(obs_val, bool) or not isinstance(obs_val, (int, float)) or not math.isfinite(obs_val):
            return False, "FLAG_KINEMATIC_MATH_ERROR"

    dev_val = getattr(measurement, "deviation", None)
    if dev_val is None and isinstance(measurement, dict):
        dev_val = measurement.get("deviation")
    if dev_val is not None:
        if isinstance(dev_val, bool) or not isinstance(dev_val, (int, float)) or not math.isfinite(dev_val):
            return False, "FLAG_KINEMATIC_MATH_ERROR"

    return True, None


# =============================================================================
# FIVE-WAY DETERMINISTIC CASCADING CLASSIFIER
# =============================================================================

def classify_repetition_observation(
    rep_obs: Any,
    min_confidence: float = 0.50,
) -> Tuple[ObservabilityCategory, List[str], Optional[float], Optional[bool]]:
    """
    Deterministic cascading 5-way partition for an individual repetition observation.

    Classification order:
    1. Landmark completeness (missing landmarks / len < 33 -> CATEGORY_NOT_OBSERVABLE)
    2. Occlusion (is_occluded is True -> CATEGORY_OCCLUDED)
    3. Confidence validity (None, bool, non-numeric, NaN, Inf, out-of-bounds -> CATEGORY_NOT_OBSERVABLE)
    4. Measurement validity (non-finite kinematic value -> CATEGORY_NOT_OBSERVABLE)
    5. Explicit unobserved status -> CATEGORY_NOT_OBSERVABLE
    6. Sub-threshold confidence (c < min_confidence -> CATEGORY_LOW_CONFIDENCE)
    7. Acceptability validity (None, non-boolean -> CATEGORY_NOT_OBSERVABLE)
    8. Observed acceptable vs defective (True -> CATEGORY_OBSERVED_ACCEPTABLE, False -> CATEGORY_OBSERVED_DEFECTIVE)

    Returns:
        (category, data_quality_flags, valid_confidence_or_None, is_acceptable_or_None)
    """
    flags: List[str] = []

    # Extract fields defensively
    if isinstance(rep_obs, dict):
        has_landmarks = "landmarks" in rep_obs
        raw_landmarks = rep_obs.get("landmarks")
        raw_confidence = rep_obs.get("confidence")
        raw_is_acceptable = rep_obs.get("is_acceptable")
        raw_measurement = rep_obs.get("measurement")
        is_occluded = rep_obs.get("is_occluded", False)
        raw_status = rep_obs.get("status")
    else:
        has_landmarks = hasattr(rep_obs, "landmarks")
        raw_landmarks = getattr(rep_obs, "landmarks", None)
        raw_confidence = getattr(rep_obs, "confidence", None)
        raw_is_acceptable = getattr(rep_obs, "is_acceptable", None)
        raw_measurement = getattr(rep_obs, "measurement", None)
        is_occluded = getattr(rep_obs, "is_occluded", False)
        raw_status = getattr(rep_obs, "status", None)

    # 1. Landmarks completeness
    if has_landmarks:
        lm_valid, lm_flag = validate_landmarks(raw_landmarks)
        if not lm_valid:
            if lm_flag:
                flags.append(lm_flag)
            return ObservabilityCategory.CATEGORY_NOT_OBSERVABLE, flags, None, None

    # 2. Joint Occlusion
    if is_occluded is True or (isinstance(raw_status, str) and raw_status.upper() in ("OCCLUDED", "CATEGORY_OCCLUDED")):
        flags.append("FLAG_OCCLUDED")
        return ObservabilityCategory.CATEGORY_OCCLUDED, flags, None, None

    # 3. Confidence validation
    conf_valid, conf_val, conf_flag = validate_numeric_confidence(raw_confidence)
    if not conf_valid:
        if conf_flag:
            flags.append(conf_flag)
        return ObservabilityCategory.CATEGORY_NOT_OBSERVABLE, flags, None, None

    # 4. Measurement validation
    meas_valid, meas_flag = validate_measurement(raw_measurement)
    if not meas_valid:
        if meas_flag:
            flags.append(meas_flag)
        return ObservabilityCategory.CATEGORY_NOT_OBSERVABLE, flags, None, None

    # 5. Explicit unobserved or invalid status
    if raw_status in (ObservabilityStatus.NOT_OBSERVABLE, ObservabilityStatus.INVALID, "NOT_OBSERVED", "NOT_OBSERVABLE", "CATEGORY_NOT_OBSERVABLE", "INVALID"):
        return ObservabilityCategory.CATEGORY_NOT_OBSERVABLE, flags, None, None

    # 6. Low Confidence floor
    if conf_val < min_confidence:
        flags.append("FLAG_SUBTHRESHOLD_CONFIDENCE")
        return ObservabilityCategory.CATEGORY_LOW_CONFIDENCE, flags, None, None

    # 7. Strict Boolean Acceptability
    acc_valid, acc_val, acc_flag = validate_boolean_acceptability(raw_is_acceptable)
    if not acc_valid:
        if acc_flag:
            flags.append(acc_flag)
        return ObservabilityCategory.CATEGORY_NOT_OBSERVABLE, flags, None, None

    # 8. Observed Acceptable vs Defective
    if acc_val is True:
        return ObservabilityCategory.CATEGORY_OBSERVED_ACCEPTABLE, flags, conf_val, True
    else:
        return ObservabilityCategory.CATEGORY_OBSERVED_DEFECTIVE, flags, conf_val, False


# =============================================================================
# IN-MEMORY SESSION EVIDENCE AGGREGATOR
# =============================================================================

class SessionEvidenceAggregator:
    """
    Pure in-memory aggregator transforming repetition-level technique evidence
    into deterministic SessionEvidenceRecord and SessionIssueSummary models.
    """

    def __init__(self, config: Optional[EvidenceAggregationConfig] = None) -> None:
        self.config = config or EvidenceAggregationConfig()
        self.normalizer = FormIssueNormalizer()

    def _resolve_issue_metadata(
        self, exercise_id: str, heuristic_or_issue: str
    ) -> Tuple[str, str, str]:
        """
        Deterministically resolves (issue_id, source_heuristic, category)
        for a given exercise and heuristic or issue name.
        """
        # Canonicalize alias if present
        h_name = HEURISTIC_ALIASES.get(heuristic_or_issue, heuristic_or_issue)

        # 1. If passed directly as a canonical issue_id
        if h_name in self.normalizer.get_all_valid_issue_ids():
            issue_id = h_name
            source_heuristic = ISSUE_ID_TO_HEURISTIC_NAME.get(issue_id, h_name)
            cat_enum = HEURISTIC_TO_CATEGORY.get(source_heuristic)
            category = cat_enum.value if cat_enum else "technique"
            return issue_id, source_heuristic, category

        # 2. Check (exercise_id, heuristic_name) mapping
        resolved_issue = HEURISTIC_NAME_TO_ISSUE_ID.get((exercise_id, h_name))
        if resolved_issue is not None:
            issue_id = resolved_issue
            source_heuristic = h_name
            cat_enum = HEURISTIC_TO_CATEGORY.get(source_heuristic)
            category = cat_enum.value if cat_enum else "technique"
            return issue_id, source_heuristic, category

        # 3. Fallback
        cat_enum = HEURISTIC_TO_CATEGORY.get(h_name)
        category = cat_enum.value if cat_enum else "technique"
        return h_name, h_name, category

    def classify_repetition(
        self, rep_obs: Any, heuristic_name: Optional[str] = None
    ) -> Tuple[ObservabilityCategory, List[str]]:
        """Public helper to classify an individual repetition observation."""
        cat, flags, _, _ = classify_repetition_observation(
            rep_obs, min_confidence=self.config.MIN_HEURISTIC_CONFIDENCE
        )
        return cat, flags

    def aggregate_heuristic(
        self,
        exercise_id: str,
        heuristic_name: str,
        rep_observations: List[Any],
        calculation_error: Optional[Exception] = None,
    ) -> SessionIssueSummary:
        """
        Aggregates repetition observations for a single technique heuristic.

        Enforces:
        - 5-way partition mutual exclusivity
        - sum(categories) == target_reps_total
        - defect_rate = defective / observed (None if observed == 0)
        - mean_confidence = arithmetic mean across observed reps (None if observed == 0)
        - fail-closed calculation status on unhandled errors
        """
        issue_id, source_heuristic, category = self._resolve_issue_metadata(
            exercise_id, heuristic_name
        )

        # 1. Calculation failure injection or unhandled error
        if calculation_error is not None:
            logger.warning(
                f"Heuristic calculation error recorded for {source_heuristic}: {calculation_error}"
            )
            return SessionIssueSummary(
                issue_id=issue_id,
                source_heuristic=source_heuristic,
                category=category,
                calculation_status=CalculationStatus.FAILED,
                data_quality_flags=["ERROR_HEURISTIC_CALCULATION_FAILED"],
                target_reps_total=len(rep_observations),
                target_reps_observed=0,
                target_reps_defective=0,
                target_reps_occluded=0,
                target_reps_low_confidence=0,
                target_reps_not_observable=0,
                target_reps_used_for_defect_rate=0,
                defect_rate=None,
                mean_confidence=None,
                representative_measurement=None,
                sample_feedback=[],
            )

        # 2. Empty input handling
        target_reps_total = len(rep_observations)
        if target_reps_total == 0:
            return SessionIssueSummary(
                issue_id=issue_id,
                source_heuristic=source_heuristic,
                category=category,
                calculation_status=CalculationStatus.INSUFFICIENT_INPUT,
                data_quality_flags=["FLAG_INSUFFICIENT_INPUT"],
                target_reps_total=0,
                target_reps_observed=0,
                target_reps_defective=0,
                target_reps_occluded=0,
                target_reps_low_confidence=0,
                target_reps_not_observable=0,
                target_reps_used_for_defect_rate=0,
                defect_rate=None,
                mean_confidence=None,
                representative_measurement=None,
                sample_feedback=[],
            )

        # 3. Process observations through the 5-way partition
        c_not_observable = 0
        c_occluded = 0
        c_low_confidence = 0
        c_observed_acceptable = 0
        c_observed_defective = 0
        observed_confidences: List[float] = []
        data_quality_flags: List[str] = []
        sample_feedback: List[str] = []
        representative_measurement: Optional[FormMeasurementData] = None

        try:
            for rep_obs in rep_observations:
                # Catch simulated or embedded exceptions
                if isinstance(rep_obs, Exception):
                    raise rep_obs
                if isinstance(rep_obs, dict) and rep_obs.get("calculation_error") is not None:
                    raise RuntimeError(str(rep_obs["calculation_error"]))

                cat, flags, conf, acc = classify_repetition_observation(
                    rep_obs, min_confidence=self.config.MIN_HEURISTIC_CONFIDENCE
                )
                for f in flags:
                    if f not in data_quality_flags:
                        data_quality_flags.append(f)

                if cat == ObservabilityCategory.CATEGORY_NOT_OBSERVABLE:
                    c_not_observable += 1
                elif cat == ObservabilityCategory.CATEGORY_OCCLUDED:
                    c_occluded += 1
                elif cat == ObservabilityCategory.CATEGORY_LOW_CONFIDENCE:
                    c_low_confidence += 1
                elif cat == ObservabilityCategory.CATEGORY_OBSERVED_ACCEPTABLE:
                    c_observed_acceptable += 1
                    if conf is not None:
                        observed_confidences.append(conf)
                elif cat == ObservabilityCategory.CATEGORY_OBSERVED_DEFECTIVE:
                    c_observed_defective += 1
                    if conf is not None:
                        observed_confidences.append(conf)

                # Extract sample feedback
                fb = None
                if isinstance(rep_obs, dict):
                    fb = rep_obs.get("feedback")
                elif hasattr(rep_obs, "feedback"):
                    fb = getattr(rep_obs, "feedback")
                if fb and isinstance(fb, str) and fb.strip() and fb.strip() not in sample_feedback:
                    sample_feedback.append(fb.strip())

                # Extract representative measurement
                if representative_measurement is None:
                    meas = None
                    if isinstance(rep_obs, dict):
                        meas = rep_obs.get("measurement")
                    elif hasattr(rep_obs, "measurement"):
                        meas = getattr(rep_obs, "measurement")
                    if meas is not None:
                        if isinstance(meas, FormMeasurementData):
                            representative_measurement = meas
                        elif isinstance(meas, dict):
                            try:
                                representative_measurement = FormMeasurementData(**meas)
                            except Exception:
                                pass

        except Exception as exc:
            logger.exception(f"Unhandled calculation error in heuristic {heuristic_name}: {exc}")
            return SessionIssueSummary(
                issue_id=issue_id,
                source_heuristic=source_heuristic,
                category=category,
                calculation_status=CalculationStatus.FAILED,
                data_quality_flags=["ERROR_HEURISTIC_CALCULATION_FAILED"],
                target_reps_total=target_reps_total,
                target_reps_observed=0,
                target_reps_defective=0,
                target_reps_occluded=0,
                target_reps_low_confidence=0,
                target_reps_not_observable=0,
                target_reps_used_for_defect_rate=0,
                defect_rate=None,
                mean_confidence=None,
                representative_measurement=None,
                sample_feedback=[],
            )

        # 4. Partition invariant verification
        target_reps_observed = c_observed_acceptable + c_observed_defective
        target_reps_defective = c_observed_defective
        target_reps_used_for_defect_rate = target_reps_observed

        partition_sum = (
            c_not_observable + c_occluded + c_low_confidence + target_reps_observed
        )
        if partition_sum != target_reps_total:
            raise ValueError(
                f"Five-way partition invariant violated for {heuristic_name}: "
                f"sum({c_not_observable}+{c_occluded}+{c_low_confidence}+{target_reps_observed}) "
                f"!= total({target_reps_total})"
            )

        # 5. Defect rate computation
        if target_reps_observed > 0:
            defect_rate = float(target_reps_defective) / float(target_reps_observed)
        else:
            defect_rate = None

        # 6. Mean confidence computation
        if len(observed_confidences) > 0:
            mean_confidence = sum(observed_confidences) / len(observed_confidences)
        else:
            mean_confidence = None

        return SessionIssueSummary(
            issue_id=issue_id,
            source_heuristic=source_heuristic,
            category=category,
            calculation_status=CalculationStatus.SUCCESS,
            data_quality_flags=data_quality_flags,
            target_reps_total=target_reps_total,
            target_reps_observed=target_reps_observed,
            target_reps_defective=target_reps_defective,
            target_reps_occluded=c_occluded,
            target_reps_low_confidence=c_low_confidence,
            target_reps_not_observable=c_not_observable,
            target_reps_used_for_defect_rate=target_reps_used_for_defect_rate,
            defect_rate=defect_rate,
            mean_confidence=mean_confidence,
            representative_measurement=representative_measurement,
            sample_feedback=sample_feedback,
        )

    def aggregate_session(
        self,
        session_data: Any = None,
        exercise_id: Optional[str] = None,
        user_id: Optional[str] = None,
        session_id: Optional[str] = None,
        completed_at: Optional[str] = None,
        reps: Optional[List[Any]] = None,
        heuristics_data: Optional[Dict[str, List[Any]]] = None,
        heuristic_errors: Optional[Dict[str, Exception]] = None,
        total_reps: Optional[int] = None,
        valid_reps: Optional[int] = None,
        session_observability_ratio: Optional[float] = None,
        provenance_tier: ProvenanceTier = ProvenanceTier.TIER_1_NORMALIZED,
        **kwargs: Any,
    ) -> SessionEvidenceRecord:
        """
        Aggregates a complete workout session's technique evidence into a SessionEvidenceRecord.

        Handles:
        - Multi-heuristic aggregation with deterministic issue-level statuses.
        - Session-level calculation status determination:
            * All issue calculations succeed -> SUCCESS
            * At least one succeeds and at least one fails -> PARTIAL_FAILURE
            * All calculations fail -> FAILED
            * Zero total reps or insufficient inputs -> INSUFFICIENT_INPUT
        - T19 Multi-Heuristic Failure Isolation: failed heuristics remain isolated and
          do not discard or taint successful issue evidence.
        - Computes session observability ratio and trend eligibility.
        """
        # 1. Resolve session metadata
        s_id = session_id
        u_id = user_id
        ex_id = exercise_id
        comp_at = completed_at
        p_tier = provenance_tier

        if session_data is not None:
            if isinstance(session_data, dict):
                s_id = s_id or session_data.get("session_id")
                u_id = u_id or session_data.get("user_id")
                ex_id = ex_id or session_data.get("exercise_id") or session_data.get("canonical_exercise_id")
                comp_at = comp_at or session_data.get("completed_at")
                if "provenance_tier" in session_data:
                    p_tier = session_data["provenance_tier"]
                if reps is None and "reps" in session_data:
                    reps = session_data["reps"]
                if heuristics_data is None and "heuristics_data" in session_data:
                    heuristics_data = session_data["heuristics_data"]
                if total_reps is None and "total_reps" in session_data:
                    total_reps = session_data["total_reps"]
                if valid_reps is None and "valid_reps" in session_data:
                    valid_reps = session_data["valid_reps"]
                if session_observability_ratio is None and "session_observability_ratio" in session_data:
                    session_observability_ratio = session_data["session_observability_ratio"]
            else:
                s_id = s_id or getattr(session_data, "session_id", None)
                u_id = u_id or getattr(session_data, "user_id", None)
                ex_id = ex_id or getattr(session_data, "exercise_id", None) or getattr(session_data, "canonical_exercise_id", None)
                comp_at = comp_at or getattr(session_data, "completed_at", None)
                if hasattr(session_data, "provenance_tier"):
                    p_tier = getattr(session_data, "provenance_tier")
                if reps is None and hasattr(session_data, "reps"):
                    reps = getattr(session_data, "reps")
                if total_reps is None and hasattr(session_data, "total_reps"):
                    total_reps = getattr(session_data, "total_reps")
                if valid_reps is None and hasattr(session_data, "valid_reps"):
                    valid_reps = getattr(session_data, "valid_reps")
                if session_observability_ratio is None and hasattr(session_data, "session_observability_ratio"):
                    session_observability_ratio = getattr(session_data, "session_observability_ratio")

        s_id = s_id or f"sess_{uuid.uuid4().hex[:12]}"
        u_id = u_id or "user_default"
        ex_id = ex_id or "ex_squat"
        comp_at = comp_at or datetime.now(timezone.utc).isoformat()

        # Handle complete calculation failure simulation or corrupted session state (T20)
        if kwargs.get("force_session_failure") or (session_data and isinstance(session_data, dict) and session_data.get("corrupted_state")):
            return SessionEvidenceRecord(
                session_id=s_id,
                user_id=u_id,
                exercise_id=ex_id,
                completed_at=comp_at,
                total_reps=total_reps or 0,
                valid_reps=0,
                session_observability_ratio=0.0,
                is_eligible_for_trends=False,
                calculation_status=CalculationStatus.FAILED,
                data_quality_flags=["ERROR_SESSION_CALCULATION_FAILED"],
                provenance_tier=p_tier,
                issues={},
                normalized_issues=[],
            )

        # 2. Organize heuristic input data
        heuristic_map: Dict[str, List[Any]] = {}

        if heuristics_data:
            heuristic_map = {k: list(v) for k, v in heuristics_data.items()}
        elif reps is not None:
            # Reps is a list of repetition payloads
            for rep_idx, rep in enumerate(reps):
                if isinstance(rep, dict):
                    # Check if rep provides a dict of heuristics
                    if "heuristics" in rep and isinstance(rep["heuristics"], dict):
                        for h_name, h_obs in rep["heuristics"].items():
                            heuristic_map.setdefault(h_name, []).append(h_obs)
                    elif "heuristic_results" in rep and isinstance(rep["heuristic_results"], dict):
                        for h_name, h_obs in rep["heuristic_results"].items():
                            heuristic_map.setdefault(h_name, []).append(h_obs)
                    elif "heuristic_name" in rep:
                        # Single heuristic observation represented as rep
                        h_name = rep["heuristic_name"]
                        heuristic_map.setdefault(h_name, []).append(rep)
                    else:
                        # Rep may contain NormalizedFormIssue objects
                        pass
                elif isinstance(rep, list):
                    for item in rep:
                        h_name = getattr(item, "source_heuristic", None)
                        if h_name:
                            heuristic_map.setdefault(h_name, []).append(item)
                elif hasattr(rep, "source_heuristic"):
                    h_name = getattr(rep, "source_heuristic")
                    heuristic_map.setdefault(h_name, []).append(rep)

        # 3. Determine rep counts
        calculated_total_reps = len(reps) if reps is not None else 0
        if calculated_total_reps == 0 and heuristic_map:
            calculated_total_reps = max(len(v) for v in heuristic_map.values())
        if total_reps is None:
            total_reps = calculated_total_reps

        # 4. Check for Empty Evidence Input (T01)
        if total_reps == 0 or (reps is not None and len(reps) == 0 and not heuristic_map):
            return SessionEvidenceRecord(
                session_id=s_id,
                user_id=u_id,
                exercise_id=ex_id,
                completed_at=comp_at,
                total_reps=0,
                valid_reps=0,
                session_observability_ratio=0.0,
                is_eligible_for_trends=False,
                calculation_status=CalculationStatus.INSUFFICIENT_INPUT,
                data_quality_flags=["FLAG_INSUFFICIENT_INPUT"],
                provenance_tier=p_tier,
                issues={},
                normalized_issues=[],
            )

        # 5. Process each heuristic
        issue_summaries: Dict[str, SessionIssueSummary] = {}
        session_quality_flags: List[str] = []
        normalized_issues_collected: List[NormalizedFormIssue] = []

        h_errors = heuristic_errors or {}

        for h_name, h_reps in heuristic_map.items():
            h_err = h_errors.get(h_name)
            summary = self.aggregate_heuristic(
                exercise_id=ex_id,
                heuristic_name=h_name,
                rep_observations=h_reps,
                calculation_error=h_err,
            )
            issue_summaries[summary.issue_id] = summary

            for flag in summary.data_quality_flags:
                if flag not in session_quality_flags:
                    session_quality_flags.append(flag)

        # 6. Session-level calculation status determination
        if not issue_summaries:
            session_status = CalculationStatus.INSUFFICIENT_INPUT
        else:
            statuses = [s.calculation_status for s in issue_summaries.values()]
            has_success = any(st == CalculationStatus.SUCCESS for st in statuses)
            has_failed = any(st == CalculationStatus.FAILED for st in statuses)
            all_failed = all(st == CalculationStatus.FAILED for st in statuses)
            all_insufficient = all(st == CalculationStatus.INSUFFICIENT_INPUT for st in statuses)

            if all_insufficient:
                session_status = CalculationStatus.INSUFFICIENT_INPUT
            elif all_failed:
                session_status = CalculationStatus.FAILED
            elif has_success and has_failed:
                session_status = CalculationStatus.PARTIAL_FAILURE
            else:
                session_status = CalculationStatus.SUCCESS

        # 7. Session observability ratio & valid reps computation
        total_eval_reps = sum(s.target_reps_total for s in issue_summaries.values())
        total_obs_reps = sum(s.target_reps_observed for s in issue_summaries.values())

        if total_eval_reps > 0:
            calc_obs_ratio = round(total_obs_reps / total_eval_reps, 4)
        else:
            calc_obs_ratio = 0.0

        if session_observability_ratio is None:
            session_observability_ratio = calc_obs_ratio

        if valid_reps is None:
            if total_reps > 0:
                valid_reps = round(total_reps * min(1.0, session_observability_ratio))
            else:
                valid_reps = 0

        # 8. Trends eligibility gate
        is_eligible_for_trends = (
            valid_reps >= self.config.MIN_VALID_REPS_PER_SESSION
            and session_observability_ratio >= self.config.MIN_SESSION_OBSERVABILITY_RATIO
            and session_status != CalculationStatus.FAILED
        )

        return SessionEvidenceRecord(
            session_id=s_id,
            user_id=u_id,
            exercise_id=ex_id,
            completed_at=comp_at,
            total_reps=total_reps,
            valid_reps=valid_reps,
            session_observability_ratio=session_observability_ratio,
            is_eligible_for_trends=is_eligible_for_trends,
            calculation_status=session_status,
            data_quality_flags=session_quality_flags,
            provenance_tier=p_tier,
            issues=issue_summaries,
            normalized_issues=normalized_issues_collected,
        )
