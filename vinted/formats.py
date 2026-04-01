from __future__ import annotations

RATING_STARS = {5: "⭐⭐⭐⭐⭐", 4: "⭐⭐⭐⭐", 3: "⭐⭐⭐", 2: "⭐⭐", 1: "⭐"}
RECOMMENDATION_LABEL = {
    "buy": "✅ Покупать",
    "negotiate": "🤝 Торговаться",
    "skip": "❌ Пропустить",
}


def format_analysis(data: dict) -> str:
    rating = data.get("rating", "?")
    stars = RATING_STARS.get(rating, "?")
    rec = RECOMMENDATION_LABEL.get(data.get("recommendation", ""), data.get("recommendation", ""))

    resale = data.get("estimated_resale_pln", {})
    profit = data.get("profit_estimate_pln", {})

    lines = [
        f"{stars} {rating}/5 — {rec}",
        "",
        f"🏷 {data.get('brand', '?')} {data.get('model', '?')}",
        f"📅 Year: {data.get('year') or 'н/д'}",
        f"📊 State: {data.get('condition_state', '?')}",
        "",
        f"💰 Price: {data.get('asking_price_pln', '?')} PLN",
        f"💵 Resale: {resale.get('min', '?')} – {resale.get('max', '?')} PLN",
        f"📈 Profit: {profit.get('min', '?')} – {profit.get('max', '?')} PLN",
        f"📊 ROI: {data.get('roi_percent', '?')}%",
    ]

    if data.get("negotiate_target"):
        lines.append(f"🎯 Negotiate up to: {data['negotiate_target']} PLN")

    if data.get("red_flags"):
        lines += ["", "🚩 Red flags:"]
        for flag in data["red_flags"]:
            lines.append(f"  • {flag}")

    if data.get("sale_strategy"):
        lines += ["", f"📋 Strategy: {data['sale_strategy']}"]

    return "\n".join(lines)
