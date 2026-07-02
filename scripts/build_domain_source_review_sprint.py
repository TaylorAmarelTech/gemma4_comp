#!/usr/bin/env python3
"""Build a source-review sprint packet for a benchmark domain.

This is a compact worklist derived from the source-coverage matrix and blank
source-review packet. It separates:

1. scope-resolution tasks that must happen before source rows can be promoted
2. non-scope-blocked source rows ready for curator source review
3. deferred source rows that remain blocked by broad corridor/forum scope

It does not fetch sources, verify law, fill review rows, edit a grounding
manifest, generate prompts, or authorize comparable benchmark scoring.
"""
from __future__ import annotations

import argparse
import json
import pathlib
import re
import sys
from typing import Any

_ROOT = pathlib.Path(__file__).resolve().parents[1]
_SCRIPTS = pathlib.Path(__file__).resolve().parent
if str(_SCRIPTS) not in sys.path:
    sys.path.insert(0, str(_SCRIPTS))

from build_domain_source_coverage_matrix import build_source_coverage_matrix  # noqa: E402
from build_domain_source_review_packet import build_source_review_packet  # noqa: E402

OUT_DIR = _ROOT / "reports" / "benchmark"
_SAFE_DOMAIN_ID = re.compile(r"^[a-z0-9_:-]{1,80}$")


def _safe_domain_id(domain_id: str) -> str:
    if not _SAFE_DOMAIN_ID.fullmatch(domain_id):
        raise ValueError(f"unsafe domain id: {domain_id!r}")
    return domain_id


def _load_json(path: pathlib.Path) -> dict[str, Any]:
    doc = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(doc, dict):
        raise ValueError(f"expected JSON object: {path}")
    return doc


def _source_rows_by_id(review_packet: dict[str, Any]) -> dict[str, dict[str, Any]]:
    return {
        str(row.get("source_id")): row
        for row in review_packet.get("source_candidate_intake_rows", [])
        if isinstance(row, dict) and row.get("source_id")
    }


def _scope_rows_by_task(review_packet: dict[str, Any]) -> dict[str, dict[str, Any]]:
    return {
        str(row.get("task_id")): row
        for row in review_packet.get("scope_resolution_intake_rows", [])
        if isinstance(row, dict) and row.get("task_id")
    }


def _source_sprint_row(matrix_row: dict[str, Any], review_row: dict[str, Any]) -> dict[str, Any]:
    return {
        "sprint_item_id": f"SOURCE-{matrix_row['source_id']}",
        "source_id": matrix_row["source_id"],
        "source_task_id": matrix_row["source_task_id"],
        "cell_id": matrix_row["cell_id"],
        "priority_band": matrix_row["priority_band"],
        "jurisdiction": matrix_row["jurisdiction"],
        "jurisdiction_label": matrix_row.get("jurisdiction_label"),
        "category": matrix_row["category"],
        "coverage_status": matrix_row["coverage_status"],
        "action": matrix_row["action"],
        "blocked_prompt_ids": list(matrix_row.get("blocked_prompt_ids") or []),
        "review_packet_defaults": {
            "proposed_manifest_verification_status": review_row.get("proposed_manifest_verification_status"),
            "ready_for_manifest_promotion": review_row.get("ready_for_manifest_promotion"),
            "privacy_review_required": review_row.get("privacy_review_required"),
            "expert_review_required": review_row.get("expert_review_required"),
        },
        "fields_to_complete": [
            "candidate_title",
            "candidate_authority",
            "candidate_url",
            "candidate_archive_url",
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
        ],
        "next_step": matrix_row["next_step"],
    }


