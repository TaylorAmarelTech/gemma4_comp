#!/usr/bin/env python3
"""Build a next-actions backlog for the global protections sister project.

This command composes the readiness bundle and lower-level curation packets into
an operator worklist. It keeps the backlog compact and privacy-safe: no prompt
text, source URLs, private cases, or legal claims are copied into the output.

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
import build_global_protections_project_plan as project_plan_builder  # noqa: E402
import build_global_protections_readiness_bundle as readiness_builder  # noqa: E402
import build_global_protections_source_channel_matrix as source_matrix_builder  # noqa: E402

OUT_DIR = _ROOT / "reports" / "benchmark"
OUT = OUT_DIR / "global_protections_next_actions.json"
MD_OUT = OUT_DIR / "global_protections_next_actions.md"
DEFAULT_DOMAIN = readiness_builder.DEFAULT_DOMAIN


def _display_path(path: pathlib.Path) -> str:
    try:
        return path.relative_to(_ROOT).as_posix()
    except ValueError:
        return path.as_posix()


def _artifact_path(path: pathlib.Path) -> str:
    return handoff_artifact_path(path, root=_ROOT)


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
    """Return default artifact paths for the next-actions chain."""
    base = output_dir or OUT_DIR
    paths = readiness_builder.component_paths(output_dir=base, domain_id=domain_id)
    paths = {key: _artifact_path(pathlib.Path(value)) for key, value in paths.items()}
    paths["global_protections_next_actions_json"] = _artifact_path(
        base / "global_protections_next_actions.json"
    )
    paths["global_protections_next_actions_markdown"] = _artifact_path(
        base / "global_protections_next_actions.md"
    )
    return paths


def _scope_action(row: dict[str, Any], index: int) -> dict[str, Any]:
    return {
        "id": f"GP-SCOPE-{index:03d}",
        "priority": 10,
        "lane": "worker_protection_source_curation",
        "item_type": "scope_resolution",
        "status": "not_started",
        "source_task_id": row.get("scope_task_id"),
        "scope": row.get("scope"),
        "category": row.get("category"),
        "blocked_prompt_count": len(row.get("blocked_prompt_ids") or []),
        "related_coverage_cell_count": len(row.get("related_coverage_cell_ids") or []),
        "required_output": "resolved concrete jurisdiction, forum, regulator, flag, port, or corridor scope",
        "next_step": "resolve broad labels before promoting local-law source rows",
        "blocks": [
            "source_row_promotion",
            "worker_protection_comparable_scoring",
        ],
    }


def _source_action(row: dict[str, Any], index: int) -> dict[str, Any]:
    defaults = row.get("review_packet_defaults") or {}
    return {
        "id": f"GP-SOURCE-{index:03d}",
        "priority": 20,
        "lane": "worker_protection_source_curation",
        "item_type": "source_review",
        "status": "not_started",
        "source_id": row.get("source_id"),
        "source_task_id": row.get("source_task_id"),
        "cell_id": row.get("cell_id"),
        "jurisdiction": row.get("jurisdiction"),
        "category": row.get("category"),
        "coverage_status": row.get("coverage_status"),
        "fields_to_complete_count": len(row.get("fields_to_complete") or []),
        "privacy_review_required": defaults.get("privacy_review_required"),
        "expert_review_required": defaults.get("expert_review_required"),
        "ready_for_manifest_promotion": defaults.get("ready_for_manifest_promotion"),
        "required_output": "curator-filled source-review packet row with dated public-source metadata",
        "next_step": row.get("next_step"),
        "blocks": [
            "manifest_promotion",
            "worker_protection_comparable_scoring",
        ],
    }


def _deferred_action(row: dict[str, Any], index: int) -> dict[str, Any]:
    return {
        "id": f"GP-DEFERRED-SOURCE-{index:03d}",
        "priority": 30,
        "lane": "worker_protection_source_curation",
        "item_type": "deferred_source_review",
        "status": "blocked_by_scope_resolution",
        "source_id": row.get("source_id"),
        "cell_id": row.get("cell_id"),
        "jurisdiction": row.get("jurisdiction"),
        "category": row.get("category"),
        "related_scope_task_count": len(row.get("related_scope_task_ids") or []),
        "unresolved_scope_count": len(row.get("related_unresolved_scopes") or []),
        "blocked_prompt_count": len(row.get("blocked_prompt_ids") or []),
        "required_output": "scope resolution first, then source-review packet row",
        "next_step": row.get("defer_reason"),
        "blocks": [
            "source_row_promotion",
            "worker_protection_comparable_scoring",
        ],
    }


def _regulatory_action(row: dict[str, Any], index: int) -> dict[str, Any]:
    readiness = row.get("readiness") or {}
    curator_scope = row.get("curator_scope") or {}
    priority = row.get("expansion_priority") if isinstance(row.get("expansion_priority"), dict) else {}
    rank = priority.get("rank")
    rank_value = rank if isinstance(rank, int) and rank > 0 else index
    return {
        "id": f"GP-REGULATORY-{index:03d}",
        "priority": 40 + rank_value,
        "lane": "regulatory_candidate_intake",
        "item_type": "candidate_domain_intake",
        "status": curator_scope.get("scope_decision") or "needs_review",
        "pattern_id": row.get("pattern_id"),
        "display_name": row.get("display_name"),
        "expansion_rank": priority.get("rank"),
        "expansion_score": priority.get("score"),
        "expansion_band": priority.get("band"),
        "priority_signal_count": len(priority.get("signals") or []),
        "is_top_candidate": priority.get("rank") == 1,
        "legal_dimension_count": len(row.get("legal_dimensions") or []),
        "source_gate_count": len(row.get("required_source_gates") or []),
        "ready_for_domain_seed": readiness.get("ready_for_domain_seed"),
        "ready_for_prompt_generation": readiness.get("ready_for_prompt_generation"),
        "ready_for_comparable_scoring": readiness.get("ready_for_comparable_scoring"),
        "required_output": "curator-approved scope and artifact paths before any domain seed proposal",
        "next_step": "decide whether the candidate should become a propose-only benchmark domain seed",
        "blocks": [
            "domain_seed_file_creation",
            "prompt_generation",
            "comparable_scoring",
        ],
    }


def _grounding_layer_action(readiness_doc: dict[str, Any]) -> dict[str, Any]:
    summary = readiness_doc["summary"]
    return {
        "id": "GP-GROUNDING-LAYER-001",
        "priority": 50,
        "lane": "runner_grounding_layer",
        "item_type": "source_verified_grounding_layer",
        "status": "blocked_by_source_and_expert_review",
        "worker_verified_local_law_rows": summary["worker_verified_local_law_rows"],
        "worker_prompts_blocked_for_comparable_run": summary["worker_prompts_blocked_for_comparable_run"],
        "regulatory_seed_scaffold_operations": summary["regulatory_seed_scaffold_operations"],
        "required_output": "source-verified RAG/tool grounding layer for scored jurisdiction/category cells",
        "next_step": "implement only after source coverage, scope resolution, privacy review, and expert review pass",
        "blocks": [
            "worker_facing_use",
            "public_claims",
            "comparable_scoring",
            "leaderboard_claims",
        ],
    }


def _build_actions(chain: dict[str, dict[str, Any]], readiness_doc: dict[str, Any]) -> list[dict[str, Any]]:
    domain_sprint = chain["_domain_chain"]["source_review_sprint"]
    regulatory_intake = chain["_regulatory_chain"]["domain_intake_packet"]
    actions: list[dict[str, Any]] = []
    actions.extend(
        _scope_action(row, index)
        for index, row in enumerate(domain_sprint.get("scope_resolution_sprint_rows", []), start=1)
        if isinstance(row, dict)
    )
    actions.extend(
        _source_action(row, index)
        for index, row in enumerate(domain_sprint.get("source_review_sprint_rows", []), start=1)
        if isinstance(row, dict)
    )
    actions.extend(
        _deferred_action(row, index)
        for index, row in enumerate(domain_sprint.get("deferred_scope_blocked_source_rows", []), start=1)
        if isinstance(row, dict)
    )
    actions.extend(
        _regulatory_action(row, index)
        for index, row in enumerate(regulatory_intake.get("candidate_domain_intake", []), start=1)
        if isinstance(row, dict)
    )
    actions.append(_grounding_layer_action(readiness_doc))
    actions.sort(key=lambda item: (item["priority"], item["id"]))
    return actions


def _apply_legal_anchor_source_channels(
    rows: list[dict[str, Any]],
    legal_anchor_source_channel_ids: list[str],
) -> None:
    for row in rows:
        row["required_legal_claim_anchor_source_channel_ids"] = list(
            legal_anchor_source_channel_ids
        )


def _execution_phases(actions: list[dict[str, Any]]) -> list[dict[str, Any]]:
    """Return a compact execution sequence derived from the action backlog."""
    phase_specs = [
        {
            "id": "phase_01_scope_resolution",
            "order": 1,
            "label": "Resolve broad scopes",
            "action_types": ["scope_resolution"],
            "depends_on_phase_ids": [],
            "completion_gate": "each broad label has a concrete jurisdiction, forum, regulator, flag, port, or corridor decision",
        },
        {
            "id": "phase_02_source_review",
            "order": 2,
            "label": "Review immediate public-source rows",
            "action_types": ["source_review"],
            "depends_on_phase_ids": ["phase_01_scope_resolution"],
            "completion_gate": "source-review packet rows have dated public metadata, privacy review, and expert-review status",
        },
        {
            "id": "phase_03_regulatory_intake",
            "order": 3,
            "label": "Triage regulatory candidate domains",
            "action_types": ["candidate_domain_intake"],
            "depends_on_phase_ids": [],
            "completion_gate": "candidate scope, proposed domain ID, artifact paths, and review gates are curator-approved",
        },
        {
            "id": "phase_04_deferred_source_review",
            "order": 4,
            "label": "Revisit scope-blocked source rows",
            "action_types": ["deferred_source_review"],
            "depends_on_phase_ids": ["phase_01_scope_resolution"],
            "completion_gate": "deferred rows are converted into source-review rows only after scope blockers are resolved",
        },
        {
            "id": "phase_05_grounding_layer",
            "order": 5,
            "label": "Implement source-verified grounding layer",
            "action_types": ["source_verified_grounding_layer"],
            "depends_on_phase_ids": [
                "phase_02_source_review",
                "phase_03_regulatory_intake",
                "phase_04_deferred_source_review",
            ],
            "completion_gate": "source-verified RAG/tool grounding exists for reviewed jurisdiction/category cells",
        },
    ]
    phases: list[dict[str, Any]] = []
    for spec in phase_specs:
        phase_actions = [
            action
            for action in actions
            if action.get("item_type") in spec["action_types"]
        ]
        phases.append({
            "id": spec["id"],
            "order": spec["order"],
            "label": spec["label"],
            "action_types": list(spec["action_types"]),
            "action_count": len(phase_actions),
            "action_ids": [str(action.get("id")) for action in phase_actions],
            "depends_on_phase_ids": list(spec["depends_on_phase_ids"]),
            "completion_gate": spec["completion_gate"],
            "readiness_after_phase": {
                "ready_for_prompt_generation": False,
                "ready_for_training_use": False,
                "ready_for_public_claims": False,
                "ready_for_worker_facing_use": False,
                "ready_for_comparable_scoring": False,
            },
        })
    return phases


def _counts_by(actions: list[dict[str, Any]], key: str) -> dict[str, int]:
    counts: dict[str, int] = {}
    for action in actions:
        value = str(action.get(key) or "unknown")
        counts[value] = counts.get(value, 0) + 1
    return {value: counts[value] for value in sorted(counts)}


def _contains_disallowed_text(doc: dict[str, Any]) -> list[str]:
    encoded = json.dumps(doc, ensure_ascii=False)
    disallowed = [
        "Synthetic composite:",
        "prompt_family_sketches",
        "candidate_url",
        "source_url",
        "raw_text",
        "case_text",
        "phone",
        "email",
    ]
    return [term for term in disallowed if term in encoded]


def build_next_actions(
    *,
    chain: dict[str, dict[str, Any]] | None = None,
    readiness_doc: dict[str, Any] | None = None,
    domain_id: str = DEFAULT_DOMAIN,
    project_config_path: pathlib.Path = project_plan_builder.CONFIG,
    registry_path: pathlib.Path = project_plan_builder.REGISTRY,
    regulatory_catalog_path: pathlib.Path = project_plan_builder.REGULATORY_CATALOG,
    component_dir: pathlib.Path | None = None,
) -> dict[str, Any]:
    """Return a compact next-actions backlog for the sister-project stack."""
    chain = chain or readiness_builder.build_readiness_chain(
        domain_id=domain_id,
        project_config_path=project_config_path,
        registry_path=registry_path,
        regulatory_catalog_path=regulatory_catalog_path,
        component_dir=component_dir,
    )
    readiness_doc = readiness_doc or readiness_builder.build_readiness_bundle(
        chain=chain,
        domain_id=domain_id,
        project_config_path=project_config_path,
        registry_path=registry_path,
        regulatory_catalog_path=regulatory_catalog_path,
        component_dir=component_dir,
    )
    domain_sprint = chain["_domain_chain"]["source_review_sprint"]
    regulatory_intake = chain["_regulatory_chain"]["domain_intake_packet"]
    regulatory_meta = regulatory_intake.get("_meta") or {}
    legal_anchor_source_channel_ids = (
        source_matrix_builder.legal_claim_anchor_source_channel_ids()
    )
    actions = _build_actions(chain, readiness_doc)
    _apply_legal_anchor_source_channels(actions, legal_anchor_source_channel_ids)
    execution_phases = _execution_phases(actions)
    _apply_legal_anchor_source_channels(execution_phases, legal_anchor_source_channel_ids)
    regulatory_actions = [
        item for item in actions if item.get("item_type") == "candidate_domain_intake"
    ]
    ready_flags = {
        "prompt_generation": readiness_doc["summary"]["ready_for_prompt_generation"],
        "training_use": readiness_doc["summary"]["ready_for_training_use"],
        "public_claims": readiness_doc["summary"]["ready_for_public_claims"],
        "worker_facing_use": readiness_doc["summary"]["ready_for_worker_facing_use"],
        "comparable_scoring": readiness_doc["summary"]["ready_for_comparable_scoring"],
    }
    summary = {
        "consistency_ok": False,
        "action_count": len(actions),
        "execution_phase_count": len(execution_phases),
        "immediate_action_count": sum(1 for item in actions if item["status"] in {"not_started", "needs_review"}),
        "blocked_action_count": sum(1 for item in actions if str(item["status"]).startswith("blocked")),
        "scope_resolution_items": sum(1 for item in actions if item["item_type"] == "scope_resolution"),
        "source_review_items": sum(1 for item in actions if item["item_type"] == "source_review"),
        "deferred_source_review_items": sum(1 for item in actions if item["item_type"] == "deferred_source_review"),
        "regulatory_candidate_intake_items": sum(
            1 for item in actions if item["item_type"] == "candidate_domain_intake"
        ),
        "regulatory_priority_queue_items": regulatory_meta.get("candidate_queue_count", 0),
        "regulatory_top_candidate_id": regulatory_meta.get("top_candidate_id", ""),
        "grounding_layer_items": sum(
            1 for item in actions if item["item_type"] == "source_verified_grounding_layer"
        ),
        "legal_claim_anchor_source_channel_count": len(legal_anchor_source_channel_ids),
        "legal_claim_anchor_source_channel_ids": list(legal_anchor_source_channel_ids),
        "actions_preserving_legal_anchor_source_channels": sum(
            1
            for item in actions
            if item.get("required_legal_claim_anchor_source_channel_ids")
            == legal_anchor_source_channel_ids
        ),
        "execution_phases_preserving_legal_anchor_source_channels": sum(
            1
            for phase in execution_phases
            if phase.get("required_legal_claim_anchor_source_channel_ids")
            == legal_anchor_source_channel_ids
        ),
        "ready_for_prompt_generation": ready_flags["prompt_generation"],
        "ready_for_training_use": ready_flags["training_use"],
        "ready_for_public_claims": ready_flags["public_claims"],
        "ready_for_worker_facing_use": ready_flags["worker_facing_use"],
        "ready_for_comparable_scoring": ready_flags["comparable_scoring"],
        "policy": (
            "This backlog is an operator worklist only. It does not verify law, fill source rows, "
            "promote manifests, create prompts, train models, enable worker-facing use, or authorize scores."
        ),
    }
    checks = [
        _check(
            "readiness_bundle_consistency_ok",
            readiness_doc["summary"]["consistency_ok"] is True,
            expected=True,
            actual=readiness_doc["summary"]["consistency_ok"],
        ),
        _check(
            "scope_resolution_count_matches_sprint",
            summary["scope_resolution_items"] == domain_sprint["summary"]["scope_resolution_sprint_rows"],
            expected=domain_sprint["summary"]["scope_resolution_sprint_rows"],
            actual=summary["scope_resolution_items"],
        ),
        _check(
            "source_review_count_matches_sprint",
            summary["source_review_items"] == domain_sprint["summary"]["source_review_sprint_rows"],
            expected=domain_sprint["summary"]["source_review_sprint_rows"],
            actual=summary["source_review_items"],
        ),
        _check(
            "deferred_source_count_matches_sprint",
            summary["deferred_source_review_items"]
            == domain_sprint["summary"]["deferred_scope_blocked_source_rows"],
            expected=domain_sprint["summary"]["deferred_scope_blocked_source_rows"],
            actual=summary["deferred_source_review_items"],
        ),
        _check(
            "regulatory_candidate_count_matches_intake",
            summary["regulatory_candidate_intake_items"]
            == regulatory_intake["_meta"]["candidate_count"],
            expected=regulatory_intake["_meta"]["candidate_count"],
            actual=summary["regulatory_candidate_intake_items"],
        ),
        _check(
            "regulatory_priority_queue_matches_intake",
            summary["regulatory_priority_queue_items"] == regulatory_intake["_meta"]["candidate_queue_count"],
            expected=regulatory_intake["_meta"]["candidate_queue_count"],
            actual=summary["regulatory_priority_queue_items"],
        ),
        _check(
            "regulatory_top_candidate_first",
            bool(regulatory_actions)
            and regulatory_actions[0].get("pattern_id") == regulatory_intake["_meta"].get("top_candidate_id")
            and regulatory_actions[0].get("is_top_candidate") is True,
            expected=regulatory_intake["_meta"].get("top_candidate_id"),
            actual=regulatory_actions[0].get("pattern_id") if regulatory_actions else None,
        ),
        _check(
            "all_public_and_scoring_flags_blocked",
            not any(ready_flags.values()),
            expected=False,
            actual=ready_flags,
        ),
        _check(
            "execution_phases_cover_actions",
            sorted(
                action_id
                for phase in execution_phases
                for action_id in phase["action_ids"]
            ) == sorted(str(action["id"]) for action in actions),
            expected=summary["action_count"],
            actual=sum(len(phase["action_ids"]) for phase in execution_phases),
        ),
        _check(
            "execution_phase_readiness_stays_blocked",
            not any(
                value is True
                for phase in execution_phases
                for value in phase["readiness_after_phase"].values()
            ),
            expected=False,
            actual=[
                phase["id"]
                for phase in execution_phases
                if any(value is True for value in phase["readiness_after_phase"].values())
            ],
        ),
        _check(
            "legal_claim_anchor_source_channels_preserved",
            summary["actions_preserving_legal_anchor_source_channels"] == len(actions)
            and summary["execution_phases_preserving_legal_anchor_source_channels"]
            == len(execution_phases),
            expected={
                "legal_claim_anchor_source_channel_ids": legal_anchor_source_channel_ids,
                "action_count": len(actions),
                "execution_phase_count": len(execution_phases),
            },
            actual={
                "legal_claim_anchor_source_channel_ids": summary[
                    "legal_claim_anchor_source_channel_ids"
                ],
                "action_count": summary["actions_preserving_legal_anchor_source_channels"],
                "execution_phase_count": summary[
                    "execution_phases_preserving_legal_anchor_source_channels"
                ],
            },
        ),
    ]
    doc = {
        "_meta": {
            "schema_version": "global_protections_next_actions.v1",
            "project_config": _display_path(project_config_path),
            "domain": domain_id,
            "registry_path": _display_path(registry_path),
            "regulatory_catalog_path": _display_path(regulatory_catalog_path),
            "status": (
                "next-actions backlog; not legal advice, not source verification, not prompt generation, "
                "not training data, and not comparable benchmark evidence"
            ),
        },
        "summary": summary,
        "counts_by_lane": _counts_by(actions, "lane"),
        "counts_by_status": _counts_by(actions, "status"),
        "execution_phases": execution_phases,
        "actions": actions,
        "checks": checks,
        "artifact_paths": component_paths(output_dir=component_dir, domain_id=domain_id),
    }
    disallowed = _contains_disallowed_text(doc)
    checks.extend([
        _check(
            "backlog_contains_no_disallowed_text",
            not disallowed,
            expected=[],
            actual=disallowed,
        ),
        _check(
            "privacy_scan_ok",
            project_plan_builder._scan_privacy(doc).get("ok") is True,
            expected=True,
            actual=project_plan_builder._scan_privacy(doc).get("ok"),
        ),
    ])
    doc["summary"]["consistency_ok"] = all(check["ok"] for check in checks)
    return doc


def _md_cell(value: Any) -> str:
    text = str(value if value is not None else "")
    return text.replace("|", "\\|").replace("\n", " ").strip()


def build_markdown_report(doc: dict[str, Any]) -> str:
    """Render a compact Markdown next-actions backlog."""
    summary = doc["summary"]
    lines: list[str] = [
        "# Global Protections Next Actions",
        "",
        (
            "This backlog is an operator worklist derived from the source-gated readiness stack. "
            "It is not legal advice, not source verification, not prompt generation, and not "
            "comparable benchmark evidence."
        ),
        "",
        "## Summary",
        "",
        "| Metric | Value |",
        "|---|---:|",
        f"| Consistency OK | {str(bool(summary['consistency_ok'])).lower()} |",
        f"| Actions | {summary['action_count']} |",
        f"| Execution phases | {summary['execution_phase_count']} |",
        f"| Immediate actions | {summary['immediate_action_count']} |",
        f"| Blocked actions | {summary['blocked_action_count']} |",
        f"| Scope-resolution items | {summary['scope_resolution_items']} |",
        f"| Source-review items | {summary['source_review_items']} |",
        f"| Deferred source-review items | {summary['deferred_source_review_items']} |",
        f"| Regulatory candidate intake items | {summary['regulatory_candidate_intake_items']} |",
        f"| Regulatory priority queue items | {summary['regulatory_priority_queue_items']} |",
        f"| Regulatory top candidate | {_md_cell(summary['regulatory_top_candidate_id'])} |",
        f"| Grounding-layer items | {summary['grounding_layer_items']} |",
        f"| Legal-claim anchor source channels | {summary['legal_claim_anchor_source_channel_count']} |",
        (
            "| Actions preserving legal-anchor source channels "
            f"| {summary['actions_preserving_legal_anchor_source_channels']} |"
        ),
        (
            "| Execution phases preserving legal-anchor source channels "
            f"| {summary['execution_phases_preserving_legal_anchor_source_channels']} |"
        ),
        f"| Ready for prompt generation | {str(bool(summary['ready_for_prompt_generation'])).lower()} |",
        f"| Ready for worker-facing use | {str(bool(summary['ready_for_worker_facing_use'])).lower()} |",
        f"| Ready for comparable scoring | {str(bool(summary['ready_for_comparable_scoring'])).lower()} |",
        "",
        "## Counts By Lane",
        "",
        "| Lane | Actions |",
        "|---|---:|",
    ]
    for lane, count in doc["counts_by_lane"].items():
        lines.append(f"| `{_md_cell(lane)}` | {count} |")
    lines.extend([
        "",
        "## Execution Phases",
        "",
        "| Order | Phase | Actions | Depends on | Completion gate |",
        "|---:|---|---:|---|---|",
    ])
    for phase in doc["execution_phases"]:
        depends = ", ".join(phase["depends_on_phase_ids"]) or "none"
        lines.append(
            f"| {phase['order']} "
            f"| `{_md_cell(phase['id'])}` "
            f"| {phase['action_count']} "
            f"| {_md_cell(depends)} "
            f"| {_md_cell(phase['completion_gate'])} |"
        )
    lines.extend([
        "",
        "## Actions",
        "",
        "| Priority | ID | Lane | Type | Status | Rank | Output |",
        "|---:|---|---|---|---|---:|---|",
    ])
    for action in doc["actions"]:
        rank = action.get("expansion_rank")
        rank_display = rank if rank is not None else "n/a"
        lines.append(
            f"| {action['priority']} "
            f"| `{_md_cell(action['id'])}` "
            f"| `{_md_cell(action['lane'])}` "
            f"| `{_md_cell(action['item_type'])}` "
            f"| {_md_cell(action['status'])} "
            f"| {rank_display} "
            f"| {_md_cell(action['required_output'])} |"
        )
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
    ap.add_argument("--project-config", type=pathlib.Path, default=project_plan_builder.CONFIG)
    ap.add_argument("--registry", type=pathlib.Path, default=project_plan_builder.REGISTRY)
    ap.add_argument("--regulatory-catalog", type=pathlib.Path, default=project_plan_builder.REGULATORY_CATALOG)
    ap.add_argument("--out", type=pathlib.Path, default=OUT)
    ap.add_argument("--md-out", type=pathlib.Path, default=MD_OUT)
    ap.add_argument("--no-md", action="store_true", help="write only JSON, not the Markdown backlog")
    ap.add_argument(
        "--write-readiness",
        action="store_true",
        help="also write the composed readiness bundle artifacts",
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
    doc = build_next_actions(
        chain=chain,
        readiness_doc=readiness_doc,
        domain_id=args.domain,
        project_config_path=args.project_config,
        registry_path=args.registry,
        regulatory_catalog_path=args.regulatory_catalog,
        component_dir=args.component_dir,
    )
    if args.write_readiness:
        doc["artifact_paths"].update(
            readiness_builder.write_upstream_artifacts(
                chain,
                output_dir=args.component_dir,
                domain_id=args.domain,
                include_components=False,
            )
        )
    doc["artifact_paths"]["global_protections_next_actions_json"] = _artifact_path(args.out)
    if not args.no_md:
        doc["artifact_paths"]["global_protections_next_actions_markdown"] = _artifact_path(args.md_out)
    args.out.parent.mkdir(parents=True, exist_ok=True)
    args.out.write_text(json.dumps(doc, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
    md_path = None
    if not args.no_md:
        md_path = args.md_out
        md_path.parent.mkdir(parents=True, exist_ok=True)
        md_path.write_text(build_markdown_report(doc) + "\n", encoding="utf-8")
    summary = doc["summary"]
    print(
        "[global-protections-next-actions] "
        f"consistency_ok={str(bool(summary['consistency_ok'])).lower()}; "
        f"{summary['action_count']} actions; "
        f"{summary['immediate_action_count']} immediate; "
        f"ready_for_comparable_scoring={str(bool(summary['ready_for_comparable_scoring'])).lower()} -> {args.out}"
        + (f"; report {md_path}" if md_path else "")
    )
    return 0 if summary["consistency_ok"] else 1


if __name__ == "__main__":
    raise SystemExit(main())
