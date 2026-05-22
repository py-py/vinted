from __future__ import annotations

import asyncio
import json
import mimetypes
import re
import sys
from pathlib import Path

import httpx
from bs4 import BeautifulSoup

from ..constants import PRODUCT_URL
from ..constants import USER_AGENT
from ..domain.product import VintedProduct
from ..domain.product import VintedSeller
from ..storage.gcs import product_prefix
from ..storage.gcs import upload_bytes


async def scrape_product(product_id: str, catalog_id: str | None = None) -> VintedProduct:
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
        seller["username"] = profile_el.get_text(strip=True)
        profile_link = profile_el.find_parent("a", href=True)
        if profile_link:
            seller["link"] = profile_link["href"]

    if location_el := soup.find(attrs={"data-testid": "seller-location"}):
        seller["location"] = location_el.get_text(strip=True)

    # Fallback
    if not seller.get("location"):
        # extract location from <script> JSON data
        if m := re.search(r'country_title_local\\?"?\s*:\s*\\?"([^"\\]+)', resp.text):
            seller["location"] = m.group(1)

    # Rating — from aria-label on the rating container
    if rating_el := soup.find(attrs={"aria-label": True}, class_=lambda c: c and "Rating" in c):
        aria = rating_el.get("aria-label", "")
        stars_match = re.search(r"([\d.,]+)\s", aria)
        if stars_match:
            seller["stars"] = float(stars_match.group(1).replace(",", "."))
        label_el = rating_el.select_one("[class*='Rating__label']")
        if label_el:
            seller["reviews"] = int(label_el.get_text(strip=True))

    # --- Price --- from "total-combined-price" section
    price_el = soup.find(attrs={"data-testid": "total-combined-price"})
    price_text = price_el.get_text(strip=True)
    price_match = re.search(r"([\d.,]+)\s*(\S+)", price_text)
    price = float(price_match.group(1).replace(",", "."))

    # --- JSON-LD ---
    ld_json = {}
    if ld_script := soup.find("script", type="application/ld+json"):
        ld_json = json.loads(ld_script.string)

    # Fallback
    if not catalog_id:
        # extract catalog_id from <script> JSON data
        if m := re.search(r'catalog_id\\?"?\s*:\s*(\d+)', resp.text):
            catalog_id = m.group(1)

    return VintedProduct(
        id=product_id,
        title=title,
        description=description,
        catalog_id=catalog_id or "",
        url=url,
        price=price,
        properties=properties,
        image_urls=image_urls,
        seller=VintedSeller(**seller),
        ld_json=ld_json,
    )


async def save_images(image_urls: list[str], product_id: str) -> list[str]:
    """Download images and upload them to GCS under ``products/{product_id}/``.

    Returns the list of blob names that were written.
    """
    prefix = product_prefix(product_id)

    async with httpx.AsyncClient() as client:

        async def _store(i: int, url: str) -> str:
            resp = await client.get(url)
            resp.raise_for_status()
            ext = Path(url.split("?")[0]).suffix or ".jpg"
            blob_name = f"{prefix}/{i}{ext}"
            content_type = mimetypes.guess_type(blob_name)[0]
            await upload_bytes(blob_name, resp.content, content_type=content_type)
            print(f"-> Uploaded: {blob_name}")
            return blob_name

        return list(await asyncio.gather(*(_store(i, url) for i, url in enumerate(image_urls, 1))))


async def main() -> None:
    product_id = sys.argv[1] if len(sys.argv) > 1 else None
    catalog_id = sys.argv[2] if len(sys.argv) > 2 else None

    if product_id is None:
        raise SystemExit("Usage: python -m vinted.scrapers.product <product_id> [catalog_id]")

    product = await scrape_product(product_id, catalog_id=catalog_id)

    if product.image_urls:
        await save_images(product.image_urls, product_id)

    print(product.model_dump_json(indent=2, exclude={}))


if __name__ == "__main__":
    asyncio.run(main())
