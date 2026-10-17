"""
Pose Estimation Abstraction and Implementations (Phase 9A).

Defines:
- BasePoseEstimator: Abstract interface for pose estimation engines.
- MediaPipePoseEstimator: Production implementation using Google MediaPipe Tasks Vision.
- MockPoseEstimator: Deterministic mock implementation for offline unit testing and CI/CD.
"""

from abc import ABC, abstractmethod
import os
import threading
import time
from typing import Dict, Any, List, Optional
import numpy as np
import cv2

from ..core.config import settings
from ..utils.logger import logger

# Canonical MediaPipe 33 Landmark Names in Index Order
POSE_LANDMARK_NAMES: List[str] = [
    "NOSE",
    "LEFT_EYE_INNER",
    "LEFT_EYE",
    "LEFT_EYE_OUTER",
    "RIGHT_EYE_INNER",
    "RIGHT_EYE",
    "RIGHT_EYE_OUTER",
    "LEFT_EAR",
    "RIGHT_EAR",
    "MOUTH_LEFT",
    "MOUTH_RIGHT",
    "LEFT_SHOULDER",
    "RIGHT_SHOULDER",
    "LEFT_ELBOW",
    "RIGHT_ELBOW",
    "LEFT_WRIST",
    "RIGHT_WRIST",
    "LEFT_PINKY",
    "RIGHT_PINKY",
    "LEFT_INDEX",
    "RIGHT_INDEX",
    "LEFT_THUMB",
    "RIGHT_THUMB",
    "LEFT_HIP",
    "RIGHT_HIP",
    "LEFT_KNEE",
    "RIGHT_KNEE",
    "LEFT_ANKLE",
    "RIGHT_ANKLE",
    "LEFT_HEEL",
    "RIGHT_HEEL",
    "LEFT_FOOT_INDEX",
    "RIGHT_FOOT_INDEX",
]


class BasePoseEstimator(ABC):
    """Abstract interface for pose landmark extraction providers."""

    @abstractmethod
    def is_ready(self) -> bool:
        """Returns True if the engine is initialized and ready for inference."""
        pass

    @abstractmethod
    def estimate_pose(self, image_bytes: bytes) -> Dict[str, Any]:
        """
        Extracts pose landmarks from encoded image bytes (JPEG, PNG, WebP).
        Returns a standardized dictionary containing detection status, landmarks,
        and bounding box.
        """
        pass

    @abstractmethod
    def estimate_pose_from_array(self, image_bgr: np.ndarray) -> Dict[str, Any]:
        """Extracts pose landmarks from an in-memory BGR numpy array."""
        pass


