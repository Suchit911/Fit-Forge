"""
WebSocket API Route for Real-Time AI Form Analysis Streaming (Phase 9B.5).

Endpoints:
- /api/v1/form-analysis/ws
- /api/v1/form-analysis/ws/stream/{session_id}

Protocol:
- Binary frame packets (32-byte header + WebP/JPEG image)
- JSON control messages: pause, resume, stop, ping
- Server responses: ack, analysis, rep_completed, error, pong, stopped

Authentication:
- Verifies Firebase ID token via query parameter (?token=...) or Authorization header.
- Rejects unauthenticated connections with code 1008 (Policy Violation).
"""

import json
import time
from typing import Optional
from fastapi import (
    APIRouter,
    WebSocket,
    WebSocketDisconnect,
    Query,
    status,
    HTTPException,
)

from ...core.config import settings
from ...core.security import verify_firebase_token
from ...utils.logger import logger
from ...schemas.form_analysis import (
    WSAckMessage,
    WSAnalysisMessage,
    WSRepCompletedMessage,
    WSErrorMessage,
    WSPongMessage,
    WSStoppedMessage,
)
from ...services.form_session_manager import (
    FormSessionManager,
    FormAnalysisSession,
    InvalidExerciseError,
    SessionLimitExceededError,
    default_session_manager,
)
from ...services.form_stream_service import (
    FormStreamService,
    StreamProtocolError,
    MalformedPacketError,
    PayloadTooLargeError,
    InvalidImageError,
    FrameDimensionError,
)
from ...repositories.form_analysis_repository import get_form_analysis_repository

router = APIRouter()

# Singletons
_stream_service = FormStreamService()


def get_stream_service() -> FormStreamService:
    return _stream_service


def get_session_manager() -> FormSessionManager:
    return _stream_service.session_manager


async def authenticate_ws_token(websocket: WebSocket, token: Optional[str]) -> Optional[str]:
    """
    Validates Firebase ID token from query parameter or headers.
    Closes websocket with code 1008 if unauthenticated or invalid.
    Returns authenticated user's UID on success.
    """
    if not token:
        # Check authorization header if client passed it
        auth_header = websocket.headers.get("authorization")
        if auth_header and auth_header.startswith("Bearer "):
            token = auth_header.split(" ", 1)[1]

    if not token:
        await websocket.close(
            code=status.WS_1008_POLICY_VIOLATION,
            reason="Missing authentication token",
        )
        return None

    try:
        decoded = verify_firebase_token(token)
        uid = decoded.get("uid") or decoded.get("user_id") or decoded.get("sub") or ""
        if not uid:
            await websocket.close(
                code=status.WS_1008_POLICY_VIOLATION,
                reason="Invalid user credentials in token",
            )
            return None
        return uid
    except HTTPException as exc:
        await websocket.close(
            code=status.WS_1008_POLICY_VIOLATION,
            reason=str(exc.detail),
        )
        return None
    except Exception as e:
        logger.warning(f"WebSocket auth failed: {e}")
        await websocket.close(
            code=status.WS_1008_POLICY_VIOLATION,
            reason="Could not validate credentials",
        )
        return None


