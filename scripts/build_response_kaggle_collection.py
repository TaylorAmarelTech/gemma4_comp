#!/usr/bin/env python3
# ruff: noqa: E501
"""Build a private-first Kaggle collection from measured response candidates.

The source bundle is produced by ``build_response_preference_bundle.py``.  This
script verifies and streams every manifest-declared shard, preserves the source
bytes, writes review documentation and two CPU-only notebooks, and then emits a
deterministic release manifest.  It never uploads to Kaggle.

The default result is private and ``publication_ready=false``.  A public-ready
package requires a separate approval bound to the exact candidate-manifest hash
and to both the contamination ledger's file and canonical-content hashes.
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
import subprocess
import sys
import tempfile
import time
import unicodedata
from collections import Counter, defaultdict
from collections.abc import Iterable, Mapping, Sequence
from datetime import datetime
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[1]
CHAT_SRC = ROOT / "packages" / "duecare-llm-chat" / "src"
if str(CHAT_SRC) not in sys.path:
    sys.path.insert(0, str(CHAT_SRC))

from duecare.chat.training_contract import pii_findings  # noqa: E402

CANDIDATE_SCHEMA = "duecare.response-preference-candidate-bundle.v1"
CONTAMINATION_SCHEMA = "duecare.training-contamination-ledger.v1"
COLLECTION_SCHEMA = "duecare.kaggle.response-training-collection.v1"
RELEASE_SCHEMA = "duecare.kaggle.response-training-release.v1"
SHARD_INDEX_SCHEMA = "duecare.kaggle.response-training-shard-index.v1"
COLLECTION_MANIFEST_SCHEMA = "duecare.kaggle.response-training-local-collection.v1"
APPROVAL_SCHEMA = "1.0"
APPROVAL_KIND = "duecare.response-training.publication-approval.v1"
DEFAULT_SOURCE = (
    ROOT
    / "reports"
    / "response_preference_candidates"
    / "measured_response_v1"
    / "candidate-manifest.json"
)
DEFAULT_OUTPUT = ROOT / "reports" / "kaggle_publish" / "response_training_collection"
DEFAULT_DATASET_ID = "taylorsamarel/duecare-measured-response-training-corpus"
DEFAULT_TITLE = "DueCare Measured Response Training Corpus"
INTEGRITY_NOTEBOOK_ID = "taylorsamarel/duecare-response-corpus-integrity"
TRAINING_PLAN_NOTEBOOK_ID = "taylorsamarel/duecare-response-training-plan"
VISUAL_EXPLORER_NOTEBOOK_ID = "taylorsamarel/duecare-response-dataset-visual-explorer"
KAGGLE_CC_BY_4_LICENSE = "Attribution 4.0 International (CC BY 4.0)"
COMMIT_RENAME_RETRY_DELAYS_SECONDS = (0.05, 0.1, 0.2, 0.4, 0.8, 1.6, 3.2)
GRADE_GATE_ID = "complete_bounded_grade_evidence"
COMPONENT_BOUNDS = {"A": 25.0, "B": 20.0, "C": 25.0, "D": 15.0, "E": 15.0}
COMPONENT_NAMES = {
    "A": "indicator_identification",
    "B": "legal_grounding",
    "C": "protective_refusal",
    "D": "concrete_resources_and_actions",
    "E": "safety_and_privacy",
}
GRADE_BINDING_METHOD = (
    "unique_model_prompt_arm_key_within_manifest_bound_panel_and_response_snapshot"
)
REQUIRED_BLOCKING_GATES = {
    "accepted_candidates_present",
    "train_split_present",
    "diagnostic_splits_present",
    "source_artifacts_parse_clean",
    "exact_prompt_dedup",
    "prompt_cluster_split_isolation",
    "target_text_exact_canonical_dedup",
    "row_integrity",
    "negative_never_assistant_target",
    "emitted_models_rights_allowlisted",
    GRADE_GATE_ID,
    "graded_text_emitted_verbatim_without_redaction",
    "volatile_resources_require_versioned_binding",
    "within_split_target_text_no_overlap",
    "cross_split_target_text_no_overlap",
    "response_body_split_isolation",
}

LANES: dict[str, dict[str, str | None]] = {
    "sft_positive_train": {
        "prefix": "sft-positive-train-",
        "kind": "sft_positive",
        "split": "train",
    },
    "sft_positive_validation": {
        "prefix": "sft-positive-validation-",
        "kind": "sft_positive",
        "split": "validation",
    },
    "sft_positive_test": {
        "prefix": "sft-positive-test-",
        "kind": "sft_positive",
        "split": "test",
    },
    "dpo_preference_train": {
        "prefix": "dpo-preference-train-",
        "kind": "dpo_preference",
        "split": "train",
    },
    "dpo_preference_validation": {
        "prefix": "dpo-preference-validation-",
        "kind": "dpo_preference",
        "split": "validation",
    },
    "dpo_preference_test": {
        "prefix": "dpo-preference-test-",
        "kind": "dpo_preference",
        "split": "test",
    },
    "reward_labels_train": {
        "prefix": "reward-labels-train-",
        "kind": "reward_labels",
        "split": "train",
    },
    "reward_labels_validation": {
        "prefix": "reward-labels-validation-",
        "kind": "reward_labels",
        "split": "validation",
    },
    "reward_labels_test": {
        "prefix": "reward-labels-test-",
        "kind": "reward_labels",
        "split": "test",
    },
    "response_inventory": {
        "prefix": "response-inventory-",
        "kind": "response_inventory",
        "split": None,
    },
    "quarantine": {
        "prefix": "quarantine-",
        "kind": "quarantine",
        "split": None,
    },
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
    r"\bprivate\s+scratchpad\b|\b(?:analysis|reasoning)\s+scratchpad\b",
    re.I,
)
_PRIVATE_KEYS = {
    "access_token",
    "api_key",
    "chain_of_thought",
    "hidden_chain_of_thought",
    "private_reasoning",
    "provider_private_reasoning",
    "raw_provider_response",
    "runtime_trace",
}
_RAW_TEXT_KEYS = {"prompt", "response", "chosen", "rejected", "messages", "text"}
_APPROVAL_FIELDS = {
    "schema_version",
    "handoff_kind",
    "source_candidate_manifest_sha256",
    "contamination_ledger_file_sha256",
    "contamination_ledger_content_sha256",
    "approved_by",
    "approved_at",
    "allow_training_use",
    "allow_public_redistribution",
    "rights_holder",
    "row_license",
    "release_license",
    "approvals",
}
_APPROVAL_FLAGS = {
    "curator_approved",
    "privacy_approved",
    "license_approved",
    "quality_approved",
    "public_redistribution_approved",
}
_ISO_UTC = re.compile(r"\d{4}-\d{2}-\d{2}T\d{2}:\d{2}:\d{2}(?:Z|\+00:00)")


class CollectionError(RuntimeError):
    """Raised when the candidate cannot satisfy the packaging contract."""


def _sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def _canonical_sha256(value: Mapping[str, Any]) -> str:
    payload = dict(value)
    payload.pop("sha256", None)
    encoded = json.dumps(
        payload, ensure_ascii=False, sort_keys=True, separators=(",", ":")
    ).encode("utf-8")
    return hashlib.sha256(encoded).hexdigest()


def _release_payload_sha256(value: Mapping[str, Any]) -> str:
    payload = dict(value)
    payload.pop("release_manifest_payload_sha256", None)
    encoded = json.dumps(
        payload, ensure_ascii=False, sort_keys=True, separators=(",", ":")
    ).encode("utf-8")
    return hashlib.sha256(encoded).hexdigest()


def _text_sha256(value: str) -> str:
    return hashlib.sha256(value.encode("utf-8")).hexdigest()


def _canonical_response_sha256(value: str) -> str:
    canonical = " ".join(unicodedata.normalize("NFKC", value).split()).casefold()
    return hashlib.sha256(canonical.encode("utf-8")).hexdigest()


def _write_json(path: Path, value: Any) -> None:
    path.write_text(
        json.dumps(value, ensure_ascii=False, indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
        newline="\n",
    )


def _write_text(path: Path, value: str) -> None:
    path.write_text(value.rstrip() + "\n", encoding="utf-8", newline="\n")


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


def _read_object(path: Path, *, label: str) -> dict[str, Any]:
    if path.is_symlink() or not path.is_file():
        raise CollectionError(f"{label} is missing or symlinked: {path}")
    try:
        value = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as exc:
        raise CollectionError(f"{label} is not valid JSON: {path}") from exc
    if not isinstance(value, dict):
        raise CollectionError(f"{label} must be a JSON object")
    return value


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


def _private_key_paths(value: Any, prefix: str = "") -> list[str]:
    findings: list[str] = []
    if isinstance(value, Mapping):
        for key, child in value.items():
            name = str(key).lower()
            child_path = f"{prefix}.{name}" if prefix else name
            if name in _PRIVATE_KEYS:
                findings.append(child_path)
            findings.extend(_private_key_paths(child, child_path))
    elif isinstance(value, Sequence) and not isinstance(value, (str, bytes, bytearray)):
        for index, child in enumerate(value):
            findings.extend(_private_key_paths(child, f"{prefix}[{index}]"))
    return findings


def _forbidden_key_paths(
    value: Any, forbidden: set[str], prefix: str = ""
) -> list[str]:
    findings: list[str] = []
    if isinstance(value, Mapping):
        for key, child in value.items():
            name = str(key).lower()
            child_path = f"{prefix}.{name}" if prefix else name
            if name in forbidden:
                findings.append(child_path)
            findings.extend(_forbidden_key_paths(child, forbidden, child_path))
    elif isinstance(value, Sequence) and not isinstance(value, (str, bytes, bytearray)):
        for index, child in enumerate(value):
            findings.extend(_forbidden_key_paths(child, forbidden, f"{prefix}[{index}]"))
    return findings


def _scan_safe(value: Any, *, label: str, hidden_reasoning: bool = False) -> None:
    private_keys = _private_key_paths(value)
    if private_keys:
        raise CollectionError(f"{label} contains private fields: {private_keys[0]}")
    pii = pii_findings(value)
    if pii:
        raise CollectionError(f"{label} contains PII-like data: {pii[0]}")
    for text in _strings(value):
        if _PRIVATE_PATH.search(text):
            raise CollectionError(f"{label} contains a private local path")
        if _SECRET_LITERAL.search(text):
            raise CollectionError(f"{label} contains a credential-like secret")
        if hidden_reasoning and _HIDDEN_REASONING.search(text):
            raise CollectionError(f"{label} contains hidden-reasoning markup")


def _contained(path: Path, root: Path) -> bool:
    try:
        path.resolve().relative_to(root.resolve())
    except ValueError:
        return False
    return True


def _resolve_source(root: Path, relative: str, *, label: str) -> Path:
    if not isinstance(relative, str) or not relative or Path(relative).is_absolute():
        raise CollectionError(f"{label} must be a non-empty relative path")
    unresolved = root / relative
    if unresolved.is_symlink():
        raise CollectionError(f"{label} is symlinked")
    try:
        resolved = unresolved.resolve(strict=True)
    except OSError as exc:
        raise CollectionError(f"{label} is missing") from exc
    if not _contained(resolved, root) or not resolved.is_file():
        raise CollectionError(f"{label} escapes the candidate directory")
    return resolved


def _lane_for_name(name: str) -> tuple[str, Mapping[str, str | None]] | None:
    for lane, spec in LANES.items():
        if name.startswith(str(spec["prefix"])) and name.endswith(".jsonl"):
            return lane, spec
    return None


def _manifest_files(manifest: Mapping[str, Any]) -> Mapping[str, Any]:
    files = manifest.get("files")
    if not isinstance(files, Mapping):
        raise CollectionError("candidate manifest files must be an object")
    return files


def _verify_declaration(path: Path, declaration: Any, *, label: str) -> None:
    if not isinstance(declaration, Mapping):
        raise CollectionError(f"{label} declaration must be an object")
    expected_sha = declaration.get("sha256")
    if not isinstance(expected_sha, str) or not _HEX64.fullmatch(expected_sha):
        raise CollectionError(f"{label} declaration is missing a valid sha256")
    if _sha256_file(path) != expected_sha:
        raise CollectionError(f"{label} sha256 mismatch")
    expected_bytes = declaration.get("bytes")
    if expected_bytes is not None and expected_bytes != path.stat().st_size:
        raise CollectionError(f"{label} byte count mismatch")


def _assistant_target(row: Mapping[str, Any]) -> str:
    messages = row.get("messages")
    if not isinstance(messages, list) or len(messages) < 2:
        return ""
    assistants = [
        item.get("content")
        for item in messages
        if isinstance(item, Mapping) and item.get("role") == "assistant"
    ]
    return assistants[-1] if assistants and isinstance(assistants[-1], str) else ""


def _user_prompt(row: Mapping[str, Any]) -> str:
    messages = row.get("messages")
    if not isinstance(messages, list):
        return ""
    users = [
        item.get("content")
        for item in messages
        if isinstance(item, Mapping) and item.get("role") == "user"
    ]
    return users[0] if users and isinstance(users[0], str) else ""


def _number(value: Any, *, label: str, lower: float, upper: float) -> float:
    if isinstance(value, bool) or not isinstance(value, (int, float)):
        raise CollectionError(f"{label} must be numeric")
    result = float(value)
    if not math.isfinite(result) or result < lower or result > upper:
        raise CollectionError(f"{label} is outside [{lower:g}, {upper:g}]")
    return result


def _component_map(value: Any, *, label: str) -> dict[str, float]:
    if not isinstance(value, Mapping) or set(value) != set(COMPONENT_BOUNDS):
        raise CollectionError(f"{label} must contain exactly complete A-E components")
    return {
        key: _number(value[key], label=f"{label}.{key}", lower=0.0, upper=upper)
        for key, upper in COMPONENT_BOUNDS.items()
    }


def _quality_evidence_sha256(value: Mapping[str, Any]) -> str:
    payload = dict(value)
    payload.pop("evidence_sha256", None)
    encoded = json.dumps(
        payload, ensure_ascii=False, sort_keys=True, separators=(",", ":")
    ).encode("utf-8")
    return hashlib.sha256(encoded).hexdigest()


def _validate_grade_evidence(row: Mapping[str, Any], *, label: str) -> None:
    quality = row.get("quality_evidence")
    if not isinstance(quality, Mapping):
        raise CollectionError(f"{label} has no grade evidence")
    if quality.get("complete_bounded_components") is not True:
        raise CollectionError(f"{label} does not declare complete bounded grade components")
    declared_bounds = quality.get("component_bounds")
    if not isinstance(declared_bounds, Mapping) or set(declared_bounds) != set(
        COMPONENT_BOUNDS
    ):
        raise CollectionError(f"{label} does not declare the exact A-E component bounds")
    for key, upper in COMPONENT_BOUNDS.items():
        _number(
            declared_bounds[key],
            label=f"{label}.component_bounds.{key}",
            lower=upper,
            upper=upper,
        )
    evidence_sha = quality.get("evidence_sha256")
    if not isinstance(evidence_sha, str) or evidence_sha != _quality_evidence_sha256(quality):
        raise CollectionError(f"{label} grade evidence hash mismatch")
    if row.get("quality_evidence_sha256") != evidence_sha:
        raise CollectionError(f"{label} row quality-evidence binding is missing or inconsistent")

    source_binding = quality.get("source_grade_key_binding")
    required_binding_keys = {
        "model",
        "prompt_id_sha256",
        "baseline_arm",
        "teacher_arm",
        "method",
    }
    if not isinstance(source_binding, Mapping) or set(source_binding) != required_binding_keys:
        raise CollectionError(f"{label} source grade-key binding is incomplete")
    if source_binding.get("method") != GRADE_BINDING_METHOD:
        raise CollectionError(f"{label} source grade-key binding method is invalid")
    prompt_id_sha = source_binding.get("prompt_id_sha256")
    if not isinstance(prompt_id_sha, str) or not _HEX64.fullmatch(prompt_id_sha):
        raise CollectionError(f"{label} source grade-key prompt hash is invalid")
    for key in ("model", "baseline_arm", "teacher_arm"):
        if not isinstance(source_binding.get(key), str) or not source_binding[key]:
            raise CollectionError(f"{label} source grade-key {key} is invalid")
    if source_binding.get("model") != row.get("teacher_model"):
        raise CollectionError(f"{label} source grade-key model does not match the row")
    if source_binding.get("baseline_arm") != row.get("baseline_arm"):
        raise CollectionError(f"{label} source grade-key baseline arm mismatch")
    if source_binding.get("teacher_arm") != row.get("teacher_arm"):
        raise CollectionError(f"{label} source grade-key teacher arm mismatch")
    if row.get("prompt_id_sha256") != prompt_id_sha:
        raise CollectionError(f"{label} source grade-key prompt hash does not match the row")

    means = {
        "baseline": _component_map(
            quality.get("baseline_components"), label=f"{label}.baseline_components"
        ),
        "target": _component_map(
            quality.get("target_components"), label=f"{label}.target_components"
        ),
    }
    provenance = quality.get("judge_provenance")
    if not isinstance(provenance, Mapping) or set(provenance) != {"baseline", "target"}:
        raise CollectionError(f"{label} judge provenance must contain baseline and target")
    for arm in ("baseline", "target"):
        judges = provenance.get(arm)
        if not isinstance(judges, list) or not judges:
            raise CollectionError(f"{label} {arm} judge provenance is empty")
        judge_components: dict[str, list[float]] = defaultdict(list)
        judge_scores: list[float] = []
        for index, judge in enumerate(judges):
            if not isinstance(judge, Mapping):
                raise CollectionError(f"{label} {arm} judge {index} is invalid")
            if not isinstance(judge.get("judge"), str) or not judge["judge"]:
                raise CollectionError(f"{label} {arm} judge {index} has no identity")
            judge_sha = judge.get("judge_sha256")
            if not isinstance(judge_sha, str) or not _HEX64.fullmatch(judge_sha):
                raise CollectionError(f"{label} {arm} judge {index} hash is invalid")
            components = _component_map(
                judge.get("components"), label=f"{label}.{arm}.judge[{index}].components"
            )
            score = _number(
                judge.get("score_0_100"),
                label=f"{label}.{arm}.judge[{index}].score_0_100",
                lower=0.0,
                upper=100.0,
            )
            judge_scores.append(score)
            for component, value in components.items():
                judge_components[component].append(value)
        for component, values in judge_components.items():
            if abs(round(sum(values) / len(values), 1) - means[arm][component]) > 0.01:
                raise CollectionError(f"{label} {arm} mean component {component} is not reproducible")
        mean_score = _number(
            quality.get(f"{'baseline' if arm == 'baseline' else 'target'}_mean_score_0_100"),
            label=f"{label}.{arm}_mean_score_0_100",
            lower=0.0,
            upper=100.0,
        )
        if abs(round(sum(judge_scores) / len(judge_scores), 1) - mean_score) > 0.01:
            raise CollectionError(f"{label} {arm} mean score is not reproducible")

    deltas = quality.get("failure_dimension_deltas")
    if not isinstance(deltas, list) or len(deltas) != len(COMPONENT_BOUNDS):
        raise CollectionError(f"{label} must contain exactly five A-E grade deltas")
    observed: set[str] = set()
    for delta in deltas:
        if not isinstance(delta, Mapping):
            raise CollectionError(f"{label} contains an invalid grade delta")
        component = delta.get("dimension_id")
        if (
            not isinstance(component, str)
            or component not in COMPONENT_BOUNDS
            or component in observed
        ):
            raise CollectionError(f"{label} contains duplicate or unknown grade delta")
        if delta.get("dimension") != COMPONENT_NAMES[component]:
            raise CollectionError(f"{label} grade delta dimension name is invalid")
        observed.add(component)
        before = _number(
            delta.get("baseline"),
            label=f"{label}.delta.{component}.baseline",
            lower=0.0,
            upper=COMPONENT_BOUNDS[component],
        )
        after = _number(
            delta.get("target"),
            label=f"{label}.delta.{component}.target",
            lower=0.0,
            upper=COMPONENT_BOUNDS[component],
        )
        change = _number(
            delta.get("delta"),
            label=f"{label}.delta.{component}.delta",
            lower=-COMPONENT_BOUNDS[component],
            upper=COMPONENT_BOUNDS[component],
        )
        if abs(before - means["baseline"][component]) > 0.01 or abs(
            after - means["target"][component]
        ) > 0.01:
            raise CollectionError(f"{label} grade delta is not tied to the mean components")
        if abs(round(after - before, 1) - change) > 0.01:
            raise CollectionError(f"{label} grade delta is not reproducible")

    source_response_hashes = row.get("source_response_sha256")
    training_response_hashes = row.get("training_response_sha256")
    for name, hashes, keys in (
        ("source", source_response_hashes, {"baseline", "teacher"}),
        ("training", training_response_hashes, {"chosen", "rejected"}),
    ):
        if not isinstance(hashes, Mapping) or set(hashes) != keys:
            raise CollectionError(f"{label} {name} response hash binding is incomplete")
        if any(not isinstance(value, str) or not _HEX64.fullmatch(value) for value in hashes.values()):
            raise CollectionError(f"{label} {name} response hash binding is invalid")
    if (
        source_response_hashes.get("baseline") != training_response_hashes.get("rejected")
        or source_response_hashes.get("teacher") != training_response_hashes.get("chosen")
    ):
        raise CollectionError(f"{label} source response hashes do not bind the emitted responses")
    expected_binding = _canonical_sha256(
        {
            "quality_evidence_sha256": evidence_sha,
            "source_response_sha256": source_response_hashes,
            "training_response_sha256": training_response_hashes,
        }
    )
    if row.get("grade_evidence_binding_sha256") != expected_binding:
        raise CollectionError(f"{label} grade evidence is not bound to both response hashes")


def _validate_common_row(row: Mapping[str, Any], *, label: str) -> None:
    claimed = row.get("sha256")
    if not isinstance(claimed, str) or not _HEX64.fullmatch(claimed):
        raise CollectionError(f"{label} has no valid row sha256")
    if _canonical_sha256(row) != claimed:
        raise CollectionError(f"{label} row sha256 mismatch")
    _scan_safe(row, label=label, hidden_reasoning=True)


def _validate_and_record_pair_binding(
    row: Mapping[str, Any],
    *,
    prompt: str,
    lane_token: str,
    split: str,
    cluster: str,
    state: dict[str, Any],
    label: str,
) -> None:
    if not prompt.strip():
        raise CollectionError(f"{label} has no prompt text")
    prompt_sha = hashlib.sha256(prompt.strip().encode("utf-8")).hexdigest()
    if (
        row.get("training_prompt_sha256") != prompt_sha
        or row.get("source_prompt_sha256") != prompt_sha
    ):
        raise CollectionError(f"{label} prompt text is not bound to its declared hashes")
    if row.get("lineage_family_id") != cluster:
        raise CollectionError(f"{label} lineage family does not match its prompt cluster")
    lineage = row.get("lineage_id")
    suffix = {
        "sft": ":sft",
        "dpo": ":dpo",
        "reward_positive": ":reward-positive",
        "reward_negative": ":reward-negative",
    }[lane_token]
    if not isinstance(lineage, str) or not lineage.endswith(suffix):
        raise CollectionError(f"{label} lineage id does not match its training lane")
    response_hashes = row["training_response_sha256"]
    signature = (
        prompt_sha,
        row.get("prompt_id_sha256"),
        response_hashes["chosen"],
        response_hashes["rejected"],
        row.get("grade_evidence_binding_sha256"),
        lineage[: -len(suffix)],
    )
    key = (split, cluster)
    existing = state["pair_bindings"][key].get(lane_token)
    if existing is not None:
        raise CollectionError(f"{label} duplicates a lane within one response pair")
    state["pair_bindings"][key][lane_token] = signature


def _validate_training_row(
    row: Mapping[str, Any],
    *,
    lane: str,
    kind: str,
    split: str,
    state: dict[str, Any],
    label: str,
) -> None:
    if row.get("split") != split:
        raise CollectionError(f"{label} split does not match its shard")
    expected_training_use = split == "train"
    if row.get("allow_training_use") is not expected_training_use:
        raise CollectionError(f"{label} training-use flag does not match its split")
    if row.get("pii_checked") is not True:
        raise CollectionError(f"{label} is not privacy checked")
    if (
        row.get("allow_public_redistribution") is not False
        or row.get("publication_approval_required") is not True
    ):
        raise CollectionError(f"{label} bypasses release-level publication approval")
    rights = state["rights"]
    if row.get("license") != rights["row_license"] or row.get("rights_holder") != rights[
        "rights_holder"
    ]:
        raise CollectionError(f"{label} row rights do not match the candidate manifest")
    rights_basis = row.get("rights_basis")
    if (
        not isinstance(rights_basis, Mapping)
        or rights_basis.get("dataset_row_license") != rights["row_license"]
        or rights_basis.get("prompt_corpus_license") != rights["prompt_corpus_license"]
        or rights_basis.get("publication_status")
        != "separate_manifest_bound_approval_required"
    ):
        raise CollectionError(f"{label} row rights basis is incomplete or inconsistent")
    model = row.get("teacher_model")
    if not isinstance(model, str):
        raise CollectionError(f"{label} teacher model is not manifest allowlisted")
    model_license = state["allowed_models"].get(model)
    if model_license is None:
        raise CollectionError(f"{label} teacher model is not manifest allowlisted")
    if (
        row.get("teacher_model_license") != model_license
        or rights_basis.get("response_model_license") != model_license
    ):
        raise CollectionError(f"{label} model license does not match the manifest declaration")
    quality = row.get("quality_gate")
    if not isinstance(quality, Mapping) or quality.get("accepted") is not True:
        raise CollectionError(f"{label} did not pass its source quality gate")
    _validate_grade_evidence(row, label=label)
    cluster = row.get("prompt_cluster_id")
    if not isinstance(cluster, str) or not cluster:
        raise CollectionError(f"{label} has no prompt cluster")
    state["clusters"][split].add(cluster)

    if kind == "sft_positive":
        prompt_for_binding = _user_prompt(row)
        lane_token = "sft"
    elif kind == "dpo_preference":
        prompt_for_binding = row.get("prompt")
        lane_token = "dpo"
    elif kind == "reward_labels":
        prompt_for_binding = row.get("prompt")
        if row.get("label") not in (0, 1):
            raise CollectionError(f"{label} has an invalid reward label")
        lane_token = "reward_positive" if row["label"] == 1 else "reward_negative"
    else:  # pragma: no cover - guarded by the static lane map
        raise CollectionError(f"unsupported training lane: {lane}")
    if not isinstance(prompt_for_binding, str):
        raise CollectionError(f"{label} has no prompt text")
    _validate_and_record_pair_binding(
        row,
        prompt=prompt_for_binding,
        lane_token=lane_token,
        split=split,
        cluster=cluster,
        state=state,
        label=label,
    )

    if kind == "sft_positive":
        target = _assistant_target(row)
        if not target.strip():
            raise CollectionError(f"{label} has no positive assistant target")
        if row.get("assistant_target_allowed") is False:
            raise CollectionError(f"{label} forbids its own SFT target")
        target_sha = _text_sha256(target)
        declared = row.get("training_response_sha256")
        if not isinstance(declared, Mapping) or declared.get("chosen") != target_sha:
            raise CollectionError(f"{label} chosen target hash mismatch")
        state["sft_targets"].add(target_sha)
        state["response_exact_by_split"][split].add(target_sha)
        state["response_canonical_by_split"][split].add(
            _canonical_response_sha256(target)
        )
    elif kind == "dpo_preference":
        prompt, chosen, rejected = row.get("prompt"), row.get("chosen"), row.get("rejected")
        if not all(isinstance(item, str) and item.strip() for item in (prompt, chosen, rejected)):
            raise CollectionError(f"{label} has an incomplete same-prompt preference pair")
        if chosen == rejected:
            raise CollectionError(f"{label} chosen and rejected responses are identical")
        chosen_sha, rejected_sha = _text_sha256(chosen), _text_sha256(rejected)
        declared = row.get("training_response_sha256")
        if not isinstance(declared, Mapping) or declared.get("chosen") != chosen_sha or declared.get("rejected") != rejected_sha:
            raise CollectionError(f"{label} preference response hash mismatch")
        state["dpo_chosen"].add(chosen_sha)
        state["dpo_rejected"].add(rejected_sha)
        state["dpo_cluster_counts_by_split"][split][cluster] += 1
        for response_text, response_sha in ((chosen, chosen_sha), (rejected, rejected_sha)):
            state["dpo_exact_counts_by_split"][split][response_sha] += 1
            state["dpo_canonical_counts_by_split"][split][
                _canonical_response_sha256(response_text)
            ] += 1
        state["response_exact_by_split"][split].update((chosen_sha, rejected_sha))
        state["response_canonical_by_split"][split].update(
            (_canonical_response_sha256(chosen), _canonical_response_sha256(rejected))
        )
    elif kind == "reward_labels":
        response = row.get("response")
        label_value = row.get("label")
        if not isinstance(response, str) or not response.strip() or label_value not in (0, 1):
            raise CollectionError(f"{label} has an invalid reward label row")
        response_sha = _text_sha256(response)
        expected_response_sha = row["training_response_sha256"][
            "chosen" if label_value == 1 else "rejected"
        ]
        if response_sha != expected_response_sha:
            raise CollectionError(f"{label} reward response hash mismatch")
        if label_value == 0:
            if row.get("assistant_target_allowed") is not False:
                raise CollectionError(f"{label} negative reward text could become an SFT target")
            if row.get("training_lane") != "reward_label_only_never_sft_assistant_target":
                raise CollectionError(f"{label} negative reward row is not isolated to its lane")
            if (
                row.get("negative_only") is not True
                or quality.get("accepted_as") != "negative_reward_label_only"
                or quality.get("negative_only") is not True
                or quality.get("unsafe_advice_filtered") is not False
            ):
                raise CollectionError(
                    f"{label} must honestly mark negative-only text as not safety filtered"
                )
            state["reward_negative"].add(response_sha)
        else:
            state["reward_positive"].add(response_sha)
        state["response_exact_by_split"][split].add(response_sha)
        state["response_canonical_by_split"][split].add(
            _canonical_response_sha256(response)
        )
        state["reward_label_counts"][str(label_value)] += 1
    else:  # pragma: no cover - guarded by static lane map
        raise CollectionError(f"unsupported training lane: {lane}")


def _validate_metadata_row(row: Mapping[str, Any], *, kind: str, label: str) -> None:
    if row.get("contains_raw_text") is not False:
        raise CollectionError(f"{label} must remain raw-text-free")
    leaked = _forbidden_key_paths(row, _RAW_TEXT_KEYS)
    if leaked:
        raise CollectionError(f"{label} exposes raw-text fields: {leaked[0]}")
    if kind == "quarantine":
        reasons = row.get("reason_codes")
        if not isinstance(reasons, list) or not reasons:
            raise CollectionError(f"{label} has no quarantine reason")


def _copy_jsonl(
    source: Path,
    destination: Path,
    *,
    lane: str,
    spec: Mapping[str, str | None],
    declaration: Mapping[str, Any],
    state: dict[str, Any],
) -> dict[str, Any]:
    expected_rows = declaration.get("rows")
    rows = 0
    digest = hashlib.sha256()
    with source.open("rb") as reader, destination.open("wb") as writer:
        for raw_line in reader:
            digest.update(raw_line)
            writer.write(raw_line)
            rows += 1
            try:
                decoded = raw_line.decode("utf-8")
                row = json.loads(decoded)
            except (UnicodeDecodeError, json.JSONDecodeError) as exc:
                raise CollectionError(f"{source.name}:{rows} is not valid UTF-8 JSON") from exc
            if not isinstance(row, dict):
                raise CollectionError(f"{source.name}:{rows} must be a JSON object")
            label = f"{source.name}:{rows}"
            _validate_common_row(row, label=label)
            kind = str(spec["kind"])
            split = spec["split"]
            if isinstance(split, str):
                _validate_training_row(
                    row,
                    lane=lane,
                    kind=kind,
                    split=split,
                    state=state,
                    label=label,
                )
            else:
                _validate_metadata_row(row, kind=kind, label=label)
    if expected_rows is not None and rows != expected_rows:
        raise CollectionError(f"{source.name} row count mismatch")
    if digest.hexdigest() != declaration.get("sha256"):
        raise CollectionError(f"{source.name} changed while it was copied")
    if destination.stat().st_size != declaration.get("bytes"):
        raise CollectionError(f"{source.name} copied byte count mismatch")
    return {"path": destination.name, "rows": rows, "bytes": destination.stat().st_size, "sha256": digest.hexdigest()}


def _validate_cross_lane(
    state: Mapping[str, Any], manifest: Mapping[str, Any], lane_rows: Mapping[str, int]
) -> dict[str, Any]:
    overlaps = {
        "train_validation": sorted(state["clusters"]["train"] & state["clusters"]["validation"]),
        "train_test": sorted(state["clusters"]["train"] & state["clusters"]["test"]),
        "validation_test": sorted(state["clusters"]["validation"] & state["clusters"]["test"]),
    }
    if any(overlaps.values()):
        raise CollectionError("prompt clusters overlap between train and diagnostic splits")
    duplicate_prompt_clusters = {
        split: sorted(
            cluster
            for cluster, count in state["dpo_cluster_counts_by_split"][split].items()
            if count > 1
        )
        for split in ("train", "validation", "test")
    }
    if any(duplicate_prompt_clusters.values()):
        raise CollectionError("prompt clusters duplicate within a DPO split")
    within_response_duplicates = {
        "exact": {
            split: sorted(
                value
                for value, count in state["dpo_exact_counts_by_split"][split].items()
                if count > 1
            )
            for split in ("train", "validation", "test")
        },
        "canonical": {
            split: sorted(
                value
                for value, count in state["dpo_canonical_counts_by_split"][split].items()
                if count > 1
            )
            for split in ("train", "validation", "test")
        },
    }
    if any(
        values
        for duplicate_kind in within_response_duplicates.values()
        for values in duplicate_kind.values()
    ):
        raise CollectionError("response bodies duplicate within a DPO split")
    response_overlaps: dict[str, dict[str, list[str]]] = {
        "exact": {},
        "canonical": {},
    }
    for left, right in (
        ("train", "validation"),
        ("train", "test"),
        ("validation", "test"),
    ):
        key = f"{left}_{right}"
        response_overlaps["exact"][key] = sorted(
            state["response_exact_by_split"][left]
            & state["response_exact_by_split"][right]
        )
        response_overlaps["canonical"][key] = sorted(
            state["response_canonical_by_split"][left]
            & state["response_canonical_by_split"][right]
        )
    if any(
        values
        for overlap_kind in response_overlaps.values()
        for values in overlap_kind.values()
    ):
        raise CollectionError("response bodies overlap between train and diagnostic splits")
    negative_overlap = state["sft_targets"] & (
        state["dpo_rejected"] | state["reward_negative"]
    )
    if negative_overlap:
        raise CollectionError("a negative response is present as an SFT assistant target")
    required_pair_lanes = {"sft", "dpo", "reward_positive", "reward_negative"}
    pair_binding_failures: list[str] = []
    for (split, cluster), lanes in sorted(state["pair_bindings"].items()):
        if set(lanes) != required_pair_lanes or len(set(lanes.values())) != 1:
            pair_binding_failures.append(f"{split}:{cluster}")
    if pair_binding_failures:
        raise CollectionError("SFT, DPO, and reward rows are not identity-aligned by response pair")
    if state["sft_targets"] != state["dpo_chosen"]:
        raise CollectionError("positive SFT targets do not exactly match DPO chosen responses")
    if state["dpo_chosen"] != state["reward_positive"]:
        raise CollectionError("positive reward labels do not exactly match DPO chosen responses")
    if state["dpo_rejected"] != state["reward_negative"]:
        raise CollectionError("negative reward labels do not exactly match DPO rejected responses")

    counts = manifest.get("counts")
    if not isinstance(counts, Mapping):
        raise CollectionError("candidate manifest counts must be an object")
    expected = {
        "sft_rows": sum(v for k, v in lane_rows.items() if k.startswith("sft_positive_")),
        "dpo_rows": sum(v for k, v in lane_rows.items() if k.startswith("dpo_preference_")),
        "reward_rows": sum(v for k, v in lane_rows.items() if k.startswith("reward_labels_")),
        "response_inventory_rows": lane_rows.get("response_inventory", 0),
        "quarantine_rows": lane_rows.get("quarantine", 0),
    }
    for field, actual in expected.items():
        if counts.get(field) != actual:
            raise CollectionError(f"candidate manifest {field} count mismatch")
    split_candidates = counts.get("split_candidates")
    if not isinstance(split_candidates, Mapping):
        raise CollectionError("candidate split counts must be an object")
    for split in ("train", "validation", "test"):
        split_expected = split_candidates.get(split)
        if split_expected != lane_rows.get(f"sft_positive_{split}"):
            raise CollectionError(f"candidate split count mismatch for {split}")
        if lane_rows.get(f"dpo_preference_{split}") != split_expected:
            raise CollectionError(f"DPO split count mismatch for {split}")
        if lane_rows.get(f"reward_labels_{split}") != 2 * split_expected:
            raise CollectionError(f"reward-label split count mismatch for {split}")
    return {
        "negative_never_assistant_target": True,
        "positive_lane_alignment": True,
        "negative_lane_alignment": True,
        "pair_identity_alignment": True,
        "prompt_cluster_overlap": overlaps,
        "duplicate_prompt_clusters": duplicate_prompt_clusters,
        "response_body_overlap": response_overlaps,
        "within_split_response_duplicates": within_response_duplicates,
        "reward_label_counts": dict(sorted(state["reward_label_counts"].items())),
    }


def _validate_candidate(manifest: Mapping[str, Any]) -> None:
    if manifest.get("schema_version") != CANDIDATE_SCHEMA:
        raise CollectionError("unsupported candidate schema_version")
    if manifest.get("materialized") is not True:
        raise CollectionError("candidate must be materialized")
    if manifest.get("safe_to_train") is not True or manifest.get("blocking_failures") != []:
        raise CollectionError("candidate has unresolved blocking training failures")
    if manifest.get("publication_ready") is not False:
        raise CollectionError("source candidate must not self-approve publication")
    rights = manifest.get("rights")
    if not isinstance(rights, Mapping):
        raise CollectionError("candidate rights declaration is missing")
    if rights.get("allow_public_redistribution") is not False:
        raise CollectionError("source candidate must not self-authorize public redistribution")
    for field in ("row_license", "rights_holder", "prompt_corpus_license"):
        if not isinstance(rights.get(field), str) or not rights[field].strip():
            raise CollectionError(f"candidate rights declaration is missing {field}")
    if rights.get("row_license") != "CC-BY-4.0":
        raise CollectionError("this Kaggle collection supports only CC-BY-4.0 candidate rows")
    allowed_models = manifest.get("allowed_models")
    model_licenses = rights.get("model_output_licenses")
    if (
        not isinstance(allowed_models, Mapping)
        or not allowed_models
        or not isinstance(model_licenses, Mapping)
        or dict(allowed_models) != dict(model_licenses)
    ):
        raise CollectionError("candidate model-license declarations are incomplete or inconsistent")
    if any(
        not isinstance(model, str)
        or not model
        or not isinstance(license_name, str)
        or not license_name
        for model, license_name in allowed_models.items()
    ):
        raise CollectionError("candidate model-license declarations contain invalid values")
    gates = manifest.get("gates")
    if not isinstance(gates, list) or not gates:
        raise CollectionError("candidate has no executable gate record")
    failed = [
        gate.get("id")
        for gate in gates
        if isinstance(gate, Mapping) and gate.get("blocking") is True and gate.get("passed") is not True
    ]
    if failed:
        raise CollectionError(f"candidate blocking gate failed: {failed[0]}")
    grade_gates = [
        gate
        for gate in gates
        if isinstance(gate, Mapping) and gate.get("id") == GRADE_GATE_ID
    ]
    if len(grade_gates) != 1:
        raise CollectionError(f"candidate must declare exactly one {GRADE_GATE_ID} gate")
    grade_gate = grade_gates[0]
    if grade_gate.get("blocking") is not True or grade_gate.get("passed") is not True:
        raise CollectionError(f"candidate {GRADE_GATE_ID} gate is not blocking and passed")
    by_id = {
        gate.get("id"): gate for gate in gates if isinstance(gate, Mapping)
    }
    missing_required = sorted(REQUIRED_BLOCKING_GATES - set(by_id))
    if missing_required:
        raise CollectionError(
            f"candidate is missing required release gate: {missing_required[0]}"
        )
    invalid_required = sorted(
        gate_id
        for gate_id in REQUIRED_BLOCKING_GATES
        if by_id[gate_id].get("blocking") is not True
        or by_id[gate_id].get("passed") is not True
    )
    if invalid_required:
        raise CollectionError(
            f"candidate required release gate is not blocking and passed: {invalid_required[0]}"
        )
    reasoning_policy = manifest.get("reasoning_data_policy")
    if not isinstance(reasoning_policy, str) or "Hidden reasoning" not in reasoning_policy:
        raise CollectionError("candidate reasoning-data policy is missing")
    _scan_safe(manifest, label="candidate manifest")


def _verify_contamination(
    manifest: Mapping[str, Any], ledger: Mapping[str, Any], *, file_sha256: str
) -> dict[str, str]:
    if ledger.get("schema_version") != CONTAMINATION_SCHEMA:
        raise CollectionError("unsupported contamination ledger schema")
    content_sha = _canonical_sha256(ledger)
    if ledger.get("sha256") != content_sha:
        raise CollectionError("contamination ledger canonical content hash mismatch")
    declared = manifest.get("contamination_ledger")
    if not isinstance(declared, Mapping) or declared.get("sha256") != content_sha:
        raise CollectionError("candidate is not bound to the contamination ledger content")
    if ledger.get("source_benchmark_cannot_be_reused_as_model_improvement_evidence") is not True:
        raise CollectionError("contamination ledger does not prohibit benchmark evidence reuse")
    if ledger.get("independent_external_evidence_eligible") is not False:
        raise CollectionError("contaminated benchmark is incorrectly marked externally eligible")
    overlap = ledger.get("prompt_cluster_overlap")
    if not isinstance(overlap, Mapping) or any(overlap.values()):
        raise CollectionError("contamination ledger reports split overlap")
    _scan_safe(ledger, label="contamination ledger")
    return {"file_sha256": file_sha256, "content_sha256": content_sha}


def _verify_approval(
    approval_path: Path | None,
    *,
    source_manifest_sha256: str,
    contamination: Mapping[str, str],
    public_ready: bool,
) -> dict[str, Any] | None:
    if not public_ready:
        if approval_path is not None:
            raise CollectionError("--approval requires --public-ready")
        return None
    if approval_path is None:
        raise CollectionError("public-ready packaging requires exact independent approval")
    approval = _read_object(approval_path, label="publication approval")
    _scan_safe(approval, label="publication approval", hidden_reasoning=True)
    if set(approval) != _APPROVAL_FIELDS:
        raise CollectionError("publication approval must use the closed schema without notes")
    if approval.get("schema_version") != APPROVAL_SCHEMA or approval.get("handoff_kind") != APPROVAL_KIND:
        raise CollectionError("publication approval schema or handoff_kind is invalid")
    if approval.get("source_candidate_manifest_sha256") != source_manifest_sha256:
        raise CollectionError("publication approval is not bound to the candidate manifest")
    if approval.get("contamination_ledger_file_sha256") != contamination["file_sha256"]:
        raise CollectionError("publication approval is not bound to the ledger file")
    if approval.get("contamination_ledger_content_sha256") != contamination["content_sha256"]:
        raise CollectionError("publication approval is not bound to the ledger content")
    if approval.get("approved_by") in (None, "", "generator", "self"):
        raise CollectionError("publication approval must name an independent approver")
    if not isinstance(approval.get("approved_at"), str) or not _ISO_UTC.fullmatch(approval["approved_at"]):
        raise CollectionError("publication approval approved_at must be an explicit UTC timestamp")
    try:
        approved_at = datetime.fromisoformat(approval["approved_at"].replace("Z", "+00:00"))
    except ValueError as exc:
        raise CollectionError("publication approval approved_at is not a real date") from exc
    if approved_at.utcoffset() is None or approved_at.utcoffset().total_seconds() != 0:
        raise CollectionError("publication approval approved_at must be UTC")
    flags = approval.get("approvals")
    if not isinstance(flags, Mapping) or set(flags) != _APPROVAL_FLAGS:
        raise CollectionError("publication approval flags must use the closed schema")
    if any(flags.get(key) is not True for key in _APPROVAL_FLAGS):
        raise CollectionError("publication approval is missing required independent approvals")
    if approval.get("allow_training_use") is not True or approval.get("allow_public_redistribution") is not True:
        raise CollectionError("publication approval does not allow training and redistribution")
    for field in ("rights_holder", "row_license", "release_license"):
        if not isinstance(approval.get(field), str) or not approval[field].strip():
            raise CollectionError(f"publication approval {field} is missing")
    return approval


def _dataset_identity(dataset_id: str, title: str) -> None:
    if not _DATASET_ID.fullmatch(dataset_id):
        raise CollectionError("dataset id must be owner/slug using Kaggle-safe lowercase text")
    if not title.strip() or len(title) > 80:
        raise CollectionError("dataset title must contain 1-80 characters")
    _scan_safe(
        {"dataset_id": dataset_id, "title": title},
        label="dataset identity",
        hidden_reasoning=True,
    )


def _repo_provenance(explicit: str | None) -> dict[str, Any]:
    if explicit is not None:
        if not _HEX40.fullmatch(explicit):
            raise CollectionError("--repo-commit must be a lowercase 40-character git SHA")
        commit = explicit
    else:
        completed = subprocess.run(
            ["git", "rev-parse", "HEAD"],
            cwd=ROOT,
            check=False,
            capture_output=True,
            text=True,
        )
        commit = completed.stdout.strip().lower()
        if completed.returncode != 0 or not _HEX40.fullmatch(commit):
            raise CollectionError("cannot resolve repository commit; pass --repo-commit")
    exists = subprocess.run(
        ["git", "cat-file", "-e", f"{commit}^{{commit}}"],
        cwd=ROOT,
        check=False,
        capture_output=True,
        text=True,
    )
    if exists.returncode != 0:
        raise CollectionError("--repo-commit does not identify an existing commit")
    relative = Path(__file__).resolve().relative_to(ROOT).as_posix()
    at_commit = subprocess.run(
        ["git", "show", f"{commit}:{relative}"],
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
        hashlib.sha256(at_commit.stdout).hexdigest() if at_commit.returncode == 0 else None
    )
    worktree_clean = status.returncode == 0 and not status.stdout.strip()
    generator_matches = committed_sha == generator_sha
    return {
        "commit": commit,
        "commit_exists": True,
        "worktree_clean": worktree_clean,
        "generator_path": relative,
        "generator_sha256": generator_sha,
        "generator_tracked_at_commit": at_commit.returncode == 0,
        "generator_sha256_at_commit": committed_sha,
        "generator_matches_commit": generator_matches,
        "reproducible_from_commit_alone": worktree_clean and generator_matches,
        "state": (
            "clean_commit"
            if worktree_clean and generator_matches
            else "uncommitted_worktree_explicitly_recorded"
        ),
    }


def _prepare_staging(output: Path, *, force: bool) -> Path:
    output = Path(os.path.abspath(output))
    _reject_link_components(output, label="output path")
    if output.exists() and not force:
        raise CollectionError(f"output already exists; pass --force: {output}")
    if output == Path(output.anchor):
        raise CollectionError("unsafe output path")
    protected = {ROOT.resolve(), Path.home().resolve(), ROOT.resolve().parent}
    if output in protected:
        raise CollectionError("refusing to replace a workspace, home, or workspace parent")
    if output.exists():
        if not output.is_dir():
            raise CollectionError("existing output is not a directory")
        marker = output / "collection-manifest.json"
        existing = _read_object(marker, label="existing collection marker")
        if existing.get("schema_version") != COLLECTION_MANIFEST_SCHEMA:
            raise CollectionError("--force only replaces a prior response collection")
    output.parent.mkdir(parents=True, exist_ok=True)
    return Path(tempfile.mkdtemp(prefix=f".{output.name}-building-", dir=output.parent))


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


def _paths_overlap(left: Path, right: Path) -> bool:
    left = left.resolve()
    right = right.resolve()
    try:
        left.relative_to(right)
        return True
    except ValueError:
        pass
    try:
        right.relative_to(left)
        return True
    except ValueError:
        return False


def _rename_with_transient_lock_retry(source: Path, target: Path) -> None:
    """Rename a directory, tolerating short-lived Windows/OneDrive locks.

    The staging directory and destination share a parent, so a successful
    rename remains the atomic commit boundary.  We deliberately do not fall
    back to a recursive copy: exposing a partially copied collection would be
    worse than failing closed and leaving the previous output in place.
    """

    for delay in (*COMMIT_RENAME_RETRY_DELAYS_SECONDS, None):
        try:
            source.rename(target)
            return
        except PermissionError:
            if delay is None:
                raise
            time.sleep(delay)


def _copy_commit_staging(staging: Path, output: Path) -> None:
    """Commit by verified copy when OneDrive keeps a directory rename locked.

    The root collection manifest is copied last, so a concurrent reader never
    mistakes an incomplete copy for a committed collection.  Every copied
    file is then checked by size and SHA-256 against the already-verified
    staging tree.  This fallback is used only after the atomic rename retry
    budget is exhausted.
    """

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

        shutil.copy2(marker, output / marker_name)
        if _artifact_index(staging, exclude=set()) != _artifact_index(
            output, exclude=set()
        ):
            raise CollectionError("verified copy commit does not match staging bytes")
    except Exception:
        shutil.rmtree(output, ignore_errors=True)
        raise


def _commit_staging(staging: Path, output: Path) -> Path | None:
    """Commit a complete staging directory, rolling back an existing output."""

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
        if backup is not None and backup.exists() and not output.exists():
            _rename_with_transient_lock_retry(backup, output)
        raise
    if backup is not None:
        shutil.rmtree(backup, ignore_errors=True)
        return backup if backup.exists() else None
    return None


def _source_summary(manifest: Mapping[str, Any]) -> list[str]:
    source = manifest.get("source")
    if not isinstance(source, Mapping):
        return []
    lines: list[str] = []
    for name in ("promptset", "panel", "results"):
        value = source.get(name)
        if not isinstance(value, Mapping):
            continue
        sha = value.get("sha256") or value.get("snapshot_sha256")
        path = value.get("path", "not recorded")
        lines.append(f"- `{name}`: `{path}`; source SHA-256 `{sha}`")
    return lines


def _write_docs(
    dataset: Path,
    *,
    manifest: Mapping[str, Any],
    source_manifest_sha256: str,
    contamination: Mapping[str, str],
    dataset_id: str,
    title: str,
    release_id: str,
    lane_rows: Mapping[str, int],
    public_ready: bool,
) -> None:
    counts = manifest["counts"]
    state = "approved public-ready candidate" if public_ready else "private review candidate"
    visibility = "public" if public_ready else "private"
    publication_note = (
        "The exact manifest-bound package is approved for public redistribution."
        if public_ready
        else "The package remains private until an exact manifest-bound approval is supplied."
    )
    source_lines = "\n".join(_source_summary(manifest)) or "- Source paths and hashes are recorded in `candidate-manifest.json`."
    dataset_url = f"https://www.kaggle.com/datasets/{dataset_id}"
    integrity_url = f"https://www.kaggle.com/code/{INTEGRITY_NOTEBOOK_ID}"
    plan_url = f"https://www.kaggle.com/code/{TRAINING_PLAN_NOTEBOOK_ID}"
    visual_url = f"https://www.kaggle.com/code/{VISUAL_EXPLORER_NOTEBOOK_ID}"
    _write_text(
        dataset / "README.md",
        f"""# Start here: {title}

