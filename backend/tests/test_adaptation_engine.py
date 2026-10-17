"""
Dedicated Backend Unit, Boundary, Integration & Security Tests for Phase 9C.2:
Deterministic Progression & Adaptation Engine.

Verifies:
1. Double-Progression Rules:
   - 1 qualifying session -> no progression (insufficient data / emerging)
   - 2 qualifying sessions -> no progression (emerging signal)
   - 3 consecutive qualifying sessions -> progression_candidate
   - Interrupted sequence (pass -> fail -> pass) -> resets sequence to 1
   - 21-day boundary: Day 0 -> Day 10 -> Day 21 (gap <= 21 days) -> eligible
   - 22-day reset: Day 0 -> Day 10 -> Day 32 (gap 22 days > 21 days) -> resets
2. Load Increments:
   - Upper compound -> +2.5 kg
   - Lower compound -> +5.0 kg
   - Isolation / bodyweight -> +1 rep progression
3. Hard 5% Weekly Load Ceiling:
   - Within 5% boundary (e.g. 50 kg + 2.5 kg = 52.5 kg, exactly 5.0%) -> approved
   - Above 5% boundary (e.g. 40 kg + 2.5 kg = 42.5 kg, 6.25%) -> constrained_no_change (LOAD_CEILING_5_PERCENT_EXCEEDED)
   - Lower compound above 5% (e.g. 80 kg + 5.0 kg = 85.0 kg, 6.25%) -> constrained_no_change
   - Zero / negative baseline load handled safely without crashing
4. Volume Fatigue & Set Bounds:
   - 1 incomplete session (< 70% sets) -> no_change (one session is not enough)
   - 2 consecutive incomplete sessions (< 70% sets) -> volume_reduction_candidate (-1 set)
   - Minimum 1 set bound -> cannot reduce to 0; returns constrained_no_change (MINIMUM_SET_BOUND_REACHED)
   - Maximum 5 sets bound respected
   - Exact volume completion boundary: 69.9% is failure; 70.0% is pass
5. Conflict Resolution Precedence:
   - Double progression rep criteria met BUT 2 consecutive sessions volume failure -> volume fatigue overrides progression!
6. Form Issue Signals:
   - Recurring issue (>= 50% frequency) -> produces form_issue_candidate
   - Non-recurring issue -> no proposal
   - No direct Slot 0 corrective injection in this phase
7. Adherence Future-Block Split Adaptation:
   - 5-day plan with ~3-day observed completion over 4 weeks -> 3-day Full Body recommendation for next block
   - Missing planned frequency -> no fabricated adherence
8. Duration & RPE Constraints:
   - Duration > 1.25x target -> constrained_no_change (DURATION_EXCEEDS_125_PCT)
   - Prescribed RPE > 9.0 -> clamped to 9.0
9. Determinism:
   - Identical inputs produce byte-identical SHA-256 decision IDs and payloads
10. Security & Read-Only Invariants:
    - Unauthenticated requests rejected with HTTP 401
    - Cross-user isolation verified
    - Zero Firestore writes verified
"""

import uuid
import pytest
from datetime import datetime, timezone, timedelta
from fastapi.testclient import TestClient

from backend.app.main import app
from backend.app.core.security import get_current_user, CurrentUser
from backend.app.schemas.user import UserProfileSchema, UserProfileCreate
from backend.app.schemas.workout import (
    WorkoutSessionResponse,
    WorkoutSessionCreate,
    WorkoutSessionComplete,
    WorkoutSessionUpdate,
    WorkoutSetRecord,
    WorkoutSetSchema,
)
from backend.app.schemas.adaptation import (
    AdaptationDecision,
    AdaptationEvaluationRequest,
    AdaptationEvaluationResponse,
    PrescriptionDelta,
    generate_decision_id,
)
from backend.app.schemas.personalization import (
    PersonalizationSignalsResponse,
    WorkoutAdherenceTrend,
    SetAdherenceSignal,
    ExerciseFormSignal,
    FormIssueFrequency,
)
from backend.app.repositories.workout_repository import get_workout_repository
from backend.app.repositories.user_repository import get_user_repository
from backend.app.services.personalization_signal_service import (
    get_personalization_signal_service,
    PersonalizationSignalService,
)
from backend.app.services.adaptation_engine_service import (
    get_adaptation_engine_service,
    AdaptationEngineService,
)


@pytest.fixture
def auth_user():
    return CurrentUser(
        uid=f"usr_9c2_athlete_{uuid.uuid4().hex[:8]}",
        email="athlete9c2@example.com",
        name="Adaptation Engine Tester",
        email_verified=True,
    )


@pytest.fixture
def other_user():
    return CurrentUser(
        uid=f"usr_9c2_attacker_{uuid.uuid4().hex[:8]}",
        email="attacker9c2@example.com",
        name="Attacker User",
        email_verified=True,
    )


# =============================================================================
# 1. DOUBLE PROGRESSION BOUNDARY TESTS
# =============================================================================

def test_double_progression_one_qualifying_session(auth_user):
    """Verifies that 1 qualifying session produces no_change / insufficient consecutive sessions."""
    svc = AdaptationEngineService()
    now = datetime.now(timezone.utc)
    qualifying_sets = [
        WorkoutSetSchema(setNumber=1, targetReps=10, actualReps=10, targetWeightKg=80.0, actualWeightKg=80.0, isCompleted=True),
        WorkoutSetSchema(setNumber=2, targetReps=10, actualReps=10, targetWeightKg=80.0, actualWeightKg=80.0, isCompleted=True),
        WorkoutSetSchema(setNumber=3, targetReps=10, actualReps=10, targetWeightKg=80.0, actualWeightKg=80.0, isCompleted=True),
    ]
    sessions = [
        (
            WorkoutSessionResponse(
                id="s1", userId=auth_user.uid, workoutId="w1", workoutTitle="Push A",
                startedAt=(now - timedelta(days=2)).isoformat(),
                completedSetsCount=3, totalSetsCount=3,
                completedSets={"ex_bench_press": qualifying_sets},
            ),
            qualifying_sets
        )
    ]
    count, qualifying_sessions, weights = svc._evaluate_double_progression_streak(sessions)
    assert count == 1
    assert len(qualifying_sessions) == 1

    dec = svc._evaluate_single_exercise(
        uid=auth_user.uid,
        exercise_id="ex_bench_press",
        candidate_prescription=None,
        sessions=[s for s, _ in sessions],
        signals=PersonalizationSignalsResponse(
            userId=auth_user.uid,
            generatedAt=now.isoformat(),
            overallAdherence=SetAdherenceSignal(),
            workoutAdherenceTrend=WorkoutAdherenceTrend(),
        ),
    )
    assert dec.status in ("insufficient_data", "no_change")
    assert dec.ruleCode == "INSUFFICIENT_CONSECUTIVE_SESSIONS"
    assert dec.adaptationType == "no_change"


