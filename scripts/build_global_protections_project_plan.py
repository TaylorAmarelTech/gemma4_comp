#!/usr/bin/env python3
"""Build a source-gated plan for the global protections sister project.

The source config is a charter, not legal content. This builder validates the
charter, links it to the existing worker-protections seed domain and adjacent
regulatory miss-pattern catalog, and emits a compact non-mutating planning
artifact.

Offline + deterministic. No model, no network, no credits.

    python scripts/build_global_protections_project_plan.py
    python scripts/build_global_protections_project_plan.py --validate
"""
from __future__ import annotations

import argparse
import json
import pathlib
import re
from collections import Counter
from typing import Any

_ROOT = pathlib.Path(__file__).resolve().parents[1]
CONFIG = (
    _ROOT
    / "configs"
    / "duecare"
    / "benchmarks"
    / "sister_projects"
    / "global_protections_regulatory_benchmark.json"
)
REGISTRY = _ROOT / "configs" / "duecare" / "benchmarks" / "domains" / "registry.json"
REGULATORY_CATALOG = _ROOT / "configs" / "duecare" / "benchmarks" / "regulatory_miss_patterns.json"
OUT = _ROOT / "reports" / "benchmark" / "global_protections_project_plan.json"
MD_OUT = _ROOT / "reports" / "benchmark" / "global_protections_project_plan.md"

REQUIRED_FIELDS = frozenset({
    "project_id",
    "display_name",
    "status",
    "research_question",
    "primary_seed_domains",
    "candidate_pattern_ids",
    "target_jurisdiction_families",
    "benchmark_axes",
    "source_admission_rules",
    "scored_capabilities",
    "readiness_gates",
    "first_build_phases",
    "non_goals",
})
ALLOWED_FIELDS = REQUIRED_FIELDS | frozenset({"_meta"})
REQUIRED_GATE_FIELDS = frozenset({"id", "description", "blocks"})
REQUIRED_PHASE_FIELDS = frozenset({
    "id",
    "description",
    "output",
    "ready_for_public_scoring",
    "ready_for_training_use",
    "ready_for_worker_facing_use",
})
SAFE_STATUS = frozenset({"propose_only"})
SENSITIVE_FIELD_NAMES = frozenset({
    "name",
    "names",
    "phone",
    "email",
    "contact",
    "contacts",
    "address",
    "addresses",
    "case_text",
    "case_file",
    "worker",
    "workers",
    "complainant",
    "complainants",
    "raw_text",
    "prompt_text",
    "source_url",
    "url",
})
_SLUG = re.compile(r"^[a-z][a-z0-9_]{2,80}$")
_EMAIL = re.compile(r"\b[\w.+-]+@[\w-]+\.[\w.-]+\b", re.I)
_PHONE = re.compile(r"\+?\d[\d\s().\-]{8,}\d")
_LONG_DIGITS = re.compile(r"(?<!\d)\d{8,}(?!\d)")
_URL = re.compile(r"\b(?:https?://|www\.)", re.I)
_ISO_DATE = re.compile(r"^\d{4}-\d{2}-\d{2}$")
_LOCAL_PATH = re.compile(
    r"(?:[A-Za-z]:[\\/]|\\\\|/(?:Users|home|tmp|var|mnt|private|Volumes)(?:/|$)|~[\\/])",
    re.I,
)


def _display_path(path: pathlib.Path) -> str:
    try:
        return path.relative_to(_ROOT).as_posix()
    except ValueError:
        return path.as_posix()


def _has_sensitive_text(text: str) -> bool:
    if _ISO_DATE.fullmatch(text.strip()):
        return False
    return bool(
        _EMAIL.search(text)
        or _PHONE.search(text)
        or _LONG_DIGITS.search(text)
        or _URL.search(text)
        or _LOCAL_PATH.search(text)
        or "\\" in text
    )


def _safe_text(value: Any, *, fallback: str = "unknown", max_len: int = 520) -> str:
    if not isinstance(value, str):
        return fallback
    text = " ".join(value.strip().split())
    if not text or len(text) > max_len or _has_sensitive_text(text):
        return fallback
    try:
        text.encode("ascii")
    except UnicodeEncodeError:
        return fallback
    return text


def _safe_slug(value: Any) -> str:
    if not isinstance(value, str):
        return "unknown"
    text = value.strip()
    return text if _SLUG.fullmatch(text) else "unknown"


