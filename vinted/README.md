# How purchased items are fetched from Vinted

Code: `vinted/account/orders/api.py` (`fetch_my_orders` → `build_order`).

```mermaid
sequenceDiagram
    autonumber
    participant S as sync
    participant V as Vinted API

    loop page = 1, 2, ...
        S->>V: GET /api/v2/my_orders?type=purchased&status=completed&page=N
        V-->>S: my_orders[] → transaction_id
    end

    loop each transaction_id
        par
            S->>V: GET /api/v2/escrow_orders/{tx}/items
            V-->>S: items[]: id, title, is_deleted, photo_url
        and
            S->>V: GET /api/v2/transactions/{tx}
            V-->>S: order.items[]: size, condition, price, photos, url
        end
        Note over S: join by item id → OrderItem[]
    end
```

## Item fields

| Field | Source |
|---|---|
| `id`, `title`, `is_deleted`, `photo_url` | `escrow_orders/{tx}/items` |
| `size`, `condition` | `transactions/{tx}` → `size_title`, `status` |
| `listed_price` | `transactions/{tx}` → `price` (in PLN) |
| `url`, `catalog_id`, `photo_urls` | `transactions/{tx}` |
| `paid_price` | `escrow_orders/{tx}/items` → `paid_price_in_seller_currency` — **`null` since ~2026-09** |
