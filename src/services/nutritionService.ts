import type { DailyNutrition, CatalogFood, WeeklyNutritionDay } from '../types'
import { getIdToken } from '../lib/firebase'

const API_BASE_URL = import.meta.env.VITE_API_BASE_URL || 'http://localhost:8000/api/v1'

export function getTodayDateString(): string {
  const d = new Date()
  const year = d.getFullYear()
  const month = String(d.getMonth() + 1).padStart(2, '0')
  const day = String(d.getDate()).padStart(2, '0')
  return `${year}-${month}-${day}`
}

export function formatDisplayDate(dateStr: string): string {
  const [y, m, d] = dateStr.split('-').map(Number)
  const targetDate = new Date(y, m - 1, d)
  const todayStr = getTodayDateString()
  if (dateStr === todayStr) {
    return `Today, ${targetDate.toLocaleDateString('en-US', { month: 'short', day: 'numeric', year: 'numeric' })}`
  }
  return targetDate.toLocaleDateString('en-US', { month: 'short', day: 'numeric', year: 'numeric' })
}

export function shiftDateString(dateStr: string, days: number): string {
  const [y, m, d] = dateStr.split('-').map(Number)
  const date = new Date(y, m - 1, d)
  date.setDate(date.getDate() + days)
  const year = date.getFullYear()
  const month = String(date.getMonth() + 1).padStart(2, '0')
  const day = String(date.getDate()).padStart(2, '0')
  return `${year}-${month}-${day}`
}

export function normalizeMealType(typeOrId: string): 'breakfast' | 'lunch' | 'dinner' | 'snack' {
  const lower = typeOrId.toLowerCase()
  if (lower.includes('breakfast')) return 'breakfast'
  if (lower.includes('lunch')) return 'lunch'
  if (lower.includes('dinner')) return 'dinner'
  return 'snack'
}

export function createEmptyDailyNutrition(dateStr: string): DailyNutrition {
  return {
    date: formatDisplayDate(dateStr),
    targetCalories: 0,
    consumedCalories: 0,
    targetProteinGrams: 0,
    consumedProteinGrams: 0,
    targetCarbsGrams: 0,
    consumedCarbsGrams: 0,
    targetFatGrams: 0,
    consumedFatGrams: 0,
    targetFiberGrams: 0,
    consumedFiberGrams: 0,
    targetSugarGrams: 0,
    consumedSugarGrams: 0,
    targetSodiumMg: 0,
    consumedSodiumMg: 0,
    waterIntakeLiters: 0,
    waterTargetLiters: 0,
    meals: [
      {
        id: 'm_breakfast',
        time: '8:00 AM',
        type: 'breakfast',
        name: 'Breakfast',
        totalCalories: 0,
        totalProteinGrams: 0,
        totalCarbsGrams: 0,
        totalFatGrams: 0,
        totalFiberGrams: 0,
        totalSugarGrams: 0,
        totalSodiumMg: 0,
        foodList: [],
        foods: [],
      },
      {
        id: 'm_lunch',
        time: '12:30 PM',
        type: 'lunch',
        name: 'Lunch',
        totalCalories: 0,
        totalProteinGrams: 0,
        totalCarbsGrams: 0,
        totalFatGrams: 0,
        totalFiberGrams: 0,
        totalSugarGrams: 0,
        totalSodiumMg: 0,
        foodList: [],
        foods: [],
      },
      {
        id: 'm_dinner',
        time: '7:30 PM',
        type: 'dinner',
        name: 'Dinner',
        totalCalories: 0,
        totalProteinGrams: 0,
        totalCarbsGrams: 0,
        totalFatGrams: 0,
        totalFiberGrams: 0,
        totalSugarGrams: 0,
        totalSodiumMg: 0,
        foodList: [],
        foods: [],
      },
      {
        id: 'm_snack',
        time: '4:00 PM',
        type: 'snack',
        name: 'Snacks',
        totalCalories: 0,
        totalProteinGrams: 0,
        totalCarbsGrams: 0,
        totalFatGrams: 0,
        totalFiberGrams: 0,
        totalSugarGrams: 0,
        totalSodiumMg: 0,
        foodList: [],
        foods: [],
      },
    ],
    nutrientTargets: [],
    calorieFlow: [],
    weeklySummary: [],
    insights: [],
  }
}

