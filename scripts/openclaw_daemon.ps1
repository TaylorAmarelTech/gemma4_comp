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
param([switch]$Run, [switch]$Resume, [switch]$Once, [switch]$Register, [switch]$Unregister, [switch]$Stop, [switch]$Status)
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
    if ($k -and -not (Test-Path -LiteralPath "Env:$k")) { Set-Item -Path "Env:$k" -Value $v }
  }
}
$env:PYTHONUTF8 = '1'; $env:PYTHONIOENCODING = 'utf-8'

function Assert-ExplicitProviderBudget {
  [int]$maxCalls = 0
  $rawMaxCalls = [Environment]::GetEnvironmentVariable('DUECARE_MAX_PLANNED_MODEL_CALLS', 'Process')
  if (-not [int]::TryParse($rawMaxCalls, [ref]$maxCalls) -or $maxCalls -le 0) {
    throw 'OpenClaw is cost-locked: set an explicit positive DUECARE_MAX_PLANNED_MODEL_CALLS and the finite provider-budget variables before launch.'
  }
  foreach ($name in @(
    'DUECARE_PROVIDER_RUN_ID',
    'DUECARE_MAX_INPUT_TOKENS',
    'DUECARE_MAX_OUTPUT_TOKENS',
    'DUECARE_MAX_PROVIDER_COST_USD'
  )) {
    if ([string]::IsNullOrWhiteSpace([Environment]::GetEnvironmentVariable($name, 'Process'))) {
      throw "OpenClaw is cost-locked: required provider-budget variable $name is missing."
    }
  }
  $pricingFile = [Environment]::GetEnvironmentVariable('DUECARE_PROVIDER_PRICING_FILE', 'Process')
  $allowUnknown = [Environment]::GetEnvironmentVariable('DUECARE_ALLOW_UNKNOWN_PROVIDER_COST', 'Process')
  if ([string]::IsNullOrWhiteSpace($pricingFile) -and $allowUnknown -notmatch '^(?i:1|true|yes|on)$') {
    throw 'OpenClaw is cost-locked: configure DUECARE_PROVIDER_PRICING_FILE or explicitly record DUECARE_ALLOW_UNKNOWN_PROVIDER_COST=1.'
  }
  & $py (Join-Path $repo 'scripts\provider_budget.py') | Out-Host
  if ($LASTEXITCODE -ne 0) { throw 'OpenClaw provider-budget preflight failed.' }
}

if ($Stop) {
  New-Item -ItemType Directory -Force -Path (Split-Path $stopFile) | Out-Null
  New-Item -ItemType File -Force -Path $stopFile | Out-Null
  Write-Host "Stop sentinel created ($stopFile)."
  return
}
if ($Status) { & $py $daemon --status; return }
if ($Once)   { Assert-ExplicitProviderBudget; & $py $daemon --once; return }
if ($Unregister) { schtasks /Delete /TN $taskName /F 2>$null; Write-Host "Unregistered $taskName."; return }
if ($Register) {
  $self = $MyInvocation.MyCommand.Path
  $ps = (Get-Command powershell).Source
  $tr = "`"$ps`" -NoProfile -ExecutionPolicy Bypass -File `"$self`" -Run"
  schtasks /Create /TN $taskName /SC MINUTE /MO 20 /TR $tr /RL LIMITED /F
  Write-Host "Registered pause-preserving watchdog '$taskName' (every 20 min, lock-serialized)."
  return
}
if ($Resume) {
  Assert-ExplicitProviderBudget
  Remove-Item $stopFile -ErrorAction SilentlyContinue
  Start-Process -FilePath $py -ArgumentList @("`"$daemon`"") -WorkingDirectory $repo -WindowStyle Hidden
  Write-Host "OpenClaw resumed (detached). verdicts: reports/openclaw/vetted.jsonl | state: reports/openclaw_state.json"
  return
}
if ($Run) {
  if (Test-Path -LiteralPath $stopFile) {
    Write-Host "OpenClaw remains paused: reports/openclaw/openclaw.stop is present. Explicit resume: scripts/openclaw_daemon.ps1 -Resume"
    return
  }
  Assert-ExplicitProviderBudget
  Start-Process -FilePath $py -ArgumentList @("`"$daemon`"") -WorkingDirectory $repo -WindowStyle Hidden
  Write-Host "OpenClaw launched (detached). verdicts: reports/openclaw/vetted.jsonl | state: reports/openclaw_state.json"
  return
}
Write-Host "usage: openclaw_daemon.ps1 -Run | -Resume | -Once | -Register | -Unregister | -Stop | -Status"
