#!/usr/bin/env python3
"""Validate the full saved global-protections artifact set.

Run this after:

    python scripts/build_global_protections_curation_bundle.py --write-components

Or pass `--refresh-components` to regenerate that component set first. Use
`--refresh-all-components` when the lower-level domain and regulatory curation
artifacts should be refreshed too. The default mode remains read-only.

It loads each saved JSON artifact, confirms its companion Markdown handoff
exists and stays compact/safe, calls the matching read-only validator in memory,
and emits one compact suite report. The suite stores only per-artifact
validation summaries and failed check IDs; it does not embed raw source rows,
prompt text, model responses, or the full expected/actual payloads produced by
component validators.

Offline + deterministic. No model, no network, no credits. Read-only.
"""
from __future__ import annotations

import argparse
import json
import pathlib
import re
import sys
from typing import Any, Callable

_ROOT = pathlib.Path(__file__).resolve().parents[1]
_SCRIPTS = pathlib.Path(__file__).resolve().parent
if str(_SCRIPTS) not in sys.path:
    sys.path.insert(0, str(_SCRIPTS))

from artifact_path_policy import handoff_artifact_path  # noqa: E402
import build_global_protections_curation_bundle as curation_builder  # noqa: E402
import build_global_protections_project_plan as project_plan_builder  # noqa: E402
import validate_domain_curation_bundle as domain_curation_validator  # noqa: E402
import validate_domain_source_review_packet as domain_source_review_validator  # noqa: E402
import validate_global_protections_benchmark_blueprint as benchmark_validator  # noqa: E402
import validate_global_protections_curation_bundle as curation_validator  # noqa: E402
import validate_global_protections_curator_sprint as sprint_validator  # noqa: E402
import validate_global_protections_diagnostic_run_plan as diagnostic_validator  # noqa: E402
import validate_global_protections_eval_contract as eval_validator  # noqa: E402
import validate_global_protections_judge_calibration_plan as calibration_validator  # noqa: E402
import validate_global_protections_jurisdiction_pack_matrix as jurisdiction_validator  # noqa: E402
import validate_global_protections_next_actions as next_actions_validator  # noqa: E402
import validate_global_protections_project_plan as project_plan_validator  # noqa: E402
import validate_global_protections_readiness_bundle as readiness_validator  # noqa: E402
import validate_global_protections_source_channel_matrix as source_matrix_validator  # noqa: E402
import validate_global_protections_source_channel_review_packet as source_review_validator  # noqa: E402
import validate_global_protections_transition_gate as transition_validator  # noqa: E402
import validate_regulatory_curation_bundle as regulatory_curation_validator  # noqa: E402
import validate_regulatory_domain_intake_packet as regulatory_intake_validator  # noqa: E402

OUT_DIR = _ROOT / "reports" / "benchmark"
OUT = OUT_DIR / "global_protections_saved_artifacts_validation.json"
MD_OUT = OUT_DIR / "global_protections_saved_artifacts_validation.md"
DEFAULT_DOMAIN = curation_builder.DEFAULT_DOMAIN

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
LOWER_LEVEL_MARKDOWN_DISALLOWED_TERMS = [
    term for term in DISALLOWED_TERMS if term not in {"candidate_url", "source_url"}
]
PRIVATE_MARKDOWN_HINT_RE = re.compile(
    r"(?i)(?:[A-Z0-9._%+-]+@[A-Z0-9.-]+\.[A-Z]{2,}|(?:https?|ftp|s3|file|mailto):/?|[A-Z]:[\\/]|\\\\|/(?:users|home|tmp|var|mnt|private|volumes)(?:/|$)|OneDrive/Documents|AppData/Local|\.\./|\d{8,})"
)
MAX_MARKDOWN_BYTES = 320_000
CUSTOM_OR_INVALID = "custom_or_invalid"
KNOWN_JURISDICTION_SCOPE_IDS = frozenset({
    "bd_origin_state",
    "np_origin_state",
    "lk_origin_state",
    "ph_origin_state",
    "id_origin_destination",
    "ke_origin_destination",
    "gh_origin_destination",
    "qa_destination_forum",
})
KNOWN_DOMAIN_LENS_IDS = frozenset({
    "cross_border_worker_protections",
    "digital_consumer_credit_worker_debt",
    "informal_housing_tenancy_eviction",
})
KNOWN_LEGAL_ANCHOR_SOURCE_CHANNEL_IDS = frozenset({
    "official_gazette_or_law_portal",
    "labour_or_migration_ministry_notice",
})


def _artifact_path(path: pathlib.Path) -> str:
    return handoff_artifact_path(path, root=_ROOT)


def _safe_artifact_path_extra_keys(keys: list[str]) -> list[str]:
    return [CUSTOM_OR_INVALID] if keys else []


def _safe_artifact_path_actual(value: Any, *, allowed_values: set[str]) -> Any:
    if not isinstance(value, str):
        return type(value).__name__
    if value in allowed_values:
        return value
    return CUSTOM_OR_INVALID


def _safe_known_id_list(value: Any, *, allowed: frozenset[str]) -> Any:
    if not isinstance(value, list):
        return type(value).__name__
    safe: list[str] = []
    custom_seen = False
    for item in value:
        if isinstance(item, str) and item in allowed:
            safe.append(item)
        elif not custom_seen:
            safe.append(CUSTOM_OR_INVALID)
            custom_seen = True
    return safe


def _safe_jurisdiction_id_fields(value: dict[str, Any]) -> dict[str, Any]:
    safe = dict(value)
    if "jurisdiction_scope_ids" in safe:
        safe["jurisdiction_scope_ids"] = _safe_known_id_list(
            safe["jurisdiction_scope_ids"],
            allowed=KNOWN_JURISDICTION_SCOPE_IDS,
        )
    if "domain_lens_ids" in safe:
        safe["domain_lens_ids"] = _safe_known_id_list(
            safe["domain_lens_ids"],
            allowed=KNOWN_DOMAIN_LENS_IDS,
        )
    return safe


def _safe_legal_anchor_id_fields(value: dict[str, Any]) -> dict[str, Any]:
    safe = dict(value)
    if "legal_claim_anchor_source_channel_ids" in safe:
        safe["legal_claim_anchor_source_channel_ids"] = _safe_known_id_list(
            safe["legal_claim_anchor_source_channel_ids"],
            allowed=KNOWN_LEGAL_ANCHOR_SOURCE_CHANNEL_IDS,
        )
    return safe


def _safe_jurisdiction_pack_id_coverage(coverage: dict[str, Any]) -> dict[str, Any]:
    safe = dict(coverage)
    for key in ("jurisdiction_pack_scope_ids", "curation_jurisdiction_pack_scope_ids"):
        if key in safe:
            safe[key] = _safe_known_id_list(safe[key], allowed=KNOWN_JURISDICTION_SCOPE_IDS)
    for key in ("jurisdiction_pack_domain_lens_ids", "curation_jurisdiction_pack_domain_lens_ids"):
        if key in safe:
            safe[key] = _safe_known_id_list(safe[key], allowed=KNOWN_DOMAIN_LENS_IDS)
    return safe


def _safe_legal_anchor_channel_coverage(coverage: dict[str, Any]) -> dict[str, Any]:
    safe = dict(coverage)
    for key in list(safe):
        if key.endswith("legal_claim_anchor_source_channel_ids"):
            safe[key] = _safe_known_id_list(
                safe[key],
                allowed=KNOWN_LEGAL_ANCHOR_SOURCE_CHANNEL_IDS,
            )
    return safe


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


def refresh_component_artifacts(
    *,
    domain_id: str = DEFAULT_DOMAIN,
    project_config_path: pathlib.Path = project_plan_builder.CONFIG,
    registry_path: pathlib.Path = project_plan_builder.REGISTRY,
    regulatory_catalog_path: pathlib.Path = project_plan_builder.REGULATORY_CATALOG,
    component_dir: pathlib.Path = OUT_DIR,
    refresh_all_components: bool = False,
) -> int:
    """Regenerate the saved component set that this suite validates."""
    args = [
        "--domain",
        domain_id,
        "--project-config",
        str(project_config_path),
        "--registry",
        str(registry_path),
        "--regulatory-catalog",
        str(regulatory_catalog_path),
        "--component-dir",
        str(component_dir),
        "--out",
        str(component_dir / "global_protections_curation_bundle.json"),
        "--md-out",
        str(component_dir / "global_protections_curation_bundle.md"),
        "--write-components",
    ]
    if refresh_all_components:
        args.append("--write-all-components")
    return curation_builder.main(args)


def _artifact_specs(component_dir: pathlib.Path) -> list[dict[str, str]]:
    stems = [
        ("project_plan", "global_protections_project_plan"),
        ("jurisdiction_pack_matrix", "global_protections_jurisdiction_pack_matrix"),
        ("source_channel_matrix", "global_protections_source_channel_matrix"),
        ("source_channel_review_packet", "global_protections_source_channel_review_packet"),
        ("benchmark_blueprint", "global_protections_benchmark_blueprint"),
        ("eval_contract", "global_protections_eval_contract"),
        ("diagnostic_run_plan", "global_protections_diagnostic_run_plan"),
        ("judge_calibration_plan", "global_protections_judge_calibration_plan"),
        ("transition_gate", "global_protections_transition_gate"),
        ("readiness_bundle", "global_protections_readiness_bundle"),
        ("next_actions", "global_protections_next_actions"),
        ("curator_sprint", "global_protections_curator_sprint"),
        ("curation_bundle", "global_protections_curation_bundle"),
    ]
    return [
        {
            "artifact_id": artifact_id,
            "stem": stem,
            "json_path": str(component_dir / f"{stem}.json"),
            "markdown_path": str(component_dir / f"{stem}.md"),
        }
        for artifact_id, stem in stems
    ]


def _lower_level_artifact_specs(
    component_dir: pathlib.Path,
    *,
    domain_id: str,
) -> list[dict[str, str]]:
    domain_paths = curation_builder.readiness_builder.domain_bundle_builder.component_paths(
        domain_id,
        output_dir=component_dir,
    )
    regulatory_paths = curation_builder.readiness_builder.regulatory_bundle_builder.component_paths(
        output_dir=component_dir,
    )
    return [
        *_lower_level_specs_from_component_paths(
            domain_paths,
            component_dir=component_dir,
            prefix="domain",
        ),
        *_lower_level_specs_from_component_paths(
            regulatory_paths,
            component_dir=component_dir,
            prefix="regulatory",
        ),
    ]


def _lower_level_specs_from_component_paths(
    paths: dict[str, str],
    *,
    component_dir: pathlib.Path,
    prefix: str,
) -> list[dict[str, str]]:
    specs: list[dict[str, str]] = []
    for key, value in paths.items():
        if not key.endswith("_json"):
            continue
        base_key = key[: -len("_json")]
        markdown_key = f"{base_key}_markdown"
        stem = pathlib.PurePosixPath(value).stem
        artifact_id = base_key if base_key.startswith(f"{prefix}_") else f"{prefix}_{base_key}"
        specs.append({
            "artifact_id": artifact_id,
            "stem": stem,
            "json_path": str(component_dir / f"{stem}.json"),
            "markdown_path": str(component_dir / f"{pathlib.PurePosixPath(paths[markdown_key]).stem}.md"),
            "builder_json_key": key,
            "builder_markdown_key": markdown_key,
        })
    return specs


def _expected_bundle_artifact_paths(
    *,
    component_dir: pathlib.Path,
    domain_id: str,
) -> dict[str, str]:
    paths: dict[str, str] = {}
    for spec in _artifact_specs(component_dir):
        stem = spec["stem"]
        paths[f"{stem}_json"] = _artifact_path(pathlib.Path(spec["json_path"]))
        paths[f"{stem}_markdown"] = _artifact_path(pathlib.Path(spec["markdown_path"]))
    paths["domain"] = domain_id
    return paths


