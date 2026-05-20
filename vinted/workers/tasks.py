from __future__ import annotations

from ..core.logging import get_logger
from ..domain.enums import ItemStatus
from ..repositories.items_repo import ItemsRepository
from ..services.pipeline import analyze_item

logger = get_logger(__name__)


async def analyze_item_task(
    product_id: str,
    catalog_id: str | None = None,
    *,
    source: str = "catalog",
    force: bool = False,
) -> None:
    """Background-safe wrapper around the pipeline.

    Swallows exceptions (logging them and marking the item failed) so a single
    bad item never takes down a batch. This is the unit of work to hand to
    FastAPI BackgroundTasks now, or a Cloud Tasks / Pub-Sub worker later.
    """
    try:
        await analyze_item(product_id, catalog_id, source=source, force=force)
    except Exception:
        logger.exception("Failed to analyze item %s", product_id)
        try:
            await ItemsRepository().set_status(product_id, ItemStatus.failed)
        except Exception:
            logger.exception("Could not mark item %s as failed", product_id)
