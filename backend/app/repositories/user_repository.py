from typing import Optional, Dict, Any
from ..core.firebase import get_firestore_db
from ..schemas.user import UserProfileSchema, UserProfileCreate, UserProfileUpdate
from ..utils.logger import logger


_SENTINEL = object()


class UserRepository:
    """
    Data access layer for User Profile documents stored in Cloud Firestore:
    users/{firebase_uid}
    """

    def __init__(self, db: Any = _SENTINEL):
        self._db = db
        self._in_memory_store: Dict[str, Dict[str, Any]] = {}

    @property
    def db(self) -> Optional[Any]:
        if self._db is not _SENTINEL:
            return self._db
        return get_firestore_db()

    def get_by_uid(self, uid: str) -> Optional[UserProfileSchema]:
        """Retrieves a user profile document by Firebase UID."""
        db = self.db
        if db:
            try:
                doc_ref = db.collection("users").document(uid)
                doc = doc_ref.get()
                if doc.exists:
                    doc_data = doc.to_dict() or {}
                    # Backward compatibility: if profile_complete wasn't stored, infer from real fitness data
                    if "profile_complete" not in doc_data:
                        has_fitness_data = bool(doc_data.get("weightKg") and doc_data.get("primaryGoal") and doc_data.get("heightCm"))
                        doc_data["profile_complete"] = has_fitness_data
                    return UserProfileSchema(**doc_data)
            except Exception as e:
                logger.warning(f"Error fetching user profile for UID {uid} from Firestore: {e}")

        # In-memory fallback if Firestore client is uninitialized (e.g., testing)
        data = self._in_memory_store.get(uid)
        if data:
            if "profile_complete" not in data:
                has_fitness_data = bool(data.get("weightKg") and data.get("primaryGoal") and data.get("heightCm"))
                data["profile_complete"] = has_fitness_data
            return UserProfileSchema(**data)
        return None

    def create(self, uid: str, email: str, profile_in: UserProfileCreate) -> UserProfileSchema:
        """Creates a new user profile document in Firestore at users/{uid}."""
        data = profile_in.model_dump()
        data["id"] = uid
        if not data.get("email"):
            data["email"] = email or "user@example.com"

        # Calculate initial BMI and BMR only if measurements are genuinely provided
        if data.get("heightCm") and data.get("weightKg"):
            h_m = data["heightCm"] / 100.0
            data["bmi"] = round(data["weightKg"] / (h_m * h_m), 1)
            if data.get("age"):
                w = float(data["weightKg"])
                h = float(data["heightCm"])
                a = float(data["age"])
                gender = str(data.get("gender") or "male").lower()
                base_bmr = 10.0 * w + 6.25 * h - 5.0 * a + (5.0 if gender == "male" else (-161.0 if gender == "female" else 0.0))
                data["bmr"] = round(base_bmr, 1)
                data["tdee"] = round(base_bmr * 1.375, 1)

        self._in_memory_store[uid] = data
        db = self.db
        if db:
            try:
                doc_ref = db.collection("users").document(uid)
                doc_ref.set(data)
                logger.info(f"Created Firestore profile at users/{uid}")
            except Exception as e:
                logger.warning(f"Error creating user profile in Firestore for UID {uid}: {e}")

        return UserProfileSchema(**data)

    def update(self, uid: str, updates: UserProfileUpdate) -> Optional[UserProfileSchema]:
        """Updates an existing user profile document in Firestore."""
        current = self.get_by_uid(uid)
        if not current:
            return None

        update_data = updates.model_dump(exclude_unset=True, exclude_none=True)
        merged = current.model_dump()
        merged.update(update_data)
        merged["id"] = uid

        # Recalculate BMI/BMR/TDEE if biometric values were updated
        if any(k in update_data for k in ("heightCm", "weightKg", "age", "gender")):
            if merged.get("heightCm") and merged.get("weightKg"):
                h_m = merged["heightCm"] / 100.0
                merged["bmi"] = round(merged["weightKg"] / (h_m * h_m), 1)
                if merged.get("age"):
                    w = float(merged["weightKg"])
                    h = float(merged["heightCm"])
                    a = float(merged["age"])
                    gender = str(merged.get("gender") or "male").lower()
                    base_bmr = 10.0 * w + 6.25 * h - 5.0 * a + (5.0 if gender == "male" else (-161.0 if gender == "female" else 0.0))
                    merged["bmr"] = round(base_bmr, 1)
                    merged["tdee"] = round(base_bmr * 1.375, 1)

        self._in_memory_store[uid] = merged
        db = self.db
        if db:
            try:
                doc_ref = db.collection("users").document(uid)
                doc_ref.set(merged, merge=True)
                logger.info(f"Updated Firestore profile at users/{uid}")
            except Exception as e:
                logger.warning(f"Error updating user profile in Firestore for UID {uid}: {e}")

        return UserProfileSchema(**merged)


# Global repository instance
_user_repository_instance: Optional[UserRepository] = None


def get_user_repository() -> UserRepository:
    """FastAPI dependency for UserRepository."""
    global _user_repository_instance
    if _user_repository_instance is None:
        _user_repository_instance = UserRepository()
    return _user_repository_instance
