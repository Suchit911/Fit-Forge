import React, { useState } from 'react'
import type { LeaderboardUser } from '../../types'
import { Crown, ChevronRight, User as UserIcon } from 'lucide-react'

export interface LeaderboardCardProps {
  users: LeaderboardUser[]
}

export const LeaderboardCard: React.FC<LeaderboardCardProps> = ({ users }) => {
  const [activeTab, setActiveTab] = useState('Points')
  const tabs = ['Points', 'Streaks', 'Challenges']

  const getRankBadge = (rank?: number | null) => {
    if (rank == null) {
      return <span className="text-[10px] font-extrabold text-slate-500 px-1">-</span>
    }
    switch (rank) {
      case 1:
        return (
          <div className="flex h-5 w-5 items-center justify-center rounded-full bg-amber-500 text-slate-950 font-extrabold text-[10px]">
            1
          </div>
        )
      case 2:
        return (
          <div className="flex h-5 w-5 items-center justify-center rounded-full bg-slate-300 text-slate-950 font-extrabold text-[10px]">
            2
          </div>
        )
      case 3:
        return (
          <div className="flex h-5 w-5 items-center justify-center rounded-full bg-amber-700 text-slate-100 font-extrabold text-[10px]">
            3
          </div>
        )
      default:
        return <span className="text-[10px] font-extrabold text-slate-500 px-1">{rank}</span>
    }
  }

  return (
    <div className="rounded-3xl border border-slate-800 bg-slate-900/90 p-5 space-y-3.5 text-left shadow-2xl h-full flex flex-col justify-between">
      <div className="space-y-3">
        <div className="flex items-center justify-between pb-2 border-b border-slate-800/80">
          <h3 className="text-sm font-extrabold text-slate-100">Leaderboards</h3>
          <button type="button" className="text-xs font-semibold text-emerald-400 hover:text-emerald-300">
            View All
          </button>
        </div>

        {/* Tabs */}
        <div className="flex items-center gap-4 border-b border-slate-800/80 pb-2 text-xs font-mono">
          {tabs.map((tab) => (
            <button
              key={tab}
              type="button"
              onClick={() => setActiveTab(tab)}
              className={`font-bold transition-colors cursor-pointer ${
                activeTab === tab ? 'text-emerald-400 border-b-2 border-emerald-500 pb-1' : 'text-slate-400 hover:text-slate-200'
              }`}
            >
              {tab}
            </button>
          ))}
        </div>

        {/* Rows */}
        <div className="space-y-2 font-mono text-xs">
          {users.length === 0 ? (
            <div className="flex flex-col items-center justify-center p-6 rounded-2xl border border-dashed border-slate-800 bg-slate-950/40 text-center space-y-1">
              <UserIcon className="h-6 w-6 text-slate-600 mb-1" />
              <p className="text-xs font-bold text-slate-300">No Leaderboard Data</p>
              <p className="text-[10px] text-slate-500">
                Unlock your first achievement to join the points ranking.
              </p>
            </div>
          ) : (
            users.map((u) => (
              <div
                key={u.rank}
                className={`flex items-center justify-between p-2 rounded-2xl border transition-colors ${
                  u.isCurrentUser
                    ? 'border-emerald-500/50 bg-emerald-950/30'
                    : 'border-slate-800/60 bg-slate-950/40 hover:border-slate-700'
                }`}
              >
                <div className="flex items-center gap-2.5">
                  {getRankBadge(u.rank)}

                  <div className="flex h-7 w-7 items-center justify-center rounded-full bg-slate-800 text-slate-300 font-bold shrink-0">
                    <UserIcon className="h-3.5 w-3.5" />
                  </div>

                  <span
                    className={`text-xs font-bold ${
                      u.isCurrentUser ? 'text-emerald-400' : 'text-slate-200'
                    }`}
                  >
                    {u.name}
                  </span>
                </div>

                <div className="flex items-center gap-1">
                  <span className="font-extrabold text-slate-100">{u.pointsStr}</span>
                  {u.rank === 1 && <Crown className="h-3.5 w-3.5 text-amber-400" />}
                </div>
              </div>
            ))
          )}
        </div>
      </div>

      {/* Footer */}
      <div className="pt-2 border-t border-slate-800/80 flex items-center justify-between text-xs font-mono">
        <span className="text-slate-400 text-[10px]">
          Your Rank:{' '}
          <strong className="text-slate-300">
            {(() => {
              const current = users.find((u) => u.isCurrentUser)
              return current && current.rank != null ? `#${current.rank}` : 'Unranked'
            })()}
          </strong>
        </span>
        <button type="button" className="flex items-center gap-1 text-[10px] text-emerald-400 font-bold hover:text-emerald-300">
          View Full Leaderboard <ChevronRight className="h-3.5 w-3.5" />
        </button>
      </div>
    </div>
  )
}
