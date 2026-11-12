"""State of a single item, read from its public page (anonymous).

The page embeds Next.js flight data as JSON-escaped strings; markers verified
on 2026-11-10 (see PLAN.md):

- sold:     plugin `buyer_item_status` with title "Sprzedane"
- reserved: plugin `buyer_item_status` with title "Zarezerwowane", `is_reserved: true`
- active:   no status plugin, `availability: InStock`
- deleted:  HTTP 404

`can_buy` is not a signal — it is true on reserved items.
"""

from __future__ import annotations

import re

import httpx

from ..constants import PRODUCT_URL
from .models import ItemState

STATUS_PLUGIN_RE = re.compile(r'\{"data":\{([^{}]*)\}[^{}]*?"name":"buyer_item_status"')
TITLE_RE = re.compile(r'"title":"([^"]*)"')
RESERVED_RE = re.compile(r'"is_reserved":true')
IN_STOCK_RE = re.compile(r'"availability":"(?:https?://schema\.org/)?InStock"')

STATUS_TITLES = {
    "Sprzedane": ItemState.SOLD,
    "Zarezerwowane": ItemState.RESERVED,
}


def parse_item_state(html: str) -> ItemState:
    """Item state from the HTML of a 200 item page."""
    text = html.replace('\\"', '"')
    if plugin := STATUS_PLUGIN_RE.search(text):
        title = TITLE_RE.search(plugin.group(1))
        if title and title.group(1) in STATUS_TITLES:
            return STATUS_TITLES[title.group(1)]
    if RESERVED_RE.search(text):
        return ItemState.RESERVED
    if IN_STOCK_RE.search(text):
        return ItemState.ACTIVE
    return ItemState.UNKNOWN


async def check_item_state(client: httpx.AsyncClient, item_id: int | str) -> ItemState:
    """Fetch the item page and classify it. Raises on errors other than 404."""
    resp = await client.get(PRODUCT_URL.format(product_id=item_id))
    if resp.status_code == 404:
        return ItemState.DELETED
    resp.raise_for_status()
    return parse_item_state(resp.text)
