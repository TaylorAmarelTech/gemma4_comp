"""Tests for scripts/autonomous_engine.py publish and plan safety contracts."""
from __future__ import annotations

import importlib.util
import hashlib
import json
import subprocess
import sys
from pathlib import Path

import pytest

_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(_ROOT / "scripts"))


def _load(name, path):
    spec = importlib.util.spec_from_file_location(name, path)
    mod = importlib.util.module_from_spec(spec)
    sys.modules[name] = mod
    spec.loader.exec_module(mod)
    return mod


ae = _load("autonomous_engine", _ROOT / "scripts" / "autonomous_engine.py")


def _cp(cmd, returncode=0, stdout="", stderr=""):
    return subprocess.CompletedProcess(cmd, returncode, stdout=stdout, stderr=stderr)


def _sha(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def _write_review_gate_files(tmp_path: Path, *, source_rows: int, ready: int, accepted: int) -> tuple[Path, Path, Path]:
    candidates = tmp_path / "dimension_candidates.jsonl"
    candidates.write_text("{}\n" * source_rows, encoding="utf-8")
    packet = tmp_path / "dimension_packet.json"
    packet.write_text(json.dumps({
        "_meta": {
            "source_artifact": "configs/duecare/benchmarks/research_spider/dimension_candidates.jsonl",
            "source_artifact_sha256": _sha(candidates),
            "source_artifact_rows": source_rows,
        },
        "summary": {"dimension_candidate_rows": source_rows},
    }), encoding="utf-8")
    validation = tmp_path / "dimension_validation.json"
    validation.write_text(json.dumps({
        "_meta": {
            "packet_source_artifact_sha256": _sha(candidates),
            "packet_source_artifact_rows": source_rows,
            "packet_artifact_sha256": _sha(packet),
        },
        "summary": {
            "ok": True,
            "dimension_review_rows": source_rows,
            "rows_accepted_for_rubric_proposal": accepted,
            "rows_ready_claimed": ready,
            "root_issue_count": 0,
        },
    }), encoding="utf-8")
    return candidates, packet, validation


def test_run_job_pins_active_board_rubric_v1(monkeypatch):
    calls = []

    def fake_run(cmd, capture=False, timeout=None):
        calls.append(cmd)
        return _cp(cmd)

    monkeypatch.setattr(ae, "_run", fake_run)
    monkeypatch.setattr(ae, "log", lambda _msg: None)

    assert ae.run_job("gemma4:31b", 40) is True

    assert len(calls) == 1
    cmd = calls[0]
    assert cmd[0] == sys.executable
    assert cmd[1].endswith("rich_harness_lift.py")
    assert "--rubric-version" in cmd
    assert cmd[cmd.index("--rubric-version") + 1] == "v1"
    assert "--harness-version" in cmd
    assert cmd[cmd.index("--harness-version") + 1] == "h1"
    assert cmd[cmd.index("--grader") + 1] == "batched"
    assert "--pairwise" in cmd
    assert "v2" not in cmd
    assert "h2" not in cmd


def test_run_job_passes_perdim_mode(monkeypatch):
    calls = []
    monkeypatch.setattr(ae, "_run", lambda cmd, capture=False, timeout=None: calls.append(cmd) or _cp(cmd))
    monkeypatch.setattr(ae, "log", lambda _msg: None)
    monkeypatch.setattr(ae, "ensure_full_promptset", lambda: True)

    assert ae.run_job("gemma4:31b", 0, "full", "perdim") is True

    cmd = calls[0]
    assert cmd[cmd.index("--grader") + 1] == "perdim"
    assert cmd[cmd.index("--prompts") + 1] == str(ae.PROMPTS_FULL)
    assert "--pairwise" not in cmd
    assert "--require-complete" in cmd


def test_run_job_maps_retryable_incomplete_coverage_to_tristate(monkeypatch):
    calls = []
    monkeypatch.setattr(
        ae, "_run",
        lambda cmd, capture=False, timeout=None: calls.append(cmd) or _cp(cmd, returncode=ae.INCOMPLETE_COVERAGE_EXIT),
    )
    monkeypatch.setattr(ae, "log", lambda _msg: None)
    monkeypatch.setattr(ae, "ensure_full_promptset", lambda: True)

    assert ae.run_job("gemma4:31b", 0, "full", "perdim") is None
    assert "--require-complete" in calls[0]


def test_queue_entries_are_backward_compatible_and_perdim_jobs_are_first():
    assert ae._job(["m", 1]) == ("m", 1, None, "batched")
    assert ae._job(["m", 2, "full"]) == ("m", 2, "full", "batched")
    assert ae._job(["m", 0, "full", "perdim"]) == ("m", 0, "full", "perdim")
    assert ae._queue_state({"queue": [["m", 1], ["m", 0, "full", "perdim"]]})["valid"] is True
    assert ae._queue_state({"queue": [["m", 0, "full", "unknown"]]}) == {
        "valid": False, "error": "queue_entry_invalid", "entry_index": 0,
    }
    assert ae.DEFAULT_QUEUE[:len(ae._SWEEP_MODELS)] == [
        [model, 0, "full", "perdim"] for model in ae._SWEEP_MODELS
    ]


def test_prioritize_perdim_full_preserves_completed_prefix_and_other_job_order():
    first = [ae._SWEEP_MODELS[0], 0, "full", "perdim"]
    old_a = ["legacy-a", 40]
    old_b = ["legacy-b", 1500, "full"]
    remaining_priority = [ae._SWEEP_MODELS[2], 0, "full", "perdim"]
    st = {"queue": [first, old_a, old_b, remaining_priority], "cursor": 1}

    result = ae.prioritize_perdim_full(st)

    assert st["queue"][:1] == [first]
    assert st["queue"][1:4] == [
        [model, 0, "full", "perdim"] for model in ae._SWEEP_MODELS[1:]
    ]
    assert st["queue"][4:] == [old_a, old_b]
    assert st["queue_policy"] == "perdim_full_first_v1"
    assert result["changed"] is True
    assert result["current_job"] == [ae._SWEEP_MODELS[1], 0, "full", "perdim"]


def test_load_state_merges_perdim_jobs_without_duplicating_explicit_batched_job(tmp_path, monkeypatch):
    state_path = tmp_path / "state.json"
    default_queue = [["legacy", 1, "full"], ["flagship", 0, "full", "perdim"]]
    state_path.write_text(json.dumps({
        "queue": [["legacy", 1, "full", "batched"]],
        "cursor": 1,
        "ticks": 7,
        "done": [{"model": "legacy"}],
        "started": "s",
    }), encoding="utf-8")
    monkeypatch.setattr(ae, "STATE", state_path)
    monkeypatch.setattr(ae, "DEFAULT_QUEUE", default_queue)

    state = ae.load_state()

    assert state["cursor"] == 1
    assert state["ticks"] == 7
    assert state["done"] == [{"model": "legacy"}]
    assert state["queue"] == [
        ["legacy", 1, "full", "batched"],
        ["flagship", 0, "full", "perdim"],
    ]


def test_unexpected_staged_paths_allows_only_board_contract_paths():
    assert ae._unexpected_staged_paths([
        "docs/research/benchmark_leaderboard.md",
        "docs/autonomous_loop_plan.md",
    ]) == []
    assert ae._unexpected_staged_paths([
        "docs/research/benchmark_leaderboard.md",
        "scripts/palermo_screening.py",
    ]) == ["scripts/palermo_screening.py"]


def test_staged_paths_normalizes_windows_separators(monkeypatch):
    monkeypatch.setattr(
        ae,
        "_run",
        lambda cmd, capture=False: _cp(cmd, stdout="docs\\autonomous_loop_plan.md\n"),
    )
    assert ae._staged_paths() == ["docs/autonomous_loop_plan.md"]


def test_publish_refuses_when_unrelated_staged_paths_exist(monkeypatch):
    calls = []
    logs = []

    def fake_run(cmd, capture=False):
        calls.append(cmd)
        if cmd == ["git", "diff", "--cached", "--name-only"]:
            return _cp(cmd, stdout="docs/autonomous_loop_plan.md\nscripts/palermo_screening.py\n")
        raise AssertionError(f"unexpected command: {cmd}")

    monkeypatch.setattr(ae, "_run", fake_run)
    monkeypatch.setattr(ae, "log", logs.append)

    ae.publish("test")

    assert calls == [["git", "diff", "--cached", "--name-only"]]
    assert not any(cmd[:3] == ["git", "add", "--"] for cmd in calls)
    assert not any(cmd[:2] == ["git", "commit"] for cmd in calls)
    assert not any(cmd[:2] == ["git", "push"] for cmd in calls)
    assert any("refusing commit" in line and "scripts/palermo_screening.py" in line for line in logs)


def test_publish_rechecks_staged_paths_after_git_add(monkeypatch):
    calls = []
    logs = []

    def fake_run(cmd, capture=False):
        calls.append(cmd)
        if cmd == ["git", "diff", "--cached", "--name-only"]:
            if calls.count(cmd) == 1:
                return _cp(cmd, stdout="")
            return _cp(cmd, stdout="docs/autonomous_loop_plan.md\nscripts/palermo_screening.py\n")
        if cmd[:3] == ["git", "add", "--"]:
            return _cp(cmd)
        if cmd[:4] == ["git", "status", "--porcelain", "--"]:
            return _cp(cmd, stdout="M  docs/autonomous_loop_plan.md\n")
        raise AssertionError(f"unexpected command: {cmd}")

    monkeypatch.setattr(ae, "_run", fake_run)
    monkeypatch.setattr(ae, "log", logs.append)

    ae.publish("test")

    assert any(cmd[:3] == ["git", "add", "--"] for cmd in calls)
    assert not any(cmd[:2] == ["git", "commit"] for cmd in calls)
    assert not any(cmd[:2] == ["git", "push"] for cmd in calls)
    assert any("refusing commit" in line and "scripts/palermo_screening.py" in line for line in logs)


def test_publish_commits_only_allowed_paths_with_pathspec(monkeypatch):
    calls = []
    diff_cached_calls = 0

    def fake_run(cmd, capture=False):
        nonlocal diff_cached_calls
        calls.append(cmd)
        if cmd == ["git", "diff", "--cached", "--name-only"]:
            diff_cached_calls += 1
            return _cp(cmd, stdout="docs/autonomous_loop_plan.md\n")
        if cmd[:3] == ["git", "add", "--"]:
            return _cp(cmd)
        if cmd[:4] == ["git", "status", "--porcelain", "--"]:
            return _cp(cmd, stdout="M  docs/autonomous_loop_plan.md\n")
        if cmd[:2] == ["git", "commit"]:
            return _cp(cmd)
        if cmd == ["git", "push"]:
            return _cp(cmd)
        raise AssertionError(f"unexpected command: {cmd}")

    monkeypatch.setattr(ae, "_run", fake_run)
    monkeypatch.setattr(ae, "log", lambda _msg: None)

    ae.publish("test")

    assert diff_cached_calls == 2
    commit_cmd = next(cmd for cmd in calls if cmd[:2] == ["git", "commit"])
    assert "--" in commit_cmd
    pathspec = commit_cmd[commit_cmd.index("--") + 1:]
    assert pathspec == ae.COMMIT_PATHS
    assert ["git", "push"] in calls


def test_publish_stops_if_git_add_fails(monkeypatch):
    calls = []
    logs = []

    def fake_run(cmd, capture=False):
        calls.append(cmd)
        if cmd == ["git", "diff", "--cached", "--name-only"]:
            return _cp(cmd, stdout="")
        if cmd[:3] == ["git", "add", "--"]:
            return _cp(cmd, returncode=1, stderr="nope")
        raise AssertionError(f"unexpected command: {cmd}")

    monkeypatch.setattr(ae, "_run", fake_run)
    monkeypatch.setattr(ae, "log", logs.append)

    ae.publish("test")

    assert calls == [
        ["git", "diff", "--cached", "--name-only"],
        ["git", "add", "--", *ae.COMMIT_PATHS],
    ]
    assert any("git add failed" in line for line in logs)


def test_update_plan_writes_ascii_status_doc(tmp_path, monkeypatch):
    plan = tmp_path / "autonomous_loop_plan.md"
    candidates, packet, validation = _write_review_gate_files(tmp_path, source_rows=7, ready=0, accepted=0)
    monkeypatch.setattr(ae, "PLAN", plan)
    monkeypatch.setattr(ae, "STOP", tmp_path / "autonomous_engine.stop")
    monkeypatch.setattr(ae, "DIMENSION_CANDIDATES", candidates)
    monkeypatch.setattr(ae, "DIM_REVIEW_PACKET", packet)
    monkeypatch.setattr(ae, "DIM_REVIEW_VALIDATION", validation)
    monkeypatch.setattr(ae, "now", lambda: "2026-06-29T00:00:00Z")
    monkeypatch.setattr(ae, "_full_prompt_count", lambda: (50, ""))
    monkeypatch.setattr(ae, "_jsonl_line_count", lambda _path: 7)
    monkeypatch.setattr(ae, "_jsonl_field_counts", lambda _path, field: {
        "candidate_needs_review_before_rubric_merge": 7,
    } if field == "status" else {})

    ae.update_plan({"cursor": 0, "queue": [["m", 1]], "started": "s", "ticks": 1}, ["m", 1])

    text = plan.read_text(encoding="utf-8")
    assert "# Autonomous benchmark engine - plan & live status" in text
    assert "**Started** s - **updated** 2026-06-29T00:00:00Z - **ticks** 1" in text
    assert "- **Status:** `scripts/autonomous_engine.ps1 -Status` reports state cursor/queue health" in text
    assert "`state_only` diagnostic report and returns a non-launch exit code" in text
    assert "preserves the Python exit code in `$LASTEXITCODE`" in text
    assert "`--no-ollama-check` is state-only for preflight diagnostics" in text
    assert "direct Python loop mode" in text
    assert "## Current scope" in text
    assert (
        "**Active runner:** `rich_harness_lift.py`; board rubric version: `v1`; "
        "opt-in rubric versions excluded: `v2`; rubric mixing allowed: `no`; "
        "board harness version: `h1`; opt-in harness versions excluded: `h2`; "
        "harness mixing allowed: `no`; grader: `batched`; "
        "per-dimension evidence mixed into board: `no`; "
        "candidate-dimension sweep active: `no`."
    ) in text
    assert (
        "1 target prompts; 3 response-generation cells; 9 component-judge cells; "
        "9 underlying component judge calls (1 per panel cell); 3 pairwise-judge cells"
    ) in text
    assert "7 candidate dimensions; 7 still need curator review; 350 full-registry prompt-dimension cells" in text
    assert "gate `validated_zero_proposals`; accepted proposals 0; ready claims 0." in text
    assert "candidate-dimension row labels alone are not enough" in text
    assert chr(0x2014) not in text and chr(0x00B7) not in text and chr(0x00E2) not in text


def test_update_plan_marks_current_job_paused_when_stop_sentinel_exists(tmp_path, monkeypatch):
    plan = tmp_path / "autonomous_loop_plan.md"
    candidates, packet, validation = _write_review_gate_files(tmp_path, source_rows=2, ready=1, accepted=1)
    stop = tmp_path / "autonomous_engine.stop"
    stop.write_text("local operator note that must not be copied", encoding="utf-8")
    monkeypatch.setattr(ae, "PLAN", plan)
    monkeypatch.setattr(ae, "STOP", stop)
    monkeypatch.setattr(ae, "DIMENSION_CANDIDATES", candidates)
    monkeypatch.setattr(ae, "DIM_REVIEW_PACKET", packet)
    monkeypatch.setattr(ae, "DIM_REVIEW_VALIDATION", validation)
    monkeypatch.setattr(ae, "now", lambda: "2026-06-29T00:00:00Z")
    monkeypatch.setattr(ae, "_full_prompt_count", lambda: (20000, ""))
    monkeypatch.setattr(ae, "_jsonl_line_count", lambda _path: 2)
    monkeypatch.setattr(ae, "_jsonl_field_counts", lambda _path, field: {
        "candidate_needs_review_before_rubric_merge": 2,
    } if field == "status" else {})

    ae.update_plan({"cursor": 1, "queue": [["done", 1], ["m", 10000, "full", "perdim"]],
                    "started": "s", "ticks": 11}, ["m", 10000, "full", "perdim"])

    text = plan.read_text(encoding="utf-8")
    assert "# Autonomous benchmark engine - plan & paused status" in text
    assert "**Progress** 1/2 jobs complete - paused before `m` n=10000 (full registry)" in text
    assert "grader=perdim" in text
    assert "| 1 | `done` | 1 | curated | batched | done |" in text
    assert "| 2 | `m` | 10000 | full | perdim | paused |" in text
    assert (
        "10,000 target prompts; 30,000 response-generation cells; 90,000 component-judge cells; "
        "450,000 underlying component judge calls (5 per panel cell)"
    ) in text
    assert "2 candidate dimensions; 2 still need curator review; 40,000 full-registry prompt-dimension cells" in text
    assert "gate `proposals_ready_for_manual_merge`; accepted proposals 1; ready claims 1." in text
    assert "local operator note" not in text
    assert "`scripts/autonomous_engine.ps1 -Run`" in text
    assert "later watchdog ticks do not resume paused judging" in text


def test_main_status_reports_pause_sentinel_without_reading_note(tmp_path, monkeypatch, capsys):
    stop = tmp_path / "autonomous_engine.stop"
    stop.write_text("worker@example.com local note", encoding="utf-8")
    lock = tmp_path / "autonomous_engine.lock"
    lock.write_text("999999,2026-06-30T00:00:00Z", encoding="utf-8")
    preflight_report = tmp_path / "autonomous_engine_preflight.json"
    preflight_report.write_text(json.dumps({
        "_meta": {
            "schema_version": "autonomous_engine_preflight.v1",
            "written_at": "2026-06-30T00:01:00Z",
            "mode": "manual_preflight",
        },
        "ready": False,
        "blockers": ["ollama_unavailable"],
        "ignored_blockers": ["stop_sentinel_present"],
        "cursor": 0,
        "cursor_state": {"raw": 0, "value": 0, "valid": True, "error": ""},
        "queue_state": {"valid": True, "error": "", "entry_index": None},
        "current_job": {"model": "m", "n": 1, "set": "full"},
        "paused": True,
        "stop_sentinel": "external/autonomous_engine.stop",
        "lock": {"exists": True, "pid": 999999, "alive": False},
        "dimension_candidates": {"review_gate": {"status": "validated_zero_proposals"}},
        "ollama": {
            "checked": True,
            "ok": False,
            "diagnosis": {"code": "ollama_log_access_denied"},
            "stderr_tail": "worker@example.com should not be copied into status",
        },
    }), encoding="utf-8")
    monkeypatch.setattr(sys, "argv", ["autonomous_engine.py", "--status"])
    monkeypatch.setattr(ae, "STOP", stop)
    monkeypatch.setattr(ae, "LOCK", lock)
    monkeypatch.setattr(ae, "PREFLIGHT_REPORT", preflight_report)
    monkeypatch.setattr(ae, "pid_alive", lambda _pid: False)
    prompts = tmp_path / "full_promptset.json"
    prompts.write_text("{}", encoding="utf-8")
    candidates = tmp_path / "dimension_candidates.jsonl"
    candidates.write_text("{}", encoding="utf-8")
    monkeypatch.setattr(ae, "PROMPTS_FULL", prompts)
    monkeypatch.setattr(ae, "DIMENSION_CANDIDATES", candidates)
    monkeypatch.setattr(ae, "_full_prompt_count", lambda: (76442, ""))
    monkeypatch.setattr(ae, "_jsonl_line_count", lambda _path: 201)
    monkeypatch.setattr(ae, "_jsonl_field_counts", lambda _path, field: {
        "candidate_needs_review_before_rubric_merge": 201,
    } if field == "status" else {})
    monkeypatch.setattr(ae, "_dimension_review_gate_status", lambda: {
        "status": "validated_zero_proposals",
        "active_rubric_promotion_ready": False,
        "validation": {"summary": {"rows_accepted_for_rubric_proposal": 0, "rows_ready_claimed": 0}},
    })
    monkeypatch.setattr(ae, "load_state", lambda: {
        "started": "s",
        "updated": "u",
        "ticks": 1,
        "cursor": 0,
        "queue": [["m", 1, "full"]],
        "done": [],
    })

    assert ae.main() == 0

    payload = __import__("json").loads(capsys.readouterr().out)
    assert payload["paused"] is True
    assert payload["stop_sentinel"] == "external/autonomous_engine.stop"
    assert payload["current_job"] == {
        "index": 1, "model": "m", "n": 1, "set": "full", "grader": "batched",
    }
    assert payload["cursor_state"] == {"raw": 0, "value": 0, "valid": True, "error": ""}
    assert payload["queue_state"] == {"valid": True, "error": "", "entry_index": None}
    assert payload["engine_process_alive"] is False
    assert payload["lock"] == {
        "exists": True,
        "pid": 999999,
        "alive": False,
        "stale": True,
        "state": "stale",
    }
    assert payload["last_preflight_report"] == "external/autonomous_engine_preflight.json"
    assert payload["latest_preflight"]["ready"] is False
    assert payload["latest_preflight"]["blockers"] == ["ollama_unavailable"]
    assert payload["latest_preflight"]["ignored_blockers"] == ["stop_sentinel_present"]
    assert payload["latest_preflight"]["dimension_review_status"] == "validated_zero_proposals"
    assert payload["latest_preflight"]["ollama_checked"] is True
    assert payload["latest_preflight"]["ollama_ok"] is False
    assert payload["latest_preflight"]["readiness_scope"] == "launch"
    assert payload["latest_preflight"]["ollama_diagnosis_code"] == "ollama_log_access_denied"
    assert payload["latest_preflight"]["saved_lock_state"] == {
        "exists": True,
        "pid": 999999,
        "alive": False,
        "stale": True,
        "state": "stale",
    }
    assert payload["latest_preflight"]["matches_current_state"] is True
    assert payload["latest_preflight"]["state_mismatch_reasons"] == []
    assert payload["latest_preflight"]["needs_refresh"] is False
    assert "refresh_command" not in payload["latest_preflight"]
    assert payload["active_loop_scope"]["candidate_dimension_sweep_active"] is False
    assert payload["active_loop_scope"]["rubric_version"] == "v1"
    assert payload["active_loop_scope"]["opt_in_rubric_versions_excluded"] == ["v2"]
    assert payload["active_loop_scope"]["rubric_version_mixing_allowed"] is False
    assert payload["active_loop_scope"]["harness_version"] == "h1"
    assert payload["active_loop_scope"]["opt_in_harness_versions_excluded"] == ["h2"]
    assert payload["active_loop_scope"]["harness_version_mixing_allowed"] is False
    assert payload["active_loop_scope"]["grader"] == "batched"
    assert payload["active_loop_scope"]["judge_calls_per_panel_cell"] == 1
    assert payload["active_loop_scope"]["max_component_judge_calls"] == 9
    assert payload["active_loop_scope"]["target_prompt_count"] == 1
    assert payload["active_loop_scope"]["max_component_judge_cells"] == 9
    assert payload["full_promptset"]["prompt_count"] == 76442
    assert payload["candidate_dimension_scope"]["rows"] == 201
    assert payload["candidate_dimension_scope"]["review_gate_status"] == "validated_zero_proposals"
    assert payload["candidate_dimension_scope"]["active_rubric_promotion_ready"] is False
    assert payload["candidate_dimension_scope"]["review_gate_validation_summary_issues"] == []
    assert payload["candidate_dimension_scope"]["ready_for_mass_grading"] is False
    assert payload["candidate_dimension_scope"]["row_status_ready_for_mass_grading"] is False
    assert payload["candidate_dimension_scope"]["parse_errors"] == []
    assert payload["candidate_dimension_scope"]["current_job_prompt_dimension_cells"] == 201
    assert payload["candidate_dimension_scope"]["full_registry_prompt_dimension_cells"] == 15364842
    assert "worker@example.com" not in str(payload)


def test_status_marks_latest_preflight_stale_when_current_state_changes(tmp_path, monkeypatch):
    preflight_report = tmp_path / "autonomous_engine_preflight.json"
    preflight_report.write_text(json.dumps({
        "_meta": {"schema_version": "autonomous_engine_preflight.v1"},
        "ready": True,
        "blockers": [],
        "ignored_blockers": [],
        "cursor": 0,
        "current_job": {"model": "old", "n": 1, "set": "curated"},
        "paused": True,
        "stop_sentinel": "external/autonomous_engine.stop",
        "lock": {"exists": True, "pid": 1234, "alive": True},
    }), encoding="utf-8")
    monkeypatch.setattr(ae, "PREFLIGHT_REPORT", preflight_report)
    monkeypatch.setattr(ae, "STOP", tmp_path / "autonomous_engine.stop")
    monkeypatch.setattr(ae, "LOCK", tmp_path / "autonomous_engine.lock")
    monkeypatch.setattr(ae, "load_state", lambda: {
        "started": "s",
        "updated": "u",
        "ticks": 1,
        "cursor": 1,
        "queue": [["old", 1], ["new", 2, "full"]],
        "done": [["old", 1]],
    })

    payload = ae.status_payload()

    assert payload["latest_preflight"]["matches_current_state"] is False
    assert payload["latest_preflight"]["state_mismatch_reasons"] == [
        "cursor_changed",
        "cursor_state_changed",
        "queue_state_changed",
        "current_job_changed",
        "pause_state_changed",
        "stop_sentinel_changed",
        "lock_changed",
    ]
    assert payload["latest_preflight"]["needs_refresh"] is True
    assert payload["latest_preflight"]["refresh_command"] == "scripts/autonomous_engine.ps1 -Preflight"
    assert payload["current_job"] == {
        "index": 2, "model": "new", "n": 2, "set": "full", "grader": "batched",
    }


def test_status_marks_no_ollama_preflight_as_state_only(tmp_path, monkeypatch):
    preflight_report = tmp_path / "autonomous_engine_preflight.json"
    preflight_report.write_text(json.dumps({
        "_meta": {"schema_version": "autonomous_engine_preflight.v1"},
        "ready": True,
        "blockers": [],
        "ignored_blockers": ["stop_sentinel_present"],
        "cursor": 0,
        "cursor_state": {"raw": 0, "value": 0, "valid": True, "error": ""},
        "queue_state": {"valid": True, "error": "", "entry_index": None},
        "current_job": {"model": "m", "n": 1, "set": "curated"},
        "paused": True,
        "stop_sentinel": "external/autonomous_engine.stop",
        "lock": {"exists": False, "pid": None, "alive": False},
        "readiness_scope": "state_only",
        "launch_ready_requires_ollama_check": True,
        "ollama": {"checked": False, "ok": None},
    }), encoding="utf-8")
    monkeypatch.setattr(ae, "PREFLIGHT_REPORT", preflight_report)

    summary = ae._latest_preflight_summary(
        cursor=0,
        cursor_state={"raw": 0, "value": 0, "valid": True, "error": ""},
        queue_state={"valid": True, "error": "", "entry_index": None},
        current_job={"index": 1, "model": "m", "n": 1, "set": "curated"},
        paused=True,
        stop_sentinel="external/autonomous_engine.stop",
        lock={"exists": False, "pid": None, "alive": False},
    )

    assert summary["ready"] is True
    assert summary["matches_current_state"] is True
    assert summary["ollama_checked"] is False
    assert summary["ollama_ok"] is None
    assert summary["readiness_scope"] == "state_only"
    assert summary["launch_ready_requires_ollama_check"] is True
    assert summary["saved_lock_state"] == {
        "exists": False,
        "pid": None,
        "alive": False,
        "stale": False,
        "state": "absent",
    }


def test_latest_preflight_summary_surfaces_dimension_review_issue_ids(tmp_path, monkeypatch):
    preflight_report = tmp_path / "autonomous_engine_preflight.json"
    preflight_report.write_text(json.dumps({
        "_meta": {"schema_version": "autonomous_engine_preflight.v1"},
        "ready": False,
        "blockers": ["dimension_review_validation_summary_malformed"],
        "dimension_candidates": {
            "review_gate": {
                "status": "validation_summary_malformed",
                "validation_summary_issues": [
                    "root_issue_count_missing_or_not_integer",
                    17,
                    "dimension_review_rows_must_match_packet_source_artifact_rows",
                ],
            },
        },
        "ollama": {"checked": False, "ok": None},
    }), encoding="utf-8")
    monkeypatch.setattr(ae, "PREFLIGHT_REPORT", preflight_report)

    summary = ae._latest_preflight_summary()

    assert summary["dimension_review_status"] == "validation_summary_malformed"
    assert summary["dimension_review_validation_summary_issues"] == [
        "root_issue_count_missing_or_not_integer",
        "dimension_review_rows_must_match_packet_source_artifact_rows",
    ]


def test_status_marks_missing_latest_preflight_unmatched(tmp_path, monkeypatch):
    monkeypatch.setattr(ae, "PREFLIGHT_REPORT", tmp_path / "missing_preflight.json")

    summary = ae._latest_preflight_summary()

    assert summary == {
        "exists": False,
        "path": "",
        "matches_current_state": False,
        "state_mismatch_reasons": ["preflight_report_missing"],
        "needs_refresh": True,
        "refresh_command": "scripts/autonomous_engine.ps1 -Preflight",
    }


def test_status_uses_pause_safe_preflight_refresh_command(tmp_path, monkeypatch):
    monkeypatch.setattr(ae, "PREFLIGHT_REPORT", tmp_path / "missing_preflight.json")

    summary = ae._latest_preflight_summary(paused=True)

    assert summary["needs_refresh"] is True
    assert summary["refresh_command"] == "scripts/autonomous_engine.ps1 -Preflight -IgnoreStopSentinel"


def test_status_marks_malformed_latest_preflight_unmatched(tmp_path, monkeypatch):
    preflight_report = tmp_path / "autonomous_engine_preflight.json"
    preflight_report.write_text("{not json", encoding="utf-8")
    monkeypatch.setattr(ae, "PREFLIGHT_REPORT", preflight_report)

    summary = ae._latest_preflight_summary()

    assert summary["exists"] is True
    assert summary["path"] == "external/autonomous_engine_preflight.json"
    assert summary["matches_current_state"] is False
    assert summary["state_mismatch_reasons"] == ["preflight_report_unreadable"]
    assert summary["needs_refresh"] is True
    assert summary["refresh_command"] == "scripts/autonomous_engine.ps1 -Preflight"
    assert "JSONDecodeError" in summary["error"]


def test_status_marks_non_object_latest_preflight_unmatched(tmp_path, monkeypatch):
    preflight_report = tmp_path / "autonomous_engine_preflight.json"
    preflight_report.write_text("[]", encoding="utf-8")
    monkeypatch.setattr(ae, "PREFLIGHT_REPORT", preflight_report)

    summary = ae._latest_preflight_summary()

    assert summary == {
        "exists": True,
        "path": "external/autonomous_engine_preflight.json",
        "error": "preflight_report_not_object",
        "matches_current_state": False,
        "state_mismatch_reasons": ["preflight_report_not_object"],
        "needs_refresh": True,
        "refresh_command": "scripts/autonomous_engine.ps1 -Preflight",
    }


def test_latest_preflight_marks_lock_exists_change_stale(tmp_path, monkeypatch):
    preflight_report = tmp_path / "autonomous_engine_preflight.json"
    preflight_report.write_text(json.dumps({
        "_meta": {"schema_version": "autonomous_engine_preflight.v1"},
        "lock": {"exists": True, "pid": None, "alive": False},
    }), encoding="utf-8")
    monkeypatch.setattr(ae, "PREFLIGHT_REPORT", preflight_report)

    summary = ae._latest_preflight_summary(lock={"exists": False, "pid": None, "alive": False})

    assert summary["matches_current_state"] is False
    assert summary["state_mismatch_reasons"] == ["lock_changed"]
    assert summary["saved_lock_state"] == {
        "exists": True,
        "pid": None,
        "alive": False,
        "stale": True,
        "state": "stale",
    }


def test_lock_status_classifies_absent_stale_and_live_locks(tmp_path, monkeypatch):
    lock = tmp_path / "autonomous_engine.lock"
    monkeypatch.setattr(ae, "LOCK", lock)

    assert ae._lock_status() == {
        "exists": False,
        "pid": None,
        "alive": False,
        "stale": False,
        "state": "absent",
    }

    lock.write_text("12345,2026-07-01T00:00:00Z", encoding="utf-8")
    monkeypatch.setattr(ae, "pid_alive", lambda _pid: False)
    assert ae._lock_status() == {
        "exists": True,
        "pid": 12345,
        "alive": False,
        "stale": True,
        "state": "stale",
    }

    monkeypatch.setattr(ae, "pid_alive", lambda _pid: True)
    assert ae._lock_status() == {
        "exists": True,
        "pid": 12345,
        "alive": True,
        "stale": False,
        "state": "live",
    }


def test_preflight_and_status_block_negative_state_cursor(tmp_path, monkeypatch):
    monkeypatch.setattr(ae, "STOP", tmp_path / "autonomous_engine.stop")
    monkeypatch.setattr(ae, "LOCK", tmp_path / "autonomous_engine.lock")
    monkeypatch.setattr(ae, "PROMPTS_FULL", tmp_path / "full_promptset.json")
    monkeypatch.setattr(ae, "DIMENSION_CANDIDATES", tmp_path / "dimension_candidates.jsonl")
    monkeypatch.setattr(ae, "_dimension_review_gate_status", lambda: {
        "status": "validated_zero_proposals",
        "active_rubric_promotion_ready": False,
        "validation": {"summary": {}},
    })
    monkeypatch.setattr(ae, "load_state", lambda: {
        "started": "s",
        "updated": "u",
        "ticks": 1,
        "cursor": -1,
        "queue": [["first", 1], ["must-not-select", 2, "full"]],
        "done": [],
    })

    report = ae.preflight_status(check_ollama=False)
    status = ae.status_payload()

    assert report["blockers"] == ["state_cursor_invalid"]
    assert report["cursor_state"] == {"raw": -1, "value": None, "valid": False, "error": "cursor_negative"}
    assert report["current_job"] == {"model": None, "n": None, "set": None, "grader": None}
    assert status["cursor_state"] == report["cursor_state"]
    assert status["current_job"] == {
        "index": None, "model": None, "n": None, "set": None, "grader": None,
    }


def test_preflight_blocks_non_integer_state_cursor(tmp_path, monkeypatch):
    monkeypatch.setattr(ae, "STOP", tmp_path / "autonomous_engine.stop")
    monkeypatch.setattr(ae, "LOCK", tmp_path / "autonomous_engine.lock")
    monkeypatch.setattr(ae, "PROMPTS_FULL", tmp_path / "full_promptset.json")
    monkeypatch.setattr(ae, "DIMENSION_CANDIDATES", tmp_path / "dimension_candidates.jsonl")
    monkeypatch.setattr(ae, "_dimension_review_gate_status", lambda: {
        "status": "validated_zero_proposals",
        "active_rubric_promotion_ready": False,
        "validation": {"summary": {}},
    })
    monkeypatch.setattr(ae, "load_state", lambda: {
        "cursor": "1",
        "queue": [["first", 1], ["second", 2]],
        "done": [],
    })

    report = ae.preflight_status(check_ollama=False)

    assert report["blockers"] == ["state_cursor_invalid"]
    assert report["cursor_state"] == {"raw": "1", "value": None, "valid": False, "error": "cursor_not_integer"}
    assert report["current_job"] == {"model": None, "n": None, "set": None, "grader": None}


def test_tick_refuses_invalid_state_cursor_without_running_job(tmp_path, monkeypatch):
    logs = []
    monkeypatch.setattr(ae, "STOP", tmp_path / "autonomous_engine.stop")
    monkeypatch.setattr(ae, "load_state", lambda: {
        "cursor": -1,
        "queue": [["first", 1], ["must-not-run", 2]],
        "done": [],
    })
    monkeypatch.setattr(ae, "log", logs.append)
    monkeypatch.setattr(ae, "run_job", lambda *_args, **_kwargs: (_ for _ in ()).throw(AssertionError("no job")))
    monkeypatch.setattr(ae, "regen_board", lambda: (_ for _ in ()).throw(AssertionError("no regen")))

    assert ae.tick() is False

    assert logs == ["invalid engine state cursor (cursor_negative); refusing tick"]


def _tick_with_state(monkeypatch, tmp_path, st, *, ok):
    """Run one tick() against a shared ``st`` with every side-effect helper stubbed and run_job -> ``ok``.
    tick mutates ``st`` in place and save_state is a no-op, so the caller inspects ``st`` directly."""
    logs: list[str] = []
    monkeypatch.setattr(ae, "STOP", tmp_path / "autonomous_engine.stop")   # absent -> not paused
    monkeypatch.setattr(ae, "load_state", lambda: st)
    monkeypatch.setattr(ae, "run_job", lambda *_a, **_k: ok)
    monkeypatch.setattr(ae, "regen_board", lambda: None)
    monkeypatch.setattr(ae, "publish", lambda *_a, **_k: None)
    monkeypatch.setattr(ae, "update_plan", lambda *_a, **_k: None)
    monkeypatch.setattr(ae, "save_state", lambda _st: None)
    monkeypatch.setattr(ae, "log", logs.append)
    assert ae.tick() is True
    return st, logs


def test_tick_skips_job_after_max_consecutive_failures(tmp_path, monkeypatch):
    st = {
        "cursor": 1,
        "queue": [["done-model", 40], ["bad-model", 10000, "full"], ["next-model", 40]],
        "done": [],
        "job_fails": ae.MAX_JOB_FAILS - 1,           # the next failure trips the skip
    }
    st, logs = _tick_with_state(monkeypatch, tmp_path, st, ok=False)
    assert st["cursor"] == 2                          # advanced PAST the persistently-failing job
    assert "job_fails" not in st                      # counter reset after the skip
    assert len(st["skipped"]) == 1
    skipped = st["skipped"][0]
    assert (skipped["model"], skipped["n"], skipped["set"], skipped["fails"]) == \
        ("bad-model", 10000, "full", ae.MAX_JOB_FAILS)
    assert skipped["grader"] == "batched"
    assert isinstance(skipped["at"], str) and skipped["at"].endswith("Z")
    assert any("skipping past it" in m for m in logs)


def test_tick_retries_failing_job_below_threshold(tmp_path, monkeypatch):
    st = {
        "cursor": 1,
        "queue": [["done-model", 40], ["bad-model", 10000, "full"], ["next-model", 40]],
        "done": [],
    }
    st, _logs = _tick_with_state(monkeypatch, tmp_path, st, ok=False)
    assert st["cursor"] == 1                          # unchanged -> same job retries next tick
    assert st["job_fails"] == 1
    assert "skipped" not in st


def test_tick_required_full_perdim_job_is_never_skipped_after_hard_failures(tmp_path, monkeypatch):
    st = {
        "cursor": 0,
        "queue": [["gemma4:31b", 0, "full", "perdim"], ["gpt-oss:120b", 0, "full", "perdim"]],
        "done": [],
        "job_fails": ae.MAX_JOB_FAILS - 1,
    }
    st, logs = _tick_with_state(monkeypatch, tmp_path, st, ok=False)
    assert st["cursor"] == 0
    assert st["job_fails"] == ae.MAX_JOB_FAILS
    assert "skipped" not in st
    assert any("required jobs are never skipped" in message for message in logs)


def test_tick_incomplete_closure_retains_cursor_without_hard_failure_budget(tmp_path, monkeypatch):
    st = {
        "cursor": 0,
        "queue": [["gemma4:31b", 0, "full", "perdim"], ["gpt-oss:120b", 0, "full", "perdim"]],
        "done": [],
        "job_fails": 2,
    }
    st, logs = _tick_with_state(monkeypatch, tmp_path, st, ok=None)
    assert st["cursor"] == 0
    assert st["closure_retries"] == 1
    assert "job_fails" not in st
    assert "skipped" not in st
    assert any("retaining cursor for repair pass 1" in message for message in logs)


def test_required_closure_evidence_requires_exact_scope_hash_and_counts(tmp_path, monkeypatch):
    promptset = tmp_path / "full_promptset.json"
    promptset.write_text(
        json.dumps({"prompts": [{"id": "p1"}, {"id": "p2"}]}),
        encoding="utf-8",
    )
    monkeypatch.setattr(ae, "PROMPTS_FULL", promptset)
    model = "gemma4:31b"
    judges = list(dict.fromkeys(
        judge.strip() for judge in ae.JUDGES.split(",") if judge.strip()
    ))
    eligible_judges = [
        judge for judge in judges if ae.model_family(judge) != ae.model_family(model)
    ]
    response_count = 2 * len(ae.ACTIVE_ARMS)
    panel_count = response_count * len(eligible_judges)
    dimension_count = panel_count * ae.ACTIVE_COMPONENT_COUNT
    closure = {
        "schema": ae.COVERAGE_SCHEMA,
        "status": "complete",
        "phase": "closed",
        "complete": True,
        "models": [model],
        "judges": judges,
        "prompt_count": 2,
        "promptset_sha256": _sha(promptset),
        "rubric_version": ae.ACTIVE_RICH_HARNESS_RUBRIC_VERSION,
        "harness_version": ae.ACTIVE_RICH_HARNESS_HARNESS_VERSION,
        "grader": "perdim",
        "arms": list(ae.ACTIVE_ARMS),
        "expected": {
            "response_cells": response_count,
            "panel_cells": panel_count,
            "dimension_outputs": dimension_count,
        },
        "promptset_stable": True,
        "promptset_sha256_after": _sha(promptset),
        "response_cells": {
            "expected": response_count,
            "complete": response_count,
            "missing": 0,
        },
        "panel_cells": {
            "expected": panel_count,
            "complete": panel_count,
            "missing": 0,
        },
        "dimension_outputs": {
            "expected": dimension_count,
            "complete_in_valid_panel_cells": dimension_count,
            "missing_from_valid_panel_cells": 0,
            "dimensions_per_panel_cell": ae.ACTIVE_COMPONENT_COUNT,
        },
    }

    assert ae._required_closure_evidence(closure, model) == (True, "")

    for field, invalid, expected_issue in (
        ("models", ["wrong-model"], "model_scope_mismatch"),
        ("promptset_sha256_after", "0" * 64, "final_promptset_hash_mismatch"),
        ("prompt_count", 1, "prompt_count_mismatch"),
        ("phase", "coverage_audit", "phase_mismatch"),
    ):
        changed = json.loads(json.dumps(closure))
        changed[field] = invalid
        valid, reason = ae._required_closure_evidence(changed, model)
        assert valid is False
        assert expected_issue in reason


@pytest.mark.parametrize(
    "closure",
    [
        {"status": "missing", "complete": False},
        {"status": "unreadable", "complete": False, "error": "JSONDecodeError"},
        {
            "schema": ae.COVERAGE_SCHEMA,
            "status": "complete",
            "phase": "closed",
            "complete": True,
            "models": ["wrong-model"],
        },
    ],
    ids=("missing", "unreadable", "wrong-model"),
)
def test_tick_success_without_valid_required_closure_retains_cursor(
        tmp_path, monkeypatch, closure,
):
    promptset = tmp_path / "full_promptset.json"
    promptset.write_text(json.dumps({"prompts": [{"id": "p1"}]}), encoding="utf-8")
    monkeypatch.setattr(ae, "PROMPTS_FULL", promptset)
    st = {
        "cursor": 0,
        "queue": [["gemma4:31b", 0, "full", "perdim"]],
        "done": [],
        "job_fails": 2,
    }
    monkeypatch.setattr(ae, "_coverage_manifest_summary", lambda: closure)

    st, logs = _tick_with_state(monkeypatch, tmp_path, st, ok=True)

    assert st["cursor"] == 0
    assert st["done"] == []
    assert st["closure_retries"] == 1
    assert "job_fails" not in st
    assert "primary_flywheel_complete_at" not in st
    assert any("without valid exact closure evidence" in message for message in logs)


def test_primary_flywheel_requires_exact_closure_evidence_for_all_four_models(monkeypatch):
    monkeypatch.setattr(
        ae,
        "_required_closure_evidence",
        lambda closure, model: (
            closure.get("exact") is True and closure.get("models") == [model],
            "invalid" if closure.get("exact") is not True else "",
        ),
    )
    done = []
    for model in ae._SWEEP_MODELS:
        done.append({
            "model": model,
            "n": 0,
            "set": "full",
            "grader": "perdim",
            "closure": {"complete": True, "exact": True, "models": [model]},
        })
    assert ae._primary_flywheel_complete({"done": done}) is True

    without_last = {"done": done[:-1]}
    assert ae._primary_flywheel_complete(without_last) is False
    no_proof = {"done": [{**done[0], "closure": {"complete": True, "exact": False}}, *done[1:]]}
    assert ae._primary_flywheel_complete(no_proof) is False


def test_tick_resets_fail_counter_on_success(tmp_path, monkeypatch):
    st = {
        "cursor": 1,
        "queue": [["done-model", 40], ["good-model", 40], ["next-model", 40]],
        "done": [],
        "job_fails": 2,                               # a prior transient blip
    }
    st, _logs = _tick_with_state(monkeypatch, tmp_path, st, ok=True)
    assert st["cursor"] == 2                          # advanced on success
    assert "job_fails" not in st                      # counter cleared
    assert st["done"][-1]["model"] == "good-model"
    assert st["done"][-1]["grader"] == "batched"


def test_tick_records_and_publishes_perdim_mode(tmp_path, monkeypatch):
    state = {
        "cursor": 0,
        "queue": [["flagship", 0, "full", "perdim"]],
        "done": [],
    }
    calls = {"run": [], "publish": []}
    monkeypatch.setattr(ae, "STOP", tmp_path / "autonomous_engine.stop")
    monkeypatch.setattr(ae, "load_state", lambda: state)
    monkeypatch.setattr(ae, "run_job", lambda *args: calls["run"].append(args) or True)
    monkeypatch.setattr(ae, "regen_board", lambda: None)
    monkeypatch.setattr(ae, "update_plan", lambda *_args: None)
    monkeypatch.setattr(ae, "save_state", lambda _state: None)
    monkeypatch.setattr(ae, "publish", calls["publish"].append)
    monkeypatch.setattr(ae, "log", lambda _msg: None)
    closure = {"complete": True, "models": ["flagship"], "status": "complete"}
    monkeypatch.setattr(ae, "_coverage_manifest_summary", lambda: closure)
    monkeypatch.setattr(ae, "_required_closure_evidence", lambda proof, model: (True, ""))

    assert ae.tick() is True

    assert calls["run"] == [("flagship", 0, "full", "perdim")]
    assert state["done"] == [{
        "model": "flagship",
        "n": 0,
        "set": "full",
        "grader": "perdim",
        "at": state["done"][0]["at"],
        "closure": closure,
    }]
    assert calls["publish"] == ["flagship n=all full grader=perdim"]


def test_preflight_and_status_block_malformed_state_queue(tmp_path, monkeypatch):
    monkeypatch.setattr(ae, "STOP", tmp_path / "autonomous_engine.stop")
    monkeypatch.setattr(ae, "LOCK", tmp_path / "autonomous_engine.lock")
    monkeypatch.setattr(ae, "PROMPTS_FULL", tmp_path / "full_promptset.json")
    monkeypatch.setattr(ae, "DIMENSION_CANDIDATES", tmp_path / "dimension_candidates.jsonl")
    monkeypatch.setattr(ae, "_dimension_review_gate_status", lambda: {
        "status": "validated_zero_proposals",
        "active_rubric_promotion_ready": False,
        "validation": {"summary": {}},
    })
    monkeypatch.setattr(ae, "load_state", lambda: {
        "cursor": 0,
        "queue": [["", 1], ["must-not-select", 2]],
        "done": [],
    })

    report = ae.preflight_status(check_ollama=False)
    status = ae.status_payload()

    assert report["blockers"] == ["state_queue_invalid"]
    assert report["queue_state"] == {"valid": False, "error": "queue_entry_invalid", "entry_index": 0}
    assert report["current_job"] == {"model": None, "n": None, "set": None, "grader": None}
    assert status["queue_state"] == report["queue_state"]
    assert status["current_job"] == {
        "index": None, "model": None, "n": None, "set": None, "grader": None,
    }


def test_tick_refuses_malformed_state_queue_without_running_job(tmp_path, monkeypatch):
    logs = []
    monkeypatch.setattr(ae, "STOP", tmp_path / "autonomous_engine.stop")
    monkeypatch.setattr(ae, "load_state", lambda: {
        "cursor": 0,
        "queue": [["model", -1]],
        "done": [],
    })
    monkeypatch.setattr(ae, "log", logs.append)
    monkeypatch.setattr(ae, "run_job", lambda *_args, **_kwargs: (_ for _ in ()).throw(AssertionError("no job")))
    monkeypatch.setattr(ae, "regen_board", lambda: (_ for _ in ()).throw(AssertionError("no regen")))

    assert ae.tick() is False

    assert logs == ["invalid engine state queue (queue_entry_invalid); refusing tick"]


def test_preflight_and_status_block_malformed_dimension_candidates(tmp_path, monkeypatch):
    reports = tmp_path / "reports"
    reports.mkdir()
    prompts = reports / "benchmark" / "full_promptset.json"
    prompts.parent.mkdir()
    prompts.write_text(json.dumps({"prompts": [{"id": "p1"}, {"id": "p2"}]}), encoding="utf-8")
    candidates = tmp_path / "configs" / "duecare" / "benchmarks" / "research_spider" / "dimension_candidates.jsonl"
    candidates.parent.mkdir(parents=True)
    candidates.write_text('{"status": "candidate_needs_review_before_rubric_merge"\n', encoding="utf-8")
    packet = reports / "benchmark" / "research_spider_dimension_candidate_review_packet.json"
    packet.write_text(json.dumps({
        "_meta": {
            "source_artifact_sha256": _sha(candidates),
            "source_artifact_rows": 1,
        },
        "summary": {"dimension_candidate_rows": 1},
    }), encoding="utf-8")
    validation = reports / "benchmark" / "research_spider_dimension_candidate_review_validation.json"
    validation.write_text(json.dumps({
        "_meta": {
            "packet_source_artifact_sha256": _sha(candidates),
            "packet_source_artifact_rows": 1,
            "packet_artifact_sha256": _sha(packet),
        },
        "summary": {
            "ok": True,
            "dimension_review_rows": 1,
            "rows_accepted_for_rubric_proposal": 0,
            "rows_ready_claimed": 0,
            "root_issue_count": 0,
        },
    }), encoding="utf-8")
    monkeypatch.setattr(ae, "PROMPTS_FULL", prompts)
    monkeypatch.setattr(ae, "DIMENSION_CANDIDATES", candidates)
    monkeypatch.setattr(ae, "DIM_REVIEW_PACKET", packet)
    monkeypatch.setattr(ae, "DIM_REVIEW_VALIDATION", validation)
    monkeypatch.setattr(ae, "STOP", reports / "autonomous_engine.stop")
    monkeypatch.setattr(ae, "LOCK", reports / "autonomous_engine.lock")
    monkeypatch.setattr(ae, "load_state", lambda: {
        "started": "s",
        "updated": "u",
        "ticks": 1,
        "cursor": 0,
        "queue": [["m", 2, "full"]],
        "done": [],
    })

    report = ae.preflight_status(check_ollama=False)
    status = ae.status_payload()

    assert report["blockers"] == ["dimension_candidates_parse_error"]
    assert report["dimension_candidates"]["parse_errors"] == [
        {"field": "status", "error": report["dimension_candidates"]["status_counts"]["__error__"]},
        {"field": "group", "error": report["dimension_candidates"]["group_counts"]["__error__"]},
    ]
    assert report["dimension_candidates"]["review_gate"]["status"] == "validated_zero_proposals"
    assert status["candidate_dimension_scope"]["parse_errors"] == report["dimension_candidates"]["parse_errors"]
    assert status["candidate_dimension_scope"]["ready_for_mass_grading"] is False


def test_preflight_reports_pause_promptset_panel_and_ollama_blockers(tmp_path, monkeypatch):
    reports = tmp_path / "reports"
    promptset = reports / "benchmark" / "full_promptset.json"
    promptset.parent.mkdir(parents=True)
    promptset.write_text(json.dumps({"version": "test", "prompts": [{}, {}]}), encoding="utf-8")
    panel = reports / "rich_lift" / "panel.jsonl"
    panel.parent.mkdir(parents=True)
    panel.write_text('{"id":"a"}\n\n{"id":"b"}\n', encoding="utf-8")
    stop = reports / "autonomous_engine.stop"
    stop.write_text("worker@example.com local operator note", encoding="utf-8")
    dimensions = (
        tmp_path / "configs" / "duecare" / "benchmarks" / "research_spider" / "dimension_candidates.jsonl"
    )
    dimensions.parent.mkdir(parents=True)
    dimensions.write_text(
        json.dumps({
            "group": "case_response_skill",
            "name": "raw candidate name must not be copied",
            "status": "candidate_needs_review_before_rubric_merge",
        }) + "\n" +
        json.dumps({
            "group": "case_response_skill",
            "name": "second raw candidate name must not be copied",
            "status": "candidate_needs_review_before_rubric_merge",
        }) + "\n",
        encoding="utf-8",
    )
    gate_dir = reports / "benchmark"
    gate_dir.mkdir(parents=True, exist_ok=True)
    packet = gate_dir / "research_spider_dimension_candidate_review_packet.json"
    packet.write_text(json.dumps({
        "_meta": {
            "source_artifact_sha256": _sha(dimensions),
            "source_artifact_rows": 2,
        },
        "summary": {
            "dimension_candidate_rows": 2,
            "default_ready_for_rubric_promotion": 0,
            "policy": "long prose should not be copied into preflight",
        },
    }), encoding="utf-8")
    validation = gate_dir / "research_spider_dimension_candidate_review_validation.json"
    validation.write_text(json.dumps({
        "_meta": {
            "packet_source_artifact_sha256": _sha(dimensions),
            "packet_source_artifact_rows": 2,
            "packet_artifact_sha256": _sha(packet),
        },
        "summary": {
            "ok": True,
            "dimension_review_rows": 2,
            "rows_ready_claimed": 0,
            "rows_accepted_for_rubric_proposal": 0,
            "root_issue_count": 0,
            "policy": "long validation prose should not be copied into preflight",
        },
    }), encoding="utf-8")

    monkeypatch.setattr(ae, "ROOT", tmp_path)
    monkeypatch.setattr(ae, "STOP", stop)
    monkeypatch.setattr(ae, "LOCK", reports / "autonomous_engine.lock")
    monkeypatch.setattr(ae, "PROMPTS_FULL", promptset)
    monkeypatch.setattr(ae, "DIMENSION_CANDIDATES", dimensions)
    monkeypatch.setattr(ae, "DIM_REVIEW_PACKET", packet)
    monkeypatch.setattr(ae, "DIM_REVIEW_VALIDATION", validation)
    monkeypatch.setattr(ae, "load_state", lambda: {
        "started": "s",
        "updated": "u",
        "ticks": 1,
        "cursor": 0,
        "queue": [["gemma4:31b", 10000, "full"]],
        "done": [],
    })

    def fake_run(cmd, capture=False, timeout=None):
        assert cmd == ["ollama", "ps"]
        assert timeout == 8
        return _cp(cmd, returncode=1, stderr="Access is denied")

    monkeypatch.setattr(ae, "_run", fake_run)

    report = ae.preflight_status()

    assert report["ready"] is False
    assert report["blockers"] == ["stop_sentinel_present", "ollama_unavailable"]
    assert report["ignored_blockers"] == []
    assert report["paused"] is True
    assert report["stop_sentinel"] == "reports/autonomous_engine.stop"
    assert report["current_job"] == {
        "model": "gemma4:31b", "n": 10000, "set": "full", "grader": "batched",
    }
    assert report["full_promptset"]["prompt_count"] == 2
    assert report["full_promptset"]["error"] == ""
    assert report["active_loop_scope"] == {
        "runner": "rich_harness_lift.py",
        "candidate_dimension_sweep_active": False,
        "grader": "batched",
        "grader_path_isolated": False,
        "board_default_evidence": True,
        "rubric_version": "v1",
        "opt_in_rubric_versions_excluded": ["v2"],
        "rubric_version_mixing_allowed": False,
        "harness_version": "h1",
        "opt_in_harness_versions_excluded": ["h2"],
        "harness_version_mixing_allowed": False,
        "rubric_shape": "3 response arms x 5 calibrated components x configured judge panel",
        "calibrated_component_count": 5,
        "judge_calls_per_panel_cell": 1,
        "target_prompt_count": 2,
        "response_generation_cells": 6,
        "max_component_judge_cells": 18,
        "max_component_judge_calls": 18,
        "pairwise_enabled": True,
        "max_pairwise_judge_cells": 6,
        "configured_judges": 3,
    }
    assert report["panel"]["rows"] == 2
    assert report["panel"]["grader"] == "batched"
    assert report["dimension_candidates"]["rows"] == 2
    assert report["dimension_candidates"]["status_counts"] == {
        "candidate_needs_review_before_rubric_merge": 2,
    }
    assert report["dimension_candidates"]["group_counts"] == {"case_response_skill": 2}
    assert report["dimension_candidates"]["review_gate"]["status"] == "validated_zero_proposals"
    assert report["dimension_candidates"]["review_gate"]["active_rubric_promotion_ready"] is False
    assert report["dimension_candidates"]["review_gate"]["packet"]["summary"] == {
        "dimension_candidate_rows": 2,
        "default_ready_for_rubric_promotion": 0,
    }
    assert report["dimension_candidates"]["review_gate"]["validation"]["summary"] == {
        "ok": True,
        "dimension_review_rows": 2,
        "rows_ready_claimed": 0,
        "rows_accepted_for_rubric_proposal": 0,
        "root_issue_count": 0,
    }
    assert report["dimension_candidates"]["sweep_estimate"] == {
        "active_in_autonomous_engine": False,
        "ready_for_mass_grading": False,
        "row_status_ready_for_mass_grading": False,
        "review_gate_status": "validated_zero_proposals",
        "active_rubric_promotion_ready": False,
        "review_needed_count": 2,
        "approved_like_count": 0,
        "full_registry_prompt_dimension_cells": 4,
        "current_job_prompt_dimension_cells": 4,
        "promotion_gate": (
            "Run build_dimension_candidate_review_packet.py, fill curator review rows, then run "
            "validate_dimension_candidate_review_packet.py before any candidate dimension becomes active."
        ),
        "note": "Candidate dimensions require curator review before they become an active grading rubric.",
    }
    assert report["ollama"]["stderr_tail"] == "Access is denied"
    assert "worker@example.com" not in json.dumps(report)
    assert "raw candidate name" not in json.dumps(report)


def test_preflight_uses_isolated_perdim_panel_and_call_counts(tmp_path, monkeypatch):
    panel_dir = tmp_path / "reports" / "rich_lift"
    panel_dir.mkdir(parents=True)
    (panel_dir / "panel.jsonl").write_text('{"batched":1}\n', encoding="utf-8")
    (panel_dir / "panel_perdim.jsonl").write_text('{"perdim":1}\n{"perdim":2}\n', encoding="utf-8")
    monkeypatch.setattr(ae, "ROOT", tmp_path)
    monkeypatch.setattr(ae, "STOP", tmp_path / "reports" / "autonomous_engine.stop")
    monkeypatch.setattr(ae, "LOCK", tmp_path / "reports" / "autonomous_engine.lock")
    monkeypatch.setattr(ae, "PROMPTS_FULL", tmp_path / "reports" / "benchmark" / "full_promptset.json")
    monkeypatch.setattr(ae, "DIMENSION_CANDIDATES", tmp_path / "dimension_candidates.jsonl")
    monkeypatch.setattr(ae, "_full_prompt_count", lambda: (10, ""))
    monkeypatch.setattr(ae, "_dimension_review_gate_status", lambda: {
        "status": "validated_zero_proposals",
        "active_rubric_promotion_ready": False,
        "validation": {"summary": {}},
    })
    monkeypatch.setattr(ae, "load_state", lambda: {
        "cursor": 0,
        "queue": [["flagship", 0, "full", "perdim"]],
        "done": [],
    })

    report = ae.preflight_status(check_ollama=False)

    assert report["current_job"]["grader"] == "perdim"
    assert report["panel"]["path"] == "reports/rich_lift/panel_perdim.jsonl"
    assert report["panel"]["rows"] == 2
    assert report["panel"]["grader"] == "perdim"
    assert report["active_loop_scope"]["candidate_dimension_sweep_active"] is False
    assert report["active_loop_scope"]["grader_path_isolated"] is True
    assert report["active_loop_scope"]["board_default_evidence"] is False
    assert report["active_loop_scope"]["max_component_judge_cells"] == 90
    assert report["active_loop_scope"]["max_component_judge_calls"] == 450
    assert report["active_loop_scope"]["pairwise_enabled"] is False
    assert report["active_loop_scope"]["max_pairwise_judge_cells"] == 0


def test_candidate_dimension_mass_grading_readiness_requires_review_gate(tmp_path, monkeypatch):
    reports = tmp_path / "reports"
    promptset = reports / "benchmark" / "full_promptset.json"
    promptset.parent.mkdir(parents=True)
    promptset.write_text(json.dumps({"prompts": [{}, {}]}), encoding="utf-8")
    dimensions = tmp_path / "configs" / "duecare" / "benchmarks" / "research_spider" / "dimension_candidates.jsonl"
    dimensions.parent.mkdir(parents=True)
    dimensions.write_text(
        '{"status":"approved","group":"case_response_skill"}\n'
        '{"status":"approved","group":"case_response_skill"}\n',
        encoding="utf-8",
    )
    packet = reports / "benchmark" / "research_spider_dimension_candidate_review_packet.json"
    packet.write_text(json.dumps({
        "_meta": {
            "source_artifact_sha256": _sha(dimensions),
            "source_artifact_rows": 2,
        },
        "summary": {"dimension_candidate_rows": 2},
    }), encoding="utf-8")
    validation = reports / "benchmark" / "research_spider_dimension_candidate_review_validation.json"
    validation.write_text(json.dumps({
        "_meta": {
            "packet_source_artifact_sha256": _sha(dimensions),
            "packet_source_artifact_rows": 2,
            "packet_artifact_sha256": _sha(packet),
        },
        "summary": {
            "ok": True,
            "dimension_review_rows": 2,
            "rows_ready_claimed": 0,
            "rows_accepted_for_rubric_proposal": 0,
            "root_issue_count": 0,
        },
    }), encoding="utf-8")
    monkeypatch.setattr(ae, "PROMPTS_FULL", promptset)
    monkeypatch.setattr(ae, "DIMENSION_CANDIDATES", dimensions)
    monkeypatch.setattr(ae, "DIM_REVIEW_PACKET", packet)
    monkeypatch.setattr(ae, "DIM_REVIEW_VALIDATION", validation)
    monkeypatch.setattr(ae, "STOP", reports / "autonomous_engine.stop")
    monkeypatch.setattr(ae, "LOCK", reports / "autonomous_engine.lock")
    monkeypatch.setattr(ae, "load_state", lambda: {
        "cursor": 0,
        "queue": [["m", 2, "full"]],
        "done": [],
    })

    report = ae.preflight_status(check_ollama=False)
    status = ae.status_payload()

    sweep = report["dimension_candidates"]["sweep_estimate"]
    assert sweep["row_status_ready_for_mass_grading"] is True
    assert sweep["review_gate_status"] == "validated_zero_proposals"
    assert sweep["active_rubric_promotion_ready"] is False
    assert sweep["ready_for_mass_grading"] is False
    assert status["candidate_dimension_scope"]["row_status_ready_for_mass_grading"] is True
    assert status["candidate_dimension_scope"]["ready_for_mass_grading"] is False


def test_preflight_blocks_malformed_dimension_review_validation_summary(tmp_path, monkeypatch):
    reports = tmp_path / "reports"
    promptset = reports / "benchmark" / "full_promptset.json"
    promptset.parent.mkdir(parents=True)
    promptset.write_text(json.dumps({"prompts": [{"id": "p1"}]}), encoding="utf-8")
    candidates, packet, validation = _write_review_gate_files(tmp_path, source_rows=1, ready=0, accepted=0)
    validation_doc = json.loads(validation.read_text(encoding="utf-8"))
    del validation_doc["summary"]["root_issue_count"]
    validation.write_text(json.dumps(validation_doc), encoding="utf-8")
    monkeypatch.setattr(ae, "PROMPTS_FULL", promptset)
    monkeypatch.setattr(ae, "DIMENSION_CANDIDATES", candidates)
    monkeypatch.setattr(ae, "DIM_REVIEW_PACKET", packet)
    monkeypatch.setattr(ae, "DIM_REVIEW_VALIDATION", validation)
    monkeypatch.setattr(ae, "STOP", reports / "autonomous_engine.stop")
    monkeypatch.setattr(ae, "LOCK", reports / "autonomous_engine.lock")
    monkeypatch.setattr(ae, "load_state", lambda: {
        "cursor": 0,
        "queue": [["m", 1, "full"]],
        "done": [],
    })

    report = ae.preflight_status(check_ollama=False)

    gate = report["dimension_candidates"]["review_gate"]
    assert gate["status"] == "validation_summary_malformed"
    assert gate["active_rubric_promotion_ready"] is False
    assert gate["validation_summary_issues"] == ["root_issue_count_missing_or_not_integer"]
    assert report["ready"] is False
    assert "dimension_review_validation_summary_malformed" in report["blockers"]
    status = ae.status_payload()
    assert status["candidate_dimension_scope"]["review_gate_validation_summary_issues"] == [
        "root_issue_count_missing_or_not_integer",
    ]


def test_preflight_blocks_dimension_review_validation_row_count_drift(tmp_path, monkeypatch):
    reports = tmp_path / "reports"
    promptset = reports / "benchmark" / "full_promptset.json"
    promptset.parent.mkdir(parents=True)
    promptset.write_text(json.dumps({"prompts": [{"id": "p1"}]}), encoding="utf-8")
    candidates, packet, validation = _write_review_gate_files(tmp_path, source_rows=2, ready=0, accepted=0)
    validation_doc = json.loads(validation.read_text(encoding="utf-8"))
    validation_doc["summary"]["dimension_review_rows"] = 1
    validation.write_text(json.dumps(validation_doc), encoding="utf-8")
    monkeypatch.setattr(ae, "PROMPTS_FULL", promptset)
    monkeypatch.setattr(ae, "DIMENSION_CANDIDATES", candidates)
    monkeypatch.setattr(ae, "DIM_REVIEW_PACKET", packet)
    monkeypatch.setattr(ae, "DIM_REVIEW_VALIDATION", validation)
    monkeypatch.setattr(ae, "STOP", reports / "autonomous_engine.stop")
    monkeypatch.setattr(ae, "LOCK", reports / "autonomous_engine.lock")
    monkeypatch.setattr(ae, "load_state", lambda: {
        "cursor": 0,
        "queue": [["m", 1, "full"]],
        "done": [],
    })

    report = ae.preflight_status(check_ollama=False)

    gate = report["dimension_candidates"]["review_gate"]
    assert gate["status"] == "validation_summary_malformed"
    assert gate["validation_summary_issues"] == [
        "dimension_review_rows_must_match_packet_source_artifact_rows",
    ]
    assert report["ready"] is False
    assert "dimension_review_validation_summary_malformed" in report["blockers"]


def test_preflight_blocks_stale_dimension_review_validation_source_row_metadata(tmp_path, monkeypatch):
    reports = tmp_path / "reports"
    promptset = reports / "benchmark" / "full_promptset.json"
    promptset.parent.mkdir(parents=True)
    promptset.write_text(json.dumps({"prompts": [{"id": "p1"}]}), encoding="utf-8")
    candidates, packet, validation = _write_review_gate_files(tmp_path, source_rows=2, ready=0, accepted=0)
    validation_doc = json.loads(validation.read_text(encoding="utf-8"))
    validation_doc["_meta"]["packet_source_artifact_rows"] = 1
    validation.write_text(json.dumps(validation_doc), encoding="utf-8")
    monkeypatch.setattr(ae, "PROMPTS_FULL", promptset)
    monkeypatch.setattr(ae, "DIMENSION_CANDIDATES", candidates)
    monkeypatch.setattr(ae, "DIM_REVIEW_PACKET", packet)
    monkeypatch.setattr(ae, "DIM_REVIEW_VALIDATION", validation)
    monkeypatch.setattr(ae, "STOP", reports / "autonomous_engine.stop")
    monkeypatch.setattr(ae, "LOCK", reports / "autonomous_engine.lock")
    monkeypatch.setattr(ae, "load_state", lambda: {
        "cursor": 0,
        "queue": [["m", 1, "full"]],
        "done": [],
    })

    report = ae.preflight_status(check_ollama=False)

    gate = report["dimension_candidates"]["review_gate"]
    assert gate["status"] == "validation_stale_for_review_packet"
    assert gate["active_rubric_promotion_ready"] is False
    assert report["ready"] is False
    assert "dimension_review_validation_stale" in report["blockers"]


def test_preflight_marks_dimension_review_packet_stale_when_source_changes(tmp_path, monkeypatch):
    reports = tmp_path / "reports"
    candidates = tmp_path / "configs" / "duecare" / "benchmarks" / "research_spider" / "dimension_candidates.jsonl"
    candidates.parent.mkdir(parents=True)
    candidates.write_text('{"status":"candidate_needs_review_before_rubric_merge"}\n', encoding="utf-8")
    packet = reports / "benchmark" / "research_spider_dimension_candidate_review_packet.json"
    packet.parent.mkdir(parents=True)
    packet.write_text(json.dumps({
        "_meta": {
            "source_artifact_sha256": "stale",
            "source_artifact_rows": 1,
        },
        "summary": {"dimension_candidate_rows": 1},
    }), encoding="utf-8")
    validation = reports / "benchmark" / "research_spider_dimension_candidate_review_validation.json"
    validation.write_text(json.dumps({
        "_meta": {
            "packet_source_artifact_sha256": "stale",
            "packet_source_artifact_rows": 1,
            "packet_artifact_sha256": _sha(packet),
        },
        "summary": {
            "ok": True,
            "dimension_review_rows": 1,
            "rows_ready_claimed": 0,
            "rows_accepted_for_rubric_proposal": 0,
            "root_issue_count": 0,
        },
    }), encoding="utf-8")

    monkeypatch.setattr(ae, "ROOT", tmp_path)
    monkeypatch.setattr(ae, "STOP", reports / "autonomous_engine.stop")
    monkeypatch.setattr(ae, "LOCK", reports / "autonomous_engine.lock")
    monkeypatch.setattr(ae, "PROMPTS_FULL", reports / "benchmark" / "full_promptset.json")
    monkeypatch.setattr(ae, "DIMENSION_CANDIDATES", candidates)
    monkeypatch.setattr(ae, "DIM_REVIEW_PACKET", packet)
    monkeypatch.setattr(ae, "DIM_REVIEW_VALIDATION", validation)
    monkeypatch.setattr(ae, "load_state", lambda: {
        "cursor": 0,
        "queue": [["gemma4:31b", 40]],
        "done": [],
    })

    report = ae.preflight_status(check_ollama=False)

    gate = report["dimension_candidates"]["review_gate"]
    assert gate["status"] == "review_packet_stale_for_dimension_candidates"
    assert gate["active_rubric_promotion_ready"] is False
    assert gate["dimension_candidates_sha256"] == _sha(candidates)
    assert report["ready"] is False
    assert "dimension_review_packet_stale" in report["blockers"]


def test_preflight_blocks_missing_dimension_review_validation(tmp_path, monkeypatch):
    reports = tmp_path / "reports"
    candidates = tmp_path / "configs" / "duecare" / "benchmarks" / "research_spider" / "dimension_candidates.jsonl"
    candidates.parent.mkdir(parents=True)
    candidates.write_text('{"status":"candidate_needs_review_before_rubric_merge"}\n', encoding="utf-8")
    packet = reports / "benchmark" / "research_spider_dimension_candidate_review_packet.json"
    packet.parent.mkdir(parents=True)
    packet.write_text(json.dumps({
        "_meta": {
            "source_artifact_sha256": _sha(candidates),
            "source_artifact_rows": 1,
        },
        "summary": {"dimension_candidate_rows": 1},
    }), encoding="utf-8")

    monkeypatch.setattr(ae, "ROOT", tmp_path)
    monkeypatch.setattr(ae, "STOP", reports / "autonomous_engine.stop")
    monkeypatch.setattr(ae, "LOCK", reports / "autonomous_engine.lock")
    monkeypatch.setattr(ae, "PROMPTS_FULL", reports / "benchmark" / "full_promptset.json")
    monkeypatch.setattr(ae, "DIMENSION_CANDIDATES", candidates)
    monkeypatch.setattr(ae, "DIM_REVIEW_PACKET", packet)
    monkeypatch.setattr(
        ae,
        "DIM_REVIEW_VALIDATION",
        reports / "benchmark" / "research_spider_dimension_candidate_review_validation.json",
    )
    monkeypatch.setattr(ae, "load_state", lambda: {
        "cursor": 0,
        "queue": [["gemma4:31b", 40]],
        "done": [],
    })

    report = ae.preflight_status(check_ollama=False)

    assert report["ready"] is False
    assert report["blockers"] == ["dimension_review_validation_missing"]
    assert report["ignored_blockers"] == []
    assert report["dimension_candidates"]["review_gate"]["status"] == "validation_missing"


def test_preflight_blocks_unreadable_dimension_review_packet(tmp_path, monkeypatch):
    reports = tmp_path / "reports"
    reports.mkdir()
    prompts = reports / "benchmark" / "full_promptset.json"
    prompts.parent.mkdir()
    prompts.write_text(json.dumps({"prompts": [{"id": "p1"}]}), encoding="utf-8")
    candidates = tmp_path / "configs" / "duecare" / "benchmarks" / "research_spider" / "dimension_candidates.jsonl"
    candidates.parent.mkdir(parents=True)
    candidates.write_text('{"status":"candidate_needs_review_before_rubric_merge"}\n', encoding="utf-8")
    packet = reports / "benchmark" / "research_spider_dimension_candidate_review_packet.json"
    packet.write_text("{not json", encoding="utf-8")
    validation = reports / "benchmark" / "research_spider_dimension_candidate_review_validation.json"
    validation.write_text(json.dumps({"_meta": {}, "summary": {"ok": True}}), encoding="utf-8")
    monkeypatch.setattr(ae, "PROMPTS_FULL", prompts)
    monkeypatch.setattr(ae, "DIMENSION_CANDIDATES", candidates)
    monkeypatch.setattr(ae, "DIM_REVIEW_PACKET", packet)
    monkeypatch.setattr(ae, "DIM_REVIEW_VALIDATION", validation)
    monkeypatch.setattr(ae, "STOP", reports / "autonomous_engine.stop")
    monkeypatch.setattr(ae, "LOCK", reports / "autonomous_engine.lock")
    monkeypatch.setattr(ae, "load_state", lambda: {
        "cursor": 0,
        "queue": [["m", 1, "full"]],
        "done": [],
    })

    report = ae.preflight_status(check_ollama=False)

    assert report["blockers"] == ["dimension_review_packet_unreadable"]
    gate = report["dimension_candidates"]["review_gate"]
    assert gate["status"] == "review_packet_unreadable"
    assert "JSONDecodeError" in gate["packet"]["summary_error"]


def test_preflight_blocks_unreadable_dimension_review_validation(tmp_path, monkeypatch):
    reports = tmp_path / "reports"
    reports.mkdir()
    prompts = reports / "benchmark" / "full_promptset.json"
    prompts.parent.mkdir()
    prompts.write_text(json.dumps({"prompts": [{"id": "p1"}]}), encoding="utf-8")
    candidates = tmp_path / "configs" / "duecare" / "benchmarks" / "research_spider" / "dimension_candidates.jsonl"
    candidates.parent.mkdir(parents=True)
    candidates.write_text('{"status":"candidate_needs_review_before_rubric_merge"}\n', encoding="utf-8")
    packet = reports / "benchmark" / "research_spider_dimension_candidate_review_packet.json"
    packet.write_text(json.dumps({
        "_meta": {"source_artifact_sha256": _sha(candidates)},
        "summary": {"dimension_candidate_rows": 1},
    }), encoding="utf-8")
    validation = reports / "benchmark" / "research_spider_dimension_candidate_review_validation.json"
    validation.write_text("{not json", encoding="utf-8")
    monkeypatch.setattr(ae, "PROMPTS_FULL", prompts)
    monkeypatch.setattr(ae, "DIMENSION_CANDIDATES", candidates)
    monkeypatch.setattr(ae, "DIM_REVIEW_PACKET", packet)
    monkeypatch.setattr(ae, "DIM_REVIEW_VALIDATION", validation)
    monkeypatch.setattr(ae, "STOP", reports / "autonomous_engine.stop")
    monkeypatch.setattr(ae, "LOCK", reports / "autonomous_engine.lock")
    monkeypatch.setattr(ae, "load_state", lambda: {
        "cursor": 0,
        "queue": [["m", 1, "full"]],
        "done": [],
    })

    report = ae.preflight_status(check_ollama=False)

    assert report["blockers"] == ["dimension_review_validation_unreadable"]
    gate = report["dimension_candidates"]["review_gate"]
    assert gate["status"] == "validation_unreadable"
    assert "JSONDecodeError" in gate["validation"]["summary_error"]


def test_preflight_can_ignore_stop_sentinel_for_wrapper_launch(tmp_path, monkeypatch):
    reports = tmp_path / "reports"
    stop = reports / "autonomous_engine.stop"
    stop.parent.mkdir(parents=True)
    stop.write_text("", encoding="utf-8")
    candidates, packet, validation = _write_review_gate_files(tmp_path, source_rows=1, ready=0, accepted=0)
    promptset = reports / "benchmark" / "full_promptset.json"
    promptset.parent.mkdir(parents=True)
    promptset.write_text(json.dumps({"prompts": [{}]}), encoding="utf-8")

    monkeypatch.setattr(ae, "ROOT", tmp_path)
    monkeypatch.setattr(ae, "STOP", stop)
    monkeypatch.setattr(ae, "LOCK", reports / "autonomous_engine.lock")
    monkeypatch.setattr(ae, "PROMPTS_FULL", promptset)
    monkeypatch.setattr(ae, "DIMENSION_CANDIDATES", candidates)
    monkeypatch.setattr(ae, "DIM_REVIEW_PACKET", packet)
    monkeypatch.setattr(ae, "DIM_REVIEW_VALIDATION", validation)
    monkeypatch.setattr(ae, "load_state", lambda: {
        "cursor": 0,
        "queue": [["gemma4:31b", 1, "full"]],
        "done": [],
    })

    report = ae.preflight_status(check_ollama=False, ignore_stop_sentinel=True)

    assert report["ready"] is True
    assert report["blockers"] == []
    assert report["ignored_blockers"] == ["stop_sentinel_present"]
    assert report["paused"] is True
    assert report["stop_sentinel"] == "reports/autonomous_engine.stop"


def test_preflight_reports_ollama_timeout_as_blocker(tmp_path, monkeypatch):
    reports = tmp_path / "reports"
    candidates, packet, validation = _write_review_gate_files(tmp_path, source_rows=1, ready=0, accepted=0)
    monkeypatch.setattr(ae, "ROOT", tmp_path)
    monkeypatch.setattr(ae, "STOP", reports / "autonomous_engine.stop")
    monkeypatch.setattr(ae, "LOCK", reports / "autonomous_engine.lock")
    monkeypatch.setattr(ae, "PROMPTS_FULL", reports / "benchmark" / "full_promptset.json")
    monkeypatch.setattr(ae, "DIMENSION_CANDIDATES", candidates)
    monkeypatch.setattr(ae, "DIM_REVIEW_PACKET", packet)
    monkeypatch.setattr(ae, "DIM_REVIEW_VALIDATION", validation)
    monkeypatch.setattr(ae, "load_state", lambda: {
        "cursor": 0,
        "queue": [["gemma4:31b", 1000]],
        "done": [],
    })

    def fake_run(cmd, capture=False, timeout=None):
        assert cmd == ["ollama", "ps"]
        assert timeout == 8
        raise subprocess.TimeoutExpired(cmd, timeout)

    monkeypatch.setattr(ae, "_run", fake_run)

    report = ae.preflight_status()

    assert report["ready"] is False
    assert report["blockers"] == ["ollama_unavailable"]
    assert report["ollama"]["returncode"] is None
    assert report["ollama"]["error"].startswith("TimeoutExpired:")


def test_ollama_status_redacts_user_path_and_classifies_log_permission_failure(monkeypatch):
    def fake_run(cmd, capture=False, timeout=None):
        assert cmd == ["ollama", "ps"]
        assert timeout == 8
        return _cp(
            cmd,
            returncode=1,
            stderr=(
                r"ERROR failed to create server log open "
                r"C:\Users\Taylor\AppData\Local\Ollama\app.log: Access is denied. "
                r"remove C:\\Users\\Taylor\\AppData\\Local\\Ollama\\app-1.log: Access is denied."
            ),
        )

    monkeypatch.setattr(ae, "_run", fake_run)

    report = ae._ollama_status()

    assert report["ok"] is False
    assert "Taylor" not in report["stderr_tail"]
    assert "%USERPROFILE%\\AppData\\Local\\Ollama\\app.log" in report["stderr_tail"]
    assert "%USERPROFILE%\\\\AppData\\\\Local\\\\Ollama\\\\app-1.log" in report["stderr_tail"]
    assert report["diagnosis"]["code"] == "ollama_log_access_denied"


def test_preflight_blocks_missing_full_promptset_without_ollama_check(tmp_path, monkeypatch):
    reports = tmp_path / "reports"
    candidates, packet, validation = _write_review_gate_files(tmp_path, source_rows=1, ready=0, accepted=0)
    monkeypatch.setattr(ae, "ROOT", tmp_path)
    monkeypatch.setattr(ae, "STOP", reports / "autonomous_engine.stop")
    monkeypatch.setattr(ae, "LOCK", reports / "autonomous_engine.lock")
    monkeypatch.setattr(ae, "PROMPTS_FULL", reports / "benchmark" / "full_promptset.json")
    monkeypatch.setattr(ae, "DIMENSION_CANDIDATES", candidates)
    monkeypatch.setattr(ae, "DIM_REVIEW_PACKET", packet)
    monkeypatch.setattr(ae, "DIM_REVIEW_VALIDATION", validation)
    monkeypatch.setattr(ae, "load_state", lambda: {
        "cursor": 0,
        "queue": [["gemma4:31b", 10000, "full"]],
        "done": [],
    })

    report = ae.preflight_status(check_ollama=False)

    assert report["ready"] is False
    assert report["blockers"] == ["full_promptset_unavailable"]
    assert report["readiness_scope"] == "state_only"
    assert report["launch_ready_requires_ollama_check"] is True
    assert report["full_promptset"]["prompt_count"] is None
    assert report["full_promptset"]["error"] == "missing"
    assert report["ollama"] == {"checked": False, "ok": None}


def test_main_preflight_returns_nonzero_when_blocked_without_lock_or_tick(tmp_path, monkeypatch, capsys):
    preflight_report = tmp_path / "autonomous_engine_preflight.json"
    monkeypatch.setattr(sys, "argv", ["autonomous_engine.py", "--preflight"])
    monkeypatch.setattr(ae, "PREFLIGHT_REPORT", preflight_report)
    monkeypatch.setattr(ae, "now", lambda: "2026-06-30T00:00:00Z")
    monkeypatch.setattr(ae, "preflight_status", lambda check_ollama=True, ignore_stop_sentinel=False: {
        "ready": False,
        "blockers": ["stop_sentinel_present"],
        "ignored_blockers": [],
    })
    monkeypatch.setattr(ae, "acquire_lock", lambda: (_ for _ in ()).throw(AssertionError("no lock")))
    monkeypatch.setattr(ae, "tick", lambda: (_ for _ in ()).throw(AssertionError("no tick")))

    assert ae.main() == 2

    assert json.loads(capsys.readouterr().out) == {
        "ready": False,
        "blockers": ["stop_sentinel_present"],
        "ignored_blockers": [],
    }
    persisted = json.loads(preflight_report.read_text(encoding="utf-8"))
    assert persisted["_meta"]["mode"] == "manual_preflight"
    assert persisted["_meta"]["schema_version"] == "autonomous_engine_preflight.v1"
    assert persisted["blockers"] == ["stop_sentinel_present"]
    assert persisted["ignored_blockers"] == []


def test_main_preflight_can_skip_ollama_check(tmp_path, monkeypatch, capsys):
    calls = []
    preflight_report = tmp_path / "autonomous_engine_preflight.json"
    monkeypatch.setattr(sys, "argv", ["autonomous_engine.py", "--preflight", "--no-ollama-check"])
    monkeypatch.setattr(ae, "PREFLIGHT_REPORT", preflight_report)
    monkeypatch.setattr(ae, "now", lambda: "2026-06-30T00:00:00Z")

    def fake_preflight(*, check_ollama=True, ignore_stop_sentinel=False):
        calls.append(check_ollama)
        return {
            "ready": True,
            "readiness_scope": "state_only",
            "launch_ready_requires_ollama_check": True,
            "blockers": [],
            "ignored_blockers": [],
        }

    monkeypatch.setattr(ae, "preflight_status", fake_preflight)

    assert ae.main() == 3
    assert calls == [False]
    assert json.loads(capsys.readouterr().out) == {
        "ready": True,
        "readiness_scope": "state_only",
        "launch_ready_requires_ollama_check": True,
        "blockers": [],
        "ignored_blockers": [],
    }
    persisted = json.loads(preflight_report.read_text(encoding="utf-8"))
    assert persisted["_meta"]["mode"] == "manual_preflight"
    assert persisted["ready"] is True
    assert persisted["readiness_scope"] == "state_only"
    assert persisted["launch_ready_requires_ollama_check"] is True


def test_main_startup_preflight_blocks_normal_run_before_lock_or_tick(tmp_path, monkeypatch, capsys):
    logs = []
    preflight_report = tmp_path / "autonomous_engine_preflight.json"
    monkeypatch.setattr(sys, "argv", ["autonomous_engine.py", "--once"])
    monkeypatch.setattr(ae, "PREFLIGHT_REPORT", preflight_report)
    monkeypatch.setattr(ae, "now", lambda: "2026-06-30T00:00:00Z")
    monkeypatch.setattr(ae, "log", logs.append)
    monkeypatch.setattr(ae, "preflight_status", lambda check_ollama=True, ignore_stop_sentinel=False: {
        "ready": False,
        "blockers": ["dimension_review_packet_stale"],
        "ignored_blockers": [],
        "ollama": {"diagnosis": {"code": "ollama_log_access_denied"}},
    })
    monkeypatch.setattr(ae, "acquire_lock", lambda: (_ for _ in ()).throw(AssertionError("no lock")))
    monkeypatch.setattr(ae, "tick", lambda: (_ for _ in ()).throw(AssertionError("no tick")))

    assert ae.main() == 2

    assert json.loads(capsys.readouterr().out) == {
        "ready": False,
        "blockers": ["dimension_review_packet_stale"],
        "ignored_blockers": [],
        "ollama": {"diagnosis": {"code": "ollama_log_access_denied"}},
    }
    assert "startup preflight blocked launch: dimension_review_packet_stale" in logs
    assert "startup preflight ollama diagnosis: ollama_log_access_denied" in logs
    persisted = json.loads(preflight_report.read_text(encoding="utf-8"))
    assert persisted["_meta"]["mode"] == "startup_gate"
    assert persisted["blockers"] == ["dimension_review_packet_stale"]


def test_main_startup_execution_refuses_no_ollama_check_before_lock_or_tick(monkeypatch, capsys):
    monkeypatch.setattr(sys, "argv", ["autonomous_engine.py", "--once", "--no-ollama-check"])
    monkeypatch.setattr(
        ae,
        "preflight_status",
        lambda check_ollama=True, ignore_stop_sentinel=False: (
            _ for _ in ()
        ).throw(AssertionError("no startup preflight")),
    )
    monkeypatch.setattr(ae, "acquire_lock", lambda: (_ for _ in ()).throw(AssertionError("no lock")))
    monkeypatch.setattr(ae, "tick", lambda: (_ for _ in ()).throw(AssertionError("no tick")))

    assert ae.main() == 2

    captured = capsys.readouterr()
    assert captured.out == ""
    assert "--no-ollama-check is diagnostic-only for --preflight" in captured.err


def test_main_skip_startup_preflight_allows_once_tick(monkeypatch):
    calls = []
    monkeypatch.setattr(
        sys,
        "argv",
        ["autonomous_engine.py", "--once", "--no-ollama-check", "--skip-startup-preflight"],
    )
    monkeypatch.setattr(
        ae,
        "preflight_status",
        lambda check_ollama=True, ignore_stop_sentinel=False: (
            _ for _ in ()
        ).throw(AssertionError("no startup preflight")),
    )
    monkeypatch.setattr(ae, "acquire_lock", lambda: calls.append("lock") or True)
    monkeypatch.setattr(ae, "release_lock", lambda: calls.append("release"))
    monkeypatch.setattr(ae, "tick", lambda: calls.append("tick") or True)
    monkeypatch.setattr(ae, "log", lambda msg: calls.append(("log", msg)))

    assert ae.main() == 0

    assert calls == [
        "lock",
        ("log", f"autonomous_engine START pid={ae.os.getpid()} once=True"),
        "tick",
        ("log", "autonomous_engine EXIT"),
        "release",
    ]


def test_main_refresh_plan_does_not_acquire_lock_or_tick(monkeypatch, capsys):
    calls = []

    monkeypatch.setattr(sys, "argv", ["autonomous_engine.py", "--refresh-plan"])
    monkeypatch.setattr(ae, "load_state", lambda: {"queue": [["m", 1]], "cursor": 0})
    monkeypatch.setattr(ae, "update_plan", lambda st, current: calls.append((st, current)))
    monkeypatch.setattr(ae, "acquire_lock", lambda: (_ for _ in ()).throw(AssertionError("no lock")))
    monkeypatch.setattr(ae, "tick", lambda: (_ for _ in ()).throw(AssertionError("no tick")))

    assert ae.main() == 0

    assert calls == [({"queue": [["m", 1]], "cursor": 0}, ["m", 1])]
    assert "refreshed docs" in capsys.readouterr().out


def test_powershell_launcher_exposes_skip_startup_preflight():
    text = (_ROOT / "scripts" / "autonomous_engine.ps1").read_text(encoding="utf-8")

    assert "[switch]$SkipStartupPreflight" in text
    assert "[switch]$IgnoreStopSentinel" in text
    assert "[switch]$WatchdogRun" in text
    assert "[switch]$Restart" in text
    assert "--skip-startup-preflight" in text
    assert "--ignore-stop-sentinel" in text
    assert "function Set-EngineExitCode" in text
    assert "function Test-LaunchedAsProcessFile" in text
    assert "function Get-VerifiedEngineProcess" in text
    assert "Get-CimInstance -ClassName Win32_Process" in text
    assert "does not own this repository's autonomous_engine.py" in text
    assert "& taskkill /PID $enginePid /T /F" in text
    assert text.index("Get-VerifiedEngineProcess -ProcessId") < text.index("& taskkill /PID")
    assert "[Environment]::GetCommandLineArgs()" in text
    assert "$host.SetShouldExit($Code)" in text
    assert "exit $Code" not in text
    assert "function Invoke-EnginePreflight" in text
    assert "$script:EnginePreflightExitCode = $LASTEXITCODE" in text
    assert "Set-EngineExitCode $script:EnginePreflightExitCode" in text
    assert "Set-EngineExitCode $LASTEXITCODE" in text
    assert "Set-EngineExitCode 2" in text
    assert "Set-EngineExitCode $runPreflightCode" in text
    assert "$runPreflightCode = $script:EnginePreflightExitCode" in text
    assert "Invoke-EnginePreflight -SkipOllama:$NoOllamaCheck -IgnoreStopSentinel:$IgnoreStopSentinel" in text
    assert "Invoke-EnginePreflight -SkipOllama:$NoOllamaCheck -IgnoreStopSentinel:$Run" in text
    assert "-NoOllamaCheck is state-only for -Preflight" in text
    assert "($Run -or $Once -or $WatchdogRun) -and $NoOllamaCheck -and -not $SkipStartupPreflight" in text
    assert "if ($NoOllamaCheck) { $engineArgs += '--no-ollama-check' }" in text
    assert "Autonomous engine not launched; preflight blocked start" in text
    assert "pause sentinel still present: reports/autonomous_engine.stop" in text
    assert "Start-Process" in text


def test_powershell_register_uses_pause_preserving_watchdog_mode():
    text = (_ROOT / "scripts" / "autonomous_engine.ps1").read_text(encoding="utf-8")
    register_block = text.split("if ($Register) {", 1)[1].split("if ($Run -or $WatchdogRun) {", 1)[0]
    launch_block = text.split("if ($Run -or $WatchdogRun) {", 1)[1]

    assert "Remove-Item $stopFile" not in register_block
    assert '-WatchdogRun' in register_block
    assert '-Run"' not in register_block
    assert "Pause sentinel is still present" in register_block
    assert "explicitly run -Run" in register_block
    assert "($Run -or $Once -or $WatchdogRun) -and $NoOllamaCheck -and -not $SkipStartupPreflight" in text
    assert "Invoke-EnginePreflight -SkipOllama:$NoOllamaCheck -IgnoreStopSentinel:$Run" in launch_block
    assert "if ($Run) { Remove-Item $stopFile -ErrorAction SilentlyContinue }" in launch_block
