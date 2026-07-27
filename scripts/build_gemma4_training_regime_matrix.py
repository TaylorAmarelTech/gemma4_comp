#!/usr/bin/env python3
"""Build a verified comparison matrix from completed Gemma adapter runs.

The output keeps optimizer curves, preference metrics, locked before/after
responses, adapter hashes, and lineage-defined holdout groups together. It is
designed for notebook publication; it does not turn a narrow format metric or
a model-based judge score into a field-effectiveness claim.
"""

from __future__ import annotations

import argparse
import csv
import hashlib
import json
import shutil
from collections import Counter, defaultdict
from collections.abc import Mapping, Sequence
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[1]
DEFAULT_OUTPUT = ROOT / "reports" / "training_runs" / "gemma4_regime_matrix_v1"
SCHEMA = "duecare.gemma4.training_regime_matrix.v1"
MARKER = ".duecare-gemma4-regime-matrix"


class MatrixError(RuntimeError):
    """Raised when a run or comparison receipt cannot be verified."""


def _sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def _canonical_sha256(value: Any) -> str:
    payload = json.dumps(
        value, ensure_ascii=False, sort_keys=True, separators=(",", ":")
    ).encode("utf-8")
    return hashlib.sha256(payload).hexdigest()


def _read_json(path: Path) -> dict[str, Any]:
    value = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(value, dict):
        raise MatrixError(f"expected a JSON object: {path}")
    return value


def _read_jsonl(path: Path) -> list[dict[str, Any]]:
    rows: list[dict[str, Any]] = []
    for number, line in enumerate(path.read_text(encoding="utf-8").splitlines(), 1):
        if not line.strip():
            continue
        row = json.loads(line)
        if not isinstance(row, dict):
            raise MatrixError(f"expected an object at {path}:{number}")
        rows.append(row)
    return rows


