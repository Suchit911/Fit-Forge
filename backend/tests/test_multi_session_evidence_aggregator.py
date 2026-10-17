"""
Focused Unit Tests for MultiSessionEvidenceAggregator (Subphase 9C.6.2.3).

Covers:
- Approach B lookback selection: Filter all eligible first, then take latest K=5.
- T23: Legacy provenance exclusion (TIER_4_UNPROVENANCED).
- T27: Bounded lookback window invariant (latest 5 eligible of 8).
- T28: Issue-level data sufficiency gate (N_target_eval < 3 -> INSUFFICIENT_DATA).
- T29: Zero qualifying sessions (N_qualifying == 0 -> NO_EVIDENCE, qualifying_mean_confidence = None).
- T30: Actionable dual-gate pass (all sessions >= 0.55, mean >= 0.60 -> ACTIONABLE_PATTERN).
- T31: Actionable per-session confidence-floor failure (session at 0.52 < 0.55 -> REPEATED_PATTERN).
- T32: Confidence Triad Invariant interaction at initialization.
- T19: Multi-heuristic failure isolation (Torso FAILED -> +0/+0, INSUFFICIENT_DATA; Depth -> ACTIONABLE).
- Single qualifying session -> EMERGING_OCCURRENCE.
- Two qualifying sessions -> REPEATED_PATTERN.
- Deterministic 4-step precedence ladder verification.
- Complete ExerciseEvidenceSummary composite aggregation and provenance tracking.
"""

import pytest
from typing import Dict, List, Optional

from backend.app.schemas.form_evidence import (
    EvidenceLevel,
    CalculationStatus,
    ProvenanceTier,
    EvidenceAggregationConfig,
    SessionIssueSummary,
    SessionEvidenceRecord,
    AggregatedIssueEvidence,
    ExerciseEvidenceSummary,
)
from backend.app.services.form_analysis.multi_session_evidence_aggregator import (
    MultiSessionEvidenceAggregator,
)


# =============================================================================
# TEST FACTORIES
# =============================================================================

def make_issue_summary(
    issue_id: str = "insufficient_depth",
    source_heuristic: str = "squat_depth",
    category: str = "ROM",
    calculation_status: CalculationStatus = CalculationStatus.SUCCESS,
    target_reps_total: int = 10,
    target_reps_observed: int = 10,
    target_reps_defective: int = 6,
    defect_rate: Optional[float] = 0.60,
    mean_confidence: Optional[float] = 0.80,
    target_reps_occluded: int = 0,
    data_quality_flags: Optional[List[str]] = None,
) -> SessionIssueSummary:
    """Creates a mock SessionIssueSummary with default or customized fields."""
    return SessionIssueSummary(
        issue_id=issue_id,
        source_heuristic=source_heuristic,
        category=category,
        calculation_status=calculation_status,
        data_quality_flags=data_quality_flags or [],
        target_reps_total=target_reps_total,
        target_reps_observed=target_reps_observed,
        target_reps_defective=target_reps_defective,
        target_reps_occluded=target_reps_occluded,
        target_reps_low_confidence=0,
        target_reps_not_observable=0,
        target_reps_used_for_defect_rate=target_reps_observed,
        defect_rate=defect_rate,
        mean_confidence=mean_confidence,
    )


def make_session(
    session_id: str,
    exercise_id: str = "ex_squat",
    completed_at: str = "2026-09-28T12:00:00Z",
    valid_reps: int = 10,
    total_reps: int = 10,
    session_observability_ratio: float = 1.0,
    calculation_status: CalculationStatus = CalculationStatus.SUCCESS,
    provenance_tier: ProvenanceTier = ProvenanceTier.TIER_1_NORMALIZED,
    issues: Optional[Dict[str, SessionIssueSummary]] = None,
    is_eligible_for_trends: bool = True,
) -> SessionEvidenceRecord:
    """Creates a mock SessionEvidenceRecord with specified metadata and issues."""
    iss_dict = issues if issues is not None else {
        "insufficient_depth": make_issue_summary()
    }
    return SessionEvidenceRecord(
        session_id=session_id,
        user_id="user_test",
        exercise_id=exercise_id,
        completed_at=completed_at,
        total_reps=total_reps,
        valid_reps=valid_reps,
        session_observability_ratio=session_observability_ratio,
        is_eligible_for_trends=is_eligible_for_trends,
        calculation_status=calculation_status,
        data_quality_flags=[],
        provenance_tier=provenance_tier,
        issues=iss_dict,
        normalized_issues=[],
    )


