from __future__ import annotations

from datetime import UTC
from datetime import datetime
from typing import Any
from typing import Optional

from sqlalchemy import DateTime
from sqlalchemy.dialects.postgresql import JSONB
from sqlmodel import Field
from sqlmodel import SQLModel

from ..domain.enums import ItemStatus


def _now() -> datetime:
    return datetime.now(UTC)


class Item(SQLModel, table=True):
    """One row per scraped Vinted item, plus its analysis and lifecycle status.

    Variable / nested data (``properties``, ``image_urls``, ``seller``, ``analysis``)
    is stored in JSONB columns so the schema stays stable across catalog-specific
    analysis subtypes.
    """

    __tablename__ = "items"

    id: str = Field(primary_key=True)  # Vinted item id
    title: str = ""
    description: str = ""
    catalog_id: str = ""
    url: str = ""
    price: float = 0.0
    properties: dict[str, Any] = Field(default_factory=dict, sa_type=JSONB)
    image_urls: list[str] = Field(default_factory=list, sa_type=JSONB)
    seller: dict[str, Any] = Field(default_factory=dict, sa_type=JSONB)
    source: str = "catalog"
    status: str = Field(default=ItemStatus.new.value, index=True)
    # none_as_null: store a missing analysis as SQL NULL, not a JSON ``null`` scalar.
    analysis: Optional[dict[str, Any]] = Field(default=None, sa_type=JSONB(none_as_null=True))
    created_at: datetime = Field(default_factory=_now, sa_type=DateTime(timezone=True))
    analyzed_at: Optional[datetime] = Field(default=None, sa_type=DateTime(timezone=True))
