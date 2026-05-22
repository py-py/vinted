from __future__ import annotations

from fastapi import FastAPI
from sqladmin import Admin

from ..db.session import get_engine
from .views import ItemAdmin


def setup_admin(app: FastAPI) -> Admin:
    """Mount the SQLAdmin panel (served at /admin) on the FastAPI app."""
    admin = Admin(app, engine=get_engine(), title="Vinted Analyzer")
    admin.add_view(ItemAdmin)
    return admin
