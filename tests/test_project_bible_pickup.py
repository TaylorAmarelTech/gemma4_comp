"""Regression tests for the project-bible continuation handoff."""
from __future__ import annotations

import copy
import importlib.util
import json
from datetime import datetime, timezone
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
GLOBAL_SAVED_ARTIFACT_VALIDATOR_DEPENDENCY_FILES = [
    "scripts/artifact_path_policy.py",
    "scripts/build_global_protections_curation_bundle.py",
    "scripts/build_global_protections_project_plan.py",
    "scripts/validate_domain_curation_bundle.py",
    "scripts/validate_domain_source_review_packet.py",
    "scripts/validate_global_protections_benchmark_blueprint.py",
    "scripts/validate_global_protections_curation_bundle.py",
    "scripts/validate_global_protections_curator_sprint.py",
    "scripts/validate_global_protections_diagnostic_run_plan.py",
    "scripts/validate_global_protections_eval_contract.py",
    "scripts/validate_global_protections_judge_calibration_plan.py",
    "scripts/validate_global_protections_jurisdiction_pack_matrix.py",
    "scripts/validate_global_protections_next_actions.py",
    "scripts/validate_global_protections_project_plan.py",
    "scripts/validate_global_protections_readiness_bundle.py",
    "scripts/validate_global_protections_source_channel_matrix.py",
    "scripts/validate_global_protections_source_channel_review_packet.py",
    "scripts/validate_global_protections_transition_gate.py",
    "scripts/validate_regulatory_curation_bundle.py",
    "scripts/validate_regulatory_domain_intake_packet.py",
]
AUTONOMOUS_ENGINE_DEPENDENCY_FILES = [
    "scripts/_atomic.py",
]


def _read(rel_path: str) -> str:
    return (ROOT / rel_path).read_text(encoding="utf-8")


def _load_pickup_validator():
    script = ROOT / "scripts" / "validate_project_bible_pickup.py"
    spec = importlib.util.spec_from_file_location("validate_project_bible_pickup", script)
    assert spec is not None
    module = importlib.util.module_from_spec(spec)
    assert spec.loader is not None
    spec.loader.exec_module(module)
    return module


def _paused_status_fixture() -> dict:
    return {
        "paused": True,
        "stop_sentinel": "reports/autonomous_engine.stop",
        "engine_process_alive": False,
        "cursor": 11,
        "queue_len": 41,
        "done": 11,
        "lock": {"state": "stale"},
        "current_job": {"index": 12, "model": "gemma4:31b", "n": 10000, "set": "full"},
        "full_promptset": {"prompt_count": 76442},
        "active_loop_scope": {
            "runner": "rich_harness_lift.py",
            "candidate_dimension_sweep_active": False,
            "rubric_version": "v1",
            "opt_in_rubric_versions_excluded": ["v2"],
            "rubric_version_mixing_allowed": False,
            "harness_version": "h1",
            "opt_in_harness_versions_excluded": ["h2"],
            "harness_version_mixing_allowed": False,
        },
        "latest_preflight": {
            "exists": True,
            "path": "reports/autonomous_engine_preflight.json",
            "ready": False,
            "mode": "manual_preflight",
            "schema_version": "autonomous_engine_preflight.v1",
            "matches_current_state": True,
            "needs_refresh": False,
            "readiness_scope": "state_only",
            "ollama_checked": False,
            "launch_ready_requires_ollama_check": True,
            "saved_lock_state": {"state": "stale"},
            "dimension_review_status": "validated_zero_proposals",
            "blockers": ["stop_sentinel_present"],
            "ignored_blockers": [],
            "state_mismatch_reasons": [],
        },
        "candidate_dimension_scope": {
            "rows": 201,
            "review_gate_status": "validated_zero_proposals",
            "active_in_autonomous_engine": False,
            "ready_for_mass_grading": False,
            "active_rubric_promotion_ready": False,
            "review_needed_count": 201,
            "current_job_prompt_dimension_cells": 2010000,
            "full_registry_prompt_dimension_cells": 15364842,
        },
    }


def _valid_global_protections_saved_artifacts_report() -> dict:
    return {
        "summary": {
            "valid": True,
            "artifact_count": 13,
            "valid_artifact_count": 13,
            "failed_artifact_count": 0,
            "missing_or_unreadable_artifact_count": 0,
            "markdown_artifact_count": 13,
            "missing_or_unreadable_markdown_count": 0,
            "unsafe_markdown_count": 0,
            "artifact_path_mismatch_count": 0,
            "total_check_count": 157,
            "total_failed_check_count": 0,
            "suite_check_count": 21,
            "suite_failed_check_count": 0,
            "phase_coverage_mismatch_count": 0,
            "legal_anchor_channel_mismatch_count": 0,
            "readiness_blocker_mismatch_count": 0,
            "curation_bundle_next_execution_phase_count": 5,
            "curation_bundle_next_phase_covered_actions": 34,
            "curation_bundle_curator_execution_phase_count": 5,
            "curation_bundle_curator_phase_covered_actions": 34,
            "ready_for_comparable_scoring": False,
        },
    }


def _write_minimal_pickup_tree(
    tmp_path: Path,
    *,
    mismatched_pack_project_id: bool = False,
    handoff_artifact: dict | None = None,
) -> None:
    files = {
        "AGENTS.md": "agent rules\n",
        "CLAUDE.md": (
            "Long-loop pickup brief (2026-07-02)\n"
            "[`PROJECT_BIBLE.md`](PROJECT_BIBLE.md)\n"
            "[`Plans.md`](Plans.md)\n"
            "compatibility bridge back to the project bible\n"
            "not a second planning source\n"
            "docs/codex/PROJECT_BIBLE.md\n"
            ".claude/rules/05_project_bible_pickup.md\n"
            "Fable 5-style agents\n"
            "Current validation discipline\n"
            "treat older suite counts in this file as historical\n"
            "python -m pytest packages --collect-only -q\n"
        ),
        "ROOT_FILES.md": (
            "| `PROJECT_BIBLE.md` | Root pointer to the canonical long-loop "
            "pickup brief in `docs/codex/PROJECT_BIBLE.md`. |\n"
            "| `Plans.md` | Compatibility bridge for older Claude Code handoffs. |\n"
        ),
        "PROJECT_BIBLE.md": (
            "Claude Code\n"
            "Codex\n"
            "Fable 5-style agents\n"
            "repo-root pickup tools\n"
            "Older hidden Claude handoffs may mention `Plans.md`\n"
            "compatibility bridge back to this pickup path\n"
            "not a separate planning source\n"
            "Read order for continuation sessions\n"
            "AGENTS.md\n"
            "CLAUDE.md\n"
            "docs/codex/PROJECT_BIBLE.md\n"
            ".claude/rules/05_project_bible_pickup.md\n"
            "reports/autonomous_engine.stop\n"
            "call Ollama\n"
            "promote candidate dimensions\n"
            "normal preflight and review gates\n"
        ),
        "Plans.md": (
            "compatibility bridge\n"
            "older Claude Code handoffs\n"
            "not the canonical planning source\n"
            "AGENTS.md\n"
            "CLAUDE.md\n"
            "PROJECT_BIBLE.md\n"
            "docs/codex/PROJECT_BIBLE.md\n"
            "paused engine state\n"
            "privacy-safe aggregate validators\n"
            "offline, propose-only\n"
            "v2 rubric and h2 harness evidence isolated\n"
            "reports/autonomous_engine.stop\n"
            "call Ollama\n"
            "promote candidate dimensions\n"
            "normal preflight and review gates\n"
        ),
        ".claude/rules/05_project_bible_pickup.md": (
            "root `PROJECT_BIBLE.md`\n"
            "docs/codex/PROJECT_BIBLE.md\n"
            "Plans.md\n"
            "compatibility bridge back to the project bible\n"
            "pause-safe loop\n"
            "Fable 5-style agents\n"
            "reports/autonomous_engine.stop\n"
            "call Ollama\n"
            "promote candidate dimensions\n"
            "active_loop_scope.rubric_version\n"
            "active_loop_scope.harness_version\n"
            "--rubric-version v2\n"
            "--harness-version h2\n"
            "--benign-control configs/duecare/benchmarks/benign_control_prompts.json\n"
            "separate over-refusal block\n"
            "never merged into the active v1/h1 under-refusal lift headline, public\n"
            "leaderboard, or autonomous loop\n"
            "opt-in research surfaces only\n"
            "do not mix v2/h2 rows into the active leaderboard\n"
        ),
        "docs/FILE_PURPOSE_GUIDE.md": (
            "| Agent handoff | `AGENTS.md`, `CLAUDE.md`, `PROJECT_BIBLE.md`, `Plans.md`, "
            "`.claude/rules/` |\n"
        ),
        "docs/REPO_LAYOUT.md": (
            "- AI pickup bridge: root [`PROJECT_BIBLE.md`](../PROJECT_BIBLE.md) "
            "points Claude Code, Codex, and Fable 5-style agents to "
            "[`docs/codex/PROJECT_BIBLE.md`](codex/PROJECT_BIBLE.md); "
            "root [`Plans.md`](../Plans.md) is a compatibility bridge for older "
            "Claude Code handoffs.\n"
        ),
        "docs/codex/PROJECT_BIBLE.md": (
            "docs/codex/goal_commands/13_project_bible_continuation.md\n"
            "python scripts\\validate_project_bible_pickup.py\n"
            "Copied handoff trees must include\n"
            "scripts/artifact_path_policy.py\n"
            "tests/test_artifact_path_policy.py\n"
            "safe `external/<name>` labels\n"
            "private-looking repo-relative segments\n"
            "external/custom_or_invalid\n"
            "tests/test_autonomous_engine.py\n"
            "scripts/build_domain_source_review_packet.py\n"
            "scripts/validate_domain_source_review_packet.py\n"
            "tests/test_build_domain_source_review_packet.py\n"
            "tests/test_validate_domain_source_review_packet.py\n"
            "tests/test_build_domain_grounding_manifest_proposal.py\n"
            "source-review privacy scans\n"
            "8+ digit copied case-like\n"
            "tests/test_build_global_protections_project_plan.py\n"
            "tests/test_validate_global_protections_project_plan.py\n"
            "tests/test_validate_sister_project_planning.py\n"
            "direct helper validators/builders\n"
            "direct local imports\n"
            "sister-project validator's direct local imports\n"
            "autonomous engine helper modules\n"
            "hidden rule also names `Plans.md`\n"
            "compatibility bridge for older handoffs\n"
            "`Plans.md` files fail closed\n"
            "compatibility bridge back to the Project Bible\n"
            "safe loop priorities\n"
            "paused-engine boundary\n"
            "--root <path>\n"
            "--status-json <path>\n"
            "--global-protections-report-json <path>\n"
            "hidden Claude handoff\n"
            "structured-handoff\n"
            "missing hidden artifact type fails closed\n"
            "aggregate open-risk severity counts\n"
            "aggregate open-risk kind counts\n"
            "open_risks shape\n"
            "Open-risk kind labels are allowlisted\n"
            "unknown hidden open-risk kind labels also fail closed\n"
            "high/critical blocking-risk count\n"
            "failed-check presence\n"
            "malformed hidden failed_checks values fail closed\n"
            "context-reset recommendation\n"
            "context_reset.recommended must be boolean\n"
            "context_reset.policy must be an object if present\n"
            "context_reset.policy.mode must stay allowlisted\n"
            "context_reset.policy.dryRun must be boolean if present\n"
            "context_reset.policy.thresholds and context_reset.counters must be objects if present\n"
            "context_reset.policy.thresholds and counters keys must stay allowlisted if present\n"
            "context_reset.policy.thresholds and counters values must be real integers if present\n"
            "context_reset.reasons must be a list if present\n"
            "context_reset reason entries must be strings if present\n"
            "context_reset.candidates must be a list if present\n"
            "context_reset candidate entries must be objects if present\n"
            "context_reset candidate triggered fields must be booleans if present\n"
            "context_reset triggered candidate counts are aggregate-only if present\n"
            "context_reset.recommended must be true when any valid candidate has triggered true\n"
            "context_reset candidate keys must stay allowlisted\n"
            "context_reset candidate actual and threshold fields must be real integers if present\n"
            "context_reset candidate triggered flags must match actual greater than threshold when both numbers are present\n"
            "Hidden decision_log and continuity sections are also aggregate-only\n"
            "decision_log must be a list if present\n"
            "decision_log entries must be objects if present\n"
            "decision_log decision labels must stay allowlisted\n"
            "decision_log actor labels must stay allowlisted if present\n"
            "decision_log timestamps must be valid ISO-8601 strings if present\n"
            "planItems and wipTasks must be absent, null, or lists if present\n"
            "task container counts are aggregate-only; task text and paths are never copied\n"
            "continuity must be an object if present\n"
            "continuity boolean fields must remain booleans\n"
            "continuity effort_hint must stay one of the allowlisted labels\n"
            "summaries, rationale text, paths, and private details are never copied\n"
            "parse failures are reported\n"
            "ready `false`\n"
            "stop_sentinel_present\n"
            "declared candidate pattern IDs\n"
            "unresolved source-gap rows\n"
            "Malformed scheme-prompt rows become aggregate row-shape and privacy counts\n"
            "Non-list scheme-prompt containers fail closed\n"
            "prompt_rows_not_list\n"
            "source admission rules\n"
            "Malformed project readiness-gate IDs fail closed as aggregate required-gate\n"
            "Malformed project phase and jurisdiction-pack row IDs fail closed\n"
            "Malformed grounding source row IDs fail closed\n"
            "Malformed or non-list grounding source containers expose\n"
            "Malformed grounding source URL values are scanned\n"
            "Private-looking details inside otherwise `https://` source URLs still fail\n"
            "current 34-check floor\n"
            "Malformed domain-lens review gates fail closed as aggregate counts\n"
            "readiness_gate_missing=0\n"
            "international anchors cannot substitute\n"
            "public complaint lists\n"
            "source_admission_missing=0\n"
            "scored_capability_missing=0\n"
            "omits raw scheme-prompt IDs\n"
            "metadata keys and values\n"
            "grounding_source_privacy_issue_count\n"
            "scheme_prompt_privacy_issue_count\n"
            "missing, malformed, or private source statuses\n"
            "source URLs\n"
            "malformed or copied schemes\n"
            "OneDrive/Documents/\n"
            "AppData/Local/\n"
            "s3:/\n"
            "aggregate counts\n"
            "invalid_or_unknown\n"
            "custom_or_invalid\n"
            "copied phase IDs\n"
            "Prompt parse-error details\n"
            "safe line numbers\n"
            "Boolean parse-error line values are not treated as line numbers\n"
            "Nonpositive parse-error line values are ignored\n"
            "known safe error labels\n"
            "custom error labels\n"
            "Hidden handoff string fields\n"
            "Hidden handoff nested state containers\n"
            "version and legacy_version labels\n"
            "dedicated hidden handoff version check\n"
            "allowlisted labels\n"
            "unknown hidden handoff labels fail closed\n"
            "timestamp presence\n"
            "timestamp validity\n"
            "validated_after_handoff\n"
            "not newer than the validation run\n"
            "High or critical hidden open-risk severities fail closed\n"
            "unknown hidden open-risk severities fail closed\n"
            "Unknown hidden open-risk kind labels also fail closed\n"
            "shape problem\n"
            "Copied sister/global summary count fields require real integers, not booleans\n"
            "Copied sister failed-id summaries keep only safe rule IDs\n"
            "malformed or private failed IDs become `custom_or_invalid`\n"
            "Copied sister project identity labels are allowlisted\n"
            "private or unknown identity labels become `custom_or_invalid`\n"
            "Boolean hidden recent-edit counts are ignored\n"
            "malformed hidden recentEdits values fail closed\n"
            "safe `recentEdits` length\n"
            "previous_state.plan_counts keys must stay allowlisted if present\n"
            "previous_state.plan_counts values must be real integers if present\n"
            "Saved status string fields\n"
            "unknown status labels fail closed\n"
            "custom blocker or mismatch labels\n"
            "Malformed copied status-list fields or entries also become `custom_or_invalid`\n"
            "forward-slash local model paths\n"
            "URL-scheme model labels\n"
            "Boolean values in numeric status count fields fail shape validation\n"
            "paused status queue counts must be coherent\n"
            "saved preflight schema and mode must match manual preflight v1\n"
            "saved preflight path must stay at reports/autonomous_engine_preflight.json\n"
            "saved preflight must exist and not need refresh\n"
            "launch readiness must still require an Ollama check\n"
            "saved preflight dimension-review status must match candidate-dimension review gate\n"
            "python scripts\\validate_sister_project_planning.py\n"
            "tests/test_validate_global_protections_saved_artifacts.py\n"
            "python scripts\\validate_global_protections_saved_artifacts.py\n"
            "python scripts\\validate_global_protections_saved_artifacts.py --json\n"
            "python -m pytest tests\\test_validate_global_protections_saved_artifacts.py -q\n"
            "python -m pytest tests -q -k \"global_protections or regulatory_miss_pattern\"\n"
            "python scripts\\autonomous_engine.py --status\n"
            "latest_preflight.saved_lock_state.state: \"stale\"\n"
            "Ollama not checked\n"
            "Candidate dimensions from the research spider are propose-only\n"
            "reports/autonomous_engine_preflight.json\n"
            "tests/test_rubric_v2.py\n"
            "active_loop_scope.rubric_version\n"
            "rubric_version\n"
            "opt_in_rubric_versions_excluded\n"
            "rubric_version_mixing_allowed\n"
            "active_loop_scope.harness_version\n"
            "harness_version\n"
            "opt_in_harness_versions_excluded\n"
            "harness_version_mixing_allowed\n"
            "tests/test_harness_v2.py\n"
            "--harness-version h2\n"
            "refusal-collapse fix\n"
            "h2 responses are NOT comparable with h1\n"
            "--rubric-version v2\n"
            "separate panel/report artifacts\n"
            "over-refusal channel\n"
            "Intent-aware benchmark\n"
            "under-refusal lift\n"
            "over-refusal block\n"
            "never merged\n"
            "--benign-control\n"
            "configs/duecare/benchmarks/benign_control_prompts.json\n"
            "adversarial prompts only\n"
            "tagged opt-in `rubric`, `harness`, or benign-control `intent` rows\n"
            "Malformed explicit rubric/harness/intent tags fail closed\n"
            "public leaderboard rows, or autonomous-loop evidence\n"
            "tests/test_intent_split.py\n"
            "tests/test_plan.py\n"
            "scripts/benchmark_leaderboard.py\n"
            "rich_harness_lift.py --plan\n"
            "NO model was called\n"
            "comparable `v1`/`h1` surface over adversarial prompts only\n"
            "contract metrics\n"
            "benchmark-ID guard\n"
            "email-like values\n"
            "path traversal\n"
            "long numeric case-like identifiers\n"
            "Markdown output\n"
            "Category/corridor/difficulty breakdown labels\n"
            "custom_or_invalid\n"
            "strict JSON\n"
            "NaN\n"
            "Infinity\n"
            "allowlisted numeric fields\n"
            "helper debug strings\n"
            "provenance fields\n"
            "generated` must be a timezone-aware ISO timestamp\n"
            "safe placeholders\n"
            "Pairwise, latency, and contract metrics require safe prompt, judge when present, and arm provenance before they can affect the public board\n"
            "Never mix v2 rows into v1 leaderboard\n"
        ),
        "docs/codex/README.md": "[`PROJECT_BIBLE.md`](PROJECT_BIBLE.md)\n",
        "docs/codex/00_do_not_break.md": "do not break\n",
        "docs/codex/00_kernel_compatibility_gate.md": "kernel gate\n",
        "docs/codex/00_execution_order.md": "execution order\n",
        "docs/codex/goal_commands/README.md": "[13](13_project_bible_continuation.md)\n",
        "docs/codex/goal_commands/13_project_bible_continuation.md": (
            "Fable 5-style agents\n"
            "Read, in order: AGENTS.md, CLAUDE.md, PROJECT_BIBLE.md\n"
            "python scripts\\autonomous_engine.py --status\n"
            "lock.state: \"stale\"\n"
            "latest_preflight.saved_lock_state.state: \"stale\"\n"
            "active_loop_scope.rubric_version\n"
            "active_loop_scope.harness_version\n"
            "--rubric-version v2\n"
            "--harness-version h2\n"
            "--benign-control configs/duecare/benchmarks/benign_control_prompts.json\n"
            "excluded from the active leaderboard and autonomous loop\n"
            "must not be merged into the active\n"
            "public leaderboard, or autonomous loop\n"
            "Do not remove reports/autonomous_engine.stop\n"
            "do not start scripts/autonomous_engine.py in run/once mode\n"
            "do not call Ollama\n"
            "do not promote candidate dimensions\n"
            "python scripts\\validate_project_bible_pickup.py\n"
            "python -m pytest tests\\test_artifact_path_policy.py -q\n"
            "python -m pytest tests\\test_intent_split.py -q\n"
            "python -m pytest tests\\test_plan.py -q\n"
            "rich_harness_lift.py --plan\n"
            "NO model was called\n"
            "python scripts\\validate_sister_project_planning.py\n"
            "python scripts\\validate_global_protections_saved_artifacts.py\n"
            "python -m pytest tests\\test_validate_global_protections_saved_artifacts.py -q\n"
            "python -m pytest tests -q -k \"global_protections or regulatory_miss_pattern\"\n"
            "python scripts\\validate_public_surface.py\n"
            "python -m pytest packages --collect-only -q\n"
            "python scripts\\validate_main_kaggle_kernels.py\n"
            "py -3.12 scripts\\validate_kaggle_page_sources.py\n"
        ),
        "scripts/autonomous_engine.py": "# placeholder\n",
        "scripts/benchmark_leaderboard.py": "# placeholder\n",
        "scripts/build_domain_grounding_manifest_proposal.py": "# placeholder\n",
        "scripts/build_domain_source_review_packet.py": "# placeholder\n",
        "scripts/rich_harness_lift.py": "# placeholder\n",
        "scripts/validate_global_protections_saved_artifacts.py": "# placeholder\n",
        "scripts/validate_project_bible_pickup.py": "# placeholder\n",
        "scripts/validate_sister_project_planning.py": "# placeholder\n",
        "configs/duecare/benchmarks/benign_control_prompts.json": json.dumps({
            "domain": "trafficking",
            "intent": "benign_control",
            "prompts": [
                {
                    "id": f"BENIGN-{idx:04d}",
                    "intent": "benign",
                    "category": "synthetic_worker_help",
                    "corridor": "generic",
                    "difficulty": "benign",
                    "source": "benign_control_synthetic",
                    "text": f"How can a migrant worker check a safe, legitimate help option {idx}?",
                }
                for idx in range(1, 13)
            ],
        }) + "\n",
        "tests/test_autonomous_engine.py": "# placeholder\n",
        "tests/test_artifact_path_policy.py": "# placeholder\n",
        "tests/test_benchmark_leaderboard.py": "# placeholder\n",
        "tests/test_build_domain_grounding_manifest_proposal.py": "# placeholder\n",
        "tests/test_build_domain_source_review_packet.py": "# placeholder\n",
        "tests/test_build_global_protections_project_plan.py": "# placeholder\n",
        "tests/test_harness_v2.py": "# placeholder\n",
        "tests/test_intent_split.py": "# placeholder\n",
        "tests/test_plan.py": "# placeholder\n",
        "tests/test_rubric_v2.py": "# placeholder\n",
        "tests/test_validate_domain_source_review_packet.py": "# placeholder\n",
        "tests/test_validate_global_protections_project_plan.py": "# placeholder\n",
        "tests/test_validate_global_protections_saved_artifacts.py": "# placeholder\n",
        "tests/test_validate_sister_project_planning.py": "# placeholder\n",
    }
    files.update({
        rel_path: "# placeholder\n"
        for rel_path in AUTONOMOUS_ENGINE_DEPENDENCY_FILES
    })
    files.update({
        rel_path: "# placeholder\n"
        for rel_path in GLOBAL_SAVED_ARTIFACT_VALIDATOR_DEPENDENCY_FILES
    })
    for rel_path, content in files.items():
        path = tmp_path / rel_path
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(content, encoding="utf-8")

    project = json.loads(
        (ROOT / "configs/duecare/benchmarks/sister_projects/global_protections_regulatory_benchmark.json")
        .read_text(encoding="utf-8")
    )
    packs = json.loads(
        (ROOT / "configs/duecare/benchmarks/sister_projects/global_protections_jurisdiction_packs.json")
        .read_text(encoding="utf-8")
    )
    grounding = json.loads(
        (ROOT / "configs/duecare/benchmarks/domains/developing_country_worker_protections/grounding_sources.json")
        .read_text(encoding="utf-8")
    )
    if mismatched_pack_project_id:
        packs["project_id"] = "mismatched_project_for_root_test"

    sister_dir = tmp_path / "configs/duecare/benchmarks/sister_projects"
    domain_dir = tmp_path / "configs/duecare/benchmarks/domains/developing_country_worker_protections"
    sister_dir.mkdir(parents=True, exist_ok=True)
    domain_dir.mkdir(parents=True, exist_ok=True)
    (sister_dir / "global_protections_regulatory_benchmark.json").write_text(
        json.dumps(project),
        encoding="utf-8",
    )
    (sister_dir / "global_protections_jurisdiction_packs.json").write_text(
        json.dumps(packs),
        encoding="utf-8",
    )
    (domain_dir / "grounding_sources.json").write_text(
        json.dumps(grounding),
        encoding="utf-8",
    )
    (domain_dir / "scheme_prompts.jsonl").write_text(
        (ROOT / "configs/duecare/benchmarks/domains/developing_country_worker_protections/scheme_prompts.jsonl")
        .read_text(encoding="utf-8"),
        encoding="utf-8",
    )
    if handoff_artifact is not None:
        handoff_path = tmp_path / ".claude/state/handoff-artifact.json"
        handoff_path.parent.mkdir(parents=True, exist_ok=True)
        handoff_path.write_text(json.dumps(handoff_artifact), encoding="utf-8")


