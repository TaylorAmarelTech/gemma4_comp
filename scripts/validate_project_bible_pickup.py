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
KNOWN_HANDOFF_SESSION_STATES = frozenset({"stopped", "running", "paused", "idle"})
KNOWN_HANDOFF_NEXT_ACTION_SOURCES = frozenset({"fallback", "manual", "user", "codex", "claude"})
KNOWN_HANDOFF_PRIORITIES = frozenset({"low", "normal", "medium", "high", "urgent"})
KNOWN_HANDOFF_RISK_SEVERITIES = frozenset({"low", "medium", "high", "critical"})
BLOCKING_HANDOFF_RISK_SEVERITIES = frozenset({"high", "critical"})
KNOWN_STATUS_JOB_SETS = frozenset({"curated", "full"})
KNOWN_STATUS_LOCK_STATES = frozenset({"absent", "stale", "live", "unknown"})
KNOWN_STATUS_READINESS_SCOPES = frozenset({"state_only", "launch"})
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
SAFE_MODEL_LABEL_RE = re.compile(r"^[A-Za-z0-9][A-Za-z0-9._:/+-]{0,80}$")
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
    *AUTONOMOUS_ENGINE_DEPENDENCY_FILES,
    "scripts/validate_global_protections_saved_artifacts.py",
    "scripts/validate_project_bible_pickup.py",
    "scripts/validate_sister_project_planning.py",
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
    if not isinstance(value, list):
        return []
    labels = [
        _known_status_label(item, allowed=allowed)
        for item in value
        if isinstance(item, str) and item
    ]
    return [label for label in labels if label is not None]


