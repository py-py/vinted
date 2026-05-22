from __future__ import annotations

import mimetypes
from pathlib import Path

from ..constants import CATALOG_RECIPES
from ..constants import PROMPTS_DIR
from ..storage.gcs import download_bytes
from ..storage.gcs import list_blob_names
from ..storage.gcs import product_prefix
from .base import Image

_IMAGE_SUFFIXES = (".jpg", ".jpeg", ".png", ".webp", ".gif")


def load_prompt(catalog_id: str) -> str:
    """Compose base prompt + catalog-specific prompt + user settings."""
    prompt = (PROMPTS_DIR / "base.md").read_text()

    recipe = CATALOG_RECIPES.get(catalog_id, {})
    if recipe.get("prompt"):
        prompt += "\n\n" + (PROMPTS_DIR / recipe["prompt"]).read_text()

    prompt += "\n\n" + (PROMPTS_DIR / "user_settings.md").read_text()
    return prompt


async def load_images(product_id: str) -> list[Image]:
    """Load saved product images from GCS as (media_type, bytes) tuples."""
    images: list[Image] = []
    for name in await list_blob_names(product_prefix(product_id)):
        if Path(name).suffix.lower() in _IMAGE_SUFFIXES:
            media_type = mimetypes.guess_type(name)[0] or "image/jpeg"
            images.append((media_type, await download_bytes(name)))
    return images
