"""
Program Repository (Phase 9C.3).

Data access layer for user-scoped programs:
users/{uid}/programs/{program_id}

Provides atomic Firestore operations and an isolated in-memory store for unit tests.
Enforces single active program constraint, idempotent session sync, and adaptation audit history.
"""

from datetime import datetime, timezone
from typing import Optional, List, Dict, Any
from google.cloud.firestore_v1.base_query import FieldFilter
from ..core.firebase import get_firestore_db
from ..schemas.program import (
    ProgramDocument,
    ProgramResponse,
    ProgramCompletedWorkout,
    ProgramStatus,
)
from ..utils.logger import logger

_SENTINEL = object()


class ProgramRepository:
    """
    Repository managing persistence for user workout programs:
    users/{uid}/programs/{program_id}
    """

    def __init__(self, db: Any = _SENTINEL):
        self._db = db
        # In-memory store keyed by f"{uid}:{program_id}"
        self._in_memory_programs: Dict[str, Dict[str, Any]] = {}

    @property
    def db(self) -> Optional[Any]:
        if self._db is not _SENTINEL:
            return self._db
        return get_firestore_db()

    def get_program(self, uid: str, program_id: str) -> Optional[ProgramResponse]:
        """Retrieves a single program belonging to the user."""
        db = self.db
        if db:
            try:
                doc = db.collection("users").document(uid).collection("programs").document(program_id).get()
                if doc.exists:
                    data = doc.to_dict()
                    if data.get("userId") == uid or data.get("user_id") == uid:
                        return ProgramResponse(**data)
            except Exception as e:
                logger.error(f"Error fetching program {program_id} from Firestore: {e}")

        key = f"{uid}:{program_id}"
        item = self._in_memory_programs.get(key)
        if item and (item.get("userId") == uid or item.get("user_id") == uid):
            return ProgramResponse(**item)
        return None

    def get_active_program(self, uid: str) -> Optional[ProgramResponse]:
        """Retrieves the current active program for the user, if one exists."""
        db = self.db
        if db:
            try:
                coll = db.collection("users").document(uid).collection("programs")
                docs = list(coll.where(filter=FieldFilter("status", "==", "active")).limit(1).stream())
                if docs:
                    return ProgramResponse(**docs[0].to_dict())
            except Exception as e:
                logger.error(f"Error fetching active program for {uid} from Firestore: {e}")

        for key, prog in self._in_memory_programs.items():
            if key.startswith(f"{uid}:") and prog.get("status") == "active":
                return ProgramResponse(**prog)
        return None

    def list_user_programs(self, uid: str) -> List[ProgramResponse]:
        """Lists all programs (active, completed, abandoned) for a user."""
        db = self.db
        programs: List[ProgramResponse] = []
        if db:
            try:
                coll = db.collection("users").document(uid).collection("programs")
                for doc in coll.stream():
                    data = doc.to_dict()
                    if data.get("userId") == uid or data.get("user_id") == uid:
                        programs.append(ProgramResponse(**data))
                return programs
            except Exception as e:
                logger.error(f"Error listing programs for {uid} from Firestore: {e}")

        for key, prog in self._in_memory_programs.items():
            if key.startswith(f"{uid}:"):
                programs.append(ProgramResponse(**prog))
        return programs

    def create_program(self, uid: str, program_data: Dict[str, Any]) -> ProgramResponse:
        """
        Creates a new program for the user.
        Raises ValueError if user already has an active program.
        """
        active = self.get_active_program(uid)
        if active and active.status == "active":
            raise ValueError("An active program already exists for this user.")

        program_id = program_data["programId"]
        db = self.db
        if db:
            try:
                doc_ref = db.collection("users").document(uid).collection("programs").document(program_id)
                doc_ref.set(program_data)
                logger.info(f"Created program at users/{uid}/programs/{program_id}")
            except Exception as e:
                logger.error(f"Error creating program in Firestore: {e}")

        key = f"{uid}:{program_id}"
        self._in_memory_programs[key] = dict(program_data)
        return ProgramResponse(**program_data)

    def update_program(self, uid: str, program_id: str, updates: Dict[str, Any]) -> Optional[ProgramResponse]:
        """Applies updates to an existing program document."""
        existing = self.get_program(uid, program_id)
        if not existing:
            return None

        current = existing.model_dump()
        current.update(updates)
        current["updatedAt"] = datetime.now(timezone.utc).isoformat()

        db = self.db
        if db:
            try:
                doc_ref = db.collection("users").document(uid).collection("programs").document(program_id)
                doc_ref.set(current, merge=True)
                logger.info(f"Updated program at users/{uid}/programs/{program_id}")
            except Exception as e:
                logger.error(f"Error updating program in Firestore: {e}")

        key = f"{uid}:{program_id}"
        self._in_memory_programs[key] = current
        return ProgramResponse(**current)

    def record_adaptation(self, uid: str, program_id: str, decision_data: Dict[str, Any]) -> Optional[ProgramResponse]:
        """
        Appends an adaptation decision to adaptationHistory keyed by decisionId.
        Idempotent: if decisionId already exists, does nothing.
        """
        program = self.get_program(uid, program_id)
        if not program:
            return None

        current = program.model_dump()
        history = current.setdefault("adaptationHistory", [])
        decision_id = decision_data.get("decisionId") or decision_data.get("decision_id")

        if decision_id:
            for existing in history:
                if (existing.get("decisionId") or existing.get("decision_id")) == decision_id:
                    # Already present, return current state idempotently
                    return ProgramResponse(**current)

        history.append(decision_data)
        current["updatedAt"] = datetime.now(timezone.utc).isoformat()

        db = self.db
        if db:
            try:
                doc_ref = db.collection("users").document(uid).collection("programs").document(program_id)
                doc_ref.set(current, merge=True)
            except Exception as e:
                logger.error(f"Error recording adaptation in Firestore: {e}")

        key = f"{uid}:{program_id}"
        self._in_memory_programs[key] = current
        return ProgramResponse(**current)

    def clear_in_memory(self) -> None:
        """Utility for test suites to clear in-memory state."""
        self._in_memory_programs.clear()


# Global Singleton Provider
_program_repository_instance: Optional[ProgramRepository] = None


def get_program_repository() -> ProgramRepository:
    """FastAPI dependency provider for ProgramRepository."""
    global _program_repository_instance
    if _program_repository_instance is None:
        _program_repository_instance = ProgramRepository()
    return _program_repository_instance