def _optional_bundle_artifact_paths(
    *,
    component_dir: pathlib.Path,
    domain_id: str,
) -> dict[str, str]:
    """Return optional lower-level paths emitted by --write-all-components."""
    paths = curation_builder.readiness_builder.component_paths(
        output_dir=component_dir,
        domain_id=domain_id,
    )
    paths.update(
        curation_builder.readiness_builder.domain_bundle_builder.component_paths(
            domain_id,
            output_dir=component_dir,
        )
    )
    paths.update(
        curation_builder.readiness_builder.regulatory_bundle_builder.component_paths(
            output_dir=component_dir,
        )
    )
    paths["domain"] = domain_id
    return paths


def _artifact_path_agreement_drift(
    *,
    component_dir: pathlib.Path,
    domain_id: str,
    require_optional_paths: bool = False,
) -> list[dict[str, Any]]:
    curation_path = component_dir / "global_protections_curation_bundle.json"
    doc = _load_json(curation_path)
    if not isinstance(doc, dict):
        return [{
            "rule": "curation_bundle_unreadable",
            "expected": _artifact_path(curation_path),
            "actual": type(doc).__name__,
        }]
    actual = doc.get("artifact_paths")
    if not isinstance(actual, dict):
        return [{"rule": "artifact_paths_object", "expected": "object", "actual": type(actual).__name__}]
    expected = _expected_bundle_artifact_paths(component_dir=component_dir, domain_id=domain_id)
    optional = _optional_bundle_artifact_paths(component_dir=component_dir, domain_id=domain_id)
    allowed = dict(optional)
    allowed.update(expected)
    findings: list[dict[str, Any]] = []
    required = allowed if require_optional_paths else expected
    missing = sorted(set(required) - set(actual))
    extra = sorted(set(actual) - set(allowed))
    if missing or extra:
        findings.append({
            "rule": "artifact_path_keys",
            "missing": missing,
            "extra": _safe_artifact_path_extra_keys(extra),
        })
    allowed_values = set(allowed.values())
    for key in sorted(set(allowed) & set(actual)):
        if actual.get(key) != allowed[key]:
            findings.append({
                "rule": "artifact_path_value",
                "key": key,
                "expected": allowed[key],
                "actual": _safe_artifact_path_actual(actual.get(key), allowed_values=allowed_values),
            })
    return findings


def _lower_level_bundle_expected_paths(
    artifact_id: str,
    *,
    component_dir: pathlib.Path,
    domain_id: str,
) -> dict[str, str] | None:
    if artifact_id == "domain_curation_bundle":
        return curation_builder.readiness_builder.domain_bundle_builder.component_paths(
            domain_id,
            output_dir=component_dir,
        )
    if artifact_id == "regulatory_curation_bundle":
        return curation_builder.readiness_builder.regulatory_bundle_builder.component_paths(
            output_dir=component_dir,
        )
    return None


def _artifact_path_map_drift(
    actual: Any,
    *,
    expected: dict[str, str],
) -> list[dict[str, Any]]:
    if not isinstance(actual, dict):
        return [{"rule": "artifact_paths_object", "expected": "object", "actual": type(actual).__name__}]
    findings: list[dict[str, Any]] = []
    missing = sorted(set(expected) - set(actual))
    extra = sorted(set(actual) - set(expected))
    if missing or extra:
        findings.append({
            "rule": "artifact_path_keys",
            "missing": missing,
            "extra": _safe_artifact_path_extra_keys(extra),
        })
    allowed_values = set(expected.values())
    for key in sorted(set(expected) & set(actual)):
        if actual.get(key) != expected[key]:
            findings.append({
                "rule": "artifact_path_value",
                "key": key,
                "expected": expected[key],
                "actual": _safe_artifact_path_actual(actual.get(key), allowed_values=allowed_values),
            })
    return findings


def _append_validation_check(report: dict[str, Any], check: dict[str, Any]) -> dict[str, Any]:
    checks = report.setdefault("checks", [])
    checks.append(check)
    summary = report.setdefault("summary", {})
    failed = _failed_ids(checks)
    summary["check_count"] = len(checks)
    summary["failed_check_count"] = len(failed)
    summary["failed_check_ids"] = failed
    summary["valid"] = not failed
    return report


def _with_lower_level_bundle_path_check(
    report: dict[str, Any],
    doc: Any,
    *,
    artifact_id: str,
    component_dir: pathlib.Path,
    domain_id: str,
) -> dict[str, Any]:
    expected = _lower_level_bundle_expected_paths(
        artifact_id,
        component_dir=component_dir,
        domain_id=domain_id,
    )
    if expected is None:
        return report
    actual = doc.get("artifact_paths") if isinstance(doc, dict) else None
    drift = _artifact_path_map_drift(actual, expected=expected)
    return _append_validation_check(
        report,
        _check(
            "lower_level_bundle_artifact_paths_match_files",
            not drift,
            expected=[],
            actual=drift,
        ),
    )


def _markdown_check(
    path: pathlib.Path,
    *,
    disallowed_terms: list[str] = DISALLOWED_TERMS,
) -> dict[str, Any]:
    try:
        raw = path.read_text(encoding="utf-8")
    except OSError:
        return {
            "markdown_path": _artifact_path(path),
            "markdown_readable": False,
            "markdown_safe": False,
            "markdown_issue_ids": ["markdown_unreadable"],
            "markdown_bytes": None,
        }
    size = len(raw.encode("utf-8"))
    disallowed = [term for term in disallowed_terms if term in raw]
    issue_ids: list[str] = []
    if not raw.strip():
        issue_ids.append("markdown_empty")
    if size > MAX_MARKDOWN_BYTES:
        issue_ids.append("markdown_too_large")
    if disallowed:
        issue_ids.append("markdown_disallowed_text")
    if "\\" in raw or "C:/" in raw or "/Users/" in raw or "../" in raw:
        issue_ids.append("markdown_path_leak")
    if PRIVATE_MARKDOWN_HINT_RE.search(raw):
        issue_ids.append("markdown_private_hint")
    return {
        "markdown_path": _artifact_path(path),
        "markdown_readable": True,
        "markdown_safe": not issue_ids,
        "markdown_issue_ids": issue_ids,
        "markdown_bytes": size,
    }


def _summary_row(
    artifact_id: str,
    json_path: pathlib.Path,
    markdown_path: pathlib.Path,
    report: dict[str, Any],
    *,
    markdown_disallowed_terms: list[str] = DISALLOWED_TERMS,
) -> dict[str, Any]:
    summary = report.get("summary") if isinstance(report.get("summary"), dict) else {}
    meta = report.get("_meta") if isinstance(report.get("_meta"), dict) else {}
    comparable_ready = summary.get("ready_for_comparable_scoring")
    if comparable_ready is None:
        comparable_ready = summary.get("ready_for_comparable_run")
    valid = summary.get("valid")
    if valid is None:
        valid = summary.get("ok")
    if valid is None:
        valid = meta.get("validation_ok")
    row = {
        "artifact_id": artifact_id,
        "json_path": _artifact_path(json_path),
        "readable": True,
        "valid": bool(valid),
        "check_count": summary.get("check_count", 0),
        "failed_check_count": summary.get("failed_check_count", 0),
        "failed_check_ids": list(summary.get("failed_check_ids") or []),
        "ready_for_comparable_scoring": comparable_ready,
    }
    for key in (
        "execution_phase_count",
        "execution_phase_covered_action_count",
        "next_execution_phase_count",
        "next_execution_phase_covered_actions",
        "curator_execution_phase_count",
        "curator_execution_phase_covered_actions",
    ):
        if key in summary:
            row[key] = summary.get(key)
    row.update(_markdown_check(markdown_path, disallowed_terms=markdown_disallowed_terms))
    return row


def _missing_row(
    artifact_id: str,
    json_path: pathlib.Path,
    markdown_path: pathlib.Path,
    *,
    markdown_disallowed_terms: list[str] = DISALLOWED_TERMS,
) -> dict[str, Any]:
    row = {
        "artifact_id": artifact_id,
        "json_path": _artifact_path(json_path),
        "readable": False,
        "valid": False,
        "check_count": 1,
        "failed_check_count": 1,
        "failed_check_ids": ["artifact_unreadable"],
        "ready_for_comparable_scoring": None,
    }
    row.update(_markdown_check(markdown_path, disallowed_terms=markdown_disallowed_terms))
    return row


def _curation_phase_coverage(doc: Any) -> dict[str, Any]:
    summary = doc.get("summary") if isinstance(doc, dict) and isinstance(doc.get("summary"), dict) else {}
    next_phase_count = summary.get("next_execution_phase_count")
    next_phase_covered = summary.get("next_execution_phase_covered_actions")
    curator_phase_count = summary.get("curator_execution_phase_count")
    curator_phase_covered = summary.get("curator_execution_phase_covered_actions")
    next_action_count = summary.get("next_action_count")
    curator_sprint_items = summary.get("curator_sprint_item_count")
    curator_blocked_later = summary.get("curator_blocked_later_items")
    expected_curator_covered = (
        curator_sprint_items + curator_blocked_later
        if isinstance(curator_sprint_items, int) and isinstance(curator_blocked_later, int)
        else None
    )
    values = (
        next_phase_count,
        next_phase_covered,
        curator_phase_count,
        curator_phase_covered,
    )
    return {
        "next_execution_phase_count": next_phase_count,
        "next_execution_phase_covered_actions": next_phase_covered,
        "curator_execution_phase_count": curator_phase_count,
        "curator_execution_phase_covered_actions": curator_phase_covered,
        "next_action_count": next_action_count,
        "curator_expected_phase_covered_actions": expected_curator_covered,
        "phase_coverage_present": all(isinstance(value, int) for value in values),
        "phase_counts_match": (
            isinstance(next_phase_count, int) and next_phase_count == curator_phase_count
        ),
        "phase_covered_action_counts_match": (
            isinstance(next_phase_covered, int) and next_phase_covered == curator_phase_covered
        ),
        "next_phase_coverage_matches_action_count": (
            isinstance(next_action_count, int) and next_phase_covered == next_action_count
        ),
        "curator_phase_coverage_matches_sprint_and_blocked": (
            expected_curator_covered is not None and curator_phase_covered == expected_curator_covered
        ),
    }


def _row_by_artifact_id(rows: list[dict[str, Any]], artifact_id: str) -> dict[str, Any]:
    return next((row for row in rows if row.get("artifact_id") == artifact_id), {})


def _direct_phase_coverage_mismatches(
    rows: list[dict[str, Any]],
    phase_coverage: dict[str, Any],
) -> list[dict[str, Any]]:
    expected_by_artifact = {
        "next_actions": {
            "execution_phase_count": phase_coverage["next_execution_phase_count"],
            "execution_phase_covered_action_count": phase_coverage[
                "next_execution_phase_covered_actions"
            ],
        },
        "curator_sprint": {
            "execution_phase_count": phase_coverage["curator_execution_phase_count"],
            "execution_phase_covered_action_count": phase_coverage[
                "curator_execution_phase_covered_actions"
            ],
        },
    }
    mismatches: list[dict[str, Any]] = []
    for artifact_id, expected in expected_by_artifact.items():
        row = _row_by_artifact_id(rows, artifact_id)
        actual = {
            "execution_phase_count": row.get("execution_phase_count"),
            "execution_phase_covered_action_count": row.get(
                "execution_phase_covered_action_count"
            ),
        }
        if actual != expected:
            mismatches.append({
                "artifact_id": artifact_id,
                "rule": "direct_phase_coverage_matches_curation_bundle",
                "expected": expected,
                "actual": actual,
            })
    return mismatches


def _summary(doc: Any) -> dict[str, Any]:
    return doc.get("summary") if isinstance(doc, dict) and isinstance(doc.get("summary"), dict) else {}


def _component_summary(doc: Any, component_id: str) -> dict[str, Any]:
    if not isinstance(doc, dict) or not isinstance(doc.get("component_summaries"), dict):
        return {}
    row = doc["component_summaries"].get(component_id)
    return row if isinstance(row, dict) else {}


