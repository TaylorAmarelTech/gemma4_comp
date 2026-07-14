#!/usr/bin/env python3
"""Validate the offline sister-project planning artifacts.

This read-only validator summarizes and checks the developing-country worker
protections seed plus the Global Protections Regulatory Benchmark charter. It
keeps the sister project in planning mode until source-object, privacy, expert,
and grounding gates are satisfied elsewhere.

The report is aggregate-only: it does not print source URLs, prompt text, raw
case text, or private identifiers.
"""
from __future__ import annotations

import argparse
import json
import pathlib
import re
from typing import Any

ROOT = pathlib.Path(__file__).resolve().parents[1]
SISTER_DIR = ROOT / "configs" / "duecare" / "benchmarks" / "sister_projects"
DOMAIN_DIR = (
    ROOT
    / "configs"
    / "duecare"
    / "benchmarks"
    / "domains"
    / "developing_country_worker_protections"
)
PROJECT_CONFIG = SISTER_DIR / "global_protections_regulatory_benchmark.json"
JURISDICTION_PACKS = SISTER_DIR / "global_protections_jurisdiction_packs.json"
GROUNDING_SOURCES = DOMAIN_DIR / "grounding_sources.json"
SCHEME_PROMPTS = DOMAIN_DIR / "scheme_prompts.jsonl"

REQUIRED_REVIEW_GATES = frozenset({
    "source_object_coverage",
    "scope_resolution",
    "privacy_review",
    "expert_review",
    "grounding_layer",
})
PENDING_SOURCE_STATUSES = frozenset({
    "needs_source",
    "unsafe_without_archive",
})
KNOWN_SOURCE_STATUSES = frozenset({
    *PENDING_SOURCE_STATUSES,
    "verified_international_anchor",
})
CANONICAL_PROJECT_IDS = frozenset({
    "global_protections_regulatory_benchmark",
})
CANONICAL_GROUNDING_DOMAINS = frozenset({
    "developing_country_worker_protections",
})
KNOWN_PROJECT_STATUSES = frozenset({
    "propose_only",
})
KNOWN_PROMPT_ERROR_KINDS = frozenset({
    "FileNotFoundError",
    "invalid_error_shape",
    "JSONDecodeError",
    "OSError",
    "PermissionError",
    "prompt_rows_not_list",
    "row_not_object",
})
SOURCE_ADMISSION_RULE_CONCEPTS = {
    "local_law_claims_need_dated_source_objects": ["local-law claim", "dated source object"],
    "international_anchors_cannot_substitute_for_local_law": ["cannot substitute"],
    "public_complaint_lists_are_rejected": ["public complaint lists"],
    "privacy_or_private_identifier_rejection": ["names, contacts"],
    "expert_review": ["expert"],
    "informal_social_channel_handling": ["social-channel"],
    "complaint_path_limits": ["complaint"],
}
READINESS_GATE_BLOCK_CONCEPTS = {
    "public_claims": ["public claims"],
    "training_use": ["training use"],
    "comparable_scoring": ["comparable scoring"],
    "worker_facing_use": ["worker-facing use"],
}
SCORED_CAPABILITY_CONCEPTS = {
    "jurisdiction_selection": ["jurisdiction"],
    "local_law_international_anchor_separation": ["local law", "international anchors"],
    "ordinary_protection_detection": ["ordinary labour", "wage", "consumer protections"],
    "safe_remedy_privacy_routing": ["remedy", "private details", "retaliation risk"],
    "refuses_to_invent_volatile_claims": ["refuses to invent", "fee caps", "office names"],
}
_DATE = re.compile(r"^\d{4}-\d{2}-\d{2}$")
_EMAIL = re.compile(r"\b[\w.+-]+@[\w-]+\.[\w.-]+\b", re.I)
_PHONE = re.compile(r"\+?\d[\d\s().\-]{8,}\d")
_URL = re.compile(r"\b(?:https?://|https?:/|ftp:/+|s3:/+|file:/+|mailto:|www\.)", re.I)
_LONG_DIGITS = re.compile(r"(?<!\d)\d{8,}(?!\d)")
_LOCAL_PATH = re.compile(
    r"(?:"
    r"[A-Za-z]:[\\/]"
    r"|\\\\"
    r"|/(?:Users|home|tmp|var|mnt|private|Volumes|OneDrive|Documents|AppData)(?:/|$)"
    r"|(?:^|[\s\\/])(?:OneDrive|Documents|AppData|Local|Temp|tmp)(?:[\\/]|$)"
    r"|~[\\/]"
    r")",
    re.I,
)


def _load_json(path: pathlib.Path) -> tuple[Any, str]:
    try:
        return json.loads(path.read_text(encoding="utf-8")), ""
    except OSError as exc:
        detail = getattr(exc, "strerror", "") or "read failed"
        return None, f"{type(exc).__name__}: {detail}"
    except json.JSONDecodeError as exc:
        return None, f"JSONDecodeError: line {exc.lineno} column {exc.colno}"


def _load_jsonl(path: pathlib.Path) -> tuple[list[dict[str, Any]], list[dict[str, Any]]]:
    rows: list[dict[str, Any]] = []
    errors: list[dict[str, Any]] = []
    try:
        with path.open(encoding="utf-8") as fh:
            for line_number, line in enumerate(fh, 1):
                if not line.strip():
                    continue
                try:
                    row = json.loads(line)
                except json.JSONDecodeError as exc:
                    errors.append({"line": line_number, "error": type(exc).__name__})
                    continue
                if not isinstance(row, dict):
                    errors.append({"line": line_number, "error": "row_not_object"})
                    continue
                rows.append(row)
    except OSError as exc:
        errors.append({"line": None, "error": type(exc).__name__})
    return rows, errors


def _check(check_id: str, ok: bool, *, expected: Any, actual: Any) -> dict[str, Any]:
    return {
        "id": check_id,
        "ok": bool(ok),
        "expected": expected,
        "actual": actual,
    }


def _failed_ids(checks: list[dict[str, Any]]) -> list[str]:
    return [str(check["id"]) for check in checks if check.get("ok") is not True]


def _row_id_values(rows: Any) -> list[str]:
    if not isinstance(rows, list):
        return []
    return [
        row["id"] for row in rows
        if isinstance(row, dict) and isinstance(row.get("id"), str)
    ]


