#!/usr/bin/env python3
# ruff: noqa: E501  (profile descriptions and hints read better on one line)
"""DueCare — one launcher, several audiences.

Pick the surface that matches who you are; the launcher checks prerequisites,
prints exactly what it will run, and starts it. Nothing here is magic -- every
profile maps to a plain command you could run yourself.

    python launch.py                       # list the profiles
    python launch.py workbench             # local FastAPI workbench (needs Ollama + packages)
    python launch.py ngo                   # Dockerized all-in-one, built from source
    python launch.py demo                  # the standalone FastAPI demo app
    python launch.py benchmark             # regenerate the public benchmark read (offline)
    python launch.py notebook              # print the notebook-launch instructions
    python launch.py <profile> --dry-run   # show the command without running it
"""

from __future__ import annotations

import argparse
import shutil
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent
COMPOSE_DIR = ROOT / "examples" / "deployment" / "local-all-in-one"


def _has(cmd: str) -> bool:
    return shutil.which(cmd) is not None


def _duecare_installed() -> bool:
    try:
        import duecare.chat  # noqa: F401
    except Exception:
        return False
    return True


def _cmd_workbench() -> list[str]:
    return [sys.executable, "-m", "duecare.chat.run_server", "--host", "0.0.0.0", "--port", "8080"]


def _cmd_demo() -> list[str]:
    return [sys.executable, "-m", "uvicorn", "src.demo.app:app", "--host", "0.0.0.0", "--port", "8080"]


def _cmd_ngo() -> list[str]:
    return [
        "docker", "compose",
        "-f", str(COMPOSE_DIR / "docker-compose.yml"),
        "-f", str(COMPOSE_DIR / "docker-compose.build.yml"),
        "up", "--build",
    ]


def _cmd_benchmark() -> list[str]:
    return [sys.executable, str(ROOT / "scripts" / "analyze_full_results.py")]


PROFILES: dict[str, dict] = {
    "workbench": {
        "who": "developer / reviewer",
        "desc": "The full FastAPI chat + harness workbench at http://localhost:8080.",
        "cmd": _cmd_workbench,
        "needs": lambda: _duecare_installed() and _has("ollama"),
        "hint": "Install: `uv sync --all-packages` (or `pip install duecare-llm`), then `ollama pull gemma4:e2b`.",
    },
    "ngo": {
        "who": "NGO / regulator / non-technical operator",
        "desc": "One-command Dockerized stack (Ollama + DueCare + reverse proxy), built from source.",
        "cmd": _cmd_ngo,
        "needs": lambda: _has("docker"),
        "hint": "Install Docker Desktop. First run downloads the Gemma model; then open http://localhost.",
    },
    "demo": {
        "who": "quick look / screen recording",
        "desc": "The standalone FastAPI demo app at http://localhost:8080.",
        "cmd": _cmd_demo,
        "needs": lambda: _duecare_installed(),
        "hint": "Install the packages first: `uv sync --all-packages`.",
    },
    "benchmark": {
        "who": "researcher / analyst",
        "desc": "Regenerate the harness-lift read from the graded panel (offline, no model, no server).",
        "cmd": _cmd_benchmark,
        "needs": lambda: (ROOT / "reports" / "rich_lift" / "panel.jsonl").is_file(),
        "hint": "Or explore the public data on Kaggle: taylorsamarel/duecare-harness-benchmark-grades.",
    },
    "notebook": {
        "who": "Colab / Kaggle user (web server in a notebook)",
        "desc": "Run DueCare in a notebook with a public URL.",
        "cmd": None,
        "needs": lambda: True,
        "hint": "See examples/deployment/notebook/README.md — pip-install DueCare and launch the server with a tunnel URL.",
    },
}


def _print_profiles() -> None:
    print("DueCare launcher — pick a profile:\n")
    width = max(len(k) for k in PROFILES)
    for name, p in PROFILES.items():
        print(f"  {name.ljust(width)}  {p['who']}")
        print(f"  {' '.ljust(width)}  {p['desc']}")
    print("\nRun:  python launch.py <profile>   (add --dry-run to preview)")


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="DueCare launcher", add_help=True)
    parser.add_argument("profile", nargs="?", choices=list(PROFILES), help="which surface to launch")
    parser.add_argument("--dry-run", action="store_true", help="print the command without running it")
    args = parser.parse_args(argv)

    if not args.profile:
        _print_profiles()
        return 0

    profile = PROFILES[args.profile]
    if profile["cmd"] is None:
        print(f"[{args.profile}] {profile['desc']}")
        print(f"  -> {profile['hint']}")
        return 0

    cmd = profile["cmd"]()
    print(f"[{args.profile}] for the {profile['who']}")
    print(f"  will run: {' '.join(cmd)}")
    if not profile["needs"]():
        print(f"  ! prerequisites not detected. {profile['hint']}")
        if not args.dry_run:
            print("  (re-run with the prerequisites installed, or use --dry-run to just preview.)")
            return 1
    if args.dry_run:
        return 0
    try:
        return subprocess.call(cmd, cwd=str(ROOT))
    except KeyboardInterrupt:
        return 130


if __name__ == "__main__":
    raise SystemExit(main())