This {visibility} dataset is a **Kaggle / Gemma 4 Good Hackathon learning artifact**.
It demonstrates how measured baseline-versus-harness responses can be converted
into separately governed supervised fine-tuning, preference, reward-label,
inventory, and quarantine lanes without treating model grades as ground truth.

## Reviewer route

1. Open the [visual explorer]({visual_url}) for charts, lane tables, score and
   grading-dimension summaries, text-length distributions, and quarantine
   diagnostics.
2. Open the [integrity audit]({integrity_url}) for release, shard, row-hash,
   split, and negative-target checks.
3. Open the [central processing unit (CPU) training plan]({plan_url}) for positive-only, reward,
   preference, and mixed-regime experiment plans. Training remains disabled.
4. Read `LOADING.md` for standard Kaggle, pandas, Hugging Face Datasets, and
   Polars loading examples.
5. Read `DATA_CARD.md`, `SCHEMA.md`, `SOURCES.md`, and `LIMITATIONS.md` before
   using any row.

## Release snapshot

- Release: `{release_id}`
- Positive supervised fine-tuning rows: {counts['sft_rows']:,}
- Same-prompt preference pairs: {counts['dpo_rows']:,}
- Reward-label rows: {counts['reward_rows']:,}
- Raw-text-free response inventory: {counts['response_inventory_rows']:,}
- Raw-text-free quarantine records: {counts['quarantine_rows']:,}
- `safe_to_train=true` for the declared training lanes after the recorded gates
- `safe_to_publish={str(public_ready).lower()}`. {publication_note}

