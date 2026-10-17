import React from 'react'
import { Sparkles } from 'lucide-react'

export interface AICoachingTipsCardProps {
  tips: string[]
}

export const AICoachingTipsCard: React.FC<AICoachingTipsCardProps> = ({ tips }) => {
  return (
    <div className="rounded-2xl border border-purple-500/30 bg-gradient-to-b from-purple-950/30 to-slate-900/90 p-5 space-y-3 text-left shadow-lg">
      <div className="flex items-center gap-2 pb-2 border-b border-purple-500/20">
        <Sparkles className="h-4 w-4 text-purple-400" />
        <h3 className="text-sm font-extrabold text-purple-300">AI Coaching Tips</h3>
      </div>

      <div className="space-y-2 text-xs leading-relaxed">
        {tips.map((tip, idx) => (
          <div key={idx} className="flex items-start gap-2">
            <span className="text-purple-400 font-bold">•</span>
            <p className="text-slate-300 font-medium">{tip}</p>
          </div>
        ))}
      </div>
    </div>
  )
}
