import React from 'react'
import type { MuscleGroupProgressItem } from '../../types'
import { ArrowUp } from 'lucide-react'

export interface MuscleGroupProgressCardProps {
  groups: MuscleGroupProgressItem[]
}

export const MuscleGroupProgressCard: React.FC<MuscleGroupProgressCardProps> = ({ groups }) => {
  return (
    <div className="rounded-3xl border border-slate-800 bg-slate-900/90 p-5 space-y-4 text-left shadow-2xl h-full flex flex-col justify-between">
      <h3 className="text-sm font-extrabold text-slate-100 pb-2 border-b border-slate-800/80">
        Muscle Group Progress
      </h3>

      <div className="grid grid-cols-12 gap-3 items-center">
        {/* Anatomical Body Graphic (Front & Back) */}
        <div className="col-span-5 flex justify-center gap-2">
          <svg className="h-28 w-14 text-slate-700" viewBox="0 0 100 150" fill="none">
            <circle cx="50" cy="18" r="10" stroke="currentColor" strokeWidth="2" fill="#0f172a" />
            <path d="M32 35 L 68 35 L 62 85 L 38 85 Z" stroke="currentColor" strokeWidth="2" fill="#0f172a" />
            <path d="M30 35 L 18 80 M 70 35 L 82 80" stroke="currentColor" strokeWidth="3" />
            <path d="M42 85 L 38 140 M 58 85 L 62 140" stroke="currentColor" strokeWidth="4" />
            <path d="M35 40 Q 50 48, 65 40 L 62 58 Q 50 64, 38 58 Z" fill="#10b981" stroke="#34d399" strokeWidth="1.5" />
            <circle cx="32" cy="38" r="5" fill="#f59e0b" />
            <circle cx="68" cy="38" r="5" fill="#f59e0b" />
            <rect x="42" y="60" width="16" height="22" rx="3" fill="#f59e0b" />
            <path d="M42 88 L 39 135 M 58 88 L 61 135" stroke="#10b981" strokeWidth="4" />
          </svg>

          <svg className="h-28 w-14 text-slate-700" viewBox="0 0 100 150" fill="none">
            <circle cx="50" cy="18" r="10" stroke="currentColor" strokeWidth="2" fill="#0f172a" />
            <path d="M32 35 L 68 35 L 62 85 L 38 85 Z" stroke="currentColor" strokeWidth="2" fill="#0f172a" />
            <path d="M30 35 L 18 80 M 70 35 L 82 80" stroke="currentColor" strokeWidth="3" />
            <path d="M42 85 L 38 140 M 58 85 L 62 140" stroke="currentColor" strokeWidth="4" />
            <path d="M35 42 L 65 42 L 60 80 L 40 80 Z" fill="#10b981" stroke="#34d399" strokeWidth="1.5" />
            <path d="M26 44 L 23 60 M 74 44 L 77 60" stroke="#f59e0b" strokeWidth="3" />
          </svg>
        </div>

        {/* Percentage List Right */}
        <div className="col-span-7 space-y-1.5 font-mono text-xs">
          {groups.map((m) => {
            const isHigh = m.status === 'Excellent'
            const colorClass = isHigh ? 'text-emerald-400' : 'text-amber-400'
            const dotColor = isHigh ? 'bg-emerald-500' : 'bg-amber-500'

            return (
              <div key={m.name} className="flex items-center justify-between">
                <span className="flex items-center gap-1.5 text-slate-300 text-[11px]">
                  <span className={`h-2 w-2 rounded-full ${dotColor}`} />
                  {m.name}
                </span>
                <span className={`font-extrabold flex items-center ${colorClass}`}>
                  {m.changePct} <ArrowUp className="h-3 w-3 ml-0.5" />
                </span>
              </div>
            )
          })}
        </div>
      </div>

      {/* Legend Footer */}
      <div className="pt-2 border-t border-slate-800/80 flex items-center justify-around text-[10px] font-mono text-slate-400">
        <span className="flex items-center gap-1">
          <span className="h-2 w-2 rounded-full bg-emerald-500" /> Excellent
        </span>
        <span className="flex items-center gap-1">
          <span className="h-2 w-2 rounded-full bg-amber-500" /> Good
        </span>
        <span className="flex items-center gap-1">
          <span className="h-2 w-2 rounded-full bg-red-500" /> Needs Work
        </span>
      </div>
    </div>
  )
}
