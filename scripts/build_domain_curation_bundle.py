#!/usr/bin/env python3
"""Build an end-to-end source-curation status bundle for a benchmark domain.

This command runs the source-gated curation chain in memory:

1. grounding gap queue
2. source-research plan
3. source-coverage matrix
4. blank source-review packet
5. source-review sprint packet
6. source-review progress ledger
7. source-review validation report
8. non-mutating grounding-manifest proposal

It emits a compact status bundle and consistency checks. It does not fetch
sources, verify law, or edit ``grounding_sources.json``.
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

import build_domain_grounding_manifest_proposal as manifest_proposal  # noqa: E402
import build_domain_grounding_queue as grounding_queue  # noqa: E402
import build_domain_source_coverage_matrix as source_coverage_matrix  # noqa: E402
import build_domain_source_research_plan as source_research_plan  # noqa: E402
import build_domain_source_review_ledger as source_review_ledger  # noqa: E402
import build_domain_source_review_packet as source_review_packet  # noqa: E402
import build_domain_source_review_sprint as source_review_sprint  # noqa: E402
import validate_domain_source_review_packet as source_review_validator  # noqa: E402
from artifact_path_policy import handoff_artifact_path  # noqa: E402

OUT_DIR = _ROOT / "reports" / "benchmark"
_SAFE_DOMAIN_ID = re.compile(r"^[a-z0-9_:-]{1,80}$")


def _artifact_path(path: pathlib.Path) -> str:
    return handoff_artifact_path(path, root=_ROOT)


def _safe_domain_id(domain_id: str) -> str:
    if not _SAFE_DOMAIN_ID.fullmatch(domain_id):
        raise ValueError(f"unsafe domain id: {domain_id!r}")
    return domain_id


def build_curation_chain(domain_id: str) -> dict[str, dict[str, Any]]:
    """Run the non-mutating source-curation chain and return full component docs."""
    domain_id = _safe_domain_id(domain_id)
    queue_doc = grounding_queue.build_grounding_queue(domain_id)
    research_doc = source_research_plan.build_source_research_plan(domain_id, queue_doc=queue_doc)
    matrix_doc = source_coverage_matrix.build_source_coverage_matrix(domain_id, plan_doc=research_doc)
    packet_doc = source_review_packet.build_source_review_packet(domain_id, source_plan_doc=research_doc)
    sprint_doc = source_review_sprint.build_source_review_sprint(
        domain_id,
        matrix_doc=matrix_doc,
        review_packet_doc=packet_doc,
    )
    ledger_doc = source_review_ledger.build_source_review_ledger(
        domain_id,
        review_packet_doc=packet_doc,
    )
    validation_doc = source_review_validator.validate_source_review_packet(packet_doc, domain_id=domain_id)
    proposal_doc = manifest_proposal.build_grounding_manifest_proposal(
        domain_id,
        validation_doc=validation_doc,
    )
    return {
        "grounding_queue": queue_doc,
        "source_research_plan": research_doc,
        "source_coverage_matrix": matrix_doc,
        "source_review_packet": packet_doc,
        "source_review_sprint": sprint_doc,
        "source_review_ledger": ledger_doc,
        "source_review_validation": validation_doc,
        "grounding_manifest_proposal": proposal_doc,
    }


def _check(check_id: str, ok: bool, *, expected: Any, actual: Any) -> dict[str, Any]:
    return {
        "id": check_id,
        "ok": bool(ok),
        "expected": expected,
        "actual": actual,
    }


def _component_summaries(chain: dict[str, dict[str, Any]]) -> dict[str, Any]:
    return {
        name: dict(doc.get("summary", {}))
        for name, doc in chain.items()
    }


def build_curation_bundle(
    domain_id: str,
    *,
    chain: dict[str, dict[str, Any]] | None = None,
    component_dir: pathlib.Path | None = None,
) -> dict[str, Any]:
    """Return a compact end-to-end curation bundle with consistency checks."""
    domain_id = _safe_domain_id(domain_id)
    chain = chain or build_curation_chain(domain_id)
    queue_summary = chain["grounding_queue"]["summary"]
    research_summary = chain["source_research_plan"]["summary"]
    packet_summary = chain["source_review_packet"]["summary"]
    matrix_summary = chain["source_coverage_matrix"]["summary"]
    sprint_summary = chain["source_review_sprint"]["summary"]
    ledger_summary = chain["source_review_ledger"]["summary"]
    validation_summary = chain["source_review_validation"]["summary"]
    proposal_summary = chain["grounding_manifest_proposal"]["summary"]
    source_counts = {
        "grounding_queue": len(chain["grounding_queue"]["source_object_queue"]),
        "source_research_plan": research_summary["source_object_tasks"],
        "source_review_packet": packet_summary["source_candidate_rows"],
        "source_review_validation": validation_summary["source_rows"],
    }
    scope_counts = {
        "grounding_queue": len(chain["grounding_queue"].get("scope_refinement_queue", [])),
        "source_research_plan": research_summary["scope_refinement_tasks"],
        "source_review_packet": packet_summary["scope_resolution_rows"],
        "source_review_validation": validation_summary["scope_rows"],
    }
    checks = [
        _check(
            "source_object_counts_match",
            len(set(source_counts.values())) == 1,
            expected="same count across queue, plan, packet, validation",
            actual=source_counts,
        ),
        _check(
            "scope_refinement_counts_match",
            len(set(scope_counts.values())) == 1,
            expected="same count across queue, plan, packet, validation",
            actual=scope_counts,
        ),
        _check(
            "blocked_prompt_count_matches",
            queue_summary["prompts_blocked_for_comparable_run"] == research_summary["blocked_prompt_count"],
            expected=queue_summary["prompts_blocked_for_comparable_run"],
            actual=research_summary["blocked_prompt_count"],
        ),
        _check(
            "blank_packet_safety_audit_ok",
            chain["source_review_packet"]["safety_audit"]["ok"] is True,
            expected=True,
            actual=chain["source_review_packet"]["safety_audit"]["ok"],
        ),
        _check(
            "coverage_matrix_counts_match",
            matrix_summary["coverage_cells"] == research_summary["source_object_tasks"],
            expected=research_summary["source_object_tasks"],
            actual=matrix_summary["coverage_cells"],
        ),
        _check(
            "coverage_matrix_consistency_ok",
            matrix_summary["consistency_ok"] is True,
            expected=True,
            actual=matrix_summary["consistency_ok"],
        ),
        _check(
            "source_review_sprint_consistency_ok",
            sprint_summary["consistency_ok"] is True,
            expected=True,
            actual=sprint_summary["consistency_ok"],
        ),
        _check(
            "source_review_sprint_has_no_ready_claims",
            sprint_summary["all_source_rows_ready_for_manifest_promotion"] is False
            and sprint_summary["all_scope_rows_ready_for_source_queue_update"] is False,
            expected=False,
            actual=(
                sprint_summary["all_source_rows_ready_for_manifest_promotion"]
                or sprint_summary["all_scope_rows_ready_for_source_queue_update"]
            ),
        ),
        _check(
            "source_review_ledger_consistency_ok",
            ledger_summary["consistency_ok"] is True,
            expected=True,
            actual=ledger_summary["consistency_ok"],
        ),
        _check(
            "source_review_ledger_matches_validation",
            ledger_summary["source_rows_ready_claimed"] == validation_summary["source_rows_ready_claimed"]
            and ledger_summary["scope_rows_ready_claimed"] == validation_summary["scope_rows_ready_claimed"],
            expected={
                "source_ready": validation_summary["source_rows_ready_claimed"],
                "scope_ready": validation_summary["scope_rows_ready_claimed"],
            },
            actual={
                "source_ready": ledger_summary["source_rows_ready_claimed"],
                "scope_ready": ledger_summary["scope_rows_ready_claimed"],
            },
        ),
        _check(
            "source_review_validation_ok",
            validation_summary["ok"] is True,
            expected=True,
            actual=validation_summary["ok"],
        ),
        _check(
            "manifest_proposal_ok",
            proposal_summary["proposal_ok"] is True,
            expected=True,
            actual=proposal_summary["proposal_ok"],
        ),
        _check(
            "manifest_preview_valid",
            proposal_summary["preview_validation_issue_count"] == 0,
            expected=0,
            actual=proposal_summary["preview_validation_issue_count"],
        ),
    ]
    consistency_ok = all(item["ok"] for item in checks)
    comparable_ready = (
        queue_summary["prompts_ready_for_comparable_run"] == queue_summary["prompt_count"]
        and proposal_summary["ready_for_manual_manifest_patch"] is False
        and queue_summary["verified_local_law_rows"] > 0
    )
    return {
        "_meta": {
            "domain": domain_id,
            "display_name": chain["grounding_queue"]["_meta"].get("display_name"),
            "status": (
                "end-to-end source-curation bundle; not legal advice, not source verification, "
                "and not comparable benchmark evidence"
            ),
        },
        "summary": {
            "consistency_ok": consistency_ok,
            "prompt_count": queue_summary["prompt_count"],
            "prompts_ready_for_comparable_run": queue_summary["prompts_ready_for_comparable_run"],
            "prompts_blocked_for_comparable_run": queue_summary["prompts_blocked_for_comparable_run"],
            "verified_local_law_rows": queue_summary["verified_local_law_rows"],
            "source_object_tasks": source_counts["source_research_plan"],
            "scope_refinement_tasks": scope_counts["source_research_plan"],
            "source_coverage_cells": matrix_summary["coverage_cells"],
            "source_coverage_scope_blocked_cells": matrix_summary["scope_blocked_cells"],
            "source_coverage_pending_manifest_rows_to_promote": matrix_summary[
                "pending_manifest_rows_to_promote"
            ],
            "source_coverage_missing_manifest_rows_to_add": matrix_summary["missing_manifest_rows_to_add"],
            "source_review_sprint_rows": sprint_summary["source_review_sprint_rows"],
            "scope_resolution_sprint_rows": sprint_summary["scope_resolution_sprint_rows"],
            "source_review_sprint_deferred_scope_blocked_rows": sprint_summary[
                "deferred_scope_blocked_source_rows"
            ],
            "source_review_ledger_source_rows_not_started": ledger_summary["source_rows_not_started"],
            "source_review_ledger_scope_rows_not_started": ledger_summary["scope_rows_not_started"],
            "source_review_ledger_source_rows_in_progress_not_ready": ledger_summary[
                "source_rows_in_progress_not_ready"
            ],
            "source_review_ledger_scope_rows_in_progress_not_ready": ledger_summary[
                "scope_rows_in_progress_not_ready"
            ],
            "source_review_validation_ok": validation_summary["ok"],
            "source_rows_ready_claimed": validation_summary["source_rows_ready_claimed"],
            "source_rows_accepted_for_manifest_proposal": validation_summary[
                "source_rows_accepted_for_manifest_proposal"
            ],
            "manifest_proposal_ok": proposal_summary["proposal_ok"],
            "manifest_operations_ready_for_manual_patch": proposal_summary["accepted_operations"],
            "ready_for_manual_manifest_patch": proposal_summary["ready_for_manual_manifest_patch"],
            "ready_for_comparable_run": comparable_ready,
            "policy": (
                "This bundle is a status artifact only. It proves local consistency of the generated "
                "curation chain but does not promote law, fetch sources, or score the domain."
            ),
        },
        "component_summaries": _component_summaries(chain),
        "consistency_checks": checks,
        "artifact_paths": component_paths(domain_id, output_dir=component_dir),
    }


def default_out_path(domain_id: str) -> pathlib.Path:
    return OUT_DIR / f"{_safe_domain_id(domain_id)}_curation_bundle.json"


def default_markdown_path(json_path: pathlib.Path) -> pathlib.Path:
    return json_path.with_suffix(".md")


def component_paths(domain_id: str, *, output_dir: pathlib.Path | None = None) -> dict[str, str]:
    """Return handoff-safe component artifact paths for the domain."""
    domain_id = _safe_domain_id(domain_id)
    base = output_dir or OUT_DIR
    names = {
        "grounding_queue": f"{domain_id}_grounding_queue",
        "source_research_plan": f"{domain_id}_source_research_plan",
        "source_coverage_matrix": f"{domain_id}_source_coverage_matrix",
        "source_review_packet": f"{domain_id}_source_review_packet",
        "source_review_sprint": f"{domain_id}_source_review_sprint",
        "source_review_ledger": f"{domain_id}_source_review_ledger",
        "source_review_validation": f"{domain_id}_source_review_validation",
        "grounding_manifest_proposal": f"{domain_id}_grounding_manifest_proposal",
        "curation_bundle": f"{domain_id}_curation_bundle",
    }
    out: dict[str, str] = {}
    for key, stem in names.items():
        out[f"{key}_json"] = _artifact_path(base / f"{stem}.json")
        out[f"{key}_markdown"] = _artifact_path(base / f"{stem}.md")
    return out


def _component_file_paths(domain_id: str, *, output_dir: pathlib.Path | None = None) -> dict[str, pathlib.Path]:
    """Return writable component artifact paths for the domain."""
    domain_id = _safe_domain_id(domain_id)
    base = output_dir or OUT_DIR
    names = {
        "grounding_queue": f"{domain_id}_grounding_queue",
        "source_research_plan": f"{domain_id}_source_research_plan",
        "source_coverage_matrix": f"{domain_id}_source_coverage_matrix",
        "source_review_packet": f"{domain_id}_source_review_packet",
        "source_review_sprint": f"{domain_id}_source_review_sprint",
        "source_review_ledger": f"{domain_id}_source_review_ledger",
        "source_review_validation": f"{domain_id}_source_review_validation",
        "grounding_manifest_proposal": f"{domain_id}_grounding_manifest_proposal",
        "curation_bundle": f"{domain_id}_curation_bundle",
    }
    out: dict[str, pathlib.Path] = {}
    for key, stem in names.items():
        out[f"{key}_json"] = base / f"{stem}.json"
        out[f"{key}_markdown"] = base / f"{stem}.md"
    return out


def _write_doc_pair(
    doc: dict[str, Any],
    json_path: pathlib.Path,
    markdown_path: pathlib.Path,
    markdown: str,
) -> None:
    json_path.parent.mkdir(parents=True, exist_ok=True)
    markdown_path.parent.mkdir(parents=True, exist_ok=True)
    json_path.write_text(json.dumps(doc, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
    markdown_path.write_text(markdown + "\n", encoding="utf-8")


def write_component_artifacts(
    domain_id: str,
    chain: dict[str, dict[str, Any]],
    *,
    output_dir: pathlib.Path | None = None,
) -> dict[str, str]:
    """Write component artifacts and return handoff-safe artifact paths."""
    file_paths = _component_file_paths(domain_id, output_dir=output_dir)
    paths = component_paths(domain_id, output_dir=output_dir)
    writers = {
        "grounding_queue": (
            grounding_queue.build_markdown_report,
            chain["grounding_queue"],
        ),
        "source_research_plan": (
            source_research_plan.build_markdown_report,
            chain["source_research_plan"],
        ),
        "source_coverage_matrix": (
            source_coverage_matrix.build_markdown_report,
            chain["source_coverage_matrix"],
        ),
        "source_review_packet": (
            source_review_packet.build_markdown_report,
            chain["source_review_packet"],
        ),
        "source_review_sprint": (
            source_review_sprint.build_markdown_report,
            chain["source_review_sprint"],
        ),
        "source_review_ledger": (
            source_review_ledger.build_markdown_report,
            chain["source_review_ledger"],
        ),
        "source_review_validation": (
            source_review_validator.build_markdown_report,
            chain["source_review_validation"],
        ),
        "grounding_manifest_proposal": (
            manifest_proposal.build_markdown_report,
            chain["grounding_manifest_proposal"],
        ),
    }
    for key, (markdown_fn, doc) in writers.items():
        _write_doc_pair(
            doc,
            file_paths[f"{key}_json"],
            file_paths[f"{key}_markdown"],
            markdown_fn(doc),
        )
    return paths


def _md_cell(value: Any) -> str:
    text = str(value if value is not None else "")
    return text.replace("|", "\\|").replace("\n", " ").strip()


def build_markdown_report(doc: dict[str, Any]) -> str:
    """Render a compact Markdown curation bundle."""
    meta = doc["_meta"]
    summary = doc["summary"]
    lines: list[str] = [
        f"# Domain Curation Bundle - {_md_cell(meta.get('display_name') or meta.get('domain'))}",
        "",
        (
            "This bundle is a deterministic, non-mutating status report for the source-gated "
            "curation chain. It is not legal advice, not source verification, and not comparable "
            "benchmark evidence."
        ),
        "",
        "## Summary",
        "",
        "| Metric | Value |",
        "|---|---:|",
        f"| Consistency OK | {str(bool(summary['consistency_ok'])).lower()} |",
        f"| Prompt count | {summary['prompt_count']} |",
        f"| Prompts ready for comparable run | {summary['prompts_ready_for_comparable_run']} |",
        f"| Prompts blocked for comparable run | {summary['prompts_blocked_for_comparable_run']} |",
        f"| Verified local-law rows | {summary['verified_local_law_rows']} |",
        f"| Source-object tasks | {summary['source_object_tasks']} |",
        f"| Scope-refinement tasks | {summary['scope_refinement_tasks']} |",
        f"| Source-coverage cells | {summary['source_coverage_cells']} |",
        f"| Source-coverage scope-blocked cells | {summary['source_coverage_scope_blocked_cells']} |",
        f"| Source-coverage pending manifest rows to promote | {summary['source_coverage_pending_manifest_rows_to_promote']} |",
        f"| Source-coverage missing manifest rows to add | {summary['source_coverage_missing_manifest_rows_to_add']} |",
        f"| Source-review sprint rows | {summary['source_review_sprint_rows']} |",
        f"| Scope-resolution sprint rows | {summary['scope_resolution_sprint_rows']} |",
        f"| Source-review sprint deferred scope-blocked rows | {summary['source_review_sprint_deferred_scope_blocked_rows']} |",
        f"| Source-review ledger source rows not started | {summary['source_review_ledger_source_rows_not_started']} |",
        f"| Source-review ledger scope rows not started | {summary['source_review_ledger_scope_rows_not_started']} |",
        f"| Source-review ledger source rows in progress | {summary['source_review_ledger_source_rows_in_progress_not_ready']} |",
        f"| Source-review ledger scope rows in progress | {summary['source_review_ledger_scope_rows_in_progress_not_ready']} |",
        f"| Source rows ready claimed | {summary['source_rows_ready_claimed']} |",
        f"| Source rows accepted for manifest proposal | {summary['source_rows_accepted_for_manifest_proposal']} |",
        f"| Manifest operations ready for manual patch | {summary['manifest_operations_ready_for_manual_patch']} |",
        f"| Ready for comparable run | {str(bool(summary['ready_for_comparable_run'])).lower()} |",
        "",
        "## Consistency Checks",
        "",
        "| Check | OK | Expected | Actual |",
        "|---|---:|---|---|",
    ]
    for check in doc["consistency_checks"]:
        lines.append(
            f"| {_md_cell(check['id'])} "
            f"| {str(bool(check['ok'])).lower()} "
            f"| {_md_cell(check['expected'])} "
            f"| {_md_cell(check['actual'])} |"
        )
    lines.extend([
        "",
        "## Artifact Paths",
        "",
    ])
    for key, path in doc["artifact_paths"].items():
        lines.append(f"- `{_md_cell(key)}`: `{_md_cell(path)}`")
    lines.append("")
    return "\n".join(lines)


def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--domain", default="developing_country_worker_protections")
    ap.add_argument("--out", type=pathlib.Path, default=None)
    ap.add_argument("--md-out", type=pathlib.Path, default=None, help="Markdown report path; defaults to --out with .md suffix")
    ap.add_argument("--no-md", action="store_true", help="write only JSON, not the Markdown bundle report")
    ap.add_argument("--write-components", action="store_true", help="also write each component JSON/Markdown artifact")
    ap.add_argument("--component-dir", type=pathlib.Path, default=OUT_DIR, help="directory for --write-components outputs")
    args = ap.parse_args(argv)

    domain_id = _safe_domain_id(args.domain)
    chain = build_curation_chain(domain_id)
    doc = build_curation_bundle(domain_id, chain=chain)
    if args.write_components:
        doc["artifact_paths"].update(write_component_artifacts(domain_id, chain, output_dir=args.component_dir))
    out_path = args.out or default_out_path(domain_id)
    doc["artifact_paths"]["curation_bundle_json"] = _artifact_path(out_path)
    md_path = None
    if not args.no_md:
        md_path = args.md_out or default_markdown_path(out_path)
        doc["artifact_paths"]["curation_bundle_markdown"] = _artifact_path(md_path)
        md_path.parent.mkdir(parents=True, exist_ok=True)
    out_path.parent.mkdir(parents=True, exist_ok=True)
    out_path.write_text(json.dumps(doc, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
    if md_path is not None:
        md_path.write_text(build_markdown_report(doc) + "\n", encoding="utf-8")
    summary = doc["summary"]
    print(
        f"wrote {out_path}: consistency_ok={str(bool(summary['consistency_ok'])).lower()}; "
        f"{summary['prompts_blocked_for_comparable_run']}/{summary['prompt_count']} prompts blocked; "
        f"ready_for_comparable_run={str(bool(summary['ready_for_comparable_run'])).lower()}"
        + (f"; report {md_path}" if md_path else "")
    )
    return 0 if summary["consistency_ok"] else 1


if __name__ == "__main__":
    raise SystemExit(main())
