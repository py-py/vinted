"""
Tests for vinted.account.sales.api against recorded Vinted API responses.

Fixtures in ./fixtures/ are raw JSON responses captured on 2026-10-24
from api.vinted.pl escrow-orders (type=sold, status=completed, per_page=2),
plus escrow_orders/{tx}[/items] and transactions/{tx} for bundle 22009759206
(4 items, listed 170 PLN, sold for 123.82). Buyer login/photo are scrubbed.

Run:
    make test  (or: pytest vinted/account/sales)
"""

from __future__ import annotations

import json
from collections.abc import Awaitable
from collections.abc import Callable
from pathlib import Path

import httpx
import pytest

from vinted.account.orders.api import ESCROW_ITEMS_URL
from vinted.account.orders.api import ESCROW_ORDER_URL
from vinted.account.orders.api import TRANSACTION_URL

from ..api import SOLD_ORDERS_URL
from ..api import allocate_sold_prices
from ..api import build_sale
from ..api import fetch_sold_orders

pytestmark = pytest.mark.anyio

FIXTURES = Path(__file__).resolve().parent / "fixtures"


def load(name: str) -> dict:
    return json.loads((FIXTURES / f"{name}.json").read_text())


@pytest.fixture
def calls() -> list[httpx.Request]:
    return []


###############################################################################
#  Fetch Sold Orders — Pagination and Query Params
###############################################################################


@pytest.fixture
def paged_client(calls: list[httpx.Request]) -> Callable[[list[dict]], httpx.AsyncClient]:
    """Factory: client serving `pages` in order; further pages are empty."""

    def make(pages: list[dict]) -> httpx.AsyncClient:
        def handler(request: httpx.Request) -> httpx.Response:
            calls.append(request)
            page = int(request.url.params["page"])
            body = pages[page - 1] if page <= len(pages) else {"my_orders": []}
            return httpx.Response(200, json=body)

        return httpx.AsyncClient(transport=httpx.MockTransport(handler))

    return make


async def test_paginates_and_concatenates_orders(paged_client, calls) -> None:
    pages = [load("sold_orders_page1"), load("sold_orders_page2")]
    async with paged_client(pages) as client:
        orders = await fetch_sold_orders(client, per_page=2, max_pages=2)

    expected = [o["transaction_id"] for p in pages for o in p["my_orders"]]
    assert [o["transaction_id"] for o in orders] == expected
    assert len(calls) == 2


async def test_sends_expected_query_params(paged_client, calls) -> None:
    async with paged_client([load("sold_orders_page1")]) as client:
        await fetch_sold_orders(client, status="completed", per_page=2, max_pages=1)

    request = calls[0]
    assert str(request.url.copy_with(query=None)) == SOLD_ORDERS_URL
    assert dict(request.url.params) == {
        "type": "sold",
        "status": "completed",
        "per_page": "2",
        "page": "1",
    }


async def test_stops_on_empty_page(paged_client, calls) -> None:
    pages = [load("sold_orders_page1"), load("sold_orders_page2")]
    async with paged_client(pages) as client:
        orders = await fetch_sold_orders(client, per_page=2)

    assert len(orders) == 4
    assert [int(r.url.params["page"]) for r in calls] == [1, 2, 3]


async def test_stops_on_short_page(paged_client, calls) -> None:
    async with paged_client([load("sold_orders_page1")]) as client:
        orders = await fetch_sold_orders(client, per_page=100)

    assert len(orders) == 2
    assert len(calls) == 1


###############################################################################
#  Build Sale — Merging Escrow and Transaction Data
###############################################################################

BUNDLE_TX = 22009759206


@pytest.fixture
def raw_sale() -> dict:
    """my_orders-style list entry for BUNDLE_TX (escrow/transaction fixtures)."""
    return {
        "conversation_id": "01a065ef-b27c-7592-8fe6-ce55a46cfbb0",
        "date": "2026-09-03T12:40:41Z",
        "escrow_order_id": BUNDLE_TX,
        "photo_url": "https://images1.vinted.net/t/thumb.jpeg",
        "price": {"amount": "123.82", "currency_code": "PLN"},
        "status": "Order completed successfully. The buyer accepted the item.",
        "title": "Bundle 4 items",
        "transaction_id": BUNDLE_TX,
        "transaction_user_status": "completed",
    }


@pytest.fixture
def routes() -> dict[str, dict]:
    """Responses by URL (query ignored); tests may mutate or drop entries."""
    return {
        ESCROW_ORDER_URL.format(transaction_id=BUNDLE_TX): load("escrow_order"),
        ESCROW_ITEMS_URL.format(transaction_id=BUNDLE_TX): load("escrow_order_items"),
        TRANSACTION_URL.format(transaction_id=BUNDLE_TX): load("transaction"),
    }


