from __future__ import annotations

from typing import Optional

from pydantic import BaseModel


class VintedSeller(BaseModel):
    username: str = ""
    location: str = ""
    link: str = ""
    stars: Optional[float] = None
    reviews: Optional[int] = None


class VintedProduct(BaseModel):
    id: str
    title: str = ""
    description: str = ""
    catalog_id: str
    url: str
    price: float
    properties: dict[str, str] = {}
    image_urls: list[str] = []
    seller: VintedSeller = VintedSeller()
    ld_json: dict = {}

    def model_dump_json(self, *args, **kwargs) -> str:
        kwargs.setdefault("exclude", {"ld_json"})
        return super().model_dump_json(*args, **kwargs)

    @property
    def main_image_url(self):
        return self.image_urls[0] if self.image_urls else ""