def test_project_bible_is_linked_from_agent_indexes():
    root_project_bible = _read("PROJECT_BIBLE.md")
    plans = _read("Plans.md")
    claude = _read("CLAUDE.md")
    root_files = _read("ROOT_FILES.md")
    file_purpose_guide = _read("docs/FILE_PURPOSE_GUIDE.md")
    repo_layout = _read("docs/REPO_LAYOUT.md")
    codex_readme = _read("docs/codex/README.md")
    command_readme = _read("docs/codex/goal_commands/README.md")
    project_bible = _read("docs/codex/PROJECT_BIBLE.md")

    assert "docs/codex/PROJECT_BIBLE.md" in root_project_bible
    assert "Claude Code" in root_project_bible
    assert "Codex" in root_project_bible
    assert "Fable 5-style agents" in root_project_bible
    assert "repo-root pickup tools" in root_project_bible
    assert "Older hidden Claude handoffs may mention `Plans.md`" in root_project_bible
    assert "compatibility bridge back to this pickup path" in root_project_bible
    assert "not a separate planning source" in root_project_bible
    assert "Read order for continuation sessions" in root_project_bible
    assert "AGENTS.md" in root_project_bible
    assert "CLAUDE.md" in root_project_bible
    assert ".claude/rules/05_project_bible_pickup.md" in root_project_bible
    assert "reports/autonomous_engine.stop" in root_project_bible
    assert "call Ollama" in root_project_bible
    assert "promote candidate dimensions" in root_project_bible
    assert "normal preflight and review gates" in root_project_bible
    assert "compatibility bridge" in plans
    assert "older Claude Code handoffs" in plans
    assert "not the canonical planning source" in plans
    assert "AGENTS.md" in plans
    assert "CLAUDE.md" in plans
    assert "PROJECT_BIBLE.md" in plans
    assert "docs/codex/PROJECT_BIBLE.md" in plans
    assert "paused engine state" in plans
    assert "privacy-safe aggregate validators" in plans
    assert "offline, propose-only" in plans
    assert "v2 rubric and h2 harness evidence isolated" in plans
    assert "reports/autonomous_engine.stop" in plans
    assert "call Ollama" in plans
    assert "promote candidate dimensions" in plans
    assert "normal preflight and review gates" in plans
    assert "`PROJECT_BIBLE.md`" in root_files
    assert "Root pointer to the canonical long-loop pickup brief" in root_files
    assert "docs/codex/PROJECT_BIBLE.md" in root_files
    assert "`Plans.md`" in root_files
    assert "Compatibility bridge for older Claude Code handoffs" in root_files
    assert "| Agent handoff |" in file_purpose_guide
    assert "PROJECT_BIBLE.md" in file_purpose_guide
    assert "Plans.md" in file_purpose_guide
    assert ".claude/rules/" in file_purpose_guide
    assert "AI pickup bridge" in repo_layout
    assert "../PROJECT_BIBLE.md" in repo_layout
    assert "../Plans.md" in repo_layout
    assert "codex/PROJECT_BIBLE.md" in repo_layout
    assert "Fable 5-style agents" in repo_layout
    assert "older Claude Code handoffs" in repo_layout
    assert "Long-loop pickup brief (2026-07-02)" in claude
    assert "[`PROJECT_BIBLE.md`](PROJECT_BIBLE.md)" in claude
    assert "[`Plans.md`](Plans.md)" in claude
    assert "compatibility bridge back to the project bible" in claude
    assert "not a second planning source" in claude
    assert "docs/codex/PROJECT_BIBLE.md" in claude
    assert ".claude/rules/05_project_bible_pickup.md" in claude
    assert "Fable 5-style agents" in claude
    assert "[`PROJECT_BIBLE.md`](PROJECT_BIBLE.md)" in codex_readme
    assert "13_project_bible_continuation.md" in command_readme
    assert "docs/codex/goal_commands/13_project_bible_continuation.md" in project_bible
    assert "scripts/artifact_path_policy.py" in project_bible
    assert "tests/test_artifact_path_policy.py" in project_bible
    assert "safe `external/<name>` labels" in project_bible
    assert "private-looking repo-relative segments" in project_bible
    assert "external/custom_or_invalid" in project_bible
    assert 'lock.state: "stale"' in project_bible
    assert 'latest_preflight.saved_lock_state.state: "stale"' in project_bible
    assert "python scripts\\validate_sister_project_planning.py" in project_bible
    assert "tests/test_autonomous_engine.py" in project_bible
    assert "tests/test_validate_global_protections_saved_artifacts.py" in project_bible
    assert "tests/test_validate_sister_project_planning.py" in project_bible
    assert "Copied handoff trees must include" in project_bible
    assert "direct helper validators/builders" in project_bible
    assert "direct local imports" in project_bible
    assert "sister-project validator's" in project_bible
    assert "autonomous engine helper modules" in project_bible
    assert "hidden rule also names `Plans.md`" in project_bible
    assert "compatibility bridge for older handoffs" in project_bible
    assert "`Plans.md` files fail closed" in project_bible
    assert "compatibility bridge back to the Project Bible" in project_bible
    assert "safe loop priorities" in project_bible
    assert "paused-engine boundary" in project_bible
    assert "--project-config" in project_bible
    assert "--root <path>" in project_bible
    assert "--status-json <path>" in project_bible
    assert "--global-protections-report-json <path>" in project_bible
    assert "hidden Claude handoff" in project_bible
    assert "structured-handoff" in project_bible
    assert "missing hidden artifact type fails closed" in project_bible
    assert "aggregate open-risk severity counts" in project_bible
    assert "aggregate open-risk kind counts" in project_bible
    assert "open_risks shape" in project_bible
    assert "Open-risk kind labels are allowlisted" in project_bible
    assert "unknown hidden open-risk kind labels also fail closed" in project_bible.lower()
    assert "high/critical blocking-risk count" in project_bible
    assert "failed-check" in project_bible
    assert "malformed hidden failed_checks values fail closed" in project_bible
    assert "parse failures are reported" in project_bible
    assert "ready `false`" in project_bible
    assert "stop_sentinel_present" in project_bible
    assert "declared candidate pattern IDs" in project_bible
    assert "unresolved source-gap rows" in project_bible
    assert "Malformed scheme-prompt rows become aggregate row-shape and privacy counts" in project_bible
    assert "Non-list scheme-prompt containers fail closed" in project_bible
    assert "prompt_rows_not_list" in project_bible
    assert "source admission rules" in project_bible
    assert "Malformed project readiness-gate IDs fail closed as aggregate required-gate" in project_bible
    assert "Malformed project phase and jurisdiction-pack row IDs fail closed" in project_bible
    assert "Malformed grounding source row IDs fail closed" in project_bible
    assert "Malformed or non-list grounding source containers expose" in project_bible
    assert "Malformed grounding source URL values are scanned" in project_bible
    assert "Private-looking details inside otherwise `https://` source URLs still fail" in project_bible
    assert "current 34-check floor" in project_bible
    assert "Malformed domain-lens review gates fail closed as aggregate counts" in project_bible
    assert "international anchors cannot" in project_bible
    assert "public complaint lists" in project_bible
    assert "omits raw scheme-prompt IDs" in project_bible
    assert "metadata keys and values" in project_bible
    assert "grounding_source_privacy_issue_count" in project_bible
    assert "scheme_prompt_privacy_issue_count" in project_bible
    assert "missing, malformed, or private source statuses" in project_bible
    assert "source URLs" in project_bible
    assert "malformed or copied schemes" in project_bible
    assert "s3:/" in project_bible
    assert "OneDrive/Documents/" in project_bible
    assert "AppData/Local/" in project_bible
    assert "aggregate counts" in project_bible
    assert "invalid_or_unknown" in project_bible
    assert "custom_or_invalid" in project_bible
    assert "copied phase IDs" in project_bible
    assert "Prompt parse-error details" in project_bible
    assert "safe line numbers" in project_bible
    assert "Boolean parse-error line values are not treated as line numbers" in project_bible
    assert "Nonpositive parse-error line values are ignored" in project_bible
    assert "known safe error labels" in project_bible
    assert "custom error labels" in project_bible
    assert "Hidden handoff string fields" in project_bible
    assert "Hidden handoff nested state containers" in project_bible
    assert "version and legacy_version labels" in project_bible
    assert "dedicated hidden handoff version check" in project_bible
    assert "allowlisted labels" in project_bible
    assert "unknown hidden handoff labels fail closed" in project_bible
    assert "timestamp presence" in project_bible
    assert "timestamp validity" in project_bible
    assert "validated_after_handoff" in project_bible
    assert "not newer than the validation run" in project_bible
    assert "High or critical hidden open-risk severities fail closed" in project_bible
    assert "unknown hidden open-risk severities fail closed" in project_bible
    assert "Unknown hidden open-risk kind labels also fail closed" in project_bible
    assert "context-reset recommendation" in project_bible
    assert "context_reset.recommended must be boolean" in project_bible
    assert "context_reset.policy must be an object if present" in project_bible
    assert "context_reset.policy.mode must stay allowlisted" in project_bible
    assert "context_reset.policy.dryRun must be boolean if present" in project_bible
    assert (
        "context_reset.policy.thresholds and context_reset.counters must be objects if present"
        in project_bible
    )
    assert (
        "context_reset.policy.thresholds and counters keys must stay allowlisted if present"
        in project_bible
    )
    assert (
        "context_reset.policy.thresholds and counters values must be real integers if present"
        in project_bible
    )
    assert "context_reset.reasons must be a list if present" in project_bible
    assert "context_reset reason entries must be strings if present" in project_bible
    assert "context_reset.candidates must be a list if present" in project_bible
    assert "context_reset candidate entries must be objects if present" in project_bible
    assert (
        "context_reset candidate triggered fields must be booleans if present"
        in project_bible
    )
    assert (
        "context_reset triggered candidate counts are aggregate-only if present"
        in project_bible
    )
    assert (
        "context_reset.recommended must be true when any valid candidate has triggered true"
        in project_bible
    )
    assert "context_reset candidate keys must stay allowlisted" in project_bible
    assert (
        "context_reset candidate actual and threshold fields must be real integers if present"
        in project_bible
    )
    assert (
        "context_reset candidate triggered flags must match actual greater than threshold when both numbers are present"
        in project_bible
    )
    assert "Hidden decision_log and continuity sections are also aggregate-only" in project_bible
    assert "decision_log must be a list if present" in project_bible
    assert "decision_log entries must be objects if present" in project_bible
    assert "decision_log decision labels must stay allowlisted" in project_bible
    assert "decision_log actor labels must stay allowlisted if present" in project_bible
    assert "decision_log timestamps must be valid ISO-8601 strings if present" in project_bible
    assert "planItems and wipTasks must be absent, null, or lists if present" in project_bible
    assert "task container counts are aggregate-only; task text and paths are never copied" in project_bible
    assert "continuity must be an object if present" in project_bible
    assert "continuity boolean fields must remain booleans" in project_bible
    assert "continuity effort_hint must stay one of the allowlisted labels" in project_bible
    assert "summaries, rationale text, paths, and private details are never copied" in project_bible
    assert "shape problem" in project_bible
    assert (
        "Copied sister/global summary count fields require real integers, not booleans"
        in project_bible
    )
    assert "Copied sister failed-id summaries keep only safe rule IDs" in project_bible
    assert "malformed or private failed IDs become `custom_or_invalid`" in project_bible
    assert "Copied sister project identity labels are allowlisted" in project_bible
    assert "private or unknown identity labels become `custom_or_invalid`" in project_bible
    assert "Boolean hidden recent-edit counts are ignored" in project_bible
    assert "malformed hidden recentEdits values fail closed" in project_bible
    assert "safe `recentEdits` length" in project_bible
    assert "previous_state.plan_counts keys must stay allowlisted if present" in project_bible
    assert "previous_state.plan_counts values must be real integers if present" in project_bible
    assert "Saved status string fields" in project_bible
    assert "unknown status labels fail closed" in project_bible
    assert "custom blocker or mismatch labels" in project_bible
    assert "Malformed copied status-list fields or entries also become `custom_or_invalid`" in project_bible
    assert "forward-slash local model paths" in project_bible
    assert "URL-scheme model labels" in project_bible
    assert "Boolean values in numeric status count fields fail shape validation" in project_bible
    assert "python scripts\\validate_sister_project_planning.py`:" in project_bible
    assert "`65 checks, 0 findings`" in project_bible
    assert "`34 checks, 0 findings`" in project_bible
    assert "`readiness_gate_missing=0`" in project_bible
    assert "`source_admission_missing=0`" in project_bible
    assert "`scored_capability_missing=0`" in project_bible
    assert "`privacy_issues=project:0,packs:0,grounding:0,prompts:0,grounding_sources:0`" in project_bible
    assert "aggregate-only safety signal" in project_bible
    assert "python scripts\\validate_global_protections_saved_artifacts.py" in project_bible
    assert "python scripts\\validate_global_protections_saved_artifacts.py --json" in project_bible
    assert "python -m pytest tests\\test_validate_global_protections_saved_artifacts.py -q" in project_bible
    assert 'python -m pytest tests -q -k "global_protections or regulatory_miss_pattern"' in project_bible
    assert "Global-protections project plan" in project_bible
    assert "Queued scopes are explicit backlog only" in project_bible
    assert "reports/autonomous_engine_preflight.json" in project_bible
    assert "active_loop_scope.rubric_version" in project_bible
    assert "rubric_version" in project_bible
    assert "opt_in_rubric_versions_excluded" in project_bible
    assert "rubric_version_mixing_allowed" in project_bible
    assert "active_loop_scope.harness_version" in project_bible
    assert "harness_version" in project_bible
    assert "opt_in_harness_versions_excluded" in project_bible
    assert "harness_version_mixing_allowed" in project_bible
    assert "tests/test_harness_v2.py" in project_bible
    assert "--harness-version h2" in project_bible
    assert "refusal-collapse fix" in project_bible
    assert "h2 responses are NOT comparable with h1" in project_bible
    assert "Intent-aware benchmark" in project_bible
    assert "under-refusal lift" in project_bible
    assert "over-refusal block" in project_bible
    assert "never merged" in project_bible
    assert "--benign-control" in project_bible
    assert "configs/duecare/benchmarks/benign_control_prompts.json" in project_bible
    assert "adversarial prompts only" in project_bible
    assert "tagged opt-in `rubric`, `harness`, or benign-control `intent` rows" in project_bible
    assert "Malformed explicit rubric/harness/intent tags fail closed" in project_bible
    assert "public leaderboard rows, or autonomous-loop evidence" in project_bible
    assert "tests/test_intent_split.py" in project_bible
    assert "tests/test_plan.py" in project_bible
    assert "scripts/benchmark_leaderboard.py" in project_bible
    assert "rich_harness_lift.py --plan" in project_bible
    assert "NO model was called" in project_bible
    assert "python -m pytest tests\\test_artifact_path_policy.py -q" in project_bible
    assert "`7 passed`" in project_bible
    assert "stale public external-file placeholder wording" in project_bible
    assert "`9 passed`" in project_bible
    assert "resolver failures" in project_bible
    assert "comparable `v1`/`h1` surface over adversarial prompts only" in project_bible
    assert "contract metrics" in project_bible
    assert "benchmark-ID guard" in project_bible
    assert "email-like values" in project_bible
    assert "path traversal" in project_bible
    assert "long numeric case-like identifiers" in project_bible
    assert "Markdown output" in project_bible
    assert "Category/corridor/difficulty breakdown labels" in project_bible
    assert "custom_or_invalid" in project_bible
    assert "strict JSON" in project_bible
    assert "NaN" in project_bible
    assert "Infinity" in project_bible
    assert "allowlisted numeric fields" in project_bible
    assert "helper debug strings" in project_bible
    assert "provenance fields" in project_bible
    assert "generated` must be a timezone-aware ISO timestamp" in project_bible
    assert "safe placeholders" in project_bible
    assert (
        "Pairwise, latency, and contract metrics require safe prompt, judge when present, and arm provenance before they can affect the public board"
        in project_bible
    )
    assert "Current validation discipline" in claude
    assert "treat older suite counts in this file as historical" in claude
    assert "python -m pytest packages --collect-only -q" in claude


def test_goal_command_readme_indexes_every_numbered_command_file():
    command_dir = ROOT / "docs" / "codex" / "goal_commands"
    command_readme = _read("docs/codex/goal_commands/README.md")

    command_files = sorted(
        path.name for path in command_dir.glob("[0-9][0-9]_*.md")
    )

    assert command_files
    missing = [
        filename for filename in command_files
        if f"]({filename})" not in command_readme
    ]
    assert missing == []


def test_goal_command_readme_separates_original_goal_and_long_run_rules():
    command_readme = _read("docs/codex/goal_commands/README.md")

    assert "All command packs assume:" in command_readme
    assert "Original per-goal packs also assume:" in command_readme
    assert "Later long-run packs (`07` through `13`) define their own commit cadence" in command_readme
    assert "Every command in this directory assumes" not in command_readme


