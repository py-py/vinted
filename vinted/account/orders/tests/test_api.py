"""
Tests for vinted.account.orders.api against recorded Vinted API responses.

Fixtures in ./fixtures/ are raw JSON responses captured on 2026-10-15
for transaction 22646003889 (a 3-item bundle from an EE seller, paid in PLN).
They reflect the API shape after ~2026-09:
  - my_orders: `photo` is null, thumbnail moved to top-level `photo_url`;
    `conversation_id` is a UUID string, `date` is UTC with `Z`.
  - escrow_orders/{tx}/items: `size`, `status` are "" and
    `paid_price_in_seller_currency` is null; size/condition come from
    transactions/{tx} -> order.items[].

Run:
    make test  (or: pytest vinted/account/orders)
"""

from __future__ import annotations

import json
from collections.abc import Awaitable
from collections.abc import Callable
from pathlib import Path

import httpx
import pytest

from ..api import ESCROW_ITEMS_URL
from ..api import ESCROW_ORDER_URL
from ..api import MY_ORDERS_URL
from ..api import TRANSACTION_URL
from ..api import build_order
from ..api import fetch_my_orders

pytestmark = pytest.mark.anyio

FIXTURES = Path(__file__).resolve().parent / "fixtures"
TX = 22646003889
CONVERSATION_ID = "01a0e1f0-5731-7836-9bf0-76c74a079965"

ESCROW_ORDER = ESCROW_ORDER_URL.format(transaction_id=TX)
ESCROW_ITEMS = ESCROW_ITEMS_URL.format(transaction_id=TX)
TRANSACTION = TRANSACTION_URL.format(transaction_id=TX)


def load(name: str) -> dict:
    return json.loads((FIXTURES / f"{name}.json").read_text())


@pytest.fixture
def calls() -> list[httpx.Request]:
    return []


###############################################################################
#  Fetch My Orders — Pagination and Query Params
###############################################################################


@pytest.fixture
def paged_client(calls: list[httpx.Request]) -> Callable[[list[dict]], httpx.AsyncClient]:
    """Factory: client serving `pages` in order for my_orders; further pages are empty."""

    def make(pages: list[dict]) -> httpx.AsyncClient:
        def handler(request: httpx.Request) -> httpx.Response:
            calls.append(request)
            page = int(request.url.params["page"])
            body = pages[page - 1] if page <= len(pages) else {"my_orders": []}
            return httpx.Response(200, json=body)

        return httpx.AsyncClient(transport=httpx.MockTransport(handler))

    return make


async def test_paginates_and_concatenates_orders(paged_client, calls) -> None:
    pages = [load("my_orders_page1"), load("my_orders_page2")]
    async with paged_client(pages) as client:
        orders = await fetch_my_orders(client, per_page=2, max_pages=2)

    expected = [o["transaction_id"] for p in pages for o in p["my_orders"]]
    assert [o["transaction_id"] for o in orders] == expected
    assert len(calls) == 2


async def test_sends_expected_query_params(paged_client, calls) -> None:
    async with paged_client([load("my_orders_page1")]) as client:
        await fetch_my_orders(client, status="completed", per_page=2, max_pages=1)

    request = calls[0]
    assert str(request.url.copy_with(query=None)) == MY_ORDERS_URL
    assert dict(request.url.params) == {
        "type": "purchased",
        "status": "completed",
        "per_page": "2",
        "page": "1",
    }


async def test_stops_on_empty_page(paged_client, calls) -> None:
    pages = [load("my_orders_page1"), load("my_orders_page2")]
    async with paged_client(pages) as client:
        orders = await fetch_my_orders(client, per_page=2)

    assert len(orders) == 4
    assert [int(r.url.params["page"]) for r in calls] == [1, 2, 3]


async def test_stops_on_short_page(paged_client, calls) -> None:
    async with paged_client([load("my_orders_page1")]) as client:
        orders = await fetch_my_orders(client, per_page=100)

    assert len(orders) == 2
    assert len(calls) == 1


async def test_returns_raw_order_dicts(paged_client) -> None:
    async with paged_client([load("my_orders_page1")]) as client:
        orders = await fetch_my_orders(client, per_page=100)

    first = orders[0]
    assert first["transaction_id"] == TX
    assert first["conversation_id"] == CONVERSATION_ID
    assert first["photo"] is None
    assert first["photo_url"].startswith("https://images1.vinted.net/")


###############################################################################
#  Build Order — Merging Escrow and Transaction Data
###############################################################################


@pytest.fixture
def raw_order() -> dict:
    return load("my_orders_page1")["my_orders"][0]


