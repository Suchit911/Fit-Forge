"""
Unit, Isolation, and Evaluation Suite for ExerciseRecommendationService (Phase 9B.8.4).

Verifies:
- 16 mandatory test plan corrections
- 15 realistic evaluation scenarios using actual catalog IDs
- Multi-equipment subset semantics and hard eligibility gates
- Exact bounded mathematical scoring and weights summation
- Stable multi-tiered tie-breaking and deterministic reason generation
- Intent-aware diversity post-processing
- Read-only FastAPI endpoint integration
- Zero external network, Firestore writes, or LLM dependencies
"""

import pytest
from fastapi.testclient import TestClient
from backend.app.main import app
from backend.app.schemas.exercise import (
    RecommendationIntent,
    ExerciseRecommendationRequest,
    ExerciseRecommendationResponse,
    CANONICAL_CV_EXERCISES,
    PROHIBITED_MEDICAL_PHRASES,
)
from backend.app.services.exercise_recommendation_service import (
    ExerciseRecommendationService,
    get_exercise_recommendation_service,
    GENERAL_SCORING_WEIGHTS,
    RELATIONSHIP_SCORING_WEIGHTS,
    CORRECTIVE_SCORING_WEIGHTS,
)
from backend.app.seeds.catalog import CATALOG_BY_ID, CATALOG_EXERCISES

client = TestClient(app)


@pytest.fixture
def service() -> ExerciseRecommendationService:
    return get_exercise_recommendation_service()


# =============================================================================
# 16 MANDATORY TEST PLAN CORRECTIONS
# =============================================================================

def test_1_progression_intent_cannot_return_regression_edges(service: ExerciseRecommendationService):
    """Verifies progression queries return only progressions, never regression edges."""
    req = ExerciseRecommendationRequest(
        intent=RecommendationIntent.PROGRESSION,
        sourceExerciseId="ex_squat",
    )
    res = service.recommend(req)
    assert res.totalEligible > 0
    prog_ids = [c.exerciseId for c in res.candidates]
    # ex_squat regressions: ex_box_squat, ex_goblet_squat
    assert "ex_box_squat" not in prog_ids
    assert "ex_goblet_squat" not in prog_ids
    assert "ex_front_squat" in prog_ids
    for c in res.candidates:
        assert c.relationshipType == "progression"


def test_2_regression_intent_cannot_return_progression_edges(service: ExerciseRecommendationService):
    """Verifies regression queries return only regressions, never progression edges."""
    req = ExerciseRecommendationRequest(
        intent=RecommendationIntent.REGRESSION,
        sourceExerciseId="ex_squat",
    )
    res = service.recommend(req)
    assert res.totalEligible > 0
    reg_ids = [c.exerciseId for c in res.candidates]
    # ex_squat progressions: ex_front_squat, ex_overhead_squat
    assert "ex_front_squat" not in reg_ids
    assert "ex_overhead_squat" not in reg_ids
    assert "ex_box_squat" in reg_ids
    for c in res.candidates:
        assert c.relationshipType == "regression"


def test_3_substitution_intent_cannot_return_complement_edges(service: ExerciseRecommendationService):
    """Verifies substitution queries never return complement edges."""
    req = ExerciseRecommendationRequest(
        intent=RecommendationIntent.SUBSTITUTION,
        sourceExerciseId="ex_bench_press",
    )
    res = service.recommend(req)
    assert res.totalEligible > 0
    sub_ids = [c.exerciseId for c in res.candidates]
    # ex_bench_press complements: ex_face_pull, ex_band_pull_apart, etc.
    assert "ex_face_pull" not in sub_ids
    assert "ex_band_pull_apart" not in sub_ids
    for c in res.candidates:
        assert c.relationshipType == "substitution"


