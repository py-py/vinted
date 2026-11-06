from __future__ import annotations

import pytest
from pydantic_ai import BinaryContent
from pydantic_ai import capture_run_messages
from pydantic_ai.messages import UserPromptPart
from pydantic_ai.models.test import TestModel

from ..describe import MAX_PHOTOS
from ..describe import ListingText
from ..describe import agent
from ..describe import describe
from ..describe import resolve

OUTPUT = {"title": "Sandały Nike Sunray Protect, r. 27", "description": "Czarne, lekko noszone."}


def _sent_images() -> list[BinaryContent]:
    with capture_run_messages() as messages:
        describe([b"jpeg-%d" % i for i in range(MAX_PHOTOS + 3)])
    parts = [p for m in messages for p in getattr(m, "parts", []) if isinstance(p, UserPromptPart)]
    return [c for c in parts[0].content if isinstance(c, BinaryContent)]


def test_describe_returns_structured_text() -> None:
    with agent.override(model=TestModel(custom_output_args=OUTPUT)):
        assert describe([b"jpeg"]) == ListingText(**OUTPUT)


def test_describe_sends_main_photo_first_and_caps_count() -> None:
    with agent.override(model=TestModel(custom_output_args=OUTPUT)):
        images = _sent_images()
    assert len(images) == MAX_PHOTOS
    assert images[0].data == b"jpeg-0"
    assert {i.media_type for i in images} == {"image/jpeg"}


def test_describe_adds_notes_to_prompt() -> None:
    with agent.override(model=TestModel(custom_output_args=OUTPUT)):
        with capture_run_messages() as messages:
            describe([b"jpeg"], notes="  new, never worn ")
    parts = [p for m in messages for p in getattr(m, "parts", []) if isinstance(p, UserPromptPart)]
    assert "new, never worn" in parts[0].content[0]


def test_resolve_reads_provider_model_and_quirks(monkeypatch):
    monkeypatch.setenv("GEMINI_MODEL", "gemini-2.5-flash")
    monkeypatch.setenv("DEEPSEEK_MODEL", "deepseek-pro")
    assert resolve("google") == ("google:gemini-2.5-flash", {"temperature": 0.2})
    assert resolve("deepseek") == (
        "deepseek:deepseek-pro",
        {"temperature": 0.2, "extra_body": {"thinking": {"type": "disabled"}}},
    )


def test_resolve_rejects_unknown_provider():
    with pytest.raises(ValueError, match="LISTING_PROVIDER"):
        resolve("openai")
