#!/usr/bin/env python3
"""Phase 3 training runner -- Unsloth LoRA (SFT then DPO) on the harness-lift distilled data.

Consumes the organized training splits from organize_training_data.py:
  reports/training/sft_train.jsonl : {"messages": [user, {"role":"assistant", harnessed reply}]}
  reports/training/dpo_train.jsonl : {"prompt", "chosen": harnessed reply, "rejected": baseline reply}

The held-out splits stay out of the trainer and are reserved for the generalisation diagnostic.

and fine-tunes a Gemma 4 base with the canonical Unsloth recipe (FastModel -> get_peft_model ->
get_chat_template "gemma-4-thinking" -> SFTTrainer + train_on_responses_only, then an optional DPO
pass) so the model internalises the harness's stable behaviours -- arm C of the 4-arm eval in
docs/phase3_training_framework.md. The recipe mirrors the A-00 kernel's training block.

GPU-bound: the training step imports unsloth/trl/torch and needs a CUDA GPU (Kaggle T4/A100). On a
machine without them use --validate to check the data + config + plan WITHOUT the heavy deps (CPU-safe).

    python scripts/train_lift_distill.py --validate                       # CPU: check data + print plan
    python scripts/train_lift_distill.py --validate --dpo reports/training/contract_dpo.jsonl
    python scripts/train_lift_distill.py --validate --dpo reports/training/dpo_train_plus_contract.jsonl
    python scripts/train_lift_distill.py --test-run                       # GPU: ~20-step E4B smoke
    python scripts/train_lift_distill.py --base-model google/gemma-4-E4B-it --epochs 2   # GPU: full

Prereqs (Kaggle): pip install "unsloth" "unsloth_zoo" trl peft accelerate bitsandbytes
Design: docs/phase3_training_framework.md  .  Special Technology Track: Unsloth
"""
from __future__ import annotations

import argparse
import hashlib
import importlib.metadata
import json
import pathlib
import re
import sys
from collections import Counter
from datetime import datetime, timezone
from typing import Any, Callable

_ROOT = pathlib.Path(__file__).resolve().parents[1]
sys.path.insert(0, str(pathlib.Path(__file__).resolve().parent))
from build_reasoning_targets import _ACTION_TERMS, _has_any, has_statute  # noqa: E402
from remedy_taxonomy import CORE_BASE_REMEDIES, CORE_TRIGGER_REMEDIES  # noqa: E402
from reasoning_contract import verify_reasoning  # noqa: E402

SFT_DEFAULT = _ROOT / "reports" / "training" / "sft_train.jsonl"
DPO_DEFAULT = _ROOT / "reports" / "training" / "dpo_train.jsonl"
OUT_DEFAULT = _ROOT / "reports" / "training" / "adapter"
REPAIRED_SFT_NAME = "sft_train_reasoning_repaired.jsonl"
CONTRACT_DPO_NAME = "contract_dpo.jsonl"
DPO_MIX_NAME = "dpo_train_plus_contract.jsonl"
CONTRACT_DPO_LINKS = {"statute", "action"}
_EMAIL = re.compile(r"\b[\w.+-]+@[\w-]+\.[\w.-]+\b", re.I)
_PHONE = re.compile(r"\+?\d[\d\s().\-]{8,}\d")
_LOCAL_PATH_HINT = re.compile(
    r"(?:[A-Za-z]:[\\/]|\\\\|(?:^|[\s\"'(:])/(?:Users|home|tmp|var|mnt|private|Volumes)(?:/|$)|~[\\/])",
    re.I,
)
_SAFE_RELATIVE_PATH = re.compile(r"^[A-Za-z0-9._/\-]+$")
_SAFE_MODEL_REF = re.compile(r"^[A-Za-z0-9][A-Za-z0-9._-]*(/[A-Za-z0-9][A-Za-z0-9._-]*)?$")
_SAFE_PROMPT_ID = re.compile(r"^[A-Za-z0-9 ._:/#-]{1,180}$")
_SAFE_MANIFEST_ISSUE_CODE = re.compile(r"^[a-z][a-z0-9_]{0,160}$")
_PATH_REPORT_KEYS = frozenset({"path", "base_path", "output_path", "file", "sft", "dpo", "output_dir"})
_VALIDATION_DETAIL_PREFIXES = {
    "SFT variant manifest missing:": "SFT variant manifest missing",
    "SFT variant manifest invalid:": "SFT variant manifest invalid",
    "DPO variant manifest missing:": "DPO variant manifest missing",
    "DPO variant manifest invalid:": "DPO variant manifest invalid",
}
SOURCE_REPAIR_SUMMARY_FIELDS = (
    "path",
    "output_path",
    "repaired_rows",
    "safe_to_train",
    "require_core_remedies",
    "by_added_core_remedy",
    "repair_manifest_issues",
    "source_queue",
)
SOURCE_QUEUE_SUMMARY_FIELDS = (
    "metadata_only",
    "privacy_scan_ok",
    "safe_for_repair",
    "actionable_for_repair",
    "queue_manifest_issues",
    "queued",
    "target_links",
    "require_core_remedies",
    "by_core_missing",
)
BASE_DPO_SOURCE_SUMMARY_FIELDS = (
    "path",
    "base_path",
    "dpo_train",
    "dpo_heldout",
    "seed",
    "heldout_fraction",
    "dedup_kept_pre_split",
)
CONTRACT_DPO_SOURCE_SUMMARY_FIELDS = (
    "path",
    "output_path",
    "pairs",
    "safe_to_train",
    "by_ablated_link",
    "pair_integrity_issues",
    "contract_manifest_issues",
    "duplicate_output_pair_rows",
    "skipped_duplicate_pairs",
)
REASONING_REPAIR_META_FIELDS = (
    "source",
    "original_prompt_id",
    "category",
    "added_links",
    "added_core_remedies",
    "original_missing_links",
    "original_target_missing_links",
    "original_target_core_missing",
    "repaired_chain_links",
    "repaired_n_steps",
    "selected_convention",
)
SFT_VARIANT_META_FIELDS = ("name", "base_prompt_id", "source", "replacement")
CORE_REMEDY_KEYS = set(CORE_BASE_REMEDIES) | {
    remedy for remedies in CORE_TRIGGER_REMEDIES.values() for remedy in remedies
}
DEFAULT_BASE = "google/gemma-4-E4B-it"
DEFAULT_BASE_REVISION = "a4c2d58be94dda072b918d9db64ee85c8ed34e3f"
CHAT_TEMPLATE = "gemma-4-thinking"
INSTRUCTION_PART = "<|turn>user\n"
RESPONSE_PART = "<|turn>model\n"


def load_jsonl(path: pathlib.Path) -> list[dict[str, Any]]:
    if not path.exists():
        return []
    rows: list[dict[str, Any]] = []
    for ln in path.read_text(encoding="utf-8").splitlines():
        if ln.strip():
            try:
                row = json.loads(ln)
            except json.JSONDecodeError:
                continue
            if isinstance(row, dict):
                rows.append(row)
    return rows


def load_sft_manifest(path: pathlib.Path) -> dict[str, Any] | None:
    """Load the optional metadata manifest beside a generated SFT variant."""
    manifest_path = path.with_name(f"{path.stem}_manifest.json")
    if not manifest_path.exists():
        if path.name == REPAIRED_SFT_NAME:
            return {"path": str(manifest_path), "missing": True}
        return None
    try:
        doc = json.loads(manifest_path.read_text(encoding="utf-8"))
    except json.JSONDecodeError as exc:
        return {"path": str(manifest_path), "error": f"invalid JSON: {exc}"}
    if isinstance(doc, dict):
        doc = dict(doc)
        doc["path"] = str(manifest_path)
        return doc
    return {"path": str(manifest_path), "error": "manifest root is not an object"}


def load_dpo_manifest(path: pathlib.Path) -> dict[str, Any] | None:
    """Load the optional metadata manifest beside a generated DPO variant."""
    manifest_path = path.with_name(f"{path.stem}_manifest.json")
    if not manifest_path.exists():
        if path.name in {CONTRACT_DPO_NAME, DPO_MIX_NAME}:
            return {"path": str(manifest_path), "missing": True}
        return None
    try:
        doc = json.loads(manifest_path.read_text(encoding="utf-8"))
    except json.JSONDecodeError as exc:
        return {"path": str(manifest_path), "error": f"invalid JSON: {exc}"}
    if isinstance(doc, dict):
        doc = dict(doc)
        doc["path"] = str(manifest_path)
        return doc
    return {"path": str(manifest_path), "error": "manifest root is not an object"}


