import React from 'react'
import type { QuickHelpGuideItem } from '../../types'
import { Play, Video, Plus, Utensils, Bot, Watch } from 'lucide-react'

export interface QuickHelpSectionProps {
  guides: QuickHelpGuideItem[]
  onGuideClick: (guide: QuickHelpGuideItem) => void
  onViewAllClick: () => void
}

export const QuickHelpSection: React.FC<QuickHelpSectionProps> = ({
  guides,
  onGuideClick,
  onViewAllClick,
}) => {
  const getIcon = (iconName: string) => {
    switch (iconName) {
      case 'play':
        return <Play className="h-5 w-5 fill-current" />
      case 'video':
        return <Video className="h-5 w-5" />
      case 'plus':
        return <Plus className="h-5 w-5" />
      case 'utensils':
        return <Utensils className="h-5 w-5" />
      case 'bot':
        return <Bot className="h-5 w-5" />
      default:
        return <Watch className="h-5 w-5" />
    }
  }

  return (
    <div className="rounded-3xl border border-slate-800 bg-slate-900/90 p-5 space-y-4 text-left shadow-2xl">
      <div className="flex items-center justify-between pb-2 border-b border-slate-800/80">
        <h3 className="text-sm font-extrabold text-slate-100">Quick Help</h3>
        <button
          type="button"
          onClick={onViewAllClick}
          className="text-xs font-semibold text-emerald-400 hover:text-emerald-300 cursor-pointer"
        >
          View All Guides
        </button>
      </div>

      <div className="grid grid-cols-2 sm:grid-cols-3 lg:grid-cols-6 gap-3">
        {guides.map((g) => (
          <div
            key={g.id}
            onClick={() => onGuideClick(g)}
            className="group rounded-2xl border border-slate-800 bg-slate-950/70 p-4 text-center space-y-2 flex flex-col items-center justify-between hover:border-slate-700 hover:shadow-lg transition-all cursor-pointer min-h-[160px]"
          >
            <div
              className="flex h-11 w-11 items-center justify-center rounded-2xl border border-slate-800 bg-slate-900 shadow-inner my-1 transition-transform group-hover:scale-110"
              style={{ color: g.color }}
            >
              {getIcon(g.iconName)}
            </div>

            <div className="space-y-1 font-sans">
              <h4 className="text-xs font-extrabold text-slate-100 group-hover:text-emerald-400 transition-colors line-clamp-2 leading-tight">
                {g.title}
              </h4>
              <p className="text-[9px] text-slate-400 line-clamp-2 leading-tight">
                {g.description}
              </p>
            </div>

            <span className="text-[9px] font-mono font-bold text-emerald-400 block pt-1">
              {g.readTime}
            </span>
          </div>
        ))}
      </div>
    </div>
  )
}