def test_claude_hidden_pickup_rule_preserves_pause_boundary():
    rule = _read(".claude/rules/05_project_bible_pickup.md")

    assert "root `PROJECT_BIBLE.md`" in rule
    assert "docs/codex/PROJECT_BIBLE.md" in rule
    assert "Plans.md" in rule
    assert "compatibility bridge back to the project bible" in rule
    assert "pause-safe loop" in rule
    assert "Fable 5-style agents" in rule
    assert "reports/autonomous_engine.stop" in rule
    assert "call Ollama" in rule
    assert "promote candidate dimensions" in rule
    assert "active_loop_scope.rubric_version" in rule
    assert "active_loop_scope.harness_version" in rule
    assert "--rubric-version v2" in rule
    assert "--harness-version h2" in rule
    assert "--benign-control configs/duecare/benchmarks/benign_control_prompts.json" in rule
    assert "separate over-refusal block" in rule
    assert "never merged into the active v1/h1 under-refusal lift headline, public" in rule
    assert "leaderboard, or autonomous loop" in rule
    assert "opt-in research surfaces only" in rule
    assert "do not mix v2/h2 rows into the active leaderboard" in rule


def test_project_bible_continuation_goal_pins_safety_and_validation():
    command = _read("docs/codex/goal_commands/13_project_bible_continuation.md")

    assert "/goal In the DueCare repository root" in command
    assert "C:\\Users\\" not in command
    assert "OneDrive\\Documents" not in command
    assert "Fable 5-style agents" in command
    assert "Read, in order: AGENTS.md, CLAUDE.md, PROJECT_BIBLE.md" in command
    assert "docs/codex/PROJECT_BIBLE.md" in command
    assert "python scripts\\autonomous_engine.py --status" in command
    assert 'latest_preflight.saved_lock_state.state: "stale"' in command
    assert "active_loop_scope.rubric_version" in command
    assert "active_loop_scope.harness_version" in command
    assert "--rubric-version v2" in command
    assert "--harness-version h2" in command
    assert "--benign-control configs/duecare/benchmarks/benign_control_prompts.json" in command
    assert "excluded from the active leaderboard and autonomous loop" in command
    assert "must not be merged into the active" in command
    assert "public leaderboard, or autonomous loop" in command
    assert "Do not remove reports/autonomous_engine.stop" in command
    assert "do not call Ollama" in command
    assert "do not promote candidate dimensions" in command
    assert "python scripts\\validate_project_bible_pickup.py" in command
    assert "python -m pytest tests\\test_artifact_path_policy.py -q" in command
    assert "python -m pytest tests\\test_intent_split.py -q" in command
    assert "python -m pytest tests\\test_plan.py -q" in command
    assert "rich_harness_lift.py --plan" in command
    assert "NO model was called" in command
    assert "python scripts\\validate_global_protections_saved_artifacts.py" in command
    assert "python -m pytest tests\\test_validate_global_protections_saved_artifacts.py -q" in command
    assert 'python -m pytest tests -q -k "global_protections or regulatory_miss_pattern"' in command
    assert "python scripts\\validate_sister_project_planning.py" in command
    assert "python scripts\\validate_public_surface.py" in command
    assert "python -m pytest packages --collect-only -q" in command
    assert "python scripts\\validate_main_kaggle_kernels.py" in command
    assert "py -3.12 scripts\\validate_kaggle_page_sources.py" in command


def test_project_bible_pickup_validator_requires_delegated_validator_files():
    validator = _load_pickup_validator()

    assert validator.AUTONOMOUS_ENGINE_DEPENDENCY_FILES == AUTONOMOUS_ENGINE_DEPENDENCY_FILES
    assert (
        validator.GLOBAL_SAVED_ARTIFACT_VALIDATOR_DEPENDENCY_FILES
        == GLOBAL_SAVED_ARTIFACT_VALIDATOR_DEPENDENCY_FILES
    )
    assert "Plans.md" in validator.REQUIRED_FILES
    assert "scripts/validate_global_protections_saved_artifacts.py" in validator.REQUIRED_FILES
    assert "scripts/validate_project_bible_pickup.py" in validator.REQUIRED_FILES
    assert "scripts/validate_sister_project_planning.py" in validator.REQUIRED_FILES
    assert "scripts/benchmark_leaderboard.py" in validator.REQUIRED_FILES
    assert "scripts/build_domain_grounding_manifest_proposal.py" in validator.REQUIRED_FILES
    assert "scripts/build_domain_source_review_packet.py" in validator.REQUIRED_FILES
    assert "scripts/rich_harness_lift.py" in validator.REQUIRED_FILES
    assert "configs/duecare/benchmarks/benign_control_prompts.json" in validator.REQUIRED_FILES
    assert "tests/test_autonomous_engine.py" in validator.REQUIRED_FILES
    assert "tests/test_artifact_path_policy.py" in validator.REQUIRED_FILES
    assert "tests/test_benchmark_leaderboard.py" in validator.REQUIRED_FILES
    assert "tests/test_build_domain_grounding_manifest_proposal.py" in validator.REQUIRED_FILES
    assert "tests/test_build_domain_source_review_packet.py" in validator.REQUIRED_FILES
    assert "tests/test_build_global_protections_project_plan.py" in validator.REQUIRED_FILES
    assert "tests/test_harness_v2.py" in validator.REQUIRED_FILES
    assert "tests/test_intent_split.py" in validator.REQUIRED_FILES
    assert "tests/test_plan.py" in validator.REQUIRED_FILES
    assert "tests/test_rubric_v2.py" in validator.REQUIRED_FILES
    assert "tests/test_validate_domain_source_review_packet.py" in validator.REQUIRED_FILES
    assert "tests/test_validate_global_protections_project_plan.py" in validator.REQUIRED_FILES
    assert "tests/test_validate_global_protections_saved_artifacts.py" in validator.REQUIRED_FILES
    assert "tests/test_validate_sister_project_planning.py" in validator.REQUIRED_FILES
    for rel_path in AUTONOMOUS_ENGINE_DEPENDENCY_FILES:
        assert rel_path in validator.REQUIRED_FILES
    for rel_path in GLOBAL_SAVED_ARTIFACT_VALIDATOR_DEPENDENCY_FILES:
        assert rel_path in validator.REQUIRED_FILES
    assert "ROOT_FILES.md" in validator.REQUIRED_FILES
    assert "docs/FILE_PURPOSE_GUIDE.md" in validator.REQUIRED_FILES
    assert "docs/REPO_LAYOUT.md" in validator.REQUIRED_FILES


def test_project_bible_pickup_validator_imports_global_saved_artifact_validator():
    validator = _load_pickup_validator()

    assert hasattr(validator, "validate_global_protections_saved_artifacts")


def test_project_bible_pickup_validator_passes_paused_fixture():
    validator = _load_pickup_validator()

    report = validator.build_report(
        status_payload=_paused_status_fixture(),
        global_protections_report=_valid_global_protections_saved_artifacts_report(),
    )

    assert report["summary"]["ok"] is True
    assert report["summary"]["check_count"] == 65
    assert report["summary"]["failed_ids"] == []
    assert report["snapshot"]["paused"] is True
    assert report["snapshot"]["engine_process_alive"] is False
    assert report["snapshot"]["lock_state"] == "stale"
    assert report["snapshot"]["current_job"] == {
        "index": 12,
        "model": "gemma4:31b",
        "n": 10000,
        "set": "full",
    }
    assert report["snapshot"]["latest_preflight"] == {
        "exists": True,
        "path": "reports/autonomous_engine_preflight.json",
        "ready": False,
        "mode": "manual_preflight",
        "schema_version": "autonomous_engine_preflight.v1",
        "readiness_scope": "state_only",
        "ollama_checked": False,
        "launch_ready_requires_ollama_check": True,
        "matches_current_state": True,
        "needs_refresh": False,
        "saved_lock_state": "stale",
        "dimension_review_status": "validated_zero_proposals",
        "blockers": ["stop_sentinel_present"],
        "ignored_blockers": [],
        "state_mismatch_reasons": [],
    }
    assert report["snapshot"]["active_loop_scope"] == {
        "runner": "rich_harness_lift.py",
        "candidate_dimension_sweep_active": False,
        "rubric_version": "v1",
        "opt_in_rubric_versions_excluded": ["v2"],
        "rubric_version_mixing_allowed": False,
        "harness_version": "h1",
        "opt_in_harness_versions_excluded": ["h2"],
        "harness_version_mixing_allowed": False,
    }
    assert report["snapshot"]["candidate_dimensions"] == {
        "rows": 201,
        "review_gate_status": "validated_zero_proposals",
        "active_in_autonomous_engine": False,
        "ready_for_mass_grading": False,
        "active_rubric_promotion_ready": False,
        "review_needed_count": 201,
        "current_job_prompt_dimension_cells": 2010000,
        "full_registry_prompt_dimension_cells": 15364842,
    }
    assert report["sister_project_planning"] == {
        "ok": True,
        "check_count": 34,
        "failed_count": 0,
        "failed_ids": [],
        "project_id": "global_protections_regulatory_benchmark",
        "project_status": "propose_only",
        "project_pack_id_match": True,
        "grounding_domain": "developing_country_worker_protections",
        "scheme_prompt_count": 12,
        "scheme_prompt_category_count": 12,
        "scheme_prompt_candidate_pattern_count": 10,
        "scheme_prompt_candidate_patterns_without_project_declaration_count": 0,
        "scheme_prompt_unresolved_scope_count": 12,
        "scheme_prompt_not_ready_count": 12,
        "scheme_prompt_categories_without_source_slots_count": 0,
        "queued_jurisdiction_scope_count": 5,
        "local_source_jurisdictions_without_scope_count": 0,
        "duplicate_id_issue_count": 0,
        "readiness_gate_missing_block_concept_count": 0,
        "source_admission_missing_concept_count": 0,
        "scored_capability_missing_concept_count": 0,
        "project_privacy_issue_count": 0,
        "jurisdiction_pack_privacy_issue_count": 0,
        "grounding_metadata_privacy_issue_count": 0,
        "grounding_source_privacy_issue_count": 0,
        "scheme_prompt_privacy_issue_count": 0,
    }
    assert report["global_protections_saved_artifacts"] == {
        "valid": True,
        "artifact_count": 13,
        "valid_artifact_count": 13,
        "failed_artifact_count": 0,
        "missing_or_unreadable_artifact_count": 0,
        "markdown_artifact_count": 13,
        "missing_or_unreadable_markdown_count": 0,
        "unsafe_markdown_count": 0,
        "artifact_path_mismatch_count": 0,
        "total_check_count": 157,
        "total_failed_check_count": 0,
        "suite_check_count": 21,
        "suite_failed_check_count": 0,
        "phase_coverage_mismatch_count": 0,
        "legal_anchor_channel_mismatch_count": 0,
        "readiness_blocker_mismatch_count": 0,
        "next_phase_coverage": {"phase_count": 5, "covered_actions": 34},
        "curator_phase_coverage": {"phase_count": 5, "covered_actions": 34},
        "ready_for_comparable_scoring": False,
    }


def test_project_bible_pickup_validator_rejects_incoherent_mixed_engine_status():
    validator = _load_pickup_validator()
    status = copy.deepcopy(_paused_status_fixture())
    status["engine_process_alive"] = True
    status["lock"]["state"] = "live"
    status["latest_preflight"]["ollama_checked"] = True
    status["latest_preflight"]["readiness_scope"] = "launch"

    report = validator.build_report(
        status_payload=status,
        global_protections_report=_valid_global_protections_saved_artifacts_report(),
    )

    assert report["summary"]["ok"] is False
    assert set(report["summary"]["failed_ids"]) >= {
        "engine_pause_or_live_mode_is_coherent",
        "lock_state_matches_engine_mode",
        "latest_preflight_scope_matches_engine_mode",
    }


def test_project_bible_pickup_validator_accepts_coherent_live_status():
    validator = _load_pickup_validator()
    status = copy.deepcopy(_paused_status_fixture())
    status["paused"] = False
    status["stop_sentinel"] = ""
    status["engine_process_alive"] = True
    status["lock"] = {
        "exists": True, "pid": 1234, "alive": True, "stale": False, "state": "live",
    }
    preflight = status["latest_preflight"]
    preflight.update({
        "launch_ready_requires_ollama_check": False,
        "ollama_checked": True,
        "readiness_scope": "launch",
        "ready": False,
        "blockers": ["live_engine_lock_present"],
        "ignored_blockers": [],
        "saved_lock_state": {
            "exists": True, "pid": 1234, "alive": True, "stale": False, "state": "live",
        },
    })

    report = validator.build_report(
        status_payload=status,
        global_protections_report=_valid_global_protections_saved_artifacts_report(),
    )

    assert report["summary"]["ok"] is True


def test_project_bible_pickup_validator_rejects_boolean_numeric_status_fields():
    validator = _load_pickup_validator()
    status = copy.deepcopy(_paused_status_fixture())
    status["cursor"] = True
    status["queue_len"] = False
    status["current_job"]["index"] = True
    status["current_job"]["n"] = False
    status["full_promptset"]["prompt_count"] = True
    status["candidate_dimension_scope"]["rows"] = False
    status["candidate_dimension_scope"]["review_needed_count"] = True
    status["candidate_dimension_scope"]["current_job_prompt_dimension_cells"] = False
    status["candidate_dimension_scope"]["full_registry_prompt_dimension_cells"] = True

    report = validator.build_report(
        status_payload=status,
        global_protections_report=_valid_global_protections_saved_artifacts_report(),
    )
    shape_check = next(
        check for check in report["checks"]
        if check["id"] == "status_payload_has_expected_shape"
    )

    assert report["summary"]["ok"] is False
    assert report["summary"]["failed_ids"] == ["status_payload_has_expected_shape"]
    assert set(shape_check["actual"]) >= {
        "cursor:missing_or_not_int",
        "queue_len:missing_or_not_int",
        "current_job.index:missing_or_not_int",
        "current_job.n:missing_or_not_int",
        "full_promptset.prompt_count:missing_or_not_int",
        "candidate_dimension_scope.rows:missing_or_not_int",
        "candidate_dimension_scope.review_needed_count:missing_or_not_int",
        "candidate_dimension_scope.current_job_prompt_dimension_cells:missing_or_not_int",
        "candidate_dimension_scope.full_registry_prompt_dimension_cells:missing_or_not_int",
    }
    assert report["snapshot"]["queue"] == {"cursor": None, "queue_len": None, "done": 11}
    assert report["snapshot"]["current_job"]["index"] is None
    assert report["snapshot"]["current_job"]["n"] is None
    assert report["snapshot"]["full_promptset"]["prompt_count"] is None
    assert report["snapshot"]["candidate_dimensions"]["rows"] is None
    assert report["snapshot"]["candidate_dimensions"]["review_needed_count"] is None


def test_project_bible_pickup_validator_rejects_incoherent_status_queue_progress():
    validator = _load_pickup_validator()
    status = copy.deepcopy(_paused_status_fixture())
    status["done"] = 9
    status["current_job"]["index"] = 14

    report = validator.build_report(
        status_payload=status,
        global_protections_report=_valid_global_protections_saved_artifacts_report(),
    )
    progress_check = next(
        check for check in report["checks"]
        if check["id"] == "status_queue_progress_is_coherent"
    )

    assert report["summary"]["ok"] is False
    assert report["summary"]["failed_ids"] == ["status_queue_progress_is_coherent"]
    assert progress_check["actual"] == {
        "cursor": 11,
        "done": 9,
        "queue_len": 41,
        "current_job_index": 14,
    }


def test_project_bible_pickup_validator_rejects_missing_preflight_schema_or_mode():
    validator = _load_pickup_validator()
    status = copy.deepcopy(_paused_status_fixture())
    del status["latest_preflight"]["mode"]
    del status["latest_preflight"]["schema_version"]

    report = validator.build_report(
        status_payload=status,
        global_protections_report=_valid_global_protections_saved_artifacts_report(),
    )
    schema_check = next(
        check for check in report["checks"]
        if check["id"] == "latest_preflight_schema_and_mode_match_manual_v1"
    )

    assert report["summary"]["ok"] is False
    assert report["summary"]["failed_ids"] == [
        "latest_preflight_schema_and_mode_match_manual_v1"
    ]
    assert schema_check["actual"] == {"mode": None, "schema_version": None}


def test_project_bible_pickup_validator_rejects_copied_preflight_path_without_leak():
    validator = _load_pickup_validator()
    status = copy.deepcopy(_paused_status_fixture())
    status["latest_preflight"]["path"] = "C:\\Users\\private\\case-status.json"

    report = validator.build_report(
        status_payload=status,
        global_protections_report=_valid_global_protections_saved_artifacts_report(),
    )
    path_check = next(
        check for check in report["checks"]
        if check["id"] == "latest_preflight_path_is_expected"
    )
    rendered = json.dumps(report, ensure_ascii=False)

    assert report["summary"]["ok"] is False
    assert report["summary"]["failed_ids"] == ["latest_preflight_path_is_expected"]
    assert path_check["actual"] == {"path": "custom_or_invalid"}
    assert "case-status" not in rendered
    assert "C:\\Users" not in rendered


def test_project_bible_pickup_validator_rejects_mismatched_dimension_review_status():
    validator = _load_pickup_validator()
    status = copy.deepcopy(_paused_status_fixture())
    status["latest_preflight"]["dimension_review_status"] = "review_packet_missing"

    report = validator.build_report(
        status_payload=status,
        global_protections_report=_valid_global_protections_saved_artifacts_report(),
    )
    review_check = next(
        check for check in report["checks"]
        if check["id"] == "latest_preflight_dimension_review_matches_candidate_scope"
    )

    assert report["summary"]["ok"] is False
    assert report["summary"]["failed_ids"] == [
        "latest_preflight_dimension_review_matches_candidate_scope"
    ]
    assert review_check["actual"] == {
        "latest_preflight_dimension_review_status": "review_packet_missing",
        "candidate_review_gate_status": "validated_zero_proposals",
    }


def test_project_bible_pickup_validator_rejects_missing_or_stale_saved_preflight():
    validator = _load_pickup_validator()
    status = copy.deepcopy(_paused_status_fixture())
    status["latest_preflight"]["exists"] = False
    status["latest_preflight"]["needs_refresh"] = True

    report = validator.build_report(
        status_payload=status,
        global_protections_report=_valid_global_protections_saved_artifacts_report(),
    )
    freshness_check = next(
        check for check in report["checks"]
        if check["id"] == "latest_preflight_exists_and_is_fresh"
    )

    assert report["summary"]["ok"] is False
    assert report["summary"]["failed_ids"] == [
        "latest_preflight_exists_and_is_fresh"
    ]
    assert freshness_check["actual"] == {"exists": False, "needs_refresh": True}


def test_project_bible_pickup_validator_rejects_launch_without_required_ollama_check():
    validator = _load_pickup_validator()
    status = copy.deepcopy(_paused_status_fixture())
    status["latest_preflight"]["launch_ready_requires_ollama_check"] = False

    report = validator.build_report(
        status_payload=status,
        global_protections_report=_valid_global_protections_saved_artifacts_report(),
    )
    ollama_check = next(
        check for check in report["checks"]
        if check["id"] == "latest_preflight_ollama_requirement_is_coherent"
    )

    assert report["summary"]["ok"] is False
    assert report["summary"]["failed_ids"] == [
        "latest_preflight_ollama_requirement_is_coherent"
    ]
    assert ollama_check["actual"] == {
        "launch_ready_requires_ollama_check": False,
        "ollama_checked": False,
    }


def test_project_bible_pickup_validator_rejects_launch_ready_or_ignored_stop_sentinel():
    validator = _load_pickup_validator()
    status = copy.deepcopy(_paused_status_fixture())
    status["latest_preflight"]["ready"] = True
    status["latest_preflight"]["blockers"] = []
    status["latest_preflight"]["ignored_blockers"] = ["stop_sentinel_present"]

    report = validator.build_report(
        status_payload=status,
        global_protections_report=_valid_global_protections_saved_artifacts_report(),
    )

    assert report["summary"]["ok"] is False
    assert "latest_preflight_blockers_match_engine_mode" in report["summary"]["failed_ids"]
    assert report["snapshot"]["latest_preflight"]["ready"] is True
    assert report["snapshot"]["latest_preflight"]["ignored_blockers"] == ["stop_sentinel_present"]


