#!/usr/bin/env python3
"""Validate a saved global-protections next-actions backlog.

The next-actions builder emits the operator backlog for source curation,
regulatory candidate intake, and the later source-verified grounding layer.
This validator checks a saved JSON artifact before it is used as a handoff:
shape, action counts, blocked readiness flags, ranked regulatory queue
ordering, compactness, privacy scan, artifact-path hygiene, and optional drift
against the current deterministic next-actions chain.

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

import build_global_protections_next_actions as next_actions_builder  # noqa: E402
import build_global_protections_project_plan as project_plan_builder  # noqa: E402
import build_global_protections_source_channel_matrix as source_matrix_builder  # noqa: E402

DEFAULT_DOMAIN = next_actions_builder.DEFAULT_DOMAIN
DEFAULT_BACKLOG = next_actions_builder.OUT
OUT = next_actions_builder.OUT_DIR / "global_protections_next_actions_validation.json"
MD_OUT = next_actions_builder.OUT_DIR / "global_protections_next_actions_validation.md"

REQUIRED_TOP_LEVEL = frozenset({
    "_meta",
    "summary",
    "counts_by_lane",
    "counts_by_status",
    "execution_phases",
    "actions",
    "checks",
    "artifact_paths",
})
ALLOWED_TOP_LEVEL = REQUIRED_TOP_LEVEL
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
})
REQUIRED_CHECK_IDS = frozenset({
    "readiness_bundle_consistency_ok",
    "scope_resolution_count_matches_sprint",
    "source_review_count_matches_sprint",
    "deferred_source_count_matches_sprint",
    "regulatory_candidate_count_matches_intake",
    "regulatory_priority_queue_matches_intake",
    "regulatory_top_candidate_first",
    "all_public_and_scoring_flags_blocked",
    "execution_phases_cover_actions",
    "execution_phase_readiness_stays_blocked",
    "legal_claim_anchor_source_channels_preserved",
    "backlog_contains_no_disallowed_text",
    "privacy_scan_ok",
})
READY_FLAG_KEYS = (
    "ready_for_prompt_generation",
    "ready_for_training_use",
    "ready_for_public_claims",
    "ready_for_worker_facing_use",
    "ready_for_comparable_scoring",
)
ACTION_TYPES = frozenset({
    "scope_resolution",
    "source_review",
    "deferred_source_review",
    "candidate_domain_intake",
    "source_verified_grounding_layer",
})
RAW_PAYLOAD_KEYS = frozenset({
    "_domain_chain",
    "_regulatory_chain",
    "source_object_queue",
    "source_candidate_intake_rows",
    "scope_resolution_intake_rows",
    "candidate_domain_intake",
    "prompt_family_sketches",
    "candidate_manifest_rows",
    "source_url",
})
DISALLOWED_TERMS = [
    "Synthetic composite:",
    "prompt_family_sketches",
    "candidate_url",
    "source_url",
    "raw_text",
    "case_text",
    "prompt_text",
    "model_response_text",
    "response_text",
    "https://",
    "www.",
]
_URL = re.compile(r"\b(?:https?://|www\.)", re.I)
_WINDOWS_ABSOLUTE_PATH = re.compile(r"^[A-Za-z]:/")


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


def _redacted_privacy_view(doc: dict[str, Any]) -> dict[str, Any]:
    view = json.loads(json.dumps(doc))
    if isinstance(view.get("artifact_paths"), dict):
        view["artifact_paths"] = {
            str(key): "artifact-path-redacted"
            for key in view["artifact_paths"]
        }
    return view


def _unsafe_artifact_paths(paths: Any) -> list[dict[str, str]]:
    if not isinstance(paths, dict):
        return [{"key": "$", "value": "artifact_paths_not_object"}]
    findings: list[dict[str, str]] = []
    missing = sorted(REQUIRED_ARTIFACT_KEYS - set(paths))
    for key in missing:
        findings.append({"key": key, "value": "missing"})
    for key, value in paths.items():
        if not isinstance(value, str) or not value.strip():
            findings.append({"key": str(key), "value": "missing_or_not_string"})
            continue
        parts = pathlib.PurePosixPath(value).parts
        if (
            _URL.search(value)
            or "\\" in value
            or value.startswith("/")
            or value.startswith("~/")
            or _WINDOWS_ABSOLUTE_PATH.search(value)
            or ".." in parts
        ):
            findings.append({"key": str(key), "value": value})
    return findings


def _raw_payload_keys(doc: dict[str, Any]) -> list[str]:
    return sorted(key for key in doc if key in RAW_PAYLOAD_KEYS)


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


def _counts_by(actions: list[dict[str, Any]], key: str) -> dict[str, int]:
    counts: dict[str, int] = {}
    for action in actions:
        value = str(action.get(key) or "unknown")
        counts[value] = counts.get(value, 0) + 1
    return {value: counts[value] for value in sorted(counts)}


def _action_shape_drift(actions_value: Any) -> list[dict[str, Any]]:
    if not isinstance(actions_value, list):
        return [{"rule": "actions_list", "actual": type(actions_value).__name__}]
    findings: list[dict[str, Any]] = []
    seen_ids: set[str] = set()
    expected_legal_anchor_source_channels = (
        source_matrix_builder.legal_claim_anchor_source_channel_ids()
    )
    required = {
        "id",
        "priority",
        "lane",
        "item_type",
        "status",
        "required_output",
        "next_step",
        "blocks",
        "required_legal_claim_anchor_source_channel_ids",
    }
    for idx, action in enumerate(actions_value):
        if not isinstance(action, dict):
            findings.append({"index": idx, "rule": "action_object", "actual": type(action).__name__})
            continue
        missing = sorted(required - set(action))
        action_id = str(action.get("id") or "")
        if missing:
            findings.append({"id": action_id or idx, "rule": "required_keys", "missing": missing})
        if not action_id or action_id in seen_ids:
            findings.append({"id": action_id or idx, "rule": "unique_nonempty_id"})
        seen_ids.add(action_id)
        if not isinstance(action.get("priority"), int):
            findings.append({"id": action_id or idx, "rule": "priority_int"})
        if action.get("item_type") not in ACTION_TYPES:
            findings.append({"id": action_id or idx, "rule": "known_item_type", "actual": action.get("item_type")})
        if not isinstance(action.get("blocks"), list) or not action.get("blocks"):
            findings.append({"id": action_id or idx, "rule": "blocks_nonempty_list"})
        if (
            action.get("required_legal_claim_anchor_source_channel_ids")
            != expected_legal_anchor_source_channels
        ):
            findings.append({
                "id": action_id or idx,
                "rule": "required_legal_claim_anchor_source_channel_ids_exact",
                "expected": expected_legal_anchor_source_channels,
                "actual": action.get("required_legal_claim_anchor_source_channel_ids"),
            })
        for key in READY_FLAG_KEYS:
            if action.get(key) is True:
                findings.append({"id": action_id or idx, "rule": f"{key}_must_not_be_true"})
    return findings


def _execution_phase_drift(doc: dict[str, Any]) -> list[dict[str, Any]]:
    phases_value = doc.get("execution_phases")
    actions_value = doc.get("actions")
    if not isinstance(phases_value, list):
        return [{"rule": "execution_phases_list", "actual": type(phases_value).__name__}]
    actions = actions_value if isinstance(actions_value, list) else []
    action_ids = [
        str(action.get("id"))
        for action in actions
        if isinstance(action, dict) and action.get("id")
    ]
    findings: list[dict[str, Any]] = []
    required = {
        "id",
        "order",
        "label",
        "action_types",
        "action_count",
        "action_ids",
        "depends_on_phase_ids",
        "completion_gate",
        "readiness_after_phase",
        "required_legal_claim_anchor_source_channel_ids",
    }
    seen_phase_ids: set[str] = set()
    seen_action_ids: list[str] = []
    phase_orders: list[Any] = []
    phase_ids: list[str] = []
    expected_legal_anchor_source_channels = (
        source_matrix_builder.legal_claim_anchor_source_channel_ids()
    )
    for idx, phase in enumerate(phases_value):
        if not isinstance(phase, dict):
            findings.append({"index": idx, "rule": "phase_object", "actual": type(phase).__name__})
            continue
        phase_id = str(phase.get("id") or "")
        phase_ids.append(phase_id)
        missing = sorted(required - set(phase))
        if missing:
            findings.append({"id": phase_id or idx, "rule": "required_keys", "missing": missing})
        if not phase_id or phase_id in seen_phase_ids:
            findings.append({"id": phase_id or idx, "rule": "unique_nonempty_phase_id"})
        seen_phase_ids.add(phase_id)
        phase_orders.append(phase.get("order"))
        action_types = phase.get("action_types")
        if not isinstance(action_types, list) or not action_types:
            findings.append({"id": phase_id or idx, "rule": "action_types_nonempty_list"})
        elif any(action_type not in ACTION_TYPES for action_type in action_types):
            findings.append({
                "id": phase_id or idx,
                "rule": "known_action_types",
                "actual": action_types,
            })
        phase_action_ids = phase.get("action_ids")
        if not isinstance(phase_action_ids, list):
            findings.append({"id": phase_id or idx, "rule": "action_ids_list"})
            phase_action_ids = []
        if phase.get("action_count") != len(phase_action_ids):
            findings.append({
                "id": phase_id or idx,
                "rule": "action_count_matches_ids",
                "expected": len(phase_action_ids),
                "actual": phase.get("action_count"),
            })
        seen_action_ids.extend(str(action_id) for action_id in phase_action_ids)
        dependencies = phase.get("depends_on_phase_ids")
        if not isinstance(dependencies, list):
            findings.append({"id": phase_id or idx, "rule": "depends_on_phase_ids_list"})
            dependencies = []
        readiness = phase.get("readiness_after_phase")
        if not isinstance(readiness, dict):
            findings.append({"id": phase_id or idx, "rule": "readiness_after_phase_object"})
        else:
            for key in READY_FLAG_KEYS:
                if readiness.get(key) is not False:
                    findings.append({
                        "id": phase_id or idx,
                        "rule": f"{key}_must_remain_false",
                        "actual": readiness.get(key),
                    })
        if (
            phase.get("required_legal_claim_anchor_source_channel_ids")
            != expected_legal_anchor_source_channels
        ):
            findings.append({
                "id": phase_id or idx,
                "rule": "required_legal_claim_anchor_source_channel_ids_exact",
                "expected": expected_legal_anchor_source_channels,
                "actual": phase.get("required_legal_claim_anchor_source_channel_ids"),
            })
    expected_orders = list(range(1, len(phases_value) + 1))
    if phase_orders != expected_orders:
        findings.append({"rule": "phase_orders_contiguous", "expected": expected_orders, "actual": phase_orders})
    duplicate_action_ids = sorted({
        action_id for action_id in seen_action_ids if seen_action_ids.count(action_id) > 1
    })
    if duplicate_action_ids:
        findings.append({"rule": "action_ids_unique_across_phases", "actual": duplicate_action_ids})
    if sorted(seen_action_ids) != sorted(action_ids):
        findings.append({
            "rule": "phase_action_ids_cover_actions",
            "expected": sorted(action_ids),
            "actual": sorted(seen_action_ids),
        })
    for phase in phases_value:
        if not isinstance(phase, dict):
            continue
        for dependency in phase.get("depends_on_phase_ids") or []:
            if dependency not in phase_ids:
                findings.append({
                    "id": phase.get("id"),
                    "rule": "dependency_references_known_phase",
                    "actual": dependency,
                })
    return findings


def _summary_count_mismatches(doc: dict[str, Any]) -> list[dict[str, Any]]:
    summary = doc.get("summary") if isinstance(doc.get("summary"), dict) else {}
    actions = doc.get("actions") if isinstance(doc.get("actions"), list) else []
    phases = doc.get("execution_phases") if isinstance(doc.get("execution_phases"), list) else []
    if not all(isinstance(action, dict) for action in actions):
        return [{"summary_key": "actions", "expected": "list of objects", "actual": type(actions).__name__}]
    computed = {
        "action_count": len(actions),
        "execution_phase_count": len(phases),
        "immediate_action_count": sum(1 for item in actions if item.get("status") in {"not_started", "needs_review"}),
        "blocked_action_count": sum(1 for item in actions if str(item.get("status")).startswith("blocked")),
        "scope_resolution_items": sum(1 for item in actions if item.get("item_type") == "scope_resolution"),
        "source_review_items": sum(1 for item in actions if item.get("item_type") == "source_review"),
        "deferred_source_review_items": sum(
            1 for item in actions if item.get("item_type") == "deferred_source_review"
        ),
        "regulatory_candidate_intake_items": sum(
            1 for item in actions if item.get("item_type") == "candidate_domain_intake"
        ),
        "grounding_layer_items": sum(
            1 for item in actions if item.get("item_type") == "source_verified_grounding_layer"
        ),
        "legal_claim_anchor_source_channel_count": len(
            source_matrix_builder.legal_claim_anchor_source_channel_ids()
        ),
        "legal_claim_anchor_source_channel_ids": (
            source_matrix_builder.legal_claim_anchor_source_channel_ids()
        ),
        "actions_preserving_legal_anchor_source_channels": sum(
            1
            for item in actions
            if item.get("required_legal_claim_anchor_source_channel_ids")
            == source_matrix_builder.legal_claim_anchor_source_channel_ids()
        ),
        "execution_phases_preserving_legal_anchor_source_channels": sum(
            1
            for phase in phases
            if isinstance(phase, dict)
            and phase.get("required_legal_claim_anchor_source_channel_ids")
            == source_matrix_builder.legal_claim_anchor_source_channel_ids()
        ),
    }
    mismatches = [
        {"summary_key": key, "expected": expected, "actual": summary.get(key)}
        for key, expected in computed.items()
        if summary.get(key) != expected
    ]
    if doc.get("counts_by_lane") != _counts_by(actions, "lane"):
        mismatches.append({
            "summary_key": "counts_by_lane",
            "expected": _counts_by(actions, "lane"),
            "actual": doc.get("counts_by_lane"),
        })
    if doc.get("counts_by_status") != _counts_by(actions, "status"):
        mismatches.append({
            "summary_key": "counts_by_status",
            "expected": _counts_by(actions, "status"),
            "actual": doc.get("counts_by_status"),
        })
    return mismatches


def _execution_phase_covered_action_count(doc: dict[str, Any]) -> int:
    phases = doc.get("execution_phases") if isinstance(doc.get("execution_phases"), list) else []
    covered_ids = {
        str(action_id)
        for phase in phases
        if isinstance(phase, dict)
        for action_id in (phase.get("action_ids") if isinstance(phase.get("action_ids"), list) else [])
    }
    return len(covered_ids)


def _readiness_drift(doc: dict[str, Any]) -> list[str]:
    summary = doc.get("summary") if isinstance(doc.get("summary"), dict) else {}
    findings = [f"summary.{key}" for key in READY_FLAG_KEYS if summary.get(key) is not False]
    for idx, action in enumerate(doc.get("actions") if isinstance(doc.get("actions"), list) else []):
        if not isinstance(action, dict):
            continue
        for key in ("ready_for_domain_seed", "ready_for_prompt_generation", "ready_for_comparable_scoring"):
            if action.get(key) is True:
                findings.append(f"actions[{idx}].{key}")
    return findings


def _rank_drift(actions_value: Any, summary: dict[str, Any]) -> list[dict[str, Any]]:
    actions = actions_value if isinstance(actions_value, list) else []
    regulatory_actions = [
        action for action in actions
        if isinstance(action, dict) and action.get("item_type") == "candidate_domain_intake"
    ]
    ranks = [action.get("expansion_rank") for action in regulatory_actions]
    expected = list(range(1, len(regulatory_actions) + 1))
    findings: list[dict[str, Any]] = []
    if ranks != expected:
        findings.append({"rule": "regulatory_ranks_contiguous", "expected": expected, "actual": ranks})
    top = regulatory_actions[0] if regulatory_actions else {}
    if top.get("pattern_id") != summary.get("regulatory_top_candidate_id"):
        findings.append({
            "rule": "top_candidate_first",
            "expected": summary.get("regulatory_top_candidate_id"),
            "actual": top.get("pattern_id"),
        })
    if regulatory_actions and top.get("is_top_candidate") is not True:
        findings.append({"rule": "top_candidate_marker", "expected": True, "actual": top.get("is_top_candidate")})
    return findings


def _current_reference(
    *,
    domain_id: str,
    project_config_path: pathlib.Path,
    registry_path: pathlib.Path,
    regulatory_catalog_path: pathlib.Path,
    component_dir: pathlib.Path,
) -> dict[str, Any]:
    return next_actions_builder.build_next_actions(
        domain_id=domain_id,
        project_config_path=project_config_path,
        registry_path=registry_path,
        regulatory_catalog_path=regulatory_catalog_path,
        component_dir=component_dir,
    )


def _comparable_sections(doc: dict[str, Any]) -> dict[str, Any]:
    return {
        "summary": doc.get("summary"),
        "counts_by_lane": doc.get("counts_by_lane"),
        "counts_by_status": doc.get("counts_by_status"),
        "execution_phases": doc.get("execution_phases"),
        "actions": doc.get("actions"),
        "checks": doc.get("checks"),
    }


def validate_next_actions(
    doc: Any,
    *,
    backlog_path: pathlib.Path | None = None,
    domain_id: str = DEFAULT_DOMAIN,
    project_config_path: pathlib.Path = project_plan_builder.CONFIG,
    registry_path: pathlib.Path = project_plan_builder.REGISTRY,
    regulatory_catalog_path: pathlib.Path = project_plan_builder.REGULATORY_CATALOG,
    component_dir: pathlib.Path = next_actions_builder.OUT_DIR,
    compare_current_chain: bool = True,
) -> dict[str, Any]:
    if not isinstance(doc, dict):
        checks = [_check("next_actions_is_object", False, expected="object", actual=type(doc).__name__)]
        failed = _failed_ids(checks)
        return {
            "_meta": {
                "schema_version": "global_protections_next_actions_validation.v1",
                "source_backlog_path": _display_path(backlog_path) if backlog_path else "n/a",
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
    embedded = _embedded_check_drift(doc.get("checks"))
    action_shape = _action_shape_drift(doc.get("actions"))
    phase_drift = _execution_phase_drift(doc)
    count_mismatches = _summary_count_mismatches(doc)
    readiness_drift = _readiness_drift(doc)
    rank_drift = _rank_drift(doc.get("actions"), summary)
    unsafe_paths = _unsafe_artifact_paths(doc.get("artifact_paths"))
    raw_keys = _raw_payload_keys(doc)
    privacy_scan = project_plan_builder._scan_privacy(_redacted_privacy_view(doc))
    encoded = json.dumps(doc, ensure_ascii=False)
    disallowed = [term for term in DISALLOWED_TERMS if term in encoded]
    current = (
        _current_reference(
            domain_id=domain_id,
            project_config_path=project_config_path,
            registry_path=registry_path,
            regulatory_catalog_path=regulatory_catalog_path,
            component_dir=component_dir,
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
        _check("action_shape", not action_shape, expected=[], actual=action_shape),
        _check("execution_phases_shape", not phase_drift, expected=[], actual=phase_drift),
        _check("summary_counts_match_actions", not count_mismatches, expected=[], actual=count_mismatches),
        _check(
            "embedded_checks_all_ok",
            not embedded["failed"] and not embedded["missing_required"],
            expected={"failed": [], "missing_required": []},
            actual=embedded,
        ),
        _check("all_readiness_flags_blocked", not readiness_drift, expected=[], actual=readiness_drift),
        _check("regulatory_rank_order_intact", not rank_drift, expected=[], actual=rank_drift),
        _check("artifact_paths_are_handoff_safe", not unsafe_paths, expected=[], actual=unsafe_paths),
        _check("raw_payload_sections_absent", not raw_keys, expected=[], actual=raw_keys),
        _check("privacy_scan_ok", privacy_scan.get("ok") is True, expected=True, actual=privacy_scan.get("counts")),
        _check("next_actions_contains_no_disallowed_text", not disallowed, expected=[], actual=disallowed),
    ]
    if compare_current_chain:
        checks.append(
            _check(
                "next_actions_matches_current_chain",
                _comparable_sections(doc) == current_sections,
                expected=current_sections,
                actual=_comparable_sections(doc),
            )
        )
    failed = _failed_ids(checks)
    return {
        "_meta": {
            "schema_version": "global_protections_next_actions_validation.v1",
            "source_backlog_path": _display_path(backlog_path) if backlog_path else "n/a",
            "domain": domain_id,
            "project_config": _display_path(project_config_path),
            "registry_path": _display_path(registry_path),
            "regulatory_catalog_path": _display_path(regulatory_catalog_path),
            "component_dir": _display_path(component_dir),
            "compare_current_chain": compare_current_chain,
        },
        "summary": {
            "valid": not failed,
            "check_count": len(checks),
            "failed_check_count": len(failed),
            "failed_check_ids": failed,
            "action_count": summary.get("action_count"),
            "execution_phase_count": summary.get("execution_phase_count"),
            "execution_phase_covered_action_count": _execution_phase_covered_action_count(doc),
            "immediate_action_count": summary.get("immediate_action_count"),
            "blocked_action_count": summary.get("blocked_action_count"),
            "legal_claim_anchor_source_channel_count": summary.get(
                "legal_claim_anchor_source_channel_count"
            ),
            "legal_claim_anchor_source_channel_ids": summary.get(
                "legal_claim_anchor_source_channel_ids"
            ),
            "actions_preserving_legal_anchor_source_channels": summary.get(
                "actions_preserving_legal_anchor_source_channels"
            ),
            "execution_phases_preserving_legal_anchor_source_channels": summary.get(
                "execution_phases_preserving_legal_anchor_source_channels"
            ),
            "regulatory_top_candidate_id": summary.get("regulatory_top_candidate_id"),
            "ready_for_prompt_generation": summary.get("ready_for_prompt_generation"),
            "ready_for_worker_facing_use": summary.get("ready_for_worker_facing_use"),
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
        "# Global Protections Next Actions Validation",
        "",
        "This read-only report validates the saved next-actions backlog before it is used as a handoff.",
        "",
        "## Summary",
        "",
        "| Metric | Value |",
        "|---|---:|",
        f"| Valid | {str(bool(summary['valid'])).lower()} |",
        f"| Checks | {summary['check_count']} |",
        f"| Failed checks | {summary['failed_check_count']} |",
        f"| Actions | {_md_cell(summary.get('action_count'))} |",
        f"| Execution phases | {_md_cell(summary.get('execution_phase_count'))} |",
        f"| Phase-covered actions | {_md_cell(summary.get('execution_phase_covered_action_count'))} |",
        f"| Immediate actions | {_md_cell(summary.get('immediate_action_count'))} |",
        f"| Blocked actions | {_md_cell(summary.get('blocked_action_count'))} |",
        f"| Legal-claim anchor source channels | {_md_cell(summary.get('legal_claim_anchor_source_channel_count'))} |",
        (
            "| Actions preserving legal-anchor source channels "
            f"| {_md_cell(summary.get('actions_preserving_legal_anchor_source_channels'))} |"
        ),
        (
            "| Execution phases preserving legal-anchor source channels "
            f"| {_md_cell(summary.get('execution_phases_preserving_legal_anchor_source_channels'))} |"
        ),
        f"| Regulatory top candidate | {_md_cell(summary.get('regulatory_top_candidate_id'))} |",
        f"| Ready for prompt generation | {str(bool(summary.get('ready_for_prompt_generation'))).lower()} |",
        f"| Ready for worker-facing use | {str(bool(summary.get('ready_for_worker_facing_use'))).lower()} |",
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
    ap.add_argument("--backlog", type=pathlib.Path, default=DEFAULT_BACKLOG)
    ap.add_argument("--domain", default=DEFAULT_DOMAIN)
    ap.add_argument("--project-config", type=pathlib.Path, default=project_plan_builder.CONFIG)
    ap.add_argument("--registry", type=pathlib.Path, default=project_plan_builder.REGISTRY)
    ap.add_argument("--regulatory-catalog", type=pathlib.Path, default=project_plan_builder.REGULATORY_CATALOG)
    ap.add_argument("--component-dir", type=pathlib.Path, default=next_actions_builder.OUT_DIR)
    ap.add_argument("--out", type=pathlib.Path, default=OUT)
    ap.add_argument("--markdown-out", type=pathlib.Path, default=MD_OUT)
    ap.add_argument("--no-current-chain", action="store_true", help="skip comparison to the current generated chain")
    ap.add_argument("--validate", action="store_true", help="print the validation summary only; write nothing")
    args = ap.parse_args(argv)

    doc = _load_json(args.backlog)
    if doc is None:
        print(f"[global-protections-next-actions-validation] unreadable backlog: {args.backlog}")
        return 1
    report = validate_next_actions(
        doc,
        backlog_path=args.backlog,
        domain_id=args.domain,
        project_config_path=args.project_config,
        registry_path=args.registry,
        regulatory_catalog_path=args.regulatory_catalog,
        component_dir=args.component_dir,
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
        "[global-protections-next-actions-validation] "
        f"valid={str(bool(summary['valid'])).lower()}; "
        f"failed={summary['failed_check_count']}/{summary['check_count']}; "
        f"phase_coverage={summary['execution_phase_count']}/"
        f"{summary['execution_phase_covered_action_count']}; "
        f"ready_for_comparable_scoring={str(bool(summary['ready_for_comparable_scoring'])).lower()} -> {args.backlog}"
    )
    return 0 if summary["valid"] else 1


if __name__ == "__main__":
    raise SystemExit(main())
