FROM python:3.12-slim AS base

WORKDIR /app

RUN apt-get update && apt-get install -y --no-install-recommends \
        git \
    && rm -rf /var/lib/apt/lists/*

COPY packages/ packages/
COPY configs/ configs/
COPY pyproject.toml .

RUN pip install --no-cache-dir \
        packages/duecare-llm-core/dist/*.whl \
        packages/duecare-llm-models/dist/*.whl \
        packages/duecare-llm-domains/dist/*.whl \
        packages/duecare-llm-tasks/dist/*.whl \
        packages/duecare-llm-agents/dist/*.whl \
        packages/duecare-llm-workflows/dist/*.whl \
        packages/duecare-llm-publishing/dist/*.whl \
        packages/duecare-llm/dist/*.whl

EXPOSE 8080

ENTRYPOINT ["python", "-m", "duecare.cli"]