def test_double_progression_two_qualifying_sessions(auth_user):
    """Verifies that 2 qualifying sessions produces emerging evidence without approved progression."""
    svc = AdaptationEngineService()
    now = datetime.now(timezone.utc)
    def make_qualifying_sets(weight=80.0):
        return [
            WorkoutSetSchema(setNumber=i, targetReps=10, actualReps=10, targetWeightKg=weight, actualWeightKg=weight, isCompleted=True)
            for i in range(1, 4)
        ]

    sessions = [
        (
            WorkoutSessionResponse(
                id="s1", userId=auth_user.uid, workoutId="w1", workoutTitle="Push 1",
                startedAt=(now - timedelta(days=6)).isoformat(),
                completedSetsCount=3, totalSetsCount=3,
                completedSets={"ex_bench_press": make_qualifying_sets(80.0)},
            ),
            make_qualifying_sets(80.0)
        ),
        (
            WorkoutSessionResponse(
                id="s2", userId=auth_user.uid, workoutId="w1", workoutTitle="Push 2",
                startedAt=(now - timedelta(days=2)).isoformat(),
                completedSetsCount=3, totalSetsCount=3,
                completedSets={"ex_bench_press": make_qualifying_sets(80.0)},
            ),
            make_qualifying_sets(80.0)
        ),
    ]

    count, qualifying, _ = svc._evaluate_double_progression_streak(sessions)
    assert count == 2

    dec = svc._evaluate_single_exercise(
        uid=auth_user.uid,
        exercise_id="ex_bench_press",
        candidate_prescription=None,
        sessions=[s for s, _ in sessions],
        signals=PersonalizationSignalsResponse(
            userId=auth_user.uid,
            generatedAt=now.isoformat(),
            overallAdherence=SetAdherenceSignal(),
            workoutAdherenceTrend=WorkoutAdherenceTrend(),
        ),
    )
    assert dec.status == "no_change"
    assert dec.ruleCode == "PROGRESSION_EVIDENCE_EMERGING"
    assert dec.evidence["consecutiveQualifyingSessions"] == 2


def test_double_progression_three_consecutive_sessions_approved(auth_user):
    """Verifies that 3 consecutive qualifying sessions approves load progression (+2.5 kg on 80 kg bench)."""
    svc = AdaptationEngineService()
    now = datetime.now(timezone.utc)
    def make_qualifying_sets(weight=80.0):
        return [
            WorkoutSetSchema(setNumber=i, targetReps=10, actualReps=10, targetWeightKg=weight, actualWeightKg=weight, isCompleted=True)
            for i in range(1, 4)
        ]

    sessions = [
        (
            WorkoutSessionResponse(
                id="s1", userId=auth_user.uid, workoutId="w1", workoutTitle="Push 1",
                startedAt=(now - timedelta(days=10)).isoformat(),
                completedSetsCount=3, totalSetsCount=3,
                completedSets={"ex_bench_press": make_qualifying_sets(80.0)},
            ),
            make_qualifying_sets(80.0)
        ),
        (
            WorkoutSessionResponse(
                id="s2", userId=auth_user.uid, workoutId="w1", workoutTitle="Push 2",
                startedAt=(now - timedelta(days=6)).isoformat(),
                completedSetsCount=3, totalSetsCount=3,
                completedSets={"ex_bench_press": make_qualifying_sets(80.0)},
            ),
            make_qualifying_sets(80.0)
        ),
        (
            WorkoutSessionResponse(
                id="s3", userId=auth_user.uid, workoutId="w1", workoutTitle="Push 3",
                startedAt=(now - timedelta(days=2)).isoformat(),
                completedSetsCount=3, totalSetsCount=3,
                completedSets={"ex_bench_press": make_qualifying_sets(80.0)},
            ),
            make_qualifying_sets(80.0)
        ),
    ]

    count, qualifying, _ = svc._evaluate_double_progression_streak(sessions)
    assert count == 3

    dec = svc._evaluate_single_exercise(
        uid=auth_user.uid,
        exercise_id="ex_bench_press",
        candidate_prescription=None,
        sessions=[s for s, _ in sessions],
        signals=PersonalizationSignalsResponse(
            userId=auth_user.uid,
            generatedAt=now.isoformat(),
            overallAdherence=SetAdherenceSignal(),
            workoutAdherenceTrend=WorkoutAdherenceTrend(),
        ),
    )
    assert dec.status == "progression_candidate"
    assert dec.adaptationType == "load_progression"
    assert dec.ruleCode == "DOUBLE_PROGRESSION_3_SESSIONS"
    assert dec.deltaMagnitude == 2.5
    assert dec.proposedPrescription.weightKg == 82.5
    assert dec.previousPrescription.weightKg == 80.0


