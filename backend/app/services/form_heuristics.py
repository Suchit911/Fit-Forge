"""
Deterministic Exercise Form Heuristics Engine (Phase 9B.2).

Provides:
- Deterministic, explainable visual form heuristics for:
    1. Squat (ex_squat)
    2. Bench Press (ex_bench_press)
    3. Deadlift (ex_deadlift)
    4. Bicep Curl (ex_bicep_curl)
    5. Shoulder Press (ex_shoulder_press)
- Observability Model:
    OBSERVED: Metric was measured with sufficient confidence.
    INSUFFICIENT_CONFIDENCE: Keypoints detected but confidence below threshold.
    NOT_OBSERVABLE: Required landmarks/views are absent from the observation.
    INVALID: Corrupt, NaN, out-of-bounds, or malformed data.
- Four Core Categories:
    1. ROM (Range of Motion)
    2. Joint Alignment / Technique
    3. Symmetry
    4. Stability
- Critical Guardrail: MISSING DATA != BAD FORM. Missing or low-confidence data
  is reported as NOT_OBSERVABLE / INSUFFICIENT_CONFIDENCE, never as a form defect.
- No medical diagnosis, no injury prevention claims, no 'safe/unsafe' labels.
- Deterministic feedback templates parameterized from actual observed values.
- Zero LLM generation, zero image decoding, zero rep-counting logic.
"""

import math
from enum import Enum
from dataclasses import dataclass, field
from typing import Dict, List, Optional, Tuple, Union, Any

from ..schemas.form_analysis import (
    ObservabilityStatus,
    HeuristicCategory,
    FormHeuristicResultSchema,
    ExerciseFormReportSchema,
)


# =============================================================================
# HEURISTIC RESULT DATA STRUCTURES
# =============================================================================

@dataclass
class FormHeuristicResult:
    """Individual technique heuristic evaluation result."""
    exercise_id: str
    category: HeuristicCategory
    heuristic_name: str
    status: ObservabilityStatus
    is_acceptable: Optional[bool] = None
    observed_value: Optional[float] = None
    reference_value: Optional[Union[float, Tuple[float, float], List[float]]] = None
    deviation: Optional[float] = None
    confidence: float = 0.0
    feedback: str = ""
    unit: str = "degrees"
    timestamp_ms: Optional[float] = None

    def to_schema(self) -> FormHeuristicResultSchema:
        ref_val = None
        if isinstance(self.reference_value, (tuple, list)):
            ref_val = list(self.reference_value)
        elif isinstance(self.reference_value, (int, float)):
            ref_val = float(self.reference_value)

        return FormHeuristicResultSchema(
            exercise_id=self.exercise_id,
            category=self.category.value if isinstance(self.category, Enum) else str(self.category),
            heuristic_name=self.heuristic_name,
            status=self.status.value if isinstance(self.status, Enum) else str(self.status),
            is_acceptable=self.is_acceptable,
            observed_value=round(self.observed_value, 2) if self.observed_value is not None else None,
            reference_value=ref_val,
            deviation=round(self.deviation, 2) if self.deviation is not None else None,
            confidence=round(self.confidence, 3),
            feedback=self.feedback,
            unit=self.unit,
            timestamp_ms=self.timestamp_ms,
        )


@dataclass
class ExerciseFormReport:
    """Consolidated technique report across all heuristics for an exercise."""
    exercise_id: str
    timestamp_ms: float
    results: List[FormHeuristicResult] = field(default_factory=list)
    observable_count: int = 0
    total_required_count: int = 0
    observability_ratio: float = 0.0
    is_sufficiently_observable: bool = False

    def to_schema(self) -> ExerciseFormReportSchema:
        return ExerciseFormReportSchema(
            exercise_id=self.exercise_id,
            timestamp_ms=self.timestamp_ms,
            results=[r.to_schema() for r in self.results],
            observable_count=self.observable_count,
            total_required_count=self.total_required_count,
            observability_ratio=round(self.observability_ratio, 3),
            is_sufficiently_observable=self.is_sufficiently_observable,
        )


# =============================================================================
# CENTRALIZED CONFIGURATION FOR EXERCISE HEURISTICS
# =============================================================================

@dataclass(frozen=True)
class ExerciseHeuristicConfig:
    """Centralized thresholds and tolerances for an exercise."""
    exercise_id: str
    # ROM
    rom_target_angle: float
    rom_acceptable_tolerance: float = 5.0
    # Alignment / Technique
    alignment_thresholds: Dict[str, Any] = field(default_factory=dict)
    # Symmetry
    max_symmetry_difference_degrees: float = 12.0
    # Stability
    max_stability_std_dev: float = 6.0
    min_stability_history_frames: int = 3
    # Confidence
    min_confidence_threshold: float = 0.50


