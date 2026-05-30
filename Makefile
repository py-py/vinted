.PHONY: build shell run orders-web web-dev web-build

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

# React frontend (vinted/web-app). web-dev runs Vite with HMR and proxies /api to
# the FastAPI backend on :8000 (run that separately). web-build emits the static
# bundle to vinted/web-app/dist, which the backend serves at /.
web-dev:
	npm --prefix vinted/web-app run dev

web-build:
	npm --prefix vinted/web-app run build