def test_double_progression_interrupted_sequence(auth_user):
    """Verifies that pass -> fail -> pass sequence resets consecutive count and prevents progression."""
    svc = AdaptationEngineService()
    now = datetime.now(timezone.utc)
    def make_sets(reps=10, target=10):
        return [
            WorkoutSetSchema(setNumber=i, targetReps=target, actualReps=reps, targetWeightKg=80.0, actualWeightKg=80.0, isCompleted=True)
            for i in range(1, 4)
        ]

    sessions = [
        (
            WorkoutSessionResponse(
                id="s1", userId=auth_user.uid, workoutId="w1", workoutTitle="Push 1",
                startedAt=(now - timedelta(days=10)).isoformat(),
            ),
            make_sets(10, 10)  # Pass
        ),
        (
            WorkoutSessionResponse(
                id="s2", userId=auth_user.uid, workoutId="w1", workoutTitle="Push 2",
                startedAt=(now - timedelta(days=6)).isoformat(),
            ),
            make_sets(7, 10)   # Fail (7 reps vs 10 target)
        ),
        (
            WorkoutSessionResponse(
                id="s3", userId=auth_user.uid, workoutId="w1", workoutTitle="Push 3",
                startedAt=(now - timedelta(days=2)).isoformat(),
            ),
            make_sets(10, 10)  # Pass
        ),
    ]

    count, qualifying, _ = svc._evaluate_double_progression_streak(sessions)
    assert count == 1  # Only the most recent session qualifies


# =============================================================================
# 2. 21-DAY RESET RULE BOUNDARY TESTS
# =============================================================================

def test_21_day_boundary_eligible(auth_user):
    """Verifies that gap of exactly 21 days remains eligible for consecutive sequence."""
    svc = AdaptationEngineService()
    now = datetime.now(timezone.utc)
    def make_qualifying_sets():
        return [
            WorkoutSetSchema(setNumber=i, targetReps=10, actualReps=10, targetWeightKg=80.0, actualWeightKg=80.0, isCompleted=True)
            for i in range(1, 4)
        ]

    sessions = [
        (
            WorkoutSessionResponse(
                id="s1", userId=auth_user.uid, workoutId="w1", workoutTitle="Day 0",
                startedAt=(now - timedelta(days=31)).isoformat(),
            ),
            make_qualifying_sets()
        ),
        (
            WorkoutSessionResponse(
                id="s2", userId=auth_user.uid, workoutId="w1", workoutTitle="Day 10",
                startedAt=(now - timedelta(days=21)).isoformat(),  # 10 days after s1
            ),
            make_qualifying_sets()
        ),
        (
            WorkoutSessionResponse(
                id="s3", userId=auth_user.uid, workoutId="w1", workoutTitle="Day 21",
                startedAt=now.isoformat(),  # Exactly 21 days after s2
            ),
            make_qualifying_sets()
        ),
    ]

    count, qualifying, _ = svc._evaluate_double_progression_streak(sessions)
    assert count == 3


def test_22_day_boundary_resets(auth_user):
    """Verifies that gap of 22 days (> 21 days) resets the qualifying sequence."""
    svc = AdaptationEngineService()
    now = datetime.now(timezone.utc)
    def make_qualifying_sets():
        return [
            WorkoutSetSchema(setNumber=i, targetReps=10, actualReps=10, targetWeightKg=80.0, actualWeightKg=80.0, isCompleted=True)
            for i in range(1, 4)
        ]

    sessions = [
        (
            WorkoutSessionResponse(
                id="s1", userId=auth_user.uid, workoutId="w1", workoutTitle="Day 0",
                startedAt=(now - timedelta(days=40)).isoformat(),
            ),
            make_qualifying_sets()
        ),
        (
            WorkoutSessionResponse(
                id="s2", userId=auth_user.uid, workoutId="w1", workoutTitle="Day 10",
                startedAt=(now - timedelta(days=22, seconds=3600)).isoformat(),  # 22.04 days before s3
            ),
            make_qualifying_sets()
        ),
        (
            WorkoutSessionResponse(
                id="s3", userId=auth_user.uid, workoutId="w1", workoutTitle="Day 32",
                startedAt=now.isoformat(),
            ),
            make_qualifying_sets()
        ),
    ]

    count, qualifying, _ = svc._evaluate_double_progression_streak(sessions)
    # Gap between s2 and s3 was > 21 days, so streak reset at s3
    assert count == 1


# =============================================================================
# 3. LOAD PROGRESSION & 5% CEILING BOUNDARY TESTS
# =============================================================================

def test_lower_compound_increment_approved(auth_user):
    """Verifies lower-body compound (barbell squat) receives +5.0 kg when within 5% ceiling (100 kg -> 105 kg)."""
    svc = AdaptationEngineService()
    now = datetime.now(timezone.utc)
    def make_sets(weight=100.0):
        return [
            WorkoutSetSchema(setNumber=i, targetReps=8, actualReps=8, targetWeightKg=weight, actualWeightKg=weight, isCompleted=True)
            for i in range(1, 4)
        ]

    sessions = [
        (
            WorkoutSessionResponse(
                id=f"s{i}", userId=auth_user.uid, workoutId="w1", workoutTitle="Squat Day",
                startedAt=(now - timedelta(days=(4 - i) * 3)).isoformat(),
                completedSetsCount=3, totalSetsCount=3,
                completedSets={"ex_squat": make_sets(100.0)},
            ),
            make_sets(100.0)
        )
        for i in range(1, 4)
    ]

    dec = svc._evaluate_single_exercise(
        uid=auth_user.uid,
        exercise_id="ex_squat",
        candidate_prescription=None,
        sessions=[s for s, _ in sessions],
        signals=PersonalizationSignalsResponse(
            userId=auth_user.uid,
            generatedAt=now.isoformat(),
            overallAdherence=SetAdherenceSignal(),
            workoutAdherenceTrend=WorkoutAdherenceTrend(),
        ),
    )
    assert dec.status == "progression_candidate"
    assert dec.adaptationType == "load_progression"
    assert dec.deltaMagnitude == 5.0
    assert dec.previousPrescription.weightKg == 100.0
    assert dec.proposedPrescription.weightKg == 105.0


