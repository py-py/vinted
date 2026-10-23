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
make build   # backend Docker image (with the web build baked in) + web npm deps
make run     # API on :8000 + Vite on http://localhost:5173; Ctrl+C stops both
```

`make run DEV_PORT=8002` if port 8000 is taken. Run one side only with `make admin-web` /
`make web-dev`; run any command in the container with `make cmd CMD="..."`.
