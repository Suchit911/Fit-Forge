"""
Stage 2 Focused Real-Data Analytics & Exercise Metadata Alignment Tests.

Verifies:
1. Progress analytics metadata resolution:
   - Romanian Deadlift (ex_romanian_deadlift) contributes to hamstring & glute volume.
   - Bulgarian Split Squat (ex_bulgarian_squat) contributes to quadriceps & glute volume.
   - Incline Dumbbell Press (ex_incline_db_press) contributes to chest volume.
   - Multi-exercise combined session calculations.
   - Unknown exercise IDs emit structured diagnostics and do not contaminate other muscle totals.
   - Recognized aliases resolve consistently.
   - Date-range filtering, user isolation, and empty-history contracts.

2. Workout & PR exercise-name resolution:
   - Canonical display names in PR records ("Barbell Romanian Deadlift", "Bulgarian Split Squat", "Incline Dumbbell Press").
   - Canonical display names in PR notifications.
   - Unknown IDs receive safe raw fallback without string-munging fabrication.
   - PR deduplication and persistence semantics.
"""

import logging
import pytest
from datetime import datetime, timezone, timedelta
from fastapi.testclient import TestClient

from backend.app.main import app
from backend.app.core.security import get_current_user, CurrentUser
from backend.app.repositories.exercise_repository import (
    ExerciseRepository,
    get_exercise_repository,
    EXERCISE_ID_ALIASES,
)
from backend.app.repositories.workout_repository import (
    WorkoutRepository,
    get_workout_repository,
)
from backend.app.repositories.user_repository import (
    UserRepository,
    get_user_repository,
)
from backend.app.repositories.notification_repository import (
    NotificationRepository,
    get_notification_repository,
)
from backend.app.repositories.achievement_repository import (
    AchievementRepository,
    get_achievement_repository,
)
from backend.app.services.progress_service import (
    ProgressService,
    get_progress_service,
)
from backend.app.services.workout_service import (
    WorkoutService,
    get_workout_service,
)
from backend.app.services.notification_service import (
    NotificationService,
    get_notification_service,
)
from backend.app.services.achievement_service import (
    AchievementService,
    get_achievement_service,
)
from backend.app.schemas.workout import (
    WorkoutSessionCreate,
    WorkoutSessionComplete,
    WorkoutSessionUpdate,
    WorkoutSetRecord,
)


@pytest.fixture
def real_ex_repo():
    """Provides authoritative ExerciseRepository backed by the real canonical 100-exercise catalog."""
    return ExerciseRepository(db=None)


@pytest.fixture
def mock_wkt_repo():
    """Provides isolated WorkoutRepository."""
    return WorkoutRepository(db=None)


@pytest.fixture
def mock_user_repo():
    """Provides isolated UserRepository."""
    return UserRepository(db=None)


@pytest.fixture
def mock_notif_repo():
    """Provides isolated NotificationRepository."""
    return NotificationRepository(db=None)


@pytest.fixture
def mock_ach_repo():
    """Provides isolated AchievementRepository."""
    repo = AchievementRepository(db=None)
    repo.ensure_seeded()
    return repo


@pytest.fixture
def progress_svc(mock_wkt_repo, real_ex_repo, mock_user_repo):
    return ProgressService(
        workout_repo=mock_wkt_repo,
        exercise_repo=real_ex_repo,
        user_repo=mock_user_repo,
    )


@pytest.fixture
def workout_svc(mock_wkt_repo, real_ex_repo, mock_notif_repo, mock_ach_repo):
    notif_svc = NotificationService(repo=mock_notif_repo)
    ach_svc = AchievementService(
        achievement_repo=mock_ach_repo,
        workout_repo=mock_wkt_repo,
        notification_service=notif_svc,
    )
    return WorkoutService(
        workout_repo=mock_wkt_repo,
        exercise_repo=real_ex_repo,
        notification_service=notif_svc,
        achievement_service=ach_svc,
    )