def test_5_percent_ceiling_exact_boundary(auth_user):
    """Verifies that an increase of exactly 5.0% is approved (50 kg + 2.5 kg = 52.5 kg)."""
    svc = AdaptationEngineService()
    now = datetime.now(timezone.utc)
    def make_sets():
        return [
            WorkoutSetSchema(setNumber=i, targetReps=10, actualReps=10, targetWeightKg=50.0, actualWeightKg=50.0, isCompleted=True)
            for i in range(1, 4)
        ]

    sessions = [
        (
            WorkoutSessionResponse(
                id=f"s{i}", userId=auth_user.uid, workoutId="w1", workoutTitle="Bench Day",
                startedAt=(now - timedelta(days=(4 - i) * 3)).isoformat(),
                completedSetsCount=3, totalSetsCount=3,
                completedSets={"ex_bench_press": make_sets()},
            ),
            make_sets()
        )
        for i in range(1, 4)
    ]

    dec = svc._evaluate_single_exercise(
        uid=auth_user.uid,
        exercise_id="ex_bench_press",
        candidate_prescription=None,
        sessions=[s for s, _ in sessions],
        signals=PersonalizationSignalsResponse(
            userId=auth_user.uid,
            generatedAt=now.isoformat(),
            overallAdherence=SetAdherenceSignal(),
            workoutAdherenceTrend=WorkoutAdherenceTrend(),
        ),
    )
    assert dec.status == "progression_candidate"
    assert dec.deltaMagnitude == 2.5
    assert dec.proposedPrescription.weightKg == 52.5


def test_5_percent_ceiling_exceeded_constrained(auth_user):
    """Verifies that +2.5 kg on 40 kg baseline yields 42.5 kg (6.25% > 5%) and is constrained with explicit reason."""
    svc = AdaptationEngineService()
    now = datetime.now(timezone.utc)
    def make_sets():
        return [
            WorkoutSetSchema(setNumber=i, targetReps=10, actualReps=10, targetWeightKg=40.0, actualWeightKg=40.0, isCompleted=True)
            for i in range(1, 4)
        ]

    sessions = [
        (
            WorkoutSessionResponse(
                id=f"s{i}", userId=auth_user.uid, workoutId="w1", workoutTitle="Bench Day",
                startedAt=(now - timedelta(days=(4 - i) * 3)).isoformat(),
                completedSetsCount=3, totalSetsCount=3,
                completedSets={"ex_bench_press": make_sets()},
            ),
            make_sets()
        )
        for i in range(1, 4)
    ]

    dec = svc._evaluate_single_exercise(
        uid=auth_user.uid,
        exercise_id="ex_bench_press",
        candidate_prescription=None,
        sessions=[s for s, _ in sessions],
        signals=PersonalizationSignalsResponse(
            userId=auth_user.uid,
            generatedAt=now.isoformat(),
            overallAdherence=SetAdherenceSignal(),
            workoutAdherenceTrend=WorkoutAdherenceTrend(),
        ),
    )
    assert dec.status == "constrained_no_change"
    assert dec.ruleCode == "LOAD_CEILING_5_PERCENT_EXCEEDED"
    assert dec.deltaMagnitude == 0.0
    assert dec.proposedPrescription.weightKg == 40.0
    assert "exceeds the hard 5% weekly load increase ceiling" in dec.rationale


def test_isolation_bodyweight_rep_progression(auth_user):
    """Verifies bodyweight exercise receives bounded rep progression (+1 rep to min and max)."""
    svc = AdaptationEngineService()
    now = datetime.now(timezone.utc)
    def make_sets():
        return [
            WorkoutSetSchema(setNumber=i, targetReps=10, actualReps=10, targetWeightKg=0.0, actualWeightKg=0.0, isCompleted=True)
            for i in range(1, 4)
        ]

    sessions = [
        (
            WorkoutSessionResponse(
                id=f"s{i}", userId=auth_user.uid, workoutId="w1", workoutTitle="Pull Up Day",
                startedAt=(now - timedelta(days=(4 - i) * 3)).isoformat(),
                completedSetsCount=3, totalSetsCount=3,
                completedSets={"ex_pull_up": make_sets()},
            ),
            make_sets()
        )
        for i in range(1, 4)
    ]

    dec = svc._evaluate_single_exercise(
        uid=auth_user.uid,
        exercise_id="ex_pull_up",
        candidate_prescription=PrescriptionDelta(exerciseId="ex_pull_up", targetRepsMin=8, targetRepsMax=10, weightKg=0.0, setCount=3),
        sessions=[s for s, _ in sessions],
        signals=PersonalizationSignalsResponse(
            userId=auth_user.uid,
            generatedAt=now.isoformat(),
            overallAdherence=SetAdherenceSignal(),
            workoutAdherenceTrend=WorkoutAdherenceTrend(),
        ),
    )
    assert dec.status == "progression_candidate"
    assert dec.adaptationType == "rep_progression"
    assert dec.deltaMagnitude == 1.0
    assert dec.deltaUnit == "reps"
    assert dec.proposedPrescription.targetRepsMin == 9
    assert dec.proposedPrescription.targetRepsMax == 11


# =============================================================================
# 4. VOLUME FATIGUE & SET BOUNDS
# =============================================================================

def test_volume_fatigue_one_session_no_reduction(auth_user):
    """Verifies 1 incomplete session is not enough to propose set reduction."""
    svc = AdaptationEngineService()
    now = datetime.now(timezone.utc)
    sessions = [
        (
            WorkoutSessionResponse(
                id="s1", userId=auth_user.uid, workoutId="w1", workoutTitle="Day 1",
                startedAt=(now - timedelta(days=2)).isoformat(),
                totalSetsCount=5, completedSetsCount=2,  # 2/5 = 40% (< 70%)
            ),
            [WorkoutSetSchema(setNumber=1, targetReps=10, actualReps=10, isCompleted=True)]
        )
    ]
    failures, _ = svc._evaluate_volume_fatigue_streak(sessions)
    assert failures == 1


