#!/usr/bin/env python3
"""Build a propose-only pilot jurisdiction-pack matrix.

This matrix is the next concrete planning layer for the Global Protections
Regulatory Benchmark: it combines a small set of jurisdiction scopes with a
small set of regulatory domain lenses, then emits source-object slots that
curators must fill later. It does not fetch sources, verify law, create
prompts, promote manifests, train models, publish claims, or authorize
comparable scoring.

Offline + deterministic. No model, no network, no credits.
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

CONFIG = (
    _ROOT
    / "configs"
    / "duecare"
    / "benchmarks"
    / "sister_projects"
    / "global_protections_jurisdiction_packs.json"
)
OUT_DIR = _ROOT / "reports" / "benchmark"
OUT = OUT_DIR / "global_protections_jurisdiction_pack_matrix.json"
MD_OUT = OUT_DIR / "global_protections_jurisdiction_pack_matrix.md"

REQUIRED_FIELDS = frozenset({
    "project_id",
    "status",
    "pilot_policy",
    "domain_lenses",
    "pilot_jurisdiction_scopes",
})
ALLOWED_FIELDS = REQUIRED_FIELDS | frozenset({"_meta", "queued_jurisdiction_scopes"})
REQUIRED_LENS_FIELDS = frozenset({"id", "label", "source_object_slots", "review_gates"})
REQUIRED_SCOPE_FIELDS = frozenset({
    "id",
    "label",
    "iso3166_alpha2",
    "jurisdiction_family",
    "jurisdiction_role",
    "language_review_required",
    "scope_resolution_required",
})
REQUIRED_QUEUED_SCOPE_FIELDS = REQUIRED_SCOPE_FIELDS | frozenset({"queued_reason"})
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
    "https://",
    "www.",
]
_SLUG = re.compile(r"^[a-z][a-z0-9_]{2,80}$")
_ISO2 = re.compile(r"^[A-Z]{2}$")


def _display_path(path: pathlib.Path) -> str:
    try:
        return path.relative_to(_ROOT).as_posix()
    except ValueError:
        return path.as_posix()


def _load_json(path: pathlib.Path) -> dict[str, Any] | None:
    try:
        loaded = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError):
        return None
    return loaded if isinstance(loaded, dict) else None


def _safe_slug(value: Any) -> str:
    if not isinstance(value, str):
        return "unknown"
    text = value.strip()
    return text if _SLUG.fullmatch(text) else "unknown"


def _safe_iso2(value: Any) -> str:
    if not isinstance(value, str):
        return "XX"
    text = value.strip()
    return text if _ISO2.fullmatch(text) else "XX"


def _safe_text(value: Any, *, max_len: int = 420) -> str:
    return project_plan_builder._safe_text(value, max_len=max_len)


def _safe_list(value: Any, *, slug: bool = False, max_len: int = 420) -> list[str]:
    if not isinstance(value, list):
        return []
    out: list[str] = []
    for item in value:
        safe = _safe_slug(item) if slug else _safe_text(item, max_len=max_len)
        if safe != "unknown":
            out.append(safe)
    return out


def _check(check_id: str, ok: bool, *, expected: Any, actual: Any) -> dict[str, Any]:
    return {
        "id": check_id,
        "ok": bool(ok),
        "expected": expected,
        "actual": actual,
    }


def _project_doc_from_config(
    *,
    project_config_path: pathlib.Path,
    registry_path: pathlib.Path,
    regulatory_catalog_path: pathlib.Path,
) -> dict[str, Any]:
    config = _load_json(project_config_path)
    if config is None:
        raise ValueError(f"unreadable global protections project config: {project_config_path}")
    registry = _load_json(registry_path)
    catalog = _load_json(regulatory_catalog_path)
    return project_plan_builder.build_project_plan(
        config,
        config_path=project_config_path,
        registry=registry,
        regulatory_catalog=catalog,
        registry_path=registry_path,
        regulatory_catalog_path=regulatory_catalog_path,
    )


def _config_issues(config: Any) -> Counter[str]:
    issues: Counter[str] = Counter()
    if not isinstance(config, dict):
        issues["config_not_object"] += 1
        return issues
    missing = REQUIRED_FIELDS - set(config)
    if missing:
        issues["required_fields_missing"] += 1
    extra = set(config) - ALLOWED_FIELDS
    if extra:
        issues["unexpected_fields"] += 1
    if _safe_slug(config.get("project_id")) == "unknown":
        issues["project_id_not_safe_slug"] += 1
    if config.get("status") != "propose_only":
        issues["status_not_propose_only"] += 1
    if _safe_text(config.get("pilot_policy"), max_len=700) == "unknown":
        issues["pilot_policy_unsafe"] += 1
    lens_ids: set[str] = set()
    lenses = config.get("domain_lenses")
    if not isinstance(lenses, list) or not lenses:
        issues["domain_lenses_empty_or_not_list"] += 1
    else:
        for lens in lenses:
            if not isinstance(lens, dict):
                issues["domain_lens_not_object"] += 1
                continue
            if REQUIRED_LENS_FIELDS - set(lens):
                issues["domain_lens_required_fields_missing"] += 1
            if set(lens) - REQUIRED_LENS_FIELDS:
                issues["domain_lens_unexpected_fields"] += 1
            lens_id = _safe_slug(lens.get("id"))
            if lens_id == "unknown":
                issues["domain_lens_id_not_safe_slug"] += 1
            elif lens_id in lens_ids:
                issues["domain_lens_id_duplicate"] += 1
            else:
                lens_ids.add(lens_id)
            if _safe_text(lens.get("label")) == "unknown":
                issues["domain_lens_label_unsafe"] += 1
            if len(_safe_list(lens.get("source_object_slots"), slug=True)) < 4:
                issues["domain_lens_source_object_slots_missing"] += 1
            if len(_safe_list(lens.get("review_gates"), slug=True)) < 5:
                issues["domain_lens_review_gates_missing"] += 1
    scope_ids: set[str] = set()
    scopes = config.get("pilot_jurisdiction_scopes")
    if not isinstance(scopes, list) or not scopes:
        issues["pilot_jurisdiction_scopes_empty_or_not_list"] += 1
    else:
        for scope in scopes:
            if not isinstance(scope, dict):
                issues["pilot_scope_not_object"] += 1
                continue
            if REQUIRED_SCOPE_FIELDS - set(scope):
                issues["pilot_scope_required_fields_missing"] += 1
            if set(scope) - REQUIRED_SCOPE_FIELDS:
                issues["pilot_scope_unexpected_fields"] += 1
            scope_id = _safe_slug(scope.get("id"))
            if scope_id == "unknown":
                issues["pilot_scope_id_not_safe_slug"] += 1
            elif scope_id in scope_ids:
                issues["pilot_scope_id_duplicate"] += 1
            else:
                scope_ids.add(scope_id)
            if _safe_text(scope.get("label")) == "unknown":
                issues["pilot_scope_label_unsafe"] += 1
            if _safe_iso2(scope.get("iso3166_alpha2")) == "XX":
                issues["pilot_scope_iso2_invalid"] += 1
            for field in ("jurisdiction_family", "jurisdiction_role"):
                if _safe_text(scope.get(field)) == "unknown":
                    issues[f"pilot_scope_{field}_unsafe"] += 1
            if not isinstance(scope.get("language_review_required"), bool):
                issues["pilot_scope_language_review_required_not_bool"] += 1
            if not isinstance(scope.get("scope_resolution_required"), bool):
                issues["pilot_scope_resolution_required_not_bool"] += 1
    queued_scopes = config.get("queued_jurisdiction_scopes", [])
    if queued_scopes is not None:
        if not isinstance(queued_scopes, list):
            issues["queued_jurisdiction_scopes_not_list"] += 1
        else:
            queued_scope_ids: set[str] = set()
            for scope in queued_scopes:
                if not isinstance(scope, dict):
                    issues["queued_scope_not_object"] += 1
                    continue
                if REQUIRED_QUEUED_SCOPE_FIELDS - set(scope):
                    issues["queued_scope_required_fields_missing"] += 1
                if set(scope) - REQUIRED_QUEUED_SCOPE_FIELDS:
                    issues["queued_scope_unexpected_fields"] += 1
                scope_id = _safe_slug(scope.get("id"))
                if scope_id == "unknown":
                    issues["queued_scope_id_not_safe_slug"] += 1
                elif scope_id in queued_scope_ids or scope_id in scope_ids:
                    issues["queued_scope_id_duplicate"] += 1
                else:
                    queued_scope_ids.add(scope_id)
                if _safe_text(scope.get("label")) == "unknown":
                    issues["queued_scope_label_unsafe"] += 1
                if _safe_iso2(scope.get("iso3166_alpha2")) == "XX":
                    issues["queued_scope_iso2_invalid"] += 1
                for field in ("jurisdiction_family", "jurisdiction_role", "queued_reason"):
                    if _safe_text(scope.get(field), max_len=700) == "unknown":
                        issues[f"queued_scope_{field}_unsafe"] += 1
                if not isinstance(scope.get("language_review_required"), bool):
                    issues["queued_scope_language_review_required_not_bool"] += 1
                if not isinstance(scope.get("scope_resolution_required"), bool):
                    issues["queued_scope_resolution_required_not_bool"] += 1
    privacy_scan = project_plan_builder._scan_privacy(config)
    if privacy_scan.get("ok") is not True:
        issues["privacy_scan_not_ok"] += 1
    encoded = json.dumps(config, ensure_ascii=False)
    if any(term in encoded for term in DISALLOWED_TERMS):
        issues["disallowed_text_present"] += 1
    return issues


def _source_slot(slot_id: str, pack_id: str, index: int) -> dict[str, Any]:
    return {
        "slot_id": f"{pack_id}-slot-{index:02d}-{slot_id}",
        "source_object_slot": slot_id,
        "status": "not_started",
        "requires_dated_source_object": True,
        "requires_archive_status": True,
        "requires_source_path_review": True,
        "requires_privacy_review": True,
        "requires_expert_review": True,
        "accepted_source_object_id": "",
        "source_coverage_status": "source_gap",
    }


def _pack_cell(scope: dict[str, Any], lens: dict[str, Any], index: int) -> dict[str, Any]:
    pack_id = f"GPJPM-{index:03d}"
    slots = [
        _source_slot(slot_id, pack_id, slot_index)
        for slot_index, slot_id in enumerate(lens["source_object_slots"], start=1)
    ]
    return {
        "pack_id": pack_id,
        "jurisdiction_scope_id": scope["id"],
        "jurisdiction_scope_label": scope["label"],
        "iso3166_alpha2": scope["iso3166_alpha2"],
        "jurisdiction_family": scope["jurisdiction_family"],
        "jurisdiction_role": scope["jurisdiction_role"],
        "domain_lens_id": lens["id"],
        "domain_lens_label": lens["label"],
        "language_review_required": scope["language_review_required"],
        "scope_resolution_required": scope["scope_resolution_required"],
        "source_object_slots": slots,
        "required_review_gates": list(lens["review_gates"]),
        "ready_for_prompt_generation": False,
        "ready_for_training_use": False,
        "ready_for_public_claims": False,
        "ready_for_worker_facing_use": False,
        "ready_for_comparable_scoring": False,
        "next_step": (
            "curate dated public source objects for every slot, record archive status, "
            "complete privacy/source-path/expert review, and keep prompts blocked"
        ),
    }


def build_jurisdiction_pack_matrix(
    *,
    config: dict[str, Any] | None = None,
    project_doc: dict[str, Any] | None = None,
    config_path: pathlib.Path = CONFIG,
    project_config_path: pathlib.Path = project_plan_builder.CONFIG,
    registry_path: pathlib.Path = project_plan_builder.REGISTRY,
    regulatory_catalog_path: pathlib.Path = project_plan_builder.REGULATORY_CATALOG,
) -> dict[str, Any]:
    """Return a source-gated pilot jurisdiction-pack matrix."""
    config = config or _load_json(config_path)
    if config is None:
        raise ValueError(f"unreadable jurisdiction-pack config: {config_path}")
    project_doc = project_doc or _project_doc_from_config(
        project_config_path=project_config_path,
        registry_path=registry_path,
        regulatory_catalog_path=regulatory_catalog_path,
    )
    issue_counts = _config_issues(config)
    project_id = _safe_slug(config.get("project_id"))
    project_scope = project_doc.get("scope") if isinstance(project_doc, dict) else {}
    project_families = set(project_scope.get("target_jurisdiction_families") or [])
    project_patterns = set(project_scope.get("candidate_pattern_ids") or [])
    lenses = [
        {
            "id": _safe_slug(raw.get("id")),
            "label": _safe_text(raw.get("label")),
            "source_object_slots": _safe_list(raw.get("source_object_slots"), slug=True),
            "review_gates": _safe_list(raw.get("review_gates"), slug=True),
        }
        for raw in config.get("domain_lenses", [])
        if isinstance(raw, dict)
    ]
    scopes = [
        {
            "id": _safe_slug(raw.get("id")),
            "label": _safe_text(raw.get("label")),
            "iso3166_alpha2": _safe_iso2(raw.get("iso3166_alpha2")),
            "jurisdiction_family": _safe_text(raw.get("jurisdiction_family")),
            "jurisdiction_role": _safe_text(raw.get("jurisdiction_role")),
            "language_review_required": bool(raw.get("language_review_required")),
            "scope_resolution_required": bool(raw.get("scope_resolution_required")),
        }
        for raw in config.get("pilot_jurisdiction_scopes", [])
        if isinstance(raw, dict)
    ]
    queued_scopes = [
        {
            "id": _safe_slug(raw.get("id")),
            "label": _safe_text(raw.get("label")),
            "iso3166_alpha2": _safe_iso2(raw.get("iso3166_alpha2")),
            "jurisdiction_family": _safe_text(raw.get("jurisdiction_family")),
            "jurisdiction_role": _safe_text(raw.get("jurisdiction_role")),
            "language_review_required": bool(raw.get("language_review_required")),
            "scope_resolution_required": bool(raw.get("scope_resolution_required")),
            "queued_reason": _safe_text(raw.get("queued_reason"), max_len=700),
            "ready_for_pack_cell_generation": False,
            "ready_for_prompt_generation": False,
            "ready_for_comparable_scoring": False,
        }
        for raw in config.get("queued_jurisdiction_scopes", [])
        if isinstance(raw, dict)
    ]
    unknown_lenses = sorted({lens["id"] for lens in lenses} - project_patterns)
    unknown_families = sorted({scope["jurisdiction_family"] for scope in scopes} - project_families)
    jurisdiction_scope_ids = [scope["id"] for scope in scopes]
    domain_lens_ids = [lens["id"] for lens in lenses]
    if unknown_lenses:
        issue_counts["domain_lens_not_in_project_candidate_patterns"] += len(unknown_lenses)
    if unknown_families:
        issue_counts["pilot_scope_family_not_in_project"] += len(unknown_families)

    pack_cells = [
        _pack_cell(scope, lens, index)
        for index, (scope, lens) in enumerate(
            ((scope, lens) for scope in scopes for lens in lenses),
            start=1,
        )
    ]
    source_slot_count = sum(len(cell["source_object_slots"]) for cell in pack_cells)
    not_started_slots = sum(
        1
        for cell in pack_cells
        for slot in cell["source_object_slots"]
        if slot["status"] == "not_started"
    )
    ready_flags = {
        key: any(cell[key] for cell in pack_cells)
        for key in READY_FLAG_KEYS
    }
    disallowed = [
        term
        for term in DISALLOWED_TERMS
        if term in json.dumps({"config": config, "pack_cells": pack_cells}, ensure_ascii=False)
    ]
    privacy_scan = project_plan_builder._scan_privacy({"config": config, "pack_cells": pack_cells})
    expected_cells = len(scopes) * len(lenses)
    checks = [
        _check("privacy_scan_ok", privacy_scan.get("ok") is True, expected=True, actual=privacy_scan.get("counts")),
        _check("status_is_propose_only", config.get("status") == "propose_only", expected="propose_only", actual=config.get("status")),
        _check("project_id_matches_charter", project_id == project_doc["project"]["project_id"], expected=project_doc["project"]["project_id"], actual=project_id),
        _check("domain_lenses_known_to_project", not unknown_lenses, expected=[], actual=unknown_lenses),
        _check("jurisdiction_families_known_to_project", not unknown_families, expected=[], actual=unknown_families),
        _check("pack_cells_match_cross_product", len(pack_cells) == expected_cells, expected=expected_cells, actual=len(pack_cells)),
        _check("source_object_slots_present", source_slot_count >= expected_cells * 4, expected=f">={expected_cells * 4}", actual=source_slot_count),
        _check("source_object_slots_all_not_started", not_started_slots == source_slot_count, expected=source_slot_count, actual=not_started_slots),
        _check("every_slot_requires_dated_source_object", all(
            slot["requires_dated_source_object"]
            and slot["requires_archive_status"]
            and slot["requires_source_path_review"]
            and slot["requires_privacy_review"]
            and slot["requires_expert_review"]
            for cell in pack_cells
            for slot in cell["source_object_slots"]
        ), expected=True, actual=True),
        _check("all_public_and_scoring_flags_blocked", not any(ready_flags.values()), expected=False, actual=ready_flags),
        _check("pack_matrix_contains_no_disallowed_text", not disallowed, expected=[], actual=disallowed),
        _check("config_shape_ok", not issue_counts, expected={}, actual=dict(issue_counts)),
    ]
    consistency_ok = all(check["ok"] for check in checks)
    return {
        "_meta": {
            "schema_version": "global_protections_jurisdiction_pack_matrix.v1",
            "source_config": _display_path(config_path),
            "project_config": _display_path(project_config_path),
            "registry_path": _display_path(registry_path),
            "regulatory_catalog_path": _display_path(regulatory_catalog_path),
            "status": (
                "pilot jurisdiction-pack planning artifact; not legal advice, not source "
                "verification, not prompt generation, not training data, and not comparable "
                "benchmark evidence"
            ),
        },
        "project": {
            "project_id": project_id,
            "status": _safe_text(config.get("status")),
            "pilot_policy": _safe_text(config.get("pilot_policy"), max_len=700),
        },
        "domain_lenses": lenses,
        "pilot_jurisdiction_scopes": scopes,
        "queued_jurisdiction_scopes": queued_scopes,
        "pack_cells": pack_cells,
        "summary": {
            "consistency_ok": consistency_ok,
            "safe_for_pack_planning": consistency_ok,
            "jurisdiction_scope_count": len(scopes),
            "jurisdiction_scope_ids": list(jurisdiction_scope_ids),
            "queued_jurisdiction_scope_count": len(queued_scopes),
            "queued_jurisdiction_scope_ids": [scope["id"] for scope in queued_scopes],
            "domain_lens_count": len(lenses),
            "domain_lens_ids": list(domain_lens_ids),
            "pack_cell_count": len(pack_cells),
            "source_object_slot_count": source_slot_count,
            "not_started_source_object_slots": not_started_slots,
            "language_review_required_cells": sum(1 for cell in pack_cells if cell["language_review_required"]),
            "scope_resolution_required_cells": sum(1 for cell in pack_cells if cell["scope_resolution_required"]),
            "ready_for_prompt_generation": ready_flags["ready_for_prompt_generation"],
            "ready_for_training_use": ready_flags["ready_for_training_use"],
            "ready_for_public_claims": ready_flags["ready_for_public_claims"],
            "ready_for_worker_facing_use": ready_flags["ready_for_worker_facing_use"],
            "ready_for_comparable_scoring": ready_flags["ready_for_comparable_scoring"],
            "policy": (
                "A pack cell is only a curation target. It cannot become prompt text, public "
                "benchmark evidence, training data, or worker-facing guidance until all source "
                "objects and review gates are complete."
            ),
        },
        "checks": checks,
    }


def _md_cell(value: Any) -> str:
    text = str(value if value is not None else "")
    return text.replace("|", "\\|").replace("\n", " ").strip()


def build_markdown_report(doc: dict[str, Any]) -> str:
    """Render a compact Markdown jurisdiction-pack matrix."""
    summary = doc["summary"]
    lines = [
        "# Global Protections Jurisdiction-Pack Matrix",
        "",
        (
            "This matrix chooses pilot jurisdiction/domain pack cells for source curation. "
            "It is not legal advice, not source verification, not prompt generation, and not "
            "comparable benchmark evidence."
        ),
        "",
        "## Summary",
        "",
        "| Metric | Value |",
        "|---|---:|",
        f"| Consistency OK | {str(bool(summary['consistency_ok'])).lower()} |",
        f"| Safe for pack planning | {str(bool(summary['safe_for_pack_planning'])).lower()} |",
        f"| Jurisdiction scopes | {summary['jurisdiction_scope_count']} |",
        f"| Jurisdiction scope IDs | `{_md_cell(', '.join(summary['jurisdiction_scope_ids']))}` |",
        f"| Queued jurisdiction scopes | {summary['queued_jurisdiction_scope_count']} |",
        f"| Queued jurisdiction scope IDs | `{_md_cell(', '.join(summary['queued_jurisdiction_scope_ids']))}` |",
        f"| Domain lenses | {summary['domain_lens_count']} |",
        f"| Domain lens IDs | `{_md_cell(', '.join(summary['domain_lens_ids']))}` |",
        f"| Pack cells | {summary['pack_cell_count']} |",
        f"| Source-object slots | {summary['source_object_slot_count']} |",
        f"| Not-started source-object slots | {summary['not_started_source_object_slots']} |",
        f"| Language-review cells | {summary['language_review_required_cells']} |",
        f"| Scope-resolution cells | {summary['scope_resolution_required_cells']} |",
        f"| Ready for prompt generation | {str(bool(summary['ready_for_prompt_generation'])).lower()} |",
        f"| Ready for comparable scoring | {str(bool(summary['ready_for_comparable_scoring'])).lower()} |",
        "",
        "## Pack Cells",
        "",
        "| Pack | Jurisdiction scope | ISO | Family | Domain lens | Source-object slots | Scope review |",
        "|---|---|---|---|---|---:|---:|",
    ]
    for cell in doc["pack_cells"]:
        lines.append(
            f"| `{_md_cell(cell['pack_id'])}` "
            f"| `{_md_cell(cell['jurisdiction_scope_id'])}` "
            f"| {_md_cell(cell['iso3166_alpha2'])} "
            f"| {_md_cell(cell['jurisdiction_family'])} "
            f"| `{_md_cell(cell['domain_lens_id'])}` "
            f"| {len(cell['source_object_slots'])} "
            f"| {str(bool(cell['scope_resolution_required'])).lower()} |"
        )
    lines.extend([
        "",
        "## Checks",
        "",
        "| Check | OK | Expected | Actual |",
        "|---|---:|---|---|",
    ])
    for check in doc["checks"]:
        actual = json.dumps(check["actual"], sort_keys=True) if isinstance(check["actual"], (dict, list)) else check["actual"]
        expected = json.dumps(check["expected"], sort_keys=True) if isinstance(check["expected"], (dict, list)) else check["expected"]
        lines.append(
            f"| {_md_cell(check['id'])} "
            f"| {str(bool(check['ok'])).lower()} "
            f"| {_md_cell(expected)} "
            f"| {_md_cell(actual)} |"
        )
    lines.extend(["", "## Non-Scoring Rule", "", summary["policy"], ""])
    return "\n".join(lines)


def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--config", type=pathlib.Path, default=CONFIG)
    ap.add_argument("--project-config", type=pathlib.Path, default=project_plan_builder.CONFIG)
    ap.add_argument("--registry", type=pathlib.Path, default=project_plan_builder.REGISTRY)
    ap.add_argument("--regulatory-catalog", type=pathlib.Path, default=project_plan_builder.REGULATORY_CATALOG)
    ap.add_argument("--out", type=pathlib.Path, default=OUT)
    ap.add_argument("--md-out", type=pathlib.Path, default=MD_OUT)
    ap.add_argument("--no-md", action="store_true", help="write only JSON, not the Markdown matrix report")
    ap.add_argument("--validate", action="store_true", help="print the summary only; write nothing")
    args = ap.parse_args(argv)

    doc = build_jurisdiction_pack_matrix(
        config_path=args.config,
        project_config_path=args.project_config,
        registry_path=args.registry,
        regulatory_catalog_path=args.regulatory_catalog,
    )
    summary = doc["summary"]
    if args.validate:
        print(json.dumps({"summary": summary}, indent=2, ensure_ascii=False))
        return 0 if summary["consistency_ok"] else 1
    if not summary["consistency_ok"]:
        print(json.dumps({"summary": summary, "checks": doc["checks"]}, indent=2, ensure_ascii=False))
        print("[global-protections-jurisdiction-pack-matrix] matrix is inconsistent; refusing to write")
        return 1

    args.out.parent.mkdir(parents=True, exist_ok=True)
    args.out.write_text(json.dumps(doc, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
    md_path = None
    if not args.no_md:
        md_path = args.md_out
        md_path.parent.mkdir(parents=True, exist_ok=True)
        md_path.write_text(build_markdown_report(doc) + "\n", encoding="utf-8")
    print(
        "[global-protections-jurisdiction-pack-matrix] "
        f"consistency_ok={str(bool(summary['consistency_ok'])).lower()}; "
        f"{summary['pack_cell_count']} pack cells; "
        f"{summary['source_object_slot_count']} source-object slots; "
        f"ready_for_comparable_scoring={str(bool(summary['ready_for_comparable_scoring'])).lower()} -> {args.out}"
        + (f"; report {md_path}" if md_path else "")
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
