from __future__ import annotations

import argparse
import asyncio
import json

from ...storage import FirestoreStore
from ..purchases.photos import backfill_photos
from .api import fetch_sales


async def main() -> None:
    parser = argparse.ArgumentParser(prog="python -m vinted.account.sales")
    parser.add_argument(
        "--status",
        default="completed",
        help="escrow order status to fetch (default: completed)",
    )
    parser.add_argument(
        "--max-pages",
        type=int,
        default=None,
        help="limit pages of sold orders to fetch (100 orders per page)",
    )
    parser.add_argument(
        "--no-save",
        action="store_true",
        help="print sales as JSON instead of saving to Firestore + GCS",
    )
    parser.add_argument(
        "--force",
        action="store_true",
        help="re-fetch and merge sales already in Firestore",
    )
    parser.add_argument(
        "--backfill-photos",
        action="store_true",
        help="upload missing photos to GCS for sale items already in Firestore (skips Vinted API)",
    )
    args = parser.parse_args()

    if args.no_save:
        sales = await fetch_sales(status=args.status, max_pages=args.max_pages)
        print(json.dumps([s.model_dump() for s in sales], indent=2, ensure_ascii=False))
        return

    store = FirestoreStore()

    if args.backfill_photos:
        items = store.list_sale_item_photos()
        print(f"-> {len(items)} sale items with photos in Firestore")
        await backfill_photos(items)
        return

    skip_ids: set[int] = set() if args.force else store.existing_sale_ids()
    print(f"-> {len(skip_ids)} sales already in Firestore, will skip")

    sales = await fetch_sales(
        status=args.status, max_pages=args.max_pages, skip_transaction_ids=skip_ids
    )
    if not sales:
        print("-> No new sales to save")
        return

    store.save_sales(sales)
    photos: list = [(item.id, item.photo_urls) for sale in sales for item in sale.items]
    await backfill_photos(photos)


if __name__ == "__main__":
    asyncio.run(main())