@pytest.fixture
def multi_aggregator() -> MultiSessionEvidenceAggregator:
    return MultiSessionEvidenceAggregator()


# =============================================================================
# APPROACH B LOOKBACK SELECTION & T27 BOUNDED WINDOW INVARIANT
# =============================================================================

def test_t27_lookback_boundary_k_equals_5(multi_aggregator: MultiSessionEvidenceAggregator):
    """
    T27: When 8 eligible sessions exist, exactly the latest 5 are selected
    into the lookback window (N_session_eligible == 5).
    """
    sessions = [
        make_session(
            session_id=f"sess_{i}",
            completed_at=f"2026-09-0{i}T12:00:00Z",
        )
        for i in range(1, 9)
    ]
    lookback = multi_aggregator.select_lookback_sessions(sessions, lookback_k=5)
    assert len(lookback) == 5
    # Must be the latest 5: sess_8, sess_7, sess_6, sess_5, sess_4
    expected_ids = {"sess_8", "sess_7", "sess_6", "sess_5", "sess_4"}
    actual_ids = {s.session_id for s in lookback}
    assert actual_ids == expected_ids


def test_approach_b_filter_eligible_first_sequence(multi_aggregator: MultiSessionEvidenceAggregator):
    """
    Approach B Requirement: Filter all completed sessions to eligible FIRST,
    then select latest K.

    Scenario:
    - 8 historical sessions:
      * 3 most recent sessions are INELIGIBLE (e.g. valid_reps = 1, observability = 0.50, status = FAILED)
      * 5 older sessions are fully ELIGIBLE (valid_reps = 10, observability = 1.0)
    Under Approach B: The 5 older eligible sessions must be selected.
    Under Approach A (erroneous): Taking latest 5 first would leave only 2 eligible sessions.
    """
    # 5 older eligible sessions
    older_eligible = [
        make_session(
            session_id=f"old_elig_{i}",
            completed_at=f"2026-09-0{i}T10:00:00Z",
            valid_reps=10,
            session_observability_ratio=1.0,
            calculation_status=CalculationStatus.SUCCESS,
        )
        for i in range(1, 6)
    ]
    # 3 recent ineligible sessions
    recent_ineligible = [
        make_session(
            session_id="rec_inelig_1",
            completed_at="2026-09-10T10:00:00Z",
            valid_reps=1,  # < 3
            session_observability_ratio=1.0,
        ),
        make_session(
            session_id="rec_inelig_2",
            completed_at="2026-09-11T10:00:00Z",
            valid_reps=10,
            session_observability_ratio=0.50,  # < 0.70
        ),
        make_session(
            session_id="rec_inelig_3",
            completed_at="2026-09-12T10:00:00Z",
            valid_reps=10,
            session_observability_ratio=1.0,
            calculation_status=CalculationStatus.FAILED,  # FAILED
        ),
    ]

    all_sessions = older_eligible + recent_ineligible

    # Execute Approach B
    eligible = multi_aggregator.filter_eligible_sessions(all_sessions, exercise_id="ex_squat")
    assert len(eligible) == 5

    lookback = multi_aggregator.select_lookback_sessions(eligible, lookback_k=5)
    assert len(lookback) == 5
    lookback_ids = {s.session_id for s in lookback}
    expected_ids = {f"old_elig_{i}" for i in range(1, 6)}
    assert lookback_ids == expected_ids


# =============================================================================
# T23: PROVENANCE TIER FILTERING
# =============================================================================

def test_t23_legacy_tier_4_provenance_exclusion(multi_aggregator: MultiSessionEvidenceAggregator):
    """
    T23: Sessions with provenance_tier = TIER_4_UNPROVENANCED are excluded
    from the lookback window to prevent unprovenanced data corruption.
    """
    sessions = [
        make_session(session_id="sess_norm_1", provenance_tier=ProvenanceTier.TIER_1_NORMALIZED),
        make_session(session_id="sess_norm_2", provenance_tier=ProvenanceTier.TIER_2_COMPACT_TAGS),
        make_session(session_id="sess_legacy", provenance_tier=ProvenanceTier.TIER_4_UNPROVENANCED),
        make_session(session_id="sess_norm_3", provenance_tier=ProvenanceTier.TIER_3_DEFECT_STRING),
    ]
    eligible = multi_aggregator.filter_eligible_sessions(sessions, exercise_id="ex_squat")
    assert len(eligible) == 3
    eligible_ids = [s.session_id for s in eligible]
    assert "sess_legacy" not in eligible_ids
    assert "sess_norm_1" in eligible_ids
    assert "sess_norm_2" in eligible_ids
    assert "sess_norm_3" in eligible_ids