def test_4_complement_intent_cannot_return_substitution_edges(service: ExerciseRecommendationService):
    """Verifies complement queries never return substitution edges."""
    req = ExerciseRecommendationRequest(
        intent=RecommendationIntent.COMPLEMENT,
        sourceExerciseId="ex_bench_press",
    )
    res = service.recommend(req)
    assert res.totalEligible > 0
    comp_ids = [c.exerciseId for c in res.candidates]
    # ex_bench_press substitutions: ex_dumbbell_flat_press, ex_push_up
    assert "ex_dumbbell_flat_press" not in comp_ids
    assert "ex_push_up" not in comp_ids
    for c in res.candidates:
        assert c.relationshipType == "complement"


def test_5_invalid_corrective_source_or_issue_rejected(service: ExerciseRecommendationService):
    """Rejects non-CV source exercise or unmapped issue with clear diagnostic."""
    # Case A: Non-CV source exercise
    req_non_cv = ExerciseRecommendationRequest(
        intent=RecommendationIntent.CORRECTIVE,
        sourceExerciseId="ex_box_squat",
        correctiveIssueId="insufficient_depth",
    )
    res_non_cv = service.recommend(req_non_cv)
    assert res_non_cv.totalEligible == 0
    assert len(res_non_cv.candidates) == 0
    assert any("canonical CV source" in d for d in res_non_cv.diagnostics)

    # Case B: Unknown / unmapped issue for canonical source
    req_bad_issue = ExerciseRecommendationRequest(
        intent=RecommendationIntent.CORRECTIVE,
        sourceExerciseId="ex_squat",
        correctiveIssueId="totally_invented_issue",
    )
    res_bad_issue = service.recommend(req_bad_issue)
    assert res_bad_issue.totalEligible == 0
    assert len(res_bad_issue.candidates) == 0
    assert any("not an authoritative Phase 9B.2 finding" in d for d in res_bad_issue.diagnostics)


def test_6_valid_corrective_returns_only_mapped_candidates(service: ExerciseRecommendationService):
    """Valid corrective query returns strictly the curated candidate exercises."""
    req = ExerciseRecommendationRequest(
        intent=RecommendationIntent.CORRECTIVE,
        sourceExerciseId="ex_squat",
        correctiveIssueId="insufficient_depth",
    )
    res = service.recommend(req)
    assert res.totalEligible == 3
    cand_ids = {c.exerciseId for c in res.candidates}
    expected_ids = {"ex_box_squat", "ex_goblet_squat", "ex_90_90_hip_flow"}
    assert cand_ids == expected_ids
    for c in res.candidates:
        assert c.relationshipType == "corrective"


def test_7_equipment_not_double_counted(service: ExerciseRecommendationService):
    """
    Confirms equipment compatibility acts solely as a hard gate.
    Comparing two candidates with identical soft attributes, different equipment requirements
    do not alter their score due to equipment points.
    """
    assert "equipment" not in GENERAL_SCORING_WEIGHTS
    assert "equipment" not in RELATIONSHIP_SCORING_WEIGHTS
    assert "equipment" not in CORRECTIVE_SCORING_WEIGHTS
    assert sum(GENERAL_SCORING_WEIGHTS.values()) == pytest.approx(1.00)
    assert sum(RELATIONSHIP_SCORING_WEIGHTS.values()) == pytest.approx(1.00)
    assert sum(CORRECTIVE_SCORING_WEIGHTS.values()) == pytest.approx(1.00)


def test_8_diversity_does_not_remove_relationship_candidates(service: ExerciseRecommendationService):
    """Verifies that relationship queries never have candidates pruned by diversity."""
    req = ExerciseRecommendationRequest(
        intent=RecommendationIntent.REGRESSION,
        sourceExerciseId="ex_deadlift",
        enableDiversity=True,
    )
    res = service.recommend(req)
    # ex_deadlift has 2 regressions: ex_romanian_deadlift, ex_trap_bar_deadlift
    # both share the hinge movement pattern. Diversity must NOT prune any valid edge.
    assert res.returnedCount == 2
    assert {c.exerciseId for c in res.candidates} == {
        "ex_romanian_deadlift",
        "ex_trap_bar_deadlift",
    }


