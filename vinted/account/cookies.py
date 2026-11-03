"""Load Vinted auth cookies from a local JSON file.

Shared by the authenticated ``account`` scripts (favourites, catalog API, ...).
"""

from __future__ import annotations

import base64
import json
import sys
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


def token_claims(token: str) -> dict:
    """Decode the JWT payload (no signature check — local inspection only)."""
    _, payload, _ = token.split(".")
    padded = payload + "=" * (-len(payload) % 4)  # fix base64url padding
    return json.loads(base64.urlsafe_b64decode(padded))


def user_id_from_token(cookies: dict[str, str] | None = None) -> str:
    """Return the Vinted user_id: the `sub` claim of `access_token_web`.

    Works even when the token has expired — the id never changes.
    """
    if cookies is None:
        cookies = load_cookies()
    return token_claims(cookies["access_token_web"])["sub"]


if __name__ == "__main__":
    try:
        print(user_id_from_token())
    except (FileNotFoundError, ValueError, KeyError) as exc:
        sys.exit(f"Cannot read user_id: {exc}")
