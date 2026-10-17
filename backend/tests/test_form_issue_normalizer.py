"""
Authoritative Test Suite for Form Evidence & Issue Normalization Contracts (Phase 9C.6.1).

Verifies:
1. Schema integrity for `FormMeasurementData` and `NormalizedFormIssue` (alias `NormalizedFormIssueSchema`).
2. Type-safe measurement unit validation across 6 dimensions:
   'degrees', 'ratio', 'normalized_offset', 'percent_difference', 'variance', 'unitless'.
3. Complete deterministic mapping of all 25 visual heuristics across all 5 canonical CV exercises
   to the 15 canonical issue IDs.
4. Observability state preservation: unobserved or low-confidence heuristics are NEVER treated as defects.
5. Strict non-medical safety boundaries: rejection and sanitization of `PROHIBITED_MEDICAL_PHRASES`.
6. Legacy defect string normalization: deterministic extraction for provenanced heuristic strings,
   and strict rejection of unprovenanced, vague natural-language text.
7. Singleton provider consistency and error handling for malformed / anomalous kinematic data (NaN, Inf).
"""

import math
import pytest
from pydantic import ValidationError

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
    VALID_MEASUREMENT_UNITS,
    FormHeuristicResultSchema,
    ExerciseFormReportSchema,
)
from backend.app.services.form_heuristics import (
    FormHeuristicResult,
    ExerciseFormReport,
)
from backend.app.seeds.corrective_mappings import (
    RAW_CORRECTIVE_MAPPINGS,
    HEURISTIC_NAME_TO_ISSUE_ID,
    ISSUE_ID_TO_HEURISTIC_NAME,
)
from backend.app.services.form_issue_normalizer import (
    FormIssueNormalizer,
    get_form_issue_normalizer,
    normalize_measurement_unit,
    sanitize_feedback_message,
    HEURISTIC_TO_CATEGORY,
    HEURISTIC_TO_DEFAULT_UNIT,
    SAFE_NON_MEDICAL_FALLBACK,
)


# =============================================================================
# 1. SCHEMA VALIDATION TESTS
# =============================================================================