# =============================================================================
# T28: ISSUE-LEVEL DATA SUFFICIENCY GATE (N_target_eval < 3)
# =============================================================================

def test_t28_target_eval_under_3_insufficient_data(multi_aggregator: MultiSessionEvidenceAggregator):
    """
    T28: 5 eligible sessions exist, but target heuristic had observed reps >= 3
    in only 2 sessions -> N_target_eval = 2 < 3 -> INSUFFICIENT_DATA.
    """
    sessions = []
    # 2 sessions with observed reps = 5 (qualifies for target eval)
    for i in range(1, 3):
        iss = make_issue_summary(target_reps_observed=5, defect_rate=0.60, mean_confidence=0.80)
        sessions.append(make_session(session_id=f"sess_{i}", completed_at=f"2026-09-0{i}T10:00:00Z", issues={"insufficient_depth": iss}))

    # 3 sessions with observed reps = 1 (< 3 MIN_TARGET_HEURISTIC_OBSERVED_REPS)
    for i in range(3, 6):
        iss = make_issue_summary(target_reps_observed=1, defect_rate=1.0, mean_confidence=0.80)
        sessions.append(make_session(session_id=f"sess_{i}", completed_at=f"2026-09-0{i}T10:00:00Z", issues={"insufficient_depth": iss}))

    evidence = multi_aggregator.aggregate_issue_longitudinal(
        issue_id="insufficient_depth",
        source_heuristic="squat_depth",
        category="ROM",
        lookback_sessions=sessions,
    )

    assert evidence.session_eligible_count == 5
    assert evidence.target_evaluated_sessions_count == 2  # < 3
    assert evidence.evidence_level == EvidenceLevel.INSUFFICIENT_DATA
    assert evidence.recurrence_ratio == 0.0
    assert "FLAG_INSUFFICIENT_DATA" in evidence.data_quality_flags


# =============================================================================
# T29: ZERO QUALIFYING SESSIONS (N_qualifying == 0)
# =============================================================================

def test_t29_zero_qualifying_sessions_no_evidence(multi_aggregator: MultiSessionEvidenceAggregator):
    """
    T29: 5 eligible sessions, all with N_target_eval >= 3, defect rate 0% across all
    sessions (N_qualifying == 0) -> NO_EVIDENCE, qualifying_mean_confidence = None.
    """
    sessions = [
        make_session(
            session_id=f"sess_{i}",
            completed_at=f"2026-09-0{i}T10:00:00Z",
            issues={
                "insufficient_depth": make_issue_summary(
                    target_reps_observed=10,
                    target_reps_defective=0,
                    defect_rate=0.0,
                    mean_confidence=0.85,
                )
            },
        )
        for i in range(1, 6)
    ]

    evidence = multi_aggregator.aggregate_issue_longitudinal(
        issue_id="insufficient_depth",
        source_heuristic="squat_depth",
        category="ROM",
        lookback_sessions=sessions,
    )

    assert evidence.session_eligible_count == 5
    assert evidence.target_evaluated_sessions_count == 5
    assert evidence.qualifying_sessions_count == 0
    assert evidence.recurrence_ratio == 0.0
    assert evidence.qualifying_mean_confidence is None  # Strictly None, never 0.0
    assert evidence.evidence_level == EvidenceLevel.NO_EVIDENCE


# =============================================================================
# T30: ACTIONABLE DUAL-GATE PASS (ACTIONABLE_PATTERN)
# =============================================================================