def normalize_messages(messages: list[dict]) -> list[dict]:
    """assistant->model; string content -> [{type:text,text}] (the gemma-4 chat-template shape)."""
    out: list[dict] = []
    for msg in messages:
        if not isinstance(msg, dict):
            continue
        item = dict(msg)
        content = item.get("content")
        if not isinstance(content, str):
            continue
        if item.get("role") == "assistant":
            item["role"] = "model"
        item["content"] = [{"type": "text", "text": content}]
        out.append(item)
    return out


def _variant_names(sft: list[dict[str, Any]]) -> list[str]:
    names: set[str] = set()
    for row in sft:
        if not isinstance(row, dict):
            continue
        variant = (row.get("_meta") or {}).get("sft_variant") or {}
        name = variant.get("name")
        if name:
            names.add(str(name))
    return sorted(names)


def _sft_prompt_id_count(sft: list[dict[str, Any]]) -> int:
    count = 0
    for row in sft:
        if not isinstance(row, dict):
            continue
        meta = row.get("_meta")
        prompt_id = meta.get("prompt_id") if isinstance(meta, dict) else None
        if (
            isinstance(prompt_id, str)
            and _SAFE_PROMPT_ID.fullmatch(prompt_id.strip())
            and not _has_sensitive_display_text(prompt_id)
        ):
            count += 1
    return count


def _same_path(left: str | None, right: pathlib.Path | None) -> bool:
    if not left or right is None:
        return False
    display_right = _display_report_path(right)
    if left == display_right and display_right not in {"redacted", "n/a"}:
        return True
    try:
        return pathlib.Path(left).resolve() == pathlib.Path(right).resolve()
    except OSError:
        return False


def _safe_relative_report_path(path: pathlib.PurePath) -> str:
    display = path.as_posix()
    if not display or display.startswith("../") or "/../" in display:
        return "redacted"
    if _has_sensitive_display_text(display):
        return "redacted"
    if not _SAFE_RELATIVE_PATH.fullmatch(display):
        return "redacted"
    return display


def _has_sensitive_display_text(text: str) -> bool:
    return bool(
        _EMAIL.search(text)
        or _PHONE.search(text)
        or _LOCAL_PATH_HINT.search(text)
        or re.search(r"\b\d{9,}\b", text)
    )


def _display_report_path(raw_path: Any) -> str:
    if not raw_path:
        return "n/a"
    raw = str(raw_path)
    try:
        path = pathlib.Path(raw)
        if path.is_absolute():
            try:
                return _safe_relative_report_path(path.relative_to(_ROOT))
            except ValueError:
                return "external"
        return _safe_relative_report_path(pathlib.PurePosixPath(pathlib.PureWindowsPath(raw).as_posix()))
    except (OSError, RuntimeError, ValueError):
        return "redacted"


def _display_model_ref(raw_model: Any) -> str:
    text = str(raw_model or "").strip()
    if not text:
        return "n/a"
    if _has_sensitive_display_text(text) or text.startswith(("/", ".", "~")) or "\\" in text or ":" in text:
        return "redacted"
    if not _SAFE_MODEL_REF.fullmatch(text):
        return "redacted"
    return text


def _display_exception(exc: BaseException) -> str:
    kind = type(exc).__name__
    text = str(exc).strip()
    if not text:
        return kind
    if _has_sensitive_display_text(text) or "/" in text or "\\" in text or len(text) > 160:
        return f"{kind}: details redacted"
    if not re.fullmatch(r"[A-Za-z0-9 .,:;_()'\"[\]\-]+", text):
        return f"{kind}: details redacted"
    return f"{kind}: {text}"


def _display_validation_issue(issue: Any) -> str:
    text = str(issue or "validation issue")
    for prefix, safe in _VALIDATION_DETAIL_PREFIXES.items():
        if text.startswith(prefix):
            return safe
    if _has_sensitive_display_text(text):
        return "validation issue redacted"
    return text


def _sanitized_manifest_issues(value: Any) -> list[str] | None:
    if value is None:
        return None
    if not value:
        return []
    if not isinstance(value, list):
        return ["manifest_issue_redacted"]
    issues: list[str] = []
    for item in value:
        if (
            isinstance(item, str)
            and _SAFE_MANIFEST_ISSUE_CODE.fullmatch(item)
            and not _has_sensitive_display_text(item)
        ):
            issues.append(item)
        else:
            issues.append("manifest_issue_redacted")
    return issues


def _display_validation_report(value: Any, *, key: str = "") -> Any:
    if key == "issues" and isinstance(value, list):
        return [_display_validation_issue(issue) for issue in value]
    if isinstance(value, dict):
        return {item_key: _display_validation_report(item_value, key=str(item_key))
                for item_key, item_value in value.items()}
    if isinstance(value, list):
        return [_display_validation_report(item, key=key) for item in value]
    if key == "base_model":
        return _display_model_ref(value)
    if isinstance(value, str) and (key in _PATH_REPORT_KEYS or key.endswith("_path")):
        return _display_report_path(value)
    if isinstance(value, str) and _has_sensitive_display_text(value):
        return "redacted"
    return value


def _extra_keys(doc: Any, allowed: tuple[str, ...]) -> list[str]:
    if not isinstance(doc, dict):
        return []
    allowed_set = set(allowed)
    return sorted(str(key) for key in doc if key not in allowed_set)


def _source_queue_summary(source_queue: Any) -> dict[str, Any]:
    if not isinstance(source_queue, dict):
        return {field: None for field in SOURCE_QUEUE_SUMMARY_FIELDS}
    summary = {field: source_queue.get(field) for field in SOURCE_QUEUE_SUMMARY_FIELDS}
    summary["queue_manifest_issues"] = _sanitized_manifest_issues(source_queue.get("queue_manifest_issues"))
    target_links = source_queue.get("target_links")
    if isinstance(target_links, list):
        summary["target_links"] = [
            link for link in target_links
            if isinstance(link, str) and link in CONTRACT_DPO_LINKS
        ]
    summary["by_core_missing"] = _core_remedy_count_summary(source_queue.get("by_core_missing"))
    return summary


def _source_repair_summary(source_repair: Any) -> dict[str, Any] | None:
    if not isinstance(source_repair, dict):
        return None
    return {
        "path": source_repair.get("path"),
        "output_path": source_repair.get("output_path"),
        "repaired_rows": source_repair.get("repaired_rows"),
        "safe_to_train": source_repair.get("safe_to_train"),
        "require_core_remedies": source_repair.get("require_core_remedies"),
        "by_added_core_remedy": _core_remedy_count_summary(source_repair.get("by_added_core_remedy")),
        "repair_manifest_issues": _sanitized_manifest_issues(source_repair.get("repair_manifest_issues")),
        "source_queue": _source_queue_summary(source_repair.get("source_queue")),
    }


def _core_remedy_count_summary(values: Any) -> dict[str, int] | None:
    if not isinstance(values, dict):
        return None
    out: dict[str, int] = {}
    for key, value in values.items():
        if not isinstance(key, str) or key not in CORE_REMEDY_KEYS:
            continue
        try:
            out[key] = int(value)
        except (TypeError, ValueError):
            continue
    return {key: out[key] for key in sorted(out)}


def _dpo_link_count_summary(values: Any) -> dict[str, int] | None:
    if not isinstance(values, dict):
        return None
    out: dict[str, int] = {}
    for key, value in values.items():
        if not isinstance(key, str) or key not in CONTRACT_DPO_LINKS:
            continue
        try:
            out[key] = int(value)
        except (TypeError, ValueError):
            continue
    return {key: out[key] for key in sorted(out)}


def _dpo_link_count_keys_valid(values: Any) -> bool:
    if not isinstance(values, dict):
        return False
    for key, value in values.items():
        if not isinstance(key, str) or key not in CONTRACT_DPO_LINKS:
            return False
        try:
            int(value)
        except (TypeError, ValueError):
            return False
    return True


def _base_dpo_source_summary(source: Any) -> dict[str, Any] | None:
    if not isinstance(source, dict):
        return None
    return {field: source.get(field) for field in BASE_DPO_SOURCE_SUMMARY_FIELDS}


