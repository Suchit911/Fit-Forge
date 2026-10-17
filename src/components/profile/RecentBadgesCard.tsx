import React from 'react'
import { Award, ChevronRight } from 'lucide-react'

export interface RecentBadgesCardProps {
  onViewAllClick: () => void
  badges?: Array<{
    title: string
    desc: string
    time: string
    icon: React.ReactNode
    color: string
  }>
}

export const RecentBadgesCard: React.FC<RecentBadgesCardProps> = ({ onViewAllClick, badges = [] }) => {
  return (
    <div className="rounded-3xl border border-slate-800 bg-slate-900/90 p-5 space-y-4 text-left shadow-2xl h-full flex flex-col justify-between">
      <div className="flex items-center justify-between pb-2 border-b border-slate-800/80">
        <h3 className="text-sm font-extrabold text-slate-100">Recent Badges Earned</h3>
        <button
          type="button"
          onClick={onViewAllClick}
          className="text-xs font-semibold text-emerald-400 hover:text-emerald-300 cursor-pointer"
        >
          View All
        </button>
      </div>

      <div className="relative">
        {badges.length === 0 ? (
          <div className="flex flex-col items-center justify-center p-8 text-center space-y-2 rounded-2xl bg-slate-950/40 border border-slate-800/60">
            <Award className="h-8 w-8 text-slate-600" />
            <p className="text-xs font-bold text-slate-300">No Badges Earned Yet</p>
            <p className="text-[11px] text-slate-500 max-w-sm">
              Complete your first workout sessions and hit nutrition goals to unlock milestone badges.
            </p>
          </div>
        ) : (
          <div className="grid grid-cols-1 sm:grid-cols-2 md:grid-cols-5 gap-3 font-mono">
            {badges.map((b, idx) => (
              <div
                key={idx}
                className="rounded-2xl border border-slate-800 bg-slate-950/70 p-3 space-y-2 text-center flex flex-col items-center justify-between hover:border-slate-700 transition-colors cursor-pointer"
              >
                <div
                  className="relative flex h-10 w-9 items-center justify-center shrink-0 my-0.5"
                  style={{ color: b.color }}
                >
                  <svg className="absolute inset-0 h-full w-full" viewBox="0 0 100 115" fill="none">
                    <path
                      d="M50 0 L100 28.87 L100 86.6 L50 115.47 L0 86.6 L0 28.87 Z"
                      fill="#0f172a"
                      stroke={b.color}
                      strokeWidth="8"
                    />
                  </svg>
                  <div className="relative z-10">{b.icon}</div>
                </div>

                <div className="space-y-0.5 font-sans">
                  <h4 className="text-xs font-extrabold text-slate-100 line-clamp-1">{b.title}</h4>
                  <p className="text-[9px] text-slate-400 line-clamp-2 leading-tight">{b.desc}</p>
                  <span className="text-[9px] font-mono text-emerald-400 font-bold block pt-1">{b.time}</span>
                </div>
              </div>
            ))}
          </div>
        )}

        {badges.length > 5 && (
          <button
            type="button"
            aria-label="Next badges"
            className="absolute -right-3 top-1/2 -translate-y-1/2 hidden md:flex h-7 w-7 items-center justify-center rounded-full bg-slate-900 border border-slate-700 text-slate-300 shadow-xl hover:text-emerald-400 cursor-pointer"
          >
            <ChevronRight className="h-4 w-4" />
          </button>
        )}
      </div>
    </div>
  )
}
