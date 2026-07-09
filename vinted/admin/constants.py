"""Constants for the admin web app."""

from __future__ import annotations

from enum import StrEnum
from pathlib import Path

TEMPLATES_DIR = Path(__file__).resolve().parent / "templates"


class SaleStatus(StrEnum):
    """Where an owned item stands in the resale flow. Stored as `_sale_status`."""

    none = "none"
    listed = "listed"
    sold_unconfirmed = "sold_unconfirmed"
    sold = "sold"
    reserved = "reserved"
    parted_sold = "parted_sold"
    wait_winter = "wait_winter"
    trash = "trash"


# --- Manual item upload ------------------------------------------------------

MEDIA_ITEMS_DIR = Path("media/items")

MAX_FILES = 10
MAX_BYTES = 15 * 1024 * 1024  # 15 MB per photo
MAX_SHORT_SIDE = 1200  # downscale so the shorter side is at most this many px
LOSSY_QUALITY = 85

FORMAT_BY_EXT = {
    ".jpg": "JPEG",
    ".jpeg": "JPEG",
    ".png": "PNG",
    ".webp": "WEBP",
    ".gif": "GIF",
}
ALLOWED_EXT = frozenset(FORMAT_BY_EXT)
