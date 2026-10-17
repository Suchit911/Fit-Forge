from typing import Optional, List, Dict, Any
import uuid
from datetime import datetime, timezone
from ..core.firebase import get_firestore_db
from ..schemas.achievement import (
    AchievementDefinitionSchema,
    UserAchievementSchema,
)
from ..seeds.seed_achievements import SEED_ACHIEVEMENTS
from ..utils.logger import logger

_SENTINEL = object()


class AchievementRepository:
    """
    Data access layer for:
    1. Global achievement definitions: achievements/{achievement_id}
    2. User achievement progress & unlocks: users/{uid}/achievements/{achievement_id}
    """

    def __init__(self, db: Any = _SENTINEL):
        self._db = db
        # In-memory stores for isolated unit testing
        self._in_memory_definitions: Dict[str, Dict[str, Any]] = {
            item["id"]: dict(item) for item in SEED_ACHIEVEMENTS
        }
        self._in_memory_user_achievements: Dict[str, Dict[str, Any]] = {}

    @property
    def db(self) -> Optional[Any]:
        if self._db is not _SENTINEL:
            return self._db
        return get_firestore_db()

    def ensure_seeded(self) -> None:
        """Idempotently seeds reference achievement definitions and synchronizes authorized points."""
        for ach in SEED_ACHIEVEMENTS:
            self._in_memory_definitions[ach["id"]] = dict(ach)

        db = self.db
        if not db:
            return
        try:
            coll = db.collection("achievements")
            batch = db.batch()
            has_updates = False
            for ach_data in SEED_ACHIEVEMENTS:
                doc_ref = coll.document(ach_data["id"])
                doc = doc_ref.get()
                if not doc.exists:
                    batch.set(doc_ref, ach_data)
                    has_updates = True
                else:
                    existing = doc.to_dict() or {}
                    if existing.get("points") != ach_data["points"]:
                        batch.update(doc_ref, {"points": ach_data["points"]})
                        has_updates = True
            if has_updates:
                batch.commit()
                logger.info("Synchronized global achievement definitions safely.")
        except Exception as e:
            logger.warning(f"Could not seed/synchronize achievements in Firestore: {e}")

    # =========================================================================
    # GLOBAL DEFINITIONS
    # =========================================================================

    def list_definitions(self) -> List[AchievementDefinitionSchema]:
        """Returns all reference achievement definitions."""
        db = self.db
        if db:
            try:
                coll = db.collection("achievements")
                docs = list(coll.stream())
                if docs:
                    return [AchievementDefinitionSchema(**doc.to_dict()) for doc in docs]
            except Exception as e:
                logger.warning(f"Error fetching achievement definitions from Firestore: {e}")

        # In-memory / fallback definitions
        return [AchievementDefinitionSchema(**d) for d in self._in_memory_definitions.values()]

    def get_definition(self, achievement_id: str) -> Optional[AchievementDefinitionSchema]:
        """Fetches a single achievement definition by ID."""
        db = self.db
        if db:
            try:
                doc = db.collection("achievements").document(achievement_id).get()
                if doc.exists:
                    return AchievementDefinitionSchema(**doc.to_dict())
            except Exception as e:
                logger.warning(f"Error fetching achievement {achievement_id} from Firestore: {e}")

        data = self._in_memory_definitions.get(achievement_id)
        if data:
            return AchievementDefinitionSchema(**data)
        return None

    # =========================================================================
    # USER ACHIEVEMENT STATE
    # =========================================================================

    def list_user_achievements(self, uid: str) -> List[UserAchievementSchema]:
        """Lists all recorded user achievement states for the given user."""
        db = self.db
        if db:
            try:
                coll = db.collection("users").document(uid).collection("achievements")
                docs = list(coll.stream())
                return [UserAchievementSchema(**doc.to_dict()) for doc in docs]
            except Exception as e:
                logger.warning(f"Error fetching user achievements for {uid}: {e}")

        # In-memory lookup
        prefix = f"{uid}:"
        res = []
        for key, val in self._in_memory_user_achievements.items():
            if key.startswith(prefix):
                res.append(UserAchievementSchema(**val))
        return res

    def get_user_achievement(self, uid: str, achievement_id: str) -> Optional[UserAchievementSchema]:
        """Retrieves single achievement state for a user."""
        db = self.db
        if db:
            try:
                doc = db.collection("users").document(uid).collection("achievements").document(achievement_id).get()
                if doc.exists:
                    return UserAchievementSchema(**doc.to_dict())
            except Exception as e:
                logger.warning(f"Error fetching user achievement {achievement_id}: {e}")

        key = f"{uid}:{achievement_id}"
        val = self._in_memory_user_achievements.get(key)
        if val:
            return UserAchievementSchema(**val)
        return None

    def upsert_user_achievement(self, uid: str, data: Dict[str, Any]) -> UserAchievementSchema:
        """Upserts a single user achievement state."""
        ach_id = data["id"]
        data["userId"] = uid
        if "updatedAt" not in data:
            data["updatedAt"] = datetime.now(timezone.utc).isoformat()

        db = self.db
        if db:
            try:
                doc_ref = db.collection("users").document(uid).collection("achievements").document(ach_id)
                doc_ref.set(data, merge=True)
            except Exception as e:
                logger.warning(f"Error writing user achievement {ach_id}: {e}")

        # Always update in-memory
        key = f"{uid}:{ach_id}"
        existing = self._in_memory_user_achievements.get(key, {})
        merged = {**existing, **data}
        self._in_memory_user_achievements[key] = merged
        return UserAchievementSchema(**merged)

    def batch_upsert_user_achievements(self, uid: str, items: List[Dict[str, Any]]) -> None:
        """Atomically upserts a batch of user achievement states."""
        if not items:
            return

        now_str = datetime.now(timezone.utc).isoformat()
        for item in items:
            item["userId"] = uid
            if "updatedAt" not in item:
                item["updatedAt"] = now_str

        db = self.db
        if db:
            try:
                batch = db.batch()
                user_coll = db.collection("users").document(uid).collection("achievements")
                for item in items:
                    doc_ref = user_coll.document(item["id"])
                    batch.set(doc_ref, item, merge=True)
                batch.commit()
            except Exception as e:
                logger.warning(f"Error batch writing achievements for {uid}: {e}")

        # Always update in-memory
        for item in items:
            key = f"{uid}:{item['id']}"
            existing = self._in_memory_user_achievements.get(key, {})
            self._in_memory_user_achievements[key] = {**existing, **item}

    def clear_is_new(self, uid: str, achievement_ids: Optional[List[str]] = None) -> None:
        """Clears the isNew flag on specified or all user achievements."""
        user_achs = self.list_user_achievements(uid)
        to_clear = [
            a for a in user_achs
            if a.isNew and (achievement_ids is None or a.id in achievement_ids)
        ]
        if not to_clear:
            return

        now_str = datetime.now(timezone.utc).isoformat()
        items = [
            {**a.model_dump(), "isNew": False, "updatedAt": now_str}
            for a in to_clear
        ]
        self.batch_upsert_user_achievements(uid, items)

    def create_custom_achievement(
        self,
        uid: str,
        name: str,
        description: str,
        category: str = "Workout Mastery",
    ) -> UserAchievementSchema:
        """
        Creates a user-created milestone record under users/{uid}/achievements/custom_{uuid}.
        Custom milestones award 100 points and are marked as immediately unlocked.
        """
        custom_id = f"custom_{uuid.uuid4().hex[:12]}"
        now_str = datetime.now(timezone.utc).isoformat()

        doc_data: Dict[str, Any] = {
            "id": custom_id,
            "userId": uid,
            "achievementId": custom_id,
            "isUnlocked": True,
            "unlockedAt": now_str,
            "currentValue": 1.0,
            "targetValue": 1.0,
            "progressPercentage": 100.0,
            "isNew": True,
            "isCustom": True,
            "customTitle": name.strip(),
            "customDescription": description.strip(),
            "customCategory": category,
            "points": 100,
            "updatedAt": now_str,
        }

        return self.upsert_user_achievement(uid, doc_data)


# Singleton getter
_achievement_repository: Optional[AchievementRepository] = None


def get_achievement_repository() -> AchievementRepository:
    global _achievement_repository
    if _achievement_repository is None:
        _achievement_repository = AchievementRepository()
    return _achievement_repository
