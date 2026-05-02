"""scripts/verify.py — post-install sanity checker.

Runs in <2 seconds. Confirms the harness imports cleanly and the
bundled artifact counts are at-or-above their expected thresholds.
Used by:

  - `make verify`
  - `scripts/install.sh` (final step)
  - `scripts/install.ps1` (final step)
  - `.devcontainer/setup.sh`
  - `.github/workflows/ci.yml` (smoke-test job)

Exits 0 on success, 1 on any failure. Prints a small ASCII table
of measured vs expected counts so failures are obvious.

Honest about what it does NOT verify:
  - Does NOT call Gemma — that requires a model + GPU.
  - Does NOT check the network. The harness is purely local code.
  - Does NOT exercise GREP/RAG/Tools end-to-end against a prompt
    (use `scripts/rubric_comparison.py` for that).
"""
from __future__ import annotations

import importlib
import sys
import traceback
from dataclasses import dataclass


# Per-artifact thresholds. Each is the published headline number
# from `docs/writeup_draft.md` / `FOR_JUDGES.md` / `harness_lift_report.md`
# rounded down (so a small future addition still passes; only
# regressions trip the gate).
@dataclass(frozen=True)
class Check:
    name: str
    module: str
    attr: str
    expected_min: int
    description: str


CHECKS: tuple[Check, ...] = (
    Check("GREP rules",        "duecare.chat.harness", "GREP_RULES",        37,
          "regex rules across 5 categories"),
    Check("RAG corpus",        "duecare.chat.harness", "RAG_CORPUS",        26,
          "documents (ILO conventions, statutes, NGO briefs)"),
    Check("Tools",             "duecare.chat.harness", "_TOOL_DISPATCH",     4,
          "lookup functions (corridor / fee / indicator / NGO)"),
    Check("Example prompts",   "duecare.chat.harness", "EXAMPLE_PROMPTS",  394,
          "prompts in the bundled examples library"),
    Check("5-tier rubrics",    "duecare.chat.harness", "RUBRICS_5TIER",    207,
          "prompts with hand-graded worst..best response examples"),
    Check("Required rubrics",  "duecare.chat.harness", "RUBRICS_REQUIRED",   6,
          "categories of required-element rubrics"),
    Check("Classifier examples","duecare.chat.harness","CLASSIFIER_EXAMPLES",16,
          "pre-built classifier examples (6 with SVG document mockups)"),
)


def _measure(c: Check) -> tuple[bool, int, str | None]:
    """Returns (ok, measured, error)."""
    try:
        mod = importlib.import_module(c.module)
    except Exception as e:  # noqa: BLE001 — we want the full reason
        return False, 0, f"import {c.module} failed: {e}"
    obj = getattr(mod, c.attr, None)
    if obj is None:
        return False, 0, f"{c.module}.{c.attr} not found"
    try:
        n = len(obj)
    except TypeError as e:
        return False, 0, f"len({c.module}.{c.attr}) failed: {e}"
    return n >= c.expected_min, n, None


def main() -> int:
    print("Duecare verify  (gemma4_comp/scripts/verify.py)")
    print()
    rows = []
    failures = []
    for c in CHECKS:
        ok, n, err = _measure(c)
        rows.append((c.name, n, c.expected_min, ok, err, c.description))
        if not ok:
            failures.append((c, n, err))

    name_w = max(len(r[0]) for r in rows)
    n_w = max(len(str(r[1])) for r in rows)
    exp_w = max(len(str(r[2])) for r in rows)
    for name, n, expected, ok, err, desc in rows:
        mark = "  OK  " if ok else " FAIL "
        n_s = str(n).rjust(n_w)
        exp_s = str(expected).rjust(exp_w)
        print(f"  [{mark}]  {name:<{name_w}}  {n_s} >= {exp_s}   {desc}")
        if err:
            print(f"           error: {err}")

    print()
    if failures:
        print(f"FAIL: {len(failures)} check(s) failed.")
        print()
        print("If you just installed and this is the first run, the most")
        print("likely cause is an old chat wheel without the v2 rubric")
        print("system. Reinstall:")
        print()
        print("    pip install --upgrade --force-reinstall duecare-llm-chat")
        print()
        return 1
    print(f"OK: all {len(CHECKS)} checks passed. Harness is ready.")
    return 0


if __name__ == "__main__":
    try:
        sys.exit(main())
    except Exception:  # noqa: BLE001
        traceback.print_exc()
        sys.exit(2)
