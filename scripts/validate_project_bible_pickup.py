#!/usr/bin/env python3
"""Validate the project-bible pickup handoff.

This is a read-only guard for Claude Code / Codex continuation sessions. It
checks that the project-bible docs are wired from the agent indexes and that the
live autonomous-engine status still matches the paused handoff boundary.

It does not start the autonomous engine, run preflight, call Ollama, or promote
candidate dimensions.
"""
from __future__ import annotations

import argparse
import ast
import json
import pathlib
import re
import sys
from datetime import datetime, timezone
from typing import Any

ROOT = pathlib.Path(__file__).resolve().parents[1]
SCRIPTS = pathlib.Path(__file__).resolve().parent
if str(SCRIPTS) not in sys.path:
    sys.path.insert(0, str(SCRIPTS))

import autonomous_engine  # noqa: E402
import validate_global_protections_saved_artifacts  # noqa: E402
import validate_sister_project_planning  # noqa: E402


KNOWN_HANDOFF_ARTIFACT_TYPES = frozenset({"structured-handoff"})
KNOWN_HANDOFF_VERSIONS = frozenset({"1.0.0", "2.0.0"})
KNOWN_HANDOFF_SESSION_STATES = frozenset({"stopped", "running", "paused", "idle"})
KNOWN_HANDOFF_NEXT_ACTION_SOURCES = frozenset({"fallback", "manual", "user", "codex", "claude"})
KNOWN_HANDOFF_PRIORITIES = frozenset({"low", "normal", "medium", "high", "urgent"})
KNOWN_HANDOFF_EFFORT_HINTS = frozenset({"low", "medium", "high"})
KNOWN_HANDOFF_CONTEXT_RESET_MODES = frozenset({"auto", "manual"})
KNOWN_HANDOFF_CONTEXT_RESET_CANDIDATE_KEYS = frozenset({
    "blocked_tasks",
    "failed_checks",
    "recent_edits",
    "session_age_minutes",
    "wip_tasks",
})
KNOWN_HANDOFF_CONTEXT_RESET_COUNT_KEYS = frozenset({
    "blockedTasks",
    "failedChecks",
    "recentEdits",
    "sessionAgeMinutes",
    "wipTasks",
})
KNOWN_HANDOFF_DECISIONS = frozenset({
    "canonical_handoff_artifact_written",
    "legacy_snapshot_mirrored",
})
KNOWN_HANDOFF_DECISION_ACTORS = frozenset({
    "claude",
    "codex",
    "manual",
    "pre-compact-save",
})
KNOWN_HANDOFF_PLAN_COUNT_KEYS = frozenset({
    "blocked",
    "recent_edits",
    "total",
    "wip",
})
KNOWN_HANDOFF_RISK_SEVERITIES = frozenset({"low", "medium", "high", "critical"})
KNOWN_HANDOFF_RISK_KINDS = frozenset({"verification"})
BLOCKING_HANDOFF_RISK_SEVERITIES = frozenset({"high", "critical"})
KNOWN_STATUS_JOB_SETS = frozenset({"curated", "full"})
KNOWN_STATUS_LOCK_STATES = frozenset({"absent", "stale", "live", "unknown"})
KNOWN_STATUS_READINESS_SCOPES = frozenset({"state_only", "launch"})
KNOWN_STATUS_PREFLIGHT_MODES = frozenset({"manual_preflight"})
KNOWN_STATUS_PREFLIGHT_SCHEMA_VERSIONS = frozenset({"autonomous_engine_preflight.v1"})
KNOWN_STATUS_PREFLIGHT_PATHS = frozenset({"reports/autonomous_engine_preflight.json"})
KNOWN_STATUS_ACTIVE_RUNNERS = frozenset({"rich_harness_lift.py"})
KNOWN_STATUS_RUBRIC_VERSIONS = frozenset({"v1", "v2"})
KNOWN_STATUS_HARNESS_VERSIONS = frozenset({"h1", "h2"})
KNOWN_STATUS_STOP_SENTINELS = frozenset({"reports/autonomous_engine.stop"})
KNOWN_STATUS_PREFLIGHT_BLOCKERS = frozenset({
    "stop_sentinel_present",
    "state_cursor_invalid",
    "state_queue_invalid",
    "live_engine_lock_present",
    "full_promptset_unavailable",
    "dimension_candidates_parse_error",
    "dimension_review_gate_unknown",
    "dimension_review_packet_missing",
    "dimension_review_packet_unreadable",
    "dimension_review_validation_missing",
    "dimension_review_validation_unreadable",
    "dimension_review_packet_stale",
    "dimension_review_validation_stale",
    "dimension_review_validation_not_ok",
    "dimension_review_validation_summary_malformed",
    "ollama_unavailable",
})
KNOWN_STATUS_MISMATCH_REASONS = frozenset({
    "preflight_report_missing",
    "preflight_report_unreadable",
    "preflight_report_not_object",
    "cursor_changed",
    "cursor_state_changed",
    "queue_state_changed",
    "current_job_changed",
    "pause_state_changed",
    "stop_sentinel_changed",
    "lock_changed",
})
KNOWN_STATUS_REVIEW_GATE_STATUSES = frozenset({
    "review_packet_missing",
    "review_packet_unreadable",
    "validation_missing",
    "validation_unreadable",
    "review_packet_stale_for_dimension_candidates",
    "validation_stale_for_review_packet",
    "validation_not_ok",
    "validation_summary_malformed",
    "proposals_ready_for_manual_merge",
    "validated_zero_proposals",
})
KNOWN_SISTER_PROJECT_IDS = validate_sister_project_planning.CANONICAL_PROJECT_IDS
KNOWN_SISTER_PROJECT_STATUSES = validate_sister_project_planning.KNOWN_PROJECT_STATUSES
KNOWN_SISTER_GROUNDING_DOMAINS = validate_sister_project_planning.CANONICAL_GROUNDING_DOMAINS
MIN_SISTER_PROJECT_CHECK_COUNT = 34
SAFE_MODEL_LABEL_RE = re.compile(r"^[A-Za-z0-9][A-Za-z0-9._:/+-]{0,80}$")
SAFE_FAILED_ID_RE = re.compile(r"^[a-z][a-z0-9_]{2,120}$")
STATUS_PATHLIKE_LABEL_RE = re.compile(
    r"(?i)(?:^[a-z]:/|^(?:file|https?|ftp|s3|mailto):/?|(?:^|/)(?:users|home|onedrive|documents|appdata|tmp|temp)(?:/|$)|\d{8,})"
)
BENIGN_CONTROL_PRIVATE_HINT_RE = re.compile(
    r"(?i)(?:[A-Z0-9._%+-]+@[A-Z0-9.-]+\.[A-Z]{2,}|(?:file|https?|ftp|s3|mailto):|\\Users\\|/users/|OneDrive/Documents|AppData/Local|\d{8,})"
)
BENIGN_CONTROL_PROMPT_SET = "configs/duecare/benchmarks/benign_control_prompts.json"
MIN_BENIGN_CONTROL_PROMPTS = 12
LOCAL_SCRIPT_IMPORT_PREFIXES = ("build_", "validate_")
LOCAL_SCRIPT_IMPORT_NAMES = frozenset({
    "_atomic",
    "artifact_path_policy",
    "autonomous_engine",
    "domain_grounding",
})
AUTONOMOUS_ENGINE_DEPENDENCY_FILES = [
    "scripts/_atomic.py",
]
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
REQUIRED_FILES = [
    "AGENTS.md",
    "CLAUDE.md",
    "ROOT_FILES.md",
    "PROJECT_BIBLE.md",
    "docs/CLAUDE_CODE_HANDOFF.md",
    "Plans.md",
    ".claude/rules/05_project_bible_pickup.md",
    "docs/FILE_PURPOSE_GUIDE.md",
    "docs/REPO_LAYOUT.md",
    "docs/codex/PROJECT_BIBLE.md",
    "docs/codex/README.md",
    "docs/codex/00_do_not_break.md",
    "docs/codex/00_kernel_compatibility_gate.md",
    "docs/codex/00_execution_order.md",
    "docs/codex/goal_commands/README.md",
    "docs/codex/goal_commands/13_project_bible_continuation.md",
    "scripts/autonomous_engine.py",
    "scripts/benchmark_leaderboard.py",
    "scripts/build_domain_grounding_manifest_proposal.py",
    "scripts/build_domain_source_review_packet.py",
    "scripts/rich_harness_lift.py",
    *AUTONOMOUS_ENGINE_DEPENDENCY_FILES,
    BENIGN_CONTROL_PROMPT_SET,
    "scripts/validate_global_protections_saved_artifacts.py",
    "scripts/validate_project_bible_pickup.py",
    "scripts/validate_sister_project_planning.py",
    "tests/test_autonomous_engine.py",
    "tests/test_artifact_path_policy.py",
    "tests/test_benchmark_leaderboard.py",
    "tests/test_build_domain_grounding_manifest_proposal.py",
    "tests/test_build_domain_source_review_packet.py",
    "tests/test_build_global_protections_project_plan.py",
    "tests/test_harness_v2.py",
    "tests/test_intent_split.py",
    "tests/test_plan.py",
    "tests/test_rubric_v2.py",
    "tests/test_validate_domain_source_review_packet.py",
    "tests/test_validate_global_protections_project_plan.py",
    "tests/test_validate_global_protections_saved_artifacts.py",
    "tests/test_validate_sister_project_planning.py",
    *GLOBAL_SAVED_ARTIFACT_VALIDATOR_DEPENDENCY_FILES,
]
CLAUDE_HANDOFF_ARTIFACT = ".claude/state/handoff-artifact.json"


def _read_text(rel_path: str, *, root: pathlib.Path = ROOT) -> str:
    return (root / rel_path).read_text(encoding="utf-8")


def _load_status_json(path: pathlib.Path) -> tuple[dict[str, Any] | None, str]:
    try:
        payload = json.loads(path.read_text(encoding="utf-8"))
    except OSError as exc:
        return None, type(exc).__name__
    except json.JSONDecodeError as exc:
        return None, f"JSONDecodeError: line {exc.lineno} column {exc.colno}"
    if not isinstance(payload, dict):
        return None, "status payload is not a JSON object"
    return payload, ""


def _check(check_id: str, ok: bool, *, expected: Any, actual: Any) -> dict[str, Any]:
    return {
        "id": check_id,
        "ok": bool(ok),
        "expected": expected,
        "actual": actual,
    }


def _failed_ids(checks: list[dict[str, Any]]) -> list[str]:
    return [str(check["id"]) for check in checks if check.get("ok") is not True]


def _replace_checks(report: dict[str, Any], checks: list[dict[str, Any]]) -> dict[str, Any]:
    failed = _failed_ids(checks)
    updated = dict(report)
    updated["checks"] = checks
    updated["summary"] = {
        "ok": failed == [],
        "check_count": len(checks),
        "failed_count": len(failed),
        "failed_ids": failed,
    }
    return updated


def _severity_counts(rows: Any) -> dict[str, int]:
    counts: dict[str, int] = {}
    if not isinstance(rows, list):
        return counts
    for row in rows:
        if not isinstance(row, dict):
            severity = "custom_or_invalid"
        else:
            severity = _known_handoff_label(
                row.get("severity"),
                allowed=KNOWN_HANDOFF_RISK_SEVERITIES,
                invalid_label="custom_or_invalid",
            )
            if severity is None:
                severity = "custom_or_invalid"
        counts[severity] = counts.get(severity, 0) + 1
    return dict(sorted(counts.items()))


def _risk_kind_counts(rows: Any) -> dict[str, int]:
    counts: dict[str, int] = {}
    if not isinstance(rows, list):
        return counts
    for row in rows:
        if not isinstance(row, dict):
            kind = "custom_or_invalid"
        elif "kind" not in row:
            kind = "absent"
        else:
            kind = (
                _known_handoff_label(
                    row.get("kind"),
                    allowed=KNOWN_HANDOFF_RISK_KINDS,
                )
                or "custom_or_invalid"
            )
        counts[kind] = counts.get(kind, 0) + 1
    return dict(sorted(counts.items()))


def _decision_log_counts(rows: Any) -> tuple[dict[str, int], dict[str, int]]:
    shape_counts: dict[str, int] = {}
    decision_counts: dict[str, int] = {}
    if not isinstance(rows, list):
        return {}, {}
    for row in rows:
        if not isinstance(row, dict):
            shape = "custom_or_invalid"
            decision = "custom_or_invalid"
        else:
            shape = "dict"
            decision = _known_handoff_label(
                row.get("decision"),
                allowed=KNOWN_HANDOFF_DECISIONS,
            ) or "custom_or_invalid"
        shape_counts[shape] = shape_counts.get(shape, 0) + 1
        decision_counts[decision] = decision_counts.get(decision, 0) + 1
    return dict(sorted(shape_counts.items())), dict(sorted(decision_counts.items()))


def _decision_log_actor_counts(rows: Any) -> dict[str, int]:
    counts: dict[str, int] = {}
    if not isinstance(rows, list):
        return counts
    for row in rows:
        if not isinstance(row, dict):
            actor = "custom_or_invalid"
        elif "actor" not in row:
            actor = "absent"
        else:
            actor = (
                _known_handoff_label(
                    row.get("actor"),
                    allowed=KNOWN_HANDOFF_DECISION_ACTORS,
                )
                or "custom_or_invalid"
            )
        counts[actor] = counts.get(actor, 0) + 1
    return dict(sorted(counts.items()))


def _decision_log_timestamp_shape_counts(rows: Any) -> dict[str, int]:
    counts: dict[str, int] = {}
    if not isinstance(rows, list):
        return counts
    for row in rows:
        if not isinstance(row, dict):
            shape = "custom_or_invalid"
        elif "timestamp" not in row:
            shape = "absent"
        elif _parse_handoff_timestamp(row.get("timestamp")) is not None:
            shape = "valid_iso8601"
        else:
            shape = "custom_or_invalid"
        counts[shape] = counts.get(shape, 0) + 1
    return dict(sorted(counts.items()))


def _plan_count_key_counts(payload: Any) -> dict[str, int]:
    counts: dict[str, int] = {}
    if not isinstance(payload, dict):
        return counts
    for key in payload:
        label = key if key in KNOWN_HANDOFF_PLAN_COUNT_KEYS else "custom_or_invalid"
        counts[label] = counts.get(label, 0) + 1
    return dict(sorted(counts.items()))


def _plan_count_value_shape_counts(payload: Any) -> dict[str, int]:
    counts: dict[str, int] = {}
    if not isinstance(payload, dict):
        return counts
    for value in payload.values():
        shape = "int" if isinstance(value, int) and not isinstance(value, bool) else "custom_or_invalid"
        counts[shape] = counts.get(shape, 0) + 1
    return dict(sorted(counts.items()))


def _known_handoff_label(
    value: Any,
    *,
    allowed: frozenset[str],
    invalid_label: str = "custom_or_invalid",
) -> str | None:
    if not isinstance(value, str) or not value:
        return None
    if value in allowed:
        return value
    return invalid_label


def _known_status_label(value: Any, *, allowed: frozenset[str]) -> str | None:
    return _known_handoff_label(value, allowed=allowed)


def _known_status_label_list(value: Any, *, allowed: frozenset[str]) -> list[str]:
    if value is None:
        return []
    if not isinstance(value, list):
        return ["custom_or_invalid"]
    labels = [
        _known_status_label(item, allowed=allowed) or "custom_or_invalid"
        for item in value
    ]
    return [label for label in labels if label is not None]


def _json_object_shape(payload: dict[str, Any], key: str) -> str:
    if key not in payload:
        return "absent"
    return "dict" if isinstance(payload.get(key), dict) else "custom_or_invalid"


def _json_list_shape(payload: dict[str, Any], key: str) -> str:
    if key not in payload:
        return "absent"
    return "list" if isinstance(payload.get(key), list) else "custom_or_invalid"


def _list_entry_shape_counts(rows: Any, *, expected_type: type) -> dict[str, int]:
    counts: dict[str, int] = {}
    if not isinstance(rows, list):
        return counts
    for row in rows:
        shape = expected_type.__name__ if isinstance(row, expected_type) else "custom_or_invalid"
        counts[shape] = counts.get(shape, 0) + 1
    return dict(sorted(counts.items()))