def _scope_sprint_row(scope_row: dict[str, Any], review_row: dict[str, Any]) -> dict[str, Any]:
    return {
        "sprint_item_id": f"SCOPE-{scope_row['task_id']}",
        "scope_task_id": scope_row["task_id"],
        "scope": scope_row["scope"],
        "category": scope_row["category"],
        "related_coverage_cell_ids": list(scope_row.get("related_coverage_cell_ids") or []),
        "blocked_prompt_ids": list(scope_row.get("blocked_prompt_ids") or []),
        "review_packet_defaults": {
            "resolved_jurisdictions": list(review_row.get("resolved_jurisdictions") or []),
            "resolved_forums_or_regulators": list(review_row.get("resolved_forums_or_regulators") or []),
            "ready_for_source_queue_update": review_row.get("ready_for_source_queue_update"),
            "expert_review_required": review_row.get("expert_review_required"),
        },
        "fields_to_complete": [
            "resolved_jurisdictions",
            "resolved_forums_or_regulators",
            "origin_state_role",
            "destination_state_role",
            "flag_or_port_state_role",
            "source_ids_to_create",
            "resolution_note",
        ],
        "next_step": scope_row["next_step"],
    }


def _deferred_row(matrix_row: dict[str, Any]) -> dict[str, Any]:
    return {
        "cell_id": matrix_row["cell_id"],
        "source_id": matrix_row["source_id"],
        "jurisdiction": matrix_row["jurisdiction"],
        "category": matrix_row["category"],
        "related_scope_task_ids": list(matrix_row.get("related_scope_task_ids") or []),
        "related_unresolved_scopes": list(matrix_row.get("related_unresolved_scopes") or []),
        "blocked_prompt_ids": list(matrix_row.get("blocked_prompt_ids") or []),
        "defer_reason": "scope resolution required before source-row promotion",
    }


def _checks(
    matrix_doc: dict[str, Any],
    review_packet: dict[str, Any],
    source_sprint_rows: list[dict[str, Any]],
    scope_sprint_rows: list[dict[str, Any]],
) -> list[dict[str, Any]]:
    matrix_summary = matrix_doc.get("summary", {})
    audit = review_packet.get("safety_audit", {})
    selected_ready_claims = [
        row["source_id"]
        for row in source_sprint_rows
        if row["review_packet_defaults"].get("ready_for_manifest_promotion") is not False
    ]
    scope_ready_claims = [
        row["scope_task_id"]
        for row in scope_sprint_rows
        if row["review_packet_defaults"].get("ready_for_source_queue_update") is not False
    ]
    return [
        {
            "id": "coverage_matrix_consistency_ok",
            "ok": matrix_summary.get("consistency_ok") is True,
            "expected": True,
            "actual": matrix_summary.get("consistency_ok"),
        },
        {
            "id": "review_packet_safety_audit_ok",
            "ok": audit.get("ok") is True,
            "expected": True,
            "actual": audit.get("ok"),
        },
        {
            "id": "selected_source_rows_not_preclaimed_ready",
            "ok": not selected_ready_claims,
            "expected": [],
            "actual": selected_ready_claims,
        },
        {
            "id": "selected_scope_rows_not_preclaimed_ready",
            "ok": not scope_ready_claims,
            "expected": [],
            "actual": scope_ready_claims,
        },
        {
            "id": "no_comparable_scoring_claim",
            "ok": matrix_summary.get("ready_for_comparable_run") is False,
            "expected": False,
            "actual": matrix_summary.get("ready_for_comparable_run"),
        },
    ]


