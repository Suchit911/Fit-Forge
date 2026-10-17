import React from 'react'
import { Link } from 'react-router-dom'
import { useNutrition, useUser } from '../../hooks'

export const DailyNutritionCard: React.FC = () => {
  const { nutrition } = useNutrition()
  const { user } = useUser()

  const targetCalories = user?.targetCalories || 0
  const targetProtein = user?.targetProteinGrams || 0
  const targetCarbs = user?.targetCarbsGrams || 0
  const targetFat = user?.targetFatGrams || 0

  // Derive honest logged amounts
  const hasMeals = Boolean(nutrition?.meals && nutrition.meals.some((m) => m.foods && m.foods.length > 0))
  const consumedCalories = hasMeals ? (nutrition?.consumedCalories || 0) : 0
  const consumedProtein = hasMeals ? (nutrition?.consumedProteinGrams || 0) : 0
  const consumedCarbs = hasMeals ? (nutrition?.consumedCarbsGrams || 0) : 0
  const consumedFat = hasMeals ? (nutrition?.consumedFatGrams || 0) : 0

  const pct = targetCalories > 0 ? Math.min(100, Math.round((consumedCalories / targetCalories) * 100)) : 0
  const strokeDashoffset = Math.max(0, 364 - (364 * pct) / 100)

  return (
    <div className="rounded-2xl border border-slate-800 bg-slate-900/90 p-5 text-left flex flex-col justify-between space-y-4">
      
      {/* Header */}
      <div className="flex items-center justify-between pb-3 border-b border-slate-800/80">
        <h3 className="text-sm font-extrabold text-slate-100">Daily Nutrition</h3>
        <Link
          to="/nutrition"
          className="text-xs font-semibold text-slate-400 hover:text-slate-200 transition-colors"
        >
          See More
        </Link>
      </div>

      {/* Donut Chart Visualization */}
      <div className="relative flex items-center justify-center my-2">
        <svg className="h-36 w-36 transform -rotate-90">
          {/* Track background */}
          <circle cx="72" cy="72" r="58" stroke="#1e293b" strokeWidth="12" fill="transparent" />
          {/* Progress Ring */}
          <circle
            cx="72"
            cy="72"
            r="58"
            stroke="url(#macroGradient)"
            strokeWidth="12"
            strokeDasharray="364"
            strokeDashoffset={strokeDashoffset}
            strokeLinecap="round"
            fill="transparent"
          />
          <defs>
            <linearGradient id="macroGradient" x1="0%" y1="0%" x2="100%" y2="100%">
              <stop offset="0%" stopColor="#10b981" />
              <stop offset="50%" stopColor="#06b6d4" />
              <stop offset="100%" stopColor="#f59e0b" />
            </linearGradient>
          </defs>
        </svg>

        <div className="absolute text-center">
          <span className="text-2xl font-extrabold text-slate-100 font-mono">
            {consumedCalories.toLocaleString()}
          </span>
          <span className="block text-[10px] text-slate-400 font-mono uppercase">
            {targetCalories > 0 ? `/ ${targetCalories.toLocaleString()} kcal` : 'No Target'}
          </span>
          <span className="text-xs font-bold text-emerald-400 font-mono">{pct}%</span>
        </div>
      </div>

      {/* Macro Legend Table */}
      <div className="grid grid-cols-3 gap-2 pt-3 border-t border-slate-800/80 text-center text-xs">
        <div>
          <span className="text-slate-400 flex items-center justify-center gap-1 text-[10px]">
            <span className="h-2 w-2 rounded-full bg-emerald-400" /> Protein
          </span>
          <span className="font-mono font-bold text-slate-200 block mt-1">
            {consumedProtein}g <span className="text-slate-500 font-normal">/ {targetProtein > 0 ? `${targetProtein}g` : '--'}</span>
          </span>
        </div>

        <div>
          <span className="text-slate-400 flex items-center justify-center gap-1 text-[10px]">
            <span className="h-2 w-2 rounded-full bg-cyan-400" /> Carbs
          </span>
          <span className="font-mono font-bold text-slate-200 block mt-1">
            {consumedCarbs}g <span className="text-slate-500 font-normal">/ {targetCarbs > 0 ? `${targetCarbs}g` : '--'}</span>
          </span>
        </div>

        <div>
          <span className="text-slate-400 flex items-center justify-center gap-1 text-[10px]">
            <span className="h-2 w-2 rounded-full bg-amber-400" /> Fat
          </span>
          <span className="font-mono font-bold text-slate-200 block mt-1">
            {consumedFat}g <span className="text-slate-500 font-normal">/ {targetFat > 0 ? `${targetFat}g` : '--'}</span>
          </span>
        </div>
      </div>

    </div>
  )
}
