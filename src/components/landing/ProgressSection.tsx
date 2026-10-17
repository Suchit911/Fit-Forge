import React from 'react'
import { TrendingUp, Award, Flame, Activity } from 'lucide-react'

export const ProgressSection: React.FC = () => {
  return (
    <section id="progress" className="py-20 relative overflow-hidden">
      <div className="mx-auto max-w-7xl px-4 sm:px-6 lg:px-8">
        
        {/* Section Header */}
        <div className="text-left mb-12">
          <div className="inline-flex items-center gap-2 rounded-full border border-emerald-500/30 bg-emerald-500/10 px-3.5 py-1 text-xs font-bold text-emerald-400 mb-3">
            <TrendingUp className="h-3.5 w-3.5" />
            TRACK PROGRESS THAT MATTERS
          </div>
          <h2 className="text-3xl sm:text-4xl font-extrabold text-slate-100 tracking-tight">
            See Progress. Stay Motivated.
          </h2>
          <p className="text-xs sm:text-sm text-slate-400 mt-2 max-w-xl">
            Track every rep, every set, every weight, and every win. Visual data intelligence that drives sustainable long-term results.
          </p>
        </div>

        {/* 4 Metric Cards Grid */}
        <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-4 gap-6 text-left">
          
          {/* Card 1: Weight Trend */}
          <div className="rounded-2xl border border-slate-800 bg-slate-900 p-5 flex flex-col justify-between space-y-4">
            <div className="flex items-center justify-between">
              <span className="text-xs font-medium text-slate-400">Weight Trend</span>
              <TrendingUp className="h-4 w-4 text-emerald-400" />
            </div>
            <div>
              <span className="text-3xl font-extrabold text-slate-100 font-mono">-4.2 kg</span>
              <span className="text-xs text-emerald-400 font-mono block mt-1">This Month</span>
            </div>
            {/* Green SVG Sparkline */}
            <svg className="w-full h-12 text-emerald-400" viewBox="0 0 100 30" fill="none">
              <path
                d="M0 25 Q 25 20, 50 15 T 100 5"
                stroke="currentColor"
                strokeWidth="2.5"
                strokeLinecap="round"
              />
            </svg>
          </div>

          {/* Card 2: Strength */}
          <div className="rounded-2xl border border-slate-800 bg-slate-900 p-5 flex flex-col justify-between space-y-4">
            <div className="flex items-center justify-between">
              <span className="text-xs font-medium text-slate-400">Strength</span>
              <Award className="h-4 w-4 text-purple-400" />
            </div>
            <div>
              <span className="text-3xl font-extrabold text-purple-400 font-mono">+32%</span>
              <span className="text-xs text-slate-400 font-mono block mt-1">Bench Press PR</span>
            </div>
            {/* Purple SVG Sparkline */}
            <svg className="w-full h-12 text-purple-400" viewBox="0 0 100 30" fill="none">
              <path
                d="M0 28 Q 30 25, 60 12 T 100 4"
                stroke="currentColor"
                strokeWidth="2.5"
                strokeLinecap="round"
              />
            </svg>
          </div>

          {/* Card 3: Consistency */}
          <div className="rounded-2xl border border-slate-800 bg-slate-900 p-5 flex flex-col justify-between space-y-4">
            <div className="flex items-center justify-between">
              <span className="text-xs font-medium text-slate-400">Consistency</span>
              <Flame className="h-4 w-4 text-amber-400" />
            </div>
            <div>
              <span className="text-3xl font-extrabold text-slate-100 font-mono">18</span>
              <span className="text-xs text-amber-400 font-mono block mt-1">Day Streak</span>
            </div>
            {/* Bar Chart Simulation */}
            <div className="flex items-end gap-1.5 h-12">
              {[40, 60, 80, 70, 90, 100, 95].map((h, idx) => (
                <div key={idx} className="flex-1 bg-amber-500 rounded-t-sm" style={{ height: `${h}%` }} />
              ))}
            </div>
          </div>

          {/* Card 4: Workouts */}
          <div className="rounded-2xl border border-slate-800 bg-slate-900 p-5 flex flex-col justify-between space-y-4">
            <div className="flex items-center justify-between">
              <span className="text-xs font-medium text-slate-400">Workouts</span>
              <Activity className="h-4 w-4 text-cyan-400" />
            </div>
            <div>
              <span className="text-3xl font-extrabold text-cyan-400 font-mono">24</span>
              <span className="text-xs text-slate-400 font-mono block mt-1">This Month</span>
            </div>
            {/* Cyan SVG Sparkline */}
            <svg className="w-full h-12 text-cyan-400" viewBox="0 0 100 30" fill="none">
              <path
                d="M0 22 Q 25 10, 50 18 T 100 6"
                stroke="currentColor"
                strokeWidth="2.5"
                strokeLinecap="round"
              />
            </svg>
          </div>

        </div>

      </div>
    </section>
  )
}
