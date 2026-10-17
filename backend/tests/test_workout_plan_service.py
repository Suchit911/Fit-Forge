"""
Unit Tests for Deterministic Workout Plan Construction Service (Phase 9B.8.5.2).

Validates:
1. 1-day split routing (Full Body A)
2. 2-day split routing (Full Body A, Full Body B)
3. 3-day split routing (Full Body A, Full Body B, Full Body C)
4. 4-day split routing (Upper A, Lower A, Upper B, Lower B)
5. 5-day split routing (Upper, Lower, Push, Pull, Legs)
6. 6-day split routing (Push A, Pull A, Legs A, Push B, Pull B, Legs B)
7. Required slot ordering (Slot 0 if present, then Slots 1, 2, 3, 4, 5)
8. Primary compound enforcement (Slot 1 strictly compound)
9. Secondary compound behavior (Slot 2 strictly compound & complementary)
10. Intra-day duplicate prevention (zero duplicates in any workout day)
11. Inter-day primary diversity preference (alternates primary compound where feasible)
12. Movement-pattern preference not becoming a hard gate
13. Equipment subset semantics (exercise.equipment ⊆ available_equipment)
14. Multi-equipment failure case (requires both barbell and bench; only one provided)
15. Environment filtering (outdoor / home compatibility)
16. Explicit exercise exclusions (never selects excluded IDs)
17. Corrective Slot 0 valid case (populated when canonical CV source & valid issue provided)
18. Corrective Slot 0 omitted case (omitted when no corrective parameters provided)
19. Invalid corrective parameters (diagnostics returned for non-canonical CV source)
20. State B missing required input (validation failure / out of bounds)
21. State C conflicting hard constraints (impossible equipment/environment or split mismatch)
22. State D catalog shortfall (slot failure returns State D with exact diagnostics)
23. Deterministic identical request ordering (byte-for-byte reproducibility)
24. Deterministic plan structure (weeks, days, metrics)
25. No fabricated bodyweight fallback (slot shortfall does not invent random bodyweight)
26. No Gemini / network / Firestore dependency (pure local computation)
27. Plan-level feasibility verification (verifies whole plan before returning State A)
28. No duplicate exercise IDs across a workout day (exhaustive multi-day check)
"""

import sys
import pytest

from backend.app.schemas.workout_plan import (
    WorkoutSplitType,
    ExerciseSlotRole,
    WorkoutPlanGenerateRequest,
    WorkoutPlanResponse,
)
from backend.app.services.workout_plan_service import (
    WorkoutPlanService,
    get_workout_plan_service,
)
from backend.app.seeds.catalog import CATALOG_BY_ID


@pytest.fixture
def service() -> WorkoutPlanService:
    """Provides a clean instance of WorkoutPlanService."""
    return get_workout_plan_service()


# ============================================================================
# 1 to 6: Split Routing Tests
# ============================================================================

def test_1_day_split_routing(service: WorkoutPlanService):
    """1. 1-day split routing -> Full Body A."""
    req = WorkoutPlanGenerateRequest(trainingDaysPerWeek=1, environment="gym")
    res = service.generate_plan(req)

    assert res.feasibilityCheckPassed is True
    assert res.splitType == WorkoutSplitType.FULL_BODY
    assert len(res.weeks[0].days) == 1
    assert res.weeks[0].days[0].dayLabel == "Full Body A"


def test_2_day_split_routing(service: WorkoutPlanService):
    """2. 2-day split routing -> Full Body A, Full Body B."""
    req = WorkoutPlanGenerateRequest(trainingDaysPerWeek=2, environment="gym")
    res = service.generate_plan(req)

    assert res.feasibilityCheckPassed is True
    assert res.splitType == WorkoutSplitType.FULL_BODY
    assert len(res.weeks[0].days) == 2
    labels = [d.dayLabel for d in res.weeks[0].days]
    assert labels == ["Full Body A", "Full Body B"]


def test_3_day_split_routing(service: WorkoutPlanService):
    """3. 3-day split routing -> Full Body A, Full Body B, Full Body C."""
    req = WorkoutPlanGenerateRequest(trainingDaysPerWeek=3, environment="gym")
    res = service.generate_plan(req)

    assert res.feasibilityCheckPassed is True
    assert res.splitType == WorkoutSplitType.FULL_BODY
    assert len(res.weeks[0].days) == 3
    labels = [d.dayLabel for d in res.weeks[0].days]
    assert labels == ["Full Body A", "Full Body B", "Full Body C"]


