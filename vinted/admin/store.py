"""Lazily-created, process-wide Firestore client."""

from __future__ import annotations

from functools import lru_cache

from vinted.account.firestore import FirestoreStore


@lru_cache(maxsize=1)
def get_store() -> FirestoreStore:
    return FirestoreStore()
