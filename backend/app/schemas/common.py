from typing import Optional, Generic, TypeVar, Any
from datetime import datetime, timezone
from pydantic import BaseModel, Field

T = TypeVar("T")


class HealthCheckResponse(BaseModel):
    status: str = Field(default="healthy", description="Application health status")
    app_name: str = Field(..., description="Application name")
    version: str = Field(..., description="API Version")
    environment: str = Field(..., description="Deployment environment (development/production)")
    timestamp: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))
    firebase_connected: bool = Field(default=False, description="Whether Firebase Admin SDK is initialized")
    debug: bool = Field(default=False)


class ApiResponse(BaseModel, Generic[T]):
    success: bool = True
    message: Optional[str] = None
    data: Optional[T] = None


class ErrorResponse(BaseModel):
    success: bool = False
    error: str
    detail: Optional[Any] = None
    timestamp: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))
