from __future__ import annotations

import argparse
import asyncio
import json

from ..storage import FirestoreStore
from .api import fetch_wardrobe
from .api import listed_at
from .api import parse_item
from .sync import sync_wardrobe


async def main() -> None:
    parser = argparse.ArgumentParser(prog="python -m vinted.wardrobe")
    parser.add_argument("user_id", help="Vinted member id (from /member/{id})")
    parser.add_argument(
        "--no-save",
        action="store_true",
        help="print the fetched items as JSON instead of syncing to Firestore",
    )
    args = parser.parse_args()

    if args.no_save:
        items = await fetch_wardrobe(args.user_id)
        result = [{"api": parse_item(item), "listed_at": listed_at(item)} for item in items]
        print(json.dumps(result, indent=2, ensure_ascii=False, default=str))
        return

    result = await sync_wardrobe(args.user_id, FirestoreStore())
    print(f"-> New: {len(result.new)}")
    for item_id in result.new:
        print(f"   + {item_id}")
    print(f"-> State changes: {len(result.changes)}")
    for item_id, (old, new) in result.changes.items():
        print(f"   {item_id}: {old} -> {new}")


if __name__ == "__main__":
    asyncio.run(main())
