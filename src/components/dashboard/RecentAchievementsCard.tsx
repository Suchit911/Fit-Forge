import React from 'react'
import { Link } from 'react-router-dom'
import { Award, Flame, Star, Trophy, Dumbbell, Calendar, Target, Moon } from 'lucide-react'
import { useAchievements } from '../../hooks'

export const RecentAchievementsCard: React.FC = () => {
  const { dashboardData, isLoading } = useAchievements()

  const getIcon = (iconName: string) => {
    switch (iconName) {
      case 'dumbbell':
        return Dumbbell
      case 'flame':
        return Flame
      case 'calendar':
        return Calendar
      case 'moon':
        return Moon
      case 'target':
        return Target
      case 'star':
        return Star
      case 'trophy':
        return Trophy
      default:
        return Award
    }
  }

  const recentAchievements = dashboardData?.recentAchievements || []

  return (
    <div className="rounded-2xl border border-slate-800 bg-slate-900/90 p-5 text-left flex flex-col justify-between space-y-4">
      {/* Header */}
      <div className="flex items-center justify-between pb-3 border-b border-slate-800/80">
        <h3 className="text-sm font-extrabold text-slate-100">Recent Achievements</h3>
        <Link
          to="/achievements"
          className="text-xs font-semibold text-slate-400 hover:text-slate-200 transition-colors"
        >
          See All
        </Link>
      </div>

      {/* Achievement Item Rows */}
      {isLoading ? (
        <div className="space-y-3">
          {[1, 2, 3].map((i) => (
            <div key={i} className="h-14 rounded-xl bg-slate-950/40 border border-slate-800/50 animate-pulse" />
          ))}
        </div>
      ) : recentAchievements.length === 0 ? (
        <div className="flex flex-col items-center justify-center p-6 text-center space-y-2 rounded-xl bg-slate-950/40 border border-slate-800/60">
          <Award className="h-7 w-7 text-slate-600" />
          <p className="text-xs font-bold text-slate-300">No Achievements Yet</p>
          <p className="text-[10px] text-slate-500">
            Complete workouts and hit nutrition goals to unlock milestone badges.
          </p>
        </div>
      ) : (
        <div className="space-y-3">
          {recentAchievements.slice(0, 3).map((item) => {
            const Icon = getIcon(item.iconName)
            return (
              <div
                key={item.id}
                className="flex items-center justify-between p-3 rounded-xl bg-slate-950/70 border border-slate-800/80 hover:border-slate-700 transition-colors"
              >
                <div className="flex items-center gap-3">
                  <div
                    className="flex h-9 w-9 items-center justify-center rounded-xl border shrink-0"
                    style={{
                      borderColor: item.color ? `${item.color}40` : '#a855f740',
                      backgroundColor: item.color ? `${item.color}15` : '#a855f715',
                      color: item.color || '#a855f7',
                    }}
                  >
                    <Icon className="h-4 w-4" />
                  </div>
                  <div className="min-w-0">
                    <h5 className="text-xs font-bold text-slate-100 truncate">{item.title}</h5>
                    <p className="text-[10px] text-slate-400 truncate">{item.description}</p>
                  </div>
                </div>
                <span className="text-[10px] font-mono text-slate-500 shrink-0 ml-2">{item.timeAgo}</span>
              </div>
            )
          })}
        </div>
      )}
    </div>
  )
}