def _jurisdiction_pack_id_coverage(artifact_docs: dict[str, Any]) -> dict[str, Any]:
    jurisdiction_pack = _summary(artifact_docs.get("jurisdiction_pack_matrix"))
    curation = _summary(artifact_docs.get("curation_bundle"))
    scope_ids = jurisdiction_pack.get("jurisdiction_scope_ids")
    lens_ids = jurisdiction_pack.get("domain_lens_ids")
    return {
        "jurisdiction_pack_scope_count": jurisdiction_pack.get("jurisdiction_scope_count"),
        "jurisdiction_pack_scope_ids": scope_ids,
        "jurisdiction_pack_domain_lens_count": jurisdiction_pack.get("domain_lens_count"),
        "jurisdiction_pack_domain_lens_ids": lens_ids,
        "curation_jurisdiction_pack_scope_count": curation.get("jurisdiction_pack_scopes"),
        "curation_jurisdiction_pack_scope_ids": curation.get("jurisdiction_pack_scope_ids"),
        "curation_jurisdiction_pack_domain_lens_count": curation.get(
            "jurisdiction_pack_domain_lenses"
        ),
        "curation_jurisdiction_pack_domain_lens_ids": curation.get(
            "jurisdiction_pack_domain_lens_ids"
        ),
        "jurisdiction_pack_scope_ids_present": isinstance(scope_ids, list) and bool(scope_ids),
        "jurisdiction_pack_domain_lens_ids_present": isinstance(lens_ids, list) and bool(lens_ids),
    }


def _jurisdiction_pack_id_mismatches(
    coverage: dict[str, Any],
) -> list[dict[str, Any]]:
    comparisons = {
        "jurisdiction_pack_scope_ids_match_direct_matrix": (
            {
                "jurisdiction_scope_count": coverage["jurisdiction_pack_scope_count"],
                "jurisdiction_scope_ids": coverage["jurisdiction_pack_scope_ids"],
            },
            {
                "jurisdiction_scope_count": coverage["curation_jurisdiction_pack_scope_count"],
                "jurisdiction_scope_ids": coverage["curation_jurisdiction_pack_scope_ids"],
            },
        ),
        "jurisdiction_pack_domain_lens_ids_match_direct_matrix": (
            {
                "domain_lens_count": coverage["jurisdiction_pack_domain_lens_count"],
                "domain_lens_ids": coverage["jurisdiction_pack_domain_lens_ids"],
            },
            {
                "domain_lens_count": coverage[
                    "curation_jurisdiction_pack_domain_lens_count"
                ],
                "domain_lens_ids": coverage[
                    "curation_jurisdiction_pack_domain_lens_ids"
                ],
            },
        ),
    }
    mismatches: list[dict[str, Any]] = []
    for rule, (expected, actual) in comparisons.items():
        if actual != expected:
            mismatches.append({
                "artifact_id": "curation_bundle.jurisdiction_pack_matrix",
                "rule": rule,
                "expected": _safe_jurisdiction_id_fields(expected),
                "actual": _safe_jurisdiction_id_fields(actual),
            })
    return mismatches


def _readiness_blocker_coverage(
    artifact_docs: dict[str, Any],
    lower_artifact_docs: dict[str, Any],
) -> dict[str, Any]:
    readiness_doc = artifact_docs.get("readiness_bundle")
    readiness = _summary(readiness_doc)
    readiness_domain = _component_summary(readiness_doc, "domain_curation_bundle")
    readiness_regulatory = _component_summary(readiness_doc, "regulatory_curation_bundle")
    curation = _summary(artifact_docs.get("curation_bundle"))
    curation_readiness = _component_summary(
        artifact_docs.get("curation_bundle"),
        "readiness_bundle",
    )
    direct_domain = _summary(lower_artifact_docs.get("domain_curation_bundle"))
    direct_regulatory = _summary(lower_artifact_docs.get("regulatory_curation_bundle"))
    readiness_count_values = [
        readiness.get("worker_prompt_count"),
        readiness.get("worker_prompts_blocked_for_comparable_run"),
        readiness.get("worker_verified_local_law_rows"),
        readiness.get("worker_source_object_tasks"),
        readiness.get("worker_scope_refinement_tasks"),
        readiness.get("regulatory_pattern_count"),
        readiness.get("regulatory_candidate_count"),
        readiness.get("regulatory_seed_scaffold_operations"),
    ]
    return {
        "readiness_worker_prompt_count": readiness.get("worker_prompt_count"),
        "readiness_worker_prompts_blocked_for_comparable_run": readiness.get(
            "worker_prompts_blocked_for_comparable_run"
        ),
        "readiness_worker_verified_local_law_rows": readiness.get(
            "worker_verified_local_law_rows"
        ),
        "readiness_worker_source_object_tasks": readiness.get("worker_source_object_tasks"),
        "readiness_worker_scope_refinement_tasks": readiness.get(
            "worker_scope_refinement_tasks"
        ),
        "readiness_regulatory_pattern_count": readiness.get("regulatory_pattern_count"),
        "readiness_regulatory_candidate_count": readiness.get("regulatory_candidate_count"),
        "readiness_regulatory_seed_scaffold_operations": readiness.get(
            "regulatory_seed_scaffold_operations"
        ),
        "readiness_blocker_counts_present": all(
            isinstance(value, int) for value in readiness_count_values
        ),
        "readiness_domain_prompt_count": readiness_domain.get("prompt_count"),
        "readiness_domain_prompts_blocked_for_comparable_run": readiness_domain.get(
            "prompts_blocked_for_comparable_run"
        ),
        "readiness_domain_verified_local_law_rows": readiness_domain.get(
            "verified_local_law_rows"
        ),
        "readiness_domain_source_object_tasks": readiness_domain.get("source_object_tasks"),
        "readiness_domain_scope_refinement_tasks": readiness_domain.get(
            "scope_refinement_tasks"
        ),
        "readiness_domain_ready_for_comparable_run": readiness_domain.get(
            "ready_for_comparable_run"
        ),
        "direct_domain_prompt_count": direct_domain.get("prompt_count"),
        "direct_domain_prompts_blocked_for_comparable_run": direct_domain.get(
            "prompts_blocked_for_comparable_run"
        ),
        "direct_domain_verified_local_law_rows": direct_domain.get(
            "verified_local_law_rows"
        ),
        "direct_domain_source_object_tasks": direct_domain.get("source_object_tasks"),
        "direct_domain_scope_refinement_tasks": direct_domain.get(
            "scope_refinement_tasks"
        ),
        "direct_domain_ready_for_comparable_run": direct_domain.get(
            "ready_for_comparable_run"
        ),
        "readiness_regulatory_pattern_count_from_component": readiness_regulatory.get(
            "pattern_count"
        ),
        "readiness_regulatory_candidate_count_from_component": readiness_regulatory.get(
            "candidate_count"
        ),
        "readiness_regulatory_accepted_domain_seed_proposals": readiness_regulatory.get(
            "validation_accepted_domain_seed_proposals"
        ),
        "readiness_regulatory_ready_for_prompt_generation": readiness_regulatory.get(
            "ready_for_prompt_generation"
        ),
        "readiness_regulatory_ready_for_comparable_scoring": readiness_regulatory.get(
            "ready_for_comparable_scoring"
        ),
        "direct_regulatory_pattern_count": direct_regulatory.get("pattern_count"),
        "direct_regulatory_candidate_count": direct_regulatory.get("candidate_count"),
        "direct_regulatory_seed_scaffold_operations": direct_regulatory.get(
            "seed_scaffold_operations"
        ),
        "direct_regulatory_accepted_domain_seed_proposals": direct_regulatory.get(
            "validation_accepted_domain_seed_proposals"
        ),
        "direct_regulatory_ready_for_prompt_generation": direct_regulatory.get(
            "ready_for_prompt_generation"
        ),
        "direct_regulatory_ready_for_comparable_scoring": direct_regulatory.get(
            "ready_for_comparable_scoring"
        ),
        "curation_worker_prompt_count": curation.get("worker_prompt_count"),
        "curation_worker_prompts_blocked_for_comparable_run": curation.get(
            "worker_prompts_blocked_for_comparable_run"
        ),
        "curation_worker_verified_local_law_rows": curation.get(
            "worker_verified_local_law_rows"
        ),
        "curation_worker_source_object_tasks": curation.get(
            "worker_source_object_tasks"
        ),
        "curation_worker_scope_refinement_tasks": curation.get(
            "worker_scope_refinement_tasks"
        ),
        "curation_regulatory_pattern_count": curation.get("regulatory_pattern_count"),
        "curation_regulatory_candidate_count": curation.get(
            "regulatory_candidate_count"
        ),
        "curation_regulatory_seed_scaffold_operations": curation.get(
            "regulatory_seed_scaffold_operations"
        ),
        "curation_readiness_worker_prompt_count": curation_readiness.get(
            "worker_prompt_count"
        ),
        "curation_readiness_worker_prompts_blocked_for_comparable_run": (
            curation_readiness.get("worker_prompts_blocked_for_comparable_run")
        ),
        "curation_readiness_worker_verified_local_law_rows": curation_readiness.get(
            "worker_verified_local_law_rows"
        ),
        "curation_readiness_ready_for_comparable_scoring": curation_readiness.get(
            "ready_for_comparable_scoring"
        ),
    }


