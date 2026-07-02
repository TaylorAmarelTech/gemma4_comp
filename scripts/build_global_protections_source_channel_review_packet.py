#!/usr/bin/env python3
"""Build a blank source-channel review packet for global protections.

The source-channel matrix names the channels to search. This packet is the
curator intake surface for candidate public-source metadata. Rows start blank
and blocked; the command does not fetch sources, verify law, create source rows,
or authorize scoring.

Offline + deterministic. No model, no network, no credits.
"""
from __future__ import annotations

import argparse
import json
import pathlib
import sys
from typing import Any

_ROOT = pathlib.Path(__file__).resolve().parents[1]
_SCRIPTS = pathlib.Path(__file__).resolve().parent
if str(_SCRIPTS) not in sys.path:
    sys.path.insert(0, str(_SCRIPTS))

import build_global_protections_project_plan as project_plan_builder  # noqa: E402
import build_global_protections_source_channel_matrix as matrix_builder  # noqa: E402

OUT_DIR = _ROOT / "reports" / "benchmark"
OUT = OUT_DIR / "global_protections_source_channel_review_packet.json"
MD_OUT = OUT_DIR / "global_protections_source_channel_review_packet.md"

DISALLOWED_TERMS = [
    "Synthetic composite:",
    "prompt_family_sketches",
    "candidate_url",
    "source_url",
    "raw_text",
    "case_text",
    "https://",
    "www.",
]


def _display_path(path: pathlib.Path) -> str:
    try:
        return path.relative_to(_ROOT).as_posix()
    except ValueError:
        return path.as_posix()


def _check(check_id: str, ok: bool, *, expected: Any, actual: Any) -> dict[str, Any]:
    return {
        "id": check_id,
        "ok": bool(ok),
        "expected": expected,
        "actual": actual,
    }


def _review_row(matrix_row: dict[str, Any], index: int) -> dict[str, Any]:
    informal = bool(matrix_row.get("informal_publication"))
    return {
        "review_id": f"GPSCR-{index:03d}",
        "matrix_row_id": matrix_row.get("id"),
        "jurisdiction_family": matrix_row.get("jurisdiction_family"),
        "jurisdiction_family_id": matrix_row.get("jurisdiction_family_id"),
        "source_channel_id": matrix_row.get("source_channel_id"),
        "source_channel_label": matrix_row.get("source_channel_label"),
        "source_role": matrix_row.get("source_role"),
        "authority_tier": matrix_row.get("authority_tier"),
        "claim_use": matrix_row.get("claim_use"),
        "source_channel_evidence_status": matrix_row.get("evidence_status"),
        "status": "not_started",
        "candidate_source_title": "",
        "issuing_or_publishing_authority": "",
        "concrete_jurisdiction_or_forum": "",
        "publication_or_access_date": "",
        "archive_status": "not_started",
        "public_locator_status": "missing",
        "language": "",
        "claim_scope_note": "",
        "privacy_review_status": "not_started",
        "source_path_review_status": "not_started",
        "public_interest_review_status": "not_started" if informal else "not_required",
        "expert_review_status": "not_started",
        "authenticity_review_status": "not_started",
        "volatility_review_status": "not_started",
        "authenticity_controls_required": list(
            matrix_row.get("authenticity_controls_required") or []
        ),
        "volatility_controls_required": list(
            matrix_row.get("volatility_controls_required") or []
        ),
        "informal_publication_claim_boundary": matrix_row.get(
            "informal_publication_claim_boundary", "not_applicable"
        ),
        "required_metadata": list(matrix_row.get("required_metadata") or []),
        "review_gates": list(matrix_row.get("review_gates") or []),
        "corroboration_required": list(matrix_row.get("corroboration_required") or []),
        "rejection_triggers": list(matrix_row.get("rejection_triggers") or []),
        "ready_for_manifest_promotion": False,
        "ready_for_prompt_generation": False,
        "ready_for_training_use": False,
        "ready_for_public_claims": False,
        "ready_for_worker_facing_use": False,
        "ready_for_comparable_scoring": False,
        "next_step": (
            "fill only with public, dated, archived source metadata; reject private case rows, "
            "names, contacts, addresses, and small-community identifiers"
        ),
    }


def _contains_disallowed_text(doc: dict[str, Any]) -> list[str]:
    encoded = json.dumps(doc, ensure_ascii=False)
    return [term for term in DISALLOWED_TERMS if term in encoded]