def test_project_bible_pickup_validator_sanitizes_custom_status_json_labels():
    validator = _load_pickup_validator()
    status = copy.deepcopy(_paused_status_fixture())
    status["stop_sentinel"] = "C:\\Users\\private\\autonomous_engine.stop"
    status["lock"]["state"] = "private-live-lock-C:\\Users\\private\\lock"
    status["current_job"]["model"] = "C:/Users/private/model.gguf"
    status["current_job"]["set"] = "private-prompt-bucket"
    status["latest_preflight"]["readiness_scope"] = "private-launch-scope"
    status["latest_preflight"]["saved_lock_state"]["state"] = "private-saved-lock"
    status["latest_preflight"]["blockers"] = [
        "stop_sentinel_present",
        "private-blocker-case-row",
        {"private": "C:\\Users\\private\\copied-preflight.json"},
    ]
    status["latest_preflight"]["ignored_blockers"] = [
        "private-ignored-blocker-worker-name",
    ]
    status["latest_preflight"]["state_mismatch_reasons"] = [
        "private-mismatch-C:\\Users\\private\\preflight.json",
    ]
    status["active_loop_scope"]["runner"] = "private-runner-C:\\Users\\private\\runner.py"
    status["active_loop_scope"]["rubric_version"] = "private-rubric-v3"
    status["active_loop_scope"]["opt_in_rubric_versions_excluded"] = [
        "v2",
        "private-rubric-row",
    ]
    status["active_loop_scope"]["harness_version"] = "private-harness-h3"
    status["active_loop_scope"]["opt_in_harness_versions_excluded"] = [
        "h2",
        "private-harness-row",
    ]
    status["candidate_dimension_scope"]["review_gate_status"] = "private-review-gate"

    report = validator.build_report(
        status_payload=status,
        global_protections_report=_valid_global_protections_saved_artifacts_report(),
    )
    rendered = json.dumps(report, ensure_ascii=False)

    assert report["summary"]["ok"] is False
    assert "status_string_labels_are_known_if_present" in report["summary"]["failed_ids"]
    assert report["snapshot"]["stop_sentinel"] == "custom_or_invalid"
    assert report["snapshot"]["lock_state"] == "custom_or_invalid"
    assert report["snapshot"]["current_job"]["model"] == "custom_or_invalid"
    assert report["snapshot"]["current_job"]["set"] == "custom_or_invalid"
    assert report["snapshot"]["latest_preflight"]["readiness_scope"] == "custom_or_invalid"
    assert report["snapshot"]["latest_preflight"]["saved_lock_state"] == "custom_or_invalid"
    assert report["snapshot"]["latest_preflight"]["blockers"] == [
        "stop_sentinel_present",
        "custom_or_invalid",
        "custom_or_invalid",
    ]
    assert report["snapshot"]["latest_preflight"]["ignored_blockers"] == ["custom_or_invalid"]
    assert report["snapshot"]["latest_preflight"]["state_mismatch_reasons"] == ["custom_or_invalid"]
    assert report["snapshot"]["active_loop_scope"]["runner"] == "custom_or_invalid"
    assert report["snapshot"]["active_loop_scope"]["rubric_version"] == "custom_or_invalid"
    assert report["snapshot"]["active_loop_scope"]["opt_in_rubric_versions_excluded"] == [
        "v2",
        "custom_or_invalid",
    ]
    assert report["snapshot"]["active_loop_scope"]["harness_version"] == "custom_or_invalid"
    assert report["snapshot"]["active_loop_scope"]["opt_in_harness_versions_excluded"] == [
        "h2",
        "custom_or_invalid",
    ]
    assert report["snapshot"]["candidate_dimensions"]["review_gate_status"] == "custom_or_invalid"
    assert "private-live-lock" not in rendered
    assert "private-prompt-bucket" not in rendered
    assert "private-launch-scope" not in rendered
    assert "private-blocker-case-row" not in rendered
    assert "private-ignored-blocker" not in rendered
    assert "private-mismatch" not in rendered
    assert "private-runner" not in rendered
    assert "private-rubric" not in rendered
    assert "private-harness" not in rendered
    assert "private-review-gate" not in rendered
    assert "model.gguf" not in rendered


def test_project_bible_pickup_validator_sanitizes_file_url_status_model_label():
    validator = _load_pickup_validator()
    status = copy.deepcopy(_paused_status_fixture())
    status["current_job"]["model"] = "file:/C:/Users/private/model.gguf"

    report = validator.build_report(
        status_payload=status,
        global_protections_report=_valid_global_protections_saved_artifacts_report(),
    )
    rendered = json.dumps(report, ensure_ascii=False)

    assert report["summary"]["ok"] is False
    assert "status_string_labels_are_known_if_present" in report["summary"]["failed_ids"]
    assert report["snapshot"]["current_job"]["model"] == "custom_or_invalid"
    assert "file:/C:/Users" not in rendered
    assert "model.gguf" not in rendered


def test_project_bible_pickup_validator_sanitizes_long_numeric_status_model_label():
    validator = _load_pickup_validator()
    status = copy.deepcopy(_paused_status_fixture())
    status["current_job"]["model"] = "local-case-123456789"

    report = validator.build_report(
        status_payload=status,
        global_protections_report=_valid_global_protections_saved_artifacts_report(),
    )
    rendered = json.dumps(report, ensure_ascii=False)

    assert report["summary"]["ok"] is False
    assert "status_string_labels_are_known_if_present" in report["summary"]["failed_ids"]
    assert report["snapshot"]["current_job"]["model"] == "custom_or_invalid"
    assert "local-case-123456789" not in rendered
    assert "123456789" not in rendered


def test_project_bible_pickup_validator_rejects_custom_preflight_blocker_without_leak():
    validator = _load_pickup_validator()
    status = copy.deepcopy(_paused_status_fixture())
    status["latest_preflight"]["blockers"] = [
        "stop_sentinel_present",
        "private-blocker-case-row",
        {"private": "C:\\Users\\private\\copied-preflight.json"},
    ]

    report = validator.build_report(
        status_payload=status,
        global_protections_report=_valid_global_protections_saved_artifacts_report(),
    )
    rendered = json.dumps(report, ensure_ascii=False)

    assert report["summary"]["ok"] is False
    assert report["summary"]["failed_ids"] == [
        "status_string_labels_are_known_if_present"
    ]
    label_check = next(
        check
        for check in report["checks"]
        if check["id"] == "status_string_labels_are_known_if_present"
    )
    assert label_check["actual"] == {
        "custom_or_invalid_fields": ["latest_preflight.blockers"]
    }
    assert report["snapshot"]["latest_preflight"]["blockers"] == [
        "stop_sentinel_present",
        "custom_or_invalid",
        "custom_or_invalid",
    ]
    assert "private-blocker-case-row" not in rendered
    assert "copied-preflight" not in rendered


def test_project_bible_pickup_validator_rejects_malformed_status_label_lists_without_leak():
    validator = _load_pickup_validator()
    status = copy.deepcopy(_paused_status_fixture())
    status["latest_preflight"]["state_mismatch_reasons"] = {
        "private": "C:\\Users\\private\\copied-preflight.json",
    }

    report = validator.build_report(
        status_payload=status,
        global_protections_report=_valid_global_protections_saved_artifacts_report(),
    )
    rendered = json.dumps(report, ensure_ascii=False)

    assert report["summary"]["ok"] is False
    assert report["summary"]["failed_ids"] == [
        "status_string_labels_are_known_if_present"
    ]
    label_check = next(
        check
        for check in report["checks"]
        if check["id"] == "status_string_labels_are_known_if_present"
    )
    assert label_check["actual"] == {
        "custom_or_invalid_fields": ["latest_preflight.state_mismatch_reasons"]
    }
    assert report["snapshot"]["latest_preflight"]["state_mismatch_reasons"] == [
        "custom_or_invalid"
    ]
    assert "copied-preflight" not in rendered


def test_project_bible_pickup_validator_rejects_candidate_dimension_activation():
    validator = _load_pickup_validator()
    status = copy.deepcopy(_paused_status_fixture())
    status["candidate_dimension_scope"]["active_in_autonomous_engine"] = True
    status["candidate_dimension_scope"]["ready_for_mass_grading"] = True

    report = validator.build_report(
        status_payload=status,
        global_protections_report=_valid_global_protections_saved_artifacts_report(),
    )

    assert report["summary"]["ok"] is False
    assert "candidate_dimensions_not_active" in report["summary"]["failed_ids"]


def test_project_bible_pickup_validator_rejects_active_loop_rubric_mixing():
    validator = _load_pickup_validator()
    status = copy.deepcopy(_paused_status_fixture())
    status["active_loop_scope"]["rubric_version"] = "v2"
    status["active_loop_scope"]["opt_in_rubric_versions_excluded"] = []
    status["active_loop_scope"]["rubric_version_mixing_allowed"] = True

    report = validator.build_report(
        status_payload=status,
        global_protections_report=_valid_global_protections_saved_artifacts_report(),
    )

    assert report["summary"]["ok"] is False
    assert "active_loop_uses_board_versions_without_mixing" in report["summary"]["failed_ids"]
    assert report["snapshot"]["active_loop_scope"] == {
        "runner": "rich_harness_lift.py",
        "candidate_dimension_sweep_active": False,
        "rubric_version": "v2",
        "opt_in_rubric_versions_excluded": [],
        "rubric_version_mixing_allowed": True,
        "harness_version": "h1",
        "opt_in_harness_versions_excluded": ["h2"],
        "harness_version_mixing_allowed": False,
    }


def test_project_bible_pickup_validator_rejects_active_loop_harness_mixing():
    validator = _load_pickup_validator()
    status = copy.deepcopy(_paused_status_fixture())
    status["active_loop_scope"]["harness_version"] = "h2"
    status["active_loop_scope"]["opt_in_harness_versions_excluded"] = []
    status["active_loop_scope"]["harness_version_mixing_allowed"] = True

    report = validator.build_report(
        status_payload=status,
        global_protections_report=_valid_global_protections_saved_artifacts_report(),
    )

    assert report["summary"]["ok"] is False
    assert "active_loop_uses_board_versions_without_mixing" in report["summary"]["failed_ids"]
    assert report["snapshot"]["active_loop_scope"] == {
        "runner": "rich_harness_lift.py",
        "candidate_dimension_sweep_active": False,
        "rubric_version": "v1",
        "opt_in_rubric_versions_excluded": ["v2"],
        "rubric_version_mixing_allowed": False,
        "harness_version": "h2",
        "opt_in_harness_versions_excluded": [],
        "harness_version_mixing_allowed": True,
    }


def test_project_bible_pickup_validator_rejects_unindexed_project_bible(tmp_path):
    validator = _load_pickup_validator()
    _write_minimal_pickup_tree(tmp_path)
    (tmp_path / "ROOT_FILES.md").write_text(
        "root files without pickup entry\n",
        encoding="utf-8",
    )

    report = validator.build_report(
        root=tmp_path,
        status_payload=_paused_status_fixture(),
        global_protections_report=_valid_global_protections_saved_artifacts_report(),
        validation_time=datetime(2026, 7, 2, tzinfo=timezone.utc),
    )

    assert report["summary"]["ok"] is False
    assert "project_bible_is_indexed_in_purpose_maps" in report["summary"]["failed_ids"]
    assert report["summary"]["check_count"] == 65


def test_project_bible_pickup_validator_rejects_copied_tree_missing_pickup_validator(tmp_path):
    validator = _load_pickup_validator()
    _write_minimal_pickup_tree(tmp_path)
    (tmp_path / "scripts" / "validate_project_bible_pickup.py").unlink()

    report = validator.build_report(
        root=tmp_path,
        status_payload=_paused_status_fixture(),
        global_protections_report=_valid_global_protections_saved_artifacts_report(),
        validation_time=datetime(2026, 7, 2, tzinfo=timezone.utc),
    )

    assert report["summary"]["ok"] is False
    assert report["summary"]["failed_ids"] == ["required_pickup_files_exist"]
    assert report["checks"][0]["actual"] == ["scripts/validate_project_bible_pickup.py"]
    assert report["summary"]["check_count"] == 49


def test_project_bible_pickup_validator_rejects_copied_tree_missing_global_validator(tmp_path):
    validator = _load_pickup_validator()
    _write_minimal_pickup_tree(tmp_path)
    (tmp_path / "scripts" / "validate_global_protections_saved_artifacts.py").unlink()

    report = validator.build_report(
        root=tmp_path,
        status_payload=_paused_status_fixture(),
        global_protections_report=_valid_global_protections_saved_artifacts_report(),
        validation_time=datetime(2026, 7, 2, tzinfo=timezone.utc),
    )

    assert report["summary"]["ok"] is False
    assert report["summary"]["failed_ids"] == ["required_pickup_files_exist"]
    assert report["checks"][0]["actual"] == [
        "scripts/validate_global_protections_saved_artifacts.py"
    ]
    assert report["summary"]["check_count"] == 49


def test_project_bible_pickup_validator_rejects_copied_tree_missing_rubric_v2_test(tmp_path):
    validator = _load_pickup_validator()
    _write_minimal_pickup_tree(tmp_path)
    (tmp_path / "tests" / "test_rubric_v2.py").unlink()

    report = validator.build_report(
        root=tmp_path,
        status_payload=_paused_status_fixture(),
        global_protections_report=_valid_global_protections_saved_artifacts_report(),
        validation_time=datetime(2026, 7, 2, tzinfo=timezone.utc),
    )

    assert report["summary"]["ok"] is False
    assert report["summary"]["failed_ids"] == ["required_pickup_files_exist"]
    assert report["checks"][0]["actual"] == ["tests/test_rubric_v2.py"]
    assert report["summary"]["check_count"] == 49


def test_project_bible_pickup_validator_rejects_copied_tree_missing_harness_v2_test(tmp_path):
    validator = _load_pickup_validator()
    _write_minimal_pickup_tree(tmp_path)
    (tmp_path / "tests" / "test_harness_v2.py").unlink()

    report = validator.build_report(
        root=tmp_path,
        status_payload=_paused_status_fixture(),
        global_protections_report=_valid_global_protections_saved_artifacts_report(),
        validation_time=datetime(2026, 7, 2, tzinfo=timezone.utc),
    )

    assert report["summary"]["ok"] is False
    assert report["summary"]["failed_ids"] == ["required_pickup_files_exist"]
    assert report["checks"][0]["actual"] == ["tests/test_harness_v2.py"]
    assert report["summary"]["check_count"] == 49


def test_project_bible_pickup_validator_rejects_copied_tree_missing_rich_harness_runner(tmp_path):
    validator = _load_pickup_validator()
    _write_minimal_pickup_tree(tmp_path)
    (tmp_path / "scripts" / "rich_harness_lift.py").unlink()

    report = validator.build_report(
        root=tmp_path,
        status_payload=_paused_status_fixture(),
        global_protections_report=_valid_global_protections_saved_artifacts_report(),
        validation_time=datetime(2026, 7, 2, tzinfo=timezone.utc),
    )

    assert report["summary"]["ok"] is False
    assert report["summary"]["failed_ids"] == ["required_pickup_files_exist"]
    assert report["checks"][0]["actual"] == ["scripts/rich_harness_lift.py"]
    assert report["summary"]["check_count"] == 49


def test_project_bible_pickup_validator_rejects_copied_tree_missing_benign_control_set(tmp_path):
    validator = _load_pickup_validator()
    _write_minimal_pickup_tree(tmp_path)
    (tmp_path / "configs" / "duecare" / "benchmarks" / "benign_control_prompts.json").unlink()

    report = validator.build_report(
        root=tmp_path,
        status_payload=_paused_status_fixture(),
        global_protections_report=_valid_global_protections_saved_artifacts_report(),
        validation_time=datetime(2026, 7, 2, tzinfo=timezone.utc),
    )

    assert report["summary"]["ok"] is False
    assert report["summary"]["failed_ids"] == ["required_pickup_files_exist"]
    assert report["checks"][0]["actual"] == [
        "configs/duecare/benchmarks/benign_control_prompts.json"
    ]
    assert report["summary"]["check_count"] == 49


def test_project_bible_pickup_validator_rejects_malformed_benign_control_set_without_leak(tmp_path):
    validator = _load_pickup_validator()
    _write_minimal_pickup_tree(tmp_path)
    bad_control_path = tmp_path / "configs" / "duecare" / "benchmarks" / "benign_control_prompts.json"
    bad_control_path.write_text(
        json.dumps({
            "domain": "trafficking",
            "intent": "custom-private-intent",
            "prompts": [
                {
                    "id": "BENIGN-0001",
                    "intent": "adversarial",
                    "text": "",
                },
                {
                    "id": "BENIGN-0001",
                    "intent": "benign",
                    "text": "private worker@example.invalid source should not leak",
                },
                {
                    "id": "BENIGN-0002",
                    "intent": "benign",
                    "text": "Synthetic worker help prompt with copied case 123456789.",
                },
                "private malformed row should not leak",
            ],
        }),
        encoding="utf-8",
    )

    report = validator.build_report(
        root=tmp_path,
        status_payload=_paused_status_fixture(),
        global_protections_report=_valid_global_protections_saved_artifacts_report(),
        validation_time=datetime(2026, 7, 2, tzinfo=timezone.utc),
    )
    rendered = json.dumps(report, ensure_ascii=False)

    assert report["summary"]["ok"] is False
    assert report["summary"]["failed_ids"] == ["benign_control_prompt_set_is_pickup_safe"]
    control_check = next(
        check
        for check in report["checks"]
        if check["id"] == "benign_control_prompt_set_is_pickup_safe"
    )
    assert control_check["actual"] == {
        "read_error": None,
        "doc_shape": "dict",
        "top_level_intent": "custom_or_invalid",
        "prompts_shape": "list",
        "prompt_count": 4,
        "row_shape_issue_count": 1,
        "missing_id_count": 0,
        "duplicate_id_count": 1,
        "non_benign_intent_count": 1,
        "blank_text_count": 1,
        "private_hint_count": 2,
    }
    assert "custom-private-intent" not in rendered
    assert "worker@example.invalid" not in rendered
    assert "123456789" not in rendered
    assert "private malformed row" not in rendered
    assert "BENIGN-0001" not in rendered
    assert str(tmp_path) not in rendered
    assert report["summary"]["check_count"] == 65


def test_project_bible_pickup_validator_rejects_copied_tree_missing_intent_split_test(tmp_path):
    validator = _load_pickup_validator()
    _write_minimal_pickup_tree(tmp_path)
    (tmp_path / "tests" / "test_intent_split.py").unlink()

    report = validator.build_report(
        root=tmp_path,
        status_payload=_paused_status_fixture(),
        global_protections_report=_valid_global_protections_saved_artifacts_report(),
        validation_time=datetime(2026, 7, 2, tzinfo=timezone.utc),
    )

    assert report["summary"]["ok"] is False
    assert report["summary"]["failed_ids"] == ["required_pickup_files_exist"]
    assert report["checks"][0]["actual"] == ["tests/test_intent_split.py"]
    assert report["summary"]["check_count"] == 49


def test_project_bible_pickup_validator_rejects_copied_tree_missing_sister_planning_test(tmp_path):
    validator = _load_pickup_validator()
    _write_minimal_pickup_tree(tmp_path)
    (tmp_path / "tests" / "test_validate_sister_project_planning.py").unlink()

    report = validator.build_report(
        root=tmp_path,
        status_payload=_paused_status_fixture(),
        global_protections_report=_valid_global_protections_saved_artifacts_report(),
        validation_time=datetime(2026, 7, 2, tzinfo=timezone.utc),
    )

    assert report["summary"]["ok"] is False
    assert report["summary"]["failed_ids"] == ["required_pickup_files_exist"]
    assert report["checks"][0]["actual"] == ["tests/test_validate_sister_project_planning.py"]
    assert report["summary"]["check_count"] == 49


def test_project_bible_pickup_validator_rejects_copied_tree_missing_autonomous_engine_test(tmp_path):
    validator = _load_pickup_validator()
    _write_minimal_pickup_tree(tmp_path)
    (tmp_path / "tests" / "test_autonomous_engine.py").unlink()

    report = validator.build_report(
        root=tmp_path,
        status_payload=_paused_status_fixture(),
        global_protections_report=_valid_global_protections_saved_artifacts_report(),
        validation_time=datetime(2026, 7, 2, tzinfo=timezone.utc),
    )

    assert report["summary"]["ok"] is False
    assert report["summary"]["failed_ids"] == ["required_pickup_files_exist"]
    assert report["checks"][0]["actual"] == ["tests/test_autonomous_engine.py"]
    assert report["summary"]["check_count"] == 49


def test_project_bible_pickup_validator_rejects_copied_tree_missing_global_helper(tmp_path):
    validator = _load_pickup_validator()
    _write_minimal_pickup_tree(tmp_path)
    missing_helper = "scripts/artifact_path_policy.py"
    (tmp_path / missing_helper).unlink()

    report = validator.build_report(
        root=tmp_path,
        status_payload=_paused_status_fixture(),
        global_protections_report=_valid_global_protections_saved_artifacts_report(),
        validation_time=datetime(2026, 7, 2, tzinfo=timezone.utc),
    )

    assert report["summary"]["ok"] is False
    assert report["summary"]["failed_ids"] == ["required_pickup_files_exist"]
    assert report["checks"][0]["actual"] == [missing_helper]
    assert report["summary"]["check_count"] == 49


def test_project_bible_pickup_validator_rejects_copied_tree_missing_autonomous_helper(tmp_path):
    validator = _load_pickup_validator()
    _write_minimal_pickup_tree(tmp_path)
    missing_helper = "scripts/_atomic.py"
    (tmp_path / missing_helper).unlink()

    report = validator.build_report(
        root=tmp_path,
        status_payload=_paused_status_fixture(),
        global_protections_report=_valid_global_protections_saved_artifacts_report(),
        validation_time=datetime(2026, 7, 2, tzinfo=timezone.utc),
    )

    assert report["summary"]["ok"] is False
    assert report["summary"]["failed_ids"] == ["required_pickup_files_exist"]
    assert report["checks"][0]["actual"] == [missing_helper]
    assert report["summary"]["check_count"] == 49


def test_project_bible_pickup_validator_rejects_unlisted_global_validator_direct_import(tmp_path):
    validator = _load_pickup_validator()
    _write_minimal_pickup_tree(tmp_path)
    global_validator_path = tmp_path / "scripts" / "validate_global_protections_saved_artifacts.py"
    global_validator_path.write_text(
        "import validate_global_protections_future_helper\n",
        encoding="utf-8",
    )

    report = validator.build_report(
        root=tmp_path,
        status_payload=_paused_status_fixture(),
        global_protections_report=_valid_global_protections_saved_artifacts_report(),
        validation_time=datetime(2026, 7, 2, tzinfo=timezone.utc),
    )

    assert report["summary"]["ok"] is False
    assert report["summary"]["failed_ids"] == [
        "global_saved_artifact_validator_direct_imports_are_required"
    ]
    import_check = next(
        check
        for check in report["checks"]
        if check["id"] == "global_saved_artifact_validator_direct_imports_are_required"
    )
    assert import_check["actual"] == {
        "parse_error": None,
        "missing_required_files": [
            "scripts/validate_global_protections_future_helper.py"
        ],
        "direct_local_import_count": 1,
    }
    assert report["summary"]["check_count"] == 65


