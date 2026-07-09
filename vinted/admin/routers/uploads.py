"""Manual item upload: a form plus the handler that writes media/items/{uuid4}/."""

from __future__ import annotations

import json
import uuid
from datetime import UTC
from datetime import datetime
from pathlib import Path

from fastapi import APIRouter
from fastapi import File
from fastapi import Form
from fastapi import HTTPException
from fastapi import UploadFile
from fastapi import status
from fastapi.responses import HTMLResponse
from fastapi.responses import RedirectResponse
from PIL import UnidentifiedImageError

from ..constants import ALLOWED_EXT
from ..constants import MAX_BYTES
from ..constants import MAX_FILES
from ..constants import MEDIA_ITEMS_DIR
from ..templating import render
from ..utils import compress_image

router = APIRouter()


async def _read_photos(files: list[UploadFile]) -> list[tuple[str, bytes]]:
    """Validate and compress every upload, returning [(filename, data), …] in order.

    Nothing touches the filesystem here, so a rejected upload never leaves an
    orphaned folder behind.
    """
    payloads: list[tuple[str, bytes]] = []
    for position, upload in enumerate(files, start=1):
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
        payloads.append((f"{position}{ext}", data))
    return payloads


@router.get("/upload", response_class=HTMLResponse)
def upload_form(created: str | None = None) -> str:
    return render("upload.html", created=created)


@router.post("/upload")
async def upload_item(
    title: str = Form(...),
    description: str = Form(""),
    photos: list[UploadFile] = File(...),
) -> RedirectResponse:
    """Create media/items/{uuid4}/ from an uploaded title, description and photos.

    Photos are saved as 1.<ext>, 2.<ext>, … in upload order; title/description are
    written to meta.json alongside them.
    """
    title = title.strip()
    if not title:
        raise HTTPException(status_code=422, detail="title is required")

    files = [f for f in photos if f.filename]
    if not files:
        raise HTTPException(status_code=422, detail="at least one photo is required")
    if len(files) > MAX_FILES:
        raise HTTPException(status_code=422, detail=f"too many photos (max {MAX_FILES})")

    payloads = await _read_photos(files)

    item_id = str(uuid.uuid4())
    folder = MEDIA_ITEMS_DIR / item_id
    folder.mkdir(parents=True, exist_ok=True)
    for name, data in payloads:
        (folder / name).write_bytes(data)

    meta = {
        "id": item_id,
        "title": title,
        "description": description.strip(),
        "photos": [name for name, _ in payloads],
        "created_at": datetime.now(UTC).isoformat(),
    }
    (folder / "meta.json").write_text(json.dumps(meta, ensure_ascii=False, indent=2))

    return RedirectResponse(
        url=f"/upload?created={item_id}", status_code=status.HTTP_303_SEE_OTHER
    )