def _candidate_triggered_shape_counts(rows: Any) -> dict[str, int]:
    counts: dict[str, int] = {}
    if not isinstance(rows, list):
        return counts
    for row in rows:
        shape = _bool_field_shape(row, "triggered") if isinstance(row, dict) else "custom_or_invalid"
        counts[shape] = counts.get(shape, 0) + 1
    return dict(sorted(counts.items()))


def _candidate_triggered_value_counts(rows: Any) -> dict[str, int]:
    counts: dict[str, int] = {}
    if not isinstance(rows, list):
        return counts
    for row in rows:
        if not isinstance(row, dict):
            label = "custom_or_invalid"
        elif "triggered" not in row:
            label = "absent"
        elif isinstance(row.get("triggered"), bool):
            label = "true" if row.get("triggered") is True else "false"
        else:
            label = "custom_or_invalid"
        counts[label] = counts.get(label, 0) + 1
    return dict(sorted(counts.items()))


def _candidate_key_counts(rows: Any) -> dict[str, int]:
    counts: dict[str, int] = {}
    if not isinstance(rows, list):
        return counts
    for row in rows:
        key = (
            _known_handoff_label(
                row.get("key"),
                allowed=KNOWN_HANDOFF_CONTEXT_RESET_CANDIDATE_KEYS,
            ) or "custom_or_invalid"
            if isinstance(row, dict)
            else "custom_or_invalid"
        )
        counts[key] = counts.get(key, 0) + 1
    return dict(sorted(counts.items()))


def _candidate_numeric_shape_counts(rows: Any, key: str) -> dict[str, int]:
    counts: dict[str, int] = {}
    if not isinstance(rows, list):
        return counts
    for row in rows:
        if not isinstance(row, dict):
            shape = "custom_or_invalid"
        elif key not in row:
            shape = "absent"
        else:
            value = row.get(key)
            shape = "int" if isinstance(value, int) and not isinstance(value, bool) else "custom_or_invalid"
        counts[shape] = counts.get(shape, 0) + 1
    return dict(sorted(counts.items()))


def _candidate_trigger_consistency_counts(rows: Any) -> dict[str, int]:
    counts: dict[str, int] = {}
    if not isinstance(rows, list):
        return counts
    for row in rows:
        if not isinstance(row, dict):
            label = "custom_or_invalid"
        elif not isinstance(row.get("triggered"), bool):
            label = "custom_or_invalid" if "triggered" in row else "not_comparable"
        elif "actual" not in row or "threshold" not in row:
            label = "not_comparable"
        else:
            actual = row.get("actual")
            threshold = row.get("threshold")
            if (
                isinstance(actual, int)
                and not isinstance(actual, bool)
                and isinstance(threshold, int)
                and not isinstance(threshold, bool)
            ):
                expected_triggered = actual > threshold
                label = "consistent" if row["triggered"] is expected_triggered else "inconsistent"
            else:
                label = "custom_or_invalid"
        counts[label] = counts.get(label, 0) + 1
    return dict(sorted(counts.items()))


def _context_reset_count_key_counts(payload: Any) -> dict[str, int]:
    counts: dict[str, int] = {}
    if not isinstance(payload, dict):
        return counts
    for key in payload:
        label = key if key in KNOWN_HANDOFF_CONTEXT_RESET_COUNT_KEYS else "custom_or_invalid"
        counts[label] = counts.get(label, 0) + 1
    return dict(sorted(counts.items()))


def _context_reset_count_value_shape_counts(payload: Any) -> dict[str, int]:
    counts: dict[str, int] = {}
    if not isinstance(payload, dict):
        return counts
    for value in payload.values():
        shape = "int" if isinstance(value, int) and not isinstance(value, bool) else "custom_or_invalid"
        counts[shape] = counts.get(shape, 0) + 1
    return dict(sorted(counts.items()))


def _bool_field_shape(payload: dict[str, Any], key: str) -> str:
    if key not in payload:
        return "absent"
    return "bool" if isinstance(payload.get(key), bool) else "custom_or_invalid"


def _known_optional_handoff_label(
    payload: dict[str, Any],
    key: str,
    *,
    allowed: frozenset[str],
) -> str | None:
    if key not in payload:
        return None
    return _known_handoff_label(payload.get(key), allowed=allowed) or "custom_or_invalid"


def _hidden_failed_checks_shape(payload: dict[str, Any]) -> str:
    if "failed_checks" not in payload:
        return "absent"
    value = payload.get("failed_checks")
    if value is None:
        return "null"
    if isinstance(value, list):
        return "list"
    if isinstance(value, dict):
        return "dict"
    return "custom_or_invalid"


def _hidden_optional_task_list_snapshot(payload: dict[str, Any], key: str) -> dict[str, Any]:
    if key not in payload:
        return {"shape": "absent", "count": None}
    value = payload.get(key)
    if value is None:
        return {"shape": "null", "count": 0}
    if isinstance(value, list):
        return {"shape": "list", "count": len(value)}
    return {"shape": "custom_or_invalid", "count": None}


def _safe_model_label(value: Any) -> str | None:
    if not isinstance(value, str) or not value:
        return None
    if "\\" in value or "://" in value:
        return "custom_or_invalid"
    if STATUS_PATHLIKE_LABEL_RE.search(value):
        return "custom_or_invalid"
    if SAFE_MODEL_LABEL_RE.fullmatch(value):
        return value
    return "custom_or_invalid"


def _parse_handoff_timestamp(value: Any) -> datetime | None:
    if not isinstance(value, str) or not value:
        return None
    text = value[:-1] + "+00:00" if value.endswith("Z") else value
    try:
        parsed = datetime.fromisoformat(text)
    except ValueError:
        return None
    if parsed.tzinfo is None:
        return None
    return parsed.astimezone(timezone.utc)


def _claude_handoff_snapshot(
    root: pathlib.Path,
    *,
    validation_time: datetime | None = None,
) -> dict[str, Any]:
    path = root / CLAUDE_HANDOFF_ARTIFACT
    if not path.exists():
        return {"exists": False}
    try:
        payload = json.loads(path.read_text(encoding="utf-8"))
    except OSError as exc:
        return {"exists": True, "load_error": type(exc).__name__}
    except json.JSONDecodeError as exc:
        return {"exists": True, "load_error": f"JSONDecodeError: line {exc.lineno} column {exc.colno}"}
    if not isinstance(payload, dict):
        return {"exists": True, "load_error": "handoff payload is not a JSON object"}

    previous_state_shape = _json_object_shape(payload, "previous_state")
    previous_state = payload.get("previous_state") if previous_state_shape == "dict" else {}
    plan_counts_shape = _json_object_shape(previous_state, "plan_counts")
    plan_counts = previous_state.get("plan_counts") if plan_counts_shape == "dict" else {}
    plan_count_key_counts = _plan_count_key_counts(plan_counts)
    plan_count_value_shape_counts = _plan_count_value_shape_counts(plan_counts)
    session_state_shape = _json_object_shape(previous_state, "session_state")
    session_state = previous_state.get("session_state") if session_state_shape == "dict" else {}
    next_action_shape = _json_object_shape(payload, "next_action")
    next_action = payload.get("next_action") if next_action_shape == "dict" else {}
    decision_log_shape = _json_list_shape(payload, "decision_log")
    decision_log = payload.get("decision_log") if decision_log_shape == "list" else []
    decision_log_entry_shape_counts, decision_log_decision_counts = _decision_log_counts(
        decision_log
    )
    decision_log_actor_counts = _decision_log_actor_counts(decision_log)
    decision_log_timestamp_shape_counts = _decision_log_timestamp_shape_counts(
        decision_log
    )
    continuity_shape = _json_object_shape(payload, "continuity")
    continuity = payload.get("continuity") if continuity_shape == "dict" else {}
    continuity_plugin_first_workflow_shape = (
        _bool_field_shape(continuity, "plugin_first_workflow")
        if continuity_shape == "dict"
        else "absent"
    )
    continuity_resume_aware_shape = (
        _bool_field_shape(continuity, "resume_aware_effort_continuity")
        if continuity_shape == "dict"
        else "absent"
    )
    raw_context_reset = payload.get("context_reset")
    if "context_reset" not in payload:
        context_reset: dict[str, Any] = {}
        context_reset_shape = "absent"
        context_reset_recommended_shape = "absent"
        context_reset_policy_shape = "absent"
        context_reset_policy: dict[str, Any] = {}
        context_reset_policy_dry_run_shape = "absent"
        context_reset_policy_thresholds_shape = "absent"
        context_reset_threshold_key_counts: dict[str, int] = {}
        context_reset_threshold_value_shape_counts: dict[str, int] = {}
        context_reset_counters_shape = "absent"
        context_reset_counter_key_counts: dict[str, int] = {}
        context_reset_counter_value_shape_counts: dict[str, int] = {}
        context_reset_reasons_shape = "absent"
        context_reset_reason_entry_shape_counts: dict[str, int] = {}
        context_reset_candidates_shape = "absent"
        context_reset_candidate_entry_shape_counts: dict[str, int] = {}
        context_reset_candidate_triggered_shape_counts: dict[str, int] = {}
        context_reset_candidate_triggered_value_counts: dict[str, int] = {}
        context_reset_candidate_key_counts: dict[str, int] = {}
        context_reset_candidate_actual_shape_counts: dict[str, int] = {}
        context_reset_candidate_threshold_shape_counts: dict[str, int] = {}
        context_reset_candidate_trigger_consistency_counts: dict[str, int] = {}
    elif isinstance(raw_context_reset, dict):
        context_reset = raw_context_reset
        context_reset_shape = "dict"
        if "recommended" not in context_reset:
            context_reset_recommended_shape = "absent"
        elif isinstance(context_reset.get("recommended"), bool):
            context_reset_recommended_shape = "bool"
        else:
            context_reset_recommended_shape = "custom_or_invalid"
        context_reset_policy_shape = _json_object_shape(context_reset, "policy")
        context_reset_policy = (
            context_reset.get("policy")
            if context_reset_policy_shape == "dict"
            else {}
        )
        context_reset_policy_dry_run_shape = _bool_field_shape(
            context_reset_policy,
            "dryRun",
        ) if context_reset_policy_shape == "dict" else "absent"
        context_reset_policy_thresholds_shape = (
            _json_object_shape(context_reset_policy, "thresholds")
            if context_reset_policy_shape == "dict"
            else "absent"
        )
        context_reset_thresholds = (
            context_reset_policy.get("thresholds")
            if context_reset_policy_thresholds_shape == "dict"
            else {}
        )
        context_reset_threshold_key_counts = _context_reset_count_key_counts(
            context_reset_thresholds
        )
        context_reset_threshold_value_shape_counts = _context_reset_count_value_shape_counts(
            context_reset_thresholds
        )
        context_reset_counters_shape = _json_object_shape(context_reset, "counters")
        context_reset_counters = (
            context_reset.get("counters")
            if context_reset_counters_shape == "dict"
            else {}
        )
        context_reset_counter_key_counts = _context_reset_count_key_counts(
            context_reset_counters
        )
        context_reset_counter_value_shape_counts = _context_reset_count_value_shape_counts(
            context_reset_counters
        )
        context_reset_reasons_shape = _json_list_shape(context_reset, "reasons")
        context_reset_reasons = (
            context_reset.get("reasons")
            if context_reset_reasons_shape == "list"
            else []
        )
        context_reset_reason_entry_shape_counts = _list_entry_shape_counts(
            context_reset_reasons,
            expected_type=str,
        )
        context_reset_candidates_shape = _json_list_shape(context_reset, "candidates")
        context_reset_candidates = (
            context_reset.get("candidates")
            if context_reset_candidates_shape == "list"
            else []
        )
        context_reset_candidate_entry_shape_counts = _list_entry_shape_counts(
            context_reset_candidates,
            expected_type=dict,
        )
        context_reset_candidate_triggered_shape_counts = _candidate_triggered_shape_counts(
            context_reset_candidates
        )
        context_reset_candidate_triggered_value_counts = _candidate_triggered_value_counts(
            context_reset_candidates
        )
        context_reset_candidate_key_counts = _candidate_key_counts(
            context_reset_candidates
        )
        context_reset_candidate_actual_shape_counts = _candidate_numeric_shape_counts(
            context_reset_candidates,
            "actual",
        )
        context_reset_candidate_threshold_shape_counts = _candidate_numeric_shape_counts(
            context_reset_candidates,
            "threshold",
        )
        context_reset_candidate_trigger_consistency_counts = _candidate_trigger_consistency_counts(
            context_reset_candidates
        )
    else:
        context_reset = {}
        context_reset_shape = "custom_or_invalid"
        context_reset_recommended_shape = "absent"
        context_reset_policy_shape = "absent"
        context_reset_policy = {}
        context_reset_policy_dry_run_shape = "absent"
        context_reset_policy_thresholds_shape = "absent"
        context_reset_threshold_key_counts = {}
        context_reset_threshold_value_shape_counts = {}
        context_reset_counters_shape = "absent"
        context_reset_counter_key_counts = {}
        context_reset_counter_value_shape_counts = {}
        context_reset_reasons_shape = "absent"
        context_reset_reason_entry_shape_counts = {}
        context_reset_candidates_shape = "absent"
        context_reset_candidate_entry_shape_counts = {}
        context_reset_candidate_triggered_shape_counts = {}
        context_reset_candidate_triggered_value_counts = {}
        context_reset_candidate_key_counts = {}
        context_reset_candidate_actual_shape_counts = {}
        context_reset_candidate_threshold_shape_counts = {}
        context_reset_candidate_trigger_consistency_counts = {}
    recent_edits = payload.get("recentEdits")
    if "recentEdits" not in payload:
        recent_edits_shape = "absent"
    elif isinstance(recent_edits, list):
        recent_edits_shape = "list"
    else:
        recent_edits_shape = "custom_or_invalid"
    recent_edit_count = _strict_int(plan_counts.get("recent_edits"))
    if recent_edit_count is None and recent_edits_shape == "list":
        recent_edit_count = len(recent_edits)
    open_risks = payload.get("open_risks")
    if "open_risks" not in payload:
        open_risks_shape = "absent"
    elif isinstance(open_risks, list):
        open_risks_shape = "list"
    else:
        open_risks_shape = "custom_or_invalid"
    plan_items_snapshot = _hidden_optional_task_list_snapshot(payload, "planItems")
    wip_tasks_snapshot = _hidden_optional_task_list_snapshot(payload, "wipTasks")
    timestamp = _parse_handoff_timestamp(payload.get("timestamp"))
    if validation_time is None:
        validation_time = datetime.now(timezone.utc)
    if validation_time.tzinfo is None:
        validation_time = validation_time.replace(tzinfo=timezone.utc)
    validation_time = validation_time.astimezone(timezone.utc)
    open_risk_severity_counts = _severity_counts(open_risks)
    open_risk_kind_counts = _risk_kind_counts(open_risks)
    blocking_open_risk_count = sum(
        open_risk_severity_counts.get(severity, 0)
        for severity in BLOCKING_HANDOFF_RISK_SEVERITIES
    )
    failed_checks_shape = _hidden_failed_checks_shape(payload)
    failed_checks = payload.get("failed_checks")
    if failed_checks_shape == "list":
        failed_checks_present = len(failed_checks) > 0
    elif failed_checks_shape == "dict":
        failed_checks_present = bool(failed_checks)
    else:
        failed_checks_present = False

    return {
        "exists": True,
        "artifact_type": _known_handoff_label(
            payload.get("artifactType"),
            allowed=KNOWN_HANDOFF_ARTIFACT_TYPES,
        ),
        "version": _known_handoff_label(
            payload.get("version"),
            allowed=KNOWN_HANDOFF_VERSIONS,
        ),
        "legacy_version": _known_handoff_label(
            payload.get("legacy_version"),
            allowed=KNOWN_HANDOFF_VERSIONS,
        ),
        "timestamp_present": isinstance(payload.get("timestamp"), str) and bool(payload.get("timestamp")),
        "timestamp_valid": timestamp is not None,
        "validated_after_handoff": validation_time >= timestamp if timestamp is not None else None,
        "previous_state_shape": previous_state_shape,
        "session_state_shape": session_state_shape,
        "plan_counts_shape": plan_counts_shape,
        "plan_count_key_counts": plan_count_key_counts,
        "plan_count_value_shape_counts": plan_count_value_shape_counts,
        "next_action_shape": next_action_shape,
        "decision_log_shape": decision_log_shape,
        "decision_log_count": len(decision_log),
        "decision_log_entry_shape_counts": decision_log_entry_shape_counts,
        "decision_log_decision_counts": decision_log_decision_counts,
        "decision_log_actor_counts": decision_log_actor_counts,
        "decision_log_timestamp_shape_counts": decision_log_timestamp_shape_counts,
        "continuity_shape": continuity_shape,
        "continuity_plugin_first_workflow_shape": continuity_plugin_first_workflow_shape,
        "continuity_plugin_first_workflow": (
            continuity.get("plugin_first_workflow")
            if continuity_plugin_first_workflow_shape == "bool"
            else None
        ),
        "continuity_resume_aware_effort_continuity_shape": continuity_resume_aware_shape,
        "continuity_resume_aware_effort_continuity": (
            continuity.get("resume_aware_effort_continuity")
            if continuity_resume_aware_shape == "bool"
            else None
        ),
        "continuity_effort_hint": _known_optional_handoff_label(
            continuity,
            "effort_hint",
            allowed=KNOWN_HANDOFF_EFFORT_HINTS,
        ) if continuity_shape == "dict" else None,
        "session_state": _known_handoff_label(
            session_state.get("state"),
            allowed=KNOWN_HANDOFF_SESSION_STATES,
        ),
        "next_action_source": _known_handoff_label(
            next_action.get("source"),
            allowed=KNOWN_HANDOFF_NEXT_ACTION_SOURCES,
        ),
        "next_action_priority": _known_handoff_label(
            next_action.get("priority"),
            allowed=KNOWN_HANDOFF_PRIORITIES,
        ),
        "open_risk_count": (
            len(open_risks)
            if isinstance(open_risks, list)
            else 0
        ),
        "plan_items_shape": plan_items_snapshot["shape"],
        "plan_item_count": plan_items_snapshot["count"],
        "wip_tasks_shape": wip_tasks_snapshot["shape"],
        "wip_task_count": wip_tasks_snapshot["count"],
        "open_risks_shape": open_risks_shape,
        "open_risk_severity_counts": open_risk_severity_counts,
        "open_risk_kind_counts": open_risk_kind_counts,
        "blocking_open_risk_count": blocking_open_risk_count,
        "failed_checks_shape": failed_checks_shape,
        "failed_checks_present": failed_checks_present,
        "context_reset_recommended": (
            context_reset.get("recommended")
            if isinstance(context_reset.get("recommended"), bool)
            else None
        ),
        "context_reset_shape": context_reset_shape,
        "context_reset_recommended_shape": context_reset_recommended_shape,
        "context_reset_policy_shape": context_reset_policy_shape,
        "context_reset_policy_mode": _known_optional_handoff_label(
            context_reset_policy,
            "mode",
            allowed=KNOWN_HANDOFF_CONTEXT_RESET_MODES,
        ) if context_reset_policy_shape == "dict" else None,
        "context_reset_policy_dry_run_shape": context_reset_policy_dry_run_shape,
        "context_reset_policy_thresholds_shape": context_reset_policy_thresholds_shape,
        "context_reset_threshold_key_counts": context_reset_threshold_key_counts,
        "context_reset_threshold_value_shape_counts": context_reset_threshold_value_shape_counts,
        "context_reset_counters_shape": context_reset_counters_shape,
        "context_reset_counter_key_counts": context_reset_counter_key_counts,
        "context_reset_counter_value_shape_counts": context_reset_counter_value_shape_counts,
        "context_reset_reasons_shape": context_reset_reasons_shape,
        "context_reset_reason_entry_shape_counts": context_reset_reason_entry_shape_counts,
        "context_reset_candidates_shape": context_reset_candidates_shape,
        "context_reset_candidate_entry_shape_counts": context_reset_candidate_entry_shape_counts,
        "context_reset_candidate_triggered_shape_counts": context_reset_candidate_triggered_shape_counts,
        "context_reset_candidate_triggered_value_counts": context_reset_candidate_triggered_value_counts,
        "context_reset_candidate_key_counts": context_reset_candidate_key_counts,
        "context_reset_candidate_actual_shape_counts": context_reset_candidate_actual_shape_counts,
        "context_reset_candidate_threshold_shape_counts": context_reset_candidate_threshold_shape_counts,
        "context_reset_candidate_trigger_consistency_counts": context_reset_candidate_trigger_consistency_counts,
        "recent_edits_shape": recent_edits_shape,
        "recent_edit_count": _strict_int(recent_edit_count),
    }


