"""
HTTP layer for purchased orders.

Auth is shared with favourites: cookies are read from `cookies.json`.

Pipeline per order:
  /api/v2/my_orders                       -> list of orders (paginated)
  /api/v2/escrow_orders/{tx_id}           -> payment breakdown + totals
  /api/v2/escrow_orders/{tx_id}/items     -> per-item paid price + size/condition
  /api/v2/transactions/{tx_id}            -> per-item photos/url/catalog + seller info
"""

from __future__ import annotations

import asyncio
import random

import httpx

from ..constants import USER_AGENT
from ..favourites import load_cookies
from .models import CurrencyConversion
from .models import Order
from .models import OrderItem

MY_ORDERS_URL = "https://www.vinted.pl/api/v2/my_orders"
ESCROW_ORDER_URL = "https://www.vinted.pl/api/v2/escrow_orders/{transaction_id}"
ESCROW_ITEMS_URL = "https://www.vinted.pl/api/v2/escrow_orders/{transaction_id}/items"
TRANSACTION_URL = "https://www.vinted.pl/api/v2/transactions/{transaction_id}"


def _amount(d: dict | None) -> float:
    if not d:
        return 0.0
    return float(d.get("amount", 0) or 0)


def _currency(d: dict | None) -> str:
    if not d:
        return ""
    return d.get("currency_code", "") or ""


async def _request(
    client: httpx.AsyncClient,
    url: str,
    *,
    params: dict | None = None,
    max_retries: int = 5,
) -> httpx.Response:
    """GET with exponential backoff on 429."""
    backoff = 2.0
    resp: httpx.Response | None = None
    for attempt in range(max_retries):
        resp = await client.get(url, params=params)
        if resp.status_code == 429:
            retry_after = float(resp.headers.get("Retry-After", backoff))
            sleep = retry_after + random.uniform(0, 1)
            print(f"-> 429, sleeping {sleep:.1f}s (attempt {attempt + 1}/{max_retries})")
            await asyncio.sleep(sleep)
            backoff *= 2
            continue
        return resp
    assert resp is not None
    return resp


async def fetch_my_orders(
    client: httpx.AsyncClient,
    *,
    status: str = "completed",
    per_page: int = 100,
    max_pages: int | None = None,
) -> list[dict]:
    """Fetch all `my_orders` entries with the given status (default: completed)."""
    orders: list[dict] = []
    page = 1
    while True:
        print(f"-> Fetching my_orders page {page}")
        resp = await _request(
            client,
            MY_ORDERS_URL,
            params={
                "type": "purchased",
                "status": status,
                "per_page": per_page,
                "page": page,
            },
        )
        resp.raise_for_status()
        page_orders = resp.json().get("my_orders", [])
        if not page_orders:
            break
        orders.extend(page_orders)
        if len(page_orders) < per_page:
            break
        if max_pages and page >= max_pages:
            break
        page += 1
    print(f"-> Total orders: {len(orders)}")
    return orders


async def fetch_escrow_order(client: httpx.AsyncClient, transaction_id: int) -> dict:
    resp = await _request(client, ESCROW_ORDER_URL.format(transaction_id=transaction_id))
    resp.raise_for_status()
    return resp.json().get("escrow_order", {})


async def fetch_escrow_order_items(client: httpx.AsyncClient, transaction_id: int) -> list[dict]:
    """Per-item details (title, size, condition, paid_price) for a transaction."""
    resp = await _request(client, ESCROW_ITEMS_URL.format(transaction_id=transaction_id))
    resp.raise_for_status()
    return resp.json().get("items", [])


async def fetch_transaction(client: httpx.AsyncClient, transaction_id: int) -> dict:
    """Transaction with `order.items[]` (photos, url, catalog_id, listed price) and seller."""
    resp = await _request(client, TRANSACTION_URL.format(transaction_id=transaction_id))
    resp.raise_for_status()
    return resp.json().get("transaction", {})