# =============================================================================
# 1. PROGRESS ANALYTICS: INDIVIDUAL EXERCISE VOLUME ATTRIBUTION
# =============================================================================

def test_romanian_deadlift_volume_attribution(
    mock_wkt_repo: WorkoutRepository,
    progress_svc: ProgressService,
):
    """1. Romanian Deadlift sets contribute to hamstring and glute volume (and Legs in dashboard)."""
    uid = "user_rdl_test"
    s = mock_wkt_repo.create_session(uid, WorkoutSessionCreate(workoutId="wkt_lower_strength"))

    # 3 sets of Romanian Deadlift: 10 reps @ 100kg = 1000kg each -> 3000kg total
    for set_num in range(1, 4):
        mock_wkt_repo.update_session(
            uid,
            s.id,
            WorkoutSessionUpdate(
                recordedSet=WorkoutSetRecord(
                    exerciseId="ex_romanian_deadlift",
                    setNumber=set_num,
                    actualReps=10,
                    actualWeightKg=100.0,
                )
            ),
        )
    mock_wkt_repo.complete_session(uid, s.id, WorkoutSessionComplete(durationSeconds=1800))

    # A. Granular muscle breakdown
    sessions = mock_wkt_repo.list_user_history(uid)
    muscle_vols = progress_svc.calculate_detailed_muscle_volume(sessions)
    assert muscle_vols.get("hamstrings") == 3000.0
    assert muscle_vols.get("glutes") == 3000.0
    assert "chest" not in muscle_vols

    # B. Dashboard muscle groups (both hamstrings and glutes map to Legs without double-counting)
    dash = progress_svc.get_dashboard_data(uid, "30d")
    legs_item = next(m for m in dash.muscleGroupProgress if m.name == "Legs")
    assert legs_item.changePct == "3,000 kg"
    chest_item = next(m for m in dash.muscleGroupProgress if m.name == "Chest")
    assert chest_item.changePct == "0 kg"

    # C. Time series upper/lower breakdown
    time_series = progress_svc.get_volume_time_series(uid, "30d")
    assert len(time_series) == 1
    assert time_series[0].lowerBodyKg == 3000.0
    assert time_series[0].upperBodyKg == 0.0
    assert time_series[0].totalVolumeKg == 3000.0


def test_bulgarian_split_squat_volume_attribution(
    mock_wkt_repo: WorkoutRepository,
    progress_svc: ProgressService,
):
    """2. Bulgarian Split Squat sets contribute to quadriceps and glute volume (and Legs in dashboard)."""
    uid = "user_bss_test"
    s = mock_wkt_repo.create_session(uid, WorkoutSessionCreate(workoutId="wkt_lower_strength"))

    # 3 sets of Bulgarian Split Squat: 10 reps @ 40kg = 400kg each -> 1200kg total
    for set_num in range(1, 4):
        mock_wkt_repo.update_session(
            uid,
            s.id,
            WorkoutSessionUpdate(
                recordedSet=WorkoutSetRecord(
                    exerciseId="ex_bulgarian_squat",
                    setNumber=set_num,
                    actualReps=10,
                    actualWeightKg=40.0,
                )
            ),
        )
    mock_wkt_repo.complete_session(uid, s.id, WorkoutSessionComplete(durationSeconds=1500))

    # A. Granular muscle breakdown
    sessions = mock_wkt_repo.list_user_history(uid)
    muscle_vols = progress_svc.calculate_detailed_muscle_volume(sessions)
    assert muscle_vols.get("quadriceps") == 1200.0
    assert muscle_vols.get("glutes") == 1200.0
    assert "chest" not in muscle_vols

    # B. Dashboard muscle groups
    dash = progress_svc.get_dashboard_data(uid, "30d")
    legs_item = next(m for m in dash.muscleGroupProgress if m.name == "Legs")
    assert legs_item.changePct == "1,200 kg"

    # C. Time series upper/lower breakdown
    time_series = progress_svc.get_volume_time_series(uid, "30d")
    assert len(time_series) == 1
    assert time_series[0].lowerBodyKg == 1200.0
    assert time_series[0].upperBodyKg == 0.0
    assert time_series[0].totalVolumeKg == 1200.0


