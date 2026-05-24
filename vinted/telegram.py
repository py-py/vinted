from __future__ import annotations

import os

import httpx
from dotenv import load_dotenv

from .exceptions import BadRequestHTTPException
from .models import VintedProduct

load_dotenv()

BOT_TOKEN = os.environ["TELEGRAM_BOT_TOKEN"]
# Optional: the notifier passes chat_id per subscription, so it may be unset.
CHAT_ID = os.environ.get("TELEGRAM_CHAT_ID")
API_URL = f"https://api.telegram.org/bot{BOT_TOKEN}"


def format_item_caption(item: dict) -> str:
    """Build a Telegram caption for a single catalog item dict."""
    parts = [f"▶ {item.get('title') or '—'} ◀"]
    fields = (item.get("brand"), item.get("size"), item.get("condition"))
    if meta := " · ".join(v for v in fields if v):
        parts.append(meta)
    if price := item.get("price"):
        parts.append(f"💶 {price}")
    if url := item.get("url"):
        parts.append(url)
    caption = "\n".join(parts)
    return caption[:1021] + "..." if len(caption) > 1024 else caption


def send_item(chat_id: int | str, item: dict) -> None:
    """Send a single catalog item to Telegram as photo + caption (sync)."""
    caption = format_item_caption(item)
    image_url = item.get("image_url")

    if image_url:
        endpoint = "sendPhoto"
        payload = {"chat_id": chat_id, "photo": image_url, "caption": caption}
    else:
        endpoint = "sendMessage"
        payload = {"chat_id": chat_id, "text": caption}

    with httpx.Client() as client:
        reply = client.post(f"{API_URL}/{endpoint}", json=payload)
        try:
            reply.raise_for_status()
        except httpx.HTTPStatusError:
            if reply.status_code == 400:
                raise BadRequestHTTPException(
                    message=reply.text,
                    status_code=reply.status_code,
                )
            raise


def build_media_payload(product: VintedProduct, message: str) -> list[dict]:
    media = []
    for i, url in enumerate(product.image_urls[:10]):
        item = {"type": "photo", "media": url}
        if i == 0:
            item["caption"] = message
        media.append(item)
    return media


async def send_message(product: VintedProduct, summary: str) -> None:
    message = f"▶ {product.title} ◀\n{product.url}\n{summary}"
    cutted_message = message[:1021] + "..." if len(message) > 1024 else message
    media_payload = build_media_payload(product, cutted_message)

    async with httpx.AsyncClient() as client:
        try:
            reply = await client.post(
                f"{API_URL}/sendMediaGroup",
                json={
                    "chat_id": CHAT_ID,
                    "media": media_payload,
                },
            )
            reply.raise_for_status()
        except httpx.HTTPStatusError:
            if reply.status_code == 400:
                raise BadRequestHTTPException(
                    message=reply.text,
                    status_code=reply.status_code,
                )
            raise
