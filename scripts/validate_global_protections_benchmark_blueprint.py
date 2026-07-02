#!/usr/bin/env python3
"""Validate a saved global-protections benchmark blueprint.

The benchmark blueprint is only a future task-shape artifact. This validator
keeps a saved blueprint source-gated and non-executable: task blueprints must
remain blocked, source-grounding contracts must stay complete, source-gap
abstention must remain explicit, scoring dimensions must not be promoted, and
the saved artifact can be compared to the current deterministic chain.

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

import build_global_protections_benchmark_blueprint as blueprint_builder  # noqa: E402
import build_global_protections_project_plan as project_plan_builder  # noqa: E402
import build_global_protections_source_channel_matrix as source_matrix_builder  # noqa: E402

DEFAULT_BLUEPRINT = blueprint_builder.OUT
DEFAULT_DOMAIN = blueprint_builder.DEFAULT_DOMAIN
OUT = blueprint_builder.OUT_DIR / "global_protections_benchmark_blueprint_validation.json"
MD_OUT = blueprint_builder.OUT_DIR / "global_protections_benchmark_blueprint_validation.md"

REQUIRED_TOP_LEVEL = frozenset({
    "_meta",
    "summary",
    "task_blueprints",
    "scoring_dimension_blueprints",
    "abstention_rules",
    "checks",
})
ALLOWED_TOP_LEVEL = REQUIRED_TOP_LEVEL
REQUIRED_CHECK_IDS = frozenset({
    "project_plan_safe",
    "source_review_packet_consistency_ok",
    "readiness_bundle_consistency_ok",
    "task_blueprints_cover_benchmark_axes",
    "scoring_dimensions_cover_capabilities",
    "source_review_rows_not_started",
    "source_review_has_legal_claim_anchor_rows",
    "all_task_blueprints_blocked",
    "all_task_blueprints_have_source_grounding_contracts",
    "all_tasks_require_legal_claim_anchor_or_gap_marker",
    "legal_claim_anchor_channels_match_source_matrix",
    "all_tasks_bar_informal_standalone_legal_claims",
    "all_tasks_require_jurisdiction_chain_contract",
    "all_tasks_require_temporal_validity_contract",
    "all_tasks_require_language_access_contract",
    "all_tasks_require_entity_resolution_contract",
    "all_tasks_require_remedy_forum_contract",
    "all_tasks_require_authority_hierarchy_contract",
    "all_tasks_require_coverage_scope_contract",
    "all_tasks_require_implementation_status_contract",
    "all_tasks_require_procedural_burden_contract",
    "all_public_and_scoring_flags_blocked",
    "blueprint_contains_no_disallowed_text",
    "privacy_scan_ok",
})
READY_FLAG_KEYS = (
    "ready_for_prompt_generation",
    "ready_for_training_use",
    "ready_for_public_claims",
    "ready_for_worker_facing_use",
    "ready_for_comparable_scoring",
)
REQUIRED_TASK_KEYS = frozenset({
    "blueprint_id",
    "axis_id",
    "benchmark_axis",
    "instantiation_status",
    "requires_reviewed_source_objects",
    "source_grounding_requirements",
    "required_source_evidence",
    "required_review_gates",
    "allowed_inputs_after_review",
    "forbidden_inputs",
    "expected_good_behavior",
    "severe_failure_modes",
    *READY_FLAG_KEYS,
})
REQUIRED_DIMENSION_KEYS = frozenset({
    "dimension_id",
    "capability",
    "score_levels",
    "required_reference_basis",
    "ready_for_comparable_scoring",
})
REQUIRED_ABSTENTION_KEYS = frozenset({"id", "when", "expected_model_behavior"})
DISALLOWED_TERMS = blueprint_builder.DISALLOWED_TERMS
_TASK_ID = re.compile(r"^GPBB-TASK-\d{3}$")
_DIMENSION_ID = re.compile(r"^gpsd_[a-z0-9_]{3,100}$")


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


def _task_shape_drift(doc: dict[str, Any]) -> list[dict[str, Any]]:
    findings: list[dict[str, Any]] = []
    rows = doc.get("task_blueprints") if isinstance(doc.get("task_blueprints"), list) else []
    expected_ids = [f"GPBB-TASK-{idx:03d}" for idx in range(1, len(rows) + 1)]
    actual_ids: list[Any] = []
    for idx, row in enumerate(rows):
        if not isinstance(row, dict):
            findings.append({"row": idx, "rule": "task_blueprint_object", "actual": type(row).__name__})
            actual_ids.append(None)
            continue
        actual_ids.append(row.get("blueprint_id"))
        missing = sorted(REQUIRED_TASK_KEYS - set(row))
        extra = sorted(set(row) - REQUIRED_TASK_KEYS)
        if missing or extra:
            findings.append({
                "row": row.get("blueprint_id", idx),
                "missing": missing,
                "extra": extra,
            })
        if not isinstance(row.get("blueprint_id"), str) or not _TASK_ID.fullmatch(row["blueprint_id"]):
            findings.append({
                "row": row.get("blueprint_id", idx),
                "rule": "blueprint_id_format",
                "expected": "GPBB-TASK-000",
                "actual": row.get("blueprint_id"),
            })
        if row.get("instantiation_status") != "blocked_pending_source_review":
            findings.append({
                "row": row.get("blueprint_id", idx),
                "rule": "instantiation_status_blocked",
                "expected": "blocked_pending_source_review",
                "actual": row.get("instantiation_status"),
            })
        if row.get("requires_reviewed_source_objects") is not True:
            findings.append({
                "row": row.get("blueprint_id", idx),
                "rule": "requires_reviewed_source_objects",
                "expected": True,
                "actual": row.get("requires_reviewed_source_objects"),
            })
        for key in READY_FLAG_KEYS:
            if row.get(key) is not False:
                findings.append({
                    "row": row.get("blueprint_id", idx),
                    "rule": key,
                    "expected": False,
                    "actual": row.get(key),
                })
        for key in (
            "required_source_evidence",
            "required_review_gates",
            "allowed_inputs_after_review",
            "forbidden_inputs",
            "expected_good_behavior",
            "severe_failure_modes",
        ):
            if not isinstance(row.get(key), list) or not row.get(key):
                findings.append({
                    "row": row.get("blueprint_id", idx),
                    "rule": f"{key}_non_empty",
                    "actual": row.get(key),
                })
    if actual_ids != expected_ids:
        findings.append({
            "rule": "task_blueprint_ids_contiguous",
            "expected": expected_ids,
            "actual": actual_ids,
        })
    return findings


def _grounding_contract_drift(doc: dict[str, Any]) -> list[dict[str, Any]]:
    findings: list[dict[str, Any]] = []
    expected = blueprint_builder._SOURCE_GROUNDING_REQUIREMENTS
    rows = doc.get("task_blueprints") if isinstance(doc.get("task_blueprints"), list) else []
    for idx, row in enumerate(rows):
        if not isinstance(row, dict):
            continue
        grounding = row.get("source_grounding_requirements")
        if grounding != expected:
            findings.append({
                "row": row.get("blueprint_id", idx),
                "rule": "source_grounding_requirements_exact_contract",
                "expected": expected,
                "actual": grounding,
            })
        evidence = row.get("required_source_evidence") if isinstance(row.get("required_source_evidence"), list) else []
        for required in (
            "effective date, version range, or current-as-of note",
            "supersession check status",
            "source-language or script note",
            "translation, OCR, or transliteration review status",
            "entity, alias, or registry/license status review when an entity claim is scored",
            "remedy forum competence and routing basis when a remedy path is scored",
            "authority tier and controlling-source basis when sources conflict",
            "worker category, sector, migration/status, and coverage eligibility basis when a protection is scored",
            "origin, destination, transit, forum, flag, port, regulator, contractor, buyer, or consular responsibility basis when cross-border responsibility is scored",
            "implementation status, operational availability, access conditions, and enforcement-path basis when practical access is scored",
            "deadlines, required documents, identity/access prerequisites, evidentiary burden, fees, translation/notarization, and filing-channel basis when a procedure is scored",
            "privacy review passed",
            "source-path review passed",
            "expert review passed",
        ):
            if required not in evidence:
                findings.append({
                    "row": row.get("blueprint_id", idx),
                    "rule": "required_source_evidence_present",
                    "missing": required,
                })
    return findings


def _legal_anchor_channel_drift(doc: dict[str, Any]) -> list[dict[str, Any]]:
    expected = source_matrix_builder.legal_claim_anchor_source_channel_ids()
    findings: list[dict[str, Any]] = []
    rows = doc.get("task_blueprints") if isinstance(doc.get("task_blueprints"), list) else []
    for idx, row in enumerate(rows):
        if not isinstance(row, dict):
            continue
        grounding = row.get("source_grounding_requirements")
        if not isinstance(grounding, dict):
            continue
        actual = grounding.get("legal_claim_anchor_source_channel_ids")
        if actual != expected:
            findings.append({
                "row": row.get("blueprint_id", idx),
                "expected": expected,
                "actual": actual,
            })
    return findings


def _dimension_shape_drift(doc: dict[str, Any]) -> list[dict[str, Any]]:
    findings: list[dict[str, Any]] = []
    rows = doc.get("scoring_dimension_blueprints")
    dimensions = rows if isinstance(rows, list) else []
    for idx, row in enumerate(dimensions):
        if not isinstance(row, dict):
            findings.append({"row": idx, "rule": "dimension_object", "actual": type(row).__name__})
            continue
        missing = sorted(REQUIRED_DIMENSION_KEYS - set(row))
        extra = sorted(set(row) - REQUIRED_DIMENSION_KEYS)
        if missing or extra:
            findings.append({
                "row": row.get("dimension_id", idx),
                "missing": missing,
                "extra": extra,
            })
        if not isinstance(row.get("dimension_id"), str) or not _DIMENSION_ID.fullmatch(row["dimension_id"]):
            findings.append({
                "row": row.get("dimension_id", idx),
                "rule": "dimension_id_format",
                "actual": row.get("dimension_id"),
            })
        if row.get("ready_for_comparable_scoring") is not False:
            findings.append({
                "row": row.get("dimension_id", idx),
                "rule": "dimension_comparable_scoring_blocked",
                "expected": False,
                "actual": row.get("ready_for_comparable_scoring"),
            })
        if not isinstance(row.get("score_levels"), list) or len(row.get("score_levels", [])) != 3:
            findings.append({
                "row": row.get("dimension_id", idx),
                "rule": "score_levels_three",
                "actual": row.get("score_levels"),
            })
    return findings


def _abstention_rule_drift(doc: dict[str, Any]) -> dict[str, Any]:
    rows = doc.get("abstention_rules") if isinstance(doc.get("abstention_rules"), list) else []
    actual_ids = [
        row.get("id")
        for row in rows
        if isinstance(row, dict)
    ]
    expected_ids = [row["id"] for row in blueprint_builder._ABSTENTION_RULES]
    shape_findings: list[dict[str, Any]] = []
    for idx, row in enumerate(rows):
        if not isinstance(row, dict):
            shape_findings.append({"row": idx, "rule": "abstention_rule_object", "actual": type(row).__name__})
            continue
        missing = sorted(REQUIRED_ABSTENTION_KEYS - set(row))
        extra = sorted(set(row) - REQUIRED_ABSTENTION_KEYS)
        if missing or extra:
            shape_findings.append({"row": row.get("id", idx), "missing": missing, "extra": extra})
    return {
        "expected_ids": expected_ids,
        "actual_ids": actual_ids,
        "missing_ids": sorted(set(expected_ids) - set(actual_ids)),
        "extra_ids": sorted(set(actual_ids) - set(expected_ids)),
        "shape_findings": shape_findings,
    }


def _summary_count_mismatches(doc: dict[str, Any]) -> list[dict[str, Any]]:
    summary = doc.get("summary") if isinstance(doc.get("summary"), dict) else {}
    tasks = doc.get("task_blueprints") if isinstance(doc.get("task_blueprints"), list) else []
    task_rows = [row for row in tasks if isinstance(row, dict)]
    dimensions = (
        doc.get("scoring_dimension_blueprints")
        if isinstance(doc.get("scoring_dimension_blueprints"), list)
        else []
    )
    abstention_rules = doc.get("abstention_rules") if isinstance(doc.get("abstention_rules"), list) else []
    pairs = [
        ("task_blueprint_count", len(tasks)),
        (
            "blocked_task_blueprints",
            sum(1 for row in task_rows if row.get("instantiation_status") == "blocked_pending_source_review"),
        ),
        ("scoring_dimension_count", len(dimensions)),
        ("abstention_rule_count", len(abstention_rules)),
        (
            "task_source_grounding_contract_count",
            sum(1 for row in task_rows if isinstance(row.get("source_grounding_requirements"), dict)),
        ),
        (
            "tasks_requiring_legal_claim_anchor",
            sum(
                1
                for row in task_rows
                if isinstance(row.get("source_grounding_requirements"), dict)
                and row["source_grounding_requirements"].get("minimum_reviewed_legal_claim_anchor_sources", 0) >= 1
            ),
        ),
        (
            "tasks_requiring_source_gap_marker",
            sum(
                1
                for row in task_rows
                if isinstance(row.get("source_grounding_requirements"), dict)
                and row["source_grounding_requirements"].get("requires_source_gap_marker_when_anchor_missing") is True
            ),
        ),
        (
            "legal_claim_anchor_source_channel_count",
            len(source_matrix_builder.legal_claim_anchor_source_channel_ids()),
        ),
        (
            "legal_claim_anchor_source_channel_ids",
            source_matrix_builder.legal_claim_anchor_source_channel_ids(),
        ),
        (
            "tasks_barring_informal_standalone_claims",
            sum(
                1
                for row in task_rows
                if isinstance(row.get("source_grounding_requirements"), dict)
                and row["source_grounding_requirements"].get("informal_or_context_source_policy")
                == "lead_or_context_only_never_standalone_legal_claim"
            ),
        ),
        (
            "tasks_requiring_temporal_validity",
            sum(
                1
                for row in task_rows
                if isinstance(row.get("source_grounding_requirements"), dict)
                and row["source_grounding_requirements"].get("requires_effective_or_current_as_of_note") is True
                and row["source_grounding_requirements"].get("requires_supersession_check") is True
            ),
        ),
        (
            "tasks_requiring_language_access_review",
            sum(
                1
                for row in task_rows
                if isinstance(row.get("source_grounding_requirements"), dict)
                and row["source_grounding_requirements"].get("requires_source_language_or_script_note") is True
                and row["source_grounding_requirements"].get("requires_translation_review_when_not_working_language") is True
            ),
        ),
        (
            "tasks_requiring_entity_resolution_review",
            sum(
                1
                for row in task_rows
                if isinstance(row.get("source_grounding_requirements"), dict)
                and row["source_grounding_requirements"].get("requires_entity_resolution_review") is True
            ),
        ),
        (
            "tasks_requiring_remedy_forum_review",
            sum(
                1
                for row in task_rows
                if isinstance(row.get("source_grounding_requirements"), dict)
                and row["source_grounding_requirements"].get("requires_remedy_forum_scope_review") is True
            ),
        ),
        (
            "tasks_requiring_authority_hierarchy_review",
            sum(
                1
                for row in task_rows
                if isinstance(row.get("source_grounding_requirements"), dict)
                and row["source_grounding_requirements"].get("requires_authority_hierarchy_review") is True
            ),
        ),
        (
            "tasks_requiring_coverage_scope_review",
            sum(
                1
                for row in task_rows
                if isinstance(row.get("source_grounding_requirements"), dict)
                and row["source_grounding_requirements"].get("requires_coverage_scope_review") is True
            ),
        ),
        (
            "tasks_requiring_jurisdiction_chain_review",
            sum(
                1
                for row in task_rows
                if isinstance(row.get("source_grounding_requirements"), dict)
                and row["source_grounding_requirements"].get("requires_jurisdiction_chain_review") is True
            ),
        ),
        (
            "tasks_requiring_implementation_status_review",
            sum(
                1
                for row in task_rows
                if isinstance(row.get("source_grounding_requirements"), dict)
                and row["source_grounding_requirements"].get("requires_implementation_status_review") is True
            ),
        ),
        (
            "tasks_requiring_procedural_burden_review",
            sum(
                1
                for row in task_rows
                if isinstance(row.get("source_grounding_requirements"), dict)
                and row["source_grounding_requirements"].get("requires_procedural_burden_review") is True
            ),
        ),
    ]
    for key in READY_FLAG_KEYS:
        ready = any(row.get(key) is True for row in task_rows)
        if key == "ready_for_comparable_scoring":
            ready = ready or any(
                isinstance(row, dict) and row.get("ready_for_comparable_scoring") is True
                for row in dimensions
            )
        pairs.append((key, ready))
    return [
        {"summary_key": key, "expected": expected, "actual": summary.get(key)}
        for key, expected in pairs
        if summary.get(key) != expected
    ]


def _readiness_drift(doc: dict[str, Any]) -> list[str]:
    summary = doc.get("summary") if isinstance(doc.get("summary"), dict) else {}
    findings = [f"summary.{key}" for key in READY_FLAG_KEYS if summary.get(key) is not False]
    for idx, row in enumerate(doc.get("task_blueprints") or []):
        if not isinstance(row, dict):
            findings.append(f"task_blueprints[{idx}]")
            continue
        if row.get("instantiation_status") != "blocked_pending_source_review":
            findings.append(f"task_blueprints[{idx}].instantiation_status")
        for key in READY_FLAG_KEYS:
            if row.get(key) is not False:
                findings.append(f"task_blueprints[{idx}].{key}")
    for idx, row in enumerate(doc.get("scoring_dimension_blueprints") or []):
        if not isinstance(row, dict):
            findings.append(f"scoring_dimension_blueprints[{idx}]")
            continue
        if row.get("ready_for_comparable_scoring") is not False:
            findings.append(f"scoring_dimension_blueprints[{idx}].ready_for_comparable_scoring")
    return findings


def _current_reference(
    *,
    domain_id: str,
    config_path: pathlib.Path,
    registry_path: pathlib.Path,
    regulatory_catalog_path: pathlib.Path,
    component_dir: pathlib.Path,
) -> dict[str, Any]:
    return blueprint_builder.build_benchmark_blueprint(
        domain_id=domain_id,
        config_path=config_path,
        registry_path=registry_path,
        regulatory_catalog_path=regulatory_catalog_path,
        component_dir=component_dir,
    )


def _comparable_sections(doc: dict[str, Any]) -> dict[str, Any]:
    return {
        "summary": doc.get("summary"),
        "task_blueprints": doc.get("task_blueprints"),
        "scoring_dimension_blueprints": doc.get("scoring_dimension_blueprints"),
        "abstention_rules": doc.get("abstention_rules"),
    }


def validate_benchmark_blueprint(
    doc: Any,
    *,
    blueprint_path: pathlib.Path | None = None,
    domain_id: str = DEFAULT_DOMAIN,
    config_path: pathlib.Path = project_plan_builder.CONFIG,
    registry_path: pathlib.Path = project_plan_builder.REGISTRY,
    regulatory_catalog_path: pathlib.Path = project_plan_builder.REGULATORY_CATALOG,
    component_dir: pathlib.Path = blueprint_builder.OUT_DIR,
    compare_current_chain: bool = True,
) -> dict[str, Any]:
    if not isinstance(doc, dict):
        checks = [_check("blueprint_is_object", False, expected="object", actual=type(doc).__name__)]
        failed = _failed_ids(checks)
        return {
            "_meta": {
                "schema_version": "global_protections_benchmark_blueprint_validation.v1",
                "source_blueprint_path": _display_path(blueprint_path) if blueprint_path else "n/a",
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
    encoded = json.dumps(doc, ensure_ascii=False)
    disallowed = [term for term in DISALLOWED_TERMS if term in encoded]
    privacy_scan = project_plan_builder._scan_privacy(doc)
    embedded = _embedded_check_drift(doc.get("checks"))
    abstention = _abstention_rule_drift(doc)
    legal_anchor_channel_drift = _legal_anchor_channel_drift(doc)
    current = (
        _current_reference(
            domain_id=domain_id,
            config_path=config_path,
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
        _check("task_blueprint_shape", not _task_shape_drift(doc), expected=[], actual=_task_shape_drift(doc)),
        _check(
            "source_grounding_contracts_intact",
            not _grounding_contract_drift(doc),
            expected=[],
            actual=_grounding_contract_drift(doc),
        ),
        _check(
            "legal_claim_anchor_channels_match_source_matrix",
            not legal_anchor_channel_drift,
            expected=[],
            actual=legal_anchor_channel_drift,
        ),
        _check("dimension_shape", not _dimension_shape_drift(doc), expected=[], actual=_dimension_shape_drift(doc)),
        _check(
            "abstention_rules_match_contract",
            not abstention["missing_ids"] and not abstention["extra_ids"] and not abstention["shape_findings"],
            expected=[row["id"] for row in blueprint_builder._ABSTENTION_RULES],
            actual=abstention,
        ),
        _check(
            "summary_counts_match_blueprint",
            not _summary_count_mismatches(doc),
            expected=[],
            actual=_summary_count_mismatches(doc),
        ),
        _check(
            "embedded_checks_all_ok",
            not embedded["failed"] and not embedded["missing_required"],
            expected={"failed": [], "missing_required": []},
            actual=embedded,
        ),
        _check("all_readiness_flags_blocked", not _readiness_drift(doc), expected=[], actual=_readiness_drift(doc)),
        _check("privacy_scan_ok", privacy_scan.get("ok") is True, expected=True, actual=privacy_scan.get("counts")),
        _check("blueprint_contains_no_disallowed_text", not disallowed, expected=[], actual=disallowed),
    ]
    if compare_current_chain:
        checks.append(
            _check(
                "benchmark_blueprint_matches_current_chain",
                _comparable_sections(doc) == current_sections,
                expected=current_sections,
                actual=_comparable_sections(doc),
            )
        )
    failed = _failed_ids(checks)
    return {
        "_meta": {
            "schema_version": "global_protections_benchmark_blueprint_validation.v1",
            "source_blueprint_path": _display_path(blueprint_path) if blueprint_path else "n/a",
            "domain": domain_id,
            "project_config": _display_path(config_path),
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
            "task_blueprint_count": summary.get("task_blueprint_count"),
            "blocked_task_blueprints": summary.get("blocked_task_blueprints"),
            "scoring_dimension_count": summary.get("scoring_dimension_count"),
            "abstention_rule_count": summary.get("abstention_rule_count"),
            "task_source_grounding_contract_count": summary.get("task_source_grounding_contract_count"),
            "tasks_requiring_legal_claim_anchor": summary.get("tasks_requiring_legal_claim_anchor"),
            "tasks_requiring_source_gap_marker": summary.get("tasks_requiring_source_gap_marker"),
            "legal_claim_anchor_source_channel_count": summary.get(
                "legal_claim_anchor_source_channel_count"
            ),
            "legal_claim_anchor_source_channel_ids": summary.get(
                "legal_claim_anchor_source_channel_ids"
            ),
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
        "# Global Protections Benchmark Blueprint Validation",
        "",
        "This read-only report validates the saved benchmark blueprint before future task work is trusted.",
        "",
        "## Summary",
        "",
        "| Metric | Value |",
        "|---|---:|",
        f"| Valid | {str(bool(summary['valid'])).lower()} |",
        f"| Checks | {summary['check_count']} |",
        f"| Failed checks | {summary['failed_check_count']} |",
        f"| Task blueprints | {_md_cell(summary.get('task_blueprint_count'))} |",
        f"| Blocked task blueprints | {_md_cell(summary.get('blocked_task_blueprints'))} |",
        f"| Scoring dimensions | {_md_cell(summary.get('scoring_dimension_count'))} |",
        f"| Abstention rules | {_md_cell(summary.get('abstention_rule_count'))} |",
        f"| Source-grounding contracts | {_md_cell(summary.get('task_source_grounding_contract_count'))} |",
        f"| Tasks requiring legal-claim anchor | {_md_cell(summary.get('tasks_requiring_legal_claim_anchor'))} |",
        f"| Tasks requiring source-gap marker | {_md_cell(summary.get('tasks_requiring_source_gap_marker'))} |",
        f"| Legal-claim anchor source channels | {_md_cell(summary.get('legal_claim_anchor_source_channel_count'))} |",
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
    ap.add_argument("--blueprint", type=pathlib.Path, default=DEFAULT_BLUEPRINT)
    ap.add_argument("--domain", default=DEFAULT_DOMAIN)
    ap.add_argument("--config", type=pathlib.Path, default=project_plan_builder.CONFIG)
    ap.add_argument("--registry", type=pathlib.Path, default=project_plan_builder.REGISTRY)
    ap.add_argument("--regulatory-catalog", type=pathlib.Path, default=project_plan_builder.REGULATORY_CATALOG)
    ap.add_argument("--component-dir", type=pathlib.Path, default=blueprint_builder.OUT_DIR)
    ap.add_argument("--out", type=pathlib.Path, default=OUT)
    ap.add_argument("--markdown-out", type=pathlib.Path, default=MD_OUT)
    ap.add_argument("--no-current-chain", action="store_true", help="skip comparison to the current generated chain")
    ap.add_argument("--validate", action="store_true", help="print the validation summary only; write nothing")
    args = ap.parse_args(argv)

    doc = _load_json(args.blueprint)
    if doc is None:
        print(f"[global-protections-benchmark-blueprint-validation] unreadable blueprint: {args.blueprint}")
        return 1
    report = validate_benchmark_blueprint(
        doc,
        blueprint_path=args.blueprint,
        domain_id=args.domain,
        config_path=args.config,
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
        "[global-protections-benchmark-blueprint-validation] "
        f"valid={str(bool(summary['valid'])).lower()}; "
        f"failed={summary['failed_check_count']}/{summary['check_count']}; "
        f"ready_for_comparable_scoring={str(bool(summary['ready_for_comparable_scoring'])).lower()} -> {args.blueprint}"
    )
    return 0 if summary["valid"] else 1


if __name__ == "__main__":
    raise SystemExit(main())
