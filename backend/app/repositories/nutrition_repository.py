from typing import Optional, List, Dict, Any
from google.cloud.firestore_v1.base_query import FieldFilter
from ..core.firebase import get_firestore_db
from ..schemas.nutrition import DailyNutritionSchema, CatalogFoodSchema
from ..seeds.seed_nutrition import SEED_FOODS
from ..utils.logger import logger

_SENTINEL = object()


class NutritionRepository:
    """
    Data access layer for:
    1. User daily nutrition logs: users/{uid}/nutrition_logs/{YYYY-MM-DD}
    2. Global reference food catalogue: foods/{food_id}
    """

    def __init__(self, db: Any = _SENTINEL):
        self._db = db
        # In-memory store for test isolation
        self._in_memory_logs: Dict[str, Dict[str, Any]] = {}
        self._in_memory_foods: Dict[str, Dict[str, Any]] = {
            f["id"]: dict(f) for f in SEED_FOODS
        }

    @property
    def db(self) -> Optional[Any]:
        if self._db is not _SENTINEL:
            return self._db
        return get_firestore_db()

    def ensure_seeded(self) -> None:
        """Idempotently seeds reference food items into Firestore if empty."""
        db = self.db
        if not db:
            return
        try:
            coll = db.collection("foods")
            docs = list(coll.limit(1).stream())
            if not docs:
                logger.info("Seeding global food catalogue in Firestore...")
                batch = db.batch()
                for food_data in SEED_FOODS:
                    doc_ref = coll.document(food_data["id"])
                    batch.set(doc_ref, food_data)
                batch.commit()
                logger.info(f"Successfully seeded {len(SEED_FOODS)} foods into Firestore.")
        except Exception as e:
            logger.warning(f"Could not seed foods into Firestore: {e}")

    # =========================================================================
    # FOOD CATALOGUE
    # =========================================================================

    def search_foods(
        self,
        query: Optional[str] = None,
        category: Optional[str] = None,
        limit: int = 50,
    ) -> List[CatalogFoodSchema]:
        """Searches curated food items by name and optional category."""
        db = self.db
        all_foods: List[Dict[str, Any]] = []

        if db:
            try:
                coll = db.collection("foods")
                docs = coll.stream()
                for doc in docs:
                    all_foods.append(doc.to_dict())
            except Exception as e:
                logger.error(f"Error fetching foods from Firestore: {e}")
                all_foods = list(self._in_memory_foods.values())
        else:
            all_foods = list(self._in_memory_foods.values())

        if not all_foods:
            all_foods = list(self._in_memory_foods.values())

        filtered = all_foods
        if category:
            cat_lower = category.lower().strip()
            filtered = [f for f in filtered if f.get("category", "").lower() == cat_lower]

        if query:
            q_lower = query.lower().strip()
            filtered = [
                f for f in filtered
                if q_lower in f.get("name", "").lower() or q_lower in f.get("category", "").lower()
            ]

        return [CatalogFoodSchema(**f) for f in filtered[:limit]]

    def get_food_by_id(self, food_id: str) -> Optional[CatalogFoodSchema]:
        """Retrieves a single catalogue food item by its ID."""
        db = self.db
        if db:
            try:
                doc = db.collection("foods").document(food_id).get()
                if doc.exists:
                    return CatalogFoodSchema(**doc.to_dict())
            except Exception as e:
                logger.error(f"Error fetching food {food_id} from Firestore: {e}")

        raw = self._in_memory_foods.get(food_id)
        if raw:
            return CatalogFoodSchema(**raw)
        return None

    # =========================================================================
    # USER DAILY NUTRITION LOGS
    # =========================================================================

    def get_daily_log(self, uid: str, date: str) -> Optional[DailyNutritionSchema]:
        """Retrieves user's nutrition log document for a specific date (YYYY-MM-DD)."""
        db = self.db
        if db:
            try:
                doc = db.collection("users").document(uid).collection("nutrition_logs").document(date).get()
                if doc.exists:
                    return DailyNutritionSchema(**doc.to_dict())
            except Exception as e:
                logger.error(f"Error fetching nutrition log for {uid} on {date}: {e}")

        raw = self._in_memory_logs.get(f"{uid}:{date}")
        if raw:
            return DailyNutritionSchema(**raw)
        return None

    def save_daily_log(self, uid: str, date: str, data: Dict[str, Any]) -> DailyNutritionSchema:
        """Persists the daily nutrition log document for a user."""
        db = self.db
        if db:
            try:
                doc_ref = db.collection("users").document(uid).collection("nutrition_logs").document(date)
                doc_ref.set(data, merge=True)
            except Exception as e:
                logger.error(f"Error saving nutrition log for {uid} on {date}: {e}")

        self._in_memory_logs[f"{uid}:{date}"] = dict(data)
        return DailyNutritionSchema(**data)

    def list_logs_for_range(self, uid: str, start_date: str, end_date: str) -> List[DailyNutritionSchema]:
        """
        Retrieves daily nutrition documents for a date window [start_date, end_date].
        Avoids mandatory composite index requirements by filtering in Python.
        """
        db = self.db
        results: List[Dict[str, Any]] = []

        if db:
            try:
                coll = db.collection("users").document(uid).collection("nutrition_logs")
                docs = coll.stream()
                for doc in docs:
                    d = doc.to_dict()
                    doc_date = d.get("date", "")
                    if start_date <= doc_date <= end_date:
                        results.append(d)
            except Exception as e:
                logger.error(f"Error listing nutrition logs for {uid}: {e}")

        if not results:
            for key, log_data in self._in_memory_logs.items():
                if key.startswith(f"{uid}:"):
                    log_date = log_data.get("date", "")
                    if start_date <= log_date <= end_date:
                        results.append(log_data)

        results.sort(key=lambda x: x.get("date", ""))
        return [DailyNutritionSchema(**r) for r in results]

    def list_all_user_logs(self, uid: str) -> List[DailyNutritionSchema]:
        """Lists all recorded daily nutrition documents for a user."""
        db = self.db
        results: List[Dict[str, Any]] = []

        if db:
            try:
                coll = db.collection("users").document(uid).collection("nutrition_logs")
                docs = coll.stream()
                for doc in docs:
                    results.append(doc.to_dict())
            except Exception as e:
                logger.error(f"Error listing all nutrition logs for {uid}: {e}")

        if not results:
            for key, log_data in self._in_memory_logs.items():
                if key.startswith(f"{uid}:"):
                    results.append(log_data)

        results.sort(key=lambda x: x.get("date", ""))
        return [DailyNutritionSchema(**r) for r in results]


# Global nutrition repo provider
_nutrition_repo_instance: Optional[NutritionRepository] = None


def get_nutrition_repository() -> NutritionRepository:
    """FastAPI dependency for NutritionRepository."""
    global _nutrition_repo_instance
    if _nutrition_repo_instance is None:
        _nutrition_repo_instance = NutritionRepository()
        _nutrition_repo_instance.ensure_seeded()
    return _nutrition_repo_instance
