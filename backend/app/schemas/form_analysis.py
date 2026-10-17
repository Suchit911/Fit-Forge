from enum import Enum
from typing import List, Literal, Optional, Dict, Union, Any
from pydantic import BaseModel


class KeyMetricItemSchema(BaseModel):
    name: str
    score: float
    status: Literal["Excellent", "Good", "Fair", "Poor"]
    trendData: List[float] = []


class FormBreakdownItemSchema(BaseModel):
    metric: str
    score: float


class MuscleActivationItemSchema(BaseModel):
    name: str
    activationPct: float
    category: Literal["primary", "secondary", "stabilizer"]


class RepAnalysisItemSchema(BaseModel):
    repNumber: int
    elbowAngle: float
    status: Literal["good", "improvement", "poor", "skipped"]


class AnalysisHistoryItemSchema(BaseModel):
    id: str
    date: str
    time: str
    exerciseName: str
    weightKg: float
    score: float


class FormAnalysisSessionSchema(BaseModel):
    exerciseId: str
    exerciseName: str
    setInfo: str
    weightKg: float
    reps: int
    rpe: float
    restTime: str
    formScore: float
    formStatus: str
    analysisTime: str
    confidence: str
    videoAssetUrl: str
    keyMetrics: List[KeyMetricItemSchema] = []
    scoreBreakdown: List[FormBreakdownItemSchema] = []
    muscleActivation: List[MuscleActivationItemSchema] = []
    positiveFeedback: List[str] = []
    improvementFeedback: List[str] = []
    infoFeedback: List[str] = []
    coachingTips: List[str] = []
    repProgress: List[RepAnalysisItemSchema] = []
    history: List[AnalysisHistoryItemSchema] = []


# =============================================================================
# PHASE 9A — COMPUTER VISION & POSE ESTIMATION FOUNDATION SCHEMAS
# =============================================================================

from typing import Optional, Dict


class NormalizedLandmarkSchema(BaseModel):
    index: int
    name: str
    x: float
    y: float
    z: float = 0.0
    visibility: float = 1.0
    presence: Optional[float] = None


class BoundingBoxSchema(BaseModel):
    x_min: float
    y_min: float
    width: float
    height: float


class EstimatedBodyCenterSchema(BaseModel):
    """
    Estimated geometric centroid approximation of detected trunk/pelvis keypoints.
    NOTE: This is an estimated landmark centroid/body-center approximation,
    NOT an authoritative biomechanical center of mass.
    """
    x: float
    y: float
    z: float = 0.0
    description: str = "Estimated landmark centroid approximation (not biomechanical center of mass)"


class JointAngleResultSchema(BaseModel):
    joint_name: str
    angle_degrees: float
    confidence: float
    vertex_landmark: str
    connected_landmarks: List[str]
    is_occluded: bool = False


class PoseExtractionResponse(BaseModel):
    landmarks_detected: bool
    landmark_count: int
    landmarks: Dict[str, NormalizedLandmarkSchema] = {}
    bounding_box: Optional[BoundingBoxSchema] = None
    estimated_body_center: Optional[EstimatedBodyCenterSchema] = None
    overall_confidence: float = 0.0
    processing_time_ms: float = 0.0


class JointAnglesRequest(BaseModel):
    landmarks: Optional[Dict[str, NormalizedLandmarkSchema]] = None
    image_base64: Optional[str] = None
    target_joints: Optional[List[str]] = None


class JointAnglesResponse(BaseModel):
    landmarks_detected: bool
    joint_angles: Dict[str, JointAngleResultSchema] = {}
    overall_confidence: float = 0.0
    processing_time_ms: float = 0.0


class CVEngineHealthSchema(BaseModel):
    status: str
    engine: str
    supported_landmarks: int = 33
    confidence_threshold: float = 0.5


# =============================================================================
# PHASE 9B.2 — FORM HEURISTICS SCHEMAS
# =============================================================================

class ObservabilityStatus(str, Enum):
    OBSERVED = "OBSERVED"
    INSUFFICIENT_CONFIDENCE = "INSUFFICIENT_CONFIDENCE"
    NOT_OBSERVABLE = "NOT_OBSERVABLE"
    INVALID = "INVALID"


