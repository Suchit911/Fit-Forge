from datetime import datetime, timezone, timedelta
from typing import Optional, List, Dict, Any
from fastapi import Depends
from ..repositories.nutrition_repository import NutritionRepository, get_nutrition_repository
from ..repositories.user_repository import UserRepository, get_user_repository
from ..schemas.nutrition import (
    DailyNutritionSchema,
    MealSchema,
    FoodItemSchema,
    MealLogCreate,
    WaterLogCreate,
    NutrientTargetItemSchema,
    CalorieFlowEntrySchema,
    WeeklyNutritionDaySchema,
    NutritionInsightItemSchema,
    CatalogFoodSchema,
)
from ..utils.logger import logger


def get_today_iso_date() -> str:
    """Returns today's date in YYYY-MM-DD format in UTC."""
    return datetime.now(timezone.utc).strftime("%Y-%m-%d")


def create_default_meals() -> List[Dict[str, Any]]:
    """Creates the standard 4 meal categories for a fresh day."""
    return [
        {
            "id": "m_breakfast",
            "time": "7:30 AM",
            "type": "breakfast",
            "name": "Breakfast",
            "totalCalories": 0,
            "totalProteinGrams": 0.0,
            "totalCarbsGrams": 0.0,
            "totalFatGrams": 0.0,
            "totalFiberGrams": 0.0,
            "totalSugarGrams": 0.0,
            "totalSodiumMg": 0.0,
            "image": "/assets/meal_oatmeal_berries.jpg",
            "foodList": [],
            "foods": [],
        },
        {
            "id": "m_lunch",
            "time": "12:30 PM",
            "type": "lunch",
            "name": "Lunch",
            "totalCalories": 0,
            "totalProteinGrams": 0.0,
            "totalCarbsGrams": 0.0,
            "totalFatGrams": 0.0,
            "totalFiberGrams": 0.0,
            "totalSugarGrams": 0.0,
            "totalSodiumMg": 0.0,
            "image": "/assets/workout_lower_body.jpg",
            "foodList": [],
            "foods": [],
        },
        {
            "id": "m_snack",
            "time": "4:30 PM",
            "type": "snack",
            "name": "Pre-Workout Snack",
            "totalCalories": 0,
            "totalProteinGrams": 0.0,
            "totalCarbsGrams": 0.0,
            "totalFatGrams": 0.0,
            "totalFiberGrams": 0.0,
            "totalSugarGrams": 0.0,
            "totalSodiumMg": 0.0,
            "image": "/assets/workout_hiit_ropes.jpg",
            "foodList": [],
            "foods": [],
        },
        {
            "id": "m_dinner",
            "time": "8:00 PM",
            "type": "dinner",
            "name": "Dinner",
            "totalCalories": 0,
            "totalProteinGrams": 0.0,
            "totalCarbsGrams": 0.0,
            "totalFatGrams": 0.0,
            "totalFiberGrams": 0.0,
            "totalSugarGrams": 0.0,
            "totalSodiumMg": 0.0,
            "image": "/assets/workout_upper_pull.jpg",
            "foodList": [],
            "foods": [],
        },
    ]


