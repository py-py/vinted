"""
Analyze a scraped Vinted product using Claude or Gemini.

Usage:
    python analyze.py <product_id> [--provider claude|gemini]
"""

import asyncio
import base64
import json
import mimetypes
import sys
from pathlib import Path

from scrape_product import scrape_product

PROMPTS_DIR = Path(__file__).parent / "prompts"

# catalog_id keywords -> prompt file
PRODUCT_TYPE_MAP = {
    "ski boots": "ski_boots.md",
    "buty narciarskie": "ski_boots.md",
    "skis": "skis.md",
    "narty": "skis.md",
    "lyže": "skis.md",
}


def detect_product_type(product: dict) -> str | None:
    """Detect product type from title/description/properties."""
    text = " ".join([
        product.get("title", ""),
        product.get("description", ""),
        " ".join(product.get("properties", {}).values()),
    ]).lower()

    for keyword, prompt_file in PRODUCT_TYPE_MAP.items():
        if keyword in text:
            return prompt_file
    return None


def load_prompt(product: dict) -> str:
    """Load base prompt + type-specific prompt."""
    base = (PROMPTS_DIR / "base.md").read_text()
    type_file = detect_product_type(product)
    if type_file:
        specific = (PROMPTS_DIR / type_file).read_text()
        return f"{base}\n\n{specific}"
    return base


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


def analyze_with_claude(product: dict, images: list[tuple[str, bytes]], prompt: str) -> str:
    import anthropic

    client = anthropic.Anthropic()

    content = []
    for media_type, data in images:
        content.append({
            "type": "image",
            "source": {
                "type": "base64",
                "media_type": media_type,
                "data": base64.standard_b64encode(data).decode(),
            },
        })
    content.append({
        "type": "text",
        "text": f"Product data:\n{json.dumps(product, indent=2, ensure_ascii=False)}",
    })

    response = client.messages.create(
        model="claude-sonnet-4-6-20250514",
        max_tokens=4096,
        system=prompt,
        messages=[{"role": "user", "content": content}],
    )
    return response.content[0].text


def analyze_with_gemini(product: dict, images: list[tuple[str, bytes]], prompt: str) -> str:
    from google import genai

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


PROVIDERS = {
    "claude": analyze_with_claude,
    "gemini": analyze_with_gemini,
}


async def main() -> None:
    product_id = sys.argv[1] if len(sys.argv) > 1 else "8119502397"
    provider = sys.argv[2] if len(sys.argv) > 2 else "claude"

    if provider not in PROVIDERS:
        print(f"Unknown provider: {provider}. Use: {', '.join(PROVIDERS)}")
        sys.exit(1)

    # Scrape product data
    product = await scrape_product(product_id)

    # Load images (download if needed)
    images = load_images(product_id)
    if not images and product["image_urls"]:
        from scrape_product import save_images
        await save_images(product["image_urls"], Path("media/products") / product_id)
        images = load_images(product_id)

    # Load prompt based on product type
    prompt = load_prompt(product)
    print(f"-> Product type prompt: {detect_product_type(product) or 'base only'}")
    print(f"-> Images: {len(images)}")
    print(f"-> Provider: {provider}")
    print()

    # Analyze
    analyze_fn = PROVIDERS[provider]
    result = analyze_fn(product, images, prompt)
    print(result)


if __name__ == "__main__":
    asyncio.run(main())
