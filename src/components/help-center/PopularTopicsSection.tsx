import React from 'react'
import type { HelpTopicItem } from '../../types'
import { Rocket, Dumbbell, Activity, Utensils, Bot, TrendingUp } from 'lucide-react'

export interface PopularTopicsSectionProps {
  topics: HelpTopicItem[]
  onTopicClick: (topic: HelpTopicItem) => void
  onViewAllClick: () => void
}

export const PopularTopicsSection: React.FC<PopularTopicsSectionProps> = ({
  topics,
  onTopicClick,
  onViewAllClick,
}) => {
  const getIcon = (iconName: string) => {
    switch (iconName) {
      case 'rocket':
        return <Rocket className="h-5 w-5" />
      case 'dumbbell':
        return <Dumbbell className="h-5 w-5" />
      case 'running':
        return <Activity className="h-5 w-5" />
      case 'utensils':
        return <Utensils className="h-5 w-5" />
      case 'bot':
        return <Bot className="h-5 w-5" />
      default:
        return <TrendingUp className="h-5 w-5" />
    }
  }

  return (
    <div className="rounded-3xl border border-slate-800 bg-slate-900/90 p-5 space-y-4 text-left shadow-2xl">
      <div className="flex items-center justify-between pb-2 border-b border-slate-800/80">
        <h3 className="text-sm font-extrabold text-slate-100">Popular Topics</h3>
        <button
          type="button"
          onClick={onViewAllClick}
          className="text-xs font-semibold text-emerald-400 hover:text-emerald-300 cursor-pointer"
        >
          View All Topics
        </button>
      </div>

      <div className="grid grid-cols-2 sm:grid-cols-3 lg:grid-cols-6 gap-3">
        {topics.map((t) => (
          <div
            key={t.id}
            onClick={() => onTopicClick(t)}
            className="group rounded-2xl border border-slate-800 bg-slate-950/70 p-4 text-center space-y-2 flex flex-col items-center justify-between hover:border-slate-700 hover:shadow-lg transition-all cursor-pointer"
          >
            <div
              className="flex h-11 w-11 items-center justify-center rounded-2xl border border-slate-800 bg-slate-900 shadow-inner my-1 transition-transform group-hover:scale-110"
              style={{ color: t.color }}
            >
              {getIcon(t.iconName)}
            </div>

            <div className="space-y-0.5">
              <h4 className="text-xs font-extrabold text-slate-100 group-hover:text-emerald-400 transition-colors truncate">
                {t.title}
              </h4>
              <span className="text-[10px] font-mono text-slate-400 block">{t.articleCount} articles</span>
            </div>
          </div>
        ))}
      </div>
    </div>
  )
}
