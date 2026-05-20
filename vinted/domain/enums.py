from __future__ import annotations

from enum import StrEnum


class Recommendation(StrEnum):
    buy = "buy"
    negotiate = "negotiate"
    skip = "skip"


class ConditionState(StrEnum):
    new = "new"
    like_new = "like_new"
    good = "good"
    fair = "fair"
    poor = "poor"


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