def _claude_handoff_checks(snapshot: dict[str, Any]) -> list[dict[str, Any]]:
    load_error = snapshot.get("load_error")
    custom_handoff_label_fields = [
        field
        for field in ("session_state", "next_action_source", "next_action_priority")
        if snapshot.get(field) == "custom_or_invalid"
    ]
    return [
        _check(
            "claude_handoff_artifact_parseable_if_present",
            snapshot.get("exists") is not True or load_error is None,
            expected="absent or parseable JSON object",
            actual=load_error or "ok",
        ),
        _check(
            "claude_handoff_artifact_type_is_known_if_present",
            (
                snapshot.get("exists") is not True
                or snapshot.get("artifact_type") == "structured-handoff"
            ),
            expected={"artifact_type": "structured-handoff"},
            actual={"artifact_type": snapshot.get("artifact_type")},
        ),
        _check(
            "claude_handoff_versions_are_known_if_present",
            (
                snapshot.get("exists") is not True
                or all(
                    snapshot.get(field) in (None, *KNOWN_HANDOFF_VERSIONS)
                    for field in ("version", "legacy_version")
                )
            ),
            expected={"version": sorted(KNOWN_HANDOFF_VERSIONS), "legacy_version": sorted(KNOWN_HANDOFF_VERSIONS)},
            actual={
                "version": snapshot.get("version"),
                "legacy_version": snapshot.get("legacy_version"),
            },
        ),
        _check(
            "claude_handoff_state_and_next_action_labels_are_known_if_present",
            snapshot.get("exists") is not True or custom_handoff_label_fields == [],
            expected={"custom_or_invalid_fields": []},
            actual={"custom_or_invalid_fields": custom_handoff_label_fields},
        ),
        _check(
            "claude_handoff_nested_state_containers_are_objects_if_present",
            (
                snapshot.get("exists") is not True
                or all(
                    snapshot.get(field) in ("absent", "dict")
                    for field in (
                        "previous_state_shape",
                        "session_state_shape",
                        "plan_counts_shape",
                        "next_action_shape",
                    )
                )
            ),
            expected={
                "previous_state_shape": "absent_or_dict",
                "session_state_shape": "absent_or_dict",
                "plan_counts_shape": "absent_or_dict",
                "next_action_shape": "absent_or_dict",
            },
            actual={
                "previous_state_shape": snapshot.get("previous_state_shape"),
                "session_state_shape": snapshot.get("session_state_shape"),
                "plan_counts_shape": snapshot.get("plan_counts_shape"),
                "next_action_shape": snapshot.get("next_action_shape"),
            },
        ),
        _check(
            "claude_handoff_plan_count_keys_and_values_are_known_if_present",
            (
                snapshot.get("exists") is not True
                or snapshot.get("plan_counts_shape") != "dict"
                or (
                    "custom_or_invalid" not in snapshot.get(
                        "plan_count_key_counts", {}
                    )
                    and "custom_or_invalid" not in snapshot.get(
                        "plan_count_value_shape_counts", {}
                    )
                )
            ),
            expected={
                "plan_count_keys": sorted(KNOWN_HANDOFF_PLAN_COUNT_KEYS),
                "plan_count_value_shape_counts": {"int": "all_values"},
            },
            actual={
                "plan_count_key_counts": snapshot.get("plan_count_key_counts"),
                "plan_count_value_shape_counts": snapshot.get(
                    "plan_count_value_shape_counts"
                ),
            },
        ),
        _check(
            "claude_handoff_decision_log_is_list_if_present",
            (
                snapshot.get("exists") is not True
                or snapshot.get("decision_log_shape") in ("absent", "list")
            ),
            expected={"decision_log_shape": "absent_or_list"},
            actual={
                "decision_log_shape": snapshot.get("decision_log_shape"),
                "decision_log_count": snapshot.get("decision_log_count"),
            },
        ),
        _check(
            "claude_handoff_decision_log_entries_are_known_if_present",
            (
                snapshot.get("exists") is not True
                or snapshot.get("decision_log_shape") != "list"
                or (
                    "custom_or_invalid" not in snapshot.get("decision_log_entry_shape_counts", {})
                    and "custom_or_invalid" not in snapshot.get("decision_log_decision_counts", {})
                )
            ),
            expected={
                "decision_log_entry_shape_counts": {"dict": "all_entries"},
                "decision_log_decisions": sorted(KNOWN_HANDOFF_DECISIONS),
            },
            actual={
                "decision_log_entry_shape_counts": snapshot.get(
                    "decision_log_entry_shape_counts"
                ),
                "decision_log_decision_counts": snapshot.get(
                    "decision_log_decision_counts"
                ),
            },
        ),
        _check(
            "claude_handoff_decision_log_actor_and_timestamp_labels_are_known_if_present",
            (
                snapshot.get("exists") is not True
                or snapshot.get("decision_log_shape") != "list"
                or "custom_or_invalid" in snapshot.get(
                    "decision_log_entry_shape_counts", {}
                )
                or (
                    "custom_or_invalid" not in snapshot.get(
                        "decision_log_actor_counts", {}
                    )
                    and "custom_or_invalid" not in snapshot.get(
                        "decision_log_timestamp_shape_counts", {}
                    )
                )
            ),
            expected={
                "decision_log_actors": sorted(KNOWN_HANDOFF_DECISION_ACTORS),
                "decision_log_timestamp_shape_counts": {"absent_or_valid_iso8601": "all_entries"},
            },
            actual={
                "decision_log_actor_counts": snapshot.get("decision_log_actor_counts"),
                "decision_log_timestamp_shape_counts": snapshot.get(
                    "decision_log_timestamp_shape_counts"
                ),
            },
        ),
        _check(
            "claude_handoff_continuity_shape_and_labels_are_known_if_present",
            (
                snapshot.get("exists") is not True
                or (
                    snapshot.get("continuity_shape") in ("absent", "dict")
                    and snapshot.get("continuity_plugin_first_workflow_shape") in ("absent", "bool")
                    and snapshot.get("continuity_resume_aware_effort_continuity_shape") in ("absent", "bool")
                    and snapshot.get("continuity_effort_hint") in (None, *KNOWN_HANDOFF_EFFORT_HINTS)
                )
            ),
            expected={
                "continuity_shape": "absent_or_dict",
                "continuity_plugin_first_workflow_shape": "absent_or_bool",
                "continuity_resume_aware_effort_continuity_shape": "absent_or_bool",
                "continuity_effort_hint": sorted(KNOWN_HANDOFF_EFFORT_HINTS),
            },
            actual={
                "continuity_shape": snapshot.get("continuity_shape"),
                "continuity_plugin_first_workflow_shape": snapshot.get(
                    "continuity_plugin_first_workflow_shape"
                ),
                "continuity_resume_aware_effort_continuity_shape": snapshot.get(
                    "continuity_resume_aware_effort_continuity_shape"
                ),
                "continuity_effort_hint": snapshot.get("continuity_effort_hint"),
            },
        ),
        _check(
            "claude_handoff_timestamp_valid_if_present",
            snapshot.get("exists") is not True or snapshot.get("timestamp_valid") is True,
            expected="absent or valid ISO-8601 timestamp",
            actual={
                "timestamp_present": snapshot.get("timestamp_present"),
                "timestamp_valid": snapshot.get("timestamp_valid"),
            },
        ),
        _check(
            "claude_handoff_not_newer_than_validation_if_present",
            (
                snapshot.get("exists") is not True
                or snapshot.get("timestamp_valid") is not True
                or snapshot.get("validated_after_handoff") is True
            ),
            expected="absent or hidden handoff timestamp not newer than this validation run",
            actual={
                "timestamp_valid": snapshot.get("timestamp_valid"),
                "validated_after_handoff": snapshot.get("validated_after_handoff"),
            },
        ),
        _check(
            "claude_handoff_has_no_failed_checks_if_present",
            snapshot.get("exists") is not True or snapshot.get("failed_checks_present") is not True,
            expected="absent or no failed_checks entries",
            actual=load_error or {"failed_checks_present": snapshot.get("failed_checks_present")},
        ),
        _check(
            "claude_handoff_failed_checks_shape_is_known_if_present",
            (
                snapshot.get("exists") is not True
                or snapshot.get("failed_checks_shape") in ("absent", "null", "list", "dict")
            ),
            expected={"failed_checks_shape": "absent_null_list_or_dict"},
            actual={"failed_checks_shape": snapshot.get("failed_checks_shape")},
        ),
        _check(
            "claude_handoff_context_reset_is_bool_if_present",
            (
                snapshot.get("exists") is not True
                or (
                    snapshot.get("context_reset_shape") in ("absent", "dict")
                    and snapshot.get("context_reset_recommended_shape") in ("absent", "bool")
                )
            ),
            expected={
                "context_reset_shape": "absent_or_dict",
                "context_reset_recommended_shape": "absent_or_bool",
            },
            actual={
                "context_reset_shape": snapshot.get("context_reset_shape"),
                "context_reset_recommended_shape": snapshot.get("context_reset_recommended_shape"),
                "context_reset_recommended": snapshot.get("context_reset_recommended"),
            },
        ),
        _check(
            "claude_handoff_context_reset_policy_shape_and_labels_are_known_if_present",
            (
                snapshot.get("exists") is not True
                or (
                    snapshot.get("context_reset_policy_shape") in ("absent", "dict")
                    and snapshot.get("context_reset_policy_mode") in (
                        None,
                        *KNOWN_HANDOFF_CONTEXT_RESET_MODES,
                    )
                    and snapshot.get("context_reset_policy_dry_run_shape") in ("absent", "bool")
                    and snapshot.get("context_reset_policy_thresholds_shape") in ("absent", "dict")
                    and snapshot.get("context_reset_counters_shape") in ("absent", "dict")
                )
            ),
            expected={
                "context_reset_policy_shape": "absent_or_dict",
                "context_reset_policy_mode": sorted(KNOWN_HANDOFF_CONTEXT_RESET_MODES),
                "context_reset_policy_dry_run_shape": "absent_or_bool",
                "context_reset_policy_thresholds_shape": "absent_or_dict",
                "context_reset_counters_shape": "absent_or_dict",
            },
            actual={
                "context_reset_policy_shape": snapshot.get("context_reset_policy_shape"),
                "context_reset_policy_mode": snapshot.get("context_reset_policy_mode"),
                "context_reset_policy_dry_run_shape": snapshot.get(
                    "context_reset_policy_dry_run_shape"
                ),
                "context_reset_policy_thresholds_shape": snapshot.get(
                    "context_reset_policy_thresholds_shape"
                ),
                "context_reset_counters_shape": snapshot.get("context_reset_counters_shape"),
            },
        ),
        _check(
            "claude_handoff_context_reset_threshold_and_counter_keys_are_known_if_present",
            (
                snapshot.get("exists") is not True
                or snapshot.get("context_reset_shape") != "dict"
                or (
                    (
                        snapshot.get("context_reset_policy_thresholds_shape") != "dict"
                        or (
                            "custom_or_invalid" not in snapshot.get(
                                "context_reset_threshold_key_counts", {}
                            )
                            and "custom_or_invalid" not in snapshot.get(
                                "context_reset_threshold_value_shape_counts", {}
                            )
                        )
                    )
                    and (
                        snapshot.get("context_reset_counters_shape") != "dict"
                        or (
                            "custom_or_invalid" not in snapshot.get(
                                "context_reset_counter_key_counts", {}
                            )
                            and "custom_or_invalid" not in snapshot.get(
                                "context_reset_counter_value_shape_counts", {}
                            )
                        )
                    )
                )
            ),
            expected={
                "context_reset_count_keys": sorted(
                    KNOWN_HANDOFF_CONTEXT_RESET_COUNT_KEYS
                ),
                "context_reset_threshold_value_shape_counts": {"int": "all_values"},
                "context_reset_counter_value_shape_counts": {"int": "all_values"},
            },
            actual={
                "context_reset_threshold_key_counts": snapshot.get(
                    "context_reset_threshold_key_counts"
                ),
                "context_reset_threshold_value_shape_counts": snapshot.get(
                    "context_reset_threshold_value_shape_counts"
                ),
                "context_reset_counter_key_counts": snapshot.get(
                    "context_reset_counter_key_counts"
                ),
                "context_reset_counter_value_shape_counts": snapshot.get(
                    "context_reset_counter_value_shape_counts"
                ),
            },
        ),
        _check(
            "claude_handoff_context_reset_reason_and_candidate_shapes_are_known_if_present",
            (
                snapshot.get("exists") is not True
                or snapshot.get("context_reset_shape") != "dict"
                or (
                    snapshot.get("context_reset_reasons_shape") in ("absent", "list")
                    and "custom_or_invalid" not in snapshot.get(
                        "context_reset_reason_entry_shape_counts", {}
                    )
                    and snapshot.get("context_reset_candidates_shape") in ("absent", "list")
                    and "custom_or_invalid" not in snapshot.get(
                        "context_reset_candidate_entry_shape_counts", {}
                    )
                    and "custom_or_invalid" not in snapshot.get(
                        "context_reset_candidate_triggered_shape_counts", {}
                    )
                )
            ),
            expected={
                "context_reset_reasons_shape": "absent_or_list",
                "context_reset_reason_entry_shape_counts": {"str": "all_entries"},
                "context_reset_candidates_shape": "absent_or_list",
                "context_reset_candidate_entry_shape_counts": {"dict": "all_entries"},
                "context_reset_candidate_triggered_shape_counts": {
                    "absent_or_bool": "all_entries"
                },
            },
            actual={
                "context_reset_reasons_shape": snapshot.get("context_reset_reasons_shape"),
                "context_reset_reason_entry_shape_counts": snapshot.get(
                    "context_reset_reason_entry_shape_counts"
                ),
                "context_reset_candidates_shape": snapshot.get(
                    "context_reset_candidates_shape"
                ),
                "context_reset_candidate_entry_shape_counts": snapshot.get(
                    "context_reset_candidate_entry_shape_counts"
                ),
                "context_reset_candidate_triggered_shape_counts": snapshot.get(
                    "context_reset_candidate_triggered_shape_counts"
                ),
            },
        ),
        _check(
            "claude_handoff_context_reset_recommendation_matches_triggered_candidates_if_present",
            (
                snapshot.get("exists") is not True
                or snapshot.get("context_reset_candidates_shape") != "list"
                or snapshot.get("context_reset_recommended_shape") != "bool"
                or "custom_or_invalid" in snapshot.get(
                    "context_reset_candidate_entry_shape_counts", {}
                )
                or "custom_or_invalid" in snapshot.get(
                    "context_reset_candidate_triggered_shape_counts", {}
                )
                or snapshot.get(
                    "context_reset_candidate_triggered_value_counts", {}
                ).get("true", 0) == 0
                or snapshot.get("context_reset_recommended") is True
            ),
            expected={
                "triggered_true_candidate_count": 0,
                "or_context_reset_recommended": True,
            },
            actual={
                "context_reset_recommended": snapshot.get("context_reset_recommended"),
                "context_reset_candidate_triggered_value_counts": snapshot.get(
                    "context_reset_candidate_triggered_value_counts"
                ),
            },
        ),
        _check(
            "claude_handoff_context_reset_candidate_keys_and_numbers_are_known_if_present",
            (
                snapshot.get("exists") is not True
                or snapshot.get("context_reset_candidates_shape") != "list"
                or "custom_or_invalid" in snapshot.get(
                    "context_reset_candidate_entry_shape_counts", {}
                )
                or (
                    "custom_or_invalid" not in snapshot.get(
                        "context_reset_candidate_key_counts", {}
                    )
                    and "custom_or_invalid" not in snapshot.get(
                        "context_reset_candidate_actual_shape_counts", {}
                    )
                    and "custom_or_invalid" not in snapshot.get(
                        "context_reset_candidate_threshold_shape_counts", {}
                    )
                )
            ),
            expected={
                "context_reset_candidate_keys": sorted(
                    KNOWN_HANDOFF_CONTEXT_RESET_CANDIDATE_KEYS
                ),
                "context_reset_candidate_actual_shape_counts": {"absent_or_int": "all_entries"},
                "context_reset_candidate_threshold_shape_counts": {"absent_or_int": "all_entries"},
            },
            actual={
                "context_reset_candidate_key_counts": snapshot.get(
                    "context_reset_candidate_key_counts"
                ),
                "context_reset_candidate_actual_shape_counts": snapshot.get(
                    "context_reset_candidate_actual_shape_counts"
                ),
                "context_reset_candidate_threshold_shape_counts": snapshot.get(
                    "context_reset_candidate_threshold_shape_counts"
                ),
            },
        ),
        _check(
            "claude_handoff_context_reset_candidate_trigger_matches_numbers_if_present",
            (
                snapshot.get("exists") is not True
                or snapshot.get("context_reset_candidates_shape") != "list"
                or "custom_or_invalid" in snapshot.get(
                    "context_reset_candidate_entry_shape_counts", {}
                )
                or "custom_or_invalid" in snapshot.get(
                    "context_reset_candidate_triggered_shape_counts", {}
                )
                or "custom_or_invalid" in snapshot.get(
                    "context_reset_candidate_actual_shape_counts", {}
                )
                or "custom_or_invalid" in snapshot.get(
                    "context_reset_candidate_threshold_shape_counts", {}
                )
                or "inconsistent" not in snapshot.get(
                    "context_reset_candidate_trigger_consistency_counts", {}
                )
            ),
            expected={
                "context_reset_candidate_trigger_consistency_counts": {
                    "inconsistent": 0
                },
                "comparison": "triggered == (actual > threshold) when both numbers are present",
            },
            actual={
                "context_reset_candidate_trigger_consistency_counts": snapshot.get(
                    "context_reset_candidate_trigger_consistency_counts"
                ),
            },
        ),
        _check(
            "claude_handoff_recent_edits_are_list_if_present",
            (
                snapshot.get("exists") is not True
                or snapshot.get("recent_edits_shape") in ("absent", "list")
            ),
            expected={"recent_edits_shape": "absent_or_list"},
            actual={
                "recent_edits_shape": snapshot.get("recent_edits_shape"),
                "recent_edit_count": snapshot.get("recent_edit_count"),
            },
        ),
        _check(
            "claude_handoff_open_risks_are_list_if_present",
            (
                snapshot.get("exists") is not True
                or snapshot.get("open_risks_shape") in ("absent", "list")
            ),
            expected={"open_risks_shape": "absent_or_list"},
            actual={
                "open_risks_shape": snapshot.get("open_risks_shape"),
                "open_risk_count": snapshot.get("open_risk_count"),
            },
        ),
        _check(
            "claude_handoff_task_containers_are_lists_if_present",
            (
                snapshot.get("exists") is not True
                or (
                    snapshot.get("plan_items_shape") in ("absent", "null", "list")
                    and snapshot.get("wip_tasks_shape") in ("absent", "null", "list")
                )
            ),
            expected={
                "plan_items_shape": "absent_null_or_list",
                "wip_tasks_shape": "absent_null_or_list",
            },
            actual={
                "plan_items_shape": snapshot.get("plan_items_shape"),
                "plan_item_count": snapshot.get("plan_item_count"),
                "wip_tasks_shape": snapshot.get("wip_tasks_shape"),
                "wip_task_count": snapshot.get("wip_task_count"),
            },
        ),
        _check(
            "claude_handoff_has_no_high_or_critical_open_risks_if_present",
            (
                snapshot.get("exists") is not True
                or snapshot.get("blocking_open_risk_count") in (None, 0)
            ),
            expected={"blocking_open_risk_count": 0},
            actual={
                "open_risk_count": snapshot.get("open_risk_count"),
                "blocking_open_risk_count": snapshot.get("blocking_open_risk_count"),
                "open_risk_severity_counts": snapshot.get("open_risk_severity_counts"),
            },
        ),
        _check(
            "claude_handoff_open_risk_severities_are_known_if_present",
            (
                snapshot.get("exists") is not True
                or not isinstance(snapshot.get("open_risk_severity_counts"), dict)
                or snapshot.get("open_risk_severity_counts", {}).get("custom_or_invalid", 0) == 0
            ),
            expected={"custom_or_invalid": 0},
            actual={
                "open_risk_count": snapshot.get("open_risk_count"),
                "open_risk_severity_counts": snapshot.get("open_risk_severity_counts"),
            },
        ),
        _check(
            "claude_handoff_open_risk_kinds_are_known_if_present",
            (
                snapshot.get("exists") is not True
                or snapshot.get("open_risks_shape") != "list"
                or not isinstance(snapshot.get("open_risk_kind_counts"), dict)
                or snapshot.get("open_risk_kind_counts", {}).get("custom_or_invalid", 0) == 0
            ),
            expected={"open_risk_kinds": ["absent", *sorted(KNOWN_HANDOFF_RISK_KINDS)]},
            actual={
                "open_risk_count": snapshot.get("open_risk_count"),
                "open_risk_kind_counts": snapshot.get("open_risk_kind_counts"),
            },
        ),
    ]


