from __future__ import annotations

import asyncio
import json
import sys

from .api import fetch_wardrobe
from .api import parse_item


async def main() -> None:
    user_id = sys.argv[1] if len(sys.argv) > 1 else None
    if user_id is None:
        raise SystemExit("Usage: python -m vinted.wardrobe <user_id>")

    items = await fetch_wardrobe(user_id)
    result = [parse_item(item) for item in items]
    print(json.dumps(result, indent=2, ensure_ascii=False))


if __name__ == "__main__":
    asyncio.run(main())
