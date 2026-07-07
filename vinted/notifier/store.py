from __future__ import annotations

import hashlib
import json
import os
from datetime import UTC
from datetime import datetime
from pathlib import Path

from pydantic import BaseModel

try:
    from google.cloud import firestore
    from google.cloud.firestore_v1.base_query import FieldFilter
except ImportError:  # firestore is optional when running the json backend
    firestore = None
    FieldFilter = None

DEFAULT_STATE_PATH = Path("notifier_state.json")
DEFAULT_COLLECTION = "subscriptions"


class Subscription(BaseModel):
    id: str
    telegram_chat_id: int
    url: str
    last_seen_id: int | None = None
    active: bool = True
    created_at: str


def _subscription_id(url: str) -> str:
    """Deterministic id derived from the URL, so the same link can't be subscribed twice."""
    return hashlib.md5(url.encode("utf-8"), usedforsecurity=False).hexdigest()


def _new_subscription(telegram_chat_id: int, url: str) -> Subscription:
    return Subscription(
        id=_subscription_id(url),
        telegram_chat_id=telegram_chat_id,
        url=url,
        created_at=datetime.now(UTC).isoformat(),
    )


class JsonStore:
    """Local JSON-file store. Drop-in stand-in for the Firestore store."""

    def __init__(self, path: Path | str = DEFAULT_STATE_PATH) -> None:
        self.path = Path(path)

    def _load(self) -> dict:
        if not self.path.exists():
            return {"subscriptions": []}
        return json.loads(self.path.read_text())

    def _save(self, data: dict) -> None:
        self.path.write_text(json.dumps(data, indent=2, ensure_ascii=False))

    def list_active_subscriptions(self) -> list[Subscription]:
        data = self._load()
        return [Subscription(**raw) for raw in data["subscriptions"] if raw.get("active", True)]

    def add_subscription(self, telegram_chat_id: int, url: str) -> Subscription:
        data = self._load()
        sub_id = _subscription_id(url)
        for raw in data["subscriptions"]:
            if raw["id"] == sub_id:
                return Subscription(**raw)
        sub = _new_subscription(telegram_chat_id, url)
        data["subscriptions"].append(sub.model_dump())
        self._save(data)
        return sub

    def update_last_seen(self, sub_id: str, last_seen_id: int) -> None:
        data = self._load()
        for raw in data["subscriptions"]:
            if raw["id"] == sub_id:
                raw["last_seen_id"] = last_seen_id
                break
        self._save(data)


class FirestoreStore:
    """Firestore-backed store. Same interface as JsonStore."""

    def __init__(
        self,
        project: str | None = None,
        database: str | None = None,
        collection: str | None = None,
    ) -> None:
        if firestore is None:
            raise RuntimeError("google-cloud-firestore is not installed; run `uv sync`")
        self._client = firestore.Client(
            project=project or os.environ.get("GOOGLE_CLOUD_PROJECT"),
            database=database or os.environ.get("FIRESTORE_DATABASE", "(default)"),
        )
        self._collection = collection or os.environ.get("FIRESTORE_COLLECTION", DEFAULT_COLLECTION)

    def _col(self):
        return self._client.collection(self._collection)

    def list_active_subscriptions(self) -> list[Subscription]:
        docs = self._col().where(filter=FieldFilter("active", "==", True)).stream()
        return [Subscription(id=doc.id, **doc.to_dict()) for doc in docs]

    def add_subscription(self, telegram_chat_id: int, url: str) -> Subscription:
        doc = self._col().document(_subscription_id(url))
        snapshot = doc.get()
        if snapshot.exists:
            return Subscription(id=doc.id, **snapshot.to_dict())
        sub = _new_subscription(telegram_chat_id, url)
        doc.set(sub.model_dump(exclude={"id"}))
        return sub

    def update_last_seen(self, sub_id: str, last_seen_id: int) -> None:
        self._col().document(sub_id).update({"last_seen_id": last_seen_id})


def get_store() -> JsonStore | FirestoreStore:
    """Pick the store backend via NOTIFIER_STORE env ('firestore' default, or 'json')."""
    backend = os.environ.get("NOTIFIER_STORE", "firestore").lower()
    if backend == "json":
        return JsonStore()
    return FirestoreStore()
