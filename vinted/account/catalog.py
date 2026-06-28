"""
Fetch Vinted catalog items via the authenticated JSON API.

Unlike ``vinted.catalog`` (anonymous HTML scraping, safe to run on a server),
this uses cookies and returns the full, paginated result set.
"""

from __future__ import annotations

import argparse
import asyncio

import httpx

from ..constants import USER_AGENT
from .cookies import load_cookies

CATALOG_ITEMS_URL = "https://www.vinted.pl/api/v2/catalog/items"


async def fetch_catalog_items(
    catalog_ids: str | int | None = None,
    brand_ids: list[str] | None = None,
    status_ids: list[str] | None = None,
    color_ids: list[str] | None = None,
    order: str = "newest_first",
    cookies: dict[str, str] | None = None,
    per_page: int = 96,
    max_pages: int | None = None,
) -> list[dict]:
    """Fetch catalog items via the authenticated JSON API, paginating to the end.

    Mirrors the filters available on the Vinted catalog page. Returns the raw
    item dicts from the API; use ``parse_item_api`` to normalise them.
    """
    if cookies is None:
        cookies = load_cookies()

    base_params: dict[str, object] = {"order": order, "per_page": per_page}
    if catalog_ids is not None:
        base_params["catalog_ids"] = str(catalog_ids)
    if brand_ids:
        base_params["brand_ids[]"] = brand_ids
    if status_ids:
        base_params["status_ids[]"] = status_ids
    if color_ids:
        base_params["color_ids[]"] = color_ids

    headers = {
        "User-Agent": USER_AGENT,
        "Accept": "application/json, text/plain, */*",
    }

    all_items: list[dict] = []
    page = 1

    async with httpx.AsyncClient(
        headers=headers,
        cookies=cookies,
        follow_redirects=True,
    ) as client:
        while True:
            resp = await client.get(url=CATALOG_ITEMS_URL, params={**base_params, "page": page})
            resp.raise_for_status()
            data = resp.json()
            items = data.get("items", [])
            if not items:
                break

            all_items.extend(items)
            pagination = data.get("pagination", {})
            total_pages = pagination.get("total_pages", page)
            print(f"-> Page {page}/{total_pages} ({len(items)} items)")

            if page >= total_pages:
                break
            if max_pages is not None and page >= max_pages:
                break
            page += 1

    return all_items


def parse_item_api(item: dict) -> dict:
    """Map an API item to the same dict format as ``vinted.catalog.parse_item``."""
    total = item.get("total_item_price") or {}
    price = item.get("price") or {}
    price_amount = total.get("amount") or price.get("amount", "0")
    currency = total.get("currency_code") or price.get("currency_code", "PLN")

    return {
        "id": str(item["id"]),
        "title": item.get("title", ""),
        "brand": item.get("brand_title", ""),
        "condition": item.get("status", ""),
        "size": item.get("size_title", ""),
        "price": f"{price_amount} {currency}",
        "url": item.get("url", ""),
        "image_url": (item.get("photo") or {}).get("url", ""),
        "favourite_count": item.get("favourite_count", 0),
        "view_count": item.get("view_count", 0),
    }


async def main() -> None:
    parser = argparse.ArgumentParser(description="Fetch a Vinted catalog via the JSON API.")
    parser.add_argument("catalog_id", nargs="?", default=None, help="catalog_ids filter")
    parser.add_argument("--brand", action="append", dest="brand_ids", help="brand_ids[] filter")
    parser.add_argument("--status", action="append", dest="status_ids", help="status_ids[] filter")
    parser.add_argument("--color", action="append", dest="color_ids", help="color_ids[] filter")
    parser.add_argument("--max-pages", type=int, default=None, help="Limit number of pages")
    args = parser.parse_args()

    items = await fetch_catalog_items(
        catalog_ids=args.catalog_id,
        brand_ids=args.brand_ids,
        status_ids=args.status_ids,
        color_ids=args.color_ids,
        max_pages=args.max_pages,
    )

    print(f"\nFound {len(items)} items:\n")
    header = f"{'ID':>12s} | {'Brand':20s} | {'Size':8s} | {'Price':15s} | Title"
    print(header)
    print("-" * len(header))
    for raw in items:
        p = parse_item_api(raw)
        print(
            f"{p['id']:>12s} | {p['brand'][:20]:20s} | {p['size'][:8]:8s} | "
            f"{p['price']:15s} | {p['title']}"
        )


if __name__ == "__main__":
    asyncio.run(main())
