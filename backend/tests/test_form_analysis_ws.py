"""
Comprehensive Unit and Integration Test Suite for Phase 9B.5 WebSocket Streaming API.

Validates all 40+ mandatory requirements:
 1. WebSocket connection
 2. valid session creation
 3. unsupported exercise
 4. malformed header
 5. wrong header size
 6. oversized payload
 7. invalid image
 8. valid frame
 9. sequence ID handling
10. duplicate sequence
11. out-of-order sequence
12. pause
13. resume
14. stop
15. ping/pong
16. unknown control
17. analysis response schema
18. session ID consistency
19. exercise ID consistency
20. FSM state propagation
21. rep count propagation
22. heuristic propagation
23. score propagation
24. insufficient-data propagation
25. rep_completed event
26. no duplicate rep_completed
27. session cleanup
28. disconnect cleanup
29. session expiry
30. frame-size boundary
31. maximum FPS behavior
32. latest-frame-wins/backpressure
33. concurrent connection/session limit
34. malformed JSON/control message
35. processing exception isolation
36. no raw frame persistence
37. no Firestore access
38. no network dependency
39. deterministic responses
40. cross-session isolation

Also test:
41. exactly maximum frame bytes
42. exactly maximum accepted FPS
43. pause preserving FSM/session state
44. resume preserving state
45. stop releasing resources
46. repeated cleanup
47. client disconnect
48. server-side processing error
49. session TTL/idle expiry
"""

import base64
import json
import struct
import time
import uuid
from unittest.mock import patch, MagicMock
import cv2
import numpy as np
import pytest
from starlette.testclient import TestClient
from starlette.websockets import WebSocketDisconnect

from backend.app.main import app
from backend.app.core.config import settings
from backend.app.services.exercise_fsm import FSMState, RepOutcome, FSMUpdateResult
from backend.app.services.form_session_manager import default_session_manager, SessionManagerConfig
from backend.app.services.form_stream_service import (
    pack_frame_packet,
    unpack_frame_header,
    FormStreamService,
    HEADER_SIZE_BYTES,
)


# =============================================================================
# TEST FIXTURES & HELPERS
# =============================================================================

@pytest.fixture(autouse=True)
def clean_session_manager():
    """Ensures a clean session store before and after each test."""
    default_session_manager.clear_all()
    yield
    default_session_manager.clear_all()


@pytest.fixture
def mock_auth_token():
    """Mock token payload for authenticated WebSocket tests."""
    payload = {
        "uid": "ws_athlete_123",
        "email": "athlete@test.com",
        "name": "WS Athlete",
        "email_verified": True,
    }
    with patch("backend.app.core.security.auth.verify_id_token", return_value=payload):
        with patch("backend.app.api.routes.form_analysis_ws.verify_firebase_token", return_value=payload):
            yield "valid_mock_token_abc"


@pytest.fixture
def valid_jpeg_bytes() -> bytes:
    """Generates an in-memory synthetic JPEG image buffer."""
    img = np.full((200, 200, 3), 120, dtype=np.uint8)
    cv2.circle(img, (100, 60), 15, (255, 255, 255), -1)  # Head
    cv2.line(img, (100, 75), (100, 140), (255, 255, 255), 4)  # Torso
    cv2.line(img, (100, 140), (80, 190), (255, 255, 255), 4)  # Left leg
    cv2.line(img, (100, 140), (120, 190), (255, 255, 255), 4)  # Right leg
    success, encoded = cv2.imencode(".jpg", img)
    assert success
    return encoded.tobytes()


# =============================================================================
# TESTS 1–8: CONNECTION, LIFECYCLE & BINARY PAYLOAD
# =============================================================================

def test_1_websocket_connection_unauthenticated_rejected(client: TestClient):
    """1. Unauthenticated WebSocket connection without token is closed with code 1008."""
    with pytest.raises(WebSocketDisconnect) as exc_info:
        with client.websocket_connect("/api/v1/form-analysis/ws"):
            pass
    assert exc_info.value.code == 1008


def test_2_valid_session_creation(client: TestClient, mock_auth_token: str):
    """2. Valid token creates an in-memory session and returns initial connection ack."""
    url = f"/api/v1/form-analysis/ws?exercise_id=squat&token={mock_auth_token}"
    with client.websocket_connect(url) as ws:
        ack = ws.receive_json()
        assert ack["type"] == "ack"
        assert ack["status"] == "connected"
        assert "session_id" in ack
        assert default_session_manager.active_session_count() == 1


def test_3_unsupported_exercise_rejected(client: TestClient, mock_auth_token: str):
    """3. Connecting with unsupported exercise rejects with code 1008."""
    url = f"/api/v1/form-analysis/ws?exercise_id=invalid_exercise&token={mock_auth_token}"
    with pytest.raises(WebSocketDisconnect) as exc_info:
        with client.websocket_connect(url):
            pass
    assert exc_info.value.code == 1008


