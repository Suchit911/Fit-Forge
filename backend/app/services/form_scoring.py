"""
Deterministic Exercise Form Scoring Engine (Phase 9B.3).

Provides:
- Deterministic, explainable, bounded (0–100) form scoring model.
- Approved Category Weights:
    ROM = 0.40
    Joint Alignment / Technique = 0.35
    Symmetry = 0.15
    Stability = 0.10
    Total = 1.00
- Gating Observability Rule:
    If fewer than 70% of required heuristics are OBSERVED:
      status = INSUFFICIENT_DATA
      score = null
    Critical Invariant: MISSING DATA != BAD FORM. Missing or low-confidence data
    never produces a form penalty.
- Mathematical Scoring Model:
    S = BaseScore * C_penalty
    where:
      BaseScore = Sum(w'_c * CategoryQuality_c) across observable categories
      CategoryQuality_c = 100 - CategoryPenalty_c
      CategoryPenalty_c = Mean(HeuristicPenalty_h) for observable heuristics in category c
      C_penalty = max(0.60, min(1.0, c_rep))
      Score is strictly clamped to [0.0, 100.0].
- Rep-Level Status Tracking:
    VALID, INCOMPLETE, INVALID, INSUFFICIENT_DATA.
- Multi-Rep Set Aggregation:
    Computes arithmetic mean of valid completed reps without penalizing unobservable reps.
- Deterministic Parameterized Feedback:
    Explains score deductions and tracking status without LLM hallucinations or medical claims.
- Zero external dependencies: operates locally in-memory with pure arithmetic.
"""

import math
from enum import Enum
from dataclasses import dataclass, field
from typing import Dict, List, Optional, Tuple, Union, Any

from ..schemas.form_analysis import (
    ObservabilityStatus,
    HeuristicCategory,
    RepScoreStatus,
    CategoryScoreSchema,
    RepetitionScoreSchema,
    SetScoreSummarySchema,
    FormHeuristicResultSchema,
    ExerciseFormReportSchema,
)
from .form_heuristics import FormHeuristicResult, ExerciseFormReport
from .exercise_fsm import RepOutcome, FSMState


# =============================================================================
# CONFIGURATION & WEIGHT DATA STRUCTURES
# =============================================================================

@dataclass(frozen=True)
class CategoryWeights:
    """
    Standardized, approved category weights for form quality scoring.
    ROM: 0.40, Technique: 0.35, Symmetry: 0.15, Stability: 0.10.
    Total: exactly 1.00.
    """
    rom: float = 0.40
    technique: float = 0.35
    symmetry: float = 0.15
    stability: float = 0.10

    def __post_init__(self):
        weights = (self.rom, self.technique, self.symmetry, self.stability)
        for w in weights:
            if math.isnan(w) or math.isinf(w) or w < 0.0 or w > 1.0:
                raise ValueError(
                    f"Category weights must be finite numbers in [0.0, 1.0], got {weights}"
                )
        total = sum(weights)
        if not math.isclose(total, 1.0, abs_tol=1e-5):
            raise ValueError(
                f"Category weights must sum to exactly 1.0 (got {total:.5f})"
            )

    def get_weight(self, category: Union[HeuristicCategory, str]) -> float:
        """Resolves weight by HeuristicCategory enum or string representation."""
        cat_str = category.value if isinstance(category, Enum) else str(category)
        if cat_str in (HeuristicCategory.ROM.value, "ROM"):
            return self.rom
        elif cat_str in (HeuristicCategory.TECHNIQUE.value, "TECHNIQUE", "Joint Alignment / Technique"):
            return self.technique
        elif cat_str in (HeuristicCategory.SYMMETRY.value, "SYMMETRY", "Symmetry"):
            return self.symmetry
        elif cat_str in (HeuristicCategory.STABILITY.value, "STABILITY", "Stability"):
            return self.stability
        else:
            raise ValueError(f"Unknown heuristic category '{category}'.")


DEFAULT_CATEGORY_WEIGHTS = CategoryWeights()