def test_t30_actionable_dual_gate_pass(multi_aggregator: MultiSessionEvidenceAggregator):
    """
    T30: 3 qualifying sessions satisfying both gates:
    S1 = 0.58, S2 = 0.62, S3 = 0.66 (all >= 0.55 per-session floor; mean 0.62 >= 0.60).
    Zero occlusions on target repetitions.
    Classified as ACTIONABLE_PATTERN.
    """
    confs = [0.58, 0.62, 0.66]
    sessions = [
        make_session(
            session_id=f"sess_{i+1}",
            completed_at=f"2026-09-0{i+1}T10:00:00Z",
            issues={
                "insufficient_depth": make_issue_summary(
                    target_reps_observed=10,
                    target_reps_defective=6,
                    defect_rate=0.60,
                    mean_confidence=confs[i],
                    target_reps_occluded=0,
                )
            },
        )
        for i in range(3)
    ]

    evidence = multi_aggregator.aggregate_issue_longitudinal(
        issue_id="insufficient_depth",
        source_heuristic="squat_depth",
        category="ROM",
        lookback_sessions=sessions,
    )

    assert evidence.session_eligible_count == 3
    assert evidence.target_evaluated_sessions_count == 3
    assert evidence.qualifying_sessions_count == 3
    assert evidence.recurrence_ratio == pytest.approx(1.0)
    assert evidence.qualifying_mean_confidence == pytest.approx(0.62)
    assert evidence.evidence_level == EvidenceLevel.ACTIONABLE_PATTERN
    assert "FLAG_ACTIONABLE_PATTERN_QUALIFIED" in evidence.data_quality_flags


# =============================================================================
# T31: ACTIONABLE SESSION FLOOR FAIL (DEMOTION TO REPEATED_PATTERN)
# =============================================================================

def test_t31_actionable_session_floor_fail_demotion(multi_aggregator: MultiSessionEvidenceAggregator):
    """
    T31: 3 qualifying sessions:
    S1 = 0.52 (< 0.55 floor breach!), S2 = 0.70, S3 = 0.70.
    Aggregate mean is (0.52 + 0.70 + 0.70) / 3 = 0.64 (>= 0.60).
    Per-session floor breach forces demotion to REPEATED_PATTERN.
    """
    confs = [0.52, 0.70, 0.70]
    sessions = [
        make_session(
            session_id=f"sess_{i+1}",
            completed_at=f"2026-09-0{i+1}T10:00:00Z",
            issues={
                "insufficient_depth": make_issue_summary(
                    target_reps_observed=10,
                    target_reps_defective=6,
                    defect_rate=0.60,
                    mean_confidence=confs[i],
                    target_reps_occluded=0,
                )
            },
        )
        for i in range(3)
    ]

    evidence = multi_aggregator.aggregate_issue_longitudinal(
        issue_id="insufficient_depth",
        source_heuristic="squat_depth",
        category="ROM",
        lookback_sessions=sessions,
    )

    assert evidence.qualifying_sessions_count == 3
    assert evidence.qualifying_mean_confidence == pytest.approx(0.64)
    assert evidence.evidence_level == EvidenceLevel.REPEATED_PATTERN
    assert "FLAG_SESSION_CONFIDENCE_FLOOR_BREACH" in evidence.data_quality_flags
    assert "FLAG_REPEATED_PATTERN_DEMOTION" in evidence.data_quality_flags


def test_actionable_target_occlusion_demotion(multi_aggregator: MultiSessionEvidenceAggregator):
    """
    Qualifying session with target_reps_occluded > 0 breaches occlusion condition
    and demotes to REPEATED_PATTERN.
    """
    confs = [0.65, 0.65, 0.65]
    sessions = [
        make_session(
            session_id=f"sess_{i+1}",
            completed_at=f"2026-09-0{i+1}T10:00:00Z",
            issues={
                "insufficient_depth": make_issue_summary(
                    target_reps_observed=10,
                    target_reps_defective=6,
                    defect_rate=0.60,
                    mean_confidence=confs[i],
                    target_reps_occluded=1 if i == 0 else 0,  # Session 1 has target occlusion
                )
            },
        )
        for i in range(3)
    ]

    evidence = multi_aggregator.aggregate_issue_longitudinal(
        issue_id="insufficient_depth",
        source_heuristic="squat_depth",
        category="ROM",
        lookback_sessions=sessions,
    )

    assert evidence.evidence_level == EvidenceLevel.REPEATED_PATTERN
    assert "FLAG_TARGET_REPETITION_OCCLUSION_DETECTED" in evidence.data_quality_flags


