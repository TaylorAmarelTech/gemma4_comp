#!/usr/bin/env python3
"""Validate a saved global-protections source-channel matrix.

The source-channel matrix is the source-discovery scaffold for the global
protections sister project. This validator keeps a saved matrix compact and
safe: every jurisdiction family must retain each source channel, informal
publication rows stay lead-only, legal-claim anchors stay limited to official
law or administrative sources, all readiness flags remain blocked, and the
saved matrix can be compared to the current deterministic chain.

Offline + deterministic. No model, no network, no credits. Read-only.
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

import build_global_protections_project_plan as project_plan_builder  # noqa: E402
import build_global_protections_source_channel_matrix as matrix_builder  # noqa: E402

DEFAULT_MATRIX = matrix_builder.OUT
OUT = matrix_builder.OUT_DIR / "global_protections_source_channel_matrix_validation.json"
MD_OUT = matrix_builder.OUT_DIR / "global_protections_source_channel_matrix_validation.md"

REQUIRED_TOP_LEVEL = frozenset({
    "_meta",
    "summary",
    "source_channels",
    "matrix_rows",
    "counts_by_source_channel",
    "checks",
})
ALLOWED_TOP_LEVEL = REQUIRED_TOP_LEVEL
REQUIRED_CHECK_IDS = frozenset({
    "project_plan_safe",
    "source_channel_rows_present",
    "each_family_has_each_source_channel",
    "informal_publication_rows_are_lead_only",
    "informal_publications_never_anchor_legal_claims",
    "legal_claim_anchors_are_primary_or_admin_official",
    "all_readiness_flags_blocked",
    "metadata_fields_present",
    "authority_and_corroboration_fields_present",
    "all_rows_have_authenticity_and_volatility_controls",
    "informal_publications_require_authenticity_volatility_and_official_followup",
    "matrix_contains_no_disallowed_text",
    "privacy_scan_ok",
})
REQUIRED_SOURCE_CHANNEL_KEYS = frozenset({
    "id",
    "label",
    "source_role",
    "authority_tier",
    "claim_use",
    "priority",
    "evidence_status",
    "informal_publication",
})
REQUIRED_MATRIX_ROW_KEYS = frozenset({
    "id",
    "jurisdiction_family",
    "jurisdiction_family_id",
    "source_channel_id",
    "source_channel_label",
    "source_role",
    "authority_tier",
    "claim_use",
    "priority",
    "evidence_status",
    "informal_publication",
    "required_metadata",
    "review_gates",
    "corroboration_required",
    "rejection_triggers",
    "authenticity_controls_required",
    "volatility_controls_required",
    "authenticity_volatility_status",
    "informal_publication_claim_boundary",
    "ready_for_manifest_promotion",
    "ready_for_prompt_generation",
    "ready_for_training_use",
    "ready_for_public_claims",
    "ready_for_worker_facing_use",
    "ready_for_comparable_scoring",
    "blocks",
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
EXPECTED_BLOCKS = [
    "manifest_promotion",
    "prompt_generation",
    "training_use",
    "public_claims",
    "worker_facing_use",
    "comparable_scoring",
]
DISALLOWED_TERMS = matrix_builder.DISALLOWED_TERMS
_CHANNEL_ID = re.compile(r"^[a-z][a-z0-9_]{2,90}$")
_ROW_ID = re.compile(r"^GPSC-\d{2}-[a-z][a-z0-9_]{2,90}$")


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


def _source_channel_shape_drift(doc: dict[str, Any]) -> list[dict[str, Any]]:
    findings: list[dict[str, Any]] = []
    channels = doc.get("source_channels") if isinstance(doc.get("source_channels"), list) else []
    ids: list[Any] = []
    priorities: list[Any] = []
    for idx, channel in enumerate(channels):
        if not isinstance(channel, dict):
            findings.append({"channel": idx, "rule": "source_channel_object", "actual": type(channel).__name__})
            continue
        ids.append(channel.get("id"))
        priorities.append(channel.get("priority"))
        missing = sorted(REQUIRED_SOURCE_CHANNEL_KEYS - set(channel))
        extra = sorted(set(channel) - REQUIRED_SOURCE_CHANNEL_KEYS)
        if missing or extra:
            findings.append({"channel": channel.get("id", idx), "missing": missing, "extra": extra})
        if not isinstance(channel.get("id"), str) or not _CHANNEL_ID.fullmatch(channel["id"]):
            findings.append({
                "channel": channel.get("id", idx),
                "rule": "source_channel_id_format",
                "expected": "lowercase_slug",
                "actual": channel.get("id"),
            })
        if channel.get("informal_publication") not in (True, False):
            findings.append({
                "channel": channel.get("id", idx),
                "rule": "informal_publication_boolean",
                "expected": "boolean",
                "actual": channel.get("informal_publication"),
            })
    duplicates = sorted([item for item, count in Counter(ids).items() if count > 1])
    if duplicates:
        findings.append({"rule": "source_channel_ids_unique", "expected": [], "actual": duplicates})
    if priorities != sorted(priorities):
        findings.append({"rule": "source_channel_priorities_sorted", "expected": sorted(priorities), "actual": priorities})
    return findings


def _matrix_row_shape_drift(doc: dict[str, Any]) -> list[dict[str, Any]]:
    findings: list[dict[str, Any]] = []
    rows = doc.get("matrix_rows") if isinstance(doc.get("matrix_rows"), list) else []
    row_ids: list[Any] = []
    for idx, row in enumerate(rows):
        if not isinstance(row, dict):
            findings.append({"row": idx, "rule": "matrix_row_object", "actual": type(row).__name__})
            continue
        row_ids.append(row.get("id"))
        missing = sorted(REQUIRED_MATRIX_ROW_KEYS - set(row))
        extra = sorted(set(row) - REQUIRED_MATRIX_ROW_KEYS)
        if missing or extra:
            findings.append({"row": row.get("id", idx), "missing": missing, "extra": extra})
        if not isinstance(row.get("id"), str) or not _ROW_ID.fullmatch(row["id"]):
            findings.append({
                "row": row.get("id", idx),
                "rule": "matrix_row_id_format",
                "expected": "GPSC-00-source_channel_slug",
                "actual": row.get("id"),
            })
        if isinstance(row.get("source_channel_id"), str) and isinstance(row.get("id"), str):
            if not row["id"].endswith(f"-{row['source_channel_id']}"):
                findings.append({
                    "row": row.get("id", idx),
                    "rule": "row_id_suffix_matches_source_channel",
                    "expected": row.get("source_channel_id"),
                    "actual": row.get("id"),
                })
    duplicates = sorted([item for item, count in Counter(row_ids).items() if count > 1])
    if duplicates:
        findings.append({"rule": "matrix_row_ids_unique", "expected": [], "actual": duplicates})
    return findings


def _summary_counts_mismatches(doc: dict[str, Any]) -> list[dict[str, Any]]:
    summary = doc.get("summary") if isinstance(doc.get("summary"), dict) else {}
    channels = doc.get("source_channels") if isinstance(doc.get("source_channels"), list) else []
    rows = doc.get("matrix_rows") if isinstance(doc.get("matrix_rows"), list) else []
    object_channels = [channel for channel in channels if isinstance(channel, dict)]
    object_rows = [row for row in rows if isinstance(row, dict)]
    families = sorted({str(row.get("jurisdiction_family_id")) for row in object_rows})
    authority_tiers = sorted({str(row.get("authority_tier")) for row in object_rows})
    informal_rows = [row for row in object_rows if row.get("informal_publication") is True]
    lead_only_rows = [row for row in object_rows if "lead_only" in str(row.get("evidence_status"))]
    legal_claim_anchor_rows = [
        row for row in object_rows if str(row.get("claim_use", "")).startswith("may_support_legal_claim")
    ]
    authenticity_volatility_rows = [
        row
        for row in object_rows
        if row.get("authenticity_controls_required") and row.get("volatility_controls_required")
    ]
    informal_authenticity_rows = [
        row
        for row in informal_rows
        if row.get("informal_publication_claim_boundary")
        == "lead_only_until_authenticity_volatility_and_official_follow_up_review"
    ]
    pairs = [
        ("jurisdiction_family_count", len(families)),
        ("source_channel_count", len(object_channels)),
        ("authority_tier_count", len(authority_tiers)),
        ("matrix_row_count", len(object_rows)),
        ("informal_publication_rows", len(informal_rows)),
        ("lead_only_rows", len(lead_only_rows)),
        ("legal_claim_anchor_rows", len(legal_claim_anchor_rows)),
        (
            "legal_claim_anchor_source_channel_count",
            len(matrix_builder.legal_claim_anchor_source_channel_ids()),
        ),
        (
            "legal_claim_anchor_source_channel_ids",
            matrix_builder.legal_claim_anchor_source_channel_ids(),
        ),
        ("authenticity_volatility_control_rows", len(authenticity_volatility_rows)),
        ("informal_authenticity_volatility_control_rows", len(informal_authenticity_rows)),
    ]
    return [
        {"summary_key": key, "expected": expected, "actual": summary.get(key)}
        for key, expected in pairs
        if summary.get(key) != expected
    ]


def _counts_by_source_channel_drift(doc: dict[str, Any]) -> dict[str, Any]:
    rows = doc.get("matrix_rows") if isinstance(doc.get("matrix_rows"), list) else []
    channels = doc.get("source_channels") if isinstance(doc.get("source_channels"), list) else []
    expected = {
        str(channel.get("id")): 0
        for channel in channels
        if isinstance(channel, dict) and isinstance(channel.get("id"), str)
    }
    for row in rows:
        if isinstance(row, dict):
            channel_id = str(row.get("source_channel_id") or "unknown")
        else:
            channel_id = "non_object_row"
        expected[channel_id] = expected.get(channel_id, 0) + 1
    return {"expected": expected, "actual": doc.get("counts_by_source_channel")}


def _cross_product_drift(doc: dict[str, Any]) -> dict[str, Any]:
    rows = doc.get("matrix_rows") if isinstance(doc.get("matrix_rows"), list) else []
    channels = doc.get("source_channels") if isinstance(doc.get("source_channels"), list) else []
    channel_ids = [
        channel.get("id")
        for channel in channels
        if isinstance(channel, dict) and isinstance(channel.get("id"), str)
    ]
    family_ids = [
        row.get("jurisdiction_family_id")
        for row in rows
        if isinstance(row, dict) and isinstance(row.get("jurisdiction_family_id"), str)
    ]
    unique_family_ids = sorted(set(family_ids))
    expected_pairs = {(family_id, channel_id) for family_id in unique_family_ids for channel_id in channel_ids}
    actual_pairs = [
        (row.get("jurisdiction_family_id"), row.get("source_channel_id"))
        for row in rows
        if isinstance(row, dict)
    ]
    counts = Counter(actual_pairs)
    actual_set = set(actual_pairs)
    duplicates = [pair for pair, count in counts.items() if count > 1]
    return {
        "missing_pairs": sorted(expected_pairs - actual_set),
        "extra_pairs": sorted(actual_set - expected_pairs),
        "duplicate_pairs": sorted(duplicates),
        "expected_pair_count": len(expected_pairs),
        "actual_pair_count": len(actual_pairs),
    }


def _readiness_drift(doc: dict[str, Any]) -> list[str]:
    summary = doc.get("summary") if isinstance(doc.get("summary"), dict) else {}
    findings = [f"summary.{key}" for key in READY_FLAG_KEYS if summary.get(key) is not False]
    rows = doc.get("matrix_rows") if isinstance(doc.get("matrix_rows"), list) else []
    for idx, row in enumerate(rows):
        if not isinstance(row, dict):
            findings.append(f"matrix_rows[{idx}]")
            continue
        for key in READY_FLAG_KEYS:
            if row.get(key) is not False:
                findings.append(f"matrix_rows[{idx}].{key}")
    return findings


def _policy_drift(doc: dict[str, Any]) -> list[dict[str, Any]]:
    findings: list[dict[str, Any]] = []
    rows = doc.get("matrix_rows") if isinstance(doc.get("matrix_rows"), list) else []
    for idx, row in enumerate(rows):
        if not isinstance(row, dict):
            continue
        row_id = row.get("id", idx)
        informal = (
            row.get("informal_publication") is True
            or row.get("source_channel_id") == "social_channel_notice_or_scanned_circular"
        )
        required_metadata = row.get("required_metadata") if isinstance(row.get("required_metadata"), list) else []
        corroboration = row.get("corroboration_required") if isinstance(row.get("corroboration_required"), list) else []
        authenticity = (
            row.get("authenticity_controls_required")
            if isinstance(row.get("authenticity_controls_required"), list)
            else []
        )
        volatility = (
            row.get("volatility_controls_required")
            if isinstance(row.get("volatility_controls_required"), list)
            else []
        )
        if len(required_metadata) < 5:
            findings.append({"row": row_id, "rule": "required_metadata_count", "expected": ">=5", "actual": len(required_metadata)})
        if len(corroboration) < 3:
            findings.append({"row": row_id, "rule": "corroboration_required_count", "expected": ">=3", "actual": len(corroboration)})
        if not authenticity or not volatility or row.get("authenticity_volatility_status") != "not_started":
            findings.append({
                "row": row_id,
                "rule": "authenticity_volatility_controls",
                "expected": "controls present and status not_started",
                "actual": {
                    "authenticity_controls_required": authenticity,
                    "volatility_controls_required": volatility,
                    "authenticity_volatility_status": row.get("authenticity_volatility_status"),
                },
            })
        if row.get("blocks") != EXPECTED_BLOCKS:
            findings.append({"row": row_id, "rule": "blocked_uses", "expected": EXPECTED_BLOCKS, "actual": row.get("blocks")})
        if informal:
            expected = {
                "authority_tier": "informal_publication_lead",
                "claim_use": "lead_only_never_standalone_legal_claim",
                "boundary": "lead_only_until_authenticity_volatility_and_official_follow_up_review",
            }
            actual = {
                "authority_tier": row.get("authority_tier"),
                "claim_use": row.get("claim_use"),
                "boundary": row.get("informal_publication_claim_boundary"),
            }
            if actual != expected or "lead_only" not in str(row.get("evidence_status")):
                findings.append({
                    "row": row_id,
                    "rule": "informal_publication_lead_only_boundary",
                    "expected": expected,
                    "actual": actual | {"evidence_status": row.get("evidence_status")},
                })
            if (
                "capture provenance and hash recorded" not in authenticity
                or "official-source follow-up target recorded" not in volatility
            ):
                findings.append({
                    "row": row_id,
                    "rule": "informal_authenticity_volatility_controls",
                    "expected": [
                        "capture provenance and hash recorded",
                        "official-source follow-up target recorded",
                    ],
                    "actual": {
                        "authenticity_controls_required": authenticity,
                        "volatility_controls_required": volatility,
                    },
                })
        elif row.get("informal_publication_claim_boundary") != "not_applicable":
            findings.append({
                "row": row_id,
                "rule": "non_informal_boundary",
                "expected": "not_applicable",
                "actual": row.get("informal_publication_claim_boundary"),
            })
    return findings


def _legal_anchor_drift(doc: dict[str, Any]) -> list[dict[str, Any]]:
    rows = doc.get("matrix_rows") if isinstance(doc.get("matrix_rows"), list) else []
    allowed = set(matrix_builder.legal_claim_anchor_source_channel_ids())
    findings: list[dict[str, Any]] = []
    for idx, row in enumerate(rows):
        if not isinstance(row, dict):
            continue
        if str(row.get("claim_use", "")).startswith("may_support_legal_claim") and row.get("source_channel_id") not in allowed:
            findings.append({
                "row": row.get("id", idx),
                "expected": sorted(allowed),
                "actual": row.get("source_channel_id"),
            })
    return findings


def _current_reference(
    *,
    config_path: pathlib.Path,
    registry_path: pathlib.Path,
    regulatory_catalog_path: pathlib.Path,
) -> dict[str, Any]:
    return matrix_builder.build_source_channel_matrix(
        config_path=config_path,
        registry_path=registry_path,
        regulatory_catalog_path=regulatory_catalog_path,
    )


def _comparable_sections(doc: dict[str, Any]) -> dict[str, Any]:
    return {
        "summary": doc.get("summary"),
        "source_channels": doc.get("source_channels"),
        "matrix_rows": doc.get("matrix_rows"),
        "counts_by_source_channel": doc.get("counts_by_source_channel"),
        "checks": doc.get("checks"),
    }


def validate_source_channel_matrix(
    doc: Any,
    *,
    matrix_path: pathlib.Path | None = None,
    config_path: pathlib.Path = project_plan_builder.CONFIG,
    registry_path: pathlib.Path = project_plan_builder.REGISTRY,
    regulatory_catalog_path: pathlib.Path = project_plan_builder.REGULATORY_CATALOG,
    compare_current_chain: bool = True,
) -> dict[str, Any]:
    if not isinstance(doc, dict):
        checks = [_check("matrix_is_object", False, expected="object", actual=type(doc).__name__)]
        failed = _failed_ids(checks)
        return {
            "_meta": {
                "schema_version": "global_protections_source_channel_matrix_validation.v1",
                "source_matrix_path": _display_path(matrix_path) if matrix_path else "n/a",
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
    channel_counts = _counts_by_source_channel_drift(doc)
    cross_product = _cross_product_drift(doc)
    current = (
        _current_reference(
            config_path=config_path,
            registry_path=registry_path,
            regulatory_catalog_path=regulatory_catalog_path,
        )
        if compare_current_chain
        else None
    )
    current_sections = _comparable_sections(current) if current else None
    checks = [
        _check(
            "top_level_shape",
            REQUIRED_TOP_LEVEL.issubset(doc) and not (set(doc) - ALLOWED_TOP_LEVEL),
            expected=sorted(REQUIRED_TOP_LEVEL),
            actual=sorted(doc),
        ),
        _check(
            "summary_consistency_ok",
            summary.get("consistency_ok") is True and summary.get("safe_for_project_planning") is True,
            expected={"consistency_ok": True, "safe_for_project_planning": True},
            actual={
                "consistency_ok": summary.get("consistency_ok"),
                "safe_for_project_planning": summary.get("safe_for_project_planning"),
            },
        ),
        _check(
            "source_channel_shape",
            not _source_channel_shape_drift(doc),
            expected=[],
            actual=_source_channel_shape_drift(doc),
        ),
        _check(
            "matrix_row_shape",
            not _matrix_row_shape_drift(doc),
            expected=[],
            actual=_matrix_row_shape_drift(doc),
        ),
        _check(
            "summary_counts_match_matrix",
            not _summary_counts_mismatches(doc),
            expected=[],
            actual=_summary_counts_mismatches(doc),
        ),
        _check(
            "counts_by_source_channel_match_rows",
            channel_counts["actual"] == channel_counts["expected"],
            expected=channel_counts["expected"],
            actual=channel_counts["actual"],
        ),
        _check(
            "embedded_checks_all_ok",
            not embedded["failed"] and not embedded["missing_required"],
            expected={"failed": [], "missing_required": []},
            actual=embedded,
        ),
        _check(
            "each_family_has_each_source_channel",
            not cross_product["missing_pairs"]
            and not cross_product["extra_pairs"]
            and not cross_product["duplicate_pairs"]
            and cross_product["actual_pair_count"] == cross_product["expected_pair_count"],
            expected={
                "missing_pairs": [],
                "extra_pairs": [],
                "duplicate_pairs": [],
                "actual_pair_count": cross_product["expected_pair_count"],
            },
            actual=cross_product,
        ),
        _check(
            "all_readiness_flags_blocked",
            not _readiness_drift(doc),
            expected=[],
            actual=_readiness_drift(doc),
        ),
        _check(
            "source_channel_policy_boundaries_intact",
            not _policy_drift(doc),
            expected=[],
            actual=_policy_drift(doc),
        ),
        _check(
            "legal_claim_anchors_are_official_only",
            not _legal_anchor_drift(doc),
            expected=[],
            actual=_legal_anchor_drift(doc),
        ),
        _check(
            "privacy_scan_ok",
            privacy_scan.get("ok") is True,
            expected=True,
            actual=privacy_scan.get("counts"),
        ),
        _check(
            "matrix_contains_no_disallowed_text",
            not disallowed,
            expected=[],
            actual=disallowed,
        ),
    ]
    if compare_current_chain:
        checks.append(
            _check(
                "matrix_matches_current_chain",
                _comparable_sections(doc) == current_sections,
                expected=current_sections,
                actual=_comparable_sections(doc),
            )
        )
    failed = _failed_ids(checks)
    return {
        "_meta": {
            "schema_version": "global_protections_source_channel_matrix_validation.v1",
            "source_matrix_path": _display_path(matrix_path) if matrix_path else "n/a",
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
            "jurisdiction_family_count": summary.get("jurisdiction_family_count"),
            "source_channel_count": summary.get("source_channel_count"),
            "matrix_row_count": summary.get("matrix_row_count"),
            "informal_publication_rows": summary.get("informal_publication_rows"),
            "legal_claim_anchor_rows": summary.get("legal_claim_anchor_rows"),
            "legal_claim_anchor_source_channel_count": summary.get(
                "legal_claim_anchor_source_channel_count"
            ),
            "legal_claim_anchor_source_channel_ids": summary.get(
                "legal_claim_anchor_source_channel_ids"
            ),
            "ready_for_manifest_promotion": summary.get("ready_for_manifest_promotion"),
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
        "# Global Protections Source-Channel Matrix Validation",
        "",
        "This read-only report validates the saved source-channel matrix before source-discovery work is trusted.",
        "",
        "## Summary",
        "",
        "| Metric | Value |",
        "|---|---:|",
        f"| Valid | {str(bool(summary['valid'])).lower()} |",
        f"| Checks | {summary['check_count']} |",
        f"| Failed checks | {summary['failed_check_count']} |",
        f"| Jurisdiction families | {_md_cell(summary.get('jurisdiction_family_count'))} |",
        f"| Source channels | {_md_cell(summary.get('source_channel_count'))} |",
        f"| Matrix rows | {_md_cell(summary.get('matrix_row_count'))} |",
        f"| Informal publication rows | {_md_cell(summary.get('informal_publication_rows'))} |",
        f"| Legal-claim anchor rows | {_md_cell(summary.get('legal_claim_anchor_rows'))} |",
        f"| Legal-claim anchor source channels | {_md_cell(summary.get('legal_claim_anchor_source_channel_count'))} |",
        f"| Legal-claim anchor source channel IDs | {_md_cell(summary.get('legal_claim_anchor_source_channel_ids'))} |",
        f"| Ready for manifest promotion | {str(bool(summary.get('ready_for_manifest_promotion'))).lower()} |",
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
    ap.add_argument("--matrix", type=pathlib.Path, default=DEFAULT_MATRIX)
    ap.add_argument("--config", type=pathlib.Path, default=project_plan_builder.CONFIG)
    ap.add_argument("--registry", type=pathlib.Path, default=project_plan_builder.REGISTRY)
    ap.add_argument("--regulatory-catalog", type=pathlib.Path, default=project_plan_builder.REGULATORY_CATALOG)
    ap.add_argument("--out", type=pathlib.Path, default=OUT)
    ap.add_argument("--markdown-out", type=pathlib.Path, default=MD_OUT)
    ap.add_argument("--no-current-chain", action="store_true", help="skip comparison to the current generated chain")
    ap.add_argument("--validate", action="store_true", help="print the validation summary only; write nothing")
    args = ap.parse_args(argv)

    doc = _load_json(args.matrix)
    if doc is None:
        print(f"[global-protections-source-channel-matrix-validation] unreadable matrix: {args.matrix}")
        return 1
    report = validate_source_channel_matrix(
        doc,
        matrix_path=args.matrix,
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
        "[global-protections-source-channel-matrix-validation] "
        f"valid={str(bool(summary['valid'])).lower()}; "
        f"failed={summary['failed_check_count']}/{summary['check_count']}; "
        f"ready_for_comparable_scoring={str(bool(summary['ready_for_comparable_scoring'])).lower()} -> {args.matrix}"
    )
    return 0 if summary["valid"] else 1


if __name__ == "__main__":
    raise SystemExit(main())
