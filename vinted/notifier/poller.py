from __future__ import annotations

import time
from urllib.parse import parse_qsl
from urllib.parse import urlencode
from urllib.parse import urlparse
from urllib.parse import urlunparse

from ..catalog import parse_catalog_url
from ..constants import NOTIFIER_MAX_PAGES
from ..telegram import send_item
from .store import JsonStore
from .store import Subscription

PAGE_DELAY_SECONDS = 0.3


def get_item_id(item: dict) -> int | None:
    raw = item.get("id")
    return int(raw) if raw else None


def _with_page(url: str, page: int) -> str:
    parts = urlparse(url)
    query = dict(parse_qsl(parts.query, keep_blank_values=True))
    query["page"] = str(page)
    return urlunparse(parts._replace(query=urlencode(query)))


def collect_new_items(url: str, last_seen_id: int) -> list[dict]:
    """Walk catalog pages (newest first) until we reach already-seen items.

    Stops at the first page that contains an item with id <= last_seen_id, or
    after NOTIFIER_MAX_PAGES pages (safety cap against floods / non-monotonic ids).
    """
    new_items: list[dict] = []
    for page in range(1, NOTIFIER_MAX_PAGES + 1):
        if page > 1:
            time.sleep(PAGE_DELAY_SECONDS)
        items = parse_catalog_url(_with_page(url, page))
        if not items:
            break
        new_items += [it for it in items if (i := get_item_id(it)) and i > last_seen_id]
        if any((i := get_item_id(it)) and i <= last_seen_id for it in items):
            break  # reached already-seen items; nothing older is new
    return new_items


def poll_subscription(store: JsonStore, sub: Subscription) -> int:
    """Poll one subscription, send new items, return how many were sent."""
    # First run: seed the high-water mark from page 1, don't spam the whole page.
    if sub.last_seen_id is None:
        items = parse_catalog_url(sub.url)
        ids = [item_id for item in items if (item_id := get_item_id(item)) is not None]
        if not ids:
            print(f"[{sub.id}] no items parsed")
            return 0
        store.update_last_seen(sub.id, max(ids))
        print(f"[{sub.id}] seeded last_seen_id={max(ids)} (no messages sent)")
        return 0

    new_items = collect_new_items(sub.url, sub.last_seen_id)
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