def _safe_list(value: Any, *, max_len: int = 520) -> list[str]:
    if not isinstance(value, list):
        return []
    return [
        _safe_text(item, max_len=max_len)
        for item in value
        if isinstance(item, str) and _safe_text(item, max_len=max_len) != "unknown"
    ]


def _scan_privacy(value: Any, *, path: str = "$") -> dict[str, Any]:
    findings: dict[str, list[str]] = {
        "sensitive_field_paths": [],
        "email_like_paths": [],
        "phone_like_paths": [],
        "long_digit_paths": [],
        "url_like_paths": [],
        "local_path_like_paths": [],
    }

    def walk(item: Any, current: str) -> None:
        if isinstance(item, dict):
            for key, child in item.items():
                child_path = f"{current}.{key}"
                if str(key).lower() in SENSITIVE_FIELD_NAMES:
                    findings["sensitive_field_paths"].append(child_path)
                walk(child, child_path)
        elif isinstance(item, list):
            for idx, child in enumerate(item):
                walk(child, f"{current}[{idx}]")
        elif isinstance(item, str):
            is_iso_date = bool(_ISO_DATE.fullmatch(item.strip()))
            if _EMAIL.search(item):
                findings["email_like_paths"].append(current)
            if _PHONE.search(item) and not is_iso_date:
                findings["phone_like_paths"].append(current)
            if _LONG_DIGITS.search(item):
                findings["long_digit_paths"].append(current)
            if _URL.search(item):
                findings["url_like_paths"].append(current)
            if _LOCAL_PATH.search(item) or "\\" in item:
                findings["local_path_like_paths"].append(current)

    walk(value, path)
    counts = {key.replace("_paths", ""): len(paths) for key, paths in findings.items()}
    findings["counts"] = counts
    findings["ok"] = not any(counts.values())
    return findings


def _load_json(path: pathlib.Path) -> dict[str, Any] | None:
    try:
        loaded = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError):
        return None
    return loaded if isinstance(loaded, dict) else None


def _list_field_issues(
    config: dict[str, Any],
    field: str,
    *,
    slug: bool = False,
    max_len: int = 520,
) -> list[str]:
    value = config.get(field)
    if not isinstance(value, list) or not value:
        return [f"{field}_empty_or_not_list"]
    issues: list[str] = []
    for item in value:
        if slug:
            if _safe_slug(item) == "unknown":
                issues.append(f"{field}_contains_unsafe_slug")
        elif not isinstance(item, str) or _safe_text(item, max_len=max_len) == "unknown":
            issues.append(f"{field}_contains_unsafe_text")
    return sorted(set(issues))


def _readiness_gate_issues(value: Any) -> list[str]:
    if not isinstance(value, list) or not value:
        return ["readiness_gates_empty_or_not_list"]
    issues: list[str] = []
    seen: set[str] = set()
    for raw in value:
        if not isinstance(raw, dict):
            issues.append("readiness_gate_not_object")
            continue
        missing = sorted(REQUIRED_GATE_FIELDS - set(raw))
        if missing:
            issues.append("readiness_gate_required_fields_missing")
        unknown = sorted(set(raw) - REQUIRED_GATE_FIELDS)
        if unknown:
            issues.append("readiness_gate_unexpected_fields")
        gate_id = raw.get("id")
        if _safe_slug(gate_id) == "unknown":
            issues.append("readiness_gate_id_not_safe_slug")
        elif gate_id in seen:
            issues.append("readiness_gate_id_duplicate")
        else:
            seen.add(gate_id)
        if _safe_text(raw.get("description")) == "unknown":
            issues.append("readiness_gate_description_unsafe")
        issues.extend(_list_field_issues(raw, "blocks"))
    return sorted(set(issues))


