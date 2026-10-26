"""
Listings API: create a listing, upload/serve/replace/delete/reorder its photos.

Photos are processed by `vinted.listing.photos.process` (EXIF stripped, 1600 px max),
stored in GCS under listing/{listing_id}/{photo_id}.jpeg and tracked in Firestore
`listings/{listing_id}.photos` (array order = display order). One file per upload request,
so the browser can upload a batch in parallel without hitting Cloud Run's request size limit.
"""

from __future__ import annotations

import uuid
from datetime import UTC
from datetime import datetime

from fastapi import APIRouter
from fastapi import HTTPException
from fastapi import Response
from fastapi import UploadFile
from pydantic import BaseModel
from pydantic import Field

from ..listing.photos import MAX_BYTES
from ..listing.photos import InvalidPhoto
from ..listing.photos import process
from .deps import PhotoStoreDep
from .deps import StoreDep

router = APIRouter(prefix="/api/listings", tags=["listings"])


###############################################################################
#  Schemas — API Request and Response Models
###############################################################################


class ListingPhoto(BaseModel):
    id: str
    url: str = Field(description="Served by GET /api/listings/{id}/photos/{photo_id}")
    width: int
    height: int
    bytes: int
    created_at: datetime


class Listing(BaseModel):
    id: str
    created_at: datetime
    updated_at: datetime
    photos: list[ListingPhoto]


class PhotoOrderUpdate(BaseModel):
    photo_ids: list[uuid.UUID] = Field(description="Every photo id of the listing, in new order")


###############################################################################
#  Helpers — Firestore Docs to API Models
###############################################################################


def _to_photo(listing_id: str, photo: dict) -> ListingPhoto:
    url = router.url_path_for("get_listing_photo", listing_id=listing_id, photo_id=photo["id"])
    return ListingPhoto(
        id=photo["id"],
        url=str(url),
        width=photo["width"],
        height=photo["height"],
        bytes=photo["bytes"],
        created_at=photo["created_at"],
    )


def _to_listing(doc: dict) -> Listing:
    return Listing(
        id=doc["id"],
        created_at=doc["created_at"],
        updated_at=doc.get("updated_at") or doc["created_at"],
        photos=[_to_photo(doc["id"], p) for p in doc.get("photos") or []],
    )


def _store_photo(listing_id: str, file: UploadFile, photos: PhotoStoreDep) -> dict:
    """Process an uploaded file and put it in GCS; returns the photo entry for Firestore."""
    # Read one byte past the limit to detect oversized files without buffering all of them.
    data = file.file.read(MAX_BYTES + 1)
    if len(data) > MAX_BYTES:
        raise HTTPException(status_code=413, detail="File too large")
    try:
        jpeg, width, height = process(data)
    except InvalidPhoto as e:
        raise HTTPException(status_code=422, detail=f"Invalid photo: {e}") from e

    photo_id = str(uuid.uuid4())
    return {
        "id": photo_id,
        "path": photos.upload_listing_photo(listing_id, photo_id, jpeg),
        "width": width,
        "height": height,
        "bytes": len(jpeg),
        "created_at": datetime.now(UTC),
    }


def _get_or_404(store: StoreDep, listing_id: uuid.UUID) -> dict:
    doc = store.get_listing(str(listing_id))
    if doc is None:
        raise HTTPException(status_code=404, detail="Listing not found")
    return doc


###############################################################################
#  Routes — Listings and Their Photos
###############################################################################


@router.get("")
def list_listings(store: StoreDep) -> list[Listing]:
    return [_to_listing(d) for d in store.list_listings()]


@router.post("", status_code=201)
def create_listing(store: StoreDep) -> Listing:
    return _to_listing(store.create_listing())


@router.get("/{listing_id}")
def get_listing(listing_id: uuid.UUID, store: StoreDep) -> Listing:
    return _to_listing(_get_or_404(store, listing_id))


