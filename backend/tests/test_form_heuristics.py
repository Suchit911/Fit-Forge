"""
Comprehensive Deterministic Unit Tests for Form Heuristics (Phase 9B.2).

Verifies all 30 minimum test requirements:
1. Valid squat technique observations.
2. Squat depth deviation.
3. Squat alignment deviation.
4. Squat bilateral symmetry.
5. Bench ROM.
6. Bench left/right asymmetry.
7. Bench stability.
8. Deadlift hip/knee sequencing.
9. Deadlift torso-angle deviation.
10. Deadlift symmetry.
11. Bicep curl ROM.
12. Bicep curl excessive upper-arm movement.
13. Shoulder press ROM.
14. Shoulder press symmetry.
15. Shoulder press stability.
16. Low-confidence observations (INSUFFICIENT_CONFIDENCE).
17. Missing landmarks (NOT_OBSERVABLE).
18. NOT_OBSERVABLE behavior (Missing data != bad form).
19. INVALID observation.
20. NaN / infinity protection.
21. Temporal noisy observations.
22. Single-frame noise must not immediately produce a definitive defect where a temporal window is required.
23. Determinism: identical inputs produce identical outputs.
24. Threshold boundary tests.
25. Just-inside threshold.
26. Just-outside threshold.
27. Cross-exercise configuration isolation.
28. Invalid exercise ID.
29. Insufficient observation history.
30. Observability ratio and 70% sufficiency rule for Phase 9B.3.
"""

import math
import pytest
from typing import Dict, List, Any

from backend.app.schemas.form_analysis import ObservabilityStatus, HeuristicCategory
from backend.app.services.form_heuristics import (
    FormHeuristicsService,
    FormHeuristicResult,
    ExerciseFormReport,
    ExerciseHeuristicConfig,
    STANDARD_HEURISTIC_CONFIGS,
)
from backend.app.services.exercise_fsm import KinematicObservation


@pytest.fixture
def service():
    return FormHeuristicsService()


# =============================================================================
# 1. VALID SQUAT OBSERVATION
# =============================================================================

def test_1_valid_squat_technique(service):
    """Clean squat observation with all metrics within acceptable limits."""
    history = [
        {"joint_angles": {"left_knee": 94.0, "right_knee": 94.0}, "confidence": 0.95, "timestamp_ms": 0.0},
        {"joint_angles": {"left_knee": 92.0, "right_knee": 92.0}, "confidence": 0.95, "timestamp_ms": 50.0},
        {"joint_angles": {"left_knee": 90.0, "right_knee": 90.0}, "confidence": 0.95, "timestamp_ms": 100.0},
    ]

    current = {
        "joint_angles": {
            "left_knee": 88.0,
            "right_knee": 89.0,
            "torso_angle": 35.0,
            "knee_tracking_ratio": 0.88,
        },
        "confidence": 0.95,
        "timestamp_ms": 300.0,
    }

    report = service.evaluate("ex_squat", current, history)
    assert report.is_sufficiently_observable is True
    assert report.observable_count == 5

    for res in report.results:
        assert res.status == ObservabilityStatus.OBSERVED
        assert res.is_acceptable is True
        assert res.deviation == 0.0


# =============================================================================
# 2. SQUAT DEPTH DEVIATION
# =============================================================================

def test_2_squat_depth_deviation(service):
    """Squat depth of 105° (above 95° parallel threshold) must flag deviation."""
    current = {
        "joint_angles": {"left_knee": 105.0, "right_knee": 106.0},
        "confidence": 0.90,
    }
    report = service.evaluate("ex_squat", current)
    depth_res = next(r for r in report.results if r.heuristic_name == "squat_depth")

    assert depth_res.status == ObservabilityStatus.OBSERVED
    assert depth_res.is_acceptable is False
    assert depth_res.observed_value == 105.0
    assert depth_res.deviation == 10.0
    assert "did not reach" in depth_res.feedback


# =============================================================================
# 3. SQUAT ALIGNMENT DEVIATION
# =============================================================================

