import React from 'react'
import type { CurrentChallengeItem } from '../../types'
import { Dumbbell, Flame, Trophy, Target, ChevronRight } from 'lucide-react'

export interface CurrentChallengesSectionProps {
  challenges: CurrentChallengeItem[]
}

export const CurrentChallengesSection: React.FC<CurrentChallengesSectionProps> = ({ challenges }) => {
  const getIcon = (iconName: string) => {
    switch (iconName) {
      case 'dumbbell':
        return <Dumbbell className="h-5 w-5 text-emerald-400" />
      case 'flame':
        return <Flame className="h-5 w-5 text-blue-400" />
      case 'trophy':
        return <Trophy className="h-5 w-5 text-purple-400" />
      default:
        return <Target className="h-5 w-5 text-amber-400" />
    }
  }

  return (
    <div className="rounded-3xl border border-slate-800 bg-slate-900/90 p-5 space-y-4 text-left shadow-2xl">
      <div className="flex items-center justify-between pb-2 border-b border-slate-800/80">
        <h3 className="text-sm font-extrabold text-slate-100">Current Challenges</h3>
        <button type="button" className="text-xs font-semibold text-emerald-400 hover:text-emerald-300">
          View All
        </button>
      </div>

      <div className="relative">
        {challenges.length === 0 ? (
          <div className="flex flex-col items-center justify-center p-8 rounded-2xl border border-dashed border-slate-800 bg-slate-950/40 text-center space-y-2 font-mono">
            <Target className="h-8 w-8 text-slate-600" />
            <h4 className="text-xs font-bold text-slate-300">No Active Challenges</h4>
            <p className="text-[10px] text-slate-500 max-w-sm">
              Community and monthly challenges will appear here once active. Complete workouts to earn standard achievement badges.
            </p>
          </div>
        ) : (
          <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-4 gap-3 font-mono">
            {challenges.map((ch) => {
              const pct = Math.round((ch.current / ch.target) * 100)

              return (
                <div
                  key={ch.id}
                  className="group rounded-2xl border border-slate-800 bg-slate-950/70 p-4 space-y-3 hover:border-slate-700 transition-colors cursor-pointer flex flex-col justify-between"
                >
                  <div className="flex items-start gap-3">
                    <div
                      className="relative flex h-10 w-9 items-center justify-center shrink-0 my-0.5"
                      style={{ color: ch.color }}
                    >
                      <svg className="absolute inset-0 h-full w-full" viewBox="0 0 100 115" fill="none">
                        <path
                          d="M50 0 L100 28.87 L100 86.6 L50 115.47 L0 86.6 L0 28.87 Z"
                          fill="#0f172a"
                          stroke={ch.color}
                          strokeWidth="8"
                        />
                      </svg>
                      <div className="relative z-10">{getIcon(ch.iconName)}</div>
                    </div>

                    <div className="space-y-0.5 font-sans">
                      <h4 className="text-xs font-extrabold text-slate-100 group-hover:text-emerald-400 transition-colors">
                        {ch.title}
                      </h4>
                      <p className="text-[10px] text-slate-400 line-clamp-1">{ch.description}</p>
                    </div>
                  </div>

                  <div className="space-y-1 pt-1 border-t border-slate-800/60">
                    <div className="flex justify-between text-[10px] text-slate-400">
                      <span className="font-bold text-slate-200">
                        {ch.current.toLocaleString()} / {ch.target.toLocaleString()}
                      </span>
                      <span className="font-bold text-emerald-400">{ch.daysLeft} days left</span>
                    </div>

                    <div className="w-full h-1.5 bg-slate-900 rounded-full overflow-hidden border border-slate-800">
                      <div
                        className="h-full rounded-full"
                        style={{ width: `${pct}%`, backgroundColor: ch.color }}
                      />
                    </div>
                  </div>
                </div>
              )
            })}
          </div>
        )}

        {/* Carousel Chevron Right */}
        {challenges.length > 4 && (
          <button
            type="button"
            aria-label="Next challenges"
            className="absolute -right-3 top-1/2 -translate-y-1/2 hidden lg:flex h-7 w-7 items-center justify-center rounded-full bg-slate-900 border border-slate-700 text-slate-300 shadow-xl hover:text-emerald-400 cursor-pointer"
          >
            <ChevronRight className="h-4 w-4" />
          </button>
        )}
      </div>
    </div>
  )
}
