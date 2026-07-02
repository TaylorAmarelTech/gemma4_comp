#!/usr/bin/env python3
"""Build a curator sprint packet for the global protections sister project.

The next-actions backlog identifies every known blocker. This command turns the
immediate, human-reviewable work into a compact sprint packet:

1. scope-resolution rows
2. immediate source-review rows
3. regulatory candidate-intake rows

It also keeps blocked-later work visible. The output deliberately avoids prompt
text, source URLs, private cases, and legal claims.

Offline + deterministic. No model, no network, no credits.
"""
from __future__ import annotations

import argparse
import json
import pathlib
import sys
from typing import Any

_ROOT = pathlib.Path(__file__).resolve().parents[1]
_SCRIPTS = pathlib.Path(__file__).resolve().parent
if str(_SCRIPTS) not in sys.path:
    sys.path.insert(0, str(_SCRIPTS))

from artifact_path_policy import handoff_artifact_path  # noqa: E402
import build_global_protections_next_actions as next_actions_builder  # noqa: E402
import build_global_protections_project_plan as project_plan_builder  # noqa: E402
import build_global_protections_readiness_bundle as readiness_builder  # noqa: E402

OUT_DIR = _ROOT / "reports" / "benchmark"
OUT = OUT_DIR / "global_protections_curator_sprint.json"
MD_OUT = OUT_DIR / "global_protections_curator_sprint.md"
DEFAULT_DOMAIN = readiness_builder.DEFAULT_DOMAIN

_SCOPE_REVIEW_FIELDS = [
    "concrete jurisdictions or forums",
    "origin and destination role split",
    "flag, port, buyer, contractor, or regulator role when relevant",
    "public-source trail for each resolved forum",
    "resolution note explaining why the broad label is no longer sufficient",
]
_SOURCE_REVIEW_FIELDS = [
    "source title and authority",
    "stable public link or archive note",
    "publication or access date",
    "source type and language",
    "official or public-interest basis",
    "legal scope note",
    "privacy, license, and reviewer notes",
]
_REGULATORY_REVIEW_FIELDS = [
    "scope decision",
    "proposed domain identifier",
    "approved scope statement",
    "concrete jurisdiction strategy",
    "primary public-interest use case",
    "future artifact paths",
    "privacy, source-path, expert, and registry review gates",
]
_DISALLOWED_TERMS = [
    "Synthetic composite:",
    "prompt_family_sketches",
    "candidate_url",
    "source_url",
    "raw_text",
    "case_text",
    "https://",
    "www.",
]


def _artifact_path(path: pathlib.Path) -> str:
    return handoff_artifact_path(path, root=_ROOT)


def _display_path(path: pathlib.Path) -> str:
    try:
        return path.relative_to(_ROOT).as_posix()
    except ValueError:
        return path.as_posix()


def _check(check_id: str, ok: bool, *, expected: Any, actual: Any) -> dict[str, Any]:
    return {
        "id": check_id,
        "ok": bool(ok),
        "expected": expected,
        "actual": actual,
    }


def component_paths(
    *,
    output_dir: pathlib.Path | None = None,
    domain_id: str = DEFAULT_DOMAIN,
) -> dict[str, str]:
    """Return default artifact paths for the curator sprint chain."""
    base = output_dir or OUT_DIR
    paths = next_actions_builder.component_paths(output_dir=base, domain_id=domain_id)
    paths["global_protections_curator_sprint_json"] = _artifact_path(
        base / "global_protections_curator_sprint.json"
    )
    paths["global_protections_curator_sprint_markdown"] = _artifact_path(
        base / "global_protections_curator_sprint.md"
    )
    return {key: _artifact_path(pathlib.Path(value)) for key, value in paths.items()}


def _actions_by_id(next_actions_doc: dict[str, Any]) -> dict[str, dict[str, Any]]:
    return {
        str(action.get("id")): action
        for action in next_actions_doc.get("actions", [])
        if isinstance(action, dict) and action.get("id")
    }