def _readiness_blocker_mismatches(
    coverage: dict[str, Any],
    *,
    require_lower_level: bool,
) -> list[dict[str, Any]]:
    comparisons: dict[str, tuple[dict[str, Any], dict[str, Any]]] = {
        "readiness_bundle.domain_curation_bundle": (
            {
                "prompt_count": coverage["readiness_worker_prompt_count"],
                "prompts_blocked_for_comparable_run": coverage[
                    "readiness_worker_prompts_blocked_for_comparable_run"
                ],
                "verified_local_law_rows": coverage[
                    "readiness_worker_verified_local_law_rows"
                ],
                "source_object_tasks": coverage["readiness_worker_source_object_tasks"],
                "scope_refinement_tasks": coverage[
                    "readiness_worker_scope_refinement_tasks"
                ],
                "ready_for_comparable_run": False,
            },
            {
                "prompt_count": coverage["readiness_domain_prompt_count"],
                "prompts_blocked_for_comparable_run": coverage[
                    "readiness_domain_prompts_blocked_for_comparable_run"
                ],
                "verified_local_law_rows": coverage[
                    "readiness_domain_verified_local_law_rows"
                ],
                "source_object_tasks": coverage["readiness_domain_source_object_tasks"],
                "scope_refinement_tasks": coverage[
                    "readiness_domain_scope_refinement_tasks"
                ],
                "ready_for_comparable_run": coverage[
                    "readiness_domain_ready_for_comparable_run"
                ],
            },
        ),
        "readiness_bundle.regulatory_curation_bundle": (
            {
                "pattern_count": coverage["readiness_regulatory_pattern_count"],
                "candidate_count": coverage["readiness_regulatory_candidate_count"],
                "validation_accepted_domain_seed_proposals": 0,
                "ready_for_prompt_generation": False,
                "ready_for_comparable_scoring": False,
            },
            {
                "pattern_count": coverage[
                    "readiness_regulatory_pattern_count_from_component"
                ],
                "candidate_count": coverage[
                    "readiness_regulatory_candidate_count_from_component"
                ],
                "validation_accepted_domain_seed_proposals": coverage[
                    "readiness_regulatory_accepted_domain_seed_proposals"
                ],
                "ready_for_prompt_generation": coverage[
                    "readiness_regulatory_ready_for_prompt_generation"
                ],
                "ready_for_comparable_scoring": coverage[
                    "readiness_regulatory_ready_for_comparable_scoring"
                ],
            },
        ),
        "curation_bundle.summary": (
            {
                "worker_prompt_count": coverage["readiness_worker_prompt_count"],
                "worker_prompts_blocked_for_comparable_run": coverage[
                    "readiness_worker_prompts_blocked_for_comparable_run"
                ],
                "worker_verified_local_law_rows": coverage[
                    "readiness_worker_verified_local_law_rows"
                ],
                "worker_source_object_tasks": coverage[
                    "readiness_worker_source_object_tasks"
                ],
                "worker_scope_refinement_tasks": coverage[
                    "readiness_worker_scope_refinement_tasks"
                ],
                "regulatory_pattern_count": coverage[
                    "readiness_regulatory_pattern_count"
                ],
                "regulatory_candidate_count": coverage[
                    "readiness_regulatory_candidate_count"
                ],
                "regulatory_seed_scaffold_operations": coverage[
                    "readiness_regulatory_seed_scaffold_operations"
                ],
            },
            {
                "worker_prompt_count": coverage["curation_worker_prompt_count"],
                "worker_prompts_blocked_for_comparable_run": coverage[
                    "curation_worker_prompts_blocked_for_comparable_run"
                ],
                "worker_verified_local_law_rows": coverage[
                    "curation_worker_verified_local_law_rows"
                ],
                "worker_source_object_tasks": coverage[
                    "curation_worker_source_object_tasks"
                ],
                "worker_scope_refinement_tasks": coverage[
                    "curation_worker_scope_refinement_tasks"
                ],
                "regulatory_pattern_count": coverage["curation_regulatory_pattern_count"],
                "regulatory_candidate_count": coverage[
                    "curation_regulatory_candidate_count"
                ],
                "regulatory_seed_scaffold_operations": coverage[
                    "curation_regulatory_seed_scaffold_operations"
                ],
            },
        ),
        "curation_bundle.readiness_bundle": (
            {
                "worker_prompt_count": coverage["readiness_worker_prompt_count"],
                "worker_prompts_blocked_for_comparable_run": coverage[
                    "readiness_worker_prompts_blocked_for_comparable_run"
                ],
                "worker_verified_local_law_rows": coverage[
                    "readiness_worker_verified_local_law_rows"
                ],
                "ready_for_comparable_scoring": False,
            },
            {
                "worker_prompt_count": coverage[
                    "curation_readiness_worker_prompt_count"
                ],
                "worker_prompts_blocked_for_comparable_run": coverage[
                    "curation_readiness_worker_prompts_blocked_for_comparable_run"
                ],
                "worker_verified_local_law_rows": coverage[
                    "curation_readiness_worker_verified_local_law_rows"
                ],
                "ready_for_comparable_scoring": coverage[
                    "curation_readiness_ready_for_comparable_scoring"
                ],
            },
        ),
    }
    if require_lower_level:
        comparisons["lower_level.domain_curation_bundle"] = (
            {
                "prompt_count": coverage["readiness_domain_prompt_count"],
                "prompts_blocked_for_comparable_run": coverage[
                    "readiness_domain_prompts_blocked_for_comparable_run"
                ],
                "verified_local_law_rows": coverage[
                    "readiness_domain_verified_local_law_rows"
                ],
                "source_object_tasks": coverage["readiness_domain_source_object_tasks"],
                "scope_refinement_tasks": coverage[
                    "readiness_domain_scope_refinement_tasks"
                ],
                "ready_for_comparable_run": coverage[
                    "readiness_domain_ready_for_comparable_run"
                ],
            },
            {
                "prompt_count": coverage["direct_domain_prompt_count"],
                "prompts_blocked_for_comparable_run": coverage[
                    "direct_domain_prompts_blocked_for_comparable_run"
                ],
                "verified_local_law_rows": coverage[
                    "direct_domain_verified_local_law_rows"
                ],
                "source_object_tasks": coverage["direct_domain_source_object_tasks"],
                "scope_refinement_tasks": coverage[
                    "direct_domain_scope_refinement_tasks"
                ],
                "ready_for_comparable_run": coverage[
                    "direct_domain_ready_for_comparable_run"
                ],
            },
        )
        comparisons["lower_level.regulatory_curation_bundle"] = (
            {
                "pattern_count": coverage[
                    "readiness_regulatory_pattern_count_from_component"
                ],
                "candidate_count": coverage[
                    "readiness_regulatory_candidate_count_from_component"
                ],
                "seed_scaffold_operations": coverage[
                    "readiness_regulatory_seed_scaffold_operations"
                ],
                "validation_accepted_domain_seed_proposals": coverage[
                    "readiness_regulatory_accepted_domain_seed_proposals"
                ],
                "ready_for_prompt_generation": coverage[
                    "readiness_regulatory_ready_for_prompt_generation"
                ],
                "ready_for_comparable_scoring": coverage[
                    "readiness_regulatory_ready_for_comparable_scoring"
                ],
            },
            {
                "pattern_count": coverage["direct_regulatory_pattern_count"],
                "candidate_count": coverage["direct_regulatory_candidate_count"],
                "seed_scaffold_operations": coverage[
                    "direct_regulatory_seed_scaffold_operations"
                ],
                "validation_accepted_domain_seed_proposals": coverage[
                    "direct_regulatory_accepted_domain_seed_proposals"
                ],
                "ready_for_prompt_generation": coverage[
                    "direct_regulatory_ready_for_prompt_generation"
                ],
                "ready_for_comparable_scoring": coverage[
                    "direct_regulatory_ready_for_comparable_scoring"
                ],
            },
        )
    mismatches: list[dict[str, Any]] = []
    for artifact_id, (expected, actual) in comparisons.items():
        if actual != expected:
            mismatches.append({
                "artifact_id": artifact_id,
                "rule": "readiness_blocker_counts_match",
                "expected": expected,
                "actual": actual,
            })
    return mismatches


def _legal_anchor_channel_coverage(artifact_docs: dict[str, Any]) -> dict[str, Any]:
    source_matrix = _summary(artifact_docs.get("source_channel_matrix"))
    source_review = _summary(artifact_docs.get("source_channel_review_packet"))
    blueprint = _summary(artifact_docs.get("benchmark_blueprint"))
    eval_contract = _summary(artifact_docs.get("eval_contract"))
    diagnostic = _summary(artifact_docs.get("diagnostic_run_plan"))
    judge_calibration = _summary(artifact_docs.get("judge_calibration_plan"))
    transition_gate = _summary(artifact_docs.get("transition_gate"))
    readiness = _summary(artifact_docs.get("readiness_bundle"))
    next_actions = _summary(artifact_docs.get("next_actions"))
    curator_sprint = _summary(artifact_docs.get("curator_sprint"))
    curation = _summary(artifact_docs.get("curation_bundle"))
    expected_ids = blueprint.get("legal_claim_anchor_source_channel_ids")
    expected_count = blueprint.get("legal_claim_anchor_source_channel_count")
    return {
        "benchmark_legal_claim_anchor_source_channel_count": expected_count,
        "benchmark_legal_claim_anchor_source_channel_ids": expected_ids,
        "source_channel_matrix_legal_claim_anchor_source_channel_count": source_matrix.get(
            "legal_claim_anchor_source_channel_count"
        ),
        "source_channel_matrix_legal_claim_anchor_source_channel_ids": source_matrix.get(
            "legal_claim_anchor_source_channel_ids"
        ),
        "source_channel_review_legal_claim_anchor_source_channel_count": source_review.get(
            "legal_claim_anchor_source_channel_count"
        ),
        "source_channel_review_legal_claim_anchor_source_channel_ids": source_review.get(
            "legal_claim_anchor_source_channel_ids"
        ),
        "eval_legal_claim_anchor_source_channel_count": eval_contract.get(
            "legal_claim_anchor_source_channel_count"
        ),
        "eval_legal_claim_anchor_source_channel_ids": eval_contract.get(
            "legal_claim_anchor_source_channel_ids"
        ),
        "diagnostic_legal_claim_anchor_source_channel_count": diagnostic.get(
            "legal_claim_anchor_source_channel_count"
        ),
        "diagnostic_legal_claim_anchor_source_channel_ids": diagnostic.get(
            "legal_claim_anchor_source_channel_ids"
        ),
        "judge_calibration_legal_claim_anchor_source_channel_count": judge_calibration.get(
            "legal_claim_anchor_source_channel_count"
        ),
        "judge_calibration_legal_claim_anchor_source_channel_ids": judge_calibration.get(
            "legal_claim_anchor_source_channel_ids"
        ),
        "transition_gate_legal_claim_anchor_source_channel_count": transition_gate.get(
            "legal_claim_anchor_source_channel_count"
        ),
        "transition_gate_legal_claim_anchor_source_channel_ids": transition_gate.get(
            "legal_claim_anchor_source_channel_ids"
        ),
        "readiness_legal_claim_anchor_source_channel_count": readiness.get(
            "legal_claim_anchor_source_channel_count"
        ),
        "readiness_legal_claim_anchor_source_channel_ids": readiness.get(
            "legal_claim_anchor_source_channel_ids"
        ),
        "next_actions_legal_claim_anchor_source_channel_count": next_actions.get(
            "legal_claim_anchor_source_channel_count"
        ),
        "next_actions_legal_claim_anchor_source_channel_ids": next_actions.get(
            "legal_claim_anchor_source_channel_ids"
        ),
        "curator_sprint_legal_claim_anchor_source_channel_count": curator_sprint.get(
            "legal_claim_anchor_source_channel_count"
        ),
        "curator_sprint_legal_claim_anchor_source_channel_ids": curator_sprint.get(
            "legal_claim_anchor_source_channel_ids"
        ),
        "curation_benchmark_legal_claim_anchor_source_channel_count": curation.get(
            "benchmark_legal_claim_anchor_source_channel_count"
        ),
        "curation_benchmark_legal_claim_anchor_source_channel_ids": curation.get(
            "benchmark_legal_claim_anchor_source_channel_ids"
        ),
        "curation_source_channel_matrix_legal_claim_anchor_source_channel_count": curation.get(
            "source_channel_legal_claim_anchor_source_channel_count"
        ),
        "curation_source_channel_matrix_legal_claim_anchor_source_channel_ids": curation.get(
            "source_channel_legal_claim_anchor_source_channel_ids"
        ),
        "curation_source_channel_review_legal_claim_anchor_source_channel_count": curation.get(
            "source_channel_review_legal_claim_anchor_source_channel_count"
        ),
        "curation_source_channel_review_legal_claim_anchor_source_channel_ids": curation.get(
            "source_channel_review_legal_claim_anchor_source_channel_ids"
        ),
        "curation_eval_legal_claim_anchor_source_channel_count": curation.get(
            "eval_legal_claim_anchor_source_channel_count"
        ),
        "curation_eval_legal_claim_anchor_source_channel_ids": curation.get(
            "eval_legal_claim_anchor_source_channel_ids"
        ),
        "curation_diagnostic_legal_claim_anchor_source_channel_count": curation.get(
            "diagnostic_legal_claim_anchor_source_channel_count"
        ),
        "curation_diagnostic_legal_claim_anchor_source_channel_ids": curation.get(
            "diagnostic_legal_claim_anchor_source_channel_ids"
        ),
        "curation_judge_calibration_legal_claim_anchor_source_channel_count": curation.get(
            "judge_calibration_legal_claim_anchor_source_channel_count"
        ),
        "curation_judge_calibration_legal_claim_anchor_source_channel_ids": curation.get(
            "judge_calibration_legal_claim_anchor_source_channel_ids"
        ),
        "curation_transition_gate_legal_claim_anchor_source_channel_count": curation.get(
            "transition_gate_legal_claim_anchor_source_channel_count"
        ),
        "curation_transition_gate_legal_claim_anchor_source_channel_ids": curation.get(
            "transition_gate_legal_claim_anchor_source_channel_ids"
        ),
        "curation_readiness_legal_claim_anchor_source_channel_count": curation.get(
            "readiness_legal_claim_anchor_source_channel_count"
        ),
        "curation_readiness_legal_claim_anchor_source_channel_ids": curation.get(
            "readiness_legal_claim_anchor_source_channel_ids"
        ),
        "curation_next_actions_legal_claim_anchor_source_channel_count": curation.get(
            "next_actions_legal_claim_anchor_source_channel_count"
        ),
        "curation_next_actions_legal_claim_anchor_source_channel_ids": curation.get(
            "next_actions_legal_claim_anchor_source_channel_ids"
        ),
        "curation_curator_sprint_legal_claim_anchor_source_channel_count": curation.get(
            "curator_sprint_legal_claim_anchor_source_channel_count"
        ),
        "curation_curator_sprint_legal_claim_anchor_source_channel_ids": curation.get(
            "curator_sprint_legal_claim_anchor_source_channel_ids"
        ),
        "channel_ids_present": isinstance(expected_ids, list) and bool(expected_ids),
        "channel_count_present": isinstance(expected_count, int),
    }


