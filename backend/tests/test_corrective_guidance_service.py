"""
Authoritative Comprehensive Unit Test Suite for CorrectiveGuidanceService (Phase 9C.6.3 Step 3).

Comprehensive deterministic coverage of:
- Category A: Service Construction and Input Validation
- Category B: Evidence Resolution (Mode A, Mode B, Repository Fallbacks, Snapshot Immutability)
- Category C: Evidence-Level Qualification Gates (NO_EVIDENCE, INSUFFICIENT_DATA, EMERGING_OCCURRENCE, REPEATED_PATTERN, ACTIONABLE_PATTERN)
- Category D: Issue Resolution (Explicit, Primary Fallback, Unmapped, KeyError Handling)
- Category E: Catalog and Recommendation Integration (Corrective Intent, Weights Reuse, Empty/Failure Handling)
- Category F: Hard Constraints (Normal Subset Semantics, Home/Gym, Exclusions, Multi-Constraints)
- Category G: Deterministic Ranking (Full-Precision Score DESC, Priority ASC, Compound Before Isolation, Exercise ID ASC, Post-Sort Rounding)
- Category H: Output Contract (Envelope, Item Fields, Limit Truncation, Disclaimer, JSON Serialization)
- Category I: Medical Safety Boundary (Prohibited Phrase Sanitization, Mandatory Disclaimer, Non-Medical Messaging)
- Category J: Side-Effect Boundaries (Zero Writes, Zero Plan/Workout Mutation, Zero LLM Calls)
- Category K: Failure and Edge Cases (Whitespace Stripping, Fallbacks, Unknown Catalog IDs)
- Category L: Determinism (Repeated Invocations, Order Invariance)
"""

import ast
import json
import os
import pytest
from datetime import datetime, timezone
from types import SimpleNamespace
from typing import Any, Dict, List, Optional
from unittest.mock import MagicMock

from backend.app.schemas.form_evidence import (
    EvidenceLevel,
    CalculationStatus,
    AggregatedIssueEvidence,
    ExerciseEvidenceSummary,
)
from backend.app.schemas.corrective_guidance import (
    CorrectiveGuidanceResponse,
    CorrectiveRecommendationItem,
    AUTHORITATIVE_CORRECTIVE_DISCLAIMER,
)
from backend.app.schemas.exercise import (
    RecommendationIntent,
    ExerciseRecommendationRequest,
    ExerciseRecommendationResponse,
    ExerciseRecommendationNode,
    ExerciseRelationshipNode,
    PROHIBITED_MEDICAL_PHRASES,
)
from backend.app.services.form_analysis.corrective_guidance_service import (
    CorrectiveGuidanceService,
    get_corrective_guidance_service,
)
from backend.app.repositories.form_analysis_repository import FormAnalysisRepository
from backend.app.services.exercise_relationship_service import ExerciseRelationshipService
from backend.app.services.exercise_recommendation_service import (
    ExerciseRecommendationService,
    CORRECTIVE_SCORING_WEIGHTS,
)
from backend.app.services.form_analysis.multi_session_evidence_aggregator import (
    MultiSessionEvidenceAggregator,
)


# =============================================================================
# FIXTURES & BUILDERS
# =============================================================================

@pytest.fixture
def repo() -> FormAnalysisRepository:
    repository = FormAnalysisRepository(db=None)
    repository.clear_in_memory_for_testing()
    return repository


@pytest.fixture
def service(repo: FormAnalysisRepository) -> CorrectiveGuidanceService:
    return CorrectiveGuidanceService(repository=repo)


def build_evidence_summary(
    exercise_id: str = "ex_squat",
    user_id: str = "test-user-guidance",
    level: EvidenceLevel = EvidenceLevel.ACTIONABLE_PATTERN,
    issue_id: Optional[str] = "insufficient_depth",
    recurrence_ratio: float = 1.0,
    mean_confidence: Optional[float] = 0.85,
) -> ExerciseEvidenceSummary:
    """Builds an ExerciseEvidenceSummary fixture for testing."""
    issues: Dict[str, AggregatedIssueEvidence] = {}
    if issue_id:
        issues[issue_id] = AggregatedIssueEvidence(
            issue_id=issue_id,
            source_heuristic="squat_depth",
            category="ROM",
            session_eligible_count=4,
            target_evaluated_sessions_count=4,
            qualifying_sessions_count=4 if level in (EvidenceLevel.ACTIONABLE_PATTERN, EvidenceLevel.REPEATED_PATTERN) else (1 if level == EvidenceLevel.EMERGING_OCCURRENCE else 0),
            recurrence_ratio=recurrence_ratio,
            qualifying_mean_confidence=mean_confidence,
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
        status_message="Evaluation completed.",
        calculation_status=CalculationStatus.SUCCESS,
        issues=issues,
    )


def build_mock_node(
    exercise_id: str,
    name: str = "Mock Exercise",
    score: float = 85.0,
    exercise_type: str = "isolation",
    reasons: Optional[List[str]] = None,
    difficulty: str = "beginner",
    movement_pattern: str = "squat",
) -> ExerciseRecommendationNode:
    """Builds an ExerciseRecommendationNode for controlled ranking and tie-breaking tests."""
    return ExerciseRecommendationNode(
        exercise_id=exercise_id,
        name=name,
        movement_pattern=movement_pattern,
        exercise_type=exercise_type,
        difficulty=difficulty,
        score=score,
        reasons=reasons or ["Focus on movement mechanics."],
    )


# =============================================================================
# CATEGORY A: SERVICE CONSTRUCTION AND INPUT VALIDATION
# =============================================================================

