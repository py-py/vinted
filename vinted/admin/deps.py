from __future__ import annotations

from functools import lru_cache
from typing import Annotated

from fastapi import Depends

from ..storage import FirestoreStore


@lru_cache(maxsize=1)
def get_store() -> FirestoreStore:
    """One shared Firestore client per process; override in tests via dependency_overrides."""
    return FirestoreStore()


StoreDep = Annotated[FirestoreStore, Depends(get_store)]
