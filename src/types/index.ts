// DOMAIN INTERFACES FOR AI FITNESS PLATFORM

export type DifficultyLevel = 'beginner' | 'intermediate' | 'advanced'
export type FitnessGoal = 'muscle_gain' | 'fat_loss' | 'strength' | 'endurance' | 'general_fitness'
export type Environment = 'gym' | 'home' | 'outdoor' | 'anywhere'
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

// USER PROFILE
export interface UserProfile {
  id: string
  name: string
  email: string
  profile_complete?: boolean
  gender?: string
  age?: number
  heightCm?: number
  weightKg?: number
  targetWeightKg?: number
  fitnessLevel?: DifficultyLevel
  primaryGoal?: FitnessGoal
  secondaryGoals?: FitnessGoal[]
  environment?: Environment
  availableEquipment?: EquipmentType[]
  workoutFrequencyDaysPerWeek?: number
  workoutDurationMinutes?: number
  preferredWorkoutType?: string
  preferredTrainingTime?: string
  dietaryPreference?: string
  targetCalories?: number
  targetProteinGrams?: number
  targetCarbsGrams?: number
  targetFatGrams?: number
  hydrationGoalLiters?: number
  bmi?: number
  bmr?: number
  tdee?: number
  streakDays?: number
  totalWorkouts?: number
  totalCaloriesBurned?: number
  totalPoints?: number
}

// EXERCISE TYPES
export interface Exercise {
  id: string
  name: string
  description: string
  primaryMuscles: MuscleGroup[]
  secondaryMuscles: MuscleGroup[]
  equipment: EquipmentType[]
  difficulty: DifficultyLevel
  category: 'strength' | 'hypertrophy' | 'endurance' | 'mobility' | 'activation_warmup' | 'cardio' | 'custom'
  instructions: string[]
  commonMistakes: string[]
  safetyNotes: string[]
  supportedFormAnalysis: boolean
  supportedCameraMode?: 'front' | 'side'
}

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

export type ExerciseType = 'compound' | 'isolation'
export type Laterality = 'bilateral' | 'unilateral' | 'alternating'
export type PlaneOfMotion = 'sagittal' | 'frontal' | 'transverse' | 'multi_planar'
export type CVExerciseKey = 'squat' | 'bench_press' | 'deadlift' | 'bicep_curl' | 'shoulder_press'

export interface ExerciseKnowledge extends Exercise {
  aliases?: string[]
  movementPattern?: MovementPattern
  exerciseType?: ExerciseType
  laterality?: Laterality
  planeOfMotion?: PlaneOfMotion
  stabilizerMuscles?: MuscleGroup[]
  optionalEquipment?: EquipmentType[]
  targetEnvironments?: Environment[]
  targetGoals?: FitnessGoal[]
  setupCues?: string[]
  executionCues?: string[]
  breathingPattern?: string
  progressions?: string[]
  regressions?: string[]
  substitutions?: string[]
  complementaryExercises?: string[]
  movementCautions?: string[]
  cvExerciseId?: CVExerciseKey | null
  cvSupportedPlanes?: PlaneOfMotion[]
  cvLimitationsNote?: string
  isDeprecated?: boolean
  deprecatedReplacementId?: string
}

export interface FormCorrectiveGuidance {
  finding: string
  cue: string
  regressions: string[]
  accessoryExercises: string[]
  techniqueDrills: string[]
}

export interface ExerciseRecommendationCandidate {
  exerciseId: string
  exercise: ExerciseKnowledge
  score: number
  reasons: string[]
  isPrimaryMatch: boolean
}

export interface ExerciseRecommendationResponse {
  candidates: ExerciseRecommendationCandidate[]
  appliedFilters: Record<string, unknown>
  totalEligible: number
}

// WORKOUT TYPES
export interface WorkoutSet {
  setNumber: number
  targetReps: number
  targetWeightKg?: number
  isCompleted: boolean
  actualReps?: number
  actualWeightKg?: number
  rpe?: number
}

export interface WorkoutExercise {
  id: string
  exerciseId: string
  exercise: Exercise
  sets: WorkoutSet[]
  restSecondsBetweenSets: number
  notes?: string
}

export interface Workout {
  id: string
  title: string
  description: string
  targetEnvironment: Environment
  estimatedDurationMinutes: number
  difficulty: DifficultyLevel
  targetMuscles: MuscleGroup[]
  exercises: WorkoutExercise[]
}

export interface ActiveWorkoutState {
  workoutId: string
  currentExerciseIndex: number
  currentSetIndex: number
  elapsedSeconds: number
  isPaused: boolean
  completedSets: Record<string, WorkoutSet[]>
  isFinished: boolean
}