@dataclass(frozen=True)
class ScoringConfig:
    """
    Centralized configuration for form scoring engine tolerances and bounds.
    """
    weights: CategoryWeights = field(default_factory=CategoryWeights)
    observability_threshold: float = 0.70  # Exactly 70% observable required
    min_confidence_floor: float = 0.60    # Lower bound for confidence dampening
    base_penalty: float = 20.0            # Base penalty for an unaccepted heuristic
    max_heuristic_penalty: float = 100.0  # Maximum penalty per heuristic
    min_heuristic_penalty: float = 0.0    # Minimum penalty per heuristic
    unit_scales: Dict[str, float] = field(default_factory=lambda: {
        "degrees": 2.5,          # 1° excess = +2.5 penalty points
        "norm_units": 500.0,     # 0.01 norm_units excess = +5.0 penalty points
        "ratio": 160.0,          # 0.1 ratio deficit = +16.0 penalty points
        "std_dev": 10.0,         # 1.0 std_dev excess = +10.0 penalty points
        "degrees/frame": 10.0,   # 1.0 deg/frame jitter excess = +10.0 penalty points
    })

    def __post_init__(self):
        if not (0.0 < self.observability_threshold <= 1.0) or math.isnan(self.observability_threshold) or math.isinf(self.observability_threshold):
            raise ValueError(f"observability_threshold must be in (0.0, 1.0], got {self.observability_threshold}")
        if not (0.0 <= self.min_confidence_floor <= 1.0) or math.isnan(self.min_confidence_floor) or math.isinf(self.min_confidence_floor):
            raise ValueError(f"min_confidence_floor must be in [0.0, 1.0], got {self.min_confidence_floor}")
        if not (0.0 <= self.base_penalty <= 100.0) or math.isnan(self.base_penalty) or math.isinf(self.base_penalty):
            raise ValueError(f"base_penalty must be in [0.0, 100.0], got {self.base_penalty}")


DEFAULT_SCORING_CONFIG = ScoringConfig()


# =============================================================================
# SCORING RESULT DATA STRUCTURES
# =============================================================================

@dataclass
class CategoryScore:
    """Detailed score breakdown for a single heuristic category."""
    category: HeuristicCategory
    weight: float
    normalized_weight: float
    raw_penalty: float
    category_score: Optional[float]  # 100 - raw_penalty, or None if unobservable
    is_observable: bool = True
    observable_count: int = 0
    total_count: int = 0
    feedback_items: List[str] = field(default_factory=list)

    def to_schema(self) -> CategoryScoreSchema:
        return CategoryScoreSchema(
            category=self.category.value if isinstance(self.category, Enum) else str(self.category),
            weight=round(self.weight, 3),
            normalized_weight=round(self.normalized_weight, 3),
            raw_penalty=round(self.raw_penalty, 2),
            category_score=round(self.category_score, 1) if self.category_score is not None else None,
            is_observable=self.is_observable,
            observable_count=self.observable_count,
            total_count=self.total_count,
            feedback_items=self.feedback_items,
        )


@dataclass
class RepetitionScore:
    """Complete scoring result for an individual repetition."""
    exercise_id: str
    rep_number: Optional[int]
    status: RepScoreStatus
    score: Optional[float]
    base_score: Optional[float]
    confidence_factor: float
    rep_confidence: float
    observability_ratio: float
    is_sufficiently_observable: bool
    category_scores: Dict[str, CategoryScore] = field(default_factory=dict)
    contributing_defects: List[str] = field(default_factory=list)
    feedback: List[str] = field(default_factory=list)
    timestamp_ms: Optional[float] = None

    def to_schema(self) -> RepetitionScoreSchema:
        return RepetitionScoreSchema(
            exercise_id=self.exercise_id,
            rep_number=self.rep_number,
            status=self.status.value if isinstance(self.status, Enum) else str(self.status),
            score=round(self.score, 1) if self.score is not None else None,
            base_score=round(self.base_score, 1) if self.base_score is not None else None,
            confidence_factor=round(self.confidence_factor, 3),
            rep_confidence=round(self.rep_confidence, 3),
            observability_ratio=round(self.observability_ratio, 3),
            is_sufficiently_observable=self.is_sufficiently_observable,
            category_scores={k: v.to_schema() for k, v in self.category_scores.items()},
            contributing_defects=self.contributing_defects,
            feedback=self.feedback,
            timestamp_ms=self.timestamp_ms,
        )


