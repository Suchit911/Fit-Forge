"""
Authoritative Test Suite for Exercise Relationships & Corrective Guidance (Phase 9B.8.3).

Verifies Requirements A through Y:
- A: Relationship schema validation
- B: No dangling references across the catalog
- C: No self-references in any relationship
- D: No duplicate relationship IDs within any type
- E: Relationship semantic validity
- F: Deterministic ordering across multiple invocations
- G: Progression retrieval (compound and isolation)
- H: Regression retrieval (simpler/accessible variants)
- I: Substitution retrieval (movement pattern & equipment alternatives)
- J: Complement retrieval (accessory and supporting patterns)
- K: Related-exercise aggregation in ExerciseRelationshipsResponse
- L: Corrective mapping from observable technique issues to candidates
- M: Unknown exercise handling (explicit 404 / KeyError)
- N: Unknown issue handling (explicit 404 / KeyError)
- O: Empty relationship behavior (explicit empty list, no hallucinations)
- P: Candidate deduplication preserving strongest relationship classification
- Q: Catalog graph statistics (edges, degrees, distribution)
- R: Phase 3 ExerciseSchema compatibility
- S: Exactly 5 canonical CV exercises remain unchanged
- T: Invalid relationship data fails validation clearly
- U: Normalized issue IDs map only to actual Phase 9B.2 heuristics
- V: Corrective candidates exist in 100-exercise catalog
- W: Orphan definition implemented strictly (degree 0 incoming and outgoing)
- X: Valid substitution cycles preserved without false rejection
- Y: No prohibited medical or clinical claims across all rationales and reasons
"""

import pytest
from fastapi.testclient import TestClient
from pydantic import ValidationError

from backend.app.main import app
from backend.app.schemas.exercise import (
    ExerciseRelationshipType,
    ExerciseRelationshipNode,
    CorrectiveGuidanceCandidate,
    ExerciseRelationshipsResponse,
    CatalogGraphStatistics,
    CANONICAL_CV_EXERCISES,
    PROHIBITED_MEDICAL_PHRASES,
)
from backend.app.seeds.catalog import (
    CATALOG_EXERCISES,
    CATALOG_BY_ID,
)
from backend.app.seeds.corrective_mappings import (
    RAW_CORRECTIVE_MAPPINGS,
    HEURISTIC_NAME_TO_ISSUE_ID,
    ISSUE_ID_TO_HEURISTIC_NAME,
)
from backend.app.services.exercise_relationship_service import (
    ExerciseRelationshipService,
    get_exercise_relationship_service,
    RELATIONSHIP_PRECEDENCE,
)
from backend.app.services.form_heuristics import STANDARD_HEURISTIC_CONFIGS


@pytest.fixture
def client():
    return TestClient(app)


@pytest.fixture
def service():
    return get_exercise_relationship_service()


# =============================================================================
# A. Relationship schema validation
# =============================================================================

def test_a_relationship_schema_validation():
    """Validates that ExerciseRelationshipNode validates fields and rejects invalid types."""
    valid_node = ExerciseRelationshipNode(
        exercise_id="ex_box_squat",
        name="Barbell Box Squat",
        relationship_type="regression",
        movement_pattern="squat",
        difficulty="beginner",
        equipment=["barbell"],
        primary_muscles=["quadriceps", "glutes"],
        rationale="Provides a defined depth target for practicing controlled depth.",
        priority=1,
    )
    assert valid_node.exerciseId == "ex_box_squat"
    assert valid_node.relationshipType == "regression"

    # Reject invalid relationship type
    with pytest.raises(ValidationError):
        ExerciseRelationshipNode(
            exercise_id="ex_box_squat",
            name="Barbell Box Squat",
            relationship_type="invalid_type",  # Not in Literal
            movement_pattern="squat",
            difficulty="beginner",
            equipment=["barbell"],
            primary_muscles=["quadriceps"],
            rationale="Test",
        )


# =============================================================================
# B. No dangling references
# =============================================================================

def test_b_no_dangling_references():
    """Verifies that every relationship target across all 100 exercises exists in CATALOG_BY_ID."""
    for ex in CATALOG_EXERCISES:
        for rel_name, target_list in [
            ("progressions", ex.progressions),
            ("regressions", ex.regressions),
            ("substitutions", ex.substitutions),
            ("complementaryExercises", ex.complementaryExercises),
        ]:
            for target_id in target_list:
                assert target_id in CATALOG_BY_ID, (
                    f"Dangling reference: Exercise '{ex.id}' references '{target_id}' in '{rel_name}'."
                )


