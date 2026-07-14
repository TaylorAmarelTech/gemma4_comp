#!/usr/bin/env python3
"""Validate filled source-review packets before manifest promotion.

This validator is the gate after ``build_domain_source_review_packet.py``. It
does not edit the grounding manifest. It reads a curator-filled review packet,
checks any claimed promotion rows, and emits proposed manifest rows only for
source candidates that pass date, source, privacy, and expert-review checks.
"""
from __future__ import annotations

import argparse
import datetime as _dt
import json
import pathlib
import re
import sys
from typing import Any

_ROOT = pathlib.Path(__file__).resolve().parents[1]
_SCRIPTS = pathlib.Path(__file__).resolve().parent
if str(_SCRIPTS) not in sys.path:
    sys.path.insert(0, str(_SCRIPTS))

OUT_DIR = _ROOT / "reports" / "benchmark"
_SAFE_DOMAIN_ID = re.compile(r"^[a-z0-9_:-]{1,80}$")
_HTTPS_URL = re.compile(r"^https://", re.IGNORECASE)
_EMAIL = re.compile(r"\b[\w.+-]+@[\w-]+\.[\w.-]+\b", re.I)
_PHONE = re.compile(r"\+?\d[\d\s().\-]{8,}\d")
_LONG_DIGITS = re.compile(r"(?<!\d)\d{8,}(?!\d)")
_LOCAL_PATH_HINT = re.compile(r"(?:[A-Za-z]:[\\/]|\\\\|/(?:Users|home|tmp|var|mnt)(?:/|$)|~[\\/])", re.I)
_ALLOWED_PROMOTION_STATUSES = {"verified_local_law"}
_ALLOWED_SOURCE_CLASSES = {"official", "public_interest_with_citation_trail"}

_REQUIRED_PROMOTION_FIELDS = (
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
)

_PII_SCANNED_SOURCE_FIELDS = (
    "candidate_title",
    "candidate_authority",
    "candidate_source_type",
    "candidate_language",
    "official_or_public_interest",
    "legal_scope_note",
    "privacy_notes",
    "license_or_terms_note",
    "reviewer_notes",
)

_PII_SCANNED_SCOPE_FIELDS = (
    "scope",
    "category",
    "origin_state_role",
    "destination_state_role",
    "flag_or_port_state_role",
    "resolution_note",
)


def _safe_domain_id(domain_id: str) -> str:
    if not _SAFE_DOMAIN_ID.fullmatch(domain_id):
        raise ValueError(f"unsafe domain id: {domain_id!r}")
    return domain_id


def _clean_text(value: Any, *, max_len: int = 500) -> str:
    if not isinstance(value, str):
        return ""
    return " ".join(value.split())[:max_len]


def _date_ok(value: Any) -> bool:
    if not isinstance(value, str) or not value.strip():
        return False
    try:
        _dt.date.fromisoformat(value)
    except ValueError:
        return False
    return True


def _privacy_findings(fields: dict[str, Any], *, prefix: str) -> list[str]:
    findings: list[str] = []
    for key, value in fields.items():
        if not isinstance(value, str):
            continue
        path = f"{prefix}.{key}"
        if _EMAIL.search(value):
            findings.append(f"{path}: email_like_text")
        if _PHONE.search(value):
            findings.append(f"{path}: phone_like_text")
        if _LONG_DIGITS.search(value):
            findings.append(f"{path}: long_digit_text")
        if _LOCAL_PATH_HINT.search(value):
            findings.append(f"{path}: local_path_like_text")
    return findings


def _ready_claimed(row: dict[str, Any]) -> bool:
    return (
        row.get("ready_for_manifest_promotion") is True
        or row.get("proposed_manifest_verification_status") in _ALLOWED_PROMOTION_STATUSES
    )


def _candidate_manifest_row(row: dict[str, Any]) -> dict[str, Any]:
    accessed = _clean_text(row.get("candidate_accessed_date"), max_len=20)
    title = _clean_text(row.get("candidate_title"), max_len=240)
    legal_scope = _clean_text(row.get("legal_scope_note"), max_len=360)
    return {
        "id": _clean_text(row.get("source_id"), max_len=120),
        "title": title,
        "jurisdiction": _clean_text(row.get("jurisdiction"), max_len=80),
        "source_type": _clean_text(row.get("candidate_source_type"), max_len=80),
        "authority": _clean_text(row.get("candidate_authority"), max_len=160),
        "url": _clean_text(row.get("candidate_url"), max_len=500),
        "verification_status": "verified_local_law",
        "verified_date": accessed,
        "coverage_tags": [_clean_text(row.get("category"), max_len=120)],
        "use_limitations": (
            f"Local-law/source row proposed from review packet. "
            f"Accessed {accessed}. Scope note: {legal_scope}"
        )[:500],
    }


