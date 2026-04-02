# Ski Boots — Additional Analysis

You are evaluating **alpine (downhill) ski boots** for resale. Apply all base rules, plus the following.

> **Scope:** we evaluate **only hard-shell plastic alpine ski boots**.
> If the listing contains cross-country boots, snowboard boots, hiking boots, or any other non-alpine footwear — set rating to **1** and recommendation to **`skip`**, with a `red_flag` explaining the mismatch.
> Photos may include bonus items (skis, helmets, poles, etc.) — that is a `green_flag`, but we still evaluate **only the boots**.

---

## 1. Identification

| Field             | How to determine                                          |
| ----------------- | --------------------------------------------------------- |
| **Brand & Model** | Full name from shell markings or buckle engravings        |
| **Series**        | Piste / Race / Freeride / Junior / Touring                |
| **Season**        | Approximate year/season (e.g. "2022/2023")                |
| **Flex index**    | From model name or visible markings; map to level (below) |

**Flex-to-level mapping:**

| Level           | Flex range |
| --------------- | :--------: |
| Beginner        |   60–80    |
| Intermediate    |   80–100   |
| Advanced/Expert |  100–130   |
| Race            |    130+    |

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

| Age        | Action                                                                 |
| ---------- | ---------------------------------------------------------------------- |
| > 10 years | Unsafe, unsellable → set `safety_warning`                              |
| 6–10 years | Reduced value, flag risk                                               |
| Unknown    | `"safety_warning": "age unknown — inspect PU integrity before resale"` |

> PU (polyurethane) degrades over time — always estimate age when possible.

---

## 3. Target Sizes (Liquidity)

Sizes within these ranges sell fastest:

| Category | Mondo (cm) | EU size |
| -------- | :--------: | :-----: |
| Junior   |   ≥ 19.0   |   30+   |
| Women    | 24.0–25.5  |  38–40  |
| Men      | 27.0–28.5  |  42–44  |

- Sizes **outside** these ranges sell slower → rating **−1**.
- **Extreme** sizes (Junior < 18.5 cm / Men > 29.5 cm) → rating **−2**.

---

## 4. Rating Modifiers

### Downgrade (−1 to −2 stars)

| # | Condition                   | Modifier |
| - | --------------------------- | :------: |
| 1 | Rental boots detected       |    −2    |
| 2 | Visible rust on bolts       |    −1    |
| 3 | Size outside target range   |    −1    |
| 4 | No sole photos available    |    −1    |
| 5 | Boots older than 10 seasons |    −1    |

### Upgrade (+1 star)

| # | Condition                                                                |
| - | ------------------------------------------------------------------------ |
| 1 | Original box visible in photos                                           |
| 2 | GripWalk sole system                                                     |
| 3 | Target size (see section 3)                                              |
| 4 | Top resale brand: **Salomon, Atomic, Head, Rossignol, Nordica, Fischer** |

> **Note:** every condition that triggers an upgrade should also be added to `green_flags` in the response.

---

## 5. Resale Value Estimation

Estimate resale value based on brand reputation, model tier, condition, age, and size liquidity.
Higher-tier models from top brands in target sizes command premium prices;
older boots and off-sizes sell at significant discounts.

---

## 6. Additional JSON Fields

Add these fields to the base response:

```json
{
  "flex_index": "... or null",
  "mondo_size": "... or null",
  "eu_size": "... or null",
  "is_rental": false,
  "estimated_age_years": "...",
  "safety_warning": "... or null"
}
```

| Field                 | Description                                                |
| --------------------- | ---------------------------------------------------------- |
| `flex_index`          | Flex value from model name or markings; `null` if unknown  |
| `mondo_size`          | Mondopoint size in cm; `null` if unknown                   |
| `eu_size`             | EU size (e.g. 38, 42); `null` if unknown                   |
| `is_rental`           | `true` if rental signs detected                            |
| `estimated_age_years` | Approximate age in years                                   |
| `safety_warning`      | PU degradation warning; `null` if boots are < 6 years old  |
