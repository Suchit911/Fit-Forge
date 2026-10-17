import React from 'react'
import { Link } from 'react-router-dom'
import { Dumbbell, Flame, ChevronRight, Clock } from 'lucide-react'

export const WorkoutSection: React.FC = () => {
  const workouts = [
    {
      title: 'Strength Training',
      desc: 'Build muscle & get stronger',
      time: '45 min • Intermediate',
      tag: 'GYM',
      tagColor: 'bg-purple-500/20 text-purple-400 border-purple-500/30',
      icon: Dumbbell,
      image: '/assets/workout_strength.jpg',
    },
    {
      title: 'HIIT Cardio',
      desc: 'Burn fat & improve endurance',
      time: '25 min • All Levels',
      tag: 'HOME',
      tagColor: 'bg-amber-500/20 text-amber-400 border-amber-500/30',
      icon: Flame,
      image: '/assets/hero_trainer.jpg',
    },
    {
      title: 'Powerlifting',
      desc: 'Increase strength & power',
      time: '60 min • Advanced',
      tag: 'GYM',
      tagColor: 'bg-purple-500/20 text-purple-400 border-purple-500/30',
      icon: Dumbbell,
      image: '/assets/workout_strength.jpg',
    },
    {
      title: 'Full Body Circuit',
      desc: 'No equipment needed',
      time: '30 min • Beginner',
      tag: 'HOME',
      tagColor: 'bg-amber-500/20 text-amber-400 border-amber-500/30',
      icon: Flame,
      image: '/assets/form_squat.jpg',
    },
  ]

  return (
    <section id="workouts" className="py-20 bg-slate-950/40 border-y border-slate-800/80">
      <div className="mx-auto max-w-7xl px-4 sm:px-6 lg:px-8">
        
        {/* Section Header */}
        <div className="flex flex-col md:flex-row md:items-end justify-between mb-12 text-left">
          <div>
            <div className="inline-flex items-center gap-2 rounded-full border border-emerald-500/30 bg-emerald-500/10 px-3.5 py-1 text-xs font-bold text-emerald-400 mb-3">
              PERSONALIZED WORKOUTS
            </div>
            <h2 className="text-3xl sm:text-4xl font-extrabold text-slate-100 tracking-tight">
              Workouts Built Around You
            </h2>
            <p className="text-xs sm:text-sm text-slate-400 mt-2 max-w-xl">
              Whether you train at home or in the gym, our AI creates the perfect workout based on your goals, equipment, time, and fitness level.
            </p>
          </div>

          <div className="mt-4 md:mt-0 flex gap-2">
            <Link
              to="/workouts"
              className="inline-flex items-center gap-2 text-xs font-bold text-emerald-400 hover:text-emerald-300"
            >
              Explore All Workouts <ChevronRight className="h-4 w-4" />
            </Link>
          </div>
        </div>

        {/* Workout Cards Collection Grid */}
        <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-4 gap-6">
          {workouts.map((w, i) => {
            const Icon = w.icon
            return (
              <div
                key={i}
                className="group relative rounded-2xl border border-slate-800 bg-slate-900 overflow-hidden transition-all hover:border-slate-700 hover:scale-[1.02] flex flex-col justify-between"
              >
                {/* Image header */}
                <div className="relative aspect-[4/3] w-full overflow-hidden bg-slate-950">
                  <img
                    src={w.image}
                    alt={w.title}
                    className="w-full h-full object-cover transition-transform duration-500 group-hover:scale-105 opacity-80"
                  />
                  <div className="absolute inset-0 bg-gradient-to-t from-slate-900 via-transparent to-transparent" />
                  <span
                    className={`absolute top-3 left-3 rounded-full border px-2.5 py-0.5 text-[10px] font-bold uppercase tracking-wider ${w.tagColor}`}
                  >
                    {w.tag}
                  </span>
                </div>

                {/* Card Content */}
                <div className="p-5 text-left space-y-3 flex-1 flex flex-col justify-between">
                  <div>
                    <div className="flex items-center gap-2 text-xs font-bold text-slate-100">
                      <Icon className="h-4 w-4 text-emerald-400" />
                      <span>{w.title}</span>
                    </div>
                    <p className="text-xs text-slate-400 mt-1">{w.desc}</p>
                  </div>

                  <div className="pt-3 border-t border-slate-800/80 flex items-center justify-between text-[11px] text-slate-400 font-mono">
                    <span className="flex items-center gap-1">
                      <Clock className="h-3.5 w-3.5 text-slate-500" />
                      {w.time}
                    </span>
                    <Link
                      to="/workouts"
                      className="text-emerald-400 hover:text-emerald-300 font-sans font-bold"
                    >
                      Start →
                    </Link>
                  </div>
                </div>

              </div>
            )
          })}
        </div>

      </div>
    </section>
  )
}
