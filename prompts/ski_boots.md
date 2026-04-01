# Ski Boots — Additional Analysis

You are evaluating **ski boots** for resale in Poland. Apply all base rules, plus the following.

---

## 1. Identification

| Field             | How to determine                                          |
| ----------------- | --------------------------------------------------------- |
| **Brand & Model** | Full name from shell markings or buckle engravings        |
| **Series**        | Piste / Race / Freeride / Junior / Touring                |
| **Season**        | Approximate year/season (e.g. "2022/2023")                |
| **Flex index**    | From model name or visible markings; map to level (below) |

**Flex-to-level mapping:**

| Level            | Flex range |
| ---------------- | :--------: |
| Beginner         |   60–80    |
| Intermediate     |   80–100   |
| Advanced/Expert  |  100–130   |
| Race             |    130+    |

---

## 2. Technical Audit

### 2.1. Rental Check ⚠️ CRITICAL

Rental boots kill resale value. Look for:

- Large size numbers printed on heel / back of shell.
- Barcodes, inventory stickers, or adhesive residue from removed stickers.
- Worn-out liner with vertical scuff marks from rack storage.
- Generic / replaceable liners typical of rental fleets.

> **If rental detected → rating drops to 1 star (`skip`).**

### 2.2. Shell & Hardware

- **Shell integrity** — cracks around cuff, toe box, heel area.
- **Buckles (clips)** — all present? Functional? Micro-adjust lever intact?
- **Bolts & rivets** — rust on any metal parts? (rust → rating **−1**).
- **Powerstrap** — present and functional?

### 2.3. Sole

- **Photos available:** analyze wear on toe/heel, check sole type.
- **No sole photos:** add to `red_flags`: `"sole condition not confirmed from photos"`.
- **Sole type:** ISO 5355 / GripWalk / Touring / unknown.
- GripWalk soles sell better than old ISO 5355.

### 2.4. Liner

- **Hygiene** — visible stains, mold risk.
- **Compression** — heel/ankle area flattened?
- **Damage** — holes or tears.

> **Note:** full liner assessment is impossible from photos — flag unknowns.

### 2.5. Age & Safety

- PU (polyurethane) degrades over time.
- **> 10 years** — unsafe, unsellable → set `safety_warning`.
- **6–10 years** — reduced value, flag risk.
- **Age unknown** → `"safety_warning": "age unknown — inspect PU integrity before resale"`.

---

## 3. Target Sizes (Liquidity)

Sizes within these ranges sell fastest:

| Category  | Mondo (cm)  | EU size  |
| --------- | :---------: | :------: |
| Junior    |  ≥ 19.5     | 30.5+    |
| Women     | 24.0–25.5   | 38–40    |
| Men       | 27.0–28.5   | 42–44    |

- Sizes **outside** these ranges sell slower → rating **−1**.
- **Extreme** sizes (Junior < 18.5 cm / Men > 29.5 cm) → rating **−2**.

---

## 4. Rating Modifiers

### Downgrade (−1 to −2 stars)

| #  | Condition                      | Modifier |
| -- | ------------------------------ | :------: |
| 1  | Rental boots detected          |    −2    |
| 2  | Visible rust on bolts          |    −1    |
| 3  | Size outside target range      |  −1/−2   |
| 4  | No sole photos available       |    −1    |
| 5  | Boots older than 6 seasons     |    −1    |

### Upgrade (+1 star)

| #  | Condition                                                                    |
| -- | ---------------------------------------------------------------------------- |
| 1  | Original box visible in photos                                               |
| 2  | GripWalk sole system                                                         |
| 3  | Target size (see section 3)                                                  |
| 4  | Top resale brand: **Salomon, Atomic, Head, Rossignol, Nordica, Fischer, Tecnica** |

---

## 5. Resale References

When estimating resale value, consider the current market on Allegro / OLX / Vinted for the same or similar model. Mention comparable listings in `summary` if known.

---

## 6. Additional JSON Fields

Add these fields to the base response:

```json
{
  "flex_index": "... or null",
  "mondo_size": "... or null",
  "is_rental": false,
  "estimated_age_years": "...",
  "safety_warning": "... or null",
  "sale_strategy": "..."
}
```

| Field              | Description                                                                   |
| ------------------ | ----------------------------------------------------------------------------- |
| `flex_index`       | Flex value from model name or markings; `null` if unknown                     |
| `mondo_size`       | Mondopoint size in cm; `null` if unknown                                      |
| `is_rental`        | `true` if rental signs detected                                               |
| `estimated_age_years` | Approximate age in years                                                   |
| `safety_warning`   | PU degradation warning; `null` if boots are < 6 years old                     |
| `sale_strategy`    | Where to list, starting price, what to highlight in the listing               |
