"""Anonymous (cookie-less) Vinted scraping — safe to run on a server.

- ``catalog`` — parse a catalog listing page.
- ``item`` — scrape a single product page.
"""

from .catalog import parse_catalog
from .catalog import parse_item
from .item import save_images
from .item import scrape_product

__all__ = [
    "parse_catalog",
    "parse_item",
    "save_images",
    "scrape_product",
]
