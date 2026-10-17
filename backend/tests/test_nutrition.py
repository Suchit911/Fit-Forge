from datetime import datetime, timezone, timedelta
from unittest.mock import patch
from fastapi.testclient import TestClient
from backend.app.main import app
from backend.app.core.security import CurrentUser, get_current_user
from backend.app.repositories.nutrition_repository import NutritionRepository, get_nutrition_repository
from backend.app.repositories.user_repository import UserRepository, get_user_repository
from backend.app.schemas.user import UserProfileSchema
import pytest


@pytest.fixture
def mock_nutrition_repo():
    """Provides an isolated in-memory NutritionRepository."""
    return NutritionRepository(db=None)


@pytest.fixture
def mock_user_repo():
    """Provides an isolated in-memory UserRepository."""
    return UserRepository(db=None)


# =============================================================================
# 1. EMPTY DAILY NUTRITION STATE
# =============================================================================

def test_get_daily_nutrition_empty_state(
    client: TestClient,
    mock_nutrition_repo: NutritionRepository,
    mock_user_repo: UserRepository,
):
    """1. Test fresh user receives clean zero consumed values with user targets and 4 meal slots."""
    user = CurrentUser(uid="fresh_nutri_user", email="nutri@pulseai.fit", name="Fresh User", email_verified=True)
    app.dependency_overrides[get_current_user] = lambda: user
    app.dependency_overrides[get_nutrition_repository] = lambda: mock_nutrition_repo
    app.dependency_overrides[get_user_repository] = lambda: mock_user_repo

    try:
        res = client.get("/api/v1/nutrition/daily?date=2026-09-05")
        assert res.status_code == 200
        data = res.json()
        assert data["date"] == "2026-09-05"
        assert data["consumedCalories"] == 0
        assert data["consumedProteinGrams"] == 0.0
        assert data["consumedCarbsGrams"] == 0.0
        assert data["consumedFatGrams"] == 0.0
        assert data["waterIntakeLiters"] == 0.0
        assert len(data["meals"]) >= 4
        # Meal categories initialized
        meal_types = [m["type"] for m in data["meals"]]
        assert "breakfast" in meal_types
        assert "lunch" in meal_types
        assert "dinner" in meal_types
        assert "snack" in meal_types
        # Nutrients targets array present
        assert len(data["nutrientTargets"]) >= 4
    finally:
        app.dependency_overrides.clear()


# =============================================================================
# 2. USER TARGET INTEGRATION
# =============================================================================

def test_user_target_integration(
    client: TestClient,
    mock_nutrition_repo: NutritionRepository,
    mock_user_repo: UserRepository,
):
    """2. Test that daily nutrition targets are pulled from the user profile."""
    user = CurrentUser(uid="custom_target_user", email="target@pulseai.fit", name="Target Pro", email_verified=True)
    # Seed user profile with custom nutrition targets
    custom_profile = {
        "id": user.uid,
        "name": user.name,
        "email": user.email,
        "targetCalories": 2800,
        "targetProteinGrams": 190,
        "targetCarbsGrams": 320,
        "targetFatGrams": 75,
    }
    mock_user_repo._in_memory_store[user.uid] = custom_profile

    app.dependency_overrides[get_current_user] = lambda: user
    app.dependency_overrides[get_nutrition_repository] = lambda: mock_nutrition_repo
    app.dependency_overrides[get_user_repository] = lambda: mock_user_repo

    try:
        res = client.get("/api/v1/nutrition/daily?date=2026-09-05")
        assert res.status_code == 200
        data = res.json()
        assert data["targetCalories"] == 2800
        assert data["targetProteinGrams"] == 190.0
        assert data["targetCarbsGrams"] == 320.0
        assert data["targetFatGrams"] == 75.0
    finally:
        app.dependency_overrides.clear()


# =============================================================================
# 3. LOG ONE MEAL ITEM
# =============================================================================

