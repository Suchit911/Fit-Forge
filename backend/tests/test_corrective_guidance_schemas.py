"""
Focused Unit Tests for Corrective Guidance Domain Schemas (Phase 9C.6.3 Step 1).

Verifies:
1. CorrectiveRecommendationItem can be constructed with valid data.
2. CorrectiveGuidanceResponse can be constructed with valid data.
3. EvidenceLevel is the canonical enum from form_evidence.py.
4. candidates defaults safely to an empty list.
5. default is_proposal_candidate is False.
6. default is_eligible_for_proposal is False.
7. disclaimer is present with authoritative text.
8. Required fields are strictly enforced.
9. No mutable-default leakage occurs between instances.
10. Strict boolean validation on is_proposal_candidate and is_eligible_for_proposal.
11. Strict non-boolean numeric validation on score.
12. Prevention of unauthorized extra fields (extra="forbid").
"""

import pytest
from pydantic import ValidationError

from backend.app.schemas.form_evidence import EvidenceLevel
from backend.app.schemas.corrective_guidance import (
    CorrectiveRecommendationItem,
    CorrectiveGuidanceResponse,
    AUTHORITATIVE_CORRECTIVE_DISCLAIMER,
)


# =============================================================================
# FIXTURES & VALID PAYLOAD FACTORIES
# =============================================================================

def make_valid_candidate_data(**overrides) -> dict:
    data = {
        "exercise_id": "ex_box_squat",
        "name": "Box Squat",
        "difficulty": "intermediate",
        "equipment": ["barbell", "box"],
        "primary_muscles": ["quadriceps", "glutes"],
        "score": 87.5,
        "reasons": ["Improves squat depth awareness and hip hinge control."],
        "educational_cue": "Pause briefly on the box without rocking back before ascending.",
        "mapping_priority": 1,
        "is_proposal_candidate": False,
    }
    data.update(overrides)
    return data


def make_valid_response_data(**overrides) -> dict:
    data = {
        "source_exercise_id": "ex_squat",
        "target_issue_id": "insufficient_depth",
        "evidence_level": EvidenceLevel.ACTIONABLE_PATTERN,
        "status_message": "Persistent technique deviation across lookback sessions qualifies for corrective intervention.",
        "is_eligible_for_proposal": True,
        "candidates": [CorrectiveRecommendationItem(**make_valid_candidate_data())],
    }
    data.update(overrides)
    return data


# =============================================================================
# TEST 1 & 2: VALID CONSTRUCTION
# =============================================================================

def test_corrective_recommendation_item_valid_construction():
    """1. CorrectiveRecommendationItem can be constructed with valid data."""
    data = make_valid_candidate_data()
    item = CorrectiveRecommendationItem(**data)

    assert item.exercise_id == "ex_box_squat"
    assert item.name == "Box Squat"
    assert item.difficulty == "intermediate"
    assert item.equipment == ["barbell", "box"]
    assert item.primary_muscles == ["quadriceps", "glutes"]
    assert item.score == 87.5
    assert item.reasons == ["Improves squat depth awareness and hip hinge control."]
    assert item.educational_cue == "Pause briefly on the box without rocking back before ascending."
    assert item.mapping_priority == 1
    assert item.is_proposal_candidate is False


def test_corrective_guidance_response_valid_construction():
    """2. CorrectiveGuidanceResponse can be constructed with valid data."""
    data = make_valid_response_data()
    resp = CorrectiveGuidanceResponse(**data)

    assert resp.source_exercise_id == "ex_squat"
    assert resp.target_issue_id == "insufficient_depth"
    assert resp.evidence_level == EvidenceLevel.ACTIONABLE_PATTERN
    assert "Persistent technique deviation" in resp.status_message
    assert resp.is_eligible_for_proposal is True
    assert len(resp.candidates) == 1
    assert resp.candidates[0].exercise_id == "ex_box_squat"


# =============================================================================
# TEST 3: CANONICAL EVIDENCE LEVEL ENUM
# =============================================================================

def test_evidence_level_canonical_enum():
    """3. EvidenceLevel is the canonical enum from form_evidence.py."""
    resp = CorrectiveGuidanceResponse(
        source_exercise_id="ex_squat",
        evidence_level=EvidenceLevel.REPEATED_PATTERN,
        status_message="Technique issue observed in 2 sessions.",
    )

    # Must be identical enum type and instance
    assert isinstance(resp.evidence_level, EvidenceLevel)
    assert resp.evidence_level is EvidenceLevel.REPEATED_PATTERN
    assert resp.evidence_level.value == "REPEATED_PATTERN"

    # All canonical enum values are supported
    for level in [
        EvidenceLevel.NO_EVIDENCE,
        EvidenceLevel.INSUFFICIENT_DATA,
        EvidenceLevel.EMERGING_OCCURRENCE,
        EvidenceLevel.REPEATED_PATTERN,
        EvidenceLevel.ACTIONABLE_PATTERN,
    ]:
        r = CorrectiveGuidanceResponse(
            source_exercise_id="ex_squat",
            evidence_level=level,
            status_message="Test message",
        )
        assert r.evidence_level is level

    # Invalid enum string is rejected
    with pytest.raises(ValidationError):
        CorrectiveGuidanceResponse(
            source_exercise_id="ex_squat",
            evidence_level="INVALID_EVIDENCE_LEVEL",  # type: ignore
            status_message="Test",
        )


# =============================================================================
# TEST 4, 5, 6, 7: DEFAULTS & AUTHORITATIVE DISCLAIMER
# =============================================================================