def _phase_issues(value: Any) -> list[str]:
    if not isinstance(value, list) or not value:
        return ["first_build_phases_empty_or_not_list"]
    issues: list[str] = []
    seen: set[str] = set()
    for raw in value:
        if not isinstance(raw, dict):
            issues.append("first_build_phase_not_object")
            continue
        missing = sorted(REQUIRED_PHASE_FIELDS - set(raw))
        if missing:
            issues.append("first_build_phase_required_fields_missing")
        unknown = sorted(set(raw) - REQUIRED_PHASE_FIELDS)
        if unknown:
            issues.append("first_build_phase_unexpected_fields")
        phase_id = raw.get("id")
        if _safe_slug(phase_id) == "unknown":
            issues.append("first_build_phase_id_not_safe_slug")
        elif phase_id in seen:
            issues.append("first_build_phase_id_duplicate")
        else:
            seen.add(phase_id)
        for field in ("description", "output"):
            if _safe_text(raw.get(field)) == "unknown":
                issues.append(f"first_build_phase_{field}_unsafe")
        if raw.get("ready_for_public_scoring") is not False:
            issues.append("first_build_phase_public_scoring_not_blocked")
        if raw.get("ready_for_training_use") is not False:
            issues.append("first_build_phase_training_use_not_blocked")
        if raw.get("ready_for_worker_facing_use") is not False:
            issues.append("first_build_phase_worker_use_not_blocked")
    return sorted(set(issues))


def _config_issues(config: Any) -> Counter[str]:
    issues: Counter[str] = Counter()
    if not isinstance(config, dict):
        issues["config_not_object"] += 1
        return issues
    missing = sorted(REQUIRED_FIELDS - set(config))
    if missing:
        issues["required_fields_missing"] += 1
    unknown = sorted(set(config) - ALLOWED_FIELDS)
    if unknown:
        issues["unexpected_fields"] += 1
    if any(str(key).lower() in SENSITIVE_FIELD_NAMES for key in config):
        issues["sensitive_top_level_fields_present"] += 1
    if _safe_slug(config.get("project_id")) == "unknown":
        issues["project_id_not_safe_slug"] += 1
    if _safe_text(config.get("display_name")) == "unknown":
        issues["display_name_unsafe"] += 1
    if config.get("status") not in SAFE_STATUS:
        issues["status_not_propose_only"] += 1
    if _safe_text(config.get("research_question"), max_len=700) == "unknown":
        issues["research_question_unsafe"] += 1
    for field in (
        "target_jurisdiction_families",
        "benchmark_axes",
        "source_admission_rules",
        "scored_capabilities",
        "non_goals",
    ):
        for issue in _list_field_issues(config, field, max_len=700):
            issues[issue] += 1
    for field in ("primary_seed_domains", "candidate_pattern_ids"):
        for issue in _list_field_issues(config, field, slug=True):
            issues[issue] += 1
    for issue in _readiness_gate_issues(config.get("readiness_gates")):
        issues[issue] += 1
    for issue in _phase_issues(config.get("first_build_phases")):
        issues[issue] += 1
    privacy_scan = _scan_privacy(config)
    if privacy_scan.get("ok") is not True:
        issues["privacy_scan_not_ok"] += 1
    return issues


def _safe_gate(raw: Any) -> dict[str, Any]:
    if not isinstance(raw, dict):
        return {"id": "unknown", "description": "unknown", "blocks": []}
    return {
        "id": _safe_slug(raw.get("id")),
        "description": _safe_text(raw.get("description")),
        "blocks": _safe_list(raw.get("blocks")),
    }


def _safe_phase(raw: Any) -> dict[str, Any]:
    if not isinstance(raw, dict):
        return {
            "id": "unknown",
            "description": "unknown",
            "output": "unknown",
            "ready_for_public_scoring": False,
            "ready_for_training_use": False,
            "ready_for_worker_facing_use": False,
        }
    return {
        "id": _safe_slug(raw.get("id")),
        "description": _safe_text(raw.get("description")),
        "output": _safe_text(raw.get("output")),
        "ready_for_public_scoring": bool(raw.get("ready_for_public_scoring")),
        "ready_for_training_use": bool(raw.get("ready_for_training_use")),
        "ready_for_worker_facing_use": bool(raw.get("ready_for_worker_facing_use")),
    }


def _registry_domain_ids(registry: dict[str, Any] | None) -> set[str]:
    domains = registry.get("domains") if isinstance(registry, dict) else None
    return {str(key) for key in domains} if isinstance(domains, dict) else set()


def _regulatory_pattern_ids(catalog: dict[str, Any] | None) -> set[str]:
    patterns = catalog.get("patterns") if isinstance(catalog, dict) else None
    if not isinstance(patterns, list):
        return set()
    return {
        raw["id"]
        for raw in patterns
        if isinstance(raw, dict) and isinstance(raw.get("id"), str) and _SLUG.fullmatch(raw["id"])
    }