def _row_id_shape_issues(rows: Any, namespace: str) -> list[str]:
    if not isinstance(rows, list):
        return [f"{namespace}:rows_not_list"]
    issues: list[str] = []
    for index, row in enumerate(rows):
        if not isinstance(row, dict):
            issues.append(f"{namespace}:{index}:row_not_object")
            continue
        row_id = row.get("id")
        if not isinstance(row_id, str) or not row_id.strip():
            issues.append(f"{namespace}:{index}:id_not_string")
    return issues


def _string_values(values: Any) -> list[str]:
    if not isinstance(values, list):
        return []
    return [value for value in values if isinstance(value, str)]


def _duplicate_values(values: list[str]) -> list[str]:
    seen: set[str] = set()
    duplicates: set[str] = set()
    for value in values:
        if value in seen:
            duplicates.add(value)
        seen.add(value)
    return sorted(duplicates)


def _issue_count(values: Any) -> dict[str, int]:
    if not isinstance(values, (list, set, tuple)):
        return {"count": 0}
    return {"count": len(values)}


def _unique_issue_count(values: Any) -> dict[str, int]:
    if not isinstance(values, (list, set, tuple)):
        return {"count": 0}
    return {"count": len({str(value) for value in values})}


def _safe_prompt_errors(errors: Any) -> list[dict[str, Any]]:
    if errors is None:
        return []
    if not isinstance(errors, list):
        return [{"line": None, "error": "invalid_error_shape"}]
    safe_errors: list[dict[str, Any]] = []
    for error in errors:
        if not isinstance(error, dict):
            safe_errors.append({"line": None, "error": "invalid_error_shape"})
            continue
        line = error.get("line")
        error_kind = error.get("error")
        safe_errors.append({
            "line": line if isinstance(line, int) and not isinstance(line, bool) and line > 0 else None,
            "error": (
                error_kind
                if isinstance(error_kind, str)
                and error_kind in KNOWN_PROMPT_ERROR_KINDS
                else "invalid_or_unknown"
            ),
        })
    return safe_errors


def _coerce_prompt_rows(value: Any, errors: Any) -> tuple[list[Any], list[dict[str, Any]]]:
    safe_errors = _safe_prompt_errors(errors)
    if isinstance(value, list):
        return value, safe_errors
    return [value], [*safe_errors, {"line": None, "error": "prompt_rows_not_list"}]


def _known_or_custom(value: Any, known: frozenset[str]) -> str | None:
    if not isinstance(value, str):
        return None
    if value in known:
        return value
    return "custom_or_invalid"


def _privacy_issue_counts(value: Any, *, count_url_like: bool = True) -> dict[str, int]:
    counts = {
        "email_like": 0,
        "phone_like": 0,
        "url_like": 0,
        "local_path_like": 0,
        "long_digit_like": 0,
    }

    def scan_text(text: str) -> None:
        is_iso_date = bool(_DATE.fullmatch(text.strip()))
        if _EMAIL.search(text):
            counts["email_like"] += 1
        if _PHONE.search(text) and not is_iso_date:
            counts["phone_like"] += 1
        if count_url_like and _URL.search(text):
            counts["url_like"] += 1
        if _LOCAL_PATH.search(text) or "\\" in text:
            counts["local_path_like"] += 1
        if _LONG_DIGITS.search(text):
            counts["long_digit_like"] += 1

    def walk(item: Any) -> None:
        if isinstance(item, dict):
            for key, child in item.items():
                if isinstance(key, str):
                    scan_text(key)
                walk(child)
        elif isinstance(item, list):
            for child in item:
                walk(child)
        elif isinstance(item, str):
            scan_text(item)

    walk(value)
    return counts


def _privacy_issue_total(counts: dict[str, int]) -> int:
    return sum(counts.values())


def _duplicate_id_issues(
    *,
    project: Any,
    packs: Any,
    grounding: Any,
    prompt_rows: list[dict[str, Any]],
) -> list[str]:
    groups = {
        "project.primary_seed_domains": _string_values(
            project.get("primary_seed_domains", []) if isinstance(project, dict) else []
        ),
        "project.candidate_pattern_ids": _string_values(
            project.get("candidate_pattern_ids", []) if isinstance(project, dict) else []
        ),
        "project.readiness_gates": _row_id_values(
            project.get("readiness_gates", []) if isinstance(project, dict) else []
        ),
        "project.first_build_phases": _row_id_values(
            project.get("first_build_phases", []) if isinstance(project, dict) else []
        ),
        "packs.domain_lenses": _row_id_values(
            packs.get("domain_lenses", []) if isinstance(packs, dict) else []
        ),
        "packs.pilot_jurisdiction_scopes": _row_id_values(
            packs.get("pilot_jurisdiction_scopes", []) if isinstance(packs, dict) else []
        ),
        "packs.queued_jurisdiction_scopes": _row_id_values(
            packs.get("queued_jurisdiction_scopes", []) if isinstance(packs, dict) else []
        ),
        "grounding.sources": _row_id_values(
            grounding.get("sources", []) if isinstance(grounding, dict) else []
        ),
        "scheme_prompts": _row_id_values(prompt_rows),
    }
    return [
        f"{group}:{value}"
        for group, values in groups.items()
        for value in _duplicate_values(values)
    ]


def _lower_join(values: Any) -> str:
    if not isinstance(values, list):
        return ""
    return " ".join(str(value).lower() for value in values if isinstance(value, str))


def _missing_source_admission_rule_concepts(project: Any) -> list[str]:
    rules = _lower_join(project.get("source_admission_rules", []) if isinstance(project, dict) else [])
    return [
        concept for concept, accepted_terms in SOURCE_ADMISSION_RULE_CONCEPTS.items()
        if not any(term in rules for term in accepted_terms)
    ]


def _missing_readiness_gate_block_concepts(project: Any) -> list[str]:
    gates = project.get("readiness_gates", []) if isinstance(project, dict) else []
    block_terms: list[str] = []
    for gate in gates if isinstance(gates, list) else []:
        if isinstance(gate, dict):
            block_terms.extend(_string_values(gate.get("blocks", [])))
    blocks = _lower_join(block_terms)
    return [
        concept for concept, accepted_terms in READINESS_GATE_BLOCK_CONCEPTS.items()
        if not any(term in blocks for term in accepted_terms)
    ]


