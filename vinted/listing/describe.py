"""
Listing text from photos: a DeepSeek vision model (via pydantic-ai) suggests a title and a
description for a new listing. Nothing is saved here; the admin UI shows the suggestion as an
unsaved draft.

Env: DEEPSEEK_API_KEY, DEEPSEEK_MODEL (a vision-capable model, default `deepseek-flash`).
"""

from __future__ import annotations

import os

from pydantic import BaseModel
from pydantic import Field
from pydantic_ai import Agent
from pydantic_ai import BinaryContent

from ..constants import PROMPTS_DIR

DEFAULT_MODEL = "deepseek-flash"
# Main photo plus a few detail shots is enough; more only adds cost.
MAX_PHOTOS = 8


class ListingText(BaseModel):
    title: str = Field(description="Short Vinted listing title")
    description: str = Field(description="Listing description for buyers")


# `defer_model_check`: the provider (and its API key) is resolved on the first run, so importing
# this module (the admin app, tests) works without DEEPSEEK_API_KEY.
agent = Agent(
    f"deepseek:{os.environ.get('DEEPSEEK_MODEL', DEFAULT_MODEL)}",
    output_type=ListingText,
    instructions=(PROMPTS_DIR / "listing.md").read_text(),
    # DeepSeek thinks by default, and thinking rejects the forced tool_choice that structured
    # output uses (400 "Thinking mode does not support this tool_choice"); also cheaper.
    model_settings={"extra_body": {"thinking": {"type": "disabled"}}},
    defer_model_check=True,
)


def describe(photos: list[bytes]) -> ListingText:
    """Suggest a title and description from listing photos (JPEGs, main photo first)."""
    images = [BinaryContent(data, media_type="image/jpeg") for data in photos[:MAX_PHOTOS]]
    prompt = "Write the listing for the item in these photos. The first photo is the main one."
    return agent.run_sync([prompt, *images]).output