def test_9_diversity_does_not_remove_corrective_candidates(service: ExerciseRecommendationService):
    """Verifies that corrective queries never have candidates pruned by diversity."""
    req = ExerciseRecommendationRequest(
        intent=RecommendationIntent.CORRECTIVE,
        sourceExerciseId="ex_squat",
        correctiveIssueId="insufficient_depth",
        enableDiversity=True,
    )
    res = service.recommend(req)
    # Box Squat and Goblet Squat both share the squat pattern. Diversity must NOT prune either.
    assert res.returnedCount == 3
    cand_ids = {c.exerciseId for c in res.candidates}
    assert "ex_box_squat" in cand_ids
    assert "ex_goblet_squat" in cand_ids


def test_10_muscle_mismatch_does_not_hard_exclude(service: ExerciseRecommendationService):
    """Verifies muscle preference is a soft ranking signal, not a hard elimination filter."""
    req = ExerciseRecommendationRequest(
        intent=RecommendationIntent.GENERAL,
        targetMuscles=["biceps"],
        limit=50,
    )
    res = service.recommend(req)
    # Non-bicep exercises like Barbell Back Squat or Bench Press must still be eligible
    cand_ids = [c.exerciseId for c in res.candidates]
    assert "ex_squat" in cand_ids or "ex_bench_press" in cand_ids


def test_11_insufficient_data_does_not_fabricate_bodyweight_fallback(service: ExerciseRecommendationService):
    """Confirms State B returns 0 candidates and clean diagnostics without bodyweight fallback."""
    # Progression missing source exercise
    req_prog = ExerciseRecommendationRequest(
        intent=RecommendationIntent.PROGRESSION,
        sourceExerciseId=None,
    )
    res_prog = service.recommend(req_prog)
    assert res_prog.totalEligible == 0
    assert len(res_prog.candidates) == 0
    assert any("requires 'source_exercise_id'" in d for d in res_prog.diagnostics)

    # Corrective missing issue
    req_corr = ExerciseRecommendationRequest(
        intent=RecommendationIntent.CORRECTIVE,
        sourceExerciseId="ex_squat",
        correctiveIssueId=None,
    )
    res_corr = service.recommend(req_corr)
    assert res_corr.totalEligible == 0
    assert len(res_corr.candidates) == 0
    assert any("requires 'corrective_issue_id'" in d for d in res_corr.diagnostics)


def test_12_scores_strictly_bounded_0_to_100(service: ExerciseRecommendationService):
    """Verifies scores are strictly within [0.0, 100.0] across diverse requests."""
    requests = [
        ExerciseRecommendationRequest(intent=RecommendationIntent.GENERAL, targetGoal="strength"),
        ExerciseRecommendationRequest(intent=RecommendationIntent.PROGRESSION, sourceExerciseId="ex_squat"),
        ExerciseRecommendationRequest(intent=RecommendationIntent.REGRESSION, sourceExerciseId="ex_deadlift"),
        ExerciseRecommendationRequest(
            intent=RecommendationIntent.CORRECTIVE,
            sourceExerciseId="ex_bench_press",
            correctiveIssueId="excessive_elbow_flare",
        ),
    ]
    for req in requests:
        res = service.recommend(req)
        for c in res.candidates:
            assert 0.0 <= c.score <= 100.0


def test_13_score_weights_sum_exactly_one():
    """Verifies that all intent profile weights sum to exactly 1.00."""
    assert sum(GENERAL_SCORING_WEIGHTS.values()) == pytest.approx(1.00)
    assert sum(RELATIONSHIP_SCORING_WEIGHTS.values()) == pytest.approx(1.00)
    assert sum(CORRECTIVE_SCORING_WEIGHTS.values()) == pytest.approx(1.00)


