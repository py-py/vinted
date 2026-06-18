#!/usr/bin/env python3
"""Shared base for the newbalance.pl listing scrapers.

newbalance.pl is a Next.js storefront whose HTML only ever contains page 1 of a
listing (URL params like ?page=2 are ignored server-side), so the catalog is read
entirely from the site's own GraphQL API:

  1. resolve a slug (full path, e.g. 'meskie/obuwie' or 'promocja') to an internal
     (objectType, objectId) via the `urlResolver` query;
  2. page through the `products` query until `lastPage`, deduping by item id.

Subclass `NBListingScraper` for a concrete listing kind — see scrape_sales.py
(categories) and scrape_promotions.py (the sale flag, with filters).
"""

import csv
import json
import sys
import urllib.parse
import urllib.request
from pathlib import Path

UA = "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36"
SITE = "https://newbalance.pl"
GRAPHQL = "https://aplikacja.newbalance.pl/api/graphql/frontend"
# project_root/media — this file lives in <root>/scripts/new_balance/
MEDIA_DIR = Path(__file__).resolve().parents[2] / "media"

PRODUCTS_QUERY = (
    "query($t:ListingType!,$id:ID!,$page:Int!,$limit:Int,$sort:String,$f:FiltersInput){"
    "products(id:$id,type:$t,page:$page,limit:$limit,sort:$sort,filters:$f){"
    "items{id name niceUrl categoryPath{name} "
    "prices{sellPrice{gross} listPrice{gross} basePrice{gross} omnibusPrice{gross}}}"
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


class NBListingScraper:
    """Resolve a slug, page through its products, and write the rows to media/."""

    HEADER = [
        "model",
        "category",
        "price_PLN",
        "price_before_discount_PLN",
        "lowest_30d_PLN",
        "discount_%",
        "is_best_30d",
        "vs_lowest_30d_%",
        "url",
    ]
    DEFAULT_SORT = "-gross_sell_price"

    def __init__(self, slug, sort=None, filters=None, limit=96):
        self.slug = slug
        self.sort = sort or self.DEFAULT_SORT
        self.filters = filters or {}
        self.limit = limit

    @classmethod
    def from_url(cls, url):
        """Build a scraper from a listing URL, parsing the slug (path), sort and
        f.* filters from the query string."""
        u = urllib.parse.urlparse(url)
        slug = u.path.strip("/")
        sort = None
        filters = {}
        for key, vals in urllib.parse.parse_qs(u.query).items():
            if key == "sort":
                sort = vals[0]
            elif key.startswith("f."):
                filters[key[2:]] = vals
        return cls(slug, sort, filters)

    def resolve(self):
        """Resolve the slug to (listingType, objectId). objectType (category/flag/...)
        maps to the ListingType enum as from_<type>."""
        q = (
            "query($slug:String!)"
            "{urlResolver(slug:$slug){objectType objectId isRedirect redirectTo}}"
        )
        ent = graphql(q, {"slug": self.slug})["urlResolver"]
        if not ent or not ent.get("objectId"):
            sys.exit(f"could not resolve slug={self.slug!r}")
        if ent.get("isRedirect"):
            print(f"note: {self.slug} redirects to {ent.get('redirectTo')}", file=sys.stderr)
        return f"from_{ent['objectType']}", str(ent["objectId"])

    def filters_input(self):
        """Turn {attr_id: [values]} into a GraphQL FiltersInput, or None if empty.
        A single value becomes {key,value}; several become {key,values:[...]}."""
        fields = []
        for key, vals in self.filters.items():
            vals = vals if isinstance(vals, list) else [vals]
            if len(vals) == 1:
                fields.append({"key": key, "value": vals[0]})
            else:
                fields.append({"key": key, "values": vals})
        return {"fields": fields} if fields else None

    @staticmethod
    def row(it):
        """Map one product item to a CSV row matching HEADER."""
        pr = it["prices"]
        sell = (pr.get("sellPrice") or {}).get("gross")
        # the pre-discount price ("Cena pierwsza") lives in listPrice or basePrice
        base = (pr.get("listPrice") or pr.get("basePrice") or {}).get("gross")
        # omnibusPrice = "Najniższa cena z 30 dni przed obniżką" (EU Omnibus directive)
        lowest_30d = (pr.get("omnibusPrice") or {}).get("gross")
        on_sale = base and sell and base > sell
        before = base if on_sale else None
        # GraphQL has no discount-% field, so derive it the way the site renders its
        # badge: round((base - sell) / base * 100)
        discount = round((1 - sell / base) * 100) if on_sale else None
        # is today's price the best of the last 30 days, and by how much? compare to
        # omnibusPrice: vs_lowest < 0 means cheaper than the recent low (a real low).
        is_best_30d = vs_lowest = None
        if sell and lowest_30d:
            is_best_30d = sell <= lowest_30d
            vs_lowest = round((sell / lowest_30d - 1) * 100)
        category = " / ".join(c["name"] for c in (it.get("categoryPath") or []))
        return (
            it["name"],
            category,
            sell,
            before,
            lowest_30d,
            discount,
            is_best_30d,
            vs_lowest,
            f"{SITE}/{it['niceUrl']}",
        )

    def scrape(self):
        listing_type, obj_id = self.resolve()
        f_input = self.filters_input()
        print(
            f"slug={self.slug} -> {listing_type} id={obj_id} filters={self.filters or '{}'}",
            file=sys.stderr,
        )
        rows, seen, page = [], set(), 1
        while True:
            data = graphql(
                PRODUCTS_QUERY,
                {
                    "t": listing_type,
                    "id": obj_id,
                    "page": page,
                    "limit": self.limit,
                    "sort": self.sort,
                    "f": f_input,
                },
            )["products"]
            items = data["items"]
            for it in items:
                if it["id"] in seen:
                    continue
                seen.add(it["id"])
                rows.append(self.row(it))
            last = data["pagination"]["lastPage"]
            print(f"page {page}/{last} — {len(rows)} unique", file=sys.stderr)
            if page >= last or not items:
                break
            page += 1
        return rows

    def output_path(self):
        return MEDIA_DIR / f"newbalance_{self.slug.replace('/', '_')}.csv"

    def run(self):
        rows = self.scrape()
        MEDIA_DIR.mkdir(parents=True, exist_ok=True)
        out = self.output_path()
        with open(out, "w", newline="", encoding="utf-8") as f:
            w = csv.writer(f)
            w.writerow(self.HEADER)
            w.writerows(rows)
        print(f"wrote {len(rows)} rows -> {out}", file=sys.stderr)
        return out