def _validate_source_row(row: dict[str, Any], index: int) -> dict[str, Any]:
    task_id = _clean_text(row.get("task_id"), max_len=120) or f"source_row_{index}"
    issues: list[str] = []
    warnings: list[str] = []
    ready_claimed = _ready_claimed(row)
    for field in ("task_id", "source_id", "jurisdiction", "category"):
        if not _clean_text(row.get(field)):
            issues.append(f"{field}_missing")
    if not ready_claimed:
        return {
            "task_id": task_id,
            "source_id": row.get("source_id"),
            "ready_claimed": False,
            "accepted_for_manifest_proposal": False,
            "issues": issues,
            "warnings": warnings,
        }

    for field in _REQUIRED_PROMOTION_FIELDS:
        if not _clean_text(row.get(field)):
            issues.append(f"{field}_required_for_promotion")
    if row.get("proposed_manifest_verification_status") not in _ALLOWED_PROMOTION_STATUSES:
        issues.append("proposed_manifest_verification_status_must_be_verified_local_law")
    if row.get("ready_for_manifest_promotion") is not True:
        issues.append("ready_for_manifest_promotion_must_be_true")
    if row.get("privacy_review_required") is not False:
        issues.append("privacy_review_required_must_be_false_after_review")
    if row.get("expert_review_required") is not False:
        issues.append("expert_review_required_must_be_false_after_review")
    if _clean_text(row.get("candidate_source_type")) == "country_law_placeholder":
        issues.append("candidate_source_type_cannot_be_country_law_placeholder")
    if not _HTTPS_URL.match(_clean_text(row.get("candidate_url"))):
        issues.append("candidate_url_must_be_https")
    archive_url = _clean_text(row.get("candidate_archive_url"))
    if archive_url and not _HTTPS_URL.match(archive_url):
        issues.append("candidate_archive_url_must_be_https_when_present")
    if not _date_ok(row.get("candidate_publication_date")):
        issues.append("candidate_publication_date_must_be_yyyy_mm_dd")
    if not _date_ok(row.get("candidate_accessed_date")):
        issues.append("candidate_accessed_date_must_be_yyyy_mm_dd")
    if row.get("official_or_public_interest") not in _ALLOWED_SOURCE_CLASSES:
        issues.append("official_or_public_interest_must_be_allowed_value")
    if row.get("pii_risk") not in {"none_detected", "none"}:
        issues.append("pii_risk_must_be_none_detected")
    privacy_findings = _privacy_findings(
        {field: row.get(field) for field in _PII_SCANNED_SOURCE_FIELDS},
        prefix=task_id,
    )
    issues.extend(privacy_findings)
    candidate = None if issues else _candidate_manifest_row(row)
    return {
        "task_id": task_id,
        "source_id": row.get("source_id"),
        "ready_claimed": True,
        "accepted_for_manifest_proposal": candidate is not None,
        "issues": issues,
        "warnings": warnings,
        "candidate_manifest_row": candidate,
    }


def _scope_ready_claimed(row: dict[str, Any]) -> bool:
    return row.get("ready_for_source_queue_update") is True


def _validate_scope_row(row: dict[str, Any], index: int) -> dict[str, Any]:
    task_id = _clean_text(row.get("task_id"), max_len=120) or f"scope_row_{index}"
    issues: list[str] = []
    ready_claimed = _scope_ready_claimed(row)
    if not ready_claimed:
        return {
            "task_id": task_id,
            "scope_id": row.get("scope_id"),
            "ready_claimed": False,
            "accepted_for_source_queue_update": False,
            "issues": issues,
        }
    resolved = row.get("resolved_jurisdictions")
    forums = row.get("resolved_forums_or_regulators")
    source_ids = row.get("source_ids_to_create")
    if not isinstance(resolved, list) or not resolved or not all(isinstance(v, str) and v.strip() for v in resolved):
        issues.append("resolved_jurisdictions_required")
    if not isinstance(forums, list) or not forums or not all(isinstance(v, str) and v.strip() for v in forums):
        issues.append("resolved_forums_or_regulators_required")
    if not isinstance(source_ids, list) or not source_ids or not all(isinstance(v, str) and v.strip() for v in source_ids):
        issues.append("source_ids_to_create_required")
    if not _clean_text(row.get("resolution_note")):
        issues.append("resolution_note_required")
    if row.get("expert_review_required") is not False:
        issues.append("expert_review_required_must_be_false_after_review")
    issues.extend(_privacy_findings(
        {field: row.get(field) for field in _PII_SCANNED_SCOPE_FIELDS},
        prefix=task_id,
    ))
    candidate = None
    if not issues:
        candidate = {
            "scope_id": row.get("scope_id"),
            "scope": row.get("scope"),
            "category": row.get("category"),
            "resolved_jurisdictions": resolved,
            "resolved_forums_or_regulators": forums,
            "source_ids_to_create": source_ids,
            "resolution_note": _clean_text(row.get("resolution_note"), max_len=500),
        }
    return {
        "task_id": task_id,
        "scope_id": row.get("scope_id"),
        "ready_claimed": True,
        "accepted_for_source_queue_update": candidate is not None,
        "issues": issues,
        "scope_update_candidate": candidate,
    }


