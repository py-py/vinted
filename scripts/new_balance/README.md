# newbalance.pl scraper

Dumps a newbalance.pl listing (model name + price) to CSV. One script, `scrape.py` —
paste any listing URL (category, subcategory, or the `/promocja` sale) and it figures
out the rest.

## How it works

newbalance.pl is a **Next.js** storefront. The HTML only contains **page 1** of any
listing — URL params like `?page=2` are ignored server-side, and the SSR HTML is
sometimes a gzipped JS shell with no data — so the catalog is read entirely from the
site's own GraphQL API instead:

1. **resolve** the slug (the URL path) to an internal `(objectType, objectId)` via the
   `urlResolver` query (e.g. `meskie` → category `13026`, `meskie/obuwie` → category
   `13031`, `promocja` → flag `1`). `objectType` maps to the `ListingType` enum as
   `from_<type>` (`from_category`, `from_flag`, …);
2. page through the GraphQL `products` query until `lastPage`, deduping by item id.

`sort` and `f.<id>=<value>` filters are taken straight from the URL query string and
passed through to the `products` query (sale listings are normally narrowed this way,
e.g. `f.69=13026` = category Obuwie). If the URL has no `sort=`, it defaults to
`-gross_sell_price` (price descending).

GraphQL endpoint (no auth required):

```
POST https://aplikacja.newbalance.pl/api/graphql/frontend
query products(type: <ListingType>, id: <objId>, page: N, limit: 96, sort: ..., filters: ...)
```

## Usage

Run with the project venv (`uv run`). Just paste a listing URL:

```bash
# a category / subcategory
uv run python scripts/new_balance/scrape.py --url "https://newbalance.pl/meskie?sort=-gross_sell_price"
uv run python scripts/new_balance/scrape.py --url "https://newbalance.pl/meskie/obuwie"

# the sale, narrowed by filters
uv run python scripts/new_balance/scrape.py --url "https://newbalance.pl/promocja?sort=gross_sell_price&f.69=13026&f.95=Obuwie"
```

The CSV is written to the project's `media/` folder, with a filename derived from
the slug (`meskie/obuwie` → `media/newbalance_meskie_obuwie.csv`,
`promocja` → `media/newbalance_promocja.csv`).

Only dependency is **petl** (for CSV writing), managed via uv. Progress is printed to stderr.

## Output

CSV with columns:

| column | meaning |
|---|---|
| `model` | full product name |
| `category` | category path from GraphQL `categoryPath`, e.g. `Męskie / Obuwie / Piłkarskie` |
| `price_PLN` | current sell price (gross, PLN) |
| `price_before_discount_PLN` | "Cena pierwsza" — pre-discount price, if on promo (else empty) |
| `lowest_30d_PLN` | "Najniższa cena z 30 dni przed obniżką" (GraphQL `omnibusPrice`) |
| `discount_%` | discount %, derived from `price` vs `price_before_discount` (empty if not on promo) |
| `is_best_30d` | `True` if today's price ≤ the 30-day low. Only filled when `lowest_30d` ≠ `price_before_discount` (otherwise it adds nothing) |
| `vs_lowest_30d_%` | today's price vs the 30-day low, signed: `-13` = 13% cheaper, `+50` = 50% pricier. Same fill condition as `is_best_30d` |
| `url` | product page URL |

`is_best_30d` / `vs_lowest_30d_%` cut through inflated "before" prices: a big `discount_%`
off `price_before_discount` can still be *above* the 30-day low (positive `vs_lowest_30d_%`).

GraphQL exposes no discount-% field on products, so it is computed the same way the
site renders its badge: `round((base − sell) / base × 100)`.
