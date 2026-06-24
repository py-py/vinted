#!/usr/bin/env python3
"""Dump a buffalo-boots.com category listing (products + prices) to CSV.

buffalo-boots.com is a **SCAYLE** storefront (the commerce engine by ABOUT YOU)
behind a Next.js frontend. The public website (`www.`) is fully gated by Cloudflare
bot management — every non-browser request, even robots.txt, gets a 403 — so the
catalog is read instead from the storefront's own JSON API on the `api.` host, which
is *not* behind that bot wall:

    GET https://api.buffalo-boots.com/sni-pl-prd-stor-we-char/v1/v1/categories/{id}
        ?page={n}&perPage={m}

The only non-obvious requirement is the `x-charybdis` header: a base64-encoded JSON
blob carrying the storefront config (shop id, environment, locale context). It is the
*same static value for every visitor* — not a personal/auth token — so it is embedded
below (`DEFAULT_TOKEN`) and `build_token()` re-encodes it for the chosen market via
`--context` / `--shop-id`. Without the header the API returns 400.

`BuffaloScraper` pages through a category until `totalPages`, deduping by product id.
The category id is the trailing number of a category URL slug
(`.../c/shoes-heels-3140` -> 3140), so just paste any category URL. The market defaults
to **EU/Poland** (`--context en-eu --shop-id 1087`): EUR pricing with the EU-Omnibus
30-day low. Pass `--context en-int --shop-id 1090` for the international store.

Product URLs use the slugless `/{context}/p/{id}` form (the trailing id resolves the
PDP on its own), which avoids the redirect a localized colour slug would trigger.

    python scrape.py --url "https://www.buffalo-boots.com/en-eu/c/shoes-heels-3140"
    python scrape.py --category-id 3142
    python scrape.py --category-id 3142 --context en-int --shop-id 1090

The CSV is written to the project's media/ folder. Run with the project venv (uv) —
CSV output uses petl.
"""

import argparse
import base64
import json
import re
import sys
import time
import urllib.parse
import urllib.request
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path

import petl

UA = "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36"
SITE = "https://www.buffalo-boots.com"
API_BASE = "https://api.buffalo-boots.com/sni-pl-prd-stor-we-char/v1/v1"
# project_root/media — this file lives in <root>/scripts/buffalo/
MEDIA_DIR = Path(__file__).resolve().parents[2] / "media"

# Storefront config sent by every browser as the `x-charybdis` header. Not a secret
# or per-user token — it is the same static value for all visitors (shop 1090, the
# en-int locale). The API returns 400 without it. Override via --token / $BUFFALO_TOKEN.
DEFAULT_TOKEN = (
    "eyJjb25jZXB0IjoiQlVGIiwic2NheWxlRW52aXJvbm1lbnQiOiJzbmlwZXMtbGl2ZSIsInNjYXlsZVNo"
    "b3BJZCI6IjEwOTAiLCJjbXNTcGFjZSI6IjlrZW1hZnA4eTQ1MyIsImNtc0Vudmlyb25tZW50IjoibWFz"
    "dGVyIiwiY21zQWNjZXNzVG9rZW4iOiJ0emU3RkdqT3Q1alNCdkhDRlFFX0s1a2hxbUdvNmoyV203VGE0"
    "RWd6eTFVIiwidHJlZSI6IjM4IiwiaGFkZXMiOmZhbHNlLCJjYW1wYWlnbktleSI6IiIsImNvbnRleHQi"
    "OiJlbi1pbnQiLCJ1c2VNaXdhIjpmYWxzZSwibG95YWx0eSI6ZmFsc2UsImxveWFsdHlDYW1wYWlnbktl"
    "eSI6IiIsImNvbXBhbnkiOiJmaW4iLCJuZXdzbGV0dGVyUmVnaXN0cmF0aW9uIjoiMyIsInVzZXJSZWdp"
    "c3RyYXRpb24iOiIzIiwibm90aWZ5TWVSZWdpc3RyYXRpb24iOjAsInVwZ3JhZGVVc2VyU2VydmljZSI6"
    "MCwiaGFzMzBEYXlzUHJpY2VGYWxsYmFjayI6ZmFsc2UsInBob25lVmFsaWRhdGlvbiI6IiIsImhhc1By"
    "ZWZlcmVuY2VDZW50ZXIiOmZhbHNlLCJoYXNTdGFtcGNhcmQiOmZhbHNlLCJzaG93TG93ZXN0UHJpY2VM"
    "ZWdhbFJlcXVpcmVtZW50cyI6ZmFsc2UsImxveWFsdHlFbmdpbmUiOiJ1bmRlZmluZWQiLCJzb3VyY2Ui"
    "OiJXZWIiLCJ6ZW5kZXNrU3ViZG9tYWluIjoic25pcGVzc3VwcG9ydCIsImJhc2VzdG9yZVVybCI6IiJ9"
)


def decode_token(token):
    """Decode the base64 x-charybdis blob to its config dict (empty on failure)."""
    try:
        return json.loads(base64.b64decode(token + "=" * (-len(token) % 4)))
    except Exception:
        return {}


