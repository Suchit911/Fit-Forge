from pathlib import Path
from typing import List, Optional, Union
from pydantic import field_validator
from pydantic_settings import BaseSettings, SettingsConfigDict

BACKEND_DIR = Path(__file__).resolve().parent.parent.parent
ROOT_DIR = BACKEND_DIR.parent


class Settings(BaseSettings):
    # Application Info
    APP_NAME: str = "AI FITNESS API"
    APP_VERSION: str = "1.0.0"
    APP_ENV: str = "development"
    DEBUG: bool = True
    API_V1_STR: str = "/api/v1"

    # Server Host / Port
    HOST: str = "127.0.0.1"
    PORT: int = 8000

    # Cross-Origin Resource Sharing (CORS)
    CORS_ORIGINS: Union[List[str], str] = [
        "http://localhost:5173",
        "http://127.0.0.1:5173",
        "http://localhost:3000",
        "http://127.0.0.1:3000",
    ]

    @field_validator("CORS_ORIGINS", mode="before")
    @classmethod
    def assemble_cors_origins(cls, v: Union[str, List[str]]) -> List[str]:
        if isinstance(v, str) and not v.startswith("["):
            return [i.strip() for i in v.split(",") if i.strip()]
        elif isinstance(v, list):
            return v
        return ["*"]

    # Firebase Admin Settings
    FIREBASE_PROJECT_ID: Optional[str] = None
    FIREBASE_SERVICE_ACCOUNT_PATH: Optional[str] = None
    FIREBASE_STORAGE_BUCKET: Optional[str] = None

    # AI Coach & LLM Settings (Phase 8)
    GEMINI_API_KEY: Optional[str] = None
    GEMINI_MODEL: str = "gemini-2.5-flash"

    # AI Coach Application Safeguards & Limits
    COACH_MAX_MESSAGES_PER_MINUTE: int = 10
    COACH_MAX_MESSAGES_PER_DAY: int = 50
    COACH_MAX_CONVERSATIONS_PER_USER: int = 20
    COACH_MAX_MESSAGES_PER_CONVERSATION: int = 50
    COACH_MAX_INPUT_CHARS: int = 1000
    COACH_MAX_OUTPUT_TOKENS: int = 800
    COACH_TIMEOUT_SECONDS: float = 12.0

    # AI Form Analysis & Computer Vision Settings (Phase 9A)
    CV_MIN_DETECTION_CONFIDENCE: float = 0.5
    CV_MIN_TRACKING_CONFIDENCE: float = 0.5
    CV_MAX_IMAGE_SIZE_BYTES: int = 5 * 1024 * 1024  # 5 MB payload ceiling
    CV_MAX_IMAGE_DIMENSION: int = 1920
    CV_MODEL_PATH: str = "backend/models/pose_landmarker_lite.task"
    CV_USE_MOCK: bool = False

    # AI Form Analysis Session Settings (Phase 9B.4)
    FORM_MAX_CONCURRENT_SESSIONS: int = 50
    FORM_SESSION_TTL_SECONDS: int = 900
    FORM_MAX_SESSION_DURATION_SECONDS: int = 3600
    FORM_IDLE_TIMEOUT_SECONDS: int = 300

    # AI Form Analysis WebSocket Streaming Settings (Phase 9B.5)
    FORM_MAX_FRAME_BYTES: int = 5 * 1024 * 1024  # 5 MB
    FORM_MAX_FRAME_WIDTH: int = 1920
    FORM_MAX_FRAME_HEIGHT: int = 1080
    FORM_MAX_ACCEPTED_FPS: int = 25



    model_config = SettingsConfigDict(
        env_file=[
            str(BACKEND_DIR / ".env"),
            str(ROOT_DIR / ".env"),
            ".env",
        ],

        env_file_encoding="utf-8",
        case_sensitive=True,
        extra="ignore",
    )


settings = Settings()