class TestCategoryAConstructionAndValidation:
    """Covers service initialization, DI, singleton, and parameter boundaries."""

    def test_service_initialization_with_defaults(self):
        svc = CorrectiveGuidanceService()
        assert svc._relationship_service is not None
        assert svc._recommendation_service is not None
        assert svc._multi_session_aggregator is not None
        assert svc._repository is not None

    def test_service_initialization_with_injected_dependencies(self, repo: FormAnalysisRepository):
        mock_rel = MagicMock(spec=ExerciseRelationshipService)
        mock_rec = MagicMock(spec=ExerciseRecommendationService)
        mock_agg = MagicMock(spec=MultiSessionEvidenceAggregator)

        svc = CorrectiveGuidanceService(
            relationship_service=mock_rel,
            recommendation_service=mock_rec,
            multi_session_aggregator=mock_agg,
            repository=repo,
        )
        assert svc._relationship_service is mock_rel
        assert svc._recommendation_service is mock_rec
        assert svc._multi_session_aggregator is mock_agg
        assert svc._repository is repo

    def test_service_singleton_getter(self):
        svc1 = get_corrective_guidance_service()
        svc2 = get_corrective_guidance_service()
        assert svc1 is svc2
        assert isinstance(svc1, CorrectiveGuidanceService)

    @pytest.mark.parametrize("invalid_ex_id", ["", "   ", "\t\n"])
    def test_input_validation_empty_or_whitespace_exercise_id(self, service: CorrectiveGuidanceService, invalid_ex_id: str):
        summary = build_evidence_summary()
        with pytest.raises(ValueError, match="exercise_id is required"):
            service.get_corrective_guidance(exercise_id=invalid_ex_id, user_id="user-1", evidence_summary=summary)

    @pytest.mark.parametrize("invalid_user_id", ["", "   ", "\t"])
    def test_input_validation_empty_or_whitespace_user_id(self, service: CorrectiveGuidanceService, invalid_user_id: str):
        summary = build_evidence_summary()
        with pytest.raises(ValueError, match="user_id is required"):
            service.get_corrective_guidance(exercise_id="ex_squat", user_id=invalid_user_id, evidence_summary=summary)

    @pytest.mark.parametrize("invalid_limit", [0, -1, -10])
    def test_input_validation_limit_below_minimum(self, service: CorrectiveGuidanceService, invalid_limit: int):
        summary = build_evidence_summary()
        with pytest.raises(ValueError, match="Limit must be between 1 and 10"):
            service.get_corrective_guidance(exercise_id="ex_squat", user_id="user-1", evidence_summary=summary, limit=invalid_limit)

    @pytest.mark.parametrize("invalid_limit", [11, 25, 100])
    def test_input_validation_limit_above_maximum(self, service: CorrectiveGuidanceService, invalid_limit: int):
        summary = build_evidence_summary()
        with pytest.raises(ValueError, match="Limit must be between 1 and 10"):
            service.get_corrective_guidance(exercise_id="ex_squat", user_id="user-1", evidence_summary=summary, limit=invalid_limit)

    @pytest.mark.parametrize("valid_limit", [1, 3, 5, 10])
    def test_input_validation_valid_limits_accepted(self, service: CorrectiveGuidanceService, valid_limit: int):
        summary = build_evidence_summary(level=EvidenceLevel.ACTIONABLE_PATTERN)
        res = service.get_corrective_guidance(exercise_id="ex_squat", user_id="user-1", evidence_summary=summary, limit=valid_limit)
        assert isinstance(res, CorrectiveGuidanceResponse)
        assert len(res.candidates) <= valid_limit


# =============================================================================
# CATEGORY B: EVIDENCE RESOLUTION (MODE A, MODE B, IMMUTABILITY)
# =============================================================================

class TestCategoryBEvidenceResolution:
    """Covers Mode A (supplied) and Mode B (repository query & aggregation) paths."""

    def test_mode_a_supplied_summary_consumed_without_repository_query(self, service: CorrectiveGuidanceService, monkeypatch: pytest.MonkeyPatch):
        summary = build_evidence_summary(level=EvidenceLevel.ACTIONABLE_PATTERN)
        repo_spy = MagicMock()
        monkeypatch.setattr(service._repository, "list_user_detailed_history", repo_spy)
        agg_spy = MagicMock()
        monkeypatch.setattr(service._multi_session_aggregator, "aggregate_exercise_evidence", agg_spy)

        res = service.get_corrective_guidance(exercise_id="ex_squat", user_id="user-1", evidence_summary=summary)

        # Mode A must NOT query repository or invoke aggregator
        repo_spy.assert_not_called()
        agg_spy.assert_not_called()
        assert res.evidence_level == EvidenceLevel.ACTIONABLE_PATTERN
        assert res.source_exercise_id == "ex_squat"

    def test_mode_b_queries_repository_and_invokes_aggregator(self, service: CorrectiveGuidanceService, monkeypatch: pytest.MonkeyPatch):
        summary_result = build_evidence_summary(level=EvidenceLevel.ACTIONABLE_PATTERN)
        repo_mock = MagicMock(return_value=["mock_session_1", "mock_session_2"])
        monkeypatch.setattr(service._repository, "list_user_detailed_history", repo_mock)
        agg_mock = MagicMock(return_value=summary_result)
        monkeypatch.setattr(service._multi_session_aggregator, "aggregate_exercise_evidence", agg_mock)

        res = service.get_corrective_guidance(exercise_id="ex_squat", user_id="user-1", evidence_summary=None)

        repo_mock.assert_called_once_with(uid="user-1", exercise_id="ex_squat")
        agg_mock.assert_called_once_with(sessions=["mock_session_1", "mock_session_2"], exercise_id="ex_squat", user_id="user-1")
        assert res.evidence_level == EvidenceLevel.ACTIONABLE_PATTERN

    def test_mode_b_empty_history_yields_insufficient_data(self, service: CorrectiveGuidanceService):
        # Empty repository with no historical sessions
        res = service.get_corrective_guidance(exercise_id="ex_squat", user_id="new-user-empty", evidence_summary=None)
        assert isinstance(res, CorrectiveGuidanceResponse)
        assert res.evidence_level in (EvidenceLevel.INSUFFICIENT_DATA, EvidenceLevel.NO_EVIDENCE)
        assert res.candidates == []
        assert res.is_eligible_for_proposal is False

    def test_mode_b_repository_failure_propagates_cleanly(self, service: CorrectiveGuidanceService, monkeypatch: pytest.MonkeyPatch):
        def _failing_repo(*args, **kwargs):
            raise RuntimeError("Database connection timed out")

        monkeypatch.setattr(service._repository, "list_user_detailed_history", _failing_repo)

        with pytest.raises(RuntimeError, match="Database connection timed out"):
            service.get_corrective_guidance(exercise_id="ex_squat", user_id="user-fail", evidence_summary=None)

    def test_mode_a_and_mode_b_equivalence(self, service: CorrectiveGuidanceService, monkeypatch: pytest.MonkeyPatch):
        summary = build_evidence_summary(level=EvidenceLevel.ACTIONABLE_PATTERN)
        res_a = service.get_corrective_guidance(exercise_id="ex_squat", user_id="user-eq", evidence_summary=summary)

        # Mock Mode B to return that same summary
        monkeypatch.setattr(service._repository, "list_user_detailed_history", lambda *a, **k: ["sess"])
        monkeypatch.setattr(service._multi_session_aggregator, "aggregate_exercise_evidence", lambda *a, **k: summary)
        res_b = service.get_corrective_guidance(exercise_id="ex_squat", user_id="user-eq", evidence_summary=None)

        assert res_a.model_dump() == res_b.model_dump()

    def test_evidence_summary_snapshot_immutability(self, service: CorrectiveGuidanceService):
        summary = build_evidence_summary(level=EvidenceLevel.ACTIONABLE_PATTERN)
        dump_before = json.dumps(summary.model_dump(), sort_keys=True)

        service.get_corrective_guidance(exercise_id="ex_squat", user_id="user-imm", evidence_summary=summary)

        dump_after = json.dumps(summary.model_dump(), sort_keys=True)
        assert dump_before == dump_after


