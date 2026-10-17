"""
Personalization & Adaptive Performance Signal Schemas (Phase 9C.1).

Defines strongly typed, deterministic domain models for historical performance analytics,
load progression trends, rep-range achievement, set adherence, workout consistency,
and computer-vision form analysis recurrence.

Strict Invariants:
1. Analytics ONLY: No progression decisions, load adjustments, or workout alterations.
2. Grounded Data: Derived exclusively from authoritative completed sessions and form analysis history.
3. Explicit Evidence Levels: Distinguishes no_data, insufficient_data, emerging_signal, and stable_signal.
4. Non-Medical Language: Prohibits clinical diagnoses, recovery claims, or physiological readiness assertions.
"""

from typing import List, Optional, Literal, Dict, Any
from pydantic import BaseModel, Field


# =============================================================================
# Controlled Taxonomies & Evidence Levels
# =============================================================================

EvidenceLevel = Literal[
    "no_data",             # 0 observations recorded
    "insufficient_data",   # 1 observation (cannot establish trend or trajectory)
    "emerging_signal",     # 2 observations (preliminary trend observed)
    "stable_signal",       # >= 3 observations (statistically confirmed trend)
]

TrendDirection = Literal[
    "increasing",
    "stable",
    "decreasing",
    "insufficient_data",
]

PerformanceTrajectory = Literal[
    "improving",
    "stable",
    "declining",
    "insufficient_data",
]

AdherenceTier = Literal[
    "high_adherence",       # >= 85% completed / planned sets
    "moderate_adherence",   # 65% - 84.9% completed / planned sets
    "low_adherence",        # < 65% completed / planned sets
    "insufficient_data",    # < 2 sessions evaluated
]

RepPerformanceStatus = Literal[
    "above_target",         # Consistently hits or exceeds upper rep target (>= 75% sets)
    "on_target",            # Consistently inside prescribed target range (>= 70% sets)
    "below_target",         # Misses target minimum range (< 70% inside range)
    "insufficient_data",    # No target reps available or < 2 sets recorded
]

ConsistencyStatus = Literal[
    "consistent",           # Regular training with bounded gaps (<= 5 days)
    "irregular",            # Inconsistent spacing with large gaps (> 7 days)
    "infrequent",           # Very low observed weekly frequency (< 1.5 sessions/week)
    "insufficient_data",    # < 2 sessions in observation window
]

FormScoreTrend = Literal[
    "improving",
    "stable",
    "declining",
    "insufficient_data",
]


# =============================================================================
# Component Signal Schemas
# =============================================================================

class LoadProgressionSignal(BaseModel):
    """
    Deterministic load trajectory across recent sessions for an exercise.
    Evaluates whether recorded loads are increasing, stable, or decreasing.
    Threshold: +2.5% for increasing, -2.5% for decreasing, minimum 2 sessions.
    """
    exerciseId: str
    trend: TrendDirection = "insufficient_data"
    evidenceLevel: EvidenceLevel = "insufficient_data"
    sessionsObserved: int = 0
    recentAvgWeightKg: float = 0.0
    baselineAvgWeightKg: float = 0.0
    percentageChange: float = 0.0
    thresholdDescription: str = "+2.5% increase threshold, -2.5% decrease threshold across >= 2 sessions"

    model_config = {"extra": "ignore"}


class RepPerformanceSignal(BaseModel):
    """
    Compares actual recorded repetitions against target rep ranges.
    Preserves strict boundary between actual performance and prescribed goals.
    """
    exerciseId: str
    status: RepPerformanceStatus = "insufficient_data"
    evidenceLevel: EvidenceLevel = "insufficient_data"
    totalSetsWithTargets: int = 0
    avgActualReps: float = 0.0
    avgTargetReps: float = 0.0
    upperBoundCompletionCount: int = 0
    upperBoundCompletionRate: float = 0.0
    targetRangeCompletionCount: int = 0
    targetRangeCompletionRate: float = 0.0
    repCompletionRatio: float = 0.0

    model_config = {"extra": "ignore"}


