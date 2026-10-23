"""
Purchased Vinted items loaded from Firestore (purchases/{tx}/items/{id}), with
per-item PLN prices derived from the order totals. Served by `api.py`.
"""

from __future__ import annotations

from ..storage import FirestoreStore


def _allocate_pln(purchase: dict, items: list[dict]) -> dict[int, float]:
    """Distribute the order's PLN total across items proportionally to their paid_price.

    The order's `total_price` (in `currency`) already includes shipping + service fee.
    Each item gets `total_price * item.paid_price / sum(items.paid_price)`, so fees are
    split in proportion to item value. Newer orders have no paid_price (Vinted stopped
    returning it), so listed_price is used as the weight when any item lacks paid_price.
    Returns {item_id: price_pln}; items without a weight (or when the order isn't
    priced in PLN) are omitted.
    """
    if purchase.get("currency") != "PLN":
        return {}
    total = purchase.get("total_price")
    if not isinstance(total, (int, float)) or not total:
        return {}
    key = "paid_price" if all(i.get("paid_price") is not None for i in items) else "listed_price"
    items_sum: float = sum((i.get(key) or 0.0) for i in items)
    if not items_sum:
        return {}
    return {
        int(i["id"]): float(total) * (i[key] / items_sum) for i in items if i.get(key) is not None
    }


def _estimate_paid(purchase: dict, items: list[dict]) -> dict[int, tuple[float, str]]:
    """Estimate per-item paid price in seller currency for orders without paid_price.

    Splits the order's items total (conversion.items_price_seller, or items_price when
    there was no currency conversion) across items proportionally to listed_price.
    Returns {item_id: (amount, currency)} only for items missing paid_price.
    """
    conv = purchase.get("conversion") or {}
    if conv.get("items_price_seller"):
        total, currency = conv["items_price_seller"], conv.get("seller_currency", "")
    else:
        total, currency = purchase.get("items_price"), purchase.get("currency", "")
    if not isinstance(total, (int, float)) or not total:
        return {}
    listed_sum: float = sum((i.get("listed_price") or 0.0) for i in items)
    if not listed_sum:
        return {}
    return {
        int(i["id"]): (float(total) * i["listed_price"] / listed_sum, currency)
        for i in items
        if i.get("paid_price") is None and i.get("listed_price") is not None
    }


def load_purchases(store: FirestoreStore) -> list[dict]:
    """Purchases (transactions) newest first, each with its enriched items.

    Uses two queries: one stream over `purchases` for the order context, one
    collection_group("items") for all items across all purchases. Items are
    joined to their parent purchase by document id and nested under it.
    """
    purchases: dict[str, dict] = {
        snap.id: (snap.to_dict() or {}) for snap in store.purchases.stream()
    }
    items_by_purchase: dict[str, list[dict]] = {}
    for item_snap in store.client.collection_group("items").stream():
        parent_id = item_snap.reference.parent.parent.id
        items_by_purchase.setdefault(parent_id, []).append(item_snap.to_dict() or {})

    out: list[dict] = []
    for tx_id, purchase in purchases.items():
        items = items_by_purchase.get(tx_id, [])
        pln_by_id = _allocate_pln(purchase, items)
        est_by_id = _estimate_paid(purchase, items)
        enriched = [
            {
                **item,
                **(
                    {"paid_price": est[0], "currency": est[1], "paid_estimated": True}
                    if (est := est_by_id.get(item.get("id")))
                    else {}
                ),
                "price_pln": (
                    pln_by_id.get(item.get("id")) if isinstance(item.get("id"), int) else None
                ),
                "_sale_status": item.get("_sale_status") or "none",
            }
            for item in items
        ]
        out.append(
            {
                "tx_id": tx_id,
                "seller_id": purchase.get("seller_id"),
                "seller_login": purchase.get("seller_login", ""),
                "seller_country": purchase.get("seller_country", ""),
                "order_date": purchase.get("date", ""),
                "conversation_id": purchase.get("conversation_id"),
                "total_price": purchase.get("total_price"),
                "currency": purchase.get("currency", ""),
                "items": enriched,
            }
        )
    out.sort(key=lambda p: p.get("order_date") or "", reverse=True)
    return out
