DEV_PORT ?= 8000

# `docker compose run` with host gcloud ADC mounted (Firestore etc.).
GCLOUD_RUN = docker compose run --rm \
	--volume $(HOME)/.config/gcloud:/root/.config/gcloud:ro \
	--env GOOGLE_APPLICATION_CREDENTIALS=/root/.config/gcloud/application_default_credentials.json

.DEFAULT_GOAL := help

.PHONY: help build up up-local down admin-web-local shell cmd test admin-web web-dev web-build purchases sales sync scrape-item analyze cookies cookie-header

###############################################################################
#  Help — List available targets
###############################################################################

help: ## Show this help
	@awk 'BEGIN {FS = ":.*## "} /^[a-zA-Z_-]+:.*## / {printf "  \033[36m%-16s\033[0m %s\n", $$1, $$2}' $(MAKEFILE_LIST)

###############################################################################
#  Docker — Image build, shell, ad-hoc commands and tests
###############################################################################

# Backend image (also bakes in the web build) + local web deps for the Vite dev server.
build: ## Build Docker image + install web deps
	docker compose build
	npm --prefix web install

shell: ## Bash shell in the container
	docker compose run --rm vinted bash

cmd: ## Run CMD="..." in the container
	docker compose run --rm vinted $(CMD)

test: ## Run pytest (ARGS="...")
	docker compose run --rm vinted pytest $(ARGS)

###############################################################################
#  Dev Servers — API + Vite together, in Docker or on the host
###############################################################################

# API in Docker on :$(DEV_PORT) + Vite on :5173; Ctrl+C stops both.
up: ## API in Docker + Vite dev server
	@trap 'kill 0' INT TERM EXIT; \
	$(MAKE) --no-print-directory admin-web ADMIN_WEB_FLAGS=-T & \
	$(MAKE) --no-print-directory web-dev & \
	wait

# Same as `up`, but the API runs on the host via uv (no Docker); Ctrl+C stops both.
up-local: ## API on host via uv + Vite dev server
	@trap 'kill 0' INT TERM EXIT; \
	$(MAKE) --no-print-directory admin-web-local & \
	$(MAKE) --no-print-directory web-dev & \
	wait

# Stops whatever `up` / `up-local` left running (e.g. started in another terminal).
down: ## Stop API (Docker + local) and Vite
	docker compose down --remove-orphans
	pkill -f "$(CURDIR)/.venv/bin/fastapi dev" || true
	pkill -f "$(CURDIR)/web/node_modules/.*vite" || true

###############################################################################
#  Backend — FastAPI admin API (Docker / local uv)
###############################################################################

admin-web: ## FastAPI admin API in Docker
	$(GCLOUD_RUN) $(ADMIN_WEB_FLAGS) --publish $(DEV_PORT):8000 vinted fastapi dev --host 0.0.0.0 --port 8000

admin-web-local: ## FastAPI admin API on host via uv
	uv run $(if $(wildcard .env),--env-file .env) fastapi dev --port $(DEV_PORT)

###############################################################################
#  Frontend — Vite dev server and production build
###############################################################################

web-dev: ## Vite dev server
	API_URL=http://localhost:$(DEV_PORT) npm --prefix web run dev

web-build: ## Production web build
	npm --prefix web ci
	npm --prefix web run build

###############################################################################
#  Jobs — Vinted purchases/sales sync
###############################################################################

purchases: ## Sync Vinted purchases
	$(GCLOUD_RUN) vinted python -m vinted.account.purchases

sales: ## Sync Vinted sales
	$(GCLOUD_RUN) vinted python -m vinted.account.sales

# Purchases, then sales (sequential even under `make -j`).
sync: ## Purchases, then sales
	$(MAKE) --no-print-directory purchases
	$(MAKE) --no-print-directory sales

wardrobe: ## Sync a member's wardrobe (MEMBER=<id>)
	$(GCLOUD_RUN) vinted python -m vinted.wardrobe $(MEMBER)

###############################################################################
#  AI — Item scraping and LLM analysis (ITEM=<item id>)
###############################################################################

scrape-item: ## Scrape an item (ITEM=<id>)
	docker compose run --rm vinted python -m vinted.scraper.item $(ITEM)

analyze: ## LLM analysis of an item (ITEM=<id>)
	docker compose run --rm vinted python -m vinted.analyzer $(ITEM)

###############################################################################
#  Cookies — Vinted auth cookies from a copied curl / to a header
###############################################################################

cookies: ## Parse copied curl into cookies.json
	pbpaste | python scripts/parse_curl.py

cookie-header: ## Copy cookie header to clipboard
	python scripts/cookie_header.py | pbcopy
