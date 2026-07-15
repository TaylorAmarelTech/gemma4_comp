#!/usr/bin/env python3
"""Build source-review intake templates from a domain source-research plan.

The source-research plan tells curators what to search for. This script turns
that plan into structured, blank intake rows for candidate source review and
scope resolution. It deliberately starts every source row in ``needs_review``
and marks every row as not ready for manifest promotion.
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

from build_domain_source_research_plan import build_source_research_plan  # noqa: E402

OUT_DIR = _ROOT / "reports" / "benchmark"
_SAFE_DOMAIN_ID = re.compile(r"^[a-z0-9_:-]{1,80}$")
_EMAIL = re.compile(r"\b[\w.+-]+@[\w-]+\.[\w.-]+\b", re.I)
_PHONE = re.compile(r"\+?\d[\d\s().\-]{8,}\d")
_LONG_DIGITS = re.compile(r"(?<!\d)\d{8,}(?!\d)")
_LOCAL_PATH_HINT = re.compile(r"(?:[A-Za-z]:[\\/]|\\\\|/(?:Users|home|tmp|var|mnt)(?:/|$)|~[\\/])", re.I)

_SOURCE_INTAKE_FIELDS = [
    "task_id",
    "source_id",
    "jurisdiction",
    "jurisdiction_label",
    "category",
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
    "proposed_manifest_verification_status",
    "ready_for_manifest_promotion",
    "privacy_review_required",
    "expert_review_required",
]

_SCOPE_INTAKE_FIELDS = [
    "task_id",
    "scope_id",
    "scope",
    "category",
    "resolved_jurisdictions",
    "resolved_forums_or_regulators",
    "origin_state_role",
    "destination_state_role",
    "flag_or_port_state_role",
    "source_ids_to_create",
    "resolution_note",
    "ready_for_source_queue_update",
    "expert_review_required",
]


def _safe_domain_id(domain_id: str) -> str:
    if not _SAFE_DOMAIN_ID.fullmatch(domain_id):
        raise ValueError(f"unsafe domain id: {domain_id!r}")
    return domain_id


def _slug(value: str) -> str:
    slug = re.sub(r"[^A-Za-z0-9]+", "-", value.strip()).strip("-").upper()
    return slug[:96] or "ROW"


def _source_row(task: dict[str, Any]) -> dict[str, Any]:
    return {
        "task_id": task["task_id"],
        "source_id": task["source_id"],
        "jurisdiction": task["jurisdiction"],
        "jurisdiction_label": task["jurisdiction_label"],
        "category": task["category"],
        "blocked_prompt_ids": list(task.get("blocked_prompt_ids") or []),
        "candidate_title": "",
        "candidate_authority": "",
        "candidate_url": "",
        "candidate_archive_url": "",
        "candidate_source_type": "",
        "candidate_publication_date": "",
        "candidate_accessed_date": "",
        "candidate_language": "",
        "official_or_public_interest": "",
        "legal_scope_note": "",
        "privacy_notes": "",
        "pii_risk": "unknown",
        "license_or_terms_note": "",
        "reviewer_notes": "",
        "proposed_manifest_verification_status": "needs_review",
        "ready_for_manifest_promotion": False,
        "privacy_review_required": True,
        "expert_review_required": True,
        "search_queries": list(task.get("search_queries") or []),
        "required_source_types": list(task.get("required_source_types") or []),
        "reject_if": list(task.get("reject_if") or []),
        "manifest_fields_to_fill": list(task.get("manifest_fields_to_fill") or []),
    }


def _scope_row(task: dict[str, Any]) -> dict[str, Any]:
    return {
        "task_id": task["task_id"],
        "scope_id": task.get("scope_id") or f"SCOPE-{_slug(task.get('scope', ''))}-{_slug(task.get('category', ''))}",
        "scope": task["scope"],
        "category": task["category"],
        "blocked_prompt_ids": list(task.get("blocked_prompt_ids") or []),
        "resolved_jurisdictions": [],
        "resolved_forums_or_regulators": [],
        "origin_state_role": "",
        "destination_state_role": "",
        "flag_or_port_state_role": "",
        "source_ids_to_create": [],
        "resolution_note": "",
        "ready_for_source_queue_update": False,
        "expert_review_required": True,
        "research_questions": list(task.get("research_questions") or []),
        "search_queries": list(task.get("search_queries") or []),
        "acceptance_checks": list(task.get("acceptance_checks") or []),
        "reject_if": list(task.get("reject_if") or []),
    }


def _privacy_scan(value: Any) -> dict[str, Any]:
    findings: dict[str, list[str]] = {
        "email_like_paths": [],
        "phone_like_paths": [],
        "long_digit_paths": [],
        "local_path_like_paths": [],
    }

    def walk(node: Any, path: str) -> None:
        if isinstance(node, dict):
            for key, item in node.items():
                walk(item, f"{path}.{key}")
        elif isinstance(node, list):
            for index, item in enumerate(node):
                walk(item, f"{path}[{index}]")
        elif isinstance(node, str):
            if _EMAIL.search(node):
                findings["email_like_paths"].append(path)
            if _PHONE.search(node):
                findings["phone_like_paths"].append(path)
            if _LONG_DIGITS.search(node):
                findings["long_digit_paths"].append(path)
            if _LOCAL_PATH_HINT.search(node):
                findings["local_path_like_paths"].append(path)

    walk(value, "$")
    counts = {key.replace("_paths", ""): len(paths) for key, paths in findings.items()}
    return {**findings, "counts": counts, "ok": not any(counts.values())}


def validate_review_packet(doc: dict[str, Any]) -> dict[str, Any]:
    """Return a fail-closed safety summary for blank review packets."""
    issues: list[str] = []
    source_rows = doc.get("source_candidate_intake_rows", [])
    scope_rows = doc.get("scope_resolution_intake_rows", [])
    if not isinstance(source_rows, list):
        issues.append("source_candidate_intake_rows_not_list")
        source_rows = []
    if not isinstance(scope_rows, list):
        issues.append("scope_resolution_intake_rows_not_list")
        scope_rows = []
    for i, row in enumerate(source_rows):
        if not isinstance(row, dict):
            issues.append(f"source_row_{i}_not_object")
            continue
        if row.get("proposed_manifest_verification_status") != "needs_review":
            issues.append(f"{row.get('task_id', i)}: source row must start as needs_review")
        if row.get("ready_for_manifest_promotion") is not False:
            issues.append(f"{row.get('task_id', i)}: source row cannot start ready for promotion")
        for field in (
            "candidate_title",
            "candidate_authority",
            "candidate_url",
            "candidate_archive_url",
            "candidate_publication_date",
            "candidate_accessed_date",
        ):
            if row.get(field):
                issues.append(f"{row.get('task_id', i)}: template field {field} must start blank")
    for i, row in enumerate(scope_rows):
        if not isinstance(row, dict):
            issues.append(f"scope_row_{i}_not_object")
            continue
        if row.get("ready_for_source_queue_update") is not False:
            issues.append(f"{row.get('task_id', i)}: scope row cannot start ready for queue update")
        if row.get("resolved_jurisdictions"):
            issues.append(f"{row.get('task_id', i)}: resolved_jurisdictions must start blank")
    privacy_scan = _privacy_scan({
        "source_candidate_intake_rows": source_rows,
        "scope_resolution_intake_rows": scope_rows,
    })
    if privacy_scan["ok"] is not True:
        issues.append("review_packet_privacy_scan_not_ok")
    return {
        "ok": not issues,
        "issues": issues,
        "privacy_scan": privacy_scan,
        "source_candidate_rows": len(source_rows),
        "scope_resolution_rows": len(scope_rows),
    }


def build_source_review_packet(
    domain_id: str,
    *,
    source_plan_doc: dict[str, Any] | None = None,
) -> dict[str, Any]:
    """Return blank intake rows for candidate source and scope review."""
    domain_id = _safe_domain_id(domain_id)
    plan = source_plan_doc or build_source_research_plan(domain_id)
    source_rows = [
        _source_row(task)
        for task in plan.get("source_research_tasks", [])
        if isinstance(task, dict)
    ]
    scope_rows = [
        _scope_row(task)
        for task in plan.get("scope_refinement_tasks", [])
        if isinstance(task, dict)
    ]
    doc = {
        "_meta": {
            "domain": domain_id,
            "display_name": plan.get("_meta", {}).get("display_name"),
            "status": (
                "blank source-review intake packet; not legal advice, not source verification, "
                "and not manifest promotion"
            ),
            "source_plan_status": plan.get("_meta", {}).get("status"),
            "review_rule": (
                "Rows must remain needs_review until dated source metadata, privacy review, "
                "and practitioner/domain-expert review support a manifest update."
            ),
        },
        "summary": {
            "source_candidate_rows": len(source_rows),
            "scope_resolution_rows": len(scope_rows),
            "default_ready_for_manifest_promotion": 0,
            "default_ready_for_source_queue_update": 0,
            "policy": (
                "Fill these rows with public source metadata only. Do not paste worker names, "
                "contacts, complainant rows, private case details, or raw intake text."
            ),
        },
        "source_candidate_intake_schema": _SOURCE_INTAKE_FIELDS,
        "scope_resolution_intake_schema": _SCOPE_INTAKE_FIELDS,
        "source_candidate_intake_rows": source_rows,
        "scope_resolution_intake_rows": scope_rows,
        "promotion_gates": [
            "candidate source is public, stable, dated, and citable",
            "candidate source does not expose worker, complainant, or private case PII",
            "jurisdiction, worker class, sector, and date range match the benchmark prompt category",
            "informal or social-channel source has archive/date trail and corroboration",
            "domain expert or practitioner has approved the manifest-row promotion",
        ],
    }
    doc["safety_audit"] = validate_review_packet(doc)
    return doc


def default_out_path(domain_id: str) -> pathlib.Path:
    return OUT_DIR / f"{_safe_domain_id(domain_id)}_source_review_packet.json"


def default_markdown_path(json_path: pathlib.Path) -> pathlib.Path:
    return json_path.with_suffix(".md")


def _md_cell(value: Any) -> str:
    text = str(value if value is not None else "")
    return text.replace("|", "\\|").replace("\n", " ").strip()


def _md_list(values: list[Any]) -> str:
    return ", ".join(_md_cell(v) for v in values) if values else "-"


def build_markdown_report(doc: dict[str, Any]) -> str:
    """Render a Markdown review-packet summary."""
    meta = doc["_meta"]
    summary = doc["summary"]
    audit = doc["safety_audit"]
    lines: list[str] = [
        f"# Domain Source Review Packet - {_md_cell(meta.get('display_name') or meta.get('domain'))}",
        "",
        (
            "This packet contains blank source and scope intake rows. It is not legal advice, "
            "not a verification result, and not manifest promotion."
        ),
        "",
        "## Summary",
        "",
        "| Metric | Value |",
        "|---|---:|",
        f"| Source candidate rows | {summary['source_candidate_rows']} |",
        f"| Scope resolution rows | {summary['scope_resolution_rows']} |",
        f"| Rows ready for manifest promotion by default | {summary['default_ready_for_manifest_promotion']} |",
        f"| Rows ready for source-queue update by default | {summary['default_ready_for_source_queue_update']} |",
        f"| Safety audit issues | {len(audit['issues'])} |",
        "",
        "## Promotion Gates",
        "",
    ]
    lines.extend(f"- {_md_cell(gate)}" for gate in doc["promotion_gates"])
    lines.extend([
        "",
        "## Source Candidate Rows",
        "",
        "| Task | Source ID | Jurisdiction | Category | Status | Ready | Blocked prompts |",
        "|---|---|---|---|---|---:|---|",
    ])
    for row in doc["source_candidate_intake_rows"]:
        lines.append(
            f"| `{_md_cell(row['task_id'])}` "
            f"| `{_md_cell(row['source_id'])}` "
            f"| {_md_cell(row['jurisdiction_label'])} "
            f"| {_md_cell(row['category'])} "
            f"| {_md_cell(row['proposed_manifest_verification_status'])} "
            f"| {str(bool(row['ready_for_manifest_promotion'])).lower()} "
            f"| {_md_list(row['blocked_prompt_ids'])} |"
        )
    lines.extend([
        "",
        "## Scope Resolution Rows",
        "",
        "| Task | Scope | Category | Ready | Blocked prompts |",
        "|---|---|---|---:|---|",
    ])
    for row in doc["scope_resolution_intake_rows"]:
        lines.append(
            f"| `{_md_cell(row['task_id'])}` "
            f"| {_md_cell(row['scope'])} "
            f"| {_md_cell(row['category'])} "
            f"| {str(bool(row['ready_for_source_queue_update'])).lower()} "
            f"| {_md_list(row['blocked_prompt_ids'])} |"
        )
    lines.extend([
        "",
        "## Intake Schemas",
        "",
        f"- Source candidate fields: `{_md_list(doc['source_candidate_intake_schema'])}`",
        f"- Scope resolution fields: `{_md_list(doc['scope_resolution_intake_schema'])}`",
        "",
    ])
    return "\n".join(lines)


def _load_plan(path: pathlib.Path) -> dict[str, Any]:
    doc = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(doc, dict):
        raise ValueError(f"source plan file must contain a JSON object: {path}")
    return doc


def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--domain", default="developing_country_worker_protections")
    ap.add_argument("--source-plan", type=pathlib.Path, default=None, help="optional prebuilt source-research plan JSON")
    ap.add_argument("--out", type=pathlib.Path, default=None)
    ap.add_argument("--md-out", type=pathlib.Path, default=None, help="Markdown report path; defaults to --out with .md suffix")
    ap.add_argument("--no-md", action="store_true", help="write only JSON, not the Markdown review report")
    args = ap.parse_args(argv)

    plan_doc = _load_plan(args.source_plan) if args.source_plan else None
    doc = build_source_review_packet(args.domain, source_plan_doc=plan_doc)
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
        f"wrote {out_path}: {summary['source_candidate_rows']} source candidate rows; "
        f"{summary['scope_resolution_rows']} scope resolution rows"
        + (f"; report {md_path}" if md_path else "")
    )
    return 0 if doc["safety_audit"]["ok"] else 1


if __name__ == "__main__":
    raise SystemExit(main())
