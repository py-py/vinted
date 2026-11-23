# vinted.account.purchases

Syncs my purchased orders to Firestore `purchases/{tx}` + `items/{item_id}`.
Sales (`vinted.account.sales`) reuses the escrow/transaction fetchers from
`api.py`, so an endpoint change here breaks both.

Run: `make purchases` (part of `make sync`); tests: `pytest vinted/account`.
Auth: session cookies from `cookies.json`; on 401 refresh them
(`vinted-refresh-cookies` skill).

## Vinted API endpoints (verified 2026-11-23)

Defined in `vinted/constants.py` (`ESCROW_ORDERS_URL`, `ESCROW_ORDER_URL`,
`ESCROW_ITEMS_URL`, `TRANSACTION_URL`).

| Purpose | URL |
|---|---|
| Order list (`type=purchased`/`sold`) | `api.vinted.pl/escrow-orders/api/v2/current-user/escrow-orders` |
| Payment breakdown + totals | `api.vinted.pl/escrow-orders/api/v2/escrow-orders/{tx}` |
| Item ids/titles | `www.vinted.pl/api/v2/escrow_orders/{tx}/items` |
| Photos/url/catalog/size/condition + seller | `www.vinted.pl/api/v2/transactions/{tx}` |

- 2026-11: `www.vinted.pl/api/v2/my_orders` and `.../escrow_orders/{tx}`
  started returning 404. The `api.vinted.pl` replacements return the same
  fields and values (verified against recorded fixtures before replacing them).
- `current-user/escrow-orders/{tx}` (detail under `current-user`) is 404 —
  the detail URL has no `current-user` segment.
- `api.vinted.pl` returns an HTML page instead of JSON unless the request
  sends `Accept: application/json, text/plain, */*` and follows redirects —
  use the same client setup as `fetch_orders`.
- List entries no longer have `photo`; the thumbnail is top-level `photo_url`.
  New fields: `escrow_order_id` (= `transaction_id`), `escrow_order_uuid`.
- If an endpoint 404s, probe candidates with the real cookies + headers
  before changing code, and check that the response shape matches
  `build_order`'s reads (`payment_data.*`, `total_price`, `purchase_id`, …).

## Fixtures

`tests/fixtures/` holds real responses for bundle tx 22646003889. When an
endpoint moves, re-capture the same tx from the new URL, overwrite the
fixture (scrub buyer/seller `login` + `photo_url`) and update the test
docstring's capture note. Don't keep old and new copies side by side.