# =============================================================================
# T32: CONFIDENCE TRIAD INVARIANT AT STARTUP
# =============================================================================

def test_t32_confidence_triad_invariant_startup():
    """T32: Startup configuration with inverted confidence thresholds raises ValueError."""
    with pytest.raises(ValueError, match="Confidence Triad Invariant violated"):
        EvidenceAggregationConfig(
            MIN_HEURISTIC_CONFIDENCE=0.58,  # > 0.55 session floor!
            ACTIONABLE_PATTERN_SESSION_MIN_CONFIDENCE=0.55,
            ACTIONABLE_PATTERN_MIN_CONFIDENCE=0.60,
        )


# =============================================================================
# T19: MULTI-HEURISTIC PARTIAL FAILURE ISOLATION IN LONGITUDINAL AGGREGATION
# =============================================================================

def test_t19_multi_session_partial_failure_isolation(multi_aggregator: MultiSessionEvidenceAggregator):
    """
    T19: Multi-session scenario with 3 sessions where:
    - Depth: SUCCESS in all 3 sessions (defect rate 0.60, conf 0.82)
    - Torso Inclination: FAILED in all 3 sessions (calculation exception)
    - Knee Tracking: SUCCESS in all 3 sessions (defect rate 0.0, conf 0.78)

    Asserts:
    - Depth succeeds and qualifies (ACTIONABLE_PATTERN)
    - Knee tracking succeeds and qualifies for clean tracking (NO_EVIDENCE)
    - Torso inclination contributes +0 to N_target_eval, evaluates to INSUFFICIENT_DATA,
      and does NOT become NO_EVIDENCE.
    """
    sessions = []
    for i in range(1, 4):
        depth_iss = make_issue_summary(
            issue_id="insufficient_depth",
            source_heuristic="squat_depth",
            calculation_status=CalculationStatus.SUCCESS,
            defect_rate=0.60,
            mean_confidence=0.82,
        )
        knee_iss = make_issue_summary(
            issue_id="knee_tracking_deviation",
            source_heuristic="squat_knee_tracking",
            calculation_status=CalculationStatus.SUCCESS,
            target_reps_defective=0,
            defect_rate=0.0,
            mean_confidence=0.78,
        )
        torso_iss = make_issue_summary(
            issue_id="excessive_torso_lean",
            source_heuristic="squat_torso_inclination",
            calculation_status=CalculationStatus.FAILED,  # FAILED
            defect_rate=None,
            mean_confidence=None,
            data_quality_flags=["ERROR_HEURISTIC_CALCULATION_FAILED"],
        )
        sess = make_session(
            session_id=f"sess_pf_{i}",
            completed_at=f"2026-09-0{i}T10:00:00Z",
            calculation_status=CalculationStatus.PARTIAL_FAILURE,
            issues={
                "insufficient_depth": depth_iss,
                "knee_tracking_deviation": knee_iss,
                "excessive_torso_lean": torso_iss,
            },
        )
        sessions.append(sess)

    summary = multi_aggregator.aggregate_exercise_evidence(
        sessions=sessions,
        exercise_id="ex_squat",
    )

    # 1. Depth evaluates to ACTIONABLE_PATTERN
    assert "insufficient_depth" in summary.issues
    depth_ev = summary.issues["insufficient_depth"]
    assert depth_ev.target_evaluated_sessions_count == 3
    assert depth_ev.qualifying_sessions_count == 3
    assert depth_ev.evidence_level == EvidenceLevel.ACTIONABLE_PATTERN

    # 2. Knee tracking evaluates to NO_EVIDENCE
    assert "knee_tracking_deviation" in summary.issues
    knee_ev = summary.issues["knee_tracking_deviation"]
    assert knee_ev.target_evaluated_sessions_count == 3
    assert knee_ev.qualifying_sessions_count == 0
    assert knee_ev.evidence_level == EvidenceLevel.NO_EVIDENCE

    # 3. Torso inclination evaluates to INSUFFICIENT_DATA (+0/+0, never NO_EVIDENCE)
    assert "excessive_torso_lean" in summary.issues
    torso_ev = summary.issues["excessive_torso_lean"]
    assert torso_ev.target_evaluated_sessions_count == 0
    assert torso_ev.qualifying_sessions_count == 0
    assert torso_ev.evidence_level == EvidenceLevel.INSUFFICIENT_DATA
    assert torso_ev.evidence_level != EvidenceLevel.NO_EVIDENCE