def _safe_model_label(value: Any) -> str | None:
    if not isinstance(value, str) or not value:
        return None
    if "\\" in value or "://" in value:
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

    previous_state = payload.get("previous_state") if isinstance(payload.get("previous_state"), dict) else {}
    plan_counts = previous_state.get("plan_counts") if isinstance(previous_state.get("plan_counts"), dict) else {}
    session_state = previous_state.get("session_state") if isinstance(previous_state.get("session_state"), dict) else {}
    next_action = payload.get("next_action") if isinstance(payload.get("next_action"), dict) else {}
    context_reset = payload.get("context_reset") if isinstance(payload.get("context_reset"), dict) else {}
    recent_edits = payload.get("recentEdits")
    recent_edit_count = plan_counts.get("recent_edits")
    if not isinstance(recent_edit_count, int) and isinstance(recent_edits, list):
        recent_edit_count = len(recent_edits)
    open_risks = payload.get("open_risks")
    if "open_risks" not in payload:
        open_risks_shape = "absent"
    elif isinstance(open_risks, list):
        open_risks_shape = "list"
    else:
        open_risks_shape = "custom_or_invalid"
    timestamp = _parse_handoff_timestamp(payload.get("timestamp"))
    if validation_time is None:
        validation_time = datetime.now(timezone.utc)
    if validation_time.tzinfo is None:
        validation_time = validation_time.replace(tzinfo=timezone.utc)
    validation_time = validation_time.astimezone(timezone.utc)
    open_risk_severity_counts = _severity_counts(open_risks)
    blocking_open_risk_count = sum(
        open_risk_severity_counts.get(severity, 0)
        for severity in BLOCKING_HANDOFF_RISK_SEVERITIES
    )

    return {
        "exists": True,
        "artifact_type": _known_handoff_label(
            payload.get("artifactType"),
            allowed=KNOWN_HANDOFF_ARTIFACT_TYPES,
        ),
        "timestamp_present": isinstance(payload.get("timestamp"), str) and bool(payload.get("timestamp")),
        "timestamp_valid": timestamp is not None,
        "validated_after_handoff": validation_time >= timestamp if timestamp is not None else None,
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
        "open_risks_shape": open_risks_shape,
        "open_risk_severity_counts": open_risk_severity_counts,
        "blocking_open_risk_count": blocking_open_risk_count,
        "failed_checks_present": payload.get("failed_checks") not in (None, [], {}),
        "context_reset_recommended": (
            context_reset.get("recommended")
            if isinstance(context_reset.get("recommended"), bool)
            else None
        ),
        "recent_edit_count": recent_edit_count if isinstance(recent_edit_count, int) else None,
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
                or snapshot.get("artifact_type") in (None, "structured-handoff")
            ),
            expected={"artifact_type": "structured-handoff"},
            actual={"artifact_type": snapshot.get("artifact_type")},
        ),
        _check(
            "claude_handoff_state_and_next_action_labels_are_known_if_present",
            snapshot.get("exists") is not True or custom_handoff_label_fields == [],
            expected={"custom_or_invalid_fields": []},
            actual={"custom_or_invalid_fields": custom_handoff_label_fields},
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


def _safe_current_job(status: dict[str, Any]) -> dict[str, Any]:
    current_job = status.get("current_job")
    if not isinstance(current_job, dict):
        return {"index": None, "model": None, "n": None, "set": None}
    return {
        "index": current_job.get("index") if isinstance(current_job.get("index"), int) else None,
        "model": _safe_model_label(current_job.get("model")),
        "n": current_job.get("n") if isinstance(current_job.get("n"), int) else None,
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
        "candidate_dimension_scope": dict,
    }
    issues = []
    for key, expected_type in required_types.items():
        value = status.get(key)
        if not isinstance(value, expected_type):
            issues.append(f"{key}:missing_or_not_{expected_type.__name__}")
    return issues


def _status_snapshot(status: dict[str, Any]) -> dict[str, Any]:
    latest_preflight = status.get("latest_preflight")
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
            "cursor": status.get("cursor") if isinstance(status.get("cursor"), int) else None,
            "queue_len": status.get("queue_len") if isinstance(status.get("queue_len"), int) else None,
            "done": status.get("done") if isinstance(status.get("done"), int) else None,
        },
        "full_promptset": {
            "prompt_count": (
                full_promptset.get("prompt_count")
                if isinstance(full_promptset, dict)
                and isinstance(full_promptset.get("prompt_count"), int)
                else None
            ),
        },
        "latest_preflight": {
            "exists": _status_value(status, "latest_preflight.exists"),
            "ready": _status_value(status, "latest_preflight.ready"),
            "readiness_scope": _known_status_label(
                _status_value(status, "latest_preflight.readiness_scope"),
                allowed=KNOWN_STATUS_READINESS_SCOPES,
            ),
            "ollama_checked": _status_value(status, "latest_preflight.ollama_checked"),
            "matches_current_state": _status_value(status, "latest_preflight.matches_current_state"),
            "needs_refresh": _status_value(status, "latest_preflight.needs_refresh"),
            "saved_lock_state": _known_status_label(
                _status_value(status, "latest_preflight.saved_lock_state.state"),
                allowed=KNOWN_STATUS_LOCK_STATES,
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
        "candidate_dimensions": {
            "rows": (
                candidate_scope.get("rows")
                if isinstance(candidate_scope, dict)
                and isinstance(candidate_scope.get("rows"), int)
                else None
            ),
            "review_gate_status": _known_status_label(
                _status_value(status, "candidate_dimension_scope.review_gate_status"),
                allowed=KNOWN_STATUS_REVIEW_GATE_STATUSES,
            ),
            "active_in_autonomous_engine": _status_value(status, "candidate_dimension_scope.active_in_autonomous_engine"),
            "ready_for_mass_grading": _status_value(status, "candidate_dimension_scope.ready_for_mass_grading"),
            "active_rubric_promotion_ready": _status_value(status, "candidate_dimension_scope.active_rubric_promotion_ready"),
            "review_needed_count": _status_value(status, "candidate_dimension_scope.review_needed_count"),
            "current_job_prompt_dimension_cells": _status_value(
                status,
                "candidate_dimension_scope.current_job_prompt_dimension_cells",
            ),
            "full_registry_prompt_dimension_cells": _status_value(
                status,
                "candidate_dimension_scope.full_registry_prompt_dimension_cells",
            ),
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
        for key in ("readiness_scope", "saved_lock_state"):
            if latest_preflight.get(key) == "custom_or_invalid":
                fields.append(f"latest_preflight.{key}")
        for key in ("blockers", "ignored_blockers", "state_mismatch_reasons"):
            values = latest_preflight.get(key)
            if isinstance(values, list) and "custom_or_invalid" in values:
                fields.append(f"latest_preflight.{key}")

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
        "check_count": summary.get("check_count") if isinstance(summary.get("check_count"), int) else None,
        "failed_count": summary.get("failed_count") if isinstance(summary.get("failed_count"), int) else None,
        "failed_ids": (
            summary.get("failed_ids")
            if isinstance(summary.get("failed_ids"), list)
            else []
        ),
        "project_id": summary.get("project_id") if isinstance(summary.get("project_id"), str) else None,
        "project_status": (
            summary.get("project_status") if isinstance(summary.get("project_status"), str) else None
        ),
        "project_pack_id_match": (
            summary.get("project_pack_id_match")
            if isinstance(summary.get("project_pack_id_match"), bool)
            else None
        ),
        "grounding_domain": (
            summary.get("grounding_domain") if isinstance(summary.get("grounding_domain"), str) else None
        ),
        "scheme_prompt_count": (
            summary.get("scheme_prompt_count") if isinstance(summary.get("scheme_prompt_count"), int) else None
        ),
        "scheme_prompt_category_count": (
            summary.get("scheme_prompt_category_count")
            if isinstance(summary.get("scheme_prompt_category_count"), int)
            else None
        ),
        "scheme_prompt_candidate_pattern_count": (
            summary.get("scheme_prompt_candidate_pattern_count")
            if isinstance(summary.get("scheme_prompt_candidate_pattern_count"), int)
            else None
        ),
        "scheme_prompt_candidate_patterns_without_project_declaration_count": (
            summary.get("scheme_prompt_candidate_patterns_without_project_declaration_count")
            if isinstance(summary.get("scheme_prompt_candidate_patterns_without_project_declaration_count"), int)
            else None
        ),
        "scheme_prompt_unresolved_scope_count": (
            summary.get("scheme_prompt_unresolved_scope_count")
            if isinstance(summary.get("scheme_prompt_unresolved_scope_count"), int)
            else None
        ),
        "scheme_prompt_not_ready_count": (
            summary.get("scheme_prompt_not_ready_count")
            if isinstance(summary.get("scheme_prompt_not_ready_count"), int)
            else None
        ),
        "scheme_prompt_categories_without_source_slots_count": (
            summary.get("scheme_prompt_categories_without_source_slots_count")
            if isinstance(summary.get("scheme_prompt_categories_without_source_slots_count"), int)
            else None
        ),
        "queued_jurisdiction_scope_count": (
            summary.get("queued_jurisdiction_scope_count")
            if isinstance(summary.get("queued_jurisdiction_scope_count"), int)
            else None
        ),
        "local_source_jurisdictions_without_scope_count": (
            summary.get("local_source_jurisdictions_without_scope_count")
            if isinstance(summary.get("local_source_jurisdictions_without_scope_count"), int)
            else None
        ),
        "duplicate_id_issue_count": (
            summary.get("duplicate_id_issue_count")
            if isinstance(summary.get("duplicate_id_issue_count"), int)
            else None
        ),
        "readiness_gate_missing_block_concept_count": (
            summary.get("readiness_gate_missing_block_concept_count")
            if isinstance(summary.get("readiness_gate_missing_block_concept_count"), int)
            else None
        ),
        "source_admission_missing_concept_count": (
            summary.get("source_admission_missing_concept_count")
            if isinstance(summary.get("source_admission_missing_concept_count"), int)
            else None
        ),
        "project_privacy_issue_count": (
            summary.get("project_privacy_issue_count")
            if isinstance(summary.get("project_privacy_issue_count"), int)
            else None
        ),
        "jurisdiction_pack_privacy_issue_count": (
            summary.get("jurisdiction_pack_privacy_issue_count")
            if isinstance(summary.get("jurisdiction_pack_privacy_issue_count"), int)
            else None
        ),
        "grounding_metadata_privacy_issue_count": (
            summary.get("grounding_metadata_privacy_issue_count")
            if isinstance(summary.get("grounding_metadata_privacy_issue_count"), int)
            else None
        ),
    }


def _sister_project_checks(report: dict[str, Any]) -> list[dict[str, Any]]:
    snapshot = _sister_project_snapshot(report)
    return [
        _check(
            "sister_project_planning_validator_passes",
            snapshot.get("ok") is True,
            expected={"ok": True, "failed_ids": []},
            actual={
                "ok": snapshot.get("ok"),
                "failed_ids": snapshot.get("failed_ids"),
                "duplicate_id_issue_count": snapshot.get("duplicate_id_issue_count"),
                "readiness_gate_missing_block_concept_count": snapshot.get(
                    "readiness_gate_missing_block_concept_count"
                ),
                "source_admission_missing_concept_count": snapshot.get(
                    "source_admission_missing_concept_count"
                ),
                "project_privacy_issue_count": snapshot.get("project_privacy_issue_count"),
                "jurisdiction_pack_privacy_issue_count": snapshot.get(
                    "jurisdiction_pack_privacy_issue_count"
                ),
                "grounding_metadata_privacy_issue_count": snapshot.get(
                    "grounding_metadata_privacy_issue_count"
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
            summary.get("artifact_count") if isinstance(summary.get("artifact_count"), int) else None
        ),
        "valid_artifact_count": (
            summary.get("valid_artifact_count")
            if isinstance(summary.get("valid_artifact_count"), int)
            else None
        ),
        "failed_artifact_count": (
            summary.get("failed_artifact_count")
            if isinstance(summary.get("failed_artifact_count"), int)
            else None
        ),
        "missing_or_unreadable_artifact_count": (
            summary.get("missing_or_unreadable_artifact_count")
            if isinstance(summary.get("missing_or_unreadable_artifact_count"), int)
            else None
        ),
        "markdown_artifact_count": (
            summary.get("markdown_artifact_count")
            if isinstance(summary.get("markdown_artifact_count"), int)
            else None
        ),
        "missing_or_unreadable_markdown_count": (
            summary.get("missing_or_unreadable_markdown_count")
            if isinstance(summary.get("missing_or_unreadable_markdown_count"), int)
            else None
        ),
        "unsafe_markdown_count": (
            summary.get("unsafe_markdown_count")
            if isinstance(summary.get("unsafe_markdown_count"), int)
            else None
        ),
        "artifact_path_mismatch_count": (
            summary.get("artifact_path_mismatch_count")
            if isinstance(summary.get("artifact_path_mismatch_count"), int)
            else None
        ),
        "total_check_count": (
            summary.get("total_check_count") if isinstance(summary.get("total_check_count"), int) else None
        ),
        "total_failed_check_count": (
            summary.get("total_failed_check_count")
            if isinstance(summary.get("total_failed_check_count"), int)
            else None
        ),
        "suite_check_count": (
            summary.get("suite_check_count")
            if isinstance(summary.get("suite_check_count"), int)
            else None
        ),
        "suite_failed_check_count": (
            summary.get("suite_failed_check_count")
            if isinstance(summary.get("suite_failed_check_count"), int)
            else None
        ),
        "phase_coverage_mismatch_count": (
            summary.get("phase_coverage_mismatch_count")
            if isinstance(summary.get("phase_coverage_mismatch_count"), int)
            else None
        ),
        "legal_anchor_channel_mismatch_count": (
            summary.get("legal_anchor_channel_mismatch_count")
            if isinstance(summary.get("legal_anchor_channel_mismatch_count"), int)
            else None
        ),
        "readiness_blocker_mismatch_count": (
            summary.get("readiness_blocker_mismatch_count")
            if isinstance(summary.get("readiness_blocker_mismatch_count"), int)
            else None
        ),
        "next_phase_coverage": {
            "phase_count": summary.get("curation_bundle_next_execution_phase_count"),
            "covered_actions": summary.get("curation_bundle_next_phase_covered_actions"),
        },
        "curator_phase_coverage": {
            "phase_count": summary.get("curation_bundle_curator_execution_phase_count"),
            "covered_actions": summary.get("curation_bundle_curator_phase_covered_actions"),
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
        "Read order for continuation sessions",
        "AGENTS.md",
        "CLAUDE.md",
        "docs/codex/PROJECT_BIBLE.md",
        ".claude/rules/05_project_bible_pickup.md",
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
            "project_bible_is_indexed_in_purpose_maps",
            (
                _text_contains(root_files, [
                    "`PROJECT_BIBLE.md`",
                    "Root pointer to the canonical long-loop pickup brief",
                    "docs/codex/PROJECT_BIBLE.md",
                ]) == []
                and _text_contains(file_purpose_guide, [
                    "| Agent handoff |",
                    "PROJECT_BIBLE.md",
                    ".claude/rules/",
                ]) == []
                and _text_contains(repo_layout, [
                    "AI pickup bridge",
                    "../PROJECT_BIBLE.md",
                    "codex/PROJECT_BIBLE.md",
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
                "docs/codex/PROJECT_BIBLE.md",
                ".claude/rules/05_project_bible_pickup.md",
            ]) == [],
            expected="CLAUDE.md references both pickup files",
            actual="ok" if "docs/codex/PROJECT_BIBLE.md" in claude else "missing project bible",
        ),
        _check(
            "claude_marks_old_suite_counts_historical",
            _text_contains(claude, [
                "Current validation discipline",
                "treat older suite counts in this file as historical",
                "python -m pytest packages --collect-only -q",
            ]) == [],
            expected="CLAUDE.md warns against reusing old suite counts as current evidence",
            actual="present" if "treat older suite counts in this file as historical" in claude else "missing",
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
        "docs/codex/PROJECT_BIBLE.md",
        "reports/autonomous_engine.stop",
        "call Ollama",
        "promote candidate dimensions",
    ])
    checks.append(_check(
        "hidden_pickup_rule_preserves_pause_boundary",
        hidden_rule_missing == [],
        expected=[],
        actual=hidden_rule_missing,
    ))

    goal_missing = _text_contains(goal_command, [
        "python scripts\\autonomous_engine.py --status",
        "lock.state: \"stale\"",
        "latest_preflight.saved_lock_state.state: \"stale\"",
        "Do not remove reports/autonomous_engine.stop",
        "do not start scripts/autonomous_engine.py in run/once mode",
        "do not call Ollama",
        "do not promote candidate dimensions",
        "python scripts\\validate_project_bible_pickup.py",
        "python scripts\\validate_sister_project_planning.py",
        "python scripts\\validate_global_protections_saved_artifacts.py",
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
        "direct helper validators/builders",
        "direct local imports",
        "sister-project validator's",
        "autonomous engine helper modules",
        "--root <path>",
        "--status-json <path>",
        "--global-protections-report-json <path>",
        "hidden Claude handoff",
        "structured-handoff",
        "unknown hidden handoff labels fail closed",
        "aggregate open-risk severity counts",
        "open_risks shape",
        "high/critical blocking-risk count",
        "unknown hidden open-risk severities fail closed",
        "failed-check",
        "ready `false`",
        "stop_sentinel_present",
        "declared candidate pattern IDs",
        "unresolved source-gap rows",
        "source admission rules",
        "international anchors cannot",
        "public complaint lists",
        "source_admission_missing=0",
        "omits raw scheme-prompt IDs",
        "source URLs",
        "aggregate counts",
        "invalid_or_unknown",
        "custom_or_invalid",
        "copied phase IDs",
        "Prompt parse-error details",
        "safe line numbers",
        "known safe error labels",
        "custom error labels",
        "Hidden handoff string fields",
        "allowlisted labels",
        "timestamp presence",
        "timestamp validity",
        "validated_after_handoff",
        "not newer than the validation run",
        "High or critical hidden open-risk severities fail closed",
        "unknown hidden open-risk severities fail closed",
        "Saved status string fields",
        "unknown status labels fail closed",
        "custom blocker or mismatch labels",
        "python scripts\\validate_sister_project_planning.py",
        "python scripts\\validate_global_protections_saved_artifacts.py",
        "python scripts\\validate_global_protections_saved_artifacts.py --json",
        'python -m pytest tests -q -k "global_protections or regulatory_miss_pattern"',
        "python scripts\\autonomous_engine.py --status",
        "latest_preflight.saved_lock_state.state: \"stale\"",
        "Ollama not checked",
        "Candidate dimensions from the research spider are propose-only",
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
    candidate_scope = status.get("candidate_dimension_scope")
    lock = status.get("lock")
    snapshot = _status_snapshot(status)
    custom_status_label_fields = _custom_status_label_fields(snapshot)

    checks.extend([
        _check(
            "status_string_labels_are_known_if_present",
            custom_status_label_fields == [],
            expected={"custom_or_invalid_fields": []},
            actual={"custom_or_invalid_fields": custom_status_label_fields},
        ),
        _check("engine_is_paused", status.get("paused") is True, expected=True, actual=status.get("paused")),
        _check(
            "stop_sentinel_is_present",
            status.get("stop_sentinel") == "reports/autonomous_engine.stop",
            expected="reports/autonomous_engine.stop",
            actual=_known_status_label(
                status.get("stop_sentinel"),
                allowed=KNOWN_STATUS_STOP_SENTINELS,
            ),
        ),
        _check(
            "engine_process_not_alive",
            status.get("engine_process_alive") is False,
            expected=False,
            actual=status.get("engine_process_alive"),
        ),
        _check(
            "lock_state_is_not_live",
            isinstance(lock, dict) and lock.get("state") in {"absent", "stale"},
            expected=["absent", "stale"],
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
            "latest_preflight_is_state_only_without_ollama",
            (
                isinstance(latest_preflight, dict)
                and latest_preflight.get("readiness_scope") == "state_only"
                and latest_preflight.get("ollama_checked") is False
            ),
            expected={"readiness_scope": "state_only", "ollama_checked": False},
            actual={
                "readiness_scope": _known_status_label(
                    _status_value(status, "latest_preflight.readiness_scope"),
                    allowed=KNOWN_STATUS_READINESS_SCOPES,
                ),
                "ollama_checked": _status_value(status, "latest_preflight.ollama_checked"),
            },
        ),
        _check(
            "latest_preflight_blocks_launch_on_stop_sentinel",
            (
                isinstance(latest_preflight, dict)
                and latest_preflight.get("ready") is False
                and isinstance(latest_preflight.get("blockers"), list)
                and "stop_sentinel_present" in latest_preflight.get("blockers")
                and latest_preflight.get("ignored_blockers") == []
            ),
            expected={
                "ready": False,
                "blockers_include": "stop_sentinel_present",
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
            "saved_preflight_lock_state_is_not_live",
            _status_value(status, "latest_preflight.saved_lock_state.state") in {"absent", "stale"},
            expected=["absent", "stale"],
            actual=_known_status_label(
                _status_value(status, "latest_preflight.saved_lock_state.state"),
                allowed=KNOWN_STATUS_LOCK_STATES,
            ),
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
            f"privacy_issues=project:{sister_project.get('project_privacy_issue_count')},"
            f"packs:{sister_project.get('jurisdiction_pack_privacy_issue_count')},"
            f"grounding:{sister_project.get('grounding_metadata_privacy_issue_count')}"
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
