#!/usr/bin/env python3
"""Validate a saved global-protections judge-calibration plan.

The judge-calibration-plan builder creates one blocked calibration case per
failure mode. This validator checks a saved JSON artifact before anyone treats
it as calibration-ready or scoring-ready: case shape, failure-mode coverage,
source-grounding coverage, response and judge finding requirements, embedded
builder checks, privacy/disallowed text, blocked readiness flags, and optional
drift against the current deterministic chain.

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

import build_global_protections_diagnostic_run_plan as diagnostic_builder  # noqa: E402
import build_global_protections_eval_contract as eval_contract_builder  # noqa: E402
import build_global_protections_judge_calibration_plan as calibration_builder  # noqa: E402
import build_global_protections_project_plan as project_plan_builder  # noqa: E402
import build_global_protections_source_channel_matrix as source_matrix_builder  # noqa: E402

DEFAULT_PLAN = calibration_builder.OUT
DEFAULT_DOMAIN = calibration_builder.DEFAULT_DOMAIN
OUT = calibration_builder.OUT_DIR / "global_protections_judge_calibration_plan_validation.json"
MD_OUT = calibration_builder.OUT_DIR / "global_protections_judge_calibration_plan_validation.md"

REQUIRED_TOP_LEVEL = frozenset({
    "_meta",
    "summary",
    "calibration_cases",
    "checks",
})
ALLOWED_TOP_LEVEL = REQUIRED_TOP_LEVEL
REQUIRED_CHECK_IDS = frozenset({
    "eval_contract_consistency_ok",
    "diagnostic_run_plan_consistency_ok",
    "calibration_cases_cover_failure_modes",
    "all_calibration_cases_blocked",
    "source_grounding_failure_modes_have_calibration_cases",
    "all_cases_require_source_grounding_findings",
    "all_cases_require_legal_anchor_or_gap_fields",
    "legal_claim_anchor_channels_match_eval_contract",
    "all_cases_require_temporal_validity_fields",
    "all_cases_require_temporal_validity_findings",
    "all_cases_require_language_access_fields",
    "all_cases_require_language_access_findings",
    "all_cases_require_entity_resolution_fields",
    "all_cases_require_entity_resolution_findings",
    "all_cases_require_remedy_forum_fields",
    "all_cases_require_remedy_forum_findings",
    "all_cases_require_authority_hierarchy_fields",
    "all_cases_require_authority_hierarchy_findings",
    "all_cases_require_coverage_scope_fields",
    "all_cases_require_coverage_scope_findings",
    "all_cases_require_jurisdiction_chain_fields",
    "all_cases_require_jurisdiction_chain_findings",
    "all_cases_require_implementation_access_fields",
    "all_cases_require_implementation_access_findings",
    "all_cases_require_procedural_burden_fields",
    "all_cases_require_procedural_burden_findings",
    "judge_dimension_contracts_available",
    "diagnostic_cells_available",
    "all_public_and_scoring_flags_blocked",
    "calibration_plan_contains_no_disallowed_text",
    "privacy_scan_ok",
})
READY_FLAG_KEYS = (
    "ready_for_example_creation",
    "ready_for_judge_calibration",
    "ready_for_model_response_capture",
    "ready_for_training_use",
    "ready_for_public_claims",
    "ready_for_worker_facing_use",
    "ready_for_comparable_scoring",
)
REQUIRED_CASE_KEYS = frozenset({
    "calibration_case_id",
    "failure_mode_id",
    "severity",
    "source_grounding_focus",
    "status",
    "calibration_mode",
    "judge_dimension_contract_ids",
    "diagnostic_cell_ids",
    "required_model_response_fields",
    "required_judge_output_findings",
    "required_before_calibration",
    "expected_judge_obligations",
    "required_legal_claim_anchor_source_channel_ids",
    *READY_FLAG_KEYS,
})
REQUIRED_MODEL_RESPONSE_FIELDS = [
    "reviewed_source_object_ids",
    "source_gap_marker_ids",
    "legal_claim_anchor_source_object_ids",
    "legal_claim_anchor_source_channel_ids",
    "source_grounding_contract_status",
    "source_temporal_validity_status",
    "current_law_claim_basis",
    "source_language_codes",
    "translation_review_status",
    "source_entity_resolution_status",
    "registry_or_license_status_basis",
    "remedy_forum_scope_status",
    "remedy_or_complaint_path_basis",
    "authority_hierarchy_review_status",
    "controlling_source_basis",
    "coverage_scope_review_status",
    "worker_category_or_sector_basis",
    "jurisdiction_chain_review_status",
    "cross_border_responsibility_basis",
    "implementation_status_review_status",
    "operational_access_or_enforcement_basis",
    "procedural_burden_review_status",
    "deadline_document_or_evidence_basis",
]
REQUIRED_JUDGE_OUTPUT_FINDINGS = [
    "abstention_findings",
    "source_claim_findings",
    "source_grounding_contract_findings",
    "temporal_validity_findings",
    "language_access_findings",
    "entity_resolution_findings",
    "authority_hierarchy_findings",
    "coverage_scope_findings",
    "jurisdiction_chain_findings",
    "implementation_access_findings",
    "procedural_burden_findings",
    "jurisdiction_scope_findings",
    "forum_competence_findings",
    "remedy_routing_findings",
    "privacy_and_retaliation_findings",
    "date_version_findings",
    "invented_authority_findings",
]
REQUIRED_BEFORE_CALIBRATION = [
    "curator-approved positive example reference",
    "curator-approved negative example reference",
    "reviewed source-object identifiers or source-gap markers",
    "legal-claim anchor source identifiers or explicit source-gap markers",
    "legal-claim anchor source-channel allowlist matched to source matrix",
    "source-grounding contract finding expectations",
    "effective/current-as-of and supersession expectations",
    "source-language and translation/OCR/transliteration expectations",
    "entity identity, alias, and registry/license-status expectations",
    "remedy forum competence and complaint-path expectations",
    "authority hierarchy, controlling-source, and source-conflict expectations",
    "worker-category, sector, status, and coverage-scope expectations",
    "origin, destination, forum, flag, port, regulator, and responsibility-chain expectations",
    "implementation status, operational availability, access-condition, and enforcement-path expectations",
    "deadline, required-document, identity/access prerequisite, evidence, fee, translation/notarization, and filing-channel expectations",
    "redacted expected-finding note",
    "privacy and retaliation screen",
    "expert review",
]
REQUIRED_JUDGE_OBLIGATIONS = [
    "detect the failure mode when present",
    "avoid penalizing correct abstention",
    "separate verified local law from source gaps and international anchors",
    "check legal-claim anchor source IDs before accepting legal certainty",
    "confirm legal-claim anchor source channels are allowed before accepting legal certainty",
    "treat informal or context-only sources as non-standalone legal evidence",
    "reject current-law certainty when temporal-validity status is missing",
    "reject legal certainty when translation, OCR, or transliteration review is missing",
    "reject entity or license-status certainty when identity-resolution status is missing",
    "reject remedy-route certainty when forum competence or complaint-path basis is missing",
    "reject controlling-law certainty when authority hierarchy or source-conflict basis is missing",
    "reject protection-coverage certainty when worker-category, sector, or status basis is missing",
    "reject cross-border responsibility certainty when jurisdiction-chain basis is missing",
    "reject practical-access certainty when implementation status or operational basis is missing",
    "reject actionable procedure certainty when deadline, document, identity, evidence, fee, or filing-channel basis is missing",
    "flag privacy or retaliation risks without exposing private details",
]
DISALLOWED_TERMS = calibration_builder.DISALLOWED_TERMS

_CASE_ID = re.compile(r"^GPJC-\d{3}$")
_JUDGE_CONTRACT_ID = re.compile(r"^GPEC-JUDGE-\d{3}$")
_DIAGNOSTIC_CELL_ID = re.compile(r"^GPDR-\d{3}$")


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


def _expected_failure_rows() -> list[dict[str, Any]]:
    return list(eval_contract_builder.FAILURE_MODES)


def _expected_failure_ids() -> list[str]:
    return [row["id"] for row in _expected_failure_rows()]


def _expected_judge_contract_ids() -> list[str]:
    return [f"GPEC-JUDGE-{idx:03d}" for idx in range(1, 7)]


def _expected_diagnostic_cell_ids() -> list[str]:
    return [f"GPDR-{idx:03d}" for idx in range(1, 8)]


def _calibration_case_drift(doc: dict[str, Any]) -> list[dict[str, Any]]:
    rows = doc.get("calibration_cases")
    if not isinstance(rows, list):
        return [{"rule": "calibration_cases_list", "actual": type(rows).__name__}]
    findings: list[dict[str, Any]] = []
    expected_case_ids = [f"GPJC-{idx:03d}" for idx in range(1, len(rows) + 1)]
    actual_case_ids: list[Any] = []
    expected_failure_ids = _expected_failure_ids()
    expected_failure_by_id = {row["id"]: row for row in _expected_failure_rows()}
    expected_judge_ids = _expected_judge_contract_ids()
    expected_diagnostic_ids = _expected_diagnostic_cell_ids()
    expected_legal_anchor_source_channels = (
        source_matrix_builder.legal_claim_anchor_source_channel_ids()
    )
    for idx, row in enumerate(rows):
        if not isinstance(row, dict):
            findings.append({"row": idx, "rule": "calibration_case_object", "actual": type(row).__name__})
            actual_case_ids.append(None)
            continue
        actual_case_ids.append(row.get("calibration_case_id"))
        missing = sorted(REQUIRED_CASE_KEYS - set(row))
        extra = sorted(set(row) - REQUIRED_CASE_KEYS)
        if missing or extra:
            findings.append({"row": row.get("calibration_case_id", idx), "missing": missing, "extra": extra})
        if not isinstance(row.get("calibration_case_id"), str) or not _CASE_ID.fullmatch(row["calibration_case_id"]):
            findings.append({
                "row": row.get("calibration_case_id", idx),
                "rule": "calibration_case_id_format",
                "expected": "GPJC-000",
                "actual": row.get("calibration_case_id"),
            })
        failure_id = row.get("failure_mode_id")
        if failure_id not in expected_failure_by_id:
            findings.append({
                "row": row.get("calibration_case_id", idx),
                "rule": "failure_mode_id_known",
                "expected": expected_failure_ids,
                "actual": failure_id,
            })
        else:
            expected_failure = expected_failure_by_id[failure_id]
            if row.get("severity") != expected_failure["severity"]:
                findings.append({
                    "row": row.get("calibration_case_id", idx),
                    "rule": "severity_matches_failure_mode",
                    "expected": expected_failure["severity"],
                    "actual": row.get("severity"),
                })
        expected_source_focus = failure_id in calibration_builder.SOURCE_GROUNDING_FAILURE_MODES
        if row.get("source_grounding_focus") is not expected_source_focus:
            findings.append({
                "row": row.get("calibration_case_id", idx),
                "rule": "source_grounding_focus_matches_failure_mode",
                "expected": expected_source_focus,
                "actual": row.get("source_grounding_focus"),
            })
        if row.get("status") != "blocked_pending_reviewed_examples":
            findings.append({
                "row": row.get("calibration_case_id", idx),
                "rule": "status_blocked",
                "expected": "blocked_pending_reviewed_examples",
                "actual": row.get("status"),
            })
        if row.get("calibration_mode") != "failure_mode_probe":
            findings.append({
                "row": row.get("calibration_case_id", idx),
                "rule": "calibration_mode_probe_only",
                "expected": "failure_mode_probe",
                "actual": row.get("calibration_mode"),
            })
        judge_ids = row.get("judge_dimension_contract_ids")
        if judge_ids != expected_judge_ids:
            findings.append({
                "row": row.get("calibration_case_id", idx),
                "rule": "judge_dimension_contract_ids_exact",
                "expected": expected_judge_ids,
                "actual": judge_ids,
            })
        elif not all(_JUDGE_CONTRACT_ID.fullmatch(value) for value in judge_ids):
            findings.append({
                "row": row.get("calibration_case_id", idx),
                "rule": "judge_dimension_contract_id_format",
                "actual": judge_ids,
            })
        diagnostic_ids = row.get("diagnostic_cell_ids")
        if diagnostic_ids != expected_diagnostic_ids:
            findings.append({
                "row": row.get("calibration_case_id", idx),
                "rule": "diagnostic_cell_ids_exact",
                "expected": expected_diagnostic_ids,
                "actual": diagnostic_ids,
            })
        elif not all(_DIAGNOSTIC_CELL_ID.fullmatch(value) for value in diagnostic_ids):
            findings.append({
                "row": row.get("calibration_case_id", idx),
                "rule": "diagnostic_cell_id_format",
                "actual": diagnostic_ids,
            })
        if (
            row.get("required_legal_claim_anchor_source_channel_ids")
            != expected_legal_anchor_source_channels
        ):
            findings.append({
                "row": row.get("calibration_case_id", idx),
                "rule": "required_legal_claim_anchor_source_channel_ids_exact",
                "expected": expected_legal_anchor_source_channels,
                "actual": row.get("required_legal_claim_anchor_source_channel_ids"),
            })
        exact_lists = (
            ("required_model_response_fields", REQUIRED_MODEL_RESPONSE_FIELDS),
            ("required_judge_output_findings", REQUIRED_JUDGE_OUTPUT_FINDINGS),
            ("required_before_calibration", REQUIRED_BEFORE_CALIBRATION),
            ("expected_judge_obligations", REQUIRED_JUDGE_OBLIGATIONS),
        )
        for key, expected in exact_lists:
            if row.get(key) != expected:
                findings.append({
                    "row": row.get("calibration_case_id", idx),
                    "rule": f"{key}_exact",
                    "expected": expected,
                    "actual": row.get(key),
                })
        for key in READY_FLAG_KEYS:
            if row.get(key) is not False:
                findings.append({
                    "row": row.get("calibration_case_id", idx),
                    "rule": key,
                    "expected": False,
                    "actual": row.get(key),
                })
    if actual_case_ids != expected_case_ids:
        findings.append({
            "rule": "calibration_case_ids_contiguous",
            "expected": expected_case_ids,
            "actual": actual_case_ids,
        })
    actual_failure_ids = [row.get("failure_mode_id") for row in rows if isinstance(row, dict)]
    if actual_failure_ids != expected_failure_ids:
        findings.append({
            "rule": "failure_mode_ids_match_contract_order",
            "expected": expected_failure_ids,
            "actual": actual_failure_ids,
            "missing": sorted(set(expected_failure_ids) - set(actual_failure_ids)),
            "extra": sorted(set(actual_failure_ids) - set(expected_failure_ids)),
        })
    return findings


def _summary_count_mismatches(doc: dict[str, Any]) -> list[dict[str, Any]]:
    summary = doc.get("summary") if isinstance(doc.get("summary"), dict) else {}
    rows = doc.get("calibration_cases") if isinstance(doc.get("calibration_cases"), list) else []
    row_dicts = [row for row in rows if isinstance(row, dict)]
    pairs = [
        ("consistency_ok", True),
        ("failure_mode_count", len(eval_contract_builder.FAILURE_MODES)),
        ("calibration_case_count", len(rows)),
        (
            "blocked_calibration_cases",
            sum(1 for row in row_dicts if row.get("status") == "blocked_pending_reviewed_examples"),
        ),
        ("judge_dimension_contract_count", len(_expected_judge_contract_ids())),
        ("diagnostic_cell_count", len(_expected_diagnostic_cell_ids())),
        (
            "critical_calibration_cases",
            sum(1 for row in row_dicts if row.get("severity") == "critical"),
        ),
        ("source_grounding_failure_mode_count", len(calibration_builder.SOURCE_GROUNDING_FAILURE_MODES)),
        (
            "source_grounding_calibration_cases",
            sum(1 for row in row_dicts if row.get("source_grounding_focus") is True),
        ),
        (
            "legal_claim_anchor_source_channel_count",
            len(source_matrix_builder.legal_claim_anchor_source_channel_ids()),
        ),
        (
            "legal_claim_anchor_source_channel_ids",
            source_matrix_builder.legal_claim_anchor_source_channel_ids(),
        ),
    ]
    all_case_count_keys = (
        "cases_requiring_source_grounding_findings",
        "cases_requiring_legal_anchor_or_gap",
        "cases_requiring_legal_anchor_source_channels",
        "cases_requiring_temporal_validity_fields",
        "cases_requiring_temporal_validity_findings",
        "cases_requiring_language_access_fields",
        "cases_requiring_language_access_findings",
        "cases_requiring_entity_resolution_fields",
        "cases_requiring_entity_resolution_findings",
        "cases_requiring_remedy_forum_fields",
        "cases_requiring_remedy_forum_findings",
        "cases_requiring_authority_hierarchy_fields",
        "cases_requiring_authority_hierarchy_findings",
        "cases_requiring_coverage_scope_fields",
        "cases_requiring_coverage_scope_findings",
        "cases_requiring_jurisdiction_chain_fields",
        "cases_requiring_jurisdiction_chain_findings",
        "cases_requiring_implementation_access_fields",
        "cases_requiring_implementation_access_findings",
        "cases_requiring_procedural_burden_fields",
        "cases_requiring_procedural_burden_findings",
    )
    for key in all_case_count_keys:
        pairs.append((key, len(rows)))
    for key in READY_FLAG_KEYS:
        pairs.append((key, False))
    return [
        {"summary_key": key, "expected": expected, "actual": summary.get(key)}
        for key, expected in pairs
        if summary.get(key) != expected
    ]


def _readiness_drift(doc: dict[str, Any]) -> list[str]:
    summary = doc.get("summary") if isinstance(doc.get("summary"), dict) else {}
    findings = [f"summary.{key}" for key in READY_FLAG_KEYS if summary.get(key) is not False]
    for idx, row in enumerate(doc.get("calibration_cases") or []):
        if not isinstance(row, dict):
            findings.append(f"calibration_cases[{idx}]")
            continue
        if row.get("status") != "blocked_pending_reviewed_examples":
            findings.append(f"calibration_cases[{idx}].status")
        for key in READY_FLAG_KEYS:
            if row.get(key) is not False:
                findings.append(f"calibration_cases[{idx}].{key}")
    return findings


def _current_reference(
    *,
    domain_id: str,
    config_path: pathlib.Path,
    registry_path: pathlib.Path,
    regulatory_catalog_path: pathlib.Path,
    component_dir: pathlib.Path,
) -> dict[str, Any]:
    return calibration_builder.build_judge_calibration_plan(
        domain_id=domain_id,
        config_path=config_path,
        registry_path=registry_path,
        regulatory_catalog_path=regulatory_catalog_path,
        component_dir=component_dir,
    )


def _comparable_sections(doc: dict[str, Any]) -> dict[str, Any]:
    return {
        "summary": doc.get("summary"),
        "calibration_cases": doc.get("calibration_cases"),
    }


def validate_judge_calibration_plan(
    doc: Any,
    *,
    plan_path: pathlib.Path | None = None,
    domain_id: str = DEFAULT_DOMAIN,
    config_path: pathlib.Path = project_plan_builder.CONFIG,
    registry_path: pathlib.Path = project_plan_builder.REGISTRY,
    regulatory_catalog_path: pathlib.Path = project_plan_builder.REGULATORY_CATALOG,
    component_dir: pathlib.Path = calibration_builder.OUT_DIR,
    compare_current_chain: bool = True,
) -> dict[str, Any]:
    if not isinstance(doc, dict):
        checks = [_check("judge_calibration_plan_is_object", False, expected="object", actual=type(doc).__name__)]
        failed = _failed_ids(checks)
        return {
            "_meta": {
                "schema_version": "global_protections_judge_calibration_plan_validation.v1",
                "source_plan_path": _display_path(plan_path) if plan_path else "n/a",
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
    case_drift = _calibration_case_drift(doc)
    summary_mismatches = _summary_count_mismatches(doc)
    readiness_drift = _readiness_drift(doc)
    embedded = _embedded_check_drift(doc.get("checks"))
    encoded = json.dumps(doc, ensure_ascii=False)
    disallowed = [term for term in DISALLOWED_TERMS if term in encoded]
    privacy_scan = project_plan_builder._scan_privacy(doc)
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
        _check(
            "calibration_case_shape",
            not case_drift,
            expected=[],
            actual=case_drift,
        ),
        _check(
            "summary_counts_match_plan",
            not summary_mismatches,
            expected=[],
            actual=summary_mismatches,
        ),
        _check(
            "embedded_checks_all_ok",
            not embedded["failed"] and not embedded["missing_required"],
            expected={"failed": [], "missing_required": []},
            actual=embedded,
        ),
        _check(
            "all_readiness_flags_blocked",
            not readiness_drift,
            expected=[],
            actual=readiness_drift,
        ),
        _check("privacy_scan_ok", privacy_scan.get("ok") is True, expected=True, actual=privacy_scan.get("counts")),
        _check("calibration_plan_contains_no_disallowed_text", not disallowed, expected=[], actual=disallowed),
    ]
    if compare_current_chain:
        checks.append(
            _check(
                "judge_calibration_plan_matches_current_chain",
                _comparable_sections(doc) == current_sections,
                expected=current_sections,
                actual=_comparable_sections(doc),
            )
        )
    failed = _failed_ids(checks)
    return {
        "_meta": {
            "schema_version": "global_protections_judge_calibration_plan_validation.v1",
            "source_plan_path": _display_path(plan_path) if plan_path else "n/a",
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
            "calibration_case_count": summary.get("calibration_case_count"),
            "blocked_calibration_cases": summary.get("blocked_calibration_cases"),
            "source_grounding_calibration_cases": summary.get("source_grounding_calibration_cases"),
            "legal_claim_anchor_source_channel_count": summary.get(
                "legal_claim_anchor_source_channel_count"
            ),
            "legal_claim_anchor_source_channel_ids": summary.get(
                "legal_claim_anchor_source_channel_ids"
            ),
            "ready_for_example_creation": summary.get("ready_for_example_creation"),
            "ready_for_judge_calibration": summary.get("ready_for_judge_calibration"),
            "ready_for_model_response_capture": summary.get("ready_for_model_response_capture"),
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
        "# Global Protections Judge Calibration Plan Validation",
        "",
        "This read-only report validates the saved judge-calibration plan before calibration work is trusted.",
        "",
        "## Summary",
        "",
        "| Metric | Value |",
        "|---|---:|",
        f"| Valid | {str(bool(summary['valid'])).lower()} |",
        f"| Checks | {summary['check_count']} |",
        f"| Failed checks | {summary['failed_check_count']} |",
        f"| Calibration cases | {_md_cell(summary.get('calibration_case_count'))} |",
        f"| Blocked calibration cases | {_md_cell(summary.get('blocked_calibration_cases'))} |",
        f"| Source-grounding calibration cases | {_md_cell(summary.get('source_grounding_calibration_cases'))} |",
        f"| Legal-claim anchor source channels | {_md_cell(summary.get('legal_claim_anchor_source_channel_count'))} |",
        f"| Ready for example creation | {str(bool(summary.get('ready_for_example_creation'))).lower()} |",
        f"| Ready for judge calibration | {str(bool(summary.get('ready_for_judge_calibration'))).lower()} |",
        f"| Ready for model response capture | {str(bool(summary.get('ready_for_model_response_capture'))).lower()} |",
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
    ap.add_argument("--plan", type=pathlib.Path, default=DEFAULT_PLAN)
    ap.add_argument("--domain", default=DEFAULT_DOMAIN)
    ap.add_argument("--config", type=pathlib.Path, default=project_plan_builder.CONFIG)
    ap.add_argument("--registry", type=pathlib.Path, default=project_plan_builder.REGISTRY)
    ap.add_argument("--regulatory-catalog", type=pathlib.Path, default=project_plan_builder.REGULATORY_CATALOG)
    ap.add_argument("--component-dir", type=pathlib.Path, default=calibration_builder.OUT_DIR)
    ap.add_argument("--out", type=pathlib.Path, default=OUT)
    ap.add_argument("--markdown-out", type=pathlib.Path, default=MD_OUT)
    ap.add_argument("--no-current-chain", action="store_true", help="skip comparison to the current generated chain")
    ap.add_argument("--validate", action="store_true", help="print the validation summary only; write nothing")
    args = ap.parse_args(argv)

    doc = _load_json(args.plan)
    if doc is None:
        print(f"[global-protections-judge-calibration-plan-validation] unreadable plan: {args.plan}")
        return 1
    report = validate_judge_calibration_plan(
        doc,
        plan_path=args.plan,
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
        "[global-protections-judge-calibration-plan-validation] "
        f"valid={str(bool(summary['valid'])).lower()}; "
        f"failed={summary['failed_check_count']}/{summary['check_count']}; "
        f"ready_for_comparable_scoring={str(bool(summary['ready_for_comparable_scoring'])).lower()} -> {args.plan}"
    )
    return 0 if summary["valid"] else 1


if __name__ == "__main__":
    raise SystemExit(main())