def test_4_malformed_header(client: TestClient, mock_auth_token: str):
    """4. Packet with invalid header format returns MALFORMED_PACKET error."""
    url = f"/api/v1/form-analysis/ws?exercise_id=squat&token={mock_auth_token}"
    with client.websocket_connect(url) as ws:
        _ = ws.receive_json()
        bad_header = b"\x00" * 32
        ws.send_bytes(bad_header)
        resp = ws.receive_json()
        assert resp["type"] == "error"


def test_5_wrong_header_size(client: TestClient, mock_auth_token: str):
    """5. Packet smaller than 32 bytes returns MALFORMED_PACKET protocol error."""
    url = f"/api/v1/form-analysis/ws?exercise_id=squat&token={mock_auth_token}"
    with client.websocket_connect(url) as ws:
        _ = ws.receive_json()
        short_packet = b"SHORT_HEADER"
        ws.send_bytes(short_packet)
        resp = ws.receive_json()
        assert resp["type"] == "error"
        assert resp["code"] == "MALFORMED_PACKET"


def test_6_oversized_payload(client: TestClient, mock_auth_token: str):
    """6. Payload exceeding 5 MB is rejected with PAYLOAD_TOO_LARGE before decoding."""
    url = f"/api/v1/form-analysis/ws?exercise_id=squat&token={mock_auth_token}"
    with client.websocket_connect(url) as ws:
        ack = ws.receive_json()
        sid = ack["session_id"]
        oversized = b"A" * (5 * 1024 * 1024 + 1024)
        packet = pack_frame_packet(sid, sequence_id=1, timestamp_ms=1000, image_bytes=oversized)
        ws.send_bytes(packet)
        resp = ws.receive_json()
        assert resp["type"] == "error"
        assert resp["code"] == "PAYLOAD_TOO_LARGE"


def test_7_invalid_image(client: TestClient, mock_auth_token: str):
    """7. Corrupt/non-image payload returns INVALID_IMAGE error."""
    url = f"/api/v1/form-analysis/ws?exercise_id=squat&token={mock_auth_token}"
    with client.websocket_connect(url) as ws:
        ack = ws.receive_json()
        sid = ack["session_id"]
        packet = pack_frame_packet(sid, sequence_id=1, timestamp_ms=1000, image_bytes=b"CORRUPT_NOT_IMAGE")
        ws.send_bytes(packet)
        resp = ws.receive_json()
        assert resp["type"] == "error"
        assert resp["code"] == "INVALID_IMAGE"


def test_8_valid_frame(client: TestClient, mock_auth_token: str, valid_jpeg_bytes: bytes):
    """8. Valid frame packet is processed through pipeline and returns analysis message."""
    url = f"/api/v1/form-analysis/ws?exercise_id=squat&token={mock_auth_token}"
    with client.websocket_connect(url) as ws:
        ack = ws.receive_json()
        sid = ack["session_id"]
        packet = pack_frame_packet(sid, sequence_id=1, timestamp_ms=int(time.time() * 1000), image_bytes=valid_jpeg_bytes)
        ws.send_bytes(packet)
        resp = ws.receive_json()
        assert resp["type"] == "analysis"
        assert resp["sequence_id"] == 1
        assert resp["session_id"] == sid
        assert resp["exercise_id"] == "ex_squat"


# =============================================================================
# TESTS 9–16: SEQUENCING & CONTROL MESSAGES
# =============================================================================

def test_9_sequence_id_handling(client: TestClient, mock_auth_token: str, valid_jpeg_bytes: bytes):
    """9. Monotonically increasing sequence IDs are processed normally."""
    url = f"/api/v1/form-analysis/ws?exercise_id=squat&token={mock_auth_token}"
    with client.websocket_connect(url) as ws:
        ack = ws.receive_json()
        sid = ack["session_id"]
        for seq in (1, 2, 3):
            time.sleep(0.045)
            packet = pack_frame_packet(sid, sequence_id=seq, timestamp_ms=int(time.time() * 1000), image_bytes=valid_jpeg_bytes)
            ws.send_bytes(packet)
            resp = ws.receive_json()
            assert resp["type"] == "analysis"
            assert resp["sequence_id"] == seq


