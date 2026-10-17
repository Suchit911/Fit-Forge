"""
Focused Unit Test Suite for Form Evidence Schemas & Configuration (Subphase 9C.6.2.1).

Verifies:
1. Enum definitions: EvidenceLevel, CalculationStatus, ProvenanceTier, ObservabilityCategory.
2. Schema construction and serialization: SessionIssueSummary, SessionEvidenceRecord,
   AggregatedIssueEvidence, ExerciseEvidenceSummary.
3. Default configuration values match Version 2.3.3 specification.
4. Canonical parameter names are used and aliases do not exist.
5. Individual parameter domain bounds.
6. Confidence Triad valid configuration.
7. Confidence Triad invalid configuration fail-fast with ValueError.
8. MIN_TARGET_HEURISTIC_OBSERVED_REPS <= MIN_VALID_REPS_PER_SESSION invariant.
9. REPEATED_PATTERN_MIN_SESSIONS <= ACTIONABLE_PATTERN_MIN_SESSIONS invariant.
10. ACTIONABLE_PATTERN_MIN_SESSIONS <= LOOKBACK_SESSIONS_K invariant.
"""

import pytest
from backend.app.schemas.form_evidence import (
    EvidenceLevel,
    CalculationStatus,
    ProvenanceTier,
    ObservabilityCategory,
    SessionIssueSummary,
    SessionEvidenceRecord,
    AggregatedIssueEvidence,
    ExerciseEvidenceSummary,
    EvidenceAggregationConfig,
)


class TestFormEvidenceEnums:
    """Verifies complete, mutually exclusive enumeration definitions."""

    def test_evidence_level_enum(self):
        expected = {
            "NO_EVIDENCE",
            "INSUFFICIENT_DATA",
            "EMERGING_OCCURRENCE",
            "REPEATED_PATTERN",
            "ACTIONABLE_PATTERN",
        }
        assert {e.value for e in EvidenceLevel} == expected

    def test_calculation_status_enum(self):
        expected = {
            "SUCCESS",
            "PARTIAL_FAILURE",
            "FAILED",
            "INSUFFICIENT_INPUT",
        }
        assert {e.value for e in CalculationStatus} == expected

    def test_provenance_tier_enum(self):
        expected = {
            "TIER_1_NORMALIZED",
            "TIER_2_COMPACT_TAGS",
            "TIER_3_DEFECT_STRING",
            "TIER_4_UNPROVENANCED",
        }
        assert {e.value for e in ProvenanceTier} == expected

    def test_observability_category_enum(self):
        expected = {
            "CATEGORY_NOT_OBSERVABLE",
            "CATEGORY_OCCLUDED",
            "CATEGORY_LOW_CONFIDENCE",
            "CATEGORY_OBSERVED_ACCEPTABLE",
            "CATEGORY_OBSERVED_DEFECTIVE",
        }
        assert {e.value for e in ObservabilityCategory} == expected


class TestFormEvidenceSchemas:
    """Verifies schema instantiation, defaults, and round-trip serialization."""

    def test_session_issue_summary_defaults(self):
        summary = SessionIssueSummary(
            issue_id="insufficient_depth",
            source_heuristic="squat_depth",
            category="RANGE_OF_MOTION",
        )
        assert summary.calculation_status == CalculationStatus.SUCCESS
        assert summary.target_reps_total == 0
        assert summary.target_reps_observed == 0
        assert summary.defect_rate is None
        assert summary.mean_confidence is None
        assert summary.data_quality_flags == []

        # Round-trip serialization
        dumped = summary.model_dump()
        restored = SessionIssueSummary.model_validate(dumped)
        assert restored.issue_id == "insufficient_depth"
        assert restored.calculation_status == CalculationStatus.SUCCESS

    def test_session_evidence_record_instantiation(self):
        issue = SessionIssueSummary(
            issue_id="insufficient_depth",
            source_heuristic="squat_depth",
            category="RANGE_OF_MOTION",
            target_reps_total=10,
            target_reps_observed=8,
            target_reps_defective=4,
            defect_rate=0.50,
            mean_confidence=0.82,
        )
        record = SessionEvidenceRecord(
            session_id="sess_123",
            user_id="user_456",
            exercise_id="squat",
            completed_at="2026-09-28T12:00:00Z",
            total_reps=10,
            valid_reps=10,
            session_observability_ratio=0.85,
            is_eligible_for_trends=True,
            calculation_status=CalculationStatus.SUCCESS,
            provenance_tier=ProvenanceTier.TIER_1_NORMALIZED,
            issues={"insufficient_depth": issue},
        )
        assert record.session_id == "sess_123"
        assert record.issues["insufficient_depth"].defect_rate == 0.50
        assert record.provenance_tier == ProvenanceTier.TIER_1_NORMALIZED

    def test_aggregated_issue_evidence_defaults_and_fields(self):
        evidence = AggregatedIssueEvidence(
            issue_id="insufficient_depth",
            source_heuristic="squat_depth",
            category="RANGE_OF_MOTION",
            session_eligible_count=5,
            target_evaluated_sessions_count=5,
            qualifying_sessions_count=3,
            recurrence_ratio=0.60,
            qualifying_mean_confidence=0.75,
            evidence_level=EvidenceLevel.ACTIONABLE_PATTERN,
        )
        assert evidence.session_eligible_count == 5
        assert evidence.target_evaluated_sessions_count == 5
        assert evidence.qualifying_sessions_count == 3
        assert evidence.recurrence_ratio == 0.60
        assert evidence.qualifying_mean_confidence == 0.75
        assert evidence.evidence_level == EvidenceLevel.ACTIONABLE_PATTERN
        assert evidence.aggregation_version == "2.3.3"
        assert evidence.config_version == "1.0.0"

    def test_exercise_evidence_summary_disclaimer(self):
        summary = ExerciseEvidenceSummary(
            user_id="user_456",
            exercise_id="squat",
            lookback_sessions_evaluated=5,
            eligible_sessions_count=5,
            evaluated_at="2026-09-28T12:05:00Z",
            evidence_level=EvidenceLevel.ACTIONABLE_PATTERN,
            status_message="Actionable pattern detected",
        )
        assert "not a medical diagnosis" in summary.disclaimer
        assert summary.aggregation_version == "2.3.3"
        assert summary.calculation_status == CalculationStatus.SUCCESS


