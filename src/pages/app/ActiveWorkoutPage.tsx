import React, { useState, useEffect, useRef } from 'react'
import { useParams, useNavigate, useLocation } from 'react-router-dom'
import { useQueryClient } from '@tanstack/react-query'
import { useWorkoutDetail, useActiveWorkout } from '../../hooks'
import { ActiveWorkoutHeader } from '../../components/workout/ActiveWorkoutHeader'
import { ActiveExerciseCard } from '../../components/workout/ActiveExerciseCard'
import { SetTrackerTable } from '../../components/workout/SetTrackerTable'
import { UpNextSection, type UpNextExerciseItem } from '../../components/workout/UpNextSection'
import { WorkoutProgressPanel } from '../../components/workout/WorkoutProgressPanel'
import { HeartRateCard } from '../../components/workout/HeartRateCard'
import { CaloriesBurnedCard } from '../../components/workout/CaloriesBurnedCard'
import { MuscleFocusCard } from '../../components/workout/MuscleFocusCard'
import { NowPlayingCard } from '../../components/workout/NowPlayingCard'
import { EndWorkoutModal } from '../../components/workout/EndWorkoutModal'
import { Skeleton, ErrorState, EmptyState } from '../../components/ui'
import {
  workoutPlanExecutionService,
  type GeneratedWorkoutExecutionContext,
} from '../../services/workoutPlanExecutionService'
import { programService } from '../../services/programService'
import {
  ACTIVE_PROGRAM_QUERY_KEY,
  ACTIVE_PROGRAM_PRESCRIPTION_BASE_KEY,
} from '../../hooks/useActiveProgram'
import type { PlannedExercise, PlannedSet } from '../../types/workoutPlan'

