USER_AGENT = (
    "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) "
    "AppleWebKit/537.36 (KHTML, like Gecko) "
    "Chrome/124.0.0.0 Safari/537.36"
)


CATALOG_URL = "https://www.vinted.pl/catalog?catalog[]={catalog_id}&order=newest_first&page={page}"
PRODUCT_URL = "https://www.vinted.pl/items/{product_id}"

CATALOG_RECIPES = {
    "4733": {"name": "Skis", "prompt": "skis.md"},
    "2683": {"name": "Man Ski boots", "prompt": "ski_boots.md"},
    "2652": {"name": "Woman Ski boots", "prompt": "ski_boots.md"},
    "2715": {"name": "Girls ski boots", "prompt": "ski_boots.md"},
    "2746": {"name": "Boys ski boots", "prompt": "ski_boots.md"},
}
