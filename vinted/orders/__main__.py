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
    parser.add_argument(
        "--force",
        action="store_true",
        help="with --save: re-fetch and overwrite orders already in Firestore",
    )
    args = parser.parse_args()

    store: FirestoreStore | None = None
    skip_ids: set[int] = set()
    if args.save and not args.force:
        store = FirestoreStore()
        skip_ids = store.existing_transaction_ids()
        print(f"-> {len(skip_ids)} purchases already in Firestore, will skip")

    orders = await fetch_orders(max_pages=args.max_pages, skip_transaction_ids=skip_ids)

    if args.save:
        if not orders:
            print("-> No new purchases to save")
            return
        (store or FirestoreStore()).save_orders(orders)
    else:
        print(json.dumps([o.model_dump() for o in orders], indent=2, ensure_ascii=False))


if __name__ == "__main__":
    asyncio.run(main())