def _check(check_id: str, ok: bool, *, expected: Any, actual: Any) -> dict[str, Any]:
    return {
        "id": check_id,
        "ok": bool(ok),
        "expected": expected,
        "actual": actual,
    }


def build_project_plan(
    config: dict[str, Any],
    *,
    config_path: pathlib.Path = CONFIG,
    registry: dict[str, Any] | None = None,
    regulatory_catalog: dict[str, Any] | None = None,
    registry_path: pathlib.Path = REGISTRY,
    regulatory_catalog_path: pathlib.Path = REGULATORY_CATALOG,
) -> dict[str, Any]:
    """Return a sanitized, non-mutating project plan and readiness report."""
    issue_counts = _config_issues(config)
    primary_domains = [_safe_slug(item) for item in config.get("primary_seed_domains", []) if _safe_slug(item) != "unknown"]
    candidate_pattern_ids = [
        _safe_slug(item) for item in config.get("candidate_pattern_ids", []) if _safe_slug(item) != "unknown"
    ]
    registry = registry if registry is not None else _load_json(registry_path)
    regulatory_catalog = (
        regulatory_catalog if regulatory_catalog is not None else _load_json(regulatory_catalog_path)
    )
    registry_ids = _registry_domain_ids(registry)
    catalog_ids = _regulatory_pattern_ids(regulatory_catalog)
    registered_seed_domains = sorted(set(primary_domains) & registry_ids)
    missing_seed_domains = sorted(set(primary_domains) - registry_ids)
    regulatory_candidates_found = sorted(set(candidate_pattern_ids) & catalog_ids)
    missing_candidate_patterns = sorted(set(candidate_pattern_ids) - catalog_ids)
    if missing_seed_domains:
        issue_counts["primary_seed_domain_not_registered"] += len(missing_seed_domains)
    if missing_candidate_patterns:
        issue_counts["candidate_pattern_missing_from_catalog"] += len(missing_candidate_patterns)

    gates = [_safe_gate(raw) for raw in config.get("readiness_gates", []) if isinstance(raw, dict)]
    phases = [_safe_phase(raw) for raw in config.get("first_build_phases", []) if isinstance(raw, dict)]
    ready_for_public_scoring = any(phase["ready_for_public_scoring"] for phase in phases)
    ready_for_training_use = any(phase["ready_for_training_use"] for phase in phases)
    ready_for_worker_facing_use = any(phase["ready_for_worker_facing_use"] for phase in phases)
    privacy_scan = _scan_privacy(config)
    checks = [
        _check("privacy_scan_ok", privacy_scan.get("ok") is True, expected=True, actual=privacy_scan.get("ok")),
        _check(
            "status_is_propose_only",
            config.get("status") == "propose_only",
            expected="propose_only",
            actual=_safe_text(config.get("status")),
        ),
        _check(
            "primary_seed_domain_registered",
            bool(registered_seed_domains) and not missing_seed_domains,
            expected=primary_domains,
            actual=registered_seed_domains,
        ),
        _check(
            "regulatory_candidates_found",
            len(regulatory_candidates_found) == len(candidate_pattern_ids),
            expected=len(candidate_pattern_ids),
            actual=len(regulatory_candidates_found),
        ),
        _check(
            "source_admission_rules_present",
            len(config.get("source_admission_rules", [])) >= 5,
            expected="at least 5",
            actual=len(config.get("source_admission_rules", [])) if isinstance(config.get("source_admission_rules"), list) else 0,
        ),
        _check(
            "readiness_gates_present",
            len(gates) >= 5,
            expected="at least 5",
            actual=len(gates),
        ),
        _check(
            "public_scoring_blocked",
            ready_for_public_scoring is False,
            expected=False,
            actual=ready_for_public_scoring,
        ),
        _check(
            "training_use_blocked",
            ready_for_training_use is False,
            expected=False,
            actual=ready_for_training_use,
        ),
        _check(
            "worker_facing_use_blocked",
            ready_for_worker_facing_use is False,
            expected=False,
            actual=ready_for_worker_facing_use,
        ),
    ]
    safe_for_project_planning = not issue_counts
    return {
        "_meta": {
            "schema_version": "global_protections_project_plan.v1",
            "source_config": _display_path(config_path),
            "registry_path": _display_path(registry_path),
            "regulatory_catalog_path": _display_path(regulatory_catalog_path),
            "status": (
                "source-gated sister-project planning artifact; not legal advice, not source "
                "verification, not prompt generation, and not comparable benchmark evidence"
            ),
        },
        "project": {
            "project_id": _safe_slug(config.get("project_id")),
            "display_name": _safe_text(config.get("display_name")),
            "status": _safe_text(config.get("status")),
            "research_question": _safe_text(config.get("research_question"), max_len=700),
        },
        "scope": {
            "primary_seed_domains": primary_domains,
            "candidate_pattern_ids": candidate_pattern_ids,
            "target_jurisdiction_families": _safe_list(config.get("target_jurisdiction_families"), max_len=700),
            "benchmark_axes": _safe_list(config.get("benchmark_axes"), max_len=700),
            "source_admission_rules": _safe_list(config.get("source_admission_rules"), max_len=700),
            "scored_capabilities": _safe_list(config.get("scored_capabilities"), max_len=700),
            "non_goals": _safe_list(config.get("non_goals"), max_len=700),
        },
        "readiness": {
            "gates": gates,
            "first_build_phases": phases,
            "ready_for_research_planning": safe_for_project_planning,
            "ready_for_prompt_generation": False,
            "ready_for_training_use": False,
            "ready_for_public_claims": False,
            "ready_for_worker_facing_use": False,
            "ready_for_comparable_scoring": False,
            "policy": (
                "The project can plan source curation only. Prompt expansion, training use, public "
                "claims, worker-facing use, and comparable scoring remain blocked until source "
                "coverage, privacy review, expert review, and a source-verified grounding layer pass."
            ),
        },
        "existing_pipeline_links": {
            "registered_seed_domains": registered_seed_domains,
            "missing_seed_domains": missing_seed_domains,
            "regulatory_candidates_found": regulatory_candidates_found,
            "missing_candidate_patterns": missing_candidate_patterns,
            "source_gated_chains": [
                "scripts/build_domain_curation_bundle.py --domain developing_country_worker_protections",
                "scripts/build_regulatory_curation_bundle.py --write-components",
            ],
        },
        "summary": {
            "safe_for_project_planning": safe_for_project_planning,
            "primary_seed_domain_count": len(primary_domains),
            "registered_seed_domain_count": len(registered_seed_domains),
            "candidate_pattern_count": len(candidate_pattern_ids),
            "regulatory_candidates_found_count": len(regulatory_candidates_found),
            "target_jurisdiction_family_count": len(config.get("target_jurisdiction_families", []))
            if isinstance(config.get("target_jurisdiction_families"), list)
            else 0,
            "benchmark_axis_count": len(config.get("benchmark_axes", []))
            if isinstance(config.get("benchmark_axes"), list)
            else 0,
            "source_admission_rule_count": len(config.get("source_admission_rules", []))
            if isinstance(config.get("source_admission_rules"), list)
            else 0,
            "scored_capability_count": len(config.get("scored_capabilities", []))
            if isinstance(config.get("scored_capabilities"), list)
            else 0,
            "readiness_gate_count": len(gates),
            "first_build_phase_count": len(phases),
            "ready_for_comparable_scoring": False,
        },
        "checks": checks,
        "privacy_scan": privacy_scan,
        "issues": {key: issue_counts[key] for key in sorted(issue_counts)},
    }


