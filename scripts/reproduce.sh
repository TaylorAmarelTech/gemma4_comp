#!/usr/bin/env bash
# Duecare reproducibility runner.
#
# One command, ~5 minutes, regenerates every measurable claim in the
# writeup + FOR_JUDGES from source. If anything in this script fails,
# a corresponding claim in the submission docs is no longer true and
# the writeup needs to be updated (or the regression fixed).
#
# Usage:
#   bash scripts/reproduce.sh
#
# What it produces:
#   - docs/harness_lift_report.md       (3-dimension lift table)
#   - docs/harness_lift_data.json       (raw numbers)
#   - docs/corpus_coverage.md           (2D coverage matrices)
#   - docs/corpus_coverage.json         (raw counts)
#   - docs/corpus_stats.md              (regenerated stats)
#
# What it verifies:
#   - The harness imports cleanly with the expected counts.
#   - The prompt corpus validates (0 errors / 0 warnings).
#   - Mean lift on the cross-cutting rubric is >= +50 pp.
#   - Per-dimension lifts: jurisdiction >= +80, ILO >= +45,
#     substance-over-form >= +30 pp.
#
# Anything below those thresholds exits non-zero — protects the
# writeup's headline numbers from silent regression.

set -euo pipefail

# ---- Pretty output ----
BOLD=$'\033[1m'; DIM=$'\033[2m'; RESET=$'\033[0m'
GREEN=$'\033[32m'; RED=$'\033[31m'
say()  { printf "\n%s%s%s\n" "$BOLD" "$*" "$RESET"; }
ok()   { printf "%s ✓ %s\n" "$GREEN" "$*${RESET}"; }
err()  { printf "%s ✗ %s\n" "$RED" "$*${RESET}"; exit 1; }

cd "$(dirname "$0")/.."

# ---- 1. Verify install ----
say "[1/5] Verify harness imports + counts..."
python scripts/verify.py || err "verify.py failed — install may be incomplete"

# ---- 2. Validate prompt corpus ----
say "[2/5] Validate prompt corpus..."
python scripts/prompt_corpus.py validate

# ---- 3. Regenerate corpus stats + per-category exports ----
say "[3/5] Regenerate corpus stats + per-category exports..."
python scripts/prompt_corpus.py stats
python scripts/prompt_corpus.py export-by-category > /dev/null

# ---- 4. Coverage matrix ----
say "[4/5] Regenerate coverage matrix..."
python scripts/coverage_matrix.py

# ---- 5. Harness lift report ----
say "[5/5] Run harness lift comparison..."
python scripts/rubric_comparison.py

# ---- 6. Threshold gate ----
say "Verifying lift numbers haven't regressed below documented thresholds..."
python - <<'PYEOF'
import json
import sys
from pathlib import Path

data = json.loads(Path("docs/harness_lift_data.json").read_text(encoding="utf-8"))

overall_lift = data["overall"]["lift_mean_pp"]
per_dim = data["per_dimension"]
jurisdiction = per_dim["1_jurisdiction"]["lift_pp"]
ilo = per_dim["2_ilo_international"]["lift_pp"]
substance = per_dim["3_substance_over_form"]["lift_pp"]

# Thresholds: keep ~10pp below the headline numbers in the writeup,
# so a small future change doesn't trip the gate but a real
# regression does.
THRESHOLDS = {
    "Mean overall lift":       (overall_lift,   50.0),
    "Jurisdiction-specific":   (jurisdiction,   80.0),
    "ILO / international":     (ilo,            45.0),
    "Substance-over-form":     (substance,      30.0),
}

failures = []
for name, (measured, floor) in THRESHOLDS.items():
    status = "OK" if measured >= floor else "FAIL"
    print(f"  [{status:>4}] {name:<28}  +{measured:5.1f} pp  (floor +{floor:.1f} pp)")
    if measured < floor:
        failures.append((name, measured, floor))

if failures:
    print()
    print("Lift regressed below documented thresholds:")
    for name, m, f in failures:
        print(f"  - {name}: +{m} pp < required +{f} pp")
    print()
    print("Either fix the regression or update the writeup numbers.")
    sys.exit(1)
PYEOF

ok "All claims reproduced + thresholds met."
echo
echo "Outputs:"
echo "  - docs/harness_lift_report.md   (mean lift + per-dimension table)"
echo "  - docs/harness_lift_data.json   (raw numbers for downstream tooling)"
echo "  - docs/corpus_coverage.md       (2D coverage heatmaps)"
echo "  - docs/corpus_coverage.json     (raw counts)"
echo "  - docs/corpus_stats.md          (corpus stats summary)"
