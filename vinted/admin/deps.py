from __future__ import annotations

from functools import lru_cache
from typing import Annotated

from fastapi import Depends

from ..storage import FirestoreStore
from ..storage import PhotoStore


@lru_cache(maxsize=1)
def get_store() -> FirestoreStore:
    """One shared Firestore client per process; override in tests via dependency_overrides."""
    return FirestoreStore()


StoreDep = Annotated[FirestoreStore, Depends(get_store)]


@lru_cache(maxsize=1)
def get_photo_store() -> PhotoStore:
    """One shared GCS client per process; override in tests via dependency_overrides."""
    return PhotoStore()


PhotoStoreDep = Annotated[PhotoStore, Depends(get_photo_store)]
