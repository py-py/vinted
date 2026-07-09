"""Reading and writing manually uploaded items under media/items/{uuid4}/.

Layout of one item folder:
    1.<ext>, 2.<ext>, …  photos, numbered in display order
    meta.json            id, title, description, photos, created_at[, updated_at]
"""

from __future__ import annotations

import json
import uuid
from pathlib import Path

from fastapi import HTTPException
from fastapi import UploadFile
from PIL import UnidentifiedImageError

from .constants import ALLOWED_EXT
from .constants import MAX_BYTES
from .constants import MAX_FILES
from .constants import MEDIA_ITEMS_DIR
from .utils import compress_image

META_FILE = "meta.json"


def item_folder(item_id: str) -> Path:
    """media/items/{item_id}, or 404. Rejects anything that isn't a bare UUID.

    Parsing as a UUID is what keeps `..` and absolute paths out of the joined path.
    """
    try:
        uuid.UUID(item_id)
    except ValueError:
        raise HTTPException(status_code=404, detail="item not found") from None
    folder = MEDIA_ITEMS_DIR / item_id
    if not folder.is_dir():
        raise HTTPException(status_code=404, detail="item not found")
    return folder


def load_meta(folder: Path) -> dict:
    try:
        return json.loads((folder / META_FILE).read_text())
    except (OSError, ValueError):
        raise HTTPException(status_code=404, detail="item metadata is missing") from None


def write_meta(folder: Path, meta: dict) -> None:
    (folder / META_FILE).write_text(json.dumps(meta, ensure_ascii=False, indent=2))


def clean_title(title: str) -> str:
    title = title.strip()
    if not title:
        raise HTTPException(status_code=422, detail="title is required")
    return title


def check_photo_count(count: int) -> None:
    if not count:
        raise HTTPException(status_code=422, detail="at least one photo is required")
    if count > MAX_FILES:
        raise HTTPException(status_code=422, detail=f"too many photos (max {MAX_FILES})")


async def read_photos(files: list[UploadFile]) -> list[tuple[str, bytes]]:
    """Validate and compress every upload, returning [(ext, data), …] in order.

    Nothing touches the filesystem here, so a rejected upload never leaves an
    orphaned folder behind, nor clobbers an existing one.
    """
    payloads: list[tuple[str, bytes]] = []
    for upload in files:
        ext = Path(upload.filename or "").suffix.lower()
        if ext not in ALLOWED_EXT:
            raise HTTPException(status_code=422, detail=f"unsupported file type: {ext or '?'}")
        data = await upload.read()
        if len(data) > MAX_BYTES:
            raise HTTPException(
                status_code=422,
                detail=f"{upload.filename} exceeds {MAX_BYTES // 1024 // 1024} MB",
            )
        try:
            data = compress_image(data, ext)
        except (UnidentifiedImageError, OSError, ValueError):
            raise HTTPException(
                status_code=422, detail=f"{upload.filename} is not a readable image"
            ) from None
        payloads.append((ext, data))
    return payloads


def rewrite_photos(folder: Path, payloads: list[tuple[str, bytes]]) -> list[str]:
    """Replace the folder's photos with `payloads`, renumbered 1.<ext>, 2.<ext>, ….

    Written under temporary names first, so a crash mid-write can't leave the item
    with a half-deleted set of photos. Returns the final filenames in order.
    """
    staged = [
        (folder / f".new_{i}{ext}", f"{i}{ext}", data) for i, (ext, data) in enumerate(payloads, 1)
    ]
    for tmp, _, data in staged:
        tmp.write_bytes(data)

    for existing in folder.iterdir():
        if existing.name != META_FILE and not existing.name.startswith(".new_"):
            existing.unlink()

    for tmp, final, _ in staged:
        tmp.rename(folder / final)
    return [final for _, final, _ in staged]
