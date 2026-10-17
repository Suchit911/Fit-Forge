from fastapi import APIRouter, status
from ....schemas.common import HealthCheckResponse
from ....core.config import settings
from ....core.firebase import is_firebase_available

router = APIRouter(tags=["Health"])


@router.get(
    "/health",
    response_model=HealthCheckResponse,
    status_code=status.HTTP_200_OK,
    summary="Health check",
    description="Returns the current operating health of the API server and Firebase status.",
)
async def check_health() -> HealthCheckResponse:
    """Returns application health status."""
    return HealthCheckResponse(
        status="healthy",
        app_name=settings.APP_NAME,
        version=settings.APP_VERSION,
        environment=settings.APP_ENV,
        firebase_connected=is_firebase_available(),
        debug=settings.DEBUG,
    )
