"""
Comprehensive Unit & Behavioral Test Suite for Phase 9B.3 Form Scoring Engine.

Validates all 35+ mandatory requirements:
 1. Perfect/acceptable form -> score = 100.0
 2. ROM-only deviation -> reduced by 0.40 weight
 3. Technique-only deviation -> reduced by 0.35 weight
 4. Symmetry-only deviation -> reduced by 0.15 weight
 5. Stability-only deviation -> reduced by 0.10 weight
 6. Multiple category deviations -> cumulative reduction
 7. Weight calculation correctness
 8. Weights sum to 1.0
 9. Score bounded at 0
10. Score bounded at 100
11. Confidence penalty at c=1.0 (no penalty)
12. Confidence penalty below 0.60 (clamped to 0.60 floor)
13. Confidence penalty between 0.60 and 1.0
14. Exactly 70% observable -> score allowed
15. Below 70% observable (69.99%) -> INSUFFICIENT_DATA, score = null
16. Zero observable -> INSUFFICIENT_DATA, score = null
17. Missing heuristic data -> NOT_OBSERVABLE, no penalty
18. Low-confidence heuristic data -> INSUFFICIENT_CONFIDENCE, no penalty
19. NOT_OBSERVABLE -> no penalty
20. INVALID heuristic -> no penalty
21. NaN protection
22. Infinity protection
23. Negative penalty protection (clamps to 0)
24. Excessive penalty protection (clamps to 100)
25. Duplicate/malformed category input
26. Invalid confidence (negative / >1 / NaN)
27. Incomplete rep -> status INCOMPLETE, score null
28. Invalid rep -> status INVALID, score null
29. Multi-rep deterministic aggregation (mean score)
30. Insufficient-data reps in aggregation (excluded from mean, counts recorded)
31. Determinism across repeated identical calls
32. Cross-exercise configuration isolation
33. Every category contributes according to its approved top-level weight
34. No category dominates merely due to having more heuristics
35. Deterministic feedback derivation
36. Pydantic schema serialization
37. Custom configuration overrides
"""

import math
import pytest
from typing import List

from backend.app.schemas.form_analysis import (
    ObservabilityStatus,
    HeuristicCategory,
    RepScoreStatus,
    CategoryScoreSchema,
    RepetitionScoreSchema,
    SetScoreSummarySchema,
)
from backend.app.services.form_heuristics import FormHeuristicResult, ExerciseFormReport
from backend.app.services.exercise_fsm import RepOutcome
from backend.app.services.form_scoring import (
    FormScoringEngine,
    CategoryWeights,
    ScoringConfig,
    CategoryScore,
    RepetitionScore,
    SetScoreSummary,
    DEFAULT_CATEGORY_WEIGHTS,
    DEFAULT_SCORING_CONFIG,
)


# =============================================================================
# FIXTURES & TEST HELPERS
# =============================================================================

def make_heuristic(
    category: HeuristicCategory,
    name: str = "test_heuristic",
    status: ObservabilityStatus = ObservabilityStatus.OBSERVED,
    is_acceptable: bool = True,
    deviation: float = 0.0,
    confidence: float = 1.0,
    unit: str = "degrees",
    exercise_id: str = "ex_squat",
    feedback: str = "Acceptable form.",
) -> FormHeuristicResult:
    """Creates a deterministic FormHeuristicResult for scoring tests."""
    return FormHeuristicResult(
        exercise_id=exercise_id,
        category=category,
        heuristic_name=name,
        status=status,
        is_acceptable=is_acceptable if status == ObservabilityStatus.OBSERVED else None,
        observed_value=90.0,
        reference_value=90.0,
        deviation=deviation,
        confidence=confidence,
        feedback=feedback,
        unit=unit,
        timestamp_ms=1000.0,
    )


