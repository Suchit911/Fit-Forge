import React from 'react'
import { Plus } from 'lucide-react'
export interface ExercisesHeaderProps {
  onCreateCustomClick: () => void
}

export const ExercisesHeader: React.FC<ExercisesHeaderProps> = ({ onCreateCustomClick }) => {
  return (
    <header className="flex flex-col md:flex-row md:items-center justify-between gap-4 pb-6 border-b border-slate-800/80">
      {/* Left Title */}
      <div className="text-left">
        <h1 className="text-2xl font-extrabold text-slate-100 tracking-tight">Exercises</h1>
        <p className="text-xs text-slate-400 mt-1 font-medium">
          Discover and learn 500+ exercises with detailed guides
        </p>
      </div>

      {/* Right Controls */}
      <div className="flex items-center gap-3">
        {/* Create Custom Exercise Button */}
        <button
          type="button"
          onClick={onCreateCustomClick}
          className="inline-flex items-center gap-1.5 rounded-xl border border-emerald-500/40 bg-emerald-500/10 hover:bg-emerald-500 hover:text-slate-950 px-4 py-2 text-xs font-extrabold text-emerald-400 transition-all cursor-pointer shadow-md shadow-emerald-950/40"
        >
          <Plus className="h-4 w-4" /> Create Custom Exercise
        </button>
      </div>
    </header>
  )
}
