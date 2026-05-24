from __future__ import annotations

from datetime import UTC
from datetime import datetime
from typing import Any

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.ext.asyncio import async_sessionmaker

from ..db.models import Item
from ..db.session import get_sessionmaker
from ..domain.analysis import BaseAnalysis
from ..domain.enums import Catalog
from ..domain.enums import ItemStatus
from ..domain.product import VintedProduct


def _now() -> datetime:
    return datetime.now(UTC)


def _to_catalog(value: str) -> Catalog | None:
    """Map a scraped catalog id string to a known ``Catalog``, or ``None``."""
    try:
        return Catalog(int(value))
    except (ValueError, TypeError):
        return None


def _to_vinted_id(value: object) -> int | None:
    """Map the Vinted item id (passed around as a string) to an int, or ``None``."""
    try:
        return int(value)  # type: ignore[arg-type]
    except (ValueError, TypeError):
        return None


class ItemsRepository:
    """SQL-backed store for scraped items and their analyses (one row per item).

    Each method runs in its own short-lived transaction, so the same repository
    instance is safe to reuse across the request, the CLI and background tasks
    without holding a connection open during long LLM calls.
    """

    def __init__(self, session_factory: async_sessionmaker[AsyncSession] | None = None) -> None:
        self._sessionmaker = session_factory or get_sessionmaker()

    @staticmethod
    async def _by_vinted_id(session: AsyncSession, vinted_id: int) -> Item | None:
        """Fetch a single item by its Vinted id within an open session."""
        result = await session.execute(select(Item).where(Item.vinted_id == vinted_id))
        return result.scalar_one_or_none()

    async def get(self, item_id: str) -> dict[str, Any] | None:
        """Return the stored item by its Vinted id, or ``None`` if it is missing."""
        vinted_id = _to_vinted_id(item_id)
        if vinted_id is None:
            return None
        async with self._sessionmaker() as session:
            item = await self._by_vinted_id(session, vinted_id)
            return item.model_dump(mode="json") if item is not None else None

    async def save_product(self, product: VintedProduct) -> None:
        vinted_id = _to_vinted_id(product.id)
        async with self._sessionmaker() as session:
            item = await self._by_vinted_id(session, vinted_id) if vinted_id is not None else None
            if item is None:
                item = Item(vinted_id=vinted_id, created_at=_now())
                session.add(item)
            item.title = product.title
            item.description = product.description
            item.catalog_id = _to_catalog(product.catalog_id)
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
        vinted_id = _to_vinted_id(item_id)
        async with self._sessionmaker() as session:
            item = await self._by_vinted_id(session, vinted_id) if vinted_id is not None else None
            if item is None:
                item = Item(vinted_id=vinted_id, created_at=_now())
                session.add(item)
            item.analysis = analysis.model_dump(mode="json")
            item.status = status.value
            item.analyzed_at = _now()
            await session.commit()

    async def set_status(self, item_id: str, status: ItemStatus) -> None:
        vinted_id = _to_vinted_id(item_id)
        async with self._sessionmaker() as session:
            item = await self._by_vinted_id(session, vinted_id) if vinted_id is not None else None
            if item is None:
                item = Item(vinted_id=vinted_id, created_at=_now())
                session.add(item)
            item.status = status.value
            await session.commit()
