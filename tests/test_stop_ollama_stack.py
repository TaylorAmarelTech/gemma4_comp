"""Static safety contracts for the Windows cost-stop scripts.

The scripts are intentionally not executed in tests: doing so would create live stop sentinels,
disable scheduled tasks, and terminate processes. These assertions keep their fail-closed identity,
pause-preserving watchdog behavior, and scoped Git operations reviewable without touching runtime
state.
"""
from __future__ import annotations

from pathlib import Path

_ROOT = Path(__file__).resolve().parents[1]
_SCRIPT = (_ROOT / "scripts" / "stop_ollama_stack.ps1").read_text(encoding="utf-8")
_DAEMON_WRAPPERS = {
    name: (_ROOT / "scripts" / name).read_text(encoding="utf-8")
    for name in ("hermes.ps1", "openclaw_daemon.ps1", "orchestrator.ps1")
}
_MODEL_WRAPPERS = {
    name: (_ROOT / "scripts" / name).read_text(encoding="utf-8")
    for name in ("autonomous_engine.ps1", "hermes.ps1", "openclaw_daemon.ps1")
}


def test_only_verified_repository_daemon_trees_are_terminated():
    assert "function Get-VerifiedRepositoryDaemonProcesses" in _SCRIPT
    assert "Get-CimInstance -ClassName Win32_Process" in _SCRIPT
    assert "$process.ExecutablePath" in _SCRIPT
    assert "$pythonName -notmatch" in _SCRIPT
    assert "$daemonCommand = '(?i)^\\s*'" in _SCRIPT
    assert "[regex]::IsMatch([string]$process.CommandLine, $daemonCommand)" in _SCRIPT
    for relative_script in (
        "scripts\\autonomous_engine.py",
        "scripts\\hermes.py",
        "scripts\\openclaw_daemon.py",
        "scripts\\orchestrator.py",
    ):
        assert relative_script in _SCRIPT

    verification = _SCRIPT.index(
        "Get-VerifiedRepositoryDaemonProcesses -Repository $repo -ExpectedScripts $daemonScripts",
        _SCRIPT.index("# 3. Stop only verified process trees"),
    )
    termination = _SCRIPT.index("& taskkill /PID")
    assert verification < termination
    assert 'Assert-LastNativeSuccess "taskkill for verified $($rootProcess.script) PID' in _SCRIPT


def test_cost_stop_covers_every_recurring_caller_and_has_a_read_only_status():
    assert "function Get-RepositoryRelativePath" in _SCRIPT
    assert "[IO.Path]::GetRelativePath" not in _SCRIPT
    for task_name in (
        "DueCareAutonomousEngine",
        "DueCareHermes",
        "DueCareOpenClaw",
        "DueCareOrchestrator",
        "DueCareFlywheelManager",
    ):
        assert task_name in _SCRIPT
    for sentinel in (
        "autonomous_engine.stop",
        "hermes\\hermes.stop",
        "openclaw\\openclaw.stop",
        "orchestrator\\orchestrator.stop",
    ):
        assert sentinel in _SCRIPT

    write_sentinels = _SCRIPT.index("# 1. Write every daemon sentinel")
    disable_tasks = _SCRIPT.index("# 2. Disable every recurring task")
    terminate = _SCRIPT.index("# 3. Stop only verified process trees")
    assert write_sentinels < disable_tasks < terminate
    assert "function Get-CostStopState" in _SCRIPT
    assert "[switch]$Status" in _SCRIPT
    assert "cost_stop_active" in _SCRIPT
    assert "reports/cost_stop_status.json" in _SCRIPT
    status_branch = _SCRIPT.index("if ($Status)")
    resume_branch = _SCRIPT.index("if ($Resume)")
    create_reports = _SCRIPT.index(
        "New-Item -ItemType Directory -Force -Path $reports | Out-Null"
    )
    assert status_branch < resume_branch < create_reports


def test_daemon_watchdogs_preserve_stop_sentinels_until_explicit_resume():
    for name, wrapper in _DAEMON_WRAPPERS.items():
        assert "[switch]$Resume" in wrapper, name
        register = wrapper[wrapper.index("if ($Register)") : wrapper.index("if ($Resume)")]
        assert "Remove-Item $stopFile" not in register, name
        resume = wrapper[wrapper.index("if ($Resume)") : wrapper.index("if ($Run)")]
        assert "Remove-Item $stopFile" in resume, name
        assert "Start-Process" in resume, name
        run = wrapper[wrapper.index("if ($Run)") :]
        assert "if (Test-Path -LiteralPath $stopFile)" in run, name
        assert "remains paused" in run, name
        assert "Start-Process" in run, name


def test_model_daemon_wrappers_require_an_explicit_finite_provider_budget():
    for name, wrapper in _MODEL_WRAPPERS.items():
        assert "function Assert-ExplicitProviderBudget" in wrapper, name
        assert "DUECARE_MAX_PLANNED_MODEL_CALLS" in wrapper, name
        for required in (
            "DUECARE_PROVIDER_RUN_ID",
            "DUECARE_MAX_INPUT_TOKENS",
            "DUECARE_MAX_OUTPUT_TOKENS",
            "DUECARE_MAX_PROVIDER_COST_USD",
        ):
            assert required in wrapper, name
        assert "DUECARE_PROVIDER_PRICING_FILE" in wrapper, name
        assert "DUECARE_ALLOW_UNKNOWN_PROVIDER_COST" in wrapper, name
        assert "scripts\\provider_budget.py" in wrapper, name
        assert "if ($LASTEXITCODE -ne 0)" in wrapper, name
        assert '-not (Test-Path -LiteralPath "Env:$k")' in wrapper, name

        if name == "autonomous_engine.ps1":
            launch_guard = wrapper.index("if ($Run -or $Once -or $WatchdogRun)")
            budget_check = wrapper.index("Assert-ExplicitProviderBudget", launch_guard)
            assert budget_check < wrapper.index("if ($Preflight)", launch_guard)
            assert budget_check < wrapper.index("Start-Process", launch_guard)
        else:
            assert "if ($Once)   { Assert-ExplicitProviderBudget" in wrapper, name
            resume = wrapper[wrapper.index("if ($Resume)") : wrapper.index("if ($Run)")]
            assert resume.index("Assert-ExplicitProviderBudget") < resume.index(
                "Remove-Item $stopFile"
            ), name
            run = wrapper[wrapper.index("if ($Run)") :]
            assert run.index("if (Test-Path -LiteralPath $stopFile)") < run.index(
                "Assert-ExplicitProviderBudget"
            ), name
            assert run.index("Assert-ExplicitProviderBudget") < run.index(
                "Start-Process"
            ), name


def test_board_commit_is_path_limited_and_native_failures_are_checked():
    expected_paths = {
        "apps/duecare-ai.com/app/static/benchmark_leaderboard.json",
        "docs/research/benchmark_leaderboard.md",
        "docs/research/rich_harness_lift_100.md",
    }
    assert expected_paths <= set(line.strip(" ',") for line in _SCRIPT.splitlines())
    assert "[switch]$CaptureBoard" in _SCRIPT
    assert "[switch]$PublishBoard" in _SCRIPT
    assert "if ($PublishBoard) { $CaptureBoard = $true }" in _SCRIPT
    assert "if ($CaptureBoard)" in _SCRIPT
    assert "elseif (-not $PublishBoard)" in _SCRIPT
    assert "unattended stop path never publishes repository changes" in _SCRIPT
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
