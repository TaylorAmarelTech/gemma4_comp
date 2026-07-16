#!/usr/bin/env python3
"""Package the verified DueCare scratch-model learning run for Kaggle."""

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
DEFAULT_SOURCE = (
    ROOT
    / "reports"
    / "kaggle_publish"
    / "kaggle_kernel_outputs"
    / "grounded_byte_model_cpu_private_v1"
    / "from-scratch-tpu"
)
DEFAULT_OUTPUT = (
    ROOT
    / "reports"
    / "kaggle_publish"
    / "grounded_scratch_model_collection_v1"
)
DATASET_ID = "taylorsamarel/duecare-grounded-byte-model-learning-study"
TITLE = "DueCare Grounded Byte Model Learning Study"
SCHEMA = "duecare.kaggle.grounded_byte_model_study.v1"
SOURCE_DATASET_ID = "taylorsamarel/duecare-measured-review-curriculum-200k"
SOURCE_RELEASE_SHA256 = (
    "1b062ce12fe43494f7d63659a53017c857e0ac0103759d8f71b3340f63bdc2b7"
)
MARKER = ".duecare-grounded-byte-model-collection"
TEXT_SUFFIXES = {".json", ".jsonl", ".md", ".csv", ".txt", ".cff"}
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
    """Raised when the model-study evidence cannot be packaged safely."""


def _sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def _canonical_sha256(value: Any) -> str:
    payload = json.dumps(
        value, ensure_ascii=True, sort_keys=True, separators=(",", ":")
    ).encode("utf-8")
    return hashlib.sha256(payload).hexdigest()