def test_project_bible_pickup_validator_rejects_unlisted_pickup_validator_direct_import(tmp_path):
    validator = _load_pickup_validator()
    _write_minimal_pickup_tree(tmp_path)
    pickup_validator_path = tmp_path / "scripts" / "validate_project_bible_pickup.py"
    pickup_validator_path.write_text(
        "import build_project_bible_future_helper\n",
        encoding="utf-8",
    )

    report = validator.build_report(
        root=tmp_path,
        status_payload=_paused_status_fixture(),
        global_protections_report=_valid_global_protections_saved_artifacts_report(),
        validation_time=datetime(2026, 7, 2, tzinfo=timezone.utc),
    )

    assert report["summary"]["ok"] is False
    assert report["summary"]["failed_ids"] == [
        "project_bible_pickup_validator_direct_imports_are_required"
    ]
    import_check = next(
        check
        for check in report["checks"]
        if check["id"] == "project_bible_pickup_validator_direct_imports_are_required"
    )
    assert import_check["actual"] == {
        "parse_error": None,
        "missing_required_files": [
            "scripts/build_project_bible_future_helper.py"
        ],
        "direct_local_import_count": 1,
    }
    assert report["summary"]["check_count"] == 65


def test_project_bible_pickup_validator_rejects_unlisted_autonomous_engine_direct_import(tmp_path):
    validator = _load_pickup_validator()
    _write_minimal_pickup_tree(tmp_path)
    autonomous_engine_path = tmp_path / "scripts" / "autonomous_engine.py"
    autonomous_engine_path.write_text(
        "import build_autonomous_future_helper\n",
        encoding="utf-8",
    )

    report = validator.build_report(
        root=tmp_path,
        status_payload=_paused_status_fixture(),
        global_protections_report=_valid_global_protections_saved_artifacts_report(),
        validation_time=datetime(2026, 7, 2, tzinfo=timezone.utc),
    )

    assert report["summary"]["ok"] is False
    assert report["summary"]["failed_ids"] == [
        "autonomous_engine_direct_imports_are_required"
    ]
    import_check = next(
        check
        for check in report["checks"]
        if check["id"] == "autonomous_engine_direct_imports_are_required"
    )
    assert import_check["actual"] == {
        "parse_error": None,
        "missing_required_files": [
            "scripts/build_autonomous_future_helper.py"
        ],
        "direct_local_import_count": 1,
    }
    assert report["summary"]["check_count"] == 65


def test_project_bible_pickup_validator_rejects_unlisted_sister_validator_direct_import(tmp_path):
    validator = _load_pickup_validator()
    _write_minimal_pickup_tree(tmp_path)
    sister_validator_path = tmp_path / "scripts" / "validate_sister_project_planning.py"
    sister_validator_path.write_text(
        "import build_sister_project_future_helper\n",
        encoding="utf-8",
    )

    report = validator.build_report(
        root=tmp_path,
        status_payload=_paused_status_fixture(),
        global_protections_report=_valid_global_protections_saved_artifacts_report(),
        validation_time=datetime(2026, 7, 2, tzinfo=timezone.utc),
    )

    assert report["summary"]["ok"] is False
    assert report["summary"]["failed_ids"] == [
        "sister_project_validator_direct_imports_are_required"
    ]
    import_check = next(
        check
        for check in report["checks"]
        if check["id"] == "sister_project_validator_direct_imports_are_required"
    )
    assert import_check["actual"] == {
        "parse_error": None,
        "missing_required_files": [
            "scripts/build_sister_project_future_helper.py"
        ],
        "direct_local_import_count": 1,
    }
    assert report["summary"]["check_count"] == 65


def test_project_bible_pickup_validator_rejects_thin_root_project_bible(tmp_path):
    validator = _load_pickup_validator()
    _write_minimal_pickup_tree(tmp_path)
    (tmp_path / "PROJECT_BIBLE.md").write_text(
        "docs/codex/PROJECT_BIBLE.md\n"
        "reports/autonomous_engine.stop\n",
        encoding="utf-8",
    )

    report = validator.build_report(
        root=tmp_path,
        status_payload=_paused_status_fixture(),
        global_protections_report=_valid_global_protections_saved_artifacts_report(),
        validation_time=datetime(2026, 7, 2, tzinfo=timezone.utc),
    )

    assert report["summary"]["ok"] is False
    assert "root_project_bible_points_to_canonical_pickup" in report["summary"]["failed_ids"]
    root_bible_check = next(
        check
        for check in report["checks"]
        if check["id"] == "root_project_bible_points_to_canonical_pickup"
    )
    assert "Fable 5-style agents" in root_bible_check["actual"]
    assert "Read order for continuation sessions" in root_bible_check["actual"]
    assert report["summary"]["check_count"] == 65


def test_project_bible_pickup_validator_rejects_thin_plans_bridge(tmp_path):
    validator = _load_pickup_validator()
    _write_minimal_pickup_tree(tmp_path)
    (tmp_path / "Plans.md").write_text(
        "Re-read Plans.md and continue.\n",
        encoding="utf-8",
    )

    report = validator.build_report(
        root=tmp_path,
        status_payload=_paused_status_fixture(),
        global_protections_report=_valid_global_protections_saved_artifacts_report(),
        validation_time=datetime(2026, 7, 2, tzinfo=timezone.utc),
    )
    plans_check = next(
        check
        for check in report["checks"]
        if check["id"] == "plans_bridge_redirects_to_project_bible"
    )

    assert report["summary"]["ok"] is False
    assert "plans_bridge_redirects_to_project_bible" in report["summary"]["failed_ids"]
    assert "PROJECT_BIBLE.md" in plans_check["actual"]
    assert "normal preflight and review gates" in plans_check["actual"]
    assert report["summary"]["check_count"] == 65


def test_project_bible_pickup_validator_rejects_stale_claude_pickup_pointer(tmp_path):
    validator = _load_pickup_validator()
    _write_minimal_pickup_tree(tmp_path)
    (tmp_path / "CLAUDE.md").write_text(
        "Long-loop pickup brief (2026-07-01)\n"
        "docs/codex/PROJECT_BIBLE.md\n"
        ".claude/rules/05_project_bible_pickup.md\n"
        "Fable 5-style agents\n"
        "Current validation discipline\n"
        "treat older suite counts in this file as historical\n"
        "python -m pytest packages --collect-only -q\n",
        encoding="utf-8",
    )

    report = validator.build_report(
        root=tmp_path,
        status_payload=_paused_status_fixture(),
        global_protections_report=_valid_global_protections_saved_artifacts_report(),
        validation_time=datetime(2026, 7, 2, tzinfo=timezone.utc),
    )
    rendered = json.dumps(report, ensure_ascii=False)

    assert report["summary"]["ok"] is False
    assert report["summary"]["failed_ids"] == [
        "claude_points_to_project_bible_and_hidden_rule"
    ]
    claude_check = next(
        check
        for check in report["checks"]
        if check["id"] == "claude_points_to_project_bible_and_hidden_rule"
    )
    assert claude_check["actual"] == "missing pickup pointer detail"
    assert "2026-07-01" not in rendered
    assert str(tmp_path) not in rendered


def test_project_bible_pickup_validator_rejects_goal_command_without_root_project_bible(tmp_path):
    validator = _load_pickup_validator()
    _write_minimal_pickup_tree(tmp_path)
    (tmp_path / "docs/codex/goal_commands/13_project_bible_continuation.md").write_text(
        "Fable 5-style agents\n"
        "Read, in order: AGENTS.md, CLAUDE.md, .claude/rules/05_project_bible_pickup.md, "
        "docs/codex/PROJECT_BIBLE.md\n"
        "python scripts\\autonomous_engine.py --status\n"
        "lock.state: \"stale\"\n"
        "latest_preflight.saved_lock_state.state: \"stale\"\n"
        "active_loop_scope.rubric_version\n"
        "active_loop_scope.harness_version\n"
        "--rubric-version v2\n"
        "--harness-version h2\n"
        "--benign-control configs/duecare/benchmarks/benign_control_prompts.json\n"
        "excluded from the active leaderboard and autonomous loop\n"
        "must not be merged into the active\n"
        "public leaderboard, or autonomous loop\n"
        "Do not remove reports/autonomous_engine.stop\n"
        "do not start scripts/autonomous_engine.py in run/once mode\n"
        "do not call Ollama\n"
            "do not promote candidate dimensions\n"
            "python scripts\\validate_project_bible_pickup.py\n"
            "python -m pytest tests\\test_artifact_path_policy.py -q\n"
            "python -m pytest tests\\test_intent_split.py -q\n"
            "python -m pytest tests\\test_plan.py -q\n"
            "rich_harness_lift.py --plan\n"
            "NO model was called\n"
            "python scripts\\validate_sister_project_planning.py\n"
        "python scripts\\validate_global_protections_saved_artifacts.py\n"
        "python -m pytest tests\\test_validate_global_protections_saved_artifacts.py -q\n"
        "python -m pytest tests -q -k \"global_protections or regulatory_miss_pattern\"\n"
        "python scripts\\validate_public_surface.py\n"
        "python -m pytest packages --collect-only -q\n"
        "python scripts\\validate_main_kaggle_kernels.py\n"
        "py -3.12 scripts\\validate_kaggle_page_sources.py\n",
        encoding="utf-8",
    )

    report = validator.build_report(
        root=tmp_path,
        status_payload=_paused_status_fixture(),
        global_protections_report=_valid_global_protections_saved_artifacts_report(),
        validation_time=datetime(2026, 7, 2, tzinfo=timezone.utc),
    )

    assert report["summary"]["ok"] is False
    assert report["summary"]["failed_ids"] == [
        "goal_13_pins_status_safety_and_validation_commands"
    ]
    goal_check = next(
        check
        for check in report["checks"]
        if check["id"] == "goal_13_pins_status_safety_and_validation_commands"
    )
    assert goal_check["actual"] == [
        "Read, in order: AGENTS.md, CLAUDE.md, PROJECT_BIBLE.md"
    ]


def test_project_bible_pickup_validator_rejects_goal_command_without_fable_audience(tmp_path):
    validator = _load_pickup_validator()
    _write_minimal_pickup_tree(tmp_path)
    (tmp_path / "docs/codex/goal_commands/13_project_bible_continuation.md").write_text(
        "Use this when you want Claude Code, Codex, or a similar coding agent to resume.\n"
        "Read, in order: AGENTS.md, CLAUDE.md, PROJECT_BIBLE.md\n"
        "python scripts\\autonomous_engine.py --status\n"
        "lock.state: \"stale\"\n"
        "latest_preflight.saved_lock_state.state: \"stale\"\n"
        "active_loop_scope.rubric_version\n"
        "active_loop_scope.harness_version\n"
        "--rubric-version v2\n"
        "--harness-version h2\n"
        "--benign-control configs/duecare/benchmarks/benign_control_prompts.json\n"
        "excluded from the active leaderboard and autonomous loop\n"
        "must not be merged into the active\n"
        "public leaderboard, or autonomous loop\n"
        "Do not remove reports/autonomous_engine.stop\n"
        "do not start scripts/autonomous_engine.py in run/once mode\n"
        "do not call Ollama\n"
            "do not promote candidate dimensions\n"
            "python scripts\\validate_project_bible_pickup.py\n"
            "python -m pytest tests\\test_artifact_path_policy.py -q\n"
            "python -m pytest tests\\test_intent_split.py -q\n"
            "python -m pytest tests\\test_plan.py -q\n"
            "rich_harness_lift.py --plan\n"
            "NO model was called\n"
            "python scripts\\validate_sister_project_planning.py\n"
        "python scripts\\validate_global_protections_saved_artifacts.py\n"
        "python -m pytest tests\\test_validate_global_protections_saved_artifacts.py -q\n"
        "python -m pytest tests -q -k \"global_protections or regulatory_miss_pattern\"\n"
        "python scripts\\validate_public_surface.py\n"
        "python -m pytest packages --collect-only -q\n"
        "python scripts\\validate_main_kaggle_kernels.py\n"
        "py -3.12 scripts\\validate_kaggle_page_sources.py\n",
        encoding="utf-8",
    )

    report = validator.build_report(
        root=tmp_path,
        status_payload=_paused_status_fixture(),
        global_protections_report=_valid_global_protections_saved_artifacts_report(),
        validation_time=datetime(2026, 7, 2, tzinfo=timezone.utc),
    )

    assert report["summary"]["ok"] is False
    assert report["summary"]["failed_ids"] == [
        "goal_13_pins_status_safety_and_validation_commands"
    ]
    goal_check = next(
        check
        for check in report["checks"]
        if check["id"] == "goal_13_pins_status_safety_and_validation_commands"
    )
    assert goal_check["actual"] == ["Fable 5-style agents"]


def test_project_bible_pickup_validator_rejects_failed_sister_project_report():
    validator = _load_pickup_validator()
    sister_report = {
        "summary": {
            "ok": False,
            "check_count": 34,
            "failed_count": 1,
            "failed_ids": ["planning_ids_are_unique_within_namespaces"],
            "project_id": "global_protections_regulatory_benchmark",
            "project_status": "propose_only",
            "project_pack_id_match": True,
            "grounding_domain": "developing_country_worker_protections",
            "scheme_prompt_count": 12,
            "scheme_prompt_category_count": 12,
            "scheme_prompt_candidate_pattern_count": 10,
            "scheme_prompt_candidate_patterns_without_project_declaration_count": 0,
            "scheme_prompt_unresolved_scope_count": 12,
            "scheme_prompt_not_ready_count": 12,
            "scheme_prompt_categories_without_source_slots_count": 0,
            "queued_jurisdiction_scope_count": 5,
            "local_source_jurisdictions_without_scope_count": 0,
            "duplicate_id_issue_count": 1,
            "readiness_gate_missing_block_concept_count": 0,
            "source_admission_missing_concept_count": 0,
            "scored_capability_missing_concept_count": 0,
            "project_privacy_issue_count": 0,
            "jurisdiction_pack_privacy_issue_count": 0,
            "grounding_metadata_privacy_issue_count": 0,
            "grounding_source_privacy_issue_count": 0,
            "scheme_prompt_privacy_issue_count": 0,
        },
        "checks": [],
    }

    report = validator.build_report(
        status_payload=_paused_status_fixture(),
        sister_project_report=sister_report,
        global_protections_report=_valid_global_protections_saved_artifacts_report(),
    )

    assert report["summary"]["ok"] is False
    assert "sister_project_planning_validator_passes" in report["summary"]["failed_ids"]
    assert report["sister_project_planning"]["failed_ids"] == [
        "planning_ids_are_unique_within_namespaces",
    ]
    assert report["sister_project_planning"]["duplicate_id_issue_count"] == 1


def test_project_bible_pickup_validator_rejects_stale_sister_project_check_floor():
    validator = _load_pickup_validator()
    sister_report = validator.validate_sister_project_planning.build_report()
    sister_report["summary"]["check_count"] = 33

    report = validator.build_report(
        status_payload=_paused_status_fixture(),
        sister_project_report=sister_report,
        global_protections_report=_valid_global_protections_saved_artifacts_report(),
    )

    assert report["summary"]["ok"] is False
    assert "sister_project_planning_validator_passes" in report["summary"]["failed_ids"]
    assert report["sister_project_planning"]["check_count"] == 33


def test_project_bible_pickup_validator_rejects_boolean_sister_summary_counts():
    validator = _load_pickup_validator()
    sister_report = validator.validate_sister_project_planning.build_report()
    sister_report["summary"]["check_count"] = True
    sister_report["summary"]["failed_count"] = False
    sister_report["summary"]["duplicate_id_issue_count"] = False
    sister_report["summary"]["project_privacy_issue_count"] = False
    sister_report["summary"]["grounding_source_privacy_issue_count"] = False

    report = validator.build_report(
        status_payload=_paused_status_fixture(),
        sister_project_report=sister_report,
        global_protections_report=_valid_global_protections_saved_artifacts_report(),
    )

    assert report["summary"]["ok"] is False
    assert "sister_project_planning_validator_passes" in report["summary"]["failed_ids"]
    assert report["sister_project_planning"]["check_count"] is None
    assert report["sister_project_planning"]["failed_count"] is None
    assert report["sister_project_planning"]["duplicate_id_issue_count"] is None
    assert report["sister_project_planning"]["project_privacy_issue_count"] is None
    assert report["sister_project_planning"]["grounding_source_privacy_issue_count"] is None


def test_project_bible_pickup_validator_rejects_malformed_sister_failed_ids_without_leak():
    validator = _load_pickup_validator()
    sister_report = validator.validate_sister_project_planning.build_report()
    sister_report["summary"]["failed_ids"] = "C:\\Users\\private\\failed-checks.json"

    report = validator.build_report(
        status_payload=_paused_status_fixture(),
        sister_project_report=sister_report,
        global_protections_report=_valid_global_protections_saved_artifacts_report(),
    )
    rendered = json.dumps(report, ensure_ascii=False)

    assert report["summary"]["ok"] is False
    assert "sister_project_planning_validator_passes" in report["summary"]["failed_ids"]
    assert report["sister_project_planning"]["failed_ids"] == ["custom_or_invalid"]
    assert "failed-checks" not in rendered
    assert "C:\\Users" not in rendered


def test_project_bible_pickup_validator_redacts_private_sister_failed_id_entries():
    validator = _load_pickup_validator()
    sister_report = validator.validate_sister_project_planning.build_report()
    sister_report["summary"]["ok"] = False
    sister_report["summary"]["failed_count"] = 1
    sister_report["summary"]["failed_ids"] = [
        "planning_ids_are_unique_within_namespaces",
        "worker@example.invalid",
        "private_case_123456789",
        {"private": "C:\\Users\\private\\failed-checks.json"},
    ]

    report = validator.build_report(
        status_payload=_paused_status_fixture(),
        sister_project_report=sister_report,
        global_protections_report=_valid_global_protections_saved_artifacts_report(),
    )
    rendered = json.dumps(report, ensure_ascii=False)

    assert report["summary"]["ok"] is False
    assert "sister_project_planning_validator_passes" in report["summary"]["failed_ids"]
    assert report["sister_project_planning"]["failed_ids"] == [
        "planning_ids_are_unique_within_namespaces",
        "custom_or_invalid",
        "custom_or_invalid",
        "custom_or_invalid",
    ]
    assert "worker@example.invalid" not in rendered
    assert "private_case_123456789" not in rendered
    assert "123456789" not in rendered
    assert "failed-checks" not in rendered


def test_project_bible_pickup_validator_redacts_private_sister_identity_labels():
    validator = _load_pickup_validator()
    sister_report = validator.validate_sister_project_planning.build_report()
    sister_report["summary"]["project_id"] = "C:\\Users\\private\\project.json"
    sister_report["summary"]["project_status"] = "worker@example.invalid"
    sister_report["summary"]["grounding_domain"] = "file:/C:/Users/private/domain.json"

    report = validator.build_report(
        status_payload=_paused_status_fixture(),
        sister_project_report=sister_report,
        global_protections_report=_valid_global_protections_saved_artifacts_report(),
    )
    rendered = json.dumps(report, ensure_ascii=False)

    assert report["summary"]["ok"] is False
    assert "sister_project_planning_validator_passes" in report["summary"]["failed_ids"]
    assert report["sister_project_planning"]["project_id"] == "custom_or_invalid"
    assert report["sister_project_planning"]["project_status"] == "custom_or_invalid"
    assert report["sister_project_planning"]["grounding_domain"] == "custom_or_invalid"
    assert "project.json" not in rendered
    assert "worker@example.invalid" not in rendered
    assert "domain.json" not in rendered


def test_project_bible_pickup_validator_rejects_failed_global_saved_artifacts():
    validator = _load_pickup_validator()
    global_report = _valid_global_protections_saved_artifacts_report()
    global_report["summary"]["valid"] = False
    global_report["summary"]["failed_artifact_count"] = 1
    global_report["summary"]["total_failed_check_count"] = 2

    report = validator.build_report(
        status_payload=_paused_status_fixture(),
        global_protections_report=global_report,
    )

    assert report["summary"]["ok"] is False
    assert "global_protections_saved_artifacts_validator_passes" in report["summary"]["failed_ids"]
    assert report["global_protections_saved_artifacts"]["failed_artifact_count"] == 1


def test_project_bible_pickup_validator_rejects_boolean_global_summary_counts():
    validator = _load_pickup_validator()
    global_report = _valid_global_protections_saved_artifacts_report()
    summary = global_report["summary"]
    summary["artifact_count"] = True
    summary["valid_artifact_count"] = True
    summary["total_check_count"] = True
    summary["total_failed_check_count"] = False
    summary["curation_bundle_next_execution_phase_count"] = True
    summary["curation_bundle_next_phase_covered_actions"] = False
    summary["phase_coverage_mismatch_count"] = False
    summary["legal_anchor_channel_mismatch_count"] = False
    summary["readiness_blocker_mismatch_count"] = False

    report = validator.build_report(
        status_payload=_paused_status_fixture(),
        global_protections_report=global_report,
    )

    assert report["summary"]["ok"] is False
    assert "global_protections_saved_artifacts_validator_passes" in report["summary"]["failed_ids"]
    assert report["global_protections_saved_artifacts"]["artifact_count"] is None
    assert report["global_protections_saved_artifacts"]["valid_artifact_count"] is None
    assert report["global_protections_saved_artifacts"]["total_check_count"] is None
    assert report["global_protections_saved_artifacts"]["total_failed_check_count"] is None
    assert report["global_protections_saved_artifacts"]["next_phase_coverage"] == {
        "phase_count": None,
        "covered_actions": None,
    }
    assert report["global_protections_saved_artifacts"]["phase_coverage_mismatch_count"] is None
    assert report["global_protections_saved_artifacts"]["legal_anchor_channel_mismatch_count"] is None
    assert report["global_protections_saved_artifacts"]["readiness_blocker_mismatch_count"] is None


