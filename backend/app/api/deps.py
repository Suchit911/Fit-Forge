from typing import Generator
from ..core.security import get_current_user, CurrentUser
from ..core.config import settings, Settings

def get_settings() -> Settings:
    """Returns application configuration instance."""
    return settings

__all__ = ["get_current_user", "CurrentUser", "get_settings"]
