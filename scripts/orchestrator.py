#!/usr/bin/env python3
"""DueCare orchestrator -- coordination, health registry, and backups for the autonomous mesh.

Runs alongside the agents; it does NOT run model jobs (the benchmark engine owns those) and never
commits the board (the engine owns board commits). Each tick it:

  1. HEALTH -- reads each agent's on-disk state and writes ONE registry
     (reports/orchestrator/registry.json): is the benchmark engine / research (Hermes) /
     automation (OpenClaw) alive and progressing? A single place to see the whole mesh.
  2. BACKUP -- snapshots the irreplaceable state (the graded panel, the published board, the prompt
     spec, the engine cursor) to reports/_backups/<UTC>/, keeping the last N (the flywheel can't
     lose data).
  3. (extensible) research + automation ticks plug in at the marked points.

Durable + safe: single-owner lock, graceful .stop sentinel, read-only on other agents' live files.

    python scripts/orchestrator.py --once     # one tick (Task Scheduler)
    python scripts/orchestrator.py            # loop
    python scripts/orchestrator.py --status   # print the registry and exit
"""
from __future__ import annotations

import argparse
import json
import os
import pathlib
import shutil
import subprocess
import time
from datetime import datetime, timezone

ROOT = pathlib.Path(__file__).resolve().parents[1]
REPORTS = ROOT / "reports"
ORCH = REPORTS / "orchestrator"
REGISTRY = ORCH / "registry.json"
LOG = ORCH / "orchestrator.log"
STOP = ORCH / "orchestrator.stop"
LOCK = ORCH / "orchestrator.lock"
BACKUPS = REPORTS / "_backups"
KEEP_BACKUPS = 24
# Off-OneDrive durable mirror: OneDrive has corrupted this tree before (it stripped the Python env),
# and the graded panel is the irreplaceable detail the board + ALL training data derive from. Keep a
# copy outside the synced tree so a OneDrive corruption of reports/_backups can't destroy it.
EXTERNAL_BACKUPS = pathlib.Path(
    os.environ.get("DUECARE_BACKUP_DIR")
    or (pathlib.Path(os.environ.get("LOCALAPPDATA") or pathlib.Path.home()) / "duecare-backups"))
KEEP_EXTERNAL = 4

ENGINE_STATE = REPORTS / "autonomous_engine_state.json"
ENGINE_LOCK = REPORTS / "autonomous_engine.lock"
PANEL = REPORTS / "rich_lift" / "panel.jsonl"

BACKUP_TARGETS = [
    "reports/rich_lift/panel.jsonl",
    "reports/rich_lift/pairwise.jsonl",
    "reports/rich_lift/results.jsonl",
    "apps/duecare-ai.com/app/static/benchmark_leaderboard.json",
    "docs/research/benchmark_leaderboard.md",
    "configs/duecare/benchmarks/scheme_prompts.json",
    "reports/autonomous_engine_state.json",
    "reports/hermes/proposals.jsonl",     # the flywheel's discovered prompts (irreplaceable)
    "reports/openclaw/vetted.jsonl",       # the flywheel's vetting verdicts (irreplaceable)
]


def now() -> str:
    return datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


def _stamp() -> str:
    return datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ")


def log(msg: str) -> None:
    line = f"[{now()}] {msg}"
    print(line, flush=True)
    try:
        ORCH.mkdir(parents=True, exist_ok=True)
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
            log(f"another orchestrator running (pid {old}); exiting")
            return False
    ORCH.mkdir(parents=True, exist_ok=True)
    LOCK.write_text(f"{os.getpid()},{now()}", encoding="utf-8")
    return True


def release_lock() -> None:
    try:
        if LOCK.exists() and LOCK.read_text(encoding="utf-8").startswith(str(os.getpid())):
            LOCK.unlink()
    except OSError:
        pass


def _read_json(p: pathlib.Path) -> dict:
    try:
        return json.loads(p.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError):
        return {}


def _age_min(p: pathlib.Path) -> float | None:
    try:
        return round((datetime.now(timezone.utc).timestamp() - p.stat().st_mtime) / 60, 1)
    except OSError:
        return None


def _lock_pid(p: pathlib.Path) -> int:
    try:
        return int(p.read_text(encoding="utf-8").split(",")[0])
    except (OSError, ValueError):
        return -1


def _last_commit_age_min(grep: str) -> float | None:
    try:
        out = subprocess.run(["git", "log", "-1", "--format=%ct", f"--grep={grep}"],
                             cwd=str(ROOT), capture_output=True, text=True, timeout=20)
        ts = out.stdout.strip()
        if ts:
            return round((datetime.now(timezone.utc).timestamp() - int(ts)) / 60, 1)
    except Exception:  # noqa: BLE001
        pass
    return None


