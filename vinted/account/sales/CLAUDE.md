# vinted.account.sales

Syncs my sold orders to Firestore `sales/{tx}` + `items/{item_id}`.

Run: `make sales` (part of `make sync`); tests: `pytest vinted/account`.
Auth: session cookies from `cookies.json`, same as purchases.

## Vinted API

Endpoints live in `vinted/constants.py` and are shared with purchases; URLs,
moves and request quirks are in `../purchases/CLAUDE.md`. Per sale:

- `ESCROW_ORDERS_URL?type=sold` → list of sold orders (paginated, same shape
  as purchases).
- `ESCROW_ORDER_URL` → items price + shipment.
- `ESCROW_ITEMS_URL` → item ids/titles (kept for deleted listings).
- `TRANSACTION_URL` → per-item listed price/photos/url + buyer.

## Facts

- Vinted deletes old sold listings (~3 months); `transactions/{tx}` then
  returns `order.items: []`, so escrow items are the source of truth for the
  item list.
- Vinted does not return a per-item sold price (escrow items have it null),
  so for bundles `items_price` is split across items proportionally to
  `listed_price` (`allocate_sold_prices`; rounding remainder on the last item).

## Fixtures

`tests/fixtures/` holds real responses for bundle tx 22009759206 (4 items,
listed 170 PLN, sold for 123.82). Same re-capture rules as purchases.
