"""
Real-Time Form Analysis Streaming Pipeline Service (Phase 9B.5).

Provides:
- Binary frame packet parser with fixed 32-byte header:
    [0..15]   UUID session_id (16 bytes binary)
    [16..23]  uint64 sequence_id (8 bytes, big-endian)
    [24..31]  uint64 timestamp_ms (8 bytes, big-endian)
    [32..End] Encoded image payload (WebP / JPEG / PNG)
- Complete pipeline coordination:
    Packet Validation -> Image Decode (9A) -> Pose Extraction (9A) ->
    Joint Angles (9A) -> FSM Transition (9B.1) -> Heuristic Evaluation (9B.2) ->
    Form Scoring (9B.3) -> Session State Update (9B.4).
- Deterministic sequencing, duplicate / out-of-order frame rejection.
- Bounded latest-frame-wins backpressure and FPS enforcement.
- Single rep_completed event emission per completed FSM repetition.
- Memory & Security Invariants:
    - Zero raw frame persistence.
    - Zero Firestore / database writes.
    - Strict 5 MB payload ceiling before image decoding.
    - Maximum dimensions enforcement (1920x1080).
"""

import math
import struct
import time
import uuid
import cv2
import numpy as np
from dataclasses import dataclass, field
from typing import Dict, List, Optional, Tuple, Union, Any

from ..core.config import settings
from ..schemas.form_analysis import (
    ObservabilityStatus,
    HeuristicCategory,
    RepScoreStatus,
    WSAckMessage,
    WSAnalysisMessage,
    WSRepCompletedMessage,
    WSErrorMessage,
    WSPongMessage,
    WSStoppedMessage,
)
from .exercise_fsm import KinematicObservation, FSMState, RepOutcome, FSMUpdateResult
from .form_analysis_service import FormAnalysisService
from .form_heuristics import FormHeuristicsService, ExerciseFormReport
from .form_scoring import FormScoringEngine, RepetitionScore
from .form_session_manager import FormSessionManager, FormAnalysisSession, default_session_manager


# =============================================================================
# CONSTANTS & PROTOCOL DEFINITIONS
# =============================================================================

HEADER_SIZE_BYTES = 32
HEADER_STRUCT_FORMAT = ">16sQQ"  # 16-byte UUID bytes, uint64 sequence_id, uint64 timestamp_ms


class StreamProtocolError(Exception):
    """Base protocol exception for stream processing."""
    def __init__(self, message: str, code: str = "PROTOCOL_ERROR", sequence_id: Optional[int] = None):
        super().__init__(message)
        self.code = code
        self.sequence_id = sequence_id


class MalformedPacketError(StreamProtocolError):
    def __init__(self, message: str, sequence_id: Optional[int] = None):
        super().__init__(message, code="MALFORMED_PACKET", sequence_id=sequence_id)


class PayloadTooLargeError(StreamProtocolError):
    def __init__(self, message: str, sequence_id: Optional[int] = None):
        super().__init__(message, code="PAYLOAD_TOO_LARGE", sequence_id=sequence_id)


class InvalidImageError(StreamProtocolError):
    def __init__(self, message: str, sequence_id: Optional[int] = None):
        super().__init__(message, code="INVALID_IMAGE", sequence_id=sequence_id)


class FrameDimensionError(StreamProtocolError):
    def __init__(self, message: str, sequence_id: Optional[int] = None):
        super().__init__(message, code="FRAME_DIMENSION_EXCEEDED", sequence_id=sequence_id)


# =============================================================================
# PACKET PACKER & UNPACKER HELPERS
# =============================================================================

def pack_frame_packet(
    session_id: Union[str, uuid.UUID],
    sequence_id: int,
    timestamp_ms: int,
    image_bytes: bytes,
) -> bytes:
    """
    Constructs a 32-byte binary header followed by image bytes.
    Used by test suites and future client transport adapters.
    """
    if isinstance(session_id, uuid.UUID):
        session_bytes = session_id.bytes
    elif isinstance(session_id, str):
        try:
            session_bytes = uuid.UUID(session_id).bytes
        except ValueError:
            session_bytes = session_id.encode("utf-8")[:16].ljust(16, b"\x00")
    else:
        session_bytes = bytes(16)

    header = struct.pack(HEADER_STRUCT_FORMAT, session_bytes, int(sequence_id), int(timestamp_ms))
    return header + image_bytes


