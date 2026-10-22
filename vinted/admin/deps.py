from __future__ import annotations

from functools import lru_cache
from pathlib import Path
from typing import Annotated

from fastapi import Depends
from jinja2 import Environment
from jinja2 import FileSystemLoader
from jinja2 import select_autoescape

from ..storage import FirestoreStore

_TEMPLATES_DIR = Path(__file__).resolve().parent / "templates"
templates = Environment(
    loader=FileSystemLoader(_TEMPLATES_DIR),
    autoescape=select_autoescape(["html"]),
)


@lru_cache(maxsize=1)
def get_store() -> FirestoreStore:
    """One shared Firestore client per process; override in tests via dependency_overrides."""
    return FirestoreStore()


StoreDep = Annotated[FirestoreStore, Depends(get_store)]
