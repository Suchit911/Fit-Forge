"""
Minimal Smoke & Structural Verification Tests for CorrectiveGuidanceService (Phase 9C.6.3 Step 2).

Verifies:
- Service imports successfully.
- Valid constructor and dependency injection.
- EvidenceLevel gate is reachable.
- Supplied ExerciseEvidenceSummary can be consumed (Mode A).
- Zero candidate generation occurs for NO_EVIDENCE.
- Zero candidate generation occurs for INSUFFICIENT_DATA.
- Zero candidate generation occurs for EMERGING_OCCURRENCE.
- Service can construct a valid REPEATED_PATTERN response (is_eligible_for_proposal = False).
- Service can construct a valid ACTIONABLE_PATTERN response (is_eligible_for_proposal = True).
- Mandatory disclaimer is always present.
- Proposal eligibility strictly follows evidence level.
- Limit boundaries (1 <= limit <= 10) are enforced.
- Mode B (omitted evidence_summary) fallback executes cleanly.
"""

import pytest
from datetime import datetime, timezone
from typing import Dict, List, Optional

from backend.app.schemas.form_evidence import (
    EvidenceLevel,
    CalculationStatus,
    AggregatedIssueEvidence,
    ExerciseEvidenceSummary,
)
from backend.app.schemas.corrective_guidance import (
    CorrectiveGuidanceResponse,
    AUTHORITATIVE_CORRECTIVE_DISCLAIMER,
)
from backend.app.services.form_analysis.corrective_guidance_service import (
    CorrectiveGuidanceService,
    get_corrective_guidance_service,
)
from backend.app.repositories.form_analysis_repository import (
    FormAnalysisRepository,
)


# =============================================================================
# FIXTURES & SUMMARY FACTORIES
# =============================================================================

@pytest.fixture
def service() -> CorrectiveGuidanceService:
    repo = FormAnalysisRepository(db=None)
    repo.clear_in_memory_for_testing()
    return CorrectiveGuidanceService(repository=repo)


def make_summary(
    exercise_id: str = "ex_squat",
    user_id: str = "user-smoke-1",
    level: EvidenceLevel = EvidenceLevel.ACTIONABLE_PATTERN,
    issue_id: Optional[str] = "insufficient_depth",
) -> ExerciseEvidenceSummary:
    issues: Dict[str, AggregatedIssueEvidence] = {}
    if issue_id:
        issues[issue_id] = AggregatedIssueEvidence(
            issue_id=issue_id,
            source_heuristic="squat_depth",
            category="ROM",
            session_eligible_count=4,
            target_evaluated_sessions_count=4,
            qualifying_sessions_count=4 if level in (EvidenceLevel.ACTIONABLE_PATTERN, EvidenceLevel.REPEATED_PATTERN) else (1 if level == EvidenceLevel.EMERGING_OCCURRENCE else 0),
            recurrence_ratio=1.0 if level in (EvidenceLevel.ACTIONABLE_PATTERN, EvidenceLevel.REPEATED_PATTERN) else (0.25 if level == EvidenceLevel.EMERGING_OCCURRENCE else 0.0),
            qualifying_mean_confidence=0.85 if level == EvidenceLevel.ACTIONABLE_PATTERN else (0.50 if level == EvidenceLevel.REPEATED_PATTERN else None),
            evidence_level=level,
            aggregation_version="2.3.3",
            config_version="1.0.0",
        )

    return ExerciseEvidenceSummary(
        aggregation_version="2.3.3",
        config_version="1.0.0",
        user_id=user_id,
        exercise_id=exercise_id,
        lookback_sessions_evaluated=4,
        eligible_sessions_count=4,
        evaluated_at=datetime.now(timezone.utc).isoformat(),
        primary_issue_id=issue_id,
        evidence_level=level,
        status_message="Test status",
        calculation_status=CalculationStatus.SUCCESS,
        issues=issues,
    )


