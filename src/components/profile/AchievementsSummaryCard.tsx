import React from 'react'
import { Calendar, BicepsFlexed, Flame, Moon, Target, Lock } from 'lucide-react'

export interface AchievementsSummaryCardProps {
  onViewAllClick: () => void
  totalBadges?: number
  totalPoints?: number
  rank?: string
}

export const AchievementsSummaryCard: React.FC<AchievementsSummaryCardProps> = ({
  onViewAllClick,
  totalBadges = 0,
  totalPoints = 0,
  rank = 'Unranked',
}) => {
  const badgeDefinitions = [
    { title: 'Week Warrior', icon: <Calendar className="h-4 w-4" />, color: '#10b981' },
    { title: 'Strength Builder', icon: <BicepsFlexed className="h-4 w-4" />, color: '#f59e0b' },
    { title: 'Calorie Crusher', icon: <Flame className="h-4 w-4" />, color: '#3b82f6' },
    { title: 'Early Riser', icon: <Moon className="h-4 w-4" />, color: '#a855f7' },
    { title: 'Consistency King', icon: <Target className="h-4 w-4" />, color: '#f97316' },
  ]

  const hasBadges = totalBadges > 0

  return (
    <div className="rounded-3xl border border-slate-800 bg-slate-900/90 p-5 space-y-3.5 text-left shadow-2xl h-full flex flex-col justify-between">
      <div className="flex items-center justify-between pb-2 border-b border-slate-800/80">
        <h3 className="text-sm font-extrabold text-slate-100">Achievements Summary</h3>
        <button
          type="button"
          onClick={onViewAllClick}
          className="text-xs font-semibold text-emerald-400 hover:text-emerald-300 cursor-pointer"
        >
          View All
        </button>
      </div>

      {/* 5 Hexagonal Badges Strip */}
      <div className="flex items-center justify-around gap-2">
        {badgeDefinitions.map((b, idx) => {
          const isUnlocked = idx < totalBadges
          return (
            <div
              key={idx}
              className="relative flex h-10 w-9 items-center justify-center transition-opacity"
              style={{ color: isUnlocked ? b.color : '#64748b' }}
              title={isUnlocked ? b.title : `${b.title} (Locked)`}
            >
              <svg className="absolute inset-0 h-full w-full" viewBox="0 0 100 115" fill="none">
                <path
                  d="M50 0 L100 28.87 L100 86.6 L50 115.47 L0 86.6 L0 28.87 Z"
                  fill="#0f172a"
                  stroke={isUnlocked ? b.color : '#334155'}
                  strokeWidth="8"
                />
              </svg>
              <div className="relative z-10">
                {isUnlocked ? b.icon : <Lock className="h-3.5 w-3.5 text-slate-600" />}
              </div>
            </div>
          )
        })}
      </div>

      {/* Bottom 4 Metrics */}
      <div className="grid grid-cols-4 gap-2 pt-2 border-t border-slate-800/80 font-mono text-center">
        <div>
          <span className="text-[9px] text-slate-400 font-bold block">Total Badges</span>
          <span className="text-base font-extrabold text-slate-100 block">{totalBadges}</span>
        </div>

        <div>
          <span className="text-[9px] text-slate-400 font-bold block">Total Points</span>
          <span className="text-base font-extrabold text-slate-100 block">{totalPoints.toLocaleString()}</span>
        </div>

        <div>
          <span className="text-[9px] text-slate-400 font-bold block">Current Rank</span>
          <span className="text-base font-extrabold text-emerald-400 block text-[11px] pt-0.5">{rank}</span>
        </div>

        <div className="space-y-0.5 text-left pl-1">
          <span className="text-[9px] text-slate-400 font-bold block">Next Milestone</span>
          <div className="flex items-center gap-1">
            <span className="text-[9px] font-bold text-purple-400">Lvl {hasBadges ? 2 : 1}</span>
            <span className="text-[9px] font-bold text-slate-200 truncate">{hasBadges ? 'Bronze' : 'Novice'}</span>
          </div>
          <div className="w-full h-1 bg-slate-950 rounded-full overflow-hidden border border-slate-800">
            <div
              className="h-full bg-purple-500 rounded-full"
              style={{ width: `${Math.min(100, Math.round((totalPoints / 1000) * 100))}%` }}
            />
          </div>
          <span className="text-[8px] text-slate-500 block text-right">
            {Math.max(0, 1000 - totalPoints)} pts to go
          </span>
        </div>
      </div>
    </div>
  )
}
