# vinted

Scrape Vinted listings, store them in PostgreSQL, analyse each item with an LLM
(Gemini or Claude) to get a buy / negotiate / skip verdict, and notify via Telegram.
Item images are stored in Google Cloud Storage.

## Architecture

```
Scheduler / API trigger
        │
        ▼
  [scrapers] ──► Postgres `items` (status=new, dedup by item id)
       │                │  enqueue per new item
       └─ images ─► GCS ▼
  [llm] Gemini│Claude ──► Postgres (status=analyzed, +analysis)
                        │
                        ▼
  recommendation in {buy, negotiate} & rating >= NOTIFY_MIN_RATING
        ├─ yes ──► [notifications] Telegram   (status=notified)
        └─ no  ─────────────────────────────► (status=skipped)
```

Data lives in PostgreSQL via [SQLModel](https://sqlmodel.tiangolo.com/) with
[Alembic](https://alembic.sqlalchemy.org/) migrations; nested/variable fields
(`properties`, `image_urls`, `seller`, `analysis`) are JSONB columns. A
[SQLAdmin](https://aminalaee.dev/sqladmin/) panel is mounted at `/admin`.

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
├── db/                SQLModel models, async engine/session, alembic migrations
├── storage/           Google Cloud Storage client for product images
├── repositories/      items repository (SQLModel-backed)
├── admin/             SQLAdmin panel (mounted at /admin)
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

Copy `.env.example` to `.env` and fill in credentials. Set `DATABASE_URL` and
`GCS_BUCKET`; point `GOOGLE_APPLICATION_CREDENTIALS` at a service-account key with
access to the bucket (or run with ambient GCP credentials).

### Database

Start Postgres and apply migrations:

```bash
make db        # docker compose up -d db  (host port 5433)
make migrate   # alembic upgrade head
```

After changing a SQLModel model, generate a migration:

```bash
make migration M="describe change"   # alembic revision --autogenerate
```

## Run

```bash
# API (Swagger at http://127.0.0.1:8000/docs, admin at http://127.0.0.1:8000/admin)
make api

# One item end-to-end: python -m vinted.cli <product_id> [catalog_id] [--force]
make cli CMD="8142652778 2683"
```

### Trigger endpoints

- `POST /scrape/catalog/{catalog_id}?pages=1&force=false` — scrape a catalog, enqueue analysis per item
- `POST /scrape/item/{item_id}?catalog_id=...&force=false` — analyse a single item
- `GET  /items/{item_id}` — fetch the stored record + analysis
- `GET  /health`
- `GET  /admin` — SQLAdmin panel to browse / filter / export items

## Choosing the LLM provider

Set `LLM_PROVIDER=gemini` (default) or `LLM_PROVIDER=claude` in `.env`.
The Claude analyzer is currently a stub — see `vinted/llm/claude.py`.