# =============================================================================
# TESTS
# =============================================================================

def test_service_import_and_singleton():
    """Verify service imports and singleton accessor functions."""
    svc = get_corrective_guidance_service()
    assert isinstance(svc, CorrectiveGuidanceService)
    svc2 = get_corrective_guidance_service()
    assert svc is svc2


def test_no_evidence_gate(service: CorrectiveGuidanceService):
    """NO_EVIDENCE produces empty candidates, is_eligible_for_proposal=False, disclaimer present."""
    summary = make_summary(level=EvidenceLevel.NO_EVIDENCE, issue_id="insufficient_depth")
    res = service.get_corrective_guidance(
        exercise_id="ex_squat",
        user_id="user-smoke-1",
        evidence_summary=summary,
    )
    assert isinstance(res, CorrectiveGuidanceResponse)
    assert res.evidence_level == EvidenceLevel.NO_EVIDENCE
    assert res.candidates == []
    assert res.is_eligible_for_proposal is False
    assert res.disclaimer == AUTHORITATIVE_CORRECTIVE_DISCLAIMER


def test_insufficient_data_gate(service: CorrectiveGuidanceService):
    """INSUFFICIENT_DATA produces empty candidates, is_eligible_for_proposal=False, disclaimer present."""
    summary = make_summary(level=EvidenceLevel.INSUFFICIENT_DATA, issue_id=None)
    res = service.get_corrective_guidance(
        exercise_id="ex_squat",
        user_id="user-smoke-1",
        evidence_summary=summary,
    )
    assert res.evidence_level == EvidenceLevel.INSUFFICIENT_DATA
    assert res.candidates == []
    assert res.is_eligible_for_proposal is False
    assert res.disclaimer == AUTHORITATIVE_CORRECTIVE_DISCLAIMER


def test_emerging_occurrence_gate(service: CorrectiveGuidanceService):
    """EMERGING_OCCURRENCE produces empty candidates, is_eligible_for_proposal=False, disclaimer present."""
    summary = make_summary(level=EvidenceLevel.EMERGING_OCCURRENCE, issue_id="insufficient_depth")
    res = service.get_corrective_guidance(
        exercise_id="ex_squat",
        user_id="user-smoke-1",
        evidence_summary=summary,
    )
    assert res.evidence_level == EvidenceLevel.EMERGING_OCCURRENCE
    assert res.candidates == []
    assert res.is_eligible_for_proposal is False
    assert res.disclaimer == AUTHORITATIVE_CORRECTIVE_DISCLAIMER


def test_repeated_pattern_response(service: CorrectiveGuidanceService):
    """REPEATED_PATTERN returns candidate drills, is_eligible_for_proposal=False."""
    summary = make_summary(level=EvidenceLevel.REPEATED_PATTERN, issue_id="insufficient_depth")
    res = service.get_corrective_guidance(
        exercise_id="ex_squat",
        user_id="user-smoke-1",
        evidence_summary=summary,
        user_available_equipment=["barbell", "dumbbell", "bodyweight", "box"],
        limit=3,
    )
    assert res.evidence_level == EvidenceLevel.REPEATED_PATTERN
    assert len(res.candidates) > 0
    assert len(res.candidates) <= 3
    assert res.is_eligible_for_proposal is False
    for cand in res.candidates:
        assert cand.is_proposal_candidate is False
        assert cand.score > 0
        assert len(cand.educational_cue) > 0
    assert res.disclaimer == AUTHORITATIVE_CORRECTIVE_DISCLAIMER