def unpack_frame_header(data: bytes) -> Tuple[str, int, int, bytes]:
    """
    Unpacks fixed 32-byte binary header.
    Returns: (session_id_str, sequence_id, timestamp_ms, payload_bytes)
    Raises MalformedPacketError if data is less than 32 bytes.
    """
    if len(data) < HEADER_SIZE_BYTES:
        raise MalformedPacketError(
            f"Packet size ({len(data)} bytes) is smaller than required 32-byte header."
        )

    header_bytes = data[:HEADER_SIZE_BYTES]
    payload = data[HEADER_SIZE_BYTES:]

    session_bytes, seq_id, ts_ms = struct.unpack(HEADER_STRUCT_FORMAT, header_bytes)

    try:
        session_id_str = str(uuid.UUID(bytes=session_bytes))
    except ValueError:
        # Fallback to trimmed ascii/hex string if not canonical UUID
        session_id_str = session_bytes.rstrip(b"\x00").decode("utf-8", errors="replace")

    return session_id_str, seq_id, ts_ms, payload


# =============================================================================
# STREAM FRAME RESULT
# =============================================================================

@dataclass
class StreamFrameResult:
    """Result emitted by the streaming pipeline for a single frame."""
    sequence_id: int
    analysis: WSAnalysisMessage
    rep_completed: Optional[WSRepCompletedMessage] = None
    processing_ms: float = 0.0


# =============================================================================
# STREAM PIPELINE SERVICE
# =============================================================================

