/**
 * @deprecated
 * STAGE 3 REAL-DATA REMEDIATION:
 * This fixture file is NOT reachable in any production application runtime paths.
 * All runtime exercises and workouts are strictly fetched from canonical backend APIs.
 * Preserved solely as a legacy reference fixture.
 */
import type { Exercise, Workout } from '../types'

export const mockExercises: Exercise[] = [

  {
    id: 'ex_bench_press',
    name: 'Bench Press',
    description: 'Primary chest hypertrophy and upper body pushing strength builder.',
    primaryMuscles: ['chest'],
    secondaryMuscles: ['shoulders', 'triceps'],
    equipment: ['barbell'],
    difficulty: 'intermediate',
    category: 'strength',
    instructions: [
      'Lie flat on the bench with feet firmly planted on the ground.',
      'Grasp the bar slightly wider than shoulder-width.',
      'Unrack the bar and lower under control to mid-chest.',
      'Press explosively back to lockout.'
    ],
    commonMistakes: ['Bouncing bar off chest', 'Flaring elbows'],
    safetyNotes: ['Use a spotter or safety bars.'],
    supportedFormAnalysis: true,
    supportedCameraMode: 'side'
  },
  {
    id: 'ex_incline_db_press',
    name: 'Incline Dumbbell Press',
    description: 'Targets upper chest clavicular head with greater freedom of movement.',
    primaryMuscles: ['chest'],
    secondaryMuscles: ['shoulders', 'triceps'],
    equipment: ['dumbbells'],
    difficulty: 'intermediate',
    category: 'hypertrophy',
    instructions: [
      'Set bench to 30 degrees.',
      'Press dumbbells upward until arms are extended.',
      'Lower under control to chest level.'
    ],
    commonMistakes: ['Setting bench angle too steep'],
    safetyNotes: ['Kick dumbbells up into position using knees.'],
    supportedFormAnalysis: false
  },
  {
    id: 'ex_deadlift',
    name: 'Deadlift',
    description: 'Full body posterior chain builder for back, glutes, and hamstrings strength.',
    primaryMuscles: ['back', 'hamstrings'],
    secondaryMuscles: ['glutes', 'core'],
    equipment: ['barbell'],
    difficulty: 'advanced',
    category: 'strength',
    instructions: [
      'Stand over bar with feet hip-width apart.',
      'Hinge at hips, grip bar firmly, and pull slack out.',
      'Drive through floor keeping bar close to shins.'
    ],
    commonMistakes: ['Rounding lumbar spine'],
    safetyNotes: ['Brace core heavily throughout pull.'],
    supportedFormAnalysis: true
  },
  {
    id: 'ex_squat',
    name: 'Squat',
    description: 'King of lower body exercises targeting quad, glute, and core strength.',
    primaryMuscles: ['quadriceps', 'glutes'],
    secondaryMuscles: ['hamstrings', 'core'],
    equipment: ['barbell'],
    difficulty: 'intermediate',
    category: 'strength',
    instructions: [
      'Set bar on upper traps, feet shoulder-width.',
      'Squat down until thighs break parallel.',
      'Drive up through mid-foot.'
    ],
    commonMistakes: ['Knees caving inward (valgus)'],
    safetyNotes: ['Set safety pins at appropriate height.'],
    supportedFormAnalysis: true
  },
  {
    id: 'ex_cable_crossover',
    name: 'Cable Crossover',
    description: 'Constant tension cable chest isolation for inner chest definition.',
    primaryMuscles: ['chest'],
    secondaryMuscles: ['shoulders'],
    equipment: ['cable_machine'],
    difficulty: 'intermediate',
    category: 'hypertrophy',
    instructions: ['Bring cable handles together in front of chest.'],
    commonMistakes: ['Bending elbows excessively'],
    safetyNotes: ['Maintain slight bend in elbows.'],
    supportedFormAnalysis: false
  },
  {
    id: 'ex_landmine_press',
    name: 'Landmine Press',
    description: 'Angled overhead pressing for shoulder health and core stability.',
    primaryMuscles: ['shoulders'],
    secondaryMuscles: ['triceps', 'core'],
    equipment: ['barbell'],
    difficulty: 'intermediate',
    category: 'hypertrophy',
    instructions: ['Press landmine bar upward at an angle.'],
    commonMistakes: ['Leaning back excessively'],
    safetyNotes: ['Keep core braced.'],
    supportedFormAnalysis: false
  },
  {
    id: 'ex_bulgarian_squat',
    name: 'Bulgarian Split Squat',
    description: 'Unilateral leg strength builder targeting quads, glutes, and balance.',
    primaryMuscles: ['quadriceps', 'glutes'],
    secondaryMuscles: ['hamstrings'],
    equipment: ['dumbbells'],
    difficulty: 'intermediate',
    category: 'hypertrophy',
    instructions: ['Elevate rear foot on bench and lunge downward.'],
    commonMistakes: ['Front heel coming off ground'],
    safetyNotes: ['Maintain vertical torso angle.'],
    supportedFormAnalysis: false
  },
  {
    id: 'ex_face_pull',
    name: 'Face Pull',
    description: 'Postural correction isolation for rear delts and rotators.',
    primaryMuscles: ['back', 'shoulders'],
    secondaryMuscles: ['biceps'],
    equipment: ['cable_machine'],
    difficulty: 'intermediate',
    category: 'hypertrophy',
    instructions: ['Pull rope attachment toward nose, splitting hands.'],
    commonMistakes: ['Using momentum'],
    safetyNotes: ['Keep weight manageable for clean contraction.'],
    supportedFormAnalysis: false
  }
]