// NUTRITION TYPES
export interface FoodItem {
  id: string
  name: string
  calories: number
  proteinGrams: number
  carbsGrams: number
  fatGrams: number
  servingSizeGrams: number
  fiberGrams?: number
  sugarGrams?: number
  sodiumMg?: number
}

export interface Meal {
  id: string
  time: string
  type: 'breakfast' | 'lunch' | 'dinner' | 'snack'
  name: string
  totalCalories: number
  totalProteinGrams: number
  totalCarbsGrams: number
  totalFatGrams: number
  totalFiberGrams?: number
  totalSugarGrams?: number
  totalSodiumMg?: number
  image?: string
  foodList: string[]
  foods: FoodItem[]
}

export interface NutrientTargetItem {
  name: string
  current: number
  target: number
  unit: string
  pct: number
  color: string
}

export interface CalorieFlowEntry {
  label: string
  amount: number
  type: 'goal' | 'consumed' | 'remaining'
}

export interface WeeklyNutritionDay {
  day: string
  date?: string
  pct: number
  calories: number
  isCurrent?: boolean
}

export interface NutritionInsightItem {
  id: string
  type: 'positive' | 'warning' | 'info'
  title: string
  description?: string
}

export interface DailyNutrition {
  date: string
  targetCalories: number
  consumedCalories: number
  targetProteinGrams: number
  consumedProteinGrams: number
  targetCarbsGrams: number
  consumedCarbsGrams: number
  targetFatGrams: number
  consumedFatGrams: number
  targetFiberGrams?: number
  consumedFiberGrams?: number
  targetSugarGrams?: number
  consumedSugarGrams?: number
  targetSodiumMg?: number
  consumedSodiumMg?: number
  waterIntakeLiters: number
  waterTargetLiters: number
  meals: Meal[]
  nutrientTargets: NutrientTargetItem[]
  calorieFlow: CalorieFlowEntry[]
  weeklySummary: WeeklyNutritionDay[]
  insights: NutritionInsightItem[]
}

export interface CatalogFood {
  id: string
  name: string
  category: string
  caloriesPer100g: number
  proteinGramsPer100g: number
  carbsGramsPer100g: number
  fatGramsPer100g: number
  fiberGramsPer100g: number
  sugarGramsPer100g: number
  sodiumMgPer100g: number
  defaultServingGrams: number
  servingUnit?: string
}

export interface ProgressKpiItem {
  id: string
  title: string
  value: string
  changePct: string
  trendData: number[]
  color: string
}

export interface StrengthProgressPoint {
  date: string
  upperBodyKg: number
  lowerBodyKg: number
  totalVolumeKg: number
}

export interface BodyCompositionStats {
  dateCompare: string
  weightKg: number
  weightChangeKg: number
  bodyFatPct: number
  bodyFatChangePct: number
  muscleMassKg: number
  muscleMassChangeKg: number
  bmi: number
  bmiChange: number
  goalProgressPct: number
  goalKgToGo: number
}

export interface MuscleGroupProgressItem {
  name: string
  changePct: string
  status: 'Excellent' | 'Good' | 'Needs Work'
}

export interface PerformanceTrendItem {
  name: string
  value: string
  status: string
  trendData: number[]
  iconName: string
}

export interface PersonalRecordItem {
  id: string
  exerciseName: string
  category: string
  date: string
  value: string
  improvement: string
}

export interface RecentWorkoutItem {
  id: string
  title: string
  date: string
  durationMin: number
  volumeKg: number
  caloriesKcal: number
  scorePct: number
}

export interface ProgressPhotoItem {
  id: string
  date: string
  imageUrl: string
}

export interface ProgressDashboardData {
  kpis: ProgressKpiItem[]
  strengthProgress: StrengthProgressPoint[]
  bodyComposition: BodyCompositionStats
  muscleGroupProgress: MuscleGroupProgressItem[]
  performanceTrends: PerformanceTrendItem[]
  personalRecords: PersonalRecordItem[]
  recentWorkouts: RecentWorkoutItem[]
  progressPhotos: ProgressPhotoItem[]
}

export interface BodyMeasurement {
  date: string
  weightKg: number
  waistCm?: number
  chestCm?: number
  armsCm?: number
  thighsCm?: number
  bodyFatPercentage?: number
}

export interface StrengthPR {
  exerciseId: string
  exerciseName: string
  weightKg: number
  reps: number
  achievedDate: string
}

export interface ProgressSummary {
  weightHistory: BodyMeasurement[]
  personalRecords: StrengthPR[]
  workoutVolumeHistory: { date: string; volumeKg: number }[]
  weeklyConsistencyDays: number
  streakDays: number
  dashboardData?: ProgressDashboardData
}

