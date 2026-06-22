#!/usr/bin/env python3
"""Dump a newbalance.pl listing (models + prices) to CSV.

newbalance.pl is a Next.js storefront whose HTML only ever contains page 1 of a
listing (URL params like ?page=2 are ignored server-side), so the catalog is read
entirely from the site's own GraphQL API:

  1. resolve a slug (full path, e.g. 'meskie/obuwie' or 'promocja') to an internal
     (objectType, objectId) via the `urlResolver` query;
  2. page through the `products` query until `lastPage`, deduping by item id.

`NBListingScraper` handles every listing kind (category, sale flag, …) — the slug,
sort and f.* filters all come from the URL, so just paste any listing URL:

    python scrape.py --url "https://newbalance.pl/meskie?sort=-gross_sell_price"
    python scrape.py --url "https://newbalance.pl/meskie/obuwie?sort=-gross_sell_price"
    python scrape.py --url "https://newbalance.pl/promocja?sort=gross_sell_price&f.69=13026&f.95=Obuwie"

The CSV is written to the project's media/ folder. No auth needed. Run with the
project venv (uv) — CSV output uses petl.
"""

import argparse
import json
import sys
import urllib.parse
import urllib.request
from pathlib import Path

import petl

UA = "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36"
SITE = "https://newbalance.pl"
GRAPHQL = "https://aplikacja.newbalance.pl/api/graphql/frontend"
# project_root/media — this file lives in <root>/scripts/new_balance/
MEDIA_DIR = Path(__file__).resolve().parents[2] / "media"

PRODUCTS_QUERY = """
query (
  $t: ListingType!
  $id: ID!
  $page: Int!
  $limit: Int
  $sort: String
  $f: FiltersInput
) {
  products(
    id: $id
    type: $t
    page: $page
    limit: $limit
    sort: $sort
    filters: $f
  ) {
    items {
      id
      name
      niceUrl
      categoryPath {
        name
      }
      prices {
        sellPrice {
          gross
        }
        listPrice {
          gross
        }
        basePrice {
          gross
        }
        omnibusPrice {
          gross
        }
      }
      variants {
        option
        availability {
          stock {
            amount
          }
        }
      }
    }
    pagination {
      itemsCount
      lastPage
    }
  }
}
"""


URL_RESOLVER_QUERY = """
query ($slug: String!) {
  urlResolver(slug: $slug) {
    objectType
    objectId
    isRedirect
    redirectTo
  }
}
"""


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


