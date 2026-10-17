import React from 'react'
import type { RecentAchievementBadge } from '../../types'
import {
  Calendar,
  BicepsFlexed,
  Flame,
  Moon,
  Target,
  TrendingUp,
  ChevronLeft,
  ChevronRight,
  Award,
  Trophy,
  Star,
  Dumbbell,
  Apple,
  Droplets,
  Heart,
  Zap,
} from 'lucide-react'

export interface RecentAchievementsSectionProps {
  badges: RecentAchievementBadge[]
}

export const RecentAchievementsSection: React.FC<RecentAchievementsSectionProps> = ({ badges }) => {
  const getIcon = (iconName: string) => {
    switch (iconName) {
      case 'calendar':
        return <Calendar className="h-5 w-5" />
      case 'biceps':
        return <BicepsFlexed className="h-5 w-5" />
      case 'dumbbell':
        return <Dumbbell className="h-5 w-5" />
      case 'flame':
        return <Flame className="h-5 w-5" />
      case 'moon':
        return <Moon className="h-5 w-5" />
      case 'star':
        return <Star className="h-5 w-5" />
      case 'trophy':
        return <Trophy className="h-5 w-5" />
      case 'apple':
        return <Apple className="h-5 w-5" />
      case 'droplets':
        return <Droplets className="h-5 w-5" />
      case 'heart':
        return <Heart className="h-5 w-5" />
      case 'zap':
        return <Zap className="h-5 w-5" />
      case 'target':
        return <Target className="h-5 w-5" />
      case 'award':
        return <Award className="h-5 w-5" />
      default:
        return <TrendingUp className="h-5 w-5" />
    }
  }

  return (
    <div className="rounded-3xl border border-slate-800 bg-slate-900/90 p-5 space-y-4 text-left shadow-2xl h-full flex flex-col justify-between">
      <div className="flex items-center justify-between pb-2 border-b border-slate-800/80">
        <h3 className="text-sm font-extrabold text-slate-100">Recent Achievements</h3>
        <button type="button" className="text-xs font-semibold text-emerald-400 hover:text-emerald-300">
          View All
        </button>
      </div>

      <div className="relative">
        {badges.length === 0 ? (
          <div className="flex flex-col items-center justify-center p-8 rounded-2xl border border-dashed border-slate-800 bg-slate-950/40 text-center space-y-2">
            <Award className="h-8 w-8 text-slate-600" />
            <h4 className="text-xs font-bold text-slate-300">No Achievements Unlocked Yet</h4>
            <p className="text-[10px] text-slate-500 max-w-sm">
              Complete your first workout or log your meals to earn your first badges!
            </p>
          </div>
        ) : (
          <div className="grid grid-cols-2 sm:grid-cols-3 lg:grid-cols-6 gap-3">
            {badges.map((badge) => (
              <div
                key={badge.id}
                className="relative group rounded-2xl border border-slate-800 bg-slate-950/70 p-3.5 text-center space-y-2 flex flex-col items-center justify-between hover:border-slate-700 transition-all cursor-pointer"
              >
                {badge.isNew && (
                  <span className="absolute -top-2 left-1/2 -translate-x-1/2 px-1.5 py-0.5 rounded-full bg-emerald-500 text-[8px] font-extrabold text-slate-950 uppercase tracking-wider shadow-sm">
                    NEW
                  </span>
                )}

                {/* Hexagonal Badge Illustration */}
                <div
                  className="relative flex h-14 w-12 items-center justify-center my-1 transition-transform group-hover:scale-110"
                  style={{ color: badge.color }}
                >
                  <svg className="absolute inset-0 h-full w-full" viewBox="0 0 100 115" fill="none">
                    <path
                      d="M50 0 L100 28.87 L100 86.6 L50 115.47 L0 86.6 L0 28.87 Z"
                      fill="#0f172a"
                      stroke={badge.color}
                      strokeWidth="8"
                    />
                  </svg>
                  <div className="relative z-10">{getIcon(badge.iconName)}</div>
                </div>

                <div className="space-y-1">
                  <h4 className="text-xs font-extrabold text-slate-100 group-hover:text-emerald-400 transition-colors line-clamp-1">
                    {badge.title}
                  </h4>
                  <p className="text-[10px] text-slate-400 font-medium line-clamp-2 leading-tight">
                    {badge.description}
                  </p>
                  <span className="text-[9px] font-mono text-emerald-400 font-bold block pt-1">
                    {badge.timeAgo}
                  </span>
                </div>
              </div>
            ))}
          </div>
        )}

        {/* Carousel Chevrons */}
        {badges.length > 6 && (
          <>
            <button
              type="button"
              aria-label="Previous"
              className="absolute -left-3 top-1/2 -translate-y-1/2 hidden lg:flex h-7 w-7 items-center justify-center rounded-full bg-slate-900 border border-slate-700 text-slate-300 shadow-xl hover:text-emerald-400 cursor-pointer"
            >
              <ChevronLeft className="h-4 w-4" />
            </button>
            <button
              type="button"
              aria-label="Next"
              className="absolute -right-3 top-1/2 -translate-y-1/2 hidden lg:flex h-7 w-7 items-center justify-center rounded-full bg-slate-900 border border-slate-700 text-slate-300 shadow-xl hover:text-emerald-400 cursor-pointer"
            >
              <ChevronRight className="h-4 w-4" />
            </button>
          </>
        )}
      </div>
    </div>
  )
}