class TestFormIssueSchemas:
    """Tests for Pydantic v2 schema contracts, field validators, and non-medical boundaries."""

    def test_valid_normalized_form_issue_instantiation(self):
        """Valid NormalizedFormIssue instantiates and validates cleanly."""
        measurement = FormMeasurementData(
            unit="degrees",
            observed_value=82.5,
            reference_value=[90.0, 110.0],
            deviation=-7.5,
        )
        issue = NormalizedFormIssue(
            exercise_id="ex_squat",
            issue_id="insufficient_depth",
            source_heuristic="squat_depth",
            category=HeuristicCategory.ROM,
            status=ObservabilityStatus.OBSERVED,
            is_acceptable=False,
            confidence=0.88,
            measurement=measurement,
            rep_index=1,
            movement_phase="INFLECTION",
            feedback="Squat depth was above parallel (82.5° vs 90.0° required).",
        )
        assert issue.exercise_id == "ex_squat"
        assert issue.issue_id == "insufficient_depth"
        assert issue.source_heuristic == "squat_depth"
        assert issue.category == HeuristicCategory.ROM
        assert issue.status == ObservabilityStatus.OBSERVED
        assert issue.is_acceptable is False
        assert issue.confidence == 0.88
        assert issue.measurement is not None
        assert issue.measurement.unit == "degrees"
        assert issue.measurement.observed_value == 82.5
        assert issue.measurement.deviation == -7.5

    def test_schema_alias_compatibility(self):
        """NormalizedFormIssueSchema is an alias for NormalizedFormIssue."""
        assert NormalizedFormIssueSchema is NormalizedFormIssue

    @pytest.mark.parametrize("unit", [
        "degrees",
        "ratio",
        "normalized_offset",
        "percent_difference",
        "variance",
        "unitless",
    ])
    def test_all_valid_measurement_units(self, unit):
        """All 6 canonical measurement units are valid in FormMeasurementData."""
        data = FormMeasurementData(unit=unit, observed_value=1.23)
        assert data.unit == unit
        assert data.observed_value == 1.23

    def test_invalid_measurement_unit_rejected(self):
        """Unsupported measurement units raise ValidationError."""
        with pytest.raises(ValidationError) as exc_info:
            FormMeasurementData(unit="kilograms", observed_value=100.0)  # type: ignore
        assert "unit" in str(exc_info.value)

    def test_unknown_issue_id_rejected(self):
        """Unknown issue_id raises ValidationError."""
        with pytest.raises(ValidationError) as exc_info:
            NormalizedFormIssue(
                exercise_id="ex_squat",
                issue_id="nonexistent_issue_xyz",
                source_heuristic="squat_depth",
                category=HeuristicCategory.ROM,
                status=ObservabilityStatus.OBSERVED,
                feedback="Test feedback.",
            )
        assert "Unknown canonical issue_id" in str(exc_info.value)

    def test_unknown_exercise_id_rejected(self):
        """Non-canonical exercise_id raises ValidationError."""
        with pytest.raises(ValidationError) as exc_info:
            NormalizedFormIssue(
                exercise_id="ex_leg_press",
                issue_id="insufficient_depth",
                source_heuristic="squat_depth",
                category=HeuristicCategory.ROM,
                status=ObservabilityStatus.OBSERVED,
                feedback="Test feedback.",
            )
        assert "not a canonical CV exercise" in str(exc_info.value)

    def test_mismatched_heuristic_issue_pair_rejected(self):
        """Mismatched source_heuristic and issue_id raises ValidationError."""
        with pytest.raises(ValidationError) as exc_info:
            NormalizedFormIssue(
                exercise_id="ex_squat",
                issue_id="excessive_torso_lean",  # squat_depth maps to insufficient_depth!
                source_heuristic="squat_depth",
                category=HeuristicCategory.ROM,
                status=ObservabilityStatus.OBSERVED,
                feedback="Test feedback.",
            )
        assert "maps to issue" in str(exc_info.value)

    def test_heuristic_not_belonging_to_exercise_rejected(self):
        """A heuristic valid for deadlift but invalid for squat raises ValidationError."""
        with pytest.raises(ValidationError) as exc_info:
            NormalizedFormIssue(
                exercise_id="ex_squat",
                issue_id="early_hip_rise",
                source_heuristic="deadlift_hip_knee_sequencing",
                category=HeuristicCategory.TECHNIQUE,
                status=ObservabilityStatus.OBSERVED,
                feedback="Test feedback.",
            )
        assert "not valid for exercise" in str(exc_info.value)

    @pytest.mark.parametrize("prohibited_phrase", PROHIBITED_MEDICAL_PHRASES)
    def test_prohibited_medical_phrases_rejected_in_feedback(self, prohibited_phrase):
        """Any feedback containing prohibited medical phrases raises ValidationError."""
        feedback_text = f"This movement drill {prohibited_phrase} during training."
        with pytest.raises(ValidationError) as exc_info:
            NormalizedFormIssue(
                exercise_id="ex_squat",
                issue_id="insufficient_depth",
                source_heuristic="squat_depth",
                category=HeuristicCategory.ROM,
                status=ObservabilityStatus.OBSERVED,
                feedback=feedback_text,
            )
        assert "prohibited medical phrase" in str(exc_info.value)

    def test_category_and_status_string_coercion(self):
        """String values for category and status coerce cleanly to their Enum types."""
        issue = NormalizedFormIssue(
            exercise_id="ex_deadlift",
            issue_id="insufficient_lockout",
            source_heuristic="deadlift_hip_lockout",
            category="ROM",  # string representation
            status="OBSERVED",  # string representation
            feedback="Hip lockout was slightly incomplete.",
        )
        assert issue.category == HeuristicCategory.ROM
        assert issue.status == ObservabilityStatus.OBSERVED

    def test_schema_serialization_roundtrip(self):
        """NormalizedFormIssue serializes to JSON and deserializes cleanly."""
        original = NormalizedFormIssue(
            exercise_id="ex_bench_press",
            issue_id="excessive_elbow_flare",
            source_heuristic="bench_elbow_flare",
            category=HeuristicCategory.TECHNIQUE,
            status=ObservabilityStatus.OBSERVED,
            is_acceptable=False,
            confidence=0.92,
            measurement=FormMeasurementData(unit="degrees", observed_value=78.0, deviation=8.0),
            rep_index=2,
            feedback="Elbow flare exceeded 70 degrees.",
        )
        json_data = original.model_dump_json()
        restored = NormalizedFormIssue.model_validate_json(json_data)
        assert restored.exercise_id == original.exercise_id
        assert restored.issue_id == original.issue_id
        assert restored.measurement.observed_value == original.measurement.observed_value


