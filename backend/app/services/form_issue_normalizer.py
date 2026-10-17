"""
Authoritative Form Issue Normalizer Service (Phase 9C.6.1).

Provides:
- Deterministic normalization of raw MediaPipe visual heuristic observations
  into standardized, catalog-aligned `NormalizedFormIssue` records.
- Canonical alignment of all 25 visual heuristics across the 5 canonical exercises
  (ex_squat, ex_bench_press, ex_deadlift, ex_bicep_curl, ex_shoulder_press) to the
  15 canonical issue IDs defined in `backend/app/seeds/corrective_mappings.py`.
- Type-safe, polymorphic measurement normalization across all 6 supported dimensions:
  'degrees', 'ratio', 'normalized_offset', 'percent_difference', 'variance', 'unitless'.
- Strict non-medical safety boundaries: zero diagnostic claims, zero injury guarantees,
  and active sanitization/validation against `PROHIBITED_MEDICAL_PHRASES`.
- Observability preservation: unobserved or low-confidence heuristics are NEVER
  treated as defects (MISSING DATA != BAD FORM).
- Robust legacy defect string normalization supporting provenanced scoring defects
  while strictly rejecting unprovenanced, vague natural language strings.
"""

import math
import logging
from enum import Enum
from typing import Dict, List, Optional, Set, Tuple, Union, Any, Literal

from backend.app.schemas.exercise import (
    CANONICAL_CV_EXERCISES,
    PROHIBITED_MEDICAL_PHRASES,
)
from backend.app.schemas.form_analysis import (
    ObservabilityStatus,
    HeuristicCategory,
    FormMeasurementData,
    NormalizedFormIssue,
    NormalizedFormIssueSchema,
    VALID_ISSUE_IDS,
    MeasurementUnit,
)
from backend.app.seeds.corrective_mappings import (
    HEURISTIC_NAME_TO_ISSUE_ID,
    ISSUE_ID_TO_HEURISTIC_NAME,
    RAW_CORRECTIVE_MAPPINGS,
)

logger = logging.getLogger(__name__)

# =============================================================================
# DETERMINISTIC CANONICAL LOOKUP TABLES
# =============================================================================

HEURISTIC_TO_CATEGORY: Dict[str, HeuristicCategory] = {
    # Squat (ex_squat)
    "squat_depth": HeuristicCategory.ROM,
    "squat_torso_inclination": HeuristicCategory.TECHNIQUE,
    "squat_knee_tracking": HeuristicCategory.TECHNIQUE,
    "squat_knee_symmetry": HeuristicCategory.SYMMETRY,
    "squat_movement_stability": HeuristicCategory.STABILITY,
    # Bench Press (ex_bench_press)
    "bench_elbow_rom": HeuristicCategory.ROM,
    "bench_elbow_flare": HeuristicCategory.TECHNIQUE,
    "bench_elbow_symmetry": HeuristicCategory.SYMMETRY,
    "bench_movement_stability": HeuristicCategory.STABILITY,
    # Deadlift (ex_deadlift)
    "deadlift_hip_lockout": HeuristicCategory.ROM,
    "deadlift_hip_knee_sequencing": HeuristicCategory.TECHNIQUE,
    "deadlift_torso_angle": HeuristicCategory.TECHNIQUE,
    "deadlift_body_center_stability": HeuristicCategory.TECHNIQUE,
    "deadlift_hip_symmetry": HeuristicCategory.SYMMETRY,
    "deadlift_movement_stability": HeuristicCategory.STABILITY,
    # Bicep Curl (ex_bicep_curl)
    "curl_elbow_rom": HeuristicCategory.ROM,
    "curl_upper_arm_drift": HeuristicCategory.TECHNIQUE,
    "curl_torso_momentum": HeuristicCategory.TECHNIQUE,
    "curl_elbow_symmetry": HeuristicCategory.SYMMETRY,
    "curl_movement_stability": HeuristicCategory.STABILITY,
    # Shoulder Press (ex_shoulder_press)
    "shoulder_press_lockout": HeuristicCategory.ROM,
    "shoulder_press_forearm_verticality": HeuristicCategory.TECHNIQUE,
    "shoulder_press_torso_lean": HeuristicCategory.TECHNIQUE,
    "shoulder_press_elbow_symmetry": HeuristicCategory.SYMMETRY,
    "shoulder_press_movement_stability": HeuristicCategory.STABILITY,
}

