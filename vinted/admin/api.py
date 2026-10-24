"""
JSON API for the web admin (`web/`): purchases, items with sale status and sell price,
sales, stats.

Everything is derived from `load_purchases` / `load_sales` (one full Firestore read per request);
filtering and pagination happen in memory, which is fine at the current data size.
"""

from __future__ import annotations

from collections import Counter
from datetime import date
from typing import Annotated

from fastapi import APIRouter
from fastapi import HTTPException
from fastapi import Path
from fastapi import Query
from fastapi import Response
from pydantic import BaseModel
from pydantic import Field

from ..account.orders.models import SaleStatus
from ..storage.gcs import extract_token
from .deps import PhotoStoreDep
from .deps import StoreDep
from .purchases import load_purchases
from .sales import load_sales

router = APIRouter(prefix="/api", tags=["api"])


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
    sell_price: float | None = Field(default=None, description="Resale price, PLN")
    status: SaleStatus = SaleStatus.NONE
    order_date: str = ""
    seller_login: str = ""
    seller_country: str = ""


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


class SaleItem(BaseModel):
    id: int
    tx_id: str
    title: str = ""
    size: str = ""
    condition: str = ""
    url: str = ""
    photo_urls: list[str] = []
    stored_photo_urls: list[str] = Field(default=[], description="See `Item.stored_photo_urls`")
    listed_price: float | None = None
    sold_price: float | None = Field(
        default=None, description="Bundles: items_price split by listed_price share"
    )
    currency: str = ""


class Sale(BaseModel):
    tx_id: str
    buyer_id: int | None = None
    buyer_login: str = ""
    buyer_country: str = ""
    order_date: str = ""
    conversation_id: int | str | None = None
    items_price: float | None = Field(default=None, description="Paid by buyer, w/o shipment")
    shipment_price: float | None = None
    currency: str = ""
    items: list[SaleItem]


class StatusUpdate(BaseModel):
    status: SaleStatus


class StatusUpdateResult(BaseModel):
    tx_id: str
    item_id: str
    status: SaleStatus


class SellPriceUpdate(BaseModel):
    sell_price: float | None = Field(ge=0, description="PLN; null clears it")


class SellPriceUpdateResult(BaseModel):
    tx_id: str
    item_id: str
    sell_price: float | None


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
    sold_pln: float
    sold_items: int = Field(description="Items with a sell price set")
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
    photo_urls = _photo_urls(item)
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
        sell_price=item.get("_sell_price"),
        status=SaleStatus(raw_status) if raw_status in SaleStatus else SaleStatus.NONE,
        order_date=purchase.get("order_date") or "",
        seller_login=purchase.get("seller_login") or "",
        seller_country=purchase.get("seller_country") or "",
    )


def _to_purchase(purchase: dict) -> Purchase:
    return Purchase(
        **{k: v for k, v in purchase.items() if k != "items"},
        items=[_to_item(purchase, i) for i in purchase["items"] if i.get("id") is not None],
    )


def _photo_urls(item: dict) -> list[str]:
    return item.get("photo_urls") or ([item["photo_url"]] if item.get("photo_url") else [])


def _to_sale_item(sale: dict, item: dict) -> SaleItem:
    photo_urls = _photo_urls(item)
    return SaleItem(
        id=item["id"],
        tx_id=sale["tx_id"],
        title=item.get("title") or "",
        size=item.get("size") or "",
        condition=item.get("condition") or "",
        url=item.get("url") or "",
        photo_urls=photo_urls,
        stored_photo_urls=[_stored_photo_url(item["id"], u) for u in photo_urls],
        listed_price=item.get("listed_price"),
        sold_price=item.get("sold_price"),
        currency=item.get("currency") or "",
    )


def _to_sale(sale: dict) -> Sale:
    return Sale(
        **{k: v for k, v in sale.items() if k != "items"},
        items=[_to_sale_item(sale, i) for i in sale["items"] if i.get("id") is not None],
    )


def _matches(query: str, *fields: str) -> bool:
    query = query.casefold()
    return any(query in f.casefold() for f in fields)


###############################################################################
#  Routes — Purchases, Sales, Items, Stats and Photos
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


@router.get("/sales")
def list_sales(
    store: StoreDep,
    q: Annotated[str | None, Query(description="Search in buyer login and item titles")] = None,
    date_from: Annotated[date | None, Query(description="Sale date, inclusive")] = None,
    date_to: Annotated[date | None, Query(description="Sale date, inclusive")] = None,
) -> list[Sale]:
    sales = [_to_sale(s) for s in load_sales(store)]
    if q:
        sales = [s for s in sales if _matches(q, s.buyer_login, *(i.title for i in s.items))]
    if date_from:
        sales = [s for s in sales if s.order_date[:10] >= date_from.isoformat()]
    if date_to:
        sales = [s for s in sales if s.order_date[:10] <= date_to.isoformat()]
    return sales


@router.get("/items")
def list_items(
    store: StoreDep,
    status: Annotated[list[SaleStatus] | None, Query(description="Keep only these")] = None,
    q: Annotated[str | None, Query(description="Search in title and seller login")] = None,
    has_sell_price: Annotated[
        bool | None, Query(description="Keep only items with (true) or without (false) one")
    ] = None,
    page: Annotated[int, Query(ge=1)] = 1,
    size: Annotated[int, Query(ge=1, le=200)] = 50,
) -> Page[Item]:
    items = [i for p in map(_to_purchase, load_purchases(store)) for i in p.items]
    if status:
        items = [i for i in items if i.status in status]
    if q:
        items = [i for i in items if _matches(q, i.title, i.seller_login)]
    if has_sell_price is not None:
        items = [i for i in items if (i.sell_price is not None) == has_sell_price]
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


@router.patch("/items/{tx_id}/{item_id}/sell-price")
def update_item_sell_price(
    tx_id: Annotated[str, Path(description="Purchase (transaction) id")],
    item_id: Annotated[str, Path(description="Item id within the purchase")],
    update: SellPriceUpdate,
    store: StoreDep,
) -> SellPriceUpdateResult:
    store.set_item_sell_price(tx_id, item_id, update.sell_price)
    return SellPriceUpdateResult(tx_id=tx_id, item_id=item_id, sell_price=update.sell_price)


@router.get("/stats")
def get_stats(store: StoreDep) -> Stats:
    purchases = [_to_purchase(p) for p in load_purchases(store)]
    items = [i for p in purchases for i in p.items]
    sold = [i for i in items if i.sell_price is not None]

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
        sold_pln=sum(i.sell_price or 0.0 for i in sold),
        sold_items=len(sold),
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
