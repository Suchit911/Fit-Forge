import React from 'react'
import { Calendar, ChevronDown } from 'lucide-react'

export interface AchievementsTabsProps {
  activeTab: string
  onTabChange: (tab: string) => void
  currentFilter: string
}

export const AchievementsTabs: React.FC<AchievementsTabsProps> = ({
  activeTab,
  onTabChange,
  currentFilter,
}) => {
  const tabs = ['Overview', 'Badges', 'Challenges', 'Milestones', 'Collections']

  return (
    <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-4 border-b border-slate-800/80 pb-3 text-left">
      {/* Left Tabs */}
      <div className="flex items-center gap-6 overflow-x-auto">
        {tabs.map((tab) => (
          <button
            key={tab}
            type="button"
            onClick={() => onTabChange(tab)}
            className={`relative text-xs font-bold transition-all cursor-pointer whitespace-nowrap ${
              activeTab === tab
                ? 'text-emerald-400 font-extrabold'
                : 'text-slate-400 hover:text-slate-200 font-medium'
            }`}
          >
            {tab}
            {activeTab === tab && (
              <span className="absolute -bottom-3 left-0 right-0 h-0.5 bg-emerald-500 rounded-full shadow-sm shadow-emerald-500/50" />
            )}
          </button>
        ))}
      </div>

      {/* Right Filter Selector */}
      <div className="flex items-center gap-2 text-xs font-mono text-slate-300">
        <div className="flex items-center gap-2 rounded-xl border border-slate-800 bg-slate-900 px-3 py-1.5 cursor-pointer hover:border-slate-700">
          <Calendar className="h-3.5 w-3.5 text-emerald-400" />
          <span className="font-bold">{currentFilter}</span>
          <ChevronDown className="h-3.5 w-3.5 text-slate-500" />
        </div>
      </div>
    </div>
  )
}
