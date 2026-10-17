import React from 'react'
import type { PersonalStatsData } from '../../types'
import { Scale, Flame, Dumbbell, Activity } from 'lucide-react'

export interface PersonalStatsCardProps {
  stats: PersonalStatsData
}

export const PersonalStatsCard: React.FC<PersonalStatsCardProps> = ({ stats }) => {
  return (
    <div className="rounded-3xl border border-slate-800 bg-slate-900/90 p-5 space-y-3.5 text-left shadow-2xl h-full flex flex-col justify-between">
      <div className="flex items-center justify-between pb-2 border-b border-slate-800/80">
        <h3 className="text-sm font-extrabold text-slate-100">Personal Stats</h3>
        <button type="button" className="text-xs font-semibold text-emerald-400 hover:text-emerald-300">
          View History
        </button>
      </div>

      <div className="space-y-3 font-mono text-xs">
        {/* Current Weight */}
        <div className="flex items-center justify-between p-2 rounded-xl bg-slate-950/60 border border-slate-800">
          <div className="flex items-center gap-2">
            <Scale className="h-4 w-4 text-emerald-400" />
            <span className="font-bold text-slate-300">Current Weight</span>
          </div>
          <div className="flex items-center gap-3">
            <span className="font-extrabold text-slate-100">
              {stats.currentWeightKg > 0 ? `${stats.currentWeightKg} kg` : 'Not recorded'}
            </span>
            {stats.currentWeightKg > 0 && stats.weightChangeKg !== 0 && (
              <span className="text-[10px] font-bold text-emerald-400 flex items-center">
                {stats.weightChangeKg < 0 ? '↓' : '↑'} {Math.abs(stats.weightChangeKg)} kg
              </span>
            )}
          </div>
        </div>

        {/* Body Fat */}
        <div className="flex items-center justify-between p-2 rounded-xl bg-slate-950/60 border border-slate-800">
          <div className="flex items-center gap-2">
            <Flame className="h-4 w-4 text-amber-400" />
            <span className="font-bold text-slate-300">Body Fat</span>
          </div>
          <div className="flex items-center gap-3">
            <span className="font-extrabold text-slate-100">
              {stats.bodyFatPct > 0 ? `${stats.bodyFatPct} %` : 'Not recorded'}
            </span>
            {stats.bodyFatPct > 0 && stats.bodyFatChangePct !== 0 && (
              <span className="text-[10px] font-bold text-emerald-400 flex items-center">
                {stats.bodyFatChangePct < 0 ? '↓' : '↑'} {Math.abs(stats.bodyFatChangePct)} %
              </span>
            )}
          </div>
        </div>

        {/* Muscle Mass */}
        <div className="flex items-center justify-between p-2 rounded-xl bg-slate-950/60 border border-slate-800">
          <div className="flex items-center gap-2">
            <Dumbbell className="h-4 w-4 text-blue-400" />
            <span className="font-bold text-slate-300">Muscle Mass</span>
          </div>
          <div className="flex items-center gap-3">
            <span className="font-extrabold text-slate-100">
              {stats.muscleMassKg > 0 ? `${stats.muscleMassKg} kg` : 'Not recorded'}
            </span>
            {stats.muscleMassKg > 0 && stats.muscleMassChangeKg !== 0 && (
              <span className="text-[10px] font-bold text-emerald-400 flex items-center">
                ↑ {stats.muscleMassChangeKg} kg
              </span>
            )}
          </div>
        </div>

        {/* BMI */}
        <div className="flex items-center justify-between p-2 rounded-xl bg-slate-950/60 border border-slate-800">
          <div className="flex items-center gap-2">
            <Activity className="h-4 w-4 text-cyan-400" />
            <span className="font-bold text-slate-300">BMI</span>
          </div>
          <div className="flex items-center gap-3">
            <span className="font-extrabold text-slate-100">{stats.bmi > 0 ? stats.bmi : '—'}</span>
            <span className="text-[10px] font-bold text-emerald-400">{stats.bmiStatus}</span>
          </div>
        </div>
      </div>
    </div>
  )
}