export interface AIChatConversation {
  id: string
  title: string
  timestamp: string
  previewText: string
  dateGroup: string
}

export interface AICoachWeeklyMetric {
  title: string
  current: number
  target: number
  unit: string
  pct: number
  color: string
}

export interface SuggestedQuestionItem {
  id: string
  question: string
  iconName: string
  color: string
}

export interface AIRecommendation {
  type: 'workout_adaptation' | 'recovery' | 'nutrition' | 'form_tip'
  title: string
  description: string
  actionLabel?: string
  actionTargetUrl?: string
}

export interface AIChatMessage {
  id: string
  sender: 'user' | 'assistant'
  timestamp: string
  text: string
  structuredData?: {
    recommendations?: AIRecommendation[]
    suggestedWorkouts?: Partial<Workout>[]
    referencedScience?: string[]
  }
}

export interface AICoachDashboardData {
  conversations: AIChatConversation[]
  activeConversationId: string
  messages: AIChatMessage[]
  weeklyMetrics: AICoachWeeklyMetric[]
  insights: AIRecommendation[]
  suggestedQuestions: SuggestedQuestionItem[]
}

// FORM ANALYSIS TYPES
export interface KeyMetricItem {
  name: string
  score: number
  status: 'Excellent' | 'Good' | 'Fair' | 'Poor'
  trendData: number[]
}

export interface FormBreakdownItem {
  metric: string
  score: number
}

export interface MuscleActivationItem {
  name: string
  activationPct: number
  category: 'primary' | 'secondary' | 'stabilizer'
}

export interface RepAnalysisItem {
  repNumber: number
  elbowAngle: number
  status: 'good' | 'improvement' | 'poor' | 'skipped'
}

export interface AnalysisHistoryItem {
  id: string
  date: string
  time: string
  exerciseName: string
  weightKg: number
  score: number
}

export interface FormAnalysisSession {
  exerciseId: string
  exerciseName: string
  setInfo: string
  weightKg: number
  reps: number
  rpe: number
  restTime: string
  formScore: number
  formStatus: string
  analysisTime: string
  confidence: string
  videoAssetUrl: string
  keyMetrics: KeyMetricItem[]
  scoreBreakdown: FormBreakdownItem[]
  muscleActivation: MuscleActivationItem[]
  positiveFeedback: string[]
  improvementFeedback: string[]
  infoFeedback: string[]
  coachingTips: string[]
  repProgress: RepAnalysisItem[]
  history: AnalysisHistoryItem[]
}

export interface FormAnalysisMockState {
  isAnalyzing: boolean
  exerciseId?: string
  exerciseName?: string
  repCount: number
  formScore: number
  detectedIssues: string[]
  currentFeedback: string
  poseLandmarksDetected: boolean
}

// GAMIFICATION & ACHIEVEMENTS TYPES
export interface Achievement {
  id: string
  title: string
  description: string
  iconName: string
  unlockedAt?: string
  progressPercentage: number
  isUnlocked: boolean
}

export interface AchievementKpiItem {
  id: string
  title: string
  value: string
  supportingText: string
  iconName: string
  color: string
}

export interface RecentAchievementBadge {
  id: string
  title: string
  description: string
  timeAgo: string
  isNew?: boolean
  iconName: string
  color: string
}

export interface AchievementsProgressData {
  overallPct: number
  achievedCount: number
  inProgressCount: number
  lockedCount: number
  nextMilestone: {
    level: number
    title: string
    description: string
    currentPts: number
    targetPts: number
    ptsToGo: number
    currentLevel?: number
  }
}

export interface AchievementCategoryItem {
  id: string
  title: string
  current: number
  total: number
  pct: number
  iconName: string
  color: string
}

export interface CurrentChallengeItem {
  id: string
  title: string
  description: string
  current: number
  target: number
  unit?: string
  daysLeft: number
  iconName: string
  color: string
}

export interface LeaderboardUser {
  rank?: number | null
  name: string
  points: number
  pointsStr: string
  isCurrentUser?: boolean
}

export interface AchievementsDashboardData {
  kpis: AchievementKpiItem[]
  recentAchievements: RecentAchievementBadge[]
  progressSummary: AchievementsProgressData
  categories: AchievementCategoryItem[]
  currentChallenges: CurrentChallengeItem[]
  leaderboard: LeaderboardUser[]
}

// PROFILE TYPES
export interface ProfileHeroStats {
  name: string
  verified: boolean
  plan: string
  memberSince: string
  location: string
  quote: string
  streakDays: number
  totalWorkouts: number
  totalCaloriesBurned: number
  totalPoints: number
  rankPct: string
  avatarUrl: string
}

export interface PersonalInformationData {
  age: number
  heightCm: number
  weightKg: number
  fitnessGoal: string
  activityLevel: string
}