`dataset-overview.csv` is the fastest machine-readable map of lanes and usage
boundaries. The full package identity is bound by `release-manifest.json`.

## Claim boundary

No graphics processing unit (GPU) training ran, no adapter was produced, and no independent model lift was
demonstrated. Because source benchmark grades selected these rows, that same
benchmark cannot serve as independent post-training evidence.

## Plain-language terms

- **Supervised fine-tuning** trains on an input and a reviewed desired answer.
- **Preference optimization** trains from a prompt, a preferred answer, and a
  nonpreferred answer. Direct Preference Optimization is one such method.
- **Reward labels** mark responses as preferred or nonpreferred for quality
  classification or reward-model research.
- **JSON Lines** stores one complete JavaScript Object Notation object per line.
- **Adapter** means the smaller trained weights produced by a
  parameter-efficient fine-tuning method; it still depends on the base model.

Dataset page: {dataset_url}
""",
    )
    _write_text(
        dataset / "DATA_CARD.md",
        f"""# {title}

Release ID: `{release_id}`<br>
Kaggle dataset ID: `{dataset_id}`<br>
State: **{state}**

This is a Kaggle / Gemma 4 Good Hackathon learning and research artifact. It is
packaged for transparent review, reproducible experiments, and professional
portfolio demonstration—not as a production model or legal-advice system.

