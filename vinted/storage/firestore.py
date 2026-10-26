"""
Firestore client and persistence helpers for Vinted data.

Project/database are read from env: GOOGLE_CLOUD_PROJECT, FIRESTORE_DATABASE.
"""

from __future__ import annotations

import os
import uuid
from datetime import UTC
from datetime import datetime

from google.cloud import firestore

from ..account.purchases.models import Order
from ..account.purchases.models import SaleStatus
from ..account.sales.models import Sale

PURCHASES_COLLECTION = "purchases"
SALES_COLLECTION = "sales"
LISTINGS_COLLECTION = "listings"


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
        listings/{listing_id}                 -> {id, title, description, created_at,
                                                  updated_at, photos: [...]}

    Listing `photos` is an array of {id, path, width, height, bytes, created_at};
    array order is the display order.
    """

    def __init__(self) -> None:
        self.client = firestore.Client(
            project=os.environ["GOOGLE_CLOUD_PROJECT"],
            database=os.environ["FIRESTORE_DATABASE"],
        )
        self.purchases = self.client.collection(PURCHASES_COLLECTION)
        self.sales = self.client.collection(SALES_COLLECTION)
        self.listings = self.client.collection(LISTINGS_COLLECTION)

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

    def set_item_sale_item_id(
        self, transaction_id: str, item_id: str, sale_item_id: int | None
    ) -> None:
        """Link (or unlink, with None) an item to the sale item it was resold as.

        Stored under the custom field `_sale_item_id` on purchases/{tx}/items/{id};
        the value is an item id under sales/{tx}/items.
        """
        item_ref = self.purchases.document(transaction_id).collection("items").document(item_id)
        value = firestore.DELETE_FIELD if sale_item_id is None else sale_item_id
        item_ref.set({"_sale_item_id": value}, merge=True)

    def create_listing(self) -> dict:
        """Create an empty listing with a fresh uuid4 id and return its doc."""
        now = datetime.now(UTC)
        doc = {"id": str(uuid.uuid4()), "created_at": now, "updated_at": now, "photos": []}
        self.listings.document(doc["id"]).create(doc)
        return doc

    def list_listings(self) -> list[dict]:
        """All listings, newest first."""
        docs = [snap.to_dict() or {} for snap in self.listings.stream()]
        return sorted(docs, key=lambda d: d["created_at"], reverse=True)

    def get_listing(self, listing_id: str) -> dict | None:
        snap = self.listings.document(listing_id).get()
        return snap.to_dict() if snap.exists else None

    def delete_listing(self, listing_id: str) -> None:
        self.listings.document(listing_id).delete()

    def update_listing(self, listing_id: str, fields: dict) -> None:
        """Set top-level listing fields (title, description). Raises NotFound if missing."""
        self.listings.document(listing_id).update(
            {**fields, "updated_at": firestore.SERVER_TIMESTAMP}
        )

    def add_listing_photo(self, listing_id: str, photo: dict) -> None:
        """Append a photo to the listing. Raises NotFound if the listing doesn't exist.

        ArrayUnion is atomic, so parallel uploads into one listing don't overwrite each other.
        """
        self.listings.document(listing_id).update(
            {
                "photos": firestore.ArrayUnion([photo]),
                "updated_at": firestore.SERVER_TIMESTAMP,
            }
        )

    def remove_listing_photo(self, listing_id: str, photo_id: str) -> dict | None:
        """Drop a photo from the listing; returns the removed photo, None if it wasn't there."""

        @firestore.transactional
        def run(tx: firestore.Transaction) -> dict | None:
            ref = self.listings.document(listing_id)
            photos = (ref.get(transaction=tx).to_dict() or {}).get("photos") or []
            removed = next((p for p in photos if p["id"] == photo_id), None)
            if removed is not None:
                tx.update(
                    ref,
                    {
                        "photos": [p for p in photos if p["id"] != photo_id],
                        "updated_at": firestore.SERVER_TIMESTAMP,
                    },
                )
            return removed

        return run(self.client.transaction())

    def replace_listing_photo(self, listing_id: str, photo_id: str, photo: dict) -> dict | None:
        """Swap a photo for `photo` at the same position; returns the old one, None if missing."""

        @firestore.transactional
        def run(tx: firestore.Transaction) -> dict | None:
            ref = self.listings.document(listing_id)
            photos = (ref.get(transaction=tx).to_dict() or {}).get("photos") or []
            index = next((i for i, p in enumerate(photos) if p["id"] == photo_id), None)
            if index is None:
                return None
            old = photos[index]
            photos[index] = photo
            tx.update(ref, {"photos": photos, "updated_at": firestore.SERVER_TIMESTAMP})
            return old

        return run(self.client.transaction())

    def reorder_listing_photos(self, listing_id: str, photo_ids: list[str]) -> list[dict]:
        """Put the listing's photos in `photo_ids` order; returns the reordered photos.

        `photo_ids` must name every current photo exactly once, otherwise ValueError —
        a stale client must not drop photos uploaded after it last loaded the listing.
        """

        @firestore.transactional
        def run(tx: firestore.Transaction) -> list[dict]:
            ref = self.listings.document(listing_id)
            photos = (ref.get(transaction=tx).to_dict() or {}).get("photos") or []
            by_id = {p["id"]: p for p in photos}
            if len(photo_ids) != len(by_id) or set(photo_ids) != set(by_id):
                raise ValueError("photo_ids must list every photo of the listing exactly once")
            reordered = [by_id[i] for i in photo_ids]
            tx.update(ref, {"photos": reordered, "updated_at": firestore.SERVER_TIMESTAMP})
            return reordered

        return run(self.client.transaction())

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
