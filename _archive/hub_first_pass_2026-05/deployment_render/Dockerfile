# Lightweight CPU-only Render deployment for duecare-ai.com.
# This intentionally does not install training, GPU, or llama.cpp deps.

FROM python:3.12-slim AS base

WORKDIR /app

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1

COPY deployment/render/requirements.txt /app/requirements.txt
RUN pip install --no-cache-dir -r /app/requirements.txt

COPY src/ /app/src/

RUN useradd --create-home --shell /bin/bash duecare
USER duecare

EXPOSE 10000

HEALTHCHECK --interval=30s --timeout=5s --retries=3 \
    CMD python -c "import urllib.request; urllib.request.urlopen('http://127.0.0.1:10000/healthz', timeout=3).read()" || exit 1

ENTRYPOINT ["sh", "-c", "uvicorn src.hub.app:app --host 0.0.0.0 --port ${PORT:-10000}"]
