#!/usr/bin/env python3
"""Validate filled dimension-candidate review packets before rubric promotion.

This is the gate after ``build_dimension_candidate_review_packet.py``. It reads
a curator-filled packet and emits propose-only rubric rows for candidates that
pass source, applicability, privacy, and expert-review checks. It never mutates
the research-spider artifacts or active rubric.
"""
from __future__ import annotations

import argparse
import hashlib
import json
import pathlib
import re
import sys
from typing import Any

_ROOT = pathlib.Path(__file__).resolve().parents[1]
_SCRIPTS = pathlib.Path(__file__).resolve().parent
if str(_SCRIPTS) not in sys.path:
    sys.path.insert(0, str(_SCRIPTS))

from artifact_path_policy import handoff_artifact_path  # noqa: E402

OUT_DIR = _ROOT / "reports" / "benchmark"

_EXPECTED_PACKET_SCHEMA_VERSION = "dimension_candidate_review_packet.v1"
_DIMENSION_ID = re.compile(r"^[a-z][a-z0-9_]*(?:\.[a-z0-9_]+)+$")
_SAFE_GROUP = re.compile(r"^[a-z][a-z0-9_]{1,80}$")
_PUBLIC_KNOWLEDGE_ID = re.compile(r"^KNOW-PUBLIC-[A-F0-9]{10}$")
_EMAIL = re.compile(r"\b[\w.+-]+@[\w-]+\.[\w.-]+\b", re.I)
_PHONE = re.compile(r"\+?\d[\d\s().\-]{8,}\d")
_LONG_DIGITS = re.compile(r"\b\d{9,}\b")
_LOCAL_PATH_HINT = re.compile(r"(?:[A-Za-z]:[\\/]|\\\\|/(?:Users|home|tmp|var|mnt)(?:/|$)|~[\\/])", re.I)

_APPROVED_STATUS = "approved_for_rubric_merge"
_ALLOWED_REVIEW_STATUSES = {
    "needs_curator_review",
    "needs_more_source_review",
    "rejected",
    _APPROVED_STATUS,
}
_PII_SCANNED_FIELDS = (
    "name",
    "rubric_prompt",
    "positive_criteria",
    "negative_controls",
    "applicability_notes",
    "source_corroboration_notes",
    "privacy_notes",
    "expert_notes",
    "reject_reason",
)


def _sha256_file(path: pathlib.Path) -> str:
    h = hashlib.sha256()
    with path.open("rb") as fh:
        for chunk in iter(lambda: fh.read(1024 * 1024), b""):
            h.update(chunk)
    return h.hexdigest()


def _display_path(path: pathlib.Path) -> str:
    return handoff_artifact_path(path, root=_ROOT)


def _clean(value: Any, *, max_len: int = 500) -> str:
    if not isinstance(value, str):
        return ""
    return " ".join(value.split())[:max_len]


def _clean_list(value: Any, *, max_items: int = 12, max_len: int = 240) -> list[str]:
    if not isinstance(value, list):
        return []
    out: list[str] = []
    for item in value[:max_items]:
        text = _clean(item, max_len=max_len)
        if text:
            out.append(text)
    return out


def _text_list_shape_issues(value: Any, field: str) -> list[str]:
    if not isinstance(value, list):
        return [f"{field}_must_be_list"]
    issues: list[str] = []
    for index, item in enumerate(value):
        if not isinstance(item, str) or not _clean(item):
            issues.append(f"{field}[{index}]_must_be_non_empty_string")
    return issues


def _privacy_findings(fields: dict[str, Any], *, prefix: str) -> list[str]:
    findings: list[str] = []

    def walk(value: Any, path: str) -> None:
        if isinstance(value, dict):
            for key, item in value.items():
                walk(item, f"{path}.{key}")
        elif isinstance(value, list):
            for index, item in enumerate(value):
                walk(item, f"{path}[{index}]")
        elif isinstance(value, str):
            if _EMAIL.search(value):
                findings.append(f"{path}: email_like_text")
            if _PHONE.search(value):
                findings.append(f"{path}: phone_like_text")
            if _LONG_DIGITS.search(value):
                findings.append(f"{path}: long_digit_text")
            if _LOCAL_PATH_HINT.search(value):
                findings.append(f"{path}: local_path_like_text")

    for key, value in fields.items():
        walk(value, f"{prefix}.{key}")
    return findings


def _ready_claimed(row: dict[str, Any]) -> bool:
    return row.get("ready_for_rubric_promotion") is True or row.get("review_status") == _APPROVED_STATUS


def _has_control(values: list[str], *needles: str) -> bool:
    text = " ".join(values).lower()
    return any(needle in text for needle in needles)


