"""
Firestore client and persistence helpers for Vinted data.

Project/database are read from env: GOOGLE_CLOUD_PROJECT, FIRESTORE_DATABASE.
"""

from __future__ import annotations

import os

from google.cloud import firestore

from .orders.models import Order

PURCHASES_COLLECTION = "purchases"


class FirestoreStore:
    """
    Firestore-backed store for Vinted data.

    Layout:
        purchases/{transaction_id}            -> order-level fields
        purchases/{transaction_id}/items/{id} -> per-item fields
    """

    def __init__(self) -> None:
        self.client = firestore.Client(
            project=os.environ["GOOGLE_CLOUD_PROJECT"],
            database=os.environ["FIRESTORE_DATABASE"],
        )
        self.purchases = self.client.collection(PURCHASES_COLLECTION)

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

    def set_item_status(self, transaction_id: str, item_id: str, status: str) -> None:
        """Set a single item's sale status.

        Stored under the custom field `_sale_status` (leading underscore marks fields
        we add ourselves, not synced from Vinted) on purchases/{tx}/items/{id}. One of
        "none" (not for sale), "listed" (listed for sale), "sold".
        """
        item_ref = self.purchases.document(transaction_id).collection("items").document(item_id)
        item_ref.set({"_sale_status": status}, merge=True)

    def save_order(self, order: Order) -> None:
        if not order.transaction_id:
            raise ValueError(f"order has empty transaction_id: {order}")

        purchase_ref = self.purchases.document(str(order.transaction_id))
        order_doc = order.model_dump(exclude={"items"})
        order_doc["updated_at"] = firestore.SERVER_TIMESTAMP

        batch = self.client.batch()
        batch.set(purchase_ref, order_doc)
        for item in order.items:
            batch.set(purchase_ref.collection("items").document(str(item.id)), item.model_dump())
        batch.commit()

    def save_orders(self, orders: list[Order]) -> None:
        for i, order in enumerate(orders, 1):
            print(f"-> [{i}/{len(orders)}] saving tx={order.transaction_id}")
            self.save_order(order)
