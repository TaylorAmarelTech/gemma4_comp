#!/usr/bin/env python3
"""DueCare autonomous benchmark engine -- a durable, self-contained loop.

Runs INDEPENDENTLY of Claude Code (which pauses between turns and cannot carry a
multi-day loop). It owns the benchmark: works a queue of (model, target_n) jobs
through ``rich_harness_lift.py``, regenerates the leaderboard, and commits+pushes
the BOARD ONLY (data, never code) so the public benchmark fills in on its own clock.

Durable + resumable + safe:
  * shared memory = ``reports/rich_lift/panel.jsonl`` (resumable grading) plus
    ``reports/autonomous_engine_state.json`` (queue cursor / done list).
  * single-owner lock (``reports/autonomous_engine.lock``) so it never races itself.
  * graceful stop: create ``reports/autonomous_engine.stop`` (checked each tick).
  * auto-commits ONLY the regenerated board + this plan doc; never code.

    python scripts/autonomous_engine.py            # run the loop (foreground/detached)
    python scripts/autonomous_engine.py --once      # one tick then exit (Task Scheduler)
    python scripts/autonomous_engine.py --status     # print state and exit
    python scripts/autonomous_engine.py --preflight  # print launch blockers/readiness and exit
    python scripts/autonomous_engine.py --skip-startup-preflight  # emergency override only
    type nul > reports/autonomous_engine.stop        # request a graceful stop
"""
from __future__ import annotations

import argparse
from collections import Counter
import hashlib
import json
import os
import pathlib
import re
import subprocess
import sys
import time
from datetime import datetime, timezone

from artifact_path_policy import handoff_artifact_path  # noqa: E402
from _atomic import write_text_atomic  # noqa: E402  (scripts/ is on sys.path as the run dir)

ROOT = pathlib.Path(__file__).resolve().parents[1]
REPORTS = ROOT / "reports"
STATE = REPORTS / "autonomous_engine_state.json"
LOG = REPORTS / "autonomous_engine.log"
PREFLIGHT_REPORT = REPORTS / "autonomous_engine_preflight.json"
STOP = REPORTS / "autonomous_engine.stop"
LOCK = REPORTS / "autonomous_engine.lock"
PLAN = ROOT / "docs" / "autonomous_loop_plan.md"
PROMPTS_FULL = REPORTS / "benchmark" / "full_promptset.json"  # gitignored; built by build_benchmark_promptset --full
DIMENSION_CANDIDATES = ROOT / "configs" / "duecare" / "benchmarks" / "research_spider" / "dimension_candidates.jsonl"
DIM_REVIEW_PACKET = REPORTS / "benchmark" / "research_spider_dimension_candidate_review_packet.json"
DIM_REVIEW_VALIDATION = REPORTS / "benchmark" / "research_spider_dimension_candidate_review_validation.json"

JUDGES = "gpt-oss:120b,glm-5.2,deepseek-v4-pro"
COMMIT_PATHS = [
    "apps/duecare-ai.com/app/static/benchmark_leaderboard.json",
    "docs/research/benchmark_leaderboard.md",
    "docs/research/rich_harness_lift_100.md",
    "docs/autonomous_loop_plan.md",
]
COMMIT_PATHS_SET = frozenset(COMMIT_PATHS)

# (model, target_n[, "full"]) worked top->bottom; n=0 = all prompts in the set. A 3rd "full"
# element grades the FULL ~76k-prompt registry set instead of the curated set. Resumable:
# re-running a partly-done job skips graded units. Extend this list to keep the engine busy longer.
# The flagship models swept across the FULL ~76k-prompt registry, at growing depth (n=0 = all 76,442).
_SWEEP_MODELS = ["gemma4:31b", "gpt-oss:120b", "glm-5.2", "deepseek-v4-pro"]
# Coarser, more aggressive climb so large-n coverage lands sooner: after a quick n=1500 round the
# depth jumps 1500 -> 10000 -> 40000 -> ALL (0 = the whole ~74,640-prompt registry). Grading is
# resumable, so each rung only grades the prompts the previous rung didn't (no rework).
_SWEEP_LEVELS = [1500, 10000, 40000, 0]
# Curated breadth: one n=40 pass to fill the multi-model leaderboard, fed 5 models per round.
_BREADTH = [
    "glm-5.1", "deepseek-v3.2", "kimi-k2.6", "qwen3.5:397b", "minimax-m2.7",
    "minimax-m3", "qwen3-coder:480b", "mistral-large-3:675b", "devstral-2:123b", "nemotron-3-ultra",
    "gemini-3-flash-preview", "gemma3:27b", "gpt-oss:20b", "gemma3:12b", "deepseek-v3.1:671b",
    "deepseek-v4-flash", "devstral-small-2:24b", "nemotron-3-super", "qwen3-coder-next", "glm-5",
    "glm-4.7", "kimi-k2.5", "minimax-m2.5", "minimax-m2.1", "ministral-3:14b",
]
# Interleave: each round grows the EXHAUSTIVE full-registry sweep on every flagship (so coverage of
# all ~74,640 seed prompts climbs from the FIRST tick -- the full set is shuffled, so each prefix is a
# representative sample) and adds 5 breadth models, so the field still widens to a rich multi-model
# board. The very first job is a full-sweep job; n=0 in the final round = the whole registry.
DEFAULT_QUEUE: list[list] = []
# Spread all breadth models across however many rungs there are (ceil division), so coarsening the
# level count never silently drops breadth coverage.
_BREADTH_CHUNK = (len(_BREADTH) + len(_SWEEP_LEVELS) - 1) // len(_SWEEP_LEVELS)
for _i, _lvl in enumerate(_SWEEP_LEVELS):
    DEFAULT_QUEUE += [[m, _lvl, "full"] for m in _SWEEP_MODELS]
    DEFAULT_QUEUE += [[m, 40] for m in _BREADTH[_i * _BREADTH_CHUNK:(_i + 1) * _BREADTH_CHUNK]]


def now() -> str:
    return datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


def log(msg: str) -> None:
    line = f"[{now()}] {msg}"
    print(line, flush=True)
    try:
        REPORTS.mkdir(parents=True, exist_ok=True)
        with LOG.open("a", encoding="utf-8") as f:
            f.write(line + "\n")
    except OSError:
        pass


def pid_alive(pid: int) -> bool:
    try:
        if os.name == "nt":
            out = subprocess.run(["tasklist", "/FI", f"PID eq {pid}"],
                                 capture_output=True, text=True, timeout=20)
            return str(pid) in out.stdout
        os.kill(pid, 0)
        return True
    except Exception:  # noqa: BLE001
        return False


def acquire_lock() -> bool:
    if LOCK.exists():
        try:
            old = int(LOCK.read_text(encoding="utf-8").split(",")[0])
        except (OSError, ValueError):
            old = -1
        if old > 0 and old != os.getpid() and pid_alive(old):
            log(f"another engine is running (pid {old}); exiting")
            return False
        log(f"stale lock (pid {old}); taking over")
    REPORTS.mkdir(parents=True, exist_ok=True)
    LOCK.write_text(f"{os.getpid()},{now()}", encoding="utf-8")
    return True


