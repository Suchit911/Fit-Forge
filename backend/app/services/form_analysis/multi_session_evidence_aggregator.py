"""
Authoritative Multi-Session Form Evidence Aggregator Service (Phase 9C.6.2.3).

Provides:
- Pure in-memory multi-session longitudinal evidence aggregation engine.
- Approach B lookback selection:
    1. Filter historical sessions to the eligible population first.
    2. Select the latest K (LOOKBACK_SESSIONS_K = 5) eligible sessions.
- Strict session eligibility verification (rejection of unfinalized sessions, calculation FAILED,
  sub-threshold volume, sub-threshold observability, and TIER_4_UNPROVENANCED legacy records).
- Issue-level target evaluation:
    * N_session_eligible (Lookback window sessions, <= LOOKBACK_SESSIONS_K)
    * N_target_eval (Sessions where target issue calculation succeeded AND observed reps >= 3)
    * N_qualifying (Sessions in N_target_eval with defect_rate >= 0.50)
    * RecurrenceRatio = N_qualifying / N_target_eval (0.0 if N_target_eval < 3)
    * C_qualifying_mean = mean confidence across N_qualifying sessions (None if N_qualifying == 0)
- Deterministic 4-step precedence decision tree:
    Step 1: N_session_eligible < 3 OR N_target_eval < 3 -> INSUFFICIENT_DATA
    Step 2: N_qualifying == 0                           -> NO_EVIDENCE (qualifying_mean_confidence = None)
    Step 3: N_qualifying == 1                           -> EMERGING_OCCURRENCE
    Step 4: N_qualifying >= 3 AND Dual Confidence Gate  -> ACTIONABLE_PATTERN, Else -> REPEATED_PATTERN
- Dual Confidence Gate for ACTIONABLE_PATTERN:
    * Aggregate qualifying mean confidence >= ACTIONABLE_PATTERN_MIN_CONFIDENCE (0.60)
    * Every qualifying session individually satisfies >= ACTIONABLE_PATTERN_SESSION_MIN_CONFIDENCE (0.55)
    * Zero camera occlusion on target issue repetitions in qualifying sessions
- T19 Multi-Heuristic Failure Isolation: failed heuristics in a session are excluded from their own
  target evaluation (+0/+0) and never become NO_EVIDENCE, while successful issues remain fully eligible.
- Emits read-only AggregatedIssueEvidence and ExerciseEvidenceSummary models with complete provenance.
"""

import logging
from datetime import datetime, timezone
from typing import Dict, List, Optional, Tuple, Any, Union, Set

from backend.app.schemas.form_evidence import (
    EvidenceLevel,
    CalculationStatus,
    ProvenanceTier,
    EvidenceAggregationConfig,
    SessionIssueSummary,
    SessionEvidenceRecord,
    AggregatedIssueEvidence,
    ExerciseEvidenceSummary,
)
from backend.app.schemas.form_analysis import FormMeasurementData, NormalizedFormIssue
from backend.app.seeds.corrective_mappings import (
    HEURISTIC_NAME_TO_ISSUE_ID,
    ISSUE_ID_TO_HEURISTIC_NAME,
    RAW_CORRECTIVE_MAPPINGS,
)
from backend.app.services.form_issue_normalizer import (
    HEURISTIC_TO_CATEGORY,
    FormIssueNormalizer,
)
from backend.app.services.form_analysis.session_evidence_aggregator import (
    SessionEvidenceAggregator,
    HEURISTIC_ALIASES,
)

logger = logging.getLogger(__name__)

