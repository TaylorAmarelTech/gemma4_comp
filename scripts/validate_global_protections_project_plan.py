#!/usr/bin/env python3
"""Validate a saved global-protections project plan.

The project plan is the root handoff for the global protections sister project.
This validator checks a saved JSON artifact before downstream builders trust it:
compact top-level shape, count integrity, linked seed/catalog state, blocked
readiness flags, phase-output path hygiene, embedded builder checks, privacy and
disallowed-text scans, and optional drift against the current deterministic
project-plan chain.

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

DEFAULT_PLAN = project_plan_builder.OUT
OUT = _ROOT / "reports" / "benchmark" / "global_protections_project_plan_validation.json"
MD_OUT = _ROOT / "reports" / "benchmark" / "global_protections_project_plan_validation.md"

REQUIRED_TOP_LEVEL = frozenset({
    "_meta",
    "project",
    "scope",
    "readiness",
    "existing_pipeline_links",
    "summary",
    "checks",
    "privacy_scan",
    "issues",
})
ALLOWED_TOP_LEVEL = REQUIRED_TOP_LEVEL
REQUIRED_PROJECT_KEYS = frozenset({
    "project_id",
    "display_name",
    "status",
    "research_question",
})
REQUIRED_SCOPE_KEYS = frozenset({
    "primary_seed_domains",
    "candidate_pattern_ids",
    "target_jurisdiction_families",
    "benchmark_axes",
    "source_admission_rules",
    "scored_capabilities",
    "non_goals",
})
REQUIRED_READINESS_KEYS = frozenset({
    "gates",
    "first_build_phases",
    "ready_for_research_planning",
    "ready_for_prompt_generation",
    "ready_for_training_use",
    "ready_for_public_claims",
    "ready_for_worker_facing_use",
    "ready_for_comparable_scoring",
    "policy",
})
REQUIRED_PIPELINE_LINK_KEYS = frozenset({
    "registered_seed_domains",
    "missing_seed_domains",
    "regulatory_candidates_found",
    "missing_candidate_patterns",
    "source_gated_chains",
})
REQUIRED_GATE_KEYS = frozenset({"id", "description", "blocks"})
REQUIRED_PHASE_KEYS = frozenset({
    "id",
    "description",
    "output",
    "ready_for_public_scoring",
    "ready_for_training_use",
    "ready_for_worker_facing_use",
})
REQUIRED_CHECK_IDS = frozenset({
    "privacy_scan_ok",
    "status_is_propose_only",
    "primary_seed_domain_registered",
    "regulatory_candidates_found",
    "source_admission_rules_present",
    "readiness_gates_present",
    "public_scoring_blocked",
    "training_use_blocked",
    "worker_facing_use_blocked",
})
READY_FLAG_KEYS = (
    "ready_for_prompt_generation",
    "ready_for_training_use",
    "ready_for_public_claims",
    "ready_for_worker_facing_use",
    "ready_for_comparable_scoring",
)
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
_SLUG = re.compile(r"^[a-z][a-z0-9_]{2,80}$")
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


def _shape_drift(doc: dict[str, Any]) -> list[dict[str, Any]]:
    findings: list[dict[str, Any]] = []
    top_extra = sorted(set(doc) - ALLOWED_TOP_LEVEL)
    top_missing = sorted(REQUIRED_TOP_LEVEL - set(doc))
    if top_missing or top_extra:
        findings.append({"section": "$", "missing": top_missing, "extra": top_extra})
    sections = [
        ("project", REQUIRED_PROJECT_KEYS),
        ("scope", REQUIRED_SCOPE_KEYS),
        ("readiness", REQUIRED_READINESS_KEYS),
        ("existing_pipeline_links", REQUIRED_PIPELINE_LINK_KEYS),
    ]
    for section, required in sections:
        value = doc.get(section)
        if not isinstance(value, dict):
            findings.append({"section": section, "rule": "object", "actual": type(value).__name__})
            continue
        missing = sorted(required - set(value))
        extra = sorted(set(value) - required)
        if missing or extra:
            findings.append({"section": section, "missing": missing, "extra": extra})
    return findings


def _readiness_gate_drift(doc: dict[str, Any]) -> list[dict[str, Any]]:
    readiness = doc.get("readiness") if isinstance(doc.get("readiness"), dict) else {}
    gates = readiness.get("gates") if isinstance(readiness.get("gates"), list) else []
    findings: list[dict[str, Any]] = []
    ids: list[Any] = []
    for idx, gate in enumerate(gates):
        if not isinstance(gate, dict):
            findings.append({"gate": idx, "rule": "gate_object", "actual": type(gate).__name__})
            continue
        ids.append(gate.get("id"))
        missing = sorted(REQUIRED_GATE_KEYS - set(gate))
        extra = sorted(set(gate) - REQUIRED_GATE_KEYS)
        if missing or extra:
            findings.append({"gate": gate.get("id", idx), "missing": missing, "extra": extra})
        if not isinstance(gate.get("id"), str) or not _SLUG.fullmatch(gate["id"]):
            findings.append({"gate": gate.get("id", idx), "rule": "gate_id_slug", "actual": gate.get("id")})
        if not isinstance(gate.get("blocks"), list) or not gate.get("blocks"):
            findings.append({"gate": gate.get("id", idx), "rule": "gate_blocks_non_empty_list", "actual": gate.get("blocks")})
    duplicates = sorted({item for item in ids if ids.count(item) > 1})
    if duplicates:
        findings.append({"rule": "readiness_gate_ids_unique", "expected": [], "actual": duplicates})
    return findings


def _first_phase_drift(doc: dict[str, Any]) -> list[dict[str, Any]]:
    readiness = doc.get("readiness") if isinstance(doc.get("readiness"), dict) else {}
    phases = readiness.get("first_build_phases") if isinstance(readiness.get("first_build_phases"), list) else []
    findings: list[dict[str, Any]] = []
    ids: list[Any] = []
    for idx, phase in enumerate(phases):
        if not isinstance(phase, dict):
            findings.append({"phase": idx, "rule": "phase_object", "actual": type(phase).__name__})
            continue
        ids.append(phase.get("id"))
        missing = sorted(REQUIRED_PHASE_KEYS - set(phase))
        extra = sorted(set(phase) - REQUIRED_PHASE_KEYS)
        if missing or extra:
            findings.append({"phase": phase.get("id", idx), "missing": missing, "extra": extra})
        if not isinstance(phase.get("id"), str) or not _SLUG.fullmatch(phase["id"]):
            findings.append({"phase": phase.get("id", idx), "rule": "phase_id_slug", "actual": phase.get("id")})
        if phase.get("ready_for_public_scoring") is not False:
            findings.append({
                "phase": phase.get("id", idx),
                "rule": "public_scoring_blocked",
                "expected": False,
                "actual": phase.get("ready_for_public_scoring"),
            })
        if phase.get("ready_for_training_use") is not False:
            findings.append({
                "phase": phase.get("id", idx),
                "rule": "training_use_blocked",
                "expected": False,
                "actual": phase.get("ready_for_training_use"),
            })
        if phase.get("ready_for_worker_facing_use") is not False:
            findings.append({
                "phase": phase.get("id", idx),
                "rule": "worker_facing_use_blocked",
                "expected": False,
                "actual": phase.get("ready_for_worker_facing_use"),
            })
    duplicates = sorted({item for item in ids if ids.count(item) > 1})
    if duplicates:
        findings.append({"rule": "first_build_phase_ids_unique", "expected": [], "actual": duplicates})
    return findings


def _summary_count_mismatches(doc: dict[str, Any]) -> list[dict[str, Any]]:
    summary = doc.get("summary") if isinstance(doc.get("summary"), dict) else {}
    scope = doc.get("scope") if isinstance(doc.get("scope"), dict) else {}
    readiness = doc.get("readiness") if isinstance(doc.get("readiness"), dict) else {}
    links = doc.get("existing_pipeline_links") if isinstance(doc.get("existing_pipeline_links"), dict) else {}
    pairs = [
        ("primary_seed_domain_count", len(scope.get("primary_seed_domains") or [])),
        ("registered_seed_domain_count", len(links.get("registered_seed_domains") or [])),
        ("candidate_pattern_count", len(scope.get("candidate_pattern_ids") or [])),
        ("regulatory_candidates_found_count", len(links.get("regulatory_candidates_found") or [])),
        ("target_jurisdiction_family_count", len(scope.get("target_jurisdiction_families") or [])),
        ("benchmark_axis_count", len(scope.get("benchmark_axes") or [])),
        ("source_admission_rule_count", len(scope.get("source_admission_rules") or [])),
        ("scored_capability_count", len(scope.get("scored_capabilities") or [])),
        ("readiness_gate_count", len(readiness.get("gates") or [])),
        ("first_build_phase_count", len(readiness.get("first_build_phases") or [])),
    ]
    return [
        {"summary_key": key, "expected": expected, "actual": summary.get(key)}
        for key, expected in pairs
        if summary.get(key) != expected
    ]


def _linkage_drift(doc: dict[str, Any]) -> list[dict[str, Any]]:
    scope = doc.get("scope") if isinstance(doc.get("scope"), dict) else {}
    links = doc.get("existing_pipeline_links") if isinstance(doc.get("existing_pipeline_links"), dict) else {}
    primary = set(scope.get("primary_seed_domains") or [])
    candidates = set(scope.get("candidate_pattern_ids") or [])
    registered = set(links.get("registered_seed_domains") or [])
    missing_seed = set(links.get("missing_seed_domains") or [])
    found = set(links.get("regulatory_candidates_found") or [])
    missing_candidates = set(links.get("missing_candidate_patterns") or [])
    findings: list[dict[str, Any]] = []
    if registered | missing_seed != primary or registered & missing_seed:
        findings.append({
            "rule": "seed_domain_partition",
            "expected": sorted(primary),
            "actual": {
                "registered_seed_domains": sorted(registered),
                "missing_seed_domains": sorted(missing_seed),
            },
        })
    if found | missing_candidates != candidates or found & missing_candidates:
        findings.append({
            "rule": "candidate_pattern_partition",
            "expected": sorted(candidates),
            "actual": {
                "regulatory_candidates_found": sorted(found),
                "missing_candidate_patterns": sorted(missing_candidates),
            },
        })
    if missing_seed:
        findings.append({"rule": "no_missing_seed_domains", "expected": [], "actual": sorted(missing_seed)})
    if missing_candidates:
        findings.append({"rule": "no_missing_candidate_patterns", "expected": [], "actual": sorted(missing_candidates)})
    return findings


def _readiness_drift(doc: dict[str, Any]) -> list[str]:
    findings: list[str] = []
    summary = doc.get("summary") if isinstance(doc.get("summary"), dict) else {}
    readiness = doc.get("readiness") if isinstance(doc.get("readiness"), dict) else {}
    if summary.get("safe_for_project_planning") is not True:
        findings.append("summary.safe_for_project_planning")
    if readiness.get("ready_for_research_planning") is not True:
        findings.append("readiness.ready_for_research_planning")
    for key in READY_FLAG_KEYS:
        if summary.get(key) is not False and key in summary:
            findings.append(f"summary.{key}")
        if readiness.get(key) is not False:
            findings.append(f"readiness.{key}")
    phases = readiness.get("first_build_phases") if isinstance(readiness.get("first_build_phases"), list) else []
    for idx, phase in enumerate(phases):
        if not isinstance(phase, dict):
            findings.append(f"readiness.first_build_phases[{idx}]")
            continue
        if phase.get("ready_for_public_scoring") is not False:
            findings.append(f"readiness.first_build_phases[{idx}].ready_for_public_scoring")
        if phase.get("ready_for_training_use") is not False:
            findings.append(f"readiness.first_build_phases[{idx}].ready_for_training_use")
        if phase.get("ready_for_worker_facing_use") is not False:
            findings.append(f"readiness.first_build_phases[{idx}].ready_for_worker_facing_use")
    return findings


def _path_hygiene_drift(doc: dict[str, Any]) -> list[dict[str, Any]]:
    findings: list[dict[str, Any]] = []
    meta = doc.get("_meta") if isinstance(doc.get("_meta"), dict) else {}
    readiness = doc.get("readiness") if isinstance(doc.get("readiness"), dict) else {}
    phases = readiness.get("first_build_phases") if isinstance(readiness.get("first_build_phases"), list) else []
    path_values: list[tuple[str, Any]] = [
        ("_meta.source_config", meta.get("source_config")),
        ("_meta.registry_path", meta.get("registry_path")),
        ("_meta.regulatory_catalog_path", meta.get("regulatory_catalog_path")),
    ]
    path_values.extend(
        (f"readiness.first_build_phases[{idx}].output", phase.get("output"))
        for idx, phase in enumerate(phases)
        if isinstance(phase, dict)
    )
    for path, value in path_values:
        if not isinstance(value, str):
            findings.append({"path": path, "rule": "string_path", "actual": type(value).__name__})
            continue
        if (
            _URL.search(value)
            or "\\" in value
            or value.startswith("/")
            or value.startswith("~/")
            or value.startswith("../")
            or "/../" in value
            or _WINDOWS_ABSOLUTE_PATH.search(value)
        ):
            findings.append({"path": path, "rule": "repo_relative_path", "actual": value})
    return findings


def _privacy_scan_drift(doc: dict[str, Any]) -> dict[str, Any]:
    recorded = doc.get("privacy_scan") if isinstance(doc.get("privacy_scan"), dict) else {}
    fresh = project_plan_builder._scan_privacy(doc)
    return {
        "recorded_ok": recorded.get("ok"),
        "recorded_counts": recorded.get("counts"),
        "fresh_ok": fresh.get("ok"),
        "fresh_counts": fresh.get("counts"),
    }


def _current_reference(
    *,
    config_path: pathlib.Path,
    registry_path: pathlib.Path,
    regulatory_catalog_path: pathlib.Path,
) -> dict[str, Any]:
    config = project_plan_builder._load_json(config_path)
    if config is None:
        raise ValueError(f"unreadable global protections project config: {config_path}")
    registry = project_plan_builder._load_json(registry_path)
    catalog = project_plan_builder._load_json(regulatory_catalog_path)
    return project_plan_builder.build_project_plan(
        config,
        config_path=config_path,
        registry=registry,
        regulatory_catalog=catalog,
        registry_path=registry_path,
        regulatory_catalog_path=regulatory_catalog_path,
    )


def _comparable_sections(doc: dict[str, Any]) -> dict[str, Any]:
    return {
        "project": doc.get("project"),
        "scope": doc.get("scope"),
        "readiness": doc.get("readiness"),
        "existing_pipeline_links": doc.get("existing_pipeline_links"),
        "summary": doc.get("summary"),
        "checks": doc.get("checks"),
        "privacy_scan": doc.get("privacy_scan"),
        "issues": doc.get("issues"),
    }


def validate_project_plan(
    doc: Any,
    *,
    plan_path: pathlib.Path | None = None,
    config_path: pathlib.Path = project_plan_builder.CONFIG,
    registry_path: pathlib.Path = project_plan_builder.REGISTRY,
    regulatory_catalog_path: pathlib.Path = project_plan_builder.REGULATORY_CATALOG,
    compare_current_chain: bool = True,
) -> dict[str, Any]:
    if not isinstance(doc, dict):
        checks = [_check("plan_is_object", False, expected="object", actual=type(doc).__name__)]
        failed = _failed_ids(checks)
        return {
            "_meta": {
                "schema_version": "global_protections_project_plan_validation.v1",
                "source_plan_path": _display_path(plan_path) if plan_path else "n/a",
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
    project = doc.get("project") if isinstance(doc.get("project"), dict) else {}
    encoded = json.dumps(doc, ensure_ascii=False)
    disallowed = [term for term in DISALLOWED_TERMS if term in encoded]
    embedded = _embedded_check_drift(doc.get("checks"))
    privacy = _privacy_scan_drift(doc)
    current = (
        _current_reference(
            config_path=config_path,
            registry_path=registry_path,
            regulatory_catalog_path=regulatory_catalog_path,
        )
        if compare_current_chain
        else None
    )
    current_sections = _comparable_sections(current) if current else None
    checks = [
        _check("top_level_and_section_shape", not _shape_drift(doc), expected=[], actual=_shape_drift(doc)),
        _check(
            "project_status_is_propose_only",
            project.get("status") == "propose_only",
            expected="propose_only",
            actual=project.get("status"),
        ),
        _check("readiness_gate_shape", not _readiness_gate_drift(doc), expected=[], actual=_readiness_gate_drift(doc)),
        _check("first_build_phase_shape", not _first_phase_drift(doc), expected=[], actual=_first_phase_drift(doc)),
        _check(
            "summary_counts_match_sections",
            not _summary_count_mismatches(doc),
            expected=[],
            actual=_summary_count_mismatches(doc),
        ),
        _check("seed_and_candidate_links_complete", not _linkage_drift(doc), expected=[], actual=_linkage_drift(doc)),
        _check(
            "embedded_checks_all_ok",
            not embedded["failed"] and not embedded["missing_required"],
            expected={"failed": [], "missing_required": []},
            actual=embedded,
        ),
        _check("all_downstream_readiness_flags_blocked", not _readiness_drift(doc), expected=[], actual=_readiness_drift(doc)),
        _check("phase_output_paths_are_repo_relative", not _path_hygiene_drift(doc), expected=[], actual=_path_hygiene_drift(doc)),
        _check(
            "privacy_scan_ok",
            privacy["recorded_ok"] is True and privacy["fresh_ok"] is True,
            expected={"recorded_ok": True, "fresh_ok": True},
            actual=privacy,
        ),
        _check("plan_contains_no_disallowed_text", not disallowed, expected=[], actual=disallowed),
        _check("issues_empty", doc.get("issues") == {}, expected={}, actual=doc.get("issues")),
    ]
    if compare_current_chain:
        checks.append(
            _check(
                "plan_matches_current_chain",
                _comparable_sections(doc) == current_sections,
                expected=current_sections,
                actual=_comparable_sections(doc),
            )
        )
    failed = _failed_ids(checks)
    return {
        "_meta": {
            "schema_version": "global_protections_project_plan_validation.v1",
            "source_plan_path": _display_path(plan_path) if plan_path else "n/a",
            "project_config": _display_path(config_path),
            "registry_path": _display_path(registry_path),
            "regulatory_catalog_path": _display_path(regulatory_catalog_path),
            "compare_current_chain": compare_current_chain,
        },
        "summary": {
            "valid": not failed,
            "check_count": len(checks),
            "failed_check_count": len(failed),
            "failed_check_ids": failed,
            "project_id": project.get("project_id"),
            "safe_for_project_planning": summary.get("safe_for_project_planning"),
            "primary_seed_domain_count": summary.get("primary_seed_domain_count"),
            "registered_seed_domain_count": summary.get("registered_seed_domain_count"),
            "candidate_pattern_count": summary.get("candidate_pattern_count"),
            "regulatory_candidates_found_count": summary.get("regulatory_candidates_found_count"),
            "readiness_gate_count": summary.get("readiness_gate_count"),
            "first_build_phase_count": summary.get("first_build_phase_count"),
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
        "# Global Protections Project Plan Validation",
        "",
        "This read-only report validates the saved sister-project plan before downstream builders trust it.",
        "",
        "## Summary",
        "",
        "| Metric | Value |",
        "|---|---:|",
        f"| Valid | {str(bool(summary['valid'])).lower()} |",
        f"| Checks | {summary['check_count']} |",
        f"| Failed checks | {summary['failed_check_count']} |",
        f"| Project ID | {_md_cell(summary.get('project_id'))} |",
        f"| Safe for project planning | {str(bool(summary.get('safe_for_project_planning'))).lower()} |",
        f"| Primary seed domains | {_md_cell(summary.get('primary_seed_domain_count'))} |",
        f"| Registered seed domains | {_md_cell(summary.get('registered_seed_domain_count'))} |",
        f"| Candidate patterns | {_md_cell(summary.get('candidate_pattern_count'))} |",
        f"| Regulatory candidates found | {_md_cell(summary.get('regulatory_candidates_found_count'))} |",
        f"| Readiness gates | {_md_cell(summary.get('readiness_gate_count'))} |",
        f"| First build phases | {_md_cell(summary.get('first_build_phase_count'))} |",
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
    ap.add_argument("--config", type=pathlib.Path, default=project_plan_builder.CONFIG)
    ap.add_argument("--registry", type=pathlib.Path, default=project_plan_builder.REGISTRY)
    ap.add_argument("--regulatory-catalog", type=pathlib.Path, default=project_plan_builder.REGULATORY_CATALOG)
    ap.add_argument("--out", type=pathlib.Path, default=OUT)
    ap.add_argument("--markdown-out", type=pathlib.Path, default=MD_OUT)
    ap.add_argument("--no-current-chain", action="store_true", help="skip comparison to the current generated chain")
    ap.add_argument("--validate", action="store_true", help="print the validation summary only; write nothing")
    args = ap.parse_args(argv)

    doc = _load_json(args.plan)
    if doc is None:
        print(f"[global-protections-project-plan-validation] unreadable plan: {args.plan}")
        return 1
    report = validate_project_plan(
        doc,
        plan_path=args.plan,
        config_path=args.config,
        registry_path=args.registry,
        regulatory_catalog_path=args.regulatory_catalog,
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
        "[global-protections-project-plan-validation] "
        f"valid={str(bool(summary['valid'])).lower()}; "
        f"failed={summary['failed_check_count']}/{summary['check_count']}; "
        f"ready_for_comparable_scoring={str(bool(summary['ready_for_comparable_scoring'])).lower()} -> {args.plan}"
    )
    return 0 if summary["valid"] else 1


if __name__ == "__main__":
    raise SystemExit(main())
