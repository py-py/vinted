DEV_PORT ?= 8000

.PHONY: build run run-local admin-web-local shell cmd test admin-web web-dev web-build orders sales sync scrape-item analyze cookies cookie-header

###############################################################################
#  Docker — Image build, shell, ad-hoc commands and tests
###############################################################################

# Backend image (also bakes in the web build) + local web deps for the Vite dev server.
build:
	docker compose build
	npm --prefix web install

shell:
	docker compose run --rm vinted bash

cmd:
	docker compose run --rm vinted $(CMD)

test:
	docker compose run --rm vinted pytest $(ARGS)

###############################################################################
#  Dev Servers — API + Vite together, in Docker or on the host
###############################################################################

# API in Docker on :$(DEV_PORT) + Vite on :5173; Ctrl+C stops both.
run:
	@trap 'kill 0' INT TERM EXIT; \
	$(MAKE) --no-print-directory admin-web ADMIN_WEB_FLAGS=-T & \
	$(MAKE) --no-print-directory web-dev & \
	wait

# Same as `run`, but the API runs on the host via uv (no Docker); Ctrl+C stops both.
run-local:
	@trap 'kill 0' INT TERM EXIT; \
	$(MAKE) --no-print-directory admin-web-local & \
	$(MAKE) --no-print-directory web-dev & \
	wait

###############################################################################
#  Backend — FastAPI admin API (Docker / local uv)
###############################################################################

admin-web:
	docker compose run --rm $(ADMIN_WEB_FLAGS) \
		--publish $(DEV_PORT):8000 \
		--volume $(HOME)/.config/gcloud:/root/.config/gcloud:ro \
		--env GOOGLE_APPLICATION_CREDENTIALS=/root/.config/gcloud/application_default_credentials.json \
		vinted fastapi dev --host 0.0.0.0 --port 8000

admin-web-local:
	uv run $(if $(wildcard .env),--env-file .env) fastapi dev --port $(DEV_PORT)

###############################################################################
#  Frontend — Vite dev server and production build
###############################################################################

web-dev:
	API_URL=http://localhost:$(DEV_PORT) npm --prefix web run dev

web-build:
	npm --prefix web ci
	npm --prefix web run build

###############################################################################
#  Jobs — Vinted orders/sales sync
###############################################################################

orders:
	docker compose run --rm \
		--volume $(HOME)/.config/gcloud:/root/.config/gcloud:ro \
		--env GOOGLE_APPLICATION_CREDENTIALS=/root/.config/gcloud/application_default_credentials.json \
		vinted python -m vinted.account.orders

sales:
	docker compose run --rm \
		--volume $(HOME)/.config/gcloud:/root/.config/gcloud:ro \
		--env GOOGLE_APPLICATION_CREDENTIALS=/root/.config/gcloud/application_default_credentials.json \
		vinted python -m vinted.account.sales

# Orders, then sales (sequential even under `make -j`).
sync:
	$(MAKE) --no-print-directory orders
	$(MAKE) --no-print-directory sales

###############################################################################
#  AI — Item scraping and LLM analysis (ITEM=<item id>)
###############################################################################

scrape-item:
	docker compose run --rm vinted python -m vinted.scraper.item $(ITEM)

analyze:
	docker compose run --rm vinted python -m vinted.analyzer $(ITEM)

###############################################################################
#  Cookies — Vinted auth cookies from a copied curl / to a header
###############################################################################

cookies:
	pbpaste | python scripts/parse_curl.py

cookie-header:
	python scripts/cookie_header.py | pbcopy
