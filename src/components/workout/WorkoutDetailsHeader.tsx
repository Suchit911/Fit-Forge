import React, { useRef } from 'react'
import { Link } from 'react-router-dom'
import { Search } from 'lucide-react'
import { useSearchShortcut } from '../layout/HeaderControls'

export interface WorkoutDetailsHeaderProps {
  title: string
}

export const WorkoutDetailsHeader: React.FC<WorkoutDetailsHeaderProps> = ({ title }) => {
  const searchInputRef = useRef<HTMLInputElement>(null)
  useSearchShortcut(searchInputRef)

  return (
    <header className="flex flex-col md:flex-row md:items-center justify-between gap-4 pb-6 border-b border-slate-800/80">
      {/* Left Breadcrumb */}
      <div className="flex items-center gap-2 text-xs font-mono text-slate-400">
        <Link to="/workouts" className="hover:text-emerald-400 transition-colors">
          Workouts
        </Link>
        <span className="text-slate-600">/</span>
        <span className="text-slate-200 font-bold">{title}</span>
      </div>

      {/* Right Controls */}
      <div className="flex items-center gap-3">
        {/* Search Bar */}
        <div className="relative w-64 hidden sm:block">
          <Search className="absolute left-3 top-1/2 -translate-y-1/2 h-3.5 w-3.5 text-slate-500" />
          <input
            ref={searchInputRef}
            type="text"
            placeholder="Search exercises, workouts..."
            aria-label="Search exercises and workouts"
            className="w-full h-9 rounded-xl border border-slate-800 bg-slate-900/90 pl-9 pr-10 text-xs text-slate-200 placeholder:text-slate-500 focus:outline-none focus:border-emerald-500 transition-colors"
          />
          <kbd className="absolute right-2.5 top-1/2 -translate-y-1/2 rounded bg-slate-800 px-1.5 py-0.5 text-[9px] font-mono font-semibold text-slate-400 border border-slate-700">
            ⌘ K
          </kbd>
        </div>
      </div>
    </header>
  )
}