def test_log_one_meal_item(
    client: TestClient,
    mock_nutrition_repo: NutritionRepository,
    mock_user_repo: UserRepository,
):
    """3. Test logging a single custom food item adds it to the meal and updates totals."""
    user = CurrentUser(uid="logger_user_1", email="log1@pulseai.fit", name="Log User 1", email_verified=True)
    app.dependency_overrides[get_current_user] = lambda: user
    app.dependency_overrides[get_nutrition_repository] = lambda: mock_nutrition_repo
    app.dependency_overrides[get_user_repository] = lambda: mock_user_repo

    try:
        payload = {
            "mealType": "breakfast",
            "foodName": "Oatmeal with Blueberries",
            "calories": 320,
            "proteinGrams": 12.0,
            "carbsGrams": 55.0,
            "fatGrams": 6.0,
            "fiberGrams": 8.0,
            "sugarGrams": 14.0,
            "sodiumMg": 15.0,
            "servingSizeGrams": 180.0,
            "date": "2026-09-05",
        }
        res = client.post("/api/v1/nutrition/meals", json=payload)
        assert res.status_code == 200
        data = res.json()
        assert data["consumedCalories"] == 320
        assert data["consumedProteinGrams"] == 12.0
        assert data["consumedCarbsGrams"] == 55.0
        assert data["consumedFatGrams"] == 6.0
        assert data["consumedFiberGrams"] == 8.0

        # Breakfast meal contains the food
        bf = next(m for m in data["meals"] if m["type"] == "breakfast")
        assert bf["totalCalories"] == 320
        assert len(bf["foods"]) == 1
        assert bf["foods"][0]["name"] == "Oatmeal with Blueberries"
    finally:
        app.dependency_overrides.clear()


# =============================================================================
# 4. MULTIPLE FOODS IN SAME MEAL
# =============================================================================

def test_multiple_foods_same_meal(
    client: TestClient,
    mock_nutrition_repo: NutritionRepository,
    mock_user_repo: UserRepository,
):
    """4. Test that logging multiple foods in the same meal sums totals properly."""
    user = CurrentUser(uid="multi_food_user", email="multi@pulseai.fit", name="Multi User", email_verified=True)
    app.dependency_overrides[get_current_user] = lambda: user
    app.dependency_overrides[get_nutrition_repository] = lambda: mock_nutrition_repo
    app.dependency_overrides[get_user_repository] = lambda: mock_user_repo

    try:
        # Food 1: Eggs
        client.post(
            "/api/v1/nutrition/meals",
            json={
                "mealType": "breakfast",
                "foodName": "3 Scrambled Eggs",
                "calories": 210,
                "proteinGrams": 18.0,
                "carbsGrams": 2.0,
                "fatGrams": 14.0,
                "date": "2026-09-05",
            },
        )
        # Food 2: Whole Wheat Toast
        res = client.post(
            "/api/v1/nutrition/meals",
            json={
                "mealType": "breakfast",
                "foodName": "Whole Wheat Toast",
                "calories": 140,
                "proteinGrams": 6.0,
                "carbsGrams": 24.0,
                "fatGrams": 2.0,
                "date": "2026-09-05",
            },
        )
        assert res.status_code == 200
        data = res.json()
        assert data["consumedCalories"] == 350
        assert data["consumedProteinGrams"] == 24.0
        assert data["consumedCarbsGrams"] == 26.0
        assert data["consumedFatGrams"] == 16.0

        bf = next(m for m in data["meals"] if m["type"] == "breakfast")
        assert len(bf["foods"]) == 2
        assert bf["totalCalories"] == 350
    finally:
        app.dependency_overrides.clear()


# =============================================================================
# 5. FOODS ACROSS DIFFERENT MEALS
# =============================================================================

