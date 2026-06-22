# New Balance (newbalance.pl) — resale-liquidity analysis, 2026-06-22

Fresh snapshot of the same analysis as `new_balance.md` (which has the full scraper
write-up and method). Discounted men's footwear in `/promocja` vs Vinted PL demand, to
judge what's worth buying to flip. Captured **2026-06-22** (morning).

Scraper unchanged — see `new_balance.md §1`. Today's CSVs:
`media/newbalance_promocja.csv` (1059 rows), `…_meskie_obuwie.csv`, `…_damskie_obuwie.csv`.

---

## 1. What's in the sale today

Of 1059 promo items, **359 are men's footwear** (`category` starts `Męskie / Obuwie`).
Liquid silhouettes present, with their genuine-low check (`vs_lowest_30d_%` — today vs the
EU-Omnibus 30-day low; negative = real low, positive = inflated "before" price):

| silhouette | SKUs on sale | min price | med price | med discount | med vs 30d-low |
|---|--:|--:|--:|--:|--:|
| **1906R** | 18 | 400 | 470 | −38% | **−12%** (real) |
| **1906** | 15 | 400 | 430 | −39% | **−20%** (real) |
| 9060 | 10 | 500 | 550 | −31% | **+25%** (inflated) |
| 327 | 10 | 300 | 335 | −37% | **+30%** (inflated) |
| 550 | 7 | 300 | 400 | −33% | −11% (real) |
| 1080 v14 | 5 | 590 | 590 | −31% | — |
| 860 v14 | 2 | 500 | 500 | −33% | — |

**Change vs the 2026-06-19 snapshot:** **2002R is gone** from the men's sale (it was a top
pick three days ago). **1906R** now has the deepest discount presence (18 SKUs) and **327**
has appeared. The 1906 family (1906 + 1906R = 33 SKUs) dominates the discounted shelf.

The `vs_lowest_30d_%` column matters: **9060 and 327 show big headline discounts off an
inflated "before" price** — today's 9060 (500) sits **+25%** above its real 30-day low (400)
and 327 (300) is **+30%** above its 30-day low (230). The 1906/1906R discounts are genuine.

---

## 2. Vinted PL demand (catalog `1231` = Buty męskie, `search_text` per model)

### All conditions
| model | listings (cap 960) | %fav | medFav | med used price |
|---|--:|--:|--:|--:|
| 1906 | 467 | 92% | 9 | 300 |
| 1906R | 563 | 92% | 7 | 292 |
| 9060 | 960 (cap) | 89% | 5 | 410 |
| 327 | 610 | 89% | 4.5 | 200 |
| 550 | 960 (cap) | **63%** | **1.5** | 120 |
| 1080 v14 | 169 | 94% | 7 | 280 |
| 860 v14 | 154 | 84% | 4 | 184 |

Same story as last time: **550 is the worst** — oversupplied (960+ cap), lowest per-listing
demand (63% fav, medFav 1.5), cheapest used. Iconic ≠ liquid.

### New With Tags only (`status_ids[]=6`) — the honest comparison for flipping new pairs
| model | buy today (newbalance.pl) | cheapest genuine-low SKU | Vinted NWT median | margin | %fav | medFav |
|---|--:|---|--:|--:|--:|--:|
| **1906** | 400 (−20% vs 30d-low) | U1906WFB / U1906WFA | 479 | **+79 (+20%)** | 98% | 14 |
| **1906R** | 400 (−15% vs 30d-low) | U1906RCT / U1906RCU | 471 | **+71 (+18%)** | 98% | 13 |
| 9060 | 550 (no real low) | U906029M szare | 510 | **−40** | 93% | 8 |
| 327 | 300 (+30% — fake low) | U327WRB beżowe | 330 | +30 nominal | 95% | 7.5 |
| 550 | 300 (−50%) | BB550WT1 białe | 320 | +20 (+7%) | 84% | 3 |
| 1080 v14 | 590 | M1080J14 zielone | 390 | **−200** | 95% | 9 |
| 860 v14 | 500 | M86014D szare | 320 | **−180** | 96% | 7 |

