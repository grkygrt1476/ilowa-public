COMPOSE ?= docker compose
COMPOSE_FILE ?= docker-compose.yml
HOST_UID ?= $(shell id -u)
HOST_GID ?= $(shell id -g)
COMPOSE_ENV = HOST_UID=$(HOST_UID) HOST_GID=$(HOST_GID) API_PORT=$(API_PORT) DB_PORT=$(DB_PORT)
COMPOSE_CMD = $(COMPOSE_ENV) $(COMPOSE) -f $(COMPOSE_FILE)

API_PORT ?= 18000
DB_PORT ?= 15432
WANT_WHERE ?= 0
API_URL ?= http://localhost:$(API_PORT)/health
PROOF_URL ?= http://localhost:$(API_PORT)/api/v1/jobs?per_page=3

.PHONY: up down logs wait migrate seed proof demo scan where

up:
	@if [ "$(WANT_WHERE)" = "1" ]; then $(MAKE) --no-print-directory where; fi
	$(COMPOSE_CMD) up -d --build

down:
	$(COMPOSE_CMD) down -v --remove-orphans

logs:
	$(COMPOSE_CMD) logs -f api

wait:
	API_URL=$(API_URL) scripts/wait_api.sh

migrate:
	$(COMPOSE_CMD) exec -T api sh -lc 'cd /app && if [ -f backend_api/alembic.ini ]; then alembic -c backend_api/alembic.ini upgrade head; else alembic upgrade head; fi'

seed: migrate
	$(COMPOSE_CMD) exec -T api sh -lc 'python /app/ai_modeling/scripts/build_demo_csv_from_json.py'
	$(COMPOSE_CMD) exec -T api sh -lc 'python -m backend_api.scripts.import_ai_jobs --csv ai_modeling/data_samples/demo_jobs_50.json --clear'
	$(COMPOSE_CMD) exec -T api sh -lc 'python -m backend_api.scripts.import_ai_job_embeddings --csv ai_modeling/data_samples/demo_jobs_50_with_embeddings.csv'

proof:
	API_URL=$(API_URL) PROOF_URL=$(PROOF_URL) scripts/proof.sh

demo: up wait seed proof

scan:
	@if [ "$(WANT_WHERE)" = "1" ]; then $(MAKE) --no-print-directory where; fi
	scripts/security_scan.sh

where:
	@printf 'PWD=%s\n' "$$PWD"
	@printf 'GIT_TOP=%s\n' "$$(git rev-parse --show-toplevel 2>/dev/null || echo 'N/A')"
	@printf 'GIT_REMOTE=%s\n' "$$(git config --get remote.origin.url 2>/dev/null || echo 'N/A')"
	@printf 'GIT_BRANCH=%s\n' "$$(git rev-parse --abbrev-ref HEAD 2>/dev/null || echo 'N/A')"
	@printf 'GIT_COMMIT=%s\n' "$$(git rev-parse --short HEAD 2>/dev/null || echo 'N/A')"
	@case "$$PWD" in /tmp/t|/tmp/t/*) echo "WARNING: cleanroom (/tmp/t) - avoid edits/commits here.";; esac
	@printf 'COMPOSE_PROJECT=%s\n' "$$(basename "$$(pwd)")"
