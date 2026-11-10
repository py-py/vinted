"""
Tests for vinted.wardrobe.sync diff logic (no Firestore, no HTTP).

Run:
    make test  (or: pytest vinted/wardrobe)
"""

from __future__ import annotations

from datetime import UTC
from datetime import datetime

from ..api import parse_item
from ..models import ItemState
from ..sync import SyncResult
from ..sync import apply_state
from ..sync import diff_fetched
from ..sync import member_doc

EARLIER = datetime(2026, 11, 1, tzinfo=UTC)
NOW = datetime(2026, 11, 10, 12, 0, tzinfo=UTC)


def raw(item_id: int, price: str = "100.0") -> dict:
    return {
        "id": item_id,
        "title": f"item {item_id}",
        "price": {"amount": price, "currency_code": "PLN"},
        "photos": [{"url": "p.webp", "high_resolution": {"timestamp": 1794309700}}],
        "user": {"login": "julia.wal802"},
    }


def saved(item_id: int, state: ItemState = ItemState.ACTIVE, **extra) -> dict:
    return {
        "api": parse_item(raw(item_id)),
        "state": state,
        "created_at": EARLIER,
        "updated_at": EARLIER,
        "last_seen_at": EARLIER,
        "gone_at": None,
        **extra,
    }


###############################################################################
#  Diff Fetched — New, Unchanged, Changed, Reappeared, Missing
###############################################################################


def test_new_item_is_created_active() -> None:
    result = diff_fetched([raw(1)], {}, NOW)

    assert result.new == [1]
    doc = result.updates[1]
    assert doc["state"] == ItemState.ACTIVE
    assert doc["created_at"] == doc["updated_at"] == doc["last_seen_at"] == NOW
    assert doc["gone_at"] is None
    assert doc["listed_at"] == datetime.fromtimestamp(1794309700, UTC)
    assert doc["api"]["title"] == "item 1"


def test_unchanged_item_only_moves_last_seen() -> None:
    result = diff_fetched([raw(1)], {1: saved(1)}, NOW)

    update = result.updates[1]
    assert update["last_seen_at"] == NOW
    assert "updated_at" not in update
    assert "created_at" not in update
    assert "state" not in update
    assert result.new == result.missing == []


def test_changed_api_bumps_updated_at() -> None:
    result = diff_fetched([raw(1, price="80.0")], {1: saved(1)}, NOW)

    assert result.updates[1]["updated_at"] == NOW
    assert result.updates[1]["api"]["price"]["amount"] == "80.0"
    assert result.changes == {}


def test_reappeared_item_goes_back_to_active() -> None:
    doc = saved(1, ItemState.RESERVED, gone_at=EARLIER)
    result = diff_fetched([raw(1)], {1: doc}, NOW)

    update = result.updates[1]
    assert update["state"] == ItemState.ACTIVE
    assert update["gone_at"] is None
    assert update["updated_at"] == NOW
    assert result.changes == {1: (ItemState.RESERVED, ItemState.ACTIVE)}


def test_missing_lists_only_open_states() -> None:
    docs = {
        1: saved(1, ItemState.ACTIVE),
        2: saved(2, ItemState.RESERVED),
        3: saved(3, ItemState.UNKNOWN),
        4: saved(4, ItemState.SOLD),
        5: saved(5, ItemState.DELETED),
    }
    result = diff_fetched([], docs, NOW)

    assert result.missing == [1, 2, 3]
    assert result.updates == {}


###############################################################################
#  Apply State — Page-Checked State of Missing Items
###############################################################################


def test_active_to_sold_sets_gone_at() -> None:
    result = SyncResult()
    apply_state(result, 1, saved(1), ItemState.SOLD, NOW)

    assert result.updates[1] == {"state": ItemState.SOLD, "updated_at": NOW, "gone_at": NOW}
    assert result.changes == {1: (ItemState.ACTIVE, ItemState.SOLD)}


def test_reserved_to_sold_keeps_first_gone_at() -> None:
    result = SyncResult()
    apply_state(result, 1, saved(1, ItemState.RESERVED, gone_at=EARLIER), ItemState.SOLD, NOW)

    assert "gone_at" not in result.updates[1]
    assert result.updates[1]["state"] == ItemState.SOLD


def test_reserved_back_to_active_clears_gone_at() -> None:
    result = SyncResult()
    apply_state(result, 1, saved(1, ItemState.RESERVED, gone_at=EARLIER), ItemState.ACTIVE, NOW)

    assert result.updates[1]["gone_at"] is None


def test_same_state_is_noop() -> None:
    result = SyncResult()
    apply_state(result, 1, saved(1, ItemState.RESERVED), ItemState.RESERVED, NOW)

    assert result.updates == {}
    assert result.changes == {}


###############################################################################
#  Member Doc — Counters and Timestamps
###############################################################################


def test_new_member_doc() -> None:
    fetched = [raw(1), raw(2)]
    result = diff_fetched(fetched, {}, NOW)
    doc = member_doc("282635132", fetched, {}, result, NOW, is_new=True)

    assert doc == {
        "api": {"user_id": 282635132, "login": "julia.wal802"},
        "last_fetched_at": NOW,
        "active_count": 2,
        "created_at": NOW,
        "updated_at": NOW,
    }


def test_member_counts_after_state_changes() -> None:
    docs = {1: saved(1), 2: saved(2), 3: saved(3, ItemState.SOLD)}
    fetched = [raw(1)]
    result = diff_fetched(fetched, docs, NOW)
    apply_state(result, 2, docs[2], ItemState.SOLD, NOW)
    doc = member_doc("1", fetched, docs, result, NOW, is_new=False)

    assert doc["active_count"] == 1
    assert doc["updated_at"] == NOW
    assert "created_at" not in doc


def test_quiet_sync_does_not_bump_member_updated_at() -> None:
    docs = {1: saved(1)}
    fetched = [raw(1)]
    result = diff_fetched(fetched, docs, NOW)
    doc = member_doc("1", fetched, docs, result, NOW, is_new=False)

    assert "updated_at" not in doc
    assert doc["last_fetched_at"] == NOW
