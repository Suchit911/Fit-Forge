"""
Deterministic Progression & Adaptation Engine Schemas (Phase 9C.2).

Defines strongly-typed, deterministic domain models for evaluated workout adaptations:
- Load progression candidates (Double-progression rule: 3 qualifying consecutive sessions, 21-day reset, 5% ceiling)
- Volume reduction candidates (Volume fatigue: 2 consecutive sessions < 70% completed sets, 1–5 set bounds)
- Rep progression candidates (Isolation and bodyweight exercises)
- Exercise regression and substitution proposals
- Recurring form issue proposals (CV signals without Slot 0 injection)
- Future-block split adaptation recommendations (Mesocycle level)

Strict Invariants:
1. Decision Layer ONLY: Produces bounded proposals; does NOT mutate Firestore active programs.
2. Grounded Data: Derived strictly from Phase 9C.1 performance signals and authoritative sessions.
3. Deterministic Decision IDs: SHA-256 hashes generated from canonical decision inputs.
4. Full Reversibility: Exposes prior and proposed prescription states.
5. Non-Medical Language: Enforces objective biomechanical and performance terminology.
"""

from typing import List, Optional, Literal, Dict, Any, Union
from pydantic import BaseModel, Field, model_validator
import hashlib
import json

from .personalization import EvidenceLevel
from .user import EquipmentType, Environment, FitnessGoal, DifficultyLevel
from .exercise import MovementPattern, ExerciseType, EnvironmentType


# =============================================================================
# Controlled Taxonomies & States
# =============================================================================

AdaptationType = Literal[
    "load_progression",          # Bounded increase in working resistance (kg)
    "rep_progression",           # Bounded increase in target rep range (+1 rep)
    "volume_reduction",          # Bounded reduction in prescribed sets (-1 set)
    "exercise_regression",       # Proposes mechanically simpler catalog regression
    "exercise_substitution",     # Proposes equivalent equipment/exercise substitution
    "split_adjustment",          # Future-block mesocycle training frequency adjustment
    "recurring_form_issue",      # Structured notice of persistent form flaw
    "no_change",                 # Current prescription remains optimal
]

DecisionStatus = Literal[
    "insufficient_data",                  # < qualifying consecutive observations
    "no_change",                          # Evidence indicates stable prescription
    "progression_candidate",              # Double-progression criteria met and approved
    "volume_reduction_candidate",         # Volume fatigue criteria met
    "regression_candidate",               # Regression relationship recommended
    "substitution_candidate",             # Substitution relationship recommended
    "future_split_adjustment_candidate",  # Mesocycle adherence mismatch detected
    "form_issue_candidate",               # Recurring CV issue detected
    "constrained_no_change",              # Adaptation justified but blocked by safety bound
]


# =============================================================================
# Prescription Delta & Reversibility Model
# =============================================================================

class PrescriptionDelta(BaseModel):
    """
    Encapsulates specific exercise prescription parameters for reversibility.
    Allows exact reconstruction of prior state and comparison against proposed state.
    """
    exerciseId: Optional[str] = None
    exerciseName: Optional[str] = None
    weightKg: Optional[float] = None
    setCount: Optional[int] = Field(default=None, ge=1, le=5)
    targetRepsMin: Optional[int] = Field(default=None, ge=1)
    targetRepsMax: Optional[int] = Field(default=None, ge=1)
    targetRpe: Optional[float] = Field(default=None, ge=1.0, le=10.0)
    restSeconds: Optional[int] = Field(default=None, ge=0)

    model_config = {"extra": "ignore"}

    @model_validator(mode="after")
    def validate_rep_range(self) -> "PrescriptionDelta":
        if self.targetRepsMin is not None and self.targetRepsMax is not None:
            if self.targetRepsMin > self.targetRepsMax:
                raise ValueError(
                    f"targetRepsMin ({self.targetRepsMin}) cannot exceed targetRepsMax ({self.targetRepsMax})."
                )
        return self


# =============================================================================
# Core Adaptation Decision Model
# =============================================================================

