import React from 'react'
import type { RepAnalysisItem } from '../../types'

export interface RepProgressCardProps {
  reps: RepAnalysisItem[]
}

export const RepProgressCard: React.FC<RepProgressCardProps> = ({ reps = [] }) => {
  const completedCount = reps.length
  const goodCount = reps.filter((r) => r.status === 'good').length
  const improvementCount = reps.filter((r) => r.status === 'improvement').length
  const poorCount = reps.filter((r) => r.status === 'poor').length

  return (
    <div className="rounded-3xl border border-slate-800 bg-slate-900/90 p-5 space-y-4 text-left h-full flex flex-col justify-between">
      <div className="flex items-center justify-between pb-2 border-b border-slate-800/80">
        <h3 className="text-sm font-extrabold text-slate-100">Rep Progress</h3>
        <span className="text-xs font-mono font-bold text-slate-400">
          {completedCount === 0 ? '0 Reps Recorded' : `${completedCount} ${completedCount === 1 ? 'Rep' : 'Reps'} Completed`}
        </span>
      </div>

      {/* Rep Circles Row */}
      {reps.length === 0 ? (
        <div className="py-6 flex flex-col items-center justify-center text-center space-y-1 text-slate-500 font-mono text-xs">
          <p>No completed repetitions recorded.</p>
          <p className="text-[11px] text-slate-600">Start live camera stream and perform reps to observe tracking.</p>
        </div>
      ) : (
        <div className="flex flex-wrap items-center gap-2.5 py-2">
          {reps.map((r, idx) => {
            const isGood = r.status === 'good'
            const isImprovement = r.status === 'improvement'

            return (
              <div key={idx} className="flex flex-col items-center gap-1 font-mono">
                <div
                  className={`flex h-9 w-9 items-center justify-center rounded-full text-xs font-extrabold border transition-all ${
                    isGood
                      ? 'bg-emerald-500 text-slate-950 border-emerald-400 shadow-md shadow-emerald-950/40'
                      : isImprovement
                      ? 'bg-amber-500 text-slate-950 border-amber-400 shadow-md shadow-amber-950/40'
                      : 'bg-rose-500 text-slate-950 border-rose-400'
                  }`}
                >
                  {r.repNumber}
                </div>
                <span className="text-[10px] text-slate-400 font-bold">
                  {r.elbowAngle}°
                </span>
              </div>
            )
          })}
        </div>
      )}

      {/* Rep Analysis Legend */}
      <div className="pt-3 border-t border-slate-800/80 flex flex-wrap items-center justify-between text-[11px] font-mono">
        <span className="text-slate-400 font-bold">Rep Breakdown</span>
        <div className="flex flex-wrap items-center gap-3">
          <span className="flex items-center gap-1 text-slate-300">
            <span className="h-2 w-2 rounded-full bg-emerald-500" /> Good ({goodCount})
          </span>
          <span className="flex items-center gap-1 text-slate-300">
            <span className="h-2 w-2 rounded-full bg-amber-500" /> Needs Improvement ({improvementCount})
          </span>
          {poorCount > 0 && (
            <span className="flex items-center gap-1 text-slate-300">
              <span className="h-2 w-2 rounded-full bg-rose-500" /> Poor ({poorCount})
            </span>
          )}
        </div>
      </div>
    </div>
  )
}
