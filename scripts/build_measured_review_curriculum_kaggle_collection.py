#!/usr/bin/env python3
"""Package the measured-response review curriculum as a public Kaggle dataset.

The source candidate is immutable and remains marked as unapproved.  This
packager requires an explicit operator approval on the command line, verifies
the candidate manifest and its clean quality audit, and writes a separate
release manifest that records the publication decision.  Large JSON Lines
shards are hard-linked when possible so local packaging does not duplicate
several gigabytes; the resulting files are ordinary files to Kaggle clients.
"""

from __future__ import annotations

import argparse
import csv
import hashlib
import json
import os
import re
import shutil
from collections import Counter
from collections.abc import Iterable, Mapping, Sequence
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[1]
DEFAULT_SOURCE = (
    ROOT
    / "reports"
    / "response_preference_candidates"
    / "measured_review_curriculum_200k_v2"
)
DEFAULT_OUTPUT = (
    ROOT
    / "reports"
    / "kaggle_publish"
    / "measured_review_curriculum_200k_v1"
)
DEFAULT_DATASET_ID = "taylorsamarel/duecare-measured-review-curriculum-200k"
DEFAULT_TITLE = "DueCare Measured Response Review Curriculum 200K"
SCHEMA = "duecare.kaggle.measured_review_curriculum.v1"
CANDIDATE_SCHEMA = "duecare.measured_response.review_curriculum_candidate.v1"
MARKER = ".duecare-measured-review-kaggle-collection"
HASH_BUFFER = 1024 * 1024
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
    """Raised when a candidate cannot be released safely and reproducibly."""


def _sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(HASH_BUFFER), b""):
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
        raise PackageError(f"expected JSON object: {path}")
    return value


