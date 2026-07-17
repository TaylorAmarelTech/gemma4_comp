# ruff: noqa: E501
"""Package the enriched cross-model harness-lift leaderboard as a citable Kaggle DATASET.

Reads the real, committed board (apps/duecare-ai.com/app/static/benchmark_leaderboard.json --
the same artifact the public site renders) and emits a clean, machine-readable dataset bundle:
a flat per-model CSV (baseline/harness/lift/normalized_gain + the five A-E component gains),
the full board JSON, a README + Kaggle dataset-metadata.json, and a SHA-bound release manifest.
Aggregated leaderboard only -- no raw grades, no prompts, no PII. Propose-only: stages under
reports/kaggle_publish/; never pushes.

    python scripts/build_cross_model_leaderboard_dataset.py
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
BOARD = ROOT / "apps" / "duecare-ai.com" / "app" / "static" / "benchmark_leaderboard.json"
DEFAULT_OUT = ROOT / "reports" / "kaggle_publish" / "cross_model_leaderboard"
DATASET_ID = "taylorsamarel/duecare-cross-model-harness-leaderboard"
COMP = ("A", "B", "C", "D", "E")
COMP_NAMES = {"A": "indicator", "B": "legal", "C": "refusal", "D": "resources", "E": "privacy"}


def _sha256(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def _flat_rows(board: dict) -> list[dict]:
    rows = []
    for m in board.get("models", []):
        cg = m.get("components_gain", {}) or {}
        row = {
            "rank": m.get("rank"),
            "model": m.get("model"),
            "n_prompts": m.get("n_prompts"),
            "n_observations": m.get("n_observations"),
            "baseline": m.get("baseline"),
            "harness_core": m.get("harness_core"),
            "harnessed": m.get("harnessed"),
            "lift": m.get("lift"),
            "lift_core": m.get("lift_core"),
            "normalized_gain": m.get("normalized_gain"),
            "pairwise_full_vs_core": m.get("pairwise_full_vs_core"),
        }
        for c in COMP:
            row[f"comp_gain_{c}_{COMP_NAMES[c]}"] = cg.get(c)
        rows.append(row)
    return rows


def _csv_bytes(rows: list[dict]) -> bytes:
    if not rows:
        return b""
    buf = io.StringIO()
    w = csv.DictWriter(buf, fieldnames=list(rows[0].keys()))
    w.writeheader()
    w.writerows(rows)
    return buf.getvalue().encode("utf-8")


def _readme(board: dict, rows: list[dict]) -> str:
    judges = ", ".join(board.get("judges", []))
    lines = [
        "# DueCare cross-model harness-lift leaderboard",
        "",
        "A machine-readable, citable leaderboard: how much a thin, model-agnostic legal-grounding",
        "harness (fired indicator rules + retrieved law + deterministic tools, added to the prompt",
        "and nothing else) raises each model on a 0-100 migrant-worker-safety rubric. Every model",
        "answers each adversarial prompt twice (raw, then harness-wrapped); a panel of frontier",
        f"judges ({judges}), each from a different family and never grading its own, scores both",
        "replies. The reported metric is the paired per-prompt lift.",
        "",
        "## Files",
        "- `leaderboard.csv` -- one row per model: baseline / harness_core / harnessed means, raw",
        "  `lift`, ceiling-adjusted `normalized_gain`, and the five A-E component gains.",
        "- `leaderboard.json` -- the full board (per-model stats, per-dimension baseline/full, pairwise).",
        "",
        "## Columns (leaderboard.csv)",
        "`rank` (by raw lift) - `model` - `n_prompts` / `n_observations` - `baseline` / `harness_core`",
        "/ `harnessed` (mean 0-100) - `lift` = harnessed - baseline - `lift_core` = core - baseline -",
        "`normalized_gain` = fraction of remaining headroom (100 - baseline) captured, ceiling-adjusted",
        "so high-baseline models compare fairly with low ones - `comp_gain_A..E` = per-dimension lift",
        "(A indicator, B legal, C refusal, D resources, E privacy).",
        "",
        "## Read it honestly",
        "`normalized_gain` re-ranks the board versus raw `lift`: the model with the largest raw lift",
        "usually just had the most baseline headroom. Sample sizes vary widely across models -- treat",
        "small-n rows as indicative. **These are rubric-scored benchmark results judged by language",
        "models, not anti-trafficking professionals -- benchmark evidence about response quality, not",
        "field-detection or victim-identification claims.**",
        "",
        f"Models: {len(rows)} - judges: {len(board.get('judges', []))} - benchmark: "
        f"`{board.get('benchmark', {}).get('id')}` - git_sha at generation: `{board.get('git_sha', '')[:8]}`.",
        "License: MIT.",
    ]
    return "\n".join(lines) + "\n"


def _metadata(rows: list[dict]) -> dict:
    return {
        "title": "DueCare Cross-Model Harness-Lift Leaderboard",
        "id": DATASET_ID,
        "isPrivate": False,
        "licenses": [{"name": "MIT"}],
        "subtitle": "How much a legal-grounding harness lifts each model on a worker-safety rubric",
        "keywords": ["benchmark", "nlp", "text", "evaluation"],
        "resources": [
            {
                "path": "leaderboard.csv",
                "description": "One row per model: baseline/harness/harnessed means, raw lift, ceiling-adjusted normalized gain, and A-E component gains.",
                "schema": {
                    "fields": [
                        {"name": "rank", "type": "integer", "description": "Rank by raw lift."},
                        {"name": "model", "type": "string", "description": "Model tag."},
                        {"name": "n_prompts", "type": "integer", "description": "Distinct prompts with complete board evidence."},
                        {"name": "baseline", "type": "number", "description": "Mean 0-100 rubric score, raw arm."},
                        {"name": "harnessed", "type": "number", "description": "Mean 0-100 rubric score, full harness arm."},
                        {"name": "lift", "type": "number", "description": "harnessed minus baseline."},
                        {"name": "normalized_gain", "type": "number", "description": "Fraction of remaining headroom (100-baseline) captured; ceiling-adjusted."},
                    ]
                },
            },
            {"path": "leaderboard.json", "description": "Full board: per-model stats, per-dimension baseline/full, pairwise full-vs-core."},
        ],
    }


def build(output_dir: Path, *, board_path: Path = BOARD) -> dict:
    board = json.loads(board_path.read_text(encoding="utf-8"))
    rows = _flat_rows(board)
    if not rows:
        raise RuntimeError(f"no models in {board_path}")
    if output_dir.exists():
        shutil.rmtree(output_dir)
    dataset = output_dir / "dataset"
    dataset.mkdir(parents=True)

    files = {
        "leaderboard.csv": _csv_bytes(rows),
        "leaderboard.json": (json.dumps(board, indent=2, sort_keys=True) + "\n").encode("utf-8"),
        "README.md": _readme(board, rows).encode("utf-8"),
    }
    for name, data in files.items():
        (dataset / name).write_bytes(data)
    artifacts = {name: {"bytes": len(data), "sha256": _sha256(data)} for name, data in files.items()}
    manifest = {
        "dataset_id": DATASET_ID,
        "n_models": len(rows),
        "judges": board.get("judges", []),
        "source_git_sha": board.get("git_sha"),
        "safe_to_publish": True,
        "contains_raw_grades_or_pii": False,
        "artifacts": artifacts,
    }
    (dataset / "release-manifest.json").write_bytes((json.dumps(manifest, indent=2, sort_keys=True) + "\n").encode("utf-8"))
    (dataset / "dataset-metadata.json").write_text(json.dumps(_metadata(rows), indent=2), encoding="utf-8")
    valid_ng = [r["normalized_gain"] for r in rows if r["normalized_gain"] is not None]
    return {"dataset_id": DATASET_ID, "n_models": len(rows), "output_dir": str(output_dir),
            "top_by_lift": rows[0]["model"], "max_norm_gain": max(valid_ng) if valid_ng else None}


def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--output", type=Path, default=DEFAULT_OUT)
    ap.add_argument("--board", type=Path, default=BOARD)
    args = ap.parse_args(argv)
    print(json.dumps(build(args.output, board_path=args.board), indent=2, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
