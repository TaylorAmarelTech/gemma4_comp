#!/usr/bin/env python3
"""Validate a saved global-protections transition gate.

The transition gate is the go/no-go artifact for moving from source review to
manifest promotion, prompt instantiation, model capture, judge output,
calibration, training use, public claims, comparable scoring, and worker-facing
use. This validator keeps a saved gate blocked, privacy-safe, and aligned with
the current deterministic transition chain.

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
import build_global_protections_source_channel_matrix as source_matrix_builder  # noqa: E402
import build_global_protections_transition_gate as transition_builder  # noqa: E402

DEFAULT_GATE = transition_builder.OUT
DEFAULT_DOMAIN = transition_builder.DEFAULT_DOMAIN
OUT = transition_builder.OUT_DIR / "global_protections_transition_gate_validation.json"
MD_OUT = transition_builder.OUT_DIR / "global_protections_transition_gate_validation.md"

REQUIRED_TOP_LEVEL = frozenset({"_meta", "summary", "transitions", "checks"})
ALLOWED_TOP_LEVEL = REQUIRED_TOP_LEVEL
REQUIRED_CHECK_IDS = frozenset({
    "source_review_packet_consistency_ok",
    "benchmark_blueprint_consistency_ok",
    "eval_contract_consistency_ok",
    "diagnostic_run_plan_consistency_ok",
    "judge_calibration_plan_consistency_ok",
    "all_transitions_blocked",
    "source_grounding_transitions_present",
    "temporal_validity_transitions_present",
    "language_access_transitions_present",
    "entity_resolution_transitions_present",
    "remedy_forum_transitions_present",
    "authority_hierarchy_transitions_present",
    "coverage_scope_transitions_present",
    "jurisdiction_chain_transitions_present",
    "implementation_access_transitions_present",
    "procedural_burden_transitions_present",
    "source_rows_still_not_started",
    "calibration_cases_still_blocked",
    "legal_claim_anchor_channels_match_eval_diagnostic_and_calibration",
    "all_public_and_scoring_flags_blocked",
    "transition_gate_contains_no_disallowed_text",
    "privacy_scan_ok",
})
READY_FLAG_KEYS = (
    "ready_for_manifest_promotion",
    "ready_for_prompt_generation",
    "ready_for_task_instantiation",
    "ready_for_model_response_capture",
    "ready_for_judge_output",
    "ready_for_judge_calibration",
    "ready_for_training_use",
    "ready_for_public_claims",
    "ready_for_worker_facing_use",
    "ready_for_comparable_scoring",
)
GATE_FLAG_KEYS = (
    "source_grounding_gate",
    "temporal_validity_gate",
    "language_access_gate",
    "entity_resolution_gate",
    "remedy_forum_gate",
    "authority_hierarchy_gate",
    "coverage_scope_gate",
    "jurisdiction_chain_gate",
    "implementation_access_gate",
    "procedural_burden_gate",
)
REQUIRED_TRANSITION_KEYS = frozenset({
    "transition_id",
    "transition_key",
    "from_state",
    "to_state",
    "status",
    "blocked_by",
    "required_evidence",
    "required_legal_claim_anchor_source_channel_ids",
    *GATE_FLAG_KEYS,
    *READY_FLAG_KEYS,
})
EXPECTED_TRANSITION_KEYS = tuple(defn["id"] for defn in transition_builder.TRANSITION_DEFINITIONS)
DISALLOWED_TERMS = transition_builder.DISALLOWED_TERMS
_TRANSITION_ID = re.compile(r"^GPTG-\d{3}$")


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


def _summary_count_mismatches(doc: dict[str, Any]) -> list[dict[str, Any]]:
    summary = doc.get("summary") if isinstance(doc.get("summary"), dict) else {}
    rows = doc.get("transitions") if isinstance(doc.get("transitions"), list) else []
    row_dicts = [row for row in rows if isinstance(row, dict)]
    pairs = [
        ("transition_count", len(rows)),
        ("blocked_transition_count", sum(1 for row in row_dicts if row.get("status") == "blocked")),
        (
            "source_grounding_transition_count",
            sum(1 for row in row_dicts if row.get("source_grounding_gate") is True),
        ),
        (
            "temporal_validity_transition_count",
            sum(1 for row in row_dicts if row.get("temporal_validity_gate") is True),
        ),
        (
            "language_access_transition_count",
            sum(1 for row in row_dicts if row.get("language_access_gate") is True),
        ),
        (
            "entity_resolution_transition_count",
            sum(1 for row in row_dicts if row.get("entity_resolution_gate") is True),
        ),
        (
            "remedy_forum_transition_count",
            sum(1 for row in row_dicts if row.get("remedy_forum_gate") is True),
        ),
        (
            "authority_hierarchy_transition_count",
            sum(1 for row in row_dicts if row.get("authority_hierarchy_gate") is True),
        ),
        (
            "coverage_scope_transition_count",
            sum(1 for row in row_dicts if row.get("coverage_scope_gate") is True),
        ),
        (
            "jurisdiction_chain_transition_count",
            sum(1 for row in row_dicts if row.get("jurisdiction_chain_gate") is True),
        ),
        (
            "implementation_access_transition_count",
            sum(1 for row in row_dicts if row.get("implementation_access_gate") is True),
        ),
        (
            "procedural_burden_transition_count",
            sum(1 for row in row_dicts if row.get("procedural_burden_gate") is True),
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
            "transitions_preserving_legal_anchor_source_channels",
            sum(
                1
                for row in row_dicts
                if row.get("required_legal_claim_anchor_source_channel_ids")
                == source_matrix_builder.legal_claim_anchor_source_channel_ids()
            ),
        ),
    ]
    for key in READY_FLAG_KEYS:
        pairs.append((key, any(row.get(key) is True for row in row_dicts)))
    return [
        {"summary_key": key, "expected": expected, "actual": summary.get(key)}
        for key, expected in pairs
        if summary.get(key) != expected
    ]


def _transition_shape_drift(doc: dict[str, Any]) -> list[dict[str, Any]]:
    findings: list[dict[str, Any]] = []
    rows = doc.get("transitions") if isinstance(doc.get("transitions"), list) else []
    expected_ids = [f"GPTG-{idx:03d}" for idx in range(1, len(rows) + 1)]
    actual_ids: list[Any] = []
    expected_legal_anchor_source_channels = (
        source_matrix_builder.legal_claim_anchor_source_channel_ids()
    )
    for idx, row in enumerate(rows):
        if not isinstance(row, dict):
            findings.append({"row": idx, "rule": "transition_row_object", "actual": type(row).__name__})
            actual_ids.append(None)
            continue
        actual_ids.append(row.get("transition_id"))
        missing = sorted(REQUIRED_TRANSITION_KEYS - set(row))
        extra = sorted(set(row) - REQUIRED_TRANSITION_KEYS)
        if missing or extra:
            findings.append({
                "row": row.get("transition_id", idx),
                "missing": missing,
                "extra": extra,
            })
        if not isinstance(row.get("transition_id"), str) or not _TRANSITION_ID.fullmatch(row["transition_id"]):
            findings.append({
                "row": row.get("transition_id", idx),
                "rule": "transition_id_format",
                "expected": "GPTG-000",
                "actual": row.get("transition_id"),
            })
        for key in ("transition_key", "from_state", "to_state", "status"):
            if not isinstance(row.get(key), str) or not row.get(key, "").strip():
                findings.append({
                    "row": row.get("transition_id", idx),
                    "rule": f"{key}_non_empty_string",
                    "expected": "non-empty string",
                    "actual": row.get(key),
                })
        if row.get("status") != "blocked":
            findings.append({
                "row": row.get("transition_id", idx),
                "rule": "status_blocked",
                "expected": "blocked",
                "actual": row.get("status"),
            })
        for key in (*GATE_FLAG_KEYS, *READY_FLAG_KEYS):
            if not isinstance(row.get(key), bool):
                findings.append({
                    "row": row.get("transition_id", idx),
                    "rule": f"{key}_bool",
                    "expected": "bool",
                    "actual": row.get(key),
                })
        if not isinstance(row.get("blocked_by"), list) or not row.get("blocked_by"):
            findings.append({
                "row": row.get("transition_id", idx),
                "rule": "blocked_by_non_empty",
                "actual": row.get("blocked_by"),
            })
        elif not all(isinstance(item, str) and item.strip() for item in row["blocked_by"]):
            findings.append({
                "row": row.get("transition_id", idx),
                "rule": "blocked_by_items_non_empty_strings",
                "expected": "non-empty string list",
                "actual": row.get("blocked_by"),
            })
        if not isinstance(row.get("required_evidence"), list) or not row.get("required_evidence"):
            findings.append({
                "row": row.get("transition_id", idx),
                "rule": "required_evidence_non_empty",
                "actual": row.get("required_evidence"),
            })
        elif not all(isinstance(item, str) and item.strip() for item in row["required_evidence"]):
            findings.append({
                "row": row.get("transition_id", idx),
                "rule": "required_evidence_items_non_empty_strings",
                "expected": "non-empty string list",
                "actual": row.get("required_evidence"),
            })
        if not isinstance(row.get("required_legal_claim_anchor_source_channel_ids"), list):
            findings.append({
                "row": row.get("transition_id", idx),
                "rule": "required_legal_claim_anchor_source_channel_ids_list",
                "expected": expected_legal_anchor_source_channels,
                "actual": row.get("required_legal_claim_anchor_source_channel_ids"),
            })
        elif not all(
            isinstance(item, str) and item.strip()
            for item in row["required_legal_claim_anchor_source_channel_ids"]
        ):
            findings.append({
                "row": row.get("transition_id", idx),
                "rule": "required_legal_claim_anchor_source_channel_ids_items_non_empty_strings",
                "expected": "non-empty string list",
                "actual": row.get("required_legal_claim_anchor_source_channel_ids"),
            })
        if (
            row.get("required_legal_claim_anchor_source_channel_ids")
            != expected_legal_anchor_source_channels
        ):
            findings.append({
                "row": row.get("transition_id", idx),
                "rule": "required_legal_claim_anchor_source_channel_ids_exact",
                "expected": expected_legal_anchor_source_channels,
                "actual": row.get("required_legal_claim_anchor_source_channel_ids"),
            })
    if actual_ids != expected_ids:
        findings.append({
            "rule": "transition_ids_contiguous",
            "expected": expected_ids,
            "actual": actual_ids,
        })
    return findings


def _transition_key_drift(doc: dict[str, Any]) -> dict[str, Any]:
    rows = doc.get("transitions") if isinstance(doc.get("transitions"), list) else []
    actual_keys = [
        row.get("transition_key")
        for row in rows
        if isinstance(row, dict)
    ]
    counts = Counter(actual_keys)
    duplicate_keys = [key for key, count in counts.items() if count > 1]
    return {
        "expected_keys": list(EXPECTED_TRANSITION_KEYS),
        "actual_keys": actual_keys,
        "missing_keys": sorted(set(EXPECTED_TRANSITION_KEYS) - set(actual_keys)),
        "extra_keys": sorted(set(actual_keys) - set(EXPECTED_TRANSITION_KEYS)),
        "duplicate_keys": sorted(duplicate_keys),
    }


def _readiness_drift(doc: dict[str, Any]) -> list[str]:
    summary = doc.get("summary") if isinstance(doc.get("summary"), dict) else {}
    findings = [f"summary.{key}" for key in READY_FLAG_KEYS if summary.get(key) is not False]
    rows = doc.get("transitions") if isinstance(doc.get("transitions"), list) else []
    for idx, row in enumerate(rows):
        if not isinstance(row, dict):
            findings.append(f"transitions[{idx}]")
            continue
        if row.get("status") != "blocked":
            findings.append(f"transitions[{idx}].status")
        for key in READY_FLAG_KEYS:
            if row.get(key) is not False:
                findings.append(f"transitions[{idx}].{key}")
    return findings


def _current_reference(
    *,
    domain_id: str,
    config_path: pathlib.Path,
    registry_path: pathlib.Path,
    regulatory_catalog_path: pathlib.Path,
    component_dir: pathlib.Path,
) -> dict[str, Any]:
    return transition_builder.build_transition_gate(
        domain_id=domain_id,
        config_path=config_path,
        registry_path=registry_path,
        regulatory_catalog_path=regulatory_catalog_path,
        component_dir=component_dir,
    )


def _comparable_sections(doc: dict[str, Any]) -> dict[str, Any]:
    return {
        "summary": doc.get("summary"),
        "transitions": doc.get("transitions"),
    }


def validate_transition_gate(
    doc: Any,
    *,
    gate_path: pathlib.Path | None = None,
    domain_id: str = DEFAULT_DOMAIN,
    config_path: pathlib.Path = project_plan_builder.CONFIG,
    registry_path: pathlib.Path = project_plan_builder.REGISTRY,
    regulatory_catalog_path: pathlib.Path = project_plan_builder.REGULATORY_CATALOG,
    component_dir: pathlib.Path = transition_builder.OUT_DIR,
    compare_current_chain: bool = True,
) -> dict[str, Any]:
    if not isinstance(doc, dict):
        checks = [_check("gate_is_object", False, expected="object", actual=type(doc).__name__)]
        failed = _failed_ids(checks)
        return {
            "_meta": {
                "schema_version": "global_protections_transition_gate_validation.v1",
                "source_gate_path": _display_path(gate_path) if gate_path else "n/a",
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
    transition_keys = _transition_key_drift(doc)
    transition_shape_drift = _transition_shape_drift(doc)
    summary_count_mismatches = _summary_count_mismatches(doc)
    readiness_drift = _readiness_drift(doc)
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
            "transition_row_shape",
            not transition_shape_drift,
            expected=[],
            actual=transition_shape_drift,
        ),
        _check(
            "transition_keys_match_contract",
            not transition_keys["missing_keys"]
            and not transition_keys["extra_keys"]
            and not transition_keys["duplicate_keys"]
            and tuple(transition_keys["actual_keys"]) == EXPECTED_TRANSITION_KEYS,
            expected=list(EXPECTED_TRANSITION_KEYS),
            actual=transition_keys,
        ),
        _check(
            "summary_counts_match_transitions",
            not summary_count_mismatches,
            expected=[],
            actual=summary_count_mismatches,
        ),
        _check(
            "embedded_checks_all_ok",
            not embedded["failed"] and not embedded["missing_required"],
            expected={"failed": [], "missing_required": []},
            actual=embedded,
        ),
        _check(
            "all_transitions_remain_blocked",
            not readiness_drift,
            expected=[],
            actual=readiness_drift,
        ),
        _check(
            "privacy_scan_ok",
            privacy_scan.get("ok") is True,
            expected=True,
            actual=privacy_scan.get("counts"),
        ),
        _check(
            "gate_contains_no_disallowed_text",
            not disallowed,
            expected=[],
            actual=disallowed,
        ),
    ]
    if compare_current_chain:
        checks.append(
            _check(
                "transition_gate_matches_current_chain",
                _comparable_sections(doc) == current_sections,
                expected=current_sections,
                actual=_comparable_sections(doc),
            )
        )
    failed = _failed_ids(checks)
    return {
        "_meta": {
            "schema_version": "global_protections_transition_gate_validation.v1",
            "source_gate_path": _display_path(gate_path) if gate_path else "n/a",
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
            "transition_count": summary.get("transition_count"),
            "blocked_transition_count": summary.get("blocked_transition_count"),
            "source_grounding_transition_count": summary.get("source_grounding_transition_count"),
            "temporal_validity_transition_count": summary.get("temporal_validity_transition_count"),
            "language_access_transition_count": summary.get("language_access_transition_count"),
            "entity_resolution_transition_count": summary.get("entity_resolution_transition_count"),
            "remedy_forum_transition_count": summary.get("remedy_forum_transition_count"),
            "authority_hierarchy_transition_count": summary.get("authority_hierarchy_transition_count"),
            "coverage_scope_transition_count": summary.get("coverage_scope_transition_count"),
            "jurisdiction_chain_transition_count": summary.get("jurisdiction_chain_transition_count"),
            "implementation_access_transition_count": summary.get("implementation_access_transition_count"),
            "procedural_burden_transition_count": summary.get("procedural_burden_transition_count"),
            "legal_claim_anchor_source_channel_count": summary.get(
                "legal_claim_anchor_source_channel_count"
            ),
            "legal_claim_anchor_source_channel_ids": summary.get(
                "legal_claim_anchor_source_channel_ids"
            ),
            "transitions_preserving_legal_anchor_source_channels": summary.get(
                "transitions_preserving_legal_anchor_source_channels"
            ),
            "ready_for_model_response_capture": summary.get("ready_for_model_response_capture"),
            "ready_for_judge_output": summary.get("ready_for_judge_output"),
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
        "# Global Protections Transition Gate Validation",
        "",
        "This read-only report validates the saved transition gate before any blocked transition is trusted.",
        "",
        "## Summary",
        "",
        "| Metric | Value |",
        "|---|---:|",
        f"| Valid | {str(bool(summary['valid'])).lower()} |",
        f"| Checks | {summary['check_count']} |",
        f"| Failed checks | {summary['failed_check_count']} |",
        f"| Transitions | {_md_cell(summary.get('transition_count'))} |",
        f"| Blocked transitions | {_md_cell(summary.get('blocked_transition_count'))} |",
        f"| Source-grounding transitions | {_md_cell(summary.get('source_grounding_transition_count'))} |",
        f"| Temporal-validity transitions | {_md_cell(summary.get('temporal_validity_transition_count'))} |",
        f"| Language-access transitions | {_md_cell(summary.get('language_access_transition_count'))} |",
        f"| Entity-resolution transitions | {_md_cell(summary.get('entity_resolution_transition_count'))} |",
        f"| Remedy/forum transitions | {_md_cell(summary.get('remedy_forum_transition_count'))} |",
        f"| Authority-hierarchy transitions | {_md_cell(summary.get('authority_hierarchy_transition_count'))} |",
        f"| Coverage-scope transitions | {_md_cell(summary.get('coverage_scope_transition_count'))} |",
        f"| Jurisdiction-chain transitions | {_md_cell(summary.get('jurisdiction_chain_transition_count'))} |",
        f"| Implementation-access transitions | {_md_cell(summary.get('implementation_access_transition_count'))} |",
        f"| Procedural-burden transitions | {_md_cell(summary.get('procedural_burden_transition_count'))} |",
        f"| Legal-claim anchor source channels | {_md_cell(summary.get('legal_claim_anchor_source_channel_count'))} |",
        (
            "| Transitions preserving legal-anchor source channels "
            f"| {_md_cell(summary.get('transitions_preserving_legal_anchor_source_channels'))} |"
        ),
        f"| Ready for model response capture | {str(bool(summary.get('ready_for_model_response_capture'))).lower()} |",
        f"| Ready for judge output | {str(bool(summary.get('ready_for_judge_output'))).lower()} |",
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
    ap.add_argument("--gate", type=pathlib.Path, default=DEFAULT_GATE)
    ap.add_argument("--domain", default=DEFAULT_DOMAIN)
    ap.add_argument("--config", type=pathlib.Path, default=project_plan_builder.CONFIG)
    ap.add_argument("--registry", type=pathlib.Path, default=project_plan_builder.REGISTRY)
    ap.add_argument("--regulatory-catalog", type=pathlib.Path, default=project_plan_builder.REGULATORY_CATALOG)
    ap.add_argument("--component-dir", type=pathlib.Path, default=transition_builder.OUT_DIR)
    ap.add_argument("--out", type=pathlib.Path, default=OUT)
    ap.add_argument("--markdown-out", type=pathlib.Path, default=MD_OUT)
    ap.add_argument("--no-current-chain", action="store_true", help="skip comparison to the current generated chain")
    ap.add_argument("--validate", action="store_true", help="print the validation summary only; write nothing")
    args = ap.parse_args(argv)

    doc = _load_json(args.gate)
    if doc is None:
        print(f"[global-protections-transition-gate-validation] unreadable gate: {args.gate}")
        return 1
    report = validate_transition_gate(
        doc,
        gate_path=args.gate,
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
        "[global-protections-transition-gate-validation] "
        f"valid={str(bool(summary['valid'])).lower()}; "
        f"failed={summary['failed_check_count']}/{summary['check_count']}; "
        f"ready_for_comparable_scoring={str(bool(summary['ready_for_comparable_scoring'])).lower()} -> {args.gate}"
    )
    return 0 if summary["valid"] else 1


if __name__ == "__main__":
    raise SystemExit(main())
