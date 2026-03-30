from __future__ import annotations

import re

import httpx
from bs4 import BeautifulSoup


CATALOGS = {
    4733: "Skis",
    2683: "Man Ski boots",
    2652: "Woman Ski boots",
    2715: "Girls ski boots",
    2746: "Boys ski boots",
}

CATALOG_URL = (
    "https://www.vinted.pl/catalog?catalog[]={catalog_id}&order=newest_first&page={page}"
)

USER_AGENT = (
    "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) "
    "AppleWebKit/537.36 (KHTML, like Gecko) "
    "Chrome/124.0.0.0 Safari/537.36"
)


def parse_catalog(catalog_id: int, page_number: int = 1) -> list[dict]:
    """Parse Vinted catalog page and return a list of item dicts."""
    url = CATALOG_URL.format(catalog_id=catalog_id, page=page_number)

    resp = httpx.get(url, headers={"User-Agent": USER_AGENT}, follow_redirects=True)
    resp.raise_for_status()

    soup = BeautifulSoup(resp.text, "html.parser")
    raw_items = soup.select("[data-testid='grid-item']")

    items = []
    for el in raw_items:
        item = _parse_item(el)
        if item:
            items.append(item)

    return items


def parse_item_id(url: str) -> str | None:
    """
    Extract the numeric item ID from a Vinted item URL.
    URL: https://www.vinted.pl/items/8142652778-sjezdove-lyze-150-cm-head?referrer=catalog
    """
    match = re.search(r"/items/(\d+)", url)
    return match.group(1) if match else None


def _parse_item(el: BeautifulSoup) -> dict | None:
    """Extract item data from a grid-item element."""
    link = el.select_one("a[href*='/items/']")
    if not link:
        return None
    href = link.get("href", "")
    item_url = f"https://www.vinted.pl{href}" if href.startswith("/") else href

    item_id = parse_item_id(href)

    img = el.select_one("img")
    image_url = (img.get("src") or "") if img else ""
    alt = (img.get("alt") or "") if img else ""

    price_el = el.select_one("[data-testid$='price-text'], .web_ui__Text__subtitle")
    price_text = (price_el.get_text(strip=True) if price_el else "").replace("\xa0", " ")

    brand_match = re.search(r"marka:\s*(.+?)(?:,|$)", alt)
    brand = brand_match.group(1).strip() if brand_match else ""

    title = alt.split(",")[0].strip() if alt else ""

    condition_match = re.search(r"stan:\s*(.+?)(?:,|$)", alt)
    condition = condition_match.group(1).strip() if condition_match else ""

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
    items = parse_catalog(catalog_id=2683, page_number=1)
    print(f"Found {len(items)} items:\n")
    for item in items:
        print(item)