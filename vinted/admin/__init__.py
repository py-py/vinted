from __future__ import annotations

from pathlib import Path

from fastapi import FastAPI
from sqladmin import Admin

from ..db.session import get_engine
from .views import ItemAdmin
from .views import SellerAdmin

_TEMPLATES_DIR = str(Path(__file__).parent / "templates")


def setup_admin(app: FastAPI) -> Admin:
    """Mount the SQLAdmin panel (served at /admin) on the FastAPI app.

    ``templates_dir`` holds a ``sqladmin/base.html`` override that loads the
    PhotoSwipe lightbox (see that template).
    """
    admin = Admin(
        app,
        engine=get_engine(),
        title="Vinted Analyzer",
        templates_dir=_TEMPLATES_DIR,
    )
    admin.add_view(ItemAdmin)
    admin.add_view(SellerAdmin)
    return admin
