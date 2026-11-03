"""
Fetch Vinted favourites via JSON API.

Cookies are stored in a local JSON file; the user_id is read from the
access token unless passed as an argument.
"""

from __future__ import annotations

import asyncio
import sys

import httpx

from vinted.account.cookies import load_cookies
from vinted.account.cookies import user_id_from_token
from vinted.constants import USER_AGENT

FAVOURITES_URL = "https://www.vinted.pl/api/v2/users/{user_id}/items/favourites"


async def fetch_favourites(
    user_id: str,
    cookies: dict[str, str] | None = None,
    per_page: int = 96,
) -> list[dict]:
    if cookies is None:
        cookies = load_cookies()

    url = FAVOURITES_URL.format(user_id=user_id)

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
            resp = await client.get(url, params={"per_page": per_page, "page": page})
            resp.raise_for_status()
            data = resp.json()
            items = data.get("items", [])
            if not items:
                break

            all_items.extend(items)
            print(f"-> Page {page} ({len(items)} items)")

            if len(items) < per_page:
                break
            page += 1

    return all_items


def parse_favourite_item(item: dict) -> dict:
    """Map API item to the same dict format as catalog.parse_catalog()."""
    total = item.get("total_item_price", {})
    price_amount = total.get("amount") or item.get("price", {}).get("amount", "0")
    currency = total.get("currency_code") or item.get("price", {}).get("currency_code", "PLN")

    return {
        "id": str(item["id"]),
        "title": item.get("title", ""),
        "brand": item.get("brand_title", ""),
        "condition": item.get("status", ""),
        "size": item.get("size_title", ""),
        "price": f"{price_amount} {currency}",
        "url": item.get("url", ""),
        "image_url": item.get("photo", {}).get("url", ""),
        "catalogue_id": str(item.get("catalogue_id", "")),
        "favourite_count": item.get("favourite_count", 0),
    }


async def main() -> None:
    user_id = sys.argv[1] if len(sys.argv) > 1 else user_id_from_token()
    items = await fetch_favourites(user_id=user_id)
    print(f"Total favourites: {len(items)}\n")
    header = f"{'ID':>12s} | {'Brand':20s} | {'Size':8s} | {'Price':15s} | Title"
    print(header)
    print("-" * len(header))
    for item in items:
        p = parse_favourite_item(item)
        print(
            f"{p['id']:>12s} | {p['brand']:20s} | {p['size']:8s} | {p['price']:15s} | {p['title']}"
        )


if __name__ == "__main__":
    asyncio.run(main())