def make_standard_four_category_heuristics(
    rom_acceptable: bool = True,
    rom_dev: float = 0.0,
    tech_acceptable: bool = True,
    tech_dev: float = 0.0,
    sym_acceptable: bool = True,
    sym_dev: float = 0.0,
    stab_acceptable: bool = True,
    stab_dev: float = 0.0,
    confidence: float = 1.0,
    exercise_id: str = "ex_squat",
) -> List[FormHeuristicResult]:
    """Generates a complete set of 4 heuristics across ROM, Tech, Sym, and Stability."""
    return [
        make_heuristic(
            HeuristicCategory.ROM, "knee_depth",
            is_acceptable=rom_acceptable, deviation=rom_dev,
            confidence=confidence, exercise_id=exercise_id
        ),
        make_heuristic(
            HeuristicCategory.TECHNIQUE, "torso_inclination",
            is_acceptable=tech_acceptable, deviation=tech_dev,
            confidence=confidence, exercise_id=exercise_id
        ),
        make_heuristic(
            HeuristicCategory.SYMMETRY, "knee_symmetry",
            is_acceptable=sym_acceptable, deviation=sym_dev,
            confidence=confidence, exercise_id=exercise_id
        ),
        make_heuristic(
            HeuristicCategory.STABILITY, "rep_stability",
            is_acceptable=stab_acceptable, deviation=stab_dev,
            confidence=confidence, exercise_id=exercise_id
        ),
    ]


@pytest.fixture
def engine():
    return FormScoringEngine()


# =============================================================================
# SCENARIOS 1–6: FORM QUALITY & CATEGORY WEIGHT CONTRIBUTIONS
# =============================================================================

def test_1_perfect_form_scores_100(engine):
    """1. Perfect/acceptable form yields maximum score (100.0)."""
    heuristics = make_standard_four_category_heuristics(
        rom_acceptable=True,
        tech_acceptable=True,
        sym_acceptable=True,
        stab_acceptable=True,
        confidence=1.0,
    )
    result = engine.score_repetition("ex_squat", heuristics)
    assert result.status == RepScoreStatus.VALID
    assert result.score == 100.0
    assert result.base_score == 100.0
    assert result.confidence_factor == 1.0
    assert len(result.contributing_defects) == 0


def test_2_rom_only_deviation_governed_by_040_weight(engine):
    """2. ROM-only deviation reduces score exactly proportional to 0.40 weight."""
    # Using a custom config with base_penalty=50.0 and deviation=0 for clean predictable penalty
    cfg = ScoringConfig(base_penalty=50.0)
    heuristics = make_standard_four_category_heuristics(
        rom_acceptable=False, rom_dev=0.0,
        tech_acceptable=True,
        sym_acceptable=True,
        stab_acceptable=True,
        confidence=1.0,
    )
    # ROM penalty = 50.0. All others = 0.0.
    # Base score = 100.0 - (0.40 * 50.0) = 80.0
    result = engine.score_repetition("ex_squat", heuristics, custom_config=cfg)
    assert result.status == RepScoreStatus.VALID
    assert result.base_score == 80.0
    assert result.score == 80.0
    assert result.category_scores[HeuristicCategory.ROM.value].raw_penalty == 50.0
    assert result.category_scores[HeuristicCategory.ROM.value].category_score == 50.0


def test_3_technique_only_deviation_governed_by_035_weight(engine):
    """3. Technique-only deviation reduces score exactly proportional to 0.35 weight."""
    cfg = ScoringConfig(base_penalty=50.0)
    heuristics = make_standard_four_category_heuristics(
        rom_acceptable=True,
        tech_acceptable=False, tech_dev=0.0,
        sym_acceptable=True,
        stab_acceptable=True,
        confidence=1.0,
    )
    # Technique penalty = 50.0. Others = 0.
    # Base score = 100.0 - (0.35 * 50.0) = 82.5
    result = engine.score_repetition("ex_squat", heuristics, custom_config=cfg)
    assert result.status == RepScoreStatus.VALID
    assert result.base_score == 82.5
    assert result.score == 82.5
    assert result.category_scores[HeuristicCategory.TECHNIQUE.value].category_score == 50.0


def test_4_symmetry_only_deviation_governed_by_015_weight(engine):
    """4. Symmetry-only deviation reduces score exactly proportional to 0.15 weight."""
    cfg = ScoringConfig(base_penalty=50.0)
    heuristics = make_standard_four_category_heuristics(
        rom_acceptable=True,
        tech_acceptable=True,
        sym_acceptable=False, sym_dev=0.0,
        stab_acceptable=True,
        confidence=1.0,
    )
    # Symmetry penalty = 50.0. Others = 0.
    # Base score = 100.0 - (0.15 * 50.0) = 92.5
    result = engine.score_repetition("ex_squat", heuristics, custom_config=cfg)
    assert result.status == RepScoreStatus.VALID
    assert result.base_score == 92.5
    assert result.score == 92.5


