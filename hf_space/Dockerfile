FROM python:3.11-slim

# HF Space convention: write /app and run as user 1000
RUN useradd -m -u 1000 user
USER user
ENV HOME=/home/user PATH=/home/user/.local/bin:$PATH
WORKDIR $HOME/app

# System deps for httpx + certifi
USER root
RUN apt-get update && apt-get install -y --no-install-recommends \
        ca-certificates curl && \
    rm -rf /var/lib/apt/lists/*
USER user

# Pin pip for reproducibility
RUN python -m pip install --no-cache-dir --upgrade pip==25.0

# Install duecare-llm-chat from PyPI (or from a local wheel if present)
COPY --chown=user:user requirements.txt .
RUN python -m pip install --no-cache-dir -r requirements.txt

# Copy the Space-specific entry point + start script
COPY --chown=user:user app.py start.sh ./
RUN chmod +x start.sh

# HF Spaces expose port 7860 by default
EXPOSE 7860

# Healthcheck — Space's reverse proxy uses this
HEALTHCHECK --interval=30s --timeout=5s --start-period=10s --retries=3 \
    CMD curl --fail http://127.0.0.1:7860/healthz || exit 1

CMD ["./start.sh"]
