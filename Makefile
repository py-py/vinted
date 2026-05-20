.PHONY: build shell run api cli

build:
	docker compose build

shell:
	docker compose run --rm vinted bash

run:
	docker compose run --rm vinted $(CMD)

# Run the FastAPI app locally with autoreload
api:
	uv run uvicorn vinted.main:app --reload

# Run the pipeline for a single item, e.g. make cli CMD="8142652778 2683"
cli:
	uv run python -m vinted.cli $(CMD)
