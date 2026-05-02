.PHONY: install install-uv install-pip dev test test-stress adversarial cleanroom \
        build lint serve serve-chat serve-classifier verify reproduce \
        docker docker-build docker-up docker-down docker-logs \
        helm helm-install helm-uninstall \
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

# ── Docker ───────────────────────────────────────────────────────
docker: docker-up  ## Alias for docker-up
docker-build:  ## Build the multi-arch Docker image (chat + classifier)
	docker build -t duecare-llm:latest -f Dockerfile .

docker-up:  ## Start chat + classifier via docker-compose (one command)
	docker compose up -d --build

docker-down:  ## Stop docker-compose stack
	docker compose down

docker-logs:  ## Tail docker-compose logs
	docker compose logs -f --tail=100

docker-run:
	docker run --rm -it duecare-llm:latest --help

# ── Kubernetes (Helm) ────────────────────────────────────────────
helm: helm-install  ## Alias for helm-install
helm-install:  ## Install the Duecare Helm chart into the current kube context
	helm upgrade --install duecare infra/helm/duecare \
		--namespace duecare --create-namespace \
		--values infra/helm/duecare/values.yaml

helm-uninstall:  ## Remove the Duecare Helm release
	helm uninstall duecare --namespace duecare

# ── Cleanup ──────────────────────────────────────────────────────
clean:  ## Remove build artifacts (dist/, __pycache__, *.egg-info)
	find packages -type d -name dist -exec rm -rf {} + 2>/dev/null || true
	find . -type d -name __pycache__ -exec rm -rf {} + 2>/dev/null || true
	find . -type d -name "*.egg-info" -exec rm -rf {} + 2>/dev/null || true
