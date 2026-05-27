from __future__ import annotations

import asyncio
import json
import sys

from .api import fetch_orders


async def main() -> None:
    max_pages = int(sys.argv[1]) if len(sys.argv) > 1 else None
    orders = await fetch_orders(max_pages=max_pages)
    print(json.dumps([o.model_dump() for o in orders], indent=2, ensure_ascii=False))


if __name__ == "__main__":
    asyncio.run(main())