class MediaPipePoseEstimator(BasePoseEstimator):
    """
    Production implementation of BasePoseEstimator using MediaPipe Tasks Vision.
    Executes entirely on-premise on CPU/GPU without external cloud requests.
    """

    def __init__(
        self,
        model_path: Optional[str] = None,
        min_detection_confidence: float = 0.5,
        min_tracking_confidence: float = 0.5,
    ):
        self.min_detection_confidence = min_detection_confidence
        self.min_tracking_confidence = min_tracking_confidence
        self._lock = threading.Lock()
        self._landmarker = None

        # Resolve model path
        resolved_path = model_path or settings.CV_MODEL_PATH
        if not os.path.isabs(resolved_path):
            base_dir = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", ".."))
            candidates = [
                os.path.join(base_dir, resolved_path),
                os.path.join(base_dir, "models", "pose_landmarker_lite.task"),
                os.path.abspath(resolved_path),
            ]
            self.model_path = next((c for c in candidates if os.path.isfile(c)), resolved_path)
        else:
            self.model_path = resolved_path

        self._initialize_engine()

    def _initialize_engine(self) -> None:
        """Initializes the MediaPipe Tasks PoseLandmarker."""
        if not os.path.isfile(self.model_path):
            logger.warning(
                f"MediaPipe pose model not found at path: {self.model_path}. "
                "MediaPipePoseEstimator running in unready state."
            )
            self._landmarker = None
            return

        try:
            import mediapipe as mp
            from mediapipe.tasks.python import vision
            from mediapipe.tasks.python.core.base_options import BaseOptions

            options = vision.PoseLandmarkerOptions(
                base_options=BaseOptions(model_asset_path=self.model_path),
                running_mode=vision.RunningMode.IMAGE,
                min_pose_detection_confidence=self.min_detection_confidence,
                min_pose_presence_confidence=self.min_detection_confidence,
                min_tracking_confidence=self.min_tracking_confidence,
                num_poses=1,
            )
            self._landmarker = vision.PoseLandmarker.create_from_options(options)
            logger.info("MediaPipe Tasks PoseLandmarker initialized successfully.")
        except Exception as e:
            logger.error(f"Failed to initialize MediaPipe PoseLandmarker: {e}")
            self._landmarker = None

    def is_ready(self) -> bool:
        return self._landmarker is not None

    def estimate_pose(self, image_bytes: bytes) -> Dict[str, Any]:
        """Decodes image bytes and estimates pose landmarks."""
        if not image_bytes:
            return self._empty_response(0.0)

        # Enforce image payload size check
        if len(image_bytes) > settings.CV_MAX_IMAGE_SIZE_BYTES:
            raise ValueError(
                f"Image payload exceeds maximum allowed size of {settings.CV_MAX_IMAGE_SIZE_BYTES} bytes."
            )

        start_time = time.perf_counter()
        try:
            # Decode in-memory without disk write
            np_arr = np.frombuffer(image_bytes, np.uint8)
            img_bgr = cv2.imdecode(np_arr, cv2.IMREAD_COLOR)
            if img_bgr is None:
                return self._empty_response(round((time.perf_counter() - start_time) * 1000, 2))

            return self.estimate_pose_from_array(img_bgr)
        except ValueError:
            raise
        except Exception as e:
            logger.error(f"Error decoding image for pose estimation: {e}")
            return self._empty_response(round((time.perf_counter() - start_time) * 1000, 2))

    def estimate_pose_from_array(self, image_bgr: np.ndarray) -> Dict[str, Any]:
        """Runs MediaPipe inference on BGR image array."""
        start_time = time.perf_counter()

        if not self.is_ready() or image_bgr is None or image_bgr.size == 0:
            return self._empty_response(round((time.perf_counter() - start_time) * 1000, 2))

        try:
            # Downscale if image exceeds max dimension to bound compute latency
            h, w = image_bgr.shape[:2]
            max_dim = settings.CV_MAX_IMAGE_DIMENSION
            if max(h, w) > max_dim:
                scale = max_dim / max(h, w)
                new_w, new_h = int(w * scale), int(h * scale)
                image_bgr = cv2.resize(image_bgr, (new_w, new_h), interpolation=cv2.INTER_AREA)

            # Convert BGR to RGB
            img_rgb = cv2.cvtColor(image_bgr, cv2.COLOR_BGR2RGB)

            import mediapipe as mp
            mp_image = mp.Image(image_format=mp.ImageFormat.SRGB, data=img_rgb)

            # Thread-safe detection execution
            with self._lock:
                detection_result = self._landmarker.detect(mp_image)

            duration_ms = round((time.perf_counter() - start_time) * 1000, 2)

            if not detection_result.pose_landmarks or len(detection_result.pose_landmarks) == 0:
                return self._empty_response(duration_ms)

            # Extract the primary detected pose
            primary_pose = detection_result.pose_landmarks[0]
            landmarks_dict: Dict[str, Any] = {}
            visibilities: List[float] = []

            x_coords, y_coords = [], []

            for idx, lm in enumerate(primary_pose):
                name = POSE_LANDMARK_NAMES[idx] if idx < len(POSE_LANDMARK_NAMES) else f"LANDMARK_{idx}"
                vis = float(getattr(lm, "visibility", 1.0) if getattr(lm, "visibility", None) is not None else 1.0)
                pres = float(getattr(lm, "presence", 1.0) if getattr(lm, "presence", None) is not None else 1.0)

                x = float(lm.x)
                y = float(lm.y)
                z = float(getattr(lm, "z", 0.0))

                landmarks_dict[name] = {
                    "index": idx,
                    "name": name,
                    "x": round(x, 4),
                    "y": round(y, 4),
                    "z": round(z, 4),
                    "visibility": round(vis, 4),
                    "presence": round(pres, 4),
                }
                visibilities.append(vis)
                x_coords.append(x)
                y_coords.append(y)

            # Calculate bounding box
            x_min, x_max = max(0.0, min(x_coords)), min(1.0, max(x_coords))
            y_min, y_max = max(0.0, min(y_coords)), min(1.0, max(y_coords))
            bbox = {
                "x_min": round(x_min, 4),
                "y_min": round(y_min, 4),
                "width": round(x_max - x_min, 4),
                "height": round(y_max - y_min, 4),
            }

            avg_conf = round(sum(visibilities) / len(visibilities), 4) if visibilities else 0.0

            return {
                "landmarks_detected": True,
                "landmark_count": len(landmarks_dict),
                "landmarks": landmarks_dict,
                "bounding_box": bbox,
                "overall_confidence": avg_conf,
                "processing_time_ms": duration_ms,
            }

        except Exception as e:
            logger.error(f"MediaPipe pose estimation execution error: {e}")
            duration_ms = round((time.perf_counter() - start_time) * 1000, 2)
            return self._empty_response(duration_ms)

    def _empty_response(self, processing_time_ms: float) -> Dict[str, Any]:
        return {
            "landmarks_detected": False,
            "landmark_count": 0,
            "landmarks": {},
            "bounding_box": None,
            "overall_confidence": 0.0,
            "processing_time_ms": processing_time_ms,
        }