@router.delete("/{listing_id}", status_code=204)
def delete_listing(listing_id: uuid.UUID, store: StoreDep, photos: PhotoStoreDep) -> None:
    _get_or_404(store, listing_id)
    photos.delete_listing_photos(str(listing_id))
    store.delete_listing(str(listing_id))


@router.post(
    "/{listing_id}/photos",
    status_code=201,
    responses={
        413: {"description": "File too large"},
        422: {"description": "Not a supported image"},
    },
)
def upload_listing_photo(
    listing_id: uuid.UUID,
    file: UploadFile,
    store: StoreDep,
    photos: PhotoStoreDep,
) -> ListingPhoto:
    """Upload one photo (JPEG, PNG, WebP or HEIC); it's stored as a JPEG, 1600 px max."""
    _get_or_404(store, listing_id)
    photo = _store_photo(str(listing_id), file, photos)
    store.add_listing_photo(str(listing_id), photo)
    return _to_photo(str(listing_id), photo)


@router.put(
    "/{listing_id}/photos/{photo_id}",
    responses={
        404: {"description": "Listing or photo not found"},
        413: {"description": "File too large"},
        422: {"description": "Not a supported image"},
    },
)
def replace_listing_photo(
    listing_id: uuid.UUID,
    photo_id: uuid.UUID,
    file: UploadFile,
    store: StoreDep,
    photos: PhotoStoreDep,
) -> ListingPhoto:
    """Replace a photo with its edited version (rotated / cropped), keeping its position.

    The new photo gets a fresh id, so the immutable cache of the old URL never goes stale.
    """
    doc = _get_or_404(store, listing_id)
    if not any(p["id"] == str(photo_id) for p in doc.get("photos") or []):
        raise HTTPException(status_code=404, detail="Photo not found")
    photo = _store_photo(str(listing_id), file, photos)
    if store.replace_listing_photo(str(listing_id), str(photo_id), photo) is None:
        # Deleted meanwhile: drop the orphaned upload.
        photos.delete_listing_photo(str(listing_id), photo["id"])
        raise HTTPException(status_code=404, detail="Photo not found")
    photos.delete_listing_photo(str(listing_id), str(photo_id))
    return _to_photo(str(listing_id), photo)


@router.get(
    "/{listing_id}/photos/{photo_id}",
    response_class=Response,
    responses={200: {"content": {"image/jpeg": {}}}, 404: {"description": "Not in GCS"}},
)
def get_listing_photo(
    listing_id: uuid.UUID,
    photo_id: uuid.UUID,
    photos: PhotoStoreDep,
) -> Response:
    data = photos.download_listing_photo(str(listing_id), str(photo_id))
    if data is None:
        raise HTTPException(status_code=404, detail="Photo not found")
    # Photo ids are never reused, so the bytes never change.
    return Response(
        data,
        media_type="image/jpeg",
        headers={"Cache-Control": "private, max-age=31536000, immutable"},
    )


@router.delete("/{listing_id}/photos/{photo_id}", status_code=204)
def delete_listing_photo(
    listing_id: uuid.UUID,
    photo_id: uuid.UUID,
    store: StoreDep,
    photos: PhotoStoreDep,
) -> None:
    _get_or_404(store, listing_id)
    if store.remove_listing_photo(str(listing_id), str(photo_id)) is None:
        raise HTTPException(status_code=404, detail="Photo not found")
    photos.delete_listing_photo(str(listing_id), str(photo_id))


@router.patch("/{listing_id}/photos")
def reorder_listing_photos(
    listing_id: uuid.UUID,
    update: PhotoOrderUpdate,
    store: StoreDep,
) -> list[ListingPhoto]:
    _get_or_404(store, listing_id)
    try:
        reordered = store.reorder_listing_photos(
            str(listing_id), [str(i) for i in update.photo_ids]
        )
    except ValueError as e:
        raise HTTPException(status_code=409, detail=str(e)) from e
    return [_to_photo(str(listing_id), p) for p in reordered]