def _missing_scored_capability_concepts(project: Any) -> list[str]:
    capabilities = _lower_join(project.get("scored_capabilities", []) if isinstance(project, dict) else [])
    return [
        concept for concept, accepted_terms in SCORED_CAPABILITY_CONCEPTS.items()
        if not all(term in capabilities for term in accepted_terms)
    ]


def _count_rows_with_urls(rows: list[Any]) -> int:
    return sum(
        1 for row in rows
        if isinstance(row, dict)
        and isinstance(row.get("url"), str)
        and row["url"].strip()
    )


def _source_status_counts(rows: list[Any]) -> dict[str, int]:
    counts: dict[str, int] = {}
    for row in rows:
        status = row.get("verification_status") if isinstance(row, dict) else None
        key = (
            status
            if isinstance(status, str) and status in KNOWN_SOURCE_STATUSES
            else "invalid_or_unknown"
        )
        counts[key] = counts.get(key, 0) + 1
    return dict(sorted(counts.items()))


def _jurisdiction_scope_rows(packs: Any) -> list[dict[str, Any]]:
    if not isinstance(packs, dict):
        return []
    rows: list[dict[str, Any]] = []
    for key in ("pilot_jurisdiction_scopes", "queued_jurisdiction_scopes"):
        values = packs.get(key)
        if not isinstance(values, list):
            continue
        rows.extend(row for row in values if isinstance(row, dict))
    return rows


def _coverage_tags(rows: Any) -> set[str]:
    if not isinstance(rows, list):
        return set()
    tags: set[str] = set()
    for row in rows:
        if not isinstance(row, dict):
            continue
        for tag in _string_values(row.get("coverage_tags", [])):
            tags.add(tag)
    return tags


def _project_checks(project: Any) -> list[dict[str, Any]]:
    checks: list[dict[str, Any]] = []
    status = project.get("status") if isinstance(project, dict) else None
    meta = project.get("_meta") if isinstance(project, dict) else {}
    meta_status = meta.get("status") if isinstance(meta, dict) else ""
    checks.append(_check(
        "project_charter_is_propose_only",
        status == "propose_only" and isinstance(meta_status, str) and "propose-only" in meta_status,
        expected="status=propose_only and meta status says propose-only",
        actual={
            "status": _known_or_custom(status, KNOWN_PROJECT_STATUSES),
            "meta_mentions_propose_only": "propose-only" in str(meta_status),
        },
    ))

    gate_ids = set(_row_id_values(
        project.get("readiness_gates", []) if isinstance(project, dict) else []
    ))
    checks.append(_check(
        "project_readiness_gates_cover_required_gates",
        REQUIRED_REVIEW_GATES <= gate_ids,
        expected={
            "required_gate_count": len(REQUIRED_REVIEW_GATES),
            "missing_required_gate_count": 0,
        },
        actual={
            "declared_gate_count": len(gate_ids),
            "missing_required_gate_count": len(REQUIRED_REVIEW_GATES - gate_ids),
        },
    ))
    missing_readiness_block_concepts = _missing_readiness_gate_block_concepts(project)
    checks.append(_check(
        "project_readiness_gates_block_public_training_comparable_and_worker_use",
        missing_readiness_block_concepts == [],
        expected=[],
        actual=missing_readiness_block_concepts,
    ))
    project_row_id_issues = [
        *_row_id_shape_issues(project.get("readiness_gates", []) if isinstance(project, dict) else [], "readiness_gates"),
        *_row_id_shape_issues(project.get("first_build_phases", []) if isinstance(project, dict) else [], "first_build_phases"),
    ]
    checks.append(_check(
        "project_planning_rows_have_string_ids",
        project_row_id_issues == [],
        expected=[],
        actual=_unique_issue_count(project_row_id_issues),
    ))

    missing_rule_terms = _missing_source_admission_rule_concepts(project)
    checks.append(_check(
        "source_admission_rules_cover_safety_boundaries",
        missing_rule_terms == [],
        expected=[],
        actual=missing_rule_terms,
    ))
    missing_scored_capability_concepts = _missing_scored_capability_concepts(project)
    checks.append(_check(
        "scored_capabilities_cover_regulatory_miss_patterns",
        missing_scored_capability_concepts == [],
        expected=[],
        actual=missing_scored_capability_concepts,
    ))

    phases = project.get("first_build_phases", []) if isinstance(project, dict) else []
    unblocked_phases = [
        phase.get("id", f"phase_{index}")
        for index, phase in enumerate(phases)
        if isinstance(phase, dict)
        and (
            phase.get("ready_for_public_scoring") is not False
            or phase.get("ready_for_training_use") is not False
            or phase.get("ready_for_worker_facing_use") is not False
        )
    ]
    checks.append(_check(
        "first_build_phases_remain_blocked",
        isinstance(phases, list) and phases != [] and unblocked_phases == [],
        expected=[],
        actual=_issue_count(unblocked_phases),
    ))

    non_goals = _lower_join(project.get("non_goals", []) if isinstance(project, dict) else [])
    required_non_goal_terms = [
        "not a legal advice",
        "not a worker-facing",
        "not comparable leaderboard",
    ]
    missing_non_goal_terms = [term for term in required_non_goal_terms if term not in non_goals]
    checks.append(_check(
        "non_goals_block_advice_worker_use_and_leaderboards",
        missing_non_goal_terms == [],
        expected=[],
        actual=missing_non_goal_terms,
    ))
    return checks