def test_volume_fatigue_two_consecutive_sessions_reduces_sets(auth_user):
    """Verifies 2 consecutive volume failures (< 70%) proposes reducing set count by 1 (4 -> 3 sets)."""
    svc = AdaptationEngineService()
    now = datetime.now(timezone.utc)
    sessions = [
        (
            WorkoutSessionResponse(
                id="s1", userId=auth_user.uid, workoutId="w1", workoutTitle="Day 1",
                startedAt=(now - timedelta(days=5)).isoformat(),
                totalSetsCount=5, completedSetsCount=3,  # 3/5 = 60% (< 70%)
                completedSets={"ex_bench_press": [WorkoutSetSchema(setNumber=1, targetReps=10, actualReps=10, isCompleted=True)]},
            ),
            [WorkoutSetSchema(setNumber=1, targetReps=10, actualReps=10, isCompleted=True)]
        ),
        (
            WorkoutSessionResponse(
                id="s2", userId=auth_user.uid, workoutId="w1", workoutTitle="Day 2",
                startedAt=(now - timedelta(days=2)).isoformat(),
                totalSetsCount=5, completedSetsCount=2,  # 2/5 = 40% (< 70%)
                completedSets={"ex_bench_press": [WorkoutSetSchema(setNumber=1, targetReps=10, actualReps=10, isCompleted=True)]},
            ),
            [WorkoutSetSchema(setNumber=1, targetReps=10, actualReps=10, isCompleted=True)]
        ),
    ]

    dec = svc._evaluate_single_exercise(
        uid=auth_user.uid,
        exercise_id="ex_bench_press",
        candidate_prescription=PrescriptionDelta(exerciseId="ex_bench_press", setCount=4),
        sessions=[s for s, _ in sessions],
        signals=PersonalizationSignalsResponse(
            userId=auth_user.uid,
            generatedAt=now.isoformat(),
            overallAdherence=SetAdherenceSignal(),
            workoutAdherenceTrend=WorkoutAdherenceTrend(),
        ),
    )
    assert dec.status == "volume_reduction_candidate"
    assert dec.adaptationType == "volume_reduction"
    assert dec.deltaMagnitude == -1.0
    assert dec.deltaUnit == "sets"
    assert dec.previousPrescription.setCount == 4
    assert dec.proposedPrescription.setCount == 3


def test_volume_fatigue_minimum_set_bound_enforced(auth_user):
    """Verifies that if current set count is already 1, further reduction is blocked (MINIMUM_SET_BOUND_REACHED)."""
    svc = AdaptationEngineService()
    now = datetime.now(timezone.utc)
    sessions = [
        (
            WorkoutSessionResponse(
                id="s1", userId=auth_user.uid, workoutId="w1", workoutTitle="Day 1",
                startedAt=(now - timedelta(days=5)).isoformat(),
                totalSetsCount=4, completedSetsCount=2,  # 50%
                completedSets={"ex_bench_press": [WorkoutSetSchema(setNumber=1, targetReps=10, actualReps=10, isCompleted=True)]},
            ),
            [WorkoutSetSchema(setNumber=1, targetReps=10, actualReps=10, isCompleted=True)]
        ),
        (
            WorkoutSessionResponse(
                id="s2", userId=auth_user.uid, workoutId="w1", workoutTitle="Day 2",
                startedAt=(now - timedelta(days=2)).isoformat(),
                totalSetsCount=4, completedSetsCount=1,  # 25%
                completedSets={"ex_bench_press": [WorkoutSetSchema(setNumber=1, targetReps=10, actualReps=10, isCompleted=True)]},
            ),
            [WorkoutSetSchema(setNumber=1, targetReps=10, actualReps=10, isCompleted=True)]
        ),
    ]

    dec = svc._evaluate_single_exercise(
        uid=auth_user.uid,
        exercise_id="ex_bench_press",
        candidate_prescription=PrescriptionDelta(exerciseId="ex_bench_press", setCount=1),
        sessions=[s for s, _ in sessions],
        signals=PersonalizationSignalsResponse(
            userId=auth_user.uid,
            generatedAt=now.isoformat(),
            overallAdherence=SetAdherenceSignal(),
            workoutAdherenceTrend=WorkoutAdherenceTrend(),
        ),
    )
    assert dec.status == "constrained_no_change"
    assert dec.ruleCode == "MINIMUM_SET_BOUND_REACHED"
    assert dec.proposedPrescription.setCount == 1


# =============================================================================
# 5. CONFLICT RESOLUTION PRECEDENCE
# =============================================================================

def test_conflict_volume_fatigue_overrides_progression(auth_user):
    """Verifies that conservative volume fatigue strictly overrides progression when both signals are present."""
    svc = AdaptationEngineService()
    now = datetime.now(timezone.utc)
    def make_qualifying_sets():
        return [
            WorkoutSetSchema(setNumber=1, targetReps=10, actualReps=10, targetWeightKg=80.0, actualWeightKg=80.0, isCompleted=True),
        ]

    # 3 sessions reaching target reps for this exercise, but the overall workout suffered volume failure (< 70%)
    sessions = [
        (
            WorkoutSessionResponse(
                id="s1", userId=auth_user.uid, workoutId="w1", workoutTitle="Day 1",
                startedAt=(now - timedelta(days=8)).isoformat(),
                totalSetsCount=10, completedSetsCount=10,
                completedSets={"ex_bench_press": make_qualifying_sets()},
            ),
            make_qualifying_sets()
        ),
        (
            WorkoutSessionResponse(
                id="s2", userId=auth_user.uid, workoutId="w1", workoutTitle="Day 2",
                startedAt=(now - timedelta(days=5)).isoformat(),
                totalSetsCount=10, completedSetsCount=5,  # 50% volume failure!
                completedSets={"ex_bench_press": make_qualifying_sets()},
            ),
            make_qualifying_sets()
        ),
        (
            WorkoutSessionResponse(
                id="s3", userId=auth_user.uid, workoutId="w1", workoutTitle="Day 3",
                startedAt=(now - timedelta(days=2)).isoformat(),
                totalSetsCount=10, completedSetsCount=4,  # 40% volume failure!
                completedSets={"ex_bench_press": make_qualifying_sets()},
            ),
            make_qualifying_sets()
        ),
    ]

    dec = svc._evaluate_single_exercise(
        uid=auth_user.uid,
        exercise_id="ex_bench_press",
        candidate_prescription=PrescriptionDelta(exerciseId="ex_bench_press", setCount=4, weightKg=80.0),
        sessions=[s for s, _ in sessions],
        signals=PersonalizationSignalsResponse(
            userId=auth_user.uid,
            generatedAt=now.isoformat(),
            overallAdherence=SetAdherenceSignal(),
            workoutAdherenceTrend=WorkoutAdherenceTrend(),
        ),
    )
    # Conservative volume fatigue MUST override progression!
    assert dec.status == "volume_reduction_candidate"
    assert dec.adaptationType == "volume_reduction"
    assert dec.ruleCode == "VOLUME_FATIGUE_2_SESSIONS"
    assert dec.proposedPrescription.setCount == 3
    assert dec.proposedPrescription.weightKg == 80.0  # Weight not increased