def test_project_bible_pickup_validator_rejects_thin_global_saved_artifacts_summary():
    validator = _load_pickup_validator()
    global_report = {
        "summary": {
            "valid": True,
            "artifact_count": 13,
            "failed_artifact_count": 0,
            "total_failed_check_count": 0,
            "suite_failed_check_count": 0,
            "phase_coverage_mismatch_count": 0,
            "ready_for_comparable_scoring": False,
        },
    }

    report = validator.build_report(
        status_payload=_paused_status_fixture(),
        global_protections_report=global_report,
    )

    assert report["summary"]["ok"] is False
    assert "global_protections_saved_artifacts_validator_passes" in report["summary"]["failed_ids"]
    assert report["global_protections_saved_artifacts"]["next_phase_coverage"] == {
        "phase_count": None,
        "covered_actions": None,
    }
    assert report["global_protections_saved_artifacts"]["total_check_count"] is None
    assert report["global_protections_saved_artifacts"]["legal_anchor_channel_mismatch_count"] is None


def test_project_bible_pickup_validator_embedded_sister_report_uses_supplied_root(tmp_path):
    validator = _load_pickup_validator()
    _write_minimal_pickup_tree(tmp_path, mismatched_pack_project_id=True)

    report = validator.build_report(
        root=tmp_path,
        status_payload=_paused_status_fixture(),
        global_protections_report=_valid_global_protections_saved_artifacts_report(),
    )

    assert report["summary"]["ok"] is False
    assert "sister_project_planning_validator_passes" in report["summary"]["failed_ids"]
    assert "project_and_jurisdiction_pack_ids_match" in report["sister_project_planning"]["failed_ids"]


def test_project_bible_pickup_validator_summarizes_hidden_handoff_without_paths(tmp_path):
    validator = _load_pickup_validator()
    handoff_artifact = {
        "version": "2.0.0",
        "legacy_version": "1.0.0",
        "artifactType": "structured-handoff",
        "timestamp": "2026-07-01T00:00:00Z",
        "previous_state": {
            "session_state": {"state": "stopped"},
            "plan_counts": {"recent_edits": 2},
        },
        "next_action": {"source": "fallback", "priority": "normal"},
        "open_risks": [
            {
                "severity": "medium",
                "kind": "verification",
                "summary": "private path should not leak",
                "detail": "C:\\Users\\private\\worker-case-row.csv",
            },
            {"severity": "low", "summary": "another aggregate-only risk"},
        ],
        "failed_checks": None,
        "context_reset": {"recommended": True},
        "decision_log": [
            {
                "decision": "canonical_handoff_artifact_written",
                "rationale": "private C:\\Users\\private\\decision-log.jsonl",
            },
        ],
        "continuity": {
            "plugin_first_workflow": True,
            "resume_aware_effort_continuity": True,
            "effort_hint": "medium",
            "summary": "private continuity detail C:\\Users\\private\\continuity.txt",
        },
        "recentEdits": ["C:\\Users\\private\\case-a.txt", "reports/private-case.csv"],
    }
    _write_minimal_pickup_tree(tmp_path, handoff_artifact=handoff_artifact)

    report = validator.build_report(
        root=tmp_path,
        status_payload=_paused_status_fixture(),
        global_protections_report=_valid_global_protections_saved_artifacts_report(),
    )
    rendered = json.dumps(report, ensure_ascii=False)

    assert report["summary"]["ok"] is True
    assert report["claude_handoff"] == {
        "exists": True,
        "artifact_type": "structured-handoff",
        "version": "2.0.0",
        "legacy_version": "1.0.0",
        "timestamp_present": True,
        "timestamp_valid": True,
        "validated_after_handoff": True,
        "previous_state_shape": "dict",
        "session_state_shape": "dict",
        "plan_counts_shape": "dict",
        "plan_count_key_counts": {"recent_edits": 1},
        "plan_count_value_shape_counts": {"int": 1},
        "next_action_shape": "dict",
        "decision_log_shape": "list",
        "decision_log_count": 1,
        "decision_log_entry_shape_counts": {"dict": 1},
        "decision_log_decision_counts": {"canonical_handoff_artifact_written": 1},
        "decision_log_actor_counts": {"absent": 1},
        "decision_log_timestamp_shape_counts": {"absent": 1},
        "continuity_shape": "dict",
        "continuity_plugin_first_workflow_shape": "bool",
        "continuity_plugin_first_workflow": True,
        "continuity_resume_aware_effort_continuity_shape": "bool",
        "continuity_resume_aware_effort_continuity": True,
        "continuity_effort_hint": "medium",
        "session_state": "stopped",
        "next_action_source": "fallback",
        "next_action_priority": "normal",
        "open_risk_count": 2,
        "plan_items_shape": "absent",
        "plan_item_count": None,
        "wip_tasks_shape": "absent",
        "wip_task_count": None,
        "open_risks_shape": "list",
        "open_risk_severity_counts": {"low": 1, "medium": 1},
        "open_risk_kind_counts": {"absent": 1, "verification": 1},
        "blocking_open_risk_count": 0,
        "failed_checks_shape": "null",
        "failed_checks_present": False,
        "context_reset_recommended": True,
        "context_reset_shape": "dict",
        "context_reset_recommended_shape": "bool",
        "context_reset_policy_shape": "absent",
        "context_reset_policy_mode": None,
        "context_reset_policy_dry_run_shape": "absent",
        "context_reset_policy_thresholds_shape": "absent",
        "context_reset_threshold_key_counts": {},
        "context_reset_threshold_value_shape_counts": {},
        "context_reset_counters_shape": "absent",
        "context_reset_counter_key_counts": {},
        "context_reset_counter_value_shape_counts": {},
        "context_reset_reasons_shape": "absent",
        "context_reset_reason_entry_shape_counts": {},
        "context_reset_candidates_shape": "absent",
        "context_reset_candidate_entry_shape_counts": {},
        "context_reset_candidate_triggered_shape_counts": {},
        "context_reset_candidate_triggered_value_counts": {},
        "context_reset_candidate_key_counts": {},
        "context_reset_candidate_actual_shape_counts": {},
        "context_reset_candidate_threshold_shape_counts": {},
        "context_reset_candidate_trigger_consistency_counts": {},
        "recent_edits_shape": "list",
        "recent_edit_count": 2,
    }
    assert "worker-case-row" not in rendered
    assert "case-a.txt" not in rendered
    assert "decision-log" not in rendered
    assert "continuity.txt" not in rendered
    assert str(tmp_path) not in rendered


def test_project_bible_pickup_validator_rejects_boolean_hidden_recent_edit_count(tmp_path):
    validator = _load_pickup_validator()
    handoff_artifact = {
        "artifactType": "structured-handoff",
        "timestamp": "2026-07-01T00:00:00Z",
        "previous_state": {
            "session_state": {"state": "stopped"},
            "plan_counts": {"recent_edits": True},
        },
        "open_risks": [],
        "failed_checks": None,
        "recentEdits": ["C:\\Users\\private\\case-a.txt", "reports/private-case.csv"],
    }
    _write_minimal_pickup_tree(tmp_path, handoff_artifact=handoff_artifact)

    report = validator.build_report(
        root=tmp_path,
        status_payload=_paused_status_fixture(),
        global_protections_report=_valid_global_protections_saved_artifacts_report(),
    )
    rendered = json.dumps(report, ensure_ascii=False)

    assert report["summary"]["ok"] is False
    assert report["summary"]["failed_ids"] == [
        "claude_handoff_plan_count_keys_and_values_are_known_if_present"
    ]
    assert report["claude_handoff"]["plan_count_key_counts"] == {"recent_edits": 1}
    assert report["claude_handoff"]["plan_count_value_shape_counts"] == {
        "custom_or_invalid": 1,
    }
    assert report["claude_handoff"]["recent_edits_shape"] == "list"
    assert report["claude_handoff"]["recent_edit_count"] == 2
    assert "case-a.txt" not in rendered
    assert str(tmp_path) not in rendered


def test_project_bible_pickup_validator_rejects_malformed_hidden_plan_counts_without_leak(tmp_path):
    validator = _load_pickup_validator()
    handoff_artifact = {
        "artifactType": "structured-handoff",
        "timestamp": "2026-07-01T00:00:00Z",
        "previous_state": {
            "session_state": {"state": "stopped"},
            "plan_counts": {
                "privatePlanCount": "C:\\Users\\private\\plan-count.txt",
                "total": 2,
                "wip": "worker@example.invalid",
            },
        },
        "open_risks": [],
        "failed_checks": None,
        "recentEdits": ["reports/safe-count-source.txt"],
    }
    _write_minimal_pickup_tree(tmp_path, handoff_artifact=handoff_artifact)

    report = validator.build_report(
        root=tmp_path,
        status_payload=_paused_status_fixture(),
        global_protections_report=_valid_global_protections_saved_artifacts_report(),
    )
    rendered = json.dumps(report, ensure_ascii=False)

    assert report["summary"]["ok"] is False
    assert report["summary"]["failed_ids"] == [
        "claude_handoff_plan_count_keys_and_values_are_known_if_present"
    ]
    assert report["claude_handoff"]["plan_counts_shape"] == "dict"
    assert report["claude_handoff"]["plan_count_key_counts"] == {
        "custom_or_invalid": 1,
        "total": 1,
        "wip": 1,
    }
    assert report["claude_handoff"]["plan_count_value_shape_counts"] == {
        "custom_or_invalid": 2,
        "int": 1,
    }
    assert report["claude_handoff"]["recent_edit_count"] == 1
    assert "privatePlanCount" not in rendered
    assert "plan-count.txt" not in rendered
    assert "worker@example.invalid" not in rendered
    assert "safe-count-source" not in rendered
    assert "C:\\Users" not in rendered
    assert str(tmp_path) not in rendered


def test_project_bible_pickup_validator_rejects_malformed_hidden_state_containers_without_leak(tmp_path):
    validator = _load_pickup_validator()
    fixtures = [
        (
            tmp_path / "top-level",
            {
                "artifactType": "structured-handoff",
                "timestamp": "2026-07-01T00:00:00Z",
                "previous_state": "C:\\Users\\private\\previous-state.json",
                "next_action": {"source": "fallback", "priority": "normal"},
                "open_risks": [],
                "failed_checks": None,
                "context_reset": {"recommended": False},
            },
            {
                "previous_state_shape": "custom_or_invalid",
                "session_state_shape": "absent",
                "plan_counts_shape": "absent",
                "next_action_shape": "dict",
            },
            ["previous-state"],
        ),
        (
            tmp_path / "nested",
            {
                "artifactType": "structured-handoff",
                "timestamp": "2026-07-01T00:00:00Z",
                "previous_state": {
                    "session_state": "C:\\Users\\private\\session-state.json",
                    "plan_counts": "C:\\Users\\private\\plan-counts.json",
                },
                "next_action": "C:\\Users\\private\\next-action.json",
                "open_risks": [],
                "failed_checks": None,
                "context_reset": {"recommended": False},
            },
            {
                "previous_state_shape": "dict",
                "session_state_shape": "custom_or_invalid",
                "plan_counts_shape": "custom_or_invalid",
                "next_action_shape": "custom_or_invalid",
            },
            ["session-state", "plan-counts", "next-action"],
        ),
    ]

    for root, handoff_artifact, expected_shapes, forbidden_fragments in fixtures:
        _write_minimal_pickup_tree(root, handoff_artifact=handoff_artifact)

        report = validator.build_report(
            root=root,
            status_payload=_paused_status_fixture(),
            global_protections_report=_valid_global_protections_saved_artifacts_report(),
            validation_time=datetime(2026, 7, 2, tzinfo=timezone.utc),
        )
        rendered = json.dumps(report, ensure_ascii=False)

        assert report["summary"]["ok"] is False
        assert report["summary"]["failed_ids"] == [
            "claude_handoff_nested_state_containers_are_objects_if_present"
        ]
        for key, expected in expected_shapes.items():
            assert report["claude_handoff"][key] == expected
        for fragment in forbidden_fragments:
            assert fragment not in rendered
        assert "C:\\Users" not in rendered
        assert str(root) not in rendered


def test_project_bible_pickup_validator_rejects_malformed_hidden_decision_log_without_leak(tmp_path):
    validator = _load_pickup_validator()
    handoff_artifact = {
        "artifactType": "structured-handoff",
        "timestamp": "2026-07-01T00:00:00Z",
        "previous_state": {"session_state": {"state": "stopped"}},
        "next_action": {"source": "fallback", "priority": "normal"},
        "open_risks": [],
        "failed_checks": None,
        "context_reset": {"recommended": False},
        "decision_log": "C:\\Users\\private\\decision-log.jsonl",
    }
    _write_minimal_pickup_tree(tmp_path, handoff_artifact=handoff_artifact)

    report = validator.build_report(
        root=tmp_path,
        status_payload=_paused_status_fixture(),
        global_protections_report=_valid_global_protections_saved_artifacts_report(),
        validation_time=datetime(2026, 7, 2, tzinfo=timezone.utc),
    )
    rendered = json.dumps(report, ensure_ascii=False)

    assert report["summary"]["ok"] is False
    assert report["summary"]["failed_ids"] == [
        "claude_handoff_decision_log_is_list_if_present"
    ]
    assert report["claude_handoff"]["decision_log_shape"] == "custom_or_invalid"
    assert report["claude_handoff"]["decision_log_count"] == 0
    assert report["claude_handoff"]["decision_log_entry_shape_counts"] == {}
    assert report["claude_handoff"]["decision_log_decision_counts"] == {}
    assert "decision-log" not in rendered
    assert "C:\\Users" not in rendered
    assert str(tmp_path) not in rendered


def test_project_bible_pickup_validator_rejects_malformed_hidden_decision_log_entries_without_leak(tmp_path):
    validator = _load_pickup_validator()
    handoff_artifact = {
        "artifactType": "structured-handoff",
        "timestamp": "2026-07-01T00:00:00Z",
        "previous_state": {"session_state": {"state": "stopped"}},
        "next_action": {"source": "fallback", "priority": "normal"},
        "open_risks": [],
        "failed_checks": None,
        "context_reset": {"recommended": False},
        "decision_log": [
            "C:\\Users\\private\\decision-entry.json",
            {
                "decision": "private-decision-worker@example.invalid",
                "rationale": "private rationale C:\\Users\\private\\decision-log.jsonl",
            },
        ],
    }
    _write_minimal_pickup_tree(tmp_path, handoff_artifact=handoff_artifact)

    report = validator.build_report(
        root=tmp_path,
        status_payload=_paused_status_fixture(),
        global_protections_report=_valid_global_protections_saved_artifacts_report(),
        validation_time=datetime(2026, 7, 2, tzinfo=timezone.utc),
    )
    rendered = json.dumps(report, ensure_ascii=False)

    assert report["summary"]["ok"] is False
    assert report["summary"]["failed_ids"] == [
        "claude_handoff_decision_log_entries_are_known_if_present"
    ]
    assert report["claude_handoff"]["decision_log_shape"] == "list"
    assert report["claude_handoff"]["decision_log_count"] == 2
    assert report["claude_handoff"]["decision_log_entry_shape_counts"] == {
        "custom_or_invalid": 1,
        "dict": 1,
    }
    assert report["claude_handoff"]["decision_log_decision_counts"] == {
        "custom_or_invalid": 2,
    }
    assert "private-decision" not in rendered
    assert "private rationale" not in rendered
    assert "decision-entry" not in rendered
    assert "decision-log" not in rendered
    assert "worker@example.invalid" not in rendered
    assert "C:\\Users" not in rendered
    assert str(tmp_path) not in rendered


def test_project_bible_pickup_validator_rejects_malformed_hidden_decision_log_actor_and_timestamp_without_leak(tmp_path):
    validator = _load_pickup_validator()
    handoff_artifact = {
        "artifactType": "structured-handoff",
        "timestamp": "2026-07-01T00:00:00Z",
        "previous_state": {"session_state": {"state": "stopped"}},
        "next_action": {"source": "fallback", "priority": "normal"},
        "open_risks": [],
        "failed_checks": None,
        "context_reset": {"recommended": False},
        "decision_log": [
            {
                "timestamp": "private timestamp C:\\Users\\private\\decision-time.jsonl",
                "actor": "private-actor-worker@example.invalid",
                "decision": "canonical_handoff_artifact_written",
                "rationale": "private rationale C:\\Users\\private\\decision-log.jsonl",
            },
        ],
    }
    _write_minimal_pickup_tree(tmp_path, handoff_artifact=handoff_artifact)

    report = validator.build_report(
        root=tmp_path,
        status_payload=_paused_status_fixture(),
        global_protections_report=_valid_global_protections_saved_artifacts_report(),
        validation_time=datetime(2026, 7, 2, tzinfo=timezone.utc),
    )
    rendered = json.dumps(report, ensure_ascii=False)

    assert report["summary"]["ok"] is False
    assert report["summary"]["failed_ids"] == [
        "claude_handoff_decision_log_actor_and_timestamp_labels_are_known_if_present"
    ]
    assert report["claude_handoff"]["decision_log_shape"] == "list"
    assert report["claude_handoff"]["decision_log_count"] == 1
    assert report["claude_handoff"]["decision_log_entry_shape_counts"] == {"dict": 1}
    assert report["claude_handoff"]["decision_log_decision_counts"] == {
        "canonical_handoff_artifact_written": 1,
    }
    assert report["claude_handoff"]["decision_log_actor_counts"] == {
        "custom_or_invalid": 1,
    }
    assert report["claude_handoff"]["decision_log_timestamp_shape_counts"] == {
        "custom_or_invalid": 1,
    }
    assert "private timestamp" not in rendered
    assert "private-actor" not in rendered
    assert "worker@example.invalid" not in rendered
    assert "decision-time" not in rendered
    assert "private rationale" not in rendered
    assert "decision-log" not in rendered
    assert "C:\\Users" not in rendered
    assert str(tmp_path) not in rendered


def test_project_bible_pickup_validator_rejects_malformed_hidden_task_containers_without_leak(tmp_path):
    validator = _load_pickup_validator()
    handoff_artifact = {
        "artifactType": "structured-handoff",
        "timestamp": "2026-07-01T00:00:00Z",
        "previous_state": {"session_state": {"state": "stopped"}},
        "next_action": {"source": "fallback", "priority": "normal"},
        "open_risks": [],
        "failed_checks": None,
        "context_reset": {"recommended": False},
        "planItems": "C:\\Users\\private\\plan-items.json",
        "wipTasks": {"task": "worker@example.invalid"},
    }
    _write_minimal_pickup_tree(tmp_path, handoff_artifact=handoff_artifact)

    report = validator.build_report(
        root=tmp_path,
        status_payload=_paused_status_fixture(),
        global_protections_report=_valid_global_protections_saved_artifacts_report(),
        validation_time=datetime(2026, 7, 2, tzinfo=timezone.utc),
    )
    rendered = json.dumps(report, ensure_ascii=False)

    assert report["summary"]["ok"] is False
    assert report["summary"]["failed_ids"] == [
        "claude_handoff_task_containers_are_lists_if_present"
    ]
    assert report["claude_handoff"]["plan_items_shape"] == "custom_or_invalid"
    assert report["claude_handoff"]["plan_item_count"] is None
    assert report["claude_handoff"]["wip_tasks_shape"] == "custom_or_invalid"
    assert report["claude_handoff"]["wip_task_count"] is None
    assert "plan-items" not in rendered
    assert "worker@example.invalid" not in rendered
    assert "C:\\Users" not in rendered
    assert str(tmp_path) not in rendered


def test_project_bible_pickup_validator_rejects_malformed_hidden_continuity_without_leak(tmp_path):
    validator = _load_pickup_validator()
    handoff_artifact = {
        "artifactType": "structured-handoff",
        "timestamp": "2026-07-01T00:00:00Z",
        "previous_state": {"session_state": {"state": "stopped"}},
        "next_action": {"source": "fallback", "priority": "normal"},
        "open_risks": [],
        "failed_checks": None,
        "context_reset": {"recommended": False},
        "continuity": {
            "plugin_first_workflow": "C:\\Users\\private\\plugin-state.json",
            "resume_aware_effort_continuity": "worker@example.invalid",
            "effort_hint": "private-effort-worker-case",
            "summary": "private continuity text should not leak",
        },
    }
    _write_minimal_pickup_tree(tmp_path, handoff_artifact=handoff_artifact)

    report = validator.build_report(
        root=tmp_path,
        status_payload=_paused_status_fixture(),
        global_protections_report=_valid_global_protections_saved_artifacts_report(),
        validation_time=datetime(2026, 7, 2, tzinfo=timezone.utc),
    )
    rendered = json.dumps(report, ensure_ascii=False)

    assert report["summary"]["ok"] is False
    assert report["summary"]["failed_ids"] == [
        "claude_handoff_continuity_shape_and_labels_are_known_if_present"
    ]
    assert report["claude_handoff"]["continuity_shape"] == "dict"
    assert report["claude_handoff"]["continuity_plugin_first_workflow_shape"] == "custom_or_invalid"
    assert report["claude_handoff"]["continuity_resume_aware_effort_continuity_shape"] == "custom_or_invalid"
    assert report["claude_handoff"]["continuity_effort_hint"] == "custom_or_invalid"
    assert "plugin-state" not in rendered
    assert "worker@example.invalid" not in rendered
    assert "private-effort" not in rendered
    assert "private continuity text" not in rendered
    assert "C:\\Users" not in rendered
    assert str(tmp_path) not in rendered