HEURISTIC_TO_DEFAULT_UNIT: Dict[str, MeasurementUnit] = {
    # Squat
    "squat_depth": "degrees",
    "squat_torso_inclination": "degrees",
    "squat_knee_tracking": "ratio",
    "squat_knee_symmetry": "percent_difference",
    "squat_movement_stability": "variance",
    # Bench Press
    "bench_elbow_rom": "degrees",
    "bench_elbow_flare": "degrees",
    "bench_elbow_symmetry": "percent_difference",
    "bench_movement_stability": "variance",
    # Deadlift
    "deadlift_hip_lockout": "degrees",
    "deadlift_hip_knee_sequencing": "unitless",
    "deadlift_torso_angle": "degrees",
    "deadlift_body_center_stability": "normalized_offset",
    "deadlift_hip_symmetry": "percent_difference",
    "deadlift_movement_stability": "variance",
    # Bicep Curl
    "curl_elbow_rom": "degrees",
    "curl_upper_arm_drift": "normalized_offset",
    "curl_torso_momentum": "degrees",
    "curl_elbow_symmetry": "percent_difference",
    "curl_movement_stability": "variance",
    # Shoulder Press
    "shoulder_press_lockout": "degrees",
    "shoulder_press_forearm_verticality": "degrees",
    "shoulder_press_torso_lean": "degrees",
    "shoulder_press_elbow_symmetry": "percent_difference",
    "shoulder_press_movement_stability": "variance",
}

SAFE_NON_MEDICAL_FALLBACK = "Technique adjustment recommended based on observed movement pattern."


def normalize_measurement_unit(
    raw_unit: Optional[str],
    heuristic_name: Optional[str] = None,
) -> MeasurementUnit:
    """
    Normalizes arbitrary unit strings from MediaPipe heuristic evaluation
    to the 6 canonical measurement units.
    """
    default_unit: MeasurementUnit = "degrees"
    if heuristic_name and heuristic_name in HEURISTIC_TO_DEFAULT_UNIT:
        default_unit = HEURISTIC_TO_DEFAULT_UNIT[heuristic_name]

    if not raw_unit:
        return default_unit

    u = raw_unit.strip().lower()
    if u in ("degrees", "deg", "°", "angle"):
        return "degrees"
    if u in ("ratio", "ratio_units"):
        return "ratio"
    if u in ("normalized_offset", "norm_units", "normalized_units", "offset", "centroid_drift"):
        return "normalized_offset"
    if u in ("percent_difference", "pct", "%", "percent", "percentage", "symmetry_delta"):
        return "percent_difference"
    if u in ("variance", "var", "stability_variance", "cv"):
        return "variance"
    if u in ("unitless", "none", "timing", "frames", "ms"):
        return "unitless"

    return default_unit


def sanitize_feedback_message(feedback: Optional[str]) -> str:
    """
    Enforces the non-medical safety boundary on technique feedback strings.
    If prohibited medical phrases are detected, replaces with an engineering-compliant fallback.
    """
    if not feedback or not feedback.strip():
        return SAFE_NON_MEDICAL_FALLBACK

    cleaned = feedback.strip()
    lower = cleaned.lower()
    for phrase in PROHIBITED_MEDICAL_PHRASES:
        if phrase in lower:
            logger.warning(
                f"Prohibited medical phrase detected in form feedback: '{phrase}'. "
                "Sanitizing to safe technical fallback."
            )
            return SAFE_NON_MEDICAL_FALLBACK

    return cleaned


# =============================================================================
# FORM ISSUE NORMALIZER SERVICE
# =============================================================================

