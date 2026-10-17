"""
Deterministic Exercise Relationship & Corrective Guidance Service (Phase 9B.8.3).

Responsibilities:
- Precompute and index the full relationship graph across all 100 catalog exercises.
- Provide O(1) categorized queries:
    - get_progressions()
    - get_regressions()
    - get_substitutions()
    - get_complements()
    - get_corrective_exercises()
- Provide deduplicated candidate aggregation preserving strongest relationship classification.
- Provide topological graph statistics (total edges, degree distribution, orphans).
- Enforce strict non-medical language and deterministic, explainable ordering.
- Zero Gemini/LLM, zero external network calls, zero user-specific Firestore writes.
"""

from typing import List, Dict, Tuple, Optional, Set
from backend.app.schemas.exercise import (
    ExerciseKnowledgeSchema,
    ExerciseRelationshipType,
    ExerciseRelationshipNode,
    CorrectiveGuidanceCandidate,
    ExerciseRelationshipsResponse,
    CatalogGraphStatistics,
    is_canonical_cv_exercise,
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

# Relationship Precedence Hierarchy for Candidate Deduplication
# Strongest / most specific relationship type is retained if an exercise appears in multiple paths.
RELATIONSHIP_PRECEDENCE: Dict[ExerciseRelationshipType, int] = {
    "progression": 1,
    "regression": 2,
    "substitution": 3,
    "complement": 4,
    "corrective": 5,
}


def _format_muscles(muscles: List[str]) -> str:
    """Formats muscle list into clean comma-separated string."""
    return ", ".join(m.replace("_", " ") for m in muscles) if muscles else "target muscles"


def _format_equipment(equipment: List[str]) -> str:
    """Formats equipment list into clean readable string."""
    return ", ".join(eq.replace("_", " ") for eq in equipment) if equipment else "bodyweight"


def _generate_deterministic_rationale(
    source: ExerciseKnowledgeSchema,
    target: ExerciseKnowledgeSchema,
    rel_type: ExerciseRelationshipType,
    custom_reason: Optional[str] = None,
) -> str:
    """
    Generates a deterministic, factual, non-medical rationale for a relationship edge.
    Strictly avoids clinical, injury, or unsupported biomechanical claims.
    """
    if custom_reason:
        return custom_reason

    src_pat = source.movementPattern.replace("_", " ")
    tgt_pat = target.movementPattern.replace("_", " ")
    tgt_muscles = _format_muscles(target.primaryMuscles)
    tgt_eq = _format_equipment(target.equipment)

    if rel_type == "progression":
        if source.equipment == target.equipment:
            return (
                f"Advanced {tgt_pat} variation with increased mechanical loading "
                f"and stabilization demands for the {tgt_muscles}."
            )
        return (
            f"Progresses from {source.name} to {target.name} using {tgt_eq}, "
            f"increasing movement challenge within the {tgt_pat} pattern."
        )

    elif rel_type == "regression":
        return (
            f"Accessible {tgt_pat} variation that reduces loading or balance demands "
            f"while preserving movement pattern practice for the {tgt_muscles}."
        )

    elif rel_type == "substitution":
        if source.movementPattern == target.movementPattern:
            return (
                f"Provides a comparable {tgt_pat} movement pattern targeting {tgt_muscles} "
                f"using {tgt_eq}."
            )
        return (
            f"Alternative exercise engaging {tgt_muscles} with comparable movement demands "
            f"using {tgt_eq}."
        )

    elif rel_type == "complement":
        return (
            f"Accessory movement training supporting {tgt_muscles} to build balanced "
            f"strength alongside the primary {src_pat} pattern."
        )

    return (
        f"Selected exercise candidate supporting movement quality and technique consistency "
        f"for {tgt_muscles}."
    )


class ExerciseRelationshipService:
    """
    Deterministic domain service managing the exercise relationship graph and corrective mappings.
    Thread-safe and stateless per request; precomputes all indexes upon instantiation.
    """

    def __init__(self, catalog: Optional[Dict[str, ExerciseKnowledgeSchema]] = None):
        self._catalog = catalog or CATALOG_BY_ID
        self._raw_exercises = list(self._catalog.values())

        # Precomputed lookup indexes
        self._progressions: Dict[str, List[ExerciseRelationshipNode]] = {}
        self._regressions: Dict[str, List[ExerciseRelationshipNode]] = {}
        self._substitutions: Dict[str, List[ExerciseRelationshipNode]] = {}
        self._complements: Dict[str, List[ExerciseRelationshipNode]] = {}

        # Corrective indexes:
        # Key: (exercise_id, issue_or_heuristic_name) -> List[ExerciseRelationshipNode]
        self._correctives_by_key: Dict[Tuple[str, str], List[ExerciseRelationshipNode]] = {}
        # Key: exercise_id -> List[CorrectiveGuidanceCandidate]
        self._corrective_candidates_by_exercise: Dict[str, List[CorrectiveGuidanceCandidate]] = {}
        # Key: exercise_id -> List[ExerciseRelationshipNode] (all unique correctives for exercise)
        self._all_correctives_by_exercise: Dict[str, List[ExerciseRelationshipNode]] = {}

        # Topological statistics cache
        self._stats_cache: Optional[CatalogGraphStatistics] = None

        # Build deterministic indexes
        self._build_indexes()

    def _build_node(
        self,
        source: ExerciseKnowledgeSchema,
        target_id: str,
        rel_type: ExerciseRelationshipType,
        priority: int = 1,
        custom_reason: Optional[str] = None,
    ) -> ExerciseRelationshipNode:
        """Constructs a validated relationship node for a target exercise."""
        target = self._catalog[target_id]
        rationale = _generate_deterministic_rationale(
            source=source,
            target=target,
            rel_type=rel_type,
            custom_reason=custom_reason,
        )
        return ExerciseRelationshipNode(
            exercise_id=target.id,
            name=target.name,
            relationship_type=rel_type,
            movement_pattern=target.movementPattern,
            difficulty=target.difficulty,
            equipment=target.equipment,
            primary_muscles=target.primaryMuscles,
            rationale=rationale,
            priority=priority,
            is_canonical_cv=is_canonical_cv_exercise(target.id),
        )

    def _build_indexes(self) -> None:
        """Constructs all deterministic relationship indexes in deterministic order."""
        # 1. Index 4 primary relationship types across all exercises
        for ex in self._raw_exercises:
            # Progressions
            progs = [
                self._build_node(ex, target_id, "progression", priority=idx + 1)
                for idx, target_id in enumerate(ex.progressions)
                if target_id in self._catalog
            ]
            self._progressions[ex.id] = progs

            # Regressions
            regs = [
                self._build_node(ex, target_id, "regression", priority=idx + 1)
                for idx, target_id in enumerate(ex.regressions)
                if target_id in self._catalog
            ]
            self._regressions[ex.id] = regs

            # Substitutions
            subs = [
                self._build_node(ex, target_id, "substitution", priority=idx + 1)
                for idx, target_id in enumerate(ex.substitutions)
                if target_id in self._catalog
            ]
            self._substitutions[ex.id] = subs

            # Complements
            comps = [
                self._build_node(ex, target_id, "complement", priority=idx + 1)
                for idx, target_id in enumerate(ex.complementaryExercises)
                if target_id in self._catalog
            ]
            self._complements[ex.id] = comps

        # 2. Index Corrective Guidance Mappings from Phase 9B.2 observations
        for m in RAW_CORRECTIVE_MAPPINGS:
            src_id = m["source_exercise_id"]
            if src_id not in self._catalog:
                continue

            src_ex = self._catalog[src_id]
            h_name = m["heuristic_name"]
            issue_id = m["issue_id"]
            reason = m["reason"]
            prio = m["priority"]

            candidate_nodes: List[ExerciseRelationshipNode] = []
            for idx, cand_id in enumerate(m["candidate_exercise_ids"]):
                if cand_id in self._catalog:
                    node = self._build_node(
                        source=src_ex,
                        target_id=cand_id,
                        rel_type="corrective",
                        priority=prio,
                        custom_reason=reason,
                    )
                    candidate_nodes.append(node)

            # Sort candidate nodes deterministically by priority then ID
            candidate_nodes.sort(key=lambda n: (n.priority, n.exerciseId))

            # Store mapping under both normalized issue_id and underlying heuristic_name
            self._correctives_by_key[(src_id, issue_id)] = candidate_nodes
            self._correctives_by_key[(src_id, h_name)] = candidate_nodes

            # Record high-level candidate structure
            cand_struct = CorrectiveGuidanceCandidate(
                issue_id=issue_id,
                heuristic_name=h_name,
                source_exercise_id=src_id,
                candidate_exercises=candidate_nodes,
                reason=reason,
                priority=prio,
            )
            self._corrective_candidates_by_exercise.setdefault(src_id, []).append(cand_struct)

            # Accumulate all unique correctives for the exercise
            existing_corr = self._all_correctives_by_exercise.setdefault(src_id, [])
            for c_node in candidate_nodes:
                if not any(e.exerciseId == c_node.exerciseId for e in existing_corr):
                    existing_corr.append(c_node)

        # Sort all correctives per exercise deterministically
        for src_id in self._all_correctives_by_exercise:
            self._all_correctives_by_exercise[src_id].sort(
                key=lambda n: (n.priority, n.exerciseId)
            )

    def _require_valid_exercise(self, exercise_id: str) -> ExerciseKnowledgeSchema:
        """Validates that the exercise exists in the catalog, or raises KeyError."""
        if exercise_id not in self._catalog:
            raise KeyError(f"Exercise '{exercise_id}' was not found in the 100-exercise catalog.")
        return self._catalog[exercise_id]

    # =========================================================================
    # AUTHORITATIVE CATEGORIZED QUERIES
    # =========================================================================

    def get_progressions(self, exercise_id: str) -> List[ExerciseRelationshipNode]:
        """Returns deterministic list of harder/more demanding progression exercises."""
        self._require_valid_exercise(exercise_id)
        return list(self._progressions.get(exercise_id, []))

    def get_regressions(self, exercise_id: str) -> List[ExerciseRelationshipNode]:
        """Returns deterministic list of simpler/more accessible regression exercises."""
        self._require_valid_exercise(exercise_id)
        return list(self._regressions.get(exercise_id, []))

    def get_substitutions(self, exercise_id: str) -> List[ExerciseRelationshipNode]:
        """Returns deterministic list of equivalent substitution exercises."""
        self._require_valid_exercise(exercise_id)
        return list(self._substitutions.get(exercise_id, []))

    def get_complements(self, exercise_id: str) -> List[ExerciseRelationshipNode]:
        """Returns deterministic list of accessory/complementary exercises."""
        self._require_valid_exercise(exercise_id)
        return list(self._complements.get(exercise_id, []))

    def get_corrective_exercises(self, exercise_id: str, issue_id: str) -> List[ExerciseRelationshipNode]:
        """
        Returns deterministic corrective exercise candidates addressing an observed technique cue.
        Supports query via normalized issue ID (e.g. 'insufficient_depth') OR
        underlying Phase 9B.2 heuristic name (e.g. 'squat_depth').
        """
        self._require_valid_exercise(exercise_id)
        key = (exercise_id, issue_id.strip())
        if key not in self._correctives_by_key:
            valid_keys = [
                k[1] for k in self._correctives_by_key.keys() if k[0] == exercise_id
            ]
            raise KeyError(
                f"Technique issue or heuristic '{issue_id}' was not found for exercise '{exercise_id}'. "
                f"Valid issues for this exercise: {sorted(set(valid_keys))}"
            )
        return list(self._correctives_by_key[key])

    def get_corrective_candidates(self, exercise_id: str) -> List[CorrectiveGuidanceCandidate]:
        """Returns all corrective guidance candidate structures for an exercise."""
        self._require_valid_exercise(exercise_id)
        return list(self._corrective_candidates_by_exercise.get(exercise_id, []))

    # =========================================================================
    # CANDIDATE DEDUPLICATION & AGGREGATION
    # =========================================================================

    def get_deduplicated_candidates(self, exercise_id: str) -> List[ExerciseRelationshipNode]:
        """
        Returns a single unified list of related exercises with deterministic ordering.
        If an exercise appears through multiple relationship paths:
        - Retains the single strongest relationship type according to RELATIONSHIP_PRECEDENCE:
          progression > regression > substitution > complement > corrective
        - Sorts deterministically by:
            1. priority (ascending)
            2. relationship type rank (ascending)
            3. exercise_id (alphabetical)
        """
        self._require_valid_exercise(exercise_id)

        progs = self.get_progressions(exercise_id)
        regs = self.get_regressions(exercise_id)
        subs = self.get_substitutions(exercise_id)
        comps = self.get_complements(exercise_id)
        corrs = self._all_correctives_by_exercise.get(exercise_id, [])

        all_nodes = progs + regs + subs + comps + corrs

        # Deduplicate retaining the strongest relationship classification
        seen: Dict[str, ExerciseRelationshipNode] = {}
        for node in all_nodes:
            tid = node.exerciseId
            if tid not in seen:
                seen[tid] = node
            else:
                existing = seen[tid]
                curr_rank = RELATIONSHIP_PRECEDENCE[node.relationshipType]
                exist_rank = RELATIONSHIP_PRECEDENCE[existing.relationshipType]
                if curr_rank < exist_rank:
                    seen[tid] = node

        # Sort with deterministic tie-breaking
        deduped = list(seen.values())
        deduped.sort(
            key=lambda n: (
                n.priority,
                RELATIONSHIP_PRECEDENCE[n.relationshipType],
                n.exerciseId,
            )
        )
        return deduped

    def get_related_exercises(self, exercise_id: str) -> ExerciseRelationshipsResponse:
        """
        Returns a complete summary response containing categorized relationships
        and the derived deduplicated candidates.
        """
        ex = self._require_valid_exercise(exercise_id)
        progs = self.get_progressions(exercise_id)
        regs = self.get_regressions(exercise_id)
        subs = self.get_substitutions(exercise_id)
        comps = self.get_complements(exercise_id)
        corrs = list(self._all_correctives_by_exercise.get(exercise_id, []))
        deduped = self.get_deduplicated_candidates(exercise_id)

        total_rel = len(progs) + len(regs) + len(subs) + len(comps) + len(corrs)

        return ExerciseRelationshipsResponse(
            source_exercise_id=ex.id,
            source_exercise_name=ex.name,
            progressions=progs,
            regressions=regs,
            substitutions=subs,
            complements=comps,
            correctives=corrs,
            deduplicated_candidates=deduped,
            total_relationships=total_rel,
        )

    # =========================================================================
    # GRAPH TOPOLOGY & STATISTICS
    # =========================================================================

    def get_graph_statistics(self) -> CatalogGraphStatistics:
        """
        Computes deterministic topological metrics for the catalog relationship graph.
        
        Orphan Definition (Phase 9B.8.3):
        An exercise is considered orphaned if and only if it has:
          - zero outgoing progression edges
          - zero outgoing regression edges
          - zero outgoing substitution edges
          - zero outgoing complement edges
          - AND zero incoming edges across those same four relationship types.
        Corrective mappings are tracked separately and do not alter this orphan statistic.
        """
        if self._stats_cache is not None:
            return self._stats_cache

        total_exercises = len(self._raw_exercises)
        with_p = sum(1 for ex in self._raw_exercises if len(ex.progressions) > 0)
        with_r = sum(1 for ex in self._raw_exercises if len(ex.regressions) > 0)
        with_s = sum(1 for ex in self._raw_exercises if len(ex.substitutions) > 0)
        with_c = sum(1 for ex in self._raw_exercises if len(ex.complementaryExercises) > 0)

        # Count total edges across the 4 relationship types
        total_edges = sum(
            len(ex.progressions) + len(ex.regressions) + len(ex.substitutions) + len(ex.complementaryExercises)
            for ex in self._raw_exercises
        )

        avg_edges = round(total_edges / total_exercises, 2) if total_exercises > 0 else 0.0

        # Degree computation: outgoing + incoming across (progressions, regressions, substitutions, complements)
        outgoing_degree: Dict[str, int] = {
            ex.id: len(ex.progressions) + len(ex.regressions) + len(ex.substitutions) + len(ex.complementaryExercises)
            for ex in self._raw_exercises
        }
        incoming_degree: Dict[str, int] = {ex.id: 0 for ex in self._raw_exercises}

        for ex in self._raw_exercises:
            for target in ex.progressions + ex.regressions + ex.substitutions + ex.complementaryExercises:
                if target in incoming_degree:
                    incoming_degree[target] += 1

        orphaned = [
            ex.id for ex in self._raw_exercises
            if outgoing_degree[ex.id] == 0 and incoming_degree[ex.id] == 0
        ]

        # Degree distribution (total degree: outgoing + incoming)
        degree_dist: Dict[str, int] = {}
        for ex in self._raw_exercises:
            total_deg = outgoing_degree[ex.id] + incoming_degree[ex.id]
            bucket = f"degree_{total_deg}"
            degree_dist[bucket] = degree_dist.get(bucket, 0) + 1

        # Sort degree distribution keys deterministically
        sorted_degree_dist = {
            k: degree_dist[k] for k in sorted(degree_dist.keys(), key=lambda x: int(x.split("_")[1]))
        }

        self._stats_cache = CatalogGraphStatistics(
            total_exercises=total_exercises,
            exercises_with_progressions=with_p,
            exercises_with_regressions=with_r,
            exercises_with_substitutions=with_s,
            exercises_with_complements=with_c,
            total_edges=total_edges,
            average_relationships_per_exercise=avg_edges,
            corrective_mappings_count=len(RAW_CORRECTIVE_MAPPINGS),
            orphaned_exercise_count=len(orphaned),
            degree_distribution=sorted_degree_dist,
        )
        return self._stats_cache


# Global singleton instance for precomputed zero-overhead lookups
_service_instance: Optional[ExerciseRelationshipService] = None


def get_exercise_relationship_service() -> ExerciseRelationshipService:
    """Returns the precomputed global ExerciseRelationshipService singleton."""
    global _service_instance
    if _service_instance is None:
        _service_instance = ExerciseRelationshipService()
    return _service_instance
