import React from 'react'
import { CheckCircle2, AlertTriangle, Info } from 'lucide-react'

export interface AICoachFeedbackCardProps {
  positive: string[]
  improvement: string[]
  info: string[]
}

export const AICoachFeedbackCard: React.FC<AICoachFeedbackCardProps> = ({
  positive,
  improvement,
  info,
}) => {
  return (
    <div className="rounded-3xl border border-slate-800 bg-slate-900/90 p-5 space-y-3.5 text-left h-full flex flex-col justify-between">
      <h3 className="text-sm font-extrabold text-slate-100 pb-2 border-b border-slate-800/80">
        AI Coach Feedback
      </h3>

      <div className="space-y-3 text-xs">
        {positive.length === 0 && improvement.length === 0 && info.length === 0 ? (
          <div className="py-6 text-center text-xs text-slate-500 font-mono">
            No feedback yet. Begin exercise in camera view to receive real-time coaching feedback.
          </div>
        ) : (
          <>
            {/* Positive Items */}
            {positive.map((text, idx) => (
              <div key={`pos-${idx}`} className="flex items-start gap-2.5">
                <CheckCircle2 className="h-4 w-4 text-emerald-400 shrink-0 mt-0.5" />
                <p className="text-slate-300 font-medium">{text}</p>
              </div>
            ))}

            {/* Improvement Items */}
            {improvement.map((text, idx) => (
              <div key={`imp-${idx}`} className="flex items-start gap-2.5">
                <AlertTriangle className="h-4 w-4 text-amber-400 shrink-0 mt-0.5" />
                <p className="text-slate-300 font-medium">{text}</p>
              </div>
            ))}

            {/* Info Items */}
            {info.map((text, idx) => (
              <div key={`inf-${idx}`} className="flex items-start gap-2.5">
                <Info className="h-4 w-4 text-cyan-400 shrink-0 mt-0.5" />
                <p className="text-slate-300 font-medium">{text}</p>
              </div>
            ))}
          </>
        )}
      </div>
    </div>
  )
}