# =============================================================================
# CATEGORY C: EVIDENCE-LEVEL QUALIFICATION GATES
# =============================================================================

class TestCategoryCEvidenceQualificationGates:
    """Covers strict candidate gating across all 5 EvidenceLevels."""

    def test_gate_no_evidence(self, service: CorrectiveGuidanceService):
        summary = build_evidence_summary(level=EvidenceLevel.NO_EVIDENCE)
        res = service.get_corrective_guidance(exercise_id="ex_squat", user_id="user-1", evidence_summary=summary)
        assert res.evidence_level == EvidenceLevel.NO_EVIDENCE
        assert res.candidates == []
        assert res.is_eligible_for_proposal is False
        assert "regular training" in res.status_message.lower()

    def test_gate_insufficient_data(self, service: CorrectiveGuidanceService):
        summary = build_evidence_summary(level=EvidenceLevel.INSUFFICIENT_DATA)
        res = service.get_corrective_guidance(exercise_id="ex_squat", user_id="user-1", evidence_summary=summary)
        assert res.evidence_level == EvidenceLevel.INSUFFICIENT_DATA
        assert res.candidates == []
        assert res.is_eligible_for_proposal is False
        assert "insufficient" in res.status_message.lower()

    def test_gate_emerging_occurrence(self, service: CorrectiveGuidanceService):
        summary = build_evidence_summary(level=EvidenceLevel.EMERGING_OCCURRENCE)
        res = service.get_corrective_guidance(exercise_id="ex_squat", user_id="user-1", evidence_summary=summary)
        assert res.evidence_level == EvidenceLevel.EMERGING_OCCURRENCE
        assert res.candidates == []
        assert res.is_eligible_for_proposal is False
        assert "isolated" in res.status_message.lower() or "focus on movement cues" in res.status_message.lower()

    def test_gate_repeated_pattern_candidates_returned_but_ineligible_for_proposal(self, service: CorrectiveGuidanceService):
        summary = build_evidence_summary(level=EvidenceLevel.REPEATED_PATTERN)
        res = service.get_corrective_guidance(exercise_id="ex_squat", user_id="user-1", evidence_summary=summary)
        assert res.evidence_level == EvidenceLevel.REPEATED_PATTERN
        assert len(res.candidates) > 0
        assert res.is_eligible_for_proposal is False
        for cand in res.candidates:
            assert cand.is_proposal_candidate is False
        assert "supplemental" in res.status_message.lower() or "technique practice" in res.status_message.lower()

    def test_gate_actionable_pattern_candidates_returned_and_eligible_for_proposal(self, service: CorrectiveGuidanceService):
        summary = build_evidence_summary(level=EvidenceLevel.ACTIONABLE_PATTERN)
        res = service.get_corrective_guidance(exercise_id="ex_squat", user_id="user-1", evidence_summary=summary)
        assert res.evidence_level == EvidenceLevel.ACTIONABLE_PATTERN
        assert len(res.candidates) > 0
        assert res.is_eligible_for_proposal is True
        for cand in res.candidates:
            assert cand.is_proposal_candidate is True
        assert "persistent" in res.status_message.lower() or "qualify for future-workout" in res.status_message.lower()

    def test_gate_actionable_pattern_with_zero_candidates_remains_proposal_ineligible(self, service: CorrectiveGuidanceService):
        # Exclude all candidate exercises
        summary = build_evidence_summary(level=EvidenceLevel.ACTIONABLE_PATTERN)
        res = service.get_corrective_guidance(
            exercise_id="ex_squat",
            user_id="user-1",
            evidence_summary=summary,
            user_excluded_exercises=["ex_box_squat", "ex_goblet_squat", "ex_90_90_hip_flow"],
        )
        assert res.evidence_level == EvidenceLevel.ACTIONABLE_PATTERN
        assert res.candidates == []
        # Invariant: Actionable pattern with 0 candidates must NOT become eligible for proposals
        assert res.is_eligible_for_proposal is False


