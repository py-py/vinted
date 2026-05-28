"""
GCS client for storing Vinted purchase photos.

Layout: items/{item_id}/images/{token}.jpeg
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


class PhotoStore:
    def __init__(self) -> None:
        self.client = storage.Client(project=os.environ["GOOGLE_CLOUD_PROJECT"])
        self.bucket = self.client.bucket(os.environ["VINTED_GCS_BUCKET"])

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
        token = extract_token(url)
        path = f"items/{item_id}/images/{token}.jpeg"
        blob = self.bucket.blob(path)

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