def _contract_dpo_source_summary(source: Any) -> dict[str, Any] | None:
    if not isinstance(source, dict):
        return None
    return {
        "path": source.get("path"),
        "output_path": source.get("output_path"),
        "pairs": source.get("pairs"),
        "safe_to_train": source.get("safe_to_train"),
        "by_ablated_link": _dpo_link_count_summary(source.get("by_ablated_link")),
        "pair_integrity_issues": _sanitized_manifest_issues(source.get("pair_integrity_issues")),
        "contract_manifest_issues": _sanitized_manifest_issues(source.get("contract_manifest_issues")),
        "duplicate_output_pair_rows": source.get("duplicate_output_pair_rows"),
        "skipped_duplicate_pairs": source.get("skipped_duplicate_pairs"),
    }


def _mixed_dpo_sources_summary(source_manifests: Any) -> dict[str, Any] | None:
    if not isinstance(source_manifests, dict):
        return None
    return {
        "base_dpo": _base_dpo_source_summary(source_manifests.get("base_dpo")),
        "contract_dpo": _contract_dpo_source_summary(source_manifests.get("contract_dpo")),
    }


def _repair_target_links(sft_manifest: dict[str, Any]) -> set[str]:
    source_repair = sft_manifest.get("source_repair_manifest")
    source_queue = source_repair.get("source_queue") if isinstance(source_repair, dict) else {}
    links = source_queue.get("target_links") if isinstance(source_queue, dict) else None
    if isinstance(links, list) and links:
        valid = {link for link in links if isinstance(link, str) and link in CONTRACT_DPO_LINKS}
        if len(valid) == len(links):
            return valid
    return set(CONTRACT_DPO_LINKS)


def _core_remedy_repairs_enabled(sft_manifest: dict[str, Any]) -> bool:
    source_repair = sft_manifest.get("source_repair_manifest")
    source_queue = source_repair.get("source_queue") if isinstance(source_repair, dict) else {}
    return (
        isinstance(source_repair, dict)
        and source_repair.get("require_core_remedies") is True
        and isinstance(source_queue, dict)
        and source_queue.get("require_core_remedies") is True
    )


def _invalid_core_remedy_list(value: Any, *, require_non_empty: bool = False) -> bool:
    if not isinstance(value, list):
        return True
    if require_non_empty and not value:
        return True
    return any(not isinstance(item, str) or item not in CORE_REMEDY_KEYS for item in value)


def _reasoning_repair_source_issues(
    sft_manifest: dict[str, Any],
    source_repair: dict[str, Any],
) -> list[str]:
    """Validate the embedded build_reasoning_repairs.py manifest summary."""
    issues: list[str] = []
    if _extra_keys(source_repair, SOURCE_REPAIR_SUMMARY_FIELDS):
        issues.append("reasoning_repaired source repair manifest must contain metadata summary keys only")
    if source_repair.get("safe_to_train") is not True:
        issues.append("reasoning_repaired source repair manifest must have safe_to_train=true")
    if source_repair.get("repair_manifest_issues"):
        issues.append("reasoning_repaired source repair manifest must have no repair_manifest_issues")

    source_repair_rows = source_repair.get("repaired_rows")
    if not isinstance(source_repair_rows, int) or source_repair_rows <= 0:
        issues.append("reasoning_repaired source repair manifest must include repaired_rows>0")
    else:
        repaired_input_rows = sft_manifest.get("repaired_input_rows")
        replaced_rows = sft_manifest.get("replaced_rows")
        if not isinstance(repaired_input_rows, int) or repaired_input_rows <= 0:
            issues.append("reasoning_repaired SFT manifest must include repaired_input_rows>0")
        elif source_repair_rows != repaired_input_rows:
            issues.append("reasoning_repaired source repair repaired_rows must match repaired_input_rows")
        if not isinstance(replaced_rows, int) or replaced_rows <= 0:
            issues.append("reasoning_repaired SFT manifest must include replaced_rows>0")
        elif source_repair_rows != replaced_rows:
            issues.append("reasoning_repaired source repair repaired_rows must match replaced_rows")

    source_queue = source_repair.get("source_queue")
    if not isinstance(source_queue, dict):
        issues.append("reasoning_repaired source repair manifest must include source_queue")
    else:
        if _extra_keys(source_queue, SOURCE_QUEUE_SUMMARY_FIELDS):
            issues.append("reasoning_repaired source repair source_queue must contain metadata summary keys only")
        if source_queue.get("metadata_only") is not True:
            issues.append("reasoning_repaired source repair source_queue must have metadata_only=true")
        if source_queue.get("privacy_scan_ok") is not True:
            issues.append("reasoning_repaired source repair source_queue must have privacy_scan_ok=true")
        if source_queue.get("safe_for_repair") is not True:
            issues.append("reasoning_repaired source repair source_queue must have safe_for_repair=true")
        if source_queue.get("actionable_for_repair") is not True:
            issues.append("reasoning_repaired source repair source_queue must have actionable_for_repair=true")
        if source_queue.get("queue_manifest_issues"):
            issues.append("reasoning_repaired source repair source_queue must have no queue_manifest_issues")
        queued = source_queue.get("queued")
        if source_repair_rows is not None and isinstance(source_repair_rows, int):
            if not isinstance(queued, int) or queued < source_repair_rows:
                issues.append("reasoning_repaired source repair source_queue queued must cover repaired_rows")
        target_links = source_queue.get("target_links")
        if (not isinstance(target_links, list) or not target_links
                or any(not isinstance(link, str) or link not in CONTRACT_DPO_LINKS for link in target_links)):
            issues.append("reasoning_repaired source repair source_queue target_links must be statute/action")
        if source_repair.get("require_core_remedies") is True and source_queue.get("require_core_remedies") is not True:
            issues.append("reasoning_repaired source repair core remedies metadata must be manifest-enabled")
        if source_queue.get("require_core_remedies") is True and source_repair.get("require_core_remedies") is not True:
            issues.append("reasoning_repaired source repair core remedies metadata must be manifest-enabled")
    return issues


def _sum_int_values(values: Any) -> int | None:
    if not isinstance(values, dict):
        return None
    total = 0
    for value in values.values():
        try:
            total += int(value)
        except (TypeError, ValueError):
            return None
    return total


def _contract_link_present(text: str, link: str) -> bool:
    if link == "statute":
        return has_statute(text)
    if link == "action":
        return _has_any(text, _ACTION_TERMS)
    return False


def _nonempty_text(value: Any) -> bool:
    return isinstance(value, str) and bool(value.strip())


def _contract_pair_integrity_issues(
    rows: list[dict],
    dpo_manifest: dict[str, Any],
    *,
    label: str,
) -> list[str]:
    """Validate the text-level ablation guarantee for contract-DPO rows."""
    issues: list[str] = []
    counts: Counter[str] = Counter()
    min_steps = dpo_manifest.get("min_steps")
    if not isinstance(min_steps, int) or min_steps <= 0:
        min_steps = 4

    for row in rows:
        prompt = row.get("prompt", "")
        chosen = row.get("chosen", "")
        rejected = row.get("rejected", "")
        meta = row.get("_meta") if isinstance(row.get("_meta"), dict) else {}
        link = str(meta.get("ablated_link") or "")
        if not (_nonempty_text(prompt) and _nonempty_text(chosen) and _nonempty_text(rejected)):
            counts["invalid_shape"] += 1
            continue
        prompt = prompt.strip()
        chosen = chosen.strip()
        rejected = rejected.strip()
        if chosen == rejected:
            counts["rejected_unchanged"] += 1
        if len(rejected) >= len(chosen):
            counts["rejected_not_shorter"] += 1
        if link not in CONTRACT_DPO_LINKS:
            counts["invalid_ablated_link"] += 1
            continue
        if not _contract_link_present(chosen, link):
            counts["chosen_missing_ablated_link"] += 1
        if _contract_link_present(rejected, link):
            counts["rejected_still_carries_ablated_link"] += 1
        chosen_verdict = verify_reasoning(chosen, min_steps=min_steps)
        rejected_verdict = verify_reasoning(rejected, min_steps=min_steps)
        if not chosen_verdict.satisfied:
            counts["chosen_not_contract_satisfied"] += 1
        if rejected_verdict.steps.get(link):
            counts["rejected_contract_still_has_ablated_link"] += 1
        if rejected_verdict.n_steps >= chosen_verdict.n_steps:
            counts["chain_not_reduced"] += 1

    if counts["invalid_shape"]:
        issues.append(f"{label} rows must include non-empty prompt/chosen/rejected")
    if counts["rejected_unchanged"]:
        issues.append(f"{label} rejected text must differ from chosen")
    if counts["rejected_not_shorter"]:
        issues.append(f"{label} rejected text must be shorter deletion-only output")
    if counts["invalid_ablated_link"]:
        issues.append(f"{label} rows must use statute/action ablated_link")
    if counts["chosen_missing_ablated_link"]:
        issues.append(f"{label} chosen text must carry the ablated_link")
    if counts["rejected_still_carries_ablated_link"]:
        issues.append(f"{label} rejected text must remove the ablated_link")
    if counts["chosen_not_contract_satisfied"]:
        issues.append(f"{label} chosen text must satisfy the reasoning contract")
    if counts["rejected_contract_still_has_ablated_link"]:
        issues.append(f"{label} rejected contract verdict must miss the ablated_link")
    if counts["chain_not_reduced"]:
        issues.append(f"{label} rejected chain score must be lower than chosen")
    return issues