class TestEvidenceAggregationConfig:
    """Verifies canonical naming, domain bounds, and relational invariants for configuration."""

    def test_default_configuration_values(self):
        config = EvidenceAggregationConfig()
        assert config.MIN_HEURISTIC_CONFIDENCE == 0.50
        assert config.ACTIONABLE_PATTERN_SESSION_MIN_CONFIDENCE == 0.55
        assert config.ACTIONABLE_PATTERN_MIN_CONFIDENCE == 0.60
        assert config.MIN_TARGET_HEURISTIC_OBSERVED_REPS == 3
        assert config.MIN_VALID_REPS_PER_SESSION == 3
        assert config.SESSION_DEFECT_RATE_THRESHOLD == 0.50
        assert config.REPEATED_PATTERN_MIN_SESSIONS == 2
        assert config.ACTIONABLE_PATTERN_MIN_SESSIONS == 3
        assert config.LOOKBACK_SESSIONS_K == 5
        assert config.MIN_SESSION_OBSERVABILITY_RATIO == 0.70

    def test_canonical_parameter_names_and_no_aliases(self):
        config = EvidenceAggregationConfig()
        # Verify canonical names exist
        canonical_fields = [
            "MIN_HEURISTIC_CONFIDENCE",
            "ACTIONABLE_PATTERN_SESSION_MIN_CONFIDENCE",
            "ACTIONABLE_PATTERN_MIN_CONFIDENCE",
            "MIN_TARGET_HEURISTIC_OBSERVED_REPS",
            "MIN_VALID_REPS_PER_SESSION",
            "SESSION_DEFECT_RATE_THRESHOLD",
            "REPEATED_PATTERN_MIN_SESSIONS",
            "ACTIONABLE_PATTERN_MIN_SESSIONS",
            "LOOKBACK_SESSIONS_K",
            "MIN_SESSION_OBSERVABILITY_RATIO",
        ]
        for field in canonical_fields:
            assert hasattr(config, field)

        # Verify deprecated aliases do NOT exist
        deprecated_aliases = [
            "ACTIONABLE_SESSION_MIN_CONF",
            "ACTIONABLE_MIN_CONF",
            "MIN_HEURISTIC_CONF",
            "REPEATED_MIN",
            "LOOKBACK_K",
        ]
        for alias in deprecated_aliases:
            assert not hasattr(config, alias)

    def test_individual_parameter_bounds(self):
        # MIN_HEURISTIC_CONFIDENCE [0.10, 1.00]
        with pytest.raises(ValueError, match="MIN_HEURISTIC_CONFIDENCE"):
            EvidenceAggregationConfig(MIN_HEURISTIC_CONFIDENCE=0.05)
        with pytest.raises(ValueError, match="MIN_HEURISTIC_CONFIDENCE"):
            EvidenceAggregationConfig(MIN_HEURISTIC_CONFIDENCE=1.05)

        # LOOKBACK_SESSIONS_K [3, 20]
        with pytest.raises(ValueError, match="LOOKBACK_SESSIONS_K"):
            EvidenceAggregationConfig(LOOKBACK_SESSIONS_K=2)
        with pytest.raises(ValueError, match="LOOKBACK_SESSIONS_K"):
            EvidenceAggregationConfig(LOOKBACK_SESSIONS_K=25)

        # MIN_SESSION_OBSERVABILITY_RATIO [0.10, 1.00]
        with pytest.raises(ValueError, match="MIN_SESSION_OBSERVABILITY_RATIO"):
            EvidenceAggregationConfig(MIN_SESSION_OBSERVABILITY_RATIO=0.0)
        with pytest.raises(ValueError, match="MIN_SESSION_OBSERVABILITY_RATIO"):
            EvidenceAggregationConfig(MIN_SESSION_OBSERVABILITY_RATIO=1.2)

        # Non-boolean enforcement (booleans are subclasses of int in Python)
        with pytest.raises(ValueError, match="must be numeric"):
            EvidenceAggregationConfig(LOOKBACK_SESSIONS_K=True)  # type: ignore

    def test_confidence_triad_valid_configurations(self):
        # Valid: 0.50 <= 0.55 <= 0.60
        cfg1 = EvidenceAggregationConfig(
            MIN_HEURISTIC_CONFIDENCE=0.50,
            ACTIONABLE_PATTERN_SESSION_MIN_CONFIDENCE=0.55,
            ACTIONABLE_PATTERN_MIN_CONFIDENCE=0.60,
        )
        assert cfg1.MIN_HEURISTIC_CONFIDENCE <= cfg1.ACTIONABLE_PATTERN_SESSION_MIN_CONFIDENCE <= cfg1.ACTIONABLE_PATTERN_MIN_CONFIDENCE

        # Valid equal boundaries: 0.50 <= 0.50 <= 0.50
        cfg2 = EvidenceAggregationConfig(
            MIN_HEURISTIC_CONFIDENCE=0.50,
            ACTIONABLE_PATTERN_SESSION_MIN_CONFIDENCE=0.50,
            ACTIONABLE_PATTERN_MIN_CONFIDENCE=0.50,
        )
        assert cfg2.MIN_HEURISTIC_CONFIDENCE == 0.50

    def test_confidence_triad_invalid_configurations(self):
        # Case A: MIN_HEURISTIC_CONFIDENCE > ACTIONABLE_PATTERN_SESSION_MIN_CONFIDENCE
        with pytest.raises(ValueError, match="Confidence Triad Invariant violated"):
            EvidenceAggregationConfig(
                MIN_HEURISTIC_CONFIDENCE=0.58,
                ACTIONABLE_PATTERN_SESSION_MIN_CONFIDENCE=0.55,
                ACTIONABLE_PATTERN_MIN_CONFIDENCE=0.60,
            )

        # Case B: ACTIONABLE_PATTERN_SESSION_MIN_CONFIDENCE > ACTIONABLE_PATTERN_MIN_CONFIDENCE
        with pytest.raises(ValueError, match="Confidence Triad Invariant violated"):
            EvidenceAggregationConfig(
                MIN_HEURISTIC_CONFIDENCE=0.50,
                ACTIONABLE_PATTERN_SESSION_MIN_CONFIDENCE=0.65,
                ACTIONABLE_PATTERN_MIN_CONFIDENCE=0.60,
            )

    def test_relational_target_reps_le_valid_reps(self):
        # Invalid: MIN_TARGET_HEURISTIC_OBSERVED_REPS (4) > MIN_VALID_REPS_PER_SESSION (3)
        with pytest.raises(ValueError, match="MIN_TARGET_HEURISTIC_OBSERVED_REPS .* cannot exceed MIN_VALID_REPS_PER_SESSION"):
            EvidenceAggregationConfig(
                MIN_TARGET_HEURISTIC_OBSERVED_REPS=4,
                MIN_VALID_REPS_PER_SESSION=3,
            )

    def test_relational_repeated_le_actionable_sessions(self):
        # Invalid: REPEATED_PATTERN_MIN_SESSIONS (4) > ACTIONABLE_PATTERN_MIN_SESSIONS (3)
        with pytest.raises(ValueError, match="REPEATED_PATTERN_MIN_SESSIONS .* cannot exceed ACTIONABLE_PATTERN_MIN_SESSIONS"):
            EvidenceAggregationConfig(
                REPEATED_PATTERN_MIN_SESSIONS=4,
                ACTIONABLE_PATTERN_MIN_SESSIONS=3,
            )

    def test_relational_actionable_sessions_le_lookback_k(self):
        # Invalid: ACTIONABLE_PATTERN_MIN_SESSIONS (6) > LOOKBACK_SESSIONS_K (5)
        with pytest.raises(ValueError, match="ACTIONABLE_PATTERN_MIN_SESSIONS .* cannot exceed LOOKBACK_SESSIONS_K"):
            EvidenceAggregationConfig(
                ACTIONABLE_PATTERN_MIN_SESSIONS=6,
                LOOKBACK_SESSIONS_K=5,
            )
