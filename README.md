# vinted

## Setup

Install dependencies (creates a `.venv` from `pyproject.toml`/`uv.lock`):

```bash
uv sync
```

Install pre-commit hooks:

```bash
uv run pre-commit install
```

## Admin

FastAPI serves a JSON API under `/api` and the built React app from `web/` (see
`web/README.md`), both behind HTTP Basic auth (`ADMIN_USERNAME` / `ADMIN_PASSWORD`).

```bash
make admin-web   # API (+ the web build baked into the image) on :$(DEV_PORT), default 8000
make web-dev     # Vite dev server on :5173, proxying /api to the API above
```
