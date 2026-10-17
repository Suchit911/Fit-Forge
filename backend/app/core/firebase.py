import os
from pathlib import Path
from typing import Optional, Any
import firebase_admin
from firebase_admin import credentials, firestore, storage
from ..utils.logger import logger
from .config import settings

_firebase_initialized = False


def resolve_sa_path(path_str: Optional[str]) -> Optional[str]:
    """Resolves relative service account path against backend directories."""
    if not path_str:
        return None
    p = Path(path_str)
    if p.is_file():
        return str(p.resolve())
    backend_dir = Path(__file__).resolve().parent.parent.parent
    if (backend_dir / p).is_file():
        return str((backend_dir / p).resolve())
    if (backend_dir / "credentials" / p.name).is_file():
        return str((backend_dir / "credentials" / p.name).resolve())
    return str(p)


def init_firebase() -> bool:
    """
    Safely initializes the Firebase Admin SDK.
    Follows zero-fake-credential rule: if no credentials are provided,
    it remains uninitialized and logs a clear informational message
    without failing or crashing the application.
    """
    global _firebase_initialized

    if _firebase_initialized or len(firebase_admin._apps) > 0:
        _firebase_initialized = True
        return True

    sa_path = resolve_sa_path(settings.FIREBASE_SERVICE_ACCOUNT_PATH)
    project_id = settings.FIREBASE_PROJECT_ID

    try:
        if sa_path and os.path.exists(sa_path):
            cred = credentials.Certificate(sa_path)
            options = {}
            if project_id:
                options["projectId"] = project_id
            if settings.FIREBASE_STORAGE_BUCKET:
                options["storageBucket"] = settings.FIREBASE_STORAGE_BUCKET
            firebase_admin.initialize_app(cred, options=options)
            _firebase_initialized = True
            logger.info("Firebase Admin SDK initialized successfully via service account file.")
            return True

        # Check standard GOOGLE_APPLICATION_CREDENTIALS environment variable
        elif os.environ.get("GOOGLE_APPLICATION_CREDENTIALS") and os.path.exists(
            os.environ["GOOGLE_APPLICATION_CREDENTIALS"]
        ):
            cred = credentials.ApplicationDefault()
            firebase_admin.initialize_app(cred)
            _firebase_initialized = True
            logger.info("Firebase Admin SDK initialized via Application Default Credentials.")
            return True

        else:
            logger.info(
                "Firebase service account key not provided. "
                "Firebase Admin SDK running in uninitialized/mock mode for Phase 1 foundation."
            )
            _firebase_initialized = False
            return False

    except Exception as e:
        logger.warning(f"Failed to initialize Firebase Admin SDK: {e}")
        _firebase_initialized = False
        return False


def is_firebase_available() -> bool:
    """Returns True if Firebase Admin SDK is initialized with valid credentials."""
    return _firebase_initialized or len(firebase_admin._apps) > 0


def get_firestore_db() -> Optional[Any]:
    """Returns Cloud Firestore client if Firebase is initialized, else None."""
    if is_firebase_available():
        return firestore.client()
    return None


def get_storage_bucket() -> Optional[Any]:
    """Returns Firebase Storage bucket if Firebase is initialized, else None."""
    if is_firebase_available():
        return storage.bucket()
    return None
