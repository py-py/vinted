from __future__ import annotations

from ..catalog import parse_catalog_url
from ..telegram import send_item
from .store import JsonStore
from .store import Subscription


def _item_id(item: dict) -> int | None:
    raw = item.get("id")
    return int(raw) if raw else None


def poll_subscription(store: JsonStore, sub: Subscription) -> int:
    """Poll one subscription, send new items, return how many were sent."""
    items = parse_catalog_url(sub.url)
    ids = [iid for it in items if (iid := _item_id(it)) is not None]
    if not ids:
        print(f"[{sub.id}] no items parsed")
        return 0

    # First run: seed the high-water mark, don't spam the whole page.
    if sub.last_seen_id is None:
        store.update_last_seen(sub.id, max(ids))
        print(f"[{sub.id}] seeded last_seen_id={max(ids)} (no messages sent)")
        return 0

    new_items = [it for it in items if (iid := _item_id(it)) and iid > sub.last_seen_id]
    new_items.sort(key=lambda it: int(it["id"]))  # oldest -> newest

    for item in new_items:
        send_item(sub.telegram_chat_id, item)

    if new_items:
        store.update_last_seen(sub.id, max(int(it["id"]) for it in new_items))

    print(f"[{sub.id}] sent {len(new_items)} new item(s)")
    return len(new_items)


def run_once(store: JsonStore) -> None:
    subs = store.list_active_subscriptions()
    print(f"Polling {len(subs)} active subscription(s)")
    for sub in subs:
        poll_subscription(store, sub)
