import React from 'react'
import type { TrainingPreferencesData } from '../../types'
import { Calendar, Dumbbell, Wrench, Clock, Sun } from 'lucide-react'

export interface TrainingPreferencesCardProps {
  pref: TrainingPreferencesData
  onEditClick: () => void
}

export const TrainingPreferencesCard: React.FC<TrainingPreferencesCardProps> = ({ pref, onEditClick }) => {
  return (
    <div className="rounded-3xl border border-slate-800 bg-slate-900/90 p-5 space-y-3.5 text-left shadow-2xl h-full flex flex-col justify-between">
      <div className="flex items-center justify-between pb-2 border-b border-slate-800/80">
        <h3 className="text-sm font-extrabold text-slate-100">Training Preferences</h3>
        <button
          type="button"
          onClick={onEditClick}
          className="text-xs font-semibold text-emerald-400 hover:text-emerald-300 cursor-pointer"
        >
          Edit
        </button>
      </div>

      <div className="space-y-3 font-mono text-xs">
        <div className="flex items-center justify-between py-1 border-b border-slate-800/50">
          <div className="flex items-center gap-2">
            <Calendar className="h-4 w-4 text-emerald-400" />
            <span className="text-slate-400 font-bold">Training Days</span>
          </div>
          <span className="font-extrabold text-slate-100">{pref.trainingDays}</span>
        </div>

        <div className="flex items-center justify-between py-1 border-b border-slate-800/50">
          <div className="flex items-center gap-2">
            <Dumbbell className="h-4 w-4 text-emerald-400" />
            <span className="text-slate-400 font-bold">Preferred Workout Type</span>
          </div>
          <span className="font-extrabold text-slate-100">{pref.preferredWorkoutType}</span>
        </div>

        <div className="flex items-center justify-between py-1 border-b border-slate-800/50">
          <div className="flex items-center gap-2">
            <Wrench className="h-4 w-4 text-emerald-400" />
            <span className="text-slate-400 font-bold">Equipment Available</span>
          </div>
          <span className="font-extrabold text-slate-100">{pref.equipmentAvailable}</span>
        </div>

        <div className="flex items-center justify-between py-1 border-b border-slate-800/50">
          <div className="flex items-center gap-2">
            <Clock className="h-4 w-4 text-emerald-400" />
            <span className="text-slate-400 font-bold">Workout Duration</span>
          </div>
          <span className="font-extrabold text-slate-100">{pref.workoutDuration}</span>
        </div>

        <div className="flex items-center justify-between py-1">
          <div className="flex items-center gap-2">
            <Sun className="h-4 w-4 text-emerald-400" />
            <span className="text-slate-400 font-bold">Preferred Time</span>
          </div>
          <span className="font-extrabold text-slate-100">{pref.preferredTime}</span>
        </div>
      </div>
    </div>
  )
}