# =============================================================================
# CATEGORY D: ISSUE RESOLUTION
# =============================================================================

class TestCategoryDIssueResolution:
    """Covers explicit issue ID, primary fallback, and unmapped/invalid issues."""

    def test_issue_resolution_explicit_matching_issue(self, service: CorrectiveGuidanceService):
        summary = build_evidence_summary(issue_id="insufficient_depth", level=EvidenceLevel.ACTIONABLE_PATTERN)
        res = service.get_corrective_guidance(
            exercise_id="ex_squat",
            user_id="user-1",
            issue_id="insufficient_depth",
            evidence_summary=summary,
        )
        assert res.target_issue_id == "insufficient_depth"
        assert len(res.candidates) > 0

    def test_issue_resolution_explicit_issue_unobserved_in_summary(self, service: CorrectiveGuidanceService):
        summary = build_evidence_summary(issue_id="insufficient_depth", level=EvidenceLevel.ACTIONABLE_PATTERN)
        # Query for an issue not in summary.issues -> fails closed to NO_EVIDENCE
        res = service.get_corrective_guidance(
            exercise_id="ex_squat",
            user_id="user-1",
            issue_id="valgus_collapse",
            evidence_summary=summary,
        )
        assert res.target_issue_id == "valgus_collapse"
        assert res.evidence_level == EvidenceLevel.NO_EVIDENCE
        assert res.candidates == []
        assert res.is_eligible_for_proposal is False

    def test_issue_resolution_fallback_to_primary_issue(self, service: CorrectiveGuidanceService):
        summary = build_evidence_summary(issue_id="insufficient_depth", level=EvidenceLevel.ACTIONABLE_PATTERN)
        res = service.get_corrective_guidance(
            exercise_id="ex_squat",
            user_id="user-1",
            issue_id=None,
            evidence_summary=summary,
        )
        assert res.target_issue_id == "insufficient_depth"

    def test_issue_resolution_missing_primary_issue_and_none_requested(self, service: CorrectiveGuidanceService):
        summary = build_evidence_summary(issue_id=None, level=EvidenceLevel.ACTIONABLE_PATTERN)
        summary.primary_issue_id = None
        res = service.get_corrective_guidance(
            exercise_id="ex_squat",
            user_id="user-1",
            issue_id=None,
            evidence_summary=summary,
        )
        assert res.target_issue_id is None
        assert res.candidates == []
        assert res.is_eligible_for_proposal is False
        assert "no specific target issue" in res.status_message.lower()

    def test_issue_resolution_unmapped_issue_in_catalog(self, service: CorrectiveGuidanceService):
        summary = build_evidence_summary(issue_id="unmapped_nonexistent_issue", level=EvidenceLevel.ACTIONABLE_PATTERN)
        res = service.get_corrective_guidance(
            exercise_id="ex_squat",
            user_id="user-1",
            issue_id="unmapped_nonexistent_issue",
            evidence_summary=summary,
        )
        assert res.candidates == []
        assert "no corrective drills mapped" in res.status_message.lower()
        assert res.is_eligible_for_proposal is False

    def test_issue_resolution_relationship_service_key_error_handled(self, service: CorrectiveGuidanceService, monkeypatch: pytest.MonkeyPatch):
        def _failing_lookup(exercise_id, issue_id):
            raise KeyError("Mapping not defined")

        monkeypatch.setattr(service._relationship_service, "get_corrective_exercises", _failing_lookup)

        summary = build_evidence_summary(level=EvidenceLevel.ACTIONABLE_PATTERN)
        res = service.get_corrective_guidance(exercise_id="ex_squat", user_id="user-1", evidence_summary=summary)
        assert res.candidates == []
        assert "no corrective drills mapped" in res.status_message.lower()


# =============================================================================
# CATEGORY E: CATALOG AND RECOMMENDATION INTEGRATION
# =============================================================================

class TestCategoryECatalogAndRecommendationIntegration:
    """Covers interaction with ExerciseRecommendationService and weights reuse."""

    def test_delegation_to_recommendation_service_with_corrective_intent(
        self, service: CorrectiveGuidanceService, monkeypatch: pytest.MonkeyPatch
    ):
        summary = build_evidence_summary(level=EvidenceLevel.ACTIONABLE_PATTERN)
        captured_requests = []

        real_recommend = service._recommendation_service.recommend

        def _spy_recommend(req: ExerciseRecommendationRequest):
            captured_requests.append(req)
            return real_recommend(req)

        monkeypatch.setattr(service._recommendation_service, "recommend", _spy_recommend)

        service.get_corrective_guidance(
            exercise_id="ex_squat",
            user_id="user-1",
            user_available_equipment=["dumbbells"],
            user_environment="home",
            limit=3,
            evidence_summary=summary,
        )

        assert len(captured_requests) == 1
        req = captured_requests[0]
        assert req.intent == RecommendationIntent.CORRECTIVE
        assert req.sourceExerciseId == "ex_squat"
        assert req.correctiveIssueId == "insufficient_depth"
        assert req.availableEquipment == ["dumbbells"]
        assert req.environment == "home"
        assert req.limit == 3

    def test_authoritative_corrective_weights_reused(self):
        # Invariant: weights match canonical specification
        assert CORRECTIVE_SCORING_WEIGHTS["corrective_match"] == pytest.approx(0.50)
        assert CORRECTIVE_SCORING_WEIGHTS["movement_pattern"] == pytest.approx(0.25)
        assert CORRECTIVE_SCORING_WEIGHTS["difficulty"] == pytest.approx(0.15)
        assert CORRECTIVE_SCORING_WEIGHTS["muscle"] == pytest.approx(0.10)

    def test_empty_recommendation_response_handled(
        self, service: CorrectiveGuidanceService, monkeypatch: pytest.MonkeyPatch
    ):
        summary = build_evidence_summary(level=EvidenceLevel.ACTIONABLE_PATTERN)
        empty_resp = ExerciseRecommendationResponse(candidates=[])
        monkeypatch.setattr(service._recommendation_service, "recommend", lambda req: empty_resp)

        res = service.get_corrective_guidance(exercise_id="ex_squat", user_id="user-1", evidence_summary=summary)
        assert res.candidates == []
        assert "no compatible corrective drills" in res.status_message.lower()

    def test_recommendation_service_error_propagates(
        self, service: CorrectiveGuidanceService, monkeypatch: pytest.MonkeyPatch
    ):
        summary = build_evidence_summary(level=EvidenceLevel.ACTIONABLE_PATTERN)

        def _crashing_recommend(req):
            raise ValueError("Corrupted catalog state")

        monkeypatch.setattr(service._recommendation_service, "recommend", _crashing_recommend)

        with pytest.raises(ValueError, match="Corrupted catalog state"):
            service.get_corrective_guidance(exercise_id="ex_squat", user_id="user-1", evidence_summary=summary)


