from __future__ import annotations

from enum import Enum
from typing import Optional

from pydantic import BaseModel
from pydantic import Field

from vinted.constants import CATALOG_WOMEN_SKI_BOOTS


class Recommendation(str, Enum):
    buy = "buy"
    negotiate = "negotiate"
    skip = "skip"


class ConditionState(str, Enum):
    new = "new"
    like_new = "like_new"
    good = "good"
    fair = "fair"
    poor = "poor"


class SellerTrust(str, Enum):
    high = "high"
    medium = "medium"
    low = "low"


class PriceRange(BaseModel):
    min: float = Field(description="Minimum estimate in PLN")
    max: float = Field(description="Maximum estimate in PLN")


class BaseAnalysis(BaseModel):
    rating: int = Field(description="Star rating 1-5 based on ROI", ge=1, le=5)
    recommendation: Recommendation = Field(description="buy / negotiate / skip")
    brand: str = Field(description="Product brand")
    model: str = Field(description="Product model")
    year: Optional[str] = Field(description="Year or season, e.g. 2022/2023")
    condition_state: ConditionState = Field(description="Actual condition from photos")
    condition_notes: str = Field(description="Detailed condition assessment")
    asking_price_pln: float = Field(description="Seller asking price + fees in PLN")
    estimated_resale_pln: PriceRange = Field(description="Expected resale price range")
    profit_estimate_pln: PriceRange = Field(description="Net profit after fees")
    roi_percent: float = Field(description="ROI = profit / asking_price * 100")
    red_flags: list[str] = Field(description="List of risks and warnings")
    seller_trust: SellerTrust = Field(description="Seller reliability assessment")
    negotiate_target: Optional[float] = Field(description="Suggested offer price if negotiate")
    summary: str = Field(description="2-3 sentence verdict in Russian")


class SkiBootsAnalysis(BaseAnalysis):
    flex_index: Optional[str] = Field(description="Boot flex index, e.g. 80, 100-110")
    mondo_size: Optional[str] = Field(description="Mondo point size, e.g. 25.0 / 25.5")
    is_rental: bool = Field(description="True if rental boot indicators detected")
    estimated_age_years: Optional[str] = Field(description="Estimated age or 'unknown'")
    safety_warning: Optional[str] = Field(description="Safety concern if old or cracked")
    sale_strategy: str = Field(description="Where to list, price strategy, what to highlight")


CATALOG_SCHEMAS: dict[str, type[BaseAnalysis]] = {
    CATALOG_WOMEN_SKI_BOOTS: SkiBootsAnalysis,
    "2683": SkiBootsAnalysis,
    "2715": SkiBootsAnalysis,
    "2746": SkiBootsAnalysis,
}


def get_schema(catalog_id: str) -> type[BaseAnalysis]:
    return CATALOG_SCHEMAS.get(catalog_id, BaseAnalysis)
