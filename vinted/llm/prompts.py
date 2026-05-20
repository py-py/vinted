from __future__ import annotations

import mimetypes
from pathlib import Path

from ..constants import CATALOG_RECIPES
from ..constants import PROMPTS_DIR
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


def load_images(product_id: str) -> list[Image]:
    """Load saved product images from disk as (media_type, bytes) tuples."""
    folder = Path("media/products") / product_id
    if not folder.exists():
        return []

    images: list[Image] = []
    for path in sorted(folder.iterdir()):
        if path.suffix.lower() in _IMAGE_SUFFIXES:
            media_type = mimetypes.guess_type(path.name)[0] or "image/jpeg"
            images.append((media_type, path.read_bytes()))
    return images
