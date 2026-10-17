import React from 'react'
import { Bot } from 'lucide-react'

export const CoachStatusCard: React.FC = () => {
  return (
    <div className="rounded-3xl border border-slate-800 bg-slate-900/90 p-5 flex items-center justify-between gap-4 text-left shadow-2xl">
      <div className="space-y-1">
        <h3 className="text-sm font-extrabold text-slate-100">Coach Status</h3>
        <span className="text-xs font-mono font-bold text-emerald-400 flex items-center gap-1">
          <span className="h-2 w-2 rounded-full bg-emerald-400 animate-pulse" /> Online
        </span>
        <p className="text-[11px] text-slate-400 font-medium pt-1 max-w-[180px]">
          Ready to help you achieve your fitness goals!
        </p>
      </div>

      {/* Large Glowing AI Robot Avatar */}
      <div className="relative flex h-16 w-16 items-center justify-center rounded-2xl bg-emerald-950/80 border border-emerald-500/50 text-emerald-400 shadow-xl shadow-emerald-950/60 ring-2 ring-emerald-500/20 shrink-0">
        <Bot className="h-9 w-9" />
      </div>
    </div>
  )
}
