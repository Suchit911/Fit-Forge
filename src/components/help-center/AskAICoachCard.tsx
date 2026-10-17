import React from 'react'
import { Sparkles, Bot } from 'lucide-react'
import { useNavigate } from 'react-router-dom'

export const AskAICoachCard: React.FC = () => {
  const navigate = useNavigate()

  return (
    <div className="relative rounded-3xl border border-purple-500/30 bg-gradient-to-br from-slate-900 via-purple-950/20 to-slate-900 p-5 space-y-4 text-left shadow-2xl overflow-hidden">
      {/* Background Ambient Purple Glow */}
      <div className="absolute -top-12 -right-12 h-36 w-36 rounded-full bg-purple-600/20 blur-2xl pointer-events-none" />

      <div className="grid grid-cols-12 gap-3 items-center">
        {/* Left Text & CTA (7 of 12 cols) */}
        <div className="col-span-7 space-y-2">
          <div className="flex items-center gap-1.5 text-purple-400 font-extrabold text-xs uppercase tracking-wide">
            <Sparkles className="h-4 w-4 text-purple-400" />
            <span>Ask AI Coach</span>
          </div>

          <p className="text-xs text-slate-300 font-medium leading-tight">
            Get instant answers about your fitness journey
          </p>

          <button
            type="button"
            onClick={() => navigate('/coach')}
            className="w-full rounded-xl bg-purple-600 hover:bg-purple-500 text-white font-extrabold text-xs py-2.5 px-4 shadow-lg shadow-purple-950/50 transition-all cursor-pointer"
          >
            Ask AI Coach
          </button>

          <div className="flex items-center gap-1.5 text-[10px] font-mono text-emerald-400 font-bold pt-1">
            <span className="h-2 w-2 rounded-full bg-emerald-400 animate-pulse" />
            <span>Available 24/7</span>
          </div>
        </div>

        {/* Right 3D AI Robot Graphic (5 of 12 cols) */}
        <div className="col-span-5 flex justify-center">
          <div className="relative flex h-24 w-24 items-center justify-center rounded-3xl border border-purple-500/40 bg-purple-950/40 shadow-2xl">
            <Bot className="h-14 w-14 text-purple-300 animate-bounce duration-1000" />
            <div className="absolute inset-0 rounded-3xl ring-2 ring-purple-500/30 ring-offset-2 ring-offset-slate-950" />
          </div>
        </div>
      </div>
    </div>
  )
}
