#requires -Version 5.1
<#
.SYNOPSIS
  Launch / control Hermes (scripts/hermes.py): the research/discovery daemon (propose-only).
.EXAMPLE
  .\scripts\hermes.ps1 -Run         # start detached
  .\scripts\hermes.ps1 -Register    # Task Scheduler watchdog every 20 min (survives reboot)
  .\scripts\hermes.ps1 -Status      # print discovery state
  .\scripts\hermes.ps1 -Stop        # graceful stop
#>
param([switch]$Run, [switch]$Once, [switch]$Register, [switch]$Unregister, [switch]$Stop, [switch]$Status)
$ErrorActionPreference = 'Stop'
$repo = Split-Path -Parent $PSScriptRoot
$hermes = Join-Path $repo 'scripts\hermes.py'
$stopFile = Join-Path $repo 'reports\hermes\hermes.stop'
$taskName = 'DueCareHermes'

$py = Join-Path $env:LOCALAPPDATA 'gemma4-testenv\venv\Scripts\python.exe'
if (-not (Test-Path $py)) { $py = 'python' }

# Hermes needs OLLAMA_API_KEY (it generates via Ollama cloud) -- load .env without overriding env.
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
if ($Status) { & $py $hermes --status; return }
if ($Once)   { & $py $hermes --once; return }
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
  Start-Process -FilePath $py -ArgumentList @("`"$hermes`"") -WorkingDirectory $repo -WindowStyle Hidden
  Write-Host "Hermes launched (detached). proposals: reports/hermes/proposals.jsonl | state: reports/hermes_state.json"
  return
}
Write-Host "usage: hermes.ps1 -Run | -Once | -Register | -Unregister | -Stop | -Status"
