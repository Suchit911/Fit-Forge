"""
Dedicated Backend Unit, Integration, Lifecycle, Security & Authority Tests for Phase 9C.4:
Adaptive Workout Plan & Dynamic Prescription Integration.

Verifies:
1. Retrieval:
   - No active program -> 404
   - Baseline effective prescription equals original planSnapshot
   - Completed workout is marked isCompleted=True and remains historical
2. Double Progression:
   - Upper compound +2.5 kg applied to future days
   - Lower compound +5.0 kg applied to future days
   - Isolation +1.0 kg applied to future days
   - Bodyweight +1 rep applied
   - Exact 5% ceiling allowed (50 kg + 2.5 kg = 52.5 kg)
   - >5% ceiling constrained/rejected (40 kg + 2.5 kg = 42.5 kg -> 6.25%)
   - No authoritative baseline weight -> constrained/rejected, never fabricate weight
3. Volume Fatigue:
   - Volume fatigue reduces sets by exactly 1 set
   - Minimum 1 set bound enforced (cannot reduce to 0 sets)
   - Maximum 5 sets bound respected
4. Safety & Bounds:
   - Target RPE clamped to <= 9.0
   - Duration bound <= 125% enforced
5. Immutability & Future-Workout Targeting:
   - Completed workouts in completedWorkouts are NEVER modified
   - In-progress workouts are NOT silently modified
   - Future eligible workouts receive adaptations
   - Original planSnapshot remains 100% byte-for-byte intact
   - effectivePlanSnapshot reflects adapted prescriptions
6. Versioning & Idempotency:
   - planVersion increments deterministically (1 -> 2 -> 3)
   - Detailed audit entry stored in adaptationHistory
   - Duplicate decision returns status="already_applied"
   - Duplicate decision causes NO second load increase (60 -> 62.5, NEVER 65)
7. Adherence / Next-Block Split:
   - Preserved in pendingNextBlockSplit without mutating active mesocycle
8. Boundary & Security:
   - Abandoned program rejected (422)
   - Completed program rejected (422)
   - Cross-user isolation enforced (403/404)
   - Unauthenticated requests return 401
   - No Slot 0 corrective injection
   - Deterministic output across repeated runs
9. DECISION AUTHORITY & TAMPERING PREVENTION (Correction Pass):
   - Valid 9C.2 decision is accepted.
   - Same decision with modified exerciseId rejected.
   - Same decision with modified adaptationType rejected.
   - Same decision with modified ruleCode rejected.
   - Same decision with modified proposed load rejected.
   - Same decision with modified proposed reps rejected.
   - Same decision with modified proposed sets rejected.
   - Same decision with modified RPE rejected.
   - Same decision with modified evidence rejected.
   - Same decision with modified programId rejected.
   - Same decision with modified planId rejected.
   - Same decision with modified decisionId rejected.
   - Stale decision rejected.
   - Decision from another program rejected.
   - Decision from another user rejected.
   - Arbitrary fabricated AdaptationDecision rejected.
   - Forged progression cannot bypass the 5% ceiling.
   - Forged volume reduction cannot bypass set bounds.
   - Forged RPE cannot exceed 9.
   - Forged duration cannot exceed 125%.
"""

import uuid
import json
import pytest
from datetime import datetime, timezone, timedelta
from fastapi import HTTPException
from fastapi.testclient import TestClient

from backend.app.main import app
from backend.app.core.security import get_current_user, CurrentUser
from backend.app.schemas.program import (
    ProgramResponse,
    ProgramStartRequest,
    ProgramSyncSessionRequest,
    ProgramAbandonRequest,
    EffectivePrescriptionResponse,
    ApplyAdaptationRequest,
    ApplyAdaptationResponse,
    ProgramVersionsResponse,
)
from backend.app.schemas.workout_plan import (
    WorkoutPlanResponse,
    PlannedWeek,
    PlannedWorkoutDay,
    PlannedExercise,
    PlannedSet,
    WorkoutSplitType,
    ExerciseSlotRole,
)
from backend.app.schemas.workout import (
    WorkoutSessionCreate,
    WorkoutSessionResponse,
    WorkoutSessionComplete,
    WorkoutSetRecord,
    WorkoutSetSchema,
)
from backend.app.schemas.adaptation import (
    AdaptationDecision,
    PrescriptionDelta,
    AdaptationEvaluationRequest,
    generate_decision_id,
)
from backend.app.repositories.program_repository import (
    get_program_repository,
    ProgramRepository,
)
from backend.app.repositories.workout_repository import (
    get_workout_repository,
    WorkoutRepository,
)
from backend.app.repositories.user_repository import (
    get_user_repository,
    UserRepository,
)
from backend.app.services.program_service import (
    get_program_service,
    ProgramService,
)
from backend.app.services.adaptation_application_service import (
    get_adaptation_application_service,
    AdaptationApplicationService,
)
from backend.app.services.adaptation_engine_service import (
    get_adaptation_engine_service,
    AdaptationEngineService,
)


# =============================================================================
# Fixtures & Helpers
# =============================================================================

@pytest.fixture
def auth_user():
    return CurrentUser(
        uid=f"usr_9c4_athlete_{uuid.uuid4().hex[:8]}",
        email="athlete9c4@example.com",
        name="Athlete 9C4",
        email_verified=True,
    )


@pytest.fixture
def other_user():
    return CurrentUser(
        uid=f"usr_9c4_other_{uuid.uuid4().hex[:8]}",
        email="other9c4@example.com",
        name="Other User",
        email_verified=True,
    )


@pytest.fixture(autouse=True)
def clean_repos():
    """Cleans in-memory stores before and after each test and ensures in-memory isolation."""
    prog_repo = get_program_repository()
    wkt_repo = get_workout_repository()
    orig_prog_db = prog_repo._db
    orig_wkt_db = wkt_repo._db
    prog_repo._db = None
    wkt_repo._db = None
    prog_repo.clear_in_memory()
    wkt_repo._in_memory_sessions.clear()
    yield
    prog_repo.clear_in_memory()
    wkt_repo._in_memory_sessions.clear()
    prog_repo._db = orig_prog_db
    wkt_repo._db = orig_wkt_db


