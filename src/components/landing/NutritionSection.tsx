import React from 'react'
import { Utensils, Droplets, Flame, Check } from 'lucide-react'

export const NutritionSection: React.FC = () => {
  const meals = [
    { type: 'Breakfast', name: 'Oats with Fruits & Nuts', kcal: 520 },
    { type: 'Lunch', name: 'Soya Chunks Curry & Rice', kcal: 680 },
    { type: 'Dinner', name: 'Paneer & Quinoa Bowl', kcal: 690 },
  ]

  const waterBars = [60, 80, 100, 70, 90, 85, 75]

  return (
    <section id="nutrition" className="py-20 bg-slate-950/60 border-y border-slate-800/80">
      <div className="mx-auto max-w-7xl px-4 sm:px-6 lg:px-8">
        
        {/* Section Header */}
        <div className="text-left mb-12">
          <div className="inline-flex items-center gap-2 rounded-full border border-amber-500/30 bg-amber-500/10 px-3.5 py-1 text-xs font-bold text-amber-400 mb-3">
            <Utensils className="h-3.5 w-3.5" />
            NUTRITION INTELLIGENCE
          </div>
          <h2 className="text-3xl sm:text-4xl font-extrabold text-slate-100 tracking-tight">
            Eat Smart. Reach Your Goals.
          </h2>
          <p className="text-xs sm:text-sm text-slate-400 mt-2 max-w-xl">
            Personalized meal plans, macro tracking, and smart food recommendations tailored to your dietary preferences to fuel your transformation.
          </p>
        </div>

        {/* 3 Nutrition Cards Grid */}
        <div className="grid grid-cols-1 md:grid-cols-3 gap-6 text-left">
          
          {/* Card 1: Today's Macros */}
          <div className="rounded-2xl border border-slate-800 bg-slate-900 p-6 flex flex-col justify-between space-y-4">
            <div className="flex items-center justify-between">
              <h3 className="text-sm font-bold text-slate-200">Today's Macros</h3>
              <Flame className="h-4 w-4 text-emerald-400" />
            </div>

            <div className="relative flex items-center justify-center my-4">
              <svg className="h-32 w-32 transform -rotate-90">
                <circle cx="64" cy="64" r="52" stroke="#1e293b" strokeWidth="10" fill="transparent" />
                <circle
                  cx="64"
                  cy="64"
                  r="52"
                  stroke="#10b981"
                  strokeWidth="10"
                  strokeDasharray="326"
                  strokeDashoffset="75"
                  strokeLinecap="round"
                  fill="transparent"
                />
              </svg>
              <div className="absolute text-center">
                <span className="text-2xl font-extrabold text-slate-100 font-mono">1,890</span>
                <span className="block text-[10px] text-slate-400 uppercase font-mono">/ 2,400 kcal</span>
              </div>
            </div>

            <div className="grid grid-cols-3 gap-2 pt-3 border-t border-slate-800 text-center text-xs">
              <div>
                <span className="text-slate-400 block text-[10px]">Protein</span>
                <span className="font-mono font-bold text-emerald-400">142g</span>
              </div>
              <div>
                <span className="text-slate-400 block text-[10px]">Carbs</span>
                <span className="font-mono font-bold text-cyan-400">210g</span>
              </div>
              <div>
                <span className="text-slate-400 block text-[10px]">Fat</span>
                <span className="font-mono font-bold text-amber-400">65g</span>
              </div>
            </div>
          </div>

          {/* Card 2: Meal Plan */}
          <div className="rounded-2xl border border-slate-800 bg-slate-900 p-6 flex flex-col justify-between space-y-4">
            <div className="flex items-center justify-between">
              <h3 className="text-sm font-bold text-slate-200">Meal Plan</h3>
              <span className="text-[10px] font-mono text-emerald-400">Vegetarian</span>
            </div>

            <div className="space-y-3">
              {meals.map((m, idx) => (
                <div key={idx} className="flex items-center justify-between p-2.5 rounded-xl bg-slate-950/60 border border-slate-800/80 text-xs">
                  <div>
                    <span className="text-[10px] font-mono text-amber-400 uppercase">{m.type}</span>
                    <p className="font-semibold text-slate-200 mt-0.5">{m.name}</p>
                  </div>
                  <span className="font-mono text-slate-400 text-[11px]">{m.kcal} kcal</span>
                </div>
              ))}
            </div>

            <div className="pt-2 text-[11px] text-slate-400 flex items-center gap-1.5">
              <Check className="h-3.5 w-3.5 text-emerald-400" /> High-protein Indian & Western recipes
            </div>
          </div>

          {/* Card 3: Water Intake */}
          <div className="rounded-2xl border border-slate-800 bg-slate-900 p-6 flex flex-col justify-between space-y-4">
            <div className="flex items-center justify-between">
              <h3 className="text-sm font-bold text-slate-200">Water Intake</h3>
              <Droplets className="h-4 w-4 text-cyan-400" />
            </div>

            <div>
              <div className="flex items-baseline gap-1">
                <span className="text-3xl font-extrabold text-slate-100 font-mono">2.1L</span>
                <span className="text-xs text-slate-400 font-mono">/ 3L</span>
              </div>
              <span className="text-[10px] text-cyan-400 font-mono mt-1 block">70% Daily Goal Achieved</span>
            </div>

            {/* Weekly Bar Chart Simulation */}
            <div className="flex items-end justify-between h-24 gap-1.5 pt-4">
              {waterBars.map((height, i) => (
                <div key={i} className="flex-1 flex flex-col items-center gap-1">
                  <div
                    className="w-full bg-cyan-500/80 rounded-t-md transition-all"
                    style={{ height: `${height}%` }}
                  />
                  <span className="text-[9px] text-slate-500 font-mono">M T W T F S S`[i]</span>
                </div>
              ))}
            </div>
          </div>

        </div>

      </div>
    </section>
  )
}
