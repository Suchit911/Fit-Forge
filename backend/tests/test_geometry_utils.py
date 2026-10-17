"""
Unit Tests for Form Analysis Geometric Mathematics Utilities (Phase 9A).

Verifies:
- 2D interior angle calculations (right angle, straight line, acute angle, zero angle).
- 3D spatial angle calculations.
- Zero-division guardrails and degenerate vectors.
- Cosine clamping for numerical stability.
- Bounded angle outputs strictly in [0.0, 180.0].
- Euclidean distance and segment tilt.
- Estimated body centroid approximation (with mandatory caveat check).
- Deterministic joint confidence rule (min keypoint visibility, overall mean of evaluated joints).
"""

import pytest
import math
from backend.app.services.geometry_utils import (
    calculate_angle_2d,
    calculate_angle_3d,
    calculate_distance_2d,
    calculate_tilt_degrees,
    calculate_estimated_body_center,
    compute_standard_joint_angles,
    STANDARD_JOINT_DEFINITIONS,
)


def test_calculate_angle_2d_right_angle():
    """Triangle (0,1) - (0,0) - (1,0) must yield exactly 90.0 degrees."""
    pA = {"x": 0.0, "y": 1.0}
    pB = {"x": 0.0, "y": 0.0}  # Vertex
    pC = {"x": 1.0, "y": 0.0}
    angle = calculate_angle_2d(pA, pB, pC)
    assert angle == 90.0


def test_calculate_angle_2d_straight_line():
    """Collinear points (-1,0) - (0,0) - (1,0) must yield 180.0 degrees."""
    pA = {"x": -1.0, "y": 0.0}
    pB = {"x": 0.0, "y": 0.0}  # Vertex
    pC = {"x": 1.0, "y": 0.0}
    angle = calculate_angle_2d(pA, pB, pC)
    assert angle == 180.0


def test_calculate_angle_2d_acute_angle():
    """(0,1) - (0,0) - (1,1) must yield 45.0 degrees."""
    pA = {"x": 0.0, "y": 1.0}
    pB = {"x": 0.0, "y": 0.0}  # Vertex
    pC = {"x": 1.0, "y": 1.0}
    angle = calculate_angle_2d(pA, pB, pC)
    assert angle == 45.0


def test_calculate_angle_2d_zero_angle():
    """Co-directional overlapping rays must yield 0.0 degrees."""
    pA = {"x": 1.0, "y": 0.0}
    pB = {"x": 0.0, "y": 0.0}  # Vertex
    pC = {"x": 2.0, "y": 0.0}
    angle = calculate_angle_2d(pA, pB, pC)
    assert angle == 0.0


def test_calculate_angle_2d_degenerate_zero_vector():
    """Overlapping points (A == B) must return None safely without ZeroDivisionError."""
    pA = {"x": 0.0, "y": 0.0}
    pB = {"x": 0.0, "y": 0.0}
    pC = {"x": 1.0, "y": 0.0}
    angle = calculate_angle_2d(pA, pB, pC)
    assert angle is None


def test_calculate_angle_2d_domain_clamping():
    """
    Simulates floating-point rounding error where dot / (n1*n2) might slightly exceed 1.0.
    Clamping must prevent ValueError: math domain error.
    """
    # Vectors with minuscule drift
    pA = {"x": 1.0000000000000002, "y": 0.0}
    pB = {"x": 0.0, "y": 0.0}
    pC = {"x": 1.0, "y": 0.0}
    angle = calculate_angle_2d(pA, pB, pC)
    assert angle is not None
    assert angle == 0.0


def test_calculate_angle_3d_spatial():
    """Verifies 3D angle calculation incorporating depth z."""
    pA = {"x": 0.0, "y": 1.0, "z": 0.0}
    pB = {"x": 0.0, "y": 0.0, "z": 0.0}
    pC = {"x": 0.0, "y": 0.0, "z": 1.0}
    angle = calculate_angle_3d(pA, pB, pC)
    assert angle == 90.0