# =============================================================================
# SINGLE & TWO QUALIFYING SESSIONS (EMERGING VS REPEATED)
# =============================================================================

def test_single_qualifying_session_emerging_occurrence(multi_aggregator: MultiSessionEvidenceAggregator):
    """
    N_qualifying == 1 with N_target_eval >= 3 classifies as EMERGING_OCCURRENCE.
    """
    sessions = []
    # 1 qualifying session (defect rate = 0.60)
    sessions.append(
        make_session(
            session_id="sess_qual",
            completed_at="2026-09-01T10:00:00Z",
            issues={"insufficient_depth": make_issue_summary(defect_rate=0.60, mean_confidence=0.80)},
        )
    )
    # 2 clean sessions (defect rate = 0.0)
    for i in range(2, 4):
        sessions.append(
            make_session(
                session_id=f"sess_clean_{i}",
                completed_at=f"2026-09-0{i}T10:00:00Z",
                issues={"insufficient_depth": make_issue_summary(defect_rate=0.0, target_reps_defective=0, mean_confidence=0.80)},
            )
        )

    evidence = multi_aggregator.aggregate_issue_longitudinal(
        issue_id="insufficient_depth",
        source_heuristic="squat_depth",
        category="ROM",
        lookback_sessions=sessions,
    )

    assert evidence.target_evaluated_sessions_count == 3
    assert evidence.qualifying_sessions_count == 1
    assert evidence.recurrence_ratio == pytest.approx(0.3333, abs=1e-3)
    assert evidence.evidence_level == EvidenceLevel.EMERGING_OCCURRENCE


def test_two_qualifying_sessions_repeated_pattern(multi_aggregator: MultiSessionEvidenceAggregator):
    """
    N_qualifying == 2 with N_target_eval >= 3 classifies as REPEATED_PATTERN.
    """
    sessions = []
    # 2 qualifying sessions
    for i in range(1, 3):
        sessions.append(
            make_session(
                session_id=f"sess_qual_{i}",
                completed_at=f"2026-09-0{i}T10:00:00Z",
                issues={"insufficient_depth": make_issue_summary(defect_rate=0.60, mean_confidence=0.80)},
            )
        )
    # 1 clean session
    sessions.append(
        make_session(
            session_id="sess_clean",
            completed_at="2026-09-03T10:00:00Z",
            issues={"insufficient_depth": make_issue_summary(defect_rate=0.0, target_reps_defective=0, mean_confidence=0.80)},
        )
    )

    evidence = multi_aggregator.aggregate_issue_longitudinal(
        issue_id="insufficient_depth",
        source_heuristic="squat_depth",
        category="ROM",
        lookback_sessions=sessions,
    )

    assert evidence.target_evaluated_sessions_count == 3
    assert evidence.qualifying_sessions_count == 2
    assert evidence.recurrence_ratio == pytest.approx(0.6667, abs=1e-3)
    assert evidence.evidence_level == EvidenceLevel.REPEATED_PATTERN


# =============================================================================
# DETERMINISTIC PRECEDENCE LADDER GUARANTEE
# =============================================================================

def test_deterministic_precedence_ladder(multi_aggregator: MultiSessionEvidenceAggregator):
    """
    Verifies that the 4-step precedence ladder is strictly enforced:
    - If N_session_eligible < 3: INSUFFICIENT_DATA even if qualifying == 1 or 2.
    - If N_target_eval < 3: INSUFFICIENT_DATA even if qualifying == 1 or 2.
    """
    # 2 sessions only (N_session_eligible = 2 < 3)
    sessions = [
        make_session(
            session_id=f"sess_{i}",
            completed_at=f"2026-09-0{i}T10:00:00Z",
            issues={"insufficient_depth": make_issue_summary(defect_rate=0.60)},
        )
        for i in range(1, 3)
    ]

    evidence = multi_aggregator.aggregate_issue_longitudinal(
        issue_id="insufficient_depth",
        source_heuristic="squat_depth",
        category="ROM",
        lookback_sessions=sessions,
    )

    # Step 1 catches N_session_eligible < 3 before Step 4 can run
    assert evidence.session_eligible_count == 2
    assert evidence.evidence_level == EvidenceLevel.INSUFFICIENT_DATA
