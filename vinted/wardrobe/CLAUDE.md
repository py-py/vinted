# vinted.wardrobe

Monitors a public Vinted member's wardrobe: syncs items to Firestore and
detects new / reserved / sold / deleted listings between runs. Full design
and verified markers: `PLAN.md`.

Run: `make wardrobe MEMBER=<id>` or `python -m vinted.wardrobe <id> [--no-save]`
(`MEMBER`, not `USER` — the shell owns `USER`).

## Firestore

- Collection is `wardrobes` (plural): `wardrobes/{user_id}` and
  `wardrobes/{user_id}/items/{item_id}`. Firestore needs the `items`
  subcollection — `wardrobes/{user_id}/{item_id}` is not a valid doc path.
- Vinted data lives in the `api` map; our fields (`state`, `listed_at`,
  `created_at`, `updated_at`, `last_seen_at`, `gone_at`) at the top level.
  Keep that split when adding fields.
- `save_wardrobe` uses `set(merge=[fields])` so each written field (incl. the
  whole `api` map) is replaced, not deep-merged.
- `updated_at` moves only on a real change; `last_seen_at` / `last_fetched_at`
  move every run.

## Vinted API facts (anonymous, verified 2026-11-10)

- `GET /api/v2/wardrobe/{id}/items` needs no token — only the session cookies
  from first opening `/member/{id}`. `per_page` max is 96.
- Returns active items only; sold and reserved items silently disappear.
- No created date anywhere: `listed_at` = min `photos[].high_resolution.timestamp`
  (tracks item id order on 360 items).
- `view_count` is always 0 without cookies — don't rely on it.
- `/api/v2/items/{id}` is 404 and `/details` 403 anonymously; use the HTML
  item page (`PRODUCT_URL`) instead.

## Item page markers (`status.py`)

Page data is JSON-escaped Next.js flight data — unescape `\"` before matching.

- `buyer_item_status` plugin title `Sprzedane` → sold; `Zarezerwowane` → reserved
- `is_reserved: true` → reserved
- `availability: InStock` → active
- HTTP 404 → deleted; other HTTP errors keep the saved state (re-check next run)
- `can_buy` is NOT a signal: it is `true` on reserved items.

Reference items: 10720963834 (sold), 10723152138 (reserved, member
282635132), 10747201625 (active). Hidden items are unverified → `unknown`.