export const mockWorkouts: Workout[] = [
  {
    id: 'wkt_upper_push',
    title: 'Upper Body Push',
    description: 'Chest, Shoulders & Triceps',
    targetEnvironment: 'gym',
    estimatedDurationMinutes: 45,
    difficulty: 'intermediate',
    targetMuscles: ['chest', 'shoulders', 'triceps'],
    exercises: [
      {
        id: 'we_1',
        exerciseId: 'ex_bench_press',
        exercise: mockExercises[0],
        sets: [
          { setNumber: 1, targetReps: 10, targetWeightKg: 60, isCompleted: false },
          { setNumber: 2, targetReps: 10, targetWeightKg: 60, isCompleted: false },
          { setNumber: 3, targetReps: 8, targetWeightKg: 65, isCompleted: false },
          { setNumber: 4, targetReps: 8, targetWeightKg: 65, isCompleted: false },
        ],
        restSecondsBetweenSets: 90,
      },
      {
        id: 'we_2',
        exerciseId: 'ex_incline_db_press',
        exercise: mockExercises[1],
        sets: [
          { setNumber: 1, targetReps: 10, targetWeightKg: 24, isCompleted: false },
          { setNumber: 2, targetReps: 10, targetWeightKg: 24, isCompleted: false },
          { setNumber: 3, targetReps: 10, targetWeightKg: 24, isCompleted: false },
        ],
        restSecondsBetweenSets: 90,
      },
    ],
  },
  {
    id: 'wkt_lower_strength',
    title: 'Lower Body Strength',
    description: 'Quads, Hamstrings & Glutes',
    targetEnvironment: 'gym',
    estimatedDurationMinutes: 50,
    difficulty: 'intermediate',
    targetMuscles: ['quadriceps', 'hamstrings', 'glutes'],
    exercises: [
      {
        id: 'we_3',
        exerciseId: 'ex_squat',
        exercise: mockExercises[3],
        sets: [
          { setNumber: 1, targetReps: 8, targetWeightKg: 80, isCompleted: false },
          { setNumber: 2, targetReps: 8, targetWeightKg: 80, isCompleted: false },
          { setNumber: 3, targetReps: 8, targetWeightKg: 85, isCompleted: false },
        ],
        restSecondsBetweenSets: 120,
      },
      {
        id: 'we_4',
        exerciseId: 'ex_deadlift',
        exercise: mockExercises[2],
        sets: [
          { setNumber: 1, targetReps: 6, targetWeightKg: 100, isCompleted: false },
          { setNumber: 2, targetReps: 6, targetWeightKg: 100, isCompleted: false },
          { setNumber: 3, targetReps: 6, targetWeightKg: 105, isCompleted: false },
        ],
        restSecondsBetweenSets: 120,
      },
    ],
  },
  {
    id: 'wkt_upper_pull',
    title: 'Upper Body Pull',
    description: 'Back, Biceps & Rear Delts',
    targetEnvironment: 'gym',
    estimatedDurationMinutes: 45,
    difficulty: 'intermediate',
    targetMuscles: ['back', 'biceps', 'shoulders'],
    exercises: [
      {
        id: 'we_5',
        exerciseId: 'ex_deadlift',
        exercise: mockExercises[2],
        sets: [
          { setNumber: 1, targetReps: 6, targetWeightKg: 100, isCompleted: false },
          { setNumber: 2, targetReps: 6, targetWeightKg: 100, isCompleted: false },
        ],
        restSecondsBetweenSets: 120,
      },
      {
        id: 'we_6',
        exerciseId: 'ex_face_pull',
        exercise: mockExercises[7],
        sets: [
          { setNumber: 1, targetReps: 12, targetWeightKg: 20, isCompleted: false },
          { setNumber: 2, targetReps: 12, targetWeightKg: 20, isCompleted: false },
        ],
        restSecondsBetweenSets: 60,
      },
    ],
  },
  {
    id: 'wkt_full_hiit',
    title: 'Full Body HIIT',
    description: 'Strength & Cardio',
    targetEnvironment: 'gym',
    estimatedDurationMinutes: 30,
    difficulty: 'advanced',
    targetMuscles: ['full_body', 'quadriceps', 'chest'],
    exercises: [
      {
        id: 'we_7',
        exerciseId: 'ex_squat',
        exercise: mockExercises[3],
        sets: [{ setNumber: 1, targetReps: 15, targetWeightKg: 50, isCompleted: false }],
        restSecondsBetweenSets: 45,
      },
    ],
  },
  {
    id: 'wkt_core_abs',
    title: 'Core & Abs',
    description: 'Core Strength & Stability',
    targetEnvironment: 'home',
    estimatedDurationMinutes: 20,
    difficulty: 'beginner',
    targetMuscles: ['core', 'abs'],
    exercises: [
      {
        id: 'we_8',
        exerciseId: 'ex_squat',
        exercise: mockExercises[3],
        sets: [{ setNumber: 1, targetReps: 15, targetWeightKg: 0, isCompleted: false }],
        restSecondsBetweenSets: 45,
      },
    ],
  },
  {
    id: 'wkt_mobility',
    title: 'Mobility & Flexibility',
    description: 'Improve Mobility & Recovery',
    targetEnvironment: 'home',
    estimatedDurationMinutes: 25,
    difficulty: 'beginner',
    targetMuscles: ['full_body'],
    exercises: [
      {
        id: 'we_9',
        exerciseId: 'ex_squat',
        exercise: mockExercises[3],
        sets: [{ setNumber: 1, targetReps: 10, targetWeightKg: 0, isCompleted: false }],
        restSecondsBetweenSets: 60,
      },
    ],
  },
]

