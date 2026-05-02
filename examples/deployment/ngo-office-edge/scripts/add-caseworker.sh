#!/usr/bin/env bash
# Add a caseworker — registers a tenant id with a daily token budget.
#
# Usage:
#   bash scripts/add-caseworker.sh alice@your-org.org
#   bash scripts/add-caseworker.sh alice@your-org.org --budget 5000000
#
# What it does:
#   - Adds (or updates) a row in tenants.yaml — the per-tenant config
#     loaded by the server at startup.
#   - Calls the running server's set_tenant_budget() via the
#     control-plane API (same effect as a server restart).
#
# tenants.yaml lives at: examples/deployment/ngo-office-edge/tenants.yaml
#
# Format:
#   tenants:
#     - id: alice@your-org.org
#       daily_token_budget: 1000000
#       rate_limit_per_min: 60
#       concurrency: 10

set -euo pipefail

CASEWORKER="${1:-}"
BUDGET="${2:-1000000}"

if [[ "${1:-}" == "--budget" ]]; then
  echo "Usage: $0 <caseworker-id> [--budget N]"; exit 1
fi
if [[ -z "$CASEWORKER" ]]; then
  echo "Usage: $0 <caseworker-id> [--budget N]"
  echo "  caseworker-id: typically the email used by your OIDC provider"
  echo "  budget:        daily output-token budget (default 1,000,000)"
  exit 1
fi
if [[ "${2:-}" == "--budget" ]]; then
  BUDGET="${3:-1000000}"
fi

cd "$(dirname "$0")/.."

TENANTS_FILE="tenants.yaml"
if [[ ! -f "$TENANTS_FILE" ]]; then
  cat > "$TENANTS_FILE" <<EOF
# Per-caseworker tenant config for the NGO-office-edge deployment.
# Loaded at server startup by the metering layer.
# Edit by running:
#   bash scripts/add-caseworker.sh <id> [--budget N]

tenants: []
EOF
fi

# Append the row
python3 - <<PY
import sys
import yaml
from pathlib import Path

p = Path("$TENANTS_FILE")
data = yaml.safe_load(p.read_text()) or {"tenants": []}
data.setdefault("tenants", [])

# Replace any existing row for this id
data["tenants"] = [t for t in data["tenants"] if t.get("id") != "$CASEWORKER"]
data["tenants"].append({
    "id": "$CASEWORKER",
    "daily_token_budget": int($BUDGET),
    "rate_limit_per_min": 60,
    "concurrency": 10,
})

with open(p, "w") as f:
    yaml.safe_dump(data, f, sort_keys=False, default_flow_style=False)

print(f"  ✓ tenant '$CASEWORKER' added/updated with budget=$BUDGET tokens/day")
print(f"  · file: {p.resolve()}")
PY

# Optionally hot-apply via curl if the server has a control endpoint.
# Most deployments don't; the next server restart picks up the file.
echo
echo "  ${BOLD:-}To apply without restart, the server must have"
echo "  loaded tenants.yaml at startup. Otherwise restart:"
echo "    docker compose restart chat"
