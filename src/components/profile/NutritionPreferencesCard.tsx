import React from 'react'
import type { NutritionPreferencesData } from '../../types'
import { Utensils, Flame, BicepsFlexed, Wheat, Droplet } from 'lucide-react'

export interface NutritionPreferencesCardProps {
  pref: NutritionPreferencesData
  onEditClick: () => void
}

export const NutritionPreferencesCard: React.FC<NutritionPreferencesCardProps> = ({ pref, onEditClick }) => {
  return (
    <div className="rounded-3xl border border-slate-800 bg-slate-900/90 p-5 space-y-3.5 text-left shadow-2xl h-full flex flex-col justify-between">
      <div className="flex items-center justify-between pb-2 border-b border-slate-800/80">
        <h3 className="text-sm font-extrabold text-slate-100">Nutrition Preferences</h3>
        <button
          type="button"
          onClick={onEditClick}
          className="text-xs font-semibold text-emerald-400 hover:text-emerald-300 cursor-pointer"
        >
          Edit
        </button>
      </div>

      <div className="space-y-3 font-mono text-xs">
        <div className="flex items-center justify-between py-1 border-b border-slate-800/50">
          <div className="flex items-center gap-2">
            <Utensils className="h-4 w-4 text-emerald-400" />
            <span className="text-slate-400 font-bold">Dietary Preference</span>
          </div>
          <span className="font-extrabold text-slate-100">{pref.dietaryPreference}</span>
        </div>

        <div className="flex items-center justify-between py-1 border-b border-slate-800/50">
          <div className="flex items-center gap-2">
            <Flame className="h-4 w-4 text-emerald-400" />
            <span className="text-slate-400 font-bold">Daily Calorie Target</span>
          </div>
          <span className="font-extrabold text-slate-100">
            {pref.dailyCalorieTarget && pref.dailyCalorieTarget > 0 ? `${pref.dailyCalorieTarget.toLocaleString()} kcal` : 'Not set'}
          </span>
        </div>

        <div className="flex items-center justify-between py-1 border-b border-slate-800/50">
          <div className="flex items-center gap-2">
            <BicepsFlexed className="h-4 w-4 text-emerald-400" />
            <span className="text-slate-400 font-bold">Protein Target</span>
          </div>
          <span className="font-extrabold text-slate-100">
            {pref.proteinTargetGrams && pref.proteinTargetGrams > 0 ? `${pref.proteinTargetGrams} g` : 'Not set'}
          </span>
        </div>

        <div className="flex items-center justify-between py-1 border-b border-slate-800/50">
          <div className="flex items-center gap-2">
            <Wheat className="h-4 w-4 text-emerald-400" />
            <span className="text-slate-400 font-bold">Carb Target</span>
          </div>
          <span className="font-extrabold text-slate-100">
            {pref.carbTargetGrams && pref.carbTargetGrams > 0 ? `${pref.carbTargetGrams} g` : 'Not set'}
          </span>
        </div>

        <div className="flex items-center justify-between py-1">
          <div className="flex items-center gap-2">
            <Droplet className="h-4 w-4 text-emerald-400" />
            <span className="text-slate-400 font-bold">Hydration Goal</span>
          </div>
          <span className="font-extrabold text-slate-100">
            {pref.hydrationGoalLiters && pref.hydrationGoalLiters > 0 ? `${pref.hydrationGoalLiters.toFixed(1)} L / day` : 'Not set'}
          </span>
        </div>
      </div>
    </div>
  )
}
