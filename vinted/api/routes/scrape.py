from __future__ import annotations

from fastapi import APIRouter
from fastapi import BackgroundTasks

from ...scrapers.catalog import parse_catalog
from ...workers.tasks import analyze_item_task

router = APIRouter(prefix="/scrape", tags=["scrape"])


@router.post("/catalog/{catalog_id}")
async def scrape_catalog(
    catalog_id: int,
    background: BackgroundTasks,
    pages: int = 1,
    force: bool = False,
) -> dict:
    """Scrape a catalog and enqueue per-item analysis in the background."""
    item_ids: list[str] = []
    for page in range(1, pages + 1):
        for item in parse_catalog(catalog_id, page):
            item_id = item.get("id")
            if not item_id:
                continue
            background.add_task(
                analyze_item_task,
                item_id,
                str(catalog_id),
                source="catalog",
                force=force,
            )
            item_ids.append(item_id)

    return {"catalog_id": catalog_id, "enqueued": len(item_ids), "item_ids": item_ids}


@router.post("/item/{item_id}")
async def scrape_item(
    item_id: str,
    background: BackgroundTasks,
    catalog_id: str | None = None,
    force: bool = False,
) -> dict:
    """Enqueue analysis for a single item."""
    background.add_task(
        analyze_item_task,
        item_id,
        catalog_id,
        source="manual",
        force=force,
    )
    return {"item_id": item_id, "status": "enqueued"}
