import React, { useRef } from 'react'
import { Search } from 'lucide-react'
import { useUser } from '../../hooks'
import { useSearchShortcut } from '../layout/HeaderControls'

export const DashboardHeader: React.FC = () => {
  const { user, authUser } = useUser()
  const searchInputRef = useRef<HTMLInputElement>(null)
  useSearchShortcut(searchInputRef)

  const greetingName = user?.name ? user.name.split(' ')[0] : (authUser?.displayName ? authUser.displayName.split(' ')[0] : 'Athlete')

  return (
    <header className="flex flex-col md:flex-row md:items-center justify-between gap-4 pb-6 border-b border-slate-800/80">
      {/* Left Greeting */}
      <div className="text-left">
        <h1 className="text-2xl font-extrabold text-slate-100 tracking-tight flex items-center gap-2">
          Good Morning, {greetingName}! 👋
        </h1>
        <p className="text-xs text-slate-400 mt-1 font-medium">
          Ready to crush your fitness goals today?
        </p>
      </div>

      {/* Right Action Controls */}
      <div className="flex items-center gap-3">
        {/* Search Input Bar */}
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
