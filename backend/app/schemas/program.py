"""
Program Schemas & Lifecycle Models (Phase 9C.3 & 9C.4).

Defines strongly typed domain models for persistent user workout programs / mesocycles:
- Lifecycle states: draft, active, completed, abandoned
- Authoritative plan snapshot persistence (immutable baseline)
- Effective plan snapshot persistence & versioning (Phase 9C.4)
- Completed workout session tracking and synchronization
- Adaptation decision audit history storage (keyed by decisionId)
- Versioning and bounded representation
"""

from typing import List, Optional, Literal, Dict, Any
from pydantic import BaseModel, Field, AliasChoices, field_serializer, model_validator
from .workout_plan import WorkoutPlanResponse, WorkoutSplitType, PLANNER_VERSION, PlannedWorkoutDay
from .adaptation import AdaptationDecision

PROGRAM_SCHEMA_VERSION: str = "1.1.0"
PROGRAM_VERSION: str = "9C.3"
MAX_PROGRAM_DOC_BYTES: int = 800 * 1024  # 800 KB threshold (Firestore max is 1 MB)


ProgramStatus = Literal["draft", "active", "completed", "abandoned"]


class ProgramCompletedWorkout(BaseModel):
    """Compact summary reference to a completed workout session in the program."""
    sessionId: str = Field(..., validation_alias=AliasChoices("sessionId", "session_id"))
    planId: str = Field(..., validation_alias=AliasChoices("planId", "plan_id"))
    weekNumber: int = Field(..., validation_alias=AliasChoices("weekNumber", "week_number"), ge=1)
    dayNumber: int = Field(..., validation_alias=AliasChoices("dayNumber", "day_number"), ge=1)
    completedAt: str = Field(..., validation_alias=AliasChoices("completedAt", "completed_at"))
    durationSeconds: int = Field(default=0, validation_alias=AliasChoices("durationSeconds", "duration_seconds"), ge=0)
    completedSetsCount: int = Field(default=0, validation_alias=AliasChoices("completedSetsCount", "completed_sets_count"), ge=0)
    totalSetsCount: int = Field(default=0, validation_alias=AliasChoices("totalSetsCount", "total_sets_count"), ge=0)

    model_config = {"extra": "ignore", "populate_by_name": True}


