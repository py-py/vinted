"""Sync a member's wardrobe into Firestore and detect new / reserved / sold / deleted items.

Item doc (wardrobe/{user_id}/items/{item_id}): Vinted data under `api`, our
own fields at the top level — see PLAN.md for the layout.
"""

from __future__ import annotations

from dataclasses import dataclass
from dataclasses import field
from datetime import UTC
from datetime import datetime

import httpx

from ..constants import USER_AGENT
from ..storage import FirestoreStore
from .api import fetch_wardrobe
from .api import listed_at
from .api import parse_item
from .models import OPEN_STATES
from .models import ItemState
from .status import check_item_state


@dataclass
class SyncResult:
    """Item field updates to write, plus what changed for reporting."""

    updates: dict[int, dict] = field(default_factory=dict)
    new: list[int] = field(default_factory=list)
    missing: list[int] = field(default_factory=list)
    changes: dict[int, tuple[ItemState, ItemState]] = field(default_factory=dict)


###############################################################################
#  Diff — Fetched Wardrobe vs Saved Items
###############################################################################


def diff_fetched(fetched: list[dict], saved: dict[int, dict], now: datetime) -> SyncResult:
    """Compare fetched wardrobe items with saved docs.

    New items are created, present items refreshed (reappeared ones go back
    to active), and open-state items not in the fetch are listed in `missing`
    for a page check.
    """
    result = SyncResult()
    fetched_ids: set[int] = set()

    for raw in fetched:
        item_id = int(raw["id"])
        fetched_ids.add(item_id)
        api = parse_item(raw)
        doc = saved.get(item_id)

        if doc is None:
            result.new.append(item_id)
            result.updates[item_id] = {
                "api": api,
                "listed_at": listed_at(raw),
                "state": ItemState.ACTIVE,
                "created_at": now,
                "updated_at": now,
                "last_seen_at": now,
                "gone_at": None,
            }
            continue

        update: dict = {"api": api, "listed_at": listed_at(raw), "last_seen_at": now}
        old_state = ItemState(doc.get("state", ItemState.ACTIVE))
        if old_state != ItemState.ACTIVE:
            result.changes[item_id] = (old_state, ItemState.ACTIVE)
            update |= {"state": ItemState.ACTIVE, "gone_at": None}
        if old_state != ItemState.ACTIVE or doc.get("api") != api:
            update["updated_at"] = now
        result.updates[item_id] = update

    result.missing = sorted(
        item_id
        for item_id, doc in saved.items()
        if item_id not in fetched_ids and doc.get("state", ItemState.ACTIVE) in OPEN_STATES
    )
    return result


def apply_state(
    result: SyncResult, item_id: int, doc: dict, state: ItemState, now: datetime
) -> None:
    """Record the page-checked state of a missing item (no-op if unchanged)."""
    old_state = ItemState(doc.get("state", ItemState.ACTIVE))
    if state == old_state:
        return
    update: dict = {"state": state, "updated_at": now}
    if state == ItemState.ACTIVE:
        update["gone_at"] = None
    elif not doc.get("gone_at"):
        update["gone_at"] = now
    result.changes[item_id] = (old_state, state)
    result.updates[item_id] = update


###############################################################################
#  Sync — Fetch, Check Missing Items, Save
###############################################################################


async def sync_wardrobe(user_id: str, store: FirestoreStore) -> SyncResult:
    now = datetime.now(UTC)
    fetched = await fetch_wardrobe(user_id)
    saved = store.load_wardrobe_items(user_id)
    result = diff_fetched(fetched, saved, now)

    if result.missing:
        print(f"-> Checking {len(result.missing)} missing item(s)")
        async with httpx.AsyncClient(
            headers={"User-Agent": USER_AGENT}, follow_redirects=True
        ) as client:
            for item_id in result.missing:
                try:
                    state = await check_item_state(client, item_id)
                except httpx.HTTPError as exc:
                    # Keep the saved state; the item is re-checked next run.
                    print(f"   ! {item_id}: {exc!r}")
                    continue
                apply_state(result, item_id, saved[item_id], state, now)

    is_new_member = store.get_wardrobe_member(user_id) is None
    member = member_doc(user_id, fetched, saved, result, now, is_new=is_new_member)
    store.save_wardrobe(user_id, member, result.updates)
    return result


def member_doc(
    user_id: str,
    fetched: list[dict],
    saved: dict[int, dict],
    result: SyncResult,
    now: datetime,
    *,
    is_new: bool,
) -> dict:
    """Fields of wardrobe/{user_id} to write for this sync."""
    states = {item_id: doc.get("state", ItemState.ACTIVE) for item_id, doc in saved.items()}
    states |= {item_id: u["state"] for item_id, u in result.updates.items() if "state" in u}

    doc: dict = {
        "last_fetched_at": now,
        "active_count": sum(1 for s in states.values() if s == ItemState.ACTIVE),
    }
    if fetched and (login := (fetched[0].get("user") or {}).get("login")):
        doc["api"] = {"user_id": int(user_id), "login": login}
    if is_new:
        doc["created_at"] = now
    if is_new or any("updated_at" in u for u in result.updates.values()):
        doc["updated_at"] = now
    return doc
