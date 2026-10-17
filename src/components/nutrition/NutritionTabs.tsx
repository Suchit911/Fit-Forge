import React from 'react'
import { Calendar, ChevronLeft, ChevronRight } from 'lucide-react'

export interface NutritionTabsProps {
  activeTab: string
  onTabChange: (tab: string) => void
  currentDate: string
  onPrevDate: () => void
  onNextDate: () => void
}

export const NutritionTabs: React.FC<NutritionTabsProps> = ({
  activeTab,
  onTabChange,
  currentDate,
  onPrevDate,
  onNextDate,
}) => {
  const tabs = [
    'Overview',
    'Meal Plan',
    'Food Diary',
    'Recipes',
    'Nutrition Insights',
    'Supplements',
    'Hydration',
  ]

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

      {/* Right Date Selector */}
      <div className="flex items-center gap-2 text-xs font-mono text-slate-300">
        <div className="flex items-center gap-2 rounded-xl border border-slate-800 bg-slate-900 px-3 py-1.5">
          <Calendar className="h-3.5 w-3.5 text-emerald-400" />
          <span className="font-bold">{currentDate}</span>
        </div>

        <button
          type="button"
          onClick={onPrevDate}
          aria-label="Previous day"
          className="rounded-lg border border-slate-800 bg-slate-900 p-1.5 text-slate-400 hover:text-slate-200 transition-colors cursor-pointer"
        >
          <ChevronLeft className="h-3.5 w-3.5" />
        </button>

        <button
          type="button"
          onClick={onNextDate}
          aria-label="Next day"
          className="rounded-lg border border-slate-800 bg-slate-900 p-1.5 text-slate-400 hover:text-slate-200 transition-colors cursor-pointer"
        >
          <ChevronRight className="h-3.5 w-3.5" />
        </button>
      </div>
    </div>
  )
}
