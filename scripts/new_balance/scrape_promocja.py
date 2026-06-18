#!/usr/bin/env python3
"""Dump the newbalance.pl sale listing (/promocja) with filters to CSV.

Same GraphQL approach as scrape_nb.py, but the sale page is a `flag` listing
(promocja -> flag id 1) and is normally narrowed with filters
(`f.<id>=<value>` in the URL, e.g. `f.69=13026` = category Obuwie). Those filters
are passed straight through as the GraphQL `filters` input.

Usage:
    # just paste the sale URL — slug, sort and f.* filters are parsed out of it:
    python scrape_promocja.py --url "https://newbalance.pl/promocja?sort=gross_sell_price&f.69=13026&f.95=Obuwie"

No auth needed. Only stdlib.
"""

import argparse
import csv
import json
import sys
import urllib.parse
import urllib.request
from pathlib import Path

UA = "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36"
SITE = "https://newbalance.pl"
GRAPHQL = "https://aplikacja.newbalance.pl/api/graphql/frontend"
# project_root/media — this script lives in <root>/scripts/new_balance/
MEDIA_DIR = Path(__file__).resolve().parents[2] / "media"

PRODUCTS_QUERY = (
    "query($t:ListingType!,$id:ID!,$page:Int!,$limit:Int,$sort:String,$f:FiltersInput){"
    "products(id:$id,type:$t,page:$page,limit:$limit,sort:$sort,filters:$f){"
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
    """Resolve a slug to (listingType, objectId) via the site's urlResolver.
    objectType (flag/category/...) maps to the ListingType enum as from_<type>."""
    q = "query($slug:String!){urlResolver(slug:$slug){objectType objectId isRedirect redirectTo}}"
    ent = graphql(q, {"slug": slug})["urlResolver"]
    if not ent or not ent.get("objectId"):
        sys.exit(f"could not resolve slug={slug!r}")
    return f"from_{ent['objectType']}", str(ent["objectId"])


def filters_input(filters):
    """Turn {attr_id: [values]} into a GraphQL FiltersInput, or None if empty.
    A single value becomes {key,value}; several become {key,values:[...]}."""
    fields = []
    for key, vals in filters.items():
        if len(vals) == 1:
            fields.append({"key": key, "value": vals[0]})
        else:
            fields.append({"key": key, "values": vals})
    return {"fields": fields} if fields else None


def scrape(slug, sort, filters, limit=96):
    listing_type, obj_id = resolve_listing(slug)
    f_input = filters_input(filters)
    print(f"slug={slug} -> {listing_type} id={obj_id} filters={filters or '{}'}", file=sys.stderr)
    rows, seen, page = [], set(), 1
    while True:
        data = graphql(
            PRODUCTS_QUERY,
            {
                "t": listing_type,
                "id": obj_id,
                "page": page,
                "limit": limit,
                "sort": sort,
                "f": f_input,
            },
        )["products"]
        items = data["items"]
        for it in items:
            if it["id"] in seen:
                continue
            seen.add(it["id"])
            pr = it["prices"]
            sell = (pr.get("sellPrice") or {}).get("gross")
            # on the sale page the pre-discount price lives in basePrice, not listPrice
            base = (pr.get("listPrice") or pr.get("basePrice") or {}).get("gross")
            on_sale = base and sell and base > sell
            before = base if on_sale else None
            # GraphQL has no discount-% field on products, so derive it from the prices
            discount = round((1 - sell / base) * 100) if on_sale else None
            rows.append((it["name"], sell, before, discount, f"{SITE}/{it['niceUrl']}"))
        last = data["pagination"]["lastPage"]
        print(f"page {page}/{last} — {len(rows)} unique", file=sys.stderr)
        if page >= last or not items:
            break
        page += 1
    return rows


def parse_url(url):
    """Parse a /promocja URL into (slug, sort, filters)."""
    u = urllib.parse.urlparse(url)
    slug = u.path.strip("/")
    sort = None
    filters = {}
    for key, vals in urllib.parse.parse_qs(u.query).items():
        if key == "sort":
            sort = vals[0]
        elif key.startswith("f."):
            filters[key[2:]] = vals
    return slug, sort, filters


def main():
    ap = argparse.ArgumentParser(
        description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter
    )
    ap.add_argument(
        "--url", required=True, help="full sale URL; slug, sort and f.* filters are parsed from it"
    )
    args = ap.parse_args()

    slug, sort, filters = parse_url(args.url)
    sort = sort or "gross_sell_price"

    rows = scrape(slug, sort, filters)
    MEDIA_DIR.mkdir(parents=True, exist_ok=True)
    out = MEDIA_DIR / f"newbalance_{slug.replace('/', '_')}.csv"
    with open(out, "w", newline="", encoding="utf-8") as f:
        w = csv.writer(f)
        w.writerow(["model", "price_PLN", "price_before_discount_PLN", "discount_%", "url"])
        w.writerows(rows)
    print(f"wrote {len(rows)} rows -> {out}", file=sys.stderr)


if __name__ == "__main__":
    main()