def test_foods_across_different_meals(
    client: TestClient,
    mock_nutrition_repo: NutritionRepository,
    mock_user_repo: UserRepository,
):
    """5. Test that breakfast, lunch, and dinner are properly partitioned and accumulate in daily totals."""
    user = CurrentUser(uid="three_meals_user", email="three@pulseai.fit", name="Three Meals", email_verified=True)
    app.dependency_overrides[get_current_user] = lambda: user
    app.dependency_overrides[get_nutrition_repository] = lambda: mock_nutrition_repo
    app.dependency_overrides[get_user_repository] = lambda: mock_user_repo

    try:
        # Breakfast: 400 kcal
        client.post(
            "/api/v1/nutrition/meals",
            json={"mealType": "breakfast", "foodName": "Breakfast Meal", "calories": 400, "proteinGrams": 30.0, "carbsGrams": 50.0, "fatGrams": 8.0, "date": "2026-09-05"},
        )
        # Lunch: 650 kcal
        client.post(
            "/api/v1/nutrition/meals",
            json={"mealType": "lunch", "foodName": "Lunch Bowl", "calories": 650, "proteinGrams": 45.0, "carbsGrams": 70.0, "fatGrams": 18.0, "date": "2026-09-05"},
        )
        # Dinner: 550 kcal
        res = client.post(
            "/api/v1/nutrition/meals",
            json={"mealType": "dinner", "foodName": "Dinner Salmon", "calories": 550, "proteinGrams": 40.0, "carbsGrams": 35.0, "fatGrams": 22.0, "date": "2026-09-05"},
        )
        assert res.status_code == 200
        data = res.json()
        assert data["consumedCalories"] == 1600  # 400 + 650 + 550
        assert data["consumedProteinGrams"] == 115.0  # 30 + 45 + 40
        assert data["consumedCarbsGrams"] == 155.0  # 50 + 70 + 35
        assert data["consumedFatGrams"] == 48.0  # 8 + 18 + 22
    finally:
        app.dependency_overrides.clear()


# =============================================================================
# 6. FOOD DELETION
# =============================================================================

def test_food_deletion(
    client: TestClient,
    mock_nutrition_repo: NutritionRepository,
    mock_user_repo: UserRepository,
):
    """6. Test deleting a food item decrements meal and daily totals."""
    user = CurrentUser(uid="delete_nutri_user", email="del@pulseai.fit", name="Delete User", email_verified=True)
    app.dependency_overrides[get_current_user] = lambda: user
    app.dependency_overrides[get_nutrition_repository] = lambda: mock_nutrition_repo
    app.dependency_overrides[get_user_repository] = lambda: mock_user_repo

    try:
        # Add 2 items to lunch
        client.post(
            "/api/v1/nutrition/meals",
            json={"mealType": "lunch", "foodName": "Chicken", "calories": 300, "proteinGrams": 35.0, "carbsGrams": 0.0, "fatGrams": 6.0, "date": "2026-09-05"},
        )
        post2 = client.post(
            "/api/v1/nutrition/meals",
            json={"mealType": "lunch", "foodName": "Rice", "calories": 200, "proteinGrams": 4.0, "carbsGrams": 45.0, "fatGrams": 1.0, "date": "2026-09-05"},
        ).json()

        lunch_meal = next(m for m in post2["meals"] if m["type"] == "lunch")
        assert len(lunch_meal["foods"]) == 2
        assert post2["consumedCalories"] == 500
        rice_food_id = next(f["id"] for f in lunch_meal["foods"] if f["name"] == "Rice")

        # Delete Rice
        del_res = client.delete(f"/api/v1/nutrition/meals/{lunch_meal['id']}/foods/{rice_food_id}?date=2026-09-05")
        assert del_res.status_code == 200
        del_data = del_res.json()
        assert del_data["consumedCalories"] == 300
        assert del_data["consumedCarbsGrams"] == 0.0
        updated_lunch = next(m for m in del_data["meals"] if m["type"] == "lunch")
        assert len(updated_lunch["foods"]) == 1
    finally:
        app.dependency_overrides.clear()


# =============================================================================
# 7. WATER INTAKE LOGGING
# =============================================================================

