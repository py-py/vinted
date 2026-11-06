"""
Listing text from photos: a Gemini vision model (via pydantic-ai) suggests a title and a
description for a new listing. Nothing is saved here; the admin UI shows the suggestion as an
unsaved draft.

Env: GEMINI_API_KEY, GEMINI_MODEL (default `gemini-2.5-flash`).
"""

from __future__ import annotations

import os

from pydantic import BaseModel
from pydantic import Field
from pydantic_ai import Agent
from pydantic_ai import BinaryContent

from ..constants import PROMPTS_DIR
from .photos import MAX_PHOTOS_PER_LISTING

DEFAULT_MODEL = "gemini-2.5-flash"
# Every photo is sent: the size tag is often one of the last ones.
MAX_PHOTOS = MAX_PHOTOS_PER_LISTING


class ListingText(BaseModel):
    title: str = Field(description="Short Vinted listing title")
    description: str = Field(description="Listing description for buyers")


# `defer_model_check`: the provider (and its API key) is resolved on the first run, so importing
# this module (the admin app, tests) works without GEMINI_API_KEY.
agent = Agent(
    f"google:{os.environ.get('GEMINI_MODEL', DEFAULT_MODEL)}",
    output_type=ListingText,
    instructions=(PROMPTS_DIR / "listing.md").read_text(),
    # Low temperature: the same photos should give the same size and model every time.
    model_settings={"temperature": 0.2},
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
