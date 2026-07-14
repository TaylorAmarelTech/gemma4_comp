#!/usr/bin/env python3
"""Build a public Kaggle training dataset from one verified DueCare bundle.

This is deliberately a release gate, not a generic JSONL copier.  It accepts
the manifest-bound bundle emitted by the active A-00 Kaggle workbench, verifies
the source artifact hashes and the canonical training contract, strips private
runtime trace metadata, re-hashes the public rows, and writes a self-contained
Kaggle dataset directory.

The command fails closed when provenance, licensing, privacy, held-out lineage,
model revision, source grounding, row integrity, or hidden-reasoning checks do
not pass.  It never publishes by itself; use ``scripts/publish_kaggle.py`` on a
verified release directory after curator review.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import re
import sys
from collections.abc import Iterable, Mapping, Sequence
from datetime import UTC, datetime
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
    validate_training_rows,
)

SOURCE_HANDOFF_KIND = "duecare.a00.synthetic.training_bundle.v2"
APPROVAL_HANDOFF_KIND = "duecare.training.publication_approval.v1"
RELEASE_HANDOFF_KIND = "duecare.kaggle.training_dataset_release.v1"
RELEASE_SCHEMA_VERSION = "1.0"
DEFAULT_DATASET_ID = "taylorsamarel/duecare-harness-training-data"
DEFAULT_TITLE = "DueCare Harness Training Data"
ALLOWED_ROW_LICENSES = frozenset(
    {
        "CC-BY-4.0",
        "CC-BY-SA-4.0",
        "Apache-2.0",
        "MIT",
    }
)
UNPINNED_REVISIONS = frozenset({"", "main", "master", "latest", "runtime-unpinned", "unknown"})

PUBLIC_SFT_FIELDS = (
    "id",
    "messages",
    "source_profile",
    "rubric_targets",
    "synthetic",
    "pii_checked",
    "lineage_id",
    "split",
    "license",
    "quality_gate",
    "source_refs",
    "knowledge_pack_refs",
    "prompt_family",
    "created_at",
    "model_revision",
    "harness_version",
    "rubric_version",
    "structured_rationale",
    "rights_holder",
    "allow_training_use",
    "allow_public_redistribution",
)
PUBLIC_PREFERENCE_FIELDS = (
    "id",
    "prompt",
    "chosen",
    "rejected",
    "preference_rationale",
    "pii_checked",
    "lineage_id",
    "split",
    "license",
    "quality_gate",
    "source_refs",
    "knowledge_pack_refs",
    "created_at",
    "model_revision",
    "harness_version",
    "rubric_version",
    "rights_holder",
    "allow_training_use",
    "allow_public_redistribution",
)

_HEX40_OR_64 = re.compile(r"^[0-9a-f]{40}(?:[0-9a-f]{24})?$")
_HEX64 = re.compile(r"^[0-9a-f]{64}$")
_SAFE_DATASET_ID = re.compile(r"^[A-Za-z0-9_.-]+/[A-Za-z0-9_.-]+$")
_SAFE_RELEASE_ID = re.compile(r"[^a-z0-9]+")
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


class ReleaseError(ValueError):
    """A metadata-only public-release validation failure."""


def _utc() -> str:
    return datetime.now(UTC).replace(microsecond=0).isoformat()


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
        raise ReleaseError(f"unreadable JSON artifact: {path.name}") from exc
    if not isinstance(value, dict):
        raise ReleaseError(f"JSON artifact must contain an object: {path.name}")
    return value


def _read_jsonl(path: Path) -> list[dict[str, Any]]:
    rows: list[dict[str, Any]] = []
    try:
        lines = path.read_text(encoding="utf-8").splitlines()
    except (OSError, UnicodeDecodeError) as exc:
        raise ReleaseError(f"unreadable JSONL artifact: {path.name}") from exc
    for line_number, line in enumerate(lines, start=1):
        if not line.strip():
            continue
        try:
            row = json.loads(line)
        except json.JSONDecodeError as exc:
            raise ReleaseError(f"invalid JSONL row in {path.name} at line {line_number}") from exc
        if not isinstance(row, dict):
            raise ReleaseError(f"JSONL row must be an object in {path.name} at line {line_number}")
        rows.append(row)
    return rows


def _write_json(path: Path, value: Mapping[str, Any]) -> None:
    path.write_text(json.dumps(value, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")


def _write_jsonl(path: Path, rows: Iterable[Mapping[str, Any]]) -> int:
    count = 0
    with path.open("w", encoding="utf-8", newline="\n") as handle:
        for row in rows:
            handle.write(json.dumps(row, ensure_ascii=False, sort_keys=True) + "\n")
            count += 1
    return count


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
    return any(_PRIVATE_PATH.search(text) or _SECRET_LITERAL.search(text) for text in _strings(value))


def _contained(path: Path, root: Path) -> bool:
    try:
        path.relative_to(root)
        return True
    except ValueError:
        return False


def _resolve_artifact(manifest_path: Path, raw_value: Any) -> Path:
    if not isinstance(raw_value, str) or not raw_value.strip():
        raise ReleaseError("artifact path is missing")
    base = manifest_path.parent.resolve()
    raw = Path(raw_value)
    candidates: list[Path] = []
    if not raw.is_absolute():
        candidates.append(base / raw)
    candidates.append(base / raw.name)
    for candidate in candidates:
        if not candidate.exists() or not candidate.is_file():
            continue
        try:
            resolved = candidate.resolve(strict=True)
        except OSError as exc:
            raise ReleaseError(f"artifact cannot be resolved: {candidate.name}") from exc
        if not _contained(resolved, base):
            raise ReleaseError(f"artifact escapes bundle directory: {candidate.name}")
        return resolved
    raise ReleaseError(f"artifact is missing from bundle directory: {raw.name}")


def _verified_approval(
    approval_path: Path,
    *,
    source_manifest_sha256: str,
    prompt_scope: Mapping[str, Any],
) -> dict[str, Any]:
    approval_path = approval_path.resolve(strict=True)
    approval = _read_json(approval_path)
    if approval.get("schema_version") != "1.0":
        raise ReleaseError("publication approval schema_version is not 1.0")
    if approval.get("handoff_kind") != APPROVAL_HANDOFF_KIND:
        raise ReleaseError("publication approval handoff_kind is invalid")
    if approval.get("source_manifest_sha256") != source_manifest_sha256:
        raise ReleaseError("publication approval is not bound to this source manifest")
    approved_by = str(approval.get("approved_by") or "").strip()
    approved_at = str(approval.get("approved_at") or "").strip()
    if not approved_by or not approved_at or pii_findings({"approved_by": approved_by}):
        raise ReleaseError("publication approval identity or timestamp is missing/unsafe")
    if _contains_private_path_or_secret(approval):
        raise ReleaseError("publication approval contains a private path or credential signature")

    decisions = approval.get("approvals")
    required_decisions = (
        "curator_approved",
        "privacy_approved",
        "license_approved",
        "quality_approved",
        "public_redistribution_approved",
    )
    if not isinstance(decisions, Mapping) or any(decisions.get(key) is not True for key in required_decisions):
        raise ReleaseError("publication approval decisions are incomplete")
    if approval.get("allow_training_use") is not True:
        raise ReleaseError("publication approval does not grant training use")
    if approval.get("allow_public_redistribution") is not True:
        raise ReleaseError("publication approval does not grant public redistribution")
    rights_holder = str(approval.get("rights_holder") or "").strip()
    row_license = str(approval.get("row_license") or "").strip()
    release_license = str(approval.get("release_license") or "").strip()
    if not rights_holder or pii_findings({"rights_holder": rights_holder}):
        raise ReleaseError("publication approval rights holder is missing/unsafe")
    if row_license not in ALLOWED_ROW_LICENSES:
        raise ReleaseError("publication approval row license is not allowed")
    if release_license != row_license:
        raise ReleaseError("release license must match the approved per-row license")

    quality = approval.get("quality_audit")
    if not isinstance(quality, Mapping):
        raise ReleaseError("publication approval quality audit is missing")
    if quality.get("clean") is not True or list(quality.get("risk_flags") or []):
        raise ReleaseError("publication approval quality audit is not clean")
    audit_sha = quality.get("artifact_sha256")
    if not isinstance(audit_sha, str) or not _HEX64.fullmatch(audit_sha):
        raise ReleaseError("publication approval quality-audit checksum is missing")

    approved_scope = approval.get("prompt_scope")
    if not isinstance(approved_scope, Mapping) or dict(approved_scope) != dict(prompt_scope):
        raise ReleaseError("publication approval prompt scope does not match the source bundle")
    return approval


def _verify_prompt_scope(raw_scope: Any) -> dict[str, Any]:
    if not isinstance(raw_scope, Mapping):
        raise ReleaseError("source prompt_scope is missing")
    scope = dict(raw_scope)
    prompt_count = scope.get("prompt_count")
    prompt_sha256 = scope.get("prompt_sha256")
    closure_status = scope.get("closure_status")
    full_closure = scope.get("full_flywheel_closure")
    if not isinstance(prompt_count, int) or isinstance(prompt_count, bool) or prompt_count <= 0:
        raise ReleaseError("prompt_scope prompt_count is invalid")
    if not isinstance(prompt_sha256, str) or not _HEX64.fullmatch(prompt_sha256):
        raise ReleaseError("prompt_scope prompt_sha256 is invalid")
    if closure_status not in {"partial", "exact"}:
        raise ReleaseError("prompt_scope closure_status must be partial or exact")
    if full_closure is not (closure_status == "exact"):
        raise ReleaseError("prompt_scope closure status and full_flywheel_closure disagree")
    closure_sha = scope.get("closure_evidence_sha256")
    if closure_status == "exact":
        if not isinstance(closure_sha, str) or not _HEX64.fullmatch(closure_sha):
            raise ReleaseError("exact prompt scope requires closure evidence")
    elif closure_sha not in {None, ""}:
        raise ReleaseError("partial prompt scope must not claim exact closure evidence")
    return scope


def _prompt_from_sft(row: Mapping[str, Any]) -> str:
    messages = row.get("messages")
    if not isinstance(messages, list):
        return ""
    for message in messages:
        if isinstance(message, Mapping) and message.get("role") == "user":
            content = message.get("content")
            return content if isinstance(content, str) else ""
    return ""


def _assistant_from_sft(row: Mapping[str, Any]) -> str:
    messages = row.get("messages")
    if not isinstance(messages, list):
        return ""
    for message in reversed(messages):
        if isinstance(message, Mapping) and message.get("role") in {"assistant", "model"}:
            content = message.get("content")
            return content if isinstance(content, str) else ""
    return ""


def _normalise_row(row: Mapping[str, Any], *, preference: bool) -> dict[str, Any]:
    fields = PUBLIC_PREFERENCE_FIELDS if preference else PUBLIC_SFT_FIELDS
    public = {key: row[key] for key in fields if key in row}
    public["sha256"] = training_row_sha256(public)
    return public


def _assert_unique(rows: Sequence[Mapping[str, Any]], field: str, label: str) -> None:
    values = [str(row.get(field) or "") for row in rows]
    if any(not value for value in values):
        raise ReleaseError(f"{label} contains a missing {field}")
    if len(values) != len(set(values)):
        raise ReleaseError(f"{label} contains duplicate {field} values")


def _assert_rows_public_safe(
    rows: Sequence[Mapping[str, Any]],
    label: str,
    *,
    row_license: str,
    rights_holder: str,
) -> None:
    for row in rows:
        if pii_findings(row):
            raise ReleaseError(f"{label} contains PII detector findings")
        if _contains_private_path_or_secret(row):
            raise ReleaseError(f"{label} contains a private path or credential signature")
        if any(_HIDDEN_REASONING.search(text) for text in _strings(row)):
            raise ReleaseError(f"{label} contains hidden-reasoning markup")
        if row.get("license") != row_license or row_license not in ALLOWED_ROW_LICENSES:
            raise ReleaseError(f"{label} contains a row outside the approved license")
        if row.get("rights_holder") != rights_holder:
            raise ReleaseError(f"{label} contains a row outside the approved rights holder")
        if row.get("allow_training_use") is not True:
            raise ReleaseError(f"{label} contains a row without training-use permission")
        if row.get("allow_public_redistribution") is not True:
            raise ReleaseError(f"{label} contains a row without redistribution permission")
        revision = str(row.get("model_revision") or "").strip().lower()
        if revision in UNPINNED_REVISIONS or not _HEX40_OR_64.fullmatch(revision):
            raise ReleaseError(f"{label} contains an unpinned model revision")
        quality = row.get("quality_gate")
        if not isinstance(quality, Mapping) or quality.get("accepted") is not True:
            raise ReleaseError(f"{label} contains a row without an accepted quality gate")
        if quality.get("unsafe_advice_filtered") is not True:
            raise ReleaseError(f"{label} contains a row without the unsafe-advice gate")
        if row.get("sha256") != training_row_sha256(row):
            raise ReleaseError(f"{label} contains a row-integrity mismatch")


def _grounded_fraction(rows: Sequence[Mapping[str, Any]]) -> float:
    if not rows:
        return 0.0
    grounded = 0
    for row in rows:
        refs = row.get("source_refs") if isinstance(row.get("source_refs"), list) else []
        packs = row.get("knowledge_pack_refs") if isinstance(row.get("knowledge_pack_refs"), list) else []
        if any(str(item).strip() for item in [*refs, *packs]):
            grounded += 1
    return grounded / len(rows)


def _preference_length_ratio(rows: Sequence[Mapping[str, Any]]) -> float:
    chosen = [len(str(row.get("chosen") or "")) for row in rows]
    rejected = [len(str(row.get("rejected") or "")) for row in rows]
    chosen_mean = sum(chosen) / len(chosen) if chosen else 0.0
    rejected_mean = sum(rejected) / len(rejected) if rejected else 0.0
    return chosen_mean / rejected_mean if rejected_mean else float("inf")


def _verify_heldout_rows(
    rows: Sequence[Mapping[str, Any]],
    *,
    split: str,
    declared_hashes: set[str],
    declared_lineages: set[str],
    row_license: str,
    rights_holder: str,
) -> None:
    if not rows:
        raise ReleaseError(f"held-out {split} rows are empty")
    _assert_unique(rows, "id", f"held-out {split}")
    _assert_rows_public_safe(
        rows,
        f"held-out {split}",
        row_license=row_license,
        rights_holder=rights_holder,
    )
    for row in rows:
        if row.get("split") != split:
            raise ReleaseError(f"held-out {split} artifact contains a different split")
        if pii_findings(row) or _contains_private_path_or_secret(row):
            raise ReleaseError(f"held-out {split} rows fail privacy scanning")
        prompt = _prompt_from_sft(row)
        lineage = str(row.get("lineage_id") or "")
        if not prompt or canonical_sha256(prompt) not in declared_hashes:
            raise ReleaseError(f"held-out {split} prompt hash is not declared")
        if not lineage or lineage not in declared_lineages:
            raise ReleaseError(f"held-out {split} lineage is not declared")


def inspect_source_bundle(
    manifest_path: Path,
    *,
    approval_path: Path,
    min_sft_rows: int = 20,
    min_preference_rows: int = 20,
    min_grounded_fraction: float = 0.8,
) -> dict[str, Any]:
    """Load and verify one A-00 training bundle without writing output."""

    manifest_path = manifest_path.resolve(strict=True)
    manifest = _read_json(manifest_path)
    manifest_sha256 = _sha256_file(manifest_path)
    if manifest.get("schema_version") != "1.0":
        raise ReleaseError("source manifest schema_version is not 1.0")
    if manifest.get("handoff_kind") != SOURCE_HANDOFF_KIND:
        raise ReleaseError("source manifest handoff_kind is not the A-00 training bundle contract")
    if manifest.get("safe_to_train") is not True:
        raise ReleaseError("source manifest is not marked safe_to_train")
    source_validation = manifest.get("training_validation")
    if not isinstance(source_validation, Mapping) or source_validation.get("ok") is not True:
        raise ReleaseError("source training validation is not passing")

    reason_policy = str(manifest.get("reasoning_data_policy") or "")
    if not reason_policy:
        raise ReleaseError("source reasoning-data policy is missing")
    source_scope = manifest.get("source_scope")
    if not isinstance(source_scope, Mapping):
        raise ReleaseError("source-scope declaration is missing")
    if source_scope.get("raw_publication_ingestion_by_default") is not False:
        raise ReleaseError("raw publication ingestion must be disabled by default")
    prompt_scope = _verify_prompt_scope(manifest.get("prompt_scope"))
    approval = _verified_approval(
        approval_path,
        source_manifest_sha256=manifest_sha256,
        prompt_scope=prompt_scope,
    )
    row_license = str(approval["row_license"])
    rights_holder = str(approval["rights_holder"])

    artifacts = manifest.get("artifacts")
    artifact_hashes = manifest.get("artifact_sha256")
    if not isinstance(artifacts, Mapping) or not isinstance(artifact_hashes, Mapping):
        raise ReleaseError("source artifact map or checksum map is missing")
    required = ("sft", "dpo", "sft_validation", "sft_test", "quarantine", "source_audit")
    resolved: dict[str, Path] = {}
    for key in required:
        path = _resolve_artifact(manifest_path, artifacts.get(key))
        expected = artifact_hashes.get(key)
        if not isinstance(expected, str) or not _HEX64.fullmatch(expected):
            raise ReleaseError(f"source checksum is missing for {key}")
        if _sha256_file(path) != expected:
            raise ReleaseError(f"source checksum mismatch for {key}")
        resolved[key] = path

    sft_rows = _read_jsonl(resolved["sft"])
    preference_rows = _read_jsonl(resolved["dpo"])
    validation_rows = _read_jsonl(resolved["sft_validation"])
    test_rows = _read_jsonl(resolved["sft_test"])
    if len(sft_rows) < min_sft_rows:
        raise ReleaseError(f"SFT row count is below release minimum ({min_sft_rows})")
    if len(preference_rows) < min_preference_rows:
        raise ReleaseError(f"preference row count is below release minimum ({min_preference_rows})")

    _assert_unique(sft_rows, "id", "SFT train")
    _assert_unique(preference_rows, "id", "preference train")
    if {str(row["id"]) for row in sft_rows} != {str(row["id"]) for row in preference_rows}:
        raise ReleaseError("SFT and preference train row ids do not match")

    _assert_rows_public_safe(
        sft_rows,
        "SFT train",
        row_license=row_license,
        rights_holder=rights_holder,
    )
    _assert_rows_public_safe(
        preference_rows,
        "preference train",
        row_license=row_license,
        rights_holder=rights_holder,
    )
    declared_hashes = {str(value) for value in manifest.get("heldout_prompt_sha256") or [] if str(value)}
    declared_lineages = {str(value) for value in manifest.get("heldout_lineage_ids") or [] if str(value)}
    if not declared_hashes or not declared_lineages:
        raise ReleaseError("held-out prompt hashes and lineage ids are required")
    _verify_heldout_rows(
        validation_rows,
        split="validation",
        declared_hashes=declared_hashes,
        declared_lineages=declared_lineages,
        row_license=row_license,
        rights_holder=rights_holder,
    )
    _verify_heldout_rows(
        test_rows,
        split="test",
        declared_hashes=declared_hashes,
        declared_lineages=declared_lineages,
        row_license=row_license,
        rights_holder=rights_holder,
    )

    actual_heldout_hashes = {
        canonical_sha256(_prompt_from_sft(row))
        for row in [*validation_rows, *test_rows]
    }
    actual_heldout_lineages = {
        str(row.get("lineage_id") or "")
        for row in [*validation_rows, *test_rows]
    }
    if actual_heldout_hashes != declared_hashes:
        raise ReleaseError("declared held-out prompt hashes do not exactly match held-out rows")
    if actual_heldout_lineages != declared_lineages:
        raise ReleaseError("declared held-out lineage ids do not exactly match held-out rows")

    train_lineages = {str(row.get("lineage_id") or "") for row in sft_rows}
    if train_lineages & declared_lineages:
        raise ReleaseError("training lineage overlaps a declared held-out lineage")
    train_hashes = {canonical_sha256(_prompt_from_sft(row)) for row in sft_rows}
    if train_hashes & declared_hashes:
        raise ReleaseError("training prompt overlaps a declared held-out prompt hash")

    validation = validate_training_rows(
        sft_rows,
        preference_rows,
        evaluation_prompt_hashes=declared_hashes,
        evaluation_lineage_ids=declared_lineages,
        require_preference=True,
    )
    if not validation["ok"]:
        failures = ",".join(validation.get("blocking_failures") or [])
        raise ReleaseError(f"canonical training contract failed: {failures}")

    grounded_fraction = min(_grounded_fraction(sft_rows), _grounded_fraction(preference_rows))
    if grounded_fraction < min_grounded_fraction:
        raise ReleaseError(
            f"source grounding coverage {grounded_fraction:.3f} is below {min_grounded_fraction:.3f}"
        )
    length_ratio = _preference_length_ratio(preference_rows)
    if length_ratio > 2.0:
        raise ReleaseError(f"preference chosen/rejected length ratio is too high ({length_ratio:.3f})")

    quarantine = _read_json(resolved["quarantine"])
    if quarantine.get("contains_raw_text") is not False:
        raise ReleaseError("quarantine artifact is not declared raw-text-free")
    if _contains_private_path_or_secret(quarantine) or pii_findings(quarantine):
        raise ReleaseError("quarantine artifact fails privacy scanning")
    source_audit = _read_json(resolved["source_audit"])
    if _contains_private_path_or_secret(source_audit) or pii_findings(source_audit):
        raise ReleaseError("source audit fails privacy scanning")
    source_approvals = source_audit.get("approvals")
    if source_audit.get("clean") is not True or list(source_audit.get("risk_flags") or []):
        raise ReleaseError("source audit is not clean")
    if not isinstance(source_approvals, Mapping) or any(
        source_approvals.get(key) is not True
        for key in ("curator_approved", "privacy_approved", "license_approved")
    ):
        raise ReleaseError("source-audit approvals are incomplete")
    if source_audit.get("prompt_scope") != prompt_scope:
        raise ReleaseError("source-audit prompt scope does not match the source manifest")
    if source_audit.get("quality_audit_sha256") != (approval.get("quality_audit") or {}).get(
        "artifact_sha256"
    ):
        raise ReleaseError("source audit and approval quality-audit checksums disagree")

    return {
        "manifest": manifest,
        "manifest_path": manifest_path,
        "manifest_sha256": manifest_sha256,
        "approval": approval,
        "approval_path": approval_path.resolve(strict=True),
        "approval_sha256": _sha256_file(approval_path.resolve(strict=True)),
        "prompt_scope": prompt_scope,
        "sft_rows": sft_rows,
        "preference_rows": preference_rows,
        "validation_rows": validation_rows,
        "test_rows": test_rows,
        "quarantine": quarantine,
        "source_audit": source_audit,
        "validation": validation,
        "grounded_fraction": grounded_fraction,
        "preference_length_ratio": length_ratio,
    }


def _safe_release_slug(value: Any) -> str:
    slug = _SAFE_RELEASE_ID.sub("-", str(value or "release").lower()).strip("-")
    return slug[:80] or "release"


def _file_entry(path: Path, *, rows: int | None = None) -> dict[str, Any]:
    entry: dict[str, Any] = {"sha256": _sha256_file(path), "bytes": path.stat().st_size}
    if rows is not None:
        entry["rows"] = rows
    return entry


def _prepare_output_dir(path: Path) -> Path:
    resolved_parent = path.parent.resolve()
    if path.exists():
        if not path.is_dir():
            raise ReleaseError("output path exists and is not a directory")
        if any(path.iterdir()):
            raise ReleaseError("output directory is not empty")
        return path.resolve()
    resolved_parent.mkdir(parents=True, exist_ok=True)
    path.mkdir()
    return path.resolve()


def build_release(
    manifest_path: Path,
    *,
    approval_path: Path,
    output_dir: Path,
    dataset_id: str = DEFAULT_DATASET_ID,
    title: str = DEFAULT_TITLE,
    min_sft_rows: int = 20,
    min_preference_rows: int = 20,
    min_grounded_fraction: float = 0.8,
) -> dict[str, Any]:
    """Verify, normalize, and write one public Kaggle dataset release."""

    if not _SAFE_DATASET_ID.fullmatch(dataset_id):
        raise ReleaseError("dataset id must use owner/slug form")
    inspected = inspect_source_bundle(
        manifest_path,
        approval_path=approval_path,
        min_sft_rows=min_sft_rows,
        min_preference_rows=min_preference_rows,
        min_grounded_fraction=min_grounded_fraction,
    )
    target = _prepare_output_dir(output_dir)

    sft_rows = [_normalise_row(row, preference=False) for row in inspected["sft_rows"]]
    preference_rows = [_normalise_row(row, preference=True) for row in inspected["preference_rows"]]
    validation_rows = [_normalise_row(row, preference=False) for row in inspected["validation_rows"]]
    test_rows = [_normalise_row(row, preference=False) for row in inspected["test_rows"]]
    manifest = inspected["manifest"]
    approval = inspected["approval"]
    release_license = str(approval["release_license"])
    declared_hashes = {str(value) for value in manifest["heldout_prompt_sha256"]}
    declared_lineages = {str(value) for value in manifest["heldout_lineage_ids"]}
    public_validation = validate_training_rows(
        sft_rows,
        preference_rows,
        evaluation_prompt_hashes=declared_hashes,
        evaluation_lineage_ids=declared_lineages,
        require_preference=True,
    )
    if not public_validation["ok"]:
        raise ReleaseError("normalized public rows failed the canonical training contract")

    paths = {
        "sft_train.jsonl": target / "sft_train.jsonl",
        "preference_train.jsonl": target / "preference_train.jsonl",
        "sft_validation.jsonl": target / "sft_validation.jsonl",
        "sft_test.jsonl": target / "sft_test.jsonl",
        "quarantine_summary.json": target / "quarantine_summary.json",
        "source_audit.json": target / "source_audit.json",
        "publication_approval.json": target / "publication_approval.json",
    }
    row_counts = {
        "sft_train.jsonl": _write_jsonl(paths["sft_train.jsonl"], sft_rows),
        "preference_train.jsonl": _write_jsonl(paths["preference_train.jsonl"], preference_rows),
        "sft_validation.jsonl": _write_jsonl(paths["sft_validation.jsonl"], validation_rows),
        "sft_test.jsonl": _write_jsonl(paths["sft_test.jsonl"], test_rows),
    }
    _write_json(paths["quarantine_summary.json"], inspected["quarantine"])
    _write_json(paths["source_audit.json"], inspected["source_audit"])
    _write_json(paths["publication_approval.json"], approval)

    source_id = str(manifest.get("id") or inspected["manifest_sha256"][:16])
    release_id = f"{_safe_release_slug(source_id)}-{inspected['manifest_sha256'][:12]}"
    file_entries = {
        name: _file_entry(path, rows=row_counts.get(name))
        for name, path in paths.items()
    }
    release_manifest: dict[str, Any] = {
        "schema_version": RELEASE_SCHEMA_VERSION,
        "handoff_kind": RELEASE_HANDOFF_KIND,
        "release_id": release_id,
        "created_at": _utc(),
        "dataset_id": dataset_id,
        "title": title,
        "public": True,
        "release_license": release_license,
        "source_bundle": {
            "id": source_id,
            "handoff_kind": manifest.get("handoff_kind"),
            "manifest_sha256": inspected["manifest_sha256"],
            "model": manifest.get("model"),
            "generator_mode": manifest.get("generator_mode"),
            "harness_profile": manifest.get("harness_profile"),
        },
        "publication_approval": {
            "handoff_kind": approval.get("handoff_kind"),
            "approval_sha256": _sha256_file(paths["publication_approval.json"]),
            "approved_by": approval.get("approved_by"),
            "approved_at": approval.get("approved_at"),
            "rights_holder": approval.get("rights_holder"),
            "row_license": approval.get("row_license"),
            "allow_training_use": approval.get("allow_training_use"),
            "allow_public_redistribution": approval.get("allow_public_redistribution"),
        },
        "prompt_scope": inspected["prompt_scope"],
        "release_tier": (
            "complete-flywheel" if inspected["prompt_scope"]["closure_status"] == "exact" else "preview"
        ),
        "counts": {
            "sft_train": len(sft_rows),
            "preference_train": len(preference_rows),
            "sft_validation": len(validation_rows),
            "sft_test": len(test_rows),
            "quarantined": len(inspected["quarantine"].get("rows") or []),
        },
        "heldout_prompt_sha256": sorted(declared_hashes),
        "heldout_lineage_ids": sorted(declared_lineages),
        "reasoning_data_policy": (
            "Final answers, citations/source references, preference rationales, and deliberately authored "
            "structured rationales only. Private hidden chain-of-thought is neither requested nor published."
        ),
        "gates": {
            "source_manifest_safe_to_train": True,
            "canonical_training_contract": public_validation,
            "source_grounded_fraction": round(float(inspected["grounded_fraction"]), 4),
            "preference_chosen_over_rejected_length_ratio": round(
                float(inspected["preference_length_ratio"]), 4
            ),
            "runtime_trace_metadata_removed": True,
            "private_paths_and_secret_signatures_absent": True,
        },
        "files": file_entries,
        "safe_to_publish": True,
    }

    dataset_metadata = {
        "title": title,
        "id": dataset_id,
        "licenses": [{"name": release_license}],
        "subtitle": "Manifest-bound SFT and preference data from the DueCare harness",
        "description": (
            "A gated DueCare training release containing lineage-isolated SFT, preference, validation, and "
            "test rows. Every public row carries provenance, license, quality-gate, immutable model revision, "
            "and SHA-256 metadata. Hidden chain-of-thought, private case material, volatile contact details, "
            "and failing candidate rows are excluded. See DATA_CARD.md and release-manifest.json."
        ),
        "keywords": [],
        "collaborators": [],
    }
    _write_json(target / "dataset-metadata.json", dataset_metadata)
    data_card = f"""# {title}

