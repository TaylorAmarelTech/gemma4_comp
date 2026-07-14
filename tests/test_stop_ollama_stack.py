"""Static safety contracts for the Windows cost-stop script.

The script is intentionally not executed in tests: doing so would create the live stop sentinel, disable
scheduled tasks, and terminate a process. These assertions keep its fail-closed identity and scoped Git
operations reviewable without touching runtime state.
"""
from __future__ import annotations

from pathlib import Path


_ROOT = Path(__file__).resolve().parents[1]
_SCRIPT = (_ROOT / "scripts" / "stop_ollama_stack.ps1").read_text(encoding="utf-8")


def test_lock_pid_is_verified_as_this_repos_python_engine_before_taskkill():
    assert "function Get-VerifiedEngineProcess" in _SCRIPT
    assert "Get-CimInstance -ClassName Win32_Process" in _SCRIPT
    assert "$process.ExecutablePath" in _SCRIPT
    assert "$pythonName -notmatch" in _SCRIPT
    assert "-PythonExecutable" not in _SCRIPT
    assert "scripts\\autonomous_engine.py" in _SCRIPT
    assert "$engineCommand = '(?i)^\\s*'" in _SCRIPT
    assert "[regex]::IsMatch($commandLine, $engineCommand)" in _SCRIPT

    verification = _SCRIPT.index("Get-VerifiedEngineProcess -ProcessId")
    termination = _SCRIPT.index("& taskkill /PID")
    assert verification < termination
    assert 'Assert-LastNativeSuccess "taskkill for verified engine PID' in _SCRIPT


def test_board_commit_is_path_limited_and_native_failures_are_checked():
    expected_paths = {
        "apps/duecare-ai.com/app/static/benchmark_leaderboard.json",
        "docs/research/benchmark_leaderboard.md",
        "docs/research/rich_harness_lift_100.md",
    }
    assert expected_paths <= set(line.strip(" ',") for line in _SCRIPT.splitlines())
    assert "git commit --only" in _SCRIPT
    assert "& git add" not in _SCRIPT
    assert "HEAD...@{upstream}" in _SCRIPT
    assert "branch is not synchronized with upstream" in _SCRIPT
    assert 'Assert-LastNativeSuccess "benchmark leaderboard generation"' in _SCRIPT
    assert 'Assert-LastNativeSuccess "git status for final board paths"' in _SCRIPT
    assert 'Assert-LastNativeSuccess "git upstream comparison before final board commit"' in _SCRIPT
    assert 'Assert-LastNativeSuccess "git commit for final board paths"' in _SCRIPT
    assert 'Assert-LastNativeSuccess "git push for final board commit"' in _SCRIPT
    assert "regenerated + committed final board" not in _SCRIPT
    assert "$operationFailed = $true" in _SCRIPT
    assert "DueCare stop actions completed with errors" in _SCRIPT