# =============================================================================
# CATEGORY F: HARD CONSTRAINTS
# =============================================================================

class TestCategoryFHardConstraints:
    """Covers equipment subset semantics (required <= available), environment, and exclusions."""

    def test_equipment_exact_match_accepted(self, service: CorrectiveGuidanceService, monkeypatch: pytest.MonkeyPatch):
        """required == available qualifies (Check 1 exact-match subset semantics)."""
        summary = build_evidence_summary(level=EvidenceLevel.ACTIONABLE_PATTERN)
        # ex_box_squat requires box_platform; goblet_squat requires dumbbells
        res = service.get_corrective_guidance(
            exercise_id="ex_squat",
            user_id="user-1",
            user_available_equipment=["dumbbells"],
            evidence_summary=summary,
        )
        # ex_goblet_squat requires dumbbells only -> exact match accepted
        cand_ids = [c.exercise_id for c in res.candidates]
        assert "ex_goblet_squat" in cand_ids
        # ex_box_squat requires box_platform -> excluded
        assert "ex_box_squat" not in cand_ids

    def test_equipment_proper_subset_accepted(self, service: CorrectiveGuidanceService):
        """required < available qualifies."""
        summary = build_evidence_summary(level=EvidenceLevel.ACTIONABLE_PATTERN)
        res = service.get_corrective_guidance(
            exercise_id="ex_squat",
            user_id="user-1",
            user_available_equipment=["dumbbells", "barbell", "box_platform", "yoga_mat"],
            evidence_summary=summary,
        )
        assert len(res.candidates) > 0

    def test_equipment_missing_item_excluded(self, service: CorrectiveGuidanceService):
        summary = build_evidence_summary(level=EvidenceLevel.ACTIONABLE_PATTERN)
        # Provide only bodyweight; goblet squat requires dumbbells, box squat requires box
        res = service.get_corrective_guidance(
            exercise_id="ex_squat",
            user_id="user-1",
            user_available_equipment=["bodyweight"],
            evidence_summary=summary,
        )
        cand_ids = [c.exercise_id for c in res.candidates]
        assert "ex_goblet_squat" not in cand_ids
        assert "ex_box_squat" not in cand_ids

    def test_equipment_aliases_normalized(self, service: CorrectiveGuidanceService):
        summary = build_evidence_summary(level=EvidenceLevel.ACTIONABLE_PATTERN)
        # Pass "Dumbbell" (singular, capitalized) - must be normalized to "dumbbells"
        res = service.get_corrective_guidance(
            exercise_id="ex_squat",
            user_id="user-1",
            user_available_equipment=["Dumbbell"],
            evidence_summary=summary,
        )
        cand_ids = [c.exercise_id for c in res.candidates]
        assert "ex_goblet_squat" in cand_ids

    def test_environment_gym_vs_home_filtering(self, service: CorrectiveGuidanceService):
        summary = build_evidence_summary(level=EvidenceLevel.ACTIONABLE_PATTERN)
        res_home = service.get_corrective_guidance(
            exercise_id="ex_squat",
            user_id="user-1",
            user_environment="home",
            user_available_equipment=["dumbbells", "yoga_mat"],
            evidence_summary=summary,
        )
        for c in res_home.candidates:
            # Home compatible
            assert c.exercise_id != "ex_cable_pull_through"

    def test_user_excluded_exercises_removed(self, service: CorrectiveGuidanceService):
        summary = build_evidence_summary(level=EvidenceLevel.ACTIONABLE_PATTERN)
        res = service.get_corrective_guidance(
            exercise_id="ex_squat",
            user_id="user-1",
            user_excluded_exercises=["ex_goblet_squat"],
            evidence_summary=summary,
        )
        cand_ids = [c.exercise_id for c in res.candidates]
        assert "ex_goblet_squat" not in cand_ids

    def test_multiple_simultaneous_constraints(self, service: CorrectiveGuidanceService):
        summary = build_evidence_summary(level=EvidenceLevel.ACTIONABLE_PATTERN)
        res = service.get_corrective_guidance(
            exercise_id="ex_squat",
            user_id="user-1",
            user_available_equipment=["dumbbells", "box_platform"],
            user_environment="home",
            user_excluded_exercises=["ex_box_squat"],
            evidence_summary=summary,
        )
        cand_ids = [c.exercise_id for c in res.candidates]
        assert "ex_box_squat" not in cand_ids


# =============================================================================
# CATEGORY G: DETERMINISTIC RANKING & SCORE PRECISION
# =============================================================================

