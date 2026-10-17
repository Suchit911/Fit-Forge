import React from 'react'
import type { FitnessGoalData } from '../../types'

export interface FitnessGoalsCardProps {
  goals: FitnessGoalData
  onEditGoalClick: () => void
}

export const FitnessGoalsCard: React.FC<FitnessGoalsCardProps> = ({ goals, onEditGoalClick }) => {
  return (
    <div className="rounded-3xl border border-slate-800 bg-slate-900/90 p-5 space-y-3.5 text-left shadow-2xl h-full flex flex-col justify-between">
      <div className="flex items-center justify-between pb-2 border-b border-slate-800/80">
        <h3 className="text-sm font-extrabold text-slate-100 flex items-center gap-1.5">
          <span className="h-2 w-2 rounded-full bg-emerald-400" /> Fitness Goals
        </h3>
        <button
          type="button"
          onClick={onEditGoalClick}
          className="text-xs font-semibold text-emerald-400 hover:text-emerald-300 cursor-pointer"
        >
          Edit Goal
        </button>
      </div>

      <div className="grid grid-cols-12 gap-3 items-center font-mono text-xs">
        {/* Left Rows (7 of 12 cols) */}
        <div className="col-span-7 space-y-2.5">
          <div className="space-y-0.5">
            <span className="text-[10px] text-slate-400 font-bold uppercase">Primary Goal</span>
            <span className="font-extrabold text-slate-100 block">{goals.primaryGoal}</span>
          </div>

          <div className="space-y-0.5">
            <span className="text-[10px] text-slate-400 font-bold uppercase">Target Weight</span>
            <span className="font-extrabold text-slate-100 block">{goals.targetWeightKg} kg</span>
          </div>

          <div className="space-y-0.5">
            <span className="text-[10px] text-slate-400 font-bold uppercase">Weekly Workout Target</span>
            <span className="font-extrabold text-slate-100 block">{goals.weeklyWorkoutTarget}</span>
          </div>

          <div className="space-y-0.5">
            <span className="text-[10px] text-slate-400 font-bold uppercase">Target Date</span>
            <span className="font-extrabold text-slate-100 block">{goals.targetDate}</span>
          </div>
        </div>

        {/* Right Circular Progress Ring (5 of 12 cols) */}
        <div className="col-span-5 flex flex-col items-center justify-center text-center space-y-1 border-l border-slate-800/80 pl-2">
          <div className="relative flex items-center justify-center">
            <svg className="h-24 w-24 transform -rotate-90">
              <circle cx="48" cy="48" r="38" stroke="#1e293b" strokeWidth="6" fill="transparent" />
              <circle
                cx="48"
                cy="48"
                r="38"
                stroke="#10b981"
                strokeWidth="6"
                strokeDasharray="238"
                strokeDashoffset={238 - (238 * goals.progressPct) / 100}
                strokeLinecap="round"
                fill="transparent"
              />
            </svg>
            <div className="absolute text-center">
              <span className="text-xl font-extrabold text-slate-100 block">{goals.progressPct}%</span>
              <span className="text-[8px] text-slate-400 font-sans block">Progress to Goal</span>
            </div>
          </div>

          <span className="text-[10px] text-slate-400 font-bold block pt-1">{goals.kgToGo} kg to go</span>
        </div>
      </div>
    </div>
  )
}
