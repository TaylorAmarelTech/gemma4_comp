.PHONY: install install-uv install-pip dev test test-stress adversarial cleanroom \
        build lint serve serve-chat serve-classifier verify reproduce \
        demo demo-with-monitoring demo-with-auth doctor backup backup-light \
        docker docker-build docker-up docker-down docker-logs docker-up-auth \
        docker-dev docker-dev-up docker-dev-down docker-dev-shell docker-dev-test \
        observability observability-up observability-down observability-logs \
        helm helm-install helm-uninstall helm-lint helm-template \
        notebooks kaggle-push kaggle-status kaggle-publish-all kaggle-dry-run kaggle-auth \
        clean help

PACKAGES := duecare-llm-core duecare-llm-models duecare-llm-domains duecare-llm-tasks \
            duecare-llm-agents duecare-llm-workflows duecare-llm-publishing duecare-llm

# Default target: show help
.DEFAULT_GOAL := help

help:  ## Show this help
	@grep -E '^[a-zA-Z_-]+:.*?## ' $(MAKEFILE_LIST) \
		| awk 'BEGIN {FS = ":.*?## "}; {printf "  \033[36m%-22s\033[0m %s\n", $$1, $$2}'

# ── Install ──────────────────────────────────────────────────────
install: install-uv  ## Install all 17 packages (preferred: uv); falls back to pip
install-uv:
	@command -v uv >/dev/null 2>&1 \
		&& uv sync --all-packages \
		|| $(MAKE) install-pip

install-pip:  ## Install via pip (no uv required)
	pip install --upgrade pip wheel
	@for pkg in $(PACKAGES); do \
		echo "Installing $$pkg ..."; \
		pip install -e packages/$$pkg; \
	done
	@echo "Installing duecare-llm-chat ..."
	pip install -e packages/duecare-llm-chat

dev: install verify  ## Install + verify in one shot (for new contributors)

# ── Testing ──────────────────────────────────────────────────────
test:
	python -m pytest packages tests -q

test-stress:
	@for i in 1 2 3; do echo "=== run $$i ==="; python -m pytest packages tests -q --no-header 2>&1 | tail -3; done

adversarial:
	python scripts/adversarial_validation.py --all --stress 3

cleanroom:
	python scripts/cleanroom_install.py

# ── Build ────────────────────────────────────────────────────────
build:
	@for pkg in $(PACKAGES); do \
		echo "Building $$pkg ..."; \
		python -m build --wheel packages/$$pkg; \
	done

# ── Lint ─────────────────────────────────────────────────────────
lint:
	ruff check packages/ tests/ scripts/
	mypy packages/

# ── Kaggle ───────────────────────────────────────────────────────
kaggle-auth:
	python scripts/publish_kaggle.py auth-check

kaggle-push:
	python scripts/publish_kaggle.py push-notebooks

kaggle-status:
	python scripts/publish_kaggle.py status-notebooks

kaggle-publish-all:
	python scripts/publish_kaggle.py publish-all

kaggle-dry-run:
	python scripts/publish_kaggle.py --dry-run publish-all

# ── Data Pipeline ────────────────────────────────────────────────
extract-prompts:
	python scripts/extract_benchmark_prompts.py

prepare-training:
	python scripts/prepare_training_data.py --include-negative

finetune:
	python scripts/finetune_unsloth.py

# ── Local Evaluation ────────────────────────────────────────────
eval-local:
	python scripts/run_local_gemma.py --max-prompts 50

eval-graded:
	python scripts/run_local_gemma.py --graded-only

eval-compare:
	python scripts/compare_models.py --max-prompts 20

# ── Notebooks ────────────────────────────────────────────────────
# Rebuild every notebook from its builder, then run the repo-wide gate.
# Individual builders live at scripts/build_notebook_NNN_*.py; shared
# orchestrators are build_index_notebook.py, build_notebook_005_glossary.py,
# build_section_conclusion_notebooks.py, build_showcase_notebooks.py,
# build_grading_notebooks.py, build_deployment_application_notebooks.py,
# and the legacy build_kaggle_notebooks.py (still authoritative for 610).
notebooks:
	python scripts/build_index_notebook.py
	python scripts/build_notebook_005_glossary.py
	python scripts/build_section_conclusion_notebooks.py
	python scripts/build_showcase_notebooks.py
	python scripts/build_grading_notebooks.py
	python scripts/build_deployment_application_notebooks.py
	python scripts/build_kaggle_notebooks.py
	@for f in scripts/build_notebook_*.py; do \
		[ "$$f" = "scripts/build_notebook_005_glossary.py" ] && continue; \
		python "$$f" > /dev/null || echo "FAILED: $$f"; \
	done
	python scripts/validate_notebooks.py

# Validate only (fast path when you only edited metadata or one notebook):
validate-notebooks:
	python scripts/validate_notebooks.py

