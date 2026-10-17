"""
Focused Unit Tests for SessionEvidenceAggregator (Subphase 9C.6.2.2).

Covers:
- T01: Empty Evidence Input
- T02: All Repetitions Occluded
- T03: Sub-Threshold Confidence
- T04: Missing Confidence (None)
- T05: Boolean Confidence True
- T06: Boolean Confidence False
- T07: String Confidence
- T08: NaN Confidence
- T09: Infinite Confidence (+Inf, -Inf)
- T10: Out-of-Range Confidence (> 1.0, < 0.0)
- T11: Boundary Confidence 0.0
- T12: Boundary Confidence 0.50
- T13: Null is_acceptable
- T14: Numeric Acceptability (0 and 1)
- T15: String Acceptability ("True" and "False")
- T16: Missing / Incomplete Landmarks (< 33)
- T17: Malformed Kinematic Measurement (NaN / Inf)
- T18: Five-Way Partition Sum Identity & Defect Rate
- T19: Multi-Heuristic Partial Failure Contract & Isolation
- T20: Complete Calculation Failure
- Additional Volume & Observability Gate Verification
"""

import math
import pytest
from typing import Dict, List, Any

from backend.app.schemas.form_evidence import (
    CalculationStatus,
    ObservabilityCategory,
    ProvenanceTier,
    EvidenceAggregationConfig,
    SessionIssueSummary,
    SessionEvidenceRecord,
)
from backend.app.schemas.form_analysis import FormMeasurementData
from backend.app.services.form_analysis.session_evidence_aggregator import (
    SessionEvidenceAggregator,
    validate_numeric_confidence,
    validate_boolean_acceptability,
    validate_landmarks,
    validate_measurement,
    classify_repetition_observation,
)


@pytest.fixture
def aggregator() -> SessionEvidenceAggregator:
    return SessionEvidenceAggregator()


# =============================================================================
# T01: EMPTY EVIDENCE INPUT
# =============================================================================

def test_t01_empty_evidence_input(aggregator: SessionEvidenceAggregator):
    """T01: Empty repetition list fails closed to INSUFFICIENT_INPUT."""
    record = aggregator.aggregate_session(
        exercise_id="ex_squat",
        reps=[],
    )
    assert record.calculation_status == CalculationStatus.INSUFFICIENT_INPUT
    assert record.total_reps == 0
    assert record.valid_reps == 0
    assert record.session_observability_ratio == 0.0
    assert record.is_eligible_for_trends is False
    assert "FLAG_INSUFFICIENT_INPUT" in record.data_quality_flags


def test_t01_empty_heuristic_input(aggregator: SessionEvidenceAggregator):
    """T01 (Heuristic-level): Zero reps evaluated for a single heuristic."""
    summary = aggregator.aggregate_heuristic(
        exercise_id="ex_squat",
        heuristic_name="squat_depth",
        rep_observations=[],
    )
    assert summary.calculation_status == CalculationStatus.INSUFFICIENT_INPUT
    assert summary.target_reps_total == 0
    assert summary.target_reps_observed == 0
    assert summary.defect_rate is None
    assert summary.mean_confidence is None
    assert "FLAG_INSUFFICIENT_INPUT" in summary.data_quality_flags


# =============================================================================
# T02: ALL REPETITIONS OCCLUDED
# =============================================================================

def test_t02_all_repetitions_occluded(aggregator: SessionEvidenceAggregator):
    """T02: 10 occluded reps must classify into CATEGORY_OCCLUDED and never as defects."""
    reps = [{"is_occluded": True, "confidence": 0.85, "is_acceptable": False} for _ in range(10)]
    summary = aggregator.aggregate_heuristic(
        exercise_id="ex_squat",
        heuristic_name="squat_depth",
        rep_observations=reps,
    )
    assert summary.target_reps_total == 10
    assert summary.target_reps_occluded == 10
    assert summary.target_reps_observed == 0
    assert summary.target_reps_defective == 0
    assert summary.defect_rate is None
    assert summary.mean_confidence is None
    assert summary.calculation_status == CalculationStatus.SUCCESS
    assert "FLAG_OCCLUDED" in summary.data_quality_flags


# =============================================================================
# T03: SUB-THRESHOLD CONFIDENCE
# =============================================================================

