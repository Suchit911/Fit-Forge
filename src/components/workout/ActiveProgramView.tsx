import React, { useState, useEffect } from 'react'
import { Dumbbell, CheckCircle2, Archive, Sparkles, PlusCircle } from 'lucide-react'
import type { ProgramResponse } from '../../types/program.ts'
import { useActiveProgram } from '../../hooks/useActiveProgram.ts'
import { EmptyState } from '../ui/EmptyState.tsx'
import { ErrorState } from '../ui/ErrorState.tsx'
import { Skeleton } from '../ui/Skeleton.tsx'
import { useToast } from '../ui/Toast.tsx'
import { workoutPlanExecutionService } from '../../services/workoutPlanExecutionService.ts'
import { ActiveProgramHeader } from './ActiveProgramHeader.tsx'
import { ProgramWeekTimeline } from './ProgramWeekTimeline.tsx'
import { TodayPrescriptionPreview } from './TodayPrescriptionPreview.tsx'
import { AdaptationHistoryModal } from './AdaptationHistoryModal.tsx'
import { AbandonProgramModal } from './AbandonProgramModal.tsx'

export interface ActiveProgramViewProps {
  program?: ProgramResponse | null
  onNavigateToGenerate?: () => void
}

export const ActiveProgramView: React.FC<ActiveProgramViewProps> = ({
  program: propProgram,
  onNavigateToGenerate,
}) => {
  const {
    program: queryProgram,
    isLoading: queryLoading,
    isError: queryIsError,
    error: queryError,
    refetch,
    abandonProgram,
    isAbandoning,
  } = useActiveProgram()
  const { showToast } = useToast()

  // Use authoritative prop if supplied, otherwise consume active program query
  const program = propProgram !== undefined ? propProgram : queryProgram
  const isLoading = propProgram === undefined && queryLoading
  const isError = propProgram === undefined && queryIsError
  const error = queryError

  // Local UI selection state (does NOT mutate backend pointers)
  const [selectedWeek, setSelectedWeek] = useState<number>(1)
  const [selectedDay, setSelectedDay] = useState<number>(1)

  // Adaptation History Modal UI state
  const [isHistoryModalOpen, setIsHistoryModalOpen] = useState<boolean>(false)

  // Abandon Program Modal UI state
  const [isAbandonModalOpen, setIsAbandonModalOpen] = useState<boolean>(false)
  const [abandonError, setAbandonError] = useState<string | null>(null)

  // Sync initial selection with authoritative backend pointers once loaded
  useEffect(() => {
    if (program) {
      setSelectedWeek(program.currentWeek || 1)
      setSelectedDay(program.currentDay || 1)
    }
  }, [program?.programId])

  // 1. Loading State
  if (isLoading) {
    return (
      <div className="space-y-6 text-left">
        {/* Header Skeleton */}
        <div className="rounded-2xl border border-slate-800 bg-slate-900/80 p-6 space-y-4">
          <Skeleton className="h-6 w-48" />
          <Skeleton className="h-8 w-80" />
          <Skeleton className="h-3 w-full rounded-full mt-4" />
        </div>
        {/* Timeline Skeleton */}
        <div className="space-y-3">
          <Skeleton className="h-5 w-40" />
          <div className="grid grid-cols-2 sm:grid-cols-4 gap-3">
            <Skeleton className="h-28 w-full rounded-2xl" />
            <Skeleton className="h-28 w-full rounded-2xl" />
            <Skeleton className="h-28 w-full rounded-2xl" />
            <Skeleton className="h-28 w-full rounded-2xl" />
          </div>
        </div>
        {/* Prescription Skeleton */}
        <Skeleton className="h-64 w-full rounded-2xl" />
      </div>
    )
  }

  // 2. API Error State
  if (isError) {
    return (
      <ErrorState
        title="Failed to Load Active Program"
        message={error?.message || 'A network error occurred while retrieving your active program.'}
        onRetry={() => refetch()}
      />
    )
  }

  // 3. No Active Program Empty State
  if (!program) {
    return (
      <EmptyState
        title="No Active Program"
        description="Start a generated workout plan to begin tracking your program. You will be able to follow your multi-week mesocycle, monitor progression, and receive adaptive prescriptions."
        actionLabel="Generate Workout Plan"
        icon={<Dumbbell className="h-10 w-10 text-emerald-400" />}
        onAction={onNavigateToGenerate}
      />
    )
  }

  // 4. Find metadata for currently selected day in planSnapshot
  const activeWeekData =
    (program.planSnapshot?.weeks || []).find(
      (w: any) => (w.week_number ?? w.weekNumber) === selectedWeek
    ) || program.planSnapshot?.weeks?.[0]

  const activeDayData =
    (activeWeekData?.days || []).find(
      (d: any) => (d.day_number ?? d.dayNumber) === selectedDay
    ) || activeWeekData?.days?.[0]

  const isSelectedRestDay = activeDayData?.is_rest_day ?? activeDayData?.isRestDay ?? false
  const selectedDayLabel = activeDayData?.day_label ?? activeDayData?.dayLabel ?? `Day ${selectedDay}`
  const isToday =
    selectedWeek === (program.currentWeek || 1) &&
    selectedDay === (program.currentDay || 1) &&
    program.status === 'active'

  const handleSelectWeek = (weekNumber: number) => {
    setSelectedWeek(weekNumber)
    // Find first day of selected week to preview
    const targetWeek = (program.planSnapshot?.weeks || []).find(
      (w: any) => (w.week_number ?? w.weekNumber) === weekNumber
    )
    if (targetWeek && targetWeek.days && targetWeek.days.length > 0) {
      const firstDay = targetWeek.days[0]
      setSelectedDay(firstDay.day_number ?? firstDay.dayNumber ?? 1)
    } else {
      setSelectedDay(1)
    }
  }

  const handleConfirmAbandon = async () => {
    setAbandonError(null)
    try {
      await abandonProgram()
      // Clear stale execution context only after backend confirms success
      workoutPlanExecutionService.clearActiveExecutionContext()
      showToast('Active program abandoned. Your workout history remains safely preserved.', 'info')
      setIsAbandonModalOpen(false)
    } catch (err: any) {
      const errMsg = err?.message || 'Failed to abandon active program.'
      setAbandonError(errMsg)
      showToast(errMsg, 'error')
    }
  }

  const isCompleted = program.status === 'completed'
  const isAbandoned = program.status === 'abandoned'

  return (
    <div className="space-y-6 text-left pb-8">
      {/* Completed Program Notification Banner */}
      {isCompleted && (
        <div
          role="region"
          aria-label="Mesocycle Completed Notice"
          className="rounded-2xl border border-emerald-500/40 bg-emerald-500/10 p-5 flex flex-col sm:flex-row sm:items-center justify-between gap-4"
        >
          <div className="flex items-start gap-3 min-w-0">
            <div className="p-2.5 rounded-xl bg-emerald-500/20 text-emerald-400 shrink-0">
              <CheckCircle2 className="h-6 w-6" aria-hidden="true" />
            </div>
            <div className="min-w-0">
              <h3 className="text-base font-black text-emerald-200">
                Mesocycle Completed! 🎉
              </h3>
              <p className="text-xs text-emerald-300/80 mt-1 max-w-xl leading-relaxed break-words">
                You have completed all {program.totalPlannedWorkouts || program.completedWorkouts?.length || 0} planned workouts for this program. You can review your completed progression below or generate a new plan for your next training block.
              </p>
            </div>
          </div>
          {onNavigateToGenerate && (
            <button
              type="button"
              id="generate-next-program-btn"
              onClick={onNavigateToGenerate}
              className="min-h-[44px] inline-flex items-center justify-center gap-2 rounded-xl bg-emerald-500 hover:bg-emerald-400 text-slate-950 px-4 py-2.5 text-xs font-bold shrink-0 shadow-lg shadow-emerald-500/20 transition-all cursor-pointer focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-emerald-400 focus-visible:ring-offset-2 focus-visible:ring-offset-slate-900"
            >
              <Sparkles className="h-4 w-4" aria-hidden="true" />
              <span>Generate Next Program</span>
            </button>
          )}
        </div>
      )}

      {/* Abandoned Historical Program Notification Banner */}
      {isAbandoned && (
        <div
          role="region"
          aria-label="Historical Program Notice"
          className="rounded-2xl border border-slate-700 bg-slate-800/60 p-5 flex flex-col sm:flex-row sm:items-center justify-between gap-4"
        >
          <div className="flex items-start gap-3 min-w-0">
            <div className="p-2.5 rounded-xl bg-slate-700 text-slate-400 shrink-0">
              <Archive className="h-6 w-6" aria-hidden="true" />
            </div>
            <div className="min-w-0">
              <h3 className="text-base font-bold text-slate-200">
                Historical Program (Abandoned)
              </h3>
              <p className="text-xs text-slate-400 mt-1 max-w-xl leading-relaxed break-words">
                This program was abandoned on {program.abandonedAt ? new Date(program.abandonedAt).toLocaleDateString() : 'previously'}. All completed workouts and adaptation records remain securely preserved in your history.
              </p>
            </div>
          </div>
          {onNavigateToGenerate && (
            <button
              type="button"
              id="generate-workout-plan-btn"
              onClick={onNavigateToGenerate}
              className="min-h-[44px] inline-flex items-center justify-center gap-2 rounded-xl bg-slate-700 hover:bg-slate-600 text-slate-200 border border-slate-600 px-4 py-2.5 text-xs font-bold shrink-0 transition-all cursor-pointer focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-slate-400 focus-visible:ring-offset-2 focus-visible:ring-offset-slate-900"
            >
              <PlusCircle className="h-4 w-4" aria-hidden="true" />
              <span>Generate Workout Plan</span>
            </button>
          )}
        </div>
      )}

      {/* Authoritative Program Header Card */}
      <ActiveProgramHeader
        program={program}
        onOpenHistory={() => setIsHistoryModalOpen(true)}
        onAbandon={
          program.status === 'active'
            ? () => {
              setAbandonError(null)
              setIsAbandonModalOpen(true)
            }
            : undefined
        }
      />

      {/* Week Timeline and Day Cards Selector */}
      <ProgramWeekTimeline
        program={program}
        selectedWeek={selectedWeek}
        selectedDay={selectedDay}
        onSelectWeek={handleSelectWeek}
        onSelectDay={(dayNum) => setSelectedDay(dayNum)}
      />

      {/* Authoritative Effective Prescription Preview for Selected Week / Day */}
      <TodayPrescriptionPreview
        week={selectedWeek}
        day={selectedDay}
        isToday={isToday}
        isRestDay={isSelectedRestDay}
        dayLabel={selectedDayLabel}
        program={program}
        onOpenHistory={() => setIsHistoryModalOpen(true)}
      />

      {/* Authoritative Adaptation History Modal */}
      <AdaptationHistoryModal
        isOpen={isHistoryModalOpen}
        onClose={() => setIsHistoryModalOpen(false)}
        program={program}
      />

      {/* Abandon Program Confirmation Modal */}
      <AbandonProgramModal
        isOpen={isAbandonModalOpen}
        onClose={() => {
          if (!isAbandoning) setIsAbandonModalOpen(false)
        }}
        onConfirmAbandon={handleConfirmAbandon}
        isAbandoning={isAbandoning}
        errorMessage={abandonError}
      />
    </div>
  )
}
