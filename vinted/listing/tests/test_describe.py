from __future__ import annotations

from pydantic_ai import BinaryContent
from pydantic_ai import capture_run_messages
from pydantic_ai.messages import UserPromptPart
from pydantic_ai.models.test import TestModel

from ..describe import MAX_PHOTOS
from ..describe import ListingText
from ..describe import agent
from ..describe import describe

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