# =============================================================================
# C. No self references
# =============================================================================

def test_c_no_self_references():
    """Verifies that no exercise references itself in any relationship array."""
    for ex in CATALOG_EXERCISES:
        for rel_name, target_list in [
            ("progressions", ex.progressions),
            ("regressions", ex.regressions),
            ("substitutions", ex.substitutions),
            ("complementaryExercises", ex.complementaryExercises),
        ]:
            assert ex.id not in target_list, (
                f"Self-reference detected: Exercise '{ex.id}' references itself in '{rel_name}'."
            )


# =============================================================================
# D. No duplicate relationship IDs
# =============================================================================

def test_d_no_duplicate_relationship_ids():
    """Verifies that within each relationship array, there are no duplicate target IDs."""
    for ex in CATALOG_EXERCISES:
        for rel_name, target_list in [
            ("progressions", ex.progressions),
            ("regressions", ex.regressions),
            ("substitutions", ex.substitutions),
            ("complementaryExercises", ex.complementaryExercises),
        ]:
            assert len(target_list) == len(set(target_list)), (
                f"Duplicate target IDs found in '{rel_name}' of exercise '{ex.id}': {target_list}"
            )


# =============================================================================
# E. Relationship semantic validity
# =============================================================================

def test_e_relationship_semantic_validity(service):
    """Verifies that progressions, regressions, and substitutions match expected biomechanical relationships."""
    # ex_squat regressions should include simpler or boxed squatting variants
    squat_regs = [n.exerciseId for n in service.get_regressions("ex_squat")]
    assert "ex_box_squat" in squat_regs or "ex_goblet_squat" in squat_regs

    # ex_push_up progressions should include harder push-up variations or dips
    pushup_progs = [n.exerciseId for n in service.get_progressions("ex_push_up")]
    assert any(p in pushup_progs for p in ["ex_diamond_push_up", "ex_decline_push_up", "ex_handstand_push_up"])

    # ex_bench_press substitutions should be horizontal pushing patterns
    bench_subs = service.get_substitutions("ex_bench_press")
    for s in bench_subs:
        target_ex = CATALOG_BY_ID[s.exerciseId]
        assert target_ex.movementPattern in ("horizontal_push", "isolation")


# =============================================================================
# F. Deterministic ordering
# =============================================================================

def test_f_deterministic_ordering(service):
    """Verifies that multiple repeated calls produce 100% byte-for-byte identical ordering."""
    test_ids = ["ex_squat", "ex_bench_press", "ex_deadlift", "ex_pull_up", "ex_plank"]
    # ex_plank in catalog is ex_front_plank
    valid_ids = ["ex_squat", "ex_bench_press", "ex_deadlift", "ex_front_plank", "ex_pull_up"]

    for eid in valid_ids:
        call1 = [n.exerciseId for n in service.get_deduplicated_candidates(eid)]
        call2 = [n.exerciseId for n in service.get_deduplicated_candidates(eid)]
        call3 = [n.exerciseId for n in service.get_deduplicated_candidates(eid)]
        assert call1 == call2 == call3, f"Non-deterministic candidate ordering for '{eid}'"


# =============================================================================
# G. Progression retrieval
# =============================================================================

def test_g_progression_retrieval(service):
    """Verifies retrieval of harder variations."""
    progs = service.get_progressions("ex_squat")
    assert len(progs) > 0
    assert all(p.relationshipType == "progression" for p in progs)
    prog_ids = [p.exerciseId for p in progs]
    assert "ex_front_squat" in prog_ids or "ex_overhead_squat" in prog_ids


# =============================================================================
# H. Regression retrieval
# =============================================================================

def test_h_regression_retrieval(service):
    """Verifies retrieval of simpler/more accessible variations."""
    regs = service.get_regressions("ex_deadlift")
    assert len(regs) > 0
    assert all(r.relationshipType == "regression" for r in regs)
    reg_ids = [r.exerciseId for r in regs]
    assert any(rid in reg_ids for rid in ["ex_romanian_deadlift", "ex_kettlebell_deadlift", "ex_trap_bar_deadlift"])


# =============================================================================
# I. Substitution retrieval
# =============================================================================

