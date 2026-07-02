#!/usr/bin/env python3
"""Build a compact source-coverage matrix for a benchmark domain.

This is a derived triage artifact for the source-research plan. It groups the
source-object tasks by jurisdiction and category, flags pending manifest rows
that can be promoted after review, and marks cells that are still blocked by
broad corridor/scope labels.

It does not fetch sources, verify law, create source rows, edit a grounding
manifest, generate prompts, or authorize comparable benchmark scoring.
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

from build_domain_source_research_plan import build_source_research_plan  # noqa: E402

OUT_DIR = _ROOT / "reports" / "benchmark"
_SAFE_DOMAIN_ID = re.compile(r"^[a-z0-9_:-]{1,80}$")


def _safe_domain_id(domain_id: str) -> str:
    if not _SAFE_DOMAIN_ID.fullmatch(domain_id):
        raise ValueError(f"unsafe domain id: {domain_id!r}")
    return domain_id


def _load_plan(path: pathlib.Path) -> dict[str, Any]:
    doc = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(doc, dict):
        raise ValueError(f"source-research plan must contain a JSON object: {path}")
    return doc


def _priority_band(task: dict[str, Any], scope_blocked: bool) -> str:
    if scope_blocked:
        return "1_scope_refinement_first"
    if task.get("action") == "curate_and_promote_existing_manifest_row":
        return "2_promote_existing_pending_row"
    return "3_add_missing_source_row"


def _coverage_status(task: dict[str, Any]) -> str:
    if task.get("action") == "curate_and_promote_existing_manifest_row":
        return "pending_manifest_row"
    if task.get("current_status") == "missing":
        return "missing_manifest_row"
    return "needs_review"


def _next_step(task: dict[str, Any], scope_blocked: bool) -> str:
    if scope_blocked:
        return "resolve broad corridor scope, then complete source review for this jurisdiction/category"
    if task.get("action") == "curate_and_promote_existing_manifest_row":
        return "fill the existing pending manifest row with dated source metadata and expert review"
    return "create a reviewed manifest row only after dated public source and privacy checks pass"


def _scope_index(scope_tasks: list[dict[str, Any]]) -> dict[str, list[dict[str, Any]]]:
    by_prompt: dict[str, list[dict[str, Any]]] = {}
    for task in scope_tasks:
        for prompt_id in task.get("blocked_prompt_ids", []) or []:
            by_prompt.setdefault(str(prompt_id), []).append(task)
    return by_prompt


def _cell_id(jurisdiction: str, category: str) -> str:
    return f"{jurisdiction}:{category}"


def _build_matrix_rows(plan_doc: dict[str, Any]) -> list[dict[str, Any]]:
    source_tasks = [
        task for task in plan_doc.get("source_research_tasks", [])
        if isinstance(task, dict)
    ]
    scope_tasks = [
        task for task in plan_doc.get("scope_refinement_tasks", [])
        if isinstance(task, dict)
    ]
    scopes_by_prompt = _scope_index(scope_tasks)
    rows: list[dict[str, Any]] = []
    for task in source_tasks:
        prompt_ids = [str(pid) for pid in task.get("blocked_prompt_ids", []) or []]
        related_scope_tasks = {
            str(scope_task.get("task_id"))
            for prompt_id in prompt_ids
            for scope_task in scopes_by_prompt.get(prompt_id, [])
        }
        related_scopes = sorted({
            str(scope_task.get("scope"))
            for prompt_id in prompt_ids
            for scope_task in scopes_by_prompt.get(prompt_id, [])
            if scope_task.get("scope")
        })
        jurisdiction = str(task.get("jurisdiction") or "")
        category = str(task.get("category") or "")
        scope_blocked = bool(related_scope_tasks)
        rows.append({
            "cell_id": _cell_id(jurisdiction, category),
            "jurisdiction": jurisdiction,
            "jurisdiction_label": task.get("jurisdiction_label"),
            "category": category,
            "source_id": task.get("source_id"),
            "source_task_id": task.get("task_id"),
            "action": task.get("action"),
            "coverage_status": _coverage_status(task),
            "current_status": task.get("current_status"),
            "priority_band": _priority_band(task, scope_blocked),
            "scope_blocked": scope_blocked,
            "related_scope_task_ids": sorted(related_scope_tasks),
            "related_unresolved_scopes": related_scopes,
            "blocked_prompt_ids": prompt_ids,
            "blocked_prompt_count": len(prompt_ids),
            "next_step": _next_step(task, scope_blocked),
        })
    rows.sort(key=lambda row: (
        row["priority_band"],
        row["jurisdiction"],
        row["category"],
        str(row["source_id"]),
    ))
    return rows


def _scope_rows(plan_doc: dict[str, Any], matrix_rows: list[dict[str, Any]]) -> list[dict[str, Any]]:
    cells_by_scope_task: dict[str, list[str]] = {}
    for row in matrix_rows:
        for task_id in row["related_scope_task_ids"]:
            cells_by_scope_task.setdefault(task_id, []).append(row["cell_id"])
    rows: list[dict[str, Any]] = []
    for task in plan_doc.get("scope_refinement_tasks", []) or []:
        if not isinstance(task, dict):
            continue
        task_id = str(task.get("task_id"))
        cells = sorted(set(cells_by_scope_task.get(task_id, [])))
        rows.append({
            "task_id": task_id,
            "scope": task.get("scope"),
            "category": task.get("category"),
            "blocked_prompt_ids": list(task.get("blocked_prompt_ids") or []),
            "related_coverage_cell_ids": cells,
            "related_coverage_cell_count": len(cells),
            "next_step": "resolve to concrete jurisdictions/forums before local-law source rows are promoted",
        })
    rows.sort(key=lambda row: (str(row["scope"]), str(row["category"]), str(row["task_id"])))
    return rows


def _checks(plan_doc: dict[str, Any], matrix_rows: list[dict[str, Any]], scope_rows: list[dict[str, Any]]) -> list[dict[str, Any]]:
    summary = plan_doc.get("summary", {})
    ready_claim = bool(summary.get("prompts_ready_for_comparable_run"))
    return [
        {
            "id": "source_task_count_matches_matrix",
            "ok": summary.get("source_object_tasks") == len(matrix_rows),
            "expected": summary.get("source_object_tasks"),
            "actual": len(matrix_rows),
        },
        {
            "id": "scope_task_count_matches_matrix",
            "ok": summary.get("scope_refinement_tasks") == len(scope_rows),
            "expected": summary.get("scope_refinement_tasks"),
            "actual": len(scope_rows),
        },
        {
            "id": "no_comparable_scoring_claim",
            "ok": ready_claim is False,
            "expected": False,
            "actual": ready_claim,
        },
    ]


def build_source_coverage_matrix(
    domain_id: str,
    *,
    plan_doc: dict[str, Any] | None = None,
) -> dict[str, Any]:
    """Return a compact source-coverage triage matrix for a domain."""
    domain_id = _safe_domain_id(domain_id)
    plan_doc = plan_doc or build_source_research_plan(domain_id)
    plan_summary = plan_doc.get("summary", {})
    matrix_rows = _build_matrix_rows(plan_doc)
    scope_rows = _scope_rows(plan_doc, matrix_rows)
    priority_counts: dict[str, int] = {}
    for row in matrix_rows:
        priority_counts[row["priority_band"]] = priority_counts.get(row["priority_band"], 0) + 1
    action_counts: dict[str, int] = {}
    for row in matrix_rows:
        action = str(row["action"])
        action_counts[action] = action_counts.get(action, 0) + 1
    checks = _checks(plan_doc, matrix_rows, scope_rows)
    blocked_prompt_ids = sorted({
        str(prompt_id)
        for row in matrix_rows
        for prompt_id in row["blocked_prompt_ids"]
    } | {
        str(prompt_id)
        for row in scope_rows
        for prompt_id in row["blocked_prompt_ids"]
    })
    return {
        "_meta": {
            "domain": domain_id,
            "display_name": (plan_doc.get("_meta") or {}).get("display_name"),
            "status": (
                "source-coverage matrix; not legal advice, not source verification, "
                "and not comparable benchmark evidence"
            ),
            "source_plan_status": (plan_doc.get("_meta") or {}).get("status"),
        },
        "summary": {
            "consistency_ok": all(check["ok"] for check in checks),
            "coverage_cells": len(matrix_rows),
            "jurisdiction_count": len({row["jurisdiction"] for row in matrix_rows}),
            "category_count": len({row["category"] for row in matrix_rows}),
            "blocked_prompt_count": len(blocked_prompt_ids),
            "pending_manifest_rows_to_promote": action_counts.get("curate_and_promote_existing_manifest_row", 0),
            "missing_manifest_rows_to_add": action_counts.get("add_manifest_row", 0),
            "scope_refinement_tasks": len(scope_rows),
            "scope_blocked_cells": sum(1 for row in matrix_rows if row["scope_blocked"]),
            "priority_counts": {key: priority_counts[key] for key in sorted(priority_counts)},
            "prompts_ready_for_comparable_run": plan_summary.get("prompts_ready_for_comparable_run"),
            "prompts_blocked_for_comparable_run": plan_summary.get("prompts_blocked_for_comparable_run"),
            "ready_for_comparable_run": False,
            "policy": (
                "Use this matrix only to prioritize curation work. It contains task metadata, not legal "
                "claims; every source row still needs dated public-source review, privacy review, and "
                "expert review before manifest promotion or scoring."
            ),
        },
        "matrix_rows": matrix_rows,
        "scope_refinement_rows": scope_rows,
        "consistency_checks": checks,
        "source_plan_summary": {
            "source_object_tasks": plan_summary.get("source_object_tasks"),
            "scope_refinement_tasks": plan_summary.get("scope_refinement_tasks"),
            "blocked_prompt_count": plan_summary.get("blocked_prompt_count"),
            "missing_verified_local_jurisdictions": plan_summary.get("missing_verified_local_jurisdictions", []),
            "unresolved_corridor_scopes": plan_summary.get("unresolved_corridor_scopes", []),
        },
    }


def default_out_path(domain_id: str) -> pathlib.Path:
    return OUT_DIR / f"{_safe_domain_id(domain_id)}_source_coverage_matrix.json"


def default_markdown_path(json_path: pathlib.Path) -> pathlib.Path:
    return json_path.with_suffix(".md")


def _md_cell(value: Any) -> str:
    text = str(value if value is not None else "")
    return text.replace("|", "\\|").replace("\n", " ").strip()


def _md_list(values: list[Any]) -> str:
    return ", ".join(_md_cell(v) for v in values) if values else "-"


def build_markdown_report(doc: dict[str, Any]) -> str:
    """Render a compact Markdown source-coverage matrix."""
    meta = doc["_meta"]
    summary = doc["summary"]
    lines: list[str] = [
        f"# Domain Source Coverage Matrix - {_md_cell(meta.get('display_name') or meta.get('domain'))}",
        "",
        (
            "This matrix is a triage artifact for source curation. It is not legal advice, "
            "not source verification, and not comparable benchmark evidence."
        ),
        "",
        "## Summary",
        "",
        "| Metric | Value |",
        "|---|---:|",
        f"| Consistency OK | {str(bool(summary['consistency_ok'])).lower()} |",
        f"| Coverage cells | {summary['coverage_cells']} |",
        f"| Jurisdictions | {summary['jurisdiction_count']} |",
        f"| Categories | {summary['category_count']} |",
        f"| Blocked prompts covered | {summary['blocked_prompt_count']} |",
        f"| Pending manifest rows to promote | {summary['pending_manifest_rows_to_promote']} |",
        f"| Missing manifest rows to add | {summary['missing_manifest_rows_to_add']} |",
        f"| Scope-refinement tasks | {summary['scope_refinement_tasks']} |",
        f"| Scope-blocked cells | {summary['scope_blocked_cells']} |",
        f"| Ready for comparable run | {str(bool(summary['ready_for_comparable_run'])).lower()} |",
        "",
        "## Priority Bands",
        "",
        "| Band | Cells |",
        "|---|---:|",
    ]
    for band, count in summary["priority_counts"].items():
        lines.append(f"| `{_md_cell(band)}` | {count} |")
    lines.extend([
        "",
        "## Matrix",
        "",
        "| Priority | Cell | Source ID | Status | Scope blocked | Blocked prompts | Next step |",
        "|---|---|---|---|---:|---|---|",
    ])
    for row in doc["matrix_rows"]:
        lines.append(
            f"| `{_md_cell(row['priority_band'])}` "
            f"| `{_md_cell(row['cell_id'])}` "
            f"| `{_md_cell(row['source_id'])}` "
            f"| {_md_cell(row['coverage_status'])} "
            f"| {str(bool(row['scope_blocked'])).lower()} "
            f"| {_md_list(row['blocked_prompt_ids'])} "
            f"| {_md_cell(row['next_step'])} |"
        )
    lines.extend([
        "",
        "## Scope Refinement",
        "",
        "| Task | Scope | Category | Related cells | Blocked prompts |",
        "|---|---|---|---|---|",
    ])
    for row in doc["scope_refinement_rows"]:
        lines.append(
            f"| `{_md_cell(row['task_id'])}` "
            f"| {_md_cell(row['scope'])} "
            f"| {_md_cell(row['category'])} "
            f"| {_md_list(row['related_coverage_cell_ids'])} "
            f"| {_md_list(row['blocked_prompt_ids'])} |"
        )
    lines.extend([
        "",
        "## Consistency Checks",
        "",
        "| Check | OK | Expected | Actual |",
        "|---|---:|---|---|",
    ])
    for check in doc["consistency_checks"]:
        lines.append(
            f"| {_md_cell(check['id'])} "
            f"| {str(bool(check['ok'])).lower()} "
            f"| {_md_cell(check['expected'])} "
            f"| {_md_cell(check['actual'])} |"
        )
    lines.append("")
    return "\n".join(lines)


def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--domain", default="developing_country_worker_protections")
    ap.add_argument("--plan", type=pathlib.Path, default=None, help="optional prebuilt source-research plan JSON")
    ap.add_argument("--out", type=pathlib.Path, default=None)
    ap.add_argument("--md-out", type=pathlib.Path, default=None, help="Markdown report path; defaults to --out with .md suffix")
    ap.add_argument("--no-md", action="store_true", help="write only JSON, not the Markdown matrix report")
    args = ap.parse_args(argv)

    plan_doc = _load_plan(args.plan) if args.plan else None
    doc = build_source_coverage_matrix(args.domain, plan_doc=plan_doc)
    out_path = args.out or default_out_path(args.domain)
    out_path.parent.mkdir(parents=True, exist_ok=True)
    out_path.write_text(json.dumps(doc, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
    md_path = None
    if not args.no_md:
        md_path = args.md_out or default_markdown_path(out_path)
        md_path.parent.mkdir(parents=True, exist_ok=True)
        md_path.write_text(build_markdown_report(doc) + "\n", encoding="utf-8")
    summary = doc["summary"]
    print(
        f"wrote {out_path}: {summary['coverage_cells']} coverage cells; "
        f"{summary['scope_blocked_cells']} scope-blocked; "
        f"ready_for_comparable_run={str(bool(summary['ready_for_comparable_run'])).lower()}"
        + (f"; report {md_path}" if md_path else "")
    )
    return 0 if summary["consistency_ok"] else 1


if __name__ == "__main__":
    raise SystemExit(main())
