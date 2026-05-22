from __future__ import annotations

import asyncio
from functools import lru_cache

from google.cloud import storage

from ..core.config import get_settings


def product_prefix(product_id: str) -> str:
    """GCS key prefix under which a product's images live."""
    return f"products/{product_id}"


@lru_cache
def _get_bucket() -> storage.Bucket:
    """Return a cached GCS bucket handle.

    Credentials are resolved via Application Default Credentials
    (GOOGLE_APPLICATION_CREDENTIALS or the ambient GCP environment).
    """
    settings = get_settings()
    if not settings.gcs_bucket:
        raise RuntimeError("GCS_BUCKET is not configured")
    client = storage.Client(project=settings.gcp_project)
    return client.bucket(settings.gcs_bucket)


async def upload_bytes(blob_name: str, data: bytes, content_type: str | None = None) -> str:
    """Upload raw bytes to ``blob_name`` and return the blob's public URL.

    The google-cloud-storage client is synchronous, so the blocking call runs in
    a worker thread to avoid stalling the event loop.
    """

    def _upload() -> str:
        blob = _get_bucket().blob(blob_name)
        blob.upload_from_string(data, content_type=content_type)
        return blob.public_url

    return await asyncio.to_thread(_upload)


async def download_bytes(blob_name: str) -> bytes:
    """Download and return the raw bytes of ``blob_name``."""

    def _download() -> bytes:
        return _get_bucket().blob(blob_name).download_as_bytes()

    return await asyncio.to_thread(_download)


async def list_blob_names(prefix: str) -> list[str]:
    """Return the sorted blob names under ``prefix``."""

    def _list() -> list[str]:
        return sorted(blob.name for blob in _get_bucket().list_blobs(prefix=prefix))

    return await asyncio.to_thread(_list)