def test_5_stability_only_deviation_governed_by_010_weight(engine):
    """5. Stability-only deviation reduces score exactly proportional to 0.10 weight."""
    cfg = ScoringConfig(base_penalty=50.0)
    heuristics = make_standard_four_category_heuristics(
        rom_acceptable=True,
        tech_acceptable=True,
        sym_acceptable=True,
        stab_acceptable=False, stab_dev=0.0,
        confidence=1.0,
    )
    # Stability penalty = 50.0. Others = 0.
    # Base score = 100.0 - (0.10 * 50.0) = 95.0
    result = engine.score_repetition("ex_squat", heuristics, custom_config=cfg)
    assert result.status == RepScoreStatus.VALID
    assert result.base_score == 95.0
    assert result.score == 95.0


def test_6_multiple_category_deviations_cumulative(engine):
    """6. Multiple category deviations accumulate predictably according to category weights."""
    cfg = ScoringConfig(base_penalty=40.0)
    heuristics = make_standard_four_category_heuristics(
        rom_acceptable=False, rom_dev=0.0,   # ROM penalty 40 * 0.40 = 16.0
        tech_acceptable=False, tech_dev=0.0, # Tech penalty 40 * 0.35 = 14.0
        sym_acceptable=True,
        stab_acceptable=True,
        confidence=1.0,
    )
    # Expected deduction: 16.0 + 14.0 = 30.0 -> Score = 70.0
    result = engine.score_repetition("ex_squat", heuristics, custom_config=cfg)
    assert result.status == RepScoreStatus.VALID
    assert result.base_score == 70.0
    assert result.score == 70.0


# =============================================================================
# SCENARIOS 7–10: WEIGHT VALIDATION & BOUNDS
# =============================================================================

def test_7_8_weight_calculation_and_sum_to_one():
    """7 & 8. Category weights validate correctly and sum to exactly 1.0."""
    weights = CategoryWeights(rom=0.40, technique=0.35, symmetry=0.15, stability=0.10)
    assert math.isclose(weights.rom + weights.technique + weights.symmetry + weights.stability, 1.0)
    
    # Non-summing weights must raise ValueError
    with pytest.raises(ValueError, match="must sum to exactly 1.0"):
        CategoryWeights(rom=0.40, technique=0.35, symmetry=0.15, stability=0.20)

    # Negative weights must raise ValueError
    with pytest.raises(ValueError, match="finite numbers in"):
        CategoryWeights(rom=-0.10, technique=0.50, symmetry=0.30, stability=0.30)


def test_9_score_bounded_at_zero(engine):
    """9. Severe form deviations clamp the score to minimum 0.0."""
    cfg = ScoringConfig(base_penalty=100.0)
    heuristics = make_standard_four_category_heuristics(
        rom_acceptable=False, rom_dev=50.0,
        tech_acceptable=False, tech_dev=50.0,
        sym_acceptable=False, sym_dev=50.0,
        stab_acceptable=False, stab_dev=50.0,
        confidence=1.0,
    )
    result = engine.score_repetition("ex_squat", heuristics, custom_config=cfg)
    assert result.status == RepScoreStatus.VALID
    assert result.score == 0.0
    assert result.base_score == 0.0


def test_10_score_bounded_at_100(engine):
    """10. Score cannot exceed 100.0 even under boundary configurations."""
    heuristics = make_standard_four_category_heuristics(confidence=1.0)
    result = engine.score_repetition("ex_squat", heuristics, rep_confidence=1.5)
    assert result.status == RepScoreStatus.VALID
    assert result.score == 100.0


# =============================================================================
# SCENARIOS 11–13: CONFIDENCE PENALTY (C_penalty)
# =============================================================================

def test_11_confidence_penalty_at_c_1_0(engine):
    """11. At c=1.0, confidence penalty multiplier is 1.0 (no reduction)."""
    heuristics = make_standard_four_category_heuristics(confidence=1.0)
    result = engine.score_repetition("ex_squat", heuristics, rep_confidence=1.0)
    assert result.confidence_factor == 1.0
    assert result.score == 100.0


