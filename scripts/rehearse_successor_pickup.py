#!/usr/bin/env python3
"""Run a model-free successor pickup rehearsal and write a sanitized receipt.

The rehearsal invokes only local, deterministic validators. It never starts the
autonomous engine, calls a model provider, publishes an artifact, or accesses
the network. Command output is shown to the operator but the optional JSON
receipt stores only counts and hashes, not raw output or absolute paths.
"""
from __future__ import annotations

import argparse
import hashlib
import json
import os
import subprocess
import sys
import tempfile
import time
from dataclasses import dataclass
from datetime import UTC, datetime
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]


@dataclass(frozen=True)
class RehearsalStep:
    name: str
    args: tuple[str, ...]
    purpose: str


STEPS: tuple[RehearsalStep, ...] = (
    RehearsalStep(
        "handoff scope",
        ("scripts/validate_publication_readiness.py", "--scope", "handoff"),
        "succession documents and live paused-state consistency",
    ),
    RehearsalStep(
        "core scope",
        ("scripts/validate_publication_readiness.py", "--scope", "core"),
        "portable public, package, and notebook release gates",
    ),
    RehearsalStep(
        "notebook surfaces",
        ("scripts/validate_benchmark.py",),
        "active and optional notebook syntax plus committed task-notebook cells",
    ),
    RehearsalStep(
        "durable archive",
        ("scripts/durable_archive.py", "--verify"),
        "checksum verification for every archived file",
    ),
    RehearsalStep(
        "engine observation",
        ("scripts/autonomous_engine.py", "--status"),
        "read-only live status after the pickup gate confirms the pause boundary",
    ),
)


def offline_environment(source: dict[str, str] | None = None) -> dict[str, str]:
    """Return a fail-closed child environment for deterministic rehearsal."""
    env = dict(os.environ if source is None else source)
    env.update(
        {
            "DUECARE_MAX_PLANNED_MODEL_CALLS": "0",
            "HF_HUB_OFFLINE": "1",
            "TRANSFORMERS_OFFLINE": "1",
            "WANDB_MODE": "disabled",
            "PYTHONUTF8": "1",
        }
    )
    return env


def _digest(text: str) -> str:
    return hashlib.sha256(text.encode("utf-8", errors="replace")).hexdigest()


def _line_count(text: str) -> int:
    return len(text.splitlines())


def _tail(text: str, limit: int = 12) -> str:
    return "\n".join(text.splitlines()[-limit:])


def run_step(step: RehearsalStep, root: Path, timeout: float) -> dict[str, object]:
    """Run one local Python step and return a privacy-minimized result."""
    started = time.monotonic()
    try:
        completed = subprocess.run(
            [sys.executable, *step.args],
            cwd=root,
            env=offline_environment(),
            capture_output=True,
            text=True,
            encoding="utf-8",
            errors="replace",
            timeout=timeout,
        )
        output = "\n".join(
            part.rstrip() for part in (completed.stdout, completed.stderr) if part.strip()
        )
        returncode = completed.returncode
        error = None
    except subprocess.TimeoutExpired as exc:
        output = "\n".join(
            str(part) for part in (exc.stdout or "", exc.stderr or "") if part
        )
        returncode = 124
        error = f"timed out after {timeout:g}s"
    except OSError as exc:
        output = ""
        returncode = 126
        error = type(exc).__name__

    elapsed = round(time.monotonic() - started, 3)
    return {
        "name": step.name,
        "command": "python " + " ".join(step.args),
        "purpose": step.purpose,
        "returncode": returncode,
        "passed": returncode == 0 and error is None,
        "elapsed_seconds": elapsed,
        "output_line_count": _line_count(output),
        "output_sha256": _digest(output),
        "error": error,
        "console_tail": _tail(output),
    }


