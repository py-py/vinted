"""
Analyze a scraped Vinted product using Claude or Gemini.

Usage:
    python analyze.py <product_id> [--provider claude|gemini]
"""
from __future__ import annotations

import asyncio
from dotenv import load_dotenv
from google import genai

import json
import mimetypes
import sys
from pathlib import Path

from scrape_product import scrape_product
from constants import CATALOG_RECIPES

load_dotenv()

PROMPTS_DIR = Path(__file__).parent / "prompts"


def load_prompt(catalog_id) -> str:
    """Load base prompt + type-specific prompt."""
    base = (PROMPTS_DIR / "base.md").read_text()
    type_file = CATALOG_RECIPES[catalog_id]["prompt"]
    specific = (PROMPTS_DIR / type_file).read_text()
    return f"{base}\n\n{specific}"


def load_images(product_id: str) -> list[tuple[str, bytes]]:
    """Load saved images from disk. Returns list of (media_type, bytes)."""
    folder = Path("media/products") / product_id
    if not folder.exists():
        return []

    images = []
    for path in sorted(folder.iterdir()):
        if path.suffix.lower() in (".jpg", ".jpeg", ".png", ".webp", ".gif"):
            media_type = mimetypes.guess_type(path.name)[0] or "image/jpeg"
            images.append((media_type, path.read_bytes()))
    return images



def analyze_with_gemini(product: dict, images: list[tuple[str, bytes]], prompt: str) -> str:
    client = genai.Client()

    parts = []
    for media_type, data in images:
        parts.append(genai.types.Part.from_bytes(data=data, mime_type=media_type))
    parts.append(f"Product data:\n{json.dumps(product, indent=2, ensure_ascii=False)}")

    response = client.models.generate_content(
        model="gemini-2.5-flash",
        contents=parts,
        config=genai.types.GenerateContentConfig(system_instruction=prompt),
    )
    return response.text


async def main() -> None:
    product_id = sys.argv[1] if len(sys.argv) > 1 else "8119502397"
    catalog_id = sys.argv[2] if len(sys.argv) > 2 else "2652"

    # Scrape product data
    product = await scrape_product(product_id, catalog_id)

    # Load images (download if needed)
    images = load_images(product_id)
    if not images and product["image_urls"]:
        from scrape_product import save_images
        await save_images(product["image_urls"], Path("media/products") / product_id)
        images = load_images(product_id)

    # Load prompt based on product type
    prompt = load_prompt(catalog_id)
    print(f"-> Images: {len(images)}")
    result = analyze_with_gemini(product, images, prompt)
    print(result)


if __name__ == "__main__":
    asyncio.run(main())
