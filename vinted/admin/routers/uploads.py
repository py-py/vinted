"""Manual item upload: a form plus the handler that writes media/items/{uuid4}/."""

from __future__ import annotations

import uuid
from datetime import UTC
from datetime import datetime

from fastapi import APIRouter
from fastapi import File
from fastapi import Form
from fastapi import UploadFile
from fastapi import status
from fastapi.responses import HTMLResponse
from fastapi.responses import RedirectResponse

from ..constants import MEDIA_ITEMS_DIR
from ..storage import check_photo_count
from ..storage import clean_title
from ..storage import read_photos
from ..storage import rewrite_photos
from ..storage import write_meta
from ..templating import render

router = APIRouter()


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
    title = clean_title(title)
    files = [f for f in photos if f.filename]
    check_photo_count(len(files))
    payloads = await read_photos(files)

    item_id = str(uuid.uuid4())
    folder = MEDIA_ITEMS_DIR / item_id
    folder.mkdir(parents=True, exist_ok=True)
    saved = rewrite_photos(folder, payloads)

    write_meta(
        folder,
        {
            "id": item_id,
            "title": title,
            "description": description.strip(),
            "photos": saved,
            "created_at": datetime.now(UTC).isoformat(),
        },
    )
    return RedirectResponse(
        url=f"/upload?created={item_id}", status_code=status.HTTP_303_SEE_OTHER
    )
