#!/usr/bin/env python3
"""Validate corridor-curation slots, sources, lineage, and adjudication.

The default run validates the deterministic workbook and any candidate rows
currently staged under ignored reports/. ``--require-complete`` additionally
requires all 75 slots to contain source-approved, privacy-clean, independently
reviewed rows. Findings never echo prompt, answer, contact, or source payloads.

Offline + deterministic. No model, no network, no credits. Read-only unless an
explicit ``--out`` report path is supplied.
"""
from __future__ import annotations

import argparse
import json
import re
import sys
from collections import Counter, defaultdict
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[1]
SCRIPTS = Path(__file__).resolve().parent
RESEARCH_TOOLS = ROOT / "packages" / "duecare-llm-research-tools" / "src"
for import_path in (SCRIPTS, RESEARCH_TOOLS):
    if str(import_path) not in sys.path:
        sys.path.insert(0, str(import_path))

import build_corridor_curation_workbook as workbook_builder  # noqa: E402
from duecare.research_tools.dedup import content_key, hamming, simhash64  # noqa: E402

ROWS = ROOT / "reports" / "training" / "corridor_curation_rows.jsonl"

REQUIRED_ROW_FIELDS = frozenset(
    {
        "id",
        "slot_id",
        "task_id",
        "category",
        "corridor",
        "scenario_kind",
        "perspective",
        "language",
        "split",
        "lineage_id",
        "lineage_family_id",
        "source_kind",
        "source_ids",
        "source_snapshots",
        "source_retrieved_at",
        "transformation",
        "prompt",
        "target_response",
        "reviews",
        "adjudication",
    }
)
ALLOWED_ROW_FIELDS = REQUIRED_ROW_FIELDS
REVIEW_FIELDS = frozenset({"reviewer_role", "decision", "reviewed_at", "checks"})
REVIEW_CHECKS = frozenset(
    {
        "source_verified",
        "rights_verified",
        "privacy_passed",
        "label_correct",
        "response_grounded",
        "volatile_claims_externalized",
        "benign_control_checked",
        "native_language_reviewed",
    }
)
ADJUDICATION_FIELDS = frozenset({"status", "final_decision", "resolver_role", "resolved_at"})
SHA256_RE = re.compile(r"[0-9a-f]{64}")
DATE_RE = re.compile(r"20\d{2}-\d{2}-\d{2}(?:T[^\s]+)?")
ROLE_RE = re.compile(r"[a-z][a-z0-9_-]{2,63}")
EMAIL_RE = re.compile(r"\b[A-Z0-9._%+-]+@[A-Z0-9.-]+\.[A-Z]{2,}\b", re.I)
PHONE_RE = re.compile(
    r"(?<![\w-])(?:\+\d{1,3}[ .-]?)?(?:\(\d{2,4}\)|\d{2,4})[ .-]\d{3,4}[ .-]\d{3,4}(?![\w-])"
)
LONG_DIGIT_RE = re.compile(r"(?<![A-Za-z0-9])\d{8,}(?![A-Za-z0-9])")
LOCAL_PATH_RE = re.compile(
    r"(?:[A-Za-z]:\\(?:Users|Documents|Desktop|OneDrive)\\|/(?:home|Users)/)", re.I
)


def _load_json(path: Path) -> dict[str, Any]:
    try:
        value = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as exc:
        raise ValueError(f"unreadable JSON: {path.name}") from exc
    if not isinstance(value, dict):
        raise ValueError(f"JSON root must be an object: {path.name}")
    return value


def load_candidate_rows(path: Path) -> tuple[list[dict[str, Any]], list[str]]:
    """Load JSONL without returning malformed payloads in error messages."""
    if not path.exists():
        return [], []
    rows: list[dict[str, Any]] = []
    issues: list[str] = []
    try:
        lines = path.read_text(encoding="utf-8").splitlines()
    except OSError:
        return [], ["rows_unreadable"]
    for index, line in enumerate(lines, 1):
        if not line.strip():
            continue
        try:
            value = json.loads(line)
        except json.JSONDecodeError:
            issues.append(f"row_{index}_invalid_json")
            continue
        if not isinstance(value, dict):
            issues.append(f"row_{index}_not_object")
            continue
        rows.append(value)
    return rows, issues


