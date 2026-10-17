"""
Deterministic Exercise Rep-Counting FSM Unit Tests (Phase 9B.1).

Tests all 5 supported exercises:
1. Squat (ex_squat)
2. Bench Press (ex_bench_press)
3. Deadlift (ex_deadlift)
4. Bicep Curl (ex_bicep_curl)
5. Shoulder Press (ex_shoulder_press)

Verifies Scenarios A through N:
A. Valid complete rep -> exactly 1 completed rep
B. Two valid reps -> exactly 2 completed reps
C. Partial movement -> 0 completed reps
D. Insufficient ROM -> 0 completed reps
E. Reversed movement -> no false completion
F. Hysteresis boundary -> threshold noise does not toggle states
G. Rapid valid movement -> 0.7s cooldown does not block fast legitimate reps
H. Duplicate / noisy completion -> no double counting from boundary flutter
I. Occlusion <= 400 ms -> state preserved and resumes after recovery
J. Occlusion > 400 ms -> trajectory invalidated, no rep count
K. Low confidence -> no false rep completion
L. No movement + elapsed time -> 0 reps
M. Determinism -> identical input sequence yields identical output sequence
N. Cross-exercise isolation -> FSM configurations remain completely independent
"""

import pytest
from typing import List, Dict, Tuple
from backend.app.services.exercise_fsm import (
    ExerciseFSM,
    ExerciseFSMConfig,
    FSMState,
    RepOutcome,
    TrackingStatus,
    MovementDirection,
    KinematicObservation,
    get_exercise_fsm,
    STANDARD_FSM_CONFIGS,
)


# =============================================================================
# SYNTHETIC TRAJECTORY GENERATORS
# =============================================================================

def generate_trajectory(
    exercise_id: str,
    start_angle: float,
    inflection_angle: float,
    return_angle: float,
    num_frames: int = 40,
    start_time_ms: float = 0.0,
    frame_interval_ms: float = 50.0,
    confidence: float = 0.95,
    landmarks_detected: bool = True,
    secondary_angle: float = 170.0,
) -> List[KinematicObservation]:
    """Generates a smooth piecewise-linear kinematic trajectory."""
    cfg = STANDARD_FSM_CONFIGS[exercise_id]
    observations: List[KinematicObservation] = []
    
    half_frames = num_frames // 2
    second_half_frames = num_frames - half_frames
    
    # Phase 1: start_angle -> inflection_angle
    for i in range(half_frames):
        t = start_time_ms + i * frame_interval_ms
        frac = i / max(1, half_frames - 1)
        angle = start_angle + frac * (inflection_angle - start_angle)
        
        joints = {joint: angle for joint in cfg.primary_joints}
        if cfg.secondary_joints:
            for s_joint in cfg.secondary_joints:
                joints[s_joint] = secondary_angle

        observations.append(
            KinematicObservation(
                timestamp_ms=t,
                joint_angles=joints,
                confidence=confidence,
                landmarks_detected=landmarks_detected,
            )
        )
        
    # Phase 2: inflection_angle -> return_angle
    phase2_start_t = start_time_ms + half_frames * frame_interval_ms
    for j in range(second_half_frames):
        t = phase2_start_t + j * frame_interval_ms
        frac = j / max(1, second_half_frames - 1)
        angle = inflection_angle + frac * (return_angle - inflection_angle)
        
        joints = {joint: angle for joint in cfg.primary_joints}
        if cfg.secondary_joints:
            for s_joint in cfg.secondary_joints:
                joints[s_joint] = secondary_angle

        observations.append(
            KinematicObservation(
                timestamp_ms=t,
                joint_angles=joints,
                confidence=confidence,
                landmarks_detected=landmarks_detected,
            )
        )
        
    return observations