def test_project_bible_pickup_validator_rejects_malformed_hidden_recent_edits_without_leak(tmp_path):
    validator = _load_pickup_validator()
    handoff_artifact = {
        "artifactType": "structured-handoff",
        "timestamp": "2026-07-01T00:00:00Z",
        "previous_state": {"session_state": {"state": "stopped"}},
        "open_risks": [],
        "failed_checks": None,
        "context_reset": {"recommended": False},
        "recentEdits": "C:\\Users\\private\\case-a.txt",
    }
    _write_minimal_pickup_tree(tmp_path, handoff_artifact=handoff_artifact)

    report = validator.build_report(
        root=tmp_path,
        status_payload=_paused_status_fixture(),
        global_protections_report=_valid_global_protections_saved_artifacts_report(),
        validation_time=datetime(2026, 7, 2, tzinfo=timezone.utc),
    )
    rendered = json.dumps(report, ensure_ascii=False)

    assert report["summary"]["ok"] is False
    assert report["summary"]["failed_ids"] == [
        "claude_handoff_recent_edits_are_list_if_present"
    ]
    assert report["claude_handoff"]["recent_edits_shape"] == "custom_or_invalid"
    assert report["claude_handoff"]["recent_edit_count"] is None
    assert "case-a.txt" not in rendered
    assert "C:\\Users" not in rendered
    assert str(tmp_path) not in rendered


def test_project_bible_pickup_validator_rejects_malformed_hidden_open_risks_without_leak(tmp_path):
    validator = _load_pickup_validator()
    handoff_artifact = {
        "artifactType": "structured-handoff",
        "timestamp": "2026-07-01T00:00:00Z",
        "previous_state": {"session_state": {"state": "stopped"}},
        "open_risks": {
            "severity": "high",
            "summary": "private malformed risk should not leak",
            "detail": "C:\\Users\\private\\case-log.txt",
        },
        "failed_checks": None,
        "context_reset": {"recommended": False},
    }
    _write_minimal_pickup_tree(tmp_path, handoff_artifact=handoff_artifact)

    report = validator.build_report(
        root=tmp_path,
        status_payload=_paused_status_fixture(),
        global_protections_report=_valid_global_protections_saved_artifacts_report(),
        validation_time=datetime(2026, 7, 2, tzinfo=timezone.utc),
    )
    rendered = json.dumps(report, ensure_ascii=False)

    assert report["summary"]["ok"] is False
    assert "claude_handoff_open_risks_are_list_if_present" in report["summary"]["failed_ids"]
    assert report["claude_handoff"]["open_risks_shape"] == "custom_or_invalid"
    assert report["claude_handoff"]["open_risk_count"] == 0
    assert report["claude_handoff"]["open_risk_severity_counts"] == {}
    assert "private malformed risk" not in rendered
    assert "case-log.txt" not in rendered
    assert str(tmp_path) not in rendered


def test_project_bible_pickup_validator_rejects_high_or_critical_hidden_open_risks_without_leak(tmp_path):
    validator = _load_pickup_validator()
    handoff_artifact = {
        "artifactType": "structured-handoff",
        "timestamp": "2026-07-01T00:00:00Z",
        "previous_state": {"session_state": {"state": "stopped"}},
        "open_risks": [
            {
                "severity": "high",
                "summary": "private high-risk detail should not leak",
                "detail": "C:\\Users\\private\\case-log.txt",
            },
            {
                "severity": "critical",
                "summary": "private critical-risk detail should not leak",
            },
        ],
        "failed_checks": None,
        "context_reset": {"recommended": False},
    }
    _write_minimal_pickup_tree(tmp_path, handoff_artifact=handoff_artifact)

    report = validator.build_report(
        root=tmp_path,
        status_payload=_paused_status_fixture(),
        global_protections_report=_valid_global_protections_saved_artifacts_report(),
        validation_time=datetime(2026, 7, 2, tzinfo=timezone.utc),
    )
    rendered = json.dumps(report, ensure_ascii=False)

    assert report["summary"]["ok"] is False
    assert "claude_handoff_has_no_high_or_critical_open_risks_if_present" in report["summary"]["failed_ids"]
    assert report["claude_handoff"]["open_risk_count"] == 2
    assert report["claude_handoff"]["blocking_open_risk_count"] == 2
    assert report["claude_handoff"]["open_risk_severity_counts"] == {"critical": 1, "high": 1}
    assert "private high-risk detail" not in rendered
    assert "private critical-risk detail" not in rendered
    assert "case-log.txt" not in rendered
    assert str(tmp_path) not in rendered


def test_project_bible_pickup_validator_rejects_future_hidden_handoff_timestamp_without_leak(tmp_path):
    validator = _load_pickup_validator()
    handoff_artifact = {
        "artifactType": "structured-handoff",
        "timestamp": "2026-07-03T00:00:00Z",
        "previous_state": {"session_state": {"state": "stopped"}},
        "open_risks": [],
        "failed_checks": None,
        "context_reset": {"recommended": False},
    }
    _write_minimal_pickup_tree(tmp_path, handoff_artifact=handoff_artifact)

    report = validator.build_report(
        root=tmp_path,
        status_payload=_paused_status_fixture(),
        global_protections_report=_valid_global_protections_saved_artifacts_report(),
        validation_time=datetime(2026, 7, 2, tzinfo=timezone.utc),
    )
    rendered = json.dumps(report, ensure_ascii=False)

    assert report["summary"]["ok"] is False
    assert "claude_handoff_not_newer_than_validation_if_present" in report["summary"]["failed_ids"]
    assert "claude_handoff_timestamp_valid_if_present" not in report["summary"]["failed_ids"]
    assert report["claude_handoff"]["timestamp_valid"] is True
    assert report["claude_handoff"]["validated_after_handoff"] is False
    assert "2026-07-03" not in rendered
    assert str(tmp_path) not in rendered


def test_project_bible_pickup_validator_sanitizes_custom_hidden_handoff_labels(tmp_path):
    validator = _load_pickup_validator()
    handoff_artifact = {
        "version": "private-version-worker@example.invalid",
        "legacy_version": "s3:/private-bucket/legacy-version",
        "artifactType": "private-artifact-type-C:\\Users\\private\\handoff.json",
        "timestamp": "2026-07-01T00:00:00Z",
        "previous_state": {
            "session_state": {"state": "private-state-worker-123"},
            "plan_counts": {"recent_edits": 1},
        },
        "next_action": {
            "source": "private-source-case-log",
            "priority": "private-priority-worker-name",
        },
        "open_risks": [
            {
                "severity": "private-risk-severity-case-row",
                "kind": "private-risk-kind-worker@example.invalid",
                "summary": "private risk text should not leak",
            },
        ],
        "failed_checks": None,
        "context_reset": {"recommended": False},
        "recentEdits": ["C:\\Users\\private\\case-a.txt"],
    }
    _write_minimal_pickup_tree(tmp_path, handoff_artifact=handoff_artifact)

    report = validator.build_report(
        root=tmp_path,
        status_payload=_paused_status_fixture(),
        global_protections_report=_valid_global_protections_saved_artifacts_report(),
        validation_time=datetime(2026, 7, 2, tzinfo=timezone.utc),
    )
    rendered = json.dumps(report, ensure_ascii=False)

    assert report["summary"]["ok"] is False
    assert "claude_handoff_artifact_type_is_known_if_present" in report["summary"]["failed_ids"]
    assert "claude_handoff_versions_are_known_if_present" in report["summary"]["failed_ids"]
    assert "claude_handoff_state_and_next_action_labels_are_known_if_present" in report["summary"]["failed_ids"]
    assert "claude_handoff_open_risk_severities_are_known_if_present" in report["summary"]["failed_ids"]
    assert "claude_handoff_open_risk_kinds_are_known_if_present" in report["summary"]["failed_ids"]
    assert report["claude_handoff"] == {
        "exists": True,
        "artifact_type": "custom_or_invalid",
        "version": "custom_or_invalid",
        "legacy_version": "custom_or_invalid",
        "timestamp_present": True,
        "timestamp_valid": True,
        "validated_after_handoff": True,
        "previous_state_shape": "dict",
        "session_state_shape": "dict",
        "plan_counts_shape": "dict",
        "plan_count_key_counts": {"recent_edits": 1},
        "plan_count_value_shape_counts": {"int": 1},
        "next_action_shape": "dict",
        "decision_log_shape": "absent",
        "decision_log_count": 0,
        "decision_log_entry_shape_counts": {},
        "decision_log_decision_counts": {},
        "decision_log_actor_counts": {},
        "decision_log_timestamp_shape_counts": {},
        "continuity_shape": "absent",
        "continuity_plugin_first_workflow_shape": "absent",
        "continuity_plugin_first_workflow": None,
        "continuity_resume_aware_effort_continuity_shape": "absent",
        "continuity_resume_aware_effort_continuity": None,
        "continuity_effort_hint": None,
        "session_state": "custom_or_invalid",
        "next_action_source": "custom_or_invalid",
        "next_action_priority": "custom_or_invalid",
        "open_risk_count": 1,
        "plan_items_shape": "absent",
        "plan_item_count": None,
        "wip_tasks_shape": "absent",
        "wip_task_count": None,
        "open_risks_shape": "list",
        "open_risk_severity_counts": {"custom_or_invalid": 1},
        "open_risk_kind_counts": {"custom_or_invalid": 1},
        "blocking_open_risk_count": 0,
        "failed_checks_shape": "null",
        "failed_checks_present": False,
        "context_reset_recommended": False,
        "context_reset_shape": "dict",
        "context_reset_recommended_shape": "bool",
        "context_reset_policy_shape": "absent",
        "context_reset_policy_mode": None,
        "context_reset_policy_dry_run_shape": "absent",
        "context_reset_policy_thresholds_shape": "absent",
        "context_reset_threshold_key_counts": {},
        "context_reset_threshold_value_shape_counts": {},
        "context_reset_counters_shape": "absent",
        "context_reset_counter_key_counts": {},
        "context_reset_counter_value_shape_counts": {},
        "context_reset_reasons_shape": "absent",
        "context_reset_reason_entry_shape_counts": {},
        "context_reset_candidates_shape": "absent",
        "context_reset_candidate_entry_shape_counts": {},
        "context_reset_candidate_triggered_shape_counts": {},
        "context_reset_candidate_triggered_value_counts": {},
        "context_reset_candidate_key_counts": {},
        "context_reset_candidate_actual_shape_counts": {},
        "context_reset_candidate_threshold_shape_counts": {},
        "context_reset_candidate_trigger_consistency_counts": {},
        "recent_edits_shape": "list",
        "recent_edit_count": 1,
    }
    assert "private-artifact-type" not in rendered
    assert "private-version" not in rendered
    assert "legacy-version" not in rendered
    assert "private-state" not in rendered
    assert "private-source" not in rendered
    assert "private-priority" not in rendered
    assert "private-risk-severity" not in rendered
    assert "private-risk-kind" not in rendered
    assert "case-a.txt" not in rendered
    assert str(tmp_path) not in rendered


def test_project_bible_pickup_validator_rejects_custom_hidden_versions_without_state_label_failure(tmp_path):
    validator = _load_pickup_validator()
    handoff_artifact = {
        "version": "private-version-worker@example.invalid",
        "legacy_version": "s3:/private-bucket/legacy-version",
        "artifactType": "structured-handoff",
        "timestamp": "2026-07-01T00:00:00Z",
        "previous_state": {"session_state": {"state": "stopped"}},
        "next_action": {"source": "fallback", "priority": "normal"},
        "open_risks": [{"severity": "low", "summary": "private version-only risk"}],
        "failed_checks": None,
        "context_reset": {"recommended": False},
    }
    _write_minimal_pickup_tree(tmp_path, handoff_artifact=handoff_artifact)

    report = validator.build_report(
        root=tmp_path,
        status_payload=_paused_status_fixture(),
        global_protections_report=_valid_global_protections_saved_artifacts_report(),
        validation_time=datetime(2026, 7, 2, tzinfo=timezone.utc),
    )
    rendered = json.dumps(report, ensure_ascii=False)

    assert report["summary"]["ok"] is False
    assert report["summary"]["failed_ids"] == [
        "claude_handoff_versions_are_known_if_present"
    ]
    assert report["claude_handoff"]["artifact_type"] == "structured-handoff"
    assert report["claude_handoff"]["version"] == "custom_or_invalid"
    assert report["claude_handoff"]["legacy_version"] == "custom_or_invalid"
    assert report["claude_handoff"]["session_state"] == "stopped"
    assert report["claude_handoff"]["next_action_source"] == "fallback"
    assert report["claude_handoff"]["next_action_priority"] == "normal"
    assert "private-version" not in rendered
    assert "legacy-version" not in rendered
    assert "private version-only risk" not in rendered
    assert str(tmp_path) not in rendered


def test_project_bible_pickup_validator_rejects_custom_hidden_state_labels_without_leak(tmp_path):
    validator = _load_pickup_validator()
    handoff_artifact = {
        "artifactType": "structured-handoff",
        "timestamp": "2026-07-01T00:00:00Z",
        "previous_state": {"session_state": {"state": "private-state-worker-123"}},
        "next_action": {
            "source": "private-source-case-log",
            "priority": "private-priority-worker-name",
        },
        "open_risks": [{"severity": "low", "summary": "private risk text"}],
        "failed_checks": None,
        "context_reset": {"recommended": False},
    }
    _write_minimal_pickup_tree(tmp_path, handoff_artifact=handoff_artifact)

    report = validator.build_report(
        root=tmp_path,
        status_payload=_paused_status_fixture(),
        global_protections_report=_valid_global_protections_saved_artifacts_report(),
        validation_time=datetime(2026, 7, 2, tzinfo=timezone.utc),
    )
    rendered = json.dumps(report, ensure_ascii=False)

    assert report["summary"]["ok"] is False
    assert report["summary"]["failed_ids"] == [
        "claude_handoff_state_and_next_action_labels_are_known_if_present"
    ]
    label_check = next(
        check
        for check in report["checks"]
        if check["id"] == "claude_handoff_state_and_next_action_labels_are_known_if_present"
    )
    assert label_check["actual"] == {
        "custom_or_invalid_fields": [
            "session_state",
            "next_action_source",
            "next_action_priority",
        ]
    }
    assert report["claude_handoff"]["session_state"] == "custom_or_invalid"
    assert report["claude_handoff"]["next_action_source"] == "custom_or_invalid"
    assert report["claude_handoff"]["next_action_priority"] == "custom_or_invalid"
    assert "private-state" not in rendered
    assert "private-source" not in rendered
    assert "private-priority" not in rendered
    assert "private risk text" not in rendered
    assert str(tmp_path) not in rendered


def test_project_bible_pickup_validator_rejects_custom_hidden_artifact_type_without_leak(tmp_path):
    validator = _load_pickup_validator()
    handoff_artifact = {
        "artifactType": "private-artifact-type-C:\\Users\\private\\handoff.json",
        "timestamp": "2026-07-01T00:00:00Z",
        "previous_state": {"session_state": {"state": "stopped"}},
        "open_risks": [{"severity": "low", "summary": "private risk text"}],
        "failed_checks": None,
        "context_reset": {"recommended": False},
    }
    _write_minimal_pickup_tree(tmp_path, handoff_artifact=handoff_artifact)

    report = validator.build_report(
        root=tmp_path,
        status_payload=_paused_status_fixture(),
        global_protections_report=_valid_global_protections_saved_artifacts_report(),
        validation_time=datetime(2026, 7, 2, tzinfo=timezone.utc),
    )
    rendered = json.dumps(report, ensure_ascii=False)

    assert report["summary"]["ok"] is False
    assert "claude_handoff_artifact_type_is_known_if_present" in report["summary"]["failed_ids"]
    assert report["claude_handoff"]["artifact_type"] == "custom_or_invalid"
    assert report["claude_handoff"]["open_risk_severity_counts"] == {"low": 1}
    assert "private-artifact-type" not in rendered
    assert "private risk text" not in rendered
    assert str(tmp_path) not in rendered


def test_project_bible_pickup_validator_rejects_missing_hidden_artifact_type_without_leak(tmp_path):
    validator = _load_pickup_validator()
    handoff_artifact = {
        "timestamp": "2026-07-01T00:00:00Z",
        "previous_state": {"session_state": {"state": "stopped"}},
        "next_action": {"source": "fallback", "priority": "normal"},
        "open_risks": [{"severity": "low", "summary": "private missing-type risk"}],
        "failed_checks": None,
        "context_reset": {"recommended": False},
    }
    _write_minimal_pickup_tree(tmp_path, handoff_artifact=handoff_artifact)

    report = validator.build_report(
        root=tmp_path,
        status_payload=_paused_status_fixture(),
        global_protections_report=_valid_global_protections_saved_artifacts_report(),
        validation_time=datetime(2026, 7, 2, tzinfo=timezone.utc),
    )
    rendered = json.dumps(report, ensure_ascii=False)

    assert report["summary"]["ok"] is False
    assert report["summary"]["failed_ids"] == [
        "claude_handoff_artifact_type_is_known_if_present"
    ]
    assert report["claude_handoff"]["artifact_type"] is None
    assert report["claude_handoff"]["session_state"] == "stopped"
    assert report["claude_handoff"]["next_action_source"] == "fallback"
    assert report["claude_handoff"]["next_action_priority"] == "normal"
    assert report["claude_handoff"]["open_risk_severity_counts"] == {"low": 1}
    assert "private missing-type risk" not in rendered
    assert str(tmp_path) not in rendered


def test_project_bible_pickup_validator_rejects_invalid_hidden_handoff_timestamp_without_leak(tmp_path):
    validator = _load_pickup_validator()
    handoff_artifact = {
        "artifactType": "structured-handoff",
        "timestamp": "private timestamp C:\\Users\\private\\timeline.jsonl",
        "previous_state": {"session_state": {"state": "stopped"}},
        "open_risks": [],
        "failed_checks": None,
        "context_reset": {"recommended": False},
    }
    _write_minimal_pickup_tree(tmp_path, handoff_artifact=handoff_artifact)

    report = validator.build_report(
        root=tmp_path,
        status_payload=_paused_status_fixture(),
        global_protections_report=_valid_global_protections_saved_artifacts_report(),
        validation_time=datetime(2026, 7, 2, tzinfo=timezone.utc),
    )
    rendered = json.dumps(report, ensure_ascii=False)

    assert report["summary"]["ok"] is False
    assert "claude_handoff_timestamp_valid_if_present" in report["summary"]["failed_ids"]
    assert report["claude_handoff"]["timestamp_present"] is True
    assert report["claude_handoff"]["timestamp_valid"] is False
    assert report["claude_handoff"]["validated_after_handoff"] is None
    assert "private timestamp" not in rendered
    assert "timeline.jsonl" not in rendered
    assert str(tmp_path) not in rendered


def test_project_bible_pickup_validator_rejects_hidden_handoff_failed_checks_without_details(tmp_path):
    validator = _load_pickup_validator()
    handoff_artifact = {
        "artifactType": "structured-handoff",
        "timestamp": "2026-07-01T00:00:00Z",
        "previous_state": {"session_state": {"state": "stopped"}},
        "open_risks": [],
        "failed_checks": [
            {
                "id": "private_source_leak",
                "detail": "C:\\Users\\private\\case-log.txt",
            },
        ],
        "context_reset": {"recommended": False},
    }
    _write_minimal_pickup_tree(tmp_path, handoff_artifact=handoff_artifact)

    report = validator.build_report(
        root=tmp_path,
        status_payload=_paused_status_fixture(),
        global_protections_report=_valid_global_protections_saved_artifacts_report(),
    )
    rendered = json.dumps(report, ensure_ascii=False)

    assert report["summary"]["ok"] is False
    assert "claude_handoff_has_no_failed_checks_if_present" in report["summary"]["failed_ids"]
    assert report["claude_handoff"]["failed_checks_shape"] == "list"
    assert report["claude_handoff"]["failed_checks_present"] is True
    assert "private_source_leak" not in rendered
    assert "case-log.txt" not in rendered
    assert str(tmp_path) not in rendered


def test_project_bible_pickup_validator_rejects_malformed_hidden_failed_checks_without_leak(tmp_path):
    validator = _load_pickup_validator()
    handoff_artifact = {
        "artifactType": "structured-handoff",
        "timestamp": "2026-07-01T00:00:00Z",
        "previous_state": {"session_state": {"state": "stopped"}},
        "open_risks": [],
        "failed_checks": "C:\\Users\\private\\failed-checks.json",
        "context_reset": {"recommended": False},
    }
    _write_minimal_pickup_tree(tmp_path, handoff_artifact=handoff_artifact)

    report = validator.build_report(
        root=tmp_path,
        status_payload=_paused_status_fixture(),
        global_protections_report=_valid_global_protections_saved_artifacts_report(),
        validation_time=datetime(2026, 7, 2, tzinfo=timezone.utc),
    )
    rendered = json.dumps(report, ensure_ascii=False)

    assert report["summary"]["ok"] is False
    assert report["summary"]["failed_ids"] == [
        "claude_handoff_failed_checks_shape_is_known_if_present"
    ]
    assert report["claude_handoff"]["failed_checks_shape"] == "custom_or_invalid"
    assert report["claude_handoff"]["failed_checks_present"] is False
    assert "failed-checks.json" not in rendered
    assert "C:\\Users" not in rendered
    assert str(tmp_path) not in rendered