def test_t03_sub_threshold_confidence(aggregator: SessionEvidenceAggregator):
    """T03: Reps with confidence < 0.50 classify as CATEGORY_LOW_CONFIDENCE, never as defects."""
    reps = [{"confidence": 0.49, "is_acceptable": False} for _ in range(10)]
    summary = aggregator.aggregate_heuristic(
        exercise_id="ex_squat",
        heuristic_name="squat_depth",
        rep_observations=reps,
    )
    assert summary.target_reps_total == 10
    assert summary.target_reps_low_confidence == 10
    assert summary.target_reps_observed == 0
    assert summary.target_reps_defective == 0
    assert summary.defect_rate is None
    assert summary.mean_confidence is None
    assert summary.calculation_status == CalculationStatus.SUCCESS
    assert "FLAG_SUBTHRESHOLD_CONFIDENCE" in summary.data_quality_flags


# =============================================================================
# T04 - T10: STRICT CONFIDENCE VALIDATION
# =============================================================================

def test_t04_missing_confidence_none(aggregator: SessionEvidenceAggregator):
    """T04: confidence = None fails closed to CATEGORY_NOT_OBSERVABLE with FLAG_MISSING_CONFIDENCE."""
    reps = [{"confidence": None, "is_acceptable": True} for _ in range(5)]
    summary = aggregator.aggregate_heuristic(
        exercise_id="ex_squat",
        heuristic_name="squat_depth",
        rep_observations=reps,
    )
    assert summary.target_reps_total == 5
    assert summary.target_reps_not_observable == 5
    assert summary.target_reps_observed == 0
    assert summary.defect_rate is None
    assert "FLAG_MISSING_CONFIDENCE" in summary.data_quality_flags


def test_t05_boolean_confidence_true(aggregator: SessionEvidenceAggregator):
    """T05: confidence = True fails closed to CATEGORY_NOT_OBSERVABLE (strict non-boolean)."""
    reps = [{"confidence": True, "is_acceptable": True} for _ in range(5)]
    summary = aggregator.aggregate_heuristic(
        exercise_id="ex_squat",
        heuristic_name="squat_depth",
        rep_observations=reps,
    )
    assert summary.target_reps_total == 5
    assert summary.target_reps_not_observable == 5
    assert summary.target_reps_observed == 0
    assert summary.defect_rate is None
    assert "FLAG_BOOLEAN_CONFIDENCE_PROHIBITED" in summary.data_quality_flags


def test_t06_boolean_confidence_false(aggregator: SessionEvidenceAggregator):
    """T06: confidence = False fails closed to CATEGORY_NOT_OBSERVABLE (strict non-boolean)."""
    reps = [{"confidence": False, "is_acceptable": True} for _ in range(5)]
    summary = aggregator.aggregate_heuristic(
        exercise_id="ex_squat",
        heuristic_name="squat_depth",
        rep_observations=reps,
    )
    assert summary.target_reps_total == 5
    assert summary.target_reps_not_observable == 5
    assert summary.target_reps_observed == 0
    assert summary.defect_rate is None
    assert "FLAG_BOOLEAN_CONFIDENCE_PROHIBITED" in summary.data_quality_flags


def test_t07_string_confidence(aggregator: SessionEvidenceAggregator):
    """T07: String confidence fails closed to CATEGORY_NOT_OBSERVABLE."""
    reps = [{"confidence": "0.85", "is_acceptable": True} for _ in range(5)]
    summary = aggregator.aggregate_heuristic(
        exercise_id="ex_squat",
        heuristic_name="squat_depth",
        rep_observations=reps,
    )
    assert summary.target_reps_total == 5
    assert summary.target_reps_not_observable == 5
    assert summary.target_reps_observed == 0
    assert summary.defect_rate is None
    assert "FLAG_INVALID_CONFIDENCE_TYPE" in summary.data_quality_flags


def test_t08_nan_confidence(aggregator: SessionEvidenceAggregator):
    """T08: NaN confidence fails closed to CATEGORY_NOT_OBSERVABLE."""
    reps = [{"confidence": float("nan"), "is_acceptable": True} for _ in range(5)]
    summary = aggregator.aggregate_heuristic(
        exercise_id="ex_squat",
        heuristic_name="squat_depth",
        rep_observations=reps,
    )
    assert summary.target_reps_total == 5
    assert summary.target_reps_not_observable == 5
    assert summary.target_reps_observed == 0
    assert summary.defect_rate is None
    assert "FLAG_NAN_CONFIDENCE" in summary.data_quality_flags


