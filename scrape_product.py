"""
Vinted image scraper using Playwright.
Extracts images from a listing via CSS selector: #content > section > section > div

Usage:
    pip install playwright
    playwright install chromium
    python vinted_scraper.py [url]
"""

import asyncio
import sys
from pathlib import Path

import httpx
from playwright.async_api import async_playwright


SELECTOR = "#content > section > section > div"
PRODUCT_URL = "https://www.vinted.pl/items/{product_id}"


async def scrape_images(product_id: str) -> list[str]:
    url = PRODUCT_URL.format(product_id=product_id)

    async with async_playwright() as p:
        browser = await p.chromium.launch(headless=True)
        context = await browser.new_context(
            user_agent=(
                "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) "
                "AppleWebKit/537.36 (KHTML, like Gecko) "
                "Chrome/124.0.0.0 Safari/537.36"
            ),
            locale="pl-PL",
        )
        page = await context.new_page()

        print(f"→ Fetching: {url}")
        await page.goto(url, wait_until="domcontentloaded")

        # Wait for the image container to appear
        try:
            await page.wait_for_selector(SELECTOR, timeout=10_000)
        except Exception:
            print("⚠️  Selector not found within timeout — page may require auth.")

        # Extract all <img> src attributes within the selector
        image_urls: list[str] = await page.eval_on_selector_all(
            f"{SELECTOR} img",
            "imgs => imgs.map(img => img.src || img.getAttribute('data-src')).filter(Boolean)",
        )

        # Deduplicate while preserving order
        unique_urls: list[str] = []
        for u in image_urls:
            if u not in unique_urls:
                unique_urls.append(u)

        await browser.close()
        return unique_urls


async def save_images(image_urls: list[str], product_id: str) -> None:
    """Download images to ./images/{product_id}/."""
    folder = Path("media/images") / product_id
    folder.mkdir(parents=True, exist_ok=True)

    async with httpx.AsyncClient() as client:
        for i, img_url in enumerate(image_urls, 1):
            resp = await client.get(img_url)
            resp.raise_for_status()
            ext = Path(img_url.split("?")[0]).suffix or ".jpg"
            filepath = folder / f"{i}{ext}"
            filepath.write_bytes(resp.content)
            print(f"  Saved: {filepath}")


async def main() -> None:
    product_id = sys.argv[1] if len(sys.argv) > 1 else "8119502397"
    images = await scrape_images(product_id)

    if not images:
        print("No images found.")
        return

    print(f"\n✅ Found {len(images)} image(s), saving to ./images/{product_id}/\n")
    await save_images(images, product_id)


if __name__ == "__main__":
    asyncio.run(main())