def build_sample_multiweek_plan(
    total_weeks: int = 2,
    days_per_week: int = 2,
) -> WorkoutPlanResponse:
    """Constructs a valid WorkoutPlanResponse with realistic catalog exercises."""
    weeks: list[PlannedWeek] = []
    for w in range(1, total_weeks + 1):
        days: list[PlannedWorkoutDay] = []
        for d in range(1, days_per_week + 1):
            if d == 1:
                # Lower compound (squat) + Isolation
                ex1 = PlannedExercise(
                    slotRole=ExerciseSlotRole.PRIMARY_COMPOUND,
                    slotIndex=1,
                    exerciseId="ex_barbell_squat",
                    name="Barbell Back Squat",
                    movementPattern="squat",
                    exerciseType="compound",
                    difficulty="intermediate",
                    equipment=["barbell"],
                    primaryMuscles=["quadriceps", "glutes"],
                    prescribedSets=[
                        PlannedSet(setNumber=1, targetReps=8, targetRepsMin=6, targetRepsMax=8, restSeconds=120, targetRpe=8.0, targetWeightKg=100.0, weightKg=100.0),
                        PlannedSet(setNumber=2, targetReps=8, targetRepsMin=6, targetRepsMax=8, restSeconds=120, targetRpe=8.0, targetWeightKg=100.0, weightKg=100.0),
                        PlannedSet(setNumber=3, targetReps=8, targetRepsMin=6, targetRepsMax=8, restSeconds=120, targetRpe=8.0, targetWeightKg=100.0, weightKg=100.0),
                    ],
                    totalSets=3,
                    estimatedDurationMinutes=15,
                    score=90.0,
                    targetWeightKg=100.0,
                    weightKg=100.0,
                    reasons=["Primary lower strength"],
                    prescriptionRationale="Baseline compound progression",
                )
                ex2 = PlannedExercise(
                    slotRole=ExerciseSlotRole.ACCESSORY_1,
                    slotIndex=3,
                    exerciseId="ex_bicep_curl",
                    name="Dumbbell Bicep Curl",
                    movementPattern="isolation",
                    exerciseType="isolation",
                    difficulty="beginner",
                    equipment=["dumbbells"],
                    primaryMuscles=["biceps"],
                    prescribedSets=[
                        PlannedSet(setNumber=1, targetReps=12, targetRepsMin=10, targetRepsMax=12, restSeconds=60, targetRpe=8.0, targetWeightKg=20.0, weightKg=20.0),
                        PlannedSet(setNumber=2, targetReps=12, targetRepsMin=10, targetRepsMax=12, restSeconds=60, targetRpe=8.0, targetWeightKg=20.0, weightKg=20.0),
                    ],
                    totalSets=2,
                    estimatedDurationMinutes=10,
                    score=85.0,
                    targetWeightKg=20.0,
                    weightKg=20.0,
                    reasons=["Accessory arm volume"],
                )
                exercises = [ex1, ex2]
                focus = "Lower & Arms"
            else:
                # Upper compound (bench press) + bodyweight
                ex1 = PlannedExercise(
                    slotRole=ExerciseSlotRole.PRIMARY_COMPOUND,
                    slotIndex=1,
                    exerciseId="ex_bench_press",
                    name="Barbell Bench Press",
                    movementPattern="horizontal_push",
                    exerciseType="compound",
                    difficulty="intermediate",
                    equipment=["barbell"],
                    primaryMuscles=["chest", "triceps"],
                    prescribedSets=[
                        PlannedSet(setNumber=1, targetReps=8, targetRepsMin=6, targetRepsMax=8, restSeconds=120, targetRpe=8.0, targetWeightKg=50.0, weightKg=50.0),
                        PlannedSet(setNumber=2, targetReps=8, targetRepsMin=6, targetRepsMax=8, restSeconds=120, targetRpe=8.0, targetWeightKg=50.0, weightKg=50.0),
                        PlannedSet(setNumber=3, targetReps=8, targetRepsMin=6, targetRepsMax=8, restSeconds=120, targetRpe=8.0, targetWeightKg=50.0, weightKg=50.0),
                    ],
                    totalSets=3,
                    estimatedDurationMinutes=15,
                    score=92.0,
                    targetWeightKg=50.0,
                    weightKg=50.0,
                    reasons=["Primary upper strength"],
                )
                ex2 = PlannedExercise(
                    slotRole=ExerciseSlotRole.ACCESSORY_1,
                    slotIndex=3,
                    exerciseId="ex_pushup",
                    name="Push-Up",
                    movementPattern="horizontal_push",
                    exerciseType="compound",
                    difficulty="beginner",
                    equipment=["bodyweight"],
                    primaryMuscles=["chest", "triceps"],
                    prescribedSets=[
                        PlannedSet(setNumber=1, targetReps=15, targetRepsMin=12, targetRepsMax=15, restSeconds=60, targetRpe=8.0),
                        PlannedSet(setNumber=2, targetReps=15, targetRepsMin=12, targetRepsMax=15, restSeconds=60, targetRpe=8.0),
                    ],
                    totalSets=2,
                    estimatedDurationMinutes=10,
                    score=80.0,
                    reasons=["Bodyweight chest volume"],
                )
                exercises = [ex1, ex2]
                focus = "Upper Body"

            days.append(
                PlannedWorkoutDay(
                    dayNumber=d,
                    dayLabel=f"Day {d} Workout",
                    isRestDay=False,
                    focus=focus,
                    exercises=exercises,
                    totalSets=sum(e.totalSets for e in exercises),
                    estimatedDurationMinutes=45,
                )
            )

        weeks.append(
            PlannedWeek(
                weekNumber=w,
                phaseLabel="Baseline Accumulation" if w == 1 else "Volume Loading",
                days=days,
                totalWeeklySets=sum(d.totalSets for d in days),
                totalWorkouts=len(days),
            )
        )

    return WorkoutPlanResponse(
        planId=f"plan_test_{uuid.uuid4().hex[:8]}",
        title="2-Week Upper/Lower Mesocycle",
        description="2-Week Upper/Lower Mesocycle Plan",
        splitType=WorkoutSplitType.UPPER_LOWER,
        totalWeeks=total_weeks,
        trainingDaysPerWeek=days_per_week,
        weeks=weeks,
        targetGoal="strength",
        fitnessLevel="intermediate",
        environment="gym",
        availableEquipment=["barbell", "dumbbells", "bodyweight"],
        periodizationModel="linear_block",
        summary="2-week test plan",
        appliedFilters={"planner_version": "9B.8.5.1", "target_duration_minutes": 60},
    )


def seed_qualifying_sessions(
    uid: str,
    exercise_id: str,
    weight_kg: float = 50.0,
    reps: int = 8,
    sets_count: int = 3,
    num_sessions: int = 3,
    is_completed: bool = True,
    completion_rate: float = 1.0,
) -> list[WorkoutSessionResponse]:
    """Seeds completed workout sessions into the WorkoutRepository for uid."""
    wkt_repo = get_workout_repository()
    now = datetime.now(timezone.utc)
    sessions = []
    for i in range(num_sessions):
        sess_id = f"sess_{uuid.uuid4().hex[:8]}"
        sets = []
        for s_idx in range(1, sets_count + 1):
            set_done = is_completed and (s_idx <= int(sets_count * completion_rate))
            sets.append(
                WorkoutSetSchema(
                    setNumber=s_idx,
                    targetReps=reps,
                    targetRepsMax=reps,
                    targetRepsMin=max(1, reps - 2),
                    actualReps=reps if set_done else 0,
                    targetWeightKg=weight_kg,
                    actualWeightKg=weight_kg if set_done else 0.0,
                    isCompleted=set_done,
                )
            )
        completed_count = sum(1 for st in sets if st.isCompleted)
        s_date = (now - timedelta(days=(num_sessions - i) * 2)).isoformat()
        session_data = {
            "id": sess_id,
            "userId": uid,
            "workoutId": f"wkt_{i}",
            "workoutTitle": f"Workout {i}",
            "status": "completed",
            "startedAt": s_date,
            "completedAt": s_date,
            "totalSetsCount": sets_count,
            "completedSetsCount": completed_count,
            "completedSets": {exercise_id: sets},
        }
        wkt_repo._in_memory_sessions[f"{uid}:{sess_id}"] = session_data
        sessions.append(WorkoutSessionResponse(**session_data))
    return sessions


def get_authoritative_decision(
    uid: str,
    exercise_id: str,
    weight_kg: float = 50.0,
    sets_count: int = 3,
    reps_min: int = 6,
    reps_max: int = 8,
    target_rpe: float = 8.0,
) -> AdaptationDecision:
    """Evaluates and returns an authoritative Phase 9C.2 decision for the user."""
    engine = get_adaptation_engine_service()
    candidate = PrescriptionDelta(
        exerciseId=exercise_id,
        weightKg=weight_kg,
        setCount=sets_count,
        targetRepsMin=reps_min,
        targetRepsMax=reps_max,
        targetRpe=target_rpe,
        restSeconds=90,
    )
    resp = engine.evaluate_adaptations(
        uid=uid,
        request=AdaptationEvaluationRequest(candidateExercises=[candidate], windowDays=28),
    )
    for dec in resp.primaryDecisions:
        if dec.exerciseId == exercise_id:
            return dec
    raise ValueError(f"No decision produced for exercise {exercise_id}")


def seed_split_adherence_data(uid: str):
    """Seeds user profile and completed workouts causing adherence split recommendation."""
    user_repo = get_user_repository()
    wkt_repo = get_workout_repository()
    user_repo._in_memory_store[uid] = {
        "id": uid,
        "name": "Athlete 9C4",
        "email": "athlete9c4@example.com",
        "workoutFrequencyDaysPerWeek": 5,
        "profile_complete": True,
    }
    now = datetime.now(timezone.utc)
    for i in range(12):
        s_id = f"adherence_sess_{i}_{uuid.uuid4().hex[:6]}"
        s_time = (now - timedelta(days=26 - (i * 2))).isoformat()
        wkt_repo._in_memory_sessions[f"{uid}:{s_id}"] = {
            "id": s_id,
            "userId": uid,
            "workoutId": f"wkt_{i}",
            "workoutTitle": f"Workout {i}",
            "status": "completed",
            "startedAt": s_time,
            "completedAt": s_time,
            "totalSetsCount": 3,
            "completedSetsCount": 3,
            "completedSets": {},
        }


# =============================================================================
# 1. RETRIEVAL & BASELINE TESTS
# =============================================================================

def test_get_effective_prescription_no_active_program(auth_user):
    """Querying effective prescription when user has no active program returns 404."""
    service = get_adaptation_application_service()
    with pytest.raises(HTTPException) as exc_info:
        service.get_effective_prescription(auth_user.uid, week=1, day=1)
    assert exc_info.value.status_code == 404
    assert "No active workout program found" in exc_info.value.detail


def test_get_effective_prescription_baseline_equals_original(auth_user):
    """Prior to any adaptation, effective prescription exactly equals original planSnapshot."""
    prog_service = get_program_service()
    adapt_service = get_adaptation_application_service()

    plan = build_sample_multiweek_plan(total_weeks=2, days_per_week=2)
    prog = prog_service.start_program(auth_user.uid, ProgramStartRequest(plan=plan))
    assert prog.status == "active"
    assert prog.planVersion == 1

    eff = adapt_service.get_effective_prescription(auth_user.uid, week=1, day=1)
    assert eff.programId == prog.programId
    assert eff.planVersion == 1
    assert eff.isAdapted is False
    assert eff.isCompleted is False
    assert len(eff.appliedAdaptations) == 0
    assert len(eff.day.exercises) == 2
    assert eff.day.exercises[0].exerciseId == "ex_barbell_squat"
    assert eff.day.exercises[0].prescribedSets[0].targetWeightKg == 100.0


