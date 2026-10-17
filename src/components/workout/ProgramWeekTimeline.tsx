import React from 'react'
import { Calendar, ChevronRight } from 'lucide-react'
import type { ProgramResponse } from '../../types/program.ts'
import { ProgramDayCard } from './ProgramDayCard.tsx'
import {
  deriveProgramDayState,
  getCompletedDaysCountForWeek,
} from '../../utils/activeProgramOverview.ts'

export interface ProgramWeekTimelineProps {
  program: ProgramResponse
  selectedWeek: number
  selectedDay: number
  onSelectWeek: (weekNumber: number) => void
  onSelectDay: (dayNumber: number) => void
}

export const ProgramWeekTimeline: React.FC<ProgramWeekTimelineProps> = ({
  program,
  selectedWeek,
  selectedDay,
  onSelectWeek,
  onSelectDay,
}) => {
  const totalWeeks = program.totalWeeks || 1
  const currentWeek = program.currentWeek || 1
  const completedWorkouts = program.completedWorkouts || []

  // Create array of week numbers [1, 2, ..., totalWeeks]
  const weekNumbers = Array.from({ length: totalWeeks }, (_, i) => i + 1)

  // Extract planned days for the currently selected week
  const weeksData = program.planSnapshot?.weeks || []
  const activeWeekData =
    weeksData.find((w) => (w.week_number ?? w.weekNumber) === selectedWeek) || weeksData[0]

  const phaseLabel = activeWeekData?.phase_label ?? activeWeekData?.phaseLabel ?? ''
  const days = activeWeekData?.days || []

  const handleWeekKeyDown = (e: React.KeyboardEvent, weekNum: number) => {
    const currentIndex = weekNumbers.indexOf(weekNum)
    let targetIndex = -1

    if (e.key === 'ArrowRight' || e.key === 'ArrowDown') {
      e.preventDefault()
      targetIndex = (currentIndex + 1) % weekNumbers.length
    } else if (e.key === 'ArrowLeft' || e.key === 'ArrowUp') {
      e.preventDefault()
      targetIndex = (currentIndex - 1 + weekNumbers.length) % weekNumbers.length
    } else if (e.key === 'Home') {
      e.preventDefault()
      targetIndex = 0
    } else if (e.key === 'End') {
      e.preventDefault()
      targetIndex = weekNumbers.length - 1
    }

    if (targetIndex !== -1) {
      const targetWeek = weekNumbers[targetIndex]
      onSelectWeek(targetWeek)
      const el = document.getElementById(`week-tab-${targetWeek}`)
      el?.focus()
    }
  }

  return (
    <div className="space-y-6 text-left">
      {/* Week Navigation Pills Bar */}
      <div className="space-y-2">
        <div className="flex items-center justify-between">
          <label className="text-xs font-bold uppercase tracking-wider text-slate-400 flex items-center gap-1.5">
            <Calendar className="h-3.5 w-3.5 text-emerald-400" aria-hidden="true" />
            <span>Select Program Week ({totalWeeks} Weeks Total)</span>
          </label>
          <span className="text-[11px] font-mono text-slate-400">
            Current: <strong className="text-emerald-400 font-bold">Week {currentWeek}</strong>
          </span>
        </div>

        <div
          role="tablist"
          aria-label="Program weeks"
          className="flex items-center gap-2.5 overflow-x-auto pb-1.5 max-w-full"
        >
          {weekNumbers.map((wNum) => {
            const isSelected = selectedWeek === wNum
            const isCurrent = currentWeek === wNum

            // Check if planned workouts in this week are completed
            const weekCompletedCount = getCompletedDaysCountForWeek(completedWorkouts, wNum)

            return (
              <button
                key={wNum}
                role="tab"
                id={`week-tab-${wNum}`}
                aria-selected={isSelected}
                aria-controls="week-schedule-panel"
                tabIndex={isSelected ? 0 : -1}
                type="button"
                onClick={() => onSelectWeek(wNum)}
                onKeyDown={(e) => handleWeekKeyDown(e, wNum)}
                className={`px-4 py-2.5 rounded-xl border text-left transition-all cursor-pointer shrink-0 min-h-[44px] min-w-[44px] focus:outline-none focus-visible:ring-2 focus-visible:ring-emerald-500 focus-visible:ring-offset-2 focus-visible:ring-offset-slate-900 ${
                  isSelected
                    ? 'border-emerald-500 bg-emerald-500/10 text-slate-100 shadow-md shadow-emerald-500/10 font-bold'
                    : isCurrent
                    ? 'border-emerald-500/40 bg-slate-900/90 text-slate-300 hover:border-emerald-500/60'
                    : 'border-slate-800 bg-slate-900/60 text-slate-400 hover:border-slate-700 hover:text-slate-200'
                }`}
              >
                <div className="flex items-center gap-2">
                  <span className={`text-xs ${isSelected ? 'text-emerald-300 font-bold' : 'text-slate-300'}`}>
                    Week {wNum}
                  </span>
                  {isCurrent && (
                    <span className="h-1.5 w-1.5 rounded-full bg-emerald-400 shrink-0" title="Active week" aria-hidden="true" />
                  )}
                </div>
                <span className="block text-[10px] font-mono text-slate-400 mt-0.5">
                  {weekCompletedCount > 0 ? `${weekCompletedCount} done` : 'Pending'}
                </span>
              </button>
            )
          })}
        </div>
      </div>

      {/* Selected Week Header Sub-bar */}
      <div className="flex flex-wrap items-center justify-between gap-2 p-3.5 rounded-xl border border-slate-800 bg-slate-900/40">
        <div className="flex items-center gap-2">
          <span className="text-xs font-bold text-slate-200">
            Week {selectedWeek} Schedule
          </span>
          {phaseLabel && (
            <span className="text-[11px] font-semibold text-emerald-400 bg-emerald-500/10 border border-emerald-500/20 px-2 py-0.5 rounded-full">
              {phaseLabel}
            </span>
          )}
        </div>
        <span className="text-xs text-slate-400 flex items-center gap-1 font-mono">
          <span>Click any day to preview prescription</span>
          <ChevronRight className="h-3.5 w-3.5 text-slate-400" aria-hidden="true" />
        </span>
      </div>

      {/* Days Grid for Selected Week (Tab Panel for Selected Week) */}
      <div
        id="week-schedule-panel"
        role="tabpanel"
        aria-labelledby={`week-tab-${selectedWeek}`}
        className="grid grid-cols-1 sm:grid-cols-2 md:grid-cols-3 lg:grid-cols-4 gap-4"
      >
        {days.map((day) => {
          const dayNum = day.day_number ?? day.dayNumber
          const dayLabel = day.day_label ?? day.dayLabel ?? `Day ${dayNum}`
          const focus = day.focus || ''
          const totalSets = day.total_sets ?? day.totalSets ?? 0
          const durationMinutes = day.estimated_duration_minutes ?? day.estimatedDurationMinutes ?? 45

          // Authoritative state derivation
          const state = deriveProgramDayState(day, selectedWeek, program)

          const isSelected = selectedDay === dayNum

          return (
            <ProgramDayCard
              key={dayNum}
              dayNumber={dayNum}
              dayLabel={dayLabel}
              focus={focus}
              state={state}
              totalSets={totalSets}
              durationMinutes={durationMinutes}
              isSelected={isSelected}
              onSelect={() => onSelectDay(dayNum)}
            />
          )
        })}
      </div>
    </div>
  )
}
