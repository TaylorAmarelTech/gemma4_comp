#!/usr/bin/env bash
# Duecare diagnostic CLI — "what's wrong with my deployment?"
#
# Runs a comprehensive health check + prints a one-screen diagnostic
# report. Use this when chat is slow / errors are spiking / the
# Reports tab is empty / a worker can't connect.
#
# Usage:
#   bash scripts/duecare-doctor.sh                 # default: localhost:8080
#   bash scripts/duecare-doctor.sh --url https://chat.your-org.com
#   bash scripts/duecare-doctor.sh --json          # machine-readable

set -euo pipefail

URL="${DUECARE_URL:-http://localhost:8080}"
OUTPUT="text"

while [[ $# -gt 0 ]]; do
  case "$1" in
    --url)  URL="$2"; shift 2 ;;
    --json) OUTPUT="json"; shift ;;
    --help|-h) grep '^#' "$0" | sed 's/^# //;s/^#//' | head -15; exit 0 ;;
    *) echo "Unknown flag: $1"; exit 1 ;;
  esac
done

# ─── Pretty / JSON helpers ───
GREEN=$'\033[32m'; YELLOW=$'\033[33m'; RED=$'\033[31m'
BOLD=$'\033[1m'; DIM=$'\033[2m'; RESET=$'\033[0m'
declare -a RESULTS=()

check() {
  local name="$1" status="$2" detail="$3"
  case "$status" in
    pass) RESULTS+=("PASS:$name:$detail") ;;
    warn) RESULTS+=("WARN:$name:$detail") ;;
    fail) RESULTS+=("FAIL:$name:$detail") ;;
  esac
}

# ─── Checks ───

# 1. Docker daemon
if command -v docker >/dev/null && docker info >/dev/null 2>&1; then
  check "docker" pass "$(docker --version | awk '{print $3}' | tr -d ',')"
else
  check "docker" fail "not installed or daemon down"
fi

# 2. Docker Compose v2
if docker compose version >/dev/null 2>&1; then
  check "compose-v2" pass "$(docker compose version --short)"
else
  check "compose-v2" fail "not available"
fi

# 3. Disk free
DF_FREE_GB=$(df -BG --output=avail . 2>/dev/null | tail -1 | tr -d 'G ' || echo 0)
if [[ ${DF_FREE_GB:-0} -ge 10 ]]; then
  check "disk-free" pass "${DF_FREE_GB} GB"
elif [[ ${DF_FREE_GB:-0} -ge 5 ]]; then
  check "disk-free" warn "${DF_FREE_GB} GB (recommend ≥10 GB for model cache)"
else
  check "disk-free" fail "${DF_FREE_GB} GB (need ≥5 GB minimum)"
fi

# 4. RAM (Linux + macOS)
if [[ "$(uname)" == "Linux" ]]; then
  RAM_GB=$(awk '/^MemTotal:/ {printf "%.0f", $2/1024/1024}' /proc/meminfo)
elif [[ "$(uname)" == "Darwin" ]]; then
  RAM_GB=$(sysctl -n hw.memsize | awk '{printf "%.0f", $1/1024/1024/1024}')
else
  RAM_GB=0
fi
if [[ ${RAM_GB:-0} -ge 16 ]]; then
  check "ram" pass "${RAM_GB} GB"
elif [[ ${RAM_GB:-0} -ge 8 ]]; then
  check "ram" warn "${RAM_GB} GB (E4B needs ≥16 GB; E2B works on 8 GB)"
else
  check "ram" warn "${RAM_GB:-?} GB (only Gemma 3 1B fits comfortably below 8 GB)"
fi

# 5. Healthz reachable
HEALTHZ=$(curl -sf -m 5 "$URL/healthz" 2>/dev/null || true)
if [[ -n "$HEALTHZ" ]]; then
  check "chat-healthz" pass "$URL responds"
else
  check "chat-healthz" fail "$URL/healthz unreachable"
fi

