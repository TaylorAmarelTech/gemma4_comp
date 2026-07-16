#!/usr/bin/env python3
"""Package grounded Gemma 4 training regimes and safety evidence for Kaggle.

The package contains multiple Low-Rank Adaptation experiments, an optional
preference-optimization stage, relative adapter weights, exact manifests,
before-and-after generations, deterministic harness ablations, recorded
benchmark failures, and blinded judge studies. It contains no base Gemma
weights and makes no production, legal-quality, or real-world lift claim.
"""

from __future__ import annotations

import argparse
import csv
import hashlib
import json
import re
import shutil
import time
from collections.abc import Sequence
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[1]
DEFAULT_RUNS = (
    ROOT / "reports" / "training_runs" / "gemma4_e2b_grounded_adapter_v3_short",
    ROOT / "reports" / "training_runs" / "gemma4_e2b_grounded_adapter_v3",
    ROOT / "reports" / "training_runs" / "gemma4_e2b_regime_rank4_sft_v1",
    ROOT / "reports" / "training_runs" / "gemma4_e2b_regime_rank4_robust_dpo_v1",
)
DEFAULT_EVIDENCE_RUN = (
    ROOT / "reports" / "training_runs" / "gemma4_e2b_grounded_adapter_v3"
)
DEFAULT_REGIME_MATRIX = (
    ROOT / "reports" / "training_runs" / "gemma4_regime_matrix_v1"
)
DEFAULT_OUTPUT = (
    ROOT / "reports" / "kaggle_publish" / "gemma4_adapter_study_collection_v2"
)
DEFAULT_CURRICULUM = (
    ROOT
    / "reports"
    / "response_preference_candidates"
    / "measured_review_curriculum_200k_v2"
)
DATASET_ID = "taylorsamarel/duecare-gemma4-adapter-learning-study"
TITLE = "DueCare Gemma 4 Adapter Learning Study"
SCHEMA = "duecare.kaggle.gemma4_adapter_study.v5"
MARKER = ".duecare-gemma4-kaggle-collection"
TEXT_SUFFIXES = {".json", ".jsonl", ".md", ".jinja", ".csv", ".txt"}
PRIVATE_PATH = re.compile(
    r"(?i)(?:[A-Z]:[/\\]Users[/\\][^/\\\s]+|/home/[^/\s]+/|"
    r"(?:^|[/\\])(?:AppData|OneDrive)(?:[/\\]|$))"
)
SECRET = re.compile(
    r"(?i)(?:AKIA[0-9A-Z]{16}|gh[pousr]_[A-Za-z0-9_]{20,}|"
    r"sk-(?:proj-)?[A-Za-z0-9_-]{20,}|hf_[A-Za-z0-9]{20,}|"
    r"AIza[0-9A-Za-z_-]{35}|-----BEGIN(?: RSA| EC| OPENSSH)? PRIVATE KEY-----)"
)


class PackageError(RuntimeError):
    """Raised when training evidence cannot be safely packaged."""


def _sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def _canonical_sha256(value: Any) -> str:
    return hashlib.sha256(
        json.dumps(value, ensure_ascii=False, sort_keys=True, separators=(",", ":")).encode(
            "utf-8"
        )
    ).hexdigest()


def _read_json(path: Path) -> dict[str, Any]:
    value = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(value, dict):
        raise PackageError(f"expected a JSON object: {path}")
    return value


def _read_jsonl(path: Path) -> list[dict[str, Any]]:
    rows: list[dict[str, Any]] = []
    for line_number, line in enumerate(path.read_text(encoding="utf-8").splitlines(), 1):
        if not line.strip():
            continue
        value = json.loads(line)
        if not isinstance(value, dict):
            raise PackageError(f"expected an object at {path}:{line_number}")
        rows.append(value)
    return rows


