"""
Firestore client and persistence helpers for Vinted data.

Project/database are read from env: GOOGLE_CLOUD_PROJECT, FIRESTORE_DATABASE.
"""

from __future__ import annotations

import os

from google.cloud import firestore

from ..account.orders.models import Order
from ..account.orders.models import SaleStatus
from ..account.sales.models import Sale

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
        sales/{transaction_id}                -> sale-level fields
        sales/{transaction_id}/items/{id}     -> per-item fields
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

    def existing_sale_ids(self) -> set[int]:
        return {int(doc.id) for doc in self.sales.list_documents()}

    def list_item_photos(self) -> list[tuple[int, list[str]]]:
        """(item_id, photo_urls) for every item in every purchase. Empty lists are dropped."""
        return self._list_item_photos(self.purchases)

    def list_sale_item_photos(self) -> list[tuple[int, list[str]]]:
        """(item_id, photo_urls) for every item in every sale. Empty lists are dropped."""
        return self._list_item_photos(self.sales)

    @staticmethod
    def _list_item_photos(
        collection: firestore.CollectionReference,
    ) -> list[tuple[int, list[str]]]:
        pairs: list[tuple[int, list[str]]] = []
        for parent_ref in collection.list_documents():
            for item_doc in parent_ref.collection("items").stream():
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

    def save_order(self, order: Order) -> None:
        """Upsert an order and its items.

        New docs are written in full. Existing docs are merged with only non-empty
        fields: Vinted's API stopped returning some fields (paid_price, size, ...)
        for older orders, and a re-sync must not wipe them or `_sale_status`.
        """
        if not order.transaction_id:
            raise ValueError(f"order has empty transaction_id: {order}")
        self._upsert(
            self.purchases.document(str(order.transaction_id)),
            order.model_dump(exclude={"items"}),
            [(str(item.id), item.model_dump()) for item in order.items],
        )

    def save_orders(self, orders: list[Order]) -> None:
        for i, order in enumerate(orders, 1):
            print(f"-> [{i}/{len(orders)}] saving tx={order.transaction_id}")
            self.save_order(order)

    def save_sale(self, sale: Sale) -> None:
        """Upsert a sale and its items into sales/{tx}; same merge rules as `save_order`.

        Vinted deletes old sold listings, so a re-sync returns fewer fields — the
        non-empty merge keeps the photos/prices saved while the listing was alive.
        """
        if not sale.transaction_id:
            raise ValueError(f"sale has empty transaction_id: {sale}")
        self._upsert(
            self.sales.document(str(sale.transaction_id)),
            sale.model_dump(exclude={"items"}),
            [(str(item.id), item.model_dump()) for item in sale.items],
        )

    def save_sales(self, sales: list[Sale]) -> None:
        for i, sale in enumerate(sales, 1):
            print(f"-> [{i}/{len(sales)}] saving sale tx={sale.transaction_id}")
            self.save_sale(sale)

    def _upsert(
        self,
        parent_ref: firestore.DocumentReference,
        parent_doc: dict,
        items: list[tuple[str, dict]],
    ) -> None:
        """Write a parent doc + its `items` sub-collection in one batch.

        Docs that already exist are merged with only their non-empty fields.
        """
        docs = [(parent_ref, parent_doc)]
        docs += [(parent_ref.collection("items").document(item_id), doc) for item_id, doc in items]
        existing = {
            snap.reference.path
            for snap in self.client.get_all([ref for ref, _ in docs])
            if snap.exists
        }

        batch = self.client.batch()
        for ref, doc in docs:
            if ref.path in existing:
                doc = _non_empty(doc)
            if ref is parent_ref:
                doc["updated_at"] = firestore.SERVER_TIMESTAMP
            batch.set(ref, doc, merge=True)
        batch.commit()
