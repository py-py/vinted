from __future__ import annotations

from datetime import UTC
from datetime import datetime

import httpx

from ..constants import USER_AGENT
from ..utils import get_with_backoff

WARDROBE_API_URL = "https://www.vinted.pl/api/v2/wardrobe/{user_id}/items"
MEMBER_URL = "https://www.vinted.pl/member/{user_id}"


async def fetch_wardrobe(
    user_id: str,
    *,
    per_page: int = 96,  # max items per page
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
            resp = await get_with_backoff(
                client,
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
    """The Vinted-sourced part of an item doc (stored under `api`)."""
    return {
        "id": item.get("id"),
        "title": item.get("title", ""),
        "url": item.get("url", ""),
        "price": item.get("price") or {},
        "brand": item.get("brand", ""),
        "size": item.get("size", ""),
        "status": item.get("status", ""),
        "photo_urls": [p.get("url", "") for p in item.get("photos") or []],
        "favourite_count": item.get("favourite_count", 0),
        "view_count": item.get("view_count", 0),
    }


def listed_at(item: dict) -> datetime | None:
    """When the listing was created: the earliest photo upload timestamp.

    The wardrobe API has no created_at; photo timestamps track item creation
    (see PLAN.md). None for an item without photo timestamps.
    """
    stamps = [
        hr["timestamp"]
        for p in item.get("photos") or []
        if (hr := p.get("high_resolution")) and hr.get("timestamp")
    ]
    return datetime.fromtimestamp(min(stamps), UTC) if stamps else None
