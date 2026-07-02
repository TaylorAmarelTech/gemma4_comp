#!/usr/bin/env python3
"""Build a curator review packet for public-research dimension candidates.

The research spider emits ``dimension_candidates.jsonl`` as candidate rubric
material. This script turns those candidates into a blank review packet. Every
row starts as not ready for rubric promotion; a separate validator must review
filled rows before any candidate can become an active grading dimension.
"""
from __future__ import annotations

import argparse
from collections import Counter
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

RESEARCH_DIR = _ROOT / "configs" / "duecare" / "benchmarks" / "research_spider"
DEFAULT_CANDIDATES = RESEARCH_DIR / "dimension_candidates.jsonl"
OUT_DIR = _ROOT / "reports" / "benchmark"

_EMAIL = re.compile(r"\b[\w.+-]+@[\w-]+\.[\w.-]+\b", re.I)
_PHONE = re.compile(r"\+?\d[\d\s().\-]{8,}\d")
_LONG_DIGITS = re.compile(r"\b\d{9,}\b")
_LOCAL_PATH_HINT = re.compile(r"(?:[A-Za-z]:[\\/]|\\\\|/(?:Users|home|tmp|var|mnt)(?:/|$)|~[\\/])", re.I)
_PUBLIC_KNOWLEDGE_ID = re.compile(r"^KNOW-PUBLIC-[A-F0-9]{10}$")

_REVIEW_FIELDS = [
    "review_id",
    "dimension_candidate_id",
    "candidate_dim_id",
    "group",
    "source_family",
    "source_knowledge_object_id",
    "name",
    "rubric_prompt",
    "positive_criteria",
    "negative_controls",
    "candidate_status",
    "review_status",
    "approved_dimension_id",
    "merge_target_group",
    "applicability_notes",
    "source_corroboration_notes",
    "privacy_notes",
    "expert_notes",
    "reject_reason",
    "ready_for_rubric_promotion",
    "privacy_review_required",
    "expert_review_required",
]

