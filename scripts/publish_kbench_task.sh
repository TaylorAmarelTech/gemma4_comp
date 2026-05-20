#!/usr/bin/env bash
# scripts/publish_kbench_task.sh
#
# One-button publisher for the DueCare Kaggle Community Benchmark task.
#
# Wraps the `kaggle benchmarks tasks` CLI surface so a single command:
#
#   bash scripts/publish_kbench_task.sh
#
# performs:
#
#   1. auth check     - verifies ~/.kaggle/access_token or kaggle.json exists
#                        and the API is reachable (lists the model catalog as
#                        a probe; this works on accounts without task-creator
#                        access too, so it's the right liveness check)
#   2. enrollment probe - calls `kaggle benchmarks tasks list` and reports
#                        whether task-creator endpoints are reachable. If they
#                        return 404, the user needs to visit
#                        https://www.kaggle.com/benchmarks/tasks/new in the
#                        browser once OR email kaggle-benchmarks@google.com.
#   3. push           - `kaggle benchmarks tasks push` with the canonical
#                        task slug and the kernel.py file location.
#   4. status         - confirms the task is registered post-push.
#   5. (optional) run - when --run <model> is supplied, kicks off a smoke
#                        run against the named Kaggle-hosted model.
#
# Usage:
#   bash scripts/publish_kbench_task.sh                        # dry run + push
#   bash scripts/publish_kbench_task.sh --dry-run              # diagnostics only
#   bash scripts/publish_kbench_task.sh --run claude-opus-4-7  # push + run smoke
#   bash scripts/publish_kbench_task.sh --task my-other-slug   # override slug
#   bash scripts/publish_kbench_task.sh --file path/to/k.py    # override source
#
# Exits non-zero on any failure so it composes cleanly with CI later.

set -euo pipefail

TASK_SLUG="duecare-migrant-worker-safety-benchmark"
TASK_FILE="kaggle/04-kaggle-community-benchmark/kernel.py"
DRY_RUN=0
RUN_MODEL=""

while [[ $# -gt 0 ]]; do
    case "$1" in
        --task)
            TASK_SLUG="$2"
            shift 2
            ;;
        --file)
            TASK_FILE="$2"
            shift 2
            ;;
        --run)
            RUN_MODEL="$2"
            shift 2
            ;;
        --dry-run)
            DRY_RUN=1
            shift
            ;;
        -h|--help)
            sed -n '2,30p' "$0"
            exit 0
            ;;
        *)
            echo "Unknown flag: $1" >&2
            echo "Run with --help for usage." >&2
            exit 2
            ;;
    esac
done

cyan()  { printf "\033[36m%s\033[0m\n" "$*"; }
green() { printf "\033[32m%s\033[0m\n" "$*"; }
red()   { printf "\033[31m%s\033[0m\n" "$*" >&2; }
yellow(){ printf "\033[33m%s\033[0m\n" "$*"; }

# Pick a kaggle CLI binary. Prefer the project venv (matches the version
# we've validated against); fall back to PATH so the script still works
# in cleanroom CI.
KAGGLE_BIN=""
if [[ -x ".venv/Scripts/kaggle.exe" ]]; then
    KAGGLE_BIN=".venv/Scripts/kaggle.exe"
elif [[ -x ".venv/bin/kaggle" ]]; then
    KAGGLE_BIN=".venv/bin/kaggle"
elif command -v kaggle >/dev/null 2>&1; then
    KAGGLE_BIN="$(command -v kaggle)"
else
    red "kaggle CLI not found. Install with: pip install kaggle kaggle-benchmarks"
    exit 1
fi

cyan "[1/4] auth probe ($KAGGLE_BIN)"
if [[ ! -f "$HOME/.kaggle/access_token" && ! -f "$HOME/.kaggle/kaggle.json" ]]; then
    red "No Kaggle credentials. Create one of:"
    red "  ~/.kaggle/access_token  (preferred; KGAT_... token)"
    red "  ~/.kaggle/kaggle.json   (legacy {username,key})"
    exit 1
fi
if ! "$KAGGLE_BIN" benchmarks tasks models >/dev/null 2>&1; then
    red "Auth probe failed: 'kaggle benchmarks tasks models' did not return."
    red "Check that ~/.kaggle/access_token or kaggle.json is readable."
    exit 1
fi
green "  auth probe OK (model catalog reachable)"

cyan "[2/4] task-creator enrollment probe"
LIST_OUT=$("$KAGGLE_BIN" benchmarks tasks list 2>&1) || true
if echo "$LIST_OUT" | grep -q "404\|Not found\|NOT_FOUND"; then
    yellow "  task-creator endpoints are gated (404)."
    yellow "  Action needed (pick one):"
    yellow "    a) Visit https://www.kaggle.com/benchmarks/tasks/new in your"
    yellow "       browser once and click 'Create task'. This may enroll the"
    yellow "       account in the task-creator program."
    yellow "    b) Email kaggle-benchmarks@google.com requesting task-creator"
    yellow "       access for your account."
    if [[ $DRY_RUN -eq 1 ]]; then
        yellow "  --dry-run set; stopping here without push."
        exit 0
    fi
    red "  Cannot push until enrollment is unlocked."
    exit 3
fi
green "  task-creator endpoints reachable"
echo "$LIST_OUT" | head -10

if [[ $DRY_RUN -eq 1 ]]; then
    cyan "--dry-run set; stopping before push."
    exit 0
fi

cyan "[3/4] push $TASK_SLUG  <-  $TASK_FILE"
if [[ ! -f "$TASK_FILE" ]]; then
    red "Source file not found: $TASK_FILE"
    exit 1
fi
"$KAGGLE_BIN" benchmarks tasks push "$TASK_SLUG" -f "$TASK_FILE"
green "  push OK"

cyan "[4/4] status check"
"$KAGGLE_BIN" benchmarks tasks status "$TASK_SLUG" || true

if [[ -n "$RUN_MODEL" ]]; then
    cyan "[bonus] smoke run against model: $RUN_MODEL"
    "$KAGGLE_BIN" benchmarks tasks run "$TASK_SLUG" --model "$RUN_MODEL"
    green "  run enqueued; poll with: $KAGGLE_BIN benchmarks tasks status $TASK_SLUG"
fi

green "done."
