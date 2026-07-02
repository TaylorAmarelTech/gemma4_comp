#!/usr/bin/env python3
"""Validate a saved global-protections diagnostic run plan.

The diagnostic-run-plan builder creates dry-run cells from the benchmark
blueprint and evaluation contract. This validator checks a saved JSON artifact
before anyone treats it as executable or scoring-ready: cell shape, run-gate
coverage, required response and judge fields, failure checks, embedded builder
checks, privacy/disallowed text, blocked readiness flags, and optional drift
against the current deterministic chain.

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
import build_global_protections_project_plan as project_plan_builder  # noqa: E402
import build_global_protections_source_channel_matrix as source_matrix_builder  # noqa: E402

DEFAULT_PLAN = diagnostic_builder.OUT
DEFAULT_DOMAIN = diagnostic_builder.DEFAULT_DOMAIN
OUT = diagnostic_builder.OUT_DIR / "global_protections_diagnostic_run_plan_validation.json"
MD_OUT = diagnostic_builder.OUT_DIR / "global_protections_diagnostic_run_plan_validation.md"

REQUIRED_TOP_LEVEL = frozenset({
    "_meta",
    "summary",
    "diagnostic_cells",
    "checks",
})
ALLOWED_TOP_LEVEL = REQUIRED_TOP_LEVEL
REQUIRED_CHECK_IDS = frozenset({
    "benchmark_blueprint_consistency_ok",
    "eval_contract_consistency_ok",
    "readiness_bundle_consistency_ok",
    "diagnostic_cells_cover_task_blueprints",
    "all_diagnostic_cells_blocked",
    "run_gates_match_eval_contract",
    "model_response_schema_available",
    "legal_claim_anchor_channels_match_eval_contract",
    "judge_schema_available",
    "core_failure_modes_available",
    "all_public_and_scoring_flags_blocked",
    "diagnostic_plan_contains_no_disallowed_text",
    "privacy_scan_ok",
})
READY_FLAG_KEYS = (
    "ready_for_task_instantiation",
    "ready_for_model_response_capture",
    "ready_for_judge_calibration",
    "ready_for_training_use",
    "ready_for_public_claims",
    "ready_for_worker_facing_use",
    "ready_for_comparable_scoring",
)
REQUIRED_CELL_KEYS = frozenset({
    "diagnostic_cell_id",
    "task_blueprint_id",
    "axis_id",
    "benchmark_axis",
    "status",
    "execution_mode",
    "required_before_model_call",
    "required_run_gate_ids",
    "required_model_response_fields",
    "required_legal_claim_anchor_source_channel_ids",
    "required_judge_output_fields",
    "failure_modes_to_check",
    "expected_artifact_policy",
    *READY_FLAG_KEYS,
})
REQUIRED_BEFORE_MODEL_CALL_ITEMS = frozenset({
    "curator-approved task instantiation",
    "reviewed source-object identifiers or source-gap markers",
    "temporal-validity status for any current-law claim",
    "source-language and translation/OCR/transliteration review status",
    "entity/alias and registry/license-status review basis",
    "remedy/forum competence and complaint-path review basis",
    "authority hierarchy and controlling-source review basis",
    "worker category, sector, status, and coverage-scope review basis",
    "origin, destination, forum, flag, port, regulator, and responsibility-chain review basis",
    "implementation status, operational availability, access-condition, and enforcement-path review basis",
    "privacy and retaliation screen",
    "expert review",
    "source-verified grounding layer",
})
DISALLOWED_TERMS = diagnostic_builder.DISALLOWED_TERMS

_CELL_ID = re.compile(r"^GPDR-\d{3}$")
_TASK_ID = re.compile(r"^GPBB-TASK-\d{3}$")


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


def _expected_run_gate_ids() -> list[str]:
    return [row["id"] for row in eval_contract_builder.RUN_GATES]


def _expected_failure_ids() -> list[str]:
    return list(diagnostic_builder.CORE_FAILURE_IDS)


def _diagnostic_cell_drift(doc: dict[str, Any]) -> list[dict[str, Any]]:
    rows = doc.get("diagnostic_cells")
    if not isinstance(rows, list):
        return [{"rule": "diagnostic_cells_list", "actual": type(rows).__name__}]
    findings: list[dict[str, Any]] = []
    expected_cell_ids = [f"GPDR-{idx:03d}" for idx in range(1, len(rows) + 1)]
    actual_cell_ids: list[Any] = []
    expected_run_gates = _expected_run_gate_ids()
    expected_model_fields = list(eval_contract_builder.MODEL_RESPONSE_RECORD_FIELDS)
    expected_judge_fields = list(eval_contract_builder.JUDGE_OUTPUT_FIELDS)
    expected_legal_anchor_source_channels = (
        source_matrix_builder.legal_claim_anchor_source_channel_ids()
    )
    expected_failures = _expected_failure_ids()
    for idx, row in enumerate(rows):
        if not isinstance(row, dict):
            findings.append({"row": idx, "rule": "diagnostic_cell_object", "actual": type(row).__name__})
            actual_cell_ids.append(None)
            continue
        actual_cell_ids.append(row.get("diagnostic_cell_id"))
        missing = sorted(REQUIRED_CELL_KEYS - set(row))
        extra = sorted(set(row) - REQUIRED_CELL_KEYS)
        if missing or extra:
            findings.append({"row": row.get("diagnostic_cell_id", idx), "missing": missing, "extra": extra})
        if not isinstance(row.get("diagnostic_cell_id"), str) or not _CELL_ID.fullmatch(row["diagnostic_cell_id"]):
            findings.append({
                "row": row.get("diagnostic_cell_id", idx),
                "rule": "diagnostic_cell_id_format",
                "expected": "GPDR-000",
                "actual": row.get("diagnostic_cell_id"),
            })
        if not isinstance(row.get("task_blueprint_id"), str) or not _TASK_ID.fullmatch(row["task_blueprint_id"]):
            findings.append({
                "row": row.get("diagnostic_cell_id", idx),
                "rule": "task_blueprint_id_format",
                "expected": "GPBB-TASK-000",
                "actual": row.get("task_blueprint_id"),
            })
        if not isinstance(row.get("axis_id"), str) or not row.get("axis_id", "").strip():
            findings.append({"row": row.get("diagnostic_cell_id", idx), "rule": "axis_id_non_empty"})
        if not isinstance(row.get("benchmark_axis"), str) or not row.get("benchmark_axis", "").strip():
            findings.append({"row": row.get("diagnostic_cell_id", idx), "rule": "benchmark_axis_non_empty"})
        if row.get("status") != "blocked_pending_source_review":
            findings.append({
                "row": row.get("diagnostic_cell_id", idx),
                "rule": "status_blocked",
                "expected": "blocked_pending_source_review",
                "actual": row.get("status"),
            })
        if row.get("execution_mode") != "dry_run_plan_only":
            findings.append({
                "row": row.get("diagnostic_cell_id", idx),
                "rule": "execution_mode_dry_run_only",
                "expected": "dry_run_plan_only",
                "actual": row.get("execution_mode"),
            })
        before_call = row.get("required_before_model_call")
        if not isinstance(before_call, list) or not before_call:
            findings.append({
                "row": row.get("diagnostic_cell_id", idx),
                "rule": "required_before_model_call_non_empty",
                "actual": before_call,
            })
        else:
            missing_before_call = sorted(REQUIRED_BEFORE_MODEL_CALL_ITEMS - set(before_call))
            if missing_before_call:
                findings.append({
                    "row": row.get("diagnostic_cell_id", idx),
                    "rule": "required_before_model_call_core_items",
                    "missing": missing_before_call,
                })
        if row.get("required_run_gate_ids") != expected_run_gates:
            findings.append({
                "row": row.get("diagnostic_cell_id", idx),
                "rule": "required_run_gate_ids_exact",
                "expected": expected_run_gates,
                "actual": row.get("required_run_gate_ids"),
            })
        if row.get("required_model_response_fields") != expected_model_fields:
            findings.append({
                "row": row.get("diagnostic_cell_id", idx),
                "rule": "required_model_response_fields_exact",
                "expected": expected_model_fields,
                "actual": row.get("required_model_response_fields"),
            })
        if row.get("required_legal_claim_anchor_source_channel_ids") != expected_legal_anchor_source_channels:
            findings.append({
                "row": row.get("diagnostic_cell_id", idx),
                "rule": "required_legal_claim_anchor_source_channel_ids_exact",
                "expected": expected_legal_anchor_source_channels,
                "actual": row.get("required_legal_claim_anchor_source_channel_ids"),
            })
        if row.get("required_judge_output_fields") != expected_judge_fields:
            findings.append({
                "row": row.get("diagnostic_cell_id", idx),
                "rule": "required_judge_output_fields_exact",
                "expected": expected_judge_fields,
                "actual": row.get("required_judge_output_fields"),
            })
        if row.get("failure_modes_to_check") != expected_failures:
            findings.append({
                "row": row.get("diagnostic_cell_id", idx),
                "rule": "failure_modes_to_check_exact",
                "expected": expected_failures,
                "actual": row.get("failure_modes_to_check"),
            })
        if not isinstance(row.get("expected_artifact_policy"), str) or not row.get("expected_artifact_policy", "").strip():
            findings.append({
                "row": row.get("diagnostic_cell_id", idx),
                "rule": "expected_artifact_policy_non_empty",
                "actual": row.get("expected_artifact_policy"),
            })
        for key in READY_FLAG_KEYS:
            if row.get(key) is not False:
                findings.append({
                    "row": row.get("diagnostic_cell_id", idx),
                    "rule": key,
                    "expected": False,
                    "actual": row.get(key),
                })
    if actual_cell_ids != expected_cell_ids:
        findings.append({
            "rule": "diagnostic_cell_ids_contiguous",
            "expected": expected_cell_ids,
            "actual": actual_cell_ids,
        })
    return findings


def _summary_count_mismatches(doc: dict[str, Any]) -> list[dict[str, Any]]:
    summary = doc.get("summary") if isinstance(doc.get("summary"), dict) else {}
    rows = doc.get("diagnostic_cells") if isinstance(doc.get("diagnostic_cells"), list) else []
    row_dicts = [row for row in rows if isinstance(row, dict)]
    pairs = [
        ("consistency_ok", True),
        ("task_blueprint_count", len(rows)),
        ("diagnostic_cell_count", len(rows)),
        (
            "blocked_diagnostic_cells",
            sum(1 for row in row_dicts if row.get("status") == "blocked_pending_source_review"),
        ),
        ("run_gate_count", len(_expected_run_gate_ids())),
        ("failure_mode_count", len(eval_contract_builder.FAILURE_MODES)),
        ("core_failure_modes_per_cell", len(diagnostic_builder.CORE_FAILURE_IDS)),
        ("model_response_record_field_count", len(eval_contract_builder.MODEL_RESPONSE_RECORD_FIELDS)),
        ("judge_output_field_count", len(eval_contract_builder.JUDGE_OUTPUT_FIELDS)),
        (
            "legal_claim_anchor_source_channel_count",
            len(source_matrix_builder.legal_claim_anchor_source_channel_ids()),
        ),
        (
            "legal_claim_anchor_source_channel_ids",
            source_matrix_builder.legal_claim_anchor_source_channel_ids(),
        ),
    ]
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
    for idx, row in enumerate(doc.get("diagnostic_cells") or []):
        if not isinstance(row, dict):
            findings.append(f"diagnostic_cells[{idx}]")
            continue
        if row.get("status") != "blocked_pending_source_review":
            findings.append(f"diagnostic_cells[{idx}].status")
        if row.get("execution_mode") != "dry_run_plan_only":
            findings.append(f"diagnostic_cells[{idx}].execution_mode")
        for key in READY_FLAG_KEYS:
            if row.get(key) is not False:
                findings.append(f"diagnostic_cells[{idx}].{key}")
    return findings


def _current_reference(
    *,
    domain_id: str,
    config_path: pathlib.Path,
    registry_path: pathlib.Path,
    regulatory_catalog_path: pathlib.Path,
    component_dir: pathlib.Path,
) -> dict[str, Any]:
    return diagnostic_builder.build_diagnostic_run_plan(
        domain_id=domain_id,
        config_path=config_path,
        registry_path=registry_path,
        regulatory_catalog_path=regulatory_catalog_path,
        component_dir=component_dir,
    )


def _comparable_sections(doc: dict[str, Any]) -> dict[str, Any]:
    return {
        "summary": doc.get("summary"),
        "diagnostic_cells": doc.get("diagnostic_cells"),
    }


def validate_diagnostic_run_plan(
    doc: Any,
    *,
    plan_path: pathlib.Path | None = None,
    domain_id: str = DEFAULT_DOMAIN,
    config_path: pathlib.Path = project_plan_builder.CONFIG,
    registry_path: pathlib.Path = project_plan_builder.REGISTRY,
    regulatory_catalog_path: pathlib.Path = project_plan_builder.REGULATORY_CATALOG,
    component_dir: pathlib.Path = diagnostic_builder.OUT_DIR,
    compare_current_chain: bool = True,
) -> dict[str, Any]:
    if not isinstance(doc, dict):
        checks = [_check("diagnostic_run_plan_is_object", False, expected="object", actual=type(doc).__name__)]
        failed = _failed_ids(checks)
        return {
            "_meta": {
                "schema_version": "global_protections_diagnostic_run_plan_validation.v1",
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
    cell_drift = _diagnostic_cell_drift(doc)
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
            "diagnostic_cell_shape",
            not cell_drift,
            expected=[],
            actual=cell_drift,
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
        _check("diagnostic_plan_contains_no_disallowed_text", not disallowed, expected=[], actual=disallowed),
    ]
    if compare_current_chain:
        checks.append(
            _check(
                "diagnostic_run_plan_matches_current_chain",
                _comparable_sections(doc) == current_sections,
                expected=current_sections,
                actual=_comparable_sections(doc),
            )
        )
    failed = _failed_ids(checks)
    return {
        "_meta": {
            "schema_version": "global_protections_diagnostic_run_plan_validation.v1",
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
            "diagnostic_cell_count": summary.get("diagnostic_cell_count"),
            "blocked_diagnostic_cells": summary.get("blocked_diagnostic_cells"),
            "run_gate_count": summary.get("run_gate_count"),
            "failure_mode_count": summary.get("failure_mode_count"),
            "legal_claim_anchor_source_channel_count": summary.get(
                "legal_claim_anchor_source_channel_count"
            ),
            "legal_claim_anchor_source_channel_ids": summary.get(
                "legal_claim_anchor_source_channel_ids"
            ),
            "ready_for_task_instantiation": summary.get("ready_for_task_instantiation"),
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
        "# Global Protections Diagnostic Run Plan Validation",
        "",
        "This read-only report validates the saved diagnostic run plan before any model-run work is trusted.",
        "",
        "## Summary",
        "",
        "| Metric | Value |",
        "|---|---:|",
        f"| Valid | {str(bool(summary['valid'])).lower()} |",
        f"| Checks | {summary['check_count']} |",
        f"| Failed checks | {summary['failed_check_count']} |",
        f"| Diagnostic cells | {_md_cell(summary.get('diagnostic_cell_count'))} |",
        f"| Blocked diagnostic cells | {_md_cell(summary.get('blocked_diagnostic_cells'))} |",
        f"| Run gates | {_md_cell(summary.get('run_gate_count'))} |",
        f"| Failure modes | {_md_cell(summary.get('failure_mode_count'))} |",
        f"| Legal-claim anchor source channels | {_md_cell(summary.get('legal_claim_anchor_source_channel_count'))} |",
        f"| Ready for task instantiation | {str(bool(summary.get('ready_for_task_instantiation'))).lower()} |",
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
    ap.add_argument("--plan", type=pathlib.Path, default=DEFAULT_PLAN)
    ap.add_argument("--domain", default=DEFAULT_DOMAIN)
    ap.add_argument("--config", type=pathlib.Path, default=project_plan_builder.CONFIG)
    ap.add_argument("--registry", type=pathlib.Path, default=project_plan_builder.REGISTRY)
    ap.add_argument("--regulatory-catalog", type=pathlib.Path, default=project_plan_builder.REGULATORY_CATALOG)
    ap.add_argument("--component-dir", type=pathlib.Path, default=diagnostic_builder.OUT_DIR)
    ap.add_argument("--out", type=pathlib.Path, default=OUT)
    ap.add_argument("--markdown-out", type=pathlib.Path, default=MD_OUT)
    ap.add_argument("--no-current-chain", action="store_true", help="skip comparison to the current generated chain")
    ap.add_argument("--validate", action="store_true", help="print the validation summary only; write nothing")
    args = ap.parse_args(argv)

    doc = _load_json(args.plan)
    if doc is None:
        print(f"[global-protections-diagnostic-run-plan-validation] unreadable plan: {args.plan}")
        return 1
    report = validate_diagnostic_run_plan(
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
        "[global-protections-diagnostic-run-plan-validation] "
        f"valid={str(bool(summary['valid'])).lower()}; "
        f"failed={summary['failed_check_count']}/{summary['check_count']}; "
        f"ready_for_comparable_scoring={str(bool(summary['ready_for_comparable_scoring'])).lower()} -> {args.plan}"
    )
    return 0 if summary["valid"] else 1


if __name__ == "__main__":
    raise SystemExit(main())
