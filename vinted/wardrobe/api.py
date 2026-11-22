from __future__ import annotations

import re
from datetime import UTC
from datetime import datetime

import httpx

from ..constants import USER_AGENT
from ..utils import get_with_backoff
from .models import MemberState

WARDROBE_API_URL = "https://www.vinted.pl/api/v2/wardrobe/{user_id}/items"
MEMBER_URL = "https://www.vinted.pl/member/{user_id}"

BANNED_RE = re.compile(r'"is_account_banned":(true|false)')
DELETED_RE = re.compile(r'"is_deleted":(true|false)')


def parse_member_state(html: str, user_id: str) -> MemberState:
    """Member account state from the HTML of their profile page.

    The profile's user object (`"id":{user_id},"anon_id"...`) carries
    `is_account_banned` / `is_deleted`; a banned member's wardrobe API returns
    no items. Search from that object so other users on the page don't match.
    """
    text = html.replace('\\"', '"')
    start = text.find(f'"id":{user_id},"anon_id"')
    text = text[start:] if start >= 0 else text
    if (m := DELETED_RE.search(text)) and m.group(1) == "true":
        return MemberState.DELETED
    if (m := BANNED_RE.search(text)) and m.group(1) == "true":
        return MemberState.BANNED
    return MemberState.ACTIVE


async def fetch_wardrobe(
    user_id: str,
    *,
    per_page: int = 96,  # max items per page
    max_pages: int | None = None,
) -> tuple[MemberState, list[dict]]:
    """Fetch the member's account state and all items from their wardrobe.

    Items are only fetched for an active member; a banned or deleted one has
    no listing, so their items come back empty.
    """
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
        resp = await client.get(MEMBER_URL.format(user_id=user_id))
        if resp.status_code == 404:
            return MemberState.DELETED, []
        resp.raise_for_status()
        state = parse_member_state(resp.text, user_id)
        if state != MemberState.ACTIVE:
            print(f"-> Member is {state}, skipping items")
            return state, []

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
    return MemberState.ACTIVE, items


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
