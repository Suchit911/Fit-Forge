from typing import Optional, List, Dict, Any
from ..core.firebase import get_firestore_db
from ..schemas.workout import ExerciseSchema
from ..schemas.exercise import ExerciseKnowledgeSchema, CANONICAL_CV_EXERCISES
from ..schemas.user import MuscleGroup, EquipmentType, DifficultyLevel
from ..seeds.exercise_catalog import RAW_CATALOG_DATA, CATALOG_BY_ID
from ..utils.logger import logger


_SENTINEL = object()

# Canonical ID aliases for backward compatibility and alternate ID formats
EXERCISE_ID_ALIASES: Dict[str, str] = {
    "ex_bulgarian_split_squat": "ex_bulgarian_squat",
    "ex_incline_dumbbell_press": "ex_incline_db_press",
    "ex_pullup": "ex_pull_up",
    "ex_barbell_bench_press": "ex_bench_press",
    "ex_barbell_squat": "ex_squat",
    "ex_barbell_back_squat": "ex_squat",
    "ex_barbell_deadlift": "ex_deadlift",
    "ex_rdl": "ex_romanian_deadlift",
    "ex_barbell_rdl": "ex_romanian_deadlift",
}


class ExerciseRepository:
    """
    Data access layer for Exercises.
    Uses Cloud Firestore 'exercises' collection with in-memory fallback.
    The authoritative single source of truth is the canonical 100-exercise catalog.
    """

    def __init__(self, db: Any = _SENTINEL):
        self._db = db
        # In-memory store pre-populated with canonical catalog for offline/test isolation
        self._in_memory_store: Dict[str, Dict[str, Any]] = self._load_default_exercises()

    @classmethod
    def _load_default_exercises(cls) -> Dict[str, Dict[str, Any]]:
        """
        Loads all 100 canonical exercises from the authoritative exercise catalog.
        Canonical catalog is imported directly from backend.app.seeds.exercise_catalog.
        """
        return {e["id"]: dict(e) for e in RAW_CATALOG_DATA}

    @staticmethod
    def _to_schema(item: Dict[str, Any]) -> ExerciseKnowledgeSchema:
        """Converts raw dictionary to ExerciseKnowledgeSchema, safeguarding against legacy/partial records."""
        data = dict(item)
        if data.get("supportedFormAnalysis") and not data.get("cvExerciseId"):
            data["cvExerciseId"] = CANONICAL_CV_EXERCISES.get(data.get("id"))
        return ExerciseKnowledgeSchema(**data)

    @property
    def db(self) -> Optional[Any]:
        if self._db is not _SENTINEL:
            return self._db
        return get_firestore_db()

    def ensure_seeded(self) -> None:
        """Idempotently seeds reference exercises into Firestore if incomplete or missing."""
        db = self.db
        if not db:
            return
        try:
            coll = db.collection("exercises")
            default_exercises = self._load_default_exercises()
            existing_docs = {d.id: d.to_dict() for d in coll.stream()}
            needs_seed = len(existing_docs) < len(default_exercises) or any(
                ex_id not in existing_docs or (existing_docs[ex_id].get("supportedFormAnalysis") and not existing_docs[ex_id].get("cvExerciseId"))
                for ex_id in default_exercises
            )
            if needs_seed:
                logger.info("Seeding global exercises reference collection in Firestore from canonical catalog...")
                batch = db.batch()
                for ex_id, ex_data in default_exercises.items():
                    doc_ref = coll.document(ex_id)
                    batch.set(doc_ref, ex_data)
                batch.commit()
                logger.info(f"Successfully seeded {len(default_exercises)} canonical exercises into Firestore.")
        except Exception as e:
            logger.warning(f"Could not seed exercises in Firestore: {e}")

    def list_exercises(
        self,
        muscle: Optional[MuscleGroup] = None,
        equipment: Optional[EquipmentType] = None,
        difficulty: Optional[DifficultyLevel] = None,
        category: Optional[str] = None,
        search: Optional[str] = None,
    ) -> List[ExerciseKnowledgeSchema]:
        """Lists exercises matching the supplied filters."""
        db = self.db
        all_data: List[Dict[str, Any]] = []

        if db:
            try:
                coll = db.collection("exercises")
                docs = coll.stream()
                for doc in docs:
                    all_data.append(doc.to_dict())
            except Exception as e:
                logger.error(f"Error fetching exercises from Firestore: {e}")
                all_data = list(self._in_memory_store.values())
        else:
            all_data = list(self._in_memory_store.values())

        # If Firestore had 0 items, fallback to seed data
        if not all_data:
            all_data = list(self._in_memory_store.values())

        # In-memory filtering for flexible multi-tag querying
        filtered = all_data

        if muscle:
            m = str(muscle).lower()
            filtered = [
                e for e in filtered
                if m in [x.lower() for x in e.get("primaryMuscles", [])]
                or m in [x.lower() for x in e.get("secondaryMuscles", [])]
            ]

        if equipment:
            eq = str(equipment).lower()
            filtered = [
                e for e in filtered
                if eq in [x.lower() for x in e.get("equipment", [])]
            ]

        if difficulty:
            d = str(difficulty).lower()
            filtered = [
                e for e in filtered
                if e.get("difficulty", "").lower() == d
            ]

        if category:
            cat = str(category).lower()
            filtered = [
                e for e in filtered
                if e.get("category", "").lower() == cat
            ]

        if search:
            q = search.lower().strip()
            filtered = [
                e for e in filtered
                if q in e.get("name", "").lower()
                or q in e.get("description", "").lower()
                or any(q in a.lower() for a in e.get("aliases", []))
            ]

        return [self._to_schema(item) for item in filtered]

    def get_by_id(self, exercise_id: str) -> Optional[ExerciseKnowledgeSchema]:
        """Retrieves a single exercise by ID or recognized alias."""
        resolved_id = EXERCISE_ID_ALIASES.get(exercise_id, exercise_id)
        db = self.db
        if db:
            try:
                doc = db.collection("exercises").document(resolved_id).get()
                if doc.exists:
                    return self._to_schema(doc.to_dict())
            except Exception as e:
                logger.error(f"Error fetching exercise {resolved_id} from Firestore: {e}")

        # Fallback to in-memory store
        item = self._in_memory_store.get(resolved_id)
        if item:
            return self._to_schema(item)
        return None


# Global instance
_exercise_repo_instance: Optional[ExerciseRepository] = None


def get_exercise_repository() -> ExerciseRepository:
    """FastAPI dependency provider for ExerciseRepository."""
    global _exercise_repo_instance
    if _exercise_repo_instance is None:
        _exercise_repo_instance = ExerciseRepository()
        _exercise_repo_instance.ensure_seeded()
    return _exercise_repo_instance