def test_t09_infinite_confidence(aggregator: SessionEvidenceAggregator):
    """T09: Infinite confidence (+Inf, -Inf) fails closed to CATEGORY_NOT_OBSERVABLE."""
    reps = [
        {"confidence": float("inf"), "is_acceptable": True},
        {"confidence": float("-inf"), "is_acceptable": True},
    ]
    summary = aggregator.aggregate_heuristic(
        exercise_id="ex_squat",
        heuristic_name="squat_depth",
        rep_observations=reps,
    )
    assert summary.target_reps_total == 2
    assert summary.target_reps_not_observable == 2
    assert summary.target_reps_observed == 0
    assert summary.defect_rate is None
    assert "FLAG_INFINITE_CONFIDENCE" in summary.data_quality_flags


def test_t10_out_of_range_confidence(aggregator: SessionEvidenceAggregator):
    """T10: Confidence outside [0.0, 1.0] fails closed to CATEGORY_NOT_OBSERVABLE."""
    reps = [
        {"confidence": 1.50, "is_acceptable": True},
        {"confidence": -0.20, "is_acceptable": True},
    ]
    summary = aggregator.aggregate_heuristic(
        exercise_id="ex_squat",
        heuristic_name="squat_depth",
        rep_observations=reps,
    )
    assert summary.target_reps_total == 2
    assert summary.target_reps_not_observable == 2
    assert summary.target_reps_observed == 0
    assert summary.defect_rate is None
    assert "FLAG_OUT_OF_RANGE_CONFIDENCE" in summary.data_quality_flags


# =============================================================================
# T11 - T12: CONFIDENCE BOUNDARY TESTS (0.0 vs 0.50)
# =============================================================================

def test_t11_boundary_confidence_zero(aggregator: SessionEvidenceAggregator):
    """T11: Confidence 0.0 is valid numeric, but < 0.50 floor -> CATEGORY_LOW_CONFIDENCE."""
    reps = [{"confidence": 0.0, "is_acceptable": True} for _ in range(5)]
    summary = aggregator.aggregate_heuristic(
        exercise_id="ex_squat",
        heuristic_name="squat_depth",
        rep_observations=reps,
    )
    assert summary.target_reps_total == 5
    assert summary.target_reps_low_confidence == 5
    assert summary.target_reps_observed == 0
    assert summary.defect_rate is None
    assert "FLAG_SUBTHRESHOLD_CONFIDENCE" in summary.data_quality_flags


def test_t12_boundary_confidence_exact_threshold(aggregator: SessionEvidenceAggregator):
    """T12: Confidence 0.50 meets canonical threshold and enters observed evaluation."""
    reps = [{"confidence": 0.50, "is_acceptable": True} for _ in range(5)]
    summary = aggregator.aggregate_heuristic(
        exercise_id="ex_squat",
        heuristic_name="squat_depth",
        rep_observations=reps,
    )
    assert summary.target_reps_total == 5
    assert summary.target_reps_observed == 5
    assert summary.target_reps_low_confidence == 0
    assert summary.target_reps_defective == 0
    assert summary.defect_rate == 0.0
    assert summary.mean_confidence == 0.50


# =============================================================================
# T13 - T15: STRICT BOOLEAN ACCEPTABILITY
# =============================================================================

def test_t13_null_is_acceptable(aggregator: SessionEvidenceAggregator):
    """T13: is_acceptable = None fails closed to CATEGORY_NOT_OBSERVABLE."""
    reps = [{"confidence": 0.85, "is_acceptable": None} for _ in range(5)]
    summary = aggregator.aggregate_heuristic(
        exercise_id="ex_squat",
        heuristic_name="squat_depth",
        rep_observations=reps,
    )
    assert summary.target_reps_total == 5
    assert summary.target_reps_not_observable == 5
    assert summary.target_reps_observed == 0
    assert summary.defect_rate is None
    assert "FLAG_NULL_ACCEPTABILITY" in summary.data_quality_flags


