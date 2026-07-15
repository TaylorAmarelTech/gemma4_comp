<#
.SYNOPSIS
  Stop the DueCare Ollama stack to save costs: capture the final board, disable every DueCare scheduled
  task, and stop the running benchmark engine.

.DESCRIPTION
  Writing the engine stop sentinel alone is NOT enough -- the watchdog's -Run path deletes the
  sentinel and relaunches. A durable cost-stop must DISABLE the scheduled tasks. This script:
    1. writes reports/autonomous_engine.stop (engine exits before its next job),
    2. verifies the lock PID is this repository's Python engine before stopping its process tree
       (partial grading is resumable, so nothing is lost) and the panel is frozen,
    3. regenerates + commits the leaderboard from the accumulated panel so the stop reflects EVERYTHING
       graded so far (per "stop regardless of whether all prompts finished"); best-effort, never blocks,
    4. disables the four DueCare scheduled tasks so nothing relaunches or keeps calling Ollama.

  Used by the 30-day auto-stop (one-time task DueCareStop30Day) and runnable by hand to stop early
  (competition winners announced). Reverse with -Resume (re-enable the tasks + remove the sentinel),
  then relaunch the engine with scripts/autonomous_engine.ps1 -Run.
#>
[CmdletBinding()]
param([switch]$Resume)

$ErrorActionPreference = 'Stop'
$repo = Split-Path -Parent $PSScriptRoot
$reports = Join-Path $repo 'reports'
New-Item -ItemType Directory -Force -Path $reports | Out-Null
$sentinel = Join-Path $reports 'autonomous_engine.stop'
$tasks = 'DueCareAutonomousEngine', 'DueCareHermes', 'DueCareOpenClaw', 'DueCareOrchestrator'
$operationFailed = $false

function Assert-LastNativeSuccess {
    param([Parameter(Mandatory = $true)][string]$Operation)
    if ($LASTEXITCODE -ne 0) {
        throw "$Operation failed (exit $LASTEXITCODE)"
    }
}

