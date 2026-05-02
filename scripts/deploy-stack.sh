#!/usr/bin/env bash
# Duecare Docker-stack one-command bring-up.
#
# Audience: anyone who wants Duecare running locally without learning
# Docker Compose first. NGO directors. Developers spinning up a demo.
# Sysadmins evaluating the harness on a Mac mini.
#
# Usage:
#   ./scripts/deploy-stack.sh                # default: Gemma 4 E2B
#   ./scripts/deploy-stack.sh --model gemma4:e4b
#   ./scripts/deploy-stack.sh --model gemma3:1b --port 9000
#   ./scripts/deploy-stack.sh --dev          # use docker-compose.dev.yml
#   ./scripts/deploy-stack.sh --auth         # add oauth2-proxy overlay
#   ./scripts/deploy-stack.sh --observability  # also bring up Prom+Grafana
#   ./scripts/deploy-stack.sh --check        # smoke-test an already-running stack
#
# What it does:
#   1. Checks Docker is installed + running.
#   2. Prepares .env (copies .env.example if missing).
#   3. Pulls/builds the Duecare image.
#   4. docker compose up -d (with the right overlay).
#   5. Waits for Ollama healthcheck, pulls the chosen model.
#   6. Smoke-tests /healthz + /metrics + /api/chat.
#   7. Prints the URLs + the next 3 commands.

set -euo pipefail

# ───────── Pretty output ─────────
BOLD=$'\033[1m'; DIM=$'\033[2m'; RESET=$'\033[0m'
GREEN=$'\033[32m'; YELLOW=$'\033[33m'; RED=$'\033[31m'; BLUE=$'\033[34m'
say()  { printf "%s\n" "${BOLD}$*${RESET}"; }
note() { printf "%s\n" "${DIM}$*${RESET}"; }
ok()   { printf "%s\n" "${GREEN}  ✓ $*${RESET}"; }
warn() { printf "%s\n" "${YELLOW}  ⚠ $*${RESET}"; }
fail() { printf "%s\n" "${RED}  ✗ $*${RESET}"; exit 1; }
hr()   { printf "%s\n" "${DIM}────────────────────────────────────────${RESET}"; }

# ───────── Defaults + flags ─────────
MODEL="gemma4:e2b"
HTTP_PORT=8080
DEV=0
AUTH=0
OBS=0
CHECK_ONLY=0

while [[ $# -gt 0 ]]; do
  case "$1" in
    --model)         MODEL="$2"; shift 2 ;;
    --port)          HTTP_PORT="$2"; shift 2 ;;
    --dev)           DEV=1; shift ;;
    --auth)          AUTH=1; shift ;;
    --observability) OBS=1; shift ;;
    --check)         CHECK_ONLY=1; shift ;;
    --help|-h)
      grep '^#' "$0" | sed 's/^# //; s/^#//' | head -25
      exit 0 ;;
    *) fail "Unknown flag: $1 (try --help)" ;;
  esac
done

# ───────── Sanity checks ─────────
say "Duecare deploy-stack"
hr