def test_3_squat_alignment_deviation(service):
    """Excessive forward torso inclination (52° > 45°) and narrow knee tracking (0.65 < 0.75)."""
    current = {
        "joint_angles": {
            "left_knee": 88.0,
            "right_knee": 88.0,
            "torso_angle": 52.0,
            "knee_tracking_ratio": 0.65,
        },
        "confidence": 0.90,
    }
    report = service.evaluate("ex_squat", current)
    torso_res = next(r for r in report.results if r.heuristic_name == "squat_torso_inclination")
    tracking_res = next(r for r in report.results if r.heuristic_name == "squat_knee_tracking")

    assert torso_res.is_acceptable is False
    assert torso_res.deviation == 7.0
    assert "exceeded" in torso_res.feedback

    assert tracking_res.is_acceptable is False
    assert tracking_res.deviation == 0.10
    assert "deviation observed" in tracking_res.feedback


# =============================================================================
# 4. SQUAT BILATERAL SYMMETRY
# =============================================================================

def test_4_squat_bilateral_symmetry(service):
    """Left knee at 85°, right knee at 101° (diff 16° > 12° max)."""
    current = {
        "joint_angles": {"left_knee": 85.0, "right_knee": 101.0},
        "confidence": 0.92,
    }
    report = service.evaluate("ex_squat", current)
    symm_res = next(r for r in report.results if r.heuristic_name == "squat_knee_symmetry")

    assert symm_res.status == ObservabilityStatus.OBSERVED
    assert symm_res.is_acceptable is False
    assert symm_res.observed_value == 16.0
    assert symm_res.deviation == 4.0
    assert "asymmetry exceeded" in symm_res.feedback


# =============================================================================
# 5. BENCH ROM
# =============================================================================

def test_5_bench_rom(service):
    """Elbow angle <= 90° satisfies ROM; elbow angle > 90° flags deficit."""
    good_current = {"joint_angles": {"left_elbow": 82.0, "right_elbow": 84.0}, "confidence": 0.90}
    bad_current = {"joint_angles": {"left_elbow": 98.0, "right_elbow": 99.0}, "confidence": 0.90}

    good_res = next(r for r in service.evaluate("ex_bench_press", good_current).results if r.heuristic_name == "bench_elbow_rom")
    bad_res = next(r for r in service.evaluate("ex_bench_press", bad_current).results if r.heuristic_name == "bench_elbow_rom")

    assert good_res.is_acceptable is True
    assert bad_res.is_acceptable is False
    assert bad_res.deviation == 8.0


# =============================================================================
# 6. BENCH LEFT/RIGHT ASYMMETRY
# =============================================================================

def test_6_bench_left_right_asymmetry(service):
    """Bilateral elbow difference 15° (> 12° max) flags asymmetry."""
    current = {"joint_angles": {"left_elbow": 80.0, "right_elbow": 95.0}, "confidence": 0.90}
    res = next(r for r in service.evaluate("ex_bench_press", current).results if r.heuristic_name == "bench_elbow_symmetry")

    assert res.is_acceptable is False
    assert res.observed_value == 15.0
    assert res.deviation == 3.0


# =============================================================================
# 7. BENCH STABILITY
# =============================================================================

def test_7_bench_stability(service):
    """High frame-to-frame standard deviation (> 6.0°) flags instability."""
    history = [
        {"joint_angles": {"left_elbow": 80.0}},
        {"joint_angles": {"left_elbow": 95.0}},
        {"joint_angles": {"left_elbow": 78.0}},
    ]
    current = {"joint_angles": {"left_elbow": 96.0}}
    res = next(r for r in service.evaluate("ex_bench_press", current, history).results if r.heuristic_name == "bench_movement_stability")

    assert res.status == ObservabilityStatus.OBSERVED
    assert res.is_acceptable is False
    assert res.deviation > 0.0


# =============================================================================
# 8. DEADLIFT HIP/KNEE SEQUENCING
# =============================================================================