@pytest.fixture
def routes() -> dict[str, dict]:
    """Responses by URL (query ignored); tests may mutate or drop entries."""
    return {
        ESCROW_ORDER: load("escrow_order"),
        ESCROW_ITEMS: load("escrow_order_items"),
        TRANSACTION: load("transaction"),
    }


@pytest.fixture
def build(routes, calls, raw_order) -> Callable[..., Awaitable]:
    """Run build_order against `routes`; pass `raw` to override the my_orders entry."""

    def handler(request: httpx.Request) -> httpx.Response:
        calls.append(request)
        url = str(request.url.copy_with(query=None))
        if url not in routes:
            return httpx.Response(404, json={"code": 404, "message": f"no fixture for {url}"})
        return httpx.Response(200, json=routes[url])

    async def run(raw: dict | None = None):
        async with httpx.AsyncClient(transport=httpx.MockTransport(handler)) as client:
            return await build_order(client, raw or raw_order)

    return run


async def test_requests_all_three_endpoints(build, calls, routes) -> None:
    await build()

    assert {str(r.url) for r in calls} == set(routes)


async def test_order_fields(build) -> None:
    order = await build()

    assert order.transaction_id == TX
    assert order.conversation_id == CONVERSATION_ID
    assert order.purchase_id == "KvXExBSJiW-oeW7GNGnNS"
    assert order.title == "Bundle 3 items"
    assert order.date == "2026-09-27T08:17:23Z"
    assert order.is_bundle
    assert order.seller_id == 312208246
    assert order.seller_login == "helina2r"
    assert order.seller_country == "EE"
    assert order.status == "completed"


async def test_order_photo_url_from_top_level_field(build, raw_order) -> None:
    order = await build()

    assert order.photo_url == raw_order["photo_url"]


async def test_order_photo_url_prefers_legacy_photo_object(build, raw_order) -> None:
    order = await build({**raw_order, "photo": {"url": "https://legacy/photo.jpg"}})

    assert order.photo_url == "https://legacy/photo.jpg"


async def test_order_prices(build) -> None:
    order = await build()

    assert order.items_price == 147.5
    assert order.service_fee == 10.28
    assert order.shipment_price == 11.47
    assert order.total_price == 169.25
    assert order.currency == "PLN"


async def test_currency_conversion(build) -> None:
    order = await build()

    conv = order.conversion
    assert conv is not None
    assert conv.seller_currency == "EUR"
    assert conv.buyer_currency == "PLN"
    assert conv.rate == 4.43
    assert conv.fee_fraction == 0.012
    assert conv.provider == "Adyen N.V."
    assert conv.items_price_seller == 33.3
    assert conv.shipment_price_seller == 2.59


async def test_no_conversion_when_absent(build, routes) -> None:
    routes[ESCROW_ORDER]["escrow_order"]["payment_data"]["conversion_data"] = None
    order = await build()

    assert order.conversion is None


async def test_items_merged_from_escrow_and_transaction(build) -> None:
    order = await build()

    got = [
        (i.id, i.size, i.condition, i.listed_price, i.catalog_id, len(i.photo_urls))
        for i in order.items
    ]
    assert got == [
        (10092914997, "38", "Good", 53.09, 2632, 4),
        (10149546725, "44", "Very good", 66.36, 1242, 4),
        (10149615955, "45", "Good", 44.24, 1242, 5),
    ]
    first = order.items[0]
    assert first.title == "Rohelised Jordan Low/ Nike"
    assert first.url == "https://www.vinted.pl/items/10092914997-rohelised-jordan-low-nike"
    assert first.photo_url.startswith("https://images1.vinted.net/")
    assert not first.is_deleted


async def test_items_without_paid_price(build) -> None:
    order = await build()

    for item in order.items:
        assert item.paid_price is None
        assert item.currency == ""


async def test_items_prefer_escrow_values_when_present(build, routes) -> None:
    """Legacy shape: escrow items carried size/status/paid price themselves."""
    routes[ESCROW_ITEMS]["items"][0].update(
        size="39",
        status="Very good",
        paid_price_in_seller_currency={"amount": "12.00", "currency_code": "EUR"},
    )
    order = await build()

    first = order.items[0]
    assert first.size == "39"
    assert first.condition == "Very good"
    assert first.paid_price == 12.0
    assert first.currency == "EUR"


async def test_raises_on_http_error(build, routes) -> None:
    del routes[TRANSACTION]

    with pytest.raises(httpx.HTTPStatusError):
        await build()
