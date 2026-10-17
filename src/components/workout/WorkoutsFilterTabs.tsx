import React, { useState } from 'react'

export interface WorkoutsFilterTabsProps {
  activeTab?: string
  onTabChange?: (tab: string) => void
}

export const WorkoutsFilterTabs: React.FC<WorkoutsFilterTabsProps> = ({
  activeTab: controlledActiveTab,
  onTabChange,
}) => {
  const [internalActiveTab, setInternalActiveTab] = useState('All Workouts')
  const activeTab = controlledActiveTab !== undefined ? controlledActiveTab : internalActiveTab

  const handleTabClick = (tab: string) => {
    if (onTabChange) {
      onTabChange(tab)
    } else {
      setInternalActiveTab(tab)
    }
  }

  const tabs = ['All Workouts', 'Generate Plan', 'Active Program', 'Custom Workouts', 'Favorites', 'History']

  const handleKeyDown = (e: React.KeyboardEvent, currentTab: string) => {
    const currentIndex = tabs.indexOf(currentTab)
    let targetIndex = -1

    if (e.key === 'ArrowRight' || e.key === 'ArrowDown') {
      e.preventDefault()
      targetIndex = (currentIndex + 1) % tabs.length
    } else if (e.key === 'ArrowLeft' || e.key === 'ArrowUp') {
      e.preventDefault()
      targetIndex = (currentIndex - 1 + tabs.length) % tabs.length
    } else if (e.key === 'Home') {
      e.preventDefault()
      targetIndex = 0
    } else if (e.key === 'End') {
      e.preventDefault()
      targetIndex = tabs.length - 1
    }

    if (targetIndex !== -1) {
      const targetTab = tabs[targetIndex]
      handleTabClick(targetTab)
      const el = document.getElementById(`tab-${targetTab.toLowerCase().replace(/\s+/g, '-')}`)
      el?.focus()
    }
  }

  return (
    <div role="tablist" aria-label="Workout library filters" className="flex items-center gap-2 overflow-x-auto pb-1 text-left max-w-full">
      {tabs.map((tab) => {
        const isSelected = activeTab === tab
        return (
          <button
            key={tab}
            role="tab"
            id={`tab-${tab.toLowerCase().replace(/\s+/g, '-')}`}
            aria-selected={isSelected}
            tabIndex={isSelected ? 0 : -1}
            type="button"
            onClick={() => handleTabClick(tab)}
            onKeyDown={(e) => handleKeyDown(e, tab)}
            className={`min-h-[44px] inline-flex items-center justify-center rounded-xl px-4 py-2.5 text-xs font-semibold transition-all whitespace-nowrap cursor-pointer focus:outline-none focus-visible:ring-2 focus-visible:ring-emerald-500 focus-visible:ring-offset-2 focus-visible:ring-offset-slate-900 ${
              isSelected
                ? 'bg-emerald-500 text-slate-950 shadow-md shadow-emerald-500/20 font-extrabold'
                : 'border border-slate-800 bg-slate-900/60 text-slate-400 hover:bg-slate-800 hover:text-slate-200'
            }`}
          >
            {tab}
          </button>
        )
      })}
    </div>
  )
}