def test_project_bible_pickup_validator_rejects_malformed_hidden_context_reset_without_leak(tmp_path):
    validator = _load_pickup_validator()
    handoff_artifact = {
        "artifactType": "structured-handoff",
        "timestamp": "2026-07-01T00:00:00Z",
        "previous_state": {"session_state": {"state": "stopped"}},
        "open_risks": [],
        "failed_checks": None,
        "context_reset": {
            "recommended": "C:\\Users\\private\\context-reset-needed.txt",
        },
    }
    _write_minimal_pickup_tree(tmp_path, handoff_artifact=handoff_artifact)

    report = validator.build_report(
        root=tmp_path,
        status_payload=_paused_status_fixture(),
        global_protections_report=_valid_global_protections_saved_artifacts_report(),
        validation_time=datetime(2026, 7, 2, tzinfo=timezone.utc),
    )
    rendered = json.dumps(report, ensure_ascii=False)

    assert report["summary"]["ok"] is False
    assert report["summary"]["failed_ids"] == [
        "claude_handoff_context_reset_is_bool_if_present"
    ]
    assert report["claude_handoff"]["context_reset_recommended"] is None
    assert report["claude_handoff"]["context_reset_shape"] == "dict"
    assert report["claude_handoff"]["context_reset_recommended_shape"] == "custom_or_invalid"
    assert "context-reset-needed" not in rendered
    assert "C:\\Users" not in rendered
    assert str(tmp_path) not in rendered


def test_project_bible_pickup_validator_rejects_malformed_hidden_context_reset_policy_without_leak(tmp_path):
    validator = _load_pickup_validator()
    handoff_artifact = {
        "artifactType": "structured-handoff",
        "timestamp": "2026-07-01T00:00:00Z",
        "previous_state": {"session_state": {"state": "stopped"}},
        "open_risks": [],
        "failed_checks": None,
        "context_reset": {
            "recommended": False,
            "policy": {
                "mode": "private-mode-worker@example.invalid",
                "dryRun": "C:\\Users\\private\\dry-run.txt",
                "thresholds": "C:\\Users\\private\\thresholds.json",
            },
            "counters": "private counters C:\\Users\\private\\counters.json",
            "summary": "private reset summary should not leak",
        },
    }
    _write_minimal_pickup_tree(tmp_path, handoff_artifact=handoff_artifact)

    report = validator.build_report(
        root=tmp_path,
        status_payload=_paused_status_fixture(),
        global_protections_report=_valid_global_protections_saved_artifacts_report(),
        validation_time=datetime(2026, 7, 2, tzinfo=timezone.utc),
    )
    rendered = json.dumps(report, ensure_ascii=False)

    assert report["summary"]["ok"] is False
    assert report["summary"]["failed_ids"] == [
        "claude_handoff_context_reset_policy_shape_and_labels_are_known_if_present"
    ]
    assert report["claude_handoff"]["context_reset_shape"] == "dict"
    assert report["claude_handoff"]["context_reset_recommended_shape"] == "bool"
    assert report["claude_handoff"]["context_reset_policy_shape"] == "dict"
    assert report["claude_handoff"]["context_reset_policy_mode"] == "custom_or_invalid"
    assert report["claude_handoff"]["context_reset_policy_dry_run_shape"] == "custom_or_invalid"
    assert report["claude_handoff"]["context_reset_policy_thresholds_shape"] == "custom_or_invalid"
    assert report["claude_handoff"]["context_reset_counters_shape"] == "custom_or_invalid"
    assert "private-mode" not in rendered
    assert "worker@example.invalid" not in rendered
    assert "dry-run" not in rendered
    assert "thresholds.json" not in rendered
    assert "counters.json" not in rendered
    assert "private reset summary" not in rendered
    assert "C:\\Users" not in rendered
    assert str(tmp_path) not in rendered


def test_project_bible_pickup_validator_rejects_malformed_hidden_context_reset_counts_without_leak(tmp_path):
    validator = _load_pickup_validator()
    handoff_artifact = {
        "artifactType": "structured-handoff",
        "timestamp": "2026-07-01T00:00:00Z",
        "previous_state": {"session_state": {"state": "stopped"}},
        "open_risks": [],
        "failed_checks": None,
        "context_reset": {
            "recommended": False,
            "policy": {
                "mode": "auto",
                "dryRun": False,
                "thresholds": {
                    "privateThreshold": "C:\\Users\\private\\threshold.txt",
                    "wipTasks": True,
                },
            },
            "counters": {
                "privateCounter": "worker@example.invalid",
                "recentEdits": "C:\\Users\\private\\counter.txt",
            },
        },
    }
    _write_minimal_pickup_tree(tmp_path, handoff_artifact=handoff_artifact)

    report = validator.build_report(
        root=tmp_path,
        status_payload=_paused_status_fixture(),
        global_protections_report=_valid_global_protections_saved_artifacts_report(),
        validation_time=datetime(2026, 7, 2, tzinfo=timezone.utc),
    )
    rendered = json.dumps(report, ensure_ascii=False)

    assert report["summary"]["ok"] is False
    assert report["summary"]["failed_ids"] == [
        "claude_handoff_context_reset_threshold_and_counter_keys_are_known_if_present"
    ]
    assert report["claude_handoff"]["context_reset_policy_shape"] == "dict"
    assert report["claude_handoff"]["context_reset_policy_mode"] == "auto"
    assert report["claude_handoff"]["context_reset_policy_dry_run_shape"] == "bool"
    assert report["claude_handoff"]["context_reset_policy_thresholds_shape"] == "dict"
    assert report["claude_handoff"]["context_reset_counters_shape"] == "dict"
    assert report["claude_handoff"]["context_reset_threshold_key_counts"] == {
        "custom_or_invalid": 1,
        "wipTasks": 1,
    }
    assert report["claude_handoff"]["context_reset_threshold_value_shape_counts"] == {
        "custom_or_invalid": 2,
    }
    assert report["claude_handoff"]["context_reset_counter_key_counts"] == {
        "custom_or_invalid": 1,
        "recentEdits": 1,
    }
    assert report["claude_handoff"]["context_reset_counter_value_shape_counts"] == {
        "custom_or_invalid": 2,
    }
    assert "privateThreshold" not in rendered
    assert "privateCounter" not in rendered
    assert "threshold.txt" not in rendered
    assert "counter.txt" not in rendered
    assert "worker@example.invalid" not in rendered
    assert "C:\\Users" not in rendered
    assert str(tmp_path) not in rendered


def test_project_bible_pickup_validator_rejects_malformed_hidden_context_reset_lists_without_leak(tmp_path):
    validator = _load_pickup_validator()
    handoff_artifact = {
        "artifactType": "structured-handoff",
        "timestamp": "2026-07-01T00:00:00Z",
        "previous_state": {"session_state": {"state": "stopped"}},
        "open_risks": [],
        "failed_checks": None,
        "context_reset": {
            "recommended": False,
            "reasons": [
                "private reason C:\\Users\\private\\reason.txt",
                {"detail": "worker@example.invalid"},
            ],
            "candidates": [
                "C:\\Users\\private\\candidate.json",
                {
                    "key": "private-candidate-key",
                    "label": "private candidate label",
                    "triggered": "C:\\Users\\private\\triggered.txt",
                },
            ],
        },
    }
    _write_minimal_pickup_tree(tmp_path, handoff_artifact=handoff_artifact)

    report = validator.build_report(
        root=tmp_path,
        status_payload=_paused_status_fixture(),
        global_protections_report=_valid_global_protections_saved_artifacts_report(),
        validation_time=datetime(2026, 7, 2, tzinfo=timezone.utc),
    )
    rendered = json.dumps(report, ensure_ascii=False)

    assert report["summary"]["ok"] is False
    assert report["summary"]["failed_ids"] == [
        "claude_handoff_context_reset_reason_and_candidate_shapes_are_known_if_present"
    ]
    assert report["claude_handoff"]["context_reset_reasons_shape"] == "list"
    assert report["claude_handoff"]["context_reset_reason_entry_shape_counts"] == {
        "custom_or_invalid": 1,
        "str": 1,
    }
    assert report["claude_handoff"]["context_reset_candidates_shape"] == "list"
    assert report["claude_handoff"]["context_reset_candidate_entry_shape_counts"] == {
        "custom_or_invalid": 1,
        "dict": 1,
    }
    assert report["claude_handoff"]["context_reset_candidate_triggered_shape_counts"] == {
        "custom_or_invalid": 2,
    }
    assert "private reason" not in rendered
    assert "reason.txt" not in rendered
    assert "worker@example.invalid" not in rendered
    assert "candidate.json" not in rendered
    assert "private-candidate-key" not in rendered
    assert "private candidate label" not in rendered
    assert "triggered.txt" not in rendered
    assert "C:\\Users" not in rendered
    assert str(tmp_path) not in rendered


def test_project_bible_pickup_validator_rejects_malformed_hidden_context_reset_candidate_keys_without_leak(tmp_path):
    validator = _load_pickup_validator()
    handoff_artifact = {
        "artifactType": "structured-handoff",
        "timestamp": "2026-07-01T00:00:00Z",
        "previous_state": {"session_state": {"state": "stopped"}},
        "open_risks": [],
        "failed_checks": None,
        "context_reset": {
            "recommended": False,
            "candidates": [
                {
                    "key": "private-candidate-worker@example.invalid",
                    "label": "private candidate label should not leak",
                    "actual": "C:\\Users\\private\\actual.txt",
                    "threshold": True,
                    "triggered": False,
                },
            ],
        },
    }
    _write_minimal_pickup_tree(tmp_path, handoff_artifact=handoff_artifact)

    report = validator.build_report(
        root=tmp_path,
        status_payload=_paused_status_fixture(),
        global_protections_report=_valid_global_protections_saved_artifacts_report(),
        validation_time=datetime(2026, 7, 2, tzinfo=timezone.utc),
    )
    rendered = json.dumps(report, ensure_ascii=False)

    assert report["summary"]["ok"] is False
    assert report["summary"]["failed_ids"] == [
        "claude_handoff_context_reset_candidate_keys_and_numbers_are_known_if_present"
    ]
    assert report["claude_handoff"]["context_reset_candidates_shape"] == "list"
    assert report["claude_handoff"]["context_reset_candidate_entry_shape_counts"] == {
        "dict": 1,
    }
    assert report["claude_handoff"]["context_reset_candidate_triggered_shape_counts"] == {
        "bool": 1,
    }
    assert report["claude_handoff"]["context_reset_candidate_key_counts"] == {
        "custom_or_invalid": 1,
    }
    assert report["claude_handoff"]["context_reset_candidate_actual_shape_counts"] == {
        "custom_or_invalid": 1,
    }
    assert report["claude_handoff"]["context_reset_candidate_threshold_shape_counts"] == {
        "custom_or_invalid": 1,
    }
    assert "private-candidate" not in rendered
    assert "worker@example.invalid" not in rendered
    assert "private candidate label" not in rendered
    assert "actual.txt" not in rendered
    assert "C:\\Users" not in rendered
    assert str(tmp_path) not in rendered


def test_project_bible_pickup_validator_rejects_hidden_context_reset_recommendation_contradiction_without_leak(tmp_path):
    validator = _load_pickup_validator()
    handoff_artifact = {
        "artifactType": "structured-handoff",
        "timestamp": "2026-07-01T00:00:00Z",
        "previous_state": {"session_state": {"state": "stopped"}},
        "open_risks": [],
        "failed_checks": None,
        "context_reset": {
            "recommended": False,
            "candidates": [
                {
                    "key": "recent_edits",
                    "label": "private triggered candidate should not leak",
                    "actual": 17,
                    "threshold": 8,
                    "triggered": True,
                },
            ],
            "summary": "private reset contradiction summary",
        },
    }
    _write_minimal_pickup_tree(tmp_path, handoff_artifact=handoff_artifact)

    report = validator.build_report(
        root=tmp_path,
        status_payload=_paused_status_fixture(),
        global_protections_report=_valid_global_protections_saved_artifacts_report(),
        validation_time=datetime(2026, 7, 2, tzinfo=timezone.utc),
    )
    rendered = json.dumps(report, ensure_ascii=False)

    assert report["summary"]["ok"] is False
    assert report["summary"]["failed_ids"] == [
        "claude_handoff_context_reset_recommendation_matches_triggered_candidates_if_present"
    ]
    assert report["claude_handoff"]["context_reset_recommended"] is False
    assert report["claude_handoff"]["context_reset_candidates_shape"] == "list"
    assert report["claude_handoff"]["context_reset_candidate_entry_shape_counts"] == {
        "dict": 1,
    }
    assert report["claude_handoff"]["context_reset_candidate_triggered_shape_counts"] == {
        "bool": 1,
    }
    assert report["claude_handoff"]["context_reset_candidate_triggered_value_counts"] == {
        "true": 1,
    }
    assert report["claude_handoff"]["context_reset_candidate_key_counts"] == {
        "recent_edits": 1,
    }
    assert report["claude_handoff"]["context_reset_candidate_actual_shape_counts"] == {
        "int": 1,
    }
    assert report["claude_handoff"]["context_reset_candidate_threshold_shape_counts"] == {
        "int": 1,
    }
    assert "private triggered candidate" not in rendered
    assert "private reset contradiction" not in rendered
    assert str(tmp_path) not in rendered


def test_project_bible_pickup_validator_rejects_hidden_context_reset_trigger_math_contradiction_without_leak(tmp_path):
    validator = _load_pickup_validator()
    handoff_artifact = {
        "artifactType": "structured-handoff",
        "timestamp": "2026-07-01T00:00:00Z",
        "previous_state": {"session_state": {"state": "stopped"}},
        "open_risks": [],
        "failed_checks": None,
        "context_reset": {
            "recommended": True,
            "candidates": [
                {
                    "key": "recent_edits",
                    "label": "private trigger math label should not leak",
                    "actual": 17,
                    "threshold": 8,
                    "triggered": False,
                },
            ],
            "summary": "private trigger math summary",
        },
    }
    _write_minimal_pickup_tree(tmp_path, handoff_artifact=handoff_artifact)

    report = validator.build_report(
        root=tmp_path,
        status_payload=_paused_status_fixture(),
        global_protections_report=_valid_global_protections_saved_artifacts_report(),
        validation_time=datetime(2026, 7, 2, tzinfo=timezone.utc),
    )
    rendered = json.dumps(report, ensure_ascii=False)

    assert report["summary"]["ok"] is False
    assert report["summary"]["failed_ids"] == [
        "claude_handoff_context_reset_candidate_trigger_matches_numbers_if_present"
    ]
    assert report["claude_handoff"]["context_reset_recommended"] is True
    assert report["claude_handoff"]["context_reset_candidate_entry_shape_counts"] == {
        "dict": 1,
    }
    assert report["claude_handoff"]["context_reset_candidate_triggered_shape_counts"] == {
        "bool": 1,
    }
    assert report["claude_handoff"]["context_reset_candidate_triggered_value_counts"] == {
        "false": 1,
    }
    assert report["claude_handoff"]["context_reset_candidate_key_counts"] == {
        "recent_edits": 1,
    }
    assert report["claude_handoff"]["context_reset_candidate_actual_shape_counts"] == {
        "int": 1,
    }
    assert report["claude_handoff"]["context_reset_candidate_threshold_shape_counts"] == {
        "int": 1,
    }
    assert report["claude_handoff"]["context_reset_candidate_trigger_consistency_counts"] == {
        "inconsistent": 1,
    }
    assert "private trigger math" not in rendered
    assert str(tmp_path) not in rendered


def test_project_bible_pickup_validator_rejects_malformed_hidden_handoff_without_path_leak(tmp_path):
    validator = _load_pickup_validator()
    _write_minimal_pickup_tree(tmp_path)
    handoff_path = tmp_path / ".claude/state/handoff-artifact.json"
    handoff_path.parent.mkdir(parents=True, exist_ok=True)
    handoff_path.write_text("{not json", encoding="utf-8")

    report = validator.build_report(
        root=tmp_path,
        status_payload=_paused_status_fixture(),
        global_protections_report=_valid_global_protections_saved_artifacts_report(),
    )
    rendered = json.dumps(report, ensure_ascii=False)

    assert report["summary"]["ok"] is False
    assert "claude_handoff_artifact_parseable_if_present" in report["summary"]["failed_ids"]
    assert report["claude_handoff"]["exists"] is True
    assert "JSONDecodeError" in report["claude_handoff"]["load_error"]
    assert str(tmp_path) not in rendered
    assert "handoff-artifact.json" not in rendered


def test_main_root_flag_validates_copied_tree_artifacts(tmp_path, monkeypatch, capsys):
    validator = _load_pickup_validator()
    _write_minimal_pickup_tree(tmp_path, mismatched_pack_project_id=True)
    monkeypatch.setattr(
        validator.autonomous_engine,
        "status_payload",
        lambda: _paused_status_fixture(),
    )

    rc = validator.main(["--root", str(tmp_path), "--json"])
    printed = capsys.readouterr().out

    assert rc == 1
    assert "sister_project_planning_validator_passes" in printed
    assert "project_and_jurisdiction_pack_ids_match" in printed
    assert str(tmp_path) not in printed


def test_main_status_json_flag_uses_saved_status_without_live_probe(tmp_path, monkeypatch, capsys):
    validator = _load_pickup_validator()
    status_path = tmp_path / "saved_status.json"
    status_path.write_text(json.dumps(_paused_status_fixture()), encoding="utf-8")
    monkeypatch.setattr(
        validator.autonomous_engine,
        "status_payload",
        lambda: (_ for _ in ()).throw(AssertionError("live status should not be called")),
    )

    rc = validator.main(["--status-json", str(status_path), "--json"])
    printed = capsys.readouterr().out

    assert rc == 0
    assert '"check_count": 65' in printed
    assert '"paused": true' in printed
    assert str(tmp_path) not in printed


def test_main_saved_status_and_global_summary_skip_live_probes(tmp_path, monkeypatch, capsys):
    validator = _load_pickup_validator()
    status_path = tmp_path / "saved_status.json"
    global_path = tmp_path / "global_summary.json"
    status_path.write_text(json.dumps(_paused_status_fixture()), encoding="utf-8")
    global_path.write_text(
        json.dumps(_valid_global_protections_saved_artifacts_report()["summary"]),
        encoding="utf-8",
    )
    monkeypatch.setattr(
        validator.autonomous_engine,
        "status_payload",
        lambda: (_ for _ in ()).throw(AssertionError("live status should not be called")),
    )
    monkeypatch.setattr(
        validator.validate_global_protections_saved_artifacts,
        "validate_saved_artifacts",
        lambda **_: (_ for _ in ()).throw(AssertionError("saved artifacts should not be read")),
    )

    rc = validator.main([
        "--status-json",
        str(status_path),
        "--global-protections-report-json",
        str(global_path),
        "--json",
    ])
    printed = capsys.readouterr().out

    assert rc == 0
    assert '"check_count": 65' in printed
    assert '"global_protections_saved_artifacts"' in printed
    assert '"ready_for_comparable_scoring": false' in printed
    assert str(tmp_path) not in printed


def test_text_report_surfaces_global_protections_mismatch_counts(capsys):
    validator = _load_pickup_validator()
    report = validator.build_report(
        status_payload=_paused_status_fixture(),
        global_protections_report=_valid_global_protections_saved_artifacts_report(),
    )

    validator._print_text_report(report)
    printed = capsys.readouterr().out

    assert "Global protections -" in printed
    assert "artifacts=13/13" in printed
    assert "markdown=13/13" in printed
    assert "failed_checks=0/157" in printed
    assert "suite_failed=0/21" in printed
    assert "path_mismatches=0" in printed
    assert "mismatches=phase:0 legal_anchor:0 readiness:0" in printed


def test_main_status_json_load_error_is_sanitized(tmp_path, monkeypatch, capsys):
    validator = _load_pickup_validator()
    status_path = tmp_path / "bad_status.json"
    status_path.write_text("{not json", encoding="utf-8")
    monkeypatch.setattr(
        validator.autonomous_engine,
        "status_payload",
        lambda: (_ for _ in ()).throw(AssertionError("live status should not be called")),
    )

    rc = validator.main(["--status-json", str(status_path), "--json"])
    printed = capsys.readouterr().out

    assert rc == 1
    assert "status_json_loads" in printed
    assert "JSONDecodeError" in printed
    assert str(tmp_path) not in printed
    assert "bad_status.json" not in printed
    assert "engine_process_liveness_matches_mode" not in printed


def test_main_global_summary_json_load_error_is_sanitized(tmp_path, monkeypatch, capsys):
    validator = _load_pickup_validator()
    global_path = tmp_path / "bad_global_summary.json"
    global_path.write_text("{not json", encoding="utf-8")
    monkeypatch.setattr(
        validator.autonomous_engine,
        "status_payload",
        lambda: _paused_status_fixture(),
    )

    rc = validator.main(["--global-protections-report-json", str(global_path), "--json"])
    printed = capsys.readouterr().out

    assert rc == 1
    assert "global_protections_report_json_loads" in printed
    assert "JSONDecodeError" in printed
    assert str(tmp_path) not in printed
    assert "bad_global_summary.json" not in printed


def test_main_status_json_rejects_preflight_shape_without_downstream_noise(tmp_path, monkeypatch, capsys):
    validator = _load_pickup_validator()
    status_path = tmp_path / "preflight_shaped.json"
    status_path.write_text(
        json.dumps({
            "ready": False,
            "readiness_scope": "state_only",
            "ollama_checked": False,
            "saved_lock_state": {"state": "stale"},
        }),
        encoding="utf-8",
    )
    monkeypatch.setattr(
        validator.autonomous_engine,
        "status_payload",
        lambda: (_ for _ in ()).throw(AssertionError("live status should not be called")),
    )

    rc = validator.main(["--status-json", str(status_path), "--json"])
    printed = capsys.readouterr().out

    assert rc == 1
    assert "status_payload_has_expected_shape" in printed
    assert "full JSON object from python scripts\\\\autonomous_engine.py --status" in printed
    assert "engine_process_liveness_matches_mode" not in printed
    assert "latest_preflight_matches_current_state" not in printed
    assert str(tmp_path) not in printed
