"""Jinja environment shared by the admin routes."""

from __future__ import annotations

from typing import Any

from jinja2 import Environment
from jinja2 import FileSystemLoader
from jinja2 import select_autoescape

from .constants import TEMPLATES_DIR

_env = Environment(
    loader=FileSystemLoader(TEMPLATES_DIR),
    autoescape=select_autoescape(["html"]),
)


def render(template: str, **context: Any) -> str:
    return _env.get_template(template).render(**context)
