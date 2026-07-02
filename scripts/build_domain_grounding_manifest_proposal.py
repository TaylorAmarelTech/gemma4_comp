#!/usr/bin/env python3
"""Build a non-mutating grounding-manifest update proposal.

This is the final offline handoff after a source-review validation report. It
loads the existing domain grounding manifest and the validated candidate rows,
then emits a proposal document with operations and a full preview manifest. It
never edits ``grounding_sources.json``.
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

from domain_grounding import GroundingError, load_grounding_manifest, validate_grounding_manifest  # noqa: E402
from domain_registry import resolve_grounding_manifest  # noqa: E402

OUT_DIR = _ROOT / "reports" / "benchmark"
_SAFE_DOMAIN_ID = re.compile(r"^[a-z0-9_:-]{1,80}$")
_PENDING_STATUSES = {"needs_source", "needs_archive", "unsafe_without_archive"}


def _safe_domain_id(domain_id: str) -> str:
    if not _SAFE_DOMAIN_ID.fullmatch(domain_id):
        raise ValueError(f"unsafe domain id: {domain_id!r}")
    return domain_id


def _load_json_object(path: pathlib.Path) -> dict[str, Any]:
    doc = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(doc, dict):
        raise ValueError(f"expected JSON object at {path}")
    return doc


def _display_path(path: pathlib.Path) -> str:
    try:
        return str(path.resolve().relative_to(_ROOT).as_posix())
    except ValueError:
        return str(path)


def _validate_candidate(candidate: dict[str, Any]) -> list[str]:
    try:
        validate_grounding_manifest({
            "_meta": {
                "domain": "candidate",
                "schema_version": "0.1",
                "last_updated": candidate.get("verified_date"),
            },
            "sources": [candidate],
        })
    except (GroundingError, ValueError, TypeError) as exc:
        return [f"candidate_manifest_shape_invalid: {exc}"]
    return []


def _candidate_rejection_reasons(
    candidate: dict[str, Any],
    *,
    existing: dict[str, Any] | None,
    duplicate_ids: set[str],
) -> list[str]:
    reasons = _validate_candidate(candidate)
    source_id = str(candidate.get("id") or "")
    if source_id in duplicate_ids:
        reasons.append("duplicate_candidate_source_id")
    if existing:
        if existing.get("verification_status") not in _PENDING_STATUSES:
            reasons.append("existing_source_row_is_not_pending")
        if existing.get("jurisdiction") != candidate.get("jurisdiction"):
            reasons.append("candidate_jurisdiction_differs_from_existing_row")
        existing_tags = set(existing.get("coverage_tags") or [])
        candidate_tags = set(candidate.get("coverage_tags") or [])
        if existing_tags and candidate_tags and not (existing_tags & candidate_tags):
            reasons.append("candidate_coverage_tags_do_not_match_existing_row")
    return reasons


def _operation_for(candidate: dict[str, Any], existing: dict[str, Any] | None) -> str:
    return "promote_existing_source_row" if existing else "add_source_row"


def _preview_manifest(
    manifest: dict[str, Any],
    accepted_operations: list[dict[str, Any]],
) -> dict[str, Any]:
    sources = [dict(row) for row in manifest["sources"]]
    index_by_id = {row["id"]: i for i, row in enumerate(sources)}
    for op in accepted_operations:
        candidate = dict(op["candidate_manifest_row"])
        if op["operation"] == "promote_existing_source_row":
            sources[index_by_id[candidate["id"]]] = candidate
        else:
            sources.append(candidate)
    meta = dict(manifest["_meta"])
    if accepted_operations:
        meta["status"] = (
            "proposal preview: includes manually reviewed source rows; apply only after curator approval"
        )
    return {"_meta": meta, "sources": sources}


def build_grounding_manifest_proposal(
    domain_id: str,
    *,
    validation_doc: dict[str, Any],
    manifest_path: pathlib.Path | None = None,
) -> dict[str, Any]:
    """Return a non-mutating proposal from a validation report and manifest."""
    domain_id = _safe_domain_id(domain_id)
    if manifest_path is None:
        manifest_path = resolve_grounding_manifest(domain_id)
        if manifest_path is None:
            raise ValueError(f"domain {domain_id!r} has no grounding manifest")
    manifest = load_grounding_manifest(manifest_path)
    existing_by_id = {row["id"]: row for row in manifest["sources"]}
    candidates = validation_doc.get("candidate_manifest_rows", [])
    if not isinstance(candidates, list):
        candidates = []
    validation_ok = bool(validation_doc.get("summary", {}).get("ok"))
    candidate_id_counts = Counter(
        str(candidate.get("id") or "")
        for candidate in candidates
        if isinstance(candidate, dict)
    )
    duplicate_ids = {source_id for source_id, count in candidate_id_counts.items() if source_id and count > 1}

    accepted: list[dict[str, Any]] = []
    rejected: list[dict[str, Any]] = []
    for i, candidate in enumerate(candidates):
        if not isinstance(candidate, dict):
            rejected.append({
                "index": i,
                "source_id": None,
                "reasons": ["candidate_not_object"],
            })
            continue
        source_id = str(candidate.get("id") or "")
        existing = existing_by_id.get(source_id)
        reasons = _candidate_rejection_reasons(candidate, existing=existing, duplicate_ids=duplicate_ids)
        if reasons:
            rejected.append({
                "index": i,
                "source_id": source_id,
                "operation": _operation_for(candidate, existing),
                "reasons": reasons,
            })
            continue
        accepted.append({
            "operation": _operation_for(candidate, existing),
            "source_id": source_id,
            "jurisdiction": candidate.get("jurisdiction"),
            "coverage_tags": candidate.get("coverage_tags", []),
            "replaces_status": existing.get("verification_status") if existing else None,
            "candidate_manifest_row": candidate,
        })

    preview = _preview_manifest(manifest, accepted)
    preview_issues: list[str] = []
    try:
        normalized_preview = validate_grounding_manifest(preview, path=manifest_path)
        preview = {"_meta": normalized_preview["_meta"], "sources": normalized_preview["sources"]}
    except (GroundingError, ValueError, TypeError) as exc:
        preview_issues.append(str(exc))

    validation_issue = [] if validation_ok else ["source_review_validation_report_not_ok"]
    proposal_ok = validation_ok and not rejected and not preview_issues
    ready = proposal_ok and bool(accepted)
    return {
        "_meta": {
            "domain": domain_id,
            "status": "non-mutating grounding manifest proposal",
            "grounding_manifest": _display_path(manifest_path),
            "source_validation_status": validation_doc.get("_meta", {}).get("status"),
        },
        "summary": {
            "proposal_ok": proposal_ok,
            "ready_for_manual_manifest_patch": ready,
            "validation_report_ok": validation_ok,
            "candidate_rows": len(candidates),
            "accepted_operations": len(accepted),
            "rejected_candidates": len(rejected),
            "promote_existing_source_rows": sum(
                1 for op in accepted if op["operation"] == "promote_existing_source_row"
            ),
            "add_source_rows": sum(1 for op in accepted if op["operation"] == "add_source_row"),
            "current_manifest_source_count": len(manifest["sources"]),
            "preview_manifest_source_count": len(preview["sources"]),
            "preview_validation_issue_count": len(preview_issues),
            "policy": (
                "This proposal is a review artifact only. It does not edit the grounding manifest; "
                "a curator must apply any accepted row deliberately."
            ),
        },
        "validation_issues": validation_issue,
        "preview_validation_issues": preview_issues,
        "accepted_operations": accepted,
        "rejected_candidate_rows": rejected,
        "proposed_manifest_preview": preview,
    }


def default_validation_path(domain_id: str) -> pathlib.Path:
    return OUT_DIR / f"{_safe_domain_id(domain_id)}_source_review_validation.json"


def default_out_path(domain_id: str) -> pathlib.Path:
    return OUT_DIR / f"{_safe_domain_id(domain_id)}_grounding_manifest_proposal.json"


def default_markdown_path(json_path: pathlib.Path) -> pathlib.Path:
    return json_path.with_suffix(".md")


def _md_cell(value: Any) -> str:
    text = str(value if value is not None else "")
    return text.replace("|", "\\|").replace("\n", " ").strip()


def _md_list(values: list[Any]) -> str:
    return ", ".join(_md_cell(v) for v in values) if values else "-"


def build_markdown_report(doc: dict[str, Any]) -> str:
    """Render a Markdown proposal report."""
    meta = doc["_meta"]
    summary = doc["summary"]
    lines: list[str] = [
        f"# Domain Grounding Manifest Proposal - {_md_cell(meta['domain'])}",
        "",
        (
            "This is a non-mutating proposal. It summarizes candidate source rows "
            "against the current grounding manifest and includes a preview only."
        ),
        "",
        "## Summary",
        "",
        "| Metric | Value |",
        "|---|---:|",
        f"| Proposal OK | {str(bool(summary['proposal_ok'])).lower()} |",
        f"| Ready for manual manifest patch | {str(bool(summary['ready_for_manual_manifest_patch'])).lower()} |",
        f"| Candidate rows | {summary['candidate_rows']} |",
        f"| Accepted operations | {summary['accepted_operations']} |",
        f"| Rejected candidates | {summary['rejected_candidates']} |",
        f"| Promote existing rows | {summary['promote_existing_source_rows']} |",
        f"| Add source rows | {summary['add_source_rows']} |",
        f"| Current manifest source count | {summary['current_manifest_source_count']} |",
        f"| Preview manifest source count | {summary['preview_manifest_source_count']} |",
        "",
        "## Accepted Operations",
        "",
        "| Operation | Source ID | Jurisdiction | Coverage tags | Replaces status |",
        "|---|---|---|---|---|",
    ]
    if doc["accepted_operations"]:
        for op in doc["accepted_operations"]:
            lines.append(
                f"| {_md_cell(op['operation'])} "
                f"| `{_md_cell(op['source_id'])}` "
                f"| {_md_cell(op.get('jurisdiction'))} "
                f"| {_md_list(op.get('coverage_tags', []))} "
                f"| {_md_cell(op.get('replaces_status') or '-')} |"
            )
    else:
        lines.append("| - | - | - | - | - |")
    lines.extend([
        "",
        "## Rejected Candidates",
        "",
        "| Source ID | Operation | Reasons |",
        "|---|---|---|",
    ])
    if doc["rejected_candidate_rows"]:
        for row in doc["rejected_candidate_rows"]:
            lines.append(
                f"| `{_md_cell(row.get('source_id') or '-')}` "
                f"| {_md_cell(row.get('operation') or '-')} "
                f"| {_md_list(row.get('reasons', []))} |"
            )
    else:
        lines.append("| - | - | - |")
    lines.extend([
        "",
        "## Inputs",
        "",
        f"- Grounding manifest: `{_md_cell(meta['grounding_manifest'])}`",
        "",
    ])
    return "\n".join(lines)


def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--domain", default="developing_country_worker_protections")
    ap.add_argument("--validation-report", type=pathlib.Path, default=None)
    ap.add_argument("--manifest", type=pathlib.Path, default=None)
    ap.add_argument("--out", type=pathlib.Path, default=None)
    ap.add_argument("--md-out", type=pathlib.Path, default=None, help="Markdown report path; defaults to --out with .md suffix")
    ap.add_argument("--no-md", action="store_true", help="write only JSON, not the Markdown proposal report")
    args = ap.parse_args(argv)

    domain_id = _safe_domain_id(args.domain)
    validation_path = args.validation_report or default_validation_path(domain_id)
    doc = build_grounding_manifest_proposal(
        domain_id,
        validation_doc=_load_json_object(validation_path),
        manifest_path=args.manifest,
    )
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
        f"wrote {out_path}: {summary['accepted_operations']} accepted operations; "
        f"{summary['rejected_candidates']} rejected; "
        f"ready={str(bool(summary['ready_for_manual_manifest_patch'])).lower()}"
        + (f"; report {md_path}" if md_path else "")
    )
    return 0 if summary["proposal_ok"] else 1


if __name__ == "__main__":
    raise SystemExit(main())