def _source_map(catalog: dict[str, Any]) -> dict[str, dict[str, Any]]:
    sources = catalog.get("sources")
    if not isinstance(sources, list):
        return {}
    return {
        str(source["id"]): source
        for source in sources
        if isinstance(source, dict) and isinstance(source.get("id"), str)
    }


def _privacy_counts(row: dict[str, Any]) -> dict[str, int]:
    text = "\n".join(
        str(row.get(field) or "") for field in ("prompt", "target_response", "transformation")
    )
    patterns = {
        "email_like": EMAIL_RE,
        "phone_like": PHONE_RE,
        "long_digit_like": LONG_DIGIT_RE,
        "local_path_like": LOCAL_PATH_RE,
    }
    return {
        name: len(pattern.findall(text))
        for name, pattern in patterns.items()
        if pattern.search(text)
    }


def _is_date(value: Any) -> bool:
    return isinstance(value, str) and DATE_RE.fullmatch(value) is not None


def _is_nonempty(value: Any, minimum: int = 1) -> bool:
    return isinstance(value, str) and len(value.strip()) >= minimum


def _review_issues(review: Any, *, prefix: str) -> list[str]:
    if not isinstance(review, dict):
        return [f"{prefix}_shape"]
    issues: list[str] = []
    if set(review) != REVIEW_FIELDS:
        issues.append(f"{prefix}_fields")
    if (
        not isinstance(review.get("reviewer_role"), str)
        or ROLE_RE.fullmatch(review["reviewer_role"]) is None
    ):
        issues.append(f"{prefix}_role")
    if review.get("decision") not in {"accept", "reject"}:
        issues.append(f"{prefix}_decision")
    if not _is_date(review.get("reviewed_at")):
        issues.append(f"{prefix}_date")
    checks = review.get("checks")
    if not isinstance(checks, dict) or set(checks) != REVIEW_CHECKS:
        issues.append(f"{prefix}_checks_shape")
    elif any(
        value is not True and key != "native_language_reviewed"
        for key, value in checks.items()
    ):
        issues.append(f"{prefix}_checks_failed")
    elif not isinstance(checks.get("native_language_reviewed"), bool):
        issues.append(f"{prefix}_native_check_type")
    return issues


def _adjudication_issues(adjudication: Any, reviews: list[dict[str, Any]]) -> list[str]:
    if not isinstance(adjudication, dict):
        return ["adjudication_shape"]
    issues: list[str] = []
    if set(adjudication) != ADJUDICATION_FIELDS:
        issues.append("adjudication_fields")
    decisions = [review.get("decision") for review in reviews if isinstance(review, dict)]
    roles = {review.get("reviewer_role") for review in reviews if isinstance(review, dict)}
    if adjudication.get("final_decision") != "accept":
        issues.append("adjudication_not_accepted")
    if decisions and len(set(decisions)) == 1:
        if adjudication.get("status") != "consensus":
            issues.append("adjudication_consensus_status")
        if (
            adjudication.get("resolver_role") is not None
            or adjudication.get("resolved_at") is not None
        ):
            issues.append("adjudication_consensus_resolver")
    else:
        resolver = adjudication.get("resolver_role")
        if adjudication.get("status") != "resolved":
            issues.append("adjudication_resolution_status")
        if (
            not isinstance(resolver, str)
            or ROLE_RE.fullmatch(resolver) is None
            or resolver in roles
        ):
            issues.append("adjudication_resolver")
        if not _is_date(adjudication.get("resolved_at")):
            issues.append("adjudication_resolution_date")
    return issues


