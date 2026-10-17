/**
 * Deterministic Progression & Adaptation Engine Domain Contracts (Phase 9C.2).
 * Matches the canonical serialization of the FastAPI backend endpoints:
 * GET /api/v1/personalization/adaptations
 * POST /api/v1/personalization/adaptations/evaluate
 */

import type { EvidenceLevel } from './personalization'

export type AdaptationType =
  | 'load_progression'
  | 'rep_progression'
  | 'volume_reduction'
  | 'exercise_regression'
  | 'exercise_substitution'
  | 'split_adjustment'
  | 'recurring_form_issue'
  | 'no_change'

export type DecisionStatus =
  | 'insufficient_data'
  | 'no_change'
  | 'progression_candidate'
  | 'volume_reduction_candidate'
  | 'regression_candidate'
  | 'substitution_candidate'
  | 'future_split_adjustment_candidate'
  | 'form_issue_candidate'
  | 'constrained_no_change'

export interface PrescriptionDelta {
  exerciseId?: string
  exerciseName?: string
  weightKg?: number
  setCount?: number
  targetRepsMin?: number
  targetRepsMax?: number
  targetRpe?: number
  restSeconds?: number
}

export interface AdaptationDecision {
  decisionId: string
  exerciseId?: string
  canonicalName?: string
  adaptationType: AdaptationType
  status: DecisionStatus
  ruleCode: string
  evidenceLevel: EvidenceLevel
  evidence: Record<string, any>
  previousPrescription?: PrescriptionDelta
  proposedPrescription?: PrescriptionDelta
  deltaMagnitude?: number
  deltaUnit?: string
  rationale: string
  reasons: string[]
  constraintsApplied: string[]
  isReversible: boolean
  sourceSessionIds: string[]
  generatedAt: string
}

export interface FutureSplitRecommendation {
  currentSplit?: string
  recommendedSplit: string
  recommendedDaysPerWeek: number
  observedWeeklyFrequency: number
  plannedWeeklyFrequency?: number
  adherenceRate?: number
  ruleCode: string
  reason: string
  isFutureBlockOnly: boolean
}

export interface AdaptationEvaluationRequest {
  candidateExercises?: PrescriptionDelta[]
  targetDurationMinutes?: number
  availableEquipment?: string[]
  environment?: string
  fitnessGoal?: string
  windowDays?: number
}

export interface AdaptationEvaluationResponse {
  userId: string
  generatedAt: string
  evaluationWindowDays: number
  primaryDecisions: AdaptationDecision[]
  futureSplitProposal?: FutureSplitRecommendation
  summaryMetrics: {
    totalDecisionsEvaluated: number
    progressionCandidates: number
    volumeReductionCandidates: number
    formIssueCandidates: number
    constrainedNoChange: number
    noChange: number
    insufficientData: number
    hasFutureSplitProposal: boolean
    [key: string]: any
  }
}
