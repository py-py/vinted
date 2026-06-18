#!/usr/bin/env python3
"""Dump a newbalance.pl category listing (models + prices) to CSV.

newbalance.pl is a Next.js storefront. The HTML only ever contains page 1 of a
listing (URL params like ?page=2 are ignored server-side), so the catalog is read
entirely from the site's own GraphQL API:

  1. resolve the slug (full path, e.g. 'meskie' or 'meskie/obuwie') to an internal
     (objectType, objectId) via the `urlResolver` query;
  2. page through the GraphQL `products` query until `lastPage`, deduping by item id.

For the sale/promo listing (filters), use scrape_promocja.py instead.

Usage:
    python scrape_nb.py                       # default: meskie, sorted by price desc
    python scrape_nb.py --slug damskie
    python scrape_nb.py --slug meskie/obuwie
    python scrape_nb.py --slug meskie --sort -gross_sell_price --out out.csv

No auth needed. Only stdlib.
"""

import argparse
import csv
import json
import sys
import urllib.request
from pathlib import Path

UA = "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36"
SITE = "https://newbalance.pl"
GRAPHQL = "https://aplikacja.newbalance.pl/api/graphql/frontend"
# project_root/media — this script lives in <root>/scripts/new_balance/
MEDIA_DIR = Path(__file__).resolve().parents[2] / "media"

PRODUCTS_QUERY = (
    "query($t:ListingType!,$id:ID!,$page:Int!,$limit:Int,$sort:String){"
    "products(id:$id,type:$t,page:$page,limit:$limit,sort:$sort){"
    "items{id name niceUrl prices{sellPrice{gross} listPrice{gross} basePrice{gross}}}"
    "pagination{itemsCount lastPage}}}"
)


def graphql(query, variables):
    body = json.dumps({"query": query, "variables": variables}).encode()
    req = urllib.request.Request(
        GRAPHQL,
        data=body,
        headers={"Content-Type": "application/json", "User-Agent": UA},
    )
    resp = json.loads(urllib.request.urlopen(req, timeout=30).read())
    if resp.get("errors"):
        sys.exit("GraphQL errors: " + json.dumps(resp["errors"], ensure_ascii=False))
    return resp["data"]


def resolve_listing(slug):
    """Resolve a slug (full path) to (listingType, objectId) via the site's urlResolver.
    objectType (category/flag/producer/...) maps to the ListingType enum as from_<type>."""
    q = "query($slug:String!){urlResolver(slug:$slug){objectType objectId isRedirect redirectTo}}"
    ent = graphql(q, {"slug": slug})["urlResolver"]
    if not ent or not ent.get("objectId"):
        sys.exit(f"could not resolve slug={slug!r}")
    if ent.get("isRedirect"):
        print(f"note: {slug} redirects to {ent.get('redirectTo')}", file=sys.stderr)
    return f"from_{ent['objectType']}", str(ent["objectId"])


def scrape(slug, sort, limit=96):
    listing_type, obj_id = resolve_listing(slug)
    print(f"slug={slug} -> {listing_type} id={obj_id}", file=sys.stderr)
    rows, seen, page = [], set(), 1
    while True:
        data = graphql(
            PRODUCTS_QUERY,
            {"t": listing_type, "id": obj_id, "page": page, "limit": limit, "sort": sort},
        )["products"]
        items = data["items"]
        for it in items:
            if it["id"] in seen:
                continue
            seen.add(it["id"])
            pr = it["prices"]
            sell = (pr.get("sellPrice") or {}).get("gross")
            base = (pr.get("listPrice") or pr.get("basePrice") or {}).get("gross")
            on_sale = base and sell and base > sell
            before = base if on_sale else None
            # same formula the site uses: round((base - sell) / base * 100)
            discount = round((1 - sell / base) * 100) if on_sale else None
            rows.append((it["name"], sell, before, discount, f"{SITE}/{it['niceUrl']}"))
        last = data["pagination"]["lastPage"]
        print(f"page {page}/{last} — {len(rows)} unique", file=sys.stderr)
        if page >= last or not items:
            break
        page += 1
    return rows


def main():
    ap = argparse.ArgumentParser(
        description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter
    )
    ap.add_argument("--slug", default="meskie", help="listing slug (e.g. meskie, meskie/obuwie)")
    ap.add_argument(
        "--sort", default="-gross_sell_price", help="sort key (default: price descending)"
    )
    args = ap.parse_args()

    rows = scrape(args.slug, args.sort)
    MEDIA_DIR.mkdir(parents=True, exist_ok=True)
    out = MEDIA_DIR / f"newbalance_{args.slug.replace('/', '_')}.csv"
    with open(out, "w", newline="", encoding="utf-8") as f:
        w = csv.writer(f)
        w.writerow(["model", "price_PLN", "price_before_discount_PLN", "discount_%", "url"])
        w.writerows(rows)
    print(f"wrote {len(rows)} rows -> {out}", file=sys.stderr)


if __name__ == "__main__":
    main()
