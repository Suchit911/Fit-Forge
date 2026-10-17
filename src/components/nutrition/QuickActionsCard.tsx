import React from 'react'
import { PlusCircle, Camera, Calendar, BookOpen } from 'lucide-react'

export interface QuickActionsCardProps {
  onLogMealClick: () => void
  onScanFoodClick: () => void
  onMealPlannerClick: () => void
  onFoodDiaryClick: () => void
}

export const QuickActionsCard: React.FC<QuickActionsCardProps> = ({
  onLogMealClick,
  onScanFoodClick,
  onMealPlannerClick,
  onFoodDiaryClick,
}) => {
  return (
    <div className="rounded-3xl border border-slate-800 bg-slate-900/90 p-5 space-y-3 text-left shadow-2xl">
      <h3 className="text-sm font-extrabold text-slate-100 pb-2 border-b border-slate-800/80">
        Quick Actions
      </h3>

      <div className="grid grid-cols-4 gap-2">
        <button
          type="button"
          onClick={onLogMealClick}
          className="flex flex-col items-center justify-center p-3 rounded-2xl bg-slate-950/70 border border-slate-800 hover:border-slate-700 hover:text-emerald-400 transition-colors text-center cursor-pointer space-y-1.5"
        >
          <PlusCircle className="h-5 w-5 text-emerald-400" />
          <span className="text-[10px] font-bold text-slate-200 leading-tight">Log Meal</span>
        </button>

        <button
          type="button"
          onClick={onScanFoodClick}
          className="flex flex-col items-center justify-center p-3 rounded-2xl bg-slate-950/70 border border-slate-800 hover:border-slate-700 hover:text-cyan-400 transition-colors text-center cursor-pointer space-y-1.5"
        >
          <Camera className="h-5 w-5 text-cyan-400" />
          <span className="text-[10px] font-bold text-slate-200 leading-tight">Scan Food</span>
        </button>

        <button
          type="button"
          onClick={onMealPlannerClick}
          className="flex flex-col items-center justify-center p-3 rounded-2xl bg-slate-950/70 border border-slate-800 hover:border-slate-700 hover:text-amber-400 transition-colors text-center cursor-pointer space-y-1.5"
        >
          <Calendar className="h-5 w-5 text-amber-400" />
          <span className="text-[10px] font-bold text-slate-200 leading-tight">Meal Planner</span>
        </button>

        <button
          type="button"
          onClick={onFoodDiaryClick}
          className="flex flex-col items-center justify-center p-3 rounded-2xl bg-slate-950/70 border border-slate-800 hover:border-slate-700 hover:text-purple-400 transition-colors text-center cursor-pointer space-y-1.5"
        >
          <BookOpen className="h-5 w-5 text-purple-400" />
          <span className="text-[10px] font-bold text-slate-200 leading-tight">Food Diary</span>
        </button>
      </div>
    </div>
  )
}