def test_8_deadlift_hip_knee_sequencing(service):
    """Hip extending 25° while knees extend only 2° flags early hip rise."""
    history = [
        {"joint_angles": {"left_hip": 80.0, "left_knee": 80.0}, "confidence": 0.90},
        {"joint_angles": {"left_hip": 90.0, "left_knee": 81.0}, "confidence": 0.90},
    ]
    current = {
        "joint_angles": {"left_hip": 105.0, "left_knee": 82.0},
        "confidence": 0.90,
    }
    report = service.evaluate("ex_deadlift", current, history)
    seq_res = next(r for r in report.results if r.heuristic_name == "deadlift_hip_knee_sequencing")

    assert seq_res.status == ObservabilityStatus.OBSERVED
    assert seq_res.is_acceptable is False
    assert "Early hip rise observed" in seq_res.feedback


# =============================================================================
# 9. DEADLIFT TORSO-ANGLE DEVIATION
# =============================================================================

def test_9_deadlift_torso_angle_deviation(service):
    """Setup torso angle 65° (> 55° max) flags deviation."""
    current = {"joint_angles": {"torso_angle": 65.0}, "confidence": 0.90}
    res = next(r for r in service.evaluate("ex_deadlift", current).results if r.heuristic_name == "deadlift_torso_angle")

    assert res.is_acceptable is False
    assert res.deviation == 10.0


# =============================================================================
# 10. DEADLIFT SYMMETRY
# =============================================================================

def test_10_deadlift_symmetry(service):
    """Bilateral hip difference 17° (> 12° max) flags asymmetry."""
    current = {"joint_angles": {"left_hip": 150.0, "right_hip": 167.0}, "confidence": 0.90}
    res = next(r for r in service.evaluate("ex_deadlift", current).results if r.heuristic_name == "deadlift_hip_symmetry")

    assert res.is_acceptable is False
    assert res.observed_value == 17.0
    assert res.deviation == 5.0


# =============================================================================
# 11. BICEP CURL ROM
# =============================================================================

def test_11_bicep_curl_rom(service):
    """Flexion <= 55° satisfies ROM; 68° flags deficit."""
    good_current = {"joint_angles": {"left_elbow": 50.0}, "confidence": 0.90}
    bad_current = {"joint_angles": {"left_elbow": 68.0}, "confidence": 0.90}

    good_res = next(r for r in service.evaluate("ex_bicep_curl", good_current).results if r.heuristic_name == "curl_elbow_rom")
    bad_res = next(r for r in service.evaluate("ex_bicep_curl", bad_current).results if r.heuristic_name == "curl_elbow_rom")

    assert good_res.is_acceptable is True
    assert bad_res.is_acceptable is False
    assert bad_res.deviation == 13.0


# =============================================================================
# 12. BICEP CURL EXCESSIVE UPPER-ARM MOVEMENT
# =============================================================================

def test_12_bicep_curl_excessive_upper_arm_movement(service):
    """Upper-arm anterior drift 0.12 (> 0.08 max) flags technique deviation."""
    current = {"joint_angles": {"upper_arm_drift": 0.12}, "confidence": 0.90}
    res = next(r for r in service.evaluate("ex_bicep_curl", current).results if r.heuristic_name == "curl_upper_arm_drift")

    assert res.is_acceptable is False
    assert res.deviation == 0.04
    assert "anterior drift exceeded" in res.feedback


# =============================================================================
# 13. SHOULDER PRESS ROM
# =============================================================================

def test_13_shoulder_press_rom(service):
    """Elbow angle >= 165° satisfies lockout; 152° flags deficit."""
    good_current = {"joint_angles": {"left_elbow": 168.0}, "confidence": 0.90}
    bad_current = {"joint_angles": {"left_elbow": 152.0}, "confidence": 0.90}

    good_res = next(r for r in service.evaluate("ex_shoulder_press", good_current).results if r.heuristic_name == "shoulder_press_lockout")
    bad_res = next(r for r in service.evaluate("ex_shoulder_press", bad_current).results if r.heuristic_name == "shoulder_press_lockout")

    assert good_res.is_acceptable is True
    assert bad_res.is_acceptable is False
    assert bad_res.deviation == 13.0


# =============================================================================
# 14. SHOULDER PRESS SYMMETRY
# =============================================================================

