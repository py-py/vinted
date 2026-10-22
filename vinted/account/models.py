from __future__ import annotations

from enum import StrEnum


class SaleStatus(StrEnum):
    NONE = "none"
    LISTED = "listed"
    SOLD_UNCONFIRMED = "sold_unconfirmed"
    SOLD = "sold"
    RESERVED = "reserved"
    PARTED_SOLD = "parted_sold"
    WAIT_WINTER = "wait_winter"
    TRASH = "trash"
