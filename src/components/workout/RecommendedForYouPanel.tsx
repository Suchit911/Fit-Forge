import React, { useState } from 'react'
import { Plus, Check } from 'lucide-react'

export const RecommendedForYouPanel: React.FC = () => {
  const [isAdded, setIsAdded] = useState(false)

  return (
    <div className="rounded-2xl border border-slate-800 bg-slate-900/90 p-5 space-y-3 text-left">
      <h3 className="text-sm font-extrabold text-slate-100 pb-2 border-b border-slate-800/80">
        Recommended For You
      </h3>

      <div className="flex items-center justify-between p-3 rounded-xl bg-slate-950/70 border border-slate-800/80">
        <div className="flex items-center gap-3">
          <div className="h-10 w-12 rounded-lg overflow-hidden bg-slate-900 border border-slate-800 shrink-0">
            <img src="/assets/workout_upper_pull.jpg" alt="Pull-ups" className="w-full h-full object-cover opacity-80" />
          </div>
          <div>
            <h4 className="text-xs font-bold text-slate-100">Add Pull-ups</h4>
            <span className="text-[10px] text-slate-400 font-mono">3 sets × Failure</span>
          </div>
        </div>

        <button
          type="button"
          onClick={() => setIsAdded(!isAdded)}
          className={`inline-flex items-center gap-1 rounded-xl px-3 py-1.5 text-xs font-extrabold transition-all cursor-pointer ${
            isAdded
              ? 'bg-slate-800 text-slate-300 border border-slate-700'
              : 'bg-emerald-500 hover:bg-emerald-400 text-slate-950 shadow-md shadow-emerald-500/20'
          }`}
        >
          {isAdded ? (
            <>
              <Check className="h-3.5 w-3.5" /> Added
            </>
          ) : (
            <>
              <Plus className="h-3.5 w-3.5" /> Add
            </>
          )}
        </button>
      </div>
    </div>
  )
}
