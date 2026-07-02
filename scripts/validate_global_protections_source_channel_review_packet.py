#!/usr/bin/env python3
"""Validate a saved global-protections source-channel review packet.

The source-channel review packet is the generic intake surface for dated public
source metadata. This validator keeps the saved packet source-gated and
privacy-safe: row counts must match, ready flags must remain blocked, informal
publication rows stay lead-only, official-law claim anchors stay limited to
official law or administrative sources, date fields use ISO dates when filled,
and the saved summary can be compared to the current deterministic chain.

Offline + deterministic. No model, no network, no credits. Read-only.
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

import build_global_protections_project_plan as project_plan_builder  # noqa: E402
import build_global_protections_source_channel_review_packet as packet_builder  # noqa: E402

DEFAULT_PACKET = packet_builder.OUT
OUT = packet_builder.OUT_DIR / "global_protections_source_channel_review_packet_validation.json"
MD_OUT = packet_builder.OUT_DIR / "global_protections_source_channel_review_packet_validation.md"

REQUIRED_TOP_LEVEL = frozenset({
    "_meta",
    "summary",
    "review_rows",
    "counts_by_status",
    "checks",
})
ALLOWED_TOP_LEVEL = REQUIRED_TOP_LEVEL
REQUIRED_CHECK_IDS = frozenset({
    "source_channel_matrix_consistency_ok",
    "review_rows_match_matrix_rows",
    "all_rows_not_started",
    "all_readiness_flags_blocked",
    "informal_publications_require_public_interest_review",
    "informal_publications_remain_lead_only_claims",
    "legal_claim_anchor_rows_are_official_law_or_admin",
    "authority_and_corroboration_fields_present",
    "all_rows_require_authenticity_and_volatility_review",
    "informal_publications_keep_official_followup_boundary",
    "non_informal_rows_do_not_require_public_interest_review",
    "review_packet_contains_no_disallowed_text",
    "privacy_scan_ok",
})
REQUIRED_ROW_KEYS = frozenset({
    "review_id",
    "matrix_row_id",
    "jurisdiction_family",
    "jurisdiction_family_id",
    "source_channel_id",
    "source_channel_label",
    "source_role",
    "authority_tier",
    "claim_use",
    "source_channel_evidence_status",
    "status",
    "candidate_source_title",
    "issuing_or_publishing_authority",
    "concrete_jurisdiction_or_forum",
    "publication_or_access_date",
    "archive_status",
    "public_locator_status",
    "language",
    "claim_scope_note",
    "privacy_review_status",
    "source_path_review_status",
    "public_interest_review_status",
    "expert_review_status",
    "authenticity_review_status",
    "volatility_review_status",
    "authenticity_controls_required",
    "volatility_controls_required",
    "informal_publication_claim_boundary",
    "required_metadata",
    "review_gates",
    "corroboration_required",
    "rejection_triggers",
    "ready_for_manifest_promotion",
    "ready_for_prompt_generation",
    "ready_for_training_use",
    "ready_for_public_claims",
    "ready_for_worker_facing_use",
    "ready_for_comparable_scoring",
    "next_step",
})
READY_FLAG_KEYS = (
    "ready_for_manifest_promotion",
    "ready_for_prompt_generation",
    "ready_for_training_use",
    "ready_for_public_claims",
    "ready_for_worker_facing_use",
    "ready_for_comparable_scoring",
)
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
_REVIEW_ID = re.compile(r"^GPSCR-\d{3}$")
_ISO_DATE = re.compile(r"^\d{4}-\d{2}-\d{2}$")


def _display_path(path: pathlib.Path) -> str:
    try:
        return path.relative_to(_ROOT).as_posix()
    except ValueError:
        return path.as_posix()


def _load_json(path: pathlib.Path) -> Any:
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError):
        return None


def _check(check_id: str, ok: bool, *, expected: Any, actual: Any) -> dict[str, Any]:
    return {
        "id": check_id,
        "ok": bool(ok),
        "expected": expected,
        "actual": actual,
    }


def _failed_ids(checks: list[dict[str, Any]]) -> list[str]:
    return [str(check["id"]) for check in checks if check.get("ok") is not True]


def _counts_mismatches(doc: dict[str, Any]) -> list[dict[str, Any]]:
    summary = doc.get("summary") if isinstance(doc.get("summary"), dict) else {}
    rows = doc.get("review_rows") if isinstance(doc.get("review_rows"), list) else []
    status_counts: dict[str, int] = {}
    informal_rows = []
    legal_claim_anchor_rows = []
    lead_only_rows = []
    authenticity_volatility_rows = []
    informal_authenticity_volatility_rows = []
    ready_for_manifest = 0
    for row in rows:
        if not isinstance(row, dict):
            continue
        status = str(row.get("status") or "unknown")
        status_counts[status] = status_counts.get(status, 0) + 1
        if row.get("source_channel_id") == "social_channel_notice_or_scanned_circular":
            informal_rows.append(row)
        if str(row.get("claim_use", "")).startswith("may_support_legal_claim"):
            legal_claim_anchor_rows.append(row)
        if row.get("claim_use") == "lead_only_never_standalone_legal_claim":
            lead_only_rows.append(row)
        if row.get("authenticity_review_status") == "not_started" and row.get("volatility_review_status") == "not_started":
            if row.get("authenticity_controls_required") and row.get("volatility_controls_required"):
                authenticity_volatility_rows.append(row)
        if (
            row in informal_rows
            and row.get("informal_publication_claim_boundary")
            == "lead_only_until_authenticity_volatility_and_official_follow_up_review"
        ):
            informal_authenticity_volatility_rows.append(row)
        if row.get("ready_for_manifest_promotion") is True:
            ready_for_manifest += 1
    pairs = [
        ("review_row_count", len(rows)),
        ("not_started_rows", status_counts.get("not_started", 0)),
        ("informal_publication_rows", len(informal_rows)),
        ("legal_claim_anchor_rows", len(legal_claim_anchor_rows)),
        (
            "legal_claim_anchor_source_channel_count",
            len(packet_builder.matrix_builder.legal_claim_anchor_source_channel_ids()),
        ),
        (
            "legal_claim_anchor_source_channel_ids",
            packet_builder.matrix_builder.legal_claim_anchor_source_channel_ids(),
        ),
        ("lead_only_claim_rows", len(lead_only_rows)),
        ("authenticity_volatility_review_rows", len(authenticity_volatility_rows)),
        (
            "informal_authenticity_volatility_review_rows",
            len(informal_authenticity_volatility_rows),
        ),
        ("rows_ready_for_manifest_promotion", ready_for_manifest),
    ]
    return [
        {"summary_key": key, "expected": expected, "actual": summary.get(key)}
        for key, expected in pairs
        if summary.get(key) != expected
    ]


def _counts_by_status_drift(doc: dict[str, Any]) -> dict[str, Any]:
    rows = doc.get("review_rows") if isinstance(doc.get("review_rows"), list) else []
    expected: dict[str, int] = {}
    for row in rows:
        if isinstance(row, dict):
            status = str(row.get("status") or "unknown")
        else:
            status = "non_object_row"
        expected[status] = expected.get(status, 0) + 1
    actual = doc.get("counts_by_status")
    return {"expected": expected, "actual": actual}


def _row_shape_drift(doc: dict[str, Any]) -> list[dict[str, Any]]:
    findings: list[dict[str, Any]] = []
    rows = doc.get("review_rows") if isinstance(doc.get("review_rows"), list) else []
    for idx, row in enumerate(rows):
        if not isinstance(row, dict):
            findings.append({"row": idx, "rule": "review_row_object", "actual": type(row).__name__})
            continue
        missing = sorted(REQUIRED_ROW_KEYS - set(row))
        extra = sorted(set(row) - REQUIRED_ROW_KEYS)
        if missing or extra:
            findings.append({
                "row": row.get("review_id", idx),
                "missing": missing,
                "extra": extra,
            })
        if not isinstance(row.get("review_id"), str) or not _REVIEW_ID.fullmatch(row["review_id"]):
            findings.append({
                "row": row.get("review_id", idx),
                "rule": "review_id_format",
                "expected": "GPSCR-000",
                "actual": row.get("review_id"),
            })
    return findings


def _readiness_drift(doc: dict[str, Any]) -> list[str]:
    summary = doc.get("summary") if isinstance(doc.get("summary"), dict) else {}
    findings = [f"summary.{key}" for key in READY_FLAG_KEYS if summary.get(key) is not False]
    if summary.get("rows_ready_for_manifest_promotion") != 0:
        findings.append("summary.rows_ready_for_manifest_promotion")
    for idx, row in enumerate(doc.get("review_rows") or []):
        if not isinstance(row, dict):
            findings.append(f"review_rows[{idx}]")
            continue
        for key in READY_FLAG_KEYS:
            if row.get(key) is not False:
                findings.append(f"review_rows[{idx}].{key}")
    return findings


def _informal_policy_drift(doc: dict[str, Any]) -> list[dict[str, Any]]:
    findings: list[dict[str, Any]] = []
    rows = doc.get("review_rows") if isinstance(doc.get("review_rows"), list) else []
    for idx, row in enumerate(rows):
        if not isinstance(row, dict):
            continue
        informal = row.get("source_channel_id") == "social_channel_notice_or_scanned_circular"
        if informal:
            expected = {
                "public_interest_review_status": "not_started",
                "authority_tier": "informal_publication_lead",
                "claim_use": "lead_only_never_standalone_legal_claim",
                "boundary": "lead_only_until_authenticity_volatility_and_official_follow_up_review",
            }
            actual = {
                "public_interest_review_status": row.get("public_interest_review_status"),
                "authority_tier": row.get("authority_tier"),
                "claim_use": row.get("claim_use"),
                "boundary": row.get("informal_publication_claim_boundary"),
            }
            if actual != expected:
                findings.append({"row": row.get("review_id", idx), "expected": expected, "actual": actual})
            controls = row.get("authenticity_controls_required") or []
            volatility = row.get("volatility_controls_required") or []
            if (
                "capture provenance and hash recorded" not in controls
                or "official-source follow-up target recorded" not in volatility
            ):
                findings.append({
                    "row": row.get("review_id", idx),
                    "rule": "informal_controls_required",
                    "actual": {
                        "authenticity_controls_required": controls,
                        "volatility_controls_required": volatility,
                    },
                })
        elif row.get("public_interest_review_status") != "not_required":
            findings.append({
                "row": row.get("review_id", idx),
                "rule": "non_informal_public_interest_review_status",
                "expected": "not_required",
                "actual": row.get("public_interest_review_status"),
            })
    return findings


def _legal_anchor_drift(doc: dict[str, Any]) -> list[dict[str, Any]]:
    rows = doc.get("review_rows") if isinstance(doc.get("review_rows"), list) else []
    findings: list[dict[str, Any]] = []
    allowed = set(packet_builder.matrix_builder.legal_claim_anchor_source_channel_ids())
    for idx, row in enumerate(rows):
        if not isinstance(row, dict):
            continue
        if str(row.get("claim_use", "")).startswith("may_support_legal_claim") and row.get("source_channel_id") not in allowed:
            findings.append({
                "row": row.get("review_id", idx),
                "expected": sorted(allowed),
                "actual": row.get("source_channel_id"),
            })
    return findings


def _date_format_drift(doc: dict[str, Any]) -> list[dict[str, Any]]:
    rows = doc.get("review_rows") if isinstance(doc.get("review_rows"), list) else []
    findings: list[dict[str, Any]] = []
    for idx, row in enumerate(rows):
        if not isinstance(row, dict):
            continue
        value = row.get("publication_or_access_date")
        if value in ("", None):
            continue
        if not isinstance(value, str) or not _ISO_DATE.fullmatch(value.strip()):
            findings.append({"row": row.get("review_id", idx), "expected": "YYYY-MM-DD", "actual": value})
            continue
        try:
            _dt.date.fromisoformat(value)
        except ValueError:
            findings.append({"row": row.get("review_id", idx), "expected": "valid YYYY-MM-DD", "actual": value})
    return findings


def _embedded_check_drift(checks_value: Any) -> dict[str, Any]:
    checks = checks_value if isinstance(checks_value, list) else []
    check_ids = {str(check.get("id")) for check in checks if isinstance(check, dict)}
    failed = [
        str(check.get("id", "unknown"))
        for check in checks
        if not isinstance(check, dict) or check.get("ok") is not True
    ]
    return {
        "failed": sorted(failed),
        "missing_required": sorted(REQUIRED_CHECK_IDS - check_ids),
        "check_count": len(checks),
    }


def _current_reference(
    *,
    config_path: pathlib.Path,
    registry_path: pathlib.Path,
    regulatory_catalog_path: pathlib.Path,
) -> dict[str, Any]:
    return packet_builder.build_source_channel_review_packet(
        config_path=config_path,
        registry_path=registry_path,
        regulatory_catalog_path=regulatory_catalog_path,
    )


def validate_source_channel_review_packet(
    doc: Any,
    *,
    packet_path: pathlib.Path | None = None,
    config_path: pathlib.Path = project_plan_builder.CONFIG,
    registry_path: pathlib.Path = project_plan_builder.REGISTRY,
    regulatory_catalog_path: pathlib.Path = project_plan_builder.REGULATORY_CATALOG,
    compare_current_chain: bool = True,
) -> dict[str, Any]:
    if not isinstance(doc, dict):
        checks = [_check("packet_is_object", False, expected="object", actual=type(doc).__name__)]
        failed = _failed_ids(checks)
        return {
            "_meta": {
                "schema_version": "global_protections_source_channel_review_packet_validation.v1",
                "source_packet_path": _display_path(packet_path) if packet_path else "n/a",
                "compare_current_chain": compare_current_chain,
            },
            "summary": {
                "valid": False,
                "check_count": len(checks),
                "failed_check_count": len(failed),
                "failed_check_ids": failed,
                "ready_for_comparable_scoring": None,
            },
            "checks": checks,
        }

    summary = doc.get("summary") if isinstance(doc.get("summary"), dict) else {}
    encoded = json.dumps(doc, ensure_ascii=False)
    disallowed = [term for term in DISALLOWED_TERMS if term in encoded]
    privacy_scan = project_plan_builder._scan_privacy(doc)
    embedded = _embedded_check_drift(doc.get("checks"))
    status_drift = _counts_by_status_drift(doc)
    current = (
        _current_reference(
            config_path=config_path,
            registry_path=registry_path,
            regulatory_catalog_path=regulatory_catalog_path,
        )
        if compare_current_chain
        else None
    )
    current_summary = current["summary"] if current else None
    checks = [
        _check(
            "top_level_shape",
            REQUIRED_TOP_LEVEL.issubset(doc) and not (set(doc) - ALLOWED_TOP_LEVEL),
            expected=sorted(REQUIRED_TOP_LEVEL),
            actual=sorted(doc),
        ),
        _check(
            "review_row_shape",
            not _row_shape_drift(doc),
            expected=[],
            actual=_row_shape_drift(doc),
        ),
        _check(
            "summary_counts_match_rows",
            not _counts_mismatches(doc),
            expected=[],
            actual=_counts_mismatches(doc),
        ),
        _check(
            "counts_by_status_match_rows",
            status_drift["actual"] == status_drift["expected"],
            expected=status_drift["expected"],
            actual=status_drift["actual"],
        ),
        _check(
            "embedded_checks_all_ok",
            not embedded["failed"] and not embedded["missing_required"],
            expected={"failed": [], "missing_required": []},
            actual=embedded,
        ),
        _check(
            "all_readiness_flags_blocked",
            not _readiness_drift(doc),
            expected=[],
            actual=_readiness_drift(doc),
        ),
        _check(
            "informal_publications_stay_lead_only",
            not _informal_policy_drift(doc),
            expected=[],
            actual=_informal_policy_drift(doc),
        ),
        _check(
            "legal_claim_anchors_are_official_only",
            not _legal_anchor_drift(doc),
            expected=[],
            actual=_legal_anchor_drift(doc),
        ),
        _check(
            "publication_or_access_dates_are_iso_when_present",
            not _date_format_drift(doc),
            expected=[],
            actual=_date_format_drift(doc),
        ),
        _check(
            "privacy_scan_ok",
            privacy_scan.get("ok") is True,
            expected=True,
            actual=privacy_scan.get("counts"),
        ),
        _check(
            "packet_contains_no_disallowed_text",
            not disallowed,
            expected=[],
            actual=disallowed,
        ),
    ]
    if compare_current_chain:
        checks.append(
            _check(
                "summary_matches_current_chain",
                summary == current_summary,
                expected=current_summary,
                actual=summary,
            )
        )
    failed = _failed_ids(checks)
    return {
        "_meta": {
            "schema_version": "global_protections_source_channel_review_packet_validation.v1",
            "source_packet_path": _display_path(packet_path) if packet_path else "n/a",
            "project_config": _display_path(config_path),
            "registry_path": _display_path(registry_path),
            "regulatory_catalog_path": _display_path(regulatory_catalog_path),
            "compare_current_chain": compare_current_chain,
        },
        "summary": {
            "valid": not failed,
            "check_count": len(checks),
            "failed_check_count": len(failed),
            "failed_check_ids": failed,
            "review_row_count": summary.get("review_row_count"),
            "informal_publication_rows": summary.get("informal_publication_rows"),
            "legal_claim_anchor_rows": summary.get("legal_claim_anchor_rows"),
            "legal_claim_anchor_source_channel_count": summary.get(
                "legal_claim_anchor_source_channel_count"
            ),
            "legal_claim_anchor_source_channel_ids": summary.get(
                "legal_claim_anchor_source_channel_ids"
            ),
            "rows_ready_for_manifest_promotion": summary.get("rows_ready_for_manifest_promotion"),
            "ready_for_prompt_generation": summary.get("ready_for_prompt_generation"),
            "ready_for_comparable_scoring": summary.get("ready_for_comparable_scoring"),
        },
        "checks": checks,
    }


def _md_cell(value: Any) -> str:
    text = json.dumps(value, sort_keys=True) if isinstance(value, (dict, list)) else str(value)
    return text.replace("|", "\\|").replace("\n", " ").strip()


def render_markdown(report: dict[str, Any]) -> str:
    summary = report["summary"]
    lines = [
        "# Global Protections Source-Channel Review Packet Validation",
        "",
        "This read-only report validates the saved source-channel review packet before source-intake work is trusted.",
        "",
        "## Summary",
        "",
        "| Metric | Value |",
        "|---|---:|",
        f"| Valid | {str(bool(summary['valid'])).lower()} |",
        f"| Checks | {summary['check_count']} |",
        f"| Failed checks | {summary['failed_check_count']} |",
        f"| Review rows | {_md_cell(summary.get('review_row_count'))} |",
        f"| Informal publication rows | {_md_cell(summary.get('informal_publication_rows'))} |",
        f"| Legal-claim anchor rows | {_md_cell(summary.get('legal_claim_anchor_rows'))} |",
        f"| Legal-claim anchor source channels | {_md_cell(summary.get('legal_claim_anchor_source_channel_count'))} |",
        f"| Legal-claim anchor source channel IDs | {_md_cell(summary.get('legal_claim_anchor_source_channel_ids'))} |",
        f"| Rows ready for manifest promotion | {_md_cell(summary.get('rows_ready_for_manifest_promotion'))} |",
        f"| Ready for prompt generation | {str(bool(summary.get('ready_for_prompt_generation'))).lower()} |",
        f"| Ready for comparable scoring | {str(bool(summary.get('ready_for_comparable_scoring'))).lower()} |",
        "",
        "## Checks",
        "",
        "| Check | OK | Expected | Actual |",
        "|---|---:|---|---|",
    ]
    for check in report["checks"]:
        lines.append(
            f"| {_md_cell(check['id'])} "
            f"| {str(bool(check['ok'])).lower()} "
            f"| {_md_cell(check['expected'])} "
            f"| {_md_cell(check['actual'])} |"
        )
    if summary["failed_check_ids"]:
        lines.extend(["", "## Failed Check IDs", ""])
        for check_id in summary["failed_check_ids"]:
            lines.append(f"- `{check_id}`")
    lines.append("")
    return "\n".join(lines)


def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--packet", type=pathlib.Path, default=DEFAULT_PACKET)
    ap.add_argument("--config", type=pathlib.Path, default=project_plan_builder.CONFIG)
    ap.add_argument("--registry", type=pathlib.Path, default=project_plan_builder.REGISTRY)
    ap.add_argument("--regulatory-catalog", type=pathlib.Path, default=project_plan_builder.REGULATORY_CATALOG)
    ap.add_argument("--out", type=pathlib.Path, default=OUT)
    ap.add_argument("--markdown-out", type=pathlib.Path, default=MD_OUT)
    ap.add_argument("--no-current-chain", action="store_true", help="skip comparison to the current generated chain")
    ap.add_argument("--validate", action="store_true", help="print the validation summary only; write nothing")
    args = ap.parse_args(argv)

    doc = _load_json(args.packet)
    if doc is None:
        print(f"[global-protections-source-channel-review-packet-validation] unreadable packet: {args.packet}")
        return 1
    report = validate_source_channel_review_packet(
        doc,
        packet_path=args.packet,
        config_path=args.config,
        registry_path=args.registry,
        regulatory_catalog_path=args.regulatory_catalog,
        compare_current_chain=not args.no_current_chain,
    )
    summary = report["summary"]
    if args.validate:
        print(json.dumps(summary, indent=2, ensure_ascii=False))
        return 0 if summary["valid"] else 1

    args.out.parent.mkdir(parents=True, exist_ok=True)
    args.markdown_out.parent.mkdir(parents=True, exist_ok=True)
    args.out.write_text(json.dumps(report, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
    args.markdown_out.write_text(render_markdown(report), encoding="utf-8")
    print(
        "[global-protections-source-channel-review-packet-validation] "
        f"valid={str(bool(summary['valid'])).lower()}; "
        f"failed={summary['failed_check_count']}/{summary['check_count']}; "
        f"ready_for_comparable_scoring={str(bool(summary['ready_for_comparable_scoring'])).lower()} -> {args.packet}"
    )
    return 0 if summary["valid"] else 1


if __name__ == "__main__":
    raise SystemExit(main())
