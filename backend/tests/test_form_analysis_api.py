"""
API Integration Tests for Form Analysis & Computer Vision Endpoints (Phase 9A).

Verifies:
- GET /health: Operational readiness of the local CV subsystem.
- POST /pose/extract: Multipart file upload and Base64 JSON parsing with 5 MB ceiling enforcement.
- POST /pose/angles: Independent geometric angle calculation from supplied landmarks or image.
- GET /session/{exercise_id}: Stateless baseline metadata (authenticated vs unauthenticated).
- Payload validation, unsupported media types, and empty payload rejections.
"""

import base64
import cv2
import numpy as np
import pytest
from unittest.mock import patch
from fastapi.testclient import TestClient

from backend.app.core.config import settings


@pytest.fixture
def synthetic_jpeg_bytes() -> bytes:
    """Generates an in-memory synthetic JPEG image buffer."""
    img = np.full((200, 200, 3), 100, dtype=np.uint8)
    cv2.circle(img, (100, 70), 20, (255, 255, 255), -1)
    cv2.line(img, (100, 90), (100, 160), (255, 255, 255), 5)
    success, encoded = cv2.imencode(".jpg", img)
    assert success
    return encoded.tobytes()


def test_cv_health_endpoint(client: TestClient):
    """Verifies that GET /health returns operational readiness of the CV engine."""
    response = client.get("/api/v1/form-analysis/health")
    assert response.status_code == 200
    data = response.json()
    assert data["status"] in ["healthy", "mock_mode"]
    assert data["supported_landmarks"] == 33
    assert data["confidence_threshold"] == settings.CV_MIN_TRACKING_CONFIDENCE


def test_pose_extract_multipart_success(client: TestClient, synthetic_jpeg_bytes: bytes):
    """Verifies successful multipart image upload and landmark extraction."""
    response = client.post(
        "/api/v1/form-analysis/pose/extract",
        files={"file": ("test_frame.jpg", synthetic_jpeg_bytes, "image/jpeg")},
    )
    assert response.status_code == 200
    data = response.json()
    assert "landmarks_detected" in data
    assert "landmark_count" in data
    assert "processing_time_ms" in data


def test_pose_extract_base64_success(client: TestClient, synthetic_jpeg_bytes: bytes):
    """Verifies successful base64 image payload extraction."""
    b64_str = base64.b64encode(synthetic_jpeg_bytes).decode("utf-8")
    response = client.post(
        "/api/v1/form-analysis/pose/extract",
        json={"image_base64": f"data:image/jpeg;base64,{b64_str}"},
    )
    assert response.status_code == 200
    data = response.json()
    assert "landmarks_detected" in data


def test_pose_extract_unsupported_media_type(client: TestClient):
    """Verifies that non-image MIME types (e.g. text/plain) are rejected with 422."""
    response = client.post(
        "/api/v1/form-analysis/pose/extract",
        files={"file": ("notes.txt", b"Not an image file", "text/plain")},
    )
    assert response.status_code == 422
    assert "Unsupported media type" in response.json()["detail"]


def test_pose_extract_empty_request_rejected(client: TestClient):
    """Verifies that empty request body returns 400 Bad Request."""
    response = client.post("/api/v1/form-analysis/pose/extract", json={})
    assert response.status_code == 400


def test_pose_extract_oversized_payload_rejected(client: TestClient):
    """Verifies that payloads exceeding 5 MB are rejected with 413 Payload Too Large."""
    oversized = b"X" * (settings.CV_MAX_IMAGE_SIZE_BYTES + 1024)
    response = client.post(
        "/api/v1/form-analysis/pose/extract",
        files={"file": ("large.jpg", oversized, "image/jpeg")},
    )
    assert response.status_code == 413
    assert "exceeds maximum limit" in response.json()["detail"]


def test_pose_angles_from_supplied_landmarks(client: TestClient):
    """
    Verifies that /pose/angles computes joint angles directly from supplied landmarks.
    Tests geometry independently without requiring image decoding (Correction #6).
    """
    landmarks_payload = {
        "LEFT_SHOULDER": {"index": 11, "name": "LEFT_SHOULDER", "x": 0.40, "y": 0.20, "visibility": 0.95},
        "LEFT_ELBOW": {"index": 13, "name": "LEFT_ELBOW", "x": 0.40, "y": 0.50, "visibility": 0.90},  # Vertex
        "LEFT_WRIST": {"index": 15, "name": "LEFT_WRIST", "x": 0.70, "y": 0.50, "visibility": 0.85},   # 90 deg right
    }

    response = client.post(
        "/api/v1/form-analysis/pose/angles",
        json={
            "landmarks": landmarks_payload,
            "target_joints": ["left_elbow"],
        },
    )
    assert response.status_code == 200
    data = response.json()
    assert data["landmarks_detected"] is True
    assert "left_elbow" in data["joint_angles"]
    elbow = data["joint_angles"]["left_elbow"]
    assert elbow["angle_degrees"] == 90.0
    assert elbow["confidence"] == 0.85
    assert elbow["is_occluded"] is False


def test_pose_angles_missing_inputs_rejected(client: TestClient):
    """Verifies that /pose/angles returns 400 when neither landmarks nor image are provided."""
    response = client.post("/api/v1/form-analysis/pose/angles", json={})
    assert response.status_code == 400


def test_stateless_session_metadata_authenticated(client: TestClient):
    """
    Verifies that authenticated user can retrieve stateless baseline session metadata.
    Confirms zero database persistence in Phase 9A (Correction #7).
    """
    mock_payload = {
        "uid": "form_athlete_999",
        "email": "form_athlete@test.com",
        "name": "Form Athlete",
        "email_verified": True,
    }
    with patch("backend.app.core.security.auth.verify_id_token", return_value=mock_payload):
        response = client.get(
            "/api/v1/form-analysis/session/ex_bench_press",
            headers={"Authorization": "Bearer mock_valid_token_cv"},
        )
        assert response.status_code == 200
        data = response.json()
        assert data["exerciseId"] == "ex_bench_press"
        assert data["exerciseName"] == "Bench Press"
        assert data["formScore"] == 0.0
        assert data["formStatus"] == "Ready"
        assert len(data["keyMetrics"]) > 0


def test_stateless_session_metadata_unauthenticated_rejected(client: TestClient):
    """Verifies that unauthenticated request to /session/{id} returns 401."""
    response = client.get("/api/v1/form-analysis/session/ex_bench_press")
    assert response.status_code == 401