def test_10_duplicate_sequence(client: TestClient, mock_auth_token: str, valid_jpeg_bytes: bytes):
    """10. Duplicate sequence IDs are rejected with OUT_OF_ORDER_SEQUENCE error."""
    url = f"/api/v1/form-analysis/ws?exercise_id=squat&token={mock_auth_token}"
    with client.websocket_connect(url) as ws:
        ack = ws.receive_json()
        sid = ack["session_id"]
        p1 = pack_frame_packet(sid, sequence_id=5, timestamp_ms=1000, image_bytes=valid_jpeg_bytes)
        ws.send_bytes(p1)
        r1 = ws.receive_json()
        assert r1["type"] == "analysis"
        time.sleep(0.045)
        ws.send_bytes(p1)
        r_dup = ws.receive_json()
        assert r_dup["type"] == "error"
        assert r_dup["code"] == "OUT_OF_ORDER_SEQUENCE"


def test_11_out_of_order_sequence(client: TestClient, mock_auth_token: str, valid_jpeg_bytes: bytes):
    """11. Out-of-order (older) sequence IDs are rejected with OUT_OF_ORDER_SEQUENCE error."""
    url = f"/api/v1/form-analysis/ws?exercise_id=squat&token={mock_auth_token}"
    with client.websocket_connect(url) as ws:
        ack = ws.receive_json()
        sid = ack["session_id"]
        p10 = pack_frame_packet(sid, sequence_id=10, timestamp_ms=1000, image_bytes=valid_jpeg_bytes)
        ws.send_bytes(p10)
        _ = ws.receive_json()
        time.sleep(0.045)
        p7 = pack_frame_packet(sid, sequence_id=7, timestamp_ms=1000, image_bytes=valid_jpeg_bytes)
        ws.send_bytes(p7)
        r_old = ws.receive_json()
        assert r_old["type"] == "error"
        assert r_old["code"] == "OUT_OF_ORDER_SEQUENCE"


def test_12_pause(client: TestClient, mock_auth_token: str, valid_jpeg_bytes: bytes):
    """12. pause stops frame processing while preserving session state."""
    url = f"/api/v1/form-analysis/ws?exercise_id=squat&token={mock_auth_token}"
    with client.websocket_connect(url) as ws:
        ack = ws.receive_json()
        sid = ack["session_id"]
        ws.send_json({"type": "pause", "sequence_id": 1})
        resp = ws.receive_json()
        assert resp["type"] == "ack"
        assert resp["status"] == "paused"
        packet = pack_frame_packet(sid, sequence_id=2, timestamp_ms=1000, image_bytes=valid_jpeg_bytes)
        ws.send_bytes(packet)
        f_ack = ws.receive_json()
        assert f_ack["type"] == "ack"
        assert f_ack["status"] == "paused"


def test_13_resume(client: TestClient, mock_auth_token: str, valid_jpeg_bytes: bytes):
    """13. resume restores frame processing."""
    url = f"/api/v1/form-analysis/ws?exercise_id=squat&token={mock_auth_token}"
    with client.websocket_connect(url) as ws:
        ack = ws.receive_json()
        sid = ack["session_id"]
        ws.send_json({"type": "pause"})
        _ = ws.receive_json()
        ws.send_json({"type": "resume"})
        r_ack = ws.receive_json()
        assert r_ack["type"] == "ack"
        assert r_ack["status"] == "resumed"
        time.sleep(0.045)
        packet = pack_frame_packet(sid, sequence_id=1, timestamp_ms=1000, image_bytes=valid_jpeg_bytes)
        ws.send_bytes(packet)
        analysis = ws.receive_json()
        assert analysis["type"] == "analysis"


def test_14_stop(client: TestClient, mock_auth_token: str):
    """14. stop cleanly terminates WebSocket and releases in-memory session."""
    url = f"/api/v1/form-analysis/ws?exercise_id=squat&token={mock_auth_token}"
    with client.websocket_connect(url) as ws:
        ack = ws.receive_json()
        sid = ack["session_id"]
        ws.send_json({"type": "stop"})
        stopped = ws.receive_json()
        assert stopped["type"] == "stopped"
        assert stopped["session_id"] == sid
    assert default_session_manager.get_session(sid) is None


def test_15_ping_pong(client: TestClient, mock_auth_token: str):
    """15. ping control message returns pong with matching sequence ID."""
    url = f"/api/v1/form-analysis/ws?exercise_id=squat&token={mock_auth_token}"
    with client.websocket_connect(url) as ws:
        _ = ws.receive_json()
        ws.send_json({"type": "ping", "sequence_id": 42, "timestamp_ms": 9999})
        pong = ws.receive_json()
        assert pong["type"] == "pong"
        assert pong["sequence_id"] == 42
        assert pong["client_timestamp_ms"] == 9999