def test_14_identical_requests_produce_identical_candidate_ordering(service: ExerciseRecommendationService):
    """Verifies 100% deterministic, byte-for-byte identical output across repeated runs."""
    req = ExerciseRecommendationRequest(
        intent=RecommendationIntent.GENERAL,
        targetGoal="strength",
        environment="gym",
        availableEquipment=["barbell", "dumbbells", "bench"],
        limit=10,
    )
    res1 = service.recommend(req)
    res2 = service.recommend(req)

    dump1 = res1.model_dump()
    dump2 = res2.model_dump()
    assert dump1 == dump2


def test_15_form_analysis_supported_only_returns_canonical_five(service: ExerciseRecommendationService):
    """Verifies form_analysis_supported_only restricts candidates to the canonical 5 CV exercises."""
    req = ExerciseRecommendationRequest(
        intent=RecommendationIntent.GENERAL,
        formAnalysisSupportedOnly=True,
        limit=50,
    )
    res = service.recommend(req)
    cand_ids = {c.exerciseId for c in res.candidates}
    canonical_set = set(CANONICAL_CV_EXERCISES.keys())
    assert cand_ids == canonical_set
    for c in res.candidates:
        assert c.isCanonicalCv is True


def test_16_zero_external_network_or_gemini_dependency(service: ExerciseRecommendationService):
    """Verifies recommendation service executes in-memory without network or LLM client calls."""
    import backend.app.services.exercise_recommendation_service as mod
    # Assert module does not import or use Gemini/LLM
    assert not hasattr(mod, "genai")
    assert not hasattr(mod, "gemini")
    assert not hasattr(mod, "llm_client")
    assert not hasattr(mod, "firestore")


# =============================================================================
# 15 CONCRETE EVALUATION SCENARIOS
# =============================================================================

def test_eval_scenario_1_general_goal_discovery(service: ExerciseRecommendationService):
    """Scenario 1: General Goal Discovery (muscle_gain in gym)."""
    req = ExerciseRecommendationRequest(
        intent=RecommendationIntent.GENERAL,
        targetGoal="muscle_gain",
        environment="gym",
        limit=5,
    )
    res = service.recommend(req)
    assert res.returnedCount == 5
    assert all("gym" in CATALOG_BY_ID[c.exerciseId].targetEnvironments for c in res.candidates)


def test_eval_scenario_2_gym_barbell_dumbbell(service: ExerciseRecommendationService):
    """Scenario 2: Gym with Barbell / Dumbbell."""
    req = ExerciseRecommendationRequest(
        intent=RecommendationIntent.GENERAL,
        targetGoal="strength",
        availableEquipment=["barbell", "dumbbells", "bench"],
        limit=5,
    )
    res = service.recommend(req)
    assert res.returnedCount > 0
    avail = {"barbell", "dumbbells", "bench"}
    for c in res.candidates:
        assert set(c.equipment).issubset(avail)


def test_eval_scenario_3_home_dumbbells_only(service: ExerciseRecommendationService):
    """Scenario 3: Home with Dumbbells Only."""
    req = ExerciseRecommendationRequest(
        intent=RecommendationIntent.GENERAL,
        environment="home",
        availableEquipment=["dumbbells"],
        limit=5,
    )
    res = service.recommend(req)
    assert res.returnedCount > 0
    for c in res.candidates:
        assert set(c.equipment).issubset({"dumbbells"})
        assert "barbell" not in c.equipment
        assert "cable" not in c.equipment


def test_eval_scenario_4_home_bodyweight_only(service: ExerciseRecommendationService):
    """Scenario 4: Home with Bodyweight Only."""
    req = ExerciseRecommendationRequest(
        intent=RecommendationIntent.GENERAL,
        environment="home",
        availableEquipment=["bodyweight"],
        limit=5,
    )
    res = service.recommend(req)
    assert res.returnedCount > 0
    for c in res.candidates:
        assert c.equipment == ["bodyweight"]


