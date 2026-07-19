# ruff: noqa: E501
"""Publish the EXHAUSTIVE per-dimension grades (panel_perdim.jsonl) as a versioned Kaggle dataset.

This is the highest-resolution output of the run: one 0-100 score PLUS the five A-E component scores
per (model, prompt, arm, judge), where every dimension got its own judge call. It is the exhaustive
counterpart to the batched grades dataset, and it grows as the seed-shuffled sweep runs to 100% -- so
this is a re-versionable interim snapshot, not a frozen final. Scores + components + hashes only: no
response text, no prompts, no PII (a hard guard refuses any long free-text field). This is the format
you train, test, benchmark, and fine-tune from: pair baseline vs harnessed per prompt, or use the raw
per-(arm,judge,dimension) scores directly. Propose-only: stages under reports/kaggle_publish/.

    python scripts/build_perdim_grades_dataset.py
"""
from __future__ import annotations

import argparse
import csv
import hashlib
import io
import json
import shutil
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
DEFAULT_OUT = ROOT / "reports" / "kaggle_publish" / "perdim_grades"
PANEL = ROOT / "reports" / "rich_lift" / "panel_perdim.jsonl"
COVERAGE = ROOT / "reports" / "rich_lift" / "panel_perdim.coverage.json"
DATASET_ID = "taylorsamarel/duecare-harness-perdim-grades"
COMP = ("A", "B", "C", "D", "E")
MAX_TEXT = 200  # any string field longer than this -> possible response content -> refuse to publish