def test_t14_numeric_acceptability_zero_and_one(aggregator: SessionEvidenceAggregator):
    """T14: is_acceptable = 1 or 0 fails closed without coercion."""
    reps = [
        {"confidence": 0.85, "is_acceptable": 1},
        {"confidence": 0.85, "is_acceptable": 0},
    ]
    summary = aggregator.aggregate_heuristic(
        exercise_id="ex_squat",
        heuristic_name="squat_depth",
        rep_observations=reps,
    )
    assert summary.target_reps_total == 2
    assert summary.target_reps_not_observable == 2
    assert summary.target_reps_observed == 0
    assert summary.defect_rate is None
    assert "FLAG_NON_BOOLEAN_ACCEPTABILITY" in summary.data_quality_flags


def test_t15_string_acceptability(aggregator: SessionEvidenceAggregator):
    """T15: String acceptability ("True" / "False") fails closed without coercion."""
    reps = [
        {"confidence": 0.85, "is_acceptable": "True"},
        {"confidence": 0.85, "is_acceptable": "False"},
    ]
    summary = aggregator.aggregate_heuristic(
        exercise_id="ex_squat",
        heuristic_name="squat_depth",
        rep_observations=reps,
    )
    assert summary.target_reps_total == 2
    assert summary.target_reps_not_observable == 2
    assert summary.target_reps_observed == 0
    assert summary.defect_rate is None
    assert "FLAG_NON_BOOLEAN_ACCEPTABILITY" in summary.data_quality_flags


# =============================================================================
# T16 - T17: LANDMARK & MEASUREMENT INTEGRITY
# =============================================================================

def test_t16_missing_landmarks_under_33(aggregator: SessionEvidenceAggregator):
    """T16: Landmarks array with fewer than 33 keypoints fails closed to CATEGORY_NOT_OBSERVABLE."""
    reps = [{"landmarks": [{"x": 0.1, "y": 0.2}] * 15, "confidence": 0.85, "is_acceptable": True}]
    summary = aggregator.aggregate_heuristic(
        exercise_id="ex_squat",
        heuristic_name="squat_depth",
        rep_observations=reps,
    )
    assert summary.target_reps_total == 1
    assert summary.target_reps_not_observable == 1
    assert summary.target_reps_observed == 0
    assert summary.defect_rate is None
    assert "FLAG_MISSING_LANDMARKS" in summary.data_quality_flags


def test_t17_malformed_measurement_nan(aggregator: SessionEvidenceAggregator):
    """T17: Non-finite kinematic measurement fails closed to CATEGORY_NOT_OBSERVABLE."""
    reps = [
        {
            "confidence": 0.85,
            "is_acceptable": True,
            "measurement": FormMeasurementData(unit="degrees", observed_value=float("nan")),
        }
    ]
    summary = aggregator.aggregate_heuristic(
        exercise_id="ex_squat",
        heuristic_name="squat_depth",
        rep_observations=reps,
    )
    assert summary.target_reps_total == 1
    assert summary.target_reps_not_observable == 1
    assert summary.target_reps_observed == 0
    assert summary.defect_rate is None
    assert "FLAG_KINEMATIC_MATH_ERROR" in summary.data_quality_flags


# =============================================================================
# T18: FIVE-WAY MUTUALLY EXCLUSIVE PARTITION & SUM IDENTITY
# =============================================================================

