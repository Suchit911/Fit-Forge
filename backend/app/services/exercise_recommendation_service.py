"""
Deterministic Personalized Exercise Recommendation Service (Phase 9B.8.4).

Connects the 100-exercise catalog, relationship graph, and corrective guidance
mappings with user constraints to generate explainable, ranked exercise candidates.

Core Architectural Rules:
- Deterministic decision layer only: Zero Gemini, Zero LLMs, Zero ML, Zero Vector DB.
- Strict candidate generation by intent:
    - GENERAL: entire 100-exercise catalog
    - PROGRESSION: ExerciseRelationshipService.get_progressions(source)
    - REGRESSION: ExerciseRelationshipService.get_regressions(source)
    - SUBSTITUTION: ExerciseRelationshipService.get_substitutions(source)
    - COMPLEMENT: ExerciseRelationshipService.get_complements(source)
    - CORRECTIVE: ExerciseRelationshipService.get_corrective_exercises(source, issue)
- Equipment is strictly a hard eligibility gate: exercise.equipment ⊆ available_equipment.
- Equipment is completely removed from soft scoring.
- Soft scores are normalized [0.0, 1.0] and weights sum to exactly 1.00.
- State handling:
    - State A (Valid): ranked candidates
    - State B (Insufficient Data): 0 candidates with missing-field diagnostic
    - State C (Conflicting Constraints): 0 candidates with conflicting_filters list
- Intent-aware diversity: enabled for general discovery; disabled for relationship and corrective.
- Deterministic tie-breaking: score DESC -> priority ASC -> compound before isolation -> exercise_id ASC.
- Read-only: zero Firestore writes, zero external network calls.
"""

from typing import List, Dict, Any, Optional, Set, Tuple
from backend.app.schemas.exercise import (
    RecommendationIntent,
    ExerciseRecommendationRequest,
    ExerciseRecommendationNode,
    ExerciseRecommendationResponse,
    ExerciseKnowledgeSchema,
    ExerciseRelationshipNode,
    MovementPattern,
    ExerciseCategory,
    ExerciseType,
    Laterality,
    DifficultyLevel,
    EquipmentType,
    MuscleGroup,
    FitnessGoal,
    CANONICAL_CV_EXERCISES,
    is_canonical_cv_exercise,
    PROHIBITED_MEDICAL_PHRASES,
)
from backend.app.seeds.catalog import (
    CATALOG_EXERCISES,
    CATALOG_BY_ID,
)
from backend.app.services.exercise_relationship_service import (
    ExerciseRelationshipService,
    get_exercise_relationship_service,
)

# Explicit Scoring Profiles (Weights sum to exactly 1.00)
GENERAL_SCORING_WEIGHTS: Dict[str, float] = {
    "goal": 0.30,
    "muscle": 0.30,
    "movement_pattern": 0.20,
    "difficulty": 0.10,
    "category_laterality": 0.10,
}

RELATIONSHIP_SCORING_WEIGHTS: Dict[str, float] = {
    "relationship_edge": 0.35,
    "goal": 0.25,
    "muscle": 0.25,
    "difficulty": 0.15,
}

CORRECTIVE_SCORING_WEIGHTS: Dict[str, float] = {
    "corrective_match": 0.50,
    "movement_pattern": 0.25,
    "difficulty": 0.15,
    "muscle": 0.10,
}

DIFFICULTY_NUMERIC_MAP: Dict[DifficultyLevel, int] = {
    "beginner": 0,
    "intermediate": 1,
    "advanced": 2,
}


