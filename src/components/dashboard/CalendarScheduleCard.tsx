import React, { useState } from 'react'
import { ChevronLeft, ChevronRight } from 'lucide-react'

export const CalendarScheduleCard: React.FC = () => {
  const [selectedDay, setSelectedDay] = useState(15)

  const daysOfWeek = ['S', 'M', 'T', 'W', 'T', 'F', 'S']
  const dates = [
    28, 29, 30, 1, 2, 3, 4,
    5, 6, 7, 8, 9, 10, 11,
    12, 13, 14, 15, 16, 17, 18,
    19, 20, 21, 22, 23, 24, 25,
    26, 27, 28, 29, 30, 31, 1
  ]

  return (
    <div className="rounded-2xl border border-slate-800 bg-slate-900/90 p-5 text-left space-y-4">
      
      {/* Header */}
      <div className="flex items-center justify-between pb-3 border-b border-slate-800/80">
        <h3 className="text-sm font-extrabold text-slate-100">Calendar & Schedule</h3>
        <div className="flex items-center gap-1 text-slate-400">
          <button type="button" className="p-1 rounded hover:bg-slate-800 hover:text-slate-200">
            <ChevronLeft className="h-4 w-4" />
          </button>
          <button type="button" className="p-1 rounded hover:bg-slate-800 hover:text-slate-200">
            <ChevronRight className="h-4 w-4" />
          </button>
        </div>
      </div>

      {/* Weekday Labels */}
      <div className="grid grid-cols-7 text-center text-[10px] font-mono text-slate-500 font-bold">
        {daysOfWeek.map((day, idx) => (
          <span key={idx}>{day}</span>
        ))}
      </div>

      {/* Date Grid */}
      <div className="grid grid-cols-7 gap-1 text-center text-xs font-mono">
        {dates.map((d, idx) => {
          const isCurrentMonth = idx >= 3 && idx < 34
          const isSelected = d === selectedDay && isCurrentMonth

          return (
            <button
              key={idx}
              type="button"
              onClick={() => isCurrentMonth && setSelectedDay(d)}
              className={`h-7 w-7 mx-auto flex items-center justify-center rounded-full transition-all cursor-pointer ${
                isSelected
                  ? 'bg-emerald-500 text-slate-950 font-extrabold shadow-md shadow-emerald-500/30'
                  : isCurrentMonth
                  ? 'text-slate-200 hover:bg-slate-800'
                  : 'text-slate-700'
              }`}
            >
              {d}
            </button>
          )
        })}
      </div>

      {/* Schedule Items List */}
      <div className="pt-3 border-t border-slate-800/80 space-y-2.5">
        <div className="flex items-center justify-between text-xs">
          <span className="font-bold text-slate-200">Today • {new Date().toLocaleDateString('en-US', { month: 'short', day: 'numeric', year: 'numeric' })}</span>
          <span className="text-[10px] text-slate-400 font-mono">Schedule</span>
        </div>

        {/* Honest empty state */}
        <div className="p-3 rounded-xl bg-slate-950/70 border border-slate-800/80 text-center space-y-1">
          <p className="text-xs font-semibold text-slate-300">No Scheduled Sessions</p>
          <p className="text-[11px] text-slate-400">
            Select a workout from the catalog or sync a wearable tracker to populate your daily timeline.
          </p>
        </div>
      </div>

    </div>
  )
}