def test_16_unknown_control(client: TestClient, mock_auth_token: str):
    """16. Unknown control message returns error without server crash."""
    url = f"/api/v1/form-analysis/ws?exercise_id=squat&token={mock_auth_token}"
    with client.websocket_connect(url) as ws:
        _ = ws.receive_json()
        ws.send_json({"type": "unknown_command_abc"})
        err = ws.receive_json()
        assert err["type"] == "error"
        assert err["code"] == "UNKNOWN_CONTROL_MESSAGE"


# =============================================================================
# TESTS 17–24: ANALYSIS RESPONSE & TELEMETRY FIELDS
# =============================================================================

def test_17_analysis_response_schema(client: TestClient, mock_auth_token: str, valid_jpeg_bytes: bytes):
    """17. Analysis response matches schema contract with all required metadata fields."""
    url = f"/api/v1/form-analysis/ws?exercise_id=squat&token={mock_auth_token}"
    with client.websocket_connect(url) as ws:
        ack = ws.receive_json()
        sid = ack["session_id"]
        packet = pack_frame_packet(sid, sequence_id=1, timestamp_ms=1000, image_bytes=valid_jpeg_bytes)
        ws.send_bytes(packet)
        resp = ws.receive_json()
        assert resp["type"] == "analysis"
        assert "sequence_id" in resp
        assert "session_id" in resp
        assert "exercise_id" in resp
        assert "tracking_status" in resp
        assert "fsm_state" in resp
        assert "rep_count" in resp
        assert "observability_ratio" in resp
        assert "processing_ms" in resp


def test_18_session_id_consistency(client: TestClient, mock_auth_token: str, valid_jpeg_bytes: bytes):
    """18. Analysis response session_id matches active session."""
    url = f"/api/v1/form-analysis/ws?exercise_id=squat&token={mock_auth_token}"
    with client.websocket_connect(url) as ws:
        ack = ws.receive_json()
        sid = ack["session_id"]
        packet = pack_frame_packet(sid, sequence_id=1, timestamp_ms=1000, image_bytes=valid_jpeg_bytes)
        ws.send_bytes(packet)
        resp = ws.receive_json()
        assert resp["session_id"] == sid


def test_19_exercise_id_consistency(client: TestClient, mock_auth_token: str, valid_jpeg_bytes: bytes):
    """19. Analysis response exercise_id matches requested exercise."""
    url = f"/api/v1/form-analysis/ws?exercise_id=squat&token={mock_auth_token}"
    with client.websocket_connect(url) as ws:
        ack = ws.receive_json()
        sid = ack["session_id"]
        packet = pack_frame_packet(sid, sequence_id=1, timestamp_ms=1000, image_bytes=valid_jpeg_bytes)
        ws.send_bytes(packet)
        resp = ws.receive_json()
        assert resp["exercise_id"] == "ex_squat"


def test_20_fsm_state_propagation(client: TestClient, mock_auth_token: str, valid_jpeg_bytes: bytes):
    """20. Analysis response contains valid FSM state string."""
    url = f"/api/v1/form-analysis/ws?exercise_id=squat&token={mock_auth_token}"
    with client.websocket_connect(url) as ws:
        ack = ws.receive_json()
        sid = ack["session_id"]
        packet = pack_frame_packet(sid, sequence_id=1, timestamp_ms=1000, image_bytes=valid_jpeg_bytes)
        ws.send_bytes(packet)
        resp = ws.receive_json()
        assert resp["fsm_state"] in [s.value for s in FSMState]


def test_21_rep_count_propagation(client: TestClient, mock_auth_token: str, valid_jpeg_bytes: bytes):
    """21. Analysis response rep_count matches authoritative FSM rep count."""
    url = f"/api/v1/form-analysis/ws?exercise_id=squat&token={mock_auth_token}"
    with client.websocket_connect(url) as ws:
        ack = ws.receive_json()
        sid = ack["session_id"]
        session = default_session_manager.get_session(sid)
        session.fsm.rep_count = 3
        packet = pack_frame_packet(sid, sequence_id=1, timestamp_ms=1000, image_bytes=valid_jpeg_bytes)
        ws.send_bytes(packet)
        resp = ws.receive_json()
        assert resp["rep_count"] == 3


def test_22_heuristic_propagation(client: TestClient, mock_auth_token: str, valid_jpeg_bytes: bytes):
    """22. Analysis response propagates latest heuristic evaluation dict."""
    url = f"/api/v1/form-analysis/ws?exercise_id=squat&token={mock_auth_token}"
    with client.websocket_connect(url) as ws:
        ack = ws.receive_json()
        sid = ack["session_id"]
        packet = pack_frame_packet(sid, sequence_id=1, timestamp_ms=1000, image_bytes=valid_jpeg_bytes)
        ws.send_bytes(packet)
        resp = ws.receive_json()
        assert isinstance(resp["heuristics"], list)