def _scope_item(row: dict[str, Any], action: dict[str, Any], index: int) -> dict[str, Any]:
    return {
        "sprint_id": f"CURATOR-SCOPE-{index:03d}",
        "backlog_action_id": action.get("id"),
        "scope_task_id": row.get("scope_task_id"),
        "scope": row.get("scope"),
        "category": row.get("category"),
        "blocked_prompt_count": len(row.get("blocked_prompt_ids") or []),
        "related_coverage_cell_count": len(row.get("related_coverage_cell_ids") or []),
        "required_legal_claim_anchor_source_channel_ids": list(
            action.get("required_legal_claim_anchor_source_channel_ids") or []
        ),
        "review_fields": list(_SCOPE_REVIEW_FIELDS),
        "acceptance_checks": [
            "resolved scope names at least one concrete jurisdiction, forum, regulator, flag, or port",
            "origin and destination responsibilities are separated when cross-border responsibility matters",
            "new source-object rows can be created for every resolved jurisdiction/category pair",
            "private worker, complainant, household, and case-level details are not introduced",
            "ready-for-scoring remains false after the scope decision",
        ],
        "blocked_until_done": list(action.get("blocks") or []),
    }


def _source_item(row: dict[str, Any], action: dict[str, Any], index: int) -> dict[str, Any]:
    defaults = row.get("review_packet_defaults") or {}
    return {
        "sprint_id": f"CURATOR-SOURCE-{index:03d}",
        "backlog_action_id": action.get("id"),
        "source_id": row.get("source_id"),
        "source_task_id": row.get("source_task_id"),
        "cell_id": row.get("cell_id"),
        "jurisdiction": row.get("jurisdiction"),
        "category": row.get("category"),
        "coverage_status": row.get("coverage_status"),
        "review_fields": list(_SOURCE_REVIEW_FIELDS),
        "field_count_from_review_packet": len(row.get("fields_to_complete") or []),
        "required_legal_claim_anchor_source_channel_ids": list(
            action.get("required_legal_claim_anchor_source_channel_ids") or []
        ),
        "privacy_review_required": defaults.get("privacy_review_required"),
        "expert_review_required": defaults.get("expert_review_required"),
        "ready_for_manifest_promotion": defaults.get("ready_for_manifest_promotion"),
        "acceptance_checks": [
            "source metadata is public, dated, stable, and reproducible",
            "source scope matches the jurisdiction/category cell",
            "international anchors are not treated as substitutes for verified local law",
            "privacy review rejects names, contact details, addresses, and private case rows",
            "expert review remains required before manifest promotion or scoring",
        ],
        "blocked_until_done": list(action.get("blocks") or []),
    }


def _regulatory_item(row: dict[str, Any], action: dict[str, Any], index: int) -> dict[str, Any]:
    readiness = row.get("readiness") or {}
    gates = row.get("review_gates") or {}
    priority = row.get("expansion_priority") if isinstance(row.get("expansion_priority"), dict) else {}
    return {
        "sprint_id": f"CURATOR-REGULATORY-{index:03d}",
        "backlog_action_id": action.get("id"),
        "pattern_id": row.get("pattern_id"),
        "display_name": row.get("display_name"),
        "expansion_rank": priority.get("rank"),
        "expansion_score": priority.get("score"),
        "expansion_band": priority.get("band"),
        "priority_signal_count": len(priority.get("signals") or []),
        "is_top_candidate": priority.get("rank") == 1,
        "legal_dimension_count": len(row.get("legal_dimensions") or []),
        "source_gate_count": len(row.get("required_source_gates") or []),
        "review_fields": list(_REGULATORY_REVIEW_FIELDS),
        "required_legal_claim_anchor_source_channel_ids": list(
            action.get("required_legal_claim_anchor_source_channel_ids") or []
        ),
        "review_gate_status": {
            "privacy": gates.get("privacy_review_status"),
            "source_path": gates.get("source_path_review_status"),
            "expert": gates.get("expert_review_status"),
            "domain_registry": gates.get("domain_registry_review_status"),
        },
        "readiness": {
            "ready_for_domain_seed": readiness.get("ready_for_domain_seed"),
            "ready_for_prompt_generation": readiness.get("ready_for_prompt_generation"),
            "ready_for_comparable_scoring": readiness.get("ready_for_comparable_scoring"),
        },
        "acceptance_checks": [
            "priority rank is used only for triage and does not approve the domain",
            "scope is approved before any proposed domain seed exists",
            "artifact paths are future paths only and do not create files",
            "privacy, source-path, expert, and registry review gates all pass before seed proposal",
            "prompt generation and comparable scoring remain false",
        ],
        "blocked_until_done": list(action.get("blocks") or []),
    }