# Canonical status descriptions aligned with Phase 9C.6 specification
STATUS_MESSAGES: Dict[EvidenceLevel, str] = {
    EvidenceLevel.NO_EVIDENCE: (
        "No qualifying technique issue was identified from the available evidence. "
        "Continue regular training. This result does not establish that all technique characteristics "
        "were observed or validated."
    ),
    EvidenceLevel.INSUFFICIENT_DATA: (
        "Insufficient repetition or camera observability data to evaluate technique patterns. "
        "Complete at least 3 clean repetitions with clear camera visibility."
    ),
    EvidenceLevel.EMERGING_OCCURRENCE: (
        "Isolated technique deviation observed in latest session. Focus on movement cues during standard sets "
        "before adding corrective drills."
    ),
    EvidenceLevel.REPEATED_PATTERN: (
        "Repeated movement pattern observed across multiple sessions. Educational technique cues and "
        "corrective exercises recommended."
    ),
    EvidenceLevel.ACTIONABLE_PATTERN: (
        "Persistent movement pattern confirmed across sessions meeting elevated confidence criteria. "
        "Technique adjustments recommended."
    ),
}


class MultiSessionEvidenceAggregator:
    """
    Pure in-memory multi-session longitudinal evidence aggregator.
    """

    def __init__(
        self,
        config: Optional[EvidenceAggregationConfig] = None,
        session_aggregator: Optional[SessionEvidenceAggregator] = None,
    ) -> None:
        self.config = config or EvidenceAggregationConfig()
        self.session_aggregator = session_aggregator or SessionEvidenceAggregator(self.config)
        self.normalizer = FormIssueNormalizer()

    # =========================================================================
    # APPROACH B LOOKBACK SELECTION PIPELINE
    # =========================================================================

    def is_session_eligible(self, session: Any) -> Tuple[bool, List[str]]:
        """
        Determines whether a session qualifies for the longitudinal lookback window.

        Eligibility Criteria (V2.3.3):
        - Status must be completed / finalized (status != "incomplete", status != "in_progress")
        - Calculation status must not be FAILED (session.calculation_status != FAILED)
        - Provenance tier must not be TIER_4_UNPROVENANCED (T23)
        - Valid repetitions must meet minimum: valid_reps >= MIN_VALID_REPS_PER_SESSION (3)
        - Session observability ratio must meet minimum: session_observability_ratio >= MIN_SESSION_OBSERVABILITY_RATIO (0.70)
        """
        rejection_reasons: List[str] = []

        # Extract fields defensively
        if isinstance(session, dict):
            status = session.get("status", "completed")
            calc_status = session.get("calculation_status", CalculationStatus.SUCCESS)
            prov_tier = session.get("provenance_tier", ProvenanceTier.TIER_1_NORMALIZED)
            valid_reps = session.get("valid_reps", 0)
            obs_ratio = session.get("session_observability_ratio", 0.0)
            is_eligible_flag = session.get("is_eligible_for_trends")
        else:
            status = getattr(session, "status", "completed")
            calc_status = getattr(session, "calculation_status", CalculationStatus.SUCCESS)
            prov_tier = getattr(session, "provenance_tier", ProvenanceTier.TIER_1_NORMALIZED)
            valid_reps = getattr(session, "valid_reps", 0)
            obs_ratio = getattr(session, "session_observability_ratio", 0.0)
            is_eligible_flag = getattr(session, "is_eligible_for_trends", None)

        # 1. Completion status check
        if status in ("incomplete", "in_progress", "failed", "aborted"):
            rejection_reasons.append(f"UNFINALIZED_SESSION_STATUS_{status.upper()}")

        # 2. Calculation status check
        if calc_status == CalculationStatus.FAILED or str(calc_status).upper() == "FAILED":
            rejection_reasons.append("SESSION_CALCULATION_FAILED")

        # 3. Provenance Tier check (T23)
        if prov_tier == ProvenanceTier.TIER_4_UNPROVENANCED or str(prov_tier).upper() == "TIER_4_UNPROVENANCED":
            rejection_reasons.append("DISALLOWED_PROVENANCE_TIER_4")

        # 4. Volume check (T21)
        if valid_reps < self.config.MIN_VALID_REPS_PER_SESSION:
            rejection_reasons.append(
                f"INSUFFICIENT_VALID_REPS_{valid_reps}_LT_{self.config.MIN_VALID_REPS_PER_SESSION}"
            )

        # 5. Observability ratio check (T22)
        if obs_ratio < self.config.MIN_SESSION_OBSERVABILITY_RATIO:
            rejection_reasons.append(
                f"INSUFFICIENT_OBSERVABILITY_{obs_ratio}_LT_{self.config.MIN_SESSION_OBSERVABILITY_RATIO}"
            )

        # 6. Flag check
        if is_eligible_flag is False and not rejection_reasons:
            rejection_reasons.append("SESSION_MARKED_INELIGIBLE_FOR_TRENDS")

        is_eligible = len(rejection_reasons) == 0
        return is_eligible, rejection_reasons

    def filter_eligible_sessions(
        self,
        sessions: List[Any],
        exercise_id: Optional[str] = None,
    ) -> List[SessionEvidenceRecord]:
        """
        Step 1 of Approach B:
        Filters historical sessions to the eligible population.
        Ensures each session is normalized to a SessionEvidenceRecord.
        """
        eligible: List[SessionEvidenceRecord] = []

        for item in sessions:
            # Convert or ensure SessionEvidenceRecord
            record: Optional[SessionEvidenceRecord] = None
            if isinstance(item, SessionEvidenceRecord):
                record = item
            elif isinstance(item, dict):
                # If already an aggregated session dict
                if "issues" in item and isinstance(item["issues"], dict):
                    try:
                        record = SessionEvidenceRecord(**item)
                    except Exception:
                        record = self.session_aggregator.aggregate_session(session_data=item)
                else:
                    record = self.session_aggregator.aggregate_session(session_data=item)
            else:
                # Other schema object
                if hasattr(item, "issues") and isinstance(getattr(item, "issues"), dict):
                    try:
                        record = SessionEvidenceRecord.model_validate(item)
                    except Exception:
                        record = self.session_aggregator.aggregate_session(session_data=item)
                else:
                    record = self.session_aggregator.aggregate_session(session_data=item)

            if record is None:
                continue

            # Verify exercise_id match if provided
            if exercise_id and record.exercise_id != exercise_id:
                continue

            # Check eligibility
            is_elig, reasons = self.is_session_eligible(record)
            if is_elig:
                eligible.append(record)
            else:
                logger.debug(f"Session {record.session_id} excluded from lookback: {reasons}")

        return eligible

    def select_lookback_sessions(
        self,
        eligible_sessions: List[SessionEvidenceRecord],
        lookback_k: Optional[int] = None,
    ) -> List[SessionEvidenceRecord]:
        """
        Step 2 of Approach B:
        Selects the latest K sessions from the ALREADY-ELIGIBLE population.
        Default K is LOOKBACK_SESSIONS_K = 5.
        """
        k = lookback_k or self.config.LOOKBACK_SESSIONS_K

        if not eligible_sessions:
            return []

        def _get_timestamp(s: SessionEvidenceRecord) -> float:
            if not s.completed_at:
                return 0.0
            try:
                clean_ts = s.completed_at.replace("Z", "+00:00")
                return datetime.fromisoformat(clean_ts).timestamp()
            except Exception:
                return 0.0

        # Check if timestamps are informative
        timestamps = [_get_timestamp(s) for s in eligible_sessions]
        has_varying_timestamps = len(set(timestamps)) > 1

        if has_varying_timestamps:
            # Sort newest first, then take top K
            sorted_eligible = sorted(eligible_sessions, key=_get_timestamp, reverse=True)
            return sorted_eligible[:k]
        else:
            # Preserving order: take the last K items (chronological convention)
            return eligible_sessions[-k:]

    # =========================================================================
    # ISSUE-LEVEL LONGITUDINAL EVALUATION & 4-STEP DECISION TREE
    # =========================================================================

    def _resolve_canonical_issue_info(
        self, exercise_id: str, heuristic_or_issue: str
    ) -> Tuple[str, str, str]:
        """Resolves (issue_id, source_heuristic, category) deterministically."""
        h_name = HEURISTIC_ALIASES.get(heuristic_or_issue, heuristic_or_issue)

        if h_name in self.normalizer.get_all_valid_issue_ids():
            issue_id = h_name
            source_heuristic = ISSUE_ID_TO_HEURISTIC_NAME.get(issue_id, h_name)
            cat_enum = HEURISTIC_TO_CATEGORY.get(source_heuristic)
            category = cat_enum.value if cat_enum else "technique"
            return issue_id, source_heuristic, category

        resolved_issue = HEURISTIC_NAME_TO_ISSUE_ID.get((exercise_id, h_name))
        if resolved_issue is not None:
            issue_id = resolved_issue
            source_heuristic = h_name
            cat_enum = HEURISTIC_TO_CATEGORY.get(source_heuristic)
            category = cat_enum.value if cat_enum else "technique"
            return issue_id, source_heuristic, category

        cat_enum = HEURISTIC_TO_CATEGORY.get(h_name)
        category = cat_enum.value if cat_enum else "technique"
        return h_name, h_name, category

    def aggregate_issue_longitudinal(
        self,
        issue_id: str,
        source_heuristic: str,
        category: str,
        lookback_sessions: List[SessionEvidenceRecord],
    ) -> AggregatedIssueEvidence:
        """
        Computes longitudinal metrics and EvidenceLevel for a specific technique issue.

        Authoritative Population Metrics:
        - N_session_eligible = len(lookback_sessions) (<= LOOKBACK_SESSIONS_K)
        - N_target_eval = sessions in lookback where issue calculation succeeded
          AND target_reps_observed >= MIN_TARGET_HEURISTIC_OBSERVED_REPS (3)
        - N_qualifying = sessions in N_target_eval where defect_rate >= SESSION_DEFECT_RATE_THRESHOLD (0.50)
        - RecurrenceRatio = N_qualifying / N_target_eval (0.0 if N_target_eval < 3)
        - C_qualifying_mean = mean confidence across N_qualifying sessions (None if N_qualifying == 0)

        4-Step Precedence Decision Tree:
        Step 1: N_session_eligible < 3 OR N_target_eval < 3 -> INSUFFICIENT_DATA
        Step 2: N_qualifying == 0                           -> NO_EVIDENCE
        Step 3: N_qualifying == 1                           -> EMERGING_OCCURRENCE
        Step 4: N_qualifying >= 3 AND Dual Confidence Gate  -> ACTIONABLE_PATTERN, Else -> REPEATED_PATTERN
        """
        n_session_eligible = len(lookback_sessions)

        target_eval_sessions: List[SessionEvidenceRecord] = []
        qualifying_sessions: List[SessionEvidenceRecord] = []
        data_quality_flags: List[str] = []
        provenance_tiers_used: Set[str] = set()

        first_observed_at: Optional[str] = None
        latest_observed_at: Optional[str] = None

        # 1. Target Issue Isolation (Approach B)
        for session in lookback_sessions:
            if str(session.provenance_tier) not in provenance_tiers_used:
                provenance_tiers_used.add(str(session.provenance_tier))

            issue_summary = session.issues.get(issue_id)
            if issue_summary is None:
                # Also try looking up by source_heuristic
                for iss in session.issues.values():
                    if iss.source_heuristic == source_heuristic:
                        issue_summary = iss
                        break

            if issue_summary is None:
                continue

            # Failed calculation isolation (T19 contract)
            if issue_summary.calculation_status == CalculationStatus.FAILED:
                # Contributes +0 to N_target_eval and +0 to N_qualifying
                if "FLAG_HEURISTIC_CALCULATION_FAILED_IN_SESSION" not in data_quality_flags:
                    data_quality_flags.append("FLAG_HEURISTIC_CALCULATION_FAILED_IN_SESSION")
                continue

            # Check observed repetition sufficiency for this heuristic in this session
            if issue_summary.target_reps_observed < self.config.MIN_TARGET_HEURISTIC_OBSERVED_REPS:
                continue

            # Session qualifies for N_target_eval
            target_eval_sessions.append(session)

            # Check single-session defect rate threshold
            if (
                issue_summary.defect_rate is not None
                and issue_summary.defect_rate >= self.config.SESSION_DEFECT_RATE_THRESHOLD
            ):
                qualifying_sessions.append(session)
                # Track timestamps
                if session.completed_at:
                    if first_observed_at is None or session.completed_at < first_observed_at:
                        first_observed_at = session.completed_at
                    if latest_observed_at is None or session.completed_at > latest_observed_at:
                        latest_observed_at = session.completed_at

        n_target_eval = len(target_eval_sessions)
        n_qualifying = len(qualifying_sessions)

        # 2. Recurrence Ratio Computation
        if n_target_eval >= self.config.ACTIONABLE_PATTERN_MIN_SESSIONS:
            recurrence_ratio = round(float(n_qualifying) / float(n_target_eval), 4)
        else:
            recurrence_ratio = 0.0

        # 3. Actionable Confidence Metric (C_qualifying_mean)
        if n_qualifying >= 1:
            conf_vals: List[float] = []
            for s in qualifying_sessions:
                iss = s.issues.get(issue_id)
                if iss and iss.mean_confidence is not None:
                    conf_vals.append(iss.mean_confidence)
            if conf_vals:
                qualifying_mean_confidence = round(sum(conf_vals) / len(conf_vals), 4)
            else:
                qualifying_mean_confidence = None
        else:
            qualifying_mean_confidence = None

        # 4. Deterministic 4-Step Precedence Decision Tree
        evidence_level: EvidenceLevel

        # Step 1: Insufficiency Check
        if (
            n_session_eligible < self.config.ACTIONABLE_PATTERN_MIN_SESSIONS
            or n_target_eval < self.config.MIN_TARGET_HEURISTIC_OBSERVED_REPS
        ):
            evidence_level = EvidenceLevel.INSUFFICIENT_DATA
            data_quality_flags.append("FLAG_INSUFFICIENT_DATA")

        # Step 2: No Evidence Check
        elif n_qualifying == 0:
            evidence_level = EvidenceLevel.NO_EVIDENCE
            qualifying_mean_confidence = None

        # Step 3: Emerging Occurrence Check
        elif n_qualifying == 1:
            evidence_level = EvidenceLevel.EMERGING_OCCURRENCE
            data_quality_flags.append("FLAG_EMERGING_OCCURRENCE")

        # Step 4: Pattern Qualification & Dual Confidence Gate
        elif n_qualifying >= self.config.ACTIONABLE_PATTERN_MIN_SESSIONS:
            # Dual Confidence Gate verification
            passes_aggregate_gate = (
                qualifying_mean_confidence is not None
                and qualifying_mean_confidence >= self.config.ACTIONABLE_PATTERN_MIN_CONFIDENCE
            )

            passes_per_session_floor = True
            for s in qualifying_sessions:
                iss = s.issues.get(issue_id)
                if (
                    iss is None
                    or iss.mean_confidence is None
                    or iss.mean_confidence < self.config.ACTIONABLE_PATTERN_SESSION_MIN_CONFIDENCE
                ):
                    passes_per_session_floor = False
                    break

            # Target occlusion check: qualifying sessions must have 0 target occlusions
            passes_occlusion_gate = True
            for s in qualifying_sessions:
                iss = s.issues.get(issue_id)
                if iss and iss.target_reps_occluded > 0:
                    passes_occlusion_gate = False
                    break

            if passes_aggregate_gate and passes_per_session_floor and passes_occlusion_gate:
                evidence_level = EvidenceLevel.ACTIONABLE_PATTERN
                data_quality_flags.append("FLAG_ACTIONABLE_PATTERN_QUALIFIED")
            else:
                evidence_level = EvidenceLevel.REPEATED_PATTERN
                data_quality_flags.append("FLAG_REPEATED_PATTERN_DEMOTION")
                if not passes_per_session_floor:
                    data_quality_flags.append("FLAG_SESSION_CONFIDENCE_FLOOR_BREACH")
                if not passes_aggregate_gate:
                    data_quality_flags.append("FLAG_AGGREGATE_CONFIDENCE_BREACH")
                if not passes_occlusion_gate:
                    data_quality_flags.append("FLAG_TARGET_REPETITION_OCCLUSION_DETECTED")

        else:
            # n_qualifying == 2 (REPEATED_PATTERN_MIN_SESSIONS <= n_qualifying < ACTIONABLE_PATTERN_MIN_SESSIONS)
            evidence_level = EvidenceLevel.REPEATED_PATTERN
            data_quality_flags.append("FLAG_REPEATED_PATTERN_QUALIFIED")

        source_session_ids = [s.session_id for s in target_eval_sessions]
        qualifying_session_ids = [s.session_id for s in qualifying_sessions]

        return AggregatedIssueEvidence(
            issue_id=issue_id,
            source_heuristic=source_heuristic,
            category=category,
            session_eligible_count=n_session_eligible,
            target_evaluated_sessions_count=n_target_eval,
            qualifying_sessions_count=n_qualifying,
            recurrence_ratio=recurrence_ratio,
            qualifying_mean_confidence=qualifying_mean_confidence,
            evidence_level=evidence_level,
            first_observed_at=first_observed_at,
            latest_observed_at=latest_observed_at,
            source_session_ids=source_session_ids,
            qualifying_session_ids=qualifying_session_ids,
            provenance_tiers_used=sorted(list(provenance_tiers_used)),
            aggregation_version="2.3.3",
            config_version="1.0.0",
            data_quality_flags=data_quality_flags,
        )

    # =========================================================================
    # EXERCISE-LEVEL COMPOSITE EVALUATION
    # =========================================================================

    def aggregate_exercise_evidence(
        self,
        sessions: List[Any],
        exercise_id: str,
        user_id: Optional[str] = None,
        lookback_k: Optional[int] = None,
    ) -> ExerciseEvidenceSummary:
        """
        Executes complete multi-session longitudinal technique evaluation for an exercise.

        Sequence:
        1. Approach B: Filter all completed sessions to eligible first.
        2. Select latest K (default LOOKBACK_SESSIONS_K = 5) eligible sessions.
        3. Determine canonical issue catalog for exercise.
        4. Evaluate each issue longitudinally via aggregate_issue_longitudinal.
        5. Formulate composite ExerciseEvidenceSummary with primary issue and status.
        """
        u_id = user_id or "user_default"
        k = lookback_k or self.config.LOOKBACK_SESSIONS_K

        # Step 1: Filter to eligible population
        eligible_sessions = self.filter_eligible_sessions(sessions, exercise_id=exercise_id)
        if eligible_sessions and not user_id:
            u_id = eligible_sessions[0].user_id

        # Step 2: Select latest K eligible sessions
        lookback_sessions = self.select_lookback_sessions(eligible_sessions, lookback_k=k)
        n_eligible = len(lookback_sessions)

        # Collect canonical issues to evaluate for this exercise
        canonical_heuristics = self.normalizer.get_mapped_heuristics_for_exercise(exercise_id)
        target_issue_map: Dict[str, Tuple[str, str, str]] = {}

        for h_name in canonical_heuristics:
            iss_id, src_h, cat = self._resolve_canonical_issue_info(exercise_id, h_name)
            target_issue_map[iss_id] = (iss_id, src_h, cat)

        # Also collect any additional issues present in lookback sessions
        for s in lookback_sessions:
            for iss_id, s_iss in s.issues.items():
                if iss_id not in target_issue_map:
                    target_issue_map[iss_id] = (
                        iss_id,
                        s_iss.source_heuristic,
                        s_iss.category,
                    )

        # Step 3: Evaluate each issue
        issues_aggregated: Dict[str, AggregatedIssueEvidence] = {}
        exercise_quality_flags: List[str] = []

        for iss_id, (target_iss, src_h, cat) in target_issue_map.items():
            issue_evidence = self.aggregate_issue_longitudinal(
                issue_id=target_iss,
                source_heuristic=src_h,
                category=cat,
                lookback_sessions=lookback_sessions,
            )
            issues_aggregated[target_iss] = issue_evidence
            for flag in issue_evidence.data_quality_flags:
                if flag not in exercise_quality_flags:
                    exercise_quality_flags.append(flag)

        # Step 4: Primary issue and composite level selection
        # Priority ladder: ACTIONABLE_PATTERN > REPEATED_PATTERN > EMERGING_OCCURRENCE > NO_EVIDENCE > INSUFFICIENT_DATA
        primary_issue_id: Optional[str] = None
        composite_level: EvidenceLevel = EvidenceLevel.INSUFFICIENT_DATA

        actionable_issues = [
            i for i in issues_aggregated.values() if i.evidence_level == EvidenceLevel.ACTIONABLE_PATTERN
        ]
        repeated_issues = [
            i for i in issues_aggregated.values() if i.evidence_level == EvidenceLevel.REPEATED_PATTERN
        ]
        emerging_issues = [
            i for i in issues_aggregated.values() if i.evidence_level == EvidenceLevel.EMERGING_OCCURRENCE
        ]
        no_evidence_issues = [
            i for i in issues_aggregated.values() if i.evidence_level == EvidenceLevel.NO_EVIDENCE
        ]

        if actionable_issues:
            composite_level = EvidenceLevel.ACTIONABLE_PATTERN
            # Select highest recurrence ratio, then highest qualifying count
            actionable_issues.sort(
                key=lambda x: (x.recurrence_ratio, x.qualifying_sessions_count), reverse=True
            )
            primary_issue_id = actionable_issues[0].issue_id
        elif repeated_issues:
            composite_level = EvidenceLevel.REPEATED_PATTERN
            repeated_issues.sort(
                key=lambda x: (x.recurrence_ratio, x.qualifying_sessions_count), reverse=True
            )
            primary_issue_id = repeated_issues[0].issue_id
        elif emerging_issues:
            composite_level = EvidenceLevel.EMERGING_OCCURRENCE
            emerging_issues.sort(key=lambda x: x.recurrence_ratio, reverse=True)
            primary_issue_id = emerging_issues[0].issue_id
        elif no_evidence_issues and len(no_evidence_issues) == len(issues_aggregated):
            composite_level = EvidenceLevel.NO_EVIDENCE
            primary_issue_id = None
        else:
            composite_level = EvidenceLevel.INSUFFICIENT_DATA
            primary_issue_id = None

        status_message = STATUS_MESSAGES.get(composite_level, STATUS_MESSAGES[EvidenceLevel.INSUFFICIENT_DATA])
        source_session_ids = [s.session_id for s in lookback_sessions]

        return ExerciseEvidenceSummary(
            aggregation_version="2.3.3",
            config_version="1.0.0",
            user_id=u_id,
            exercise_id=exercise_id,
            lookback_sessions_evaluated=n_eligible,
            eligible_sessions_count=n_eligible,
            evaluated_at=datetime.now(timezone.utc).isoformat(),
            primary_issue_id=primary_issue_id,
            evidence_level=composite_level,
            status_message=status_message,
            calculation_status=CalculationStatus.SUCCESS,
            source_session_ids=source_session_ids,
            data_quality_flags=exercise_quality_flags,
            issues=issues_aggregated,
        )
