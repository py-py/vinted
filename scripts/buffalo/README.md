# buffalo-boots.com scraper

Dumps a buffalo-boots.com category listing (product + price + per-size stock) to CSV.
One script, `scrape.py` — paste any category URL (or pass a category id) and it pages
through the whole category.

## How it works

buffalo-boots.com is a **SCAYLE** storefront (the commerce engine by ABOUT YOU) behind
a Next.js frontend. The public website (`www.`) is **fully gated by Cloudflare bot
management** — every non-browser request, even `robots.txt`, returns `403 Attention
Required`, with or without a browser `User-Agent`. So the catalog is read instead from
the storefront's own JSON API on the **`api.` host**, which is *not* behind that bot
wall:

```
GET https://api.buffalo-boots.com/sni-pl-prd-stor-we-char/v1/v1/categories/{id}?page={n}&perPage={m}
```

The category `id` is the **trailing number** of a category URL slug
(`.../c/shoes-heels-3140` → `3140`). The script pages from `page=1` (1-based on input)
until `pagination.totalPages`, deduping by product id.

**Two passes for stock.** The category listing ships only a *single placeholder variant*
per product (usually size 36, often out of stock), so per-size stock can't be read from
it. After paging the listing, the script fetches each product's full variant set from the
per-product endpoint (`/products/{id}`, 8 concurrent workers, retried on transient
errors) and uses those for `sizes_in_stock` / `stock_total`:

```
GET https://api.buffalo-boots.com/sni-pl-prd-stor-we-char/v1/v1/products/{id}
```

### The `x-charybdis` header

The one non-obvious requirement: the API returns **400** without an `x-charybdis`
request header. It is a base64-encoded JSON blob carrying the **storefront config**
(shop id `1090`, environment `snipes-live`, locale `context: en-int`, Contentful space,
…) — the *same static value for every visitor*, **not** a personal or auth token. It is
embedded in `scrape.py` as `DEFAULT_TOKEN`, and the locale `context` is decoded from it
to build product URLs.

The header is plain config, so the **market is selected by editing two of its fields** —
`build_token()` does this for you from `--context` / `--shop-id` (see below) and
re-encodes the header.

No login or cookies are needed.

### Choosing the market — EU/Poland is the default

Buffalo runs an international store (`/en-int/`) and the **EU store at `/en-eu/`** (the
English-language storefront covering Poland). All of them price in **EUR** — there is no
PLN store on this API. The market is two independent knobs in the token, both defaulting
to the EU store:

- **`--context`** picks the *locale → assortment* and the URL locale prefix. Default
  **`en-eu`**; `en-int` returns a different product set.
- **`--shop-id`** picks the *price list*. Default **`1087`** — an EU consumer-market shop
  that carries the **EU-Omnibus 30-day low**, which `en-int`/`1090` does *not* return.

So the default run targets the EU/Poland store with the 30-day low populated, so the
`lowest_30d_EUR` / `is_best_30d` / `vs_lowest_30d_%` columns light up. Pass
`--context en-int --shop-id 1090` for the international store.

## Usage

Run with the project venv (`uv run`). Paste a category URL, or pass the id directly —
the market defaults to EU/Poland:

```bash
# EU/Poland (default): EUR price list with the 30-day Omnibus low
uv run python scripts/buffalo/scrape.py --url "https://www.buffalo-boots.com/en-eu/c/shoes-heels-3140"

# by category id (still EU/Poland)
uv run python scripts/buffalo/scrape.py --category-id 3142

# international store instead
uv run python scripts/buffalo/scrape.py --category-id 3142 --context en-int --shop-id 1090
```

To find a category id, open the category on the site and read the number at the end of
the URL (`/c/<slug>-<id>`). Sub-categories work the same way (each has its own id).

The CSV is written to the project's `media/` folder, named from the locale + slug (or
id), so markets don't overwrite each other: `en-eu` + `shoes-heels-3140` →
`media/buffalo_en-eu_shoes-heels-3140.csv`, `--context en-int … 3142` →
`media/buffalo_en-int_3142.csv`.

Only dependency is **petl** (CSV writing), managed via uv. Progress is printed to stderr.

## Output

CSV with columns:

| column | meaning |
|---|---|
| `model` | product name (`displayName`, e.g. `Rainelle`) |
| `color` | colour attribute, e.g. `gold` |
| `category` | breadcrumb path, e.g. `Shoes / Heels` |
| `price_EUR` | current price (from the `priceRange.min`, gross, EUR) |
| `price_before_discount_EUR` | strike-through "before" price (current + applied reductions), only when the item is on sale (`hasStrikeout`) |
| `lowest_30d_EUR` | EU-Omnibus 30-day low (`lowestPriorPrice`). Provided only in locales that legally require it — **empty in `en-int`**; kept for parity with the New Balance scraper |
| `discount_%` | discount badge %, taken straight from the API (`relativeDiscount`) |
| `is_best_30d` | `True` if today's price ≤ the 30-day low. Only filled when `lowest_30d` is present and ≠ the "before" price |
| `vs_lowest_30d_%` | today's price vs the 30-day low, signed (`-13` = 13% cheaper). Same fill condition as `is_best_30d` |
| `sizes_in_stock` | JSON object mapping each in-stock EU size to its quantity, e.g. `{"36": 2, "37": 1}` (from the per-product `variants` — `attributes.size` → `stock.quantity`); only variants with quantity > 0 |
| `stock_total` | total pairs in stock across all sizes |
| `url` | product page URL, `…/<context>/p/<id>` (e.g. `…/en-eu/p/64629`) |

Prices come from the API as integer minor units (cents); the script divides by 100
(e.g. `3100` → `31.0`).

**Product URLs.** The link uses the slugless `/{context}/p/{id}` form — the trailing
product id resolves the PDP on its own. This sidesteps the redirect that the API's
*localized* colour slug triggers on the live site (for `en-eu` the API returns
`…-negro-…` / `…-blanco-…`, which the site 301-redirects to its English `…-black-…`).

Rows are written **best-price first**, sorted by one unified *real savings vs the 30-day
low* %, ascending (most negative = best), with cheapest price as the tie-break — the same
logic as the New Balance scraper:

- where the Omnibus 30-day low is provided, `vs_lowest_30d_%` is used directly (a
  **positive** value means the headline discount is off an inflated "before" price → the
  row sinks to the bottom);
- where it is absent (e.g. `en-int`), the headline `discount_%` is itself the genuine
  saving → `-discount_%` is used;
- not on sale → 0, ranked between the real deals and the inflated ones.

> Note: the Omnibus 30-day low is only returned by EU consumer-market shops (the default
> `--shop-id 1087` is one). Switch to the international store
> (`--context en-int --shop-id 1090`) and `lowest_30d_EUR` / `is_best_30d` /
> `vs_lowest_30d_%` go empty, with ranking falling back to the headline `discount_%`.