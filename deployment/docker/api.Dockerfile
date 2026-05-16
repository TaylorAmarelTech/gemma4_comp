FROM python:3.12-slim

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PIP_NO_CACHE_DIR=1

WORKDIR /app

RUN apt-get update \
    && apt-get install -y --no-install-recommends curl \
    && rm -rf /var/lib/apt/lists/*

COPY packages /app/packages
COPY configs /app/configs

RUN python -m pip install --upgrade pip \
    && python -m pip install \
        -e /app/packages/duecare-llm-core \
        -e /app/packages/duecare-llm-models \
        -e /app/packages/duecare-llm-domains \
        -e /app/packages/duecare-llm-tasks \
        -e /app/packages/duecare-llm-evidence-db \
        -e /app/packages/duecare-llm-engine \
        -e /app/packages/duecare-llm-nl2sql \
        -e /app/packages/duecare-llm-research-tools \
        -e /app/packages/duecare-llm-benchmark \
        -e /app/packages/duecare-llm-server \
        -e /app/packages/duecare-llm-cli

RUN useradd --create-home --shell /usr/sbin/nologin duecare \
    && mkdir -p /data/duecare /app/cache \
    && chown -R duecare:duecare /data/duecare /app/cache

USER duecare
EXPOSE 8080

HEALTHCHECK --interval=30s --timeout=10s --start-period=60s --retries=3 \
    CMD curl -fsS http://localhost:8080/healthz || exit 1

CMD ["duecare", "serve", "--host", "0.0.0.0", "--port", "8080"]
