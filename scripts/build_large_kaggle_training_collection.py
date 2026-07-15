#!/usr/bin/env python3
# ruff: noqa: E501
"""Build a private-first Kaggle collection from a large DueCare candidate.

The input is the manifest-bound, sharded candidate emitted by
``build_large_multiperspective_training_bundle.py``.  This builder deliberately
does not publish anything.  It streams source shards through a disk-backed
SQLite index, writes deterministic bounded-size public shards, emits rich
dataset documentation, and creates two CPU-safe Kaggle notebooks.

Candidate output is private and ``safe_to_publish=false`` by default.  Passing
``--public-ready`` requires a separate approval whose source-manifest and
quality-audit hashes match the exact candidate.  Generation never self-approves.
"""

from __future__ import annotations

import argparse
import csv
import hashlib
import json
import math
import os
import re
import shutil
import sqlite3
import subprocess
import sys
import tempfile
import time
from collections import Counter
from collections.abc import Iterable, Mapping, Sequence
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[1]
CHAT_SRC = ROOT / "packages" / "duecare-llm-chat" / "src"
if str(CHAT_SRC) not in sys.path:
    sys.path.insert(0, str(CHAT_SRC))

from duecare.chat.training_contract import (  # noqa: E402
    canonical_sha256,
    pii_findings,
    training_row_sha256,
)

CANDIDATE_SCHEMA = "duecare.large_multiperspective.candidate.v1"
APPROVAL_KIND = "duecare.training.publication_approval.v1"
APPROVAL_SCHEMA = "1.0"
COLLECTION_SCHEMA = "duecare.kaggle.large_training_collection.v1"
RELEASE_SCHEMA = "duecare.kaggle.large_training_release.v1"
SHARD_INDEX_SCHEMA = "duecare.kaggle.large_shard_index.v1"
DEFAULT_DATASET_ID = "taylorsamarel/duecare-multiperspective-finetuning-corpus"
DEFAULT_TITLE = "DueCare Multiperspective Fine-Tuning Corpus"
DEFAULT_OUTPUT_ROOT = ROOT / "reports" / "kaggle_publish" / "large_training_collection"
DEFAULT_SHARD_TARGET_ROWS = 4096
DEFAULT_MODEL_SOURCE = "google/gemma-4/Transformers/gemma-4-e2b-it/1"
INTEGRITY_NOTEBOOK_ID = "taylorsamarel/duecare-large-corpus-integrity-and-exploration"
TRAINING_PLAN_NOTEBOOK_ID = "taylorsamarel/duecare-gemma-4-large-corpus-plan-and-smoke"
VISUAL_EXPLORER_NOTEBOOK_ID = "taylorsamarel/duecare-large-corpus-visual-explorer"
ALLOWED_LICENSES = {"CC-BY-SA-4.0", "CC-BY-4.0", "apache-2.0"}
COMMIT_RENAME_RETRY_DELAYS_SECONDS = (0.05, 0.1, 0.2, 0.4, 0.8, 1.6, 3.2)

LANES: dict[str, dict[str, str]] = {
    "sft_train": {"prefix": "sft-train", "split": "train", "kind": "sft"},
    "preference_train": {
        "prefix": "preference-train",
        "split": "train",
        "kind": "preference",
    },
    "sft_validation": {
        "prefix": "sft-validation",
        "split": "validation",
        "kind": "sft",
    },
    "sft_test": {"prefix": "sft-test", "split": "test", "kind": "sft"},
}

_HEX40 = re.compile(r"[0-9a-f]{40}")
_HEX64 = re.compile(r"[0-9a-f]{64}")
_DATASET_ID = re.compile(r"[a-z0-9][a-z0-9_-]*/[a-z0-9][a-z0-9-]{2,49}")
_PRIVATE_PATH = re.compile(
    r"(?i)(?:[A-Z]:[/\\]Users[/\\][^/\\\s]+|/home/[^/\s]+/|"
    r"(?:^|[/\\])(?:AppData|OneDrive)(?:[/\\]|$)|(?:file|s3|ftp):/{1,3})"
)
_SECRET_LITERAL = re.compile(
    r"(?i)(?:AKIA[0-9A-Z]{16}|ASIA[0-9A-Z]{16}|"
    r"gh[pousr]_[A-Za-z0-9_]{20,}|github_pat_[A-Za-z0-9_]{20,}|"
    r"sk-(?:proj-)?[A-Za-z0-9_-]{20,}|hf_[A-Za-z0-9]{20,}|"
    r"AIza[0-9A-Za-z_-]{35}|xox[baprs]-[A-Za-z0-9-]{10,}|"
    r"-----BEGIN(?: RSA| EC| OPENSSH)? PRIVATE KEY-----)"
)
_HIDDEN_REASONING = re.compile(
    r"<\|?(?:think|thought)(?:\|?>)|"
    r"<\|?channel\|?>\s*(?:analysis|thought)|"
    r"\b(?:hidden|private)\s+chain[- ]of[- ]thought\b|"
    r"\bprivate\s+scratchpad\b",
    re.I,
)
_PRIVATE_KEYS = {
    "chain_of_thought",
    "hidden_chain_of_thought",
    "private_reasoning",
    "provider_private_reasoning",
    "runtime_trace",
    "raw_provider_response",
    "api_key",
    "access_token",
}


class CollectionError(ValueError):
    """Raised when a candidate cannot safely become a Kaggle collection."""