def build_source_review_sprint(
    domain_id: str,
    *,
    matrix_doc: dict[str, Any] | None = None,
    review_packet_doc: dict[str, Any] | None = None,
    max_source_rows: int = 6,
) -> dict[str, Any]:
    """Return a compact source-review sprint packet for a domain."""
    domain_id = _safe_domain_id(domain_id)
    matrix_doc = matrix_doc or build_source_coverage_matrix(domain_id)
    review_packet_doc = review_packet_doc or build_source_review_packet(domain_id)
    source_by_id = _source_rows_by_id(review_packet_doc)
    scope_by_task = _scope_rows_by_task(review_packet_doc)

    matrix_rows = [
        row for row in matrix_doc.get("matrix_rows", [])
        if isinstance(row, dict)
    ]
    actionable_source_rows = [
        row for row in matrix_rows
        if row.get("scope_blocked") is False
    ][:max(0, max_source_rows)]
    deferred_source_rows = [
        _deferred_row(row)
        for row in matrix_rows
        if row.get("scope_blocked") is True
    ]
    source_sprint_rows = [
        _source_sprint_row(row, source_by_id[str(row["source_id"])])
        for row in actionable_source_rows
        if str(row.get("source_id")) in source_by_id
    ]
    scope_sprint_rows = [
        _scope_sprint_row(row, scope_by_task[str(row["task_id"])])
        for row in matrix_doc.get("scope_refinement_rows", [])
        if isinstance(row, dict) and str(row.get("task_id")) in scope_by_task
    ]
    missing_source_packet_rows = sorted({
        str(row.get("source_id"))
        for row in actionable_source_rows
        if str(row.get("source_id")) not in source_by_id
    })
    missing_scope_packet_rows = sorted({
        str(row.get("task_id"))
        for row in matrix_doc.get("scope_refinement_rows", [])
        if isinstance(row, dict) and str(row.get("task_id")) not in scope_by_task
    })
    checks = _checks(matrix_doc, review_packet_doc, source_sprint_rows, scope_sprint_rows)
    if missing_source_packet_rows:
        checks.append({
            "id": "selected_source_rows_exist_in_review_packet",
            "ok": False,
            "expected": [],
            "actual": missing_source_packet_rows,
        })
    if missing_scope_packet_rows:
        checks.append({
            "id": "selected_scope_rows_exist_in_review_packet",
            "ok": False,
            "expected": [],
            "actual": missing_scope_packet_rows,
        })
    source_by_band: dict[str, int] = {}
    for row in source_sprint_rows:
        band = row["priority_band"]
        source_by_band[band] = source_by_band.get(band, 0) + 1
    return {
        "_meta": {
            "domain": domain_id,
            "display_name": (matrix_doc.get("_meta") or {}).get("display_name"),
            "status": (
                "source-review sprint packet; not legal advice, not source verification, "
                "not manifest promotion, and not comparable benchmark evidence"
            ),
            "source_matrix_status": (matrix_doc.get("_meta") or {}).get("status"),
            "review_packet_status": (review_packet_doc.get("_meta") or {}).get("status"),
        },
        "summary": {
            "consistency_ok": all(check["ok"] for check in checks),
            "source_review_sprint_rows": len(source_sprint_rows),
            "scope_resolution_sprint_rows": len(scope_sprint_rows),
            "deferred_scope_blocked_source_rows": len(deferred_source_rows),
            "selected_source_rows_by_priority": {key: source_by_band[key] for key in sorted(source_by_band)},
            "all_source_rows_ready_for_manifest_promotion": False,
            "all_scope_rows_ready_for_source_queue_update": False,
            "ready_for_comparable_run": False,
            "policy": (
                "This sprint packet is an operations worklist only. Curators must fill the review "
                "packet with dated public-source metadata, privacy notes, and expert review before "
                "any manifest proposal or scoring claim."
            ),
        },
        "scope_resolution_sprint_rows": scope_sprint_rows,
        "source_review_sprint_rows": source_sprint_rows,
        "deferred_scope_blocked_source_rows": deferred_source_rows,
        "promotion_gates": list(review_packet_doc.get("promotion_gates") or []),
        "consistency_checks": checks,
    }


def default_out_path(domain_id: str) -> pathlib.Path:
    return OUT_DIR / f"{_safe_domain_id(domain_id)}_source_review_sprint.json"


def default_markdown_path(json_path: pathlib.Path) -> pathlib.Path:
    return json_path.with_suffix(".md")


def _md_cell(value: Any) -> str:
    text = str(value if value is not None else "")
    return text.replace("|", "\\|").replace("\n", " ").strip()


def _md_list(values: list[Any]) -> str:
    return ", ".join(_md_cell(v) for v in values) if values else "-"