class HeuristicCategory(str, Enum):
    ROM = "ROM"
    TECHNIQUE = "Joint Alignment / Technique"
    SYMMETRY = "Symmetry"
    STABILITY = "Stability"


class FormHeuristicResultSchema(BaseModel):
    exercise_id: str
    category: str
    heuristic_name: str
    status: str
    is_acceptable: Optional[bool] = None
    observed_value: Optional[float] = None
    reference_value: Optional[Union[float, List[float]]] = None
    deviation: Optional[float] = None
    confidence: float = 0.0
    feedback: str
    unit: str = "degrees"
    timestamp_ms: Optional[float] = None


class ExerciseFormReportSchema(BaseModel):
    exercise_id: str
    timestamp_ms: float
    results: List[FormHeuristicResultSchema] = []
    observable_count: int = 0
    total_required_count: int = 0
    observability_ratio: float = 0.0
    is_sufficiently_observable: bool = False


# =============================================================================
# PHASE 9B.3: DETERMINISTIC FORM SCORING SCHEMAS
# =============================================================================

class RepScoreStatus(str, Enum):
    VALID = "VALID"
    INCOMPLETE = "INCOMPLETE"
    INVALID = "INVALID"
    INSUFFICIENT_DATA = "INSUFFICIENT_DATA"


class CategoryScoreSchema(BaseModel):
    category: str
    weight: float
    normalized_weight: float
    raw_penalty: float
    category_score: Optional[float] = None
    is_observable: bool = True
    observable_count: int = 0
    total_count: int = 0
    feedback_items: List[str] = []


class RepetitionScoreSchema(BaseModel):
    exercise_id: str
    rep_number: Optional[int] = None
    status: str
    score: Optional[float] = None
    base_score: Optional[float] = None
    confidence_factor: float = 1.0
    rep_confidence: float = 0.0
    observability_ratio: float = 0.0
    is_sufficiently_observable: bool = False
    category_scores: Dict[str, CategoryScoreSchema] = {}
    contributing_defects: List[str] = []
    feedback: List[str] = []
    timestamp_ms: Optional[float] = None


class SetScoreSummarySchema(BaseModel):
    exercise_id: str
    status: str
    overall_score: Optional[float] = None
    total_reps: int = 0
    valid_reps: int = 0
    insufficient_data_reps: int = 0
    incomplete_reps: int = 0
    invalid_reps: int = 0
    rep_scores: List[RepetitionScoreSchema] = []
    summary_feedback: List[str] = []


# =============================================================================
# PHASE 9B.5: WEBSOCKET STREAMING SCHEMAS
# =============================================================================

class WSClientMessageType(str, Enum):
    PAUSE = "pause"
    RESUME = "resume"
    STOP = "stop"
    PING = "ping"


class WSServerMessageType(str, Enum):
    ACK = "ack"
    ANALYSIS = "analysis"
    REP_COMPLETED = "rep_completed"
    ERROR = "error"
    PONG = "pong"
    STOPPED = "stopped"


class WSAckMessage(BaseModel):
    type: str = "ack"
    sequence_id: Optional[int] = None
    status: str = "ok"
    session_id: Optional[str] = None
    server_time_ms: float = 0.0
    processing_ms: Optional[float] = None


class WSAnalysisMessage(BaseModel):
    type: str = "analysis"
    sequence_id: int
    session_id: str
    exercise_id: str
    timestamp_ms: float
    latency_e2e_ms: Optional[float] = None
    processing_ms: float = 0.0
    tracking_status: str
    fsm_state: str
    rep_count: int
    primary_angle: Optional[float] = None
    observability_ratio: float = 0.0
    is_sufficiently_observable: bool = False
    landmarks_detected: bool = False
    landmarks: List[Dict[str, Any]] = []
    joint_angles: Dict[str, float] = {}
    heuristics: List[Dict[str, Any]] = []
    latest_score: Optional[float] = None
    score_status: Optional[str] = None
    feedback: List[str] = []


