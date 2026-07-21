#!/usr/bin/env python3
# ruff: noqa: E501
"""Regenerate the committed evals-as-CI fixtures deterministically.

The evals gate (``scripts/run_evals_gate.py``) and the GitHub Action
``.github/workflows/duecare-evals.yml`` must run WITHOUT the large, gitignored
report files. This script materializes two small, committed slices from those
sources so CI is self-contained:

Sources (gitignored, large -- present only on a working machine):
    reports/rich_lift/panel.jsonl
        The per-(model, arm, prompt_id, judge) LLM-judge panel. ~23 MB.
    reports/kaggle_publish/prompt_response_showcase/prompt_response_showcase.jsonl
        The public prompt/response showcase (composite/synthetic, no PII). ~13 MB.

Outputs (committed, small, safe -- next to this script):
    panel_sample.jsonl
        gemma4:31b baseline + harness_core rows, all judges, for a deterministic
        seeded sample of prompt_ids. Guarantees >= 150 paired prompts so the
        headline paired lift (harness_core - baseline) is meaningful.
    showcase_sample.jsonl
        A deterministic seeded sample of showcase rows (prompt_text +
        baseline_response + harness_core_response) for the deterministic verify_lift.

Determinism: prompt_ids are ordered by a stable SHA-256 keyed with a fixed SEED,
then the first N are taken. sha256 is stable across runs, machines, and Python
builds, so the same inputs produce byte-identical outputs. No RNG state, no
platform-dependent hashing.

The showcase content is already public composite/synthetic data (see the dataset
DATA_CARD.md); no PII is copied. The panel slice carries only numeric scores and
short arm/judge/prompt_id labels -- no free text at all.

Usage:
    python packages/duecare-llm-kit/tests/fixtures/make_fixtures.py
    python packages/duecare-llm-kit/tests/fixtures/make_fixtures.py --check   # verify only, no write
"""
from __future__ import annotations

import argparse
import hashlib
import json
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
REPO_ROOT = HERE.parents[3]  # fixtures -> tests -> duecare-llm-kit -> packages -> repo root

PANEL_SRC = REPO_ROOT / "reports" / "rich_lift" / "panel.jsonl"
SHOWCASE_SRC = (
    REPO_ROOT
    / "reports"
    / "kaggle_publish"
    / "prompt_response_showcase"
    / "prompt_response_showcase.jsonl"
)

PANEL_OUT = HERE / "panel_sample.jsonl"
SHOWCASE_OUT = HERE / "showcase_sample.jsonl"

# --- Selection parameters (frozen; changing these changes the committed fixtures) ---
SEED = "duecare-evals-ci-20260721"
HEADLINE_MODEL = "gemma4:31b"
PANEL_ARMS = ("baseline", "harness_core")
PANEL_KEEP = ("model", "arm", "prompt_id", "judge", "score_0_100", "components")
# >= 150 paired prompts is the hard requirement. With ~3 judges x 2 arms = 6 rows per
# paired prompt in the real panel, 160 prompts materializes ~960 rows.
PANEL_PROMPTS = 160
SHOWCASE_ROWS = 200
SHOWCASE_KEEP = (
    "prompt_id",
    "category",
    "difficulty",
    "prompt_text",
    "baseline_response",
    "harness_core_response",
)


def _seeded_key(value: str) -> str:
    """Stable, seeded ordering key for a prompt_id -- deterministic across machines."""
    return hashlib.sha256(f"{SEED}:{value}".encode("utf-8")).hexdigest()


def _iter_jsonl(path: Path):
    with path.open("r", encoding="utf-8") as fh:
        for line in fh:
            line = line.strip()
            if line:
                yield json.loads(line)


def _write_jsonl(path: Path, rows: list[dict]) -> None:
    # Explicit \n newlines + ensure_ascii so the committed file is ASCII and byte-stable.
    with path.open("w", encoding="utf-8", newline="\n") as fh:
        for row in rows:
            fh.write(json.dumps(row, ensure_ascii=True, sort_keys=True) + "\n")


def build_panel_rows() -> list[dict]:
    """Materialize the gemma4:31b baseline+harness_core panel slice."""
    by_pid: dict[str, list[dict]] = {}
    arms_by_pid: dict[str, set] = {}
    for rec in _iter_jsonl(PANEL_SRC):
        if rec.get("model") != HEADLINE_MODEL:
            continue
        arm = rec.get("arm")
        pid = rec.get("prompt_id")
        if arm not in PANEL_ARMS or not pid:
            continue
        if not isinstance(rec.get("score_0_100"), (int, float)):
            continue
        by_pid.setdefault(pid, []).append(rec)
        arms_by_pid.setdefault(pid, set()).add(arm)

    paired = [pid for pid, arms in arms_by_pid.items() if set(PANEL_ARMS) <= arms]
    paired.sort(key=_seeded_key)
    chosen = paired[:PANEL_PROMPTS]
    if len(chosen) < 150:
        raise SystemExit(
            f"FAIL: only {len(chosen)} paired gemma4:31b prompts available; need >= 150"
        )

    out: list[dict] = []
    for pid in chosen:
        for rec in by_pid[pid]:
            out.append({k: rec.get(k) for k in PANEL_KEEP})
    # Stable emission order independent of source order.
    out.sort(key=lambda r: (r["prompt_id"], r["arm"], r.get("judge") or ""))
    return out


def build_showcase_rows() -> list[dict]:
    """Materialize a deterministic seeded slice of the prompt/response showcase."""
    rows = list(_iter_jsonl(SHOWCASE_SRC))
    rows.sort(key=lambda r: _seeded_key(str(r.get("prompt_id") or "")))
    chosen = rows[:SHOWCASE_ROWS]
    out = [{k: rec.get(k) for k in SHOWCASE_KEEP} for rec in chosen]
    out.sort(key=lambda r: str(r.get("prompt_id") or ""))
    return out


def _sha256_file(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def _count_paired(panel_rows: list[dict]) -> int:
    pids_by_arm: dict[str, set] = {a: set() for a in PANEL_ARMS}
    for r in panel_rows:
        if r.get("arm") in pids_by_arm:
            pids_by_arm[r["arm"]].add(r.get("prompt_id"))
    return len(set.intersection(*(pids_by_arm[a] for a in PANEL_ARMS)))


def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser(description="Regenerate committed evals-as-CI fixtures.")
    ap.add_argument("--check", action="store_true", help="Build in memory and report counts; do not write.")
    args = ap.parse_args(argv)

    for src in (PANEL_SRC, SHOWCASE_SRC):
        if not src.exists():
            raise SystemExit(
                f"FAIL: source not found: {src}\n"
                "These large reports are gitignored; run this on a machine that has them."
            )

    panel_rows = build_panel_rows()
    showcase_rows = build_showcase_rows()
    paired = _count_paired(panel_rows)

    print(f"panel_sample.jsonl    : {len(panel_rows)} rows, {paired} paired gemma4:31b prompts")
    print(f"showcase_sample.jsonl : {len(showcase_rows)} rows")

    if args.check:
        print("--check: not writing.")
        return 0

    _write_jsonl(PANEL_OUT, panel_rows)
    _write_jsonl(SHOWCASE_OUT, showcase_rows)
    print(f"wrote {PANEL_OUT}  sha256={_sha256_file(PANEL_OUT)[:16]}")
    print(f"wrote {SHOWCASE_OUT}  sha256={_sha256_file(SHOWCASE_OUT)[:16]}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
