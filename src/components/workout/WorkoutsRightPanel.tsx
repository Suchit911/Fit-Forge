import React, { useState } from 'react'
import { Link } from 'react-router-dom'
import { Users, Clock, Flame, ArrowRight } from 'lucide-react'

export const WorkoutsRightPanel: React.FC = () => {
  const [selectedMuscle, setSelectedMuscle] = useState('Back')
  const [selectedDifficulty, setSelectedDifficulty] = useState('Intermediate')

  const muscles = ['Chest', 'Back', 'Shoulders', 'Arms', 'Legs', 'Core', 'Full Body']
  const difficulties = ['Beginner', 'Intermediate', 'Advanced']

  return (
    <div className="space-y-6 text-left">
      {/* Filter Workouts Card */}
      <div className="rounded-2xl border border-slate-800 bg-slate-900/90 p-5 space-y-4">
        <div className="flex items-center justify-between pb-3 border-b border-slate-800/80">
          <h3 className="text-sm font-extrabold text-slate-100">Filter Workouts</h3>
          <button type="button" className="text-xs font-semibold text-emerald-400 hover:text-emerald-300">
            Clear All
          </button>
        </div>

        {/* Muscle Group */}
        <div className="space-y-2">
          <label className="text-xs font-bold text-slate-300 block">Muscle Group</label>
          <div className="flex flex-wrap gap-2">
            {muscles.map((m) => (
              <button
                key={m}
                type="button"
                onClick={() => setSelectedMuscle(m)}
                className={`rounded-xl px-3 py-1.5 text-xs font-semibold border transition-all cursor-pointer ${
                  selectedMuscle === m
                    ? 'border-emerald-500 bg-emerald-950/60 text-emerald-400 font-bold'
                    : 'border-slate-800 bg-slate-950/60 text-slate-400 hover:border-slate-700 hover:text-slate-200'
                }`}
              >
                {m}
              </button>
            ))}
          </div>
        </div>

        {/* Difficulty Level */}
        <div className="space-y-2 pt-2">
          <label className="text-xs font-bold text-slate-300 block">Difficulty Level</label>
          <div className="grid grid-cols-3 gap-2">
            {difficulties.map((d) => (
              <button
                key={d}
                type="button"
                onClick={() => setSelectedDifficulty(d)}
                className={`rounded-xl py-1.5 text-[11px] font-semibold border text-center transition-all cursor-pointer ${
                  selectedDifficulty === d
                    ? 'border-emerald-500 bg-emerald-950/60 text-emerald-400 font-bold'
                    : 'border-slate-800 bg-slate-950/60 text-slate-400 hover:border-slate-700 hover:text-slate-200'
                }`}
              >
                {d}
              </button>
            ))}
          </div>
        </div>

        {/* Workout Type Dropdown */}
        <div className="space-y-2 pt-2">
          <label className="text-xs font-bold text-slate-300 block">Workout Type</label>
          <select className="w-full h-9 rounded-xl border border-slate-800 bg-slate-950 px-3 text-xs text-slate-200 focus:outline-none">
            <option value="all">All Types</option>
            <option value="strength">Strength Training</option>
            <option value="hypertrophy">Hypertrophy</option>
            <option value="cardio">Cardio & HIIT</option>
          </select>
        </div>

        {/* Duration Slider */}
        <div className="space-y-2 pt-2">
          <div className="flex justify-between text-xs">
            <span className="font-bold text-slate-300">Duration</span>
            <span className="font-mono text-emerald-400">10 min - 120+ min</span>
          </div>
          <input
            type="range"
            min="10"
            max="120"
            defaultValue="45"
            className="w-full accent-emerald-500 bg-slate-950 h-1.5 rounded-lg cursor-pointer"
          />
        </div>
      </div>

      {/* Weekly Summary Card */}
      <div className="rounded-2xl border border-slate-800 bg-slate-900/90 p-5 space-y-4">
        <div className="flex items-center justify-between pb-3 border-b border-slate-800/80">
          <h3 className="text-sm font-extrabold text-slate-100">Weekly Summary</h3>
          <span className="text-[10px] text-slate-400 font-mono">This Week ⌄</span>
        </div>

        <div className="grid grid-cols-3 gap-2 text-center">
          <div className="p-2 rounded-xl bg-slate-950/60 border border-slate-800">
            <Users className="h-4 w-4 text-emerald-400 mx-auto mb-1" />
            <span className="text-sm font-extrabold text-slate-100 font-mono block">5</span>
            <span className="text-[9px] text-slate-400">Workouts</span>
          </div>
          <div className="p-2 rounded-xl bg-slate-950/60 border border-slate-800">
            <Clock className="h-4 w-4 text-purple-400 mx-auto mb-1" />
            <span className="text-sm font-extrabold text-slate-100 font-mono block">225</span>
            <span className="text-[9px] text-slate-400">Minutes</span>
          </div>
          <div className="p-2 rounded-xl bg-slate-950/60 border border-slate-800">
            <Flame className="h-4 w-4 text-amber-400 mx-auto mb-1" />
            <span className="text-sm font-extrabold text-slate-100 font-mono block">12,450</span>
            <span className="text-[9px] text-slate-400">Calories</span>
          </div>
        </div>

        {/* Progress Bar */}
        <div className="space-y-1.5 pt-2">
          <div className="flex justify-between text-[11px] font-mono">
            <span className="text-slate-400">Weekly Goal Progress</span>
            <span className="text-emerald-400 font-bold">80%</span>
          </div>
          <p className="text-[10px] text-slate-400">5 of 6 workouts completed</p>
          <div className="w-full h-2 bg-slate-950 rounded-full overflow-hidden border border-slate-800">
            <div className="h-full bg-emerald-500 rounded-full" style={{ width: '80%' }} />
          </div>
        </div>
      </div>

      {/* Quick Actions Card */}
      <div className="rounded-2xl border border-slate-800 bg-slate-900/90 p-5 space-y-3">
        <h3 className="text-sm font-extrabold text-slate-100 pb-2 border-b border-slate-800/80">
          Quick Actions
        </h3>

        <Link
          to="/workouts/wkt_upper_push"
          className="flex items-center justify-between p-3 rounded-xl bg-slate-950/70 border border-slate-800 hover:border-slate-700 transition-colors"
        >
          <div>
            <h4 className="text-xs font-bold text-slate-100">My Workout Plan</h4>
            <span className="text-[10px] text-slate-400">View your current plan</span>
          </div>
          <ArrowRight className="h-4 w-4 text-slate-400" />
        </Link>

        <button
          type="button"
          className="w-full flex items-center justify-between p-3 rounded-xl bg-slate-950/70 border border-slate-800 hover:border-slate-700 transition-colors text-left"
        >
          <div>
            <h4 className="text-xs font-bold text-slate-100">Custom Workout</h4>
            <span className="text-[10px] text-slate-400">Create a new workout</span>
          </div>
          <ArrowRight className="h-4 w-4 text-slate-400" />
        </button>

        <Link
          to="/workouts/history"
          className="flex items-center justify-between p-3 rounded-xl bg-slate-950/70 border border-slate-800 hover:border-slate-700 transition-colors"
        >
          <div>
            <h4 className="text-xs font-bold text-slate-100">Workout History</h4>
            <span className="text-[10px] text-slate-400">View completed workouts</span>
          </div>
          <ArrowRight className="h-4 w-4 text-slate-400" />
        </Link>
      </div>

    </div>
  )
}