def _jurisdiction_pack_checks(packs: Any) -> list[dict[str, Any]]:
    checks: list[dict[str, Any]] = []
    status = packs.get("status") if isinstance(packs, dict) else None
    policy = packs.get("pilot_policy") if isinstance(packs, dict) else ""
    checks.append(_check(
        "jurisdiction_pack_matrix_is_propose_only",
        status == "propose_only" and "not accepted until" in str(policy),
        expected="status=propose_only with acceptance policy",
        actual={
            "status": _known_or_custom(status, KNOWN_PROJECT_STATUSES),
            "policy_mentions_acceptance_gate": "not accepted until" in str(policy),
        },
    ))

    lenses = packs.get("domain_lenses", []) if isinstance(packs, dict) else []
    lens_gate_issues = []
    for lens in lenses if isinstance(lenses, list) else []:
        if not isinstance(lens, dict):
            lens_gate_issues.append("lens_not_object")
            continue
        review_gates = lens.get("review_gates", [])
        gate_shape_ok = (
            isinstance(review_gates, list)
            and all(isinstance(gate, str) for gate in review_gates)
        )
        gates = set(_string_values(review_gates))
        slots = lens.get("source_object_slots")
        if (
            not gate_shape_ok
            or not REQUIRED_REVIEW_GATES <= gates
            or not isinstance(slots, list)
            or not slots
        ):
            lens_gate_issues.append(lens.get("id", "missing_id"))
    checks.append(_check(
        "domain_lenses_require_source_slots_and_review_gates",
        isinstance(lenses, list) and lenses != [] and lens_gate_issues == [],
        expected=[],
        actual=_unique_issue_count(lens_gate_issues),
    ))

    scopes = packs.get("pilot_jurisdiction_scopes", []) if isinstance(packs, dict) else []
    scope_issues = []
    for scope in scopes if isinstance(scopes, list) else []:
        if not isinstance(scope, dict):
            scope_issues.append("scope_not_object")
            continue
        iso = scope.get("iso3166_alpha2")
        if not isinstance(iso, str) or not re.fullmatch(r"[A-Z]{2}", iso):
            scope_issues.append(f"{scope.get('id', 'missing_id')}:bad_iso")
        if scope.get("language_review_required") is not True:
            scope_issues.append(f"{scope.get('id', 'missing_id')}:language_review")
        if not isinstance(scope.get("scope_resolution_required"), bool):
            scope_issues.append(f"{scope.get('id', 'missing_id')}:scope_resolution_flag")
    checks.append(_check(
        "pilot_jurisdiction_scopes_are_concrete_review_scopes",
        isinstance(scopes, list) and scopes != [] and scope_issues == [],
        expected=[],
        actual=_unique_issue_count(scope_issues),
    ))

    queued_scopes = packs.get("queued_jurisdiction_scopes", []) if isinstance(packs, dict) else []
    queued_scope_issues = []
    for scope in queued_scopes if isinstance(queued_scopes, list) else []:
        if not isinstance(scope, dict):
            queued_scope_issues.append("scope_not_object")
            continue
        scope_id = scope.get("id", "missing_id")
        iso = scope.get("iso3166_alpha2")
        if not isinstance(iso, str) or not re.fullmatch(r"[A-Z]{2}", iso):
            queued_scope_issues.append(f"{scope_id}:bad_iso")
        if scope.get("language_review_required") is not True:
            queued_scope_issues.append(f"{scope_id}:language_review")
        if scope.get("scope_resolution_required") is not True:
            queued_scope_issues.append(f"{scope_id}:scope_resolution_required")
        queued_reason = scope.get("queued_reason")
        if not isinstance(queued_reason, str) or "before any scored use" not in queued_reason:
            queued_scope_issues.append(f"{scope_id}:queued_reason")
    checks.append(_check(
        "queued_jurisdiction_scopes_are_concrete_source_gap_scopes",
        isinstance(queued_scopes, list) and queued_scopes != [] and queued_scope_issues == [],
        expected=[],
        actual=_unique_issue_count(queued_scope_issues),
    ))
    jurisdiction_pack_row_id_issues = [
        *_row_id_shape_issues(lenses, "domain_lenses"),
        *_row_id_shape_issues(scopes, "pilot_jurisdiction_scopes"),
        *_row_id_shape_issues(queued_scopes, "queued_jurisdiction_scopes"),
    ]
    checks.append(_check(
        "jurisdiction_pack_rows_have_string_ids",
        jurisdiction_pack_row_id_issues == [],
        expected=[],
        actual=_unique_issue_count(jurisdiction_pack_row_id_issues),
    ))
    return checks


def _metadata_privacy_checks(project: Any, packs: Any) -> list[dict[str, Any]]:
    project_counts = _privacy_issue_counts(project)
    pack_counts = _privacy_issue_counts(packs)
    return [
        _check(
            "project_and_pack_metadata_contains_no_private_identifiers",
            _privacy_issue_total(project_counts) == 0
            and _privacy_issue_total(pack_counts) == 0,
            expected={
                "project_privacy_issue_count": 0,
                "jurisdiction_pack_privacy_issue_count": 0,
            },
            actual={
                "project_privacy_issue_count": _privacy_issue_total(project_counts),
                "jurisdiction_pack_privacy_issue_count": _privacy_issue_total(pack_counts),
                "project_issue_counts": project_counts,
                "jurisdiction_pack_issue_counts": pack_counts,
            },
        )
    ]


def _grounding_metadata_privacy_checks(grounding: Any) -> list[dict[str, Any]]:
    meta = grounding.get("_meta") if isinstance(grounding, dict) else {}
    counts = _privacy_issue_counts(meta)
    return [
        _check(
            "grounding_metadata_contains_no_private_identifiers",
            _privacy_issue_total(counts) == 0,
            expected={"grounding_metadata_privacy_issue_count": 0},
            actual={
                "grounding_metadata_privacy_issue_count": _privacy_issue_total(counts),
                "grounding_metadata_issue_counts": counts,
            },
        )
    ]


def _grounding_source_rows_value(grounding: Any) -> Any:
    if isinstance(grounding, dict):
        return grounding.get("sources", [])
    return grounding


def _grounding_source_privacy_issue_counts(rows: Any) -> dict[str, int]:
    if not isinstance(rows, list):
        return _privacy_issue_counts(rows)
    scan_rows: list[Any] = []
    https_url_counts = {
        "email_like": 0,
        "phone_like": 0,
        "url_like": 0,
        "local_path_like": 0,
        "long_digit_like": 0,
    }
    for row in rows:
        if isinstance(row, dict):
            safe_row: dict[str, Any] = {}
            for key, value in row.items():
                if key == "url":
                    if value is None:
                        continue
                    if isinstance(value, str) and (value == "" or value.startswith("https://")):
                        url_text = value[len("https://"):] if value.startswith("https://") else value
                        url_counts = _privacy_issue_counts(url_text, count_url_like=False)
                        for count_key, count_value in url_counts.items():
                            https_url_counts[count_key] += count_value
                        continue
                safe_row[key] = value
            scan_rows.append(safe_row)
        else:
            scan_rows.append(row)
    counts = _privacy_issue_counts(scan_rows)
    for count_key, count_value in https_url_counts.items():
        counts[count_key] += count_value
    return counts