def test_i_substitution_retrieval(service):
    """Verifies retrieval of viable movement substitutes."""
    subs = service.get_substitutions("ex_barbell_hip_thrust")
    assert len(subs) > 0
    assert all(s.relationshipType == "substitution" for s in subs)
    sub_ids = [s.exerciseId for s in subs]
    assert "ex_romanian_deadlift" in sub_ids or "ex_kettlebell_deadlift" in sub_ids

    bench_subs = [s.exerciseId for s in service.get_substitutions("ex_bench_press")]
    assert "ex_dumbbell_flat_press" in bench_subs or "ex_push_up" in bench_subs


# =============================================================================
# J. Complement retrieval
# =============================================================================

def test_j_complement_retrieval(service):
    """Verifies retrieval of supporting/accessory movements."""
    comps = service.get_complements("ex_bench_press")
    assert len(comps) > 0
    assert all(c.relationshipType == "complement" for c in comps)
    comp_ids = [c.exerciseId for c in comps]
    # Upper back, rear delts, or rotator cuff support horizontal pressing
    assert any(cid in comp_ids for cid in ["ex_face_pull", "ex_band_pull_apart", "ex_overhead_dumbbell_tricep_extension"])


# =============================================================================
# K. Related-exercise aggregation
# =============================================================================

def test_k_related_exercise_aggregation(service):
    """Verifies aggregation into ExerciseRelationshipsResponse."""
    response = service.get_related_exercises("ex_squat")
    assert isinstance(response, ExerciseRelationshipsResponse)
    assert response.sourceExerciseId == "ex_squat"
    assert response.sourceExerciseName == "Barbell Back Squat"
    assert len(response.progressions) > 0
    assert len(response.regressions) > 0
    assert len(response.substitutions) > 0
    assert len(response.complements) > 0
    assert len(response.correctives) > 0
    assert len(response.deduplicatedCandidates) > 0
    assert response.totalRelationships == (
        len(response.progressions)
        + len(response.regressions)
        + len(response.substitutions)
        + len(response.complements)
        + len(response.correctives)
    )


# =============================================================================
# L. Corrective mapping
# =============================================================================

def test_l_corrective_mapping(service):
    """Verifies corrective exercise lookup for observed form issues across all 5 CV exercises."""
    cv_exercises = ["ex_squat", "ex_bench_press", "ex_deadlift", "ex_bicep_curl", "ex_shoulder_press"]
    for eid in cv_exercises:
        candidates = service.get_corrective_candidates(eid)
        assert len(candidates) > 0, f"Expected corrective candidates for CV exercise '{eid}'"
        for cand in candidates:
            assert cand.sourceExerciseId == eid
            assert len(cand.candidateExercises) > 0
            # Test that querying by issueId works
            queried_by_issue = service.get_corrective_exercises(eid, cand.issueId)
            assert len(queried_by_issue) > 0
            # Test that querying by heuristicName works
            queried_by_heuristic = service.get_corrective_exercises(eid, cand.heuristicName)
            assert len(queried_by_heuristic) > 0
            assert [c.exerciseId for c in queried_by_issue] == [c.exerciseId for c in queried_by_heuristic]


# =============================================================================
# M. Unknown exercise handling
# =============================================================================

def test_m_unknown_exercise_handling(service, client):
    """Verifies that unknown exercise ID raises KeyError in service and 404 in API."""
    with pytest.raises(KeyError) as exc_info:
        service.get_progressions("ex_nonexistent_xyz")
    assert "was not found" in str(exc_info.value)

    res = client.get("/api/v1/exercises/relationships/ex_nonexistent_xyz")
    assert res.status_code == 404
    assert "was not found" in res.json()["detail"]


# =============================================================================
# N. Unknown issue handling
# =============================================================================

def test_n_unknown_issue_handling(service, client):
    """Verifies that unknown issue ID raises KeyError in service and 404 in API."""
    with pytest.raises(KeyError) as exc_info:
        service.get_corrective_exercises("ex_squat", "unknown_technique_issue")
    assert "was not found" in str(exc_info.value)

    res = client.get("/api/v1/exercises/relationships/ex_squat/correctives/unknown_technique_issue")
    assert res.status_code == 404
    assert "was not found" in res.json()["detail"]


# =============================================================================
# O. Empty relationship behavior
# =============================================================================

