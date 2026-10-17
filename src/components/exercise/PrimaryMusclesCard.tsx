import React from 'react'

export const PrimaryMusclesCard: React.FC = () => {
  return (
    <div className="rounded-3xl border border-slate-800 bg-slate-900/90 p-6 space-y-4 text-left">
      <h3 className="text-base font-extrabold text-slate-100">Primary Muscles</h3>

      <div className="flex items-center justify-around py-2">
        {/* Front View */}
        <div className="flex flex-col items-center gap-1">
          <svg className="h-28 w-20 text-slate-700" viewBox="0 0 100 150" fill="none">
            <circle cx="50" cy="18" r="10" stroke="currentColor" strokeWidth="2" fill="#0f172a" />
            <path d="M32 35 L 68 35 L 62 85 L 38 85 Z" stroke="currentColor" strokeWidth="2" fill="#0f172a" />
            <path d="M30 35 L 18 80 M 70 35 L 82 80" stroke="currentColor" strokeWidth="3" />
            <path d="M42 85 L 38 140 M 58 85 L 62 140" stroke="currentColor" strokeWidth="4" />
            {/* Highlighted Chest */}
            <path d="M35 40 Q 50 48, 65 40 L 62 58 Q 50 64, 38 58 Z" fill="#ef4444" stroke="#f97316" strokeWidth="1.5" />
          </svg>
          <span className="text-[10px] font-mono text-slate-400">Front</span>
        </div>

        {/* Back View */}
        <div className="flex flex-col items-center gap-1">
          <svg className="h-28 w-20 text-slate-700" viewBox="0 0 100 150" fill="none">
            <circle cx="50" cy="18" r="10" stroke="currentColor" strokeWidth="2" fill="#0f172a" />
            <path d="M32 35 L 68 35 L 62 85 L 38 85 Z" stroke="currentColor" strokeWidth="2" fill="#0f172a" />
            <path d="M30 35 L 18 80 M 70 35 L 82 80" stroke="currentColor" strokeWidth="3" />
            <path d="M42 85 L 38 140 M 58 85 L 62 140" stroke="currentColor" strokeWidth="4" />
            {/* Highlighted Triceps Back */}
            <path d="M26 44 L 23 60 M 74 44 L 77 60" stroke="#f97316" strokeWidth="3" />
          </svg>
          <span className="text-[10px] font-mono text-slate-400">Back</span>
        </div>

        {/* Side View */}
        <div className="flex flex-col items-center gap-1">
          <svg className="h-28 w-20 text-slate-700" viewBox="0 0 100 150" fill="none">
            <circle cx="50" cy="18" r="10" stroke="currentColor" strokeWidth="2" fill="#0f172a" />
            <path d="M40 35 L 60 35 L 55 85 L 45 85 Z" stroke="currentColor" strokeWidth="2" fill="#0f172a" />
            <path d="M50 35 L 55 80" stroke="currentColor" strokeWidth="3" />
            <path d="M50 85 L 52 140" stroke="currentColor" strokeWidth="4" />
            {/* Highlighted Side Deltoid / Chest */}
            <circle cx="54" cy="42" r="7" fill="#ef4444" />
          </svg>
          <span className="text-[10px] font-mono text-slate-400">Side</span>
        </div>
      </div>
    </div>
  )
}