def _write_json(path: Path, value: Any) -> None:
    path.write_text(
        json.dumps(value, ensure_ascii=True, indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
        newline="\n",
    )


def _write_text(path: Path, value: str) -> None:
    path.write_text(value.strip() + "\n", encoding="utf-8", newline="\n")


def _prepare_output(path: Path, *, force: bool) -> Path:
    path = path.resolve()
    if path.exists():
        if not force:
            raise PackageError(f"output already exists; use --force: {path}")
        if not (path / MARKER).is_file():
            raise PackageError(f"refusing to replace unowned output: {path}")
        shutil.rmtree(path)
    path.mkdir(parents=True)
    (path / MARKER).write_text(SCHEMA + "\n", encoding="utf-8")
    return path


def _verify_run(run_dir: Path) -> tuple[dict[str, Any], dict[str, Any]]:
    manifest_path = run_dir / "run-manifest.json"
    manifest = _read_json(manifest_path)
    if manifest.get("adapter_produced") is not True or manifest.get(
        "training_completed"
    ) is not True:
        raise PackageError(f"run is incomplete: {run_dir}")
    artifacts = manifest.get("artifacts") or {}
    for name in ("training_rows", "holdout_rows", "evaluation", "metrics"):
        declaration = artifacts.get(name) or {}
        path = run_dir / str(declaration.get("path") or "")
        if not path.is_file() or _sha256(path) != declaration.get("sha256"):
            raise PackageError(f"run artifact failed verification: {run_dir.name}:{name}")
    preference_declaration = artifacts.get("preference_rows") or {}
    preference_enabled = bool(
        (manifest.get("preference_training_config") or {}).get("enabled")
    )
    if preference_enabled:
        preference_path = run_dir / str(preference_declaration.get("path") or "")
        if not preference_path.is_file() or _sha256(
            preference_path
        ) != preference_declaration.get("sha256"):
            raise PackageError(
                f"run preference artifact failed verification: {run_dir.name}"
            )
    for relative, declaration in (artifacts.get("adapter_files") or {}).items():
        path = run_dir / relative
        if not path.is_file() or _sha256(path) != declaration.get("sha256"):
            raise PackageError(f"adapter artifact failed verification: {relative}")
    data_policy = manifest.get("data_policy") or {}
    if data_policy.get("free_standing_fictional_generation") is not False:
        raise PackageError(f"run does not prohibit free-standing fiction: {run_dir}")
    if data_policy.get("parent_hash_required") is not True:
        raise PackageError(f"run does not require parent hashes: {run_dir}")
    if data_policy.get("split_inherited_from_parent") is not True:
        raise PackageError(f"run does not inherit its split from parents: {run_dir}")
    train_path = run_dir / artifacts["training_rows"]["path"]
    holdout_path = run_dir / artifacts["holdout_rows"]["path"]
    train_rows = _read_jsonl(train_path)
    holdout_rows = _read_jsonl(holdout_path)
    for lane, rows in (("train", train_rows), ("holdout", holdout_rows)):
        if not rows or any(
            row.get("grounded_remix") is not True
            or row.get("synthetic_kind") != "deterministic_source_grounded_remix"
            or not row.get("source_row_sha256")
            or not row.get("source_parent_row_sha256")
            or not row.get("source_lineage_family_id")
            for row in rows
        ):
            raise PackageError(f"{lane} rows are not fully grounded and traceable: {run_dir}")
    if preference_enabled:
        preference_rows = _read_jsonl(
            run_dir / str(preference_declaration["path"])
        )
        if not preference_rows or any(
            row.get("grounded_remix") is not True
            or row.get("synthetic_kind")
            != "deterministic_source_grounded_preference_remix"
            or not row.get("source_row_sha256")
            or not row.get("source_lineage_family_id")
            for row in preference_rows
        ):
            raise PackageError(
                f"preference rows are not fully grounded and traceable: {run_dir}"
            )
    train_parents = {str(row["source_lineage_family_id"]) for row in train_rows}
    holdout_parents = {str(row["source_lineage_family_id"]) for row in holdout_rows}
    overlap = train_parents & holdout_parents
    if overlap:
        raise PackageError(f"training and holdout parents overlap in {run_dir}: {len(overlap)}")
    metrics = _read_json(run_dir / artifacts["metrics"]["path"])
    return manifest, metrics


def _copy_run(run_dir: Path, dataset: Path, label: str) -> None:
    destination = dataset / "runs" / label
    destination.mkdir(parents=True)
    manifest = _read_json(run_dir / "run-manifest.json")
    artifacts = manifest["artifacts"]
    for name in (
        "run-manifest.json",
        artifacts["training_rows"]["path"],
        artifacts["holdout_rows"]["path"],
        artifacts["evaluation"]["path"],
        artifacts["metrics"]["path"],
    ):
        shutil.copy2(run_dir / name, destination / Path(name).name)
    preference = artifacts.get("preference_rows") or {}
    if preference.get("path"):
        shutil.copy2(
            run_dir / str(preference["path"]),
            destination / Path(str(preference["path"])).name,
        )
    adapter_destination = destination / "adapter"
    adapter_destination.mkdir()
    for name in (
        "adapter_config.json",
        "adapter_model.safetensors",
        "chat_template.jinja",
        "processor_config.json",
        "tokenizer_config.json",
    ):
        source = run_dir / "adapter" / name
        if source.is_file():
            shutil.copy2(source, adapter_destination / name)


def _copy_four_arm(run_dir: Path, dataset: Path) -> dict[str, Any]:
    source = run_dir / "four_arm_study"
    manifest = _read_json(source / "four-arm-manifest.json")
    for name, declaration in (manifest.get("artifacts") or {}).items():
        path = source / name
        if not path.is_file() or _sha256(path) != declaration.get("sha256"):
            raise PackageError(f"four-arm artifact failed verification: {name}")
    destination = dataset / "four-arm-study"
    destination.mkdir()
    for name in (
        "four-arm-manifest.json",
        "four-arm-summary.json",
        "four-arm-evaluation.jsonl",
        "recorded-egregious-examples.jsonl",
    ):
        shutil.copy2(source / name, destination / name)
    return manifest


def _copy_frontier_judge(run_dir: Path, dataset: Path) -> dict[str, Any]:
    source = run_dir / "four_arm_study" / "frontier_judge_study"
    manifest = _read_json(source / "judge-manifest.json")
    summary = _read_json(source / "frontier-judge-summary.json")
    if summary.get("complete") is not True:
        raise PackageError("frontier judge study is incomplete")
    if summary.get("same_judge_before_and_after") is not True:
        raise PackageError("frontier judge changed inside the comparable study")
    if summary.get("both_presentation_orders") is not True:
        raise PackageError("frontier judge study lacks both presentation orders")
    for name, declaration in (manifest.get("artifacts") or {}).items():
        path = source / name
        if not path.is_file() or _sha256(path) != declaration.get("sha256"):
            raise PackageError(f"frontier judge artifact failed verification: {name}")
    verdicts = _read_jsonl(source / "judge-verdicts.jsonl")
    latest = {str(row.get("request_id")): row for row in verdicts}
    if len(latest) != summary.get("requested_verdicts"):
        raise PackageError("frontier judge checkpoint does not cover every request")
    if any(
        row.get("valid") is not True or row.get("training_eligible") is not False
        for row in latest.values()
    ):
        raise PackageError("frontier judge verdicts are invalid or training-eligible")
    destination = dataset / "frontier-judge-study"
    destination.mkdir()
    for name in (
        "judge-manifest.json",
        "frontier-judge-summary.json",
        "judge-context.md",
        "judge-rubric.md",
        "judge-requests.jsonl",
        "judge-verdicts.jsonl",
        "judge-model-selection.json",
    ):
        path = source / name
        if path.is_file():
            shutil.copy2(path, destination / name)
    return manifest


def _copy_recorded_safety_judge(run_dir: Path, dataset: Path) -> dict[str, Any]:
    source = (
        run_dir
        / "four_arm_study"
        / "recorded_harmful_request_judge_study"
    )
    manifest = _read_json(source / "judge-manifest.json")
    summary = _read_json(source / "recorded-harmful-request-summary.json")
    if summary.get("complete") is not True:
        raise PackageError("recorded harmful-request judge study is incomplete")
    if summary.get("same_judge_for_all_pairs") is not True:
        raise PackageError("recorded harmful-request judge changed inside the study")
    if summary.get("both_presentation_orders") is not True:
        raise PackageError("recorded harmful-request study lacks both orders")
    if summary.get("training_eligible") is not False:
        raise PackageError("recorded harmful-request verdicts became training-eligible")
    for name, declaration in (manifest.get("artifacts") or {}).items():
        path = source / name
        if not path.is_file() or _sha256(path) != declaration.get("sha256"):
            raise PackageError(f"recorded safety judge artifact failed: {name}")
    destination = dataset / "recorded-harmful-request-judge-study"
    destination.mkdir()
    for name in (
        "judge-manifest.json",
        "recorded-harmful-request-summary.json",
        "judge-context.md",
        "judge-rubric.md",
        "judge-requests.jsonl",
        "judge-verdicts.jsonl",
        "judge-model-selection.json",
    ):
        path = source / name
        if path.is_file():
            shutil.copy2(path, destination / name)
    return manifest


def _copy_system_evidence_receipt(run_dir: Path, dataset: Path) -> dict[str, Any]:
    source = run_dir / "system-evidence-receipt.json"
    receipt = _read_json(source)
    declared_sha = receipt.get("receipt_payload_sha256")
    payload = {
        key: value for key, value in receipt.items() if key != "receipt_payload_sha256"
    }
    if not declared_sha or _canonical_sha256(payload) != declared_sha:
        raise PackageError("system evidence receipt payload hash is invalid")
    if receipt.get("training_eligible") is not False:
        raise PackageError("system benchmark evidence became training-eligible")
    not_measured = set(receipt.get("not_measured") or [])
    if not {
        "victim identification accuracy",
        "real-world field detection effectiveness",
    }.issubset(not_measured):
        raise PackageError("system evidence receipt lost its field-effectiveness boundary")
    for declaration in (receipt.get("source_files") or {}).values():
        relative = str(declaration.get("path") or "")
        path = ROOT / relative
        if not path.is_file() or _sha256(path) != declaration.get("sha256"):
            raise PackageError(f"system evidence source failed verification: {relative}")
    destination = dataset / "system-evidence"
    destination.mkdir()
    shutil.copy2(source, destination / source.name)
    return receipt


def _copy_curriculum_receipt(
    curriculum_dir: Path, run_manifest: dict[str, Any], dataset: Path
) -> dict[str, Any]:
    source = curriculum_dir.resolve(strict=True)
    manifest_path = source / "candidate-manifest.json"
    expected = run_manifest.get("source_candidate_manifest_sha256")
    if not expected or _sha256(manifest_path) != expected:
        raise PackageError("source curriculum manifest does not match adapter run")
    manifest = _read_json(manifest_path)
    audit_declaration = manifest.get("quality_audit") or {}
    audit_path = source / str(audit_declaration.get("path") or "")
    if not audit_path.is_file() or _sha256(audit_path) != audit_declaration.get(
        "sha256"
    ):
        raise PackageError("source curriculum quality audit failed verification")
    summary = _read_json(source / "build-summary.json")
    if summary.get("quality_audit_clean") is not True:
        raise PackageError("source curriculum receipt is not clean")
    destination = dataset / "source-curriculum"
    destination.mkdir()
    for name in ("candidate-manifest.json", "build-summary.json", "quality-audit.json"):
        shutil.copy2(source / name, destination / name)
    return summary


def _copy_regime_matrix(source_dir: Path, dataset: Path) -> dict[str, Any]:
    source = source_dir.resolve(strict=True)
    receipt = _read_json(source / "matrix-receipt.json")
    matrix_path = source / "training-regime-matrix.json"
    if not matrix_path.is_file() or _sha256(matrix_path) != receipt.get(
        "matrix_sha256"
    ):
        raise PackageError("training regime matrix failed verification")
    declarations = receipt.get("artifacts") or {}
    for name, declaration in declarations.items():
        path = source / name
        if not path.is_file() or _sha256(path) != declaration.get("sha256"):
            raise PackageError(f"training regime artifact failed verification: {name}")
    destination = dataset / "training-regime-study"
    destination.mkdir()
    for path in (
        matrix_path,
        source / "matrix-receipt.json",
        *(source / name for name in declarations),
    ):
        shutil.copy2(path, destination / path.name)
    return _read_json(matrix_path)


def _artifact_index(root: Path, *, exclude: set[str] | None = None) -> dict[str, Any]:
    excluded = exclude or set()
    return {
        path.relative_to(root).as_posix(): {
            "bytes": path.stat().st_size,
            "sha256": _sha256(path),
        }
        for path in sorted(root.rglob("*"))
        if path.is_file() and path.relative_to(root).as_posix() not in excluded
    }


def _privacy_scan(dataset: Path) -> dict[str, Any]:
    findings: list[dict[str, str]] = []
    for path in sorted(dataset.rglob("*")):
        if not path.is_file() or path.suffix.lower() not in TEXT_SUFFIXES:
            continue
        text = path.read_text(encoding="utf-8", errors="replace")
        if PRIVATE_PATH.search(text):
            findings.append(
                {"path": path.relative_to(dataset).as_posix(), "category": "private_path"}
            )
        if SECRET.search(text):
            findings.append(
                {"path": path.relative_to(dataset).as_posix(), "category": "credential"}
            )
    return {"clean": not findings, "finding_count": len(findings), "findings": findings}


def resolve_run_directories(run_dirs: Sequence[Path]) -> tuple[list[Path], list[str]]:
    """Split requested run directories into existing runs and skipped names.

    Default invocations may name future runs that have not happened yet; those
    are skipped with a recorded name instead of failing the whole packaging,
    while the caller still enforces the minimum completed-run count.
    """
    resolved: list[Path] = []
    skipped: list[str] = []
    for raw in run_dirs:
        candidate = raw.resolve()
        if candidate.is_dir():
            resolved.append(candidate)
        else:
            skipped.append(candidate.name)
    return resolved, skipped


def build_collection(
    run_dirs: Sequence[Path],
    output_root: Path,
    *,
    evidence_run: Path = DEFAULT_EVIDENCE_RUN,
    regime_matrix: Path = DEFAULT_REGIME_MATRIX,
    force: bool,
) -> dict[str, Any]:
    resolved_runs, skipped_missing_runs = resolve_run_directories(run_dirs)
    if len(resolved_runs) < 2:
        raise PackageError(
            "at least two completed runs are required for a learning study; "
            f"resolved {len(resolved_runs)} and skipped missing "
            f"{skipped_missing_runs or ['none']}"
        )
    output_root = _prepare_output(output_root, force=force)
    dataset = output_root / "dataset"
    dataset.mkdir()
    shutil.copy2(
        ROOT / "configs" / "duecare" / "model_fallbacks.json",
        dataset / "model-fallback-registry.json",
    )
    run_records: list[dict[str, Any]] = []
    verified: list[tuple[Path, dict[str, Any], dict[str, Any]]] = []
    for index, run_dir in enumerate(resolved_runs, 1):
        manifest, metrics = _verify_run(run_dir)
        label = f"run-{index:02d}"
        _copy_run(run_dir, dataset, label)
        evaluation = metrics.get("evaluation") or {}
        training_config = manifest.get("training_config") or {}
        preference_config = manifest.get("preference_training_config") or {}
        preference_metrics = metrics.get("preference_training") or {}
        run_records.append(
            {
                "run": label,
                "experiment_id": manifest.get("experiment_id"),
                "steps": metrics["training"]["steps"],
                "training_loss": metrics["training"]["training_loss"],
                "train_runtime_seconds": metrics["training"]["runtime_seconds"],
                "wall_clock_seconds": metrics["wall_clock_seconds"],
                "peak_graphics_memory_bytes": metrics["memory"][
                    "peak_training_allocated_bytes"
                ],
                "trainable_parameters": metrics["training"]["trainable_parameters"],
                "adapter_rank": training_config.get("rank")
                or manifest.get("adapter_rank"),
                "supervised_scheduler": training_config.get("lr_scheduler_type"),
                "supervised_learning_rate": training_config.get("learning_rate"),
                "preference_training": bool(preference_config.get("enabled")),
                "preference_steps": preference_metrics.get("steps", 0),
                "preference_loss": preference_metrics.get("training_loss"),
                "preference_loss_type": preference_metrics.get("loss_type"),
                "preference_runtime_seconds": preference_metrics.get(
                    "runtime_seconds", 0
                ),
                "heldout_rows": evaluation.get("rows"),
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
                "grounded_remix": True,
                "free_standing_fictional_generation": False,
                "run_manifest_sha256": _sha256(run_dir / "run-manifest.json"),
            }
        )
        verified.append((run_dir, manifest, metrics))
    four_arm = _copy_four_arm(verified[-1][0], dataset)
    frontier_judge = _copy_frontier_judge(verified[-1][0], dataset)
    evidence_source = evidence_run.resolve(strict=True)
    recorded_safety_judge = _copy_recorded_safety_judge(evidence_source, dataset)
    system_evidence = _copy_system_evidence_receipt(evidence_source, dataset)
    if regime_matrix.resolve().is_dir():
        regime_receipt = _copy_regime_matrix(regime_matrix, dataset)
    else:
        regime_receipt = {
            "present": False,
            "note": (
                "regime-matrix run directory was not present at build time; "
                "the collection packages completed runs only"
            ),
        }
    curriculum_receipt = _copy_curriculum_receipt(
        DEFAULT_CURRICULUM, verified[-1][1], dataset
    )

    with (dataset / "run-overview.csv").open(
        "w", encoding="utf-8", newline=""
    ) as handle:
        writer = csv.DictWriter(handle, fieldnames=list(run_records[0]))
        writer.writeheader()
        writer.writerows(run_records)
    _write_json(dataset / "preview.json", run_records)

    _write_text(
        dataset / "README.md",
        """
# DueCare Gemma 4 Adapter Learning Study

## Start here

1. Open the [learning-curve and optimization notebook](https://www.kaggle.com/code/taylorsamarel/duecare-gemma4-learning-curves)
   for loss, learning-rate, gradient-norm, memory, throughput, and transfer
   graphics.
2. Open the [four-arm before/after notebook](https://www.kaggle.com/code/taylorsamarel/duecare-gemma4-four-arm-before-after)
   for base and trained Gemma, each with and without the deterministic harness,
   plus recorded high-severity benchmark failures and their source hashes.
3. Open the [Tensor Processing Unit training lab](https://www.kaggle.com/code/taylorsamarel/duecare-gemma-4-tpu-lora-training-lab)
   for the quota-conscious distributed-training continuation.
4. Open the [lineage and training-receipt audit](https://www.kaggle.com/code/taylorsamarel/duecare-grounded-lineage-and-training-receipts)
   to see why 207,680 rows are not 207,680 independent source families.
5. Open the [frontier-judge measurement audit](https://www.kaggle.com/code/taylorsamarel/duecare-frontier-judge-measurement-audit)
   for frozen-context hashes, blinded presentation orders, confidence, and
   order-effect diagnostics.
6. Open the [end-to-end evidence-to-triage system showcase](https://www.kaggle.com/code/taylorsamarel/duecare-training-publication-toolchain)
   to connect the source corpus, broader harness evidence, adapter, recorded
   harmful-request study, judge audit, loading tools, and bounded real-world
   claim ladder in one place.

This public Kaggle hackathon artifact contains multiple real local Gemma 4
training regimes: short and longer supervised fine-tuning controls plus a
matched robust preference-optimization continuation. It includes relative
adapter weights, exact loss and learning-rate logs, preference reward
diagnostics, before-and-after generations, frozen judging, and deterministic
harness ablations. Every training, preference, and holdout row is a
deterministic remix of an approved DueCare prompt and response. The package
carries parent hashes and contains no free-standing fictional cases.

On the recorded harmful-request lane, the same frozen judge preferred all six
DueCare harness responses over the corresponding high-severity Gemma failures
in both presentation orders. This measures safer harmful-request handling on a
recorded benchmark. It does not measure victim identification, prevalence, a
legal finding, or field detection effectiveness.

The package also contains a machine-readable receipt over an earlier 911-pair
Gemma 4 harness evaluation and a 140-pair adversarial study. Those studies
measure trafficking-safety response quality on synthetic/composite prompts,
not real-case detection. Their raw source-checkpoint hashes are preserved so
the system-level notebook can show the wider evidence without silently turning
benchmark scores into field claims.

**Low-Rank Adaptation** is a parameter-efficient method that trains a small
set of added weights instead of updating the whole model. A **graphics
processing unit** is the NVIDIA accelerator used for these runs. The base Gemma
weights are not redistributed here.

The strongest honest finding is whatever the run-bound artifacts demonstrate
on a small lineage-separated grounded-remix holdout. This is a working
training pipeline and learning study, not evidence of legal quality or
real-world effectiveness. The deterministic objective and any frontier-model
judgment are reported as separate instruments.
""",
    )
    _write_text(
        dataset / "LOADING.md",
        """
# Loading, verification, and cleanup

## Inspect tables and metrics

```python
import json
from pathlib import Path

root = Path("/kaggle/input/duecare-gemma4-adapter-learning-study")
overview = root / "run-overview.csv"
latest_run = sorted((root / "runs").glob("run-*"))[-1]
metrics = json.loads((latest_run / "metrics.json").read_text())
print(overview.read_text().splitlines()[:3])
print(metrics["training"]["training_loss"])
```

## Load the relative adapter

The adapter requires the compatible Gemma 4 E2B base model. Install the
versions recorded in the selected `runs/run-*/run-manifest.json`, load the base checkpoint,
then use the Parameter-Efficient Fine-Tuning library:

```python
from pathlib import Path
from peft import PeftModel
from transformers import AutoModelForMultimodalLM, AutoProcessor

base_id = "unsloth/gemma-4-e2b-it-unsloth-bnb-4bit"
root = Path("/kaggle/input/duecare-gemma4-adapter-learning-study")
latest_run = sorted((root / "runs").glob("run-*"))[-1]
base = AutoModelForMultimodalLM.from_pretrained(base_id, device_map="auto")
processor = AutoProcessor.from_pretrained(base_id)
model = PeftModel.from_pretrained(base, latest_run / "adapter")
```

## Unload and release accelerator memory

```python
import gc
import torch

del model, base, processor
gc.collect()
if torch.cuda.is_available():
    torch.cuda.empty_cache()
```

Do not merge or republish weights without separately checking the Gemma terms,
the adapter manifest, and the intended-use boundary.
""",
    )
    _write_text(
        dataset / "DATA_CARD.md",
        """
# Dataset card

## Contents

- Multiple Gemma 4 text-only Low-Rank Adaptation regimes, including a matched
  supervised control and robust preference-optimization continuation.
- Relative adapter weights, not base model weights.
- Training curves, memory measurements, and package versions.
- Four-arm outputs: base and adapted model, each with and without the
  deterministic response harness.
- Recorded high-severity DueCare benchmark responses with prompt, model,
  scorer, response, and source-artifact hashes. These rows are evaluation
  evidence and are not training targets.
- A blinded, two-order frontier-judge comparison of six recorded harmful Gemma
  responses against their real DueCare harness responses; verdicts remain
  training-ineligible.
- Grounded-remix training receipts linking each compact training view to an
  approved source prompt and response without adding new facts.
- A checksummed system-evidence receipt over the 911-pair paired Gemma harness
  study, its deterministic cross-check, and 140 adversarial prompt pairs.

## Intended use

Education, reproducibility, notebook visualization, adapter-loading practice,
and research on evidence-bounded response formatting.

## Prohibited interpretation

The data does not establish trafficking, legal correctness, worker outcomes,
independent safety improvement, or production readiness.
""",
    )
    _write_text(
        dataset / "SCHEMA.md",
        """
# Schemas

- `runs/run-*/metrics.json`: per-step loss, gradient norm, learning rate,
  runtime, parameter counts, graphics-memory measurements, and preference
  reward/log-probability diagnostics when that stage ran.
- `runs/run-*/evaluation.jsonl`: locked prompts with frozen-base and adapted
  generations plus objective measurements.
- `four-arm-study/four-arm-evaluation.jsonl`: base and adapter outputs with and
  without the deterministic review harness, including origin labels.
- `four-arm-study/recorded-egregious-examples.jsonl`: recorded benchmark
  failures with source hashes and the matching harnessed response when present.
- `frontier-judge-study/judge-requests.jsonl`: anonymous pair identities,
  frozen context/rubric hashes, and both presentation orders.
- `frontier-judge-study/judge-verdicts.jsonl`: model-based measurement outputs;
  these are explicitly excluded from training.
- `frontier-judge-study/frontier-judge-summary.json`: completeness, mean
  treatment deltas, bootstrap intervals, and order-effect diagnostics.
- `recorded-harmful-request-judge-study/recorded-harmful-request-summary.json`:
  six recorded Gemma failure/harness pairs, blinded in both presentation
  orders, with pair-bootstrap interval and explicit capability boundaries.
- `system-evidence/system-evidence-receipt.json`: paired response-quality
  statistics over 911 synthetic/composite benchmark prompts, a 998-pair
  deterministic cross-check, 140 transformed adversarial prompts, source
  checkpoint hashes, and explicit non-field-detection boundaries.
- `source-curriculum/build-summary.json`: 207,680-row lane counts and the 649,
  66, and 76 parent-family counts for train, validation, and test.
- `source-curriculum/quality-audit.json`: axis coverage, privacy gates, and
  parent-family split-overlap evidence.
- `model-fallback-registry.json`: ordered judge and TPU-training candidates,
  capability requirements, and freeze/receipt rules.
- `run-overview.csv`: Kaggle-previewable run comparison.
- `training-regime-study/training-regime-matrix.json`: verified run settings,
  adapter hashes, matched holdout groups, and bounded claim ledger.
- `training-regime-study/learning-curve-points.csv`: supervised and preference
  optimizer events in one Kaggle-previewable table.
- `training-regime-study/locked-response-comparisons.jsonl`: the exact base and
  adapted responses for side-by-side notebook rendering.
""",
    )
    _write_text(
        dataset / "LIMITATIONS.md",
        """
# Limitations

- Compact grounded-remix training examples and a small holdout are far too
  limited for a domain-quality claim.
- Multiple descendants of one approved source response are not independent
  observations; row count must not be confused with effective sample size.
- Low final training loss with weak holdout transfer is evidence of overfitting,
  not generalization.
- The harness guarantees a bounded wrapper, not factual validation.
- The objective metric rewards declared structure and boundary terms; it is not
  a human or legal-quality judgment.
- The frozen frontier judge is one additional measurement instrument. It is not
  blinded human adjudication, and its preferences must not be recycled into
  this study's training data.
- The recorded harmful-request result measures refusal and non-facilitation on
  six benchmark prompts. It does not establish improved victim identification,
  prevalence estimation, legal findings, or real-world detection.
- The 911-pair and adversarial results use synthetic/composite benchmark
  prompts. They test response quality and robustness, not sensitivity,
  specificity, prevalence, or victim-identification accuracy in the world.
""",
    )
    _write_text(
        dataset / "SOURCES.md",
        """
# Sources and terms

The source model is `unsloth/gemma-4-e2b-it-unsloth-bnb-4bit`. Adapter use
requires access to a compatible Gemma 4 base model and acceptance of the Gemma
Terms of Use. Training views are deterministic, checksummed remixes of approved
DueCare prompt/response rows. DueCare-authored metrics, documentation, and
evaluation scaffolds are released under Creative Commons Attribution 4.0. No
base model weights are included.
""",
    )
    _write_text(
        dataset / "LICENSE",
        """
Mixed terms apply. DueCare-authored documentation, measurements, grounded
remix scaffolds, and evaluation tooling are licensed under Creative Commons
Attribution 4.0. Relative adapter weights depend on Gemma 4 and remain subject
to applicable Gemma terms. No base Gemma weights are redistributed. Users are
responsible for accepting and complying with the base model terms.
""",
    )
    _write_text(
        dataset / "CITATION.cff",
        """
cff-version: 1.2.0
title: DueCare Gemma 4 Adapter Learning Study
message: Cite the dataset, exact Kaggle version, and release-manifest SHA-256.
type: dataset
authors:
  - family-names: Amarel
    given-names: Taylor S.
date-released: 2026-07-15
license: CC-BY-4.0
repository-code: https://github.com/TaylorAmarelTech/gemma4_comp
""",
    )
    _write_json(
        dataset / "mlcroissant.json",
        {
            "@context": "https://schema.org/",
            "@type": "Dataset",
            "name": TITLE,
            "description": (
                "Multiple grounded-remix Gemma 4 training regimes, relative "
                "adapter weights, optimizer diagnostics, and multi-arm evaluation evidence."
            ),
            "url": f"https://www.kaggle.com/datasets/{DATASET_ID}",
            "license": (
                "Mixed: CC-BY-4.0 for DueCare-authored material; "
                "Gemma terms for adapters"
            ),
            "distribution": [
                {
                    "@type": "DataDownload",
                    "name": "Run overview",
                    "contentUrl": "run-overview.csv",
                    "encodingFormat": "text/csv",
                },
                {
                    "@type": "DataDownload",
                    "name": "Four-arm evaluation",
                    "contentUrl": "four-arm-study/four-arm-evaluation.jsonl",
                    "encodingFormat": "application/x-ndjson",
                },
                {
                    "@type": "DataDownload",
                    "name": "Frontier judge summary",
                    "contentUrl": "frontier-judge-study/frontier-judge-summary.json",
                    "encodingFormat": "application/json",
                },
                {
                    "@type": "DataDownload",
                    "name": "System evidence receipt",
                    "contentUrl": "system-evidence/system-evidence-receipt.json",
                    "encodingFormat": "application/json",
                },
                {
                    "@type": "DataDownload",
                    "name": "Recorded harmful-request judge summary",
                    "contentUrl": (
                        "recorded-harmful-request-judge-study/"
                        "recorded-harmful-request-summary.json"
                    ),
                    "encodingFormat": "application/json",
                },
            ],
        },
    )
    metadata = {
        "title": TITLE,
        "id": DATASET_ID,
        "subtitle": "Grounded Gemma 4 adapter curves and harness ablation",
        "description": (
            "A public Gemma hackathon learning study with multiple grounded-remix "
            "training regimes, relative adapter weights, supervised and preference "
            "learning curves, paired outputs, and deterministic-harness evaluations."
        ),
        "isPrivate": False,
        # Kaggle's machine-readable value for a mixed/terms-governed release is
        # `other`; the data card explains the terms split precisely.
        "licenses": [{"name": "other"}],
        "keywords": ["nlp"],
        "collaborators": [],
        "resources": [
            {"path": "README.md", "description": "Reviewer start-here guide"},
            {"path": "DATA_CARD.md", "description": "Purpose and use boundary"},
            {"path": "LOADING.md", "description": "Load, verify, and unload examples"},
            {"path": "run-overview.csv", "description": "Training-regime comparison"},
            {
                "path": "training-regime-study/training-regime-matrix.json",
                "description": "Verified matched-regime settings and results",
            },
            {
                "path": "four-arm-study/four-arm-evaluation.jsonl",
                "description": "Base and adapter outputs with and without harness",
            },
            {
                "path": "frontier-judge-study/frontier-judge-summary.json",
                "description": "Frozen blinded judge and order-effect summary",
            },
            {
                "path": (
                    "recorded-harmful-request-judge-study/"
                    "recorded-harmful-request-summary.json"
                ),
                "description": "Blinded safety comparison on recorded harmful requests",
            },
            {
                "path": "system-evidence/system-evidence-receipt.json",
                "description": "Checksummed broader harness response-quality evidence",
            },
            {
                "path": "source-curriculum/build-summary.json",
                "description": "Row counts, parent counts, and curriculum receipt",
            },
        ],
    }
    _write_json(dataset / "dataset-metadata.json", metadata)
    privacy = _privacy_scan(dataset)
    if not privacy["clean"]:
        raise PackageError(f"privacy scan failed: {privacy}")
    artifacts = _artifact_index(dataset, exclude={"release-manifest.json"})
    release_payload = {
        "schema_version": SCHEMA,
        "dataset_id": DATASET_ID,
        "publication_state": "approved_public_ready",
        "safe_to_train": False,
        "safe_to_publish": True,
        "adapter_produced": True,
        "graphics_processor_training_ran": True,
        "runs": run_records,
        "four_arm_summary": four_arm.get("summary"),
        "frontier_judge_summary": frontier_judge.get("summary"),
        "recorded_harmful_request_judge_summary": recorded_safety_judge.get(
            "summary"
        ),
        "system_evidence_receipt": system_evidence,
        "source_curriculum_receipt": curriculum_receipt,
        "training_regime_study": {
            "present": regime_receipt.get("present", True),
            "run_count": regime_receipt.get("run_count"),
            "matched_holdout_groups": regime_receipt.get("matched_holdout_groups"),
            "claim_boundary": regime_receipt.get("claim_boundary"),
            "note": regime_receipt.get("note"),
        },
        "skipped_missing_run_directories": skipped_missing_runs,
        "privacy_audit": privacy,
        "claims": {
            "narrow_grounded_remix_format_lift_in_latest_run": bool(
                run_records[-1]["narrow_lift"]
            ),
            "matched_supervised_and_preference_regimes_completed": any(
                record["preference_training"] for record in run_records
            ),
            "frontier_judge_study_completed": bool(
                (frontier_judge.get("summary") or {}).get("complete")
            ),
            "frontier_judge_is_human_gold": False,
            "frontier_judge_verdicts_training_eligible": False,
            "recorded_harmful_request_study_completed": bool(
                (recorded_safety_judge.get("summary") or {}).get("complete")
            ),
            "recorded_harmful_request_harness_won_all_pairs": (
                (recorded_safety_judge.get("summary") or {}).get("harness_wins")
                == (recorded_safety_judge.get("summary") or {}).get("recorded_pairs")
            ),
            "recorded_harmful_request_verdicts_training_eligible": False,
            "paired_trafficking_safety_response_quality_lift_demonstrated": (
                system_evidence["large_pairwise_model_judge"]["lift"] > 0
            ),
            "adversarial_response_quality_lift_demonstrated": (
                system_evidence["adversarial_robustness"]["overall"]["mean"] > 0
            ),
            "victim_identification_improvement_demonstrated": False,
            "field_detection_improvement_demonstrated": False,
            "real_world_lift": False,
            "legal_quality_demonstrated": False,
            "production_ready": False,
        },
        "artifacts": artifacts,
    }
    release = dict(release_payload)
    release["release_manifest_payload_sha256"] = _canonical_sha256(release_payload)
    release["created_at"] = time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime())
    release_path = dataset / "release-manifest.json"
    _write_json(release_path, release)
    collection = {
        "schema_version": SCHEMA,
        "dataset_id": DATASET_ID,
        "dataset_path": "dataset",
        "release_manifest_sha256": _sha256(release_path),
        "safe_to_publish": True,
        "artifacts": _artifact_index(dataset),
    }
    _write_json(output_root / "collection-manifest.json", collection)
    return {
        "dataset_id": DATASET_ID,
        "dataset_path": str(dataset),
        "release_manifest_sha256": _sha256(release_path),
        "run_count": len(run_records),
        "adapter_count": len(run_records),
        "four_arm_rows": (four_arm.get("summary") or {}).get("rows"),
        "frontier_judge_model": frontier_judge.get("judge_model"),
        "frontier_judge_complete": (frontier_judge.get("summary") or {}).get(
            "complete"
        ),
        "recorded_harmful_request_harness_wins": (
            recorded_safety_judge.get("summary") or {}
        ).get("harness_wins"),
        "safe_to_publish": True,
        "privacy_audit": privacy,
    }


def parser() -> argparse.ArgumentParser:
    value = argparse.ArgumentParser(description=__doc__)
    value.add_argument("--run-dir", type=Path, action="append", dest="run_dirs")
    value.add_argument("--output-root", type=Path, default=DEFAULT_OUTPUT)
    value.add_argument("--evidence-run", type=Path, default=DEFAULT_EVIDENCE_RUN)
    value.add_argument("--regime-matrix", type=Path, default=DEFAULT_REGIME_MATRIX)
    value.add_argument("--force", action="store_true")
    return value


def main(argv: Sequence[str] | None = None) -> int:
    args = parser().parse_args(argv)
    run_dirs = tuple(args.run_dirs) if args.run_dirs else DEFAULT_RUNS
    result = build_collection(
        run_dirs,
        args.output_root,
        evidence_run=args.evidence_run,
        regime_matrix=args.regime_matrix,
        force=args.force,
    )
    print(json.dumps(result, indent=2, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
