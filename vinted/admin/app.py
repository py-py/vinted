"""
FastAPI admin app for Vinted data.

Run:
    fastapi dev
"""

from __future__ import annotations

from dotenv import load_dotenv
from fastapi import Depends
from fastapi import FastAPI

from . import purchases
from .auth import require_auth

load_dotenv()

app = FastAPI(title="Vinted admin", dependencies=[Depends(require_auth)])
app.include_router(purchases.router)