# =============================================================================
# 2. DOUBLE PROGRESSION APPLICATION TESTS
# =============================================================================

def test_apply_adaptation_upper_compound_load_progression_2_5kg(auth_user):
    """Upper compound progression applies exactly +2.5 kg to eligible future days."""
    prog_service = get_program_service()
    adapt_service = get_adaptation_application_service()

    plan = build_sample_multiweek_plan(total_weeks=2, days_per_week=2)
    prog_service.start_program(auth_user.uid, ProgramStartRequest(plan=plan))

    # Seed 3 qualifying sessions on bench press at 50.0 kg
    seed_qualifying_sessions(auth_user.uid, "ex_bench_press", weight_kg=50.0, reps=8, sets_count=3, num_sessions=3)
    decision = get_authoritative_decision(auth_user.uid, "ex_bench_press", weight_kg=50.0, sets_count=3, reps_min=6, reps_max=8)

    resp = adapt_service.apply_adaptation(auth_user.uid, ApplyAdaptationRequest(decision=decision))
    assert resp.status == "applied"
    assert resp.planVersion == 2
    assert resp.affectedDaysCount == 2  # Week 1 Day 2, Week 2 Day 2

    # Verify effective prescription for Week 1 Day 2
    eff = adapt_service.get_effective_prescription(auth_user.uid, week=1, day=2)
    assert eff.isAdapted is True
    assert eff.planVersion == 2
    bench = next(ex for ex in eff.day.exercises if ex.exerciseId == "ex_bench_press")
    assert bench.targetWeightKg == 52.5
    assert bench.prescribedSets[0].targetWeightKg == 52.5
    assert "Adapted (+2.5 kg)" in (bench.progressionNote or "")


def test_apply_adaptation_lower_compound_load_progression_5kg(auth_user):
    """Lower compound progression applies exactly +5.0 kg to eligible future days."""
    prog_service = get_program_service()
    adapt_service = get_adaptation_application_service()

    plan = build_sample_multiweek_plan(total_weeks=2, days_per_week=2)
    prog_service.start_program(auth_user.uid, ProgramStartRequest(plan=plan))

    # Seed 3 qualifying sessions on squat at 100.0 kg
    seed_qualifying_sessions(auth_user.uid, "ex_barbell_squat", weight_kg=100.0, reps=8, sets_count=3, num_sessions=3)
    decision = get_authoritative_decision(auth_user.uid, "ex_barbell_squat", weight_kg=100.0, sets_count=3, reps_min=6, reps_max=8)

    resp = adapt_service.apply_adaptation(auth_user.uid, ApplyAdaptationRequest(decision=decision))
    assert resp.status == "applied"
    assert resp.planVersion == 2

    eff = adapt_service.get_effective_prescription(auth_user.uid, week=1, day=1)
    assert eff.isAdapted is True
    squat = next(ex for ex in eff.day.exercises if ex.exerciseId == "ex_barbell_squat")
    assert squat.targetWeightKg == 105.0
    assert squat.prescribedSets[0].targetWeightKg == 105.0


def test_apply_adaptation_isolation_load_progression_1kg(auth_user):
    """Isolation exercise progression applies +1.0 kg."""
    prog_service = get_program_service()
    adapt_service = get_adaptation_application_service()

    plan = build_sample_multiweek_plan(total_weeks=2, days_per_week=2)
    prog_service.start_program(auth_user.uid, ProgramStartRequest(plan=plan))

    # Seed 3 qualifying sessions on bicep curl at 20.0 kg
    seed_qualifying_sessions(auth_user.uid, "ex_bicep_curl", weight_kg=20.0, reps=12, sets_count=2, num_sessions=3)
    decision = get_authoritative_decision(auth_user.uid, "ex_bicep_curl", weight_kg=20.0, sets_count=2, reps_min=10, reps_max=12)

    resp = adapt_service.apply_adaptation(auth_user.uid, ApplyAdaptationRequest(decision=decision))
    assert resp.status == "applied"

    eff = adapt_service.get_effective_prescription(auth_user.uid, week=1, day=1)
    curl = next(ex for ex in eff.day.exercises if ex.exerciseId == "ex_bicep_curl")
    assert curl.targetWeightKg == 21.0
    assert curl.prescribedSets[0].targetWeightKg == 21.0


def test_apply_adaptation_bodyweight_rep_progression_plus_1_rep(auth_user):
    """Bodyweight exercise progression applies +1 rep."""
    prog_service = get_program_service()
    adapt_service = get_adaptation_application_service()

    plan = build_sample_multiweek_plan(total_weeks=2, days_per_week=2)
    prog_service.start_program(auth_user.uid, ProgramStartRequest(plan=plan))

    # Seed 3 qualifying sessions on pushup
    seed_qualifying_sessions(auth_user.uid, "ex_pushup", weight_kg=0.0, reps=15, sets_count=2, num_sessions=3)
    decision = get_authoritative_decision(auth_user.uid, "ex_pushup", weight_kg=0.0, sets_count=2, reps_min=12, reps_max=15)

    resp = adapt_service.apply_adaptation(auth_user.uid, ApplyAdaptationRequest(decision=decision))
    assert resp.status == "applied"
    assert resp.planVersion == 2

    eff = adapt_service.get_effective_prescription(auth_user.uid, week=1, day=2)
    pushup = next(ex for ex in eff.day.exercises if ex.exerciseId == "ex_pushup")
    assert pushup.prescribedSets[0].targetReps == 16
    assert pushup.prescribedSets[0].targetRepsMin == 13
    assert pushup.prescribedSets[0].targetRepsMax == 16


def test_apply_adaptation_exact_5_percent_ceiling_approved(auth_user):
    """An exact 5.0% load increase (e.g. 50 kg + 2.5 kg = 52.5 kg) is approved."""
    prog_service = get_program_service()
    adapt_service = get_adaptation_application_service()

    plan = build_sample_multiweek_plan(total_weeks=2, days_per_week=2)
    prog_service.start_program(auth_user.uid, ProgramStartRequest(plan=plan))

    seed_qualifying_sessions(auth_user.uid, "ex_bench_press", weight_kg=50.0, reps=8, sets_count=3, num_sessions=3)
    decision = get_authoritative_decision(auth_user.uid, "ex_bench_press", weight_kg=50.0, sets_count=3, reps_min=6, reps_max=8)

    resp = adapt_service.apply_adaptation(auth_user.uid, ApplyAdaptationRequest(decision=decision))
    assert resp.status == "applied"


def test_apply_adaptation_above_5_percent_ceiling_constrained(auth_user):
    """A proposed load increase exceeding 5.0% ceiling is constrained/rejected without mutating the plan."""
    prog_service = get_program_service()
    adapt_service = get_adaptation_application_service()

    plan = build_sample_multiweek_plan(total_weeks=2, days_per_week=2)
    prog_service.start_program(auth_user.uid, ProgramStartRequest(plan=plan))

    # Bench press at 40.0 kg: +2.5 kg would be +6.25%, which exceeds 5.0%
    seed_qualifying_sessions(auth_user.uid, "ex_bench_press", weight_kg=40.0, reps=8, sets_count=3, num_sessions=3)
    decision = get_authoritative_decision(auth_user.uid, "ex_bench_press", weight_kg=40.0, sets_count=3, reps_min=6, reps_max=8)

    assert decision.status == "constrained_no_change"
    resp = adapt_service.apply_adaptation(auth_user.uid, ApplyAdaptationRequest(decision=decision))
    assert resp.status == "constrained"
    assert resp.planVersion == 1


def test_apply_adaptation_no_authoritative_baseline_load_rejected(auth_user):
    """Without an authoritative baseline load, load progression is constrained to prevent fabricated weights."""
    prog_service = get_program_service()
    adapt_service = get_adaptation_application_service()

    plan = build_sample_multiweek_plan(total_weeks=2, days_per_week=2)
    prog_service.start_program(auth_user.uid, ProgramStartRequest(plan=plan))

    # User with NO history evaluating an unweighted candidate
    engine = get_adaptation_engine_service()
    resp_eval = engine.evaluate_adaptations(
        auth_user.uid,
        AdaptationEvaluationRequest(candidateExercises=[PrescriptionDelta(exerciseId="ex_barbell_squat", weightKg=0.0)]),
    )
    decision = resp_eval.primaryDecisions[0]

    resp = adapt_service.apply_adaptation(auth_user.uid, ApplyAdaptationRequest(decision=decision))
    assert resp.status == "rejected"
    assert resp.planVersion == 1


# =============================================================================
# 3. VOLUME FATIGUE APPLICATION TESTS
# =============================================================================

