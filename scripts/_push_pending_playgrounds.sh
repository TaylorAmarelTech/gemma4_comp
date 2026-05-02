#!/bin/bash
# Push the 6 Free Form Exploration kernels after UTC reset.
# Run: bash scripts/_push_pending_playgrounds.sh
set -eu

cd "$(dirname "$0")/.."

if [ -z "${KAGGLE_API_TOKEN:-}" ] && [ -z "${KAGGLE_KEY:-}" ] && [ ! -f "${HOME:-}/.kaggle/kaggle.json" ]; then
  echo "Kaggle credentials are not configured."
  echo "Set KAGGLE_API_TOKEN, or KAGGLE_USERNAME + KAGGLE_KEY, or ~/.kaggle/kaggle.json before running this script."
  exit 2
fi

PYTHON_BIN=".venv/Scripts/python.exe"
if [ ! -x "$PYTHON_BIN" ]; then
  PYTHON_BIN="python"
fi

"$PYTHON_BIN" scripts/publish_kaggle.py push-notebooks --ids 150 155 160 170 180 199