# =============================================================================
# 2. DETERMINISTIC MAPPING TESTS (25 HEURISTICS -> 15 ISSUE IDS)
# =============================================================================

class TestFormIssueNormalizerMappings:
    """Verifies that all 25 heuristics across 5 canonical exercises map deterministically."""

    @pytest.fixture
    def normalizer(self):
        return get_form_issue_normalizer()

    def test_all_25_raw_corrective_mappings_covered(self, normalizer):
        """Every entry in RAW_CORRECTIVE_MAPPINGS must be correctly retrieved by the normalizer."""
        assert len(RAW_CORRECTIVE_MAPPINGS) == 25
        for m in RAW_CORRECTIVE_MAPPINGS:
            ex_id = m["source_exercise_id"]
            h_name = m["heuristic_name"]
            expected_issue = m["issue_id"]

            retrieved = normalizer.get_canonical_issue_id(ex_id, h_name)
            assert retrieved == expected_issue, (
                f"Failed mapping for ({ex_id}, {h_name}): expected {expected_issue}, got {retrieved}"
            )
            assert normalizer.is_valid_heuristic_for_exercise(ex_id, h_name) is True

    def test_all_5_canonical_cv_exercises_supported(self, normalizer):
        """All 5 canonical CV exercises are supported and map the expected number of heuristics."""
        expected_counts = {
            "ex_squat": 5,
            "ex_bench_press": 4,
            "ex_deadlift": 6,
            "ex_bicep_curl": 5,
            "ex_shoulder_press": 5,
        }
        for ex_id, expected_count in expected_counts.items():
            heuristics = normalizer.get_mapped_heuristics_for_exercise(ex_id)
            assert len(heuristics) == expected_count, (
                f"Expected {expected_count} heuristics for {ex_id}, got {len(heuristics)}: {heuristics}"
            )

    def test_canonical_issue_ids_set(self, normalizer):
        """Exactly 15 unique canonical issue IDs are recognized."""
        issue_ids = normalizer.get_all_valid_issue_ids()
        assert len(issue_ids) == 15
        assert issue_ids == VALID_ISSUE_IDS
        expected_15 = {
            "insufficient_depth",
            "excessive_torso_lean",
            "knee_tracking_deviation",
            "asymmetrical_movement",
            "unstable_torso",
            "excessive_elbow_flare",
            "poor_press_symmetry",
            "unstable_movement",
            "insufficient_lockout",
            "early_hip_rise",
            "body_center_drift",
            "incomplete_rom",
            "excessive_arm_movement",
            "insufficient_overhead_range",
            "forearm_tilt",
        }
        assert issue_ids == expected_15

    def test_heuristic_to_category_and_unit_coverage(self):
        """All 25 heuristics have precomputed category and measurement unit entries."""
        for m in RAW_CORRECTIVE_MAPPINGS:
            h_name = m["heuristic_name"]
            assert h_name in HEURISTIC_TO_CATEGORY, f"Missing category mapping for {h_name}"
            assert h_name in HEURISTIC_TO_DEFAULT_UNIT, f"Missing unit mapping for {h_name}"
            unit = HEURISTIC_TO_DEFAULT_UNIT[h_name]
            assert unit in VALID_MEASUREMENT_UNITS, f"Invalid default unit '{unit}' for {h_name}"