def _md_cell(value: Any) -> str:
    text = str(value if value is not None else "")
    return text.replace("|", "\\|").replace("\n", " ").strip()


def build_markdown_report(doc: dict[str, Any]) -> str:
    """Render a compact Markdown project plan."""
    project = doc["project"]
    summary = doc["summary"]
    readiness = doc["readiness"]
    lines: list[str] = [
        f"# {_md_cell(project['display_name'])}",
        "",
        (
            "This is a source-gated sister-project planning artifact. It is not legal advice, "
            "not source verification, not prompt generation, and not comparable benchmark evidence."
        ),
        "",
        "## Research Question",
        "",
        _md_cell(project["research_question"]),
        "",
        "## Summary",
        "",
        "| Metric | Value |",
        "|---|---:|",
        f"| Safe for project planning | {str(bool(summary['safe_for_project_planning'])).lower()} |",
        f"| Primary seed domains | {summary['primary_seed_domain_count']} |",
        f"| Registered seed domains | {summary['registered_seed_domain_count']} |",
        f"| Candidate patterns | {summary['candidate_pattern_count']} |",
        f"| Regulatory candidates found | {summary['regulatory_candidates_found_count']} |",
        f"| Jurisdiction families | {summary['target_jurisdiction_family_count']} |",
        f"| Benchmark axes | {summary['benchmark_axis_count']} |",
        f"| Source admission rules | {summary['source_admission_rule_count']} |",
        f"| Scored capabilities | {summary['scored_capability_count']} |",
        f"| Readiness gates | {summary['readiness_gate_count']} |",
        f"| First build phases | {summary['first_build_phase_count']} |",
        f"| Ready for comparable scoring | {str(bool(summary['ready_for_comparable_scoring'])).lower()} |",
        "",
        "## Benchmark Axes",
        "",
    ]
    for axis in doc["scope"]["benchmark_axes"]:
        lines.append(f"- {_md_cell(axis)}")
    lines.extend(["", "## Source Admission Rules", ""])
    for rule in doc["scope"]["source_admission_rules"]:
        lines.append(f"- {_md_cell(rule)}")
    lines.extend(["", "## Readiness Gates", "", "| Gate | Blocks |", "|---|---|"])
    for gate in readiness["gates"]:
        lines.append(f"| `{_md_cell(gate['id'])}` | {_md_cell(', '.join(gate['blocks']))} |")
    lines.extend(["", "## Existing Pipeline Links", ""])
    for key, values in doc["existing_pipeline_links"].items():
        if isinstance(values, list):
            lines.append(f"- `{_md_cell(key)}`: {len(values)}")
    lines.extend(["", "## Checks", "", "| Check | OK | Expected | Actual |", "|---|---:|---|---|"])
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
        readiness["policy"],
        "",
    ])
    if doc["issues"]:
        lines.extend(["## Issues", ""])
        for key, count in doc["issues"].items():
            lines.append(f"- `{key}`: {count}")
        lines.append("")
    return "\n".join(lines)