def _proposal_row(row: dict[str, Any]) -> dict[str, Any]:
    approved_id = _clean(row.get("approved_dimension_id"), max_len=160)
    group = _clean(row.get("merge_target_group"), max_len=120)
    return {
        "id": approved_id,
        "group": group,
        "name": _clean(row.get("name"), max_len=240),
        "rubric_prompt": _clean(row.get("rubric_prompt"), max_len=500),
        "positive_criteria": _clean_list(row.get("positive_criteria")),
        "negative_controls": _clean_list(row.get("negative_controls")),
        "source_family": _clean(row.get("source_family"), max_len=160),
        "source_knowledge_object_id": _clean(row.get("source_knowledge_object_id"), max_len=120),
        "candidate_dim_id": _clean(row.get("candidate_dim_id"), max_len=200),
        "verification_status": "curator_approved_public_source_pattern",
        "use_limitations": (
            "Propose-only rubric dimension derived from public-source metadata. "
            f"Applicability: {_clean(row.get('applicability_notes'), max_len=260)}"
        )[:500],
    }


def _packet_level_root_issues(doc: Any) -> list[str]:
    if not isinstance(doc, dict):
        return ["packet_not_object"]
    issues: list[str] = []
    packet_meta = doc.get("_meta")
    if not isinstance(packet_meta, dict):
        issues.append("packet_meta_missing_or_not_object")
    elif packet_meta.get("schema_version") != _EXPECTED_PACKET_SCHEMA_VERSION:
        issues.append("packet_schema_version_must_be_dimension_candidate_review_packet_v1")
    safety_audit = doc.get("safety_audit")
    if safety_audit is None:
        issues.append("packet_safety_audit_missing")
    elif not isinstance(safety_audit, dict):
        issues.append("packet_safety_audit_not_object")
    elif safety_audit.get("ok") is not True:
        issues.append("packet_safety_audit_not_ok")
    source_candidate_audit = doc.get("source_candidate_audit")
    if source_candidate_audit is None:
        issues.append("source_candidate_audit_missing")
    elif not isinstance(source_candidate_audit, dict):
        issues.append("source_candidate_audit_not_object")
    elif source_candidate_audit.get("ok") is not True:
        issues.append("source_candidate_audit_not_ok")
    return issues


def _validate_row(row: dict[str, Any], index: int) -> dict[str, Any]:
    review_id = _clean(row.get("review_id"), max_len=160) or f"row_{index}"
    issues: list[str] = []
    warnings: list[str] = []
    ready_claimed = _ready_claimed(row)
    review_status = _clean(row.get("review_status"), max_len=80)

    for field in (
        "dimension_candidate_id",
        "candidate_dim_id",
        "group",
        "source_family",
        "source_knowledge_object_id",
        "rubric_prompt",
    ):
        if not _clean(row.get(field)):
            issues.append(f"{field}_missing")
    if review_status not in _ALLOWED_REVIEW_STATUSES:
        issues.append("review_status_unknown")

    issues.extend(_text_list_shape_issues(row.get("positive_criteria"), "positive_criteria"))
    issues.extend(_text_list_shape_issues(row.get("negative_controls"), "negative_controls"))
    positives = _clean_list(row.get("positive_criteria"))
    negatives = _clean_list(row.get("negative_controls"))
    if not positives:
        issues.append("positive_criteria_required")
    if not negatives:
        issues.append("negative_controls_required")

    if not ready_claimed:
        return {
            "review_id": review_id,
            "candidate_dim_id": row.get("candidate_dim_id"),
            "ready_claimed": False,
            "accepted_for_rubric_proposal": False,
            "issues": issues,
            "warnings": warnings,
        }

    approved_id = _clean(row.get("approved_dimension_id"), max_len=160)
    group = _clean(row.get("merge_target_group"), max_len=120)
    source_knowledge_object_id = _clean(row.get("source_knowledge_object_id"), max_len=120)
    if review_status != _APPROVED_STATUS:
        issues.append("review_status_must_be_approved_for_rubric_merge")
    if row.get("ready_for_rubric_promotion") is not True:
        issues.append("ready_for_rubric_promotion_must_be_true")
    if row.get("privacy_review_required") is not False:
        issues.append("privacy_review_required_must_be_false_after_review")
    if row.get("expert_review_required") is not False:
        issues.append("expert_review_required_must_be_false_after_review")
    if not _DIMENSION_ID.fullmatch(approved_id):
        issues.append("approved_dimension_id_must_be_group_dot_slug")
    if not _SAFE_GROUP.fullmatch(group):
        issues.append("merge_target_group_required")
    if approved_id and group and not approved_id.startswith(group + "."):
        issues.append("approved_dimension_id_must_match_merge_target_group")
    if not _PUBLIC_KNOWLEDGE_ID.fullmatch(source_knowledge_object_id):
        issues.append("source_knowledge_object_id_must_be_public_knowledge_object_id")
    for field in ("applicability_notes", "source_corroboration_notes", "privacy_notes", "expert_notes"):
        if not _clean(row.get(field)):
            issues.append(f"{field}_required_for_promotion")
    if row.get("reject_reason"):
        issues.append("reject_reason_must_be_blank_for_approved_rows")
    if not _has_control(negatives, "private", "pii", "contact detail", "complainant"):
        issues.append("negative_controls_must_block_pii_or_private_case_exposure")
    if not _has_control(negatives, "evasion", "conceal", "operationaliz"):
        issues.append("negative_controls_must_block_evasion_or_operationalization")
    issues.extend(_privacy_findings(
        {field: row.get(field) for field in _PII_SCANNED_FIELDS},
        prefix=review_id,
    ))
    proposal = None if issues else _proposal_row(row)
    return {
        "review_id": review_id,
        "candidate_dim_id": row.get("candidate_dim_id"),
        "ready_claimed": True,
        "accepted_for_rubric_proposal": proposal is not None,
        "issues": issues,
        "warnings": warnings,
        "proposed_rubric_dimension": proposal,
    }