# 6. Metrics endpoint
METRICS_HEAD=$(curl -sf -m 5 "$URL/metrics" 2>/dev/null | head -1 || true)
if [[ "$METRICS_HEAD" == \#* ]]; then
  check "metrics" pass "Prometheus exposition served"
else
  check "metrics" warn "endpoint not Prometheus-shaped (install [observability] extras)"
fi

# 7. Model present in Ollama
if docker compose ps ollama >/dev/null 2>&1 && \
   docker compose exec -T ollama ollama list 2>/dev/null | grep -q "gemma"; then
  MODEL_LIST=$(docker compose exec -T ollama ollama list 2>/dev/null | tail -n +2 | awk '{print $1}' | paste -sd, -)
  check "ollama-model" pass "$MODEL_LIST"
elif docker compose ps ollama >/dev/null 2>&1; then
  check "ollama-model" warn "no Gemma model pulled yet — chat falls back to canned responses"
else
  check "ollama-model" fail "Ollama service not running"
fi

# 8. Containers running
RUNNING=$(docker compose ps --format json 2>/dev/null | tr -d '\n' | grep -o '"State":"running"' | wc -l || echo 0)
check "containers-running" pass "$RUNNING container(s)"

# 9. Recent errors in logs
ERRS=$(docker compose logs --tail=200 2>/dev/null | grep -iE 'error|exception|critical' | grep -v "GET /metrics" | wc -l || echo 0)
if [[ $ERRS -eq 0 ]]; then
  check "recent-errors" pass "no errors in last 200 log lines"
elif [[ $ERRS -lt 5 ]]; then
  check "recent-errors" warn "$ERRS error lines in last 200"
else
  check "recent-errors" fail "$ERRS error lines in last 200 — investigate"
fi

# 10. Real chat call
CHAT_RESP=$(curl -sf -m 30 -X POST "$URL/api/chat" \
  -H 'content-type: application/json' \
  -H 'X-Tenant-ID: doctor' \
  -d '{"question":"hello"}' 2>/dev/null || true)
if [[ -n "$CHAT_RESP" ]]; then
  check "chat-roundtrip" pass "POST /api/chat returned a response"
else
  check "chat-roundtrip" warn "no response (maybe still warming up)"
fi

# ─── Output ───
if [[ "$OUTPUT" == "json" ]]; then
  echo "["
  for i in "${!RESULTS[@]}"; do
    IFS=':' read -r status name detail <<< "${RESULTS[$i]}"
    printf '  {"check": "%s", "status": "%s", "detail": "%s"}' "$name" "$status" "$detail"
    [[ $i -lt $((${#RESULTS[@]} - 1)) ]] && echo "," || echo ""
  done
  echo "]"
else
  echo
  echo "${BOLD}Duecare diagnostic — $URL${RESET}"
  echo "${DIM}$(date)${RESET}"
  echo
  PASS=0; WARN=0; FAIL=0
  for r in "${RESULTS[@]}"; do
    IFS=':' read -r status name detail <<< "$r"
    case "$status" in
      PASS) printf "  %s✓ %-20s%s %s%s%s\n" "$GREEN" "$name" "$RESET" "$DIM" "$detail" "$RESET"; PASS=$((PASS+1)) ;;
      WARN) printf "  %s⚠ %-20s%s %s\n" "$YELLOW" "$name" "$RESET" "$detail"; WARN=$((WARN+1)) ;;
      FAIL) printf "  %s✗ %-20s%s %s\n" "$RED"    "$name" "$RESET" "$detail"; FAIL=$((FAIL+1)) ;;
    esac
  done
  echo
  echo "  ${GREEN}$PASS pass${RESET}  ${YELLOW}$WARN warn${RESET}  ${RED}$FAIL fail${RESET}"
  echo
  if [[ $FAIL -gt 0 ]]; then
    echo "  ${BOLD}Next step:${RESET} see docs/considerations/runbook.md"
    echo "  ${BOLD}Logs:${RESET}     docker compose logs --tail=100"
    exit 1
  fi
fi