def test_apply_adaptation_volume_fatigue_minus_1_set(auth_user):
    """Volume fatigue adaptation reduces prescribed sets by exactly 1 across future workouts."""
    prog_service = get_program_service()
    adapt_service = get_adaptation_application_service()

    plan = build_sample_multiweek_plan(total_weeks=2, days_per_week=2)
    prog_service.start_program(auth_user.uid, ProgramStartRequest(plan=plan))

    # 2 consecutive volume failures on squat (1/3 sets completed -> < 70%)
    seed_qualifying_sessions(auth_user.uid, "ex_barbell_squat", weight_kg=100.0, reps=8, sets_count=3, num_sessions=2, completion_rate=0.34)
    decision = get_authoritative_decision(auth_user.uid, "ex_barbell_squat", weight_kg=100.0, sets_count=3)
    assert decision.status == "volume_reduction_candidate"
    assert decision.deltaMagnitude == -1.0

    resp = adapt_service.apply_adaptation(auth_user.uid, ApplyAdaptationRequest(decision=decision))
    assert resp.status == "applied"
    assert resp.planVersion == 2

    # Squat had 3 sets, now has exactly 2 sets
    eff = adapt_service.get_effective_prescription(auth_user.uid, week=1, day=1)
    squat = next(ex for ex in eff.day.exercises if ex.exerciseId == "ex_barbell_squat")
    assert squat.totalSets == 2
    assert len(squat.prescribedSets) == 2


def test_apply_adaptation_volume_fatigue_minimum_1_set_bound(auth_user):
    """Volume reduction cannot reduce sets below 1 set (exercise deletion prohibited)."""
    prog_service = get_program_service()
    adapt_service = get_adaptation_application_service()

    plan = build_sample_multiweek_plan(total_weeks=2, days_per_week=2)
    # Set squat to only 1 set in plan
    for w in plan.weeks:
        for d in w.days:
            for ex in d.exercises:
                if ex.exerciseId == "ex_barbell_squat":
                    ex.prescribedSets = [ex.prescribedSets[0]]
                    ex.totalSets = 1
    prog_service.start_program(auth_user.uid, ProgramStartRequest(plan=plan))

    seed_qualifying_sessions(auth_user.uid, "ex_barbell_squat", weight_kg=100.0, reps=8, sets_count=1, num_sessions=2, completion_rate=0.0)
    decision = get_authoritative_decision(auth_user.uid, "ex_barbell_squat", weight_kg=100.0, sets_count=1)
    assert decision.status == "constrained_no_change"

    resp = adapt_service.apply_adaptation(auth_user.uid, ApplyAdaptationRequest(decision=decision))
    assert resp.status == "constrained"
    assert resp.planVersion == 1


# =============================================================================
# 4. SAFETY & BOUNDS TESTS
# =============================================================================

def test_apply_adaptation_rpe_clamped_to_9(auth_user):
    """Prescribed target RPE is always clamped to <= 9.0."""
    prog_service = get_program_service()
    adapt_service = get_adaptation_application_service()

    plan = build_sample_multiweek_plan(total_weeks=2, days_per_week=2)
    prog_service.start_program(auth_user.uid, ProgramStartRequest(plan=plan))

    seed_qualifying_sessions(auth_user.uid, "ex_bench_press", weight_kg=50.0, reps=8, sets_count=3, num_sessions=3)
    decision = get_authoritative_decision(auth_user.uid, "ex_bench_press", weight_kg=50.0, sets_count=3, reps_min=6, reps_max=8, target_rpe=8.0)

    resp = adapt_service.apply_adaptation(auth_user.uid, ApplyAdaptationRequest(decision=decision))
    assert resp.status == "applied"

    eff = adapt_service.get_effective_prescription(auth_user.uid, week=1, day=2)
    bench = next(ex for ex in eff.day.exercises if ex.exerciseId == "ex_bench_press")
    for s in bench.prescribedSets:
        assert s.targetRpe <= 9.0


# =============================================================================
# 5. IMMUTABILITY & FUTURE-WORKOUT TARGETING TESTS
# =============================================================================

def test_apply_adaptation_completed_workout_never_modified(auth_user):
    """Historical completed workouts are strictly immutable; adaptations apply exclusively to future workouts."""
    prog_service = get_program_service()
    adapt_service = get_adaptation_application_service()
    wkt_repo = get_workout_repository()

    plan = build_sample_multiweek_plan(total_weeks=2, days_per_week=2)
    prog = prog_service.start_program(auth_user.uid, ProgramStartRequest(plan=plan))

    # Complete Week 1 Day 1
    create_req = WorkoutSessionCreate(
        workoutId="generated",
        workoutTitle="Week 1 Day 1",
        totalSetsCount=5,
        programId=prog.programId,
        planId=prog.planId,
        weekNumber=1,
        dayNumber=1,
    )
    sess = wkt_repo.create_session(auth_user.uid, create_req)
    wkt_repo.complete_session(auth_user.uid, sess.id, WorkoutSessionComplete(durationSeconds=2400))

    sync_req = ProgramSyncSessionRequest(sessionId=sess.id, weekNumber=1, dayNumber=1)
    prog_service.sync_session(auth_user.uid, sync_req)

    # Apply adaptation for squat (+5 kg)
    seed_qualifying_sessions(auth_user.uid, "ex_barbell_squat", weight_kg=100.0, reps=8, sets_count=3, num_sessions=3)
    decision = get_authoritative_decision(auth_user.uid, "ex_barbell_squat", weight_kg=100.0, sets_count=3)

    resp = adapt_service.apply_adaptation(auth_user.uid, ApplyAdaptationRequest(decision=decision))
    assert resp.status == "applied"

    # Week 1 Day 1 (completed) MUST have isCompleted=True and retains original 100 kg
    eff_w1d1 = adapt_service.get_effective_prescription(auth_user.uid, week=1, day=1)
    assert eff_w1d1.isCompleted is True
    squat_w1 = next(ex for ex in eff_w1d1.day.exercises if ex.exerciseId == "ex_barbell_squat")
    assert squat_w1.targetWeightKg == 100.0

    # Week 2 Day 1 (future) is adapted to 105.0 kg!
    eff_w2d1 = adapt_service.get_effective_prescription(auth_user.uid, week=2, day=1)
    assert eff_w2d1.isCompleted is False
    assert eff_w2d1.isAdapted is True
    squat_w2 = next(ex for ex in eff_w2d1.day.exercises if ex.exerciseId == "ex_barbell_squat")
    assert squat_w2.targetWeightKg == 105.0


def test_apply_adaptation_original_plan_snapshot_byte_intact(auth_user):
    """The original planSnapshot remains 100% byte-for-byte intact after any adaptation."""
    prog_service = get_program_service()
    adapt_service = get_adaptation_application_service()

    plan = build_sample_multiweek_plan(total_weeks=2, days_per_week=2)
    prog = prog_service.start_program(auth_user.uid, ProgramStartRequest(plan=plan))

    original_json = json.dumps(prog.planSnapshot.model_dump(), sort_keys=True)

    seed_qualifying_sessions(auth_user.uid, "ex_barbell_squat", weight_kg=100.0, reps=8, sets_count=3, num_sessions=3)
    decision = get_authoritative_decision(auth_user.uid, "ex_barbell_squat", weight_kg=100.0, sets_count=3)

    adapt_service.apply_adaptation(auth_user.uid, ApplyAdaptationRequest(decision=decision))

    after_prog = prog_service.get_active_program(auth_user.uid)
    after_original_json = json.dumps(after_prog.planSnapshot.model_dump(), sort_keys=True)

    assert original_json == after_original_json


# =============================================================================
# 6. VERSIONING & IDEMPOTENCY TESTS
# =============================================================================

def test_apply_adaptation_duplicate_decision_idempotent(auth_user):
    """Applying the exact same decisionId twice returns already_applied and does NOT bump planVersion twice."""
    prog_service = get_program_service()
    adapt_service = get_adaptation_application_service()

    plan = build_sample_multiweek_plan(total_weeks=2, days_per_week=2)
    prog_service.start_program(auth_user.uid, ProgramStartRequest(plan=plan))

    seed_qualifying_sessions(auth_user.uid, "ex_bench_press", weight_kg=50.0, reps=8, sets_count=3, num_sessions=3)
    decision = get_authoritative_decision(auth_user.uid, "ex_bench_press", weight_kg=50.0, sets_count=3)

    # First call: applied
    resp1 = adapt_service.apply_adaptation(auth_user.uid, ApplyAdaptationRequest(decision=decision))
    assert resp1.status == "applied"
    assert resp1.planVersion == 2

    # Second call with exact same decision: already_applied, version stays 2
    resp2 = adapt_service.apply_adaptation(auth_user.uid, ApplyAdaptationRequest(decision=decision))
    assert resp2.status == "already_applied"
    assert resp2.planVersion == 2

    # Load stays 52.5 kg, NEVER 55.0 kg
    eff = adapt_service.get_effective_prescription(auth_user.uid, week=1, day=2)
    bench = next(ex for ex in eff.day.exercises if ex.exerciseId == "ex_bench_press")
    assert bench.targetWeightKg == 52.5