def release_lock() -> None:
    try:
        if LOCK.exists() and LOCK.read_text(encoding="utf-8").startswith(str(os.getpid())):
            LOCK.unlink()
    except OSError:
        pass


def load_state() -> dict:
    if STATE.exists():
        try:
            st = json.loads(STATE.read_text(encoding="utf-8"))
            st.setdefault("queue", [list(j) for j in DEFAULT_QUEUE])
            st.setdefault("cursor", 0)
            st.setdefault("ticks", 0)
            st.setdefault("done", [])
            st.setdefault("started", now())
            # merge: append any DEFAULT_QUEUE job not already queued, so new jobs (e.g. the full
            # sweep) flow into an already-running queue without losing the cursor / done progress.
            have = {tuple(j) for j in st["queue"]}
            for j in DEFAULT_QUEUE:
                if tuple(j) not in have:
                    st["queue"].append(list(j))
            return st
        except (OSError, json.JSONDecodeError):
            pass
    return {"queue": [list(j) for j in DEFAULT_QUEUE], "cursor": 0, "ticks": 0,
            "done": [], "started": now()}


def save_state(st: dict) -> None:
    st["updated"] = now()
    REPORTS.mkdir(parents=True, exist_ok=True)
    write_text_atomic(STATE, json.dumps(st, indent=2) + "\n")


def _run(cmd: list[str], capture: bool = False, timeout: float | None = None) -> subprocess.CompletedProcess:
    return subprocess.run(cmd, cwd=str(ROOT), capture_output=capture, text=True, timeout=timeout)


def _file_info(path: pathlib.Path) -> dict[str, object]:
    info: dict[str, object] = {"path": _rel(path), "exists": path.exists()}
    if path.exists():
        try:
            stat = path.stat()
            info.update({"bytes": stat.st_size, "mtime": int(stat.st_mtime)})
        except OSError as exc:
            info["error"] = f"{type(exc).__name__}: {exc}"
    return info


def _sha256_file(path: pathlib.Path) -> str | None:
    if not path.exists():
        return None
    try:
        h = hashlib.sha256()
        with path.open("rb") as fh:
            for chunk in iter(lambda: fh.read(1024 * 1024), b""):
                h.update(chunk)
        return h.hexdigest()
    except OSError:
        return None


def _rel(path: pathlib.Path) -> str:
    return handoff_artifact_path(path, root=ROOT)


def _full_prompt_count(path: pathlib.Path | None = None) -> tuple[int | None, str]:
    path = path or PROMPTS_FULL
    if not path.exists():
        return None, "missing"
    try:
        doc = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as exc:
        return None, f"{type(exc).__name__}: {exc}"
    prompts = doc.get("prompts") if isinstance(doc, dict) else None
    if not isinstance(prompts, list):
        return None, "prompts_not_list"
    return len(prompts), ""


def _jsonl_line_count(path: pathlib.Path) -> int | None:
    if not path.exists():
        return None
    try:
        with path.open(encoding="utf-8") as fh:
            return sum(1 for line in fh if line.strip())
    except OSError:
        return None


def _jsonl_field_counts(path: pathlib.Path, field: str) -> dict[str, int | str]:
    if not path.exists():
        return {}
    counts: Counter[str] = Counter()
    try:
        with path.open(encoding="utf-8") as fh:
            for line in fh:
                if not line.strip():
                    continue
                row = json.loads(line)
                value = row.get(field) if isinstance(row, dict) else None
                if isinstance(value, str) and value.strip():
                    counts[value.strip()] += 1
    except (OSError, json.JSONDecodeError) as exc:
        return {"__error__": f"{type(exc).__name__}: {exc}"}
    return dict(sorted(counts.items(), key=lambda item: (-item[1], item[0])))


def _jsonl_field_error(counts: dict[str, int | str]) -> str:
    error = counts.get("__error__")
    return error if isinstance(error, str) else ""


def _dimension_candidate_parse_errors(
    *,
    status_counts: dict[str, int | str],
    group_counts: dict[str, int | str],
) -> list[dict[str, str]]:
    errors: list[dict[str, str]] = []
    for field, counts in (("status", status_counts), ("group", group_counts)):
        error = _jsonl_field_error(counts)
        if error:
            errors.append({"field": field, "error": error})
    return errors


def _compact_summary(value: object) -> dict[str, object]:
    if not isinstance(value, dict):
        return {}
    out: dict[str, object] = {}
    for key, item in value.items():
        if key == "policy":
            continue
        if isinstance(item, (str, int, float, bool)) or item is None:
            out[str(key)] = item
        elif isinstance(item, dict):
            out[str(key)] = {
                str(k): v for k, v in item.items()
                if isinstance(v, (str, int, float, bool)) or v is None
            }
    return out


def _compact_meta(value: object) -> dict[str, object]:
    if not isinstance(value, dict):
        return {}
    keys = {
        "schema_version",
        "source_artifact",
        "source_artifact_sha256",
        "source_artifact_bytes",
        "source_artifact_rows",
        "packet_source_artifact",
        "packet_source_artifact_sha256",
        "packet_source_artifact_rows",
        "packet_artifact",
        "packet_artifact_sha256",
        "packet_artifact_bytes",
    }
    return {
        key: value[key] for key in keys
        if key in value and isinstance(value[key], (str, int, float, bool))
    }


def _json_summary_info(path: pathlib.Path) -> dict[str, object]:
    info = _file_info(path)
    if not path.exists():
        return info
    try:
        doc = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as exc:
        info["summary_error"] = f"{type(exc).__name__}: {exc}"
        return info
    if isinstance(doc, dict):
        info["summary"] = _compact_summary(doc.get("summary"))
        info["meta"] = _compact_meta(doc.get("_meta"))
    else:
        info["summary"] = {}
        info["meta"] = {}
    return info


def _dimension_validation_summary_issues(
    validation_summary: dict[str, object],
    *,
    packet_source_rows: object,
) -> list[str]:
    issues: list[str] = []
    for field in (
        "rows_accepted_for_rubric_proposal",
        "rows_ready_claimed",
        "dimension_review_rows",
        "root_issue_count",
    ):
        if not isinstance(validation_summary.get(field), int):
            issues.append(f"{field}_missing_or_not_integer")
    root_issue_count = validation_summary.get("root_issue_count")
    if isinstance(root_issue_count, int) and root_issue_count != 0:
        issues.append("root_issue_count_must_be_zero")
    dimension_review_rows = validation_summary.get("dimension_review_rows")
    if not isinstance(packet_source_rows, int):
        issues.append("packet_source_artifact_rows_missing_or_not_integer")
    elif isinstance(dimension_review_rows, int) and dimension_review_rows != packet_source_rows:
        issues.append("dimension_review_rows_must_match_packet_source_artifact_rows")
    return issues


