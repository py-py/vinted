from __future__ import annotations

from typing import Optional

from pydantic import BaseModel


class VintedSeller(BaseModel):
    username: str = ""
    link: str = ""
    location: str = ""
    stars: Optional[float] = None
    reviews: Optional[int] = None


class VintedProduct(BaseModel):
    id: str
    catalog_id: str
    url: str
    title: str = ""
    image_urls: list[str] = []
    description: str = ""
    properties: dict[str, str] = {}
    seller: VintedSeller = VintedSeller()
    ld_json: dict = {}
