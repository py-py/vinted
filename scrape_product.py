"""
Vinted product scraper using httpx + BeautifulSoup (no browser needed).

Usage:
    pip install httpx beautifulsoup4
    python scrape_product.py [product_id]
"""

import asyncio
import json
import re
import sys
from pathlib import Path

import httpx
from bs4 import BeautifulSoup

from constants import PRODUCT_URL
from models import VintedProduct
from models import VintedSeller

USER_AGENT = (
    "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) "
    "AppleWebKit/537.36 (KHTML, like Gecko) "
    "Chrome/124.0.0.0 Safari/537.36"
)


async def scrape_product(product_id: str, catalog_id: str) -> VintedProduct:
    url = PRODUCT_URL.format(product_id=product_id)

    async with httpx.AsyncClient(
        headers={"User-Agent": USER_AGENT}, follow_redirects=True
    ) as client:
        print(f"-> Fetching: {url}")
        resp = await client.get(url)
        resp.raise_for_status()

    soup = BeautifulSoup(resp.text, "html.parser")

    # --- Title ---
    title = soup.title.get_text(strip=True) if soup.title else ""
    title = title.removesuffix(" | Vinted")

    # --- Images --- all unique image URLs from .item-photos
    image_urls = []
    if photos_div := soup.select_one(".item-photos"):
        for img in photos_div.find_all("img"):
            src = img.get("src") or img.get("data-src")
            if src and src not in image_urls:
                image_urls.append(src)

    # --- Properties --- from .details-list--details
    properties = {}
    if details_div := soup.select_one(".details-list--details"):
        for item in details_div.select(".details-list__item"):
            vals = item.select(".details-list__item-value")
            if len(vals) >= 2:
                key = vals[0].get_text(strip=True)
                # Remove hidden overflow menus/buttons from value
                val_clone = vals[1]
                for hidden in val_clone.select("button, [class*='overflow-menu']"):
                    hidden.decompose()
                value = val_clone.get_text(strip=True)
                properties[key] = value

    # --- Description --- full text (no CSS clipping in raw HTML)
    description = ""
    if desc_div := soup.select_one("div.u-text-wrap"):
        description = desc_div.get_text("\n", strip=True)

    # --- Seller ---
    seller = {}
    if profile_el := soup.find(attrs={"data-testid": "profile-username"}):
        seller["name"] = profile_el.get_text(strip=True)
        profile_link = profile_el.find_parent("a", href=True)
        if profile_link:
            seller["link"] = profile_link["href"]

    if location_el := soup.find(attrs={"data-testid": "seller-location"}):
        seller["location"] = location_el.get_text(strip=True)

    # Rating — from aria-label on the rating container
    if rating_el := soup.find(attrs={"aria-label": True}, class_=lambda c: c and "Rating" in c):
        aria = rating_el.get("aria-label", "")
        stars_match = re.search(r"([\d.,]+)\s", aria)
        if stars_match:
            seller["stars"] = float(stars_match.group(1).replace(",", "."))
        label_el = rating_el.select_one("[class*='Rating__label']")
        if label_el:
            seller["reviews"] = int(label_el.get_text(strip=True))

    # --- JSON-LD ---
    ld_json = {}
    if ld_script := soup.find("script", type="application/ld+json"):
        ld_json = json.loads(ld_script.string)

    return VintedProduct(
        id=product_id,
        catalog_id=catalog_id,
        url=url,
        title=title,
        image_urls=image_urls,
        description=description,
        properties=properties,
        seller=VintedSeller(**seller),
        ld_json=ld_json,
    )


async def save_images(image_urls: list[str], folder: Path) -> None:
    """Download images to ./media/products/{product_id}/."""
    folder.mkdir(parents=True, exist_ok=True)

    async with httpx.AsyncClient() as client:

        async def _download(i: int, url: str) -> None:
            resp = await client.get(url)
            resp.raise_for_status()
            ext = Path(url.split("?")[0]).suffix or ".jpg"
            filepath = folder / f"{i}{ext}"
            filepath.write_bytes(resp.content)
            print(f"-> Saved: {filepath}")

        await asyncio.gather(*(_download(i, url) for i, url in enumerate(image_urls, 1)))


async def main() -> None:
    product_id = sys.argv[1] if len(sys.argv) > 1 else "8119502397"
    catalog_id = sys.argv[2] if len(sys.argv) > 2 else "2652"

    product = await scrape_product(product_id, catalog_id)

    folder = Path("media/products") / product_id
    if product.image_urls:
        await save_images(product.image_urls, folder)

    print(product.model_dump_json(indent=2))


if __name__ == "__main__":
    asyncio.run(main())
