from __future__ import annotations

import argparse
import asyncio
import json

from ..firestore import FirestoreStore
from .api import fetch_orders


async def main() -> None:
    parser = argparse.ArgumentParser(prog="python -m vinted.orders")
    parser.add_argument("max_pages", nargs="?", type=int, default=None)
    parser.add_argument("--save", action="store_true", help="write orders to Firestore")
    args = parser.parse_args()

    orders = await fetch_orders(max_pages=args.max_pages)

    if args.save:
        store = FirestoreStore()
        store.save_orders(orders)
    else:
        print(json.dumps([o.model_dump() for o in orders], indent=2, ensure_ascii=False))


if __name__ == "__main__":
    asyncio.run(main())
