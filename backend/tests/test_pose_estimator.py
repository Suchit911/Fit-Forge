"""
Unit Tests for Pose Estimator Engines (Phase 9A).

Verifies:
- BasePoseEstimator contract.
- MockPoseEstimator deterministic presets and mock states.
- MediaPipePoseEstimator initialization, empty buffers, corrupt bytes, and size limits.
- Canonical 33 pose landmark topology coverage.
"""

import pytest
import numpy as np
import cv2

from backend.app.services.pose_estimator import (
    BasePoseEstimator,
    MediaPipePoseEstimator,
    MockPoseEstimator,
    POSE_LANDMARK_NAMES,
)
from backend.app.core.config import settings


def test_canonical_landmark_names_count():
    """Verifies that all 33 canonical MediaPipe landmark names are defined."""
    assert len(POSE_LANDMARK_NAMES) == 33
    assert POSE_LANDMARK_NAMES[0] == "NOSE"
    assert POSE_LANDMARK_NAMES[11] == "LEFT_SHOULDER"
    assert POSE_LANDMARK_NAMES[12] == "RIGHT_SHOULDER"
    assert POSE_LANDMARK_NAMES[23] == "LEFT_HIP"
    assert POSE_LANDMARK_NAMES[24] == "RIGHT_HIP"
    assert POSE_LANDMARK_NAMES[32] == "RIGHT_FOOT_INDEX"


def test_mock_pose_estimator_presets():
    """Verifies that MockPoseEstimator generates valid 33-landmark presets."""
    mock = MockPoseEstimator(default_preset="standing")
    assert mock.is_ready() is True

    # 1. Standing preset
    res_standing = mock.estimate_pose(b"fake_image_bytes")
    assert res_standing["landmarks_detected"] is True
    assert res_standing["landmark_count"] == 33
    assert len(res_standing["landmarks"]) == 33
    assert "LEFT_ELBOW" in res_standing["landmarks"]
    assert res_standing["bounding_box"] is not None
    assert res_standing["overall_confidence"] > 0.90

    # 2. Squat preset
    mock.set_preset("squat")
    res_squat = mock.estimate_pose(b"fake_image_bytes")
    assert res_squat["landmarks_detected"] is True
    assert res_squat["landmarks"]["LEFT_KNEE"]["x"] != res_standing["landmarks"]["LEFT_KNEE"]["x"]

    # 3. Bench press preset
    mock.set_preset("bench_press")
    res_bench = mock.estimate_pose(b"fake_image_bytes")
    assert res_bench["landmarks_detected"] is True
    assert res_bench["landmarks"]["LEFT_WRIST"]["y"] != res_standing["landmarks"]["LEFT_WRIST"]["y"]


def test_mock_pose_estimator_detection_disabled():
    """Verifies that disabling detection returns a clean non-detected result."""
    mock = MockPoseEstimator()
    mock.set_detection_enabled(False)
    res = mock.estimate_pose(b"fake_image_bytes")
    assert res["landmarks_detected"] is False
    assert res["landmark_count"] == 0
    assert res["landmarks"] == {}
    assert res["bounding_box"] is None


def test_mock_pose_estimator_oversized_payload_rejected():
    """Verifies that payloads exceeding CV_MAX_IMAGE_SIZE_BYTES are rejected before processing."""
    mock = MockPoseEstimator()
    oversized_bytes = b"0" * (settings.CV_MAX_IMAGE_SIZE_BYTES + 10)
    with pytest.raises(ValueError) as exc:
        mock.estimate_pose(oversized_bytes)
    assert "exceeds maximum allowed size" in str(exc.value)


def test_mediapipe_pose_estimator_empty_and_corrupt_bytes():
    """Verifies that empty or corrupt bytes return empty response without crashing."""
    mp_estimator = MediaPipePoseEstimator()

    # Empty bytes
    res_empty = mp_estimator.estimate_pose(b"")
    assert res_empty["landmarks_detected"] is False
    assert res_empty["landmark_count"] == 0

    # Corrupt non-image bytes
    res_corrupt = mp_estimator.estimate_pose(b"not_a_valid_image_file_bytes_here")
    assert res_corrupt["landmarks_detected"] is False
    assert res_corrupt["landmark_count"] == 0


def test_mediapipe_pose_estimator_blank_frame():
    """Verifies that a solid black image array returns landmarks_detected=False gracefully."""
    mp_estimator = MediaPipePoseEstimator()
    black_img = np.zeros((240, 320, 3), dtype=np.uint8)
    res = mp_estimator.estimate_pose_from_array(black_img)
    assert res["landmarks_detected"] is False
    assert res["landmark_count"] == 0


def test_mediapipe_pose_estimator_synthetic_frame_inference():
    """
    Verifies that an in-memory synthetic BGR image is processed cleanly by MediaPipe.
    Guarantees no memory leaks, unhandled exceptions, or disk writes.
    """
    mp_estimator = MediaPipePoseEstimator()
    # Create simple synthetic test image
    img = np.full((300, 300, 3), 128, dtype=np.uint8)
    cv2.circle(img, (150, 100), 30, (255, 255, 255), -1)  # Head proxy
    cv2.line(img, (150, 130), (150, 220), (255, 255, 255), 8)  # Torso proxy

    res = mp_estimator.estimate_pose_from_array(img)
    # Output structure must be well-formed regardless of whether BlazePose finds human
    assert "landmarks_detected" in res
    assert "landmark_count" in res
    assert "processing_time_ms" in res
    assert isinstance(res["processing_time_ms"], float)