def test_actionable_pattern_response(service: CorrectiveGuidanceService):
    """ACTIONABLE_PATTERN returns candidate drills, is_eligible_for_proposal=True."""
    summary = make_summary(level=EvidenceLevel.ACTIONABLE_PATTERN, issue_id="insufficient_depth")
    res = service.get_corrective_guidance(
        exercise_id="ex_squat",
        user_id="user-smoke-1",
        evidence_summary=summary,
        user_available_equipment=["barbell", "dumbbell", "bodyweight", "box"],
        limit=3,
    )
    assert res.evidence_level == EvidenceLevel.ACTIONABLE_PATTERN
    assert len(res.candidates) > 0
    assert res.is_eligible_for_proposal is True
    for cand in res.candidates:
        assert cand.is_proposal_candidate is True
    assert res.disclaimer == AUTHORITATIVE_CORRECTIVE_DISCLAIMER


def test_limit_validation(service: CorrectiveGuidanceService):
    """Enforces 1 <= limit <= 10."""
    summary = make_summary(level=EvidenceLevel.ACTIONABLE_PATTERN)
    with pytest.raises(ValueError):
        service.get_corrective_guidance("ex_squat", "user-1", evidence_summary=summary, limit=0)
    with pytest.raises(ValueError):
        service.get_corrective_guidance("ex_squat", "user-1", evidence_summary=summary, limit=11)


def test_mode_b_omitted_evidence_summary(service: CorrectiveGuidanceService):
    """Mode B executes cleanly when evidence_summary is omitted (zero historical sessions yields INSUFFICIENT_DATA)."""
    res = service.get_corrective_guidance(
        exercise_id="ex_squat",
        user_id="new-user-no-history",
        evidence_summary=None,
    )
    assert isinstance(res, CorrectiveGuidanceResponse)
    assert res.evidence_level in (EvidenceLevel.INSUFFICIENT_DATA, EvidenceLevel.NO_EVIDENCE)
    assert res.candidates == []
    assert res.is_eligible_for_proposal is False
    assert res.disclaimer == AUTHORITATIVE_CORRECTIVE_DISCLAIMER


def test_ranking_precision_distinguishes_scores_with_same_rounded_display(
    service: CorrectiveGuidanceService, monkeypatch: pytest.MonkeyPatch
):
    """
    Demonstrates that full-precision score is used for ranking:
    Cand Z has raw score 84.506 (rounds to 84.51 display).
    Cand A has raw score 84.504 (rounds to 84.51 display).
    Under 2-decimal pre-rounding, both tie at 84.51 and Cand A would rank first by alphabetical ID.
    Under authoritative full-precision ranking, Cand Z ranks first because 84.506 > 84.504.
    Both output candidates display score = 84.51 strictly rounded after sorting.
    """
    from backend.app.schemas.exercise import (
        ExerciseRecommendationResponse,
        ExerciseRecommendationNode,
    )

    node_z = ExerciseRecommendationNode(
        exercise_id="ex_cand_z",
        name="Candidate Z",
        movement_pattern="squat",
        exercise_type="isolation",
        difficulty="beginner",
        score=84.514,
        reasons=["Technique drill Z."],
    )
    node_a = ExerciseRecommendationNode(
        exercise_id="ex_cand_a",
        name="Candidate A",
        movement_pattern="squat",
        exercise_type="isolation",
        difficulty="beginner",
        score=84.506,
        reasons=["Technique drill A."],
    )

    # Return node_a first from delegated service to test that sorting re-orders by full precision
    mock_resp = ExerciseRecommendationResponse(candidates=[node_a, node_z])
    monkeypatch.setattr(service._recommendation_service, "recommend", lambda req: mock_resp)

    summary = make_summary(level=EvidenceLevel.ACTIONABLE_PATTERN)
    res = service.get_corrective_guidance("ex_squat", "user-1", evidence_summary=summary, limit=5)

    assert len(res.candidates) == 2
    # Full precision places 84.506 (Cand Z) ahead of 84.504 (Cand A), despite alphabetical tie-break favoring A
    assert res.candidates[0].exercise_id == "ex_cand_z"
    assert res.candidates[1].exercise_id == "ex_cand_a"
    # Both display scores are rounded strictly to 2 decimal places (84.51)
    assert res.candidates[0].score == 84.51
    assert res.candidates[1].score == 84.51