def test_water_logging(
    client: TestClient,
    mock_nutrition_repo: NutritionRepository,
    mock_user_repo: UserRepository,
):
    """7. Test water logging increments daily waterIntakeLiters up to safe cap."""
    user = CurrentUser(uid="water_user", email="water@pulseai.fit", name="Water Hero", email_verified=True)
    app.dependency_overrides[get_current_user] = lambda: user
    app.dependency_overrides[get_nutrition_repository] = lambda: mock_nutrition_repo
    app.dependency_overrides[get_user_repository] = lambda: mock_user_repo

    try:
        # Add 0.5L
        res1 = client.post("/api/v1/nutrition/water", json={"amountLiters": 0.5, "date": "2026-09-05"})
        assert res1.status_code == 200
        assert res1.json()["waterIntakeLiters"] == 0.5

        # Add another 0.8L
        res2 = client.post("/api/v1/nutrition/water", json={"amountLiters": 0.8, "date": "2026-09-05"})
        assert res2.status_code == 200
        assert res2.json()["waterIntakeLiters"] == 1.3
    finally:
        app.dependency_overrides.clear()


# =============================================================================
# 8. DATE ISOLATION
# =============================================================================

def test_date_isolation(
    client: TestClient,
    mock_nutrition_repo: NutritionRepository,
    mock_user_repo: UserRepository,
):
    """8. Test that meals logged on date A do not appear on date B."""
    user = CurrentUser(uid="date_iso_user", email="iso@pulseai.fit", name="Date Iso", email_verified=True)
    app.dependency_overrides[get_current_user] = lambda: user
    app.dependency_overrides[get_nutrition_repository] = lambda: mock_nutrition_repo
    app.dependency_overrides[get_user_repository] = lambda: mock_user_repo

    try:
        # Log 500 kcal on 2026-09-01
        client.post(
            "/api/v1/nutrition/meals",
            json={"mealType": "dinner", "foodName": "Day 1 Feast", "calories": 500, "proteinGrams": 40.0, "carbsGrams": 40.0, "fatGrams": 15.0, "date": "2026-09-01"},
        )

        # Check 2026-09-02 -> must have 0 consumed calories
        day2 = client.get("/api/v1/nutrition/daily?date=2026-09-02").json()
        assert day2["consumedCalories"] == 0
        assert day2["date"] == "2026-09-02"

        # Check 2026-09-01 -> has 500 kcal
        day1 = client.get("/api/v1/nutrition/daily?date=2026-09-01").json()
        assert day1["consumedCalories"] == 500
    finally:
        app.dependency_overrides.clear()


# =============================================================================
# 9. WEEKLY NUTRITION AGGREGATION
# =============================================================================

def test_weekly_nutrition_aggregation(
    client: TestClient,
    mock_nutrition_repo: NutritionRepository,
    mock_user_repo: UserRepository,
):
    """9. Test 7-day weekly summary accurately aggregates calendar days."""
    user = CurrentUser(uid="weekly_nutri_user", email="week@pulseai.fit", name="Week Hero", email_verified=True)
    app.dependency_overrides[get_current_user] = lambda: user
    app.dependency_overrides[get_nutrition_repository] = lambda: mock_nutrition_repo
    app.dependency_overrides[get_user_repository] = lambda: mock_user_repo

    try:
        # Log nutrition on 2026-09-03 and 2026-09-05
        client.post(
            "/api/v1/nutrition/meals",
            json={"mealType": "lunch", "foodName": "Meal A", "calories": 1200, "proteinGrams": 80.0, "carbsGrams": 100.0, "fatGrams": 30.0, "date": "2026-09-03"},
        )
        client.post(
            "/api/v1/nutrition/meals",
            json={"mealType": "lunch", "foodName": "Meal B", "calories": 1800, "proteinGrams": 120.0, "carbsGrams": 150.0, "fatGrams": 45.0, "date": "2026-09-05"},
        )

        res = client.get("/api/v1/nutrition/weekly?date=2026-09-05")
        assert res.status_code == 200
        days = res.json()
        assert len(days) == 7

        # Day for 2026-09-05 is current and has 1800 kcal
        today_item = next(d for d in days if d["date"] == "2026-09-05")
        assert today_item["calories"] == 1800
        assert today_item["isCurrent"] is True

        # Day for 2026-09-03 has 1200 kcal
        sep3_item = next(d for d in days if d["date"] == "2026-09-03")
        assert sep3_item["calories"] == 1200
    finally:
        app.dependency_overrides.clear()


