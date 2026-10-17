"""
Geometric and Vector Mathematics Utilities for Pose & Form Analysis (Phase 9A).

Provides:
- Numerically stable 2D and 3D 3-point joint angle calculations with cosine clamping.
- Zero-division guardrails for collapsed/overlapping keypoints.
- Bounded angle outputs strictly in [0.0, 180.0] degrees.
- Euclidean distance and segment tilt calculations.
- Estimated body centroid approximation (NOT biomechanical center of mass).
- Deterministic joint confidence aggregation based on relevant evaluated keypoints.
"""

import math
from typing import Dict, Any, List, Optional, Tuple, Union


# Canonical Joint Triplet Definitions (Vertex is always index 1)
STANDARD_JOINT_DEFINITIONS: Dict[str, Tuple[str, str, str]] = {
    "left_elbow": ("LEFT_SHOULDER", "LEFT_ELBOW", "LEFT_WRIST"),
    "right_elbow": ("RIGHT_SHOULDER", "RIGHT_ELBOW", "RIGHT_WRIST"),
    "left_knee": ("LEFT_HIP", "LEFT_KNEE", "LEFT_ANKLE"),
    "right_knee": ("RIGHT_HIP", "RIGHT_KNEE", "RIGHT_ANKLE"),
    "left_hip": ("LEFT_SHOULDER", "LEFT_HIP", "LEFT_KNEE"),
    "right_hip": ("RIGHT_SHOULDER", "RIGHT_HIP", "RIGHT_KNEE"),
    "left_shoulder": ("LEFT_HIP", "LEFT_SHOULDER", "LEFT_ELBOW"),
    "right_shoulder": ("RIGHT_HIP", "RIGHT_SHOULDER", "RIGHT_ELBOW"),
}

TORSO_CENTROID_LANDMARKS: List[str] = [
    "LEFT_SHOULDER",
    "RIGHT_SHOULDER",
    "LEFT_HIP",
    "RIGHT_HIP",
]

EPSILON = 1e-7


def _get_coord(point: Union[Dict[str, Any], Any], key: str, default: float = 0.0) -> float:
    """Helper to extract float coordinate from dict or pydantic model/object."""
    if isinstance(point, dict):
        return float(point.get(key, default))
    return float(getattr(point, key, default))


def calculate_angle_2d(
    pointA: Union[Dict[str, Any], Any],
    pointB: Union[Dict[str, Any], Any],
    pointC: Union[Dict[str, Any], Any],
) -> Optional[float]:
    """
    Calculates the 2D interior angle at vertex pointB formed by rays BA and BC.
    
    Formula:
      v1 = (Ax - Bx, Ay - By)
      v2 = (Cx - Bx, Cy - By)
      cos(theta) = (v1 . v2) / (|v1| * |v2|)
      theta = arccos(clamp(cos(theta), -1.0, 1.0)) in degrees [0, 180]
      
    Returns None if vectors are degenerate (zero length) or points are invalid.
    """
    try:
        ax, ay = _get_coord(pointA, "x"), _get_coord(pointA, "y")
        bx, by = _get_coord(pointB, "x"), _get_coord(pointB, "y")
        cx, cy = _get_coord(pointC, "x"), _get_coord(pointC, "y")

        v1x, v1y = ax - bx, ay - by
        v2x, v2y = cx - bx, cy - by

        n1 = math.hypot(v1x, v1y)
        n2 = math.hypot(v2x, v2y)

        if n1 <= EPSILON or n2 <= EPSILON:
            return None

        dot = (v1x * v2x) + (v1y * v2y)
        cos_val = dot / (n1 * n2)

        # Domain clamping to avoid floating-point arccos ValueError
        cos_clamped = max(-1.0, min(1.0, cos_val))
        angle_rad = math.acos(cos_clamped)
        angle_deg = math.degrees(angle_rad)

        return round(angle_deg, 2)
    except Exception:
        return None


def calculate_angle_3d(
    pointA: Union[Dict[str, Any], Any],
    pointB: Union[Dict[str, Any], Any],
    pointC: Union[Dict[str, Any], Any],
) -> Optional[float]:
    """
    Calculates the 3D spatial angle at vertex pointB formed by rays BA and BC.
    Includes relative depth z coordinate.
    """
    try:
        ax, ay, az = _get_coord(pointA, "x"), _get_coord(pointA, "y"), _get_coord(pointA, "z", 0.0)
        bx, by, bz = _get_coord(pointB, "x"), _get_coord(pointB, "y"), _get_coord(pointB, "z", 0.0)
        cx, cy, cz = _get_coord(pointC, "x"), _get_coord(pointC, "y"), _get_coord(pointC, "z", 0.0)

        v1x, v1y, v1z = ax - bx, ay - by, az - bz
        v2x, v2y, v2z = cx - bx, cy - by, cz - bz

        n1 = math.sqrt(v1x**2 + v1y**2 + v1z**2)
        n2 = math.sqrt(v2x**2 + v2y**2 + v2z**2)

        if n1 <= EPSILON or n2 <= EPSILON:
            return None

        dot = (v1x * v2x) + (v1y * v2y) + (v1z * v2z)
        cos_val = dot / (n1 * n2)

        cos_clamped = max(-1.0, min(1.0, cos_val))
        angle_rad = math.acos(cos_clamped)
        angle_deg = math.degrees(angle_rad)

        return round(angle_deg, 2)
    except Exception:
        return None


