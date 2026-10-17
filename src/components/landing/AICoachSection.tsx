import React from 'react'
import { Bot, MessageSquare, Zap, Target, BookOpen, Sparkles, CheckCircle2 } from 'lucide-react'

export const AICoachSection: React.FC = () => {
  const chips = [
    { label: 'Instant Answers', icon: Zap },
    { label: 'Plan Adjustments', icon: Target },
    { label: 'Technique Tips', icon: BookOpen },
    { label: 'Motivation Boost', icon: Sparkles },
  ]

  return (
    <section id="ai-coach" className="py-20 relative overflow-hidden">
      <div className="absolute top-1/2 left-1/4 -translate-y-1/2 w-[500px] h-[500px] bg-purple-500/10 rounded-full blur-[140px] pointer-events-none" />

      <div className="mx-auto max-w-7xl px-4 sm:px-6 lg:px-8 relative z-10">
        <div className="grid grid-cols-1 lg:grid-cols-12 gap-12 items-center">
          
          {/* Left Text Column */}
          <div className="lg:col-span-6 space-y-6 text-left">
            <div className="inline-flex items-center gap-2 rounded-full border border-purple-500/30 bg-purple-500/10 px-3.5 py-1 text-xs font-bold text-purple-400">
              <Bot className="h-3.5 w-3.5" />
              AI COACH THAT UNDERSTANDS YOU
            </div>

            <h2 className="text-3xl sm:text-4xl lg:text-5xl font-extrabold tracking-tight text-slate-100 leading-[1.15]">
              Get Smarter Guidance <br />
              <span className="text-transparent bg-clip-text bg-gradient-to-r from-purple-400 via-indigo-300 to-cyan-400">
                Every Step of the Way
              </span>
            </h2>

            <p className="text-sm sm:text-base text-slate-400 leading-relaxed max-w-xl">
              Chat with your AI fitness coach anytime. Get answers, adjust your plan, learn techniques, and stay on track with personalized recommendations built from your exercise performance.
            </p>

            {/* Feature Chips */}
            <div className="grid grid-cols-2 gap-3 pt-2">
              {chips.map((c, i) => {
                const Icon = c.icon
                return (
                  <div
                    key={i}
                    className="flex items-center gap-3 rounded-xl border border-slate-800 bg-slate-900/60 p-3 text-xs font-semibold text-slate-200"
                  >
                    <div className="flex h-8 w-8 items-center justify-center rounded-lg bg-purple-500/10 text-purple-400">
                      <Icon className="h-4 w-4" />
                    </div>
                    <span>{c.label}</span>
                  </div>
                )
              })}
            </div>
          </div>

          {/* Right Phone Mockup Column */}
          <div className="lg:col-span-6 flex justify-center">
            <div className="relative w-full max-w-sm rounded-[40px] border-4 border-slate-800 bg-slate-950 p-4 shadow-2xl">
              
              {/* Phone Speaker Notch */}
              <div className="mx-auto mb-4 h-4 w-28 rounded-full bg-slate-900" />

              {/* App Chat Header */}
              <div className="flex items-center gap-3 border-b border-slate-800 pb-3 mb-4 text-left">
                <div className="flex h-9 w-9 items-center justify-center rounded-full bg-purple-500/20 text-purple-400 border border-purple-500/30">
                  <Bot className="h-5 w-5" />
                </div>
                <div>
                  <h4 className="text-xs font-bold text-slate-100">AI Coach</h4>
                  <span className="flex items-center gap-1 text-[10px] text-emerald-400 font-mono">
                    <span className="h-1.5 w-1.5 rounded-full bg-emerald-400 animate-pulse" /> Online
                  </span>
                </div>
              </div>

              {/* Chat Bubble Thread */}
              <div className="space-y-3 text-left">
                
                {/* User Message */}
                <div className="flex flex-col items-end">
                  <div className="max-w-[85%] rounded-2xl rounded-tr-none bg-purple-600 px-4 py-2.5 text-xs text-white">
                    How was my workout today?
                  </div>
                </div>

                <div className="flex flex-col items-end">
                  <div className="max-w-[85%] rounded-2xl rounded-tr-none bg-purple-600 px-4 py-2.5 text-xs text-white">
                    It was great! But felt my shoulders getting tired.
                  </div>
                </div>

                {/* AI Assistant Message */}
                <div className="flex flex-col items-start">
                  <div className="max-w-[90%] rounded-2xl rounded-tl-none border border-slate-800 bg-slate-900 px-4 py-3 text-xs text-slate-200 space-y-2">
                    <p>
                      Great job! I recommend adding face pulls to improve shoulder stability and posture.
                    </p>
                    
                    {/* Embedded Suggested Exercise Card */}
                    <div className="rounded-xl border border-slate-800 bg-slate-950 p-3 mt-2">
                      <div className="flex items-center justify-between">
                        <span className="text-[10px] font-mono text-purple-400 uppercase">Suggested Exercise</span>
                        <CheckCircle2 className="h-3.5 w-3.5 text-emerald-400" />
                      </div>
                      <h5 className="text-xs font-bold text-slate-100 mt-1">Face Pulls</h5>
                      <p className="text-[10px] text-slate-400 font-mono">3 sets × 15 reps</p>
                    </div>
                  </div>
                </div>

              </div>

              {/* Input Placeholder */}
              <div className="mt-4 flex items-center justify-between rounded-xl border border-slate-800 bg-slate-900 px-3 py-2 text-xs text-slate-500">
                <span>Ask AI Coach anything...</span>
                <MessageSquare className="h-4 w-4 text-purple-400" />
              </div>

            </div>
          </div>

        </div>
      </div>
    </section>
  )
}
