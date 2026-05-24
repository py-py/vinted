from __future__ import annotations

from datetime import datetime

from pydantic import BaseModel

from ..db.models import VintedSeller

__all__ = ["VintedProduct", "VintedSeller"]


class VintedProduct(BaseModel):
    id: str
    title: str = ""
    description: str = ""
    catalog_id: str
    url: str
    price: float
    properties: dict[str, str] = {}
    image_urls: list[str] = []
    seller: VintedSeller | None = None
    uploaded_at: datetime | None = None
    ld_json: dict = {}

    def model_dump_json(self, *args, **kwargs) -> str:
        kwargs.setdefault("exclude", {"ld_json"})
        return super().model_dump_json(*args, **kwargs)

    @property
    def main_image_url(self):
        return self.image_urls[0] if self.image_urls else ""
