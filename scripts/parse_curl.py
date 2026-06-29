#!/usr/bin/env python3
r"""Refresh cookies.json from a browser "Copy as cURL" command.

Single source of truth for the cookie-refresh flow: the `vinted-refresh-cookies`
skill just runs this script. It extracts the cookie string from a curl command,
parses the keys the Vinted client needs, decodes the access token's expiry, and
merges the result into cookies.json.

Uses `shlex` (stdlib) — no regex, no extra deps. It tokenizes the curl text the
way a POSIX shell would, so quoted strings stay whole and `\`-line-continuations
become harmless standalone tokens.

Secrets are never printed in full — only key names and the JWT `exp` claim.

Usage:
    python scripts/parse_curl.py path/to/curl.txt     # read from a file
    pbpaste | python scripts/parse_curl.py            # read from stdin (macOS)
    python scripts/parse_curl.py                      # no arg -> reads stdin
"""

from __future__ import annotations

import base64
import json
import shlex
import sys
from datetime import UTC
from datetime import datetime
from pathlib import Path

# cookies.json lives at the repo root (this script is in scripts/).
COOKIES_PATH = Path(__file__).resolve().parent.parent / "cookies.json"

# The 3 keys the Vinted client actually needs (vinted/favourites.py, vinted/orders/).
REQUIRED = ["access_token_web", "datadome", "cf_clearance"]


def extract_cookie_string(curl: str) -> str:
    """Return the raw cookie string from a curl command's -b/--cookie or Cookie: header."""
    tokens = shlex.split(curl)
    for i, tok in enumerate(tokens):
        # -b <value>  or  --cookie <value>  -> value is the next token
        if tok in ("-b", "--cookie") and i + 1 < len(tokens):
            return tokens[i + 1]
        # -H 'cookie: <value>'  -> strip the "cookie:" prefix
        if tok == "-H" and i + 1 < len(tokens) and tokens[i + 1].lower().startswith("cookie:"):
            return tokens[i + 1].split(":", 1)[1].strip()
    raise ValueError("no -b / --cookie / Cookie: header found in curl text")


def parse_cookies(cookie_str: str) -> dict[str, str]:
    """Split a cookie string ("a=1; b=2") into a dict. Values may contain '='."""
    jar: dict[str, str] = {}
    for pair in cookie_str.split("; "):
        if "=" in pair:
            key, value = pair.split("=", 1)  # split on FIRST '=' only
            jar[key.strip()] = value.strip()
    return jar


def access_token_expiry(token: str) -> datetime | None:
    """Decode the JWT middle segment and return its `exp` as an aware UTC datetime."""
    try:
        _, payload, _ = token.split(".")
        padded = payload + "=" * (-len(payload) % 4)  # fix base64url padding
        claims = json.loads(base64.urlsafe_b64decode(padded))
        return datetime.fromtimestamp(claims["exp"], tz=UTC)
    except (ValueError, KeyError, json.JSONDecodeError):
        return None


def _humanize_delta(exp: datetime) -> str:
    """Return a short "in 1h 58m" / "EXPIRED 5m ago" string relative to now."""
    seconds = int((exp - datetime.now(tz=UTC)).total_seconds())
    if seconds >= 0:
        hours, minutes = divmod(seconds // 60, 60)
        return "in " + (f"{hours}h {minutes}m" if hours else f"{minutes}m")
    hours, minutes = divmod(-seconds // 60, 60)
    return "EXPIRED " + (f"{hours}h {minutes}m" if hours else f"{minutes}m") + " ago"


def update_cookies_file(values: dict[str, str]) -> None:
    """Merge the required cookie values into cookies.json, preserving any other keys."""
    data: dict[str, str] = {}
    if COOKIES_PATH.exists():
        data = json.loads(COOKIES_PATH.read_text(encoding="utf-8"))
    data.update(values)
    COOKIES_PATH.write_text(json.dumps(data, indent=2) + "\n", encoding="utf-8")


def main() -> None:
    if len(sys.argv) > 1:
        curl = Path(sys.argv[1]).read_text(encoding="utf-8")
    else:
        curl = sys.stdin.read()

    if not curl.strip():
        sys.exit("no curl text provided (pass a file path or pipe it via stdin)")

    cookies = parse_cookies(extract_cookie_string(curl))
    print(f"parsed {len(cookies)} cookies")  # names only below — never echo values

    missing = [k for k in REQUIRED if k not in cookies]
    if missing:
        sys.exit(f"MISSING required keys: {missing} — {COOKIES_PATH.name} left unchanged")

    print("required keys present:")
    for k in REQUIRED:
        print(f"  ✓ {k}")

    exp = access_token_expiry(cookies["access_token_web"])
    if exp:
        print(f"access_token_web expires {exp:%Y-%m-%d %H:%M:%S} UTC ({_humanize_delta(exp)})")

    update_cookies_file({k: cookies[k] for k in REQUIRED})
    print(f"updated {COOKIES_PATH}")


if __name__ == "__main__":
    main()
