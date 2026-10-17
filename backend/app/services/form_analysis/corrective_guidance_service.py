"""
Authoritative Corrective Guidance Service (Phase 9C.6.3 Step 2).

Bridges multi-session longitudinal technique evidence (Phase 9C.6.2) with the
catalog relationship graph (Phase 9B.8.3) and recommendation engine (Phase 9B.8.4).

Core Invariants:
1. Purely advisory & read-only: Zero active workout mutations, zero Firestore writes.
2. Evidence qualification gates: NO_EVIDENCE, INSUFFICIENT_DATA, and EMERGING_OCCURRENCE
   strictly yield empty candidate lists.
3. REPEATED_PATTERN yields educational drills; is_eligible_for_proposal = False.
4. ACTIONABLE_PATTERN yields educational drills; is_eligible_for_proposal = True.
5. Deterministic ranking: score DESC -> mapping priority ASC -> compound before isolation -> exercise_id ASC.
6. Hard constraint filtering: Equipment subset, environment compatibility, user exclusions.
7. Strict non-medical safety boundary: Zero diagnoses, sanitized cues, mandatory authoritative disclaimer.
8. Zero LLM calls.
"""

import logging
from typing import List, Optional, Dict, Any

from backend.app.schemas.form_evidence import (
    EvidenceLevel,
    ExerciseEvidenceSummary,
)
from backend.app.schemas.corrective_guidance import (
    CorrectiveRecommendationItem,
    CorrectiveGuidanceResponse,
    AUTHORITATIVE_CORRECTIVE_DISCLAIMER,
)
from backend.app.schemas.exercise import (
    RecommendationIntent,
    ExerciseRecommendationRequest,
    PROHIBITED_MEDICAL_PHRASES,
    CANONICAL_CV_EXERCISES,
)
from backend.app.seeds.catalog import CATALOG_BY_ID
from backend.app.services.exercise_relationship_service import (
    ExerciseRelationshipService,
    get_exercise_relationship_service,
)
from backend.app.services.exercise_recommendation_service import (
    ExerciseRecommendationService,
)
from backend.app.services.form_analysis.multi_session_evidence_aggregator import (
    MultiSessionEvidenceAggregator,
    STATUS_MESSAGES,
)
from backend.app.repositories.form_analysis_repository import (
    FormAnalysisRepository,
    get_form_analysis_repository,
)

logger = logging.getLogger(__name__)

EQUIPMENT_NORMALIZATION: Dict[str, str] = {
    "dumbbell": "dumbbells",
    "dumbbells": "dumbbells",
    "box": "box_platform",
    "box_platform": "box_platform",
    "resistance_band": "resistance_bands",
    "resistance_bands": "resistance_bands",
    "cable": "cable_machine",
    "cable_machine": "cable_machine",
    "barbell": "barbell",
    "kettlebell": "kettlebell",
    "bodyweight": "bodyweight",
    "smith_machine": "smith_machine",
    "leg_press": "leg_press",
    "pull_up_bar": "pull_up_bar",
    "yoga_mat": "yoga_mat",
    "bench": "bench",
    "incline_bench": "incline_bench",
    "trap_bar": "trap_bar",
    "dip_station": "dip_station",
}

ENVIRONMENT_NORMALIZATION: Dict[str, str] = {
    "home": "home",
    "gym": "gym",
    "outdoor": "outdoor",
    "outdoors": "outdoor",
    "anywhere": "anywhere",
}


