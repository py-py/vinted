#!/usr/bin/env python3
"""Build a `Cookie:` header value from cookies.json.

Full header -> stdout, masked preview + token expiry -> stderr.

Usage:
    python scripts/cookie_header.py | pbcopy     # copy to clipboard (macOS)
    curl -b "$(python scripts/cookie_header.py)" https://www.vinted.pl/api/v2/...
"""

from __future__ import annotations

import json
import sys

from parse_curl import COOKIES_PATH
from parse_curl import REQUIRED
from parse_curl import _humanize_delta
from parse_curl import access_token_expiry


def build_header(cookies: dict[str, str]) -> str:
    """Join cookies into a header value: "a=1; b=2;"."""
    return "; ".join(f"{k}={v}" for k, v in cookies.items()) + ";"


def _mask(value: str) -> str:
    return value[:6] + "***"


def main() -> None:
    if not COOKIES_PATH.exists():
        sys.exit(f"{COOKIES_PATH} not found — run `make cookies` first")
    cookies: dict[str, str] = json.loads(COOKIES_PATH.read_text(encoding="utf-8"))

    missing = [k for k in REQUIRED if k not in cookies]
    if missing:
        sys.exit(f"MISSING required keys in {COOKIES_PATH.name}: {missing}")

    print(build_header(cookies))

    print(build_header({k: _mask(v) for k, v in cookies.items()}), file=sys.stderr)
    exp = access_token_expiry(cookies["access_token_web"])
    if exp:
        print(
            f"access_token_web expires {exp:%Y-%m-%d %H:%M:%S} UTC ({_humanize_delta(exp)})",
            file=sys.stderr,
        )


if __name__ == "__main__":
    main()
