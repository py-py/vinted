from __future__ import annotations

import argparse
import asyncio
from datetime import UTC
from datetime import datetime

from rich.console import Console
from rich.table import Table

from ..storage import FirestoreStore
from .api import MEMBER_URL
from .models import ItemState
from .sync import sync_wardrobe


async def main() -> None:
    parser = argparse.ArgumentParser(prog="python -m vinted.wardrobe")
    parser.add_argument(
        "user_id",
        nargs="?",
        help="Member id (from /member/{id}), ALL for every tracked member; omit to list them",
    )
    parser.add_argument(
        "--sales",
        action="store_true",
        help="show sold items (of one member, or all when no id / ALL) instead of syncing",
    )
    args = parser.parse_args()

    if args.sales:
        list_sales(FirestoreStore(), args.user_id)
        return

    if args.user_id is None:
        list_members(FirestoreStore())
        return

    store = FirestoreStore()
    if args.user_id.upper() == "ALL":
        members = store.load_wardrobe_members()
        for user_id, doc in sorted(members.items()):
            login = (doc.get("api") or {}).get("login", "")
            print(f"=> {login} [{user_id}]")
            await sync_member(user_id, store)
    else:
        await sync_member(args.user_id, store)


async def sync_member(user_id: str, store: FirestoreStore) -> None:
    result = await sync_wardrobe(user_id, store)
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


def list_sales(store: FirestoreStore, user_id: str | None) -> None:
    members = store.load_wardrobe_members()
    user_ids = sorted(members) if user_id is None or user_id.upper() == "ALL" else [user_id]

    sold = [
        (uid, item_id, doc)
        for uid in user_ids
        for item_id, doc in store.load_wardrobe_items(uid).items()
        if doc.get("state") == ItemState.SOLD
    ]
    sold.sort(key=lambda row: row[2].get("gone_at") or datetime.min.replace(tzinfo=UTC))

    table = Table("ID", "Username", "Sold")
    table.add_column("Title", overflow="fold")
    table.add_column("Price", justify="right")
    table.add_column("URL", overflow="fold")
    for uid, item_id, doc in sold:
        login = ((members.get(uid) or {}).get("api") or {}).get("login", "")
        gone_at = doc.get("gone_at")
        sold_at = gone_at.strftime("%Y-%m-%d %H:%M") if gone_at else ""
        api = doc.get("api") or {}
        price = api.get("price") or {}
        amount = price.get("amount")
        price_str = f"{float(amount):.2f} {price.get('currency_code', '')}" if amount else ""
        title = api.get("title", "")
        table.add_row(str(item_id), login, sold_at, title, price_str, api.get("url", ""))
    Console().print(table)


if __name__ == "__main__":
    asyncio.run(main())
