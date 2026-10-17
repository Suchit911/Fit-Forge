"""
Exercise Rep-Counting Finite State Machine (Phase 9B.1).

Provides:
- Deterministic Finite State Machines (FSMs) for:
    1. Squat (ex_squat)
    2. Bench Press (ex_bench_press)
    3. Deadlift (ex_deadlift)
    4. Bicep Curl (ex_bicep_curl)
    5. Shoulder Press (ex_shoulder_press)
- Phase progression: IDLE -> SETUP -> IN_PROGRESS -> INFLECTION -> RETURNING -> COMPLETED
- Boundary hysteresis (deadband +/-8° to 12°) preventing boundary flutter.
- Minimum Range of Motion (ROM) enforcement rejecting partial twitches.
- Secondary refractory cooldown (0.7s) to debounce duplicate rep events.
- Strict 400 ms landmark occlusion buffering & invalidation rule.
- Deterministic confidence checking.
- Kinematic-first invariant: rep counting is strictly governed by observed joint kinematics,
  never by elapsed time.
"""

from enum import Enum
from dataclasses import dataclass, field
from typing import Dict, List, Optional, Tuple, Union, Any


class FSMState(str, Enum):
    IDLE = "IDLE"
    SETUP = "SETUP"
    IN_PROGRESS = "IN_PROGRESS"
    INFLECTION = "INFLECTION"
    RETURNING = "RETURNING"
    COMPLETED = "COMPLETED"
    INCOMPLETE_RESET = "INCOMPLETE_RESET"
    INVALIDATED_RESET = "INVALIDATED_RESET"


class MovementDirection(str, Enum):
    """
    Direction of primary joint angle during the first active phase of movement.
    - FLEXION_FIRST: Angle decreases from extended baseline to flexed inflection (e.g. Squat, Bench, Curl).
    - EXTENSION_FIRST: Angle increases from flexed baseline to extended inflection (e.g. Deadlift, Shoulder Press).
    """
    FLEXION_FIRST = "FLEXION_FIRST"
    EXTENSION_FIRST = "EXTENSION_FIRST"


class RepOutcome(str, Enum):
    NONE = "NONE"
    VALID_REP = "VALID_REP"
    INCOMPLETE_REP = "INCOMPLETE_REP"
    INVALIDATED_REP = "INVALIDATED_REP"
    INSUFFICIENT_CONFIDENCE = "INSUFFICIENT_CONFIDENCE"


class TrackingStatus(str, Enum):
    TRACKING_ACTIVE = "TRACKING_ACTIVE"
    OCCLUDED_BUFFERING = "OCCLUDED_BUFFERING"
    LOST = "LOST"
    LOW_CONFIDENCE = "LOW_CONFIDENCE"


@dataclass(frozen=True)
class ExerciseFSMConfig:
    """Configurable kinematic thresholds and boundaries for an exercise FSM."""
    exercise_id: str
    canonical_name: str
    primary_joints: Tuple[str, ...]
    secondary_joints: Optional[Tuple[str, ...]] = None
    start_threshold: float = 160.0
    initiation_delta: float = 12.0
    inflection_threshold: float = 95.0
    return_threshold: float = 160.0
    min_rom_degrees: float = 60.0
    hysteresis_degrees: float = 10.0
    direction: MovementDirection = MovementDirection.FLEXION_FIRST
    refractory_cooldown_seconds: float = 0.7
    max_occlusion_ms: float = 400.0
    min_tracking_confidence: float = 0.50
    secondary_lockout_threshold: Optional[float] = None  # e.g. for Deadlift knee lockout