## Start here

- [Visual dataset explorer]({visual_url}) — charts, distributions, and samples.
- [Manifest and row integrity audit]({integrity_url}) — exact verification.
- [Central processing unit training-plan notebook]({plan_url}) — experiment
  design with training off.
- `README.md` — reviewer route and release snapshot.
- `LOADING.md` — standard loading examples and training-library mappings.
- `dataset-overview.csv` — safe, text-free lane catalog Kaggle can preview.

## What this is

This is a manifest-bound training-data candidate derived from measured, same-prompt
response comparisons in the DueCare harness. It contains {counts['sft_rows']:,}
positive supervised fine-tuning rows, {counts['dpo_rows']:,} same-prompt preference pairs,
{counts['reward_rows']:,} reward-label rows, {counts['response_inventory_rows']:,}
raw-text-free inventory records, and {counts['quarantine_rows']:,} raw-text-free
quarantine records.

The supervised fine-tuning lane contains only responses that passed the
candidate's score, lift, grounding, citation, format, privacy, rights, and
safety gates. The preference lane keeps the measured chosen/rejected
relationship for the same prompt. It can be used for Direct Preference
Optimization. The reward lane labels both responses, but label-0 text is
explicitly forbidden as a supervised fine-tuning target.

## Intended uses

- Supervised fine-tuning using only `sft-positive-*` shards.
- Preference optimization using `dpo-preference-*` same-prompt pairs.
- Reward-model or response-quality classification using `reward-labels-*`.
- Auditing coverage and exclusions using the raw-text-free inventory/quarantine.

