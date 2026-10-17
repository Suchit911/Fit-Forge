from typing import Optional, Dict, Any
from fastapi import Depends, HTTPException, status
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from pydantic import BaseModel
from firebase_admin import auth
from .firebase import is_firebase_available
from ..utils.logger import logger

security_scheme = HTTPBearer(auto_error=False)


class CurrentUser(BaseModel):
    """Normalized authenticated user payload decoded from Firebase ID token."""
    uid: str
    email: Optional[str] = None
    name: Optional[str] = None
    email_verified: bool = False
    claims: Dict[str, Any] = {}


def verify_firebase_token(token: str) -> Dict[str, Any]:
    """
    Verifies a Firebase ID token using the Firebase Admin SDK.
    Raises HTTPException if invalid, expired, or if Firebase is unconfigured.
    """
    if not is_firebase_available():
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="Firebase Authentication is not configured on the backend. Provide service account credentials.",
        )

    try:
        decoded_token = auth.verify_id_token(token, check_revoked=True)
        return decoded_token
    except auth.RevokedIdTokenError:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Authentication token has been revoked.",
            headers={"WWW-Authenticate": "Bearer"},
        )
    except auth.ExpiredIdTokenError:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Authentication token has expired. Please refresh your session.",
            headers={"WWW-Authenticate": "Bearer"},
        )
    except Exception as e:
        logger.warning(f"Invalid Firebase ID token received: {e}")
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Could not validate credentials.",
            headers={"WWW-Authenticate": "Bearer"},
        )


async def get_current_user(
    auth_header: Optional[HTTPAuthorizationCredentials] = Depends(security_scheme),
) -> CurrentUser:
    """
    FastAPI dependency for protected endpoints.
    Extracts and verifies Bearer token from the Authorization header.
    """
    if not auth_header or not auth_header.credentials:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Missing Bearer authentication token in request header.",
            headers={"WWW-Authenticate": "Bearer"},
        )

    decoded = verify_firebase_token(auth_header.credentials)

    uid = decoded.get("uid") or decoded.get("user_id") or decoded.get("sub") or ""
    if not uid:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Token payload is missing a valid user identifier.",
            headers={"WWW-Authenticate": "Bearer"},
        )

    return CurrentUser(
        uid=uid,
        email=decoded.get("email"),
        name=decoded.get("name"),
        email_verified=decoded.get("email_verified", False),
        claims=decoded,
    )