STANDARD_HEURISTIC_CONFIGS: Dict[str, ExerciseHeuristicConfig] = {
    # Squat
    "ex_squat": ExerciseHeuristicConfig(
        exercise_id="ex_squat",
        rom_target_angle=95.0,  # Parallel depth threshold: <= 95° knee angle
        rom_acceptable_tolerance=5.0,
        alignment_thresholds={
            "max_torso_inclination": 45.0,  # Degrees forward lean from vertical
            "min_knee_tracking_ratio": 0.75, # Inter-knee / inter-ankle width ratio
        },
        max_symmetry_difference_degrees=12.0,
        max_stability_std_dev=6.0,
        min_stability_history_frames=3,
        min_confidence_threshold=0.50,
    ),
    # Bench Press
    "ex_bench_press": ExerciseHeuristicConfig(
        exercise_id="ex_bench_press",
        rom_target_angle=90.0,  # Bottom pressing depth: <= 90° elbow angle
        rom_acceptable_tolerance=5.0,
        alignment_thresholds={
            "elbow_flare_min": 35.0,  # Minimum elbow tuck from torso
            "elbow_flare_max": 75.0,  # Maximum allowable elbow flare
        },
        max_symmetry_difference_degrees=12.0,
        max_stability_std_dev=6.0,
        min_stability_history_frames=3,
        min_confidence_threshold=0.50,
    ),
    # Deadlift
    "ex_deadlift": ExerciseHeuristicConfig(
        exercise_id="ex_deadlift",
        rom_target_angle=165.0,  # Standing lockout: >= 165° hip angle
        rom_acceptable_tolerance=5.0,
        alignment_thresholds={
            "max_early_hip_lead_delta": 15.0, # Hip rise leading knee extension
            "max_torso_setup_angle": 55.0,     # Trunk angle from horizontal at setup
            "max_body_center_drift": 0.08,     # Normalized landmark centroid shift
        },
        max_symmetry_difference_degrees=12.0,
        max_stability_std_dev=6.0,
        min_stability_history_frames=3,
        min_confidence_threshold=0.50,
    ),
    # Bicep Curl
    "ex_bicep_curl": ExerciseHeuristicConfig(
        exercise_id="ex_bicep_curl",
        rom_target_angle=55.0,  # Peak contraction: <= 55° elbow angle
        rom_acceptable_tolerance=5.0,
        alignment_thresholds={
            "max_upper_arm_drift": 0.08,   # Anterior elbow displacement relative to torso
            "max_torso_sway_degrees": 12.0, # Torso backward lean
        },
        max_symmetry_difference_degrees=12.0,
        max_stability_std_dev=6.0,
        min_stability_history_frames=3,
        min_confidence_threshold=0.50,
    ),
    # Shoulder Press
    "ex_shoulder_press": ExerciseHeuristicConfig(
        exercise_id="ex_shoulder_press",
        rom_target_angle=165.0,  # Overhead lockout: >= 165° elbow angle
        rom_acceptable_tolerance=5.0,
        alignment_thresholds={
            "max_forearm_tilt_degrees": 15.0, # Forearm deviation from vertical
            "max_torso_backward_lean": 18.0,  # Lumbar hyperextension proxy
        },
        max_symmetry_difference_degrees=12.0,
        max_stability_std_dev=6.0,
        min_stability_history_frames=3,
        min_confidence_threshold=0.50,
    ),
}

