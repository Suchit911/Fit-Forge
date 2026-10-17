import uuid
from datetime import datetime, timezone
from typing import Optional, List, Dict, Any
from google.cloud import firestore
from ..core.firebase import get_firestore_db
from ..core.config import settings
from ..utils.logger import logger

_SENTINEL = object()

ALLOWED_CONVERSATION_FIELDS = {
    "id",
    "title",
    "createdAt",
    "updatedAt",
    "previewText",
    "messageCount",
}

ALLOWED_MESSAGE_FIELDS = {
    "id",
    "conversationId",
    "sender",
    "text",
    "createdAt",
}


def sanitize_conversation_data(data: Dict[str, Any]) -> Dict[str, Any]:
    """Ensures only authoritative conversation fields are persisted."""
    clean = {k: v for k, v in data.items() if k in ALLOWED_CONVERSATION_FIELDS}
    now_iso = datetime.now(timezone.utc).isoformat()
    if "createdAt" not in clean or not clean["createdAt"]:
        clean["createdAt"] = now_iso
    if "updatedAt" not in clean or not clean["updatedAt"]:
        clean["updatedAt"] = now_iso
    if "previewText" not in clean:
        clean["previewText"] = ""
    if "messageCount" not in clean:
        clean["messageCount"] = 0
    return clean


def sanitize_message_data(data: Dict[str, Any]) -> Dict[str, Any]:
    """Ensures only authoritative message fields are persisted."""
    clean = {k: v for k, v in data.items() if k in ALLOWED_MESSAGE_FIELDS}
    if "createdAt" not in clean or not clean["createdAt"]:
        clean["createdAt"] = datetime.now(timezone.utc).isoformat()
    return clean


