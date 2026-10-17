"""
Authoritative Domain Schemas and Configuration for Form Evidence Aggregation (Phase 9C.6.2.1).

Defines:
- Enums: EvidenceLevel, CalculationStatus, ProvenanceTier, ObservabilityCategory.
- Single-Session Schemas: SessionIssueSummary, SessionEvidenceRecord.
- Longitudinal Schemas: AggregatedIssueEvidence, ExerciseEvidenceSummary.
- Configuration: EvidenceAggregationConfig with strict validation of individual parameter
  bounds, relational constraints, and the Confidence Triad Invariant.
"""

from dataclasses import dataclass
from enum import Enum
import math
from typing import Dict, List, Optional, Any
from pydantic import BaseModel, Field

from backend.app.schemas.form_analysis import NormalizedFormIssue, FormMeasurementData


class EvidenceLevel(str, Enum):
    """Canonical longitudinal evidence levels for movement technique issues."""
    NO_EVIDENCE = "NO_EVIDENCE"
    INSUFFICIENT_DATA = "INSUFFICIENT_DATA"
    EMERGING_OCCURRENCE = "EMERGING_OCCURRENCE"
    REPEATED_PATTERN = "REPEATED_PATTERN"
    ACTIONABLE_PATTERN = "ACTIONABLE_PATTERN"


class CalculationStatus(str, Enum):
    """Execution status for single-session heuristic and composite aggregation."""
    SUCCESS = "SUCCESS"
    PARTIAL_FAILURE = "PARTIAL_FAILURE"
    FAILED = "FAILED"
    INSUFFICIENT_INPUT = "INSUFFICIENT_INPUT"


class ProvenanceTier(str, Enum):
    """Provenance tiers defining historical data fidelity for longitudinal trends."""
    TIER_1_NORMALIZED = "TIER_1_NORMALIZED"
    TIER_2_COMPACT_TAGS = "TIER_2_COMPACT_TAGS"
    TIER_3_DEFECT_STRING = "TIER_3_DEFECT_STRING"
    TIER_4_UNPROVENANCED = "TIER_4_UNPROVENANCED"


class ObservabilityCategory(str, Enum):
    """Mutually exclusive 5-way partition for repetition-level observations."""
    CATEGORY_NOT_OBSERVABLE = "CATEGORY_NOT_OBSERVABLE"
    CATEGORY_OCCLUDED = "CATEGORY_OCCLUDED"
    CATEGORY_LOW_CONFIDENCE = "CATEGORY_LOW_CONFIDENCE"
    CATEGORY_OBSERVED_ACCEPTABLE = "CATEGORY_OBSERVED_ACCEPTABLE"
    CATEGORY_OBSERVED_DEFECTIVE = "CATEGORY_OBSERVED_DEFECTIVE"


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


