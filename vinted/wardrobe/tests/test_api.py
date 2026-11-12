"""
Tests for vinted.wardrobe.api item parsing.

Run:
    make test  (or: pytest vinted/wardrobe)
"""

from __future__ import annotations

from datetime import UTC
from datetime import datetime

from ..api import listed_at
from ..api import parse_item


def photo(url: str, timestamp: int | None) -> dict:
    hr = {"timestamp": timestamp} if timestamp is not None else None
    return {"url": url, "high_resolution": hr}


ITEM = {
    "id": 10746688465,
    "title": "Wodoszczelne buty sportowe do kostki",
    "url": "https://www.vinted.pl/items/10746688465-wodoszczelne-buty",
    "price": {"amount": "40.0", "currency_code": "PLN"},
    "brand": "H&M",
    "size": "29",
    "status": "Bardzo dobry",
    "favourite_count": 42,
    "view_count": 0,
    "is_closed": False,
    "photos": [photo("a.webp", 1794309720), photo("b.webp", 1794309700)],
}


###############################################################################
#  Parse Item — Vinted Fields Stored Under `api`
###############################################################################


def test_parse_item_keeps_api_fields_only() -> None:
    assert parse_item(ITEM) == {
        "id": 10746688465,
        "title": "Wodoszczelne buty sportowe do kostki",
        "url": "https://www.vinted.pl/items/10746688465-wodoszczelne-buty",
        "price": {"amount": "40.0", "currency_code": "PLN"},
        "brand": "H&M",
        "size": "29",
        "status": "Bardzo dobry",
        "photo_urls": ["a.webp", "b.webp"],
        "favourite_count": 42,
        "view_count": 0,
    }


def test_parse_item_tolerates_missing_fields() -> None:
    parsed = parse_item({"id": 1, "photos": None, "price": None})
    assert parsed["photo_urls"] == []
    assert parsed["price"] == {}


###############################################################################
#  Listed At — Earliest Photo Timestamp
###############################################################################


def test_listed_at_is_earliest_photo_timestamp() -> None:
    assert listed_at(ITEM) == datetime.fromtimestamp(1794309700, UTC)


def test_listed_at_skips_photos_without_timestamp() -> None:
    item = {"photos": [photo("a", None), photo("b", 1794309720)]}
    assert listed_at(item) == datetime.fromtimestamp(1794309720, UTC)


def test_listed_at_none_without_photos() -> None:
    assert listed_at({"photos": []}) is None