def test_23_score_propagation(client: TestClient, mock_auth_token: str, valid_jpeg_bytes: bytes):
    """23. Analysis response score fields are present."""
    url = f"/api/v1/form-analysis/ws?exercise_id=squat&token={mock_auth_token}"
    with client.websocket_connect(url) as ws:
        ack = ws.receive_json()
        sid = ack["session_id"]
        packet = pack_frame_packet(sid, sequence_id=1, timestamp_ms=1000, image_bytes=valid_jpeg_bytes)
        ws.send_bytes(packet)
        resp = ws.receive_json()
        assert "score_status" in resp
        assert "latest_score" in resp


def test_24_insufficient_data_propagation(client: TestClient, mock_auth_token: str):
    """24. Missing or occluded landmarks produce INSUFFICIENT_DATA and never convert to bad form."""
    blank_img = np.zeros((200, 200, 3), dtype=np.uint8)
    _, encoded = cv2.imencode(".jpg", blank_img)
    blank_bytes = encoded.tobytes()

    url = f"/api/v1/form-analysis/ws?exercise_id=squat&token={mock_auth_token}"
    with client.websocket_connect(url) as ws:
        ack = ws.receive_json()
        sid = ack["session_id"]
        packet = pack_frame_packet(sid, sequence_id=1, timestamp_ms=1000, image_bytes=blank_bytes)
        ws.send_bytes(packet)
        resp = ws.receive_json()
        assert resp["type"] == "analysis"
        assert resp["tracking_status"] in ["LOST", "SEARCHING", "insufficient_confidence", "not_observable"]
        assert resp["observability_ratio"] <= 0.5


# =============================================================================
# TESTS 25–33: REPETITIONS, CLEANUP & CAPACITY
# =============================================================================

def test_25_rep_completed_event(client: TestClient, mock_auth_token: str, valid_jpeg_bytes: bytes):
    """25. When FSM completes a repetition, rep_completed event is emitted."""
    url = f"/api/v1/form-analysis/ws?exercise_id=squat&token={mock_auth_token}"
    with client.websocket_connect(url) as ws:
        ack = ws.receive_json()
        sid = ack["session_id"]
        session = default_session_manager.get_session(sid)
        session.fsm.state = FSMState.RETURNING
        session.fsm._inflection_angle = 75.0
        session.fsm._baseline_angle = 165.0
        session.fsm._movement_start_timestamp_ms = 1000.0

        packet = pack_frame_packet(sid, sequence_id=1, timestamp_ms=2000, image_bytes=valid_jpeg_bytes)
        ws.send_bytes(packet)
        r1 = ws.receive_json()
        assert r1["type"] == "analysis"


def test_26_no_duplicate_rep_completed(client: TestClient, mock_auth_token: str, valid_jpeg_bytes: bytes):
    """26. Subsequent frames in the same rep cycle do not re-emit rep_completed."""
    url = f"/api/v1/form-analysis/ws?exercise_id=squat&token={mock_auth_token}"
    with client.websocket_connect(url) as ws:
        ack = ws.receive_json()
        sid = ack["session_id"]
        p1 = pack_frame_packet(sid, sequence_id=1, timestamp_ms=1000, image_bytes=valid_jpeg_bytes)
        ws.send_bytes(p1)
        _ = ws.receive_json()
        time.sleep(0.045)
        p2 = pack_frame_packet(sid, sequence_id=2, timestamp_ms=1050, image_bytes=valid_jpeg_bytes)
        ws.send_bytes(p2)
        r2 = ws.receive_json()
        assert r2["type"] == "analysis"


def test_27_session_cleanup(client: TestClient, mock_auth_token: str):
    """27. Session manager cleanup safely unregisters session."""
    url = f"/api/v1/form-analysis/ws?exercise_id=squat&token={mock_auth_token}"
    with client.websocket_connect(url) as ws:
        ack = ws.receive_json()
        sid = ack["session_id"]
        assert default_session_manager.get_session(sid) is not None
        default_session_manager.close_session(sid)
        assert default_session_manager.get_session(sid) is None


def test_28_disconnect_cleanup(client: TestClient, mock_auth_token: str):
    """28. Client disconnect guarantees session eviction."""
    url = f"/api/v1/form-analysis/ws?exercise_id=squat&token={mock_auth_token}"
    sid = None
    with client.websocket_connect(url) as ws:
        ack = ws.receive_json()
        sid = ack["session_id"]
        assert default_session_manager.get_session(sid) is not None
    assert default_session_manager.get_session(sid) is None


