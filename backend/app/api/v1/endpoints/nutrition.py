from typing import List, Optional
from fastapi import APIRouter, Depends, Query, HTTPException, status
from ....core.security import get_current_user, CurrentUser
from ....schemas.nutrition import (
    DailyNutritionSchema,
    MealLogCreate,
    WaterLogCreate,
    WeeklyNutritionDaySchema,
    CatalogFoodSchema,
)
from ....services.nutrition_service import NutritionService, get_nutrition_service

router = APIRouter()


@router.get("/daily", response_model=DailyNutritionSchema, summary="Get daily nutrition summary and logged meals")
async def get_daily_nutrition(
    date: Optional[str] = Query(None, description="Target date in YYYY-MM-DD format (defaults to UTC today)"),
    current_user: CurrentUser = Depends(get_current_user),
    service: NutritionService = Depends(get_nutrition_service),
):
    """
    Retrieves complete daily nutrition status for the verified user.
    If no log exists for the date, initializes clean empty state with user profile targets.
    """
    return service.get_or_create_daily_nutrition(current_user.uid, date_str=date)


@router.post("/meals", response_model=DailyNutritionSchema, summary="Log a food item into a meal category")
async def log_meal_item(
    payload: MealLogCreate,
    current_user: CurrentUser = Depends(get_current_user),
    service: NutritionService = Depends(get_nutrition_service),
):
    """
    Logs a food item into a meal category (breakfast, lunch, snack, dinner) for the specified date.
    Recalculates meal totals, daily consumed macros/calories, and persists to Firestore.
    """
    return service.log_meal_item(current_user.uid, payload)


@router.delete(
    "/meals/{meal_id}/foods/{food_id}",
    response_model=DailyNutritionSchema,
    summary="Delete a logged food item from a meal",
)
async def delete_meal_food(
    meal_id: str,
    food_id: str,
    date: Optional[str] = Query(None, description="Date in YYYY-MM-DD format"),
    current_user: CurrentUser = Depends(get_current_user),
    service: NutritionService = Depends(get_nutrition_service),
):
    """
    Removes a food item from a meal slot and updates daily totals.
    """
    return service.delete_meal_food(current_user.uid, meal_id=meal_id, food_id=food_id, date_str=date)


@router.post("/water", response_model=DailyNutritionSchema, summary="Log water intake")
async def log_water(
    payload: WaterLogCreate,
    current_user: CurrentUser = Depends(get_current_user),
    service: NutritionService = Depends(get_nutrition_service),
):
    """
    Increments daily water intake in Liters (capped safely at 10.0L).
    """
    return service.log_water(current_user.uid, payload)


@router.get("/weekly", response_model=List[WeeklyNutritionDaySchema], summary="Get trailing 7-day nutrition summary")
async def get_weekly_nutrition(
    date: Optional[str] = Query(None, description="End date in YYYY-MM-DD format"),
    current_user: CurrentUser = Depends(get_current_user),
    service: NutritionService = Depends(get_nutrition_service),
):
    """
    Computes trailing 7 calendar days leading up to the specified date.
    """
    return service.get_weekly_summary(current_user.uid, end_date_str=date)


@router.get("/foods", response_model=List[CatalogFoodSchema], summary="Search curated food catalogue")
async def search_foods(
    query: Optional[str] = Query(None, description="Food name or keyword search"),
    category: Optional[str] = Query(None, description="Category filter (protein, carbs, fats, vegetables, fruits, dairy, snacks, supplements)"),
    current_user: CurrentUser = Depends(get_current_user),
    service: NutritionService = Depends(get_nutrition_service),
):
    """
    Returns matching food items from the curated fitness food catalogue.
    """
    return service.search_foods(query=query, category=category)