def _sha256(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def _load(path: Path) -> list[dict]:
    return [json.loads(x) for x in path.read_text(encoding="utf-8").splitlines() if x.strip()]


def _flatten(rows: list[dict]) -> list[dict]:
    out = []
    for r in rows:
        comps = r.get("components") or {}
        row = {"model": r.get("model"), "prompt_id": r.get("prompt_id"), "arm": r.get("arm"),
               "judge": r.get("judge"), "score_0_100": r.get("score_0_100"), "grader": r.get("grader")}
        for c in COMP:
            row[f"comp_{c}"] = comps.get(c)
        out.append(row)
    return out


def _assert_scores_only(rows: list[dict]) -> None:
    for r in rows:
        for k, v in r.items():
            if isinstance(v, str) and len(v) > MAX_TEXT:
                raise RuntimeError(f"field {k!r} looks like free text ({len(v)} chars) -- refusing to publish")


def _csv_bytes(rows: list[dict]) -> bytes:
    if not rows:
        return b""
    buf = io.StringIO()
    w = csv.DictWriter(buf, fieldnames=list(rows[0].keys()))
    w.writeheader()
    w.writerows(rows)
    return buf.getvalue().encode("utf-8")


def _readme(n_rows: int, n_prompts: int, cov: dict | None) -> str:
    exp = (cov or {}).get("baseline_coverage", {}).get("dimension_outputs", {})
    pct = ""
    if exp.get("expected"):
        done = exp.get("complete_in_valid_panel_cells", 0)
        pct = f" (~{100 * (done or 0) / exp['expected']:.1f}% of the full per-dimension scope so far)"
    return "\n".join([
        "# DueCare harness per-dimension grades (exhaustive sweep)",
        "",
        "The highest-resolution output of the DueCare benchmark: for each (model, prompt, arm, judge),",
        "the 0-100 rubric score AND the five A-E component scores, where **every dimension got its own",
        "judge call** (the `perdim` grader). This is the exhaustive counterpart to the batched",
        "`duecare-harness-benchmark-grades` dataset.",
        "",
        f"**Snapshot:** {n_rows:,} rows over {n_prompts:,} prompts{pct}. The seed-shuffled sweep grades",
        "the full 78,719-prompt registry x 3 arms x 3 judges x 5 dimensions and runs to 100%; this dataset",
        "is **re-versioned as it grows**, so a partial snapshot is an unbiased random sample of the full scope.",
        "",
        "## Columns (`perdim_grades.csv`)",
        "`model` - `prompt_id` - `arm` (baseline / harness_core / harness_full) - `judge` - `score_0_100`",
        "- `grader` - `comp_A`..`comp_E` (the five reasoned dimensions: A indicator, B legal, C refusal,",
        "D resources, E privacy).",
        "",
        "## How to use it (train / test / benchmark / fine-tune ANY model)",
        "- **Benchmark / test:** average the judges per (prompt, arm), pair baseline vs harness_core, take",
        "  the per-prompt lift. Works for any model that has rows here.",
        "- **Per-dimension analysis:** the `comp_A..E` columns let you score a model on each safety",
        "  dimension separately, not just the compressed 0-100.",
        "- **Fine-tune:** the prompts where the harness clearly lifts a weak baseline are SFT/DPO pairs",
        "  (chosen = harnessed, rejected = baseline); the response text lives, PII-scrubbed, in the",
        "  separate training corpora. This dataset is the *label* signal.",
        "",
        "**Honest boundary:** judge-scored (LLM panel) rubric measurements over synthetic/composite prompts",
        "-- silver labels, not human-verified gold, and not field detection. Scores + components + hashes",
        "only; no response text, no prompts, no PII. License: MIT.",
    ]) + "\n"


def _metadata() -> dict:
    return {
        "title": "DueCare Harness Per-Dimension Grades",
        "id": DATASET_ID,
        "isPrivate": False,
        "licenses": [{"name": "MIT"}],
        "subtitle": "Exhaustive per-(model,prompt,arm,judge) 0-100 + A-E component safety scores",
        "keywords": ["benchmark", "nlp", "evaluation", "text"],
        "resources": [
            {"path": "perdim_grades.csv", "description": "One row per (model, prompt, arm, judge): 0-100 score + the five A-E component scores (per-dimension judge calls).",
             "schema": {"fields": [
                 {"name": "model", "type": "string", "description": "Graded model tag."},
                 {"name": "prompt_id", "type": "string", "description": "Prompt id."},
                 {"name": "arm", "type": "string", "description": "baseline / harness_core / harness_full."},
                 {"name": "judge", "type": "string", "description": "Judge model (self-family excluded)."},
                 {"name": "score_0_100", "type": "number", "description": "Overall 0-100 rubric score."},
                 {"name": "comp_A", "type": "number", "description": "Dimension A (indicator) 0-100."},
                 {"name": "comp_E", "type": "number", "description": "Dimension E (privacy) 0-100."},
             ]}},
        ],
    }


def build(output_dir: Path, *, panel: Path = PANEL, coverage: Path = COVERAGE) -> dict:
    rows = _load(panel)
    if not rows:
        raise RuntimeError(f"no rows in {panel}")
    flat = _flatten(rows)
    _assert_scores_only(flat)
    n_prompts = len({r["prompt_id"] for r in flat if r["prompt_id"]})
    cov = json.loads(coverage.read_text(encoding="utf-8")) if coverage.exists() else None

    if output_dir.exists():
        shutil.rmtree(output_dir)
    dataset = output_dir / "dataset"
    dataset.mkdir(parents=True)
    files = {
        "perdim_grades.csv": _csv_bytes(flat),
        "README.md": _readme(len(flat), n_prompts, cov).encode("utf-8"),
    }
    for name, data in files.items():
        (dataset / name).write_bytes(data)
    artifacts = {name: {"bytes": len(data), "sha256": _sha256(data)} for name, data in files.items()}
    manifest = {"dataset_id": DATASET_ID, "n_rows": len(flat), "n_prompts": n_prompts,
                "scores_only": True, "contains_response_text_or_pii": False, "artifacts": artifacts}
    (dataset / "release-manifest.json").write_bytes((json.dumps(manifest, indent=2, sort_keys=True) + "\n").encode("utf-8"))
    (dataset / "dataset-metadata.json").write_text(json.dumps(_metadata(), indent=2), encoding="utf-8")
    return {"dataset_id": DATASET_ID, "n_rows": len(flat), "n_prompts": n_prompts, "output_dir": str(output_dir)}


def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--output", type=Path, default=DEFAULT_OUT)
    ap.add_argument("--panel", type=Path, default=PANEL)
    args = ap.parse_args(argv)
    print(json.dumps(build(args.output, panel=args.panel), indent=2, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
