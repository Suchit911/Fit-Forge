import React from 'react'
import type { AchievementCategoryItem } from '../../types'
import { Dumbbell, BicepsFlexed, Activity, Calendar, Apple, Heart, Star, Trophy } from 'lucide-react'

export interface AchievementCategoriesSectionProps {
  categories: AchievementCategoryItem[]
}

export const AchievementCategoriesSection: React.FC<AchievementCategoriesSectionProps> = ({ categories }) => {
  const getIcon = (iconName: string) => {
    switch (iconName) {
      case 'dumbbell':
        return <Dumbbell className="h-4 w-4 text-emerald-400" />
      case 'biceps':
        return <BicepsFlexed className="h-4 w-4 text-amber-400" />
      case 'running':
        return <Activity className="h-4 w-4 text-blue-400" />
      case 'calendar':
        return <Calendar className="h-4 w-4 text-purple-400" />
      case 'apple':
        return <Apple className="h-4 w-4 text-emerald-400" />
      case 'heart':
        return <Heart className="h-4 w-4 text-orange-400" />
      case 'star':
        return <Star className="h-4 w-4 text-cyan-400" />
      default:
        return <Trophy className="h-4 w-4 text-pink-400" />
    }
  }

  return (
    <div className="rounded-3xl border border-slate-800 bg-slate-900/90 p-5 space-y-4 text-left shadow-2xl h-full flex flex-col justify-between">
      <div className="flex items-center justify-between pb-2 border-b border-slate-800/80">
        <h3 className="text-sm font-extrabold text-slate-100">Achievement Categories</h3>
        <button type="button" className="text-xs font-semibold text-emerald-400 hover:text-emerald-300">
          View All
        </button>
      </div>

      <div className="grid grid-cols-2 sm:grid-cols-4 gap-3 font-mono">
        {categories.map((cat) => (
          <div
            key={cat.id}
            className="rounded-2xl border border-slate-800 bg-slate-950/70 p-3 space-y-2 hover:border-slate-700 transition-colors cursor-pointer"
          >
            <div className="flex items-center justify-between">
              <div className="flex h-7 w-7 items-center justify-center rounded-lg border border-slate-800 bg-slate-900 shrink-0">
                {getIcon(cat.iconName)}
              </div>
              <span className="text-[10px] font-bold text-slate-400">{cat.current} / {cat.total}</span>
            </div>

            <div className="space-y-1">
              <h4 className="text-xs font-extrabold text-slate-100 truncate">{cat.title}</h4>
              <span className="text-[10px] text-slate-400 font-bold block">{cat.pct}% Complete</span>

              <div className="w-full h-1 bg-slate-900 rounded-full overflow-hidden border border-slate-800">
                <div
                  className="h-full rounded-full"
                  style={{ width: `${cat.pct}%`, backgroundColor: cat.color }}
                />
              </div>
            </div>
          </div>
        ))}
      </div>
    </div>
  )
}
