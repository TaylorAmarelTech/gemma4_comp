#!/usr/bin/env bash
# DueCare coding harness — Aider driven by Ollama-cloud GLM 5.2 (architect) + Kimi K2.6 (editor).
# No Claude / no Anthropic. Reads OLLAMA_API_KEY from the repo .env and targets the Ollama
# cloud OpenAI-compatible endpoint. Model selection + behavior live in .aider.conf.yml.
#
# Usage (from repo root):
#   scripts/harness/aider-ollama.sh                          # interactive REPL
#   scripts/harness/aider-ollama.sh path/to/file.py          # open files in the session
#   scripts/harness/aider-ollama.sh --message "..." f.py     # one-shot, headless
#
# Override knobs (optional env):
#   OLLAMA_OPENAI_BASE   default https://ollama.com/v1
#   AIDER_BIN            default $HOME/.local/bin/aider
set -euo pipefail
repo="$(cd "$(dirname "${BASH_SOURCE[0]}")/../.." && pwd)"

set -a
# shellcheck disable=SC1091
[ -f "$repo/.env" ] && . "$repo/.env"
set +a

: "${OLLAMA_API_KEY:?OLLAMA_API_KEY not set — add it to $repo/.env}"
base="${OLLAMA_OPENAI_BASE:-https://ollama.com/v1}"

# Aider also auto-loads the repo .env, which defines a real OPENAI_API_KEY — that
# would clobber our Ollama key (→ 401). Hand Aider a private env-file via --env-file
# (Aider loads it last, so it wins). Mode 0600, removed on exit.
umask 177
env_tmp="$(mktemp "${TMPDIR:-/tmp}/aider-ollama.XXXXXX")"
trap 'rm -f "$env_tmp"' EXIT
{ printf 'OPENAI_API_BASE=%s\n' "$base"
  printf 'OPENAI_API_KEY=%s\n'  "$OLLAMA_API_KEY"; } > "$env_tmp"

export PYTHONUTF8=1 PYTHONIOENCODING=utf-8

# Keep Aider's history out of the repo root (the root-file policy test globs *.md).
mkdir -p "$repo/.aider"
hist_args=( --chat-history-file "$repo/.aider/chat.history.md"
            --input-history-file "$repo/.aider/input.history"
            --llm-history-file  "$repo/.aider/llm.history" )

# Swap roles without editing .aider.conf.yml, e.g.:
#   DUECARE_ARCHITECT=kimi-k2.6 DUECARE_EDITOR=glm-5.2 scripts/harness/aider-ollama.sh ...
# A bare model id or an "openai/" id both work.
role_args=()
[ -n "${DUECARE_ARCHITECT:-}" ] && role_args+=( --model        "openai/${DUECARE_ARCHITECT#openai/}" )
[ -n "${DUECARE_EDITOR:-}"    ] && role_args+=( --editor-model "openai/${DUECARE_EDITOR#openai/}" )

aider_bin="${AIDER_BIN:-$HOME/.local/bin/aider}"
[ -x "$aider_bin" ] || aider_bin="aider"   # fall back to PATH
"$aider_bin" --env-file "$env_tmp" "${hist_args[@]}" "${role_args[@]+"${role_args[@]}"}" "$@"
