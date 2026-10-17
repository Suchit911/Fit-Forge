"""
Form Analysis and Computer Vision API Endpoints (Phase 9A).

Endpoints:
- GET /health: Status of the CV inference engine.
- POST /pose/extract: Stateless landmark extraction from image bytes or base64.
- POST /pose/angles: Computation of joint angles from supplied landmarks or image.
- GET /session/{exercise_id}: Stateless exercise metadata and baseline configuration.
"""

from typing import Optional, List
from fastapi import (
    APIRouter,
    Depends,
    File,
    UploadFile,
    Body,
    Request,
    HTTPException,
    status,
    Query,
)

from ....core.config import settings
from ....core.security import get_current_user, CurrentUser
from ....schemas.form_analysis import (
    PoseExtractionResponse,
    JointAnglesRequest,
    JointAnglesResponse,
    FormAnalysisSessionSchema,
    CVEngineHealthSchema,
    FormAnalysisSessionSummarySchema,
    FormAnalysisSessionDetailSchema,
    FinalizeSessionRequest,
)
from ....services.form_analysis_service import FormAnalysisService
from ....services.form_session_manager import default_session_manager
from ....repositories.form_analysis_repository import (
    FormAnalysisRepository,
    get_form_analysis_repository,
)
from ....utils.logger import logger

router = APIRouter()

# Service singleton
_form_service = FormAnalysisService()


def get_form_analysis_service() -> FormAnalysisService:
    return _form_service


@router.get(
    "/health",
    response_model=CVEngineHealthSchema,
    summary="Check Computer Vision Engine Health",
)
def get_cv_health(
    service: FormAnalysisService = Depends(get_form_analysis_service),
) -> CVEngineHealthSchema:
    """Returns operational readiness of the local CV / pose estimation subsystem."""
    engine_name = "MediaPipe Tasks Vision" if service.estimator.is_ready() else "Mock Pose Estimator"
    status_str = "healthy" if service.estimator.is_ready() else "mock_mode"
    return CVEngineHealthSchema(
        status=status_str,
        engine=engine_name,
        supported_landmarks=33,
        confidence_threshold=settings.CV_MIN_TRACKING_CONFIDENCE,
    )


@router.post(
    "/pose/extract",
    response_model=PoseExtractionResponse,
    summary="Extract 33 Pose Landmarks from Image",
)
async def extract_pose(
    request: Request,
    file: Optional[UploadFile] = File(None),
    service: FormAnalysisService = Depends(get_form_analysis_service),
) -> PoseExtractionResponse:
    """
    Extracts canonical 33 body landmarks, bounding box, and body centroid approximation.
    Processes image buffers strictly in volatile memory. Never persists image data.
    Enforces a strict 5 MB payload limit before processing.
    """
    content_type = request.headers.get("content-type", "")

    # 1. Handle JSON Base64 payload
    if "application/json" in content_type:
        try:
            body = await request.json()
        except Exception:
            raise HTTPException(status_code=400, detail="Invalid JSON request body.")
        
        image_b64 = body.get("image_base64")
        if not image_b64:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Must provide 'image_base64' in JSON body.",
            )
        return service.extract_pose_from_base64(image_b64)

    # 2. Handle Multipart File Upload
    elif "multipart/form-data" in content_type or file is not None:
        if file is None:
            form = await request.form()
            file = form.get("file")
            if not file or not hasattr(file, "read"):
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail="Multipart file field 'file' is missing.",
                )

        if file.content_type and not file.content_type.startswith("image/"):
            raise HTTPException(
                status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
                detail=f"Unsupported media type '{file.content_type}'. Must be an image (JPEG, PNG, WebP).",
            )

        content = await file.read()
        if len(content) > settings.CV_MAX_IMAGE_SIZE_BYTES:
            raise HTTPException(
                status_code=status.HTTP_413_REQUEST_ENTITY_TOO_LARGE,
                detail=f"Image exceeds maximum limit of {settings.CV_MAX_IMAGE_SIZE_BYTES} bytes (5 MB).",
            )
        if len(content) == 0:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Uploaded image file is empty.",
            )
        return service.extract_pose_from_bytes(content)

    else:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Either a multipart image file or a JSON payload with 'image_base64' must be provided.",
        )



@router.post(
    "/pose/angles",
    response_model=JointAnglesResponse,
    summary="Calculate Joint Angles from Landmarks or Image",
)
def compute_angles(
    payload: JointAnglesRequest,
    use_3d: bool = Query(False, description="Whether to include relative depth z coordinate"),
    service: FormAnalysisService = Depends(get_form_analysis_service),
) -> JointAnglesResponse:
    """
    Calculates biomechanical joint angles (elbows, knees, hips, shoulders).
    Geometry logic is independently testable from supplied landmarks dictionary.
    """
    # If landmarks are already supplied, evaluate geometry directly
    if payload.landmarks:
        return service.compute_joint_angles(
            landmarks=payload.landmarks,
            target_joints=payload.target_joints,
            use_3d=use_3d,
        )

    # If image_base64 is provided instead, extract landmarks first
    if payload.image_base64:
        pose_res = service.extract_pose_from_base64(payload.image_base64)
        if not pose_res.landmarks_detected or not pose_res.landmarks:
            return JointAnglesResponse(
                landmarks_detected=False,
                joint_angles={},
                overall_confidence=0.0,
                processing_time_ms=pose_res.processing_time_ms,
            )
        return service.compute_joint_angles(
            landmarks=pose_res.landmarks,
            target_joints=payload.target_joints,
            use_3d=use_3d,
        )

    raise HTTPException(
        status_code=status.HTTP_400_BAD_REQUEST,
        detail="Must provide either 'landmarks' dictionary or 'image_base64' in request body.",
    )