def _legal_anchor_channel_mismatches(
    coverage: dict[str, Any],
) -> list[dict[str, Any]]:
    expected_ids = coverage["benchmark_legal_claim_anchor_source_channel_ids"]
    expected_count = coverage["benchmark_legal_claim_anchor_source_channel_count"]
    comparisons = {
        "source_channel_matrix": (
            coverage["source_channel_matrix_legal_claim_anchor_source_channel_count"],
            coverage["source_channel_matrix_legal_claim_anchor_source_channel_ids"],
        ),
        "source_channel_review_packet": (
            coverage["source_channel_review_legal_claim_anchor_source_channel_count"],
            coverage["source_channel_review_legal_claim_anchor_source_channel_ids"],
        ),
        "eval_contract": (
            coverage["eval_legal_claim_anchor_source_channel_count"],
            coverage["eval_legal_claim_anchor_source_channel_ids"],
        ),
        "diagnostic_run_plan": (
            coverage["diagnostic_legal_claim_anchor_source_channel_count"],
            coverage["diagnostic_legal_claim_anchor_source_channel_ids"],
        ),
        "judge_calibration_plan": (
            coverage["judge_calibration_legal_claim_anchor_source_channel_count"],
            coverage["judge_calibration_legal_claim_anchor_source_channel_ids"],
        ),
        "transition_gate": (
            coverage["transition_gate_legal_claim_anchor_source_channel_count"],
            coverage["transition_gate_legal_claim_anchor_source_channel_ids"],
        ),
        "readiness_bundle": (
            coverage["readiness_legal_claim_anchor_source_channel_count"],
            coverage["readiness_legal_claim_anchor_source_channel_ids"],
        ),
        "next_actions": (
            coverage["next_actions_legal_claim_anchor_source_channel_count"],
            coverage["next_actions_legal_claim_anchor_source_channel_ids"],
        ),
        "curator_sprint": (
            coverage["curator_sprint_legal_claim_anchor_source_channel_count"],
            coverage["curator_sprint_legal_claim_anchor_source_channel_ids"],
        ),
        "curation_bundle.benchmark_blueprint": (
            coverage["curation_benchmark_legal_claim_anchor_source_channel_count"],
            coverage["curation_benchmark_legal_claim_anchor_source_channel_ids"],
        ),
        "curation_bundle.source_channel_matrix": (
            coverage["curation_source_channel_matrix_legal_claim_anchor_source_channel_count"],
            coverage["curation_source_channel_matrix_legal_claim_anchor_source_channel_ids"],
        ),
        "curation_bundle.source_channel_review_packet": (
            coverage["curation_source_channel_review_legal_claim_anchor_source_channel_count"],
            coverage["curation_source_channel_review_legal_claim_anchor_source_channel_ids"],
        ),
        "curation_bundle.eval_contract": (
            coverage["curation_eval_legal_claim_anchor_source_channel_count"],
            coverage["curation_eval_legal_claim_anchor_source_channel_ids"],
        ),
        "curation_bundle.diagnostic_run_plan": (
            coverage["curation_diagnostic_legal_claim_anchor_source_channel_count"],
            coverage["curation_diagnostic_legal_claim_anchor_source_channel_ids"],
        ),
        "curation_bundle.judge_calibration_plan": (
            coverage["curation_judge_calibration_legal_claim_anchor_source_channel_count"],
            coverage["curation_judge_calibration_legal_claim_anchor_source_channel_ids"],
        ),
        "curation_bundle.transition_gate": (
            coverage["curation_transition_gate_legal_claim_anchor_source_channel_count"],
            coverage["curation_transition_gate_legal_claim_anchor_source_channel_ids"],
        ),
        "curation_bundle.readiness_bundle": (
            coverage["curation_readiness_legal_claim_anchor_source_channel_count"],
            coverage["curation_readiness_legal_claim_anchor_source_channel_ids"],
        ),
        "curation_bundle.next_actions": (
            coverage["curation_next_actions_legal_claim_anchor_source_channel_count"],
            coverage["curation_next_actions_legal_claim_anchor_source_channel_ids"],
        ),
        "curation_bundle.curator_sprint": (
            coverage["curation_curator_sprint_legal_claim_anchor_source_channel_count"],
            coverage["curation_curator_sprint_legal_claim_anchor_source_channel_ids"],
        ),
    }
    mismatches: list[dict[str, Any]] = []
    for artifact_id, (actual_count, actual_ids) in comparisons.items():
        if actual_count != expected_count or actual_ids != expected_ids:
            mismatches.append({
                "artifact_id": artifact_id,
                "rule": "legal_claim_anchor_source_channels_match_benchmark_blueprint",
                "expected": _safe_legal_anchor_id_fields({
                    "legal_claim_anchor_source_channel_count": expected_count,
                    "legal_claim_anchor_source_channel_ids": expected_ids,
                }),
                "actual": _safe_legal_anchor_id_fields({
                    "legal_claim_anchor_source_channel_count": actual_count,
                    "legal_claim_anchor_source_channel_ids": actual_ids,
                }),
            })
    return mismatches


def _component_validator(
    artifact_id: str,
    *,
    domain_id: str,
    project_config_path: pathlib.Path,
    registry_path: pathlib.Path,
    regulatory_catalog_path: pathlib.Path,
    component_dir: pathlib.Path,
    compare_current_chain: bool,
) -> Callable[[Any, pathlib.Path], dict[str, Any]]:
    common_project = {
        "registry_path": registry_path,
        "regulatory_catalog_path": regulatory_catalog_path,
        "compare_current_chain": compare_current_chain,
    }
    common_domain = {
        "domain_id": domain_id,
        "registry_path": registry_path,
        "regulatory_catalog_path": regulatory_catalog_path,
        "compare_current_chain": compare_current_chain,
    }
    if artifact_id == "project_plan":
        return lambda doc, path: project_plan_validator.validate_project_plan(
            doc,
            plan_path=path,
            config_path=project_config_path,
            **common_project,
        )
    if artifact_id == "jurisdiction_pack_matrix":
        return lambda doc, path: jurisdiction_validator.validate_jurisdiction_pack_matrix(
            doc,
            matrix_path=path,
            project_config_path=project_config_path,
            registry_path=registry_path,
            regulatory_catalog_path=regulatory_catalog_path,
            compare_current_chain=compare_current_chain,
        )
    if artifact_id == "source_channel_matrix":
        return lambda doc, path: source_matrix_validator.validate_source_channel_matrix(
            doc,
            matrix_path=path,
            config_path=project_config_path,
            **common_project,
        )
    if artifact_id == "source_channel_review_packet":
        return lambda doc, path: source_review_validator.validate_source_channel_review_packet(
            doc,
            packet_path=path,
            config_path=project_config_path,
            **common_project,
        )
    if artifact_id == "benchmark_blueprint":
        return lambda doc, path: benchmark_validator.validate_benchmark_blueprint(
            doc,
            blueprint_path=path,
            config_path=project_config_path,
            component_dir=component_dir,
            **common_domain,
        )
    if artifact_id == "eval_contract":
        return lambda doc, path: eval_validator.validate_eval_contract(
            doc,
            contract_path=path,
            config_path=project_config_path,
            component_dir=component_dir,
            **common_domain,
        )
    if artifact_id == "diagnostic_run_plan":
        return lambda doc, path: diagnostic_validator.validate_diagnostic_run_plan(
            doc,
            plan_path=path,
            config_path=project_config_path,
            component_dir=component_dir,
            **common_domain,
        )
    if artifact_id == "judge_calibration_plan":
        return lambda doc, path: calibration_validator.validate_judge_calibration_plan(
            doc,
            plan_path=path,
            config_path=project_config_path,
            component_dir=component_dir,
            **common_domain,
        )
    if artifact_id == "transition_gate":
        return lambda doc, path: transition_validator.validate_transition_gate(
            doc,
            gate_path=path,
            config_path=project_config_path,
            component_dir=component_dir,
            **common_domain,
        )
    if artifact_id == "readiness_bundle":
        return lambda doc, path: readiness_validator.validate_readiness_bundle(
            doc,
            bundle_path=path,
            project_config_path=project_config_path,
            component_dir=component_dir,
            **common_domain,
        )
    if artifact_id == "next_actions":
        return lambda doc, path: next_actions_validator.validate_next_actions(
            doc,
            backlog_path=path,
            project_config_path=project_config_path,
            component_dir=component_dir,
            **common_domain,
        )
    if artifact_id == "curator_sprint":
        return lambda doc, path: sprint_validator.validate_curator_sprint(
            doc,
            sprint_path=path,
            project_config_path=project_config_path,
            **common_domain,
        )
    if artifact_id == "curation_bundle":
        return lambda doc, path: curation_validator.validate_curation_bundle(
            doc,
            bundle_path=path,
            expected_domain=domain_id,
            project_config_path=project_config_path,
            registry_path=registry_path,
            regulatory_catalog_path=regulatory_catalog_path,
            component_dir=component_dir,
            compare_current_chain=compare_current_chain,
        )
    raise KeyError(f"unknown global protections artifact: {artifact_id}")


def _truthy_comparable_paths(value: Any, *, path: str = "$") -> list[str]:
    findings: list[str] = []
    if isinstance(value, dict):
        for key, child in value.items():
            key_text = str(key)
            child_path = f"{path}.{key_text}"
            lowered = key_text.lower()
            readiness_key = (
                lowered in {"ready_for_comparable_scoring", "ready_for_comparable_run"}
                or lowered.startswith("ready_for_comparable_")
                or lowered.startswith("prompts_ready_for_comparable_")
                or lowered.endswith("_ready_for_comparable_scoring_count")
                or lowered.endswith("_ready_for_comparable_run_count")
            )
            if readiness_key and (child is True or (isinstance(child, int) and child > 0)):
                findings.append(child_path)
            findings.extend(_truthy_comparable_paths(child, path=child_path))
    elif isinstance(value, list):
        for idx, child in enumerate(value):
            findings.extend(_truthy_comparable_paths(child, path=f"{path}[{idx}]"))
    return findings


def _generic_lower_level_report(doc: Any, *, artifact_id: str, artifact_path: pathlib.Path) -> dict[str, Any]:
    summary = doc.get("summary") if isinstance(doc, dict) and isinstance(doc.get("summary"), dict) else {}
    meta = doc.get("_meta") if isinstance(doc, dict) and isinstance(doc.get("_meta"), dict) else {}
    valid = summary.get("valid")
    if valid is None:
        valid = summary.get("ok")
    if valid is None:
        valid = meta.get("validation_ok")
    issues = list(meta.get("issues") or []) if isinstance(meta.get("issues"), list) else []
    status_ok = bool(valid) if valid is not None else not issues
    comparable_paths = _truthy_comparable_paths(doc)
    checks = [
        _check(
            "lower_level_artifact_is_object",
            isinstance(doc, dict),
            expected="object",
            actual=type(doc).__name__,
        ),
        _check(
            "lower_level_artifact_status_ok",
            status_ok,
            expected=True,
            actual={"valid": valid, "issues": issues},
        ),
        _check(
            "lower_level_comparable_flags_blocked",
            not comparable_paths,
            expected=[],
            actual=comparable_paths,
        ),
    ]
    failed = _failed_ids(checks)
    return {
        "_meta": {
            "schema_version": "global_protections_lower_level_artifact_validation.v1",
            "artifact_id": artifact_id,
            "source_path": _artifact_path(artifact_path),
        },
        "summary": {
            "valid": not failed,
            "check_count": len(checks),
            "failed_check_count": len(failed),
            "failed_check_ids": failed,
            "ready_for_comparable_scoring": bool(comparable_paths),
        },
        "checks": checks,
    }