def build_source_channel_review_packet(
    *,
    matrix_doc: dict[str, Any] | None = None,
    config_path: pathlib.Path = project_plan_builder.CONFIG,
    registry_path: pathlib.Path = project_plan_builder.REGISTRY,
    regulatory_catalog_path: pathlib.Path = project_plan_builder.REGULATORY_CATALOG,
) -> dict[str, Any]:
    """Return a blank, non-mutating source-channel review packet."""
    matrix_doc = matrix_doc or matrix_builder.build_source_channel_matrix(
        config_path=config_path,
        registry_path=registry_path,
        regulatory_catalog_path=regulatory_catalog_path,
    )
    matrix_rows = [
        row for row in matrix_doc.get("matrix_rows", []) if isinstance(row, dict)
    ]
    review_rows = [
        _review_row(row, index)
        for index, row in enumerate(matrix_rows, start=1)
    ]
    ready_flags = {
        "manifest_promotion": any(row["ready_for_manifest_promotion"] for row in review_rows),
        "prompt_generation": any(row["ready_for_prompt_generation"] for row in review_rows),
        "training_use": any(row["ready_for_training_use"] for row in review_rows),
        "public_claims": any(row["ready_for_public_claims"] for row in review_rows),
        "worker_facing_use": any(row["ready_for_worker_facing_use"] for row in review_rows),
        "comparable_scoring": any(row["ready_for_comparable_scoring"] for row in review_rows),
    }
    status_counts: dict[str, int] = {}
    for row in review_rows:
        status = str(row.get("status") or "unknown")
        status_counts[status] = status_counts.get(status, 0) + 1
    informal_rows = [
        row
        for row in review_rows
        if row["source_channel_id"] == "social_channel_notice_or_scanned_circular"
    ]
    legal_claim_anchor_rows = [
        row for row in review_rows if str(row["claim_use"]).startswith("may_support_legal_claim")
    ]
    legal_claim_anchor_channels = matrix_builder.legal_claim_anchor_source_channel_ids()
    lead_only_claim_rows = [
        row for row in review_rows if row["claim_use"] == "lead_only_never_standalone_legal_claim"
    ]
    authenticity_volatility_review_rows = [
        row
        for row in review_rows
        if row["authenticity_review_status"] == "not_started"
        and row["volatility_review_status"] == "not_started"
        and row["authenticity_controls_required"]
        and row["volatility_controls_required"]
    ]
    informal_authenticity_volatility_review_rows = [
        row
        for row in informal_rows
        if row["informal_publication_claim_boundary"]
        == "lead_only_until_authenticity_volatility_and_official_follow_up_review"
    ]
    summary = {
        "consistency_ok": False,
        "matrix_consistency_ok": matrix_doc["summary"]["consistency_ok"],
        "matrix_row_count": matrix_doc["summary"]["matrix_row_count"],
        "review_row_count": len(review_rows),
        "not_started_rows": status_counts.get("not_started", 0),
        "informal_publication_rows": len(informal_rows),
        "legal_claim_anchor_rows": len(legal_claim_anchor_rows),
        "legal_claim_anchor_source_channel_count": len(legal_claim_anchor_channels),
        "legal_claim_anchor_source_channel_ids": list(legal_claim_anchor_channels),
        "lead_only_claim_rows": len(lead_only_claim_rows),
        "authenticity_volatility_review_rows": len(authenticity_volatility_review_rows),
        "informal_authenticity_volatility_review_rows": len(
            informal_authenticity_volatility_review_rows
        ),
        "rows_ready_for_manifest_promotion": sum(
            1 for row in review_rows if row["ready_for_manifest_promotion"]
        ),
        "ready_for_manifest_promotion": ready_flags["manifest_promotion"],
        "ready_for_prompt_generation": ready_flags["prompt_generation"],
        "ready_for_training_use": ready_flags["training_use"],
        "ready_for_public_claims": ready_flags["public_claims"],
        "ready_for_worker_facing_use": ready_flags["worker_facing_use"],
        "ready_for_comparable_scoring": ready_flags["comparable_scoring"],
        "policy": (
            "This packet is a blank curator intake artifact. It does not verify law, fill source "
            "metadata, promote manifests, create prompts, train models, publish claims, enable "
            "worker-facing use, or authorize comparable scoring."
        ),
    }
    checks = [
        _check(
            "source_channel_matrix_consistency_ok",
            matrix_doc["summary"]["consistency_ok"] is True,
            expected=True,
            actual=matrix_doc["summary"]["consistency_ok"],
        ),
        _check(
            "review_rows_match_matrix_rows",
            len(review_rows) == matrix_doc["summary"]["matrix_row_count"],
            expected=matrix_doc["summary"]["matrix_row_count"],
            actual=len(review_rows),
        ),
        _check(
            "all_rows_not_started",
            status_counts == {"not_started": len(review_rows)},
            expected={"not_started": len(review_rows)},
            actual=status_counts,
        ),
        _check(
            "all_readiness_flags_blocked",
            not any(ready_flags.values()),
            expected=False,
            actual=ready_flags,
        ),
        _check(
            "informal_publications_require_public_interest_review",
            all(row["public_interest_review_status"] == "not_started" for row in informal_rows),
            expected="not_started for each informal-publication row",
            actual={row["review_id"]: row["public_interest_review_status"] for row in informal_rows},
        ),
        _check(
            "informal_publications_remain_lead_only_claims",
            all(row["claim_use"] == "lead_only_never_standalone_legal_claim" for row in informal_rows),
            expected="lead_only_never_standalone_legal_claim",
            actual={row["review_id"]: row["claim_use"] for row in informal_rows},
        ),
        _check(
            "legal_claim_anchor_rows_are_official_law_or_admin",
            all(
                row["source_channel_id"] in legal_claim_anchor_channels
                for row in legal_claim_anchor_rows
            ),
            expected=legal_claim_anchor_channels,
            actual=sorted({row["source_channel_id"] for row in legal_claim_anchor_rows}),
        ),
        _check(
            "authority_and_corroboration_fields_present",
            all(
                row["authority_tier"]
                and row["claim_use"]
                and len(row["corroboration_required"]) >= 3
                for row in review_rows
            ),
            expected="authority_tier, claim_use, and at least 3 corroboration requirements",
            actual=min((len(row["corroboration_required"]) for row in review_rows), default=0),
        ),
        _check(
            "all_rows_require_authenticity_and_volatility_review",
            len(authenticity_volatility_review_rows) == len(review_rows),
            expected=len(review_rows),
            actual=len(authenticity_volatility_review_rows),
        ),
        _check(
            "informal_publications_keep_official_followup_boundary",
            all(
                "capture provenance and hash recorded" in row["authenticity_controls_required"]
                and "official-source follow-up target recorded" in row["volatility_controls_required"]
                and row["informal_publication_claim_boundary"]
                == "lead_only_until_authenticity_volatility_and_official_follow_up_review"
                for row in informal_rows
            ),
            expected=(
                "informal publications remain lead-only until authenticity, volatility, "
                "capture, and official-source follow-up review"
            ),
            actual={
                row["review_id"]: {
                    "authenticity_controls_required": row["authenticity_controls_required"],
                    "volatility_controls_required": row["volatility_controls_required"],
                    "informal_publication_claim_boundary": row[
                        "informal_publication_claim_boundary"
                    ],
                }
                for row in informal_rows
            },
        ),
        _check(
            "non_informal_rows_do_not_require_public_interest_review",
            all(
                row["public_interest_review_status"] == "not_required"
                for row in review_rows
                if row not in informal_rows
            ),
            expected="not_required for non-informal rows",
            actual=sum(
                1
                for row in review_rows
                if row not in informal_rows and row["public_interest_review_status"] != "not_required"
            ),
        ),
    ]
    doc = {
        "_meta": {
            "schema_version": "global_protections_source_channel_review_packet.v1",
            "project_config": _display_path(config_path),
            "registry_path": _display_path(registry_path),
            "regulatory_catalog_path": _display_path(regulatory_catalog_path),
            "status": (
                "blank source-channel review packet; not legal advice, not source verification, "
                "not prompt generation, not training data, and not comparable benchmark evidence"
            ),
        },
        "summary": summary,
        "review_rows": review_rows,
        "counts_by_status": status_counts,
        "checks": checks,
    }
    disallowed = _contains_disallowed_text(doc)
    scan = project_plan_builder._scan_privacy(doc)
    checks.extend([
        _check("review_packet_contains_no_disallowed_text", not disallowed, expected=[], actual=disallowed),
        _check("privacy_scan_ok", scan.get("ok") is True, expected=True, actual=scan.get("ok")),
    ])
    doc["summary"]["consistency_ok"] = all(check["ok"] for check in checks)
    return doc


