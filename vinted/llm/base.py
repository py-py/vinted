from __future__ import annotations

from typing import Protocol

from ..domain.analysis import BaseAnalysis
from ..domain.product import VintedProduct

# (media_type, raw_bytes), e.g. ("image/jpeg", b"...")
Image = tuple[str, bytes]


class ProductAnalyzer(Protocol):
    """Common interface for an LLM-backed product analyzer.

    Implementations turn a scraped product (+ its images + a system prompt)
    into a structured ``BaseAnalysis`` (or a catalog-specific subclass).
    """

    async def analyze(
        self,
        product: VintedProduct,
        images: list[Image],
        prompt: str,
        schema: type[BaseAnalysis],
    ) -> BaseAnalysis: ...