# =============================================================================
# 3. NORMALIZATION METHOD TESTS
# =============================================================================

class TestNormalizeHeuristicResult:
    """Tests normalization of individual heuristic results from various sources."""

    @pytest.fixture
    def normalizer(self):
        return get_form_issue_normalizer()

    def test_normalize_from_dataclass(self, normalizer):
        """Normalizes a FormHeuristicResult dataclass object."""
        result = FormHeuristicResult(
            exercise_id="ex_squat",
            category=HeuristicCategory.TECHNIQUE,
            heuristic_name="squat_torso_inclination",
            status=ObservabilityStatus.OBSERVED,
            is_acceptable=False,
            observed_value=48.2,
            reference_value=[0.0, 40.0],
            deviation=8.2,
            confidence=0.91,
            feedback="Torso forward lean exceeded 40.0 degrees.",
            unit="degrees",
        )
        issue = normalizer.normalize_heuristic_result(result, rep_index=3, movement_phase="ECCENTRIC")
        assert issue is not None
        assert issue.issue_id == "excessive_torso_lean"
        assert issue.source_heuristic == "squat_torso_inclination"
        assert issue.rep_index == 3
        assert issue.movement_phase == "ECCENTRIC"
        assert issue.measurement is not None
        assert issue.measurement.unit == "degrees"
        assert issue.measurement.observed_value == 48.2
        assert issue.measurement.deviation == 8.2

    def test_normalize_from_pydantic_schema(self, normalizer):
        """Normalizes a FormHeuristicResultSchema Pydantic object."""
        schema = FormHeuristicResultSchema(
            exercise_id="ex_bench_press",
            category="Joint Alignment / Technique",
            heuristic_name="bench_elbow_flare",
            status="OBSERVED",
            is_acceptable=False,
            observed_value=76.0,
            reference_value=[45.0, 70.0],
            deviation=6.0,
            confidence=0.85,
            feedback="Elbow flare exceeded 70 degrees.",
            unit="degrees",
        )
        issue = normalizer.normalize_heuristic_result(schema, rep_index=2)
        assert issue is not None
        assert issue.issue_id == "excessive_elbow_flare"
        assert issue.category == HeuristicCategory.TECHNIQUE
        assert issue.status == ObservabilityStatus.OBSERVED

    def test_normalize_from_dict(self, normalizer):
        """Normalizes a plain dictionary representation."""
        raw_dict = {
            "exercise_id": "ex_deadlift",
            "heuristic_name": "deadlift_body_center_stability",
            "category": "Joint Alignment / Technique",
            "status": "OBSERVED",
            "is_acceptable": False,
            "observed_value": 0.12,
            "reference_value": 0.08,
            "deviation": 0.04,
            "confidence": 0.89,
            "feedback": "Body center drift exceeded threshold.",
            "unit": "norm_units",
        }
        issue = normalizer.normalize_heuristic_result(raw_dict)
        assert issue is not None
        assert issue.issue_id == "body_center_drift"
        assert issue.measurement is not None
        assert issue.measurement.unit == "normalized_offset"
        assert issue.measurement.observed_value == 0.12

    def test_normalize_unit_polymorphism(self, normalizer):
        """Verifies correct unit normalization across all distinct heuristic types."""
        # 1. Ratio
        res_ratio = FormHeuristicResult(
            exercise_id="ex_squat",
            category=HeuristicCategory.TECHNIQUE,
            heuristic_name="squat_knee_tracking",
            status=ObservabilityStatus.OBSERVED,
            observed_value=0.78,
            unit="ratio",
            feedback="Knee tracking ratio deviated.",
        )
        issue_ratio = normalizer.normalize_heuristic_result(res_ratio)
        assert issue_ratio.measurement.unit == "ratio"

        # 2. Symmetry (percent_difference)
        res_sym = FormHeuristicResult(
            exercise_id="ex_bench_press",
            category=HeuristicCategory.SYMMETRY,
            heuristic_name="bench_elbow_symmetry",
            status=ObservabilityStatus.OBSERVED,
            observed_value=14.5,
            unit="percent_difference",
            feedback="Bilateral elbow symmetry delta observed.",
        )
        issue_sym = normalizer.normalize_heuristic_result(res_sym)
        assert issue_sym.measurement.unit == "percent_difference"

        # 3. Stability (variance)
        res_stab = FormHeuristicResult(
            exercise_id="ex_shoulder_press",
            category=HeuristicCategory.STABILITY,
            heuristic_name="shoulder_press_movement_stability",
            status=ObservabilityStatus.OBSERVED,
            observed_value=0.25,
            unit="variance",
            feedback="Trunk movement stability variance observed.",
        )
        issue_stab = normalizer.normalize_heuristic_result(res_stab)
        assert issue_stab.measurement.unit == "variance"

        # 4. Sequencing (unitless)
        res_seq = FormHeuristicResult(
            exercise_id="ex_deadlift",
            category=HeuristicCategory.TECHNIQUE,
            heuristic_name="deadlift_hip_knee_sequencing",
            status=ObservabilityStatus.OBSERVED,
            observed_value=1.5,
            unit="unitless",
            feedback="Hips rose early relative to knee extension.",
        )
        issue_seq = normalizer.normalize_heuristic_result(res_seq)
        assert issue_seq.measurement.unit == "unitless"

    def test_nan_and_inf_anomalies_handled_gracefully(self, normalizer):
        """Mathematical anomalies (NaN, Inf) are safely sanitized and marked INVALID."""
        result_nan = FormHeuristicResult(
            exercise_id="ex_squat",
            category=HeuristicCategory.ROM,
            heuristic_name="squat_depth",
            status=ObservabilityStatus.OBSERVED,
            observed_value=float("nan"),
            deviation=float("inf"),
            feedback="Angle computation anomaly.",
        )
        issue = normalizer.normalize_heuristic_result(result_nan)
        assert issue is not None
        assert issue.status == ObservabilityStatus.INVALID
        assert issue.measurement is None or issue.measurement.observed_value is None

    def test_unmapped_or_invalid_exercise_returns_none(self, normalizer):
        """Unmapped heuristics or non-canonical exercises return None without raising unhandled errors."""
        res_unknown_ex = FormHeuristicResult(
            exercise_id="ex_unknown",
            category=HeuristicCategory.ROM,
            heuristic_name="squat_depth",
            status=ObservabilityStatus.OBSERVED,
            feedback="Test",
        )
        assert normalizer.normalize_heuristic_result(res_unknown_ex) is None

        res_unknown_h = FormHeuristicResult(
            exercise_id="ex_squat",
            category=HeuristicCategory.ROM,
            heuristic_name="unknown_heuristic_metric",
            status=ObservabilityStatus.OBSERVED,
            feedback="Test",
        )
        assert normalizer.normalize_heuristic_result(res_unknown_h) is None
        assert normalizer.normalize_heuristic_result(None) is None

    def test_feedback_sanitization_in_normalizer(self, normalizer):
        """If incoming heuristic feedback contains prohibited phrases, normalizer sanitizes it safely."""
        result = FormHeuristicResult(
            exercise_id="ex_deadlift",
            category=HeuristicCategory.ROM,
            heuristic_name="deadlift_hip_lockout",
            status=ObservabilityStatus.OBSERVED,
            feedback="Full hip lockout cures injury and guarantees safety.",
        )
        issue = normalizer.normalize_heuristic_result(result)
        assert issue is not None
        assert issue.feedback == SAFE_NON_MEDICAL_FALLBACK
        for phrase in PROHIBITED_MEDICAL_PHRASES:
            assert phrase not in issue.feedback.lower()