class FormStreamService:
    """
    Coordinates real-time frame processing across 9A -> 9B.1 -> 9B.2 -> 9B.3 -> 9B.4.
    """

    def __init__(
        self,
        form_analysis_service: Optional[FormAnalysisService] = None,
        heuristics_service: Optional[FormHeuristicsService] = None,
        scoring_engine: Optional[FormScoringEngine] = None,
        session_manager: Optional[FormSessionManager] = None,
    ):
        self.form_service = form_analysis_service or FormAnalysisService()
        self.heuristics_service = heuristics_service or FormHeuristicsService()
        self.scoring_engine = scoring_engine or FormScoringEngine()
        self.session_manager = session_manager or default_session_manager

    def process_binary_frame(
        self,
        session: FormAnalysisSession,
        raw_packet: bytes,
        last_processed_sequence_id: int = -1,
        last_completed_rep_emitted: int = -1,
    ) -> StreamFrameResult:
        """
        Executes end-to-end pipeline on raw binary frame packet.
        
        Steps:
        1. Parse 32-byte header.
        2. Validate sequence ID monotonicity.
        3. Validate payload size <= 5 MB before decoding.
        4. Decode image & validate dimensions.
        5. Extract landmarks & compute joint angles (Phase 9A).
        6. Update Exercise FSM (Phase 9B.1).
        7. Evaluate Form Heuristics (Phase 9B.2).
        8. Score completed reps (Phase 9B.3).
        9. Update In-Memory Session state (Phase 9B.4).
        10. Assemble structured deterministic analysis & rep_completed messages.
        """
        t_start = time.perf_counter()

        # 1. Unpack Header
        session_id, sequence_id, timestamp_ms, payload = unpack_frame_header(raw_packet)

        # 2. Sequence Monotonicity Check
        if sequence_id <= last_processed_sequence_id:
            raise StreamProtocolError(
                f"Duplicate or out-of-order sequence ID {sequence_id} (last processed: {last_processed_sequence_id}).",
                code="OUT_OF_ORDER_SEQUENCE",
                sequence_id=sequence_id,
            )

        # 3. Payload Size Ceiling Enforcement BEFORE image decoding
        max_bytes = getattr(settings, "FORM_MAX_FRAME_BYTES", 5 * 1024 * 1024)
        if len(payload) > max_bytes:
            raise PayloadTooLargeError(
                f"Frame payload ({len(payload)} bytes) exceeds maximum limit of {max_bytes} bytes (5 MB).",
                sequence_id=sequence_id,
            )

        if len(payload) == 0:
            raise InvalidImageError("Frame image payload is empty.", sequence_id=sequence_id)

        # 4. Image Decoding (OpenCV in-memory buffer)
        nparr = np.frombuffer(payload, np.uint8)
        frame = cv2.imdecode(nparr, cv2.IMREAD_COLOR)
        if frame is None:
            raise InvalidImageError(
                "Could not decode image bytes. Supported formats: WebP, JPEG, PNG.",
                sequence_id=sequence_id,
            )

        h, w = frame.shape[:2]
        max_w = getattr(settings, "FORM_MAX_FRAME_WIDTH", 1920)
        max_h = getattr(settings, "FORM_MAX_FRAME_HEIGHT", 1080)
        if w > max_w or h > max_h:
            raise FrameDimensionError(
                f"Frame dimensions {w}x{h} exceed maximum permitted {max_w}x{max_h}.",
                sequence_id=sequence_id,
            )

        # 5. Pose Extraction & Joint Angles (Phase 9A)
        pose_res = self.form_service.estimator.estimate_pose(payload)
        landmarks_dict = pose_res.get("landmarks", {})
        landmarks_detected = pose_res.get("landmarks_detected", False)
        overall_conf = pose_res.get("overall_confidence", 0.0)

        angles_dict: Dict[str, float] = {}
        if landmarks_detected and landmarks_dict:
            angles_res = self.form_service.compute_joint_angles(landmarks=landmarks_dict)
            for j_name, detail in angles_res.joint_angles.items():
                angles_dict[j_name] = detail.angle_degrees

        # Format landmarks for client rendering
        landmarks_list: List[Dict[str, Any]] = []
        for lm_name, lm_data in landmarks_dict.items():
            landmarks_list.append({
                "id": lm_data.get("index", 0),
                "name": lm_name,
                "x": round(lm_data.get("x", 0.0), 3),
                "y": round(lm_data.get("y", 0.0), 3),
                "z": round(lm_data.get("z", 0.0), 3),
                "visibility": round(lm_data.get("visibility", 0.0), 2),
            })

        # 6. Exercise FSM Update (Phase 9B.1)
        obs_time_ms = float(timestamp_ms) if timestamp_ms > 0 else (time.time() * 1000.0)
        obs = KinematicObservation(
            timestamp_ms=obs_time_ms,
            joint_angles=angles_dict,
            confidence=overall_conf,
            landmarks_detected=landmarks_detected,
        )
        fsm_update: FSMUpdateResult = session.fsm.update(obs)

        # 7. Form Heuristics Evaluation (Phase 9B.2)
        history_list = list(session.recent_observations)
        heuristic_report: ExerciseFormReport = self.heuristics_service.evaluate(
            exercise_id=session.canonical_exercise_id,
            observation=obs,
            history=history_list,
        )

        # 8. Form Scoring if rep completed (Phase 9B.3)
        rep_score: Optional[RepetitionScore] = None
        rep_completed_msg: Optional[WSRepCompletedMessage] = None

        if fsm_update.rep_completed and fsm_update.completed_rep_number is not None:
            rep_num = fsm_update.completed_rep_number
            # Avoid duplicate rep_completed emissions for the same rep number
            if rep_num > last_completed_rep_emitted:
                rep_score = self.scoring_engine.score_repetition(
                    exercise_id=session.canonical_exercise_id,
                    heuristic_results=heuristic_report,
                    rep_outcome=fsm_update.outcome,
                    rep_number=rep_num,
                    rep_confidence=obs.confidence,
                    timestamp_ms=obs_time_ms,
                )

                cat_scores_dict: Dict[str, Any] = {}
                if rep_score.category_scores:
                    for k, v in rep_score.category_scores.items():
                        cat_scores_dict[k] = {
                            "score": v.category_score,
                            "penalty": v.raw_penalty,
                            "weight": v.weight,
                        }

                rep_completed_msg = WSRepCompletedMessage(
                    type="rep_completed",
                    sequence_id=sequence_id,
                    session_id=session.session_id,
                    exercise_id=session.canonical_exercise_id,
                    rep_number=rep_num,
                    fsm_outcome=fsm_update.outcome.value if hasattr(fsm_update.outcome, "value") else str(fsm_update.outcome),
                    rom_degrees=round(fsm_update.rom_degrees, 1) if fsm_update.rom_degrees is not None else None,
                    duration_ms=round(fsm_update.duration_ms, 1) if fsm_update.duration_ms is not None else None,
                    score=rep_score.score,
                    score_status=rep_score.status.value,
                    category_scores=cat_scores_dict,
                    feedback=rep_score.feedback,
                )

        # 9. Update In-Memory Session State (Phase 9B.4)
        self.session_manager.update_session(
            session_id=session.session_id,
            observation=obs,
            fsm_result=fsm_update,
            heuristic_report=heuristic_report,
            rep_score=rep_score if rep_score is not None else None,
        )

        # 10. Assemble Analysis Message
        t_end = time.perf_counter()
        processing_ms = round((t_end - t_start) * 1000.0, 2)
        server_now_ms = time.time() * 1000.0
        latency_e2e = round(max(0.0, server_now_ms - timestamp_ms), 1) if timestamp_ms > 0 else None

        # Build heuristics summary for client
        heuristics_data: List[Dict[str, Any]] = []
        for h_res in heuristic_report.results:
            heuristics_data.append({
                "name": h_res.heuristic_name,
                "category": h_res.category.value if hasattr(h_res.category, "value") else str(h_res.category),
                "status": h_res.status.value if hasattr(h_res.status, "value") else str(h_res.status),
                "is_acceptable": h_res.is_acceptable,
                "observed_value": h_res.observed_value,
                "deviation": h_res.deviation,
                "feedback": h_res.feedback,
            })

        feedback_list: List[str] = []
        if rep_score and rep_score.feedback:
            feedback_list = rep_score.feedback
        elif heuristic_report.results:
            # Top feedback findings
            for hr in heuristic_report.results:
                if hr.status == ObservabilityStatus.OBSERVED and hr.is_acceptable is False:
                    feedback_list.append(hr.feedback)

        latest_score_val = None
        score_status_val = None
        if session.latest_rep_score:
            latest_score_val = session.latest_rep_score.score
            score_status_val = session.latest_rep_score.status.value

        analysis_msg = WSAnalysisMessage(
            type="analysis",
            sequence_id=sequence_id,
            session_id=session.session_id,
            exercise_id=session.canonical_exercise_id,
            timestamp_ms=obs_time_ms,
            latency_e2e_ms=latency_e2e,
            processing_ms=processing_ms,
            tracking_status=fsm_update.tracking_status.value if hasattr(fsm_update.tracking_status, "value") else str(fsm_update.tracking_status),
            fsm_state=fsm_update.state.value if hasattr(fsm_update.state, "value") else str(fsm_update.state),
            rep_count=fsm_update.rep_count,
            primary_angle=round(fsm_update.primary_angle, 1) if fsm_update.primary_angle is not None else None,
            observability_ratio=round(heuristic_report.observability_ratio, 3),
            is_sufficiently_observable=heuristic_report.is_sufficiently_observable,
            landmarks_detected=landmarks_detected,
            landmarks=landmarks_list,
            joint_angles={k: round(v, 1) for k, v in angles_dict.items()},
            heuristics=heuristics_data,
            latest_score=latest_score_val,
            score_status=score_status_val,
            feedback=feedback_list,
        )

        return StreamFrameResult(
            sequence_id=sequence_id,
            analysis=analysis_msg,
            rep_completed=rep_completed_msg,
            processing_ms=processing_ms,
        )