def _reasoning_repaired_sft_row_issues(
    sft: list[dict],
    sft_manifest: dict[str, Any],
) -> list[str]:
    """Validate row-level provenance tags for sft_train_reasoning_repaired JSONL rows."""
    issues: list[str] = []
    repaired_variant_rows = 0
    missing_replacement_rows = 0
    missing_prompt_id_rows = 0
    prompt_mismatch_rows = 0
    missing_repair_meta_rows = 0
    wrong_repair_source_rows = 0
    missing_added_links_rows = 0
    invalid_added_links_rows = 0
    invalid_added_core_remedy_rows = 0
    core_metadata_without_manifest_rows = 0
    missing_added_repair_item_rows = 0
    unexpected_repair_meta_rows = 0
    unexpected_variant_meta_rows = 0
    allowed_repair_links = _repair_target_links(sft_manifest)
    allow_core_remedies = _core_remedy_repairs_enabled(sft_manifest)

    for row in sft:
        meta = row.get("_meta") or {}
        variant = meta.get("sft_variant")
        if not isinstance(variant, dict):
            continue
        if variant.get("name") != "reasoning_repaired":
            continue
        repaired_variant_rows += 1
        if _extra_keys(variant, SFT_VARIANT_META_FIELDS):
            unexpected_variant_meta_rows += 1
        prompt_id = str(meta.get("prompt_id") or "")
        base_prompt_id = str(variant.get("base_prompt_id") or "")
        if variant.get("replacement") is not True:
            missing_replacement_rows += 1
        if not prompt_id or not base_prompt_id:
            missing_prompt_id_rows += 1
        elif prompt_id != base_prompt_id:
            prompt_mismatch_rows += 1

        repair = meta.get("reasoning_repair")
        if not isinstance(repair, dict):
            missing_repair_meta_rows += 1
            continue
        if _extra_keys(repair, REASONING_REPAIR_META_FIELDS):
            unexpected_repair_meta_rows += 1
        if repair.get("source") != "reasoning_gap_queue":
            wrong_repair_source_rows += 1
        original_prompt_id = str(repair.get("original_prompt_id") or "")
        if prompt_id and original_prompt_id and original_prompt_id != prompt_id:
            prompt_mismatch_rows += 1
        added_links = repair.get("added_links")
        added_core = repair.get("added_core_remedies")
        has_valid_links = (
            isinstance(added_links, list)
            and bool(added_links)
            and not any(not isinstance(link, str) or link not in allowed_repair_links for link in added_links)
        )
        has_valid_core = (
            isinstance(added_core, list)
            and bool(added_core)
            and not _invalid_core_remedy_list(added_core, require_non_empty=True)
        )
        if not isinstance(added_links, list):
            missing_added_links_rows += 1
        elif added_links and any(not isinstance(link, str) or link not in allowed_repair_links for link in added_links):
            invalid_added_links_rows += 1
        elif not added_links and not (allow_core_remedies and has_valid_core):
            missing_added_links_rows += 1
        if (added_core is not None or "original_target_core_missing" in repair) and not allow_core_remedies:
            core_metadata_without_manifest_rows += 1
        if added_core is not None and _invalid_core_remedy_list(added_core):
            invalid_added_core_remedy_rows += 1
        if "original_target_core_missing" in repair and _invalid_core_remedy_list(
            repair.get("original_target_core_missing"),
        ):
            invalid_added_core_remedy_rows += 1
        if not has_valid_links and not has_valid_core:
            missing_added_repair_item_rows += 1

    if repaired_variant_rows != sft_manifest.get("replaced_rows"):
        issues.append("reasoning_repaired row count must match manifest replaced_rows")
    if repaired_variant_rows != sft_manifest.get("repaired_input_rows"):
        issues.append("reasoning_repaired row count must match manifest repaired_input_rows")
    if unexpected_variant_meta_rows:
        issues.append("reasoning_repaired rows must contain only expected sft_variant metadata")
    if missing_replacement_rows:
        issues.append("reasoning_repaired rows must have sft_variant.replacement=true")
    if missing_prompt_id_rows:
        issues.append("reasoning_repaired rows must include prompt_id and base_prompt_id")
    if prompt_mismatch_rows:
        issues.append("reasoning_repaired row prompt IDs must match repair metadata")
    if missing_repair_meta_rows:
        issues.append("reasoning_repaired rows must include reasoning_repair metadata")
    if wrong_repair_source_rows:
        issues.append("reasoning_repaired rows must have reasoning_repair.source=reasoning_gap_queue")
    if missing_added_links_rows:
        issues.append("reasoning_repaired rows must include non-empty reasoning_repair.added_links")
    if invalid_added_links_rows:
        issues.append("reasoning_repaired rows must use source_queue target_links for reasoning_repair.added_links")
    if invalid_added_core_remedy_rows:
        issues.append("reasoning_repaired rows must use known core remedies for reasoning_repair.added_core_remedies")
    if core_metadata_without_manifest_rows:
        issues.append("reasoning_repaired rows must not include core remedy repair metadata without a core-enabled source manifest")
    if missing_added_repair_item_rows:
        issues.append("reasoning_repaired rows must include at least one added repair item")
    if unexpected_repair_meta_rows:
        issues.append("reasoning_repaired rows must contain only expected reasoning_repair metadata")
    return issues


def _mixed_dpo_source_issues(dpo_manifest: dict[str, Any]) -> list[str]:
    """Validate embedded source summaries for dpo_train_plus_contract manifests."""
    issues: list[str] = []
    source_manifests = dpo_manifest.get("source_manifests")
    if not isinstance(source_manifests, dict):
        return ["mixed DPO variant manifest must include source_manifests"]
    if _extra_keys(source_manifests, ("base_dpo", "contract_dpo")):
        issues.append("mixed DPO variant source_manifests must contain base_dpo and contract_dpo only")

    base_rows = dpo_manifest.get("base_rows")
    contract_rows = dpo_manifest.get("contract_rows")
    base_source = source_manifests.get("base_dpo")
    contract_source = source_manifests.get("contract_dpo")

    if not isinstance(base_source, dict):
        issues.append("mixed DPO variant manifest must include base_dpo source manifest summary")
    else:
        if _extra_keys(base_source, BASE_DPO_SOURCE_SUMMARY_FIELDS):
            issues.append("mixed DPO base source manifest must contain metadata summary keys only")
        if not isinstance(base_rows, int):
            issues.append("mixed DPO variant manifest base_rows must be an integer")
        elif base_source.get("dpo_train") != base_rows:
            issues.append("mixed DPO base source dpo_train must match base_rows")

    if not isinstance(contract_source, dict):
        issues.append("mixed DPO variant manifest must include contract_dpo source manifest summary")
    else:
        if _extra_keys(contract_source, CONTRACT_DPO_SOURCE_SUMMARY_FIELDS):
            issues.append("mixed DPO contract source manifest must contain metadata summary keys only")
        if contract_source.get("safe_to_train") is not True:
            issues.append("mixed DPO contract source manifest must have safe_to_train=true")
        if contract_source.get("pair_integrity_issues"):
            issues.append("mixed DPO contract source manifest must have no pair_integrity_issues")
        if contract_source.get("contract_manifest_issues"):
            issues.append("mixed DPO contract source manifest must have no contract_manifest_issues")
        if isinstance(contract_rows, int):
            if contract_source.get("pairs") != contract_rows:
                issues.append("mixed DPO contract source pairs must match contract_rows")
            if not _dpo_link_count_keys_valid(contract_source.get("by_ablated_link")):
                issues.append("mixed DPO contract source link counts must use statute/action numeric counts")
            source_links_total = _sum_int_values(contract_source.get("by_ablated_link") or {})
            if source_links_total is None:
                issues.append("mixed DPO contract source link counts must be numeric")
            elif source_links_total != contract_rows:
                issues.append("mixed DPO contract source link counts must match contract_rows")
        if contract_source.get("duplicate_output_pair_rows") not in (0, None):
            issues.append("mixed DPO contract source manifest must have duplicate_output_pair_rows=0")
    return issues


