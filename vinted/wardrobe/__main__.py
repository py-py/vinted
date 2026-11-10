from __future__ import annotations

import argparse
import asyncio

from rich.console import Console
from rich.table import Table

from ..storage import FirestoreStore
from .api import MEMBER_URL
from .sync import sync_wardrobe


async def main() -> None:
    parser = argparse.ArgumentParser(prog="python -m vinted.wardrobe")
    parser.add_argument(
        "user_id",
        nargs="?",
        help="Vinted member id (from /member/{id}); omit to list tracked members",
    )
    args = parser.parse_args()

    if args.user_id is None:
        list_members(FirestoreStore())
        return

    result = await sync_wardrobe(args.user_id, FirestoreStore())
    print(f"-> New: {len(result.new)}")
    for item_id in result.new:
        print(f"   + {item_id}")
    print(f"-> State changes: {len(result.changes)}")
    for item_id, (old, new) in result.changes.items():
        print(f"   {item_id}: {old} -> {new}")


def list_members(store: FirestoreStore) -> None:
    table = Table("ID", "Username", "URL")
    for user_id, doc in sorted(store.load_wardrobe_members().items()):
        login = (doc.get("api") or {}).get("login", "")
        table.add_row(user_id, login, MEMBER_URL.format(user_id=user_id))
    Console().print(table)


if __name__ == "__main__":
    asyncio.run(main())
