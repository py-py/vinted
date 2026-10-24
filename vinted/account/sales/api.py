"""
HTTP layer for sold orders.

Auth is shared with orders: cookies are read from `cookies.json`.

Pipeline per sale:
  api.vinted.pl/escrow-orders/api/v2/current-user/escrow-orders?type=sold
                                          -> list of sold orders (paginated, same
                                             shape as `my_orders` + `escrow_order_id`)
  /api/v2/escrow_orders/{tx_id}           -> items price + shipment
  /api/v2/escrow_orders/{tx_id}/items     -> item ids/titles (kept for deleted listings)
  /api/v2/transactions/{tx_id}            -> per-item listed price/photos/url + buyer

Vinted deletes old sold listings (~3 months); `transactions/{tx}` then returns
`order.items: []`, so escrow items are the source of truth for the item list.

Vinted does not return a per-item sold price (escrow items have it null), so for
bundles `items_price` is split across items proportionally to `listed_price`.
"""

from __future__ import annotations

import asyncio

import httpx

from vinted.account.cookies import load_cookies
from vinted.account.orders.api import _amount
from vinted.account.orders.api import _currency
from vinted.account.orders.api import _request
from vinted.account.orders.api import fetch_escrow_order
from vinted.account.orders.api import fetch_escrow_order_items
from vinted.account.orders.api import fetch_transaction
from vinted.constants import USER_AGENT

from .models import Sale
from .models import SaleItem

SOLD_ORDERS_URL = "https://api.vinted.pl/escrow-orders/api/v2/current-user/escrow-orders"


async def fetch_sold_orders(
    client: httpx.AsyncClient,
    *,
    status: str = "completed",
    per_page: int = 100,
    max_pages: int | None = None,
) -> list[dict]:
    """Fetch all sold escrow orders with the given status (default: completed)."""
    orders: list[dict] = []
    page = 1
    while True:
        print(f"-> Fetching sold orders page {page}")
        resp = await _request(
            client,
            SOLD_ORDERS_URL,
            params={
                "type": "sold",
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
    print(f"-> Total sold orders: {len(orders)}")
    return orders


def allocate_sold_prices(total: float, listed: list[float]) -> list[float]:
    """Split `total` by `listed` shares (evenly if none listed); rounding remainder on last."""
    if not listed:
        return []
    weight = sum(listed)
    shares = [p / weight for p in listed] if weight else [1 / len(listed)] * len(listed)
    prices = [round(total * s, 2) for s in shares]
    prices[-1] = round(total - sum(prices[:-1]), 2)
    return prices


async def build_sale(client: httpx.AsyncClient, raw: dict) -> Sale:
    transaction_id = raw["transaction_id"]
    escrow, items_data, transaction = await asyncio.gather(
        fetch_escrow_order(client, transaction_id),
        fetch_escrow_order_items(client, transaction_id),
        fetch_transaction(client, transaction_id),
    )

    payment = escrow.get("payment_data") or {}
    items_price_dict = (payment.get("items_price") or {}).get("price") or raw.get("price") or {}
    items_price = _amount(items_price_dict)
    currency = _currency(items_price_dict)

    tx_items_by_id = {it["id"]: it for it in transaction.get("order", {}).get("items", [])}
    tx_items = [tx_items_by_id.get(it["id"], {}) for it in items_data]
    listed = [_amount(tx.get("price")) for tx in tx_items]
    sold = allocate_sold_prices(items_price, listed)

    items: list[SaleItem] = []
    for it, tx_item, listed_price, sold_price in zip(
        items_data, tx_items, listed, sold, strict=True
    ):
        photos = tx_item.get("photos") or []
        items.append(
            SaleItem(
                id=it["id"],
                title=it.get("title") or tx_item.get("title", "") or "",
                size=it.get("size") or tx_item.get("size_title", "") or "",
                condition=it.get("status") or tx_item.get("status", "") or "",
                url=tx_item.get("url", ""),
                catalog_id=tx_item.get("catalog_id"),
                photo_url=it.get("photo_url", "") or "",
                photo_urls=[p["url"] for p in photos if p.get("url")],
                listed_price=listed_price or None,
                sold_price=sold_price,
                currency=_currency(tx_item.get("price")) or currency,
                is_deleted=bool(it.get("is_deleted")),
            )
        )

    buyer = transaction.get("buyer") or {}
    return Sale(
        transaction_id=transaction_id,
        escrow_order_id=raw.get("escrow_order_id") or transaction_id,
        conversation_id=raw["conversation_id"],
        title=raw.get("title", "") or escrow.get("title", ""),
        date=raw.get("date", "") or escrow.get("created_at", ""),
        is_bundle=len(items) > 1,
        buyer_id=buyer.get("id") or escrow.get("buyer_id"),
        buyer_login=buyer.get("login", "") or "",
        buyer_country=buyer.get("country_code", "") or "",
        items=items,
        items_price=items_price,
        shipment_price=_amount((payment.get("shipment_price") or {}).get("price")),
        currency=currency,
        status=raw.get("status", ""),
        transaction_user_status=raw.get("transaction_user_status", "") or "",
        photo_url=raw.get("photo_url", "") or "",
    )


async def fetch_sales(
    *,
    status: str = "completed",
    per_page: int = 100,
    max_pages: int | None = None,
) -> list[Sale]:
    cookies = load_cookies()
    async with httpx.AsyncClient(
        headers={
            "User-Agent": USER_AGENT,
            "Accept": "application/json, text/plain, */*",
        },
        cookies=cookies,
        follow_redirects=True,
    ) as client:
        raw_orders = await fetch_sold_orders(
            client, status=status, per_page=per_page, max_pages=max_pages
        )
        sales: list[Sale] = []
        for i, raw in enumerate(raw_orders, 1):
            print(f"-> [{i}/{len(raw_orders)}] tx={raw['transaction_id']}")
            sales.append(await build_sale(client, raw))
    return sales