_PII_SCANNED_REVIEW_FIELDS = (
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

_PII_SCANNED_SOURCE_FIELDS = (
    "name",
    "rubric_prompt",
    "positive_criteria",
    "negative_controls",
)


def _load_jsonl(path: pathlib.Path) -> tuple[list[dict[str, Any]], list[str], int]:
    rows: list[dict[str, Any]] = []
    issues: list[str] = []
    nonblank_lines = 0
    for line_no, line in enumerate(path.read_text(encoding="utf-8").splitlines(), start=1):
        line = line.strip()
        if not line:
            continue
        nonblank_lines += 1
        try:
            row = json.loads(line)
        except json.JSONDecodeError as exc:
            issues.append(f"line_{line_no}: json_decode_error:{exc.msg}")
            continue
        if isinstance(row, dict):
            rows.append(row)
        else:
            issues.append(f"line_{line_no}: row_not_object")
    return rows, issues, nonblank_lines


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


def _clean_list(value: Any, *, max_items: int = 12, max_len: int = 220) -> list[str]:
    if not isinstance(value, list):
        return []
    out: list[str] = []
    for item in value[:max_items]:
        text = _clean(item, max_len=max_len)
        if text:
            out.append(text)
    return out


def _text_list_shape_issues(value: Any, field: str, row_label: str) -> list[str]:
    if not isinstance(value, list):
        return [f"{row_label}: {field}_must_be_list"]
    issues: list[str] = []
    for index, item in enumerate(value):
        if not isinstance(item, str) or not _clean(item):
            issues.append(f"{row_label}: {field}[{index}]_must_be_non_empty_string")
    return issues


def _source_candidate_shape_issues(row: dict[str, Any], index: int) -> list[str]:
    row_id = _clean(row.get("id"), max_len=120)
    row_label = row_id or f"row_{index}"
    issues: list[str] = []
    for field in (
        "id",
        "candidate_dim_id",
        "group",
        "source_family",
        "source_knowledge_object_id",
        "name",
        "rubric_prompt",
        "status",
    ):
        if not _clean(row.get(field)):
            issues.append(f"{row_label}: {field}_missing_or_not_string")
    source_knowledge_object_id = _clean(row.get("source_knowledge_object_id"), max_len=120)
    if source_knowledge_object_id and not _PUBLIC_KNOWLEDGE_ID.fullmatch(source_knowledge_object_id):
        issues.append(f"{row_label}: source_knowledge_object_id_must_be_public_knowledge_object_id")
    issues.extend(_text_list_shape_issues(row.get("positive_criteria"), "positive_criteria", row_label))
    issues.extend(_text_list_shape_issues(row.get("negative_controls"), "negative_controls", row_label))
    return issues


def _source_candidate_privacy_issues(rows: list[dict[str, Any]]) -> tuple[list[str], dict[str, Any]]:
    privacy_scan = _privacy_scan({
        "source_candidates": [
            {field: row.get(field) for field in _PII_SCANNED_SOURCE_FIELDS}
            for row in rows
        ],
    })
    issues: list[str] = []
    for key in ("email_like_paths", "phone_like_paths", "long_digit_paths", "local_path_like_paths"):
        kind = key.removesuffix("_paths")
        for path in privacy_scan.get(key, []):
            issues.append(f"source_candidate_privacy_scan:{kind}:{path}")
    return issues, privacy_scan


def _source_candidate_audit(
    rows: list[dict[str, Any]],
    *,
    load_issues: list[str],
    nonblank_lines: int,
) -> dict[str, Any]:
    issues = list(load_issues)
    for index, row in enumerate(rows, start=1):
        issues.extend(_source_candidate_shape_issues(row, index))
    privacy_issues, privacy_scan = _source_candidate_privacy_issues(rows)
    issues.extend(privacy_issues)
    return {
        "ok": not issues,
        "issues": issues,
        "privacy_scan": privacy_scan,
        "accepted_candidate_rows": len(rows),
        "source_nonblank_lines": nonblank_lines,
    }


def _review_id(row: dict[str, Any], index: int) -> str:
    source_id = _clean(row.get("id"), max_len=80)
    return f"DIM-REVIEW-{source_id or index + 1:03}"


def _review_row(row: dict[str, Any], index: int) -> dict[str, Any]:
    return {
        "review_id": _review_id(row, index),
        "dimension_candidate_id": _clean(row.get("id"), max_len=120),
        "candidate_dim_id": _clean(row.get("candidate_dim_id"), max_len=200),
        "group": _clean(row.get("group"), max_len=120),
        "source_family": _clean(row.get("source_family"), max_len=160),
        "source_knowledge_object_id": _clean(row.get("source_knowledge_object_id"), max_len=120),
        "name": _clean(row.get("name"), max_len=240),
        "rubric_prompt": _clean(row.get("rubric_prompt"), max_len=500),
        "positive_criteria": _clean_list(row.get("positive_criteria")),
        "negative_controls": _clean_list(row.get("negative_controls")),
        "candidate_status": _clean(row.get("status"), max_len=120),
        "review_status": "needs_curator_review",
        "approved_dimension_id": "",
        "merge_target_group": "",
        "applicability_notes": "",
        "source_corroboration_notes": "",
        "privacy_notes": "",
        "expert_notes": "",
        "reject_reason": "",
        "ready_for_rubric_promotion": False,
        "privacy_review_required": True,
        "expert_review_required": True,
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


def validate_blank_review_packet(doc: dict[str, Any]) -> dict[str, Any]:
    issues: list[str] = []
    rows = doc.get("dimension_review_rows", [])
    if not isinstance(rows, list):
        issues.append("dimension_review_rows_not_list")
        rows = []
    seen_ids: set[str] = set()
    for index, row in enumerate(rows):
        if not isinstance(row, dict):
            issues.append(f"row_{index}_not_object")
            continue
        review_id = _clean(row.get("review_id"), max_len=160) or f"row_{index}"
        if review_id in seen_ids:
            issues.append(f"{review_id}: duplicate_review_id")
        seen_ids.add(review_id)
        if row.get("review_status") != "needs_curator_review":
            issues.append(f"{review_id}: review_status_must_start_needs_curator_review")
        if row.get("ready_for_rubric_promotion") is not False:
            issues.append(f"{review_id}: ready_for_rubric_promotion_must_start_false")
        if row.get("privacy_review_required") is not True:
            issues.append(f"{review_id}: privacy_review_required_must_start_true")
        if row.get("expert_review_required") is not True:
            issues.append(f"{review_id}: expert_review_required_must_start_true")
        for field in ("approved_dimension_id", "merge_target_group", "reject_reason"):
            if row.get(field):
                issues.append(f"{review_id}: {field}_must_start_blank")
        for field in (
            "dimension_candidate_id",
            "candidate_dim_id",
            "group",
            "source_family",
            "source_knowledge_object_id",
            "rubric_prompt",
        ):
            if not _clean(row.get(field)):
                issues.append(f"{review_id}: {field}_missing")
    privacy_scan = _privacy_scan({
        "dimension_review_rows": [
            {field: row.get(field) for field in _PII_SCANNED_REVIEW_FIELDS}
            for row in rows
            if isinstance(row, dict)
        ],
    })
    if privacy_scan["ok"] is not True:
        issues.append("dimension_review_packet_privacy_scan_not_ok")
    return {
        "ok": not issues,
        "issues": issues,
        "privacy_scan": privacy_scan,
        "dimension_review_rows": len(rows),
    }


def build_dimension_candidate_review_packet(
    *,
    candidates_path: pathlib.Path = DEFAULT_CANDIDATES,
) -> dict[str, Any]:
    candidates, load_issues, nonblank_lines = _load_jsonl(candidates_path)
    source_candidate_audit = _source_candidate_audit(
        candidates,
        load_issues=load_issues,
        nonblank_lines=nonblank_lines,
    )
    rows = [_review_row(row, index) for index, row in enumerate(candidates)]
    status_counts = Counter(row.get("candidate_status", "") for row in rows)
    group_counts = Counter(row.get("group", "") for row in rows)
    source_family_counts = Counter(row.get("source_family", "") for row in rows)
    doc: dict[str, Any] = {
        "_meta": {
            "schema_version": "dimension_candidate_review_packet.v1",
            "status": (
                "blank dimension-candidate review packet; not rubric promotion, "
                "not legal advice, and not an active judging plan"
            ),
            "source_artifact": _display_path(candidates_path),
            "source_artifact_sha256": _sha256_file(candidates_path),
            "source_artifact_bytes": candidates_path.stat().st_size,
            "source_artifact_rows": len(candidates),
            "source_artifact_nonblank_lines": nonblank_lines,
            "review_rule": (
                "Rows must remain needs_curator_review until public-source corroboration, "
                "privacy review, applicability review, and expert review support rubric promotion."
            ),
        },
        "summary": {
            "dimension_candidate_rows": len(rows),
            "default_ready_for_rubric_promotion": 0,
            "status_counts": dict(sorted(status_counts.items())),
            "group_counts": dict(sorted(group_counts.items())),
            "source_family_count": len([key for key in source_family_counts if key]),
            "policy": (
                "Use public source metadata only. Do not paste worker names, complainant rows, "
                "private case details, contact details, or raw intake text."
            ),
        },
        "dimension_review_schema": _REVIEW_FIELDS,
        "dimension_review_rows": rows,
        "source_candidate_audit": source_candidate_audit,
        "promotion_gates": [
            "candidate dimension is grounded in public-source patterns, not private case rows",
            "positive criteria are observable response behaviors, not country-law claims without sources",
            "negative controls block PII exposure, evasion guidance, and exploitative operationalization",
            "applicability scope is clear enough for per-prompt dimension selection",
            "curator and domain expert approve promotion before any mass judging run",
        ],
    }
    doc["safety_audit"] = validate_blank_review_packet(doc)
    if not source_candidate_audit["ok"]:
        doc["safety_audit"]["ok"] = False
        doc["safety_audit"]["issues"].append("source_candidate_audit_not_ok")
    return doc


def default_out_path() -> pathlib.Path:
    return OUT_DIR / "research_spider_dimension_candidate_review_packet.json"


def default_markdown_path(json_path: pathlib.Path) -> pathlib.Path:
    return json_path.with_suffix(".md")


def _md_cell(value: Any) -> str:
    text = str(value if value is not None else "")
    return text.replace("|", "\\|").replace("\n", " ").strip()


def build_markdown_report(doc: dict[str, Any]) -> str:
    meta = doc["_meta"]
    summary = doc["summary"]
    audit = doc["safety_audit"]
    source_audit = doc.get("source_candidate_audit", {})
    source_issues = source_audit.get("issues") if isinstance(source_audit, dict) else []
    lines = [
        "# Dimension Candidate Review Packet",
        "",
        (
            "This packet is a blank curator intake artifact for research-spider dimension "
            "candidates. It is not rubric promotion and not an active judging plan."
        ),
        "",
        "## Summary",
        "",
        "| Metric | Value |",
        "|---|---:|",
        f"| Dimension candidate rows | {summary['dimension_candidate_rows']} |",
        f"| Rows ready for rubric promotion by default | {summary['default_ready_for_rubric_promotion']} |",
        f"| Source families | {summary['source_family_count']} |",
        f"| Source candidate audit issues | {len(source_issues) if isinstance(source_issues, list) else 0} |",
        f"| Safety audit issues | {len(audit['issues'])} |",
        "",
        "## Promotion Gates",
        "",
    ]
    lines.extend(f"- {_md_cell(gate)}" for gate in doc["promotion_gates"])
    lines.extend([
        "",
        "## Candidate Rows",
        "",
        "| Review ID | Candidate | Group | Source family | Status | Ready |",
        "|---|---|---|---|---|---:|",
    ])
    for row in doc["dimension_review_rows"]:
        lines.append(
            f"| `{_md_cell(row['review_id'])}` "
            f"| `{_md_cell(row['candidate_dim_id'])}` "
            f"| {_md_cell(row['group'])} "
            f"| {_md_cell(row['source_family'])} "
            f"| {_md_cell(row['review_status'])} "
            f"| {str(bool(row['ready_for_rubric_promotion'])).lower()} |"
        )
    lines.extend([
        "",
        "## Intake Schema",
        "",
        f"- Dimension review fields: `{', '.join(_REVIEW_FIELDS)}`",
        "",
        f"Source artifact: `{_md_cell(meta['source_artifact'])}`",
    ])
    return "\n".join(lines)


def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--candidates", type=pathlib.Path, default=DEFAULT_CANDIDATES)
    ap.add_argument("--out", type=pathlib.Path, default=None)
    ap.add_argument("--md-out", type=pathlib.Path, default=None)
    ap.add_argument("--no-md", action="store_true")
    args = ap.parse_args(argv)

    doc = build_dimension_candidate_review_packet(candidates_path=args.candidates)
    out_path = args.out or default_out_path()
    out_path.parent.mkdir(parents=True, exist_ok=True)
    out_path.write_text(json.dumps(doc, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
    md_path = None
    if not args.no_md:
        md_path = args.md_out or default_markdown_path(out_path)
        md_path.parent.mkdir(parents=True, exist_ok=True)
        md_path.write_text(build_markdown_report(doc) + "\n", encoding="utf-8")
    print(
        f"wrote {out_path}: {doc['summary']['dimension_candidate_rows']} dimension candidate rows"
        + (f"; report {md_path}" if md_path else "")
    )
    return 0 if doc["safety_audit"]["ok"] else 1


if __name__ == "__main__":
    raise SystemExit(main())