def test_incline_dumbbell_press_volume_attribution(
    mock_wkt_repo: WorkoutRepository,
    progress_svc: ProgressService,
):
    """3. Incline Dumbbell Press sets contribute to chest volume (and Chest/Upper Body)."""
    uid = "user_incline_test"
    s = mock_wkt_repo.create_session(uid, WorkoutSessionCreate(workoutId="wkt_upper_push"))

    # 3 sets of Incline Dumbbell Press: 10 reps @ 60kg = 600kg each -> 1800kg total
    for set_num in range(1, 4):
        mock_wkt_repo.update_session(
            uid,
            s.id,
            WorkoutSessionUpdate(
                recordedSet=WorkoutSetRecord(
                    exerciseId="ex_incline_db_press",
                    setNumber=set_num,
                    actualReps=10,
                    actualWeightKg=60.0,
                )
            ),
        )
    mock_wkt_repo.complete_session(uid, s.id, WorkoutSessionComplete(durationSeconds=1600))

    # A. Granular muscle breakdown
    sessions = mock_wkt_repo.list_user_history(uid)
    muscle_vols = progress_svc.calculate_detailed_muscle_volume(sessions)
    assert muscle_vols.get("chest") == 1800.0
    assert "quadriceps" not in muscle_vols
    assert "glutes" not in muscle_vols

    # B. Dashboard muscle groups
    dash = progress_svc.get_dashboard_data(uid, "30d")
    chest_item = next(m for m in dash.muscleGroupProgress if m.name == "Chest")
    assert chest_item.changePct == "1,800 kg"
    legs_item = next(m for m in dash.muscleGroupProgress if m.name == "Legs")
    assert legs_item.changePct == "0 kg"

    # C. Time series upper/lower breakdown
    time_series = progress_svc.get_volume_time_series(uid, "30d")
    assert len(time_series) == 1
    assert time_series[0].upperBodyKg == 1800.0
    assert time_series[0].lowerBodyKg == 0.0
    assert time_series[0].totalVolumeKg == 1800.0


# =============================================================================
# 2. COMBINED SESSION MULTI-EXERCISE CALCULATION
# =============================================================================

