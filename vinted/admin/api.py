"""
JSON API for the web admin (`web/`): purchases, items with sale status, stats, sales.

Everything is derived from `load_purchases` (one full Firestore read per request);
filtering and pagination happen in memory, which is fine at the current data size.
"""

from __future__ import annotations

import uuid
from collections import Counter
from datetime import date
from typing import Annotated

from fastapi import APIRouter
from fastapi import Form
from fastapi import HTTPException
from fastapi import Path
from fastapi import Query
from fastapi import Response
from fastapi import UploadFile
from pydantic import BaseModel
from pydantic import Field

from ..account.orders.models import SaleStatus
from ..storage.gcs import extract_token
from .deps import PhotoStoreDep
from .deps import StoreDep
from .purchases import load_purchases

router = APIRouter(prefix="/api", tags=["api"])

# The web app resizes photos to 1600px on the longest side before upload (~0.3 MB each).
MAX_SALE_PHOTOS = 20
MAX_SALE_PHOTO_BYTES = 5 * 1024 * 1024


###############################################################################
#  Schemas — API Request and Response Models
###############################################################################


class Item(BaseModel):
    id: int
    tx_id: str
    title: str = ""
    size: str = ""
    condition: str = ""
    url: str = ""
    photo_urls: list[str] = []
    stored_photo_urls: list[str] = Field(
        default=[],
        description=(
            "GCS copies served by /api/photos, used when Vinted "
            "has deleted the listing. Same order as photo_urls; "
            "empty string if the URL has no token."
        ),
    )
    paid_price: float | None = None
    paid_estimated: bool = False
    currency: str = ""
    price_pln: float | None = None
    status: SaleStatus = SaleStatus.NONE
    order_date: str = ""
    seller_login: str = ""


class Purchase(BaseModel):
    tx_id: str
    seller_id: int | None = None
    seller_login: str = ""
    seller_country: str = ""
    order_date: str = ""
    conversation_id: int | str | None = None
    total_price: float | None = None
    currency: str = ""
    items: list[Item]


class StatusUpdate(BaseModel):
    status: SaleStatus


class StatusUpdateResult(BaseModel):
    tx_id: str
    item_id: str
    status: SaleStatus


class Sale(BaseModel):
    id: str
    title: str
    description: str = ""
    price_pln: float | None = None
    photo_urls: list[str] = []
    created_at: str = ""


class Page[T](BaseModel):
    items: list[T]
    total: int
    page: int
    size: int


class MonthStats(BaseModel):
    month: str  # YYYY-MM
    purchases: int
    items: int
    spent_pln: float


class Stats(BaseModel):
    purchases: int
    items: int
    spent_pln: float
    by_status: dict[SaleStatus, int]
    by_month: list[MonthStats]


###############################################################################
#  Helpers — Firestore Docs to API Models
###############################################################################


def _stored_photo_url(item_id: int, url: str) -> str:
    try:
        token = extract_token(url)
        return router.url_path_for("get_photo", item_id=item_id, token=token)
    except ValueError:
        return ""


def _to_item(purchase: dict, item: dict) -> Item:
    raw_status = item.get("_sale_status")
    photo_urls = item.get("photo_urls") or ([item["photo_url"]] if item.get("photo_url") else [])
    return Item(
        id=item["id"],
        tx_id=purchase["tx_id"],
        title=item.get("title") or "",
        size=item.get("size") or "",
        condition=item.get("condition") or "",
        url=item.get("url") or "",
        photo_urls=photo_urls,
        stored_photo_urls=[_stored_photo_url(item["id"], u) for u in photo_urls],
        paid_price=item.get("paid_price"),
        paid_estimated=item.get("paid_estimated", False),
        currency=item.get("currency") or "",
        price_pln=item.get("price_pln"),
        status=SaleStatus(raw_status) if raw_status in SaleStatus else SaleStatus.NONE,
        order_date=purchase.get("order_date") or "",
        seller_login=purchase.get("seller_login") or "",
    )


def _to_purchase(purchase: dict) -> Purchase:
    return Purchase(
        **{k: v for k, v in purchase.items() if k != "items"},
        items=[_to_item(purchase, i) for i in purchase["items"] if i.get("id") is not None],
    )


def _to_sale(sale_id: str, sale: dict) -> Sale:
    created_at = sale.get("created_at")
    return Sale(
        id=sale_id,
        title=sale.get("title") or "",
        description=sale.get("description") or "",
        price_pln=sale.get("price_pln"),
        photo_urls=[
            router.url_path_for("get_sale_photo", sale_id=sale_id, photo_id=photo_id)
            for photo_id in sale.get("photos") or []
        ],
        created_at=created_at.isoformat() if created_at else "",
    )


def _matches(query: str, *fields: str) -> bool:
    query = query.casefold()
    return any(query in f.casefold() for f in fields)


###############################################################################
#  Routes — Purchases, Items, Stats and Photos
###############################################################################


@router.get("/purchases")
def list_purchases(
    store: StoreDep,
    q: Annotated[str | None, Query(description="Search in seller login and item titles")] = None,
    date_from: Annotated[date | None, Query(description="Order date, inclusive")] = None,
    date_to: Annotated[date | None, Query(description="Order date, inclusive")] = None,
) -> list[Purchase]:
    purchases = [_to_purchase(p) for p in load_purchases(store)]
    if q:
        purchases = [
            p for p in purchases if _matches(q, p.seller_login, *(i.title for i in p.items))
        ]
    if date_from:
        purchases = [p for p in purchases if p.order_date[:10] >= date_from.isoformat()]
    if date_to:
        purchases = [p for p in purchases if p.order_date[:10] <= date_to.isoformat()]
    return purchases


