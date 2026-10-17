from contextlib import asynccontextmanager
from fastapi import FastAPI, Request, status
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from fastapi.exceptions import RequestValidationError

from .core.config import settings
from .core.firebase import init_firebase, is_firebase_available
from .api.v1.router import api_router
from .schemas.common import HealthCheckResponse, ErrorResponse
from .utils.logger import logger


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Application startup and shutdown events."""
    logger.info(f"Starting {settings.APP_NAME} in [{settings.APP_ENV}] mode...")
    
    # Safely attempt to initialize Firebase (will not crash if keys are unconfigured)
    init_firebase()
    
    yield
    
    logger.info(f"Shutting down {settings.APP_NAME}...")


app = FastAPI(
    title=settings.APP_NAME,
    version=settings.APP_VERSION,
    description="FastAPI Backend for the AI FITNESS Platform.",
    docs_url="/docs",
    redoc_url="/redoc",
    openapi_url="/openapi.json",
    lifespan=lifespan,
)

# Set up CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.CORS_ORIGINS,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


# Global Exception Handlers
@app.exception_handler(RequestValidationError)
async def validation_exception_handler(request: Request, exc: RequestValidationError):
    """Handles request payload schema validation errors."""
    sanitized_errors = []
    for err in exc.errors():
        sanitized_errors.append({
            "loc": [str(x) for x in err.get("loc", [])],
            "msg": str(err.get("msg", "")),
            "type": str(err.get("type", "")),
        })
    return JSONResponse(
        status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
        content=ErrorResponse(
            success=False,
            error="Validation Error",
            detail=sanitized_errors,
        ).model_dump(mode="json"),
    )


@app.exception_handler(Exception)
async def generic_exception_handler(request: Request, exc: Exception):
    """Centralized fallback for unexpected errors."""
    logger.error(f"Unhandled exception at {request.url.path}: {exc}", exc_info=True)
    return JSONResponse(
        status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
        content=ErrorResponse(
            success=False,
            error="Internal Server Error",
            detail=str(exc) if settings.DEBUG else "An unexpected error occurred.",
        ).model_dump(mode="json"),
    )


# Root Health Check (Convenience access at /health)
@app.get(
    "/health",
    response_model=HealthCheckResponse,
    tags=["Health"],
    summary="Root Health Check",
)
async def root_health():
    """Root level health check endpoint."""
    return HealthCheckResponse(
        status="healthy",
        app_name=settings.APP_NAME,
        version=settings.APP_VERSION,
        environment=settings.APP_ENV,
        firebase_connected=is_firebase_available(),
        debug=settings.DEBUG,
    )


# Root landing endpoint
@app.get("/", tags=["Root"])
async def root():
    """API entry point."""
    return {
        "message": f"Welcome to {settings.APP_NAME}",
        "version": settings.APP_VERSION,
        "docs": "/docs",
        "health": "/health",
        "api_v1": settings.API_V1_STR,
    }


# Mount API v1 router
app.include_router(api_router, prefix=settings.API_V1_STR)