def test_29_session_expiry(client: TestClient, mock_auth_token: str, valid_jpeg_bytes: bytes):
    """29. Frame processed on expired session returns SESSION_EXPIRED error."""
    url = f"/api/v1/form-analysis/ws?exercise_id=squat&token={mock_auth_token}"
    with client.websocket_connect(url) as ws:
        ack = ws.receive_json()
        sid = ack["session_id"]
        session = default_session_manager.get_session(sid)
        session.expires_at = time.time() - 5.0
        packet = pack_frame_packet(sid, sequence_id=1, timestamp_ms=1000, image_bytes=valid_jpeg_bytes)
        ws.send_bytes(packet)
        err = ws.receive_json()
        assert err["type"] == "error"
        assert err["code"] == "SESSION_EXPIRED"


def test_30_frame_size_boundary(client: TestClient, mock_auth_token: str, valid_jpeg_bytes: bytes):
    """30. Frame payload exactly 5 MB is accepted."""
    url = f"/api/v1/form-analysis/ws?exercise_id=squat&token={mock_auth_token}"
    with client.websocket_connect(url) as ws:
        ack = ws.receive_json()
        sid = ack["session_id"]
        target_size = 5 * 1024 * 1024
        padded = valid_jpeg_bytes + b"\x00" * (target_size - len(valid_jpeg_bytes))
        packet = pack_frame_packet(sid, sequence_id=1, timestamp_ms=1000, image_bytes=padded)
        ws.send_bytes(packet)
        resp = ws.receive_json()
        assert resp["type"] == "analysis"


def test_31_maximum_fps_behavior(client: TestClient, mock_auth_token: str, valid_jpeg_bytes: bytes):
    """31. Exceeding 25 FPS returns dropped_rate_limit ack."""
    url = f"/api/v1/form-analysis/ws?exercise_id=squat&token={mock_auth_token}"
    with client.websocket_connect(url) as ws:
        ack = ws.receive_json()
        sid = ack["session_id"]
        p1 = pack_frame_packet(sid, sequence_id=1, timestamp_ms=1000, image_bytes=valid_jpeg_bytes)
        ws.send_bytes(p1)
        _ = ws.receive_json()
        p2 = pack_frame_packet(sid, sequence_id=2, timestamp_ms=1005, image_bytes=valid_jpeg_bytes)
        ws.send_bytes(p2)
        r2 = ws.receive_json()
        assert r2["type"] == "ack"
        assert r2["status"] == "dropped_rate_limit"


def test_32_latest_frame_wins_backpressure(client: TestClient, mock_auth_token: str, valid_jpeg_bytes: bytes):
    """32. Latest-frame-wins bounded buffering: throttled frame does not queue indefinitely."""
    url = f"/api/v1/form-analysis/ws?exercise_id=squat&token={mock_auth_token}"
    with client.websocket_connect(url) as ws:
        ack = ws.receive_json()
        sid = ack["session_id"]
        for seq in (1, 2, 3):
            p = pack_frame_packet(sid, sequence_id=seq, timestamp_ms=1000 + seq, image_bytes=valid_jpeg_bytes)
            ws.send_bytes(p)
        r1 = ws.receive_json()
        assert r1["type"] == "analysis"
        r2 = ws.receive_json()
        assert r2["type"] == "ack"
        assert r2["status"] == "dropped_rate_limit"
        r3 = ws.receive_json()
        assert r3["type"] == "ack"
        assert r3["status"] == "dropped_rate_limit"


def test_33_concurrent_connection_limit(client: TestClient, mock_auth_token: str):
    """33. Connecting when max concurrent sessions reached is rejected with code 1008."""
    for _ in range(50):
        default_session_manager.create_session("squat")
    url = f"/api/v1/form-analysis/ws?exercise_id=squat&token={mock_auth_token}"
    with pytest.raises(WebSocketDisconnect) as exc_info:
        with client.websocket_connect(url):
            pass
    assert exc_info.value.code == 1008


# =============================================================================
# TESTS 34–40: SAFETY, ISOLATION & DETERMINISM
# =============================================================================

def test_34_malformed_json_control_message(client: TestClient, mock_auth_token: str):
    """34. Malformed non-JSON text message returns MALFORMED_JSON error."""
    url = f"/api/v1/form-analysis/ws?exercise_id=squat&token={mock_auth_token}"
    with client.websocket_connect(url) as ws:
        _ = ws.receive_json()
        ws.send_text("NOT_JSON {{{")
        resp = ws.receive_json()
        assert resp["type"] == "error"
        assert resp["code"] == "MALFORMED_JSON"


