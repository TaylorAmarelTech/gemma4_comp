#!/usr/bin/env python3
"""Validate a saved global-protections curator sprint packet.

The curator sprint packet is the handoff closest to human review work. This
validator checks that a saved sprint remains a source-gated, privacy-safe
operations packet: summary counts match the worklists, readiness stays blocked,
regulatory candidate ranks are preserved, source-review rows cannot be mistaken
for accepted source objects, and the saved summary matches the current
deterministic chain.

Offline + deterministic. No model, no network, no credits. Read-only.
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

import build_global_protections_curator_sprint as sprint_builder  # noqa: E402
import build_global_protections_project_plan as project_plan_builder  # noqa: E402
import build_global_protections_source_channel_matrix as source_matrix_builder  # noqa: E402

DEFAULT_SPRINT = sprint_builder.OUT
DEFAULT_DOMAIN = sprint_builder.DEFAULT_DOMAIN
OUT = sprint_builder.OUT_DIR / "global_protections_curator_sprint_validation.json"
MD_OUT = sprint_builder.OUT_DIR / "global_protections_curator_sprint_validation.md"

REQUIRED_TOP_LEVEL = frozenset({
    "_meta",
    "summary",
    "scope_resolution_items",
    "source_review_items",
    "regulatory_candidate_intake_items",
    "blocked_later_items",
    "execution_phase_summary",
    "exit_gates",
    "checks",
    "artifact_paths",
})
ALLOWED_TOP_LEVEL = REQUIRED_TOP_LEVEL
REQUIRED_CHECK_IDS = frozenset({
    "sprint_item_count_matches_immediate_actions",
    "regulatory_priority_queue_matches_backlog",
    "regulatory_top_candidate_first",
    "all_public_and_scoring_flags_blocked",
    "execution_phase_summary_matches_backlog",
    "execution_phase_readiness_stays_blocked",
    "legal_claim_anchor_source_channels_preserved",
    "sprint_contains_no_disallowed_text",
    "privacy_scan_ok",
})
REQUIRED_ARTIFACT_KEYS = frozenset({
    "project_plan_json",
    "project_plan_markdown",
    "domain_curation_bundle_json",
    "domain_curation_bundle_markdown",
    "regulatory_curation_bundle_json",
    "regulatory_curation_bundle_markdown",
    "global_protections_readiness_bundle_json",
    "global_protections_readiness_bundle_markdown",
    "global_protections_next_actions_json",
    "global_protections_next_actions_markdown",
    "global_protections_curator_sprint_json",
    "global_protections_curator_sprint_markdown",
})
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
READY_FLAG_KEYS = (
    "ready_for_prompt_generation",
    "ready_for_training_use",
    "ready_for_public_claims",
    "ready_for_worker_facing_use",
    "ready_for_comparable_scoring",
)
_URL = re.compile(r"\b(?:https?://|www\.)", re.I)


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


def _unsafe_artifact_paths(paths: Any) -> list[dict[str, str]]:
    if not isinstance(paths, dict):
        return [{"key": "$", "value": "artifact_paths_not_object"}]
    findings: list[dict[str, str]] = []
    for key, value in paths.items():
        if not isinstance(value, str) or not value.strip():
            findings.append({"key": str(key), "value": "missing_or_not_string"})
            continue
        if "\\" in value or _URL.search(value):
            findings.append({"key": str(key), "value": value})
    return findings


def _redacted_privacy_view(doc: dict[str, Any]) -> dict[str, Any]:
    view = json.loads(json.dumps(doc))
    if isinstance(view.get("artifact_paths"), dict):
        view["artifact_paths"] = {
            str(key): "artifact-path-redacted"
            for key in view["artifact_paths"]
        }
    return view


def _counts_mismatches(doc: dict[str, Any]) -> list[dict[str, Any]]:
    summary = doc.get("summary") if isinstance(doc.get("summary"), dict) else {}
    scope_items = doc.get("scope_resolution_items") if isinstance(doc.get("scope_resolution_items"), list) else []
    source_items = doc.get("source_review_items") if isinstance(doc.get("source_review_items"), list) else []
    regulatory_items = (
        doc.get("regulatory_candidate_intake_items")
        if isinstance(doc.get("regulatory_candidate_intake_items"), list)
        else []
    )
    blocked_items = doc.get("blocked_later_items") if isinstance(doc.get("blocked_later_items"), list) else []
    phase_rows = (
        doc.get("execution_phase_summary")
        if isinstance(doc.get("execution_phase_summary"), list)
        else []
    )
    pairs = [
        ("execution_phase_count", len(phase_rows)),
        ("scope_resolution_items", len(scope_items)),
        ("source_review_items", len(source_items)),
        ("regulatory_candidate_intake_items", len(regulatory_items)),
        ("regulatory_priority_queue_items", len(regulatory_items)),
        ("blocked_later_items", len(blocked_items)),
        ("sprint_item_count", len(scope_items) + len(source_items) + len(regulatory_items)),
    ]
    return [
        {"summary_key": key, "expected": expected, "actual": summary.get(key)}
        for key, expected in pairs
        if summary.get(key) != expected
    ]


def _execution_phase_covered_action_count(doc: dict[str, Any]) -> int:
    phases = (
        doc.get("execution_phase_summary")
        if isinstance(doc.get("execution_phase_summary"), list)
        else []
    )
    covered_ids = {
        str(action_id)
        for phase in phases
        if isinstance(phase, dict)
        for key in ("sprint_action_ids", "blocked_later_action_ids")
        for action_id in (phase.get(key) if isinstance(phase.get(key), list) else [])
    }
    return len(covered_ids)


def _phase_summary_drift(doc: dict[str, Any]) -> list[dict[str, Any]]:
    phases = doc.get("execution_phase_summary")
    if not isinstance(phases, list):
        return [{"rule": "execution_phase_summary_list", "actual": type(phases).__name__}]
    sprint_ids = [
        str(item.get("backlog_action_id"))
        for section in (
            doc.get("scope_resolution_items"),
            doc.get("source_review_items"),
            doc.get("regulatory_candidate_intake_items"),
        )
        if isinstance(section, list)
        for item in section
        if isinstance(item, dict) and item.get("backlog_action_id")
    ]
    blocked_ids = [
        str(item.get("backlog_action_id"))
        for item in (doc.get("blocked_later_items") if isinstance(doc.get("blocked_later_items"), list) else [])
        if isinstance(item, dict) and item.get("backlog_action_id")
    ]
    expected_ids = sorted([*sprint_ids, *blocked_ids])
    findings: list[dict[str, Any]] = []
    required = {
        "phase_id",
        "order",
        "label",
        "depends_on_phase_ids",
        "completion_gate",
        "backlog_action_count",
        "sprint_action_ids",
        "blocked_later_action_ids",
        "required_legal_claim_anchor_source_channel_ids",
        "readiness_after_phase",
    }
    phase_ids: list[str] = []
    orders: list[Any] = []
    covered_sprint_ids: list[str] = []
    covered_blocked_ids: list[str] = []
    for idx, phase in enumerate(phases):
        if not isinstance(phase, dict):
            findings.append({"index": idx, "rule": "phase_summary_object", "actual": type(phase).__name__})
            continue
        phase_id = str(phase.get("phase_id") or "")
        phase_ids.append(phase_id)
        orders.append(phase.get("order"))
        missing = sorted(required - set(phase))
        if missing:
            findings.append({"phase_id": phase_id or idx, "rule": "required_keys", "missing": missing})
        sprint_action_ids = phase.get("sprint_action_ids")
        blocked_later_action_ids = phase.get("blocked_later_action_ids")
        if not isinstance(sprint_action_ids, list):
            findings.append({"phase_id": phase_id or idx, "rule": "sprint_action_ids_list"})
            sprint_action_ids = []
        if not isinstance(blocked_later_action_ids, list):
            findings.append({"phase_id": phase_id or idx, "rule": "blocked_later_action_ids_list"})
            blocked_later_action_ids = []
        covered_sprint_ids.extend(str(action_id) for action_id in sprint_action_ids)
        covered_blocked_ids.extend(str(action_id) for action_id in blocked_later_action_ids)
        if phase.get("backlog_action_count") != len(sprint_action_ids) + len(blocked_later_action_ids):
            findings.append({
                "phase_id": phase_id or idx,
                "rule": "backlog_action_count_matches_ids",
                "expected": len(sprint_action_ids) + len(blocked_later_action_ids),
                "actual": phase.get("backlog_action_count"),
            })
        dependencies = phase.get("depends_on_phase_ids")
        if not isinstance(dependencies, list):
            findings.append({"phase_id": phase_id or idx, "rule": "depends_on_phase_ids_list"})
            dependencies = []
        readiness = phase.get("readiness_after_phase")
        if not isinstance(readiness, dict):
            findings.append({"phase_id": phase_id or idx, "rule": "readiness_after_phase_object"})
        else:
            for key in READY_FLAG_KEYS:
                if readiness.get(key) is not False:
                    findings.append({
                        "phase_id": phase_id or idx,
                        "rule": f"{key}_must_remain_false",
                        "actual": readiness.get(key),
                    })
    expected_orders = list(range(1, len(phases) + 1))
    if orders != expected_orders:
        findings.append({"rule": "phase_orders_contiguous", "expected": expected_orders, "actual": orders})
    duplicate_phase_ids = sorted({phase_id for phase_id in phase_ids if phase_ids.count(phase_id) > 1})
    if duplicate_phase_ids:
        findings.append({"rule": "phase_ids_unique", "actual": duplicate_phase_ids})
    covered_ids = sorted([*covered_sprint_ids, *covered_blocked_ids])
    if covered_ids != expected_ids:
        findings.append({
            "rule": "phase_action_ids_cover_sprint_packet",
            "expected": expected_ids,
            "actual": covered_ids,
        })
    for phase in phases:
        if not isinstance(phase, dict):
            continue
        for dependency in phase.get("depends_on_phase_ids") or []:
            if dependency not in phase_ids:
                findings.append({
                    "phase_id": phase.get("phase_id"),
                    "rule": "dependency_references_known_phase",
                    "actual": dependency,
                })
    return findings


def _sprint_items(doc: dict[str, Any]) -> list[dict[str, Any]]:
    return [
        item
        for section_key in (
            "scope_resolution_items",
            "source_review_items",
            "regulatory_candidate_intake_items",
        )
        for item in (
            doc.get(section_key)
            if isinstance(doc.get(section_key), list)
            else []
        )
        if isinstance(item, dict)
    ]


def _legal_anchor_channel_drift(doc: dict[str, Any]) -> list[dict[str, Any]]:
    summary = doc.get("summary") if isinstance(doc.get("summary"), dict) else {}
    expected_ids = source_matrix_builder.legal_claim_anchor_source_channel_ids()
    sprint_items = _sprint_items(doc)
    blocked_items = [
        item
        for item in (
            doc.get("blocked_later_items")
            if isinstance(doc.get("blocked_later_items"), list)
            else []
        )
        if isinstance(item, dict)
    ]
    phase_rows = [
        phase
        for phase in (
            doc.get("execution_phase_summary")
            if isinstance(doc.get("execution_phase_summary"), list)
            else []
        )
        if isinstance(phase, dict)
    ]

    sprint_items_preserving = sum(
        1
        for item in sprint_items
        if item.get("required_legal_claim_anchor_source_channel_ids") == expected_ids
    )
    blocked_items_preserving = sum(
        1
        for item in blocked_items
        if item.get("required_legal_claim_anchor_source_channel_ids") == expected_ids
    )
    phases_preserving = sum(
        1
        for phase in phase_rows
        if phase.get("required_legal_claim_anchor_source_channel_ids") == expected_ids
    )
    checks = [
        (
            "legal_claim_anchor_source_channel_ids_match_source_matrix",
            expected_ids,
            summary.get("legal_claim_anchor_source_channel_ids"),
        ),
        (
            "legal_claim_anchor_source_channel_count_matches_source_matrix",
            len(expected_ids),
            summary.get("legal_claim_anchor_source_channel_count"),
        ),
        (
            "sprint_items_preserving_legal_anchor_source_channels_match_items",
            len(sprint_items),
            sprint_items_preserving,
        ),
        (
            "blocked_later_items_preserving_legal_anchor_source_channels_match_items",
            len(blocked_items),
            blocked_items_preserving,
        ),
        (
            "execution_phases_preserving_legal_anchor_source_channels_match_phases",
            len(phase_rows),
            phases_preserving,
        ),
        (
            "summary_sprint_items_preserving_legal_anchor_source_channels_matches_items",
            sprint_items_preserving,
            summary.get("sprint_items_preserving_legal_anchor_source_channels"),
        ),
        (
            "summary_blocked_later_items_preserving_legal_anchor_source_channels_matches_items",
            blocked_items_preserving,
            summary.get("blocked_later_items_preserving_legal_anchor_source_channels"),
        ),
        (
            "summary_execution_phases_preserving_legal_anchor_source_channels_matches_phases",
            phases_preserving,
            summary.get("execution_phases_preserving_legal_anchor_source_channels"),
        ),
    ]
    return [
        {"rule": rule, "expected": expected, "actual": actual}
        for rule, expected, actual in checks
        if actual != expected
    ]


def _readiness_drift(doc: dict[str, Any]) -> list[str]:
    summary = doc.get("summary") if isinstance(doc.get("summary"), dict) else {}
    findings: list[str] = [
        f"summary.{key}" for key in READY_FLAG_KEYS if summary.get(key) is not False
    ]
    for idx, item in enumerate(doc.get("regulatory_candidate_intake_items") or []):
        if not isinstance(item, dict):
            findings.append(f"regulatory_candidate_intake_items[{idx}]")
            continue
        readiness = item.get("readiness") if isinstance(item.get("readiness"), dict) else {}
        if readiness.get("ready_for_prompt_generation") is not False:
            findings.append(f"regulatory_candidate_intake_items[{idx}].ready_for_prompt_generation")
        if readiness.get("ready_for_comparable_scoring") is not False:
            findings.append(f"regulatory_candidate_intake_items[{idx}].ready_for_comparable_scoring")
    return findings


def _regulatory_rank_drift(doc: dict[str, Any]) -> list[dict[str, Any]]:
    summary = doc.get("summary") if isinstance(doc.get("summary"), dict) else {}
    items = doc.get("regulatory_candidate_intake_items")
    rows = items if isinstance(items, list) else []
    expected_ranks = list(range(1, len(rows) + 1))
    actual_ranks = [
        row.get("expansion_rank") if isinstance(row, dict) else None
        for row in rows
    ]
    findings: list[dict[str, Any]] = []
    if actual_ranks != expected_ranks:
        findings.append({
            "rule": "regulatory_ranks_are_contiguous",
            "expected": expected_ranks,
            "actual": actual_ranks,
        })
    top_id = summary.get("regulatory_top_candidate_id")
    first = rows[0] if rows and isinstance(rows[0], dict) else {}
    if rows and (first.get("pattern_id") != top_id or first.get("is_top_candidate") is not True):
        findings.append({
            "rule": "top_candidate_first",
            "expected": top_id,
            "actual": first.get("pattern_id"),
        })
    for idx, row in enumerate(rows):
        if not isinstance(row, dict):
            findings.append({"rule": "regulatory_item_object", "expected": "object", "actual": idx})
            continue
        if row.get("priority_signal_count", 0) <= 0:
            findings.append({
                "rule": "priority_signals_present",
                "expected": ">0",
                "actual": row.get("priority_signal_count"),
                "row": row.get("pattern_id"),
            })
        if row.get("readiness", {}).get("ready_for_domain_seed") is not False:
            findings.append({
                "rule": "priority_does_not_approve_domain_seed",
                "expected": False,
                "actual": row.get("readiness", {}).get("ready_for_domain_seed"),
                "row": row.get("pattern_id"),
            })
    return findings


def _source_review_drift(doc: dict[str, Any]) -> list[dict[str, Any]]:
    findings: list[dict[str, Any]] = []
    rows = doc.get("source_review_items") if isinstance(doc.get("source_review_items"), list) else []
    for idx, row in enumerate(rows):
        if not isinstance(row, dict):
            findings.append({"rule": "source_item_object", "expected": "object", "actual": idx})
            continue
        for key, expected in (
            ("privacy_review_required", True),
            ("expert_review_required", True),
            ("ready_for_manifest_promotion", False),
        ):
            if row.get(key) is not expected:
                findings.append({
                    "rule": f"source_review_{key}",
                    "expected": expected,
                    "actual": row.get(key),
                    "row": row.get("source_id"),
                })
    return findings


def _consistency_drift(checks_value: Any) -> dict[str, Any]:
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
    domain_id: str,
    project_config_path: pathlib.Path,
    registry_path: pathlib.Path,
    regulatory_catalog_path: pathlib.Path,
) -> dict[str, Any]:
    return sprint_builder.build_curator_sprint(
        domain_id=domain_id,
        project_config_path=project_config_path,
        registry_path=registry_path,
        regulatory_catalog_path=regulatory_catalog_path,
    )


def validate_curator_sprint(
    doc: Any,
    *,
    sprint_path: pathlib.Path | None = None,
    domain_id: str = DEFAULT_DOMAIN,
    project_config_path: pathlib.Path = project_plan_builder.CONFIG,
    registry_path: pathlib.Path = project_plan_builder.REGISTRY,
    regulatory_catalog_path: pathlib.Path = project_plan_builder.REGULATORY_CATALOG,
    compare_current_chain: bool = True,
) -> dict[str, Any]:
    if not isinstance(doc, dict):
        checks = [_check("sprint_is_object", False, expected="object", actual=type(doc).__name__)]
        failed = _failed_ids(checks)
        return {
            "_meta": {
                "schema_version": "global_protections_curator_sprint_validation.v1",
                "source_sprint_path": _display_path(sprint_path) if sprint_path else "n/a",
                "domain": domain_id,
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
    artifact_paths = doc.get("artifact_paths")
    privacy_scan = project_plan_builder._scan_privacy(_redacted_privacy_view(doc))
    encoded = json.dumps(doc, ensure_ascii=False)
    disallowed = [term for term in DISALLOWED_TERMS if term in encoded]
    consistency = _consistency_drift(doc.get("checks"))
    current = (
        _current_reference(
            domain_id=domain_id,
            project_config_path=project_config_path,
            registry_path=registry_path,
            regulatory_catalog_path=regulatory_catalog_path,
        )
        if compare_current_chain
        else None
    )
    current_summary = current["summary"] if current else None
    current_phase_summary = current.get("execution_phase_summary") if current else None
    phase_drift = _phase_summary_drift(doc)
    checks = [
        _check(
            "top_level_shape",
            REQUIRED_TOP_LEVEL.issubset(doc) and not (set(doc) - ALLOWED_TOP_LEVEL),
            expected=sorted(REQUIRED_TOP_LEVEL),
            actual=sorted(doc),
        ),
        _check(
            "artifact_paths_present",
            isinstance(artifact_paths, dict) and REQUIRED_ARTIFACT_KEYS.issubset(artifact_paths),
            expected=sorted(REQUIRED_ARTIFACT_KEYS),
            actual=sorted(artifact_paths) if isinstance(artifact_paths, dict) else type(artifact_paths).__name__,
        ),
        _check(
            "artifact_paths_safe",
            not _unsafe_artifact_paths(artifact_paths),
            expected=[],
            actual=_unsafe_artifact_paths(artifact_paths),
        ),
        _check(
            "summary_counts_match_sections",
            not _counts_mismatches(doc),
            expected=[],
            actual=_counts_mismatches(doc),
        ),
        _check(
            "execution_phase_summary_valid",
            not phase_drift,
            expected=[],
            actual=phase_drift,
        ),
        _check(
            "legal_claim_anchor_source_channels_preserved",
            not _legal_anchor_channel_drift(doc),
            expected=[],
            actual=_legal_anchor_channel_drift(doc),
        ),
        _check(
            "consistency_checks_all_ok",
            not consistency["failed"] and not consistency["missing_required"],
            expected={"failed": [], "missing_required": []},
            actual=consistency,
        ),
        _check(
            "all_prompt_and_scoring_flags_blocked",
            not _readiness_drift(doc),
            expected=[],
            actual=_readiness_drift(doc),
        ),
        _check(
            "regulatory_priority_queue_valid",
            not _regulatory_rank_drift(doc),
            expected=[],
            actual=_regulatory_rank_drift(doc),
        ),
        _check(
            "source_review_rows_still_unpromoted",
            not _source_review_drift(doc),
            expected=[],
            actual=_source_review_drift(doc),
        ),
        _check(
            "privacy_scan_ok",
            privacy_scan.get("ok") is True,
            expected=True,
            actual=privacy_scan.get("counts"),
        ),
        _check(
            "sprint_contains_no_disallowed_text",
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
        checks.append(
            _check(
                "execution_phase_summary_matches_current_chain",
                doc.get("execution_phase_summary") == current_phase_summary,
                expected=current_phase_summary,
                actual=doc.get("execution_phase_summary"),
            )
        )
    failed = _failed_ids(checks)
    return {
        "_meta": {
            "schema_version": "global_protections_curator_sprint_validation.v1",
            "source_sprint_path": _display_path(sprint_path) if sprint_path else "n/a",
            "domain": domain_id,
            "project_config": _display_path(project_config_path),
            "registry_path": _display_path(registry_path),
            "regulatory_catalog_path": _display_path(regulatory_catalog_path),
            "compare_current_chain": compare_current_chain,
        },
        "summary": {
            "valid": not failed,
            "check_count": len(checks),
            "failed_check_count": len(failed),
            "failed_check_ids": failed,
            "sprint_item_count": summary.get("sprint_item_count"),
            "execution_phase_count": summary.get("execution_phase_count"),
            "execution_phase_covered_action_count": _execution_phase_covered_action_count(doc),
            "legal_claim_anchor_source_channel_count": summary.get(
                "legal_claim_anchor_source_channel_count"
            ),
            "legal_claim_anchor_source_channel_ids": summary.get(
                "legal_claim_anchor_source_channel_ids"
            ),
            "sprint_items_preserving_legal_anchor_source_channels": summary.get(
                "sprint_items_preserving_legal_anchor_source_channels"
            ),
            "blocked_later_items_preserving_legal_anchor_source_channels": summary.get(
                "blocked_later_items_preserving_legal_anchor_source_channels"
            ),
            "execution_phases_preserving_legal_anchor_source_channels": summary.get(
                "execution_phases_preserving_legal_anchor_source_channels"
            ),
            "regulatory_priority_queue_items": summary.get("regulatory_priority_queue_items"),
            "regulatory_top_candidate_id": summary.get("regulatory_top_candidate_id"),
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
        "# Global Protections Curator Sprint Validation",
        "",
        "This read-only report validates the saved curator sprint packet before human review work starts.",
        "",
        "## Summary",
        "",
        "| Metric | Value |",
        "|---|---:|",
        f"| Valid | {str(bool(summary['valid'])).lower()} |",
        f"| Checks | {summary['check_count']} |",
        f"| Failed checks | {summary['failed_check_count']} |",
        f"| Sprint items | {_md_cell(summary.get('sprint_item_count'))} |",
        f"| Execution phases | {_md_cell(summary.get('execution_phase_count'))} |",
        f"| Phase-covered actions | {_md_cell(summary.get('execution_phase_covered_action_count'))} |",
        (
            "| Legal-claim anchor source channels "
            f"| {_md_cell(summary.get('legal_claim_anchor_source_channel_count'))} |"
        ),
        (
            "| Sprint items preserving legal-anchor source channels "
            f"| {_md_cell(summary.get('sprint_items_preserving_legal_anchor_source_channels'))} |"
        ),
        (
            "| Blocked-later items preserving legal-anchor source channels "
            f"| {_md_cell(summary.get('blocked_later_items_preserving_legal_anchor_source_channels'))} |"
        ),
        (
            "| Execution phases preserving legal-anchor source channels "
            f"| {_md_cell(summary.get('execution_phases_preserving_legal_anchor_source_channels'))} |"
        ),
        f"| Regulatory queue | {_md_cell(summary.get('regulatory_priority_queue_items'))} |",
        f"| Regulatory top candidate | {_md_cell(summary.get('regulatory_top_candidate_id'))} |",
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
    ap.add_argument("--sprint", type=pathlib.Path, default=DEFAULT_SPRINT)
    ap.add_argument("--domain", default=DEFAULT_DOMAIN)
    ap.add_argument("--project-config", type=pathlib.Path, default=project_plan_builder.CONFIG)
    ap.add_argument("--registry", type=pathlib.Path, default=project_plan_builder.REGISTRY)
    ap.add_argument("--regulatory-catalog", type=pathlib.Path, default=project_plan_builder.REGULATORY_CATALOG)
    ap.add_argument("--out", type=pathlib.Path, default=OUT)
    ap.add_argument("--markdown-out", type=pathlib.Path, default=MD_OUT)
    ap.add_argument("--no-current-chain", action="store_true", help="skip comparison to the current generated chain")
    ap.add_argument("--validate", action="store_true", help="print the validation summary only; write nothing")
    args = ap.parse_args(argv)

    doc = _load_json(args.sprint)
    if doc is None:
        print(f"[global-protections-curator-sprint-validation] unreadable sprint: {args.sprint}")
        return 1
    report = validate_curator_sprint(
        doc,
        sprint_path=args.sprint,
        domain_id=args.domain,
        project_config_path=args.project_config,
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
        "[global-protections-curator-sprint-validation] "
        f"valid={str(bool(summary['valid'])).lower()}; "
        f"failed={summary['failed_check_count']}/{summary['check_count']}; "
        f"phase_coverage={summary['execution_phase_count']}/"
        f"{summary['execution_phase_covered_action_count']}; "
        f"ready_for_comparable_scoring={str(bool(summary['ready_for_comparable_scoring'])).lower()} -> {args.sprint}"
    )
    return 0 if summary["valid"] else 1


if __name__ == "__main__":
    raise SystemExit(main())