class MockPoseEstimator(BasePoseEstimator):
    """
    Deterministic mock implementation of BasePoseEstimator.
    Used for automated unit testing, CI/CD, and offline verification with zero external assets.
    """

    def __init__(self, default_preset: str = "standing"):
        self.preset = default_preset
        self.detection_enabled = True

    def is_ready(self) -> bool:
        return True

    def set_preset(self, preset: str) -> None:
        self.preset = preset

    def set_detection_enabled(self, enabled: bool) -> None:
        self.detection_enabled = enabled

    def estimate_pose(self, image_bytes: bytes) -> Dict[str, Any]:
        if len(image_bytes) > settings.CV_MAX_IMAGE_SIZE_BYTES:
            raise ValueError(
                f"Image payload exceeds maximum allowed size of {settings.CV_MAX_IMAGE_SIZE_BYTES} bytes."
            )
        return self._generate_preset_response()

    def estimate_pose_from_array(self, image_bgr: np.ndarray) -> Dict[str, Any]:
        return self._generate_preset_response()

    def _generate_preset_response(self) -> Dict[str, Any]:
        if not self.detection_enabled:
            return {
                "landmarks_detected": False,
                "landmark_count": 0,
                "landmarks": {},
                "bounding_box": None,
                "overall_confidence": 0.0,
                "processing_time_ms": 1.2,
            }

        landmarks: Dict[str, Any] = {}

        # Preset joint angle configurations
        if self.preset == "squat":
            # Knee flexed ~90 degrees
            hip_y, knee_y, ankle_y = 0.55, 0.70, 0.90
            knee_x = 0.58
        elif self.preset == "bench_press":
            # Elbow flexed ~90 degrees
            hip_y, knee_y, ankle_y = 0.50, 0.70, 0.90
            knee_x = 0.50
        else:
            # Standing upright: straight legs and arms
            hip_y, knee_y, ankle_y = 0.50, 0.72, 0.92
            knee_x = 0.45

        # Populate all 33 canonical landmarks
        for idx, name in enumerate(POSE_LANDMARK_NAMES):
            # Default coordinates
            x, y, z = 0.50, 0.50, 0.0
            vis = 0.95

            # Key torso/limb positions
            if name == "NOSE":
                x, y = 0.50, 0.15
            elif name == "LEFT_SHOULDER":
                x, y = 0.42, 0.28
            elif name == "RIGHT_SHOULDER":
                x, y = 0.58, 0.28
            elif name == "LEFT_ELBOW":
                x, y = (0.35, 0.42) if self.preset != "bench_press" else (0.32, 0.35)
            elif name == "RIGHT_ELBOW":
                x, y = (0.65, 0.42) if self.preset != "bench_press" else (0.68, 0.35)
            elif name == "LEFT_WRIST":
                x, y = (0.32, 0.55) if self.preset != "bench_press" else (0.32, 0.25)
            elif name == "RIGHT_WRIST":
                x, y = (0.68, 0.55) if self.preset != "bench_press" else (0.68, 0.25)
            elif name == "LEFT_HIP":
                x, y = 0.45, hip_y
            elif name == "RIGHT_HIP":
                x, y = 0.55, hip_y
            elif name == "LEFT_KNEE":
                x, y = knee_x, knee_y
            elif name == "RIGHT_KNEE":
                x, y = 1.0 - knee_x, knee_y
            elif name == "LEFT_ANKLE":
                x, y = 0.44, ankle_y
            elif name == "RIGHT_ANKLE":
                x, y = 0.56, ankle_y

            landmarks[name] = {
                "index": idx,
                "name": name,
                "x": round(x, 4),
                "y": round(y, 4),
                "z": round(z, 4),
                "visibility": round(vis, 4),
                "presence": round(vis, 4),
            }

        return {
            "landmarks_detected": True,
            "landmark_count": len(landmarks),
            "landmarks": landmarks,
            "bounding_box": {
                "x_min": 0.30,
                "y_min": 0.15,
                "width": 0.40,
                "height": 0.77,
            },
            "overall_confidence": 0.95,
            "processing_time_ms": 1.5,
        }