class ExerciseRecommendationService:
    """Deterministic, catalog-backed exercise recommendation engine."""

    def __init__(
        self,
        relationship_service: Optional[ExerciseRelationshipService] = None,
        catalog_by_id: Optional[Dict[str, ExerciseKnowledgeSchema]] = None,
        catalog_exercises: Optional[List[ExerciseKnowledgeSchema]] = None,
    ):
        self._relationship_service = (
            relationship_service
            if relationship_service is not None
            else get_exercise_relationship_service()
        )
        self._catalog_by_id = catalog_by_id if catalog_by_id is not None else CATALOG_BY_ID
        self._catalog_exercises = (
            catalog_exercises if catalog_exercises is not None else CATALOG_EXERCISES
        )

    # =========================================================================
    # PUBLIC RECOMMENDATION PIPELINE
    # =========================================================================

    def recommend(self, request: ExerciseRecommendationRequest) -> ExerciseRecommendationResponse:
        """
        Executes the full deterministic recommendation pipeline:
        1. Strict Candidate Generation (by intent) & Source/Issue Validation
        2. Hard Eligibility Filtering (equipment, environment, CV gate, exclusions)
        3. Mathematical Bounded Soft Scoring (weights sum to 1.00)
        4. Deterministic Templated Reasons Generation
        5. Stable Multi-Tiered Tie-Breaking
        6. Intent-Aware Diversity Post-Processing
        7. Truncation to limit & diagnostic state construction
        """
        applied_filters: Dict[str, Any] = {"intent": request.intent.value if hasattr(request.intent, "value") else str(request.intent)}
        diagnostics: List[str] = []
        conflicting_filters: List[str] = []

        # ---------------------------------------------------------------------
        # STEP 1: STRICT CANDIDATE GENERATION & VALIDATION
        # ---------------------------------------------------------------------
        raw_candidates, gen_diagnostics = self._generate_candidates_for_intent(request)
        if gen_diagnostics:
            # STATE B: Insufficient data or invalid source/issue
            return ExerciseRecommendationResponse(
                intent=request.intent,
                totalEvaluated=0,
                totalEligible=0,
                returnedCount=0,
                candidates=[],
                appliedFilters=applied_filters,
                diagnostics=gen_diagnostics,
                conflictingFilters=[],
            )

        total_evaluated = len(raw_candidates)

        # ---------------------------------------------------------------------
        # STEP 2: HARD ELIGIBILITY GATES
        # ---------------------------------------------------------------------
        eligible_candidates, filter_conflicts = self._apply_hard_gates(raw_candidates, request)
        total_eligible = len(eligible_candidates)

        if total_eligible == 0:
            if total_evaluated > 0:
                # STATE C: Conflicting hard constraints
                return ExerciseRecommendationResponse(
                    intent=request.intent,
                    totalEvaluated=total_evaluated,
                    totalEligible=0,
                    returnedCount=0,
                    candidates=[],
                    appliedFilters=self._summarize_applied_filters(request),
                    diagnostics=[
                        f"Zero catalog exercises satisfied the active hard constraints for intent '{request.intent.value if hasattr(request.intent, 'value') else request.intent}'."
                    ],
                    conflictingFilters=filter_conflicts,
                )
            else:
                # 0 evaluated (e.g. source exercise has no defined graph edges)
                return ExerciseRecommendationResponse(
                    intent=request.intent,
                    totalEvaluated=0,
                    totalEligible=0,
                    returnedCount=0,
                    candidates=[],
                    appliedFilters=self._summarize_applied_filters(request),
                    diagnostics=[f"No catalog edges exist for the requested intent '{request.intent.value if hasattr(request.intent, 'value') else request.intent}'."],
                    conflictingFilters=[],
                )

        # ---------------------------------------------------------------------
        # STEP 3: BOUNDED MATHEMATICAL SOFT SCORING & REASONS
        # ---------------------------------------------------------------------
        scored_nodes: List[ExerciseRecommendationNode] = []
        for cand_tuple in eligible_candidates:
            exercise, rel_node = cand_tuple
            score = self._compute_score(exercise, rel_node, request)
            reasons = self._generate_deterministic_reasons(exercise, rel_node, request)
            is_canonical = is_canonical_cv_exercise(exercise.id)

            scored_nodes.append(
                ExerciseRecommendationNode(
                    exercise_id=exercise.id,
                    name=exercise.name,
                    movement_pattern=exercise.movementPattern,
                    exercise_type=exercise.exerciseType,
                    difficulty=exercise.difficulty,
                    equipment=list(exercise.equipment),
                    primary_muscles=list(exercise.primaryMuscles),
                    score=score,
                    reasons=reasons,
                    relationship_type=rel_node.relationshipType if rel_node else None,
                    is_canonical_cv=is_canonical,
                )
            )

        # ---------------------------------------------------------------------
        # STEP 4: STABLE MULTI-TIERED TIE-BREAKING
        # ---------------------------------------------------------------------
        # Tier 1: Score DESC (2 decimal places)
        # Tier 2: Priority ASC (Priority 1 before 2)
        # Tier 3: Compound before isolation
        # Tier 4: Exercise ID ASC (alphabetical)
        scored_nodes.sort(
            key=lambda node: (
                -round(node.score, 2),
                self._get_candidate_priority(node, eligible_candidates),
                0 if node.exerciseType == "compound" else 1,
                node.exerciseId,
            )
        )

        # ---------------------------------------------------------------------
        # STEP 5: INTENT-AWARE DIVERSITY
        # ---------------------------------------------------------------------
        diversified_nodes = self._apply_intent_aware_diversity(scored_nodes, request)

        # ---------------------------------------------------------------------
        # STEP 6: TRUNCATION TO REQUEST LIMIT
        # ---------------------------------------------------------------------
        final_candidates = diversified_nodes[: request.limit]

        return ExerciseRecommendationResponse(
            intent=request.intent,
            totalEvaluated=total_evaluated,
            totalEligible=total_eligible,
            returnedCount=len(final_candidates),
            candidates=final_candidates,
            appliedFilters=self._summarize_applied_filters(request),
            diagnostics=diagnostics,
            conflictingFilters=conflicting_filters,
        )

    # =========================================================================
    # CANDIDATE GENERATION & VALIDATION
    # =========================================================================

    def _generate_candidates_for_intent(
        self, request: ExerciseRecommendationRequest
    ) -> Tuple[List[Tuple[ExerciseKnowledgeSchema, Optional[ExerciseRelationshipNode]]], List[str]]:
        """
        Retrieves the initial candidate pool based exclusively on request intent.
        Enforces strict scope isolation and validates required source/issue parameters.
        Returns (candidate_tuples, diagnostic_messages).
        """
        intent = request.intent
        diagnostics: List[str] = []

        if intent == RecommendationIntent.GENERAL:
            # Entire 100-exercise catalog
            candidates = [(ex, None) for ex in self._catalog_exercises]
            return candidates, []

        elif intent in (
            RecommendationIntent.PROGRESSION,
            RecommendationIntent.REGRESSION,
            RecommendationIntent.SUBSTITUTION,
            RecommendationIntent.COMPLEMENT,
        ):
            if not request.sourceExerciseId or not request.sourceExerciseId.strip():
                return [], [f"Intent '{intent.value}' requires 'source_exercise_id'."]

            source_id = request.sourceExerciseId.strip()
            if source_id not in self._catalog_by_id:
                return [], [f"Source exercise '{source_id}' was not found in the 100-exercise catalog."]

            try:
                if intent == RecommendationIntent.PROGRESSION:
                    rel_nodes = self._relationship_service.get_progressions(source_id)
                elif intent == RecommendationIntent.REGRESSION:
                    rel_nodes = self._relationship_service.get_regressions(source_id)
                elif intent == RecommendationIntent.SUBSTITUTION:
                    rel_nodes = self._relationship_service.get_substitutions(source_id)
                else:  # COMPLEMENT
                    rel_nodes = self._relationship_service.get_complements(source_id)
            except KeyError as e:
                return [], [str(e)]

            candidates = []
            for node in rel_nodes:
                if node.exerciseId in self._catalog_by_id:
                    candidates.append((self._catalog_by_id[node.exerciseId], node))
            return candidates, []

        elif intent == RecommendationIntent.CORRECTIVE:
            if not request.sourceExerciseId or not request.sourceExerciseId.strip():
                return [], ["Intent 'corrective' requires 'source_exercise_id'."]

            source_id = request.sourceExerciseId.strip()
            if source_id not in CANONICAL_CV_EXERCISES:
                return [], [
                    "Corrective recommendations require a canonical CV source exercise "
                    "(ex_squat, ex_bench_press, ex_deadlift, ex_bicep_curl, ex_shoulder_press)."
                ]

            if not request.correctiveIssueId or not request.correctiveIssueId.strip():
                return [], ["Intent 'corrective' requires 'corrective_issue_id'."]

            issue_id = request.correctiveIssueId.strip()
            try:
                rel_nodes = self._relationship_service.get_corrective_exercises(source_id, issue_id)
            except KeyError:
                return [], [
                    f"Issue '{issue_id}' is not an authoritative Phase 9B.2 finding for exercise '{source_id}'."
                ]

            candidates = []
            for node in rel_nodes:
                if node.exerciseId in self._catalog_by_id:
                    candidates.append((self._catalog_by_id[node.exerciseId], node))
            return candidates, []

        return [], [f"Unknown recommendation intent: '{intent}'"]

    # =========================================================================
    # HARD ELIGIBILITY FILTERS
    # =========================================================================

    def _apply_hard_gates(
        self,
        candidates: List[Tuple[ExerciseKnowledgeSchema, Optional[ExerciseRelationshipNode]]],
        request: ExerciseRecommendationRequest,
    ) -> Tuple[List[Tuple[ExerciseKnowledgeSchema, Optional[ExerciseRelationshipNode]]], List[str]]:
        """
        Applies binary hard gates (0 or 1).
        An exercise failing any active hard gate is immediately excluded.
        Returns (eligible_candidates, conflict_diagnostics).
        """
        eligible: List[Tuple[ExerciseKnowledgeSchema, Optional[ExerciseRelationshipNode]]] = []
        equipment_failures = 0
        environment_failures = 0
        exclusion_failures = 0
        cv_gate_failures = 0

        excluded_ids = set(request.excludedExerciseIds)
        excluded_equip = set(request.excludedEquipment)
        avail_equip_set = set(request.availableEquipment) if request.availableEquipment is not None else None

        for cand_tuple in candidates:
            exercise, _ = cand_tuple

            # 1. Non-deprecated catalog membership
            if exercise.isDeprecated or exercise.id not in self._catalog_by_id:
                continue

            # 2. Explicit exercise exclusion
            if exercise.id in excluded_ids:
                exclusion_failures += 1
                continue

            # 3. Available Equipment Gate: exercise.equipment ⊆ available_equipment
            if avail_equip_set is not None:
                if not all(eq in avail_equip_set for eq in exercise.equipment):
                    equipment_failures += 1
                    continue

            # 4. Excluded Equipment Gate: exercise.equipment ∩ excludedEquipment == ∅
            if excluded_equip:
                if any(eq in excluded_equip for eq in exercise.equipment):
                    equipment_failures += 1
                    continue

            # 5. Environment Gate
            if request.environment is not None:
                if (
                    request.environment not in exercise.targetEnvironments
                    and "anywhere" not in exercise.targetEnvironments
                ):
                    environment_failures += 1
                    continue

            # 6. CV Support Gate
            if request.formAnalysisSupportedOnly:
                if exercise.id not in CANONICAL_CV_EXERCISES:
                    cv_gate_failures += 1
                    continue

            eligible.append(cand_tuple)

        conflicts: List[str] = []
        if len(candidates) > 0 and len(eligible) == 0:
            if equipment_failures > 0:
                conflicts.append(
                    f"Equipment mismatch eliminated {equipment_failures} candidate(s) "
                    f"(available: {request.availableEquipment}, excluded: {request.excludedEquipment})."
                )
            if environment_failures > 0:
                conflicts.append(
                    f"Environment '{request.environment}' eliminated {environment_failures} candidate(s)."
                )
            if cv_gate_failures > 0:
                conflicts.append(
                    f"form_analysis_supported_only eliminated {cv_gate_failures} candidate(s) not in canonical CV set."
                )
            if exclusion_failures > 0:
                conflicts.append(
                    f"Explicit exclusions eliminated {exclusion_failures} candidate(s)."
                )

        return eligible, conflicts

    # =========================================================================
    # MATHEMATICAL SOFT SCORING
    # =========================================================================

    def _compute_score(
        self,
        exercise: ExerciseKnowledgeSchema,
        rel_node: Optional[ExerciseRelationshipNode],
        request: ExerciseRecommendationRequest,
    ) -> float:
        """
        Computes normalized score in [0.0, 100.0] using intent-specific profile.
        Weights sum to exactly 1.00. Zero equipment points awarded.
        """
        intent = request.intent

        if intent == RecommendationIntent.GENERAL:
            w = GENERAL_SCORING_WEIGHTS
            s_goal = self._score_goal(exercise, request)
            s_muscle = self._score_muscle(exercise, request)
            s_pattern = self._score_movement_pattern(exercise, request)
            s_diff = self._score_difficulty(exercise, request)
            s_cat_lat = self._score_category_laterality(exercise, request)

            raw = (
                w["goal"] * s_goal
                + w["muscle"] * s_muscle
                + w["movement_pattern"] * s_pattern
                + w["difficulty"] * s_diff
                + w["category_laterality"] * s_cat_lat
            )

        elif intent in (
            RecommendationIntent.PROGRESSION,
            RecommendationIntent.REGRESSION,
            RecommendationIntent.SUBSTITUTION,
            RecommendationIntent.COMPLEMENT,
        ):
            w = RELATIONSHIP_SCORING_WEIGHTS
            s_edge = self._score_relationship_edge(rel_node)
            s_goal = self._score_goal(exercise, request)
            s_muscle = self._score_muscle(exercise, request)
            s_diff = self._score_difficulty(exercise, request)

            raw = (
                w["relationship_edge"] * s_edge
                + w["goal"] * s_goal
                + w["muscle"] * s_muscle
                + w["difficulty"] * s_diff
            )

        elif intent == RecommendationIntent.CORRECTIVE:
            w = CORRECTIVE_SCORING_WEIGHTS
            s_corr = self._score_corrective_match(rel_node)
            s_pattern = self._score_movement_pattern(exercise, request)
            s_diff = self._score_difficulty(exercise, request)
            s_muscle = self._score_muscle(exercise, request)

            raw = (
                w["corrective_match"] * s_corr
                + w["movement_pattern"] * s_pattern
                + w["difficulty"] * s_diff
                + w["muscle"] * s_muscle
            )
        else:
            raw = 0.50

        # Bound score strictly to [0.0, 100.0] and round to 2 decimal places
        bounded = max(0.0, min(100.0, raw * 100.0))
        return round(bounded, 2)

    def _score_goal(
        self, exercise: ExerciseKnowledgeSchema, request: ExerciseRecommendationRequest
    ) -> float:
        """Normalized goal alignment signal in [0.0, 1.0]."""
        if not request.targetGoal:
            return 1.0
        return 1.0 if request.targetGoal in exercise.targetGoals else 0.20

    def _score_muscle(
        self, exercise: ExerciseKnowledgeSchema, request: ExerciseRecommendationRequest
    ) -> float:
        """
        Normalized muscle overlap signal in [0.0, 1.0].
        Soft signal: muscle mismatch never hard-excludes an exercise.
        """
        if not request.targetMuscles:
            return 1.0

        target_set = set(request.targetMuscles)
        primary_matches = len(target_set & set(exercise.primaryMuscles))
        primary_denom = max(1, len(exercise.primaryMuscles))

        secondary_matches = len(target_set & set(exercise.secondaryMuscles))
        secondary_denom = max(1, len(exercise.secondaryMuscles))

        overlap = 0.75 * (primary_matches / primary_denom) + 0.25 * (secondary_matches / secondary_denom)
        if overlap == 0.0:
            return 0.10  # Soft minimum baseline
        return min(1.0, overlap)

    def _score_movement_pattern(
        self, exercise: ExerciseKnowledgeSchema, request: ExerciseRecommendationRequest
    ) -> float:
        """Normalized movement pattern match signal in [0.0, 1.0]."""
        if not request.movementPattern:
            return 1.0
        return 1.0 if exercise.movementPattern == request.movementPattern else 0.0

    def _score_difficulty(
        self, exercise: ExerciseKnowledgeSchema, request: ExerciseRecommendationRequest
    ) -> float:
        """Normalized difficulty suitability signal in [0.0, 1.0]."""
        if not request.fitnessLevel:
            return 1.0
        ex_val = DIFFICULTY_NUMERIC_MAP.get(exercise.difficulty, 1)
        req_val = DIFFICULTY_NUMERIC_MAP.get(request.fitnessLevel, 1)
        step_diff = abs(ex_val - req_val)
        if step_diff == 0:
            return 1.0
        elif step_diff == 1:
            return 0.50
        return 0.0

    def _score_category_laterality(
        self, exercise: ExerciseKnowledgeSchema, request: ExerciseRecommendationRequest
    ) -> float:
        """Normalized category and laterality fit in [0.0, 1.0]."""
        cat_score = 1.0
        if request.preferredCategory:
            cat_score = 1.0 if exercise.category == request.preferredCategory else 0.0

        lat_score = 1.0
        if request.preferredLaterality:
            lat_score = 1.0 if exercise.laterality == request.preferredLaterality else 0.0

        return 0.60 * cat_score + 0.40 * lat_score

    def _score_relationship_edge(self, rel_node: Optional[ExerciseRelationshipNode]) -> float:
        """Normalized relationship graph transition priority in [0.0, 1.0]."""
        if not rel_node:
            return 0.50
        prio = rel_node.priority
        if prio == 1:
            return 1.0
        elif prio == 2:
            return 0.50
        return max(0.10, 1.0 / prio)

    def _score_corrective_match(self, rel_node: Optional[ExerciseRelationshipNode]) -> float:
        """Normalized corrective mapping priority in [0.0, 1.0]."""
        if not rel_node:
            return 0.50
        prio = rel_node.priority
        if prio == 1:
            return 1.0
        elif prio == 2:
            return 0.70
        return 0.50

    # =========================================================================
    # DETERMINISTIC REASONS GENERATION
    # =========================================================================

    def _generate_deterministic_reasons(
        self,
        exercise: ExerciseKnowledgeSchema,
        rel_node: Optional[ExerciseRelationshipNode],
        request: ExerciseRecommendationRequest,
    ) -> List[str]:
        """
        Generates concise, templated explanations of meaningful positive signals.
        Zero LLM calls. No medical or clinical claims.
        """
        reasons: List[str] = []

        # 1. Corrective Intent Specific Reason
        if request.intent == RecommendationIntent.CORRECTIVE:
            if rel_node and rel_node.rationale:
                reasons.append(
                    f"Corrective candidate for {request.correctiveIssueId}: {rel_node.rationale}"
                )
            else:
                reasons.append(f"Corrective candidate for {request.correctiveIssueId}")

        # 2. Relationship Edge Specific Reason
        elif rel_node and rel_node.relationshipType:
            source_name = (
                self._catalog_by_id[request.sourceExerciseId].name
                if request.sourceExerciseId and request.sourceExerciseId in self._catalog_by_id
                else request.sourceExerciseId or "source exercise"
            )
            rel_label = rel_node.relationshipType.capitalize()
            reasons.append(f"{rel_label} from {source_name}")

        # 3. Goal Alignment
        if request.targetGoal and request.targetGoal in exercise.targetGoals:
            goal_str = (
                request.targetGoal.value
                if hasattr(request.targetGoal, "value")
                else str(request.targetGoal)
            ).replace("_", " ")
            reasons.append(f"Matches selected fitness goal: {goal_str}")

        # 4. Movement Pattern Match
        if request.movementPattern and exercise.movementPattern == request.movementPattern:
            pat_str = exercise.movementPattern.replace("_", " ")
            reasons.append(f"Matches requested movement pattern: {pat_str}")

        # 5. Target Muscles Match
        if request.targetMuscles:
            target_set = set(request.targetMuscles)
            matched = sorted(
                list(target_set & (set(exercise.primaryMuscles) | set(exercise.secondaryMuscles)))
            )
            if matched:
                formatted_muscles = ", ".join(m.replace("_", " ") for m in matched)
                reasons.append(
                    f"Targets {len(matched)} requested muscle group(s): {formatted_muscles}"
                )

        # 6. Difficulty Fit
        if request.fitnessLevel and exercise.difficulty == request.fitnessLevel:
            reasons.append(f"Suitable for selected fitness level: {request.fitnessLevel}")

        # Fallback if no specific positive criteria triggered
        if not reasons:
            reasons.append("Eligible catalog movement matching general discovery criteria")

        # Sanity check: Non-medical language enforcement
        sanitized_reasons: List[str] = []
        for r in reasons:
            lower = r.lower()
            if not any(phrase in lower for phrase in PROHIBITED_MEDICAL_PHRASES):
                sanitized_reasons.append(r)

        return sanitized_reasons

    # =========================================================================
    # INTENT-AWARE DIVERSITY
    # =========================================================================

    def _apply_intent_aware_diversity(
        self,
        nodes: List[ExerciseRecommendationNode],
        request: ExerciseRecommendationRequest,
    ) -> List[ExerciseRecommendationNode]:
        """
        Applies diversity capping according to intent:
        - GENERAL: Caps to max 2 per movement pattern in top-N, UNLESS that movement
          pattern was explicitly requested.
        - RELATIONSHIP & CORRECTIVE: Diversity post-processing is strictly DISABLED to
          never prune valid relationship edges or curated corrective candidates.
        """
        # Diversity is active ONLY for GENERAL discovery when enabled
        if request.intent != RecommendationIntent.GENERAL or not request.enableDiversity:
            return nodes

        diversified: List[ExerciseRecommendationNode] = []
        pattern_counts: Dict[MovementPattern, int] = {}
        explicit_pattern = request.movementPattern

        for node in nodes:
            pat = node.movementPattern
            # If pattern was explicitly requested, never cap it
            if explicit_pattern and pat == explicit_pattern:
                diversified.append(node)
                continue

            current_count = pattern_counts.get(pat, 0)
            if current_count < 2:
                diversified.append(node)
                pattern_counts[pat] = current_count + 1

        return diversified

    # =========================================================================
    # HELPERS
    # =========================================================================

    def _get_candidate_priority(
        self,
        node: ExerciseRecommendationNode,
        candidates: List[Tuple[ExerciseKnowledgeSchema, Optional[ExerciseRelationshipNode]]],
    ) -> int:
        """Retrieves relationship node priority (1, 2, 3...) or defaults to 1."""
        for ex, r_node in candidates:
            if ex.id == node.exerciseId and r_node is not None:
                return r_node.priority
        return 1

    def _summarize_applied_filters(self, request: ExerciseRecommendationRequest) -> Dict[str, Any]:
        """Summarizes non-empty applied filters for transparency."""
        filters: Dict[str, Any] = {
            "intent": request.intent.value if hasattr(request.intent, "value") else str(request.intent)
        }
        if request.targetGoal:
            filters["target_goal"] = (
                request.targetGoal.value
                if hasattr(request.targetGoal, "value")
                else str(request.targetGoal)
            )
        if request.fitnessLevel:
            filters["fitness_level"] = request.fitnessLevel
        if request.environment:
            filters["environment"] = request.environment
        if request.availableEquipment is not None:
            filters["available_equipment"] = [
                eq.value if hasattr(eq, "value") else str(eq) for eq in request.availableEquipment
            ]
        if request.movementPattern:
            filters["movement_pattern"] = request.movementPattern
        if request.targetMuscles:
            filters["target_muscles"] = [
                m.value if hasattr(m, "value") else str(m) for m in request.targetMuscles
            ]
        if request.excludedEquipment:
            filters["excluded_equipment"] = [
                eq.value if hasattr(eq, "value") else str(eq) for eq in request.excludedEquipment
            ]
        if request.excludedExerciseIds:
            filters["excluded_exercise_ids"] = list(request.excludedExerciseIds)
        if request.sourceExerciseId:
            filters["source_exercise_id"] = request.sourceExerciseId
        if request.correctiveIssueId:
            filters["corrective_issue_id"] = request.correctiveIssueId
        if request.formAnalysisSupportedOnly:
            filters["form_analysis_supported_only"] = True
        return filters


# Global singleton
_recommendation_service_instance: Optional[ExerciseRecommendationService] = None


def get_exercise_recommendation_service() -> ExerciseRecommendationService:
    """Returns the global ExerciseRecommendationService singleton."""
    global _recommendation_service_instance
    if _recommendation_service_instance is None:
        _recommendation_service_instance = ExerciseRecommendationService()
    return _recommendation_service_instance