def validate_source_review_packet(doc: dict[str, Any], *, domain_id: str | None = None) -> dict[str, Any]:
    """Validate a filled review packet and return non-mutating proposals."""
    meta = doc.get("_meta") if isinstance(doc, dict) else {}
    domain = domain_id or (meta.get("domain") if isinstance(meta, dict) else None) or "unknown"
    source_rows = doc.get("source_candidate_intake_rows", []) if isinstance(doc, dict) else []
    scope_rows = doc.get("scope_resolution_intake_rows", []) if isinstance(doc, dict) else []
    root_issues: list[str] = []
    if not isinstance(source_rows, list):
        root_issues.append("source_candidate_intake_rows_not_list")
        source_rows = []
    if not isinstance(scope_rows, list):
        root_issues.append("scope_resolution_intake_rows_not_list")
        scope_rows = []

    source_results = [
        _validate_source_row(row, i) if isinstance(row, dict) else {
            "task_id": f"source_row_{i}",
            "ready_claimed": False,
            "accepted_for_manifest_proposal": False,
            "issues": ["source_row_not_object"],
            "warnings": [],
        }
        for i, row in enumerate(source_rows)
    ]
    scope_results = [
        _validate_scope_row(row, i) if isinstance(row, dict) else {
            "task_id": f"scope_row_{i}",
            "ready_claimed": False,
            "accepted_for_source_queue_update": False,
            "issues": ["scope_row_not_object"],
        }
        for i, row in enumerate(scope_rows)
    ]
    candidate_manifest_rows = [
        result["candidate_manifest_row"]
        for result in source_results
        if result.get("candidate_manifest_row")
    ]
    scope_update_candidates = [
        result["scope_update_candidate"]
        for result in scope_results
        if result.get("scope_update_candidate")
    ]
    source_ready_claimed = sum(1 for result in source_results if result.get("ready_claimed"))
    source_accepted = len(candidate_manifest_rows)
    scope_ready_claimed = sum(1 for result in scope_results if result.get("ready_claimed"))
    scope_accepted = len(scope_update_candidates)
    blocked_ready_source = [
        result["task_id"] for result in source_results
        if result.get("ready_claimed") and not result.get("accepted_for_manifest_proposal")
    ]
    blocked_ready_scope = [
        result["task_id"] for result in scope_results
        if result.get("ready_claimed") and not result.get("accepted_for_source_queue_update")
    ]
    all_issues = [
        issue
        for result in [*source_results, *scope_results]
        for issue in result.get("issues", [])
    ]
    ok = not root_issues and not blocked_ready_source and not blocked_ready_scope and not any(
        result.get("issues") and not result.get("ready_claimed")
        for result in [*source_results, *scope_results]
    )
    return {
        "_meta": {
            "domain": domain,
            "status": (
                "source-review validation report; proposed rows only, no grounding manifest mutation"
            ),
            "source_packet_status": meta.get("status") if isinstance(meta, dict) else None,
        },
        "summary": {
            "ok": ok,
            "source_rows": len(source_rows),
            "source_rows_ready_claimed": source_ready_claimed,
            "source_rows_accepted_for_manifest_proposal": source_accepted,
            "source_rows_blocked_after_ready_claim": len(blocked_ready_source),
            "scope_rows": len(scope_rows),
            "scope_rows_ready_claimed": scope_ready_claimed,
            "scope_rows_accepted_for_queue_update": scope_accepted,
            "scope_rows_blocked_after_ready_claim": len(blocked_ready_scope),
            "root_issue_count": len(root_issues),
            "row_issue_count": len(all_issues),
            "policy": (
                "A passing validation report is still propose-only. Human review must apply any "
                "manifest change deliberately; this command never mutates grounding_sources.json."
            ),
        },
        "root_issues": root_issues,
        "source_row_results": source_results,
        "scope_row_results": scope_results,
        "candidate_manifest_rows": candidate_manifest_rows,
        "scope_update_candidates": scope_update_candidates,
    }


def default_packet_path(domain_id: str) -> pathlib.Path:
    return OUT_DIR / f"{_safe_domain_id(domain_id)}_source_review_packet.json"


def default_out_path(domain_id: str) -> pathlib.Path:
    return OUT_DIR / f"{_safe_domain_id(domain_id)}_source_review_validation.json"


def default_markdown_path(json_path: pathlib.Path) -> pathlib.Path:
    return json_path.with_suffix(".md")


