"""
FastAPI viewer for purchased Vinted items.

Data is pulled from Firestore (purchases/{tx}/items/{id}). Photos are loaded
directly from the Vinted CDN URLs stored in Firestore — no GCS access here.

Run:
    uvicorn vinted.admin.web:app --reload
"""

from __future__ import annotations

import os
import secrets
from functools import lru_cache
from pathlib import Path

from dotenv import load_dotenv
from fastapi import Depends
from fastapi import FastAPI
from fastapi import HTTPException
from fastapi import status
from fastapi.responses import HTMLResponse
from fastapi.security import HTTPBasic
from fastapi.security import HTTPBasicCredentials
from jinja2 import Environment
from jinja2 import FileSystemLoader
from jinja2 import select_autoescape
from pydantic import BaseModel

from ..firestore import FirestoreStore

load_dotenv()

_ADMIN_USERNAME = os.environ.get("ADMIN_USERNAME", "")
_ADMIN_PASSWORD = os.environ.get("ADMIN_PASSWORD", "")
_security = HTTPBasic()


def require_auth(credentials: HTTPBasicCredentials = Depends(_security)) -> str:
    """Gate every route behind HTTP Basic auth (ADMIN_USERNAME / ADMIN_PASSWORD).

    Fails closed: if credentials aren't configured the site is unreachable rather
    than wide open. Uses constant-time comparison to avoid leaking length/contents
    via timing.
    """
    if not _ADMIN_USERNAME or not _ADMIN_PASSWORD:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="Admin auth not configured: set ADMIN_USERNAME and ADMIN_PASSWORD",
        )
    user_ok = secrets.compare_digest(
        credentials.username.encode("utf-8"), _ADMIN_USERNAME.encode("utf-8")
    )
    pass_ok = secrets.compare_digest(
        credentials.password.encode("utf-8"), _ADMIN_PASSWORD.encode("utf-8")
    )
    if not (user_ok and pass_ok):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid credentials",
            headers={"WWW-Authenticate": "Basic"},
        )
    return credentials.username


app = FastAPI(title="Vinted purchases", dependencies=[Depends(require_auth)])

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


@app.get("/", response_class=HTMLResponse)
def index() -> str:
    purchases = _load_purchases()
    context = {
        "purchases": purchases,
        "total_items": sum(len(p["items"]) for p in purchases),
    }
    return _env.get_template("items.html").render(**context)


_SALE_STATUSES = {
    "none",
    "listed",
    "sold_unconfirmed",
    "sold",
    "reserved",
    "parted_sold",
    "wait_winter",
}


class StatusUpdate(BaseModel):
    status: str


@app.post("/items/{tx_id}/{item_id}/status")
def set_status(tx_id: str, item_id: str, update: StatusUpdate) -> dict:
    if update.status not in _SALE_STATUSES:
        raise HTTPException(status_code=422, detail=f"invalid status: {update.status!r}")
    _store().set_item_status(tx_id, item_id, update.status)
    return {"tx_id": tx_id, "item_id": item_id, "status": update.status}