def test_14_shoulder_press_symmetry(service):
    """Left elbow 168°, right elbow 150° (diff 18° > 12° max) flags asymmetry."""
    current = {"joint_angles": {"left_elbow": 168.0, "right_elbow": 150.0}, "confidence": 0.90}
    res = next(r for r in service.evaluate("ex_shoulder_press", current).results if r.heuristic_name == "shoulder_press_elbow_symmetry")

    assert res.is_acceptable is False
    assert res.observed_value == 18.0
    assert res.deviation == 6.0


# =============================================================================
# 15. SHOULDER PRESS STABILITY
# =============================================================================

def test_15_shoulder_press_stability(service):
    """Stable overhead pressing trajectory satisfies stability."""
    history = [
        {"joint_angles": {"left_elbow": 160.0}},
        {"joint_angles": {"left_elbow": 163.0}},
        {"joint_angles": {"left_elbow": 165.0}},
    ]
    current = {"joint_angles": {"left_elbow": 167.0}}
    res = next(r for r in service.evaluate("ex_shoulder_press", current, history).results if r.heuristic_name == "shoulder_press_movement_stability")

    assert res.status == ObservabilityStatus.OBSERVED
    assert res.is_acceptable is True


# =============================================================================
# 16. LOW CONFIDENCE OBSERVATIONS
# =============================================================================

def test_16_low_confidence_observations(service):
    """Confidence 0.35 (< 0.50) must yield INSUFFICIENT_CONFIDENCE, NOT bad form."""
    current = {
        "joint_angles": {"left_knee": 88.0, "right_knee": 88.0, "torso_angle": 35.0},
        "confidence": 0.35,
    }
    report = service.evaluate("ex_squat", current)
    for res in report.results:
        assert res.status in (ObservabilityStatus.INSUFFICIENT_CONFIDENCE, ObservabilityStatus.NOT_OBSERVABLE)
        assert res.is_acceptable is None
        assert res.deviation is None


# =============================================================================
# 17. MISSING LANDMARKS
# =============================================================================

def test_17_missing_landmarks(service):
    """Empty joint angles dictionary must report all metrics as NOT_OBSERVABLE."""
    current = {"joint_angles": {}, "confidence": 0.90}
    report = service.evaluate("ex_squat", current)

    assert report.observable_count == 0
    for res in report.results:
        assert res.status == ObservabilityStatus.NOT_OBSERVABLE
        assert res.is_acceptable is None


# =============================================================================
# 18. NOT_OBSERVABLE BEHAVIOR (CRITICAL: MISSING DATA != BAD FORM)
# =============================================================================

def test_18_not_observable_behavior_missing_contralateral_limb(service):
    """If only left knee is visible, symmetry is NOT_OBSERVABLE, NEVER bad symmetry."""
    current = {
        "joint_angles": {"left_knee": 90.0},  # right_knee missing
        "confidence": 0.90,
    }
    report = service.evaluate("ex_squat", current)
    symm_res = next(r for r in report.results if r.heuristic_name == "squat_knee_symmetry")

    assert symm_res.status == ObservabilityStatus.NOT_OBSERVABLE
    assert symm_res.is_acceptable is None
    assert symm_res.deviation is None
    assert "not both observable" in symm_res.feedback


# =============================================================================
# 19. INVALID OBSERVATION
# =============================================================================

def test_19_invalid_observation_none(service):
    """Passing None as observation returns an INVALID input report."""
    report = service.evaluate("ex_squat", None)
    assert report.observable_count == 0
    assert report.is_sufficiently_observable is False
    assert report.results[0].status == ObservabilityStatus.INVALID


# =============================================================================
# 20. NAN / INFINITY PROTECTION
# =============================================================================

def test_20_nan_infinity_protection(service):
    """NaN or Inf angles must yield INVALID status, never NaN deviation or crashes."""
    nan_current = {"joint_angles": {"left_knee": float("nan"), "right_knee": 90.0}, "confidence": 0.90}
    inf_current = {"joint_angles": {"left_knee": float("inf"), "right_knee": 90.0}, "confidence": 0.90}

    report_nan = service.evaluate("ex_squat", nan_current)
    report_inf = service.evaluate("ex_squat", inf_current)

    nan_symm = next(r for r in report_nan.results if r.heuristic_name == "squat_knee_symmetry")
    inf_symm = next(r for r in report_inf.results if r.heuristic_name == "squat_knee_symmetry")

    assert nan_symm.status == ObservabilityStatus.INVALID
    assert inf_symm.status == ObservabilityStatus.INVALID