def _dimension_review_gate_status() -> dict[str, object]:
    packet = _json_summary_info(DIM_REVIEW_PACKET)
    validation = _json_summary_info(DIM_REVIEW_VALIDATION)
    validation_summary = validation.get("summary") if isinstance(validation.get("summary"), dict) else {}
    packet_meta = packet.get("meta") if isinstance(packet.get("meta"), dict) else {}
    validation_meta = validation.get("meta") if isinstance(validation.get("meta"), dict) else {}
    current_source_sha = _sha256_file(DIMENSION_CANDIDATES)
    validation_ok = validation_summary.get("ok")
    proposals = validation_summary.get("rows_accepted_for_rubric_proposal")
    packet_source_rows = packet_meta.get("source_artifact_rows")
    validation_summary_issues = _dimension_validation_summary_issues(
        validation_summary,
        packet_source_rows=packet_source_rows,
    )
    if not packet.get("exists"):
        status = "review_packet_missing"
    elif packet.get("summary_error"):
        status = "review_packet_unreadable"
    elif not validation.get("exists"):
        status = "validation_missing"
    elif validation.get("summary_error"):
        status = "validation_unreadable"
    elif packet_meta.get("source_artifact_sha256") != current_source_sha:
        status = "review_packet_stale_for_dimension_candidates"
    elif validation_meta.get("packet_source_artifact_sha256") != packet_meta.get("source_artifact_sha256"):
        status = "validation_stale_for_review_packet"
    elif validation_meta.get("packet_source_artifact_rows") != packet_meta.get("source_artifact_rows"):
        status = "validation_stale_for_review_packet"
    elif validation_meta.get("packet_artifact_sha256") != _sha256_file(DIM_REVIEW_PACKET):
        status = "validation_stale_for_review_packet"
    elif validation_ok is not True:
        status = "validation_not_ok"
    elif validation_summary_issues:
        status = "validation_summary_malformed"
    elif isinstance(proposals, int) and proposals > 0:
        status = "proposals_ready_for_manual_merge"
    else:
        status = "validated_zero_proposals"
    return {
        "status": status,
        "active_rubric_promotion_ready": status == "proposals_ready_for_manual_merge",
        "dimension_candidates_sha256": current_source_sha,
        "validation_summary_issues": validation_summary_issues,
        "packet": packet,
        "validation": validation,
    }


def _dimension_review_gate_blocker(status: object) -> str | None:
    """Map stale/missing dimension-review states to preflight blocker ids."""
    if not isinstance(status, str):
        return "dimension_review_gate_unknown"
    return {
        "review_packet_missing": "dimension_review_packet_missing",
        "review_packet_unreadable": "dimension_review_packet_unreadable",
        "validation_missing": "dimension_review_validation_missing",
        "validation_unreadable": "dimension_review_validation_unreadable",
        "review_packet_stale_for_dimension_candidates": "dimension_review_packet_stale",
        "validation_stale_for_review_packet": "dimension_review_validation_stale",
        "validation_not_ok": "dimension_review_validation_not_ok",
        "validation_summary_malformed": "dimension_review_validation_summary_malformed",
    }.get(status)


def _int_value(value: object) -> int | None:
    return value if isinstance(value, int) else None


def _prompt_target_count(n: int | None, prompts_key: str | None, full_count: int | None) -> int | None:
    if n is None:
        return None
    if prompts_key == "full":
        if full_count is None:
            return None
        return full_count if n == 0 else min(n, full_count)
    return None if n == 0 else n


def _active_rich_harness_scope(
    *,
    current_model: str | None,
    current_n: int | None,
    current_set: str | None,
    full_count: int | None,
) -> dict[str, object]:
    target = _prompt_target_count(current_n, current_set, full_count) if current_model else None
    judge_count = len([j for j in JUDGES.split(",") if j.strip()])
    return {
        "runner": "rich_harness_lift.py",
        "candidate_dimension_sweep_active": False,
        "rubric_shape": "3 response arms x 5 calibrated components x configured judge panel",
        "target_prompt_count": target,
        "response_generation_cells": None if target is None else target * 3,
        "max_component_judge_cells": None if target is None else target * 3 * judge_count,
        "max_pairwise_judge_cells": None if target is None else target * judge_count,
        "configured_judges": judge_count,
    }


def _dimension_sweep_estimate(
    *,
    full_count: int | None,
    current_n: int | None,
    current_set: str | None,
    dimension_rows: int | None,
    status_counts: dict[str, int | str],
    review_gate_status: str | None = None,
    active_rubric_promotion_ready: bool | None = None,
) -> dict[str, object]:
    target = _prompt_target_count(current_n, current_set, full_count)
    review_needed = int(status_counts.get("candidate_needs_review_before_rubric_merge", 0) or 0)
    approved_like = sum(
        int(count)
        for status, count in status_counts.items()
        if isinstance(count, int) and str(status).lower() in {"approved", "reviewed", "ready", "merged"}
    )
    row_status_ready = bool(dimension_rows and approved_like == dimension_rows and review_needed == 0)
    gate_ready = active_rubric_promotion_ready if active_rubric_promotion_ready is not None else True
    return {
        "active_in_autonomous_engine": False,
        "ready_for_mass_grading": row_status_ready and gate_ready,
        "row_status_ready_for_mass_grading": row_status_ready,
        "review_gate_status": review_gate_status,
        "active_rubric_promotion_ready": active_rubric_promotion_ready,
        "review_needed_count": review_needed,
        "approved_like_count": approved_like,
        "full_registry_prompt_dimension_cells": (
            None if full_count is None or dimension_rows is None else full_count * dimension_rows
        ),
        "current_job_prompt_dimension_cells": (
            None if target is None or dimension_rows is None else target * dimension_rows
        ),
        "promotion_gate": (
            "Run build_dimension_candidate_review_packet.py, fill curator review rows, then run "
            "validate_dimension_candidate_review_packet.py before any candidate dimension becomes active."
        ),
        "note": "Candidate dimensions require curator review before they become an active grading rubric.",
    }


def _fmt_count(value: object) -> str:
    return "unknown" if value is None else f"{int(value):,}"


def _lock_status() -> dict[str, object]:
    if not LOCK.exists():
        return {"exists": False, "pid": None, "alive": False, "stale": False, "state": "absent"}
    try:
        pid = int(LOCK.read_text(encoding="utf-8").split(",")[0])
    except (OSError, ValueError):
        pid = -1
    alive = pid > 0 and pid_alive(pid)
    return {"exists": True, "pid": pid, "alive": alive, "stale": not alive, "state": "live" if alive else "stale"}


def _preflight_lock_status(report_lock: object) -> dict[str, object] | None:
    if not isinstance(report_lock, dict):
        return None
    exists_raw = report_lock.get("exists")
    alive_raw = report_lock.get("alive")
    pid_raw = report_lock.get("pid")
    exists = exists_raw if isinstance(exists_raw, bool) else None
    alive = alive_raw if isinstance(alive_raw, bool) else None
    pid = pid_raw if isinstance(pid_raw, int) and not isinstance(pid_raw, bool) else None
    state = "unknown"
    stale: bool | None = None
    if exists is False:
        state = "absent"
        stale = False
    elif exists is True and alive is True:
        state = "live"
        stale = False
    elif exists is True and alive is False:
        state = "stale"
        stale = True
    return {"exists": exists, "pid": pid, "alive": alive, "stale": stale, "state": state}


def _queue_value(st: dict) -> list:
    queue = st.get("queue", [])
    return queue if isinstance(queue, list) else []


