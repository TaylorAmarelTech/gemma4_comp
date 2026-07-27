#requires -Version 5.1
<#
.SYNOPSIS
  Launch / control the DueCare orchestrator (scripts/orchestrator.py): health registry + backups
  for the autonomous mesh (benchmark engine, research/Hermes, automation/OpenClaw).
.EXAMPLE
  .\scripts\orchestrator.ps1 -Run         # start detached
  .\scripts\orchestrator.ps1 -Register    # Task Scheduler watchdog every 15 min (survives reboot)
  .\scripts\orchestrator.ps1 -Status      # print the mesh registry
  .\scripts\orchestrator.ps1 -Stop        # graceful stop
#>
param([switch]$Run, [switch]$Resume, [switch]$Once, [switch]$Register, [switch]$Unregister, [switch]$Stop, [switch]$Status)
$ErrorActionPreference = 'Stop'
$repo = Split-Path -Parent $PSScriptRoot
$orch = Join-Path $repo 'scripts\orchestrator.py'
$stopFile = Join-Path $repo 'reports\orchestrator\orchestrator.stop'
$taskName = 'DueCareOrchestrator'

$py = Join-Path $env:LOCALAPPDATA 'gemma4-testenv\venv\Scripts\python.exe'
if (-not (Test-Path $py)) { $py = 'python' }

# Load .env so future research/automation ticks see OLLAMA_API_KEY (does not override existing env).
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
  New-Item -ItemType Directory -Force -Path (Split-Path $stopFile) | Out-Null
  New-Item -ItemType File -Force -Path $stopFile | Out-Null
  Write-Host "Stop sentinel created ($stopFile)."
  return
}
if ($Status) { & $py $orch --status; return }
if ($Once)   { & $py $orch --once; return }
if ($Unregister) { schtasks /Delete /TN $taskName /F 2>$null; Write-Host "Unregistered $taskName."; return }
if ($Register) {
  $self = $MyInvocation.MyCommand.Path
  $ps = (Get-Command powershell).Source
  $tr = "`"$ps`" -NoProfile -ExecutionPolicy Bypass -File `"$self`" -Run"
  schtasks /Create /TN $taskName /SC MINUTE /MO 15 /TR $tr /RL LIMITED /F
  Write-Host "Registered pause-preserving watchdog '$taskName' (every 15 min, lock-serialized)."
  return
}
if ($Resume) {
  Remove-Item $stopFile -ErrorAction SilentlyContinue
  Start-Process -FilePath $py -ArgumentList @("`"$orch`"") -WorkingDirectory $repo -WindowStyle Hidden
  Write-Host "Orchestrator resumed (detached). registry: reports/orchestrator/registry.json | log: reports/orchestrator/orchestrator.log"
  return
}
if ($Run) {
  if (Test-Path -LiteralPath $stopFile) {
    Write-Host "Orchestrator remains paused: reports/orchestrator/orchestrator.stop is present. Explicit resume: scripts/orchestrator.ps1 -Resume"
    return
  }
  Start-Process -FilePath $py -ArgumentList @("`"$orch`"") -WorkingDirectory $repo -WindowStyle Hidden
  Write-Host "Orchestrator launched (detached). registry: reports/orchestrator/registry.json | log: reports/orchestrator/orchestrator.log"
  return
}
Write-Host "usage: orchestrator.ps1 -Run | -Resume | -Once | -Register | -Unregister | -Stop | -Status"
