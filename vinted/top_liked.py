"""
Rank Vinted catalog items by likes (``favourite_count``).

A catalog listing URL (the one in the browser, with ``catalog[]``, ``brand_ids[]``,
``status_ids[]``, ``order`` …) is translated to the JSON catalog API
``/api/v2/catalog/items`` — which, unlike the HTML grid, exposes ``favourite_count`` per
item. We page through the listing, then sort all items by likes descending.

Results are sorted by likes and written to a CSV in media/.

Auth: the catalog API needs the same cookies as favourites (``access_token_web`` is a
~2h token), loaded from cookies.json. Refresh them with the ``vinted-refresh-cookies``
skill if you get a 401.

    uv run python -m vinted.top_liked "<vinted.pl/catalog URL>" --pages 10
"""

from __future__ import annotations

import argparse
import asyncio
import datetime
import urllib.parse
from pathlib import Path

import httpx
import petl

from .constants import USER_AGENT
from .favourites import load_cookies

CATALOG_ITEMS_URL = "https://www.vinted.pl/api/v2/catalog/items"

# project_root/media — this file lives in <root>/vinted/
MEDIA_DIR = Path(__file__).resolve().parents[1] / "media"

CSV_HEADER = [
    "favourite_count",
    "created",
    "price",
    "size",
    "brand",
    "title",
    "url",
    "id",
]

# browser catalog[] query key -> JSON API param name (others keep their name sans "[]")
KEY_ALIASES = {"catalog": "catalog_ids"}


def url_to_api_params(catalog_url: str) -> dict[str, str]:
    """Turn a browser catalog URL into JSON-API query params.

    Browser uses repeated ``foo[]=1&foo[]=2``; the API takes a single comma-joined
    ``foo=1,2``. ``catalog[]`` maps to ``catalog_ids``; ``page``/``per_page`` are dropped
    here (paging is handled by the caller).
    """
    query = urllib.parse.urlparse(catalog_url).query
    collected: dict[str, list[str]] = {}
    for raw_key, values in urllib.parse.parse_qs(query).items():
        key = raw_key[:-2] if raw_key.endswith("[]") else raw_key
        if key in ("page", "per_page"):
            continue
        key = KEY_ALIASES.get(key, key)
        collected.setdefault(key, []).extend(values)
    return {k: ",".join(v) for k, v in collected.items()}


async def fetch_catalog_items(
    params: dict[str, str],
    pages: int = 10,
    per_page: int = 96,
    cookies: dict[str, str] | None = None,
) -> list[dict]:
    """Page through the catalog API and return the raw item dicts (deduped by id)."""
    if cookies is None:
        cookies = load_cookies()

    headers = {"User-Agent": USER_AGENT, "Accept": "application/json, text/plain, */*"}
    items: dict[int, dict] = {}

    async with httpx.AsyncClient(
        headers=headers, cookies=cookies, follow_redirects=True, timeout=30
    ) as client:
        for page in range(1, pages + 1):
            resp = await client.get(
                CATALOG_ITEMS_URL, params={**params, "page": page, "per_page": per_page}
            )
            resp.raise_for_status()
            batch = resp.json().get("items", [])
            for it in batch:
                items[it["id"]] = it
            print(f"-> page {page}: {len(batch)} items ({len(items)} unique)")
            if len(batch) < per_page:
                break

    return list(items.values())


def listing_created(item: dict) -> str:
    """Listing creation time as ``YYYY-MM-DD HH:MM:SS`` (UTC).

    The catalog API carries no ``created_at`` on items; the closest proxy is the main
    photo's upload timestamp (``photo.high_resolution.timestamp``), a full Unix time —
    i.e. when the listing's photo was uploaded. Empty string if absent.
    """
    ts = ((item.get("photo") or {}).get("high_resolution") or {}).get("timestamp")
    if not ts:
        return ""
    return datetime.datetime.fromtimestamp(ts, datetime.UTC).strftime("%Y-%m-%d %H:%M:%S")


def summarise(item: dict) -> dict:
    """Pull the fields we care about out of a raw API item."""
    price = item.get("total_item_price") or item.get("price") or {}
    return {
        "favourite_count": item.get("favourite_count", 0),
        "created": listing_created(item),
        "price": f"{price.get('amount', '?')} {price.get('currency_code', '')}".strip(),
        "size": item.get("size_title", ""),
        "brand": item.get("brand_title", ""),
        "title": item.get("title", ""),
        "url": item.get("url", ""),
        "id": item["id"],
    }


async def top_liked(catalog_url: str, pages: int = 10) -> list[dict]:
    """All items for a catalog URL, summarised and sorted by likes descending."""
    params = url_to_api_params(catalog_url)
    print(f"API params: {params}")
    raw = await fetch_catalog_items(params, pages=pages)
    return sorted(
        (summarise(i) for i in raw),
        key=lambda r: r["favourite_count"],
        reverse=True,
    )


def output_path(catalog_url: str) -> Path:
    """media/vinted_top_liked_<key=val_…>.csv derived from the URL's filter params."""
    params = url_to_api_params(catalog_url)
    slug = "_".join(f"{k}{v}" for k, v in sorted(params.items()) if k != "order") or "all"
    return MEDIA_DIR / f"vinted_top_liked_{slug}.csv"


async def main() -> None:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("url", help="a vinted.pl/catalog listing URL")
    ap.add_argument("--pages", type=int, default=10, help="catalog pages to scan (default 10)")
    ap.add_argument("--limit", type=int, default=30, help="top items to print (default 30)")
    args = ap.parse_args()

    rows = await top_liked(args.url, pages=args.pages)

    MEDIA_DIR.mkdir(parents=True, exist_ok=True)
    out = output_path(args.url)
    petl.tocsv(petl.fromdicts(rows, header=CSV_HEADER), str(out), encoding="utf-8")
    print(f"\nwrote {len(rows)} rows (most-liked first) -> {out}")

    header = f"{'likes':>5s} | {'created (UTC)':19s} | {'price':>12s} | {'size':6s} | title"
    print("\n" + header)
    print("-" * len(header))
    for r in rows[: args.limit]:
        print(
            f"{r['favourite_count']:>5d} | {r['created']:19s} | "
            f"{r['price']:>12s} | {r['size']:6.6s} | {r['title'][:40]}"
        )
        print(f"        {r['url']}")


if __name__ == "__main__":
    asyncio.run(main())
