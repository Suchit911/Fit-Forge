from datetime import datetime, timezone, timedelta
from typing import Optional, List, Dict, Any, Tuple
from fastapi import Depends
from ..repositories.workout_repository import WorkoutRepository, get_workout_repository
from ..repositories.exercise_repository import ExerciseRepository, get_exercise_repository, EXERCISE_ID_ALIASES
from ..repositories.user_repository import UserRepository, get_user_repository
from ..schemas.exercise import ExerciseKnowledgeSchema
from ..utils.logger import logger
from ..schemas.progress import (
    ProgressPeriod,
    PeriodComparison,
    ProgressSummaryResponse,
    StrengthProgressPointSchema,
    ExerciseProgressionPoint,
    ExerciseProgressionResponse,
    ProgressKpiItemSchema,
    BodyCompositionStatsSchema,
    MuscleGroupProgressItemSchema,
    PerformanceTrendItemSchema,
    PersonalRecordItemSchema,
    RecentWorkoutItemSchema,
    ProgressPhotoItemSchema,
    ProgressDashboardResponse,
)
from ..schemas.workout import WorkoutSessionResponse


def parse_session_datetime(iso_str: str) -> Optional[datetime]:
    """Safely parses ISO timestamp into a timezone-aware UTC datetime."""
    if not iso_str:
        return None
    try:
        dt = datetime.fromisoformat(iso_str.replace("Z", "+00:00"))
        if dt.tzinfo is None:
            dt = dt.replace(tzinfo=timezone.utc)
        return dt.astimezone(timezone.utc)
    except Exception:
        return None


def calculate_period_boundaries(period: ProgressPeriod) -> Tuple[Optional[datetime], Optional[datetime], Optional[datetime]]:
    """
    Returns (start_cutoff, previous_start_cutoff, now).
    For '30d': start_cutoff = now - 30d, previous_start = now - 60d.
    """
    now = datetime.now(timezone.utc)
    if period == "7d":
        return now - timedelta(days=7), now - timedelta(days=14), now
    elif period == "30d":
        return now - timedelta(days=30), now - timedelta(days=60), now
    elif period == "90d":
        return now - timedelta(days=90), now - timedelta(days=180), now
    else:  # "all"
        return None, None, now


def format_pct_change(current_val: float, prev_val: float, period_label: str) -> str:
    """Computes deterministic percentage change string vs previous period."""
    if prev_val <= 0:
        return "+100% vs last " + period_label if current_val > 0 else "0% vs last " + period_label
    diff_pct = round(((current_val - prev_val) / prev_val) * 100)
    sign = "+" if diff_pct > 0 else ""
    return f"{sign}{diff_pct}% vs last {period_label}"


