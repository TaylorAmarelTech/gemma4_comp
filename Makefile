.PHONY: install test build lint clean serve notebooks adversarial cleanroom kaggle-push kaggle-status

PACKAGES := duecare-llm-core duecare-llm-models duecare-llm-domains duecare-llm-tasks \
            duecare-llm-agents duecare-llm-workflows duecare-llm-publishing duecare-llm

# ── Install ──────────────────────────────────────────────────────
install:
	uv sync --all-packages

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
notebooks:
	python scripts/build_kaggle_notebooks.py
	python scripts/build_notebook_00.py
	python scripts/build_notebook_00a.py
	python scripts/build_notebook_00b.py

# ── Demo Server ──────────────────────────────────────────────────
serve:
	uvicorn src.demo.app:app --host 0.0.0.0 --port 8080 --reload

# ── Docker ───────────────────────────────────────────────────────
docker-build:
	docker build -t duecare-llm:latest .

docker-run:
	docker run --rm -it duecare-llm:latest --help

# ── Cleanup ──────────────────────────────────────────────────────
clean:
	find packages -type d -name dist -exec rm -rf {} + 2>/dev/null || true
	find . -type d -name __pycache__ -exec rm -rf {} + 2>/dev/null || true
	find . -type d -name "*.egg-info" -exec rm -rf {} + 2>/dev/null || true