def _blocked_later_items(next_actions_doc: dict[str, Any]) -> list[dict[str, Any]]:
    items: list[dict[str, Any]] = []
    for action in next_actions_doc.get("actions", []):
        if not isinstance(action, dict):
            continue
        if action.get("item_type") not in {"deferred_source_review", "source_verified_grounding_layer"}:
            continue
        items.append({
            "backlog_action_id": action.get("id"),
            "lane": action.get("lane"),
            "item_type": action.get("item_type"),
            "status": action.get("status"),
            "reason": action.get("next_step"),
            "required_legal_claim_anchor_source_channel_ids": list(
                action.get("required_legal_claim_anchor_source_channel_ids") or []
            ),
            "blocks": list(action.get("blocks") or []),
        })
    return items


def _execution_phase_summary(
    next_actions_doc: dict[str, Any],
    *,
    sprint_action_ids: set[str],
    blocked_later_action_ids: set[str],
) -> list[dict[str, Any]]:
    """Return phase coverage for the curator sprint without copying raw actions."""
    phases: list[dict[str, Any]] = []
    for phase in next_actions_doc.get("execution_phases", []):
        if not isinstance(phase, dict):
            continue
        phase_action_ids = [str(action_id) for action_id in phase.get("action_ids", [])]
        sprint_ids = [action_id for action_id in phase_action_ids if action_id in sprint_action_ids]
        blocked_ids = [
            action_id for action_id in phase_action_ids if action_id in blocked_later_action_ids
        ]
        phases.append({
            "phase_id": phase.get("id"),
            "order": phase.get("order"),
            "label": phase.get("label"),
            "depends_on_phase_ids": list(phase.get("depends_on_phase_ids") or []),
            "completion_gate": phase.get("completion_gate"),
            "backlog_action_count": len(phase_action_ids),
            "sprint_action_ids": sprint_ids,
            "blocked_later_action_ids": blocked_ids,
            "required_legal_claim_anchor_source_channel_ids": list(
                phase.get("required_legal_claim_anchor_source_channel_ids") or []
            ),
            "readiness_after_phase": dict(phase.get("readiness_after_phase") or {}),
        })
    return phases


def _contains_disallowed_text(doc: dict[str, Any]) -> list[str]:
    encoded = json.dumps(doc, ensure_ascii=False)
    return [term for term in _DISALLOWED_TERMS if term in encoded]


