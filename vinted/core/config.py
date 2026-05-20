from __future__ import annotations

from functools import lru_cache
from typing import Literal

from pydantic_settings import BaseSettings
from pydantic_settings import SettingsConfigDict


class Settings(BaseSettings):
    """Central configuration, loaded from environment / .env.

    Field names map to upper-case env vars (e.g. ``gemini_api_key`` -> ``GEMINI_API_KEY``).
    All fields are optional so the package imports cleanly without a populated environment;
    missing credentials only fail when the relevant client is actually used.
    """

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        extra="ignore",
    )

    # --- Vinted ---
    vinted_user_id: str | None = None
    vinted_locale: str = "pl"

    # --- Telegram ---
    telegram_bot_token: str | None = None
    telegram_chat_id: str | None = None

    # --- LLM provider ---
    llm_provider: Literal["gemini", "claude"] = "gemini"
    gemini_api_key: str | None = None
    gemini_model: str = "gemini-2.5-flash"
    anthropic_api_key: str | None = None
    claude_model: str = "claude-sonnet-4-6"

    # --- GCP / Firestore ---
    gcp_project: str | None = None
    firestore_collection: str = "items"

    # --- Notification policy ---
    notify_min_rating: int = 4
    notify_recommendations: list[str] = ["buy", "negotiate"]


@lru_cache
def get_settings() -> Settings:
    """Return a cached Settings instance."""
    return Settings()