def test_defaults_and_authoritative_disclaimer():
    """
    4. candidates defaults safely to an empty list.
    5. default is_proposal_candidate is False.
    6. default is_eligible_for_proposal is False.
    7. disclaimer is present with authoritative text.
    """
    # Item defaults: mapping_priority=1, is_proposal_candidate=False
    data = make_valid_candidate_data()
    del data["mapping_priority"]
    del data["is_proposal_candidate"]
    item = CorrectiveRecommendationItem(**data)
    assert item.mapping_priority == 1
    assert item.is_proposal_candidate is False

    # Response defaults: target_issue_id=None, is_eligible_for_proposal=False,
    # candidates=[], disclaimer=AUTHORITATIVE_CORRECTIVE_DISCLAIMER
    resp = CorrectiveGuidanceResponse(
        source_exercise_id="ex_squat",
        evidence_level=EvidenceLevel.NO_EVIDENCE,
        status_message="No qualifying technique issue was identified from available evidence.",
    )
    assert resp.target_issue_id is None
    assert resp.is_eligible_for_proposal is False
    assert resp.candidates == []
    assert resp.disclaimer == (
        "These exercise suggestions are general movement drills to assist with technique practice. "
        "They are not medical treatments or rehabilitation prescriptions."
    )
    assert resp.disclaimer == AUTHORITATIVE_CORRECTIVE_DISCLAIMER


# =============================================================================
# TEST 8: REQUIRED FIELDS ENFORCEMENT
# =============================================================================

@pytest.mark.parametrize(
    "missing_field",
    [
        "exercise_id",
        "name",
        "difficulty",
        "equipment",
        "primary_muscles",
        "score",
        "reasons",
        "educational_cue",
    ],
)
def test_item_required_fields_enforced(missing_field: str):
    """8. Required fields for CorrectiveRecommendationItem are strictly enforced."""
    data = make_valid_candidate_data()
    del data[missing_field]
    with pytest.raises(ValidationError) as exc_info:
        CorrectiveRecommendationItem(**data)
    assert missing_field in str(exc_info.value)


@pytest.mark.parametrize(
    "missing_field",
    [
        "source_exercise_id",
        "evidence_level",
        "status_message",
    ],
)
def test_response_required_fields_enforced(missing_field: str):
    """8. Required fields for CorrectiveGuidanceResponse are strictly enforced."""
    data = make_valid_response_data()
    del data[missing_field]
    with pytest.raises(ValidationError) as exc_info:
        CorrectiveGuidanceResponse(**data)
    assert missing_field in str(exc_info.value)


# =============================================================================
# TEST 9: NO MUTABLE DEFAULT LEAKAGE
# =============================================================================

def test_no_mutable_default_leakage():
    """9. No mutable-default leakage occurs between separate schema instances."""
    resp1 = CorrectiveGuidanceResponse(
        source_exercise_id="ex_squat",
        evidence_level=EvidenceLevel.NO_EVIDENCE,
        status_message="Message 1",
    )
    resp2 = CorrectiveGuidanceResponse(
        source_exercise_id="ex_deadlift",
        evidence_level=EvidenceLevel.NO_EVIDENCE,
        status_message="Message 2",
    )

    assert resp1.candidates is not resp2.candidates
    assert resp1.candidates == []
    assert resp2.candidates == []

    # Mutating resp1.candidates must not affect resp2
    item = CorrectiveRecommendationItem(**make_valid_candidate_data())
    resp1.candidates.append(item)
    assert len(resp1.candidates) == 1
    assert len(resp2.candidates) == 0


# =============================================================================
# TEST 10 & 11: STRICT VALIDATION (BOOLEANS & SCORE)
# =============================================================================

@pytest.mark.parametrize("invalid_bool", [1, 0, "True", "False", 1.0, 0.0, None])
def test_item_is_proposal_candidate_strict_boolean(invalid_bool):
    """10. is_proposal_candidate must strictly be bool (rejecting ints, strings, None)."""
    data = make_valid_candidate_data(is_proposal_candidate=invalid_bool)
    with pytest.raises(ValidationError) as exc_info:
        CorrectiveRecommendationItem(**data)
    assert "is_proposal_candidate" in str(exc_info.value)


@pytest.mark.parametrize("invalid_bool", [1, 0, "True", "False", 1.0, 0.0, None])
def test_response_is_eligible_for_proposal_strict_boolean(invalid_bool):
    """10. is_eligible_for_proposal must strictly be bool (rejecting ints, strings, None)."""
    data = make_valid_response_data(is_eligible_for_proposal=invalid_bool)
    with pytest.raises(ValidationError) as exc_info:
        CorrectiveGuidanceResponse(**data)
    assert "is_eligible_for_proposal" in str(exc_info.value)


@pytest.mark.parametrize("invalid_score", [True, False])
def test_item_score_rejects_boolean(invalid_score):
    """11. score must strictly be a numeric float, rejecting booleans."""
    data = make_valid_candidate_data(score=invalid_score)
    with pytest.raises(ValidationError) as exc_info:
        CorrectiveRecommendationItem(**data)
    assert "score" in str(exc_info.value)


# =============================================================================
# TEST 12: EXTRA FIELDS FORBIDDEN
# =============================================================================

def test_extra_fields_forbidden():
    """12. Extra unauthorized fields are strictly rejected (model_config extra='forbid')."""
    data_item = make_valid_candidate_data(unauthorized_field="malicious_payload")
    with pytest.raises(ValidationError) as exc_item:
        CorrectiveRecommendationItem(**data_item)
    assert "extra_forbidden" in str(exc_item.value) or "Extra inputs are not permitted" in str(exc_item.value)

    data_resp = make_valid_response_data(unauthorized_field="malicious_payload")
    with pytest.raises(ValidationError) as exc_resp:
        CorrectiveGuidanceResponse(**data_resp)
    assert "extra_forbidden" in str(exc_resp.value) or "Extra inputs are not permitted" in str(exc_resp.value)
