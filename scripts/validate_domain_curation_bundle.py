#!/usr/bin/env python3
"""Validate a saved domain curation bundle artifact.

The domain curation builder proves a source-gated domain curation chain in
memory. This validator checks a saved JSON artifact before anyone treats it as
a current handoff: shape, compactness, blocked readiness flags, consistency
checks, privacy scan, artifact-path hygiene, and summary counts against the
current non-mutating chain.

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

import build_domain_curation_bundle as curation_builder  # noqa: E402

DEFAULT_DOMAIN = "developing_country_worker_protections"
OUT_DIR = curation_builder.OUT_DIR

REQUIRED_TOP_LEVEL = frozenset({
    "_meta",
    "summary",
    "component_summaries",
    "consistency_checks",
    "artifact_paths",
})
ALLOWED_TOP_LEVEL = REQUIRED_TOP_LEVEL
REQUIRED_COMPONENTS = frozenset({
    "grounding_queue",
    "source_research_plan",
    "source_coverage_matrix",
    "source_review_packet",
    "source_review_sprint",
    "source_review_ledger",
    "source_review_validation",
    "grounding_manifest_proposal",
})
REQUIRED_ARTIFACT_KEYS = frozenset({
    "grounding_queue_json",
    "grounding_queue_markdown",
    "source_research_plan_json",
    "source_research_plan_markdown",
    "source_coverage_matrix_json",
    "source_coverage_matrix_markdown",
    "source_review_packet_json",
    "source_review_packet_markdown",
    "source_review_sprint_json",
    "source_review_sprint_markdown",
    "source_review_ledger_json",
    "source_review_ledger_markdown",
    "source_review_validation_json",
    "source_review_validation_markdown",
    "grounding_manifest_proposal_json",
    "grounding_manifest_proposal_markdown",
    "curation_bundle_json",
    "curation_bundle_markdown",
})
REQUIRED_CONSISTENCY_IDS = frozenset({
    "source_object_counts_match",
    "scope_refinement_counts_match",
    "blocked_prompt_count_matches",
    "blank_packet_safety_audit_ok",
    "coverage_matrix_counts_match",
    "coverage_matrix_consistency_ok",
    "source_review_sprint_consistency_ok",
    "source_review_sprint_has_no_ready_claims",
    "source_review_ledger_consistency_ok",
    "source_review_ledger_matches_validation",
    "source_review_validation_ok",
    "manifest_proposal_ok",
    "manifest_preview_valid",
})
RAW_PAYLOAD_KEYS = frozenset({
    "source_object_queue",
    "scope_refinement_queue",
    "source_candidate_intake_rows",
    "scope_resolution_intake_rows",
    "source_review_sprint_rows",
    "candidate_manifest_rows",
    "scope_update_candidates",
    "accepted_operations",
    "rejected_candidates",
    "preview_manifest",
    "candidate_manifest_row",
    "scope_update_candidate",
})
DISALLOWED_TERMS = [
    "Synthetic composite:",
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
_EMAIL = re.compile(r"\b[\w.+-]+@[\w-]+\.[\w.-]+\b", re.I)
_PHONE = re.compile(r"\+?\d[\d\s().\-]{8,}\d")
_LOCAL_PATH_HINT = re.compile(
    r"(?i)(?:^[A-Za-z]:[\\/]|[\\/]Users[\\/]|[\\/]home[\\/]|[\\/]tmp[\\/]|\\\\|~[\\/])"
)


def default_bundle_path(domain_id: str = DEFAULT_DOMAIN) -> pathlib.Path:
    return curation_builder.default_out_path(domain_id)


def default_out_path(domain_id: str = DEFAULT_DOMAIN) -> pathlib.Path:
    return OUT_DIR / f"{curation_builder._safe_domain_id(domain_id)}_curation_bundle_validation.json"


def default_markdown_path(out_path: pathlib.Path) -> pathlib.Path:
    return out_path.with_suffix(".md")


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


def _privacy_scan(doc: Any) -> dict[str, Any]:
    encoded = json.dumps(doc, ensure_ascii=False)
    counts = {
        "email_like": len(_EMAIL.findall(encoded)),
        "phone_like": len(_PHONE.findall(encoded)),
        "local_path_like": len(_LOCAL_PATH_HINT.findall(encoded)),
    }
    return {
        "ok": not any(counts.values()),
        "counts": counts,
    }


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


def _artifact_path_map_drift(actual: Any, *, expected: dict[str, str]) -> list[dict[str, Any]]:
    if not isinstance(actual, dict):
        return [{"rule": "artifact_paths_object", "expected": "object", "actual": type(actual).__name__}]
    findings: list[dict[str, Any]] = []
    missing = sorted(set(expected) - set(actual))
    extra = sorted(set(actual) - set(expected))
    if missing or extra:
        findings.append({"rule": "artifact_path_keys", "missing": missing, "extra": extra})
    for key in sorted(set(expected) & set(actual)):
        if actual.get(key) != expected[key]:
            findings.append({
                "rule": "artifact_path_value",
                "key": key,
                "expected": expected[key],
                "actual": actual.get(key),
            })
    return findings


def _raw_payload_keys(doc: dict[str, Any]) -> list[str]:
    return sorted(key for key in doc if key in RAW_PAYLOAD_KEYS)


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
        "missing_required": sorted(REQUIRED_CONSISTENCY_IDS - check_ids),
        "check_count": len(checks),
    }


def _count_mismatches(doc: dict[str, Any]) -> list[dict[str, Any]]:
    summary = doc.get("summary") if isinstance(doc.get("summary"), dict) else {}
    components = doc.get("component_summaries") if isinstance(doc.get("component_summaries"), dict) else {}
    queue = components.get("grounding_queue") if isinstance(components.get("grounding_queue"), dict) else {}
    research = (
        components.get("source_research_plan")
        if isinstance(components.get("source_research_plan"), dict)
        else {}
    )
    matrix = (
        components.get("source_coverage_matrix")
        if isinstance(components.get("source_coverage_matrix"), dict)
        else {}
    )
    sprint = (
        components.get("source_review_sprint")
        if isinstance(components.get("source_review_sprint"), dict)
        else {}
    )
    ledger = (
        components.get("source_review_ledger")
        if isinstance(components.get("source_review_ledger"), dict)
        else {}
    )
    validation = (
        components.get("source_review_validation")
        if isinstance(components.get("source_review_validation"), dict)
        else {}
    )
    proposal = (
        components.get("grounding_manifest_proposal")
        if isinstance(components.get("grounding_manifest_proposal"), dict)
        else {}
    )
    pairs = [
        ("prompt_count", queue, "prompt_count"),
        ("prompts_ready_for_comparable_run", queue, "prompts_ready_for_comparable_run"),
        ("prompts_blocked_for_comparable_run", queue, "prompts_blocked_for_comparable_run"),
        ("verified_local_law_rows", queue, "verified_local_law_rows"),
        ("source_object_tasks", research, "source_object_tasks"),
        ("scope_refinement_tasks", research, "scope_refinement_tasks"),
        ("source_coverage_cells", matrix, "coverage_cells"),
        ("source_coverage_scope_blocked_cells", matrix, "scope_blocked_cells"),
        (
            "source_coverage_pending_manifest_rows_to_promote",
            matrix,
            "pending_manifest_rows_to_promote",
        ),
        ("source_coverage_missing_manifest_rows_to_add", matrix, "missing_manifest_rows_to_add"),
        ("source_review_sprint_rows", sprint, "source_review_sprint_rows"),
        ("scope_resolution_sprint_rows", sprint, "scope_resolution_sprint_rows"),
        (
            "source_review_sprint_deferred_scope_blocked_rows",
            sprint,
            "deferred_scope_blocked_source_rows",
        ),
        ("source_review_ledger_source_rows_not_started", ledger, "source_rows_not_started"),
        ("source_review_ledger_scope_rows_not_started", ledger, "scope_rows_not_started"),
        (
            "source_review_ledger_source_rows_in_progress_not_ready",
            ledger,
            "source_rows_in_progress_not_ready",
        ),
        (
            "source_review_ledger_scope_rows_in_progress_not_ready",
            ledger,
            "scope_rows_in_progress_not_ready",
        ),
        ("source_review_validation_ok", validation, "ok"),
        ("source_rows_ready_claimed", validation, "source_rows_ready_claimed"),
        (
            "source_rows_accepted_for_manifest_proposal",
            validation,
            "source_rows_accepted_for_manifest_proposal",
        ),
        ("manifest_proposal_ok", proposal, "proposal_ok"),
        ("manifest_operations_ready_for_manual_patch", proposal, "accepted_operations"),
        ("ready_for_manual_manifest_patch", proposal, "ready_for_manual_manifest_patch"),
    ]
    mismatches: list[dict[str, Any]] = []
    for summary_key, component, component_key in pairs:
        expected = component.get(component_key)
        actual = summary.get(summary_key)
        if actual != expected:
            mismatches.append({
                "summary_key": summary_key,
                "component_key": component_key,
                "expected": expected,
                "actual": actual,
            })
    return mismatches


def _readiness_drift(doc: dict[str, Any]) -> list[str]:
    summary = doc.get("summary") if isinstance(doc.get("summary"), dict) else {}
    components = doc.get("component_summaries") if isinstance(doc.get("component_summaries"), dict) else {}
    findings: list[str] = []
    if summary.get("consistency_ok") is not True:
        findings.append("summary.consistency_ok")
    if summary.get("ready_for_manual_manifest_patch") is not False:
        findings.append("summary.ready_for_manual_manifest_patch")
    if summary.get("ready_for_comparable_run") is not False:
        findings.append("summary.ready_for_comparable_run")
    if summary.get("verified_local_law_rows") != 0:
        findings.append("summary.verified_local_law_rows")
    if summary.get("prompts_ready_for_comparable_run") != 0:
        findings.append("summary.prompts_ready_for_comparable_run")
    if summary.get("prompts_blocked_for_comparable_run") != summary.get("prompt_count"):
        findings.append("summary.prompts_blocked_for_comparable_run")
    if summary.get("source_rows_ready_claimed") != 0:
        findings.append("summary.source_rows_ready_claimed")
    if summary.get("source_rows_accepted_for_manifest_proposal") != 0:
        findings.append("summary.source_rows_accepted_for_manifest_proposal")
    if summary.get("manifest_operations_ready_for_manual_patch") != 0:
        findings.append("summary.manifest_operations_ready_for_manual_patch")

    matrix = (
        components.get("source_coverage_matrix")
        if isinstance(components.get("source_coverage_matrix"), dict)
        else {}
    )
    if matrix.get("ready_for_comparable_run") is not False:
        findings.append("component_summaries.source_coverage_matrix.ready_for_comparable_run")
    sprint = (
        components.get("source_review_sprint")
        if isinstance(components.get("source_review_sprint"), dict)
        else {}
    )
    if sprint.get("all_source_rows_ready_for_manifest_promotion") is not False:
        findings.append(
            "component_summaries.source_review_sprint.all_source_rows_ready_for_manifest_promotion"
        )
    if sprint.get("all_scope_rows_ready_for_source_queue_update") is not False:
        findings.append(
            "component_summaries.source_review_sprint.all_scope_rows_ready_for_source_queue_update"
        )
    if sprint.get("ready_for_comparable_run") is not False:
        findings.append("component_summaries.source_review_sprint.ready_for_comparable_run")
    ledger = (
        components.get("source_review_ledger")
        if isinstance(components.get("source_review_ledger"), dict)
        else {}
    )
    if ledger.get("ready_for_comparable_run") is not False:
        findings.append("component_summaries.source_review_ledger.ready_for_comparable_run")
    proposal = (
        components.get("grounding_manifest_proposal")
        if isinstance(components.get("grounding_manifest_proposal"), dict)
        else {}
    )
    if proposal.get("ready_for_manual_manifest_patch") is not False:
        findings.append("component_summaries.grounding_manifest_proposal.ready_for_manual_manifest_patch")
    if proposal.get("accepted_operations") != 0:
        findings.append("component_summaries.grounding_manifest_proposal.accepted_operations")
    return findings


def _current_reference(domain_id: str) -> dict[str, Any]:
    return curation_builder.build_curation_bundle(domain_id)


def _comparable_sections(doc: dict[str, Any]) -> dict[str, Any]:
    return {
        "summary": doc.get("summary"),
        "component_summaries": doc.get("component_summaries"),
        "consistency_checks": doc.get("consistency_checks"),
    }


def validate_domain_curation_bundle(
    doc: Any,
    *,
    bundle_path: pathlib.Path | None = None,
    domain_id: str = DEFAULT_DOMAIN,
    component_dir: pathlib.Path | None = None,
    compare_current_chain: bool = True,
) -> dict[str, Any]:
    if not isinstance(doc, dict):
        checks = [_check("domain_curation_bundle_is_object", False, expected="object", actual=type(doc).__name__)]
        failed = _failed_ids(checks)
        return {
            "_meta": {
                "schema_version": "domain_curation_bundle_validation.v1",
                "source_bundle_path": _display_path(bundle_path) if bundle_path else "n/a",
                "domain": domain_id,
                "component_dir": _display_path(component_dir) if component_dir else _display_path(OUT_DIR),
                "compare_current_chain": compare_current_chain,
            },
            "summary": {
                "valid": False,
                "check_count": len(checks),
                "failed_check_count": len(failed),
                "failed_check_ids": failed,
                "ready_for_comparable_run": None,
            },
            "checks": checks,
        }

    summary = doc.get("summary") if isinstance(doc.get("summary"), dict) else {}
    components = doc.get("component_summaries") if isinstance(doc.get("component_summaries"), dict) else {}
    artifact_paths = doc.get("artifact_paths")
    consistency = _consistency_drift(doc.get("consistency_checks"))
    unsafe_paths = _unsafe_artifact_paths(artifact_paths)
    expected_artifact_paths = curation_builder.component_paths(domain_id, output_dir=component_dir)
    artifact_path_drift = _artifact_path_map_drift(
        artifact_paths,
        expected=expected_artifact_paths,
    )
    raw_keys = _raw_payload_keys(doc)
    privacy_scan = _privacy_scan(_redacted_privacy_view(doc))
    encoded = json.dumps(doc, ensure_ascii=False)
    disallowed = [term for term in DISALLOWED_TERMS if term in encoded]
    count_mismatches = _count_mismatches(doc)
    readiness_drift = _readiness_drift(doc)
    current = _current_reference(domain_id) if compare_current_chain else None
    current_sections = _comparable_sections(current) if current else None

    checks = [
        _check(
            "top_level_shape",
            REQUIRED_TOP_LEVEL.issubset(doc) and not (set(doc) - ALLOWED_TOP_LEVEL),
            expected=sorted(REQUIRED_TOP_LEVEL),
            actual=sorted(doc),
        ),
        _check(
            "component_summaries_present",
            isinstance(components, dict) and REQUIRED_COMPONENTS.issubset(components),
            expected=sorted(REQUIRED_COMPONENTS),
            actual=sorted(components) if isinstance(components, dict) else type(components).__name__,
        ),
        _check(
            "artifact_paths_present",
            isinstance(artifact_paths, dict) and REQUIRED_ARTIFACT_KEYS.issubset(artifact_paths),
            expected=sorted(REQUIRED_ARTIFACT_KEYS),
            actual=sorted(artifact_paths) if isinstance(artifact_paths, dict) else type(artifact_paths).__name__,
        ),
        _check("artifact_paths_safe", not unsafe_paths, expected=[], actual=unsafe_paths),
        _check("artifact_paths_match_component_dir", not artifact_path_drift, expected=[], actual=artifact_path_drift),
        _check("raw_payload_sections_absent", not raw_keys, expected=[], actual=raw_keys),
        _check("privacy_scan_ok", privacy_scan["ok"] is True, expected=True, actual=privacy_scan["counts"]),
        _check("domain_curation_bundle_contains_no_disallowed_text", not disallowed, expected=[], actual=disallowed),
        _check(
            "consistency_checks_all_ok",
            not consistency["failed"] and not consistency["missing_required"],
            expected={"failed": [], "missing_required": []},
            actual=consistency,
        ),
        _check("summary_counts_match_component_summaries", not count_mismatches, expected=[], actual=count_mismatches),
        _check("all_source_and_scope_readiness_blocked", not readiness_drift, expected=[], actual=readiness_drift),
    ]
    if compare_current_chain:
        checks.append(
            _check(
                "domain_curation_bundle_matches_current_chain",
                _comparable_sections(doc) == current_sections,
                expected=current_sections,
                actual=_comparable_sections(doc),
            )
        )
    failed = _failed_ids(checks)
    return {
        "_meta": {
            "schema_version": "domain_curation_bundle_validation.v1",
            "source_bundle_path": _display_path(bundle_path) if bundle_path else "n/a",
            "domain": domain_id,
            "component_dir": _display_path(component_dir) if component_dir else _display_path(OUT_DIR),
            "compare_current_chain": compare_current_chain,
        },
        "summary": {
            "valid": not failed,
            "check_count": len(checks),
            "failed_check_count": len(failed),
            "failed_check_ids": failed,
            "prompt_count": summary.get("prompt_count"),
            "prompts_blocked_for_comparable_run": summary.get("prompts_blocked_for_comparable_run"),
            "verified_local_law_rows": summary.get("verified_local_law_rows"),
            "source_object_tasks": summary.get("source_object_tasks"),
            "scope_refinement_tasks": summary.get("scope_refinement_tasks"),
            "source_rows_ready_claimed": summary.get("source_rows_ready_claimed"),
            "manifest_operations_ready_for_manual_patch": summary.get(
                "manifest_operations_ready_for_manual_patch"
            ),
            "ready_for_manual_manifest_patch": summary.get("ready_for_manual_manifest_patch"),
            "ready_for_comparable_run": summary.get("ready_for_comparable_run"),
        },
        "checks": checks,
    }


def _md_cell(value: Any) -> str:
    text = json.dumps(value, sort_keys=True) if isinstance(value, (dict, list)) else str(value)
    return text.replace("|", "\\|").replace("\n", " ").strip()


def render_markdown(report: dict[str, Any]) -> str:
    summary = report["summary"]
    lines = [
        "# Domain Curation Bundle Validation",
        "",
        "This read-only report validates the saved domain curation bundle before it is used as a handoff.",
        "",
        "## Summary",
        "",
        "| Metric | Value |",
        "|---|---:|",
        f"| Valid | {str(bool(summary['valid'])).lower()} |",
        f"| Checks | {summary['check_count']} |",
        f"| Failed checks | {summary['failed_check_count']} |",
        f"| Component dir | {_md_cell(report.get('_meta', {}).get('component_dir'))} |",
        f"| Prompt count | {_md_cell(summary.get('prompt_count'))} |",
        f"| Prompts blocked | {_md_cell(summary.get('prompts_blocked_for_comparable_run'))} |",
        f"| Verified local-law rows | {_md_cell(summary.get('verified_local_law_rows'))} |",
        f"| Source-object tasks | {_md_cell(summary.get('source_object_tasks'))} |",
        f"| Scope-refinement tasks | {_md_cell(summary.get('scope_refinement_tasks'))} |",
        f"| Source rows ready claimed | {_md_cell(summary.get('source_rows_ready_claimed'))} |",
        (
            "| Manifest operations ready "
            f"| {_md_cell(summary.get('manifest_operations_ready_for_manual_patch'))} |"
        ),
        (
            "| Ready for manual manifest patch "
            f"| {str(bool(summary.get('ready_for_manual_manifest_patch'))).lower()} |"
        ),
        f"| Ready for comparable run | {str(bool(summary.get('ready_for_comparable_run'))).lower()} |",
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
    ap.add_argument("--domain", default=DEFAULT_DOMAIN)
    ap.add_argument("--bundle", type=pathlib.Path, default=None)
    ap.add_argument("--out", type=pathlib.Path, default=None)
    ap.add_argument("--markdown-out", type=pathlib.Path, default=None)
    ap.add_argument("--component-dir", type=pathlib.Path, default=None)
    ap.add_argument("--no-current-chain", action="store_true", help="skip comparison to the current generated chain")
    ap.add_argument("--validate", action="store_true", help="print the validation summary only; write nothing")
    args = ap.parse_args(argv)

    domain_id = curation_builder._safe_domain_id(args.domain)
    bundle_path = args.bundle or default_bundle_path(domain_id)
    out_path = args.out or default_out_path(domain_id)
    markdown_path = args.markdown_out or default_markdown_path(out_path)
    doc = _load_json(bundle_path)
    if doc is None:
        print(f"[domain-curation-bundle-validation] unreadable bundle: {bundle_path}")
        return 1
    report = validate_domain_curation_bundle(
        doc,
        bundle_path=bundle_path,
        domain_id=domain_id,
        component_dir=args.component_dir,
        compare_current_chain=not args.no_current_chain,
    )
    summary = report["summary"]
    if args.validate:
        print(json.dumps(summary, indent=2, ensure_ascii=False))
        return 0 if summary["valid"] else 1

    out_path.parent.mkdir(parents=True, exist_ok=True)
    markdown_path.parent.mkdir(parents=True, exist_ok=True)
    out_path.write_text(json.dumps(report, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
    markdown_path.write_text(render_markdown(report), encoding="utf-8")
    print(
        "[domain-curation-bundle-validation] "
        f"valid={str(bool(summary['valid'])).lower()}; "
        f"failed={summary['failed_check_count']}/{summary['check_count']}; "
        f"ready_for_comparable_run={str(bool(summary['ready_for_comparable_run'])).lower()} -> {bundle_path}"
    )
    return 0 if summary["valid"] else 1


if __name__ == "__main__":
    raise SystemExit(main())