def _text_contains(text: str, needles: list[str]) -> list[str]:
    return [needle for needle in needles if needle not in text]


def _local_script_import_path(module_name: str) -> str | None:
    root_name = module_name.split(".", 1)[0]
    if root_name in LOCAL_SCRIPT_IMPORT_NAMES or root_name.startswith(LOCAL_SCRIPT_IMPORT_PREFIXES):
        return f"scripts/{root_name}.py"
    return None


def _direct_local_script_imports(
    rel_path: str,
    *,
    root: pathlib.Path = ROOT,
) -> tuple[list[str], str | None]:
    try:
        tree = ast.parse(_read_text(rel_path, root=root))
    except SyntaxError as exc:
        return [], f"SyntaxError: line {exc.lineno} offset {exc.offset}"
    imports: set[str] = set()
    for node in ast.walk(tree):
        if isinstance(node, ast.Import):
            for alias in node.names:
                import_path = _local_script_import_path(alias.name)
                if import_path is not None:
                    imports.add(import_path)
        elif isinstance(node, ast.ImportFrom) and node.level == 0 and node.module:
            import_path = _local_script_import_path(node.module)
            if import_path is not None:
                imports.add(import_path)
    return sorted(imports), None


def _numbered_goal_command_files(root: pathlib.Path = ROOT) -> list[str]:
    command_dir = root / "docs" / "codex" / "goal_commands"
    return sorted(path.name for path in command_dir.glob("[0-9][0-9]_*.md"))


def _status_value(status: dict[str, Any], path: str) -> Any:
    value: Any = status
    for part in path.split("."):
        if not isinstance(value, dict):
            return None
        value = value.get(part)
    return value


def _strict_int(value: Any) -> int | None:
    return value if isinstance(value, int) and not isinstance(value, bool) else None


def _summary_int(summary: dict[str, Any], key: str) -> int | None:
    return _strict_int(summary.get(key))


def _safe_failed_ids(summary: dict[str, Any]) -> list[str]:
    if "failed_ids" not in summary or summary.get("failed_ids") is None:
        return []
    failed_ids = summary.get("failed_ids")
    if not isinstance(failed_ids, list):
        return ["custom_or_invalid"]
    safe_ids: list[str] = []
    for failed_id in failed_ids:
        if (
            isinstance(failed_id, str)
            and SAFE_FAILED_ID_RE.fullmatch(failed_id)
            and not STATUS_PATHLIKE_LABEL_RE.search(failed_id)
        ):
            safe_ids.append(failed_id)
        else:
            safe_ids.append("custom_or_invalid")
    return safe_ids


def _known_sister_label(value: Any, *, allowed: frozenset[str]) -> str | None:
    if not isinstance(value, str) or not value:
        return None
    if value in allowed:
        return value
    return "custom_or_invalid"


def _safe_current_job(status: dict[str, Any]) -> dict[str, Any]:
    current_job = status.get("current_job")
    if not isinstance(current_job, dict):
        return {"index": None, "model": None, "n": None, "set": None}
    return {
        "index": _strict_int(current_job.get("index")),
        "model": _safe_model_label(current_job.get("model")),
        "n": _strict_int(current_job.get("n")),
        "set": _known_status_label(current_job.get("set"), allowed=KNOWN_STATUS_JOB_SETS),
    }


def _status_shape_issues(status: Any) -> list[str]:
    if not isinstance(status, dict):
        return ["payload_not_object"]
    required_types = {
        "paused": bool,
        "stop_sentinel": str,
        "engine_process_alive": bool,
        "lock": dict,
        "latest_preflight": dict,
        "active_loop_scope": dict,
        "candidate_dimension_scope": dict,
    }
    issues = []
    for key, expected_type in required_types.items():
        value = status.get(key)
        if not isinstance(value, expected_type):
            issues.append(f"{key}:missing_or_not_{expected_type.__name__}")
    numeric_fields = (
        "cursor",
        "queue_len",
        "done",
        "current_job.index",
        "current_job.n",
        "full_promptset.prompt_count",
        "candidate_dimension_scope.rows",
        "candidate_dimension_scope.review_needed_count",
        "candidate_dimension_scope.current_job_prompt_dimension_cells",
        "candidate_dimension_scope.full_registry_prompt_dimension_cells",
    )
    for path in numeric_fields:
        if _strict_int(_status_value(status, path)) is None:
            issues.append(f"{path}:missing_or_not_int")
    return issues