def calculate_distance_2d(
    pointA: Union[Dict[str, Any], Any],
    pointB: Union[Dict[str, Any], Any],
) -> float:
    """Calculates 2D Euclidean distance between two landmarks."""
    ax, ay = _get_coord(pointA, "x"), _get_coord(pointA, "y")
    bx, by = _get_coord(pointB, "x"), _get_coord(pointB, "y")
    return round(math.hypot(ax - bx, ay - by), 4)


def calculate_tilt_degrees(
    pointA: Union[Dict[str, Any], Any],
    pointB: Union[Dict[str, Any], Any],
) -> float:
    """
    Calculates the angle in degrees of segment AB relative to the horizontal axis.
    Returns value in [-180.0, 180.0].
    """
    ax, ay = _get_coord(pointA, "x"), _get_coord(pointA, "y")
    bx, by = _get_coord(pointB, "x"), _get_coord(pointB, "y")
    rad = math.atan2(by - ay, bx - ax)
    return round(math.degrees(rad), 2)


def calculate_estimated_body_center(
    landmarks: Dict[str, Any]
) -> Optional[Dict[str, Any]]:
    """
    Calculates an estimated landmark centroid / body-center approximation
    from available core torso keypoints (shoulders and hips).
    
    MANDATORY GUARDRAIL:
    This is an estimated landmark centroid approximation, NOT an authoritative
    biomechanical center of mass. Do NOT use for safety-critical clinical decisions.
    """
    valid_points = []
    for name in TORSO_CENTROID_LANDMARKS:
        pt = landmarks.get(name)
        if pt:
            vis = _get_coord(pt, "visibility", 1.0)
            if vis >= 0.3:
                valid_points.append(pt)

    if not valid_points:
        return None

    total_x = sum(_get_coord(p, "x") for p in valid_points)
    total_y = sum(_get_coord(p, "y") for p in valid_points)
    total_z = sum(_get_coord(p, "z", 0.0) for p in valid_points)
    count = len(valid_points)

    return {
        "x": round(total_x / count, 4),
        "y": round(total_y / count, 4),
        "z": round(total_z / count, 4),
        "description": "Estimated landmark centroid approximation (not biomechanical center of mass)",
    }


def compute_standard_joint_angles(
    landmarks: Dict[str, Any],
    confidence_threshold: float = 0.5,
    target_joints: Optional[List[str]] = None,
    use_3d: bool = False,
) -> Tuple[Dict[str, Any], float]:
    """
    Computes biomechanical joint angles for specified or standard joint triplets.
    
    Confidence Rule (Correction #5):
    - Each joint confidence = min(confidence(pA), confidence(pB), confidence(pC)).
    - Overall confidence = deterministic mean of confidences of the requested/evaluated joints.
    """
    joints_to_eval = target_joints if target_joints else list(STANDARD_JOINT_DEFINITIONS.keys())
    results: Dict[str, Any] = {}
    joint_confidences: List[float] = []

    angle_fn = calculate_angle_3d if use_3d else calculate_angle_2d

    for joint_name in joints_to_eval:
        definition = STANDARD_JOINT_DEFINITIONS.get(joint_name)
        if not definition:
            continue

        p_name, v_name, d_name = definition
        p_pt = landmarks.get(p_name)
        v_pt = landmarks.get(v_name)
        d_pt = landmarks.get(d_name)

        if not p_pt or not v_pt or not d_pt:
            continue

        p_vis = _get_coord(p_pt, "visibility", 1.0)
        v_vis = _get_coord(v_pt, "visibility", 1.0)
        d_vis = _get_coord(d_pt, "visibility", 1.0)

        # Joint confidence is bounded by its weakest keypoint
        joint_conf = round(min(p_vis, v_vis, d_vis), 4)
        is_occluded = joint_conf < confidence_threshold

        angle = angle_fn(p_pt, v_pt, d_pt)
        if angle is not None:
            results[joint_name] = {
                "joint_name": joint_name,
                "angle_degrees": angle,
                "confidence": joint_conf,
                "vertex_landmark": v_name,
                "connected_landmarks": [p_name, d_name],
                "is_occluded": is_occluded,
            }
            joint_confidences.append(joint_conf)

    # Deterministic overall confidence derived from evaluated joints
    overall_conf = round(sum(joint_confidences) / len(joint_confidences), 4) if joint_confidences else 0.0

    return results, overall_conf
