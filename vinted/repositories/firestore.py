from __future__ import annotations

from functools import lru_cache

from google.cloud import firestore

from ..core.config import get_settings


@lru_cache
def get_client() -> firestore.AsyncClient:
    """Return a cached async Firestore client.

    Credentials are resolved via Application Default Credentials
    (GOOGLE_APPLICATION_CREDENTIALS or the ambient GCP environment).
    """
    settings = get_settings()
    return firestore.AsyncClient(project=settings.gcp_project)
