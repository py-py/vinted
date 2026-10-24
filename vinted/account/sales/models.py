from __future__ import annotations

from pydantic import BaseModel


class SaleItem(BaseModel):
    id: int
    title: str
    size: str = ""
    condition: str = ""
    url: str = ""
    catalog_id: int | None = None
    photo_url: str = ""
    photo_urls: list[str] = []
    listed_price: float | None = None
    sold_price: float | None = None  # bundles: items_price split by listed_price share
    currency: str = ""
    is_deleted: bool = False


class Sale(BaseModel):
    transaction_id: int
    escrow_order_id: int
    conversation_id: int | str
    title: str
    date: str
    is_bundle: bool
    buyer_id: int | None = None
    buyer_login: str = ""
    buyer_country: str = ""
    items: list[SaleItem]
    items_price: float
    shipment_price: float
    currency: str
    status: str
    transaction_user_status: str = ""
    photo_url: str = ""
