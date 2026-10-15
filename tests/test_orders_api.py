"""
Tests for vinted.account.orders.api against recorded Vinted API responses.

Fixtures in tests/fixtures/vinted/ are raw JSON responses captured on 2026-10-15
for transaction 22646003889 (a 3-item bundle from an EE seller, paid in PLN).
They reflect the API shape after ~2026-09:
  - my_orders: `photo` is null, thumbnail moved to top-level `photo_url`;
    `conversation_id` is a UUID string, `date` is UTC with `Z`.
  - escrow_orders/{tx}/items: `size`, `status` are "" and
    `paid_price_in_seller_currency` is null; size/condition come from
    transactions/{tx} -> order.items[].

Run:
    python -m unittest discover tests
"""

from __future__ import annotations

import copy
import json
import unittest
from pathlib import Path

import httpx

from vinted.account.orders.api import ESCROW_ITEMS_URL
from vinted.account.orders.api import ESCROW_ORDER_URL
from vinted.account.orders.api import MY_ORDERS_URL
from vinted.account.orders.api import TRANSACTION_URL
from vinted.account.orders.api import build_order
from vinted.account.orders.api import fetch_my_orders

FIXTURES = Path(__file__).resolve().parent / "fixtures" / "vinted"
TX = 22646003889


def load(name: str) -> dict:
    return json.loads((FIXTURES / f"{name}.json").read_text())


def make_client(routes: dict[str, dict], calls: list[httpx.Request]) -> httpx.AsyncClient:
    """AsyncClient whose responses are looked up by URL path (query ignored)."""

    def handler(request: httpx.Request) -> httpx.Response:
        calls.append(request)
        url = str(request.url.copy_with(query=None))
        if url not in routes:
            return httpx.Response(404, json={"code": 404, "message": f"no fixture for {url}"})
        return httpx.Response(200, json=routes[url])

    return httpx.AsyncClient(transport=httpx.MockTransport(handler))


class FetchMyOrdersTest(unittest.IsolatedAsyncioTestCase):
    def setUp(self) -> None:
        self.calls: list[httpx.Request] = []

    def make_paged_client(self, pages: list[dict]) -> httpx.AsyncClient:
        """Serve `pages` in order for my_orders; any further page is empty."""

        def handler(request: httpx.Request) -> httpx.Response:
            self.calls.append(request)
            page = int(request.url.params["page"])
            body = pages[page - 1] if page <= len(pages) else {"my_orders": []}
            return httpx.Response(200, json=body)

        return httpx.AsyncClient(transport=httpx.MockTransport(handler))

    async def test_paginates_and_concatenates_orders(self) -> None:
        pages = [load("my_orders_page1"), load("my_orders_page2")]
        async with self.make_paged_client(pages) as client:
            orders = await fetch_my_orders(client, per_page=2, max_pages=2)

        expected = [o["transaction_id"] for p in pages for o in p["my_orders"]]
        self.assertEqual([o["transaction_id"] for o in orders], expected)
        self.assertEqual(len(self.calls), 2)

    async def test_sends_expected_query_params(self) -> None:
        async with self.make_paged_client([load("my_orders_page1")]) as client:
            await fetch_my_orders(client, status="completed", per_page=2, max_pages=1)

        request = self.calls[0]
        self.assertEqual(str(request.url.copy_with(query=None)), MY_ORDERS_URL)
        self.assertEqual(
            dict(request.url.params),
            {"type": "purchased", "status": "completed", "per_page": "2", "page": "1"},
        )

    async def test_stops_on_empty_page(self) -> None:
        pages = [load("my_orders_page1"), load("my_orders_page2")]
        async with self.make_paged_client(pages) as client:
            orders = await fetch_my_orders(client, per_page=2)

        self.assertEqual(len(orders), 4)
        self.assertEqual([int(r.url.params["page"]) for r in self.calls], [1, 2, 3])

    async def test_stops_on_short_page(self) -> None:
        async with self.make_paged_client([load("my_orders_page1")]) as client:
            orders = await fetch_my_orders(client, per_page=100)

        self.assertEqual(len(orders), 2)
        self.assertEqual(len(self.calls), 1)

    async def test_returns_raw_order_dicts(self) -> None:
        async with self.make_paged_client([load("my_orders_page1")]) as client:
            orders = await fetch_my_orders(client, per_page=100)

        first = orders[0]
        self.assertEqual(first["transaction_id"], TX)
        self.assertEqual(first["conversation_id"], "01a0e1f0-5731-7836-9bf0-76c74a079965")
        self.assertIsNone(first["photo"])
        self.assertTrue(first["photo_url"].startswith("https://images1.vinted.net/"))


