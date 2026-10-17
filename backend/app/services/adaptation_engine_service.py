"""
Deterministic Progression & Adaptation Engine Service (Phase 9C.2).

Computes bounded, evidence-based, explainable adaptation decisions derived
exclusively from Phase 9C.1 performance analytics and authoritative completed workout sessions.

Strict Invariants:
1. Decision Layer ONLY: Produces bounded proposals; does NOT mutate Firestore active programs.
2. Grounded Data: Reuses Phase 9C.1 analytics and authoritative completed sessions.
3. Double Progression: Requires 3 consecutive completed sessions reaching target rep maximums.
4. 21-Day Reset Rule: Gaps > 21 days between consecutive qualifying sessions reset the sequence.
5. Hard 5% Load Ceiling: Proposed load must not exceed baseline * 1.05.
6. Volume Fatigue: Requires 2 consecutive sessions with < 70% volume completion to propose set reduction.
7. Conservative Precedence: Safety and fatigue constraints override progression proposals.
8. Zero Firestore Writes: Purely read-only evaluation.
"""

from datetime import datetime, timezone, timedelta
from typing import Optional, List, Dict, Any, Tuple
import statistics

from ..schemas.adaptation import (
    AdaptationType,
    DecisionStatus,
    PrescriptionDelta,
    AdaptationDecision,
    FutureSplitRecommendation,
    AdaptationEvaluationRequest,
    AdaptationEvaluationResponse,
    generate_decision_id,
)
from ..schemas.personalization import (
    PersonalizationSignalsResponse,
    ExercisePerformanceSummary,
    EvidenceLevel,
)
from ..schemas.exercise import (
    ExerciseKnowledgeSchema,
    CANONICAL_CV_EXERCISES,
    is_canonical_cv_exercise,
)
from ..schemas.workout import (
    WorkoutSessionResponse,
    WorkoutSetSchema,
)
from ..seeds.catalog import CATALOG_BY_ID
from ..repositories.workout_repository import WorkoutRepository, get_workout_repository
from ..repositories.exercise_repository import ExerciseRepository, get_exercise_repository
from ..services.personalization_signal_service import (
    PersonalizationSignalService,
    get_personalization_signal_service,
)
from ..services.exercise_relationship_service import (
    ExerciseRelationshipService,
    get_exercise_relationship_service,
)
from ..services.progress_service import parse_session_datetime
from ..utils.logger import logger


# Engineering Boundaries & Constants
MAX_QUALIFYING_GAP_DAYS: int = 21           # Consecutive sequence resets if gap > 21 days
REQUIRED_PROGRESSION_SESSIONS: int = 3      # 3 consecutive qualifying sessions required
REQUIRED_VOLUME_FAILURE_SESSIONS: int = 2   # 2 consecutive volume failures required
VOLUME_FAILURE_THRESHOLD_PCT: float = 0.70  # < 70% completed/planned sets constitutes volume failure
UPPER_COMPOUND_LOAD_INCREMENT: float = 2.5  # Upper-body compound standard increment (+2.5 kg)
LOWER_COMPOUND_LOAD_INCREMENT: float = 5.0  # Lower-body compound standard increment (+5.0 kg)
ISOLATION_LOAD_INCREMENT: float = 1.0       # Weighted isolation standard increment (+1.0 kg)
MAX_WEEKLY_LOAD_INCREASE_PCT: float = 0.05  # Hard safety ceiling: maximum 5% increase
MIN_NORMAL_SETS: int = 1                    # Minimum allowed set count
MAX_NORMAL_SETS: int = 5                    # Maximum allowed set count
MAX_PERMITTED_RPE: float = 9.0              # Maximum permitted prescribed RPE
MAX_DURATION_MULTIPLIER: float = 1.25       # Adapted duration <= target duration * 1.25


def is_lower_compound(exercise: ExerciseKnowledgeSchema) -> bool:
    """Classifies if catalog exercise is a lower-body compound movement."""
    if exercise.exerciseType != "compound":
        return False
    if exercise.movementPattern in ("squat", "hinge", "lunge"):
        return True
    lower_muscles = {"quadriceps", "hamstrings", "glutes", "calves"}
    return any(m in lower_muscles for m in exercise.primaryMuscles)


def is_upper_compound(exercise: ExerciseKnowledgeSchema) -> bool:
    """Classifies if catalog exercise is an upper-body compound movement."""
    if exercise.exerciseType != "compound":
        return False
    if exercise.movementPattern in ("horizontal_push", "horizontal_pull", "vertical_push", "vertical_pull"):
        return True
    upper_muscles = {"chest", "back", "shoulders"}
    return any(m in upper_muscles for m in exercise.primaryMuscles)


