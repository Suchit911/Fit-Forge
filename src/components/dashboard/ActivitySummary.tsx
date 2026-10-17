import React from 'react'
import { Footprints, Flame, Clock, Heart } from 'lucide-react'
import { useUser } from '../../hooks'

export const ActivitySummary: React.FC = () => {
  const { user } = useUser()
  const hasActivity = (user?.totalWorkouts || 0) > 0

  return (
    <div className="rounded-2xl border border-slate-800 bg-slate-900/90 p-5 text-left space-y-4">
      
      <div className="flex items-center justify-between pb-2 border-b border-slate-800/80">
        <h3 className="text-sm font-extrabold text-slate-100">
          Today's Activity Summary
        </h3>
        {!hasActivity && (
          <span className="text-[10px] text-slate-500 font-mono">
            No tracker synced
          </span>
        )}
      </div>

      <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-4 gap-4">
        
        {/* Card 1: Steps */}
        <div className="rounded-xl border border-slate-800 bg-slate-950/70 p-4 space-y-2">
          <div className="flex items-center justify-between">
            <span className="text-xs text-slate-400 font-medium">Steps</span>
            <Footprints className="h-4 w-4 text-emerald-400" />
          </div>
          <div className="flex items-baseline gap-1">
            <span className="text-xl font-extrabold text-slate-100 font-mono">
              --
            </span>
            <span className="text-xs text-slate-500 font-mono">not synced</span>
          </div>
          <div className="w-full h-1.5 bg-slate-800 rounded-full overflow-hidden">
            <div
              className="h-full bg-slate-700 rounded-full"
              style={{ width: '0%' }}
            />
          </div>
        </div>

        {/* Card 2: Active Calories */}
        <div className="rounded-xl border border-slate-800 bg-slate-950/70 p-4 space-y-2">
          <div className="flex items-center justify-between">
            <span className="text-xs text-slate-400 font-medium">Active Calories</span>
            <Flame className="h-4 w-4 text-amber-400" />
          </div>
          <div className="flex items-baseline gap-1">
            <span className="text-xl font-extrabold text-slate-100 font-mono">
              {user?.totalCaloriesBurned ? user.totalCaloriesBurned.toLocaleString() : '0'}
            </span>
            <span className="text-xs text-slate-500 font-mono">/ 500 kcal</span>
          </div>
          <div className="w-full h-1.5 bg-slate-800 rounded-full overflow-hidden">
            <div
              className="h-full bg-amber-400 rounded-full"
              style={{ width: user?.totalCaloriesBurned ? `${Math.min(100, Math.round((user.totalCaloriesBurned / 500) * 100))}%` : '0%' }}
            />
          </div>
        </div>

        {/* Card 3: Workout Time */}
        <div className="rounded-xl border border-slate-800 bg-slate-950/70 p-4 space-y-2">
          <div className="flex items-center justify-between">
            <span className="text-xs text-slate-400 font-medium">Workout Time</span>
            <Clock className="h-4 w-4 text-purple-400" />
          </div>
          <div className="flex items-baseline gap-1">
            <span className="text-xl font-extrabold text-slate-100 font-mono">
              {hasActivity ? '30' : '0'}
            </span>
            <span className="text-xs text-slate-500 font-mono">/ {user?.workoutDurationMinutes || 45} min</span>
          </div>
          <div className="w-full h-1.5 bg-slate-800 rounded-full overflow-hidden">
            <div
              className="h-full bg-purple-400 rounded-full"
              style={{ width: hasActivity ? '66%' : '0%' }}
            />
          </div>
        </div>

        {/* Card 4: Heart Rate */}
        <div className="rounded-xl border border-slate-800 bg-slate-950/70 p-4 space-y-2">
          <div className="flex items-center justify-between">
            <span className="text-xs text-slate-400 font-medium">Heart Rate</span>
            <Heart className="h-4 w-4 text-red-400/50" />
          </div>
          <div>
            <span className="text-xl font-extrabold text-slate-100 font-mono">
              --
            </span>
            <span className="text-xs text-slate-500 font-mono ml-1">not synced</span>
          </div>
          {/* Baseline flat line */}
          <svg className="w-full h-5 text-slate-700" viewBox="0 0 100 20" fill="none">
            <path
              d="M0 10 L 100 10"
              stroke="currentColor"
              strokeWidth="2"
              strokeLinecap="round"
            />
          </svg>
        </div>

      </div>

    </div>
  )
}
