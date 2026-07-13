<#
.SYNOPSIS
  Stop the DueCare Ollama stack to save costs: disable every DueCare scheduled task and stop the
  running benchmark engine.

.DESCRIPTION
  Writing the engine stop sentinel alone is NOT enough -- the watchdog's -Run path deletes the
  sentinel and relaunches. A durable cost-stop must DISABLE the scheduled tasks. This script:
    1. writes reports/autonomous_engine.stop (engine exits before its next job),
    2. disables the four DueCare scheduled tasks so nothing relaunches or keeps calling Ollama,
    3. best-effort kills the live engine process tree so it stops immediately (partial grading is
       resumable, so nothing is lost).

  Used by the 30-day auto-stop (registered as a one-time task DueCareStop30Day) and runnable by hand.
  Reverse it with -Resume (re-enable the tasks + remove the sentinel), then relaunch the engine with
  scripts/autonomous_engine.ps1 -Run.
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

# 2. disable every DueCare scheduled task so nothing relaunches
foreach ($t in $tasks) {
    try { Disable-ScheduledTask -TaskName $t -ErrorAction Stop | Out-Null; "disabled $t" }
    catch { "could not disable $t : $($_.Exception.Message)" }
}

# 3. best-effort: stop the live engine process tree now (resumable, so no grading is lost)
$lock = Join-Path $reports 'autonomous_engine.lock'
if (Test-Path $lock) {
    $enginePid = ((Get-Content $lock -Raw) -split ',')[0].Trim()
    if ($enginePid -match '^\d+$') {
        taskkill /PID $enginePid /T /F 2>$null | Out-Null
        "killed engine tree pid $enginePid"
    }
}

"DueCare Ollama stack STOPPED at $(Get-Date -Format o) -- costs halted. Resume with: scripts\stop_ollama_stack.ps1 -Resume"
