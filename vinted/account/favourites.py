"""
Fetch Vinted favourites via JSON API.

Cookies are stored in a local JSON file.
"""

from __future__ import annotations

import asyncio
import json
import os
import sys
from pathlib import Path

import httpx
from constants import USER_AGENT
from dotenv import load_dotenv

load_dotenv()
VINTED_USER_ID = os.environ["VINTED_USER_ID"]

FAVOURITES_URL = "https://www.vinted.pl/api/v2/users/{user_id}/items/favourites"

COOKIES_PATH = Path(__file__).parent.parent / "cookies.json"

# Minimum cookies required for authenticated API access
REQUIRED_COOKIE_KEYS = [
    "access_token_web",
    "datadome",
    "cf_clearance",
]


def load_cookies(path: Path = COOKIES_PATH) -> dict[str, str]:
    if not path.exists():
        raise FileNotFoundError(
            f"Cookies file not found: {path}\nCreate it with keys: {REQUIRED_COOKIE_KEYS}"
        )
    cookies = json.loads(path.read_text())
    missing = [k for k in REQUIRED_COOKIE_KEYS if k not in cookies]
    if missing:
        raise ValueError(f"Missing required cookies: {missing}")
    return cookies


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
    user_id = sys.argv[1] if len(sys.argv) > 1 else VINTED_USER_ID
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
