from __future__ import annotations

from ..core.config import get_settings
from .base import ProductAnalyzer
from .claude import ClaudeAnalyzer
from .gemini import GeminiAnalyzer


def get_analyzer(provider: str | None = None) -> ProductAnalyzer:
    """Return the configured LLM analyzer.

    Provider defaults to ``settings.llm_provider`` (``gemini`` | ``claude``).
    """
    provider = provider or get_settings().llm_provider

    if provider == "gemini":
        return GeminiAnalyzer()
    if provider == "claude":
        return ClaudeAnalyzer()

    raise ValueError(f"Unknown LLM provider: {provider!r}")