class FormIssueNormalizer:
    """
    Service responsible for converting individual heuristic outputs, full form reports,
    and legacy defect strings into canonical NormalizedFormIssue schemas.
    """

    def __init__(self) -> None:
        self._mappings = HEURISTIC_NAME_TO_ISSUE_ID
        self._reverse_mappings = ISSUE_ID_TO_HEURISTIC_NAME
        self._valid_issues = VALID_ISSUE_IDS
        self._canonical_exercises = set(CANONICAL_CV_EXERCISES.keys())

    def get_canonical_issue_id(self, exercise_id: str, heuristic_name: str) -> Optional[str]:
        """Returns the canonical issue_id for an (exercise_id, heuristic_name) pair, or None."""
        return self._mappings.get((exercise_id, heuristic_name))

    def get_all_valid_issue_ids(self) -> Set[str]:
        """Returns the complete set of 15 canonical issue IDs."""
        return set(self._valid_issues)

    def get_mapped_heuristics_for_exercise(self, exercise_id: str) -> List[str]:
        """Returns the sorted list of mapped heuristics for a canonical CV exercise."""
        return sorted([
            h_name for (ex_id, h_name) in self._mappings.keys()
            if ex_id == exercise_id
        ])

    def is_valid_heuristic_for_exercise(self, exercise_id: str, heuristic_name: str) -> bool:
        """Returns True if the heuristic is mapped for the given canonical exercise."""
        return (exercise_id, heuristic_name) in self._mappings

    def normalize_heuristic_result(
        self,
        result: Any,
        rep_index: Optional[int] = None,
        movement_phase: Optional[str] = None,
    ) -> Optional[NormalizedFormIssue]:
        """
        Normalizes a FormHeuristicResult, FormHeuristicResultSchema, or dictionary
        into a canonical NormalizedFormIssue. Returns None if mapping is invalid.
        """
        if result is None:
            return None

        # 1. Extract fields defensively from dataclass, Pydantic model, or dict
        if isinstance(result, dict):
            exercise_id = result.get("exercise_id")
            heuristic_name = result.get("heuristic_name")
            category_raw = result.get("category")
            status_raw = result.get("status")
            is_acceptable = result.get("is_acceptable")
            observed_value = result.get("observed_value")
            reference_value = result.get("reference_value")
            deviation = result.get("deviation")
            confidence = result.get("confidence", 0.0)
            feedback = result.get("feedback", "")
            unit_raw = result.get("unit")
            rep_idx = result.get("rep_index", rep_index)
            phase = result.get("movement_phase", movement_phase)
        else:
            exercise_id = getattr(result, "exercise_id", None)
            heuristic_name = getattr(result, "heuristic_name", None)
            category_raw = getattr(result, "category", None)
            status_raw = getattr(result, "status", None)
            is_acceptable = getattr(result, "is_acceptable", None)
            observed_value = getattr(result, "observed_value", None)
            reference_value = getattr(result, "reference_value", None)
            deviation = getattr(result, "deviation", None)
            confidence = getattr(result, "confidence", 0.0)
            feedback = getattr(result, "feedback", "")
            unit_raw = getattr(result, "unit", None)
            rep_idx = getattr(result, "rep_index", rep_index)
            phase = getattr(result, "movement_phase", movement_phase)

        if not exercise_id or not heuristic_name:
            return None

        if exercise_id not in self._canonical_exercises:
            return None

        issue_id = self.get_canonical_issue_id(exercise_id, heuristic_name)
        if not issue_id:
            return None

        # 2. Resolve ObservabilityStatus
        status: ObservabilityStatus
        if isinstance(status_raw, ObservabilityStatus):
            status = status_raw
        elif isinstance(status_raw, str):
            try:
                status = ObservabilityStatus(status_raw)
            except ValueError:
                status = ObservabilityStatus.INVALID
        else:
            status = ObservabilityStatus.INVALID

        # 3. Resolve HeuristicCategory
        category: HeuristicCategory
        if isinstance(category_raw, HeuristicCategory):
            category = category_raw
        elif isinstance(category_raw, str):
            matched = False
            for cat in HeuristicCategory:
                if category_raw in (cat.value, cat.name):
                    category = cat
                    matched = True
                    break
            if not matched:
                category = HEURISTIC_TO_CATEGORY.get(heuristic_name, HeuristicCategory.TECHNIQUE)
        else:
            category = HEURISTIC_TO_CATEGORY.get(heuristic_name, HeuristicCategory.TECHNIQUE)

        # 4. Filter invalid numerical anomalies (NaN, Inf)
        if observed_value is not None:
            try:
                if math.isnan(observed_value) or math.isinf(observed_value):
                    observed_value = None
                    status = ObservabilityStatus.INVALID
            except TypeError:
                observed_value = None

        if deviation is not None:
            try:
                if math.isnan(deviation) or math.isinf(deviation):
                    deviation = None
            except TypeError:
                deviation = None

        # 5. Format reference_value
        ref_val: Optional[Union[float, List[float]]] = None
        if isinstance(reference_value, (list, tuple)):
            clean_list: List[float] = []
            for v in reference_value:
                try:
                    vf = float(v)
                    if not (math.isnan(vf) or math.isinf(vf)):
                        clean_list.append(round(vf, 2))
                except (TypeError, ValueError):
                    pass
            if clean_list:
                ref_val = clean_list
        elif isinstance(reference_value, (int, float)):
            try:
                vf = float(reference_value)
                if not (math.isnan(vf) or math.isinf(vf)):
                    ref_val = round(vf, 2)
            except (TypeError, ValueError):
                pass

        # 6. Resolve MeasurementUnit and construct FormMeasurementData
        measurement_unit = normalize_measurement_unit(unit_raw, heuristic_name)
        measurement: Optional[FormMeasurementData] = None
        if observed_value is not None or ref_val is not None or deviation is not None:
            measurement = FormMeasurementData(
                unit=measurement_unit,
                observed_value=round(observed_value, 2) if observed_value is not None else None,
                reference_value=ref_val,
                deviation=round(deviation, 2) if deviation is not None else None,
            )

        # 7. Clamp confidence and sanitize feedback
        clamped_conf = max(0.0, min(1.0, float(confidence or 0.0)))
        safe_feedback = sanitize_feedback_message(feedback)

        return NormalizedFormIssue(
            exercise_id=exercise_id,
            issue_id=issue_id,
            source_heuristic=heuristic_name,
            category=category,
            status=status,
            is_acceptable=is_acceptable,
            confidence=round(clamped_conf, 3),
            measurement=measurement,
            rep_index=rep_idx,
            movement_phase=phase,
            feedback=safe_feedback,
        )

    def normalize_form_report(
        self,
        report: Any,
        rep_index: Optional[int] = None,
        defects_only: bool = False,
    ) -> List[NormalizedFormIssue]:
        """
        Normalizes all heuristic results contained in an ExerciseFormReport or
        ExerciseFormReportSchema into a list of NormalizedFormIssue items.

        CRITICAL ARCHITECTURAL GUARDRAIL:
        If `defects_only=True`, an issue is included ONLY when:
          1. status == ObservabilityStatus.OBSERVED
          2. is_acceptable is False
        Missing data, low confidence, or unobservable statuses are NEVER treated as defects.
        """
        if report is None:
            return []

        if isinstance(report, dict):
            raw_results = report.get("results", [])
        else:
            raw_results = getattr(report, "results", [])

        normalized_issues: List[NormalizedFormIssue] = []
        for raw in raw_results:
            issue = self.normalize_heuristic_result(raw, rep_index=rep_index)
            if issue is None:
                continue

            if defects_only:
                # Strictly evaluate acceptable flag only under full observability
                if issue.status == ObservabilityStatus.OBSERVED and issue.is_acceptable is False:
                    normalized_issues.append(issue)
            else:
                normalized_issues.append(issue)

        return normalized_issues

    def normalize_defect_string(
        self,
        exercise_id: str,
        defect_str: str,
        rep_index: Optional[int] = None,
        confidence: float = 1.0,
    ) -> Optional[NormalizedFormIssue]:
        """
        Normalizes a contributing defect string from a RepetitionScore into a NormalizedFormIssue.
        Example strings:
          - 'squat_depth: Squat depth was above parallel (85.2° vs 90.0° required).'
          - 'bench_elbow_flare penalty: 25.0'
          - 'squat_depth'

        LEGACY SAFETY RULE:
        Never infer canonical issue IDs from unprovenanced natural-language strings
        (e.g., 'Good execution with minor adjustments observed.'). If the string cannot be
        deterministically attributed to a mapped heuristic for this exercise, returns None.
        """
        if not defect_str or not exercise_id or exercise_id not in self._canonical_exercises:
            return None

        clean_str = defect_str.strip()
        mapped_heuristics = self.get_mapped_heuristics_for_exercise(exercise_id)

        matched_heuristic: Optional[str] = None
        extracted_feedback: str = ""

        # Deterministic match against mapped heuristics for this exercise
        for h_name in mapped_heuristics:
            if clean_str == h_name:
                matched_heuristic = h_name
                extracted_feedback = f"Technique adjustment observed for {h_name.replace('_', ' ')}."
                break
            elif clean_str.startswith(f"{h_name}:"):
                matched_heuristic = h_name
                extracted_feedback = clean_str[len(f"{h_name}:"):].strip()
                break
            elif clean_str.startswith(f"{h_name} "):
                matched_heuristic = h_name
                extracted_feedback = clean_str[len(h_name):].strip()
                break

        if not matched_heuristic:
            # Unprovenanced or non-matching text - reject per Section 9.2 safety rules
            return None

        issue_id = self.get_canonical_issue_id(exercise_id, matched_heuristic)
        if not issue_id:
            return None

        category = HEURISTIC_TO_CATEGORY.get(matched_heuristic, HeuristicCategory.TECHNIQUE)
        safe_feedback = sanitize_feedback_message(extracted_feedback)
        clamped_conf = max(0.0, min(1.0, float(confidence)))

        return NormalizedFormIssue(
            exercise_id=exercise_id,
            issue_id=issue_id,
            source_heuristic=matched_heuristic,
            category=category,
            status=ObservabilityStatus.OBSERVED,
            is_acceptable=False,
            confidence=round(clamped_conf, 3),
            measurement=None,
            rep_index=rep_index,
            feedback=safe_feedback,
        )


# =============================================================================
# SINGLETON INSTANCE ACCESSOR
# =============================================================================

_normalizer_instance: Optional[FormIssueNormalizer] = None


def get_form_issue_normalizer() -> FormIssueNormalizer:
    """Returns the singleton instance of FormIssueNormalizer."""
    global _normalizer_instance
    if _normalizer_instance is None:
        _normalizer_instance = FormIssueNormalizer()
    return _normalizer_instance