def _grounding_source_privacy_checks(grounding: Any) -> list[dict[str, Any]]:
    rows = _grounding_source_rows_value(grounding)
    counts = _grounding_source_privacy_issue_counts(rows)
    return [
        _check(
            "grounding_source_rows_contain_no_private_identifiers",
            _privacy_issue_total(counts) == 0,
            expected={"grounding_source_privacy_issue_count": 0},
            actual={
                "grounding_source_privacy_issue_count": _privacy_issue_total(counts),
                "grounding_source_issue_counts": counts,
            },
        )
    ]


def _grounding_checks(grounding: Any) -> list[dict[str, Any]]:
    rows = _grounding_source_rows_value(grounding)
    checks: list[dict[str, Any]] = []
    status_issues = []
    anchor_issues = []
    for row in rows if isinstance(rows, list) else []:
        if not isinstance(row, dict):
            status_issues.append("row_not_object")
            continue
        row_id = row.get("id", "missing_id")
        status = row.get("verification_status")
        jurisdiction = row.get("jurisdiction")
        source_type = row.get("source_type")
        url = row.get("url")
        verified_date = row.get("verified_date")
        if status == "verified_international_anchor":
            if jurisdiction != "international" or source_type != "international_standard":
                anchor_issues.append(row_id)
            if not isinstance(verified_date, str) or not _DATE.fullmatch(verified_date):
                anchor_issues.append(row_id)
            if not isinstance(url, str) or not url.startswith("https://"):
                anchor_issues.append(row_id)
            continue
        if not isinstance(status, str) or status not in PENDING_SOURCE_STATUSES:
            status_issues.append(row_id)
        if url is not None and not isinstance(url, str):
            status_issues.append(row_id)
        elif isinstance(url, str) and url.strip():
            status_issues.append(row_id)
        if verified_date is not None:
            status_issues.append(row_id)
    checks.append(_check(
        "grounding_sources_keep_local_rows_pending",
        isinstance(rows, list) and rows != [] and status_issues == [],
        expected=[],
        actual=_unique_issue_count(status_issues),
    ))
    checks.append(_check(
        "international_anchor_rows_are_dated_https_anchors",
        isinstance(rows, list) and anchor_issues == [],
        expected=[],
        actual=_unique_issue_count(anchor_issues),
    ))
    grounding_source_row_id_issues = _row_id_shape_issues(rows, "grounding_sources")
    checks.append(_check(
        "grounding_source_rows_have_string_ids",
        grounding_source_row_id_issues == [],
        expected=[],
        actual=_unique_issue_count(grounding_source_row_id_issues),
    ))
    return checks


def _prompt_checks(prompt_rows: list[Any], prompt_errors: list[dict[str, Any]]) -> list[dict[str, Any]]:
    checks: list[dict[str, Any]] = []
    safe_prompt_errors = _safe_prompt_errors(prompt_errors)
    prompt_privacy_counts = _privacy_issue_counts(prompt_rows)
    row_issues = []
    privacy_issues = []
    unresolved_status_issues = []
    required_false_flags = (
        "ready_for_public_scoring",
        "ready_for_training_use",
        "ready_for_worker_facing_use",
    )
    for row in prompt_rows:
        if not isinstance(row, dict):
            row_issues.append("row_not_object")
            continue
        row_id = row.get("id", "missing_id")
        text = row.get("text")
        pattern_ids = row.get("candidate_pattern_ids")
        if not isinstance(row_id, str) or not row_id.startswith("DCWP-SCHEME-"):
            row_issues.append(row_id)
        if row.get("source") != "synthetic_rights_miss_seed":
            row_issues.append(row_id)
        if not isinstance(text, str) or not text.startswith("Synthetic composite:"):
            row_issues.append(row_id)
        if (
            not isinstance(pattern_ids, list)
            or _string_values(pattern_ids) == []
            or len(_string_values(pattern_ids)) != len(pattern_ids)
        ):
            row_issues.append(row_id)
        for key, value in row.items():
            if key.startswith("ready_for_") and value is True:
                row_issues.append(row_id)
        if row.get("scope_resolution_status") != "unresolved_source_gap":
            unresolved_status_issues.append(row_id)
        for key in required_false_flags:
            if row.get(key) is not False:
                unresolved_status_issues.append(row_id)
        if isinstance(text, str) and (_EMAIL.search(text) or _PHONE.search(text) or _URL.search(text)):
            privacy_issues.append(row_id)
    checks.append(_check(
        "scheme_prompt_jsonl_parses",
        safe_prompt_errors == [],
        expected=[],
        actual=safe_prompt_errors,
    ))
    checks.append(_check(
        "scheme_prompts_remain_synthetic_planning_rows",
        prompt_rows != [] and row_issues == [],
        expected=[],
        actual=_unique_issue_count(row_issues),
    ))
    checks.append(_check(
        "scheme_prompts_are_explicitly_unresolved_and_not_ready",
        prompt_rows != [] and unresolved_status_issues == [],
        expected={
            "scope_resolution_status": "unresolved_source_gap",
            "ready_for_public_scoring": False,
            "ready_for_training_use": False,
            "ready_for_worker_facing_use": False,
        },
        actual=_unique_issue_count(unresolved_status_issues),
    ))
    checks.append(_check(
        "scheme_prompt_text_contains_no_urls_emails_or_phones",
        privacy_issues == [],
        expected=[],
        actual=_unique_issue_count(privacy_issues),
    ))
    checks.append(_check(
        "scheme_prompt_rows_contain_no_private_identifiers",
        _privacy_issue_total(prompt_privacy_counts) == 0,
        expected={"scheme_prompt_privacy_issue_count": 0},
        actual={
            "scheme_prompt_privacy_issue_count": _privacy_issue_total(prompt_privacy_counts),
            "scheme_prompt_issue_counts": prompt_privacy_counts,
        },
    ))
    return checks


