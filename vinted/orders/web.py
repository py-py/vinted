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
from fastapi.responses import HTMLResponse
from jinja2 import Environment
from jinja2 import FileSystemLoader
from jinja2 import select_autoescape

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


def _price_in_pln(
    paid_price: float | None,
    item_currency: str,
    conversion: dict | None,
) -> float | None:
    """Convert an item's paid_price (in seller currency) to PLN if possible."""
    if paid_price is None:
        return None
    if item_currency == "PLN":
        return paid_price
    if (
        conversion
        and conversion.get("buyer_currency") == "PLN"
        and conversion.get("seller_currency") == item_currency
        and conversion.get("rate")
    ):
        return paid_price * float(conversion["rate"])
    return None


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

    out: list[dict] = []
    for item_snap in store.client.collection_group("items").stream():
        parent_id = item_snap.reference.parent.parent.id
        purchase = purchases.get(parent_id) or {}
        item = item_snap.to_dict() or {}
        out.append(
            {
                **item,
                "price_pln": _price_in_pln(
                    item.get("paid_price"),
                    item.get("currency", ""),
                    purchase.get("conversion"),
                ),
                "seller_login": purchase.get("seller_login", ""),
                "seller_country": purchase.get("seller_country", ""),
                "order_date": purchase.get("date", ""),
                "transaction_id": purchase.get("transaction_id"),
            }
        )
    out.sort(key=lambda x: x.get("order_date") or "", reverse=True)
    return out


@app.get("/", response_class=HTMLResponse)
def index() -> str:
    return _env.get_template("items.html").render(items=_load_items())