Release `{release_id}` is a manifest-bound export of the DueCare harness-to-training-data flywheel.

## Contents

- `{len(sft_rows)}` SFT train rows
- `{len(preference_rows)}` preference train rows
- `{len(validation_rows)}` validation rows
- `{len(test_rows)}` test rows
- metadata-only quarantine and source-audit artifacts

## Training use

Keep every lineage in exactly one split. Verify `release-manifest.json` and every row SHA-256 before
training. The active DueCare A-00 Kaggle workbench can run response-only LoRA SFT followed by DPO and
writes an adapter completion manifest pinned to the base model revision.

## Reasoning-data boundary

This release contains final answers, citations/source references, preference rationales, and deliberately
authored structured rationales. It does not request, recover, or publish private hidden chain-of-thought.

## Safety and provenance

Rows failing privacy, source grounding, unsafe-advice, licensing, held-out isolation, integrity, or model
revision gates are not copied into this directory. Runtime traces are removed from public rows. This is
synthetic model-training data, not legal advice or a worker-contact dataset.

License: {release_license}. Per-row generation provenance is retained in the JSONL metadata.
"""
    (target / "DATA_CARD.md").write_text(data_card, encoding="utf-8")
    release_manifest["files"].update(
        {
            "dataset-metadata.json": _file_entry(target / "dataset-metadata.json"),
            "DATA_CARD.md": _file_entry(target / "DATA_CARD.md"),
        }
    )
    _write_json(target / "release-manifest.json", release_manifest)
    verify_release_dir(target)
    return release_manifest


def verify_release_dir(release_dir: Path) -> dict[str, Any]:
    """Verify a built directory immediately before a Kaggle upload."""

    root = release_dir.resolve(strict=True)
    if not root.is_dir():
        raise ReleaseError("release path is not a directory")
    manifest = _read_json(root / "release-manifest.json")
    if manifest.get("schema_version") != RELEASE_SCHEMA_VERSION:
        raise ReleaseError("release schema_version is invalid")
    if manifest.get("handoff_kind") != RELEASE_HANDOFF_KIND:
        raise ReleaseError("release handoff_kind is invalid")
    if manifest.get("safe_to_publish") is not True or manifest.get("public") is not True:
        raise ReleaseError("release is not marked safe and public")
    metadata = _read_json(root / "dataset-metadata.json")
    if metadata.get("id") != manifest.get("dataset_id"):
        raise ReleaseError("dataset metadata id does not match the release manifest")
    if not metadata.get("licenses"):
        raise ReleaseError("dataset metadata license is missing")
    subtitle = str(metadata.get("subtitle") or "")
    if not 20 <= len(subtitle) <= 80:
        raise ReleaseError("dataset metadata subtitle must be 20-80 characters for Kaggle")

    prompt_scope = _verify_prompt_scope(manifest.get("prompt_scope"))
    source_bundle = manifest.get("source_bundle")
    if not isinstance(source_bundle, Mapping):
        raise ReleaseError("release source-bundle summary is missing")
    source_manifest_sha = source_bundle.get("manifest_sha256")
    if not isinstance(source_manifest_sha, str) or not _HEX64.fullmatch(source_manifest_sha):
        raise ReleaseError("release source-manifest checksum is missing")
    approval_path = root / "publication_approval.json"
    approval = _verified_approval(
        approval_path,
        source_manifest_sha256=source_manifest_sha,
        prompt_scope=prompt_scope,
    )
    approval_summary = manifest.get("publication_approval")
    if not isinstance(approval_summary, Mapping):
        raise ReleaseError("release publication-approval summary is missing")
    if approval_summary.get("approval_sha256") != _sha256_file(approval_path):
        raise ReleaseError("publication-approval checksum does not match the release summary")
    if manifest.get("release_license") != approval.get("release_license"):
        raise ReleaseError("release license does not match the approval")
    metadata_licenses = {
        str(item.get("name") or "")
        for item in metadata.get("licenses") or []
        if isinstance(item, Mapping)
    }
    if metadata_licenses != {str(approval.get("release_license"))}:
        raise ReleaseError("dataset metadata license does not match the approval")

    declared = manifest.get("files")
    if not isinstance(declared, Mapping) or not declared:
        raise ReleaseError("release file map is missing")
    for name, details in declared.items():
        if not isinstance(name, str) or Path(name).name != name:
            raise ReleaseError("release file map contains an unsafe path")
        if not isinstance(details, Mapping):
            raise ReleaseError(f"release file metadata is invalid: {name}")
        path = (root / name).resolve(strict=True)
        if not _contained(path, root) or not path.is_file():
            raise ReleaseError(f"release file escapes the release directory: {name}")
        if path.is_symlink():
            raise ReleaseError(f"release file must not be a symlink: {name}")
        expected = details.get("sha256")
        if not isinstance(expected, str) or _sha256_file(path) != expected:
            raise ReleaseError(f"release file checksum mismatch: {name}")
        if int(details.get("bytes", -1)) != path.stat().st_size:
            raise ReleaseError(f"release file size mismatch: {name}")
    actual_names = {path.name for path in root.iterdir() if path.is_file()}
    expected_names = set(declared) | {"release-manifest.json"}
    if actual_names != expected_names:
        raise ReleaseError("release directory contains undeclared or missing files")
    if any(path.is_dir() for path in root.iterdir()):
        raise ReleaseError("release directory must not contain subdirectories")
    if _contains_private_path_or_secret(manifest) or _contains_private_path_or_secret(metadata):
        raise ReleaseError("release metadata contains a private path or credential signature")

    required_data_files = {
        "sft_train.jsonl",
        "preference_train.jsonl",
        "sft_validation.jsonl",
        "sft_test.jsonl",
        "quarantine_summary.json",
        "source_audit.json",
        "publication_approval.json",
        "dataset-metadata.json",
        "DATA_CARD.md",
    }
    if set(declared) != required_data_files:
        raise ReleaseError("release file map does not match the required publication surface")

    sft_rows = _read_jsonl(root / "sft_train.jsonl")
    preference_rows = _read_jsonl(root / "preference_train.jsonl")
    validation_rows = _read_jsonl(root / "sft_validation.jsonl")
    test_rows = _read_jsonl(root / "sft_test.jsonl")
    row_license = str(approval["row_license"])
    rights_holder = str(approval["rights_holder"])
    for rows, label, allowed in (
        (sft_rows, "SFT train", set(PUBLIC_SFT_FIELDS) | {"sha256"}),
        (preference_rows, "preference train", set(PUBLIC_PREFERENCE_FIELDS) | {"sha256"}),
        (validation_rows, "SFT validation", set(PUBLIC_SFT_FIELDS) | {"sha256"}),
        (test_rows, "SFT test", set(PUBLIC_SFT_FIELDS) | {"sha256"}),
    ):
        _assert_rows_public_safe(
            rows,
            label,
            row_license=row_license,
            rights_holder=rights_holder,
        )
        if any(set(row) - allowed for row in rows):
            raise ReleaseError(f"{label} contains undeclared public fields")
    _assert_unique(sft_rows, "id", "SFT train")
    _assert_unique(preference_rows, "id", "preference train")
    if {str(row["id"]) for row in sft_rows} != {str(row["id"]) for row in preference_rows}:
        raise ReleaseError("release SFT and preference row ids do not match")

    declared_hashes = {str(value) for value in manifest.get("heldout_prompt_sha256") or [] if str(value)}
    declared_lineages = {str(value) for value in manifest.get("heldout_lineage_ids") or [] if str(value)}
    _verify_heldout_rows(
        validation_rows,
        split="validation",
        declared_hashes=declared_hashes,
        declared_lineages=declared_lineages,
        row_license=row_license,
        rights_holder=rights_holder,
    )
    _verify_heldout_rows(
        test_rows,
        split="test",
        declared_hashes=declared_hashes,
        declared_lineages=declared_lineages,
        row_license=row_license,
        rights_holder=rights_holder,
    )
    actual_heldout_hashes = {
        canonical_sha256(_prompt_from_sft(row)) for row in [*validation_rows, *test_rows]
    }
    actual_heldout_lineages = {
        str(row.get("lineage_id") or "") for row in [*validation_rows, *test_rows]
    }
    if declared_hashes != actual_heldout_hashes or declared_lineages != actual_heldout_lineages:
        raise ReleaseError("release held-out declarations do not exactly match held-out rows")
    train_hashes = {canonical_sha256(_prompt_from_sft(row)) for row in sft_rows}
    train_lineages = {str(row.get("lineage_id") or "") for row in sft_rows}
    if train_hashes & declared_hashes or train_lineages & declared_lineages:
        raise ReleaseError("release train rows overlap the held-out set")
    contract = validate_training_rows(
        sft_rows,
        preference_rows,
        evaluation_prompt_hashes=declared_hashes,
        evaluation_lineage_ids=declared_lineages,
        require_preference=True,
    )
    if not contract["ok"]:
        raise ReleaseError("release rows fail the canonical training contract")
    if _preference_length_ratio(preference_rows) > 2.0:
        raise ReleaseError("release preference rows fail the length-bias gate")
    if min(_grounded_fraction(sft_rows), _grounded_fraction(preference_rows)) < 0.8:
        raise ReleaseError("release rows fail the source-grounding coverage gate")

    counts = manifest.get("counts") if isinstance(manifest.get("counts"), Mapping) else {}
    expected_counts = {
        "sft_train": len(sft_rows),
        "preference_train": len(preference_rows),
        "sft_validation": len(validation_rows),
        "sft_test": len(test_rows),
    }
    if any(counts.get(key) != value for key, value in expected_counts.items()):
        raise ReleaseError("release manifest row counts do not match the JSONL files")
    for name, value in (
        ("sft_train.jsonl", len(sft_rows)),
        ("preference_train.jsonl", len(preference_rows)),
        ("sft_validation.jsonl", len(validation_rows)),
        ("sft_test.jsonl", len(test_rows)),
    ):
        if declared[name].get("rows") != value:
            raise ReleaseError(f"release file row count mismatch: {name}")

    source_audit = _read_json(root / "source_audit.json")
    if source_audit.get("clean") is not True or list(source_audit.get("risk_flags") or []):
        raise ReleaseError("release source audit is not clean")
    source_approvals = source_audit.get("approvals")
    if not isinstance(source_approvals, Mapping) or any(
        source_approvals.get(key) is not True
        for key in ("curator_approved", "privacy_approved", "license_approved")
    ):
        raise ReleaseError("release source-audit approvals are incomplete")
    if source_audit.get("prompt_scope") != prompt_scope:
        raise ReleaseError("release source-audit prompt scope does not match")
    quality = approval.get("quality_audit") or {}
    if source_audit.get("quality_audit_sha256") != quality.get("artifact_sha256"):
        raise ReleaseError("release source audit and approval quality-audit checksums disagree")
    expected_tier = "complete-flywheel" if prompt_scope["closure_status"] == "exact" else "preview"
    if manifest.get("release_tier") != expected_tier:
        raise ReleaseError("release tier does not match prompt closure status")
    return {
        "ok": True,
        "release_id": manifest.get("release_id"),
        "dataset_id": manifest.get("dataset_id"),
        "files": len(declared),
        "counts": manifest.get("counts"),
    }


def _default_output(manifest_path: Path) -> Path:
    digest = _sha256_file(manifest_path)[:12]
    return ROOT / "reports" / "kaggle_training_releases" / f"release-{digest}"


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description=__doc__)
    sub = parser.add_subparsers(dest="command", required=True)
    build = sub.add_parser("build", help="verify one A-00 bundle and create a Kaggle release directory")
    build.add_argument("--manifest", type=Path, required=True)
    build.add_argument(
        "--approval",
        type=Path,
        required=True,
        help="manifest-bound curator/privacy/license/publication approval JSON",
    )
    build.add_argument("--output-dir", type=Path)
    build.add_argument("--dataset-id", default=DEFAULT_DATASET_ID)
    build.add_argument("--title", default=DEFAULT_TITLE)
    build.add_argument("--min-sft-rows", type=int, default=20)
    build.add_argument("--min-preference-rows", type=int, default=20)
    build.add_argument("--min-grounded-fraction", type=float, default=0.8)
    verify = sub.add_parser("verify", help="re-verify a built release directory without modifying it")
    verify.add_argument("--release-dir", type=Path, required=True)
    return parser


def main(argv: Sequence[str] | None = None) -> int:
    args = build_parser().parse_args(argv)
    try:
        if args.command == "verify":
            report = verify_release_dir(args.release_dir)
        else:
            output_dir = args.output_dir or _default_output(args.manifest)
            report = build_release(
                args.manifest,
                approval_path=args.approval,
                output_dir=output_dir,
                dataset_id=args.dataset_id,
                title=args.title,
                min_sft_rows=max(1, args.min_sft_rows),
                min_preference_rows=max(1, args.min_preference_rows),
                min_grounded_fraction=min(1.0, max(0.0, args.min_grounded_fraction)),
            )
        print(json.dumps(report, ensure_ascii=False, indent=2))
        return 0
    except (OSError, ReleaseError) as exc:
        print(f"[kaggle-training-release] BLOCKED: {exc}", file=sys.stderr)
        return 2


if __name__ == "__main__":
    raise SystemExit(main())