def _mixed_dpo_row_issues(dpo: list[dict], dpo_manifest: dict[str, Any]) -> list[str]:
    """Validate row-level provenance tags for dpo_train_plus_contract JSONL rows."""
    issues: list[str] = []
    base_component_rows = 0
    contract_component_rows = 0
    missing_variant_rows = 0
    wrong_variant_name_rows = 0
    invalid_component_rows = 0
    contract_source_not_contract_component = 0
    contract_component_not_contract_source = 0
    missing_contract_link_rows = 0
    by_link: Counter[str] = Counter()
    contract_component_rows_list: list[dict] = []

    for row in dpo:
        meta = row.get("_meta") or {}
        variant = meta.get("dpo_variant")
        if not isinstance(variant, dict):
            missing_variant_rows += 1
            if meta.get("source") == "contract_ablation":
                contract_source_not_contract_component += 1
            continue

        if variant.get("name") != "base_plus_contract":
            wrong_variant_name_rows += 1
        component = variant.get("component")
        if component == "base":
            base_component_rows += 1
        elif component == "contract":
            contract_component_rows += 1
        else:
            invalid_component_rows += 1

        is_contract_source = meta.get("source") == "contract_ablation"
        if is_contract_source and component != "contract":
            contract_source_not_contract_component += 1
        if component == "contract" and not is_contract_source:
            contract_component_not_contract_source += 1
        if component == "contract":
            contract_component_rows_list.append(row)
            link = meta.get("ablated_link")
            if link:
                by_link[str(link)] += 1
            else:
                missing_contract_link_rows += 1

    if missing_variant_rows:
        issues.append("mixed DPO rows must include dpo_variant metadata")
    if wrong_variant_name_rows:
        issues.append("mixed DPO row dpo_variant names must be base_plus_contract")
    if invalid_component_rows:
        issues.append("mixed DPO row dpo_variant components must be base or contract")
    if base_component_rows != dpo_manifest.get("base_rows"):
        issues.append("mixed DPO row base components must match manifest base_rows")
    if contract_component_rows != dpo_manifest.get("contract_rows"):
        issues.append("mixed DPO row contract components must match manifest contract_rows")
    if contract_source_not_contract_component:
        issues.append("mixed DPO contract_ablation rows must be tagged as contract component")
    if contract_component_not_contract_source:
        issues.append("mixed DPO contract component rows must have source=contract_ablation")
    if missing_contract_link_rows:
        issues.append("mixed DPO contract component rows must include ablated_link")
    manifest_links = dpo_manifest.get("by_ablated_link")
    if contract_component_rows and not isinstance(manifest_links, dict):
        issues.append("mixed DPO variant manifest must include by_ablated_link")
    elif isinstance(manifest_links, dict):
        if not _dpo_link_count_keys_valid(manifest_links):
            issues.append("mixed DPO manifest by_ablated_link must use statute/action numeric counts")
        if _sum_int_values(manifest_links) != contract_component_rows:
            issues.append("mixed DPO manifest by_ablated_link total must match contract_rows")
        actual_links = {key: by_link[key] for key in sorted(by_link)}
        expected_links: dict[str, int] = {}
        for key, value in manifest_links.items():
            try:
                expected_links[str(key)] = int(value)
            except (TypeError, ValueError):
                issues.append("mixed DPO manifest by_ablated_link counts must be numeric")
                expected_links = {}
                break
        if expected_links and expected_links != actual_links:
            issues.append("mixed DPO contract row ablated_link counts must match manifest by_ablated_link")
    if contract_component_rows_list:
        issues.extend(_contract_pair_integrity_issues(
            contract_component_rows_list,
            dpo_manifest,
            label="mixed DPO contract component",
        ))
    return issues


def _contract_dpo_row_issues(dpo: list[dict], dpo_manifest: dict[str, Any]) -> list[str]:
    """Validate row-level provenance tags for direct contract_dpo.jsonl selections."""
    issues: list[str] = []
    by_link: Counter[str] = Counter()
    missing_source_rows = 0
    missing_link_rows = 0

    for row in dpo:
        meta = row.get("_meta") or {}
        if meta.get("source") != "contract_ablation":
            missing_source_rows += 1
        link = meta.get("ablated_link")
        if link:
            by_link[str(link)] += 1
        else:
            missing_link_rows += 1

    if missing_source_rows:
        issues.append("contract DPO rows must have source=contract_ablation")
    if missing_link_rows:
        issues.append("contract DPO rows must include ablated_link")
    manifest_links = dpo_manifest.get("by_ablated_link")
    if not isinstance(manifest_links, dict):
        issues.append("contract DPO manifest must include by_ablated_link")
    else:
        if not _dpo_link_count_keys_valid(manifest_links):
            issues.append("contract DPO manifest by_ablated_link must use statute/action numeric counts")
        if _sum_int_values(manifest_links) != len(dpo):
            issues.append("contract DPO manifest by_ablated_link total must match loaded rows")
        actual_links = {k: by_link[k] for k in sorted(by_link)}
        expected_links: dict[str, int] = {}
        for key, value in manifest_links.items():
            try:
                expected_links[str(key)] = int(value)
            except (TypeError, ValueError):
                issues.append("contract DPO manifest by_ablated_link counts must be numeric")
                expected_links = {}
                break
        if expected_links and expected_links != actual_links:
            issues.append("contract DPO row ablated_link counts must match manifest by_ablated_link")
    issues.extend(_contract_pair_integrity_issues(dpo, dpo_manifest, label="contract DPO"))
    return issues


