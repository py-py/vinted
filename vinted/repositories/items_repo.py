from __future__ import annotations

from datetime import UTC
from datetime import datetime
from typing import Any

from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.ext.asyncio import async_sessionmaker

from ..db.models import Item
from ..db.session import get_sessionmaker
from ..domain.analysis import BaseAnalysis
from ..domain.enums import ItemStatus
from ..domain.product import VintedProduct


def _now() -> datetime:
    return datetime.now(UTC)


class ItemsRepository:
    """SQL-backed store for scraped items and their analyses (one row per item).

    Each method runs in its own short-lived transaction, so the same repository
    instance is safe to reuse across the request, the CLI and background tasks
    without holding a connection open during long LLM calls.
    """

    def __init__(self, session_factory: async_sessionmaker[AsyncSession] | None = None) -> None:
        self._sessionmaker = session_factory or get_sessionmaker()

    async def get(self, item_id: str) -> dict[str, Any] | None:
        """Return the stored item, or ``None`` if it is missing."""
        async with self._sessionmaker() as session:
            item = await session.get(Item, item_id)
            return item.model_dump(mode="json") if item is not None else None

    async def save_product(self, product: VintedProduct) -> None:
        async with self._sessionmaker() as session:
            item = await session.get(Item, product.id)
            if item is None:
                item = Item(id=product.id, created_at=_now())
                session.add(item)
            item.title = product.title
            item.description = product.description
            item.catalog_id = product.catalog_id
            item.url = product.url
            item.price = product.price
            item.properties = product.properties
            item.image_urls = product.image_urls
            item.seller = product.seller.model_dump()
            item.status = ItemStatus.new.value
            await session.commit()

    async def save_analysis(
        self,
        item_id: str,
        analysis: BaseAnalysis,
        *,
        status: ItemStatus,
    ) -> None:
        async with self._sessionmaker() as session:
            item = await session.get(Item, item_id)
            if item is None:
                item = Item(id=item_id, created_at=_now())
                session.add(item)
            item.analysis = analysis.model_dump(mode="json")
            item.status = status.value
            item.analyzed_at = _now()
            await session.commit()

    async def set_status(self, item_id: str, status: ItemStatus) -> None:
        async with self._sessionmaker() as session:
            item = await session.get(Item, item_id)
            if item is None:
                item = Item(id=item_id, created_at=_now())
                session.add(item)
            item.status = status.value
            await session.commit()
