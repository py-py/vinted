from __future__ import annotations

import asyncio
import json
import sys

import httpx

from .constants import USER_AGENT

WARDROBE_API_URL = "https://www.vinted.pl/api/v2/wardrobe/{user_id}/items"
MEMBER_URL = "https://www.vinted.pl/member/{user_id}"


async def fetch_wardrobe(
    user_id: str,
    *,
    per_page: int = 20,
    max_pages: int | None = None,
) -> list[dict]:
    """Fetch all items from a Vinted user's wardrobe."""
    items: list[dict] = []
    page = 1

    async with httpx.AsyncClient(
        headers={
            "User-Agent": USER_AGENT,
            "Accept": "application/json, text/plain, */*",
            "Accept-Language": "en-US,en;q=0.9",
            "Referer": MEMBER_URL.format(user_id=user_id),
            "X-Requested-With": "XMLHttpRequest",
        },
        follow_redirects=True,
    ) as client:
        await client.get(MEMBER_URL.format(user_id=user_id))

        while True:
            print(f"-> Fetching page {page}")
            resp = await client.get(
                WARDROBE_API_URL.format(user_id=user_id),
                params={"page": page, "per_page": per_page, "order": "relevance"},
            )
            resp.raise_for_status()

            data = resp.json()
            page_items = data.get("items", [])
            if not page_items:
                break

            items.extend(page_items)

            total_pages = data.get("pagination", {}).get("total_pages", 1)
            if page >= total_pages or (max_pages and page >= max_pages):
                break
            page += 1

    print(f"-> Total items: {len(items)}")
    return items


def parse_item(item: dict) -> dict:
    return {
        "id": item.get("id"),
        "url": item.get("url", ""),
        "name": item.get("title", ""),
        "total_item_price": item.get("total_item_price", {}),
        "favourite_count": item.get("favourite_count", 0),
        "image_urls": [p.get("url", "") for p in item.get("photos", [])],
    }


async def main() -> None:
    user_id = sys.argv[1] if len(sys.argv) > 1 else None
    if user_id is None:
        raise SystemExit("Usage: python -m vinted.wardrobe <user_id>")

    items = await fetch_wardrobe(user_id)
    result = [parse_item(item) for item in items]
    print(json.dumps(result, indent=2, ensure_ascii=False))


if __name__ == "__main__":
    asyncio.run(main())
