"""
Authoritative Domain Schemas for Corrective Guidance Service (Phase 9C.6.3 Step 1).

Defines:
- CorrectiveRecommendationItem: Individual ranked corrective drill candidate.
- CorrectiveGuidanceResponse: Composite response payload with evidence qualification,
  status messaging, advisory proposal eligibility, and non-medical disclaimer.
"""

from typing import List, Optional, Any
from pydantic import BaseModel, Field, field_validator

from backend.app.schemas.form_evidence import EvidenceLevel

AUTHORITATIVE_CORRECTIVE_DISCLAIMER: str = (
    "These exercise suggestions are general movement drills to assist with technique practice. "
    "They are not medical treatments or rehabilitation prescriptions."
)


class CorrectiveRecommendationItem(BaseModel):
    """
    Individual catalog-backed corrective exercise candidate addressing an observed technique issue.
    """
    exercise_id: str
    name: str
    difficulty: str
    equipment: List[str]
    primary_muscles: List[str]
    score: float
    reasons: List[str]
    educational_cue: str
    mapping_priority: int = 1
    is_proposal_candidate: bool = False

    model_config = {"extra": "forbid"}

    @field_validator("score", mode="before")
    @classmethod
    def validate_score_not_bool(cls, v: Any) -> float:
        if isinstance(v, bool):
            raise ValueError("score must be a numeric float, not a boolean.")
        return v

    @field_validator("is_proposal_candidate", mode="before")
    @classmethod
    def validate_strict_proposal_candidate(cls, v: Any) -> bool:
        if v is not None and type(v) is not bool:
            raise ValueError(
                "is_proposal_candidate must be a strict boolean (True or False), not an integer or string."
            )
        return v


class CorrectiveGuidanceResponse(BaseModel):
    """
    Structured response payload for corrective guidance evaluation.
    """
    source_exercise_id: str
    target_issue_id: Optional[str] = None
    evidence_level: EvidenceLevel
    status_message: str
    is_eligible_for_proposal: bool = False
    candidates: List[CorrectiveRecommendationItem] = Field(default_factory=list)
    disclaimer: str = AUTHORITATIVE_CORRECTIVE_DISCLAIMER

    model_config = {"extra": "forbid"}

    @field_validator("is_eligible_for_proposal", mode="before")
    @classmethod
    def validate_strict_eligible_proposal(cls, v: Any) -> bool:
        if v is not None and type(v) is not bool:
            raise ValueError(
                "is_eligible_for_proposal must be a strict boolean (True or False), not an integer or string."
            )
        return v
