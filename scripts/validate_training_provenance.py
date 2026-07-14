#!/usr/bin/env python3
"""Validate the Phase 3 training provenance chain before publishing model evidence.

This bundles the CPU-safe gates that should agree before a model card is cited:

1. latest finetune_registry.py row exists for the model_id;
2. structured artifact_files fingerprints verify against local files;
3. build_model_card.py can render a card from that verified record; and
4. corridor_expansion_plan.json is safe, metadata-only, and tied to the current quality audit; and
5. train_lift_distill.py validates the selected SFT/DPO files recorded in the row.

Generated data stays under gitignored reports/training/; this script only reads those artifacts.

    python scripts/validate_training_provenance.py
    python scripts/validate_training_provenance.py --model-id duecare-gemma-4-e4b-safetyjudge-v0.1.0
    python scripts/validate_training_provenance.py --json
"""
from __future__ import annotations

import argparse
import hashlib
import json
import math
import pathlib
import re
import sys
from typing import Any

_ROOT = pathlib.Path(__file__).resolve().parents[1]
sys.path.insert(0, str(pathlib.Path(__file__).resolve().parent))

from audit_training_quality import (  # noqa: E402
    QUALITY_AUDIT_SUMMARY_FIELDS,
    quality_audit_summary as _quality_audit_summary_from_file,
)
from build_model_card import (  # noqa: E402
    _display_artifact_path,
    _display_model_id,
    _sanitized_artifact_issues,
    render_card,
)
from finetune_registry import (  # noqa: E402
    REGISTRY,
    latest_by_id,
    load as load_registry,
    verify_record_artifacts,
)
from train_lift_distill import (  # noqa: E402
    DPO_DEFAULT,
    SFT_DEFAULT,
    load_dpo_manifest,
    load_jsonl,
    load_sft_manifest,
    validate as validate_training_data,
)

