"""Edit one manually uploaded item: its metadata, its photos, and serving them."""

from __future__ import annotations

import mimetypes
from datetime import UTC
from datetime import datetime
from pathlib import Path

from fastapi import APIRouter
from fastapi import File
from fastapi import Form
from fastapi import HTTPException
from fastapi import UploadFile
from fastapi import status
from fastapi.responses import FileResponse
from fastapi.responses import HTMLResponse
from fastapi.responses import RedirectResponse

from ..constants import MAX_FILES
from ..storage import check_photo_count
from ..storage import clean_title
from ..storage import item_folder
from ..storage import load_meta
from ..storage import read_photos
from ..storage import rewrite_photos
from ..storage import write_meta
from ..templating import render

router = APIRouter()


@router.get("/items/{item_id}/edit", response_class=HTMLResponse)
def edit_form(item_id: str, saved: bool = False) -> str:
    """Show the stored title, description and photos for media/items/{item_id}/."""
    meta = load_meta(item_folder(item_id))
    return render("edit.html", item_id=item_id, meta=meta, saved=saved, max_files=MAX_FILES)


@router.post("/items/{item_id}/edit")
async def edit_item(
    item_id: str,
    title: str = Form(...),
    description: str = Form(""),
    delete: list[str] = Form(default=[]),
    photos: list[UploadFile] = File(default=[]),
) -> RedirectResponse:
    """Update title/description, drop the photos named in `delete`, append new ones.

    Surviving photos keep their relative order and are renumbered from 1.
    """
    folder = item_folder(item_id)
    meta = load_meta(folder)
    title = clean_title(title)

    dropped = set(delete)
    kept = [name for name in meta.get("photos", []) if name not in dropped]
    added = await read_photos([f for f in photos if f.filename])
    check_photo_count(len(kept) + len(added))

    payloads = [(Path(name).suffix, (folder / name).read_bytes()) for name in kept] + added
    meta["photos"] = rewrite_photos(folder, payloads)
    meta["title"] = title
    meta["description"] = description.strip()
    meta["updated_at"] = datetime.now(UTC).isoformat()
    write_meta(folder, meta)

    return RedirectResponse(
        url=f"/items/{item_id}/edit?saved=true", status_code=status.HTTP_303_SEE_OTHER
    )


@router.get("/media/items/{item_id}/{name}")
def item_photo(item_id: str, name: str) -> FileResponse:
    """Serve one photo. Only names listed in the item's meta.json are reachable."""
    folder = item_folder(item_id)
    if name not in load_meta(folder).get("photos", []):
        raise HTTPException(status_code=404, detail="photo not found")
    media_type, _ = mimetypes.guess_type(name)
    return FileResponse(folder / name, media_type=media_type)