def _lower_level_component_validator(
    artifact_id: str,
    *,
    domain_id: str,
    registry_path: pathlib.Path,
    regulatory_catalog_path: pathlib.Path,
    component_dir: pathlib.Path,
    compare_current_chain: bool,
) -> Callable[[Any, pathlib.Path], dict[str, Any]]:
    if artifact_id == "domain_source_review_packet":
        return lambda doc, path: _generic_lower_level_report(
            domain_source_review_validator.validate_source_review_packet(doc, domain_id=domain_id),
            artifact_id=artifact_id,
            artifact_path=path,
        )
    if artifact_id == "domain_curation_bundle":
        return lambda doc, path: domain_curation_validator.validate_domain_curation_bundle(
            doc,
            bundle_path=path,
            domain_id=domain_id,
            component_dir=component_dir,
            compare_current_chain=compare_current_chain,
        )
    if artifact_id == "regulatory_domain_intake_packet":
        return lambda doc, path: _generic_lower_level_report(
            regulatory_intake_validator.validate_intake_packet(
                doc,
                packet_path=path,
                registry_path=registry_path,
            ),
            artifact_id=artifact_id,
            artifact_path=path,
        )
    if artifact_id == "regulatory_curation_bundle":
        return lambda doc, path: regulatory_curation_validator.validate_regulatory_curation_bundle(
            doc,
            bundle_path=path,
            config_path=regulatory_catalog_path,
            registry_path=registry_path,
            component_dir=component_dir,
            compare_current_chain=compare_current_chain,
        )
    return lambda doc, path: _generic_lower_level_report(
        doc,
        artifact_id=artifact_id,
        artifact_path=path,
    )


def _validate_lower_level_artifacts(
    *,
    domain_id: str,
    registry_path: pathlib.Path,
    regulatory_catalog_path: pathlib.Path,
    component_dir: pathlib.Path,
    compare_current_chain: bool,
    specs: list[dict[str, str]] | None = None,
) -> list[dict[str, Any]]:
    rows: list[dict[str, Any]] = []
    for spec in specs or _lower_level_artifact_specs(component_dir, domain_id=domain_id):
        artifact_id = spec["artifact_id"]
        json_path = pathlib.Path(spec["json_path"])
        markdown_path = pathlib.Path(spec["markdown_path"])
        doc = _load_json(json_path)
        if doc is None:
            rows.append(
                _missing_row(
                    artifact_id,
                    json_path,
                    markdown_path,
                    markdown_disallowed_terms=LOWER_LEVEL_MARKDOWN_DISALLOWED_TERMS,
                )
            )
            continue
        validate = _lower_level_component_validator(
            artifact_id,
            domain_id=domain_id,
            registry_path=registry_path,
            regulatory_catalog_path=regulatory_catalog_path,
            component_dir=component_dir,
            compare_current_chain=compare_current_chain,
        )
        validation_report = validate(doc, json_path)
        validation_report = _with_lower_level_bundle_path_check(
            validation_report,
            doc,
            artifact_id=artifact_id,
            component_dir=component_dir,
            domain_id=domain_id,
        )
        rows.append(
            _summary_row(
                artifact_id,
                json_path,
                markdown_path,
                validation_report,
                markdown_disallowed_terms=LOWER_LEVEL_MARKDOWN_DISALLOWED_TERMS,
            )
        )
    return rows


def validate_saved_artifacts(
    *,
    domain_id: str = DEFAULT_DOMAIN,
    project_config_path: pathlib.Path = project_plan_builder.CONFIG,
    registry_path: pathlib.Path = project_plan_builder.REGISTRY,
    regulatory_catalog_path: pathlib.Path = project_plan_builder.REGULATORY_CATALOG,
    component_dir: pathlib.Path = OUT_DIR,
    compare_current_chain: bool = True,
    validate_lower_components: bool = False,
) -> dict[str, Any]:
    rows: list[dict[str, Any]] = []
    artifact_docs: dict[str, Any] = {}
    for spec in _artifact_specs(component_dir):
        artifact_id = spec["artifact_id"]
        json_path = pathlib.Path(spec["json_path"])
        markdown_path = pathlib.Path(spec["markdown_path"])
        doc = _load_json(json_path)
        if doc is None:
            rows.append(_missing_row(artifact_id, json_path, markdown_path))
            continue
        artifact_docs[artifact_id] = doc
        validate = _component_validator(
            artifact_id,
            domain_id=domain_id,
            project_config_path=project_config_path,
            registry_path=registry_path,
            regulatory_catalog_path=regulatory_catalog_path,
            component_dir=component_dir,
            compare_current_chain=compare_current_chain,
        )
        rows.append(_summary_row(artifact_id, json_path, markdown_path, validate(doc, json_path)))

    lower_specs = (
        _lower_level_artifact_specs(component_dir, domain_id=domain_id)
        if validate_lower_components
        else []
    )
    lower_artifact_docs: dict[str, Any] = {}
    for spec in lower_specs:
        doc = _load_json(pathlib.Path(spec["json_path"]))
        if doc is not None:
            lower_artifact_docs[spec["artifact_id"]] = doc
    lower_expected_ids = [spec["artifact_id"] for spec in lower_specs]
    lower_rows = (
        _validate_lower_level_artifacts(
            domain_id=domain_id,
            registry_path=registry_path,
            regulatory_catalog_path=regulatory_catalog_path,
            component_dir=component_dir,
            compare_current_chain=compare_current_chain,
            specs=lower_specs,
        )
        if validate_lower_components
        else []
    )
    lower_actual_ids = [row["artifact_id"] for row in lower_rows]

    failed_artifacts = [row["artifact_id"] for row in rows if row["valid"] is not True]
    missing_artifacts = [row["artifact_id"] for row in rows if row["readable"] is not True]
    missing_markdown = [row["artifact_id"] for row in rows if row["markdown_readable"] is not True]
    unsafe_markdown = [row["artifact_id"] for row in rows if row["markdown_safe"] is not True]
    lower_failed_artifacts = [row["artifact_id"] for row in lower_rows if row["valid"] is not True]
    lower_missing_artifacts = [row["artifact_id"] for row in lower_rows if row["readable"] is not True]
    lower_missing_markdown = [row["artifact_id"] for row in lower_rows if row["markdown_readable"] is not True]
    lower_unsafe_markdown = [row["artifact_id"] for row in lower_rows if row["markdown_safe"] is not True]
    artifact_path_drift = _artifact_path_agreement_drift(
        component_dir=component_dir,
        domain_id=domain_id,
        require_optional_paths=validate_lower_components,
    )
    scoring_ready_artifacts = [
        row["artifact_id"] for row in rows if row.get("ready_for_comparable_scoring") is True
    ]
    lower_scoring_ready_artifacts = [
        row["artifact_id"] for row in lower_rows if row.get("ready_for_comparable_scoring") is True
    ]
    total_checks = sum(int(row.get("check_count") or 0) for row in rows)
    total_failed = sum(int(row.get("failed_check_count") or 0) for row in rows)
    lower_total_checks = sum(int(row.get("check_count") or 0) for row in lower_rows)
    lower_total_failed = sum(int(row.get("failed_check_count") or 0) for row in lower_rows)
    phase_coverage = _curation_phase_coverage(artifact_docs.get("curation_bundle"))
    direct_phase_coverage_mismatches = _direct_phase_coverage_mismatches(rows, phase_coverage)
    jurisdiction_pack_id_coverage = _jurisdiction_pack_id_coverage(artifact_docs)
    jurisdiction_pack_id_mismatches = _jurisdiction_pack_id_mismatches(
        jurisdiction_pack_id_coverage
    )
    safe_jurisdiction_pack_id_coverage = _safe_jurisdiction_pack_id_coverage(
        jurisdiction_pack_id_coverage
    )
    legal_anchor_channel_coverage = _legal_anchor_channel_coverage(artifact_docs)
    legal_anchor_channel_mismatches = _legal_anchor_channel_mismatches(
        legal_anchor_channel_coverage
    )
    safe_legal_anchor_channel_coverage = _safe_legal_anchor_channel_coverage(
        legal_anchor_channel_coverage
    )
    readiness_blocker_coverage = _readiness_blocker_coverage(
        artifact_docs,
        lower_artifact_docs,
    )
    readiness_blocker_mismatches = _readiness_blocker_mismatches(
        readiness_blocker_coverage,
        require_lower_level=validate_lower_components,
    )
    next_actions_row = _row_by_artifact_id(rows, "next_actions")
    curator_sprint_row = _row_by_artifact_id(rows, "curator_sprint")
    summary = {
        "valid": not failed_artifacts and not lower_failed_artifacts,
        "artifact_count": len(rows),
        "valid_artifact_count": len(rows) - len(failed_artifacts),
        "failed_artifact_count": len(failed_artifacts),
        "missing_or_unreadable_artifact_count": len(missing_artifacts),
        "markdown_artifact_count": len(rows),
        "missing_or_unreadable_markdown_count": len(missing_markdown),
        "unsafe_markdown_count": len(unsafe_markdown),
        "artifact_path_mismatch_count": len(artifact_path_drift),
        "total_check_count": total_checks,
        "total_failed_check_count": total_failed,
        "validate_lower_components": validate_lower_components,
        "lower_level_expected_artifact_count": len(lower_specs),
        "lower_level_expected_artifact_ids": lower_expected_ids,
        "lower_level_artifact_count": len(lower_rows),
        "lower_level_valid_artifact_count": len(lower_rows) - len(lower_failed_artifacts),
        "lower_level_failed_artifact_count": len(lower_failed_artifacts),
        "lower_level_missing_or_unreadable_artifact_count": len(lower_missing_artifacts),
        "lower_level_missing_or_unreadable_markdown_count": len(lower_missing_markdown),
        "lower_level_unsafe_markdown_count": len(lower_unsafe_markdown),
        "lower_level_total_check_count": lower_total_checks,
        "lower_level_total_failed_check_count": lower_total_failed,
        "curation_bundle_next_execution_phase_count": phase_coverage["next_execution_phase_count"],
        "curation_bundle_next_phase_covered_actions": phase_coverage[
            "next_execution_phase_covered_actions"
        ],
        "curation_bundle_curator_execution_phase_count": phase_coverage[
            "curator_execution_phase_count"
        ],
        "curation_bundle_curator_phase_covered_actions": phase_coverage[
            "curator_execution_phase_covered_actions"
        ],
        "curation_bundle_next_action_count": phase_coverage["next_action_count"],
        "curation_bundle_curator_phase_expected_actions": phase_coverage[
            "curator_expected_phase_covered_actions"
        ],
        "next_actions_execution_phase_count": next_actions_row.get("execution_phase_count"),
        "next_actions_phase_covered_actions": next_actions_row.get(
            "execution_phase_covered_action_count"
        ),
        "curator_sprint_execution_phase_count": curator_sprint_row.get("execution_phase_count"),
        "curator_sprint_phase_covered_actions": curator_sprint_row.get(
            "execution_phase_covered_action_count"
        ),
        "phase_coverage_mismatch_count": len(direct_phase_coverage_mismatches),
        "phase_coverage_mismatches": direct_phase_coverage_mismatches,
        **safe_jurisdiction_pack_id_coverage,
        "jurisdiction_pack_id_mismatch_count": len(jurisdiction_pack_id_mismatches),
        "jurisdiction_pack_id_mismatches": jurisdiction_pack_id_mismatches,
        **safe_legal_anchor_channel_coverage,
        "legal_anchor_channel_mismatch_count": len(legal_anchor_channel_mismatches),
        "legal_anchor_channel_mismatches": legal_anchor_channel_mismatches,
        **readiness_blocker_coverage,
        "readiness_blocker_mismatch_count": len(readiness_blocker_mismatches),
        "readiness_blocker_mismatches": readiness_blocker_mismatches,
        "failed_artifact_ids": failed_artifacts,
        "missing_or_unreadable_artifact_ids": missing_artifacts,
        "missing_or_unreadable_markdown_ids": missing_markdown,
        "unsafe_markdown_ids": unsafe_markdown,
        "lower_level_failed_artifact_ids": lower_failed_artifacts,
        "lower_level_missing_or_unreadable_artifact_ids": lower_missing_artifacts,
        "lower_level_missing_or_unreadable_markdown_ids": lower_missing_markdown,
        "lower_level_unsafe_markdown_ids": lower_unsafe_markdown,
        "artifact_path_mismatches": artifact_path_drift,
        "ready_for_comparable_scoring": bool(scoring_ready_artifacts or lower_scoring_ready_artifacts),
        "scoring_ready_artifact_ids": scoring_ready_artifacts,
        "lower_level_scoring_ready_artifact_ids": lower_scoring_ready_artifacts,
    }
    compact_report = {
        "_meta": {
            "schema_version": "global_protections_saved_artifacts_validation.v1",
            "domain": domain_id,
            "project_config": _artifact_path(project_config_path),
            "registry_path": _artifact_path(registry_path),
            "regulatory_catalog_path": _artifact_path(regulatory_catalog_path),
            "component_dir": _artifact_path(component_dir),
            "compare_current_chain": compare_current_chain,
            "validate_lower_components": validate_lower_components,
            "status": (
                "read-only saved-artifact validation suite; not legal advice, not source "
                "verification, not prompt generation, and not comparable benchmark evidence"
            ),
        },
        "summary": summary,
        "artifact_results": rows,
        "lower_level_artifact_results": lower_rows,
    }
    encoded = json.dumps(compact_report, ensure_ascii=False)
    disallowed = [term for term in DISALLOWED_TERMS if term in encoded]
    privacy_scan = project_plan_builder._scan_privacy(compact_report)
    checks = [
        _check("expected_artifact_count_present", len(rows) == 13, expected=13, actual=len(rows)),
        _check("all_artifacts_readable", not missing_artifacts, expected=[], actual=missing_artifacts),
        _check("all_markdown_reports_readable", not missing_markdown, expected=[], actual=missing_markdown),
        _check("all_markdown_reports_safe", not unsafe_markdown, expected=[], actual=unsafe_markdown),
        _check("curation_bundle_artifact_paths_match_files", not artifact_path_drift, expected=[], actual=artifact_path_drift),
        _check("all_artifact_validations_pass", not failed_artifacts, expected=[], actual=failed_artifacts),
        _check("all_comparable_scoring_flags_blocked", not scoring_ready_artifacts, expected=[], actual=scoring_ready_artifacts),
        _check("suite_contains_no_disallowed_text", not disallowed, expected=[], actual=disallowed),
        _check("privacy_scan_ok", privacy_scan.get("ok") is True, expected=True, actual=privacy_scan.get("counts")),
        _check(
            "curation_bundle_phase_coverage_present",
            phase_coverage["phase_coverage_present"],
            expected=True,
            actual={
                "next_execution_phase_count": phase_coverage["next_execution_phase_count"],
                "next_execution_phase_covered_actions": phase_coverage[
                    "next_execution_phase_covered_actions"
                ],
                "curator_execution_phase_count": phase_coverage[
                    "curator_execution_phase_count"
                ],
                "curator_execution_phase_covered_actions": phase_coverage[
                    "curator_execution_phase_covered_actions"
                ],
            },
        ),
        _check(
            "curation_bundle_phase_counts_match",
            phase_coverage["phase_counts_match"],
            expected=phase_coverage["next_execution_phase_count"],
            actual=phase_coverage["curator_execution_phase_count"],
        ),
        _check(
            "curation_bundle_phase_covered_action_counts_match",
            phase_coverage["phase_covered_action_counts_match"],
            expected=phase_coverage["next_execution_phase_covered_actions"],
            actual=phase_coverage["curator_execution_phase_covered_actions"],
        ),
        _check(
            "curation_bundle_next_phase_coverage_matches_action_count",
            phase_coverage["next_phase_coverage_matches_action_count"],
            expected=phase_coverage["next_action_count"],
            actual=phase_coverage["next_execution_phase_covered_actions"],
        ),
        _check(
            "curation_bundle_curator_phase_coverage_matches_sprint_and_blocked",
            phase_coverage["curator_phase_coverage_matches_sprint_and_blocked"],
            expected=phase_coverage["curator_expected_phase_covered_actions"],
            actual=phase_coverage["curator_execution_phase_covered_actions"],
        ),
        _check(
            "direct_phase_coverage_matches_curation_bundle",
            not direct_phase_coverage_mismatches,
            expected=[],
            actual=direct_phase_coverage_mismatches,
        ),
        _check(
            "jurisdiction_pack_ids_present",
            jurisdiction_pack_id_coverage["jurisdiction_pack_scope_ids_present"]
            and jurisdiction_pack_id_coverage["jurisdiction_pack_domain_lens_ids_present"],
            expected={
                "jurisdiction_scope_ids": "non-empty list",
                "domain_lens_ids": "non-empty list",
            },
            actual={
                "jurisdiction_scope_ids": safe_jurisdiction_pack_id_coverage[
                    "jurisdiction_pack_scope_ids"
                ],
                "domain_lens_ids": safe_jurisdiction_pack_id_coverage[
                    "jurisdiction_pack_domain_lens_ids"
                ],
            },
        ),
        _check(
            "jurisdiction_pack_ids_match_curation_bundle",
            not jurisdiction_pack_id_mismatches,
            expected=[],
            actual=jurisdiction_pack_id_mismatches,
        ),
        _check(
            "legal_anchor_source_channels_present",
            legal_anchor_channel_coverage["channel_ids_present"]
            and legal_anchor_channel_coverage["channel_count_present"],
            expected={
                "legal_claim_anchor_source_channel_count": "integer",
                "legal_claim_anchor_source_channel_ids": "non-empty list",
            },
            actual={
                "legal_claim_anchor_source_channel_count": legal_anchor_channel_coverage[
                    "benchmark_legal_claim_anchor_source_channel_count"
                ],
                "legal_claim_anchor_source_channel_ids": safe_legal_anchor_channel_coverage[
                    "benchmark_legal_claim_anchor_source_channel_ids"
                ],
            },
        ),
        _check(
            "legal_anchor_source_channels_match_across_artifacts",
            not legal_anchor_channel_mismatches,
            expected=[],
            actual=legal_anchor_channel_mismatches,
        ),
        _check(
            "readiness_blocker_counts_present",
            readiness_blocker_coverage["readiness_blocker_counts_present"],
            expected={
                "worker_prompt_count": "integer",
                "worker_prompts_blocked_for_comparable_run": "integer",
                "worker_verified_local_law_rows": "integer",
                "worker_source_object_tasks": "integer",
                "worker_scope_refinement_tasks": "integer",
                "regulatory_pattern_count": "integer",
                "regulatory_candidate_count": "integer",
                "regulatory_seed_scaffold_operations": "integer",
            },
            actual={
                "worker_prompt_count": readiness_blocker_coverage[
                    "readiness_worker_prompt_count"
                ],
                "worker_prompts_blocked_for_comparable_run": readiness_blocker_coverage[
                    "readiness_worker_prompts_blocked_for_comparable_run"
                ],
                "worker_verified_local_law_rows": readiness_blocker_coverage[
                    "readiness_worker_verified_local_law_rows"
                ],
                "worker_source_object_tasks": readiness_blocker_coverage[
                    "readiness_worker_source_object_tasks"
                ],
                "worker_scope_refinement_tasks": readiness_blocker_coverage[
                    "readiness_worker_scope_refinement_tasks"
                ],
                "regulatory_pattern_count": readiness_blocker_coverage[
                    "readiness_regulatory_pattern_count"
                ],
                "regulatory_candidate_count": readiness_blocker_coverage[
                    "readiness_regulatory_candidate_count"
                ],
                "regulatory_seed_scaffold_operations": readiness_blocker_coverage[
                    "readiness_regulatory_seed_scaffold_operations"
                ],
            },
        ),
        _check(
            "readiness_blocker_counts_match_across_artifacts",
            not readiness_blocker_mismatches,
            expected=[],
            actual=readiness_blocker_mismatches,
        ),
    ]
    if validate_lower_components:
        checks.extend([
            _check(
                "expected_lower_level_artifact_count_present",
                len(lower_rows) == len(lower_specs),
                expected=len(lower_specs),
                actual=len(lower_rows),
            ),
            _check(
                "lower_level_artifact_ids_match_builder_paths",
                lower_actual_ids == lower_expected_ids,
                expected=lower_expected_ids,
                actual=lower_actual_ids,
            ),
            _check("all_lower_level_artifacts_readable", not lower_missing_artifacts, expected=[], actual=lower_missing_artifacts),
            _check(
                "all_lower_level_markdown_reports_readable",
                not lower_missing_markdown,
                expected=[],
                actual=lower_missing_markdown,
            ),
            _check(
                "all_lower_level_markdown_reports_safe",
                not lower_unsafe_markdown,
                expected=[],
                actual=lower_unsafe_markdown,
            ),
            _check(
                "all_lower_level_artifact_validations_pass",
                not lower_failed_artifacts,
                expected=[],
                actual=lower_failed_artifacts,
            ),
            _check(
                "all_lower_level_comparable_flags_blocked",
                not lower_scoring_ready_artifacts,
                expected=[],
                actual=lower_scoring_ready_artifacts,
            ),
        ])
    failed_checks = _failed_ids(checks)
    compact_report["checks"] = checks
    compact_report["summary"]["suite_check_count"] = len(checks)
    compact_report["summary"]["suite_failed_check_count"] = len(failed_checks)
    compact_report["summary"]["suite_failed_check_ids"] = failed_checks
    compact_report["summary"]["valid"] = compact_report["summary"]["valid"] and not failed_checks
    return compact_report


