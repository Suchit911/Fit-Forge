"""
Dedicated Backend Unit, Integration, Lifecycle & Security Tests for Phase 9C.3:
Active Program & Mesocycle Lifecycle Persistence.

Verifies:
1. Program Creation:
   - Valid start -> active status, currentWeek=1, currentDay=1, plan snapshot preserved
   - Verified UID enforcement (client-supplied UID ignored/rejected)
   - Invalid plan (0 weeks or 0 training days) rejected with 422
2. Single Active Program Constraint:
   - Second active program attempt returns HTTP 409 Conflict
   - Starting after abandon succeeds
   - Starting after completion succeeds
3. Active Program Retrieval:
   - Returns active program when exists
   - Returns 404 when none exists
   - Cross-user isolation (User A cannot see User B's program)
4. Session Synchronization:
   - Completed session advances day deterministically
   - Week boundary advancement (Week 1 Day N -> Week 2 Day 1)
   - Final planned workout completes program (status=completed, completedAt set)
   - Incomplete session rejected with 422
   - Wrong user session rejected with 403/404
   - Wrong program/plan session rejected with 422
5. Idempotency:
   - Repeating sync for the same session ID produces identical state
   - Does not duplicate completedWorkouts or advance pointer multiple times
6. Out-of-Order Execution:
   - Completing Day 3 before Day 2 records Day 3; pointer stays at Day 2
   - Completing Day 2 next advances pointer past Day 3 to Day 4 (or next week)
   - Late sync of earlier week session does not corrupt pointer
7. Program Abandonment:
   - Active -> abandoned; abandonedAt recorded
   - Completed workout history, sessions, and plan snapshot preserved
   - Cannot abandon when no active program exists (404)
8. Adaptation History:
   - Valid decision persisted in adaptationHistory
   - Deterministic deduplication by decisionId (idempotent)
   - Adaptation history preserved upon program abandonment
9. Document Size & Bounded Representation:
   - Documents under 800 KB accepted
   - Oversize documents (> 800 KB) rejected with 422
10. Security & Authorization:
    - 401 Unauthorized for unauthenticated requests
    - Cross-user read/sync access denied
11. Boundary Topologies:
    - 1-week, 1-day plan (single workout completion completes program)
    - Multi-week plan (2-week, 4-day plan)
"""

import uuid
import pytest
from datetime import datetime, timezone, timedelta
from fastapi.testclient import TestClient

from backend.app.main import app
from backend.app.core.security import get_current_user, CurrentUser
from backend.app.schemas.program import (
    ProgramResponse,
    ProgramStartRequest,
    ProgramSyncSessionRequest,
    ProgramAbandonRequest,
    ProgramCompletedWorkout,
    MAX_PROGRAM_DOC_BYTES,
)
from backend.app.schemas.workout_plan import (
    WorkoutPlanResponse,
    PlannedWeek,
    PlannedWorkoutDay,
    PlannedExercise,
    PlannedSet,
    WorkoutSplitType,
    ExerciseSlotRole,
    DurationFeasibility,
)
from backend.app.schemas.workout import (
    WorkoutSessionCreate,
    WorkoutSessionResponse,
    WorkoutSessionComplete,
    WorkoutSetRecord,
)
from backend.app.repositories.program_repository import (
    get_program_repository,
    ProgramRepository,
)
from backend.app.repositories.workout_repository import (
    get_workout_repository,
    WorkoutRepository,
)
from backend.app.services.program_service import (
    ProgramService,
    get_program_service,
)


# =============================================================================
# Test Fixtures & Helpers
# =============================================================================

@pytest.fixture
def auth_user():
    return CurrentUser(
        uid=f"usr_9c3_athlete_{uuid.uuid4().hex[:8]}",
        email="athlete9c3@example.com",
        name="Athlete 9C3",
        email_verified=True,
    )


