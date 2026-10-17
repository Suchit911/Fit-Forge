/**
 * Personalization & Adaptive Performance Signal Domain Types (Phase 9C.1).
 * Matches the canonical serialization of the FastAPI backend endpoints:
 * GET /api/v1/personalization/signals
 * GET /api/v1/personalization/exercises/{exercise_id}
 */

export type EvidenceLevel =
  | 'no_data'
  | 'insufficient_data'
  | 'emerging_signal'
  | 'stable_signal'

export type TrendDirection =
  | 'increasing'
  | 'stable'
  | 'decreasing'
  | 'insufficient_data'

export type PerformanceTrajectory =
  | 'improving'
  | 'stable'
  | 'declining'
  | 'insufficient_data'

export type AdherenceTier =
  | 'high_adherence'
  | 'moderate_adherence'
  | 'low_adherence'
  | 'insufficient_data'

export type RepPerformanceStatus =
  | 'above_target'
  | 'on_target'
  | 'below_target'
  | 'insufficient_data'

export type ConsistencyStatus =
  | 'consistent'
  | 'irregular'
  | 'infrequent'
  | 'insufficient_data'

export type FormScoreTrend =
  | 'improving'
  | 'stable'
  | 'declining'
  | 'insufficient_data'

export interface LoadProgressionSignal {
  exerciseId: string
  trend: TrendDirection
  evidenceLevel: EvidenceLevel
  sessionsObserved: number
  recentAvgWeightKg: number
  baselineAvgWeightKg: number
  percentageChange: number
  thresholdDescription: string
}

export interface RepPerformanceSignal {
  exerciseId: string
  status: RepPerformanceStatus
  evidenceLevel: EvidenceLevel
  totalSetsWithTargets: number
  avgActualReps: number
  avgTargetReps: number
  upperBoundCompletionCount: number
  upperBoundCompletionRate: number
  targetRangeCompletionCount: number
  targetRangeCompletionRate: number
  repCompletionRatio: number
}

export interface ExercisePerformanceSummary {
  exerciseId: string
  exerciseName: string
  sessionsObserved: number
  totalSetsPerformed: number
  totalRepsPerformed: number
  totalVolumeKg: number
  avgRepsPerSet: number
  avgWeightKg: number
  bestWeightKg: number
  bestEstimated1RM: number
  prWeightKg: number
  prReps: number
  prDate?: string | null
  loadProgression: LoadProgressionSignal
  repPerformance: RepPerformanceSignal
  performanceTrajectory: PerformanceTrajectory
  evidenceLevel: EvidenceLevel
  lastPerformedDate?: string | null
}

export interface SetAdherenceSignal {
  tier: AdherenceTier
  evidenceLevel: EvidenceLevel
  totalSessionsEvaluated: number
  totalCompletedSets: number
  totalPlannedSets: number
  overallCompletionRate: number
  adherenceByExercise: Record<string, number>
}

export interface WorkoutAdherenceTrend {
  observationWindowDays: number
  sessionsCompleted: number
  expectedSessions?: number | null
  adherenceRate?: number | null
  observedFrequencyPerWeek: number
  expectedFrequencyPerWeek?: number | null
  avgDaysBetweenWorkouts: number
  maxGapDays: number
  consistencyStatus: ConsistencyStatus
  evidenceLevel: EvidenceLevel
}

export interface FormIssueFrequency {
  issue: string
  occurrenceCount: number
  totalSessionsWithExercise: number
  frequencyRate: number
  isRecurring: boolean
}

export interface ExerciseFormSignal {
  exerciseId: string
  canonicalCvExercise: string
  sessionsObserved: number
  totalRepsAnalyzed: number
  avgFormScore?: number | null
  scoreTrend: FormScoreTrend
  latestIssue?: string | null
  detectedIssues: FormIssueFrequency[]
  evidenceLevel: EvidenceLevel
}

export interface PersonalizationSignalsResponse {
  userId: string
  generatedAt: string
  windowDays: number
  overallAdherence: SetAdherenceSignal
  workoutAdherenceTrend: WorkoutAdherenceTrend
  exercises: Record<string, ExercisePerformanceSummary>
  formSignals: Record<string, ExerciseFormSignal>
  summaryMetrics: {
    totalCompletedWorkouts: number
    trackedExercisesCount: number
    cvExercisesTracked: number
    [key: string]: any
  }
}