@router.websocket("/ws")
@router.websocket("/ws/stream/{path_session_id}")
async def form_analysis_websocket(
    websocket: WebSocket,
    path_session_id: Optional[str] = None,
    exercise_id: Optional[str] = Query("squat"),
    session_id: Optional[str] = Query(None),
    token: Optional[str] = Query(None),
):
    """
    Dedicated full-duplex WebSocket endpoint for real-time form analysis streaming.
    """
    # 1. Authenticate WebSocket connection
    uid = await authenticate_ws_token(websocket, token)
    if uid is None:
        return  # Closed in authenticate_ws_token

    mgr = get_session_manager()
    stream_service = get_stream_service()
    effective_session_id = path_session_id or session_id

    # 2. Resolve or Create In-Memory Session
    session: Optional[FormAnalysisSession] = None
    if effective_session_id:
        session = mgr.get_session(effective_session_id)
        if session is None:
            await websocket.close(
                code=status.WS_1008_POLICY_VIOLATION,
                reason="Session not found or expired",
            )
            return
    else:
        # Create a new session for the exercise
        target_exercise = exercise_id or "squat"
        try:
            session = mgr.create_session(
                exercise_id=target_exercise,
                client_metadata={"authenticated_uid": uid},
            )
        except InvalidExerciseError as exc:
            await websocket.close(
                code=status.WS_1008_POLICY_VIOLATION,
                reason=f"Unsupported exercise: {exc}",
            )
            return
        except SessionLimitExceededError:
            await websocket.close(
                code=status.WS_1008_POLICY_VIOLATION,
                reason="Maximum concurrent sessions limit reached",
            )
            return

    # 3. Accept WebSocket
    await websocket.accept()

    # Send initial connection ack
    welcome_ack = WSAckMessage(
        type="ack",
        status="connected",
        session_id=session.session_id,
        server_time_ms=time.time() * 1000.0,
    )
    await websocket.send_json(welcome_ack.model_dump(mode="json"))

    # 4. Stream Loop State
    last_processed_seq: int = -1
    last_completed_rep: int = -1
    last_frame_time: float = 0.0
    is_paused: bool = False
    fps_limit = float(getattr(settings, "FORM_MAX_ACCEPTED_FPS", 25))

    try:
        while True:
            message = await websocket.receive()

            # Handle disconnect message
            if message.get("type") == "websocket.disconnect":
                break

            # -----------------------------------------------------------------
            # A. BINARY FRAME MESSAGE
            # -----------------------------------------------------------------
            if "bytes" in message and message["bytes"]:
                raw_bytes = message["bytes"]

                if is_paused:
                    ack = WSAckMessage(
                        type="ack",
                        status="paused",
                        session_id=session.session_id,
                        server_time_ms=time.time() * 1000.0,
                    )
                    await websocket.send_json(ack.model_dump(mode="json"))
                    continue

                # Check if session has expired
                active_session = mgr.get_session(session.session_id)
                if active_session is None:
                    err = WSErrorMessage(
                        type="error",
                        error="Session expired",
                        detail="Session reached idle timeout or absolute duration limit.",
                        code="SESSION_EXPIRED",
                    )
                    await websocket.send_json(err.model_dump(mode="json"))
                    await websocket.close(code=status.WS_1008_POLICY_VIOLATION, reason="Session expired")
                    break

                # FPS enforcement (rate limiting / latest-frame sampling)
                now_perf = time.perf_counter()
                min_interval = 1.0 / fps_limit
                if (now_perf - last_frame_time) < (min_interval - 0.002):
                    ack = WSAckMessage(
                        type="ack",
                        status="dropped_rate_limit",
                        session_id=session.session_id,
                        server_time_ms=time.time() * 1000.0,
                    )
                    await websocket.send_json(ack.model_dump(mode="json"))
                    continue

                # Process Frame through Pipeline
                try:
                    result = stream_service.process_binary_frame(
                        session=session,
                        raw_packet=raw_bytes,
                        last_processed_sequence_id=last_processed_seq,
                        last_completed_rep_emitted=last_completed_rep,
                    )
                    last_processed_seq = result.sequence_id
                    last_frame_time = time.perf_counter()

                    # 1. Send Analysis
                    await websocket.send_json(result.analysis.model_dump(mode="json"))

                    # 2. If repetition completed, emit rep_completed event
                    if result.rep_completed is not None:
                        last_completed_rep = result.rep_completed.rep_number
                        await websocket.send_json(result.rep_completed.model_dump(mode="json"))

                except StreamProtocolError as exc:
                    err = WSErrorMessage(
                        type="error",
                        sequence_id=exc.sequence_id,
                        error=str(exc),
                        code=exc.code,
                    )
                    await websocket.send_json(err.model_dump(mode="json"))
                except Exception as exc:
                    logger.error(f"Unexpected error in frame pipeline: {exc}", exc_info=True)
                    err = WSErrorMessage(
                        type="error",
                        error="Server processing exception",
                        detail=str(exc) if settings.DEBUG else "Internal processing error",
                        code="SERVER_ERROR",
                    )
                    await websocket.send_json(err.model_dump(mode="json"))

            # -----------------------------------------------------------------
            # B. TEXT / JSON CONTROL MESSAGE
            # -----------------------------------------------------------------
            elif "text" in message and message["text"]:
                text_payload = message["text"]
                try:
                    data = json.loads(text_payload)
                except Exception:
                    err = WSErrorMessage(
                        type="error",
                        error="Malformed JSON",
                        detail="Control message could not be parsed as JSON.",
                        code="MALFORMED_JSON",
                    )
                    await websocket.send_json(err.model_dump(mode="json"))
                    continue

                msg_type = str(data.get("type", "")).lower()
                seq_id = data.get("sequence_id") or data.get("sequence")

                if msg_type == "pause":
                    is_paused = True
                    ack = WSAckMessage(
                        type="ack",
                        sequence_id=seq_id,
                        status="paused",
                        session_id=session.session_id,
                        server_time_ms=time.time() * 1000.0,
                    )
                    await websocket.send_json(ack.model_dump(mode="json"))

                elif msg_type == "resume":
                    is_paused = False
                    ack = WSAckMessage(
                        type="ack",
                        sequence_id=seq_id,
                        status="resumed",
                        session_id=session.session_id,
                        server_time_ms=time.time() * 1000.0,
                    )
                    await websocket.send_json(ack.model_dump(mode="json"))

                elif msg_type == "stop":
                    # Phase 9B.7: Deterministic finalization and persistence
                    repo_provider = websocket.app.dependency_overrides.get(
                        get_form_analysis_repository, get_form_analysis_repository
                    )
                    repo = repo_provider()
                    finalized_summary = None

                    if session.rep_count >= 1 or len(session.completed_reps) >= 1:
                        try:
                            summary_schema = repo.build_session_summary(session=session, uid=uid)
                            if summary_schema:
                                saved = repo.save_session_summary(uid, summary_schema)
                                finalized_summary = saved.model_dump(mode="json")
                        except Exception as exc:
                            logger.error(f"Error persisting form analysis session {session.session_id}: {exc}")

                    overall_score = (
                        finalized_summary.get("overall_score")
                        if finalized_summary
                        else (session.session_score_summary.overall_score if session.session_score_summary else None)
                    )

                    stopped_msg = WSStoppedMessage(
                        type="stopped",
                        session_id=session.session_id,
                        rep_count=session.rep_count,
                        overall_score=overall_score,
                        summary=finalized_summary if finalized_summary else session.to_summary_dict(),
                    )
                    await websocket.send_json(stopped_msg.model_dump(mode="json"))
                    mgr.close_session(session.session_id)
                    await websocket.close(code=status.WS_1000_NORMAL_CLOSURE)
                    break

                elif msg_type == "ping":
                    pong = WSPongMessage(
                        type="pong",
                        sequence_id=seq_id,
                        client_timestamp_ms=data.get("timestamp_ms"),
                        server_timestamp_ms=time.time() * 1000.0,
                    )
                    await websocket.send_json(pong.model_dump(mode="json"))

                else:
                    err = WSErrorMessage(
                        type="error",
                        sequence_id=seq_id,
                        error=f"Unknown control message type '{msg_type}'",
                        detail="Supported control types: pause, resume, stop, ping.",
                        code="UNKNOWN_CONTROL_MESSAGE",
                    )
                    await websocket.send_json(err.model_dump(mode="json"))

    except WebSocketDisconnect:
        logger.info(f"WebSocket client disconnected: session={session.session_id}")
    except Exception as e:
        logger.warning(f"WebSocket connection exception: {e}")
    finally:
        # Guarantee session eviction on disconnect
        if session:
            mgr.close_session(session.session_id)
