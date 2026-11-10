# Wardrobe monitor

Status: implemented (`sync.py`, `status.py`, `api.py`).

Track a public member's wardrobe in Firestore and detect new, sold and deleted
listings between fetches.

## Firestore layout

Firestore paths alternate collection/document, so items live in a subcollection:

```
wardrobes/{user_id}                 -> member doc
wardrobes/{user_id}/items/{item_id} -> item doc
```

Both docs keep Vinted data and our own data apart: everything from the API
sits in an `api` map (overwritten as a whole on each fetch), everything we
compute or track sits at the top level.

Item doc:

```
{
  "api": {                        # from the wardrobe API, replaced each fetch
    "id", "title", "url", "price", "brand", "size",
    "status",                     # condition, e.g. "Bardzo dobry"
    "photo_urls",
    "favourite_count", "view_count"   # view_count is always 0 anonymously
  },
  "listed_at":    min(api photos[].high_resolution.timestamp), derived by us
  "state":        "active" | "reserved" | "sold" | "deleted" | "unknown",
  "created_at":   first time we saved the item
  "updated_at":   last time `api` or `state` actually changed
  "last_seen_at": last fetch the item was present in
  "gone_at":      first fetch the item was missing (null while active)
}
```

Member doc:

```
{
  "api":             {"user_id", "login"},
  "created_at":      first sync
  "updated_at":      last sync that changed anything
  "last_fetched_at": last sync
  "active_count":    items with state == active
}
```

`updated_at` moves only on a real change (diff of the `api` map or a `state`
transition); `last_seen_at` / `last_fetched_at` move every run.

### Why `listed_at` from photo timestamps

The wardrobe API has no `created_at`, and `/api/v2/items/{id}/details` is 403
without cookies. Checked on member 183486796 (360 items): photo timestamps rise
with item id (2 inversions out of 359 pairs), and all photos of an item share
the same timestamp in 349/360 items — a reliable proxy for creation time.
Replacing photos later may shift it (untested).

## API facts

- `GET /api/v2/wardrobe/{user_id}/items?page=N&per_page=96` — anonymous, needs
  only the session cookies from first opening `/member/{user_id}`.
- `per_page` max is **96** (larger values are capped).
- Returns active items only: `is_closed`, `is_reserved`, `is_hidden` were all
  `false` and `item_closing_action` was `null` for all 360 items. Reserved
  items are excluded too (10723152138 of member 282635132 was missing).
- `view_count` is `0` for every item without cookies — not usable.

## Sync algorithm — `sync_wardrobe(user_id)`

1. Fetch all pages (`per_page=96`).
2. Load saved items with `state in (active, reserved, unknown)` — reserved
   and unknown are re-checked every run until they settle.
3. Diff:
   - **new** (in fetch, not saved) → create, `state=active`,
     `created_at = updated_at = last_seen_at = now`.
   - **still active** → replace `api`, set `last_seen_at`; bump `updated_at`
     only if `api` differs from the saved one.
   - **missing** (saved active/reserved/unknown, not in fetch) → status
     check (step 4).
   - **reappeared** (saved non-active, back in fetch) → `state=active`,
     clear `gone_at`, bump `updated_at`.
4. Status check for each missing item via the public item page (`PRODUCT_URL`):
   Checks in this order:
   - 404 → `deleted`
   - `buyer_item_status` plugin `title: "Sprzedane"` → `sold`
   - `buyer_item_status` plugin `title: "Zarezerwowane"` (or
     `is_reserved: true`) → `reserved`
   - `availability: InStock` → `active` (still listed, missed by the fetch)
   - otherwise (hidden/…) → `unknown`

   `can_buy` is **not** a signal: it is `true` on reserved items.

   Markers verified 2026-11-10:

   | | sold 10720963834 | reserved 10723152138 | active 10747201625 |
   |---|---|---|---|
   | `buyer_item_status` | `Sprzedane` / `SUCCESS` | `Zarezerwowane` / `AMPLIFIED` | — |
   | `is_reserved` | false | true | false |
   | `can_buy` | false | true | true |
   | `availability` | — | — | `InStock` |
   | in wardrobe API | no | no | yes |

   1072096380 → 404.

   On a state change: set `gone_at` (if not set), bump `updated_at`.
5. Write everything in one Firestore batch; update the parent doc.
6. Return a summary `{new, reserved, sold, deleted}` for logging / Telegram later
   (`vinted/telegram.py`).

## Code

- `api.py` — `fetch_wardrobe`, `parse_item` (the `api` map), `listed_at`.
- `status.py` — `check_item_state` / `parse_item_state` (item page markers).
- `models.py` — `ItemState`, `OPEN_STATES`.
- `sync.py` — `diff_fetched`, `apply_state`, `member_doc`, `sync_wardrobe`.
- `vinted/storage/firestore.py` — `get_wardrobe_member`,
  `load_wardrobe_items`, `save_wardrobe` (field-level replace, batches of 400).
- `__main__.py` — `python -m vinted.wardrobe <user_id> [--no-save]`.
- `Makefile` — `make wardrobe MEMBER=<id>` (`USER` is taken by the shell).
- `tests/` — parsing, page markers, diff logic.

## Open points

- **Scheduling** — manual / `make` for now; cron or Cloud Scheduler later.
- **Hidden items** also vanish from the wardrobe; no example yet, so they
  fall into `unknown`.
