"""
Firestore client and persistence helpers for Vinted data.

Project/database are read from env: GOOGLE_CLOUD_PROJECT, FIRESTORE_DATABASE.
"""

from __future__ import annotations

import os

from google.cloud import firestore

from ..account.orders.models import Order
from ..account.orders.models import SaleStatus

PURCHASES_COLLECTION = "purchases"
SALES_COLLECTION = "sales"


def _non_empty(doc: dict) -> dict:
    """Drop None/""/[]/{} values so a merge never blanks out previously saved data."""
    return {k: v for k, v in doc.items() if v not in (None, "", [], {})}


class FirestoreStore:
    """
    Firestore-backed store for Vinted data.

    Layout:
        purchases/{transaction_id}            -> order-level fields
        purchases/{transaction_id}/items/{id} -> per-item fields
        sales/{auto_id}                       -> items created for selling in the admin
    """

    def __init__(self) -> None:
        self.client = firestore.Client(
            project=os.environ["GOOGLE_CLOUD_PROJECT"],
            database=os.environ["FIRESTORE_DATABASE"],
        )
        self.purchases = self.client.collection(PURCHASES_COLLECTION)
        self.sales = self.client.collection(SALES_COLLECTION)

    def existing_transaction_ids(self) -> set[int]:
        return {int(doc.id) for doc in self.purchases.list_documents()}

    def list_item_photos(self) -> list[tuple[int, list[str]]]:
        """(item_id, photo_urls) for every item in every purchase. Empty lists are dropped."""
        pairs: list[tuple[int, list[str]]] = []
        for purchase_ref in self.purchases.list_documents():
            for item_doc in purchase_ref.collection("items").stream():
                urls = (item_doc.to_dict() or {}).get("photo_urls") or []
                if urls:
                    pairs.append((int(item_doc.id), list(urls)))
        return pairs

    def set_item_status(self, transaction_id: str, item_id: str, status: SaleStatus) -> None:
        """Set a single item's sale status.

        Stored under the custom field `_sale_status` (leading underscore marks fields
        we add ourselves, not synced from Vinted) on purchases/{tx}/items/{id}. See
        `SaleStatus` for the allowed values.
        """
        item_ref = self.purchases.document(transaction_id).collection("items").document(item_id)
        item_ref.set({"_sale_status": status}, merge=True)

    def set_item_sell_price(
        self, transaction_id: str, item_id: str, sell_price: float | None
    ) -> None:
        """Set (or clear, with None) the PLN price an item was resold for.

        Stored under the custom field `_sell_price` on purchases/{tx}/items/{id}.
        """
        item_ref = self.purchases.document(transaction_id).collection("items").document(item_id)
        value = firestore.DELETE_FIELD if sell_price is None else sell_price
        item_ref.set({"_sell_price": value}, merge=True)

    def new_sale_id(self) -> str:
        """Reserve a Firestore auto id, so photos can be stored before the doc is written."""
        return self.sales.document().id

    def save_sale(self, sale_id: str, sale: dict) -> None:
        self.sales.document(sale_id).set({**sale, "created_at": firestore.SERVER_TIMESTAMP})

    def list_sales(self) -> list[tuple[str, dict]]:
        """(sale_id, doc) newest first."""
        query = self.sales.order_by("created_at", direction=firestore.Query.DESCENDING)
        return [(snap.id, snap.to_dict() or {}) for snap in query.stream()]

    def save_order(self, order: Order) -> None:
        """Upsert an order and its items.

        New docs are written in full. Existing docs are merged with only non-empty
        fields: Vinted's API stopped returning some fields (paid_price, size, ...)
        for older orders, and a re-sync must not wipe them or `_sale_status`.
        """
        if not order.transaction_id:
            raise ValueError(f"order has empty transaction_id: {order}")

        purchase_ref = self.purchases.document(str(order.transaction_id))
        docs = [(purchase_ref, order.model_dump(exclude={"items"}))]
        docs += [
            (purchase_ref.collection("items").document(str(item.id)), item.model_dump())
            for item in order.items
        ]
        existing = {
            snap.reference.path
            for snap in self.client.get_all([ref for ref, _ in docs])
            if snap.exists
        }

        batch = self.client.batch()
        for ref, doc in docs:
            if ref.path in existing:
                doc = _non_empty(doc)
            if ref is purchase_ref:
                doc["updated_at"] = firestore.SERVER_TIMESTAMP
            batch.set(ref, doc, merge=True)
        batch.commit()

    def save_orders(self, orders: list[Order]) -> None:
        for i, order in enumerate(orders, 1):
            print(f"-> [{i}/{len(orders)}] saving tx={order.transaction_id}")
            self.save_order(order)
