from __future__ import annotations

import asyncio
import mimetypes
import sys
from pathlib import Path

from dotenv import load_dotenv
from google import genai

from .constants import CATALOG_RECIPES
from .constants import PROMPTS_DIR
from .formats import format_analytics
from .models import VintedProduct
from .schemas import BaseAnalysis
from .schemas import get_schema
from .scraper import save_images
from .scraper import scrape_product
from .telegram import send_message

load_dotenv()


def load_prompt(catalog_id) -> str:
    """Load base prompt + type-specific prompt + user settings."""
    base = (PROMPTS_DIR / "base.md").read_text()
    type_file = CATALOG_RECIPES[catalog_id]["prompt"]
    specific = (PROMPTS_DIR / type_file).read_text()
    user_settings = (PROMPTS_DIR / "user_settings.md").read_text()
    return f"{base}\n\n{specific}\n\n{user_settings}"


def load_image_paths(product_id: str) -> list[Path]:
    """Load saved images from disk. Returns list of (media_type, bytes)."""
    folder = Path("media/products") / product_id
    return sorted(folder.iterdir()) if folder.exists() else []


def load_images(product_id: str) -> list[tuple[str, bytes]]:
    """Load saved images from disk. Returns list of (media_type, bytes)."""
    images = []
    for path in load_image_paths(product_id):
        if path.suffix.lower() in (".jpg", ".jpeg", ".png", ".webp", ".gif"):
            media_type = mimetypes.guess_type(path.name)[0] or "image/jpeg"
            images.append((media_type, path.read_bytes()))
    return images


def analyze_with_gemini(
    product: VintedProduct, images: list[tuple[str, bytes]], prompt: str
) -> BaseAnalysis:
    print(f"-> Analyzing: {product.url}")

    parts = []
    for media_type, data in images:
        parts.append(genai.types.Part.from_bytes(data=data, mime_type=media_type))
    parts.append(f"Product data:\n{product.model_dump_json(indent=2)}")

    # gemini-2.5-flash
    # gemini-2.5-flash-lite
    # gemini-3-flash-preview
    # gemini-3-pro-preview
    # gemini-3.1-pro-preview
    #   ┌───────────────────────┬───────────────┬──────────┬───────────────┐
    #   │        Модель         │   Скорость    │ Качество │     Цена      │
    #   ├───────────────────────┼───────────────┼──────────┼───────────────┤
    #   │ gemini-2.5-flash      │ быстрая       │ хорошее  │ дешёвая       │
    #   ├───────────────────────┼───────────────┼──────────┼───────────────┤
    #   │ gemini-2.5-flash-lite │ самая быстрая │ базовое  │ самая дешёвая │
    #   ├───────────────────────┼───────────────┼──────────┼───────────────┤
    #   │ gemini-2.5-pro        │ медленная     │ лучшее   │ дорогая       │
    #   └───────────────────────┴───────────────┴──────────┴───────────────┘
    #
    #   Preview (нестабильные):
    #
    #   ┌────────────────────────┬───────────────────────┐
    #   │         Модель         │        Заметки        │
    #   ├────────────────────────┼───────────────────────┤
    #   │ gemini-3-flash-preview │ новейшая, но preview  │
    #   ├────────────────────────┼───────────────────────┤
    #   │ gemini-3-pro-preview   │ новейшая pro, preview │
    #   ├────────────────────────┼───────────────────────┤
    #   │ gemini-3.1-pro-preview │ ещё новее, preview    │
    #   └────────────────────────┴───────────────────────┘
    client = genai.Client()
    schema = get_schema(product.catalog_id)
    response = client.models.generate_content(
        model="gemini-2.5-flash",
        contents=parts,
        config=genai.types.GenerateContentConfig(
            system_instruction=prompt,
            temperature=0.1,
            response_mime_type="application/json",
            response_schema=schema,
        ),
    )
    return schema.model_validate_json(response.text)


async def main() -> None:
    product_id = sys.argv[1] if len(sys.argv) > 1 else None
    catalog_id = sys.argv[2] if len(sys.argv) > 2 else None

    if product_id is None:
        raise SystemExit("Usage: python -m vinted.analyzer <product_id> [catalog_id]")

    # Scrape product data
    product: VintedProduct = await scrape_product(product_id, catalog_id=catalog_id)

    # Load images (download if needed)
    images = load_images(product_id)
    if not images and product.image_urls:
        await save_images(product.image_urls, product.path_to_images)
        images = load_images(product_id)

    # Load prompt based on product type
    prompt = load_prompt(product.catalog_id)
    data: BaseAnalysis = analyze_with_gemini(product, images, prompt)
    print(data.model_dump_json(indent=2))

    # Formatting
    analytics_summary = format_analytics(product, data)
    print(analytics_summary)

    # Send to Telegram
    await send_message(product=product, analytics_summary=analytics_summary)


if __name__ == "__main__":
    asyncio.run(main())
