import React from 'react'

export interface HowToPerformCardProps {
  instructions?: string[]
}

export const HowToPerformCard: React.FC<HowToPerformCardProps> = ({ instructions = [] }) => {
  return (
    <div className="rounded-3xl border border-slate-800 bg-slate-900/90 p-6 space-y-4 text-left">
      <h3 className="text-base font-extrabold text-slate-100">How to Perform</h3>

      {instructions.length === 0 ? (
        <p className="text-xs text-slate-400">No specific instructions recorded for this exercise.</p>
      ) : (
        <div className="space-y-3.5">
          {instructions.map((step, idx) => (
            <div key={idx} className="flex items-start gap-3 text-xs leading-relaxed">
              <div className="flex h-5 w-5 items-center justify-center rounded-full bg-emerald-500/20 border border-emerald-500/40 font-mono font-bold text-emerald-400 text-[10px] shrink-0 mt-0.5">
                {idx + 1}
              </div>
              <p className="text-slate-300 font-medium">{step}</p>
            </div>
          ))}
        </div>
      )}
    </div>
  )
}