def test_combined_session_volume_calculation(
    mock_wkt_repo: WorkoutRepository,
    progress_svc: ProgressService,
):
    """4. Calculation remains correct when RDL, BSS, and Incline DB Press appear together in one session."""
    uid = "user_combined_session"
    s = mock_wkt_repo.create_session(uid, WorkoutSessionCreate(workoutId="wkt_full_body"))

    # Romanian Deadlift: 2 sets @ 1000kg = 2000kg
    for set_num in range(1, 3):
        mock_wkt_repo.update_session(
            uid,
            s.id,
            WorkoutSessionUpdate(
                recordedSet=WorkoutSetRecord(
                    exerciseId="ex_romanian_deadlift",
                    setNumber=set_num,
                    actualReps=10,
                    actualWeightKg=100.0,
                )
            ),
        )

    # Bulgarian Split Squat: 2 sets @ 400kg = 800kg
    for set_num in range(1, 3):
        mock_wkt_repo.update_session(
            uid,
            s.id,
            WorkoutSessionUpdate(
                recordedSet=WorkoutSetRecord(
                    exerciseId="ex_bulgarian_squat",
                    setNumber=set_num,
                    actualReps=10,
                    actualWeightKg=40.0,
                )
            ),
        )

    # Incline DB Press: 2 sets @ 500kg = 1000kg
    for set_num in range(1, 3):
        mock_wkt_repo.update_session(
            uid,
            s.id,
            WorkoutSessionUpdate(
                recordedSet=WorkoutSetRecord(
                    exerciseId="ex_incline_db_press",
                    setNumber=set_num,
                    actualReps=10,
                    actualWeightKg=50.0,
                )
            ),
        )

    mock_wkt_repo.complete_session(uid, s.id, WorkoutSessionComplete(durationSeconds=3600))

    # A. Detailed muscle breakdown
    sessions = mock_wkt_repo.list_user_history(uid)
    muscle_vols = progress_svc.calculate_detailed_muscle_volume(sessions)
    assert muscle_vols["hamstrings"] == 2000.0
    assert muscle_vols["quadriceps"] == 800.0
    assert muscle_vols["glutes"] == 2000.0 + 800.0  # 2800.0 (both RDL and BSS target glutes)
    assert muscle_vols["chest"] == 1000.0

    # B. Dashboard muscle groups: Legs = 2000 (RDL) + 800 (BSS) = 2800 kg; Chest = 1000 kg
    dash = progress_svc.get_dashboard_data(uid, "30d")
    legs_item = next(m for m in dash.muscleGroupProgress if m.name == "Legs")
    assert legs_item.changePct == "2,800 kg"
    chest_item = next(m for m in dash.muscleGroupProgress if m.name == "Chest")
    assert chest_item.changePct == "1,000 kg"

    # C. Time series
    ts = progress_svc.get_volume_time_series(uid, "30d")
    assert len(ts) == 1
    assert ts[0].lowerBodyKg == 2800.0  # 2000 + 800
    assert ts[0].upperBodyKg == 1000.0  # 1000
    assert ts[0].totalVolumeKg == 3800.0  # 2000 + 800 + 1000


# =============================================================================
# 3. UNKNOWN EXERCISE IDS & LOGGING DIAGNOSTICS
# =============================================================================

def test_unknown_exercise_id_diagnostic_and_non_contamination(
    mock_wkt_repo: WorkoutRepository,
    progress_svc: ProgressService,
    caplog: pytest.LogCaptureFixture,
):
    """5. Unknown exercise IDs produce a structured diagnostic log and do not contaminate muscle totals."""
    uid = "user_unknown_ex_test"
    s = mock_wkt_repo.create_session(uid, WorkoutSessionCreate(workoutId="wkt_test"))

    # Valid set: Incline DB Press 500kg
    mock_wkt_repo.update_session(
        uid,
        s.id,
        WorkoutSessionUpdate(
            recordedSet=WorkoutSetRecord(
                exerciseId="ex_incline_db_press",
                setNumber=1,
                actualReps=10,
                actualWeightKg=50.0,
            )
        ),
    )

    # Unknown exercise set: ex_nonexistent_lift_999 1500kg
    mock_wkt_repo.update_session(
        uid,
        s.id,
        WorkoutSessionUpdate(
            recordedSet=WorkoutSetRecord(
                exerciseId="ex_nonexistent_lift_999",
                setNumber=1,
                actualReps=10,
                actualWeightKg=150.0,
            )
        ),
    )

    mock_wkt_repo.complete_session(uid, s.id, WorkoutSessionComplete(durationSeconds=2000))

    with caplog.at_level(logging.WARNING):
        # A. Check time series
        ts = progress_svc.get_volume_time_series(uid, "30d")
        assert len(ts) == 1
        # Upper body contains strictly the 500kg from Incline DB Press
        assert ts[0].upperBodyKg == 500.0
        # Lower body is strictly 0.0
        assert ts[0].lowerBodyKg == 0.0
        # Total volume records the total completed volume (2000.0kg)
        assert ts[0].totalVolumeKg == 2000.0

        # B. Check dashboard muscle groups
        dash = progress_svc.get_dashboard_data(uid, "30d")
        chest_item = next(m for m in dash.muscleGroupProgress if m.name == "Chest")
        assert chest_item.changePct == "500 kg"
        legs_item = next(m for m in dash.muscleGroupProgress if m.name == "Legs")
        assert legs_item.changePct == "0 kg"

        # C. Detailed muscle volume
        sessions = mock_wkt_repo.list_user_history(uid)
        muscle_vols = progress_svc.calculate_detailed_muscle_volume(sessions)
        assert muscle_vols == {"chest": 500.0}

        # D. Verify warning log emitted for unknown exercise ID
        warning_records = [
            r for r in caplog.records
            if "ex_nonexistent_lift_999" in r.message and r.levelno == logging.WARNING
        ]
        assert len(warning_records) > 0


