#!/usr/bin/env python3
"""Build a source-review progress ledger for a benchmark domain.

This command summarizes the current state of a source-review packet:

* source rows that are still blank, partially filled, ready-claimed, accepted,
  or blocked by validation
* scope rows that are still blank, partially filled, ready-claimed, accepted,
  or blocked by validation
* required field completion and review-gate status for each row

It does not fetch sources, verify law, fill review rows, edit a grounding
manifest, generate prompts, or authorize comparable benchmark scoring.
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
_SCRIPTS = pathlib.Path(__file__).resolve().parent
if str(_SCRIPTS) not in sys.path:
    sys.path.insert(0, str(_SCRIPTS))

from build_domain_source_review_packet import build_source_review_packet  # noqa: E402
from validate_domain_source_review_packet import validate_source_review_packet  # noqa: E402

OUT_DIR = _ROOT / "reports" / "benchmark"
_SAFE_DOMAIN_ID = re.compile(r"^[a-z0-9_:-]{1,80}$")

SOURCE_REVIEW_FIELDS = [
    "candidate_title",
    "candidate_authority",
    "candidate_url",
    "candidate_source_type",
    "candidate_publication_date",
    "candidate_accessed_date",
    "candidate_language",
    "official_or_public_interest",
    "legal_scope_note",
    "privacy_notes",
    "pii_risk",
    "license_or_terms_note",
    "reviewer_notes",
]

SOURCE_PROMOTION_FIELDS = [
    "candidate_title",
    "candidate_authority",
    "candidate_url",
    "candidate_source_type",
    "candidate_publication_date",
    "candidate_accessed_date",
    "candidate_language",
    "official_or_public_interest",
    "legal_scope_note",
    "privacy_notes",
    "license_or_terms_note",
    "reviewer_notes",
]

SCOPE_REVIEW_FIELDS = [
    "resolved_jurisdictions",
    "resolved_forums_or_regulators",
    "origin_state_role",
    "destination_state_role",
    "flag_or_port_state_role",
    "source_ids_to_create",
    "resolution_note",
]

SCOPE_REQUIRED_FIELDS = [
    "resolved_jurisdictions",
    "resolved_forums_or_regulators",
    "source_ids_to_create",
    "resolution_note",
]


def _safe_domain_id(domain_id: str) -> str:
    if not _SAFE_DOMAIN_ID.fullmatch(domain_id):
        raise ValueError(f"unsafe domain id: {domain_id!r}")
    return domain_id


def _load_json(path: pathlib.Path) -> dict[str, Any]:
    doc = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(doc, dict):
        raise ValueError(f"expected JSON object: {path}")
    return doc


def _has_value(field: str, value: Any) -> bool:
    if isinstance(value, str):
        if field == "pii_risk" and value.strip().lower() == "unknown":
            return False
        return bool(value.strip())
    if isinstance(value, list):
        return bool(value)
    if isinstance(value, bool):
        return True
    return value is not None


def _filled_fields(row: dict[str, Any], fields: list[str]) -> list[str]:
    return [field for field in fields if _has_value(field, row.get(field))]


def _missing_fields(row: dict[str, Any], fields: list[str]) -> list[str]:
    return [field for field in fields if not _has_value(field, row.get(field))]


def _source_ready_claimed(row: dict[str, Any]) -> bool:
    return (
        row.get("ready_for_manifest_promotion") is True
        or row.get("proposed_manifest_verification_status") == "verified_local_law"
    )


def _scope_ready_claimed(row: dict[str, Any]) -> bool:
    return row.get("ready_for_source_queue_update") is True


def _source_status(
    row: dict[str, Any],
    validation_result: dict[str, Any],
    filled: list[str],
) -> str:
    if validation_result.get("accepted_for_manifest_proposal") is True:
        return "accepted_for_manifest_proposal"
    if _source_ready_claimed(row):
        return "ready_claim_blocked_by_validation" if validation_result.get("issues") else "ready_claim_pending"
    if filled:
        return "in_progress_not_ready"
    return "not_started"


def _scope_status(
    row: dict[str, Any],
    validation_result: dict[str, Any],
    filled: list[str],
) -> str:
    if validation_result.get("accepted_for_source_queue_update") is True:
        return "accepted_for_source_queue_update"
    if _scope_ready_claimed(row):
        return "ready_claim_blocked_by_validation" if validation_result.get("issues") else "ready_claim_pending"
    if filled:
        return "in_progress_not_ready"
    return "not_started"


def _validation_by_task(results: list[dict[str, Any]]) -> dict[str, dict[str, Any]]:
    return {
        str(result.get("task_id")): result
        for result in results
        if isinstance(result, dict) and result.get("task_id")
    }


def _source_ledger_rows(
    packet: dict[str, Any],
    validation: dict[str, Any],
) -> list[dict[str, Any]]:
    by_task = _validation_by_task(validation.get("source_row_results", []))
    rows: list[dict[str, Any]] = []
    for row in packet.get("source_candidate_intake_rows", []) or []:
        if not isinstance(row, dict):
            continue
        task_id = str(row.get("task_id"))
        result = by_task.get(task_id, {})
        filled = _filled_fields(row, SOURCE_REVIEW_FIELDS)
        missing = _missing_fields(row, SOURCE_PROMOTION_FIELDS)
        rows.append({
            "task_id": task_id,
            "source_id": row.get("source_id"),
            "jurisdiction": row.get("jurisdiction"),
            "jurisdiction_label": row.get("jurisdiction_label"),
            "category": row.get("category"),
            "blocked_prompt_ids": list(row.get("blocked_prompt_ids") or []),
            "status": _source_status(row, result, filled),
            "filled_review_fields": filled,
            "filled_review_field_count": len(filled),
            "missing_promotion_fields": missing,
            "missing_promotion_field_count": len(missing),
            "ready_claimed": _source_ready_claimed(row),
            "accepted_for_manifest_proposal": result.get("accepted_for_manifest_proposal") is True,
            "privacy_review_required": row.get("privacy_review_required"),
            "expert_review_required": row.get("expert_review_required"),
            "validation_issue_count": len(result.get("issues") or []),
            "validation_issues": list(result.get("issues") or []),
        })
    rows.sort(key=lambda item: (item["status"], str(item["jurisdiction"]), str(item["category"]), str(item["source_id"])))
    return rows


def _scope_ledger_rows(
    packet: dict[str, Any],
    validation: dict[str, Any],
) -> list[dict[str, Any]]:
    by_task = _validation_by_task(validation.get("scope_row_results", []))
    rows: list[dict[str, Any]] = []
    for row in packet.get("scope_resolution_intake_rows", []) or []:
        if not isinstance(row, dict):
            continue
        task_id = str(row.get("task_id"))
        result = by_task.get(task_id, {})
        filled = _filled_fields(row, SCOPE_REVIEW_FIELDS)
        missing = _missing_fields(row, SCOPE_REQUIRED_FIELDS)
        rows.append({
            "task_id": task_id,
            "scope_id": row.get("scope_id"),
            "scope": row.get("scope"),
            "category": row.get("category"),
            "blocked_prompt_ids": list(row.get("blocked_prompt_ids") or []),
            "status": _scope_status(row, result, filled),
            "filled_review_fields": filled,
            "filled_review_field_count": len(filled),
            "missing_required_fields": missing,
            "missing_required_field_count": len(missing),
            "ready_claimed": _scope_ready_claimed(row),
            "accepted_for_source_queue_update": result.get("accepted_for_source_queue_update") is True,
            "expert_review_required": row.get("expert_review_required"),
            "validation_issue_count": len(result.get("issues") or []),
            "validation_issues": list(result.get("issues") or []),
        })
    rows.sort(key=lambda item: (item["status"], str(item["scope"]), str(item["category"]), str(item["task_id"])))
    return rows


def _checks(packet: dict[str, Any], validation: dict[str, Any], source_rows: list[dict[str, Any]], scope_rows: list[dict[str, Any]]) -> list[dict[str, Any]]:
    packet_source_count = len(packet.get("source_candidate_intake_rows", []) or [])
    packet_scope_count = len(packet.get("scope_resolution_intake_rows", []) or [])
    validation_summary = validation.get("summary", {})
    return [
        {
            "id": "source_row_count_matches_packet",
            "ok": packet_source_count == len(source_rows),
            "expected": packet_source_count,
            "actual": len(source_rows),
        },
        {
            "id": "scope_row_count_matches_packet",
            "ok": packet_scope_count == len(scope_rows),
            "expected": packet_scope_count,
            "actual": len(scope_rows),
        },
        {
            "id": "validation_source_count_matches_packet",
            "ok": validation_summary.get("source_rows") == packet_source_count,
            "expected": packet_source_count,
            "actual": validation_summary.get("source_rows"),
        },
        {
            "id": "validation_scope_count_matches_packet",
            "ok": validation_summary.get("scope_rows") == packet_scope_count,
            "expected": packet_scope_count,
            "actual": validation_summary.get("scope_rows"),
        },
        {
            "id": "no_comparable_scoring_claim",
            "ok": True,
            "expected": False,
            "actual": False,
        },
    ]


def build_source_review_ledger(
    domain_id: str,
    *,
    review_packet_doc: dict[str, Any] | None = None,
) -> dict[str, Any]:
    """Return a compact progress ledger for a source-review packet."""
    domain_id = _safe_domain_id(domain_id)
    packet = review_packet_doc or build_source_review_packet(domain_id)
    validation = validate_source_review_packet(packet, domain_id=domain_id)
    source_rows = _source_ledger_rows(packet, validation)
    scope_rows = _scope_ledger_rows(packet, validation)
    source_status_counts = Counter(row["status"] for row in source_rows)
    scope_status_counts = Counter(row["status"] for row in scope_rows)
    checks = _checks(packet, validation, source_rows, scope_rows)
    return {
        "_meta": {
            "domain": domain_id,
            "display_name": (packet.get("_meta") or {}).get("display_name"),
            "status": (
                "source-review progress ledger; not legal advice, not source verification, "
                "not manifest promotion, and not comparable benchmark evidence"
            ),
            "source_packet_status": (packet.get("_meta") or {}).get("status"),
            "validation_status": (validation.get("_meta") or {}).get("status"),
        },
        "summary": {
            "consistency_ok": all(check["ok"] for check in checks),
            "source_rows": len(source_rows),
            "source_rows_not_started": source_status_counts.get("not_started", 0),
            "source_rows_in_progress_not_ready": source_status_counts.get("in_progress_not_ready", 0),
            "source_rows_ready_claimed": sum(1 for row in source_rows if row["ready_claimed"]),
            "source_rows_accepted_for_manifest_proposal": sum(
                1 for row in source_rows if row["accepted_for_manifest_proposal"]
            ),
            "source_rows_blocked_by_validation": source_status_counts.get("ready_claim_blocked_by_validation", 0),
            "scope_rows": len(scope_rows),
            "scope_rows_not_started": scope_status_counts.get("not_started", 0),
            "scope_rows_in_progress_not_ready": scope_status_counts.get("in_progress_not_ready", 0),
            "scope_rows_ready_claimed": sum(1 for row in scope_rows if row["ready_claimed"]),
            "scope_rows_accepted_for_source_queue_update": sum(
                1 for row in scope_rows if row["accepted_for_source_queue_update"]
            ),
            "scope_rows_blocked_by_validation": scope_status_counts.get("ready_claim_blocked_by_validation", 0),
            "validation_ok": validation.get("summary", {}).get("ok"),
            "ready_for_comparable_run": False,
            "policy": (
                "This ledger reports review progress only. Source rows still need dated public-source "
                "metadata, privacy review, and expert review before validation can propose manifest rows."
            ),
        },
        "source_review_ledger_rows": source_rows,
        "scope_review_ledger_rows": scope_rows,
        "validation_summary": dict(validation.get("summary", {})),
        "consistency_checks": checks,
    }


def default_out_path(domain_id: str) -> pathlib.Path:
    return OUT_DIR / f"{_safe_domain_id(domain_id)}_source_review_ledger.json"


def default_markdown_path(json_path: pathlib.Path) -> pathlib.Path:
    return json_path.with_suffix(".md")


def _md_cell(value: Any) -> str:
    text = str(value if value is not None else "")
    return text.replace("|", "\\|").replace("\n", " ").strip()


def _md_list(values: list[Any]) -> str:
    return ", ".join(_md_cell(v) for v in values) if values else "-"


def build_markdown_report(doc: dict[str, Any]) -> str:
    """Render a compact Markdown source-review ledger."""
    meta = doc["_meta"]
    summary = doc["summary"]
    lines: list[str] = [
        f"# Domain Source Review Ledger - {_md_cell(meta.get('display_name') or meta.get('domain'))}",
        "",
        (
            "This ledger reports review-packet progress. It is not legal advice, not source "
            "verification, not manifest promotion, and not comparable benchmark evidence."
        ),
        "",
        "## Summary",
        "",
        "| Metric | Value |",
        "|---|---:|",
        f"| Consistency OK | {str(bool(summary['consistency_ok'])).lower()} |",
        f"| Source rows | {summary['source_rows']} |",
        f"| Source rows not started | {summary['source_rows_not_started']} |",
        f"| Source rows in progress | {summary['source_rows_in_progress_not_ready']} |",
        f"| Source rows ready claimed | {summary['source_rows_ready_claimed']} |",
        f"| Source rows accepted for manifest proposal | {summary['source_rows_accepted_for_manifest_proposal']} |",
        f"| Source rows blocked by validation | {summary['source_rows_blocked_by_validation']} |",
        f"| Scope rows | {summary['scope_rows']} |",
        f"| Scope rows not started | {summary['scope_rows_not_started']} |",
        f"| Scope rows in progress | {summary['scope_rows_in_progress_not_ready']} |",
        f"| Scope rows ready claimed | {summary['scope_rows_ready_claimed']} |",
        f"| Scope rows accepted for source queue update | {summary['scope_rows_accepted_for_source_queue_update']} |",
        f"| Scope rows blocked by validation | {summary['scope_rows_blocked_by_validation']} |",
        f"| Ready for comparable run | {str(bool(summary['ready_for_comparable_run'])).lower()} |",
        "",
        "## Source Rows",
        "",
        "| Task | Source ID | Status | Filled fields | Missing promotion fields | Validation issues |",
        "|---|---|---|---:|---:|---:|",
    ]
    for row in doc["source_review_ledger_rows"]:
        lines.append(
            f"| `{_md_cell(row['task_id'])}` "
            f"| `{_md_cell(row['source_id'])}` "
            f"| {_md_cell(row['status'])} "
            f"| {row['filled_review_field_count']} "
            f"| {row['missing_promotion_field_count']} "
            f"| {row['validation_issue_count']} |"
        )
    lines.extend([
        "",
        "## Scope Rows",
        "",
        "| Task | Scope | Category | Status | Filled fields | Missing required fields | Validation issues |",
        "|---|---|---|---|---:|---:|---:|",
    ])
    for row in doc["scope_review_ledger_rows"]:
        lines.append(
            f"| `{_md_cell(row['task_id'])}` "
            f"| {_md_cell(row['scope'])} "
            f"| {_md_cell(row['category'])} "
            f"| {_md_cell(row['status'])} "
            f"| {row['filled_review_field_count']} "
            f"| {row['missing_required_field_count']} "
            f"| {row['validation_issue_count']} |"
        )
    lines.extend([
        "",
        "## Consistency Checks",
        "",
        "| Check | OK | Expected | Actual |",
        "|---|---:|---|---|",
    ])
    for check in doc["consistency_checks"]:
        lines.append(
            f"| {_md_cell(check['id'])} "
            f"| {str(bool(check['ok'])).lower()} "
            f"| {_md_cell(check['expected'])} "
            f"| {_md_cell(check['actual'])} |"
        )
    lines.append("")
    return "\n".join(lines)


def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--domain", default="developing_country_worker_protections")
    ap.add_argument("--review-packet", type=pathlib.Path, default=None, help="optional source-review packet JSON")
    ap.add_argument("--out", type=pathlib.Path, default=None)
    ap.add_argument("--md-out", type=pathlib.Path, default=None, help="Markdown report path; defaults to --out with .md suffix")
    ap.add_argument("--no-md", action="store_true", help="write only JSON, not the Markdown ledger")
    args = ap.parse_args(argv)

    packet = _load_json(args.review_packet) if args.review_packet else None
    doc = build_source_review_ledger(args.domain, review_packet_doc=packet)
    out_path = args.out or default_out_path(args.domain)
    out_path.parent.mkdir(parents=True, exist_ok=True)
    out_path.write_text(json.dumps(doc, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
    md_path = None
    if not args.no_md:
        md_path = args.md_out or default_markdown_path(out_path)
        md_path.parent.mkdir(parents=True, exist_ok=True)
        md_path.write_text(build_markdown_report(doc) + "\n", encoding="utf-8")
    summary = doc["summary"]
    print(
        f"wrote {out_path}: {summary['source_rows_not_started']}/{summary['source_rows']} source rows not started; "
        f"{summary['scope_rows_not_started']}/{summary['scope_rows']} scope rows not started; "
        f"ready_for_comparable_run={str(bool(summary['ready_for_comparable_run'])).lower()}"
        + (f"; report {md_path}" if md_path else "")
    )
    return 0 if summary["consistency_ok"] else 1


if __name__ == "__main__":
    raise SystemExit(main())
