/**
 * Program & Mesocycle Lifecycle Domain Types (Phase 9C.5.1).
 *
 * Defines strongly typed contracts for persistent user workout programs matching
 * the approved FastAPI backend schemas in `backend/app/schemas/program.py`:
 * - Lifecycle states: draft, active, completed, abandoned
 * - Completed workout summaries and mesocycle progress
 * - Authoritative program documents & snapshots
 * - Authoritative effective day prescriptions (EffectivePrescriptionResponse)
 * - Program versioning and adaptation audit history (ProgramVersionsResponse)
 * - Request payloads for starting, syncing, and abandoning programs
 */

import type {
  WorkoutPlanResponse,
  WorkoutSplitType,
  PlannedWorkoutDay,
} from './workoutPlan.ts'

export type ProgramStatus = 'draft' | 'active' | 'completed' | 'abandoned'

export interface ProgramCompletedWorkout {
  sessionId: string
  session_id?: string
  planId: string
  plan_id?: string
  weekNumber: number
  week_number?: number
  dayNumber: number
  day_number?: number
  completedAt: string
  completed_at?: string
  durationSeconds: number
  duration_seconds?: number
  completedSetsCount: number
  completed_sets_count?: number
  totalSetsCount: number
  total_sets_count?: number
}

export interface AdaptationAuditRecord {
  decisionId: string
  decision_id?: string
  appliedAt: string
  applied_at?: string
  adaptationType: string
  adaptation_type?: string
  ruleCode: string
  rule_code?: string
  exerciseId?: string | null
  exercise_id?: string | null
  affectedExerciseId?: string | null
  affected_exercise_id?: string | null
  affectedDays?: Array<{ weekNumber: number; dayNumber: number }>
  affected_days?: Array<{ week_number: number; day_number: number }>
  affectedDaysCount?: number
  affected_days_count?: number
  versionBefore?: number
  version_before?: number
  versionAfter?: number
  version_after?: number
  programId?: string
  program_id?: string
  status?: string
  details?: string
  previousPrescription?: Record<string, any> | null
  previous_prescription?: Record<string, any> | null
  appliedPrescription?: Record<string, any> | null
  applied_prescription?: Record<string, any> | null
  proposedPrescription?: Record<string, any> | null
  proposed_prescription?: Record<string, any> | null
  constraints?: string[]
  evidence?: Record<string, any> | null
  rationale?: string
  reasons?: string[]
  isReversible?: boolean
  is_reversible?: boolean
}

export interface ProgramResponse {
  programId: string
  program_id?: string
  userId: string
  user_id?: string
  planId: string
  plan_id?: string
  title: string
  status: ProgramStatus
  splitType: WorkoutSplitType
  split_type?: WorkoutSplitType
  totalWeeks: number
  total_weeks?: number
  daysPerWeek: number
  days_per_week?: number
  currentWeek: number
  current_week?: number
  currentDay: number
  current_day?: number
  startedAt: string
  started_at?: string
  updatedAt: string
  updated_at?: string
  completedAt?: string | null
  completed_at?: string | null
  abandonedAt?: string | null
  abandoned_at?: string | null
  completedWorkouts: ProgramCompletedWorkout[]
  completed_workouts?: ProgramCompletedWorkout[]
  totalPlannedWorkouts: number
  total_planned_workouts?: number
  adaptationHistory: AdaptationAuditRecord[]
  adaptation_history?: AdaptationAuditRecord[]
  planSnapshot: WorkoutPlanResponse
  plan_snapshot?: WorkoutPlanResponse
  effectivePlanSnapshot?: WorkoutPlanResponse | null
  effective_plan_snapshot?: WorkoutPlanResponse | null
  planVersion: number
  plan_version?: number
  pendingNextBlockSplit?: Record<string, any> | null
  pending_next_block_split?: Record<string, any> | null
  createdFrom?: string
  created_from?: string
  programVersion: string
  program_version?: string
  programSchemaVersion: string
  program_schema_version?: string
  planSchemaVersion: string
  plan_schema_version?: string
}

export interface AppliedAdaptationSummary {
  decisionId: string
  decision_id?: string
  adaptationType: string
  adaptation_type?: string
  ruleCode: string
  rule_code?: string
  exerciseId?: string | null
  exercise_id?: string | null
  affectedExerciseId?: string | null
  affected_exercise_id?: string | null
  deltaMagnitude?: number | null
  delta_magnitude?: number | null
  deltaUnit?: string | null
  delta_unit?: string | null
  versionBefore?: number
  version_before?: number
  versionAfter?: number
  version_after?: number
  appliedAt?: string
  applied_at?: string
  details?: string
  previousPrescription?: Record<string, any> | null
  previous_prescription?: Record<string, any> | null
  appliedPrescription?: Record<string, any> | null
  applied_prescription?: Record<string, any> | null
  proposedPrescription?: Record<string, any> | null
  proposed_prescription?: Record<string, any> | null
  constraints?: string[]
  evidence?: Record<string, any> | null
  rationale?: string
  reasons?: string[]
}

export interface EffectivePrescriptionResponse {
  programId: string
  program_id?: string
  planId: string
  plan_id?: string
  planVersion: number
  plan_version?: number
  weekNumber: number
  week_number?: number
  dayNumber: number
  day_number?: number
  phaseLabel: string
  phase_label?: string
  isAdapted: boolean
  is_adapted?: boolean
  isCompleted: boolean
  is_completed?: boolean
  day: PlannedWorkoutDay
  appliedAdaptations: AppliedAdaptationSummary[]
  applied_adaptations?: AppliedAdaptationSummary[]
}

export interface ProgramVersionsResponse {
  programId: string
  program_id?: string
  programVersion: string
  program_version?: string
  planVersion: number
  plan_version?: number
  totalAdaptationsApplied: number
  total_adaptations_applied?: number
  adaptationHistory: AdaptationAuditRecord[]
  adaptation_history?: AdaptationAuditRecord[]
  pendingNextBlockSplit?: Record<string, any> | null
  pending_next_block_split?: Record<string, any> | null
}

export interface ProgramStartRequest {
  plan: WorkoutPlanResponse
  title?: string
  createdFrom?: string
  created_from?: string
}

export interface ProgramSyncSessionRequest {
  sessionId: string
  session_id?: string
  weekNumber?: number
  week_number?: number
  dayNumber?: number
  day_number?: number
}

export interface ProgramAbandonRequest {
  reason?: string
}

/**
 * Backend schema compatibility interfaces for apply-adaptation.
 * NOTE: As required by Phase 9C.5 boundaries, these are NOT exposed to normal frontend UI workflows.
 */
export interface ApplyAdaptationRequest {
  decision: any // AdaptationDecision
  programId?: string
  planId?: string
}

export interface ApplyAdaptationResponse {
  programId: string
  program_id?: string
  planVersion: number
  plan_version?: number
  status: 'applied' | 'already_applied' | 'constrained' | 'rejected'
  decisionId: string
  decision_id?: string
  adaptationType: string
  adaptation_type?: string
  ruleCode: string
  rule_code?: string
  affectedDaysCount: number
  affected_days_count?: number
  details: string
  adaptationRecord?: Record<string, any> | null
  adaptation_record?: Record<string, any> | null
  program: ProgramResponse
}
