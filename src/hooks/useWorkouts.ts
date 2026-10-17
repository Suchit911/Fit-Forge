import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query'
import { workoutService, type WorkoutSessionData } from '../services'

export function useWorkouts() {
  const workoutsQuery = useQuery({
    queryKey: ['workouts'],
    queryFn: () => workoutService.getWorkouts(),
  })

  const todayWorkoutQuery = useQuery({
    queryKey: ['todayWorkout'],
    queryFn: () => workoutService.getTodayWorkout(),
  })

  return {
    workouts: workoutsQuery.data || [],
    isLoading: workoutsQuery.isLoading,
    isError: workoutsQuery.isError,
    error: workoutsQuery.error,
    todayWorkout: todayWorkoutQuery.data,
    isTodayLoading: todayWorkoutQuery.isLoading,
    isTodayError: todayWorkoutQuery.isError,
    refetchWorkouts: workoutsQuery.refetch,
    refetchTodayWorkout: todayWorkoutQuery.refetch,
  }
}

export function useWorkoutDetail(id: string) {
  const queryClient = useQueryClient()

  const workoutQuery = useQuery({
    queryKey: ['workout', id],
    queryFn: () => workoutService.getWorkoutById(id),
    enabled: !!id,
  })

  const logSessionMutation = useMutation({
    mutationFn: ({ durationSeconds, completedSetsCount }: { durationSeconds: number; completedSetsCount: number }) =>
      workoutService.logWorkoutSession(id, durationSeconds, completedSetsCount),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['workouts'] })
      queryClient.invalidateQueries({ queryKey: ['workoutHistory'] })
      queryClient.invalidateQueries({ queryKey: ['progressSummary'] })
    },
  })

  return {
    workout: workoutQuery.data,
    isLoading: workoutQuery.isLoading,
    isError: workoutQuery.isError,
    error: workoutQuery.error,
    refetch: workoutQuery.refetch,
    logSession: logSessionMutation.mutateAsync,
    isLogging: logSessionMutation.isPending,
    logError: logSessionMutation.error,
  }
}

export function useActiveWorkout(workoutId?: string) {
  const queryClient = useQueryClient()

  const activeSessionQuery = useQuery({
    queryKey: ['activeSession'],
    queryFn: () => workoutService.getActiveSession(),
  })

  const startSessionMutation = useMutation({
    mutationFn: ({
      workoutId: wid,
      notes,
      workoutTitle,
      totalSetsCount,
      programId,
      planId,
      weekNumber,
      dayNumber,
    }: {
      workoutId: string
      notes?: string
      workoutTitle?: string
      totalSetsCount?: number
      programId?: string
      planId?: string
      weekNumber?: number
      dayNumber?: number
    }) =>
      workoutService.startWorkoutSession(
        wid,
        notes,
        workoutTitle,
        totalSetsCount,
        programId,
        planId,
        weekNumber,
        dayNumber
      ),
    onSuccess: (session) => {
      queryClient.setQueryData(['activeSession'], session)
      queryClient.invalidateQueries({ queryKey: ['activeSession'] })
    },
  })

  const updateProgressMutation = useMutation({
    mutationFn: ({
      sessionId,
      updates,
    }: {
      sessionId: string
      updates: Parameters<typeof workoutService.updateWorkoutSession>[1]
    }) => workoutService.updateWorkoutSession(sessionId, updates),
    onSuccess: (session) => {
      queryClient.setQueryData(['activeSession'], session)
    },
  })

  const completeSessionMutation = useMutation({
    mutationFn: ({
      sessionId,
      durationSeconds,
      notes,
    }: {
      sessionId: string
      durationSeconds: number
      notes?: string
    }) => workoutService.completeWorkoutSession(sessionId, durationSeconds, notes),
    onSuccess: () => {
      queryClient.setQueryData(['activeSession'], null)
      queryClient.invalidateQueries({ queryKey: ['activeSession'] })
      queryClient.invalidateQueries({ queryKey: ['workoutHistory'] })
      queryClient.invalidateQueries({ queryKey: ['progressSummary'] })
      queryClient.invalidateQueries({ queryKey: ['achievementsDashboard'] })
      queryClient.invalidateQueries({ queryKey: ['notificationsData'] })
      queryClient.invalidateQueries({ queryKey: ['notificationsUnreadCount'] })
    },
  })

  return {
    activeSession: activeSessionQuery.data as WorkoutSessionData | null | undefined,
    isLoadingActive: activeSessionQuery.isLoading,
    startSession: (
      idToStart?: string,
      notes?: string,
      workoutTitle?: string,
      totalSetsCount?: number,
      programId?: string,
      planId?: string,
      weekNumber?: number,
      dayNumber?: number
    ) => {
      const targetId = idToStart || workoutId
      if (!targetId) {
        throw new Error('Workout ID is required to start a workout session')
      }
      return startSessionMutation.mutateAsync({
        workoutId: targetId,
        notes,
        workoutTitle,
        totalSetsCount,
        programId,
        planId,
        weekNumber,
        dayNumber,
      })
    },
    isStarting: startSessionMutation.isPending,
    updateProgress: updateProgressMutation.mutateAsync,
    isUpdating: updateProgressMutation.isPending,
    completeSession: completeSessionMutation.mutateAsync,
    isCompleting: completeSessionMutation.isPending,
    refetchActiveSession: activeSessionQuery.refetch,
  }
}

export function useWorkoutHistory(limit = 20) {
  const historyQuery = useQuery({
    queryKey: ['workoutHistory', limit],
    queryFn: () => workoutService.getWorkoutHistory(limit),
  })

  return {
    history: historyQuery.data || [],
    isLoading: historyQuery.isLoading,
    isError: historyQuery.isError,
    error: historyQuery.error,
    refetch: historyQuery.refetch,
  }
}