def build_curator_sprint(
    *,
    chain: dict[str, dict[str, Any]] | None = None,
    next_actions_doc: dict[str, Any] | None = None,
    domain_id: str = DEFAULT_DOMAIN,
    project_config_path: pathlib.Path = readiness_builder.project_plan_builder.CONFIG,
    registry_path: pathlib.Path = readiness_builder.project_plan_builder.REGISTRY,
    regulatory_catalog_path: pathlib.Path = readiness_builder.project_plan_builder.REGULATORY_CATALOG,
    component_dir: pathlib.Path | None = None,
) -> dict[str, Any]:
    """Return a privacy-safe curator sprint packet."""
    chain = chain or readiness_builder.build_readiness_chain(
        domain_id=domain_id,
        project_config_path=project_config_path,
        registry_path=registry_path,
        regulatory_catalog_path=regulatory_catalog_path,
        component_dir=component_dir,
    )
    readiness_doc = readiness_builder.build_readiness_bundle(
        chain=chain,
        domain_id=domain_id,
        project_config_path=project_config_path,
        registry_path=registry_path,
        regulatory_catalog_path=regulatory_catalog_path,
        component_dir=component_dir,
    )
    next_actions_doc = next_actions_doc or next_actions_builder.build_next_actions(
        chain=chain,
        readiness_doc=readiness_doc,
        domain_id=domain_id,
        project_config_path=project_config_path,
        registry_path=registry_path,
        regulatory_catalog_path=regulatory_catalog_path,
        component_dir=component_dir,
    )
    actions = _actions_by_id(next_actions_doc)
    domain_sprint = chain["_domain_chain"]["source_review_sprint"]
    regulatory_intake = chain["_regulatory_chain"]["domain_intake_packet"]
    regulatory_meta = regulatory_intake.get("_meta") or {}

    scope_items = [
        _scope_item(row, actions.get(f"GP-SCOPE-{index:03d}", {}), index)
        for index, row in enumerate(domain_sprint.get("scope_resolution_sprint_rows", []), start=1)
        if isinstance(row, dict)
    ]
    source_items = [
        _source_item(row, actions.get(f"GP-SOURCE-{index:03d}", {}), index)
        for index, row in enumerate(domain_sprint.get("source_review_sprint_rows", []), start=1)
        if isinstance(row, dict)
    ]
    regulatory_items = [
        _regulatory_item(row, actions.get(f"GP-REGULATORY-{index:03d}", {}), index)
        for index, row in enumerate(regulatory_intake.get("candidate_domain_intake", []), start=1)
        if isinstance(row, dict)
    ]
    blocked_later = _blocked_later_items(next_actions_doc)
    sprint_action_ids = {
        str(item.get("backlog_action_id"))
        for item in [*scope_items, *source_items, *regulatory_items]
        if item.get("backlog_action_id")
    }
    blocked_later_action_ids = {
        str(item.get("backlog_action_id"))
        for item in blocked_later
        if item.get("backlog_action_id")
    }
    execution_phase_summary = _execution_phase_summary(
        next_actions_doc,
        sprint_action_ids=sprint_action_ids,
        blocked_later_action_ids=blocked_later_action_ids,
    )
    legal_anchor_source_channel_ids = list(
        next_actions_doc["summary"].get("legal_claim_anchor_source_channel_ids") or []
    )
    sprint_items = [*scope_items, *source_items, *regulatory_items]
    ready_flags = {
        "prompt_generation": readiness_doc["summary"]["ready_for_prompt_generation"],
        "training_use": readiness_doc["summary"]["ready_for_training_use"],
        "public_claims": readiness_doc["summary"]["ready_for_public_claims"],
        "worker_facing_use": readiness_doc["summary"]["ready_for_worker_facing_use"],
        "comparable_scoring": readiness_doc["summary"]["ready_for_comparable_scoring"],
    }
    summary = {
        "consistency_ok": False,
        "sprint_item_count": len(scope_items) + len(source_items) + len(regulatory_items),
        "execution_phase_count": len(execution_phase_summary),
        "scope_resolution_items": len(scope_items),
        "source_review_items": len(source_items),
        "regulatory_candidate_intake_items": len(regulatory_items),
        "regulatory_priority_queue_items": regulatory_meta.get("candidate_queue_count", 0),
        "regulatory_top_candidate_id": regulatory_meta.get("top_candidate_id", ""),
        "blocked_later_items": len(blocked_later),
        "legal_claim_anchor_source_channel_count": len(legal_anchor_source_channel_ids),
        "legal_claim_anchor_source_channel_ids": list(legal_anchor_source_channel_ids),
        "sprint_items_preserving_legal_anchor_source_channels": sum(
            1
            for item in sprint_items
            if item.get("required_legal_claim_anchor_source_channel_ids")
            == legal_anchor_source_channel_ids
        ),
        "blocked_later_items_preserving_legal_anchor_source_channels": sum(
            1
            for item in blocked_later
            if item.get("required_legal_claim_anchor_source_channel_ids")
            == legal_anchor_source_channel_ids
        ),
        "execution_phases_preserving_legal_anchor_source_channels": sum(
            1
            for phase in execution_phase_summary
            if phase.get("required_legal_claim_anchor_source_channel_ids")
            == legal_anchor_source_channel_ids
        ),
        "ready_for_prompt_generation": ready_flags["prompt_generation"],
        "ready_for_training_use": ready_flags["training_use"],
        "ready_for_public_claims": ready_flags["public_claims"],
        "ready_for_worker_facing_use": ready_flags["worker_facing_use"],
        "ready_for_comparable_scoring": ready_flags["comparable_scoring"],
        "policy": (
            "This sprint packet is a curator handoff only. It does not verify law, fill review rows, "
            "promote manifests, create domain seeds, generate prompts, train models, enable "
            "worker-facing use, or authorize scores."
        ),
    }
    checks = [
        _check(
            "next_actions_consistency_ok",
            next_actions_doc["summary"]["consistency_ok"] is True,
            expected=True,
            actual=next_actions_doc["summary"]["consistency_ok"],
        ),
        _check(
            "sprint_item_count_matches_immediate_actions",
            summary["sprint_item_count"] == next_actions_doc["summary"]["immediate_action_count"],
            expected=next_actions_doc["summary"]["immediate_action_count"],
            actual=summary["sprint_item_count"],
        ),
        _check(
            "scope_count_matches_backlog",
            summary["scope_resolution_items"] == next_actions_doc["summary"]["scope_resolution_items"],
            expected=next_actions_doc["summary"]["scope_resolution_items"],
            actual=summary["scope_resolution_items"],
        ),
        _check(
            "source_count_matches_backlog",
            summary["source_review_items"] == next_actions_doc["summary"]["source_review_items"],
            expected=next_actions_doc["summary"]["source_review_items"],
            actual=summary["source_review_items"],
        ),
        _check(
            "regulatory_count_matches_backlog",
            summary["regulatory_candidate_intake_items"]
            == next_actions_doc["summary"]["regulatory_candidate_intake_items"],
            expected=next_actions_doc["summary"]["regulatory_candidate_intake_items"],
            actual=summary["regulatory_candidate_intake_items"],
        ),
        _check(
            "regulatory_priority_queue_matches_backlog",
            summary["regulatory_priority_queue_items"]
            == next_actions_doc["summary"]["regulatory_priority_queue_items"],
            expected=next_actions_doc["summary"]["regulatory_priority_queue_items"],
            actual=summary["regulatory_priority_queue_items"],
        ),
        _check(
            "regulatory_top_candidate_first",
            bool(regulatory_items)
            and regulatory_items[0].get("pattern_id") == summary["regulatory_top_candidate_id"]
            and regulatory_items[0].get("is_top_candidate") is True,
            expected=summary["regulatory_top_candidate_id"],
            actual=regulatory_items[0].get("pattern_id") if regulatory_items else None,
        ),
        _check(
            "blocked_later_count_matches_backlog",
            summary["blocked_later_items"] == next_actions_doc["summary"]["blocked_action_count"],
            expected=next_actions_doc["summary"]["blocked_action_count"],
            actual=summary["blocked_later_items"],
        ),
        _check(
            "legal_claim_anchor_source_channels_preserved",
            summary["legal_claim_anchor_source_channel_count"]
            == next_actions_doc["summary"]["legal_claim_anchor_source_channel_count"]
            and summary["legal_claim_anchor_source_channel_ids"]
            == next_actions_doc["summary"]["legal_claim_anchor_source_channel_ids"]
            and summary["sprint_items_preserving_legal_anchor_source_channels"]
            == summary["sprint_item_count"]
            and summary["blocked_later_items_preserving_legal_anchor_source_channels"]
            == summary["blocked_later_items"]
            and summary["execution_phases_preserving_legal_anchor_source_channels"]
            == summary["execution_phase_count"],
            expected={
                "legal_claim_anchor_source_channel_count": next_actions_doc["summary"][
                    "legal_claim_anchor_source_channel_count"
                ],
                "legal_claim_anchor_source_channel_ids": next_actions_doc["summary"][
                    "legal_claim_anchor_source_channel_ids"
                ],
                "sprint_item_count": summary["sprint_item_count"],
                "blocked_later_items": summary["blocked_later_items"],
                "execution_phase_count": summary["execution_phase_count"],
            },
            actual={
                "legal_claim_anchor_source_channel_count": summary[
                    "legal_claim_anchor_source_channel_count"
                ],
                "legal_claim_anchor_source_channel_ids": summary[
                    "legal_claim_anchor_source_channel_ids"
                ],
                "sprint_item_count": summary[
                    "sprint_items_preserving_legal_anchor_source_channels"
                ],
                "blocked_later_items": summary[
                    "blocked_later_items_preserving_legal_anchor_source_channels"
                ],
                "execution_phase_count": summary[
                    "execution_phases_preserving_legal_anchor_source_channels"
                ],
            },
        ),
        _check(
            "all_public_and_scoring_flags_blocked",
            not any(ready_flags.values()),
            expected=False,
            actual=ready_flags,
        ),
        _check(
            "execution_phase_summary_matches_backlog",
            sorted(
                action_id
                for phase in execution_phase_summary
                for action_id in [
                    *phase["sprint_action_ids"],
                    *phase["blocked_later_action_ids"],
                ]
            )
            == sorted([*sprint_action_ids, *blocked_later_action_ids])
            == sorted(
                action_id
                for phase in next_actions_doc.get("execution_phases", [])
                for action_id in phase.get("action_ids", [])
            ),
            expected=next_actions_doc["summary"].get("action_count"),
            actual=sum(
                len(phase["sprint_action_ids"]) + len(phase["blocked_later_action_ids"])
                for phase in execution_phase_summary
            ),
        ),
        _check(
            "execution_phase_readiness_stays_blocked",
            not any(
                value is True
                for phase in execution_phase_summary
                for value in phase["readiness_after_phase"].values()
            ),
            expected=False,
            actual=[
                phase["phase_id"]
                for phase in execution_phase_summary
                if any(value is True for value in phase["readiness_after_phase"].values())
            ],
        ),
    ]
    doc = {
        "_meta": {
            "schema_version": "global_protections_curator_sprint.v1",
            "project_config": _display_path(project_config_path),
            "domain": domain_id,
            "registry_path": _display_path(registry_path),
            "regulatory_catalog_path": _display_path(regulatory_catalog_path),
            "status": (
                "curator sprint packet; not legal advice, not source verification, not prompt "
                "generation, not training data, and not comparable benchmark evidence"
            ),
        },
        "summary": summary,
        "scope_resolution_items": scope_items,
        "source_review_items": source_items,
        "regulatory_candidate_intake_items": regulatory_items,
        "blocked_later_items": blocked_later,
        "execution_phase_summary": execution_phase_summary,
        "exit_gates": [
            "run source-review validation after curator rows are filled",
            "build a grounding-manifest proposal only from validation-accepted rows",
            "rerun the readiness bundle and next-actions backlog after any curated packet changes",
            "keep prompt generation, worker-facing use, public claims, and comparable scoring false",
        ],
        "checks": checks,
        "artifact_paths": component_paths(output_dir=component_dir, domain_id=domain_id),
    }
    disallowed = _contains_disallowed_text(doc)
    scan = project_plan_builder._scan_privacy(doc)
    checks.extend([
        _check("sprint_contains_no_disallowed_text", not disallowed, expected=[], actual=disallowed),
        _check("privacy_scan_ok", scan.get("ok") is True, expected=True, actual=scan.get("ok")),
    ])
    doc["summary"]["consistency_ok"] = all(check["ok"] for check in checks)
    return doc


