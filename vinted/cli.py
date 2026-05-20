from __future__ import annotations

import argparse
import asyncio
import json

from .core.logging import configure_logging
from .services.pipeline import analyze_item


def main() -> None:
    """Run the full pipeline for a single item from the command line.

    Example:
        python -m vinted.cli 8142652778 2683 --force
    """
    configure_logging()

    parser = argparse.ArgumentParser(prog="vinted")
    parser.add_argument("product_id")
    parser.add_argument("catalog_id", nargs="?", default=None)
    parser.add_argument("--force", action="store_true")
    args = parser.parse_args()

    result = asyncio.run(
        analyze_item(args.product_id, args.catalog_id, source="cli", force=args.force)
    )
    print(json.dumps(result, indent=2, ensure_ascii=False))


if __name__ == "__main__":
    main()