def _status_snapshot(status: dict[str, Any]) -> dict[str, Any]:
    latest_preflight = status.get("latest_preflight")
    active_scope = status.get("active_loop_scope")
    candidate_scope = status.get("candidate_dimension_scope")
    full_promptset = status.get("full_promptset")
    snapshot: dict[str, Any] = {
        "paused": status.get("paused") if isinstance(status.get("paused"), bool) else None,
        "stop_sentinel": _known_status_label(
            status.get("stop_sentinel"),
            allowed=KNOWN_STATUS_STOP_SENTINELS,
        ),
        "engine_process_alive": (
            status.get("engine_process_alive")
            if isinstance(status.get("engine_process_alive"), bool)
            else None
        ),
        "lock_state": _known_status_label(
            _status_value(status, "lock.state"),
            allowed=KNOWN_STATUS_LOCK_STATES,
        ),
        "current_job": _safe_current_job(status),
        "queue": {
            "cursor": _strict_int(status.get("cursor")),
            "queue_len": _strict_int(status.get("queue_len")),
            "done": _strict_int(status.get("done")),
        },
        "full_promptset": {
            "prompt_count": _strict_int(full_promptset.get("prompt_count")) if isinstance(full_promptset, dict) else None,
        },
        "latest_preflight": {
            "exists": _status_value(status, "latest_preflight.exists"),
            "path": _known_status_label(
                _status_value(status, "latest_preflight.path"),
                allowed=KNOWN_STATUS_PREFLIGHT_PATHS,
            ),
            "ready": _status_value(status, "latest_preflight.ready"),
            "mode": _known_status_label(
                _status_value(status, "latest_preflight.mode"),
                allowed=KNOWN_STATUS_PREFLIGHT_MODES,
            ),
            "schema_version": _known_status_label(
                _status_value(status, "latest_preflight.schema_version"),
                allowed=KNOWN_STATUS_PREFLIGHT_SCHEMA_VERSIONS,
            ),
            "readiness_scope": _known_status_label(
                _status_value(status, "latest_preflight.readiness_scope"),
                allowed=KNOWN_STATUS_READINESS_SCOPES,
            ),
            "ollama_checked": _status_value(status, "latest_preflight.ollama_checked"),
            "launch_ready_requires_ollama_check": _status_value(
                status,
                "latest_preflight.launch_ready_requires_ollama_check",
            ),
            "matches_current_state": _status_value(status, "latest_preflight.matches_current_state"),
            "needs_refresh": _status_value(status, "latest_preflight.needs_refresh"),
            "saved_lock_state": _known_status_label(
                _status_value(status, "latest_preflight.saved_lock_state.state"),
                allowed=KNOWN_STATUS_LOCK_STATES,
            ),
            "dimension_review_status": _known_status_label(
                _status_value(status, "latest_preflight.dimension_review_status"),
                allowed=KNOWN_STATUS_REVIEW_GATE_STATUSES,
            ),
            "blockers": _known_status_label_list(
                latest_preflight.get("blockers") if isinstance(latest_preflight, dict) else None,
                allowed=KNOWN_STATUS_PREFLIGHT_BLOCKERS,
            ),
            "ignored_blockers": _known_status_label_list(
                latest_preflight.get("ignored_blockers") if isinstance(latest_preflight, dict) else None,
                allowed=KNOWN_STATUS_PREFLIGHT_BLOCKERS,
            ),
            "state_mismatch_reasons": _known_status_label_list(
                latest_preflight.get("state_mismatch_reasons") if isinstance(latest_preflight, dict) else None,
                allowed=KNOWN_STATUS_MISMATCH_REASONS,
            ),
        },
        "active_loop_scope": {
            "runner": _known_status_label(
                _status_value(status, "active_loop_scope.runner"),
                allowed=KNOWN_STATUS_ACTIVE_RUNNERS,
            ),
            "candidate_dimension_sweep_active": _status_value(
                status,
                "active_loop_scope.candidate_dimension_sweep_active",
            ),
            "rubric_version": _known_status_label(
                _status_value(status, "active_loop_scope.rubric_version"),
                allowed=KNOWN_STATUS_RUBRIC_VERSIONS,
            ),
            "opt_in_rubric_versions_excluded": _known_status_label_list(
                active_scope.get("opt_in_rubric_versions_excluded")
                if isinstance(active_scope, dict)
                else None,
                allowed=KNOWN_STATUS_RUBRIC_VERSIONS,
            ),
            "rubric_version_mixing_allowed": _status_value(
                status,
                "active_loop_scope.rubric_version_mixing_allowed",
            ),
            "harness_version": _known_status_label(
                _status_value(status, "active_loop_scope.harness_version"),
                allowed=KNOWN_STATUS_HARNESS_VERSIONS,
            ),
            "opt_in_harness_versions_excluded": _known_status_label_list(
                active_scope.get("opt_in_harness_versions_excluded")
                if isinstance(active_scope, dict)
                else None,
                allowed=KNOWN_STATUS_HARNESS_VERSIONS,
            ),
            "harness_version_mixing_allowed": _status_value(
                status,
                "active_loop_scope.harness_version_mixing_allowed",
            ),
        },
        "candidate_dimensions": {
            "rows": (
                _strict_int(candidate_scope.get("rows"))
                if isinstance(candidate_scope, dict)
                else None
            ),
            "review_gate_status": _known_status_label(
                _status_value(status, "candidate_dimension_scope.review_gate_status"),
                allowed=KNOWN_STATUS_REVIEW_GATE_STATUSES,
            ),
            "active_in_autonomous_engine": _status_value(status, "candidate_dimension_scope.active_in_autonomous_engine"),
            "ready_for_mass_grading": _status_value(status, "candidate_dimension_scope.ready_for_mass_grading"),
            "active_rubric_promotion_ready": _status_value(status, "candidate_dimension_scope.active_rubric_promotion_ready"),
            "review_needed_count": _strict_int(_status_value(status, "candidate_dimension_scope.review_needed_count")),
            "current_job_prompt_dimension_cells": _strict_int(_status_value(
                status,
                "candidate_dimension_scope.current_job_prompt_dimension_cells",
            )),
            "full_registry_prompt_dimension_cells": _strict_int(_status_value(
                status,
                "candidate_dimension_scope.full_registry_prompt_dimension_cells",
            )),
        },
    }
    return snapshot


def _custom_status_label_fields(snapshot: dict[str, Any]) -> list[str]:
    fields: list[str] = []
    if snapshot.get("stop_sentinel") == "custom_or_invalid":
        fields.append("stop_sentinel")
    if snapshot.get("lock_state") == "custom_or_invalid":
        fields.append("lock.state")

    current_job = snapshot.get("current_job")
    if isinstance(current_job, dict):
        for key in ("model", "set"):
            if current_job.get(key) == "custom_or_invalid":
                fields.append(f"current_job.{key}")

    latest_preflight = snapshot.get("latest_preflight")
    if isinstance(latest_preflight, dict):
        for key in (
            "mode",
            "schema_version",
            "readiness_scope",
            "saved_lock_state",
            "dimension_review_status",
        ):
            if latest_preflight.get(key) == "custom_or_invalid":
                fields.append(f"latest_preflight.{key}")
        for key in ("blockers", "ignored_blockers", "state_mismatch_reasons"):
            values = latest_preflight.get(key)
            if isinstance(values, list) and "custom_or_invalid" in values:
                fields.append(f"latest_preflight.{key}")

    active_scope = snapshot.get("active_loop_scope")
    if isinstance(active_scope, dict):
        for key in ("runner", "rubric_version", "harness_version"):
            if active_scope.get(key) == "custom_or_invalid":
                fields.append(f"active_loop_scope.{key}")
        for key in ("opt_in_rubric_versions_excluded", "opt_in_harness_versions_excluded"):
            values = active_scope.get(key)
            if isinstance(values, list) and "custom_or_invalid" in values:
                fields.append(f"active_loop_scope.{key}")

    candidate_dimensions = snapshot.get("candidate_dimensions")
    if isinstance(candidate_dimensions, dict):
        if candidate_dimensions.get("review_gate_status") == "custom_or_invalid":
            fields.append("candidate_dimension_scope.review_gate_status")

    return fields


def _sister_project_snapshot(report: dict[str, Any]) -> dict[str, Any]:
    summary = report.get("summary") if isinstance(report, dict) else {}
    if not isinstance(summary, dict):
        summary = {}
    return {
        "ok": summary.get("ok") if isinstance(summary.get("ok"), bool) else None,
        "check_count": _summary_int(summary, "check_count"),
        "failed_count": _summary_int(summary, "failed_count"),
        "failed_ids": _safe_failed_ids(summary),
        "project_id": _known_sister_label(
            summary.get("project_id"),
            allowed=KNOWN_SISTER_PROJECT_IDS,
        ),
        "project_status": _known_sister_label(
            summary.get("project_status"),
            allowed=KNOWN_SISTER_PROJECT_STATUSES,
        ),
        "project_pack_id_match": (
            summary.get("project_pack_id_match")
            if isinstance(summary.get("project_pack_id_match"), bool)
            else None
        ),
        "grounding_domain": _known_sister_label(
            summary.get("grounding_domain"),
            allowed=KNOWN_SISTER_GROUNDING_DOMAINS,
        ),
        "scheme_prompt_count": (
            _summary_int(summary, "scheme_prompt_count")
        ),
        "scheme_prompt_category_count": (
            _summary_int(summary, "scheme_prompt_category_count")
        ),
        "scheme_prompt_candidate_pattern_count": (
            _summary_int(summary, "scheme_prompt_candidate_pattern_count")
        ),
        "scheme_prompt_candidate_patterns_without_project_declaration_count": (
            _summary_int(summary, "scheme_prompt_candidate_patterns_without_project_declaration_count")
        ),
        "scheme_prompt_unresolved_scope_count": (
            _summary_int(summary, "scheme_prompt_unresolved_scope_count")
        ),
        "scheme_prompt_not_ready_count": (
            _summary_int(summary, "scheme_prompt_not_ready_count")
        ),
        "scheme_prompt_categories_without_source_slots_count": (
            _summary_int(summary, "scheme_prompt_categories_without_source_slots_count")
        ),
        "queued_jurisdiction_scope_count": (
            _summary_int(summary, "queued_jurisdiction_scope_count")
        ),
        "local_source_jurisdictions_without_scope_count": (
            _summary_int(summary, "local_source_jurisdictions_without_scope_count")
        ),
        "duplicate_id_issue_count": (
            _summary_int(summary, "duplicate_id_issue_count")
        ),
        "readiness_gate_missing_block_concept_count": (
            _summary_int(summary, "readiness_gate_missing_block_concept_count")
        ),
        "source_admission_missing_concept_count": (
            _summary_int(summary, "source_admission_missing_concept_count")
        ),
        "scored_capability_missing_concept_count": (
            _summary_int(summary, "scored_capability_missing_concept_count")
        ),
        "project_privacy_issue_count": (
            _summary_int(summary, "project_privacy_issue_count")
        ),
        "jurisdiction_pack_privacy_issue_count": (
            _summary_int(summary, "jurisdiction_pack_privacy_issue_count")
        ),
        "grounding_metadata_privacy_issue_count": (
            _summary_int(summary, "grounding_metadata_privacy_issue_count")
        ),
        "grounding_source_privacy_issue_count": (
            _summary_int(summary, "grounding_source_privacy_issue_count")
        ),
        "scheme_prompt_privacy_issue_count": (
            _summary_int(summary, "scheme_prompt_privacy_issue_count")
        ),
    }


def _sister_project_checks(report: dict[str, Any]) -> list[dict[str, Any]]:
    snapshot = _sister_project_snapshot(report)
    return [
        _check(
            "sister_project_planning_validator_passes",
            (
                snapshot.get("ok") is True
                and isinstance(snapshot.get("check_count"), int)
                and snapshot.get("check_count") >= MIN_SISTER_PROJECT_CHECK_COUNT
                and snapshot.get("failed_count") == 0
                and snapshot.get("failed_ids") == []
                and snapshot.get("project_id") == "global_protections_regulatory_benchmark"
                and snapshot.get("project_status") == "propose_only"
                and snapshot.get("grounding_domain") == "developing_country_worker_protections"
                and snapshot.get("duplicate_id_issue_count") == 0
                and snapshot.get("readiness_gate_missing_block_concept_count") == 0
                and snapshot.get("source_admission_missing_concept_count") == 0
                and snapshot.get("scored_capability_missing_concept_count") == 0
                and snapshot.get("project_privacy_issue_count") == 0
                and snapshot.get("jurisdiction_pack_privacy_issue_count") == 0
                and snapshot.get("grounding_metadata_privacy_issue_count") == 0
                and snapshot.get("grounding_source_privacy_issue_count") == 0
                and snapshot.get("scheme_prompt_privacy_issue_count") == 0
            ),
            expected={
                "ok": True,
                "check_count": f">={MIN_SISTER_PROJECT_CHECK_COUNT}",
                "failed_count": 0,
                "failed_ids": [],
                "project_id": "global_protections_regulatory_benchmark",
                "project_status": "propose_only",
                "grounding_domain": "developing_country_worker_protections",
            },
            actual={
                "ok": snapshot.get("ok"),
                "check_count": snapshot.get("check_count"),
                "failed_count": snapshot.get("failed_count"),
                "failed_ids": snapshot.get("failed_ids"),
                "project_id": snapshot.get("project_id"),
                "project_status": snapshot.get("project_status"),
                "grounding_domain": snapshot.get("grounding_domain"),
                "duplicate_id_issue_count": snapshot.get("duplicate_id_issue_count"),
                "readiness_gate_missing_block_concept_count": snapshot.get(
                    "readiness_gate_missing_block_concept_count"
                ),
                "source_admission_missing_concept_count": snapshot.get(
                    "source_admission_missing_concept_count"
                ),
                "scored_capability_missing_concept_count": snapshot.get(
                    "scored_capability_missing_concept_count"
                ),
                "project_privacy_issue_count": snapshot.get("project_privacy_issue_count"),
                "jurisdiction_pack_privacy_issue_count": snapshot.get(
                    "jurisdiction_pack_privacy_issue_count"
                ),
                "grounding_metadata_privacy_issue_count": snapshot.get(
                    "grounding_metadata_privacy_issue_count"
                ),
                "grounding_source_privacy_issue_count": snapshot.get(
                    "grounding_source_privacy_issue_count"
                ),
                "scheme_prompt_privacy_issue_count": snapshot.get(
                    "scheme_prompt_privacy_issue_count"
                ),
            },
        ),
    ]


def _global_protections_saved_report_for_root(root: pathlib.Path) -> dict[str, Any]:
    component_dir = root / "reports" / "benchmark"
    return validate_global_protections_saved_artifacts.validate_saved_artifacts(
        project_config_path=(
            root
            / "configs"
            / "duecare"
            / "benchmarks"
            / "sister_projects"
            / "global_protections_regulatory_benchmark.json"
        ),
        registry_path=root / "configs" / "duecare" / "benchmarks" / "domains" / "registry.json",
        regulatory_catalog_path=root / "configs" / "duecare" / "benchmarks" / "regulatory_miss_patterns.json",
        component_dir=component_dir,
    )


def _global_protections_snapshot(report: dict[str, Any]) -> dict[str, Any]:
    summary: dict[str, Any] = {}
    if isinstance(report, dict) and isinstance(report.get("summary"), dict):
        summary = report["summary"]
    elif isinstance(report, dict) and "valid" in report:
        summary = report
    if not isinstance(summary, dict):
        summary = {}
    return {
        "valid": summary.get("valid") if isinstance(summary.get("valid"), bool) else None,
        "artifact_count": (
            _summary_int(summary, "artifact_count")
        ),
        "valid_artifact_count": (
            _summary_int(summary, "valid_artifact_count")
        ),
        "failed_artifact_count": (
            _summary_int(summary, "failed_artifact_count")
        ),
        "missing_or_unreadable_artifact_count": (
            _summary_int(summary, "missing_or_unreadable_artifact_count")
        ),
        "markdown_artifact_count": (
            _summary_int(summary, "markdown_artifact_count")
        ),
        "missing_or_unreadable_markdown_count": (
            _summary_int(summary, "missing_or_unreadable_markdown_count")
        ),
        "unsafe_markdown_count": (
            _summary_int(summary, "unsafe_markdown_count")
        ),
        "artifact_path_mismatch_count": (
            _summary_int(summary, "artifact_path_mismatch_count")
        ),
        "total_check_count": (
            _summary_int(summary, "total_check_count")
        ),
        "total_failed_check_count": (
            _summary_int(summary, "total_failed_check_count")
        ),
        "suite_check_count": (
            _summary_int(summary, "suite_check_count")
        ),
        "suite_failed_check_count": (
            _summary_int(summary, "suite_failed_check_count")
        ),
        "phase_coverage_mismatch_count": (
            _summary_int(summary, "phase_coverage_mismatch_count")
        ),
        "legal_anchor_channel_mismatch_count": (
            _summary_int(summary, "legal_anchor_channel_mismatch_count")
        ),
        "readiness_blocker_mismatch_count": (
            _summary_int(summary, "readiness_blocker_mismatch_count")
        ),
        "next_phase_coverage": {
            "phase_count": _summary_int(summary, "curation_bundle_next_execution_phase_count"),
            "covered_actions": _summary_int(summary, "curation_bundle_next_phase_covered_actions"),
        },
        "curator_phase_coverage": {
            "phase_count": _summary_int(summary, "curation_bundle_curator_execution_phase_count"),
            "covered_actions": _summary_int(summary, "curation_bundle_curator_phase_covered_actions"),
        },
        "ready_for_comparable_scoring": (
            summary.get("ready_for_comparable_scoring")
            if isinstance(summary.get("ready_for_comparable_scoring"), bool)
            else None
        ),
    }


def _global_protections_checks(report: dict[str, Any]) -> list[dict[str, Any]]:
    snapshot = _global_protections_snapshot(report)
    return [
        _check(
            "global_protections_saved_artifacts_validator_passes",
            (
                snapshot.get("valid") is True
                and snapshot.get("artifact_count") == 13
                and snapshot.get("valid_artifact_count") == 13
                and snapshot.get("failed_artifact_count") == 0
                and snapshot.get("missing_or_unreadable_artifact_count") == 0
                and snapshot.get("markdown_artifact_count") == 13
                and snapshot.get("missing_or_unreadable_markdown_count") == 0
                and snapshot.get("unsafe_markdown_count") == 0
                and snapshot.get("artifact_path_mismatch_count") == 0
                and isinstance(snapshot.get("total_check_count"), int)
                and snapshot.get("total_check_count") >= 157
                and snapshot.get("total_failed_check_count") == 0
                and isinstance(snapshot.get("suite_check_count"), int)
                and snapshot.get("suite_check_count") >= 21
                and snapshot.get("suite_failed_check_count") == 0
                and snapshot.get("phase_coverage_mismatch_count") == 0
                and snapshot.get("legal_anchor_channel_mismatch_count") == 0
                and snapshot.get("readiness_blocker_mismatch_count") == 0
                and snapshot.get("next_phase_coverage") == {
                    "phase_count": 5,
                    "covered_actions": 34,
                }
                and snapshot.get("curator_phase_coverage") == {
                    "phase_count": 5,
                    "covered_actions": 34,
                }
                and snapshot.get("ready_for_comparable_scoring") is False
            ),
            expected={
                "valid": True,
                "artifact_count": 13,
                "valid_artifact_count": 13,
                "failed_artifact_count": 0,
                "missing_or_unreadable_artifact_count": 0,
                "markdown_artifact_count": 13,
                "missing_or_unreadable_markdown_count": 0,
                "unsafe_markdown_count": 0,
                "artifact_path_mismatch_count": 0,
                "total_check_count": ">=157",
                "total_failed_check_count": 0,
                "suite_check_count": ">=21",
                "suite_failed_check_count": 0,
                "phase_coverage_mismatch_count": 0,
                "legal_anchor_channel_mismatch_count": 0,
                "readiness_blocker_mismatch_count": 0,
                "next_phase_coverage": {"phase_count": 5, "covered_actions": 34},
                "curator_phase_coverage": {"phase_count": 5, "covered_actions": 34},
                "ready_for_comparable_scoring": False,
            },
            actual=snapshot,
        ),
    ]