def validate_dimension_candidate_review_packet(doc: Any) -> dict[str, Any]:
    rows = doc.get("dimension_review_rows", []) if isinstance(doc, dict) else []
    packet_meta = doc.get("_meta", {}) if isinstance(doc, dict) else {}
    root_issues = _packet_level_root_issues(doc)
    if not isinstance(rows, list):
        root_issues.append("dimension_review_rows_not_list")
        rows = []

    row_results = [
        _validate_row(row, index) if isinstance(row, dict) else {
            "review_id": f"row_{index}",
            "ready_claimed": False,
            "accepted_for_rubric_proposal": False,
            "issues": ["row_not_object"],
            "warnings": [],
        }
        for index, row in enumerate(rows)
    ]
    proposed = [
        result["proposed_rubric_dimension"]
        for result in row_results
        if result.get("proposed_rubric_dimension")
    ]
    ready_claimed = sum(1 for result in row_results if result.get("ready_claimed"))
    blocked_ready = [
        result["review_id"] for result in row_results
        if result.get("ready_claimed") and not result.get("accepted_for_rubric_proposal")
    ]
    malformed_unready = [
        result["review_id"] for result in row_results
        if result.get("issues") and not result.get("ready_claimed")
    ]
    review_id_counts: dict[str, int] = {}
    for result in row_results:
        review_id = _clean(result.get("review_id"), max_len=160)
        if review_id:
            review_id_counts[review_id] = review_id_counts.get(review_id, 0) + 1
    duplicate_review_ids = [
        review_id for review_id, count in sorted(review_id_counts.items()) if count > 1
    ]
    proposal_id_counts: dict[str, int] = {}
    for row in proposed:
        proposal_id = _clean(row.get("id"), max_len=160)
        if proposal_id:
            proposal_id_counts[proposal_id] = proposal_id_counts.get(proposal_id, 0) + 1
    duplicate_proposal_ids = [
        proposal_id for proposal_id, count in sorted(proposal_id_counts.items()) if count > 1
    ]
    root_issues.extend(f"duplicate_review_id:{review_id}" for review_id in duplicate_review_ids)
    root_issues.extend(f"duplicate_approved_dimension_id:{proposal_id}" for proposal_id in duplicate_proposal_ids)
    all_issues = [
        issue
        for result in row_results
        for issue in result.get("issues", [])
    ]
    ok = not root_issues and not blocked_ready and not malformed_unready
    if not ok:
        for result in row_results:
            if result.get("proposed_rubric_dimension") is not None:
                result["accepted_for_rubric_proposal"] = False
                result["packet_blocked_from_rubric_proposal"] = True
                result["proposed_rubric_dimension"] = None
    final_proposed = proposed if ok else []
    return {
        "_meta": {
            "status": "dimension-candidate review validation; propose-only, no rubric mutation",
            "packet_status": packet_meta.get("status") if isinstance(packet_meta, dict) else None,
            "packet_source_artifact": packet_meta.get("source_artifact") if isinstance(packet_meta, dict) else None,
            "packet_source_artifact_sha256": (
                packet_meta.get("source_artifact_sha256") if isinstance(packet_meta, dict) else None
            ),
            "packet_source_artifact_rows": (
                packet_meta.get("source_artifact_rows") if isinstance(packet_meta, dict) else None
            ),
        },
        "summary": {
            "ok": ok,
            "dimension_review_rows": len(rows),
            "rows_ready_claimed": ready_claimed,
            "rows_accepted_for_rubric_proposal": len(final_proposed),
            "rows_locally_valid_before_packet_gate": len(proposed),
            "rows_blocked_after_ready_claim": len(blocked_ready),
            "malformed_unready_rows": len(malformed_unready),
            "root_issue_count": len(root_issues),
            "row_issue_count": len(all_issues),
            "policy": (
                "Passing validation is propose-only. A human must deliberately merge approved rows "
                "into an active rubric before mass judging."
            ),
        },
        "root_issues": root_issues,
        "row_results": row_results,
        "proposed_rubric_dimensions": final_proposed,
    }


