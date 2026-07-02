#!/usr/bin/env python3
"""Validate a saved regulatory curation bundle artifact.

The regulatory curation builder proves the adjacent-domain expansion chain in
memory. This validator checks a saved JSON artifact before anyone treats it as a
current handoff: shape, compactness, blocked readiness flags, candidate-queue
counts, privacy scan, artifact-path hygiene, and summary counts against the
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

import build_regulatory_curation_bundle as curation_builder  # noqa: E402
import build_regulatory_miss_pattern_plan as pattern_plan_builder  # noqa: E402

DEFAULT_BUNDLE = curation_builder.OUT
CONFIG = curation_builder.CONFIG
REGISTRY = curation_builder.REGISTRY
OUT = curation_builder.OUT_DIR / "regulatory_curation_bundle_validation.json"
MD_OUT = curation_builder.OUT_DIR / "regulatory_curation_bundle_validation.md"

REQUIRED_TOP_LEVEL = frozenset({
    "_meta",
    "summary",
    "component_summaries",
    "consistency_checks",
    "artifact_paths",
})
ALLOWED_TOP_LEVEL = REQUIRED_TOP_LEVEL
REQUIRED_COMPONENTS = frozenset({
    "miss_pattern_plan",
    "domain_intake_packet",
    "domain_intake_validation",
    "domain_seed_proposal",
})
REQUIRED_ARTIFACT_KEYS = frozenset({
    "miss_pattern_plan_json",
    "miss_pattern_plan_markdown",
    "domain_intake_packet_json",
    "domain_intake_packet_markdown",
    "domain_intake_validation_json",
    "domain_intake_validation_markdown",
    "domain_seed_proposal_json",
    "domain_seed_proposal_markdown",
    "regulatory_curation_bundle_json",
    "regulatory_curation_bundle_markdown",
})
RAW_PAYLOAD_KEYS = frozenset({
    "patterns",
    "expansion_queue",
    "active_seed_followups",
    "candidate_domain_intake",
    "candidate_rows",
    "domain_seed_proposals",
    "accepted_operations",
    "rejected_proposals",
    "registry_preview",
})
DISALLOWED_TERMS = [
    "prompt_family_sketches",
    "candidate_url",
    "source_url",
    "raw_text",
    "case_text",
    "https://",
    "www.",
]
REQUIRED_CONSISTENCY_IDS = frozenset({
    "candidate_queue_count_matches_candidates",
    "intake_preserves_candidate_queue",
    "candidate_queue_keeps_scoring_blocked",
    "prompt_generation_blocked",
    "comparable_scoring_blocked",
})
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
    for key, value in paths.items():
        if not isinstance(value, str) or not value.strip():
            findings.append({"key": str(key), "value": "missing_or_not_string"})
            continue
        parts = pathlib.PurePosixPath(value).parts
        if (
            "\\" in value
            or _URL.search(value)
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
    return sorted(key for key in RAW_PAYLOAD_KEYS if key in doc)


def _count_mismatches(doc: dict[str, Any]) -> list[dict[str, Any]]:
    summary = doc.get("summary") if isinstance(doc.get("summary"), dict) else {}
    components = doc.get("component_summaries") if isinstance(doc.get("component_summaries"), dict) else {}
    plan = components.get("miss_pattern_plan") if isinstance(components.get("miss_pattern_plan"), dict) else {}
    intake = (
        components.get("domain_intake_packet")
        if isinstance(components.get("domain_intake_packet"), dict)
        else {}
    )
    validation = (
        components.get("domain_intake_validation")
        if isinstance(components.get("domain_intake_validation"), dict)
        else {}
    )
    proposal = (
        components.get("domain_seed_proposal")
        if isinstance(components.get("domain_seed_proposal"), dict)
        else {}
    )
    pairs = [
        ("pattern_count", plan, "pattern_count"),
        ("active_seed_count", plan, "active_seed_count"),
        ("candidate_count", plan, "candidate_count"),
        ("candidate_queue_count", plan, "candidate_queue_count"),
        ("top_candidate_id", plan, "top_candidate_id"),
        ("defer_count", plan, "defer_count"),
        ("candidate_intake_rows", intake, "candidate_count"),
        ("active_seed_followups", intake, "active_seed_count"),
        ("candidate_queue_count", intake, "candidate_queue_count"),
        ("top_candidate_id", intake, "top_candidate_id"),
        ("validation_candidate_rows", validation, "candidate_count"),
        ("validation_pending_or_deferred_rows", validation, "pending_or_deferred_count"),
        ("validation_accepted_domain_seed_proposals", validation, "accepted_for_domain_seed_proposal_count"),
        ("validation_invalid_rows", validation, "invalid_count"),
        ("seed_scaffold_operations", proposal, "accepted_operations"),
        ("seed_rejected_proposals", proposal, "rejected_proposals"),
        ("ready_for_seed_file_creation", proposal, "ready_for_seed_file_creation"),
        ("ready_for_manual_registry_patch", proposal, "ready_for_manual_registry_patch"),
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
    for key in (
        "ready_for_manual_registry_patch",
        "ready_for_prompt_generation",
        "ready_for_comparable_scoring",
    ):
        if summary.get(key) is not False:
            findings.append(f"summary.{key}")
    plan = components.get("miss_pattern_plan") if isinstance(components.get("miss_pattern_plan"), dict) else {}
    if plan.get("ready_for_comparable_scoring") is not False:
        findings.append("component_summaries.miss_pattern_plan.ready_for_comparable_scoring")
    intake = (
        components.get("domain_intake_packet")
        if isinstance(components.get("domain_intake_packet"), dict)
        else {}
    )
    for key in ("ready_for_prompt_generation_count", "ready_for_comparable_scoring_count"):
        if intake.get(key) != 0:
            findings.append(f"component_summaries.domain_intake_packet.{key}")
    validation = (
        components.get("domain_intake_validation")
        if isinstance(components.get("domain_intake_validation"), dict)
        else {}
    )
    for key in ("ready_for_prompt_generation_count", "ready_for_comparable_scoring_count"):
        if validation.get(key) != 0:
            findings.append(f"component_summaries.domain_intake_validation.{key}")
    proposal = (
        components.get("domain_seed_proposal")
        if isinstance(components.get("domain_seed_proposal"), dict)
        else {}
    )
    for key in (
        "ready_for_manual_registry_patch",
        "ready_for_prompt_generation",
        "ready_for_comparable_scoring",
    ):
        if proposal.get(key) is not False:
            findings.append(f"component_summaries.domain_seed_proposal.{key}")
    return findings


def _queue_drift(doc: dict[str, Any]) -> list[str]:
    summary = doc.get("summary") if isinstance(doc.get("summary"), dict) else {}
    components = doc.get("component_summaries") if isinstance(doc.get("component_summaries"), dict) else {}
    plan = components.get("miss_pattern_plan") if isinstance(components.get("miss_pattern_plan"), dict) else {}
    findings: list[str] = []
    if summary.get("candidate_queue_count") != summary.get("candidate_count"):
        findings.append("summary.candidate_queue_count")
    if plan.get("candidate_queue_count") != plan.get("candidate_count"):
        findings.append("component_summaries.miss_pattern_plan.candidate_queue_count")
    if summary.get("candidate_count", 0) and not summary.get("top_candidate_id"):
        findings.append("summary.top_candidate_id")
    if plan.get("candidate_count", 0) and not plan.get("top_candidate_id"):
        findings.append("component_summaries.miss_pattern_plan.top_candidate_id")
    if plan.get("priority_signal_count", 0) <= 0:
        findings.append("component_summaries.miss_pattern_plan.priority_signal_count")
    return findings


def _consistency_drift(checks_value: Any) -> dict[str, Any]:
    checks = checks_value if isinstance(checks_value, list) else []
    check_ids = {str(check.get("id")) for check in checks if isinstance(check, dict)}
    failed = [
        str(check.get("id", "unknown"))
        for check in checks
        if not isinstance(check, dict) or check.get("ok") is not True
    ]
    missing = sorted(REQUIRED_CONSISTENCY_IDS - check_ids)
    return {
        "failed": sorted(failed),
        "missing_required": missing,
        "check_count": len(checks),
    }


def _current_reference(
    *,
    config_path: pathlib.Path,
    registry_path: pathlib.Path,
    component_dir: pathlib.Path | None = None,
) -> dict[str, Any]:
    return curation_builder.build_regulatory_curation_bundle(
        config_path=config_path,
        registry_path=registry_path,
        component_dir=component_dir,
    )


def validate_regulatory_curation_bundle(
    doc: Any,
    *,
    bundle_path: pathlib.Path | None = None,
    config_path: pathlib.Path = CONFIG,
    registry_path: pathlib.Path = REGISTRY,
    component_dir: pathlib.Path | None = None,
    compare_current_chain: bool = True,
) -> dict[str, Any]:
    if not isinstance(doc, dict):
        checks = [
            _check("bundle_is_object", False, expected="object", actual=type(doc).__name__),
        ]
        failed = _failed_ids(checks)
        return {
            "_meta": {
                "schema_version": "regulatory_curation_bundle_validation.v1",
                "source_bundle_path": _display_path(bundle_path) if bundle_path else "n/a",
                "config_path": _display_path(config_path),
                "registry_path": _display_path(registry_path),
                "component_dir": _display_path(component_dir) if component_dir else _display_path(curation_builder.OUT_DIR),
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
    components = doc.get("component_summaries") if isinstance(doc.get("component_summaries"), dict) else {}
    artifact_paths = doc.get("artifact_paths")
    expected_artifact_paths = curation_builder.component_paths(output_dir=component_dir)
    artifact_path_drift = _artifact_path_map_drift(
        artifact_paths,
        expected=expected_artifact_paths,
    )
    consistency = _consistency_drift(doc.get("consistency_checks"))
    privacy_scan = pattern_plan_builder._scan_privacy(_redacted_privacy_view(doc))
    encoded = json.dumps(doc, ensure_ascii=False)
    disallowed = [term for term in DISALLOWED_TERMS if term in encoded]
    current = (
        _current_reference(
            config_path=config_path,
            registry_path=registry_path,
            component_dir=component_dir,
        )
        if compare_current_chain
        else None
    )
    current_summary = current["summary"] if current else None
    current_components = current["component_summaries"] if current else None
    checks = [
        _check(
            "top_level_shape",
            REQUIRED_TOP_LEVEL.issubset(doc) and not (set(doc) - ALLOWED_TOP_LEVEL),
            expected=sorted(REQUIRED_TOP_LEVEL),
            actual=sorted(doc),
        ),
        _check(
            "component_summaries_present",
            REQUIRED_COMPONENTS.issubset(components),
            expected=sorted(REQUIRED_COMPONENTS),
            actual=sorted(components) if isinstance(components, dict) else type(components).__name__,
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
            "artifact_paths_match_component_dir",
            not artifact_path_drift,
            expected=[],
            actual=artifact_path_drift,
        ),
        _check(
            "raw_payload_sections_absent",
            not _raw_payload_keys(doc),
            expected=[],
            actual=_raw_payload_keys(doc),
        ),
        _check(
            "privacy_scan_ok",
            privacy_scan.get("ok") is True,
            expected=True,
            actual=privacy_scan.get("counts"),
        ),
        _check(
            "bundle_contains_no_disallowed_text",
            not disallowed,
            expected=[],
            actual=disallowed,
        ),
        _check(
            "consistency_checks_all_ok",
            not consistency["failed"] and not consistency["missing_required"],
            expected={"failed": [], "missing_required": []},
            actual=consistency,
        ),
        _check(
            "summary_counts_match_component_summaries",
            not _count_mismatches(doc),
            expected=[],
            actual=_count_mismatches(doc),
        ),
        _check(
            "candidate_queue_invariants_hold",
            not _queue_drift(doc),
            expected=[],
            actual=_queue_drift(doc),
        ),
        _check(
            "all_prompt_and_scoring_flags_blocked",
            not _readiness_drift(doc),
            expected=[],
            actual=_readiness_drift(doc),
        ),
    ]
    if compare_current_chain:
        checks.extend([
            _check(
                "summary_matches_current_chain",
                summary == current_summary,
                expected=current_summary,
                actual=summary,
            ),
            _check(
                "component_summaries_match_current_chain",
                components == current_components,
                expected=current_components,
                actual=components,
            ),
        ])
    failed = _failed_ids(checks)
    return {
        "_meta": {
            "schema_version": "regulatory_curation_bundle_validation.v1",
            "source_bundle_path": _display_path(bundle_path) if bundle_path else "n/a",
            "config_path": _display_path(config_path),
            "registry_path": _display_path(registry_path),
            "component_dir": _display_path(component_dir) if component_dir else _display_path(curation_builder.OUT_DIR),
            "compare_current_chain": compare_current_chain,
        },
        "summary": {
            "valid": not failed,
            "check_count": len(checks),
            "failed_check_count": len(failed),
            "failed_check_ids": failed,
            "ready_for_prompt_generation": summary.get("ready_for_prompt_generation"),
            "ready_for_comparable_scoring": summary.get("ready_for_comparable_scoring"),
            "candidate_queue_count": summary.get("candidate_queue_count"),
            "top_candidate_id": summary.get("top_candidate_id"),
        },
        "checks": checks,
    }


def _md_cell(value: Any) -> str:
    text = json.dumps(value, sort_keys=True) if isinstance(value, (dict, list)) else str(value)
    return text.replace("|", "\\|").replace("\n", " ").strip()


def render_markdown(report: dict[str, Any]) -> str:
    summary = report["summary"]
    lines = [
        "# Regulatory Curation Bundle Validation",
        "",
        "This read-only report validates the saved regulatory curation bundle against the current source-gated chain.",
        "",
        "## Summary",
        "",
        "| Metric | Value |",
        "|---|---:|",
        f"| Valid | {str(bool(summary['valid'])).lower()} |",
        f"| Checks | {summary['check_count']} |",
        f"| Failed checks | {summary['failed_check_count']} |",
        f"| Component dir | {_md_cell(report.get('_meta', {}).get('component_dir'))} |",
        f"| Candidate queue | {_md_cell(summary.get('candidate_queue_count'))} |",
        f"| Top candidate | {_md_cell(summary.get('top_candidate_id'))} |",
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
    ap.add_argument("--bundle", type=pathlib.Path, default=DEFAULT_BUNDLE)
    ap.add_argument("--config", type=pathlib.Path, default=CONFIG)
    ap.add_argument("--registry", type=pathlib.Path, default=REGISTRY)
    ap.add_argument("--component-dir", type=pathlib.Path, default=None)
    ap.add_argument("--out", type=pathlib.Path, default=OUT)
    ap.add_argument("--markdown-out", type=pathlib.Path, default=MD_OUT)
    ap.add_argument("--no-current-chain", action="store_true", help="skip comparison to the current generated chain")
    ap.add_argument("--validate", action="store_true", help="print the validation summary only; write nothing")
    args = ap.parse_args(argv)

    doc = _load_json(args.bundle)
    if doc is None:
        print(f"[regulatory-curation-bundle-validation] unreadable bundle: {args.bundle}")
        return 1
    report = validate_regulatory_curation_bundle(
        doc,
        bundle_path=args.bundle,
        config_path=args.config,
        registry_path=args.registry,
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
        "[regulatory-curation-bundle-validation] "
        f"valid={str(bool(summary['valid'])).lower()}; "
        f"failed={summary['failed_check_count']}/{summary['check_count']}; "
        f"ready_for_comparable_scoring={str(bool(summary['ready_for_comparable_scoring'])).lower()} -> {args.bundle}"
    )
    return 0 if summary["valid"] else 1


if __name__ == "__main__":
    raise SystemExit(main())
