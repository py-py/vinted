#!/usr/bin/env python3
"""Dump the newbalance.pl sale listing (/promocja) with filters to CSV.

The sale page is a `flag` listing (promocja -> flag id 1), normally narrowed with
filters (`f.<id>=<value>` in the URL, e.g. `f.69=13026` = category Obuwie). Those
filters are passed straight through as the GraphQL `filters` input. See nb_base.py
for how it works.

Usage:
    # just paste the sale URL — slug, sort and f.* filters are parsed out of it:
    python scrape_promotions.py --url "https://newbalance.pl/promocja?sort=gross_sell_price&f.69=13026&f.95=Obuwie"

The CSV is written to the project's media/ folder. No auth needed. Only stdlib.
"""

import argparse

from nb_base import NBListingScraper


class PromoScraper(NBListingScraper):
    """The sale listing — a flag listing, normally filtered, sorted by price ascending."""

    DEFAULT_SORT = "gross_sell_price"


def main():
    ap = argparse.ArgumentParser(
        description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter
    )
    ap.add_argument(
        "--url", required=True, help="full sale URL; slug, sort and f.* filters are parsed from it"
    )
    args = ap.parse_args()

    PromoScraper.from_url(args.url).run()


if __name__ == "__main__":
    main()
