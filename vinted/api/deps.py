from __future__ import annotations

from ..core.config import Settings
from ..core.config import get_settings
from ..repositories.items_repo import ItemsRepository


def settings_dep() -> Settings:
    return get_settings()


def items_repo_dep() -> ItemsRepository:
    return ItemsRepository()
