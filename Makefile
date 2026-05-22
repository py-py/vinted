.PHONY: build shell run api cli migrate migration db

build:
	docker compose build

shell:
	docker compose run --rm vinted bash

run:
	docker compose run --rm vinted $(CMD)

# Start the Postgres service in the background
db:
	docker compose up -d db

# Run the FastAPI app locally with autoreload
api:
	uv run uvicorn vinted.main:app --reload

# Run the pipeline for a single item, e.g. make cli CMD="8142652778 2683"
cli:
	uv run python -m vinted.cli $(CMD)

# Apply all pending migrations
migrate:
	uv run alembic upgrade head

# Autogenerate a migration from model changes, e.g. make migration M="add items"
migration:
	uv run alembic revision --autogenerate -m "$(M)"
