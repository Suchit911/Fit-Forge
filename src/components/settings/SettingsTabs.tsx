import React from 'react'

export interface SettingsTabsProps {
  activeTab: string
  onTabChange: (tab: string) => void
}

export const SettingsTabs: React.FC<SettingsTabsProps> = ({ activeTab, onTabChange }) => {
  const tabs = [
    'General',
    'Notifications',
    'Appearance',
    'Privacy & Security',
    'Connected Devices',
    'AI Coach',
  ]

  return (
    <div className="flex items-center gap-6 border-b border-slate-800/80 pb-3 text-left overflow-x-auto">
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
  )
}