def test_calculate_distance_2d():
    """Verifies 2D Euclidean distance calculation."""
    pA = {"x": 0.0, "y": 0.0}
    pB = {"x": 3.0, "y": 4.0}
    dist = calculate_distance_2d(pA, pB)
    assert dist == 5.0


def test_calculate_tilt_degrees():
    """Verifies segment angle relative to horizontal axis."""
    pA = {"x": 0.0, "y": 0.0}
    pB = {"x": 1.0, "y": 0.0}  # Flat horizontal
    assert calculate_tilt_degrees(pA, pB) == 0.0

    pC = {"x": 0.0, "y": 1.0}  # Vertical downward
    assert calculate_tilt_degrees(pA, pC) == 90.0


def test_calculate_estimated_body_center():
    """
    Verifies centroid calculation across torso landmarks.
    Confirms description specifies estimated approximation (Mandatory Correction #4).
    """
    landmarks = {
        "LEFT_SHOULDER": {"x": 0.40, "y": 0.20, "z": 0.0, "visibility": 0.9},
        "RIGHT_SHOULDER": {"x": 0.60, "y": 0.20, "z": 0.0, "visibility": 0.9},
        "LEFT_HIP": {"x": 0.40, "y": 0.60, "z": 0.0, "visibility": 0.9},
        "RIGHT_HIP": {"x": 0.60, "y": 0.60, "z": 0.0, "visibility": 0.9},
    }
    center = calculate_estimated_body_center(landmarks)
    assert center is not None
    assert center["x"] == 0.50
    assert center["y"] == 0.40
    assert "not biomechanical center of mass" in center["description"]


def test_compute_standard_joint_angles_confidence_propagation():
    """
    Verifies that joint confidence is bounded by min keypoint visibility
    and overall confidence is the deterministic mean of evaluated joints (Correction #5).
    """
    landmarks = {
        "LEFT_SHOULDER": {"x": 0.40, "y": 0.20, "visibility": 0.95},
        "LEFT_ELBOW": {"x": 0.35, "y": 0.40, "visibility": 0.80},
        "LEFT_WRIST": {"x": 0.30, "y": 0.60, "visibility": 0.90},
        "RIGHT_SHOULDER": {"x": 0.60, "y": 0.20, "visibility": 0.95},
        "RIGHT_ELBOW": {"x": 0.65, "y": 0.40, "visibility": 0.70},
        "RIGHT_WRIST": {"x": 0.70, "y": 0.60, "visibility": 0.85},
    }

    results, overall_conf = compute_standard_joint_angles(
        landmarks=landmarks,
        confidence_threshold=0.5,
        target_joints=["left_elbow", "right_elbow"],
    )

    assert "left_elbow" in results
    assert "right_elbow" in results

    # Left elbow confidence = min(0.95, 0.80, 0.90) = 0.80
    assert results["left_elbow"]["confidence"] == 0.80
    assert results["left_elbow"]["is_occluded"] is False

    # Right elbow confidence = min(0.95, 0.70, 0.85) = 0.70
    assert results["right_elbow"]["confidence"] == 0.70
    assert results["right_elbow"]["is_occluded"] is False

    # Overall confidence = mean(0.80, 0.70) = 0.75
    assert overall_conf == 0.75


def test_occluded_joint_detection():
    """Verifies that keypoint visibility below confidence_threshold flags is_occluded=True."""
    landmarks = {
        "LEFT_SHOULDER": {"x": 0.40, "y": 0.20, "visibility": 0.95},
        "LEFT_ELBOW": {"x": 0.35, "y": 0.40, "visibility": 0.30},  # Low confidence / occluded
        "LEFT_WRIST": {"x": 0.30, "y": 0.60, "visibility": 0.90},
    }

    results, _ = compute_standard_joint_angles(
        landmarks=landmarks,
        confidence_threshold=0.5,
        target_joints=["left_elbow"],
    )

    assert results["left_elbow"]["confidence"] == 0.30
    assert results["left_elbow"]["is_occluded"] is True
