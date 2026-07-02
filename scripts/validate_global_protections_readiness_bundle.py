#!/usr/bin/env python3
"""Validate a saved global-protections readiness bundle.

The readiness bundle composes the sister-project charter, worker-protections
curation bundle, and regulatory curation bundle. This validator checks a saved
JSON artifact before it is used as a handoff: compact top-level shape,
component-summary shape, summary count integrity, blocked readiness flags,
embedded builder checks, artifact-path hygiene, privacy/disallowed text, and
optional drift against the current deterministic readiness chain.

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

import build_global_protections_project_plan as project_plan_builder  # noqa: E402
import build_global_protections_readiness_bundle as readiness_builder  # noqa: E402
import build_global_protections_source_channel_matrix as source_matrix_builder  # noqa: E402

DEFAULT_BUNDLE = readiness_builder.OUT
DEFAULT_DOMAIN = readiness_builder.DEFAULT_DOMAIN
OUT = readiness_builder.OUT_DIR / "global_protections_readiness_bundle_validation.json"
MD_OUT = readiness_builder.OUT_DIR / "global_protections_readiness_bundle_validation.md"

REQUIRED_TOP_LEVEL = frozenset({
    "_meta",
    "summary",
    "component_summaries",
    "checks",
    "artifact_paths",
})
ALLOWED_TOP_LEVEL = REQUIRED_TOP_LEVEL
REQUIRED_COMPONENTS = frozenset({
    "project_plan",
    "domain_curation_bundle",
    "regulatory_curation_bundle",
})
REQUIRED_COMPONENT_KEYS = {
    "project_plan": frozenset({
        "safe_for_project_planning",
        "registered_seed_domain_count",
        "regulatory_candidates_found_count",
        "ready_for_comparable_scoring",
    }),
    "domain_curation_bundle": frozenset({
        "consistency_ok",
        "prompt_count",
        "prompts_blocked_for_comparable_run",
        "verified_local_law_rows",
        "source_object_tasks",
        "scope_refinement_tasks",
        "ready_for_comparable_run",
    }),
    "regulatory_curation_bundle": frozenset({
        "consistency_ok",
        "pattern_count",
        "candidate_count",
        "validation_accepted_domain_seed_proposals",
        "ready_for_prompt_generation",
        "ready_for_comparable_scoring",
    }),
}
REQUIRED_CHECK_IDS = frozenset({
    "project_plan_safe",
    "project_links_active_seed_domain",
    "project_catalog_count_matches_regulatory_bundle",
    "project_candidate_links_match_catalog_count",
    "domain_curation_consistency_ok",
    "domain_comparable_run_blocked",
    "domain_local_law_gap_blocks_scoring",
    "regulatory_curation_consistency_ok",
    "regulatory_prompt_generation_blocked",
    "regulatory_comparable_scoring_blocked",
    "training_public_worker_and_scoring_blocked",
    "legal_claim_anchor_source_channels_match_source_matrix",
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
})
READY_FLAG_KEYS = (
    "ready_for_prompt_generation",
    "ready_for_training_use",
    "ready_for_public_claims",
    "ready_for_worker_facing_use",
    "ready_for_comparable_scoring",
)
RAW_PAYLOAD_KEYS = frozenset({
    "_domain_chain",
    "_regulatory_chain",
    "source_object_queue",
    "source_review_items",
    "source_review_packet",
    "regulatory_candidate_intake_items",
    "validated_rows",
    "proposed_manifest_rows",
    "task_blueprints",
    "prompt_family_sketches",
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
    "unredacted_response",
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


def _component_shape_drift(doc: dict[str, Any]) -> list[dict[str, Any]]:
    components = doc.get("component_summaries")
    if not isinstance(components, dict):
        return [{"rule": "component_summaries_object", "actual": type(components).__name__}]
    findings: list[dict[str, Any]] = []
    missing_components = sorted(REQUIRED_COMPONENTS - set(components))
    extra_components = sorted(set(components) - REQUIRED_COMPONENTS)
    if missing_components or extra_components:
        findings.append({
            "rule": "component_keys",
            "missing": missing_components,
            "extra": extra_components,
        })
    for component, required_keys in REQUIRED_COMPONENT_KEYS.items():
        row = components.get(component)
        if not isinstance(row, dict):
            findings.append({
                "component": component,
                "rule": "component_summary_object",
                "actual": type(row).__name__,
            })
            continue
        missing = sorted(required_keys - set(row))
        extra = sorted(set(row) - required_keys)
        if missing or extra:
            findings.append({"component": component, "missing": missing, "extra": extra})
    return findings


def _summary_count_mismatches(doc: dict[str, Any]) -> list[dict[str, Any]]:
    summary = doc.get("summary") if isinstance(doc.get("summary"), dict) else {}
    components = doc.get("component_summaries") if isinstance(doc.get("component_summaries"), dict) else {}
    project = components.get("project_plan") if isinstance(components.get("project_plan"), dict) else {}
    domain = (
        components.get("domain_curation_bundle")
        if isinstance(components.get("domain_curation_bundle"), dict)
        else {}
    )
    regulatory = (
        components.get("regulatory_curation_bundle")
        if isinstance(components.get("regulatory_curation_bundle"), dict)
        else {}
    )
    pairs = [
        ("consistency_ok", True),
        ("safe_for_project_planning", True),
        ("registered_seed_domain_count", project.get("registered_seed_domain_count")),
        ("regulatory_pattern_count", regulatory.get("pattern_count")),
        ("regulatory_candidate_count", regulatory.get("candidate_count")),
        ("worker_prompt_count", domain.get("prompt_count")),
        ("worker_prompts_blocked_for_comparable_run", domain.get("prompts_blocked_for_comparable_run")),
        ("worker_verified_local_law_rows", domain.get("verified_local_law_rows")),
        ("worker_source_object_tasks", domain.get("source_object_tasks")),
        ("worker_scope_refinement_tasks", domain.get("scope_refinement_tasks")),
        ("regulatory_seed_scaffold_operations", 0),
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
    components = doc.get("component_summaries") if isinstance(doc.get("component_summaries"), dict) else {}
    findings = [f"summary.{key}" for key in READY_FLAG_KEYS if summary.get(key) is not False]
    project = components.get("project_plan") if isinstance(components.get("project_plan"), dict) else {}
    domain = (
        components.get("domain_curation_bundle")
        if isinstance(components.get("domain_curation_bundle"), dict)
        else {}
    )
    regulatory = (
        components.get("regulatory_curation_bundle")
        if isinstance(components.get("regulatory_curation_bundle"), dict)
        else {}
    )
    if project.get("safe_for_project_planning") is not True:
        findings.append("component_summaries.project_plan.safe_for_project_planning")
    if project.get("ready_for_comparable_scoring") is not False:
        findings.append("component_summaries.project_plan.ready_for_comparable_scoring")
    if domain.get("ready_for_comparable_run") is not False:
        findings.append("component_summaries.domain_curation_bundle.ready_for_comparable_run")
    if regulatory.get("ready_for_prompt_generation") is not False:
        findings.append("component_summaries.regulatory_curation_bundle.ready_for_prompt_generation")
    if regulatory.get("ready_for_comparable_scoring") is not False:
        findings.append("component_summaries.regulatory_curation_bundle.ready_for_comparable_scoring")
    if domain.get("verified_local_law_rows") != 0:
        findings.append("component_summaries.domain_curation_bundle.verified_local_law_rows")
    if domain.get("prompts_blocked_for_comparable_run") != domain.get("prompt_count"):
        findings.append("component_summaries.domain_curation_bundle.prompts_blocked_for_comparable_run")
    if regulatory.get("validation_accepted_domain_seed_proposals") != 0:
        findings.append("component_summaries.regulatory_curation_bundle.validation_accepted_domain_seed_proposals")
    return findings


def _legal_anchor_channel_drift(doc: dict[str, Any]) -> list[dict[str, Any]]:
    summary = doc.get("summary") if isinstance(doc.get("summary"), dict) else {}
    expected_ids = source_matrix_builder.legal_claim_anchor_source_channel_ids()
    pairs = [
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
    ]
    return [
        {"rule": rule, "expected": expected, "actual": actual}
        for rule, expected, actual in pairs
        if actual != expected
    ]


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


def _current_reference(
    *,
    domain_id: str,
    project_config_path: pathlib.Path,
    registry_path: pathlib.Path,
    regulatory_catalog_path: pathlib.Path,
    component_dir: pathlib.Path,
) -> dict[str, Any]:
    return readiness_builder.build_readiness_bundle(
        domain_id=domain_id,
        project_config_path=project_config_path,
        registry_path=registry_path,
        regulatory_catalog_path=regulatory_catalog_path,
        component_dir=component_dir,
    )


def _comparable_sections(doc: dict[str, Any]) -> dict[str, Any]:
    return {
        "summary": doc.get("summary"),
        "component_summaries": doc.get("component_summaries"),
        "checks": doc.get("checks"),
    }


def validate_readiness_bundle(
    doc: Any,
    *,
    bundle_path: pathlib.Path | None = None,
    domain_id: str = DEFAULT_DOMAIN,
    project_config_path: pathlib.Path = project_plan_builder.CONFIG,
    registry_path: pathlib.Path = project_plan_builder.REGISTRY,
    regulatory_catalog_path: pathlib.Path = project_plan_builder.REGULATORY_CATALOG,
    component_dir: pathlib.Path = readiness_builder.OUT_DIR,
    compare_current_chain: bool = True,
) -> dict[str, Any]:
    if not isinstance(doc, dict):
        checks = [_check("readiness_bundle_is_object", False, expected="object", actual=type(doc).__name__)]
        failed = _failed_ids(checks)
        return {
            "_meta": {
                "schema_version": "global_protections_readiness_bundle_validation.v1",
                "source_bundle_path": _display_path(bundle_path) if bundle_path else "n/a",
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
    component_drift = _component_shape_drift(doc)
    summary_mismatches = _summary_count_mismatches(doc)
    readiness_drift = _readiness_drift(doc)
    legal_anchor_drift = _legal_anchor_channel_drift(doc)
    embedded = _embedded_check_drift(doc.get("checks"))
    unsafe_paths = _unsafe_artifact_paths(doc.get("artifact_paths"))
    raw_keys = _raw_payload_keys(doc)
    encoded = json.dumps(doc, ensure_ascii=False)
    disallowed = [term for term in DISALLOWED_TERMS if term in encoded]
    privacy_scan = project_plan_builder._scan_privacy(_redacted_privacy_view(doc))
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
        _check("component_summary_shape", not component_drift, expected=[], actual=component_drift),
        _check("summary_counts_match_components", not summary_mismatches, expected=[], actual=summary_mismatches),
        _check(
            "embedded_checks_all_ok",
            not embedded["failed"] and not embedded["missing_required"],
            expected={"failed": [], "missing_required": []},
            actual=embedded,
        ),
        _check(
            "legal_claim_anchor_source_channels_match_source_matrix",
            not legal_anchor_drift,
            expected=[],
            actual=legal_anchor_drift,
        ),
        _check("all_readiness_flags_blocked", not readiness_drift, expected=[], actual=readiness_drift),
        _check("artifact_paths_are_handoff_safe", not unsafe_paths, expected=[], actual=unsafe_paths),
        _check("raw_payload_sections_absent", not raw_keys, expected=[], actual=raw_keys),
        _check("privacy_scan_ok", privacy_scan.get("ok") is True, expected=True, actual=privacy_scan.get("counts")),
        _check("readiness_bundle_contains_no_disallowed_text", not disallowed, expected=[], actual=disallowed),
    ]
    if compare_current_chain:
        checks.append(
            _check(
                "readiness_bundle_matches_current_chain",
                _comparable_sections(doc) == current_sections,
                expected=current_sections,
                actual=_comparable_sections(doc),
            )
        )
    failed = _failed_ids(checks)
    return {
        "_meta": {
            "schema_version": "global_protections_readiness_bundle_validation.v1",
            "source_bundle_path": _display_path(bundle_path) if bundle_path else "n/a",
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
            "safe_for_project_planning": summary.get("safe_for_project_planning"),
            "worker_prompt_count": summary.get("worker_prompt_count"),
            "worker_prompts_blocked_for_comparable_run": summary.get(
                "worker_prompts_blocked_for_comparable_run"
            ),
            "worker_verified_local_law_rows": summary.get("worker_verified_local_law_rows"),
            "regulatory_pattern_count": summary.get("regulatory_pattern_count"),
            "regulatory_candidate_count": summary.get("regulatory_candidate_count"),
            "legal_claim_anchor_source_channel_count": summary.get(
                "legal_claim_anchor_source_channel_count"
            ),
            "legal_claim_anchor_source_channel_ids": summary.get(
                "legal_claim_anchor_source_channel_ids"
            ),
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
        "# Global Protections Readiness Bundle Validation",
        "",
        "This read-only report validates the saved readiness bundle before it is used as a handoff.",
        "",
        "## Summary",
        "",
        "| Metric | Value |",
        "|---|---:|",
        f"| Valid | {str(bool(summary['valid'])).lower()} |",
        f"| Checks | {summary['check_count']} |",
        f"| Failed checks | {summary['failed_check_count']} |",
        f"| Safe for project planning | {str(bool(summary.get('safe_for_project_planning'))).lower()} |",
        f"| Worker prompts | {_md_cell(summary.get('worker_prompt_count'))} |",
        (
            "| Worker prompts blocked "
            f"| {_md_cell(summary.get('worker_prompts_blocked_for_comparable_run'))} |"
        ),
        f"| Worker verified local-law rows | {_md_cell(summary.get('worker_verified_local_law_rows'))} |",
        f"| Regulatory patterns | {_md_cell(summary.get('regulatory_pattern_count'))} |",
        f"| Regulatory candidates | {_md_cell(summary.get('regulatory_candidate_count'))} |",
        (
            "| Legal-claim anchor source channels "
            f"| {_md_cell(summary.get('legal_claim_anchor_source_channel_count'))} |"
        ),
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
    ap.add_argument("--bundle", type=pathlib.Path, default=DEFAULT_BUNDLE)
    ap.add_argument("--domain", default=DEFAULT_DOMAIN)
    ap.add_argument("--project-config", type=pathlib.Path, default=project_plan_builder.CONFIG)
    ap.add_argument("--registry", type=pathlib.Path, default=project_plan_builder.REGISTRY)
    ap.add_argument("--regulatory-catalog", type=pathlib.Path, default=project_plan_builder.REGULATORY_CATALOG)
    ap.add_argument("--component-dir", type=pathlib.Path, default=readiness_builder.OUT_DIR)
    ap.add_argument("--out", type=pathlib.Path, default=OUT)
    ap.add_argument("--markdown-out", type=pathlib.Path, default=MD_OUT)
    ap.add_argument("--no-current-chain", action="store_true", help="skip comparison to the current generated chain")
    ap.add_argument("--validate", action="store_true", help="print the validation summary only; write nothing")
    args = ap.parse_args(argv)

    doc = _load_json(args.bundle)
    if doc is None:
        print(f"[global-protections-readiness-bundle-validation] unreadable bundle: {args.bundle}")
        return 1
    report = validate_readiness_bundle(
        doc,
        bundle_path=args.bundle,
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
        "[global-protections-readiness-bundle-validation] "
        f"valid={str(bool(summary['valid'])).lower()}; "
        f"failed={summary['failed_check_count']}/{summary['check_count']}; "
        f"ready_for_comparable_scoring={str(bool(summary['ready_for_comparable_scoring'])).lower()} -> {args.bundle}"
    )
    return 0 if summary["valid"] else 1


if __name__ == "__main__":
    raise SystemExit(main())