def _md_cell(value: Any) -> str:
    text = str(value if value is not None else "")
    return text.replace("|", "\\|").replace("\n", " ").strip()


def build_markdown_report(doc: dict[str, Any]) -> str:
    """Render a compact Markdown source-channel review packet."""
    summary = doc["summary"]
    lines = [
        "# Global Protections Source-Channel Review Packet",
        "",
        (
            "This packet gives curators blank rows for source-channel candidate metadata. "
            "It is not legal advice, not source verification, not prompt generation, and not "
            "comparable benchmark evidence."
        ),
        "",
        "## Summary",
        "",
        "| Metric | Value |",
        "|---|---:|",
        f"| Consistency OK | {str(bool(summary['consistency_ok'])).lower()} |",
        f"| Matrix rows | {summary['matrix_row_count']} |",
        f"| Review rows | {summary['review_row_count']} |",
        f"| Not-started rows | {summary['not_started_rows']} |",
        f"| Informal publication rows | {summary['informal_publication_rows']} |",
        f"| Legal-claim anchor rows | {summary['legal_claim_anchor_rows']} |",
        (
            "| Legal-claim anchor source channels "
            f"| {summary['legal_claim_anchor_source_channel_count']} |"
        ),
        (
            "| Legal-claim anchor source channel IDs "
            f"| `{_md_cell(', '.join(summary['legal_claim_anchor_source_channel_ids']))}` |"
        ),
        f"| Lead-only claim rows | {summary['lead_only_claim_rows']} |",
        (
            "| Authenticity/volatility review rows "
            f"| {summary['authenticity_volatility_review_rows']} |"
        ),
        (
            "| Informal authenticity/volatility review rows "
            f"| {summary['informal_authenticity_volatility_review_rows']} |"
        ),
        f"| Rows ready for manifest promotion | {summary['rows_ready_for_manifest_promotion']} |",
        f"| Ready for prompt generation | {str(bool(summary['ready_for_prompt_generation'])).lower()} |",
        f"| Ready for comparable scoring | {str(bool(summary['ready_for_comparable_scoring'])).lower()} |",
        "",
        "## Review Rows",
        "",
        (
            "| Review ID | Matrix row | Jurisdiction family | Source channel | Authority tier "
            "| Claim use | Public-interest review |"
        ),
        "|---|---|---|---|---|---|---|",
    ]
    for row in doc["review_rows"]:
        lines.append(
            f"| `{_md_cell(row['review_id'])}` "
            f"| `{_md_cell(row['matrix_row_id'])}` "
            f"| {_md_cell(row['jurisdiction_family'])} "
            f"| `{_md_cell(row['source_channel_id'])}` "
            f"| {_md_cell(row['authority_tier'])} "
            f"| {_md_cell(row['claim_use'])} "
            f"| {_md_cell(row['public_interest_review_status'])} |"
        )
    lines.extend([
        "",
        "## Checks",
        "",
        "| Check | OK | Expected | Actual |",
        "|---|---:|---|---|",
    ])
    for check in doc["checks"]:
        lines.append(
            f"| {_md_cell(check['id'])} "
            f"| {str(bool(check['ok'])).lower()} "
            f"| {_md_cell(check['expected'])} "
            f"| {_md_cell(check['actual'])} |"
        )
    lines.extend([
        "",
        "## Non-Scoring Rule",
        "",
        summary["policy"],
        "",
    ])
    return "\n".join(lines)