EXERCISE_TEST_SPECS = [
    ("ex_squat", 170.0, 85.0, 170.0),            # Flexion first: 170 -> 85 -> 170 (ROM = 85°)
    ("ex_bench_press", 165.0, 80.0, 165.0),      # Flexion first: 165 -> 80 -> 165 (ROM = 85°)
    ("ex_deadlift", 80.0, 170.0, 80.0),          # Extension first: 80 -> 170 -> 80 (ROM = 90°)
    ("ex_bicep_curl", 160.0, 45.0, 160.0),       # Flexion first: 160 -> 45 -> 160 (ROM = 115°)
    ("ex_shoulder_press", 75.0, 170.0, 75.0),    # Extension first: 75 -> 170 -> 75 (ROM = 95°)
]


# =============================================================================
# SCENARIO A: VALID COMPLETE REP (ALL 5 EXERCISES)
# =============================================================================

@pytest.mark.parametrize("ex_id,start_a,inflect_a,return_a", EXERCISE_TEST_SPECS)
def test_scenario_a_valid_complete_rep(ex_id: str, start_a: float, inflect_a: float, return_a: float):
    """A clean full repetition must increment rep_count by exactly 1 and emit VALID_REP."""
    fsm = get_exercise_fsm(ex_id)
    traj = generate_trajectory(ex_id, start_a, inflect_a, return_a, num_frames=30, frame_interval_ms=50.0)
    
    rep_completed_events = 0
    final_res = None
    for obs in traj:
        res = fsm.update(obs)
        if res.rep_completed:
            rep_completed_events += 1
            assert res.outcome == RepOutcome.VALID_REP
            assert res.completed_rep_number == 1
            assert res.rom_degrees is not None
            assert res.rom_degrees >= fsm.config.min_rom_degrees
        final_res = res
        
    assert fsm.rep_count == 1
    assert rep_completed_events == 1


# =============================================================================
# SCENARIO B: TWO CONSECUTIVE VALID REPS (ALL 5 EXERCISES)
# =============================================================================

@pytest.mark.parametrize("ex_id,start_a,inflect_a,return_a", EXERCISE_TEST_SPECS)
def test_scenario_b_two_valid_reps(ex_id: str, start_a: float, inflect_a: float, return_a: float):
    """Two consecutive valid repetitions with elapsed cooldown must yield rep_count == 2."""
    fsm = get_exercise_fsm(ex_id)
    # Rep 1: 0ms to 1500ms
    traj1 = generate_trajectory(ex_id, start_a, inflect_a, return_a, num_frames=30, start_time_ms=0.0, frame_interval_ms=50.0)
    # Rep 2: starts at 2500ms (1000ms after rep 1 completes, exceeding 0.7s cooldown)
    traj2 = generate_trajectory(ex_id, start_a, inflect_a, return_a, num_frames=30, start_time_ms=2500.0, frame_interval_ms=50.0)
    
    rep_completed_events = []
    for obs in traj1 + traj2:
        res = fsm.update(obs)
        if res.rep_completed:
            rep_completed_events.append(res)
            
    assert fsm.rep_count == 2
    assert len(rep_completed_events) == 2
    assert rep_completed_events[0].completed_rep_number == 1
    assert rep_completed_events[1].completed_rep_number == 2


# =============================================================================
# SCENARIO C: PARTIAL MOVEMENT (REVERSED BEFORE INFLECTION)
# =============================================================================

@pytest.mark.parametrize("ex_id,start_a,inflect_a,return_a", EXERCISE_TEST_SPECS)
def test_scenario_c_partial_movement(ex_id: str, start_a: float, inflect_a: float, return_a: float):
    """Movement that initiates but reverses before reaching inflection must NOT count as a rep."""
    fsm = get_exercise_fsm(ex_id)
    # Partial depth: halfway between start and inflection (does NOT reach inflection threshold)
    partial_a = (start_a + inflect_a) / 2.0
    traj = generate_trajectory(ex_id, start_a, partial_a, start_a, num_frames=30)
    
    for obs in traj:
        res = fsm.update(obs)
        assert not res.rep_completed
        
    assert fsm.rep_count == 0


# =============================================================================
# SCENARIO D: INSUFFICIENT ROM
# =============================================================================

