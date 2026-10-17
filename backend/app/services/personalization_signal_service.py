"""
Personalization & Adaptive Performance Signal Service (Phase 9C.1).

Computes deterministic, reproducible, user-scoped personalization signals derived
exclusively from authoritative workout session history, exercise catalog definitions,
and computer-vision form analysis history.

Strict Invariants:
1. Analytics ONLY: Does NOT prescribe weights, adjust sets, or alter workout programs.
2. Grounded Data: Computes metrics only from verified completed sessions; no temporary UI state.
3. Reuse Progress Logic: Authoritative 1RM (Epley formula) and PRs reuse ProgressService logic.
4. Outlier Safeguards: Requires >= 2 observations for any trend; single anomalies cannot dominate.
5. Non-Medical Language: Prohibits physiological inferences, recovery claims, or medical diagnosis.
"""

from datetime import datetime, timezone, timedelta
from typing import Optional, List, Dict, Any, Tuple
import statistics

from ..schemas.exercise import CANONICAL_CV_EXERCISES, CV_KEY_TO_CATALOG_ID
from ..schemas.workout import WorkoutSessionResponse, WorkoutSetSchema
from ..schemas.personalization import (
    EvidenceLevel,
    TrendDirection,
    PerformanceTrajectory,
    AdherenceTier,
    RepPerformanceStatus,
    ConsistencyStatus,
    FormScoreTrend,
    LoadProgressionSignal,
    RepPerformanceSignal,
    ExercisePerformanceSummary,
    SetAdherenceSignal,
    WorkoutAdherenceTrend,
    FormIssueFrequency,
    ExerciseFormSignal,
    PersonalizationSignalsResponse,
)
from ..repositories.workout_repository import WorkoutRepository, get_workout_repository
from ..repositories.exercise_repository import ExerciseRepository, get_exercise_repository
from ..repositories.user_repository import UserRepository, get_user_repository
from ..repositories.form_analysis_repository import FormAnalysisRepository, get_form_analysis_repository
from ..services.progress_service import ProgressService, parse_session_datetime
from ..utils.logger import logger


# Deterministic Engineering Thresholds
LOAD_CHANGE_THRESHOLD_PCT: float = 2.5        # +/- 2.5% load delta to declare increasing/decreasing
TRAJECTORY_CHANGE_THRESHOLD_PCT: float = 3.0   # +/- 3.0% 1RM delta to declare improving/declining
FORM_SCORE_CHANGE_THRESHOLD_PTS: float = 3.0   # +/- 3.0 score points to declare improving/declining
RECURRING_ISSUE_MIN_FREQUENCY: float = 0.50   # Appears in >= 50% of analyzed sessions
MIN_OBSERVATIONS_FOR_TREND: int = 2            # Minimum observations needed for any directional trend
CONFIRMED_TREND_OBSERVATIONS: int = 3          # Threshold for stable_signal