`margin = Vinted NWT median − buy today`. Running models (1080/860) resell *far* below their
discounted price → not flippable despite high fav rates. 9060's cheapest genuine buy (~550,
since the 500 SKU is +25% over its 30-day low) now sits *above* its NWT resale median → the
thin 06-19 margin has flipped negative. 327's "−50%" is off an inflated before-price (real
30-day low 230), so the +30 nominal margin is illusory — you can buy 327 cheaper off-sale.

## 3. Demand velocity (favs/day) — 1906 vs 1906R

Method per `docs/sneakers.md`: item `id` as a global creation clock. Two site-wide
`newest_first` snapshots **92 s apart → id-velocity 104.6 ids/s (≈9.0 M/day)**; per-item
age = `(max_id − item_id) / velocity`; ages capped at the 95th pct; `favs/day =
favourite_count / age_days`.

| model | n (NWT) | median age | medFav | favs/day (median) | favs/day (trimmed-mean) |
|---|--:|--:|--:|--:|--:|
| **1906** | 184 | 67 d | 13 | 0.17 | 0.30 |
| **1906R** | 179 | 67 d | 13 | 0.18 | 0.30 |
| 9060 | 266 | 28 d | 8 | 0.28 | 0.56 |

1906 and 1906R are **statistical twins** today — same age profile (67 d), same medFav (13),
same favs/day. Both are the top of the NB demand curve (98% fav). 9060 shows a *higher*
favs/day, but that's the known artifact: its NWT listings are mechanically younger (28 d),
which inflates the velocity ratio — the **age-robust** signals (%fav, medFav) still put
1906/1906R ahead. (Absolute favs/day scales with the measured id-velocity: 104/s now vs 30/s
on 06-19, so the day-numbers aren't comparable across snapshots — the *ratios within a
snapshot* are.)

---

## 4. Which size & colour — the margin lives here

The scraper now emits `sizes_in_stock` (a `{size: qty}` JSON map) and `stock_total` per SKU
(see `new_balance.md §1`). Crossing **remaining retail stock per size** with **Vinted NWT
supply/price per size** is where the real edge shows up — the model-average margin (+18–20%)
hides a wide spread.

### By size (Vinted NWT, 1906 + 1906R; size from `size_title`)
| EU size band | Vinted listings | Vinted med price | retail stock left | margin from 400 |
|---|--:|--:|---|--:|
| 42–44 (core) | **26–38** (crowded) | 429–499 | still plenty | +30…+100 (+8–25%) |
| **45** | 15–18 (thin) | 547–576 | thinning | **+147…+176 (+37–44%)** |
| **45.5 / 46.5 / 47.5** | 1–5 (very thin) | 550–560 | nearly gone | **+150…+160** |
| 36–37 (tiny) | 1–2 | mixed | low | low — low stock = low demand, not scarcity |

Big feet are chronically undersupplied: large sizes carry the **highest resale price**,
the **thinnest Vinted competition**, and retail 45+ is vanishing first (won't restock after
the promo). The crowded **core 42–44** still flips, but at +10% against dozens of competing
sellers. **Tiny sizes with low stock are a trap** — the stock is low because demand is, not
because they're selling out.

### By colour (Vinted NWT, 1906 + 1906R; colour parsed from title — directional, small-n)
| colour | listings | medFav | med price | read |
|---|--:|--:|--:|---|
| **black** | 14 / 11 | 16–17 | 455–494 | most-listed + 100% fav → **fastest, most predictable turnover** |
| pink | 9 / 8 | 10–14 | 430–449 | also liquid, demand/price a notch lower |
| **grey** | 4 / 3 | 27–30 | **638–699** | thin on Vinted but **abundant in the sale** → arbitrage (unproven, n=3–4) |
| white | 2–3 | 15 | 560–592 | scarce + dear |
| **blue** | 3 / 3 | **4** | **320** | weakest demand, cheapest — avoid |
| beige/brown | 1–2 | — | 280–407 | too few to read |