class TestCategoryGDeterministicRanking:
    """Covers full-precision score DESC, priority ASC, compound before isolation, and exercise_id ASC."""

    def test_ranking_full_precision_score_desc(
        self, service: CorrectiveGuidanceService, monkeypatch: pytest.MonkeyPatch
    ):
        """
        Critical Check 2 Assertion:
        84.514 > 84.506 -> candidate with 84.514 must rank FIRST,
        even though both round to 84.51 on display.
        """
        summary = build_evidence_summary(level=EvidenceLevel.ACTIONABLE_PATTERN)

        node_high = build_mock_node(exercise_id="ex_cand_z", score=84.514)
        node_low = build_mock_node(exercise_id="ex_cand_a", score=84.506)

        # Deliver low first to ensure sorting actually executes
        mock_resp = ExerciseRecommendationResponse(candidates=[node_low, node_high])
        monkeypatch.setattr(service._recommendation_service, "recommend", lambda req: mock_resp)

        res = service.get_corrective_guidance("ex_squat", "user-1", evidence_summary=summary)

        assert len(res.candidates) == 2
        assert res.candidates[0].exercise_id == "ex_cand_z"
        assert res.candidates[1].exercise_id == "ex_cand_a"
        # Both output scores rounded to 2 decimals
        assert res.candidates[0].score == 84.51
        assert res.candidates[1].score == 84.51

    def test_ranking_mapping_priority_tiebreaker(
        self, service: CorrectiveGuidanceService, monkeypatch: pytest.MonkeyPatch
    ):
        """When scores are identical, Priority 1 ranks ahead of Priority 2."""
        summary = build_evidence_summary(level=EvidenceLevel.ACTIONABLE_PATTERN)

        node_p2 = build_mock_node(exercise_id="ex_cand_p2", score=80.0)
        node_p1 = build_mock_node(exercise_id="ex_cand_p1", score=80.0)

        # Inject relationship nodes with different priorities
        rel_p1 = SimpleNamespace(exerciseId="ex_cand_p1", name="P1 Drill", priority=1, rationale="Drill rationale.")
        rel_p2 = SimpleNamespace(exerciseId="ex_cand_p2", name="P2 Drill", priority=2, rationale="Drill rationale.")
        monkeypatch.setattr(service._relationship_service, "get_corrective_exercises", lambda e, i: [rel_p2, rel_p1])

        mock_resp = ExerciseRecommendationResponse(candidates=[node_p2, node_p1])
        monkeypatch.setattr(service._recommendation_service, "recommend", lambda req: mock_resp)

        res = service.get_corrective_guidance("ex_squat", "user-1", evidence_summary=summary)

        assert len(res.candidates) == 2
        assert res.candidates[0].exercise_id == "ex_cand_p1"
        assert res.candidates[0].mapping_priority == 1
        assert res.candidates[1].exercise_id == "ex_cand_p2"
        assert res.candidates[1].mapping_priority == 2

    def test_ranking_compound_before_isolation_tiebreaker(
        self, service: CorrectiveGuidanceService, monkeypatch: pytest.MonkeyPatch
    ):
        """When score and priority are identical, compound ranks before isolation."""
        summary = build_evidence_summary(level=EvidenceLevel.ACTIONABLE_PATTERN)

        # ex_box_squat is compound in catalog; ex_cand_iso will default to isolation
        node_iso = build_mock_node(exercise_id="ex_cand_iso", score=80.0)
        node_cmp = build_mock_node(exercise_id="ex_box_squat", score=80.0)

        mock_resp = ExerciseRecommendationResponse(candidates=[node_iso, node_cmp])
        monkeypatch.setattr(service._recommendation_service, "recommend", lambda req: mock_resp)

        res = service.get_corrective_guidance("ex_squat", "user-1", evidence_summary=summary)

        assert len(res.candidates) == 2
        assert res.candidates[0].exercise_id == "ex_box_squat"
        assert res.candidates[1].exercise_id == "ex_cand_iso"

    def test_ranking_exercise_id_alphabetical_tiebreaker(
        self, service: CorrectiveGuidanceService, monkeypatch: pytest.MonkeyPatch
    ):
        """When score, priority, and type tie, alphabetical exercise_id ASC breaks tie."""
        summary = build_evidence_summary(level=EvidenceLevel.ACTIONABLE_PATTERN)

        node_b = build_mock_node(exercise_id="ex_cand_b", score=80.0)
        node_a = build_mock_node(exercise_id="ex_cand_a", score=80.0)

        mock_resp = ExerciseRecommendationResponse(candidates=[node_b, node_a])
        monkeypatch.setattr(service._recommendation_service, "recommend", lambda req: mock_resp)

        res = service.get_corrective_guidance("ex_squat", "user-1", evidence_summary=summary)

        assert len(res.candidates) == 2
        assert res.candidates[0].exercise_id == "ex_cand_a"
        assert res.candidates[1].exercise_id == "ex_cand_b"


# =============================================================================
# CATEGORY H: OUTPUT CONTRACT
# =============================================================================

