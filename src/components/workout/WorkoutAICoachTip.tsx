import React from 'react'
import { Bot } from 'lucide-react'

export const WorkoutAICoachTip: React.FC = () => {
  return (
    <div className="rounded-2xl border border-purple-500/30 bg-gradient-to-br from-slate-900 via-slate-950 to-slate-900 p-5 space-y-2 text-left shadow-xl shadow-purple-950/20">
      <div className="flex items-center gap-2 pb-2 border-b border-slate-800/80">
        <div className="flex h-6 w-6 items-center justify-center rounded-lg bg-purple-500/20 text-purple-400">
          <Bot className="h-3.5 w-3.5" />
        </div>
        <h3 className="text-xs font-extrabold text-purple-400 uppercase tracking-wider">AI Coach Tip</h3>
      </div>
      <p className="text-xs text-slate-300 leading-relaxed font-normal">
        Your last upper body session showed strong volume. Consider adding 2.5 kg to your Bench Press if your final set remains within the target rep range.
      </p>
    </div>
  )
}