def engine_health() -> dict:
    st = _read_json(ENGINE_STATE)
    pid = _lock_pid(ENGINE_LOCK)
    alive = pid > 0 and pid_alive(pid)
    return {
        "agent": "benchmark_engine",
        "alive": alive,
        "pid": pid if alive else None,
        "cursor": st.get("cursor"),
        "done": len(st.get("done", [])),
        "queue": len(st.get("queue", [])),
        "panel_age_min": _age_min(PANEL),
        "last_board_commit_age_min": _last_commit_age_min("autonomous engine board"),
        "status": "running" if alive else ("watchdog_will_restart" if ENGINE_LOCK.exists() else "down"),
    }


def research_health() -> dict:
    """Hermes research/discovery daemon -- registered here; tick lands with the daemon."""
    state = _read_json(REPORTS / "hermes_state.json")
    return {"agent": "research_hermes", "alive": bool(state),
            "status": state.get("status", "not_deployed_yet")}


def automation_health() -> dict:
    """OpenClaw vetting daemon -- live status + totals from its state file."""
    st = _read_json(REPORTS / "openclaw_state.json")
    return {"agent": "automation_openclaw", "alive": bool(st),
            "status": st.get("status", "not_deployed_yet"),
            "total_vetted": st.get("total_vetted", 0),
            "total_accepted": st.get("total_accepted", 0),
            "last_tick": st.get("last_tick")}


def _snapshot(dest: pathlib.Path) -> int:
    """Copy every existing BACKUP_TARGET under dest/<rel>, preserving the tree. Returns files copied."""
    n = 0
    for rel in BACKUP_TARGETS:
        src = ROOT / rel
        if src.exists():
            out = dest / rel
            out.parent.mkdir(parents=True, exist_ok=True)
            try:
                shutil.copy2(src, out)
                n += 1
            except OSError:
                pass
    return n


def _rotate(root: pathlib.Path, keep: int) -> None:
    """Keep only the newest `keep` timestamped snapshot dirs under root (append-only data, so the
    latest snapshot is always complete -- pruning old ones loses no detail)."""
    if root.exists():
        snaps = sorted(d for d in root.iterdir() if d.is_dir())
        for old in snaps[:-keep]:
            shutil.rmtree(old, ignore_errors=True)


def backup() -> dict:
    stamp = _stamp()
    n = _snapshot(BACKUPS / stamp)
    _rotate(BACKUPS, KEEP_BACKUPS)
    # Mirror to the off-OneDrive store so a OneDrive corruption can't take the only copy. Best-effort:
    # if the external drive/dir is unavailable the in-tree snapshot still stands.
    ext = None
    try:
        if _snapshot(EXTERNAL_BACKUPS / stamp):
            _rotate(EXTERNAL_BACKUPS, KEEP_EXTERNAL)
            ext = str(EXTERNAL_BACKUPS / stamp)
    except OSError:
        pass
    return {"dest": (f"reports/_backups/{stamp}" if n else None),
            "files": n, "external": ext, "at": now()}


def write_registry(agents: list[dict], bk: dict) -> None:
    ORCH.mkdir(parents=True, exist_ok=True)
    REGISTRY.write_text(json.dumps({
        "updated": now(), "agents": agents, "last_backup": bk, "backups_kept": KEEP_BACKUPS,
    }, indent=2) + "\n", encoding="utf-8")


def tick() -> bool:
    if STOP.exists():
        log("stop sentinel present -> exiting")
        return False
    agents = [engine_health(), research_health(), automation_health()]
    bk = backup()
    write_registry(agents, bk)
    eng = agents[0]
    log(f"tick: engine={eng['status']} done={eng['done']}/{eng['queue']} "
        f"board_commit_age={eng['last_board_commit_age_min']}m | backup={bk['files']} files")
    return True


def main() -> int:
    ap = argparse.ArgumentParser(description="DueCare orchestrator (health + backups + coordination)")
    ap.add_argument("--once", action="store_true", help="one tick then exit (Task Scheduler)")
    ap.add_argument("--sleep", type=int, default=1800, help="seconds between ticks in loop mode")
    ap.add_argument("--status", action="store_true", help="print the registry and exit")
    args = ap.parse_args()
    if args.status:
        print(REGISTRY.read_text(encoding="utf-8") if REGISTRY.exists() else "{}")
        return 0
    if not acquire_lock():
        return 0
    try:
        log(f"orchestrator START pid={os.getpid()} once={args.once}")
        while True:
            if not tick() or args.once:
                break
            time.sleep(max(30, args.sleep))
        log("orchestrator EXIT")
    finally:
        release_lock()
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