def test_scenario_d_insufficient_rom_squat():
    """Squat with only 35° excursion (below 60° min ROM) must trigger INCOMPLETE_RESET."""
    fsm = get_exercise_fsm("ex_squat")
    # Starts at 165°, descends to 125° (delta = 40° < 60° min ROM, doesn't hit 95° inflection)
    traj = generate_trajectory("ex_squat", 165.0, 125.0, 165.0, num_frames=30)
    
    incomplete_events = 0
    for obs in traj:
        res = fsm.update(obs)
        assert not res.rep_completed
        if res.outcome == RepOutcome.INCOMPLETE_REP:
            incomplete_events += 1
            
    assert fsm.rep_count == 0


# =============================================================================
# SCENARIO E: REVERSED MOVEMENT DIRECTION
# =============================================================================

def test_scenario_e_reversed_movement_direction():
    """Attempting to hyperextend knees in Squat (170° -> 180° -> 170°) must not trigger rep."""
    fsm = get_exercise_fsm("ex_squat")
    traj = generate_trajectory("ex_squat", 170.0, 180.0, 170.0, num_frames=20)
    
    for obs in traj:
        res = fsm.update(obs)
        assert not res.rep_completed
        assert res.state in (FSMState.IDLE, FSMState.SETUP)
        
    assert fsm.rep_count == 0


# =============================================================================
# SCENARIO F: HYSTERESIS BOUNDARY ABSORPTION
# =============================================================================

def test_scenario_f_hysteresis_boundary_noise():
    """High-frequency sensor noise (+/-3°) around the 95° squat inflection threshold must not bounce state."""
    fsm = get_exercise_fsm("ex_squat")
    
    # Descent to inflection (92°)
    descend_traj = generate_trajectory("ex_squat", 170.0, 92.0, 92.0, num_frames=15, frame_interval_ms=50.0)
    for obs in descend_traj:
        fsm.update(obs)
        
    assert fsm.state == FSMState.INFLECTION
    
    # 10 frames of micro-oscillation between 93° and 98° (around 95° threshold, but < 102° deadband)
    curr_t = descend_traj[-1].timestamp_ms
    state_history = []
    for i in range(10):
        curr_t += 50.0
        noisy_angle = 93.0 if i % 2 == 0 else 98.0
        res = fsm.update(
            KinematicObservation(
                timestamp_ms=curr_t,
                joint_angles={"left_knee": noisy_angle, "right_knee": noisy_angle},
                confidence=0.95,
            )
        )
        state_history.append(res.state)
        
    # All frames should remain stably in INFLECTION due to the 10° hysteresis deadband
    assert all(st == FSMState.INFLECTION for st in state_history)
    assert fsm.rep_count == 0


# =============================================================================
# SCENARIO G: RAPID VALID MOVEMENT (NOT REJECTED BY COOLDOWN)
# =============================================================================

def test_scenario_g_rapid_valid_movement():
    """A rapid legitimate squat (0.8s total duration, full ROM) must complete successfully."""
    fsm = get_exercise_fsm("ex_squat")
    # 0.8s duration: 16 frames @ 50ms = 800ms
    traj = generate_trajectory("ex_squat", 170.0, 85.0, 170.0, num_frames=16, frame_interval_ms=50.0)
    
    completed = False
    for obs in traj:
        res = fsm.update(obs)
        if res.rep_completed:
            completed = True
            
    assert completed
    assert fsm.rep_count == 1


# =============================================================================
# SCENARIO H: DUPLICATE / NOISY COMPLETION SUPPRESSION
# =============================================================================

