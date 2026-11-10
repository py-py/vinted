from __future__ import annotations

import re
from itertools import islice


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