def _queue_state(st: dict, queue: list | None = None) -> dict[str, object]:
    raw = st.get("queue", [])
    if not isinstance(raw, list):
        return {"valid": False, "error": "queue_not_list", "entry_index": None}
    queue = raw if queue is None else queue
    for i, entry in enumerate(queue):
        if not isinstance(entry, list) or len(entry) not in (2, 3):
            return {"valid": False, "error": "queue_entry_invalid", "entry_index": i}
        model = entry[0]
        n_raw = entry[1]
        prompts_key = entry[2] if len(entry) > 2 else None
        if not isinstance(model, str) or not model.strip():
            return {"valid": False, "error": "queue_entry_invalid", "entry_index": i}
        if isinstance(n_raw, bool):
            return {"valid": False, "error": "queue_entry_invalid", "entry_index": i}
        try:
            n = int(n_raw)
        except (IndexError, TypeError, ValueError):
            return {"valid": False, "error": "queue_entry_invalid", "entry_index": i}
        if n < 0 or prompts_key not in (None, "full"):
            return {"valid": False, "error": "queue_entry_invalid", "entry_index": i}
    return {"valid": True, "error": "", "entry_index": None}


def _cursor_state(st: dict, queue: list | None = None) -> dict[str, object]:
    queue = _queue_value(st) if queue is None else queue
    raw = st.get("cursor", 0)
    if isinstance(raw, bool) or not isinstance(raw, int):
        return {"raw": raw, "value": None, "valid": False, "error": "cursor_not_integer"}
    if raw < 0:
        return {"raw": raw, "value": None, "valid": False, "error": "cursor_negative"}
    if raw > len(queue):
        return {"raw": raw, "value": None, "valid": False, "error": "cursor_beyond_queue"}
    return {"raw": raw, "value": raw, "valid": True, "error": ""}


def _current_job_summary(st: dict, cursor_state: dict[str, object] | None = None) -> dict[str, object]:
    queue = _queue_value(st)
    queue_state = _queue_state(st, queue)
    if queue_state.get("valid") is not True:
        return {"index": None, "model": None, "n": None, "set": None}
    cursor_state = _cursor_state(st, queue) if cursor_state is None else cursor_state
    cursor = cursor_state.get("value")
    if cursor_state.get("valid") is not True or not isinstance(cursor, int) or cursor >= len(queue):
        return {"index": None, "model": None, "n": None, "set": None}
    model, n, key = _job(queue[cursor])
    return {
        "index": cursor + 1,
        "model": model,
        "n": n,
        "set": key or "curated",
    }


def _preflight_refresh_command(*, paused: bool | None = None) -> str:
    command = "scripts/autonomous_engine.ps1 -Preflight"
    if paused is True:
        command += " -IgnoreStopSentinel"
    return command


