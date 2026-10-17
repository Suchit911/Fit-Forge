import React from 'react'
import type { GeneralSettingsData } from '../../types'
import { Settings, Globe, Scale, Clock, Calendar, Timer } from 'lucide-react'

export interface GeneralSettingsCardProps {
  general: GeneralSettingsData
  onUpdate: (data: Partial<GeneralSettingsData>) => void
}

export const GeneralSettingsCard: React.FC<GeneralSettingsCardProps> = ({ general, onUpdate }) => {
  return (
    <div className="rounded-3xl border border-slate-800 bg-slate-900/90 p-5 space-y-4 text-left shadow-2xl h-full flex flex-col justify-between">
      <div className="flex items-center gap-2 pb-2 border-b border-slate-800/80">
        <div className="flex h-7 w-7 items-center justify-center rounded-xl bg-emerald-500/10 text-emerald-400 border border-emerald-500/20">
          <Settings className="h-4 w-4" />
        </div>
        <h3 className="text-sm font-extrabold text-slate-100">General Settings</h3>
      </div>

      <div className="space-y-3 font-mono text-xs">
        {/* Language */}
        <div className="flex items-center justify-between py-1 border-b border-slate-800/50">
          <div className="flex items-center gap-2">
            <Globe className="h-4 w-4 text-emerald-400" />
            <span className="text-slate-300 font-bold">Language</span>
          </div>
          <select
            value={general.language}
            onChange={(e) => onUpdate({ language: e.target.value })}
            className="rounded-xl border border-slate-800 bg-slate-950 px-2.5 py-1 text-xs text-slate-100 font-bold focus:outline-none cursor-pointer"
          >
            <option value="English">English</option>
            <option value="Spanish">Spanish</option>
            <option value="German">German</option>
            <option value="Hindi">Hindi</option>
          </select>
        </div>

        {/* Units */}
        <div className="flex items-center justify-between py-1 border-b border-slate-800/50">
          <div className="flex items-center gap-2">
            <Scale className="h-4 w-4 text-emerald-400" />
            <span className="text-slate-300 font-bold">Units</span>
          </div>
          <select
            value={general.units}
            onChange={(e) => onUpdate({ units: e.target.value })}
            className="rounded-xl border border-slate-800 bg-slate-950 px-2.5 py-1 text-xs text-slate-100 font-bold focus:outline-none cursor-pointer"
          >
            <option value="Metric (kg, cm)">Metric (kg, cm)</option>
            <option value="Imperial (lbs, in)">Imperial (lbs, in)</option>
          </select>
        </div>

        {/* Time Zone */}
        <div className="flex items-center justify-between py-1 border-b border-slate-800/50">
          <div className="flex items-center gap-2">
            <Clock className="h-4 w-4 text-emerald-400" />
            <span className="text-slate-300 font-bold">Time Zone</span>
          </div>
          <select
            value={general.timeZone}
            onChange={(e) => onUpdate({ timeZone: e.target.value })}
            className="rounded-xl border border-slate-800 bg-slate-950 px-2.5 py-1 text-xs text-slate-100 font-bold focus:outline-none cursor-pointer max-w-[170px] truncate"
          >
            <option value="(GMT+05:30) Asia/Kolkata">(GMT+05:30) Asia/Kolkata</option>
            <option value="(GMT-05:00) EST (US & Canada)">(GMT-05:00) EST</option>
            <option value="(GMT+00:00) UTC / London">(GMT+00:00) UTC</option>
          </select>
        </div>

        {/* Week Starts On */}
        <div className="flex items-center justify-between py-1 border-b border-slate-800/50">
          <div className="flex items-center gap-2">
            <Calendar className="h-4 w-4 text-emerald-400" />
            <span className="text-slate-300 font-bold">Week Starts On</span>
          </div>
          <select
            value={general.weekStartDay}
            onChange={(e) => onUpdate({ weekStartDay: e.target.value })}
            className="rounded-xl border border-slate-800 bg-slate-950 px-2.5 py-1 text-xs text-slate-100 font-bold focus:outline-none cursor-pointer"
          >
            <option value="Monday">Monday</option>
            <option value="Sunday">Sunday</option>
          </select>
        </div>

        {/* Default Workout Duration */}
        <div className="flex items-center justify-between py-1">
          <div className="flex items-center gap-2">
            <Timer className="h-4 w-4 text-emerald-400" />
            <span className="text-slate-300 font-bold">Default Workout Duration</span>
          </div>
          <select
            value={String(general.defaultWorkoutDurationMin)}
            onChange={(e) => onUpdate({ defaultWorkoutDurationMin: Number(e.target.value) })}
            className="rounded-xl border border-slate-800 bg-slate-950 px-2.5 py-1 text-xs text-slate-100 font-bold focus:outline-none cursor-pointer"
          >
            <option value="45">45 minutes</option>
            <option value="60">60 minutes</option>
            <option value="75">75 minutes</option>
            <option value="90">90 minutes</option>
          </select>
        </div>
      </div>
    </div>
  )
}