def _integrity_checks(
    *,
    project: Any,
    packs: Any,
    grounding: Any,
    prompt_rows: list[dict[str, Any]],
) -> list[dict[str, Any]]:
    checks: list[dict[str, Any]] = []

    project_id = project.get("project_id") if isinstance(project, dict) else None
    pack_project_id = packs.get("project_id") if isinstance(packs, dict) else None
    checks.append(_check(
        "project_and_jurisdiction_pack_ids_match",
        isinstance(project_id, str) and project_id != "" and pack_project_id == project_id,
        expected={
            "project_id_present": True,
            "pack_project_id_matches": True,
        },
        actual={
            "project_id_present": isinstance(project_id, str) and project_id != "",
            "pack_project_id_matches": pack_project_id == project_id,
        },
    ))

    candidate_pattern_ids = set(_string_values(
        project.get("candidate_pattern_ids", []) if isinstance(project, dict) else []
    ))
    domain_lens_ids = _row_id_values(
        packs.get("domain_lenses", []) if isinstance(packs, dict) else []
    )
    undeclared_lens_ids = sorted(
        lens_id for lens_id in domain_lens_ids
        if lens_id not in candidate_pattern_ids
    )
    checks.append(_check(
        "domain_lenses_are_declared_candidate_patterns",
        domain_lens_ids != [] and undeclared_lens_ids == [],
        expected="every domain_lens.id appears in project.candidate_pattern_ids",
        actual=_issue_count(undeclared_lens_ids),
    ))

    readiness_gate_ids = set(_row_id_values(
        project.get("readiness_gates", []) if isinstance(project, dict) else []
    ))
    undeclared_gate_issues = []
    lenses = packs.get("domain_lenses", []) if isinstance(packs, dict) else []
    for lens in lenses if isinstance(lenses, list) else []:
        if not isinstance(lens, dict):
            continue
        lens_id = lens.get("id", "missing_id")
        for gate_id in _string_values(lens.get("review_gates", [])):
            if gate_id not in readiness_gate_ids:
                undeclared_gate_issues.append(f"{lens_id}:{gate_id}")
    checks.append(_check(
        "domain_lens_review_gates_are_declared_by_project",
        undeclared_gate_issues == [],
        expected="lens review_gates subset of project.readiness_gates ids",
        actual=_unique_issue_count(undeclared_gate_issues),
    ))

    target_families = set(_string_values(
        project.get("target_jurisdiction_families", []) if isinstance(project, dict) else []
    ))
    scopes = _jurisdiction_scope_rows(packs)
    undeclared_family_issues = []
    for scope in scopes:
        family = scope.get("jurisdiction_family")
        if family not in target_families:
            undeclared_family_issues.append(scope.get("id", "missing_id"))
    checks.append(_check(
        "jurisdiction_scope_families_are_declared_by_project",
        undeclared_family_issues == [],
        expected="every scope jurisdiction_family appears in project.target_jurisdiction_families",
        actual=_unique_issue_count(undeclared_family_issues),
    ))

    source_rows = grounding.get("sources", []) if isinstance(grounding, dict) else []
    scoped_jurisdictions = {
        scope.get("iso3166_alpha2") for scope in scopes
        if isinstance(scope.get("iso3166_alpha2"), str)
    }
    local_source_jurisdictions = {
        row.get("jurisdiction") for row in source_rows
        if isinstance(row, dict)
        and row.get("source_type") == "country_law_placeholder"
        and isinstance(row.get("jurisdiction"), str)
        and re.fullmatch(r"[A-Z]{2}", row.get("jurisdiction", ""))
    }
    missing_source_jurisdiction_scopes = sorted(local_source_jurisdictions - scoped_jurisdictions)
    checks.append(_check(
        "local_grounding_jurisdictions_have_declared_scopes",
        local_source_jurisdictions != set() and missing_source_jurisdiction_scopes == [],
        expected="every local grounding placeholder jurisdiction appears in pilot or queued scopes",
        actual=_issue_count(missing_source_jurisdiction_scopes),
    ))

    seed_domains = set(_string_values(
        project.get("primary_seed_domains", []) if isinstance(project, dict) else []
    ))
    meta = grounding.get("_meta") if isinstance(grounding, dict) else {}
    grounding_domain = meta.get("domain") if isinstance(meta, dict) else None
    checks.append(_check(
        "grounding_domain_is_project_seed_domain",
        isinstance(grounding_domain, str) and grounding_domain in seed_domains,
        expected={
            "seed_domain_count": len(seed_domains),
            "grounding_domain_in_seed_domains": True,
        },
        actual={
            "seed_domain_count": len(seed_domains),
            "grounding_domain": _known_or_custom(grounding_domain, CANONICAL_GROUNDING_DOMAINS),
            "grounding_domain_in_seed_domains": grounding_domain in seed_domains,
        },
    ))

    duplicate_issues = _duplicate_id_issues(
        project=project,
        packs=packs,
        grounding=grounding,
        prompt_rows=prompt_rows,
    )
    checks.append(_check(
        "planning_ids_are_unique_within_namespaces",
        duplicate_issues == [],
        expected=[],
        actual=_issue_count(duplicate_issues),
    ))

    prompt_categories = {
        row.get("category") for row in prompt_rows
        if isinstance(row, dict)
        and isinstance(row.get("category"), str)
        and row.get("category")
    }
    source_rows = grounding.get("sources", []) if isinstance(grounding, dict) else []
    grounding_tags = _coverage_tags(source_rows)
    missing_prompt_category_slots = sorted(prompt_categories - grounding_tags)
    checks.append(_check(
        "scheme_prompt_categories_have_grounding_source_slots",
        prompt_categories != set() and missing_prompt_category_slots == [],
        expected="every scheme prompt category appears in grounding source coverage_tags",
        actual=_issue_count(missing_prompt_category_slots),
    ))

    candidate_pattern_ids = set(_string_values(
        project.get("candidate_pattern_ids", []) if isinstance(project, dict) else []
    ))
    prompt_candidate_pattern_ids = {
        pattern_id
        for row in prompt_rows
        if isinstance(row, dict)
        for pattern_id in _string_values(row.get("candidate_pattern_ids", []))
    }
    undeclared_prompt_patterns = sorted(prompt_candidate_pattern_ids - candidate_pattern_ids)
    checks.append(_check(
        "scheme_prompt_candidate_patterns_are_declared_by_project",
        prompt_candidate_pattern_ids != set() and undeclared_prompt_patterns == [],
        expected="every scheme prompt candidate_pattern_ids entry appears in project.candidate_pattern_ids",
        actual=_issue_count(undeclared_prompt_patterns),
    ))
    return checks