@router.get(
    "/session/{exercise_id}",
    response_model=FormAnalysisSessionSchema,
    summary="Get Stateless Baseline Exercise Metadata",
)
def get_session_metadata(
    exercise_id: str,
    current_user: CurrentUser = Depends(get_current_user),
    service: FormAnalysisService = Depends(get_form_analysis_service),
) -> FormAnalysisSessionSchema:
    """
    Returns stateless baseline configuration and metadata for an exercise.
    MANDATORY RULE: Does NOT persist or create user sessions in database (Phase 9A).
    """
    return service.get_stateless_session_metadata(exercise_id)


# =============================================================================
# PHASE 9B.7: FORM ANALYSIS SESSION SUMMARY & HISTORY (AUTHENTICATED)
# =============================================================================

@router.get(
    "/history",
    response_model=List[FormAnalysisSessionSummarySchema],
    summary="Get Authenticated User's Form Analysis History",
)
async def get_form_history(
    limit: int = Query(20, ge=1, le=50, description="Maximum number of historical sessions (default 20, max 50)"),
    exercise_id: Optional[str] = Query(None, description="Optional exercise ID filter"),
    current_user: CurrentUser = Depends(get_current_user),
    repo: FormAnalysisRepository = Depends(get_form_analysis_repository),
) -> List[FormAnalysisSessionSummarySchema]:
    """
    Retrieves completed form analysis session summaries for the verified user UID.
    Ordered chronologically with newest sessions first.
    Strictly user-scoped: cross-user data is completely isolated.
    """
    return repo.list_user_history(current_user.uid, limit=limit, exercise_id=exercise_id)


@router.get(
    "/history/{session_id}",
    response_model=FormAnalysisSessionDetailSchema,
    summary="Get Form Analysis Session Detail",
)
async def get_form_session_detail(
    session_id: str,
    current_user: CurrentUser = Depends(get_current_user),
    repo: FormAnalysisRepository = Depends(get_form_analysis_repository),
) -> FormAnalysisSessionDetailSchema:
    """
    Retrieves full detail and rep-by-rep breakdowns for a finalized form analysis session.
    Returns 404 if session not found or does not belong to authenticated user.
    """
    session = repo.get_session_summary(current_user.uid, session_id)
    if not session:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Form analysis session not found.",
        )
    return session


@router.post(
    "/sessions/{session_id}/finalize",
    response_model=FormAnalysisSessionDetailSchema,
    summary="Finalize Form Analysis Session",
)
async def finalize_session(
    session_id: str,
    payload: Optional[FinalizeSessionRequest] = None,
    current_user: CurrentUser = Depends(get_current_user),
    repo: FormAnalysisRepository = Depends(get_form_analysis_repository),
) -> FormAnalysisSessionDetailSchema:
    """
    Explicitly finalizes and persists an active form analysis session.
    Idempotent: if session has already been finalized, returns existing document.
    """
    # 1. Check if already finalized idempotently
    existing = repo.get_session_summary(current_user.uid, session_id)
    if existing:
        return existing

    # 2. Retrieve authoritative active in-memory session
    active_session = default_session_manager.get_session(session_id, auto_touch=False)
    if not active_session:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Active form analysis session not found or already closed.",
        )

    # 3. Verify user ownership
    session_owner_uid = active_session.metadata.get("authenticated_uid")
    if session_owner_uid and session_owner_uid != current_user.uid:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Form analysis session not found.",
        )

    # 4. Check completion criteria (rep_count >= 1)
    if active_session.rep_count < 1 and len(active_session.completed_reps) < 1:
        default_session_manager.close_session(session_id)
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Session has no completed repetitions to record. Session marked as aborted.",
        )

    # 5. Build and save summary
    client_duration = payload.client_duration_seconds if payload else None
    summary = repo.build_session_summary(
        session=active_session,
        uid=current_user.uid,
        client_duration_seconds=client_duration,
    )

    if not summary:
        default_session_manager.close_session(session_id)
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Could not generate session summary.",
        )

    try:
        persisted = repo.save_session_summary(current_user.uid, summary)
    except Exception as exc:
        logger.error(f"Error persisting form analysis session {session_id}: {exc}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to persist form analysis session.",
        )

    # 6. Evict in-memory session once persisted
    default_session_manager.close_session(session_id)

    return persisted


# Mount Phase 9B.5 WebSocket Streaming Routes
from ...routes.form_analysis_ws import router as ws_router

router.include_router(ws_router)