class PersonalizationSignalService:
    """
    Core domain analytics service computing deterministic personalization signals.
    User-scoped: all data access is partitioned by verified Firebase UID.
    """

    def __init__(
        self,
        workout_repo: Optional[WorkoutRepository] = None,
        exercise_repo: Optional[ExerciseRepository] = None,
        user_repo: Optional[UserRepository] = None,
        form_repo: Optional[FormAnalysisRepository] = None,
        progress_service: Optional[ProgressService] = None,
    ):
        self._workout_repo = workout_repo
        self._exercise_repo = exercise_repo
        self._user_repo = user_repo
        self._form_repo = form_repo
        self._progress_service = progress_service

    @property
    def workout_repo(self) -> WorkoutRepository:
        return self._workout_repo or get_workout_repository()

    @property
    def exercise_repo(self) -> ExerciseRepository:
        return self._exercise_repo or get_exercise_repository()

    @property
    def user_repo(self) -> UserRepository:
        return self._user_repo or get_user_repository()

    @property
    def form_repo(self) -> FormAnalysisRepository:
        return self._form_repo or get_form_analysis_repository()

    @property
    def progress_service(self) -> ProgressService:
        if self._progress_service:
            return self._progress_service
        return ProgressService(
            workout_repo=self.workout_repo,
            exercise_repo=self.exercise_repo,
            user_repo=self.user_repo,
        )

    # =========================================================================
    # CORE SIGNAL COMPUTATION
    # =========================================================================

    def get_personalization_signals(
        self,
        uid: str,
        window_days: int = 28,
    ) -> PersonalizationSignalsResponse:
        """
        Assembles all deterministic personalization signals for the authenticated user.
        Bounded observation window applies to frequency and adherence calculations.
        """
        # 1. Retrieve all completed sessions (bounded up to 100 recent sessions)
        all_completed = self.workout_repo.list_user_history(uid, limit=100)
        
        # Sort chronologically ascending (oldest to newest)
        chronological_sessions = sorted(
            all_completed,
            key=lambda s: parse_session_datetime(s.startedAt) or datetime.min.replace(tzinfo=timezone.utc),
        )

        # 2. Compute Set Adherence Signal
        set_adherence = self._compute_set_adherence(chronological_sessions)

        # 3. Compute Workout Adherence Trend
        adherence_trend = self._compute_workout_adherence_trend(uid, chronological_sessions, window_days)

        # 4. Compute Exercise Performance Summaries
        exercise_summaries = self._compute_all_exercise_summaries(chronological_sessions)

        # 5. Compute Form Analysis Signals for Canonical CV Exercises
        form_signals = self._compute_form_signals(uid)

        now_iso = datetime.now(timezone.utc).isoformat()

        return PersonalizationSignalsResponse(
            userId=uid,
            generatedAt=now_iso,
            windowDays=window_days,
            overallAdherence=set_adherence,
            workoutAdherenceTrend=adherence_trend,
            exercises=exercise_summaries,
            formSignals=form_signals,
            summaryMetrics={
                "totalCompletedWorkouts": len(chronological_sessions),
                "trackedExercisesCount": len(exercise_summaries),
                "cvExercisesTracked": len(form_signals),
            },
        )

    def get_exercise_performance_signal(
        self,
        uid: str,
        exercise_id: str,
    ) -> Optional[ExercisePerformanceSummary]:
        """Retrieves performance signals for a single exercise, or None if no data recorded."""
        all_completed = self.workout_repo.list_user_history(uid, limit=100)
        chronological_sessions = sorted(
            all_completed,
            key=lambda s: parse_session_datetime(s.startedAt) or datetime.min.replace(tzinfo=timezone.utc),
        )
        return self._compute_single_exercise_summary(exercise_id, chronological_sessions)

    # =========================================================================
    # INTERNAL ANALYTICS ENGINES
    # =========================================================================

    def _compute_set_adherence(
        self,
        sessions: List[WorkoutSessionResponse],
    ) -> SetAdherenceSignal:
        """
        Computes completed sets vs planned sets at both session and exercise granularity.
        Enforces outlier safeguard: requires >= 2 sessions for an adherence tier.
        """
        if not sessions:
            return SetAdherenceSignal(
                tier="insufficient_data",
                evidenceLevel="no_data",
                totalSessionsEvaluated=0,
                totalCompletedSets=0,
                totalPlannedSets=0,
                overallCompletionRate=0.0,
                adherenceByExercise={},
            )

        if len(sessions) < MIN_OBSERVATIONS_FOR_TREND:
            sess = sessions[0]
            completed = sess.completedSetsCount or sum(len(sl) for sl in sess.completedSets.values())
            planned = sess.totalSetsCount or completed
            rate = round(min(1.0, completed / planned), 3) if planned > 0 else 1.0
            return SetAdherenceSignal(
                tier="insufficient_data",
                evidenceLevel="insufficient_data",
                totalSessionsEvaluated=1,
                totalCompletedSets=completed,
                totalPlannedSets=planned,
                overallCompletionRate=rate,
                adherenceByExercise={},
            )

        total_completed = 0
        total_planned = 0
        ex_completed_map: Dict[str, int] = {}
        ex_planned_map: Dict[str, int] = {}

        for s in sessions:
            s_completed = s.completedSetsCount or sum(len(sl) for sl in s.completedSets.values())
            s_planned = s.totalSetsCount or s_completed
            total_completed += s_completed
            total_planned += s_planned

            for ex_id, set_list in s.completedSets.items():
                ex_completed_map[ex_id] = ex_completed_map.get(ex_id, 0) + len(set_list)
                # If set items have target set numbers, estimate planned sets per exercise
                max_set_num = max([st.setNumber for st in set_list], default=len(set_list))
                ex_planned_map[ex_id] = ex_planned_map.get(ex_id, 0) + max_set_num

        overall_rate = round(min(1.0, total_completed / total_planned), 3) if total_planned > 0 else 1.0

        adherence_by_ex: Dict[str, float] = {}
        for ex_id, c_count in ex_completed_map.items():
            p_count = ex_planned_map.get(ex_id, c_count)
            adherence_by_ex[ex_id] = round(min(1.0, c_count / p_count), 3) if p_count > 0 else 1.0

        # Tier classification
        if overall_rate >= 0.85:
            tier: AdherenceTier = "high_adherence"
        elif overall_rate >= 0.65:
            tier: AdherenceTier = "moderate_adherence"
        else:
            tier: AdherenceTier = "low_adherence"

        evidence: EvidenceLevel = "stable_signal" if len(sessions) >= CONFIRMED_TREND_OBSERVATIONS else "emerging_signal"

        return SetAdherenceSignal(
            tier=tier,
            evidenceLevel=evidence,
            totalSessionsEvaluated=len(sessions),
            totalCompletedSets=total_completed,
            totalPlannedSets=total_planned,
            overallCompletionRate=overall_rate,
            adherenceByExercise=adherence_by_ex,
        )

    def _compute_workout_adherence_trend(
        self,
        uid: str,
        sessions: List[WorkoutSessionResponse],
        window_days: int,
    ) -> WorkoutAdherenceTrend:
        """
        Analyzes workout frequency and spacing over a bounded observation window.
        Does NOT fabricate an expected frequency if user profile does not configure one.
        """
        now = datetime.now(timezone.utc)
        cutoff = now - timedelta(days=window_days)

        window_sessions = [
            s for s in sessions
            if parse_session_datetime(s.startedAt) and parse_session_datetime(s.startedAt) >= cutoff
        ]
        session_count = len(window_sessions)

        # Retrieve user profile for optional expected workout frequency
        user = self.user_repo.get_by_uid(uid)
        expected_freq_per_week = float(user.workoutFrequencyDaysPerWeek) if (user and user.workoutFrequencyDaysPerWeek) else None

        weeks_in_window = window_days / 7.0
        observed_freq = round(session_count / weeks_in_window, 2)

        expected_sessions: Optional[int] = None
        adherence_rate: Optional[float] = None
        if expected_freq_per_week is not None and expected_freq_per_week > 0:
            expected_sessions = round(expected_freq_per_week * weeks_in_window)
            if expected_sessions > 0:
                adherence_rate = round(min(2.0, session_count / expected_sessions), 2)

        # Gap analysis
        sorted_dates = []
        for s in window_sessions:
            dt = parse_session_datetime(s.startedAt)
            if dt:
                sorted_dates.append(dt.date())
        sorted_dates = sorted(list(set(sorted_dates)))

        if len(sorted_dates) >= 2:
            gaps = [(sorted_dates[i + 1] - sorted_dates[i]).days for i in range(len(sorted_dates) - 1)]
            avg_gap = round(sum(gaps) / len(gaps), 1)
            max_gap = max(gaps)
        elif len(sorted_dates) == 1:
            avg_gap = 0.0
            max_gap = (now.date() - sorted_dates[0]).days
        else:
            avg_gap = 0.0
            max_gap = 0

        # Consistency status determination
        if session_count < MIN_OBSERVATIONS_FOR_TREND:
            consistency: ConsistencyStatus = "insufficient_data"
            evidence: EvidenceLevel = "no_data" if session_count == 0 else "insufficient_data"
        else:
            evidence: EvidenceLevel = "stable_signal" if session_count >= CONFIRMED_TREND_OBSERVATIONS else "emerging_signal"
            if max_gap > 7:
                consistency = "irregular"
            elif observed_freq < 1.5:
                consistency = "infrequent"
            else:
                consistency = "consistent"

        return WorkoutAdherenceTrend(
            observationWindowDays=window_days,
            sessionsCompleted=session_count,
            expectedSessions=expected_sessions,
            adherenceRate=adherence_rate,
            observedFrequencyPerWeek=observed_freq,
            expectedFrequencyPerWeek=expected_freq_per_week,
            avgDaysBetweenWorkouts=avg_gap,
            maxGapDays=max_gap,
            consistencyStatus=consistency,
            evidenceLevel=evidence,
        )

    def _compute_all_exercise_summaries(
        self,
        sessions: List[WorkoutSessionResponse],
    ) -> Dict[str, ExercisePerformanceSummary]:
        """Iterates all exercises present in completed session history and computes summaries."""
        # Find distinct exercise IDs
        distinct_ex_ids = set()
        for s in sessions:
            for ex_id in s.completedSets.keys():
                distinct_ex_ids.add(ex_id)

        summaries: Dict[str, ExercisePerformanceSummary] = {}
        for ex_id in sorted(list(distinct_ex_ids)):
            summary = self._compute_single_exercise_summary(ex_id, sessions)
            if summary:
                summaries[ex_id] = summary

        return summaries

    def _compute_single_exercise_summary(
        self,
        exercise_id: str,
        sessions: List[WorkoutSessionResponse],
    ) -> Optional[ExercisePerformanceSummary]:
        """
        Computes detailed performance analytics for an exercise across chronological sessions.
        Reuses authoritative 1RM and PR calculations matching ProgressService.
        """
        exercise_meta = self.exercise_repo.get_by_id(exercise_id)
        ex_name = exercise_meta.name if exercise_meta else exercise_id.replace("ex_", "").replace("_", " ").title()

        # Extract chronological exposures
        sessions_with_ex: List[Tuple[WorkoutSessionResponse, List[WorkoutSetSchema]]] = []
        for s in sessions:
            sets = s.completedSets.get(exercise_id, [])
            if sets:
                sessions_with_ex.append((s, sets))

        if not sessions_with_ex:
            return None

        total_sets = 0
        total_reps = 0
        total_volume = 0.0
        all_weights: List[float] = []
        all_reps: List[int] = []

        best_weight = 0.0
        best_1rm = 0.0
        pr_weight = 0.0
        pr_reps = 0
        pr_date: Optional[str] = None
        last_date: Optional[str] = None

        session_avg_weights: List[float] = []
        session_max_1rms: List[float] = []

        sets_with_targets: List[WorkoutSetSchema] = []

        for s, set_list in sessions_with_ex:
            dt = parse_session_datetime(s.startedAt)
            date_str = dt.strftime("%b %d, %Y") if dt else "Session"
            last_date = date_str

            sess_weights: List[float] = []
            sess_1rms: List[float] = []

            for st in set_list:
                wt = st.actualWeightKg or st.targetWeightKg or 0.0
                reps = st.actualReps or st.targetReps or 0

                total_sets += 1
                total_reps += reps
                vol = wt * reps
                total_volume += vol

                if wt > 0:
                    sess_weights.append(wt)
                    all_weights.append(wt)

                if reps > 0:
                    all_reps.append(reps)

                if wt > 0 and reps > 0:
                    # Epley 1RM formula reused from ProgressService: round(wt * (1.0 + reps / 30.0), 1) if reps > 1 else wt
                    e1rm = round(wt * (1.0 + reps / 30.0), 1) if reps > 1 else wt
                    sess_1rms.append(e1rm)

                    if e1rm > best_1rm:
                        best_1rm = e1rm

                    if wt > pr_weight:
                        pr_weight = wt
                        pr_reps = reps
                        pr_date = date_str

                if wt > best_weight:
                    best_weight = wt

                if st.targetReps and st.targetReps > 0 and st.actualReps is not None:
                    sets_with_targets.append(st)

            if sess_weights:
                session_avg_weights.append(round(sum(sess_weights) / len(sess_weights), 1))
            if sess_1rms:
                session_max_1rms.append(max(sess_1rms))

        avg_reps_per_set = round(total_reps / total_sets, 1) if total_sets > 0 else 0.0
        avg_weight = round(sum(all_weights) / len(all_weights), 1) if all_weights else 0.0

        # Load Progression Signal
        load_signal = self._evaluate_load_progression(exercise_id, session_avg_weights)

        # Rep Performance Signal
        rep_signal = self._evaluate_rep_performance(exercise_id, sets_with_targets)

        # Performance Trajectory (1RM Trajectory)
        perf_trajectory = self._evaluate_performance_trajectory(session_max_1rms)

        # Evidence level
        obs_count = len(sessions_with_ex)
        if obs_count == 0:
            evidence: EvidenceLevel = "no_data"
        elif obs_count == 1:
            evidence: EvidenceLevel = "insufficient_data"
        elif obs_count == 2:
            evidence: EvidenceLevel = "emerging_signal"
        else:
            evidence: EvidenceLevel = "stable_signal"

        return ExercisePerformanceSummary(
            exerciseId=exercise_id,
            exerciseName=ex_name,
            sessionsObserved=obs_count,
            totalSetsPerformed=total_sets,
            totalRepsPerformed=total_reps,
            totalVolumeKg=round(total_volume, 1),
            avgRepsPerSet=avg_reps_per_set,
            avgWeightKg=avg_weight,
            bestWeightKg=best_weight,
            bestEstimated1RM=best_1rm,
            prWeightKg=pr_weight,
            prReps=pr_reps,
            prDate=pr_date,
            loadProgression=load_signal,
            repPerformance=rep_signal,
            performanceTrajectory=perf_trajectory,
            evidenceLevel=evidence,
            lastPerformedDate=last_date,
        )

    def _evaluate_load_progression(
        self,
        exercise_id: str,
        session_avg_weights: List[float],
    ) -> LoadProgressionSignal:
        """
        Determines recent load progression trend.
        Requires >= 2 sessions with recorded loads.
        Threshold: +2.5% for increasing, -2.5% for decreasing.
        """
        n = len(session_avg_weights)
        if n < MIN_OBSERVATIONS_FOR_TREND:
            return LoadProgressionSignal(
                exerciseId=exercise_id,
                trend="insufficient_data",
                evidenceLevel="no_data" if n == 0 else "insufficient_data",
                sessionsObserved=n,
                recentAvgWeightKg=session_avg_weights[-1] if n == 1 else 0.0,
                baselineAvgWeightKg=session_avg_weights[0] if n == 1 else 0.0,
                percentageChange=0.0,
            )

        if n >= CONFIRMED_TREND_OBSERVATIONS:
            recent_weights = session_avg_weights[-2:]
            baseline_weights = session_avg_weights[:-2]
            evidence: EvidenceLevel = "stable_signal"
        else:
            # Exactly 2 sessions
            recent_weights = [session_avg_weights[-1]]
            baseline_weights = [session_avg_weights[0]]
            evidence: EvidenceLevel = "emerging_signal"

        recent_avg = round(sum(recent_weights) / len(recent_weights), 1)
        baseline_avg = round(sum(baseline_weights) / len(baseline_weights), 1)

        if baseline_avg > 0:
            pct_change = round(((recent_avg - baseline_avg) / baseline_avg) * 100.0, 2)
        else:
            pct_change = 100.0 if recent_avg > 0 else 0.0

        if pct_change >= LOAD_CHANGE_THRESHOLD_PCT:
            trend: TrendDirection = "increasing"
        elif pct_change <= -LOAD_CHANGE_THRESHOLD_PCT:
            trend: TrendDirection = "decreasing"
        else:
            trend: TrendDirection = "stable"

        return LoadProgressionSignal(
            exerciseId=exercise_id,
            trend=trend,
            evidenceLevel=evidence,
            sessionsObserved=n,
            recentAvgWeightKg=recent_avg,
            baselineAvgWeightKg=baseline_avg,
            percentageChange=pct_change,
        )

    def _evaluate_rep_performance(
        self,
        exercise_id: str,
        sets_with_targets: List[WorkoutSetSchema],
    ) -> RepPerformanceSignal:
        """
        Compares actual recorded repetitions against target rep parameters.
        Evaluates upper-bound completion rate and target range compliance.
        """
        n = len(sets_with_targets)
        if n < MIN_OBSERVATIONS_FOR_TREND:
            return RepPerformanceSignal(
                exerciseId=exercise_id,
                status="insufficient_data",
                evidenceLevel="no_data" if n == 0 else "insufficient_data",
                totalSetsWithTargets=n,
                avgActualReps=float(sets_with_targets[0].actualReps or 0) if n == 1 else 0.0,
                avgTargetReps=float(sets_with_targets[0].targetReps or 0) if n == 1 else 0.0,
                upperBoundCompletionCount=0,
                upperBoundCompletionRate=0.0,
                targetRangeCompletionCount=0,
                targetRangeCompletionRate=0.0,
                repCompletionRatio=0.0,
            )

        total_actual = sum(st.actualReps or 0 for st in sets_with_targets)
        total_target = sum(st.targetReps or 0 for st in sets_with_targets)

        avg_actual = round(total_actual / n, 1)
        avg_target = round(total_target / n, 1)

        # Upper bound: achieved target reps or exceeded
        upper_bound_count = sum(1 for st in sets_with_targets if (st.actualReps or 0) >= st.targetReps)
        upper_bound_rate = round(upper_bound_count / n, 3)

        # Target range: within 85% of target reps
        range_count = sum(1 for st in sets_with_targets if (st.actualReps or 0) >= round(st.targetReps * 0.85))
        range_rate = round(range_count / n, 3)

        completion_ratio = round(total_actual / total_target, 2) if total_target > 0 else 1.0

        if upper_bound_rate >= 0.75:
            status: RepPerformanceStatus = "above_target"
        elif range_rate >= 0.70:
            status: RepPerformanceStatus = "on_target"
        else:
            status: RepPerformanceStatus = "below_target"

        evidence: EvidenceLevel = "stable_signal" if n >= CONFIRMED_TREND_OBSERVATIONS else "emerging_signal"

        return RepPerformanceSignal(
            exerciseId=exercise_id,
            status=status,
            evidenceLevel=evidence,
            totalSetsWithTargets=n,
            avgActualReps=avg_actual,
            avgTargetReps=avg_target,
            upperBoundCompletionCount=upper_bound_count,
            upperBoundCompletionRate=upper_bound_rate,
            targetRangeCompletionCount=range_count,
            targetRangeCompletionRate=range_rate,
            repCompletionRatio=completion_ratio,
        )

    def _evaluate_performance_trajectory(
        self,
        session_max_1rms: List[float],
    ) -> PerformanceTrajectory:
        """
        Determines overall strength trajectory using chronological session 1RM estimates.
        Requires >= 2 sessions. Threshold: +/- 3.0%.
        """
        n = len(session_max_1rms)
        if n < MIN_OBSERVATIONS_FOR_TREND:
            return "insufficient_data"

        if n >= CONFIRMED_TREND_OBSERVATIONS:
            recent = statistics.median(session_max_1rms[-2:])
            baseline = statistics.median(session_max_1rms[:-2])
        else:
            recent = session_max_1rms[-1]
            baseline = session_max_1rms[0]

        if baseline <= 0:
            return "improving" if recent > 0 else "stable"

        pct_delta = ((recent - baseline) / baseline) * 100.0
        if pct_delta >= TRAJECTORY_CHANGE_THRESHOLD_PCT:
            return "improving"
        elif pct_delta <= -TRAJECTORY_CHANGE_THRESHOLD_PCT:
            return "declining"
        else:
            return "stable"

    def _compute_form_signals(
        self,
        uid: str,
    ) -> Dict[str, ExerciseFormSignal]:
        """
        Evaluates form analysis sessions for the 5 canonical Computer Vision exercises.
        Identifies recurrent heuristic issues and score trajectories without modifying workouts.
        """
        # Fetch up to 30 detailed form analysis sessions
        detailed_history = self.form_repo.list_user_detailed_history(uid, limit=30)

        signals: Dict[str, ExerciseFormSignal] = {}

        for cat_id, cv_name in CANONICAL_CV_EXERCISES.items():
            # Find matching sessions for this exercise
            matching = [
                s for s in detailed_history
                if s.exercise_id == cat_id
                or s.exercise_id == cv_name
                or s.canonical_exercise_id == cat_id
                or s.canonical_exercise_id == cv_name
            ]

            obs_count = len(matching)
            if obs_count == 0:
                signals[cat_id] = ExerciseFormSignal(
                    exerciseId=cat_id,
                    canonicalCvExercise=cv_name,
                    sessionsObserved=0,
                    totalRepsAnalyzed=0,
                    avgFormScore=None,
                    scoreTrend="insufficient_data",
                    latestIssue=None,
                    detectedIssues=[],
                    evidenceLevel="no_data",
                )
                continue

            total_reps = sum(s.completed_reps for s in matching)
            valid_scores = [s.overall_score for s in matching if s.overall_score is not None]
            avg_score = round(sum(valid_scores) / len(valid_scores), 1) if valid_scores else None

            # Score trend (newest vs oldest session score)
            if len(valid_scores) < MIN_OBSERVATIONS_FOR_TREND:
                score_trend: FormScoreTrend = "insufficient_data"
            else:
                recent_score = valid_scores[0]
                older_score = valid_scores[-1]
                delta = recent_score - older_score
                if delta >= FORM_SCORE_CHANGE_THRESHOLD_PTS:
                    score_trend = "improving"
                elif delta <= -FORM_SCORE_CHANGE_THRESHOLD_PTS:
                    score_trend = "declining"
                else:
                    score_trend = "stable"

            # Issue frequency mapping
            issue_session_counts: Dict[str, int] = {}
            for sess in matching:
                seen_in_sess = set()
                # Aggregate summary feedback
                for fb in sess.summary_feedback:
                    fb_clean = fb.strip()
                    if fb_clean and fb_clean not in seen_in_sess:
                        seen_in_sess.add(fb_clean)

                # Aggregate rep-level feedback
                for r in sess.reps:
                    for fb in r.feedback:
                        fb_clean = fb.strip()
                        if fb_clean and fb_clean not in seen_in_sess:
                            seen_in_sess.add(fb_clean)

                for issue in seen_in_sess:
                    issue_session_counts[issue] = issue_session_counts.get(issue, 0) + 1

            # Format issues list
            issue_items: List[FormIssueFrequency] = []
            for issue, count in issue_session_counts.items():
                freq_rate = round(count / obs_count, 2)
                is_recurring = (freq_rate >= RECURRING_ISSUE_MIN_FREQUENCY) and (obs_count >= MIN_OBSERVATIONS_FOR_TREND)
                issue_items.append(
                    FormIssueFrequency(
                        issue=issue,
                        occurrenceCount=count,
                        totalSessionsWithExercise=obs_count,
                        frequencyRate=freq_rate,
                        isRecurring=is_recurring,
                    )
                )

            # Sort issues: recurring first, then frequency descending
            issue_items.sort(key=lambda item: (item.isRecurring, item.occurrenceCount), reverse=True)

            latest_issue: Optional[str] = None
            if matching and matching[0].summary_feedback:
                latest_issue = matching[0].summary_feedback[0]

            if obs_count == 1:
                evidence: EvidenceLevel = "insufficient_data"
            elif obs_count == 2:
                evidence: EvidenceLevel = "emerging_signal"
            else:
                evidence: EvidenceLevel = "stable_signal"

            signals[cat_id] = ExerciseFormSignal(
                exerciseId=cat_id,
                canonicalCvExercise=cv_name,
                sessionsObserved=obs_count,
                totalRepsAnalyzed=total_reps,
                avgFormScore=avg_score,
                scoreTrend=score_trend,
                latestIssue=latest_issue,
                detectedIssues=issue_items,
                evidenceLevel=evidence,
            )

        return signals


# Global Singleton Provider
_personalization_signal_service_instance: Optional[PersonalizationSignalService] = None


def get_personalization_signal_service() -> PersonalizationSignalService:
    """FastAPI dependency provider for PersonalizationSignalService."""
    global _personalization_signal_service_instance
    if _personalization_signal_service_instance is None:
        _personalization_signal_service_instance = PersonalizationSignalService()
    return _personalization_signal_service_instance
