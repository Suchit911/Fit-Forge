import React from 'react'
import { Cpu, Camera, TrendingUp, Utensils, ShieldCheck } from 'lucide-react'

export const FeatureStrip: React.FC = () => {
  const features = [
    {
      icon: Cpu,
      title: 'AI-Powered Personalization',
      desc: 'Plans that adapt to you',
      iconColor: 'text-purple-400',
    },
    {
      icon: Camera,
      title: 'Form Analysis with AI',
      desc: 'Real-time feedback',
      iconColor: 'text-cyan-400',
    },
    {
      icon: TrendingUp,
      title: 'Track & Improve Every Day',
      desc: 'See real progress',
      iconColor: 'text-emerald-400',
    },
    {
      icon: Utensils,
      title: 'Nutrition Plans That Fit You',
      desc: 'Eat for your goals',
      iconColor: 'text-amber-400',
    },
    {
      icon: ShieldCheck,
      title: 'Stay Consistent & Motivated',
      desc: 'Build lasting habits',
      iconColor: 'text-indigo-400',
    },
  ]

  return (
    <section className="py-8 border-y border-slate-800/80 bg-slate-950/60 backdrop-blur-sm">
      <div className="mx-auto max-w-7xl px-4 sm:px-6 lg:px-8">
        <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-5 gap-4">
          {features.map((f, i) => {
            const Icon = f.icon
            return (
              <div
                key={i}
                className="flex items-center gap-3.5 rounded-2xl border border-slate-800/80 bg-slate-900/60 p-4 transition-all hover:border-slate-700 hover:bg-slate-900 card-glow"
              >
                <div className={`flex h-11 w-11 shrink-0 items-center justify-center rounded-xl bg-slate-800/80 ${f.iconColor}`}>
                  <Icon className="h-5 w-5" />
                </div>
                <div className="text-left">
                  <h3 className="text-xs font-bold text-slate-200">{f.title}</h3>
                  <p className="text-[11px] text-slate-400 mt-0.5">{f.desc}</p>
                </div>
              </div>
            )
          })}
        </div>
      </div>
    </section>
  )
}