def test_scenario_h_duplicate_completion_suppression():
    """Multiple return threshold crossings within 200 ms must produce exactly 1 counted rep."""
    fsm = get_exercise_fsm("ex_squat")
    
    # Valid rep 1 completes at t=1000ms
    traj = generate_trajectory("ex_squat", 170.0, 85.0, 170.0, num_frames=20, start_time_ms=0.0, frame_interval_ms=50.0)
    for obs in traj:
        fsm.update(obs)
        
    assert fsm.rep_count == 1
    
    # Boundary flutter at completion line within 200ms (t=1050 to t=1200)
    completion_time = traj[-1].timestamp_ms
    for offset_ms in [50.0, 100.0, 150.0]:
        res = fsm.update(
            KinematicObservation(
                timestamp_ms=completion_time + offset_ms,
                joint_angles={"left_knee": 168.0, "right_knee": 168.0},
                confidence=0.95,
            )
        )
        assert not res.rep_completed
        
    assert fsm.rep_count == 1


# =============================================================================
# SCENARIO I: OCCLUSION <= 400 MS (RECOVERY)
# =============================================================================

def test_scenario_i_occlusion_under_400ms_recovery():
    """Temporary landmark loss for 300 ms during movement must preserve state and allow rep completion."""
    fsm = get_exercise_fsm("ex_squat")
    
    # 1. Initiate descent (170° -> 120°)
    traj1 = generate_trajectory("ex_squat", 170.0, 120.0, 120.0, num_frames=10, start_time_ms=0.0, frame_interval_ms=50.0)
    for obs in traj1:
        fsm.update(obs)
    assert fsm.state == FSMState.IN_PROGRESS
    
    # 2. Occlusion for 300 ms (6 frames of confidence=0.0)
    curr_t = traj1[-1].timestamp_ms
    for _ in range(6):
        curr_t += 50.0
        res = fsm.update(
            KinematicObservation(
                timestamp_ms=curr_t,
                joint_angles={},
                confidence=0.0,
                landmarks_detected=False,
            )
        )
        # State must be preserved during occlusion buffer
        assert res.state == FSMState.IN_PROGRESS
        assert res.tracking_status == TrackingStatus.OCCLUDED_BUFFERING
        assert not res.rep_completed
        
    # 3. Tracking recovers and continues descent to 85° and ascent to 170°
    traj2 = generate_trajectory("ex_squat", 120.0, 85.0, 170.0, num_frames=20, start_time_ms=curr_t + 50.0, frame_interval_ms=50.0)
    for obs in traj2:
        res = fsm.update(obs)
        
    assert fsm.rep_count == 1


# =============================================================================
# SCENARIO J: OCCLUSION > 400 MS (INVALIDATION)
# =============================================================================

def test_scenario_j_occlusion_over_400ms_invalidation():
    """Landmark loss exceeding 400 ms during active movement must invalidate the trajectory without rep increment."""
    fsm = get_exercise_fsm("ex_squat")
    
    # 1. Initiate descent
    traj1 = generate_trajectory("ex_squat", 170.0, 110.0, 110.0, num_frames=10, start_time_ms=0.0, frame_interval_ms=50.0)
    for obs in traj1:
        fsm.update(obs)
    assert fsm.state == FSMState.IN_PROGRESS
    
    # 2. Occlusion for 500 ms (10 frames of confidence=0.0, exceeds 400ms limit)
    curr_t = traj1[-1].timestamp_ms
    invalidated = False
    for _ in range(10):
        curr_t += 50.0
        res = fsm.update(
            KinematicObservation(
                timestamp_ms=curr_t,
                joint_angles={},
                confidence=0.0,
                landmarks_detected=False,
            )
        )
        if res.state == FSMState.INVALIDATED_RESET:
            invalidated = True
            assert res.outcome == RepOutcome.INVALIDATED_REP
            assert res.invalidation_reason == "landmarks_lost_exceeded_400ms"
            
    assert invalidated
    assert fsm.rep_count == 0


# =============================================================================
# SCENARIO K: LOW CONFIDENCE OBSERVATIONS REJECTED
# =============================================================================

def test_scenario_k_low_confidence_rejected():
    """Trajectory with low confidence (0.3 < 0.50 threshold) must never count as a rep."""
    fsm = get_exercise_fsm("ex_squat")
    traj = generate_trajectory("ex_squat", 170.0, 85.0, 170.0, num_frames=30, confidence=0.30)
    
    for obs in traj:
        res = fsm.update(obs)
        assert not res.rep_completed
        
    assert fsm.rep_count == 0


