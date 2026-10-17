import React, { useState } from 'react'
import type { Meal } from '../../types'
import { ChevronRight, Trash2 } from 'lucide-react'

export interface TodaysMealsProps {
  meals: Meal[]
  onDeleteFood?: (mealId: string, foodId: string) => void
  isDeletingFood?: boolean
}

export const TodaysMeals: React.FC<TodaysMealsProps> = ({ meals, onDeleteFood }) => {
  const [expandedMealId, setExpandedMealId] = useState<string | null>(null)

  const toggleExpand = (mealId: string) => {
    setExpandedMealId((prev) => (prev === mealId ? null : mealId))
  }

  return (
    <div className="rounded-3xl border border-slate-800 bg-slate-900/90 p-5 space-y-4 text-left shadow-2xl">
      <h3 className="text-base font-extrabold text-slate-100">Today's Meals</h3>

      <div className="relative pl-6 space-y-4">
        {/* Vertical Timeline Line */}
        <div className="absolute left-2.5 top-3 bottom-3 w-0.5 bg-slate-800" />

        {meals.map((meal) => {
          const isExpanded = expandedMealId === meal.id
          const hasFoods = meal.foods && meal.foods.length > 0

          return (
            <div key={meal.id} className="relative space-y-2">
              <div
                onClick={() => hasFoods && toggleExpand(meal.id)}
                className={`relative flex items-center justify-between gap-4 group rounded-2xl p-1.5 transition-colors ${
                  hasFoods ? 'cursor-pointer hover:bg-slate-800/30' : ''
                }`}
              >
                {/* Timeline Dot */}
                <div className="absolute -left-6 top-1/2 -translate-y-1/2 flex h-4 w-4 items-center justify-center rounded-full bg-slate-950 border border-emerald-500">
                  <span className="h-1.5 w-1.5 rounded-full bg-emerald-400" />
                </div>

                {/* Time Indicator Left */}
                <span className="text-[10px] font-mono text-slate-400 w-16 shrink-0">{meal.time}</span>

                {/* Food Circular Thumbnail */}
                <div className="h-14 w-14 rounded-full overflow-hidden bg-slate-950 border border-slate-800 shrink-0">
                  <img
                    src={meal.image || '/assets/meal_oatmeal_berries.jpg'}
                    alt={meal.name}
                    className="w-full h-full object-cover group-hover:scale-105 transition-transform"
                  />
                </div>

                {/* Meal Details Center */}
                <div className="flex-1 space-y-1">
                  <h4 className="text-xs font-bold text-slate-100 group-hover:text-emerald-400 transition-colors">
                    {meal.name}
                  </h4>
                  <p className="text-[10px] text-slate-400 line-clamp-2 leading-tight font-normal">
                    {meal.foodList && meal.foodList.length > 0
                      ? meal.foodList.join(', ')
                      : 'No foods logged yet'}
                  </p>
                </div>

                {/* Calories & Macros Right */}
                <div className="text-right font-mono shrink-0 space-y-1">
                  <span className="text-xs font-extrabold text-emerald-400 block">{meal.totalCalories} kcal</span>
                  <div className="flex items-center gap-1.5 text-[9px] text-slate-400">
                    <span>P {meal.totalProteinGrams}g</span>
                    <span>C {meal.totalCarbsGrams}g</span>
                    <span>F {meal.totalFatGrams}g</span>
                  </div>
                </div>

                {/* Chevron Right */}
                {hasFoods && (
                  <button
                    type="button"
                    aria-label="View meal details"
                    onClick={(e) => {
                      e.stopPropagation()
                      toggleExpand(meal.id)
                    }}
                    className="p-1 text-slate-500 hover:text-slate-200 transition-transform cursor-pointer"
                  >
                    <ChevronRight className={`h-4 w-4 transition-transform ${isExpanded ? 'rotate-90' : ''}`} />
                  </button>
                )}
              </div>

              {/* Expanded Food Items List with Food Deletion */}
              {isExpanded && hasFoods && (
                <div className="ml-16 space-y-1.5 pt-1.5 pb-2 font-mono">
                  {meal.foods.map((food) => (
                    <div
                      key={food.id}
                      className="flex items-center justify-between text-[11px] text-slate-300 py-1.5 px-3 rounded-xl bg-slate-950/60 border border-slate-800/60"
                    >
                      <div>
                        <span className="font-bold text-slate-200">{food.name}</span>
                        <span className="text-[10px] text-slate-500 ml-2">
                          {food.servingSizeGrams ? `${food.servingSizeGrams}g` : ''}
                        </span>
                      </div>
                      <div className="flex items-center gap-3">
                        <span className="text-emerald-400 font-bold">{food.calories} kcal</span>
                        {onDeleteFood && (
                          <button
                            type="button"
                            onClick={(e) => {
                              e.stopPropagation()
                              onDeleteFood(meal.id, food.id)
                            }}
                            title="Delete food item"
                            className="p-1 text-slate-500 hover:text-rose-400 transition-colors cursor-pointer"
                          >
                            <Trash2 className="h-3.5 w-3.5" />
                          </button>
                        )}
                      </div>
                    </div>
                  ))}
                </div>
              )}
            </div>
          )
        })}
      </div>
    </div>
  )
}