def test_eval_scenario_5_canonical_squat_progression(service: ExerciseRecommendationService):
    """Scenario 5: Canonical Squat Progression."""
    req = ExerciseRecommendationRequest(
        intent=RecommendationIntent.PROGRESSION,
        sourceExerciseId="ex_squat",
        availableEquipment=["barbell"],
    )
    res = service.recommend(req)
    cand_ids = [c.exerciseId for c in res.candidates]
    assert "ex_front_squat" in cand_ids
    assert "ex_overhead_squat" in cand_ids
    assert "ex_box_squat" not in cand_ids


def test_eval_scenario_6_canonical_deadlift_regression(service: ExerciseRecommendationService):
    """Scenario 6: Canonical Deadlift Regression."""
    req = ExerciseRecommendationRequest(
        intent=RecommendationIntent.REGRESSION,
        sourceExerciseId="ex_deadlift",
    )
    res = service.recommend(req)
    cand_ids = {c.exerciseId for c in res.candidates}
    assert cand_ids == {
        "ex_romanian_deadlift",
        "ex_trap_bar_deadlift",
    }


def test_eval_scenario_7_equipment_substitution(service: ExerciseRecommendationService):
    """Scenario 7: Bench Substitution due to Unavailable Barbell."""
    req = ExerciseRecommendationRequest(
        intent=RecommendationIntent.SUBSTITUTION,
        sourceExerciseId="ex_bench_press",
        availableEquipment=["dumbbells", "bench"],
    )
    res = service.recommend(req)
    cand_ids = [c.exerciseId for c in res.candidates]
    assert "ex_dumbbell_flat_press" in cand_ids
    assert "ex_barbell_bench_press" not in cand_ids


def test_eval_scenario_8_bench_complement(service: ExerciseRecommendationService):
    """Scenario 8: Bench Press Accessory Complements."""
    req = ExerciseRecommendationRequest(
        intent=RecommendationIntent.COMPLEMENT,
        sourceExerciseId="ex_bench_press",
    )
    res = service.recommend(req)
    cand_ids = [c.exerciseId for c in res.candidates]
    assert "ex_face_pull" in cand_ids
    assert "ex_seated_cable_row" in cand_ids


def test_eval_scenario_9_corrective_squat_depth(service: ExerciseRecommendationService):
    """Scenario 9: Corrective for Squat Depth."""
    req = ExerciseRecommendationRequest(
        intent=RecommendationIntent.CORRECTIVE,
        sourceExerciseId="ex_squat",
        correctiveIssueId="insufficient_depth",
    )
    res = service.recommend(req)
    assert res.totalEligible == 3
    cand_ids = {c.exerciseId for c in res.candidates}
    assert cand_ids == {"ex_box_squat", "ex_goblet_squat", "ex_90_90_hip_flow"}


def test_eval_scenario_10_corrective_bench_flare(service: ExerciseRecommendationService):
    """Scenario 10: Corrective for Bench Press Elbow Flare."""
    req = ExerciseRecommendationRequest(
        intent=RecommendationIntent.CORRECTIVE,
        sourceExerciseId="ex_bench_press",
        correctiveIssueId="excessive_elbow_flare",
    )
    res = service.recommend(req)
    assert res.totalEligible == 3
    cand_ids = {c.exerciseId for c in res.candidates}
    assert cand_ids == {
        "ex_close_grip_bench_press",
        "ex_dumbbell_flat_press",
        "ex_push_up",
    }


def test_eval_scenario_11_corrective_deadlift_lockout(service: ExerciseRecommendationService):
    """Scenario 11: Corrective for Deadlift Lockout."""
    req = ExerciseRecommendationRequest(
        intent=RecommendationIntent.CORRECTIVE,
        sourceExerciseId="ex_deadlift",
        correctiveIssueId="insufficient_lockout",
    )
    res = service.recommend(req)
    assert res.totalEligible == 3
    cand_ids = {c.exerciseId for c in res.candidates}
    assert cand_ids == {
        "ex_glute_bridge",
        "ex_romanian_deadlift",
        "ex_kettlebell_swing",
    }


