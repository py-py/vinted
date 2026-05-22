from __future__ import annotations

from fastapi import FastAPI

from .admin import setup_admin
from .api.routes import health
from .api.routes import items
from .api.routes import scrape
from .core.logging import configure_logging


def create_app() -> FastAPI:
    configure_logging()
    app = FastAPI(title="Vinted Analyzer", version="0.1.0")
    app.include_router(health.router)
    app.include_router(scrape.router)
    app.include_router(items.router)
    setup_admin(app)
    return app


app = create_app()
