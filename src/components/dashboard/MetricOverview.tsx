import React from 'react'
import { Activity, Moon, Droplets, Target } from 'lucide-react'
import { useUser } from '../../hooks'

export const MetricOverview: React.FC = () => {
  const { user } = useUser()
  const totalWorkouts = user?.totalWorkouts || 0
  const hasHistory = totalWorkouts > 0

  return (
    <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-4 gap-4 text-left">
      
      {/* Card 1: Training Load */}
      <div className="rounded-2xl border border-slate-800 bg-slate-900/90 p-4 flex flex-col justify-between space-y-3">
        <div className="flex items-center justify-between">
          <span className="text-xs font-medium text-slate-400">Training Load</span>
          <div className="flex h-8 w-8 items-center justify-center rounded-xl bg-emerald-500/10 text-emerald-400">
            <Activity className="h-4 w-4" />
          </div>
        </div>
        <div>
          <div className="flex items-baseline gap-1">
            <span className="text-2xl font-extrabold text-slate-100 font-mono">
              {hasHistory ? `${totalWorkouts}` : '—'}
            </span>
            <span className="text-xs text-slate-500 font-mono">{hasHistory ? 'sessions' : ''}</span>
          </div>
          <span className="text-[10px] font-mono text-emerald-400">
            {hasHistory ? 'Active Routine' : 'No training history'}
          </span>
        </div>
        {/* Sparkline */}
        <svg className="w-full h-8 text-emerald-400/40" viewBox="0 0 100 20" fill="none">
          <path
            d={hasHistory ? 'M0 15 Q 25 8, 50 12 T 100 4' : 'M0 15 L 100 15'}
            stroke="currentColor"
            strokeWidth="2"
            strokeLinecap="round"
          />
        </svg>
      </div>

      {/* Card 2: Recovery Score */}
      <div className="rounded-2xl border border-slate-800 bg-slate-900/90 p-4 flex flex-col justify-between space-y-3">
        <div className="flex items-center justify-between">
          <span className="text-xs font-medium text-slate-400">Recovery Score</span>
          <div className="flex h-8 w-8 items-center justify-center rounded-xl bg-purple-500/10 text-purple-400">
            <Moon className="h-4 w-4" />
          </div>
        </div>
        <div>
          <span className="text-2xl font-extrabold text-slate-100 font-mono">
            —
          </span>
          <span className="text-[10px] font-mono text-slate-400 block mt-0.5">
            Tracker not connected
          </span>
        </div>
        {/* Purple Sparkline */}
        <svg className="w-full h-8 text-purple-400/40" viewBox="0 0 100 20" fill="none">
          <path
            d="M0 18 L 100 18"
            stroke="currentColor"
            strokeWidth="2"
            strokeLinecap="round"
          />
        </svg>
      </div>

      {/* Card 3: Calorie Balance */}
      <div className="rounded-2xl border border-slate-800 bg-slate-900/90 p-4 flex flex-col justify-between space-y-3">
        <div className="flex items-center justify-between">
          <span className="text-xs font-medium text-slate-400">Calorie Balance</span>
          <div className="flex h-8 w-8 items-center justify-center rounded-xl bg-cyan-500/10 text-cyan-400">
            <Droplets className="h-4 w-4" />
          </div>
        </div>
        <div>
          <div className="flex items-baseline gap-1">
            <span className="text-2xl font-extrabold text-slate-100 font-mono">
              0
            </span>
            <span className="text-xs text-slate-400 font-mono">kcal</span>
          </div>
          <span className="text-[10px] font-mono text-cyan-400">
            {user?.targetCalories ? `Target: ${user.targetCalories} kcal` : 'Set in Onboarding'}
          </span>
        </div>
        {/* Cyan Sparkline */}
        <svg className="w-full h-8 text-cyan-400/40" viewBox="0 0 100 20" fill="none">
          <path d="M0 15 L 100 15" stroke="currentColor" strokeWidth="2" strokeLinecap="round" />
        </svg>
      </div>

      {/* Card 4: Weekly Progress */}
      <div className="rounded-2xl border border-slate-800 bg-slate-900/90 p-4 flex flex-col justify-between space-y-3">
        <div className="flex items-center justify-between">
          <span className="text-xs font-medium text-slate-400">Weekly Progress</span>
          <div className="flex h-8 w-8 items-center justify-center rounded-xl bg-amber-500/10 text-amber-400">
            <Target className="h-4 w-4" />
          </div>
        </div>
        <div>
          <span className="text-2xl font-extrabold text-slate-100 font-mono">
            {hasHistory ? `${Math.min(100, Math.round((totalWorkouts / (user?.workoutFrequencyDaysPerWeek || 4)) * 100))}%` : '0%'}
          </span>
          <span className="text-[10px] font-mono text-amber-400 block mt-0.5">
            {hasHistory ? `${totalWorkouts} workouts completed` : '0 workouts this week'}
          </span>
        </div>
        {/* Mini Bar Chart */}
        <div className="flex items-end gap-1 h-8">
          {[0, 0, 0, 0, 0, 0, 0].map((val, idx) => (
            <div
              key={idx}
              className="flex-1 bg-slate-800 rounded-t-sm"
              style={{ height: `${val || 10}%` }}
            />
          ))}
        </div>
      </div>

    </div>
  )
}