class TestCategoryHOutputContract:
    """Covers schema validation, candidate fields, limits, and serialization."""

    def test_output_contract_fields_and_envelope(self, service: CorrectiveGuidanceService):
        summary = build_evidence_summary(level=EvidenceLevel.ACTIONABLE_PATTERN)
        res = service.get_corrective_guidance("ex_squat", "user-1", evidence_summary=summary)

        assert isinstance(res, CorrectiveGuidanceResponse)
        assert res.source_exercise_id == "ex_squat"
        assert res.target_issue_id == "insufficient_depth"
        assert res.evidence_level == EvidenceLevel.ACTIONABLE_PATTERN
        assert isinstance(res.status_message, str)
        assert res.is_eligible_for_proposal is True
        assert res.disclaimer == AUTHORITATIVE_CORRECTIVE_DISCLAIMER

        for item in res.candidates:
            assert isinstance(item, CorrectiveRecommendationItem)
            assert isinstance(item.exercise_id, str) and item.exercise_id
            assert isinstance(item.name, str) and item.name
            assert isinstance(item.difficulty, str)
            assert isinstance(item.equipment, list)
            assert isinstance(item.primary_muscles, list)
            assert isinstance(item.score, float)
            assert isinstance(item.reasons, list)
            assert isinstance(item.educational_cue, str)
            assert isinstance(item.mapping_priority, int)
            assert isinstance(item.is_proposal_candidate, bool)

    def test_output_contract_limit_truncation(self, service: CorrectiveGuidanceService):
        summary = build_evidence_summary(level=EvidenceLevel.ACTIONABLE_PATTERN)
        res = service.get_corrective_guidance("ex_squat", "user-1", limit=2, evidence_summary=summary)
        assert len(res.candidates) <= 2

    def test_output_contract_stable_json_serialization(self, service: CorrectiveGuidanceService):
        summary = build_evidence_summary(level=EvidenceLevel.ACTIONABLE_PATTERN)
        res = service.get_corrective_guidance("ex_squat", "user-1", evidence_summary=summary)

        json_str = res.model_dump_json()
        restored = CorrectiveGuidanceResponse.model_validate_json(json_str)
        assert restored.source_exercise_id == res.source_exercise_id
        assert len(restored.candidates) == len(res.candidates)


# =============================================================================
# CATEGORY I: MEDICAL SAFETY BOUNDARY
# =============================================================================

class TestCategoryIMedicalSafetyBoundary:
    """Covers sanitization of prohibited clinical phrases and mandatory disclaimers."""

    def test_safety_prohibited_phrases_in_rationale_sanitized(
        self, service: CorrectiveGuidanceService, monkeypatch: pytest.MonkeyPatch
    ):
        summary = build_evidence_summary(level=EvidenceLevel.ACTIONABLE_PATTERN)

        # Inject relationship node with prohibited clinical claim
        bad_rel = SimpleNamespace(
            exerciseId="ex_box_squat",
            name="Box Squat",
            priority=1,
            rationale="This drill will treat pain and cure pain.",
        )
        monkeypatch.setattr(service._relationship_service, "get_corrective_exercises", lambda e, i: [bad_rel])

        node = build_mock_node(exercise_id="ex_box_squat", name="Box Squat")
        mock_resp = ExerciseRecommendationResponse(candidates=[node])
        monkeypatch.setattr(service._recommendation_service, "recommend", lambda req: mock_resp)

        res = service.get_corrective_guidance("ex_squat", "user-1", evidence_summary=summary)

        assert len(res.candidates) == 1
        cue = res.candidates[0].educational_cue
        # Clinical words must be sanitized away to fallback
        assert "treat pain" not in cue.lower()
        assert "cure pain" not in cue.lower()
        assert "Focus on movement mechanics" in cue

    def test_safety_prohibited_phrases_in_reasons_sanitized(
        self, service: CorrectiveGuidanceService, monkeypatch: pytest.MonkeyPatch
    ):
        summary = build_evidence_summary(level=EvidenceLevel.ACTIONABLE_PATTERN)

        bad_cand = SimpleNamespace(
            exerciseId="ex_box_squat",
            name="Box Squat",
            difficulty="intermediate",
            equipment=[],
            primaryMuscles=[],
            score=85.0,
            reasons=["Recommended to treat pain and prevent injuries."],
        )
        mock_resp = SimpleNamespace(candidates=[bad_cand])
        monkeypatch.setattr(service._recommendation_service, "recommend", lambda req: mock_resp)

        res = service.get_corrective_guidance("ex_squat", "user-1", evidence_summary=summary)

        assert len(res.candidates) == 1
        for reason in res.candidates[0].reasons:
            assert "treat pain" not in reason.lower()
            assert "prevent injuries" not in reason.lower()
            assert reason == "Technique improvement drill."

    def test_safety_mandatory_disclaimer_always_present(self, service: CorrectiveGuidanceService):
        for lvl in EvidenceLevel:
            summ = build_evidence_summary(level=lvl)
            res = service.get_corrective_guidance("ex_squat", "user-1", evidence_summary=summ)
            assert res.disclaimer == AUTHORITATIVE_CORRECTIVE_DISCLAIMER

    def test_safety_status_messages_free_of_prohibited_medical_terms(self, service: CorrectiveGuidanceService):
        for lvl in EvidenceLevel:
            summ = build_evidence_summary(level=lvl)
            res = service.get_corrective_guidance("ex_squat", "user-1", evidence_summary=summ)
            lower_msg = res.status_message.lower()
            for phrase in PROHIBITED_MEDICAL_PHRASES:
                assert phrase not in lower_msg


# =============================================================================
# CATEGORY J: SIDE-EFFECT BOUNDARIES
# =============================================================================

class TestCategoryJSideEffectBoundaries:
    """Verifies read-only behavior: zero Firestore writes, zero mutations, zero LLM calls."""

    def test_side_effects_zero_firestore_writes(self, service: CorrectiveGuidanceService, monkeypatch: pytest.MonkeyPatch):
        summary = build_evidence_summary(level=EvidenceLevel.ACTIONABLE_PATTERN)

        write_spy = MagicMock()
        monkeypatch.setattr(service._repository, "_persist_session_detail_atomic", write_spy)
        summary_write_spy = MagicMock()
        monkeypatch.setattr(service._repository, "save_session_summary", summary_write_spy)

        service.get_corrective_guidance("ex_squat", "user-1", evidence_summary=summary)

        write_spy.assert_not_called()
        summary_write_spy.assert_not_called()

    def test_side_effects_zero_llm_imports_or_calls(self):
        target_file = os.path.join(
            "backend", "app", "services", "form_analysis", "corrective_guidance_service.py"
        )
        assert os.path.exists(target_file)
        with open(target_file, "r", encoding="utf-8") as f:
            code = f.read()

        prohibited = [
            "openai", "anthropic", "google.generativeai", "langchain", "litellm",
            "generate_content", "ChatCompletion"
        ]
        for p in prohibited:
            assert p not in code

    def test_side_effects_no_active_workout_or_plan_mutation(self, service: CorrectiveGuidanceService):
        mock_plan = {
            "plan_id": "plan-123",
            "exercises": [{"exercise_id": "ex_squat", "sets": 3, "reps": 10}],
        }
        plan_before = json.dumps(mock_plan, sort_keys=True)

        summary = build_evidence_summary(level=EvidenceLevel.ACTIONABLE_PATTERN)
        res = service.get_corrective_guidance("ex_squat", "user-1", evidence_summary=summary)

        # Plan in caller context must remain completely untouched
        plan_after = json.dumps(mock_plan, sort_keys=True)
        assert plan_before == plan_after
        # Service returns advisory candidates, never overwriting main exercise
        assert res.source_exercise_id == "ex_squat"


