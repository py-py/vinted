"""
FastAPI admin app for Vinted data: JSON API under /api plus the built `web/` SPA.

Run:
    fastapi dev
"""

from __future__ import annotations

import os
from pathlib import Path

from dotenv import load_dotenv
from fastapi import Depends
from fastapi import FastAPI

from . import api
from . import listings
from .auth import require_auth

load_dotenv()

# `npm --prefix web run build` output; override with WEB_DIST (e.g. in the Docker image).
WEB_DIST = Path(os.environ.get("WEB_DIST", Path(__file__).resolve().parents[2] / "web" / "dist"))

app = FastAPI(title="Vinted admin", dependencies=[Depends(require_auth)])
app.include_router(api.router)
app.include_router(listings.router)
# check_dir=False: tests and the Vite dev setup run without a build; / then 404s.
app.frontend("/", directory=WEB_DIST, check_dir=False)
