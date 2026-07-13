<#
.SYNOPSIS
  Stop the DueCare Ollama stack to save costs: capture the final board, disable every DueCare scheduled
  task, and stop the running benchmark engine.

.DESCRIPTION
  Writing the engine stop sentinel alone is NOT enough -- the watchdog's -Run path deletes the
  sentinel and relaunches. A durable cost-stop must DISABLE the scheduled tasks. This script:
    1. writes reports/autonomous_engine.stop (engine exits before its next job),
    2. kills the live engine process tree so it stops immediately (partial grading is resumable, so
       nothing is lost) and the panel is frozen,
    3. regenerates + commits the leaderboard from the accumulated panel so the stop reflects EVERYTHING
       graded so far (per "stop regardless of whether all prompts finished"); best-effort, never blocks,
    4. disables the four DueCare scheduled tasks so nothing relaunches or keeps calling Ollama.

  Used by the 30-day auto-stop (one-time task DueCareStop30Day) and runnable by hand to stop early
  (competition winners announced). Reverse with -Resume (re-enable the tasks + remove the sentinel),
  then relaunch the engine with scripts/autonomous_engine.ps1 -Run.
#>
[CmdletBinding()]
param([switch]$Resume)

$ErrorActionPreference = 'Continue'
$repo = Split-Path -Parent $PSScriptRoot
$reports = Join-Path $repo 'reports'
New-Item -ItemType Directory -Force -Path $reports | Out-Null
$sentinel = Join-Path $reports 'autonomous_engine.stop'
$tasks = 'DueCareAutonomousEngine', 'DueCareHermes', 'DueCareOpenClaw', 'DueCareOrchestrator'

if ($Resume) {
    if (Test-Path $sentinel) { Remove-Item $sentinel -Force }
    foreach ($t in $tasks) {
        try { Enable-ScheduledTask -TaskName $t -ErrorAction Stop | Out-Null; "enabled $t" }
        catch { "could not enable $t : $($_.Exception.Message)" }
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
        taskkill /PID $enginePid /T /F 2>$null | Out-Null
        "killed engine tree pid $enginePid"
    }
}

# 3. capture final results: regen the board from the accumulated panel + commit, so the stop reflects
#    everything graded so far. Best-effort -- a failure here must never block the actual stop below.
try {
    $py = Join-Path $env:LOCALAPPDATA 'gemma4-testenv\venv\Scripts\python.exe'
    if (-not (Test-Path $py)) { $py = 'python' }
    Push-Location $repo
    & $py (Join-Path $repo 'scripts\benchmark_leaderboard.py') 2>&1 | Out-Null
    & git add apps/duecare-ai.com/app/static/benchmark_leaderboard.json docs/research/benchmark_leaderboard.md docs/research/rich_harness_lift_100.md 2>$null
    & git commit -m "chore(benchmark): final board at cost-stop (30-day cap / early stop)" 2>$null | Out-Null
    & git push 2>$null | Out-Null
    Pop-Location
    "regenerated + committed final board from the accumulated panel"
} catch {
    "board capture skipped: $($_.Exception.Message)"
    try { Pop-Location } catch {}
}

# 4. disable every DueCare scheduled task so nothing relaunches
foreach ($t in $tasks) {
    try { Disable-ScheduledTask -TaskName $t -ErrorAction Stop | Out-Null; "disabled $t" }
    catch { "could not disable $t : $($_.Exception.Message)" }
}

"DueCare Ollama stack STOPPED at $(Get-Date -Format o) -- costs halted. Resume with: scripts\stop_ollama_stack.ps1 -Resume"