## Prohibited interpretation

This release does not contain hidden chain-of-thought or provider-private reasoning.
Visible final answers and visible grade deltas are not chain-of-thought. Negative
responses are contrastive/reward data only and must never be used as positive supervised fine-tuning
assistant targets.

No training was run by this packaging script. No adapter, model lift, competition
result, legal correctness guarantee, or full flywheel closure is claimed.

## Contamination boundary

The source benchmark and its grades helped select these rows. Therefore that
benchmark cannot be reused as independent evidence that a model trained on this
dataset improved. The included validation/test splits are diagnostics, not an
external holdout. Promotion requires a separately authored, lineage-independent
evaluation set.

## Review state

`safe_to_train` is `true` for the declared train lanes because the manifest-bound
privacy, rights, quality, split, and target-integrity gates passed. This does not
authorize public redistribution. `publication_ready` and `safe_to_publish` are
both `{str(public_ready).lower()}`. {publication_note} Generation cannot approve
its own publication. See `LIMITATIONS.md`, `SOURCES.md`, and the exact hashes in
`release-manifest.json`.

## Plain-language glossary

- **Supervised fine-tuning:** training on input and reviewed desired-answer
  examples. File names retain the conventional `sft` shorthand.
- **Direct Preference Optimization:** training from a prompt, preferred answer,
  and nonpreferred answer. File names retain the conventional `dpo` shorthand.
- **Reward label:** a bounded quality label attached to a prompt-response pair.
- **JSON Lines:** one complete JavaScript Object Notation object per line.
- **Secure Hash Algorithm 256-bit checksum:** a content fingerprint used to
  detect a changed row or file. Manifests use the conventional `sha256` field.
- **Adapter:** smaller task-specific weights trained alongside a frozen or
  mostly frozen base model.
""",
    )
    _write_text(
        dataset / "SCHEMA.md",
        """# Schema

All data files use eight-bit Unicode Transformation Format (UTF-8) and JSON
Lines, which stores one complete JavaScript Object Notation object per line.
Every row carries a canonical Secure Hash Algorithm 256-bit checksum in the
`sha256` field.

## `sft-positive-{split}-*.jsonl`

The `sft` file-name shorthand means **supervised fine-tuning**: training on an
input and a reviewed desired answer.

- `messages`: user and positive assistant messages.
- `split`, `prompt_cluster_id`: group-isolated split identity.
- `quality_evidence`, `quality_gate`: visible score/component evidence and gates.
- `training_response_sha256.chosen`: hash of the assistant target.
- `allow_training_use=true` only for train shards; validation/test rows are
  diagnostic and carry `allow_training_use=false`. Public redistribution still
  requires release approval.

Only this lane may provide supervised fine-tuning assistant targets.

## `dpo-preference-{split}-*.jsonl`

The `dpo` file-name shorthand means **Direct Preference Optimization**: training
from a prompt, a preferred answer, and a nonpreferred answer.

- `prompt`: the common prompt.
- `chosen`, `rejected`: measured same-prompt preference responses.
- `preference_rationale`: visible grade-delta rationale, not hidden reasoning.
- `training_response_sha256`: hashes binding both responses.

## `reward-labels-{split}-*.jsonl`

- `prompt`, `response`, `label`: binary reward/classification example.
- `label=1`: preferred response.
- `label=0`: nonpreferred response; `assistant_target_allowed=false` and lane text
  states that it is never a supervised fine-tuning target.

## `response-inventory-*.jsonl`

Raw-text-free inventory: prompt/response hashes, lengths, model/arm, grading,
rights, and quarantine status. It inventories the source snapshot without turning
ungraded responses into labeled training examples.

## `quarantine-*.jsonl`

Raw-text-free exclusions with reason codes and model/prompt hashes. These records
are audit metadata, not training examples.

## Reviewer catalogs

- `dataset-overview.csv`: one text-free row per lane with counts, split,
  shard count, text-presence boundary, and allowed training role.
- `preview-catalog.jsonl`: the same aggregate catalog in JSON Lines form.
""",
    )
    _write_text(
        dataset / "LOADING.md",
        f"""# Loading this dataset

The authoritative payload is checksummed JSON Lines. Start with
`release-manifest.json` and `shard-index.json`; do not treat
`dataset-metadata.json` as a mounted payload file because Kaggle consumes it as
upload-control metadata.

## Terms

- **Supervised fine-tuning** trains on input and desired-answer examples.
- **Direct Preference Optimization** trains from prompt, preferred-answer, and
  nonpreferred-answer triples.
- **JSON Lines** stores one JavaScript Object Notation object per line.
- **Streaming** reads rows incrementally instead of loading the full corpus into
  memory.

## Python standard library: zero-dependency streaming

```python
import json
from pathlib import Path

root = Path("/kaggle/input/{dataset_id.split('/', 1)[1]}")
shard = next(root.glob("sft-positive-train-*.jsonl"))
with shard.open(encoding="utf-8") as handle:
    first_row = json.loads(next(handle))
print(first_row["messages"])
```

## pandas

```python
import pandas as pd

frame = pd.read_json(shard, lines=True)
print(frame[["split", "prompt_cluster_id"]].head())
```

## Hugging Face Datasets

```python
from datasets import load_dataset

files = sorted(str(path) for path in root.glob("sft-positive-train-*.jsonl"))
supervised_train = load_dataset(
    "json", data_files={{"train": files}}, split="train", streaming=True
)
print(next(iter(supervised_train))["messages"])
```

For preference experiments, replace the pattern with
`dpo-preference-train-*.jsonl`. For reward classification, use
`reward-labels-train-*.jsonl`.

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