class ExercisePerformanceSummary(BaseModel):
    """
    Aggregated performance analytics for a single canonical exercise across user history.
    Reuses authoritative 1RM and PR definitions from ProgressService.
    """
    exerciseId: str
    exerciseName: str
    sessionsObserved: int = 0
    totalSetsPerformed: int = 0
    totalRepsPerformed: int = 0
    totalVolumeKg: float = 0.0
    avgRepsPerSet: float = 0.0
    avgWeightKg: float = 0.0
    bestWeightKg: float = 0.0
    bestEstimated1RM: float = 0.0
    prWeightKg: float = 0.0
    prReps: int = 0
    prDate: Optional[str] = None
    loadProgression: LoadProgressionSignal
    repPerformance: RepPerformanceSignal
    performanceTrajectory: PerformanceTrajectory = "insufficient_data"
    evidenceLevel: EvidenceLevel = "insufficient_data"
    lastPerformedDate: Optional[str] = None

    model_config = {"extra": "ignore"}


class SetAdherenceSignal(BaseModel):
    """
    Evaluates completed sets vs planned sets at both session and exercise granularity.
    Protects against single-session anomalies by aggregating across the history window.
    """
    tier: AdherenceTier = "insufficient_data"
    evidenceLevel: EvidenceLevel = "insufficient_data"
    totalSessionsEvaluated: int = 0
    totalCompletedSets: int = 0
    totalPlannedSets: int = 0
    overallCompletionRate: float = 0.0
    adherenceByExercise: Dict[str, float] = Field(default_factory=dict)

    model_config = {"extra": "ignore"}


class WorkoutAdherenceTrend(BaseModel):
    """
    Analyzes session completion frequency and spacing over a bounded observation window (default 28 days).
    Does NOT invent an expected frequency if user.workoutFrequencyDaysPerWeek is not configured.
    """
    observationWindowDays: int = 28
    sessionsCompleted: int = 0
    expectedSessions: Optional[int] = None
    adherenceRate: Optional[float] = None
    observedFrequencyPerWeek: float = 0.0
    expectedFrequencyPerWeek: Optional[float] = None
    avgDaysBetweenWorkouts: float = 0.0
    maxGapDays: int = 0
    consistencyStatus: ConsistencyStatus = "insufficient_data"
    evidenceLevel: EvidenceLevel = "insufficient_data"

    model_config = {"extra": "ignore"}


class FormIssueFrequency(BaseModel):
    """Detailed occurrence frequency for an observed biomechanical technique issue."""
    issue: str
    occurrenceCount: int = 0
    totalSessionsWithExercise: int = 0
    frequencyRate: float = 0.0
    isRecurring: bool = False

    model_config = {"extra": "ignore"}


class ExerciseFormSignal(BaseModel):
    """
    Computer Vision form analysis signal for canonical CV-supported exercises.
    Restricted strictly to the 5 canonical exercises: squat, bench_press, deadlift, bicep_curl, shoulder_press.
    Does NOT prescribe corrective exercises (reserved for Phase 9C.2 / 9C.6).
    """
    exerciseId: str
    canonicalCvExercise: str
    sessionsObserved: int = 0
    totalRepsAnalyzed: int = 0
    avgFormScore: Optional[float] = None
    scoreTrend: FormScoreTrend = "insufficient_data"
    latestIssue: Optional[str] = None
    detectedIssues: List[FormIssueFrequency] = Field(default_factory=list)
    evidenceLevel: EvidenceLevel = "no_data"

    model_config = {"extra": "ignore"}


# =============================================================================
# Composite Response Schema
# =============================================================================

class PersonalizationSignalsResponse(BaseModel):
    """
    Complete structured analytics response payload for authenticated user.
    Aggregates exercise performance history, load trends, set adherence,
    frequency consistency, and CV form findings.
    """
    userId: str
    generatedAt: str
    windowDays: int = 28
    overallAdherence: SetAdherenceSignal
    workoutAdherenceTrend: WorkoutAdherenceTrend
    exercises: Dict[str, ExercisePerformanceSummary] = Field(default_factory=dict)
    formSignals: Dict[str, ExerciseFormSignal] = Field(default_factory=dict)
    summaryMetrics: Dict[str, Any] = Field(default_factory=dict)

    model_config = {"extra": "ignore"}
