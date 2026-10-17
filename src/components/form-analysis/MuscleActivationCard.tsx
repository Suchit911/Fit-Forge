import React from 'react'
import type { MuscleActivationItem } from '../../types'

export interface MuscleActivationCardProps {
  muscles: MuscleActivationItem[]
}

export const MuscleActivationCard: React.FC<MuscleActivationCardProps> = ({ muscles }) => {
  return (
    <div className="rounded-2xl border border-slate-800 bg-slate-900/90 p-5 space-y-4 text-left">
      <h3 className="text-sm font-extrabold text-slate-100 pb-2 border-b border-slate-800/80">
        Muscle Activation
      </h3>

      <div className="grid grid-cols-12 gap-4 items-center">
        {/* Anatomical Graphic */}
        <div className="col-span-5 flex justify-center gap-2 py-1">
          <svg className="h-28 w-14 text-slate-700" viewBox="0 0 100 150" fill="none">
            <circle cx="50" cy="18" r="10" stroke="currentColor" strokeWidth="2" fill="#0f172a" />
            <path d="M32 35 L 68 35 L 62 85 L 38 85 Z" stroke="currentColor" strokeWidth="2" fill="#0f172a" />
            <path d="M30 35 L 18 80 M 70 35 L 82 80" stroke="currentColor" strokeWidth="3" />
            <path d="M42 85 L 38 140 M 58 85 L 62 140" stroke="currentColor" strokeWidth="4" />
            {/* Highlighted Chest */}
            <path d="M35 40 Q 50 48, 65 40 L 62 58 Q 50 64, 38 58 Z" fill="#ef4444" stroke="#f97316" strokeWidth="1.5" />
          </svg>

          <svg className="h-28 w-14 text-slate-700" viewBox="0 0 100 150" fill="none">
            <circle cx="50" cy="18" r="10" stroke="currentColor" strokeWidth="2" fill="#0f172a" />
            <path d="M32 35 L 68 35 L 62 85 L 38 85 Z" stroke="currentColor" strokeWidth="2" fill="#0f172a" />
            <path d="M30 35 L 18 80 M 70 35 L 82 80" stroke="currentColor" strokeWidth="3" />
            <path d="M42 85 L 38 140 M 58 85 L 62 140" stroke="currentColor" strokeWidth="4" />
            {/* Highlighted Triceps Back */}
            <path d="M26 44 L 23 60 M 74 44 L 77 60" stroke="#f97316" strokeWidth="3" />
          </svg>
        </div>

        {/* Muscle Percentage Legend List */}
        <div className="col-span-7 space-y-2 font-mono text-xs">
          {muscles.length === 0 ? (
            <div className="py-4 text-center text-[11px] text-slate-500">
              Awaiting movement data. Muscle engagement estimates populate during active repetitions.
            </div>
          ) : (
            muscles.map((m) => {
              const isHigh = m.activationPct > 80
              const isMed = m.activationPct >= 60 && m.activationPct <= 80

              const colorClass = isHigh
                ? 'text-emerald-400'
                : isMed
                ? 'text-amber-400'
                : 'text-slate-400'

              const dotColor = isHigh ? 'bg-red-500' : isMed ? 'bg-amber-500' : 'bg-slate-500'

              return (
                <div key={m.name} className="flex items-center justify-between">
                  <span className="flex items-center gap-2 text-slate-300 text-[11px]">
                    <span className={`h-2 w-2 rounded-full ${dotColor}`} />
                    {m.name}
                  </span>
                  <span className={`font-bold ${colorClass}`}>{m.activationPct}%</span>
                </div>
              )
            })
          )}
        </div>
      </div>
    </div>
  )
}