def _write_json(path: Path, value: Any) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(
        json.dumps(value, ensure_ascii=True, indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
        newline="\n",
    )


def _artifact_index(root: Path, *, exclude: set[str] | None = None) -> list[dict[str, Any]]:
    excluded = exclude or set()
    rows = []
    for path in sorted(item for item in root.rglob("*") if item.is_file()):
        relative = path.relative_to(root).as_posix()
        if relative in excluded:
            continue
        rows.append(
            {
                "path": relative,
                "bytes": path.stat().st_size,
                "sha256": _sha256(path),
            }
        )
    return rows


def _prepare(output_root: Path, *, force: bool) -> Path:
    if output_root.exists():
        marker = output_root / MARKER
        if not force:
            raise PackageError(f"output exists; pass --force: {output_root}")
        if not marker.is_file():
            raise PackageError(f"refusing to replace unmarked directory: {output_root}")
        shutil.rmtree(output_root)
    output_root.mkdir(parents=True)
    (output_root / MARKER).write_text("managed by scratch-model packager\n", encoding="utf-8")
    dataset = output_root / "dataset"
    dataset.mkdir()
    return dataset


def _load_summary(source: Path) -> dict[str, Any]:
    path = source / "scratch-training-summary.json"
    if not path.is_file():
        raise PackageError(f"missing training summary: {path}")
    value = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(value, dict):
        raise PackageError("training summary must be an object")
    required = {
        "training_completed": True,
        "cpu_fallback_training_completed": True,
        "tpu_training_completed": False,
        "initialized_from_scratch": True,
        "pretrained_checkpoint_loaded": False,
        "free_standing_fictional_generation": False,
        "full_model_produced": True,
        "adapter_produced": False,
        "real_world_model_lift_demonstrated": False,
        "production_ready": False,
    }
    for key, expected in required.items():
        if value.get(key) is not expected:
            raise PackageError(f"unexpected {key}: {value.get(key)!r}")
    if value.get("release_manifest_sha256") != SOURCE_RELEASE_SHA256:
        raise PackageError("source curriculum manifest hash mismatch")
    models = value.get("saved_models")
    if not isinstance(models, list) or len(models) != 2:
        raise PackageError("exactly two saved scratch models are required")
    for record in models:
        model_path = source / str(record["model_file"])
        config_path = source / str(record["config_file"])
        if _sha256(model_path) != record["model_sha256"]:
            raise PackageError(f"model checksum mismatch: {model_path.name}")
        if _sha256(config_path) != record["config_sha256"]:
            raise PackageError(f"config checksum mismatch: {config_path.name}")
        if record.get("reload_verified") is not True:
            raise PackageError(f"reload was not verified: {model_path.name}")
    return value


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


def _copy_evidence(source: Path, dataset: Path, summary: dict[str, Any]) -> None:
    for record in summary["saved_models"]:
        shutil.copy2(source / record["model_file"], dataset / record["model_file"])
        shutil.copy2(source / record["config_file"], dataset / record["config_file"])
    for name in (
        "scratch-training-summary.json",
        "scratch-training-curves.csv",
        "scratch-before-after.jsonl",
        "byte_token_distribution.png",
        "grounded_training_coverage.png",
        "scratch_before_after_lengths.png",
        "scratch_optimization_dashboard.png",
        "scratch_parameter_scale.png",
        "scratch_transfer_and_timing.png",
    ):
        source_path = source / name
        if not source_path.is_file():
            raise PackageError(f"missing evidence artifact: {name}")
        shutil.copy2(source_path, dataset / name)


def _write_preview(dataset: Path, summary: dict[str, Any]) -> None:
    path = dataset / "model-preview.csv"
    fields = [
        "label",
        "parameters",
        "optimizer_steps",
        "initial_heldout_loss",
        "final_heldout_loss",
        "heldout_loss_delta",
        "reload_verified",
        "accelerator",
    ]
    saved = {item["label"]: item for item in summary["saved_models"]}
    with path.open("w", encoding="utf-8", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=fields)
        writer.writeheader()
        for attempt in summary["architecture_attempts"]:
            writer.writerow(
                {
                    "label": attempt["label"],
                    "parameters": attempt["parameters"],
                    "optimizer_steps": summary["optimizer_steps_per_model"],
                    "initial_heldout_loss": attempt["initial_heldout_loss"],
                    "final_heldout_loss": attempt["final_heldout_loss"],
                    "heldout_loss_delta": (
                        attempt["final_heldout_loss"] - attempt["initial_heldout_loss"]
                    ),
                    "reload_verified": saved[attempt["label"]]["reload_verified"],
                    "accelerator": summary["accelerator"],
                }
            )


def _write_docs(dataset: Path, summary: dict[str, Any]) -> None:
    attempts = summary["architecture_attempts"]
    model_lines = "\n".join(
        f"- **{row['label']}**: {row['parameters']:,} parameters; held-out "
        f"next-byte loss {row['initial_heldout_loss']:.4f} to "
        f"{row['final_heldout_loss']:.4f}."
        for row in attempts
    )
    (dataset / "README.md").write_text(
        f"""# DueCare Grounded Byte Model Learning Study

Start with `model-preview.csv`, then open the graphics and the full receipt in
`scratch-training-summary.json`. Every artifact is a first-class file, so no
nested archive must be unpacked before loading.

This is a Kaggle and Gemma hackathon learning artifact containing **two real,
complete models initialized from random weights**. It is not supervised
fine-tuning of Gemma and it contains no borrowed base-model weights.

{model_lines}

Both NumPy parameter archives passed an exact save/reload comparison. The run
used the central-processing-unit compatibility profile: 16 distinct training
parents, 4 held-out parents, and 2 optimizer steps per model. The 207,680-row
public curriculum was the source pool; the training text was a deterministic
remix of approved DueCare prompt/response rows with parent checksums. No
free-standing fictional story was generated.

These results prove optimization and serialization mechanics only. They do not
show useful language behavior, legal quality, human-trafficking status,
real-world model lift, or production readiness.

Source dataset: <https://www.kaggle.com/datasets/taylorsamarel/duecare-measured-review-curriculum-200k>

The companion notebook has been created at
`taylorsamarel/duecare-grounded-byte-model-training-lab`. Its public visibility
is pending Kaggle's daily public-notebook quota; this dataset is self-contained.
""",
        encoding="utf-8",
    )
    (dataset / "DATA_CARD.md").write_text(
        """# Dataset card

## Purpose

Teach and audit a minimal from-random-initialization language-model workflow:
lineage-aware selection, byte tokenization, two architecture arms, Adam-style
updates, held-out loss, before/after output, full-model serialization, and
exact reload verification.

## Intended uses

- educational notebook execution;
- serializer and loader testing;
- optimizer, architecture, and accelerator mechanism comparisons;
- negative-control comparison with pretrained-model adaptation.

## Prohibited interpretations

Do not call these models Gemma adapters, frontier models, legal classifiers,
worker-support systems, or evidence of real-world improvement. Do not use the
before/after outputs as positive training targets.
""",
        encoding="utf-8",
    )
    (dataset / "SCHEMA.md").write_text(
        """# Schema

- `*.npz`: complete float32 NumPy parameter leaves (`allow_pickle=False`).
- `*.config.json`: architecture, tokenizer, parameter-tree description,
  ordered leaf names, shapes, and data types.
- `scratch-training-summary.json`: compute, lineage, model, reload,
  claim, and completion receipt.
- `scratch-training-curves.csv`: model, step, loss, next-byte accuracy,
  gradient norm, learning rate, and step time.
- `scratch-before-after.jsonl`: lineage-bound random and trained text;
  every record is `training_eligible=false`.
- `model-preview.csv`: Kaggle-friendly metric preview without prompt text.
""",
        encoding="utf-8",
    )
    (dataset / "LOADING.md").write_text(
        """# Loading and unloading

```python
import json
import numpy as np

config = json.load(open("duecare-micro-byte-transformer.config.json"))
with np.load("duecare-micro-byte-transformer.npz", allow_pickle=False) as archive:
    leaves = [archive[name] for name in sorted(archive.files)]

assert [list(value.shape) for value in leaves] == [
    row["shape"] for row in config["parameter_leaves"]
]

# Release memory before another model attempt.
del leaves, config
```

Reconstructing the JAX parameter tree also requires the architecture function
shown in the companion notebook. Never use pickle loading for this package.
""",
        encoding="utf-8",
    )
    (dataset / "SOURCES.md").write_text(
        f"""# Sources

- Public curriculum: `{SOURCE_DATASET_ID}`.
- Source release-manifest SHA-256: `{SOURCE_RELEASE_SHA256}`.
- Training rows: 16 deterministic, distinct-parent grounded remixes.
- Held-out rows: 4 distinct test parents with zero parent overlap.
- Pretrained checkpoints: none.
- External tokenizer: none; the tokenizer is UTF-8 bytes plus three control
  identifiers.
""",
        encoding="utf-8",
    )
    (dataset / "LIMITATIONS.md").write_text(
        """# Limitations

- Two optimizer steps are a mechanism smoke test, not pretraining at useful scale.
- The source pool contains augmentation descendants; row count is not independent
  case count.
- Held-out loss covers four parent lineages and cannot support broad claims.
- Byte tokenization is transparent but inefficient relative to trained subword
  tokenizers.
- Random and trained completions can be malformed; they are displayed as a
  negative control and are excluded from training.
- Central-processing-unit completion does not prove the Tensor Processing Unit
  path completed.
""",
        encoding="utf-8",
    )
    (dataset / "LICENSE").write_text(
        """Mixed terms apply.

DueCare grants the model parameter archives, configuration files, and loading
example under the MIT License, without warranty. DueCare-authored cards,
measurements, charts, and receipts are licensed under Creative Commons
Attribution 4.0. The source curriculum is also published under Creative
Commons Attribution 4.0; attribution must identify DueCare contributors.
No third-party pretrained model weights are included.
""",
        encoding="utf-8",
    )
    (dataset / "CITATION.cff").write_text(
        """cff-version: 1.2.0
title: DueCare Grounded Byte Model Learning Study
message: Cite the dataset, Kaggle version, and release-manifest SHA-256.
type: dataset
authors:
  - family-names: Amarel
    given-names: Taylor
date-released: 2026-07-15
license: CC-BY-4.0
""",
        encoding="utf-8",
    )


def build(source: Path, output_root: Path, *, force: bool) -> dict[str, Any]:
    source = source.resolve(strict=True)
    summary = _load_summary(source)
    dataset = _prepare(output_root, force=force)
    _copy_evidence(source, dataset, summary)
    _write_preview(dataset, summary)
    _write_docs(dataset, summary)

    candidate = {
        "schema_version": SCHEMA,
        "dataset_id": DATASET_ID,
        "source_dataset_id": SOURCE_DATASET_ID,
        "source_release_manifest_sha256": SOURCE_RELEASE_SHA256,
        "publication_state": "approved_public_candidate",
        "safe_to_publish": True,
        "safe_to_train": False,
        "initialized_from_scratch": True,
        "training_backend": summary["accelerator"],
        "training_completed": True,
        "tpu_training_completed": False,
        "full_model_produced": True,
        "adapter_produced": False,
        "model_count": len(summary["saved_models"]),
        "models": summary["saved_models"],
        "claim_boundaries": {
            "optimization_mechanism_observed": True,
            "exact_reload_verified": True,
            "useful_language_behavior": False,
            "real_world_model_lift": False,
            "production_ready": False,
        },
    }
    candidate["candidate_manifest_payload_sha256"] = _canonical_sha256(candidate)
    _write_json(dataset / "candidate-manifest.json", candidate)

    _write_json(
        dataset / "shard-index.json",
        {
            "schema_version": SCHEMA,
            "model_files": [
                {
                    "path": row["model_file"],
                    "sha256": row["model_sha256"],
                    "reload_verified": row["reload_verified"],
                }
                for row in summary["saved_models"]
            ],
            "evidence_files": sorted(
                path.name
                for path in dataset.iterdir()
                if path.is_file()
                and path.name.startswith(("scratch-", "scratch_", "byte_", "grounded_"))
            ),
        },
    )
    _write_json(
        dataset / "mlcroissant.json",
        {
            "@context": "https://schema.org/",
            "@type": "sc:Dataset",
            "conformsTo": "http://mlcommons.org/croissant/1.1",
            "name": TITLE,
            "description": (
                "Two complete byte-level transformer learning models initialized "
                "from random weights with grounded lineage and reload receipts."
            ),
            "license": "https://creativecommons.org/licenses/by/4.0/",
            "url": f"https://www.kaggle.com/datasets/{DATASET_ID}",
            "creator": {"@type": "sc:Person", "name": "Taylor S. Amarel"},
            "distribution": [
                {
                    "@type": "cr:FileObject",
                    "name": row["model_file"],
                    "contentUrl": row["model_file"],
                    "sha256": row["model_sha256"],
                    "encodingFormat": "application/zip",
                }
                for row in summary["saved_models"]
            ],
        },
    )
    metadata = {
        "id": DATASET_ID,
        "title": TITLE,
        "subtitle": "Complete random-initialization byte models with curves and reload receipts",
        "description": (
            "A public Kaggle learning study with two complete byte-level "
            "transformers initialized from random weights, grounded-remix "
            "lineage, loss curves, before/after text, and exact reload verification."
        ),
        "isPrivate": False,
        "licenses": [{"name": "other"}],
        "keywords": ["nlp"],
        "collaborators": [],
        "resources": [
            {"path": "README.md", "description": "Reviewer start-here guide"},
            {"path": "model-preview.csv", "description": "Safe metric preview"},
            {"path": "DATA_CARD.md", "description": "Purpose and claim boundaries"},
            {"path": "LOADING.md", "description": "Safe parameter loading and unloading"},
            {
                "path": "scratch-training-summary.json",
                "description": "Machine-readable run receipt",
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
        "safe_to_publish": True,
        "safe_to_train": False,
        "source_dataset_id": SOURCE_DATASET_ID,
        "source_release_manifest_sha256": SOURCE_RELEASE_SHA256,
        "training_summary": summary,
        "privacy_audit": privacy,
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
        "release_manifest_sha256": collection["release_manifest_sha256"],
        "model_count": len(summary["saved_models"]),
        "training_backend": summary["accelerator"],
        "privacy_audit": privacy,
        "safe_to_publish": True,
    }


def parser() -> argparse.ArgumentParser:
    value = argparse.ArgumentParser(description=__doc__)
    value.add_argument("--source", type=Path, default=DEFAULT_SOURCE)
    value.add_argument("--output-root", type=Path, default=DEFAULT_OUTPUT)
    value.add_argument("--force", action="store_true")
    return value


def main(argv: Sequence[str] | None = None) -> int:
    args = parser().parse_args(argv)
    result = build(args.source, args.output_root, force=args.force)
    print(json.dumps(result, indent=2, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