def _sister_project_report_for_root(root: pathlib.Path) -> dict[str, Any]:
    sister_dir = root / "configs" / "duecare" / "benchmarks" / "sister_projects"
    domain_dir = (
        root
        / "configs"
        / "duecare"
        / "benchmarks"
        / "domains"
        / "developing_country_worker_protections"
    )
    return validate_sister_project_planning.build_report(
        project_config_path=sister_dir / "global_protections_regulatory_benchmark.json",
        jurisdiction_packs_path=sister_dir / "global_protections_jurisdiction_packs.json",
        grounding_sources_path=domain_dir / "grounding_sources.json",
        scheme_prompts_path=domain_dir / "scheme_prompts.jsonl",
    )


def _benign_control_prompt_set_snapshot(root: pathlib.Path) -> dict[str, Any]:
    snapshot: dict[str, Any] = {
        "read_error": None,
        "doc_shape": None,
        "top_level_intent": None,
        "prompts_shape": None,
        "prompt_count": 0,
        "row_shape_issue_count": 0,
        "missing_id_count": 0,
        "duplicate_id_count": 0,
        "non_benign_intent_count": 0,
        "blank_text_count": 0,
        "private_hint_count": 0,
    }
    try:
        payload = json.loads((root / BENIGN_CONTROL_PROMPT_SET).read_text(encoding="utf-8"))
    except json.JSONDecodeError:
        snapshot["read_error"] = "json_decode_error"
        return snapshot
    except OSError:
        snapshot["read_error"] = "read_error"
        return snapshot
    if not isinstance(payload, dict):
        snapshot["doc_shape"] = "custom_or_invalid"
        return snapshot
    snapshot["doc_shape"] = "dict"
    snapshot["top_level_intent"] = (
        "benign_control" if payload.get("intent") == "benign_control" else "custom_or_invalid"
    )
    prompts = payload.get("prompts")
    if not isinstance(prompts, list):
        snapshot["prompts_shape"] = "custom_or_invalid"
        return snapshot
    snapshot["prompts_shape"] = "list"
    snapshot["prompt_count"] = len(prompts)
    seen_ids: set[str] = set()
    duplicate_count = 0
    for row in prompts:
        if not isinstance(row, dict):
            snapshot["row_shape_issue_count"] += 1
            continue
        prompt_id = row.get("id")
        if isinstance(prompt_id, str) and prompt_id.strip():
            normalized_id = prompt_id.strip()
            if normalized_id in seen_ids:
                duplicate_count += 1
            seen_ids.add(normalized_id)
        else:
            snapshot["missing_id_count"] += 1
        if row.get("intent") != "benign":
            snapshot["non_benign_intent_count"] += 1
        text = row.get("text")
        if not isinstance(text, str) or not text.strip():
            snapshot["blank_text_count"] += 1
        elif BENIGN_CONTROL_PRIVATE_HINT_RE.search(text):
            snapshot["private_hint_count"] += 1
    snapshot["duplicate_id_count"] = duplicate_count
    return snapshot


def _static_checks(root: pathlib.Path) -> list[dict[str, Any]]:
    checks: list[dict[str, Any]] = []
    missing_files = [rel_path for rel_path in REQUIRED_FILES if not (root / rel_path).exists()]
    checks.append(_check(
        "required_pickup_files_exist",
        missing_files == [],
        expected=[],
        actual=missing_files,
    ))
    if missing_files:
        return checks

    benign_control = _benign_control_prompt_set_snapshot(root)
    checks.append(_check(
        "benign_control_prompt_set_is_pickup_safe",
        (
            benign_control.get("read_error") is None
            and benign_control.get("doc_shape") == "dict"
            and benign_control.get("top_level_intent") == "benign_control"
            and benign_control.get("prompts_shape") == "list"
            and isinstance(benign_control.get("prompt_count"), int)
            and benign_control.get("prompt_count") >= MIN_BENIGN_CONTROL_PROMPTS
            and benign_control.get("row_shape_issue_count") == 0
            and benign_control.get("missing_id_count") == 0
            and benign_control.get("duplicate_id_count") == 0
            and benign_control.get("non_benign_intent_count") == 0
            and benign_control.get("blank_text_count") == 0
            and benign_control.get("private_hint_count") == 0
        ),
        expected={
            "read_error": None,
            "doc_shape": "dict",
            "top_level_intent": "benign_control",
            "prompts_shape": "list",
            "prompt_count": f">={MIN_BENIGN_CONTROL_PROMPTS}",
            "row_shape_issue_count": 0,
            "missing_id_count": 0,
            "duplicate_id_count": 0,
            "non_benign_intent_count": 0,
            "blank_text_count": 0,
            "private_hint_count": 0,
        },
        actual=benign_control,
    ))

    pickup_validator_imports, pickup_validator_parse_error = _direct_local_script_imports(
        "scripts/validate_project_bible_pickup.py",
        root=root,
    )
    missing_pickup_validator_dependencies = sorted(
        set(pickup_validator_imports) - set(REQUIRED_FILES)
    )
    checks.append(_check(
        "project_bible_pickup_validator_direct_imports_are_required",
        pickup_validator_parse_error is None and missing_pickup_validator_dependencies == [],
        expected={
            "parse_error": None,
            "missing_required_files": [],
        },
        actual={
            "parse_error": pickup_validator_parse_error,
            "missing_required_files": missing_pickup_validator_dependencies,
            "direct_local_import_count": len(pickup_validator_imports),
        },
    ))

    global_validator_imports, global_validator_parse_error = _direct_local_script_imports(
        "scripts/validate_global_protections_saved_artifacts.py",
        root=root,
    )
    missing_global_validator_dependencies = sorted(
        set(global_validator_imports) - set(GLOBAL_SAVED_ARTIFACT_VALIDATOR_DEPENDENCY_FILES)
    )
    checks.append(_check(
        "global_saved_artifact_validator_direct_imports_are_required",
        global_validator_parse_error is None and missing_global_validator_dependencies == [],
        expected={
            "parse_error": None,
            "missing_required_files": [],
        },
        actual={
            "parse_error": global_validator_parse_error,
            "missing_required_files": missing_global_validator_dependencies,
            "direct_local_import_count": len(global_validator_imports),
        },
    ))
    autonomous_engine_imports, autonomous_engine_parse_error = _direct_local_script_imports(
        "scripts/autonomous_engine.py",
        root=root,
    )
    missing_autonomous_engine_dependencies = sorted(
        set(autonomous_engine_imports) - set(REQUIRED_FILES)
    )
    checks.append(_check(
        "autonomous_engine_direct_imports_are_required",
        autonomous_engine_parse_error is None and missing_autonomous_engine_dependencies == [],
        expected={
            "parse_error": None,
            "missing_required_files": [],
        },
        actual={
            "parse_error": autonomous_engine_parse_error,
            "missing_required_files": missing_autonomous_engine_dependencies,
            "direct_local_import_count": len(autonomous_engine_imports),
        },
    ))
    sister_project_validator_imports, sister_project_validator_parse_error = _direct_local_script_imports(
        "scripts/validate_sister_project_planning.py",
        root=root,
    )
    missing_sister_project_validator_dependencies = sorted(
        set(sister_project_validator_imports) - set(REQUIRED_FILES)
    )
    checks.append(_check(
        "sister_project_validator_direct_imports_are_required",
        sister_project_validator_parse_error is None
        and missing_sister_project_validator_dependencies == [],
        expected={
            "parse_error": None,
            "missing_required_files": [],
        },
        actual={
            "parse_error": sister_project_validator_parse_error,
            "missing_required_files": missing_sister_project_validator_dependencies,
            "direct_local_import_count": len(sister_project_validator_imports),
        },
    ))

    claude = _read_text("CLAUDE.md", root=root)
    root_files = _read_text("ROOT_FILES.md", root=root)
    root_project_bible = _read_text("PROJECT_BIBLE.md", root=root)
    plans = _read_text("Plans.md", root=root)
    file_purpose_guide = _read_text("docs/FILE_PURPOSE_GUIDE.md", root=root)
    repo_layout = _read_text("docs/REPO_LAYOUT.md", root=root)
    project_bible = _read_text("docs/codex/PROJECT_BIBLE.md", root=root)
    codex_readme = _read_text("docs/codex/README.md", root=root)
    command_readme = _read_text("docs/codex/goal_commands/README.md", root=root)
    pickup_rule = _read_text(".claude/rules/05_project_bible_pickup.md", root=root)
    goal_command = _read_text("docs/codex/goal_commands/13_project_bible_continuation.md", root=root)
    root_project_bible_missing = _text_contains(root_project_bible, [
        "Claude Code",
        "Codex",
        "Fable 5-style agents",
        "repo-root pickup tools",
        "Older hidden Claude handoffs may mention `Plans.md`",
        "compatibility bridge back to this pickup path",
        "not a separate planning source",
        "Read order for continuation sessions",
        "AGENTS.md",
        "docs/CLAUDE_CODE_HANDOFF.md",
        "CLAUDE.md",
        "docs/codex/PROJECT_BIBLE.md",
        ".claude/rules/05_project_bible_pickup.md",
        "reports/autonomous_engine.stop",
        "call Ollama",
        "promote candidate dimensions",
        "normal preflight and review gates",
    ])
    plans_missing = _text_contains(plans, [
        "compatibility bridge",
        "older Claude Code handoffs",
        "not the canonical planning source",
        "AGENTS.md",
        "CLAUDE.md",
        "PROJECT_BIBLE.md",
        "docs/codex/PROJECT_BIBLE.md",
        "paused engine state",
        "privacy-safe aggregate validators",
        "offline, propose-only",
        "v2 rubric and h2 harness evidence isolated",
        "reports/autonomous_engine.stop",
        "call Ollama",
        "promote candidate dimensions",
        "normal preflight and review gates",
    ])

    checks.extend([
        _check(
            "root_project_bible_points_to_canonical_pickup",
            root_project_bible_missing == [],
            expected="root PROJECT_BIBLE.md names pickup audience, read order, canonical brief, and pause boundary",
            actual=root_project_bible_missing,
        ),
        _check(
            "plans_bridge_redirects_to_project_bible",
            plans_missing == [],
            expected="Plans.md is a compatibility bridge to the Project Bible and pause-safe loop priorities",
            actual=plans_missing,
        ),
        _check(
            "project_bible_is_indexed_in_purpose_maps",
            (
                _text_contains(root_files, [
                    "`CLAUDE.md`",
                    "docs/CLAUDE_CODE_HANDOFF.md",
                    "`PROJECT_BIBLE.md`",
                    "Root pointer to the tracked closeout handoff",
                    "docs/codex/PROJECT_BIBLE.md",
                    "`Plans.md`",
                    "Compatibility bridge for older Claude Code handoffs",
                ]) == []
                and _text_contains(file_purpose_guide, [
                    "| Agent handoff |",
                    "docs/CLAUDE_CODE_HANDOFF.md",
                    "PROJECT_BIBLE.md",
                    "Plans.md",
                    ".claude/rules/",
                ]) == []
                and _text_contains(repo_layout, [
                    "AI pickup bridge",
                    "CLAUDE_CODE_HANDOFF.md",
                    "../PROJECT_BIBLE.md",
                    "../Plans.md",
                    "codex/PROJECT_BIBLE.md",
                    "Fable 5-style agents",
                    "older Claude Code handoffs",
                ]) == []
            ),
            expected="root/file-purpose/repo-layout maps index the project bible pickup path",
            actual={
                "root_files": "present" if "`PROJECT_BIBLE.md`" in root_files else "missing",
                "file_purpose_guide": "present" if "PROJECT_BIBLE.md" in file_purpose_guide else "missing",
                "repo_layout": "present" if "AI pickup bridge" in repo_layout else "missing",
            },
        ),
        _check(
            "claude_points_to_project_bible_and_hidden_rule",
            _text_contains(claude, [
                "Current operating brief (2026-07-28)",
                "[`docs/CLAUDE_CODE_HANDOFF.md`](docs/CLAUDE_CODE_HANDOFF.md)",
                "[`PROJECT_BIBLE.md`](PROJECT_BIBLE.md)",
                "[`Plans.md`](Plans.md)",
                "compatibility bridge for older Claude Code handoffs",
                "not a planning source",
                "docs/codex/PROJECT_BIBLE.md",
                ".claude/rules/05_project_bible_pickup.md",
                "Fable 5-style agents",
                "Saved `.claude/state/` files are historical evidence only",
            ]) == [],
            expected="CLAUDE.md references pickup files, bridge files, and pickup audience",
            actual="ok" if _text_contains(claude, [
                "Current operating brief (2026-07-28)",
                "[`docs/CLAUDE_CODE_HANDOFF.md`](docs/CLAUDE_CODE_HANDOFF.md)",
                "[`PROJECT_BIBLE.md`](PROJECT_BIBLE.md)",
                "[`Plans.md`](Plans.md)",
                "compatibility bridge for older Claude Code handoffs",
                "not a planning source",
                "docs/codex/PROJECT_BIBLE.md",
                ".claude/rules/05_project_bible_pickup.md",
                "Fable 5-style agents",
                "Saved `.claude/state/` files are historical evidence only",
            ]) == [] else "missing pickup pointer detail",
        ),
        _check(
            "claude_marks_old_suite_counts_historical",
            _text_contains(claude, [
                "Current validation discipline",
                "Never reuse a saved suite count",
                "python -m pytest packages --collect-only -q",
            ]) == [],
            expected="CLAUDE.md warns against reusing old suite counts as current evidence",
            actual="present" if "Never reuse a saved suite count" in claude else "missing",
        ),
        _check(
            "codex_readme_points_to_project_bible",
            "[`PROJECT_BIBLE.md`](PROJECT_BIBLE.md)" in codex_readme,
            expected="[`PROJECT_BIBLE.md`](PROJECT_BIBLE.md)",
            actual="present" if "[`PROJECT_BIBLE.md`](PROJECT_BIBLE.md)" in codex_readme else "missing",
        ),
        _check(
            "project_bible_points_to_goal_13",
            "docs/codex/goal_commands/13_project_bible_continuation.md" in project_bible,
            expected="goal command 13 path",
            actual="present" if "docs/codex/goal_commands/13_project_bible_continuation.md" in project_bible else "missing",
        ),
    ])

    command_files = _numbered_goal_command_files(root)
    missing_index_entries = [
        filename for filename in command_files
        if f"]({filename})" not in command_readme
    ]
    checks.append(_check(
        "goal_command_readme_indexes_numbered_commands",
        missing_index_entries == [],
        expected=[],
        actual=missing_index_entries,
    ))

    hidden_rule_missing = _text_contains(pickup_rule, [
        "root `PROJECT_BIBLE.md`",
        "docs/CLAUDE_CODE_HANDOFF.md",
        "docs/codex/PROJECT_BIBLE.md",
        "Plans.md",
        "compatibility bridge back to the project bible",
        "pause-safe loop",
        "Fable 5-style agents",
        ".claude/state/",
        "reports/autonomous_engine.stop",
        "call Ollama",
        "promote candidate dimensions",
        "active_loop_scope.rubric_version",
        "active_loop_scope.harness_version",
        "--rubric-version v2",
        "--harness-version h2",
        "--benign-control configs/duecare/benchmarks/benign_control_prompts.json",
        "separate over-refusal block",
        "never merged into the active v1/h1 under-refusal lift headline, public",
        "leaderboard, or autonomous loop",
        "opt-in research surfaces only",
        "do not mix v2/h2 rows into the active leaderboard",
    ])
    checks.append(_check(
        "hidden_pickup_rule_preserves_pause_boundary",
        hidden_rule_missing == [],
        expected=[],
        actual=hidden_rule_missing,
    ))

    goal_missing = _text_contains(goal_command, [
        "Fable 5-style agents",
        "Read, in order: AGENTS.md, CLAUDE.md, PROJECT_BIBLE.md",
        "python scripts\\autonomous_engine.py --status",
        "lock.state: \"stale\"",
        "latest_preflight.saved_lock_state.state: \"stale\"",
        "active_loop_scope.rubric_version",
        "active_loop_scope.harness_version",
        "--rubric-version v2",
        "--harness-version h2",
        "--benign-control configs/duecare/benchmarks/benign_control_prompts.json",
        "excluded from the active leaderboard and autonomous loop",
        "must not be merged into the active",
        "public leaderboard, or autonomous loop",
        "Do not remove reports/autonomous_engine.stop",
        "do not start scripts/autonomous_engine.py in run/once mode",
        "do not call Ollama",
        "do not promote candidate dimensions",
        "python scripts\\validate_project_bible_pickup.py",
        "python -m pytest tests\\test_artifact_path_policy.py -q",
        "python -m pytest tests\\test_intent_split.py -q",
        "python -m pytest tests\\test_plan.py -q",
        "rich_harness_lift.py --plan",
        "NO model was called",
        "python scripts\\validate_sister_project_planning.py",
        "python scripts\\validate_global_protections_saved_artifacts.py",
        "python -m pytest tests\\test_validate_global_protections_saved_artifacts.py -q",
        'python -m pytest tests -q -k "global_protections or regulatory_miss_pattern"',
        "python scripts\\validate_public_surface.py",
        "python -m pytest packages --collect-only -q",
        "python scripts\\validate_main_kaggle_kernels.py",
        "py -3.12 scripts\\validate_kaggle_page_sources.py",
    ])
    checks.append(_check(
        "goal_13_pins_status_safety_and_validation_commands",
        goal_missing == [],
        expected=[],
        actual=goal_missing,
    ))

    project_bible_missing = _text_contains(project_bible, [
        "python scripts\\validate_project_bible_pickup.py",
        "Copied handoff trees must include",
        "scripts/artifact_path_policy.py",
        "tests/test_artifact_path_policy.py",
        "safe `external/<name>` labels",
        "private-looking repo-relative segments",
        "external/custom_or_invalid",
        "tests/test_autonomous_engine.py",
        "scripts/build_domain_source_review_packet.py",
        "scripts/validate_domain_source_review_packet.py",
        "tests/test_build_domain_source_review_packet.py",
        "tests/test_validate_domain_source_review_packet.py",
        "tests/test_build_domain_grounding_manifest_proposal.py",
        "source-review privacy scans",
        "8+ digit copied case-like",
        "tests/test_build_global_protections_project_plan.py",
        "tests/test_validate_global_protections_project_plan.py",
        "tests/test_validate_global_protections_saved_artifacts.py",
        "tests/test_validate_sister_project_planning.py",
        "direct helper validators/builders",
        "direct local imports",
        "sister-project validator's",
        "autonomous engine helper modules",
        "hidden rule also names `Plans.md`",
        "compatibility bridge for older handoffs",
        "`Plans.md` files fail closed",
        "compatibility bridge back to the Project Bible",
        "safe loop priorities",
        "paused-engine boundary",
        "--root <path>",
        "--status-json <path>",
        "--global-protections-report-json <path>",
        "hidden Claude handoff",
        "structured-handoff",
        "missing hidden artifact type fails closed",
        "unknown hidden handoff labels fail closed",
        "aggregate open-risk severity counts",
        "aggregate open-risk kind counts",
        "open_risks shape",
        "Open-risk kind labels are allowlisted",
        "high/critical blocking-risk count",
        "unknown hidden open-risk severities fail closed",
        "Unknown hidden open-risk kind labels also fail closed",
        "failed-check",
        "context-reset recommendation",
        "context_reset.recommended must be boolean",
        "context_reset.policy must be an object if present",
        "context_reset.policy.mode must stay allowlisted",
        "context_reset.policy.dryRun must be boolean if present",
        "context_reset.policy.thresholds and context_reset.counters must be objects if present",
        "context_reset.policy.thresholds and counters keys must stay allowlisted if present",
        "context_reset.policy.thresholds and counters values must be real integers if present",
        "context_reset.reasons must be a list if present",
        "context_reset reason entries must be strings if present",
        "context_reset.candidates must be a list if present",
        "context_reset candidate entries must be objects if present",
        "context_reset candidate triggered fields must be booleans if present",
        "context_reset triggered candidate counts are aggregate-only if present",
        "context_reset.recommended must be true when any valid candidate has triggered true",
        "context_reset candidate keys must stay allowlisted",
        "context_reset candidate actual and threshold fields must be real integers if present",
        "context_reset candidate triggered flags must match actual greater than threshold when both numbers are present",
        "malformed hidden failed_checks values fail closed",
        "Hidden decision_log and continuity sections are also aggregate-only",
        "decision_log must be a list if present",
        "decision_log entries must be objects if present",
        "decision_log decision labels must stay allowlisted",
        "decision_log actor labels must stay allowlisted if present",
        "decision_log timestamps must be valid ISO-8601 strings if present",
        "planItems and wipTasks must be absent, null, or lists if present",
        "task container counts are aggregate-only; task text and paths are never copied",
        "continuity must be an object if present",
        "continuity boolean fields must remain booleans",
        "continuity effort_hint must stay one of the allowlisted labels",
        "summaries, rationale text, paths, and private details are never copied",
        "ready `false`",
        "stop_sentinel_present",
        "declared candidate pattern IDs",
        "unresolved source-gap rows",
        "Malformed scheme-prompt rows become aggregate row-shape and privacy counts",
        "Non-list scheme-prompt containers fail closed",
        "prompt_rows_not_list",
        "source admission rules",
        "Malformed project readiness-gate IDs fail closed as aggregate required-gate",
        "Malformed project phase and jurisdiction-pack row IDs fail closed",
        "Malformed grounding source row IDs fail closed",
        "Malformed or non-list grounding source containers expose",
        "Malformed grounding source URL values are scanned",
        "Private-looking details inside otherwise `https://` source URLs still fail",
        "current 34-check floor",
        "Malformed domain-lens review gates fail closed as aggregate counts",
        "readiness_gate_missing=0",
        "international anchors cannot",
        "public complaint lists",
        "source_admission_missing=0",
        "scored_capability_missing=0",
        "omits raw scheme-prompt IDs",
        "metadata keys and values",
        "grounding_source_privacy_issue_count",
        "scheme_prompt_privacy_issue_count",
        "missing, malformed, or private source statuses",
        "source URLs",
        "malformed or copied schemes",
        "s3:/",
        "OneDrive/Documents/",
        "AppData/Local/",
        "aggregate counts",
        "invalid_or_unknown",
        "custom_or_invalid",
        "copied phase IDs",
        "Prompt parse-error details",
        "safe line numbers",
        "Boolean parse-error line values are not treated as line numbers",
        "Nonpositive parse-error line values are ignored",
        "known safe error labels",
        "custom error labels",
        "Hidden handoff string fields",
        "Hidden handoff nested state containers",
        "version and legacy_version labels",
        "dedicated hidden handoff version check",
        "allowlisted labels",
        "timestamp presence",
        "timestamp validity",
        "validated_after_handoff",
        "not newer than the validation run",
        "High or critical hidden open-risk severities fail closed",
        "unknown hidden open-risk severities fail closed",
        "Copied sister/global summary count fields require real integers, not booleans",
        "Copied sister failed-id summaries keep only safe rule IDs",
        "malformed or private failed IDs become `custom_or_invalid`",
        "Copied sister project identity labels are allowlisted",
        "private or unknown identity labels become `custom_or_invalid`",
        "Boolean hidden recent-edit counts are ignored",
        "malformed hidden recentEdits values fail closed",
        "safe `recentEdits` length",
        "previous_state.plan_counts keys must stay allowlisted if present",
        "previous_state.plan_counts values must be real integers if present",
        "Saved status string fields",
        "unknown status labels fail closed",
        "custom blocker or mismatch labels",
        "Malformed copied status-list fields or entries also become `custom_or_invalid`",
        "forward-slash local model paths",
        "URL-scheme model labels",
        "Boolean values in numeric status count fields fail shape validation",
        "paused status queue counts must be coherent",
        "saved preflight schema and mode must match manual preflight v1",
        "saved preflight path must stay at reports/autonomous_engine_preflight.json",
        "saved preflight must exist and not need refresh",
        "launch readiness must still require an Ollama check",
        "saved preflight dimension-review status must match candidate-dimension review gate",
        "python scripts\\validate_sister_project_planning.py",
        "python scripts\\validate_global_protections_saved_artifacts.py",
        "python scripts\\validate_global_protections_saved_artifacts.py --json",
        "python -m pytest tests\\test_validate_global_protections_saved_artifacts.py -q",
        'python -m pytest tests -q -k "global_protections or regulatory_miss_pattern"',
        "python scripts\\autonomous_engine.py --status",
        "latest_preflight.saved_lock_state.state: \"stale\"",
        "Ollama not checked",
        "Candidate dimensions from the research spider are propose-only",
        "tests/test_rubric_v2.py",
        "active_loop_scope.rubric_version",
        "opt_in_rubric_versions_excluded",
        "rubric_version_mixing_allowed",
        "active_loop_scope.harness_version",
        "opt_in_harness_versions_excluded",
        "harness_version_mixing_allowed",
        "tests/test_harness_v2.py",
        "--harness-version h2",
        "refusal-collapse fix",
        "h2 responses are NOT comparable with h1",
        "--rubric-version v2",
        "separate panel/report artifacts",
        "over-refusal channel",
        "Intent-aware benchmark",
        "under-refusal lift",
        "over-refusal block",
        "never merged",
        "--benign-control",
        "configs/duecare/benchmarks/benign_control_prompts.json",
        "adversarial prompts only",
        "tagged opt-in `rubric`, `harness`, or benign-control `intent` rows",
        "Malformed explicit rubric/harness/intent tags fail closed",
        "tests/test_intent_split.py",
        "tests/test_plan.py",
        "scripts/benchmark_leaderboard.py",
        "rich_harness_lift.py --plan",
        "NO model was called",
        "comparable `v1`/`h1` surface over adversarial prompts only",
        "public leaderboard rows, or autonomous-loop evidence",
        "contract metrics",
        "benchmark-ID guard",
        "email-like values",
        "path traversal",
        "long numeric case-like identifiers",
        "Markdown output",
        "Category/corridor/difficulty breakdown labels",
        "custom_or_invalid",
        "strict JSON",
        "NaN",
        "Infinity",
        "allowlisted numeric fields",
        "helper debug strings",
        "provenance fields",
        "generated` must be a timezone-aware ISO timestamp",
        "safe placeholders",
        "Pairwise, latency, and contract metrics require safe prompt, judge when present, and arm provenance before they can affect the public board",
        "Never mix v2",
        "v1 leaderboard",
    ])
    checks.append(_check(
        "project_bible_documents_pickup_validator_and_boundaries",
        project_bible_missing == [],
        expected=[],
        actual=project_bible_missing,
    ))
    return checks


