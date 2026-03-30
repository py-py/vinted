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


IMAGE_SELECTOR = ".item-photos"
PROPERTIES_SELECTOR = ".details-list--details"
DESCRIPTION_SELECTOR = "div.u-text-wrap"
PRODUCT_URL = "https://www.vinted.pl/items/{product_id}"


async def scrape_product(product_id: str) -> dict:
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
            await page.wait_for_selector(IMAGE_SELECTOR, timeout=10_000)
        except Exception:
            print("⚠️  Selector not found within timeout — page may require auth.")

        # Extract all <img> src attributes within the selector
        image_urls: list[str] = await page.eval_on_selector_all(
            f"{IMAGE_SELECTOR} img",
            "imgs => imgs.map(img => img.src || img.getAttribute('data-src')).filter(Boolean)",
        )

        # Deduplicate while preserving order
        unique_urls: list[str] = []
        for u in image_urls:
            if u not in unique_urls:
                unique_urls.append(u)

        # Wait for the details section to load
        try:
            await page.wait_for_selector(PROPERTIES_SELECTOR, timeout=10_000)
        except Exception:
            pass

        # Extract properties (key-value pairs from the details section)
        properties = {}
        try:
            properties = await page.eval_on_selector(
                PROPERTIES_SELECTOR,
                """el => {
                    const props = {};
                    const items = el.querySelectorAll('.details-list__item');
                    items.forEach(item => {
                        const vals = item.querySelectorAll('.details-list__item-value');
                        if (vals.length >= 2) {
                            props[vals[0].innerText.trim()] = vals[1].innerText.trim();
                        }
                    });
                    return props;
                }""",
            )
        except Exception:
            print("⚠️  Could not extract properties.")

        # Extract description (remove max-height clipping to get full text)
        description = ""
        try:
            description = await page.eval_on_selector(
                DESCRIPTION_SELECTOR,
                """el => {
                    const clipped = el.querySelector('[style*="max-height"]');
                    if (clipped) clipped.style.maxHeight = 'none';
                    return el.innerText.trim();
                }""",
            )
        except Exception:
            print("⚠️  Could not extract description.")

        # Extract seller info
        seller = {}
        try:
            seller = await page.evaluate(
                """() => {
                    const links = document.querySelectorAll('a[href*="/member/"]');
                    const profileLink = [...links].find(a => !a.href.includes('signup'));
                    if (!profileLink) return {};

                    const href = profileLink.getAttribute('href') || '';
                    const nameEl = profileLink.querySelector('[class*="Cell__title"]');
                    const name = nameEl ? nameEl.innerText.trim() : '';

                    const ratingEl = profileLink.querySelector('[aria-label]');
                    const ratingAria = ratingEl ? ratingEl.getAttribute('aria-label') || '' : '';
                    const starsMatch = ratingAria.match(/([\d.,]+)\s/);
                    const stars = starsMatch ? parseFloat(starsMatch[1].replace(',', '.')) : null;

                    const labelEl = profileLink.querySelector('[class*="Rating__label"]');
                    const reviews = labelEl ? parseInt(labelEl.innerText.trim(), 10) : null;

                    const locEl = document.querySelector('[data-testid="seller-location"]');
                    const location = locEl ? locEl.innerText.trim() : '';

                    return {name, link: href, stars, reviews, location};
                }"""
            )
        except Exception:
            print("⚠️  Could not extract seller info.")

        await browser.close()

    return {
        "product_id": product_id,
        "url": url,
        "description": description,
        "properties": properties,
        "seller": seller,
        "image_urls": unique_urls,
    }


async def save_images(image_urls: list[str], product_id: str) -> None:
    """Download images to ./images/{product_id}/."""
    folder = Path("media/products") / product_id
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
    product_id = sys.argv[1] if len(sys.argv) > 1 else "8473373075"
    product = await scrape_product(product_id)

    if product["seller"]:
        s = product["seller"]
        print(f"\n👤 Seller: {s.get('name', '?')}")
        print(f"  Link: https://www.vinted.pl{s.get('link', '')}")
        print(f"  Stars: {s.get('stars', '?')} / 5")
        print(f"  Reviews: {s.get('reviews', '?')}")
        print(f"  Location: {s.get('location', '?')}")

    if product["properties"]:
        print("\n📋 Properties:")
        for key, value in product["properties"].items():
            print(f"  {key}: {value}")

    if product["description"]:
        print(f"\n📝 Description:\n  {product['description']}")

    if not product["image_urls"]:
        print("\nNo images found.")
        return

    print(f"\n✅ Found {len(product['image_urls'])} image(s), saving to ./images/{product_id}/\n")
    await save_images(product["image_urls"], product_id)


if __name__ == "__main__":
    asyncio.run(main())