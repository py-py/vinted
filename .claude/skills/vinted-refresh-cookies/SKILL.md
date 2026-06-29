---
name: vinted-refresh-cookies
description: Extract Vinted auth cookies and write them to cookies.json. Use when the user wants to refresh expired Vinted cookies, mentions "обнови куки", "refresh cookies", "куки протухли", or after a 401 from the Vinted API. Accepts either a full curl command pasted inline as the argument, or a path to a file containing one.
---

# vinted-refresh-cookies

Refresh `cookies.json` (which `vinted/favourites.py` and `vinted/orders/` read for API auth) from a CURL command that the user copied out of the browser DevTools "Copy as cURL".

The parsing/validation/JWT-decode logic lives in **one place** — `scripts/parse_curl.py`. This skill just feeds the curl text to that script; do **not** re-implement cookie parsing inline.

## Input

The argument is **either**:
- the **full curl text pasted inline** (common — starts with `curl '…'` and contains `-b '…'`), or
- a **path** to a file containing the curl command.

Detect which: if the argument starts with `curl ` (or contains `-b '` / `--cookie '` / `cookie:` header inline), treat it as inline curl text. Otherwise treat it as a file path. If neither works and no argument was given, ask the user.

## Procedure

Run the script with the project venv: `.venv/bin/python scripts/parse_curl.py`. It extracts the cookie string (via `shlex`), keeps the 3 keys the client needs (`access_token_web`, `datadome`, `cf_clearance`), decodes the access token's `exp`, and merges the result into `cookies.json`.

- **Inline curl text** → pipe it to the script's stdin via a heredoc, so secrets stay out of `argv` / shell history and no temp file ever touches disk:
  ```bash
  .venv/bin/python scripts/parse_curl.py <<'CURL'
  curl 'https://www.vinted.fr/api/v2/…' -b 'access_token_web=…; datadome=…; cf_clearance=…' …
  CURL
  ```
- **A file path the user gave** → pass it as the argument: `.venv/bin/python scripts/parse_curl.py path/to/curl.txt`.

The script exits non-zero with a clear message if no `-b`/`--cookie`/`Cookie:` header is found or if any required key is missing — relay that to the user and ask them to re-copy the curl. Do **not** fall back to regex or hand-parsing.

Then report the script's summary to the user: which keys were written and when `access_token_web` expires.

## Safety

- `cookies.json` is already in `.gitignore` — do not change that.
- The script prints only key names and the JWT `exp` — never the secret values. Don't echo the cookie values in full to chat yourself either.
- Never commit the curl text or cookies.json. If the user passed a path inside the repo, suggest adding it to `.gitignore` if it isn't already.
- Never stage the curl text through a temp file (e.g. `/tmp/…`) — pipe inline curl via the heredoc above, or pass the user's own file path directly.