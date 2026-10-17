import React, { useState, useEffect } from 'react'
import { Modal, Button, Input } from '../ui'
import { Check, Search, AlertCircle } from 'lucide-react'
import { nutritionService } from '../../services/nutritionService'
import type { CatalogFood } from '../../types'

export interface MealLoggerModalProps {
  isOpen: boolean
  onClose: () => void
  onSuccess: () => void
  date?: string
}

export const MealLoggerModal: React.FC<MealLoggerModalProps> = ({
  isOpen,
  onClose,
  onSuccess,
  date,
}) => {
  const [mealType, setMealType] = useState('breakfast')
  const [foodName, setFoodName] = useState('')
  const [calories, setCalories] = useState('350')
  const [protein, setProtein] = useState('25')
  const [carbs, setCarbs] = useState('40')
  const [fat, setFat] = useState('10')
  const [submitted, setSubmitted] = useState(false)
  const [isSubmitting, setIsSubmitting] = useState(false)
  const [errorMessage, setErrorMessage] = useState<string | null>(null)
  const [suggestions, setSuggestions] = useState<CatalogFood[]>([])
  const [selectedCatalogFood, setSelectedCatalogFood] = useState<CatalogFood | null>(null)

  // Live catalogue search debounce
  useEffect(() => {
    if (!isOpen) {
      setSuggestions([])
      setErrorMessage(null)
      setSelectedCatalogFood(null)
      return
    }

    if (foodName.trim().length < 2) {
      setSuggestions([])
      return
    }

    let active = true
    const timer = setTimeout(async () => {
      const results = await nutritionService.searchFoods(foodName.trim())
      if (active) {
        setSuggestions(results.slice(0, 5))
      }
    }, 250)

    return () => {
      active = false
      clearTimeout(timer)
    }
  }, [foodName, isOpen])

  const handleSelectSuggestion = (food: CatalogFood) => {
    setSelectedCatalogFood(food)
    setFoodName(food.name)
    const serving = food.defaultServingGrams || 100
    const factor = serving / 100
    setCalories(String(Math.round(food.caloriesPer100g * factor)))
    setProtein(String(Math.round(food.proteinGramsPer100g * factor * 10) / 10))
    setCarbs(String(Math.round(food.carbsGramsPer100g * factor * 10) / 10))
    setFat(String(Math.round(food.fatGramsPer100g * factor * 10) / 10))
    setSuggestions([])
  }

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault()
    if (!foodName.trim()) return

    setIsSubmitting(true)
    setErrorMessage(null)

    try {
      let fiber = 0
      let sugar = 0
      let sodium = 0
      let servingSizeGrams = 100

      if (selectedCatalogFood && selectedCatalogFood.name.toLowerCase() === foodName.trim().toLowerCase()) {
        servingSizeGrams = selectedCatalogFood.defaultServingGrams || 100
        const factor = servingSizeGrams / 100
        fiber = Math.round(selectedCatalogFood.fiberGramsPer100g * factor * 10) / 10
        sugar = Math.round(selectedCatalogFood.sugarGramsPer100g * factor * 10) / 10
        sodium = Math.round(selectedCatalogFood.sodiumMgPer100g * factor * 10) / 10
      }

      await nutritionService.logMealItem(
        mealType,
        foodName,
        Number(calories),
        Number(protein),
        Number(carbs),
        Number(fat),
        {
          fiber,
          sugar,
          sodium,
          servingSizeGrams,
          date,
        }
      )

      setSubmitted(true)
      setTimeout(() => {
        onSuccess()
        setSubmitted(false)
        setFoodName('')
        setSelectedCatalogFood(null)
        onClose()
      }, 600)
    } catch (err: unknown) {
      const msg = err instanceof Error ? err.message : 'Failed to log meal. Please try again.'
      setErrorMessage(msg)
    } finally {
      setIsSubmitting(false)
    }
  }

  return (
    <Modal isOpen={isOpen} onClose={onClose} title="Log Meal & Foods">
      <form onSubmit={handleSubmit} className="space-y-4 text-left pt-1 font-mono text-xs">
        {submitted ? (
          <div className="flex flex-col items-center justify-center p-6 text-center space-y-2">
            <div className="flex h-12 w-12 items-center justify-center rounded-full bg-emerald-500/20 text-emerald-400 border border-emerald-500/40">
              <Check className="h-6 w-6" />
            </div>
            <h4 className="text-sm font-extrabold text-slate-100">Meal Logged!</h4>
            <p className="text-xs text-slate-400">Nutrients added to today's intake summary.</p>
          </div>
        ) : (
          <>
            {errorMessage && (
              <div className="flex items-center gap-2 p-3 rounded-xl bg-red-500/10 border border-red-500/30 text-red-400 text-xs">
                <AlertCircle className="h-4 w-4 shrink-0" />
                <span>{errorMessage}</span>
              </div>
            )}

            <div className="space-y-1">
              <label className="text-slate-300 font-bold block">Meal Type</label>
              <select
                value={mealType}
                onChange={(e) => setMealType(e.target.value)}
                className="w-full h-9 rounded-xl border border-slate-800 bg-slate-950 px-3 text-xs text-slate-200 focus:outline-none"
              >
                <option value="breakfast">Breakfast</option>
                <option value="lunch">Lunch</option>
                <option value="snack">Pre-Workout Snack</option>
                <option value="dinner">Dinner</option>
                <option value="snack">Evening Snack</option>
              </select>
            </div>

            <div className="relative">
              <Input
                label="Food Name / Item"
                placeholder="e.g. Scrambled Eggs & Toast or Chicken Breast"
                value={foodName}
                onChange={(e) => {
                  setFoodName(e.target.value)
                  if (selectedCatalogFood && e.target.value !== selectedCatalogFood.name) {
                    setSelectedCatalogFood(null)
                  }
                }}
                required
              />

              {/* Curated Food Catalogue Dropdown Suggestions */}
              {suggestions.length > 0 && (
                <div className="absolute left-0 right-0 top-full mt-1 z-50 rounded-xl border border-slate-800 bg-slate-950/95 backdrop-blur-md shadow-2xl overflow-hidden divide-y divide-slate-800/60">
                  <div className="px-3 py-1.5 text-[10px] text-slate-400 uppercase tracking-wider flex items-center gap-1.5">
                    <Search className="h-3 w-3 text-emerald-400" />
                    <span>Catalogue Foods (Click to Auto-fill)</span>
                  </div>
                  {suggestions.map((food) => (
                    <button
                      key={food.id}
                      type="button"
                      onClick={() => handleSelectSuggestion(food)}
                      className="w-full px-3 py-2 text-left hover:bg-slate-900 flex items-center justify-between transition-colors cursor-pointer"
                    >
                      <div>
                        <span className="font-bold text-slate-200 block text-xs">{food.name}</span>
                        <span className="text-[10px] text-slate-400">
                          {food.defaultServingGrams}g ({food.category})
                        </span>
                      </div>
                      <span className="text-emerald-400 font-extrabold text-xs">
                        {Math.round((food.caloriesPer100g / 100) * food.defaultServingGrams)} kcal
                      </span>
                    </button>
                  ))}
                </div>
              )}
            </div>

            <div className="grid grid-cols-2 gap-3">
              <Input
                label="Calories (kcal)"
                type="number"
                value={calories}
                onChange={(e) => setCalories(e.target.value)}
                required
              />
              <Input
                label="Protein (g)"
                type="number"
                value={protein}
                onChange={(e) => setProtein(e.target.value)}
                required
              />
            </div>

            <div className="grid grid-cols-2 gap-3">
              <Input
                label="Carbs (g)"
                type="number"
                value={carbs}
                onChange={(e) => setCarbs(e.target.value)}
                required
              />
              <Input
                label="Fat (g)"
                type="number"
                value={fat}
                onChange={(e) => setFat(e.target.value)}
                required
              />
            </div>

            <div className="flex gap-3 pt-2">
              <Button
                type="button"
                variant="secondary"
                onClick={onClose}
                className="flex-1"
                disabled={isSubmitting}
              >
                Cancel
              </Button>
              <Button
                type="submit"
                variant="primary"
                className="flex-1"
                disabled={isSubmitting}
              >
                {isSubmitting ? 'Logging...' : 'Log Meal'}
              </Button>
            </div>
          </>
        )}
      </form>
    </Modal>
  )
}