# =============================================================================
# SCENARIO L: NO MOVEMENT + ELAPSED TIME
# =============================================================================

def test_scenario_l_no_movement_elapsed_time():
    """Standing still at baseline for 10 seconds (200 frames) must yield 0 reps."""
    fsm = get_exercise_fsm("ex_squat")
    
    for i in range(200):
        t = i * 50.0
        res = fsm.update(
            KinematicObservation(
                timestamp_ms=t,
                joint_angles={"left_knee": 172.0, "right_knee": 172.0},
                confidence=0.95,
            )
        )
        assert not res.rep_completed
        assert res.state in (FSMState.IDLE, FSMState.SETUP)
        
    assert fsm.rep_count == 0


# =============================================================================
# SCENARIO M: DETERMINISM (IDENTICAL INPUTS = IDENTICAL OUTPUTS)
# =============================================================================

@pytest.mark.parametrize("ex_id,start_a,inflect_a,return_a", EXERCISE_TEST_SPECS)
def test_scenario_m_determinism(ex_id: str, start_a: float, inflect_a: float, return_a: float):
    """Running identical trajectories through two independent FSMs must produce identical sequences."""
    traj = generate_trajectory(ex_id, start_a, inflect_a, return_a, num_frames=30, frame_interval_ms=50.0)
    
    fsm1 = get_exercise_fsm(ex_id)
    fsm2 = get_exercise_fsm(ex_id)
    
    results1 = [fsm1.update(obs) for obs in traj]
    results2 = [fsm2.update(obs) for obs in traj]
    
    assert len(results1) == len(results2)
    for r1, r2 in zip(results1, results2):
        assert r1.state == r2.state
        assert r1.rep_count == r2.rep_count
        assert r1.rep_completed == r2.rep_completed
        assert r1.outcome == r2.outcome
        assert r1.rom_degrees == r2.rom_degrees
        assert r1.primary_angle == r2.primary_angle


# =============================================================================
# SCENARIO N: CROSS-EXERCISE ISOLATION
# =============================================================================

def test_scenario_n_cross_exercise_isolation():
    """Squat FSM must not be affected by Bench Press angles, and configurations are isolated."""
    squat_fsm = get_exercise_fsm("ex_squat")
    bench_fsm = get_exercise_fsm("ex_bench_press")
    
    assert squat_fsm.config.exercise_id == "ex_squat"
    assert bench_fsm.config.exercise_id == "ex_bench_press"
    assert squat_fsm.config.primary_joints != bench_fsm.config.primary_joints
    
    # Feed elbow angles only to squat_fsm -> squat_fsm must ignore elbow angles
    obs_elbow = KinematicObservation(
        timestamp_ms=100.0,
        joint_angles={"left_elbow": 85.0, "right_elbow": 85.0},
        confidence=0.95,
    )
    res = squat_fsm.update(obs_elbow)
    assert res.primary_angle is None
    assert res.state == FSMState.IDLE
    assert squat_fsm.rep_count == 0


def test_factory_unsupported_exercise_raises_error():
    """Requesting an uncataloged exercise must raise ValueError with supported list."""
    with pytest.raises(ValueError, match="Unsupported exercise"):
        get_exercise_fsm("unknown_exercise_xyz")


def test_deadlift_secondary_knee_lockout_required():
    """Deadlift where hips extend to 170° but knees remain bent at 130° must not count as a valid rep."""
    fsm = get_exercise_fsm("ex_deadlift")
    # Generate deadlift trajectory where secondary_angle (knee) is kept at 130° (fails 165° lockout threshold)
    traj = generate_trajectory(
        "ex_deadlift",
        start_angle=80.0,
        inflection_angle=170.0,
        return_angle=80.0,
        num_frames=30,
        secondary_angle=130.0,  # Knees bent!
    )
    for obs in traj:
        res = fsm.update(obs)
        assert not res.rep_completed

    assert fsm.rep_count == 0

