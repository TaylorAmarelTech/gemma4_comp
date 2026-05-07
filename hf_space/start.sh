#!/usr/bin/env bash
# HF Space entry point — runs uvicorn on the port the Space proxies.
set -e

PORT="${PORT:-7860}"
GIT_SHA="${DUECARE_GIT_SHA:-unknown}"
echo "[hf_space] starting on port $PORT (git_sha=$GIT_SHA)"

exec uvicorn app:app \
    --host 0.0.0.0 \
    --port "$PORT" \
    --workers 1 \
    --no-access-log \
    --timeout-keep-alive 120
