from datetime import datetime, timezone
from typing import Optional, Dict, Any
from ..core.firebase import get_firestore_db
from ..schemas.settings import (
    UserSettingsSchema,
    UserSettingsUpdateSchema,
)
from ..utils.logger import logger


_SENTINEL = object()


class PersistenceError(Exception):
    """Raised when durable storage operations fail."""
    pass


class SettingsRepository:
    """
    Data access layer for User Settings documents stored in Cloud Firestore:
    users/{firebase_uid}/settings/preferences
    """

    def __init__(self, db: Any = _SENTINEL):
        self._db = db
        self._in_memory_store: Dict[str, Dict[str, Any]] = {}

    @property
    def db(self) -> Optional[Any]:
        if self._db is not _SENTINEL:
            return self._db
        return get_firestore_db()

    @property
    def is_durable(self) -> bool:
        """Returns True if backed by genuine Cloud Firestore client, False if using in-memory test fallback."""
        return self.db is not None

    def get_by_uid(self, uid: str) -> Optional[UserSettingsSchema]:
        """
        Retrieves persisted user settings document from Firestore at users/{uid}/settings/preferences.
        Returns None if no settings record has been persisted yet.
        """
        db = self.db
        if db:
            try:
                doc_ref = (
                    db.collection("users")
                    .document(uid)
                    .collection("settings")
                    .document("preferences")
                )
                doc = doc_ref.get()
                if doc.exists:
                    doc_data = doc.to_dict() or {}
                    doc_data["userId"] = uid
                    doc_data["persisted"] = True
                    return UserSettingsSchema(**doc_data)
                return None
            except Exception as e:
                logger.error(f"Error reading user settings from Firestore for UID {uid}: {e}")
                raise PersistenceError(f"Database read failure: {e}")

        # In-memory fallback if Firestore client is uninitialized (e.g. testing double)
        data = self._in_memory_store.get(uid)
        if data:
            data_copy = dict(data)
            data_copy["userId"] = uid
            data_copy["persisted"] = True
            return UserSettingsSchema(**data_copy)
        return None

    def get_or_default(self, uid: str) -> UserSettingsSchema:
        """
        Returns authenticated user's settings.
        If user has not yet persisted any settings, returns first-read defaults with persisted=False.
        Does not falsely write defaults to storage prior to an intentional user update.
        """
        existing = self.get_by_uid(uid)
        if existing:
            return existing
        return UserSettingsSchema(userId=uid, persisted=False)

    def save(self, uid: str, settings: UserSettingsSchema) -> UserSettingsSchema:
        """
        Persists full settings record to Firestore or in-memory fallback.
        Raises PersistenceError on failure; never silently swallows storage errors.
        """
        data = settings.model_dump()
        data["userId"] = uid
        data["persisted"] = True
        data["updatedAt"] = datetime.now(timezone.utc).isoformat()

        db = self.db
        if db:
            try:
                doc_ref = (
                    db.collection("users")
                    .document(uid)
                    .collection("settings")
                    .document("preferences")
                )
                doc_ref.set(data)
                logger.info(f"Persisted settings in Firestore at users/{uid}/settings/preferences")
            except Exception as e:
                logger.error(f"Error persisting settings in Firestore for UID {uid}: {e}")
                raise PersistenceError(f"Database persistence failure: {e}")
        else:
            self._in_memory_store[uid] = data

        return UserSettingsSchema(**data)

    def update(self, uid: str, updates: UserSettingsUpdateSchema) -> UserSettingsSchema:
        """
        Applies partial updates to existing settings (or first-read defaults),
        preserving all omitted fields.
        Persists the result to Firestore and returns the updated schema with persisted=True.
        """
        current = self.get_by_uid(uid)
        if not current:
            current = UserSettingsSchema(userId=uid, persisted=False)

        current_dict = current.model_dump()
        update_dict = updates.model_dump(exclude_unset=True, exclude_none=True)

        for section in ["general", "notifications", "appearance", "privacy", "aiCoach"]:
            if section in update_dict and isinstance(update_dict[section], dict):
                current_dict[section].update(update_dict[section])

        current_dict["userId"] = uid
        current_dict["persisted"] = True
        current_dict["updatedAt"] = datetime.now(timezone.utc).isoformat()

        db = self.db
        if db:
            try:
                doc_ref = (
                    db.collection("users")
                    .document(uid)
                    .collection("settings")
                    .document("preferences")
                )
                doc_ref.set(current_dict)
                logger.info(f"Updated settings in Firestore at users/{uid}/settings/preferences")
            except Exception as e:
                logger.error(f"Error updating settings in Firestore for UID {uid}: {e}")
                raise PersistenceError(f"Database persistence failure: {e}")
        else:
            self._in_memory_store[uid] = current_dict

        return UserSettingsSchema(**current_dict)


# Global repository instance
_settings_repository_instance: Optional[SettingsRepository] = None


def get_settings_repository() -> SettingsRepository:
    """FastAPI dependency for SettingsRepository."""
    global _settings_repository_instance
    if _settings_repository_instance is None:
        _settings_repository_instance = SettingsRepository()
    return _settings_repository_instance