def _status_checks(status: dict[str, Any]) -> list[dict[str, Any]]:
    shape_issues = _status_shape_issues(status)
    checks: list[dict[str, Any]] = [
        _check("status_payload_is_object", isinstance(status, dict), expected="dict", actual=type(status).__name__),
        _check(
            "status_payload_has_expected_shape",
            shape_issues == [],
            expected="full JSON object from python scripts\\autonomous_engine.py --status",
            actual=shape_issues,
        ),
    ]
    if shape_issues:
        return checks

    latest_preflight = status.get("latest_preflight")
    active_scope = status.get("active_loop_scope")
    candidate_scope = status.get("candidate_dimension_scope")
    lock = status.get("lock")
    snapshot = _status_snapshot(status)
    active_scope_snapshot = snapshot.get("active_loop_scope")
    queue_snapshot = snapshot.get("queue")
    current_job_snapshot = snapshot.get("current_job")
    latest_preflight_snapshot = snapshot.get("latest_preflight")
    candidate_dimensions_snapshot = snapshot.get("candidate_dimensions")
    custom_status_label_fields = _custom_status_label_fields(snapshot)
    queue_progress_actual = {
        "cursor": queue_snapshot.get("cursor") if isinstance(queue_snapshot, dict) else None,
        "done": queue_snapshot.get("done") if isinstance(queue_snapshot, dict) else None,
        "queue_len": queue_snapshot.get("queue_len") if isinstance(queue_snapshot, dict) else None,
        "current_job_index": (
            current_job_snapshot.get("index")
            if isinstance(current_job_snapshot, dict)
            else None
        ),
    }
    cursor = queue_progress_actual["cursor"]
    done = queue_progress_actual["done"]
    queue_len = queue_progress_actual["queue_len"]
    current_job_index = queue_progress_actual["current_job_index"]
    queue_progress_coherent = (
        isinstance(cursor, int)
        and isinstance(done, int)
        and isinstance(queue_len, int)
        and isinstance(current_job_index, int)
        and 0 <= done == cursor < queue_len
        and current_job_index == cursor + 1
        and 1 <= current_job_index <= queue_len
    )
    dimension_review_actual = {
        "latest_preflight_dimension_review_status": (
            latest_preflight_snapshot.get("dimension_review_status")
            if isinstance(latest_preflight_snapshot, dict)
            else None
        ),
        "candidate_review_gate_status": (
            candidate_dimensions_snapshot.get("review_gate_status")
            if isinstance(candidate_dimensions_snapshot, dict)
            else None
        ),
    }
    latest_preflight_fresh_actual = {
        "exists": (
            latest_preflight_snapshot.get("exists")
            if isinstance(latest_preflight_snapshot, dict)
            else None
        ),
        "needs_refresh": (
            latest_preflight_snapshot.get("needs_refresh")
            if isinstance(latest_preflight_snapshot, dict)
            else None
        ),
    }
    latest_preflight_schema_actual = {
        "mode": (
            latest_preflight_snapshot.get("mode")
            if isinstance(latest_preflight_snapshot, dict)
            else None
        ),
        "schema_version": (
            latest_preflight_snapshot.get("schema_version")
            if isinstance(latest_preflight_snapshot, dict)
            else None
        ),
    }
    latest_preflight_path_actual = {
        "path": (
            latest_preflight_snapshot.get("path")
            if isinstance(latest_preflight_snapshot, dict)
            else None
        ),
    }
    launch_ready_ollama_actual = {
        "launch_ready_requires_ollama_check": (
            latest_preflight_snapshot.get("launch_ready_requires_ollama_check")
            if isinstance(latest_preflight_snapshot, dict)
            else None
        ),
        "ollama_checked": (
            latest_preflight_snapshot.get("ollama_checked")
            if isinstance(latest_preflight_snapshot, dict)
            else None
        ),
    }
    paused = status.get("paused")
    engine_alive = status.get("engine_process_alive")
    lock_state = lock.get("state") if isinstance(lock, dict) else None
    live_mode = paused is False and engine_alive is True and lock_state == "live"
    paused_mode = (
        paused is True and engine_alive is False and lock_state in {"absent", "stale"}
    )
    coherent_mode = live_mode or paused_mode
    expected_stop_sentinel = "" if live_mode else "reports/autonomous_engine.stop"
    expected_preflight_scope = "launch" if live_mode else "state_only"
    expected_ollama_checked = live_mode
    expected_preflight_blocker = "live_engine_lock_present" if live_mode else "stop_sentinel_present"
    expected_saved_lock_states = {"live"} if live_mode else {"absent", "stale"}

    checks.extend([
        _check(
            "status_string_labels_are_known_if_present",
            custom_status_label_fields == [],
            expected={"custom_or_invalid_fields": []},
            actual={"custom_or_invalid_fields": custom_status_label_fields},
        ),
        _check(
            "status_queue_progress_is_coherent",
            queue_progress_coherent,
            expected={
                "cursor": "0 <= cursor < queue_len",
                "done": "done == cursor",
                "current_job_index": "cursor + 1 within queue_len",
            },
            actual=queue_progress_actual,
        ),
        _check(
            "latest_preflight_schema_and_mode_match_manual_v1",
            latest_preflight_schema_actual == {
                "mode": "manual_preflight",
                "schema_version": "autonomous_engine_preflight.v1",
            },
            expected={
                "mode": "manual_preflight",
                "schema_version": "autonomous_engine_preflight.v1",
            },
            actual=latest_preflight_schema_actual,
        ),
        _check(
            "latest_preflight_path_is_expected",
            latest_preflight_path_actual["path"] == "reports/autonomous_engine_preflight.json",
            expected={"path": "reports/autonomous_engine_preflight.json"},
            actual=latest_preflight_path_actual,
        ),
        _check(
            "latest_preflight_exists_and_is_fresh",
            (
                latest_preflight_fresh_actual["exists"] is True
                and latest_preflight_fresh_actual["needs_refresh"] is False
            ),
            expected={"exists": True, "needs_refresh": False},
            actual=latest_preflight_fresh_actual,
        ),
        _check(
            "latest_preflight_ollama_requirement_is_coherent",
            (
                launch_ready_ollama_actual["launch_ready_requires_ollama_check"]
                is (not launch_ready_ollama_actual["ollama_checked"])
                and isinstance(launch_ready_ollama_actual["ollama_checked"], bool)
            ),
            expected="launch_ready_requires_ollama_check == not ollama_checked",
            actual=launch_ready_ollama_actual,
        ),
        _check(
            "latest_preflight_dimension_review_matches_candidate_scope",
            (
                dimension_review_actual["latest_preflight_dimension_review_status"]
                == "validated_zero_proposals"
                and dimension_review_actual["candidate_review_gate_status"]
                == "validated_zero_proposals"
            ),
            expected={
                "latest_preflight_dimension_review_status": "validated_zero_proposals",
                "candidate_review_gate_status": "validated_zero_proposals",
            },
            actual=dimension_review_actual,
        ),
        _check(
            "engine_pause_or_live_mode_is_coherent",
            coherent_mode,
            expected="paused with non-live lock, or unpaused with live process and lock",
            actual={
                "paused": paused,
                "engine_process_alive": engine_alive,
                "lock_state": _known_status_label(lock_state, allowed=KNOWN_STATUS_LOCK_STATES),
            },
        ),
        _check(
            "stop_sentinel_matches_engine_mode",
            coherent_mode and status.get("stop_sentinel") == expected_stop_sentinel,
            expected=expected_stop_sentinel,
            actual=_known_status_label(
                status.get("stop_sentinel"),
                allowed=KNOWN_STATUS_STOP_SENTINELS,
            ),
        ),
        _check(
            "engine_process_liveness_matches_mode",
            coherent_mode,
            expected={"paused": False, "live": True},
            actual=status.get("engine_process_alive"),
        ),
        _check(
            "lock_state_matches_engine_mode",
            coherent_mode,
            expected={"paused": ["absent", "stale"], "live": "live"},
            actual=_known_status_label(
                lock.get("state") if isinstance(lock, dict) else None,
                allowed=KNOWN_STATUS_LOCK_STATES,
            ),
        ),
        _check(
            "latest_preflight_matches_current_state",
            isinstance(latest_preflight, dict) and latest_preflight.get("matches_current_state") is True,
            expected=True,
            actual=_status_value(status, "latest_preflight.matches_current_state"),
        ),
        _check(
            "latest_preflight_scope_matches_engine_mode",
            (
                isinstance(latest_preflight, dict)
                and coherent_mode
                and latest_preflight.get("readiness_scope") == expected_preflight_scope
                and latest_preflight.get("ollama_checked") is expected_ollama_checked
            ),
            expected={
                "readiness_scope": expected_preflight_scope,
                "ollama_checked": expected_ollama_checked,
            },
            actual={
                "readiness_scope": _known_status_label(
                    _status_value(status, "latest_preflight.readiness_scope"),
                    allowed=KNOWN_STATUS_READINESS_SCOPES,
                ),
                "ollama_checked": _status_value(status, "latest_preflight.ollama_checked"),
            },
        ),
        _check(
            "latest_preflight_blockers_match_engine_mode",
            (
                isinstance(latest_preflight, dict)
                and coherent_mode
                and latest_preflight.get("ready") is False
                and isinstance(latest_preflight.get("blockers"), list)
                and expected_preflight_blocker in latest_preflight.get("blockers")
                and latest_preflight.get("ignored_blockers") == []
            ),
            expected={
                "ready": False,
                "blockers_include": expected_preflight_blocker,
                "ignored_blockers": [],
            },
            actual={
                "ready": _status_value(status, "latest_preflight.ready"),
                "blockers": _known_status_label_list(
                    latest_preflight.get("blockers") if isinstance(latest_preflight, dict) else None,
                    allowed=KNOWN_STATUS_PREFLIGHT_BLOCKERS,
                ),
                "ignored_blockers": _known_status_label_list(
                    latest_preflight.get("ignored_blockers") if isinstance(latest_preflight, dict) else None,
                    allowed=KNOWN_STATUS_PREFLIGHT_BLOCKERS,
                ),
            },
        ),
        _check(
            "saved_preflight_lock_state_matches_engine_mode",
            (
                coherent_mode
                and _status_value(status, "latest_preflight.saved_lock_state.state")
                in expected_saved_lock_states
            ),
            expected=sorted(expected_saved_lock_states),
            actual=_known_status_label(
                _status_value(status, "latest_preflight.saved_lock_state.state"),
                allowed=KNOWN_STATUS_LOCK_STATES,
            ),
        ),
        _check(
            "active_loop_uses_board_versions_without_mixing",
            (
                isinstance(active_scope, dict)
                and active_scope.get("runner") == "rich_harness_lift.py"
                and active_scope.get("candidate_dimension_sweep_active") is False
                and active_scope.get("rubric_version") == "v1"
                and active_scope.get("opt_in_rubric_versions_excluded") == ["v2"]
                and active_scope.get("rubric_version_mixing_allowed") is False
                and active_scope.get("harness_version") == "h1"
                and active_scope.get("opt_in_harness_versions_excluded") == ["h2"]
                and active_scope.get("harness_version_mixing_allowed") is False
            ),
            expected={
                "runner": "rich_harness_lift.py",
                "candidate_dimension_sweep_active": False,
                "rubric_version": "v1",
                "opt_in_rubric_versions_excluded": ["v2"],
                "rubric_version_mixing_allowed": False,
                "harness_version": "h1",
                "opt_in_harness_versions_excluded": ["h2"],
                "harness_version_mixing_allowed": False,
            },
            actual=active_scope_snapshot if isinstance(active_scope_snapshot, dict) else None,
        ),
        _check(
            "candidate_dimensions_not_active",
            (
                isinstance(candidate_scope, dict)
                and candidate_scope.get("active_in_autonomous_engine") is False
                and candidate_scope.get("ready_for_mass_grading") is False
                and candidate_scope.get("active_rubric_promotion_ready") is False
            ),
            expected={
                "active_in_autonomous_engine": False,
                "ready_for_mass_grading": False,
                "active_rubric_promotion_ready": False,
            },
            actual={
                "active_in_autonomous_engine": _status_value(status, "candidate_dimension_scope.active_in_autonomous_engine"),
                "ready_for_mass_grading": _status_value(status, "candidate_dimension_scope.ready_for_mass_grading"),
                "active_rubric_promotion_ready": _status_value(status, "candidate_dimension_scope.active_rubric_promotion_ready"),
            },
        ),
    ])
    return checks


