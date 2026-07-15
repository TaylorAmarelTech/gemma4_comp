#!/usr/bin/env python3
"""Build a privacy-safe corridor expansion curation plan from quality_audit.json.

The training audit identifies dense typologies whose examples sit in a single or generic corridor. This
script turns the audit's metadata-only ``corridor_expansion_tasks`` into a smaller handoff artifact for the
next data pass:

  * one plan entry per category/corridor task;
  * grouped category batches with recommended synthetic/public row counts;
  * a manifest with source-audit fingerprint, privacy checks, and fail-closed safety flags.

It deliberately does NOT copy raw prompts, assistant answers, case narratives, messages, or worker contact
details. If the source audit did not prove that the queue/tasks are metadata-only and privacy-clean, this
builder refuses to write the plan.

Offline + deterministic. No model, no network, no credits.

    python scripts/build_corridor_expansion_plan.py
    python scripts/build_corridor_expansion_plan.py --validate
"""
from __future__ import annotations

import argparse
import hashlib
import json
import pathlib
import re
from collections import Counter, defaultdict
from typing import Any

_ROOT = pathlib.Path(__file__).resolve().parents[1]
TRAIN_DIR = _ROOT / "reports" / "training"
QUALITY_AUDIT = TRAIN_DIR / "quality_audit.json"
OUT = TRAIN_DIR / "corridor_expansion_plan.json"

FORBIDDEN_FIELDS = frozenset({"messages", "prompt", "chosen", "rejected", "assistant", "text"})
PLAN_ENTRY_FIELDS = frozenset({
    "task_id",
    "category",
    "target_corridor",
    "origin",
    "destination",
    "coverage_gap",
    "suggestion_source",
    "recommended_rows",
    "source_policy",
    "scenario_constraints",
    "acceptance_checks",
    "curation_status",
    "review_required",
})
BATCH_FIELDS = frozenset({
    "batch_id",
    "category",
    "coverage_gap",
    "observed_train_rows",
    "task_count",
    "target_corridors",
    "recommended_rows",
    "task_ids",
    "curation_status",
})
REQUIRED_TASK_FIELDS = frozenset({
    "task_id",
    "category",
    "target_corridor",
    "scenario_constraints",
    "acceptance_checks",
})
_EMAIL = re.compile(r"\b[\w.+-]+@[\w-]+\.[\w.-]+\b", re.I)
_PHONE = re.compile(r"\+?\d[\d\s().\-]{8,}\d")
_LONG_DIGITS = re.compile(r"(?<!\d)\d{8,}(?!\d)")
_LOCAL_PATH_HINT = re.compile(
    r"(?:[A-Za-z]:[\\/]|\\\\|(?:^|[\s\"'(:])/(?:Users|home|tmp|var|mnt|private|Volumes)(?:/|$)|~[\\/])",
    re.I,
)
_SAFE_RELATIVE_PATH = re.compile(r"^[A-Za-z0-9._/\-]+$")
_SAFE_LABEL = re.compile(r"^[A-Za-z0-9 ._:/#()>\-]{1,180}$")


def _has_sensitive_display_text(text: str) -> bool:
    return bool(_EMAIL.search(text) or _PHONE.search(text) or _LONG_DIGITS.search(text) or _LOCAL_PATH_HINT.search(text))


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


def _safe_label(value: Any, *, fallback: str = "unknown") -> str:
    if not isinstance(value, str):
        return fallback
    text = value.strip()
    if text and _SAFE_LABEL.fullmatch(text) and not _has_sensitive_display_text(text):
        return text
    return fallback


def _safe_slug(value: Any) -> str:
    text = str(value or "").lower()
    text = re.sub(r"[^a-z0-9]+", "-", text).strip("-")
    return text[:64].strip("-") or "unknown"


def _safe_positive_int(value: Any, *, default: int = 3) -> int:
    if isinstance(value, bool):
        return default
    if isinstance(value, int) and value > 0:
        return value
    return default


def _file_sha256(path: pathlib.Path | None) -> str | None:
    if path is None:
        return None
    try:
        return hashlib.sha256(path.read_bytes()).hexdigest()
    except OSError:
        return None