@dataclass(frozen=True)
class EvidenceAggregationConfig:
    """
    Authoritative engineering configuration for form evidence aggregation.
    
    Enforces canonical parameter names, individual bounds, volume invariants,
    and the Confidence Triad Invariant upon initialization.
    """
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
        # 1. Non-Boolean and Numeric Type Enforcement
        for field_name, val, expected_types in [
            ("MIN_HEURISTIC_CONFIDENCE", self.MIN_HEURISTIC_CONFIDENCE, (int, float)),
            ("ACTIONABLE_PATTERN_SESSION_MIN_CONFIDENCE", self.ACTIONABLE_PATTERN_SESSION_MIN_CONFIDENCE, (int, float)),
            ("ACTIONABLE_PATTERN_MIN_CONFIDENCE", self.ACTIONABLE_PATTERN_MIN_CONFIDENCE, (int, float)),
            ("MIN_TARGET_HEURISTIC_OBSERVED_REPS", self.MIN_TARGET_HEURISTIC_OBSERVED_REPS, (int,)),
            ("MIN_VALID_REPS_PER_SESSION", self.MIN_VALID_REPS_PER_SESSION, (int,)),
            ("SESSION_DEFECT_RATE_THRESHOLD", self.SESSION_DEFECT_RATE_THRESHOLD, (int, float)),
            ("REPEATED_PATTERN_MIN_SESSIONS", self.REPEATED_PATTERN_MIN_SESSIONS, (int,)),
            ("ACTIONABLE_PATTERN_MIN_SESSIONS", self.ACTIONABLE_PATTERN_MIN_SESSIONS, (int,)),
            ("LOOKBACK_SESSIONS_K", self.LOOKBACK_SESSIONS_K, (int,)),
            ("MIN_SESSION_OBSERVABILITY_RATIO", self.MIN_SESSION_OBSERVABILITY_RATIO, (int, float)),
        ]:
            if isinstance(val, bool) or not isinstance(val, expected_types):
                raise ValueError(f"Field {field_name} must be numeric of type {expected_types} and NOT bool; got {type(val).__name__} ({val})")
            if isinstance(val, (int, float)) and not math.isfinite(val):
                raise ValueError(f"Field {field_name} must be finite; got {val}")

        # 2. Individual Parameter Domain Bounds
        if not (0.10 <= self.MIN_HEURISTIC_CONFIDENCE <= 1.00):
            raise ValueError(f"MIN_HEURISTIC_CONFIDENCE must be in [0.10, 1.00], got {self.MIN_HEURISTIC_CONFIDENCE}")
        if not (0.10 <= self.ACTIONABLE_PATTERN_SESSION_MIN_CONFIDENCE <= 1.00):
            raise ValueError(f"ACTIONABLE_PATTERN_SESSION_MIN_CONFIDENCE must be in [0.10, 1.00], got {self.ACTIONABLE_PATTERN_SESSION_MIN_CONFIDENCE}")
        if not (0.10 <= self.ACTIONABLE_PATTERN_MIN_CONFIDENCE <= 1.00):
            raise ValueError(f"ACTIONABLE_PATTERN_MIN_CONFIDENCE must be in [0.10, 1.00], got {self.ACTIONABLE_PATTERN_MIN_CONFIDENCE}")
        if not (1 <= self.MIN_TARGET_HEURISTIC_OBSERVED_REPS <= 50):
            raise ValueError(f"MIN_TARGET_HEURISTIC_OBSERVED_REPS must be in [1, 50], got {self.MIN_TARGET_HEURISTIC_OBSERVED_REPS}")
        if not (1 <= self.MIN_VALID_REPS_PER_SESSION <= 50):
            raise ValueError(f"MIN_VALID_REPS_PER_SESSION must be in [1, 50], got {self.MIN_VALID_REPS_PER_SESSION}")
        if not (0.01 <= self.SESSION_DEFECT_RATE_THRESHOLD <= 1.00):
            raise ValueError(f"SESSION_DEFECT_RATE_THRESHOLD must be in [0.01, 1.00], got {self.SESSION_DEFECT_RATE_THRESHOLD}")
        if not (1 <= self.REPEATED_PATTERN_MIN_SESSIONS <= 20):
            raise ValueError(f"REPEATED_PATTERN_MIN_SESSIONS must be in [1, 20], got {self.REPEATED_PATTERN_MIN_SESSIONS}")
        if not (1 <= self.ACTIONABLE_PATTERN_MIN_SESSIONS <= 20):
            raise ValueError(f"ACTIONABLE_PATTERN_MIN_SESSIONS must be in [1, 20], got {self.ACTIONABLE_PATTERN_MIN_SESSIONS}")
        if not (3 <= self.LOOKBACK_SESSIONS_K <= 20):
            raise ValueError(f"LOOKBACK_SESSIONS_K must be in [3, 20], got {self.LOOKBACK_SESSIONS_K}")
        if not (0.10 <= self.MIN_SESSION_OBSERVABILITY_RATIO <= 1.00):
            raise ValueError(f"MIN_SESSION_OBSERVABILITY_RATIO must be in [0.10, 1.00], got {self.MIN_SESSION_OBSERVABILITY_RATIO}")

        # 3. Confidence Triad Invariant
        if not (self.MIN_HEURISTIC_CONFIDENCE <= self.ACTIONABLE_PATTERN_SESSION_MIN_CONFIDENCE <= self.ACTIONABLE_PATTERN_MIN_CONFIDENCE):
            raise ValueError(
                f"Confidence Triad Invariant violated: expected MIN_HEURISTIC_CONFIDENCE ({self.MIN_HEURISTIC_CONFIDENCE}) "
                f"<= ACTIONABLE_PATTERN_SESSION_MIN_CONFIDENCE ({self.ACTIONABLE_PATTERN_SESSION_MIN_CONFIDENCE}) "
                f"<= ACTIONABLE_PATTERN_MIN_CONFIDENCE ({self.ACTIONABLE_PATTERN_MIN_CONFIDENCE})"
            )

        # 4. Volume and Relational Invariants
        if self.MIN_TARGET_HEURISTIC_OBSERVED_REPS > self.MIN_VALID_REPS_PER_SESSION:
            raise ValueError(
                f"MIN_TARGET_HEURISTIC_OBSERVED_REPS ({self.MIN_TARGET_HEURISTIC_OBSERVED_REPS}) "
                f"cannot exceed MIN_VALID_REPS_PER_SESSION ({self.MIN_VALID_REPS_PER_SESSION})"
            )
        if self.REPEATED_PATTERN_MIN_SESSIONS > self.ACTIONABLE_PATTERN_MIN_SESSIONS:
            raise ValueError(
                f"REPEATED_PATTERN_MIN_SESSIONS ({self.REPEATED_PATTERN_MIN_SESSIONS}) "
                f"cannot exceed ACTIONABLE_PATTERN_MIN_SESSIONS ({self.ACTIONABLE_PATTERN_MIN_SESSIONS})"
            )
        if self.ACTIONABLE_PATTERN_MIN_SESSIONS > self.LOOKBACK_SESSIONS_K:
            raise ValueError(
                f"ACTIONABLE_PATTERN_MIN_SESSIONS ({self.ACTIONABLE_PATTERN_MIN_SESSIONS}) "
                f"cannot exceed LOOKBACK_SESSIONS_K ({self.LOOKBACK_SESSIONS_K})"
            )
