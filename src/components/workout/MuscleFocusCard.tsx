import React from 'react'
import { Target } from 'lucide-react'

export const MuscleFocusCard: React.FC = () => {
  return (
    <div className="rounded-3xl border border-slate-800 bg-slate-900/90 p-5 space-y-4 text-left">
      <div className="flex items-center gap-2 pb-2 border-b border-slate-800/80">
        <Target className="h-4 w-4 text-emerald-400" />
        <h3 className="text-xs font-mono font-extrabold text-slate-300 uppercase tracking-wider">
          Muscle Focus
        </h3>
      </div>

      <div className="grid grid-cols-2 gap-4 items-center">
        {/* Human Silhouette Graphic SVG */}
        <div className="flex justify-center py-2">
          <svg className="h-28 w-24 text-slate-700" viewBox="0 0 100 150" fill="none">
            {/* Head */}
            <circle cx="50" cy="18" r="10" stroke="currentColor" strokeWidth="2" fill="#0f172a" />
            {/* Torso */}
            <path
              d="M32 35 L 68 35 L 62 85 L 38 85 Z"
              stroke="currentColor"
              strokeWidth="2"
              fill="#0f172a"
            />
            {/* Arms */}
            <path d="M30 35 L 18 80 M 70 35 L 82 80" stroke="currentColor" strokeWidth="3" />
            {/* Legs */}
            <path d="M42 85 L 38 140 M 58 85 L 62 140" stroke="currentColor" strokeWidth="4" />
            
            {/* Highlighted Chest Muscle Group (Red/Orange Glowing Path) */}
            <path
              d="M35 40 Q 50 48, 65 40 L 62 58 Q 50 64, 38 58 Z"
              fill="#ef4444"
              stroke="#f97316"
              strokeWidth="1.5"
              className="animate-pulse"
            />
          </svg>
        </div>

        {/* Legend Table */}
        <div className="space-y-2 text-xs font-mono">
          <div>
            <span className="text-[10px] text-slate-500 uppercase block font-bold">Primary</span>
            <span className="flex items-center gap-1.5 text-red-400 font-extrabold">
              <span className="h-2 w-2 rounded-full bg-red-500" /> Chest
            </span>
          </div>

          <div>
            <span className="text-[10px] text-slate-500 uppercase block font-bold">Secondary</span>
            <span className="flex items-center gap-1.5 text-amber-400 font-bold">
              <span className="h-2 w-2 rounded-full bg-amber-500" /> Shoulders
            </span>
            <span className="flex items-center gap-1.5 text-amber-400 font-bold">
              <span className="h-2 w-2 rounded-full bg-amber-500" /> Triceps
            </span>
          </div>

          <div>
            <span className="text-[10px] text-slate-500 uppercase block font-bold">Stabilizers</span>
            <span className="text-slate-400 text-[11px] block">• Core</span>
            <span className="text-slate-400 text-[11px] block">• Back</span>
          </div>
        </div>
      </div>
    </div>
  )
}
