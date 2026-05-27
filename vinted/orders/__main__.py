from __future__ import annotations

import argparse
import asyncio
import json

from ..firestore import FirestoreStore
from .api import fetch_orders
from .photos import backfill_photos


async def main() -> None:
    parser = argparse.ArgumentParser(prog="python -m vinted.orders")
    parser.add_argument("max_pages", nargs="?", type=int, default=None)
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

    if args.backfill_photos:
        items = FirestoreStore().list_item_photos()
        print(f"-> {len(items)} items with photos in Firestore")
        await backfill_photos(items)
        return

    store: FirestoreStore | None = None
    skip_ids: set[int] = set()
    if not args.no_save and not args.force:
        store = FirestoreStore()
        skip_ids = store.existing_transaction_ids()
        print(f"-> {len(skip_ids)} purchases already in Firestore, will skip")

    orders = await fetch_orders(max_pages=args.max_pages, skip_transaction_ids=skip_ids)

    if args.no_save:
        print(json.dumps([o.model_dump() for o in orders], indent=2, ensure_ascii=False))
        return

    if not orders:
        print("-> No new purchases to save")
        return
    (store or FirestoreStore()).save_orders(orders)
    await backfill_photos([(it.id, it.photo_urls) for o in orders for it in o.items])


if __name__ == "__main__":
    asyncio.run(main())
