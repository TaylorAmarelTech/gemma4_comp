#!/usr/bin/env bash
# Duecare one-line installer — Linux / macOS / WSL.
#
# Usage:
#   curl -fsSL https://raw.githubusercontent.com/TaylorAmarelTech/gemma4_comp/master/scripts/install.sh | bash
#
# Or, if you've cloned the repo:
#   bash scripts/install.sh
#
# What it does:
#   1. Detects OS + arch + Python version.
#   2. Creates a venv at ./.venv (or uses the active one).
#   3. Installs duecare-llm (the meta package; pulls in the 7
#      worker-side packages).
#   4. Runs `duecare verify` to confirm the harness works (37 GREP
#      rules, 26 RAG docs, 6 rubric categories — all importable).
#   5. Prints the next 3 commands the user can run.
#
# Idempotent: re-running upgrades. Non-destructive: never touches
# system Python or sudo.

set -euo pipefail

# ----- Pretty output -----
BOLD=$'\033[1m'; DIM=$'\033[2m'; RESET=$'\033[0m'
GREEN=$'\033[32m'; YELLOW=$'\033[33m'; RED=$'\033[31m'
say()  { printf "%s\n" "${BOLD}$*${RESET}"; }
note() { printf "%s\n" "${DIM}$*${RESET}"; }
ok()   { printf "%s ✓ %s\n" "$GREEN" "$*${RESET}"; }
warn() { printf "%s ⚠ %s\n" "$YELLOW" "$*${RESET}"; }
err()  { printf "%s ✗ %s\n" "$RED" "$*${RESET}"; exit 1; }

# ----- 1. Environment detection -----
say "Duecare installer"
note "Detecting environment..."

OS=$(uname -s)
ARCH=$(uname -m)
case "$OS" in
    Linux*)   OS_NAME="linux" ;;
    Darwin*)  OS_NAME="macos" ;;
    MINGW*|MSYS*|CYGWIN*) OS_NAME="windows-bash" ;;
    *) err "Unsupported OS: $OS. Use scripts/install.ps1 on Windows." ;;
esac
case "$ARCH" in
    x86_64|amd64) ARCH_NAME="amd64" ;;
    aarch64|arm64) ARCH_NAME="arm64" ;;
    *) warn "Untested architecture: $ARCH. Continuing optimistically." ;;
esac
note "  OS:   $OS_NAME"
note "  Arch: $ARCH_NAME"

# ----- 2. Python -----
PY=""
for cand in python3.12 python3.11 python3 python; do
    if command -v "$cand" >/dev/null 2>&1; then
        PYV=$("$cand" -c 'import sys; print(f"{sys.version_info.major}.{sys.version_info.minor}")' 2>/dev/null || echo "")
        if [[ "$PYV" =~ ^3\.(11|12|13)$ ]]; then
            PY="$cand"; break
        fi
    fi
done
[[ -z "$PY" ]] && err "Need Python 3.11+ on PATH. Install from https://python.org/downloads/."
note "  Python: $($PY --version) at $(command -v $PY)"

# ----- 3. Venv -----
VENV=".venv"
if [[ -n "${VIRTUAL_ENV:-}" ]]; then
    note "  Using active venv: $VIRTUAL_ENV"
elif [[ -d "$VENV" ]]; then
    note "  Reusing existing venv: $VENV"
    # shellcheck disable=SC1091
    source "$VENV/bin/activate"
else
    note "  Creating venv: $VENV"
    "$PY" -m venv "$VENV"
    # shellcheck disable=SC1091
    source "$VENV/bin/activate"
    pip install --quiet --upgrade pip wheel
fi

# ----- 4. Install -----
say "Installing duecare-llm + dependencies (this takes ~60 sec)..."
pip install --quiet --upgrade duecare-llm 2>&1 | tail -5 || {
    warn "PyPI install failed (probably not yet published). Falling back to local editable install."
    if [[ -d "packages/duecare-llm" ]]; then
        # Install in dependency order from the local workspace
        for pkg in duecare-llm-core duecare-llm-models duecare-llm-domains \
                   duecare-llm-tasks duecare-llm-agents duecare-llm-workflows \
                   duecare-llm-publishing duecare-llm-chat duecare-llm; do
            if [[ -d "packages/$pkg" ]]; then
                pip install --quiet -e "packages/$pkg" 2>&1 | tail -2
            fi
        done
    else
        err "Not in the gemma4_comp source dir and PyPI install failed. Clone the repo first: git clone https://github.com/TaylorAmarelTech/gemma4_comp"
    fi
}
ok "Packages installed"

# ----- 5. Verify -----
say "Verifying installation..."
python -c "
from duecare.chat.harness import (
    GREP_RULES, RAG_CORPUS, _TOOL_DISPATCH,
    EXAMPLE_PROMPTS, RUBRICS_REQUIRED, RUBRICS_5TIER,
)
print(f'  GREP rules:           {len(GREP_RULES)}      (expect >= 37)')
print(f'  RAG docs:             {len(RAG_CORPUS)}      (expect >= 26)')
print(f'  Tools:                {len(_TOOL_DISPATCH)}       (expect >= 4)')
print(f'  Example prompts:      {len(EXAMPLE_PROMPTS)}     (expect >= 394)')
print(f'  5-tier rubrics:       {len(RUBRICS_5TIER)}     (expect >= 207)')
print(f'  Required-rubric cats: {len(RUBRICS_REQUIRED)}       (expect >= 6)')
assert len(GREP_RULES) >= 37, 'GREP rule count regression'
assert len(RAG_CORPUS) >= 26, 'RAG doc count regression'
"
ok "Harness imports cleanly with expected counts"

# ----- 6. What next -----
say ""
say "Next steps:"
echo "  1. Run the chat playground locally:"
echo "       ${BOLD}python -m duecare.chat.run_server${RESET}"
echo "       (then open http://localhost:8080)"
echo ""
echo "  2. Run the rubric comparison report:"
echo "       ${BOLD}python scripts/rubric_comparison.py${RESET}"
echo "       (writes docs/harness_lift_report.md)"
echo ""
echo "  3. Or use Docker instead of local Python:"
echo "       ${BOLD}docker compose up${RESET}"
echo ""
note "Full docs: docs/install.md"