class AdaptationDecision(BaseModel):
    """
    Deterministic adaptation decision proposal for a single exercise or context.
    Contains exhaustive audit information explaining why the decision was made,
    the evidence evaluated, constraints applied, and prior state reversibility.
    """
    decisionId: str = Field(..., description="Deterministic SHA-256 hash of decision content")
    exerciseId: Optional[str] = Field(default=None, description="Target exercise ID if exercise-specific")
    canonicalName: Optional[str] = Field(default=None, description="Human-readable exercise name")
    adaptationType: AdaptationType
    status: DecisionStatus
    ruleCode: str = Field(..., description="Machine-readable rule identifier triggering decision")
    evidenceLevel: EvidenceLevel = "insufficient_data"
    evidence: Dict[str, Any] = Field(default_factory=dict, description="Quantitative evidence evaluated")
    previousPrescription: Optional[PrescriptionDelta] = None
    proposedPrescription: Optional[PrescriptionDelta] = None
    deltaMagnitude: Optional[float] = Field(default=None, description="Magnitude of delta (e.g. +2.5 kg, -1 set, +1 rep)")
    deltaUnit: Optional[str] = Field(default=None, description="Unit of change: 'kg', 'sets', 'reps'")
    rationale: str = Field(..., description="Concise, non-medical explanation of the decision")
    reasons: List[str] = Field(default_factory=list, description="Structured bullet points of justification")
    constraintsApplied: List[str] = Field(default_factory=list, description="Safety boundaries and limits applied")
    isReversible: bool = Field(default=True, description="Whether previous state can be fully restored")
    sourceSessionIds: List[str] = Field(default_factory=list, description="Authoritative session IDs evaluated")
    generatedAt: str = Field(..., description="ISO 8601 UTC timestamp")

    model_config = {"extra": "ignore"}


# =============================================================================
# Future Split Recommendation Model (Mesocycle Level)
# =============================================================================

class FutureSplitRecommendation(BaseModel):
    """
    Structured future-block recommendation proposing a training split adjustment
    for the next mesocycle when adherence consistently deviates from planned frequency.
    Does NOT mutate current active week or active program.
    """
    currentSplit: Optional[str] = None
    recommendedSplit: str = Field(..., description="Recommended workout split (e.g. 'full_body')")
    recommendedDaysPerWeek: int = Field(..., ge=1, le=7)
    observedWeeklyFrequency: float = Field(..., ge=0.0)
    plannedWeeklyFrequency: Optional[float] = None
    adherenceRate: Optional[float] = None
    ruleCode: str = "ADHERENCE_SPLIT_MISMATCH_4_WEEKS"
    reason: str
    isFutureBlockOnly: bool = True

    model_config = {"extra": "ignore"}


# =============================================================================
# API Request & Response Schemas
# =============================================================================

class AdaptationEvaluationRequest(BaseModel):
    """
    Payload for evaluating adaptation decisions against a specific planned workout context.
    Optional fields allow evaluating general opportunities if no context is provided.
    """
    candidateExercises: Optional[List[PrescriptionDelta]] = Field(
        default=None,
        description="Prescribed exercises to evaluate for adaptation against user history",
    )
    targetDurationMinutes: Optional[int] = Field(default=45, ge=10, le=180)
    availableEquipment: Optional[List[EquipmentType]] = None
    environment: Optional[Environment] = "gym"
    fitnessGoal: Optional[FitnessGoal] = "general_fitness"
    windowDays: int = Field(default=28, ge=7, le=90)

    model_config = {"extra": "ignore"}


class AdaptationEvaluationResponse(BaseModel):
    """
    Structured response payload for adaptation evaluation.
    Read-only: reflects computed decisions without persisting to Firestore.
    """
    userId: str
    generatedAt: str
    evaluationWindowDays: int
    primaryDecisions: List[AdaptationDecision] = Field(default_factory=list)
    futureSplitProposal: Optional[FutureSplitRecommendation] = None
    summaryMetrics: Dict[str, Any] = Field(default_factory=dict)

    model_config = {"extra": "ignore"}


# =============================================================================
# Deterministic Hash Helper
# =============================================================================

def generate_decision_id(
    user_id: str,
    scope_id: str,
    rule_code: str,
    adaptation_type: str,
    status: str,
    delta_magnitude: Optional[float] = None,
) -> str:
    """
    Generates a reproducible 16-character SHA-256 hash identifying a decision.
    Guarantees byte-equivalent outputs for identical input parameters.
    """
    raw_str = f"{user_id}|{scope_id}|{rule_code}|{adaptation_type}|{status}|{delta_magnitude or 0.0}"
    return hashlib.sha256(raw_str.encode("utf-8")).hexdigest()[:16]