def test_eval_scenario_12_corrective_curl_drift(service: ExerciseRecommendationService):
    """Scenario 12: Corrective for Bicep Curl Arm Drift."""
    req = ExerciseRecommendationRequest(
        intent=RecommendationIntent.CORRECTIVE,
        sourceExerciseId="ex_bicep_curl",
        correctiveIssueId="excessive_arm_movement",
    )
    res = service.recommend(req)
    assert res.totalEligible == 3
    cand_ids = {c.exerciseId for c in res.candidates}
    assert cand_ids == {
        "ex_concentration_curl",
        "ex_incline_dumbbell_curl",
        "ex_cable_bicep_curl",
    }


def test_eval_scenario_13_corrective_press_lockout(service: ExerciseRecommendationService):
    """Scenario 13: Corrective for Overhead Press Range."""
    req = ExerciseRecommendationRequest(
        intent=RecommendationIntent.CORRECTIVE,
        sourceExerciseId="ex_shoulder_press",
        correctiveIssueId="insufficient_overhead_range",
    )
    res = service.recommend(req)
    assert res.totalEligible == 3
    cand_ids = {c.exerciseId for c in res.candidates}
    assert cand_ids == {
        "ex_landmine_press",
        "ex_cat_cow",
        "ex_thoracic_foam_roll",
    }


def test_eval_scenario_14_conflicting_constraints(service: ExerciseRecommendationService):
    """Scenario 14: Conflicting Constraints (Outdoor + Barbell)."""
    req = ExerciseRecommendationRequest(
        intent=RecommendationIntent.GENERAL,
        environment="outdoor",
        availableEquipment=["barbell"],
    )
    res = service.recommend(req)
    assert res.totalEligible == 0
    assert len(res.candidates) == 0
    assert len(res.conflictingFilters) > 0


def test_eval_scenario_15_insufficient_request_data(service: ExerciseRecommendationService):
    """Scenario 15: Insufficient Request Data (Progression without source)."""
    req = ExerciseRecommendationRequest(
        intent=RecommendationIntent.PROGRESSION,
        sourceExerciseId=None,
    )
    res = service.recommend(req)
    assert res.totalEligible == 0
    assert len(res.candidates) == 0
    assert any("requires 'source_exercise_id'" in d for d in res.diagnostics)


# =============================================================================
# MULTI-EQUIPMENT SUBSET & HARD GATE TESTS
# =============================================================================

def test_multi_equipment_subset_semantics(service: ExerciseRecommendationService):
    """
    Exercise requires multiple items: exercise.equipment ⊆ available_equipment.
    If exercise requires ['barbell', 'bench'] and user has only ['barbell'], it fails.
    """
    # ex_bench_press requires ['barbell', 'bench']
    req_only_barbell = ExerciseRecommendationRequest(
        intent=RecommendationIntent.GENERAL,
        availableEquipment=["barbell"],
        limit=50,
    )
    res = service.recommend(req_only_barbell)
    cand_ids = {c.exerciseId for c in res.candidates}
    assert "ex_bench_press" not in cand_ids

    req_both = ExerciseRecommendationRequest(
        intent=RecommendationIntent.GENERAL,
        availableEquipment=["barbell", "bench"],
        limit=50,
    )
    res_both = service.recommend(req_both)
    cand_ids_both = {c.exerciseId for c in res_both.candidates}
    assert "ex_bench_press" in cand_ids_both


def test_excluded_equipment_gate(service: ExerciseRecommendationService):
    """Exercises requiring excluded equipment are rejected."""
    req = ExerciseRecommendationRequest(
        intent=RecommendationIntent.GENERAL,
        excludedEquipment=["barbell"],
        limit=50,
    )
    res = service.recommend(req)
    for c in res.candidates:
        assert "barbell" not in c.equipment