class WSRepCompletedMessage(BaseModel):
    type: str = "rep_completed"
    sequence_id: int
    session_id: str
    exercise_id: str
    rep_number: int
    fsm_outcome: str
    rom_degrees: Optional[float] = None
    duration_ms: Optional[float] = None
    score: Optional[float] = None
    score_status: Optional[str] = None
    category_scores: Dict[str, Any] = {}
    feedback: List[str] = []


class WSErrorMessage(BaseModel):
    type: str = "error"
    sequence_id: Optional[int] = None
    error: str
    detail: Optional[str] = None
    code: str = "ERROR"


class WSPongMessage(BaseModel):
    type: str = "pong"
    sequence_id: Optional[int] = None
    client_timestamp_ms: Optional[float] = None
    server_timestamp_ms: float = 0.0


class WSStoppedMessage(BaseModel):
    type: str = "stopped"
    session_id: str
    rep_count: int = 0
    overall_score: Optional[float] = None
    summary: Optional[Dict[str, Any]] = None


# =============================================================================
# PHASE 9B.7: SESSION SUMMARY & HISTORY SCHEMAS
# =============================================================================

class CompactRepSummarySchema(BaseModel):
    """Compact bounded summary of an individual repetition for history persistence."""
    rep_number: int
    status: str
    score: Optional[float] = None
    rom_degrees: Optional[float] = None
    duration_ms: Optional[float] = None
    category_scores: Dict[str, Optional[float]] = {}
    feedback: List[str] = []


class FormAnalysisSessionSummarySchema(BaseModel):
    """Lightweight history list item for form analysis sessions."""
    session_id: str
    exercise_id: str
    exercise_name: str
    status: str = "completed"
    started_at: str
    completed_at: str
    duration_seconds: int = 0
    total_reps: int = 0
    completed_reps: int = 0
    valid_reps: int = 0
    overall_score: Optional[float] = None


class FormAnalysisSessionDetailSchema(BaseModel):
    """Full persisted summary of a finalized form analysis session."""
    session_id: str
    user_id: str
    exercise_id: str
    canonical_exercise_id: str
    exercise_name: str
    status: str = "completed"
    started_at: str
    completed_at: str
    duration_seconds: int = 0
    total_reps: int = 0
    completed_reps: int = 0
    valid_reps: int = 0
    incomplete_reps: int = 0
    invalid_reps: int = 0
    insufficient_data_reps: int = 0
    overall_score: Optional[float] = None
    best_score: Optional[float] = None
    worst_score: Optional[float] = None
    category_averages: Dict[str, Optional[float]] = {}
    summary_feedback: List[str] = []
    reps: List[CompactRepSummarySchema] = []
    created_at: Optional[str] = None
    payload_fingerprint: Optional[str] = None
    client_notes: Optional[str] = None


class FinalizeSessionRequest(BaseModel):
    """Optional client request body for explicit REST finalization."""
    client_duration_seconds: Optional[int] = None
    client_notes: Optional[str] = None


# =============================================================================
# PHASE 9C.6.1: FORM EVIDENCE & ISSUE NORMALIZATION SCHEMAS
# =============================================================================

from pydantic import Field, field_validator, model_validator
from backend.app.schemas.exercise import CANONICAL_CV_EXERCISES, PROHIBITED_MEDICAL_PHRASES
from backend.app.seeds.corrective_mappings import (
    HEURISTIC_NAME_TO_ISSUE_ID,
    RAW_CORRECTIVE_MAPPINGS,
)

VALID_ISSUE_IDS: set[str] = set(m["issue_id"] for m in RAW_CORRECTIVE_MAPPINGS)

MeasurementUnit = Literal[
    "degrees",
    "ratio",
    "normalized_offset",
    "percent_difference",
    "variance",
    "unitless",
]
VALID_MEASUREMENT_UNITS: set[str] = {
    "degrees",
    "ratio",
    "normalized_offset",
    "percent_difference",
    "variance",
    "unitless",
}


class FormMeasurementData(BaseModel):
    """Polymorphic measurement payload supporting diverse heuristic dimensions."""
    unit: MeasurementUnit
    observed_value: Optional[float] = None
    reference_value: Optional[Union[float, List[float]]] = None
    deviation: Optional[float] = None