# Exercise Canonical Aliases
HEURISTIC_EXERCISE_ALIASES: Dict[str, str] = {
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


# =============================================================================
# NUMERICAL UTILITIES & SANITIZATION
# =============================================================================

def _is_valid_number(val: Any) -> bool:
    """Returns True if value is a finite, non-NaN real number."""
    if val is None:
        return False
    try:
        f = float(val)
        return not (math.isnan(f) or math.isinf(f))
    except (ValueError, TypeError):
        return False


def _get_metric(obs: Any, key: str) -> Optional[float]:
    """
    Safely extracts float metric from KinematicObservation, dict, or object.
    Returns:
      - float: if key is present and is a finite number
      - float('nan'): if key is present but value is NaN, Inf, or invalid
      - None: if key is absent from the observation
    """
    if obs is None:
        return None

    raw_val = None
    found = False

    if hasattr(obs, "joint_angles") and isinstance(obs.joint_angles, dict):
        if key in obs.joint_angles:
            raw_val = obs.joint_angles[key]
            found = True
    elif isinstance(obs, dict):
        if "joint_angles" in obs and isinstance(obs["joint_angles"], dict) and key in obs["joint_angles"]:
            raw_val = obs["joint_angles"][key]
            found = True
        elif key in obs:
            raw_val = obs[key]
            found = True
    elif hasattr(obs, key):
        raw_val = getattr(obs, key)
        found = True

    if not found or raw_val is None:
        return None

    try:
        f = float(raw_val)
        if math.isnan(f) or math.isinf(f):
            return float("nan")
        return f
    except (ValueError, TypeError):
        return float("nan")



def _get_confidence(obs: Any) -> float:
    """Extracts confidence float from observation (defaults to 0.0 if missing)."""
    if obs is None:
        return 0.0
    if hasattr(obs, "confidence") and _is_valid_number(obs.confidence):
        return float(obs.confidence)
    if isinstance(obs, dict) and "confidence" in obs and _is_valid_number(obs["confidence"]):
        return float(obs["confidence"])
    return 1.0  # Default to 1.0 if not specified


def _get_timestamp(obs: Any) -> float:
    """Extracts timestamp_ms float from observation (defaults to 0.0)."""
    if obs is None:
        return 0.0
    if hasattr(obs, "timestamp_ms") and _is_valid_number(obs.timestamp_ms):
        return float(obs.timestamp_ms)
    if isinstance(obs, dict) and "timestamp_ms" in obs and _is_valid_number(obs["timestamp_ms"]):
        return float(obs["timestamp_ms"])
    return 0.0


# =============================================================================
# FORM HEURISTICS SERVICE
# =============================================================================

class FormHeuristicsService:
    """
    Deterministic domain service evaluating exercise form heuristics.
    Strictly stateless per evaluation call; consumes an observation and optional
    recent bounded history.
    """

    def __init__(self, configs: Optional[Dict[str, ExerciseHeuristicConfig]] = None):
        self.configs = configs or STANDARD_HEURISTIC_CONFIGS

    def get_config(self, exercise_id: str) -> ExerciseHeuristicConfig:
        clean_key = exercise_id.strip().lower()
        canonical = HEURISTIC_EXERCISE_ALIASES.get(clean_key)
        if not canonical or canonical not in self.configs:
            supported = list(self.configs.keys())
            raise ValueError(f"Unsupported exercise '{exercise_id}'. Supported: {supported}.")
        return self.configs[canonical]

    def evaluate(
        self,
        exercise_id: str,
        observation: Any,
        history: Optional[List[Any]] = None,
    ) -> ExerciseFormReport:
        """
        Evaluates all applicable form heuristics for the given exercise.
        
        Args:
            exercise_id: Canonical ID (e.g. 'ex_squat') or alias ('squat').
            observation: Current KinematicObservation or dict of joint angles.
            history: Optional list of recent sequential observations (bounded, e.g. 5-10 frames).
        
        Returns:
            ExerciseFormReport containing individual FormHeuristicResult items and observability metrics.
        """
        config = self.get_config(exercise_id)
        canon_id = config.exercise_id
        timestamp_ms = _get_timestamp(observation)
        conf = _get_confidence(observation)

        results: List[FormHeuristicResult] = []

        # Validate observation sanity
        if observation is None:
            return self._build_empty_report(canon_id, timestamp_ms, "Observation was None.")

        # Route to exercise-specific evaluator
        if canon_id == "ex_squat":
            results = self._evaluate_squat(config, observation, history)
        elif canon_id == "ex_bench_press":
            results = self._evaluate_bench(config, observation, history)
        elif canon_id == "ex_deadlift":
            results = self._evaluate_deadlift(config, observation, history)
        elif canon_id == "ex_bicep_curl":
            results = self._evaluate_bicep_curl(config, observation, history)
        elif canon_id == "ex_shoulder_press":
            results = self._evaluate_shoulder_press(config, observation, history)

        # Compute Observability Metrics
        total_required = len(results)
        observable_count = sum(1 for r in results if r.status == ObservabilityStatus.OBSERVED)
        ratio = (observable_count / total_required) if total_required > 0 else 0.0
        is_sufficiently_observable = ratio >= 0.70

        return ExerciseFormReport(
            exercise_id=canon_id,
            timestamp_ms=timestamp_ms,
            results=results,
            observable_count=observable_count,
            total_required_count=total_required,
            observability_ratio=ratio,
            is_sufficiently_observable=is_sufficiently_observable,
        )

    # -------------------------------------------------------------------------
    # SQUAT HEURISTICS
    # -------------------------------------------------------------------------
    def _evaluate_squat(
        self,
        config: ExerciseHeuristicConfig,
        obs: Any,
        history: Optional[List[Any]],
    ) -> List[FormHeuristicResult]:
        res: List[FormHeuristicResult] = []
        conf = _get_confidence(obs)
        t = _get_timestamp(obs)

        # 1. ROM: Knee Flexion Depth (<= 95° parallel threshold)
        lknee = _get_metric(obs, "left_knee")
        rknee = _get_metric(obs, "right_knee")
        depth_angle = None
        if lknee is not None and rknee is not None:
            depth_angle = min(lknee, rknee)  # Deepest knee
        elif lknee is not None:
            depth_angle = lknee
        elif rknee is not None:
            depth_angle = rknee

        res.append(self._check_angle_rom(
            exercise_id=config.exercise_id,
            heuristic_name="squat_depth",
            observed_angle=depth_angle,
            target_threshold=config.rom_target_angle,
            is_maximum_threshold=True,  # Lower is deeper
            conf=conf,
            t=t,
            min_conf=config.min_confidence_threshold,
            acceptable_feedback="Knee flexion reached parallel depth threshold.",
            deficit_feedback="Knee flexion did not reach the configured parallel depth threshold.",
        ))

        # 2. Technique: Torso Forward Inclination (<= 45° from vertical)
        torso_angle = _get_metric(obs, "torso_angle")
        max_torso = config.alignment_thresholds.get("max_torso_inclination", 45.0)
        res.append(self._check_max_bound_heuristic(
            exercise_id=config.exercise_id,
            heuristic_name="squat_torso_inclination",
            category=HeuristicCategory.TECHNIQUE,
            observed_value=torso_angle,
            max_threshold=max_torso,
            conf=conf,
            t=t,
            min_conf=config.min_confidence_threshold,
            acceptable_feedback="Torso inclination is within the reference range.",
            violation_feedback="Torso forward inclination exceeded the configured reference threshold.",
        ))

        # 3. Technique: Knee Tracking (>= 0.75 inter-knee / inter-ankle width ratio)
        knee_tracking_ratio = _get_metric(obs, "knee_tracking_ratio")
        min_tracking = config.alignment_thresholds.get("min_knee_tracking_ratio", 0.75)
        res.append(self._check_min_bound_heuristic(
            exercise_id=config.exercise_id,
            heuristic_name="squat_knee_tracking",
            category=HeuristicCategory.TECHNIQUE,
            observed_value=knee_tracking_ratio,
            min_threshold=min_tracking,
            conf=conf,
            t=t,
            min_conf=config.min_confidence_threshold,
            unit="ratio",
            acceptable_feedback="Knee tracking ratio satisfies the alignment threshold.",
            violation_feedback="Knee alignment deviation observed relative to ankle width.",
        ))

        # 4. Symmetry: Bilateral Knee Flexion Difference (<= 12°)
        res.append(self._check_bilateral_symmetry(
            exercise_id=config.exercise_id,
            heuristic_name="squat_knee_symmetry",
            left_val=lknee,
            right_val=rknee,
            max_diff=config.max_symmetry_difference_degrees,
            conf=conf,
            t=t,
            min_conf=config.min_confidence_threshold,
            acceptable_feedback="Bilateral knee angle symmetry is within the configured tolerance.",
            violation_feedback="Bilateral knee angle asymmetry exceeded the configured tolerance.",
        ))

        # 5. Stability: Movement stability across recent window
        res.append(self._check_window_stability(
            exercise_id=config.exercise_id,
            heuristic_name="squat_movement_stability",
            metric_key="left_knee",
            current_obs=obs,
            history=history,
            max_std=config.max_stability_std_dev,
            min_frames=config.min_stability_history_frames,
            conf=conf,
            t=t,
        ))

        return res

    # -------------------------------------------------------------------------
    # BENCH PRESS HEURISTICS
    # -------------------------------------------------------------------------
    def _evaluate_bench(
        self,
        config: ExerciseHeuristicConfig,
        obs: Any,
        history: Optional[List[Any]],
    ) -> List[FormHeuristicResult]:
        res: List[FormHeuristicResult] = []
        conf = _get_confidence(obs)
        t = _get_timestamp(obs)

        # 1. ROM: Elbow Flexion Pressing Depth (<= 90° at bottom)
        lelbow = _get_metric(obs, "left_elbow")
        relbow = _get_metric(obs, "right_elbow")
        depth_angle = None
        if lelbow is not None and relbow is not None:
            depth_angle = min(lelbow, relbow)
        elif lelbow is not None:
            depth_angle = lelbow
        elif relbow is not None:
            depth_angle = relbow

        res.append(self._check_angle_rom(
            exercise_id=config.exercise_id,
            heuristic_name="bench_elbow_rom",
            observed_angle=depth_angle,
            target_threshold=config.rom_target_angle,
            is_maximum_threshold=True,  # Lower angle is deeper
            conf=conf,
            t=t,
            min_conf=config.min_confidence_threshold,
            acceptable_feedback="Elbow flexion reached bottom chest touch threshold.",
            deficit_feedback="Elbow flexion did not reach the configured bottom threshold.",
        ))

        # 2. Technique: Elbow Flare Angle (35° <= flare <= 75°)
        elbow_flare = _get_metric(obs, "elbow_flare")
        min_flare = config.alignment_thresholds.get("elbow_flare_min", 35.0)
        max_flare = config.alignment_thresholds.get("elbow_flare_max", 75.0)
        res.append(self._check_range_bound_heuristic(
            exercise_id=config.exercise_id,
            heuristic_name="bench_elbow_flare",
            category=HeuristicCategory.TECHNIQUE,
            observed_value=elbow_flare,
            lower_bound=min_flare,
            upper_bound=max_flare,
            conf=conf,
            t=t,
            min_conf=config.min_confidence_threshold,
            acceptable_feedback="Elbow flare angle is within the reference range.",
            violation_feedback="Elbow flare angle exceeded the configured reference threshold.",
        ))

        # 3. Symmetry: Bilateral Elbow Pressing Symmetry (<= 12°)
        res.append(self._check_bilateral_symmetry(
            exercise_id=config.exercise_id,
            heuristic_name="bench_elbow_symmetry",
            left_val=lelbow,
            right_val=relbow,
            max_diff=config.max_symmetry_difference_degrees,
            conf=conf,
            t=t,
            min_conf=config.min_confidence_threshold,
            acceptable_feedback="Bilateral elbow pressing symmetry is within the configured tolerance.",
            violation_feedback="Bilateral elbow pressing asymmetry exceeded the configured tolerance.",
        ))

        # 4. Stability: Pressing stability across recent window
        res.append(self._check_window_stability(
            exercise_id=config.exercise_id,
            heuristic_name="bench_movement_stability",
            metric_key="left_elbow",
            current_obs=obs,
            history=history,
            max_std=config.max_stability_std_dev,
            min_frames=config.min_stability_history_frames,
            conf=conf,
            t=t,
        ))

        return res

    # -------------------------------------------------------------------------
    # DEADLIFT HEURISTICS
    # -------------------------------------------------------------------------
    def _evaluate_deadlift(
        self,
        config: ExerciseHeuristicConfig,
        obs: Any,
        history: Optional[List[Any]],
    ) -> List[FormHeuristicResult]:
        res: List[FormHeuristicResult] = []
        conf = _get_confidence(obs)
        t = _get_timestamp(obs)

        # 1. ROM: Standing Hip Lockout (>= 165°)
        lhip = _get_metric(obs, "left_hip")
        rhip = _get_metric(obs, "right_hip")
        hip_lockout = None
        if lhip is not None and rhip is not None:
            hip_lockout = max(lhip, rhip)
        elif lhip is not None:
            hip_lockout = lhip
        elif rhip is not None:
            hip_lockout = rhip

        res.append(self._check_angle_rom(
            exercise_id=config.exercise_id,
            heuristic_name="deadlift_hip_lockout",
            observed_angle=hip_lockout,
            target_threshold=config.rom_target_angle,
            is_maximum_threshold=False,  # Greater angle is more locked out
            conf=conf,
            t=t,
            min_conf=config.min_confidence_threshold,
            acceptable_feedback="Hip extension reached the standing lockout threshold.",
            deficit_feedback="Hip extension did not reach the configured lockout threshold.",
        ))

        # 2. Technique: Hip/Knee Sequencing
        # If hip extends much faster than knee during the pull, hips rise early.
        res.append(self._check_deadlift_sequencing(
            exercise_id=config.exercise_id,
            current_obs=obs,
            history=history,
            conf=conf,
            t=t,
            min_conf=config.min_confidence_threshold,
        ))

        # 3. Technique: Torso Angle at setup (<= 55° from horizontal)
        torso_angle = _get_metric(obs, "torso_angle")
        max_torso = config.alignment_thresholds.get("max_torso_setup_angle", 55.0)
        res.append(self._check_max_bound_heuristic(
            exercise_id=config.exercise_id,
            heuristic_name="deadlift_torso_angle",
            category=HeuristicCategory.TECHNIQUE,
            observed_value=torso_angle,
            max_threshold=max_torso,
            conf=conf,
            t=t,
            min_conf=config.min_confidence_threshold,
            acceptable_feedback="Torso setup inclination is within the reference range.",
            violation_feedback="Torso inclination deviation observed during pull.",
        ))

        # 4. Technique: Estimated Body-Center Stability (drift <= 0.08 normalized units)
        body_center_drift = _get_metric(obs, "body_center_drift")
        max_drift = config.alignment_thresholds.get("max_body_center_drift", 0.08)
        res.append(self._check_max_bound_heuristic(
            exercise_id=config.exercise_id,
            heuristic_name="deadlift_body_center_stability",
            category=HeuristicCategory.TECHNIQUE,
            observed_value=body_center_drift,
            max_threshold=max_drift,
            conf=conf,
            t=t,
            min_conf=config.min_confidence_threshold,
            unit="norm_units",
            acceptable_feedback="Estimated body-center trajectory is stable.",
            violation_feedback="Estimated body center shifted horizontally during pull.",
        ))

        # 5. Symmetry: Bilateral Hip Symmetry (<= 12°)
        res.append(self._check_bilateral_symmetry(
            exercise_id=config.exercise_id,
            heuristic_name="deadlift_hip_symmetry",
            left_val=lhip,
            right_val=rhip,
            max_diff=config.max_symmetry_difference_degrees,
            conf=conf,
            t=t,
            min_conf=config.min_confidence_threshold,
            acceptable_feedback="Bilateral hip extension symmetry is within the configured tolerance.",
            violation_feedback="Bilateral hip extension asymmetry exceeded the configured tolerance.",
        ))

        # 6. Stability: Movement stability across recent window
        res.append(self._check_window_stability(
            exercise_id=config.exercise_id,
            heuristic_name="deadlift_movement_stability",
            metric_key="left_hip",
            current_obs=obs,
            history=history,
            max_std=config.max_stability_std_dev,
            min_frames=config.min_stability_history_frames,
            conf=conf,
            t=t,
        ))

        return res

    # -------------------------------------------------------------------------
    # BICEP CURL HEURISTICS
    # -------------------------------------------------------------------------
    def _evaluate_bicep_curl(
        self,
        config: ExerciseHeuristicConfig,
        obs: Any,
        history: Optional[List[Any]],
    ) -> List[FormHeuristicResult]:
        res: List[FormHeuristicResult] = []
        conf = _get_confidence(obs)
        t = _get_timestamp(obs)

        # 1. ROM: Peak Elbow Flexion (<= 55°)
        lelbow = _get_metric(obs, "left_elbow")
        relbow = _get_metric(obs, "right_elbow")
        flex_angle = None
        if lelbow is not None and relbow is not None:
            flex_angle = min(lelbow, relbow)
        elif lelbow is not None:
            flex_angle = lelbow
        elif relbow is not None:
            flex_angle = relbow

        res.append(self._check_angle_rom(
            exercise_id=config.exercise_id,
            heuristic_name="curl_elbow_rom",
            observed_angle=flex_angle,
            target_threshold=config.rom_target_angle,
            is_maximum_threshold=True,  # Lower angle is greater flexion
            conf=conf,
            t=t,
            min_conf=config.min_confidence_threshold,
            acceptable_feedback="Elbow flexion reached the peak contraction threshold.",
            deficit_feedback="Elbow flexion did not reach the configured peak contraction threshold.",
        ))

        # 2. Technique: Upper-Arm Anterior Drift (<= 0.08 normalized units)
        upper_arm_drift = _get_metric(obs, "upper_arm_drift")
        max_drift = config.alignment_thresholds.get("max_upper_arm_drift", 0.08)
        res.append(self._check_max_bound_heuristic(
            exercise_id=config.exercise_id,
            heuristic_name="curl_upper_arm_drift",
            category=HeuristicCategory.TECHNIQUE,
            observed_value=upper_arm_drift,
            max_threshold=max_drift,
            conf=conf,
            t=t,
            min_conf=config.min_confidence_threshold,
            unit="norm_units",
            acceptable_feedback="Upper-arm position remained stable throughout curl.",
            violation_feedback="Upper-arm anterior drift exceeded the reference tolerance.",
        ))

        # 3. Technique: Torso Sway / Momentum (<= 12°)
        torso_sway = _get_metric(obs, "torso_sway")
        max_sway = config.alignment_thresholds.get("max_torso_sway_degrees", 12.0)
        res.append(self._check_max_bound_heuristic(
            exercise_id=config.exercise_id,
            heuristic_name="curl_torso_momentum",
            category=HeuristicCategory.TECHNIQUE,
            observed_value=torso_sway,
            max_threshold=max_sway,
            conf=conf,
            t=t,
            min_conf=config.min_confidence_threshold,
            acceptable_feedback="Torso inclination remained stable without excessive sway.",
            violation_feedback="Torso backward lean indicates body momentum compensation.",
        ))

        # 4. Symmetry: Bilateral Elbow Curl Symmetry (<= 12°)
        res.append(self._check_bilateral_symmetry(
            exercise_id=config.exercise_id,
            heuristic_name="curl_elbow_symmetry",
            left_val=lelbow,
            right_val=relbow,
            max_diff=config.max_symmetry_difference_degrees,
            conf=conf,
            t=t,
            min_conf=config.min_confidence_threshold,
            acceptable_feedback="Bilateral curl symmetry is within the configured tolerance.",
            violation_feedback="Bilateral curl asymmetry exceeded the configured tolerance.",
        ))

        # 5. Stability: Movement stability across recent window
        res.append(self._check_window_stability(
            exercise_id=config.exercise_id,
            heuristic_name="curl_movement_stability",
            metric_key="left_elbow",
            current_obs=obs,
            history=history,
            max_std=config.max_stability_std_dev,
            min_frames=config.min_stability_history_frames,
            conf=conf,
            t=t,
        ))

        return res

    # -------------------------------------------------------------------------
    # SHOULDER PRESS HEURISTICS
    # -------------------------------------------------------------------------
    def _evaluate_shoulder_press(
        self,
        config: ExerciseHeuristicConfig,
        obs: Any,
        history: Optional[List[Any]],
    ) -> List[FormHeuristicResult]:
        res: List[FormHeuristicResult] = []
        conf = _get_confidence(obs)
        t = _get_timestamp(obs)

        # 1. ROM: Overhead Lockout (>= 165°)
        lelbow = _get_metric(obs, "left_elbow")
        relbow = _get_metric(obs, "right_elbow")
        lockout_angle = None
        if lelbow is not None and relbow is not None:
            lockout_angle = max(lelbow, relbow)
        elif lelbow is not None:
            lockout_angle = lelbow
        elif relbow is not None:
            lockout_angle = relbow

        res.append(self._check_angle_rom(
            exercise_id=config.exercise_id,
            heuristic_name="shoulder_press_lockout",
            observed_angle=lockout_angle,
            target_threshold=config.rom_target_angle,
            is_maximum_threshold=False,  # Higher angle is more locked out
            conf=conf,
            t=t,
            min_conf=config.min_confidence_threshold,
            acceptable_feedback="Overhead elbow extension reached the lockout threshold.",
            deficit_feedback="Overhead elbow extension did not reach the configured lockout threshold.",
        ))

        # 2. Technique: Forearm Verticality (deviation <= 15°)
        forearm_tilt = _get_metric(obs, "forearm_tilt")
        max_tilt = config.alignment_thresholds.get("max_forearm_tilt_degrees", 15.0)
        res.append(self._check_max_bound_heuristic(
            exercise_id=config.exercise_id,
            heuristic_name="shoulder_press_forearm_verticality",
            category=HeuristicCategory.TECHNIQUE,
            observed_value=forearm_tilt,
            max_threshold=max_tilt,
            conf=conf,
            t=t,
            min_conf=config.min_confidence_threshold,
            acceptable_feedback="Forearm verticality is within the reference range.",
            violation_feedback="Forearm tilt exceeded the configured verticality reference.",
        ))

        # 3. Technique: Torso Backward Lean / Arch (<= 18°)
        torso_lean = _get_metric(obs, "torso_lean")
        max_lean = config.alignment_thresholds.get("max_torso_backward_lean", 18.0)
        res.append(self._check_max_bound_heuristic(
            exercise_id=config.exercise_id,
            heuristic_name="shoulder_press_torso_lean",
            category=HeuristicCategory.TECHNIQUE,
            observed_value=torso_lean,
            max_threshold=max_lean,
            conf=conf,
            t=t,
            min_conf=config.min_confidence_threshold,
            acceptable_feedback="Torso inclination remained neutral throughout press.",
            violation_feedback="Torso backward lean exceeded the reference threshold.",
        ))

        # 4. Symmetry: Bilateral Press Symmetry (<= 12°)
        res.append(self._check_bilateral_symmetry(
            exercise_id=config.exercise_id,
            heuristic_name="shoulder_press_elbow_symmetry",
            left_val=lelbow,
            right_val=relbow,
            max_diff=config.max_symmetry_difference_degrees,
            conf=conf,
            t=t,
            min_conf=config.min_confidence_threshold,
            acceptable_feedback="Bilateral pressing symmetry is within the configured tolerance.",
            violation_feedback="Bilateral pressing asymmetry exceeded the configured tolerance.",
        ))

        # 5. Stability: Pressing stability across recent window
        res.append(self._check_window_stability(
            exercise_id=config.exercise_id,
            heuristic_name="shoulder_press_movement_stability",
            metric_key="left_elbow",
            current_obs=obs,
            history=history,
            max_std=config.max_stability_std_dev,
            min_frames=config.min_stability_history_frames,
            conf=conf,
            t=t,
        ))

        return res

    # =========================================================================
    # REUSABLE DETERMINISTIC EVALUATION CHECKERS
    # =========================================================================

    def _check_angle_rom(
        self,
        exercise_id: str,
        heuristic_name: str,
        observed_angle: Optional[float],
        target_threshold: float,
        is_maximum_threshold: bool,
        conf: float,
        t: float,
        min_conf: float,
        acceptable_feedback: str,
        deficit_feedback: str,
    ) -> FormHeuristicResult:
        """Evaluates single-joint ROM threshold."""
        if observed_angle is None:
            return FormHeuristicResult(
                exercise_id=exercise_id,
                category=HeuristicCategory.ROM,
                heuristic_name=heuristic_name,
                status=ObservabilityStatus.NOT_OBSERVABLE,
                feedback="Required joint angle not observable.",
                timestamp_ms=t,
            )

        # Sanity check range [0.0, 180.0]
        if not _is_valid_number(observed_angle) or not (0.0 <= observed_angle <= 180.0):
            return FormHeuristicResult(
                exercise_id=exercise_id,
                category=HeuristicCategory.ROM,
                heuristic_name=heuristic_name,
                status=ObservabilityStatus.INVALID,
                observed_value=observed_angle if _is_valid_number(observed_angle) else None,
                feedback=f"Invalid joint angle value: {observed_angle}.",
                timestamp_ms=t,
            )

        if conf < min_conf:
            return FormHeuristicResult(
                exercise_id=exercise_id,
                category=HeuristicCategory.ROM,
                heuristic_name=heuristic_name,
                status=ObservabilityStatus.INSUFFICIENT_CONFIDENCE,
                confidence=conf,
                feedback="Tracking confidence too low to evaluate ROM.",
                timestamp_ms=t,
            )

        # Evaluated
        if is_maximum_threshold:
            # Lower is better (e.g. squat depth <= 95°)
            is_acc = observed_angle <= target_threshold
            dev = round(max(0.0, observed_angle - target_threshold), 4)
        else:
            # Higher is better (e.g. overhead lockout >= 165°)
            is_acc = observed_angle >= target_threshold
            dev = round(max(0.0, target_threshold - observed_angle), 4)

        fb = acceptable_feedback if is_acc else f"{deficit_feedback} (Observed: {observed_angle:.1f}° vs Target: {target_threshold:.1f}°)"

        return FormHeuristicResult(
            exercise_id=exercise_id,
            category=HeuristicCategory.ROM,
            heuristic_name=heuristic_name,
            status=ObservabilityStatus.OBSERVED,
            is_acceptable=is_acc,
            observed_value=observed_angle,
            reference_value=target_threshold,
            deviation=dev,
            confidence=conf,
            feedback=fb,
            timestamp_ms=t,
        )

    def _check_max_bound_heuristic(
        self,
        exercise_id: str,
        heuristic_name: str,
        category: HeuristicCategory,
        observed_value: Optional[float],
        max_threshold: float,
        conf: float,
        t: float,
        min_conf: float,
        acceptable_feedback: str,
        violation_feedback: str,
        unit: str = "degrees",
    ) -> FormHeuristicResult:
        """Evaluates an upper-bounded scalar metric (e.g. torso lean <= 45°)."""
        if observed_value is None:
            return FormHeuristicResult(
                exercise_id=exercise_id,
                category=category,
                heuristic_name=heuristic_name,
                status=ObservabilityStatus.NOT_OBSERVABLE,
                unit=unit,
                feedback="Metric not observable from current camera view.",
                timestamp_ms=t,
            )

        if not _is_valid_number(observed_value):
            return FormHeuristicResult(
                exercise_id=exercise_id,
                category=category,
                heuristic_name=heuristic_name,
                status=ObservabilityStatus.INVALID,
                unit=unit,
                feedback="Invalid non-numeric value.",
                timestamp_ms=t,
            )

        if conf < min_conf:
            return FormHeuristicResult(
                exercise_id=exercise_id,
                category=category,
                heuristic_name=heuristic_name,
                status=ObservabilityStatus.INSUFFICIENT_CONFIDENCE,
                confidence=conf,
                unit=unit,
                feedback="Tracking confidence too low to evaluate metric.",
                timestamp_ms=t,
            )

        is_acc = observed_value <= max_threshold
        dev = round(max(0.0, observed_value - max_threshold), 4)
        fb = acceptable_feedback if is_acc else f"{violation_feedback} (Observed: {observed_value:.1f} vs Max: {max_threshold:.1f})"

        return FormHeuristicResult(
            exercise_id=exercise_id,
            category=category,
            heuristic_name=heuristic_name,
            status=ObservabilityStatus.OBSERVED,
            is_acceptable=is_acc,
            observed_value=observed_value,
            reference_value=max_threshold,
            deviation=dev,
            confidence=conf,
            feedback=fb,
            unit=unit,
            timestamp_ms=t,
        )

    def _check_min_bound_heuristic(
        self,
        exercise_id: str,
        heuristic_name: str,
        category: HeuristicCategory,
        observed_value: Optional[float],
        min_threshold: float,
        conf: float,
        t: float,
        min_conf: float,
        acceptable_feedback: str,
        violation_feedback: str,
        unit: str = "ratio",
    ) -> FormHeuristicResult:
        """Evaluates a lower-bounded scalar metric (e.g. knee tracking ratio >= 0.75)."""
        if observed_value is None:
            return FormHeuristicResult(
                exercise_id=exercise_id,
                category=category,
                heuristic_name=heuristic_name,
                status=ObservabilityStatus.NOT_OBSERVABLE,
                unit=unit,
                feedback="Metric not observable from current camera view.",
                timestamp_ms=t,
            )

        if not _is_valid_number(observed_value):
            return FormHeuristicResult(
                exercise_id=exercise_id,
                category=category,
                heuristic_name=heuristic_name,
                status=ObservabilityStatus.INVALID,
                unit=unit,
                feedback="Invalid non-numeric value.",
                timestamp_ms=t,
            )

        if conf < min_conf:
            return FormHeuristicResult(
                exercise_id=exercise_id,
                category=category,
                heuristic_name=heuristic_name,
                status=ObservabilityStatus.INSUFFICIENT_CONFIDENCE,
                confidence=conf,
                unit=unit,
                feedback="Tracking confidence too low to evaluate metric.",
                timestamp_ms=t,
            )

        is_acc = observed_value >= min_threshold
        dev = round(max(0.0, min_threshold - observed_value), 4)
        fb = acceptable_feedback if is_acc else f"{violation_feedback} (Observed: {observed_value:.2f} vs Min: {min_threshold:.2f})"

        return FormHeuristicResult(
            exercise_id=exercise_id,
            category=category,
            heuristic_name=heuristic_name,
            status=ObservabilityStatus.OBSERVED,
            is_acceptable=is_acc,
            observed_value=observed_value,
            reference_value=min_threshold,
            deviation=dev,
            confidence=conf,
            feedback=fb,
            unit=unit,
            timestamp_ms=t,
        )

    def _check_range_bound_heuristic(
        self,
        exercise_id: str,
        heuristic_name: str,
        category: HeuristicCategory,
        observed_value: Optional[float],
        lower_bound: float,
        upper_bound: float,
        conf: float,
        t: float,
        min_conf: float,
        acceptable_feedback: str,
        violation_feedback: str,
        unit: str = "degrees",
    ) -> FormHeuristicResult:
        """Evaluates a metric bounded by an interval [lower, upper] (e.g. elbow flare 35°-75°)."""
        if observed_value is None:
            return FormHeuristicResult(
                exercise_id=exercise_id,
                category=category,
                heuristic_name=heuristic_name,
                status=ObservabilityStatus.NOT_OBSERVABLE,
                unit=unit,
                feedback="Metric not observable from current camera view.",
                timestamp_ms=t,
            )

        if not _is_valid_number(observed_value):
            return FormHeuristicResult(
                exercise_id=exercise_id,
                category=category,
                heuristic_name=heuristic_name,
                status=ObservabilityStatus.INVALID,
                unit=unit,
                feedback="Invalid non-numeric value.",
                timestamp_ms=t,
            )

        if conf < min_conf:
            return FormHeuristicResult(
                exercise_id=exercise_id,
                category=category,
                heuristic_name=heuristic_name,
                status=ObservabilityStatus.INSUFFICIENT_CONFIDENCE,
                confidence=conf,
                unit=unit,
                feedback="Tracking confidence too low to evaluate metric.",
                timestamp_ms=t,
            )

        is_acc = (lower_bound <= observed_value <= upper_bound)
        if observed_value < lower_bound:
            dev = round(lower_bound - observed_value, 4)
        elif observed_value > upper_bound:
            dev = round(observed_value - upper_bound, 4)
        else:
            dev = 0.0

        fb = acceptable_feedback if is_acc else f"{violation_feedback} (Observed: {observed_value:.1f}° vs [{lower_bound:.1f}°, {upper_bound:.1f}°])"

        return FormHeuristicResult(
            exercise_id=exercise_id,
            category=category,
            heuristic_name=heuristic_name,
            status=ObservabilityStatus.OBSERVED,
            is_acceptable=is_acc,
            observed_value=observed_value,
            reference_value=[lower_bound, upper_bound],
            deviation=dev,
            confidence=conf,
            feedback=fb,
            unit=unit,
            timestamp_ms=t,
        )

    def _check_bilateral_symmetry(
        self,
        exercise_id: str,
        heuristic_name: str,
        left_val: Optional[float],
        right_val: Optional[float],
        max_diff: float,
        conf: float,
        t: float,
        min_conf: float,
        acceptable_feedback: str,
        violation_feedback: str,
    ) -> FormHeuristicResult:
        """
        Evaluates symmetry between bilateral joints.
        CRITICAL: If only one side is observable, returns NOT_OBSERVABLE, NEVER bad symmetry.
        """
        # Check if either value is invalid/NaN
        if (left_val is not None and not _is_valid_number(left_val)) or (right_val is not None and not _is_valid_number(right_val)):
            return FormHeuristicResult(
                exercise_id=exercise_id,
                category=HeuristicCategory.SYMMETRY,
                heuristic_name=heuristic_name,
                status=ObservabilityStatus.INVALID,
                feedback="Invalid non-numeric value in bilateral measurement.",
                timestamp_ms=t,
            )

        if left_val is None or right_val is None:
            return FormHeuristicResult(
                exercise_id=exercise_id,
                category=HeuristicCategory.SYMMETRY,
                heuristic_name=heuristic_name,
                status=ObservabilityStatus.NOT_OBSERVABLE,
                feedback="Bilateral landmarks not both observable; symmetry cannot be evaluated.",
                timestamp_ms=t,
            )

        if conf < min_conf:
            return FormHeuristicResult(
                exercise_id=exercise_id,
                category=HeuristicCategory.SYMMETRY,
                heuristic_name=heuristic_name,
                status=ObservabilityStatus.INSUFFICIENT_CONFIDENCE,
                confidence=conf,
                feedback="Tracking confidence too low to evaluate symmetry.",
                timestamp_ms=t,
            )

        diff = abs(left_val - right_val)
        is_acc = diff <= max_diff
        dev = round(max(0.0, diff - max_diff), 4)

        fb = acceptable_feedback if is_acc else f"{violation_feedback} (Difference: {diff:.1f}° vs Max: {max_diff:.1f}°)"

        return FormHeuristicResult(
            exercise_id=exercise_id,
            category=HeuristicCategory.SYMMETRY,
            heuristic_name=heuristic_name,
            status=ObservabilityStatus.OBSERVED,
            is_acceptable=is_acc,
            observed_value=diff,
            reference_value=max_diff,
            deviation=dev,
            confidence=conf,
            feedback=fb,
            timestamp_ms=t,
        )

    def _check_window_stability(
        self,
        exercise_id: str,
        heuristic_name: str,
        metric_key: str,
        current_obs: Any,
        history: Optional[List[Any]],
        max_std: float,
        min_frames: int,
        conf: float,
        t: float,
    ) -> FormHeuristicResult:
        """
        Evaluates frame-to-frame velocity stability over a bounded sliding window.
        A single noisy frame does not trigger a defect if overall window is stable.
        """
        # Collect window frames
        window = []
        if history:
            window.extend(history)
        if current_obs is not None:
            window.append(current_obs)

        if len(window) < min_frames:
            return FormHeuristicResult(
                exercise_id=exercise_id,
                category=HeuristicCategory.STABILITY,
                heuristic_name=heuristic_name,
                status=ObservabilityStatus.NOT_OBSERVABLE,
                feedback=f"Insufficient observation history to evaluate stability (need {min_frames} frames).",
                timestamp_ms=t,
            )

        values: List[float] = []
        for frame in window:
            val = _get_metric(frame, metric_key)
            if val is not None and _is_valid_number(val):
                values.append(val)

        if len(values) < min_frames:
            return FormHeuristicResult(
                exercise_id=exercise_id,
                category=HeuristicCategory.STABILITY,
                heuristic_name=heuristic_name,
                status=ObservabilityStatus.NOT_OBSERVABLE,
                feedback="Insufficient valid data points to compute stability.",
                timestamp_ms=t,
            )

        # Compute frame-to-frame absolute deltas (velocity jitter)
        deltas = [abs(values[i] - values[i - 1]) for i in range(1, len(values))]
        if not deltas:
            jitter = 0.0
        else:
            jitter = sum(deltas) / len(deltas)

        is_acc = jitter <= max_std
        dev = round(max(0.0, jitter - max_std), 4)

        fb = (
            "Movement stability is within normal limits across recent frames."
            if is_acc
            else f"Movement velocity jitter exceeded the stability tolerance (Jitter: {jitter:.2f}° vs Max: {max_std:.2f}°)."
        )

        return FormHeuristicResult(
            exercise_id=exercise_id,
            category=HeuristicCategory.STABILITY,
            heuristic_name=heuristic_name,
            status=ObservabilityStatus.OBSERVED,
            is_acceptable=is_acc,
            observed_value=round(jitter, 2),
            reference_value=max_std,
            deviation=dev,
            confidence=conf,
            feedback=fb,
            timestamp_ms=t,
        )

    def _check_deadlift_sequencing(
        self,
        exercise_id: str,
        current_obs: Any,
        history: Optional[List[Any]],
        conf: float,
        t: float,
        min_conf: float,
    ) -> FormHeuristicResult:
        """
        Evaluates hip vs knee extension sequencing during Deadlift pull.
        If hip extends > 20° while knee extends < 5°, flags early hip rise.
        """
        window = []
        if history:
            window.extend(history)
        if current_obs is not None:
            window.append(current_obs)

        if len(window) < 3:
            return FormHeuristicResult(
                exercise_id=exercise_id,
                category=HeuristicCategory.TECHNIQUE,
                heuristic_name="deadlift_hip_knee_sequencing",
                status=ObservabilityStatus.NOT_OBSERVABLE,
                feedback="Insufficient observation history to evaluate hip/knee sequencing.",
                timestamp_ms=t,
            )

        start_frame = window[0]
        end_frame = window[-1]

        start_hip = _get_metric(start_frame, "left_hip") or _get_metric(start_frame, "right_hip")
        end_hip = _get_metric(end_frame, "left_hip") or _get_metric(end_frame, "right_hip")
        start_knee = _get_metric(start_frame, "left_knee") or _get_metric(start_frame, "right_knee")
        end_knee = _get_metric(end_frame, "left_knee") or _get_metric(end_frame, "right_knee")

        if any(v is None for v in (start_hip, end_hip, start_knee, end_knee)):
            return FormHeuristicResult(
                exercise_id=exercise_id,
                category=HeuristicCategory.TECHNIQUE,
                heuristic_name="deadlift_hip_knee_sequencing",
                status=ObservabilityStatus.NOT_OBSERVABLE,
                feedback="Hip or knee angles missing from sequencing window.",
                timestamp_ms=t,
            )

        if conf < min_conf:
            return FormHeuristicResult(
                exercise_id=exercise_id,
                category=HeuristicCategory.TECHNIQUE,
                heuristic_name="deadlift_hip_knee_sequencing",
                status=ObservabilityStatus.INSUFFICIENT_CONFIDENCE,
                confidence=conf,
                feedback="Confidence too low to evaluate sequencing.",
                timestamp_ms=t,
            )

        hip_delta = end_hip - start_hip
        knee_delta = end_knee - start_knee

        # Check for early hip rise (hip extends while knees remain stationary/flexed)
        is_early_hip_rise = (hip_delta > 18.0) and (knee_delta < 5.0)
        is_acc = not is_early_hip_rise
        dev = max(0.0, hip_delta - (knee_delta + 15.0)) if is_early_hip_rise else 0.0

        fb = (
            "Hip and knee extension properly coordinated during pull."
            if is_acc
            else f"Early hip rise observed: hip extended {hip_delta:.1f}° while knees extended only {knee_delta:.1f}°."
        )

        return FormHeuristicResult(
            exercise_id=exercise_id,
            category=HeuristicCategory.TECHNIQUE,
            heuristic_name="deadlift_hip_knee_sequencing",
            status=ObservabilityStatus.OBSERVED,
            is_acceptable=is_acc,
            observed_value=hip_delta,
            reference_value=knee_delta,
            deviation=dev,
            confidence=conf,
            feedback=fb,
            timestamp_ms=t,
        )

    def _build_empty_report(self, exercise_id: str, timestamp_ms: float, reason: str) -> ExerciseFormReport:
        return ExerciseFormReport(
            exercise_id=exercise_id,
            timestamp_ms=timestamp_ms,
            results=[
                FormHeuristicResult(
                    exercise_id=exercise_id,
                    category=HeuristicCategory.TECHNIQUE,
                    heuristic_name="input_validation",
                    status=ObservabilityStatus.INVALID,
                    feedback=reason,
                    timestamp_ms=timestamp_ms,
                )
            ],
            observable_count=0,
            total_required_count=1,
            observability_ratio=0.0,
            is_sufficiently_observable=False,
        )
