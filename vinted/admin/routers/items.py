"""Purchased items: the gallery page and per-item sale status updates."""

from __future__ import annotations

from fastapi import APIRouter
from fastapi.responses import HTMLResponse
from pydantic import BaseModel

from ..constants import SaleStatus
from ..store import get_store
from ..templating import render

router = APIRouter()


class StatusUpdate(BaseModel):
    """Body of POST /items/{tx_id}/{item_id}/status."""

    status: SaleStatus


class StatusUpdated(BaseModel):
    """Echo of the persisted sale status."""

    tx_id: str
    item_id: str
    status: SaleStatus


def allocate_pln(purchase: dict, items: list[dict]) -> dict[int, float]:
    """Distribute the order's PLN total across items proportionally to their paid_price.

    The order's `total_price` (in `currency`) already includes shipping + service fee.
    Each item gets `total_price * item.paid_price / sum(items.paid_price)`, so fees are
    split in proportion to item value. Returns {item_id: price_pln}; items without a
    paid_price (or when the order isn't priced in PLN) are omitted.
    """
    if purchase.get("currency") != "PLN":
        return {}
    total = purchase.get("total_price")
    if not isinstance(total, (int, float)) or not total:
        return {}
    items_sum: float = sum((i.get("paid_price") or 0.0) for i in items)
    if not items_sum:
        return {}
    return {
        int(i["id"]): float(total) * (i["paid_price"] / items_sum)
        for i in items
        if i.get("paid_price") is not None
    }


def load_purchases() -> list[dict]:
    """Purchases (transactions) newest first, each with its enriched items.

    Uses two queries: one stream over `purchases` for the order context, one
    collection_group("items") for all items across all purchases. Items are
    joined to their parent purchase by document id and nested under it.
    """
    store = get_store()
    purchases: dict[str, dict] = {
        snap.id: (snap.to_dict() or {}) for snap in store.purchases.stream()
    }
    items_by_purchase: dict[str, list[dict]] = {}
    for item_snap in store.client.collection_group("items").stream():
        parent_id = item_snap.reference.parent.parent.id
        items_by_purchase.setdefault(parent_id, []).append(item_snap.to_dict() or {})

    out: list[dict] = []
    for tx_id, purchase in purchases.items():
        items = items_by_purchase.get(tx_id, [])
        pln_by_id = allocate_pln(purchase, items)
        enriched = [
            {
                **item,
                "price_pln": (
                    pln_by_id.get(item.get("id")) if isinstance(item.get("id"), int) else None
                ),
                "_sale_status": item.get("_sale_status") or SaleStatus.none,
            }
            for item in items
        ]
        out.append(
            {
                "tx_id": tx_id,
                "seller_id": purchase.get("seller_id"),
                "seller_login": purchase.get("seller_login", ""),
                "seller_country": purchase.get("seller_country", ""),
                "order_date": purchase.get("date", ""),
                "conversation_id": purchase.get("conversation_id"),
                "total_price": purchase.get("total_price"),
                "currency": purchase.get("currency", ""),
                "items": enriched,
            }
        )
    out.sort(key=lambda p: p.get("order_date") or "", reverse=True)
    return out


@router.get("/", response_class=HTMLResponse)
def index() -> str:
    purchases = load_purchases()
    return render(
        "items.html",
        purchases=purchases,
        total_items=sum(len(p["items"]) for p in purchases),
    )


@router.post("/items/{tx_id}/{item_id}/status")
def set_status(tx_id: str, item_id: str, update: StatusUpdate) -> StatusUpdated:
    get_store().set_item_status(tx_id, item_id, update.status.value)
    return StatusUpdated(tx_id=tx_id, item_id=item_id, status=update.status)
