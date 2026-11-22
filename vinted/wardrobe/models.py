from __future__ import annotations

from enum import StrEnum


class ItemState(StrEnum):
    """Our tracking state of a wardrobe item (custom field `state`)."""

    ACTIVE = "active"
    RESERVED = "reserved"
    SOLD = "sold"
    DELETED = "deleted"
    UNKNOWN = "unknown"


class MemberState(StrEnum):
    """Account state of a tracked member, read from their profile page (`state`)."""

    ACTIVE = "active"
    BANNED = "banned"
    DELETED = "deleted"


# States that can still change: re-checked on every sync while missing.
OPEN_STATES = frozenset({ItemState.ACTIVE, ItemState.RESERVED, ItemState.UNKNOWN})