def _privacy_scan(value: Any, *, path: str = "$") -> dict[str, Any]:
    findings: dict[str, list[str]] = {
        "forbidden_field_paths": [],
        "unexpected_plan_field_paths": [],
        "unexpected_batch_field_paths": [],
        "email_like_paths": [],
        "phone_like_paths": [],
        "long_digit_paths": [],
        "local_path_like_paths": [],
    }

    def walk(v: Any, p: str) -> None:
        if isinstance(v, dict):
            if re.fullmatch(r"\$\.plan\[\d+\]", p):
                for key in v:
                    if str(key) not in PLAN_ENTRY_FIELDS:
                        findings["unexpected_plan_field_paths"].append(f"{p}.{key}")
            if re.fullmatch(r"\$\.batches\[\d+\]", p):
                for key in v:
                    if str(key) not in BATCH_FIELDS:
                        findings["unexpected_batch_field_paths"].append(f"{p}.{key}")
            for key, item in v.items():
                key_path = f"{p}.{key}"
                if str(key) in FORBIDDEN_FIELDS:
                    findings["forbidden_field_paths"].append(key_path)
                walk(item, key_path)
        elif isinstance(v, list):
            for idx, item in enumerate(v):
                walk(item, f"{p}[{idx}]")
        elif isinstance(v, str):
            field = p.rsplit(".", 1)[-1]
            if field.endswith("sha256"):
                return
            if _EMAIL.search(v):
                findings["email_like_paths"].append(p)
            if _PHONE.search(v):
                findings["phone_like_paths"].append(p)
            if _LONG_DIGITS.search(v):
                findings["long_digit_paths"].append(p)
            if _LOCAL_PATH_HINT.search(v) or "\\" in v:
                findings["local_path_like_paths"].append(p)

    walk(value, path)
    counts = {key.replace("_paths", ""): len(paths) for key, paths in findings.items()}
    findings["counts"] = counts
    findings["ok"] = not any(counts.values())
    return findings


def _source_privacy_ok(corridor: dict[str, Any]) -> bool:
    queue_scan = corridor.get("corridor_expansion_queue_privacy_scan") or {}
    tasks_scan = corridor.get("corridor_expansion_tasks_privacy_scan") or {}
    return (
        corridor.get("corridor_expansion_queue_metadata_only") is True
        and corridor.get("corridor_expansion_tasks_metadata_only") is True
        and queue_scan.get("ok") is True
        and tasks_scan.get("ok") is True
    )


def _category_meta(corridor: dict[str, Any]) -> dict[str, dict[str, Any]]:
    out: dict[str, dict[str, Any]] = {}
    for entry in corridor.get("corridor_expansion_queue") or []:
        if not isinstance(entry, dict):
            continue
        category = _safe_label(entry.get("category"))
        out[category] = {
            "coverage_gap": _safe_label(entry.get("coverage_gap")),
            "observed_train_rows": _safe_positive_int(entry.get("train_rows"), default=0),
        }
    return out


def _plan_entry(task: dict[str, Any]) -> tuple[dict[str, Any] | None, list[str]]:
    issues: list[str] = []
    missing = sorted(field for field in REQUIRED_TASK_FIELDS if field not in task)
    if missing:
        issues.append("corridor_expansion_task_required_fields_missing")
        return None, issues
    entry = {
        "task_id": _safe_label(task.get("task_id")),
        "category": _safe_label(task.get("category")),
        "target_corridor": _safe_label(task.get("target_corridor")),
        "origin": _safe_label(task.get("origin"), fallback=""),
        "destination": _safe_label(task.get("destination"), fallback=""),
        "coverage_gap": _safe_label(task.get("coverage_gap")),
        "suggestion_source": _safe_label(task.get("suggestion_source")),
        "recommended_rows": _safe_positive_int(task.get("suggested_min_synthetic_rows")),
        "source_policy": "synthetic_or_public_only",
        "scenario_constraints": [
            _safe_label(item) for item in task.get("scenario_constraints", []) if isinstance(item, str)
        ],
        "acceptance_checks": [
            _safe_label(item) for item in task.get("acceptance_checks", []) if isinstance(item, str)
        ],
        "curation_status": "todo",
        "review_required": True,
    }
    return entry, issues


def _batches(plan: list[dict[str, Any]], category_meta: dict[str, dict[str, Any]]) -> list[dict[str, Any]]:
    grouped: dict[str, list[dict[str, Any]]] = defaultdict(list)
    for entry in plan:
        grouped[entry["category"]].append(entry)

    batches: list[dict[str, Any]] = []
    for category in sorted(grouped):
        entries = sorted(grouped[category], key=lambda item: (item["target_corridor"], item["task_id"]))
        meta = category_meta.get(category, {})
        batches.append({
            "batch_id": f"corridor-expansion-{_safe_slug(category)}",
            "category": category,
            "coverage_gap": meta.get("coverage_gap", entries[0].get("coverage_gap", "unknown")),
            "observed_train_rows": meta.get("observed_train_rows", 0),
            "task_count": len(entries),
            "target_corridors": [entry["target_corridor"] for entry in entries],
            "recommended_rows": sum(entry["recommended_rows"] for entry in entries),
            "task_ids": [entry["task_id"] for entry in entries],
            "curation_status": "todo",
        })
    return batches