class ProgressService:
    """
    Domain service for computing deterministic progress analytics
    from completed workout sessions under users/{uid}/workout_sessions.
    """

    def __init__(
        self,
        workout_repo: Optional[WorkoutRepository] = None,
        exercise_repo: Optional[ExerciseRepository] = None,
        user_repo: Optional[UserRepository] = None,
    ):
        self._workout_repo = workout_repo
        self._exercise_repo = exercise_repo
        self._user_repo = user_repo

    @property
    def workout_repo(self) -> WorkoutRepository:
        return self._workout_repo or get_workout_repository()

    @property
    def exercise_repo(self) -> ExerciseRepository:
        return self._exercise_repo or get_exercise_repository()

    @property
    def user_repo(self) -> UserRepository:
        return self._user_repo or get_user_repository()

    def _get_completed_sessions(self, uid: str) -> List[WorkoutSessionResponse]:
        """Retrieves all completed sessions for user ordered by startedAt desc."""
        return self.workout_repo.list_user_history(uid, limit=500)

    def _get_exercise_metadata_map(self) -> Dict[str, ExerciseKnowledgeSchema]:
        """
        Builds a lookup map of canonical exercises indexed by both canonical ID
        and recognized aliases from EXERCISE_ID_ALIASES.
        """
        exercises = self.exercise_repo.list_exercises()
        meta_map: Dict[str, ExerciseKnowledgeSchema] = {e.id: e for e in exercises}
        for alias, target_id in EXERCISE_ID_ALIASES.items():
            if target_id in meta_map and alias not in meta_map:
                meta_map[alias] = meta_map[target_id]
        return meta_map

    def _resolve_exercise_metadata(
        self,
        ex_id: str,
        meta_map: Dict[str, ExerciseKnowledgeSchema],
    ) -> Optional[ExerciseKnowledgeSchema]:
        """
        Resolves exercise metadata from the cached map or repository by ID or alias.
        Returns None if unrecognized.
        """
        if ex_id in meta_map:
            return meta_map[ex_id]
        meta = self.exercise_repo.get_by_id(ex_id)
        if meta:
            meta_map[ex_id] = meta
            return meta
        return None

    def calculate_detailed_muscle_volume(
        self, sessions: List[WorkoutSessionResponse]
    ) -> Dict[str, float]:
        """
        Computes total volume attributed to each specific target muscle
        (e.g., 'hamstrings', 'glutes', 'quadriceps', 'chest', etc.)
        from completed workout sessions without mutating session records.
        """
        meta_map = self._get_exercise_metadata_map()
        muscle_volumes: Dict[str, float] = {}

        for s in sessions:
            for ex_id, set_list in s.completedSets.items():
                ex_meta = self._resolve_exercise_metadata(ex_id, meta_map)
                if not ex_meta:
                    logger.warning(
                        "Detailed muscle volume encountered unknown exercise ID '%s' in session '%s'; omitting.",
                        ex_id,
                        s.id,
                    )
                    continue

                ex_vol = sum((st.actualReps or 0) * (st.actualWeightKg or 0.0) for st in set_list)
                for m in (ex_meta.primaryMuscles or []):
                    m_key = m.lower()
                    muscle_volumes[m_key] = round(muscle_volumes.get(m_key, 0.0) + ex_vol, 2)

        return muscle_volumes

    def calculate_streak(self, sessions: List[WorkoutSessionResponse]) -> int:
        """
        Calculates consecutive active workout days leading up to today/yesterday.
        Returns 0 if streak is broken or no completed sessions exist.
        """
        if not sessions:
            return 0

        workout_dates = set()
        for s in sessions:
            dt = parse_session_datetime(s.startedAt)
            if dt:
                workout_dates.add(dt.date())

        if not workout_dates:
            return 0

        sorted_dates = sorted(list(workout_dates), reverse=True)
        today = datetime.now(timezone.utc).date()
        yesterday = today - timedelta(days=1)

        # Streak is active only if most recent workout was today or yesterday
        most_recent = sorted_dates[0]
        if most_recent < yesterday:
            return 0

        streak = 1
        current_check = most_recent - timedelta(days=1)
        while current_check in workout_dates:
            streak += 1
            current_check -= timedelta(days=1)

        return streak

    def get_summary(self, uid: str, period: ProgressPeriod = "30d") -> ProgressSummaryResponse:
        """
        Returns high-level summary metrics (workouts, volume, duration, calories, streak, consistency).
        """
        all_completed = self._get_completed_sessions(uid)
        start_cutoff, prev_start_cutoff, now = calculate_period_boundaries(period)
        period_label = "30 days" if period == "30d" else ("7 days" if period == "7d" else ("90 days" if period == "90d" else "period"))

        # Filter for current period
        current_sessions: List[WorkoutSessionResponse] = []
        previous_sessions: List[WorkoutSessionResponse] = []

        for s in all_completed:
            dt = parse_session_datetime(s.startedAt)
            if not dt:
                continue
            if start_cutoff is None or dt >= start_cutoff:
                current_sessions.append(s)
            elif prev_start_cutoff and dt >= prev_start_cutoff:
                previous_sessions.append(s)

        total_workouts = len(current_sessions)
        total_vol = sum(s.totalVolumeKg for s in current_sessions)
        total_dur_sec = sum(s.durationSeconds for s in current_sessions)
        total_dur_min = round(total_dur_sec / 60)
        total_cals = sum(s.caloriesBurned for s in current_sessions)
        avg_dur_min = round(total_dur_min / total_workouts) if total_workouts > 0 else 0

        # Streak across all historical workouts
        streak_days = self.calculate_streak(all_completed)

        # Weekly consistency: unique workout days in last 7 days
        week_cutoff = now - timedelta(days=7)
        recent_days = {
            parse_session_datetime(s.startedAt).date()
            for s in all_completed
            if parse_session_datetime(s.startedAt) and parse_session_datetime(s.startedAt) >= week_cutoff
        }
        weekly_consistency = len(recent_days)

        # Previous period comparisons
        prev_workouts = len(previous_sessions)
        prev_vol = sum(s.totalVolumeKg for s in previous_sessions)
        prev_cals = sum(s.caloriesBurned for s in previous_sessions)
        prev_dur_min = round(sum(s.durationSeconds for s in previous_sessions) / 60)

        comparison = PeriodComparison(
            workoutsChangePct=format_pct_change(total_workouts, prev_workouts, period_label),
            volumeChangePct=format_pct_change(total_vol, prev_vol, period_label),
            caloriesChangePct=format_pct_change(total_cals, prev_cals, period_label),
            durationChangePct=format_pct_change(total_dur_min, prev_dur_min, period_label),
        )

        return ProgressSummaryResponse(
            totalWorkouts=total_workouts,
            totalVolumeKg=round(total_vol, 1),
            totalDurationMinutes=total_dur_min,
            totalCaloriesBurned=total_cals,
            avgWorkoutDurationMinutes=avg_dur_min,
            currentStreakDays=streak_days,
            weeklyConsistencyDays=weekly_consistency,
            comparison=comparison,
        )

    def get_volume_time_series(self, uid: str, period: ProgressPeriod = "30d") -> List[StrengthProgressPointSchema]:
        """
        Computes date-based volume progression (upper body, lower body, total volume)
        broken down from real completed sets.
        """
        all_completed = self._get_completed_sessions(uid)
        start_cutoff, _, _ = calculate_period_boundaries(period)

        # Filter by period
        sessions = [
            s for s in all_completed
            if parse_session_datetime(s.startedAt) and (start_cutoff is None or parse_session_datetime(s.startedAt) >= start_cutoff)
        ]
        # Sort chronologically for charting
        sessions.sort(key=lambda s: parse_session_datetime(s.startedAt) or datetime.min.replace(tzinfo=timezone.utc))

        meta_map = self._get_exercise_metadata_map()

        time_series: List[StrengthProgressPointSchema] = []
        for s in sessions:
            dt = parse_session_datetime(s.startedAt)
            date_str = dt.strftime("%b %d") if dt else "Session"

            upper_vol = 0.0
            lower_vol = 0.0

            for ex_id, set_list in s.completedSets.items():
                ex_meta = self._resolve_exercise_metadata(ex_id, meta_map)
                if not ex_meta:
                    logger.warning(
                        "Progress analytics encountered unknown exercise ID '%s' in session '%s'; omitting from volume breakdown.",
                        ex_id,
                        s.id,
                    )
                    continue

                primary = [m.lower() for m in (ex_meta.primaryMuscles or [])]
                secondary = [m.lower() for m in (ex_meta.secondaryMuscles or [])]
                ex_vol = sum((st.actualReps or 0) * (st.actualWeightKg or 0.0) for st in set_list)

                if any(m in primary for m in ["quadriceps", "hamstrings", "glutes", "calves", "legs"]):
                    lower_vol += ex_vol
                elif any(m in primary for m in ["chest", "back", "shoulders", "biceps", "triceps", "arms"]):
                    upper_vol += ex_vol
                elif any(m in secondary for m in ["quadriceps", "hamstrings", "glutes", "calves", "legs"]):
                    lower_vol += ex_vol
                elif any(m in secondary for m in ["chest", "back", "shoulders", "biceps", "triceps", "arms"]):
                    upper_vol += ex_vol
                elif any(m in primary for m in ["core", "abs"]) or any(m in secondary for m in ["core", "abs"]):
                    upper_vol += ex_vol
                else:
                    logger.warning(
                        "Exercise '%s' (%s) muscles could not be classified into upper/lower volume.",
                        ex_id,
                        ex_meta.name,
                    )

            time_series.append(
                StrengthProgressPointSchema(
                    date=date_str,
                    upperBodyKg=round(upper_vol, 1),
                    lowerBodyKg=round(lower_vol, 1),
                    totalVolumeKg=round(s.totalVolumeKg, 1),
                )
            )

        return time_series

    def get_exercise_progression(self, uid: str, exercise_id: str) -> ExerciseProgressionResponse:
        """
        Computes historical progression for a specific exercise using real completed sets.
        Calculates best PR weight, PR reps, PR date, and estimated 1RM (Epley formula).
        """
        all_completed = self._get_completed_sessions(uid)
        canonical_target_id = EXERCISE_ID_ALIASES.get(exercise_id, exercise_id)
        ex_meta = self.exercise_repo.get_by_id(canonical_target_id)
        if ex_meta:
            ex_name = ex_meta.name
            target_exercise_id = ex_meta.id
        else:
            logger.warning(
                "Exercise progression requested for unknown exercise ID '%s'; using safe fallback.",
                exercise_id,
            )
            ex_name = exercise_id
            target_exercise_id = exercise_id

        progression_points: List[ExerciseProgressionPoint] = []
        best_pr_weight = 0.0
        best_pr_reps = 0
        best_pr_date: Optional[str] = None
        best_1rm = 0.0
        sessions_with_exercise = 0

        # Sort chronologically
        sorted_sessions = sorted(
            all_completed,
            key=lambda s: parse_session_datetime(s.startedAt) or datetime.min.replace(tzinfo=timezone.utc)
        )

        for s in sorted_sessions:
            sets_for_ex = []
            for set_ex_id, st_list in s.completedSets.items():
                if EXERCISE_ID_ALIASES.get(set_ex_id, set_ex_id) == target_exercise_id:
                    sets_for_ex.extend(st_list)

            if not sets_for_ex:
                continue

            sessions_with_exercise += 1
            dt = parse_session_datetime(s.startedAt)
            date_str = dt.strftime("%b %d, %Y") if dt else "Session"

            # Find best set in this session
            for st in sets_for_ex:
                reps = st.actualReps or st.targetReps or 0
                wt = st.actualWeightKg or st.targetWeightKg or 0.0
                if wt <= 0 or reps <= 0:
                    continue

                # Epley 1RM formula: weight * (1 + reps/30)
                e1rm = round(wt * (1.0 + reps / 30.0), 1) if reps > 1 else wt
                vol = round(wt * reps, 1)

                progression_points.append(
                    ExerciseProgressionPoint(
                        date=date_str,
                        sessionId=s.id,
                        reps=reps,
                        weightKg=wt,
                        volumeKg=vol,
                        estimated1RM=e1rm,
                    )
                )

                if wt > best_pr_weight:
                    best_pr_weight = wt
                    best_pr_reps = reps
                    best_pr_date = date_str

                if e1rm > best_1rm:
                    best_1rm = e1rm

        return ExerciseProgressionResponse(
            exerciseId=target_exercise_id,
            exerciseName=ex_name,
            prWeightKg=best_pr_weight,
            prReps=best_pr_reps,
            prDate=best_pr_date,
            bestEstimated1RM=best_1rm,
            totalSessionsCompleted=sessions_with_exercise,
            history=progression_points,
        )

    def calculate_personal_records(self, sessions: List[WorkoutSessionResponse]) -> List[PersonalRecordItemSchema]:
        """
        Computes personal records across all exercises recorded in completed sessions.
        """
        meta_map = self._get_exercise_metadata_map()
        records_by_ex: Dict[str, Dict[str, Any]] = {}

        for s in sessions:
            dt = parse_session_datetime(s.startedAt)
            date_str = dt.strftime("%b %d, %Y") if dt else "Recent"

            for ex_id, set_list in s.completedSets.items():
                canonical_id = EXERCISE_ID_ALIASES.get(ex_id, ex_id)
                for st in set_list:
                    wt = st.actualWeightKg or st.targetWeightKg or 0.0
                    reps = st.actualReps or st.targetReps or 0
                    if wt <= 0 or reps <= 0:
                        continue

                    current_best = records_by_ex.get(canonical_id)
                    if not current_best or wt > current_best["weight"]:
                        prev_best = current_best["weight"] if current_best else 0.0
                        imp_str = f"+{round(wt - prev_best, 1)} kg" if prev_best > 0 else "Baseline"

                        records_by_ex[canonical_id] = {
                            "weight": wt,
                            "reps": reps,
                            "date": date_str,
                            "improvement": imp_str,
                        }

        pr_items: List[PersonalRecordItemSchema] = []
        idx = 1
        for ex_id, pr_data in records_by_ex.items():
            ex_meta = self._resolve_exercise_metadata(ex_id, meta_map)
            if ex_meta:
                name = ex_meta.name
                cat = ex_meta.primaryMuscles[0].title() if (ex_meta and ex_meta.primaryMuscles) else "General"
            else:
                logger.warning(
                    "Personal record calculation encountered unknown exercise ID '%s'; using safe fallback.",
                    ex_id,
                )
                name = ex_id
                cat = "General"

            pr_items.append(
                PersonalRecordItemSchema(
                    id=f"pr_{idx}",
                    exerciseName=f"{name} ({pr_data['reps']} reps)",
                    category=cat,
                    date=pr_data["date"],
                    value=f"{pr_data['weight']} kg",
                    improvement=pr_data["improvement"],
                )
            )
            idx += 1

        return pr_items

    def get_dashboard_data(self, uid: str, period: ProgressPeriod = "30d") -> ProgressDashboardResponse:
        """
        Assembles complete chart-ready data for ProgressPage.tsx matching ProgressDashboardData schema.
        """
        summary = self.get_summary(uid, period)
        time_series = self.get_volume_time_series(uid, period)
        all_completed = self._get_completed_sessions(uid)

        # 1. KPIs
        vol_sparkline = [p.totalVolumeKg for p in time_series[-6:]] if time_series else [0, 0, 0]
        cal_sparkline = [s.caloriesBurned for s in all_completed[-6:]] if all_completed else [0, 0, 0]
        dur_sparkline = [round(s.durationSeconds / 60) for s in all_completed[-6:]] if all_completed else [0, 0, 0]
        count_sparkline = [1 for _ in all_completed[-6:]] if all_completed else [0, 0, 0]

        comp = summary.comparison or PeriodComparison()
        kpis = [
            ProgressKpiItemSchema(
                id="k1",
                title="Workout Sessions",
                value=str(summary.totalWorkouts),
                changePct=comp.workoutsChangePct,
                trendData=count_sparkline,
                color="#10b981",
            ),
            ProgressKpiItemSchema(
                id="k2",
                title="Total Volume",
                value=f"{summary.totalVolumeKg:,.0f} kg",
                changePct=comp.volumeChangePct,
                trendData=vol_sparkline,
                color="#3b82f6",
            ),
            ProgressKpiItemSchema(
                id="k3",
                title="Calories Burned",
                value=f"{summary.totalCaloriesBurned:,} kcal",
                changePct=comp.caloriesChangePct,
                trendData=cal_sparkline,
                color="#f97316",
            ),
            ProgressKpiItemSchema(
                id="k4",
                title="Avg. Workout Time",
                value=f"{summary.avgWorkoutDurationMinutes} min",
                changePct=comp.durationChangePct,
                trendData=dur_sparkline,
                color="#a855f7",
            ),
            ProgressKpiItemSchema(
                id="k5",
                title="Consistency Streak",
                value=f"{summary.currentStreakDays} Days",
                changePct=f"{summary.weeklyConsistencyDays}/7 days this week",
                trendData=[summary.currentStreakDays],
                color="#10b981",
            ),
        ]

        # 2. Body Composition from User Profile
        user_prof = self.user_repo.get_by_uid(uid)
        weight = (user_prof.weightKg if user_prof and user_prof.weightKg is not None else 0.0)
        bmi = (user_prof.bmi if user_prof and user_prof.bmi is not None else 0.0)
        target_wt = (user_prof.targetWeightKg if user_prof and user_prof.targetWeightKg is not None else 0.0)

        body_comp = BodyCompositionStatsSchema(
            dateCompare=f"Current Profile: {datetime.now(timezone.utc).strftime('%b %d, %Y')}",
            weightKg=weight,
            weightChangeKg=0.0,
            bodyFatPct=0.0,
            bodyFatChangePct=0.0,
            muscleMassKg=round(weight * 0.45, 1) if weight > 0 else 0.0,
            muscleMassChangeKg=0.0,
            bmi=bmi,
            bmiChange=0.0,
            goalProgressPct=min(100.0, round((summary.totalWorkouts / 20.0) * 100, 1)),
            goalKgToGo=round(max(0.0, weight - target_wt), 1) if (weight > 0 and target_wt > 0) else 0.0,
        )

        # 3. Muscle Group Progress Volume breakdown
        muscle_vol_map: Dict[str, float] = {
            "Chest": 0.0,
            "Back": 0.0,
            "Legs": 0.0,
            "Shoulders": 0.0,
            "Arms": 0.0,
            "Core": 0.0,
        }
        meta_map = self._get_exercise_metadata_map()

        for s in all_completed:
            for ex_id, set_list in s.completedSets.items():
                ex_meta = self._resolve_exercise_metadata(ex_id, meta_map)
                if not ex_meta:
                    logger.warning(
                        "Progress dashboard encountered unknown exercise ID '%s' in session '%s'; omitting from muscle group breakdown.",
                        ex_id,
                        s.id,
                    )
                    continue

                primary = [m.lower() for m in (ex_meta.primaryMuscles or [])]
                secondary = [m.lower() for m in (ex_meta.secondaryMuscles or [])]
                vol = sum((st.actualReps or 0) * (st.actualWeightKg or 0.0) for st in set_list)

                # Attribute volume to primary muscle group first; fall back to secondary if primary is unassigned
                if "chest" in primary:
                    muscle_vol_map["Chest"] += vol
                elif "back" in primary:
                    muscle_vol_map["Back"] += vol
                elif any(m in primary for m in ["quadriceps", "hamstrings", "glutes", "calves", "legs"]):
                    muscle_vol_map["Legs"] += vol
                elif "shoulders" in primary:
                    muscle_vol_map["Shoulders"] += vol
                elif any(m in primary for m in ["biceps", "triceps"]):
                    muscle_vol_map["Arms"] += vol
                elif any(m in primary for m in ["abs", "core"]):
                    muscle_vol_map["Core"] += vol
                elif "chest" in secondary:
                    muscle_vol_map["Chest"] += vol
                elif "back" in secondary:
                    muscle_vol_map["Back"] += vol
                elif any(m in secondary for m in ["quadriceps", "hamstrings", "glutes", "calves", "legs"]):
                    muscle_vol_map["Legs"] += vol
                elif "shoulders" in secondary:
                    muscle_vol_map["Shoulders"] += vol
                elif any(m in secondary for m in ["biceps", "triceps"]):
                    muscle_vol_map["Arms"] += vol
                elif any(m in secondary for m in ["abs", "core"]):
                    muscle_vol_map["Core"] += vol
                else:
                    logger.warning(
                        "Exercise '%s' (%s) muscles could not be attributed to standard muscle groups.",
                        ex_id,
                        ex_meta.name,
                    )

        muscle_group_items = [
            MuscleGroupProgressItemSchema(
                name=m_name,
                changePct=f"{m_vol:,.0f} kg",
                status="Excellent" if m_vol > 1000 else ("Good" if m_vol > 0 else "Needs Work"),
            )
            for m_name, m_vol in muscle_vol_map.items()
        ]

        # 4. Performance Trends
        perf_trends = [
            PerformanceTrendItemSchema(
                name="STRENGTH",
                value=f"{summary.totalVolumeKg:,.0f} kg",
                status="Active" if summary.totalWorkouts > 0 else "Baseline",
                trendData=vol_sparkline,
                iconName="dumbbell",
            ),
            PerformanceTrendItemSchema(
                name="ENDURANCE",
                value=f"{summary.totalDurationMinutes} min",
                status="Active" if summary.totalWorkouts > 0 else "Baseline",
                trendData=dur_sparkline,
                iconName="running",
            ),
            PerformanceTrendItemSchema(
                name="VOLUME",
                value=f"{len(all_completed)} Sessions",
                status="Logged",
                trendData=count_sparkline,
                iconName="lightning",
            ),
            PerformanceTrendItemSchema(
                name="CONSISTENCY",
                value=f"{summary.weeklyConsistencyDays}/7 Days",
                status="Optimal" if summary.weeklyConsistencyDays >= 3 else "Building",
                trendData=[summary.weeklyConsistencyDays],
                iconName="target",
            ),
        ]

        # 5. Personal Records
        prs = self.calculate_personal_records(all_completed)

        # 6. Recent Workouts
        recent_workouts: List[RecentWorkoutItemSchema] = []
        for s in all_completed[:10]:
            dt = parse_session_datetime(s.startedAt)
            date_str = dt.strftime("%b %d, %Y") if dt else "Recent"
            score = round((s.completedSetsCount / s.totalSetsCount * 100)) if s.totalSetsCount > 0 else 90

            recent_workouts.append(
                RecentWorkoutItemSchema(
                    id=s.id,
                    title=s.workoutTitle,
                    date=date_str,
                    durationMin=round(s.durationSeconds / 60),
                    volumeKg=s.totalVolumeKg,
                    caloriesKcal=s.caloriesBurned,
                    scorePct=min(100, score),
                )
            )

        # 7. Progress Photos Placeholder/Profile
        photos = [
            ProgressPhotoItemSchema(id="p1", date="Recent", imageUrl="/assets/hero_trainer.jpg"),
        ]

        return ProgressDashboardResponse(
            kpis=kpis,
            strengthProgress=time_series,
            bodyComposition=body_comp,
            muscleGroupProgress=muscle_group_items,
            performanceTrends=perf_trends,
            personalRecords=prs,
            recentWorkouts=recent_workouts,
            progressPhotos=photos,
        )


def get_progress_service(
    workout_repo: WorkoutRepository = Depends(get_workout_repository),
    exercise_repo: ExerciseRepository = Depends(get_exercise_repository),
    user_repo: UserRepository = Depends(get_user_repository),
) -> ProgressService:
    """FastAPI dependency for ProgressService."""
    return ProgressService(
        workout_repo=workout_repo,
        exercise_repo=exercise_repo,
        user_repo=user_repo,
    )
