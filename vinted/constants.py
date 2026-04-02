from pathlib import Path

USER_AGENT = (
    "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) "
    "AppleWebKit/537.36 (KHTML, like Gecko) "
    "Chrome/124.0.0.0 Safari/537.36"
)


CATALOG_URL = "https://www.vinted.pl/catalog?catalog[]={catalog_id}&order=newest_first&page={page}"
PRODUCT_URL = "https://www.vinted.pl/items/{product_id}"

CATALOG_WOMEN_SKI_BOOTS = "2652"

CATALOG_RECIPES = {
    "4733": {
        "name": "Skis",
        "prompt": "skis.md",
        "target_group": "All",
    },
    "2683": {
        "name": "Men Ski boots",
        "prompt": "ski_boots.md",
        "target_group": "Men",
    },
    CATALOG_WOMEN_SKI_BOOTS: {
        "name": "Woman Ski boots",
        "prompt": "ski_boots.md",
        "target_group": "Women",
    },
    "2715": {
        "name": "Girls ski boots",
        "prompt": "ski_boots.md",
        "target_group": "Kids",
    },
    "2746": {
        "name": "Boys ski boots",
        "prompt": "ski_boots.md",
        "target_group": "Kids",
    },
}

PROMPTS_DIR = Path(__file__).parent.parent / "prompts"


RATING_STARS = {5: "⭐⭐⭐⭐⭐", 4: "⭐⭐⭐⭐", 3: "⭐⭐⭐", 2: "⭐⭐", 1: "⭐"}
RECOMMENDATION_LABEL = {
    "buy": "✅ Покупать",
    "negotiate": "🤝 Торговаться",
    "skip": "❌ Не покупать",
}