export interface FitnessGoalData {
  primaryGoal: string
  targetWeightKg: number
  weeklyWorkoutTarget: string
  targetDate: string
  progressPct: number
  kgToGo: number
}

export interface PersonalStatsData {
  currentWeightKg: number
  weightChangeKg: number
  bodyFatPct: number
  bodyFatChangePct: number
  muscleMassKg: number
  muscleMassChangeKg: number
  bmi: number
  bmiStatus: string
}

export interface TrainingPreferencesData {
  trainingDays: string
  preferredWorkoutType: string
  equipmentAvailable: string
  workoutDuration: string
  preferredTime: string
}

export interface NutritionPreferencesData {
  dietaryPreference: string
  dailyCalorieTarget: number
  proteinTargetGrams: number
  carbTargetGrams: number
  hydrationGoalLiters: number
}

export interface AccountPreferenceRow {
  id: string
  title: string
  description: string
  iconName: string
}

export interface ProfileDashboardData {
  hero: ProfileHeroStats
  personalInfo: PersonalInformationData
  goals: FitnessGoalData
  stats: PersonalStatsData
  trainingPref: TrainingPreferencesData
  nutritionPref: NutritionPreferencesData
  accountRows: AccountPreferenceRow[]
}

// SETTINGS TYPES
export interface GeneralSettingsData {
  language: string
  units: string
  timeZone: string
  weekStartDay: string
  defaultWorkoutDurationMin: number
}

export interface NotificationSettingsData {
  workoutReminders: boolean
  restTimerAlerts: boolean
  achievementNotifications: boolean
  nutritionReminders: boolean
  aiCoachInsights: boolean
  weeklyProgressReport: boolean
}

export interface AppearanceSettingsData {
  darkMode: boolean
  accentColor: string
  accentIntensity: string
  uiDensity: string
  animations: boolean
  reduceMotion: boolean
}

export interface PrivacySettingsData {
  profileVisibility: string
  workoutDataVisibility: string
  progressPhotosVisibility: string
  aiAnalysisData: boolean
  twoFactorEnabled: boolean
}

export interface ConnectedDeviceItem {
  id: string
  name: string
  description: string
  isConnected: boolean
  iconName: string
}

export interface AICoachSettingsData {
  personality: string
  intensity: string
  focus: string
  workoutRecommendations: string
  nutritionRecommendations: string
  formAnalysisInsights: string
}

export interface SettingsDashboardData {
  general: GeneralSettingsData
  notifications: NotificationSettingsData
  appearance: AppearanceSettingsData
  privacy: PrivacySettingsData
  devices: ConnectedDeviceItem[]
  aiCoach: AICoachSettingsData
  userId?: string
  persisted?: boolean
  updatedAt?: string | null
}


// HELP CENTER TYPES
export interface HelpTopicItem {
  id: string
  title: string
  articleCount: number
  iconName: string
  color: string
}

export interface QuickHelpGuideItem {
  id: string
  title: string
  description: string
  readTime: string
  iconName: string
  color: string
}

export interface FaqItem {
  id: string
  question: string
  answer: string
  category?: string
}

export interface ContactOptionRow {
  id: string
  title: string
  description: string
  statusAction: string
  iconName: string
}

export interface SystemStatusRow {
  id: string
  serviceName: string
  status: 'Operational' | 'Degraded' | 'Outage'
  iconName: string
}

export interface HelpCenterDashboardData {
  topics: HelpTopicItem[]
  guides: QuickHelpGuideItem[]
  faqs: FaqItem[]
  contactOptions: ContactOptionRow[]
  systemStatus: SystemStatusRow[]
}

// NOTIFICATIONS TYPES
export interface NotificationItemData {
  id: string
  type?: string
  category: 'Workout' | 'AI Coach' | 'Nutrition' | 'Achievement' | 'Progress' | 'Recovery' | 'System'
  title: string
  message: string
  createdAt?: string
  timestamp: string
  dateGroup: 'Today' | 'Yesterday' | 'Earlier'
  read: boolean
  important: boolean
  iconName: string
  actionLabel?: string
  actionRoute?: string
}

export interface NotificationCategorySummary {
  category: string
  count: number
  percentage: number
  color: string
}

export interface ImportantUpdateItem {
  id: string
  category: string
  title: string
  description: string
  timeAgo: string
  iconName: string
}

export interface NotificationsDashboardData {
  unreadCount: number
  todayCount: number
  weekCount: number
  importantCount: number
  notifications: NotificationItemData[]
  insights: NotificationCategorySummary[]
  importantUpdates: ImportantUpdateItem[]
  preferences: Record<string, boolean>
}

export * from './coach'
export * from './workoutPlan'
export * from './program'