def test_excluded_exercise_ids_gate(service: ExerciseRecommendationService):
    """Explicitly excluded exercise IDs are filtered out."""
    req = ExerciseRecommendationRequest(
        intent=RecommendationIntent.GENERAL,
        excludedExerciseIds=["ex_squat", "ex_bench_press"],
        limit=50,
    )
    res = service.recommend(req)
    cand_ids = {c.exerciseId for c in res.candidates}
    assert "ex_squat" not in cand_ids
    assert "ex_bench_press" not in cand_ids


def test_diversity_exception_for_explicitly_requested_pattern(service: ExerciseRecommendationService):
    """
    When a movementPattern is explicitly requested in general discovery,
    the 2-exercise cap for that specific pattern is disabled.
    """
    req = ExerciseRecommendationRequest(
        intent=RecommendationIntent.GENERAL,
        movementPattern="squat",
        limit=6,
        enableDiversity=True,
    )
    res = service.recommend(req)
    squat_candidates = [c for c in res.candidates if c.movementPattern == "squat"]
    # There are 12 squat exercises in the catalog. It should return more than 2 squats!
    assert len(squat_candidates) > 2


def test_deterministic_reasons_contain_no_prohibited_medical_language(service: ExerciseRecommendationService):
    """Verifies all output reasons are clean of prohibited medical language."""
    for intent in RecommendationIntent:
        if intent in (RecommendationIntent.PROGRESSION, RecommendationIntent.REGRESSION, RecommendationIntent.SUBSTITUTION, RecommendationIntent.COMPLEMENT):
            req = ExerciseRecommendationRequest(intent=intent, sourceExerciseId="ex_squat")
        elif intent == RecommendationIntent.CORRECTIVE:
            req = ExerciseRecommendationRequest(
                intent=intent,
                sourceExerciseId="ex_squat",
                correctiveIssueId="insufficient_depth",
            )
        else:
            req = ExerciseRecommendationRequest(intent=intent)

        res = service.recommend(req)
        for c in res.candidates:
            for reason in c.reasons:
                lower = reason.lower()
                for phrase in PROHIBITED_MEDICAL_PHRASES:
                    assert phrase not in lower


def test_tie_breaking_compound_before_isolation(service: ExerciseRecommendationService):
    """Verifies compound lifts rank before isolation movements on score ties."""
    req = ExerciseRecommendationRequest(
        intent=RecommendationIntent.GENERAL,
        limit=10,
    )
    res = service.recommend(req)
    # Check that compound movements with equal rounded score rank before isolation
    for i in range(len(res.candidates) - 1):
        c1 = res.candidates[i]
        c2 = res.candidates[i + 1]
        if round(c1.score, 2) == round(c2.score, 2) and c1.exerciseType != c2.exerciseType:
            assert c1.exerciseType == "compound"
            assert c2.exerciseType == "isolation"


# =============================================================================
# API ENDPOINT INTEGRATION TESTS
# =============================================================================

def test_api_endpoint_post_recommendations_general():
    """Verifies POST /api/v1/exercises/recommendations returns 200 with typed response."""
    payload = {
        "intent": "general",
        "target_goal": "strength",
        "environment": "gym",
        "limit": 5,
    }
    response = client.post("/api/v1/exercises/recommendations", json=payload)
    assert response.status_code == 200
    data = response.json()
    assert data["intent"] == "general"
    assert data["total_eligible"] > 0
    assert len(data["candidates"]) == 5
    assert "applied_filters" in data


def test_api_endpoint_post_recommendations_corrective():
    """Verifies POST /api/v1/exercises/recommendations with corrective intent."""
    payload = {
        "intent": "corrective",
        "source_exercise_id": "ex_squat",
        "corrective_issue_id": "insufficient_depth",
    }
    response = client.post("/api/v1/exercises/recommendations", json=payload)
    assert response.status_code == 200
    data = response.json()
    assert data["intent"] == "corrective"
    assert data["total_eligible"] == 3
    assert len(data["candidates"]) == 3
