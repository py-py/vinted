DEV_PORT ?= 8000

.PHONY: build run shell cmd test admin-web web-dev web-build orders scrape-item analyze cookies cookie-header

# Backend image (also bakes in the web build) + local web deps for the Vite dev server.
build:
	docker compose build
	npm --prefix web install

shell:
	docker compose run --rm vinted bash

# API in Docker on :$(DEV_PORT) + Vite on :5173; Ctrl+C stops both.
run:
	@trap 'kill 0' INT TERM EXIT; \
	$(MAKE) --no-print-directory admin-web ADMIN_WEB_FLAGS=-T & \
	$(MAKE) --no-print-directory web-dev & \
	wait

cmd:
	docker compose run --rm vinted $(CMD)

test:
	docker compose run --rm vinted pytest $(ARGS)

admin-web:
	docker compose run --rm $(ADMIN_WEB_FLAGS) \
		--publish $(DEV_PORT):8000 \
		--volume $(HOME)/.config/gcloud:/root/.config/gcloud:ro \
		--env GOOGLE_APPLICATION_CREDENTIALS=/root/.config/gcloud/application_default_credentials.json \
		vinted fastapi dev --host 0.0.0.0 --port 8000

web-dev:
	API_URL=http://localhost:$(DEV_PORT) npm --prefix web run dev

web-build:
	npm --prefix web ci
	npm --prefix web run build

orders:
	docker compose run --rm \
		--volume $(HOME)/.config/gcloud:/root/.config/gcloud:ro \
		--env GOOGLE_APPLICATION_CREDENTIALS=/root/.config/gcloud/application_default_credentials.json \
		vinted python -m vinted.account.orders

scrape-item:
	docker compose run --rm vinted python -m vinted.scraper.item $(ITEM)

analyze:
	docker compose run --rm vinted python -m vinted.analyzer $(ITEM)

cookies:
	pbpaste | python scripts/parse_curl.py

cookie-header:
	python scripts/cookie_header.py | pbcopy