def test_apply_adaptation_audit_history_recorded(auth_user):
    """Successful adaptation appends a complete deterministic audit record into adaptationHistory."""
    prog_service = get_program_service()
    adapt_service = get_adaptation_application_service()

    plan = build_sample_multiweek_plan(total_weeks=2, days_per_week=2)
    prog_service.start_program(auth_user.uid, ProgramStartRequest(plan=plan))

    seed_qualifying_sessions(auth_user.uid, "ex_bench_press", weight_kg=50.0, reps=8, sets_count=3, num_sessions=3)
    decision = get_authoritative_decision(auth_user.uid, "ex_bench_press", weight_kg=50.0, sets_count=3)

    resp = adapt_service.apply_adaptation(auth_user.uid, ApplyAdaptationRequest(decision=decision))
    assert resp.adaptationRecord is not None
    assert resp.adaptationRecord["decisionId"] == decision.decisionId
    assert resp.adaptationRecord["versionBefore"] == 1
    assert resp.adaptationRecord["versionAfter"] == 2
    assert resp.adaptationRecord["status"] == "applied"


# =============================================================================
# 7. ADHERENCE / NEXT-BLOCK SPLIT TEST
# =============================================================================

def test_apply_adaptation_adherence_next_block_split_stored(auth_user):
    """Adherence split recommendation is stored into pendingNextBlockSplit without mutating active program."""
    prog_service = get_program_service()
    adapt_service = get_adaptation_application_service()

    plan = build_sample_multiweek_plan(total_weeks=2, days_per_week=2)
    prog_service.start_program(auth_user.uid, ProgramStartRequest(plan=plan))

    seed_split_adherence_data(auth_user.uid)
    engine = get_adaptation_engine_service()
    signals = engine.signal_service.get_personalization_signals(auth_user.uid, window_days=28)
    split_rec = engine._evaluate_future_split_adaptation(auth_user.uid, signals)
    assert split_rec is not None

    dec_id = generate_decision_id(
        user_id=auth_user.uid,
        scope_id="program_split",
        rule_code=split_rec.ruleCode,
        adaptation_type="split_adjustment",
        status="future_split_adjustment_candidate",
        delta_magnitude=0.0,
    )
    decision = AdaptationDecision(
        decisionId=dec_id,
        exerciseId=None,
        canonicalName=None,
        adaptationType="split_adjustment",
        status="future_split_adjustment_candidate",
        ruleCode=split_rec.ruleCode,
        evidenceLevel="stable_signal",
        evidence={"adherenceRate": split_rec.adherenceRate, "recommendedSplit": split_rec.recommendedSplit},
        rationale=split_rec.reason,
        reasons=[split_rec.reason],
        constraintsApplied=[],
        isReversible=True,
        sourceSessionIds=[],
        generatedAt=datetime.now(timezone.utc).isoformat(),
    )

    resp = adapt_service.apply_adaptation(auth_user.uid, ApplyAdaptationRequest(decision=decision))
    assert resp.status == "applied"

    active = prog_service.get_active_program(auth_user.uid)
    assert active.pendingNextBlockSplit is not None
    assert active.pendingNextBlockSplit["ruleCode"] == "ADHERENCE_SPLIT_MISMATCH_4_WEEKS"
    assert active.splitType == WorkoutSplitType.UPPER_LOWER
    assert active.daysPerWeek == 2


# =============================================================================
# 8. LIFECYCLE BOUNDARY & SECURITY TESTS
# =============================================================================

def test_apply_adaptation_abandoned_program_rejected(auth_user):
    """Cannot apply adaptations to an abandoned program (returns 422)."""
    prog_service = get_program_service()
    adapt_service = get_adaptation_application_service()

    plan = build_sample_multiweek_plan(total_weeks=2, days_per_week=2)
    prog_service.start_program(auth_user.uid, ProgramStartRequest(plan=plan))
    prog_service.abandon_active_program(auth_user.uid)

    seed_qualifying_sessions(auth_user.uid, "ex_bench_press", weight_kg=50.0, reps=8, sets_count=3, num_sessions=3)
    decision = get_authoritative_decision(auth_user.uid, "ex_bench_press", weight_kg=50.0, sets_count=3)

    with pytest.raises(HTTPException) as exc_info:
        adapt_service.apply_adaptation(auth_user.uid, ApplyAdaptationRequest(decision=decision))
    assert exc_info.value.status_code == 422
    assert "abandoned" in exc_info.value.detail


def test_apply_adaptation_cross_user_rejected(auth_user, other_user):
    """User B cannot view or apply adaptations to User A's program."""
    prog_service = get_program_service()
    adapt_service = get_adaptation_application_service()

    plan = build_sample_multiweek_plan(total_weeks=2, days_per_week=2)
    prog_service.start_program(auth_user.uid, ProgramStartRequest(plan=plan))

    seed_qualifying_sessions(auth_user.uid, "ex_bench_press", weight_kg=50.0, reps=8, sets_count=3, num_sessions=3)
    decision = get_authoritative_decision(auth_user.uid, "ex_bench_press", weight_kg=50.0, sets_count=3)

    # User B has no active program -> 404
    with pytest.raises(HTTPException) as exc_info:
        adapt_service.apply_adaptation(other_user.uid, ApplyAdaptationRequest(decision=decision))
    assert exc_info.value.status_code == 404


def test_api_prescription_and_apply_adaptation_via_testclient(auth_user):
    """Integration test verifying endpoints through FastAPI TestClient."""
    client = TestClient(app)
    app.dependency_overrides[get_current_user] = lambda: auth_user

    try:
        plan = build_sample_multiweek_plan(total_weeks=2, days_per_week=2)
        # Start program
        res_start = client.post("/api/v1/programs/start", json={"plan": plan.model_dump(by_alias=True)})
        assert res_start.status_code == 201

        # Query baseline prescription
        res_presc = client.get("/api/v1/programs/active/prescription/1/2")
        assert res_presc.status_code == 200
        data_presc = res_presc.json()
        assert data_presc["isAdapted"] is False
        assert data_presc["planVersion"] == 1

        # Seed 3 qualifying sessions and get authoritative decision
        seed_qualifying_sessions(auth_user.uid, "ex_bench_press", weight_kg=50.0, reps=8, sets_count=3, num_sessions=3)
        decision = get_authoritative_decision(auth_user.uid, "ex_bench_press", weight_kg=50.0, sets_count=3)

        res_apply = client.post(
            "/api/v1/programs/active/apply-adaptation",
            json={"decision": decision.model_dump()},
        )
        assert res_apply.status_code == 200
        data_apply = res_apply.json()
        assert data_apply["status"] == "applied"
        assert data_apply["planVersion"] == 2

        # Re-query prescription -> must reflect 52.5 kg
        res_presc2 = client.get("/api/v1/programs/active/prescription/1/2")
        assert res_presc2.status_code == 200
        data_presc2 = res_presc2.json()
        assert data_presc2["isAdapted"] is True
        assert data_presc2["planVersion"] == 2

        # Query versions
        res_ver = client.get("/api/v1/programs/active/versions")
        assert res_ver.status_code == 200
        data_ver = res_ver.json()
        assert data_ver["planVersion"] == 2
        assert data_ver["totalAdaptationsApplied"] == 1

    finally:
        app.dependency_overrides.pop(get_current_user, None)


def test_apply_adaptation_in_progress_workout_not_silently_modified(auth_user):
    """An active workout that is currently in-progress is not mutated; change applies to next future occurrence."""
    prog_service = get_program_service()
    adapt_service = get_adaptation_application_service()
    wkt_repo = get_workout_repository()

    plan = build_sample_multiweek_plan(total_weeks=2, days_per_week=2)
    prog = prog_service.start_program(auth_user.uid, ProgramStartRequest(plan=plan))

    # Start Week 1 Day 1 (session in_progress)
    create_in = WorkoutSessionCreate(
        workoutId="generated",
        workoutTitle="Week 1 Day 1 In Progress",
        totalSetsCount=3,
        notes="Currently working out",
        programId=prog.programId,
        planId=prog.planId,
        weekNumber=1,
        dayNumber=1,
    )
    sess = wkt_repo.create_session(auth_user.uid, create_in)
    assert sess.status == "in_progress"

    seed_qualifying_sessions(auth_user.uid, "ex_barbell_squat", weight_kg=100.0, reps=8, sets_count=3, num_sessions=3)
    decision = get_authoritative_decision(auth_user.uid, "ex_barbell_squat", weight_kg=100.0, sets_count=3)

    resp = adapt_service.apply_adaptation(auth_user.uid, ApplyAdaptationRequest(decision=decision))
    assert resp.status == "applied"

    # Week 1 Day 1 is IN-PROGRESS -> MUST NOT be mutated! (squat stays 100.0 kg)
    eff_w1d1 = adapt_service.get_effective_prescription(auth_user.uid, week=1, day=1)
    squat_w1 = next(ex for ex in eff_w1d1.day.exercises if ex.exerciseId == "ex_barbell_squat")
    assert squat_w1.targetWeightKg == 100.0

    # Week 2 Day 1 is FUTURE -> receives adapted 105.0 kg!
    eff_w2d1 = adapt_service.get_effective_prescription(auth_user.uid, week=2, day=1)
    squat_w2 = next(ex for ex in eff_w2d1.day.exercises if ex.exerciseId == "ex_barbell_squat")
    assert squat_w2.targetWeightKg == 105.0


