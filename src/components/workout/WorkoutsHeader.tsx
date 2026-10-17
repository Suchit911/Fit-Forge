import React, { useRef } from 'react'
import { Search, Plus } from 'lucide-react'
import { useSearchShortcut } from '../layout/HeaderControls'
import { useToast } from '../ui/Toast'

export interface WorkoutsHeaderProps {
  onGenerateClick?: () => void
}

export const WorkoutsHeader: React.FC<WorkoutsHeaderProps> = ({ onGenerateClick }) => {
  const searchInputRef = useRef<HTMLInputElement>(null)
  useSearchShortcut(searchInputRef)
  const { showToast } = useToast()

  return (
    <header className="flex flex-col md:flex-row md:items-center justify-between gap-4 pb-6 border-b border-slate-800/80">
      {/* Left Title */}
      <div className="text-left">
        <h1 className="text-2xl font-extrabold text-slate-100 tracking-tight">Workouts</h1>
        <p className="text-xs text-slate-400 mt-1 font-medium">
          Discover and follow personalized workouts
        </p>
      </div>

      {/* Right Controls */}
      <div className="flex items-center gap-3">
        {/* Search Bar */}
        <div className="relative w-64 hidden sm:block">
          <Search className="absolute left-3 top-1/2 -translate-y-1/2 h-3.5 w-3.5 text-slate-500" />
          <input
            ref={searchInputRef}
            type="text"
            placeholder="Search workouts, muscle groups..."
            aria-label="Search workouts"
            className="w-full h-9 rounded-xl border border-slate-800 bg-slate-900/90 pl-9 pr-10 text-xs text-slate-200 placeholder:text-slate-500 focus:outline-none focus:border-emerald-500 transition-colors"
          />
          <kbd className="absolute right-2.5 top-1/2 -translate-y-1/2 rounded bg-slate-800 px-1.5 py-0.5 text-[9px] font-mono font-semibold text-slate-400 border border-slate-700">
            ⌘ K
          </kbd>
        </div>

        {/* Generate Plan Button */}
        <button
          type="button"
          onClick={() => {
            if (onGenerateClick) {
              onGenerateClick()
            } else {
              showToast('Create Workout builder initialized', 'info')
            }
          }}
          className="min-h-[44px] inline-flex items-center justify-center gap-1.5 rounded-xl bg-emerald-500 hover:bg-emerald-400 text-slate-950 px-4 py-2.5 text-xs font-extrabold shadow-md shadow-emerald-500/20 transition-all cursor-pointer focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-emerald-400 focus-visible:ring-offset-2 focus-visible:ring-offset-slate-900"
        >
          <Plus className="h-4 w-4" aria-hidden="true" /> Generate Plan
        </button>
      </div>
    </header>
  )
}