def build_token(context=None, shop_id=None, base=DEFAULT_TOKEN):
    """Return an x-charybdis token, optionally overriding the market.

    The header is just a base64 JSON config, so a different storefront is selected by
    editing two fields on the default and re-encoding:

      * `context`  — the locale, which drives the *assortment* (e.g. 'en-int' → 53
        international products in a category, 'en-pl' → the Polish range);
      * `scayleShopId` — the *price list*. Shops 1085–1087 are EU consumer markets
        (Poland among them) that carry the EU-Omnibus 30-day low; 1090 is en-int and
        does not. All Buffalo shops on this API price in EUR.

    `showLowestPriceLegalRequirements` is forced on so the 30-day low comes through
    wherever the shop provides it.
    """
    cfg = decode_token(base)
    if context:
        cfg["context"] = context
    if shop_id:
        cfg["scayleShopId"] = str(shop_id)
    cfg["showLowestPriceLegalRequirements"] = True
    return base64.b64encode(json.dumps(cfg).encode()).decode()


def cents(value):
    """SCAYLE prices are integer minor units (3100 -> 31.00). None stays None."""
    return round(value / 100, 2) if value is not None else None


class BuffaloScraper:
    """Page through one category's products and write the rows to media/."""

    HEADER = [
        "model",
        "color",
        "category",
        "price_EUR",
        "price_before_discount_EUR",
        "lowest_30d_EUR",
        "discount_%",
        "is_best_30d",
        "vs_lowest_30d_%",
        "sizes_in_stock",
        "stock_total",
        "url",
    ]

    def __init__(self, category_id, slug=None, token=DEFAULT_TOKEN, per_page=200):
        self.category_id = str(category_id)
        self.slug = slug or self.category_id
        self.token = token
        self.per_page = per_page
        # the locale prefix for product URLs (e.g. 'en-int', 'en-pl')
        self.context = decode_token(token).get("context") or "en-int"

    @classmethod
    def from_url(cls, url, **kw):
        """Build a scraper from a category URL. The id is the trailing number of the
        last path segment: '.../c/shoes-heels-3140' -> slug 'shoes-heels-3140', id 3140."""
        seg = urllib.parse.urlparse(url).path.rstrip("/").split("/")[-1]
        m = re.search(r"(\d+)$", seg)
        if not m:
            sys.exit(f"could not find a category id at the end of {seg!r}")
        return cls(category_id=m.group(1), slug=seg, **kw)

    def _get(self, path):
        """GET an API path (relative to API_BASE) and return parsed JSON."""
        req = urllib.request.Request(
            f"{API_BASE}{path}",
            headers={
                "Accept": "application/json",
                "User-Agent": UA,
                "Origin": SITE,
                "x-charybdis": self.token,
            },
        )
        return json.loads(urllib.request.urlopen(req, timeout=30).read())

    def fetch(self, page):
        """GET one page of the category endpoint as parsed JSON."""
        qs = urllib.parse.urlencode({"page": page, "perPage": self.per_page})
        return self._get(f"/categories/{self.category_id}?{qs}")

    def product_variants(self, pid, attempts=3):
        """Full per-size variants for one product. The category listing only ships a
        single placeholder variant per product, so real size/stock data has to come
        from the per-product endpoint. Retries a few times on transient errors."""
        for attempt in range(1, attempts + 1):
            try:
                return self._get(f"/products/{pid}").get("variants") or []
            except Exception as e:  # noqa: BLE001 — one bad product shouldn't kill the run
                if attempt == attempts:
                    print(f"  warn: variants fetch failed for {pid}: {e}", file=sys.stderr)
                    return []
                time.sleep(0.5 * attempt)

    @staticmethod
    def sizes(product):
        """Map each in-stock size to its quantity across variants.

        Each variant carries a `size` attribute (EU size label) and a `stock.quantity`.
        Returns {size_label: quantity, ...} for variants with quantity > 0 only.
        """
        in_stock = {}
        for v in product.get("variants") or []:
            qty = ((v.get("stock") or {}).get("quantity")) or 0
            if qty <= 0:
                continue
            attrs = v.get("attributes") or {}
            size = ((attrs.get("size") or {}).get("values") or {}).get("label") or "?"
            in_stock[size] = in_stock.get(size, 0) + qty
        return in_stock

    def row(self, p):
        """Map one product to a dict keyed by HEADER column names."""
        attrs = p.get("attributes") or {}
        color = ((attrs.get("color") or {}).get("values") or {}).get("label")
        category = " / ".join(b.get("categoryName", "") for b in (p.get("breadcrumbs") or []))

        price_min = (p.get("priceRange") or {}).get("min") or {}
        sell = price_min.get("withTax")
        # the strike-through "before" price = current + every applied reduction; the
        # site only shows it when hasStrikeout is true (i.e. the item is actually on sale)
        reductions = sum(
            (r.get("amount") or {}).get("absoluteWithTax") or 0
            for r in (price_min.get("appliedReductions") or [])
        )
        before = sell + reductions if p.get("hasStrikeout") and sell is not None else None
        # the API hands us the badge percentage directly (relativeDiscount: 59)
        discount = p.get("relativeDiscount") or None

        # EU-Omnibus 30-day low. Populated only where the locale legally requires it
        # (empty in en-int) — kept for parity with the New Balance scraper and so the
        # column lights up automatically in locales that do provide it.
        lowest_30d = (p.get("lowestPriorPrice") or {}).get("withTax")
        is_best_30d = vs_lowest = None
        if before and lowest_30d and before != lowest_30d:
            is_best_30d = sell <= lowest_30d
            vs_lowest = round((sell / lowest_30d - 1) * 100)

        in_stock = self.sizes(p)
        return {
            "model": p.get("displayName"),
            "color": color,
            "category": category,
            "price_EUR": cents(sell),
            "price_before_discount_EUR": cents(before),
            "lowest_30d_EUR": cents(lowest_30d),
            "discount_%": discount,
            "is_best_30d": is_best_30d,
            "vs_lowest_30d_%": vs_lowest,
            "sizes_in_stock": json.dumps(in_stock, ensure_ascii=False),
            "stock_total": sum(in_stock.values()),
            # the trailing product id alone resolves the PDP; using the slugless form
            # avoids the redirect that the localized colour slug (e.g. en-pl '…-negro-…')
            # triggers on the live site
            "url": f"{SITE}/{self.context}/p/{p['id']}",
        }

    def scrape(self):
        """Return one dict per product (keyed by HEADER).

        Two passes: page the category listing to collect the products (everything but
        real size/stock), then fetch each product's full variants concurrently so
        `sizes_in_stock` / `stock_total` reflect every size, not the single placeholder
        variant the listing ships.
        """
        products, seen, page = [], set(), 1
        while True:
            data = self.fetch(page)
            pg = data.get("pagination") or {}
            total_pages = pg.get("totalPages") or 1
            batch = data.get("products") or []
            for p in batch:
                if p["id"] not in seen:
                    seen.add(p["id"])
                    products.append(p)
            print(
                f"page {page}/{total_pages} — {len(seen)}/{pg.get('totalResults', '?')} unique",
                file=sys.stderr,
            )
            if page >= total_pages or not batch:
                break
            page += 1

        print(f"fetching full variants for {len(products)} products…", file=sys.stderr)
        with ThreadPoolExecutor(max_workers=8) as pool:
            variants = pool.map(self.product_variants, [p["id"] for p in products])
        for p, v in zip(products, variants):
            p["variants"] = v
        return [self.row(p) for p in products]

    def output_path(self):
        # include the locale so different markets don't overwrite each other
        return MEDIA_DIR / f"buffalo_{self.context}_{self.slug.replace('/', '_')}.csv"

    @staticmethod
    def _sort_key(r):
        """Rank a row for the output CSV — best offers first.

        Mirrors the New Balance scraper: sort by one unified "real savings vs the
        30-day low" %, ascending (most negative = best deal). Where the Omnibus 30-day
        low is provided, `vs_lowest_30d_%` is the truest measure (a positive value means
        the headline discount is off an inflated "before" price → sinks down). Where it
        is absent (e.g. en-int), the headline `discount_%` is the genuine saving, so
        `-discount_%` is used. Not on sale → 0. Tie-break by cheapest price.
        """
        inf = float("inf")
        price = r["price_EUR"] if r["price_EUR"] is not None else inf
        if r["vs_lowest_30d_%"] is not None:
            savings = r["vs_lowest_30d_%"]
        elif r["discount_%"] is not None:
            savings = -r["discount_%"]
        else:
            savings = 0
        return (savings, price)

    def run(self):
        MEDIA_DIR.mkdir(parents=True, exist_ok=True)
        out = self.output_path()
        rows = sorted(self.scrape(), key=self._sort_key)
        # header keeps column order fixed without petl having to sample the dicts
        petl.tocsv(petl.fromdicts(rows, header=self.HEADER), str(out), encoding="utf-8")
        print(f"wrote {len(rows)} rows (best-price first) -> {out}", file=sys.stderr)
        return out


def main():
    ap = argparse.ArgumentParser(
        description=__doc__,
        formatter_class=argparse.RawDescriptionHelpFormatter,
    )
    src = ap.add_mutually_exclusive_group(required=True)
    src.add_argument("--url", help="category URL; the id is parsed from the trailing number")
    src.add_argument("--category-id", help="category id directly, e.g. 3142")
    ap.add_argument(
        "--context",
        default="en-eu",
        help="locale / market, drives the assortment and the URL locale prefix. Default "
        "'en-eu' (EU/Poland); use 'en-int' for the international range.",
    )
    ap.add_argument(
        "--shop-id",
        default="1087",
        help="SCAYLE shop id (price list). Default 1087 (Poland/EU price list, carries "
        "the 30-day Omnibus low); use 1090 for en-int.",
    )
    args = ap.parse_args()

    token = build_token(context=args.context, shop_id=args.shop_id)
    if args.url:
        scraper = BuffaloScraper.from_url(args.url, token=token)
    else:
        scraper = BuffaloScraper(category_id=args.category_id, token=token)
    scraper.run()


if __name__ == "__main__":
    main()