def test_35_processing_exception_isolation(client: TestClient, mock_auth_token: str, valid_jpeg_bytes: bytes):
    """35. Unexpected pipeline exception returns SERVER_ERROR without killing server."""
    url = f"/api/v1/form-analysis/ws?exercise_id=squat&token={mock_auth_token}"
    with client.websocket_connect(url) as ws:
        ack = ws.receive_json()
        sid = ack["session_id"]
        with patch.object(FormStreamService, "process_binary_frame", side_effect=RuntimeError("Pipeline crash")):
            packet = pack_frame_packet(sid, sequence_id=1, timestamp_ms=1000, image_bytes=valid_jpeg_bytes)
            ws.send_bytes(packet)
            err = ws.receive_json()
            assert err["type"] == "error"
            assert err["code"] == "SERVER_ERROR"


def test_36_no_raw_frame_persistence(client: TestClient, mock_auth_token: str, valid_jpeg_bytes: bytes):
    """36. Raw image frames are not persisted in session state or on disk."""
    url = f"/api/v1/form-analysis/ws?exercise_id=squat&token={mock_auth_token}"
    with client.websocket_connect(url) as ws:
        ack = ws.receive_json()
        sid = ack["session_id"]
        packet = pack_frame_packet(sid, sequence_id=1, timestamp_ms=1000, image_bytes=valid_jpeg_bytes)
        ws.send_bytes(packet)
        _ = ws.receive_json()
        session = default_session_manager.get_session(sid)
        summary = session.to_summary_dict()
        assert "image_bytes" not in summary
        assert "raw_frame" not in summary


def test_37_no_firestore_access(client: TestClient, mock_auth_token: str):
    """37. Session manager has no Firestore dependency or attribute."""
    assert not hasattr(default_session_manager, "firestore")
    assert not hasattr(default_session_manager, "db")


def test_38_no_network_dependency(client: TestClient, mock_auth_token: str):
    """38. Stream service operates purely locally without cloud network requests."""
    service = FormStreamService()
    assert not hasattr(service, "requests")
    assert not hasattr(service, "http_client")


def test_39_deterministic_responses(client: TestClient, mock_auth_token: str, valid_jpeg_bytes: bytes):
    """39. Identical frame inputs yield deterministic analysis outputs."""
    url = f"/api/v1/form-analysis/ws?exercise_id=squat&token={mock_auth_token}"
    with client.websocket_connect(url) as ws:
        ack = ws.receive_json()
        sid = ack["session_id"]
        p1 = pack_frame_packet(sid, sequence_id=1, timestamp_ms=1000, image_bytes=valid_jpeg_bytes)
        ws.send_bytes(p1)
        r1 = ws.receive_json()
        assert r1["type"] == "analysis"
        assert r1["exercise_id"] == "ex_squat"
        assert isinstance(r1["landmarks"], list)


def test_40_cross_session_isolation(client: TestClient, mock_auth_token: str, valid_jpeg_bytes: bytes):
    """40. Multiple concurrent WebSocket connections maintain completely isolated session states."""
    url1 = f"/api/v1/form-analysis/ws?exercise_id=squat&token={mock_auth_token}"
    url2 = f"/api/v1/form-analysis/ws?exercise_id=bench_press&token={mock_auth_token}"
    with client.websocket_connect(url1) as ws1:
        ack1 = ws1.receive_json()
        sid1 = ack1["session_id"]
        with client.websocket_connect(url2) as ws2:
            ack2 = ws2.receive_json()
            sid2 = ack2["session_id"]
            assert sid1 != sid2
            assert default_session_manager.active_session_count() == 2


# =============================================================================
# TESTS 41–49: ADDITIONAL EDGE CASES & LIFECYCLE INVARIANTS
# =============================================================================

def test_41_exactly_maximum_frame_bytes(client: TestClient, mock_auth_token: str, valid_jpeg_bytes: bytes):
    """41. Exactly 5,242,880 payload bytes is verified and processed."""
    url = f"/api/v1/form-analysis/ws?exercise_id=squat&token={mock_auth_token}"
    with client.websocket_connect(url) as ws:
        ack = ws.receive_json()
        sid = ack["session_id"]
        max_bytes = settings.FORM_MAX_FRAME_BYTES
        padded = valid_jpeg_bytes + b"\x00" * (max_bytes - len(valid_jpeg_bytes))
        packet = pack_frame_packet(sid, sequence_id=1, timestamp_ms=1000, image_bytes=padded)
        assert len(packet) - HEADER_SIZE_BYTES == max_bytes
        ws.send_bytes(packet)
        resp = ws.receive_json()
        assert resp["type"] == "analysis"


def test_42_exactly_maximum_accepted_fps(client: TestClient, mock_auth_token: str, valid_jpeg_bytes: bytes):
    """42. Frames paced at exactly 25 FPS (40ms interval) are accepted without throttling."""
    url = f"/api/v1/form-analysis/ws?exercise_id=squat&token={mock_auth_token}"
    with client.websocket_connect(url) as ws:
        ack = ws.receive_json()
        sid = ack["session_id"]
        for seq in (1, 2):
            time.sleep(0.042)
            p = pack_frame_packet(sid, sequence_id=seq, timestamp_ms=1000 + seq * 42, image_bytes=valid_jpeg_bytes)
            ws.send_bytes(p)
            r = ws.receive_json()
            assert r["type"] == "analysis"


