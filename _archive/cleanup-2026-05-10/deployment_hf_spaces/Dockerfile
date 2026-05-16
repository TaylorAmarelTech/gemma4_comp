# Dockerfile — HuggingFace Spaces edition of the DueCare demo.
# Differs from Dockerfile.demo only in port (7860, the HF Spaces default).
# Build locally: docker build -f deployment/hf_spaces/Dockerfile -t duecare-demo-space .
# Run:           docker run -p 7860:7860 duecare-demo-space
# Deploy: see deployment/hf_spaces/README.md

FROM python:3.12-slim AS base

WORKDIR /app

RUN apt-get update && apt-get install -y --no-install-recommends \
        git curl \
    && rm -rf /var/lib/apt/lists/*

COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY packages/ packages/
COPY pyproject.toml .
RUN pip install --no-cache-dir \
        -e packages/duecare-llm-core \
        -e packages/duecare-llm-models \
        -e packages/duecare-llm-domains \
        -e packages/duecare-llm-tasks \
        -e packages/duecare-llm-agents \
        -e packages/duecare-llm-workflows \
        -e packages/duecare-llm-publishing \
        -e packages/duecare-llm

COPY src/ src/
COPY configs/ configs/

RUN useradd --create-home --shell /bin/bash duecare
USER duecare

EXPOSE 7860

HEALTHCHECK --interval=30s --timeout=5s --retries=3 \
    CMD curl -f http://localhost:7860/api/v1/health || exit 1

ENTRYPOINT ["python", "-m", "uvicorn", "src.demo.app:app", \
            "--host", "0.0.0.0", "--port", "7860"]
