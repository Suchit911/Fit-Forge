from typing import List, Optional, Literal
from pydantic import BaseModel, Field, field_validator
from datetime import datetime


def validate_iso_date(v: Optional[str]) -> Optional[str]:
    if v is None:
        return None
    try:
        datetime.strptime(v, "%Y-%m-%d")
        return v
    except ValueError:
        raise ValueError("Date must be in YYYY-MM-DD format")


class FoodItemSchema(BaseModel):
    id: str
    name: str
    calories: int = Field(ge=0, description="Authoritative calories supplied by catalogue or user")
    proteinGrams: float = Field(ge=0.0)
    carbsGrams: float = Field(ge=0.0)
    fatGrams: float = Field(ge=0.0)
    fiberGrams: float = Field(default=0.0, ge=0.0)
    sugarGrams: float = Field(default=0.0, ge=0.0)
    sodiumMg: float = Field(default=0.0, ge=0.0)
    servingSizeGrams: float = Field(default=100.0, gt=0.0)

    model_config = {"extra": "ignore"}


class MealSchema(BaseModel):
    id: str
    time: str
    type: Literal["breakfast", "lunch", "dinner", "snack"]
    name: str
    totalCalories: int = Field(ge=0)
    totalProteinGrams: float = Field(ge=0.0)
    totalCarbsGrams: float = Field(ge=0.0)
    totalFatGrams: float = Field(ge=0.0)
    totalFiberGrams: float = Field(default=0.0, ge=0.0)
    totalSugarGrams: float = Field(default=0.0, ge=0.0)
    totalSodiumMg: float = Field(default=0.0, ge=0.0)
    image: Optional[str] = None
    foodList: List[str] = []
    foods: List[FoodItemSchema] = []

    model_config = {"extra": "ignore"}


class NutrientTargetItemSchema(BaseModel):
    name: str
    current: float = Field(ge=0.0)
    target: float = Field(ge=0.0)
    unit: str
    pct: float = Field(ge=0.0)
    color: str

    model_config = {"extra": "ignore"}


class CalorieFlowEntrySchema(BaseModel):
    label: str
    amount: int
    type: Literal["goal", "consumed", "remaining"]

    model_config = {"extra": "ignore"}


class WeeklyNutritionDaySchema(BaseModel):
    day: str
    date: Optional[str] = None
    pct: float = Field(ge=0.0)
    calories: int = Field(ge=0)
    isCurrent: Optional[bool] = False

    model_config = {"extra": "ignore"}


class NutritionInsightItemSchema(BaseModel):
    id: str
    type: Literal["positive", "warning", "info"]
    title: str
    description: Optional[str] = None

    model_config = {"extra": "ignore"}


class DailyNutritionSchema(BaseModel):
    date: str
    targetCalories: int = Field(ge=0)
    consumedCalories: int = Field(ge=0)
    targetProteinGrams: float = Field(ge=0.0)
    consumedProteinGrams: float = Field(ge=0.0)
    targetCarbsGrams: float = Field(ge=0.0)
    consumedCarbsGrams: float = Field(ge=0.0)
    targetFatGrams: float = Field(ge=0.0)
    consumedFatGrams: float = Field(ge=0.0)
    targetFiberGrams: float = Field(default=30.0, ge=0.0)
    consumedFiberGrams: float = Field(default=0.0, ge=0.0)
    targetSugarGrams: float = Field(default=50.0, ge=0.0)
    consumedSugarGrams: float = Field(default=0.0, ge=0.0)
    targetSodiumMg: float = Field(default=2300.0, ge=0.0)
    consumedSodiumMg: float = Field(default=0.0, ge=0.0)
    waterIntakeLiters: float = Field(default=0.0, ge=0.0)
    waterTargetLiters: float = Field(default=3.0, ge=0.0)
    meals: List[MealSchema] = []
    nutrientTargets: List[NutrientTargetItemSchema] = []
    calorieFlow: List[CalorieFlowEntrySchema] = []
    weeklySummary: List[WeeklyNutritionDaySchema] = []
    insights: List[NutritionInsightItemSchema] = []

    model_config = {"extra": "ignore"}


class MealLogCreate(BaseModel):
    mealType: Literal["breakfast", "lunch", "dinner", "snack"]
    foodName: str = Field(min_length=1)
    calories: int = Field(ge=0)
    proteinGrams: float = Field(ge=0.0)
    carbsGrams: float = Field(ge=0.0)
    fatGrams: float = Field(ge=0.0)
    fiberGrams: float = Field(default=0.0, ge=0.0)
    sugarGrams: float = Field(default=0.0, ge=0.0)
    sodiumMg: float = Field(default=0.0, ge=0.0)
    servingSizeGrams: float = Field(default=100.0, gt=0.0)
    foodId: Optional[str] = None
    date: Optional[str] = None

    @field_validator("date")
    @classmethod
    def check_date(cls, v: Optional[str]) -> Optional[str]:
        return validate_iso_date(v)

    model_config = {"extra": "ignore"}


class WaterLogCreate(BaseModel):
    amountLiters: float = Field(gt=0.0, le=5.0)
    date: Optional[str] = None

    @field_validator("date")
    @classmethod
    def check_date(cls, v: Optional[str]) -> Optional[str]:
        return validate_iso_date(v)

    model_config = {"extra": "ignore"}


class CatalogFoodSchema(BaseModel):
    id: str
    name: str
    category: Literal["protein", "carbs", "fats", "vegetables", "fruits", "supplements", "dairy", "snacks"]
    caloriesPer100g: int = Field(ge=0)
    proteinGramsPer100g: float = Field(ge=0.0)
    carbsGramsPer100g: float = Field(ge=0.0)
    fatGramsPer100g: float = Field(ge=0.0)
    fiberGramsPer100g: float = Field(default=0.0, ge=0.0)
    sugarGramsPer100g: float = Field(default=0.0, ge=0.0)
    sodiumMgPer100g: float = Field(default=0.0, ge=0.0)
    defaultServingGrams: float = Field(default=100.0, gt=0.0)
    imageUrl: Optional[str] = None

    model_config = {"extra": "ignore"}
