import React from 'react'
import { Link } from 'react-router-dom'
import { Bot, Dumbbell, ArrowUpRight, MessageSquare, Settings, Sparkles } from 'lucide-react'
import { useUser } from '../../hooks'

export const AICoachCard: React.FC = () => {
  const { user } = useUser()
  const hasHistory = (user?.totalWorkouts || 0) > 0

  const coachMessage = hasHistory
    ? `"Great job on your consistency! You've logged ${user?.totalWorkouts} sessions. Focus on progressive overload for continued gains."`
    : `"Welcome to AI FITNESS! I'm your dedicated AI coach. Start your first workout today to unlock personalized training tips and adaptive feedback."`

  const suggestedAction = hasHistory
    ? 'Aim for progressive overload in your next training session'
    : 'Begin your workout routine to calibrate your personalized plan'

  return (
    <div className="rounded-2xl border border-purple-500/20 bg-gradient-to-b from-slate-900 via-slate-950 to-slate-900 p-5 text-left flex flex-col justify-between space-y-4 shadow-xl shadow-purple-950/20">
      
      {/* Header */}
      <div className="flex items-center justify-between pb-3 border-b border-slate-800/80">
        <div className="flex items-center gap-2">
          <div className="flex h-8 w-8 items-center justify-center rounded-xl bg-purple-500/10 border border-purple-500/30 text-purple-400">
            <Bot className="h-4 w-4" />
          </div>
          <h3 className="text-sm font-extrabold text-slate-100">AI Coach</h3>
        </div>
        <Link
          to="/coach"
          className="text-xs font-semibold text-purple-400 hover:text-purple-300 transition-colors"
        >
          View Chat
        </Link>
      </div>

      {/* AI Message Bubble */}
      <div className="rounded-xl border border-slate-800 bg-slate-900/90 p-3.5 text-xs text-slate-200 leading-relaxed">
        {coachMessage}
      </div>

      {/* Suggested Recommendation Box */}
      <div className="space-y-1.5">
        <span className="text-[10px] font-mono text-purple-400 uppercase tracking-wider block">
          Suggested for you
        </span>
        <div className="flex items-center justify-between p-3 rounded-xl bg-emerald-950/40 border border-emerald-500/30">
          <div className="flex items-center gap-2.5">
            <Dumbbell className="h-4 w-4 text-emerald-400 shrink-0" />
            <span className="text-xs font-bold text-slate-100">
              {suggestedAction}
            </span>
          </div>
          <ArrowUpRight className="h-4 w-4 text-emerald-400 shrink-0" />
        </div>
      </div>

      {/* Bottom Action Chips */}
      <div className="flex flex-wrap gap-2 pt-2 border-t border-slate-800/80">
        <Link
          to="/coach"
          className="flex items-center gap-1.5 rounded-lg border border-slate-800 bg-slate-950 px-2.5 py-1.5 text-[11px] font-semibold text-slate-300 hover:bg-slate-800 transition-colors"
        >
          <MessageSquare className="h-3 w-3 text-purple-400" /> Ask Anything
        </Link>
        <Link
          to="/coach"
          className="flex items-center gap-1.5 rounded-lg border border-slate-800 bg-slate-950 px-2.5 py-1.5 text-[11px] font-semibold text-slate-300 hover:bg-slate-800 transition-colors"
        >
          <Settings className="h-3 w-3 text-cyan-400" /> Adjust Plan
        </Link>
        <Link
          to="/coach"
          className="flex items-center gap-1.5 rounded-lg border border-slate-800 bg-slate-950 px-2.5 py-1.5 text-[11px] font-semibold text-slate-300 hover:bg-slate-800 transition-colors"
        >
          <Sparkles className="h-3 w-3 text-amber-400" /> More Tips
        </Link>
      </div>

    </div>
  )
}