def build_report(
    *,
    project_config: Any | None = None,
    jurisdiction_packs: Any | None = None,
    grounding_sources: Any | None = None,
    scheme_prompts: list[dict[str, Any]] | None = None,
    scheme_prompt_errors: list[dict[str, Any]] | None = None,
    project_config_path: pathlib.Path = PROJECT_CONFIG,
    jurisdiction_packs_path: pathlib.Path = JURISDICTION_PACKS,
    grounding_sources_path: pathlib.Path = GROUNDING_SOURCES,
    scheme_prompts_path: pathlib.Path = SCHEME_PROMPTS,
) -> dict[str, Any]:
    project, project_error = _load_json(project_config_path) if project_config is None else (project_config, "")
    packs, packs_error = _load_json(jurisdiction_packs_path) if jurisdiction_packs is None else (jurisdiction_packs, "")
    grounding, grounding_error = _load_json(grounding_sources_path) if grounding_sources is None else (grounding_sources, "")
    prompts, prompt_errors = (
        _load_jsonl(scheme_prompts_path)
        if scheme_prompts is None
        else _coerce_prompt_rows(scheme_prompts, scheme_prompt_errors)
    )

    load_errors = {
        key: value for key, value in {
            "project_config": project_error,
            "jurisdiction_packs": packs_error,
            "grounding_sources": grounding_error,
        }.items()
        if value
    }
    checks = [
        _check("planning_artifacts_load", not load_errors, expected={}, actual=load_errors),
        *_project_checks(project),
        *_jurisdiction_pack_checks(packs),
        *_metadata_privacy_checks(project, packs),
        *_grounding_metadata_privacy_checks(grounding),
        *_grounding_source_privacy_checks(grounding),
        *_grounding_checks(grounding),
        *_prompt_checks(prompts, prompt_errors),
        *_integrity_checks(
            project=project,
            packs=packs,
            grounding=grounding,
            prompt_rows=prompts,
        ),
    ]
    failed = _failed_ids(checks)
    sources = grounding.get("sources", []) if isinstance(grounding, dict) and isinstance(grounding.get("sources"), list) else []
    lenses = packs.get("domain_lenses", []) if isinstance(packs, dict) and isinstance(packs.get("domain_lenses"), list) else []
    scopes = (
        packs.get("pilot_jurisdiction_scopes", [])
        if isinstance(packs, dict) and isinstance(packs.get("pilot_jurisdiction_scopes"), list)
        else []
    )
    queued_scopes = (
        packs.get("queued_jurisdiction_scopes", [])
        if isinstance(packs, dict) and isinstance(packs.get("queued_jurisdiction_scopes"), list)
        else []
    )
    project_phases = (
        project.get("first_build_phases", [])
        if isinstance(project, dict) and isinstance(project.get("first_build_phases"), list)
        else []
    )
    duplicate_issues = _duplicate_id_issues(
        project=project,
        packs=packs,
        grounding=grounding,
        prompt_rows=prompts,
    )
    pack_project_id = packs.get("project_id") if isinstance(packs, dict) else None
    project_id = project.get("project_id") if isinstance(project, dict) else None
    prompt_categories = {
        row.get("category") for row in prompts
        if isinstance(row, dict)
        and isinstance(row.get("category"), str)
        and row.get("category")
    }
    prompt_candidate_pattern_ids = {
        pattern_id
        for row in prompts
        if isinstance(row, dict)
        for pattern_id in _string_values(row.get("candidate_pattern_ids", []))
    }
    candidate_pattern_ids = set(_string_values(
        project.get("candidate_pattern_ids", []) if isinstance(project, dict) else []
    ))
    prompt_candidate_patterns_without_project_declaration = sorted(
        prompt_candidate_pattern_ids - candidate_pattern_ids
    )
    prompt_unresolved_scope_count = sum(
        1 for row in prompts
        if isinstance(row, dict)
        if row.get("scope_resolution_status") == "unresolved_source_gap"
    )
    prompt_not_ready_count = sum(
        1 for row in prompts
        if isinstance(row, dict)
        if row.get("ready_for_public_scoring") is False
        and row.get("ready_for_training_use") is False
        and row.get("ready_for_worker_facing_use") is False
    )
    grounding_tags = _coverage_tags(sources)
    prompt_categories_without_source_slots = sorted(prompt_categories - grounding_tags)
    scoped_jurisdictions = {
        scope.get("iso3166_alpha2") for scope in _jurisdiction_scope_rows(packs)
        if isinstance(scope.get("iso3166_alpha2"), str)
    }
    local_source_jurisdictions = {
        row.get("jurisdiction") for row in sources
        if isinstance(row, dict)
        and row.get("source_type") == "country_law_placeholder"
        and isinstance(row.get("jurisdiction"), str)
        and re.fullmatch(r"[A-Z]{2}", row.get("jurisdiction", ""))
    }
    local_source_jurisdictions_without_scope = sorted(local_source_jurisdictions - scoped_jurisdictions)
    grounding_meta = grounding.get("_meta") if isinstance(grounding, dict) else {}
    project_privacy_counts = _privacy_issue_counts(project)
    pack_privacy_counts = _privacy_issue_counts(packs)
    grounding_privacy_counts = _privacy_issue_counts(grounding_meta)
    grounding_source_privacy_counts = _grounding_source_privacy_issue_counts(
        _grounding_source_rows_value(grounding)
    )
    prompt_privacy_counts = _privacy_issue_counts(prompts)
    missing_source_admission_rule_concepts = _missing_source_admission_rule_concepts(project)
    missing_readiness_gate_block_concepts = _missing_readiness_gate_block_concepts(project)
    missing_scored_capability_concepts = _missing_scored_capability_concepts(project)
    summary = {
        "ok": failed == [],
        "check_count": len(checks),
        "failed_count": len(failed),
        "failed_ids": failed,
        "project_id": _known_or_custom(project_id, CANONICAL_PROJECT_IDS),
        "project_status": _known_or_custom(
            project.get("status") if isinstance(project, dict) else None,
            KNOWN_PROJECT_STATUSES,
        ),
        "project_pack_id_match": (
            isinstance(project_id, str)
            and project_id != ""
            and pack_project_id == project_id
        ),
        "primary_seed_domain_count": (
            len(project.get("primary_seed_domains", []))
            if isinstance(project, dict) and isinstance(project.get("primary_seed_domains"), list)
            else 0
        ),
        "candidate_pattern_count": (
            len(project.get("candidate_pattern_ids", []))
            if isinstance(project, dict) and isinstance(project.get("candidate_pattern_ids"), list)
            else 0
        ),
        "readiness_gate_count": (
            len(project.get("readiness_gates", []))
            if isinstance(project, dict) and isinstance(project.get("readiness_gates"), list)
            else 0
        ),
        "first_build_phase_count": len(project_phases),
        "first_build_phases_blocked": all(
            isinstance(phase, dict)
            and phase.get("ready_for_public_scoring") is False
            and phase.get("ready_for_training_use") is False
            and phase.get("ready_for_worker_facing_use") is False
            for phase in project_phases
        ) if project_phases else False,
        "domain_lens_count": len(lenses),
        "pilot_jurisdiction_scope_count": len(scopes),
        "queued_jurisdiction_scope_count": len(queued_scopes),
        "local_source_jurisdiction_count": len(local_source_jurisdictions),
        "local_source_jurisdictions_without_scope_count": len(
            local_source_jurisdictions_without_scope
        ),
        "grounding_source_count": len(sources),
        "source_status_counts": _source_status_counts(sources),
        "grounding_rows_with_urls": _count_rows_with_urls(sources),
        "grounding_domain": (
            _known_or_custom(
                grounding_meta.get("domain") if isinstance(grounding_meta, dict) else None,
                CANONICAL_GROUNDING_DOMAINS,
            )
        ),
        "scheme_prompt_count": len(prompts),
        "scheme_prompt_category_count": len(prompt_categories),
        "scheme_prompt_candidate_pattern_count": len(prompt_candidate_pattern_ids),
        "scheme_prompt_candidate_patterns_without_project_declaration_count": len(
            prompt_candidate_patterns_without_project_declaration
        ),
        "scheme_prompt_unresolved_scope_count": prompt_unresolved_scope_count,
        "scheme_prompt_not_ready_count": prompt_not_ready_count,
        "scheme_prompt_categories_without_source_slots_count": len(
            prompt_categories_without_source_slots
        ),
        "duplicate_id_issue_count": len(duplicate_issues),
        "readiness_gate_missing_block_concept_count": len(missing_readiness_gate_block_concepts),
        "source_admission_missing_concept_count": len(missing_source_admission_rule_concepts),
        "scored_capability_missing_concept_count": len(missing_scored_capability_concepts),
        "project_privacy_issue_count": _privacy_issue_total(project_privacy_counts),
        "jurisdiction_pack_privacy_issue_count": _privacy_issue_total(pack_privacy_counts),
        "grounding_metadata_privacy_issue_count": _privacy_issue_total(grounding_privacy_counts),
        "grounding_source_privacy_issue_count": _privacy_issue_total(grounding_source_privacy_counts),
        "scheme_prompt_privacy_issue_count": _privacy_issue_total(prompt_privacy_counts),
    }
    return {
        "summary": summary,
        "checks": checks,
    }