def validate(
    sft: list[dict],
    dpo: list[dict],
    sft_manifest: dict[str, Any] | None = None,
    dpo_manifest: dict[str, Any] | None = None,
    *,
    sft_path: pathlib.Path | None = None,
    dpo_path: pathlib.Path | None = None,
) -> dict[str, Any]:
    """CPU-safe schema check + stats. Returns {ok, sft_valid, dpo_valid, issues, ...}."""
    issues: list[str] = []
    raw_sft_rows = len(sft)
    raw_dpo_rows = len(dpo)
    sft = [row for row in sft if isinstance(row, dict)]
    dpo = [row for row in dpo if isinstance(row, dict)]
    malformed_sft_rows = raw_sft_rows - len(sft)
    malformed_dpo_rows = raw_dpo_rows - len(dpo)
    variant_rows = sum(1 for r in sft if (r.get("_meta") or {}).get("sft_variant"))
    variant_names = _variant_names(sft)
    sft_prompt_ids = _sft_prompt_id_count(sft)
    contract_dpo_rows = sum(1 for r in dpo if (r.get("_meta") or {}).get("source") == "contract_ablation")
    contract_dpo_selected = dpo_path is not None and dpo_path.name == CONTRACT_DPO_NAME
    dpo_mix_selected = dpo_path is not None and dpo_path.name == DPO_MIX_NAME
    sft_ok = 0
    for r in sft:
        msgs = r.get("messages") or []
        msgs = [m for m in msgs if isinstance(m, dict)] if isinstance(msgs, list) else []
        text_msgs = [m for m in msgs if m.get("role") in {"user", "assistant", "model"}]
        roles = [m.get("role") for m in text_msgs]
        if ("user" in roles and ("assistant" in roles or "model" in roles)
                and all(_nonempty_text(m.get("content")) for m in text_msgs)):
            sft_ok += 1
    dpo_ok = 0
    for r in dpo:
        if (_nonempty_text(r.get("prompt")) and _nonempty_text(r.get("chosen"))
                and _nonempty_text(r.get("rejected"))):
            dpo_ok += 1
    if raw_sft_rows and sft_ok == 0:
        issues.append("no valid SFT rows (need messages with a user + assistant turn)")
    if raw_dpo_rows and dpo_ok == 0:
        issues.append("no valid DPO rows (need non-empty prompt/chosen/rejected)")
    if not raw_sft_rows and not raw_dpo_rows:
        issues.append("no training split -- run scripts/build_lift_training_data.py, then "
                      "scripts/organize_training_data.py")
    manifest_summary = None
    if variant_rows and sft_manifest is None:
        issues.append("SFT variant rows require an adjacent manifest")
    if sft_manifest is not None:
        manifest_summary = {
            "path": sft_manifest.get("path"),
            "variant": sft_manifest.get("variant"),
            "safe_to_train": sft_manifest.get("safe_to_train"),
            "output_rows": sft_manifest.get("output_rows"),
            "output_path": sft_manifest.get("output_path"),
            "output_prompt_ids": sft_manifest.get("output_prompt_ids"),
            "one_row_per_base_prompt": sft_manifest.get("one_row_per_base_prompt"),
            "repaired_input_rows": sft_manifest.get("repaired_input_rows"),
            "replaced_rows": sft_manifest.get("replaced_rows"),
            "require_core_remedies": sft_manifest.get("require_core_remedies"),
            "by_added_core_remedy": _core_remedy_count_summary(sft_manifest.get("by_added_core_remedy")),
            "source_repair_manifest": _source_repair_summary(sft_manifest.get("source_repair_manifest")),
            "source_repair_manifest_issues": _sanitized_manifest_issues(
                sft_manifest.get("source_repair_manifest_issues")
            ),
        }
        if sft_manifest.get("missing"):
            issues.append(f"SFT variant manifest missing: {sft_manifest.get('path')}")
        elif sft_manifest.get("error"):
            issues.append(f"SFT variant manifest invalid: {sft_manifest.get('error')}")
        else:
            if variant_rows:
                if len(variant_names) != 1:
                    issues.append("SFT variant rows must have exactly one variant name")
                elif sft_manifest.get("variant") != variant_names[0]:
                    issues.append("SFT variant manifest variant does not match loaded rows")
                if sft_manifest.get("safe_to_train") is not True:
                    issues.append("SFT variant manifest must have safe_to_train=true")
                if sft_manifest.get("one_row_per_base_prompt") is not True:
                    issues.append("SFT variant manifest must have one_row_per_base_prompt=true")
                if sft_manifest.get("output_rows") != len(sft):
                    issues.append("SFT variant manifest output_rows does not match loaded SFT rows")
                if sft_manifest.get("output_prompt_ids") != sft_prompt_ids:
                    issues.append("SFT variant manifest output_prompt_ids does not match loaded SFT rows")
                if sft_path is not None and not _same_path(sft_manifest.get("output_path"), sft_path):
                    issues.append("SFT variant manifest output_path does not match selected SFT file")
                if variant_names == ["reasoning_repaired"]:
                    source_repair = sft_manifest.get("source_repair_manifest")
                    if not isinstance(source_repair, dict):
                        issues.append("reasoning_repaired SFT manifest must include source_repair_manifest")
                    else:
                        issues.extend(_reasoning_repair_source_issues(sft_manifest, source_repair))
                    issues.extend(_reasoning_repaired_sft_row_issues(sft, sft_manifest))
                    if sft_manifest.get("source_repair_manifest_issues"):
                        issues.append("SFT variant manifest must have no source_repair_manifest_issues")
            elif sft_manifest.get("safe_to_train") is False:
                issues.append("SFT variant manifest is not safe_to_train")
            elif sft_manifest.get("output_rows") is not None and sft_manifest.get("output_rows") != len(sft):
                issues.append("SFT variant manifest output_rows does not match loaded SFT rows")
    dpo_manifest_summary = None
    if contract_dpo_rows and dpo_manifest is None:
        issues.append("contract-derived DPO rows require an adjacent manifest")
    if dpo_mix_selected and dpo_manifest is None:
        issues.append("mixed DPO variant requires an adjacent manifest")
    if dpo_manifest is not None:
        dpo_manifest_summary = {
            "path": dpo_manifest.get("path"),
            "variant": dpo_manifest.get("variant"),
            "safe_to_train": dpo_manifest.get("safe_to_train"),
            "output_path": dpo_manifest.get("output_path"),
            "pairs": dpo_manifest.get("pairs"),
            "output_rows": dpo_manifest.get("output_rows"),
            "base_rows": dpo_manifest.get("base_rows"),
            "contract_rows": dpo_manifest.get("contract_rows"),
            "by_ablated_link": _dpo_link_count_summary(dpo_manifest.get("by_ablated_link")),
            "pair_integrity_issues": _sanitized_manifest_issues(dpo_manifest.get("pair_integrity_issues")),
            "contract_manifest_issues": _sanitized_manifest_issues(dpo_manifest.get("contract_manifest_issues")),
            "duplicate_output_pair_rows": dpo_manifest.get("duplicate_output_pair_rows"),
            "skipped_duplicate_pairs": dpo_manifest.get("skipped_duplicate_pairs"),
            "source_manifests": _mixed_dpo_sources_summary(dpo_manifest.get("source_manifests")),
            "source_manifest_issues": _sanitized_manifest_issues(dpo_manifest.get("source_manifest_issues")),
            "min_steps": dpo_manifest.get("min_steps"),
        }
        if dpo_manifest.get("missing"):
            issues.append(f"DPO variant manifest missing: {dpo_manifest.get('path')}")
        elif dpo_manifest.get("error"):
            issues.append(f"DPO variant manifest invalid: {dpo_manifest.get('error')}")
        else:
            manifest_pairs = dpo_manifest.get("pairs", dpo_manifest.get("output_rows"))
            if manifest_pairs != len(dpo):
                issues.append("DPO variant manifest pairs does not match loaded DPO rows")
            if dpo_path is not None and not _same_path(dpo_manifest.get("output_path"), dpo_path):
                issues.append("DPO variant manifest output_path does not match selected DPO file")
            if contract_dpo_rows and not dpo_manifest.get("by_ablated_link"):
                issues.append("contract-derived DPO manifest must include by_ablated_link")
            if dpo_manifest.get("safe_to_train") is False:
                issues.append("DPO variant manifest is not safe_to_train")
            if dpo_manifest.get("duplicate_output_pair_rows") not in (0, None):
                issues.append("DPO variant manifest must have duplicate_output_pair_rows=0")
            is_dpo_mix = dpo_manifest.get("variant") == "base_plus_contract" or dpo_mix_selected
            is_contract_dpo = (
                not is_dpo_mix
                and (contract_dpo_selected or contract_dpo_rows > 0)
            )
            if is_contract_dpo:
                if dpo_manifest.get("safe_to_train") is not True:
                    issues.append("contract DPO manifest must have safe_to_train=true")
                if dpo_manifest.get("pair_integrity_issues"):
                    issues.append("contract DPO manifest must have no pair_integrity_issues")
                if dpo_manifest.get("contract_manifest_issues"):
                    issues.append("contract DPO manifest must have no contract_manifest_issues")
                manifest_pairs_value = dpo_manifest.get("pairs")
                if not isinstance(manifest_pairs_value, int) or manifest_pairs_value <= 0:
                    issues.append("contract DPO manifest must include pairs>0")
                if contract_dpo_selected and len(dpo) == 0:
                    issues.append("contract DPO selected file must contain at least one pair")
                if contract_dpo_selected and contract_dpo_rows != len(dpo):
                    issues.append("contract DPO selected file rows must all be contract_ablation rows")
                issues.extend(_contract_dpo_row_issues(dpo, dpo_manifest))
            if is_dpo_mix:
                if dpo_manifest.get("safe_to_train") is not True:
                    issues.append("mixed DPO variant manifest must have safe_to_train=true")
                if dpo_manifest.get("output_rows") != len(dpo):
                    issues.append("mixed DPO variant manifest output_rows does not match loaded DPO rows")
                if dpo_manifest.get("contract_rows") != contract_dpo_rows:
                    issues.append("mixed DPO variant manifest contract_rows does not match loaded DPO rows")
                base_rows = dpo_manifest.get("base_rows")
                contract_rows = dpo_manifest.get("contract_rows")
                if isinstance(base_rows, int) and isinstance(contract_rows, int):
                    if base_rows + contract_rows != len(dpo):
                        issues.append("mixed DPO variant manifest base_rows + contract_rows does not match loaded DPO rows")
                else:
                    issues.append("mixed DPO variant manifest must include base_rows and contract_rows")
                if dpo_manifest.get("source_manifest_issues"):
                    issues.append("mixed DPO variant manifest must have no source_manifest_issues")
                issues.extend(_mixed_dpo_source_issues(dpo_manifest))
                issues.extend(_mixed_dpo_row_issues(dpo, dpo_manifest))
    return {"ok": not issues, "sft_rows": len(sft), "sft_valid": sft_ok,
            "sft_malformed_rows": malformed_sft_rows,
            "sft_variant_rows": variant_rows, "sft_variant_names": variant_names,
            "dpo_rows": len(dpo), "dpo_valid": dpo_ok,
            "dpo_malformed_rows": malformed_dpo_rows,
            "contract_dpo_rows": contract_dpo_rows,
            "sft_manifest": manifest_summary, "dpo_manifest": dpo_manifest_summary,
            "issues": issues}


