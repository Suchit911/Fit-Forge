import React from 'react'
import { CheckCircle2 } from 'lucide-react'

export const NotificationEmptyState: React.FC = () => {
  return (
    <div className="rounded-3xl border border-slate-800 bg-slate-900/90 p-12 text-center space-y-3 flex flex-col items-center justify-center shadow-2xl">
      <div className="flex h-16 w-16 items-center justify-center rounded-full bg-emerald-500/10 text-emerald-400 border border-emerald-500/20 shadow-xl">
        <CheckCircle2 className="h-8 w-8" />
      </div>
      <h3 className="text-base font-extrabold text-slate-100">You're all caught up</h3>
      <p className="text-xs text-slate-400 max-w-sm">
        No notifications match this filter. Check back later for new workout, AI, and achievement updates!
      </p>
    </div>
  )
}