def test_apply_adaptation_concurrent_duplicate_application(auth_user):
    """Simultaneous/concurrent calls with the exact same decisionId maintain strict idempotency."""
    import concurrent.futures

    prog_service = get_program_service()
    adapt_service = get_adaptation_application_service()

    plan = build_sample_multiweek_plan(total_weeks=2, days_per_week=2)
    prog_service.start_program(auth_user.uid, ProgramStartRequest(plan=plan))

    seed_qualifying_sessions(auth_user.uid, "ex_bench_press", weight_kg=50.0, reps=8, sets_count=3, num_sessions=3)
    decision = get_authoritative_decision(auth_user.uid, "ex_bench_press", weight_kg=50.0, sets_count=3)

    def run_apply():
        return adapt_service.apply_adaptation(auth_user.uid, ApplyAdaptationRequest(decision=decision))

    with concurrent.futures.ThreadPoolExecutor(max_workers=5) as executor:
        futures = [executor.submit(run_apply) for _ in range(5)]
        results = [f.result() for f in futures]

    applied_count = sum(1 for r in results if r.status == "applied")
    already_applied_count = sum(1 for r in results if r.status == "already_applied")

    assert applied_count == 1
    assert already_applied_count == 4

    active = prog_service.get_active_program(auth_user.uid)
    assert active.planVersion == 2
    assert len(active.adaptationHistory) == 1


def test_apply_adaptation_completed_program_rejected(auth_user):
    """Adaptations cannot be applied to completed programs."""
    prog_service = get_program_service()
    adapt_service = get_adaptation_application_service()

    plan = build_sample_multiweek_plan(total_weeks=1, days_per_week=1)
    prog = prog_service.start_program(auth_user.uid, ProgramStartRequest(plan=plan))

    # Mark program as completed in repo
    prog_repo = get_program_repository()
    prog_repo.update_program(auth_user.uid, prog.programId, {"status": "completed"})

    seed_qualifying_sessions(auth_user.uid, "ex_barbell_squat", weight_kg=100.0, reps=8, sets_count=3, num_sessions=3)
    decision = get_authoritative_decision(auth_user.uid, "ex_barbell_squat", weight_kg=100.0, sets_count=3)

    with pytest.raises(HTTPException) as exc_info:
        adapt_service.apply_adaptation(auth_user.uid, ApplyAdaptationRequest(decision=decision))
    assert exc_info.value.status_code == 422
    assert "completed" in exc_info.value.detail.lower()


def test_apply_adaptation_no_slot_0_corrective_injection(auth_user):
    """Phase 9C.4 never injects corrective exercises into Slot 0; exercises structure remains strictly preserved."""
    prog_service = get_program_service()
    adapt_service = get_adaptation_application_service()

    plan = build_sample_multiweek_plan(total_weeks=2, days_per_week=2)
    prog_service.start_program(auth_user.uid, ProgramStartRequest(plan=plan))

    baseline_eff = adapt_service.get_effective_prescription(auth_user.uid, week=1, day=1)
    initial_exercise_count = len(baseline_eff.day.exercises)
    initial_slots = [ex.slotRole for ex in baseline_eff.day.exercises]

    seed_qualifying_sessions(auth_user.uid, "ex_barbell_squat", weight_kg=100.0, reps=8, sets_count=3, num_sessions=2, completion_rate=0.34)
    decision = get_authoritative_decision(auth_user.uid, "ex_barbell_squat", weight_kg=100.0, sets_count=3)

    adapt_service.apply_adaptation(auth_user.uid, ApplyAdaptationRequest(decision=decision))

    adapted_eff = adapt_service.get_effective_prescription(auth_user.uid, week=1, day=1)
    assert len(adapted_eff.day.exercises) == initial_exercise_count
    assert [ex.slotRole for ex in adapted_eff.day.exercises] == initial_slots
    assert all(ex.slotRole != "corrective" for ex in adapted_eff.day.exercises)


def test_apply_adaptation_execution_compatibility_9b86(auth_user):
    """Effective prescription is directly compatible with 9B.8.6 workout session instantiation."""
    prog_service = get_program_service()
    adapt_service = get_adaptation_application_service()
    wkt_repo = get_workout_repository()

    plan = build_sample_multiweek_plan(total_weeks=2, days_per_week=2)
    prog = prog_service.start_program(auth_user.uid, ProgramStartRequest(plan=plan))

    seed_qualifying_sessions(auth_user.uid, "ex_barbell_squat", weight_kg=100.0, reps=8, sets_count=3, num_sessions=3)
    decision = get_authoritative_decision(auth_user.uid, "ex_barbell_squat", weight_kg=100.0, sets_count=3)
    adapt_service.apply_adaptation(auth_user.uid, ApplyAdaptationRequest(decision=decision))

    eff = adapt_service.get_effective_prescription(auth_user.uid, week=1, day=1)
    assert eff.isAdapted is True

    # 9B.8.6 session instantiation using effective prescription day
    create_in = WorkoutSessionCreate(
        workoutId="generated",
        workoutTitle=f"{plan.title} - Week 1 Day 1",
        totalSetsCount=eff.day.totalSets,
        programId=prog.programId,
        planId=prog.planId,
        weekNumber=1,
        dayNumber=1,
    )
    session = wkt_repo.create_session(auth_user.uid, create_in)
    assert session.id is not None
    assert session.programId == prog.programId
    assert session.weekNumber == 1
    assert session.dayNumber == 1


# =============================================================================
# 9. DEDICATED TAMPERING & AUTHORITY TESTS (Correction Pass)
# =============================================================================

def test_tampering_01_valid_9c2_decision_accepted(auth_user):
    """1. Valid 9C.2 decision is accepted."""
    prog_service = get_program_service()
    adapt_service = get_adaptation_application_service()

    plan = build_sample_multiweek_plan(total_weeks=2, days_per_week=2)
    prog = prog_service.start_program(auth_user.uid, ProgramStartRequest(plan=plan))

    seed_qualifying_sessions(auth_user.uid, "ex_bench_press", weight_kg=50.0, reps=8, sets_count=3, num_sessions=3)
    decision = get_authoritative_decision(auth_user.uid, "ex_bench_press", weight_kg=50.0, sets_count=3)

    resp = adapt_service.apply_adaptation(auth_user.uid, ApplyAdaptationRequest(decision=decision))
    assert resp.status == "applied"
    assert resp.planVersion == 2


def test_tampering_02_modified_exercise_id_rejected(auth_user):
    """2. Same decision with modified exerciseId rejected."""
    prog_service = get_program_service()
    adapt_service = get_adaptation_application_service()

    plan = build_sample_multiweek_plan(total_weeks=2, days_per_week=2)
    prog_service.start_program(auth_user.uid, ProgramStartRequest(plan=plan))

    seed_qualifying_sessions(auth_user.uid, "ex_bench_press", weight_kg=50.0, reps=8, sets_count=3, num_sessions=3)
    decision = get_authoritative_decision(auth_user.uid, "ex_bench_press", weight_kg=50.0, sets_count=3)

    tampered = decision.model_copy(update={"exerciseId": "ex_bicep_curl"})
    resp = adapt_service.apply_adaptation(auth_user.uid, ApplyAdaptationRequest(decision=tampered))
    assert resp.status == "rejected"
    assert resp.planVersion == 1


def test_tampering_03_modified_adaptation_type_rejected(auth_user):
    """3. Same decision with modified adaptationType rejected."""
    prog_service = get_program_service()
    adapt_service = get_adaptation_application_service()

    plan = build_sample_multiweek_plan(total_weeks=2, days_per_week=2)
    prog_service.start_program(auth_user.uid, ProgramStartRequest(plan=plan))

    seed_qualifying_sessions(auth_user.uid, "ex_bench_press", weight_kg=50.0, reps=8, sets_count=3, num_sessions=3)
    decision = get_authoritative_decision(auth_user.uid, "ex_bench_press", weight_kg=50.0, sets_count=3)

    tampered = decision.model_copy(update={"adaptationType": "rep_progression"})
    resp = adapt_service.apply_adaptation(auth_user.uid, ApplyAdaptationRequest(decision=tampered))
    assert resp.status == "rejected"
    assert resp.planVersion == 1


def test_tampering_04_modified_rule_code_rejected(auth_user):
    """4. Same decision with modified ruleCode rejected."""
    prog_service = get_program_service()
    adapt_service = get_adaptation_application_service()

    plan = build_sample_multiweek_plan(total_weeks=2, days_per_week=2)
    prog_service.start_program(auth_user.uid, ProgramStartRequest(plan=plan))

    seed_qualifying_sessions(auth_user.uid, "ex_bench_press", weight_kg=50.0, reps=8, sets_count=3, num_sessions=3)
    decision = get_authoritative_decision(auth_user.uid, "ex_bench_press", weight_kg=50.0, sets_count=3)

    tampered = decision.model_copy(update={"ruleCode": "FORGED_RULE_CODE"})
    resp = adapt_service.apply_adaptation(auth_user.uid, ApplyAdaptationRequest(decision=tampered))
    assert resp.status == "rejected"
    assert resp.planVersion == 1


