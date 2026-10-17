import React from 'react'
import { Cpu, Dumbbell, Camera, Utensils, TrendingUp, Bell } from 'lucide-react'

export const FeatureGrid: React.FC = () => {
  const items = [
    {
      title: 'AI Workout Builder',
      desc: 'Plans that adapt as you progress.',
      icon: Cpu,
      color: 'text-purple-400',
    },
    {
      title: '500+ Exercises',
      desc: 'Detailed guides, videos & muscle targeting.',
      icon: Dumbbell,
      color: 'text-emerald-400',
    },
    {
      title: 'AI Form Analysis',
      desc: 'Real-time feedback to perfect your form.',
      icon: Camera,
      color: 'text-cyan-400',
    },
    {
      title: 'Nutrition Planner',
      desc: 'Personalized meal plans that fit your goals.',
      icon: Utensils,
      color: 'text-amber-400',
    },
    {
      title: 'Progress Tracking',
      desc: 'Advanced analytics & insights.',
      icon: TrendingUp,
      color: 'text-emerald-400',
    },
    {
      title: 'Smart Reminders',
      desc: 'Stay consistent with smart notifications.',
      icon: Bell,
      color: 'text-indigo-400',
    },
  ]

  return (
    <section id="features" className="py-20">
      <div className="mx-auto max-w-7xl px-4 sm:px-6 lg:px-8">
        
        <div className="text-center mb-16">
          <h2 className="text-3xl sm:text-4xl font-extrabold text-slate-100 tracking-tight">
            Everything You Need. All in One Platform.
          </h2>
          <p className="text-xs sm:text-sm text-slate-400 mt-2 max-w-xl mx-auto">
            Comprehensive tools designed to streamline your workout, nutrition, technique, and progress management.
          </p>
        </div>

        <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-3 gap-6">
          {items.map((item, i) => {
            const Icon = item.icon
            return (
              <div
                key={i}
                className="rounded-2xl border border-slate-800 bg-slate-900/60 p-6 text-left space-y-3 transition-all hover:border-slate-700 hover:bg-slate-900 card-glow"
              >
                <div className={`flex h-12 w-12 items-center justify-center rounded-xl bg-slate-800/80 ${item.color}`}>
                  <Icon className="h-6 w-6" />
                </div>
                <h3 className="text-base font-bold text-slate-100">{item.title}</h3>
                <p className="text-xs text-slate-400 leading-relaxed">{item.desc}</p>
              </div>
            )
          })}
        </div>

      </div>
    </section>
  )
}