DEFAULT_MODEL_ID = "duecare-gemma-4-e4b-safetyjudge-v0.1.0"
_QUALITY_AUDIT_SUMMARY_ALLOWED_KEYS = set(QUALITY_AUDIT_SUMMARY_FIELDS) | {"path"}
_PATH_REPORT_KEYS = frozenset({"path", "base_path", "output_path", "file", "sft", "dpo"})
_UNRESOLVABLE_PATHS = frozenset({"external", "redacted", "n/a"})
_CORRIDOR_PLAN_FORBIDDEN_FIELDS = frozenset({"messages", "prompt", "chosen", "rejected", "assistant", "text"})
_CORRIDOR_PLAN_REQUIRED_MANIFEST_FIELDS = frozenset({
    "planned_task_count",
    "batch_count",
    "recommended_rows",
    "metadata_only",
    "source_privacy_ok",
    "privacy_scan",
    "plan_manifest_issues",
    "safe_for_curation",
    "actionable_for_curation",
})
_TRAINER_LABEL_ISSUE_SUFFIXES = (
    "rows must include non-empty prompt/chosen/rejected",
    "rejected text must differ from chosen",
    "rejected text must be shorter deletion-only output",
    "rows must use statute/action ablated_link",
    "chosen text must carry the ablated_link",
    "rejected text must remove the ablated_link",
    "chosen text must satisfy the reasoning contract",
    "rejected contract verdict must miss the ablated_link",
    "rejected chain score must be lower than chosen",
)
_SAFE_TRAINER_ISSUES = frozenset({
    "reasoning_repaired source repair manifest must contain metadata summary keys only",
    "reasoning_repaired source repair manifest must have safe_to_train=true",
    "reasoning_repaired source repair manifest must have no repair_manifest_issues",
    "reasoning_repaired source repair manifest must include repaired_rows>0",
    "reasoning_repaired SFT manifest must include repaired_input_rows>0",
    "reasoning_repaired source repair repaired_rows must match repaired_input_rows",
    "reasoning_repaired SFT manifest must include replaced_rows>0",
    "reasoning_repaired source repair repaired_rows must match replaced_rows",
    "reasoning_repaired source repair manifest must include source_queue",
    "reasoning_repaired source repair source_queue must contain metadata summary keys only",
    "reasoning_repaired source repair source_queue must have metadata_only=true",
    "reasoning_repaired source repair source_queue must have privacy_scan_ok=true",
    "reasoning_repaired source repair source_queue must have safe_for_repair=true",
    "reasoning_repaired source repair source_queue must have actionable_for_repair=true",
    "reasoning_repaired source repair source_queue must have no queue_manifest_issues",
    "reasoning_repaired source repair source_queue queued must cover repaired_rows",
    "reasoning_repaired source repair source_queue target_links must be statute/action",
    "reasoning_repaired source repair core remedies metadata must be manifest-enabled",
    "reasoning_repaired row count must match manifest replaced_rows",
    "reasoning_repaired row count must match manifest repaired_input_rows",
    "reasoning_repaired rows must contain only expected sft_variant metadata",
    "reasoning_repaired rows must have sft_variant.replacement=true",
    "reasoning_repaired rows must include prompt_id and base_prompt_id",
    "reasoning_repaired row prompt IDs must match repair metadata",
    "reasoning_repaired rows must include reasoning_repair metadata",
    "reasoning_repaired rows must have reasoning_repair.source=reasoning_gap_queue",
    "reasoning_repaired rows must include non-empty reasoning_repair.added_links",
    "reasoning_repaired rows must use source_queue target_links for reasoning_repair.added_links",
    "reasoning_repaired rows must use known core remedies for reasoning_repair.added_core_remedies",
    "reasoning_repaired rows must not include core remedy repair metadata without a core-enabled source manifest",
    "reasoning_repaired rows must include at least one added repair item",
    "reasoning_repaired rows must contain only expected reasoning_repair metadata",
    "mixed DPO variant source_manifests must contain base_dpo and contract_dpo only",
    "mixed DPO variant manifest must include base_dpo source manifest summary",
    "mixed DPO base source manifest must contain metadata summary keys only",
    "mixed DPO variant manifest base_rows must be an integer",
    "mixed DPO base source dpo_train must match base_rows",
    "mixed DPO variant manifest must include contract_dpo source manifest summary",
    "mixed DPO contract source manifest must contain metadata summary keys only",
    "mixed DPO contract source manifest must have safe_to_train=true",
    "mixed DPO contract source manifest must have no pair_integrity_issues",
    "mixed DPO contract source manifest must have no contract_manifest_issues",
    "mixed DPO contract source pairs must match contract_rows",
    "mixed DPO contract source link counts must use statute/action numeric counts",
    "mixed DPO contract source link counts must be numeric",
    "mixed DPO contract source link counts must match contract_rows",
    "mixed DPO contract source manifest must have duplicate_output_pair_rows=0",
    "mixed DPO rows must include dpo_variant metadata",
    "mixed DPO row dpo_variant names must be base_plus_contract",
    "mixed DPO row dpo_variant components must be base or contract",
    "mixed DPO row base components must match manifest base_rows",
    "mixed DPO row contract components must match manifest contract_rows",
    "mixed DPO contract_ablation rows must be tagged as contract component",
    "mixed DPO contract component rows must have source=contract_ablation",
    "mixed DPO contract component rows must include ablated_link",
    "mixed DPO variant manifest must include by_ablated_link",
    "mixed DPO manifest by_ablated_link must use statute/action numeric counts",
    "mixed DPO manifest by_ablated_link total must match contract_rows",
    "mixed DPO manifest by_ablated_link counts must be numeric",
    "mixed DPO contract row ablated_link counts must match manifest by_ablated_link",
    "contract DPO rows must have source=contract_ablation",
    "contract DPO rows must include ablated_link",
    "contract DPO manifest must include by_ablated_link",
    "contract DPO manifest by_ablated_link must use statute/action numeric counts",
    "contract DPO manifest by_ablated_link total must match loaded rows",
    "contract DPO manifest by_ablated_link counts must be numeric",
    "contract DPO row ablated_link counts must match manifest by_ablated_link",
    "no valid SFT rows (need messages with a user + assistant turn)",
    "no valid DPO rows (need non-empty prompt/chosen/rejected)",
    "no training split -- run scripts/build_lift_training_data.py, then scripts/organize_training_data.py",
    "SFT variant rows require an adjacent manifest",
    "SFT variant rows must have exactly one variant name",
    "SFT variant manifest variant does not match loaded rows",
    "SFT variant manifest must have safe_to_train=true",
    "SFT variant manifest must have one_row_per_base_prompt=true",
    "SFT variant manifest output_rows does not match loaded SFT rows",
    "SFT variant manifest output_prompt_ids does not match loaded SFT rows",
    "SFT variant manifest output_path does not match selected SFT file",
    "reasoning_repaired SFT manifest must include source_repair_manifest",
    "SFT variant manifest must have no source_repair_manifest_issues",
    "SFT variant manifest is not safe_to_train",
    "contract-derived DPO rows require an adjacent manifest",
    "mixed DPO variant requires an adjacent manifest",
    "DPO variant manifest pairs does not match loaded DPO rows",
    "DPO variant manifest output_path does not match selected DPO file",
    "contract-derived DPO manifest must include by_ablated_link",
    "DPO variant manifest is not safe_to_train",
    "DPO variant manifest must have duplicate_output_pair_rows=0",
    "contract DPO manifest must have safe_to_train=true",
    "contract DPO manifest must have no pair_integrity_issues",
    "contract DPO manifest must have no contract_manifest_issues",
    "contract DPO manifest must include pairs>0",
    "contract DPO selected file must contain at least one pair",
    "contract DPO selected file rows must all be contract_ablation rows",
    "mixed DPO variant manifest must have safe_to_train=true",
    "mixed DPO variant manifest output_rows does not match loaded DPO rows",
    "mixed DPO variant manifest contract_rows does not match loaded DPO rows",
    "mixed DPO variant manifest base_rows + contract_rows does not match loaded DPO rows",
    "mixed DPO variant manifest must include base_rows and contract_rows",
    "mixed DPO variant manifest must have no source_manifest_issues",
}) | frozenset(
    f"{label} {suffix}"
    for label in ("contract DPO", "mixed DPO contract component")
    for suffix in _TRAINER_LABEL_ISSUE_SUFFIXES
)
_SAFE_TRAINER_ISSUE_PREFIXES = {
    "SFT variant manifest missing:": "SFT variant manifest missing",
    "SFT variant manifest invalid:": "SFT variant manifest invalid",
    "DPO variant manifest missing:": "DPO variant manifest missing",
    "DPO variant manifest invalid:": "DPO variant manifest invalid",
}
_TRAINER_SUMMARY_KEYS = (
    "ok",
    "sft_rows",
    "sft_valid",
    "sft_malformed_rows",
    "sft_variant_rows",
    "sft_variant_names",
    "dpo_rows",
    "dpo_valid",
    "dpo_malformed_rows",
    "contract_dpo_rows",
)
_SAFE_VARIANT_NAME = re.compile(r"^[A-Za-z0-9_.-]{1,80}$")
_EMAIL = re.compile(r"\b[\w.+-]+@[\w-]+\.[\w.-]+\b", re.I)
_PHONE = re.compile(r"\+?\d[\d\s().\-]{8,}\d")
_LOCAL_PATH_HINT = re.compile(r"(?i)(?:^[A-Za-z]:[\\/]|[\\/]Users[\\/]|[\\/]home[\\/]|[\\/]tmp[\\/]|\\\\|~[\\/])")
_TRAINER_MANIFEST_KEYS = {
    "path",
    "variant",
    "safe_to_train",
    "output_rows",
    "output_path",
    "output_prompt_ids",
    "one_row_per_base_prompt",
    "repaired_input_rows",
    "replaced_rows",
    "source_repair_manifest",
    "source_repair_manifest_issues",
    "require_core_remedies",
    "by_added_core_remedy",
    "pairs",
    "base_rows",
    "contract_rows",
    "by_ablated_link",
    "pair_integrity_issues",
    "contract_manifest_issues",
    "duplicate_output_pair_rows",
    "skipped_duplicate_pairs",
    "source_manifests",
    "source_manifest_issues",
    "min_steps",
}
_TRAINER_MANIFEST_BOOL_KEYS = frozenset({
    "safe_to_train",
    "one_row_per_base_prompt",
    "metadata_only",
    "privacy_scan_ok",
    "safe_for_repair",
    "actionable_for_repair",
    "require_core_remedies",
})
_TRAINER_MANIFEST_COUNT_KEYS = frozenset({
    "output_rows",
    "output_prompt_ids",
    "repaired_input_rows",
    "replaced_rows",
    "pairs",
    "base_rows",
    "contract_rows",
    "repaired_rows",
    "queued",
    "require_core_remedies",
    "dpo_train",
    "dpo_heldout",
    "seed",
    "dedup_kept_pre_split",
    "duplicate_output_pair_rows",
    "skipped_duplicate_pairs",
    "min_steps",
})
_TRAINER_MANIFEST_NUMBER_KEYS = frozenset({"heldout_fraction"})
_TRAINER_MANIFEST_ISSUE_KEYS = {
    "repair_manifest_issues",
    "queue_manifest_issues",
    "source_repair_manifest_issues",
    "pair_integrity_issues",
    "contract_manifest_issues",
    "source_manifest_issues",
}
_TRAINER_CONTRACT_LINKS = frozenset({"statute", "action"})
_TRAINER_CORE_REMEDIES = frozenset({
    "compensation_damages",
    "non_punishment",
    "unpaid_wage_recovery",
    "fee_refund",
})
_SOURCE_QUEUE_SUMMARY_KEYS = (
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
_SOURCE_REPAIR_SUMMARY_KEYS = (
    "path",
    "output_path",
    "repaired_rows",
    "safe_to_train",
    "require_core_remedies",
    "by_added_core_remedy",
    "repair_manifest_issues",
    "source_queue",
)
_BASE_DPO_SOURCE_SUMMARY_KEYS = (
    "path",
    "base_path",
    "dpo_train",
    "dpo_heldout",
    "seed",
    "heldout_fraction",
    "dedup_kept_pre_split",
)
_CONTRACT_DPO_SOURCE_SUMMARY_KEYS = (
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


def _resolve_path(raw_path: Any) -> pathlib.Path | None:
    if not raw_path:
        return None
    if str(raw_path) in _UNRESOLVABLE_PATHS:
        return None
    path = pathlib.Path(str(raw_path))
    return path if path.is_absolute() else _ROOT / path


def _record_artifacts(record: dict[str, Any]) -> dict[str, Any]:
    artifacts = record.get("artifacts")
    return artifacts if isinstance(artifacts, dict) else {}


def _artifact_path(record: dict[str, Any], key: str) -> pathlib.Path | None:
    artifacts = _record_artifacts(record)
    direct = _resolve_path(artifacts.get(key))
    if direct is not None:
        return direct
    artifact_files = artifacts.get("artifact_files") or {}
    if not isinstance(artifact_files, dict):
        return None
    entry = artifact_files.get(key)
    if isinstance(entry, dict):
        return _resolve_path(entry.get("path"))
    return None


def _report_path(path: pathlib.Path | str | None) -> str:
    return _display_artifact_path(path)


def _safe_mismatch_value(value: Any) -> Any:
    if value is None or isinstance(value, bool):
        return value
    if isinstance(value, int):
        return value if value >= 0 else "redacted"
    if isinstance(value, float) and math.isfinite(value) and value >= 0:
        return value
    return "redacted"


def _contains_sensitive_text(value: str) -> bool:
    return bool(
        _EMAIL.search(value)
        or _PHONE.search(value)
        or _LOCAL_PATH_HINT.search(value)
        or re.search(r"\b\d{9,}\b", value)
        or "\\" in value
    )


def _safe_summary_bool(value: Any) -> bool | str | None:
    if value is None:
        return None
    return value if isinstance(value, bool) else "redacted"


def _safe_summary_count(value: Any) -> int | str | None:
    if value is None:
        return None
    if isinstance(value, bool):
        return "redacted"
    if isinstance(value, int) and value >= 0:
        return value
    return "redacted"


def _safe_summary_number(value: Any) -> int | float | str | None:
    if value is None:
        return None
    if isinstance(value, bool):
        return "redacted"
    if isinstance(value, int) and value >= 0:
        return value
    if isinstance(value, float) and math.isfinite(value) and value >= 0:
        return value
    return "redacted"


def _safe_variant_name(value: Any) -> str | None:
    if value is None:
        return None
    if (
        isinstance(value, str)
        and _SAFE_VARIANT_NAME.fullmatch(value)
        and not _contains_sensitive_text(value)
    ):
        return value
    return "redacted"


def _safe_variant_names(value: Any) -> list[str]:
    if not isinstance(value, list):
        return []
    names: list[str] = []
    for item in value:
        if (
            isinstance(item, str)
            and _SAFE_VARIANT_NAME.fullmatch(item)
            and not _contains_sensitive_text(item)
        ):
            names.append(item)
    return names


def _sanitize_manifest_scalar(value: Any, *, key: str) -> Any:
    if key in _TRAINER_MANIFEST_BOOL_KEYS:
        return _safe_summary_bool(value)
    if key in _TRAINER_MANIFEST_COUNT_KEYS:
        return _safe_summary_count(value)
    if key in _TRAINER_MANIFEST_NUMBER_KEYS:
        return _safe_summary_number(value)
    if key == "variant":
        return _safe_variant_name(value)
    return _sanitize_report_paths(value, key=key)


def _sanitized_extra_keys(keys: list[Any]) -> list[str]:
    out: list[str] = []
    for idx, key in enumerate(keys, start=1):
        if isinstance(key, str) and key in _QUALITY_AUDIT_SUMMARY_ALLOWED_KEYS:
            out.append(key)
        else:
            out.append(f"additional_field_{idx}")
    return out


def _sanitize_report_paths(value: Any, *, key: str = "") -> Any:
    if isinstance(value, dict):
        return {item_key: _sanitize_report_paths(item_value, key=str(item_key))
                for item_key, item_value in value.items()}
    if isinstance(value, list):
        return [_sanitize_report_paths(item, key=key) for item in value]
    if isinstance(value, str) and (key in _PATH_REPORT_KEYS or key.endswith("_path")):
        return _report_path(value)
    return value


def _safe_trainer_issue(issue: Any) -> str:
    text = str(issue or "trainer issue")
    if text in _SAFE_TRAINER_ISSUES:
        return text
    for prefix, safe in _SAFE_TRAINER_ISSUE_PREFIXES.items():
        if text.startswith(prefix):
            return safe
    return "trainer issue redacted"


def _sanitized_manifest_issue_list(value: Any) -> list[str]:
    if not value:
        return []
    if not isinstance(value, list):
        return ["manifest issue redacted"]
    return ["manifest issue redacted" for _ in value]


def _sanitized_link_counts(value: Any) -> dict[str, int] | None:
    if not isinstance(value, dict):
        return None
    out: dict[str, int] = {}
    for key, raw in value.items():
        if key not in _TRAINER_CONTRACT_LINKS:
            continue
        try:
            out[str(key)] = int(raw)
        except (TypeError, ValueError):
            continue
    return {key: out[key] for key in sorted(out)}


def _sanitized_core_counts(value: Any) -> dict[str, int] | None:
    if not isinstance(value, dict):
        return None
    out: dict[str, int] = {}
    for key, raw in value.items():
        if key not in _TRAINER_CORE_REMEDIES:
            continue
        try:
            out[str(key)] = int(raw)
        except (TypeError, ValueError):
            continue
    return {key: out[key] for key in sorted(out)}


def _sanitized_source_queue(value: Any) -> dict[str, Any] | None:
    if not isinstance(value, dict):
        return None
    out: dict[str, Any] = {}
    for key in _SOURCE_QUEUE_SUMMARY_KEYS:
        raw = value.get(key)
        if key in _TRAINER_MANIFEST_ISSUE_KEYS:
            out[key] = _sanitized_manifest_issue_list(raw)
        elif key == "target_links" and isinstance(raw, list):
            out[key] = [link for link in raw if isinstance(link, str) and link in _TRAINER_CONTRACT_LINKS]
        elif key == "by_core_missing":
            out[key] = _sanitized_core_counts(raw)
        else:
            out[key] = _sanitize_manifest_scalar(raw, key=key)
    return out


def _sanitized_source_repair_manifest(value: Any) -> dict[str, Any] | None:
    if not isinstance(value, dict):
        return None
    out: dict[str, Any] = {}
    for key in _SOURCE_REPAIR_SUMMARY_KEYS:
        raw = value.get(key)
        if key in _TRAINER_MANIFEST_ISSUE_KEYS:
            out[key] = _sanitized_manifest_issue_list(raw)
        elif key == "source_queue":
            out[key] = _sanitized_source_queue(raw)
        elif key == "by_added_core_remedy":
            out[key] = _sanitized_core_counts(raw)
        else:
            out[key] = _sanitize_manifest_scalar(raw, key=key)
    return out


def _sanitized_source_manifest(
    value: Any,
    allowed_keys: tuple[str, ...],
) -> dict[str, Any] | None:
    if not isinstance(value, dict):
        return None
    out: dict[str, Any] = {}
    for key in allowed_keys:
        raw = value.get(key)
        if key in _TRAINER_MANIFEST_ISSUE_KEYS:
            out[key] = _sanitized_manifest_issue_list(raw)
        elif key == "by_ablated_link":
            out[key] = _sanitized_link_counts(raw)
        else:
            out[key] = _sanitize_manifest_scalar(raw, key=key)
    return out


def _sanitized_source_manifests(value: Any) -> dict[str, Any] | None:
    if not isinstance(value, dict):
        return None
    out: dict[str, Any] = {}
    base = _sanitized_source_manifest(value.get("base_dpo"), _BASE_DPO_SOURCE_SUMMARY_KEYS)
    contract = _sanitized_source_manifest(value.get("contract_dpo"), _CONTRACT_DPO_SOURCE_SUMMARY_KEYS)
    if base is not None:
        out["base_dpo"] = base
    if contract is not None:
        out["contract_dpo"] = contract
    return out


def _sanitized_trainer_manifest(value: Any) -> dict[str, Any] | None:
    if not isinstance(value, dict):
        return None
    out: dict[str, Any] = {}
    for key, raw in value.items():
        if key not in _TRAINER_MANIFEST_KEYS:
            continue
        if key in _TRAINER_MANIFEST_ISSUE_KEYS:
            out[key] = _sanitized_manifest_issue_list(raw)
        elif key == "source_repair_manifest":
            out[key] = _sanitized_source_repair_manifest(raw)
        elif key == "source_manifests":
            out[key] = _sanitized_source_manifests(raw)
        elif key == "by_ablated_link":
            out[key] = _sanitized_link_counts(raw)
        elif key == "by_added_core_remedy":
            out[key] = _sanitized_core_counts(raw)
        else:
            out[key] = _sanitize_manifest_scalar(raw, key=str(key))
    return out


def _sanitize_nested_manifest_issues(value: Any, *, key: str = "") -> Any:
    if key in _TRAINER_MANIFEST_ISSUE_KEYS:
        return _sanitized_manifest_issue_list(value)
    if isinstance(value, dict):
        return {item_key: _sanitize_nested_manifest_issues(item_value, key=str(item_key))
                for item_key, item_value in value.items()}
    if isinstance(value, list):
        return [_sanitize_nested_manifest_issues(item, key=key) for item in value]
    return value


def _sanitized_trainer_report(trainer: dict[str, Any]) -> dict[str, Any]:
    if not isinstance(trainer, dict):
        return {"ok": False, "issues": ["trainer issue redacted"]}
    out: dict[str, Any] = {}
    for key in _TRAINER_SUMMARY_KEYS:
        if key not in trainer:
            continue
        if key == "ok":
            out[key] = _safe_summary_bool(trainer.get(key))
        elif key == "sft_variant_names":
            out[key] = _safe_variant_names(trainer.get(key))
        else:
            out[key] = _safe_summary_count(trainer.get(key))
    for manifest_key in ("sft_manifest", "dpo_manifest"):
        manifest = _sanitized_trainer_manifest(trainer.get(manifest_key))
        if manifest is not None:
            out[manifest_key] = _sanitize_nested_manifest_issues(manifest)
    out["issues"] = [_safe_trainer_issue(issue) for issue in trainer.get("issues") or []]
    if trainer.get("ok") is False and not out["issues"]:
        out["issues"] = ["trainer issue redacted"]
    return out


def _model_card_check(record: dict[str, Any], registry_check: dict[str, Any]) -> dict[str, Any]:
    if registry_check.get("legacy_without_artifact_files"):
        return {"ok": False, "issue": "registry row has no structured artifact_files payload"}
    if registry_check.get("checked", 0) == 0:
        return {"ok": False, "issue": "registry row has no materialized artifact fingerprints"}
    if not registry_check.get("ok"):
        return {"ok": False, "issue": "registry artifact verification failed"}
    card = render_card(record)
    has_artifact_fingerprints = "## Artifact fingerprints" in card
    if card.strip() and not has_artifact_fingerprints:
        return {"ok": False, "issue": "model card is missing artifact fingerprints section"}
    return {
        "ok": bool(card.strip()),
        "chars": len(card),
        "has_artifact_fingerprints": has_artifact_fingerprints,
    }


def _quality_audit_check(record: dict[str, Any]) -> dict[str, Any]:
    artifacts = _record_artifacts(record)
    audit_path = _artifact_path(record, "quality_audit") or _artifact_path(record, "quality_audit_path")
    summary = artifacts.get("quality_audit_summary")
    if audit_path is None and summary is None:
        return {"ok": True, "available": False}
    if audit_path is None:
        return {"ok": False, "available": False, "issue": "quality_audit_summary recorded without quality_audit artifact"}
    expected = _quality_audit_summary_from_file(audit_path)
    if expected is None:
        return {"ok": False, "available": True, "path": _report_path(audit_path),
                "issue": "quality_audit unreadable or invalid"}
    if not isinstance(summary, dict):
        return {"ok": False, "available": True, "path": _report_path(audit_path),
                "issue": "quality_audit_summary missing or malformed"}
    extra_keys = sorted(str(key) for key in summary if key not in _QUALITY_AUDIT_SUMMARY_ALLOWED_KEYS)
    if extra_keys:
        return {"ok": False, "available": True, "path": _report_path(audit_path),
                "issue": "quality_audit_summary contains non-metadata keys",
                "extra_keys": _sanitized_extra_keys(extra_keys)}
    mismatches: dict[str, dict[str, Any]] = {}
    for field in QUALITY_AUDIT_SUMMARY_FIELDS:
        if summary.get(field) != expected.get(field):
            if field == "risk_flags":
                expected_flags = expected.get(field) if isinstance(expected.get(field), list) else []
                recorded_flags = summary.get(field) if isinstance(summary.get(field), list) else []
                mismatches[field] = {
                    "expected_count": len(expected_flags),
                    "recorded_count": len(recorded_flags),
                }
            else:
                mismatches[field] = {
                    "expected": _safe_mismatch_value(expected.get(field)),
                    "recorded": _safe_mismatch_value(summary.get(field)),
                }
    if mismatches:
        return {"ok": False, "available": True, "path": _report_path(audit_path),
                "issue": "quality_audit_summary does not match quality_audit artifact",
                "mismatches": mismatches}
    safe_summary = {field: expected.get(field) for field in QUALITY_AUDIT_SUMMARY_FIELDS}
    if expected.get("clean") is not True:
        return {
            "ok": False,
            "available": True,
            "path": _report_path(audit_path),
            "issue": "quality_audit is not clean",
            "summary": safe_summary,
        }
    return {"ok": True, "available": True, "path": _report_path(audit_path),
            "summary": safe_summary}


def _file_sha256(path: pathlib.Path | None) -> str | None:
    if path is None:
        return None
    try:
        return hashlib.sha256(path.read_bytes()).hexdigest()
    except OSError:
        return None


def _load_json_object(path: pathlib.Path) -> dict[str, Any] | None:
    try:
        payload = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError):
        return None
    return payload if isinstance(payload, dict) else None


def _corridor_plan_privacy_scan(plan: Any, batches: Any) -> dict[str, Any]:
    findings: dict[str, list[str]] = {
        "forbidden_field_paths": [],
        "email_like_paths": [],
        "phone_like_paths": [],
        "long_digit_paths": [],
        "local_path_like_paths": [],
    }

    def walk(value: Any, path: str) -> None:
        if isinstance(value, dict):
            for key, item in value.items():
                key_path = f"{path}.{key}"
                if str(key) in _CORRIDOR_PLAN_FORBIDDEN_FIELDS:
                    findings["forbidden_field_paths"].append(key_path)
                walk(item, key_path)
        elif isinstance(value, list):
            for idx, item in enumerate(value):
                walk(item, f"{path}[{idx}]")
        elif isinstance(value, str):
            field = path.rsplit(".", 1)[-1]
            if field.endswith("sha256"):
                return
            if _EMAIL.search(value):
                findings["email_like_paths"].append(path)
            if _PHONE.search(value):
                findings["phone_like_paths"].append(path)
            if re.search(r"\b\d{9,}\b", value):
                findings["long_digit_paths"].append(path)
            if _LOCAL_PATH_HINT.search(value) or "\\" in value:
                findings["local_path_like_paths"].append(path)

    walk({"plan": plan, "batches": batches}, "$")
    counts = {key.replace("_paths", ""): len(paths) for key, paths in findings.items()}
    findings["counts"] = counts
    findings["ok"] = not any(counts.values())
    return findings


def _nonnegative_int(value: Any) -> int | None:
    if isinstance(value, bool):
        return None
    return value if isinstance(value, int) and value >= 0 else None


def _corridor_expansion_plan_check(record: dict[str, Any], quality_audit: dict[str, Any]) -> dict[str, Any]:
    plan_path = (
        _artifact_path(record, "corridor_expansion_plan")
        or _artifact_path(record, "corridor_expansion_plan_path")
    )
    manifest_path = _artifact_path(record, "corridor_expansion_plan_manifest")
    if plan_path is None and manifest_path is None:
        return {"ok": True, "available": False}
    if plan_path is None:
        return {"ok": False, "available": False, "issue": "corridor_expansion_plan_manifest recorded without plan"}
    if manifest_path is None:
        return {"ok": False, "available": True, "path": _report_path(plan_path),
                "issue": "corridor_expansion_plan_manifest missing"}

    plan_doc = _load_json_object(plan_path)
    side_manifest = _load_json_object(manifest_path)
    if plan_doc is None:
        return {"ok": False, "available": True, "path": _report_path(plan_path),
                "manifest_path": _report_path(manifest_path),
                "issue": "corridor_expansion_plan unreadable or invalid"}
    if side_manifest is None:
        return {"ok": False, "available": True, "path": _report_path(plan_path),
                "manifest_path": _report_path(manifest_path),
                "issue": "corridor_expansion_plan_manifest unreadable or invalid"}

    embedded_manifest = plan_doc.get("manifest")
    plan = plan_doc.get("plan")
    batches = plan_doc.get("batches")
    issues: list[str] = []
    if not isinstance(embedded_manifest, dict):
        issues.append("corridor_expansion_plan_embedded_manifest_missing")
        embedded_manifest = {}
    if embedded_manifest != side_manifest:
        issues.append("corridor_expansion_plan_side_manifest_mismatch")
    manifest = side_manifest
    missing_fields = sorted(field for field in _CORRIDOR_PLAN_REQUIRED_MANIFEST_FIELDS if field not in manifest)
    if missing_fields:
        issues.append("corridor_expansion_plan_manifest_fields_missing")
    if not isinstance(plan, list):
        issues.append("corridor_expansion_plan_entries_not_list")
        plan = []
    if not isinstance(batches, list):
        issues.append("corridor_expansion_plan_batches_not_list")
        batches = []

    privacy_scan = _corridor_plan_privacy_scan(plan, batches)
    if privacy_scan.get("ok") is not True:
        issues.append("corridor_expansion_plan_privacy_scan_not_ok")
    recorded_scan = manifest.get("privacy_scan") if isinstance(manifest.get("privacy_scan"), dict) else {}
    if recorded_scan.get("ok") is not True:
        issues.append("corridor_expansion_plan_recorded_privacy_scan_not_ok")
    if manifest.get("metadata_only") is not True:
        issues.append("corridor_expansion_plan_metadata_only_not_true")
    if manifest.get("source_privacy_ok") is not True:
        issues.append("corridor_expansion_plan_source_privacy_not_ok")
    if manifest.get("safe_for_curation") is not True:
        issues.append("corridor_expansion_plan_safe_for_curation_not_true")
    if manifest.get("plan_manifest_issues") not in ([], None):
        issues.append("corridor_expansion_plan_manifest_issues_present")

    planned = _nonnegative_int(manifest.get("planned_task_count"))
    if planned is None or planned != len(plan):
        issues.append("corridor_expansion_plan_task_count_mismatch")
    batch_count = _nonnegative_int(manifest.get("batch_count"))
    if batch_count is None or batch_count != len(batches):
        issues.append("corridor_expansion_plan_batch_count_mismatch")
    recommended = _nonnegative_int(manifest.get("recommended_rows"))
    actual_recommended = 0
    for entry in plan:
        if isinstance(entry, dict):
            value = _nonnegative_int(entry.get("recommended_rows"))
            if value is not None:
                actual_recommended += value
    if recommended is None or recommended != actual_recommended:
        issues.append("corridor_expansion_plan_recommended_rows_mismatch")

    output_path = manifest.get("output_path")
    if output_path is not None and output_path != _report_path(plan_path):
        issues.append("corridor_expansion_plan_output_path_mismatch")
    recorded_manifest_path = manifest.get("manifest_path")
    if recorded_manifest_path is not None and recorded_manifest_path != _report_path(manifest_path):
        issues.append("corridor_expansion_plan_manifest_path_mismatch")

    audit_summary = (quality_audit.get("summary") if isinstance(quality_audit, dict) else {}) or {}
    expected_tasks = audit_summary.get("corridor_expansion_task_count")
    if isinstance(expected_tasks, int) and manifest.get("source_task_count") != expected_tasks:
        issues.append("corridor_expansion_plan_source_task_count_mismatch")
    audit_path = _artifact_path(record, "quality_audit") or _artifact_path(record, "quality_audit_path")
    audit_sha = _file_sha256(audit_path)
    if audit_sha and manifest.get("source_audit_sha256") != audit_sha:
        issues.append("corridor_expansion_plan_source_audit_sha_mismatch")

    summary = {
        "planned_task_count": _safe_summary_count(manifest.get("planned_task_count")),
        "batch_count": _safe_summary_count(manifest.get("batch_count")),
        "recommended_rows": _safe_summary_count(manifest.get("recommended_rows")),
        "safe_for_curation": _safe_summary_bool(manifest.get("safe_for_curation")),
        "actionable_for_curation": _safe_summary_bool(manifest.get("actionable_for_curation")),
        "privacy_ok": privacy_scan.get("ok") is True and recorded_scan.get("ok") is True,
    }
    base = {
        "available": True,
        "path": _report_path(plan_path),
        "manifest_path": _report_path(manifest_path),
        "summary": summary,
    }
    if issues:
        return {
            "ok": False,
            **base,
            "issue": "corridor_expansion_plan manifest does not match generated artifacts",
            "manifest_issues": sorted(set(issues)),
        }
    return {"ok": True, **base}


def _sanitized_registry_check(registry_check: dict[str, Any]) -> dict[str, Any]:
    allowed = {
        "model_id",
        "created_utc",
        "status",
        "checked",
        "matched",
        "pending",
        "legacy_without_artifact_files",
        "ok",
    }
    out = {key: registry_check.get(key) for key in allowed if key in registry_check}
    if "model_id" in out:
        out["model_id"] = _display_model_id(out["model_id"])
    out["issues"] = _sanitized_artifact_issues(registry_check.get("issues") or [])
    return out


def validate_training_provenance(
    *,
    model_id: str = DEFAULT_MODEL_ID,
    registry: pathlib.Path = REGISTRY,
    sft: pathlib.Path | None = None,
    dpo: pathlib.Path | None = None,
) -> dict[str, Any]:
    records = load_registry(registry)
    record = latest_by_id(records).get(model_id)
    display_model_id = _display_model_id(model_id)
    report: dict[str, Any] = {
        "model_id": display_model_id,
        "registry_path": _report_path(registry),
        "ok": False,
        "issues": [],
    }
    if not record:
        report["issues"].append(f"no registry record for {display_model_id}")
        return report

    registry_check = verify_record_artifacts(record)
    report["registry"] = _sanitized_registry_check(registry_check)
    if registry_check.get("legacy_without_artifact_files"):
        report["issues"].append("registry row has no structured artifact_files payload")
    if registry_check.get("checked", 0) == 0:
        report["issues"].append("registry row has no materialized artifact fingerprints")
    for issue in report["registry"].get("issues") or []:
        report["issues"].append(f"registry artifact {issue.get('artifact')}: {issue.get('issue')}")

    card_check = _model_card_check(record, registry_check)
    report["model_card"] = card_check
    if not card_check.get("ok"):
        report["issues"].append(f"model card: {card_check.get('issue', 'render failed')}")

    audit_check = _quality_audit_check(record)
    report["quality_audit"] = audit_check
    if not audit_check.get("ok"):
        report["issues"].append(f"quality audit: {audit_check.get('issue', 'verification failed')}")

    corridor_check = _corridor_expansion_plan_check(record, audit_check)
    report["corridor_expansion_plan"] = corridor_check
    if not corridor_check.get("ok"):
        report["issues"].append(
            f"corridor expansion plan: {corridor_check.get('issue', 'verification failed')}"
        )

    sft_path = sft or _artifact_path(record, "selected_sft") or _artifact_path(record, "sft_path") or SFT_DEFAULT
    dpo_path = dpo or _artifact_path(record, "selected_dpo") or _artifact_path(record, "dpo_path") or DPO_DEFAULT
    report["selected_training_files"] = {"sft": _report_path(sft_path), "dpo": _report_path(dpo_path)}
    trainer = validate_training_data(
        load_jsonl(sft_path),
        load_jsonl(dpo_path),
        sft_manifest=load_sft_manifest(sft_path),
        dpo_manifest=load_dpo_manifest(dpo_path),
        sft_path=sft_path,
        dpo_path=dpo_path,
    )
    report["trainer"] = _sanitized_trainer_report(trainer)
    for issue in report["trainer"].get("issues") or []:
        report["issues"].append(f"trainer: {issue}")

    report["ok"] = not report["issues"]
    return report


def _print_human(report: dict[str, Any]) -> None:
    state = "OK" if report.get("ok") else "FAIL"
    print(f"[training-provenance] {state} {report.get('model_id')}")
    registry = report.get("registry") or {}
    if registry:
        print(f"  registry: checked={registry.get('checked')} matched={registry.get('matched')} "
              f"pending={registry.get('pending')}")
    trainer = report.get("trainer") or {}
    if trainer:
        print(f"  trainer: sft={trainer.get('sft_valid')}/{trainer.get('sft_rows')} "
              f"dpo={trainer.get('dpo_valid')}/{trainer.get('dpo_rows')}")
    card = report.get("model_card") or {}
    if card:
        print(f"  model_card: ok={card.get('ok')} chars={card.get('chars', 0)}")
    audit = report.get("quality_audit") or {}
    if audit:
        summary = audit.get("summary") or {}
        print(f"  quality_audit: ok={audit.get('ok')} available={audit.get('available')} "
              f"dense_single_corridor={summary.get('dense_single_corridor_typologies')} "
              f"corridor_queue={summary.get('corridor_expansion_queue_count')}")
    corridor = report.get("corridor_expansion_plan") or {}
    if corridor:
        summary = corridor.get("summary") or {}
        print(f"  corridor_expansion_plan: ok={corridor.get('ok')} available={corridor.get('available')} "
              f"tasks={summary.get('planned_task_count')} batches={summary.get('batch_count')}")
    for issue in report.get("issues") or []:
        print(f"  - {issue}")


def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--model-id", default=DEFAULT_MODEL_ID)
    ap.add_argument("--registry", type=pathlib.Path, default=REGISTRY)
    ap.add_argument("--sft", type=pathlib.Path, default=None, help="override selected SFT file")
    ap.add_argument("--dpo", type=pathlib.Path, default=None, help="override selected DPO file")
    ap.add_argument("--json", action="store_true", help="print machine-readable JSON")
    args = ap.parse_args(argv)

    report = validate_training_provenance(
        model_id=args.model_id,
        registry=args.registry,
        sft=args.sft,
        dpo=args.dpo,
    )
    if args.json:
        print(json.dumps(report, indent=2))
    else:
        _print_human(report)
    return 0 if report["ok"] else 1


if __name__ == "__main__":
    raise SystemExit(main())