def _md_cell(value: Any) -> str:
    text = json.dumps(value, sort_keys=True) if isinstance(value, (dict, list)) else str(value)
    return text.replace("|", "\\|").replace("\n", " ").strip()


def render_markdown(report: dict[str, Any]) -> str:
    summary = report["summary"]
    lines = [
        "# Global Protections Saved Artifacts Validation",
        "",
        "This read-only suite validates every saved global-protections JSON artifact after component regeneration.",
        "",
        "## Summary",
        "",
        "| Metric | Value |",
        "|---|---:|",
        f"| Valid | {str(bool(summary['valid'])).lower()} |",
        f"| Artifacts | {summary['artifact_count']} |",
        f"| Valid artifacts | {summary['valid_artifact_count']} |",
        f"| Failed artifacts | {summary['failed_artifact_count']} |",
        f"| Missing/unreadable artifacts | {summary['missing_or_unreadable_artifact_count']} |",
        f"| Missing/unreadable Markdown | {summary['missing_or_unreadable_markdown_count']} |",
        f"| Unsafe Markdown | {summary['unsafe_markdown_count']} |",
        f"| Artifact path mismatches | {summary['artifact_path_mismatch_count']} |",
        f"| Component checks | {summary['total_check_count']} |",
        f"| Failed component checks | {summary['total_failed_check_count']} |",
        f"| Validate lower-level artifacts | {str(bool(summary['validate_lower_components'])).lower()} |",
        f"| Expected lower-level artifacts | {summary['lower_level_expected_artifact_count']} |",
        f"| Lower-level artifacts | {summary['lower_level_artifact_count']} |",
        f"| Failed lower-level artifacts | {summary['lower_level_failed_artifact_count']} |",
        f"| Lower-level component checks | {summary['lower_level_total_check_count']} |",
        f"| Failed lower-level component checks | {summary['lower_level_total_failed_check_count']} |",
        f"| Readiness worker prompts | {summary['readiness_worker_prompt_count']} |",
        (
            "| Readiness worker prompts blocked "
            f"| {summary['readiness_worker_prompts_blocked_for_comparable_run']} |"
        ),
        (
            "| Readiness verified local-law rows "
            f"| {summary['readiness_worker_verified_local_law_rows']} |"
        ),
        (
            "| Readiness source-object tasks "
            f"| {summary['readiness_worker_source_object_tasks']} |"
        ),
        (
            "| Readiness scope-refinement tasks "
            f"| {summary['readiness_worker_scope_refinement_tasks']} |"
        ),
        (
            "| Readiness regulatory patterns "
            f"| {summary['readiness_regulatory_pattern_count']} |"
        ),
        (
            "| Readiness regulatory candidate domains "
            f"| {summary['readiness_regulatory_candidate_count']} |"
        ),
        (
            "| Readiness regulatory seed scaffold operations "
            f"| {summary['readiness_regulatory_seed_scaffold_operations']} |"
        ),
        f"| Readiness blocker mismatches | {summary['readiness_blocker_mismatch_count']} |",
        f"| Curation bundle next phases | {summary['curation_bundle_next_execution_phase_count']} |",
        f"| Curation bundle next phase-covered actions | {summary['curation_bundle_next_phase_covered_actions']} |",
        f"| Curation bundle curator phases | {summary['curation_bundle_curator_execution_phase_count']} |",
        f"| Curation bundle curator phase-covered actions | {summary['curation_bundle_curator_phase_covered_actions']} |",
        f"| Direct next-actions phases | {summary['next_actions_execution_phase_count']} |",
        f"| Direct next-actions phase-covered actions | {summary['next_actions_phase_covered_actions']} |",
        f"| Direct curator-sprint phases | {summary['curator_sprint_execution_phase_count']} |",
        f"| Direct curator-sprint phase-covered actions | {summary['curator_sprint_phase_covered_actions']} |",
        f"| Phase coverage mismatches | {summary['phase_coverage_mismatch_count']} |",
        (
            "| Direct jurisdiction-pack scopes "
            f"| {summary['jurisdiction_pack_scope_count']} |"
        ),
        (
            "| Curation bundle jurisdiction-pack scopes "
            f"| {summary['curation_jurisdiction_pack_scope_count']} |"
        ),
        (
            "| Direct jurisdiction-pack domain lenses "
            f"| {summary['jurisdiction_pack_domain_lens_count']} |"
        ),
        (
            "| Curation bundle jurisdiction-pack domain lenses "
            f"| {summary['curation_jurisdiction_pack_domain_lens_count']} |"
        ),
        f"| Jurisdiction-pack ID mismatches | {summary['jurisdiction_pack_id_mismatch_count']} |",
        (
            "| Legal-anchor source channels "
            f"| {summary['benchmark_legal_claim_anchor_source_channel_count']} |"
        ),
        (
            "| Direct source-channel matrix legal-anchor source channels "
            f"| {summary['source_channel_matrix_legal_claim_anchor_source_channel_count']} |"
        ),
        (
            "| Direct source-channel review legal-anchor source channels "
            f"| {summary['source_channel_review_legal_claim_anchor_source_channel_count']} |"
        ),
        (
            "| Curation bundle source-channel matrix legal-anchor source channels "
            f"| {summary['curation_source_channel_matrix_legal_claim_anchor_source_channel_count']} |"
        ),
        (
            "| Curation bundle source-channel review legal-anchor source channels "
            f"| {summary['curation_source_channel_review_legal_claim_anchor_source_channel_count']} |"
        ),
        (
            "| Direct readiness legal-anchor source channels "
            f"| {summary['readiness_legal_claim_anchor_source_channel_count']} |"
        ),
        (
            "| Curation bundle readiness legal-anchor source channels "
            f"| {summary['curation_readiness_legal_claim_anchor_source_channel_count']} |"
        ),
        (
            "| Direct next-actions legal-anchor source channels "
            f"| {summary['next_actions_legal_claim_anchor_source_channel_count']} |"
        ),
        (
            "| Curation bundle next-actions legal-anchor source channels "
            f"| {summary['curation_next_actions_legal_claim_anchor_source_channel_count']} |"
        ),
        (
            "| Direct curator-sprint legal-anchor source channels "
            f"| {summary['curator_sprint_legal_claim_anchor_source_channel_count']} |"
        ),
        (
            "| Curation bundle curator-sprint legal-anchor source channels "
            f"| {summary['curation_curator_sprint_legal_claim_anchor_source_channel_count']} |"
        ),
        f"| Legal-anchor channel mismatches | {summary['legal_anchor_channel_mismatch_count']} |",
        f"| Suite checks | {summary['suite_check_count']} |",
        f"| Failed suite checks | {summary['suite_failed_check_count']} |",
        f"| Ready for comparable scoring | {str(bool(summary['ready_for_comparable_scoring'])).lower()} |",
        "",
        "## Artifacts",
        "",
        "| Artifact | Valid | Failed checks | Markdown safe | Ready for comparable scoring | JSON path |",
        "|---|---:|---:|---:|---:|---|",
    ]
    for row in report["artifact_results"]:
        lines.append(
            f"| `{_md_cell(row['artifact_id'])}` "
            f"| {str(bool(row['valid'])).lower()} "
            f"| {_md_cell(row['failed_check_count'])} "
            f"| {str(bool(row.get('markdown_safe'))).lower()} "
            f"| {str(bool(row.get('ready_for_comparable_scoring'))).lower()} "
            f"| `{_md_cell(row['json_path'])}` |"
        )
    if report.get("lower_level_artifact_results"):
        lines.extend([
            "",
            "## Lower-Level Artifacts",
            "",
            "| Artifact | Valid | Failed checks | Markdown safe | Ready for comparable scoring | JSON path |",
            "|---|---:|---:|---:|---:|---|",
        ])
        for row in report["lower_level_artifact_results"]:
            lines.append(
                f"| `{_md_cell(row['artifact_id'])}` "
                f"| {str(bool(row['valid'])).lower()} "
                f"| {_md_cell(row['failed_check_count'])} "
                f"| {str(bool(row.get('markdown_safe'))).lower()} "
                f"| {str(bool(row.get('ready_for_comparable_scoring'))).lower()} "
                f"| `{_md_cell(row['json_path'])}` |"
            )
    if summary["failed_artifact_ids"]:
        lines.extend(["", "## Failed Artifacts", ""])
        for artifact_id in summary["failed_artifact_ids"]:
            row = next(row for row in report["artifact_results"] if row["artifact_id"] == artifact_id)
            lines.append(f"- `{artifact_id}`: {_md_cell(row['failed_check_ids'])}")
    if summary["lower_level_failed_artifact_ids"]:
        lines.extend(["", "## Failed Lower-Level Artifacts", ""])
        for artifact_id in summary["lower_level_failed_artifact_ids"]:
            row = next(
                row for row in report["lower_level_artifact_results"] if row["artifact_id"] == artifact_id
            )
            lines.append(f"- `{artifact_id}`: {_md_cell(row['failed_check_ids'])}")
    if summary["unsafe_markdown_ids"]:
        lines.extend(["", "## Unsafe Markdown", ""])
        for artifact_id in summary["unsafe_markdown_ids"]:
            row = next(row for row in report["artifact_results"] if row["artifact_id"] == artifact_id)
            lines.append(f"- `{artifact_id}`: {_md_cell(row['markdown_issue_ids'])}")
    if summary["artifact_path_mismatches"]:
        lines.extend(["", "## Artifact Path Mismatches", ""])
        for finding in summary["artifact_path_mismatches"]:
            lines.append(f"- {_md_cell(finding)}")
    if summary["phase_coverage_mismatches"]:
        lines.extend(["", "## Phase Coverage Mismatches", ""])
        for finding in summary["phase_coverage_mismatches"]:
            lines.append(f"- {_md_cell(finding)}")
    if summary["jurisdiction_pack_id_mismatches"]:
        lines.extend(["", "## Jurisdiction-Pack ID Mismatches", ""])
        for finding in summary["jurisdiction_pack_id_mismatches"]:
            lines.append(f"- {_md_cell(finding)}")
    if summary["legal_anchor_channel_mismatches"]:
        lines.extend(["", "## Legal-Anchor Channel Mismatches", ""])
        for finding in summary["legal_anchor_channel_mismatches"]:
            lines.append(f"- {_md_cell(finding)}")
    if summary["readiness_blocker_mismatches"]:
        lines.extend(["", "## Readiness Blocker Mismatches", ""])
        for finding in summary["readiness_blocker_mismatches"]:
            lines.append(f"- {_md_cell(finding)}")
    if summary["suite_failed_check_ids"]:
        lines.extend(["", "## Failed Suite Check IDs", ""])
        for check_id in summary["suite_failed_check_ids"]:
            lines.append(f"- `{check_id}`")
    lines.append("")
    return "\n".join(lines)