# =============================================================================
# 4. RECOGNIZED ALIAS RESOLUTION
# =============================================================================

def test_recognized_aliases_resolve_consistently(
    mock_wkt_repo: WorkoutRepository,
    progress_svc: ProgressService,
):
    """6. Recognized aliases (ex_bulgarian_split_squat, ex_incline_dumbbell_press, ex_rdl) resolve accurately."""
    uid = "user_aliases_test"
    s = mock_wkt_repo.create_session(uid, WorkoutSessionCreate(workoutId="wkt_test"))

    # Log sets using aliases
    # ex_bulgarian_split_squat -> ex_bulgarian_squat (quadriceps, glutes)
    mock_wkt_repo.update_session(
        uid,
        s.id,
        WorkoutSessionUpdate(
            recordedSet=WorkoutSetRecord(
                exerciseId="ex_bulgarian_split_squat",
                setNumber=1,
                actualReps=10,
                actualWeightKg=50.0,
            )
        ),
    )
    # ex_incline_dumbbell_press -> ex_incline_db_press (chest)
    mock_wkt_repo.update_session(
        uid,
        s.id,
        WorkoutSessionUpdate(
            recordedSet=WorkoutSetRecord(
                exerciseId="ex_incline_dumbbell_press",
                setNumber=1,
                actualReps=10,
                actualWeightKg=60.0,
            )
        ),
    )
    # ex_rdl -> ex_romanian_deadlift (hamstrings, glutes)
    mock_wkt_repo.update_session(
        uid,
        s.id,
        WorkoutSessionUpdate(
            recordedSet=WorkoutSetRecord(
                exerciseId="ex_rdl",
                setNumber=1,
                actualReps=10,
                actualWeightKg=100.0,
            )
        ),
    )
    mock_wkt_repo.complete_session(uid, s.id, WorkoutSessionComplete(durationSeconds=2400))

    # A. Volume time series
    ts = progress_svc.get_volume_time_series(uid, "30d")
    assert len(ts) == 1
    # Lower body: BSS (500kg) + RDL (1000kg) = 1500kg
    assert ts[0].lowerBodyKg == 1500.0
    # Upper body: Incline DB Press (600kg) = 600kg
    assert ts[0].upperBodyKg == 600.0

    # B. Dashboard muscle groups
    dash = progress_svc.get_dashboard_data(uid, "30d")
    legs_item = next(m for m in dash.muscleGroupProgress if m.name == "Legs")
    assert legs_item.changePct == "1,500 kg"
    chest_item = next(m for m in dash.muscleGroupProgress if m.name == "Chest")
    assert chest_item.changePct == "600 kg"

    # C. Exercise progression via alias returns canonical ID and name
    prog = progress_svc.get_exercise_progression(uid, "ex_bulgarian_split_squat")
    assert prog.exerciseId == "ex_bulgarian_squat"
    assert prog.exerciseName == "Bulgarian Split Squat"
    assert prog.prWeightKg == 50.0


# =============================================================================
# 5. WORKOUT & PR CANONICAL DISPLAY NAMES
# =============================================================================

