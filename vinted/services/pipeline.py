from __future__ import annotations

from typing import Any

from ..core.config import get_settings
from ..core.logging import get_logger
from ..domain.analysis import BaseAnalysis
from ..domain.analysis import get_schema
from ..domain.enums import ItemStatus
from ..llm.factory import get_analyzer
from ..llm.prompts import load_images
from ..llm.prompts import load_prompt
from ..notifications.telegram import send_message
from ..repositories.items_repo import ItemsRepository
from ..scrapers.product import save_images
from ..scrapers.product import scrape_product

logger = get_logger(__name__)

_TERMINAL_STATUSES = {
    ItemStatus.analyzed.value,
    ItemStatus.notified.value,
    ItemStatus.skipped.value,
}


async def analyze_item(
    product_id: str,
    catalog_id: str | None = None,
    *,
    source: str = "catalog",
    force: bool = False,
) -> dict[str, Any]:
    """End-to-end pipeline for a single item: scrape -> store -> analyze -> store -> notify."""
    settings = get_settings()
    repo = ItemsRepository()

    # Dedup: skip items already processed unless forced.
    if not force:
        existing = await repo.get(product_id)
        if existing and existing.get("status") in _TERMINAL_STATUSES:
            logger.info("Skipping %s (status=%s)", product_id, existing.get("status"))
            return existing

    # 1. Scrape full product detail and persist the raw record.
    product = await scrape_product(product_id, catalog_id=catalog_id)
    await repo.save_product(product, source=source)

    # 2. Ensure images are available locally for the LLM.
    images = load_images(product.id)
    if not images and product.image_urls:
        await save_images(product.image_urls, product.path_to_assets)
        images = load_images(product.id)

    # 3. Run the configured LLM analyzer.
    prompt = load_prompt(product.catalog_id)
    schema = get_schema(product.catalog_id)
    analyzer = get_analyzer()
    analysis: BaseAnalysis = await analyzer.analyze(product, images, prompt, schema)

    # 4. Decide whether this is worth a notification.
    should_notify = (
        analysis.recommendation.value in settings.notify_recommendations
        and analysis.rating >= settings.notify_min_rating
    )
    status = ItemStatus.notified if should_notify else ItemStatus.skipped
    await repo.save_analysis(product.id, analysis, status=status)

    # 5. Notify.
    if should_notify:
        await send_message(product=product, summary=analysis.format(product))

    logger.info("Processed %s -> %s", product.id, status.value)
    return {
        "id": product.id,
        "status": status.value,
        "analysis": analysis.model_dump(mode="json"),
    }
