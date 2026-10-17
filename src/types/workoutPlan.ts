/**
 * Deterministic Workout Plan Domain Types (Phase 9B.8.5.5).
 * Matches the canonical serialization of the FastAPI backend endpoint:
 * POST /api/v1/workout-plans/generate
 */

export type WorkoutSplitType = 'full_body' | 'upper_lower' | 'push_pull_legs'

export type ExerciseSlotRole =
  | 'warmup_corrective'
  | 'primary_compound'
  | 'secondary_compound'
  | 'accessory_1'
  | 'accessory_2'
  | 'core_mobility'

export type DurationFeasibility =
  | 'feasible'
  | 'potentially_over_target'
  | 'impossible_under_constraints'

export type FitnessGoal =
  | 'muscle_gain'
  | 'fat_loss'
  | 'strength'
  | 'endurance'
  | 'general_fitness'

export type DifficultyLevel = 'beginner' | 'intermediate' | 'advanced'

export type EnvironmentType = 'gym' | 'home' | 'outdoor' | 'anywhere'

export type EquipmentType =
  | 'bodyweight'
  | 'dumbbells'
  | 'barbell'
  | 'kettlebell'
  | 'resistance_bands'
  | 'cable_machine'
  | 'smith_machine'
  | 'leg_press'
  | 'pull_up_bar'
  | 'yoga_mat'
  | 'bench'
  | 'incline_bench'
  | 'trap_bar'
  | 'dip_station'
  | 'box_platform'

export type MuscleGroup =
  | 'chest'
  | 'shoulders'
  | 'triceps'
  | 'biceps'
  | 'back'
  | 'quadriceps'
  | 'hamstrings'
  | 'glutes'
  | 'calves'
  | 'abs'
  | 'core'
  | 'full_body'

export type MovementPattern =
  | 'squat'
  | 'hinge'
  | 'horizontal_push'
  | 'horizontal_pull'
  | 'vertical_push'
  | 'vertical_pull'
  | 'lunge'
  | 'isolation'
  | 'core_anti_extension'
  | 'core_anti_rotation'
  | 'carry'
  | 'mobility'

export interface PlannedSet {
  set_number: number
  target_reps: number
  target_reps_min?: number | null
  target_reps_max?: number | null
  target_rpe?: number | null
  rest_seconds: number
  target_weight_kg?: number | null
  weight_kg?: number | null
  notes?: string | null
}

export interface PlannedExercise {
  slot_role: ExerciseSlotRole
  slotRole?: ExerciseSlotRole
  slot_index: number
  slotIndex?: number
  exercise_id: string
  exerciseId?: string
  name: string
  movement_pattern: MovementPattern
  movementPattern?: MovementPattern
  exercise_type: string
  exerciseType?: string
  difficulty: DifficultyLevel
  equipment: EquipmentType[]
  primary_muscles: MuscleGroup[]
  primaryMuscles?: MuscleGroup[]
  prescribed_sets: PlannedSet[]
  prescribedSets?: PlannedSet[]
  total_sets: number
  totalSets?: number
  estimated_duration_minutes: number
  estimatedDurationMinutes?: number
  target_weight_kg?: number | null
  targetWeightKg?: number | null
  weight_kg?: number | null
  weightKg?: number | null
  is_adapted?: boolean
  isAdapted?: boolean
  score: number
  reasons: string[]
  is_canonical_cv: boolean
  isCanonicalCv?: boolean
  progression_note?: string | null
  progressionNote?: string | null
  prescription_rationale?: string | null
  prescriptionRationale?: string | null
}

export interface PlannedWorkoutDay {
  day_number: number
  dayNumber?: number
  day_label: string
  dayLabel?: string
  is_rest_day: boolean
  isRestDay?: boolean
  focus: string
  target_patterns: MovementPattern[]
  targetPatterns?: MovementPattern[]
  target_muscles: MuscleGroup[]
  targetMuscles?: MuscleGroup[]
  exercises: PlannedExercise[]
  total_sets: number
  totalSets?: number
  estimated_duration_minutes: number
  estimatedDurationMinutes?: number
}

export interface PlannedWeek {
  week_number: number
  weekNumber?: number
  phase_label: string
  phaseLabel?: string
  days: PlannedWorkoutDay[]
  total_weekly_sets: number
  totalWeeklySets?: number
  total_workouts: number
  totalWorkouts?: number
}

export interface WorkoutPlanResponse {
  plan_id: string
  title: string
  description: string
  target_goal: FitnessGoal
  fitness_level: DifficultyLevel
  split_type: WorkoutSplitType
  training_days_per_week: number
  total_weeks: number
  weeks: PlannedWeek[]
  applied_filters: Record<string, any>
  feasibility_check_passed: boolean
  duration_feasibility: DurationFeasibility
  diagnostics: string[]
  conflicting_filters: string[]
}

export interface WorkoutPlanGenerateRequest {
  target_goal?: FitnessGoal
  fitness_level?: DifficultyLevel
  environment?: EnvironmentType
  available_equipment?: EquipmentType[] | null
  training_days_per_week?: number
  plan_duration_weeks?: number
  target_workout_duration_minutes?: number
  excluded_exercise_ids?: string[]
  excluded_equipment?: EquipmentType[]
  preferred_movement_patterns?: MovementPattern[]
  target_muscles?: MuscleGroup[]
  corrective_source_exercise_id?: string | null
  corrective_issue_id?: string | null
  form_analysis_supported_only?: boolean
  preferred_split?: WorkoutSplitType | null
}
