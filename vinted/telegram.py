from __future__ import annotations

import os

import httpx
from dotenv import load_dotenv

from .exceptions import BadRequestHTTPException
from .models import VintedProduct

load_dotenv()

BOT_TOKEN = os.environ["TELEGRAM_BOT_TOKEN"]
CHAT_ID = os.environ["TELEGRAM_CHAT_ID"]
API_URL = f"https://api.telegram.org/bot{BOT_TOKEN}"


async def send_message(
    product: VintedProduct,
    analysis: str,
    parse_mode: str = "Markdown",
) -> None:
    message = f"▶ {product.title} ◀\n{product.url}\n{analysis}"

    async with httpx.AsyncClient() as client:
        try:
            reply = await client.post(
                f"{API_URL}/sendPhoto",
                json={
                    "chat_id": CHAT_ID,
                    "caption": message,
                    "photo": product.main_image_url,
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
