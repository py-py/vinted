from __future__ import annotations

import argparse
import asyncio
import json

from ..firestore import FirestoreStore
from .api import fetch_orders
from .photos import backfill_photos


async def main() -> None:
    parser = argparse.ArgumentParser(prog="python -m vinted.account.orders")
    parser.add_argument(
        "--max-pages",
        type=int,
        default=None,
        help="limit pages of my_orders to fetch (5 orders per page)",
    )
    parser.add_argument(
        "--no-save",
        action="store_true",
        help="print orders as JSON instead of saving to Firestore + GCS",
    )
    parser.add_argument(
        "--force",
        action="store_true",
        help="re-fetch and overwrite orders already in Firestore",
    )
    parser.add_argument(
        "--backfill-photos",
        action="store_true",
        help="upload missing photos to GCS for items already in Firestore (skips Vinted API)",
    )
    args = parser.parse_args()

    if args.no_save:
        orders = await fetch_orders(max_pages=args.max_pages)
        print(json.dumps([o.model_dump() for o in orders], indent=2, ensure_ascii=False))
        return

    store = FirestoreStore()

    if args.backfill_photos:
        items = store.list_item_photos()
        print(f"-> {len(items)} items with photos in Firestore")
        await backfill_photos(items)
        return

    store = FirestoreStore()
    skip_ids: set[int] = set() if args.force else store.existing_transaction_ids()
    print(f"-> {len(skip_ids)} purchases already in Firestore, will skip")

    orders = await fetch_orders(max_pages=args.max_pages, skip_transaction_ids=skip_ids)
    if not orders:
        print("-> No new purchases to save")
        return

    store.save_orders(orders)
    photos: list = [(item.id, item.photo_urls) for order in orders for item in order.items]
    await backfill_photos(photos)


if __name__ == "__main__":
    asyncio.run(main())
