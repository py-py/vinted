from __future__ import annotations

from enum import IntEnum
from enum import StrEnum


class Catalog(IntEnum):
    """Known Vinted catalog ids (see constants.CATALOG_RECIPES)."""

    skis = 4733
    men_ski_boots = 2683
    women_ski_boots = 2652
    girls_ski_boots = 2715
    boys_ski_boots = 2746


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