# ── Demo Server ──────────────────────────────────────────────────
serve:  ## Run the Duecare demo server (legacy entry, src/demo)
	uvicorn src.demo.app:app --host 0.0.0.0 --port 8080 --reload

serve-chat:  ## Run the chat playground locally (port 8080)
	python -m duecare.chat.run_server --host 0.0.0.0 --port 8080

serve-classifier:  ## Run the classifier locally (port 8081)
	python -m duecare.chat.run_server --classifier --host 0.0.0.0 --port 8081

# ── Verify + Reproduce ───────────────────────────────────────────
verify:  ## Smoke-check installation: harness imports + counts above thresholds
	python scripts/verify.py

reproduce:  ## Reproduce all submission claims end-to-end (~5 min)
	bash scripts/reproduce.sh

# ── One-command lifecycle (the friendliest entry points) ─────────
demo:  ## Bring up the whole stack + pull Gemma 4 + smoke-test (recommended for first-time)
	bash scripts/deploy-stack.sh

demo-with-monitoring:  ## demo + Prometheus/Grafana/Loki/OTel observability stack
	bash scripts/deploy-stack.sh --observability

demo-with-auth:  ## demo + oauth2-proxy SSO overlay (configure OAUTH2_* in .env first)
	bash scripts/deploy-stack.sh --auth

doctor:  ## Diagnose a running deployment (prints health report)
	bash scripts/duecare-doctor.sh

backup:  ## Snapshot journal + audit log + caddy state to backups/duecare-DATE.tgz
	bash scripts/backup.sh

backup-light:  ## Same as backup but skip the Ollama model cache (90% smaller)
	bash scripts/backup.sh --skip-models

# ── Docker ───────────────────────────────────────────────────────
docker: docker-up  ## Alias for docker-up
docker-build:  ## Build the multi-arch Docker image (chat + classifier)
	docker build -t duecare-llm:latest -f Dockerfile .

docker-up:  ## Start chat + classifier via docker-compose (one command)
	docker compose up -d --build

docker-up-auth:  ## Start chat + classifier with OAuth2-proxy in front (OIDC SSO)
	docker compose -f docker-compose.yml -f docker-compose.auth.yml up -d --build

docker-down:  ## Stop docker-compose stack
	docker compose down

docker-logs:  ## Tail docker-compose logs
	docker compose logs -f --tail=100

docker-run:
	docker run --rm -it duecare-llm:latest --help

# ── Docker (developer hot-reload compose) ────────────────────────
docker-dev: docker-dev-up  ## Alias for docker-dev-up
docker-dev-up:  ## Start hot-reload dev stack (bind-mounts repo, ruff/mypy/pytest in image)
	docker compose -f docker-compose.dev.yml up -d --build

docker-dev-down:  ## Stop dev stack
	docker compose -f docker-compose.dev.yml down

docker-dev-shell:  ## Open a bash shell inside the dev container
	docker compose -f docker-compose.dev.yml exec dev bash

docker-dev-test:  ## Run pytest inside the dev container (fastest local feedback loop)
	docker compose -f docker-compose.dev.yml exec dev pytest -x

# ── Observability stack (Prometheus + Grafana + OTel + Loki) ─────
observability: observability-up  ## Alias for observability-up
observability-up:  ## Start Prom + Loki + OTel + Grafana (http://localhost:3000)
	docker compose -f infra/observability/docker-compose.yml up -d

observability-down:  ## Stop observability stack
	docker compose -f infra/observability/docker-compose.yml down

observability-logs:  ## Tail observability stack logs
	docker compose -f infra/observability/docker-compose.yml logs -f --tail=100

# ── Kubernetes (Helm) ────────────────────────────────────────────
helm: helm-install  ## Alias for helm-install
helm-install:  ## Install the Duecare Helm chart into the current kube context
	helm upgrade --install duecare infra/helm/duecare \
		--namespace duecare --create-namespace \
		--values infra/helm/duecare/values.yaml

helm-uninstall:  ## Remove the Duecare Helm release
	helm uninstall duecare --namespace duecare

helm-lint:  ## Lint the Helm chart for syntax + best-practice violations
	helm lint infra/helm/duecare

helm-template:  ## Render the Helm chart locally (preview the K8s YAML before apply)
	helm template duecare infra/helm/duecare \
		--namespace duecare \
		--values infra/helm/duecare/values.yaml

# ── Cleanup ──────────────────────────────────────────────────────
clean:  ## Remove build artifacts (dist/, __pycache__, *.egg-info)
	find packages -type d -name dist -exec rm -rf {} + 2>/dev/null || true
	find . -type d -name __pycache__ -exec rm -rf {} + 2>/dev/null || true
	find . -type d -name "*.egg-info" -exec rm -rf {} + 2>/dev/null || true
