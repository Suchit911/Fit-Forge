import React from 'react'
import { Heart } from 'lucide-react'

export const HeartRateCard: React.FC = () => {
  return (
    <div className="rounded-3xl border border-slate-800 bg-slate-900/90 p-5 space-y-3 text-left">
      <div className="flex items-center gap-2 pb-2 border-b border-slate-800/80">
        <Heart className="h-4 w-4 text-red-500 animate-pulse" />
        <h3 className="text-xs font-mono font-extrabold text-slate-300 uppercase tracking-wider">
          Heart Rate
        </h3>
      </div>

      <div className="flex items-baseline justify-between">
        <div>
          <div className="flex items-baseline gap-1">
            <span className="text-3xl font-extrabold text-slate-100 font-mono">138</span>
            <span className="text-xs font-bold text-red-400 font-mono">bpm</span>
          </div>
          <span className="text-[10px] text-red-400 font-mono font-bold block mt-0.5">
            Zone 3 (Cardio)
          </span>
        </div>

        {/* Dynamic Heart Rate Sparkline */}
        <div className="w-32 h-10 text-red-500">
          <svg className="w-full h-full" viewBox="0 0 100 30" fill="none">
            <path
              d="M0 20 L 15 20 L 20 10 L 25 28 L 30 5 L 35 22 L 40 18 L 50 20 L 55 12 L 60 25 L 65 8 L 70 20 L 100 20"
              stroke="currentColor"
              strokeWidth="2"
              strokeLinecap="round"
              strokeLinejoin="round"
            />
          </svg>
        </div>
      </div>
    </div>
  )
}