# =============================================================================
# 10. FOOD CATALOGUE SEARCH
# =============================================================================

def test_food_catalogue_search(
    client: TestClient,
    mock_nutrition_repo: NutritionRepository,
    mock_user_repo: UserRepository,
):
    """10. Test case-insensitive search and category filtering in curated foods catalogue."""
    user = CurrentUser(uid="search_user", email="search@pulseai.fit", name="Searcher", email_verified=True)
    app.dependency_overrides[get_current_user] = lambda: user
    app.dependency_overrides[get_nutrition_repository] = lambda: mock_nutrition_repo
    app.dependency_overrides[get_user_repository] = lambda: mock_user_repo

    try:
        # 1. Search by name query "chicken"
        res_q = client.get("/api/v1/nutrition/foods?query=chicken")
        assert res_q.status_code == 200
        items_q = res_q.json()
        assert len(items_q) >= 1
        assert any("chicken" in f["name"].lower() for f in items_q)

        # 2. Filter by category "protein"
        res_cat = client.get("/api/v1/nutrition/foods?category=protein")
        assert res_cat.status_code == 200
        items_cat = res_cat.json()
        assert len(items_cat) >= 5
        assert all(f["category"] == "protein" for f in items_cat)
    finally:
        app.dependency_overrides.clear()


# =============================================================================
# 11. MISSING AUTHORIZATION REJECTION (401)
# =============================================================================

def test_missing_authorization_rejection(client: TestClient):
    """11. Test that unauthenticated requests to nutrition endpoints return 401."""
    assert client.get("/api/v1/nutrition/daily").status_code == 401
    assert client.post("/api/v1/nutrition/meals", json={"mealType": "lunch", "foodName": "A", "calories": 100, "proteinGrams": 10.0, "carbsGrams": 10.0, "fatGrams": 2.0}).status_code == 401
    assert client.post("/api/v1/nutrition/water", json={"amountLiters": 0.5}).status_code == 401
    assert client.get("/api/v1/nutrition/weekly").status_code == 401
    assert client.get("/api/v1/nutrition/foods").status_code == 401


# =============================================================================
# 12. INVALID FIREBASE TOKEN REJECTION (401)
# =============================================================================

def test_invalid_firebase_token_rejection(client: TestClient):
    """12. Test that requests with forged or expired Firebase tokens return 401."""
    with patch("backend.app.core.security.auth.verify_id_token", side_effect=Exception("Invalid auth token")):
        headers = {"Authorization": "Bearer forged_fake_token_xyz"}
        assert client.get("/api/v1/nutrition/daily", headers=headers).status_code == 401
        assert client.post("/api/v1/nutrition/water", json={"amountLiters": 0.5}, headers=headers).status_code == 401


# =============================================================================
# 13. CROSS-USER ISOLATION
# =============================================================================

def test_cross_user_isolation(
    client: TestClient,
    mock_nutrition_repo: NutritionRepository,
    mock_user_repo: UserRepository,
):
    """13. Test User B cannot see or tamper with User A's nutrition logs."""
    user_a = CurrentUser(uid="user_a_nutrition", email="usera@pulseai.fit", name="Alice", email_verified=True)
    user_b = CurrentUser(uid="user_b_nutrition", email="userb@pulseai.fit", name="Bob", email_verified=True)

    # 1. User A logs breakfast
    app.dependency_overrides[get_current_user] = lambda: user_a
    app.dependency_overrides[get_nutrition_repository] = lambda: mock_nutrition_repo
    app.dependency_overrides[get_user_repository] = lambda: mock_user_repo
    client.post(
        "/api/v1/nutrition/meals",
        json={"mealType": "breakfast", "foodName": "Alice Oats", "calories": 400, "proteinGrams": 20.0, "carbsGrams": 60.0, "fatGrams": 5.0, "date": "2026-09-05"},
    )
    app.dependency_overrides.clear()

    # 2. User B logs in
    app.dependency_overrides[get_current_user] = lambda: user_b
    app.dependency_overrides[get_nutrition_repository] = lambda: mock_nutrition_repo
    app.dependency_overrides[get_user_repository] = lambda: mock_user_repo

    try:
        user_b_daily = client.get("/api/v1/nutrition/daily?date=2026-09-05").json()
        assert user_b_daily["consumedCalories"] == 0
        bf = next(m for m in user_b_daily["meals"] if m["type"] == "breakfast")
        assert len(bf["foods"]) == 0
    finally:
        app.dependency_overrides.clear()


