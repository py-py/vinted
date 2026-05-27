"""
Firestore client and persistence helpers for Vinted data.

Defaults match the existing notifier setup: project=vinted-492007, db=vinted-dev.
"""

from __future__ import annotations

import os

from google.cloud import firestore

from .orders.models import Order

DEFAULT_PROJECT = "vinted-492007"
DEFAULT_DATABASE = "vinted-dev"
PURCHASES_COLLECTION = "purchases"


class FirestoreStore:
    """
    Firestore-backed store for Vinted data.

    Layout:
        purchases/{transaction_id}            -> order-level fields
        purchases/{transaction_id}/items/{id} -> per-item fields
    """

    def __init__(
        self,
        project: str | None = None,
        database: str | None = None,
    ) -> None:
        self.client = firestore.Client(
            project=project or os.environ.get("GOOGLE_CLOUD_PROJECT", DEFAULT_PROJECT),
            database=database or os.environ.get("FIRESTORE_DATABASE", DEFAULT_DATABASE),
        )

    def save_order(self, order: Order) -> None:
        if not order.transaction_id:
            raise ValueError(f"order has empty transaction_id: {order}")

        purchase_ref = self.client.collection(PURCHASES_COLLECTION).document(
            str(order.transaction_id)
        )
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
