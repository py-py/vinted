"""Load Vinted auth cookies from a local JSON file.

Shared by the authenticated ``account`` scripts (favourites, catalog API, ...).
"""

from __future__ import annotations

import json
from pathlib import Path

# Repo root: vinted/vinted/account/cookies.py -> parent x3
COOKIES_PATH = Path(__file__).parent.parent.parent / "cookies.json"

# Minimum cookies required for authenticated API access
REQUIRED_COOKIE_KEYS = [
    "access_token_web",
    "datadome",
    "cf_clearance",
]


def load_cookies(path: Path = COOKIES_PATH) -> dict[str, str]:
    if not path.exists():
        raise FileNotFoundError(
            f"Cookies file not found: {path}\nCreate it with keys: {REQUIRED_COOKIE_KEYS}"
        )
    cookies = json.loads(path.read_text())
    missing = [k for k in REQUIRED_COOKIE_KEYS if k not in cookies]
    if missing:
        raise ValueError(f"Missing required cookies: {missing}")
    return cookies
