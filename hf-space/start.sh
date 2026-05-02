#!/bin/bash
# Entrypoint for the HF Spaces container.
# Skips the cloudflared download (HF Spaces handles HTTPS termination).
# Forces the kernel into "no-tunnel" mode by setting TUNNEL=none in env.
set -e
export TUNNEL=none
export PORT=8080
exec python3 /app/kernel.py