class BuildOrderTest(unittest.IsolatedAsyncioTestCase):
    def setUp(self) -> None:
        self.calls: list[httpx.Request] = []
        self.raw_order = load("my_orders_page1")["my_orders"][0]
        self.routes = {
            ESCROW_ORDER_URL.format(transaction_id=TX): load("escrow_order"),
            ESCROW_ITEMS_URL.format(transaction_id=TX): load("escrow_order_items"),
            TRANSACTION_URL.format(transaction_id=TX): load("transaction"),
        }

    async def build(self):
        async with make_client(self.routes, self.calls) as client:
            return await build_order(client, self.raw_order)

    async def test_requests_all_three_endpoints(self) -> None:
        await self.build()

        requested = {str(r.url) for r in self.calls}
        self.assertEqual(requested, set(self.routes))

    async def test_order_fields(self) -> None:
        order = await self.build()

        self.assertEqual(order.transaction_id, TX)
        self.assertEqual(order.conversation_id, "01a0e1f0-5731-7836-9bf0-76c74a079965")
        self.assertEqual(order.purchase_id, "KvXExBSJiW-oeW7GNGnNS")
        self.assertEqual(order.title, "Bundle 3 items")
        self.assertEqual(order.date, "2026-09-27T08:17:23Z")
        self.assertTrue(order.is_bundle)
        self.assertEqual(order.seller_id, 312208246)
        self.assertEqual(order.seller_login, "helina2r")
        self.assertEqual(order.seller_country, "EE")
        self.assertEqual(order.status, "completed")

    async def test_order_photo_url_from_top_level_field(self) -> None:
        order = await self.build()

        self.assertEqual(order.photo_url, self.raw_order["photo_url"])

    async def test_order_photo_url_prefers_legacy_photo_object(self) -> None:
        self.raw_order = {**self.raw_order, "photo": {"url": "https://legacy/photo.jpg"}}
        order = await self.build()

        self.assertEqual(order.photo_url, "https://legacy/photo.jpg")

    async def test_order_prices(self) -> None:
        order = await self.build()

        self.assertEqual(order.items_price, 147.5)
        self.assertEqual(order.service_fee, 10.28)
        self.assertEqual(order.shipment_price, 11.47)
        self.assertEqual(order.total_price, 169.25)
        self.assertEqual(order.currency, "PLN")

    async def test_currency_conversion(self) -> None:
        order = await self.build()

        conv = order.conversion
        self.assertIsNotNone(conv)
        self.assertEqual(conv.seller_currency, "EUR")
        self.assertEqual(conv.buyer_currency, "PLN")
        self.assertEqual(conv.rate, 4.43)
        self.assertEqual(conv.fee_fraction, 0.012)
        self.assertEqual(conv.provider, "Adyen N.V.")
        self.assertEqual(conv.items_price_seller, 33.3)
        self.assertEqual(conv.shipment_price_seller, 2.59)

    async def test_no_conversion_when_absent(self) -> None:
        escrow = copy.deepcopy(self.routes[ESCROW_ORDER_URL.format(transaction_id=TX)])
        escrow["escrow_order"]["payment_data"]["conversion_data"] = None
        self.routes[ESCROW_ORDER_URL.format(transaction_id=TX)] = escrow
        order = await self.build()

        self.assertIsNone(order.conversion)

    async def test_items_merged_from_escrow_and_transaction(self) -> None:
        order = await self.build()

        got = [
            (i.id, i.size, i.condition, i.listed_price, i.catalog_id, len(i.photo_urls))
            for i in order.items
        ]
        self.assertEqual(
            got,
            [
                (10092914997, "38", "Good", 53.09, 2632, 4),
                (10149546725, "44", "Very good", 66.36, 1242, 4),
                (10149615955, "45", "Good", 44.24, 1242, 5),
            ],
        )
        first = order.items[0]
        self.assertEqual(first.title, "Rohelised Jordan Low/ Nike")
        self.assertEqual(
            first.url, "https://www.vinted.pl/items/10092914997-rohelised-jordan-low-nike"
        )
        self.assertTrue(first.photo_url.startswith("https://images1.vinted.net/"))
        self.assertFalse(first.is_deleted)

    async def test_items_without_paid_price(self) -> None:
        order = await self.build()

        for item in order.items:
            self.assertIsNone(item.paid_price)
            self.assertEqual(item.currency, "")

    async def test_items_prefer_escrow_values_when_present(self) -> None:
        """Legacy shape: escrow items carried size/status/paid price themselves."""
        items = copy.deepcopy(self.routes[ESCROW_ITEMS_URL.format(transaction_id=TX)])
        items["items"][0].update(
            size="39",
            status="Very good",
            paid_price_in_seller_currency={"amount": "12.00", "currency_code": "EUR"},
        )
        self.routes[ESCROW_ITEMS_URL.format(transaction_id=TX)] = items
        order = await self.build()

        first = order.items[0]
        self.assertEqual(first.size, "39")
        self.assertEqual(first.condition, "Very good")
        self.assertEqual(first.paid_price, 12.0)
        self.assertEqual(first.currency, "EUR")

    async def test_raises_on_http_error(self) -> None:
        del self.routes[TRANSACTION_URL.format(transaction_id=TX)]

        with self.assertRaises(httpx.HTTPStatusError):
            await self.build()


if __name__ == "__main__":
    unittest.main()
