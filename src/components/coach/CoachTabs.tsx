import React from 'react'
import { Settings } from 'lucide-react'

export interface CoachTabsProps {
  activeTab: string
  onTabChange: (tab: string) => void
  onSettingsClick: () => void
}

export const CoachTabs: React.FC<CoachTabsProps> = ({
  activeTab,
  onTabChange,
  onSettingsClick,
}) => {
  const tabs = ['Chat', 'Insights']

  return (
    <div className="flex items-center justify-between border-b border-slate-800/80 pb-3 text-left">
      {/* Left Tabs */}
      <div className="flex items-center gap-6">
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

      {/* Right Coach Settings Action */}
      <button
        type="button"
        onClick={onSettingsClick}
        className="flex items-center gap-1.5 rounded-xl border border-slate-800 bg-slate-900 px-3 py-1.5 text-xs font-bold text-slate-300 hover:text-slate-100 hover:border-slate-700 transition-colors cursor-pointer"
      >
        <Settings className="h-3.5 w-3.5 text-slate-400" />
        <span>Coach Settings</span>
      </button>
    </div>
  )
}
