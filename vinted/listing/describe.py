"""
Listing text from photos: a vision LLM (via pydantic-ai) suggests a title and a description
for a new listing. Nothing is saved here; the admin UI shows the suggestion as an unsaved draft.

Env (all required): LISTING_PROVIDER (`google` or `deepseek`), then that provider's key and
model: GEMINI_API_KEY / GEMINI_MODEL, or DEEPSEEK_API_KEY / DEEPSEEK_MODEL.
"""

from __future__ import annotations

import os
from dataclasses import dataclass

from pydantic import BaseModel
from pydantic import Field
from pydantic_ai import Agent
from pydantic_ai import BinaryContent
from pydantic_ai.settings import ModelSettings

from ..constants import PROMPTS_DIR
from .photos import MAX_PHOTOS_PER_LISTING

# Every photo is sent: the size tag is often one of the last ones.
MAX_PHOTOS = MAX_PHOTOS_PER_LISTING


class ListingText(BaseModel):
    title: str = Field(description="Short Vinted listing title")
    description: str = Field(description="Listing description for buyers")


@dataclass(frozen=True)
class Provider:
    model_env: str
    settings: ModelSettings


BASE_SETTINGS: ModelSettings = {"temperature": 0.2}

PROVIDERS: dict[str, Provider] = {
    "google": Provider(
        model_env="GEMINI_MODEL",
        settings={},
    ),
    "deepseek": Provider(
        model_env="DEEPSEEK_MODEL",
        # Thinking mode rejects the forced tool_choice used for structured output.
        settings={"extra_body": {"thinking": {"type": "disabled"}}},
    ),
}


def resolve(name: str) -> tuple[str, ModelSettings]:
    """The pydantic-ai `provider:model` string and model settings for provider `name`."""
    if name not in PROVIDERS:
        raise ValueError(f"LISTING_PROVIDER must be one of {sorted(PROVIDERS)}, got {name!r}")
    provider = PROVIDERS[name]
    model = os.environ[provider.model_env]
    return f"{name}:{model}", {**BASE_SETTINGS, **provider.settings}


LISTING_PROVIDER = os.environ["LISTING_PROVIDER"]
MODEL, MODEL_SETTINGS = resolve(LISTING_PROVIDER)

agent = Agent(
    MODEL,
    output_type=ListingText,
    instructions=(PROMPTS_DIR / "listing.md").read_text(),
    model_settings=MODEL_SETTINGS,
    defer_model_check=True,
)


def describe(photos: list[bytes], notes: str | None = None) -> ListingText:
    """Suggest a title and description from listing photos (JPEGs, main photo first).

    `notes`: facts from the seller the photos can't show (e.g. "new, never worn").
    """
    images = [BinaryContent(data, media_type="image/jpeg") for data in photos[:MAX_PHOTOS]]
    prompt = "Write the listing for the item in these photos. The first photo is the main one."
    if notes and notes.strip():
        prompt += f"\n\nSeller's notes about the item (trust them):\n{notes.strip()}"
    return agent.run_sync([prompt, *images]).output