# =============================================================================
# 4. REPORT NORMALIZATION AND OBSERVABILITY GUARDRAIL TESTS
# =============================================================================

class TestNormalizeFormReport:
    """Verifies batch normalization and the critical observability guardrail."""

    @pytest.fixture
    def normalizer(self):
        return get_form_issue_normalizer()

    def test_normalize_all_results_in_report(self, normalizer):
        """Normalizes all heuristic results when defects_only=False."""
        report = ExerciseFormReport(
            exercise_id="ex_squat",
            timestamp_ms=1000.0,
            results=[
                FormHeuristicResult(
                    exercise_id="ex_squat",
                    category=HeuristicCategory.ROM,
                    heuristic_name="squat_depth",
                    status=ObservabilityStatus.OBSERVED,
                    is_acceptable=True,
                    observed_value=95.0,
                    feedback="Good depth.",
                ),
                FormHeuristicResult(
                    exercise_id="ex_squat",
                    category=HeuristicCategory.TECHNIQUE,
                    heuristic_name="squat_torso_inclination",
                    status=ObservabilityStatus.OBSERVED,
                    is_acceptable=False,
                    observed_value=46.0,
                    feedback="Excessive lean.",
                ),
                FormHeuristicResult(
                    exercise_id="ex_squat",
                    category=HeuristicCategory.TECHNIQUE,
                    heuristic_name="squat_knee_tracking",
                    status=ObservabilityStatus.NOT_OBSERVABLE,
                    is_acceptable=None,
                    feedback="Feet occluded.",
                ),
            ],
        )
        issues = normalizer.normalize_form_report(report, rep_index=1, defects_only=False)
        assert len(issues) == 3
        statuses = [i.status for i in issues]
        assert ObservabilityStatus.OBSERVED in statuses
        assert ObservabilityStatus.NOT_OBSERVABLE in statuses

    def test_critical_guardrail_defects_only_filters_unobserved(self, normalizer):
        """
        CRITICAL ARCHITECTURAL GUARDRAIL:
        defects_only=True includes an issue ONLY if:
          1. status == ObservabilityStatus.OBSERVED
          2. is_acceptable is False
        Missing data, low confidence, or unobservable statuses are NEVER defects.
        """
        report = ExerciseFormReport(
            exercise_id="ex_bench_press",
            timestamp_ms=2000.0,
            results=[
                # 1. OBSERVED and Acceptable -> NOT a defect
                FormHeuristicResult(
                    exercise_id="ex_bench_press",
                    category=HeuristicCategory.ROM,
                    heuristic_name="bench_elbow_rom",
                    status=ObservabilityStatus.OBSERVED,
                    is_acceptable=True,
                    feedback="Full ROM achieved.",
                ),
                # 2. OBSERVED and Unacceptable -> VALID DEFECT
                FormHeuristicResult(
                    exercise_id="ex_bench_press",
                    category=HeuristicCategory.TECHNIQUE,
                    heuristic_name="bench_elbow_flare",
                    status=ObservabilityStatus.OBSERVED,
                    is_acceptable=False,
                    feedback="Excessive elbow flare.",
                ),
                # 3. NOT_OBSERVABLE -> MUST NOT be included as a defect
                FormHeuristicResult(
                    exercise_id="ex_bench_press",
                    category=HeuristicCategory.SYMMETRY,
                    heuristic_name="bench_elbow_symmetry",
                    status=ObservabilityStatus.NOT_OBSERVABLE,
                    is_acceptable=None,
                    feedback="Left arm occluded.",
                ),
                # 4. INSUFFICIENT_CONFIDENCE -> MUST NOT be included as a defect
                FormHeuristicResult(
                    exercise_id="ex_bench_press",
                    category=HeuristicCategory.STABILITY,
                    heuristic_name="bench_movement_stability",
                    status=ObservabilityStatus.INSUFFICIENT_CONFIDENCE,
                    is_acceptable=None,
                    feedback="Low confidence keypoints.",
                ),
            ],
        )
        defects = normalizer.normalize_form_report(report, rep_index=2, defects_only=True)
        # Exactly one defect should be returned: bench_elbow_flare!
        assert len(defects) == 1
        assert defects[0].source_heuristic == "bench_elbow_flare"
        assert defects[0].issue_id == "excessive_elbow_flare"
        assert defects[0].status == ObservabilityStatus.OBSERVED
        assert defects[0].is_acceptable is False

    def test_normalize_empty_or_none_report(self, normalizer):
        """Empty or None reports return an empty list without error."""
        assert normalizer.normalize_form_report(None) == []
        assert normalizer.normalize_form_report(ExerciseFormReport(exercise_id="ex_squat", timestamp_ms=0)) == []


