#!/usr/bin/env python3
"""Dump a newbalance.pl category listing (models + prices) to CSV.

A normal category listing, e.g. 'meskie' or 'meskie/obuwie'. For the sale/promo
listing (filters), use scrape_promotions.py instead. See nb_base.py for how it works.

Usage:
    # just paste a listing URL — slug and sort are parsed out of it:
    python scrape_sales.py --url "https://newbalance.pl/meskie/obuwie?sort=-gross_sell_price"

The CSV is written to the project's media/ folder. No auth needed. Only stdlib.
"""

import argparse

from nb_base import NBListingScraper


class CategoryScraper(NBListingScraper):
    """A normal category listing (no filters), sorted by price descending."""

    DEFAULT_SORT = "-gross_sell_price"


def main():
    ap = argparse.ArgumentParser(
        description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter
    )
    ap.add_argument(
        "--url", required=True, help="full listing URL; slug and sort are parsed from it"
    )
    args = ap.parse_args()

    CategoryScraper.from_url(args.url).run()


if __name__ == "__main__":
    main()
