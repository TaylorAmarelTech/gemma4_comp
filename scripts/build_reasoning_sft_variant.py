#!/usr/bin/env python3
"""Build an explicit SFT training variant that uses verified reasoning repairs.

The repaired rows from build_reasoning_repairs.py are proposed training examples. This script stages them
as a separate, non-destructive SFT arm:

  base train split: reports/training/sft_train.jsonl
  repaired rows:    reports/training/reasoning_repaired_sft.jsonl
  output variant:   reports/training/sft_train_reasoning_repaired.jsonl

It REPLACES matching prompt_id rows in the base train split instead of appending duplicates. The manifest
checks that the output still has one assistant target per prompt while letting the GPU window compare:

  base SFT:               --sft reports/training/sft_train.jsonl
  reasoning-repaired SFT: --sft reports/training/sft_train_reasoning_repaired.jsonl

Propose-only. The base split is never mutated; all outputs are gitignored reports/training artifacts.
"""
from __future__ import annotations

import argparse
import json
import pathlib
import re
import sys
from collections import Counter
from typing import Any

_ROOT = pathlib.Path(__file__).resolve().parents[1]
sys.path.insert(0, str(pathlib.Path(__file__).resolve().parent))

from build_reasoning_targets import _load_jsonl, _meta_dict  # noqa: E402
from remedy_taxonomy import CORE_BASE_REMEDIES, CORE_TRIGGER_REMEDIES  # noqa: E402
from reasoning_contract import STEPS  # noqa: E402

TRAIN_DIR = _ROOT / "reports" / "training"
SFT_TRAIN = TRAIN_DIR / "sft_train.jsonl"
REPAIRED = TRAIN_DIR / "reasoning_repaired_sft.jsonl"
OUT = TRAIN_DIR / "sft_train_reasoning_repaired.jsonl"
_EMAIL = re.compile(r"\b[\w.+-]+@[\w-]+\.[\w.-]+\b", re.I)
_PHONE = re.compile(r"\+?\d[\d\s().\-]{8,}\d")
_LOCAL_PATH_HINT = re.compile(
    r"(?:[A-Za-z]:[\\/]|\\\\|(?:^|[\s\"'(:])/(?:Users|home|tmp|var|mnt|private|Volumes)(?:/|$)|~[\\/])",
    re.I,
)
_SAFE_RELATIVE_PATH = re.compile(r"^[A-Za-z0-9._/\-]+$")
_SAFE_IDENTIFIER = re.compile(r"^[A-Za-z0-9 ._:/#-]{1,180}$")
_SAFE_LABEL = re.compile(r"^[A-Za-z0-9 ._:/#-]{1,120}$")
_LONG_DIGITS = re.compile(r"(?<!\d)\d{8,}(?!\d)")
_CASE_LIKE_PROMPT_ID = re.compile(
    r"\b(?:case|claim|complaint|contact|docket|file|passport|person|phone|worker)[ ._:/#-]*\d{8,}\b"
    r"|\b\d{8,}[ ._:/#-]*(?:case|claim|complaint|contact|docket|file|passport|person|phone|worker)\b",
    re.I,
)
_PATH_REPORT_KEYS = frozenset({"path", "output_path", "manifest_path", "sft", "repaired", "out"})


def manifest_path_for(out_path: pathlib.Path) -> pathlib.Path:
    return out_path.with_name(f"{out_path.stem}_manifest.json")


MANIFEST = manifest_path_for(OUT)


def _has_sensitive_display_text(text: str) -> bool:
    return bool(
        _EMAIL.search(text)
        or _PHONE.search(text)
        or _LOCAL_PATH_HINT.search(text)
        or _LONG_DIGITS.search(text)
    )


def _safe_relative_report_path(path: pathlib.PurePath) -> str:
    display = path.as_posix()
    if not display or display.startswith("../") or "/../" in display:
        return "redacted"
    if _has_sensitive_display_text(display):
        return "redacted"
    if not _SAFE_RELATIVE_PATH.fullmatch(display):
        return "redacted"
    return display


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