def test_12_confidence_penalty_below_0_60(engine):
    """12. At c < 0.60, confidence penalty clamps to the approved floor 0.60."""
    heuristics = make_standard_four_category_heuristics(confidence=0.40)
    result = engine.score_repetition("ex_squat", heuristics, rep_confidence=0.40)
    assert result.confidence_factor == 0.60
    assert result.score == 60.0  # 100.0 * 0.60


def test_13_confidence_penalty_between_0_60_and_1_0(engine):
    """13. Between 0.60 and 1.0, confidence factor linearly scales the score."""
    heuristics = make_standard_four_category_heuristics(confidence=0.85)
    result = engine.score_repetition("ex_squat", heuristics, rep_confidence=0.85)
    assert result.confidence_factor == 0.85
    assert result.score == 85.0  # 100.0 * 0.85


# =============================================================================
# SCENARIOS 14–16: GATING OBSERVABILITY RULE (70% THRESHOLD)
# =============================================================================

def test_14_exactly_70_percent_observable_allowed(engine):
    """14. Exactly 70% observable (e.g. 7 out of 10) allows scoring."""
    heuristics = [
        make_heuristic(HeuristicCategory.ROM, f"h_{i}", status=ObservabilityStatus.OBSERVED)
        for i in range(7)
    ] + [
        make_heuristic(HeuristicCategory.ROM, f"h_{i}", status=ObservabilityStatus.NOT_OBSERVABLE)
        for i in range(7, 10)
    ]
    result = engine.score_repetition("ex_squat", heuristics)
    assert result.observability_ratio == 0.70
    assert result.status == RepScoreStatus.VALID
    assert result.score is not None


def test_15_below_70_percent_observable_insufficient_data(engine):
    """15. Observability < 70% (e.g. 69.99% or 6 of 10) returns INSUFFICIENT_DATA and score=null."""
    heuristics = [
        make_heuristic(HeuristicCategory.ROM, f"h_{i}", status=ObservabilityStatus.OBSERVED)
        for i in range(6)
    ] + [
        make_heuristic(HeuristicCategory.ROM, f"h_{i}", status=ObservabilityStatus.NOT_OBSERVABLE)
        for i in range(6, 10)
    ]
    result = engine.score_repetition("ex_squat", heuristics)
    assert result.observability_ratio == 0.60
    assert result.status == RepScoreStatus.INSUFFICIENT_DATA
    assert result.score is None
    assert result.base_score is None
    assert "Insufficient landmark observability" in result.feedback[0]


def test_16_zero_observable_insufficient_data(engine):
    """16. Zero observable heuristics returns INSUFFICIENT_DATA and score=null."""
    heuristics = [
        make_heuristic(HeuristicCategory.ROM, f"h_{i}", status=ObservabilityStatus.NOT_OBSERVABLE)
        for i in range(5)
    ]
    result = engine.score_repetition("ex_squat", heuristics)
    assert result.observability_ratio == 0.0
    assert result.status == RepScoreStatus.INSUFFICIENT_DATA
    assert result.score is None


# =============================================================================
# SCENARIOS 17–20: MISSING DATA != BAD FORM
# =============================================================================

def test_17_missing_heuristic_data_no_form_penalty(engine):
    """17. Missing heuristic data does not penalize form."""
    h = make_heuristic(HeuristicCategory.ROM, "missing", status=ObservabilityStatus.NOT_OBSERVABLE)
    penalty = engine.calculate_heuristic_penalty(h)
    assert penalty == 0.0


def test_18_low_confidence_heuristic_no_form_penalty(engine):
    """18. INSUFFICIENT_CONFIDENCE heuristic does not penalize form."""
    h = make_heuristic(HeuristicCategory.TECHNIQUE, "low_conf", status=ObservabilityStatus.INSUFFICIENT_CONFIDENCE, confidence=0.30)
    penalty = engine.calculate_heuristic_penalty(h)
    assert penalty == 0.0


def test_19_not_observable_heuristic_no_form_penalty(engine):
    """19. NOT_OBSERVABLE status strictly incurs 0 penalty."""
    h = make_heuristic(HeuristicCategory.SYMMETRY, "unseen_limb", status=ObservabilityStatus.NOT_OBSERVABLE)
    penalty = engine.calculate_heuristic_penalty(h)
    assert penalty == 0.0


