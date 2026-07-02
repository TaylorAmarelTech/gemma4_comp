#!/usr/bin/env python3
"""Validate a saved global-protections jurisdiction-pack matrix.

The jurisdiction-pack matrix is only a source-curation planning surface. This
validator keeps a saved matrix source-gated and privacy-safe: the jurisdiction
and domain cross-product must be intact, every source-object slot must remain
blank and not-started, prompt/scoring readiness must stay blocked, and the
saved matrix can be compared to the current deterministic chain.

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

import build_global_protections_jurisdiction_pack_matrix as matrix_builder  # noqa: E402
import build_global_protections_project_plan as project_plan_builder  # noqa: E402

DEFAULT_MATRIX = matrix_builder.OUT
OUT = matrix_builder.OUT_DIR / "global_protections_jurisdiction_pack_matrix_validation.json"
MD_OUT = matrix_builder.OUT_DIR / "global_protections_jurisdiction_pack_matrix_validation.md"

REQUIRED_TOP_LEVEL = frozenset({
    "_meta",
    "project",
    "domain_lenses",
    "pilot_jurisdiction_scopes",
    "queued_jurisdiction_scopes",
    "pack_cells",
    "summary",
    "checks",
})
ALLOWED_TOP_LEVEL = REQUIRED_TOP_LEVEL
REQUIRED_CHECK_IDS = frozenset({
    "privacy_scan_ok",
    "status_is_propose_only",
    "project_id_matches_charter",
    "domain_lenses_known_to_project",
    "jurisdiction_families_known_to_project",
    "pack_cells_match_cross_product",
    "source_object_slots_present",
    "source_object_slots_all_not_started",
    "every_slot_requires_dated_source_object",
    "all_public_and_scoring_flags_blocked",
    "pack_matrix_contains_no_disallowed_text",
    "config_shape_ok",
})
REQUIRED_PACK_CELL_KEYS = frozenset({
    "pack_id",
    "jurisdiction_scope_id",
    "jurisdiction_scope_label",
    "iso3166_alpha2",
    "jurisdiction_family",
    "jurisdiction_role",
    "domain_lens_id",
    "domain_lens_label",
    "language_review_required",
    "scope_resolution_required",
    "source_object_slots",
    "required_review_gates",
    "ready_for_prompt_generation",
    "ready_for_training_use",
    "ready_for_public_claims",
    "ready_for_worker_facing_use",
    "ready_for_comparable_scoring",
    "next_step",
})
REQUIRED_SLOT_KEYS = frozenset({
    "slot_id",
    "source_object_slot",
    "status",
    "requires_dated_source_object",
    "requires_archive_status",
    "requires_source_path_review",
    "requires_privacy_review",
    "requires_expert_review",
    "accepted_source_object_id",
    "source_coverage_status",
})
READY_FLAG_KEYS = matrix_builder.READY_FLAG_KEYS
DISALLOWED_TERMS = matrix_builder.DISALLOWED_TERMS
_PACK_ID = re.compile(r"^GPJPM-\d{3}$")
_SLOT_ID = re.compile(r"^GPJPM-\d{3}-slot-\d{2}-[a-z][a-z0-9_]{2,80}$")


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


def _summary_counts_mismatches(doc: dict[str, Any]) -> list[dict[str, Any]]:
    summary = doc.get("summary") if isinstance(doc.get("summary"), dict) else {}
    scopes = doc.get("pilot_jurisdiction_scopes") if isinstance(doc.get("pilot_jurisdiction_scopes"), list) else []
    queued_scopes = (
        doc.get("queued_jurisdiction_scopes")
        if isinstance(doc.get("queued_jurisdiction_scopes"), list)
        else []
    )
    lenses = doc.get("domain_lenses") if isinstance(doc.get("domain_lenses"), list) else []
    cells = doc.get("pack_cells") if isinstance(doc.get("pack_cells"), list) else []
    slots = [
        slot
        for cell in cells
        if isinstance(cell, dict) and isinstance(cell.get("source_object_slots"), list)
        for slot in cell["source_object_slots"]
        if isinstance(slot, dict)
    ]
    pairs = [
        ("jurisdiction_scope_count", len(scopes)),
        (
            "jurisdiction_scope_ids",
            [scope.get("id") for scope in scopes if isinstance(scope, dict)],
        ),
        ("queued_jurisdiction_scope_count", len(queued_scopes)),
        (
            "queued_jurisdiction_scope_ids",
            [scope.get("id") for scope in queued_scopes if isinstance(scope, dict)],
        ),
        ("domain_lens_count", len(lenses)),
        (
            "domain_lens_ids",
            [lens.get("id") for lens in lenses if isinstance(lens, dict)],
        ),
        ("pack_cell_count", len(cells)),
        ("source_object_slot_count", len(slots)),
        (
            "not_started_source_object_slots",
            sum(1 for slot in slots if slot.get("status") == "not_started"),
        ),
        (
            "language_review_required_cells",
            sum(1 for cell in cells if isinstance(cell, dict) and cell.get("language_review_required") is True),
        ),
        (
            "scope_resolution_required_cells",
            sum(1 for cell in cells if isinstance(cell, dict) and cell.get("scope_resolution_required") is True),
        ),
    ]
    return [
        {"summary_key": key, "expected": expected, "actual": summary.get(key)}
        for key, expected in pairs
        if summary.get(key) != expected
    ]


def _pack_cell_shape_drift(doc: dict[str, Any]) -> list[dict[str, Any]]:
    findings: list[dict[str, Any]] = []
    cells = doc.get("pack_cells") if isinstance(doc.get("pack_cells"), list) else []
    expected_pack_ids = [f"GPJPM-{idx:03d}" for idx in range(1, len(cells) + 1)]
    actual_pack_ids: list[Any] = []
    for idx, cell in enumerate(cells):
        if not isinstance(cell, dict):
            findings.append({"cell": idx, "rule": "pack_cell_object", "actual": type(cell).__name__})
            actual_pack_ids.append(None)
            continue
        actual_pack_ids.append(cell.get("pack_id"))
        missing = sorted(REQUIRED_PACK_CELL_KEYS - set(cell))
        extra = sorted(set(cell) - REQUIRED_PACK_CELL_KEYS)
        if missing or extra:
            findings.append({
                "cell": cell.get("pack_id", idx),
                "missing": missing,
                "extra": extra,
            })
        if not isinstance(cell.get("pack_id"), str) or not _PACK_ID.fullmatch(cell["pack_id"]):
            findings.append({
                "cell": cell.get("pack_id", idx),
                "rule": "pack_id_format",
                "expected": "GPJPM-000",
                "actual": cell.get("pack_id"),
            })
        if not isinstance(cell.get("source_object_slots"), list) or not cell.get("source_object_slots"):
            findings.append({
                "cell": cell.get("pack_id", idx),
                "rule": "source_object_slots_present",
                "expected": "non-empty list",
                "actual": type(cell.get("source_object_slots")).__name__,
            })
    if actual_pack_ids != expected_pack_ids:
        findings.append({
            "rule": "pack_ids_contiguous",
            "expected": expected_pack_ids,
            "actual": actual_pack_ids,
        })
    return findings


def _source_slot_drift(doc: dict[str, Any]) -> list[dict[str, Any]]:
    findings: list[dict[str, Any]] = []
    cells = doc.get("pack_cells") if isinstance(doc.get("pack_cells"), list) else []
    required_true = (
        "requires_dated_source_object",
        "requires_archive_status",
        "requires_source_path_review",
        "requires_privacy_review",
        "requires_expert_review",
    )
    for cell_idx, cell in enumerate(cells):
        if not isinstance(cell, dict):
            continue
        pack_id = cell.get("pack_id")
        slots = cell.get("source_object_slots") if isinstance(cell.get("source_object_slots"), list) else []
        for slot_idx, slot in enumerate(slots):
            row_id = f"{pack_id or cell_idx}:{slot_idx}"
            if not isinstance(slot, dict):
                findings.append({"slot": row_id, "rule": "source_slot_object", "actual": type(slot).__name__})
                continue
            missing = sorted(REQUIRED_SLOT_KEYS - set(slot))
            extra = sorted(set(slot) - REQUIRED_SLOT_KEYS)
            if missing or extra:
                findings.append({
                    "slot": slot.get("slot_id", row_id),
                    "missing": missing,
                    "extra": extra,
                })
            if not isinstance(slot.get("slot_id"), str) or not _SLOT_ID.fullmatch(slot["slot_id"]):
                findings.append({
                    "slot": slot.get("slot_id", row_id),
                    "rule": "slot_id_format",
                    "expected": "GPJPM-000-slot-00-safe_slug",
                    "actual": slot.get("slot_id"),
                })
            if isinstance(pack_id, str) and isinstance(slot.get("slot_id"), str):
                if not slot["slot_id"].startswith(f"{pack_id}-"):
                    findings.append({
                        "slot": slot.get("slot_id", row_id),
                        "rule": "slot_id_begins_with_pack_id",
                        "expected": pack_id,
                        "actual": slot.get("slot_id"),
                    })
            expected = {
                "status": "not_started",
                "source_coverage_status": "source_gap",
                "accepted_source_object_id": "",
            }
            actual = {
                "status": slot.get("status"),
                "source_coverage_status": slot.get("source_coverage_status"),
                "accepted_source_object_id": slot.get("accepted_source_object_id"),
            }
            if actual != expected:
                findings.append({
                    "slot": slot.get("slot_id", row_id),
                    "rule": "source_slot_unpromoted",
                    "expected": expected,
                    "actual": actual,
                })
            for key in required_true:
                if slot.get(key) is not True:
                    findings.append({
                        "slot": slot.get("slot_id", row_id),
                        "rule": key,
                        "expected": True,
                        "actual": slot.get(key),
                    })
    return findings


def _cross_product_drift(doc: dict[str, Any]) -> dict[str, Any]:
    scopes = doc.get("pilot_jurisdiction_scopes") if isinstance(doc.get("pilot_jurisdiction_scopes"), list) else []
    lenses = doc.get("domain_lenses") if isinstance(doc.get("domain_lenses"), list) else []
    cells = doc.get("pack_cells") if isinstance(doc.get("pack_cells"), list) else []
    scope_ids = [
        scope.get("id")
        for scope in scopes
        if isinstance(scope, dict) and isinstance(scope.get("id"), str)
    ]
    lens_ids = [
        lens.get("id")
        for lens in lenses
        if isinstance(lens, dict) and isinstance(lens.get("id"), str)
    ]
    expected_pairs = {(scope_id, lens_id) for scope_id in scope_ids for lens_id in lens_ids}
    actual_pairs = [
        (cell.get("jurisdiction_scope_id"), cell.get("domain_lens_id"))
        for cell in cells
        if isinstance(cell, dict)
    ]
    counts = Counter(actual_pairs)
    actual_set = set(actual_pairs)
    duplicates = [pair for pair, count in counts.items() if count > 1]
    return {
        "missing_pairs": sorted(expected_pairs - actual_set),
        "extra_pairs": sorted(actual_set - expected_pairs),
        "duplicate_pairs": sorted(duplicates),
        "expected_pair_count": len(expected_pairs),
        "actual_pair_count": len(actual_pairs),
    }


def _readiness_drift(doc: dict[str, Any]) -> list[str]:
    summary = doc.get("summary") if isinstance(doc.get("summary"), dict) else {}
    findings = [f"summary.{key}" for key in READY_FLAG_KEYS if summary.get(key) is not False]
    cells = doc.get("pack_cells") if isinstance(doc.get("pack_cells"), list) else []
    for idx, cell in enumerate(cells):
        if not isinstance(cell, dict):
            findings.append(f"pack_cells[{idx}]")
            continue
        for key in READY_FLAG_KEYS:
            if cell.get(key) is not False:
                findings.append(f"pack_cells[{idx}].{key}")
    return findings


def _current_reference(
    *,
    config_path: pathlib.Path,
    project_config_path: pathlib.Path,
    registry_path: pathlib.Path,
    regulatory_catalog_path: pathlib.Path,
) -> dict[str, Any]:
    return matrix_builder.build_jurisdiction_pack_matrix(
        config_path=config_path,
        project_config_path=project_config_path,
        registry_path=registry_path,
        regulatory_catalog_path=regulatory_catalog_path,
    )


def _comparable_sections(doc: dict[str, Any]) -> dict[str, Any]:
    return {
        "summary": doc.get("summary"),
        "domain_lenses": doc.get("domain_lenses"),
        "pilot_jurisdiction_scopes": doc.get("pilot_jurisdiction_scopes"),
        "queued_jurisdiction_scopes": doc.get("queued_jurisdiction_scopes"),
        "pack_cells": doc.get("pack_cells"),
    }


def validate_jurisdiction_pack_matrix(
    doc: Any,
    *,
    matrix_path: pathlib.Path | None = None,
    config_path: pathlib.Path = matrix_builder.CONFIG,
    project_config_path: pathlib.Path = project_plan_builder.CONFIG,
    registry_path: pathlib.Path = project_plan_builder.REGISTRY,
    regulatory_catalog_path: pathlib.Path = project_plan_builder.REGULATORY_CATALOG,
    compare_current_chain: bool = True,
) -> dict[str, Any]:
    if not isinstance(doc, dict):
        checks = [_check("matrix_is_object", False, expected="object", actual=type(doc).__name__)]
        failed = _failed_ids(checks)
        return {
            "_meta": {
                "schema_version": "global_protections_jurisdiction_pack_matrix_validation.v1",
                "source_matrix_path": _display_path(matrix_path) if matrix_path else "n/a",
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
    cross_product = _cross_product_drift(doc)
    current = (
        _current_reference(
            config_path=config_path,
            project_config_path=project_config_path,
            registry_path=registry_path,
            regulatory_catalog_path=regulatory_catalog_path,
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
            "project_status_is_propose_only",
            isinstance(doc.get("project"), dict) and doc["project"].get("status") == "propose_only",
            expected="propose_only",
            actual=doc.get("project", {}).get("status") if isinstance(doc.get("project"), dict) else type(doc.get("project")).__name__,
        ),
        _check(
            "pack_cell_shape",
            not _pack_cell_shape_drift(doc),
            expected=[],
            actual=_pack_cell_shape_drift(doc),
        ),
        _check(
            "source_slot_integrity",
            not _source_slot_drift(doc),
            expected=[],
            actual=_source_slot_drift(doc),
        ),
        _check(
            "summary_counts_match_matrix",
            not _summary_counts_mismatches(doc),
            expected=[],
            actual=_summary_counts_mismatches(doc),
        ),
        _check(
            "embedded_checks_all_ok",
            not embedded["failed"] and not embedded["missing_required"],
            expected={"failed": [], "missing_required": []},
            actual=embedded,
        ),
        _check(
            "cross_product_cells_unique_and_complete",
            not cross_product["missing_pairs"]
            and not cross_product["extra_pairs"]
            and not cross_product["duplicate_pairs"]
            and cross_product["actual_pair_count"] == cross_product["expected_pair_count"],
            expected={
                "missing_pairs": [],
                "extra_pairs": [],
                "duplicate_pairs": [],
                "actual_pair_count": cross_product["expected_pair_count"],
            },
            actual=cross_product,
        ),
        _check(
            "all_readiness_flags_blocked",
            not _readiness_drift(doc),
            expected=[],
            actual=_readiness_drift(doc),
        ),
        _check(
            "privacy_scan_ok",
            privacy_scan.get("ok") is True,
            expected=True,
            actual=privacy_scan.get("counts"),
        ),
        _check(
            "matrix_contains_no_disallowed_text",
            not disallowed,
            expected=[],
            actual=disallowed,
        ),
    ]
    if compare_current_chain:
        checks.append(
            _check(
                "matrix_matches_current_chain",
                _comparable_sections(doc) == current_sections,
                expected=current_sections,
                actual=_comparable_sections(doc),
            )
        )
    failed = _failed_ids(checks)
    return {
        "_meta": {
            "schema_version": "global_protections_jurisdiction_pack_matrix_validation.v1",
            "source_matrix_path": _display_path(matrix_path) if matrix_path else "n/a",
            "config_path": _display_path(config_path),
            "project_config": _display_path(project_config_path),
            "registry_path": _display_path(registry_path),
            "regulatory_catalog_path": _display_path(regulatory_catalog_path),
            "compare_current_chain": compare_current_chain,
        },
        "summary": {
            "valid": not failed,
            "check_count": len(checks),
            "failed_check_count": len(failed),
            "failed_check_ids": failed,
            "jurisdiction_scope_count": summary.get("jurisdiction_scope_count"),
            "jurisdiction_scope_ids": summary.get("jurisdiction_scope_ids"),
            "queued_jurisdiction_scope_count": summary.get("queued_jurisdiction_scope_count"),
            "queued_jurisdiction_scope_ids": summary.get("queued_jurisdiction_scope_ids"),
            "domain_lens_count": summary.get("domain_lens_count"),
            "domain_lens_ids": summary.get("domain_lens_ids"),
            "pack_cell_count": summary.get("pack_cell_count"),
            "source_object_slot_count": summary.get("source_object_slot_count"),
            "not_started_source_object_slots": summary.get("not_started_source_object_slots"),
            "ready_for_prompt_generation": summary.get("ready_for_prompt_generation"),
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
        "# Global Protections Jurisdiction-Pack Matrix Validation",
        "",
        "This read-only report validates the saved jurisdiction-pack matrix before pack curation work is trusted.",
        "",
        "## Summary",
        "",
        "| Metric | Value |",
        "|---|---:|",
        f"| Valid | {str(bool(summary['valid'])).lower()} |",
        f"| Checks | {summary['check_count']} |",
        f"| Failed checks | {summary['failed_check_count']} |",
        f"| Jurisdiction scopes | {_md_cell(summary.get('jurisdiction_scope_count'))} |",
        f"| Jurisdiction scope IDs | {_md_cell(summary.get('jurisdiction_scope_ids'))} |",
        f"| Queued jurisdiction scopes | {_md_cell(summary.get('queued_jurisdiction_scope_count'))} |",
        f"| Queued jurisdiction scope IDs | {_md_cell(summary.get('queued_jurisdiction_scope_ids'))} |",
        f"| Domain lenses | {_md_cell(summary.get('domain_lens_count'))} |",
        f"| Domain lens IDs | {_md_cell(summary.get('domain_lens_ids'))} |",
        f"| Pack cells | {_md_cell(summary.get('pack_cell_count'))} |",
        f"| Source-object slots | {_md_cell(summary.get('source_object_slot_count'))} |",
        f"| Not-started source-object slots | {_md_cell(summary.get('not_started_source_object_slots'))} |",
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
    ap.add_argument("--matrix", type=pathlib.Path, default=DEFAULT_MATRIX)
    ap.add_argument("--config", type=pathlib.Path, default=matrix_builder.CONFIG)
    ap.add_argument("--project-config", type=pathlib.Path, default=project_plan_builder.CONFIG)
    ap.add_argument("--registry", type=pathlib.Path, default=project_plan_builder.REGISTRY)
    ap.add_argument("--regulatory-catalog", type=pathlib.Path, default=project_plan_builder.REGULATORY_CATALOG)
    ap.add_argument("--out", type=pathlib.Path, default=OUT)
    ap.add_argument("--markdown-out", type=pathlib.Path, default=MD_OUT)
    ap.add_argument("--no-current-chain", action="store_true", help="skip comparison to the current generated chain")
    ap.add_argument("--validate", action="store_true", help="print the validation summary only; write nothing")
    args = ap.parse_args(argv)

    doc = _load_json(args.matrix)
    if doc is None:
        print(f"[global-protections-jurisdiction-pack-matrix-validation] unreadable matrix: {args.matrix}")
        return 1
    report = validate_jurisdiction_pack_matrix(
        doc,
        matrix_path=args.matrix,
        config_path=args.config,
        project_config_path=args.project_config,
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
        "[global-protections-jurisdiction-pack-matrix-validation] "
        f"valid={str(bool(summary['valid'])).lower()}; "
        f"failed={summary['failed_check_count']}/{summary['check_count']}; "
        f"ready_for_comparable_scoring={str(bool(summary['ready_for_comparable_scoring'])).lower()} -> {args.matrix}"
    )
    return 0 if summary["valid"] else 1


if __name__ == "__main__":
    raise SystemExit(main())