export const ActiveWorkoutPage: React.FC = () => {
  const { id } = useParams<{ id: string }>()
  const navigate = useNavigate()
  const location = useLocation()
  const queryClient = useQueryClient()

  // 1. Detect Generated Plan Execution Context (from location state or in-memory service)
  const locationStateContext = location.state as GeneratedWorkoutExecutionContext | undefined
  const inMemoryContext = workoutPlanExecutionService.getActiveExecutionContext()
  const generatedContext = locationStateContext || inMemoryContext

  const contextValidation = generatedContext
    ? workoutPlanExecutionService.validateExecutionContext(generatedContext)
    : { isValid: false, error: 'No execution context provided' }

  const hasValidGeneratedExercises = !!(
    generatedContext &&
    contextValidation.isValid &&
    generatedContext.day &&
    Array.isArray(generatedContext.day.exercises) &&
    generatedContext.day.exercises.length > 0
  )

  // Generated mode is strictly active if id is 'generated' (or missing with context) AND has valid generated day
  const isGeneratedMode = (id === 'generated' || (!id && hasValidGeneratedExercises)) && hasValidGeneratedExercises

  // Strict route check: if id === 'generated' but context was lost/missing/invalid, NEVER fall back to static
  const isMissingGeneratedContext =
    (id === 'generated' && !hasValidGeneratedExercises) || (!!generatedContext && !contextValidation.isValid)

  const workoutId = isGeneratedMode ? 'generated' : (id || '')

  // Query for static workouts (only enabled if NOT generated mode)
  const { workout, isLoading: isStaticLoading, isError: isStaticError, refetch: refetchWorkout } = useWorkoutDetail(
    isGeneratedMode || isMissingGeneratedContext ? '' : workoutId
  )


  // Active workout session hook
  const {
    activeSession,
    startSession,
    updateProgress,
    completeSession,
    isUpdating,
  } = useActiveWorkout(workoutId)

  // Component UI State
  const [isEndModalOpen, setIsEndModalOpen] = useState(false)
  const [activeExIndex, setActiveExIndex] = useState<number>(0)
  const [isCompleting, setIsCompleting] = useState(false)
  const isCompletingRef = useRef(false)
  const sessionStartTimeRef = useRef<number>(Date.now())
  const [completionError, setCompletionError] = useState<string | null>(null)
  const [setUpdateError, setSetUpdateError] = useState<string | null>(null)

  // Align start timestamp with authoritative backend session startedAt if available
  useEffect(() => {
    if (activeSession?.startedAt) {
      const startedEpoch = new Date(activeSession.startedAt).getTime()
      if (!isNaN(startedEpoch) && startedEpoch > 0 && startedEpoch <= Date.now()) {
        sessionStartTimeRef.current = startedEpoch
      }
    }
  }, [activeSession?.startedAt])
  const [recordedSetsByEx, setRecordedSetsByEx] = useState<
    Record<
      string,
      Array<{
        setNumber: number
        actualReps: number
        actualWeightKg: number
        rpe?: number
        isCompleted: boolean
      }>
    >
  >({})

  // Total planned sets calculation
  const generatedExercises: PlannedExercise[] = isGeneratedMode && generatedContext
    ? generatedContext.day.exercises
    : []

  const totalPlannedSets = isGeneratedMode
    ? generatedExercises.reduce((acc, ex) => acc + ex.total_sets, 0)
    : workout?.exercises?.reduce((acc, we) => acc + we.sets.length, 0) || 0

  const totalCompletedSets = Object.values(recordedSetsByEx).reduce(
    (acc, setList) => acc + setList.filter((s) => s.isCompleted).length,
    0
  )

  // Safeguard: start session once when entering generated mode
  const sessionStartAttemptedRef = useRef(false)
  useEffect(() => {
    if (isGeneratedMode && !sessionStartAttemptedRef.current && !activeSession && generatedContext) {
      sessionStartAttemptedRef.current = true
      const targetDayNumber = generatedContext.dayNumber ?? generatedContext.day.day_number
      const notes = `Generated Plan: ${generatedContext.planTitle} | Week ${generatedContext.weekNumber} (${generatedContext.phaseLabel}) | Day ${targetDayNumber}: ${generatedContext.day.day_label}`
      const workoutTitle = `${generatedContext.day.day_label} Routine`
      startSession(
        'generated',
        notes,
        workoutTitle,
        totalPlannedSets,
        generatedContext.programId,
        generatedContext.planId,
        generatedContext.weekNumber,
        targetDayNumber
      ).catch((err) => {
        console.warn('Session start deferred or offline:', err)
      })
    }
  }, [isGeneratedMode, activeSession, generatedContext, startSession, totalPlannedSets])

  // Safeguard: start session for standard catalog workout if not already started
  const staticSessionStartRef = useRef(false)
  useEffect(() => {
    if (!isGeneratedMode && !isMissingGeneratedContext && workout && !staticSessionStartRef.current && !activeSession) {
      staticSessionStartRef.current = true
      startSession(workout.id, `Catalog workout: ${workout.title}`).catch((err) => {
        console.warn('Static session start deferred or offline:', err)
      })
    }
  }, [isGeneratedMode, isMissingGeneratedContext, workout, activeSession, startSession])

  // 1. Missing Generated Plan Context (Direct URL access or page reload without context)
  if (isMissingGeneratedContext) {
    return (
      <EmptyState
        title="No Active Generated Plan"
        description="Your generated workout session was not found or was cleared upon page reload. Please return to Workouts to view or regenerate your plan."
        actionLabel="Back to Workouts"
        onAction={() => navigate('/workouts')}
      />
    )
  }

  // 2. Static Mode Loading & Error States
  if (!isGeneratedMode) {
    if (!workoutId) {
      return (
        <EmptyState
          title="Workout Not Found"
          description="The requested workout ID does not exist."
          actionLabel="Back to Workouts"
          onAction={() => navigate('/workouts')}
        />
      )
    }

    if (isStaticLoading) {
      return (
        <div className="space-y-6 text-left">
          <Skeleton className="h-6 w-48" />
          <Skeleton className="h-96 w-full" />
          <Skeleton className="h-48 w-full" />
        </div>
      )
    }

    if (isStaticError) {
      return (
        <ErrorState
          title="Active Workout Error"
          message="Could not load active workout data. Please check your connection and try again."
          onRetry={refetchWorkout}
        />
      )
    }


    if (!workout) {
      return (
        <EmptyState
          title="Workout Not Found"
          description="The requested workout for active session does not exist."
          actionLabel="Back to Workouts"
          onAction={() => navigate('/workouts')}
        />
      )
    }
  }

  // =========================================================================
  // DUAL-MODE EXERCISE DATA RESOLUTION
  // =========================================================================

  // Current Exercise Details (Generated Mode vs Static Mode)
  const currentPlannedExercise: PlannedExercise | undefined = isGeneratedMode
    ? generatedExercises[activeExIndex] || generatedExercises[0]
    : undefined

  const currentStaticExercise = !isGeneratedMode && workout?.exercises
    ? workout.exercises[activeExIndex] || workout.exercises[0]
    : undefined

  const currentExerciseId = isGeneratedMode
    ? currentPlannedExercise?.exercise_id || ''
    : currentStaticExercise?.exerciseId || ''

  const exerciseName = isGeneratedMode
    ? currentPlannedExercise?.name || 'Exercise'
    : currentStaticExercise?.exercise?.name || 'Exercise'

  const targetMuscle = isGeneratedMode
    ? currentPlannedExercise?.primary_muscles[0] || 'Full Body'
    : currentStaticExercise?.exercise?.primaryMuscles[0] || 'Full Body'

  const totalExercisesCount = isGeneratedMode
    ? generatedExercises.length
    : workout?.exercises?.length || 0

  const setsCount = isGeneratedMode
    ? currentPlannedExercise?.total_sets || 3
    : currentStaticExercise?.sets?.length || 4

  const repRangeDisplay = isGeneratedMode
    ? currentPlannedExercise?.prescribed_sets[0]?.target_reps_min &&
      currentPlannedExercise?.prescribed_sets[0]?.target_reps_max
      ? `${currentPlannedExercise.prescribed_sets[0].target_reps_min}–${currentPlannedExercise.prescribed_sets[0].target_reps_max}`
      : `${currentPlannedExercise?.prescribed_sets[0]?.target_reps || 10}`
    : currentStaticExercise?.sets[0]?.targetReps
    ? `${currentStaticExercise.sets[0].targetReps}`
    : '8–10'

  const restSeconds = isGeneratedMode
    ? currentPlannedExercise?.prescribed_sets[0]?.rest_seconds || 90
    : currentStaticExercise?.restSecondsBetweenSets || 90

  const equipmentDisplay = isGeneratedMode
    ? currentPlannedExercise?.equipment?.join(', ') || 'bodyweight'
    : currentStaticExercise?.exercise?.equipment?.join(', ') || 'bodyweight'

  const slotRole = isGeneratedMode ? currentPlannedExercise?.slot_role : undefined
  const targetRpe = isGeneratedMode ? currentPlannedExercise?.prescribed_sets[0]?.target_rpe : undefined
  const prescriptionRationale = isGeneratedMode ? currentPlannedExercise?.prescription_rationale : undefined
  const recommendationReasons = isGeneratedMode ? currentPlannedExercise?.reasons : undefined
  const movementPattern = isGeneratedMode ? currentPlannedExercise?.movement_pattern : undefined

  // Prescribed sets for SetTrackerTable
  const tablePrescribedSets: PlannedSet[] = isGeneratedMode
    ? currentPlannedExercise?.prescribed_sets || []
    : (currentStaticExercise?.sets || []).map((s) => ({
        set_number: s.setNumber,
        target_reps: s.targetReps,
        target_reps_min: s.targetReps,
        target_reps_max: s.targetReps,
        target_rpe: s.rpe || null,
        rest_seconds: currentStaticExercise?.restSecondsBetweenSets || 90,
        notes: null,
      }))

  // Header Title & Badges
  const workoutTitle = isGeneratedMode && generatedContext
    ? `${generatedContext.day.day_label} Routine`
    : workout?.title || 'Workout'

  const planBadge = isGeneratedMode && generatedContext
    ? `${generatedContext.planTitle} • Week ${generatedContext.weekNumber}`
    : undefined

  const phaseBadge = isGeneratedMode && generatedContext ? generatedContext.phaseLabel : undefined

  // Set Recording Handler
  const handleRecordSet = async (record: {
    exerciseId: string
    setNumber: number
    actualReps: number
    actualWeightKg: number
    rpe?: number
  }) => {
    setSetUpdateError(null)

    // 1. Update local state
    setRecordedSetsByEx((prev) => {
      const existing = prev[record.exerciseId] || []
      const filtered = existing.filter((s) => s.setNumber !== record.setNumber)
      return {
        ...prev,
        [record.exerciseId]: [
          ...filtered,
          {
            setNumber: record.setNumber,
            actualReps: record.actualReps,
            actualWeightKg: record.actualWeightKg,
            rpe: record.rpe,
            isCompleted: true,
          },
        ].sort((a, b) => a.setNumber - b.setNumber),
      }
    })

    // 2. Authoritative backend PATCH update if session is active
    const curSession = activeSession
    if (curSession && curSession.id) {
      try {
        await updateProgress({
          sessionId: curSession.id,
          updates: {
            currentExerciseIndex: activeExIndex,
            currentSetIndex: record.setNumber - 1,
            recordedSet: {
              exerciseId: record.exerciseId,
              setNumber: record.setNumber,
              actualReps: record.actualReps,
              actualWeightKg: record.actualWeightKg,
              rpe: record.rpe,
            },
          },
        })
      } catch (err: any) {
        console.warn('Set update recorded locally, backend sync deferred:', err)
        setSetUpdateError('Set logged locally. Backend sync is temporarily unavailable.')
      }
    }
  }

  // Exercise Navigation
  const handlePreviousExercise = () => {
    setActiveExIndex((prev) => Math.max(0, prev - 1))
  }

  const handleNextExercise = () => {
    setActiveExIndex((prev) => Math.min(totalExercisesCount - 1, prev + 1))
  }

  const handleSelectUpcomingExercise = (targetIdx: number) => {
    if (targetIdx >= 0 && targetIdx < totalExercisesCount) {
      setActiveExIndex(targetIdx)
    }
  }

  // Upcoming exercises mapping (strictly dynamic, NO dummy fallbacks)
  const upcomingExercises: UpNextExerciseItem[] = isGeneratedMode
    ? generatedExercises
        .map((ex, idx) => ({ ex, idx }))
        .filter(({ idx }) => idx > activeExIndex)
        .map(({ ex, idx }) => ({
          num: idx + 1,
          index: idx,
          name: ex.name,
          setsReps: `${ex.total_sets} sets × ${
            ex.prescribed_sets[0]?.target_reps_min
              ? `${ex.prescribed_sets[0].target_reps_min}–${ex.prescribed_sets[0].target_reps_max}`
              : ex.prescribed_sets[0]?.target_reps || 10
          } reps`,
          rest: `${ex.prescribed_sets[0]?.rest_seconds || 90}s rest`,
          image: '/assets/workout_lower_body.jpg',
          slotRole: ex.slot_role,
          exerciseId: ex.exercise_id,
        }))
    : (workout?.exercises || [])
        .map((we, idx) => ({ we, idx }))
        .filter(({ idx }) => idx > activeExIndex)
        .map(({ we, idx }) => ({
          num: idx + 1,
          index: idx,
          name: we.exercise?.name || 'Exercise',
          setsReps: `${we.sets?.length || 4} sets × ${we.sets[0]?.targetReps || 10} reps`,
          rest: `${we.restSecondsBetweenSets || 90}s rest`,
          image: '/assets/workout_lower_body.jpg',
          exerciseId: we.exerciseId,
        }))

  // Session Completion Handler
  const handleConfirmEndWorkout = async () => {
    if (isCompletingRef.current) return
    isCompletingRef.current = true
    setIsCompleting(true)
    setCompletionError(null)
    try {
      const curSession = activeSession
      if (curSession && curSession.id) {
        const targetDayNumber = generatedContext?.dayNumber ?? generatedContext?.day.day_number
        const notes = isGeneratedMode && generatedContext
          ? `Completed: ${generatedContext.planTitle} | Week ${generatedContext.weekNumber} | Day ${targetDayNumber}: ${generatedContext.day.day_label}`
          : `Completed catalog workout: ${workout?.title || 'Workout'}`

        const durationSeconds = workoutPlanExecutionService.calculateElapsedDurationSeconds(
          sessionStartTimeRef.current,
          Date.now()
        )

        await completeSession({
          sessionId: curSession.id,
          durationSeconds,
          notes,
        })

        // Program sync handshake if this session belongs to an active program
        if (isGeneratedMode && generatedContext?.programId) {
          if (typeof targetDayNumber !== 'number' || targetDayNumber < 1) {
            throw new Error(`Cannot sync program session: invalid dayNumber (${targetDayNumber}).`)
          }
          const updatedProgram = await programService.syncSession({
            sessionId: curSession.id,
            weekNumber: generatedContext.weekNumber,
            dayNumber: targetDayNumber,
          })

          queryClient.setQueryData(ACTIVE_PROGRAM_QUERY_KEY, updatedProgram)
          await Promise.all([
            queryClient.invalidateQueries({ queryKey: ACTIVE_PROGRAM_QUERY_KEY }),
            queryClient.invalidateQueries({ queryKey: ACTIVE_PROGRAM_PRESCRIPTION_BASE_KEY }),
            queryClient.invalidateQueries({ queryKey: ['personalizationSignals'] }),
            queryClient.invalidateQueries({ queryKey: ['progressSummary'] }),
            queryClient.invalidateQueries({ queryKey: ['workoutHistory'] }),
          ])
        }
      } else if (isGeneratedMode && generatedContext?.programId) {
        throw new Error('Active workout session not found. Cannot complete or sync program.')
      }

      // Clean up ephemeral context ONLY on success
      workoutPlanExecutionService.clearActiveExecutionContext()
      setIsCompleting(false)
      isCompletingRef.current = false
      setIsEndModalOpen(false)

      if (isGeneratedMode && generatedContext?.programId) {
        navigate('/workouts?tab=program')
      } else {
        navigate('/workouts')
      }
    } catch (err: any) {
      console.error('Session completion / sync error:', err)
      setCompletionError(err?.message || 'Failed to complete workout session or sync program. Please try again.')
      setIsCompleting(false)
      isCompletingRef.current = false
      // Do not clear context or navigate away on error
    }
  }

  return (
    <div className="space-y-6 text-left pb-12">
      {/* Active Workout Header with Plan and Phase Badges */}
      <ActiveWorkoutHeader
        workoutTitle={workoutTitle}
        planBadge={planBadge}
        phaseBadge={phaseBadge}
      />

      {setUpdateError && (
        <div className="p-3 rounded-2xl bg-amber-500/10 border border-amber-500/30 text-amber-300 text-xs font-mono">
          {setUpdateError}
        </div>
      )}

      {/* Main Multi-Column Content Grid */}
      <div className="grid grid-cols-1 lg:grid-cols-12 gap-6">
        {/* Left Column (8 of 12 columns on desktop) */}
        <div className="lg:col-span-8 space-y-6">
          {/* Main Exercise & Prescription Card */}
          <ActiveExerciseCard
            currentExerciseIndex={activeExIndex + 1}
            totalExercises={totalExercisesCount}
            exerciseName={exerciseName}
            targetMuscle={targetMuscle}
            setsCount={setsCount}
            repRange={repRangeDisplay}
            restSeconds={restSeconds}
            equipment={equipmentDisplay}
            formScore={92}
            image="/assets/dashboard_push_lifter.jpg"
            slotRole={slotRole}
            targetRpe={targetRpe}
            prescriptionRationale={prescriptionRationale}
            recommendationReasons={recommendationReasons}
            movementPattern={movementPattern}
            onPreviousExercise={handlePreviousExercise}
            onNextExercise={handleNextExercise}
            hasPreviousExercise={activeExIndex > 0}
            hasNextExercise={activeExIndex < totalExercisesCount - 1}
          />

          {/* Set Tracker Table with Prescribed Sets and User Load/Reps Logging */}
          <SetTrackerTable
            exerciseId={currentExerciseId}
            prescribedSets={tablePrescribedSets}
            recordedSets={recordedSetsByEx[currentExerciseId]}
            onRecordSet={handleRecordSet}
            isRecording={isUpdating}
          />

          {/* Up Next Horizontal Section with Jump Navigation */}
          <UpNextSection
            upcomingExercises={upcomingExercises}
            onSelectExercise={handleSelectUpcomingExercise}
          />
        </div>

        {/* Right Column (4 of 12 columns on desktop) */}
        <div className="lg:col-span-4 space-y-6">
          <WorkoutProgressPanel onEndWorkoutClick={() => setIsEndModalOpen(true)} />
          <HeartRateCard />
          <CaloriesBurnedCard />
          <MuscleFocusCard />
          <NowPlayingCard />
        </div>
      </div>

      {/* End Workout Confirmation Modal */}
      <EndWorkoutModal
        isOpen={isEndModalOpen}
        onClose={() => {
          setIsEndModalOpen(false)
          setCompletionError(null)
        }}
        onConfirmEnd={handleConfirmEndWorkout}
        isCompleting={isCompleting}
        completedSetsCount={totalCompletedSets}
        totalSetsCount={totalPlannedSets}
        errorMessage={completionError}
      />
    </div>
  )
}