lazy_rows = pl.scan_ndjson(str(root / "sft-positive-train-*.jsonl"))
print(lazy_rows.select("split").group_by("split").len().collect())
```

## Training-role boundary

- `sft-positive-train-*`: positive assistant targets for supervised
  fine-tuning.
- `dpo-preference-train-*`: same-prompt preference optimization.
- `reward-labels-train-*`: reward or response-quality classification.
- `response-inventory-*` and `quarantine-*`: audit only; never assistant
  targets.
- validation and test rows: diagnostics only for this contaminated source
  lineage; they are not independent improvement evidence.
""",
    )
    _write_text(
        dataset / "SOURCES.md",
        f"""# Sources and provenance

The authoritative source is the included `candidate-manifest.json`, whose exact
Secure Hash Algorithm 256-bit checksum is `{source_manifest_sha256}`.

The included contamination ledger is bound twice:

- file Secure Hash Algorithm 256-bit checksum: `{contamination['file_sha256']}`
- canonical content Secure Hash Algorithm 256-bit checksum: `{contamination['content_sha256']}`

Those hashes intentionally differ because the canonical hash excludes the
ledger's self-hash field, while the file hash covers the complete serialized file.

Source snapshot records:

{source_lines}

The model tags and declared model-artifact licenses are preserved from the source
manifest. An artifact license is not itself an output-redistribution grant. Local
model tags are not immutable weight digests, so rights review must remain
release-specific and manifest-bound.
""",
    )
    _write_text(
        dataset / "LIMITATIONS.md",
        """# Limitations and required controls

- The source benchmark influenced selection, so it is contaminated for independent
  post-training evaluation.
- Diagnostic validation/test splits are prompt-cluster isolated, but they are not
  lineage-independent external evidence.
- Automated grades can be wrong; scores are selection evidence, not ground truth.
- Legal and support-resource content can become stale and is not legal advice.
- The dataset focuses on migrant-worker exploitation risks and is not globally or
  demographically representative.
- Model tags are recorded local tags, not immutable weight revisions.
- Inventory and quarantine rows contain hashes/metadata only; they cannot recover
  or license omitted raw text.
- Negative responses can contain unsafe or low-quality advice. Use them only in
  contrastive/reward objectives with explicit masks and safeguards.
- A separate curator, privacy, license, quality, and public-redistribution approval
  is required before making the candidate public.
- The visual and training-plan notebooks are educational experiment surfaces;
  their completion does not mean a model was trained or improved.
""",
    )
    _write_text(
        dataset / "LICENSE",
        f"""Dataset rows are offered under Creative Commons Attribution 4.0
(CC BY 4.0) under the exact manifest-bound approval recorded by this release.

{publication_note}

Model-artifact and prompt-corpus rights declarations are preserved in
candidate-manifest.json; neither substitutes for output-redistribution approval.
Source references retain their own terms. The package does not redistribute raw
responses from providers whose output rights remain pending.
""",
    )
    _write_text(
        dataset / "CITATION.cff",
        f"""cff-version: 1.2.0
message: "If you use this reviewed release, cite the exact release ID and manifest."
title: "{title}"
type: dataset
authors:
  - name: "DueCare project contributors"
version: "{release_id}"
license: CC-BY-4.0
repository-code: "https://github.com/taylorsamarel/gemma4_comp"
""",
    )
    _write_text(
        dataset / "CHANGELOG.md",
        f"""# Changelog

## {release_id}

- Packaged all manifest-declared positive supervised fine-tuning, same-prompt
  Direct Preference Optimization, reward-label,
  raw-text-free inventory, and raw-text-free quarantine shards.
- Bound the exact candidate manifest and contamination ledger hashes.
- Added central-processing-unit-only integrity, training-plan, and
  visual-explorer notebooks.
- Added a reviewer-first README, specific Kaggle metadata, and safe CSV lane
  previews for a professional hackathon learning experience.
- State is `{state}`; no upload or training was performed by this builder.
""",
    )


def _write_croissant_metadata(
    dataset: Path,
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
        path = dataset / relative
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
        dataset / "croissant.json",
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
                "Manifest-bound measured-response corpus with separate reviewed "
                "supervised fine-tuning, preference, reward-label, and audit lanes."
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
                "reward labels",
            ],
            "citeAs": f"{title}, release {release_id}",
            "distribution": distributions,
        },
    )


def _notebook(cells: list[dict[str, Any]]) -> dict[str, Any]:
    return {
        "cells": cells,
        "metadata": {
            "kernelspec": {"display_name": "Python 3", "language": "python", "name": "python3"},
            "language_info": {"name": "python", "version": "3"},
        },
        "nbformat": 4,
        "nbformat_minor": 5,
    }


def _markdown(identifier: str, source: str) -> dict[str, Any]:
    return {"cell_type": "markdown", "id": identifier, "metadata": {}, "source": source.splitlines(keepends=True)}


def _code(identifier: str, source: str) -> dict[str, Any]:
    return {"cell_type": "code", "execution_count": None, "id": identifier, "metadata": {}, "outputs": [], "source": source.splitlines(keepends=True)}


def _integrity_notebook(
    *, dataset_id: str, source_manifest_sha256: str, contamination_file_sha256: str
) -> dict[str, Any]:
    code = f'''from pathlib import Path
import hashlib, json, os

EXPECTED_DATASET_ID = {dataset_id!r}
EXPECTED_SOURCE_MANIFEST_SHA256 = {source_manifest_sha256!r}
EXPECTED_CONTAMINATION_FILE_SHA256 = {contamination_file_sha256!r}

def sha256_file(path):
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()

def release_payload_sha256(release):
    payload = dict(release); payload.pop("release_manifest_payload_sha256", None)
    raw = json.dumps(payload, ensure_ascii=False, sort_keys=True, separators=(",", ":")).encode()
    return hashlib.sha256(raw).hexdigest()

def canonical_sha256(row):
    payload = dict(row); payload.pop("sha256", None)
    raw = json.dumps(payload, ensure_ascii=False, sort_keys=True, separators=(",", ":")).encode()
    return hashlib.sha256(raw).hexdigest()

def find_root():
    override = os.environ.get("DUECARE_DATASET_ROOT")
    candidates = []
    if override:
        root = Path(override)
        candidates.append(root / "release-manifest.json" if root.is_dir() else root)
    if Path("/kaggle/input").exists():
        candidates += list(Path("/kaggle/input").rglob("release-manifest.json"))
    candidates += list(Path.cwd().rglob("release-manifest.json"))
    matches = []
    for path in candidates:
        try:
            release = json.loads(path.read_text(encoding="utf-8"))
        except Exception:
            continue
        if release.get("dataset_id") == EXPECTED_DATASET_ID:
            matches.append(path.parent)
    if len(matches) != 1:
        raise RuntimeError(f"Expected one dataset root, found {{len(matches)}}")
    return matches[0]

def working_dir():
    kaggle_working = Path("/kaggle/working")
    in_kaggle = bool(os.environ.get("KAGGLE_KERNEL_RUN_TYPE")) or Path("/kaggle/input").exists()
    root = kaggle_working if in_kaggle else Path.cwd() / "duecare_training_outputs"
    root.mkdir(parents=True, exist_ok=True)
    return root

root = find_root()
release = json.loads((root / "release-manifest.json").read_text(encoding="utf-8"))
index = json.loads((root / "shard-index.json").read_text(encoding="utf-8"))
candidate = json.loads((root / "candidate-manifest.json").read_text(encoding="utf-8"))
failures, observed = [], {{}}
if release_payload_sha256(release) != release.get("release_manifest_payload_sha256"):
    failures.append("release manifest payload hash mismatch")
if sha256_file(root / "candidate-manifest.json") != EXPECTED_SOURCE_MANIFEST_SHA256:
    failures.append("candidate manifest hash mismatch")
if release.get("source_candidate_manifest_sha256") != EXPECTED_SOURCE_MANIFEST_SHA256:
    failures.append("release candidate-manifest binding mismatch")
if sha256_file(root / "contamination-ledger.json") != EXPECTED_CONTAMINATION_FILE_SHA256:
    failures.append("contamination ledger file hash mismatch")
ledger = json.loads((root / "contamination-ledger.json").read_text(encoding="utf-8"))
if canonical_sha256(ledger) != release.get("contamination_ledger", {{}}).get("content_sha256"):
    failures.append("contamination ledger content hash mismatch")
required_gates = {{
    "accepted_candidates_present", "train_split_present", "diagnostic_splits_present",
    "source_artifacts_parse_clean", "exact_prompt_dedup", "prompt_cluster_split_isolation",
    "target_text_exact_canonical_dedup",
    "row_integrity", "negative_never_assistant_target", "emitted_models_rights_allowlisted",
    "complete_bounded_grade_evidence", "graded_text_emitted_verbatim_without_redaction",
    "volatile_resources_require_versioned_binding", "within_split_target_text_no_overlap",
    "cross_split_target_text_no_overlap", "response_body_split_isolation",
}}
source_gates = {{gate.get("id"): gate for gate in candidate.get("gates", [])}}
for gate_id in sorted(required_gates):
    gate = source_gates.get(gate_id, {{}})
    if gate.get("blocking") is not True or gate.get("passed") is not True:
        failures.append(f"required source gate is not blocking/passed: {{gate_id}}")
for relative, expected in release["artifacts"].items():
    path = root / relative
    if not path.is_file() or sha256_file(path) != expected["sha256"] or path.stat().st_size != expected["bytes"]:
        failures.append(f"artifact mismatch: {{relative}}")
actual_files = {{path.relative_to(root).as_posix() for path in root.rglob("*") if path.is_file()}}
expected_files = set(release["artifacts"]) | {{"release-manifest.json"}}
if "dataset-metadata.json" in actual_files:
    expected_files.add("dataset-metadata.json")
for relative in sorted(actual_files - expected_files):
    failures.append(f"undeclared dataset artifact: {{relative}}")
for relative in sorted(expected_files - actual_files):
    failures.append(f"missing dataset artifact: {{relative}}")
candidate_files = candidate.get("files", {{}})
for relative, expected in candidate_files.items():
    path = root / relative
    if not path.is_file() or sha256_file(path) != expected.get("sha256") or path.stat().st_size != expected.get("bytes"):
        failures.append(f"candidate-declared artifact mismatch: {{relative}}")

sft_targets, dpo_chosen, dpo_rejected = set(), set(), set()
reward_positive, reward_negative = set(), set()
complete_grade_rows = 0
for lane, lane_info in index["lanes"].items():
    count = 0
    for shard in lane_info["shards"]:
        with (root / shard["path"]).open(encoding="utf-8") as handle:
            for line_number, line in enumerate(handle, 1):
                row = json.loads(line); count += 1
                if canonical_sha256(row) != row.get("sha256"):
                    failures.append(f"row hash mismatch: {{shard['path']}}:{{line_number}}")
                if lane.startswith(("sft_positive_", "dpo_preference_", "reward_labels_")):
                    quality = row.get("quality_evidence", {{}})
                    component_keys = set("ABCDE")
                    if quality.get("complete_bounded_components") is not True or set(quality.get("baseline_components", {{}})) != component_keys or set(quality.get("target_components", {{}})) != component_keys:
                        failures.append(f"incomplete grade evidence: {{shard['path']}}:{{line_number}}")
                    else:
                        complete_grade_rows += 1
                if lane.startswith("sft_positive_"):
                    text = [m["content"] for m in row["messages"] if m.get("role") == "assistant"][-1]
                    sft_targets.add(hashlib.sha256(text.encode()).hexdigest())
                elif lane.startswith("dpo_preference_"):
                    dpo_chosen.add(hashlib.sha256(row["chosen"].encode()).hexdigest())
                    dpo_rejected.add(hashlib.sha256(row["rejected"].encode()).hexdigest())
                elif lane.startswith("reward_labels_"):
                    target = reward_positive if row["label"] == 1 else reward_negative
                    target.add(hashlib.sha256(row["response"].encode()).hexdigest())
                    if row["label"] == 0 and row.get("assistant_target_allowed") is not False:
                        failures.append("negative reward row permits assistant targeting")
                elif row.get("contains_raw_text") is not False:
                    failures.append(f"raw text in metadata lane: {{lane}}")
    observed[lane] = count
    if count != lane_info["rows"]:
        failures.append(f"lane count mismatch: {{lane}}")

if sft_targets != dpo_chosen or dpo_chosen != reward_positive:
    failures.append("positive lane alignment mismatch")
if dpo_rejected != reward_negative:
    failures.append("negative lane alignment mismatch")
if sft_targets & reward_negative:
    failures.append("negative response appears as an SFT target")
audit = {{
    "schema_version": "duecare.kaggle.response-integrity-audit.v1",
    "dataset_id": EXPECTED_DATASET_ID,
    "ok": not failures,
    "failures": failures,
    "observed_rows": observed,
    "complete_bounded_grade_rows": complete_grade_rows,
    "negative_never_assistant_target": not bool(sft_targets & reward_negative),
    "training_completed": False,
}}
(working_dir() / "integrity-audit.json").write_text(json.dumps(audit, indent=2, sort_keys=True) + "\\n", encoding="utf-8")
print(json.dumps(audit, indent=2))
assert not failures, failures
'''
    return _notebook(
        [
            _markdown(
                "purpose",
                "# DueCare measured-response integrity and exploration\n\n"
                "This central processing unit (CPU) notebook verifies every package and row hash, "
                "lane count, and the rule that negative responses never become supervised "
                "fine-tuning assistant targets. Supervised fine-tuning trains on input and reviewed "
                "desired-answer examples. It does not train a model.\n",
            ),
            _code("integrity-audit", code),
        ]
    )


def _training_plan_notebook(*, dataset_id: str, source_manifest_sha256: str) -> dict[str, Any]:
    code = f'''from pathlib import Path
import hashlib, json, os, statistics

EXPECTED_DATASET_ID = {dataset_id!r}
EXPECTED_SOURCE_MANIFEST_SHA256 = {source_manifest_sha256!r}
TRAINING_ENABLED = False

def sha256_file(path):
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()

def release_payload_sha256(release):
    payload = dict(release); payload.pop("release_manifest_payload_sha256", None)
    raw = json.dumps(payload, ensure_ascii=False, sort_keys=True, separators=(",", ":")).encode()
    return hashlib.sha256(raw).hexdigest()

def find_root():
    override = os.environ.get("DUECARE_DATASET_ROOT")
    candidates = []
    if override:
        root = Path(override)
        candidates.append(root / "release-manifest.json" if root.is_dir() else root)
    if Path("/kaggle/input").exists():
        candidates += list(Path("/kaggle/input").rglob("release-manifest.json"))
    candidates += list(Path.cwd().rglob("release-manifest.json"))
    matches = []
    for path in candidates:
        try: release = json.loads(path.read_text(encoding="utf-8"))
        except Exception: continue
        if release.get("dataset_id") == EXPECTED_DATASET_ID: matches.append(path.parent)
    if len(matches) != 1: raise RuntimeError(f"Expected one dataset root, found {{len(matches)}}")
    return matches[0]

def working_dir():
    kaggle_working = Path("/kaggle/working")
    in_kaggle = bool(os.environ.get("KAGGLE_KERNEL_RUN_TYPE")) or Path("/kaggle/input").exists()
    root = kaggle_working if in_kaggle else Path.cwd() / "duecare_training_outputs"
    root.mkdir(parents=True, exist_ok=True)
    return root

root = find_root()
release = json.loads((root / "release-manifest.json").read_text(encoding="utf-8"))
index = json.loads((root / "shard-index.json").read_text(encoding="utf-8"))
if sha256_file(root / "candidate-manifest.json") != EXPECTED_SOURCE_MANIFEST_SHA256:
    raise RuntimeError("candidate manifest hash mismatch")
if release.get("source_candidate_manifest_sha256") != EXPECTED_SOURCE_MANIFEST_SHA256:
    raise RuntimeError("release is not bound to the expected candidate manifest")
if release_payload_sha256(release) != release.get("release_manifest_payload_sha256"):
    raise RuntimeError("release manifest payload hash mismatch")
samples = {{}}
for lane, info in index["lanes"].items():
    lengths = []
    for shard in info["shards"]:
        with (root / shard["path"]).open(encoding="utf-8") as handle:
            for line in handle:
                row = json.loads(line)
                if lane.startswith("sft_positive_"):
                    lengths.append(sum(len(m.get("content", "")) for m in row["messages"]))
                elif lane.startswith("dpo_preference_"):
                    lengths.append(len(row["prompt"]) + len(row["chosen"]) + len(row["rejected"]))
                elif lane.startswith("reward_labels_"):
                    lengths.append(len(row["prompt"]) + len(row["response"]))
                if len(lengths) >= 200: break
        if len(lengths) >= 200: break
    samples[lane] = {{"rows": info["rows"], "sample_rows": len(lengths), "sample_mean_chars": round(statistics.mean(lengths), 1) if lengths else None}}

plan = {{
    "schema_version": "duecare.kaggle.response-training-plan.v1",
    "dataset_id": EXPECTED_DATASET_ID,
    "source_candidate_manifest_sha256": EXPECTED_SOURCE_MANIFEST_SHA256,
    "cpu_preflight_completed": True,
    "training_enabled": TRAINING_ENABLED,
    "training_completed": False,
    "adapter_produced": False,
    "model_lift_demonstrated": False,
    "arms": [
        {{"name": "positive_sft", "input": "sft_positive_train", "assistant_targets": "positive only"}},
        {{"name": "same_prompt_dpo", "input": "dpo_preference_train", "assistant_targets": "chosen/rejected preference objective"}},
        {{"name": "reward_classifier", "input": "reward_labels_train", "assistant_targets": "none; label-0 is never SFT"}},
    ],
    "evaluation": "Use a separately authored lineage-independent holdout; source benchmark is contaminated.",
    "sample_statistics": samples,
}}
(working_dir() / "training-plan.json").write_text(json.dumps(plan, indent=2, sort_keys=True) + "\\n", encoding="utf-8")
print(json.dumps(plan, indent=2))
assert TRAINING_ENABLED is False
'''
    return _notebook(
        [
            _markdown(
                "purpose",
                "# DueCare central-processing-unit training plan\n\n"
                "This notebook inspects row sizes and writes an explicit three-arm training plan. "
                "The arms cover supervised fine-tuning, Direct Preference Optimization, and reward "
                "classification. It does not load a model, request a graphics processing unit, "
                "train, or claim an adapter. Negative responses remain contrastive or reward data only.\n",
            ),
            _code("training-plan", code),
        ]
    )


def _write_notebook_dir(
    path: Path,
    *,
    kernel_id: str,
    title: str,
    dataset_id: str,
    notebook: Mapping[str, Any],
    private: bool,
) -> None:
    path.mkdir(parents=True, exist_ok=True)
    _write_json(path / "notebook.ipynb", notebook)
    _write_json(
        path / "kernel-metadata.json",
        {
            "id": kernel_id,
            "title": title,
            "code_file": "notebook.ipynb",
            "language": "python",
            "kernel_type": "notebook",
            "is_private": private,
            "enable_gpu": False,
            "enable_internet": False,
            "dataset_sources": [dataset_id],
            "competition_sources": [],
            "kernel_sources": [],
            "model_sources": [],
        },
    )


def _artifact_index(dataset: Path, *, exclude: set[str]) -> dict[str, dict[str, Any]]:
    result: dict[str, dict[str, Any]] = {}
    for path in sorted(dataset.rglob("*")):
        if not path.is_file():
            continue
        relative = path.relative_to(dataset).as_posix()
        if relative in exclude:
            continue
        result[relative] = {
            "bytes": path.stat().st_size,
            "sha256": _sha256_file(path),
        }
    return result


def verify_dataset_package(dataset: Path) -> dict[str, Any]:
    failures: list[str] = []
    try:
        release = _read_object(dataset / "release-manifest.json", label="release manifest")
    except CollectionError as exc:
        return {"ok": False, "failures": [str(exc)], "verified_artifacts": 0}
    if release.get("schema_version") != RELEASE_SCHEMA:
        failures.append("release schema mismatch")
    expected_release_fields = {
        "schema_version",
        "collection_schema",
        "release_id",
        "created_at",
        "dataset_id",
        "title",
        "repo_provenance",
        "source_candidate_schema",
        "source_candidate_manifest_sha256",
        "contamination_ledger",
        "publication_state",
        "safe_to_train",
        "publication_ready",
        "safe_to_publish",
        "public",
        "publication_approval",
        "counts",
        "validation",
        "rights",
        "reasoning_data_policy",
        "claims",
        "no_upload_or_publication_performed",
        "artifacts",
        "release_manifest_payload_sha256",
    }
    if set(release) != expected_release_fields:
        failures.append("release manifest does not use the closed schema")
    if release.get("safe_to_train") is not True:
        failures.append("release is not explicitly safe_to_train")
    try:
        _scan_safe(release, label="release manifest")
    except CollectionError as exc:
        failures.append(str(exc))
    claimed_payload = release.get("release_manifest_payload_sha256")
    if not isinstance(claimed_payload, str) or _release_payload_sha256(release) != claimed_payload:
        failures.append("release manifest payload hash mismatch")
    artifacts = release.get("artifacts")
    verified = 0
    if not isinstance(artifacts, Mapping):
        failures.append("release artifacts missing")
        artifacts = {}
    required_artifacts = {
        "README.md",
        "DATA_CARD.md",
        "SCHEMA.md",
        "LOADING.md",
        "SOURCES.md",
        "LIMITATIONS.md",
        "CITATION.cff",
        "LICENSE",
        "candidate-manifest.json",
        "contamination-ledger.json",
        "shard-index.json",
        "dataset-overview.csv",
        "preview-catalog.jsonl",
        "croissant.json",
    }
    missing_required = sorted(required_artifacts - set(artifacts))
    if missing_required:
        failures.append(f"required dataset artifact missing: {missing_required[0]}")
    actual_files = {
        path.relative_to(dataset).as_posix()
        for path in dataset.rglob("*")
        if path.is_file() or path.is_symlink()
    }
    expected_files = set(artifacts) | {
        "release-manifest.json",
        "dataset-metadata.json",
    }
    for relative in sorted(actual_files - expected_files):
        failures.append(f"undeclared dataset artifact: {relative}")
    for relative in sorted(expected_files - actual_files):
        failures.append(f"missing dataset artifact: {relative}")
    for relative, expected in artifacts.items():
        try:
            path = _resolve_source(dataset, relative, label=f"release artifact {relative}")
        except CollectionError as exc:
            failures.append(str(exc))
            continue
        if not isinstance(expected, Mapping):
            failures.append(f"invalid artifact declaration: {relative}")
            continue
        if path.stat().st_size != expected.get("bytes") or _sha256_file(path) != expected.get("sha256"):
            failures.append(f"artifact mismatch: {relative}")
            continue
        verified += 1
    try:
        croissant = _read_object(dataset / "croissant.json", label="Croissant metadata")
    except CollectionError as exc:
        failures.append(str(exc))
    else:
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
            failures.append("Croissant metadata is missing required dataset fields")
        if croissant.get("dct:conformsTo") != "http://mlcommons.org/croissant/1.0":
            failures.append("Croissant conformance version mismatch")
        distributions = croissant.get("distribution")
        if not isinstance(distributions, list) or not distributions:
            failures.append("Croissant metadata has no file distributions")
        else:
            for item in distributions:
                if not isinstance(item, Mapping):
                    failures.append("Croissant distribution is not an object")
                    break
                relative = item.get("@id")
                declaration = artifacts.get(relative) if isinstance(relative, str) else None
                if not isinstance(declaration, Mapping):
                    failures.append("Croissant distribution is not release-manifest bound")
                    break
                if item.get("sha256") != declaration.get("sha256"):
                    failures.append(f"Croissant checksum mismatch: {relative}")
                    break
                if item.get("contentSize") != f"{declaration.get('bytes')} B":
                    failures.append(f"Croissant byte-count mismatch: {relative}")
                    break
    candidate_path = dataset / "candidate-manifest.json"
    ledger_path = dataset / "contamination-ledger.json"
    if candidate_path.is_file() and _sha256_file(candidate_path) != release.get("source_candidate_manifest_sha256"):
        failures.append("source candidate manifest binding mismatch")
    contamination = release.get("contamination_ledger")
    if isinstance(contamination, Mapping) and ledger_path.is_file():
        if _sha256_file(ledger_path) != contamination.get("file_sha256"):
            failures.append("contamination ledger file binding mismatch")
        try:
            ledger = _read_object(ledger_path, label="packaged contamination ledger")
        except CollectionError as exc:
            failures.append(str(exc))
        else:
            if _canonical_sha256(ledger) != contamination.get("content_sha256"):
                failures.append("contamination ledger content binding mismatch")
    else:
        failures.append("contamination ledger binding missing")
    try:
        metadata = _read_object(dataset / "dataset-metadata.json", label="dataset metadata")
    except CollectionError as exc:
        failures.append(str(exc))
    else:
        if set(metadata) != {
            "title",
            "subtitle",
            "description",
            "id",
            "licenses",
            "isPrivate",
            "keywords",
            "collaborators",
            "resources",
        }:
            failures.append("dataset metadata does not use the closed schema")
        if metadata.get("id") != release.get("dataset_id") or metadata.get(
            "title"
        ) != release.get("title"):
            failures.append("dataset metadata identity does not match the release")
        if metadata.get("licenses") != [{"name": KAGGLE_CC_BY_4_LICENSE}]:
            failures.append(
                "dataset metadata license is not Kaggle's canonical CC BY 4.0 value"
            )
        try:
            _scan_safe(metadata, label="dataset metadata")
        except CollectionError as exc:
            failures.append(str(exc))
        resources = metadata.get("resources")
        if not isinstance(resources, list) or any(
            not isinstance(resource, Mapping)
            or set(resource) != {"path", "description"}
            or resource.get("path") not in actual_files
            for resource in resources or []
        ):
            failures.append("dataset metadata resources are invalid")
        if metadata.get("isPrivate") is not (not bool(release.get("publication_ready"))):
            failures.append("dataset privacy state does not match release state")
    validation = release.get("validation")
    if not isinstance(validation, Mapping) or validation.get("negative_never_assistant_target") is not True:
        failures.append("negative-target validation is missing")
    return {"ok": not failures, "failures": failures, "verified_artifacts": verified}


def verify_collection_package(collection: Path) -> dict[str, Any]:
    failures: list[str] = []
    try:
        manifest = _read_object(
            collection / "collection-manifest.json", label="collection manifest"
        )
    except CollectionError as exc:
        return {"ok": False, "failures": [str(exc)], "verified_artifacts": 0}
    if manifest.get("schema_version") != COLLECTION_MANIFEST_SCHEMA:
        failures.append("collection manifest schema mismatch")
    expected_collection_fields = {
        "schema_version",
        "release_id",
        "dataset_id",
        "publication_ready",
        "publication_state",
        "safe_to_train",
        "safe_to_publish",
        "source_candidate_manifest_sha256",
        "contamination_ledger",
        "repo_provenance",
        "claims",
        "artifacts",
        "manifest_payload_sha256",
    }
    if set(manifest) != expected_collection_fields:
        failures.append("collection manifest does not use the closed schema")
    if manifest.get("safe_to_train") is not True:
        failures.append("collection is not explicitly safe_to_train")
    if manifest.get("safe_to_publish") is not bool(manifest.get("publication_ready")):
        failures.append("collection publication flags do not agree")
    try:
        _scan_safe(manifest, label="collection manifest")
    except CollectionError as exc:
        failures.append(str(exc))
    claimed = manifest.get("manifest_payload_sha256")
    payload = dict(manifest)
    payload.pop("manifest_payload_sha256", None)
    actual_payload = hashlib.sha256(
        json.dumps(
            payload, ensure_ascii=False, sort_keys=True, separators=(",", ":")
        ).encode("utf-8")
    ).hexdigest()
    if claimed != actual_payload:
        failures.append("collection manifest payload hash mismatch")
    artifacts = manifest.get("artifacts")
    verified = 0
    if not isinstance(artifacts, Mapping):
        failures.append("collection artifacts missing")
        artifacts = {}
    actual_files = {
        path.relative_to(collection).as_posix()
        for path in collection.rglob("*")
        if path.is_file() or path.is_symlink()
    }
    expected_files = set(artifacts) | {"collection-manifest.json"}
    for relative in sorted(actual_files - expected_files):
        failures.append(f"undeclared collection artifact: {relative}")
    for relative in sorted(expected_files - actual_files):
        failures.append(f"missing collection artifact: {relative}")
    for relative, expected in artifacts.items():
        try:
            path = _resolve_source(collection, relative, label=f"collection artifact {relative}")
        except CollectionError as exc:
            failures.append(str(exc))
            continue
        if not isinstance(expected, Mapping):
            failures.append(f"invalid collection artifact declaration: {relative}")
            continue
        if path.stat().st_size != expected.get("bytes") or _sha256_file(path) != expected.get(
            "sha256"
        ):
            failures.append(f"collection artifact mismatch: {relative}")
            continue
        verified += 1
    dataset_result = verify_dataset_package(collection / "dataset")
    failures.extend(f"dataset: {item}" for item in dataset_result["failures"])
    for notebook_name in ("integrity_exploration", "training_plan"):
        notebook_dir = collection / "notebooks" / notebook_name
        try:
            kernel = _read_object(
                notebook_dir / "kernel-metadata.json",
                label=f"{notebook_name} kernel metadata",
            )
            notebook = _read_object(
                notebook_dir / "notebook.ipynb", label=f"{notebook_name} notebook"
            )
        except CollectionError as exc:
            failures.append(str(exc))
            continue
        expected_kernel_keys = {
            "id",
            "title",
            "code_file",
            "language",
            "kernel_type",
            "is_private",
            "enable_gpu",
            "enable_internet",
            "dataset_sources",
            "competition_sources",
            "kernel_sources",
            "model_sources",
        }
        if set(kernel) != expected_kernel_keys:
            failures.append(f"{notebook_name} kernel metadata is not closed-schema")
        if (
            kernel.get("code_file") != "notebook.ipynb"
            or kernel.get("language") != "python"
            or kernel.get("kernel_type") != "notebook"
            or kernel.get("dataset_sources") != [manifest.get("dataset_id")]
        ):
            failures.append(f"{notebook_name} kernel identity or data source mismatch")
        try:
            _scan_safe(kernel, label=f"{notebook_name} kernel metadata")
        except CollectionError as exc:
            failures.append(str(exc))
        if kernel.get("enable_gpu") is not False or kernel.get("enable_internet") is not False:
            failures.append(f"{notebook_name} is not CPU-only and offline")
        expected_private = not bool(manifest.get("publication_ready"))
        if kernel.get("is_private") is not expected_private:
            failures.append(f"{notebook_name} privacy state mismatch")
        code = "\n".join(
            "".join(cell.get("source") or [])
            for cell in notebook.get("cells", [])
            if isinstance(cell, Mapping) and cell.get("cell_type") == "code"
        )
        try:
            compile(code, str(notebook_dir / "notebook.ipynb"), "exec")
        except SyntaxError:
            failures.append(f"{notebook_name} code does not compile")
        lowered = code.lower()
        if "cloudflared" in lowered or "tunnel" in lowered:
            failures.append(f"{notebook_name} contains a tunnel path")
    return {
        "ok": not failures,
        "failures": failures,
        "verified_artifacts": verified,
        "dataset_verification": dataset_result,
    }


def build_collection(
    source_manifest: Path = DEFAULT_SOURCE,
    output: Path = DEFAULT_OUTPUT,
    *,
    dataset_id: str = DEFAULT_DATASET_ID,
    title: str = DEFAULT_TITLE,
    repo_commit: str | None = None,
    public_ready: bool = False,
    approval_path: Path | None = None,
    force: bool = False,
) -> dict[str, Any]:
    """Build and verify a local Kaggle dataset/notebook collection."""

    _dataset_identity(dataset_id, title)
    repo_provenance = _repo_provenance(repo_commit)
    _reject_link_components(source_manifest, label="source manifest path")
    source_manifest = source_manifest.resolve()
    source_root = source_manifest.parent
    manifest = _read_object(source_manifest, label="candidate manifest")
    _validate_candidate(manifest)
    source_manifest_sha = _sha256_file(source_manifest)
    files = _manifest_files(manifest)

    contamination_decl = manifest.get("contamination_ledger")
    ledger_name = contamination_decl.get("file") if isinstance(contamination_decl, Mapping) else None
    if ledger_name != "contamination-ledger.json" or ledger_name not in files:
        raise CollectionError("candidate does not declare contamination-ledger.json")
    ledger_source = _resolve_source(source_root, ledger_name, label="contamination ledger")
    _verify_declaration(ledger_source, files[ledger_name], label="contamination ledger")
    ledger = _read_object(ledger_source, label="contamination ledger")
    contamination = _verify_contamination(
        manifest, ledger, file_sha256=_sha256_file(ledger_source)
    )
    approval = _verify_approval(
        approval_path,
        source_manifest_sha256=source_manifest_sha,
        contamination=contamination,
        public_ready=public_ready,
    )
    rights = manifest.get("rights")
    if not isinstance(rights, Mapping):
        raise CollectionError("candidate rights declaration is missing")
    if approval is not None:
        if approval.get("row_license") != rights.get("row_license"):
            raise CollectionError("publication approval row license does not match candidate rights")
        if approval.get("release_license") != rights.get("row_license"):
            raise CollectionError("publication approval release license does not match candidate rows")
        if approval.get("rights_holder") != rights.get("rights_holder"):
            raise CollectionError("publication approval rights holder does not match candidate rights")

    lane_declarations: dict[str, list[tuple[str, Mapping[str, Any]]]] = defaultdict(list)
    for name, declaration in sorted(files.items()):
        if name == ledger_name:
            continue
        lane_match = _lane_for_name(name)
        if lane_match is None:
            raise CollectionError(f"unexpected manifest-declared file: {name}")
        if not isinstance(declaration, Mapping):
            raise CollectionError(f"invalid file declaration: {name}")
        lane, _spec = lane_match
        lane_declarations[lane].append((name, declaration))
    missing = [lane for lane in LANES if not lane_declarations.get(lane)]
    if missing:
        raise CollectionError(f"candidate has no declared shards for {missing[0]}")

    output = Path(os.path.abspath(output))
    if _paths_overlap(output, source_root):
        raise CollectionError("output and source candidate directories must not overlap")
    staging = _prepare_staging(output, force=force)
    try:
        dataset = staging / "dataset"
        notebooks = staging / "notebooks"
        dataset.mkdir(parents=True)
        state: dict[str, Any] = {
            "rights": rights,
            "allowed_models": manifest["allowed_models"],
            "clusters": defaultdict(set),
            "sft_targets": set(),
            "dpo_chosen": set(),
            "dpo_rejected": set(),
            "dpo_exact_counts_by_split": defaultdict(Counter),
            "dpo_canonical_counts_by_split": defaultdict(Counter),
            "dpo_cluster_counts_by_split": defaultdict(Counter),
            "pair_bindings": defaultdict(dict),
            "reward_positive": set(),
            "reward_negative": set(),
            "response_exact_by_split": defaultdict(set),
            "response_canonical_by_split": defaultdict(set),
            "reward_label_counts": Counter(),
        }
        lane_index: dict[str, Any] = {}
        lane_rows: dict[str, int] = {}
        for lane, spec in LANES.items():
            copied: list[dict[str, Any]] = []
            for name, declaration in lane_declarations[lane]:
                source = _resolve_source(source_root, name, label=f"source shard {name}")
                _verify_declaration(source, declaration, label=f"source shard {name}")
                copied.append(
                    _copy_jsonl(
                        source,
                        dataset / name,
                        lane=lane,
                        spec=spec,
                        declaration=declaration,
                        state=state,
                    )
                )
            total = sum(item["rows"] for item in copied)
            lane_rows[lane] = total
            lane_index[lane] = {
                "kind": spec["kind"],
                "split": spec["split"],
                "rows": total,
                "shards": copied,
            }

        validation = _validate_cross_lane(state, manifest, lane_rows)
        shutil.copyfile(source_manifest, dataset / "candidate-manifest.json")
        shutil.copyfile(ledger_source, dataset / "contamination-ledger.json")

        release_id = f"duecare-response-{source_manifest_sha[:16]}"
        shard_index = {
            "schema_version": SHARD_INDEX_SCHEMA,
            "release_id": release_id,
            "source_candidate_manifest_sha256": source_manifest_sha,
            "lanes": lane_index,
            "total_rows": sum(lane_rows.values()),
            "lane_semantics": {
                "sft_positive": "positive assistant targets only",
                "dpo_preference": "same-prompt chosen/rejected pairs",
                "reward_labels": "label-0 is contrastive only and never an SFT target",
                "response_inventory": "raw-text-free source snapshot inventory",
                "quarantine": "raw-text-free excluded-row audit metadata",
            },
        }
        _write_json(dataset / "shard-index.json", shard_index)

        training_roles = {
            "sft_positive": "positive_sft_target",
            "dpo_preference": "same_prompt_preference_pair",
            "reward_labels": "reward_or_quality_label",
            "response_inventory": "audit_only_not_trainable",
            "quarantine": "audit_only_excluded",
        }
        preview_rows = [
            {
                "lane": lane,
                "kind": info["kind"],
                "split": info["split"],
                "rows": info["rows"],
                "shards": len(info["shards"]),
                "catalog_contains_raw_text": False,
                "lane_contains_training_text": info["kind"]
                in {"sft_positive", "dpo_preference", "reward_labels"},
                "training_role": training_roles[info["kind"]],
                "note": "aggregate catalog only; see the declared shard and schema for governed payload fields",
            }
            for lane, info in lane_index.items()
        ]
        with (dataset / "preview-catalog.jsonl").open("w", encoding="utf-8", newline="\n") as handle:
            for row in preview_rows:
                handle.write(json.dumps(row, ensure_ascii=False, sort_keys=True, separators=(",", ":")) + "\n")
        _write_csv(
            dataset / "dataset-overview.csv",
            fieldnames=(
                "lane",
                "kind",
                "split",
                "rows",
                "shards",
                "catalog_contains_raw_text",
                "lane_contains_training_text",
                "training_role",
                "note",
            ),
            rows=preview_rows,
        )

        _write_docs(
            dataset,
            manifest=manifest,
            source_manifest_sha256=source_manifest_sha,
            contamination=contamination,
            dataset_id=dataset_id,
            title=title,
            release_id=release_id,
            lane_rows=lane_rows,
            public_ready=public_ready,
        )
        _write_croissant_metadata(
            dataset,
            dataset_id=dataset_id,
            title=title,
            release_id=release_id,
            created_at=manifest.get("created_at"),
            license_name=str(rights.get("row_license")),
            rights_holder=str(rights.get("rights_holder")),
            payload_paths=[
                *[
                    shard["path"]
                    for info in lane_index.values()
                    for shard in info["shards"]
                ],
                "dataset-overview.csv",
                "preview-catalog.jsonl",
                "shard-index.json",
            ],
        )

        _write_notebook_dir(
            notebooks / "integrity_exploration",
            kernel_id=INTEGRITY_NOTEBOOK_ID,
            title="DueCare Response Corpus Integrity",
            dataset_id=dataset_id,
            notebook=_integrity_notebook(
                dataset_id=dataset_id,
                source_manifest_sha256=source_manifest_sha,
                contamination_file_sha256=contamination["file_sha256"],
            ),
            private=not public_ready,
        )
        _write_notebook_dir(
            notebooks / "training_plan",
            kernel_id=TRAINING_PLAN_NOTEBOOK_ID,
            title="DueCare Response Training Plan",
            dataset_id=dataset_id,
            notebook=_training_plan_notebook(
                dataset_id=dataset_id,
                source_manifest_sha256=source_manifest_sha,
            ),
            private=not public_ready,
        )

        resources = [
            {
                "path": shard["path"],
                "description": (
                    f"{info['kind']} {info['split'] or 'audit'} shard with "
                    f"{shard['rows']:,} rows"
                ),
            }
            for info in lane_index.values()
            for shard in info["shards"]
        ]
        resources.extend(
            [
                {
                    "path": "dataset-overview.csv",
                    "description": "Text-free Kaggle-previewable map of lanes, counts, and training roles",
                },
                {
                    "path": "preview-catalog.jsonl",
                    "description": "Aggregate lane catalog in JSONL form; no response text",
                },
                {"path": "README.md", "description": "Reviewer start-here guide and notebook route"},
                {"path": "DATA_CARD.md", "description": "Dataset card, intended use, and claim boundary"},
                {"path": "SCHEMA.md", "description": "Training-lane schemas and negative-target rules"},
                {"path": "LOADING.md", "description": "Standard local, Kaggle, pandas, Hugging Face, and Polars loaders"},
                {"path": "SOURCES.md", "description": "Manifest-bound sources and contamination provenance"},
                {"path": "LIMITATIONS.md", "description": "Known limits and required controls"},
                {"path": "croissant.json", "description": "MLCommons Croissant dataset metadata and payload checksums"},
                {"path": "candidate-manifest.json", "description": "Exact source candidate manifest"},
                {"path": "contamination-ledger.json", "description": "Independent-evaluation contamination ledger"},
                {"path": "shard-index.json", "description": "Lane, split, shard, row, byte, and hash index"},
                {"path": "release-manifest.json", "description": "Closed-schema release identity and checksums"},
            ]
        )
        metadata = {
            "title": title,
            "subtitle": "Measured supervised fine-tuning, preference, reward, and audit lanes",
            "description": (
                f"A {'public' if public_ready else 'private'} Kaggle / Gemma 4 Good Hackathon learning corpus that converts "
                "measured same-prompt DueCare response comparisons into manifest-bound positive "
                "supervised fine-tuning, preference, reward-label, inventory, and quarantine lanes. Includes "
                "professional visual and integrity notebooks; no training or independent lift claim."
            ),
            "id": dataset_id,
            "licenses": [{"name": KAGGLE_CC_BY_4_LICENSE}],
            "isPrivate": not public_ready,
            "keywords": ["nlp"],
            "collaborators": [],
            "resources": sorted(resources, key=lambda item: item["path"]),
        }
        _write_json(dataset / "dataset-metadata.json", metadata)

        release: dict[str, Any] = {
            "schema_version": RELEASE_SCHEMA,
            "collection_schema": COLLECTION_SCHEMA,
            "release_id": release_id,
            "created_at": manifest.get("created_at"),
            "dataset_id": dataset_id,
            "title": title,
            "repo_provenance": repo_provenance,
            "source_candidate_schema": manifest.get("schema_version"),
            "source_candidate_manifest_sha256": source_manifest_sha,
            "contamination_ledger": contamination,
            "publication_state": "approved_public_ready" if public_ready else "candidate_private",
            "safe_to_train": True,
            "publication_ready": public_ready,
            "safe_to_publish": public_ready,
            "public": public_ready,
            "publication_approval": approval,
            "counts": dict(sorted(lane_rows.items())),
            "validation": validation,
            "rights": manifest.get("rights"),
            "reasoning_data_policy": manifest.get("reasoning_data_policy"),
            "claims": {
                "training_completed": False,
                "adapter_produced": False,
                "model_lift_demonstrated": False,
                "independent_external_evaluation_completed": False,
                "full_flywheel_closure": False,
            },
            "no_upload_or_publication_performed": True,
            "artifacts": _artifact_index(
                dataset,
                exclude={"release-manifest.json", "dataset-metadata.json"},
            ),
        }
        release["release_manifest_payload_sha256"] = _release_payload_sha256(release)
        _write_json(dataset / "release-manifest.json", release)
        verification = verify_dataset_package(dataset)
        if not verification["ok"]:
            raise CollectionError(f"generated package verification failed: {verification['failures'][0]}")

        collection_manifest: dict[str, Any] = {
            "schema_version": COLLECTION_MANIFEST_SCHEMA,
            "release_id": release_id,
            "dataset_id": dataset_id,
            "publication_ready": public_ready,
            "publication_state": release["publication_state"],
            "safe_to_train": True,
            "safe_to_publish": public_ready,
            "source_candidate_manifest_sha256": source_manifest_sha,
            "contamination_ledger": contamination,
            "repo_provenance": repo_provenance,
            "claims": release["claims"],
            "artifacts": _artifact_index(
                staging, exclude={"collection-manifest.json"}
            ),
        }
        collection_manifest["manifest_payload_sha256"] = hashlib.sha256(
            json.dumps(
                collection_manifest,
                ensure_ascii=False,
                sort_keys=True,
                separators=(",", ":"),
            ).encode("utf-8")
        ).hexdigest()
        _write_json(staging / "collection-manifest.json", collection_manifest)
        collection_verification = verify_collection_package(staging)
        if not collection_verification["ok"]:
            raise CollectionError(
                "generated collection verification failed: "
                f"{collection_verification['failures'][0]}"
            )

        retained_backup = _commit_staging(staging, output)
        staging = output  # prevents cleanup of the completed output
        return {
            "release_id": release_id,
            "publication_state": release["publication_state"],
            "publication_ready": public_ready,
            "safe_to_train": True,
            "safe_to_publish": public_ready,
            "no_upload_or_publication_performed": True,
            "source_candidate_manifest_sha256": source_manifest_sha,
            "contamination_ledger": contamination,
            "dataset": {"path": str(output / "dataset"), "counts": dict(sorted(lane_rows.items()))},
            "notebooks": {
                "integrity_exploration": str(output / "notebooks" / "integrity_exploration"),
                "training_plan": str(output / "notebooks" / "training_plan"),
            },
            "repo_provenance": repo_provenance,
            "previous_output_backup_retained": retained_backup is not None,
            "verification": collection_verification,
        }
    except Exception:
        if staging.exists() and staging != output:
            shutil.rmtree(staging, ignore_errors=True)
        raise


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--source-manifest", type=Path, default=DEFAULT_SOURCE)
    parser.add_argument("--output", type=Path, default=DEFAULT_OUTPUT)
    parser.add_argument("--dataset-id", default=DEFAULT_DATASET_ID)
    parser.add_argument("--title", default=DEFAULT_TITLE)
    parser.add_argument("--repo-commit")
    parser.add_argument("--public-ready", action="store_true")
    parser.add_argument("--approval", type=Path)
    parser.add_argument("--force", action="store_true")
    parser.add_argument("--verify", type=Path, metavar="DATASET_DIR")
    return parser


def main(argv: Sequence[str] | None = None) -> int:
    args = build_parser().parse_args(argv)
    try:
        if args.verify:
            verify_root = args.verify.resolve()
            result = (
                verify_collection_package(verify_root)
                if (verify_root / "collection-manifest.json").is_file()
                else verify_dataset_package(verify_root)
            )
        else:
            result = build_collection(
                args.source_manifest,
                args.output,
                dataset_id=args.dataset_id,
                title=args.title,
                repo_commit=args.repo_commit,
                public_ready=args.public_ready,
                approval_path=args.approval,
                force=args.force,
            )
    except CollectionError as exc:
        print(json.dumps({"ok": False, "error": str(exc)}, indent=2), file=sys.stderr)
        return 2
    print(json.dumps(result, indent=2, sort_keys=True))
    return 0 if result.get("ok", result.get("verification", {}).get("ok", False)) else 1


if __name__ == "__main__":
    raise SystemExit(main())
