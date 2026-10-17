import React from 'react'
import { PlusCircle, Bookmark, History } from 'lucide-react'

export interface ExerciseQuickActionsCardProps {
  onCreateCustomClick: () => void
}

export const ExerciseQuickActionsCard: React.FC<ExerciseQuickActionsCardProps> = ({ onCreateCustomClick }) => {
  return (
    <div className="rounded-2xl border border-slate-800 bg-slate-900/90 p-5 space-y-3 text-left">
      <h3 className="text-sm font-extrabold text-slate-100 pb-2 border-b border-slate-800/80">
        Quick Actions
      </h3>

      <div className="grid grid-cols-3 gap-2">
        <button
          type="button"
          onClick={onCreateCustomClick}
          className="flex flex-col items-center justify-center p-3 rounded-xl bg-slate-950/70 border border-slate-800 hover:border-slate-700 hover:text-emerald-400 transition-colors text-center cursor-pointer space-y-1.5"
        >
          <PlusCircle className="h-5 w-5 text-emerald-400" />
          <span className="text-[10px] font-bold text-slate-200 leading-tight">Create Custom Exercise</span>
        </button>

        <button
          type="button"
          className="flex flex-col items-center justify-center p-3 rounded-xl bg-slate-950/70 border border-slate-800 hover:border-slate-700 hover:text-cyan-400 transition-colors text-center cursor-pointer space-y-1.5"
        >
          <Bookmark className="h-5 w-5 text-cyan-400" />
          <span className="text-[10px] font-bold text-slate-200 leading-tight">My Exercises</span>
        </button>

        <button
          type="button"
          className="flex flex-col items-center justify-center p-3 rounded-xl bg-slate-950/70 border border-slate-800 hover:border-slate-700 hover:text-purple-400 transition-colors text-center cursor-pointer space-y-1.5"
        >
          <History className="h-5 w-5 text-purple-400" />
          <span className="text-[10px] font-bold text-slate-200 leading-tight">Exercise History</span>
        </button>
      </div>
    </div>
  )
}