def _safe_prompt_id(value: Any) -> str:
    if not isinstance(value, str):
        return ""
    text = value.strip()
    if (
        text
        and _SAFE_IDENTIFIER.fullmatch(text)
        and not _EMAIL.search(text)
        and not _LOCAL_PATH_HINT.search(text)
        and not _CASE_LIKE_PROMPT_ID.search(text)
    ):
        return text
    return ""


def _safe_category(value: Any) -> str:
    if not isinstance(value, str):
        return "unknown"
    text = value.strip()
    if text and _SAFE_LABEL.fullmatch(text) and not _has_sensitive_display_text(text):
        return text
    return "unknown"


def _display_manifest(value: Any, *, key: str = "") -> Any:
    if isinstance(value, dict):
        return {item_key: _display_manifest(item_value, key=str(item_key))
                for item_key, item_value in value.items()}
    if isinstance(value, list):
        return [_display_manifest(item, key=key) for item in value]
    if isinstance(value, str) and (key in _PATH_REPORT_KEYS or key.endswith("_path")):
        return _display_report_path(value)
    if isinstance(value, str) and _has_sensitive_display_text(value):
        return "redacted"
    return value


_SOURCE_QUEUE_SUMMARY_FIELDS = (
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
_REPAIR_META_FIELDS = (
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
_REPAIR_STEP_LIST_FIELDS = (
    "added_links",
    "original_missing_links",
    "original_target_missing_links",
)
_REPAIR_CORE_LIST_FIELDS = (
    "added_core_remedies",
    "original_target_core_missing",
)
_VALID_REPAIR_LINKS = set(STEPS)
_VALID_CORE_REMEDIES = set(CORE_BASE_REMEDIES) | {
    remedy for remedies in CORE_TRIGGER_REMEDIES.values() for remedy in remedies
}


def _same_path(a: Any, b: pathlib.Path | str | None) -> bool:
    if not a or b is None:
        return False
    display_b = _display_report_path(b)
    if a == display_b and display_b not in {"redacted", "n/a"}:
        return True
    try:
        return pathlib.Path(str(a)).resolve() == pathlib.Path(str(b)).resolve()
    except OSError:
        return pathlib.Path(str(a)) == pathlib.Path(str(b))


def _valid_count_map(value: Any, allowed_keys: set[str]) -> dict[str, int] | None:
    if not isinstance(value, dict):
        return None
    out: dict[str, int] = {}
    for key, raw in value.items():
        if not isinstance(key, str) or key not in allowed_keys:
            continue
        try:
            count = int(raw)
        except (TypeError, ValueError):
            continue
        if count >= 0:
            out[key] = count
    return {key: out[key] for key in sorted(out)}


def _source_queue_summary(source_queue: Any) -> dict[str, Any]:
    if not isinstance(source_queue, dict):
        return {field: None for field in _SOURCE_QUEUE_SUMMARY_FIELDS}
    out = {field: source_queue.get(field) for field in _SOURCE_QUEUE_SUMMARY_FIELDS}
    target_links = source_queue.get("target_links")
    if isinstance(target_links, list):
        out["target_links"] = [link for link in target_links if isinstance(link, str) and link in _VALID_REPAIR_LINKS]
    out["by_core_missing"] = _valid_count_map(source_queue.get("by_core_missing"), _VALID_CORE_REMEDIES)
    return out


def _source_queue_extra_keys(source_queue: Any) -> list[str]:
    if not isinstance(source_queue, dict):
        return []
    allowed = set(_SOURCE_QUEUE_SUMMARY_FIELDS)
    return sorted(str(key) for key in source_queue if key not in allowed)


def _repair_meta_extra_keys(repair: Any) -> list[str]:
    if not isinstance(repair, dict):
        return []
    allowed = set(_REPAIR_META_FIELDS)
    return sorted(str(key) for key in repair if key not in allowed)


def _valid_step_links(value: Any) -> list[str]:
    if not isinstance(value, list):
        return []
    return [link for link in value if isinstance(link, str) and link in _VALID_REPAIR_LINKS]


def _valid_core_remedies(value: Any) -> list[str]:
    if not isinstance(value, list):
        return []
    return [remedy for remedy in value if isinstance(remedy, str) and remedy in _VALID_CORE_REMEDIES]


def _invalid_step_list(value: Any, *, require_non_empty: bool = False) -> bool:
    if not isinstance(value, list):
        return True
    if require_non_empty and not value:
        return True
    return any(not isinstance(link, str) or link not in _VALID_REPAIR_LINKS for link in value)


def _invalid_core_list(value: Any, *, require_non_empty: bool = False) -> bool:
    if not isinstance(value, list):
        return True
    if require_non_empty and not value:
        return True
    return any(not isinstance(remedy, str) or remedy not in _VALID_CORE_REMEDIES for remedy in value)


def _invalid_chain_links(value: Any) -> bool:
    if not isinstance(value, dict):
        return True
    if set(value) != _VALID_REPAIR_LINKS:
        return True
    return any(not isinstance(value.get(step), bool) for step in STEPS)


def _sanitized_chain_links(value: Any) -> dict[str, bool]:
    if not isinstance(value, dict):
        return {}
    return {step: bool(value[step]) for step in STEPS if step in value and isinstance(value[step], bool)}


def _sanitized_repair_meta(repair: Any) -> dict[str, Any]:
    if not isinstance(repair, dict):
        return {}
    out: dict[str, Any] = {}
    for field in _REPAIR_META_FIELDS:
        if field not in repair:
            continue
        if field in _REPAIR_STEP_LIST_FIELDS:
            out[field] = _valid_step_links(repair.get(field))
        elif field in _REPAIR_CORE_LIST_FIELDS:
            out[field] = _valid_core_remedies(repair.get(field))
        elif field == "repaired_chain_links":
            out[field] = _sanitized_chain_links(repair.get(field))
        elif field == "source":
            out[field] = "reasoning_gap_queue" if repair.get(field) == "reasoning_gap_queue" else "redacted"
        elif field == "original_prompt_id":
            out[field] = _safe_prompt_id(repair.get(field))
        elif field == "category":
            out[field] = _safe_category(repair.get(field))
        elif field == "repaired_n_steps":
            value = repair.get(field)
            out[field] = value if isinstance(value, int) and not isinstance(value, bool) and value >= 0 else None
        elif field == "selected_convention":
            value = repair.get(field)
            out[field] = value if isinstance(value, int) and not isinstance(value, bool) and value > 0 else None
        else:
            out[field] = repair.get(field)
    return out


def load_repair_manifest(repaired_path: pathlib.Path) -> dict[str, Any]:
    """Load the metadata manifest emitted beside build_reasoning_repairs.py output."""
    manifest_path = manifest_path_for(repaired_path)
    if not manifest_path.exists():
        return {"path": str(manifest_path), "missing": True}
    try:
        doc = json.loads(manifest_path.read_text(encoding="utf-8"))
    except json.JSONDecodeError as exc:
        return {"path": str(manifest_path), "error": f"invalid JSON: {exc}"}
    if isinstance(doc, dict):
        doc["path"] = str(manifest_path)
        return doc
    return {"path": str(manifest_path), "error": "manifest root is not an object"}


def _repair_manifest_issues(
    manifest: dict[str, Any] | None,
    *,
    repaired_rows: list[dict[str, Any]],
    repaired_path: pathlib.Path | None = None,
) -> list[str]:
    """Fail-closed checks proving repaired rows came from the verified repair builder."""
    if manifest is None:
        return []
    if manifest.get("missing"):
        return ["reasoning_repair_manifest_missing"]
    if manifest.get("error"):
        return ["reasoning_repair_manifest_invalid"]

    issues: list[str] = []
    if manifest.get("safe_to_train") is not True:
        issues.append("reasoning_repair_manifest_not_safe")
    if manifest.get("repair_manifest_issues"):
        issues.append("reasoning_repair_manifest_issues_present")
    if manifest.get("metadata_only") is not True:
        issues.append("reasoning_repair_manifest_metadata_only_not_true")
    if manifest.get("repaired_rows") != len(repaired_rows):
        issues.append("reasoning_repair_manifest_repaired_rows_mismatch")
    if repaired_path is not None and not _same_path(manifest.get("output_path"), repaired_path):
        issues.append("reasoning_repair_manifest_output_path_mismatch")
    if manifest.get("source_queue_issues"):
        issues.append("reasoning_repair_manifest_source_queue_issues")
    source_queue = manifest.get("source_queue") or {}
    if _source_queue_extra_keys(source_queue):
        issues.append("reasoning_repair_manifest_source_queue_non_metadata_keys")
    if source_queue.get("metadata_only") is not True:
        issues.append("reasoning_repair_manifest_source_queue_metadata_only_not_true")
    if source_queue.get("privacy_scan_ok") is not True:
        issues.append("reasoning_repair_manifest_source_queue_privacy_scan_not_ok")
    if source_queue.get("safe_for_repair") is not True:
        issues.append("reasoning_repair_manifest_source_queue_not_safe_for_repair")
    if source_queue.get("actionable_for_repair") is not True:
        issues.append("reasoning_repair_manifest_source_queue_not_actionable_for_repair")
    if source_queue.get("queue_manifest_issues"):
        issues.append("reasoning_repair_manifest_source_queue_manifest_issues")
    if manifest.get("require_core_remedies") is True and source_queue.get("require_core_remedies") is not True:
        issues.append("reasoning_repair_manifest_core_remedies_mismatch")
    if source_queue.get("require_core_remedies") is True and manifest.get("require_core_remedies") is not True:
        issues.append("reasoning_repair_manifest_core_remedies_mismatch")
    return issues


def _prompt_id(row: dict[str, Any]) -> str:
    return _safe_prompt_id(_meta_dict(row).get("prompt_id"))


def _prompt_id_stats(rows: list[dict[str, Any]]) -> tuple[Counter[str], int, int]:
    counts: Counter[str] = Counter()
    missing = 0
    for row in rows:
        pid = _prompt_id(row)
        if pid:
            counts[pid] += 1
        else:
            missing += 1
    duplicate_rows = sum(n - 1 for n in counts.values() if n > 1)
    return counts, missing, duplicate_rows


def _core_remedy_repairs_enabled(repair_manifest: dict[str, Any] | None) -> bool:
    if not isinstance(repair_manifest, dict):
        return False
    source_queue = repair_manifest.get("source_queue")
    return (
        repair_manifest.get("require_core_remedies") is True
        and isinstance(source_queue, dict)
        and source_queue.get("require_core_remedies") is True
    )


def _repair_row_metadata(
    rows: list[dict[str, Any]],
    *,
    allow_core_remedies: bool = False,
) -> tuple[dict[str, int], list[str]]:
    """Return metadata-only counts and fail-closed issue codes for repaired input rows."""
    counts: Counter[str] = Counter()
    for row in rows:
        meta = _meta_dict(row)
        pid = _prompt_id(row)
        repair = meta.get("reasoning_repair")
        if not isinstance(repair, dict):
            counts["missing_reasoning_repair"] += 1
            continue
        if _repair_meta_extra_keys(repair):
            counts["unexpected_reasoning_repair_keys"] += 1
        if repair.get("source") != "reasoning_gap_queue":
            counts["wrong_repair_source"] += 1
        original_prompt_id = _safe_prompt_id(repair.get("original_prompt_id"))
        if pid and original_prompt_id and original_prompt_id != pid:
            counts["prompt_id_mismatch"] += 1
        elif not original_prompt_id:
            counts["missing_original_prompt_id"] += 1
        added_links = repair.get("added_links")
        added_core = repair.get("added_core_remedies")
        has_valid_links = isinstance(added_links, list) and bool(added_links) and not _invalid_step_list(
            added_links,
            require_non_empty=True,
        )
        has_valid_core = isinstance(added_core, list) and bool(added_core) and not _invalid_core_list(
            added_core,
            require_non_empty=True,
        )
        if not isinstance(added_links, list):
            counts["missing_added_links"] += 1
        elif added_links and _invalid_step_list(added_links, require_non_empty=True):
            counts["invalid_added_links"] += 1
        elif not added_links and not (allow_core_remedies and has_valid_core):
            counts["missing_added_links"] += 1
        if (added_core is not None or "original_target_core_missing" in repair) and not allow_core_remedies:
            counts["core_remedy_metadata_without_core_manifest"] += 1
        if added_core is not None:
            if _invalid_core_list(added_core, require_non_empty=False):
                counts["invalid_added_core_remedies"] += 1
        if "original_target_core_missing" in repair and _invalid_core_list(
            repair.get("original_target_core_missing"),
            require_non_empty=False,
        ):
            counts["invalid_original_target_core_missing"] += 1
        if not has_valid_links and not has_valid_core:
            counts["missing_added_repair_items"] += 1
        for field in ("original_missing_links", "original_target_missing_links"):
            if field in repair and _invalid_step_list(repair.get(field)):
                counts[f"invalid_{field}"] += 1
        if "repaired_chain_links" in repair and _invalid_chain_links(repair.get("repaired_chain_links")):
            counts["invalid_repaired_chain_links"] += 1

    issue_map = {
        "invalid_added_links": "repaired_row_invalid_added_links",
        "invalid_added_core_remedies": "repaired_row_invalid_added_core_remedies",
        "invalid_original_missing_links": "repaired_row_invalid_original_missing_links",
        "invalid_original_target_missing_links": "repaired_row_invalid_original_target_missing_links",
        "invalid_original_target_core_missing": "repaired_row_invalid_original_target_core_missing",
        "invalid_repaired_chain_links": "repaired_row_invalid_repaired_chain_links",
        "missing_reasoning_repair": "repaired_row_missing_reasoning_repair",
        "wrong_repair_source": "repaired_row_wrong_repair_source",
        "prompt_id_mismatch": "repaired_row_prompt_id_mismatch",
        "missing_original_prompt_id": "repaired_row_missing_original_prompt_id",
        "missing_added_links": "repaired_row_missing_added_links",
        "missing_added_repair_items": "repaired_row_missing_added_repair_items",
        "core_remedy_metadata_without_core_manifest": "repaired_row_core_remedy_metadata_without_core_manifest",
        "unexpected_reasoning_repair_keys": "repaired_row_reasoning_repair_unexpected_keys",
    }
    issues = [issue_map[key] for key in sorted(issue_map) if counts[key]]
    return {key: counts[key] for key in sorted(counts)}, issues


def build_variant(
    base_rows: list[dict[str, Any]],
    repaired_rows: list[dict[str, Any]],
    *,
    output_path: pathlib.Path = OUT,
    repair_manifest: dict[str, Any] | None = None,
    repair_manifest_issues: list[str] | None = None,
    repaired_path: pathlib.Path | None = None,
) -> dict[str, Any]:
    """Return {"rows", "manifest"} for a same-size SFT variant with repairs replacing base rows."""
    source_repair_issues = repair_manifest_issues
    if source_repair_issues is None:
        source_repair_issues = _repair_manifest_issues(
            repair_manifest,
            repaired_rows=repaired_rows,
            repaired_path=repaired_path,
    )
    base_counts, base_missing, base_duplicate_rows = _prompt_id_stats(base_rows)
    repaired_counts, repaired_missing, repaired_duplicate_rows = _prompt_id_stats(repaired_rows)
    allow_core_remedies = _core_remedy_repairs_enabled(repair_manifest)
    repair_row_metadata_counts, repair_row_metadata_issues = _repair_row_metadata(
        repaired_rows,
        allow_core_remedies=allow_core_remedies,
    )
    repaired_by_pid: dict[str, dict[str, Any]] = {}
    for row in repaired_rows:
        pid = _prompt_id(row)
        if not pid:
            continue
        repaired_by_pid[pid] = row

    rows: list[dict[str, Any]] = []
    replaced = 0
    by_added: Counter[str] = Counter()
    by_added_core: Counter[str] = Counter()
    by_category: Counter[str] = Counter()
    base_pids: set[str] = set()
    for row in base_rows:
        pid = _prompt_id(row)
        if pid:
            base_pids.add(pid)
        replacement = repaired_by_pid.get(pid)
        if replacement:
            out = dict(replacement)
            meta = _meta_dict(out)
            repair_meta = _sanitized_repair_meta(meta.get("reasoning_repair"))
            if isinstance(meta.get("reasoning_repair"), dict):
                meta["reasoning_repair"] = repair_meta
            variant_meta = {
                "name": "reasoning_repaired",
                "base_prompt_id": pid,
                "source": "build_reasoning_sft_variant.py",
                "replacement": True,
            }
            meta["sft_variant"] = variant_meta
            out["_meta"] = meta
            rows.append(out)
            replaced += 1
            by_added.update(_valid_step_links(repair_meta.get("added_links")))
            by_added_core.update(_valid_core_remedies(repair_meta.get("added_core_remedies")))
            by_category[_safe_category(repair_meta.get("category"))] += 1
        else:
            rows.append(row)

    orphan_repairs = sorted(set(repaired_by_pid) - base_pids)
    output_counts, output_missing, output_duplicate_rows = _prompt_id_stats(rows)
    same_size = len(rows) == len(base_rows)
    one_row_per_base_prompt = (
        same_size
        and repaired_missing == 0
        and output_missing == base_missing
        and base_duplicate_rows == 0
        and output_duplicate_rows == 0
        and set(output_counts) == set(base_counts)
    )
    safe_to_train = (
        one_row_per_base_prompt
        and len(orphan_repairs) == 0
        and repaired_missing == 0
        and repaired_duplicate_rows == 0
        and not source_repair_issues
        and not repair_row_metadata_issues
    )
    manifest = {
        "variant": "reasoning_repaired",
        "base_rows": len(base_rows),
        "base_prompt_ids": len(base_counts),
        "base_missing_prompt_ids": base_missing,
        "base_duplicate_prompt_id_rows": base_duplicate_rows,
        "repaired_input_rows": len(repaired_rows),
        "repaired_prompt_ids": len(repaired_counts),
        "repaired_missing_prompt_ids": repaired_missing,
        "repaired_row_metadata_counts": repair_row_metadata_counts,
        "repaired_row_metadata_issues": repair_row_metadata_issues,
        "output_rows": len(rows),
        "output_prompt_ids": len(output_counts),
        "output_missing_prompt_ids": output_missing,
        "output_duplicate_prompt_id_rows": output_duplicate_rows,
        "replaced_rows": replaced,
        "orphan_repaired_rows": len(orphan_repairs),
        "duplicate_repaired_prompt_ids": repaired_duplicate_rows,
        "by_added_link": {k: by_added[k] for k in sorted(by_added)},
        "by_added_core_remedy": {k: by_added_core[k] for k in sorted(by_added_core)},
        "by_category": {k: by_category[k] for k in sorted(by_category)},
        "require_core_remedies": allow_core_remedies,
        "same_size_as_base": same_size,
        "one_row_per_base_prompt": one_row_per_base_prompt,
        "safe_to_train": safe_to_train,
        "metadata_only": True,
        "output_contains_training_text": True,
        "source_repair_manifest": {
            "path": _display_report_path(repair_manifest.get("path")),
            "output_path": _display_report_path(repair_manifest.get("output_path")),
            "repaired_rows": repair_manifest.get("repaired_rows"),
            "safe_to_train": repair_manifest.get("safe_to_train"),
            "require_core_remedies": repair_manifest.get("require_core_remedies"),
            "by_added_core_remedy": _valid_count_map(
                repair_manifest.get("by_added_core_remedy"),
                _VALID_CORE_REMEDIES,
            ),
            "repair_manifest_issues": repair_manifest.get("repair_manifest_issues"),
            "source_queue": _source_queue_summary(repair_manifest.get("source_queue")),
        } if repair_manifest is not None else None,
        "source_repair_manifest_issues": source_repair_issues,
        "output_path": _display_report_path(output_path),
        "manifest_path": _display_report_path(manifest_path_for(output_path)),
        "note": ("Explicit SFT variant: repaired reasoning rows replace matching base train rows by prompt_id. "
                 "The base split is not mutated, and no duplicate prompt targets are appended. The JSONL output "
                 "contains training text and stays under gitignored reports/; this manifest is metadata-only. "
                 "The CLI refuses to write unless the repaired-row source manifest proves a safe source queue "
                 "and every repaired input row carries repair provenance metadata; core-remedy-only repairs "
                 "are accepted only when the source manifest proves core-remedy enforcement."),
    }
    return {"rows": rows, "manifest": manifest}


def _write_jsonl(path: pathlib.Path, rows: list[dict[str, Any]]) -> None:
    path.write_text("".join(json.dumps(r, ensure_ascii=False) + "\n" for r in rows), encoding="utf-8")


def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--sft", type=pathlib.Path, default=SFT_TRAIN, help="organized base train split")
    ap.add_argument("--repaired", type=pathlib.Path, default=REPAIRED, help="verified repaired reasoning rows")
    ap.add_argument("--out", type=pathlib.Path, default=OUT)
    ap.add_argument("--validate", action="store_true", help="print manifest only; write nothing")
    args = ap.parse_args(argv)

    base_rows = _load_jsonl(args.sft)
    repaired_rows = _load_jsonl(args.repaired)
    if not base_rows:
        print(f"[reasoning-sft-variant] no base train split at {_display_report_path(args.sft)} "
              "-- run organize_training_data.py first")
        return 1
    if not repaired_rows:
        print(f"[reasoning-sft-variant] no repaired rows at {_display_report_path(args.repaired)} "
              "-- run build_reasoning_repairs.py first")
        return 1
    repair_manifest = load_repair_manifest(args.repaired)
    repair_issues = _repair_manifest_issues(repair_manifest, repaired_rows=repaired_rows,
                                            repaired_path=args.repaired)
    doc = build_variant(base_rows, repaired_rows, output_path=args.out,
                        repair_manifest=repair_manifest, repair_manifest_issues=repair_issues,
                        repaired_path=args.repaired)
    m = doc["manifest"]
    if args.validate:
        print(json.dumps(_display_manifest(m), indent=2, ensure_ascii=False))
        return 0 if m["safe_to_train"] else 1
    if not m["safe_to_train"]:
        print(json.dumps(_display_manifest(m), indent=2, ensure_ascii=False))
        print("[reasoning-sft-variant] unsafe variant shape; refusing to write training JSONL")
        return 1
    args.out.parent.mkdir(parents=True, exist_ok=True)
    _write_jsonl(args.out, doc["rows"])
    manifest_path_for(args.out).write_text(json.dumps(m, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
    print(f"[reasoning-sft-variant] {m['base_rows']} base rows -> replaced {m['replaced_rows']} "
          f"with verified repairs -> {_display_report_path(args.out)}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
