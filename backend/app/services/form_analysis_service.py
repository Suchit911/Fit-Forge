"""
Form Analysis Service (Phase 9A).

Coordinates:
- Pose landmark extraction from image bytes/base64.
- Deterministic joint angle calculation via geometry_utils.
- Stateless baseline session configuration for supported exercises.
- Zero-leak, in-memory frame processing.
"""

import base64
import time
from typing import Dict, Any, List, Optional
from fastapi import HTTPException, status

from ..core.config import settings
from ..schemas.form_analysis import (
    PoseExtractionResponse,
    NormalizedLandmarkSchema,
    BoundingBoxSchema,
    EstimatedBodyCenterSchema,
    JointAnglesResponse,
    JointAngleResultSchema,
    FormAnalysisSessionSchema,
    KeyMetricItemSchema,
    FormBreakdownItemSchema,
    MuscleActivationItemSchema,
    RepAnalysisItemSchema,
    AnalysisHistoryItemSchema,
)
from .pose_estimator import BasePoseEstimator, MediaPipePoseEstimator, MockPoseEstimator
from . import geometry_utils
from ..utils.logger import logger

# Baseline Exercise Metadata Catalog (Stateless Configuration)
EXERCISE_METADATA_CATALOG: Dict[str, Dict[str, Any]] = {
    "ex_bench_press": {
        "exerciseName": "Bench Press",
        "setInfo": "Set 1 of 3",
        "weightKg": 60.0,
        "reps": 0,
        "rpe": 7.0,
        "restTime": "01:30 Rest",
        "formScore": 0.0,
        "formStatus": "Ready",
        "analysisTime": "00:00",
        "confidence": "Optimal",
        "videoAssetUrl": "/assets/dashboard_push_lifter.jpg",
        "keyMetrics": [
            {"name": "Range of Motion", "score": 0.0, "status": "Good", "trendData": []},
            {"name": "Bar Path", "score": 0.0, "status": "Good", "trendData": []},
            {"name": "Elbow Flare", "score": 0.0, "status": "Good", "trendData": []},
            {"name": "Stability", "score": 0.0, "status": "Good", "trendData": []},
        ],
        "scoreBreakdown": [
            {"metric": "Range of Motion", "score": 0.0},
            {"metric": "Bar Path", "score": 0.0},
            {"metric": "Stability", "score": 0.0},
        ],
        "muscleActivation": [
            {"name": "Chest", "activationPct": 0.0, "category": "primary"},
            {"name": "Triceps", "activationPct": 0.0, "category": "secondary"},
            {"name": "Shoulders", "activationPct": 0.0, "category": "secondary"},
        ],
        "positiveFeedback": ["Setup looks stable. Ready to begin set."],
        "improvementFeedback": [],
        "infoFeedback": ["Keep wrists stacked over elbows throughout movement."],
        "coachingTips": [
            "Tuck elbows at a 45° angle from torso.",
            "Lower the bar to mid-chest under control.",
            "Drive feet into the floor for leg drive.",
        ],
    },
    "ex_squat": {
        "exerciseName": "Barbell Squat",
        "setInfo": "Set 1 of 3",
        "weightKg": 80.0,
        "reps": 0,
        "rpe": 7.5,
        "restTime": "02:00 Rest",
        "formScore": 0.0,
        "formStatus": "Ready",
        "analysisTime": "00:00",
        "confidence": "Optimal",
        "videoAssetUrl": "/assets/dashboard_push_lifter.jpg",
        "keyMetrics": [
            {"name": "Squat Depth", "score": 0.0, "status": "Good", "trendData": []},
            {"name": "Knee Tracking", "score": 0.0, "status": "Good", "trendData": []},
            {"name": "Torso Angle", "score": 0.0, "status": "Good", "trendData": []},
            {"name": "Balance", "score": 0.0, "status": "Good", "trendData": []},
        ],
        "scoreBreakdown": [
            {"metric": "Squat Depth", "score": 0.0},
            {"metric": "Knee Tracking", "score": 0.0},
            {"metric": "Torso Angle", "score": 0.0},
        ],
        "muscleActivation": [
            {"name": "Quadriceps", "activationPct": 0.0, "category": "primary"},
            {"name": "Glutes", "activationPct": 0.0, "category": "primary"},
            {"name": "Hamstrings", "activationPct": 0.0, "category": "secondary"},
            {"name": "Core", "activationPct": 0.0, "category": "stabilizer"},
        ],
        "positiveFeedback": ["Stance width is optimal. Ready to begin set."],
        "improvementFeedback": [],
        "infoFeedback": ["Descend until hip crease is below top of knees."],
        "coachingTips": [
            "Keep chest proud and eyes forward.",
            "Push knees outward in line with toes.",
            "Maintain full foot contact with the floor.",
        ],
    },
}