def test_4_day_split_routing(service: WorkoutPlanService):
    """4. 4-day split routing -> Upper A, Lower A, Upper B, Lower B."""
    req = WorkoutPlanGenerateRequest(trainingDaysPerWeek=4, environment="gym")
    res = service.generate_plan(req)

    assert res.feasibilityCheckPassed is True
    assert res.splitType == WorkoutSplitType.UPPER_LOWER
    assert len(res.weeks[0].days) == 4
    labels = [d.dayLabel for d in res.weeks[0].days]
    assert labels == ["Upper A", "Lower A", "Upper B", "Lower B"]


def test_5_day_split_routing(service: WorkoutPlanService):
    """5. 5-day split routing -> Upper, Lower, Push, Pull, Legs."""
    req = WorkoutPlanGenerateRequest(trainingDaysPerWeek=5, environment="gym")
    res = service.generate_plan(req)

    assert res.feasibilityCheckPassed is True
    assert res.splitType == WorkoutSplitType.UPPER_LOWER
    assert len(res.weeks[0].days) == 5
    labels = [d.dayLabel for d in res.weeks[0].days]
    assert labels == ["Upper", "Lower", "Push", "Pull", "Legs"]


def test_6_day_split_routing(service: WorkoutPlanService):
    """6. 6-day split routing -> Push A, Pull A, Legs A, Push B, Pull B, Legs B."""
    req = WorkoutPlanGenerateRequest(trainingDaysPerWeek=6, environment="gym")
    res = service.generate_plan(req)

    assert res.feasibilityCheckPassed is True
    assert res.splitType == WorkoutSplitType.PUSH_PULL_LEGS
    assert len(res.weeks[0].days) == 6
    labels = [d.dayLabel for d in res.weeks[0].days]
    assert labels == ["Push A", "Pull A", "Legs A", "Push B", "Pull B", "Legs B"]


# ============================================================================
# 7 to 9: Slot Architecture & Compound Enforcement
# ============================================================================

def test_required_slot_ordering(service: WorkoutPlanService):
    """7. Required slot ordering -> strictly ordered by slotIndex (1, 2, 3, 4, 5)."""
    req = WorkoutPlanGenerateRequest(trainingDaysPerWeek=3, environment="gym")
    res = service.generate_plan(req)

    assert res.feasibilityCheckPassed is True
    for day in res.weeks[0].days:
        indices = [ex.slotIndex for ex in day.exercises]
        assert indices == [1, 2, 3, 4, 5]
        roles = [ex.slotRole for ex in day.exercises]
        assert roles == [
            ExerciseSlotRole.PRIMARY_COMPOUND,
            ExerciseSlotRole.SECONDARY_COMPOUND,
            ExerciseSlotRole.ACCESSORY_1,
            ExerciseSlotRole.ACCESSORY_2,
            ExerciseSlotRole.CORE_MOBILITY,
        ]


def test_primary_compound_enforcement(service: WorkoutPlanService):
    """8. Primary compound enforcement -> Slot 1 is always compound."""
    req = WorkoutPlanGenerateRequest(trainingDaysPerWeek=4, environment="gym")
    res = service.generate_plan(req)

    assert res.feasibilityCheckPassed is True
    for day in res.weeks[0].days:
        slot1 = day.exercises[0]
        assert slot1.slotRole == ExerciseSlotRole.PRIMARY_COMPOUND
        assert slot1.exerciseType == "compound"
        # Verify in catalog
        catalog_entry = CATALOG_BY_ID[slot1.exerciseId]
        assert catalog_entry.exerciseType == "compound"


def test_secondary_compound_behavior(service: WorkoutPlanService):
    """9. Secondary compound behavior -> Slot 2 is compound and distinct from Slot 1."""
    req = WorkoutPlanGenerateRequest(trainingDaysPerWeek=3, environment="gym")
    res = service.generate_plan(req)

    assert res.feasibilityCheckPassed is True
    for day in res.weeks[0].days:
        slot1 = day.exercises[0]
        slot2 = day.exercises[1]
        assert slot2.slotRole == ExerciseSlotRole.SECONDARY_COMPOUND
        assert slot2.exerciseType == "compound"
        assert slot1.exerciseId != slot2.exerciseId