if [[ $CHECK_ONLY -eq 0 ]]; then
  command -v docker >/dev/null 2>&1 || fail "Docker not found. Install: https://docs.docker.com/get-docker/"
  docker info >/dev/null 2>&1 || fail "Docker daemon not running. Start Docker Desktop / 'systemctl start docker'."
  ok "Docker ready"

  if ! docker compose version >/dev/null 2>&1; then
    fail "Docker Compose v2 required. Newer Docker Desktop has it built-in."
  fi
  ok "Docker Compose v2 ready"

  cd "$(dirname "$0")/.."
  if [[ ! -f .env ]]; then
    cp .env.example .env
    note "Created .env from .env.example — edit if you need TLS keys / OAuth"
  fi
  ok ".env in place"

  # Ensure model is set in .env
  if ! grep -q "^DUECARE_OLLAMA_MODEL=$MODEL" .env 2>/dev/null; then
    sed -i.bak '/^DUECARE_OLLAMA_MODEL=/d' .env
    echo "DUECARE_OLLAMA_MODEL=$MODEL" >> .env
    rm -f .env.bak
    ok "Set DUECARE_OLLAMA_MODEL=$MODEL in .env"
  fi
  if ! grep -q "^DUECARE_CHAT_PORT=$HTTP_PORT" .env 2>/dev/null; then
    sed -i.bak '/^DUECARE_CHAT_PORT=/d' .env
    echo "DUECARE_CHAT_PORT=$HTTP_PORT" >> .env
    rm -f .env.bak
    ok "Set DUECARE_CHAT_PORT=$HTTP_PORT in .env"
  fi

  # ───────── Compose flags ─────────
  COMPOSE_FILES=(-f docker-compose.yml)
  if [[ $DEV -eq 1 ]]; then
    COMPOSE_FILES=(-f docker-compose.dev.yml)
    say "Using DEV compose (hot-reload, bind-mount, ruff/mypy/pytest in image)"
  fi
  if [[ $AUTH -eq 1 ]]; then
    COMPOSE_FILES+=(-f docker-compose.auth.yml)
    say "Adding OAuth2-proxy overlay"
    grep -q "^OAUTH2_CLIENT_ID=" .env || warn "OAUTH2_CLIENT_ID not set in .env — auth will fail until you fill it in"
  fi

  hr
  say "Starting stack (this is the slow part — first build is ~3 min)"
  docker compose "${COMPOSE_FILES[@]}" up -d --build
  ok "Stack up"

  # ───────── Wait for Ollama ─────────
  say "Waiting for Ollama healthcheck"
  for i in $(seq 1 60); do
    if docker compose "${COMPOSE_FILES[@]}" exec -T ollama ollama list >/dev/null 2>&1; then
      ok "Ollama ready"
      break
    fi
    [[ $i -eq 60 ]] && fail "Ollama didn't come healthy in 60s. Check 'docker compose logs ollama'"
    sleep 1
  done

  # Pull the model (idempotent — Ollama skips if cached)
  say "Pulling model $MODEL (first time downloads ~$(case $MODEL in gemma4:e2b|gemma2:2b) echo 1.5 GB ;; gemma4:e4b) echo 3.5 GB ;; gemma3:1b) echo 0.6 GB ;; *) echo a few GB ;; esac))"
  docker compose "${COMPOSE_FILES[@]}" exec -T ollama ollama pull "$MODEL" || warn "Model pull failed; chat will fall back to canned responses until it succeeds"
fi

# ───────── Bring up observability if asked ─────────
if [[ $OBS -eq 1 ]]; then
  hr
  say "Starting observability stack (Prometheus + Grafana + Loki + OTel)"
  cd "$(dirname "$0")/../infra/observability"
  docker compose up -d
  ok "Observability up"
  cd - >/dev/null
fi

# ───────── Smoke test ─────────
hr
say "Smoke-testing the stack"
URL="http://localhost:$HTTP_PORT"
if curl -sf "$URL/healthz" >/dev/null; then
  ok "GET $URL/healthz returns 200"
else
  fail "$URL/healthz unreachable. Try: docker compose logs duecare-chat"
fi

if curl -s "$URL/metrics" 2>/dev/null | head -1 | grep -q '#'; then
  ok "GET $URL/metrics returns Prometheus exposition"
else
  warn "$URL/metrics not Prometheus-shaped — observability extras may be missing (pip install duecare-llm-server[observability])"
fi

# Try a real chat call (will only succeed if the model is loaded)
RESP=$(curl -sf -X POST "$URL/api/chat" \
  -H 'content-type: application/json' \
  -d '{"question": "What is the legal placement-fee cap for Filipino domestic workers going to Hong Kong?"}' \
  2>/dev/null || true)
if [[ -n "$RESP" ]]; then
  ok "POST $URL/api/chat returned a response"
else
  warn "POST /api/chat returned empty — model may still be warming up. Try again in 30s."
fi

# ───────── Final report ─────────
hr
say "Stack ready"
echo
echo "  Chat:        $URL"
echo "  OpenAPI:     $URL/docs"
echo "  Metrics:     $URL/metrics"
echo "  Healthz:     $URL/healthz"
[[ $OBS -eq 1 ]] && echo "  Grafana:     http://localhost:3000 (admin / admin)"
[[ $OBS -eq 1 ]] && echo "  Prometheus:  http://localhost:9090"
[[ $AUTH -eq 1 ]] && echo "  OAuth proxy: http://localhost:4180"
echo
echo "  Logs:    docker compose logs -f --tail=100"
echo "  Stop:    docker compose down"
echo "  Doctor:  bash scripts/duecare-doctor.sh"
echo
note "First chat in the browser may take ~30s while the model warms up."