class ProgramDocument(BaseModel):
    """
    Authoritative persistent program lifecycle record stored at:
    users/{uid}/programs/{programId}
    """
    programId: str = Field(..., validation_alias=AliasChoices("programId", "program_id"))
    userId: str = Field(..., validation_alias=AliasChoices("userId", "user_id"))
    planId: str = Field(..., validation_alias=AliasChoices("planId", "plan_id"))
    title: str
    status: ProgramStatus = "active"
    splitType: WorkoutSplitType = Field(..., validation_alias=AliasChoices("splitType", "split_type"))
    totalWeeks: int = Field(..., validation_alias=AliasChoices("totalWeeks", "total_weeks"), ge=1)
    daysPerWeek: int = Field(..., validation_alias=AliasChoices("daysPerWeek", "days_per_week"), ge=1)
    currentWeek: int = Field(default=1, validation_alias=AliasChoices("currentWeek", "current_week"), ge=1)
    currentDay: int = Field(default=1, validation_alias=AliasChoices("currentDay", "current_day"), ge=1)
    startedAt: str = Field(..., validation_alias=AliasChoices("startedAt", "started_at"))
    updatedAt: str = Field(..., validation_alias=AliasChoices("updatedAt", "updated_at"))
    completedAt: Optional[str] = Field(default=None, validation_alias=AliasChoices("completedAt", "completed_at"))
    abandonedAt: Optional[str] = Field(default=None, validation_alias=AliasChoices("abandonedAt", "abandoned_at"))
    completedWorkouts: List[ProgramCompletedWorkout] = Field(default_factory=list, validation_alias=AliasChoices("completedWorkouts", "completed_workouts"))
    totalPlannedWorkouts: int = Field(default=0, validation_alias=AliasChoices("totalPlannedWorkouts", "total_planned_workouts"), ge=0)
    adaptationHistory: List[Dict[str, Any]] = Field(default_factory=list, validation_alias=AliasChoices("adaptationHistory", "adaptation_history"))
    planSnapshot: WorkoutPlanResponse = Field(..., validation_alias=AliasChoices("planSnapshot", "plan_snapshot"))
    effectivePlanSnapshot: Optional[WorkoutPlanResponse] = Field(default=None, validation_alias=AliasChoices("effectivePlanSnapshot", "effective_plan_snapshot"))
    planVersion: int = Field(default=1, validation_alias=AliasChoices("planVersion", "plan_version"), ge=1)
    pendingNextBlockSplit: Optional[Dict[str, Any]] = Field(default=None, validation_alias=AliasChoices("pendingNextBlockSplit", "pending_next_block_split"))
    createdFrom: Optional[str] = Field(default="generated_plan", validation_alias=AliasChoices("createdFrom", "created_from"))
    programVersion: str = Field(default=PROGRAM_VERSION, validation_alias=AliasChoices("programVersion", "program_version"))
    programSchemaVersion: str = Field(default=PROGRAM_SCHEMA_VERSION, validation_alias=AliasChoices("programSchemaVersion", "program_schema_version"))
    planSchemaVersion: str = Field(default=PLANNER_VERSION, validation_alias=AliasChoices("planSchemaVersion", "plan_schema_version"))

    @field_serializer("planSnapshot", mode="plain")
    def serialize_plan_snapshot(self, v: Any) -> Dict[str, Any]:
        """Ensures planSnapshot outputs both camelCase and snake_case keys for key fields."""
        if isinstance(v, dict):
            data = dict(v)
            if "plan_id" in data and "planId" not in data:
                data["planId"] = data["plan_id"]
            if "planId" in data and "plan_id" not in data:
                data["plan_id"] = data["planId"]
            return data
        data = v.model_dump(by_alias=True)
        data["planId"] = v.planId
        data["splitType"] = v.splitType.value if hasattr(v.splitType, "value") else str(v.splitType)
        data["totalWeeks"] = v.totalWeeks
        data["trainingDaysPerWeek"] = v.trainingDaysPerWeek
        return data

    @field_serializer("effectivePlanSnapshot", mode="plain")
    def serialize_effective_plan_snapshot(self, v: Any) -> Optional[Dict[str, Any]]:
        """Ensures effectivePlanSnapshot outputs both camelCase and snake_case keys."""
        if v is None:
            return None
        if isinstance(v, dict):
            data = dict(v)
            if "plan_id" in data and "planId" not in data:
                data["planId"] = data["plan_id"]
            if "planId" in data and "plan_id" not in data:
                data["plan_id"] = data["planId"]
            return data
        data = v.model_dump(by_alias=True)
        data["planId"] = v.planId
        data["splitType"] = v.splitType.value if hasattr(v.splitType, "value") else str(v.splitType)
        data["totalWeeks"] = v.totalWeeks
        data["trainingDaysPerWeek"] = v.trainingDaysPerWeek
        return data

    model_config = {"extra": "ignore", "populate_by_name": True}


class ProgramResponse(ProgramDocument):
    """Response representation identical to document schema."""
    pass


# ============================================================================
# API Request & Response Models
# ============================================================================

class ProgramStartRequest(BaseModel):
    """Request payload to start a persistent program from a generated plan."""
    plan: WorkoutPlanResponse
    title: Optional[str] = None
    createdFrom: Optional[str] = Field(default="generated_plan", validation_alias=AliasChoices("createdFrom", "created_from"))

    model_config = {"extra": "ignore", "populate_by_name": True}


class ProgramSyncSessionRequest(BaseModel):
    """Request payload to synchronize a completed workout session with the active program."""
    sessionId: str = Field(..., validation_alias=AliasChoices("sessionId", "session_id"))
    weekNumber: Optional[int] = Field(default=None, validation_alias=AliasChoices("weekNumber", "week_number"), ge=1)
    dayNumber: Optional[int] = Field(default=None, validation_alias=AliasChoices("dayNumber", "day_number"), ge=1)

    model_config = {"extra": "ignore", "populate_by_name": True}