# ============================================================================
# 10 to 12: Deduplication & Diversity Preferences
# ============================================================================

def test_intra_day_duplicate_prevention(service: WorkoutPlanService):
    """10. Intra-day duplicate prevention -> no exercise repeated within any single day."""
    req = WorkoutPlanGenerateRequest(trainingDaysPerWeek=4, environment="gym")
    res = service.generate_plan(req)

    assert res.feasibilityCheckPassed is True
    for day in res.weeks[0].days:
        ids = [ex.exerciseId for ex in day.exercises]
        assert len(ids) == len(set(ids)), f"Duplicates found in {day.dayLabel}: {ids}"


def test_inter_day_primary_diversity_preference(service: WorkoutPlanService):
    """11. Inter-day primary diversity preference -> alternates primary compound when alternatives exist."""
    req = WorkoutPlanGenerateRequest(trainingDaysPerWeek=3, environment="gym")
    res = service.generate_plan(req)

    assert res.feasibilityCheckPassed is True
    day1_primary = res.weeks[0].days[0].exercises[0].exerciseId
    day2_primary = res.weeks[0].days[1].exercises[0].exerciseId
    day3_primary = res.weeks[0].days[2].exercises[0].exerciseId

    assert day1_primary != day2_primary
    assert day2_primary != day3_primary


def test_movement_pattern_preference_not_hard_gate(service: WorkoutPlanService):
    """12. Movement-pattern preference is not a hard gate -> plan succeeds even if a preferred pattern has no compounds."""
    # Request preferred movement pattern that has few compounds in home environment
    req = WorkoutPlanGenerateRequest(
        trainingDaysPerWeek=3,
        environment="home",
        availableEquipment=["bodyweight"],
        preferredMovementPatterns=["carry"],  # Carry typically has few bodyweight compound exercises
    )
    res = service.generate_plan(req)
    assert res.feasibilityCheckPassed is True


# ============================================================================
# 13 to 16: Hard Constraints & Filtering
# ============================================================================

def test_equipment_subset_semantics(service: WorkoutPlanService):
    """13. Equipment subset semantics -> selected exercises require only available equipment."""
    available = ["dumbbells", "bench"]
    req = WorkoutPlanGenerateRequest(
        trainingDaysPerWeek=3,
        environment="home",
        availableEquipment=available,
    )
    res = service.generate_plan(req)

    assert res.feasibilityCheckPassed is True
    for day in res.weeks[0].days:
        for ex in day.exercises:
            assert all(eq in available or eq == "bodyweight" for eq in ex.equipment), (
                f"Exercise {ex.name} requires {ex.equipment}, exceeding available {available}"
            )


def test_multi_equipment_failure_case(service: WorkoutPlanService):
    """14. Multi-equipment failure case -> exercise requiring [barbell, bench] is excluded when only [barbell] is available."""
    req = WorkoutPlanGenerateRequest(
        trainingDaysPerWeek=3,
        environment="gym",
        availableEquipment=["barbell"],  # Bench NOT available
    )
    res = service.generate_plan(req)

    assert res.feasibilityCheckPassed is True
    for day in res.weeks[0].days:
        for ex in day.exercises:
            assert "bench" not in ex.equipment


def test_environment_filtering(service: WorkoutPlanService):
    """15. Environment filtering -> outdoor environment excludes gym-only exercises."""
    req = WorkoutPlanGenerateRequest(
        trainingDaysPerWeek=2,
        environment="outdoor",
        availableEquipment=["bodyweight", "pull_up_bar"],
    )
    res = service.generate_plan(req)

    assert res.feasibilityCheckPassed is True
    for day in res.weeks[0].days:
        for ex in day.exercises:
            catalog_entry = CATALOG_BY_ID[ex.exerciseId]
            assert "outdoor" in catalog_entry.targetEnvironments or "anywhere" in catalog_entry.targetEnvironments