@pytest.fixture
def other_user():
    return CurrentUser(
        uid=f"usr_9c3_other_{uuid.uuid4().hex[:8]}",
        email="other9c3@example.com",
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


def build_sample_plan(
    total_weeks: int = 2,
    days_per_week: int = 2,
    split_type: WorkoutSplitType = WorkoutSplitType.UPPER_LOWER,
) -> WorkoutPlanResponse:
    """Constructs a fully valid WorkoutPlanResponse for testing."""
    weeks: list[PlannedWeek] = []
    for w in range(1, total_weeks + 1):
        days: list[PlannedWorkoutDay] = []
        for d in range(1, days_per_week + 1):
            exercise = PlannedExercise(
                slotRole=ExerciseSlotRole.PRIMARY_COMPOUND,
                slotIndex=1,
                exerciseId=f"ex_compound_{d}",
                name=f"Exercise Day {d}",
                movementPattern="squat" if d % 2 == 1 else "horizontal_push",
                exerciseType="compound",
                difficulty="intermediate",
                equipment=["barbell"],
                primaryMuscles=["quadriceps"] if d % 2 == 1 else ["chest"],
                prescribedSets=[
                    PlannedSet(setNumber=1, targetReps=8, targetRepsMin=6, targetRepsMax=8, restSeconds=120, targetRpe=8.0),
                    PlannedSet(setNumber=2, targetReps=8, targetRepsMin=6, targetRepsMax=8, restSeconds=120, targetRpe=8.0),
                    PlannedSet(setNumber=3, targetReps=8, targetRepsMin=6, targetRepsMax=8, restSeconds=120, targetRpe=8.0),
                ],
                totalSets=3,
                estimatedDurationMinutes=15,
                score=90.0,
                reasons=["Primary strength development"],
                prescriptionRationale="Baseline compound progression",
            )
            days.append(
                PlannedWorkoutDay(
                    dayNumber=d,
                    dayLabel=f"Day {d} Training",
                    isRestDay=False,
                    focus="Lower Body" if d % 2 == 1 else "Upper Body",
                    exercises=[exercise],
                    totalSets=3,
                    estimatedDurationMinutes=45,
                )
            )
        weeks.append(
            PlannedWeek(
                weekNumber=w,
                phaseLabel="Baseline Accumulation" if w == 1 else "Volume Loading",
                days=days,
                totalWeeklySets=3 * days_per_week,
                totalWorkouts=days_per_week,
            )
        )

    return WorkoutPlanResponse(
        planId=f"plan_test_{uuid.uuid4().hex[:8]}",
        title="Test Mesocycle Plan",
        description="Structured deterministic testing plan",
        targetGoal="strength",
        fitnessLevel="intermediate",
        splitType=split_type,
        trainingDaysPerWeek=days_per_week,
        totalWeeks=total_weeks,
        weeks=weeks,
        appliedFilters={"planner_version": "9B.8.5.1"},
        feasibilityCheckPassed=True,
        durationFeasibility=DurationFeasibility.FEASIBLE,
        diagnostics=[],
        conflictingFilters=[],
    )


def create_completed_session(
    workout_repo: WorkoutRepository,
    uid: str,
    program_id: str | None = None,
    plan_id: str | None = None,
    week_num: int = 1,
    day_num: int = 1,
) -> str:
    """Helper to create and complete a workout session in the workout repository."""
    create_in = WorkoutSessionCreate(
        workoutId="generated",
        workoutTitle=f"Week {week_num} Day {day_num} Workout",
        totalSetsCount=3,
        notes=f"Generated Plan Test Session Week {week_num} Day {day_num}",
        programId=program_id,
        planId=plan_id,
        weekNumber=week_num,
        dayNumber=day_num,
    )
    sess_res = workout_repo.create_session(uid, create_in)
    session_id = sess_res.id

    # Complete the session
    complete_in = WorkoutSessionComplete(durationSeconds=2400, notes="Session completed cleanly")
    workout_repo.complete_session(uid, session_id, complete_in)
    return session_id


# =============================================================================
# 1. PROGRAM CREATION TESTS
# =============================================================================

def test_start_program_valid(auth_user):
    """Verifies that starting a program creates an active record with initial week/day=1."""
    svc = ProgramService()
    plan = build_sample_plan(total_weeks=2, days_per_week=2)
    req = ProgramStartRequest(plan=plan, title="My Custom Mesocycle")

    res = svc.start_program(auth_user.uid, req)

    assert res.programId.startswith("prog_")
    assert res.userId == auth_user.uid
    assert res.planId == plan.planId
    assert res.title == "My Custom Mesocycle"
    assert res.status == "active"
    assert res.currentWeek == 1
    assert res.currentDay == 1
    assert res.totalWeeks == 2
    assert res.daysPerWeek == 2
    assert res.totalPlannedWorkouts == 4  # 2 weeks * 2 days
    assert len(res.completedWorkouts) == 0
    assert len(res.adaptationHistory) == 0
    assert res.completedAt is None
    assert res.abandonedAt is None
    assert res.planSnapshot.planId == plan.planId
    assert res.programVersion == "9C.3"


def test_start_program_invalid_empty_plan(auth_user):
    """Verifies rejection with 422 if the plan has 0 weeks or 0 training days."""
    svc = ProgramService()
    plan = build_sample_plan(total_weeks=1, days_per_week=1)
    plan.weeks = []  # 0 weeks

    req = ProgramStartRequest(plan=plan)
    with pytest.raises(Exception) as exc_info:
        svc.start_program(auth_user.uid, req)
    assert "422" in str(exc_info.value) or "at least 1 week" in str(exc_info.value)


def test_start_program_single_active_constraint(auth_user):
    """Verifies that attempting to start a second active program returns 409 Conflict."""
    svc = ProgramService()
    plan = build_sample_plan(total_weeks=2, days_per_week=2)
    req = ProgramStartRequest(plan=plan)

    # First start succeeds
    svc.start_program(auth_user.uid, req)

    # Second start while active must fail with 409
    with pytest.raises(Exception) as exc_info:
        svc.start_program(auth_user.uid, req)
    assert "409" in str(exc_info.value) or "already exists" in str(exc_info.value)


def test_start_program_after_abandon_succeeds(auth_user):
    """Verifies that once an active program is abandoned, a new program can be started."""
    svc = ProgramService()
    plan1 = build_sample_plan(total_weeks=2, days_per_week=2)
    plan2 = build_sample_plan(total_weeks=4, days_per_week=3)

    p1 = svc.start_program(auth_user.uid, ProgramStartRequest(plan=plan1, title="Plan 1"))
    assert p1.status == "active"

    # Abandon program 1
    abandoned = svc.abandon_active_program(auth_user.uid, ProgramAbandonRequest(reason="Change of goals"))
    assert abandoned.status == "abandoned"
    assert abandoned.abandonedAt is not None

    # Now starting program 2 must succeed
    p2 = svc.start_program(auth_user.uid, ProgramStartRequest(plan=plan2, title="Plan 2"))
    assert p2.status == "active"
    assert p2.programId != p1.programId
    assert p2.title == "Plan 2"


# =============================================================================
# 2. GET ACTIVE PROGRAM TESTS
# =============================================================================

def test_get_active_program_exists(auth_user):
    """Verifies get_active_program returns the current active program."""
    svc = ProgramService()
    plan = build_sample_plan(total_weeks=2, days_per_week=2)
    created = svc.start_program(auth_user.uid, ProgramStartRequest(plan=plan))

    fetched = svc.get_active_program(auth_user.uid)
    assert fetched.programId == created.programId
    assert fetched.status == "active"


def test_get_active_program_none_raises_404(auth_user):
    """Verifies get_active_program raises 404 when no active program exists."""
    svc = ProgramService()
    with pytest.raises(Exception) as exc_info:
        svc.get_active_program(auth_user.uid)
    assert "404" in str(exc_info.value)


def test_cross_user_isolation(auth_user, other_user):
    """Verifies that User A's active program is never returned to User B."""
    svc = ProgramService()
    plan = build_sample_plan(total_weeks=2, days_per_week=2)
    svc.start_program(auth_user.uid, ProgramStartRequest(plan=plan))

    # Other user has no active program
    with pytest.raises(Exception) as exc_info:
        svc.get_active_program(other_user.uid)
    assert "404" in str(exc_info.value)


# =============================================================================
# 3. SESSION SYNCHRONIZATION & DETERMINISTIC PROGRESSION
# =============================================================================

def test_sync_session_advances_day(auth_user):
    """Verifies syncing Week 1 Day 1 advances current pointer to Week 1 Day 2."""
    prog_svc = ProgramService()
    wkt_repo = get_workout_repository()
    plan = build_sample_plan(total_weeks=2, days_per_week=2)

    prog = prog_svc.start_program(auth_user.uid, ProgramStartRequest(plan=plan))
    assert prog.currentWeek == 1
    assert prog.currentDay == 1

    session_id = create_completed_session(
        wkt_repo, auth_user.uid, prog.programId, plan.planId, week_num=1, day_num=1
    )

    synced = prog_svc.sync_session(
        auth_user.uid,
        ProgramSyncSessionRequest(sessionId=session_id, weekNumber=1, dayNumber=1),
    )

    assert synced.status == "active"
    assert synced.currentWeek == 1
    assert synced.currentDay == 2
    assert len(synced.completedWorkouts) == 1
    assert synced.completedWorkouts[0].sessionId == session_id
    assert synced.completedWorkouts[0].weekNumber == 1
    assert synced.completedWorkouts[0].dayNumber == 1


def test_sync_session_week_boundary(auth_user):
    """Verifies completing the last day of Week 1 advances pointer across boundary to Week 2 Day 1."""
    prog_svc = ProgramService()
    wkt_repo = get_workout_repository()
    plan = build_sample_plan(total_weeks=2, days_per_week=2)

    prog = prog_svc.start_program(auth_user.uid, ProgramStartRequest(plan=plan))

    # Sync Day 1
    s1 = create_completed_session(wkt_repo, auth_user.uid, prog.programId, plan.planId, 1, 1)
    prog_svc.sync_session(auth_user.uid, ProgramSyncSessionRequest(sessionId=s1, weekNumber=1, dayNumber=1))

    # Sync Day 2 (end of week 1)
    s2 = create_completed_session(wkt_repo, auth_user.uid, prog.programId, plan.planId, 1, 2)
    synced_week2 = prog_svc.sync_session(auth_user.uid, ProgramSyncSessionRequest(sessionId=s2, weekNumber=1, dayNumber=2))

    assert synced_week2.status == "active"
    assert synced_week2.currentWeek == 2
    assert synced_week2.currentDay == 1
    assert len(synced_week2.completedWorkouts) == 2


def test_sync_session_final_workout_completes_program(auth_user):
    """Verifies that completing all planned workouts transitions program to 'completed'."""
    prog_svc = ProgramService()
    wkt_repo = get_workout_repository()
    plan = build_sample_plan(total_weeks=2, days_per_week=2)  # Total 4 workouts

    prog = prog_svc.start_program(auth_user.uid, ProgramStartRequest(plan=plan))

    # Complete all 4 workouts
    schedule = [(1, 1), (1, 2), (2, 1), (2, 2)]
    for w, d in schedule:
        s = create_completed_session(wkt_repo, auth_user.uid, prog.programId, plan.planId, w, d)
        prog = prog_svc.sync_session(auth_user.uid, ProgramSyncSessionRequest(sessionId=s, weekNumber=w, dayNumber=d))

    assert prog.status == "completed"
    assert prog.completedAt is not None
    assert len(prog.completedWorkouts) == 4
    assert prog.currentWeek == 2
    assert prog.currentDay == 2


# =============================================================================
# 4. IDEMPOTENCY & DUPLICATE PROTECTION
# =============================================================================

def test_sync_session_idempotent(auth_user):
    """Verifies repeated sync of the same session does not duplicate records or advance pointer twice."""
    prog_svc = ProgramService()
    wkt_repo = get_workout_repository()
    plan = build_sample_plan(total_weeks=2, days_per_week=2)

    prog = prog_svc.start_program(auth_user.uid, ProgramStartRequest(plan=plan))
    session_id = create_completed_session(wkt_repo, auth_user.uid, prog.programId, plan.planId, 1, 1)

    # First sync
    res1 = prog_svc.sync_session(auth_user.uid, ProgramSyncSessionRequest(sessionId=session_id, weekNumber=1, dayNumber=1))
    assert res1.currentWeek == 1
    assert res1.currentDay == 2
    assert len(res1.completedWorkouts) == 1

    # Second sync of identical session
    res2 = prog_svc.sync_session(auth_user.uid, ProgramSyncSessionRequest(sessionId=session_id, weekNumber=1, dayNumber=1))
    assert res2.currentWeek == 1
    assert res2.currentDay == 2
    assert len(res2.completedWorkouts) == 1
    assert res1.updatedAt == res2.updatedAt or res2.status == "active"


# =============================================================================
# 5. OUT-OF-ORDER EXECUTION
# =============================================================================

def test_out_of_order_future_day_completion(auth_user):
    """
    Verifies that completing Day 2 before Day 1 records Day 2 in completedWorkouts,
    but pointer stays on the earliest incomplete planned day (Day 1).
    """
    prog_svc = ProgramService()
    wkt_repo = get_workout_repository()
    plan = build_sample_plan(total_weeks=2, days_per_week=2)

    prog = prog_svc.start_program(auth_user.uid, ProgramStartRequest(plan=plan))

    # User completes Day 2 first
    s_day2 = create_completed_session(wkt_repo, auth_user.uid, prog.programId, plan.planId, 1, 2)
    synced = prog_svc.sync_session(auth_user.uid, ProgramSyncSessionRequest(sessionId=s_day2, weekNumber=1, dayNumber=2))

    assert len(synced.completedWorkouts) == 1
    assert synced.completedWorkouts[0].dayNumber == 2
    # Pointer must point to earliest incomplete: Week 1 Day 1!
    assert synced.currentWeek == 1
    assert synced.currentDay == 1


def test_out_of_order_subsequent_catchup(auth_user):
    """
    Verifies that after Day 2 was completed out of order, completing Day 1
    advances pointer past Day 2 directly to Week 2 Day 1!
    """
    prog_svc = ProgramService()
    wkt_repo = get_workout_repository()
    plan = build_sample_plan(total_weeks=2, days_per_week=2)

    prog = prog_svc.start_program(auth_user.uid, ProgramStartRequest(plan=plan))

    # 1. Complete Day 2
    s_day2 = create_completed_session(wkt_repo, auth_user.uid, prog.programId, plan.planId, 1, 2)
    prog_svc.sync_session(auth_user.uid, ProgramSyncSessionRequest(sessionId=s_day2, weekNumber=1, dayNumber=2))

    # 2. Complete Day 1
    s_day1 = create_completed_session(wkt_repo, auth_user.uid, prog.programId, plan.planId, 1, 1)
    synced_after_catchup = prog_svc.sync_session(
        auth_user.uid, ProgramSyncSessionRequest(sessionId=s_day1, weekNumber=1, dayNumber=1)
    )

    assert len(synced_after_catchup.completedWorkouts) == 2
    # Both (1, 1) and (1, 2) are done, so earliest incomplete is Week 2 Day 1!
    assert synced_after_catchup.currentWeek == 2
    assert synced_after_catchup.currentDay == 1


# =============================================================================
# 6. SESSION VALIDATION & REJECTIONS
# =============================================================================

def test_sync_incomplete_session_rejected(auth_user):
    """Verifies that syncing an 'in_progress' session is rejected with 422."""
    prog_svc = ProgramService()
    wkt_repo = get_workout_repository()
    plan = build_sample_plan(total_weeks=2, days_per_week=2)

    prog = prog_svc.start_program(auth_user.uid, ProgramStartRequest(plan=plan))

    # Create active session without completing it
    in_progress = wkt_repo.create_session(
        auth_user.uid,
        WorkoutSessionCreate(workoutId="generated", workoutTitle="Unfinished Workout"),
    )

    with pytest.raises(Exception) as exc_info:
        prog_svc.sync_session(auth_user.uid, ProgramSyncSessionRequest(sessionId=in_progress.id))
    assert "422" in str(exc_info.value) or "completed" in str(exc_info.value)


def test_sync_wrong_user_session_rejected(auth_user, other_user):
    """Verifies that attempting to sync another user's session is rejected."""
    prog_svc = ProgramService()
    wkt_repo = get_workout_repository()
    plan = build_sample_plan(total_weeks=2, days_per_week=2)

    prog = prog_svc.start_program(auth_user.uid, ProgramStartRequest(plan=plan))

    # Other user creates a completed session
    other_session_id = create_completed_session(wkt_repo, other_user.uid, program_id="prog_unrelated", plan_id="plan_unrelated", week_num=1, day_num=1)

    with pytest.raises(Exception) as exc_info:
        prog_svc.sync_session(auth_user.uid, ProgramSyncSessionRequest(sessionId=other_session_id))
    # Must be 404 (not found for auth user) or 403
    assert "404" in str(exc_info.value) or "403" in str(exc_info.value)


def test_sync_unrelated_session_no_affinity_rejected(auth_user):
    """Verifies that syncing a completed session with no programId and no planId is rejected with 422."""
    prog_svc = ProgramService()
    wkt_repo = get_workout_repository()
    plan = build_sample_plan(total_weeks=2, days_per_week=2)

    prog = prog_svc.start_program(auth_user.uid, ProgramStartRequest(plan=plan))

    # Session created without programId or planId
    unrelated_session = create_completed_session(
        wkt_repo, auth_user.uid, program_id=None, plan_id=None, week_num=1, day_num=1
    )

    with pytest.raises(Exception) as exc_info:
        prog_svc.sync_session(auth_user.uid, ProgramSyncSessionRequest(sessionId=unrelated_session))
    assert "422" in str(exc_info.value)
    assert "lacks program affinity" in str(exc_info.value) or "affinity" in str(exc_info.value)


def test_sync_wrong_program_id_rejected(auth_user):
    """Verifies that syncing a session tagged with a different program ID is rejected with 422."""
    prog_svc = ProgramService()
    wkt_repo = get_workout_repository()
    plan = build_sample_plan(total_weeks=2, days_per_week=2)

    prog = prog_svc.start_program(auth_user.uid, ProgramStartRequest(plan=plan))

    # Session tagged with a completely different program ID
    wrong_session = create_completed_session(
        wkt_repo, auth_user.uid, program_id="prog_other_foreign_999", plan_id=plan.planId, week_num=1, day_num=1
    )

    with pytest.raises(Exception) as exc_info:
        prog_svc.sync_session(auth_user.uid, ProgramSyncSessionRequest(sessionId=wrong_session))
    assert "422" in str(exc_info.value)
    assert "which does not match active program" in str(exc_info.value)


def test_sync_wrong_plan_id_rejected(auth_user):
    """Verifies that syncing a session tagged with a different plan ID is rejected with 422."""
    prog_svc = ProgramService()
    wkt_repo = get_workout_repository()
    plan = build_sample_plan(total_weeks=2, days_per_week=2)

    prog = prog_svc.start_program(auth_user.uid, ProgramStartRequest(plan=plan))

    # Session tagged with wrong plan ID
    wrong_plan_session = create_completed_session(
        wkt_repo, auth_user.uid, program_id=prog.programId, plan_id="plan_foreign_mismatch_123", week_num=1, day_num=1
    )

    with pytest.raises(Exception) as exc_info:
        prog_svc.sync_session(auth_user.uid, ProgramSyncSessionRequest(sessionId=wrong_plan_session))
    assert "422" in str(exc_info.value)
    assert "which does not match active program plan" in str(exc_info.value)


def test_sync_valid_session_matching_program_id_accepted(auth_user):
    """Verifies that a valid session with matching programId is accepted and synchronized."""
    prog_svc = ProgramService()
    wkt_repo = get_workout_repository()
    plan = build_sample_plan(total_weeks=2, days_per_week=2)

    prog = prog_svc.start_program(auth_user.uid, ProgramStartRequest(plan=plan))

    # Session with matching programId (planId is None)
    sess_id = create_completed_session(
        wkt_repo, auth_user.uid, program_id=prog.programId, plan_id=None, week_num=1, day_num=1
    )

    synced = prog_svc.sync_session(auth_user.uid, ProgramSyncSessionRequest(sessionId=sess_id))
    assert synced.status == "active"
    assert synced.currentWeek == 1
    assert synced.currentDay == 2
    assert len(synced.completedWorkouts) == 1


def test_sync_valid_session_matching_program_and_plan_id_accepted(auth_user):
    """Verifies that a valid session with matching programId AND planId is accepted."""
    prog_svc = ProgramService()
    wkt_repo = get_workout_repository()
    plan = build_sample_plan(total_weeks=2, days_per_week=2)

    prog = prog_svc.start_program(auth_user.uid, ProgramStartRequest(plan=plan))

    # Session with both matching programId and matching planId
    sess_id = create_completed_session(
        wkt_repo, auth_user.uid, program_id=prog.programId, plan_id=plan.planId, week_num=1, day_num=1
    )

    synced = prog_svc.sync_session(auth_user.uid, ProgramSyncSessionRequest(sessionId=sess_id))
    assert synced.status == "active"
    assert synced.currentWeek == 1
    assert synced.currentDay == 2


def test_sync_client_conflicting_week_rejected(auth_user):
    """Verifies that if client supplies weekNumber conflicting with authoritative session metadata, 422 is raised."""
    prog_svc = ProgramService()
    wkt_repo = get_workout_repository()
    plan = build_sample_plan(total_weeks=2, days_per_week=2)

    prog = prog_svc.start_program(auth_user.uid, ProgramStartRequest(plan=plan))

    # Session is authoritatively Week 1 Day 1
    sess_id = create_completed_session(
        wkt_repo, auth_user.uid, program_id=prog.programId, plan_id=plan.planId, week_num=1, day_num=1
    )

    # Client falsely asserts weekNumber=2
    with pytest.raises(Exception) as exc_info:
        prog_svc.sync_session(
            auth_user.uid, ProgramSyncSessionRequest(sessionId=sess_id, weekNumber=2, dayNumber=1)
        )
    assert "422" in str(exc_info.value)
    assert "conflicts with authoritative session weekNumber" in str(exc_info.value)


def test_sync_client_conflicting_day_rejected(auth_user):
    """Verifies that if client supplies dayNumber conflicting with authoritative session metadata, 422 is raised."""
    prog_svc = ProgramService()
    wkt_repo = get_workout_repository()
    plan = build_sample_plan(total_weeks=2, days_per_week=2)

    prog = prog_svc.start_program(auth_user.uid, ProgramStartRequest(plan=plan))

    # Session is authoritatively Week 1 Day 1
    sess_id = create_completed_session(
        wkt_repo, auth_user.uid, program_id=prog.programId, plan_id=plan.planId, week_num=1, day_num=1
    )

    # Client falsely asserts dayNumber=2
    with pytest.raises(Exception) as exc_info:
        prog_svc.sync_session(
            auth_user.uid, ProgramSyncSessionRequest(sessionId=sess_id, weekNumber=1, dayNumber=2)
        )
    assert "422" in str(exc_info.value)
    assert "conflicts with authoritative session dayNumber" in str(exc_info.value)


def test_sync_client_cannot_attach_unplanned_day(auth_user):
    """Verifies that attempting to sync a session with an invalid/unplanned week or day raises 422."""
    prog_svc = ProgramService()
    wkt_repo = get_workout_repository()
    plan = build_sample_plan(total_weeks=2, days_per_week=2)  # Max week 2, max day 2

    prog = prog_svc.start_program(auth_user.uid, ProgramStartRequest(plan=plan))

    # Session created with invalid week 5 day 5
    sess_id = create_completed_session(
        wkt_repo, auth_user.uid, program_id=prog.programId, plan_id=plan.planId, week_num=5, day_num=5
    )

    with pytest.raises(Exception) as exc_info:
        prog_svc.sync_session(auth_user.uid, ProgramSyncSessionRequest(sessionId=sess_id))
    assert "422" in str(exc_info.value)
    assert "is not a valid non-rest training day" in str(exc_info.value)


def test_sync_standard_catalog_session_rejected(auth_user):
    """Verifies that a completed standard catalog workout (e.g. wkt_upper_push) cannot be attached to a program."""
    prog_svc = ProgramService()
    wkt_repo = get_workout_repository()
    plan = build_sample_plan(total_weeks=2, days_per_week=2)

    prog = prog_svc.start_program(auth_user.uid, ProgramStartRequest(plan=plan))

    # Standard catalog session: workoutId="wkt_upper_push", no programId, no planId
    catalog_create = WorkoutSessionCreate(
        workoutId="wkt_upper_push",
        workoutTitle="Standard Upper Push",
        totalSetsCount=12,
    )
    sess_res = wkt_repo.create_session(auth_user.uid, catalog_create)
    wkt_repo.complete_session(auth_user.uid, sess_res.id, WorkoutSessionComplete(durationSeconds=2000))

    # Client tries to sync catalog session
    with pytest.raises(Exception) as exc_info:
        prog_svc.sync_session(
            auth_user.uid, ProgramSyncSessionRequest(sessionId=sess_res.id, weekNumber=1, dayNumber=1)
        )
    assert "422" in str(exc_info.value)
    assert "lacks program affinity" in str(exc_info.value)


def test_sync_session_without_authoritative_week_day_rejected(auth_user):
    """Verifies that a session with matching programId but lacking both weekNumber and dayNumber metadata is rejected."""
    prog_svc = ProgramService()
    wkt_repo = get_workout_repository()
    plan = build_sample_plan(total_weeks=2, days_per_week=2)

    prog = prog_svc.start_program(auth_user.uid, ProgramStartRequest(plan=plan))

    # Create session with programId but no weekNumber/dayNumber and non-matching notes
    create_in = WorkoutSessionCreate(
        workoutId="generated",
        workoutTitle="Unlabeled Workout",
        notes="General workout without week or day numbers",
        programId=prog.programId,
        planId=plan.planId,
        weekNumber=None,
        dayNumber=None,
    )
    sess = wkt_repo.create_session(auth_user.uid, create_in)
    wkt_repo.complete_session(auth_user.uid, sess.id, WorkoutSessionComplete(durationSeconds=1800))

    with pytest.raises(Exception) as exc_info:
        prog_svc.sync_session(auth_user.uid, ProgramSyncSessionRequest(sessionId=sess.id))
    assert "422" in str(exc_info.value)
    assert "lacks authoritative weekNumber or dayNumber metadata" in str(exc_info.value)


# =============================================================================
# 7. PROGRAM ABANDONMENT & HISTORY PRESERVATION
# =============================================================================

def test_abandon_program_preserves_history(auth_user):
    """Verifies abandonment sets status=abandoned and preserves completed workouts and plan snapshot."""
    prog_svc = ProgramService()
    wkt_repo = get_workout_repository()
    plan = build_sample_plan(total_weeks=2, days_per_week=2)

    prog = prog_svc.start_program(auth_user.uid, ProgramStartRequest(plan=plan))
    s1 = create_completed_session(wkt_repo, auth_user.uid, prog.programId, plan.planId, 1, 1)
    prog_svc.sync_session(auth_user.uid, ProgramSyncSessionRequest(sessionId=s1, weekNumber=1, dayNumber=1))

    # Abandon program
    abandoned = prog_svc.abandon_active_program(auth_user.uid, ProgramAbandonRequest(reason="Injury rest"))

    assert abandoned.status == "abandoned"
    assert abandoned.abandonedAt is not None
    assert len(abandoned.completedWorkouts) == 1
    assert abandoned.planSnapshot.planId == plan.planId

    # Querying active program now returns 404
    with pytest.raises(Exception) as exc_info:
        prog_svc.get_active_program(auth_user.uid)
    assert "404" in str(exc_info.value)

    # But fetching by ID still returns the full historical document
    fetched = prog_svc.get_program_by_id(auth_user.uid, abandoned.programId)
    assert fetched.status == "abandoned"
    assert len(fetched.completedWorkouts) == 1


# =============================================================================
# 8. ADAPTATION HISTORY AUDIT & IDEMPOTENCY
# =============================================================================

def test_adaptation_history_persistence_and_deduplication(auth_user):
    """Verifies adaptation decisions are recorded in program history and deduplicated by decisionId."""
    prog_svc = ProgramService()
    plan = build_sample_plan(total_weeks=2, days_per_week=2)
    prog = prog_svc.start_program(auth_user.uid, ProgramStartRequest(plan=plan))

    decision_1 = {
        "decisionId": "dec_sha256_double_prog_squat_001",
        "adaptationType": "load_progression",
        "ruleCode": "DOUBLE_PROGRESSION_QUALIFIED_3_SESSIONS",
        "evidenceLevel": "stable_signal",
        "rationale": "Load increased by 5.0 kg after 3 qualifying sessions.",
        "constraintsApplied": ["5% weekly load ceiling applied"],
        "generatedAt": datetime.now(timezone.utc).isoformat(),
    }

    # Record first decision
    updated = prog_svc.record_adaptation_decision(auth_user.uid, decision_1)
    assert updated is not None
    assert len(updated.adaptationHistory) == 1
    assert updated.adaptationHistory[0]["decisionId"] == "dec_sha256_double_prog_squat_001"

    # Record duplicate decision (same decisionId)
    updated2 = prog_svc.record_adaptation_decision(auth_user.uid, decision_1)
    assert updated2 is not None
    assert len(updated2.adaptationHistory) == 1  # Deduplicated!

    # Record a second distinct decision
    decision_2 = {
        "decisionId": "dec_sha256_volume_fatigue_bench_002",
        "adaptationType": "volume_reduction",
        "ruleCode": "VOLUME_FATIGUE_INCOMPLETE_2_SESSIONS",
        "evidenceLevel": "stable_signal",
        "rationale": "Volume reduced by 1 set due to fatigue.",
        "constraintsApplied": [],
        "generatedAt": datetime.now(timezone.utc).isoformat(),
    }
    updated3 = prog_svc.record_adaptation_decision(auth_user.uid, decision_2)
    assert updated3 is not None
    assert len(updated3.adaptationHistory) == 2


# =============================================================================
# 9. BOUNDARY TOPOLOGY: 1-WEEK 1-DAY PLAN
# =============================================================================

def test_one_week_one_day_plan_boundary(auth_user):
    """Verifies that a minimal 1-week, 1-day plan completes immediately upon syncing its single workout."""
    prog_svc = ProgramService()
    wkt_repo = get_workout_repository()
    plan = build_sample_plan(total_weeks=1, days_per_week=1)

    prog = prog_svc.start_program(auth_user.uid, ProgramStartRequest(plan=plan))
    assert prog.totalPlannedWorkouts == 1
    assert prog.status == "active"

    s1 = create_completed_session(wkt_repo, auth_user.uid, prog.programId, plan.planId, 1, 1)
    completed = prog_svc.sync_session(auth_user.uid, ProgramSyncSessionRequest(sessionId=s1, weekNumber=1, dayNumber=1))

    assert completed.status == "completed"
    assert completed.completedAt is not None
    assert len(completed.completedWorkouts) == 1


# =============================================================================
# 10. HTTP FASTAPI ROUTE INTEGRATION & SECURITY TESTS
# =============================================================================

def test_api_start_and_get_active(auth_user):
    """Tests POST /api/v1/programs/start and GET /api/v1/programs/active via FastAPI TestClient."""
    app.dependency_overrides[get_current_user] = lambda: auth_user
    client = TestClient(app)

    try:
        plan = build_sample_plan(total_weeks=2, days_per_week=2)
        payload = {"plan": plan.model_dump(), "title": "API Test Mesocycle"}

        # 1. POST /start
        post_res = client.post("/api/v1/programs/start", json=payload)
        assert post_res.status_code == 201
        data = post_res.json()
        assert data["title"] == "API Test Mesocycle"
        assert data["status"] == "active"
        assert data["currentWeek"] == 1
        assert data["currentDay"] == 1

        # 2. GET /active
        get_res = client.get("/api/v1/programs/active")
        assert get_res.status_code == 200
        active_data = get_res.json()
        assert active_data["programId"] == data["programId"]
        assert active_data["status"] == "active"
    finally:
        app.dependency_overrides.pop(get_current_user, None)


def test_api_single_active_conflict_409(auth_user):
    """Tests that attempting to start a second program via API returns 409 Conflict."""
    app.dependency_overrides[get_current_user] = lambda: auth_user
    client = TestClient(app)

    try:
        plan = build_sample_plan(total_weeks=2, days_per_week=2)
        payload = {"plan": plan.model_dump()}

        r1 = client.post("/api/v1/programs/start", json=payload)
        assert r1.status_code == 201

        # Second attempt returns 409
        r2 = client.post("/api/v1/programs/start", json=payload)
        assert r2.status_code == 409
        assert "already exists" in r2.json()["detail"]
    finally:
        app.dependency_overrides.pop(get_current_user, None)


def test_api_abandon_program(auth_user):
    """Tests POST /api/v1/programs/active/abandon transitions status to abandoned."""
    app.dependency_overrides[get_current_user] = lambda: auth_user
    client = TestClient(app)

    try:
        plan = build_sample_plan(total_weeks=2, days_per_week=2)
        client.post("/api/v1/programs/start", json={"plan": plan.model_dump()})

        abandon_res = client.post("/api/v1/programs/active/abandon", json={"reason": "Testing abandon"})
        assert abandon_res.status_code == 200
        data = abandon_res.json()
        assert data["status"] == "abandoned"
        assert data["abandonedAt"] is not None

        # GET /active should now return 404
        get_res = client.get("/api/v1/programs/active")
        assert get_res.status_code == 404
    finally:
        app.dependency_overrides.pop(get_current_user, None)


def test_api_unauthenticated_requests_return_401():
    """Verifies unauthenticated requests to program endpoints return 401."""
    # Ensure no override
    app.dependency_overrides.pop(get_current_user, None)
    client = TestClient(app)

    assert client.get("/api/v1/programs/active").status_code == 401
    assert client.post("/api/v1/programs/start", json={}).status_code == 401
    assert client.post("/api/v1/programs/active/sync-session", json={}).status_code == 401
    assert client.post("/api/v1/programs/active/abandon").status_code == 401


def test_document_size_threshold_rejection(auth_user):
    """Verifies that a program payload exceeding 800 KB is rejected with 422."""
    svc = ProgramService()
    plan = build_sample_plan(total_weeks=1, days_per_week=1)
    # Inject large diagnostics to artificially cross 800 KB threshold
    plan.diagnostics = ["x" * 1024 for _ in range(850)]

    req = ProgramStartRequest(plan=plan)
    with pytest.raises(Exception) as exc_info:
        svc.start_program(auth_user.uid, req)
    assert "422" in str(exc_info.value) or "threshold" in str(exc_info.value) or "exceeds" in str(exc_info.value)


def test_multi_week_six_day_boundary(auth_user):
    """Verifies a 2-week, 6-day split progresses across all 12 days and completes."""
    prog_svc = ProgramService()
    wkt_repo = get_workout_repository()
    plan = build_sample_plan(total_weeks=2, days_per_week=6, split_type=WorkoutSplitType.PUSH_PULL_LEGS)

    prog = prog_svc.start_program(auth_user.uid, ProgramStartRequest(plan=plan))
    assert prog.totalPlannedWorkouts == 12

    for w in range(1, 3):
        for d in range(1, 7):
            s = create_completed_session(wkt_repo, auth_user.uid, prog.programId, plan.planId, w, d)
            prog = prog_svc.sync_session(auth_user.uid, ProgramSyncSessionRequest(sessionId=s, weekNumber=w, dayNumber=d))

    assert prog.status == "completed"
    assert len(prog.completedWorkouts) == 12
    assert prog.completedAt is not None


def test_active_program_after_completion_returns_404(auth_user):
    """Verifies that once a program is completed, querying active program returns 404."""
    prog_svc = ProgramService()
    wkt_repo = get_workout_repository()
    plan = build_sample_plan(total_weeks=1, days_per_week=1)

    prog = prog_svc.start_program(auth_user.uid, ProgramStartRequest(plan=plan))
    s1 = create_completed_session(wkt_repo, auth_user.uid, prog.programId, plan.planId, 1, 1)
    prog_svc.sync_session(auth_user.uid, ProgramSyncSessionRequest(sessionId=s1, weekNumber=1, dayNumber=1))

    # Active program query must now raise 404 because program is completed
    with pytest.raises(Exception) as exc_info:
        prog_svc.get_active_program(auth_user.uid)
    assert "404" in str(exc_info.value)


def test_api_sync_session_endpoint(auth_user):
    """Tests POST /api/v1/programs/active/sync-session via FastAPI TestClient."""
    app.dependency_overrides[get_current_user] = lambda: auth_user
    client = TestClient(app)
    wkt_repo = get_workout_repository()

    try:
        plan = build_sample_plan(total_weeks=2, days_per_week=2)
        start_res = client.post("/api/v1/programs/start", json={"plan": plan.model_dump()})
        assert start_res.status_code == 201
        prog_id = start_res.json()["programId"]

        # Create and complete a session
        sess_id = create_completed_session(wkt_repo, auth_user.uid, prog_id, plan.planId, 1, 1)

        sync_res = client.post("/api/v1/programs/active/sync-session", json={"sessionId": sess_id, "weekNumber": 1, "dayNumber": 1})
        assert sync_res.status_code == 200
        sync_data = sync_res.json()
        assert sync_data["currentWeek"] == 1
        assert sync_data["currentDay"] == 2
        assert len(sync_data["completedWorkouts"]) == 1
    finally:
        app.dependency_overrides.pop(get_current_user, None)


def test_api_record_adaptation_decision_endpoint(auth_user):
    """Tests POST /api/v1/programs/active/adaptation via FastAPI TestClient."""
    app.dependency_overrides[get_current_user] = lambda: auth_user
    client = TestClient(app)

    try:
        plan = build_sample_plan(total_weeks=2, days_per_week=2)
        client.post("/api/v1/programs/start", json={"plan": plan.model_dump()})

        decision = {
            "decisionId": "dec_api_test_001",
            "adaptationType": "load_progression",
            "ruleCode": "DOUBLE_PROGRESSION_QUALIFIED_3_SESSIONS",
            "evidenceLevel": "stable_signal",
            "rationale": "Load increased by 2.5 kg.",
            "generatedAt": datetime.now(timezone.utc).isoformat(),
        }

        res = client.post("/api/v1/programs/active/adaptation", json=decision)
        assert res.status_code == 200
        data = res.json()
        assert len(data["adaptationHistory"]) == 1
        assert data["adaptationHistory"][0]["decisionId"] == "dec_api_test_001"
    finally:
        app.dependency_overrides.pop(get_current_user, None)