class ProgramAbandonRequest(BaseModel):
    """Request payload to abandon an active program."""
    reason: Optional[str] = None

    model_config = {"extra": "ignore", "populate_by_name": True}


class EffectivePrescriptionResponse(BaseModel):
    """Response model for GET /api/v1/programs/active/prescription/{week}/{day}."""
    programId: str = Field(..., validation_alias=AliasChoices("programId", "program_id"))
    planId: str = Field(..., validation_alias=AliasChoices("planId", "plan_id"))
    planVersion: int = Field(default=1, validation_alias=AliasChoices("planVersion", "plan_version"))
    weekNumber: int = Field(..., validation_alias=AliasChoices("weekNumber", "week_number"))
    dayNumber: int = Field(..., validation_alias=AliasChoices("dayNumber", "day_number"))
    phaseLabel: str = Field(default="", validation_alias=AliasChoices("phaseLabel", "phase_label"))
    isAdapted: bool = Field(default=False, validation_alias=AliasChoices("isAdapted", "is_adapted"))
    isCompleted: bool = Field(default=False, validation_alias=AliasChoices("isCompleted", "is_completed"))
    day: PlannedWorkoutDay
    appliedAdaptations: List[Dict[str, Any]] = Field(default_factory=list, validation_alias=AliasChoices("appliedAdaptations", "applied_adaptations"))

    model_config = {"extra": "ignore", "populate_by_name": True}


class ApplyAdaptationRequest(BaseModel):
    """Payload for POST /api/v1/programs/active/apply-adaptation."""
    decision: AdaptationDecision
    programId: Optional[str] = Field(default=None, validation_alias=AliasChoices("programId", "program_id"))
    planId: Optional[str] = Field(default=None, validation_alias=AliasChoices("planId", "plan_id"))

    model_config = {"extra": "ignore", "populate_by_name": True}


class ApplyAdaptationResponse(BaseModel):
    """Response payload for POST /api/v1/programs/active/apply-adaptation."""
    programId: str = Field(..., validation_alias=AliasChoices("programId", "program_id"))
    planVersion: int = Field(..., validation_alias=AliasChoices("planVersion", "plan_version"))
    status: Literal["applied", "already_applied", "constrained", "rejected"]
    decisionId: str = Field(..., validation_alias=AliasChoices("decisionId", "decision_id"))
    adaptationType: str = Field(..., validation_alias=AliasChoices("adaptationType", "adaptation_type"))
    ruleCode: str = Field(..., validation_alias=AliasChoices("ruleCode", "rule_code"))
    affectedDaysCount: int = Field(default=0, validation_alias=AliasChoices("affectedDaysCount", "affected_days_count"))
    details: str
    adaptationRecord: Optional[Dict[str, Any]] = Field(default=None, validation_alias=AliasChoices("adaptationRecord", "adaptation_record"))
    program: ProgramResponse

    model_config = {"extra": "ignore", "populate_by_name": True}


class ProgramVersionsResponse(BaseModel):
    """Response model for GET /api/v1/programs/active/versions."""
    programId: str = Field(..., validation_alias=AliasChoices("programId", "program_id"))
    programVersion: str = Field(..., validation_alias=AliasChoices("programVersion", "program_version"))
    planVersion: int = Field(default=1, validation_alias=AliasChoices("planVersion", "plan_version"))
    totalAdaptationsApplied: int = Field(default=0, validation_alias=AliasChoices("totalAdaptationsApplied", "total_adaptations_applied"))
    adaptationHistory: List[Dict[str, Any]] = Field(default_factory=list, validation_alias=AliasChoices("adaptationHistory", "adaptation_history"))
    pendingNextBlockSplit: Optional[Dict[str, Any]] = Field(default=None, validation_alias=AliasChoices("pendingNextBlockSplit", "pending_next_block_split"))

    model_config = {"extra": "ignore", "populate_by_name": True}