def test_pr_canonical_display_names(
    mock_wkt_repo: WorkoutRepository,
    mock_notif_repo: NotificationRepository,
    workout_svc: WorkoutService,
    progress_svc: ProgressService,
):
    """PR records and notifications use canonical display names for RDL, BSS, and Incline DB Press."""
    uid = "user_pr_canonical_names"
    s = mock_wkt_repo.create_session(uid, WorkoutSessionCreate(workoutId="wkt_full_body"))

    # RDL: 120kg
    mock_wkt_repo.update_session(
        uid,
        s.id,
        WorkoutSessionUpdate(
            recordedSet=WorkoutSetRecord(
                exerciseId="ex_romanian_deadlift",
                setNumber=1,
                actualReps=5,
                actualWeightKg=120.0,
            )
        ),
    )
    # BSS: 45kg
    mock_wkt_repo.update_session(
        uid,
        s.id,
        WorkoutSessionUpdate(
            recordedSet=WorkoutSetRecord(
                exerciseId="ex_bulgarian_squat",
                setNumber=1,
                actualReps=8,
                actualWeightKg=45.0,
            )
        ),
    )
    # Incline DB Press: 36kg
    mock_wkt_repo.update_session(
        uid,
        s.id,
        WorkoutSessionUpdate(
            recordedSet=WorkoutSetRecord(
                exerciseId="ex_incline_db_press",
                setNumber=1,
                actualReps=6,
                actualWeightKg=36.0,
            )
        ),
    )

    workout_svc.complete_session(uid, s.id, WorkoutSessionComplete(durationSeconds=2400))

    # A. Notifications check: canonical exercise names
    notifs = mock_notif_repo.list_notifications(uid)
    pr_notifs = [n for n in notifs if n["type"] == "personal_record"]
    assert len(pr_notifs) == 3

    rdl_notif = next(n for n in pr_notifs if "ex_romanian_deadlift" in n["id"])
    assert "Barbell Romanian Deadlift" in rdl_notif["message"]

    bss_notif = next(n for n in pr_notifs if "ex_bulgarian_squat" in n["id"])
    assert "Bulgarian Split Squat" in bss_notif["message"]

    incline_notif = next(n for n in pr_notifs if "ex_incline_db_press" in n["id"])
    assert "Incline Dumbbell Press" in incline_notif["message"]

    # B. Dashboard PR items: canonical exercise names and category
    dash = progress_svc.get_dashboard_data(uid, "30d")
    prs = dash.personalRecords
    assert len(prs) == 3

    rdl_pr = next(p for p in prs if "Barbell Romanian Deadlift" in p.exerciseName)
    assert rdl_pr.category == "Hamstrings"
    assert "120" in rdl_pr.value

    bss_pr = next(p for p in prs if "Bulgarian Split Squat" in p.exerciseName)
    assert bss_pr.category == "Quadriceps"
    assert "45" in bss_pr.value

    incline_pr = next(p for p in prs if "Incline Dumbbell Press" in p.exerciseName)
    assert incline_pr.category == "Chest"
    assert "36" in incline_pr.value


# =============================================================================
# 6. UNKNOWN EXERCISE ID SAFE FALLBACK (NO FABRICATED TITLES)
# =============================================================================

def test_pr_unknown_exercise_id_safe_fallback(
    mock_wkt_repo: WorkoutRepository,
    mock_notif_repo: NotificationRepository,
    workout_svc: WorkoutService,
    progress_svc: ProgressService,
    caplog: pytest.LogCaptureFixture,
):
    """Unknown exercise IDs do not receive fabricated titles from string parsing."""
    uid = "user_unknown_pr_test"
    s = mock_wkt_repo.create_session(uid, WorkoutSessionCreate(workoutId="wkt_test"))

    unknown_id = "ex_strange_custom_movement_99"
    mock_wkt_repo.update_session(
        uid,
        s.id,
        WorkoutSessionUpdate(
            recordedSet=WorkoutSetRecord(
                exerciseId=unknown_id,
                setNumber=1,
                actualReps=5,
                actualWeightKg=75.0,
            )
        ),
    )

    with caplog.at_level(logging.WARNING):
        workout_svc.complete_session(uid, s.id, WorkoutSessionComplete(durationSeconds=1200))

        # Check notification: uses safe raw ID, NOT fabricated "Strange Custom Movement 99"
        notifs = mock_notif_repo.list_notifications(uid)
        pr_notifs = [n for n in notifs if n["type"] == "personal_record"]
        assert len(pr_notifs) == 1
        assert unknown_id in pr_notifs[0]["message"]
        assert "Strange Custom Movement 99" not in pr_notifs[0]["message"]

        # Check dashboard PRs: uses safe raw ID
        dash = progress_svc.get_dashboard_data(uid, "30d")
        assert len(dash.personalRecords) == 1
        assert unknown_id in dash.personalRecords[0].exerciseName
        assert "Strange Custom Movement 99" not in dash.personalRecords[0].exerciseName

        # Verify warning log was emitted
        warnings = [
            r for r in caplog.records
            if unknown_id in r.message and r.levelno == logging.WARNING
        ]
        assert len(warnings) > 0


