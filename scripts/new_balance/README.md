# newbalance.pl scraper

Dumps newbalance.pl listings (model name + price) to CSV. Two scripts:

- **`scrape_nb.py`** — a normal category listing (`meskie`, `meskie/obuwie`, …)
- **`scrape_promocja.py`** — the sale listing (`/promocja`) with filters

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
e.g. `f.69=13026` = category Obuwie); `scrape_promocja.py` passes them straight
through as the GraphQL `filters` input.

GraphQL endpoint (no auth required):

```
POST https://aplikacja.newbalance.pl/api/graphql/frontend
query products(type: <ListingType>, id: <objId>, page: N, limit: 96, sort: ..., filters: ...)
```

## Usage

### scrape_nb.py — category listings

```bash
# default: category "meskie", sorted by gross price descending
python scrape_nb.py

# another top-level category
python scrape_nb.py --slug damskie
python scrape_nb.py --slug dzieciece

# a subcategory — pass the full path as the slug
python scrape_nb.py --slug meskie/obuwie

# custom sort / output file
python scrape_nb.py --slug meskie --sort -gross_sell_price --out out.csv
```

### scrape_promocja.py — sale listing with filters

Just paste the sale URL — slug, sort and `f.*` filters are parsed out of it:

```bash
python scrape_promocja.py --url "https://newbalance.pl/promocja?sort=gross_sell_price&f.69=13026&f.95=Obuwie"
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
| `price_PLN` | current sell price (gross, PLN) |
| `price_before_discount_PLN` | pre-discount price, if on promo (else empty) |
| `discount_%` | discount %, derived from the two prices above (empty if not on promo) |
| `url` | product page URL |

GraphQL exposes no discount-% field on products, so it is computed the same way the
site renders its badge: `round((base − sell) / base × 100)`.

Sample snapshots, captured 2026-06-18:

- `newbalance_meskie.csv` — men's category (1332 models, price descending)
- `newbalance_promocja.csv` — sale, men's footwear (429 models, price ascending)