class NewBalanceScraper:
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
        "sizes_in_stock",
        "stock_total",
        "url",
    ]

    def __init__(self, slug, sort=None, filters=None, limit=96):
        self.slug = slug
        self.sort = sort  # None -> the API returns items in its own default order
        self.filters = filters or {}
        self.limit = limit

    @classmethod
    def from_url(cls, url):
        """Build a scraper from a listing URL, parsing the slug (path), sort and
        f.* filters from the query string."""
        u = urllib.parse.urlparse(url)
        slug = u.path.strip("/")
        sort = "-gross_sell_price"  # default when the URL carries no sort= param
        filters = {}
        for key, vals in urllib.parse.parse_qs(u.query).items():
            if key == "sort":
                sort = vals[0]
            elif key.startswith("f."):
                filters[key[2:]] = vals
        return cls(slug, sort, filters)

    def resolve(self):
        """
        Resolve the slug to (listingType, objectId). objectType (category/flag/...)
        maps to the ListingType enum as from_<type>.
        """
        data = graphql(query=URL_RESOLVER_QUERY, variables={"slug": self.slug})
        resolver = data["urlResolver"]
        if not resolver or not resolver.get("objectId"):
            sys.exit(f"could not resolve slug={self.slug!r}")
        if resolver.get("isRedirect"):
            print(f"note: {self.slug} redirects to {resolver.get('redirectTo')}", file=sys.stderr)
        return f"from_{resolver['objectType']}", str(resolver["objectId"])

    def filters_input(self):
        """
        Turn {attr_id: [values]} into a GraphQL FiltersInput, or None if empty.
        A single value becomes {key,value}; several become {key,values:[...]}.
        """
        fields = []
        for key, vals in self.filters.items():
            vals = vals if isinstance(vals, list) else [vals]
            if len(vals) == 1:
                fields.append({"key": key, "value": vals[0]})
            else:
                fields.append({"key": key, "values": vals})
        return {"fields": fields} if fields else None

    @staticmethod
    def sizes(it):
        """Sum stock across variants and map each in-stock size to its quantity.

        Each variant `option` looks like '42.5 Standardowa (D)' (EU size + width);
        we use it verbatim as the key. Returns (json_string, total_pairs) where the
        JSON is e.g. {"42.5 Standardowa (D)": 15, ...} — only variants with stock > 0.
        """
        in_stock = {}
        for v in it.get("variants") or []:
            amount = ((v.get("availability") or {}).get("stock") or {}).get("amount") or 0
            if amount <= 0:
                continue
            in_stock[v.get("option") or ""] = amount
        return in_stock

    @staticmethod
    def row(it):
        """Map one product item to a dict keyed by HEADER column names."""
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
        # is today's price the best of the last 30 days, and by how much? only
        # meaningful when the 30-day low differs from the "before" price — otherwise
        # vs_lowest just mirrors discount_% and adds nothing.
        is_best_30d = vs_lowest = None
        if before and lowest_30d and before != lowest_30d:
            is_best_30d = sell <= lowest_30d
            vs_lowest = round((sell / lowest_30d - 1) * 100)
        category = " / ".join(c["name"] for c in (it.get("categoryPath") or []))
        in_stock = NewBalanceScraper.sizes(it)
        return {
            "model": it["name"],
            "category": category,
            "price_PLN": sell,
            "price_before_discount_PLN": before,
            "lowest_30d_PLN": lowest_30d,
            "discount_%": discount,
            "is_best_30d": is_best_30d,
            "vs_lowest_30d_%": vs_lowest,
            "sizes_in_stock": json.dumps(in_stock, ensure_ascii=False),
            "stock_total": sum(in_stock.values()),
            "url": f"{SITE}/{it['niceUrl']}",
        }

    def scrape(self):
        """Yield one dict per product (keyed by HEADER), paging until lastPage."""
        listing_type, obj_id = self.resolve()
        f_input = self.filters_input()
        print(
            f"slug={self.slug} -> {listing_type} id={obj_id} filters={self.filters or '{}'}",
            file=sys.stderr,
        )
        seen, page = set(), 1
        while True:
            data = graphql(
                query=PRODUCTS_QUERY,
                variables={
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
                yield self.row(it)
            last = data["pagination"]["lastPage"]
            print(f"page {page}/{last} — {len(seen)} unique", file=sys.stderr)
            if page >= last or not items:
                break
            page += 1

    def output_path(self):
        return MEDIA_DIR / f"newbalance_{self.slug.replace('/', '_')}.csv"

    def run(self):
        MEDIA_DIR.mkdir(parents=True, exist_ok=True)
        out = self.output_path()
        # header keeps column order fixed without petl having to sample the dicts
        petl.tocsv(petl.fromdicts(self.scrape(), header=self.HEADER), str(out), encoding="utf-8")
        count = petl.nrows(petl.fromcsv(str(out)))
        print(f"wrote {count} rows -> {out}", file=sys.stderr)
        return out


def main():
    ap = argparse.ArgumentParser(
        description=__doc__,
        formatter_class=argparse.RawDescriptionHelpFormatter,
    )
    ap.add_argument(
        "--url",
        required=True,
        help="full listing URL; slug, sort and f.* filters are parsed from it",
    )
    args = ap.parse_args()

    scraper = NewBalanceScraper.from_url(args.url)
    scraper.run()


if __name__ == "__main__":
    main()