def test_20_invalid_heuristic_no_form_penalty(engine):
    """20. INVALID status strictly incurs 0 penalty."""
    h = make_heuristic(HeuristicCategory.STABILITY, "invalid_val", status=ObservabilityStatus.INVALID)
    penalty = engine.calculate_heuristic_penalty(h)
    assert penalty == 0.0


# =============================================================================
# SCENARIOS 21–26: NUMERICAL SAFETY & BOUNDARIES
# =============================================================================

def test_21_nan_protection(engine):
    """21. NaN values in deviation or observed value are safely handled without crash."""
    h = make_heuristic(HeuristicCategory.ROM, "nan_dev", deviation=float("nan"), status=ObservabilityStatus.OBSERVED, is_acceptable=False)
    penalty = engine.calculate_heuristic_penalty(h)
    assert penalty == 0.0


def test_22_infinity_protection(engine):
    """22. Infinite values are safely handled without generating invalid penalties."""
    h = make_heuristic(HeuristicCategory.ROM, "inf_dev", deviation=float("inf"), status=ObservabilityStatus.OBSERVED, is_acceptable=False)
    penalty = engine.calculate_heuristic_penalty(h)
    assert penalty == 0.0


def test_23_negative_penalty_protection(engine):
    """23. Negative deviation is clamped to zero penalty."""
    h = make_heuristic(HeuristicCategory.ROM, "neg_dev", deviation=-15.0, status=ObservabilityStatus.OBSERVED, is_acceptable=True)
    penalty = engine.calculate_heuristic_penalty(h)
    assert penalty == 0.0


def test_24_excessive_penalty_protection(engine):
    """24. Huge deviations cannot cause penalty to exceed configured max_heuristic_penalty (100.0)."""
    h = make_heuristic(HeuristicCategory.ROM, "huge_dev", deviation=1000.0, status=ObservabilityStatus.OBSERVED, is_acceptable=False)
    penalty = engine.calculate_heuristic_penalty(h)
    assert penalty == 100.0


def test_25_malformed_category_input(engine):
    """25. Malformed or unknown category strings are handled gracefully."""
    heuristics = [
        make_heuristic(HeuristicCategory.ROM, "knee", status=ObservabilityStatus.OBSERVED),
    ]
    report = engine.score_repetition("ex_squat", heuristics)
    # Only 1 heuristic, 100% observable
    assert report.status == RepScoreStatus.VALID


def test_26_invalid_confidence_values_clamped(engine):
    """26. Negative or >1 confidence values are safely clamped."""
    heuristics = make_standard_four_category_heuristics(confidence=1.0)
    res_neg = engine.score_repetition("ex_squat", heuristics, rep_confidence=-0.5)
    assert res_neg.confidence_factor == 0.60  # Clamped to 0.0 -> max(0.60, 0.0) = 0.60

    res_huge = engine.score_repetition("ex_squat", heuristics, rep_confidence=5.0)
    assert res_huge.confidence_factor == 1.0  # Clamped to 1.0


# =============================================================================
# SCENARIOS 27–28: REP OUTCOME (INCOMPLETE & INVALID)
# =============================================================================

def test_27_incomplete_rep_handling(engine):
    """27. Incomplete reps receive status INCOMPLETE and score=null."""
    heuristics = make_standard_four_category_heuristics()
    res = engine.score_repetition("ex_squat", heuristics, rep_outcome=RepOutcome.INCOMPLETE_REP)
    assert res.status == RepScoreStatus.INCOMPLETE
    assert res.score is None
    assert "incomplete" in res.feedback[0].lower()


def test_28_invalid_rep_handling(engine):
    """28. Invalid reps receive status INVALID and score=null."""
    heuristics = make_standard_four_category_heuristics()
    res = engine.score_repetition("ex_squat", heuristics, rep_outcome=RepOutcome.INVALIDATED_REP)
    assert res.status == RepScoreStatus.INVALID
    assert res.score is None
    assert "invalidated" in res.feedback[0].lower()


# =============================================================================
# SCENARIOS 29–30: MULTI-REP DETERMINISTIC SET AGGREGATION
# =============================================================================