class CoachRepository:
    """
    Data access layer for user-scoped Coach conversations and messages:
    users/{uid}/coach_conversations/{conversation_id}
    users/{uid}/coach_conversations/{conversation_id}/messages/{message_id}
    """

    def __init__(self, db: Any = _SENTINEL):
        self._db = db
        # In-memory store for isolated unit tests when db=None
        # _conversations_store: Dict[uid, Dict[conversation_id, Dict[str, Any]]]
        self._conversations_store: Dict[str, Dict[str, Dict[str, Any]]] = {}
        # _messages_store: Dict[uid, Dict[conversation_id, List[Dict[str, Any]]]]
        self._messages_store: Dict[str, Dict[str, List[Dict[str, Any]]]] = {}

    @property
    def db(self) -> Optional[Any]:
        if self._db is not _SENTINEL:
            return self._db
        return get_firestore_db()

    def create_conversation(
        self,
        uid: str,
        title: Optional[str] = None,
        initial_preview: str = "",
        conversation_id: Optional[str] = None,
    ) -> Dict[str, Any]:
        """Creates a new conversation thread under users/{uid}/coach_conversations."""
        cid = conversation_id or f"conv_{int(datetime.now(timezone.utc).timestamp())}_{uuid.uuid4().hex[:6]}"
        now_iso = datetime.now(timezone.utc).isoformat()
        conv_title = (title.strip() if title and title.strip() else "Workout Plan Advice")

        data: Dict[str, Any] = {
            "id": cid,
            "title": conv_title,
            "createdAt": now_iso,
            "updatedAt": now_iso,
            "previewText": initial_preview.strip()[:120] if initial_preview else "",
            "messageCount": 0,
        }
        sanitized = sanitize_conversation_data(data)

        db = self.db
        if db:
            try:
                doc_ref = db.collection("users").document(uid).collection("coach_conversations").document(cid)
                doc_ref.set(sanitized)
                return sanitized
            except Exception as e:
                logger.error(f"Failed to create conversation {cid} in Firestore: {e}")
                raise

        # In-memory fallback
        if uid not in self._conversations_store:
            self._conversations_store[uid] = {}
        self._conversations_store[uid][cid] = sanitized
        return sanitized

    def get_conversation(self, uid: str, conversation_id: str) -> Optional[Dict[str, Any]]:
        """Retrieves a single conversation by ID for the authenticated user."""
        db = self.db
        if db:
            try:
                doc_ref = db.collection("users").document(uid).collection("coach_conversations").document(conversation_id)
                doc = doc_ref.get()
                if doc.exists:
                    return doc.to_dict()
                return None
            except Exception as e:
                logger.error(f"Failed to retrieve conversation {conversation_id} from Firestore: {e}")
                return None

        # In-memory fallback
        user_convs = self._conversations_store.get(uid, {})
        return user_convs.get(conversation_id)

    def list_conversations(self, uid: str, limit: int = 20) -> List[Dict[str, Any]]:
        """Lists user conversations ordered by updatedAt descending."""
        eff_limit = min(limit, settings.COACH_MAX_CONVERSATIONS_PER_USER)

        db = self.db
        if db:
            try:
                col_ref = (
                    db.collection("users")
                    .document(uid)
                    .collection("coach_conversations")
                    .order_by("updatedAt", direction=firestore.Query.DESCENDING)
                    .limit(eff_limit)
                )
                docs = col_ref.stream()
                return [d.to_dict() for d in docs]
            except Exception as e:
                logger.error(f"Failed to list conversations for user {uid} in Firestore: {e}")
                return []

        # In-memory fallback
        user_convs = list(self._conversations_store.get(uid, {}).values())
        user_convs.sort(key=lambda x: x.get("updatedAt", ""), reverse=True)
        return user_convs[:eff_limit]

    def update_conversation(
        self,
        uid: str,
        conversation_id: str,
        preview_text: str = "",
        increment_count: bool = True,
    ) -> Optional[Dict[str, Any]]:
        """Updates the conversation's updatedAt, previewText, and increments messageCount."""
        conv = self.get_conversation(uid, conversation_id)
        if not conv:
            return None

        now_iso = datetime.now(timezone.utc).isoformat()
        new_count = conv.get("messageCount", 0) + (1 if increment_count else 0)
        updates: Dict[str, Any] = {
            "updatedAt": now_iso,
            "previewText": preview_text.strip()[:120] if preview_text else conv.get("previewText", ""),
            "messageCount": new_count,
        }

        db = self.db
        if db:
            try:
                doc_ref = db.collection("users").document(uid).collection("coach_conversations").document(conversation_id)
                doc_ref.update(updates)
                conv.update(updates)
                return conv
            except Exception as e:
                logger.error(f"Failed to update conversation {conversation_id} in Firestore: {e}")
                return None

        # In-memory fallback
        conv.update(updates)
        self._conversations_store[uid][conversation_id] = conv
        return conv

    def delete_conversation(self, uid: str, conversation_id: str) -> bool:
        """Deletes a conversation thread and its messages for the authenticated user."""
        db = self.db
        if db:
            try:
                doc_ref = db.collection("users").document(uid).collection("coach_conversations").document(conversation_id)
                doc = doc_ref.get()
                if not doc.exists:
                    return False

                # Delete subcollection messages
                messages_ref = doc_ref.collection("messages").stream()
                for msg_doc in messages_ref:
                    msg_doc.reference.delete()

                # Delete conversation document
                doc_ref.delete()
                return True
            except Exception as e:
                logger.error(f"Failed to delete conversation {conversation_id} in Firestore: {e}")
                return False

        # In-memory fallback
        user_convs = self._conversations_store.get(uid, {})
        if conversation_id not in user_convs:
            return False
        del user_convs[conversation_id]
        if uid in self._messages_store and conversation_id in self._messages_store[uid]:
            del self._messages_store[uid][conversation_id]
        return True

    def create_message(
        self,
        uid: str,
        conversation_id: str,
        sender: str,
        text: str,
        message_id: Optional[str] = None,
    ) -> Dict[str, Any]:
        """Creates a new message under users/{uid}/coach_conversations/{conversation_id}/messages."""
        mid = message_id or f"msg_{int(datetime.now(timezone.utc).timestamp())}_{uuid.uuid4().hex[:6]}"
        now_iso = datetime.now(timezone.utc).isoformat()

        data: Dict[str, Any] = {
            "id": mid,
            "conversationId": conversation_id,
            "sender": sender,
            "text": text.strip(),
            "createdAt": now_iso,
        }
        sanitized = sanitize_message_data(data)

        db = self.db
        if db:
            try:
                doc_ref = (
                    db.collection("users")
                    .document(uid)
                    .collection("coach_conversations")
                    .document(conversation_id)
                    .collection("messages")
                    .document(mid)
                )
                doc_ref.set(sanitized)
                # Update conversation updatedAt and preview snippet
                self.update_conversation(uid, conversation_id, preview_text=text, increment_count=True)
                return sanitized
            except Exception as e:
                logger.error(f"Failed to create message {mid} in Firestore: {e}")
                raise

        # In-memory fallback
        if uid not in self._messages_store:
            self._messages_store[uid] = {}
        if conversation_id not in self._messages_store[uid]:
            self._messages_store[uid][conversation_id] = []
        self._messages_store[uid][conversation_id].append(sanitized)

        # Update conversation
        self.update_conversation(uid, conversation_id, preview_text=text, increment_count=True)
        return sanitized

    def list_messages(self, uid: str, conversation_id: str, limit: int = 50) -> List[Dict[str, Any]]:
        """Lists messages for a conversation ordered chronologically ascending."""
        eff_limit = min(limit, settings.COACH_MAX_MESSAGES_PER_CONVERSATION)

        db = self.db
        if db:
            try:
                col_ref = (
                    db.collection("users")
                    .document(uid)
                    .collection("coach_conversations")
                    .document(conversation_id)
                    .collection("messages")
                    .order_by("createdAt", direction=firestore.Query.ASCENDING)
                    .limit(eff_limit)
                )
                docs = col_ref.stream()
                return [d.to_dict() for d in docs]
            except Exception as e:
                logger.error(f"Failed to list messages for conv {conversation_id} in Firestore: {e}")
                return []

        # In-memory fallback
        messages = self._messages_store.get(uid, {}).get(conversation_id, [])
        sorted_msgs = sorted(messages, key=lambda x: x.get("createdAt", ""))
        return sorted_msgs[:eff_limit]

    def count_conversations(self, uid: str) -> int:
        """Returns the total number of conversations for the user."""
        db = self.db
        if db:
            try:
                col_ref = db.collection("users").document(uid).collection("coach_conversations")
                return len(list(col_ref.stream()))
            except Exception as e:
                logger.error(f"Failed to count conversations for user {uid}: {e}")
                return 0

        return len(self._conversations_store.get(uid, {}))


_coach_repo_instance: Optional[CoachRepository] = None


def get_coach_repository() -> CoachRepository:
    """Returns the singleton CoachRepository instance."""
    global _coach_repo_instance
    if _coach_repo_instance is None:
        _coach_repo_instance = CoachRepository()
    return _coach_repo_instance
