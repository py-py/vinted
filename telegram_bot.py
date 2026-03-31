from __future__ import annotations

import os
from dotenv import load_dotenv

import httpx


load_dotenv()

BOT_TOKEN = os.environ["TELEGRAM_BOT_TOKEN"]
CHAT_ID = os.environ["TELEGRAM_CHAT_ID"]
API_URL = f"https://api.telegram.org/bot{BOT_TOKEN}"


async def send_message(text: str, image_path: str, parse_mode: str = "Markdown") -> None:
    """
    Send a text message to the configured Telegram chat.
    Telegram limit is 4096 chars per message
    """
    async with httpx.AsyncClient() as client:
        with open(image_path, "rb") as f:
            await client.post(
                f"{API_URL}/sendMessage",
                data={
                    "chat_id": CHAT_ID,
                    "text": text,
                    "parse_mode": parse_mode,
                },
                files={"photo": f},
            )


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