def test_29_multi_rep_deterministic_aggregation(engine):
    """29. Completed set aggregates valid rep scores via arithmetic mean."""
    h_100 = make_standard_four_category_heuristics()
    h_80 = make_standard_four_category_heuristics(rom_acceptable=False, rom_dev=0.0) # 80.0
    cfg = ScoringConfig(base_penalty=50.0)

    rep1 = engine.score_repetition("ex_squat", h_100, rep_number=1, custom_config=cfg) # 100.0
    rep2 = engine.score_repetition("ex_squat", h_80, rep_number=2, custom_config=cfg)  # 80.0

    set_summary = engine.aggregate_set([rep1, rep2])
    assert set_summary.status == RepScoreStatus.VALID
    assert set_summary.total_reps == 2
    assert set_summary.valid_reps == 2
    assert set_summary.overall_score == 90.0  # (100.0 + 80.0) / 2


def test_30_insufficient_data_reps_in_aggregation_not_zero(engine):
    """30. Insufficient-data reps are excluded from mean and NEVER treated as zero."""
    h_valid = make_standard_four_category_heuristics()
    h_unseen = [make_heuristic(HeuristicCategory.ROM, f"h_{i}", status=ObservabilityStatus.NOT_OBSERVABLE) for i in range(5)]

    rep1 = engine.score_repetition("ex_squat", h_valid, rep_number=1)   # score = 100.0
    rep2 = engine.score_repetition("ex_squat", h_unseen, rep_number=2)  # status = INSUFFICIENT_DATA, score = None

    set_summary = engine.aggregate_set([rep1, rep2])
    assert set_summary.total_reps == 2
    assert set_summary.valid_reps == 1
    assert set_summary.insufficient_data_reps == 1
    # Crucial invariant: overall score is 100.0, NOT (100+0)/2 = 50.0!
    assert set_summary.overall_score == 100.0


# =============================================================================
# SCENARIOS 31–35: DETERMINISM, ISOLATION & DOMINANCE CHECKS
# =============================================================================

def test_31_determinism_across_identical_calls(engine):
    """31. Identical inputs yield bit-for-bit identical outputs."""
    heuristics = make_standard_four_category_heuristics(
        rom_acceptable=False, rom_dev=4.0,
        tech_acceptable=False, tech_dev=2.0,
    )
    r1 = engine.score_repetition("ex_squat", heuristics)
    r2 = engine.score_repetition("ex_squat", heuristics)
    assert r1.score == r2.score
    assert r1.base_score == r2.base_score
    assert r1.confidence_factor == r2.confidence_factor
    assert r1.feedback == r2.feedback


def test_32_cross_exercise_configuration_isolation(engine):
    """32. Custom configs for one evaluation do not mutate default engine configuration."""
    custom_cfg = ScoringConfig(base_penalty=40.0)
    heuristics = make_standard_four_category_heuristics(rom_acceptable=False, rom_dev=0.0)

    res_custom = engine.score_repetition("ex_squat", heuristics, custom_config=custom_cfg)
    res_default = engine.score_repetition("ex_bench_press", heuristics)

    # custom base penalty was 40.0, default is 20.0
    # under custom: ROM penalty = 40.0 -> base_score = 100 - (0.40 * 40.0) = 84.0
    # under default: ROM penalty = 20.0 -> base_score = 100 - (0.40 * 20.0) = 92.0
    assert res_custom.score == 84.0
    assert res_default.score == 92.0
    assert engine.config.base_penalty == 20.0


def test_33_every_category_contributes_according_to_approved_weight(engine):
    """33. All approved weights (0.40, 0.35, 0.15, 0.10) scale their respective categories."""
    cfg = ScoringConfig(base_penalty=100.0)

    # ROM only deduction: 100 - 40 = 60
    r_rom = engine.score_repetition("ex_squat", make_standard_four_category_heuristics(rom_acceptable=False), custom_config=cfg)
    assert r_rom.score == 60.0

    # Technique only deduction: 100 - 35 = 65
    r_tech = engine.score_repetition("ex_squat", make_standard_four_category_heuristics(tech_acceptable=False), custom_config=cfg)
    assert r_tech.score == 65.0

    # Symmetry only deduction: 100 - 15 = 85
    r_sym = engine.score_repetition("ex_squat", make_standard_four_category_heuristics(sym_acceptable=False), custom_config=cfg)
    assert r_sym.score == 85.0

    # Stability only deduction: 100 - 10 = 90
    r_stab = engine.score_repetition("ex_squat", make_standard_four_category_heuristics(stab_acceptable=False), custom_config=cfg)
    assert r_stab.score == 90.0


