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
        "latest_preflight": {
            "exists": True,
            "ready": False,
            "matches_current_state": True,
            "needs_refresh": False,
            "readiness_scope": "state_only",
            "ollama_checked": False,
            "saved_lock_state": {"state": "stale"},
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
            "docs/codex/PROJECT_BIBLE.md\n"
            ".claude/rules/05_project_bible_pickup.md\n"
            "Current validation discipline\n"
            "treat older suite counts in this file as historical\n"
            "python -m pytest packages --collect-only -q\n"
        ),
        "ROOT_FILES.md": (
            "| `PROJECT_BIBLE.md` | Root pointer to the canonical long-loop "
            "pickup brief in `docs/codex/PROJECT_BIBLE.md`. |\n"
        ),
        "PROJECT_BIBLE.md": (
            "Claude Code\n"
            "Codex\n"
            "Fable 5-style agents\n"
            "repo-root pickup tools\n"
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
        ".claude/rules/05_project_bible_pickup.md": (
            "docs/codex/PROJECT_BIBLE.md\n"
            "reports/autonomous_engine.stop\n"
            "call Ollama\n"
            "promote candidate dimensions\n"
        ),
        "docs/FILE_PURPOSE_GUIDE.md": (
            "| Agent handoff | `AGENTS.md`, `CLAUDE.md`, `PROJECT_BIBLE.md`, "
            "`.claude/rules/` |\n"
        ),
        "docs/REPO_LAYOUT.md": (
            "- AI pickup bridge: root [`PROJECT_BIBLE.md`](../PROJECT_BIBLE.md) "
            "points agents to [`docs/codex/PROJECT_BIBLE.md`](codex/PROJECT_BIBLE.md).\n"
        ),
        "docs/codex/PROJECT_BIBLE.md": (
            "docs/codex/goal_commands/13_project_bible_continuation.md\n"
            "python scripts\\validate_project_bible_pickup.py\n"
            "Copied handoff trees must include\n"
            "direct helper validators/builders\n"
            "direct local imports\n"
            "sister-project validator's direct local imports\n"
            "autonomous engine helper modules\n"
            "--root <path>\n"
            "--status-json <path>\n"
            "--global-protections-report-json <path>\n"
            "hidden Claude handoff\n"
            "structured-handoff\n"
            "aggregate open-risk severity counts\n"
            "open_risks shape\n"
            "high/critical blocking-risk count\n"
            "failed-check presence\n"
            "parse failures are reported\n"
            "ready `false`\n"
            "stop_sentinel_present\n"
            "declared candidate pattern IDs\n"
            "unresolved source-gap rows\n"
            "source admission rules\n"
            "international anchors cannot substitute\n"
            "public complaint lists\n"
            "source_admission_missing=0\n"
            "omits raw scheme-prompt IDs\n"
            "source URLs\n"
            "aggregate counts\n"
            "invalid_or_unknown\n"
            "custom_or_invalid\n"
            "copied phase IDs\n"
            "Prompt parse-error details\n"
            "safe line numbers\n"
            "known safe error labels\n"
            "custom error labels\n"
            "Hidden handoff string fields\n"
            "allowlisted labels\n"
            "unknown hidden handoff labels fail closed\n"
            "timestamp presence\n"
            "timestamp validity\n"
            "validated_after_handoff\n"
            "not newer than the validation run\n"
            "High or critical hidden open-risk severities fail closed\n"
            "unknown hidden open-risk severities fail closed\n"
            "shape problem\n"
            "Saved status string fields\n"
            "unknown status labels fail closed\n"
            "custom blocker or mismatch labels\n"
            "python scripts\\validate_sister_project_planning.py\n"
            "python scripts\\validate_global_protections_saved_artifacts.py\n"
            "python scripts\\validate_global_protections_saved_artifacts.py --json\n"
            "python -m pytest tests -q -k \"global_protections or regulatory_miss_pattern\"\n"
            "python scripts\\autonomous_engine.py --status\n"
            "latest_preflight.saved_lock_state.state: \"stale\"\n"
            "Ollama not checked\n"
            "Candidate dimensions from the research spider are propose-only\n"
            "reports/autonomous_engine_preflight.json\n"
        ),
        "docs/codex/README.md": "[`PROJECT_BIBLE.md`](PROJECT_BIBLE.md)\n",
        "docs/codex/00_do_not_break.md": "do not break\n",
        "docs/codex/00_kernel_compatibility_gate.md": "kernel gate\n",
        "docs/codex/00_execution_order.md": "execution order\n",
        "docs/codex/goal_commands/README.md": "[13](13_project_bible_continuation.md)\n",
        "docs/codex/goal_commands/13_project_bible_continuation.md": (
            "python scripts\\autonomous_engine.py --status\n"
            "lock.state: \"stale\"\n"
            "latest_preflight.saved_lock_state.state: \"stale\"\n"
            "Do not remove reports/autonomous_engine.stop\n"
            "do not start scripts/autonomous_engine.py in run/once mode\n"
            "do not call Ollama\n"
            "do not promote candidate dimensions\n"
            "python scripts\\validate_project_bible_pickup.py\n"
            "python scripts\\validate_sister_project_planning.py\n"
            "python scripts\\validate_global_protections_saved_artifacts.py\n"
            "python -m pytest tests -q -k \"global_protections or regulatory_miss_pattern\"\n"
            "python scripts\\validate_public_surface.py\n"
            "python -m pytest packages --collect-only -q\n"
            "python scripts\\validate_main_kaggle_kernels.py\n"
            "py -3.12 scripts\\validate_kaggle_page_sources.py\n"
        ),
        "scripts/autonomous_engine.py": "# placeholder\n",
        "scripts/validate_global_protections_saved_artifacts.py": "# placeholder\n",
        "scripts/validate_project_bible_pickup.py": "# placeholder\n",
        "scripts/validate_sister_project_planning.py": "# placeholder\n",
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
    assert "Read order for continuation sessions" in root_project_bible
    assert "AGENTS.md" in root_project_bible
    assert "CLAUDE.md" in root_project_bible
    assert ".claude/rules/05_project_bible_pickup.md" in root_project_bible
    assert "reports/autonomous_engine.stop" in root_project_bible
    assert "call Ollama" in root_project_bible
    assert "promote candidate dimensions" in root_project_bible
    assert "normal preflight and review gates" in root_project_bible
    assert "`PROJECT_BIBLE.md`" in root_files
    assert "Root pointer to the canonical long-loop pickup brief" in root_files
    assert "docs/codex/PROJECT_BIBLE.md" in root_files
    assert "| Agent handoff |" in file_purpose_guide
    assert "PROJECT_BIBLE.md" in file_purpose_guide
    assert ".claude/rules/" in file_purpose_guide
    assert "AI pickup bridge" in repo_layout
    assert "../PROJECT_BIBLE.md" in repo_layout
    assert "codex/PROJECT_BIBLE.md" in repo_layout
    assert "docs/codex/PROJECT_BIBLE.md" in claude
    assert ".claude/rules/05_project_bible_pickup.md" in claude
    assert "[`PROJECT_BIBLE.md`](PROJECT_BIBLE.md)" in codex_readme
    assert "13_project_bible_continuation.md" in command_readme
    assert "docs/codex/goal_commands/13_project_bible_continuation.md" in project_bible
    assert 'lock.state: "stale"' in project_bible
    assert 'latest_preflight.saved_lock_state.state: "stale"' in project_bible
    assert "python scripts\\validate_sister_project_planning.py" in project_bible
    assert "Copied handoff trees must include" in project_bible
    assert "direct helper validators/builders" in project_bible
    assert "direct local imports" in project_bible
    assert "sister-project validator's" in project_bible
    assert "autonomous engine helper modules" in project_bible
    assert "--project-config" in project_bible
    assert "--root <path>" in project_bible
    assert "--status-json <path>" in project_bible
    assert "--global-protections-report-json <path>" in project_bible
    assert "hidden Claude handoff" in project_bible
    assert "structured-handoff" in project_bible
    assert "aggregate open-risk severity counts" in project_bible
    assert "open_risks shape" in project_bible
    assert "high/critical blocking-risk count" in project_bible
    assert "failed-check" in project_bible
    assert "parse failures are reported" in project_bible
    assert "ready `false`" in project_bible
    assert "stop_sentinel_present" in project_bible
    assert "declared candidate pattern IDs" in project_bible
    assert "unresolved source-gap rows" in project_bible
    assert "source admission rules" in project_bible
    assert "international anchors cannot" in project_bible
    assert "public complaint lists" in project_bible
    assert "omits raw scheme-prompt IDs" in project_bible
    assert "source URLs" in project_bible
    assert "aggregate counts" in project_bible
    assert "invalid_or_unknown" in project_bible
    assert "custom_or_invalid" in project_bible
    assert "copied phase IDs" in project_bible
    assert "Prompt parse-error details" in project_bible
    assert "safe line numbers" in project_bible
    assert "known safe error labels" in project_bible
    assert "custom error labels" in project_bible
    assert "Hidden handoff string fields" in project_bible
    assert "allowlisted labels" in project_bible
    assert "unknown hidden handoff labels fail closed" in project_bible
    assert "timestamp presence" in project_bible
    assert "timestamp validity" in project_bible
    assert "validated_after_handoff" in project_bible
    assert "not newer than the validation run" in project_bible
    assert "High or critical hidden open-risk severities fail closed" in project_bible
    assert "unknown hidden open-risk severities fail closed" in project_bible
    assert "shape problem" in project_bible
    assert "Saved status string fields" in project_bible
    assert "unknown status labels fail closed" in project_bible
    assert "custom blocker or mismatch labels" in project_bible
    assert "python scripts\\validate_sister_project_planning.py`:" in project_bible
    assert "`38 checks, 0 findings`" in project_bible
    assert "`27 checks, 0 findings`" in project_bible
    assert "`source_admission_missing=0`" in project_bible
    assert "`privacy_issues=project:0,packs:0,grounding:0`" in project_bible
    assert "aggregate-only safety signal" in project_bible
    assert "python scripts\\validate_global_protections_saved_artifacts.py" in project_bible
    assert "python scripts\\validate_global_protections_saved_artifacts.py --json" in project_bible
    assert 'python -m pytest tests -q -k "global_protections or regulatory_miss_pattern"' in project_bible
    assert "Global-protections project plan" in project_bible
    assert "Queued scopes are explicit backlog only" in project_bible
    assert "reports/autonomous_engine_preflight.json" in project_bible
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

    assert "docs/codex/PROJECT_BIBLE.md" in rule
    assert "reports/autonomous_engine.stop" in rule
    assert "call Ollama" in rule
    assert "promote candidate dimensions" in rule


def test_project_bible_continuation_goal_pins_safety_and_validation():
    command = _read("docs/codex/goal_commands/13_project_bible_continuation.md")

    assert "/goal In C:\\Users\\amare\\OneDrive\\Documents\\gemma4_comp" in command
    assert "docs/codex/PROJECT_BIBLE.md" in command
    assert "python scripts\\autonomous_engine.py --status" in command
    assert 'latest_preflight.saved_lock_state.state: "stale"' in command
    assert "Do not remove reports/autonomous_engine.stop" in command
    assert "do not call Ollama" in command
    assert "do not promote candidate dimensions" in command
    assert "python scripts\\validate_project_bible_pickup.py" in command
    assert "python scripts\\validate_global_protections_saved_artifacts.py" in command
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
    assert "scripts/validate_global_protections_saved_artifacts.py" in validator.REQUIRED_FILES
    assert "scripts/validate_project_bible_pickup.py" in validator.REQUIRED_FILES
    assert "scripts/validate_sister_project_planning.py" in validator.REQUIRED_FILES
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
    assert report["summary"]["check_count"] == 38
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
        "ready": False,
        "readiness_scope": "state_only",
        "ollama_checked": False,
        "matches_current_state": True,
        "needs_refresh": False,
        "saved_lock_state": "stale",
        "blockers": ["stop_sentinel_present"],
        "ignored_blockers": [],
        "state_mismatch_reasons": [],
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
        "check_count": 27,
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
        "source_admission_missing_concept_count": 0,
        "project_privacy_issue_count": 0,
        "jurisdiction_pack_privacy_issue_count": 0,
        "grounding_metadata_privacy_issue_count": 0,
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


def test_project_bible_pickup_validator_rejects_live_or_ollama_checked_status():
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
        "engine_process_not_alive",
        "lock_state_is_not_live",
        "latest_preflight_is_state_only_without_ollama",
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
    assert "latest_preflight_blocks_launch_on_stop_sentinel" in report["summary"]["failed_ids"]
    assert report["snapshot"]["latest_preflight"]["ready"] is True
    assert report["snapshot"]["latest_preflight"]["ignored_blockers"] == ["stop_sentinel_present"]


def test_project_bible_pickup_validator_sanitizes_custom_status_json_labels():
    validator = _load_pickup_validator()
    status = copy.deepcopy(_paused_status_fixture())
    status["stop_sentinel"] = "C:\\Users\\private\\autonomous_engine.stop"
    status["lock"]["state"] = "private-live-lock-C:\\Users\\private\\lock"
    status["current_job"]["model"] = "C:\\Users\\private\\model.gguf"
    status["current_job"]["set"] = "private-prompt-bucket"
    status["latest_preflight"]["readiness_scope"] = "private-launch-scope"
    status["latest_preflight"]["saved_lock_state"]["state"] = "private-saved-lock"
    status["latest_preflight"]["blockers"] = [
        "stop_sentinel_present",
        "private-blocker-case-row",
    ]
    status["latest_preflight"]["ignored_blockers"] = [
        "private-ignored-blocker-worker-name",
    ]
    status["latest_preflight"]["state_mismatch_reasons"] = [
        "private-mismatch-C:\\Users\\private\\preflight.json",
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
    ]
    assert report["snapshot"]["latest_preflight"]["ignored_blockers"] == ["custom_or_invalid"]
    assert report["snapshot"]["latest_preflight"]["state_mismatch_reasons"] == ["custom_or_invalid"]
    assert report["snapshot"]["candidate_dimensions"]["review_gate_status"] == "custom_or_invalid"
    assert "private-live-lock" not in rendered
    assert "private-prompt-bucket" not in rendered
    assert "private-launch-scope" not in rendered
    assert "private-blocker-case-row" not in rendered
    assert "private-ignored-blocker" not in rendered
    assert "private-mismatch" not in rendered
    assert "private-review-gate" not in rendered
    assert "model.gguf" not in rendered


def test_project_bible_pickup_validator_rejects_custom_preflight_blocker_without_leak():
    validator = _load_pickup_validator()
    status = copy.deepcopy(_paused_status_fixture())
    status["latest_preflight"]["blockers"] = [
        "stop_sentinel_present",
        "private-blocker-case-row",
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
    ]
    assert "private-blocker-case-row" not in rendered


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
    assert report["summary"]["check_count"] == 38


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
    assert report["summary"]["check_count"] == 24


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
    assert report["summary"]["check_count"] == 24


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
    assert report["summary"]["check_count"] == 24


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
    assert report["summary"]["check_count"] == 24


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
    assert report["summary"]["check_count"] == 38


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
    assert report["summary"]["check_count"] == 38


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
    assert report["summary"]["check_count"] == 38


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
    assert report["summary"]["check_count"] == 38


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
    assert report["summary"]["check_count"] == 38


def test_project_bible_pickup_validator_rejects_failed_sister_project_report():
    validator = _load_pickup_validator()
    sister_report = {
        "summary": {
            "ok": False,
            "check_count": 27,
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
            "source_admission_missing_concept_count": 0,
            "project_privacy_issue_count": 0,
            "jurisdiction_pack_privacy_issue_count": 0,
            "grounding_metadata_privacy_issue_count": 0,
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
                "summary": "private path should not leak",
                "detail": "C:\\Users\\private\\worker-case-row.csv",
            },
            {"severity": "low", "summary": "another aggregate-only risk"},
        ],
        "failed_checks": None,
        "context_reset": {"recommended": True},
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
        "timestamp_present": True,
        "timestamp_valid": True,
        "validated_after_handoff": True,
        "session_state": "stopped",
        "next_action_source": "fallback",
        "next_action_priority": "normal",
        "open_risk_count": 2,
        "open_risks_shape": "list",
        "open_risk_severity_counts": {"low": 1, "medium": 1},
        "blocking_open_risk_count": 0,
        "failed_checks_present": False,
        "context_reset_recommended": True,
        "recent_edit_count": 2,
    }
    assert "worker-case-row" not in rendered
    assert "case-a.txt" not in rendered
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
    assert "claude_handoff_state_and_next_action_labels_are_known_if_present" in report["summary"]["failed_ids"]
    assert "claude_handoff_open_risk_severities_are_known_if_present" in report["summary"]["failed_ids"]
    assert report["claude_handoff"] == {
        "exists": True,
        "artifact_type": "custom_or_invalid",
        "timestamp_present": True,
        "timestamp_valid": True,
        "validated_after_handoff": True,
        "session_state": "custom_or_invalid",
        "next_action_source": "custom_or_invalid",
        "next_action_priority": "custom_or_invalid",
        "open_risk_count": 1,
        "open_risks_shape": "list",
        "open_risk_severity_counts": {"custom_or_invalid": 1},
        "blocking_open_risk_count": 0,
        "failed_checks_present": False,
        "context_reset_recommended": False,
        "recent_edit_count": 1,
    }
    assert "private-artifact-type" not in rendered
    assert "private-state" not in rendered
    assert "private-source" not in rendered
    assert "private-priority" not in rendered
    assert "private-risk-severity" not in rendered
    assert "case-a.txt" not in rendered
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
    assert report["claude_handoff"]["failed_checks_present"] is True
    assert "private_source_leak" not in rendered
    assert "case-log.txt" not in rendered
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
    assert '"check_count": 38' in printed
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
    assert '"check_count": 38' in printed
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
    assert "engine_process_not_alive" not in printed


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
    assert "engine_process_not_alive" not in printed
    assert "latest_preflight_matches_current_state" not in printed
    assert str(tmp_path) not in printed