function Get-VerifiedEngineProcess {
    param(
        [Parameter(Mandatory = $true)][int]$ProcessId,
        [Parameter(Mandatory = $true)][string]$Repository
    )

    $expectedRepo = [IO.Path]::GetFullPath($Repository).TrimEnd('\')
    $expectedEngine = [IO.Path]::GetFullPath((Join-Path $expectedRepo 'scripts\autonomous_engine.py'))
    if (-not $expectedEngine.StartsWith($expectedRepo + '\', [StringComparison]::OrdinalIgnoreCase)) {
        throw "expected engine path is outside the repository: $expectedEngine"
    }

    $process = Get-CimInstance -ClassName Win32_Process -Filter "ProcessId = $ProcessId" -ErrorAction Stop
    if (-not $process) {
        throw "lock PID $ProcessId is not running"
    }
    if (-not $process.ExecutablePath) {
        throw "cannot verify executable for lock PID $ProcessId"
    }
    $actualPython = [IO.Path]::GetFullPath([string]$process.ExecutablePath)
    $pythonName = [IO.Path]::GetFileName($actualPython)
    if ($pythonName -notmatch '(?i)^python(?:\d+(?:\.\d+)*)?w?\.exe$') {
        throw "lock PID $ProcessId executable is not Python: '$actualPython'"
    }
    $commandLine = [string]$process.CommandLine
    $pythonArg = '(?:"' + [regex]::Escape($actualPython) + '"|' + [regex]::Escape($actualPython) + ')'
    $engineArg = '(?:"' + [regex]::Escape($expectedEngine) + '"|' + [regex]::Escape($expectedEngine) + ')'
    $engineCommand = '(?i)^\s*' + $pythonArg + '\s+' + $engineArg + '(?:\s|$)'
    if (-not $commandLine -or -not [regex]::IsMatch($commandLine, $engineCommand)) {
        throw "lock PID $ProcessId does not own this repository's autonomous_engine.py"
    }
    return $process
}

if ($Resume) {
    if (Test-Path $sentinel) { Remove-Item $sentinel -Force }
    foreach ($t in $tasks) {
        try { Enable-ScheduledTask -TaskName $t -ErrorAction Stop | Out-Null; "enabled $t" }
        catch { $operationFailed = $true; "could not enable $t : $($_.Exception.Message)" }
    }
    if ($operationFailed) {
        throw "DueCare stack resume was incomplete; see task errors above"
    }
    "DueCare stack RE-ENABLED at $(Get-Date -Format o). Relaunch engine: scripts\autonomous_engine.ps1 -Run"
    return
}

# 1. engine stop sentinel
Set-Content -Path $sentinel -Value "ollama stack stopped $(Get-Date -Format o)" -Encoding utf8
"wrote stop sentinel: $sentinel"

# 2. stop the live engine process tree now (resumable -> no grading lost; also freezes the panel)
$lock = Join-Path $reports 'autonomous_engine.lock'
if (Test-Path $lock) {
    $enginePid = ((Get-Content $lock -Raw) -split ',')[0].Trim()
    if ($enginePid -match '^\d+$') {
        try {
            $null = Get-VerifiedEngineProcess -ProcessId ([int]$enginePid) -Repository $repo
            & taskkill /PID $enginePid /T /F 2>$null | Out-Null
            Assert-LastNativeSuccess "taskkill for verified engine PID $enginePid"
            "killed verified engine tree pid $enginePid"
        } catch {
            $operationFailed = $true
            "engine pid $enginePid was not terminated: $($_.Exception.Message)"
        }
    } else {
        $operationFailed = $true
        "engine lock has an invalid PID; no process was terminated"
    }
}

# 3. capture final results: regen the board from the accumulated panel + commit, so the stop reflects
#    everything graded so far. Best-effort -- a failure here must never block the actual stop below.
try {
    $py = Join-Path $env:LOCALAPPDATA 'gemma4-testenv\venv\Scripts\python.exe'
    if (-not (Test-Path -LiteralPath $py)) {
        $py = (Get-Command python -CommandType Application -ErrorAction Stop | Select-Object -First 1).Source
    }
    Push-Location $repo
    $locationPushed = $true
    & $py (Join-Path $repo 'scripts\benchmark_leaderboard.py') 2>&1 | Out-Null
    Assert-LastNativeSuccess "benchmark leaderboard generation"
    $boardPaths = @(
        'apps/duecare-ai.com/app/static/benchmark_leaderboard.json',
        'docs/research/benchmark_leaderboard.md',
        'docs/research/rich_harness_lift_100.md'
    )
    $boardStatus = @(& git status --porcelain -- @boardPaths 2>$null)
    Assert-LastNativeSuccess "git status for final board paths"
    if ($boardStatus.Count -eq 0) {
        "regenerated final board; no board changes to commit"
    } else {
        $branchDelta = ((& git rev-list --left-right --count 'HEAD...@{upstream}' 2>$null) -join '').Trim()
        Assert-LastNativeSuccess "git upstream comparison before final board commit"
        $deltaParts = @($branchDelta -split '\s+' | Where-Object { $_ })
        if ($deltaParts.Count -ne 2 -or $deltaParts[0] -ne '0' -or $deltaParts[1] -ne '0') {
            throw "refusing automatic board commit/push because the branch is not synchronized with upstream ($branchDelta)"
        }
        & git commit --only -m "chore(benchmark): final board at cost-stop (30-day cap / early stop)" `
            -- @boardPaths 2>$null | Out-Null
        Assert-LastNativeSuccess "git commit for final board paths"
        & git push 2>$null | Out-Null
        Assert-LastNativeSuccess "git push for final board commit"
        "regenerated, committed, and pushed final board from the accumulated panel"
    }
} catch {
    $operationFailed = $true
    "board capture/publish incomplete: $($_.Exception.Message)"
} finally {
    if ($locationPushed) { Pop-Location }
}

# 4. disable every DueCare scheduled task so nothing relaunches
foreach ($t in $tasks) {
    try { Disable-ScheduledTask -TaskName $t -ErrorAction Stop | Out-Null; "disabled $t" }
    catch { $operationFailed = $true; "could not disable $t : $($_.Exception.Message)" }
}

if ($operationFailed) {
    throw "DueCare stop actions completed with errors; the stop sentinel remains in place"
}
"DueCare Ollama stack STOPPED at $(Get-Date -Format o) -- costs halted. Resume with: scripts\stop_ollama_stack.ps1 -Resume"
