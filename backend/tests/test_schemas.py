from backend.app.schemas.user import UserProfileSchema, PersonalInformationSchema
from backend.app.schemas.workout import ExerciseSchema, WorkoutSchema, WorkoutSetSchema, WorkoutExerciseSchema
from backend.app.schemas.nutrition import DailyNutritionSchema, MealSchema, FoodItemSchema
from backend.app.schemas.progress import ProgressSummarySchema, BodyCompositionStatsSchema
from backend.app.schemas.form_analysis import FormAnalysisSessionSchema
from backend.app.schemas.notification import NotificationItemSchema


def test_user_profile_schema():
    """Validates UserProfile schema matches frontend mock data."""
    payload = {
        "id": "usr_rohit_101",
        "name": "Rohit Sharma",
        "email": "rohit.sharma@example.com",
        "age": 28,
        "heightCm": 178,
        "weightKg": 72.4,
        "fitnessLevel": "intermediate",
        "primaryGoal": "muscle_gain",
        "secondaryGoals": ["fat_loss", "strength"],
        "environment": "gym",
        "availableEquipment": ["barbell", "dumbbells", "cable_machine", "pull_up_bar"],
        "workoutFrequencyDaysPerWeek": 5,
        "workoutDurationMinutes": 45,
        "dietaryPreference": "vegetarian",
        "targetCalories": 2400,
        "targetProteinGrams": 160,
        "targetCarbsGrams": 280,
        "targetFatGrams": 80,
        "bmi": 22.8,
        "bmr": 1740,
        "tdee": 2390,
    }
    user = UserProfileSchema(**payload)
    assert user.name == "Rohit Sharma"
    assert user.fitnessLevel == "intermediate"
    assert user.targetCalories == 2400


def test_workout_and_exercise_schemas():
    """Validates Exercise and Workout schemas."""
    exercise = ExerciseSchema(
        id="ex_bench_press",
        name="Bench Press",
        description="Primary chest builder.",
        primaryMuscles=["chest"],
        secondaryMuscles=["shoulders", "triceps"],
        equipment=["barbell"],
        difficulty="intermediate",
        category="strength",
        instructions=["Lie flat", "Press up"],
        supportedFormAnalysis=True,
        supportedCameraMode="side",
    )
    assert exercise.id == "ex_bench_press"

    workout_exercise = WorkoutExerciseSchema(
        id="we_1",
        exerciseId=exercise.id,
        exercise=exercise,
        sets=[WorkoutSetSchema(setNumber=1, targetReps=10, isCompleted=True)],
        restSecondsBetweenSets=90,
    )

    workout = WorkoutSchema(
        id="wkt_upper_push",
        title="Upper Body Push",
        description="Chest and tricep focus",
        targetEnvironment="gym",
        estimatedDurationMinutes=45,
        difficulty="intermediate",
        targetMuscles=["chest", "triceps"],
        exercises=[workout_exercise],
    )
    assert workout.title == "Upper Body Push"
    assert len(workout.exercises) == 1


def test_nutrition_schema():
    """Validates DailyNutrition and Meal schemas."""
    food = FoodItemSchema(
        id="f1",
        name="Oats with Berries",
        calories=350,
        proteinGrams=14.0,
        carbsGrams=55.0,
        fatGrams=6.0,
        servingSizeGrams=150.0,
    )
    meal = MealSchema(
        id="m1",
        time="8:00 AM",
        type="breakfast",
        name="Breakfast Bowl",
        totalCalories=350,
        totalProteinGrams=14.0,
        totalCarbsGrams=55.0,
        totalFatGrams=6.0,
        foodList=["Oats", "Berries"],
        foods=[food],
    )
    daily = DailyNutritionSchema(
        date="Today, May 12, 2025",
        targetCalories=2400,
        consumedCalories=350,
        targetProteinGrams=160,
        consumedProteinGrams=14,
        targetCarbsGrams=250,
        consumedCarbsGrams=55,
        targetFatGrams=80,
        consumedFatGrams=6,
        waterIntakeLiters=1.5,
        waterTargetLiters=3.0,
        meals=[meal],
    )
    assert daily.consumedCalories == 350
    assert len(daily.meals) == 1


def test_notification_schema():
    """Validates NotificationItem schema."""
    notification = NotificationItemSchema(
        id="n1",
        category="Workout",
        title="Workout completed!",
        message="Great job on Push Day!",
        timestamp="2:42 PM",
        dateGroup="Today",
        read=False,
        important=True,
        iconName="dumbbell",
        actionLabel="View Workout >",
        actionRoute="/workouts/ex_upper_push",
    )
    assert notification.category == "Workout"
    assert notification.read is False