# Standard Exercise Configurations (Approved Initial Thresholds)
STANDARD_FSM_CONFIGS: Dict[str, ExerciseFSMConfig] = {
    # Squat: Knee flexion from >160° to <=95° at parallel/depth, return >160°, min ROM >= 60°
    "ex_squat": ExerciseFSMConfig(
        exercise_id="ex_squat",
        canonical_name="Squat",
        primary_joints=("left_knee", "right_knee"),
        start_threshold=160.0,
        initiation_delta=12.0,
        inflection_threshold=95.0,
        return_threshold=160.0,
        min_rom_degrees=60.0,
        hysteresis_degrees=10.0,
        direction=MovementDirection.FLEXION_FIRST,
        refractory_cooldown_seconds=0.7,
        max_occlusion_ms=400.0,
        min_tracking_confidence=0.50,
    ),
    # Bench Press: Elbow flexion from >155° to <=90° at bottom, return >155°, min ROM >= 55°
    "ex_bench_press": ExerciseFSMConfig(
        exercise_id="ex_bench_press",
        canonical_name="Bench Press",
        primary_joints=("left_elbow", "right_elbow"),
        start_threshold=155.0,
        initiation_delta=12.0,
        inflection_threshold=90.0,
        return_threshold=155.0,
        min_rom_degrees=55.0,
        hysteresis_degrees=10.0,
        direction=MovementDirection.FLEXION_FIRST,
        refractory_cooldown_seconds=0.7,
        max_occlusion_ms=400.0,
        min_tracking_confidence=0.50,
    ),
    # Deadlift: Hip angle from <=90° at floor to >=165° at lockout, knee lockout >=165°, min ROM >= 65°
    "ex_deadlift": ExerciseFSMConfig(
        exercise_id="ex_deadlift",
        canonical_name="Deadlift",
        primary_joints=("left_hip", "right_hip"),
        secondary_joints=("left_knee", "right_knee"),
        start_threshold=90.0,
        initiation_delta=12.0,
        inflection_threshold=165.0,
        return_threshold=90.0,
        min_rom_degrees=65.0,
        hysteresis_degrees=10.0,
        direction=MovementDirection.EXTENSION_FIRST,
        refractory_cooldown_seconds=0.7,
        max_occlusion_ms=400.0,
        min_tracking_confidence=0.50,
        secondary_lockout_threshold=165.0,
    ),
    # Bicep Curl: Elbow flexion from >150° to <=55° at peak, return >150°, min ROM >= 80°
    "ex_bicep_curl": ExerciseFSMConfig(
        exercise_id="ex_bicep_curl",
        canonical_name="Bicep Curl",
        primary_joints=("left_elbow", "right_elbow"),
        start_threshold=150.0,
        initiation_delta=12.0,
        inflection_threshold=55.0,
        return_threshold=150.0,
        min_rom_degrees=80.0,
        hysteresis_degrees=10.0,
        direction=MovementDirection.FLEXION_FIRST,
        refractory_cooldown_seconds=0.7,
        max_occlusion_ms=400.0,
        min_tracking_confidence=0.50,
    ),
    # Shoulder Press: Elbow drive from <=85° to overhead >=165°, return <=85°, min ROM >= 70°
    "ex_shoulder_press": ExerciseFSMConfig(
        exercise_id="ex_shoulder_press",
        canonical_name="Shoulder Press",
        primary_joints=("left_elbow", "right_elbow"),
        start_threshold=85.0,
        initiation_delta=12.0,
        inflection_threshold=165.0,
        return_threshold=85.0,
        min_rom_degrees=70.0,
        hysteresis_degrees=10.0,
        direction=MovementDirection.EXTENSION_FIRST,
        refractory_cooldown_seconds=0.7,
        max_occlusion_ms=400.0,
        min_tracking_confidence=0.50,
    ),
}

# Aliases for flexible exercise lookup
EXERCISE_ALIASES: Dict[str, str] = {
    "squat": "ex_squat",
    "barbell_squat": "ex_squat",
    "ex_squat": "ex_squat",
    "bench": "ex_bench_press",
    "bench_press": "ex_bench_press",
    "ex_bench_press": "ex_bench_press",
    "deadlift": "ex_deadlift",
    "ex_deadlift": "ex_deadlift",
    "bicep_curl": "ex_bicep_curl",
    "curl": "ex_bicep_curl",
    "ex_bicep_curl": "ex_bicep_curl",
    "shoulder_press": "ex_shoulder_press",
    "overhead_press": "ex_shoulder_press",
    "ohp": "ex_shoulder_press",
    "ex_shoulder_press": "ex_shoulder_press",
}


