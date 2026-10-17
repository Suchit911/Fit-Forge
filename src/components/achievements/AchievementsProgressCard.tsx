import React from 'react'
import type { AchievementsProgressData } from '../../types'

export interface AchievementsProgressCardProps {
  progress: AchievementsProgressData
}

export const AchievementsProgressCard: React.FC<AchievementsProgressCardProps> = ({ progress }) => {
  const { overallPct, achievedCount, inProgressCount, lockedCount, nextMilestone } = progress

  return (
    <div className="rounded-3xl border border-slate-800 bg-slate-900/90 p-5 space-y-4 text-left shadow-2xl h-full flex flex-col justify-between">
      <h3 className="text-sm font-extrabold text-slate-100 pb-2 border-b border-slate-800/80">
        Achievements Progress
      </h3>

      {/* Circular Progress & Breakdown */}
      <div className="flex items-center justify-around gap-4 font-mono">
        <div className="relative flex items-center justify-center">
          <svg className="h-24 w-24 transform -rotate-90">
            <circle cx="48" cy="48" r="38" stroke="#1e293b" strokeWidth="6" fill="transparent" />
            <circle
              cx="48"
              cy="48"
              r="38"
              stroke="#10b981"
              strokeWidth="6"
              strokeDasharray="238"
              strokeDashoffset={238 - (238 * overallPct) / 100}
              strokeLinecap="round"
              fill="transparent"
            />
          </svg>
          <div className="absolute text-center">
            <span className="text-xl font-extrabold text-slate-100 block">{overallPct}%</span>
            <span className="text-[9px] text-slate-400 font-sans block">Overall Progress</span>
          </div>
        </div>

        <div className="space-y-1.5 text-xs">
          <div className="flex items-center gap-2">
            <span className="h-2.5 w-2.5 rounded-full bg-emerald-500" />
            <span className="font-extrabold text-slate-100">{achievedCount}</span>
            <span className="text-slate-400 text-[11px]">Achieved</span>
          </div>

          <div className="flex items-center gap-2">
            <span className="h-2.5 w-2.5 rounded-full bg-amber-500" />
            <span className="font-extrabold text-slate-100">{inProgressCount}</span>
            <span className="text-slate-400 text-[11px]">In Progress</span>
          </div>

          <div className="flex items-center gap-2">
            <span className="h-2.5 w-2.5 rounded-full bg-slate-600" />
            <span className="font-extrabold text-slate-100">{lockedCount}</span>
            <span className="text-slate-400 text-[11px]">Locked</span>
          </div>
        </div>
      </div>

      {/* Next Milestone Box */}
      <div className="rounded-2xl border border-purple-500/30 bg-purple-950/20 p-3.5 space-y-2 font-mono">
        <div className="flex items-center justify-between">
          <span className="text-[10px] text-slate-400 font-bold uppercase">Next Milestone</span>
          <span className="text-[10px] text-purple-400 font-bold">{nextMilestone.ptsToGo} pts to go</span>
        </div>

        <div className="flex items-center gap-3">
          <div className="relative flex h-10 w-10 items-center justify-center text-purple-400 font-extrabold shrink-0">
            <svg className="absolute inset-0 h-full w-full" viewBox="0 0 100 115" fill="none">
              <path
                d="M50 0 L100 28.87 L100 86.6 L50 115.47 L0 86.6 L0 28.87 Z"
                fill="#1e1b4b"
                stroke="#a855f7"
                strokeWidth="8"
              />
            </svg>
            <span className="relative z-10 text-xs">{nextMilestone.level}</span>
          </div>

          <div className="space-y-0.5 font-sans">
            <h4 className="text-xs font-extrabold text-slate-100">{nextMilestone.title}</h4>
            <p className="text-[10px] text-slate-400">{nextMilestone.description}</p>
          </div>
        </div>

        <div className="space-y-1 pt-1">
          <div className="flex justify-between text-[10px] text-slate-400">
            <span>Progress</span>
            <span className="font-extrabold text-slate-200">
              {nextMilestone.currentPts.toLocaleString()} / {nextMilestone.targetPts.toLocaleString()}
            </span>
          </div>
          <div className="w-full h-1.5 bg-slate-900 rounded-full overflow-hidden border border-slate-800">
            <div
              className="h-full bg-purple-500 rounded-full"
              style={{ width: `${(nextMilestone.currentPts / nextMilestone.targetPts) * 100}%` }}
            />
          </div>
        </div>
      </div>
    </div>
  )
}