**Black is the most *liquid* colour** (highest supply at 100% fav, steady medFav 16–17) —
the safe fast flip. **Blue is the worst** colour bucket.

**Grey — a potential reverse arbitrage, not a scarce niche.** Its 3–4 Vinted listings at
638–699 look "scarce + dear," but that thinness is *Vinted-side only*: grey is in fact the
**most-stocked colour in the sale** — 11 SKUs, retail stock up to 466 pairs, deep in large
sizes. So the play is buy-cheap-and-deep at retail ↔ sell-thin-and-dear on Vinted. **If** the
638–699 holds, margin from a ~450–470 genuine-low grey would be +170–250 (+40–55%) — above
black. **But** it rides on n=3–4 Vinted listings, so both the price and the medFav 27–30 may
be noise from a single optimistic seller. Treat grey as a high-upside *bet*, not a confirmed
flip like black. Genuine-low greys with deep large sizes: **U1906RNG** (469.99, `vs −6%`,
45×6 / 45.5×4 / 46.5×3, 110 pairs) and **U1906RCR** (449.99, `vs −10%`, 45×4).

Caveat: colour buckets are 1–14 items each, parsed by keyword from user-written titles —
treat as direction, not precise numbers.

### Actionable buys (genuine-low ~400, large size in stock, 2026-06-22)
| SKU | colour | price | big-size stock (45+) | verdict |
|---|---|--:|---|---|
| **U1906RCT** | czarne (black) | 399.99 (−15%) | 45×3, 45.5×5 | ✅ best — liquid colour + large sizes |
| **U1906RCU** | czarne (black) | 399.99 (−15%) | 45×4 | ✅ same, shallower |
| **U1906WFA** | różowe (pink) | 399.99 (−20%) | 45×7, 45.5×6, 47.5×2 | ✅ deepest large-size stock (Σ=15); colour 2nd-tier |
| **U1906RNG** | szare (grey) | 469.99 (−6%) | 45×6, 45.5×4, 46.5×3 | 🎲 arbitrage bet — Vinted-dear (638–699) but n=3–4 |
| U1906RCR | szare (grey) | 449.99 (−10%) | 45×4, 45.5×1 | 🎲 same bet, shallower |
| U1906WFB | zielone (green) | 399.99 (−20%) | 45.5×3 | ❓ green absent from Vinted buckets — unverified |
| U1906RNE / RND | niebieskie/żółte | 429.99 (−14%) | 45×1 | ⚠️ skip — blue is the weakest colour, thin stock |

## 5. Verdict

1. **1906 / 1906R** — the only clean flip. Top resale demand (98% fav, medFav 13, identical
   favs/day) and a **genuine** ~400 discount. The margin is in the **size**: buy **45+** where
   resale runs 547–576 (**+37–44%**), not the crowded core (+10%). Best SKUs: **U1906RCT /
   U1906RCU** (black — most liquid colour) and **U1906WFA** (deepest large-size stock).
2. **Grey — high-upside bet, not a sure thing.** Most-stocked colour in the sale yet thin
   on Vinted (n=3–4) at 638–699 → if that price holds, a ~450–470 genuine-low grey
   (**U1906RNG**, **U1906RCR**) clears +40–55%, above black. But the price rides on a 3–4
   listing sample — size a small position, not your core buy.
3. **Skip blue/yellow** colourways (U1906RNE/RND) even at genuine-low — blue is the weakest
   resale colour (medFav 4, ~320). Green (U1906WFB) is unverified — too few Vinted listings.
4. **9060** — skip. The 500 SKU is +25% over its 30-day low; the genuine buy (~550) now
   exceeds its NWT resale median (510). Margin gone since 06-19.
5. **327** — skip. The "−50%" is off an inflated before-price (real low 230, today 300);
   demand only mid (medFav 4.5 all-cond), NWT margin illusory.
