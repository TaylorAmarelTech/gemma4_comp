"""Behavioral checks for the flywheel watchdog heartbeat contract."""
from __future__ import annotations

import json
import os
import shutil
import subprocess
import time
from pathlib import Path

import pytest


ROOT = Path(__file__).resolve().parents[1]
SCRIPT = ROOT / "scripts" / "manage_flywheel.ps1"


def _powershell() -> str | None:
    for name in ("pwsh", "pwsh.exe", "powershell", "powershell.exe"):
        found = shutil.which(name)
        if found:
            return found
    return None


def _prepare_repo(tmp_path: Path, *, coverage_age_seconds: float) -> None:
    rich_lift = tmp_path / "reports" / "rich_lift"
    rich_lift.mkdir(parents=True)
    (tmp_path / "reports" / "autonomous_engine.lock").write_text(
        f"{os.getpid()},test\n", encoding="utf-8"
    )
    stale_at = time.time() - 2 * 60 * 60
    for name in ("results.jsonl", "panel_perdim.jsonl"):
        path = rich_lift / name
        path.write_text("", encoding="utf-8")
        os.utime(path, (stale_at, stale_at))
    coverage = rich_lift / "panel_perdim.coverage.json"
    coverage.write_text(
        json.dumps(
            {
                "status": "running",
                "phase": "judging",
                "updated_at": "2026-07-26T20:00:00Z",
                "phase_counts": {
                    "judging": {"completed_this_pass": 0, "failures_this_pass": 7}
                },
                "failure_summary": {
                    "judging": {"total": 7, "categories": {"RateLimited": 7}}
                },
            }
        ),
        encoding="utf-8",
    )
    coverage_at = time.time() - coverage_age_seconds
    os.utime(coverage, (coverage_at, coverage_at))


def _run_manager(tmp_path: Path) -> tuple[subprocess.CompletedProcess[str], dict]:
    completed = subprocess.run(
        [
            _powershell(),
            "-NoProfile",
            "-NonInteractive",
            "-ExecutionPolicy",
            "Bypass",
            "-File",
            str(SCRIPT),
            "-CheckOnly",
            "-StallMinutes",
            "40",
            "-RepositoryRoot",
            str(tmp_path),
            "-PythonExecutable",
            str(tmp_path / "missing-python.exe"),
        ],
        capture_output=True,
        text=True,
        timeout=30,
    )
    status_path = tmp_path / "reports" / "ops" / "flywheel_status.json"
    status = json.loads(status_path.read_text(encoding="utf-8")) if status_path.exists() else {}
    return completed, status


def test_manager_is_repository_relative_and_watches_coverage_heartbeat():
    source = SCRIPT.read_text(encoding="utf-8")

    assert "[string]$RepositoryRoot = ''" in source
    assert "Split-Path -Parent $PSScriptRoot" in source
    assert "panel_perdim.coverage.json" in source
    assert "C:\\Users\\amare\\OneDrive" not in source


@pytest.mark.skipif(_powershell() is None, reason="PowerShell is not installed")
def test_fresh_failure_heartbeat_prevents_false_stall_restart(tmp_path):
    _prepare_repo(tmp_path, coverage_age_seconds=2)

    completed, status = _run_manager(tmp_path)

    assert completed.returncode == 0, completed.stdout + completed.stderr
    assert status["state"] == "healthy"
    assert status["alive"] is True
    assert status["progress_source"] == "reports/rich_lift/panel_perdim.coverage.json"
    assert status["progress_age_min"] < 1
    assert status["restarted_this_pass"] is False
    assert status["coverage_heartbeat"]["failure_summary"] == {
        "judging": {"total": 7, "categories": {"RateLimited": 7}}
    }


@pytest.mark.skipif(_powershell() is None, reason="PowerShell is not installed")
def test_check_only_reports_stall_when_every_heartbeat_is_stale(tmp_path):
    _prepare_repo(tmp_path, coverage_age_seconds=2 * 60 * 60)

    completed, status = _run_manager(tmp_path)

    assert completed.returncode == 0, completed.stdout + completed.stderr
    assert status["state"] == "stalled"
    assert status["alive"] is True
    assert status["progress_age_min"] >= 119
    assert status["restarted_this_pass"] is False
    assert not (tmp_path / "reports" / "ops" / "manage.log").exists()