def build_plan(
    audit: dict[str, Any],
    *,
    audit_path: pathlib.Path | None = None,
) -> dict[str, Any]:
    corridor = audit.get("jurisdiction_corridor_diversity") if isinstance(audit, dict) else {}
    corridor = corridor if isinstance(corridor, dict) else {}
    raw_tasks = corridor.get("corridor_expansion_tasks") or []
    source_privacy_ok = _source_privacy_ok(corridor)
    skipped: Counter[str] = Counter()
    manifest_issues: list[str] = []
    plan: list[dict[str, Any]] = []

    if not isinstance(raw_tasks, list):
        raw_tasks = []
        manifest_issues.append("corridor_expansion_tasks_not_list")

    for raw in raw_tasks:
        if not isinstance(raw, dict):
            skipped["non_object_task"] += 1
            continue
        entry, issues = _plan_entry(raw)
        manifest_issues.extend(issues)
        if entry is not None:
            plan.append(entry)
    plan.sort(key=lambda item: (item["category"], item["target_corridor"], item["task_id"]))
    batches = _batches(plan, _category_meta(corridor))

    by_category = Counter(entry["category"] for entry in plan)
    by_corridor = Counter(entry["target_corridor"] for entry in plan)
    source_sha = _file_sha256(audit_path) if audit_path else None
    expected_task_count = corridor.get("corridor_expansion_task_count")

    doc = {
        "plan": plan,
        "batches": batches,
    }
    privacy_scan = _privacy_scan(doc)
    if not source_privacy_ok:
        manifest_issues.append("corridor_expansion_source_privacy_not_ok")
    if privacy_scan.get("ok") is not True:
        manifest_issues.append("corridor_expansion_plan_privacy_scan_not_ok")
    if isinstance(expected_task_count, int) and expected_task_count != len(plan):
        manifest_issues.append("corridor_expansion_task_count_mismatch")
    if not isinstance(expected_task_count, int):
        manifest_issues.append("corridor_expansion_task_count_missing")

    manifest = {
        "source_audit_path": _display_report_path(audit_path) if audit_path else "n/a",
        "source_audit_sha256": source_sha,
        "queue_count": corridor.get("corridor_expansion_queue_count"),
        "source_task_count": expected_task_count,
        "planned_task_count": len(plan),
        "batch_count": len(batches),
        "recommended_rows": sum(entry["recommended_rows"] for entry in plan),
        "by_category": {key: by_category[key] for key in sorted(by_category)},
        "by_target_corridor": {key: by_corridor[key] for key in sorted(by_corridor)},
        "skipped": {key: skipped[key] for key in sorted(skipped)},
        "metadata_only": True,
        "source_privacy_ok": source_privacy_ok,
        "privacy_scan": privacy_scan,
        "plan_manifest_issues": sorted(set(manifest_issues)),
        "safe_for_curation": not manifest_issues,
        "actionable_for_curation": bool(plan),
        "note": (
            "Metadata-only handoff for widening dense single-corridor training coverage. Curators should "
            "add vetted synthetic or public-source rows only; raw prompts, answers, case text, names, "
            "contacts, and private worker details do not belong in this artifact."
        ),
    }
    doc["manifest"] = manifest
    return doc


def _load_audit(path: pathlib.Path) -> dict[str, Any] | None:
    try:
        audit = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError):
        return None
    return audit if isinstance(audit, dict) else None


def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--audit", type=pathlib.Path, default=QUALITY_AUDIT)
    ap.add_argument("--out", type=pathlib.Path, default=OUT)
    ap.add_argument("--manifest-out", type=pathlib.Path, default=None)
    ap.add_argument("--validate", action="store_true", help="print the manifest only; write nothing")
    args = ap.parse_args(argv)

    audit = _load_audit(args.audit)
    if audit is None:
        print(f"[corridor-expansion-plan] unreadable quality audit at {_display_report_path(args.audit)}")
        return 1
    doc = build_plan(audit, audit_path=args.audit)
    manifest = doc["manifest"]
    if args.validate:
        print(json.dumps(manifest, indent=2, ensure_ascii=False))
        return 0 if manifest["safe_for_curation"] else 1
    if not manifest["safe_for_curation"]:
        print(json.dumps(manifest, indent=2, ensure_ascii=False))
        print("[corridor-expansion-plan] source audit/plan is unsafe; refusing to write plan")
        return 1

    manifest_out = args.manifest_out or args.out.with_name(f"{args.out.stem}_manifest.json")
    manifest["output_path"] = _display_report_path(args.out)
    manifest["manifest_path"] = _display_report_path(manifest_out)
    args.out.parent.mkdir(parents=True, exist_ok=True)
    manifest_out.parent.mkdir(parents=True, exist_ok=True)
    args.out.write_text(json.dumps(doc, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
    manifest_out.write_text(json.dumps(manifest, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
    print(
        "[corridor-expansion-plan] "
        f"{manifest['planned_task_count']} tasks in {manifest['batch_count']} batches "
        f"({manifest['recommended_rows']} recommended rows) -> {_display_report_path(args.out)}"
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
