.PHONY: build shell run

build:
	docker compose build

shell:
	docker compose run --rm vinted bash

run:
	docker compose run --rm vinted $(CMD)