def test_explicit_exercise_exclusions(service: WorkoutPlanService):
    """16. Explicit exercise exclusions -> excluded exercise IDs are never selected."""
    excluded = ["ex_barbell_bench_press", "ex_barbell_squat", "ex_barbell_deadlift"]
    req = WorkoutPlanGenerateRequest(
        trainingDaysPerWeek=4,
        environment="gym",
        excludedExerciseIds=excluded,
    )
    res = service.generate_plan(req)

    assert res.feasibilityCheckPassed is True
    for day in res.weeks[0].days:
        for ex in day.exercises:
            assert ex.exerciseId not in excluded


# ============================================================================
# 17 to 19: Corrective Slot 0
# ============================================================================

def test_corrective_slot_0_valid_case(service: WorkoutPlanService):
    """17. Corrective Slot 0 valid case -> populated at Slot 0 when canonical CV source & valid issue provided."""
    req = WorkoutPlanGenerateRequest(
        trainingDaysPerWeek=3,
        environment="gym",
        correctiveSourceExerciseId="ex_squat",
        correctiveIssueId="knee_tracking_deviation",
    )
    res = service.generate_plan(req)

    assert res.feasibilityCheckPassed is True
    for day in res.weeks[0].days:
        slot0 = day.exercises[0]
        assert slot0.slotIndex == 0
        assert slot0.slotRole == ExerciseSlotRole.WARMUP_CORRECTIVE


def test_corrective_slot_0_omitted_case(service: WorkoutPlanService):
    """18. Corrective Slot 0 omitted case -> Slot 0 is omitted when no corrective parameters are supplied."""
    req = WorkoutPlanGenerateRequest(
        trainingDaysPerWeek=3,
        environment="gym",
        correctiveSourceExerciseId=None,
        correctiveIssueId=None,
    )
    res = service.generate_plan(req)

    assert res.feasibilityCheckPassed is True
    for day in res.weeks[0].days:
        roles = [ex.slotRole for ex in day.exercises]
        assert ExerciseSlotRole.WARMUP_CORRECTIVE not in roles
        assert day.exercises[0].slotIndex == 1


def test_invalid_corrective_parameters(service: WorkoutPlanService):
    """19. Invalid corrective parameters -> returns State B when corrective source is not a canonical CV exercise."""
    req = WorkoutPlanGenerateRequest(
        trainingDaysPerWeek=3,
        environment="gym",
        correctiveSourceExerciseId="ex_incline_dumbbell_press",  # Not canonical CV
        correctiveIssueId="knee_tracking_deviation",
    )
    res = service.generate_plan(req)

    assert res.feasibilityCheckPassed is False
    assert res.weeks == []
    assert any("canonical CV source" in diag for diag in res.diagnostics)


# ============================================================================
# 20 to 22: Diagnostic States (State B, State C, State D)
# ============================================================================

def test_state_b_missing_required_input(service: WorkoutPlanService):
    """20. State B missing required input -> returns State B when corrective source provided without issue."""
    req = WorkoutPlanGenerateRequest(
        trainingDaysPerWeek=3,
        correctiveSourceExerciseId="ex_squat",
        correctiveIssueId=None,  # Missing issue!
    )
    res = service.generate_plan(req)

    assert res.feasibilityCheckPassed is False
    assert res.weeks == []
    assert any("requires both" in diag for diag in res.diagnostics)


def test_state_c_conflicting_hard_constraints(service: WorkoutPlanService):
    """21. State C conflicting hard constraints -> returns State C when preferredSplit conflicts with trainingDays."""
    req = WorkoutPlanGenerateRequest(
        trainingDaysPerWeek=4,
        preferredSplit=WorkoutSplitType.PUSH_PULL_LEGS,  # PPL requires 6 days!
    )
    res = service.generate_plan(req)

    assert res.feasibilityCheckPassed is False
    assert res.weeks == []
    assert len(res.conflictingFilters) > 0
    assert any("incompatible" in diag for diag in res.diagnostics)


def test_state_d_catalog_shortfall(service: WorkoutPlanService):
    """22. State D catalog shortfall -> returns State D with exact diagnostics when a required slot cannot be filled."""
    # Exclude ALL compound movements in catalog so Slot 1 cannot be populated
    all_compounds = [
        ex.id for ex in CATALOG_BY_ID.values() if ex.exerciseType == "compound"
    ]
    req = WorkoutPlanGenerateRequest(
        trainingDaysPerWeek=1,
        environment="gym",
        excludedExerciseIds=all_compounds,
    )
    res = service.generate_plan(req)

    assert res.feasibilityCheckPassed is False
    assert res.weeks == []
    assert any("Catalog feasibility shortfall" in diag for diag in res.diagnostics)


