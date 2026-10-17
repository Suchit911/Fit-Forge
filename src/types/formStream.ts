/**
 * Strongly typed contracts for Phase 9B.6 Frontend Live Form Analysis Streaming.
 * Matches backend schemas from Phase 9A, 9B.1, 9B.2, 9B.3, 9B.4, and 9B.5.
 */

// Supported exercise IDs (Strictly 5 supported by backend engine)
export type SupportedExerciseId =
  | 'squat'
  | 'bench_press'
  | 'deadlift'
  | 'bicep_curl'
  | 'shoulder_press'

export const SUPPORTED_EXERCISES: { id: SupportedExerciseId; name: string; targetMuscles: string }[] = [
  { id: 'squat', name: 'Barbell Squat', targetMuscles: 'Quadriceps, Glutes, Hamstrings' },
  { id: 'bench_press', name: 'Barbell Bench Press', targetMuscles: 'Pectorals, Triceps, Anterior Deltoids' },
  { id: 'deadlift', name: 'Conventional Deadlift', targetMuscles: 'Posterior Chain, Glutes, Erector Spinae' },
  { id: 'bicep_curl', name: 'Bicep Curl', targetMuscles: 'Biceps Brachii, Brachialis' },
  { id: 'shoulder_press', name: 'Overhead Shoulder Press', targetMuscles: 'Deltoids, Upper Pectorals, Triceps' },
]

// Stream lifecycle states
export type StreamLifecycleState =
  | 'INITIAL'
  | 'CAMERA_PERMISSION'
  | 'CAMERA_READY'
  | 'CONNECTING'
  | 'ANALYZING'
  | 'PAUSED'
  | 'ERROR'
  | 'STOPPED'

// WebSocket connection statuses
export type ConnectionStatus =
  | 'DISCONNECTED'
  | 'CONNECTING'
  | 'CONNECTED'
  | 'RECONNECTING'
  | 'ERROR'
  | 'STOPPED'

// Backend tracking observability statuses
export type ObservabilityStatus =
  | 'OBSERVED'
  | 'INSUFFICIENT_CONFIDENCE'
  | 'NOT_OBSERVABLE'
  | 'INVALID'
  | 'INSUFFICIENT_DATA'
  | 'SEARCHING'
  | 'TRACKING'
  | 'LOST'

// Pose landmark representation matching backend format
export interface PoseLandmark {
  id: number
  name: string
  x: number
  y: number
  z: number
  visibility: number
}

// Form heuristic evaluation item from backend
export interface HeuristicItem {
  name: string
  category: string
  status: string
  is_acceptable: boolean | null
  observed_value: number | null
  deviation: number | null
  feedback: string
}

// Category score breakdown from backend
export interface CategoryScoreItem {
  score: number
  penalty: number
  weight: number
}

// ============================================================================
// SERVER -> CLIENT MESSAGES (WebSocket JSON)
// ============================================================================

export interface WSAckMessage {
  type: 'ack'
  status: 'connected' | 'paused' | 'resumed' | 'dropped_rate_limit' | string
  session_id?: string
  sequence_id?: number
}

export interface WSAnalysisMessage {
  type: 'analysis'
  sequence_id: number
  session_id: string
  exercise_id: string
  timestamp_ms?: number
  latency_e2e_ms?: number | null
  processing_ms: number
  tracking_status: string
  fsm_state: string
  rep_count: number
  primary_angle?: number | null
  observability_ratio: number
  is_sufficiently_observable: boolean
  landmarks_detected: boolean
  landmarks: PoseLandmark[]
  joint_angles: Record<string, number>
  heuristics: HeuristicItem[]
  latest_score: number | null
  score_status: string | null
  feedback: string[]
}

export interface WSRepCompletedMessage {
  type: 'rep_completed'
  sequence_id: number
  session_id: string
  exercise_id: string
  rep_number: number
  fsm_outcome: string
  rom_degrees?: number | null
  duration_ms?: number | null
  score: number | null
  score_status: string | null
  category_scores?: Record<string, CategoryScoreItem>
  feedback: string[]
}

export interface WSErrorMessage {
  type: 'error'
  sequence_id?: number | null
  error: string
  detail?: string | null
  code: string
}

export interface WSPongMessage {
  type: 'pong'
  sequence_id?: number | null
  client_timestamp_ms?: number | null
  server_timestamp_ms: number
}

export interface WSStoppedMessage {
  type: 'stopped'
  session_id: string
  rep_count: number
  overall_score: number | null
  summary?: Record<string, any> | null
}

export type WSServerMessage =
  | WSAckMessage
  | WSAnalysisMessage
  | WSRepCompletedMessage
  | WSErrorMessage
  | WSPongMessage
  | WSStoppedMessage

// ============================================================================
// CLIENT -> SERVER CONTROL MESSAGES (WebSocket JSON)
// ============================================================================

export interface WSClientControlMessage {
  type: 'pause' | 'resume' | 'stop' | 'ping'
  sequence_id?: number
  timestamp_ms?: number
}

// Completed repetition summary for frontend history display
export interface CompletedRepItem {
  repNumber: number
  outcome: string
  romDegrees?: number | null
  durationMs?: number | null
  score: number | null
  scoreStatus: string | null
  feedback: string[]
}

// ============================================================================
// PHASE 9B.7: SESSION SUMMARY & HISTORY SCHEMAS
// ============================================================================

export interface CompactRepSummary {
  rep_number: number
  status: 'valid' | 'incomplete' | 'invalid' | 'insufficient_data' | string
  score: number | null
  rom_degrees?: number | null
  rom_score?: number | null
  technique_score?: number | null
  symmetry_score?: number | null
  stability_score?: number | null
  feedback: string[]
}

export interface FormAnalysisSessionSummary {
  session_id: string
  exercise_id: string
  exercise_name: string
  status: string
  started_at: string
  completed_at: string
  duration_seconds: number
  total_reps: number
  completed_reps: number
  valid_reps: number
  overall_score: number | null
}

export interface FormAnalysisSessionDetail {
  session_id: string
  user_id: string
  exercise_id: string
  canonical_exercise_id?: string
  exercise_name: string
  status: string
  started_at: string
  completed_at: string
  duration_seconds: number
  total_reps: number
  completed_reps: number
  valid_reps: number
  incomplete_reps: number
  invalid_reps: number
  insufficient_data_reps: number
  overall_score: number | null
  best_score: number | null
  worst_score: number | null
  category_averages: Record<string, number | null>
  summary_feedback: string[]
  reps: CompactRepSummary[]
  created_at?: string
}
