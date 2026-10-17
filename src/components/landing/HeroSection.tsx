import React from 'react'
import { Link } from 'react-router-dom'
import { ArrowRight, Play, Star, Flame, Dumbbell } from 'lucide-react'

export const HeroSection: React.FC = () => {
  return (
    <section className="relative overflow-hidden pt-8 pb-16 lg:pt-16 lg:pb-24">
      {/* Background ambient lighting */}
      <div className="absolute top-1/4 left-1/2 -translate-x-1/2 -translate-y-1/2 w-[600px] h-[600px] bg-emerald-500/10 rounded-full blur-[140px] pointer-events-none" />
      <div className="absolute top-1/3 right-10 w-[400px] h-[400px] bg-cyan-500/10 rounded-full blur-[120px] pointer-events-none" />

      <div className="mx-auto max-w-7xl px-4 sm:px-6 lg:px-8 relative z-10">
        <div className="grid grid-cols-1 lg:grid-cols-12 gap-12 items-center">
          
          {/* Left Hero Text Column */}
          <div className="lg:col-span-6 space-y-6 text-left">
            
            {/* Eyebrow Badge */}
            <div className="inline-flex items-center gap-2 rounded-full border border-emerald-500/30 bg-emerald-500/10 px-3.5 py-1 text-xs font-bold text-emerald-400">
              <span className="h-1.5 w-1.5 rounded-full bg-emerald-400 animate-pulse" />
              AI-POWERED FITNESS COACH
            </div>

            {/* Headline */}
            <h1 className="text-4xl sm:text-5xl lg:text-6xl font-extrabold tracking-tight text-slate-100 leading-[1.1]">
              Your Personal <br />
              <span className="text-transparent bg-clip-text bg-gradient-to-r from-emerald-400 via-emerald-300 to-cyan-400">
                AI Fitness Coach
              </span>
            </h1>

            {/* Subtext */}
            <p className="text-sm sm:text-base text-slate-400 max-w-xl leading-relaxed">
              Smart workouts. Real results. Built around you. The all-in-one AI fitness platform that creates personalized workouts, tracks your progress, analyzes your form, and builds the perfect nutrition plan for your goals.
            </p>

            {/* Action CTAs */}
            <div className="flex flex-wrap items-center gap-4 pt-2">
              <Link
                to="/signup"
                className="inline-flex items-center gap-2 rounded-xl bg-emerald-500 hover:bg-emerald-400 text-slate-950 px-6 py-3.5 text-sm font-extrabold shadow-lg shadow-emerald-500/25 transition-all hover:scale-[1.02]"
              >
                Start Your Journey <ArrowRight className="h-4 w-4" />
              </Link>
              <a
                href="#how-it-works"
                className="inline-flex items-center gap-2 rounded-xl border border-slate-800 bg-slate-900/80 hover:bg-slate-800 text-slate-200 px-5 py-3.5 text-sm font-semibold transition-colors"
              >
                <div className="flex h-6 w-6 items-center justify-center rounded-full bg-slate-800 border border-slate-700">
                  <Play className="h-3 w-3 text-slate-300 fill-slate-300" />
                </div>
                See How It Works
              </a>
            </div>

            {/* Social Proof */}
            <div className="flex items-center gap-3 pt-4 border-t border-slate-900">
              <div className="flex text-amber-400 gap-0.5">
                {[...Array(5)].map((_, i) => (
                  <Star key={i} className="h-4 w-4 fill-amber-400" />
                ))}
              </div>
              <p className="text-xs text-slate-400 font-medium">
                Trusted by <span className="text-slate-200 font-bold">50,000+</span> fitness enthusiasts
              </p>
            </div>

          </div>

          {/* Right Hero Composition Column */}
          <div className="lg:col-span-6 relative flex justify-center items-center">
            
            {/* Main Athletic Photo Container */}
            <div className="relative w-full max-w-md lg:max-w-lg aspect-[4/5] rounded-3xl overflow-hidden border border-slate-800 shadow-2xl bg-slate-900">
              <img
                src="/assets/hero_trainer.jpg"
                alt="AI Personal Fitness Trainer"
                className="w-full h-full object-cover object-top opacity-90"
              />
              <div className="absolute inset-0 bg-gradient-to-t from-slate-950 via-transparent to-transparent opacity-80" />
            </div>

            {/* Left Overlay Card: Today's Plan */}
            <div className="absolute -left-4 sm:-left-8 top-12 z-20 w-60 rounded-2xl border border-slate-800/90 bg-slate-950/90 p-4 shadow-2xl backdrop-blur-md hidden sm:block">
              <div className="flex items-center justify-between pb-2 border-b border-slate-800/80">
                <span className="text-[11px] font-bold text-slate-300 uppercase tracking-wider">Today's Plan</span>
                <span className="h-2 w-2 rounded-full bg-emerald-400" />
              </div>
              <div className="mt-3 space-y-2 text-left">
                <div className="flex items-center gap-2 text-xs font-bold text-slate-100">
                  <Dumbbell className="h-4 w-4 text-emerald-400" />
                  <span>Upper Body Strength</span>
                </div>
                <p className="text-[10px] text-slate-400 font-mono">45 min • Gym</p>
                <div className="space-y-1 text-[11px] text-slate-300 pt-1">
                  <div className="flex justify-between"><span>Bench Press</span> <span className="text-slate-500 font-mono">4 sets × 8 reps</span></div>
                  <div className="flex justify-between"><span>Bent-Over Row</span> <span className="text-slate-500 font-mono">4 sets × 10 reps</span></div>
                  <div className="flex justify-between"><span>Shoulder Press</span> <span className="text-slate-500 font-mono">3 sets × 10 reps</span></div>
                </div>
                <Link
                  to="/workouts/today"
                  className="mt-3 block text-center rounded-lg bg-emerald-500 py-1.5 text-[11px] font-bold text-slate-950 hover:bg-emerald-400 transition-colors"
                >
                  Start Workout
                </Link>
              </div>
            </div>

            {/* Right Overlay Card 1: Weekly Progress Ring */}
            <div className="absolute -right-4 sm:-right-6 top-8 z-20 w-48 rounded-2xl border border-slate-800/90 bg-slate-950/90 p-4 shadow-2xl backdrop-blur-md hidden sm:block">
              <div className="flex justify-between text-[11px] font-bold text-slate-300 mb-2">
                <span>Weekly Progress</span>
                <span className="text-emerald-400">On Track</span>
              </div>
              <div className="relative flex items-center justify-center my-2">
                <svg className="h-20 w-20 transform -rotate-90">
                  <circle cx="40" cy="40" r="32" stroke="#1e293b" strokeWidth="6" fill="transparent" />
                  <circle
                    cx="40"
                    cy="40"
                    r="32"
                    stroke="#10b981"
                    strokeWidth="6"
                    strokeDasharray="200"
                    strokeDashoffset="44"
                    strokeLinecap="round"
                    fill="transparent"
                  />
                </svg>
                <div className="absolute text-center">
                  <span className="text-lg font-extrabold text-slate-100 font-mono">78%</span>
                  <span className="block text-[9px] text-slate-400 uppercase">On Track</span>
                </div>
              </div>
            </div>

            {/* Right Overlay Card 2: Calories & Macro Summary */}
            <div className="absolute -right-4 sm:-right-8 bottom-10 z-20 w-64 rounded-2xl border border-slate-800/90 bg-slate-950/90 p-4 shadow-2xl backdrop-blur-md hidden sm:block">
              <div className="flex items-center justify-between text-xs font-semibold text-slate-200">
                <span>Calories</span>
                <Flame className="h-4 w-4 text-emerald-400" />
              </div>
              <div className="mt-1 flex items-baseline gap-1">
                <span className="text-xl font-extrabold text-slate-100 font-mono">1,890</span>
                <span className="text-xs text-slate-400 font-mono">/ 2,400 kcal</span>
              </div>
              <div className="mt-3 grid grid-cols-3 gap-1 pt-2 border-t border-slate-800/80 text-center text-[10px]">
                <div>
                  <span className="text-slate-400 block">Protein</span>
                  <span className="font-mono font-bold text-emerald-400">142g</span>
                </div>
                <div>
                  <span className="text-slate-400 block">Carbs</span>
                  <span className="font-mono font-bold text-cyan-400">210g</span>
                </div>
                <div>
                  <span className="text-slate-400 block">Fat</span>
                  <span className="font-mono font-bold text-amber-400">65g</span>
                </div>
              </div>
            </div>

          </div>

        </div>
      </div>
    </section>
  )
}
