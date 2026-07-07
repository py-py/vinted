from __future__ import annotations

import re

import httpx
from bs4 import BeautifulSoup

from ..constants import CATALOG_URL
from ..constants import USER_AGENT
from ..utils import parse_item_id


def fetch_catalog_html(url: str) -> str:
    """Fetch a Vinted catalog/search page and return its HTML."""
    resp = httpx.get(url, headers={"User-Agent": USER_AGENT}, follow_redirects=True)
    resp.raise_for_status()
    return resp.text


def parse_catalog_html(html: str) -> list[dict]:
    """Parse catalog HTML and return a list of item dicts."""
    soup = BeautifulSoup(html, "html.parser")
    raw_items = soup.select("[data-testid='grid-item']")

    items = []
    for el in raw_items:
        if item := parse_item(el):
            items.append(item)

    return items


def parse_catalog_url(url: str) -> list[dict]:
    """Parse a full Vinted catalog/search URL (keeps filters, search_id, etc.)."""
    return parse_catalog_html(fetch_catalog_html(url))


def parse_catalog(catalog_id: int, page_number: int = 1) -> list[dict]:
    """Parse a Vinted catalog page by catalog_id and return a list of item dicts."""
    url = CATALOG_URL.format(catalog_id=catalog_id, page=page_number)
    return parse_catalog_url(url)


def parse_item(el: BeautifulSoup) -> dict | None:
    """Extract item data from a grid-item element."""
    link = el.select_one("a[href*='/items/']")
    if not link:
        return None
    href = link.get("href", "").split("?")[0]  # drop tracking query (e.g. ?referrer=catalog)
    item_url = f"https://www.vinted.pl{href}" if href.startswith("/") else href

    item_id = parse_item_id(href)

    img = el.select_one("img")
    image_url = (img.get("src") or "") if img else ""
    alt = (img.get("alt") or "") if img else ""

    price_el = el.select_one("[data-testid$='price-text'], .web_ui__Text__subtitle")
    price_text = (price_el.get_text(strip=True) if price_el else "").replace("\xa0", " ")

    total_el = el.select_one("[data-testid='total-combined-price']")
    total_price_text = (total_el.get_text(strip=True) if total_el else "").replace("\xa0", " ")

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
        "total_price": total_price_text,
        "url": item_url,
        "image_url": image_url,
    }


if __name__ == "__main__":
    items = parse_catalog(catalog_id=2683, page_number=1)
    print(f"Found {len(items)} items:\n")
    for item in items:
        print(item)