def build_markdown_report(doc: dict[str, Any]) -> str:
    """Render a compact Markdown source-review sprint packet."""
    meta = doc["_meta"]
    summary = doc["summary"]
    lines: list[str] = [
        f"# Domain Source Review Sprint - {_md_cell(meta.get('display_name') or meta.get('domain'))}",
        "",
        (
            "This sprint packet is an operations worklist for source curation. It is not legal advice, "
            "not source verification, not manifest promotion, and not comparable benchmark evidence."
        ),
        "",
        "## Summary",
        "",
        "| Metric | Value |",
        "|---|---:|",
        f"| Consistency OK | {str(bool(summary['consistency_ok'])).lower()} |",
        f"| Source-review sprint rows | {summary['source_review_sprint_rows']} |",
        f"| Scope-resolution sprint rows | {summary['scope_resolution_sprint_rows']} |",
        f"| Deferred scope-blocked source rows | {summary['deferred_scope_blocked_source_rows']} |",
        f"| Ready for comparable run | {str(bool(summary['ready_for_comparable_run'])).lower()} |",
        "",
        "## Scope Resolution Sprint",
        "",
        "| Item | Scope | Category | Related cells | Blocked prompts |",
        "|---|---|---|---|---|",
    ]
    for row in doc["scope_resolution_sprint_rows"]:
        lines.append(
            f"| `{_md_cell(row['scope_task_id'])}` "
            f"| {_md_cell(row['scope'])} "
            f"| {_md_cell(row['category'])} "
            f"| {_md_list(row['related_coverage_cell_ids'])} "
            f"| {_md_list(row['blocked_prompt_ids'])} |"
        )
    lines.extend([
        "",
        "## Source Review Sprint",
        "",
        "| Item | Cell | Source ID | Priority | Status | Fields |",
        "|---|---|---|---|---|---:|",
    ])
    for row in doc["source_review_sprint_rows"]:
        lines.append(
            f"| `{_md_cell(row['source_task_id'])}` "
            f"| `{_md_cell(row['cell_id'])}` "
            f"| `{_md_cell(row['source_id'])}` "
            f"| `{_md_cell(row['priority_band'])}` "
            f"| {_md_cell(row['coverage_status'])} "
            f"| {len(row['fields_to_complete'])} |"
        )
    lines.extend([
        "",
        "## Deferred Scope-Blocked Source Rows",
        "",
        "| Cell | Source ID | Unresolved scopes | Scope tasks |",
        "|---|---|---|---|",
    ])
    for row in doc["deferred_scope_blocked_source_rows"]:
        lines.append(
            f"| `{_md_cell(row['cell_id'])}` "
            f"| `{_md_cell(row['source_id'])}` "
            f"| {_md_list(row['related_unresolved_scopes'])} "
            f"| {_md_list(row['related_scope_task_ids'])} |"
        )
    lines.extend([
        "",
        "## Promotion Gates",
        "",
    ])
    lines.extend(f"- {_md_cell(gate)}" for gate in doc["promotion_gates"])
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
    ap.add_argument("--matrix", type=pathlib.Path, default=None, help="optional prebuilt source-coverage matrix JSON")
    ap.add_argument("--review-packet", type=pathlib.Path, default=None, help="optional prebuilt blank source-review packet JSON")
    ap.add_argument("--max-source-rows", type=int, default=6)
    ap.add_argument("--out", type=pathlib.Path, default=None)
    ap.add_argument("--md-out", type=pathlib.Path, default=None, help="Markdown report path; defaults to --out with .md suffix")
    ap.add_argument("--no-md", action="store_true", help="write only JSON, not the Markdown sprint report")
    args = ap.parse_args(argv)

    matrix_doc = _load_json(args.matrix) if args.matrix else None
    review_packet_doc = _load_json(args.review_packet) if args.review_packet else None
    doc = build_source_review_sprint(
        args.domain,
        matrix_doc=matrix_doc,
        review_packet_doc=review_packet_doc,
        max_source_rows=args.max_source_rows,
    )
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
        f"wrote {out_path}: {summary['source_review_sprint_rows']} source-review rows; "
        f"{summary['scope_resolution_sprint_rows']} scope-resolution rows; "
        f"ready_for_comparable_run={str(bool(summary['ready_for_comparable_run'])).lower()}"
        + (f"; report {md_path}" if md_path else "")
    )
    return 0 if summary["consistency_ok"] else 1


if __name__ == "__main__":
    raise SystemExit(main())