class CorrectiveGuidanceService:
    """
    Deterministic Corrective Guidance Orchestrator.
    """

    def __init__(
        self,
        relationship_service: Optional[ExerciseRelationshipService] = None,
        recommendation_service: Optional[ExerciseRecommendationService] = None,
        multi_session_aggregator: Optional[MultiSessionEvidenceAggregator] = None,
        repository: Optional[FormAnalysisRepository] = None,
    ):
        self._relationship_service = (
            relationship_service
            if relationship_service is not None
            else get_exercise_relationship_service()
        )
        self._recommendation_service = (
            recommendation_service
            if recommendation_service is not None
            else ExerciseRecommendationService(relationship_service=self._relationship_service)
        )
        self._multi_session_aggregator = (
            multi_session_aggregator
            if multi_session_aggregator is not None
            else MultiSessionEvidenceAggregator()
        )
        self._repository = (
            repository
            if repository is not None
            else get_form_analysis_repository()
        )

    def get_corrective_guidance(
        self,
        exercise_id: str,
        user_id: str,
        issue_id: Optional[str] = None,
        evidence_summary: Optional[ExerciseEvidenceSummary] = None,
        user_available_equipment: Optional[List[str]] = None,
        user_environment: Optional[str] = None,
        user_excluded_exercises: Optional[List[str]] = None,
        user_fitness_level: Optional[str] = None,
        limit: int = 3,
    ) -> CorrectiveGuidanceResponse:
        """
        Evaluates multi-session technique evidence and returns ranked corrective drill candidates.

        Steps:
        1. Validate parameters (limit in [1, 10], non-empty identifiers).
        2. Resolve or aggregate ExerciseEvidenceSummary (Mode A vs Mode B).
        3. Resolve target issue and target evidence level.
        4. Apply Evidence Qualification Gate:
           - NO_EVIDENCE, INSUFFICIENT_DATA, EMERGING_OCCURRENCE fail-closed to candidates=[].
        5. For REPEATED_PATTERN or ACTIONABLE_PATTERN:
           - Retrieve and rank candidates via ExerciseRecommendationService.
           - Apply deterministic tie-breaking and non-medical phrasing sanitization.
           - Assign proposal eligibility (True only for ACTIONABLE_PATTERN).
        6. Return strongly typed CorrectiveGuidanceResponse with mandatory disclaimer.
        """
        # Step 1: Validate input constraints
        if limit < 1 or limit > 10:
            raise ValueError(f"Limit must be between 1 and 10, got {limit}")

        if not exercise_id or not exercise_id.strip():
            raise ValueError("exercise_id is required.")

        if not user_id or not user_id.strip():
            raise ValueError("user_id is required.")

        clean_exercise_id = exercise_id.strip()
        clean_user_id = user_id.strip()

        # Step 2: Resolve ExerciseEvidenceSummary (Mode A: Supplied vs Mode B: Computed)
        if evidence_summary is not None:
            summary = evidence_summary
        else:
            # Mode B: Query historical detailed sessions and aggregate
            sessions = self._repository.list_user_detailed_history(
                uid=clean_user_id,
                exercise_id=clean_exercise_id,
            )
            summary = self._multi_session_aggregator.aggregate_exercise_evidence(
                sessions=sessions,
                exercise_id=clean_exercise_id,
                user_id=clean_user_id,
            )

        # Step 3: Issue Resolution
        target_issue_id: Optional[str] = None
        target_evidence_level: EvidenceLevel

        if issue_id is not None and issue_id.strip():
            target_issue_id = issue_id.strip()
            # If issue explicitly specified, determine evidence level for this specific issue
            if summary.issues and target_issue_id in summary.issues:
                issue_evidence = summary.issues[target_issue_id]
                target_evidence_level = issue_evidence.evidence_level
            else:
                # Issue not observed with qualifying evidence in the lookback window
                target_evidence_level = EvidenceLevel.NO_EVIDENCE
        else:
            # Default to primary recurring issue from the evidence summary
            target_issue_id = summary.primary_issue_id
            target_evidence_level = summary.evidence_level

        # Step 4: Evidence Qualification Gate
        # Disqualified levels: NO_EVIDENCE, INSUFFICIENT_DATA, EMERGING_OCCURRENCE
        if target_evidence_level == EvidenceLevel.NO_EVIDENCE:
            return CorrectiveGuidanceResponse(
                source_exercise_id=clean_exercise_id,
                target_issue_id=target_issue_id,
                evidence_level=EvidenceLevel.NO_EVIDENCE,
                status_message=STATUS_MESSAGES.get(
                    EvidenceLevel.NO_EVIDENCE,
                    "No qualifying technique issue was identified from the available evidence. Continue regular training.",
                ),
                is_eligible_for_proposal=False,
                candidates=[],
                disclaimer=AUTHORITATIVE_CORRECTIVE_DISCLAIMER,
            )

        if target_evidence_level == EvidenceLevel.INSUFFICIENT_DATA:
            return CorrectiveGuidanceResponse(
                source_exercise_id=clean_exercise_id,
                target_issue_id=target_issue_id,
                evidence_level=EvidenceLevel.INSUFFICIENT_DATA,
                status_message=STATUS_MESSAGES.get(
                    EvidenceLevel.INSUFFICIENT_DATA,
                    "Insufficient repetition or camera observability data to evaluate technique patterns.",
                ),
                is_eligible_for_proposal=False,
                candidates=[],
                disclaimer=AUTHORITATIVE_CORRECTIVE_DISCLAIMER,
            )

        if target_evidence_level == EvidenceLevel.EMERGING_OCCURRENCE:
            return CorrectiveGuidanceResponse(
                source_exercise_id=clean_exercise_id,
                target_issue_id=target_issue_id,
                evidence_level=EvidenceLevel.EMERGING_OCCURRENCE,
                status_message=STATUS_MESSAGES.get(
                    EvidenceLevel.EMERGING_OCCURRENCE,
                    "Isolated technique deviation observed in latest session. Focus on movement cues during standard sets before adding corrective drills.",
                ),
                is_eligible_for_proposal=False,
                candidates=[],
                disclaimer=AUTHORITATIVE_CORRECTIVE_DISCLAIMER,
            )

        # Qualified levels: REPEATED_PATTERN or ACTIONABLE_PATTERN
        if not target_issue_id:
            return CorrectiveGuidanceResponse(
                source_exercise_id=clean_exercise_id,
                target_issue_id=None,
                evidence_level=target_evidence_level,
                status_message="Technique deviation observed, but no specific target issue was identified for corrective drills.",
                is_eligible_for_proposal=False,
                candidates=[],
                disclaimer=AUTHORITATIVE_CORRECTIVE_DISCLAIMER,
            )

        # Step 5: Check corrective mappings existence
        try:
            rel_nodes = self._relationship_service.get_corrective_exercises(clean_exercise_id, target_issue_id)
        except KeyError:
            rel_nodes = []

        if not rel_nodes:
            return CorrectiveGuidanceResponse(
                source_exercise_id=clean_exercise_id,
                target_issue_id=target_issue_id,
                evidence_level=target_evidence_level,
                status_message=f"No corrective drills mapped for issue '{target_issue_id}' on exercise '{clean_exercise_id}'.",
                is_eligible_for_proposal=False,
                candidates=[],
                disclaimer=AUTHORITATIVE_CORRECTIVE_DISCLAIMER,
            )

        rel_node_map = {n.exerciseId: n for n in rel_nodes}

        # Normalize equipment and environment aliases
        normalized_eq: Optional[List[str]] = None
        if user_available_equipment is not None:
            normalized_eq = []
            for eq in user_available_equipment:
                cleaned = str(eq).strip().lower()
                normalized_eq.append(EQUIPMENT_NORMALIZATION.get(cleaned, cleaned))

        normalized_env = None
        if user_environment is not None:
            c_env = str(user_environment).strip().lower()
            normalized_env = ENVIRONMENT_NORMALIZATION.get(c_env, c_env)

        # Step 6: Delegate ranking and constraint filtering to ExerciseRecommendationService
        rec_request = ExerciseRecommendationRequest(
            intent=RecommendationIntent.CORRECTIVE,
            sourceExerciseId=clean_exercise_id,
            correctiveIssueId=target_issue_id,
            availableEquipment=normalized_eq,  # type: ignore[arg-type]
            environment=normalized_env,  # type: ignore[arg-type]
            excludedExerciseIds=user_excluded_exercises or [],
            fitnessLevel=user_fitness_level,  # type: ignore[arg-type]
            limit=limit,
        )

        rec_response = self._recommendation_service.recommend(rec_request)

        if not rec_response.candidates:
            return CorrectiveGuidanceResponse(
                source_exercise_id=clean_exercise_id,
                target_issue_id=target_issue_id,
                evidence_level=target_evidence_level,
                status_message="No compatible corrective drills found matching user equipment and environment constraints.",
                is_eligible_for_proposal=False,
                candidates=[],
                disclaimer=AUTHORITATIVE_CORRECTIVE_DISCLAIMER,
            )

        # Step 7: Build candidate entries preserving full raw score precision
        is_proposal = (target_evidence_level == EvidenceLevel.ACTIONABLE_PATTERN)
        candidate_entries: List[Dict[str, Any]] = []

        for cand in rec_response.candidates:
            ex_id = getattr(cand, "exerciseId", getattr(cand, "exercise_id", ""))
            name = getattr(cand, "name", "")
            diff = getattr(cand, "difficulty", "intermediate")
            diff_str = diff.value if hasattr(diff, "value") else str(diff)
            eq_list = [e.value if hasattr(e, "value") else str(e) for e in getattr(cand, "equipment", [])]
            muscle_list = [m.value if hasattr(m, "value") else str(m) for m in getattr(cand, "primaryMuscles", [])]
            raw_score = float(getattr(cand, "score", 0.0))
            reasons = list(getattr(cand, "reasons", []))

            rel_n = rel_node_map.get(ex_id)
            priority = rel_n.priority if rel_n else 1
            raw_cue = (
                rel_n.rationale
                if (rel_n and rel_n.rationale)
                else f"Practice movement control and proper mechanics for {target_issue_id}."
            )

            # Sanitize cue and reasons against PROHIBITED_MEDICAL_PHRASES
            educational_cue = self._sanitize_text(
                raw_cue,
                fallback=f"Focus on movement mechanics and controlled execution during {name}.",
            )
            sanitized_reasons = [
                self._sanitize_text(r, fallback="Technique improvement drill.")
                for r in reasons
            ]

            candidate_entries.append({
                "exercise_id": ex_id,
                "name": name,
                "difficulty": diff_str,
                "equipment": eq_list,
                "primary_muscles": muscle_list,
                "raw_score": raw_score,
                "reasons": sanitized_reasons,
                "educational_cue": educational_cue,
                "mapping_priority": priority,
                "is_proposal_candidate": is_proposal,
            })

        # Step 8: Deterministic Multi-Tiered Tie-Breaking using Full-Precision Score
        # 1. score DESC using FULL PRECISION
        # 2. mapping priority ASC
        # 3. compound before isolation
        # 4. exercise_id ASC
        def _get_ex_type(eid: str) -> str:
            if eid in CATALOG_BY_ID:
                ex = CATALOG_BY_ID[eid]
                t = getattr(ex, "exerciseType", getattr(ex, "exercise_type", "isolation"))
                return t.value if hasattr(t, "value") else str(t)
            return "isolation"

        candidate_entries.sort(
            key=lambda entry: (
                -entry["raw_score"],
                entry["mapping_priority"],
                0 if _get_ex_type(entry["exercise_id"]) == "compound" else 1,
                entry["exercise_id"],
            )
        )

        # Output score is rounded to 2 decimal places strictly after ranking
        final_items = [
            CorrectiveRecommendationItem(
                exercise_id=entry["exercise_id"],
                name=entry["name"],
                difficulty=entry["difficulty"],
                equipment=entry["equipment"],
                primary_muscles=entry["primary_muscles"],
                score=round(entry["raw_score"], 2),
                reasons=entry["reasons"],
                educational_cue=entry["educational_cue"],
                mapping_priority=entry["mapping_priority"],
                is_proposal_candidate=entry["is_proposal_candidate"],
            )
            for entry in candidate_entries[:limit]
        ]

        # Step 9: Formulate status message
        if target_evidence_level == EvidenceLevel.ACTIONABLE_PATTERN:
            status_msg = (
                f"Persistent technique pattern '{target_issue_id}' confirmed with high confidence. "
                f"Corrective drills qualify for future-workout preparation proposals."
            )
        else:
            status_msg = (
                f"Repeated movement pattern '{target_issue_id}' observed across sessions. "
                f"Supplemental corrective drills recommended for technique practice."
            )

        return CorrectiveGuidanceResponse(
            source_exercise_id=clean_exercise_id,
            target_issue_id=target_issue_id,
            evidence_level=target_evidence_level,
            status_message=status_msg,
            is_eligible_for_proposal=is_proposal and len(final_items) > 0,
            candidates=final_items,
            disclaimer=AUTHORITATIVE_CORRECTIVE_DISCLAIMER,
        )

    def _sanitize_text(self, text: str, fallback: str) -> str:
        """
        Sanitizes text by verifying zero occurrences of prohibited medical/clinical phrases.
        """
        if not text:
            return fallback
        lower = text.lower()
        for phrase in PROHIBITED_MEDICAL_PHRASES:
            if phrase in lower:
                return fallback
        return text


# Singleton instance accessor
_corrective_guidance_service_instance: Optional[CorrectiveGuidanceService] = None


def get_corrective_guidance_service() -> CorrectiveGuidanceService:
    """Returns singleton instance of CorrectiveGuidanceService."""
    global _corrective_guidance_service_instance
    if _corrective_guidance_service_instance is None:
        _corrective_guidance_service_instance = CorrectiveGuidanceService()
    return _corrective_guidance_service_instance