def _sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def _write_json(path: Path, value: Any) -> None:
    path.write_text(
        json.dumps(value, ensure_ascii=False, indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
        newline="\n",
    )


def _read_json(path: Path, *, label: str) -> dict[str, Any]:
    if path.is_symlink() or not path.is_file():
        raise CollectionError(f"{label} is missing or symlinked: {path}")
    try:
        value = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as exc:
        raise CollectionError(f"{label} is not valid JSON: {path}") from exc
    if not isinstance(value, dict):
        raise CollectionError(f"{label} must be a JSON object: {path}")
    return value


def _contained(path: Path, root: Path) -> bool:
    try:
        path.resolve().relative_to(root.resolve())
    except ValueError:
        return False
    return True


def _resolve_source_file(manifest_path: Path, raw: Any, *, label: str) -> Path:
    if isinstance(raw, Mapping):
        raw = raw.get("path") or raw.get("file")
    if not isinstance(raw, str) or not raw.strip():
        raise CollectionError(f"candidate manifest is missing {label} path")
    root = manifest_path.parent.resolve()
    unresolved = root / raw
    if unresolved.is_symlink():
        raise CollectionError(f"{label} escapes the candidate or is not a regular file")
    try:
        path = unresolved.resolve(strict=True)
    except OSError as exc:
        raise CollectionError(f"{label} escapes the candidate or is not a regular file") from exc
    if not _contained(path, root) or not path.is_file():
        raise CollectionError(f"{label} escapes the candidate or is not a regular file")
    return path


def _artifact_sha(raw: Any) -> str | None:
    if isinstance(raw, Mapping):
        value = raw.get("sha256")
        return value if isinstance(value, str) else None
    return raw if isinstance(raw, str) and _HEX64.fullmatch(raw) else None


def _shard_declarations(manifest: Mapping[str, Any], lane: str) -> list[Any]:
    artifacts = manifest.get("artifacts")
    if not isinstance(artifacts, Mapping):
        raise CollectionError("candidate manifest artifacts must be an object")
    shards = artifacts.get("shards")
    if not isinstance(shards, Mapping):
        shards = manifest.get("shards")
    if not isinstance(shards, Mapping):
        raise CollectionError("candidate manifest is missing artifacts.shards")
    declared = shards.get(lane)
    if not isinstance(declared, list) or not declared:
        raise CollectionError(f"candidate manifest has no declared shards for {lane}")
    return declared


def _verify_declared_file(path: Path, declaration: Any, *, label: str) -> None:
    expected = _artifact_sha(declaration)
    if not expected or not _HEX64.fullmatch(expected):
        raise CollectionError(f"{label} is missing a valid sha256")
    actual = _sha256_file(path)
    if actual != expected:
        raise CollectionError(f"{label} sha256 mismatch")
    if isinstance(declaration, Mapping):
        expected_bytes = declaration.get("bytes")
        if expected_bytes is not None and expected_bytes != path.stat().st_size:
            raise CollectionError(f"{label} byte count mismatch")


def _metadata_artifact(
    manifest_path: Path,
    manifest: Mapping[str, Any],
    *names: str,
) -> tuple[Path, Any] | None:
    artifacts = manifest.get("artifacts")
    metadata = artifacts.get("metadata") if isinstance(artifacts, Mapping) else None
    for name in names:
        candidates = (
            manifest.get(name),
            metadata.get(name) if isinstance(metadata, Mapping) else None,
            artifacts.get(name) if isinstance(artifacts, Mapping) else None,
        )
        for raw in candidates:
            if raw is not None:
                return _resolve_source_file(manifest_path, raw, label=name), raw
    return None


def _private_key_paths(value: Any, prefix: str = "") -> list[str]:
    findings: list[str] = []
    if isinstance(value, Mapping):
        for key, child in value.items():
            key_text = str(key).lower()
            child_path = f"{prefix}.{key_text}" if prefix else key_text
            if key_text in _PRIVATE_KEYS:
                findings.append(child_path)
            findings.extend(_private_key_paths(child, child_path))
    elif isinstance(value, Sequence) and not isinstance(value, (str, bytes, bytearray)):
        for index, child in enumerate(value):
            findings.extend(_private_key_paths(child, f"{prefix}[{index}]"))
    return findings


def _strings(value: Any) -> Iterable[str]:
    if isinstance(value, str):
        yield value
    elif isinstance(value, Mapping):
        for key, child in value.items():
            yield str(key)
            yield from _strings(child)
    elif isinstance(value, Sequence) and not isinstance(value, (str, bytes, bytearray)):
        for child in value:
            yield from _strings(child)


def _contains_private_path_or_secret(value: Any) -> bool:
    return any(
        _PRIVATE_PATH.search(text) or _SECRET_LITERAL.search(text) for text in _strings(value)
    )


def _prompt(row: Mapping[str, Any], kind: str) -> str:
    if kind == "preference":
        value = row.get("prompt")
        return value.strip() if isinstance(value, str) else ""
    messages = row.get("messages")
    if not isinstance(messages, list):
        return ""
    prompts = [
        item.get("content", "").strip()
        for item in messages
        if isinstance(item, Mapping)
        and item.get("role") == "user"
        and isinstance(item.get("content"), str)
    ]
    return prompts[-1] if prompts else ""


def _answer_chars(row: Mapping[str, Any], kind: str) -> int:
    if kind == "preference":
        return len(str(row.get("chosen") or "")) + len(str(row.get("rejected") or ""))
    messages = row.get("messages")
    if not isinstance(messages, list):
        return 0
    return sum(
        len(str(item.get("content") or ""))
        for item in messages
        if isinstance(item, Mapping) and item.get("role") == "assistant"
    )


def _validate_row(
    row: Mapping[str, Any],
    *,
    lane: str,
    model_id: str,
    model_revision: str,
) -> tuple[str, str, str, str, str]:
    spec = LANES[lane]
    row_id = str(row.get("id") or "").strip()
    lineage_id = str(row.get("lineage_id") or "").strip()
    family_id = str(row.get("lineage_family_id") or "").strip()
    if not row_id or not lineage_id or not family_id:
        raise CollectionError(f"{lane} row is missing id or lineage metadata")
    if row.get("split") != spec["split"]:
        raise CollectionError(f"{lane} row {row_id} has the wrong split")
    if row.get("synthetic") is not True or row.get("pii_checked") is not True:
        raise CollectionError(f"{lane} row {row_id} lacks synthetic/PII declarations")
    if row.get("allow_training_use") is not True:
        raise CollectionError(f"{lane} row {row_id} is not approved for training use")
    if row.get("allow_public_redistribution") is not True:
        raise CollectionError(f"{lane} row {row_id} disallows public redistribution")
    license_name = str(row.get("license") or "")
    if license_name not in ALLOWED_LICENSES:
        raise CollectionError(f"{lane} row {row_id} has an unsupported license")
    quality = row.get("quality_gate")
    if not isinstance(quality, Mapping) or quality.get("accepted") is not True:
        raise CollectionError(f"{lane} row {row_id} did not pass its quality gate")
    if quality.get("unsafe_advice_filtered") is not True:
        raise CollectionError(f"{lane} row {row_id} lacks the unsafe-advice gate")
    checks = quality.get("checks")
    if isinstance(checks, Mapping) and any(value is not True for value in checks.values()):
        raise CollectionError(f"{lane} row {row_id} contains a failed quality check")
    if pii_findings(row):
        raise CollectionError(f"{lane} row {row_id} triggered the PII detector")
    if _contains_private_path_or_secret(row):
        raise CollectionError(f"{lane} row {row_id} contains a private path or credential")
    if any(_HIDDEN_REASONING.search(text) for text in _strings(row)):
        raise CollectionError(f"{lane} row {row_id} contains hidden-reasoning markup")
    if _private_key_paths(row):
        raise CollectionError(f"{lane} row {row_id} contains private-reasoning fields")
    if row.get("sha256") != training_row_sha256(row):
        raise CollectionError(f"{lane} row {row_id} has an invalid row sha256")
    row_model = str(row.get("target_model_id") or row.get("model_id") or "")
    row_revision = str(
        row.get("target_model_revision") or row.get("model_revision") or ""
    )
    if row_model != model_id or row_revision != model_revision:
        raise CollectionError(f"{lane} row {row_id} violates the model contract")
    prompt = _prompt(row, spec["kind"])
    if not prompt:
        raise CollectionError(f"{lane} row {row_id} has no user prompt")
    if spec["kind"] == "preference":
        if not all(isinstance(row.get(key), str) and row[key].strip() for key in ("chosen", "rejected")):
            raise CollectionError(f"{lane} row {row_id} has an incomplete preference pair")
        if row["chosen"].strip() == row["rejected"].strip():
            raise CollectionError(f"{lane} row {row_id} has identical preference candidates")
    sort_key = canonical_sha256(lineage_id)
    return row_id, lineage_id, family_id, canonical_sha256(prompt), sort_key


def _candidate_metadata(
    manifest_path: Path,
) -> tuple[dict[str, Any], dict[str, Any], Path, dict[str, Any]]:
    manifest = _read_json(manifest_path, label="candidate manifest")
    if manifest.get("schema_version") != CANDIDATE_SCHEMA:
        raise CollectionError(
            f"candidate schema must be {CANDIDATE_SCHEMA!r}, got {manifest.get('schema_version')!r}"
        )
    if manifest.get("publication_status") != "candidate_only_not_approved":
        raise CollectionError("candidate manifest has an unexpected publication status")
    if manifest.get("safe_to_publish") is not False:
        raise CollectionError("input must remain an unapproved candidate")
    if manifest.get("safe_to_train") is not True:
        raise CollectionError("candidate is not safe_to_train")

    quality_artifact = _metadata_artifact(
        manifest_path, manifest, "quality_audit", "quality-audit"
    )
    if quality_artifact is None:
        raise CollectionError("candidate manifest is missing quality_audit")
    quality_path, quality_declaration = quality_artifact
    _verify_declared_file(quality_path, quality_declaration, label="quality audit")
    quality = _read_json(quality_path, label="quality audit")
    if quality.get("clean") is not True or quality.get("risk_flags") not in ([], None):
        raise CollectionError("candidate quality audit is not clean")
    if _contains_private_path_or_secret(manifest) or _contains_private_path_or_secret(quality):
        raise CollectionError("candidate metadata contains a private path or credential")
    return manifest, quality, quality_path, dict(manifest.get("artifacts") or {})


def _verify_approval(
    approval_path: Path,
    *,
    manifest_path: Path,
    manifest: Mapping[str, Any],
    quality_path: Path,
) -> dict[str, Any]:
    approval = _read_json(approval_path, label="publication approval")
    if approval.get("schema_version") != APPROVAL_SCHEMA:
        raise CollectionError("publication approval schema_version is invalid")
    if approval.get("handoff_kind") != APPROVAL_KIND:
        raise CollectionError("publication approval handoff_kind is invalid")
    manifest_sha = _sha256_file(manifest_path)
    bound_sha = approval.get("source_manifest_sha256") or approval.get(
        "candidate_manifest_sha256"
    )
    if bound_sha != manifest_sha:
        raise CollectionError("publication approval is not bound to this candidate manifest")
    approved_by = str(approval.get("approved_by") or "").strip()
    approved_at = str(approval.get("approved_at") or "").strip()
    if not approved_by or not approved_at or pii_findings({"approved_by": approved_by}):
        raise CollectionError("publication approval lacks reviewer identity or date")
    rights_holder = str(approval.get("rights_holder") or "").strip()
    if not rights_holder or pii_findings({"rights_holder": rights_holder}):
        raise CollectionError("publication approval rights holder is missing or unsafe")
    if _contains_private_path_or_secret(approval):
        raise CollectionError("publication approval contains a private path or credential")
    if approval.get("allow_training_use") is not True:
        raise CollectionError("publication approval disallows training use")
    if approval.get("allow_public_redistribution") is not True:
        raise CollectionError("publication approval disallows public redistribution")
    approvals = approval.get("approvals")
    required = {
        "curator_approved",
        "privacy_approved",
        "license_approved",
        "quality_approved",
        "public_redistribution_approved",
    }
    if not isinstance(approvals, Mapping) or any(
        approvals.get(key) is not True for key in required
    ):
        raise CollectionError("publication approval is missing required decisions")
    row_license = str(approval.get("row_license") or "")
    if row_license not in ALLOWED_LICENSES or approval.get("release_license") != row_license:
        raise CollectionError("publication approval license is invalid")
    quality_approval = approval.get("quality_audit")
    if not isinstance(quality_approval, Mapping):
        raise CollectionError("publication approval lacks quality-audit binding")
    if quality_approval.get("clean") is not True or quality_approval.get("risk_flags") not in (
        [],
        None,
    ):
        raise CollectionError("publication approval does not accept a clean quality audit")
    if quality_approval.get("artifact_sha256") != _sha256_file(quality_path):
        raise CollectionError("publication approval quality-audit hash mismatch")
    prompt_scope = manifest.get("prompt_scope")
    if prompt_scope is not None and approval.get("prompt_scope") != prompt_scope:
        raise CollectionError("publication approval prompt scope does not match the candidate")
    return approval


def _reject_link_components(path: Path, *, label: str) -> None:
    current = Path(os.path.abspath(path))
    while True:
        if current.is_symlink() or (
            current.exists()
            and hasattr(current, "is_junction")
            and current.is_junction()
        ):
            raise CollectionError(f"{label} contains a symlink or junction")
        if current.parent == current:
            return
        current = current.parent


def _prepare_staging(output_root: Path, *, force: bool) -> tuple[Path, Path]:
    output = Path(os.path.abspath(output_root))
    _reject_link_components(output, label="output path")
    if output == Path(output.anchor):
        raise CollectionError("unsafe output path")
    protected = {ROOT.resolve(), Path.home().resolve(), ROOT.resolve().parent}
    if output.resolve() in protected:
        raise CollectionError("refusing to replace a workspace, home, or workspace parent")
    if output.exists() and any(output.iterdir()):
        if not force:
            raise CollectionError(f"output directory is not empty: {output}")
        marker = output / ".duecare-large-kaggle-collection"
        if (
            not marker.is_file()
            or marker.read_text(encoding="utf-8").strip() != COLLECTION_SCHEMA
        ):
            raise CollectionError("--force refused: output lacks the DueCare ownership marker")
    output.parent.mkdir(parents=True, exist_ok=True)
    staging = Path(
        tempfile.mkdtemp(prefix=f".{output.name}-building-", dir=output.parent)
    )
    return output, staging


def _initialize_output(root: Path) -> Path:
    root.mkdir(parents=True, exist_ok=True)
    marker = root / ".duecare-large-kaggle-collection"
    marker.write_text(COLLECTION_SCHEMA + "\n", encoding="utf-8", newline="\n")
    return root


def _rename_with_transient_lock_retry(source: Path, target: Path) -> None:
    for delay in (*COMMIT_RENAME_RETRY_DELAYS_SECONDS, None):
        try:
            source.rename(target)
            return
        except PermissionError:
            if delay is None:
                raise
            time.sleep(delay)


def _tree_fingerprints(root: Path) -> dict[str, tuple[int, str]]:
    result: dict[str, tuple[int, str]] = {}
    for path in sorted(root.rglob("*")):
        if path.is_symlink() or (
            path.exists() and hasattr(path, "is_junction") and path.is_junction()
        ):
            raise CollectionError("collection tree contains a symlink or junction")
        if path.is_file():
            result[path.relative_to(root).as_posix()] = (
                path.stat().st_size,
                _sha256_file(path),
            )
    return result


def _copy_commit_staging(staging: Path, output: Path) -> None:
    marker_name = "collection-manifest.json"
    marker = staging / marker_name
    if not marker.is_file():
        raise CollectionError("staging collection marker is missing")
    if output.exists() or output.is_symlink():
        raise CollectionError("copy commit requires an absent destination")

    output.mkdir(parents=False)
    try:
        for source in sorted(staging.iterdir(), key=lambda path: path.name):
            if source.name == marker_name:
                continue
            destination = output / source.name
            if source.is_symlink() or (
                source.exists()
                and hasattr(source, "is_junction")
                and source.is_junction()
            ):
                raise CollectionError("staging collection contains a link")
            if source.is_dir():
                shutil.copytree(source, destination)
            elif source.is_file():
                shutil.copy2(source, destination)
            else:
                raise CollectionError("staging collection contains an unsupported entry")
        # This is the trust marker for a complete local collection, so expose
        # it only after every payload file has been copied.
        shutil.copy2(marker, output / marker_name)
        if _tree_fingerprints(staging) != _tree_fingerprints(output):
            raise CollectionError("verified copy commit does not match staging bytes")
    except Exception:
        shutil.rmtree(output, ignore_errors=True)
        raise


def _commit_staging(staging: Path, output: Path) -> None:
    backup: Path | None = None
    if output.exists():
        backup = output.with_name(f".{output.name}-previous")
        if backup.exists() or backup.is_symlink():
            raise CollectionError("cannot replace output while a prior backup exists")
        _rename_with_transient_lock_retry(output, backup)
    try:
        try:
            _rename_with_transient_lock_retry(staging, output)
        except PermissionError:
            _copy_commit_staging(staging, output)
            shutil.rmtree(staging, ignore_errors=True)
    except Exception:
        if output.exists():
            shutil.rmtree(output, ignore_errors=True)
        if backup is not None and backup.exists() and not output.exists():
            _rename_with_transient_lock_retry(backup, output)
        raise
    if backup is not None:
        shutil.rmtree(backup, ignore_errors=True)


def _repo_provenance(explicit: str) -> dict[str, Any]:
    value = explicit.strip().lower()
    if not value:
        proc = subprocess.run(
            ["git", "rev-parse", "HEAD"],
            cwd=ROOT,
            check=False,
            capture_output=True,
            text=True,
        )
        value = proc.stdout.strip().lower() if proc.returncode == 0 else ""
    if not _HEX40.fullmatch(value):
        raise CollectionError("--repo-commit must resolve to one immutable 40-character commit")

    relative = Path(__file__).resolve().relative_to(ROOT).as_posix()
    at_commit = subprocess.run(
        ["git", "show", f"{value}:{relative}"],
        cwd=ROOT,
        check=False,
        capture_output=True,
    )
    status = subprocess.run(
        ["git", "status", "--porcelain", "--untracked-files=all"],
        cwd=ROOT,
        check=False,
        capture_output=True,
    )
    generator_sha = _sha256_file(Path(__file__))
    committed_sha = (
        hashlib.sha256(at_commit.stdout).hexdigest()
        if at_commit.returncode == 0
        else None
    )
    generator_matches = committed_sha == generator_sha
    worktree_clean = status.returncode == 0 and not status.stdout.strip()
    return {
        "commit": value,
        "generator_path": relative,
        "generator_sha256": generator_sha,
        "generator_tracked_at_commit": at_commit.returncode == 0,
        "generator_sha256_at_commit": committed_sha,
        "generator_matches_commit": generator_matches,
        "worktree_clean": worktree_clean,
        "reproducible_from_commit_alone": worktree_clean and generator_matches,
        "state": (
            "clean_commit"
            if worktree_clean and generator_matches
            else "uncommitted_worktree_explicitly_recorded"
        ),
    }


def _dataset_identity(dataset_id: str, title: str) -> None:
    if not _DATASET_ID.fullmatch(dataset_id):
        raise CollectionError("dataset id must be owner/slug with a 3-50 character slug")
    if not 6 <= len(title) <= 50:
        raise CollectionError("dataset title must contain 6-50 characters")


def _verify_metadata_content(path: Path, *, label: str) -> None:
    def verify(value: Any) -> None:
        if pii_findings(value):
            raise CollectionError(f"{label} triggered the PII detector")
        if _contains_private_path_or_secret(value):
            raise CollectionError(f"{label} contains a private path or credential")
        if _private_key_paths(value):
            raise CollectionError(f"{label} contains private-reasoning fields")

    if path.suffix == ".jsonl":
        with path.open("r", encoding="utf-8") as handle:
            for line_number, line in enumerate(handle, 1):
                if not line.strip():
                    continue
                try:
                    value = json.loads(line)
                except json.JSONDecodeError as exc:
                    raise CollectionError(f"{label} line {line_number} is invalid JSON") from exc
                verify(value)
        return
    verify(_read_json(path, label=label))


def _copy_verified_metadata(
    dataset_dir: Path,
    manifest_path: Path,
    manifest: Mapping[str, Any],
    names: Sequence[tuple[str, tuple[str, ...]]],
) -> dict[str, dict[str, Any]]:
    copied: dict[str, dict[str, Any]] = {}
    for output_name, aliases in names:
        artifact = _metadata_artifact(manifest_path, manifest, *aliases)
        if artifact is None:
            continue
        source, declaration = artifact
        _verify_declared_file(source, declaration, label=output_name)
        _verify_metadata_content(source, label=output_name)
        target = dataset_dir / output_name
        shutil.copyfile(source, target)
        copied[output_name] = {
            "sha256": _sha256_file(target),
            "bytes": target.stat().st_size,
        }
    return copied


def _insert_source_rows(
    conn: sqlite3.Connection,
    *,
    manifest_path: Path,
    manifest: Mapping[str, Any],
) -> tuple[
    dict[str, int],
    dict[str, dict[str, dict[str, int]]],
    set[str],
    set[str],
    set[str],
]:
    model = manifest.get("model") or manifest.get("target_model")
    if not isinstance(model, Mapping):
        raise CollectionError("candidate manifest lacks the target model contract")
    model_id = str(model.get("id") or "")
    model_revision = str(model.get("revision") or "")
    if not model_id or not _HEX40.fullmatch(model_revision):
        raise CollectionError("candidate model id/revision is not immutable")

    counts: dict[str, int] = {}
    coverage: dict[str, dict[str, dict[str, int]]] = {}
    licenses: set[str] = set()
    rights_holders: set[str] = set()
    row_sources: set[str] = set()
    conn.execute("BEGIN")
    for lane, spec in LANES.items():
        lane_count = 0
        lane_coverage: dict[str, Counter[str]] = {
            key: Counter()
            for key in (
                "perspective",
                "journey_stage",
                "temporal_lens",
                "evidence_state",
                "view_mode",
                "jurisdiction_pattern",
                "lineage_family_id",
                "response_style",
                "controlled_failure",
            )
        }
        for shard_number, declaration in enumerate(_shard_declarations(manifest, lane)):
            source_path = _resolve_source_file(
                manifest_path, declaration, label=f"{lane} shard {shard_number}"
            )
            _verify_declared_file(
                source_path, declaration, label=f"{lane} shard {shard_number}"
            )
            source_rows = 0
            with source_path.open("r", encoding="utf-8", newline="") as handle:
                for line_number, raw_line in enumerate(handle, 1):
                    if not raw_line.strip():
                        continue
                    try:
                        row = json.loads(raw_line)
                    except json.JSONDecodeError as exc:
                        raise CollectionError(
                            f"{lane} shard {shard_number} line {line_number} is invalid JSON"
                        ) from exc
                    if not isinstance(row, dict):
                        raise CollectionError(f"{lane} row must be a JSON object")
                    row_id, lineage_id, family_id, prompt_sha, sort_key = _validate_row(
                        row,
                        lane=lane,
                        model_id=model_id,
                        model_revision=model_revision,
                    )
                    payload = json.dumps(
                        row, ensure_ascii=False, sort_keys=True, separators=(",", ":")
                    )
                    try:
                        conn.execute(
                            """
                            INSERT INTO rows
                              (lane, sort_key, row_id, lineage_id, family_id,
                               prompt_sha, prompt_chars, answer_chars, payload)
                            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
                            """,
                            (
                                lane,
                                sort_key,
                                row_id,
                                lineage_id,
                                family_id,
                                prompt_sha,
                                len(_prompt(row, spec["kind"])),
                                _answer_chars(row, spec["kind"]),
                                payload,
                            ),
                        )
                    except sqlite3.IntegrityError as exc:
                        raise CollectionError(f"duplicate id or prompt in {lane}: {row_id}") from exc
                    licenses.add(str(row["license"]))
                    rights_holder = str(row.get("rights_holder") or "").strip()
                    if not rights_holder or pii_findings({"rights_holder": rights_holder}):
                        raise CollectionError(f"{lane} row {row_id} lacks a safe rights holder")
                    rights_holders.add(rights_holder)
                    for source_key in ("source_refs", "knowledge_pack_refs"):
                        raw_sources = row.get(source_key)
                        if isinstance(raw_sources, list):
                            row_sources.update(
                                str(value)
                                for value in raw_sources
                                if isinstance(value, str)
                                and value.startswith(("https://", "repo:"))
                            )
                    for key, counter in lane_coverage.items():
                        value = row.get(key)
                        if value not in (None, ""):
                            counter[str(value)] += 1
                    lane_count += 1
                    source_rows += 1
            if (
                isinstance(declaration, Mapping)
                and declaration.get("rows") is not None
                and declaration.get("rows") != source_rows
            ):
                raise CollectionError(f"{lane} source shard row count mismatch")
        counts[lane] = lane_count
        coverage[lane] = {
            key: dict(sorted(counter.items()))
            for key, counter in lane_coverage.items()
            if counter
        }
    conn.commit()
    if any(count <= 0 for count in counts.values()):
        raise CollectionError("every required lane must contain rows")
    return counts, coverage, licenses, rights_holders, row_sources


def _scalar(conn: sqlite3.Connection, query: str, params: Sequence[Any] = ()) -> int:
    value = conn.execute(query, tuple(params)).fetchone()
    return int(value[0]) if value else 0


def _verify_split_contract(conn: sqlite3.Connection, manifest: Mapping[str, Any]) -> dict[str, Any]:
    for lane in LANES:
        duplicates = _scalar(
            conn,
            "SELECT COUNT(*) - COUNT(DISTINCT prompt_sha) FROM rows WHERE lane = ?",
            (lane,),
        )
        if duplicates:
            raise CollectionError(f"{lane} contains duplicate prompts")

    missing_preferences = _scalar(
        conn,
        """
        SELECT COUNT(*) FROM (
          SELECT prompt_sha FROM rows WHERE lane='sft_train'
          EXCEPT SELECT prompt_sha FROM rows WHERE lane='preference_train'
        )
        """,
    )
    missing_sft = _scalar(
        conn,
        """
        SELECT COUNT(*) FROM (
          SELECT prompt_sha FROM rows WHERE lane='preference_train'
          EXCEPT SELECT prompt_sha FROM rows WHERE lane='sft_train'
        )
        """,
    )
    if missing_preferences or missing_sft:
        raise CollectionError("SFT and preference train prompt sets do not match")

    overlap: dict[str, int] = {}
    pairs = (
        ("train_validation", "sft_train", "sft_validation"),
        ("train_test", "sft_train", "sft_test"),
        ("validation_test", "sft_validation", "sft_test"),
    )
    for name, left, right in pairs:
        count = _scalar(
            conn,
            """
            SELECT COUNT(*) FROM rows a JOIN rows b ON a.prompt_sha=b.prompt_sha
            WHERE a.lane=? AND b.lane=?
            """,
            (left, right),
        )
        overlap[name] = count
        if count:
            raise CollectionError(f"prompt leakage detected: {name}")
        family_overlap = _scalar(
            conn,
            """
            SELECT COUNT(*) FROM (
              SELECT DISTINCT family_id FROM rows WHERE lane=?
              INTERSECT SELECT DISTINCT family_id FROM rows WHERE lane=?
            )
            """,
            (left, right),
        )
        if family_overlap:
            raise CollectionError(f"lineage-family leakage detected: {name}")

    declared_hashes = manifest.get("heldout_prompt_sha256")
    if isinstance(declared_hashes, list):
        actual = {
            row[0]
            for row in conn.execute(
                "SELECT prompt_sha FROM rows WHERE lane IN ('sft_validation','sft_test')"
            )
        }
        if actual != {str(value) for value in declared_hashes}:
            raise CollectionError("held-out prompt hashes do not match the candidate manifest")
    return {
        "sft_preference_prompt_parity": True,
        "prompt_overlap": overlap,
        "lineage_family_overlap": {key: 0 for key in overlap},
    }


def _write_shards(
    conn: sqlite3.Connection,
    dataset_dir: Path,
    *,
    counts: Mapping[str, int],
    target_rows: int,
) -> tuple[dict[str, Any], list[dict[str, Any]]]:
    lanes: dict[str, Any] = {}
    preview: list[dict[str, Any]] = []
    preview_lane_counts: Counter[str] = Counter()
    for lane, spec in LANES.items():
        count = counts[lane]
        shard_count = max(1, math.ceil(count / target_rows))
        width = max(5, len(str(shard_count - 1)))
        details: list[dict[str, Any]] = []
        cursor = conn.execute(
            """
            SELECT row_id, lineage_id, family_id, prompt_sha, prompt_chars,
                   answer_chars, payload
            FROM rows WHERE lane=? ORDER BY sort_key, row_id
            """,
            (lane,),
        )
        row_index = 0
        for shard_number in range(shard_count):
            filename = (
                f"{spec['prefix']}-{shard_number:0{width}d}-of-{shard_count:0{width}d}.jsonl"
            )
            path = dataset_dir / filename
            shard_rows = 0
            first_id = ""
            last_id = ""
            with path.open("w", encoding="utf-8", newline="\n") as handle:
                while shard_rows < target_rows:
                    record = cursor.fetchone()
                    if record is None:
                        break
                    row_id, lineage_id, family_id, prompt_sha, prompt_chars, answer_chars, payload = record
                    handle.write(payload + "\n")
                    first_id = first_id or row_id
                    last_id = row_id
                    if preview_lane_counts[lane] < 8:
                        preview.append(
                            {
                                "lane": lane,
                                "split": spec["split"],
                                "id": row_id,
                                "lineage_id": lineage_id,
                                "lineage_family_id": family_id,
                                "prompt_sha256": prompt_sha,
                                "prompt_chars": prompt_chars,
                                "answer_chars": answer_chars,
                                "source_shard": filename,
                            }
                        )
                        preview_lane_counts[lane] += 1
                    shard_rows += 1
                    row_index += 1
            if not shard_rows:
                path.unlink()
                break
            details.append(
                {
                    "path": filename,
                    "sha256": _sha256_file(path),
                    "bytes": path.stat().st_size,
                    "rows": shard_rows,
                    "first_id": first_id,
                    "last_id": last_id,
                }
            )
        if row_index != count:
            raise CollectionError(f"internal shard writer lost rows for {lane}")
        lanes[lane] = {
            "kind": spec["kind"],
            "split": spec["split"],
            "rows": count,
            "shards": details,
        }
    return lanes, preview


def _write_preview(path: Path, rows: Iterable[Mapping[str, Any]]) -> int:
    count = 0
    with path.open("w", encoding="utf-8", newline="\n") as handle:
        for row in rows:
            handle.write(
                json.dumps(row, ensure_ascii=False, sort_keys=True, separators=(",", ":"))
                + "\n"
            )
            count += 1
    return count


def _write_csv(
    path: Path,
    *,
    fieldnames: Sequence[str],
    rows: Iterable[Mapping[str, Any]],
) -> int:
    count = 0
    with path.open("w", encoding="utf-8", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=list(fieldnames), lineterminator="\n")
        writer.writeheader()
        for row in rows:
            writer.writerow({name: row.get(name) for name in fieldnames})
            count += 1
    return count


def _sources(manifest: Mapping[str, Any], quality: Mapping[str, Any]) -> list[str]:
    found: set[str] = set()

    def visit(value: Any) -> None:
        if isinstance(value, str):
            if value.startswith(("https://", "repo:")):
                found.add(value)
        elif isinstance(value, Mapping):
            for child in value.values():
                visit(child)
        elif isinstance(value, Sequence) and not isinstance(value, (str, bytes, bytearray)):
            for child in value:
                visit(child)

    visit(manifest.get("source_scope"))
    visit(manifest.get("source_refs"))
    visit(manifest.get("knowledge_pack_refs"))
    visit(quality.get("source_refs"))
    return sorted(found)


def _axis_summary(manifest: Mapping[str, Any]) -> dict[str, list[str]]:
    matrix = manifest.get("matrix_definition")
    dimensions = matrix.get("dimensions") if isinstance(matrix, Mapping) else None
    if not isinstance(dimensions, Mapping):
        dimensions = manifest.get("dimensions")
    if not isinstance(dimensions, Mapping):
        return {}
    return {
        str(key): [str(item) for item in value]
        for key, value in dimensions.items()
        if isinstance(value, list)
    }


def _write_docs(
    dataset_dir: Path,
    *,
    dataset_id: str,
    title: str,
    release_id: str,
    counts: Mapping[str, int],
    lanes: Mapping[str, Any],
    sources: Sequence[str],
    axes: Mapping[str, Sequence[str]],
    public_ready: bool,
    license_name: str,
    rights_holder: str,
    generator_version: str,
) -> None:
    unique_prompts = counts["sft_train"] + counts["sft_validation"] + counts["sft_test"]
    state = "public-ready after exact approval" if public_ready else "private candidate"
    visibility = "public" if public_ready else "private"
    publication_note = (
        "The exact manifest-bound package is approved for public redistribution."
        if public_ready
        else "The package remains private until an exact manifest-bound approval is supplied."
    )
    dataset_url = f"https://www.kaggle.com/datasets/{dataset_id}"
    integrity_url = f"https://www.kaggle.com/code/{INTEGRITY_NOTEBOOK_ID}"
    plan_url = f"https://www.kaggle.com/code/{TRAINING_PLAN_NOTEBOOK_ID}"
    visual_url = f"https://www.kaggle.com/code/{VISUAL_EXPLORER_NOTEBOOK_ID}"
    dataset_dir.joinpath("README.md").write_text(
        f"""# Start here: {title}

This {visibility} corpus is a **Kaggle / Gemma 4 Good Hackathon learning artifact**
for studying multi-perspective, cross-stage, cross-temporal, and
evidence-bounded model behavior. It is deterministic synthetic research data,
not a collection of real worker cases and not a legal-advice product.

## Reviewer route

1. Open the [visual explorer]({visual_url}) for lane tables, axis coverage,
   cross-axis heatmaps, length distributions, and saved chart/summary outputs.
2. Open the [integrity and exploration notebook]({integrity_url}) for exact
   release, shard, row-hash, and split-family checks.
3. Open the [Gemma 4 plan and smoke notebook]({plan_url}) for a central
   processing unit (CPU)-safe
   training plan and opt-in model/data compatibility preflight. Training is off.
4. Read `LOADING.md` for standard Kaggle, pandas, Hugging Face Datasets, and
   Polars loading examples.
5. Read `DATA_CARD.md`, `SCHEMA.md`, `SOURCES.md`, and `LIMITATIONS.md`.

## Release snapshot

- Release: `{release_id}`
- Supervised fine-tuning train: {counts['sft_train']:,}
- Preference train: {counts['preference_train']:,}
- Validation: {counts['sft_validation']:,}
- Test: {counts['sft_test']:,}
- Unique prompts: {unique_prompts:,}
- `safe_to_train=true` under the recorded synthetic-data and split gates
- `safe_to_publish={str(public_ready).lower()}`. {publication_note}

Use `dataset-overview.csv` for lane counts, `axis-catalog.csv` for declared
design axes, and `preview-catalog.csv` for a text-free sample index that Kaggle
can render directly.

## Claim boundary

No graphics processing unit (GPU) training ran, no adapter was produced, and no model lift was
demonstrated. A future result must use an untouched, lineage-independent
four-arm evaluation: unchanged model, unchanged model plus harness, trained
adapter, and trained adapter plus harness.

## Plain-language terms

- **Supervised fine-tuning** trains on an input and a reviewed desired answer.
- **Preference optimization** trains from a prompt, a preferred answer, and a
  nonpreferred answer.
- **JSON Lines** stores one complete JavaScript Object Notation object per line.
- **Adapter** means the smaller trained weights produced by a
  parameter-efficient fine-tuning method; it still depends on the base model.

Dataset page: {dataset_url}
""",
        encoding="utf-8",
        newline="\n",
    )
    dataset_dir.joinpath("DATA_CARD.md").write_text(
        f"""# {title}

Release `{release_id}` is a manifest-bound **{state}** containing deterministic,
synthetic multi-perspective case-graph data for supervised fine-tuning,
preference optimization, and held-out evaluation.

This is a Kaggle / Gemma 4 Good Hackathon learning and research artifact,
packaged as a professional, reproducible demonstration rather than a production
model or field-deployment claim.

## Start here

- [Visual dataset explorer]({visual_url}) — coverage charts and cross-axis heatmaps.
- [Integrity and exploration notebook]({integrity_url}) — exact release checks.
- [Gemma 4 plan and smoke notebook]({plan_url}) — training plan with execution off.
- `README.md` — reviewer route and release snapshot.
- `LOADING.md` — standard loading examples and training-library mappings.
- `dataset-overview.csv`, `axis-catalog.csv`, and `preview-catalog.csv` — safe previews.

## Counts

- {counts['sft_train']:,} supervised fine-tuning training rows
- {counts['preference_train']:,} preference pairs over the same training prompts
- {counts['sft_validation']:,} validation rows
- {counts['sft_test']:,} test rows
- {unique_prompts:,} unique prompts and {sum(counts.values()):,} lane records

## Intended use

Research and reproducible fine-tuning experiments concerning cross-role, cross-stage,
cross-temporal, evidence-bounded reasoning. Keep whole lineage families in their declared splits.

## Reasoning boundary

Rows contain final answers and deliberately authored visible decision scaffolds. They do not contain
provider-private chain-of-thought, runtime traces, raw worker cases, credentials, or real contact details.

## Status and claims

This dataset package does not claim that Gemma 4 was trained, that an adapter exists, or that model lift
was demonstrated. The included smoke notebook defaults to a central processing
unit training plan and an optional graphics processing unit model/data
preflight only. See `LIMITATIONS.md` before use.

`safe_to_train=true` means the declared synthetic training lanes passed the
manifest, row-integrity, privacy, rights, quality, and family-isolation gates.
It does not grant publication approval. `safe_to_publish={str(public_ready).lower()}`.
{publication_note}

## Provenance

Generator: `{generator_version}`. Release and shard hashes are in `release-manifest.json` and
`shard-index.json`. Rights holder: `{rights_holder}`. License: `{license_name}`.

## Plain-language glossary

- **Supervised fine-tuning:** training on input and reviewed desired-answer
  examples. File and field names may retain the conventional `sft` shorthand.
- **Preference optimization:** training from a prompt, preferred answer, and
  nonpreferred answer.
- **JSON Lines:** one complete JavaScript Object Notation object per line.
- **Secure Hash Algorithm 256-bit checksum:** a content fingerprint used to
  detect a changed row or file. Manifests use the conventional `sha256` field.
- **Adapter:** smaller task-specific weights trained alongside a frozen or
  mostly frozen base model.
""",
        encoding="utf-8",
        newline="\n",
    )
    dataset_dir.joinpath("SCHEMA.md").write_text(
        """# Schema

## Supervised fine-tuning rows

Canonical JSON Lines objects contain `id`, `lineage_id`, `lineage_family_id`, `split`, `messages`,
synthetic provenance, target-model revision, visible `structured_rationale`, `quality_gate`, license,
training/public-redistribution permissions, and a self-verifying `sha256`.

## Preference rows

Preference JSON Lines objects contain the same provenance and split fields plus `prompt`, `chosen`, `rejected`,
`preference_rationale`, and controlled-failure metadata. Chosen/rejected order is semantically meaningful.

## Integrity

The row Secure Hash Algorithm 256-bit checksum is computed from canonical
sorted-key JavaScript Object Notation excluding the row's own `sha256` field.
The shard checksum covers the exact eight-bit Unicode Transformation Format
(UTF-8) JSON Lines bytes. `preview-catalog.jsonl` is metadata-only and is not an
additional training split.

## Reviewer catalogs

- `dataset-overview.csv`: one row per lane with split, kind, counts, shards, and training role.
- `axis-catalog.csv`: one row per declared design-axis value.
- `preview-catalog.csv`: text-free sample identifiers, lengths, lineage families, and shard locations.
- `preview-catalog.jsonl`: the same text-free sample index in JSON Lines form.
""",
        encoding="utf-8",
        newline="\n",
    )
    dataset_dir.joinpath("LOADING.md").write_text(
        f"""# Loading this dataset

The authoritative payload is checksummed JSON Lines. Start with
`release-manifest.json` and `shard-index.json`; do not treat
`dataset-metadata.json` as a mounted payload file because Kaggle consumes it as
upload-control metadata.

## Terms

- **Supervised fine-tuning** trains on input and desired-answer examples.
- **Preference optimization** trains from prompt, preferred-answer, and
  nonpreferred-answer triples.
- **JSON Lines** stores one JavaScript Object Notation object per line.
- **Streaming** reads rows incrementally instead of loading the full corpus into
  memory.

## Python standard library: zero-dependency streaming

```python
import json
from pathlib import Path

root = Path("/kaggle/input/{dataset_id.split('/', 1)[1]}")
shard = next(root.glob("sft-train-*.jsonl"))
with shard.open(encoding="utf-8") as handle:
    first_row = json.loads(next(handle))
print(first_row["messages"])
```

## pandas

```python
import pandas as pd

frame = pd.read_json(shard, lines=True)
print(frame[["split", "lineage_family_id"]].head())
```

## Hugging Face Datasets

```python
from datasets import load_dataset

files = sorted(str(path) for path in root.glob("sft-train-*.jsonl"))
supervised_train = load_dataset(
    "json", data_files={{"train": files}}, split="train", streaming=True
)
print(next(iter(supervised_train))["messages"])
```

For preference optimization, replace the pattern with
`preference-train-*.jsonl`. Validation and test files are diagnostic holdouts,
not training targets.

## Kagglehub outside a Kaggle notebook

```python
import kagglehub

downloaded = kagglehub.dataset_download("{dataset_id}")
print(downloaded)
```

The official Kagglehub adapters can also load supported JSON Lines files into
pandas, Hugging Face Datasets, or Polars. Pin a dataset version for a
reproducible experiment.

## Polars lazy scan

```python
import polars as pl

lazy_rows = pl.scan_ndjson(str(root / "sft-train-*.jsonl"))
print(lazy_rows.select("split").group_by("split").len().collect())
```

## Training-role boundary

- `sft-train-*`: positive assistant targets for supervised fine-tuning.
- `preference-train-*`: controlled same-prompt preference optimization.
- `sft-validation-*` and `sft-test-*`: held-out diagnostic rows.
- keep every `lineage_family_id` in exactly one split.
""",
        encoding="utf-8",
        newline="\n",
    )
    source_lines = "\n".join(f"- {item}" for item in sources) or "- See the manifest-bound source scope."
    dataset_dir.joinpath("SOURCES.md").write_text(
        f"""# Sources and provenance

All case assertions are synthetic and are grounded to invented record identifiers. Method references do
not turn synthetic scenarios into claims about current law, procedure, offices, hotlines, or real people.

{source_lines}
""",
        encoding="utf-8",
        newline="\n",
    )
    axis_lines = "\n".join(
        f"- `{name}`: {len(values)} declared values" for name, values in sorted(axes.items())
    ) or "- Axis counts are recorded in `quality-audit.json`."
    dataset_dir.joinpath("LIMITATIONS.md").write_text(
        f"""# Limitations

- This is combinatorial synthetic data, not a collection of independently reported worker cases.
- Repeated case-graph structure can create template shortcuts even when prompts and outputs are distinct.
- It is not legal advice, a current-law database, or a verified support directory.
- Public use requires the separate manifest-bound approval recorded by the release manifest.
- Training usefulness and model lift require an executed adapter run and independent evaluation.
- Preference pairs encode controlled failures and must not be interpreted as naturally occurring answers.
- Combinatorial balance is a design property, not evidence of real-world prevalence.
- Completed integrity or visualization notebooks do not mean training ran or a model improved.

Declared axes:

{axis_lines}
""",
        encoding="utf-8",
        newline="\n",
    )
    dataset_dir.joinpath("CHANGELOG.md").write_text(
        f"""# Changelog

## 1.0.0-candidate

- Built deterministic manifest-defined shards from the exact candidate.
- Added manifest-bound publication state, rich provenance documentation, and
  central-processing-unit-safe notebooks.
- Added reviewer-first navigation, safe Kaggle-previewable CSV catalogs, and
  professional hackathon learning framing.
- Dataset identifier: `{dataset_id}`.
- Publication state: `{state}`.
""",
        encoding="utf-8",
        newline="\n",
    )
    dataset_dir.joinpath("LICENSE").write_text(
        f"""Dataset license: {license_name}

The row-level license and rights-holder fields remain authoritative for each record. See
https://creativecommons.org/licenses/by-sa/4.0/ for the CC BY-SA 4.0 terms when that is the declared license.
""",
        encoding="utf-8",
        newline="\n",
    )
    dataset_dir.joinpath("CITATION.cff").write_text(
        f"""cff-version: 1.2.0
message: "If you use this dataset, cite the DueCare project and exact release manifest."
title: "{title}"
type: dataset
version: "1.0.0-candidate"
license: "{license_name}"
repository-code: "https://github.com/TaylorAmarelTech/gemma4_comp"
url: "https://www.kaggle.com/datasets/{dataset_id}"
""",
        encoding="utf-8",
        newline="\n",
    )


def _write_croissant_metadata(
    dataset_dir: Path,
    *,
    dataset_id: str,
    title: str,
    release_id: str,
    created_at: Any,
    license_name: str,
    rights_holder: str,
    payload_paths: Sequence[str],
) -> None:
    """Write dependency-free MLCommons Croissant 1.0 metadata."""

    license_urls = {
        "CC-BY-4.0": "https://creativecommons.org/licenses/by/4.0/",
        "CC-BY-SA-4.0": "https://creativecommons.org/licenses/by-sa/4.0/",
        "apache-2.0": "https://www.apache.org/licenses/LICENSE-2.0",
    }
    dataset_url = f"https://www.kaggle.com/datasets/{dataset_id}"
    created_text = str(created_at or "")
    date_published = (
        created_text[:10]
        if re.fullmatch(r"\d{4}-\d{2}-\d{2}(?:T.*)?", created_text)
        else "2026-07-15"
    )
    mime_types = {
        ".csv": "text/csv",
        ".json": "application/json",
        ".jsonl": "application/x-ndjson",
    }
    distributions = []
    for relative in sorted(set(payload_paths)):
        path = dataset_dir / relative
        if not path.is_file() or path.is_symlink():
            raise CollectionError(f"Croissant payload is missing or symlinked: {relative}")
        distributions.append(
            {
                "@type": "cr:FileObject",
                "@id": relative,
                "name": relative,
                "contentUrl": f"{dataset_url}?select={relative}",
                "contentSize": f"{path.stat().st_size} B",
                "encodingFormat": mime_types.get(path.suffix.lower(), "application/octet-stream"),
                "sha256": _sha256_file(path),
            }
        )
    _write_json(
        dataset_dir / "croissant.json",
        {
            "@context": {
                "@language": "en",
                "@vocab": "https://schema.org/",
                "cr": "http://mlcommons.org/croissant/",
                "dct": "http://purl.org/dc/terms/",
                "sc": "https://schema.org/",
            },
            "@type": "Dataset",
            "dct:conformsTo": "http://mlcommons.org/croissant/1.0",
            "name": title,
            "description": (
                "Deterministic synthetic multiperspective corpus with separate "
                "supervised fine-tuning, preference, validation, and test lanes."
            ),
            "url": dataset_url,
            "license": license_urls.get(license_name, license_name),
            "creator": {"@type": "Organization", "name": rights_holder},
            "datePublished": date_published,
            "dateModified": date_published,
            "version": release_id,
            "isLiveDataset": False,
            "keywords": [
                "responsible artificial intelligence",
                "migrant worker protection",
                "supervised fine-tuning",
                "preference optimization",
                "multi-perspective reasoning",
            ],
            "citeAs": f"{title}, release {release_id}",
            "distribution": distributions,
        },
    )


def _notebook(cells: list[dict[str, Any]]) -> dict[str, Any]:
    return {
        "cells": cells,
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


def _markdown(source: str) -> dict[str, Any]:
    return {
        "cell_type": "markdown",
        "id": hashlib.sha256(("markdown:" + source).encode("utf-8")).hexdigest()[:12],
        "metadata": {},
        "source": source.splitlines(True),
    }


def _code(source: str) -> dict[str, Any]:
    return {
        "cell_type": "code",
        "id": hashlib.sha256(("code:" + source).encode("utf-8")).hexdigest()[:12],
        "execution_count": None,
        "metadata": {},
        "outputs": [],
        "source": source.splitlines(True),
    }


def _integrity_notebook(dataset_id: str, expected_manifest_sha: str) -> dict[str, Any]:
    code = f'''from __future__ import annotations
import hashlib, json, os, re
from collections import Counter
from pathlib import Path

DATASET_ID = {dataset_id!r}
EXPECTED_MANIFEST_SHA256 = {expected_manifest_sha!r}

def working_dir():
    kaggle_working = Path("/kaggle/working")
    in_kaggle = bool(os.environ.get("KAGGLE_KERNEL_RUN_TYPE")) or Path("/kaggle/input").exists()
    root = kaggle_working if in_kaggle else Path.cwd() / "duecare_training_outputs"
    root.mkdir(parents=True, exist_ok=True)
    return root

OUTPUT = working_dir() / "integrity-audit.json"

def sha256_file(path):
    digest = hashlib.sha256()
    with Path(path).open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()

def row_sha256(row):
    value = {{key: child for key, child in row.items() if key != "sha256"}}
    payload = json.dumps(value, ensure_ascii=False, sort_keys=True, separators=(",", ":")).encode("utf-8")
    return hashlib.sha256(payload).hexdigest()

def find_root():
    override = os.environ.get("DUECARE_DATASET_ROOT")
    # Kaggle normally mounts dataset files one level below /kaggle/input, but
    # private/new dataset versions can be nested more deeply.  The manifest
    # hash and dataset_id checks below remain the trust boundary.
    candidates = [Path(override)] if override else list(Path("/kaggle/input").rglob("release-manifest.json"))
    for candidate in candidates:
        manifest_path = candidate / "release-manifest.json" if candidate.is_dir() else candidate
        if manifest_path.is_file():
            doc = json.loads(manifest_path.read_text(encoding="utf-8"))
            if doc.get("dataset_id") == DATASET_ID:
                return manifest_path.parent, doc
    raise FileNotFoundError(f"attached dataset {{DATASET_ID}} was not found")

root, release = find_root()
manifest_path = root / "release-manifest.json"
assert sha256_file(manifest_path) == EXPECTED_MANIFEST_SHA256
file_failures = []
for name, details in release["files"].items():
    path = root / name
    if not path.is_file() or sha256_file(path) != details["sha256"] or path.stat().st_size != details["bytes"]:
        file_failures.append(name)

shard_index = json.loads((root / "shard-index.json").read_text(encoding="utf-8"))
row_counts, bad_hashes, duplicate_ids = {{}}, {{}}, {{}}
distributions = {{}}
for lane, lane_info in shard_index["lanes"].items():
    seen = set(); rows = 0; bad = 0; duplicates = 0
    axis = {{key: Counter() for key in ("perspective", "journey_stage", "temporal_lens", "evidence_state", "view_mode", "jurisdiction_pattern")}}
    for shard in lane_info["shards"]:
        shard_rows = 0
        with (root / shard["path"]).open("r", encoding="utf-8") as handle:
            for line in handle:
                if not line.strip(): continue
                row = json.loads(line); shard_rows += 1; rows += 1
                row_id = str(row.get("id") or "")
                if row_id in seen: duplicates += 1
                seen.add(row_id)
                if row.get("sha256") != row_sha256(row): bad += 1
                for key, counter in axis.items():
                    if row.get(key) not in (None, ""): counter[str(row[key])] += 1
        assert shard_rows == shard["rows"]
    row_counts[lane] = rows; bad_hashes[lane] = bad; duplicate_ids[lane] = duplicates
    distributions[lane] = {{key: dict(sorted(value.items())) for key, value in axis.items() if value}}

ok = not file_failures and not any(bad_hashes.values()) and not any(duplicate_ids.values())
ok = ok and all(row_counts.get(lane) == info["rows"] for lane, info in shard_index["lanes"].items())
report = {{
    "schema_version": "duecare.kaggle.integrity_audit.v1",
    "ok": ok,
    "dataset_id": DATASET_ID,
    "release_id": release["release_id"],
    "release_manifest_sha256": EXPECTED_MANIFEST_SHA256,
    "publication_state": release["publication_state"],
    "file_failures": file_failures,
    "row_counts": row_counts,
    "bad_row_hashes": bad_hashes,
    "duplicate_ids": duplicate_ids,
    "distributions": distributions,
    "claims": {{"training_completed": False, "model_lift_demonstrated": False}},
}}
OUTPUT.parent.mkdir(parents=True, exist_ok=True)
OUTPUT.write_text(json.dumps(report, indent=2, sort_keys=True) + "\\n", encoding="utf-8")
print(json.dumps({{key: report[key] for key in ("ok", "dataset_id", "release_id", "publication_state", "row_counts")}}, indent=2))
assert ok
'''
    return _notebook(
        [
            _markdown(
                "# DueCare Large Corpus Integrity and Exploration\n\n"
                "This central processing unit (CPU) notebook verifies exact shard bytes and row hashes. "
                "It prints aggregate metadata only and does not train a model."
            ),
            _code(code),
        ]
    )


def _training_notebook(
    dataset_id: str,
    expected_manifest_sha: str,
    repo_commit: str,
) -> dict[str, Any]:
    code = f'''from __future__ import annotations
import hashlib, json, os
from pathlib import Path

DATASET_ID = {dataset_id!r}
EXPECTED_MANIFEST_SHA256 = {expected_manifest_sha!r}
REPOSITORY_COMMIT = {repo_commit!r}
RUN_GPU_MODEL_DATA_PREFLIGHT = False

def working_dir():
    kaggle_working = Path("/kaggle/working")
    in_kaggle = bool(os.environ.get("KAGGLE_KERNEL_RUN_TYPE")) or Path("/kaggle/input").exists()
    root = kaggle_working if in_kaggle else Path.cwd() / "duecare_training_outputs"
    root.mkdir(parents=True, exist_ok=True)
    return root

WORKING = working_dir()

def sha256_file(path):
    digest = hashlib.sha256()
    with Path(path).open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()

def find_root():
    override = os.environ.get("DUECARE_DATASET_ROOT")
    # Support both the traditional one-level mount and Kaggle's nested private
    # dataset layouts; the exact manifest digest is verified immediately.
    candidates = [Path(override)] if override else list(Path("/kaggle/input").rglob("release-manifest.json"))
    for candidate in candidates:
        path = candidate / "release-manifest.json" if candidate.is_dir() else candidate
        if path.is_file():
            doc = json.loads(path.read_text(encoding="utf-8"))
            if doc.get("dataset_id") == DATASET_ID: return path.parent, doc
    raise FileNotFoundError(f"attached dataset {{DATASET_ID}} was not found")

root, release = find_root()
assert sha256_file(root / "release-manifest.json") == EXPECTED_MANIFEST_SHA256
for name, details in release["files"].items():
    path = root / name
    assert path.is_file() and sha256_file(path) == details["sha256"]

plan = {{
    "schema_version": "duecare.kaggle.gemma4_large_training_plan.v1",
    "dataset_id": DATASET_ID,
    "release_id": release["release_id"],
    "release_manifest_sha256": EXPECTED_MANIFEST_SHA256,
    "repository_commit": REPOSITORY_COMMIT,
    "base_model": release["source_bundle"]["model"],
    "method": (
        "response-only Low-Rank Adaptation supervised fine-tuning followed by "
        "optional Direct Preference Optimization"
    ),
    "source_lanes": {{name: [item["path"] for item in lane["shards"]] for name, lane in release["lanes"].items()}},
    "execution_status": "not_executed",
    "gpu_opt_in": RUN_GPU_MODEL_DATA_PREFLIGHT,
    "claims": {{"training_completed": False, "adapter_produced": False, "model_lift_demonstrated": False}},
    "required_future_evidence": ["training completion manifest", "adapter hashes", "four-arm held-out evaluation"],
}}
WORKING.mkdir(parents=True, exist_ok=True)
(WORKING / "training-plan.json").write_text(json.dumps(plan, indent=2, sort_keys=True) + "\\n", encoding="utf-8")
print(json.dumps({{key: plan[key] for key in ("dataset_id", "release_id", "execution_status", "gpu_opt_in", "claims")}}, indent=2))

if RUN_GPU_MODEL_DATA_PREFLIGHT:
    import torch
    if not torch.cuda.is_available(): raise RuntimeError("GPU preflight requires a CUDA-enabled Kaggle session")
    # This is deliberately a model/data compatibility preflight, not fine-tuning.
    from unsloth import FastModel
    model_ref = release["source_bundle"]["model"]
    model, tokenizer = FastModel.from_pretrained(
        model_name=model_ref["id"], revision=model_ref["revision"], max_seq_length=2048,
        dtype=None, load_in_4bit=True, full_finetuning=False,
    )
    first_shard = root / release["lanes"]["sft_train"]["shards"][0]["path"]
    with first_shard.open("r", encoding="utf-8") as handle:
        sample = json.loads(next(line for line in handle if line.strip()))
    rendered = tokenizer.apply_chat_template(sample["messages"], tokenize=False, add_generation_prompt=False)
    tokens = tokenizer(rendered, return_tensors="pt")
    preflight = {{
        "schema_version": "duecare.kaggle.gemma4_model_data_preflight.v1",
        "ok": bool(tokens["input_ids"].shape[-1] > 0),
        "cuda_device": torch.cuda.get_device_name(0),
        "input_tokens": int(tokens["input_ids"].shape[-1]),
        "training_completed": False,
        "adapter_produced": False,
        "model_lift_demonstrated": False,
    }}
    (WORKING / "gpu-model-data-preflight.json").write_text(json.dumps(preflight, indent=2, sort_keys=True) + "\\n", encoding="utf-8")
    print(json.dumps(preflight, indent=2))
'''
    return _notebook(
        [
            _markdown(
                "# DueCare Gemma 4 Large-Corpus Plan and Smoke Preflight\n\n"
                "The default central processing unit (CPU) run verifies the release and writes a training plan. "
                "The optional graphics processing unit (GPU) path only loads the pinned model and tokenizes one "
                "row; it does **not** train or claim lift. Low-Rank Adaptation means training small adapter weights "
                "while leaving most base-model weights frozen. Direct Preference Optimization trains from a prompt, "
                "a preferred answer, and a nonpreferred answer."
            ),
            _code(code),
        ]
    )


def _write_notebook_dir(
    target: Path,
    *,
    notebook: Mapping[str, Any],
    notebook_id: str,
    title: str,
    is_private: bool,
    dataset_id: str,
    model_sources: Sequence[str] = (),
    enable_internet: bool = False,
) -> None:
    target.mkdir(parents=True, exist_ok=True)
    _write_json(target / "notebook.ipynb", notebook)
    _write_json(
        target / "kernel-metadata.json",
        {
            "id": notebook_id,
            "title": title,
            "code_file": "notebook.ipynb",
            "language": "python",
            "kernel_type": "notebook",
            "is_private": is_private,
            "enable_gpu": False,
            "enable_internet": enable_internet,
            "dataset_sources": [dataset_id],
            "competition_sources": [],
            "kernel_sources": [],
            "model_sources": list(model_sources),
            "docker_image_pinning_type": "original",
            "keywords": ["nlp"],
        },
    )


def verify_dataset_package(dataset_dir: Path) -> dict[str, Any]:
    """Stream-verify one finished package without loading its shards wholly."""

    root = dataset_dir.resolve()
    release = _read_json(root / "release-manifest.json", label="release manifest")
    if release.get("schema_version") != RELEASE_SCHEMA:
        raise CollectionError("large release manifest schema is invalid")
    if release.get("safe_to_train") is not True:
        raise CollectionError("large release must explicitly set safe_to_train=true")
    files = release.get("files")
    if not isinstance(files, Mapping):
        raise CollectionError("large release manifest files map is missing")
    required_files = {
        "README.md",
        "DATA_CARD.md",
        "SCHEMA.md",
        "LOADING.md",
        "SOURCES.md",
        "LIMITATIONS.md",
        "CITATION.cff",
        "LICENSE",
        "candidate-manifest.json",
        "quality-audit.json",
        "case-graphs.jsonl",
        "shard-index.json",
        "dataset-overview.csv",
        "axis-catalog.csv",
        "preview-catalog.csv",
        "preview-catalog.jsonl",
        "croissant.json",
    }
    missing_required = sorted(required_files - set(files))
    if missing_required:
        raise CollectionError(f"large release is missing required artifact: {missing_required[0]}")
    actual_payload_files = {
        path.name
        for path in root.iterdir()
        if path.is_file() and path.name not in {"release-manifest.json", "dataset-metadata.json"}
    }
    if actual_payload_files != set(files):
        raise CollectionError("large release file inventory does not match the payload directory")
    for name, details in files.items():
        if not isinstance(details, Mapping):
            raise CollectionError(f"invalid release file declaration: {name}")
        path = (root / str(name)).resolve()
        if not _contained(path, root) or not path.is_file() or path.is_symlink():
            raise CollectionError(f"release file is missing or unsafe: {name}")
        if details.get("sha256") != _sha256_file(path) or details.get("bytes") != path.stat().st_size:
            raise CollectionError(f"release file hash/size mismatch: {name}")
    croissant = _read_json(root / "croissant.json", label="Croissant metadata")
    required_croissant = {
        "@context",
        "@type",
        "dct:conformsTo",
        "name",
        "description",
        "url",
        "license",
        "creator",
        "datePublished",
        "distribution",
    }
    if not required_croissant.issubset(croissant):
        raise CollectionError("Croissant metadata is missing required dataset fields")
    if croissant.get("dct:conformsTo") != "http://mlcommons.org/croissant/1.0":
        raise CollectionError("Croissant conformance version mismatch")
    distributions = croissant.get("distribution")
    if not isinstance(distributions, list) or not distributions:
        raise CollectionError("Croissant metadata has no file distributions")
    for item in distributions:
        if not isinstance(item, Mapping):
            raise CollectionError("Croissant distribution is not an object")
        relative = item.get("@id")
        declaration = files.get(relative) if isinstance(relative, str) else None
        if not isinstance(declaration, Mapping):
            raise CollectionError("Croissant distribution is not release-manifest bound")
        if item.get("sha256") != declaration.get("sha256"):
            raise CollectionError(f"Croissant checksum mismatch: {relative}")
        if item.get("contentSize") != f"{declaration.get('bytes')} B":
            raise CollectionError(f"Croissant byte-count mismatch: {relative}")
    metadata = _read_json(root / "dataset-metadata.json", label="dataset metadata")
    expected_metadata_fields = {
        "title",
        "subtitle",
        "description",
        "id",
        "licenses",
        "resources",
        "keywords",
        "collaborators",
        "isPrivate",
    }
    if set(metadata) != expected_metadata_fields:
        raise CollectionError("large dataset metadata does not use the closed schema")
    if metadata.get("id") != release.get("dataset_id") or metadata.get("title") != release.get("title"):
        raise CollectionError("large dataset metadata identity mismatch")
    if metadata.get("isPrivate") is not (not bool(release.get("safe_to_publish"))):
        raise CollectionError("large dataset privacy state mismatch")
    _verify_metadata_content(root / "dataset-metadata.json", label="dataset metadata")
    resources = metadata.get("resources")
    mounted_files = actual_payload_files | {"release-manifest.json"}
    if not isinstance(resources, list) or any(
        not isinstance(item, Mapping)
        or set(item) != {"path", "description"}
        or item.get("path") not in mounted_files
        for item in resources or []
    ):
        raise CollectionError("large dataset metadata resources are invalid")
    shard_index = _read_json(root / "shard-index.json", label="shard index")
    observed: dict[str, int] = {}
    for lane, lane_info in (shard_index.get("lanes") or {}).items():
        rows = 0
        for shard in lane_info.get("shards") or []:
            path = root / shard["path"]
            shard_rows = 0
            with path.open("r", encoding="utf-8") as handle:
                for line in handle:
                    if not line.strip():
                        continue
                    row = json.loads(line)
                    if row.get("sha256") != training_row_sha256(row):
                        raise CollectionError(f"row hash mismatch in {shard['path']}")
                    shard_rows += 1
            if shard_rows != shard.get("rows"):
                raise CollectionError(f"row count mismatch in {shard['path']}")
            rows += shard_rows
        if rows != lane_info.get("rows"):
            raise CollectionError(f"lane row count mismatch: {lane}")
        observed[str(lane)] = rows
    return {
        "ok": True,
        "release_id": release.get("release_id"),
        "dataset_id": release.get("dataset_id"),
        "publication_state": release.get("publication_state"),
        "counts": observed,
    }


def _build_collection_into(
    source_manifest: Path,
    output_root: Path,
    *,
    approval_path: Path | None = None,
    public_ready: bool = False,
    dataset_id: str = DEFAULT_DATASET_ID,
    title: str = DEFAULT_TITLE,
    shard_target_rows: int = DEFAULT_SHARD_TARGET_ROWS,
    repo_commit: str = "",
) -> dict[str, Any]:
    """Build the deterministic dataset and notebook collection in ``output_root``."""

    if shard_target_rows <= 0:
        raise CollectionError("shard_target_rows must be positive")
    _dataset_identity(dataset_id, title)
    if source_manifest.is_symlink():
        raise CollectionError("candidate manifest must not be a symlink")
    source_manifest = source_manifest.resolve(strict=True)
    manifest, quality, quality_path, _ = _candidate_metadata(source_manifest)
    repo_provenance = _repo_provenance(repo_commit)
    commit = str(repo_provenance["commit"])
    approval: dict[str, Any] | None = None
    if approval_path is not None:
        if approval_path.is_symlink():
            raise CollectionError("publication approval must not be a symlink")
        approval = _verify_approval(
            approval_path.resolve(strict=True),
            manifest_path=source_manifest,
            manifest=manifest,
            quality_path=quality_path,
        )
    if public_ready and approval is None:
        raise CollectionError("--public-ready requires exact manifest-bound approval")

    root = _initialize_output(output_root)
    dataset_dir = root / "dataset"
    notebook_root = root / "notebooks"
    dataset_dir.mkdir()
    source_manifest_sha = _sha256_file(source_manifest)
    release_id = f"duecare-large-{source_manifest_sha[:16]}"

    with tempfile.TemporaryDirectory(prefix="duecare-large-kaggle-") as temp_dir:
        db_path = Path(temp_dir) / "rows.sqlite3"
        conn = sqlite3.connect(db_path)
        try:
            conn.execute("PRAGMA journal_mode=OFF")
            conn.execute("PRAGMA synchronous=OFF")
            conn.execute("PRAGMA temp_store=FILE")
            conn.execute(
                """
                CREATE TABLE rows (
                  lane TEXT NOT NULL,
                  sort_key TEXT NOT NULL,
                  row_id TEXT NOT NULL,
                  lineage_id TEXT NOT NULL,
                  family_id TEXT NOT NULL,
                  prompt_sha TEXT NOT NULL,
                  prompt_chars INTEGER NOT NULL,
                  answer_chars INTEGER NOT NULL,
                  payload TEXT NOT NULL,
                  PRIMARY KEY (lane, row_id),
                  UNIQUE (lane, prompt_sha)
                )
                """
            )
            conn.execute("CREATE INDEX rows_lane_sort ON rows(lane, sort_key, row_id)")
            counts, coverage, licenses, rights_holders, row_sources = _insert_source_rows(
                conn, manifest_path=source_manifest, manifest=manifest
            )
            declared_counts = manifest.get("counts")
            if isinstance(declared_counts, Mapping):
                for lane, observed in counts.items():
                    if declared_counts.get(lane) != observed:
                        raise CollectionError(
                            f"candidate manifest count mismatch for {lane}"
                        )
            split_contract = _verify_split_contract(conn, manifest)
            if len(licenses) != 1:
                raise CollectionError("all candidate rows must use one release license")
            release_license = next(iter(licenses))
            if len(rights_holders) != 1:
                raise CollectionError("all candidate rows must use one rights holder")
            rights_holder = next(iter(rights_holders))
            if approval is not None and approval.get("release_license") != release_license:
                raise CollectionError("approval and candidate row licenses differ")
            if approval is not None and approval.get("rights_holder") != rights_holder:
                raise CollectionError("approval and candidate row rights holders differ")
            lanes, preview = _write_shards(
                conn,
                dataset_dir,
                counts=counts,
                target_rows=shard_target_rows,
            )
        finally:
            conn.close()

    preview_catalog = [
        {**dict(row), "catalog_contains_raw_text": False}
        for row in preview
    ]
    preview_rows = _write_preview(dataset_dir / "preview-catalog.jsonl", preview_catalog)
    _write_csv(
        dataset_dir / "preview-catalog.csv",
        fieldnames=(
            "lane",
            "split",
            "source_shard",
            "id",
            "lineage_id",
            "lineage_family_id",
            "prompt_sha256",
            "prompt_chars",
            "answer_chars",
            "catalog_contains_raw_text",
        ),
        rows=preview_catalog,
    )
    _copy_verified_metadata(
        dataset_dir,
        source_manifest,
        manifest,
        (
            ("quality-audit.json", ("quality_audit", "quality-audit")),
            ("build-summary.json", ("build_summary", "build-summary")),
            ("case-graphs.jsonl", ("case_graphs", "case-graphs")),
        ),
    )
    shutil.copyfile(source_manifest, dataset_dir / "candidate-manifest.json")
    if approval is not None and approval_path is not None:
        shutil.copyfile(approval_path, dataset_dir / "publication-approval.json")

    shard_index = {
        "schema_version": SHARD_INDEX_SCHEMA,
        "release_id": release_id,
        "source_manifest_sha256": source_manifest_sha,
        "partitioner": {
            "algorithm": "sha256_lineage_sort_contiguous_chunks_v1",
            "target_rows_per_shard": shard_target_rows,
            "encoding": "utf-8-jsonl-lf",
        },
        "counts": counts,
        "lanes": lanes,
    }
    _write_json(dataset_dir / "shard-index.json", shard_index)

    source_list = sorted(set(_sources(manifest, quality)) | row_sources)
    axes = _axis_summary(manifest)
    training_roles = {
        "sft_train": "positive_sft_target",
        "preference_train": "chosen_rejected_preference_pair",
        "sft_validation": "diagnostic_holdout_not_training",
        "sft_test": "diagnostic_holdout_not_training",
    }
    overview_rows = [
        {
            "lane": lane,
            "kind": info["kind"],
            "split": info["split"],
            "rows": info["rows"],
            "shards": len(info["shards"]),
            "bytes": sum(item["bytes"] for item in info["shards"]),
            "catalog_contains_raw_text": False,
            "lane_contains_synthetic_training_text": True,
            "training_role": training_roles[lane],
        }
        for lane, info in sorted(lanes.items())
    ]
    _write_csv(
        dataset_dir / "dataset-overview.csv",
        fieldnames=(
            "lane",
            "kind",
            "split",
            "rows",
            "shards",
            "bytes",
            "catalog_contains_raw_text",
            "lane_contains_synthetic_training_text",
            "training_role",
        ),
        rows=overview_rows,
    )
    axis_rows = [
        {"axis": axis, "value": value, "declared_value_index": index}
        for axis, values in sorted(axes.items())
        for index, value in enumerate(values)
    ]
    _write_csv(
        dataset_dir / "axis-catalog.csv",
        fieldnames=("axis", "value", "declared_value_index"),
        rows=axis_rows,
    )
    generator_version = str(manifest.get("generator_version") or "unknown")
    _write_docs(
        dataset_dir,
        dataset_id=dataset_id,
        title=title,
        release_id=release_id,
        counts=counts,
        lanes=lanes,
        sources=source_list,
        axes=axes,
        public_ready=public_ready,
        license_name=release_license,
        rights_holder=rights_holder,
        generator_version=generator_version,
    )
    _write_croissant_metadata(
        dataset_dir,
        dataset_id=dataset_id,
        title=title,
        release_id=release_id,
        created_at=manifest.get("created_at"),
        license_name=release_license,
        rights_holder=rights_holder,
        payload_paths=[
            *[
                item["path"]
                for info in lanes.values()
                for item in info["shards"]
            ],
            "dataset-overview.csv",
            "axis-catalog.csv",
            "preview-catalog.csv",
            "preview-catalog.jsonl",
            "shard-index.json",
        ],
    )

    subtitle = "Manifest-bound synthetic supervised fine-tuning and preference corpus"
    description = (
        "A deterministic, manifest-bound synthetic corpus for multi-perspective, temporal, "
        "evidence-bounded supervised fine-tuning and preference research. It contains visible decision scaffolds, "
        "not hidden chain-of-thought or real worker cases."
    )
    resources = [
        {
            "path": item["path"],
            "description": f"{lane} {info['split']} shard with {item['rows']} rows",
        }
        for lane, info in lanes.items()
        for item in info["shards"]
    ]
    resources.extend(
        [
            {
                "path": "dataset-overview.csv",
                "description": "Kaggle-previewable lane, split, row, byte, and training-role map",
            },
            {
                "path": "axis-catalog.csv",
                "description": "Declared multi-perspective design axes and values",
            },
            {
                "path": "preview-catalog.csv",
                "description": "Text-free sample index for Kaggle preview and reviewer navigation",
            },
            {
                "path": "preview-catalog.jsonl",
                "description": "Metadata-only preview catalog; not an additional training split",
            },
            {"path": "README.md", "description": "Reviewer start-here guide and notebook route"},
            {"path": "DATA_CARD.md", "description": "Dataset card and use boundary"},
            {"path": "SCHEMA.md", "description": "Training schemas and reviewer catalog definitions"},
            {"path": "LOADING.md", "description": "Standard local, Kaggle, pandas, Hugging Face, and Polars loaders"},
            {"path": "SOURCES.md", "description": "Synthetic provenance and method references"},
            {"path": "LIMITATIONS.md", "description": "Known limits and required controls"},
            {"path": "croissant.json", "description": "MLCommons Croissant dataset metadata and payload checksums"},
            {"path": "release-manifest.json", "description": "Release integrity manifest"},
        ]
    )
    _write_json(
        dataset_dir / "dataset-metadata.json",
        {
            "title": title,
            "subtitle": subtitle,
            "description": description,
            "id": dataset_id,
            "licenses": [{"name": release_license}],
            "resources": resources,
            "keywords": ["nlp"],
            "collaborators": [],
            "isPrivate": not public_ready,
        },
    )

    public_state = "approved_public_ready" if public_ready else "candidate_private"
    file_names = sorted(
        path.name
        for path in dataset_dir.iterdir()
        # Kaggle consumes dataset-metadata.json as upload control metadata and
        # does not mount it as a dataset payload file.  Keep it locally, but do
        # not promise that a remote integrity notebook can hash it.
        if path.is_file()
        and path.name not in {"release-manifest.json", "dataset-metadata.json"}
    )
    files = {
        name: {
            "sha256": _sha256_file(dataset_dir / name),
            "bytes": (dataset_dir / name).stat().st_size,
        }
        for name in file_names
    }
    for lane in lanes.values():
        for shard in lane["shards"]:
            files[shard["path"]]["rows"] = shard["rows"]
    files["preview-catalog.jsonl"]["rows"] = preview_rows
    files["preview-catalog.csv"]["rows"] = preview_rows
    files["dataset-overview.csv"]["rows"] = len(overview_rows)
    files["axis-catalog.csv"]["rows"] = len(axis_rows)
    release_manifest = {
        "schema_version": RELEASE_SCHEMA,
        "handoff_kind": COLLECTION_SCHEMA,
        "release_id": release_id,
        "dataset_id": dataset_id,
        "title": title,
        "created_at": manifest.get("created_at"),
        "repo_provenance": repo_provenance,
        "publication_state": public_state,
        "safe_to_train": True,
        "safe_to_publish": public_ready,
        "public": public_ready,
        "candidate_private_by_default": True,
        "source_bundle": {
            "schema_version": manifest.get("schema_version"),
            "id": manifest.get("id") or manifest.get("candidate_id"),
            "manifest_sha256": source_manifest_sha,
            "generator_version": generator_version,
            "model": manifest.get("model") or manifest.get("target_model"),
            "reasoning_data_policy": manifest.get("reasoning_data_policy"),
        },
        "publication_approval": (
            {
                "approval_sha256": _sha256_file(dataset_dir / "publication-approval.json"),
                "approved_by": approval.get("approved_by"),
                "approved_at": approval.get("approved_at"),
            }
            if approval is not None
            else None
        ),
        "release_license": release_license,
        "rights_holder": rights_holder,
        "counts": counts,
        "coverage": coverage,
        "split_contract": split_contract,
        "prompt_scope": manifest.get("prompt_scope"),
        "lanes": lanes,
        "files": files,
        "claims": {
            "training_completed": False,
            "adapter_produced": False,
            "model_lift_demonstrated": False,
            "full_flywheel_closure": False,
        },
    }
    _write_json(dataset_dir / "release-manifest.json", release_manifest)
    release_manifest_sha = _sha256_file(dataset_dir / "release-manifest.json")

    # Keep ids equal to Kaggle's title-derived slugs so repeat pushes version
    # the same private notebooks instead of relying on Kaggle's redirect.
    integrity_id = INTEGRITY_NOTEBOOK_ID
    training_id = TRAINING_PLAN_NOTEBOOK_ID
    _write_notebook_dir(
        notebook_root / "integrity_exploration",
        notebook=_integrity_notebook(dataset_id, release_manifest_sha),
        notebook_id=integrity_id,
        title="DueCare Large Corpus Integrity and Exploration",
        is_private=not public_ready,
        dataset_id=dataset_id,
    )
    _write_notebook_dir(
        notebook_root / "gemma4_plan_smoke",
        notebook=_training_notebook(dataset_id, release_manifest_sha, commit),
        notebook_id=training_id,
        title="DueCare Gemma 4 Large Corpus Plan and Smoke",
        is_private=not public_ready,
        dataset_id=dataset_id,
        model_sources=[DEFAULT_MODEL_SOURCE],
        enable_internet=True,
    )

    verification = verify_dataset_package(dataset_dir)
    collection = {
        "schema_version": COLLECTION_SCHEMA,
        "release_id": release_id,
        "publication_state": public_state,
        "safe_to_train": True,
        "safe_to_publish": public_ready,
        "dataset": {
            "id": dataset_id,
            "path": "dataset",
            "release_manifest_sha256": release_manifest_sha,
            "counts": counts,
        },
        "notebooks": {
            "integrity_exploration": {
                "id": integrity_id,
                "path": "notebooks/integrity_exploration",
                "published_accelerator": "cpu",
            },
            "gemma4_plan_smoke": {
                "id": training_id,
                "path": "notebooks/gemma4_plan_smoke",
                "published_accelerator": "cpu",
                "gpu_opt_in": True,
                "training_claimed": False,
            },
        },
        "repository_commit": commit,
        "repo_provenance": repo_provenance,
        "verification": verification,
        "no_publication_performed": True,
    }
    _write_json(root / "collection-manifest.json", collection)
    return collection


def build_collection(
    source_manifest: Path,
    output_root: Path,
    *,
    approval_path: Path | None = None,
    public_ready: bool = False,
    dataset_id: str = DEFAULT_DATASET_ID,
    title: str = DEFAULT_TITLE,
    shard_target_rows: int = DEFAULT_SHARD_TARGET_ROWS,
    repo_commit: str = "",
    force: bool = False,
) -> dict[str, Any]:
    """Build transactionally, preserving any prior verified collection."""

    output, staging = _prepare_staging(output_root, force=force)
    try:
        collection = _build_collection_into(
            source_manifest,
            staging,
            approval_path=approval_path,
            public_ready=public_ready,
            dataset_id=dataset_id,
            title=title,
            shard_target_rows=shard_target_rows,
            repo_commit=repo_commit,
        )
        _commit_staging(staging, output)
        staging = output
        return collection
    except Exception:
        if staging.exists() and staging != output:
            shutil.rmtree(staging, ignore_errors=True)
        raise


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--source-manifest", type=Path, required=True)
    parser.add_argument("--output-root", type=Path, default=DEFAULT_OUTPUT_ROOT)
    parser.add_argument("--approval", type=Path)
    parser.add_argument("--public-ready", action="store_true")
    parser.add_argument("--dataset-id", default=DEFAULT_DATASET_ID)
    parser.add_argument("--title", default=DEFAULT_TITLE)
    parser.add_argument("--shard-target-rows", type=int, default=DEFAULT_SHARD_TARGET_ROWS)
    parser.add_argument("--repo-commit", default="")
    parser.add_argument("--force", action="store_true")
    return parser


def main(argv: Sequence[str] | None = None) -> int:
    args = build_parser().parse_args(argv)
    try:
        result = build_collection(
            args.source_manifest,
            args.output_root,
            approval_path=args.approval,
            public_ready=args.public_ready,
            dataset_id=args.dataset_id,
            title=args.title,
            shard_target_rows=args.shard_target_rows,
            repo_commit=args.repo_commit,
            force=args.force,
        )
    except (CollectionError, FileNotFoundError) as exc:
        print(f"ERROR: {exc}", file=sys.stderr)
        return 2
    print(json.dumps(result, ensure_ascii=False, indent=2, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