def _md_cell(value: Any) -> str:
    text = str(value if value is not None else "")
    return text.replace("|", "\\|").replace("\n", " ").strip()


def build_markdown_report(doc: dict[str, Any]) -> str:
    """Render a compact Markdown curator sprint packet."""
    summary = doc["summary"]
    lines: list[str] = [
        "# Global Protections Curator Sprint",
        "",
        (
            "This sprint packet turns the source-gated backlog into immediate curator work. "
            "It is not legal advice, not source verification, not prompt generation, and not "
            "comparable benchmark evidence."
        ),
        "",
        "## Summary",
        "",
        "| Metric | Value |",
        "|---|---:|",
        f"| Consistency OK | {str(bool(summary['consistency_ok'])).lower()} |",
        f"| Sprint items | {summary['sprint_item_count']} |",
        f"| Execution phases | {summary['execution_phase_count']} |",
        f"| Scope-resolution items | {summary['scope_resolution_items']} |",
        f"| Source-review items | {summary['source_review_items']} |",
        f"| Regulatory candidate intake items | {summary['regulatory_candidate_intake_items']} |",
        f"| Regulatory priority queue items | {summary['regulatory_priority_queue_items']} |",
        f"| Regulatory top candidate | {_md_cell(summary['regulatory_top_candidate_id'])} |",
        f"| Blocked-later items | {summary['blocked_later_items']} |",
        (
            "| Legal-claim anchor source channels "
            f"| {summary['legal_claim_anchor_source_channel_count']} |"
        ),
        (
            "| Sprint items preserving legal-anchor source channels "
            f"| {summary['sprint_items_preserving_legal_anchor_source_channels']} |"
        ),
        (
            "| Blocked-later items preserving legal-anchor source channels "
            f"| {summary['blocked_later_items_preserving_legal_anchor_source_channels']} |"
        ),
        (
            "| Execution phases preserving legal-anchor source channels "
            f"| {summary['execution_phases_preserving_legal_anchor_source_channels']} |"
        ),
        f"| Ready for prompt generation | {str(bool(summary['ready_for_prompt_generation'])).lower()} |",
        f"| Ready for worker-facing use | {str(bool(summary['ready_for_worker_facing_use'])).lower()} |",
        f"| Ready for comparable scoring | {str(bool(summary['ready_for_comparable_scoring'])).lower()} |",
        "",
        "## Scope Resolution",
        "",
        "| Sprint ID | Scope | Category | Prompts blocked | Related cells |",
        "|---|---|---|---:|---:|",
    ]
    for item in doc["scope_resolution_items"]:
        lines.append(
            f"| `{_md_cell(item['sprint_id'])}` "
            f"| {_md_cell(item['scope'])} "
            f"| {_md_cell(item['category'])} "
            f"| {item['blocked_prompt_count']} "
            f"| {item['related_coverage_cell_count']} |"
        )
    lines.extend([
        "",
        "## Source Review",
        "",
        "| Sprint ID | Source ID | Cell | Coverage status | Fields |",
        "|---|---|---|---|---:|",
    ])
    for item in doc["source_review_items"]:
        lines.append(
            f"| `{_md_cell(item['sprint_id'])}` "
            f"| `{_md_cell(item['source_id'])}` "
            f"| `{_md_cell(item['cell_id'])}` "
            f"| {_md_cell(item['coverage_status'])} "
            f"| {item['field_count_from_review_packet']} |"
        )
    lines.extend([
        "",
        "## Regulatory Candidate Intake",
        "",
        "| Sprint ID | Pattern | Rank | Band | Legal dimensions | Source gates |",
        "|---|---|---:|---|---:|---:|",
    ])
    for item in doc["regulatory_candidate_intake_items"]:
        rank = item.get("expansion_rank") if item.get("expansion_rank") is not None else "n/a"
        lines.append(
            f"| `{_md_cell(item['sprint_id'])}` "
            f"| `{_md_cell(item['pattern_id'])}` "
            f"| {rank} "
            f"| {_md_cell(item.get('expansion_band'))} "
            f"| {item['legal_dimension_count']} "
            f"| {item['source_gate_count']} |"
        )
    lines.extend([
        "",
        "## Execution Phase Summary",
        "",
        "| Order | Phase | Sprint actions | Blocked later | Depends on |",
        "|---:|---|---:|---:|---|",
    ])
    for phase in doc["execution_phase_summary"]:
        depends = ", ".join(phase["depends_on_phase_ids"]) or "none"
        lines.append(
            f"| {phase['order']} "
            f"| `{_md_cell(phase['phase_id'])}` "
            f"| {len(phase['sprint_action_ids'])} "
            f"| {len(phase['blocked_later_action_ids'])} "
            f"| {_md_cell(depends)} |"
        )
    lines.extend([
        "",
        "## Blocked Later",
        "",
        "| Backlog ID | Type | Status | Reason |",
        "|---|---|---|---|",
    ])
    for item in doc["blocked_later_items"]:
        lines.append(
            f"| `{_md_cell(item['backlog_action_id'])}` "
            f"| `{_md_cell(item['item_type'])}` "
            f"| {_md_cell(item['status'])} "
            f"| {_md_cell(item['reason'])} |"
        )
    lines.extend([
        "",
        "## Exit Gates",
        "",
    ])
    lines.extend(f"- {_md_cell(gate)}" for gate in doc["exit_gates"])
    lines.extend([
        "",
        "## Checks",
        "",
        "| Check | OK | Expected | Actual |",
        "|---|---:|---|---|",
    ])
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
        summary["policy"],
        "",
    ])
    return "\n".join(lines)


