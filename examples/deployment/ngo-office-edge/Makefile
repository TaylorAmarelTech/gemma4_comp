# NGO-office-edge convenience targets.
#
# Run from this directory: examples/deployment/ngo-office-edge/

.PHONY: setup up down logs doctor backup restore add-caseworker pull update

setup:  ## First-time setup (detects RAM, picks model, brings up stack)
	bash scripts/setup.sh

up:  ## Start the stack
	docker compose up -d

down:  ## Stop the stack
	docker compose down

logs:  ## Tail logs
	docker compose logs -f --tail=100

doctor:  ## Diagnose health
	bash ../../../scripts/duecare-doctor.sh

backup:  ## Snapshot to backups/
	bash ../../../scripts/backup.sh --skip-models --dest backups

restore:  ## Restore from backup. Usage: make restore ARCHIVE=backups/duecare-DATE.tgz
	@[ -z "$(ARCHIVE)" ] && echo "Usage: make restore ARCHIVE=backups/duecare-DATE.tgz" && exit 1 || true
	bash ../../../scripts/restore.sh "$(ARCHIVE)"

add-caseworker:  ## Add a tenant. Usage: make add-caseworker ID=alice@your-org.org
	@[ -z "$(ID)" ] && echo "Usage: make add-caseworker ID=alice@your-org.org [BUDGET=N]" && exit 1 || true
	bash scripts/add-caseworker.sh "$(ID)" $(if $(BUDGET),--budget $(BUDGET),)

pull:  ## Pull a different / newer Gemma model. Usage: make pull MODEL=gemma4:e4b
	@[ -z "$(MODEL)" ] && echo "Usage: make pull MODEL=gemma4:e4b" && exit 1 || true
	docker compose exec ollama ollama pull "$(MODEL)"

update:  ## Pull repo updates + rebuild
	cd ../../.. && git pull
	docker compose pull
	docker compose up -d --build

help:
	@grep -E '^[a-zA-Z_-]+:.*?## ' $(MAKEFILE_LIST) \
		| awk 'BEGIN {FS = ":.*?## "}; {printf "  \033[36m%-20s\033[0m %s\n", $$1, $$2}'

.DEFAULT_GOAL := help
