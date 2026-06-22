# New Balance (newbalance.pl) — scraper & resale-liquidity analysis

Log of the work: building a listing scraper for **newbalance.pl** and using it,
together with Vinted demand data, to judge which discounted New Balance models are
worth buying for resale. Snapshot captured **2026-06-19**.

---

## 1. The scraper

Code: `scripts/new_balance/scrape.py` (+ `README.md`). Output: CSV in `media/`.

### How the site works
newbalance.pl is a **Next.js** storefront. Two gotchas:
- the default page fetcher gets `404` (UA-blocked); a browser `User-Agent` gets `200`;
- the HTML only ever contains **page 1** — `?page=2` is ignored server-side, and the SSR
  HTML is sometimes a gzipped JS shell with no data.

So the catalog is read from the site's own **GraphQL API** instead:

```
POST https://aplikacja.newbalance.pl/api/graphql/frontend
```

1. **resolve** the slug (URL path) → internal `(objectType, objectId)` via the
   `urlResolver` query. `objectType` maps to the `ListingType` enum as `from_<type>`:
   - `meskie` → category `13026`
   - `meskie/obuwie` → category `13031`
   - `promocja` → **flag** `1`
2. page through the `products` query until `lastPage`, deduping by item id.

`sort` and `f.<id>=<value>` filters are taken straight from the URL and passed through
(`f.69=13026` = category Obuwie, `f.95=Obuwie`, …). No `sort=` in the URL → defaults to
`-gross_sell_price`.

### Usage
```bash
uv run python scripts/new_balance/scrape.py --url "https://newbalance.pl/meskie/obuwie"
uv run python scripts/new_balance/scrape.py --url "https://newbalance.pl/promocja?sort=gross_sell_price&f.69=13026&f.95=Obuwie"
```

### CSV columns
| column | meaning |
|---|---|
| `model` | full product name |
| `category` | category path (`categoryPath`), e.g. `Męskie / Obuwie / Piłkarskie` |
| `price_PLN` | current sell price (`sellPrice.gross`) |
| `price_before_discount_PLN` | "Cena pierwsza" (`listPrice`/`basePrice`), if on promo |
| `lowest_30d_PLN` | "Najniższa cena z 30 dni przed obniżką" (`omnibusPrice`, EU Omnibus) |
| `discount_%` | `round((base − sell) / base × 100)` — same formula the site's badge uses |
| `is_best_30d` | `True` if today's price ≤ the 30-day low. Filled only when `lowest_30d` ≠ `price_before_discount` |
| `vs_lowest_30d_%` | today vs the 30-day low, signed (`-13` = 13% cheaper, `+50` = 50% pricier). Same fill condition |
| `sizes_in_stock` | JSON `{size: qty}` for in-stock sizes, e.g. `{"41.5 Standardowa (D)": 12}` (`variants`: key `option`, value `availability.stock.amount`); stock > 0 only |
| `stock_total` | total pairs in stock across all sizes |
| `url` | product page URL |

`is_best_30d` / `vs_lowest_30d_%` exist to cut through **inflated "before" prices**: a big
`discount_%` off `price_before_discount` can still be *above* the genuine 30-day low.

### Notes discovered along the way
- GraphQL has **no** discount-% field on products — the % is computed client-side.
- GraphQL has **no** demand/liquidity field — that comes from Vinted (below).
- `/promocja` header sometimes shows a stale count (e.g. 1136) vs the live API (1134) —
  the page HTML is CDN-cached; the GraphQL `itemsCount` is authoritative.

---

## 2. Resale-liquidity analysis

Question: of the discounted men's footwear in `/promocja`, what is most liquid to flip?

The promo CSV has **no demand signal** — only prices. So demand was pulled from
**Vinted PL** (`GET /api/v2/catalog/items`, catalog `1231` = Buty męskie, `search_text`
per model), and combined with the discounted buy price.

