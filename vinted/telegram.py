from __future__ import annotations

import os

import httpx
from dotenv import load_dotenv

from .models import VintedProduct

load_dotenv()

BOT_TOKEN = os.environ["TELEGRAM_BOT_TOKEN"]
CHAT_ID = os.environ["TELEGRAM_CHAT_ID"]
API_URL = f"https://api.telegram.org/bot{BOT_TOKEN}"


async def send_message(
    product: VintedProduct, analysis: str, parse_mode: str = "Markdown"
) -> None:
    """
    Send a text message to the configured Telegram chat.
    Telegram limit is 4096 chars per message

    data = product.model_dump_json(exclude={"ld_json","image_urls"}, indent=2)
    message = f"## [{product.title}]({product.url})\n\n```json {data}```"
    """
    image_urls = product.image_urls
    message = f"*{product.title}* [URL]({product.url})\n\n\n```json {analysis}```"
    async with httpx.AsyncClient() as client:
        reply = await client.post(
            f"{API_URL}/sendPhoto",
            json={
                "chat_id": CHAT_ID,
                "caption": message,
                "parse_mode": parse_mode,
                "photo": image_urls[0],
            },
        )
        print(reply.status_code, reply.text)
        print(product)


async def send_photos(image_paths: list[str], caption: str = "") -> None:
    """Send photos to the configured Telegram chat."""
    async with httpx.AsyncClient() as client:
        for i, path in enumerate(image_paths):
            with open(path, "rb") as f:
                data = {"chat_id": CHAT_ID}
                if i == 0 and caption:
                    data["caption"] = caption[:1024]
                await client.post(
                    f"{API_URL}/sendPhoto",
                    data=data,
                    files={"photo": f},
                )
