# Duecare Live Demo — HF Spaces Docker image
# Builds Chromium + the Hanchen Unsloth stack + the duecare wheels +
# starts the FastAPI server on port 8080.

FROM nvidia/cuda:12.1.0-runtime-ubuntu22.04 AS builder

# System deps
RUN apt-get update && apt-get install -y --no-install-recommends \
    python3.11 python3-pip curl git wget ca-certificates \
    && rm -rf /var/lib/apt/lists/*

WORKDIR /app

# Hanchen's Unsloth Gemma 4 stack
RUN pip install --no-cache-dir \
    "torch>=2.8.0" "triton>=3.4.0" \
    "torchvision" "bitsandbytes" \
    "unsloth" "unsloth_zoo>=2026.4.6" \
    "transformers==5.5.0" "torchcodec" "timm"

# Server deps
RUN pip install --no-cache-dir \
    "fastapi>=0.115" "uvicorn>=0.30" "pydantic>=2.0" \
    "trafilatura>=1.12" "playwright>=1.48"

# Playwright Chromium (for A4 agentic-research; safe to skip if unused)
RUN python3 -m playwright install chromium --with-deps || true

# Duecare wheels (will be COPYed in by the Space build process)
COPY wheels/*.whl /tmp/wheels/
RUN pip install --no-cache-dir /tmp/wheels/*.whl

# The kernel.py from kaggle/live-demo/ becomes the entry script
COPY kernel.py /app/kernel.py
COPY start.sh /app/start.sh
RUN chmod +x /app/start.sh

EXPOSE 8080

# Pre-cache Gemma 4 weights at build time (HF_TOKEN required as build arg)
ARG HF_TOKEN
ENV HF_TOKEN=${HF_TOKEN}
RUN python3 -c "from huggingface_hub import snapshot_download; \
    snapshot_download('unsloth/gemma-4-E4B-it', \
                      cache_dir='/root/.cache/huggingface', \
                      token='${HF_TOKEN}')" || \
    echo "Gemma 4 weights pre-cache skipped (HF_TOKEN not provided at build)"

CMD ["/app/start.sh"]
