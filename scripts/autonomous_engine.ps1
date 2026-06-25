#requires -Version 5.1
<#
.SYNOPSIS
  Launch / control the DueCare autonomous benchmark engine (scripts/autonomous_engine.py).

.DESCRIPTION
  Loads the repo .env (OLLAMA_API_KEY etc.), selects the recovery-venv Python (the system Python is
  OneDrive-corrupted), and runs the engine. The engine is durable + resumable and keeps advancing the
  benchmark on its own clock, surviving Claude Code pausing.

.EXAMPLE
  .\scripts\autonomous_engine.ps1 -Run         # start the loop detached (runs now)
  .\scripts\autonomous_engine.ps1 -Register    # Task Scheduler watchdog every 15 min (survives reboot+death)
  .\scripts\autonomous_engine.ps1 -Status      # print engine state
  .\scripts\autonomous_engine.ps1 -Stop        # request a graceful stop
  .\scripts\autonomous_engine.ps1 -Unregister  # remove the Task Scheduler job
#>
param(
  [switch]$Run,
  [switch]$Once,
  [switch]$Register,
  [switch]$Unregister,
  [switch]$Stop,
  [switch]$Status
)
$ErrorActionPreference = 'Stop'
$repo = Split-Path -Parent $PSScriptRoot
$engine = Join-Path $repo 'scripts\autonomous_engine.py'
$reports = Join-Path $repo 'reports'
$stopFile = Join-Path $reports 'autonomous_engine.stop'
$taskName = 'DueCareAutonomousEngine'

$py = Join-Path $env:LOCALAPPDATA 'gemma4-testenv\venv\Scripts\python.exe'
if (-not (Test-Path $py)) { $py = 'python' }

# Load repo .env so the engine's model subprocesses see OLLAMA_API_KEY (does not override existing env).
$envFile = Join-Path $repo '.env'
if (Test-Path $envFile) {
  foreach ($line in Get-Content $envFile) {
    if ($line -match '^\s*#' -or $line -notmatch '=') { continue }
    $idx = $line.IndexOf('='); if ($idx -lt 1) { continue }
    $k = $line.Substring(0, $idx).Trim()
    $v = $line.Substring($idx + 1).Trim().Trim('"').Trim("'")
    if ($k) { Set-Item -Path "Env:$k" -Value $v }
  }
}
$env:PYTHONUTF8 = '1'; $env:PYTHONIOENCODING = 'utf-8'

if ($Stop) {
  New-Item -ItemType Directory -Force -Path $reports | Out-Null
  New-Item -ItemType File -Force -Path $stopFile | Out-Null
  Write-Host "Stop sentinel created ($stopFile); the engine exits before its next job."
  return
}
if ($Status) { & $py $engine --status; return }
if ($Once)   { & $py $engine --once; return }
if ($Unregister) {
  schtasks /Delete /TN $taskName /F 2>$null
  Write-Host "Unregistered Task Scheduler job '$taskName'."
  return
}
if ($Register) {
  Remove-Item $stopFile -ErrorAction SilentlyContinue
  $self = $MyInvocation.MyCommand.Path
  $ps = (Get-Command powershell).Source
  $tr = "`"$ps`" -NoProfile -ExecutionPolicy Bypass -File `"$self`" -Run"
  # Every 15 min, (re)launch the engine; its single-owner lock means a live engine keeps running and
  # only a dead/post-reboot one is restarted. Runs in the user session (no stored credentials needed).
  schtasks /Create /TN $taskName /SC MINUTE /MO 15 /TR $tr /RL LIMITED /F
  Write-Host "Registered Task Scheduler watchdog '$taskName' (every 15 min, lock-serialized)."
  Write-Host "It restarts the engine after a crash or reboot+login. Remove with -Unregister."
  return
}
if ($Run) {
  Remove-Item $stopFile -ErrorAction SilentlyContinue
  Start-Process -FilePath $py -ArgumentList @("`"$engine`"") -WorkingDirectory $repo -WindowStyle Hidden
  Write-Host "Autonomous engine launched (detached)."
  Write-Host "  state: reports/autonomous_engine_state.json   log: reports/autonomous_engine.log"
  Write-Host "  stop:  .\scripts\autonomous_engine.ps1 -Stop"
  return
}
Write-Host "usage: autonomous_engine.ps1 -Run | -Once | -Register | -Unregister | -Stop | -Status"