# =============================================================================
# 14. CALORIE FLOW CALCULATION
# =============================================================================

def test_calorie_flow_calculation(
    client: TestClient,
    mock_nutrition_repo: NutritionRepository,
    mock_user_repo: UserRepository,
):
    """14. Test that the waterfall flow (Goal, meals, Remaining) computes accurately."""
    user = CurrentUser(uid="flow_user", email="flow@pulseai.fit", name="Flow User", email_verified=True)
    app.dependency_overrides[get_current_user] = lambda: user
    app.dependency_overrides[get_nutrition_repository] = lambda: mock_nutrition_repo
    app.dependency_overrides[get_user_repository] = lambda: mock_user_repo

    try:
        # Log lunch 600 kcal
        res = client.post(
            "/api/v1/nutrition/meals",
            json={"mealType": "lunch", "foodName": "Lunch Feast", "calories": 600, "proteinGrams": 40.0, "carbsGrams": 60.0, "fatGrams": 15.0, "date": "2026-09-05"},
        )
        data = res.json()
        flow = data["calorieFlow"]
        assert flow[0]["label"] == "Goal"
        assert flow[0]["amount"] == 2400
        # Lunch has -600
        lunch_flow = next(cf for cf in flow if cf["label"] == "Lunch")
        assert lunch_flow["amount"] == -600
        # Remaining has 1800 (2400 - 600)
        rem_flow = next(cf for cf in flow if cf["label"] == "Remaining")
        assert rem_flow["amount"] == 1800
    finally:
        app.dependency_overrides.clear()


# =============================================================================
# 15. CRITICAL RULE: AUTHORITATIVE CALORIES NOT OVERWRITTEN BY 4/4/9
# =============================================================================

def test_authoritative_calories_not_replaced(
    client: TestClient,
    mock_nutrition_repo: NutritionRepository,
    mock_user_repo: UserRepository,
):
    """
    15. CRITICAL CALORIE RULE:
    If a food has calories=250, protein=10g, carbs=30g, fat=8g (which would be
    10*4 + 30*4 + 8*9 = 232 kcal), the authoritative 250 kcal MUST be preserved!
    """
    user = CurrentUser(uid="auth_cal_user", email="calrule@pulseai.fit", name="Cal Rule User", email_verified=True)
    app.dependency_overrides[get_current_user] = lambda: user
    app.dependency_overrides[get_nutrition_repository] = lambda: mock_nutrition_repo
    app.dependency_overrides[get_user_repository] = lambda: mock_user_repo

    try:
        res = client.post(
            "/api/v1/nutrition/meals",
            json={
                "mealType": "snack",
                "foodName": "Commercial Protein Bar",
                "calories": 250,  # Authoritative label calories
                "proteinGrams": 10.0,
                "carbsGrams": 30.0,
                "fatGrams": 8.0,
                "date": "2026-09-05",
            },
        )
        assert res.status_code == 200
        data = res.json()
        # MUST BE 250, NOT 232!
        assert data["consumedCalories"] == 250
        snack_meal = next(m for m in data["meals"] if m["type"] == "snack")
        assert snack_meal["totalCalories"] == 250
        assert snack_meal["foods"][0]["calories"] == 250
    finally:
        app.dependency_overrides.clear()


# =============================================================================
# 16. FIBER, SUGAR, AND SODIUM AGGREGATION
# =============================================================================

