from __future__ import annotations

from ..core.config import get_settings
from ..core.logging import get_logger
from ..domain.analysis import BaseAnalysis
from ..domain.product import VintedProduct
from .base import Image

logger = get_logger(__name__)


class ClaudeAnalyzer:
    """Analyze products with Anthropic Claude.

    STUB — not implemented yet. The intended approach mirrors GeminiAnalyzer:

    1. Build a ``messages`` payload with the product JSON as text plus each image
       as a base64 ``image`` content block.
    2. Force structured output by exposing ``schema`` as a single tool
       (``tools=[{... input_schema: schema.model_json_schema() ...}]``) and
       ``tool_choice={"type": "tool", "name": ...}``.
    3. Parse the tool-use block's ``input`` back through ``schema.model_validate``.

    Use ``anthropic.AsyncAnthropic`` so this stays a real coroutine.
    """

    def __init__(self, model: str | None = None, api_key: str | None = None) -> None:
        settings = get_settings()
        self._model = model or settings.claude_model
        self._api_key = api_key or settings.anthropic_api_key

    async def analyze(
        self,
        product: VintedProduct,
        images: list[Image],
        prompt: str,
        schema: type[BaseAnalysis],
    ) -> BaseAnalysis:
        raise NotImplementedError(
            "ClaudeAnalyzer.analyze is not implemented yet — see class docstring for the plan."
        )
