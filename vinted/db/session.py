from __future__ import annotations

from functools import lru_cache

from sqlalchemy.ext.asyncio import AsyncEngine
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.ext.asyncio import async_sessionmaker
from sqlalchemy.ext.asyncio import create_async_engine

from ..core.config import get_settings


@lru_cache
def get_engine() -> AsyncEngine:
    """Return a cached async engine built from ``DATABASE_URL``."""
    settings = get_settings()
    return create_async_engine(settings.database_url, pool_pre_ping=True, future=True)


@lru_cache
def get_sessionmaker() -> async_sessionmaker[AsyncSession]:
    """Return a cached async session factory.

    ``expire_on_commit=False`` lets callers read attributes (e.g. for
    ``model_dump``) after a commit without an extra round-trip.
    """
    return async_sessionmaker(get_engine(), class_=AsyncSession, expire_on_commit=False)