class NormalizedFormIssue(BaseModel):
    """Authoritative normalized form issue record."""
    exercise_id: str
    issue_id: str
    source_heuristic: str
    category: HeuristicCategory
    status: ObservabilityStatus
    is_acceptable: Optional[bool] = None
    confidence: float = Field(default=0.0, ge=0.0, le=1.0)
    measurement: Optional[FormMeasurementData] = None
    rep_index: Optional[int] = None
    movement_phase: Optional[str] = None
    feedback: str
    validation_metadata: Dict[str, Any] = Field(default_factory=dict)

    @field_validator("category", mode="before")
    @classmethod
    def validate_category(cls, v: Any) -> HeuristicCategory:
        if isinstance(v, HeuristicCategory):
            return v
        if isinstance(v, str):
            for cat in HeuristicCategory:
                if v == cat.value or v == cat.name:
                    return cat
            try:
                return HeuristicCategory(v)
            except ValueError:
                valid_cats = [c.value for c in HeuristicCategory]
                raise ValueError(f"Invalid category '{v}'. Must be one of {valid_cats}")
        return v

    @field_validator("status", mode="before")
    @classmethod
    def validate_status(cls, v: Any) -> ObservabilityStatus:
        if isinstance(v, ObservabilityStatus):
            return v
        if isinstance(v, str):
            for stat in ObservabilityStatus:
                if v == stat.value or v == stat.name:
                    return stat
            try:
                return ObservabilityStatus(v)
            except ValueError:
                valid_stats = [s.value for s in ObservabilityStatus]
                raise ValueError(f"Invalid status '{v}'. Must be one of {valid_stats}")
        return v

    @field_validator("issue_id")
    @classmethod
    def validate_issue_id(cls, v: str) -> str:
        if v not in VALID_ISSUE_IDS:
            raise ValueError(
                f"Unknown canonical issue_id '{v}'. Must be one of {sorted(VALID_ISSUE_IDS)}"
            )
        return v

    @field_validator("exercise_id")
    @classmethod
    def validate_exercise_id(cls, v: str) -> str:
        if v not in CANONICAL_CV_EXERCISES:
            raise ValueError(f"Exercise '{v}' is not a canonical CV exercise.")
        return v

    @field_validator("source_heuristic")
    @classmethod
    def validate_heuristic_mapping(cls, v: str, info) -> str:
        exercise_id = info.data.get("exercise_id")
        issue_id = info.data.get("issue_id")
        if exercise_id and issue_id and exercise_id in CANONICAL_CV_EXERCISES:
            expected_issue = HEURISTIC_NAME_TO_ISSUE_ID.get((exercise_id, v))
            if expected_issue is None:
                raise ValueError(f"Heuristic '{v}' is not valid for exercise '{exercise_id}'.")
            if expected_issue != issue_id:
                raise ValueError(
                    f"Heuristic '{v}' maps to issue '{expected_issue}', not '{issue_id}'."
                )
        return v

    @field_validator("feedback")
    @classmethod
    def validate_non_medical_language(cls, v: str) -> str:
        lower_fb = v.lower()
        for phrase in PROHIBITED_MEDICAL_PHRASES:
            if phrase in lower_fb:
                raise ValueError(f"Feedback contains prohibited medical phrase: '{phrase}'")
        return v

    @model_validator(mode="after")
    def validate_model_integrity(self) -> "NormalizedFormIssue":
        if self.exercise_id in CANONICAL_CV_EXERCISES:
            expected_issue = HEURISTIC_NAME_TO_ISSUE_ID.get((self.exercise_id, self.source_heuristic))
            if expected_issue is None:
                raise ValueError(
                    f"Heuristic '{self.source_heuristic}' is not valid for exercise '{self.exercise_id}'."
                )
            if expected_issue != self.issue_id:
                raise ValueError(
                    f"Heuristic '{self.source_heuristic}' maps to issue '{expected_issue}', not '{self.issue_id}'."
                )
        return self


NormalizedFormIssueSchema = NormalizedFormIssue

