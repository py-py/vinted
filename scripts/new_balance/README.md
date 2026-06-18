# newbalance.pl scraper

Dumps newbalance.pl listings (model name + price) to CSV.

- **`nb_base.py`** — shared `NBListingScraper` base class (resolve → paginate → write CSV)
- **`scrape_sales.py`** — `CategoryScraper`: a normal category listing (`meskie`, `meskie/obuwie`, …)
- **`scrape_promotions.py`** — `PromoScraper`: the sale listing (`/promocja`) with filters

Both scripts take a `--url` and subclass `NBListingScraper`, differing only in their
default sort. `scrape_promotions.py` additionally carries the `f.*` sale filters through.

## How it works

newbalance.pl is a **Next.js** storefront. The HTML only contains **page 1** of any
listing — URL params like `?page=2` are ignored server-side, and the SSR HTML is
sometimes a gzipped JS shell with no data — so the catalog is read entirely from the
site's own GraphQL API instead:

1. **resolve** the slug to an internal `(objectType, objectId)` via the `urlResolver`
   query (e.g. `meskie` → category `13026`, `meskie/obuwie` → category `13031`,
   `promocja` → flag `1`). The slug is the full path after the domain; `objectType`
   maps to the `ListingType` enum as `from_<type>` (`from_category`, `from_flag`, …);
2. page through the GraphQL `products` query until `lastPage`, deduping by item id.

The sale listing is normally narrowed with filters (`f.<id>=<value>` in the URL,
e.g. `f.69=13026` = category Obuwie); `scrape_promotions.py` passes them straight
through as the GraphQL `filters` input.

GraphQL endpoint (no auth required):

```
POST https://aplikacja.newbalance.pl/api/graphql/frontend
query products(type: <ListingType>, id: <objId>, page: N, limit: 96, sort: ..., filters: ...)
```

## Usage

### scrape_sales.py — category listings

Just paste a listing URL — slug and sort are parsed out of it:

```bash
python scrape_sales.py --url "https://newbalance.pl/meskie?sort=-gross_sell_price"
python scrape_sales.py --url "https://newbalance.pl/meskie/obuwie?sort=-gross_sell_price"
```

### scrape_promotions.py — sale listing with filters

Just paste the sale URL — slug, sort and `f.*` filters are parsed out of it:

```bash
python scrape_promotions.py --url "https://newbalance.pl/promocja?sort=gross_sell_price&f.69=13026&f.95=Obuwie"
```

The CSV is written to the project's `media/` folder, with a filename derived from
the slug (`meskie/obuwie` → `media/newbalance_meskie_obuwie.csv`,
`promocja` → `media/newbalance_promocja.csv`).

Both scripts: stdlib only, no dependencies. Progress is printed to stderr.

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
| `is_best_30d` | `True` if today's price ≤ the 30-day low — i.e. genuinely the best recent price |
| `vs_lowest_30d_%` | today's price vs the 30-day low, signed: `-13` = 13% cheaper, `+50` = 50% pricier |
| `url` | product page URL |

`is_best_30d` / `vs_lowest_30d_%` cut through inflated "before" prices: a big `discount_%`
off `price_before_discount` can still be *above* the 30-day low (positive `vs_lowest_30d_%`).

GraphQL exposes no discount-% field on products, so it is computed the same way the
site renders its badge: `round((base − sell) / base × 100)`.

Sample snapshots, captured 2026-06-18:

- `newbalance_meskie.csv` — men's category (1332 models, price descending)
- `newbalance_promocja.csv` — sale, men's footwear (429 models, price ascending)
