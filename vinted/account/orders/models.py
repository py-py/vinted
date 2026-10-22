from __future__ import annotations

from enum import StrEnum

from pydantic import BaseModel


class SaleStatus(StrEnum):
    NONE = "none"
    LISTED = "listed"
    SOLD_UNCONFIRMED = "sold_unconfirmed"
    SOLD = "sold"
    RESERVED = "reserved"
    PARTED_SOLD = "parted_sold"
    WAIT_WINTER = "wait_winter"
    TRASH = "trash"


class CurrencyConversion(BaseModel):
    seller_currency: str
    buyer_currency: str
    rate: float
    fee_fraction: float
    provider: str = ""
    items_price_seller: float
    shipment_price_seller: float


class OrderItem(BaseModel):
    id: int
    title: str
    size: str = ""
    condition: str = ""
    url: str = ""
    catalog_id: int | None = None
    photo_url: str = ""
    photo_urls: list[str] = []
    paid_price: float | None = None
    listed_price: float | None = None
    currency: str = ""
    is_deleted: bool = False


class Order(BaseModel):
    transaction_id: int
    conversation_id: int | str  # legacy numeric ids; newer conversations use UUID strings
    purchase_id: str = ""
    title: str
    date: str
    is_bundle: bool
    seller_id: int
    seller_login: str = ""
    seller_country: str = ""
    items: list[OrderItem]
    photo_url: str = ""
    items_price: float
    service_fee: float
    shipment_price: float
    total_price: float
    currency: str
    status: str
    conversion: CurrencyConversion | None = None