def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--domain", default=DEFAULT_DOMAIN)
    ap.add_argument("--project-config", type=pathlib.Path, default=project_plan_builder.CONFIG)
    ap.add_argument("--registry", type=pathlib.Path, default=project_plan_builder.REGISTRY)
    ap.add_argument("--regulatory-catalog", type=pathlib.Path, default=project_plan_builder.REGULATORY_CATALOG)
    ap.add_argument("--component-dir", type=pathlib.Path, default=OUT_DIR)
    ap.add_argument("--out", type=pathlib.Path, default=OUT)
    ap.add_argument("--markdown-out", type=pathlib.Path, default=MD_OUT)
    ap.add_argument(
        "--refresh-components",
        action="store_true",
        help="regenerate the global protections component artifacts before validation",
    )
    ap.add_argument(
        "--refresh-all-components",
        action="store_true",
        help="regenerate the global protections component set plus lower-level domain/regulatory artifacts",
    )
    ap.add_argument(
        "--validate-lower-components",
        action="store_true",
        help="validate lower-level domain/regulatory curation bundles when present",
    )
    ap.add_argument("--no-current-chain", action="store_true", help="skip comparisons to current deterministic builders")
    ap.add_argument("--validate", action="store_true", help="print the suite summary only; write nothing")
    ap.add_argument("--json", action="store_true", help="print the full suite report as JSON; write nothing")
    args = ap.parse_args(argv)
    if args.validate and args.json:
        ap.error("--validate and --json are mutually exclusive")

    refresh_components = args.refresh_components or args.refresh_all_components
    validate_lower_components = args.validate_lower_components or args.refresh_all_components
    if refresh_components:
        refresh_status = refresh_component_artifacts(
            domain_id=args.domain,
            project_config_path=args.project_config,
            registry_path=args.registry,
            regulatory_catalog_path=args.regulatory_catalog,
            component_dir=args.component_dir,
            refresh_all_components=args.refresh_all_components,
        )
        if refresh_status != 0:
            return refresh_status

    report = validate_saved_artifacts(
        domain_id=args.domain,
        project_config_path=args.project_config,
        registry_path=args.registry,
        regulatory_catalog_path=args.regulatory_catalog,
        component_dir=args.component_dir,
        compare_current_chain=not args.no_current_chain,
        validate_lower_components=validate_lower_components,
    )
    report["_meta"]["refresh_components"] = refresh_components
    report["_meta"]["refresh_all_components"] = args.refresh_all_components
    report["_meta"]["validate_lower_components"] = validate_lower_components
    summary = report["summary"]
    if args.validate:
        print(json.dumps(summary, indent=2, ensure_ascii=False))
        return 0 if summary["valid"] else 1
    if args.json:
        print(json.dumps(report, indent=2, ensure_ascii=False))
        return 0 if summary["valid"] else 1

    args.out.parent.mkdir(parents=True, exist_ok=True)
    args.markdown_out.parent.mkdir(parents=True, exist_ok=True)
    args.out.write_text(json.dumps(report, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
    args.markdown_out.write_text(render_markdown(report), encoding="utf-8")
    print(
        "[global-protections-saved-artifacts-validation] "
        f"valid={str(bool(summary['valid'])).lower()}; "
        f"failed_artifacts={summary['failed_artifact_count']}/{summary['artifact_count']}; "
        f"failed_checks={summary['total_failed_check_count']}/{summary['total_check_count']}; "
        f"lower_level_artifacts={summary['lower_level_failed_artifact_count']}/"
        f"{summary['lower_level_artifact_count']}; "
        f"lower_level_checks={summary['lower_level_total_failed_check_count']}/"
        f"{summary['lower_level_total_check_count']}; "
        f"suite_checks={summary['suite_failed_check_count']}/{summary['suite_check_count']}; "
        f"phase_coverage=next:{summary['curation_bundle_next_execution_phase_count']}/"
        f"{summary['curation_bundle_next_phase_covered_actions']},"
        f"curator:{summary['curation_bundle_curator_execution_phase_count']}/"
        f"{summary['curation_bundle_curator_phase_covered_actions']}; "
        f"phase_mismatches={summary['phase_coverage_mismatch_count']}; "
        f"readiness_blocker_mismatches={summary['readiness_blocker_mismatch_count']}; "
        f"legal_anchor_mismatches={summary['legal_anchor_channel_mismatch_count']}; "
        f"ready_for_comparable_scoring={str(bool(summary['ready_for_comparable_scoring'])).lower()} -> {args.component_dir}"
    )
    return 0 if summary["valid"] else 1


if __name__ == "__main__":
    raise SystemExit(main())