# ============================================================================
# 23 to 25: Determinism & Bodyweight Fallback Guard
# ============================================================================

def test_deterministic_identical_request_ordering(service: WorkoutPlanService):
    """23. Deterministic identical request ordering -> byte-for-byte identical output and plan ID."""
    req1 = WorkoutPlanGenerateRequest(
        trainingDaysPerWeek=3,
        environment="gym",
        targetGoal="strength",
        fitnessLevel="intermediate",
    )
    req2 = WorkoutPlanGenerateRequest(
        trainingDaysPerWeek=3,
        environment="gym",
        targetGoal="strength",
        fitnessLevel="intermediate",
    )

    res1 = service.generate_plan(req1)
    res2 = service.generate_plan(req2)

    assert res1.planId == res2.planId
    assert res1.model_dump() == res2.model_dump()


def test_deterministic_plan_structure(service: WorkoutPlanService):
    """24. Deterministic plan structure -> multi-week structure matches duration and phases."""
    req = WorkoutPlanGenerateRequest(trainingDaysPerWeek=3, planDurationWeeks=8)
    res = service.generate_plan(req)

    assert res.feasibilityCheckPassed is True
    assert len(res.weeks) == 8
    # Week 1: Baseline Accumulation
    assert res.weeks[0].phaseLabel == "Baseline Accumulation"
    # Week 4: Deload & Consolidation
    assert res.weeks[3].phaseLabel == "Deload & Consolidation"
    # Week 5: Baseline Accumulation (Block 2)
    assert res.weeks[4].phaseLabel == "Baseline Accumulation"
    # Week 8: Deload & Consolidation (Block 2)
    assert res.weeks[7].phaseLabel == "Deload & Consolidation"


def test_no_fabricated_bodyweight_fallback(service: WorkoutPlanService):
    """25. No fabricated bodyweight fallback -> does not inject bodyweight exercises when equipment fails."""
    # User has only "barbell", no bodyweight allowed
    req = WorkoutPlanGenerateRequest(
        trainingDaysPerWeek=3,
        environment="gym",
        availableEquipment=["barbell"],
        excludedEquipment=["bodyweight"],
    )
    res = service.generate_plan(req)

    if res.feasibilityCheckPassed:
        for day in res.weeks[0].days:
            for ex in day.exercises:
                assert "bodyweight" not in ex.equipment


# ============================================================================
# 26 to 28: Dependency Audit & Whole-Plan Feasibility
# ============================================================================

def test_no_gemini_network_firestore_dependency():
    """26. No Gemini / network / Firestore dependency -> zero external/cloud imports in service."""
    import backend.app.services.workout_plan_service as wps_module

    source = open(wps_module.__file__, "r", encoding="utf-8").read()

    forbidden_tokens = [
        "google.generativeai",
        "google.cloud.firestore",
        "firebase_admin",
        "httpx",
        "requests",
        "urllib.request",
        "aiohttp",
    ]

    for token in forbidden_tokens:
        assert token not in source, f"Forbidden dependency '{token}' found in workout_plan_service.py"


def test_plan_level_feasibility_verification(service: WorkoutPlanService):
    """27. Plan-level feasibility verification -> validates all days and slots before returning State A."""
    req = WorkoutPlanGenerateRequest(trainingDaysPerWeek=5, environment="gym")
    res = service.generate_plan(req)

    assert res.feasibilityCheckPassed is True
    for day in res.weeks[0].days:
        assert len(day.exercises) >= 5
        assert day.totalSets > 0
        assert day.estimatedDurationMinutes > 0


def test_no_duplicate_exercise_ids_across_workout_day(service: WorkoutPlanService):
    """28. No duplicate exercise IDs across workout day -> exhaustive check across all 6 split configurations."""
    for days in range(1, 7):
        req = WorkoutPlanGenerateRequest(trainingDaysPerWeek=days, environment="gym")
        res = service.generate_plan(req)
        assert res.feasibilityCheckPassed is True
        for day in res.weeks[0].days:
            ids = [ex.exerciseId for ex in day.exercises]
            assert len(ids) == len(set(ids)), f"Duplicate exercises found in {day.dayLabel} ({days}-day split): {ids}"