def validate_row(
    row: dict[str, Any],
    slot: dict[str, Any],
    sources: dict[str, dict[str, Any]],
) -> tuple[list[str], dict[str, int]]:
    issues: list[str] = []
    missing = REQUIRED_ROW_FIELDS - set(row)
    extra = set(row) - ALLOWED_ROW_FIELDS
    if missing:
        issues.append("missing_fields")
    if extra:
        issues.append("unexpected_fields")
    exact_fields = {
        "id": slot["slot_id"],
        "slot_id": slot["slot_id"],
        "task_id": slot["task_id"],
        "category": slot["category"],
        "corridor": slot["corridor"],
        "scenario_kind": slot["scenario_kind"],
        "perspective": slot["planned_perspective"],
        "language": slot["planned_language"],
        "split": slot["planned_split"],
        "lineage_family_id": slot["planned_lineage_family_id"],
    }
    for field, expected in exact_fields.items():
        if row.get(field) != expected:
            issues.append(f"{field}_mismatch")
    if not _is_nonempty(row.get("lineage_id"), 12):
        issues.append("lineage_id")
    if row.get("source_kind") not in {"synthetic", "public_source_derived"}:
        issues.append("source_kind")
    if not _is_nonempty(row.get("transformation"), 20):
        issues.append("transformation")
    if not _is_nonempty(row.get("prompt"), 40):
        issues.append("prompt_too_short")
    if not _is_nonempty(row.get("target_response"), 80):
        issues.append("target_response_too_short")

    source_ids = row.get("source_ids")
    if (
        not isinstance(source_ids, list)
        or not source_ids
        or any(not isinstance(item, str) for item in source_ids)
    ):
        issues.append("source_ids")
        source_ids = []
    elif len(source_ids) != len(set(source_ids)):
        issues.append("source_ids_duplicate")
    allowed_ids = set(slot.get("candidate_source_ids") or [])
    if any(source_id not in allowed_ids for source_id in source_ids):
        issues.append("source_not_planned_for_corridor")
    snapshots = row.get("source_snapshots")
    retrieved = row.get("source_retrieved_at")
    if not isinstance(snapshots, dict) or set(snapshots) != set(source_ids):
        issues.append("source_snapshots")
        snapshots = {}
    if not isinstance(retrieved, dict) or set(retrieved) != set(source_ids):
        issues.append("source_retrieved_at")
        retrieved = {}
    for source_id in source_ids:
        source = sources.get(source_id)
        if source is None:
            issues.append("source_unknown")
            continue
        if (
            source.get("admission_status") != "approved"
            or source.get("rights_status") != "approved"
            or source.get("training_use") != "allowed"
        ):
            issues.append("source_not_approved")
        expected_sha = source.get("snapshot_sha256")
        if not isinstance(expected_sha, str) or SHA256_RE.fullmatch(expected_sha) is None:
            issues.append("source_catalog_snapshot")
        if snapshots.get(source_id) != expected_sha:
            issues.append("source_snapshot_mismatch")
        if not _is_date(retrieved.get(source_id)):
            issues.append("source_retrieval_date")

    reviews_value = row.get("reviews")
    reviews = reviews_value if isinstance(reviews_value, list) else []
    if len(reviews) < int(slot.get("required_independent_reviews") or 2):
        issues.append("independent_review_count")
    roles: list[str] = []
    for index, review in enumerate(reviews):
        issues.extend(_review_issues(review, prefix=f"review_{index + 1}"))
        if isinstance(review, dict) and isinstance(review.get("reviewer_role"), str):
            roles.append(review["reviewer_role"])
    if len(roles) != len(set(roles)):
        issues.append("reviewer_roles_not_distinct")
    if slot.get("requires_native_language_review") is True and not any(
        isinstance(review, dict)
        and isinstance(review.get("checks"), dict)
        and review["checks"].get("native_language_reviewed") is True
        for review in reviews
    ):
        issues.append("native_language_review_missing")
    issues.extend(_adjudication_issues(row.get("adjudication"), reviews))

    privacy = _privacy_counts(row)
    if privacy:
        issues.append("privacy_scan")
    return sorted(set(issues)), privacy