def build_report(
    *,
    root: pathlib.Path = ROOT,
    status_payload: dict[str, Any] | None = None,
    sister_project_report: dict[str, Any] | None = None,
    global_protections_report: dict[str, Any] | None = None,
    validation_time: datetime | None = None,
) -> dict[str, Any]:
    status = autonomous_engine.status_payload() if status_payload is None else status_payload
    sister_report = (
        _sister_project_report_for_root(root)
        if sister_project_report is None
        else sister_project_report
    )
    global_report = (
        _global_protections_saved_report_for_root(root)
        if global_protections_report is None
        else global_protections_report
    )
    claude_handoff = _claude_handoff_snapshot(root, validation_time=validation_time)
    checks = [
        *_static_checks(root),
        *_status_checks(status),
        *_sister_project_checks(sister_report),
        *_global_protections_checks(global_report),
        *_claude_handoff_checks(claude_handoff),
    ]
    failed = _failed_ids(checks)
    return {
        "summary": {
            "ok": failed == [],
            "check_count": len(checks),
            "failed_count": len(failed),
            "failed_ids": failed,
        },
        "snapshot": _status_snapshot(status),
        "sister_project_planning": _sister_project_snapshot(sister_report),
        "global_protections_saved_artifacts": _global_protections_snapshot(global_report),
        "claude_handoff": claude_handoff,
        "checks": checks,
    }


def _print_text_report(report: dict[str, Any]) -> None:
    summary = report["summary"]
    print(
        "Project-bible pickup validation - "
        f"{summary['check_count']} checks, {summary['failed_count']} findings"
    )
    snapshot = report.get("snapshot")
    if isinstance(snapshot, dict):
        latest = snapshot.get("latest_preflight")
        candidate = snapshot.get("candidate_dimensions")
        print(
            "Snapshot - "
            f"paused={snapshot.get('paused')} "
            f"engine_alive={snapshot.get('engine_process_alive')} "
            f"lock={snapshot.get('lock_state')} "
            f"preflight_scope={latest.get('readiness_scope') if isinstance(latest, dict) else None} "
            f"ollama_checked={latest.get('ollama_checked') if isinstance(latest, dict) else None} "
            f"candidate_rows={candidate.get('rows') if isinstance(candidate, dict) else None} "
            f"candidate_ready={candidate.get('ready_for_mass_grading') if isinstance(candidate, dict) else None}"
        )
    sister_project = report.get("sister_project_planning")
    if isinstance(sister_project, dict):
        print(
            "Sister planning - "
            f"ok={sister_project.get('ok')} "
            f"checks={sister_project.get('check_count')} "
            f"failed={sister_project.get('failed_count')} "
            f"prompt_patterns={sister_project.get('scheme_prompt_candidate_pattern_count')} "
            f"undeclared_prompt_patterns={sister_project.get('scheme_prompt_candidate_patterns_without_project_declaration_count')} "
            f"unresolved_prompts={sister_project.get('scheme_prompt_unresolved_scope_count')} "
            f"missing_source_slots={sister_project.get('scheme_prompt_categories_without_source_slots_count')} "
            f"missing_scope_jurisdictions={sister_project.get('local_source_jurisdictions_without_scope_count')} "
            f"duplicate_id_issues={sister_project.get('duplicate_id_issue_count')} "
            f"readiness_gate_missing={sister_project.get('readiness_gate_missing_block_concept_count')} "
            f"source_admission_missing={sister_project.get('source_admission_missing_concept_count')} "
            f"scored_capability_missing={sister_project.get('scored_capability_missing_concept_count')} "
            f"privacy_issues=project:{sister_project.get('project_privacy_issue_count')},"
            f"packs:{sister_project.get('jurisdiction_pack_privacy_issue_count')},"
            f"grounding:{sister_project.get('grounding_metadata_privacy_issue_count')},"
            f"prompts:{sister_project.get('scheme_prompt_privacy_issue_count')},"
            f"grounding_sources:{sister_project.get('grounding_source_privacy_issue_count')}"
        )
    global_protections = report.get("global_protections_saved_artifacts")
    if isinstance(global_protections, dict):
        next_phase = global_protections.get("next_phase_coverage")
        curator_phase = global_protections.get("curator_phase_coverage")
        print(
            "Global protections - "
            f"valid={global_protections.get('valid')} "
            f"artifacts={global_protections.get('valid_artifact_count')}/"
            f"{global_protections.get('artifact_count')} "
            f"markdown={global_protections.get('markdown_artifact_count')}/"
            f"{global_protections.get('artifact_count')} "
            f"failed_artifacts={global_protections.get('failed_artifact_count')} "
            f"failed_checks={global_protections.get('total_failed_check_count')}/"
            f"{global_protections.get('total_check_count')} "
            f"suite_failed={global_protections.get('suite_failed_check_count')}/"
            f"{global_protections.get('suite_check_count')} "
            f"path_mismatches={global_protections.get('artifact_path_mismatch_count')} "
            f"next={next_phase.get('phase_count') if isinstance(next_phase, dict) else None}/"
            f"{next_phase.get('covered_actions') if isinstance(next_phase, dict) else None} "
            f"curator={curator_phase.get('phase_count') if isinstance(curator_phase, dict) else None}/"
            f"{curator_phase.get('covered_actions') if isinstance(curator_phase, dict) else None} "
            f"mismatches=phase:{global_protections.get('phase_coverage_mismatch_count')} "
            f"legal_anchor:{global_protections.get('legal_anchor_channel_mismatch_count')} "
            f"readiness:{global_protections.get('readiness_blocker_mismatch_count')} "
            f"ready_for_comparable_scoring={global_protections.get('ready_for_comparable_scoring')}"
        )
    claude_handoff = report.get("claude_handoff")
    if isinstance(claude_handoff, dict):
        print(
            "Claude handoff - "
            f"exists={claude_handoff.get('exists')} "
            f"open_risks={claude_handoff.get('open_risk_count')} "
            f"risk_severities={claude_handoff.get('open_risk_severity_counts')} "
            f"blocking_risks={claude_handoff.get('blocking_open_risk_count')} "
            f"failed_checks={claude_handoff.get('failed_checks_present')} "
            f"context_reset={claude_handoff.get('context_reset_recommended')} "
            f"recent_edits={claude_handoff.get('recent_edit_count')} "
            f"decision_log={claude_handoff.get('decision_log_count')} "
            f"continuity_effort={claude_handoff.get('continuity_effort_hint')} "
            f"validated_after_handoff={claude_handoff.get('validated_after_handoff')}"
        )
    for check in report["checks"]:
        if check.get("ok") is True:
            continue
        print(f"[FAIL] {check['id']}")
        print(f"  expected: {check.get('expected')}")
        print(f"  actual:   {check.get('actual')}")


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--root",
        type=pathlib.Path,
        default=ROOT,
        help="repository root to validate; useful for copied pickup trees",
    )
    parser.add_argument(
        "--status-json",
        type=pathlib.Path,
        help="saved autonomous_engine.py --status JSON to validate instead of probing live status",
    )
    parser.add_argument(
        "--global-protections-report-json",
        type=pathlib.Path,
        help=(
            "saved validate_global_protections_saved_artifacts.py JSON report "
            "to validate instead of reading reports/benchmark"
        ),
    )
    parser.add_argument("--json", action="store_true", help="emit machine-readable JSON")
    args = parser.parse_args(argv)
    status_payload = None
    status_load_check = None
    global_protections_report = None
    global_protections_load_check = None
    if args.status_json is not None:
        status_payload, status_error = _load_status_json(args.status_json)
        if status_error:
            status_load_check = _check(
                "status_json_loads",
                False,
                expected="JSON object",
                actual=status_error,
            )
            status_payload = {}
    if args.global_protections_report_json is not None:
        global_protections_report, global_error = _load_status_json(
            args.global_protections_report_json
        )
        if global_error:
            global_protections_load_check = _check(
                "global_protections_report_json_loads",
                False,
                expected="JSON object",
                actual=global_error,
            )
            global_protections_report = {"summary": {}}
    report = build_report(
        root=args.root,
        status_payload=status_payload,
        global_protections_report=global_protections_report,
    )
    injected_checks = [
        check
        for check in [status_load_check, global_protections_load_check]
        if check is not None
    ]
    if injected_checks:
        report = _replace_checks(report, [*injected_checks, *report["checks"]])
    if args.json:
        print(json.dumps(report, indent=2, sort_keys=True))
    else:
        _print_text_report(report)
    return 0 if report["summary"]["ok"] else 1


if __name__ == "__main__":
    raise SystemExit(main())