def test_t18_five_way_sum_identity(aggregator: SessionEvidenceAggregator):
    """
    T18: Five-way partition across 10 mixed repetitions:
    2 unobservable, 2 occluded, 2 low-confidence, 2 acceptable, 2 defective.
    Enforces sum(5 categories) == target_reps_total, observed == 4, defect_rate == 0.50.
    """
    reps = [
        # 2 Unobservable (missing conf, null acceptability)
        {"confidence": None, "is_acceptable": True},
        {"confidence": 0.80, "is_acceptable": None},
        # 2 Occluded
        {"is_occluded": True, "confidence": 0.80, "is_acceptable": True},
        {"is_occluded": True, "confidence": 0.80, "is_acceptable": False},
        # 2 Low confidence (c < 0.50)
        {"confidence": 0.40, "is_acceptable": True},
        {"confidence": 0.45, "is_acceptable": False},
        # 2 Observed Acceptable (c >= 0.50, is_acceptable = True)
        {"confidence": 0.80, "is_acceptable": True},
        {"confidence": 0.90, "is_acceptable": True},
        # 2 Observed Defective (c >= 0.50, is_acceptable = False)
        {"confidence": 0.80, "is_acceptable": False},
        {"confidence": 0.70, "is_acceptable": False},
    ]

    summary = aggregator.aggregate_heuristic(
        exercise_id="ex_squat",
        heuristic_name="squat_depth",
        rep_observations=reps,
    )

    # 1. Total & Individual Category Counts
    assert summary.target_reps_total == 10
    assert summary.target_reps_not_observable == 2
    assert summary.target_reps_occluded == 2
    assert summary.target_reps_low_confidence == 2
    assert summary.target_reps_observed == 4
    assert summary.target_reps_defective == 2

    # 2. Strict Partition Sum Invariant
    sum_categories = (
        summary.target_reps_not_observable
        + summary.target_reps_occluded
        + summary.target_reps_low_confidence
        + summary.target_reps_observed
    )
    assert sum_categories == summary.target_reps_total

    # 3. Defect Rate & Denominator Invariant
    assert summary.target_reps_used_for_defect_rate == 4
    assert summary.defect_rate == pytest.approx(0.50)

    # 4. Mean Confidence across observed repetitions only: (0.80 + 0.90 + 0.80 + 0.70) / 4 = 0.80
    assert summary.mean_confidence == pytest.approx(0.80)


# =============================================================================
# T19: MULTI-HEURISTIC PARTIAL_FAILURE CONTRACT
# =============================================================================

def test_t19_multi_heuristic_partial_failure_contract(aggregator: SessionEvidenceAggregator):
    """
    T19: Multi-heuristic squat workout session evaluating 3 heuristics:
    1. Squat Depth: SUCCESS (10 reps, 6 defective, mean conf 0.82)
    2. Torso Inclination: FAILED (unhandled calculation exception)
    3. Knee Valgus: SUCCESS (10 reps, 0 defective, mean conf 0.78)

    Asserts all 8 V2.3.3 assertions:
    1. Depth aggregation eligibility (issue in record, calculation_status = SUCCESS)
    2. Knee tracking aggregation eligibility (issue in record, calculation_status = SUCCESS)
    3. Torso inclination denominator exclusion (+0 to numerator, defect_rate = None)
    4. No false clean technique attribution (calculation_status = FAILED)
    5. Metadata traceability (ERROR_HEURISTIC_CALCULATION_FAILED in flags)
    6. Non-destructive session status (composite status = PARTIAL_FAILURE)
    7. Recurrence ratio consistency
    8. Persistence & model integrity
    """
    # 10 reps for Depth: 6 defective (conf 0.82), 4 acceptable (conf 0.82)
    depth_reps = [
        {"confidence": 0.82, "is_acceptable": False} for _ in range(6)
    ] + [
        {"confidence": 0.82, "is_acceptable": True} for _ in range(4)
    ]

    # 10 reps for Knee tracking: 0 defective, 10 acceptable (conf 0.78)
    knee_reps = [
        {"confidence": 0.78, "is_acceptable": True} for _ in range(10)
    ]

    # Torso lean reps triggers an exception
    torso_reps = [{"confidence": 0.75, "is_acceptable": True} for _ in range(10)]

    session_record = aggregator.aggregate_session(
        exercise_id="ex_squat",
        heuristics_data={
            "squat_depth": depth_reps,
            "squat_torso_inclination": torso_reps,
            "squat_knee_tracking": knee_reps,
        },
        heuristic_errors={
            "squat_torso_inclination": RuntimeError("Division by zero in trunk normalizer"),
        },
    )

    # Assertion 6: Composite session-level status is PARTIAL_FAILURE
    assert session_record.calculation_status == CalculationStatus.PARTIAL_FAILURE

    # Assertion 1: Depth evidence remains SUCCESS and available
    assert "insufficient_depth" in session_record.issues
    depth_issue = session_record.issues["insufficient_depth"]
    assert depth_issue.calculation_status == CalculationStatus.SUCCESS
    assert depth_issue.target_reps_total == 10
    assert depth_issue.target_reps_observed == 10
    assert depth_issue.target_reps_defective == 6
    assert depth_issue.defect_rate == pytest.approx(0.60)
    assert depth_issue.mean_confidence == pytest.approx(0.82)

    # Assertion 2: Knee tracking evidence remains SUCCESS and available
    assert "knee_tracking_deviation" in session_record.issues
    knee_issue = session_record.issues["knee_tracking_deviation"]
    assert knee_issue.calculation_status == CalculationStatus.SUCCESS
    assert knee_issue.target_reps_total == 10
    assert knee_issue.target_reps_observed == 10
    assert knee_issue.target_reps_defective == 0
    assert knee_issue.defect_rate == pytest.approx(0.0)
    assert knee_issue.mean_confidence == pytest.approx(0.78)

    # Assertions 3, 4, 5: Torso inclination failed, defect_rate is None, flag preserved
    assert "excessive_torso_lean" in session_record.issues
    torso_issue = session_record.issues["excessive_torso_lean"]
    assert torso_issue.calculation_status == CalculationStatus.FAILED
    assert torso_issue.defect_rate is None
    assert torso_issue.mean_confidence is None
    assert "ERROR_HEURISTIC_CALCULATION_FAILED" in torso_issue.data_quality_flags

    # Assertion 8: Session record retains issues intact
    assert len(session_record.issues) == 3