def _duplicate_issues(rows: list[dict[str, Any]]) -> tuple[set[str], int, int]:
    invalid_slots: set[str] = set()
    exact_seen: dict[str, str] = {}
    signatures: list[tuple[int, str, str]] = []
    exact_count = 0
    near_count = 0
    for row in rows:
        slot_id = str(row.get("slot_id") or "unknown")
        text = f"{row.get('prompt', '')}\n{row.get('target_response', '')}"
        key = content_key(text)
        if key in exact_seen:
            exact_count += 1
            invalid_slots.update((slot_id, exact_seen[key]))
        else:
            exact_seen[key] = slot_id
        signature = simhash64(str(row.get("prompt") or ""))
        family = str(row.get("lineage_family_id") or "")
        for previous_sig, previous_slot, previous_family in signatures:
            if family != previous_family and hamming(signature, previous_sig) <= 3:
                near_count += 1
                invalid_slots.update((slot_id, previous_slot))
        signatures.append((signature, slot_id, family))
    return invalid_slots, exact_count, near_count


def validate(
    workbook: dict[str, Any],
    current_workbook: dict[str, Any],
    catalog: dict[str, Any],
    rows: list[dict[str, Any]],
    *,
    load_issues: list[str] | None = None,
) -> dict[str, Any]:
    slots_value = workbook.get("slots")
    slots = slots_value if isinstance(slots_value, list) else []
    slot_map = {
        str(slot["slot_id"]): slot
        for slot in slots
        if isinstance(slot, dict) and isinstance(slot.get("slot_id"), str)
    }
    sources = _source_map(catalog)
    catalog_issues = workbook_builder.validate_source_catalog(catalog)
    load_issues = list(load_issues or [])
    row_issues: dict[str, list[str]] = defaultdict(list)
    privacy_totals: Counter[str] = Counter()
    seen_slots: Counter[str] = Counter()
    seen_lineages: Counter[str] = Counter()
    family_splits: dict[str, set[str]] = defaultdict(set)

    for row in rows:
        slot_id = str(row.get("slot_id") or "unknown")
        seen_slots[slot_id] += 1
        lineage_id = str(row.get("lineage_id") or "")
        if lineage_id:
            seen_lineages[lineage_id] += 1
        family = str(row.get("lineage_family_id") or "")
        split = str(row.get("split") or "")
        if family and split:
            family_splits[family].add(split)
        slot = slot_map.get(slot_id)
        if slot is None:
            row_issues[slot_id].append("unexpected_slot")
            continue
        issues, privacy = validate_row(row, slot, sources)
        row_issues[slot_id].extend(issues)
        privacy_totals.update(privacy)

    for slot_id, count in seen_slots.items():
        if count > 1:
            row_issues[slot_id].append("duplicate_slot")
    duplicate_lineages = {lineage for lineage, count in seen_lineages.items() if count > 1}
    if duplicate_lineages:
        for row in rows:
            if str(row.get("lineage_id") or "") in duplicate_lineages:
                row_issues[str(row.get("slot_id") or "unknown")].append("duplicate_lineage_id")
    leaking_families = {family for family, splits in family_splits.items() if len(splits) > 1}
    if leaking_families:
        for row in rows:
            if str(row.get("lineage_family_id") or "") in leaking_families:
                row_issues[str(row.get("slot_id") or "unknown")].append("lineage_family_split_leak")
    duplicate_slots, exact_count, near_count = _duplicate_issues(rows)
    for slot_id in duplicate_slots:
        row_issues[slot_id].append("exact_or_cross_family_near_duplicate")

    row_issues = {
        slot_id: sorted(set(issues))
        for slot_id, issues in sorted(row_issues.items())
        if issues
    }
    filled_slots = {
        slot_id
        for slot_id in seen_slots
        if slot_id in slot_map and seen_slots[slot_id] == 1
    }
    valid_filled_slots = filled_slots - set(row_issues)
    missing_count = len(set(slot_map) - filled_slots)
    complete = (
        len(slot_map) == 75
        and len(rows) == 75
        and missing_count == 0
        and not row_issues
        and not load_issues
    )
    structural_ok = (
        workbook == current_workbook
        and len(slot_map) == 75
        and not catalog_issues
        and not load_issues
        and not row_issues
    )
    return {
        "schema": "duecare.corridor-curation-validation.v1",
        "summary": {
            "valid": structural_ok,
            "complete": complete,
            "ready_for_training": structural_ok and complete,
            "expected_slots": len(slot_map),
            "provided_rows": len(rows),
            "valid_rows": len(valid_filled_slots),
            "missing_slots": missing_count,
            "invalid_row_count": len(row_issues),
            "load_issue_count": len(load_issues),
            "catalog_issue_count": len(catalog_issues),
            "exact_duplicate_pairs": exact_count,
            "cross_family_near_duplicate_pairs": near_count,
            "planned_model_calls": 0,
        },
        "checks": {
            "workbook_matches_current_inputs": workbook == current_workbook,
            "slot_count_is_75": len(slot_map) == 75,
            "source_catalog_valid": not catalog_issues,
            "candidate_rows_parse": not load_issues,
            "provided_rows_valid": not row_issues,
            "lineage_families_isolated": not leaking_families,
            "privacy_scan_ok": not privacy_totals,
            "complete_75_row_adjudication": complete,
        },
        "catalog_issue_codes": catalog_issues,
        "load_issue_codes": sorted(load_issues),
        "row_issue_codes": row_issues,
        "privacy_category_counts": dict(sorted(privacy_totals.items())),
    }


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--workbook", type=Path, default=workbook_builder.OUT)
    parser.add_argument("--plan", type=Path, default=workbook_builder.PLAN)
    parser.add_argument("--sources", type=Path, default=workbook_builder.SOURCE_CATALOG)
    parser.add_argument("--rows", type=Path, default=ROWS)
    parser.add_argument("--out", type=Path, help="optional ignored JSON validation receipt")
    parser.add_argument("--json", action="store_true", help="print the full metadata-only report")
    parser.add_argument(
        "--require-complete", action="store_true", help="require all 75 approved rows"
    )
    args = parser.parse_args(argv)
    try:
        plan = _load_json(args.plan)
        catalog = _load_json(args.sources)
        current = workbook_builder.build_workbook(
            plan,
            catalog,
            plan_sha256=workbook_builder._sha256(args.plan),
            catalog_sha256=workbook_builder._sha256(args.sources),
        )
        workbook = _load_json(args.workbook) if args.workbook.exists() else current
        rows, load_issues = load_candidate_rows(args.rows)
        report = validate(workbook, current, catalog, rows, load_issues=load_issues)
    except (OSError, ValueError) as exc:
        print(f"[corridor-curation] FAIL: {exc}")
        return 1
    if args.out:
        args.out.parent.mkdir(parents=True, exist_ok=True)
        args.out.write_text(json.dumps(report, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    if args.json:
        print(json.dumps(report, indent=2, sort_keys=True))
    else:
        summary = report["summary"]
        print(
            "[corridor-curation] "
            f"valid={str(summary['valid']).lower()} complete={str(summary['complete']).lower()} "
            f"rows={summary['valid_rows']}/{summary['expected_slots']} "
            f"missing={summary['missing_slots']} invalid={summary['invalid_row_count']} "
            f"privacy_findings={sum(report['privacy_category_counts'].values())} model_calls=0"
        )
    required_ok = (
        report["summary"]["ready_for_training"]
        if args.require_complete
        else report["summary"]["valid"]
    )
    return 0 if required_ok else 1


if __name__ == "__main__":
    raise SystemExit(main())
