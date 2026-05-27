"""
Backfill purchase item photos into GCS.
"""

from __future__ import annotations

import asyncio

import httpx

from ..constants import USER_AGENT
from ..gcs import PhotoStore

_MAX_CONCURRENT_UPLOADS = 8


async def backfill_photos(
    items: list[tuple[int, list[str]]],
    store: PhotoStore | None = None,
) -> None:
    """Upload photos to GCS for the given (item_id, photo_urls) pairs."""
    tasks_args = [(item_id, url) for item_id, urls in items for url in urls]
    if not tasks_args:
        print("-> photos: nothing to upload")
        return

    photo_store: PhotoStore = store or PhotoStore()
    sem = asyncio.Semaphore(_MAX_CONCURRENT_UPLOADS)
    uploaded = 0
    skipped = 0
    failures: list[str] = []

    async with httpx.AsyncClient(
        headers={"User-Agent": USER_AGENT},
        timeout=30.0,
        follow_redirects=True,
    ) as client:

        async def _one(item_id: int, url: str) -> None:
            nonlocal uploaded, skipped
            async with sem:
                try:
                    gs_uri = await photo_store.upload_photo(item_id, url, client)
                except Exception as e:
                    failures.append(f"{url}: {e}")
                    return
            if gs_uri is None:
                skipped += 1
            else:
                uploaded += 1

        print(f"-> photos: {len(tasks_args)} URLs to process")
        await asyncio.gather(*(_one(iid, u) for iid, u in tasks_args))

    print(f"-> photos: uploaded={uploaded}, skipped={skipped}, failed={len(failures)}")
    for f in failures:
        print(f"   FAIL {f}")