def test_o_empty_relationship_behavior(service):
    """Verifies that exercises with no progressions return an explicit empty list (no fabrication)."""
    # Find an exercise with no progressions in catalog (e.g. pinnacle progression exercises)
    exercises_no_prog = [e.id for e in CATALOG_EXERCISES if len(e.progressions) == 0]
    assert len(exercises_no_prog) > 0, "Expected some terminal exercises to have no progressions"

    terminal_id = exercises_no_prog[0]
    progs = service.get_progressions(terminal_id)
    assert progs == [], f"Expected empty list for '{terminal_id}', got: {progs}"


# =============================================================================
# P. Candidate deduplication
# =============================================================================

def test_p_candidate_deduplication(service):
    """Verifies deduplication retains the strongest relationship classification and deterministic ordering."""
    deduped = service.get_deduplicated_candidates("ex_squat")
    ids = [d.exerciseId for d in deduped]
    assert len(ids) == len(set(ids)), "Duplicate exercise IDs found in deduplicated candidates"

    # Verify precedence: if an exercise was both a progression and something else, it is progression
    ex_squat = CATALOG_BY_ID["ex_squat"]
    for node in deduped:
        if node.exerciseId in ex_squat.progressions:
            assert node.relationshipType == "progression", (
                f"Candidate '{node.exerciseId}' is in progressions but classified as '{node.relationshipType}'"
            )


# =============================================================================
# Q. Graph statistics
# =============================================================================

def test_q_graph_statistics(service, client):
    """Verifies catalog graph statistics metrics and orphan count."""
    stats = service.get_graph_statistics()
    assert isinstance(stats, CatalogGraphStatistics)
    assert stats.totalExercises == 100
    assert stats.totalEdges == 616
    assert stats.averageRelationshipsPerExercise == 6.16
    assert stats.exercisesWithProgressions == 69
    assert stats.exercisesWithRegressions == 88
    assert stats.exercisesWithSubstitutions == 100
    assert stats.exercisesWithComplements == 100
    assert stats.correctiveMappingsCount == 25
    assert stats.orphanedExerciseCount == 0

    # API verification
    res = client.get("/api/v1/exercises/relationships/stats")
    assert res.status_code == 200
    data = res.json()
    assert data["total_exercises"] == 100
    assert data["total_edges"] == 616
    assert data["orphaned_exercise_count"] == 0


# =============================================================================
# R. Phase 3 compatibility
# =============================================================================

def test_r_phase_3_compatibility(client):
    """Verifies that Phase 3 exercises endpoint and data model remain intact."""
    res = client.get("/api/v1/exercises")
    assert res.status_code == 200
    exercises = res.json()
    assert len(exercises) == 100
    first = exercises[0]
    for required_key in ["id", "name", "description", "primaryMuscles", "difficulty", "category"]:
        assert required_key in first


# =============================================================================
# S. Exactly five CV mappings
# =============================================================================

def test_s_canonical_cv_mappings():
    """Verifies that exactly 5 canonical exercises in the catalog map to CV keys."""
    expected = {
        "ex_squat": "squat",
        "ex_bench_press": "bench_press",
        "ex_deadlift": "deadlift",
        "ex_bicep_curl": "bicep_curl",
        "ex_shoulder_press": "shoulder_press",
    }
    assert CANONICAL_CV_EXERCISES == expected
    cv_supported = [e for e in CATALOG_EXERCISES if e.supportedFormAnalysis]
    assert len(cv_supported) == 5
    assert set(e.id for e in cv_supported) == set(expected.keys())


# =============================================================================
# T. Invalid relationship data fails validation
# =============================================================================

def test_t_invalid_relationship_fails_validation():
    """Verifies that invalid relationship data fails validation clearly rather than being repaired."""
    # Self reference
    with pytest.raises(ValueError):
        from backend.app.schemas.exercise import ExerciseKnowledgeSchema
        ExerciseKnowledgeSchema(
            id="ex_test",
            name="Test",
            description="Test description",
            primaryMuscles=["chest"],
            progressions=["ex_test"],  # Self reference
        )


# =============================================================================
# U. Normalized issue IDs map only to actual Phase 9B.2 heuristics
# =============================================================================