def _latest_preflight_summary(
    *,
    cursor: object | None = None,
    cursor_state: dict[str, object] | None = None,
    queue_state: dict[str, object] | None = None,
    current_job: dict[str, object] | None = None,
    paused: bool | None = None,
    stop_sentinel: str | None = None,
    lock: dict[str, object] | None = None,
) -> dict[str, object]:
    if not PREFLIGHT_REPORT.exists():
        return {
            "exists": False,
            "path": "",
            "matches_current_state": False,
            "state_mismatch_reasons": ["preflight_report_missing"],
            "needs_refresh": True,
            "refresh_command": _preflight_refresh_command(paused=paused),
        }
    summary: dict[str, object] = {"exists": True, "path": _rel(PREFLIGHT_REPORT)}
    try:
        doc = json.loads(PREFLIGHT_REPORT.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as exc:
        summary["error"] = f"{type(exc).__name__}: {exc}"
        summary["matches_current_state"] = False
        summary["state_mismatch_reasons"] = ["preflight_report_unreadable"]
        summary["needs_refresh"] = True
        summary["refresh_command"] = _preflight_refresh_command(paused=paused)
        return summary
    if not isinstance(doc, dict):
        summary["error"] = "preflight_report_not_object"
        summary["matches_current_state"] = False
        summary["state_mismatch_reasons"] = ["preflight_report_not_object"]
        summary["needs_refresh"] = True
        summary["refresh_command"] = _preflight_refresh_command(paused=paused)
        return summary
    meta = doc.get("_meta") if isinstance(doc, dict) else {}
    if isinstance(meta, dict):
        summary["schema_version"] = meta.get("schema_version")
        summary["written_at"] = meta.get("written_at")
        summary["mode"] = meta.get("mode")
    summary["ready"] = doc.get("ready")
    summary["blockers"] = doc.get("blockers") if isinstance(doc.get("blockers"), list) else []
    summary["ignored_blockers"] = (
        doc.get("ignored_blockers") if isinstance(doc.get("ignored_blockers"), list) else []
    )
    dimensions = doc.get("dimension_candidates")
    if isinstance(dimensions, dict):
        review_gate = dimensions.get("review_gate")
        if isinstance(review_gate, dict):
            summary["dimension_review_status"] = review_gate.get("status")
            validation_summary_issues = review_gate.get("validation_summary_issues")
            if isinstance(validation_summary_issues, list):
                summary["dimension_review_validation_summary_issues"] = [
                    issue for issue in validation_summary_issues
                    if isinstance(issue, str)
                ]
    ollama = doc.get("ollama")
    if isinstance(ollama, dict):
        summary["ollama_checked"] = bool(ollama.get("checked"))
        summary["ollama_ok"] = ollama.get("ok")
        doc_scope = doc.get("readiness_scope")
        summary["readiness_scope"] = (
            doc_scope if isinstance(doc_scope, str)
            else ("launch" if ollama.get("checked") else "state_only")
        )
        if isinstance(doc.get("launch_ready_requires_ollama_check"), bool):
            summary["launch_ready_requires_ollama_check"] = doc.get("launch_ready_requires_ollama_check")
        elif doc.get("ready") is True and not ollama.get("checked"):
            summary["launch_ready_requires_ollama_check"] = True
        diagnosis = ollama.get("diagnosis")
        if isinstance(diagnosis, dict):
            summary["ollama_diagnosis_code"] = diagnosis.get("code")
    saved_lock = _preflight_lock_status(doc.get("lock"))
    if saved_lock is not None:
        summary["saved_lock_state"] = saved_lock
    mismatch_reasons: list[str] = []
    if cursor is not None and doc.get("cursor") != cursor:
        mismatch_reasons.append("cursor_changed")
    if cursor_state is not None and doc.get("cursor_state") != cursor_state:
        mismatch_reasons.append("cursor_state_changed")
    if queue_state is not None and doc.get("queue_state") != queue_state:
        mismatch_reasons.append("queue_state_changed")
    if current_job is not None:
        expected_job = {
            "model": current_job.get("model"),
            "n": current_job.get("n"),
            "set": current_job.get("set"),
        }
        if doc.get("current_job") != expected_job:
            mismatch_reasons.append("current_job_changed")
    if paused is not None and doc.get("paused") != paused:
        mismatch_reasons.append("pause_state_changed")
    if stop_sentinel is not None and doc.get("stop_sentinel", "") != stop_sentinel:
        mismatch_reasons.append("stop_sentinel_changed")
    if lock is not None:
        report_lock = doc.get("lock")
        lock_matches = (
            isinstance(report_lock, dict)
            and report_lock.get("exists") == lock.get("exists")
            and report_lock.get("pid") == lock.get("pid")
            and report_lock.get("alive") == lock.get("alive")
        )
        if not lock_matches:
            mismatch_reasons.append("lock_changed")
    summary["matches_current_state"] = not mismatch_reasons
    summary["state_mismatch_reasons"] = mismatch_reasons
    summary["needs_refresh"] = bool(mismatch_reasons)
    if mismatch_reasons:
        summary["refresh_command"] = _preflight_refresh_command(paused=paused)
    return summary


def _status_scope_summary(current_job: dict[str, object]) -> dict[str, object]:
    model = current_job.get("model") if isinstance(current_job.get("model"), str) else None
    n = current_job.get("n") if isinstance(current_job.get("n"), int) else None
    job_set = current_job.get("set") if isinstance(current_job.get("set"), str) else None
    full_count, full_error = _full_prompt_count()
    dimension_rows = _jsonl_line_count(DIMENSION_CANDIDATES)
    dimension_status_counts = _jsonl_field_counts(DIMENSION_CANDIDATES, "status")
    dimension_group_counts = _jsonl_field_counts(DIMENSION_CANDIDATES, "group")
    dimension_parse_errors = _dimension_candidate_parse_errors(
        status_counts=dimension_status_counts,
        group_counts=dimension_group_counts,
    )
    review_gate = _dimension_review_gate_status()
    review_gate_summary_issues = review_gate.get("validation_summary_issues")
    if isinstance(review_gate_summary_issues, list):
        review_gate_summary_issues = [
            issue for issue in review_gate_summary_issues
            if isinstance(issue, str)
        ]
    else:
        review_gate_summary_issues = []
    active_scope = _active_rich_harness_scope(
        current_model=model,
        current_n=n,
        current_set=job_set,
        full_count=full_count,
    )
    dimension_sweep = _dimension_sweep_estimate(
        full_count=full_count,
        current_n=n,
        current_set=job_set,
        dimension_rows=dimension_rows,
        status_counts=dimension_status_counts,
        review_gate_status=review_gate.get("status") if isinstance(review_gate.get("status"), str) else None,
        active_rubric_promotion_ready=(
            review_gate.get("active_rubric_promotion_ready")
            if isinstance(review_gate.get("active_rubric_promotion_ready"), bool)
            else None
        ),
    )
    return {
        "active_loop_scope": active_scope,
        "full_promptset": {
            **_file_info(PROMPTS_FULL),
            "prompt_count": full_count,
            "error": full_error,
        },
        "candidate_dimension_scope": {
            "path": _rel(DIMENSION_CANDIDATES),
            "rows": dimension_rows,
            "status_counts": dimension_status_counts,
            "group_counts": dimension_group_counts,
            "parse_errors": dimension_parse_errors,
            "review_gate_status": review_gate.get("status"),
            "active_rubric_promotion_ready": review_gate.get("active_rubric_promotion_ready"),
            "review_gate_validation_summary_issues": review_gate_summary_issues,
            **dimension_sweep,
        },
    }


def status_payload() -> dict[str, object]:
    st = load_state()
    queue = _queue_value(st)
    queue_state = _queue_state(st, queue)
    lock = _lock_status()
    cursor_state = _cursor_state(st, queue)
    current_job = _current_job_summary(st, cursor_state)
    paused = STOP.exists()
    stop_sentinel = _rel(STOP) if paused else ""
    latest_preflight = _latest_preflight_summary(
        cursor=st.get("cursor"),
        cursor_state=cursor_state,
        queue_state=queue_state,
        current_job=current_job,
        paused=paused,
        stop_sentinel=stop_sentinel,
        lock=lock,
    )
    return {
        "started": st.get("started"),
        "updated": st.get("updated"),
        "ticks": st.get("ticks"),
        "cursor": st.get("cursor"),
        "cursor_state": cursor_state,
        "queue_state": queue_state,
        "queue_len": len(queue),
        "done": len(st.get("done", [])),
        "paused": paused,
        "stop_sentinel": stop_sentinel,
        "current_job": current_job,
        "engine_process_alive": bool(lock.get("alive")),
        "lock": lock,
        "last_preflight_report": latest_preflight.get("path", ""),
        "latest_preflight": latest_preflight,
        **_status_scope_summary(current_job),
    }


_LOCAL_USER_PATH = re.compile(r"[A-Za-z]:\\+Users\\+[^\\\s\"]+", re.I)


def _sanitize_diagnostic_text(text: str) -> str:
    return _LOCAL_USER_PATH.sub("%USERPROFILE%", text)


def _diagnostic_tail(text: str, *, limit: int = 400) -> str:
    sanitized = _sanitize_diagnostic_text(text)
    if len(sanitized) <= limit:
        return sanitized
    lines = [line for line in sanitized.splitlines() if line.strip()]
    kept: list[str] = []
    total = 0
    for line in reversed(lines):
        extra = len(line) + (1 if kept else 0)
        if kept and total + extra > limit:
            break
        if not kept and len(line) > limit:
            return line[-limit:]
        kept.append(line)
        total += extra
    return "\n".join(reversed(kept)) if kept else sanitized[-limit:]


def _ollama_diagnosis(text: str) -> dict[str, str]:
    lowered = text.lower()
    if "access is denied" in lowered and ("app.log" in lowered or "failed to create server log" in lowered):
        return {
            "code": "ollama_log_access_denied",
            "hint": (
                "Ollama could not write its local log file. Close or restart Ollama, then fix permissions "
                "on the local Ollama log directory before relaunching the engine."
            ),
        }
    if "timed out waiting for server to start" in lowered:
        return {
            "code": "ollama_server_start_timeout",
            "hint": "Ollama did not become ready before the bounded preflight timeout.",
        }
    return {}


def _ollama_status() -> dict[str, object]:
    try:
        result = _run(["ollama", "ps"], capture=True, timeout=8)
    except OSError as exc:
        return {
            "checked": True,
            "ok": False,
            "returncode": None,
            "error": f"{type(exc).__name__}: {exc}",
        }
    except subprocess.TimeoutExpired as exc:
        return {
            "checked": True,
            "ok": False,
            "returncode": None,
            "error": f"{type(exc).__name__}: {exc}",
        }
    stdout = (result.stdout or "").strip()
    stderr = (result.stderr or "").strip()
    stdout_tail = _diagnostic_tail(stdout)
    stderr_tail = _diagnostic_tail(stderr)
    status = {
        "checked": True,
        "ok": result.returncode == 0,
        "returncode": result.returncode,
        "stdout_tail": stdout_tail,
        "stderr_tail": stderr_tail,
    }
    diagnosis = _ollama_diagnosis(stderr)
    if diagnosis:
        status["diagnosis"] = diagnosis
    return status


def preflight_status(*, check_ollama: bool = True, ignore_stop_sentinel: bool = False) -> dict[str, object]:
    """Return a compact, non-mutating launch-readiness report."""
    st = load_state()
    queue = _queue_value(st)
    queue_state = _queue_state(st, queue)
    cursor_state = _cursor_state(st, queue)
    cursor = cursor_state.get("value")
    current = (
        queue[cursor]
        if queue_state.get("valid") is True and isinstance(cursor, int) and cursor < len(queue)
        else None
    )
    current_model = current_n = current_set = None
    if current is not None:
        current_model, current_n, current_set = _job(current)
    full_count, full_error = _full_prompt_count()
    lock = _lock_status()
    panel = _file_info(ROOT / "reports" / "rich_lift" / "panel.jsonl")
    panel["rows"] = _jsonl_line_count(ROOT / "reports" / "rich_lift" / "panel.jsonl")
    dimension_candidates = _file_info(DIMENSION_CANDIDATES)
    dimension_candidates["rows"] = _jsonl_line_count(DIMENSION_CANDIDATES)
    dimension_candidates["status_counts"] = _jsonl_field_counts(DIMENSION_CANDIDATES, "status")
    dimension_candidates["group_counts"] = _jsonl_field_counts(DIMENSION_CANDIDATES, "group")
    dimension_candidates["parse_errors"] = _dimension_candidate_parse_errors(
        status_counts=dimension_candidates["status_counts"],
        group_counts=dimension_candidates["group_counts"],
    )
    dimension_candidates["review_gate"] = _dimension_review_gate_status()
    dimension_candidates["sweep_estimate"] = _dimension_sweep_estimate(
        full_count=full_count,
        current_n=current_n,
        current_set=current_set,
        dimension_rows=_int_value(dimension_candidates["rows"]),
        status_counts=dimension_candidates["status_counts"],
        review_gate_status=(
            dimension_candidates["review_gate"].get("status")
            if isinstance(dimension_candidates["review_gate"].get("status"), str)
            else None
        ),
        active_rubric_promotion_ready=(
            dimension_candidates["review_gate"].get("active_rubric_promotion_ready")
            if isinstance(dimension_candidates["review_gate"].get("active_rubric_promotion_ready"), bool)
            else None
        ),
    )
    ollama = _ollama_status() if check_ollama else {"checked": False, "ok": None}
    blockers: list[str] = []
    ignored_blockers: list[str] = []
    if STOP.exists():
        if ignore_stop_sentinel:
            ignored_blockers.append("stop_sentinel_present")
        else:
            blockers.append("stop_sentinel_present")
    if cursor_state.get("valid") is not True:
        blockers.append("state_cursor_invalid")
    if queue_state.get("valid") is not True:
        blockers.append("state_queue_invalid")
    if lock.get("alive"):
        blockers.append("live_engine_lock_present")
    if current_set == "full" and (full_count is None or full_count <= 0):
        blockers.append("full_promptset_unavailable")
    if dimension_candidates["parse_errors"]:
        blockers.append("dimension_candidates_parse_error")
    review_gate = dimension_candidates["review_gate"]
    review_gate_blocker = (
        _dimension_review_gate_blocker(review_gate.get("status"))
        if isinstance(review_gate, dict)
        else "dimension_review_gate_unknown"
    )
    if review_gate_blocker:
        blockers.append(review_gate_blocker)
    if check_ollama and not ollama.get("ok"):
        blockers.append("ollama_unavailable")
    readiness_scope = "launch" if check_ollama else "state_only"
    return {
        "ready": not blockers,
        "readiness_scope": readiness_scope,
        "launch_ready_requires_ollama_check": not check_ollama,
        "blockers": blockers,
        "ignored_blockers": ignored_blockers,
        "started": st.get("started"),
        "updated": st.get("updated"),
        "ticks": st.get("ticks"),
        "cursor": st.get("cursor"),
        "cursor_state": cursor_state,
        "queue_state": queue_state,
        "queue_len": len(queue),
        "done": len(st.get("done", [])),
        "paused": STOP.exists(),
        "stop_sentinel": _rel(STOP) if STOP.exists() else "",
        "current_job": {
            "model": current_model,
            "n": current_n,
            "set": (current_set or "curated") if current is not None else None,
        },
        "full_promptset": {
            **_file_info(PROMPTS_FULL),
            "prompt_count": full_count,
            "error": full_error,
        },
        "active_loop_scope": _active_rich_harness_scope(
            current_model=current_model,
            current_n=current_n,
            current_set=current_set,
            full_count=full_count,
        ),
        "panel": panel,
        "dimension_candidates": dimension_candidates,
        "lock": lock,
        "ollama": ollama,
    }


def write_preflight_report(report: dict[str, object], *, mode: str) -> None:
    """Persist the latest launch-readiness report for detached/scheduled diagnosis."""
    doc = {
        "_meta": {
            "schema_version": "autonomous_engine_preflight.v1",
            "written_at": now(),
            "mode": mode,
            "path": _rel(PREFLIGHT_REPORT),
        },
        **report,
    }
    REPORTS.mkdir(parents=True, exist_ok=True)
    write_text_atomic(PREFLIGHT_REPORT, json.dumps(doc, indent=2, sort_keys=True) + "\n")


def startup_preflight_gate(*, check_ollama: bool = True) -> dict[str, object]:
    """Run startup preflight and log a compact blocker summary before any lock/tick."""
    report = preflight_status(check_ollama=check_ollama)
    write_preflight_report(report, mode="startup_gate")
    if report.get("ready"):
        return report
    blockers = report.get("blockers")
    shown = ", ".join(str(item) for item in blockers) if isinstance(blockers, list) else "unknown"
    log(f"startup preflight blocked launch: {shown}")
    ollama = report.get("ollama")
    if isinstance(ollama, dict) and isinstance(ollama.get("diagnosis"), dict):
        code = ollama["diagnosis"].get("code")
        if code:
            log(f"startup preflight ollama diagnosis: {code}")
    return report


def _job(entry) -> tuple[str, int, "str | None"]:
    """Unpack a queue entry: ``[model, n]`` or ``[model, n, prompts_key]``."""
    return str(entry[0]), int(entry[1]), (entry[2] if len(entry) > 2 else None)


def ensure_full_promptset() -> bool:
    """Build the gitignored full-registry prompt set if missing. Returns True if it's available."""
    if PROMPTS_FULL.exists():
        return True
    log("full prompt set missing -> building (build_benchmark_promptset.py --full)")
    r = _run([sys.executable, str(ROOT / "scripts" / "build_benchmark_promptset.py"), "--full"], capture=True)
    log(f"build full set rc={r.returncode} {(r.stdout or '').strip()[-120:]}")
    return PROMPTS_FULL.exists()


def run_job(model: str, n: int, prompts_key: "str | None" = None) -> bool:
    log(f"run_job START model={model} n={n} set={prompts_key or 'curated'}")
    cmd = [sys.executable, str(ROOT / "scripts" / "rich_harness_lift.py"),
           "--n", str(n), "--models", model, "--judges", JUDGES,
           "--pairwise", "--max-tokens", "0", "--pace", "0.6"]  # 0 = unlimited output (no truncation)
    if prompts_key == "full":
        if not ensure_full_promptset():
            log("full prompt set unavailable -> skipping job")
            return False
        cmd += ["--prompts", str(PROMPTS_FULL)]
    rc = _run(cmd).returncode
    log(f"run_job END model={model} rc={rc}")
    return rc == 0


def regen_board() -> None:
    r = _run([sys.executable, str(ROOT / "scripts" / "benchmark_leaderboard.py")], capture=True)
    log(f"regen_board rc={r.returncode} {(r.stdout or '').strip()[-160:]}")


def _staged_paths() -> list[str] | None:
    """Return currently staged repo-relative paths, or None if git refused the read."""
    staged = _run(["git", "diff", "--cached", "--name-only"], capture=True)
    if staged.returncode != 0:
        log(f"publish: unable to inspect staged paths rc={staged.returncode} "
            f"{((staged.stderr or '')).strip()[-120:]}")
        return None
    return [p.strip().replace("\\", "/") for p in (staged.stdout or "").splitlines() if p.strip()]


def _unexpected_staged_paths(paths: list[str]) -> list[str]:
    """Staged paths that would violate the autonomous engine's board-only commit contract."""
    return sorted(p for p in paths if p not in COMMIT_PATHS_SET)


def _log_unexpected_staged_paths(paths: list[str]) -> None:
    shown = ", ".join(paths[:6])
    extra = "" if len(paths) <= 6 else f", ... +{len(paths) - 6} more"
    log(f"publish: refusing commit; unrelated staged paths present: {shown}{extra}")


def publish(tag: str) -> None:
    staged_before = _staged_paths()
    if staged_before is None:
        return
    unexpected_before = _unexpected_staged_paths(staged_before)
    if unexpected_before:
        _log_unexpected_staged_paths(unexpected_before)
        return
    added = _run(["git", "add", "--", *COMMIT_PATHS], capture=True)
    if added.returncode != 0:
        log(f"publish: git add failed rc={added.returncode} {((added.stderr or '')).strip()[-120:]}")
        return
    st = _run(["git", "status", "--porcelain", "--", *COMMIT_PATHS], capture=True)
    if not (st.stdout or "").strip():
        log("publish: board unchanged, no commit")
        return
    staged = _staged_paths()
    if staged is None:
        return
    unexpected = _unexpected_staged_paths(staged)
    if unexpected:
        _log_unexpected_staged_paths(unexpected)
        return
    msg = (f"chore(benchmark): autonomous engine board update ({tag})\n\n"
           f"[autonomous_engine] board data only; generated by scripts/autonomous_engine.py.")
    c = _run(["git", "commit", "-m", msg, "--", *COMMIT_PATHS], capture=True)
    if c.returncode != 0:
        log(f"publish: commit rc={c.returncode} {((c.stderr or '')).strip()[-120:]}")
        return
    p = _run(["git", "push"], capture=True)
    log(f"publish: commit rc={c.returncode} push rc={p.returncode} {((p.stderr or '')).strip()[-120:]}")


def update_plan(st: dict, current) -> None:
    queue = _queue_value(st)
    queue_state = _queue_state(st, queue)
    cursor_state = _cursor_state(st, queue)
    cur = cursor_state["value"] if cursor_state.get("valid") is True else 0
    paused = STOP.exists()
    current_model = current_n = current_set = None
    cur_str = "idle/maintenance"
    if current:
        current_model, current_n, current_set = _job(current)
        cur_str = (
            f"`{current_model}` n={'all' if current_n == 0 else current_n}"
            + (" (full registry)" if current_set == "full" else "")
        )
    title_status = "paused" if paused else "live"
    progress = (f"{cur}/{len(queue)} jobs complete - paused before {cur_str}"
                if paused else f"{cur}/{len(queue)} jobs - current {cur_str}")
    full_count, _full_error = _full_prompt_count()
    dimension_rows = _jsonl_line_count(DIMENSION_CANDIDATES)
    dimension_status_counts = _jsonl_field_counts(DIMENSION_CANDIDATES, "status")
    scope = _active_rich_harness_scope(
        current_model=current_model,
        current_n=current_n,
        current_set=current_set,
        full_count=full_count,
    )
    dimension_sweep = _dimension_sweep_estimate(
        full_count=full_count,
        current_n=current_n,
        current_set=current_set,
        dimension_rows=dimension_rows,
        status_counts=dimension_status_counts,
    )
    review_gate = _dimension_review_gate_status()
    validation_summary = (
        review_gate["validation"].get("summary")
        if isinstance(review_gate.get("validation"), dict)
        and isinstance(review_gate["validation"].get("summary"), dict)
        else {}
    )
    lines = [
        f"# Autonomous benchmark engine - plan & {title_status} status",
        "",
        "> A durable, self-contained loop (`scripts/autonomous_engine.py`) that runs INDEPENDENTLY",
        "> of Claude Code. It works a queue of (model, n[, full]) benchmark jobs through",
        "> `rich_harness_lift.py`, regenerates the leaderboard, and commits+pushes the board (data",
        "> only) on its own clock. Shared memory: `reports/rich_lift/panel.jsonl` +",
        "> `reports/autonomous_engine_state.json`. Latest readiness: `reports/autonomous_engine_preflight.json`.",
        "> A `full` job grades the whole ~76k-prompt registry.",
        "",
        f"- **Started** {st.get('started')} - **updated** {now()} - **ticks** {st.get('ticks')}",
        f"- **Progress** {progress}",
    ]
    if paused:
        lines.append("- **Pause sentinel:** `reports/autonomous_engine.stop` exists; the engine will not start a new tick until it is removed.")
    if queue_state.get("valid") is not True:
        entry_note = ""
        if queue_state.get("entry_index") is not None:
            entry_note = f" at queue entry {int(queue_state['entry_index']) + 1}"
        lines.append(
            f"- **State queue:** invalid `{queue_state.get('error')}`{entry_note}; "
            "preflight and tick fail closed until the state file is repaired."
        )
    lines += [
        "",
        "## Control",
        "- **Stop gracefully:** create `reports/autonomous_engine.stop` (checked each tick).",
        "- **Status:** `scripts/autonomous_engine.ps1 -Status` reports state cursor/queue health, the current job, active runner cell counts, candidate-dimension sweep readiness, pause sentinel, lock liveness, whether the latest saved preflight blockers still match current state without calling Ollama, and whether that saved readiness was launch-scoped or state-only; missing, unreadable, or state-stale preflight reports are flagged as unmatched and include a pause-safe refresh command.",
        "- **Preflight:** `scripts/autonomous_engine.ps1 -Preflight` checks sentinel, lock, state cursor/queue shape, full promptset, panel, dimension candidates, and Ollama before restart, fails closed on malformed state, malformed candidate-dimension JSONL, plus unreadable or stale review artifacts, then writes `reports/autonomous_engine_preflight.json`. Add `-IgnoreStopSentinel` to preview launch readiness while paused. `-NoOllamaCheck` writes a `state_only` diagnostic report and returns a non-launch exit code even when state checks pass; the wrapper preserves the Python exit code in `$LASTEXITCODE`, and `powershell -File` callers receive the same process exit code.",
        "- **Startup gate:** normal wrapper launches preflight before detach while treating the pause sentinel as an ignored launch blocker; it removes the sentinel only after readiness passes. `-NoOllamaCheck` / `--no-ollama-check` is state-only for preflight diagnostics and is refused for normal startup execution (`-Run`, `-Once`, or direct Python loop mode). The Python engine also preflights before taking the lock or starting a tick. Emergency override is `--skip-startup-preflight`.",
        "- **Watchdog:** `scripts/autonomous_engine.ps1 -Register` installs a pause-preserving Task Scheduler launcher (`-WatchdogRun`) that does not ignore or remove `reports/autonomous_engine.stop`; registration and later watchdog ticks do not resume paused judging.",
        "- **Restart:** explicitly run `scripts/autonomous_engine.ps1 -Run`; the wrapper verifies launch readiness, then removes `reports/autonomous_engine.stop` and resumes from the state file + panel - no rework.",
        "- **Launch:** `scripts/autonomous_engine.ps1 -Run` (loads .env, recovery venv, detaches).",
        "",
        "## Current scope",
        "- **Active runner:** `rich_harness_lift.py`; candidate-dimension sweep active: `no`.",
        (f"- **Active job estimate:** {_fmt_count(scope['target_prompt_count'])} target prompts; "
         f"{_fmt_count(scope['response_generation_cells'])} response-generation cells; "
         f"{_fmt_count(scope['max_component_judge_cells'])} component-judge cells; "
         f"{_fmt_count(scope['max_pairwise_judge_cells'])} pairwise-judge cells."),
        (f"- **Candidate dimension sweep estimate:** {_fmt_count(dimension_rows)} candidate dimensions; "
         f"{_fmt_count(dimension_sweep['review_needed_count'])} still need curator review; "
         f"{_fmt_count(dimension_sweep['full_registry_prompt_dimension_cells'])} full-registry "
         "prompt-dimension cells if later promoted."),
        (
            "- **Dimension promotion gate:** build `reports/benchmark/"
            "research_spider_dimension_candidate_review_packet.json`, fill curator review fields, "
            "then validate it before rubric merge."
        ),
        (
            f"- **Dimension review artifacts:** gate `{review_gate['status']}`; "
            f"accepted proposals {_fmt_count(validation_summary.get('rows_accepted_for_rubric_proposal'))}; "
            f"ready claims {_fmt_count(validation_summary.get('rows_ready_claimed'))}."
        ),
        "- **Mass-grading guard:** candidate-dimension row labels alone are not enough; the review gate must report promotion-ready proposals before any candidate-dimension sweep is ready.",
        "",
        "## Job queue",
        "| # | model | n | set | status |",
        "|---:|---|---:|---|---|",
    ]
    if queue_state.get("valid") is True:
        for i, entry in enumerate(queue):
            m, n, k = _job(entry)
            status = "done" if i < cur else ("paused" if paused and i == cur else ("RUNNING" if i == cur else "queued"))
            lines.append(f"| {i + 1} | `{m}` | {'all' if n == 0 else n} | {'full' if k == 'full' else 'curated'} | {status} |")
    else:
        lines.append("| - | - | - | - | invalid queue state; see status/preflight |")
    lines.append("")
    PLAN.write_text("\n".join(lines) + "\n", encoding="utf-8")


def tick() -> bool:
    if STOP.exists():
        log("stop sentinel present -> exiting")
        return False
    st = load_state()
    st["ticks"] = st.get("ticks", 0) + 1
    queue = _queue_value(st)
    queue_state = _queue_state(st, queue)
    if queue_state.get("valid") is not True:
        log(f"invalid engine state queue ({queue_state.get('error')}); refusing tick")
        return False
    cursor_state = _cursor_state(st, queue)
    if cursor_state.get("valid") is not True:
        log(f"invalid engine state cursor ({cursor_state.get('error')}); refusing tick")
        return False
    cur = cursor_state["value"]
    if cur >= len(queue):
        log("queue exhausted -> maintenance regen")
        regen_board()
        update_plan(st, None)
        publish("maintenance")
        save_state(st)
        return True
    model, n, key = _job(queue[cur])
    update_plan(st, queue[cur])
    ok = run_job(model, n, key)
    regen_board()
    if ok:
        st["done"].append({"model": model, "n": n, "set": key or "curated", "at": now()})
        st["cursor"] = cur + 1
    save_state(st)
    next_state = _cursor_state(st, queue)
    next_cursor = next_state.get("value")
    nxt = None if not isinstance(next_cursor, int) or next_cursor >= len(queue) else queue[next_cursor]
    update_plan(st, nxt)
    publish(f"{model} n={'all' if n == 0 else n}" + (" full" if key == "full" else ""))
    return True


def main() -> int:
    ap = argparse.ArgumentParser(description="DueCare autonomous benchmark engine")
    ap.add_argument("--once", action="store_true", help="run one tick then exit (for Task Scheduler)")
    ap.add_argument("--sleep", type=int, default=20, help="seconds between ticks in loop mode")
    ap.add_argument("--status", action="store_true", help="print state and exit")
    ap.add_argument("--preflight", action="store_true", help="print launch readiness/blockers and exit")
    ap.add_argument("--no-ollama-check", action="store_true",
                    help="skip ollama ps during preflight checks")
    ap.add_argument("--ignore-stop-sentinel", action="store_true",
                    help="during --preflight only, report the stop sentinel but do not treat it as a blocker")
    ap.add_argument("--skip-startup-preflight", action="store_true",
                    help="emergency override: run without the startup preflight launch gate")
    ap.add_argument("--refresh-plan", action="store_true",
                    help="refresh docs/autonomous_loop_plan.md from state without running a benchmark tick")
    args = ap.parse_args()

    if args.status:
        print(json.dumps(status_payload(), indent=2, sort_keys=True))
        return 0

    if args.preflight:
        report = preflight_status(
            check_ollama=not args.no_ollama_check,
            ignore_stop_sentinel=args.ignore_stop_sentinel,
        )
        write_preflight_report(report, mode="manual_preflight")
        print(json.dumps(report, indent=2, sort_keys=True))
        if args.no_ollama_check and report["ready"]:
            return 3
        return 0 if report["ready"] else 2

    if args.refresh_plan:
        st = load_state()
        queue = _queue_value(st)
        queue_state = _queue_state(st, queue)
        cursor_state = _cursor_state(st, queue)
        cur = cursor_state.get("value")
        current = (
            queue[cur]
            if queue_state.get("valid") is True and isinstance(cur, int) and cur < len(queue)
            else None
        )
        update_plan(st, current)
        print(f"refreshed {PLAN.relative_to(ROOT)}")
        return 0

    if args.no_ollama_check and not args.skip_startup_preflight:
        message = (
            "--no-ollama-check is diagnostic-only for --preflight; "
            "startup execution requires an Ollama-checked preflight unless "
            "--skip-startup-preflight is used as an emergency override."
        )
        print(message, file=sys.stderr)
        return 2

    if not args.skip_startup_preflight:
        report = startup_preflight_gate(check_ollama=not args.no_ollama_check)
        if not report.get("ready"):
            print(json.dumps(report, indent=2, sort_keys=True))
            return 2

    if not acquire_lock():
        return 0
    try:
        log(f"autonomous_engine START pid={os.getpid()} once={args.once}")
        while True:
            cont = tick()
            if args.once or not cont:
                break
            time.sleep(max(5, args.sleep))
        log("autonomous_engine EXIT")
    finally:
        release_lock()
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
