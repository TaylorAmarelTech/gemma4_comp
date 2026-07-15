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
  .\scripts\autonomous_engine.ps1 -Restart     # verified, scoped engine-tree restart; resumes checkpoints
  .\scripts\autonomous_engine.ps1 -Register    # Task Scheduler watchdog every 15 min (survives reboot+death)
  .\scripts\autonomous_engine.ps1 -Status      # print engine state
  .\scripts\autonomous_engine.ps1 -Preflight   # check blockers before removing the pause sentinel
  .\scripts\autonomous_engine.ps1 -Preflight -NoOllamaCheck  # inspect state/promptset readiness only
  .\scripts\autonomous_engine.ps1 -Preflight -IgnoreStopSentinel  # preview launch readiness while paused
  .\scripts\autonomous_engine.ps1 -Run -SkipStartupPreflight  # emergency override only
  .\scripts\autonomous_engine.ps1 -Stop        # request a graceful stop
  .\scripts\autonomous_engine.ps1 -Unregister  # remove the Task Scheduler job
#>
param(
  [switch]$Run,
  [switch]$Restart,
  [switch]$Once,
  [switch]$Register,
  [switch]$Unregister,
  [switch]$Stop,
  [switch]$Status,
  [switch]$Preflight,
  [switch]$NoOllamaCheck,
  [switch]$IgnoreStopSentinel,
  [switch]$SkipStartupPreflight,
  [switch]$WatchdogRun
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

function Get-VerifiedEngineProcess {
  param([Parameter(Mandatory = $true)][int]$ProcessId)
  $expectedEngine = [IO.Path]::GetFullPath($engine)
  $process = Get-CimInstance -ClassName Win32_Process -Filter "ProcessId = $ProcessId" -ErrorAction Stop
  if (-not $process -or -not $process.ExecutablePath) {
    throw "cannot verify engine lock PID $ProcessId"
  }
  $actualPython = [IO.Path]::GetFullPath([string]$process.ExecutablePath)
  if ([IO.Path]::GetFileName($actualPython) -notmatch '(?i)^python(?:\d+(?:\.\d+)*)?w?\.exe$') {
    throw "engine lock PID $ProcessId is not a Python process"
  }
  $pythonArg = '(?:"' + [regex]::Escape($actualPython) + '"|' + [regex]::Escape($actualPython) + ')'
  $engineArg = '(?:"' + [regex]::Escape($expectedEngine) + '"|' + [regex]::Escape($expectedEngine) + ')'
  if (-not [regex]::IsMatch([string]$process.CommandLine, '(?i)^\s*' + $pythonArg + '\s+' + $engineArg + '(?:\s|$)')) {
    throw "engine lock PID $ProcessId does not own this repository's autonomous_engine.py"
  }
  return $process
}

if ($Restart) {
  New-Item -ItemType Directory -Force -Path $reports | Out-Null
  New-Item -ItemType File -Force -Path $stopFile | Out-Null
  $lockFile = Join-Path $reports 'autonomous_engine.lock'
  if (Test-Path $lockFile) {
    $enginePid = ((Get-Content $lockFile -Raw) -split ',')[0].Trim()
    if ($enginePid -notmatch '^\d+$') { throw "engine lock has an invalid PID; refusing restart" }
    try {
      $null = Get-VerifiedEngineProcess -ProcessId ([int]$enginePid)
      & taskkill /PID $enginePid /T /F 2>$null | Out-Null
      if ($LASTEXITCODE -ne 0) { throw "taskkill failed (exit $LASTEXITCODE)" }
      Write-Host "Stopped verified autonomous engine tree PID $enginePid; JSONL/SQLite checkpoints retained."
    } catch {
      $stillAlive = Get-Process -Id ([int]$enginePid) -ErrorAction SilentlyContinue
      if ($stillAlive) { throw }
      Write-Host "Engine lock PID $enginePid was already stopped; continuing with checkpointed restart."
    }
  }
  $Run = $true
}

if ($Stop) {
  New-Item -ItemType Directory -Force -Path $reports | Out-Null
  New-Item -ItemType File -Force -Path $stopFile | Out-Null
  Write-Host "Stop sentinel created ($stopFile); the engine exits before its next job."
  return
}
if ($Status) { & $py $engine --status; return }
function Test-LaunchedAsProcessFile {
  $processArgs = [Environment]::GetCommandLineArgs()
  for ($i = 0; $i -lt ($processArgs.Length - 1); $i++) {
    if ($processArgs[$i] -ine '-File') { continue }
    try {
      $entryPath = (Resolve-Path -LiteralPath $processArgs[$i + 1] -ErrorAction Stop).Path
      $thisPath = (Resolve-Path -LiteralPath $MyInvocation.ScriptName -ErrorAction Stop).Path
      return $entryPath -ieq $thisPath
    } catch {
      return $false
    }
  }
  return $false
}
function Set-EngineExitCode {
  param([int]$Code)
  $global:LASTEXITCODE = $Code
  if (Test-LaunchedAsProcessFile) {
    $host.SetShouldExit($Code)
  }
}
function Invoke-EnginePreflight {
  param([switch]$SkipOllama, [switch]$IgnoreStopSentinel)
  $preflightArgs = @('--preflight')
  if ($SkipOllama) { $preflightArgs += '--no-ollama-check' }
  if ($IgnoreStopSentinel) { $preflightArgs += '--ignore-stop-sentinel' }
  & $py $engine @preflightArgs
  $script:EnginePreflightExitCode = $LASTEXITCODE
}
if ($Preflight) {
  Invoke-EnginePreflight -SkipOllama:$NoOllamaCheck -IgnoreStopSentinel:$IgnoreStopSentinel
  Set-EngineExitCode $script:EnginePreflightExitCode
  return
}
if (($Run -or $Once -or $WatchdogRun) -and $NoOllamaCheck -and -not $SkipStartupPreflight) {
  Write-Host "Autonomous engine not launched; -NoOllamaCheck is state-only for -Preflight and cannot be used for startup execution."
  Write-Host "  use: .\scripts\autonomous_engine.ps1 -Preflight -NoOllamaCheck"
  Write-Host "  emergency override: .\scripts\autonomous_engine.ps1 -Run -SkipStartupPreflight"
  Set-EngineExitCode 2
  return
}
if ($Once) {
  $engineArgs = @('--once')
  if ($NoOllamaCheck) { $engineArgs += '--no-ollama-check' }
  if ($SkipStartupPreflight) { $engineArgs += '--skip-startup-preflight' }
  & $py $engine @engineArgs
  Set-EngineExitCode $LASTEXITCODE
  return
}
if ($Unregister) {
  schtasks /Delete /TN $taskName /F 2>$null
  Write-Host "Unregistered Task Scheduler job '$taskName'."
  return
}
if ($Register) {
  $self = $MyInvocation.MyCommand.Path
  $ps = (Get-Command powershell).Source
  $tr = "`"$ps`" -NoProfile -ExecutionPolicy Bypass -File `"$self`" -WatchdogRun"
  # Every 15 min, (re)launch the engine; its single-owner lock means a live engine keeps running and
  # only a dead/post-reboot one is restarted. Runs in the user session (no stored credentials needed).
  schtasks /Create /TN $taskName /SC MINUTE /MO 15 /TR $tr /RL LIMITED /F
  Write-Host "Registered Task Scheduler watchdog '$taskName' (every 15 min, lock-serialized)."
  Write-Host "It restarts the engine after a crash or reboot+login. Remove with -Unregister."
  if (Test-Path $stopFile) {
    Write-Host "Pause sentinel is still present; the watchdog will not resume until you explicitly run -Run."
  }
  return
}
if ($Run -or $WatchdogRun) {
  if (-not $SkipStartupPreflight) {
    Invoke-EnginePreflight -SkipOllama:$NoOllamaCheck -IgnoreStopSentinel:$Run
    $runPreflightCode = $script:EnginePreflightExitCode
    if ($runPreflightCode -ne 0) {
      Write-Host "Autonomous engine not launched; preflight blocked start (exit $runPreflightCode)."
      if (Test-Path $stopFile) { Write-Host "  pause sentinel still present: reports/autonomous_engine.stop" }
      Write-Host "  preflight: reports/autonomous_engine_preflight.json"
      Write-Host "  override: .\scripts\autonomous_engine.ps1 -Run -SkipStartupPreflight"
      Set-EngineExitCode $runPreflightCode
      return
    }
  }
  if ($Run) { Remove-Item $stopFile -ErrorAction SilentlyContinue }
  $engineArgs = @("`"$engine`"")
  if ($NoOllamaCheck) { $engineArgs += '--no-ollama-check' }
  if ($SkipStartupPreflight) { $engineArgs += '--skip-startup-preflight' }
  Start-Process -FilePath $py -ArgumentList $engineArgs -WorkingDirectory $repo -WindowStyle Hidden
  Write-Host "Autonomous engine launched (detached)."
  Write-Host "  state: reports/autonomous_engine_state.json   log: reports/autonomous_engine.log"
  Write-Host "  preflight: reports/autonomous_engine_preflight.json"
  Write-Host "  stop:  .\scripts\autonomous_engine.ps1 -Stop"
  return
}
Write-Host "usage: autonomous_engine.ps1 -Run | -Restart | -Once | -Register | -Unregister | -Stop | -Status | -Preflight [-NoOllamaCheck] [-IgnoreStopSentinel] [-SkipStartupPreflight]"
