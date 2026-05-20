from __future__ import annotations

import asyncio

from google import genai

from ..core.config import get_settings
from ..core.logging import get_logger
from ..domain.analysis import BaseAnalysis
from ..domain.product import VintedProduct
from .base import Image

logger = get_logger(__name__)


class GeminiAnalyzer:
    """Analyze products with Google Gemini (structured JSON output)."""

    def __init__(self, model: str | None = None, api_key: str | None = None) -> None:
        settings = get_settings()
        self._model = model or settings.gemini_model
        self._client = genai.Client(api_key=api_key or settings.gemini_api_key)

    async def analyze(
        self,
        product: VintedProduct,
        images: list[Image],
        prompt: str,
        schema: type[BaseAnalysis],
    ) -> BaseAnalysis:
        # google-genai's generate_content is synchronous; run it off the event loop.
        return await asyncio.to_thread(self._analyze_sync, product, images, prompt, schema)

    def _analyze_sync(
        self,
        product: VintedProduct,
        images: list[Image],
        prompt: str,
        schema: type[BaseAnalysis],
    ) -> BaseAnalysis:
        logger.info("Analyzing %s with Gemini (%s)", product.url, self._model)

        parts: list = [
            genai.types.Part.from_bytes(data=data, mime_type=media_type)
            for media_type, data in images
        ]
        parts.append(f"Product data:\n{product.model_dump_json(indent=2)}")

        response = self._client.models.generate_content(
            model=self._model,
            contents=parts,
            config=genai.types.GenerateContentConfig(
                system_instruction=prompt,
                temperature=0.1,
                response_mime_type="application/json",
                response_schema=schema,
            ),
        )
        return schema.model_validate_json(response.text)
