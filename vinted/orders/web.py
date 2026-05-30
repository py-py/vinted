"""
FastAPI backend for the Vinted purchases viewer.

Exposes a JSON API under /api and serves the built React SPA
(vinted/web-app/dist) at /. Data comes from Firestore
(purchases/{tx}/items/{id}); photos are Vinted CDN URLs stored there.

Dev:
    uvicorn vinted.orders.web:app --reload     # API on :8000
    (cd vinted/web-app && npm run dev)          # Vite on :5173, proxies /api -> :8000

Prod / local:
    (cd vinted/web-app && npm run build)        # -> vinted/web-app/dist
    uvicorn vinted.orders.web:app               # serves API + built SPA
"""

from __future__ import annotations

from functools import lru_cache
from pathlib import Path

from fastapi import FastAPI
from fastapi import HTTPException
from fastapi.responses import HTMLResponse
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel

from ..firestore import FirestoreStore

app = FastAPI(title="Vinted purchases")

# vinted/orders/web.py -> vinted/web-app/dist
_DIST_DIR = Path(__file__).resolve().parent.parent / "web-app" / "dist"

_SALE_STATUSES = {"none", "listed", "bought", "sold", "reserved", "parted_sold", "wait_winter"}


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


def _load_purchases() -> list[dict]:
    """Purchases (transactions) newest first, each with its enriched items.

    Uses two queries: one stream over `purchases` for the order context, one
    collection_group("items") for all items across all purchases. Items are
    joined to their parent purchase by document id and nested under it.
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
        enriched = [
            {
                **item,
                "price_pln": (
                    pln_by_id.get(item.get("id")) if isinstance(item.get("id"), int) else None
                ),
                "_sale_status": item.get("_sale_status") or "none",
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


@app.get("/api/purchases")
def api_purchases() -> list[dict]:
    """All purchases, newest first, each with its nested items."""
    return _load_purchases()


class ItemPatch(BaseModel):
    """Partial update for an item. Only the sale status for now; editable fields
    (title, price, …) will be added here as the modal editor grows.

    The API uses the plain name `sale_status`; it is persisted to Firestore under
    the custom field `_sale_status` (see FirestoreStore.set_item_status)."""

    sale_status: str | None = None


@app.patch("/api/items/{tx_id}/{item_id}")
def patch_item(tx_id: str, item_id: str, patch: ItemPatch) -> dict:
    if patch.sale_status is not None:
        if patch.sale_status not in _SALE_STATUSES:
            raise HTTPException(status_code=422, detail=f"invalid status: {patch.sale_status!r}")
        _store().set_item_status(tx_id, item_id, patch.sale_status)
    return {"tx_id": tx_id, "item_id": item_id, "sale_status": patch.sale_status}


# Serve the built SPA at / (registered last so /api/* takes precedence). When the
# frontend hasn't been built yet, show a hint instead of crashing at startup.
if _DIST_DIR.is_dir():
    app.mount("/", StaticFiles(directory=_DIST_DIR, html=True), name="spa")
else:

    @app.get("/", response_class=HTMLResponse)
    def _frontend_not_built() -> str:
        return (
            "<!doctype html><meta charset=utf-8>"
            "<h1>Frontend not built</h1>"
            "<p>Dev: <code>cd vinted/web-app &amp;&amp; npm run dev</code> (Vite on :5173).</p>"
            "<p>Or build it: <code>cd vinted/web-app &amp;&amp; npm run build</code>, then restart this server.</p>"  # NOQA: E501
            "<p>API is live at <a href='/api/purchases'>/api/purchases</a>.</p>"
        )
