"""
Sold Vinted items loaded from Firestore (sales/{tx}/items/{id}). Served by `api.py`.
"""

from __future__ import annotations

from ..storage import FirestoreStore


def load_sales(store: FirestoreStore) -> list[dict]:
    """Sales (transactions) newest first, each with its items.

    Same two-query join as `load_purchases`: `collection_group("items")` also
    returns purchase items, which are dropped since no sale has their parent id.
    """
    sales: dict[str, dict] = {snap.id: (snap.to_dict() or {}) for snap in store.sales.stream()}
    items_by_sale: dict[str, list[dict]] = {}
    for item_snap in store.client.collection_group("items").stream():
        parent_id = item_snap.reference.parent.parent.id
        if parent_id in sales:
            items_by_sale.setdefault(parent_id, []).append(item_snap.to_dict() or {})

    out = [
        {
            "tx_id": tx_id,
            "buyer_id": sale.get("buyer_id"),
            "buyer_login": sale.get("buyer_login", ""),
            "buyer_country": sale.get("buyer_country", ""),
            "order_date": sale.get("date", ""),
            "conversation_id": sale.get("conversation_id"),
            "items_price": sale.get("items_price"),
            "shipment_price": sale.get("shipment_price"),
            "currency": sale.get("currency", ""),
            "items": items_by_sale.get(tx_id, []),
        }
        for tx_id, sale in sales.items()
    ]
    out.sort(key=lambda s: s.get("order_date") or "", reverse=True)
    return out