@dataclass
class SetScoreSummary:
    """Deterministic aggregation of multiple completed repetition scores in a set."""
    exercise_id: str
    status: RepScoreStatus
    overall_score: Optional[float]
    total_reps: int
    valid_reps: int
    insufficient_data_reps: int
    incomplete_reps: int
    invalid_reps: int
    rep_scores: List[RepetitionScore] = field(default_factory=list)
    summary_feedback: List[str] = field(default_factory=list)

    def to_schema(self) -> SetScoreSummarySchema:
        return SetScoreSummarySchema(
            exercise_id=self.exercise_id,
            status=self.status.value if isinstance(self.status, Enum) else str(self.status),
            overall_score=round(self.overall_score, 1) if self.overall_score is not None else None,
            total_reps=self.total_reps,
            valid_reps=self.valid_reps,
            insufficient_data_reps=self.insufficient_data_reps,
            incomplete_reps=self.incomplete_reps,
            invalid_reps=self.invalid_reps,
            rep_scores=[r.to_schema() for r in self.rep_scores],
            summary_feedback=self.summary_feedback,
        )


# =============================================================================
# DETERMINISTIC FORM SCORING SERVICE
# =============================================================================

class FormScoringEngine:
    """
    Deterministic domain service calculating form quality scores from heuristic results.
    Stateless per execution, mathematically bounded in [0.0, 100.0], explainable.
    """

    def __init__(self, config: Optional[ScoringConfig] = None):
        self.config = config or DEFAULT_SCORING_CONFIG

    # -------------------------------------------------------------------------
    # PENALTY CALCULATION
    # -------------------------------------------------------------------------

    def calculate_heuristic_penalty(
        self,
        heuristic: Any,
        custom_config: Optional[ScoringConfig] = None,
    ) -> float:
        """
        Maps an individual heuristic result into a bounded penalty [0.0, 100.0].
        
        Rules:
        - If status != OBSERVED: penalty is strictly 0.0 (MISSING DATA != BAD FORM).
        - If is_acceptable == True: penalty is strictly 0.0.
        - If is_acceptable == False:
            penalty = min(max_penalty, max(0.0, base_penalty + excess * scale))
        """
        cfg = custom_config or self.config

        # Extract status
        status = getattr(heuristic, "status", None)
        if isinstance(status, str):
            try:
                status = ObservabilityStatus(status)
            except ValueError:
                status = ObservabilityStatus.INVALID

        if status != ObservabilityStatus.OBSERVED:
            return 0.0

        # Extract acceptability
        is_acc = getattr(heuristic, "is_acceptable", None)
        if is_acc is True:
            return 0.0

        # Deviation and unit
        dev = getattr(heuristic, "deviation", None)
        unit = getattr(heuristic, "unit", "degrees") or "degrees"

        # Check for invalid numbers
        if dev is not None:
            try:
                dev = float(dev)
                if math.isnan(dev) or math.isinf(dev):
                    return 0.0  # Invalid values do not create false form defects
                dev = max(0.0, dev)
            except (ValueError, TypeError):
                return 0.0
        else:
            dev = 0.0

        # Compute scaled penalty
        scale = cfg.unit_scales.get(unit, 2.5)
        excess_penalty = dev * scale
        total_penalty = cfg.base_penalty + excess_penalty

        # Clamp strictly to configured bounds
        clamped = max(cfg.min_heuristic_penalty, min(cfg.max_heuristic_penalty, total_penalty))
        return round(clamped, 4)

    # -------------------------------------------------------------------------
    # CONFIDENCE DERIVATION
    # -------------------------------------------------------------------------

    def derive_rep_confidence(
        self,
        heuristics: List[Any],
        explicit_confidence: Optional[float] = None,
    ) -> float:
        """
        Derives the representative repetition tracking confidence c_rep in [0.0, 1.0].
        If explicit_confidence is provided and valid, it is clamped to [0.0, 1.0].
        Otherwise, computes the arithmetic mean confidence of all OBSERVED heuristics.
        """
        if explicit_confidence is not None:
            try:
                c = float(explicit_confidence)
                if not math.isnan(c) and not math.isinf(c):
                    return max(0.0, min(1.0, c))
            except (ValueError, TypeError):
                pass

        # Fallback: mean confidence of all OBSERVED heuristics
        observed_confs: List[float] = []
        for h in heuristics:
            status = getattr(h, "status", None)
            if isinstance(status, str):
                try:
                    status = ObservabilityStatus(status)
                except ValueError:
                    continue
            if status == ObservabilityStatus.OBSERVED:
                c = getattr(h, "confidence", 0.0)
                if isinstance(c, (int, float)) and not math.isnan(c) and not math.isinf(c):
                    observed_confs.append(max(0.0, min(1.0, float(c))))

        if not observed_confs:
            return 0.0

        return sum(observed_confs) / len(observed_confs)

    # -------------------------------------------------------------------------
    # REP-LEVEL SCORING
    # -------------------------------------------------------------------------

    def score_repetition(
        self,
        exercise_id: str,
        heuristic_results: Union[ExerciseFormReport, List[Any]],
        rep_outcome: Union[RepOutcome, str] = RepOutcome.VALID_REP,
        rep_number: Optional[int] = None,
        rep_confidence: Optional[float] = None,
        timestamp_ms: Optional[float] = None,
        custom_config: Optional[ScoringConfig] = None,
    ) -> RepetitionScore:
        """
        Scores a single repetition using its associated heuristic results.
        
        Steps:
        1. Normalize input heuristics from ExerciseFormReport or list.
        2. Handle incomplete / invalid rep status from FSM.
        3. Enforce the Observability Threshold (>= 70%). If < 70%, return INSUFFICIENT_DATA with null score.
        4. Calculate category-level penalties and qualities independently.
        5. Re-normalize category weights across observable categories.
        6. Compute BaseScore = Sum(w'_c * CategoryQuality_c).
        7. Compute Confidence Factor C_penalty = max(0.60, min(1.0, c_rep)).
        8. Compute Final Score = BaseScore * C_penalty, clamped to [0.0, 100.0].
        9. Generate deterministic explainable feedback.
        """
        cfg = custom_config or self.config

        # 1. Normalize heuristics and metadata
        if isinstance(heuristic_results, ExerciseFormReport):
            raw_list = heuristic_results.results
            exercise_id = heuristic_results.exercise_id or exercise_id
            if timestamp_ms is None:
                timestamp_ms = heuristic_results.timestamp_ms
        elif isinstance(heuristic_results, list):
            raw_list = heuristic_results
        else:
            raw_list = []

        # Convert outcome string if necessary
        outcome_str = rep_outcome.value if isinstance(rep_outcome, Enum) else str(rep_outcome)

        # 2. Check for Incomplete / Invalid Rep Outcome from FSM
        if outcome_str in (RepOutcome.INCOMPLETE_REP.value, "INCOMPLETE", "INCOMPLETE_REP", "INCOMPLETE_RESET"):
            return RepetitionScore(
                exercise_id=exercise_id,
                rep_number=rep_number,
                status=RepScoreStatus.INCOMPLETE,
                score=None,
                base_score=None,
                confidence_factor=1.0,
                rep_confidence=0.0,
                observability_ratio=0.0,
                is_sufficiently_observable=False,
                category_scores={},
                contributing_defects=[],
                feedback=["Repetition was incomplete. Movement did not transition through the full repetition cycle."],
                timestamp_ms=timestamp_ms,
            )

        if outcome_str in (RepOutcome.INVALIDATED_REP.value, "INVALID", "INVALIDATED_REP", "INVALIDATED_RESET"):
            return RepetitionScore(
                exercise_id=exercise_id,
                rep_number=rep_number,
                status=RepScoreStatus.INVALID,
                score=None,
                base_score=None,
                confidence_factor=1.0,
                rep_confidence=0.0,
                observability_ratio=0.0,
                is_sufficiently_observable=False,
                category_scores={},
                contributing_defects=[],
                feedback=["Repetition was invalidated due to tracking occlusion or invalid kinematic measurements."],
                timestamp_ms=timestamp_ms,
            )

        # 3. Observability Evaluation
        total_heuristics = len(raw_list)
        observed_heuristics: List[Any] = []
        for h in raw_list:
            st = getattr(h, "status", None)
            if isinstance(st, str):
                try:
                    st = ObservabilityStatus(st)
                except ValueError:
                    st = ObservabilityStatus.INVALID
            if st == ObservabilityStatus.OBSERVED:
                observed_heuristics.append(h)

        observable_count = len(observed_heuristics)
        observability_ratio = (observable_count / total_heuristics) if total_heuristics > 0 else 0.0
        is_sufficiently_observable = observability_ratio >= cfg.observability_threshold

        # Strict Gating Rule: < 70% observable -> INSUFFICIENT_DATA, score = null
        if not is_sufficiently_observable:
            req_pct = cfg.observability_threshold * 100.0
            obs_pct = observability_ratio * 100.0
            return RepetitionScore(
                exercise_id=exercise_id,
                rep_number=rep_number,
                status=RepScoreStatus.INSUFFICIENT_DATA,
                score=None,
                base_score=None,
                confidence_factor=1.0,
                rep_confidence=self.derive_rep_confidence(raw_list, rep_confidence),
                observability_ratio=observability_ratio,
                is_sufficiently_observable=False,
                category_scores={},
                contributing_defects=[],
                feedback=[
                    f"Insufficient landmark observability for a reliable score ({observable_count}/{total_heuristics} heuristics observed, {obs_pct:.1f}% < {req_pct:.1f}% required). Adjust camera view."
                ],
                timestamp_ms=timestamp_ms,
            )

        # 4. Category-level Aggregation
        categories = [
            HeuristicCategory.ROM,
            HeuristicCategory.TECHNIQUE,
            HeuristicCategory.SYMMETRY,
            HeuristicCategory.STABILITY,
        ]

        cat_scores: Dict[str, CategoryScore] = {}
        all_defects: List[str] = []

        for cat in categories:
            cat_weight = cfg.weights.get_weight(cat)

            # Filter heuristics belonging to this category
            cat_heuristics: List[Any] = []
            for h in raw_list:
                h_cat = getattr(h, "category", None)
                h_cat_str = h_cat.value if isinstance(h_cat, Enum) else str(h_cat)
                if h_cat_str == cat.value or (cat == HeuristicCategory.TECHNIQUE and h_cat_str in ("TECHNIQUE", "Joint Alignment / Technique")):
                    cat_heuristics.append(h)

            cat_observed = [
                h for h in cat_heuristics
                if (getattr(h, "status", None) == ObservabilityStatus.OBSERVED or getattr(h, "status", None) == "OBSERVED")
            ]

            if not cat_observed:
                # Category has no observable heuristics
                cat_scores[cat.value] = CategoryScore(
                    category=cat,
                    weight=cat_weight,
                    normalized_weight=0.0,
                    raw_penalty=0.0,
                    category_score=None,
                    is_observable=False,
                    observable_count=0,
                    total_count=len(cat_heuristics),
                    feedback_items=[],
                )
            else:
                penalties: List[float] = []
                cat_feedback: List[str] = []
                for h in cat_observed:
                    p = self.calculate_heuristic_penalty(h, cfg)
                    penalties.append(p)
                    if p > 0.0:
                        h_name = getattr(h, "heuristic_name", "heuristic")
                        h_fb = getattr(h, "feedback", "")
                        defect_desc = f"{h_name}: {h_fb}" if h_fb else f"{h_name} penalty: {p:.1f}"
                        cat_feedback.append(defect_desc)
                        all_defects.append(defect_desc)

                mean_penalty = sum(penalties) / len(penalties)
                raw_penalty = max(0.0, min(100.0, mean_penalty))
                category_score = max(0.0, min(100.0, 100.0 - raw_penalty))

                cat_scores[cat.value] = CategoryScore(
                    category=cat,
                    weight=cat_weight,
                    normalized_weight=0.0,  # Will be set in next step
                    raw_penalty=raw_penalty,
                    category_score=category_score,
                    is_observable=True,
                    observable_count=len(cat_observed),
                    total_count=len(cat_heuristics),
                    feedback_items=cat_feedback,
                )

        # 5. Re-normalize category weights across observable categories
        observable_categories = [cs for cs in cat_scores.values() if cs.is_observable]
        total_observable_weight = sum(cs.weight for cs in observable_categories)

        if total_observable_weight <= 0.0:
            return RepetitionScore(
                exercise_id=exercise_id,
                rep_number=rep_number,
                status=RepScoreStatus.INSUFFICIENT_DATA,
                score=None,
                base_score=None,
                confidence_factor=1.0,
                rep_confidence=0.0,
                observability_ratio=observability_ratio,
                is_sufficiently_observable=False,
                category_scores=cat_scores,
                contributing_defects=[],
                feedback=["No observable categories available to compute score."],
                timestamp_ms=timestamp_ms,
            )

        base_score = 0.0
        for cs in observable_categories:
            norm_w = cs.weight / total_observable_weight
            cs.normalized_weight = norm_w
            if cs.category_score is not None:
                base_score += norm_w * cs.category_score

        base_score = max(0.0, min(100.0, base_score))

        # 6. Confidence Dampening
        c_rep = self.derive_rep_confidence(raw_list, rep_confidence)
        confidence_factor = max(cfg.min_confidence_floor, min(1.0, c_rep))

        # 7. Final Form Quality Score
        final_score = base_score * confidence_factor
        final_score = round(max(0.0, min(100.0, final_score)), 1)

        # 8. Deterministic Explainable Feedback
        feedback_list = self._generate_rep_feedback(
            final_score=final_score,
            base_score=base_score,
            confidence_factor=confidence_factor,
            category_scores=cat_scores,
            defects=all_defects,
        )

        return RepetitionScore(
            exercise_id=exercise_id,
            rep_number=rep_number,
            status=RepScoreStatus.VALID,
            score=final_score,
            base_score=round(base_score, 1),
            confidence_factor=round(confidence_factor, 3),
            rep_confidence=round(c_rep, 3),
            observability_ratio=round(observability_ratio, 3),
            is_sufficiently_observable=True,
            category_scores=cat_scores,
            contributing_defects=all_defects,
            feedback=feedback_list,
            timestamp_ms=timestamp_ms,
        )

    # -------------------------------------------------------------------------
    # MULTI-REP SET AGGREGATION
    # -------------------------------------------------------------------------

    def aggregate_set(
        self,
        reps: List[RepetitionScore],
        exercise_id: Optional[str] = None,
    ) -> SetScoreSummary:
        """
        Deterministically aggregates multiple completed repetition scores in a set.
        
        Rules:
        - Repetitions with INSUFFICIENT_DATA, INCOMPLETE, or INVALID are excluded
          from the numerical arithmetic mean.
        - Missing or unobservable data is NEVER converted to a 0 score.
        - If no valid repetitions exist: overall_score is null.
        """
        total_reps = len(reps)
        ex_id = exercise_id or (reps[0].exercise_id if reps else "unknown")

        if total_reps == 0:
            return SetScoreSummary(
                exercise_id=ex_id,
                status=RepScoreStatus.INSUFFICIENT_DATA,
                overall_score=None,
                total_reps=0,
                valid_reps=0,
                insufficient_data_reps=0,
                incomplete_reps=0,
                invalid_reps=0,
                rep_scores=[],
                summary_feedback=["No repetitions submitted for set aggregation."],
            )

        valid_reps: List[RepetitionScore] = []
        insufficient_count = 0
        incomplete_count = 0
        invalid_count = 0

        for r in reps:
            if r.status == RepScoreStatus.VALID and r.score is not None:
                valid_reps.append(r)
            elif r.status == RepScoreStatus.INSUFFICIENT_DATA:
                insufficient_count += 1
            elif r.status == RepScoreStatus.INCOMPLETE:
                incomplete_count += 1
            elif r.status == RepScoreStatus.INVALID:
                invalid_count += 1

        valid_count = len(valid_reps)

        if valid_count > 0:
            mean_score = sum(r.score for r in valid_reps) / valid_count
            overall_score = round(max(0.0, min(100.0, mean_score)), 1)
            status = RepScoreStatus.VALID
            summary_feedback = [
                f"Set completed: {valid_count}/{total_reps} valid repetitions scored (average form score: {overall_score:.1f})."
            ]
            if insufficient_count > 0:
                summary_feedback.append(
                    f"{insufficient_count} rep(s) excluded due to insufficient camera observability (< 70%)."
                )
            if incomplete_count > 0:
                summary_feedback.append(f"{incomplete_count} rep(s) were incomplete.")
            if invalid_count > 0:
                summary_feedback.append(f"{invalid_count} rep(s) were invalidated.")
        else:
            overall_score = None
            if insufficient_count > 0:
                status = RepScoreStatus.INSUFFICIENT_DATA
                summary_feedback = [
                    f"Set score unavailable: {insufficient_count}/{total_reps} repetition(s) had insufficient camera observability."
                ]
            elif invalid_count > 0:
                status = RepScoreStatus.INVALID
                summary_feedback = [f"Set score unavailable: {invalid_count} repetition(s) were invalidated."]
            else:
                status = RepScoreStatus.INCOMPLETE
                summary_feedback = [f"Set score unavailable: {incomplete_count} repetition(s) were incomplete."]

        return SetScoreSummary(
            exercise_id=ex_id,
            status=status,
            overall_score=overall_score,
            total_reps=total_reps,
            valid_reps=valid_count,
            insufficient_data_reps=insufficient_count,
            incomplete_reps=incomplete_count,
            invalid_reps=invalid_count,
            rep_scores=reps,
            summary_feedback=summary_feedback,
        )

    # -------------------------------------------------------------------------
    # FEEDBACK GENERATOR
    # -------------------------------------------------------------------------

    def _generate_rep_feedback(
        self,
        final_score: float,
        base_score: float,
        confidence_factor: float,
        category_scores: Dict[str, CategoryScore],
        defects: List[str],
    ) -> List[str]:
        """Assembles deterministic parameterized feedback messages."""
        feedback: List[str] = []

        if final_score >= 90.0:
            feedback.append("High technique quality observed across evaluated movement criteria.")
        elif final_score >= 75.0:
            feedback.append("Good repetition execution with minor technique adjustments observed.")
        elif final_score >= 50.0:
            feedback.append("Moderate technique deviations observed; review specific movement cues.")
        else:
            feedback.append("Significant technique deviations observed across evaluated movement criteria.")

        # Highlight category-specific notes
        for cat_name, cs in category_scores.items():
            if cs.is_observable and cs.category_score is not None:
                if cs.category_score < 75.0:
                    feedback.append(
                        f"{cat_name} score: {cs.category_score:.1f}/100 (penalty deduction: {cs.raw_penalty:.1f})."
                    )

        # Contributing defect notes
        for defect in defects[:3]:  # Top 3 defects to avoid flooding
            feedback.append(f"Observation: {defect}")

        # Note confidence dampening if applied
        if confidence_factor < 0.99:
            feedback.append(
                f"Score adjusted by tracking confidence factor ({confidence_factor:.2f}). Ensure clear lighting and camera framing."
            )

        return feedback