def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--config", type=pathlib.Path, default=CONFIG)
    ap.add_argument("--registry", type=pathlib.Path, default=REGISTRY)
    ap.add_argument("--regulatory-catalog", type=pathlib.Path, default=REGULATORY_CATALOG)
    ap.add_argument("--out", type=pathlib.Path, default=OUT)
    ap.add_argument("--markdown-out", type=pathlib.Path, default=MD_OUT)
    ap.add_argument("--validate", action="store_true", help="print the summary only; write nothing")
    args = ap.parse_args(argv)

    config = _load_json(args.config)
    if config is None:
        print(f"[global-protections-project-plan] unreadable config: {args.config}")
        return 1
    registry = _load_json(args.registry)
    catalog = _load_json(args.regulatory_catalog)
    doc = build_project_plan(
        config,
        config_path=args.config,
        registry=registry,
        regulatory_catalog=catalog,
        registry_path=args.registry,
        regulatory_catalog_path=args.regulatory_catalog,
    )
    if args.validate:
        print(json.dumps({"summary": doc["summary"], "issues": doc["issues"]}, indent=2, ensure_ascii=False))
        return 0 if doc["summary"]["safe_for_project_planning"] else 1
    if not doc["summary"]["safe_for_project_planning"]:
        print(json.dumps({"summary": doc["summary"], "issues": doc["issues"]}, indent=2, ensure_ascii=False))
        print("[global-protections-project-plan] config is unsafe; refusing to write plan")
        return 1

    args.out.parent.mkdir(parents=True, exist_ok=True)
    args.markdown_out.parent.mkdir(parents=True, exist_ok=True)
    args.out.write_text(json.dumps(doc, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
    args.markdown_out.write_text(build_markdown_report(doc) + "\n", encoding="utf-8")
    print(
        "[global-protections-project-plan] "
        f"safe_for_project_planning={str(bool(doc['summary']['safe_for_project_planning'])).lower()}; "
        f"{doc['summary']['registered_seed_domain_count']} seed domains; "
        f"{doc['summary']['regulatory_candidates_found_count']} regulatory candidates; "
        f"ready_for_comparable_scoring=false -> {args.out}"
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
