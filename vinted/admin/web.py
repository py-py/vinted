"""
FastAPI viewer for purchased Vinted items.

Data is pulled from Firestore (purchases/{tx}/items/{id}). Photos are loaded
directly from the Vinted CDN URLs stored in Firestore — no GCS access here.

Run:
    uvicorn vinted.admin.web:app --reload
"""

from __future__ import annotations

from dotenv import load_dotenv
from fastapi import Depends
from fastapi import FastAPI

from .routers import items
from .routers import uploads
from .security import require_auth

load_dotenv()

app = FastAPI(title="Vinted purchases", dependencies=[Depends(require_auth)])
app.include_router(items.router)
app.include_router(uploads.router)
