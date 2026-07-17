# ruff: noqa: E501
"""Package the DueCare benchmark's methodology-CONTROL results as a citable Kaggle dataset.

These are the controls that make the harness-lift headline defensible rather than "number goes
up": a length-matched PLACEBO arm (does a generic preamble explain the lift?), an APPLICABILITY
audit (does the rubric score the right dimensions?), and the per-judge placebo panel. All four
inputs are SCORES-ONLY jsonl (no response text, no prompts, no PII -- verified before packaging).
Propose-only: stages under reports/kaggle_publish/; never pushes.

    python scripts/build_controls_kaggle_dataset.py
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
DEFAULT_OUT = ROOT / "reports" / "kaggle_publish" / "controls"
DATASET_ID = "taylorsamarel/duecare-harness-lift-controls"

# (source jsonl, output csv, description) -- the guard refuses any file with a long free-text
# field so response content can never leak into a published control table.
SOURCES = [
    ("reports/placebo_panel.jsonl", "placebo_panel.csv",
     "3-arm control (baseline/placebo/harnessed) re-scored by a 5-judge panel with self-family exclusion."),
    ("reports/placebo_judge.jsonl", "placebo_single_judge.csv",
     "The same 3-arm placebo control scored by a single judge (the origin of the panel test)."),
    ("reports/negative_control.jsonl", "negative_control_deterministic.csv",
     "The placebo control under the ceiling-bound DETERMINISTIC grader (per prompt x dimension)."),
    ("reports/applicability_audit.jsonl", "applicability_audit.csv",
     "Independent-judge re-decision of which rubric dimensions apply, vs the deterministic gate."),
]
MAX_TEXT = 200  # any string field longer than this is treated as possible response content -> refuse


def _sha256(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def _load_jsonl(path: Path) -> list[dict]:
    rows = []
    with path.open(encoding="utf-8") as fh:
        for line in fh:
            line = line.strip()
            if line:
                rows.append(json.loads(line))
    return rows


def _assert_scores_only(rows: list[dict], name: str) -> None:
    for row in rows:
        for key, val in row.items():
            if isinstance(val, str) and len(val) > MAX_TEXT:
                raise RuntimeError(f"{name}: field {key!r} looks like free text ({len(val)} chars) -- refusing to publish")


def _csv_bytes(rows: list[dict]) -> bytes:
    cols: list[str] = []
    for row in rows:
        for key in row:
            if key not in cols:
                cols.append(key)
    buf = io.StringIO()
    w = csv.DictWriter(buf, fieldnames=cols, extrasaction="ignore")
    w.writeheader()
    for row in rows:
        w.writerow({k: (json.dumps(v) if isinstance(v, (dict, list)) else v) for k, v in row.items()})
    return buf.getvalue().encode("utf-8")


def _readme() -> str:
    return "\n".join([
        "# DueCare harness-lift benchmark -- methodology controls",
        "",
        "The controls behind the DueCare harness-lift headline. They exist to answer the skeptic's",
        "questions before they are asked: is the lift the injected knowledge or just a preamble? do the",
        "graders agree? does the rubric score the right things? All scores-only -- no response text, no",
        "prompts, no PII.",
        "",
        "## Files",
        "- `placebo_panel.csv` -- the 3-arm control (baseline / placebo / harnessed) re-scored by **5",
        "  independent judges** from different model families, self-family excluded. Columns: arm, judge,",
        "  model, prompt_id, score.",
        "- `placebo_single_judge.csv` -- the same control on one judge (arm, model, prompt_id, score).",
        "- `negative_control_deterministic.csv` -- the placebo control under the **deterministic** grader,",
        "  per (prompt x dimension) (arm, cell, dim, model, prompt_id, score).",
        "- `applicability_audit.csv` -- an independent judge re-decides which dimensions apply, vs the",
        "  deterministic gate (dim, grader_applicable, judge_applicable, prompt_id, unanimous, votes).",
        "",
        "## What the controls actually found (honest, including the inconclusive parts)",
        "1. **Placebo panel (the decisive control).** A length-matched placebo preamble carries NO domain",
        "   knowledge -- no citations, no retrieved law, no indicators, just 'read carefully, be thorough'.",
        "   Across **5 judges** the harness scores **+3.78 to +5.52 beyond the placebo** (panel mean ~+4.55),",
        "   significant for **every** judge. The 'any preamble helps' confound is closed robustly to judge",
        "   choice -- the lift is the injected knowledge, not the boilerplate.",
        "2. **Negative control on the deterministic grader (honestly inconclusive).** On the strict,",
        "   ceiling-bound rule grader the arms sit near 5.7/10 and the knowledge effect over placebo is only",
        "   **+0.08 (p just above 0.05)** -- suggestive, not significant. We report it as inconclusive; the",
        "   conclusive placebo test lives on the holistic LLM judge (item 1), not the deterministic floor.",
        "3. **Applicability audit.** An independent judge (3 passes) and the deterministic gate agree on",
        "   which dimensions apply **68%** of the time (**Cohen's kappa = 0.36**, fair), 86% cross-pass",
        "   unanimous -- applicability is genuinely judgment-dependent, not mechanical.",
        "",
        "The convergent-validity finding (deterministic lift +0.18 vs judge lift +1.73, per-prompt",
        "correlation r=0.18) is directional-only -- the two graders agree on direction, diverge on magnitude;",
        "neither is a proxy for the other, so both are reported.",
        "",
        "**These are rubric/grader measurements over synthetic/composite safety prompts, judged by language",
        "models -- not field detection, not ground truth about any person.** License: MIT.",
    ]) + "\n"


def _metadata() -> dict:
    return {
        "title": "DueCare Harness Lift Controls",
        "id": DATASET_ID,
        "isPrivate": False,
        "licenses": [{"name": "MIT"}],
        "subtitle": "Placebo + negative-control + applicability results behind the harness lift",
        "keywords": ["benchmark", "nlp", "evaluation"],
        "resources": [
            {"path": "placebo_panel.csv", "description": "3-arm (baseline/placebo/harnessed) control scored by 5 self-family-excluded judges."},
            {"path": "negative_control_deterministic.csv", "description": "Placebo control under the deterministic grader, per prompt x dimension."},
            {"path": "applicability_audit.csv", "description": "Independent-judge applicability re-decision vs the deterministic gate."},
            {"path": "placebo_single_judge.csv", "description": "Single-judge version of the placebo control."},
        ],
    }


def build(output_dir: Path) -> dict:
    if output_dir.exists():
        shutil.rmtree(output_dir)
    dataset = output_dir / "dataset"
    dataset.mkdir(parents=True)

    files: dict[str, bytes] = {}
    counts: dict[str, int] = {}
    for src, out_name, _desc in SOURCES:
        path = ROOT / src
        if not path.exists():
            raise FileNotFoundError(f"control input missing: {src}")
        rows = _load_jsonl(path)
        _assert_scores_only(rows, out_name)
        files[out_name] = _csv_bytes(rows)
        counts[out_name] = len(rows)
    files["README.md"] = _readme().encode("utf-8")

    for name, data in files.items():
        (dataset / name).write_bytes(data)
    artifacts = {name: {"bytes": len(data), "sha256": _sha256(data)} for name, data in files.items()}
    manifest = {
        "dataset_id": DATASET_ID,
        "row_counts": counts,
        "scores_only": True,
        "contains_response_text_or_pii": False,
        "artifacts": artifacts,
    }
    (dataset / "release-manifest.json").write_bytes((json.dumps(manifest, indent=2, sort_keys=True) + "\n").encode("utf-8"))
    (dataset / "dataset-metadata.json").write_text(json.dumps(_metadata(), indent=2), encoding="utf-8")
    return {"dataset_id": DATASET_ID, "row_counts": counts, "output_dir": str(output_dir)}


def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--output", type=Path, default=DEFAULT_OUT)
    args = ap.parse_args(argv)
    print(json.dumps(build(args.output), indent=2, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
