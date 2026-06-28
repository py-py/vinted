DEV_PORT ?= 8000

.PHONY: build shell run admin-web orders cookies

build:
	docker compose build

shell:
	docker compose run --rm vinted bash

run:
	docker compose run --rm vinted $(CMD)

admin-web:
	docker compose run --rm \
		--publish $(DEV_PORT):8000 \
		--volume $(HOME)/.config/gcloud:/root/.config/gcloud:ro \
		--env GOOGLE_APPLICATION_CREDENTIALS=/root/.config/gcloud/application_default_credentials.json \
		vinted uvicorn vinted.admin.web:app --reload --host 0.0.0.0 --port 8000

orders:
	docker compose run --rm \
		--volume $(HOME)/.config/gcloud:/root/.config/gcloud:ro \
		--env GOOGLE_APPLICATION_CREDENTIALS=/root/.config/gcloud/application_default_credentials.json \
		vinted python -m vinted.account.orders

cookies:
	pbpaste | python scripts/parse_curl.py
