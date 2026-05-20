from __future__ import annotations

from typing import TYPE_CHECKING
from typing import Optional

from pydantic import BaseModel
from pydantic import Field

from ..constants import CATALOG_RECIPES
from ..constants import RATING_STARS
from ..constants import RECOMMENDATION_LABEL
from .enums import ConditionState
from .enums import Recommendation
from .enums import SellerTrust

if TYPE_CHECKING:
    from .product import VintedProduct


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
    asking_price_pln: float = Field(description="Seller asking price (listing price) in PLN")
    estimated_delivery_pln: float = Field(
        description="Estimated delivery cost in PLN based on seller location",
    )
    estimated_resale_pln: PriceRange = Field(description="Expected resale price range")
    profit_estimate_pln: PriceRange = Field(description="Net profit after fees and delivery")
    roi_percent: float = Field(description="ROI = profit / asking_price * 100")
    red_flags: list[str] = Field(
        description="Negative signs: damage, fakes, missing parts, old age, etc.",
    )
    green_flags: list[str] = Field(
        description="Positive signs: good condition, popular brand, attractive price, etc",
    )
    seller_trust: SellerTrust = Field(description="Seller reliability assessment")
    negotiate_target: Optional[float] = Field(description="Suggested offer price if negotiate")
    negotiate_message: Optional[str] = Field(
        description="Recommendation what to write to the seller: proposed price and reasoning",
    )
    summary: str = Field(description="2-3 sentence verdict in Russian")
    sale_strategy: str = Field(
        description="Resale advice: where to list, starting price, what to highlight for buyers",
    )

    def format(self, product: VintedProduct) -> str:
        stars = RATING_STARS.get(self.rating, "?")
        rec = RECOMMENDATION_LABEL.get(self.recommendation.value, self.recommendation.value)

        lines = [
            f"{stars} {self.rating}/5 — {rec}",
            "",
            f"🏷 {self.brand} {self.model}",
            f"📅 Year: {self.year or '-'}",
            f"📊 State: {self.condition_state.value}",
        ]

        lines += self.format_child_attributes(product)

        lines += [
            "",
            f"💰 Price: {self.asking_price_pln} PLN",
            f"🚚 Delivery: ~{self.estimated_delivery_pln} PLN (from {product.seller.location or '-'})",  # NOQA: E501
            f"💵 Resale: {self.estimated_resale_pln.min} – {self.estimated_resale_pln.max} PLN",
            f"📈 Profit: {self.profit_estimate_pln.min} – {self.profit_estimate_pln.max} PLN",
            f"📊 ROI: {self.roi_percent}%",
        ]

        if self.negotiate_target:
            lines.append(f"🎯 Negotiate up to: {self.negotiate_target} PLN")

        if self.red_flags:
            lines += ["", "🚩 Red flags:"]
            for flag in self.red_flags:
                lines.append(f"  • {flag}")

        if self.green_flags:
            lines += ["", "✅ Green flags:"]
            for flag in self.green_flags:
                lines.append(f"  • {flag}")

        lines += ["", f"💬 Summary: {self.summary}"]

        return "\n".join(lines)

    def format_child_attributes(self, product):
        return []


class SkiBootsAnalysis(BaseAnalysis):
    flex_index: Optional[str] = Field(description="Boot flex index, e.g. 80, 100-110")
    mondo_size: Optional[str] = Field(description="Mondopoint size in cm, e.g. 25.0 / 25.5")
    eu_size: Optional[str] = Field(description="EU size, e.g. 38, 42")
    is_rental: bool = Field(description="True if rental boot indicators detected")
    estimated_age_years: Optional[str] = Field(description="Estimated age or 'unknown'")
    safety_warning: Optional[str] = Field(description="Safety concern if old or cracked")

    def format_child_attributes(self, product):
        return [
            f"👤 For: {CATALOG_RECIPES.get(product.catalog_id, {}).get('target_group', '-')}",
            f"👢 Size: {self.mondo_size or '-'} cm (EU {self.eu_size or '-'})",
        ]


PROMPT_SCHEMAS: dict[str, type[BaseAnalysis]] = {
    "ski_boots.md": SkiBootsAnalysis,
}


def get_schema(catalog_id: str) -> type[BaseAnalysis]:
    recipe = CATALOG_RECIPES.get(catalog_id, {})
    prompt_file = recipe.get("prompt", "")
    return PROMPT_SCHEMAS.get(prompt_file, BaseAnalysis)