export const nutritionService = {
  /**
   * Retrieves daily nutrition log for the selected date (YYYY-MM-DD).
   * Returns honest empty daily nutrition when unauthenticated or backend unreachable.
   */
  async getDailyNutrition(date?: string): Promise<DailyNutrition> {
    const token = await getIdToken()
    const targetDate = date || getTodayDateString()

    if (token) {
      try {
        const res = await fetch(`${API_BASE_URL}/nutrition/daily?date=${targetDate}`, {
          headers: { Authorization: `Bearer ${token}` },
        })
        if (res.ok) {
          return await res.json()
        }
      } catch (err) {
        console.warn('FastAPI /nutrition/daily unreachable:', err)
      }
    }

    return createEmptyDailyNutrition(targetDate)
  },

  /**
   * Logs a food item into a meal.
   * STRICT: NEVER silently succeeds with mock data on failure. Throws on error.
   */
  async logMealItem(
    mealIdOrType: string,
    foodName: string,
    calories: number,
    protein: number,
    carbs: number,
    fat: number,
    options?: {
      fiber?: number
      sugar?: number
      sodium?: number
      servingSizeGrams?: number
      date?: string
    }
  ): Promise<DailyNutrition> {
    const token = await getIdToken()
    if (!token) {
      throw new Error('Authentication required to log meal items.')
    }

    const payload = {
      mealType: normalizeMealType(mealIdOrType),
      foodName: foodName.trim(),
      calories: Math.max(0, Math.round(Number(calories))),
      proteinGrams: Math.max(0, Number(protein)),
      carbsGrams: Math.max(0, Number(carbs)),
      fatGrams: Math.max(0, Number(fat)),
      fiberGrams: Math.max(0, Number(options?.fiber || 0)),
      sugarGrams: Math.max(0, Number(options?.sugar || 0)),
      sodiumMg: Math.max(0, Number(options?.sodium || 0)),
      servingSizeGrams: Math.max(1, Number(options?.servingSizeGrams || 100)),
      date: options?.date || getTodayDateString(),
    }

    const res = await fetch(`${API_BASE_URL}/nutrition/meals`, {
      method: 'POST',
      headers: {
        'Content-Type': 'application/json',
        Authorization: `Bearer ${token}`,
      },
      body: JSON.stringify(payload),
    })

    if (!res.ok) {
      const errorData = await res.json().catch(() => ({}))
      const msg = errorData.detail || errorData.message || `Failed to log meal (${res.status})`
      throw new Error(typeof msg === 'string' ? msg : JSON.stringify(msg))
    }

    return await res.json()
  },

  /**
   * Logs water intake.
   * STRICT: NEVER silently succeeds with mock data on failure. Throws on error.
   */
  async logWater(amountLiters: number = 0.3, date?: string): Promise<DailyNutrition> {
    const token = await getIdToken()
    if (!token) {
      throw new Error('Authentication required to log water intake.')
    }

    const payload = {
      amountLiters: Number(amountLiters),
      date: date || getTodayDateString(),
    }

    const res = await fetch(`${API_BASE_URL}/nutrition/water`, {
      method: 'POST',
      headers: {
        'Content-Type': 'application/json',
        Authorization: `Bearer ${token}`,
      },
      body: JSON.stringify(payload),
    })

    if (!res.ok) {
      const errorData = await res.json().catch(() => ({}))
      const msg = errorData.detail || errorData.message || `Failed to log water (${res.status})`
      throw new Error(typeof msg === 'string' ? msg : JSON.stringify(msg))
    }

    return await res.json()
  },

  /**
   * Deletes a food item from a meal.
   * STRICT: NEVER silently succeeds with mock data on failure. Throws on error.
   */
  async deleteMealFood(mealId: string, foodId: string, date?: string): Promise<DailyNutrition> {
    const token = await getIdToken()
    if (!token) {
      throw new Error('Authentication required to delete food items.')
    }

    const targetDate = date || getTodayDateString()
    const res = await fetch(
      `${API_BASE_URL}/nutrition/meals/${encodeURIComponent(mealId)}/foods/${encodeURIComponent(foodId)}?date=${targetDate}`,
      {
        method: 'DELETE',
        headers: { Authorization: `Bearer ${token}` },
      }
    )

    if (!res.ok) {
      const errorData = await res.json().catch(() => ({}))
      const msg = errorData.detail || errorData.message || `Failed to delete food item (${res.status})`
      throw new Error(typeof msg === 'string' ? msg : JSON.stringify(msg))
    }

    return await res.json()
  },

  /**
   * Retrieves 7-day weekly nutrition summary for the selected date.
   */
  async getWeeklyNutrition(date?: string): Promise<WeeklyNutritionDay[]> {
    const token = await getIdToken()
    const targetDate = date || getTodayDateString()

    if (token) {
      try {
        const res = await fetch(`${API_BASE_URL}/nutrition/weekly?date=${targetDate}`, {
          headers: { Authorization: `Bearer ${token}` },
        })
        if (res.ok) {
          return await res.json()
        }
      } catch (err) {
        console.warn('FastAPI /nutrition/weekly unreachable:', err)
      }
    }

    return []
  },

  /**
   * Searches the curated food catalogue.
   */
  async searchFoods(query: string, category?: string): Promise<CatalogFood[]> {
    const token = await getIdToken()
    if (!token) return []

    try {
      const url = new URL(`${API_BASE_URL}/nutrition/foods`)
      if (query) url.searchParams.set('query', query)
      if (category) url.searchParams.set('category', category)

      const res = await fetch(url.toString(), {
        headers: { Authorization: `Bearer ${token}` },
      })
      if (res.ok) {
        return await res.json()
      }
    } catch (err) {
      console.warn('Error searching food catalogue:', err)
    }
    return []
  },
}