# =============================================================================
# 21. TEMPORAL NOISY OBSERVATIONS
# =============================================================================

def test_21_temporal_noisy_observations(service):
    """Slight velocity variance below threshold (std dev <= 6.0) remains acceptable."""
    history = [
        {"joint_angles": {"left_knee": 100.0}},
        {"joint_angles": {"left_knee": 103.0}},
        {"joint_angles": {"left_knee": 101.5}},
        {"joint_angles": {"left_knee": 104.0}},
    ]
    current = {"joint_angles": {"left_knee": 102.5}}
    res = next(r for r in service.evaluate("ex_squat", current, history).results if r.heuristic_name == "squat_movement_stability")

    assert res.status == ObservabilityStatus.OBSERVED
    assert res.is_acceptable is True


# =============================================================================
# 22. SINGLE-FRAME NOISE DOES NOT TRIGGER IMMEDIATE DEFECT
# =============================================================================

def test_22_single_frame_noise_filtered_by_window(service):
    """An isolated 4° wobble in an otherwise smooth 8-frame window does not fail stability."""
    history = [
        {"joint_angles": {"left_knee": 90.0}},
        {"joint_angles": {"left_knee": 91.0}},
        {"joint_angles": {"left_knee": 91.5}},
        {"joint_angles": {"left_knee": 92.0}},
        {"joint_angles": {"left_knee": 96.0}},  # single minor wobble
        {"joint_angles": {"left_knee": 92.5}},
        {"joint_angles": {"left_knee": 93.0}},
    ]
    current = {"joint_angles": {"left_knee": 93.5}}
    res = next(r for r in service.evaluate("ex_squat", current, history).results if r.heuristic_name == "squat_movement_stability")

    assert res.status == ObservabilityStatus.OBSERVED
    assert res.is_acceptable is True


# =============================================================================
# 23. DETERMINISM: IDENTICAL INPUTS = IDENTICAL OUTPUTS
# =============================================================================

@pytest.mark.parametrize("ex_id", ["ex_squat", "ex_bench_press", "ex_deadlift", "ex_bicep_curl", "ex_shoulder_press"])
def test_23_determinism(service, ex_id: str):
    """Two independent evaluations of identical data must produce identical reports."""
    obs = {
        "joint_angles": {
            "left_knee": 88.0, "right_knee": 89.0,
            "left_elbow": 85.0, "right_elbow": 86.0,
            "left_hip": 168.0, "right_hip": 169.0,
            "torso_angle": 35.0, "knee_tracking_ratio": 0.85,
            "elbow_flare": 55.0, "upper_arm_drift": 0.04,
            "forearm_tilt": 10.0, "torso_lean": 12.0,
        },
        "confidence": 0.95,
        "timestamp_ms": 1000.0,
    }
    svc1 = FormHeuristicsService()
    svc2 = FormHeuristicsService()

    rep1 = svc1.evaluate(ex_id, obs)
    rep2 = svc2.evaluate(ex_id, obs)

    assert len(rep1.results) == len(rep2.results)
    for r1, r2 in zip(rep1.results, rep2.results):
        assert r1.heuristic_name == r2.heuristic_name
        assert r1.status == r2.status
        assert r1.is_acceptable == r2.is_acceptable
        assert r1.observed_value == r2.observed_value
        assert r1.deviation == r2.deviation
        assert r1.feedback == r2.feedback


# =============================================================================
# 24, 25, 26. THRESHOLD BOUNDARY TESTS (EXACT, JUST-INSIDE, JUST-OUTSIDE)
# =============================================================================

def test_24_exact_threshold_boundary(service):
    """Exactly at depth threshold (95.0°) is acceptable with 0.0 deviation."""
    current = {"joint_angles": {"left_knee": 95.0}}
    res = next(r for r in service.evaluate("ex_squat", current).results if r.heuristic_name == "squat_depth")

    assert res.is_acceptable is True
    assert res.deviation == 0.0


