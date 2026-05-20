# vinted

Scrape Vinted listings, store them in Firestore, analyse each item with an LLM
(Gemini or Claude) to get a buy / negotiate / skip verdict, and notify via Telegram.

## Architecture

```
Scheduler / API trigger
        │
        ▼
  [scrapers] ──► Firestore `items` (status=new, dedup by item id)
                        │  enqueue per new item
                        ▼
  [llm] Gemini│Claude ──► Firestore (status=analyzed, +analysis)
                        │
                        ▼
  recommendation in {buy, negotiate} & rating >= NOTIFY_MIN_RATING
        ├─ yes ──► [notifications] Telegram   (status=notified)
        └─ no  ─────────────────────────────► (status=skipped)
```

### Package layout

```
vinted/
├── main.py            FastAPI app factory (vinted.main:app)
├── cli.py             single-item pipeline runner
├── api/               routes (health, scrape, items) + DI deps
├── core/              config (pydantic-settings), logging, exceptions
├── domain/            pure models: product, analysis, enums
├── scrapers/          Vinted I/O: product, catalog, favourites, wardrobe
├── llm/               provider abstraction: base, gemini, claude, factory, prompts
├── repositories/      Firestore client + items repository
├── services/          pipeline orchestration
├── notifications/     telegram
└── workers/           background-safe task wrappers
```

## Setup

Install dependencies (creates a `.venv` from `pyproject.toml`/`uv.lock`):

```bash
uv sync
```

Install pre-commit hooks:

```bash
uv run pre-commit install
```

Copy `.env.example` to `.env` and fill in credentials. For Firestore, point
`GOOGLE_APPLICATION_CREDENTIALS` at a service-account key (or run with ambient
GCP credentials).

## Run

```bash
# API (Swagger at http://127.0.0.1:8000/docs)
make api

# One item end-to-end: python -m vinted.cli <product_id> [catalog_id] [--force]
make cli CMD="8142652778 2683"
```

### Trigger endpoints

- `POST /scrape/catalog/{catalog_id}?pages=1&force=false` — scrape a catalog, enqueue analysis per item
- `POST /scrape/item/{item_id}?catalog_id=...&force=false` — analyse a single item
- `GET  /items/{item_id}` — fetch the stored record + analysis
- `GET  /health`

## Choosing the LLM provider

Set `LLM_PROVIDER=gemini` (default) or `LLM_PROVIDER=claude` in `.env`.
The Claude analyzer is currently a stub — see `vinted/llm/claude.py`.