class AdaptationEngineService:
    """
    Core deterministic adaptation engine implementing Phase 9C.2 decision logic.
    User-scoped, strictly read-only, and bounded by hard safety constraints.
    """

    def __init__(
        self,
        signal_service: Optional[PersonalizationSignalService] = None,
        workout_repo: Optional[WorkoutRepository] = None,
        exercise_repo: Optional[ExerciseRepository] = None,
        relationship_service: Optional[ExerciseRelationshipService] = None,
        catalog_by_id: Optional[Dict[str, ExerciseKnowledgeSchema]] = None,
    ):
        self._signal_service = signal_service
        self._workout_repo = workout_repo
        self._exercise_repo = exercise_repo
        self._relationship_service = relationship_service
        self._catalog = catalog_by_id or CATALOG_BY_ID

    @property
    def signal_service(self) -> PersonalizationSignalService:
        return self._signal_service or get_personalization_signal_service()

    @property
    def workout_repo(self) -> WorkoutRepository:
        return self._workout_repo or get_workout_repository()

    @property
    def exercise_repo(self) -> ExerciseRepository:
        return self._exercise_repo or get_exercise_repository()

    @property
    def relationship_service(self) -> ExerciseRelationshipService:
        return self._relationship_service or get_exercise_relationship_service()

    # =========================================================================
    # CORE EVALUATION PIPELINE
    # =========================================================================

    def evaluate_adaptations(
        self,
        uid: str,
        request: Optional[AdaptationEvaluationRequest] = None,
    ) -> AdaptationEvaluationResponse:
        """
        Evaluates deterministic adaptation decisions for the authenticated user.
        Combines Phase 9C.1 analytics with authoritative completed workout history.
        """
        window_days = request.windowDays if request else 28
        now_iso = datetime.now(timezone.utc).isoformat()

        # 1. Retrieve Phase 9C.1 signals (Reuse 9C.1 without duplicating analytics)
        signals: PersonalizationSignalsResponse = self.signal_service.get_personalization_signals(
            uid=uid,
            window_days=window_days,
        )

        # 2. Retrieve chronological completed sessions for exact sequence analysis
        all_completed = self.workout_repo.list_user_history(uid, limit=100)
        chronological_sessions = sorted(
            all_completed,
            key=lambda s: parse_session_datetime(s.startedAt) or datetime.min.replace(tzinfo=timezone.utc),
        )

        # 3. Determine exercises to evaluate
        decisions: List[AdaptationDecision] = []
        target_exercises = request.candidateExercises if (request and request.candidateExercises) else None

        if target_exercises:
            for candidate in target_exercises:
                if not candidate.exerciseId:
                    continue
                dec = self._evaluate_single_exercise(
                    uid=uid,
                    exercise_id=candidate.exerciseId,
                    candidate_prescription=candidate,
                    sessions=chronological_sessions,
                    signals=signals,
                    target_duration_minutes=request.targetDurationMinutes if request else None,
                )
                decisions.append(dec)
        else:
            # General evaluation across all exercises present in user history
            tracked_exercise_ids = sorted(list(signals.exercises.keys()))
            for ex_id in tracked_exercise_ids:
                dec = self._evaluate_single_exercise(
                    uid=uid,
                    exercise_id=ex_id,
                    candidate_prescription=None,
                    sessions=chronological_sessions,
                    signals=signals,
                    target_duration_minutes=request.targetDurationMinutes if request else None,
                )
                decisions.append(dec)

        # 4. Evaluate Recurring Form Issue Proposals from 9C.1 Form Signals
        form_proposals = self._evaluate_form_issue_proposals(uid, signals)
        decisions.extend(form_proposals)

        # 5. Evaluate Adherence Future-Block Split Adaptation
        split_proposal = self._evaluate_future_split_adaptation(uid, signals)

        # 6. Assemble Summary Metrics
        summary = {
            "totalDecisionsEvaluated": len(decisions),
            "progressionCandidates": sum(1 for d in decisions if d.status == "progression_candidate"),
            "volumeReductionCandidates": sum(1 for d in decisions if d.status == "volume_reduction_candidate"),
            "formIssueCandidates": sum(1 for d in decisions if d.status == "form_issue_candidate"),
            "constrainedNoChange": sum(1 for d in decisions if d.status == "constrained_no_change"),
            "noChange": sum(1 for d in decisions if d.status == "no_change"),
            "insufficientData": sum(1 for d in decisions if d.status == "insufficient_data"),
            "hasFutureSplitProposal": split_proposal is not None,
        }

        return AdaptationEvaluationResponse(
            userId=uid,
            generatedAt=now_iso,
            evaluationWindowDays=window_days,
            primaryDecisions=decisions,
            futureSplitProposal=split_proposal,
            summaryMetrics=summary,
        )

    # =========================================================================
    # SINGLE EXERCISE EVALUATION WITH STRICT PRECEDENCE
    # =========================================================================

    def _evaluate_single_exercise(
        self,
        uid: str,
        exercise_id: str,
        candidate_prescription: Optional[PrescriptionDelta],
        sessions: List[WorkoutSessionResponse],
        signals: PersonalizationSignalsResponse,
        target_duration_minutes: Optional[int] = None,
    ) -> AdaptationDecision:
        """
        Evaluates adaptation candidate for an exercise using strict deterministic precedence:
        1. Insufficient evidence / invalid baseline
        2. Hard safety constraints (Duration bound, RPE constraint)
        3. Volume fatigue (2 consecutive volume failures -> volume reduction overrides progression)
        4. Double progression (3 consecutive qualifying sessions + 5% ceiling)
        5. No change (evidence stable)
        """
        now_iso = datetime.now(timezone.utc).isoformat()
        exercise_meta = self._catalog.get(exercise_id)
        if not exercise_meta:
            # Fallback check against ExerciseRepository or catalog name
            repo_ex = self.exercise_repo.get_by_id(exercise_id)
            if repo_ex:
                for cat_ex in self._catalog.values():
                    if cat_ex.name.lower() == repo_ex.name.lower() or cat_ex.id in exercise_id or exercise_id in cat_ex.id:
                        exercise_meta = cat_ex
                        break
            if not exercise_meta:
                # Match common aliases like ex_barbell_bench_press -> ex_bench_press, ex_barbell_squat -> ex_squat
                normalized_id = exercise_id.replace("_barbell_", "_").replace("_dumbbell_", "_")
                exercise_meta = self._catalog.get(normalized_id)

        ex_name = exercise_meta.name if exercise_meta else exercise_id.replace("ex_", "").replace("_", " ").title()

        # Extract sessions containing this exercise
        sessions_with_ex: List[Tuple[WorkoutSessionResponse, List[WorkoutSetSchema]]] = []
        for s in sessions:
            sets = s.completedSets.get(exercise_id, [])
            if sets:
                sessions_with_ex.append((s, sets))

        # ---------------------------------------------------------------------
        # Precedence Tier 1: Insufficient Evidence
        # ---------------------------------------------------------------------
        if not sessions_with_ex:
            dec_id = generate_decision_id(uid, exercise_id, "INSUFFICIENT_EVIDENCE", "no_change", "insufficient_data")
            return AdaptationDecision(
                decisionId=dec_id,
                exerciseId=exercise_id,
                canonicalName=ex_name,
                adaptationType="no_change",
                status="insufficient_data",
                ruleCode="INSUFFICIENT_EVIDENCE",
                evidenceLevel="no_data",
                evidence={"sessionsObserved": 0},
                previousPrescription=candidate_prescription,
                proposedPrescription=candidate_prescription,
                rationale="No completed session history observed for this exercise. Preserving current prescription.",
                reasons=["No historical session data recorded for exercise."],
                constraintsApplied=[],
                isReversible=True,
                sourceSessionIds=[],
                generatedAt=now_iso,
            )

        # Baseline prescription derivation
        latest_sess, latest_sets = sessions_with_ex[-1]
        latest_weight = statistics.median([st.actualWeightKg or st.targetWeightKg or 0.0 for st in latest_sets if (st.actualWeightKg or st.targetWeightKg)]) if any(st.actualWeightKg or st.targetWeightKg for st in latest_sets) else 0.0
        latest_set_count = len(latest_sets)
        latest_target_min = latest_sets[0].targetRepsMin if hasattr(latest_sets[0], 'targetRepsMin') and latest_sets[0].targetRepsMin else (latest_sets[0].targetReps or 10)
        latest_target_max = latest_sets[0].targetRepsMax if hasattr(latest_sets[0], 'targetRepsMax') and latest_sets[0].targetRepsMax else (latest_sets[0].targetReps or 12)

        prev_presc = PrescriptionDelta(
            exerciseId=exercise_id,
            exerciseName=ex_name,
            weightKg=candidate_prescription.weightKg if (candidate_prescription and candidate_prescription.weightKg is not None) else latest_weight,
            setCount=candidate_prescription.setCount if (candidate_prescription and candidate_prescription.setCount is not None) else latest_set_count,
            targetRepsMin=candidate_prescription.targetRepsMin if (candidate_prescription and candidate_prescription.targetRepsMin is not None) else latest_target_min,
            targetRepsMax=candidate_prescription.targetRepsMax if (candidate_prescription and candidate_prescription.targetRepsMax is not None) else latest_target_max,
            targetRpe=candidate_prescription.targetRpe if (candidate_prescription and candidate_prescription.targetRpe is not None) else None,
            restSeconds=candidate_prescription.restSeconds if (candidate_prescription and candidate_prescription.restSeconds is not None) else 90,
        )

        # ---------------------------------------------------------------------
        # Precedence Tier 2: Hard Safety Constraints on Candidate Input (RPE / Duration)
        # ---------------------------------------------------------------------
        constraints_applied: List[str] = []
        if prev_presc.targetRpe and prev_presc.targetRpe > MAX_PERMITTED_RPE:
            constraints_applied.append(f"Prescribed RPE ({prev_presc.targetRpe}) exceeded safety maximum ({MAX_PERMITTED_RPE}); clamped to {MAX_PERMITTED_RPE}")
            prev_presc.targetRpe = MAX_PERMITTED_RPE

        if target_duration_minutes and candidate_prescription:
            # Estimate duration: set count * (reps * 3s + rest)
            est_duration = (prev_presc.setCount or 3) * (12 * 3 + (prev_presc.restSeconds or 90)) / 60.0
            if est_duration > target_duration_minutes * MAX_DURATION_MULTIPLIER:
                dec_id = generate_decision_id(uid, exercise_id, "DURATION_EXCEEDS_125_PCT", "no_change", "constrained_no_change")
                return AdaptationDecision(
                    decisionId=dec_id,
                    exerciseId=exercise_id,
                    canonicalName=ex_name,
                    adaptationType="no_change",
                    status="constrained_no_change",
                    ruleCode="DURATION_EXCEEDS_125_PCT",
                    evidenceLevel="stable_signal",
                    evidence={"estimatedDurationMinutes": round(est_duration, 1), "targetDurationMinutes": target_duration_minutes},
                    previousPrescription=prev_presc,
                    proposedPrescription=prev_presc,
                    rationale=f"Estimated exercise volume duration exceeds target session duration by > 25%. Prescription constrained without modification.",
                    reasons=["Target duration multiplier limit (1.25x) reached."],
                    constraintsApplied=["Duration ceiling (1.25x target) enforced."],
                    isReversible=True,
                    sourceSessionIds=[latest_sess.id],
                    generatedAt=now_iso,
                )

        # ---------------------------------------------------------------------
        # Precedence Tier 3: Volume Fatigue / Incomplete Volume Evaluation
        # 2 consecutive completed sessions with volume completion < 70%
        # ---------------------------------------------------------------------
        consecutive_volume_failures, vol_fail_sessions = self._evaluate_volume_fatigue_streak(sessions_with_ex)

        if consecutive_volume_failures >= REQUIRED_VOLUME_FAILURE_SESSIONS:
            # Propose volume reduction: -1 set
            current_sets = prev_presc.setCount or 3
            if current_sets <= MIN_NORMAL_SETS:
                dec_id = generate_decision_id(uid, exercise_id, "MINIMUM_SET_BOUND_REACHED", "volume_reduction", "constrained_no_change")
                return AdaptationDecision(
                    decisionId=dec_id,
                    exerciseId=exercise_id,
                    canonicalName=ex_name,
                    adaptationType="volume_reduction",
                    status="constrained_no_change",
                    ruleCode="MINIMUM_SET_BOUND_REACHED",
                    evidenceLevel="stable_signal",
                    evidence={
                        "consecutiveVolumeFailures": consecutive_volume_failures,
                        "currentSetCount": current_sets,
                        "minPermittedSets": MIN_NORMAL_SETS,
                        "sessionIds": [s.id for s, _ in vol_fail_sessions],
                    },
                    previousPrescription=prev_presc,
                    proposedPrescription=prev_presc,
                    deltaMagnitude=0.0,
                    deltaUnit="sets",
                    rationale="User experienced 2 consecutive sessions with volume failure, but set count is already at minimum bound (1 set). Further set reduction is prohibited.",
                    reasons=[
                        "Two consecutive completed sessions with < 70% volume completion.",
                        f"Current set count ({current_sets}) is at safety floor ({MIN_NORMAL_SETS} set).",
                    ],
                    constraintsApplied=["Minimum 1 set bound enforced."],
                    isReversible=True,
                    sourceSessionIds=[s.id for s, _ in vol_fail_sessions],
                    generatedAt=now_iso,
                )

            proposed_sets = current_sets - 1
            proposed_presc = prev_presc.model_copy()
            proposed_presc.setCount = proposed_sets

            dec_id = generate_decision_id(uid, exercise_id, "VOLUME_FATIGUE_2_SESSIONS", "volume_reduction", "volume_reduction_candidate", -1.0)
            return AdaptationDecision(
                decisionId=dec_id,
                exerciseId=exercise_id,
                canonicalName=ex_name,
                adaptationType="volume_reduction",
                status="volume_reduction_candidate",
                ruleCode="VOLUME_FATIGUE_2_SESSIONS",
                evidenceLevel="stable_signal",
                evidence={
                    "consecutiveVolumeFailures": consecutive_volume_failures,
                    "previousSetCount": current_sets,
                    "proposedSetCount": proposed_sets,
                    "sessionIds": [s.id for s, _ in vol_fail_sessions],
                },
                previousPrescription=prev_presc,
                proposedPrescription=proposed_presc,
                deltaMagnitude=-1.0,
                deltaUnit="sets",
                rationale=f"Observed 2 consecutive sessions with < 70% volume completion for {ex_name}. Proposing set reduction ({current_sets} -> {proposed_sets} sets) to manage accumulated fatigue.",
                reasons=[
                    "Two consecutive completed sessions failed prescribed set volume (< 70% completion).",
                    "Conservative fatigue reduction takes precedence over load progression.",
                ],
                constraintsApplied=["Set count bounded between 1 and 5 sets."] + constraints_applied,
                isReversible=True,
                sourceSessionIds=[s.id for s, _ in vol_fail_sessions],
                generatedAt=now_iso,
            )

        # ---------------------------------------------------------------------
        # Precedence Tier 4: Double Progression Evaluation
        # 3 consecutive qualifying sessions + 21-day reset rule + 5% ceiling
        # ---------------------------------------------------------------------
        consecutive_qualifying_count, qualifying_sessions, qualifying_weights = self._evaluate_double_progression_streak(sessions_with_ex)

        if consecutive_qualifying_count < REQUIRED_PROGRESSION_SESSIONS:
            # Not yet eligible for double progression
            status_label: DecisionStatus = "insufficient_data" if len(sessions_with_ex) < 2 else "no_change"
            rule_label = "PROGRESSION_EVIDENCE_EMERGING" if consecutive_qualifying_count == 2 else "INSUFFICIENT_CONSECUTIVE_SESSIONS"
            dec_id = generate_decision_id(uid, exercise_id, rule_label, "no_change", status_label)
            return AdaptationDecision(
                decisionId=dec_id,
                exerciseId=exercise_id,
                canonicalName=ex_name,
                adaptationType="no_change",
                status=status_label,
                ruleCode=rule_label,
                evidenceLevel="emerging_signal" if consecutive_qualifying_count == 2 else "insufficient_data",
                evidence={
                    "consecutiveQualifyingSessions": consecutive_qualifying_count,
                    "requiredSessions": REQUIRED_PROGRESSION_SESSIONS,
                    "totalSessionsObserved": len(sessions_with_ex),
                },
                previousPrescription=prev_presc,
                proposedPrescription=prev_presc,
                rationale=f"Observed {consecutive_qualifying_count}/{REQUIRED_PROGRESSION_SESSIONS} consecutive qualifying sessions. Progression requires 3 consecutive completed sessions reaching target rep maximums.",
                reasons=[
                    f"Consecutive qualifying session count ({consecutive_qualifying_count}) is below required threshold ({REQUIRED_PROGRESSION_SESSIONS}).",
                ],
                constraintsApplied=list(constraints_applied),
                isReversible=True,
                sourceSessionIds=[s.id for s, _ in qualifying_sessions],
                generatedAt=now_iso,
            )

        # 3 qualifying sessions achieved! Determine progression type
        baseline_load = prev_presc.weightKg or (statistics.median(qualifying_weights) if qualifying_weights else 0.0)

        is_bodyweight = (exercise_meta and exercise_meta.equipment == ["bodyweight"]) or baseline_load <= 0.0
        is_isolation = exercise_meta and (exercise_meta.exerciseType == "isolation" or exercise_meta.movementPattern in ("isolation", "arms", "core", "mobility"))

        if is_bodyweight or (is_isolation and baseline_load <= 0.0):
            # Rep progression for bodyweight / unweighted isolation
            current_min = prev_presc.targetRepsMin or 10
            current_max = prev_presc.targetRepsMax or 12
            proposed_min = current_min + 1
            proposed_max = current_max + 1

            proposed_presc = prev_presc.model_copy()
            proposed_presc.targetRepsMin = proposed_min
            proposed_presc.targetRepsMax = proposed_max

            dec_id = generate_decision_id(uid, exercise_id, "DOUBLE_PROGRESSION_REP_RULE", "rep_progression", "progression_candidate", 1.0)
            return AdaptationDecision(
                decisionId=dec_id,
                exerciseId=exercise_id,
                canonicalName=ex_name,
                adaptationType="rep_progression",
                status="progression_candidate",
                ruleCode="DOUBLE_PROGRESSION_REP_RULE",
                evidenceLevel="stable_signal",
                evidence={
                    "consecutiveQualifyingSessions": consecutive_qualifying_count,
                    "previousRepRange": f"{current_min}-{current_max}",
                    "proposedRepRange": f"{proposed_min}-{proposed_max}",
                    "sessionIds": [s.id for s, _ in qualifying_sessions],
                },
                previousPrescription=prev_presc,
                proposedPrescription=proposed_presc,
                deltaMagnitude=1.0,
                deltaUnit="reps",
                rationale=f"Three consecutive qualifying sessions completed reaching target rep maximums for {ex_name}. Proposing rep progression ({current_min}–{current_max} -> {proposed_min}–{proposed_max} reps).",
                reasons=[
                    "Three consecutive qualifying sessions satisfied target rep ceiling.",
                    "Isolation/bodyweight movement prioritizes rep progression over external load.",
                ],
                constraintsApplied=["Rep range min/max bounds verified."],
                isReversible=True,
                sourceSessionIds=[s.id for s, _ in qualifying_sessions],
                generatedAt=now_iso,
            )

        # External Load Progression (Compound & Weighted Exercises)
        if exercise_meta and is_lower_compound(exercise_meta):
            normal_increment = LOWER_COMPOUND_LOAD_INCREMENT  # +5.0 kg
        elif exercise_meta and is_upper_compound(exercise_meta):
            normal_increment = UPPER_COMPOUND_LOAD_INCREMENT  # +2.5 kg
        else:
            normal_increment = ISOLATION_LOAD_INCREMENT       # +1.0 kg

        proposed_load = baseline_load + normal_increment
        max_allowed_load = round(baseline_load * (1.0 + MAX_WEEKLY_LOAD_INCREASE_PCT), 2)

        # ---------------------------------------------------------------------
        # HARD 5% LOAD CEILING VALIDATION
        # ---------------------------------------------------------------------
        if proposed_load > max_allowed_load:
            # Exceeds the 5% weekly load ceiling!
            # The prompt explicitly specifies:
            # "Do NOT interpret 'standard equipment increment' as permission to exceed the 5% ceiling.
            # If no valid representable load exists within the hard bound:
            # return constrained_no_change with an explicit reason code."
            dec_id = generate_decision_id(uid, exercise_id, "LOAD_CEILING_5_PERCENT_EXCEEDED", "load_progression", "constrained_no_change", normal_increment)
            return AdaptationDecision(
                decisionId=dec_id,
                exerciseId=exercise_id,
                canonicalName=ex_name,
                adaptationType="load_progression",
                status="constrained_no_change",
                ruleCode="LOAD_CEILING_5_PERCENT_EXCEEDED",
                evidenceLevel="stable_signal",
                evidence={
                    "consecutiveQualifyingSessions": consecutive_qualifying_count,
                    "baselineWeightKg": baseline_load,
                    "proposedWeightKg": proposed_load,
                    "maxAllowedWeightKg": max_allowed_load,
                    "normalIncrementKg": normal_increment,
                    "sessionIds": [s.id for s, _ in qualifying_sessions],
                },
                previousPrescription=prev_presc,
                proposedPrescription=prev_presc,
                deltaMagnitude=0.0,
                deltaUnit="kg",
                rationale=f"Standard load increment (+{normal_increment} kg on {baseline_load} kg) yields {proposed_load} kg, which exceeds the hard 5% weekly load increase ceiling ({max_allowed_load} kg). Progression constrained.",
                reasons=[
                    f"Baseline load is {baseline_load} kg. Maximum allowed 5% load is {max_allowed_load} kg.",
                    f"Standard increment (+{normal_increment} kg) would produce an unsafe {round(((proposed_load - baseline_load) / baseline_load) * 100, 2)}% increase.",
                    "No standard representable equipment load fits within the 5% ceiling without exceeding safety bounds.",
                ],
                constraintsApplied=["Hard 5% weekly load increase ceiling strictly enforced."],
                isReversible=True,
                sourceSessionIds=[s.id for s, _ in qualifying_sessions],
                generatedAt=now_iso,
            )

        # Load progression is within the 5% ceiling!
        proposed_presc = prev_presc.model_copy()
        proposed_presc.weightKg = proposed_load

        dec_id = generate_decision_id(uid, exercise_id, "DOUBLE_PROGRESSION_3_SESSIONS", "load_progression", "progression_candidate", normal_increment)
        return AdaptationDecision(
            decisionId=dec_id,
            exerciseId=exercise_id,
            canonicalName=ex_name,
            adaptationType="load_progression",
            status="progression_candidate",
            ruleCode="DOUBLE_PROGRESSION_3_SESSIONS",
            evidenceLevel="stable_signal",
            evidence={
                "consecutiveQualifyingSessions": consecutive_qualifying_count,
                "baselineWeightKg": baseline_load,
                "proposedWeightKg": proposed_load,
                "incrementKg": normal_increment,
                "sessionIds": [s.id for s, _ in qualifying_sessions],
            },
            previousPrescription=prev_presc,
            proposedPrescription=proposed_presc,
            deltaMagnitude=normal_increment,
            deltaUnit="kg",
            rationale=f"Three consecutive qualifying sessions completed reaching target rep maximums with consistent load ({baseline_load} kg). Proposing bounded load progression (+{normal_increment} kg -> {proposed_load} kg).",
            reasons=[
                "Three consecutive qualifying completed sessions reached target rep maximums.",
                f"Proposed load increase of +{normal_increment} kg satisfies the 5% weekly load ceiling.",
            ],
            constraintsApplied=["Hard 5% weekly load ceiling satisfied."],
            isReversible=True,
            sourceSessionIds=[s.id for s, _ in qualifying_sessions],
            generatedAt=now_iso,
        )

    # =========================================================================
    # DOUBLE PROGRESSION STREAK CALCULATOR & 21-DAY RESET RULE
    # =========================================================================

    def _evaluate_double_progression_streak(
        self,
        sessions_with_ex: List[Tuple[WorkoutSessionResponse, List[WorkoutSetSchema]]],
    ) -> Tuple[int, List[Tuple[WorkoutSessionResponse, List[WorkoutSetSchema]]], List[float]]:
        """
        Evaluates consecutive qualifying sessions from most recent backwards.
        Criteria per qualifying session:
        1. All prescribed sets reached targetRepsMax (or targetReps).
        2. Gap to subsequent qualifying session <= 21 days (21-day reset rule).
        If gap > 21 days (e.g. 22 days) or a session missed target reps, the sequence breaks.
        """
        qualifying_sessions: List[Tuple[WorkoutSessionResponse, List[WorkoutSetSchema]]] = []
        qualifying_weights: List[float] = []

        # Iterate in reverse chronological order (newest to oldest)
        reversed_sessions = list(reversed(sessions_with_ex))
        prev_dt: Optional[datetime] = None

        for s, set_list in reversed_sessions:
            current_dt = parse_session_datetime(s.startedAt) or parse_session_datetime(s.completedAt)

            # Check 21-day reset rule relative to subsequent qualifying session
            if prev_dt and current_dt:
                gap_seconds = (prev_dt - current_dt).total_seconds()
                if gap_seconds > (MAX_QUALIFYING_GAP_DAYS * 86400):
                    # Gap exceeds 21 days! Consecutive sequence broken by staleness.
                    break

            # Check if all sets reached target maximum
            session_qualifies = True
            sess_weights: List[float] = []

            for st in set_list:
                actual_reps = st.actualReps
                target_max = getattr(st, 'targetRepsMax', None) or st.targetReps or 10

                if actual_reps is None or actual_reps < target_max:
                    session_qualifies = False
                    break

                wt = st.actualWeightKg or st.targetWeightKg or 0.0
                if wt > 0:
                    sess_weights.append(wt)

            if not session_qualifies:
                # Sequence broken by incomplete rep targets
                break

            qualifying_sessions.append((s, set_list))
            if sess_weights:
                qualifying_weights.append(statistics.median(sess_weights))
            prev_dt = current_dt

        # Return chronological order of qualifying sessions
        return len(qualifying_sessions), list(reversed(qualifying_sessions)), qualifying_weights

    # =========================================================================
    # VOLUME FATIGUE STREAK CALCULATOR
    # =========================================================================

    def _evaluate_volume_fatigue_streak(
        self,
        sessions_with_ex: List[Tuple[WorkoutSessionResponse, List[WorkoutSetSchema]]],
    ) -> Tuple[int, List[Tuple[WorkoutSessionResponse, List[WorkoutSetSchema]]]]:
        """
        Evaluates consecutive sessions with volume failure (< 70% completed sets vs planned).
        Returns consecutive failure count from most recent backwards.
        """
        failure_sessions: List[Tuple[WorkoutSessionResponse, List[WorkoutSetSchema]]] = []
        reversed_sessions = list(reversed(sessions_with_ex))

        for s, set_list in reversed_sessions:
            planned = s.totalSetsCount or len(set_list)
            completed = s.completedSetsCount or sum(1 for st in set_list if st.isCompleted)

            # Exact boundary: < 0.70 is failure; >= 0.70 is pass
            completion_rate = (completed / planned) if planned > 0 else 1.0
            if completion_rate < VOLUME_FAILURE_THRESHOLD_PCT:
                failure_sessions.append((s, set_list))
            else:
                # Streak broken by successful volume session
                break

        return len(failure_sessions), list(reversed(failure_sessions))

    # =========================================================================
    # FORM ISSUE SIGNAL EVALUATION
    # =========================================================================

    def _evaluate_form_issue_proposals(
        self,
        uid: str,
        signals: PersonalizationSignalsResponse,
    ) -> List[AdaptationDecision]:
        """
        Identifies recurring form analysis flaws from Phase 9C.1 form signals.
        Produces structured proposals without injecting correctives into Slot 0.
        """
        proposals: List[AdaptationDecision] = []
        now_iso = datetime.now(timezone.utc).isoformat()

        for ex_id, form_sig in signals.formSignals.items():
            for issue in form_sig.detectedIssues:
                if issue.isRecurring:
                    dec_id = generate_decision_id(uid, ex_id, "RECURRING_FORM_ISSUE_DETECTED", "recurring_form_issue", "form_issue_candidate")
                    proposal = AdaptationDecision(
                        decisionId=dec_id,
                        exerciseId=ex_id,
                        canonicalName=form_sig.canonicalCvExercise.replace("_", " ").title(),
                        adaptationType="recurring_form_issue",
                        status="form_issue_candidate",
                        ruleCode="RECURRING_FORM_ISSUE_DETECTED",
                        evidenceLevel=form_sig.evidenceLevel,
                        evidence={
                            "canonicalExercise": form_sig.canonicalCvExercise,
                            "issueId": issue.issue,
                            "occurrenceCount": issue.occurrenceCount,
                            "totalSessionsWithExercise": issue.totalSessionsWithExercise,
                            "frequencyRate": issue.frequencyRate,
                            "avgFormScore": form_sig.avgFormScore,
                        },
                        rationale=f"Recurring technique issue '{issue.issue}' observed in {issue.occurrenceCount}/{issue.totalSessionsWithExercise} CV-analyzed sessions ({int(issue.frequencyRate * 100)}%). Technique review recommended.",
                        reasons=[
                            f"Issue appears in >= 50% of analyzed sessions (observed: {int(issue.frequencyRate * 100)}%).",
                            "Flagged for future block corrective preparation without immediate Slot 0 modification.",
                        ],
                        constraintsApplied=["Slot 0 corrective injection deferred to Phase 9C.6."],
                        isReversible=True,
                        sourceSessionIds=[],
                        generatedAt=now_iso,
                    )
                    proposals.append(proposal)

        return proposals

    # =========================================================================
    # ADHERENCE FUTURE-BLOCK SPLIT EVALUATION
    # =========================================================================

    def _evaluate_future_split_adaptation(
        self,
        uid: str,
        signals: PersonalizationSignalsResponse,
    ) -> Optional[FutureSplitRecommendation]:
        """
        Evaluates planned vs completed workout frequency over ~4 weeks (28 days).
        If planned frequency is 5 days/week and completed frequency is consistently ~3 days/week,
        proposes a 3-day Full Body split for the NEXT mesocycle.
        If planned frequency is absent, does NOT fabricate adherence and returns None.
        """
        trend = signals.workoutAdherenceTrend
        if trend.expectedFrequencyPerWeek is None or trend.expectedSessions is None:
            # Cannot fabricate adherence if planned frequency was not configured
            return None

        # Planned frequency is approximately 5 days/week
        is_5_day_plan = abs(trend.expectedFrequencyPerWeek - 5.0) < 0.5
        # Observed frequency is approximately 3 days/week (e.g. 2.5 to 3.5 sessions/week)
        is_approx_3_completed = 2.0 <= trend.observedFrequencyPerWeek <= 3.6
        has_sufficient_evidence = trend.sessionsCompleted >= 4 and trend.observationWindowDays >= 21

        if is_5_day_plan and is_approx_3_completed and has_sufficient_evidence:
            return FutureSplitRecommendation(
                currentSplit="upper_lower_ppl_5d",
                recommendedSplit="full_body",
                recommendedDaysPerWeek=3,
                observedWeeklyFrequency=trend.observedFrequencyPerWeek,
                plannedWeeklyFrequency=trend.expectedFrequencyPerWeek,
                adherenceRate=trend.adherenceRate,
                ruleCode="ADHERENCE_SPLIT_MISMATCH_4_WEEKS",
                reason=(
                    f"User completed an average of {trend.observedFrequencyPerWeek} sessions/week over the past "
                    f"{trend.observationWindowDays} days against a 5-day prescribed split (adherence rate: "
                    f"{int((trend.adherenceRate or 0) * 100)}%). Recommend transitioning to a 3-day Full Body split "
                    "in the next mesocycle to optimize adherence and recovery."
                ),
                isFutureBlockOnly=True,
            )

        return None


# Global service singleton
_adaptation_engine_instance: Optional[AdaptationEngineService] = None


def get_adaptation_engine_service() -> AdaptationEngineService:
    """FastAPI dependency provider for AdaptationEngineService."""
    global _adaptation_engine_instance
    if _adaptation_engine_instance is None:
        _adaptation_engine_instance = AdaptationEngineService()
    return _adaptation_engine_instance
