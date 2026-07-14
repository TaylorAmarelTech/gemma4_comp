#!/usr/bin/env python3
"""Validate and load a manifest-bound DueCare SFT/preference bundle.

This module is the fail-closed boundary shared by standalone GPU trainers.  It
accepts either an A-00 source bundle or a verified Kaggle training-data release,
checks every trainer and held-out artifact against its manifest digest, proves
the declared held-out hashes and lineages from the validation/test rows, and
then reruns the canonical ``duecare.chat.training_contract`` validator.

The returned rows are the rows read *after* checksum verification.  Trainers
must consume these rows instead of separately reloading the input paths.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import re
import sys
from collections.abc import Mapping, Sequence
from dataclasses import dataclass
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[1]
CHAT_SRC = ROOT / "packages" / "duecare-llm-chat" / "src"
if str(CHAT_SRC) not in sys.path:
    sys.path.insert(0, str(CHAT_SRC))

from duecare.chat.training_contract import canonical_sha256, validate_training_rows  # noqa: E402

SOURCE_HANDOFF_KIND = "duecare.a00.synthetic.training_bundle.v2"
RELEASE_HANDOFF_KIND = "duecare.kaggle.training_dataset_release.v1"
_HEX64 = re.compile(r"[0-9a-f]{64}")


class TrainingBundleError(ValueError):
    """A manifest or one of its bound artifacts failed a blocking gate."""


@dataclass(frozen=True)
class VerifiedTrainingBundle:
    """Rows and metadata proven by :func:`validate_training_bundle`."""

    manifest_sha256: str
    handoff_kind: str
    sft_sha256: str
    preference_sha256: str
    heldout_prompt_sha256: tuple[str, ...]
    evaluation_prompt_sha256: tuple[str, ...]
    heldout_lineage_ids: tuple[str, ...]
    sft_rows: tuple[dict[str, Any], ...]
    preference_rows: tuple[dict[str, Any], ...]
    contract: dict[str, Any]

    def summary(self) -> dict[str, Any]:
        """Return a path-free summary safe for logs and completion manifests."""

        return {
            "schema_version": "duecare.training.verified_bundle.v1",
            "ok": True,
            "handoff_kind": self.handoff_kind,
            "manifest_sha256": self.manifest_sha256,
            "sft_sha256": self.sft_sha256,
            "preference_sha256": self.preference_sha256,
            "heldout_prompt_hashes": len(self.heldout_prompt_sha256),
            "evaluation_prompt_hashes": len(self.evaluation_prompt_sha256),
            "heldout_lineages": len(self.heldout_lineage_ids),
            "counts": {
                "sft": len(self.sft_rows),
                "preference": len(self.preference_rows),
            },
            "blocking_failures": list(self.contract.get("blocking_failures") or []),
        }


def _sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def _read_json(path: Path, label: str) -> dict[str, Any]:
    try:
        value = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, UnicodeError, json.JSONDecodeError) as exc:
        raise TrainingBundleError(f"{label} is unreadable") from exc
    if not isinstance(value, dict):
        raise TrainingBundleError(f"{label} must contain a JSON object")
    return value


def _read_jsonl(path: Path, label: str) -> tuple[dict[str, Any], ...]:
    rows: list[dict[str, Any]] = []
    try:
        lines = path.read_text(encoding="utf-8").splitlines()
    except (OSError, UnicodeError) as exc:
        raise TrainingBundleError(f"{label} is unreadable") from exc
    for line_number, line in enumerate(lines, start=1):
        if not line.strip():
            continue
        try:
            row = json.loads(line)
        except json.JSONDecodeError as exc:
            raise TrainingBundleError(f"{label} has invalid JSON at line {line_number}") from exc
        if not isinstance(row, dict):
            raise TrainingBundleError(f"{label} has a non-object row at line {line_number}")
        rows.append(row)
    if not rows:
        raise TrainingBundleError(f"{label} is empty")
    return tuple(rows)


def _contained(path: Path, root: Path) -> bool:
    try:
        path.relative_to(root)
        return True
    except ValueError:
        return False


def _resolve_artifact(manifest_path: Path, raw_value: Any, label: str) -> Path:
    if not isinstance(raw_value, str) or not raw_value.strip():
        raise TrainingBundleError(f"{label} artifact declaration is missing")
    root = manifest_path.parent.resolve()
    raw = Path(raw_value)
    candidates: list[Path] = []
    if not raw.is_absolute():
        candidates.append(root / raw)
    elif _contained(raw.resolve(), root):
        candidates.append(raw)
    # A-00 manifests may be copied out of /kaggle/working with their artifacts.
    # The basename fallback preserves the bundle while containment prevents an
    # absolute source path from becoming an arbitrary file-read primitive.
    candidates.append(root / raw.name)
    seen: set[Path] = set()
    for candidate in candidates:
        try:
            resolved = candidate.resolve(strict=True)
        except OSError:
            continue
        if resolved in seen:
            continue
        seen.add(resolved)
        if not resolved.is_file() or not _contained(resolved, root):
            continue
        if candidate.is_symlink() or resolved.is_symlink():
            raise TrainingBundleError(f"{label} artifact must not be a symlink")
        return resolved
    raise TrainingBundleError(f"{label} artifact is missing from the bundle")


def _expected_digest(value: Any, label: str) -> str:
    if not isinstance(value, str) or _HEX64.fullmatch(value) is None:
        raise TrainingBundleError(f"{label} artifact checksum is missing or invalid")
    return value


def _verified_artifact(
    manifest_path: Path,
    *,
    raw_value: Any,
    expected: Any,
    label: str,
) -> Path:
    path = _resolve_artifact(manifest_path, raw_value, label)
    if _sha256_file(path) != _expected_digest(expected, label):
        raise TrainingBundleError(f"{label} artifact checksum mismatch")
    return path


def _prompt_from_sft(row: Mapping[str, Any]) -> str:
    messages = row.get("messages")
    if not isinstance(messages, Sequence) or isinstance(messages, (str, bytes, bytearray)):
        return ""
    for message in messages:
        if (
            isinstance(message, Mapping)
            and message.get("role") == "user"
            and isinstance(message.get("content"), str)
        ):
            return str(message["content"])
    return ""


def _hash_set(value: Any, label: str) -> set[str]:
    if not isinstance(value, list) or not value:
        raise TrainingBundleError(f"{label} declaration is missing")
    hashes = {str(item) for item in value}
    if len(hashes) != len(value) or any(_HEX64.fullmatch(item) is None for item in hashes):
        raise TrainingBundleError(f"{label} declaration contains duplicates or invalid hashes")
    return hashes


def _lineage_set(value: Any) -> set[str]:
    if not isinstance(value, list) or not value:
        raise TrainingBundleError("held-out lineage declaration is missing")
    lineages = {str(item).strip() for item in value}
    if "" in lineages or len(lineages) != len(value):
        raise TrainingBundleError("held-out lineage declaration contains blanks or duplicates")
    return lineages


def _source_paths(manifest_path: Path, manifest: Mapping[str, Any]) -> dict[str, Path]:
    if manifest.get("safe_to_train") is not True:
        raise TrainingBundleError("source manifest is not marked safe_to_train")
    declared_validation = manifest.get("training_validation")
    if not isinstance(declared_validation, Mapping) or declared_validation.get("ok") is not True:
        raise TrainingBundleError("source manifest does not declare a passing training validation")
    artifacts = manifest.get("artifacts")
    digests = manifest.get("artifact_sha256")
    if not isinstance(artifacts, Mapping) or not isinstance(digests, Mapping):
        raise TrainingBundleError("source artifact or checksum map is missing")
    return {
        label: _verified_artifact(
            manifest_path,
            raw_value=artifacts.get(key),
            expected=digests.get(key),
            label=label,
        )
        for key, label in (
            ("sft", "SFT train"),
            ("dpo", "preference train"),
            ("sft_validation", "SFT validation"),
            ("sft_test", "SFT test"),
        )
    }


def _release_paths(manifest_path: Path, manifest: Mapping[str, Any]) -> dict[str, Path]:
    if manifest.get("safe_to_publish") is not True or manifest.get("public") is not True:
        raise TrainingBundleError("release manifest is not marked safe_to_publish and public")
    gates = manifest.get("gates")
    contract = gates.get("canonical_training_contract") if isinstance(gates, Mapping) else None
    if (
        not isinstance(gates, Mapping)
        or gates.get("source_manifest_safe_to_train") is not True
        or not isinstance(contract, Mapping)
        or contract.get("ok") is not True
    ):
        raise TrainingBundleError("release manifest does not declare passing training gates")
    approval = manifest.get("publication_approval")
    if not isinstance(approval, Mapping) or approval.get("allow_training_use") is not True:
        raise TrainingBundleError("release manifest does not grant training use")
    files = manifest.get("files")
    if not isinstance(files, Mapping):
        raise TrainingBundleError("release file map is missing")
    paths: dict[str, Path] = {}
    for filename, label in (
        ("sft_train.jsonl", "SFT train"),
        ("preference_train.jsonl", "preference train"),
        ("sft_validation.jsonl", "SFT validation"),
        ("sft_test.jsonl", "SFT test"),
    ):
        entry = files.get(filename)
        if not isinstance(entry, Mapping):
            raise TrainingBundleError(f"{label} release entry is missing")
        paths[label] = _verified_artifact(
            manifest_path,
            raw_value=filename,
            expected=entry.get("sha256"),
            label=label,
        )
    return paths


def _same_file(selected: Path, declared: Path, label: str) -> None:
    try:
        resolved = selected.resolve(strict=True)
    except OSError as exc:
        raise TrainingBundleError(f"selected {label} file is missing") from exc
    if selected.is_symlink() or resolved.is_symlink() or resolved != declared:
        raise TrainingBundleError(f"selected {label} file is not the manifest-bound artifact")


def validate_training_bundle(
    manifest_path: Path,
    *,
    sft_path: Path,
    preference_path: Path,
) -> VerifiedTrainingBundle:
    """Verify ``manifest_path`` and return the exact rows safe for a GPU job."""

    try:
        manifest_path = manifest_path.resolve(strict=True)
    except OSError as exc:
        raise TrainingBundleError("training bundle manifest is required and must exist") from exc
    if not manifest_path.is_file() or manifest_path.is_symlink():
        raise TrainingBundleError("training bundle manifest must be a regular file")
    manifest = _read_json(manifest_path, "training bundle manifest")
    if manifest.get("schema_version") != "1.0":
        raise TrainingBundleError("training bundle schema_version is invalid")
    handoff_kind = str(manifest.get("handoff_kind") or "")
    if handoff_kind not in {SOURCE_HANDOFF_KIND, RELEASE_HANDOFF_KIND}:
        raise TrainingBundleError("training bundle handoff_kind is not supported")
    if not str(manifest.get("reasoning_data_policy") or "").strip():
        raise TrainingBundleError("training bundle reasoning-data policy is missing")
    if handoff_kind == SOURCE_HANDOFF_KIND:
        paths = _source_paths(manifest_path, manifest)
    else:
        paths = _release_paths(manifest_path, manifest)

    _same_file(sft_path, paths["SFT train"], "SFT train")
    _same_file(preference_path, paths["preference train"], "preference train")

    sft_rows = _read_jsonl(paths["SFT train"], "SFT train")
    preference_rows = _read_jsonl(paths["preference train"], "preference train")
    validation_rows = _read_jsonl(paths["SFT validation"], "SFT validation")
    test_rows = _read_jsonl(paths["SFT test"], "SFT test")

    for rows, split in ((validation_rows, "validation"), (test_rows, "test")):
        if any(row.get("split") != split for row in rows):
            raise TrainingBundleError(f"SFT {split} artifact contains a different split")

    heldout_hashes = _hash_set(manifest.get("heldout_prompt_sha256"), "held-out prompt hash")
    heldout_lineages = _lineage_set(manifest.get("heldout_lineage_ids"))
    heldout_rows = (*validation_rows, *test_rows)
    heldout_prompts = [_prompt_from_sft(row) for row in heldout_rows]
    heldout_row_lineages = [str(row.get("lineage_id") or "").strip() for row in heldout_rows]
    if any(not prompt.strip() for prompt in heldout_prompts):
        raise TrainingBundleError("held-out rows are missing user prompts")
    if any(not lineage for lineage in heldout_row_lineages):
        raise TrainingBundleError("held-out rows are missing lineage IDs")
    actual_heldout_hashes = {canonical_sha256(prompt) for prompt in heldout_prompts}
    actual_heldout_lineages = set(heldout_row_lineages)
    if len(actual_heldout_hashes) != len(heldout_rows):
        raise TrainingBundleError("held-out rows contain duplicate prompts")
    if len(actual_heldout_lineages) != len(heldout_rows):
        raise TrainingBundleError("held-out rows contain duplicate lineages")
    if heldout_hashes != actual_heldout_hashes:
        raise TrainingBundleError(
            "held-out prompt hashes do not exactly match validation/test rows"
        )
    if heldout_lineages != actual_heldout_lineages:
        raise TrainingBundleError("held-out lineages do not exactly match validation/test rows")

    frozen_raw = manifest.get("frozen_evaluation_prompt_sha256")
    frozen_hashes = (
        _hash_set(frozen_raw, "frozen evaluation prompt hash")
        if frozen_raw is not None
        else set()
    )
    evaluation_hashes = heldout_hashes | frozen_hashes
    contract = validate_training_rows(
        sft_rows,
        preference_rows,
        evaluation_prompt_hashes=evaluation_hashes,
        evaluation_lineage_ids=heldout_lineages,
        require_preference=True,
    )
    if not contract.get("ok"):
        failures = ",".join(str(item) for item in contract.get("blocking_failures") or [])
        raise TrainingBundleError(f"canonical training contract failed: {failures or 'unknown'}")

    return VerifiedTrainingBundle(
        manifest_sha256=_sha256_file(manifest_path),
        handoff_kind=handoff_kind,
        sft_sha256=_sha256_file(paths["SFT train"]),
        preference_sha256=_sha256_file(paths["preference train"]),
        heldout_prompt_sha256=tuple(sorted(heldout_hashes)),
        evaluation_prompt_sha256=tuple(sorted(evaluation_hashes)),
        heldout_lineage_ids=tuple(sorted(heldout_lineages)),
        sft_rows=sft_rows,
        preference_rows=preference_rows,
        contract=contract,
    )


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--manifest", type=Path, required=True)
    parser.add_argument("--sft", type=Path, required=True)
    parser.add_argument("--dpo", type=Path, required=True)
    args = parser.parse_args(argv)
    try:
        verified = validate_training_bundle(
            args.manifest,
            sft_path=args.sft,
            preference_path=args.dpo,
        )
    except TrainingBundleError as exc:
        print(f"[training-contract] BLOCKED: {exc}")
        return 1
    print(json.dumps(verified.summary(), indent=2, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