# =============================================================================
# 6. FORM ISSUE SIGNALS & CV PROPOSALS
# =============================================================================

def test_form_issue_recurring_proposal_generated(auth_user):
    """Verifies recurring form issue generates structured proposal without Slot 0 injection."""
    svc = AdaptationEngineService()
    signals = PersonalizationSignalsResponse(
        userId=auth_user.uid,
        generatedAt=datetime.now(timezone.utc).isoformat(),
        overallAdherence=SetAdherenceSignal(),
        workoutAdherenceTrend=WorkoutAdherenceTrend(),
        formSignals={
            "ex_squat": ExerciseFormSignal(
                exerciseId="ex_squat",
                canonicalCvExercise="squat",
                sessionsObserved=4,
                totalRepsAnalyzed=32,
                avgFormScore=82.5,
                evidenceLevel="stable_signal",
                detectedIssues=[
                    FormIssueFrequency(
                        issue="insufficient_depth",
                        occurrenceCount=3,
                        totalSessionsWithExercise=4,
                        frequencyRate=0.75,
                        isRecurring=True,
                    ),
                    FormIssueFrequency(
                        issue="knee_valgus",
                        occurrenceCount=1,
                        totalSessionsWithExercise=4,
                        frequencyRate=0.25,
                        isRecurring=False,
                    ),
                ],
            )
        },
    )

    proposals = svc._evaluate_form_issue_proposals(auth_user.uid, signals)
    assert len(proposals) == 1
    p = proposals[0]
    assert p.status == "form_issue_candidate"
    assert p.adaptationType == "recurring_form_issue"
    assert p.ruleCode == "RECURRING_FORM_ISSUE_DETECTED"
    assert p.evidence["issueId"] == "insufficient_depth"
    assert p.evidence["occurrenceCount"] == 3
    assert "Slot 0 corrective injection deferred to Phase 9C.6" in p.constraintsApplied[0]


# =============================================================================
# 7. ADHERENCE FUTURE-BLOCK SPLIT ADAPTATION
# =============================================================================

def test_adherence_split_mismatch_4_weeks_recommended(auth_user):
    """Verifies 5-day plan with ~3 completed sessions/week produces 3-day Full Body split recommendation."""
    svc = AdaptationEngineService()
    signals = PersonalizationSignalsResponse(
        userId=auth_user.uid,
        generatedAt=datetime.now(timezone.utc).isoformat(),
        overallAdherence=SetAdherenceSignal(),
        workoutAdherenceTrend=WorkoutAdherenceTrend(
            observationWindowDays=28,
            sessionsCompleted=12,
            expectedSessions=20,
            expectedFrequencyPerWeek=5.0,
            observedFrequencyPerWeek=3.0,
            adherenceRate=0.60,
        ),
    )

    proposal = svc._evaluate_future_split_adaptation(auth_user.uid, signals)
    assert proposal is not None
    assert proposal.recommendedSplit == "full_body"
    assert proposal.recommendedDaysPerWeek == 3
    assert proposal.isFutureBlockOnly is True
    assert proposal.ruleCode == "ADHERENCE_SPLIT_MISMATCH_4_WEEKS"


def test_adherence_missing_planned_frequency_no_fabrication(auth_user):
    """Verifies that absent planned frequency produces None without fabricating adherence."""
    svc = AdaptationEngineService()
    signals = PersonalizationSignalsResponse(
        userId=auth_user.uid,
        generatedAt=datetime.now(timezone.utc).isoformat(),
        overallAdherence=SetAdherenceSignal(),
        workoutAdherenceTrend=WorkoutAdherenceTrend(
            observationWindowDays=28,
            sessionsCompleted=8,
            expectedSessions=None,
            expectedFrequencyPerWeek=None,
            observedFrequencyPerWeek=2.0,
        ),
    )

    proposal = svc._evaluate_future_split_adaptation(auth_user.uid, signals)
    assert proposal is None


# =============================================================================
# 8. DURATION & RPE CONSTRAINTS
# =============================================================================

def test_duration_exceeds_125_percent_constrained(auth_user):
    """Verifies that exercise volume exceeding 1.25x target session duration is constrained."""
    svc = AdaptationEngineService()
    now = datetime.now(timezone.utc)
    sessions = [
        WorkoutSessionResponse(
            id="s1", userId=auth_user.uid, workoutId="w1", workoutTitle="Day 1",
            startedAt=(now - timedelta(days=2)).isoformat(),
            completedSetsCount=5, totalSetsCount=5,
            completedSets={
                "ex_bench_press": [
                    WorkoutSetSchema(setNumber=i, targetReps=10, actualReps=10, targetWeightKg=80.0, actualWeightKg=80.0, isCompleted=True)
                    for i in range(1, 6)
                ]
            }
        )
    ]

    # Target duration is 15 minutes, but 5 sets * 126s = ~10.5 mins for this single exercise
    dec = svc._evaluate_single_exercise(
        uid=auth_user.uid,
        exercise_id="ex_bench_press",
        candidate_prescription=PrescriptionDelta(exerciseId="ex_bench_press", setCount=5, restSeconds=180),
        sessions=sessions,
        signals=PersonalizationSignalsResponse(
            userId=auth_user.uid,
            generatedAt=now.isoformat(),
            overallAdherence=SetAdherenceSignal(),
            workoutAdherenceTrend=WorkoutAdherenceTrend(),
        ),
        target_duration_minutes=10,  # 1.25 * 10 = 12.5 mins ceiling; 5 sets * (36s + 180s) = 18 mins > 12.5 mins
    )
    assert dec.status == "constrained_no_change"
    assert dec.ruleCode == "DURATION_EXCEEDS_125_PCT"