@pytest.fixture
def build(routes, calls, raw_sale) -> Callable[..., Awaitable]:
    """Run build_sale against `routes`; pass `raw` to override the list entry."""

    def handler(request: httpx.Request) -> httpx.Response:
        calls.append(request)
        url = str(request.url.copy_with(query=None))
        if url not in routes:
            return httpx.Response(404, json={"code": 404, "message": f"no fixture for {url}"})
        return httpx.Response(200, json=routes[url])

    async def run(raw: dict | None = None):
        async with httpx.AsyncClient(transport=httpx.MockTransport(handler)) as client:
            return await build_sale(client, raw or raw_sale)

    return run


async def test_requests_all_three_endpoints(build, calls, routes) -> None:
    await build()

    assert {str(r.url) for r in calls} == set(routes)


async def test_sale_fields(build, raw_sale) -> None:
    sale = await build()

    assert sale.transaction_id == BUNDLE_TX
    assert sale.escrow_order_id == BUNDLE_TX
    assert sale.conversation_id == raw_sale["conversation_id"]
    assert sale.title == "Bundle 4 items"
    assert sale.date == "2026-09-03T12:40:41Z"
    assert sale.is_bundle
    assert sale.buyer_id == 75448096
    assert sale.buyer_login == "buyer_login"
    assert sale.buyer_country == "CZ"
    assert sale.transaction_user_status == "completed"
    assert sale.photo_url == raw_sale["photo_url"]


async def test_sale_prices(build) -> None:
    sale = await build()

    assert sale.items_price == 123.82
    assert sale.shipment_price == 15.59
    assert sale.currency == "PLN"


async def test_sale_items_from_transaction(build) -> None:
    sale = await build()

    assert [it.id for it in sale.items] == [9045748399, 9276940986, 9349739917, 9349784676]
    first = sale.items[0]
    assert first.title.startswith("Legginsy Nike Pro")
    assert first.size == "M / 38 / 10"
    assert first.condition == "New without tags"
    assert first.catalog_id == 573
    assert len(first.photo_urls) == 10
    assert first.url.startswith("https://www.vinted.pl/items/9045748399")
    assert first.photo_url.startswith("https://images1.vinted.net/")
    assert first.currency == "PLN"
    assert not first.is_deleted


async def test_bundle_sold_prices_split_by_listed_price(build) -> None:
    sale = await build()

    assert [it.listed_price for it in sale.items] == [40.0, 30.0, 50.0, 50.0]
    assert [it.sold_price for it in sale.items] == [29.13, 21.85, 36.42, 36.42]
    assert round(sum(it.sold_price for it in sale.items), 2) == sale.items_price


async def test_single_item_sold_price_is_items_price(build, routes) -> None:
    tx = routes[TRANSACTION_URL.format(transaction_id=BUNDLE_TX)]["transaction"]
    tx["order"]["items"] = tx["order"]["items"][:1]
    escrow_items = routes[ESCROW_ITEMS_URL.format(transaction_id=BUNDLE_TX)]
    escrow_items["items"] = escrow_items["items"][:1]
    sale = await build()

    assert not sale.is_bundle
    assert sale.items[0].sold_price == 123.82


async def test_deleted_listings_fall_back_to_escrow_items(build, routes) -> None:
    """Old sold listings get deleted: transaction has `order.items: []`."""
    routes[TRANSACTION_URL.format(transaction_id=BUNDLE_TX)]["transaction"]["order"]["items"] = []
    for it in routes[ESCROW_ITEMS_URL.format(transaction_id=BUNDLE_TX)]["items"]:
        it["is_deleted"] = True
        it["photo_url"] = None
    sale = await build()

    assert len(sale.items) == 4
    assert sale.items[0].title.startswith("Legginsy Nike Pro")
    assert all(it.is_deleted and it.listed_price is None for it in sale.items)
    assert [it.sold_price for it in sale.items] == [30.95, 30.95, 30.95, 30.97]


###############################################################################
#  Allocate Sold Prices — Proportional Split
###############################################################################


def test_allocate_assigns_rounding_remainder_to_last() -> None:
    assert allocate_sold_prices(10.0, [1.0, 1.0, 1.0]) == [3.33, 3.33, 3.34]


def test_allocate_splits_evenly_without_listed_prices() -> None:
    assert allocate_sold_prices(9.0, [0.0, 0.0]) == [4.5, 4.5]


def test_allocate_empty() -> None:
    assert allocate_sold_prices(9.0, []) == []
