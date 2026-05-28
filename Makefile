.PHONY: build shell run orders-web

build:
	docker compose build

shell:
	docker compose run --rm vinted bash

run:
	docker compose run --rm vinted $(CMD)

orders-web:
	docker compose run --rm \
		--publish 8000:8000 \
		--volume $(HOME)/.config/gcloud:/root/.config/gcloud:ro \
		--env GOOGLE_APPLICATION_CREDENTIALS=/root/.config/gcloud/application_default_credentials.json \
		vinted uvicorn vinted.orders.web:app --reload --host 0.0.0.0 --port 8000