# =============================================================================
# 5. LEGACY DEFECT STRING NORMALIZATION TESTS
# =============================================================================

class TestNormalizeDefectString:
    """Verifies deterministic mapping of scoring strings and rejection of vague text."""

    @pytest.fixture
    def normalizer(self):
        return get_form_issue_normalizer()

    def test_scoring_defect_with_colon_feedback(self, normalizer):
        """Normalizes format generated by RepetitionScore: '{heuristic_name}: {feedback}'."""
        defect_str = "squat_depth: Squat depth was above parallel (85.2° vs 90.0° required)."
        issue = normalizer.normalize_defect_string("ex_squat", defect_str, rep_index=1)
        assert issue is not None
        assert issue.issue_id == "insufficient_depth"
        assert issue.source_heuristic == "squat_depth"
        assert issue.category == HeuristicCategory.ROM
        assert issue.status == ObservabilityStatus.OBSERVED
        assert issue.is_acceptable is False
        assert "Squat depth was above parallel" in issue.feedback

    def test_scoring_defect_with_penalty_string(self, normalizer):
        """Normalizes format: '{heuristic_name} penalty: {penalty_val}'."""
        defect_str = "bench_elbow_flare penalty: 25.0"
        issue = normalizer.normalize_defect_string("ex_bench_press", defect_str, rep_index=2)
        assert issue is not None
        assert issue.issue_id == "excessive_elbow_flare"
        assert issue.source_heuristic == "bench_elbow_flare"
        assert issue.category == HeuristicCategory.TECHNIQUE

    def test_bare_heuristic_name(self, normalizer):
        """Normalizes bare heuristic name string."""
        issue = normalizer.normalize_defect_string("ex_bicep_curl", "curl_upper_arm_drift", rep_index=4)
        assert issue is not None
        assert issue.issue_id == "excessive_arm_movement"
        assert issue.source_heuristic == "curl_upper_arm_drift"

    def test_unprovenanced_vague_strings_strictly_rejected(self, normalizer):
        """
        LEGACY SAFETY RULE:
        Never infer canonical issue IDs from unprovenanced natural-language strings.
        Vague summary strings must return None.
        """
        unprovenanced_strings = [
            "Good repetition execution with minor technique adjustments observed.",
            "Great set, keep up the good work!",
            "You should focus on your form more closely next time.",
            "Movement was shaky and lacked control.",
            "Form was suboptimal.",
        ]
        for s in unprovenanced_strings:
            res = normalizer.normalize_defect_string("ex_squat", s)
            assert res is None, f"Expected None for unprovenanced string '{s}', got {res}"

    def test_wrong_exercise_defect_string_rejected(self, normalizer):
        """A heuristic valid for deadlift passed under squat exercise_id returns None."""
        defect_str = "deadlift_hip_lockout: Hip extension was incomplete."
        issue = normalizer.normalize_defect_string("ex_squat", defect_str)
        assert issue is None

    def test_empty_or_whitespace_defect_string_rejected(self, normalizer):
        """Empty or whitespace-only defect strings return None."""
        assert normalizer.normalize_defect_string("ex_squat", "") is None
        assert normalizer.normalize_defect_string("ex_squat", "   ") is None


# =============================================================================
# 6. SINGLETON ACCESSOR TESTS
# =============================================================================

class TestNormalizerSingleton:
    """Verifies that get_form_issue_normalizer provides a consistent singleton."""

    def test_singleton_identity(self):
        """get_form_issue_normalizer returns the exact same instance across calls."""
        instance1 = get_form_issue_normalizer()
        instance2 = get_form_issue_normalizer()
        assert instance1 is instance2
        assert isinstance(instance1, FormIssueNormalizer)
