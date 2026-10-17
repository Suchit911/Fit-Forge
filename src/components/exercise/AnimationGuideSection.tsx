import React, { useState } from 'react'
import { Play } from 'lucide-react'

export const AnimationGuideSection: React.FC = () => {
  const [activeFrame, setActiveFrame] = useState(1)

  const frames = [
    { id: 1, label: '1. Start Position', image: '/assets/bench_press_anim_1.jpg' },
    { id: 2, label: '2. Lower Bar', image: '/assets/dashboard_push_lifter.jpg' },
    { id: 3, label: '3. Chest Contact', image: '/assets/workout_lower_body.jpg' },
    { id: 4, label: '4. Press Up', image: '/assets/workout_upper_pull.jpg' },
    { id: 5, label: '5. Lockout', image: '/assets/workout_hiit_ropes.jpg' },
  ]

  return (
    <div className="space-y-3 text-left">
      <h3 className="text-base font-extrabold text-slate-100">Animation Guide</h3>

      <div className="grid grid-cols-2 sm:grid-cols-5 gap-3">
        {frames.map((frame) => {
          const isActive = frame.id === activeFrame

          return (
            <div
              key={frame.id}
              onClick={() => setActiveFrame(frame.id)}
              className={`group relative rounded-2xl border overflow-hidden transition-all cursor-pointer ${
                isActive
                  ? 'border-emerald-500 bg-slate-900 shadow-lg shadow-emerald-950/40 ring-1 ring-emerald-500'
                  : 'border-slate-800 bg-slate-950/70 hover:border-slate-700'
              }`}
            >
              <div className="relative aspect-[16/10] w-full overflow-hidden bg-slate-950">
                <img
                  src={frame.image}
                  alt={frame.label}
                  className="w-full h-full object-cover opacity-80 group-hover:scale-105 transition-transform duration-300"
                />
                <div className="absolute inset-0 bg-gradient-to-t from-slate-950/80 via-transparent to-transparent" />

                {isActive && (
                  <div className="absolute top-1/2 left-1/2 -translate-x-1/2 -translate-y-1/2 flex h-8 w-8 items-center justify-center rounded-full bg-emerald-500 text-slate-950 shadow-md">
                    <Play className="h-3.5 w-3.5 fill-slate-950 ml-0.5" />
                  </div>
                )}
              </div>

              <div className="p-2 text-center">
                <span
                  className={`text-[10px] font-mono font-bold truncate block ${
                    isActive ? 'text-emerald-400' : 'text-slate-400'
                  }`}
                >
                  {frame.label}
                </span>
              </div>
            </div>
          )
        })}
      </div>
    </div>
  )
}
