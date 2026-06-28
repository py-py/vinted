"""Anonymous (cookie-less) Vinted scraping — safe to run on a server.

- ``catalog`` — parse a catalog listing page.
- ``item`` — scrape a single product page.
- ``wardrobe`` — fetch a public user's wardrobe (items for sale) via JSON API.
"""

from .catalog import parse_catalog
from .catalog import parse_item
from .item import save_images
from .item import scrape_product
from .wardrobe import fetch_wardrobe

__all__ = [
    "parse_catalog",
    "parse_item",
    "save_images",
    "scrape_product",
    "fetch_wardrobe",
]
