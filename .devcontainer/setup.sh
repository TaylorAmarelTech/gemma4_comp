#!/usr/bin/env bash
# Devcontainer postCreateCommand. Runs once when the container is
# first built. Subsequent attaches skip this entirely.
set -euo pipefail

echo "==> Installing Duecare workspace (editable, all 17 packages)..."
make install-pip 2>&1 | tail -20 || pip install -e packages/duecare-llm-chat

echo ""
echo "==> Verifying..."
python scripts/verify.py || python -c "
from duecare.chat.harness import GREP_RULES, RAG_CORPUS
print(f'  GREP rules: {len(GREP_RULES)}, RAG docs: {len(RAG_CORPUS)}')
"

echo ""
echo "==> Devcontainer ready."
echo ""
echo "Try:"
echo "  make help                      # see all targets"
echo "  python -m duecare.chat.run_server   # start chat playground (port 8080)"
echo "  docker compose up              # full stack (chat + classifier + Ollama)"