@dataclass
class KinematicObservation:
    """Single-frame kinematic measurement provided to the FSM."""
    timestamp_ms: float
    joint_angles: Dict[str, float]
    confidence: float
    landmarks_detected: bool = True


@dataclass
class FSMUpdateResult:
    """Structured result produced by the FSM on each observation update."""
    exercise_id: str
    state: FSMState
    rep_count: int
    rep_completed: bool
    completed_rep_number: Optional[int] = None
    rom_degrees: Optional[float] = None
    outcome: RepOutcome = RepOutcome.NONE
    invalidation_reason: Optional[str] = None
    primary_angle: Optional[float] = None
    movement_start_timestamp_ms: Optional[float] = None
    inflection_timestamp_ms: Optional[float] = None
    completion_timestamp_ms: Optional[float] = None
    duration_ms: Optional[float] = None
    tracking_status: TrackingStatus = TrackingStatus.TRACKING_ACTIVE


class ExerciseFSM:
    """
    Deterministic Finite State Machine for exercise rep counting.
    Operates strictly on kinematic observations. Timers are never substituted for movement.
    """

    def __init__(self, config: ExerciseFSMConfig):
        self.config = config
        self.state: FSMState = FSMState.IDLE
        self.rep_count: int = 0

        # Trajectory tracking
        self._baseline_angle: Optional[float] = None
        self._inflection_angle: Optional[float] = None
        self._movement_start_timestamp_ms: Optional[float] = None
        self._inflection_timestamp_ms: Optional[float] = None
        self._last_completed_timestamp_ms: Optional[float] = None

        # Occlusion tracking
        self._occlusion_start_timestamp_ms: Optional[float] = None
        self._pre_occlusion_state: Optional[FSMState] = None

    def reset(self) -> None:
        """Resets the state machine to IDLE with 0 reps."""
        self.state = FSMState.IDLE
        self.rep_count = 0
        self._reset_trajectory()
        self._occlusion_start_timestamp_ms = None
        self._pre_occlusion_state = None
        self._last_completed_timestamp_ms = None

    def _reset_trajectory(self) -> None:
        """Resets the active single-repetition trajectory state."""
        self._baseline_angle = None
        self._inflection_angle = None
        self._movement_start_timestamp_ms = None
        self._inflection_timestamp_ms = None
        self._occlusion_start_timestamp_ms = None
        self._pre_occlusion_state = None

    def _extract_primary_angle(self, joint_angles: Dict[str, float]) -> Optional[float]:
        """Extracts the representative primary joint angle from observation."""
        available_angles: List[float] = []
        for joint in self.config.primary_joints:
            if joint in joint_angles and joint_angles[joint] is not None:
                available_angles.append(joint_angles[joint])

        if not available_angles:
            return None
        # Use mean of available bilateral angles
        return sum(available_angles) / len(available_angles)

    def _check_secondary_lockout(self, joint_angles: Dict[str, float]) -> bool:
        """Verifies secondary joint lockout (e.g. knees extended in Deadlift)."""
        if not self.config.secondary_joints or self.config.secondary_lockout_threshold is None:
            return True

        secondary_angles: List[float] = []
        for joint in self.config.secondary_joints:
            if joint in joint_angles and joint_angles[joint] is not None:
                secondary_angles.append(joint_angles[joint])

        if not secondary_angles:
            # Secondary joint not observed; fail lockout
            return False

        avg_sec = sum(secondary_angles) / len(secondary_angles)
        return avg_sec >= self.config.secondary_lockout_threshold

    def update(self, obs: KinematicObservation) -> FSMUpdateResult:
        """
        Updates the FSM with a new kinematic observation.
        
        Deterministic: Given the exact same sequence of observations,
        this method produces the exact same sequence of results.
        """
        t = obs.timestamp_ms
        conf = obs.confidence
        landmarks_ok = obs.landmarks_detected and (conf >= self.config.min_tracking_confidence)
        primary_angle = self._extract_primary_angle(obs.joint_angles)

        # ---------------------------------------------------------------------
        # 1. LANDMARK OCCLUSION & TRACKING LOSS HANDLING (400 ms Rule)
        # ---------------------------------------------------------------------
        if not landmarks_ok or primary_angle is None:
            # If in an active rep trajectory (IN_PROGRESS, INFLECTION, RETURNING)
            if self.state in (FSMState.IN_PROGRESS, FSMState.INFLECTION, FSMState.RETURNING):
                if self._occlusion_start_timestamp_ms is None:
                    self._occlusion_start_timestamp_ms = t
                    self._pre_occlusion_state = self.state

                elapsed_occlusion = t - self._occlusion_start_timestamp_ms
                if elapsed_occlusion <= self.config.max_occlusion_ms:
                    # Within 400 ms: retain state, do not advance FSM, buffer
                    return FSMUpdateResult(
                        exercise_id=self.config.exercise_id,
                        state=self.state,
                        rep_count=self.rep_count,
                        rep_completed=False,
                        outcome=RepOutcome.NONE,
                        primary_angle=None,
                        tracking_status=TrackingStatus.OCCLUDED_BUFFERING,
                    )
                else:
                    # Exceeded 400 ms: invalidate rep trajectory, reset
                    self.state = FSMState.INVALIDATED_RESET
                    self._reset_trajectory()
                    return FSMUpdateResult(
                        exercise_id=self.config.exercise_id,
                        state=FSMState.INVALIDATED_RESET,
                        rep_count=self.rep_count,
                        rep_completed=False,
                        outcome=RepOutcome.INVALIDATED_REP,
                        invalidation_reason="landmarks_lost_exceeded_400ms",
                        primary_angle=None,
                        tracking_status=TrackingStatus.LOST,
                    )
            else:
                # Not in active trajectory; transition to IDLE if landmarks lost
                self.state = FSMState.IDLE
                self._reset_trajectory()
                return FSMUpdateResult(
                    exercise_id=self.config.exercise_id,
                    state=FSMState.IDLE,
                    rep_count=self.rep_count,
                    rep_completed=False,
                    outcome=RepOutcome.NONE,
                    primary_angle=None,
                    tracking_status=TrackingStatus.LOW_CONFIDENCE if obs.landmarks_detected else TrackingStatus.LOST,
                )

        # Landmarks are valid and confidence is sufficient
        # If recovering from temporary occlusion <= 400 ms:
        if self._occlusion_start_timestamp_ms is not None:
            self._occlusion_start_timestamp_ms = None
            self._pre_occlusion_state = None

        # Handle post-reset cleanup frames
        if self.state in (FSMState.INCOMPLETE_RESET, FSMState.INVALIDATED_RESET):
            self._reset_trajectory()
            self.state = FSMState.IDLE

        cfg = self.config
        rep_completed_now = False
        completed_rep_number: Optional[int] = None
        rom_calculated: Optional[float] = None
        duration_ms: Optional[float] = None
        outcome = RepOutcome.NONE
        invalidation_reason: Optional[str] = None

        # ---------------------------------------------------------------------
        # 2. FINITE STATE MACHINE TRANSITIONS
        # ---------------------------------------------------------------------
        if self.state == FSMState.IDLE:
            # Check if athlete is in starting posture
            if self._is_at_start_posture(primary_angle):
                self.state = FSMState.SETUP
                self._baseline_angle = primary_angle

        elif self.state == FSMState.SETUP:
            # Update baseline angle while stationary in starting posture
            if self._is_at_start_posture(primary_angle):
                self._baseline_angle = primary_angle
            elif self._has_initiated_movement(primary_angle):
                # Movement initiation detected beyond deadband delta
                self.state = FSMState.IN_PROGRESS
                self._movement_start_timestamp_ms = t
                if self._baseline_angle is None:
                    self._baseline_angle = cfg.start_threshold
                self._inflection_angle = primary_angle
            else:
                # Still in setup/starting zone
                pass

        elif self.state == FSMState.IN_PROGRESS:
            # Update extreme angle reached so far
            if cfg.direction == MovementDirection.FLEXION_FIRST:
                if self._inflection_angle is None or primary_angle < self._inflection_angle:
                    self._inflection_angle = primary_angle
            else:
                if self._inflection_angle is None or primary_angle > self._inflection_angle:
                    self._inflection_angle = primary_angle

            # Check if target inflection threshold reached
            if self._has_reached_inflection(primary_angle):
                # Check secondary requirement (e.g. knee lockout for deadlift)
                if self._check_secondary_lockout(obs.joint_angles):
                    self.state = FSMState.INFLECTION
                    self._inflection_timestamp_ms = t
            elif self._has_reversed_prematurely(primary_angle):
                # Athlete reversed back toward start before reaching inflection threshold
                self.state = FSMState.INCOMPLETE_RESET
                outcome = RepOutcome.INCOMPLETE_REP
                invalidation_reason = "premature_reversal_before_inflection"
                self._reset_trajectory()

        elif self.state == FSMState.INFLECTION:
            # Track peak extreme inflection
            if cfg.direction == MovementDirection.FLEXION_FIRST:
                if primary_angle < self._inflection_angle:
                    self._inflection_angle = primary_angle
            else:
                if primary_angle > self._inflection_angle:
                    self._inflection_angle = primary_angle

            # Check if movement has reversed direction past the hysteresis deadband
            if self._has_cleared_inflection_hysteresis(primary_angle):
                self.state = FSMState.RETURNING

        elif self.state == FSMState.RETURNING:
            # Check if athlete has successfully returned to starting threshold
            if self._is_at_return_posture(primary_angle):
                # Compute actual observed Range of Motion (ROM)
                start_a = self._baseline_angle if self._baseline_angle is not None else cfg.start_threshold
                inflect_a = self._inflection_angle if self._inflection_angle is not None else cfg.inflection_threshold
                rom = abs(start_a - inflect_a)
                rom_calculated = round(rom, 1)

                # Check Minimum ROM Requirement
                if rom < cfg.min_rom_degrees:
                    # Incomplete rep: did not satisfy minimum ROM
                    self.state = FSMState.INCOMPLETE_RESET
                    outcome = RepOutcome.INCOMPLETE_REP
                    invalidation_reason = f"insufficient_rom_{rom:.1f}_below_min_{cfg.min_rom_degrees}"
                    self._reset_trajectory()
                else:
                    # Secondary Refractory Cooldown Check (0.7s debounce)
                    cooldown_ms = cfg.refractory_cooldown_seconds * 1000.0
                    if (
                        self._last_completed_timestamp_ms is not None
                        and (t - self._last_completed_timestamp_ms) < cooldown_ms
                    ):
                        # Suppress duplicate completion event from boundary bounce
                        outcome = RepOutcome.NONE
                        self.state = FSMState.SETUP
                        self._reset_trajectory()
                    else:
                        # VALID REPETITION COMPLETED!
                        self.rep_count += 1
                        rep_completed_now = True
                        completed_rep_number = self.rep_count
                        outcome = RepOutcome.VALID_REP
                        self.state = FSMState.COMPLETED
                        self._last_completed_timestamp_ms = t

                        if self._movement_start_timestamp_ms is not None:
                            duration_ms = round(t - self._movement_start_timestamp_ms, 1)

                        # Auto-transition back to SETUP for next rep
                        self._reset_trajectory()
                        self._baseline_angle = primary_angle

        elif self.state == FSMState.COMPLETED:
            # Transient state: transition back to SETUP or IDLE
            if self._is_at_start_posture(primary_angle):
                self.state = FSMState.SETUP
                self._baseline_angle = primary_angle
            else:
                self.state = FSMState.IDLE

        return FSMUpdateResult(
            exercise_id=cfg.exercise_id,
            state=self.state,
            rep_count=self.rep_count,
            rep_completed=rep_completed_now,
            completed_rep_number=completed_rep_number,
            rom_degrees=rom_calculated,
            outcome=outcome,
            invalidation_reason=invalidation_reason,
            primary_angle=round(primary_angle, 1) if primary_angle is not None else None,
            movement_start_timestamp_ms=self._movement_start_timestamp_ms,
            inflection_timestamp_ms=self._inflection_timestamp_ms,
            completion_timestamp_ms=t if rep_completed_now else None,
            duration_ms=duration_ms,
            tracking_status=TrackingStatus.TRACKING_ACTIVE,
        )

    # -------------------------------------------------------------------------
    # HELPER KINEMATIC THRESHOLD EVALUATORS
    # -------------------------------------------------------------------------
    def _is_at_start_posture(self, angle: float) -> bool:
        cfg = self.config
        if cfg.direction == MovementDirection.FLEXION_FIRST:
            return angle >= (cfg.start_threshold - cfg.hysteresis_degrees)
        else:
            return angle <= (cfg.start_threshold + cfg.hysteresis_degrees)

    def _has_initiated_movement(self, angle: float) -> bool:
        cfg = self.config
        base = self._baseline_angle if self._baseline_angle is not None else cfg.start_threshold
        if cfg.direction == MovementDirection.FLEXION_FIRST:
            return angle <= (base - cfg.initiation_delta)
        else:
            return angle >= (base + cfg.initiation_delta)

    def _has_reached_inflection(self, angle: float) -> bool:
        cfg = self.config
        if cfg.direction == MovementDirection.FLEXION_FIRST:
            return angle <= cfg.inflection_threshold
        else:
            return angle >= cfg.inflection_threshold

    def _has_cleared_inflection_hysteresis(self, angle: float) -> bool:
        cfg = self.config
        inflect = self._inflection_angle if self._inflection_angle is not None else cfg.inflection_threshold
        if cfg.direction == MovementDirection.FLEXION_FIRST:
            return angle >= (inflect + cfg.hysteresis_degrees)
        else:
            return angle <= (inflect - cfg.hysteresis_degrees)

    def _has_reversed_prematurely(self, angle: float) -> bool:
        cfg = self.config
        inflect = self._inflection_angle if self._inflection_angle is not None else angle
        base = self._baseline_angle if self._baseline_angle is not None else cfg.start_threshold
        # If angle reversed significantly back toward base before reaching inflection
        if cfg.direction == MovementDirection.FLEXION_FIRST:
            # Moving back up without reaching inflection threshold
            if inflect > cfg.inflection_threshold and angle >= (inflect + cfg.hysteresis_degrees * 1.5):
                return True
        else:
            # Moving back down without reaching inflection threshold
            if inflect < cfg.inflection_threshold and angle <= (inflect - cfg.hysteresis_degrees * 1.5):
                return True
        return False

    def _is_at_return_posture(self, angle: float) -> bool:
        cfg = self.config
        base = self._baseline_angle if self._baseline_angle is not None else cfg.start_threshold
        if cfg.direction == MovementDirection.FLEXION_FIRST:
            return angle >= (base - cfg.hysteresis_degrees)
        else:
            return angle <= (base + cfg.hysteresis_degrees)


def get_exercise_fsm(exercise_id_or_name: str) -> ExerciseFSM:
    """
    Factory function returning an instantiated ExerciseFSM for the requested exercise.
    Supports canonical IDs (e.g. 'ex_squat') and aliases (e.g. 'squat').
    """
    clean_key = exercise_id_or_name.strip().lower()
    canonical_id = EXERCISE_ALIASES.get(clean_key)

    if not canonical_id or canonical_id not in STANDARD_FSM_CONFIGS:
        supported = list(STANDARD_FSM_CONFIGS.keys())
        raise ValueError(
            f"Unsupported exercise '{exercise_id_or_name}'. "
            f"Phase 9B supports the following exercises: {supported}."
        )

    config = STANDARD_FSM_CONFIGS[canonical_id]
    return ExerciseFSM(config=config)
