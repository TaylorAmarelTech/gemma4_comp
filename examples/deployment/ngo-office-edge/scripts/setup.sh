#!/usr/bin/env bash
# NGO-office-edge setup — one-command bring-up tailored for the
# director walkthrough at docs/scenarios/ngo-office-deployment.md.
#
# Differs from scripts/deploy-stack.sh by:
#   - Defaulting to docker-compose.yml in THIS directory (the
#     ngo-office-edge variant — same image + Ollama + Caddy + mDNS)
#   - Setting DUECARE_DEFAULT_TENANT to "ngo-office" so every
#     un-authenticated request gets attributed correctly
#   - Picking the model based on detected RAM
#   - Printing NGO-specific next-steps

set -euo pipefail

cd "$(dirname "$0")/.."   # examples/deployment/ngo-office-edge/

# ─── Pretty output ───
GREEN=$'\033[32m'; YELLOW=$'\033[33m'; RED=$'\033[31m'
BOLD=$'\033[1m'; DIM=$'\033[2m'; RESET=$'\033[0m'
say()  { printf "%s\n" "${BOLD}$*${RESET}"; }
ok()   { printf "%s\n" "${GREEN}  ✓ $*${RESET}"; }
warn() { printf "%s\n" "${YELLOW}  ⚠ $*${RESET}"; }
fail() { printf "%s\n" "${RED}  ✗ $*${RESET}"; exit 1; }

say "NGO-office-edge setup"
echo

# ─── Detect RAM + recommend model ───
if [[ "$(uname)" == "Linux" ]]; then
  RAM_GB=$(awk '/^MemTotal:/ {printf "%.0f", $2/1024/1024}' /proc/meminfo)
elif [[ "$(uname)" == "Darwin" ]]; then
  RAM_GB=$(sysctl -n hw.memsize | awk '{printf "%.0f", $1/1024/1024/1024}')
else
  RAM_GB=8
fi

if [[ ${RAM_GB:-0} -ge 32 ]]; then
  MODEL="gemma4:e4b"
  ok "Detected ${RAM_GB} GB RAM — using gemma4:e4b (higher quality)"
elif [[ ${RAM_GB:-0} -ge 8 ]]; then
  MODEL="gemma4:e2b"
  ok "Detected ${RAM_GB} GB RAM — using gemma4:e2b (recommended)"
else
  MODEL="gemma3:1b"
  warn "Detected ${RAM_GB} GB RAM — using gemma3:1b (smaller; only model that fits)"
fi

# ─── Prepare .env ───
if [[ ! -f .env ]]; then
  if [[ -f ../local-all-in-one/.env.example ]]; then
    cp ../local-all-in-one/.env.example .env
  else
    cp ../../../.env.example .env
  fi
  ok "Created .env from .env.example"
fi
sed -i.bak '/^DUECARE_OLLAMA_MODEL=/d' .env
echo "DUECARE_OLLAMA_MODEL=$MODEL" >> .env
sed -i.bak '/^DUECARE_DEFAULT_TENANT=/d' .env
echo "DUECARE_DEFAULT_TENANT=ngo-office" >> .env
rm -f .env.bak
ok "Set DUECARE_OLLAMA_MODEL=$MODEL + DUECARE_DEFAULT_TENANT=ngo-office"

# ─── Bring up the stack ───
say "Starting stack (~5 min on first run for the model pull)"

# Linux needs the avahi profile; macOS uses built-in Bonjour
if [[ "$(uname)" == "Linux" ]]; then
  PROFILE_FLAG="--profile linux"
else
  PROFILE_FLAG=""
fi

docker compose $PROFILE_FLAG up -d --build
ok "Stack up"

# ─── Wait for Ollama + pull model ───
say "Waiting for Ollama (up to 60s)"
for i in $(seq 1 60); do
  if docker compose exec -T ollama ollama list >/dev/null 2>&1; then
    ok "Ollama ready"
    break
  fi
  [[ $i -eq 60 ]] && fail "Ollama didn't come healthy in 60s"
  sleep 1
done

say "Pulling $MODEL (first time only — ~$(case $MODEL in gemma4:e2b) echo 1.5 GB ;; gemma4:e4b) echo 3.5 GB ;; gemma3:1b) echo 0.6 GB ;; esac))"
docker compose exec -T ollama ollama pull "$MODEL"
ok "Model ready"

# ─── Smoke test ───
say "Smoke-testing"
HTTP_PORT=$(grep '^DUECARE_CHAT_PORT=' .env 2>/dev/null | cut -d= -f2)
HTTP_PORT=${HTTP_PORT:-8080}
URL="http://localhost:$HTTP_PORT"

if curl -sf -m 5 "$URL/healthz" >/dev/null; then
  ok "$URL/healthz returns 200"
else
  warn "$URL/healthz unreachable yet — give it 30 more seconds and try 'make doctor'"
fi

# ─── Final report ───
echo
say "Office stack ready"
echo
echo "  Caseworker URL:       ${BOLD}http://duecare.local${RESET}    (mDNS — same Wi-Fi only)"
echo "  Caseworker URL (alt): ${BOLD}$URL${RESET}    (this box's IP)"
echo "  Ollama:               http://localhost:11434  (model API; for Android Settings → Cloud model)"
echo
echo "  ${BOLD}Next steps:${RESET}"
echo "    1. Bookmark ${BOLD}http://duecare.local${RESET} on each caseworker's device"
echo "    2. Read docs/scenarios/ngo-office-deployment.md from step 4 (auth + backups)"
echo "    3. Hand the [Caseworker Quickstart] section of that doc to your team"
echo "    4. Add a nightly backup cron: bash scripts/backup.sh --dest /Volumes/Backup --skip-models"
echo
echo "  ${BOLD}Useful commands:${RESET}"
echo "    make doctor     # health check"
echo "    make backup     # snapshot journal + audit log"
echo "    make demo       # restart everything"
echo "    docker compose logs -f --tail=50    # tail logs"
echo
