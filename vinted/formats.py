from __future__ import annotations

from .constants import CATALOG_RECIPES
from .models import VintedProduct
from .schemas import SkiBootsAnalysis

RATING_STARS = {5: "⭐⭐⭐⭐⭐", 4: "⭐⭐⭐⭐", 3: "⭐⭐⭐", 2: "⭐⭐", 1: "⭐"}
RECOMMENDATION_LABEL = {
    "buy": "✅ Покупать",
    "negotiate": "🤝 Торговаться",
    "skip": "❌ Пропустить",
}


def format_analytics(product: VintedProduct, data: SkiBootsAnalysis) -> str:
    stars = RATING_STARS.get(data.rating, "?")
    rec = RECOMMENDATION_LABEL.get(data.recommendation.value, data.recommendation.value)

    lines = [
        f"{stars} {data.rating}/5 — {rec}",
        "",
        f"🏷 {data.brand} {data.model}",
        f"👤 For: {CATALOG_RECIPES.get(product.catalog_id, {}).get('target_group', '-')}",
        f"👢 Size: {data.mondo_size or '-'} cm (EU {data.eu_size or '-'})",
        f"📅 Year: {data.year or 'н/д'}",
        f"📊 State: {data.condition_state.value}",
    ]

    lines += [
        "",
        f"💰 Price: {data.asking_price_pln} PLN",
        f"🚚 Delivery: ~{data.estimated_delivery_pln} PLN (from {product.seller.location or '-'})",
        f"💵 Resale: {data.estimated_resale_pln.min} – {data.estimated_resale_pln.max} PLN",
        f"📈 Profit: {data.profit_estimate_pln.min} – {data.profit_estimate_pln.max} PLN",
        f"📊 ROI: {data.roi_percent}%",
    ]

    if data.negotiate_target:
        lines.append(f"🎯 Negotiate up to: {data.negotiate_target} PLN")

    if data.red_flags:
        lines += ["", "🚩 Red flags:"]
        for flag in data.red_flags:
            lines.append(f"  • {flag}")

    if data.green_flags:
        lines += ["", "✅ Green flags:"]
        for flag in data.green_flags:
            lines.append(f"  • {flag}")

    lines += ["", f"💬 Summary: {data.summary}"]

    return "\n".join(lines)
