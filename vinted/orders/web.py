"""
FastAPI viewer for purchased Vinted items.

Data is pulled from Firestore (purchases/{tx}/items/{id}). Photos are loaded
directly from the Vinted CDN URLs stored in Firestore — no GCS access here.

Run:
    uvicorn vinted.orders.web:app --reload
"""

from __future__ import annotations

from functools import lru_cache
from pathlib import Path

from fastapi import FastAPI
from fastapi import HTTPException
from fastapi.responses import HTMLResponse
from jinja2 import Environment
from jinja2 import FileSystemLoader
from jinja2 import select_autoescape
from pydantic import BaseModel

from ..firestore import FirestoreStore

app = FastAPI(title="Vinted purchases")

_TEMPLATES_DIR = Path(__file__).resolve().parent / "templates"
_env = Environment(
    loader=FileSystemLoader(_TEMPLATES_DIR),
    autoescape=select_autoescape(["html"]),
)


@lru_cache(maxsize=1)
def _store() -> FirestoreStore:
    return FirestoreStore()


def _allocate_pln(purchase: dict, items: list[dict]) -> dict[int, float]:
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


def _load_items() -> list[dict]:
    """Flat list of items with their parent purchase context, newest first.

    Uses two queries: one stream over `purchases` for the order context, one
    collection_group("items") for all items across all purchases. Items are
    joined to their parent purchase by document id.
    """
    store = _store()
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
        pln_by_id = _allocate_pln(purchase, items)
        for item in items:
            item_id = item.get("id")
            out.append(
                {
                    **item,
                    "price_pln": pln_by_id.get(item_id) if isinstance(item_id, int) else None,
                    "_sale_status": item.get("_sale_status") or "none",
                    "seller_login": purchase.get("seller_login", ""),
                    "seller_country": purchase.get("seller_country", ""),
                    "order_date": purchase.get("date", ""),
                    "tx_id": tx_id,
                    "conversation_id": purchase.get("conversation_id"),
                }
            )
    out.sort(key=lambda x: x.get("order_date") or "", reverse=True)
    return out


@app.get("/", response_class=HTMLResponse)
def index() -> str:
    return _env.get_template("items.html").render(items=_load_items())


_SALE_STATUSES = {"none", "listed", "sold", "reserved", "parted_sold"}


class StatusUpdate(BaseModel):
    status: str


@app.post("/items/{tx_id}/{item_id}/status")
def set_status(tx_id: str, item_id: str, update: StatusUpdate) -> dict:
    if update.status not in _SALE_STATUSES:
        raise HTTPException(status_code=422, detail=f"invalid status: {update.status!r}")
    _store().set_item_status(tx_id, item_id, update.status)
    return {"tx_id": tx_id, "item_id": item_id, "status": update.status}
