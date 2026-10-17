from datetime import datetime, timezone
from typing import Optional, List, Dict, Any, Tuple
from google.api_core.exceptions import AlreadyExists, Conflict
from ..core.firebase import get_firestore_db
from ..utils.logger import logger

_SENTINEL = object()

ALLOWED_PERSISTED_FIELDS = {
    "id",
    "type",
    "category",
    "title",
    "message",
    "createdAt",
    "read",
    "readAt",
    "important",
    "iconName",
    "actionLabel",
    "actionRoute",
    "sourceId",
}


def sanitize_notification_data(data: Dict[str, Any]) -> Dict[str, Any]:
    """
    Strips non-authoritative display fields (e.g. timestamp, dateGroup)
    and ensures only authorized fields are persisted.
    """
    clean = {k: v for k, v in data.items() if k in ALLOWED_PERSISTED_FIELDS}
    if "read" not in clean:
        clean["read"] = False
    if "readAt" not in clean:
        clean["readAt"] = None
    if "important" not in clean:
        clean["important"] = False
    if "createdAt" not in clean or not clean["createdAt"]:
        clean["createdAt"] = datetime.now(timezone.utc).isoformat()
    return clean


class NotificationRepository:
    """
    Data access layer for user-scoped Notification documents stored in Cloud Firestore:
    users/{uid}/notifications/{notification_id}
    """

    def __init__(self, db: Any = _SENTINEL):
        self._db = db
        # In-memory store: Dict[uid, Dict[notification_id, Dict[str, Any]]]
        self._in_memory_store: Dict[str, Dict[str, Dict[str, Any]]] = {}

    @property
    def db(self) -> Optional[Any]:
        if self._db is not _SENTINEL:
            return self._db
        return get_firestore_db()

    def get_notification(self, uid: str, notification_id: str) -> Optional[Dict[str, Any]]:
        """Retrieves a single notification by ID for the given user."""
        db = self.db
        if db:
            try:
                doc_ref = db.collection("users").document(uid).collection("notifications").document(notification_id)
                doc = doc_ref.get()
                if doc.exists:
                    data = doc.to_dict()
                    self._in_memory_store.setdefault(uid, {})[notification_id] = data
                    return data
                return None
            except Exception as e:
                logger.warning(f"Error fetching notification {notification_id} for user {uid}: {e}")

        user_store = self._in_memory_store.get(uid, {})
        data = user_store.get(notification_id)
        return dict(data) if data else None

    def create_or_ignore(self, uid: str, data: Dict[str, Any]) -> Tuple[Dict[str, Any], bool]:
        """
        Atomically creates a notification document if it does not already exist.
        If it already exists, returns the existing document without altering any field.
        Returns: (doc_dict, was_created)
        """
        clean_data = sanitize_notification_data(data)
        doc_id = clean_data["id"]

        user_store = self._in_memory_store.setdefault(uid, {})
        user_store[doc_id] = dict(clean_data)

        db = self.db
        if db:
            doc_ref = db.collection("users").document(uid).collection("notifications").document(doc_id)
            try:
                doc_ref.create(clean_data)
                logger.info(f"Created notification {doc_id} for user {uid}")
                return clean_data, True
            except (AlreadyExists, Conflict):
                try:
                    existing = doc_ref.get()
                    existing_dict = existing.to_dict() if existing.exists else clean_data
                    user_store[doc_id] = dict(existing_dict)
                    return existing_dict, False
                except Exception:
                    return clean_data, False
            except Exception as e:
                err_msg = str(e).lower()
                if "already exists" in err_msg or "conflict" in err_msg:
                    try:
                        existing = doc_ref.get()
                        existing_dict = existing.to_dict() if existing.exists else clean_data
                        user_store[doc_id] = dict(existing_dict)
                        return existing_dict, False
                    except Exception:
                        return clean_data, False
                logger.warning(f"Error creating notification {doc_id} for user {uid}: {e}")

        return dict(clean_data), True

    def list_notifications(
        self, uid: str, limit: int = 50, before: Optional[str] = None
    ) -> List[Dict[str, Any]]:
        """
        Retrieves paginated notifications ordered by createdAt DESC, id DESC.
        Uses cursor-based pagination via 'before' ISO timestamp / tie-breaker.
        """
        db = self.db
        if db:
            try:
                col_ref = db.collection("users").document(uid).collection("notifications")
                query = col_ref.order_by("createdAt", direction="DESCENDING")
                if before:
                    query = query.start_after({"createdAt": before})
                docs = query.limit(limit).stream()
                return [d.to_dict() for d in docs]
            except Exception as e:
                logger.error(f"Error listing notifications for user {uid}: {e}")

        user_store = self._in_memory_store.get(uid, {})
        items = list(user_store.values())
        # Sort by createdAt DESC, id DESC
        items.sort(key=lambda x: (x.get("createdAt", ""), x.get("id", "")), reverse=True)

        if before:
            filtered = []
            matched_cursor = False
            for it in items:
                if matched_cursor:
                    filtered.append(it)
                elif it.get("createdAt") == before or it.get("id") == before:
                    matched_cursor = True
            items = filtered

        return [dict(x) for x in items[:limit]]

    def get_all_user_notifications(self, uid: str) -> List[Dict[str, Any]]:
        """
        Retrieves all notifications for user to compute comprehensive dashboard KPIs.
        """
        db = self.db
        if db:
            try:
                col_ref = db.collection("users").document(uid).collection("notifications")
                docs = col_ref.stream()
                return [d.to_dict() for d in docs]
            except Exception as e:
                logger.error(f"Error fetching all notifications for user {uid}: {e}")

        user_store = self._in_memory_store.get(uid, {})
        return [dict(x) for x in user_store.values()]

    def get_unread_count(self, uid: str) -> int:
        """Returns total unread count for user."""
        db = self.db
        if db:
            try:
                col_ref = db.collection("users").document(uid).collection("notifications")
                query = col_ref.where("read", "==", False)
                # Count queries in google-cloud-firestore
                results = list(query.stream())
                return len(results)
            except Exception as e:
                logger.error(f"Error counting unread notifications for user {uid}: {e}")

        user_store = self._in_memory_store.get(uid, {})
        return sum(1 for n in user_store.values() if not n.get("read", False))

    def mark_as_read(self, uid: str, notification_id: str) -> Optional[Dict[str, Any]]:
        """
        Marks single notification as read. Idempotent.
        Returns updated document dict or None if not found.
        """
        now_iso = datetime.now(timezone.utc).isoformat()
        db = self.db
        if db:
            try:
                doc_ref = db.collection("users").document(uid).collection("notifications").document(notification_id)
                doc = doc_ref.get()
                if not doc.exists:
                    return None
                data = doc.to_dict()
                if not data.get("read", False):
                    doc_ref.update({"read": True, "readAt": now_iso})
                    data["read"] = True
                    data["readAt"] = now_iso
                return data
            except Exception as e:
                logger.error(f"Error marking notification {notification_id} as read for user {uid}: {e}")
                raise e

        user_store = self._in_memory_store.get(uid, {})
        if notification_id not in user_store:
            return None
        data = user_store[notification_id]
        if not data.get("read", False):
            data["read"] = True
            data["readAt"] = now_iso
        return dict(data)

    def mark_all_as_read(self, uid: str) -> int:
        """
        Marks all user notifications as read. Idempotent.
        Returns number of notifications marked.
        """
        now_iso = datetime.now(timezone.utc).isoformat()
        db = self.db
        if db:
            try:
                col_ref = db.collection("users").document(uid).collection("notifications")
                unread_docs = list(col_ref.where("read", "==", False).stream())
                if not unread_docs:
                    return 0

                batch = db.batch()
                for d in unread_docs:
                    batch.update(d.reference, {"read": True, "readAt": now_iso})
                batch.commit()
                return len(unread_docs)
            except Exception as e:
                logger.error(f"Error marking all notifications read for user {uid}: {e}")
                raise e

        user_store = self._in_memory_store.get(uid, {})
        count = 0
        for n in user_store.values():
            if not n.get("read", False):
                n["read"] = True
                n["readAt"] = now_iso
                count += 1
        return count

    def prune_user_notifications(
        self, uid: str, max_keep: int = 100, newly_created_id: Optional[str] = None
    ) -> int:
        """
        Pruning policy:
        - Target maximum: 100 notifications per user.
        - Prune oldest READ notifications first.
        - NEVER delete unread notifications to satisfy cap.
        - If all notifications are unread, temporarily exceed 100.
        - Never delete the notification just created.
        - Delete non-important read records before important read records.
        """
        all_items = self.get_all_user_notifications(uid)
        total_count = len(all_items)
        if total_count <= max_keep:
            return 0

        excess = total_count - max_keep

        # Find eligible read notifications
        eligible = [
            n for n in all_items
            if n.get("read", False) and n.get("id") != newly_created_id
        ]

        if not eligible:
            # All are unread or only newly_created exists -> temporarily exceed 100
            return 0

        # Sort: non-important first, then oldest createdAt first
        eligible.sort(
            key=lambda x: (
                1 if x.get("important", False) else 0,
                x.get("createdAt", ""),
                x.get("id", ""),
            )
        )

        to_delete = eligible[:excess]
        deleted_count = 0

        db = self.db
        if db:
            try:
                batch = db.batch()
                col_ref = db.collection("users").document(uid).collection("notifications")
                for item in to_delete:
                    batch.delete(col_ref.document(item["id"]))
                    deleted_count += 1
                batch.commit()
                logger.info(f"Pruned {deleted_count} old read notifications for user {uid}")
                return deleted_count
            except Exception as e:
                logger.warning(f"Failed to prune old notifications for user {uid}: {e}")
                return 0

        user_store = self._in_memory_store.get(uid, {})
        for item in to_delete:
            user_store.pop(item["id"], None)
            deleted_count += 1
        return deleted_count


_repository_instance: Optional[NotificationRepository] = None


def get_notification_repository() -> NotificationRepository:
    global _repository_instance
    if _repository_instance is None:
        _repository_instance = NotificationRepository()
    return _repository_instance