class NutritionService:
    """
    Domain service for managing daily nutrition logs, meals, water intake,
    deterministic calorie/macronutrient aggregation, and curated food search.
    """

    def __init__(
        self,
        nutrition_repo: Optional[NutritionRepository] = None,
        user_repo: Optional[UserRepository] = None,
        notification_service: Optional[Any] = None,
    ):
        self._nutrition_repo = nutrition_repo
        self._user_repo = user_repo
        self._notification_service = notification_service

    @property
    def notification_service(self) -> Any:
        if self._notification_service:
            return self._notification_service
        from .notification_service import get_notification_service
        return get_notification_service()

    @property
    def nutrition_repo(self) -> NutritionRepository:
        return self._nutrition_repo or get_nutrition_repository()

    @property
    def user_repo(self) -> UserRepository:
        return self._user_repo or get_user_repository()

    # =========================================================================
    # DETERMINISTIC CALCULATION HELPERS
    # =========================================================================

    def _get_user_targets(self, uid: str) -> Dict[str, Any]:
        """Pulls nutritional targets from the user profile or provides Phase 5 defaults."""
        profile = self.user_repo.get_by_uid(uid)
        if profile:
            return {
                "targetCalories": profile.targetCalories if profile.targetCalories is not None else 2400,
                "targetProteinGrams": float(profile.targetProteinGrams) if profile.targetProteinGrams is not None else 160.0,
                "targetCarbsGrams": float(profile.targetCarbsGrams) if profile.targetCarbsGrams is not None else 250.0,
                "targetFatGrams": float(profile.targetFatGrams) if profile.targetFatGrams is not None else 80.0,
                "targetFiberGrams": 30.0,
                "targetSugarGrams": 50.0,
                "targetSodiumMg": 2300.0,
                "waterTargetLiters": 3.0,
            }
        return {
            "targetCalories": 2400,
            "targetProteinGrams": 160.0,
            "targetCarbsGrams": 250.0,
            "targetFatGrams": 80.0,
            "targetFiberGrams": 30.0,
            "targetSugarGrams": 50.0,
            "targetSodiumMg": 2300.0,
            "waterTargetLiters": 3.0,
        }

    def _build_nutrient_targets(self, log_dict: Dict[str, Any]) -> List[NutrientTargetItemSchema]:
        """Constructs target items with current consumed, goal, percentage, and UI colors."""
        items = [
            ("Calories", log_dict.get("consumedCalories", 0), log_dict.get("targetCalories", 2400), "kcal", "#10b981"),
            ("Protein", log_dict.get("consumedProteinGrams", 0.0), log_dict.get("targetProteinGrams", 160.0), "g", "#3b82f6"),
            ("Carbs", log_dict.get("consumedCarbsGrams", 0.0), log_dict.get("targetCarbsGrams", 250.0), "g", "#f59e0b"),
            ("Fat", log_dict.get("consumedFatGrams", 0.0), log_dict.get("targetFatGrams", 80.0), "g", "#a855f7"),
            ("Fiber", log_dict.get("consumedFiberGrams", 0.0), log_dict.get("targetFiberGrams", 30.0), "g", "#10b981"),
            ("Sugar", log_dict.get("consumedSugarGrams", 0.0), log_dict.get("targetSugarGrams", 50.0), "g", "#ef4444"),
            ("Sodium", log_dict.get("consumedSodiumMg", 0.0), log_dict.get("targetSodiumMg", 2300.0), "mg", "#06b6d4"),
        ]
        res = []
        for name, curr, tgt, unit, color in items:
            pct = min(100.0, round((curr / tgt) * 100.0, 1)) if tgt > 0 else 0.0
            res.append(
                NutrientTargetItemSchema(
                    name=name,
                    current=round(curr, 1) if isinstance(curr, float) else curr,
                    target=round(tgt, 1) if isinstance(tgt, float) else tgt,
                    unit=unit,
                    pct=pct,
                    color=color,
                )
            )
        return res

    def _build_calorie_flow(self, target_cals: int, meals: List[Dict[str, Any]]) -> List[CalorieFlowEntrySchema]:
        """Constructs waterfall flow: Goal -> Meals -> Remaining."""
        flow = [CalorieFlowEntrySchema(label="Goal", amount=target_cals, type="goal")]
        consumed_sum = 0
        for m in meals:
            m_cals = m.get("totalCalories", 0)
            consumed_sum += m_cals
            flow.append(
                CalorieFlowEntrySchema(
                    label=m.get("name", "Meal"),
                    amount=-m_cals,
                    type="consumed",
                )
            )
        rem = max(0, target_cals - consumed_sum)
        flow.append(CalorieFlowEntrySchema(label="Remaining", amount=rem, type="remaining"))
        return flow

    def _generate_insights(self, log_dict: Dict[str, Any]) -> List[NutritionInsightItemSchema]:
        """Generates deterministic rule-based insights without external AI APIs."""
        insights = []
        # Protein insight
        p_curr = log_dict.get("consumedProteinGrams", 0.0)
        p_tgt = log_dict.get("targetProteinGrams", 160.0)
        if p_tgt > 0:
            if p_curr >= p_tgt:
                insights.append(
                    NutritionInsightItemSchema(
                        id="ins_p1",
                        type="positive",
                        title="Great job hitting your protein goal!",
                        description="Your muscle recovery and protein synthesis are fully supported.",
                    )
                )
            elif (p_curr / p_tgt) < 0.7:
                insights.append(
                    NutritionInsightItemSchema(
                        id="ins_p2",
                        type="warning",
                        title="Protein intake is below target.",
                        description=f"You are {round(p_tgt - p_curr, 1)}g away from your daily goal.",
                    )
                )

        # Hydration insight
        w_curr = log_dict.get("waterIntakeLiters", 0.0)
        w_tgt = log_dict.get("waterTargetLiters", 3.0)
        if w_tgt > 0:
            if w_curr >= w_tgt:
                insights.append(
                    NutritionInsightItemSchema(
                        id="ins_w1",
                        type="positive",
                        title="Optimal hydration achieved.",
                        description=f"You reached your {w_tgt}L daily water goal.",
                    )
                )
            elif (w_curr / w_tgt) < 0.5:
                insights.append(
                    NutritionInsightItemSchema(
                        id="ins_w2",
                        type="info",
                        title="Stay hydrated throughout the day.",
                        description=f"You have logged {w_curr}L of your {w_tgt}L goal.",
                    )
                )

        # Calorie balance insight
        c_curr = log_dict.get("consumedCalories", 0)
        c_tgt = log_dict.get("targetCalories", 2400)
        if c_tgt > 0:
            diff = abs(c_curr - c_tgt)
            if diff <= c_tgt * 0.1 and c_curr > 0:
                insights.append(
                    NutritionInsightItemSchema(
                        id="ins_c1",
                        type="positive",
                        title="Caloric intake on track.",
                        description=f"You are within 10% of your {c_tgt} kcal target.",
                    )
                )
            elif c_curr > c_tgt:
                insights.append(
                    NutritionInsightItemSchema(
                        id="ins_c2",
                        type="warning",
                        title="Caloric surplus reached.",
                        description=f"You have exceeded your daily goal by {c_curr - c_tgt} kcal.",
                    )
                )

        if not insights:
            insights.append(
                NutritionInsightItemSchema(
                    id="ins_default",
                    type="info",
                    title="Track your nutrition consistently.",
                    description="Log your meals to maintain accurate daily macronutrient accountability.",
                )
            )

        return insights

    def _recalculate_daily_totals(self, log_dict: Dict[str, Any]) -> Dict[str, Any]:
        """
        Recalculates meal-level and daily-level totals deterministically from logged foods.
        CRITICAL: Never overwrites logged food calories with P*4 + C*4 + F*9.
        Authoritative calories are summed directly.
        """
        meals = log_dict.get("meals", [])
        daily_cals = 0
        daily_p = 0.0
        daily_c = 0.0
        daily_f = 0.0
        daily_fib = 0.0
        daily_sug = 0.0
        daily_sod = 0.0

        for meal in meals:
            foods = meal.get("foods", [])
            m_cals = sum(f.get("calories", 0) for f in foods)
            m_p = sum(f.get("proteinGrams", 0.0) for f in foods)
            m_c = sum(f.get("carbsGrams", 0.0) for f in foods)
            m_f = sum(f.get("fatGrams", 0.0) for f in foods)
            m_fib = sum(f.get("fiberGrams", 0.0) for f in foods)
            m_sug = sum(f.get("sugarGrams", 0.0) for f in foods)
            m_sod = sum(f.get("sodiumMg", 0.0) for f in foods)

            meal["totalCalories"] = m_cals
            meal["totalProteinGrams"] = round(m_p, 1)
            meal["totalCarbsGrams"] = round(m_c, 1)
            meal["totalFatGrams"] = round(m_f, 1)
            meal["totalFiberGrams"] = round(m_fib, 1)
            meal["totalSugarGrams"] = round(m_sug, 1)
            meal["totalSodiumMg"] = round(m_sod, 1)
            meal["foodList"] = [f.get("name", "") for f in foods]

            daily_cals += m_cals
            daily_p += m_p
            daily_c += m_c
            daily_f += m_f
            daily_fib += m_fib
            daily_sug += m_sug
            daily_sod += m_sod

        log_dict["consumedCalories"] = daily_cals
        log_dict["consumedProteinGrams"] = round(daily_p, 1)
        log_dict["consumedCarbsGrams"] = round(daily_c, 1)
        log_dict["consumedFatGrams"] = round(daily_f, 1)
        log_dict["consumedFiberGrams"] = round(daily_fib, 1)
        log_dict["consumedSugarGrams"] = round(daily_sug, 1)
        log_dict["consumedSodiumMg"] = round(daily_sod, 1)
        log_dict["updatedAt"] = datetime.now(timezone.utc).isoformat()

        # Update dynamic components
        log_dict["nutrientTargets"] = [t.model_dump() for t in self._build_nutrient_targets(log_dict)]
        log_dict["calorieFlow"] = [cf.model_dump() for cf in self._build_calorie_flow(log_dict.get("targetCalories", 2400), meals)]
        log_dict["insights"] = [ins.model_dump() for ins in self._generate_insights(log_dict)]

        return log_dict

    # =========================================================================
    # PUBLIC SERVICE METHODS
    # =========================================================================

    def get_or_create_daily_nutrition(self, uid: str, date_str: Optional[str] = None) -> DailyNutritionSchema:
        """
        Retrieves or initializes the daily nutrition log for a specific date (YYYY-MM-DD).
        If no log exists yet, returns clean zero-consumed state with user target macros.
        """
        date = date_str or get_today_iso_date()
        existing = self.nutrition_repo.get_daily_log(uid, date)

        targets = self._get_user_targets(uid)

        if existing:
            data = existing.model_dump()
            # Ensure targets reflect current user profile
            data["targetCalories"] = targets["targetCalories"]
            data["targetProteinGrams"] = targets["targetProteinGrams"]
            data["targetCarbsGrams"] = targets["targetCarbsGrams"]
            data["targetFatGrams"] = targets["targetFatGrams"]
            # Recalculate dynamic views
            data = self._recalculate_daily_totals(data)
            weekly = self.get_weekly_summary(uid, date)
            data["weeklySummary"] = [w.model_dump() for w in weekly]
            return DailyNutritionSchema(**data)

        # Fresh empty state for the day
        fresh_dict: Dict[str, Any] = {
            "date": date,
            "userId": uid,
            "targetCalories": targets["targetCalories"],
            "consumedCalories": 0,
            "targetProteinGrams": targets["targetProteinGrams"],
            "consumedProteinGrams": 0.0,
            "targetCarbsGrams": targets["targetCarbsGrams"],
            "consumedCarbsGrams": 0.0,
            "targetFatGrams": targets["targetFatGrams"],
            "consumedFatGrams": 0.0,
            "targetFiberGrams": targets["targetFiberGrams"],
            "consumedFiberGrams": 0.0,
            "targetSugarGrams": targets["targetSugarGrams"],
            "consumedSugarGrams": 0.0,
            "targetSodiumMg": targets["targetSodiumMg"],
            "consumedSodiumMg": 0.0,
            "waterIntakeLiters": 0.0,
            "waterTargetLiters": targets["waterTargetLiters"],
            "meals": create_default_meals(),
            "updatedAt": datetime.now(timezone.utc).isoformat(),
        }

        fresh_dict = self._recalculate_daily_totals(fresh_dict)
        weekly = self.get_weekly_summary(uid, date)
        fresh_dict["weeklySummary"] = [w.model_dump() for w in weekly]

        return DailyNutritionSchema(**fresh_dict)

    def log_meal_item(self, uid: str, payload: MealLogCreate) -> DailyNutritionSchema:
        """
        Logs a food item into a meal category for the specified date.
        Recalculates meal and daily totals and persists to Firestore.
        """
        date = payload.date or get_today_iso_date()
        daily = self.get_or_create_daily_nutrition(uid, date)
        data = daily.model_dump()

        # Determine food values (catalogue scaling or manual custom entry)
        if payload.foodId:
            cat_food = self.nutrition_repo.get_food_by_id(payload.foodId)
            if cat_food:
                ratio = payload.servingSizeGrams / 100.0
                cals = round(cat_food.caloriesPer100g * ratio)
                prot = round(cat_food.proteinGramsPer100g * ratio, 1)
                carbs = round(cat_food.carbsGramsPer100g * ratio, 1)
                fat = round(cat_food.fatGramsPer100g * ratio, 1)
                fiber = round(cat_food.fiberGramsPer100g * ratio, 1)
                sugar = round(cat_food.sugarGramsPer100g * ratio, 1)
                sodium = round(cat_food.sodiumMgPer100g * ratio, 1)
                name = cat_food.name
            else:
                cals = payload.calories
                prot = payload.proteinGrams
                carbs = payload.carbsGrams
                fat = payload.fatGrams
                fiber = payload.fiberGrams
                sugar = payload.sugarGrams
                sodium = payload.sodiumMg
                name = payload.foodName
        else:
            cals = payload.calories
            prot = payload.proteinGrams
            carbs = payload.carbsGrams
            fat = payload.fatGrams
            fiber = payload.fiberGrams
            sugar = payload.sugarGrams
            sodium = payload.sodiumMg
            name = payload.foodName

        food_id = f"f_{int(datetime.now(timezone.utc).timestamp() * 1000)}"
        new_food = {
            "id": food_id,
            "name": name,
            "calories": cals,
            "proteinGrams": prot,
            "carbsGrams": carbs,
            "fatGrams": fat,
            "fiberGrams": fiber,
            "sugarGrams": sugar,
            "sodiumMg": sodium,
            "servingSizeGrams": payload.servingSizeGrams,
        }

        # Locate or create matching meal slot
        meals = data.setdefault("meals", [])
        target_meal = None
        for m in meals:
            if m.get("type") == payload.mealType:
                target_meal = m
                break

        if not target_meal:
            target_meal = {
                "id": f"m_{payload.mealType}",
                "time": datetime.now(timezone.utc).strftime("%I:%M %p"),
                "type": payload.mealType,
                "name": payload.mealType.capitalize(),
                "totalCalories": 0,
                "totalProteinGrams": 0.0,
                "totalCarbsGrams": 0.0,
                "totalFatGrams": 0.0,
                "totalFiberGrams": 0.0,
                "totalSugarGrams": 0.0,
                "totalSodiumMg": 0.0,
                "foodList": [],
                "foods": [],
            }
            meals.append(target_meal)

        target_meal.setdefault("foods", []).append(new_food)

        # Recalculate totals and persist
        data = self._recalculate_daily_totals(data)
        saved = self.nutrition_repo.save_daily_log(uid, date, data)

        # Attach weekly summary for response
        res_dict = saved.model_dump()
        res_dict["weeklySummary"] = [w.model_dump() for w in self.get_weekly_summary(uid, date)]
        return DailyNutritionSchema(**res_dict)

    def delete_meal_food(self, uid: str, meal_id: str, food_id: str, date_str: Optional[str] = None) -> DailyNutritionSchema:
        """
        Removes a food item from a meal slot and updates daily totals.
        """
        date = date_str or get_today_iso_date()
        daily = self.get_or_create_daily_nutrition(uid, date)
        data = daily.model_dump()

        meals = data.get("meals", [])
        for m in meals:
            if m.get("id") == meal_id or m.get("type") == meal_id:
                foods = m.get("foods", [])
                m["foods"] = [f for f in foods if f.get("id") != food_id]

        data = self._recalculate_daily_totals(data)
        saved = self.nutrition_repo.save_daily_log(uid, date, data)

        res_dict = saved.model_dump()
        res_dict["weeklySummary"] = [w.model_dump() for w in self.get_weekly_summary(uid, date)]
        return DailyNutritionSchema(**res_dict)

    def log_water(self, uid: str, payload: WaterLogCreate) -> DailyNutritionSchema:
        """
        Increments user water intake for a specific date (capped at 10.0L).
        """
        date = payload.date or get_today_iso_date()
        daily = self.get_or_create_daily_nutrition(uid, date)
        data = daily.model_dump()

        current_water = data.get("waterIntakeLiters", 0.0)
        new_water = min(10.0, round(current_water + payload.amountLiters, 2))
        data["waterIntakeLiters"] = new_water

        data = self._recalculate_daily_totals(data)
        saved = self.nutrition_repo.save_daily_log(uid, date, data)

        # Trigger hydration milestone notification if target reached
        water_target = data.get("waterTargetLiters", 3.0)
        if new_water >= water_target and water_target > 0:
            try:
                self.notification_service.create_hydration_notification(uid, date)
            except Exception as e:
                logger.warning(f"Failed to create hydration notification for user {uid}, date {date}: {e}")

        res_dict = saved.model_dump()
        res_dict["weeklySummary"] = [w.model_dump() for w in self.get_weekly_summary(uid, date)]
        return DailyNutritionSchema(**res_dict)

    def get_weekly_summary(self, uid: str, end_date_str: Optional[str] = None) -> List[WeeklyNutritionDaySchema]:
        """
        Computes 7 calendar days leading up to end_date (start_date = end_date - 6 days).
        Days without logs return clean zero-data state rather than fabricated numbers.
        """
        end_date = end_date_str or get_today_iso_date()
        try:
            end_dt = datetime.strptime(end_date, "%Y-%m-%d").date()
        except Exception:
            end_dt = datetime.now(timezone.utc).date()

        start_dt = end_dt - timedelta(days=6)
        logs = self.nutrition_repo.list_logs_for_range(uid, start_dt.isoformat(), end_dt.isoformat())
        log_map = {log.date: log for log in logs}

        result = []
        for i in range(7):
            curr_dt = start_dt + timedelta(days=i)
            curr_iso = curr_dt.isoformat()
            day_name = curr_dt.strftime("%a")  # Mon, Tue, etc.
            log = log_map.get(curr_iso)

            if log and log.targetCalories > 0:
                cals = log.consumedCalories
                pct = min(100.0, round((cals / log.targetCalories) * 100.0, 1))
            else:
                cals = 0
                pct = 0.0

            result.append(
                WeeklyNutritionDaySchema(
                    day=day_name,
                    date=curr_iso,
                    pct=pct,
                    calories=cals,
                    isCurrent=(curr_dt == end_dt),
                )
            )

        return result

    def search_foods(self, query: Optional[str] = None, category: Optional[str] = None) -> List[CatalogFoodSchema]:
        """Searches curated food items in the catalogue."""
        return self.nutrition_repo.search_foods(query=query, category=category)


def get_nutrition_service(
    nutrition_repo: NutritionRepository = Depends(get_nutrition_repository),
    user_repo: UserRepository = Depends(get_user_repository),
) -> NutritionService:
    """FastAPI dependency injection provider for NutritionService."""
    return NutritionService(
        nutrition_repo=nutrition_repo,
        user_repo=user_repo,
    )
