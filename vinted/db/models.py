from __future__ import annotations

from datetime import UTC
from datetime import datetime
from typing import Any

from sqlalchemy import BigInteger
from sqlalchemy import DateTime
from sqlalchemy import Integer
from sqlalchemy.dialects.postgresql import JSONB
from sqlmodel import Field
from sqlmodel import SQLModel

from ..domain.enums import Catalog
from ..domain.enums import ItemStatus


def _now() -> datetime:
    return datetime.now(UTC)


class VintedSQLModel(SQLModel):
    """Base for our tables: a surrogate PK plus created/updated timestamps.

    Not a table itself (no ``table=True``); any subclass that sets ``table=True``
    inherits these as columns. Timestamps are app-side: ``created_at`` is set once
    on insert, ``updated_at`` is refreshed on every ORM/Core UPDATE via ``onupdate``
    (Python-side, not a DB trigger).
    """

    id: int | None = Field(default=None, primary_key=True)
    created_at: datetime = Field(
        default_factory=_now,
        sa_type=DateTime(timezone=True),
    )
    updated_at: datetime = Field(
        default_factory=_now,
        sa_type=DateTime(timezone=True),
        sa_column_kwargs={"onupdate": _now},
    )


class Item(VintedSQLModel, table=True):
    """One row per scraped Vinted item, plus its analysis and lifecycle status.

    Variable / nested data (``properties``, ``image_urls``, ``seller``, ``analysis``)
    is stored in JSONB columns so the schema stays stable across catalog-specific
    analysis subtypes.
    """

    __tablename__ = "items"

    # Where this item originated; for our own bookkeeping, not user-editable.
    source: str = "Vinted"
    vinted_id: int | None = Field(default=None, sa_type=BigInteger, index=True, unique=True)
    catalog_id: Catalog | None = Field(default=None, sa_type=Integer, index=True)

    title: str = ""
    description: str = ""
    url: str = ""
    price: float | None = Field(default=None)
    properties: dict[str, Any] = Field(default_factory=dict, sa_type=JSONB)
    image_urls: list[str] = Field(default_factory=list, sa_type=JSONB)
    seller: dict[str, Any] = Field(default_factory=dict, sa_type=JSONB)
    status: str = Field(default=ItemStatus.new.value, index=True)
    # none_as_null: store a missing analysis as SQL NULL, not a JSON ``null`` scalar.
    analysis: dict[str, Any] | None = Field(default=None, sa_type=JSONB(none_as_null=True))
    analyzed_at: datetime | None = Field(default=None, sa_type=DateTime(timezone=True))
