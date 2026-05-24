.PHONY: build shell run notify subscribe \
	gcp-enable gcp-secret gcp-sa gcp-deploy gcp-execute gcp-schedule gcp-setup gcp-logs

# --- Config (override on the CLI, e.g. make gcp-deploy GCP_REGION=europe-west1) ---
GCP_PROJECT  ?= vinted-492007
GCP_REGION   ?= europe-north1
JOB          ?= vinted-notifier
SA           ?= vinted-notifier@$(GCP_PROJECT).iam.gserviceaccount.com
SECRET       ?= TELEGRAM_BOT_TOKEN
FIRESTORE_DB ?= vinted-dev

# --- Local dev (docker compose) ---
build:
	docker compose build

shell:
	docker compose run --rm vinted bash

run:
	docker compose run --rm vinted $(CMD)

# --- Notifier (local) ---
notify:
	uv run python -m vinted.notifier

# make subscribe URL="https://www.vinted.pl/catalog?catalog[]=2652&order=newest_first"
subscribe:
	uv run python -m vinted.notifier.subscribe "$(URL)"

# --- Cloud Run Job deploy ---
# One-time provisioning: make gcp-setup
# Redeploy after code changes: make gcp-deploy

gcp-enable:
	gcloud services enable run.googleapis.com cloudbuild.googleapis.com \
		artifactregistry.googleapis.com secretmanager.googleapis.com \
		cloudscheduler.googleapis.com --project=$(GCP_PROJECT)

gcp-secret:
	gcloud secrets create $(SECRET) --replication-policy=automatic --project=$(GCP_PROJECT)
	grep '^$(SECRET)=' .env | cut -d= -f2- | tr -d '\n' \
		| gcloud secrets versions add $(SECRET) --data-file=- --project=$(GCP_PROJECT)

gcp-sa:
	gcloud iam service-accounts create vinted-notifier \
		--display-name="Vinted notifier job" --project=$(GCP_PROJECT)
	gcloud projects add-iam-policy-binding $(GCP_PROJECT) \
		--member="serviceAccount:$(SA)" --role="roles/datastore.user"
	gcloud secrets add-iam-policy-binding $(SECRET) \
		--member="serviceAccount:$(SA)" \
		--role="roles/secretmanager.secretAccessor" --project=$(GCP_PROJECT)

gcp-deploy:
	gcloud run jobs deploy $(JOB) --source . \
		--region=$(GCP_REGION) --project=$(GCP_PROJECT) \
		--service-account=$(SA) \
		--command=python --args="^|^-m|vinted.notifier" \
		--set-env-vars=NOTIFIER_STORE=firestore,FIRESTORE_DATABASE=$(FIRESTORE_DB),GOOGLE_CLOUD_PROJECT=$(GCP_PROJECT) \
		--set-secrets=$(SECRET)=$(SECRET):latest

gcp-execute:
	gcloud run jobs execute $(JOB) --region=$(GCP_REGION) --project=$(GCP_PROJECT) --wait

gcp-schedule:
	gcloud run jobs add-iam-policy-binding $(JOB) --region=$(GCP_REGION) \
		--project=$(GCP_PROJECT) \
		--member="serviceAccount:$(SA)" --role="roles/run.invoker"
	gcloud scheduler jobs create http $(JOB)-5min --location=$(GCP_REGION) \
		--schedule="*/5 * * * *" --http-method=POST \
		--uri="https://$(GCP_REGION)-run.googleapis.com/apis/run.googleapis.com/v1/namespaces/$(GCP_PROJECT)/jobs/$(JOB):run" \
		--oauth-service-account-email=$(SA) --project=$(GCP_PROJECT)

gcp-setup: gcp-enable gcp-secret gcp-sa gcp-deploy gcp-schedule

gcp-logs:
	gcloud run jobs executions list --job=$(JOB) --region=$(GCP_REGION) --project=$(GCP_PROJECT)