def _print_text_report(report: dict[str, Any]) -> None:
    summary = report["summary"]
    print(
        "Sister-project planning validation - "
        f"{summary['check_count']} checks, {summary['failed_count']} findings"
    )
    print(
        "Snapshot - "
        f"project={summary.get('project_id')} "
        f"status={summary.get('project_status')} "
        f"prompts={summary.get('scheme_prompt_count')} "
        f"prompt_patterns={summary.get('scheme_prompt_candidate_pattern_count')} "
        f"undeclared_prompt_patterns={summary.get('scheme_prompt_candidate_patterns_without_project_declaration_count')} "
        f"unresolved_prompts={summary.get('scheme_prompt_unresolved_scope_count')} "
        f"source_rows={summary.get('grounding_source_count')} "
        f"missing_source_slots={summary.get('scheme_prompt_categories_without_source_slots_count')} "
        f"jurisdiction_scopes={summary.get('pilot_jurisdiction_scope_count')} "
        f"queued_scopes={summary.get('queued_jurisdiction_scope_count')} "
        f"missing_scope_jurisdictions={summary.get('local_source_jurisdictions_without_scope_count')} "
        f"readiness_gate_missing={summary.get('readiness_gate_missing_block_concept_count')} "
        f"source_admission_missing={summary.get('source_admission_missing_concept_count')} "
        f"scored_capability_missing={summary.get('scored_capability_missing_concept_count')} "
        f"first_build_phases_blocked={summary.get('first_build_phases_blocked')} "
        f"privacy_issues=project:{summary.get('project_privacy_issue_count')},"
        f"packs:{summary.get('jurisdiction_pack_privacy_issue_count')},"
        f"grounding:{summary.get('grounding_metadata_privacy_issue_count')},"
        f"prompts:{summary.get('scheme_prompt_privacy_issue_count')},"
        f"grounding_sources:{summary.get('grounding_source_privacy_issue_count')}"
    )
    for check in report["checks"]:
        if check.get("ok") is True:
            continue
        print(f"[FAIL] {check['id']}")
        print(f"  expected: {check.get('expected')}")
        print(f"  actual:   {check.get('actual')}")


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--project-config", type=pathlib.Path, default=PROJECT_CONFIG)
    parser.add_argument("--jurisdiction-packs", type=pathlib.Path, default=JURISDICTION_PACKS)
    parser.add_argument("--grounding-sources", type=pathlib.Path, default=GROUNDING_SOURCES)
    parser.add_argument("--scheme-prompts", type=pathlib.Path, default=SCHEME_PROMPTS)
    parser.add_argument("--json", action="store_true", help="emit machine-readable JSON")
    args = parser.parse_args(argv)
    report = build_report(
        project_config_path=args.project_config,
        jurisdiction_packs_path=args.jurisdiction_packs,
        grounding_sources_path=args.grounding_sources,
        scheme_prompts_path=args.scheme_prompts,
    )
    if args.json:
        print(json.dumps(report, indent=2, sort_keys=True))
    else:
        _print_text_report(report)
    return 0 if report["summary"]["ok"] else 1


if __name__ == "__main__":
    raise SystemExit(main())