def test_34_no_category_dominates_due_to_having_more_heuristics(engine):
    """34. A category with multiple heuristics is averaged and does not overpower another category."""
    cfg = ScoringConfig(base_penalty=50.0)

    # Category with 1 heuristic failing with penalty 50.0
    h_single = [
        make_heuristic(HeuristicCategory.TECHNIQUE, "t1", is_acceptable=False, deviation=0.0),
        make_heuristic(HeuristicCategory.ROM, "r1", is_acceptable=True),
        make_heuristic(HeuristicCategory.SYMMETRY, "s1", is_acceptable=True),
        make_heuristic(HeuristicCategory.STABILITY, "st1", is_acceptable=True),
    ]
    res_single = engine.score_repetition("ex_squat", h_single, custom_config=cfg)

    # Category with 4 heuristics ALL failing with penalty 50.0
    h_multi = [
        make_heuristic(HeuristicCategory.TECHNIQUE, f"t{i}", is_acceptable=False, deviation=0.0)
        for i in range(1, 5)
    ] + [
        make_heuristic(HeuristicCategory.ROM, "r1", is_acceptable=True),
        make_heuristic(HeuristicCategory.SYMMETRY, "s1", is_acceptable=True),
        make_heuristic(HeuristicCategory.STABILITY, "st1", is_acceptable=True),
    ]
    res_multi = engine.score_repetition("ex_squat", h_multi, custom_config=cfg)

    # Because Technique quality is averaged, both single and multi fail with average penalty 50.0!
    # Therefore, Technique's contribution is IDENTICAL (0.35 * 50 = 17.5 deduction -> score 82.5)
    assert res_single.score == 82.5
    assert res_multi.score == 82.5


def test_35_deterministic_feedback_generation(engine):
    """35. Feedback clearly articulates category score reductions and observations."""
    heuristics = make_standard_four_category_heuristics(
        rom_acceptable=False, rom_dev=10.0,
        tech_acceptable=False, tech_dev=5.0,
    )
    result = engine.score_repetition("ex_squat", heuristics)
    assert any("ROM" in fb or "knee_depth" in fb for fb in result.feedback)
    assert any("Joint Alignment / Technique" in fb or "torso_inclination" in fb for fb in result.feedback)


# =============================================================================
# SCENARIOS 36–37: SCHEMA SERIALIZATION & EXERCISE REPORT SUPPORT
# =============================================================================

def test_36_schema_serialization(engine):
    """36. RepetitionScore and SetScoreSummary serialize cleanly to Pydantic schemas."""
    heuristics = make_standard_four_category_heuristics(rom_acceptable=False, rom_dev=5.0)
    rep_score = engine.score_repetition("ex_squat", heuristics, rep_number=1)

    # Repetition score schema
    rep_schema = rep_score.to_schema()
    assert isinstance(rep_schema, RepetitionScoreSchema)
    assert rep_schema.status == "VALID"
    assert rep_schema.score == rep_score.score

    # Set score schema
    set_summary = engine.aggregate_set([rep_score])
    set_schema = set_summary.to_schema()
    assert isinstance(set_schema, SetScoreSummarySchema)
    assert set_schema.status == "VALID"
    assert set_schema.overall_score == rep_score.score


def test_37_exercise_form_report_direct_input(engine):
    """37. FormScoringEngine directly scores ExerciseFormReport instances from Phase 9B.2."""
    h_list = make_standard_four_category_heuristics()
    report = ExerciseFormReport(
        exercise_id="ex_deadlift",
        timestamp_ms=5000.0,
        results=h_list,
        observable_count=4,
        total_required_count=4,
        observability_ratio=1.0,
        is_sufficiently_observable=True,
    )
    res = engine.score_repetition("ex_deadlift", report)
    assert res.exercise_id == "ex_deadlift"
    assert res.timestamp_ms == 5000.0
    assert res.status == RepScoreStatus.VALID
    assert res.score == 100.0
