from __future__ import annotations

from enum import StrEnum


class Recommendation(StrEnum):
    buy = "buy"
    negotiate = "negotiate"
    skip = "skip"


class ConditionState(StrEnum):
    new_with_tags = "new_with_tags"
    new_without_tags = "new_without_tags"
    very_good = "very_good"
    good = "good"
    satisfactory = "satisfactory"


class SellerTrust(StrEnum):
    high = "high"
    medium = "medium"
    low = "low"


class ItemStatus(StrEnum):
    """Lifecycle of an item as it moves through the pipeline."""

    new = "new"
    analyzed = "analyzed"
    notified = "notified"
    skipped = "skipped"
    failed = "failed"
