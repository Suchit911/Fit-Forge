/**
 * Active Program & Mesocycle Lifecycle Hooks (Phase 9C.5.1).
 *
 * Strictly Read/Session/Lifecycle oriented:
 * - Reads authoritative active program document
 * - Reads authoritative effective prescription for week/day
 * - Reads authoritative program versions and adaptation audit history
 * - Provides lifecycle mutations: startProgram, syncSession, abandonProgram
 * - Enforces targeted TanStack Query cache invalidations
 *
 * Strict Invariant:
 * Does NOT expose adaptation application as a user-facing frontend mutation.
 */

import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query'
import { programService } from '../services/programService.ts'
import type {
  ProgramResponse,
  ProgramStartRequest,
  ProgramSyncSessionRequest,
  ProgramAbandonRequest,
  EffectivePrescriptionResponse,
  ProgramVersionsResponse,
} from '../types/program.ts'

// ============================================================================
// Deterministic Query Keys
// ============================================================================

export const ACTIVE_PROGRAM_QUERY_KEY = ['activeProgram'] as const
export const ACTIVE_PROGRAM_PRESCRIPTION_BASE_KEY = ['activeProgramPrescription'] as const
export const PROGRAM_VERSIONS_QUERY_KEY = ['programVersions'] as const

export const effectivePrescriptionQueryKey = (week: number, day: number) =>
  [...ACTIVE_PROGRAM_PRESCRIPTION_BASE_KEY, week, day] as const

// ============================================================================
// Lifecycle Mutation Hooks
// ============================================================================

/**
 * Mutation hook to start an active workout program from a generated plan snapshot.
 */
export function useStartProgram() {
  const queryClient = useQueryClient()

  return useMutation<ProgramResponse, Error, ProgramStartRequest>({
    mutationFn: (req: ProgramStartRequest) => programService.startProgram(req),
    onSuccess: (newProgram) => {
      queryClient.setQueryData(ACTIVE_PROGRAM_QUERY_KEY, newProgram)
      queryClient.invalidateQueries({ queryKey: ACTIVE_PROGRAM_QUERY_KEY })
      queryClient.invalidateQueries({ queryKey: ACTIVE_PROGRAM_PRESCRIPTION_BASE_KEY })
      queryClient.invalidateQueries({ queryKey: PROGRAM_VERSIONS_QUERY_KEY })
    },
  })
}

/**
 * Mutation hook to synchronize a completed workout session with the active program.
 * Triggers targeted invalidation across program, prescription, signals, and progress caches.
 */
export function useSyncProgramSession() {
  const queryClient = useQueryClient()

  return useMutation<ProgramResponse, Error, ProgramSyncSessionRequest>({
    mutationFn: (req: ProgramSyncSessionRequest) => programService.syncSession(req),
    onSuccess: (updatedProgram) => {
      queryClient.setQueryData(ACTIVE_PROGRAM_QUERY_KEY, updatedProgram)
      queryClient.invalidateQueries({ queryKey: ACTIVE_PROGRAM_QUERY_KEY })
      queryClient.invalidateQueries({ queryKey: ACTIVE_PROGRAM_PRESCRIPTION_BASE_KEY })
      queryClient.invalidateQueries({ queryKey: ['personalizationSignals'] })
      queryClient.invalidateQueries({ queryKey: ['progressSummary'] })
      queryClient.invalidateQueries({ queryKey: ['workoutHistory'] })
    },
  })
}

/**
 * Mutation hook to abandon the active program while safely preserving workout history.
 */
export function useAbandonProgram() {
  const queryClient = useQueryClient()

  return useMutation<ProgramResponse, Error, ProgramAbandonRequest | undefined>({
    mutationFn: (req?: ProgramAbandonRequest) => programService.abandonActiveProgram(req),
    onSuccess: () => {
      queryClient.setQueryData(ACTIVE_PROGRAM_QUERY_KEY, null)
      queryClient.invalidateQueries({ queryKey: ACTIVE_PROGRAM_QUERY_KEY })
      queryClient.removeQueries({ queryKey: ACTIVE_PROGRAM_PRESCRIPTION_BASE_KEY })
      queryClient.removeQueries({ queryKey: PROGRAM_VERSIONS_QUERY_KEY })
    },
  })
}

// ============================================================================
// Read Query Hooks
// ============================================================================

/**
 * Primary hook to query the authenticated user's active workout program.
 * Also exposes convenience lifecycle mutation delegates.
 */
export function useActiveProgram() {
  const programQuery = useQuery<ProgramResponse | null>({
    queryKey: ACTIVE_PROGRAM_QUERY_KEY,
    queryFn: () => programService.getActiveProgram(),
    staleTime: 1000 * 60, // 60 seconds
  })

  const startMutation = useStartProgram()
  const syncMutation = useSyncProgramSession()
  const abandonMutation = useAbandonProgram()

  return {
    program: programQuery.data ?? null,
    hasActiveProgram: !!programQuery.data,
    isLoading: programQuery.isLoading,
    isError: programQuery.isError,
    error: programQuery.error,
    refetch: programQuery.refetch,

    startProgram: startMutation.mutateAsync,
    isStarting: startMutation.isPending,
    startError: startMutation.error,

    syncSession: syncMutation.mutateAsync,
    isSyncing: syncMutation.isPending,
    syncError: syncMutation.error,

    abandonProgram: abandonMutation.mutateAsync,
    isAbandoning: abandonMutation.isPending,
    abandonError: abandonMutation.error,
  }
}

/**
 * Query hook for the authoritative effective prescription for a specified week and day.
 * Single source of truth for program workouts (Phase 9C.5).
 */
export function useEffectivePrescription(
  week: number,
  day: number,
  options?: { enabled?: boolean }
) {
  const isEnabled = options?.enabled !== undefined ? options.enabled : week >= 1 && day >= 1

  const prescriptionQuery = useQuery<EffectivePrescriptionResponse>({
    queryKey: effectivePrescriptionQueryKey(week, day),
    queryFn: () => programService.getEffectivePrescription(week, day),
    staleTime: 1000 * 60 * 5, // 5 minutes
    enabled: isEnabled,
  })

  return {
    prescription: prescriptionQuery.data ?? null,
    isLoading: prescriptionQuery.isLoading,
    isError: prescriptionQuery.isError,
    error: prescriptionQuery.error,
    refetch: prescriptionQuery.refetch,
  }
}

/**
 * Query hook for active program versioning and adaptation audit history.
 */
export function useProgramVersions(options?: { enabled?: boolean }) {
  const versionsQuery = useQuery<ProgramVersionsResponse>({
    queryKey: PROGRAM_VERSIONS_QUERY_KEY,
    queryFn: () => programService.getProgramVersions(),
    staleTime: 1000 * 60 * 5, // 5 minutes
    enabled: options?.enabled ?? true,
  })

  return {
    versions: versionsQuery.data ?? null,
    isLoading: versionsQuery.isLoading,
    isError: versionsQuery.isError,
    error: versionsQuery.error,
    refetch: versionsQuery.refetch,
  }
}