class FormAnalysisService:
    """Core domain service for AI Form Analysis foundation."""

    def __init__(self, estimator: Optional[BasePoseEstimator] = None):
        if estimator is not None:
            self.estimator = estimator
        elif settings.CV_USE_MOCK:
            self.estimator = MockPoseEstimator()
        else:
            mp_estimator = MediaPipePoseEstimator()
            if mp_estimator.is_ready():
                self.estimator = mp_estimator
            else:
                logger.warning("MediaPipe model not ready. FormAnalysisService defaulting to MockPoseEstimator.")
                self.estimator = MockPoseEstimator()

    def extract_pose_from_bytes(self, image_bytes: bytes) -> PoseExtractionResponse:
        """
        Validates payload size and extracts landmarks from raw image bytes.
        Enforces 5 MB payload limit before expensive image processing.
        """
        if len(image_bytes) > settings.CV_MAX_IMAGE_SIZE_BYTES:
            raise HTTPException(
                status_code=status.HTTP_413_REQUEST_ENTITY_TOO_LARGE,
                detail=f"Image payload exceeds maximum allowed limit of {settings.CV_MAX_IMAGE_SIZE_BYTES} bytes (5 MB).",
            )

        if not image_bytes:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Empty image payload provided.",
            )

        raw_result = self.estimator.estimate_pose(image_bytes)

        landmarks_dict: Dict[str, NormalizedLandmarkSchema] = {}
        for k, v in raw_result.get("landmarks", {}).items():
            landmarks_dict[k] = NormalizedLandmarkSchema(**v)

        bbox_data = raw_result.get("bounding_box")
        bbox = BoundingBoxSchema(**bbox_data) if bbox_data else None

        # Estimated body centroid approximation (Correction #4)
        body_center = None
        if landmarks_dict:
            center_data = geometry_utils.calculate_estimated_body_center(landmarks_dict)
            if center_data:
                body_center = EstimatedBodyCenterSchema(**center_data)

        return PoseExtractionResponse(
            landmarks_detected=raw_result.get("landmarks_detected", False),
            landmark_count=raw_result.get("landmark_count", 0),
            landmarks=landmarks_dict,
            bounding_box=bbox,
            estimated_body_center=body_center,
            overall_confidence=raw_result.get("overall_confidence", 0.0),
            processing_time_ms=raw_result.get("processing_time_ms", 0.0),
        )

    def extract_pose_from_base64(self, image_base64: str) -> PoseExtractionResponse:
        """Extracts landmarks from base64 encoded image string."""
        if not image_base64:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Base64 image string cannot be empty.",
            )

        # Strip data URI prefix if present (e.g. data:image/jpeg;base64,...)
        clean_b64 = image_base64
        if "," in clean_b64:
            clean_b64 = clean_b64.split(",", 1)[1]

        try:
            image_bytes = base64.b64decode(clean_b64, validate=True)
        except Exception:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Invalid base64 image encoding.",
            )

        return self.extract_pose_from_bytes(image_bytes)

    def compute_joint_angles(
        self,
        landmarks: Dict[str, Any],
        target_joints: Optional[List[str]] = None,
        use_3d: bool = False,
    ) -> JointAnglesResponse:
        """
        Computes joint angles from supplied landmarks dictionary.
        Separated cleanly from image extraction (Correction #6).
        """
        start_time = time.perf_counter()

        if not landmarks:
            return JointAnglesResponse(
                landmarks_detected=False,
                joint_angles={},
                overall_confidence=0.0,
                processing_time_ms=round((time.perf_counter() - start_time) * 1000, 2),
            )

        angles_data, overall_conf = geometry_utils.compute_standard_joint_angles(
            landmarks=landmarks,
            confidence_threshold=settings.CV_MIN_TRACKING_CONFIDENCE,
            target_joints=target_joints,
            use_3d=use_3d,
        )

        joint_angles_dict: Dict[str, JointAngleResultSchema] = {}
        for k, v in angles_data.items():
            joint_angles_dict[k] = JointAngleResultSchema(**v)

        return JointAnglesResponse(
            landmarks_detected=len(joint_angles_dict) > 0,
            joint_angles=joint_angles_dict,
            overall_confidence=overall_conf,
            processing_time_ms=round((time.perf_counter() - start_time) * 1000, 2),
        )

    def get_stateless_session_metadata(self, exercise_id: str) -> FormAnalysisSessionSchema:
        """
        Returns stateless baseline session metadata for an exercise.
        Does NOT create or persist sessions in Firestore or database (Correction #7).
        """
        catalog_entry = EXERCISE_METADATA_CATALOG.get(exercise_id)
        if not catalog_entry:
            # Fallback baseline configuration for unlisted exercises
            catalog_entry = {
                "exerciseName": exercise_id.replace("ex_", "").replace("_", " ").title(),
                "setInfo": "Set 1 of 3",
                "weightKg": 50.0,
                "reps": 0,
                "rpe": 7.0,
                "restTime": "01:30 Rest",
                "formScore": 0.0,
                "formStatus": "Ready",
                "analysisTime": "00:00",
                "confidence": "Optimal",
                "videoAssetUrl": "/assets/dashboard_push_lifter.jpg",
                "keyMetrics": [
                    {"name": "Range of Motion", "score": 0.0, "status": "Good", "trendData": []},
                    {"name": "Form Alignment", "score": 0.0, "status": "Good", "trendData": []},
                    {"name": "Stability", "score": 0.0, "status": "Good", "trendData": []},
                ],
                "scoreBreakdown": [
                    {"metric": "Range of Motion", "score": 0.0},
                    {"metric": "Stability", "score": 0.0},
                ],
                "muscleActivation": [
                    {"name": "Primary Muscle", "activationPct": 0.0, "category": "primary"},
                ],
                "positiveFeedback": ["Ready to begin set."],
                "improvementFeedback": [],
                "infoFeedback": ["Focus on controlled tempo."],
                "coachingTips": ["Maintain proper breathing."],
            }

        return FormAnalysisSessionSchema(
            exerciseId=exercise_id,
            exerciseName=catalog_entry["exerciseName"],
            setInfo=catalog_entry["setInfo"],
            weightKg=catalog_entry["weightKg"],
            reps=catalog_entry["reps"],
            rpe=catalog_entry["rpe"],
            restTime=catalog_entry["restTime"],
            formScore=catalog_entry["formScore"],
            formStatus=catalog_entry["formStatus"],
            analysisTime=catalog_entry["analysisTime"],
            confidence=catalog_entry["confidence"],
            videoAssetUrl=catalog_entry["videoAssetUrl"],
            keyMetrics=[KeyMetricItemSchema(**m) for m in catalog_entry["keyMetrics"]],
            scoreBreakdown=[FormBreakdownItemSchema(**s) for s in catalog_entry["scoreBreakdown"]],
            muscleActivation=[MuscleActivationItemSchema(**a) for a in catalog_entry["muscleActivation"]],
            positiveFeedback=catalog_entry["positiveFeedback"],
            improvementFeedback=catalog_entry["improvementFeedback"],
            infoFeedback=catalog_entry["infoFeedback"],
            coachingTips=catalog_entry["coachingTips"],
            repProgress=[],
            history=[],
        )
