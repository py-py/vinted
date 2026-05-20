from __future__ import annotations

from datetime import UTC
from datetime import datetime
from typing import Any

from ..core.config import get_settings
from ..domain.analysis import BaseAnalysis
from ..domain.enums import ItemStatus
from ..domain.product import VintedProduct
from .firestore import get_client


def _now() -> datetime:
    return datetime.now(UTC)


class ItemsRepository:
    """Firestore-backed store for scraped items and their analyses.

    Document layout (collection ``items``, doc id = Vinted item id)::

        {
            ...scraped product fields...,
            "status": "new" | "analyzed" | "notified" | "skipped" | "failed",
            "source": "catalog" | "favourites" | "wardrobe",
            "analysis": { ...BaseAnalysis... },
            "created_at": <timestamp>,
            "analyzed_at": <timestamp>,
        }
    """

    def __init__(self, collection: str | None = None) -> None:
        self._db = get_client()
        self._collection = collection or get_settings().firestore_collection

    def _doc(self, item_id: str):
        return self._db.collection(self._collection).document(item_id)

    async def exists(self, item_id: str) -> bool:
        snapshot = await self._doc(item_id).get()
        return snapshot.exists

    async def get(self, item_id: str) -> dict[str, Any] | None:
        snapshot = await self._doc(item_id).get()
        return snapshot.to_dict() if snapshot.exists else None

    async def save_product(self, product: VintedProduct, *, source: str = "catalog") -> None:
        data = product.model_dump(exclude={"ld_json"})
        data |= {
            "status": ItemStatus.new.value,
            "source": source,
            "created_at": _now(),
        }
        await self._doc(product.id).set(data, merge=True)

    async def save_analysis(
        self, item_id: str, analysis: BaseAnalysis, *, status: ItemStatus
    ) -> None:
        await self._doc(item_id).set(
            {
                "analysis": analysis.model_dump(mode="json"),
                "status": status.value,
                "analyzed_at": _now(),
            },
            merge=True,
        )

    async def set_status(self, item_id: str, status: ItemStatus) -> None:
        await self._doc(item_id).set({"status": status.value}, merge=True)