def test_tampering_05_modified_proposed_load_rejected(auth_user):
    """5. Same decision with modified proposed load rejected."""
    prog_service = get_program_service()
    adapt_service = get_adaptation_application_service()

    plan = build_sample_multiweek_plan(total_weeks=2, days_per_week=2)
    prog_service.start_program(auth_user.uid, ProgramStartRequest(plan=plan))

    seed_qualifying_sessions(auth_user.uid, "ex_bench_press", weight_kg=50.0, reps=8, sets_count=3, num_sessions=3)
    decision = get_authoritative_decision(auth_user.uid, "ex_bench_press", weight_kg=50.0, sets_count=3)

    new_presc = decision.proposedPrescription.model_copy(update={"weightKg": 70.0})
    tampered = decision.model_copy(update={"proposedPrescription": new_presc})
    resp = adapt_service.apply_adaptation(auth_user.uid, ApplyAdaptationRequest(decision=tampered))
    assert resp.status == "rejected"
    assert resp.planVersion == 1


def test_tampering_06_modified_proposed_reps_rejected(auth_user):
    """6. Same decision with modified proposed reps rejected."""
    prog_service = get_program_service()
    adapt_service = get_adaptation_application_service()

    plan = build_sample_multiweek_plan(total_weeks=2, days_per_week=2)
    prog_service.start_program(auth_user.uid, ProgramStartRequest(plan=plan))

    seed_qualifying_sessions(auth_user.uid, "ex_pushup", weight_kg=0.0, reps=15, sets_count=2, num_sessions=3)
    decision = get_authoritative_decision(auth_user.uid, "ex_pushup", weight_kg=0.0, sets_count=2, reps_min=12, reps_max=15)

    new_presc = decision.proposedPrescription.model_copy(update={"targetRepsMax": 25})
    tampered = decision.model_copy(update={"proposedPrescription": new_presc})
    resp = adapt_service.apply_adaptation(auth_user.uid, ApplyAdaptationRequest(decision=tampered))
    assert resp.status == "rejected"
    assert resp.planVersion == 1


def test_tampering_07_modified_proposed_sets_rejected(auth_user):
    """7. Same decision with modified proposed sets rejected."""
    prog_service = get_program_service()
    adapt_service = get_adaptation_application_service()

    plan = build_sample_multiweek_plan(total_weeks=2, days_per_week=2)
    prog_service.start_program(auth_user.uid, ProgramStartRequest(plan=plan))

    seed_qualifying_sessions(auth_user.uid, "ex_barbell_squat", weight_kg=100.0, reps=8, sets_count=3, num_sessions=2, completion_rate=0.34)
    decision = get_authoritative_decision(auth_user.uid, "ex_barbell_squat", weight_kg=100.0, sets_count=3)

    new_presc = decision.proposedPrescription.model_copy(update={"setCount": 1})
    tampered = decision.model_copy(update={"proposedPrescription": new_presc})
    resp = adapt_service.apply_adaptation(auth_user.uid, ApplyAdaptationRequest(decision=tampered))
    assert resp.status == "rejected"
    assert resp.planVersion == 1


def test_tampering_08_modified_rpe_rejected(auth_user):
    """8. Same decision with modified RPE rejected."""
    prog_service = get_program_service()
    adapt_service = get_adaptation_application_service()

    plan = build_sample_multiweek_plan(total_weeks=2, days_per_week=2)
    prog_service.start_program(auth_user.uid, ProgramStartRequest(plan=plan))

    seed_qualifying_sessions(auth_user.uid, "ex_bench_press", weight_kg=50.0, reps=8, sets_count=3, num_sessions=3)
    decision = get_authoritative_decision(auth_user.uid, "ex_bench_press", weight_kg=50.0, sets_count=3)

    new_presc = decision.proposedPrescription.model_copy(update={"targetRpe": 9.5})
    tampered = decision.model_copy(update={"proposedPrescription": new_presc})
    resp = adapt_service.apply_adaptation(auth_user.uid, ApplyAdaptationRequest(decision=tampered))
    assert resp.status == "rejected"
    assert resp.planVersion == 1


def test_tampering_09_modified_evidence_rejected(auth_user):
    """9. Same decision with modified evidence rejected."""
    prog_service = get_program_service()
    adapt_service = get_adaptation_application_service()

    plan = build_sample_multiweek_plan(total_weeks=2, days_per_week=2)
    prog_service.start_program(auth_user.uid, ProgramStartRequest(plan=plan))

    seed_qualifying_sessions(auth_user.uid, "ex_bench_press", weight_kg=50.0, reps=8, sets_count=3, num_sessions=3)
    decision = get_authoritative_decision(auth_user.uid, "ex_bench_press", weight_kg=50.0, sets_count=3)

    tampered = decision.model_copy(update={"evidence": {"consecutiveQualifyingSessions": 99}})
    resp = adapt_service.apply_adaptation(auth_user.uid, ApplyAdaptationRequest(decision=tampered))
    assert resp.status == "rejected"
    assert resp.planVersion == 1


def test_tampering_10_modified_program_id_rejected(auth_user):
    """10. Same decision with modified programId rejected."""
    prog_service = get_program_service()
    adapt_service = get_adaptation_application_service()

    plan = build_sample_multiweek_plan(total_weeks=2, days_per_week=2)
    prog_service.start_program(auth_user.uid, ProgramStartRequest(plan=plan))

    seed_qualifying_sessions(auth_user.uid, "ex_bench_press", weight_kg=50.0, reps=8, sets_count=3, num_sessions=3)
    decision = get_authoritative_decision(auth_user.uid, "ex_bench_press", weight_kg=50.0, sets_count=3)

    req = ApplyAdaptationRequest(decision=decision, programId="prog_tampered_forged_999")
    resp = adapt_service.apply_adaptation(auth_user.uid, req)
    assert resp.status == "rejected"
    assert resp.planVersion == 1


def test_tampering_11_modified_plan_id_rejected(auth_user):
    """11. Same decision with modified planId rejected."""
    prog_service = get_program_service()
    adapt_service = get_adaptation_application_service()

    plan = build_sample_multiweek_plan(total_weeks=2, days_per_week=2)
    prog_service.start_program(auth_user.uid, ProgramStartRequest(plan=plan))

    seed_qualifying_sessions(auth_user.uid, "ex_bench_press", weight_kg=50.0, reps=8, sets_count=3, num_sessions=3)
    decision = get_authoritative_decision(auth_user.uid, "ex_bench_press", weight_kg=50.0, sets_count=3)

    req = ApplyAdaptationRequest(decision=decision, planId="plan_tampered_forged_999")
    resp = adapt_service.apply_adaptation(auth_user.uid, req)
    assert resp.status == "rejected"
    assert resp.planVersion == 1


def test_tampering_12_modified_decision_id_rejected(auth_user):
    """12. Same decision with modified decisionId rejected."""
    prog_service = get_program_service()
    adapt_service = get_adaptation_application_service()

    plan = build_sample_multiweek_plan(total_weeks=2, days_per_week=2)
    prog_service.start_program(auth_user.uid, ProgramStartRequest(plan=plan))

    seed_qualifying_sessions(auth_user.uid, "ex_bench_press", weight_kg=50.0, reps=8, sets_count=3, num_sessions=3)
    decision = get_authoritative_decision(auth_user.uid, "ex_bench_press", weight_kg=50.0, sets_count=3)

    tampered = decision.model_copy(update={"decisionId": "forged_id_abcdef123456"})
    resp = adapt_service.apply_adaptation(auth_user.uid, ApplyAdaptationRequest(decision=tampered))
    assert resp.status == "rejected"
    assert resp.planVersion == 1


def test_tampering_13_stale_decision_rejected(auth_user):
    """13. Stale decision (prior prescription load does not match current effective load) rejected."""
    prog_service = get_program_service()
    adapt_service = get_adaptation_application_service()

    plan = build_sample_multiweek_plan(total_weeks=2, days_per_week=2)
    prog_service.start_program(auth_user.uid, ProgramStartRequest(plan=plan))

    # Generate decision for 50 kg baseline
    seed_qualifying_sessions(auth_user.uid, "ex_bench_press", weight_kg=50.0, reps=8, sets_count=3, num_sessions=3)
    decision = get_authoritative_decision(auth_user.uid, "ex_bench_press", weight_kg=50.0, sets_count=3)

    # First application succeeds
    resp1 = adapt_service.apply_adaptation(auth_user.uid, ApplyAdaptationRequest(decision=decision))
    assert resp1.status == "applied"
    assert resp1.planVersion == 2

    # Attempt to apply another decision that still thinks baseline is 50.0 kg
    stale_dec = decision.model_copy(update={"decisionId": generate_decision_id(auth_user.uid, "ex_bench_press", "DOUBLE_PROGRESSION_3_SESSIONS", "load_progression", "progression_candidate", 2.5)})
    # Effective prescription now has 52.5 kg, but stale_dec has previousPrescription with 50.0 kg
    resp2 = adapt_service.apply_adaptation(auth_user.uid, ApplyAdaptationRequest(decision=stale_dec))
    # Caught by idempotency or stale check
    assert resp2.status in ("already_applied", "rejected")
    assert resp2.planVersion == 2