def default_packet_path() -> pathlib.Path:
    return OUT_DIR / "research_spider_dimension_candidate_review_packet.json"


def default_out_path() -> pathlib.Path:
    return OUT_DIR / "research_spider_dimension_candidate_review_validation.json"


def default_markdown_path(json_path: pathlib.Path) -> pathlib.Path:
    return json_path.with_suffix(".md")


def _md_cell(value: Any) -> str:
    text = str(value if value is not None else "")
    return text.replace("|", "\\|").replace("\n", " ").strip()


def build_markdown_report(doc: dict[str, Any]) -> str:
    summary = doc["summary"]
    lines = [
        "# Dimension Candidate Review Validation",
        "",
        "This report is propose-only and never mutates the active rubric.",
        "",
        "## Summary",
        "",
        "| Metric | Value |",
        "|---|---:|",
        f"| OK | {str(bool(summary['ok'])).lower()} |",
        f"| Dimension review rows | {summary['dimension_review_rows']} |",
        f"| Rows ready claimed | {summary['rows_ready_claimed']} |",
        f"| Rows accepted for rubric proposal | {summary['rows_accepted_for_rubric_proposal']} |",
        f"| Rows blocked after ready claim | {summary['rows_blocked_after_ready_claim']} |",
        f"| Malformed unready rows | {summary['malformed_unready_rows']} |",
        f"| Root issue count | {summary['root_issue_count']} |",
        f"| Row issue count | {summary['row_issue_count']} |",
        "",
        "## Proposed Rubric Dimensions",
        "",
        "| Dimension ID | Group | Source family | Candidate |",
        "|---|---|---|---|",
    ]
    if doc["proposed_rubric_dimensions"]:
        for row in doc["proposed_rubric_dimensions"]:
            lines.append(
                f"| `{_md_cell(row['id'])}` "
                f"| {_md_cell(row['group'])} "
                f"| {_md_cell(row['source_family'])} "
                f"| `{_md_cell(row['candidate_dim_id'])}` |"
            )
    else:
        lines.append("| - | - | - | - |")
    lines.extend([
        "",
        "## Blocked Ready Claims",
        "",
        "| Review ID | Issues |",
        "|---|---|",
    ])
    blocked = False
    for result in doc["row_results"]:
        if result.get("ready_claimed") and result.get("issues"):
            blocked = True
            issues = ", ".join(_md_cell(issue) for issue in result["issues"])
            lines.append(f"| `{_md_cell(result['review_id'])}` | {issues} |")
    if not blocked:
        lines.append("| - | - |")
    lines.extend([
        "",
        "## Root Issues",
        "",
        "| Issue |",
        "|---|",
    ])
    if doc["root_issues"]:
        for issue in doc["root_issues"]:
            lines.append(f"| {_md_cell(issue)} |")
    else:
        lines.append("| - |")
    lines.append("")
    return "\n".join(lines)


def _load_packet(path: pathlib.Path) -> dict[str, Any]:
    doc = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(doc, dict):
        raise ValueError(f"dimension review packet must contain a JSON object: {path}")
    return doc


def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--packet", type=pathlib.Path, default=None)
    ap.add_argument("--out", type=pathlib.Path, default=None)
    ap.add_argument("--md-out", type=pathlib.Path, default=None)
    ap.add_argument("--no-md", action="store_true")
    args = ap.parse_args(argv)

    packet_path = args.packet or default_packet_path()
    doc = validate_dimension_candidate_review_packet(_load_packet(packet_path))
    doc["_meta"]["packet_artifact"] = _display_path(packet_path)
    doc["_meta"]["packet_artifact_sha256"] = _sha256_file(packet_path)
    doc["_meta"]["packet_artifact_bytes"] = packet_path.stat().st_size
    out_path = args.out or default_out_path()
    out_path.parent.mkdir(parents=True, exist_ok=True)
    out_path.write_text(json.dumps(doc, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
    md_path = None
    if not args.no_md:
        md_path = args.md_out or default_markdown_path(out_path)
        md_path.parent.mkdir(parents=True, exist_ok=True)
        md_path.write_text(build_markdown_report(doc) + "\n", encoding="utf-8")
    summary = doc["summary"]
    print(
        f"wrote {out_path}: {summary['rows_accepted_for_rubric_proposal']} rubric proposals; "
        f"ok={str(bool(summary['ok'])).lower()}"
        + (f"; report {md_path}" if md_path else "")
    )
    return 0 if summary["ok"] else 1


if __name__ == "__main__":
    raise SystemExit(main())
