"""
Tests for vinted.wardrobe.status against item-page fragments.

The fragments mirror the JSON-escaped Next.js flight data of real pages
captured on 2026-11-10: 10720963834 (sold), 10723152138 (reserved),
10747201625 (active).

Run:
    make test  (or: pytest vinted/wardrobe)
"""

from __future__ import annotations

import httpx
import pytest

from ..models import ItemState
from ..status import check_item_state
from ..status import parse_item_state

pytestmark = pytest.mark.anyio


def status_plugin(item_id: str, theme: str, title: str) -> str:
    return (
        r"{\"plugins\":[{\"data\":{\"item_id\":\"" + item_id + r"\",\"seller_id\":\"1\","
        r"\"theme\":\"" + theme + r"\",\"title\":\"" + title + r"\"},"
        r"\"exposures\":[],\"name\":\"buyer_item_status\",\"section\":\"sidebar\"}]}"
    )


def item_flags(*, can_buy: bool, is_reserved: bool) -> str:
    b = str(can_buy).lower()
    r = str(is_reserved).lower()
    return (
        r"\"is_hated\":false,\"can_buy\":" + b + r",\"instant_buy\":" + b + ","
        r"\"is_reserved\":" + r + r",\"is_hidden\":false}"
    )


SOLD = status_plugin("10720963834", "SUCCESS", "Sprzedane") + item_flags(
    can_buy=False, is_reserved=False
)
RESERVED = status_plugin("10723152138", "AMPLIFIED", "Zarezerwowane") + item_flags(
    can_buy=True, is_reserved=True
)
ACTIVE = r"\"availability\":\"InStock\"," + item_flags(can_buy=True, is_reserved=False)


###############################################################################
#  Parse Item State — Page Markers
###############################################################################


@pytest.mark.parametrize(
    ("html", "expected"),
    [
        (SOLD, ItemState.SOLD),
        (RESERVED, ItemState.RESERVED),
        (ACTIVE, ItemState.ACTIVE),
    ],
    ids=["sold", "reserved", "active"],
)
def test_parse_item_state(html: str, expected: ItemState) -> None:
    assert parse_item_state(html) == expected


def test_reserved_flag_without_plugin_is_reserved() -> None:
    assert parse_item_state(item_flags(can_buy=True, is_reserved=True)) == ItemState.RESERVED


def test_can_buy_alone_is_not_active() -> None:
    assert parse_item_state(item_flags(can_buy=True, is_reserved=False)) == ItemState.UNKNOWN


def test_unknown_plugin_title_falls_through() -> None:
    html = status_plugin("1", "WARNING", "Ukryte") + item_flags(can_buy=False, is_reserved=False)
    assert parse_item_state(html) == ItemState.UNKNOWN


def test_schema_org_availability_url_is_active() -> None:
    assert parse_item_state('"availability":"https://schema.org/InStock"') == ItemState.ACTIVE


###############################################################################
#  Check Item State — HTTP Status Handling
###############################################################################


def client_returning(status: int, text: str = "") -> httpx.AsyncClient:
    return httpx.AsyncClient(
        transport=httpx.MockTransport(lambda _: httpx.Response(status, text=text))
    )


async def test_404_is_deleted() -> None:
    async with client_returning(404) as client:
        assert await check_item_state(client, 1072096380) == ItemState.DELETED


async def test_200_is_parsed() -> None:
    async with client_returning(200, SOLD) as client:
        assert await check_item_state(client, 10720963834) == ItemState.SOLD


async def test_other_errors_raise() -> None:
    async with client_returning(429) as client:
        with pytest.raises(httpx.HTTPStatusError):
            await check_item_state(client, 1)