def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--domain", default=DEFAULT_DOMAIN)
    ap.add_argument("--project-config", type=pathlib.Path, default=readiness_builder.project_plan_builder.CONFIG)
    ap.add_argument("--registry", type=pathlib.Path, default=readiness_builder.project_plan_builder.REGISTRY)
    ap.add_argument("--regulatory-catalog", type=pathlib.Path, default=readiness_builder.project_plan_builder.REGULATORY_CATALOG)
    ap.add_argument("--out", type=pathlib.Path, default=OUT)
    ap.add_argument("--md-out", type=pathlib.Path, default=MD_OUT)
    ap.add_argument("--no-md", action="store_true", help="write only JSON, not the Markdown sprint packet")
    ap.add_argument(
        "--write-next-actions",
        action="store_true",
        help="also write the upstream next-actions backlog artifacts",
    )
    ap.add_argument("--component-dir", type=pathlib.Path, default=OUT_DIR)
    args = ap.parse_args(argv)

    chain = readiness_builder.build_readiness_chain(
        domain_id=args.domain,
        project_config_path=args.project_config,
        registry_path=args.registry,
        regulatory_catalog_path=args.regulatory_catalog,
        component_dir=args.component_dir,
    )
    readiness_doc = readiness_builder.build_readiness_bundle(
        chain=chain,
        domain_id=args.domain,
        project_config_path=args.project_config,
        registry_path=args.registry,
        regulatory_catalog_path=args.regulatory_catalog,
        component_dir=args.component_dir,
    )
    next_actions_doc = next_actions_builder.build_next_actions(
        chain=chain,
        readiness_doc=readiness_doc,
        domain_id=args.domain,
        project_config_path=args.project_config,
        registry_path=args.registry,
        regulatory_catalog_path=args.regulatory_catalog,
        component_dir=args.component_dir,
    )
    doc = build_curator_sprint(
        chain=chain,
        next_actions_doc=next_actions_doc,
        domain_id=args.domain,
        project_config_path=args.project_config,
        registry_path=args.registry,
        regulatory_catalog_path=args.regulatory_catalog,
        component_dir=args.component_dir,
    )
    if args.write_next_actions:
        path_doc = next_actions_doc
        next_json = args.component_dir / "global_protections_next_actions.json"
        next_md = args.component_dir / "global_protections_next_actions.md"
        next_json.parent.mkdir(parents=True, exist_ok=True)
        next_json.write_text(json.dumps(path_doc, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
        next_md.write_text(next_actions_builder.build_markdown_report(path_doc) + "\n", encoding="utf-8")
        doc["artifact_paths"]["global_protections_next_actions_json"] = _artifact_path(next_json)
        doc["artifact_paths"]["global_protections_next_actions_markdown"] = _artifact_path(next_md)

    args.out.parent.mkdir(parents=True, exist_ok=True)
    args.out.write_text(json.dumps(doc, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
    md_path = None
    if not args.no_md:
        md_path = args.md_out
        md_path.parent.mkdir(parents=True, exist_ok=True)
        md_path.write_text(build_markdown_report(doc) + "\n", encoding="utf-8")
    summary = doc["summary"]
    print(
        "[global-protections-curator-sprint] "
        f"consistency_ok={str(bool(summary['consistency_ok'])).lower()}; "
        f"{summary['sprint_item_count']} sprint items; "
        f"{summary['blocked_later_items']} blocked later; "
        f"ready_for_comparable_scoring={str(bool(summary['ready_for_comparable_scoring'])).lower()} -> {args.out}"
        + (f"; report {md_path}" if md_path else "")
    )
    return 0 if summary["consistency_ok"] else 1


if __name__ == "__main__":
    raise SystemExit(main())