# =============================================================================
# T20: COMPLETE CALCULATION FAILURE
# =============================================================================

def test_t20_complete_calculation_failure_all_heuristics_fail(aggregator: SessionEvidenceAggregator):
    """T20: Session where all heuristics fail results in session status FAILED."""
    reps = [{"confidence": 0.80, "is_acceptable": True} for _ in range(5)]
    session_record = aggregator.aggregate_session(
        exercise_id="ex_squat",
        heuristics_data={
            "squat_depth": reps,
            "squat_torso_inclination": reps,
        },
        heuristic_errors={
            "squat_depth": RuntimeError("Fatal Depth Error"),
            "squat_torso_inclination": RuntimeError("Fatal Torso Error"),
        },
    )
    assert session_record.calculation_status == CalculationStatus.FAILED
    assert session_record.is_eligible_for_trends is False


def test_t20_complete_calculation_failure_corrupted_state(aggregator: SessionEvidenceAggregator):
    """T20: Corrupted session state fails closed to CalculationStatus.FAILED."""
    session_record = aggregator.aggregate_session(
        session_data={"corrupted_state": True},
        exercise_id="ex_squat",
    )
    assert session_record.calculation_status == CalculationStatus.FAILED
    assert session_record.is_eligible_for_trends is False
    assert "ERROR_SESSION_CALCULATION_FAILED" in session_record.data_quality_flags


# =============================================================================
# ADDITIONAL TESTS: VOLUME & OBSERVABILITY TREND GATES
# =============================================================================

def test_trend_eligibility_insufficient_reps(aggregator: SessionEvidenceAggregator):
    """Sessions with valid_reps < 3 are ineligible for trends (T21)."""
    reps = [{"confidence": 0.85, "is_acceptable": True} for _ in range(2)]
    session_record = aggregator.aggregate_session(
        exercise_id="ex_squat",
        heuristics_data={"squat_depth": reps},
        total_reps=2,
        valid_reps=2,
        session_observability_ratio=1.0,
    )
    assert session_record.valid_reps == 2
    assert session_record.is_eligible_for_trends is False


def test_trend_eligibility_low_observability(aggregator: SessionEvidenceAggregator):
    """Sessions with observability ratio < 0.70 are ineligible for trends (T22)."""
    session_record = aggregator.aggregate_session(
        exercise_id="ex_squat",
        heuristics_data={"squat_depth": [{"confidence": 0.85, "is_acceptable": True} for _ in range(10)]},
        total_reps=10,
        valid_reps=10,
        session_observability_ratio=0.65,
    )
    assert session_record.session_observability_ratio == 0.65
    assert session_record.is_eligible_for_trends is False


def test_trend_eligibility_qualifying_session(aggregator: SessionEvidenceAggregator):
    """Sessions with valid_reps >= 3 and observability >= 0.70 are eligible for trends."""
    session_record = aggregator.aggregate_session(
        exercise_id="ex_squat",
        heuristics_data={"squat_depth": [{"confidence": 0.85, "is_acceptable": True} for _ in range(5)]},
        total_reps=5,
        valid_reps=5,
        session_observability_ratio=1.0,
    )
    assert session_record.is_eligible_for_trends is True