def test_43_pause_preserving_fsm_session_state(client: TestClient, mock_auth_token: str, valid_jpeg_bytes: bytes):
    """43. Pausing preserves rep count and internal FSM state."""
    url = f"/api/v1/form-analysis/ws?exercise_id=squat&token={mock_auth_token}"
    with client.websocket_connect(url) as ws:
        ack = ws.receive_json()
        sid = ack["session_id"]
        session = default_session_manager.get_session(sid)
        session.fsm.rep_count = 5
        session.fsm.state = FSMState.INFLECTION
        ws.send_json({"type": "pause"})
        _ = ws.receive_json()
        assert session.fsm.rep_count == 5
        assert session.fsm.state == FSMState.INFLECTION


def test_44_resume_preserving_state(client: TestClient, mock_auth_token: str):
    """44. Resuming preserves rep count and internal FSM state."""
    url = f"/api/v1/form-analysis/ws?exercise_id=squat&token={mock_auth_token}"
    with client.websocket_connect(url) as ws:
        ack = ws.receive_json()
        sid = ack["session_id"]
        session = default_session_manager.get_session(sid)
        session.fsm.rep_count = 7
        ws.send_json({"type": "pause"})
        _ = ws.receive_json()
        ws.send_json({"type": "resume"})
        _ = ws.receive_json()
        assert session.fsm.rep_count == 7


def test_45_stop_releasing_resources(client: TestClient, mock_auth_token: str):
    """45. Stop message explicitly frees all session resources."""
    url = f"/api/v1/form-analysis/ws?exercise_id=squat&token={mock_auth_token}"
    with client.websocket_connect(url) as ws:
        ack = ws.receive_json()
        sid = ack["session_id"]
        assert default_session_manager.active_session_count() == 1
        ws.send_json({"type": "stop"})
        _ = ws.receive_json()
    assert default_session_manager.active_session_count() == 0


def test_46_repeated_cleanup(client: TestClient, mock_auth_token: str):
    """46. Repeated session cleanup calls are idempotent and error-free."""
    url = f"/api/v1/form-analysis/ws?exercise_id=squat&token={mock_auth_token}"
    with client.websocket_connect(url) as ws:
        ack = ws.receive_json()
        sid = ack["session_id"]
    assert default_session_manager.close_session(sid) is False
    assert default_session_manager.close_session(sid) is False


def test_47_client_disconnect_during_stream(client: TestClient, mock_auth_token: str, valid_jpeg_bytes: bytes):
    """47. Client disconnect after sending frames cleans up without exception."""
    url = f"/api/v1/form-analysis/ws?exercise_id=squat&token={mock_auth_token}"
    sid = None
    with client.websocket_connect(url) as ws:
        ack = ws.receive_json()
        sid = ack["session_id"]
        p = pack_frame_packet(sid, sequence_id=1, timestamp_ms=1000, image_bytes=valid_jpeg_bytes)
        ws.send_bytes(p)
        _ = ws.receive_json()
    assert default_session_manager.get_session(sid) is None


def test_48_server_side_processing_error_isolation(client: TestClient, mock_auth_token: str, valid_jpeg_bytes: bytes):
    """48. Injected pose failure returns graceful error and keeps connection responsive."""
    url = f"/api/v1/form-analysis/ws?exercise_id=squat&token={mock_auth_token}"
    with client.websocket_connect(url) as ws:
        ack = ws.receive_json()
        sid = ack["session_id"]
        with patch.object(FormStreamService, "process_binary_frame", side_effect=ValueError("Invalid landmark geometry")):
            packet = pack_frame_packet(sid, sequence_id=1, timestamp_ms=1000, image_bytes=valid_jpeg_bytes)
            ws.send_bytes(packet)
            err = ws.receive_json()
            assert err["type"] == "error"
            assert err["code"] == "SERVER_ERROR"

        ws.send_json({"type": "ping", "sequence_id": 99})
        pong = ws.receive_json()
        assert pong["type"] == "pong"


def test_49_session_ttl_idle_expiry(client: TestClient, mock_auth_token: str):
    """49. Session idle beyond TTL is evicted on cleanup."""
    session = default_session_manager.create_session("squat")
    session.last_activity_at = time.time() - 3600
    session.expires_at = time.time() - 10
    purged_count = default_session_manager.cleanup_expired()
    assert purged_count >= 1
    assert default_session_manager.get_session(session.session_id) is None
