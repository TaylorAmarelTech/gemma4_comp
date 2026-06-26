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

from _atomic import write_text_atomic  # noqa: E402  (scripts/ is on sys.path as the run dir)

ROOT = pathlib.Path(__file__).resolve().parents[1]
REPORTS = ROOT / "reports"
STATE = REPORTS / "autonomous_engine_state.json"
LOG = REPORTS / "autonomous_engine.log"
STOP = REPORTS / "autonomous_engine.stop"
LOCK = REPORTS / "autonomous_engine.lock"
PLAN = ROOT / "docs" / "autonomous_loop_plan.md"
PROMPTS_FULL = REPORTS / "benchmark" / "full_promptset.json"  # gitignored; built by build_benchmark_promptset --full

JUDGES = "gpt-oss:120b,glm-5.2,deepseek-v4-pro"
COMMIT_PATHS = [
    "apps/duecare-ai.com/app/static/benchmark_leaderboard.json",
    "docs/research/benchmark_leaderboard.md",
    "docs/research/rich_harness_lift_100.md",
    "docs/autonomous_loop_plan.md",
]

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


def _run(cmd: list[str], capture: bool = False) -> subprocess.CompletedProcess:
    return subprocess.run(cmd, cwd=str(ROOT), capture_output=capture, text=True)


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
           "--pairwise", "--max-tokens", "8000", "--pace", "0.6"]
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
    cur_str = "idle/maintenance"
    if current:
        m, n, k = _job(current)
        cur_str = f"`{m}` n={'all' if n == 0 else n}" + (" (full registry)" if k == "full" else "")
    lines = [
        "# Autonomous benchmark engine — plan & live status",
        "",
        "> A durable, self-contained loop (`scripts/autonomous_engine.py`) that runs INDEPENDENTLY",
        "> of Claude Code. It works a queue of (model, n[, full]) benchmark jobs through",
        "> `rich_harness_lift.py`, regenerates the leaderboard, and commits+pushes the board (data",
        "> only) on its own clock. Shared memory: `reports/rich_lift/panel.jsonl` +",
        "> `reports/autonomous_engine_state.json`. A `full` job grades the whole ~76k-prompt registry.",
        "",
        f"- **Started** {st.get('started')} · **updated** {now()} · **ticks** {st.get('ticks')}",
        f"- **Progress** {cur}/{len(queue)} jobs · current " + cur_str,
        "",
        "## Control",
        "- **Stop gracefully:** create `reports/autonomous_engine.stop` (checked each tick).",
        "- **Restart:** resumes from the state file + panel — no rework.",
        "- **Launch:** `scripts/autonomous_engine.ps1` (loads .env, recovery venv, detaches).",
        "",
        "## Job queue",
        "| # | model | n | set | status |",
        "|---:|---|---:|---|---|",
    ]
    for i, entry in enumerate(queue):
        m, n, k = _job(entry)
        status = "done" if i < cur else ("RUNNING" if i == cur else "queued")
        lines.append(f"| {i + 1} | `{m}` | {'all' if n == 0 else n} | {'full' if k == 'full' else 'curated'} | {status} |")
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
    model, n, key = _job(queue[cur])
    update_plan(st, queue[cur])
    ok = run_job(model, n, key)
    regen_board()
    if ok:
        st["done"].append({"model": model, "n": n, "set": key or "curated", "at": now()})
        st["cursor"] = cur + 1
    save_state(st)
    nxt = None if st["cursor"] >= len(queue) else queue[st["cursor"]]
    update_plan(st, nxt)
    publish(f"{model} n={'all' if n == 0 else n}" + (" full" if key == "full" else ""))
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