def test_u_normalized_issue_ids_map_to_actual_heuristics():
    """Verifies that all 25 corrective mappings use real heuristics from form_heuristics.py."""
    active_cv_exercises = set(STANDARD_HEURISTIC_CONFIGS.keys())
    assert active_cv_exercises == {"ex_squat", "ex_bench_press", "ex_deadlift", "ex_bicep_curl", "ex_shoulder_press"}

    for mapping in RAW_CORRECTIVE_MAPPINGS:
        src = mapping["source_exercise_id"]
        assert src in active_cv_exercises, f"Source '{src}' not in active CV exercises"
        h_name = mapping["heuristic_name"]
        issue_id = mapping["issue_id"]

        # Verify heuristic_name exists in HEURISTIC_NAME_TO_ISSUE_ID lookup
        assert (src, h_name) in HEURISTIC_NAME_TO_ISSUE_ID
        assert HEURISTIC_NAME_TO_ISSUE_ID[(src, h_name)] == issue_id


# =============================================================================
# V. Corrective candidates exist in catalog
# =============================================================================

def test_v_corrective_candidates_exist_in_catalog():
    """Verifies that every single corrective candidate exists in CATALOG_BY_ID."""
    for mapping in RAW_CORRECTIVE_MAPPINGS:
        for cand_id in mapping["candidate_exercise_ids"]:
            assert cand_id in CATALOG_BY_ID, f"Corrective candidate '{cand_id}' not found in catalog"
            assert cand_id != mapping["source_exercise_id"]


# =============================================================================
# W. Orphan definition implemented strictly
# =============================================================================

def test_w_orphan_definition_strictly_implemented(service):
    """
    Verifies orphan definition:
    An exercise is orphaned iff outgoing (p,r,s,c) == 0 AND incoming (p,r,s,c) == 0.
    In the authoritative 100-exercise catalog, the count is exactly 0.
    """
    stats = service.get_graph_statistics()
    assert stats.orphanedExerciseCount == 0

    outgoing = {
        e.id: len(e.progressions) + len(e.regressions) + len(e.substitutions) + len(e.complementaryExercises)
        for e in CATALOG_EXERCISES
    }
    incoming = {e.id: 0 for e in CATALOG_EXERCISES}
    for e in CATALOG_EXERCISES:
        for t in e.progressions + e.regressions + e.substitutions + e.complementaryExercises:
            if t in incoming:
                incoming[t] += 1

    orphans = [e.id for e in CATALOG_EXERCISES if outgoing[e.id] == 0 and incoming[e.id] == 0]
    assert len(orphans) == 0


# =============================================================================
# X. Valid substitution cycles are preserved
# =============================================================================

def test_x_valid_substitution_cycles_preserved(service):
    """Verifies that legitimate bidirectional substitution relationships exist and are preserved."""
    # If A is a substitution for B, and B is a substitution for A, both directions should resolve
    bidirectional_subs = []
    for ex in CATALOG_EXERCISES:
        for sub_id in ex.substitutions:
            sub_ex = CATALOG_BY_ID.get(sub_id)
            if sub_ex and ex.id in sub_ex.substitutions:
                bidirectional_subs.append((ex.id, sub_id))

    assert len(bidirectional_subs) > 0, "Expected legitimate bidirectional substitution cycles"
    # Verify graph traversal handles both without error or infinite loop
    for ex_a, ex_b in bidirectional_subs[:5]:
        subs_a = [s.exerciseId for s in service.get_substitutions(ex_a)]
        subs_b = [s.exerciseId for s in service.get_substitutions(ex_b)]
        assert ex_b in subs_a
        assert ex_a in subs_b


# =============================================================================
# Y. No prohibited medical/clinical language
# =============================================================================

def test_y_no_prohibited_medical_language(service):
    """Verifies that no relationship rationales or corrective reasons contain prohibited medical claims."""
    # Check all corrective reasons
    for m in RAW_CORRECTIVE_MAPPINGS:
        lower_reason = m["reason"].lower()
        for phrase in PROHIBITED_MEDICAL_PHRASES:
            assert phrase not in lower_reason, (
                f"Prohibited medical phrase '{phrase}' found in corrective reason: '{m['reason']}'"
            )

    # Check generated rationales across all exercises
    for ex in CATALOG_EXERCISES:
        related = service.get_related_exercises(ex.id)
        for node in (
            related.progressions
            + related.regressions
            + related.substitutions
            + related.complements
            + related.correctives
        ):
            lower_rat = node.rationale.lower()
            for phrase in PROHIBITED_MEDICAL_PHRASES:
                assert phrase not in lower_rat, (
                    f"Prohibited medical phrase '{phrase}' found in rationale for '{node.exerciseId}': '{node.rationale}'"
                )