def test_fiber_sugar_sodium_aggregation(
    client: TestClient,
    mock_nutrition_repo: NutritionRepository,
    mock_user_repo: UserRepository,
):
    """16. Test that fiber, sugar, and sodium sum accurately across logged foods."""
    user = CurrentUser(uid="micro_user", email="micro@pulseai.fit", name="Micro User", email_verified=True)
    app.dependency_overrides[get_current_user] = lambda: user
    app.dependency_overrides[get_nutrition_repository] = lambda: mock_nutrition_repo
    app.dependency_overrides[get_user_repository] = lambda: mock_user_repo

    try:
        client.post(
            "/api/v1/nutrition/meals",
            json={
                "mealType": "breakfast",
                "foodName": "Item A",
                "calories": 200,
                "proteinGrams": 10.0,
                "carbsGrams": 20.0,
                "fatGrams": 5.0,
                "fiberGrams": 6.5,
                "sugarGrams": 12.0,
                "sodiumMg": 250.0,
                "date": "2026-09-05",
            },
        )
        res = client.post(
            "/api/v1/nutrition/meals",
            json={
                "mealType": "lunch",
                "foodName": "Item B",
                "calories": 300,
                "proteinGrams": 25.0,
                "carbsGrams": 30.0,
                "fatGrams": 7.0,
                "fiberGrams": 4.5,
                "sugarGrams": 5.0,
                "sodiumMg": 450.0,
                "date": "2026-09-05",
            },
        )
        assert res.status_code == 200
        data = res.json()
        assert data["consumedFiberGrams"] == 11.0  # 6.5 + 4.5
        assert data["consumedSugarGrams"] == 17.0  # 12.0 + 5.0
        assert data["consumedSodiumMg"] == 700.0  # 250 + 450
    finally:
        app.dependency_overrides.clear()


# =============================================================================
# 17. SERVING SIZE SCALING FOR CATALOGUE FOODS
# =============================================================================

def test_serving_size_scaling_for_catalogue_food(
    client: TestClient,
    mock_nutrition_repo: NutritionRepository,
    mock_user_repo: UserRepository,
):
    """
    17. Test that selecting a catalogue food with a custom serving size
    scales calories and nutrients accurately by (servingSizeGrams / 100).
    """
    user = CurrentUser(uid="scale_user", email="scale@pulseai.fit", name="Scale User", email_verified=True)
    app.dependency_overrides[get_current_user] = lambda: user
    app.dependency_overrides[get_nutrition_repository] = lambda: mock_nutrition_repo
    app.dependency_overrides[get_user_repository] = lambda: mock_user_repo

    try:
        # Chicken Breast catalogue values: 165 kcal, 31g protein, 0g carbs, 3.6g fat per 100g.
        # Logging 200g serving:
        res = client.post(
            "/api/v1/nutrition/meals",
            json={
                "mealType": "dinner",
                "foodName": "Grilled Chicken Breast",
                "foodId": "food_chicken_breast",
                "servingSizeGrams": 200.0,
                "calories": 0,  # Will be computed from catalogue
                "proteinGrams": 0.0,
                "carbsGrams": 0.0,
                "fatGrams": 0.0,
                "date": "2026-09-05",
            },
        )
        assert res.status_code == 200
        data = res.json()
        dinner = next(m for m in data["meals"] if m["type"] == "dinner")
        logged_food = dinner["foods"][0]
        # 165 * 2 = 330 kcal
        assert logged_food["calories"] == 330
        # 31 * 2 = 62g protein
        assert logged_food["proteinGrams"] == 62.0
        # 3.6 * 2 = 7.2g fat
        assert logged_food["fatGrams"] == 7.2
    finally:
        app.dependency_overrides.clear()


# =============================================================================
# 18. VALIDATION: NEGATIVE AND MALFORMED VALUES REJECTED
# =============================================================================