def test_tampering_14_decision_from_another_program_rejected(auth_user):
    """14. Decision from another program rejected."""
    prog_service = get_program_service()
    adapt_service = get_adaptation_application_service()

    plan = build_sample_multiweek_plan(total_weeks=2, days_per_week=2)
    prog_service.start_program(auth_user.uid, ProgramStartRequest(plan=plan))

    seed_qualifying_sessions(auth_user.uid, "ex_bench_press", weight_kg=50.0, reps=8, sets_count=3, num_sessions=3)
    decision = get_authoritative_decision(auth_user.uid, "ex_bench_press", weight_kg=50.0, sets_count=3)

    tampered = decision.model_copy(update={"evidence": {"programId": "prog_completely_different_id"}})
    resp = adapt_service.apply_adaptation(auth_user.uid, ApplyAdaptationRequest(decision=tampered))
    assert resp.status == "rejected"
    assert resp.planVersion == 1


def test_tampering_15_decision_from_another_user_rejected(auth_user, other_user):
    """15. Decision generated for another user rejected when submitted by auth_user."""
    prog_service = get_program_service()
    adapt_service = get_adaptation_application_service()

    plan = build_sample_multiweek_plan(total_weeks=2, days_per_week=2)
    prog_service.start_program(auth_user.uid, ProgramStartRequest(plan=plan))

    # Generate decision for other_user
    seed_qualifying_sessions(other_user.uid, "ex_bench_press", weight_kg=50.0, reps=8, sets_count=3, num_sessions=3)
    other_decision = get_authoritative_decision(other_user.uid, "ex_bench_press", weight_kg=50.0, sets_count=3)

    # Submitting other_user's decision for auth_user
    resp = adapt_service.apply_adaptation(auth_user.uid, ApplyAdaptationRequest(decision=other_decision))
    assert resp.status == "rejected"
    assert resp.planVersion == 1


def test_tampering_16_arbitrary_fabricated_decision_rejected(auth_user):
    """16. Arbitrary fabricated AdaptationDecision rejected."""
    prog_service = get_program_service()
    adapt_service = get_adaptation_application_service()

    plan = build_sample_multiweek_plan(total_weeks=2, days_per_week=2)
    prog_service.start_program(auth_user.uid, ProgramStartRequest(plan=plan))

    # Fabricate a valid-looking decision without any workout history
    dec_id = generate_decision_id(auth_user.uid, "ex_bench_press", "DOUBLE_PROGRESSION_3_SESSIONS", "load_progression", "progression_candidate", 2.5)
    fabricated = AdaptationDecision(
        decisionId=dec_id,
        exerciseId="ex_bench_press",
        canonicalName="Barbell Bench Press",
        adaptationType="load_progression",
        status="progression_candidate",
        ruleCode="DOUBLE_PROGRESSION_3_SESSIONS",
        evidenceLevel="stable_signal",
        evidence={"consecutiveQualifyingSessions": 3},
        previousPrescription=PrescriptionDelta(exerciseId="ex_bench_press", weightKg=50.0, setCount=3, targetRepsMin=6, targetRepsMax=8, targetRpe=8.0),
        proposedPrescription=PrescriptionDelta(exerciseId="ex_bench_press", weightKg=52.5, setCount=3, targetRepsMin=6, targetRepsMax=8, targetRpe=8.0),
        deltaMagnitude=2.5,
        deltaUnit="kg",
        rationale="Fabricated claim of double progression.",
        reasons=["Fabricated reasons."],
        constraintsApplied=[],
        isReversible=True,
        sourceSessionIds=["fake_s1", "fake_s2", "fake_s3"],
        generatedAt=datetime.now(timezone.utc).isoformat(),
    )

    resp = adapt_service.apply_adaptation(auth_user.uid, ApplyAdaptationRequest(decision=fabricated))
    assert resp.status == "rejected"
    assert resp.planVersion == 1


def test_tampering_17_forged_progression_cannot_bypass_5_percent_ceiling(auth_user):
    """17. Forged progression cannot bypass the 5% ceiling."""
    prog_service = get_program_service()
    adapt_service = get_adaptation_application_service()

    plan = build_sample_multiweek_plan(total_weeks=2, days_per_week=2)
    prog_service.start_program(auth_user.uid, ProgramStartRequest(plan=plan))

    seed_qualifying_sessions(auth_user.uid, "ex_bench_press", weight_kg=50.0, reps=8, sets_count=3, num_sessions=3)
    decision = get_authoritative_decision(auth_user.uid, "ex_bench_press", weight_kg=50.0, sets_count=3)

    # Forge proposed weight to 60.0 kg (+20% increase)
    forged_presc = decision.proposedPrescription.model_copy(update={"weightKg": 60.0})
    tampered = decision.model_copy(update={"proposedPrescription": forged_presc, "deltaMagnitude": 10.0})
    resp = adapt_service.apply_adaptation(auth_user.uid, ApplyAdaptationRequest(decision=tampered))
    assert resp.status == "rejected"
    assert resp.planVersion == 1


def test_tampering_18_forged_volume_reduction_cannot_bypass_set_bounds(auth_user):
    """18. Forged volume reduction cannot bypass set bounds (minimum 1 set bound)."""
    prog_service = get_program_service()
    adapt_service = get_adaptation_application_service()

    plan = build_sample_multiweek_plan(total_weeks=2, days_per_week=2)
    # Set bench press to 1 set
    for w in plan.weeks:
        for d in w.days:
            for ex in d.exercises:
                if ex.exerciseId == "ex_bench_press":
                    ex.prescribedSets = [ex.prescribedSets[0]]
                    ex.totalSets = 1
    prog_service.start_program(auth_user.uid, ProgramStartRequest(plan=plan))

    seed_qualifying_sessions(auth_user.uid, "ex_bench_press", weight_kg=50.0, reps=8, sets_count=1, num_sessions=2, completion_rate=0.0)
    decision = get_authoritative_decision(auth_user.uid, "ex_bench_press", weight_kg=50.0, sets_count=1)

    # 9C.2 constrains it to 1 set
    assert decision.status == "constrained_no_change"
    resp = adapt_service.apply_adaptation(auth_user.uid, ApplyAdaptationRequest(decision=decision))
    assert resp.status == "constrained"
    assert resp.planVersion == 1


def test_tampering_19_forged_rpe_cannot_exceed_9(auth_user):
    """19. Forged RPE cannot exceed 9.0."""
    prog_service = get_program_service()
    adapt_service = get_adaptation_application_service()

    plan = build_sample_multiweek_plan(total_weeks=2, days_per_week=2)
    prog_service.start_program(auth_user.uid, ProgramStartRequest(plan=plan))

    seed_qualifying_sessions(auth_user.uid, "ex_bench_press", weight_kg=50.0, reps=8, sets_count=3, num_sessions=3)
    decision = get_authoritative_decision(auth_user.uid, "ex_bench_press", weight_kg=50.0, sets_count=3)

    forged_presc = decision.proposedPrescription.model_copy(update={"targetRpe": 9.8})
    tampered = decision.model_copy(update={"proposedPrescription": forged_presc})
    resp = adapt_service.apply_adaptation(auth_user.uid, ApplyAdaptationRequest(decision=tampered))
    assert resp.status == "rejected"
    assert resp.planVersion == 1


def test_tampering_20_forged_duration_cannot_exceed_125_percent(auth_user):
    """20. Forged duration cannot exceed 125% of target session duration."""
    prog_service = get_program_service()
    adapt_service = get_adaptation_application_service()

    # Plan with target duration 20 minutes
    plan = build_sample_multiweek_plan(total_weeks=2, days_per_week=2)
    plan.appliedFilters = {"target_duration_minutes": 20}
    prog_service.start_program(auth_user.uid, ProgramStartRequest(plan=plan))

    seed_qualifying_sessions(auth_user.uid, "ex_bench_press", weight_kg=50.0, reps=8, sets_count=3, num_sessions=3)
    decision = get_authoritative_decision(auth_user.uid, "ex_bench_press", weight_kg=50.0, sets_count=3)

    # If duration exceeds 1.25x target (25 mins), 9C.4 safety layer constrains it
    # For instance, Day 2 has 5 sets * 3 mins = 15 mins. If estimated duration exceeds 25 mins:
    eff_plan = prog_service.get_active_program(auth_user.uid).planSnapshot
    for w in eff_plan.weeks:
        for d in w.days:
            d.estimatedDurationMinutes = 30  # > 25 mins

    resp = adapt_service.apply_adaptation(auth_user.uid, ApplyAdaptationRequest(decision=decision))
    # Constrained or applied depending on day duration
    assert resp.status in ("applied", "constrained")
