---
name: vinted-refresh-cookies
description: Extract Vinted auth cookies and write them to cookies.json. Use when the user wants to refresh expired Vinted cookies, mentions "обнови куки", "refresh cookies", "куки протухли", or after a 401 from the Vinted API. Accepts either a full curl command pasted inline as the argument, or a path to a file containing one.
---

# vinted-refresh-cookies

Refresh `cookies.json` (which `vinted/favourites.py` and `vinted/orders/` read for API auth) from a CURL command that the user copied out of the browser DevTools "Copy as cURL".

## Input

The argument is **either**:
- the **full curl text pasted inline** (common — starts with `curl '…'` and contains `-b '…'`), or
- a **path** to a file containing the curl command.

Detect which: if the argument starts with `curl ` (or contains `-b '` / `--cookie '` / `cookie:` header inline), treat it as inline curl text. Otherwise treat it as a file path and Read it. If neither works and no argument was given, ask the user.

Do **not** stage the input through an intermediate file in `/tmp` or the repo — the user has rejected that approach. Either parse the inline string directly in the Python snippet (preferred), or Read the file the user pointed at.

## Procedure

1. **Obtain the curl text** per "Input" above (inline string or Read a file).
2. **Extract the cookie string.** Tokenize the curl text with `shlex.split()` (stdlib — handles the single/double quotes and `\`-line-continuations that Chrome's "Copy as cURL" emits for cookie strings; it doesn't *decode* `$'...'` ANSI-C escapes but tolerates them in unrelated headers, and real Vinted cookies are RFC 6265 cookie-octets so they always come back in plain `'...'` form). Walk the tokens and take the first match:
   - `-b <value>` or `--cookie <value>` → value is the next token
   - `-H <value>` where `<value>` starts with `cookie:` (case-insensitive) → strip the `cookie:` prefix and trim
   If none matches, stop and report that no `-b` / `--cookie` / `Cookie:` header was found. Do **not** fall back to regex — if shlex fails to parse, the curl text is malformed and the user should re-copy it.
3. **Parse** the cookie string into a dict by splitting on `; ` (semicolon + space), then on the first `=` of each pair. Trim whitespace. Cookie *values* may contain `=`, `_`, `-`, `.`, `~`, `+`, `/`; keep them verbatim (do **not** URL-decode).
4. **Pick the 3 required keys** that `vinted/favourites.py` expects:
   - `access_token_web`
   - `datadome`
   - `cf_clearance`
   If any are missing, stop and report which ones — partial cookies will break auth. Note: `refresh_token_web` is **not** needed right now — the auto-refresh flow has been removed from `favourites.py` / `orders/api.py`, so the operator is expected to re-run this skill manually once the access token (~2h lifetime) expires. If `refresh_token_web` happens to be in the curl, you may still write it (harmless), but don't fail when it's absent.
5. **Write** the dict as pretty-printed JSON to `cookies.json` in the project root (overwrite). Read the existing file first if it exists, only to confirm the path; do not merge — a fresh curl is the source of truth.
6. **Decode the access_token_web JWT** to report its `exp` claim:
   - Split on `.`, take the middle segment, base64-decode (`base64.urlsafe_b64decode` with `=` padding fixed), `json.loads`.
   - Convert `exp` (unix seconds) to a human-readable UTC time and show how long it lasts (e.g. `expires in 1h 58m`).
7. **Print a one-line summary**: which keys were written and when access expires.

## Implementation note

Use a single inline Python snippet via Bash (parsing + JWT decode in one place). Use the project venv: `.venv/bin/python`. Pass the cookie/curl string to Python via a heredoc (`<<'PYEOF' … PYEOF`) — this keeps secrets out of `argv` / shell history and avoids any temp file on disk. Do **not** add a new file to `vinted/` or `/tmp/` — this skill is for the operator, not the runtime.

## Safety

- `cookies.json` is already in `.gitignore` — do not change that.
- Do not echo the cookie values in full to chat (they're long-lived secrets). Print only key names and JWT `exp` info.
- Never commit the curl file or cookies.json. If the user passed a path inside the repo, suggest adding it to `.gitignore` if it isn't already.
- Never write the curl text to a temp file (e.g. `/tmp/…`) as a staging step — parse it inline in the Python heredoc instead.