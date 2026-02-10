import re
from typing import Optional

from playwright.sync_api import sync_playwright

CATALOG_URL = (
    "https://www.vinted.pl/catalog?catalog[]=4733&order=newest_first&page={page}"
)


def parse_catalog(page_number: int = 1) -> list[dict]:
    """Parse Vinted catalog page and return a list of item dicts."""
    url = CATALOG_URL.format(page=page_number)

    with sync_playwright() as pw:
        browser = pw.chromium.launch(headless=True)
        context = browser.new_context(
            user_agent=(
                "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) "
                "AppleWebKit/537.36 (KHTML, like Gecko) "
                "Chrome/131.0.0.0 Safari/537.36"
            ),
            locale="en-US",
        )
        page = context.new_page()
        page.goto(url, wait_until="domcontentloaded")

        # Accept cookies dialog if it appears
        try:
            page.click("[id*='onetrust-accept'], [data-testid*='cookie'] button", timeout=3000)
        except Exception:
            pass

        page.wait_for_selector("[data-testid='grid-item']", timeout=15000)

        raw_items = page.query_selector_all("[data-testid='grid-item']")
        items = []

        for el in raw_items:
            item = _parse_item(el)
            if item:
                items.append(item)

        browser.close()

    return items


def parse_item_id(url: str) -> Optional[str]:
    """
    Extract the numeric item ID from a Vinted item URL.
    URL: https://www.vinted.pl/items/8142652778-sjezdove-lyze-150-cm-head?referrer=catalog
    """
    match = re.search(r"/items/(\d+)", url)
    return match.group(1) if match else None


def _parse_item(el) -> Optional[dict]:
    """Extract item data from a grid-item element."""
    # Link & URL
    link = el.query_selector("a[href*='/items/']")
    if not link:
        return None
    href = link.get_attribute("href") or ""
    item_url = f"https://www.vinted.pl{href}" if href.startswith("/") else href

    # Item ID from URL
    item_id = parse_item_id(href)

    # Image
    img = el.query_selector("img")
    image_url = (img.get_attribute("src") or "") if img else ""

    # Alt text often contains: "title, marka: Brand, stan: Condition, price"
    alt = (img.get_attribute("alt") or "") if img else ""

    # Price – look for price element
    price_el = el.query_selector("[data-testid$='price-text'], .web_ui__Text__subtitle")
    price_text = (price_el.inner_text().strip() if price_el else "").replace("\xa0", " ")

    # Brand
    brand_match = re.search(r"marka:\s*(.+?)(?:,|$)", alt)
    brand = brand_match.group(1).strip() if brand_match else ""

    # Title – first segment of the alt text before first comma
    title = alt.split(",")[0].strip() if alt else ""

    # Condition (stan)
    condition_match = re.search(r"stan:\s*(.+?)(?:,|$)", alt)
    condition = condition_match.group(1).strip() if condition_match else ""

    # Size / Rozmiar
    size_match = re.search(r"rozmiar:\s*(.+?)(?:,|$)", alt, re.IGNORECASE)
    size = size_match.group(1).strip() if size_match else ""

    return {
        "id": item_id,
        "title": title,
        "brand": brand,
        "condition": condition,
        "size": size,
        "price": price_text,
        "url": item_url,
        "image_url": image_url,
    }


if __name__ == "__main__":
    items = parse_catalog(page_number=1)
    print(f"Found {len(items)} items:\n")
    for item in items:
        print(item)