#requires -Version 5.1
<#
.SYNOPSIS
  Launch / control OpenClaw (scripts/openclaw_daemon.py): the vetting / quality-gate daemon.
.EXAMPLE
  .\scripts\openclaw_daemon.ps1 -Run         # start detached
  .\scripts\openclaw_daemon.ps1 -Register    # Task Scheduler watchdog every 20 min (survives reboot)
  .\scripts\openclaw_daemon.ps1 -Status      # print vetting state
  .\scripts\openclaw_daemon.ps1 -Stop        # graceful stop
#>
param([switch]$Run, [switch]$Once, [switch]$Register, [switch]$Unregister, [switch]$Stop, [switch]$Status)
$ErrorActionPreference = 'Stop'
$repo = Split-Path -Parent $PSScriptRoot
$daemon = Join-Path $repo 'scripts\openclaw_daemon.py'
$stopFile = Join-Path $repo 'reports\openclaw\openclaw.stop'
$taskName = 'DueCareOpenClaw'

$py = Join-Path $env:LOCALAPPDATA 'gemma4-testenv\venv\Scripts\python.exe'
if (-not (Test-Path $py)) { $py = 'python' }

# OpenClaw vets via Ollama cloud -- load .env for OLLAMA_API_KEY (does not override existing env).
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
if ($Status) { & $py $daemon --status; return }
if ($Once)   { & $py $daemon --once; return }
if ($Unregister) { schtasks /Delete /TN $taskName /F 2>$null; Write-Host "Unregistered $taskName."; return }
if ($Register) {
  Remove-Item $stopFile -ErrorAction SilentlyContinue
  $self = $MyInvocation.MyCommand.Path
  $ps = (Get-Command powershell).Source
  $tr = "`"$ps`" -NoProfile -ExecutionPolicy Bypass -File `"$self`" -Run"
  schtasks /Create /TN $taskName /SC MINUTE /MO 20 /TR $tr /RL LIMITED /F
  Write-Host "Registered watchdog '$taskName' (every 20 min, lock-serialized)."
  return
}
if ($Run) {
  Remove-Item $stopFile -ErrorAction SilentlyContinue
  Start-Process -FilePath $py -ArgumentList @("`"$daemon`"") -WorkingDirectory $repo -WindowStyle Hidden
  Write-Host "OpenClaw launched (detached). verdicts: reports/openclaw/vetted.jsonl | state: reports/openclaw_state.json"
  return
}
Write-Host "usage: openclaw_daemon.ps1 -Run | -Once | -Register | -Unregister | -Stop | -Status"
