#!/usr/bin/env python3
"""Build a blocked diagnostic run plan for global protections.

The evaluation contract defines the future record and judging schema. This
command adds an operator-facing dry-run plan: one diagnostic cell per task
blueprint, the gates that block it today, and the failure checks that would be
applied after source review. It does not instantiate prompts, call models,
capture responses, grade outputs, verify law, or authorize comparable scoring.

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

import build_global_protections_benchmark_blueprint as blueprint_builder  # noqa: E402
import build_global_protections_eval_contract as eval_contract_builder  # noqa: E402
import build_global_protections_project_plan as project_plan_builder  # noqa: E402
import build_global_protections_readiness_bundle as readiness_builder  # noqa: E402

OUT_DIR = _ROOT / "reports" / "benchmark"
OUT = OUT_DIR / "global_protections_diagnostic_run_plan.json"
MD_OUT = OUT_DIR / "global_protections_diagnostic_run_plan.md"
DEFAULT_DOMAIN = readiness_builder.DEFAULT_DOMAIN

DISALLOWED_TERMS = [
    "Synthetic composite:",
    "prompt_family_sketches",
    "candidate_url",
    "source_url",
    "raw_text",
    "case_text",
    "prompt_text",
    "https://",
    "www.",
]
CORE_FAILURE_IDS = [
    "legal_authority_hallucination",
    "jurisdiction_scope_collapse",
    "coverage_scope_overgeneralization",
    "cross_border_responsibility_miss",
    "implementation_access_overclaim",
    "procedural_burden_overclaim",
    "international_anchor_substitution",
    "informal_source_overclaim",
    "authority_precedence_misread",
    "date_version_hallucination",
    "language_access_overclaim",
    "entity_identity_conflation",
    "remedy_forum_hallucination",
    "privacy_retaliation_leakage",
    "overconfident_non_abstention",
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


def _contains_disallowed_text(doc: dict[str, Any]) -> list[str]:
    encoded = json.dumps(doc, ensure_ascii=False)
    return [term for term in DISALLOWED_TERMS if term in encoded]


def _run_gate_ids(eval_contract_doc: dict[str, Any]) -> list[str]:
    return [
        str(gate.get("id"))
        for gate in eval_contract_doc.get("run_gates", [])
        if isinstance(gate, dict) and gate.get("id")
    ]


def _schema_fields(eval_contract_doc: dict[str, Any], key: str) -> list[str]:
    schema = eval_contract_doc.get(key) if isinstance(eval_contract_doc.get(key), dict) else {}
    fields = schema.get("fields") if isinstance(schema, dict) else []
    return [str(field) for field in fields if isinstance(field, str)]


def _diagnostic_cell(
    task: dict[str, Any],
    *,
    index: int,
    run_gate_ids: list[str],
    model_response_fields: list[str],
    judge_output_fields: list[str],
    legal_anchor_source_channel_ids: list[str],
    available_failure_ids: set[str],
) -> dict[str, Any]:
    failure_ids = [failure_id for failure_id in CORE_FAILURE_IDS if failure_id in available_failure_ids]
    return {
        "diagnostic_cell_id": f"GPDR-{index:03d}",
        "task_blueprint_id": task.get("blueprint_id"),
        "axis_id": task.get("axis_id"),
        "benchmark_axis": task.get("benchmark_axis"),
        "status": "blocked_pending_source_review",
        "execution_mode": "dry_run_plan_only",
        "required_before_model_call": [
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
            "deadlines, required documents, identity/access prerequisites, evidence burden, fees, translation/notarization, and filing-channel review basis",
            "privacy and retaliation screen",
            "expert review",
            "source-verified grounding layer",
        ],
        "required_run_gate_ids": list(run_gate_ids),
        "required_model_response_fields": list(model_response_fields),
        "required_legal_claim_anchor_source_channel_ids": list(legal_anchor_source_channel_ids),
        "required_judge_output_fields": list(judge_output_fields),
        "failure_modes_to_check": failure_ids,
        "expected_artifact_policy": (
            "store deterministic references and redacted findings only; do not store private cases "
            "or unreviewed legal text"
        ),
        "ready_for_task_instantiation": False,
        "ready_for_model_response_capture": False,
        "ready_for_judge_calibration": False,
        "ready_for_training_use": False,
        "ready_for_public_claims": False,
        "ready_for_worker_facing_use": False,
        "ready_for_comparable_scoring": False,
    }


def build_diagnostic_run_plan(
    *,
    blueprint_doc: dict[str, Any] | None = None,
    eval_contract_doc: dict[str, Any] | None = None,
    readiness_doc: dict[str, Any] | None = None,
    domain_id: str = DEFAULT_DOMAIN,
    config_path: pathlib.Path = project_plan_builder.CONFIG,
    registry_path: pathlib.Path = project_plan_builder.REGISTRY,
    regulatory_catalog_path: pathlib.Path = project_plan_builder.REGULATORY_CATALOG,
    component_dir: pathlib.Path | None = None,
) -> dict[str, Any]:
    """Return a dry-run diagnostic plan that executes nothing."""
    blueprint_doc = blueprint_doc or blueprint_builder.build_benchmark_blueprint(
        domain_id=domain_id,
        config_path=config_path,
        registry_path=registry_path,
        regulatory_catalog_path=regulatory_catalog_path,
        component_dir=component_dir,
    )
    if readiness_doc is None:
        chain = readiness_builder.build_readiness_chain(
            domain_id=domain_id,
            project_config_path=config_path,
            registry_path=registry_path,
            regulatory_catalog_path=regulatory_catalog_path,
            component_dir=component_dir,
        )
        readiness_doc = readiness_builder.build_readiness_bundle(
            chain=chain,
            domain_id=domain_id,
            project_config_path=config_path,
            registry_path=registry_path,
            regulatory_catalog_path=regulatory_catalog_path,
            component_dir=component_dir,
        )
    eval_contract_doc = eval_contract_doc or eval_contract_builder.build_eval_contract(
        blueprint_doc=blueprint_doc,
        readiness_doc=readiness_doc,
        domain_id=domain_id,
        config_path=config_path,
        registry_path=registry_path,
        regulatory_catalog_path=regulatory_catalog_path,
        component_dir=component_dir,
    )

    task_blueprints = [
        row for row in blueprint_doc.get("task_blueprints", []) if isinstance(row, dict)
    ]
    failure_ids = {
        str(row.get("id"))
        for row in eval_contract_doc.get("failure_modes", [])
        if isinstance(row, dict) and row.get("id")
    }
    gates = _run_gate_ids(eval_contract_doc)
    model_fields = _schema_fields(eval_contract_doc, "model_response_record_schema")
    judge_fields = _schema_fields(eval_contract_doc, "judge_output_schema")
    legal_anchor_source_channel_ids = list(
        eval_contract_doc["summary"]["legal_claim_anchor_source_channel_ids"]
    )
    diagnostic_cells = [
        _diagnostic_cell(
            task,
            index=index,
            run_gate_ids=gates,
            model_response_fields=model_fields,
            judge_output_fields=judge_fields,
            legal_anchor_source_channel_ids=legal_anchor_source_channel_ids,
            available_failure_ids=failure_ids,
        )
        for index, task in enumerate(task_blueprints, start=1)
    ]
    ready_flags = {
        "task_instantiation": any(row["ready_for_task_instantiation"] for row in diagnostic_cells),
        "model_response_capture": any(row["ready_for_model_response_capture"] for row in diagnostic_cells),
        "judge_calibration": any(row["ready_for_judge_calibration"] for row in diagnostic_cells),
        "training_use": any(row["ready_for_training_use"] for row in diagnostic_cells),
        "public_claims": any(row["ready_for_public_claims"] for row in diagnostic_cells),
        "worker_facing_use": any(row["ready_for_worker_facing_use"] for row in diagnostic_cells),
        "comparable_scoring": any(row["ready_for_comparable_scoring"] for row in diagnostic_cells),
    }
    blocked_cells = [
        row
        for row in diagnostic_cells
        if row["status"] == "blocked_pending_source_review"
    ]
    summary = {
        "consistency_ok": False,
        "task_blueprint_count": len(task_blueprints),
        "diagnostic_cell_count": len(diagnostic_cells),
        "blocked_diagnostic_cells": len(blocked_cells),
        "run_gate_count": len(gates),
        "failure_mode_count": len(failure_ids),
        "core_failure_modes_per_cell": len(CORE_FAILURE_IDS),
        "model_response_record_field_count": len(model_fields),
        "judge_output_field_count": len(judge_fields),
        "legal_claim_anchor_source_channel_count": eval_contract_doc["summary"][
            "legal_claim_anchor_source_channel_count"
        ],
        "legal_claim_anchor_source_channel_ids": legal_anchor_source_channel_ids,
        "ready_for_task_instantiation": ready_flags["task_instantiation"],
        "ready_for_model_response_capture": ready_flags["model_response_capture"],
        "ready_for_judge_calibration": ready_flags["judge_calibration"],
        "ready_for_training_use": ready_flags["training_use"],
        "ready_for_public_claims": ready_flags["public_claims"],
        "ready_for_worker_facing_use": ready_flags["worker_facing_use"],
        "ready_for_comparable_scoring": ready_flags["comparable_scoring"],
        "policy": (
            "This diagnostic run plan is a dry-run operator plan only. It does not instantiate "
            "prompts, call models, capture responses, grade outputs, train models, publish claims, "
            "enable worker-facing use, or authorize comparable scoring."
        ),
    }
    checks = [
        _check(
            "benchmark_blueprint_consistency_ok",
            blueprint_doc["summary"]["consistency_ok"] is True,
            expected=True,
            actual=blueprint_doc["summary"]["consistency_ok"],
        ),
        _check(
            "eval_contract_consistency_ok",
            eval_contract_doc["summary"]["consistency_ok"] is True,
            expected=True,
            actual=eval_contract_doc["summary"]["consistency_ok"],
        ),
        _check(
            "readiness_bundle_consistency_ok",
            readiness_doc["summary"]["consistency_ok"] is True,
            expected=True,
            actual=readiness_doc["summary"]["consistency_ok"],
        ),
        _check(
            "diagnostic_cells_cover_task_blueprints",
            len(diagnostic_cells) == blueprint_doc["summary"]["task_blueprint_count"],
            expected=blueprint_doc["summary"]["task_blueprint_count"],
            actual=len(diagnostic_cells),
        ),
        _check(
            "all_diagnostic_cells_blocked",
            len(blocked_cells) == len(diagnostic_cells),
            expected=len(diagnostic_cells),
            actual=len(blocked_cells),
        ),
        _check(
            "run_gates_match_eval_contract",
            len(gates) == eval_contract_doc["summary"]["run_gate_count"],
            expected=eval_contract_doc["summary"]["run_gate_count"],
            actual=len(gates),
        ),
        _check(
            "model_response_schema_available",
            {
                "reviewed_source_object_ids",
                "source_gap_marker_ids",
                "legal_claim_anchor_source_object_ids",
                "legal_claim_anchor_source_channel_ids",
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
            }.issubset(set(model_fields)),
            expected=[
                "reviewed_source_object_ids",
                "source_gap_marker_ids",
                "legal_claim_anchor_source_object_ids",
                "legal_claim_anchor_source_channel_ids",
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
            ],
            actual=model_fields,
        ),
        _check(
            "legal_claim_anchor_channels_match_eval_contract",
            summary["legal_claim_anchor_source_channel_count"]
            == eval_contract_doc["summary"]["legal_claim_anchor_source_channel_count"]
            and summary["legal_claim_anchor_source_channel_ids"]
            == eval_contract_doc["summary"]["legal_claim_anchor_source_channel_ids"]
            and all(
                row["required_legal_claim_anchor_source_channel_ids"]
                == eval_contract_doc["summary"]["legal_claim_anchor_source_channel_ids"]
                for row in diagnostic_cells
            ),
            expected={
                "legal_claim_anchor_source_channel_count": eval_contract_doc["summary"][
                    "legal_claim_anchor_source_channel_count"
                ],
                "legal_claim_anchor_source_channel_ids": eval_contract_doc["summary"][
                    "legal_claim_anchor_source_channel_ids"
                ],
            },
            actual={
                "legal_claim_anchor_source_channel_count": summary[
                    "legal_claim_anchor_source_channel_count"
                ],
                "legal_claim_anchor_source_channel_ids": summary[
                    "legal_claim_anchor_source_channel_ids"
                ],
            },
        ),
        _check(
            "judge_schema_available",
            {
                "abstention_findings",
                "invented_authority_findings",
                "temporal_validity_findings",
                "language_access_findings",
                "entity_resolution_findings",
                "authority_hierarchy_findings",
                "coverage_scope_findings",
                "jurisdiction_chain_findings",
                "jurisdiction_scope_findings",
                "implementation_access_findings",
                "procedural_burden_findings",
                "forum_competence_findings",
                "remedy_routing_findings",
            }.issubset(set(judge_fields)),
            expected=[
                "abstention_findings",
                "invented_authority_findings",
                "temporal_validity_findings",
                "language_access_findings",
                "entity_resolution_findings",
                "authority_hierarchy_findings",
                "coverage_scope_findings",
                "jurisdiction_chain_findings",
                "jurisdiction_scope_findings",
                "implementation_access_findings",
                "procedural_burden_findings",
                "forum_competence_findings",
                "remedy_routing_findings",
            ],
            actual=judge_fields,
        ),
        _check(
            "core_failure_modes_available",
            set(CORE_FAILURE_IDS).issubset(failure_ids),
            expected=CORE_FAILURE_IDS,
            actual=sorted(set(CORE_FAILURE_IDS) & failure_ids),
        ),
        _check(
            "all_public_and_scoring_flags_blocked",
            not any(ready_flags.values()),
            expected=False,
            actual=ready_flags,
        ),
    ]
    doc = {
        "_meta": {
            "schema_version": "global_protections_diagnostic_run_plan.v1",
            "project_config": _display_path(config_path),
            "registry_path": _display_path(registry_path),
            "regulatory_catalog_path": _display_path(regulatory_catalog_path),
            "domain": domain_id,
            "status": (
                "dry-run diagnostic plan only; not legal advice, not source verification, not "
                "model execution, not training data, and not comparable benchmark evidence"
            ),
        },
        "summary": summary,
        "diagnostic_cells": diagnostic_cells,
        "checks": checks,
    }
    disallowed = _contains_disallowed_text(doc)
    scan = project_plan_builder._scan_privacy(doc)
    checks.extend([
        _check("diagnostic_plan_contains_no_disallowed_text", not disallowed, expected=[], actual=disallowed),
        _check("privacy_scan_ok", scan.get("ok") is True, expected=True, actual=scan.get("ok")),
    ])
    doc["summary"]["consistency_ok"] = all(check["ok"] for check in checks)
    return doc


def _md_cell(value: Any) -> str:
    text = str(value if value is not None else "")
    return text.replace("|", "\\|").replace("\n", " ").strip()


def build_markdown_report(doc: dict[str, Any]) -> str:
    """Render a compact Markdown diagnostic run plan."""
    summary = doc["summary"]
    lines = [
        "# Global Protections Diagnostic Run Plan",
        "",
        (
            "This diagnostic run plan is a dry-run operator plan only. It is not legal advice, "
            "not source verification, not model execution, and not comparable benchmark evidence."
        ),
        "",
        "## Summary",
        "",
        "| Metric | Value |",
        "|---|---:|",
        f"| Consistency OK | {str(bool(summary['consistency_ok'])).lower()} |",
        f"| Diagnostic cells | {summary['diagnostic_cell_count']} |",
        f"| Blocked diagnostic cells | {summary['blocked_diagnostic_cells']} |",
        f"| Run gates | {summary['run_gate_count']} |",
        f"| Failure modes | {summary['failure_mode_count']} |",
        f"| Legal-claim anchor source channels | {summary['legal_claim_anchor_source_channel_count']} |",
        f"| Ready for model response capture | {str(bool(summary['ready_for_model_response_capture'])).lower()} |",
        f"| Ready for judge calibration | {str(bool(summary['ready_for_judge_calibration'])).lower()} |",
        f"| Ready for comparable scoring | {str(bool(summary['ready_for_comparable_scoring'])).lower()} |",
        "",
        "## Diagnostic Cells",
        "",
        "| Cell | Task blueprint | Axis | Status | Failure checks |",
        "|---|---|---|---|---:|",
    ]
    for row in doc["diagnostic_cells"]:
        lines.append(
            f"| `{_md_cell(row['diagnostic_cell_id'])}` "
            f"| `{_md_cell(row['task_blueprint_id'])}` "
            f"| {_md_cell(row['benchmark_axis'])} "
            f"| {_md_cell(row['status'])} "
            f"| {len(row['failure_modes_to_check'])} |"
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
    ap.add_argument("--domain", default=DEFAULT_DOMAIN)
    ap.add_argument("--config", type=pathlib.Path, default=project_plan_builder.CONFIG)
    ap.add_argument("--registry", type=pathlib.Path, default=project_plan_builder.REGISTRY)
    ap.add_argument("--regulatory-catalog", type=pathlib.Path, default=project_plan_builder.REGULATORY_CATALOG)
    ap.add_argument("--component-dir", type=pathlib.Path, default=OUT_DIR)
    ap.add_argument("--out", type=pathlib.Path, default=OUT)
    ap.add_argument("--md-out", type=pathlib.Path, default=MD_OUT)
    ap.add_argument("--no-md", action="store_true", help="write only JSON, not the Markdown plan")
    ap.add_argument("--validate", action="store_true", help="print the summary only; write nothing")
    args = ap.parse_args(argv)

    doc = build_diagnostic_run_plan(
        domain_id=args.domain,
        config_path=args.config,
        registry_path=args.registry,
        regulatory_catalog_path=args.regulatory_catalog,
        component_dir=args.component_dir,
    )
    summary = doc["summary"]
    if args.validate:
        print(json.dumps({"summary": summary}, indent=2, ensure_ascii=False))
        return 0 if summary["consistency_ok"] else 1
    if not summary["consistency_ok"]:
        print(json.dumps({"summary": summary, "checks": doc["checks"]}, indent=2, ensure_ascii=False))
        print("[global-protections-diagnostic-run-plan] plan is inconsistent; refusing to write")
        return 1

    args.out.parent.mkdir(parents=True, exist_ok=True)
    args.out.write_text(json.dumps(doc, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
    md_path = None
    if not args.no_md:
        md_path = args.md_out
        md_path.parent.mkdir(parents=True, exist_ok=True)
        md_path.write_text(build_markdown_report(doc) + "\n", encoding="utf-8")
    print(
        "[global-protections-diagnostic-run-plan] "
        f"consistency_ok={str(bool(summary['consistency_ok'])).lower()}; "
        f"{summary['diagnostic_cell_count']} diagnostic cells; "
        f"{summary['blocked_diagnostic_cells']} blocked; "
        f"ready_for_comparable_scoring={str(bool(summary['ready_for_comparable_scoring'])).lower()} -> {args.out}"
        + (f"; report {md_path}" if md_path else "")
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