def _git_value(root: Path, *args: str) -> str | None:
    try:
        completed = subprocess.run(
            ["git", *args],
            cwd=root,
            capture_output=True,
            text=True,
            encoding="utf-8",
            errors="replace",
            timeout=30,
        )
    except (OSError, subprocess.TimeoutExpired):
        return None
    if completed.returncode != 0:
        return None
    return completed.stdout.strip()


def git_observation(root: Path) -> dict[str, object]:
    """Return branch/revision and dirty count without exposing changed paths."""
    status = _git_value(root, "status", "--short")
    return {
        "branch": _git_value(root, "branch", "--show-current"),
        "head": _git_value(root, "rev-parse", "HEAD"),
        "dirty": bool(status) if status is not None else None,
        "changed_path_count": _line_count(status) if status is not None else None,
    }


def receipt_path(root: Path, value: str) -> Path:
    """Resolve a receipt path and require it to stay below ignored reports/."""
    reports = (root / "reports").resolve()
    candidate = Path(value)
    if not candidate.is_absolute():
        candidate = root / candidate
    candidate = candidate.resolve()
    try:
        candidate.relative_to(reports)
    except ValueError as exc:
        raise ValueError("receipt must be written below reports/") from exc
    return candidate


def write_receipt(path: Path, payload: dict[str, object]) -> None:
    """Atomically write a JSON receipt below reports/."""
    path.parent.mkdir(parents=True, exist_ok=True)
    serialized = json.dumps(payload, indent=2, sort_keys=True) + "\n"
    with tempfile.NamedTemporaryFile(
        "w", encoding="utf-8", dir=path.parent, prefix=f".{path.name}.", delete=False
    ) as handle:
        handle.write(serialized)
        temporary = Path(handle.name)
    os.replace(temporary, path)


def rehearse(root: Path, timeout: float) -> dict[str, object]:
    results = [run_step(step, root, timeout) for step in STEPS]
    receipt_results = [
        {key: value for key, value in result.items() if key != "console_tail"}
        for result in results
    ]
    return {
        "schema": "duecare.successor-rehearsal.v1",
        "generated_at": datetime.now(UTC).isoformat(),
        "repository": root.name,
        "python": f"{sys.version_info.major}.{sys.version_info.minor}.{sys.version_info.micro}",
        "git": git_observation(root),
        "controls": {
            "planned_model_calls": 0,
            "network_calls": 0,
            "publication_actions": 0,
            "raw_command_output_in_receipt": False,
        },
        "steps": receipt_results,
        "ok": all(bool(result["passed"]) for result in results),
        "_console_results": results,
    }


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--root", type=Path, default=ROOT, help="repository tree to rehearse")
    parser.add_argument("--timeout", type=float, default=900.0, help="timeout per step")
    parser.add_argument(
        "--receipt",
        default="reports/handoff/successor_rehearsal.json",
        help="ignored JSON receipt path below reports/",
    )
    parser.add_argument(
        "--no-receipt",
        action="store_true",
        help="run read-only and do not write the ignored JSON receipt",
    )
    args = parser.parse_args(argv)
    if args.timeout <= 0:
        parser.error("--timeout must be greater than zero")

    root = args.root.resolve()
    result = rehearse(root, args.timeout)
    console_results = result.pop("_console_results")
    for index, step_result in enumerate(console_results, 1):
        status = "PASS" if step_result["passed"] else "FAIL"
        print(f"[{index}/{len(console_results)}] {step_result['name']}: {status}")
        if step_result["console_tail"]:
            print(step_result["console_tail"])

    if not args.no_receipt:
        try:
            path = receipt_path(root, args.receipt)
        except ValueError as exc:
            parser.error(str(exc))
        write_receipt(path, result)
        print(f"Sanitized receipt: {path.relative_to(root)}")

    print("Successor rehearsal: PASS" if result["ok"] else "Successor rehearsal: FAIL")
    return 0 if result["ok"] else 1


if __name__ == "__main__":
    raise SystemExit(main())