def test_25_just_inside_threshold(service):
    """Just inside depth threshold (94.9°) is acceptable."""
    current = {"joint_angles": {"left_knee": 94.9}}
    res = next(r for r in service.evaluate("ex_squat", current).results if r.heuristic_name == "squat_depth")

    assert res.is_acceptable is True
    assert res.deviation == 0.0


def test_26_just_outside_threshold(service):
    """Just outside depth threshold (95.1°) is unacceptable with 0.1° deviation."""
    current = {"joint_angles": {"left_knee": 95.1}}
    res = next(r for r in service.evaluate("ex_squat", current).results if r.heuristic_name == "squat_depth")

    assert res.is_acceptable is False
    assert round(res.deviation, 1) == 0.1


# =============================================================================
# 27. CROSS-EXERCISE CONFIGURATION ISOLATION
# =============================================================================

def test_27_cross_exercise_configuration_isolation(service):
    """Customizing Squat config must not modify Bench Press config."""
    custom_squat = ExerciseHeuristicConfig(
        exercise_id="ex_squat",
        rom_target_angle=80.0,
        alignment_thresholds={"max_torso_inclination": 30.0},
    )
    custom_service = FormHeuristicsService(configs={
        "ex_squat": custom_squat,
        "ex_bench_press": STANDARD_HEURISTIC_CONFIGS["ex_bench_press"],
    })

    assert custom_service.get_config("ex_squat").rom_target_angle == 80.0
    assert custom_service.get_config("ex_bench_press").rom_target_angle == 90.0


# =============================================================================
# 28. INVALID EXERCISE ID
# =============================================================================

def test_28_invalid_exercise_id(service):
    """Unsupported exercise ID raises ValueError."""
    with pytest.raises(ValueError, match="Unsupported exercise"):
        service.evaluate("unknown_crossfit_move", {"joint_angles": {}})


# =============================================================================
# 29. INSUFFICIENT OBSERVATION HISTORY
# =============================================================================

def test_29_insufficient_observation_history(service):
    """Passing 1 frame when stability requires 3 yields NOT_OBSERVABLE, not an error."""
    history = [{"joint_angles": {"left_knee": 90.0}}]  # Only 1 frame in history + 1 current = 2 frames < 3
    current = {"joint_angles": {"left_knee": 91.0}}
    res = next(r for r in service.evaluate("ex_squat", current, history).results if r.heuristic_name == "squat_movement_stability")

    assert res.status == ObservabilityStatus.NOT_OBSERVABLE
    assert "Insufficient observation history" in res.feedback


# =============================================================================
# 30. OBSERVABILITY RATIO AND 70% SUFFICIENCY RULE FOR PHASE 9B.3
# =============================================================================

def test_30_observability_ratio_and_sufficient_data_rule(service):
    """
    If 4 of 5 heuristics are OBSERVED (80%), is_sufficiently_observable is True.
    If only 2 of 5 heuristics are OBSERVED (40%), is_sufficiently_observable is False.
    """
    # 4 of 5 observable
    mostly_observable = {
        "joint_angles": {
            "left_knee": 88.0,
            "right_knee": 89.0,
            "torso_angle": 35.0,
            # knee_tracking_ratio missing (1 not observable)
        },
        "confidence": 0.95,
    }
    history = [{"joint_angles": {"left_knee": 90.0}}, {"joint_angles": {"left_knee": 91.0}}]
    rep_high = service.evaluate("ex_squat", mostly_observable, history)
    assert rep_high.observability_ratio == 0.80
    assert rep_high.is_sufficiently_observable is True

    # 1 of 5 observable (only knee depth observable)
    poorly_observable = {
        "joint_angles": {"left_knee": 88.0},  # right_knee, torso, tracking, history all missing
        "confidence": 0.95,
    }
    rep_low = service.evaluate("ex_squat", poorly_observable, [])
    assert rep_low.observability_ratio == 0.20
    assert rep_low.is_sufficiently_observable is False
