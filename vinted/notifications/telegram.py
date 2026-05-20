from __future__ import annotations

import httpx

from ..core.config import get_settings
from ..core.exceptions import BadRequestHTTPException
from ..domain.product import VintedProduct


def build_media_payload(product: VintedProduct, message: str) -> list[dict]:
    media = []
    for i, url in enumerate(product.image_urls[:10]):
        item = {"type": "photo", "media": url}
        if i == 0:
            item["caption"] = message
        media.append(item)
    return media


async def send_message(product: VintedProduct, summary: str) -> None:
    settings = get_settings()
    api_url = f"https://api.telegram.org/bot{settings.telegram_bot_token}"

    message = f"▶ {product.title} ◀\n{product.url}\n{summary}"
    cutted_message = message[:1021] + "..." if len(message) > 1024 else message
    media_payload = build_media_payload(product, cutted_message)

    async with httpx.AsyncClient() as client:
        try:
            reply = await client.post(
                f"{api_url}/sendMediaGroup",
                json={
                    "chat_id": settings.telegram_chat_id,
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