def render_sft(rows: list[dict], apply_chat_template: Callable[[list[dict]], str]) -> list[dict]:
    """Render {messages} -> {text} via a chat-template fn (testable; the GPU path passes the tokenizer's)."""
    out: list[dict] = []
    for r in rows:
        if not isinstance(r, dict):
            continue
        msgs = normalize_messages(r.get("messages") or [])
        if not msgs:
            continue
        roles = {msg.get("role") for msg in msgs}
        if not {"user", "model"} <= roles:
            continue
        out.append({"text": apply_chat_template(msgs).removeprefix("<bos>")})
    return out


def _string_field(row: dict[str, Any], key: str) -> str:
    value = row.get(key, "")
    return value if isinstance(value, str) else ""


def render_dpo(rows: list[dict], format_prompt: Callable[[str], str]) -> list[dict]:
    """Render DPO pairs for the trainer, ignoring malformed non-string pair fields."""
    out: list[dict] = []
    for row in rows:
        if not isinstance(row, dict):
            continue
        prompt = _string_field(row, "prompt")
        chosen = _string_field(row, "chosen")
        rejected = _string_field(row, "rejected")
        if not (_nonempty_text(prompt) and _nonempty_text(chosen) and _nonempty_text(rejected)):
            continue
        out.append({"prompt": format_prompt(prompt), "chosen": chosen, "rejected": rejected})
    return out