6. **Avoid 550** (oversupplied, 63% fav, medFav 1.5) and **1080 v14 / 860 v14** (negative
   margin — running shoes resell far below the discounted buy price).

**Bottom line:** buy 1906/1906R in **large sizes (45+)**, **black first** then pink-for-size;
take a small grey position as an upside bet (U1906RNG/RCR); skip blue/yellow. Everything else
is fake-discount, oversupplied, or underwater. With 2002R cleared out, there's no second-tier
silhouette this week.

Caveats: Vinted demand uses `favourite_count` as a proxy, not actual sales (prices are
*asking*, not sold); single-snapshot counts; `search_text` token-matches so "1906" partially
overlaps "1906R"; size/colour parsed from `size_title`/title (colour buckets are small-n,
directional); PL market only.

---

## 6. Buy-now vs wait — across the whole men's line

There is **no sales feed** — neither Vinted nor newbalance.pl exposes units sold (the site's
GraphQL silently ignores any `sort=bestseller/popularity/sold` string and falls back to its
default merchandising order, which isn't a confirmed sales rank). The workable proxy is
**Vinted demand (favourite_count) × the genuine-discount state across the *full* men's
footwear catalog** (`media/newbalance_meskie_obuwie.csv`, not just `/promocja`). For each
model: demand from Vinted NWT, and `genuine-low %` = share of catalog SKUs currently priced
*below* their EU-Omnibus 30-day low (`vs_lowest_30d_% < 0`).

Buy price = cheapest **genuine-low** SKU in the catalog (its real deal); sell = Vinted NWT
median; profit = sell − buy (`*` = no genuine 30-day low exists, so buy is the current/fake
price and the "profit" is illusory or unstable).

| model | demand (%fav / medFav) | buy PLN | sell PLN | **profit** | genuine-low | action |
|---|---|--:|--:|--:|--:|---|
| 2002R | 82% / 3 | 400 | 494 | **+94 (+24%)** | 10% | 🍒 highest margin, but thin supply |
| **1906** | 98% / 13 | 400 | 479 | **+79 (+20%)** | 5% | 🍒 buy **only the −20% SKUs** (most at full 600) |
| **1906R** | 98% / 13 | 400 | 471 | **+71 (+18%)** | **45%** | ✅ **core buy** — real deals + top demand |
| **574** | 85% / 3 | 250 | 320 | **+70 (+28%)** | 24% | ✅ cheap volume, best %-margin |
| 327 | 95% / 7 | 300* | 330 | +30* | 4% | ⏳ discount fake (+30 vs 30d) — wait |
| **1000** | 95% / 7 | 400–450 | 415 | **+15…−35** | 43% | ⚠️ resale ≈ buy → thin/negative (see below) |
| 530 | 90% / 4 | 370* | 389 | +19* | 0% | ⏳ wait — fake/full price |
| 9060 | 89% / 8 | 500* | 500 | **±0*** | **0%** | ⏳ **wait** — all discounts fake, sub-450 |
| 550 | 84% / 3 | 400 | 320 | **−80** | 14% | ❌ weak demand, underwater at a real deal |
| 990 | premium | 1100* | — | — | 0% | full price (never discounts) |
| 1080 / 860 | running | 590 / 500 | 390 / 320 | **−200 / −180** | ~0–7% | ❌ negative margin |

### The 1000 — high demand, real discounts, but the margin isn't there
`New Balance 1000` is a genuine Y2K-retro line (Metallic / Triple Black / Castlerock), **not**
noise: of 182 NWT listings, 95 are real 1000s once bare-"New Balance"/204L/990/2002R hits are
dropped → **95% fav, medFav 7, NWT median 415**. Demand survives the clean-up, and the catalog
has **42 SKUs, 43% genuine-low** — far more real discounting than 1906.

**But the absolute numbers kill it:** resale median is only **415** while almost every
genuine-low 1000 sits at **449.99** → that's a **−35 loss**. The lone sub-resale deal is
`M1000S multikolor` at 399.99 (`vs −20%`) → **+15**, and even that has just 45.5×1 in large
sizes. So 1000 is the cautionary case for *why absolute margin beats discount %*: lots of
real discounts, strong favs, yet you buy at ~the price you'd resell at. **Skip as a flip**
(it's a fine wear-it buy). Best resale colour, if you do, is grey (medFav 14) — but grey
genuine-low SKUs carry little 45+ stock; the deep-large-size deal `M1000N` is niche gold.

### Takeaway
Ranked by **absolute profit**, not discount %:
- **Buy now:** **1906R** (400→471, +71, and 45% of SKUs are real deals — the core buy);
  cherry-pick the **−20% 1906** SKUs (400→479, +79) and any genuine-low **2002R** (400→494,
  **+94**, the fattest margin but only 10% on real sale); **574** for cheap volume (250→320,
  +70 / +28%). Push all of these into **large sizes (45+)**, where resale runs well above the
  medians (see §4) — that's where the +70–94 becomes +150+.
- **Skip despite the hype/discount:** **1000** — 43% genuine-low and strong favs, but
  buy ≈ resale (450 vs 415) → ~break-even to −35. Real discounts ≠ profit.
- **Wait for a real drop:** **9060** is the textbook case — top resale value (NWT 500) but
  every current "−31/−41%" is fake (+25% over its 30-day low, 0% genuine-low across 26 SKUs),
  so today's margin is ±0. Wait until it prints below ~450. **530** is mostly full-price too.
- **Never discounts:** 990 (premium, full 1150) — buy only to wear, not flip.

---

## 7. Worked example — a 2000 PLN basket (2026-06-22)

What to actually buy with a fixed budget. Two rules from the analysis above: **(a)** only
1906/1906R (the only clean flips today); **(b)** the margin is in the **size**, but not *any*
large size.

### Size: the sweet spot is 44.5–45, not bigger
Resale price keeps rising past 45, but the buyer pool collapses — 45.5/46.5/47.5 have only
1–5 Vinted listings each, so a pair can sit unsold despite the high asking price (thin market
≠ liquidity). **44.5–45** is the zone: premium price *and* a real active market.

| size band | Vinted listings (1906/1906R) | medFav | med price | read |
|---|--:|--:|--:|---|
| 42–44 (core) | 26–38 | 9–13 | 429–499 | crowded, lower price |
| **44.5** | 12–17 | 9–12 | 493–500 | ✅ large + liquid |
| **45** | 15–18 | 10–15 | 547–576 | ✅ best balance — premium + active market |
| 45.5 | 3 | 10–15 | 550–560 | thin |
| 46.5 / 47.5 | 1–5 | — | 453–560 | ⚠️ dear but almost no buyers — avoid |

### The basket — 4 pairs, ~1670 PLN (keep ~330 for fees/shipping)
| # | SKU | colour | size | buy | resale (est.) | profit |
|---|---|---|---|--:|--:|--:|
| 1 | **U1906RCT** | black | **45** | 400 | ~550 | +150 |
| 2 | **U1906RCU** | black | **44.5** | 400 | ~500 | +100 |
| 3 | **U1906WFA** | pink | **45** | 400 | ~520 | +120 |
| 4 | **U1906RNG** | grey | **45** | 470 | 550+? | +80…+170 (upside bet) |

Stock present: RCT `45×3`, RCU `44.5×8`, WFA `45×7`, RNG `45×6`. Links in §4 / the SKU list.

**Rationale:** 3 safe pairs across distinct colourways (so you don't compete with yourself on
Vinted) + 1 grey as the high-upside bet (§4); all in the 44.5–45 band; black leads (most
liquid colour). Expected gross ≈ **+450…+540** before Vinted fees/shipping. Safer variant:
drop the grey, take a 4th black/pink pair at 45 → whole basket in the most-liquid colours.

Caveats as in §5–6: gross profit, NWT asking prices not sales, ~weeks-to-months turnover
(median NWT listing age ~67 d), live stock — re-check sizes before paying.
