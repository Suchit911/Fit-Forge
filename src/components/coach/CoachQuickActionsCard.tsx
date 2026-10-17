import React from 'react'
import { TrendingUp, Sliders, MessageSquare, Calendar } from 'lucide-react'

export interface CoachQuickActionsCardProps {
  onActionClick: (action: string) => void
}

export const CoachQuickActionsCard: React.FC<CoachQuickActionsCardProps> = ({ onActionClick }) => {
  return (
    <div className="rounded-3xl border border-slate-800 bg-slate-900/90 p-5 space-y-3 text-left shadow-2xl">
      <h3 className="text-sm font-extrabold text-slate-100 pb-2 border-b border-slate-800/80">
        Quick Actions
      </h3>

      <div className="grid grid-cols-4 gap-2">
        <button
          type="button"
          onClick={() => onActionClick('Analyze Progress')}
          className="flex flex-col items-center justify-center p-3 rounded-2xl bg-slate-950/70 border border-slate-800 hover:border-slate-700 hover:text-emerald-400 transition-colors text-center cursor-pointer space-y-1.5"
        >
          <TrendingUp className="h-4 w-4 text-emerald-400" />
          <span className="text-[10px] font-bold text-slate-200 leading-tight">Analyze Progress</span>
        </button>

        <button
          type="button"
          onClick={() => onActionClick('Adjust Plan')}
          className="flex flex-col items-center justify-center p-3 rounded-2xl bg-slate-950/70 border border-slate-800 hover:border-slate-700 hover:text-cyan-400 transition-colors text-center cursor-pointer space-y-1.5"
        >
          <Sliders className="h-4 w-4 text-cyan-400" />
          <span className="text-[10px] font-bold text-slate-200 leading-tight">Adjust Plan</span>
        </button>

        <button
          type="button"
          onClick={() => onActionClick('Log Feedback')}
          className="flex flex-col items-center justify-center p-3 rounded-2xl bg-slate-950/70 border border-slate-800 hover:border-slate-700 hover:text-amber-400 transition-colors text-center cursor-pointer space-y-1.5"
        >
          <MessageSquare className="h-4 w-4 text-amber-400" />
          <span className="text-[10px] font-bold text-slate-200 leading-tight">Log Feedback</span>
        </button>

        <button
          type="button"
          onClick={() => onActionClick('Book Call')}
          className="flex flex-col items-center justify-center p-3 rounded-2xl bg-slate-950/70 border border-slate-800 hover:border-slate-700 hover:text-purple-400 transition-colors text-center cursor-pointer space-y-1.5"
        >
          <Calendar className="h-4 w-4 text-purple-400" />
          <span className="text-[10px] font-bold text-slate-200 leading-tight">Book Call</span>
        </button>
      </div>
    </div>
  )
}
