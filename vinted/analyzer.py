from __future__ import annotations

import asyncio
import json
import mimetypes
import sys
from pathlib import Path

from dotenv import load_dotenv
from google import genai

from .constants import CATALOG_RECIPES
from .models import VintedProduct
from .scraper import save_images
from .scraper import scrape_product
from .telegram import send_message

load_dotenv()

PROMPTS_DIR = Path(__file__).parent.parent / "prompts"


def load_prompt(catalog_id, language=None) -> str:
    """Load base prompt + type-specific prompt."""
    base = (PROMPTS_DIR / "base.md").read_text()
    type_file = CATALOG_RECIPES[catalog_id]["prompt"]
    specific = (PROMPTS_DIR / type_file).read_text()
    return (
        f"{base}\n\n{specific}" + f"\n\n please, make the response on {language.upper()} language"
        if language
        else ""
    )


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
) -> str:
    client = genai.Client()

    parts = []
    for media_type, data in images:
        parts.append(genai.types.Part.from_bytes(data=data, mime_type=media_type))
    parts.append(f"Product data:\n{product.model_dump_json(indent=2)}")

    # gemini-2.5-flash-lite
    # gemini-2.5-flash
    response = client.models.generate_content(
        model="gemini-2.5-flash-lite",
        contents=parts,
        config=genai.types.GenerateContentConfig(system_instruction=prompt),
    )
    return response.text


async def main() -> None:
    product_id = sys.argv[1] if len(sys.argv) > 1 else "8119502397"
    catalog_id = sys.argv[2] if len(sys.argv) > 2 else "2652"

    # Scrape product data
    product: VintedProduct = await scrape_product(product_id, catalog_id)

    # Load images (download if needed)
    images = load_images(product_id)
    if not images and product["image_urls"]:
        await save_images(product["image_urls"], Path("media/products") / product_id)
        images = load_images(product_id)

    # Load prompt based on product type
    prompt = load_prompt(catalog_id, language="RU")
    data = analyze_with_gemini(product, images, prompt)
    analysis = json.dumps(json.loads(data), indent=2)
    print(analysis)

    # Send to Telegram
    await send_message(product=product, analysis=analysis)


if __name__ == "__main__":
    asyncio.run(main())
