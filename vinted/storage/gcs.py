"""
GCS client for storing Vinted purchase photos.

Layout:
    items/{item_id}/images/{token}.jpeg    -> purchase photos copied from the Vinted CDN
    sales/{sale_id}/images/{photo_id}.jpeg -> photos uploaded for sale items in the admin
Project/bucket are read from env: GOOGLE_CLOUD_PROJECT, VINTED_GCS_BUCKET.
"""

from __future__ import annotations

import asyncio
import os
import re

import httpx
from google.api_core import exceptions as gcp_exceptions
from google.cloud import storage

# Vinted CDN URL pattern: https://imagesN.vinted.net/t/{token}/{size}/{numeric}.jpeg?s=...
_TOKEN_RE = re.compile(r"/t/([^/]+)/")


def extract_token(url: str) -> str:
    """Pull the per-image token from a Vinted CDN URL."""
    m = _TOKEN_RE.search(url)
    if not m:
        raise ValueError(f"no token in vinted photo URL: {url}")
    return m.group(1)


def photo_path(item_id: int, token: str) -> str:
    return f"items/{item_id}/images/{token}.jpeg"


def sale_photo_path(sale_id: str, photo_id: str) -> str:
    return f"sales/{sale_id}/images/{photo_id}.jpeg"


class PhotoStore:
    def __init__(self) -> None:
        self.client = storage.Client(project=os.environ["GOOGLE_CLOUD_PROJECT"])
        self.bucket = self.client.bucket(os.environ["VINTED_GCS_BUCKET"])

    def download_photo(self, item_id: int, token: str) -> bytes | None:
        """Read a stored photo; None if it was never backfilled."""
        try:
            return self.bucket.blob(photo_path(item_id, token)).download_as_bytes()
        except gcp_exceptions.NotFound:
            return None

    def upload_sale_photo(self, sale_id: str, photo_id: str, data: bytes) -> None:
        self.bucket.blob(sale_photo_path(sale_id, photo_id)).upload_from_string(
            data, content_type="image/jpeg"
        )

    def download_sale_photo(self, sale_id: str, photo_id: str) -> bytes | None:
        try:
            return self.bucket.blob(sale_photo_path(sale_id, photo_id)).download_as_bytes()
        except gcp_exceptions.NotFound:
            return None

    async def upload_photo(
        self,
        item_id: int,
        url: str,
        client: httpx.AsyncClient,
    ) -> str | None:
        """
        Download a Vinted photo and store it under items/{item_id}/images/{token}.jpeg.
        Returns the gs:// URI on upload, or None if it already exists.
        """
        blob = self.bucket.blob(photo_path(item_id, extract_token(url)))

        # Cheap HEAD: avoids re-downloading photos we already have.
        if await asyncio.to_thread(blob.exists):
            return None

        resp = await client.get(url)
        resp.raise_for_status()

        try:
            await asyncio.to_thread(
                blob.upload_from_string,
                resp.content,
                content_type="image/jpeg",
                if_generation_match=0,
            )
        except gcp_exceptions.PreconditionFailed:
            # Object already exists — if_generation_match=0 forbids overwrite.
            # Happens when another worker uploaded between exists() and upload_from_string.
            return None

        return f"gs://{self.bucket.name}/{blob.name}"
