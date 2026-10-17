import React from 'react'
import { CheckCheck, Filter, Settings } from 'lucide-react'
import { useNavigate } from 'react-router-dom'

export interface NotificationFiltersProps {
  activeFilter: string
  onFilterChange: (filter: string) => void
  onMarkAllAsRead: () => void
}

export const NotificationFilters: React.FC<NotificationFiltersProps> = ({
  activeFilter,
  onFilterChange,
  onMarkAllAsRead,
}) => {
  const navigate = useNavigate()
  const filters = ['All', 'Unread', 'Workouts', 'Nutrition', 'Achievements', 'AI Coach', 'System']

  return (
    <div className="flex flex-col md:flex-row md:items-center justify-between gap-4 border-b border-slate-800/80 pb-3 text-left">
      {/* Left Filter Tabs */}
      <div className="flex items-center gap-5 overflow-x-auto">
        {filters.map((f) => (
          <button
            key={f}
            type="button"
            onClick={() => onFilterChange(f)}
            className={`relative text-xs font-bold transition-all cursor-pointer whitespace-nowrap ${
              activeFilter === f
                ? 'text-emerald-400 font-extrabold'
                : 'text-slate-400 hover:text-slate-200 font-medium'
            }`}
          >
            {f}
            {activeFilter === f && (
              <span className="absolute -bottom-3 left-0 right-0 h-0.5 bg-emerald-500 rounded-full shadow-sm shadow-emerald-500/50" />
            )}
          </button>
        ))}
      </div>

      {/* Right Control Buttons */}
      <div className="flex items-center gap-3 shrink-0">
        <button
          type="button"
          onClick={onMarkAllAsRead}
          className="flex items-center gap-1.5 text-xs font-mono text-emerald-400 hover:text-emerald-300 font-bold transition-colors cursor-pointer"
        >
          <CheckCheck className="h-4 w-4" /> Mark all as read
        </button>

        <button
          type="button"
          className="flex items-center gap-1.5 rounded-xl border border-slate-800 bg-slate-900 px-3 py-1.5 text-xs font-mono text-slate-300 hover:text-slate-100 transition-colors cursor-pointer"
        >
          <Filter className="h-3.5 w-3.5 text-slate-400" /> Filter
        </button>

        <button
          type="button"
          onClick={() => navigate('/settings')}
          aria-label="Settings"
          className="rounded-xl border border-slate-800 bg-slate-900 p-2 text-slate-400 hover:text-slate-200 transition-colors cursor-pointer"
        >
          <Settings className="h-4 w-4" />
        </button>
      </div>
    </div>
  )
}
