from __future__ import annotations

import json
import uuid
from datetime import UTC
from datetime import datetime
from pathlib import Path

from pydantic import BaseModel

DEFAULT_STATE_PATH = Path("notifier_state.json")


class Subscription(BaseModel):
    id: str
    telegram_chat_id: int
    url: str
    last_seen_id: int | None = None
    active: bool = True
    created_at: str


class JsonStore:
    """Local JSON-file store. Drop-in stand-in for the future Firestore store."""

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
        sub = Subscription(
            id=uuid.uuid4().hex[:8],
            telegram_chat_id=telegram_chat_id,
            url=url,
            created_at=datetime.now(UTC).isoformat(),
        )
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