### Liquid silhouettes present in the sale
`1906` (38), `9060` (14), `2002R` (8), `550 / BB550` (8) — plus running models
`1080 v14`, `860 v14`. The classic `574/327/530` were absent.

### Vinted demand — all conditions
| model | listings | %fav | medFav | med used price | total_entries |
|---|--:|--:|--:|--:|--:|
| 1906 | 288 | 92% | 8 | 308 | 465 |
| 1080 v14 | 161 | 94% | 7 | 288 | 161 |
| 9060 | 288 | 91% | 5 | 400 | 960 (cap) |
| 860 v14 | 154 | 84% | 4 | 184 | 154 |
| 2002R | 288 | 82% | 3 | 259 | 960 (cap) |
| 550 | 288 | 65% | 1 | 129 | 960 (cap) |

Surprise: **550 is the worst** here — iconic but oversupplied (960+ cap), lowest
per-listing demand, cheapest used. "Iconic" ≠ liquid.

### Vinted demand — New With Tags only (`status_ids[]=6`)
This is the honest comparison for flipping *new* pairs. NWT resale prices are far higher.

| model | buy today (newbalance.pl) | cheapest SKU | Vinted NWT median | margin | %fav | medFav |
|---|--:|---|--:|--:|--:|--:|
| **1906** | 370 (−47%) | M1906REF białe | 478 | **+108 (+29%)** | 96% | 13 |
| **2002R** | 390 (−40%) | U200210D szare | 500 | **+110 (+28%)** | 97% | 9 |
| 9060 | 500 (−41%) | U9060EEO czarne | 516 | +16 (+3%) | 94% | 8 |
| 550 | 300 (−50%) | BB550HA1 białe | 320 | +20 (+7%) | 84% | 3 |
| 1080 v14 | 500 (−41%) | M1080B14 czarne | 399 | **−101** | 96% | 9 |
| 860 v14 | 500 (−33%) | M86014D szare | 320 | **−180** | 97% | 8 |

`margin = Vinted NWT median − buy today`. Running models (1080/860) resell *below* their
discounted price → not flippable despite high fav rates.

### Demand velocity (favs/day) — 1906 vs 2002R
Method (per `docs/sneakers.md`): item id = global creation clock. Two site-wide
`newest_first` snapshots 91 s apart → **id-velocity 30.2 ids/s (≈2.6 M/day)**; per-item
age = `(max_id − item_id) / velocity`; `favs/day = favourite_count / age_days`.

| model | n (NWT) | median age | medFav | favs/day (median) | favs/day (trimmed-mean) |
|---|--:|--:|--:|--:|--:|
| **1906** | 184 | 250 d | 12 | **0.05** | **0.09** |
| 2002R | 265 | 391 d | 8 | 0.02 | 0.05 |

1906 accumulates favourites **~2× faster** than 2002R *and* its NWT listings are younger
(250 d vs 391 d) → faster sell-through. The absolute favs/day depends on the measured
id-velocity (30/s now vs ~110/s in `docs/sneakers.md`, varies by time of day), but the
**1906 : 2002R ratio is velocity-independent** and robust.

---

## 3. Verdict

1. **1906** — best overall: top resale demand (96% fav, medFav 13, ~2× faster favs/day)
   and real margin (+29%). Cheapest SKU `M1906REF` at 370 is a *fake* discount
   (`vs_lowest_30d +23%`); for a genuine low + margin take `U1906WFB/WFA` at 400 (`vs −20%`).
2. **2002R** — same margin (+28%), strong demand, but slower turnover. `U200210D szare` at 390.
3. **9060** — great demand, thin margin (buy 500 ≈ resale 516); only worth it below 500.
4. **Avoid 550** (low demand + weak margin) and **1080 v14 / 860 v14** (negative margin — running shoes).

Caveat throughout: Vinted demand uses `favourite_count` as a proxy (not actual sales);
single-snapshot counts; PL market only.