def test_invalid_nutrition_values_rejected(
    client: TestClient,
    mock_nutrition_repo: NutritionRepository,
    mock_user_repo: UserRepository,
):
    """18. Test that Pydantic validation rejects negative calories, negative macros, and invalid dates."""
    user = CurrentUser(uid="val_user", email="val@pulseai.fit", name="Val User", email_verified=True)
    app.dependency_overrides[get_current_user] = lambda: user
    app.dependency_overrides[get_nutrition_repository] = lambda: mock_nutrition_repo
    app.dependency_overrides[get_user_repository] = lambda: mock_user_repo

    try:
        # Negative calories
        res_neg_cal = client.post(
            "/api/v1/nutrition/meals",
            json={"mealType": "lunch", "foodName": "Invalid", "calories": -50, "proteinGrams": 10.0, "carbsGrams": 10.0, "fatGrams": 2.0},
        )
        assert res_neg_cal.status_code == 422

        # Negative water
        res_neg_water = client.post(
            "/api/v1/nutrition/water",
            json={"amountLiters": -1.0},
        )
        assert res_neg_water.status_code == 422

        # Invalid meal type
        res_bad_meal = client.post(
            "/api/v1/nutrition/meals",
            json={"mealType": "midnight_snack", "foodName": "Invalid", "calories": 100, "proteinGrams": 10.0, "carbsGrams": 10.0, "fatGrams": 2.0},
        )
        assert res_bad_meal.status_code == 422

        # Malformed date
        res_bad_date = client.post(
            "/api/v1/nutrition/water",
            json={"amountLiters": 0.5, "date": "invalid-date-format"},
        )
        assert res_bad_date.status_code == 422
    finally:
        app.dependency_overrides.clear()


# =============================================================================
# 19. ZERO TARGET CALCULATIONS HANDLED SAFELY
# =============================================================================

def test_zero_target_calculation_handled_safely(
    client: TestClient,
    mock_nutrition_repo: NutritionRepository,
    mock_user_repo: UserRepository,
):
    """19. Test that zero targets do not cause division-by-zero errors."""
    user = CurrentUser(uid="zero_tgt_user", email="zero@pulseai.fit", name="Zero User", email_verified=True)
    mock_user_repo._in_memory_store[user.uid] = {
        "id": user.uid,
        "name": user.name,
        "email": user.email,
        "targetCalories": 0,
        "targetProteinGrams": 0,
        "targetCarbsGrams": 0,
        "targetFatGrams": 0,
    }
    app.dependency_overrides[get_current_user] = lambda: user
    app.dependency_overrides[get_nutrition_repository] = lambda: mock_nutrition_repo
    app.dependency_overrides[get_user_repository] = lambda: mock_user_repo

    try:
        res = client.get("/api/v1/nutrition/daily?date=2026-09-05")
        assert res.status_code == 200
        data = res.json()
        assert data["targetCalories"] == 0
        for tgt in data["nutrientTargets"]:
            assert tgt["pct"] == 0.0
    finally:
        app.dependency_overrides.clear()


# =============================================================================
# 20. WEEKLY SUMMARY HANDLES MISSING DAYS
# =============================================================================

def test_weekly_summary_handles_missing_days(
    client: TestClient,
    mock_nutrition_repo: NutritionRepository,
    mock_user_repo: UserRepository,
):
    """20. Test that dates with no logs return 0 kcal cleanly without crashing or fabricating data."""
    user = CurrentUser(uid="sparse_user", email="sparse@pulseai.fit", name="Sparse User", email_verified=True)
    app.dependency_overrides[get_current_user] = lambda: user
    app.dependency_overrides[get_nutrition_repository] = lambda: mock_nutrition_repo
    app.dependency_overrides[get_user_repository] = lambda: mock_user_repo

    try:
        # No meals logged at all
        res = client.get("/api/v1/nutrition/weekly?date=2026-09-05")
        assert res.status_code == 200
        days = res.json()
        assert len(days) == 7
        assert all(d["calories"] == 0 for d in days)
        assert all(d["pct"] == 0.0 for d in days)
    finally:
        app.dependency_overrides.clear()


# =============================================================================
# 21. FOOD CATALOGUE SEEDING IS IDEMPOTENT
# =============================================================================

def test_food_seeding_is_idempotent(mock_nutrition_repo: NutritionRepository):
    """21. Test that calling ensure_seeded multiple times does not corrupt or duplicate items."""
    initial_count = len(mock_nutrition_repo._in_memory_foods)
    assert initial_count >= 50

    mock_nutrition_repo.ensure_seeded()
    assert len(mock_nutrition_repo._in_memory_foods) == initial_count
