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

PRODUCT_URL = "https://www.vinted.pl/items/{product_id}"
USER_AGENT = (
    "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) "
    "AppleWebKit/537.36 (KHTML, like Gecko) "
    "Chrome/124.0.0.0 Safari/537.36"
)


async def scrape_product(product_id: str) -> dict:
    url = PRODUCT_URL.format(product_id=product_id)

    async with httpx.AsyncClient(headers={"User-Agent": USER_AGENT}, follow_redirects=True) as client:
        print(f"-> Fetching: {url}")
        resp = await client.get(url)
        resp.raise_for_status()

    soup = BeautifulSoup(resp.text, "html.parser")

    # JSON-LD structured data
    ld_json = {}
    ld_script = soup.find("script", type="application/ld+json")
    if ld_script:
        ld_json = json.loads(ld_script.string)

    # Images — all unique image URLs from .item-photos
    image_urls = []
    photos_div = soup.select_one(".item-photos")
    if photos_div:
        for img in photos_div.find_all("img"):
            src = img.get("src") or img.get("data-src")
            if src and src not in image_urls:
                image_urls.append(src)

    # Properties from .details-list--details
    properties = {}
    details_div = soup.select_one(".details-list--details")
    if details_div:
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

    # Description — full text (no CSS clipping in raw HTML)
    description = ""
    desc_div = soup.select_one("div.u-text-wrap")
    if desc_div:
        description = desc_div.get_text("\n", strip=True)

    # Seller info
    seller = {}
    profile_el = soup.find(attrs={"data-testid": "profile-username"})
    if profile_el:
        seller["name"] = profile_el.get_text(strip=True)
        profile_link = profile_el.find_parent("a", href=True)
        if profile_link:
            seller["link"] = profile_link["href"]

    location_el = soup.find(attrs={"data-testid": "seller-location"})
    if location_el:
        seller["location"] = location_el.get_text(strip=True)

    # Rating — from aria-label on the rating container
    rating_el = soup.find(attrs={"aria-label": True}, class_=lambda c: c and "Rating" in c)
    if rating_el:
        aria = rating_el.get("aria-label", "")
        stars_match = re.search(r"([\d.,]+)\s", aria)
        if stars_match:
            seller["stars"] = float(stars_match.group(1).replace(",", "."))
        label_el = rating_el.select_one("[class*='Rating__label']")
        if label_el:
            seller["reviews"] = int(label_el.get_text(strip=True))

    return {
        "product_id": product_id,
        "url": url,
        "description": description,
        "properties": properties,
        "seller": seller,
        "image_urls": image_urls,
        "ld_json": ld_json,
    }


async def save_images(image_urls: list[str], product_id: str) -> None:
    """Download images to ./media/products/{product_id}/."""
    folder = Path("media/products") / product_id
    folder.mkdir(parents=True, exist_ok=True)

    async with httpx.AsyncClient() as client:
        for i, img_url in enumerate(image_urls, 1):
            resp = await client.get(img_url)
            resp.raise_for_status()
            ext = Path(img_url.split("?")[0]).suffix or ".jpg"
            filepath = folder / f"{i}{ext}"
            filepath.write_bytes(resp.content)
            print(f"  Saved: {filepath}")


async def main() -> None:
    product_id = sys.argv[1] if len(sys.argv) > 1 else "8119502397"
    product = await scrape_product(product_id)

    if product["seller"]:
        s = product["seller"]
        print(f"\nSeller: {s.get('name', '?')}")
        print(f"  Link: https://www.vinted.pl{s.get('link', '')}")
        print(f"  Stars: {s.get('stars', '?')} / 5")
        print(f"  Reviews: {s.get('reviews', '?')}")
        print(f"  Location: {s.get('location', '?')}")

    if product["properties"]:
        print("\nProperties:")
        for key, value in product["properties"].items():
            print(f"  {key}: {value}")

    if product["description"]:
        print(f"\nDescription:\n  {product['description']}")

    if product["ld_json"]:
        print(f"\nJSON-LD:\n  {json.dumps(product['ld_json'], indent=2, ensure_ascii=False)}")

    if not product["image_urls"]:
        print("\nNo images found.")
        return

    print(f"\nFound {len(product['image_urls'])} image(s), saving...\n")
    await save_images(product["image_urls"], product_id)


if __name__ == "__main__":
    asyncio.run(main())