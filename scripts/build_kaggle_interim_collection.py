#!/usr/bin/env python3
"""Build the public, interim DueCare Kaggle training collection.

The collection is derived only from an already verified and publication-approved
DueCare Kaggle release.  It creates two purpose-specific dataset views and three
small notebooks:

* visible-reasoning SFT data;
* preference/DPO pairs;
* a CPU data audit notebook;
* a CPU-published Gemma 4 LoRA starter whose training switch requires a GPU; and
* a CPU four-arm evaluation protocol notebook.

The source rows contain final answers and deliberately authored, reviewable
decision scaffolds.  They do not contain or claim to recover hidden model
chain-of-thought.  This builder never publishes; use the Kaggle CLI only after
reviewing the generated manifests and cards.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import shutil
import sys
import textwrap
from collections.abc import Mapping, Sequence
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[1]
SCRIPT_DIR = ROOT / "scripts"
if str(SCRIPT_DIR) not in sys.path:
    sys.path.insert(0, str(SCRIPT_DIR))

from build_kaggle_training_release import verify_release_dir  # noqa: E402

DEFAULT_SOURCE_RELEASE = ROOT / "reports" / "kaggle_training_proof" / "release_v4"
DEFAULT_OUTPUT_ROOT = ROOT / "reports" / "kaggle_publish" / "interim_training_collection"
DEFAULT_REPO_COMMIT = "f6657964c904f84545715b9cc080891b1ad2efd7"

COMBINED_DATASET_ID = "taylorsamarel/duecare-proof-finetuning-data"
SFT_DATASET_ID = "taylorsamarel/duecare-visible-reasoning-sft-preview"
PREFERENCE_DATASET_ID = "taylorsamarel/duecare-preference-pairs-preview"

AUDIT_NOTEBOOK_ID = "taylorsamarel/duecare-training-data-integrity-audit"
TRAINING_NOTEBOOK_ID = "taylorsamarel/duecare-gemma-4-lora-training-starter"
EVALUATION_NOTEBOOK_ID = "taylorsamarel/duecare-four-arm-fine-tuning-evaluation"

ROW_FILES = {
    "sft_train.jsonl",
    "preference_train.jsonl",
    "sft_validation.jsonl",
    "sft_test.jsonl",
}
COMMON_SOURCE_FILES = (
    "quality_audit.json",
    "source_audit.json",
    "publication_approval.json",
    "quarantine_summary.json",
)
REASONING_BOUNDARY = (
    "Final answers, citations/source references, preference rationales, and deliberately "
    "authored visible decision scaffolds only. Hidden model chain-of-thought is neither "
    "requested, reconstructed, nor published."
)


class CollectionError(ValueError):
    """A fail-closed collection-build error."""


def _sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def _read_json(path: Path) -> dict[str, Any]:
    try:
        value = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, UnicodeDecodeError, json.JSONDecodeError) as exc:
        raise CollectionError(f"unreadable JSON artifact: {path}") from exc
    if not isinstance(value, dict):
        raise CollectionError(f"JSON artifact must contain an object: {path}")
    return value


def _read_jsonl(path: Path) -> list[dict[str, Any]]:
    rows: list[dict[str, Any]] = []
    try:
        lines = path.read_text(encoding="utf-8").splitlines()
    except (OSError, UnicodeDecodeError) as exc:
        raise CollectionError(f"unreadable JSONL artifact: {path}") from exc
    for line_number, line in enumerate(lines, start=1):
        if not line.strip():
            continue
        try:
            row = json.loads(line)
        except json.JSONDecodeError as exc:
            raise CollectionError(f"invalid JSONL row: {path.name}:{line_number}") from exc
        if not isinstance(row, dict):
            raise CollectionError(f"JSONL row must be an object: {path.name}:{line_number}")
        rows.append(row)
    return rows


def _write_json(path: Path, value: Mapping[str, Any]) -> None:
    path.write_text(json.dumps(value, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")


def _file_entry(path: Path, *, role: str, rows: int | None = None) -> dict[str, Any]:
    entry: dict[str, Any] = {
        "sha256": _sha256_file(path),
        "bytes": path.stat().st_size,
        "role": role,
    }
    if rows is not None:
        entry["rows"] = rows
    return entry


def _prepare_flat_dir(path: Path, allowed_names: set[str], *, force: bool) -> None:
    path.mkdir(parents=True, exist_ok=True)
    children = list(path.iterdir())
    if children and not force:
        raise CollectionError(f"output directory is not empty; pass --force: {path}")
    for child in children:
        if child.is_symlink() or not child.is_file() or child.name not in allowed_names:
            raise CollectionError(f"refusing to clear unexpected output entry: {child}")
        child.unlink()


def _copy_file(source: Path, target: Path) -> None:
    if source.is_symlink() or not source.is_file():
        raise CollectionError(f"source artifact must be a regular file: {source}")
    shutil.copyfile(source, target)


def _dataset_card(
    *,
    lane: str,
    title: str,
    source_manifest: Mapping[str, Any],
    counts: Mapping[str, int],
) -> str:
    source_release_id = str(source_manifest.get("release_id") or "unknown")
    if lane == "sft":
        contents = (
            f"- `{counts['sft_train']}` supervised fine-tuning rows\n"
            f"- `{counts['sft_validation']}` validation rows\n"
            f"- `{counts['sft_test']}` untouched test rows"
        )
        intended = (
            "Use the train split for response-only SFT. Keep validation and test lineages out of "
            "training and use them only for model selection and final evaluation."
        )
    else:
        contents = (
            f"- `{counts['preference_train']}` chosen/rejected preference pairs\n"
            f"- `{counts['sft_validation']}` validation rows\n"
            f"- `{counts['sft_test']}` untouched test rows"
        )
        intended = (
            "Use the preference split only after SFT or for a separately declared preference arm. "
            "Each pair contrasts a grounded answer with a bounded failure example."
        )
    return textwrap.dedent(
        f"""\
        # {title}

        This is an **interim, synthetic proof dataset** derived from the already approved combined
        release `{source_release_id}`. It is a purpose-specific view of the same proof rows, not an
        independent experiment and not the unfinished 78k+ flywheel corpus.

        ## Contents

        {contents}

        ## Intended use

        {intended}

        Verify `lane-manifest.json`, its file hashes, and `source-release-manifest.json` before use.
        The sibling public notebooks demonstrate the audit, training handoff, and four-arm
        evaluation protocol. No adapter weights or completed improvement result are included.

        ## Reasoning-data boundary

        {REASONING_BOUNDARY}

        The visible scaffold records factors such as actor, time, evidence, uncertainty, retrieval
        boundary, and a consent-preserving next action. It is training content authored for review,
        not private model telemetry.

        ## Safety, provenance, and limitations

        The source release passed its manifest, privacy, license, held-out-family, model-revision,
        row-integrity, and publication-approval gates before this view was built. Rows are synthetic
        and are not legal advice, current law, a contact directory, or a worker-case dataset. The
        preview is intentionally small and can validate plumbing; it cannot by itself establish that
        fine-tuning improves Gemma 4.

        License: CC-BY-SA-4.0. Per-row provenance and allowed-use fields are retained.
        """
    )


def _build_lane_dataset(
    *,
    source_root: Path,
    target: Path,
    source_manifest: Mapping[str, Any],
    source_manifest_sha256: str,
    lane: str,
    dataset_id: str,
    title: str,
    subtitle: str,
    force: bool,
) -> dict[str, Any]:
    if lane not in {"sft", "preference"}:
        raise CollectionError(f"unsupported lane: {lane}")
    lane_files = (
        ("sft_train.jsonl", "sft_validation.jsonl", "sft_test.jsonl")
        if lane == "sft"
        else ("preference_train.jsonl", "sft_validation.jsonl", "sft_test.jsonl")
    )
    allowed_names = {
        *lane_files,
        *COMMON_SOURCE_FILES,
        "source-release-manifest.json",
        "lane-manifest.json",
        "dataset-metadata.json",
        "DATA_CARD.md",
    }
    _prepare_flat_dir(target, allowed_names, force=force)

    copied_names = [*lane_files, *COMMON_SOURCE_FILES]
    for name in copied_names:
        source = source_root / name
        if not source.is_file():
            raise CollectionError(f"required source release artifact is missing: {name}")
        _copy_file(source, target / name)
    _copy_file(source_root / "release-manifest.json", target / "source-release-manifest.json")

    counts = {
        "sft_train": len(_read_jsonl(source_root / "sft_train.jsonl")),
        "preference_train": len(_read_jsonl(source_root / "preference_train.jsonl")),
        "sft_validation": len(_read_jsonl(source_root / "sft_validation.jsonl")),
        "sft_test": len(_read_jsonl(source_root / "sft_test.jsonl")),
    }
    data_card = _dataset_card(
        lane=lane,
        title=title,
        source_manifest=source_manifest,
        counts=counts,
    )
    (target / "DATA_CARD.md").write_text(data_card, encoding="utf-8", newline="\n")

    file_roles: dict[str, str] = {
        "sft_train.jsonl": "training",
        "preference_train.jsonl": "training",
        "sft_validation.jsonl": "validation",
        "sft_test.jsonl": "test",
        "quality_audit.json": "quality_audit",
        "source_audit.json": "source_audit",
        "publication_approval.json": "publication_approval",
        "quarantine_summary.json": "metadata_only_quarantine_summary",
        "source-release-manifest.json": "source_release_provenance",
        "DATA_CARD.md": "documentation",
    }
    file_entries: dict[str, dict[str, Any]] = {}
    for name in [*copied_names, "source-release-manifest.json", "DATA_CARD.md"]:
        rows = len(_read_jsonl(target / name)) if name in ROW_FILES else None
        file_entries[name] = _file_entry(target / name, role=file_roles[name], rows=rows)

    source_bundle = source_manifest.get("source_bundle")
    if not isinstance(source_bundle, Mapping):
        raise CollectionError("source release is missing source_bundle metadata")
    lane_manifest = {
        "schema_version": "duecare.kaggle.training_lane.v1",
        "dataset_id": dataset_id,
        "title": title,
        "lane": lane,
        "release_tier": "interim_proof",
        "created_at": source_manifest.get("created_at"),
        "source_dataset_id": source_manifest.get("dataset_id"),
        "source_release_id": source_manifest.get("release_id"),
        "source_release_sha256": source_manifest_sha256,
        "source_bundle": source_bundle,
        "release_license": source_manifest.get("release_license"),
        "publication_approval": source_manifest.get("publication_approval"),
        "counts": counts,
        "heldout_prompt_sha256": source_manifest.get("heldout_prompt_sha256", []),
        "heldout_lineage_ids": source_manifest.get("heldout_lineage_ids", []),
        "heldout_lineage_family_ids": source_manifest.get(
            "heldout_lineage_family_ids", []
        ),
        "reasoning_data_policy": REASONING_BOUNDARY,
        "collection_relationship": (
            "Purpose-specific view of the approved combined proof release; not independent "
            "training evidence and not the full flywheel corpus."
        ),
        "derived_publication_authorization": {
            "basis": "exact-byte subset redistribution from the approved source release",
            "new_or_modified_training_rows": 0,
            "source_allow_public_redistribution": bool(
                (source_manifest.get("publication_approval") or {}).get(
                    "allow_public_redistribution"
                )
            ),
            "source_approval_sha256": (
                (source_manifest.get("publication_approval") or {}).get("approval_sha256")
            ),
            "note": (
                "This is not a new curator judgment. The lane contains exact public row bytes "
                "already covered by the source approval and redistribution permission."
            ),
        },
        "gates": {
            "source_release_reverified": True,
            "source_release_safe_to_publish": bool(source_manifest.get("safe_to_publish")),
            "source_release_gates": source_manifest.get("gates", {}),
            "hidden_reasoning_excluded": True,
            "private_case_material_excluded": True,
        },
        "files": file_entries,
        "safe_to_train": True,
        "safe_to_publish": True,
    }
    _write_json(target / "lane-manifest.json", lane_manifest)

    description = (
        f"{subtitle}. An interim, manifest-bound view of the approved DueCare proof release. "
        "Includes synthetic final answers or preference pairs, visible decision scaffolds, "
        "held-out evaluation rows, provenance, privacy/license audits, and SHA-256 metadata. "
        "Hidden chain-of-thought, private cases, current legal conclusions, and credentials are "
        "excluded. See DATA_CARD.md and lane-manifest.json."
    )
    dataset_metadata = {
        "title": title,
        "id": dataset_id,
        "licenses": [{"name": "CC-BY-SA-4.0"}],
        "subtitle": subtitle,
        "description": description,
        "keywords": [],
        "collaborators": [],
    }
    _write_json(target / "dataset-metadata.json", dataset_metadata)
    return lane_manifest


def _markdown(source: str) -> dict[str, Any]:
    rendered = textwrap.dedent(source)
    return {
        "cell_type": "markdown",
        "id": hashlib.sha256(("markdown\0" + rendered).encode("utf-8")).hexdigest()[:12],
        "metadata": {},
        "source": rendered.splitlines(keepends=True),
    }


def _code(source: str) -> dict[str, Any]:
    rendered = textwrap.dedent(source)
    return {
        "cell_type": "code",
        "id": hashlib.sha256(("code\0" + rendered).encode("utf-8")).hexdigest()[:12],
        "execution_count": None,
        "metadata": {},
        "outputs": [],
        "source": rendered.splitlines(keepends=True),
    }


def _write_notebook(path: Path, cells: Sequence[Mapping[str, Any]]) -> None:
    notebook = {
        "cells": list(cells),
        "metadata": {
            "kernelspec": {
                "display_name": "Python 3",
                "language": "python",
                "name": "python3",
            },
            "language_info": {"name": "python", "version": "3"},
        },
        "nbformat": 4,
        "nbformat_minor": 5,
    }
    _write_json(path, notebook)


def _kernel_metadata(
    *,
    notebook_id: str,
    title: str,
    dataset_sources: Sequence[str],
    model_sources: Sequence[str] = (),
    enable_internet: bool = False,
) -> dict[str, Any]:
    return {
        "id": notebook_id,
        "title": title,
        "code_file": "notebook.ipynb",
        "language": "python",
        "kernel_type": "notebook",
        "is_private": False,
        "enable_gpu": False,
        "enable_internet": enable_internet,
        "dataset_sources": list(dataset_sources),
        "competition_sources": [],
        "kernel_sources": [],
        "model_sources": list(model_sources),
        "docker_image_pinning_type": "original",
        "keywords": ["synthetic-data"],
    }


NOTEBOOK_HELPERS = r'''
from __future__ import annotations

import hashlib
import json
from pathlib import Path

INPUT_ROOT = Path("/kaggle/input")
WORKING_ROOT = Path("/kaggle/working")

def dataset_dir(slug: str, marker: str) -> Path:
    direct = INPUT_ROOT / slug
    if (direct / marker).is_file():
        return direct
    marker_paths = sorted(INPUT_ROOT.rglob(marker))
    identified = []
    for marker_path in marker_paths:
        try:
            payload = json.loads(marker_path.read_text(encoding="utf-8"))
        except Exception:
            continue
        dataset_id = str(payload.get("dataset_id") or "").rsplit("/", 1)[-1]
        if dataset_id == slug:
            identified.append(marker_path.parent)
    if len(identified) == 1:
        return identified[0]
    matches = sorted(path.parent for path in marker_paths)
    if len(matches) == 1:
        return matches[0]
    raise FileNotFoundError(f"cannot resolve {slug!r} with marker {marker!r}: {matches}")

def sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()

def load_json(path: Path):
    return json.loads(path.read_text(encoding="utf-8"))

def load_jsonl(path: Path):
    return [
        json.loads(line)
        for line in path.read_text(encoding="utf-8").splitlines()
        if line.strip()
    ]

def canonical_sha256(value) -> str:
    payload = json.dumps(
        value,
        ensure_ascii=False,
        sort_keys=True,
        separators=(",", ":"),
    ).encode("utf-8")
    return hashlib.sha256(payload).hexdigest()

def row_sha256(row) -> str:
    return canonical_sha256({key: value for key, value in row.items() if key != "sha256"})
'''


def _audit_cells() -> list[dict[str, Any]]:
    return [
        _markdown(
            """
            # DueCare training-data integrity audit

            This CPU notebook re-verifies the two interim dataset views, their SHA-256 file map,
            row hashes, train/validation/test lineage isolation, and model-revision consistency.
            It prints metadata and counts rather than full sensitive-looking payloads.

            **Reasoning boundary:** the rows contain deliberately authored visible decision
            scaffolds and final answers. They do not contain or recover hidden chain-of-thought.

            The two datasets are slices of one approved proof release. They are useful for review
            and pipeline testing; they are not two independent experiments and do not establish
            that fine-tuning improved a model.
            """
        ),
        _code(NOTEBOOK_HELPERS),
        _code(
            f'''
            SFT_DIR = dataset_dir("{SFT_DATASET_ID.split('/', 1)[1]}", "lane-manifest.json")
            PREFERENCE_DIR = dataset_dir(
                "{PREFERENCE_DATASET_ID.split('/', 1)[1]}",
                "lane-manifest.json",
            )

            def verify_lane(root: Path, expected_lane: str):
                manifest = load_json(root / "lane-manifest.json")
                assert manifest["schema_version"] == "duecare.kaggle.training_lane.v1"
                assert manifest["lane"] == expected_lane
                assert manifest["safe_to_publish"] is True
                assert manifest["gates"]["hidden_reasoning_excluded"] is True
                for name, expected in manifest["files"].items():
                    path = root / name
                    assert path.is_file(), name
                    assert sha256_file(path) == expected["sha256"], name
                    assert path.stat().st_size == expected["bytes"], name
                return manifest

            sft_manifest = verify_lane(SFT_DIR, "sft")
            preference_manifest = verify_lane(PREFERENCE_DIR, "preference")
            assert (
                sft_manifest["source_release_sha256"]
                == preference_manifest["source_release_sha256"]
            )
            assert (
                sft_manifest["source_bundle"]["model"]
                == preference_manifest["source_bundle"]["model"]
            )
            print("file manifests: PASS")
            print("source release:", sft_manifest["source_release_id"])
            print("target model:", sft_manifest["source_bundle"]["model"])
            '''
        ),
        _code(
            '''
            sft_rows = load_jsonl(SFT_DIR / "sft_train.jsonl")
            preference_rows = load_jsonl(PREFERENCE_DIR / "preference_train.jsonl")
            validation_rows = load_jsonl(SFT_DIR / "sft_validation.jsonl")
            test_rows = load_jsonl(SFT_DIR / "sft_test.jsonl")

            for label, rows in {
                "sft": sft_rows,
                "preference": preference_rows,
                "validation": validation_rows,
                "test": test_rows,
            }.items():
                bad = [row["id"] for row in rows if row_sha256(row) != row.get("sha256")]
                assert not bad, f"{label} row hash failures: {bad}"

            train_families = {row["lineage_family_id"] for row in sft_rows}
            preference_families = {row["lineage_family_id"] for row in preference_rows}
            validation_families = {row["lineage_family_id"] for row in validation_rows}
            test_families = {row["lineage_family_id"] for row in test_rows}
            assert train_families == preference_families
            assert not train_families & validation_families
            assert not train_families & test_families
            assert not validation_families & test_families
            print("row hashes: PASS")
            print("lineage-family isolation: PASS")
            print({"sft": len(sft_rows), "preference": len(preference_rows),
                   "validation": len(validation_rows), "test": len(test_rows)})
            '''
        ),
        _code(
            '''
            from collections import Counter

            summary = {
                "sft_prompt_family": Counter(
                    row.get("prompt_family", "unknown") for row in sft_rows
                ),
                "sft_rubric_targets": Counter(
                    target for row in sft_rows for target in row.get("rubric_targets", [])
                ),
                "preference_quality_score": Counter(
                    row.get("quality_gate", {}).get("score_pct") for row in preference_rows
                ),
                "licenses": Counter(row.get("license") for row in [*sft_rows, *preference_rows]),
            }
            print(json.dumps(summary, indent=2, default=dict))
            print("visible scaffold example:", sft_rows[0].get("structured_rationale"))
            '''
        ),
        _markdown(
            """
            ## Audit interpretation

            A pass here establishes byte integrity, row integrity, declared provenance, and split
            isolation for the published preview. It does **not** substitute for blinded semantic
            review or a baseline-versus-adapter evaluation on independently authored cases.
            """
        ),
    ]


def _training_cells(repo_commit: str) -> list[dict[str, Any]]:
    return [
        _markdown(
            """
            # Gemma 4 LoRA training starter: DueCare interim proof data

            This notebook is published on CPU so it remains inspectable while the account's weekly
            Kaggle GPU quota is exhausted. The default run verifies the approved combined release
            and writes an exact training plan. To execute the LoRA smoke run, fork the notebook,
            enable a GPU, accept the Gemma model terms, and set `RUN_GPU_TRAINING = True`.

            The training target is commit-pinned `unsloth/gemma-4-E2B-it`. SFT and DPO consume the
            approved combined release; validation and test lineages remain excluded from training.
            No successful training or model-improvement claim is made by the default CPU run.

            **Reasoning boundary:** this trains on final answers and deliberately authored visible
            decision scaffolds, not hidden chain-of-thought.
            """
        ),
        _code(NOTEBOOK_HELPERS),
        _code(
            f'''
            COMBINED_DIR = dataset_dir(
                "{COMBINED_DATASET_ID.split('/', 1)[1]}",
                "release-manifest.json",
            )
            release = load_json(COMBINED_DIR / "release-manifest.json")
            assert release["safe_to_publish"] is True
            assert release["source_bundle"]["model"]["id"] == "unsloth/gemma-4-E2B-it"
            assert (
                release["source_bundle"]["model"]["revision"]
                == "4abfca14e6c6bfb5888b80288185b1243fb8d539"
            )
            for name, expected in release["files"].items():
                path = COMBINED_DIR / name
                if name == "dataset-metadata.json" and not path.exists():
                    # Kaggle consumes this upload-control file and does not mount it as data.
                    continue
                assert path.is_file(), name
                assert sha256_file(path) == expected["sha256"], name
            print("approved combined release: PASS")
            print("release:", release["release_id"])
            print("counts:", release["counts"])
            '''
        ),
        _code(
            f'''
            TRAINING_PLAN = {{
                "schema_version": "duecare.kaggle.gemma4_training_plan.v1",
                "source_release_id": release["release_id"],
                "source_release_sha256": sha256_file(COMBINED_DIR / "release-manifest.json"),
                "repository_commit": "{repo_commit}",
                "base_model": release["source_bundle"]["model"],
                "method": "response-only LoRA SFT followed by bounded DPO smoke pass",
                "sft_path": str(COMBINED_DIR / "sft_train.jsonl"),
                "dpo_path": str(COMBINED_DIR / "preference_train.jsonl"),
                "validation_path": str(COMBINED_DIR / "sft_validation.jsonl"),
                "test_path": str(COMBINED_DIR / "sft_test.jsonl"),
                "training_manifest": str(COMBINED_DIR / "release-manifest.json"),
                "output_dir": "/kaggle/working/duecare-gemma4-interim-adapter",
                "published_run_mode": "CPU validation only",
                "gpu_execution_requires_explicit_opt_in": True,
                "reasoning_data_policy": "{REASONING_BOUNDARY}",
            }}
            plan_path = WORKING_ROOT / "training-plan.json"
            plan_path.write_text(json.dumps(TRAINING_PLAN, indent=2) + "\\n", encoding="utf-8")
            print(json.dumps(TRAINING_PLAN, indent=2))
            print("wrote", plan_path)
            '''
        ),
        _code(
            f'''
            RUN_GPU_TRAINING = False

            if not RUN_GPU_TRAINING:
                print("GPU training is intentionally disabled in the published CPU validation run.")
                print("Fork, enable a GPU, accept the Gemma terms, then set RUN_GPU_TRAINING=True.")
            else:
                import subprocess
                import sys
                import torch

                if not torch.cuda.is_available():
                    raise RuntimeError(
                        "RUN_GPU_TRAINING=True requires a CUDA-enabled Kaggle session"
                    )

                repo_dir = WORKING_ROOT / "gemma4_comp"
                if not repo_dir.exists():
                    subprocess.run(
                        [
                            "git",
                            "clone",
                            "https://github.com/TaylorAmarelTech/gemma4_comp.git",
                            str(repo_dir),
                        ],
                        check=True,
                    )
                subprocess.run(
                    ["git", "-C", str(repo_dir), "fetch", "origin", "{repo_commit}"],
                    check=True,
                )
                subprocess.run(
                    ["git", "-C", str(repo_dir), "checkout", "--detach", "{repo_commit}"],
                    check=True,
                )
                subprocess.run(
                    [
                        sys.executable, "-m", "pip", "install", "-q",
                        "torch>=2.8.0", "triton>=3.4.0", "bitsandbytes", "unsloth",
                        "unsloth_zoo>=2026.4.6", "transformers==5.5.0", "datasets",
                        "trl", "peft", "accelerate",
                    ],
                    check=True,
                )
                command = [
                    sys.executable,
                    str(repo_dir / "scripts" / "train_lift_distill.py"),
                    "--base-model", "unsloth/gemma-4-E2B-it",
                    "--base-revision", "4abfca14e6c6bfb5888b80288185b1243fb8d539",
                    "--sft", str(COMBINED_DIR / "sft_train.jsonl"),
                    "--dpo", str(COMBINED_DIR / "preference_train.jsonl"),
                    "--training-manifest", str(COMBINED_DIR / "release-manifest.json"),
                    "--out", "/kaggle/working/duecare-gemma4-interim-adapter",
                    "--test-run",
                ]
                print("executing pinned training command:", command)
                subprocess.run(command, check=True)
            '''
        ),
        _markdown(
            """
            ## Required evidence after a GPU run

            Before calling this a fine-tuning result, inspect the completion manifest and adapter
            config, confirm the pinned base revision, and run the sibling four-arm evaluation on the
            untouched test lineages. A smoke adapter is pipeline evidence, not a production release.
            """
        ),
    ]


def _evaluation_cells() -> list[dict[str, Any]]:
    return [
        _markdown(
            """
            # DueCare four-arm fine-tuning evaluation protocol

            This CPU notebook freezes the evaluation inputs and scoring plan for four comparable
            arms: stock model, stock plus harness, adapter, and adapter plus harness. It verifies
            that held-out lineage families do not appear in SFT or preference training and exports
            a machine-readable protocol.

            The notebook does not fabricate model outputs. Until a GPU adapter run and all four arms
            complete on the same holdout, there is no claimed improvement result.
            """
        ),
        _code(NOTEBOOK_HELPERS),
        _code(
            f'''
            COMBINED_DIR = dataset_dir(
                "{COMBINED_DATASET_ID.split('/', 1)[1]}",
                "release-manifest.json",
            )
            release = load_json(COMBINED_DIR / "release-manifest.json")
            assert release["safe_to_publish"] is True
            for name, expected in release["files"].items():
                path = COMBINED_DIR / name
                if name == "dataset-metadata.json" and not path.exists():
                    # Kaggle consumes this upload-control file and does not mount it as data.
                    continue
                assert path.is_file(), name
                assert sha256_file(path) == expected["sha256"], name

            train = load_jsonl(COMBINED_DIR / "sft_train.jsonl")
            preference = load_jsonl(COMBINED_DIR / "preference_train.jsonl")
            validation = load_jsonl(COMBINED_DIR / "sft_validation.jsonl")
            test = load_jsonl(COMBINED_DIR / "sft_test.jsonl")

            train_families = {{row["lineage_family_id"] for row in [*train, *preference]}}
            validation_families = {{row["lineage_family_id"] for row in validation}}
            test_families = {{row["lineage_family_id"] for row in test}}
            assert not train_families & validation_families
            assert not train_families & test_families
            assert not validation_families & test_families
            print("held-out lineage-family isolation: PASS")
            '''
        ),
        _code(
            '''
            def user_prompt(row):
                for message in row.get("messages", []):
                    if message.get("role") == "user":
                        return message.get("content", "")
                return ""

            evaluation_rows = []
            for split, rows in (("validation", validation), ("test", test)):
                for row in rows:
                    prompt = user_prompt(row)
                    evaluation_rows.append({
                        "id": row["id"],
                        "split": split,
                        "lineage_id": row["lineage_id"],
                        "lineage_family_id": row["lineage_family_id"],
                        "prompt": prompt,
                        "prompt_sha256": hashlib.sha256(prompt.strip().encode("utf-8")).hexdigest(),
                        "rubric_targets": row.get("rubric_targets", []),
                    })

            eval_path = WORKING_ROOT / "evaluation-prompts.jsonl"
            eval_path.write_text(
                "".join(
                    json.dumps(row, ensure_ascii=False, sort_keys=True) + "\\n"
                    for row in evaluation_rows
                ),
                encoding="utf-8",
            )
            print("frozen evaluation rows:", len(evaluation_rows))
            print("wrote", eval_path)
            '''
        ),
        _code(
            '''
            EVALUATION_PLAN = {
                "schema_version": "duecare.four_arm_evaluation_plan.v1",
                "source_release_id": release["release_id"],
                "base_model": release["source_bundle"]["model"],
                "arms": [
                    "stock_model",
                    "stock_model_plus_duecare_harness",
                    "lora_adapter",
                    "lora_adapter_plus_duecare_harness",
                ],
                "frozen_splits": {"validation": len(validation), "test": len(test)},
                "primary_dimensions": [
                    "cross_jurisdiction_reasoning",
                    "temporal_uncertainty",
                    "evidence_fidelity",
                    "safety_non_uplift",
                    "retrieval_boundary",
                    "consent_preserving_action",
                ],
                "blocking_regressions": [
                    "privacy_leakage",
                    "unsupported_legal_certainty",
                    "unsafe_operational_advice",
                    "citation_or_source_fabrication",
                    "benign_over_refusal",
                ],
                "promotion_rule": (
                    "compare all arms on identical test prompts; require intended-dimension lift "
                    "with no blocking safety regression"
                ),
                "result_status": "pending_model_runs",
            }
            plan_path = WORKING_ROOT / "evaluation-plan.json"
            plan_path.write_text(json.dumps(EVALUATION_PLAN, indent=2) + "\\n", encoding="utf-8")
            print(json.dumps(EVALUATION_PLAN, indent=2))
            '''
        ),
        _markdown(
            """
            ## What this proves

            The published run proves the evaluation contract is explicit, the holdout is frozen,
            and the split families are isolated. It does not prove an adapter is better. That claim
            requires completed outputs, per-dimension grades, confidence intervals or paired tests
            appropriate to the sample, and inspection of every blocking regression.
            """
        ),
    ]


def _build_notebook_dir(
    *,
    target: Path,
    cells: Sequence[Mapping[str, Any]],
    metadata: Mapping[str, Any],
    force: bool,
) -> None:
    allowed = {"notebook.ipynb", "kernel-metadata.json"}
    _prepare_flat_dir(target, allowed, force=force)
    _write_notebook(target / "notebook.ipynb", cells)
    _write_json(target / "kernel-metadata.json", metadata)


def build_collection(
    source_release: Path,
    output_root: Path,
    *,
    force: bool = False,
    repo_commit: str = DEFAULT_REPO_COMMIT,
) -> dict[str, Any]:
    source_root = source_release.resolve()
    output = output_root.resolve()
    verification = verify_release_dir(source_root)
    if not verification.get("ok"):
        raise CollectionError("source release reverification did not return ok=true")
    source_manifest_path = source_root / "release-manifest.json"
    source_manifest = _read_json(source_manifest_path)
    if source_manifest.get("safe_to_publish") is not True:
        raise CollectionError("source release is not marked safe_to_publish=true")
    if source_manifest.get("dataset_id") != COMBINED_DATASET_ID:
        raise CollectionError("unexpected source dataset ID")

    datasets_root = output / "datasets"
    notebooks_root = output / "notebooks"
    datasets_root.mkdir(parents=True, exist_ok=True)
    notebooks_root.mkdir(parents=True, exist_ok=True)
    source_manifest_sha256 = _sha256_file(source_manifest_path)

    sft_manifest = _build_lane_dataset(
        source_root=source_root,
        target=datasets_root / "visible_reasoning_sft",
        source_manifest=source_manifest,
        source_manifest_sha256=source_manifest_sha256,
        lane="sft",
        dataset_id=SFT_DATASET_ID,
        title="DueCare Visible-Reasoning SFT Preview",
        subtitle="Synthetic SFT with visible decision scaffolds and isolated holdouts",
        force=force,
    )
    preference_manifest = _build_lane_dataset(
        source_root=source_root,
        target=datasets_root / "preference_pairs",
        source_manifest=source_manifest,
        source_manifest_sha256=source_manifest_sha256,
        lane="preference",
        dataset_id=PREFERENCE_DATASET_ID,
        title="DueCare Preference Pairs Preview",
        subtitle="Synthetic chosen/rejected pairs for bounded DPO experiments",
        force=force,
    )

    _build_notebook_dir(
        target=notebooks_root / "integrity_audit",
        cells=_audit_cells(),
        metadata=_kernel_metadata(
            notebook_id=AUDIT_NOTEBOOK_ID,
            title="DueCare Training Data Integrity Audit",
            dataset_sources=[SFT_DATASET_ID, PREFERENCE_DATASET_ID],
        ),
        force=force,
    )
    _build_notebook_dir(
        target=notebooks_root / "gemma4_training_starter",
        cells=_training_cells(repo_commit),
        metadata=_kernel_metadata(
            notebook_id=TRAINING_NOTEBOOK_ID,
            title="DueCare Gemma 4 LoRA Training Starter",
            dataset_sources=[COMBINED_DATASET_ID, SFT_DATASET_ID, PREFERENCE_DATASET_ID],
            model_sources=["google/gemma-4/Transformers/gemma-4-e2b-it/1"],
            enable_internet=True,
        ),
        force=force,
    )
    _build_notebook_dir(
        target=notebooks_root / "four_arm_evaluation",
        cells=_evaluation_cells(),
        metadata=_kernel_metadata(
            notebook_id=EVALUATION_NOTEBOOK_ID,
            title="DueCare Four-Arm Fine-Tuning Evaluation",
            dataset_sources=[COMBINED_DATASET_ID],
        ),
        force=force,
    )

    manifest = {
        "schema_version": "duecare.kaggle.interim_training_collection.v1",
        "source_release_id": source_manifest.get("release_id"),
        "source_release_sha256": source_manifest_sha256,
        "reasoning_data_policy": REASONING_BOUNDARY,
        "datasets": {
            "combined": {
                "id": COMBINED_DATASET_ID,
                "url": f"https://www.kaggle.com/datasets/{COMBINED_DATASET_ID}",
                "status": "existing_approved_source",
            },
            "sft": {
                "id": SFT_DATASET_ID,
                "path": "datasets/visible_reasoning_sft",
                "manifest_sha256": _sha256_file(
                    datasets_root / "visible_reasoning_sft" / "lane-manifest.json"
                ),
                "safe_to_publish": sft_manifest["safe_to_publish"],
            },
            "preference": {
                "id": PREFERENCE_DATASET_ID,
                "path": "datasets/preference_pairs",
                "manifest_sha256": _sha256_file(
                    datasets_root / "preference_pairs" / "lane-manifest.json"
                ),
                "safe_to_publish": preference_manifest["safe_to_publish"],
            },
        },
        "notebooks": {
            "audit": {
                "id": AUDIT_NOTEBOOK_ID,
                "path": "notebooks/integrity_audit",
                "published_accelerator": "cpu",
            },
            "training_starter": {
                "id": TRAINING_NOTEBOOK_ID,
                "path": "notebooks/gemma4_training_starter",
                "published_accelerator": "cpu",
                "gpu_training_default": False,
                "gpu_note": "Fork and opt in after GPU quota is available.",
            },
            "evaluation": {
                "id": EVALUATION_NOTEBOOK_ID,
                "path": "notebooks/four_arm_evaluation",
                "published_accelerator": "cpu",
            },
            "full_gpu_workbench": {
                "id": "taylorsamarel/duecare-fine-tuning-and-evaluation",
                "url": (
                    "https://www.kaggle.com/code/taylorsamarel/"
                    "duecare-fine-tuning-and-evaluation"
                ),
                "status": "existing_gpu_notebook",
            },
        },
        "claims": {
            "datasets_are_interim_proof": True,
            "hidden_chain_of_thought_published": False,
            "adapter_weights_published": False,
            "completed_improvement_result": False,
            "full_flywheel_corpus_published": False,
        },
    }
    _write_json(output / "collection-manifest.json", manifest)
    return manifest


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--source-release", type=Path, default=DEFAULT_SOURCE_RELEASE)
    parser.add_argument("--output-root", type=Path, default=DEFAULT_OUTPUT_ROOT)
    parser.add_argument("--repo-commit", default=DEFAULT_REPO_COMMIT)
    parser.add_argument("--force", action="store_true")
    return parser


def main(argv: Sequence[str] | None = None) -> int:
    args = build_parser().parse_args(argv)
    try:
        manifest = build_collection(
            args.source_release,
            args.output_root,
            force=args.force,
            repo_commit=args.repo_commit,
        )
    except (CollectionError, OSError, ValueError) as exc:
        print(f"BLOCKED: {exc}", file=sys.stderr)
        return 2
    print(json.dumps(manifest, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
