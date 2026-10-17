import React from 'react'
import { User, Cpu, Activity, Trophy } from 'lucide-react'

export const HowItWorksSection: React.FC = () => {
  const steps = [
    {
      step: '1. Tell Us About You',
      desc: 'Share your goals, experience, equipment & preferences.',
      icon: User,
    },
    {
      step: '2. Get Your Plan',
      desc: 'AI creates your personalized workout & nutrition plan.',
      icon: Cpu,
    },
    {
      step: '3. Track & Improve',
      desc: 'Follow the plan, track progress & get AI feedback.',
      icon: Activity,
    },
    {
      step: '4. Achieve Your Goals',
      desc: 'Stay consistent and transform your body & life.',
      icon: Trophy,
    },
  ]

  return (
    <section id="how-it-works" className="py-20 bg-slate-950/60 border-y border-slate-800/80">
      <div className="mx-auto max-w-7xl px-4 sm:px-6 lg:px-8">
        
        <div className="text-center mb-16">
          <h2 className="text-3xl sm:text-4xl font-extrabold text-slate-100 tracking-tight">
            How It Works
          </h2>
          <p className="text-xs sm:text-sm text-slate-400 mt-2">
            Four simple steps to start your AI-guided fitness transformation.
          </p>
        </div>

        {/* Connected Steps Grid */}
        <div className="relative grid grid-cols-1 md:grid-cols-4 gap-8 text-center">
          
          {/* Dashed Connecting Line (Desktop) */}
          <div className="hidden md:block absolute top-10 left-[12%] right-[12%] h-0.5 border-t-2 border-dashed border-slate-800 pointer-events-none z-0" />

          {steps.map((s, i) => {
            const Icon = s.icon
            return (
              <div key={i} className="relative z-10 flex flex-col items-center space-y-4">
                <div className="flex h-16 w-16 items-center justify-center rounded-2xl border border-slate-800 bg-slate-900 text-emerald-400 shadow-xl transition-transform hover:scale-110">
                  <Icon className="h-8 w-8" />
                </div>
                <h3 className="text-sm font-extrabold text-slate-200">{s.step}</h3>
                <p className="text-xs text-slate-400 max-w-xs leading-relaxed">{s.desc}</p>
              </div>
            )
          })}

        </div>

      </div>
    </section>
  )
}