def _write_json(path: Path, value: Any) -> None:
    path.write_text(
        json.dumps(value, ensure_ascii=True, indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
        newline="\n",
    )


def _write_jsonl(path: Path, rows: Sequence[Mapping[str, Any]]) -> None:
    path.write_text(
        "".join(
            json.dumps(row, ensure_ascii=True, sort_keys=True) + "\n" for row in rows
        ),
        encoding="utf-8",
        newline="\n",
    )


def _write_csv(path: Path, rows: Sequence[Mapping[str, Any]]) -> None:
    fields = sorted({str(key) for row in rows for key in row})
    with path.open("w", encoding="utf-8", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=fields)
        writer.writeheader()
        writer.writerows(rows)


def _prepare_output(path: Path, *, force: bool) -> Path:
    path = path.resolve()
    if path.exists():
        if not force:
            raise MatrixError(f"output already exists; use --force: {path}")
        if not (path / MARKER).is_file():
            raise MatrixError(f"refusing to replace unowned output: {path}")
        shutil.rmtree(path)
    path.mkdir(parents=True)
    (path / MARKER).write_text(SCHEMA + "\n", encoding="utf-8")
    return path


def _artifact_path(
    run_dir: Path, manifest: Mapping[str, Any], name: str
) -> Path:
    declaration = (manifest.get("artifacts") or {}).get(name) or {}
    path = run_dir / str(declaration.get("path") or "")
    if not path.is_file() or _sha256(path) != declaration.get("sha256"):
        raise MatrixError(f"run artifact failed verification: {run_dir.name}:{name}")
    return path


def _adapter_hash(manifest: Mapping[str, Any]) -> str:
    files = (manifest.get("artifacts") or {}).get("adapter_files") or {}
    preferred = files.get("adapter/adapter_model.safetensors") or {}
    if preferred.get("sha256"):
        return str(preferred["sha256"])
    hashes = sorted(
        str(declaration.get("sha256"))
        for declaration in files.values()
        if isinstance(declaration, Mapping) and declaration.get("sha256")
    )
    if not hashes:
        raise MatrixError("adapter file hashes are missing")
    return _canonical_sha256(hashes)


def verify_run(run_dir: Path) -> dict[str, Any]:
    run_dir = run_dir.resolve(strict=True)
    manifest_path = run_dir / "run-manifest.json"
    manifest = _read_json(manifest_path)
    if manifest.get("training_completed") is not True:
        raise MatrixError(f"training is incomplete: {run_dir}")
    if manifest.get("adapter_produced") is not True:
        raise MatrixError(f"adapter is missing: {run_dir}")
    metrics_path = _artifact_path(run_dir, manifest, "metrics")
    evaluation_path = _artifact_path(run_dir, manifest, "evaluation")
    _artifact_path(run_dir, manifest, "training_rows")
    _artifact_path(run_dir, manifest, "holdout_rows")
    preference_config = manifest.get("preference_training_config") or {}
    if preference_config.get("enabled"):
        _artifact_path(run_dir, manifest, "preference_rows")
    metrics = _read_json(metrics_path)
    evaluation = _read_jsonl(evaluation_path)
    expected_rows = int((manifest.get("evaluation_config") or {}).get("rows") or 0)
    if len(evaluation) != expected_rows:
        raise MatrixError(
            f"evaluation row mismatch for {run_dir.name}: {len(evaluation)} != {expected_rows}"
        )
    holdout_hashes = list(manifest.get("source_holdout_parent_sha256") or [])
    if len(holdout_hashes) != expected_rows or len(set(holdout_hashes)) != len(
        holdout_hashes
    ):
        raise MatrixError(f"holdout lineage receipt is invalid: {run_dir.name}")
    return {
        "run_dir": run_dir,
        "manifest_path": manifest_path,
        "manifest": manifest,
        "metrics": metrics,
        "evaluation": evaluation,
        "adapter_sha256": _adapter_hash(manifest),
        "holdout_group": _canonical_sha256(holdout_hashes)[:16],
    }


def _overview_row(record: Mapping[str, Any]) -> dict[str, Any]:
    manifest = record["manifest"]
    metrics = record["metrics"]
    supervised = metrics.get("training") or {}
    preference = metrics.get("preference_training") or {}
    evaluation = metrics.get("evaluation") or {}
    config = manifest.get("training_config") or {}
    preference_config = manifest.get("preference_training_config") or {}
    memory = metrics.get("memory") or {}
    return {
        "run": record["run_dir"].name,
        "experiment_id": manifest.get("experiment_id"),
        "model": manifest.get("model"),
        "source_manifest_sha256": manifest.get("source_candidate_manifest_sha256"),
        "holdout_group": record["holdout_group"],
        "holdout_rows": (manifest.get("evaluation_config") or {}).get("rows"),
        "rank": config.get("rank") or manifest.get("adapter_rank"),
        "lora_alpha": config.get("lora_alpha"),
        "lora_dropout": config.get("lora_dropout"),
        "attention_modules": config.get("finetune_attention_modules"),
        "mlp_modules": config.get("finetune_mlp_modules", False),
        "supervised_rows": config.get("rows"),
        "supervised_steps": supervised.get("steps") or config.get("steps"),
        "supervised_learning_rate": config.get("learning_rate"),
        "supervised_scheduler": config.get("lr_scheduler_type", "legacy"),
        "supervised_loss": supervised.get("training_loss"),
        "supervised_runtime_seconds": supervised.get("runtime_seconds"),
        "preference_enabled": bool(preference_config.get("enabled")),
        "preference_rows": preference_config.get("rows", 0),
        "preference_steps": preference.get("steps", 0),
        "preference_learning_rate": preference_config.get("learning_rate"),
        "preference_loss_type": preference.get("loss_type"),
        "preference_beta": preference.get("beta"),
        "preference_label_smoothing": preference.get("label_smoothing"),
        "preference_loss": preference.get("training_loss"),
        "preference_runtime_seconds": preference.get("runtime_seconds", 0),
        "trainable_parameters": supervised.get("trainable_parameters"),
        "total_parameters": supervised.get("total_parameters"),
        "peak_training_memory_bytes": memory.get("peak_training_allocated_bytes"),
        "wall_clock_seconds": metrics.get("wall_clock_seconds"),
        "base_objective_score": (evaluation.get("base_mean") or {}).get(
            "objective_score"
        ),
        "adapted_objective_score": (evaluation.get("adapted_mean") or {}).get(
            "objective_score"
        ),
        "objective_delta": (evaluation.get("delta") or {}).get("objective_score"),
        "narrow_lift": evaluation.get(
            "model_lift_demonstrated_on_locked_grounded_remix_holdout"
        ),
        "adapter_sha256": record["adapter_sha256"],
        "run_manifest_sha256": _sha256(record["manifest_path"]),
    }


def _curve_rows(record: Mapping[str, Any]) -> list[dict[str, Any]]:
    result: list[dict[str, Any]] = []
    for stage, key in (("supervised", "training"), ("preference", "preference_training")):
        for point in (record["metrics"].get(key) or {}).get("log_history") or []:
            if not isinstance(point, Mapping) or "step" not in point:
                continue
            row = {"run": record["run_dir"].name, "stage": stage}
            row.update(
                {
                    str(name): value
                    for name, value in point.items()
                    if isinstance(value, (str, int, float, bool)) or value is None
                }
            )
            result.append(row)
    return result


def _response_rows(record: Mapping[str, Any]) -> list[dict[str, Any]]:
    return [
        {
            "run": record["run_dir"].name,
            "experiment_id": record["manifest"].get("experiment_id"),
            "holdout_group": record["holdout_group"],
            **row,
        }
        for row in record["evaluation"]
    ]


def build_matrix(
    run_dirs: Sequence[Path], output_dir: Path, *, force: bool = False
) -> dict[str, Any]:
    if len(run_dirs) < 2:
        raise MatrixError("at least two completed runs are required")
    output = _prepare_output(output_dir, force=force)
    records = [verify_run(path) for path in run_dirs]
    overview = [_overview_row(record) for record in records]
    curves = [row for record in records for row in _curve_rows(record)]
    responses = [row for record in records for row in _response_rows(record)]
    source_hashes = Counter(str(row["source_manifest_sha256"]) for row in overview)
    groups: dict[str, list[str]] = defaultdict(list)
    for row in overview:
        groups[str(row["holdout_group"])].append(str(row["run"]))
    matched_groups = {
        group: runs for group, runs in sorted(groups.items()) if len(runs) >= 2
    }
    if not matched_groups:
        raise MatrixError("no two runs share an identical lineage-defined holdout")

    overview_path = output / "training-regime-overview.csv"
    curves_path = output / "learning-curve-points.csv"
    response_path = output / "locked-response-comparisons.jsonl"
    _write_csv(overview_path, overview)
    _write_csv(curves_path, curves)
    _write_jsonl(response_path, responses)
    matrix = {
        "schema_version": SCHEMA,
        "run_count": len(records),
        "source_manifest_sha256_counts": dict(source_hashes),
        "matched_holdout_groups": matched_groups,
        "overview": overview,
        "claim_boundary": (
            "Comparisons concern a lineage-locked grounded-remix format task. "
            "They do not demonstrate real-case detection, legal findings, worker "
            "outcomes, or production readiness."
        ),
        "artifacts": {
            "overview": overview_path.name,
            "curves": curves_path.name,
            "responses": response_path.name,
        },
    }
    matrix_path = output / "training-regime-matrix.json"
    _write_json(matrix_path, matrix)
    receipt = {
        "schema_version": SCHEMA,
        "matrix_sha256": _sha256(matrix_path),
        "artifacts": {
            path.name: {"bytes": path.stat().st_size, "sha256": _sha256(path)}
            for path in (overview_path, curves_path, response_path)
        },
    }
    _write_json(output / "matrix-receipt.json", receipt)
    return matrix


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("run_dirs", nargs="+", type=Path)
    parser.add_argument("--output-dir", type=Path, default=DEFAULT_OUTPUT)
    parser.add_argument("--force", action="store_true")
    return parser


def main(argv: Sequence[str] | None = None) -> int:
    args = build_parser().parse_args(argv)
    result = build_matrix(args.run_dirs, args.output_dir, force=args.force)
    print(json.dumps(result, ensure_ascii=False, indent=2, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