async def build_order(client: httpx.AsyncClient, raw_order: dict) -> Order:
    transaction_id = raw_order["transaction_id"]
    conversation_id = raw_order["conversation_id"]
    escrow, items_data, transaction = await asyncio.gather(
        fetch_escrow_order(client, transaction_id),
        fetch_escrow_order_items(client, transaction_id),
        fetch_transaction(client, transaction_id),
    )

    payment = escrow.get("payment_data", {})
    tx_items_by_id = {it["id"]: it for it in transaction.get("order", {}).get("items", [])}

    items: list[OrderItem] = []
    for it in items_data:
        paid_dict = it.get("paid_price_in_seller_currency") or {}
        tx_item = tx_items_by_id.get(it["id"], {})
        listed_dict = tx_item.get("price") or {}
        photos = tx_item.get("photos") or []
        items.append(
            OrderItem(
                id=it["id"],
                title=it.get("title", ""),
                size=it.get("size", "") or "",
                condition=it.get("status", "") or "",
                url=tx_item.get("url", ""),
                catalog_id=tx_item.get("catalog_id"),
                photo_url=it.get("photo_url", ""),
                photo_urls=[p["url"] for p in photos if p.get("url")],
                paid_price=_amount(paid_dict) or None,
                listed_price=_amount(listed_dict) or None,
                currency=_currency(paid_dict),
            )
        )

    seller = transaction.get("seller", {})
    conv_data = payment.get("conversion_data")
    conversion: CurrencyConversion | None = None
    if conv_data:
        conversion = CurrencyConversion(
            seller_currency=_currency(conv_data.get("base_rate")),
            buyer_currency=_currency(conv_data.get("rounded_rate")),
            rate=_amount(conv_data.get("rounded_rate")),
            fee_fraction=float(conv_data.get("rate") or 0),
            provider=conv_data.get("provider", "") or "",
            items_price_seller=_amount(conv_data.get("items_price")),
            shipment_price_seller=_amount(conv_data.get("shipment_price")),
        )

    total_price_dict = escrow.get("total_price") or {}
    return Order(
        transaction_id=transaction_id,
        conversation_id=conversation_id,
        purchase_id=escrow.get("purchase_id", "") or "",
        title=escrow.get("title", raw_order.get("title", "")),
        date=raw_order.get("date", escrow.get("created_at", "")),
        is_bundle=len(items) > 1,
        seller_id=escrow.get("seller_id", 0),
        seller_login=seller.get("login", ""),
        seller_country=seller.get("country_code", ""),
        items=items,
        items_price=_amount(payment.get("items_price", {}).get("price")),
        service_fee=_amount(payment.get("service_fee_price", {}).get("price")),
        shipment_price=_amount(payment.get("shipment_price", {}).get("price")),
        total_price=_amount(payment.get("total_price") or total_price_dict),
        currency=_currency(payment.get("total_price") or total_price_dict),
        status=escrow.get("status", ""),
        conversion=conversion,
    )


async def fetch_orders(
    *,
    status: str = "completed",
    per_page: int = 100,
    max_pages: int | None = None,
    skip_transaction_ids: set[int] | None = None,
) -> list[Order]:
    skip = skip_transaction_ids or set()
    cookies = load_cookies()
    async with httpx.AsyncClient(
        headers={
            "User-Agent": USER_AGENT,
            "Accept": "application/json, text/plain, */*",
        },
        cookies=cookies,
        follow_redirects=True,
    ) as client:
        raw_orders = await fetch_my_orders(
            client, status=status, per_page=per_page, max_pages=max_pages
        )
        orders: list[Order] = []
        for i, raw in enumerate(raw_orders, 1):
            tx_id = raw["transaction_id"]
            if tx_id in skip:
                print(f"-> [{i}/{len(raw_orders)}] tx={tx_id} (skipped, already saved)")
                continue
            print(f"-> [{i}/{len(raw_orders)}] tx={tx_id}")
            orders.append(await build_order(client, raw))
    return orders