def build_plan(args: argparse.Namespace) -> dict[str, Any]:
    """The training plan (CPU-safe; printed by --validate)."""
    base_revision = str(getattr(args, "base_revision", "") or "").strip()
    if not base_revision and args.base_model == DEFAULT_BASE:
        base_revision = DEFAULT_BASE_REVISION
    return {
        "base_model": args.base_model,
        "base_model_revision": base_revision,
        "chat_template": CHAT_TEMPLATE,
        "max_seq_length": args.max_seq,
        "lora": {"r": args.lora_r, "alpha": args.lora_alpha, "dropout": 0.0},
        "sft": {"file": str(args.sft), "epochs": (1 if args.test_run else args.epochs),
                "max_steps": (20 if args.test_run else args.max_steps),
                "per_device_batch": args.batch, "grad_accum": args.grad_accum, "lr": args.lr},
        "dpo": {"enabled": (not args.skip_dpo), "file": str(args.dpo), "beta": args.dpo_beta,
                "max_steps": (10 if args.test_run else args.dpo_max_steps), "lr": args.dpo_lr,
                "rpo_alpha": args.rpo_alpha, "max_length": args.max_seq,
                "max_prompt_length": args.max_seq // 2},
        "output_dir": str(args.out), "gguf": bool(args.gguf), "test_run": bool(args.test_run),
    }


def _load_dpo_components(*, enabled: bool) -> tuple[Any | None, Any | None]:
    """Load the requested DPO stage or fail before any GPU training work begins."""
    if not enabled:
        return None, None
    try:
        from trl import DPOConfig, DPOTrainer
    except ImportError as exc:
        raise SystemExit(
            "[train] DPO was requested but trl DPOConfig/DPOTrainer are unavailable "
            f"({_display_exception(exc)}). Install a compatible trl version or pass --skip-dpo "
            "explicitly for SFT-only training."
        ) from exc
    return DPOConfig, DPOTrainer


def _file_sha256(path: str | pathlib.Path) -> str:
    digest = hashlib.sha256()
    with pathlib.Path(path).open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def _plan_file_sha256(stage: dict[str, Any]) -> str:
    raw_path = stage.get("file")
    if not raw_path or not pathlib.Path(str(raw_path)).is_file():
        return "unavailable"
    return _file_sha256(str(raw_path))


def _pin_adapter_revision(output_dir: str | pathlib.Path, *, base_model: str, revision: str) -> None:
    """Persist the immutable base revision in PEFT's standard adapter config."""
    if not revision:
        return
    config_path = pathlib.Path(output_dir) / "adapter_config.json"
    if not config_path.exists():
        return
    payload = json.loads(config_path.read_text(encoding="utf-8"))
    if not isinstance(payload, dict):
        raise ValueError("adapter_config.json must contain an object")
    payload["base_model_name_or_path"] = base_model
    payload["revision"] = revision
    config_path.write_text(json.dumps(payload, indent=2, sort_keys=True) + "\n", encoding="utf-8")


def _package_version(name: str) -> str:
    try:
        return importlib.metadata.version(name)
    except importlib.metadata.PackageNotFoundError:
        return "not-installed"
    except Exception as exc:  # noqa: BLE001
        return f"unavailable:{type(exc).__name__}"


def train(plan: dict[str, Any], sft: list[dict], dpo: list[dict]) -> str:
    """The GPU path: SFT then (optionally) DPO via Unsloth. Heavy deps imported lazily."""
    base_revision = str(plan.get("base_model_revision") or "").strip()
    if not base_revision and not pathlib.Path(str(plan["base_model"])).exists():
        raise SystemExit(
            "[train] remote base models require --base-revision with an immutable commit SHA"
        )
    try:
        from unsloth import FastModel
        from unsloth.chat_templates import get_chat_template, train_on_responses_only
        from datasets import Dataset
        from trl import SFTTrainer, SFTConfig
        import torch
    except ImportError as exc:
        raise SystemExit(
            f"Unsloth/trl/torch not available ({_display_exception(exc)}). The training step needs a CUDA GPU "
            "(Kaggle T4/A100). On this machine run with --validate. Install on Kaggle:\n"
            '  pip install "unsloth" "unsloth_zoo" trl peft accelerate bitsandbytes')
    import inspect

    DPOConfig, DPOTrainer = _load_dpo_components(enabled=bool(plan["dpo"]["enabled"]))

    out_dir = plan["output_dir"]
    display_out_dir = _display_report_path(out_dir)
    display_gguf_dir = _display_report_path(f"{out_dir}-gguf")
    print(f"[train] loading {_display_model_ref(plan['base_model'])} (4-bit) ...", flush=True)
    load_kwargs = dict(
        model_name=plan["base_model"], max_seq_length=plan["max_seq_length"],
        dtype=None, load_in_4bit=True, full_finetuning=False,
    )
    if base_revision:
        load_kwargs["revision"] = base_revision
    model, tokenizer = FastModel.from_pretrained(**load_kwargs)
    lc = plan["lora"]
    model = FastModel.get_peft_model(
        model, finetune_vision_layers=False, finetune_language_layers=True,
        finetune_attention_modules=True, finetune_mlp_modules=True,
        r=lc["r"], lora_alpha=lc["alpha"], lora_dropout=lc["dropout"], bias="none", random_state=42,
    )
    tokenizer = get_chat_template(tokenizer, chat_template=plan["chat_template"])
    bf16 = bool(torch.cuda.is_available() and torch.cuda.is_bf16_supported())

    # ---- SFT stage ----
    def _apply(msgs: list[dict]) -> str:
        return tokenizer.apply_chat_template(msgs, tokenize=False, add_generation_prompt=False)

    sft_text = render_sft(sft, _apply)
    print(f"[train] SFT on {len(sft_text)} examples (bf16={bf16})", flush=True)
    s = plan["sft"]
    sft_args = SFTConfig(
        dataset_text_field="text", per_device_train_batch_size=s["per_device_batch"],
        gradient_accumulation_steps=s["grad_accum"], warmup_steps=5,
        num_train_epochs=s["epochs"], max_steps=s["max_steps"], learning_rate=s["lr"],
        fp16=not bf16, bf16=bf16, logging_steps=5, save_strategy="no", output_dir=out_dir,
        optim="adamw_8bit", weight_decay=0.001, lr_scheduler_type="linear", seed=42, report_to="none",
    )
    kw = {"model": model, "train_dataset": Dataset.from_list(sft_text), "args": sft_args}
    sig = inspect.signature(SFTTrainer.__init__)
    if "tokenizer" in sig.parameters:
        kw["tokenizer"] = tokenizer
    elif "processing_class" in sig.parameters:
        kw["processing_class"] = tokenizer
    trainer = SFTTrainer(**kw)
    trainer = train_on_responses_only(trainer, instruction_part=INSTRUCTION_PART, response_part=RESPONSE_PART)
    trainer.train()
    model.save_pretrained(out_dir)
    tokenizer.save_pretrained(out_dir)
    _pin_adapter_revision(
        out_dir,
        base_model=str(plan["base_model"]),
        revision=base_revision,
    )
    executed_stages = ["sft"]
    print(f"[train] SFT adapter saved to {display_out_dir}", flush=True)

    # ---- DPO stage (prefer the harnessed reply over the baseline) ----
    d = plan["dpo"]
    if d["enabled"] and dpo:
        assert DPOConfig is not None and DPOTrainer is not None

        def _fmt_prompt(p: str) -> str:
            return tokenizer.apply_chat_template(
                normalize_messages([{"role": "user", "content": p}]),
                tokenize=False, add_generation_prompt=True).removeprefix("<bos>")

        dpo_rows = render_dpo(dpo, _fmt_prompt)
        print(f"[train] DPO on {len(dpo_rows)} pairs (beta={d['beta']})", flush=True)
        # Set max_length/max_prompt_length explicitly: trl's small default silently truncates the
        # long grounded `chosen` while the short `rejected` survives -> a pure length-bias confound.
        # Filter to the params THIS trl version's DPOConfig accepts (these + rpo_alpha vary by version).
        dpo_cfg_kw = dict(
            per_device_train_batch_size=s["per_device_batch"], gradient_accumulation_steps=s["grad_accum"],
            warmup_steps=5, max_steps=d["max_steps"], learning_rate=d["lr"], beta=d["beta"],
            fp16=not bf16, bf16=bf16, logging_steps=5, save_strategy="no",
            output_dir=out_dir + "-dpo", optim="adamw_8bit", seed=42, report_to="none",
            max_length=d["max_length"], max_prompt_length=d["max_prompt_length"],
        )
        if d.get("rpo_alpha"):
            dpo_cfg_kw["rpo_alpha"] = d["rpo_alpha"]
        _dpo_params = set(inspect.signature(DPOConfig.__init__).parameters)
        dpo_args = DPOConfig(**{k: v for k, v in dpo_cfg_kw.items() if k in _dpo_params})
        dkw = {"model": model, "args": dpo_args, "train_dataset": Dataset.from_list(dpo_rows)}
        dsig = inspect.signature(DPOTrainer.__init__)
        if "tokenizer" in dsig.parameters:
            dkw["tokenizer"] = tokenizer
        elif "processing_class" in dsig.parameters:
            dkw["processing_class"] = tokenizer
        DPOTrainer(**dkw).train()
        model.save_pretrained(out_dir)
        tokenizer.save_pretrained(out_dir)
        _pin_adapter_revision(
            out_dir,
            base_model=str(plan["base_model"]),
            revision=base_revision,
        )
        executed_stages.append("dpo")
        print(f"[train] DPO-refined adapter saved to {display_out_dir}", flush=True)

    completion = {
        "schema_version": "1.0",
        "handoff_kind": "duecare.training.completion.v1",
        "completed_at": datetime.now(timezone.utc).isoformat(),
        "base_model": str(plan["base_model"]),
        "base_model_revision": base_revision or "local-model-artifact",
        "executed_stages": executed_stages,
        "sft_sha256": _plan_file_sha256(plan["sft"]),
        "dpo_sha256": _plan_file_sha256(plan["dpo"]) if plan["dpo"]["enabled"] else "",
        "output_dir": _display_report_path(out_dir),
        "library_versions": {
            name: _package_version(name)
            for name in ("unsloth", "trl", "peft", "transformers", "datasets")
        },
    }
    completion_path = pathlib.Path(out_dir) / "training_completion_manifest.json"
    completion_path.parent.mkdir(parents=True, exist_ok=True)
    completion_path.write_text(json.dumps(completion, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    print(f"[train] completion manifest -> {_display_report_path(completion_path)}", flush=True)

    # ---- GGUF export for on-device (LiteRT / llama.cpp) ----
    if plan.get("gguf"):
        try:
            model.save_pretrained_gguf(out_dir + "-gguf", tokenizer, quantization_method="q4_k_m")
            print(f"[train] GGUF saved to {display_gguf_dir}", flush=True)
        except Exception as exc:  # noqa: BLE001
            print(f"[train] GGUF export skipped: {_display_exception(exc)}", flush=True)
    return out_dir


def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--base-model", default=DEFAULT_BASE, help="canonical Gemma 4 E4B base model ref")
    ap.add_argument(
        "--base-revision",
        default="",
        help="immutable model commit; the canonical E4B default is pinned automatically",
    )
    ap.add_argument("--sft", type=pathlib.Path, default=SFT_DEFAULT)
    ap.add_argument("--dpo", type=pathlib.Path, default=DPO_DEFAULT)
    ap.add_argument("--out", type=pathlib.Path, default=OUT_DEFAULT)
    ap.add_argument("--max-seq", type=int, default=2048)
    ap.add_argument("--epochs", type=int, default=2)
    ap.add_argument("--max-steps", type=int, default=-1, help="overrides epochs when > 0")
    ap.add_argument("--batch", type=int, default=2)
    ap.add_argument("--grad-accum", type=int, default=4)
    ap.add_argument("--lr", type=float, default=2e-4)
    ap.add_argument("--lora-r", type=int, default=16)
    ap.add_argument("--lora-alpha", type=int, default=16)
    ap.add_argument("--skip-dpo", action="store_true", help="SFT only (skip the preference pass)")
    ap.add_argument("--dpo-beta", type=float, default=0.1)
    ap.add_argument("--dpo-max-steps", type=int, default=200)
    ap.add_argument("--dpo-lr", type=float, default=5e-6, help="DPO learning rate (keep < SFT --lr)")
    ap.add_argument("--rpo-alpha", type=float, default=1.0,
                    help="RPO regularizer (NLL-on-chosen inside DPO; anti-degeneration). 0 disables")
    ap.add_argument("--gguf", action="store_true", help="also export a q4_k_m GGUF for on-device")
    ap.add_argument("--test-run", action="store_true", help="GPU smoke: ~20 SFT + ~10 DPO steps")
    ap.add_argument("--validate", action="store_true",
                    help="CPU-safe: check the data + print the plan, no training")
    args = ap.parse_args(argv)

    sft = load_jsonl(args.sft)
    dpo = load_jsonl(args.dpo)
    sft_manifest = load_sft_manifest(args.sft)
    dpo_manifest = load_dpo_manifest(args.dpo)
    v = validate(sft, dpo, sft_manifest=sft_manifest, dpo_manifest=dpo_manifest,
                 sft_path=args.sft, dpo_path=args.dpo)
    plan = build_plan(args)
    display_plan = _display_validation_report(plan)
    display_v = _display_validation_report(v)
    print("[plan]", json.dumps(display_plan, indent=2))
    print("[data]", json.dumps(display_v, indent=2))
    if not v["ok"]:
        print("[validate] FAILED: " + "; ".join(display_v["issues"]))
        return 1
    if args.validate:
        print("[validate] OK -- data + plan valid. Run on a GPU (drop --validate) to train.")
        return 0
    out = train(plan, sft, dpo)
    print(f"[train] done -> {_display_report_path(out)}. Next: 4-arm eval (stock vs this adapter, harness off/on).")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