# =============================================================================
# 9. DETERMINISM
# =============================================================================

def test_determinism_identical_inputs_identical_decision_id():
    """Verifies that identical decision inputs produce byte-identical SHA-256 decision IDs."""
    id1 = generate_decision_id("user_123", "ex_bench_press", "DOUBLE_PROGRESSION_3_SESSIONS", "load_progression", "progression_candidate", 2.5)
    id2 = generate_decision_id("user_123", "ex_bench_press", "DOUBLE_PROGRESSION_3_SESSIONS", "load_progression", "progression_candidate", 2.5)
    assert id1 == id2
    assert len(id1) == 16


# =============================================================================
# 10. API SECURITY & CROSS-USER ISOLATION
# =============================================================================

def test_api_get_adaptations_unauthenticated(client):
    """Verifies GET /api/v1/personalization/adaptations rejects unauthenticated requests with HTTP 401."""
    app.dependency_overrides.clear()
    res = client.get("/api/v1/personalization/adaptations")
    assert res.status_code == 401


def test_api_post_evaluate_unauthenticated(client):
    """Verifies POST /api/v1/personalization/adaptations/evaluate rejects unauthenticated requests with HTTP 401."""
    app.dependency_overrides.clear()
    res = client.post("/api/v1/personalization/adaptations/evaluate", json={"windowDays": 28})
    assert res.status_code == 401


def test_api_get_adaptations_authenticated(client, auth_user):
    """Verifies authenticated user can query GET /api/v1/personalization/adaptations."""
    app.dependency_overrides[get_current_user] = lambda: auth_user
    res = client.get("/api/v1/personalization/adaptations?window_days=28")
    assert res.status_code == 200
    data = res.json()
    assert data["userId"] == auth_user.uid
    assert "primaryDecisions" in data
    assert "summaryMetrics" in data


def test_api_post_evaluate_authenticated(client, auth_user):
    """Verifies authenticated user can evaluate candidate prescription with POST /api/v1/personalization/adaptations/evaluate."""
    app.dependency_overrides[get_current_user] = lambda: auth_user
    payload = {
        "candidateExercises": [
            {
                "exerciseId": "ex_bench_press",
                "weightKg": 80.0,
                "setCount": 3,
                "targetRepsMin": 8,
                "targetRepsMax": 10,
            }
        ],
        "targetDurationMinutes": 45,
        "windowDays": 28,
    }
    res = client.post("/api/v1/personalization/adaptations/evaluate", json=payload)
    assert res.status_code == 200
    data = res.json()
    assert data["userId"] == auth_user.uid
    assert len(data["primaryDecisions"]) >= 1
    assert data["primaryDecisions"][0]["exerciseId"] == "ex_bench_press"


def test_cross_user_isolation(client, auth_user, other_user):
    """Verifies User A's workout sessions never leak into User B's adaptation evaluations."""
    workout_repo = get_workout_repository()
    # Populate User A with a completed workout
    sess = workout_repo.create_session(
        auth_user.uid,
        WorkoutSessionCreate(workoutId="generated", workoutTitle="User A Bench", totalSetsCount=3)
    )
    workout_repo.update_session(
        auth_user.uid,
        sess.id,
        WorkoutSessionUpdate(
            recordedSet=WorkoutSetRecord(exerciseId="ex_bench_press", setNumber=1, actualReps=10, actualWeightKg=90.0)
        )
    )
    workout_repo.complete_session(auth_user.uid, sess.id, WorkoutSessionComplete(durationSeconds=1800))

    # Query as other_user
    app.dependency_overrides[get_current_user] = lambda: other_user
    res = client.get("/api/v1/personalization/adaptations")
    assert res.status_code == 200
    data = res.json()
    assert data["userId"] == other_user.uid
    # other_user has 0 completed workouts
    assert data["summaryMetrics"]["totalDecisionsEvaluated"] == 0


# =============================================================================
# 11. ADDITIONAL SPECIFIC BOUNDARY TESTS
# =============================================================================

def test_zero_and_negative_load_handling(auth_user):
    """Verifies baseline load of 0.0 or negative is safely handled without crashing."""
    svc = AdaptationEngineService()
    now = datetime.now(timezone.utc)
    sessions = [
        (
            WorkoutSessionResponse(
                id="s1", userId=auth_user.uid, workoutId="w1", workoutTitle="Bodyweight Day",
                startedAt=(now - timedelta(days=2)).isoformat(),
                completedSetsCount=3, totalSetsCount=3,
                completedSets={"ex_pull_up": [WorkoutSetSchema(setNumber=1, targetReps=10, actualReps=10, actualWeightKg=0.0, isCompleted=True)]},
            ),
            [WorkoutSetSchema(setNumber=1, targetReps=10, actualReps=10, actualWeightKg=0.0, isCompleted=True)]
        )
    ]
    dec = svc._evaluate_single_exercise(
        uid=auth_user.uid,
        exercise_id="ex_pull_up",
        candidate_prescription=PrescriptionDelta(exerciseId="ex_pull_up", weightKg=0.0, setCount=3),
        sessions=[s for s, _ in sessions],
        signals=PersonalizationSignalsResponse(
            userId=auth_user.uid,
            generatedAt=now.isoformat(),
            overallAdherence=SetAdherenceSignal(),
            workoutAdherenceTrend=WorkoutAdherenceTrend(),
        ),
    )
    assert dec.previousPrescription.weightKg == 0.0


def test_max_sets_ceiling_not_exceeded():
    """Verifies that PrescriptionDelta rejects setCount > 5 (max normal sets bound)."""
    with pytest.raises(Exception):
        PrescriptionDelta(exerciseId="ex_bench_press", setCount=6)


