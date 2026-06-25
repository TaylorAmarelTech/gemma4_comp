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
    type nul > reports/autonomous_engine.stop        # request a graceful stop
"""
from __future__ import annotations

import argparse
import json
import os
import pathlib
import subprocess
import sys
import time
from datetime import datetime, timezone

ROOT = pathlib.Path(__file__).resolve().parents[1]
REPORTS = ROOT / "reports"
STATE = REPORTS / "autonomous_engine_state.json"
LOG = REPORTS / "autonomous_engine.log"
STOP = REPORTS / "autonomous_engine.stop"
LOCK = REPORTS / "autonomous_engine.lock"
PLAN = ROOT / "docs" / "autonomous_loop_plan.md"

JUDGES = "gpt-oss:120b,glm-5.2,deepseek-v4-pro"
COMMIT_PATHS = [
    "apps/duecare-ai.com/app/static/benchmark_leaderboard.json",
    "docs/research/benchmark_leaderboard.md",
    "docs/research/rich_harness_lift_100.md",
    "docs/autonomous_loop_plan.md",
]

# (model, target_n) worked top->bottom; n=0 = all 776 prompts. Resumable: re-running a
# partly-done job skips graded units. Extend this list to keep the engine busy longer.
DEFAULT_QUEUE = [
    # Phase A -- breadth at n=40 (finish the 15-model field)
    ["gpt-oss:120b", 40], ["glm-5.2", 40], ["deepseek-v4-pro", 40], ["glm-5.1", 40],
    ["deepseek-v3.2", 40], ["kimi-k2.6", 40], ["qwen3.5:397b", 40], ["minimax-m2.7", 40],
    ["minimax-m3", 40], ["qwen3-coder:480b", 40], ["mistral-large-3:675b", 40],
    ["devstral-2:123b", 40], ["nemotron-3-ultra", 40], ["gemini-3-flash-preview", 40],
    ["gemma3:27b", 40],
    # Phase B -- depth on headliners across all 776 prompts (full 77-typology coverage)
    ["gemma4:31b", 0], ["glm-5.2", 0], ["deepseek-v4-pro", 0], ["kimi-k2.6", 0],
    # Phase C -- widen the field at n=40
    ["gpt-oss:20b", 40], ["gemma3:12b", 40], ["deepseek-v3.1:671b", 40],
    ["deepseek-v4-flash", 40], ["devstral-small-2:24b", 40], ["nemotron-3-super", 40],
    ["qwen3-coder-next", 40], ["glm-5", 40], ["glm-4.7", 40], ["kimi-k2.5", 40],
    ["minimax-m2.5", 40], ["minimax-m2.1", 40], ["ministral-3:14b", 40],
    # Phase D -- depth on the rest across all 776 prompts
    ["gpt-oss:120b", 0], ["qwen3.5:397b", 0], ["qwen3-coder:480b", 0], ["minimax-m3", 0],
]


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
            return st
        except (OSError, json.JSONDecodeError):
            pass
    return {"queue": [list(j) for j in DEFAULT_QUEUE], "cursor": 0, "ticks": 0,
            "done": [], "started": now()}


def save_state(st: dict) -> None:
    st["updated"] = now()
    REPORTS.mkdir(parents=True, exist_ok=True)
    STATE.write_text(json.dumps(st, indent=2) + "\n", encoding="utf-8")


def _run(cmd: list[str], capture: bool = False) -> subprocess.CompletedProcess:
    return subprocess.run(cmd, cwd=str(ROOT), capture_output=capture, text=True)


def run_job(model: str, n: int) -> bool:
    log(f"run_job START model={model} n={n}")
    cmd = [sys.executable, str(ROOT / "scripts" / "rich_harness_lift.py"),
           "--n", str(n), "--models", model, "--judges", JUDGES,
           "--pairwise", "--max-tokens", "8000", "--pace", "0.6"]
    rc = _run(cmd).returncode
    log(f"run_job END model={model} rc={rc}")
    return rc == 0


def regen_board() -> None:
    r = _run([sys.executable, str(ROOT / "scripts" / "benchmark_leaderboard.py")], capture=True)
    log(f"regen_board rc={r.returncode} {(r.stdout or '').strip()[-160:]}")


def publish(tag: str) -> None:
    _run(["git", "add", *COMMIT_PATHS])
    st = _run(["git", "status", "--porcelain", *COMMIT_PATHS], capture=True)
    if not (st.stdout or "").strip():
        log("publish: board unchanged, no commit")
        return
    msg = (f"chore(benchmark): autonomous engine board update ({tag})\n\n"
           f"[autonomous_engine] board data only; generated by scripts/autonomous_engine.py.")
    c = _run(["git", "commit", "-m", msg], capture=True)
    p = _run(["git", "push"], capture=True)
    log(f"publish: commit rc={c.returncode} push rc={p.returncode} {((p.stderr or '')).strip()[-120:]}")


def update_plan(st: dict, current) -> None:
    cur = st.get("cursor", 0)
    queue = st.get("queue", [])
    lines = [
        "# Autonomous benchmark engine — plan & live status",
        "",
        "> A durable, self-contained loop (`scripts/autonomous_engine.py`) that runs INDEPENDENTLY",
        "> of Claude Code. It works a queue of (model, n) benchmark jobs through `rich_harness_lift.py`,",
        "> regenerates the leaderboard, and commits+pushes the board (data only) on its own clock.",
        "> Shared memory: `reports/rich_lift/panel.jsonl` + `reports/autonomous_engine_state.json`.",
        "",
        f"- **Started** {st.get('started')} · **updated** {now()} · **ticks** {st.get('ticks')}",
        f"- **Progress** {cur}/{len(queue)} jobs · current "
        + (f"`{current[0]}` n={'all 776' if current[1] == 0 else current[1]}" if current else "idle/maintenance"),
        "",
        "## Control",
        "- **Stop gracefully:** create `reports/autonomous_engine.stop` (checked each tick).",
        "- **Restart:** resumes from the state file + panel — no rework.",
        "- **Launch:** `scripts/autonomous_engine.ps1` (loads .env, recovery venv, detaches).",
        "",
        "## Job queue",
        "| # | model | n | status |",
        "|---:|---|---:|---|",
    ]
    for i, (m, n) in enumerate(queue):
        status = "done" if i < cur else ("RUNNING" if i == cur else "queued")
        lines.append(f"| {i + 1} | `{m}` | {'all 776' if n == 0 else n} | {status} |")
    lines.append("")
    PLAN.write_text("\n".join(lines) + "\n", encoding="utf-8")


def tick() -> bool:
    if STOP.exists():
        log("stop sentinel present -> exiting")
        return False
    st = load_state()
    st["ticks"] = st.get("ticks", 0) + 1
    queue = st["queue"]
    cur = st["cursor"]
    if cur >= len(queue):
        log("queue exhausted -> maintenance regen")
        regen_board()
        update_plan(st, None)
        publish("maintenance")
        save_state(st)
        return True
    model, n = queue[cur]
    update_plan(st, (model, n))
    ok = run_job(model, n)
    regen_board()
    if ok:
        st["done"].append({"model": model, "n": n, "at": now()})
        st["cursor"] = cur + 1
    save_state(st)
    nxt = None if st["cursor"] >= len(queue) else tuple(queue[st["cursor"]])
    update_plan(st, nxt)
    publish(f"{model} n={n}")
    return True


def main() -> int:
    ap = argparse.ArgumentParser(description="DueCare autonomous benchmark engine")
    ap.add_argument("--once", action="store_true", help="run one tick then exit (for Task Scheduler)")
    ap.add_argument("--sleep", type=int, default=20, help="seconds between ticks in loop mode")
    ap.add_argument("--status", action="store_true", help="print state and exit")
    args = ap.parse_args()

    if args.status:
        st = load_state()
        print(json.dumps({"started": st.get("started"), "updated": st.get("updated"),
                          "ticks": st.get("ticks"), "cursor": st.get("cursor"),
                          "queue_len": len(st.get("queue", [])), "done": len(st.get("done", []))}, indent=2))
        return 0

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
