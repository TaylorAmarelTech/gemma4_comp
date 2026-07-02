#!/usr/bin/env python3
"""Validate a saved global-protections evaluation contract.

The evaluation-contract builder defines future model-response and judge-output
schemas, failure modes, and run gates. This validator checks a saved JSON
artifact before anyone treats it as current or scoring-ready: field schemas,
judge contracts, failure taxonomy, gate coverage, embedded builder checks,
privacy/disallowed text, blocked readiness flags, and optional drift against the
current deterministic chain.

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

import build_global_protections_eval_contract as eval_builder  # noqa: E402
import build_global_protections_project_plan as project_plan_builder  # noqa: E402
import build_global_protections_source_channel_matrix as source_matrix_builder  # noqa: E402

DEFAULT_CONTRACT = eval_builder.OUT
DEFAULT_DOMAIN = eval_builder.DEFAULT_DOMAIN
OUT = eval_builder.OUT_DIR / "global_protections_eval_contract_validation.json"
MD_OUT = eval_builder.OUT_DIR / "global_protections_eval_contract_validation.md"

REQUIRED_TOP_LEVEL = frozenset({
    "_meta",
    "summary",
    "model_response_record_schema",
    "judge_output_schema",
    "judge_dimension_contracts",
    "failure_modes",
    "run_gates",
    "checks",
})
ALLOWED_TOP_LEVEL = REQUIRED_TOP_LEVEL
REQUIRED_SCHEMA_KEYS = frozenset({"fields", "policy"})
REQUIRED_JUDGE_CONTRACT_KEYS = frozenset({
    "contract_id",
    "dimension_id",
    "capability",
    "required_judge_fields",
    "required_reference_basis",
    "must_penalize_failure_modes",
    "must_reward_behaviors",
    "ready_for_judge_calibration",
    "ready_for_public_claims",
    "ready_for_comparable_scoring",
})
REQUIRED_FAILURE_KEYS = frozenset({"id", "severity", "description"})
REQUIRED_RUN_GATE_KEYS = frozenset({"id", "description", "blocks"})
REQUIRED_CHECK_IDS = frozenset({
    "benchmark_blueprint_consistency_ok",
    "readiness_bundle_consistency_ok",
    "judge_contracts_cover_scoring_dimensions",
    "task_blueprints_still_blocked",
    "blueprint_source_grounding_contracts_cover_tasks",
    "legal_claim_anchor_channels_carried_from_blueprint",
    "required_failure_modes_present",
    "all_public_and_scoring_flags_blocked",
    "model_response_schema_has_source_and_gap_fields",
    "judge_output_schema_has_abstention_and_privacy_fields",
    "judge_contracts_penalize_source_grounding_failures",
    "eval_contract_contains_no_disallowed_text",
    "privacy_scan_ok",
})
READY_FLAG_KEYS = (
    "ready_for_model_response_capture",
    "ready_for_judge_calibration",
    "ready_for_training_use",
    "ready_for_public_claims",
    "ready_for_worker_facing_use",
    "ready_for_comparable_scoring",
)
JUDGE_READY_FLAG_KEYS = (
    "ready_for_judge_calibration",
    "ready_for_public_claims",
    "ready_for_comparable_scoring",
)
TASK_COVERAGE_KEYS = (
    "task_source_grounding_contract_count",
    "tasks_requiring_legal_claim_anchor",
    "tasks_requiring_source_gap_marker",
    "tasks_barring_informal_standalone_claims",
    "tasks_requiring_temporal_validity",
    "tasks_requiring_language_access_review",
    "tasks_requiring_entity_resolution_review",
    "tasks_requiring_remedy_forum_review",
    "tasks_requiring_authority_hierarchy_review",
    "tasks_requiring_coverage_scope_review",
    "tasks_requiring_jurisdiction_chain_review",
    "tasks_requiring_implementation_status_review",
    "tasks_requiring_procedural_burden_review",
)
REQUIRED_PENALIZED_FAILURE_IDS = frozenset({
    "legal_authority_hallucination",
    "jurisdiction_scope_collapse",
    "coverage_scope_overgeneralization",
    "international_anchor_substitution",
    "informal_source_overclaim",
    "authority_precedence_misread",
    "date_version_hallucination",
    "language_access_overclaim",
    "entity_identity_conflation",
    "remedy_forum_hallucination",
    "privacy_retaliation_leakage",
    "overconfident_non_abstention",
    "cross_border_responsibility_miss",
    "implementation_access_overclaim",
    "procedural_burden_overclaim",
})
DISALLOWED_TERMS = eval_builder.DISALLOWED_TERMS

_CONTRACT_ID = re.compile(r"^GPEC-JUDGE-\d{3}$")
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


def _schema_drift(schema: Any, expected_fields: list[str], schema_name: str) -> list[dict[str, Any]]:
    if not isinstance(schema, dict):
        return [{"schema": schema_name, "rule": "schema_object", "actual": type(schema).__name__}]
    findings: list[dict[str, Any]] = []
    missing_keys = sorted(REQUIRED_SCHEMA_KEYS - set(schema))
    extra_keys = sorted(set(schema) - REQUIRED_SCHEMA_KEYS)
    if missing_keys or extra_keys:
        findings.append({
            "schema": schema_name,
            "rule": "schema_keys",
            "missing": missing_keys,
            "extra": extra_keys,
        })
    fields = schema.get("fields")
    if not isinstance(fields, list):
        findings.append({"schema": schema_name, "rule": "fields_list", "actual": type(fields).__name__})
    else:
        missing_fields = sorted(set(expected_fields) - set(fields))
        extra_fields = sorted(set(fields) - set(expected_fields))
        duplicate_fields = sorted({field for field in fields if fields.count(field) > 1})
        if missing_fields or extra_fields:
            findings.append({
                "schema": schema_name,
                "rule": "fields_exact_set",
                "missing": missing_fields,
                "extra": extra_fields,
            })
        if duplicate_fields:
            findings.append({
                "schema": schema_name,
                "rule": "fields_unique",
                "actual": duplicate_fields,
            })
        if fields != expected_fields:
            findings.append({
                "schema": schema_name,
                "rule": "fields_order",
                "expected": expected_fields,
                "actual": fields,
            })
    if not isinstance(schema.get("policy"), str) or not schema.get("policy", "").strip():
        findings.append({"schema": schema_name, "rule": "policy_non_empty", "actual": schema.get("policy")})
    return findings


def _judge_contract_drift(doc: dict[str, Any]) -> list[dict[str, Any]]:
    rows = doc.get("judge_dimension_contracts")
    if not isinstance(rows, list):
        return [{"rule": "judge_dimension_contracts_list", "actual": type(rows).__name__}]
    findings: list[dict[str, Any]] = []
    expected_contract_ids = [f"GPEC-JUDGE-{idx:03d}" for idx in range(1, len(rows) + 1)]
    actual_contract_ids: list[Any] = []
    for idx, row in enumerate(rows):
        if not isinstance(row, dict):
            findings.append({"row": idx, "rule": "judge_contract_object", "actual": type(row).__name__})
            actual_contract_ids.append(None)
            continue
        actual_contract_ids.append(row.get("contract_id"))
        missing = sorted(REQUIRED_JUDGE_CONTRACT_KEYS - set(row))
        extra = sorted(set(row) - REQUIRED_JUDGE_CONTRACT_KEYS)
        if missing or extra:
            findings.append({"row": row.get("contract_id", idx), "missing": missing, "extra": extra})
        if not isinstance(row.get("contract_id"), str) or not _CONTRACT_ID.fullmatch(row["contract_id"]):
            findings.append({
                "row": row.get("contract_id", idx),
                "rule": "contract_id_format",
                "expected": "GPEC-JUDGE-000",
                "actual": row.get("contract_id"),
            })
        if not isinstance(row.get("dimension_id"), str) or not _DIMENSION_ID.fullmatch(row["dimension_id"]):
            findings.append({
                "row": row.get("contract_id", idx),
                "rule": "dimension_id_format",
                "actual": row.get("dimension_id"),
            })
        if not isinstance(row.get("capability"), str) or not row.get("capability", "").strip():
            findings.append({"row": row.get("contract_id", idx), "rule": "capability_non_empty"})
        if row.get("required_judge_fields") != list(eval_builder.JUDGE_OUTPUT_FIELDS):
            findings.append({
                "row": row.get("contract_id", idx),
                "rule": "required_judge_fields_exact",
                "expected": list(eval_builder.JUDGE_OUTPUT_FIELDS),
                "actual": row.get("required_judge_fields"),
            })
        if not isinstance(row.get("required_reference_basis"), list) or not row.get("required_reference_basis"):
            findings.append({
                "row": row.get("contract_id", idx),
                "rule": "required_reference_basis_non_empty",
                "actual": row.get("required_reference_basis"),
            })
        penalized = row.get("must_penalize_failure_modes")
        if not isinstance(penalized, list):
            findings.append({
                "row": row.get("contract_id", idx),
                "rule": "must_penalize_failure_modes_list",
                "actual": type(penalized).__name__,
            })
        else:
            missing_penalties = sorted(REQUIRED_PENALIZED_FAILURE_IDS - set(penalized))
            if missing_penalties:
                findings.append({
                    "row": row.get("contract_id", idx),
                    "rule": "must_penalize_required_failures",
                    "missing": missing_penalties,
                })
        if not isinstance(row.get("must_reward_behaviors"), list) or not row.get("must_reward_behaviors"):
            findings.append({
                "row": row.get("contract_id", idx),
                "rule": "must_reward_behaviors_non_empty",
                "actual": row.get("must_reward_behaviors"),
            })
        for key in JUDGE_READY_FLAG_KEYS:
            if row.get(key) is not False:
                findings.append({
                    "row": row.get("contract_id", idx),
                    "rule": key,
                    "expected": False,
                    "actual": row.get(key),
                })
    if actual_contract_ids != expected_contract_ids:
        findings.append({
            "rule": "judge_contract_ids_contiguous",
            "expected": expected_contract_ids,
            "actual": actual_contract_ids,
        })
    return findings


def _failure_mode_drift(doc: dict[str, Any]) -> list[dict[str, Any]]:
    rows = doc.get("failure_modes")
    if not isinstance(rows, list):
        return [{"rule": "failure_modes_list", "actual": type(rows).__name__}]
    findings: list[dict[str, Any]] = []
    expected_ids = [row["id"] for row in eval_builder.FAILURE_MODES]
    expected_by_id = {row["id"]: row for row in eval_builder.FAILURE_MODES}
    actual_ids: list[Any] = []
    for idx, row in enumerate(rows):
        if not isinstance(row, dict):
            findings.append({"row": idx, "rule": "failure_mode_object", "actual": type(row).__name__})
            actual_ids.append(None)
            continue
        actual_ids.append(row.get("id"))
        missing = sorted(REQUIRED_FAILURE_KEYS - set(row))
        extra = sorted(set(row) - REQUIRED_FAILURE_KEYS)
        if missing or extra:
            findings.append({"row": row.get("id", idx), "missing": missing, "extra": extra})
        expected = expected_by_id.get(row.get("id"))
        if expected and row.get("severity") != expected["severity"]:
            findings.append({
                "row": row.get("id", idx),
                "rule": "failure_severity_matches_contract",
                "expected": expected["severity"],
                "actual": row.get("severity"),
            })
        if not isinstance(row.get("description"), str) or not row.get("description", "").strip():
            findings.append({"row": row.get("id", idx), "rule": "description_non_empty"})
    if actual_ids != expected_ids:
        findings.append({
            "rule": "failure_mode_ids_match_contract",
            "expected": expected_ids,
            "actual": actual_ids,
            "missing": sorted(set(expected_ids) - set(actual_ids)),
            "extra": sorted(set(actual_ids) - set(expected_ids)),
        })
    return findings


def _run_gate_drift(doc: dict[str, Any]) -> list[dict[str, Any]]:
    rows = doc.get("run_gates")
    if not isinstance(rows, list):
        return [{"rule": "run_gates_list", "actual": type(rows).__name__}]
    findings: list[dict[str, Any]] = []
    expected_ids = [row["id"] for row in eval_builder.RUN_GATES]
    expected_by_id = {row["id"]: row for row in eval_builder.RUN_GATES}
    actual_ids: list[Any] = []
    for idx, row in enumerate(rows):
        if not isinstance(row, dict):
            findings.append({"row": idx, "rule": "run_gate_object", "actual": type(row).__name__})
            actual_ids.append(None)
            continue
        actual_ids.append(row.get("id"))
        missing = sorted(REQUIRED_RUN_GATE_KEYS - set(row))
        extra = sorted(set(row) - REQUIRED_RUN_GATE_KEYS)
        if missing or extra:
            findings.append({"row": row.get("id", idx), "missing": missing, "extra": extra})
        expected = expected_by_id.get(row.get("id"))
        if expected and row != expected:
            findings.append({
                "row": row.get("id", idx),
                "rule": "run_gate_matches_contract",
                "expected": expected,
                "actual": row,
            })
        if not isinstance(row.get("blocks"), list) or not row.get("blocks"):
            findings.append({
                "row": row.get("id", idx),
                "rule": "blocks_non_empty",
                "actual": row.get("blocks"),
            })
    if actual_ids != expected_ids:
        findings.append({
            "rule": "run_gate_ids_match_contract",
            "expected": expected_ids,
            "actual": actual_ids,
            "missing": sorted(set(expected_ids) - set(actual_ids)),
            "extra": sorted(set(actual_ids) - set(expected_ids)),
        })
    return findings


def _summary_count_mismatches(doc: dict[str, Any]) -> list[dict[str, Any]]:
    summary = doc.get("summary") if isinstance(doc.get("summary"), dict) else {}
    model_schema = doc.get("model_response_record_schema") if isinstance(doc.get("model_response_record_schema"), dict) else {}
    judge_schema = doc.get("judge_output_schema") if isinstance(doc.get("judge_output_schema"), dict) else {}
    model_fields = model_schema.get("fields") if isinstance(model_schema.get("fields"), list) else []
    judge_fields = judge_schema.get("fields") if isinstance(judge_schema.get("fields"), list) else []
    judge_contracts = doc.get("judge_dimension_contracts") if isinstance(doc.get("judge_dimension_contracts"), list) else []
    failure_modes = doc.get("failure_modes") if isinstance(doc.get("failure_modes"), list) else []
    run_gates = doc.get("run_gates") if isinstance(doc.get("run_gates"), list) else []
    pairs = [
        ("consistency_ok", True),
        ("scoring_dimension_count", len(judge_contracts)),
        ("judge_dimension_contract_count", len(judge_contracts)),
        ("failure_mode_count", len(failure_modes)),
        (
            "critical_failure_mode_count",
            sum(1 for row in failure_modes if isinstance(row, dict) and row.get("severity") == "critical"),
        ),
        ("run_gate_count", len(run_gates)),
        ("model_response_record_field_count", len(model_fields)),
        ("judge_output_field_count", len(judge_fields)),
        (
            "legal_claim_anchor_source_channel_count",
            len(source_matrix_builder.legal_claim_anchor_source_channel_ids()),
        ),
        (
            "legal_claim_anchor_source_channel_ids",
            source_matrix_builder.legal_claim_anchor_source_channel_ids(),
        ),
    ]
    task_count = summary.get("task_blueprint_count")
    for key in TASK_COVERAGE_KEYS:
        pairs.append((key, task_count))
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
    for idx, row in enumerate(doc.get("judge_dimension_contracts") or []):
        if not isinstance(row, dict):
            findings.append(f"judge_dimension_contracts[{idx}]")
            continue
        for key in JUDGE_READY_FLAG_KEYS:
            if row.get(key) is not False:
                findings.append(f"judge_dimension_contracts[{idx}].{key}")
    return findings


def _current_reference(
    *,
    domain_id: str,
    config_path: pathlib.Path,
    registry_path: pathlib.Path,
    regulatory_catalog_path: pathlib.Path,
    component_dir: pathlib.Path,
) -> dict[str, Any]:
    return eval_builder.build_eval_contract(
        domain_id=domain_id,
        config_path=config_path,
        registry_path=registry_path,
        regulatory_catalog_path=regulatory_catalog_path,
        component_dir=component_dir,
    )


def _comparable_sections(doc: dict[str, Any]) -> dict[str, Any]:
    return {
        "summary": doc.get("summary"),
        "model_response_record_schema": doc.get("model_response_record_schema"),
        "judge_output_schema": doc.get("judge_output_schema"),
        "judge_dimension_contracts": doc.get("judge_dimension_contracts"),
        "failure_modes": doc.get("failure_modes"),
        "run_gates": doc.get("run_gates"),
    }


def validate_eval_contract(
    doc: Any,
    *,
    contract_path: pathlib.Path | None = None,
    domain_id: str = DEFAULT_DOMAIN,
    config_path: pathlib.Path = project_plan_builder.CONFIG,
    registry_path: pathlib.Path = project_plan_builder.REGISTRY,
    regulatory_catalog_path: pathlib.Path = project_plan_builder.REGULATORY_CATALOG,
    component_dir: pathlib.Path = eval_builder.OUT_DIR,
    compare_current_chain: bool = True,
) -> dict[str, Any]:
    if not isinstance(doc, dict):
        checks = [_check("eval_contract_is_object", False, expected="object", actual=type(doc).__name__)]
        failed = _failed_ids(checks)
        return {
            "_meta": {
                "schema_version": "global_protections_eval_contract_validation.v1",
                "source_contract_path": _display_path(contract_path) if contract_path else "n/a",
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
    model_schema_drift = _schema_drift(
        doc.get("model_response_record_schema"),
        list(eval_builder.MODEL_RESPONSE_RECORD_FIELDS),
        "model_response_record_schema",
    )
    judge_schema_drift = _schema_drift(
        doc.get("judge_output_schema"),
        list(eval_builder.JUDGE_OUTPUT_FIELDS),
        "judge_output_schema",
    )
    judge_contract_drift = _judge_contract_drift(doc)
    failure_mode_drift = _failure_mode_drift(doc)
    run_gate_drift = _run_gate_drift(doc)
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
            "model_response_record_schema_fields",
            not model_schema_drift,
            expected=list(eval_builder.MODEL_RESPONSE_RECORD_FIELDS),
            actual=model_schema_drift,
        ),
        _check(
            "judge_output_schema_fields",
            not judge_schema_drift,
            expected=list(eval_builder.JUDGE_OUTPUT_FIELDS),
            actual=judge_schema_drift,
        ),
        _check(
            "judge_dimension_contract_shape",
            not judge_contract_drift,
            expected=[],
            actual=judge_contract_drift,
        ),
        _check(
            "failure_modes_match_contract",
            not failure_mode_drift,
            expected=[row["id"] for row in eval_builder.FAILURE_MODES],
            actual=failure_mode_drift,
        ),
        _check(
            "run_gates_match_contract",
            not run_gate_drift,
            expected=[row["id"] for row in eval_builder.RUN_GATES],
            actual=run_gate_drift,
        ),
        _check(
            "summary_counts_match_contract",
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
        _check("eval_contract_contains_no_disallowed_text", not disallowed, expected=[], actual=disallowed),
    ]
    if compare_current_chain:
        checks.append(
            _check(
                "eval_contract_matches_current_chain",
                _comparable_sections(doc) == current_sections,
                expected=current_sections,
                actual=_comparable_sections(doc),
            )
        )
    failed = _failed_ids(checks)
    return {
        "_meta": {
            "schema_version": "global_protections_eval_contract_validation.v1",
            "source_contract_path": _display_path(contract_path) if contract_path else "n/a",
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
            "judge_dimension_contract_count": summary.get("judge_dimension_contract_count"),
            "failure_mode_count": summary.get("failure_mode_count"),
            "run_gate_count": summary.get("run_gate_count"),
            "model_response_record_field_count": summary.get("model_response_record_field_count"),
            "judge_output_field_count": summary.get("judge_output_field_count"),
            "legal_claim_anchor_source_channel_count": summary.get(
                "legal_claim_anchor_source_channel_count"
            ),
            "legal_claim_anchor_source_channel_ids": summary.get(
                "legal_claim_anchor_source_channel_ids"
            ),
            "ready_for_model_response_capture": summary.get("ready_for_model_response_capture"),
            "ready_for_judge_calibration": summary.get("ready_for_judge_calibration"),
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
        "# Global Protections Evaluation Contract Validation",
        "",
        "This read-only report validates the saved evaluation contract before model or judge artifacts are trusted.",
        "",
        "## Summary",
        "",
        "| Metric | Value |",
        "|---|---:|",
        f"| Valid | {str(bool(summary['valid'])).lower()} |",
        f"| Checks | {summary['check_count']} |",
        f"| Failed checks | {summary['failed_check_count']} |",
        f"| Judge dimension contracts | {_md_cell(summary.get('judge_dimension_contract_count'))} |",
        f"| Failure modes | {_md_cell(summary.get('failure_mode_count'))} |",
        f"| Run gates | {_md_cell(summary.get('run_gate_count'))} |",
        f"| Model response fields | {_md_cell(summary.get('model_response_record_field_count'))} |",
        f"| Judge output fields | {_md_cell(summary.get('judge_output_field_count'))} |",
        f"| Legal-claim anchor source channels | {_md_cell(summary.get('legal_claim_anchor_source_channel_count'))} |",
        f"| Ready for model response capture | {str(bool(summary.get('ready_for_model_response_capture'))).lower()} |",
        f"| Ready for judge calibration | {str(bool(summary.get('ready_for_judge_calibration'))).lower()} |",
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
    ap.add_argument("--contract", type=pathlib.Path, default=DEFAULT_CONTRACT)
    ap.add_argument("--domain", default=DEFAULT_DOMAIN)
    ap.add_argument("--config", type=pathlib.Path, default=project_plan_builder.CONFIG)
    ap.add_argument("--registry", type=pathlib.Path, default=project_plan_builder.REGISTRY)
    ap.add_argument("--regulatory-catalog", type=pathlib.Path, default=project_plan_builder.REGULATORY_CATALOG)
    ap.add_argument("--component-dir", type=pathlib.Path, default=eval_builder.OUT_DIR)
    ap.add_argument("--out", type=pathlib.Path, default=OUT)
    ap.add_argument("--markdown-out", type=pathlib.Path, default=MD_OUT)
    ap.add_argument("--no-current-chain", action="store_true", help="skip comparison to the current generated chain")
    ap.add_argument("--validate", action="store_true", help="print the validation summary only; write nothing")
    args = ap.parse_args(argv)

    doc = _load_json(args.contract)
    if doc is None:
        print(f"[global-protections-eval-contract-validation] unreadable contract: {args.contract}")
        return 1
    report = validate_eval_contract(
        doc,
        contract_path=args.contract,
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
        "[global-protections-eval-contract-validation] "
        f"valid={str(bool(summary['valid'])).lower()}; "
        f"failed={summary['failed_check_count']}/{summary['check_count']}; "
        f"ready_for_comparable_scoring={str(bool(summary['ready_for_comparable_scoring'])).lower()} -> {args.contract}"
    )
    return 0 if summary["valid"] else 1


if __name__ == "__main__":
    raise SystemExit(main())
