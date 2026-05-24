from __future__ import annotations

import argparse
import os

from dotenv import load_dotenv

from .store import JsonStore


def main() -> None:
    load_dotenv()
    parser = argparse.ArgumentParser(description="Add a Vinted catalog subscription.")
    parser.add_argument("url", help="Full Vinted catalog/search URL to poll")
    parser.add_argument("--chat", type=int, default=None, help="Telegram chat_id")
    args = parser.parse_args()

    chat_id = args.chat
    if chat_id is None:
        env_chat = os.environ.get("TELEGRAM_CHAT_ID")
        if not env_chat:
            raise SystemExit("Provide --chat or set TELEGRAM_CHAT_ID in .env")
        chat_id = int(env_chat)

    sub = JsonStore().add_subscription(chat_id, args.url)
    print(f"Added subscription {sub.id}: chat={sub.telegram_chat_id}")
    print(f"  url: {sub.url}")


if __name__ == "__main__":
    main()