# =============================================================================
# CATEGORY K: FAILURE AND EDGE CASES
# =============================================================================

class TestCategoryKFailureAndEdgeCases:
    """Covers edge cases, whitespace handling, fallbacks, and unknown catalog IDs."""

    def test_edge_case_whitespace_ids_stripped(self, service: CorrectiveGuidanceService):
        summary = build_evidence_summary(level=EvidenceLevel.ACTIONABLE_PATTERN)
        res = service.get_corrective_guidance("  ex_squat  ", "  user-1  ", issue_id="  insufficient_depth  ", evidence_summary=summary)
        assert res.source_exercise_id == "ex_squat"
        assert res.target_issue_id == "insufficient_depth"

    def test_edge_case_none_cue_and_fallback_provided(
        self, service: CorrectiveGuidanceService, monkeypatch: pytest.MonkeyPatch
    ):
        summary = build_evidence_summary(level=EvidenceLevel.ACTIONABLE_PATTERN)

        node = build_mock_node(exercise_id="ex_box_squat", name="Box Squat")
        mock_resp = ExerciseRecommendationResponse(candidates=[node])
        monkeypatch.setattr(service._recommendation_service, "recommend", lambda req: mock_resp)

        # Relationship node has None educationalCue and None rationale
        rel = SimpleNamespace(exerciseId="ex_box_squat", name="Box Squat", priority=1, educationalCue=None, rationale=None)
        monkeypatch.setattr(service._relationship_service, "get_corrective_exercises", lambda e, i: [rel])

        res = service.get_corrective_guidance("ex_squat", "user-1", evidence_summary=summary)
        assert len(res.candidates) == 1
        assert "Practice movement control and proper mechanics" in res.candidates[0].educational_cue

    def test_edge_case_unknown_catalog_id_defaults_isolation(
        self, service: CorrectiveGuidanceService, monkeypatch: pytest.MonkeyPatch
    ):
        summary = build_evidence_summary(level=EvidenceLevel.ACTIONABLE_PATTERN)
        node = build_mock_node(exercise_id="ex_completely_unknown_xyz", name="Unknown Drill")
        mock_resp = ExerciseRecommendationResponse(candidates=[node])
        monkeypatch.setattr(service._recommendation_service, "recommend", lambda req: mock_resp)

        # Must not raise KeyError when looking up exercise type for unknown id
        res = service.get_corrective_guidance("ex_squat", "user-1", evidence_summary=summary)
        assert len(res.candidates) == 1
        assert res.candidates[0].exercise_id == "ex_completely_unknown_xyz"


# =============================================================================
# CATEGORY L: DETERMINISM
# =============================================================================

class TestCategoryLDeterminism:
    """Covers reproducibility, stable ordering, and candidate input invariance."""

    def test_determinism_repeated_invocations_produce_identical_outputs(self, service: CorrectiveGuidanceService):
        summary = build_evidence_summary(level=EvidenceLevel.ACTIONABLE_PATTERN)

        runs = [
            service.get_corrective_guidance("ex_squat", "user-1", evidence_summary=summary)
            for _ in range(10)
        ]

        first_dump = runs[0].model_dump_json()
        for idx, run in enumerate(runs[1:], start=2):
            assert run.model_dump_json() == first_dump, f"Run {idx} diverged from run 1"

    def test_determinism_candidate_input_order_invariance(
        self, service: CorrectiveGuidanceService, monkeypatch: pytest.MonkeyPatch
    ):
        """Service ranking is invariant to the order in which candidates were originally produced."""
        summary = build_evidence_summary(level=EvidenceLevel.ACTIONABLE_PATTERN)

        node_a = build_mock_node(exercise_id="ex_cand_a", score=90.0)
        node_b = build_mock_node(exercise_id="ex_cand_b", score=80.0)
        node_c = build_mock_node(exercise_id="ex_cand_c", score=70.0)

        # Order 1: [A, B, C]
        monkeypatch.setattr(
            service._recommendation_service,
            "recommend",
            lambda req: ExerciseRecommendationResponse(candidates=[node_a, node_b, node_c]),
        )
        res_order1 = service.get_corrective_guidance("ex_squat", "user-1", evidence_summary=summary)

        # Order 2: [C, A, B]
        monkeypatch.setattr(
            service._recommendation_service,
            "recommend",
            lambda req: ExerciseRecommendationResponse(candidates=[node_c, node_a, node_b]),
        )
        res_order2 = service.get_corrective_guidance("ex_squat", "user-1", evidence_summary=summary)

        # Both must produce identical ranking: [A, B, C]
        assert [c.exercise_id for c in res_order1.candidates] == ["ex_cand_a", "ex_cand_b", "ex_cand_c"]
        assert [c.exercise_id for c in res_order2.candidates] == ["ex_cand_a", "ex_cand_b", "ex_cand_c"]
        assert res_order1.model_dump_json() == res_order2.model_dump_json()