def _md_cell(value: Any) -> str:
    text = str(value if value is not None else "")
    return text.replace("|", "\\|").replace("\n", " ").strip()


def _md_list(values: list[Any]) -> str:
    return ", ".join(_md_cell(v) for v in values) if values else "-"


def build_markdown_report(doc: dict[str, Any]) -> str:
    """Render a Markdown validation report."""
    meta = doc["_meta"]
    summary = doc["summary"]
    lines: list[str] = [
        f"# Domain Source Review Validation - {_md_cell(meta.get('domain'))}",
        "",
        (
            "This report is propose-only. It validates filled review-packet rows "
            "and never mutates the grounding manifest."
        ),
        "",
        "## Summary",
        "",
        "| Metric | Value |",
        "|---|---:|",
        f"| OK | {str(bool(summary['ok'])).lower()} |",
        f"| Source rows | {summary['source_rows']} |",
        f"| Source rows ready claimed | {summary['source_rows_ready_claimed']} |",
        f"| Source rows accepted for manifest proposal | {summary['source_rows_accepted_for_manifest_proposal']} |",
        f"| Source rows blocked after ready claim | {summary['source_rows_blocked_after_ready_claim']} |",
        f"| Scope rows | {summary['scope_rows']} |",
        f"| Scope rows ready claimed | {summary['scope_rows_ready_claimed']} |",
        f"| Scope rows accepted for queue update | {summary['scope_rows_accepted_for_queue_update']} |",
        f"| Scope rows blocked after ready claim | {summary['scope_rows_blocked_after_ready_claim']} |",
        f"| Row issue count | {summary['row_issue_count']} |",
        "",
        "## Candidate Manifest Rows",
        "",
        "| Source ID | Jurisdiction | Type | Authority | Coverage tags |",
        "|---|---|---|---|---|",
    ]
    if doc["candidate_manifest_rows"]:
        for row in doc["candidate_manifest_rows"]:
            lines.append(
                f"| `{_md_cell(row['id'])}` "
                f"| {_md_cell(row['jurisdiction'])} "
                f"| {_md_cell(row['source_type'])} "
                f"| {_md_cell(row['authority'])} "
                f"| {_md_list(row['coverage_tags'])} |"
            )
    else:
        lines.append("| - | - | - | - | - |")
    lines.extend([
        "",
        "## Blocked Ready Claims",
        "",
        "| Task | Kind | Issues |",
        "|---|---|---|",
    ])
    blocked = False
    for result in doc["source_row_results"]:
        if result.get("ready_claimed") and result.get("issues"):
            blocked = True
            lines.append(f"| `{_md_cell(result['task_id'])}` | source | {_md_list(result['issues'])} |")
    for result in doc["scope_row_results"]:
        if result.get("ready_claimed") and result.get("issues"):
            blocked = True
            lines.append(f"| `{_md_cell(result['task_id'])}` | scope | {_md_list(result['issues'])} |")
    if not blocked:
        lines.append("| - | - | - |")
    lines.append("")
    return "\n".join(lines)


def _load_packet(path: pathlib.Path) -> dict[str, Any]:
    doc = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(doc, dict):
        raise ValueError(f"source review packet must contain a JSON object: {path}")
    return doc


def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--domain", default="developing_country_worker_protections")
    ap.add_argument("--packet", type=pathlib.Path, default=None)
    ap.add_argument("--out", type=pathlib.Path, default=None)
    ap.add_argument("--md-out", type=pathlib.Path, default=None, help="Markdown report path; defaults to --out with .md suffix")
    ap.add_argument("--no-md", action="store_true", help="write only JSON, not the Markdown validation report")
    args = ap.parse_args(argv)

    domain_id = _safe_domain_id(args.domain)
    packet_path = args.packet or default_packet_path(domain_id)
    doc = validate_source_review_packet(_load_packet(packet_path), domain_id=domain_id)
    out_path = args.out or default_out_path(domain_id)
    out_path.parent.mkdir(parents=True, exist_ok=True)
    out_path.write_text(json.dumps(doc, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
    md_path = None
    if not args.no_md:
        md_path = args.md_out or default_markdown_path(out_path)
        md_path.parent.mkdir(parents=True, exist_ok=True)
        md_path.write_text(build_markdown_report(doc) + "\n", encoding="utf-8")
    summary = doc["summary"]
    print(
        f"wrote {out_path}: {summary['source_rows_accepted_for_manifest_proposal']} "
        f"source proposals; {summary['scope_rows_accepted_for_queue_update']} scope updates; "
        f"ok={str(bool(summary['ok'])).lower()}"
        + (f"; report {md_path}" if md_path else "")
    )
    return 0 if summary["ok"] else 1


if __name__ == "__main__":
    raise SystemExit(main())
