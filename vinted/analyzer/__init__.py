"""AI analysis pipeline: scrape a product, analyze with Gemini, deliver the verdict.

Run with ``python -m vinted.analyzer <product_id> [catalog_id] [--force]``.
"""

from .pipeline import analyze_with_gemini
from .pipeline import load_images
from .pipeline import load_prompt
from .pipeline import main

__all__ = [
    "analyze_with_gemini",
    "load_images",
    "load_prompt",
    "main",
]