def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--config", type=pathlib.Path, default=project_plan_builder.CONFIG)
    ap.add_argument("--registry", type=pathlib.Path, default=project_plan_builder.REGISTRY)
    ap.add_argument("--regulatory-catalog", type=pathlib.Path, default=project_plan_builder.REGULATORY_CATALOG)
    ap.add_argument("--out", type=pathlib.Path, default=OUT)
    ap.add_argument("--md-out", type=pathlib.Path, default=MD_OUT)
    ap.add_argument("--no-md", action="store_true", help="write only JSON, not the Markdown review packet")
    ap.add_argument("--validate", action="store_true", help="print the summary only; write nothing")
    args = ap.parse_args(argv)

    doc = build_source_channel_review_packet(
        config_path=args.config,
        registry_path=args.registry,
        regulatory_catalog_path=args.regulatory_catalog,
    )
    summary = doc["summary"]
    if args.validate:
        print(json.dumps({"summary": summary}, indent=2, ensure_ascii=False))
        return 0 if summary["consistency_ok"] else 1
    if not summary["consistency_ok"]:
        print(json.dumps({"summary": summary, "checks": doc["checks"]}, indent=2, ensure_ascii=False))
        print("[global-protections-source-channel-review-packet] packet is inconsistent; refusing to write")
        return 1

    args.out.parent.mkdir(parents=True, exist_ok=True)
    args.out.write_text(json.dumps(doc, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
    md_path = None
    if not args.no_md:
        md_path = args.md_out
        md_path.parent.mkdir(parents=True, exist_ok=True)
        md_path.write_text(build_markdown_report(doc) + "\n", encoding="utf-8")
    print(
        "[global-protections-source-channel-review-packet] "
        f"consistency_ok={str(bool(summary['consistency_ok'])).lower()}; "
        f"{summary['review_row_count']} review rows; "
        f"{summary['informal_publication_rows']} informal rows; "
        f"ready_for_comparable_scoring={str(bool(summary['ready_for_comparable_scoring'])).lower()} -> {args.out}"
        + (f"; report {md_path}" if md_path else "")
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