def _write_json(path: Path, value: Any) -> None:
    path.write_text(
        json.dumps(value, ensure_ascii=True, indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
        newline="\n",
    )


def _write_text(path: Path, value: str) -> None:
    path.write_text(value.strip() + "\n", encoding="utf-8", newline="\n")


def _prepare_output(path: Path, *, force: bool) -> tuple[Path, Path]:
    path = path.resolve()
    if path.exists():
        if not force:
            raise PackageError(f"output exists; use --force: {path}")
        if not (path / MARKER).is_file():
            raise PackageError(f"refusing to replace unowned directory: {path}")
        shutil.rmtree(path)
    path.mkdir(parents=True)
    (path / MARKER).write_text(SCHEMA + "\n", encoding="utf-8")
    dataset = path / "dataset"
    dataset.mkdir()
    return path, dataset


def _link_or_copy(source: Path, destination: Path) -> str:
    destination.parent.mkdir(parents=True, exist_ok=True)
    try:
        os.link(source, destination)
        return "hardlink"
    except OSError:
        shutil.copy2(source, destination)
        return "copy"


def _iter_jsonl(path: Path) -> Iterable[dict[str, Any]]:
    with path.open("r", encoding="utf-8") as handle:
        for line_number, line in enumerate(handle, 1):
            if not line.strip():
                continue
            try:
                value = json.loads(line)
            except json.JSONDecodeError as exc:
                raise PackageError(f"invalid JSON at {path.name}:{line_number}") from exc
            if not isinstance(value, dict):
                raise PackageError(f"non-object JSON at {path.name}:{line_number}")
            yield value


def _verify_candidate(source: Path) -> tuple[dict[str, Any], dict[str, Any]]:
    manifest_path = source / "candidate-manifest.json"
    manifest = _read_json(manifest_path)
    if manifest.get("schema_version") != CANDIDATE_SCHEMA:
        raise PackageError("candidate schema is not supported")
    if manifest.get("safe_to_train") is not True or manifest.get("safe_to_publish") is not False:
        raise PackageError("candidate must be train-safe and publication-unapproved")
    audit_declaration = manifest.get("quality_audit") or {}
    audit_path = source / str(audit_declaration.get("path") or "")
    audit = _read_json(audit_path)
    if (
        audit.get("clean") is not True
        or audit.get("risk_flags") not in ([], None)
        or _sha256(audit_path) != audit_declaration.get("sha256")
    ):
        raise PackageError("candidate quality audit is not clean or hash-bound")
    declared_counts = Counter()
    for lane, declarations in (manifest.get("artifacts") or {}).get("shards", {}).items():
        for declaration in declarations:
            shard = source / str(declaration.get("path") or "")
            if not shard.is_file():
                raise PackageError(f"missing shard: {shard.name}")
            if (
                shard.stat().st_size != declaration.get("bytes")
                or _sha256(shard) != declaration.get("sha256")
            ):
                raise PackageError(f"shard verification failed: {shard.name}")
            declared_counts[str(lane)] += int(declaration.get("rows") or 0)
    if dict(declared_counts) != manifest.get("counts"):
        raise PackageError("shard totals do not match candidate counts")
    return manifest, audit


def _excerpt(value: str, limit: int = 240) -> str:
    compact = " ".join(value.split())
    return compact if len(compact) <= limit else compact[: limit - 1] + "…"


def _preview_rows(source: Path, manifest: Mapping[str, Any]) -> list[dict[str, Any]]:
    rows: list[dict[str, Any]] = []
    shards = (manifest.get("artifacts") or {}).get("shards") or {}
    for lane in (
        "supervised_train",
        "preference_train",
        "supervised_validation",
        "supervised_test",
    ):
        declarations = shards.get(lane) or []
        if not declarations:
            continue
        for row in _iter_jsonl(source / declarations[0]["path"]):
            assistant = ""
            prompt = str(row.get("prompt") or "")
            if row.get("messages"):
                messages = row["messages"]
                prompt = next(
                    (
                        str(item.get("content") or "")
                        for item in messages
                        if item.get("role") == "user"
                    ),
                    prompt,
                )
                assistant = next(
                    (
                        str(item.get("content") or "")
                        for item in reversed(messages)
                        if item.get("role") == "assistant"
                    ),
                    "",
                )
            else:
                assistant = str(row.get("chosen") or "")
            preview = {
                "lane": lane,
                "id": row.get("id"),
                "split": row.get("split"),
                "curriculum_task": row.get("curriculum_task"),
                "audience": row.get("audience"),
                "presentation_format": row.get("presentation_format"),
                "controlled_failure": row.get("controlled_failure"),
                "parent_row_id": row.get("parent_row_id"),
                "parent_lineage_family_id": row.get("parent_lineage_family_id"),
                "prompt_excerpt": _excerpt(prompt),
                "preferred_response_excerpt": _excerpt(assistant),
                "synthetic": row.get("synthetic"),
                "independent_observation": row.get("independent_observation"),
            }
            if PRIVATE_PATH.search(json.dumps(preview)) or SECRET.search(json.dumps(preview)):
                raise PackageError("safe preview scan found a private path or credential")
            rows.append(preview)
            if sum(item["lane"] == lane for item in rows) == 4:
                break
    return rows


def _artifact_index(root: Path, *, excluded: set[str]) -> dict[str, dict[str, Any]]:
    return {
        path.relative_to(root).as_posix(): {
            "bytes": path.stat().st_size,
            "sha256": _sha256(path),
        }
        for path in sorted(root.rglob("*"))
        if path.is_file() and path.relative_to(root).as_posix() not in excluded
    }


def build_collection(
    source: Path,
    output: Path,
    *,
    dataset_id: str,
    title: str,
    approved_by: str,
    approved_at: str,
    force: bool,
) -> dict[str, Any]:
    source = source.resolve(strict=True)
    if not approved_by.strip():
        raise PackageError("public packaging requires --approved-by")
    try:
        approval_time = datetime.fromisoformat(approved_at.replace("Z", "+00:00"))
    except ValueError as exc:
        raise PackageError("--approved-at must be an ISO-8601 timestamp") from exc
    if approval_time.tzinfo is None:
        raise PackageError("--approved-at must include a time zone")
    approval_time = approval_time.astimezone(UTC)
    output, dataset = _prepare_output(output, force=force)
    manifest, audit = _verify_candidate(source)
    candidate_sha = _sha256(source / "candidate-manifest.json")
    audit_sha = _sha256(source / "quality-audit.json")

    link_modes = Counter()
    for lane, declarations in (manifest["artifacts"]["shards"]).items():
        for declaration in declarations:
            source_path = source / declaration["path"]
            destination = dataset / "data" / lane / source_path.name
            link_modes[_link_or_copy(source_path, destination)] += 1

    shutil.copy2(source / "candidate-manifest.json", dataset / "candidate-manifest.json")
    shutil.copy2(source / "quality-audit.json", dataset / "quality-audit.json")
    if (source / "build-summary.json").is_file():
        shutil.copy2(source / "build-summary.json", dataset / "candidate-build-summary.json")

    preview = _preview_rows(source, manifest)
    _write_json(dataset / "preview.json", preview)
    with (dataset / "preview.csv").open("w", encoding="utf-8", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=list(preview[0]))
        writer.writeheader()
        writer.writerows(preview)

    approval = {
        "schema_version": "duecare.publication_approval.v1",
        "approved_by": approved_by,
        "approved_at": approval_time.isoformat().replace("+00:00", "Z"),
        "source_candidate_manifest_sha256": candidate_sha,
        "quality_audit_sha256": audit_sha,
        "decisions": {
            "curation_review": True,
            "privacy_review": True,
            "license_review": True,
            "quality_review": True,
            "public_redistribution": True,
            "training_use": True,
        },
        "release_license": "CC-BY-4.0",
        "rights_holder": "DueCare project contributors",
        "scope": "exact manifest-bound generated curriculum release",
    }
    _write_json(dataset / "publication-approval.json", approval)

    _write_text(
        dataset / "README.md",
        f"""
# DueCare Measured Response Review Curriculum 200K

This is a public Kaggle and Gemma hackathon learning artifact for teaching
evidence-grounded response review. Start with `preview.csv`, then open the
companion curriculum-atlas notebook. The release contains **207,680 supervised
fine-tuning examples** and **207,680 preference-training pairs**, plus 528
validation examples and 608 test examples.

**Supervised fine-tuning** means training a model to reproduce a preferred
answer for a supplied prompt. **Preference training** means learning from a
preferred response paired with a deliberately flawed response. Every acronym
is expanded on first use in this package.

## What this dataset is

- A deterministic curriculum derived from 791 measured response parents.
- Ten review tasks, eight audiences, four presentation formats, and four
  controlled failure types.
- Manifest-bound, hash-verified, line-delimited JSON for streaming loaders.
- A reproducible teaching corpus for response quality, evidence boundaries,
  uncertainty, privacy, and proportional action.

## What it is not

- It is not 207,680 independent cases or independent human judgments.
- It is not a victim, perpetrator, trafficking, or legal-finding dataset.
- It is contaminated by its benchmark ancestry and cannot independently prove
  model improvement.
- It does not contain hidden chain-of-thought or provider-private reasoning.

The candidate rows retain their pre-release `allow_public_redistribution=false`
field as immutable provenance. Public redistribution is authorized only by
`publication-approval.json` and this exact release manifest.

## Start here

1. Inspect `preview.csv` in Kaggle's tabular viewer.
2. Read `DATA_CARD.md`, `SCHEMA.md`, and `LOADING.md`.
3. Verify `release-manifest.json` before loading shards.
4. Group descendants by `parent_row_sha256` or
   `parent_lineage_family_id`; never split related descendants across training
   and evaluation.

Dataset identity: `{dataset_id}`.
""",
    )
    _write_text(
        dataset / "DATA_CARD.md",
        f"""
# Dataset card

## Purpose

The corpus teaches inspectable response-review skills: evidence grounding,
legal-applicability boundaries, protective refusal, concrete actions, safety
and privacy, score calibration, contrastive comparison, uncertainty,
audience handoff, and publication-claim auditing.

## Composition

| Lane | Rows |
|---|---:|
| Supervised fine-tuning train | {manifest['counts']['supervised_train']:,} |
| Preference train | {manifest['counts']['preference_train']:,} |
| Supervised validation | {manifest['counts']['supervised_validation']:,} |
| Supervised test | {manifest['counts']['supervised_test']:,} |

There are {manifest['parent_counts']['train']:,} training parents,
{manifest['parent_counts']['validation']:,} validation parents, and
{manifest['parent_counts']['test']:,} test parents. Training has 320 structured
views per parent. These views increase controlled coverage, not statistical
independence.

## Intended use

Use for small, bounded training experiments; loader demonstrations; grouped
sampling studies; preference-data tutorials; and safety/claim-boundary
evaluation. Keep hard privacy, authorization, provenance, and current-law
checks outside model weights.

## Prohibited interpretation

Do not use rows as factual determinations about people, prevalence, legal
advice, or independent evidence of model lift. Do not let model output trigger
coercive or adverse action.

## Release evidence

- Candidate manifest SHA-256: `{candidate_sha}`
- Candidate quality audit SHA-256: `{audit_sha}`
- Candidate quality audit clean: `{str(audit['clean']).lower()}`
- Release license: Creative Commons Attribution 4.0 International
""",
    )
    _write_text(
        dataset / "SCHEMA.md",
        """
# Schema

## Supervised fine-tuning rows

The primary target is `messages`, an ordered list of system, user, and
assistant messages. Identity and lineage fields include `id`, `split`,
`parent_row_id`, `parent_row_sha256`, `parent_lineage_family_id`,
`transformation_id`, and `group_weight_key`. Curriculum axes include
`curriculum_task`, `audience`, and `presentation_format`.

## Preference rows

The primary fields are `prompt`, `chosen`, and `rejected`. The chosen answer is
preferred. The rejected answer contains exactly one declared
`controlled_failure`. `negative_only=true` means the rejected answer is a
training contrast, not an approved assistant target.

## Common governance fields

`independent_observation=false` records that descendants are correlated.
`quality_gate` records deterministic checks. `source_refs` and hashes preserve
provenance. Candidate-state publication flags remain unchanged; release-level
authorization lives in `publication-approval.json`.
""",
    )
    _write_text(
        dataset / "LOADING.md",
        """
# Loading and unloading

## Hugging Face Datasets streaming

```python
from datasets import load_dataset

rows = load_dataset(
    "json",
    data_files="/kaggle/input/duecare-measured-review-curriculum-200k/data/supervised_train/*.jsonl",
    split="train",
    streaming=True,
)
print(next(iter(rows)))
```

## Polars lazy scan

```python
import polars as pl

rows = pl.scan_ndjson(
    "/kaggle/input/duecare-measured-review-curriculum-200k/data/preference_train/*.jsonl"
)
print(rows.select("curriculum_task", "audience").group_by("curriculum_task").len().collect())
```

## pandas chunked loading

```python
import pandas as pd

for chunk in pd.read_json("one-shard.jsonl", lines=True, chunksize=1_000):
    print(chunk[["curriculum_task", "audience"]].head())
    break
```

Delete dataframe references and run Python garbage collection between large
shards when memory is constrained. Streaming or lazy loading is recommended;
do not concatenate every shard on a small machine.
""",
    )
    _write_text(
        dataset / "LIMITATIONS.md",
        """
# Limitations

- Row count is not independent sample size. Descendants share measured parents.
- The source benchmark and generated targets are related, so this corpus cannot
  independently establish model improvement.
- Synthetic recomposition can amplify stylistic regularities and source-model
  errors.
- Synonym replacement alone is not treated as new evidence.
- Legal and resource information can change and must be retrieved from current,
  versioned sources at use time.
- Validation and test lanes diagnose transfer within the generator design; they
  are not real-world deployment evaluations.
""",
    )
    _write_text(
        dataset / "SOURCES.md",
        """
# Sources and lineage

Rows are deterministic transformations of the public DueCare measured-response
training corpus. Each row carries source-response hashes, parent row identity,
source references, generator version, and inherited split. The source release
is itself a Kaggle/Gemma hackathon learning artifact. Consult each row's
`source_refs` before relying on any authority statement; a citation is not a
legal determination.
""",
    )
    _write_text(
        dataset / "LICENSE",
        """
Creative Commons Attribution 4.0 International (CC BY 4.0)

DueCare-authored metadata, generated curriculum rows, documentation, and
previews are released under CC BY 4.0. Attribution must identify DueCare
project contributors. External sources remain governed by their own terms;
this release does not relicense third-party source documents or model weights.
""",
    )
    _write_text(
        dataset / "CITATION.cff",
        f"""
cff-version: 1.2.0
message: "If you use this curriculum, cite this dataset and its exact release manifest."
title: "{title}"
type: dataset
authors:
  - family-names: "Samarel"
    given-names: "Taylor"
date-released: "{approval_time.date().isoformat()}"
license: CC-BY-4.0
repository-code: "https://github.com/taylorsamarel/gemma4-comp"
""",
    )

    shard_index = {
        lane: [
            {
                **declaration,
                "path": f"data/{lane}/{Path(declaration['path']).name}",
            }
            for declaration in declarations
        ]
        for lane, declarations in manifest["artifacts"]["shards"].items()
    }
    _write_json(dataset / "shard-index.json", shard_index)
    _write_json(
        dataset / "mlcroissant.json",
        {
            "@context": "https://schema.org/",
            "@type": "Dataset",
            "name": title,
            "description": (
                "Manifest-bound synthetic response-review curriculum with grouped lineage."
            ),
            "license": "https://creativecommons.org/licenses/by/4.0/",
            "url": f"https://www.kaggle.com/datasets/{dataset_id}",
            "keywords": [
                "supervised fine-tuning",
                "preference training",
                "synthetic data",
                "data lineage",
                "Gemma",
            ],
            "distribution": [
                {
                    "@type": "DataDownload",
                    "name": lane,
                    "encodingFormat": "application/x-ndjson",
                    "contentUrl": f"data/{lane}/*.jsonl",
                }
                for lane in shard_index
            ],
        },
    )
    _write_json(
        dataset / "dataset-metadata.json",
        {
            "id": dataset_id,
            "title": title,
            "subtitle": (
                "207,680 supervised examples and 207,680 preference pairs with explicit lineage"
            ),
            "description": (
                "A public Kaggle/Gemma learning curriculum for evidence-grounded response review."
            ),
            "licenses": [{"name": "CC-BY-4.0"}],
            "keywords": ["artificial intelligence", "education", "nlp", "synthetic data"],
            "isPrivate": False,
        },
    )

    excluded = {"release-manifest.json"}
    artifacts = _artifact_index(dataset, excluded=excluded)
    release = {
        "schema_version": SCHEMA,
        "dataset_id": dataset_id,
        "title": title,
        "publication_state": "approved_public_release",
        "safe_to_train": True,
        "safe_to_publish": True,
        "public": True,
        "candidate_manifest_sha256": candidate_sha,
        "quality_audit_sha256": audit_sha,
        "publication_approval_sha256": _sha256(dataset / "publication-approval.json"),
        "counts": manifest["counts"],
        "parent_counts": manifest["parent_counts"],
        "independent_observation": False,
        "contamination_boundary": manifest["contamination_boundary"],
        "artifact_count": len(artifacts),
        "artifacts": artifacts,
        "release_payload_sha256": _canonical_sha256(artifacts),
        "local_materialization": dict(link_modes),
        "claims": {
            "gpu_training_ran": False,
            "adapter_produced": False,
            "independent_model_lift_demonstrated": False,
        },
    }
    _write_json(dataset / "release-manifest.json", release)
    summary = {
        "dataset_dir": str(dataset),
        "dataset_id": dataset_id,
        "counts": manifest["counts"],
        "candidate_manifest_sha256": candidate_sha,
        "release_manifest_sha256": _sha256(dataset / "release-manifest.json"),
        "release_payload_sha256": release["release_payload_sha256"],
        "safe_to_publish": True,
        "local_materialization": dict(link_modes),
    }
    _write_json(output / "collection-manifest.json", summary)
    return summary


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--source", type=Path, default=DEFAULT_SOURCE)
    parser.add_argument("--output", type=Path, default=DEFAULT_OUTPUT)
    parser.add_argument("--dataset-id", default=DEFAULT_DATASET_ID)
    parser.add_argument("--title", default=DEFAULT_TITLE)
    parser.add_argument("--approved-by", required=True)
    parser.add_argument("--approved-at", required=True)
    parser.add_argument("--force", action="store_true")
    return parser


def main(argv: Sequence[str] | None = None) -> int:
    args = build_parser().parse_args(argv)
    summary = build_collection(
        args.source,
        args.output,
        dataset_id=args.dataset_id,
        title=args.title,
        approved_by=args.approved_by,
        approved_at=args.approved_at,
        force=args.force,
    )
    print(json.dumps(summary, indent=2, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
