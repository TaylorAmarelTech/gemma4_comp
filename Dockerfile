# Duecare LLM — multi-stage Dockerfile.
#
# Builds all 17 packages from source, then produces a slim runtime
# image with the chat playground + classifier server. Multi-arch:
# the same Dockerfile works on linux/amd64 (x86) and linux/arm64
# (Apple Silicon, AWS Graviton, Raspberry Pi 4+, etc.).
#
# Build (single arch):
#   docker build -t duecare-llm:latest .
#
# Build (multi-arch, push to a registry):
#   docker buildx build --platform linux/amd64,linux/arm64 \
#       --tag ghcr.io/tayloramareltech/duecare-llm:latest --push .
#
# Run (chat playground on port 8080):
#   docker run -p 8080:8080 duecare-llm:latest
#
# Run with Ollama for local Gemma 4 inference:
#   docker compose up    # uses docker-compose.yml in repo root

ARG PYTHON_VERSION=3.12

# =============================================================================
# Stage 1: builder. Builds wheels for all 17 packages.
# =============================================================================
FROM python:${PYTHON_VERSION}-slim AS builder

WORKDIR /build

RUN apt-get update \
    && apt-get install -y --no-install-recommends \
        build-essential git \
    && rm -rf /var/lib/apt/lists/*

RUN pip install --no-cache-dir --upgrade pip wheel build

# Copy package sources only (skip notebooks / kaggle / docs to keep
# the build context tight)
COPY packages/ ./packages/
COPY pyproject.toml ./

# Build wheels into /build/dist (in-package dependency order).
RUN mkdir -p /build/dist \
    && for pkg in \
        duecare-llm-core duecare-llm-models duecare-llm-domains \
        duecare-llm-tasks duecare-llm-agents duecare-llm-workflows \
        duecare-llm-publishing duecare-llm-chat duecare-llm; do \
            if [ -d "packages/$pkg" ]; then \
                echo "==> Building $pkg" \
                && python -m build --wheel --outdir /build/dist packages/$pkg \
                && echo "==> $pkg built"; \
            fi \
        done

# =============================================================================
# Stage 2: runtime. Slim image with just the wheels installed.
# =============================================================================
FROM python:${PYTHON_VERSION}-slim AS runtime

LABEL org.opencontainers.image.source="https://github.com/TaylorAmarelTech/gemma4_comp"
LABEL org.opencontainers.image.description="Duecare safety harness for Gemma 4 — chat playground + classifier API"
LABEL org.opencontainers.image.licenses="MIT"

RUN apt-get update \
    && apt-get install -y --no-install-recommends \
        curl ca-certificates \
    && rm -rf /var/lib/apt/lists/*

# Non-root user — never need root at runtime
RUN useradd --system --create-home --uid 1000 duecare
WORKDIR /home/duecare/app

# Install the wheels from the builder stage
COPY --from=builder /build/dist/*.whl /tmp/wheels/
RUN pip install --no-cache-dir /tmp/wheels/*.whl \
    && rm -rf /tmp/wheels

# Copy any optional config the user wants pre-baked
COPY --chown=duecare:duecare configs/ ./configs/

USER duecare

EXPOSE 8080

HEALTHCHECK --interval=30s --timeout=5s --start-period=15s --retries=3 \
    CMD curl --fail --silent http://localhost:8080/healthz || exit 1

ENV DUECARE_HOST=0.0.0.0
ENV DUECARE_PORT=8080
ENV DUECARE_LOG_LEVEL=info

ENTRYPOINT ["python", "-m", "duecare.chat.run_server"]
CMD ["--host", "0.0.0.0", "--port", "8080"]