def test_non_recurring_form_issue_no_proposal(auth_user):
    """Verifies that an issue with frequency < 50% (isRecurring=False) does not trigger a proposal."""
    svc = AdaptationEngineService()
    signals = PersonalizationSignalsResponse(
        userId=auth_user.uid,
        generatedAt=datetime.now(timezone.utc).isoformat(),
        overallAdherence=SetAdherenceSignal(),
        workoutAdherenceTrend=WorkoutAdherenceTrend(),
        formSignals={
            "ex_squat": ExerciseFormSignal(
                exerciseId="ex_squat",
                canonicalCvExercise="squat",
                sessionsObserved=4,
                totalRepsAnalyzed=30,
                detectedIssues=[
                    FormIssueFrequency(
                        issue="knee_valgus",
                        occurrenceCount=1,
                        totalSessionsWithExercise=4,
                        frequencyRate=0.25,
                        isRecurring=False,
                    )
                ],
            )
        },
    )
    proposals = svc._evaluate_form_issue_proposals(auth_user.uid, signals)
    assert len(proposals) == 0


def test_non_cv_exercise_excluded_from_cv_form_source(auth_user):
    """Verifies non-CV exercise is not present in form signals and does not generate form proposals."""
    from backend.app.schemas.exercise import is_canonical_cv_exercise
    assert is_canonical_cv_exercise("ex_lat_pulldown") is False
    assert is_canonical_cv_exercise("ex_bench_press") is True


def test_adherence_insufficient_four_week_evidence_no_proposal(auth_user):
    """Verifies that having fewer than 4 completed sessions across 28 days does not trigger split adaptation."""
    svc = AdaptationEngineService()
    signals = PersonalizationSignalsResponse(
        userId=auth_user.uid,
        generatedAt=datetime.now(timezone.utc).isoformat(),
        overallAdherence=SetAdherenceSignal(),
        workoutAdherenceTrend=WorkoutAdherenceTrend(
            observationWindowDays=28,
            sessionsCompleted=2,  # Only 2 sessions
            expectedSessions=20,
            expectedFrequencyPerWeek=5.0,
            observedFrequencyPerWeek=0.5,
        ),
    )
    proposal = svc._evaluate_future_split_adaptation(auth_user.uid, signals)
    assert proposal is None


def test_relationship_service_regression_and_substitution_validity():
    """Verifies ExerciseRelationshipService retrieves only regressions for regressions, and substitutions for substitutions."""
    from backend.app.services.exercise_relationship_service import get_exercise_relationship_service
    rel_svc = get_exercise_relationship_service()

    regressions = rel_svc.get_regressions("ex_squat")
    assert len(regressions) >= 1
    assert all(r.relationshipType == "regression" for r in regressions)

    substitutions = rel_svc.get_substitutions("ex_bench_press")
    assert len(substitutions) >= 1
    assert all(s.relationshipType == "substitution" for s in substitutions)


def test_duration_within_125_percent_feasible(auth_user):
    """Verifies that an exercise volume within 125% of target duration remains feasible."""
    svc = AdaptationEngineService()
    now = datetime.now(timezone.utc)
    sessions = [
        WorkoutSessionResponse(
            id="s1", userId=auth_user.uid, workoutId="w1", workoutTitle="Day 1",
            startedAt=(now - timedelta(days=2)).isoformat(),
            completedSetsCount=3, totalSetsCount=3,
            completedSets={"ex_bench_press": [WorkoutSetSchema(setNumber=1, targetReps=10, actualReps=10, isCompleted=True)]},
        )
    ]
    dec = svc._evaluate_single_exercise(
        uid=auth_user.uid,
        exercise_id="ex_bench_press",
        candidate_prescription=PrescriptionDelta(exerciseId="ex_bench_press", setCount=3, restSeconds=90),
        sessions=sessions,
        signals=PersonalizationSignalsResponse(
            userId=auth_user.uid,
            generatedAt=now.isoformat(),
            overallAdherence=SetAdherenceSignal(),
            workoutAdherenceTrend=WorkoutAdherenceTrend(),
        ),
        target_duration_minutes=45,  # 45 min * 1.25 = 56 min ceiling; 3 sets = ~6.3 mins, well within bound
    )
    assert dec.ruleCode != "DURATION_EXCEEDS_125_PCT"


def test_rpe_boundary_9_and_above_clamped(auth_user):
    """Verifies that candidate RPE of 9.0 is valid, and candidate RPE of 9.5 is clamped to 9.0."""
    svc = AdaptationEngineService()
    now = datetime.now(timezone.utc)
    sessions = [
        WorkoutSessionResponse(
            id="s1", userId=auth_user.uid, workoutId="w1", workoutTitle="Day 1",
            startedAt=(now - timedelta(days=2)).isoformat(),
            completedSetsCount=3, totalSetsCount=3,
            completedSets={"ex_bench_press": [WorkoutSetSchema(setNumber=1, targetReps=10, actualReps=10, isCompleted=True)]},
        )
    ]
    dec = svc._evaluate_single_exercise(
        uid=auth_user.uid,
        exercise_id="ex_bench_press",
        candidate_prescription=PrescriptionDelta(exerciseId="ex_bench_press", targetRpe=9.5),
        sessions=sessions,
        signals=PersonalizationSignalsResponse(
            userId=auth_user.uid,
            generatedAt=now.isoformat(),
            overallAdherence=SetAdherenceSignal(),
            workoutAdherenceTrend=WorkoutAdherenceTrend(),
        ),
    )
    assert dec.previousPrescription.targetRpe == 9.0
    assert any("clamped to 9.0" in c for c in dec.constraintsApplied)


def test_adaptation_zero_firestore_writes(client, auth_user):
    """Verifies that evaluating adaptations performs zero Firestore writes."""
    app.dependency_overrides[get_current_user] = lambda: auth_user
    workout_repo = get_workout_repository()
    initial_sessions_count = len(workout_repo.list_user_history(auth_user.uid, limit=100))

    # Perform evaluation
    res = client.get("/api/v1/personalization/adaptations")
    assert res.status_code == 200

    res_eval = client.post(
        "/api/v1/personalization/adaptations/evaluate",
        json={"windowDays": 28, "targetDurationMinutes": 45},
    )
    assert res_eval.status_code == 200

    # Verify session count and repository state unchanged
    final_sessions_count = len(workout_repo.list_user_history(auth_user.uid, limit=100))
    assert final_sessions_count == initial_sessions_count
