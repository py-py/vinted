from __future__ import annotations

import re


def parse_item_id(url: str) -> str | None:
    """
    Extract the numeric item ID from a Vinted item URL.
    URL: https://www.vinted.pl/items/8142652778-sjezdove-lyze-150-cm-head?referrer=catalog
    """
    match = re.search(r"/items/(\d+)", url)
    return match.group(1) if match else None


def parse_member_id(url: str) -> int | None:
    """
    Extract the numeric seller ID from a Vinted member URL.
    URL: https://www.vinted.pl/member/12345-some-username
    """
    match = re.search(r"/member/(\d+)", url)
    return int(match.group(1)) if match else None
