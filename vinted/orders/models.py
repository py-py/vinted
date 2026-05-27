from __future__ import annotations

from pydantic import BaseModel


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


class Order(BaseModel):
    transaction_id: int
    conversation_id: int
    purchase_id: str = ""
    title: str
    date: str
    is_bundle: bool
    seller_id: int
    seller_login: str = ""
    seller_country: str = ""
    items: list[OrderItem]
    items_price: float
    service_fee: float
    shipment_price: float
    total_price: float
    currency: str
    status: str
    conversion: CurrencyConversion | None = None
