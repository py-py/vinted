from __future__ import annotations

import asyncio
import random
import re
from itertools import islice

import httpx


def parse_item_id(url: str) -> str | None:
    """
    Extract the numeric item ID from a Vinted item URL.
    URL: https://www.vinted.pl/items/8142652778-sjezdove-lyze-150-cm-head?referrer=catalog
    """
    match = re.search(r"/items/(\d+)", url)
    return match.group(1) if match else None


def chunked(item, n):
    """Yield successive n-sized chunks from any iterable item."""
    iterable = iter(item)
    while True:
        chunk = list(islice(iterable, n))
        if not chunk:
            return
        yield chunk


async def get_with_backoff(
    client: httpx.AsyncClient,
    url: str,
    *,
    params: dict | None = None,
    max_retries: int = 5,
) -> httpx.Response:
    """GET with exponential backoff on 429."""
    backoff = 2.0
    resp: httpx.Response | None = None
    for attempt in range(max_retries):
        resp = await client.get(url, params=params)
        if resp.status_code == 429:
            retry_after = float(resp.headers.get("Retry-After", backoff))
            sleep = retry_after + random.uniform(0, 1)
            print(f"-> 429, sleeping {sleep:.1f}s (attempt {attempt + 1}/{max_retries})")
            await asyncio.sleep(sleep)
            backoff *= 2
            continue
        return resp
    assert resp is not None
    return resp