@router.get("/items")
def list_items(
    store: StoreDep,
    status: Annotated[list[SaleStatus] | None, Query(description="Keep only these")] = None,
    q: Annotated[str | None, Query(description="Search in title and seller login")] = None,
    page: Annotated[int, Query(ge=1)] = 1,
    size: Annotated[int, Query(ge=1, le=200)] = 50,
) -> Page[Item]:
    items = [i for p in map(_to_purchase, load_purchases(store)) for i in p.items]
    if status:
        items = [i for i in items if i.status in status]
    if q:
        items = [i for i in items if _matches(q, i.title, i.seller_login)]
    start = (page - 1) * size
    return Page(items=items[start : start + size], total=len(items), page=page, size=size)


@router.patch("/items/{tx_id}/{item_id}")
def update_item_status(
    tx_id: Annotated[str, Path(description="Purchase (transaction) id")],
    item_id: Annotated[str, Path(description="Item id within the purchase")],
    update: StatusUpdate,
    store: StoreDep,
) -> StatusUpdateResult:
    store.set_item_status(tx_id, item_id, update.status)
    return StatusUpdateResult(tx_id=tx_id, item_id=item_id, status=update.status)


@router.get("/stats")
def get_stats(store: StoreDep) -> Stats:
    purchases = [_to_purchase(p) for p in load_purchases(store)]
    items = [i for p in purchases for i in p.items]

    by_month: dict[str, MonthStats] = {}
    for p in purchases:
        month = p.order_date[:7]
        if not month:
            continue
        stats = by_month.setdefault(
            month, MonthStats(month=month, purchases=0, items=0, spent_pln=0)
        )
        stats.purchases += 1
        stats.items += len(p.items)
        stats.spent_pln += sum(i.price_pln or 0.0 for i in p.items)

    return Stats(
        purchases=len(purchases),
        items=len(items),
        spent_pln=sum(i.price_pln or 0.0 for i in items),
        by_status=Counter(i.status for i in items),
        by_month=[by_month[m] for m in sorted(by_month)],
    )


@router.get(
    "/photos/{item_id}/{token}",
    response_class=Response,
    responses={200: {"content": {"image/jpeg": {}}}, 404: {"description": "Not in GCS"}},
)
def get_photo(
    item_id: int,
    token: Annotated[str, Path(pattern=r"^[\w-]+$")],
    photos: PhotoStoreDep,
) -> Response:
    data = photos.download_photo(item_id, token)
    if data is None:
        raise HTTPException(status_code=404, detail="Photo not found")
    # Token is content-addressed, so the bytes never change.
    return Response(
        data,
        media_type="image/jpeg",
        headers={"Cache-Control": "private, max-age=31536000, immutable"},
    )


###############################################################################
#  Routes — Sales Created in the Admin
###############################################################################


@router.get("/sales")
def list_sales(store: StoreDep) -> list[Sale]:
    return [_to_sale(sale_id, sale) for sale_id, sale in store.list_sales()]


@router.post("/sales", status_code=201)
def create_sale(
    title: Annotated[str, Form(min_length=1, max_length=100)],
    photos: Annotated[list[UploadFile], Form(description="JPEGs, already resized")],
    store: StoreDep,
    photo_store: PhotoStoreDep,
    description: Annotated[str, Form(max_length=5000)] = "",
    price_pln: Annotated[float | None, Form(gt=0)] = None,
) -> Sale:
    if not 1 <= len(photos) <= MAX_SALE_PHOTOS:
        raise HTTPException(422, f"Expected 1–{MAX_SALE_PHOTOS} photos, got {len(photos)}")
    data = [photo.file.read(MAX_SALE_PHOTO_BYTES + 1) for photo in photos]
    for photo, blob in zip(photos, data):
        if len(blob) > MAX_SALE_PHOTO_BYTES or not blob.startswith(b"\xff\xd8"):
            raise HTTPException(422, f"{photo.filename}: expected a JPEG up to 5 MB")

    sale_id = store.new_sale_id()
    photo_ids = [uuid.uuid4().hex for _ in data]
    for photo_id, blob in zip(photo_ids, data):
        photo_store.upload_sale_photo(sale_id, photo_id, blob)
    sale = {
        "title": title.strip(),
        "description": description.strip(),
        "price_pln": price_pln,
        "photos": photo_ids,
    }
    store.save_sale(sale_id, sale)
    return _to_sale(sale_id, sale)


@router.get(
    "/sales/{sale_id}/photos/{photo_id}",
    response_class=Response,
    responses={200: {"content": {"image/jpeg": {}}}, 404: {"description": "Not in GCS"}},
)
def get_sale_photo(
    sale_id: Annotated[str, Path(pattern=r"^\w+$")],
    photo_id: Annotated[str, Path(pattern=r"^[0-9a-f]{32}$")],
    photos: PhotoStoreDep,
) -> Response:
    data = photos.download_sale_photo(sale_id, photo_id)
    if data is None:
        raise HTTPException(status_code=404, detail="Photo not found")
    return Response(
        data,
        media_type="image/jpeg",
        headers={"Cache-Control": "private, max-age=31536000, immutable"},
    )
