from __future__ import annotations

import argparse
import asyncio
import json

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
    args = parser.parse_args()

    sales = await fetch_sales(status=args.status, max_pages=args.max_pages)
    print(json.dumps([s.model_dump() for s in sales], indent=2, ensure_ascii=False))


if __name__ == "__main__":
    asyncio.run(main())