# =============================================================================
# 7. PR DEDUPLICATION AND RE-TESTING SEMANTICS
# =============================================================================

def test_pr_deduplication_and_persistence(
    mock_wkt_repo: WorkoutRepository,
    mock_notif_repo: NotificationRepository,
    workout_svc: WorkoutService,
):
    """PR detection properly compares against user history and prevents duplicate PRs for lower/equal weights."""
    uid = "user_pr_dedup_test"

    # Session 1: Bench Press 80kg (PR established)
    s1 = mock_wkt_repo.create_session(uid, WorkoutSessionCreate(workoutId="wkt_upper_push"))
    mock_wkt_repo.update_session(
        uid,
        s1.id,
        WorkoutSessionUpdate(
            recordedSet=WorkoutSetRecord(
                exerciseId="ex_bench_press",
                setNumber=1,
                actualReps=5,
                actualWeightKg=80.0,
            )
        ),
    )
    comp1 = workout_svc.complete_session(uid, s1.id, WorkoutSessionComplete(durationSeconds=1800))
    assert comp1 is not None
    assert comp1.status == "completed"

    pr_notifs_1 = [n for n in mock_notif_repo.list_notifications(uid) if n["type"] == "personal_record"]
    assert len(pr_notifs_1) == 1
    assert "80" in pr_notifs_1[0]["message"]

    # Session 2: Bench Press 80kg (Equal weight -> NO new PR)
    s2 = mock_wkt_repo.create_session(uid, WorkoutSessionCreate(workoutId="wkt_upper_push"))
    mock_wkt_repo.update_session(
        uid,
        s2.id,
        WorkoutSessionUpdate(
            recordedSet=WorkoutSetRecord(
                exerciseId="ex_bench_press",
                setNumber=1,
                actualReps=5,
                actualWeightKg=80.0,
            )
        ),
    )
    comp2 = workout_svc.complete_session(uid, s2.id, WorkoutSessionComplete(durationSeconds=1800))
    assert comp2 is not None

    pr_notifs_2 = [n for n in mock_notif_repo.list_notifications(uid) if n["type"] == "personal_record"]
    assert len(pr_notifs_2) == 1  # Still 1, no duplicate PR notification

    # Session 3: Bench Press 90kg (New PR established)
    s3 = mock_wkt_repo.create_session(uid, WorkoutSessionCreate(workoutId="wkt_upper_push"))
    mock_wkt_repo.update_session(
        uid,
        s3.id,
        WorkoutSessionUpdate(
            recordedSet=WorkoutSetRecord(
                exerciseId="ex_bench_press",
                setNumber=1,
                actualReps=5,
                actualWeightKg=90.0,
            )
        ),
    )
    comp3 = workout_svc.complete_session(uid, s3.id, WorkoutSessionComplete(durationSeconds=1800))
    assert comp3 is not None

    pr_notifs_3 = [n for n in mock_notif_repo.list_notifications(uid) if n["type"] == "personal_record"]
    assert len(pr_notifs_3) == 2
    assert any("90" in n["message"] for n in pr_notifs_3)
