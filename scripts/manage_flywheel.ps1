<#
.SYNOPSIS
  DueCare flywheel operations manager: detect + self-heal an engine that is running but
  STALLED (the known jam the 15-min -WatchdogRun does not catch, because it only replaces a
  DEAD lock pid), snapshot the large interim-goal dashboard, and write a status file.

  The existing DueCareAutonomousEngine watchdog handles dead-pid restarts. This manager is
  complementary: it only force-restarts when the lock pid is ALIVE but neither grading output nor
  the aggregate-only coverage heartbeat has advanced for -StallMinutes. The coverage heartbeat is
  important during provider failures, when the runner is alive and checkpointing failure counts but
  cannot append a completed panel row. Restarts are rate-limited and use the documented safe path
  (autonomous_engine.ps1 -Restart, which resumes checkpoints). Non-restarting with -CheckOnly.

.EXAMPLE
  pwsh scripts/manage_flywheel.ps1 -CheckOnly     # diagnose, never restart
  pwsh scripts/manage_flywheel.ps1                # manage: heal stalls, log interim, write status
#>
[CmdletBinding()]
param(
  [switch]$CheckOnly,
  [int]$StallMinutes = 40,
  [int]$MinRestartGapMinutes = 60,
  [string]$RepositoryRoot = '',
  [string]$PythonExecutable = ''
)
$ErrorActionPreference = 'Stop'
$repo = if ([string]::IsNullOrWhiteSpace($RepositoryRoot)) {
  Split-Path -Parent $PSScriptRoot
} else {
  [IO.Path]::GetFullPath($RepositoryRoot)
}
if (-not (Test-Path -LiteralPath $repo -PathType Container)) {
  throw "repository root does not exist: $repo"
}
$ops = Join-Path $repo 'reports\ops'
if (-not (Test-Path $ops)) { New-Item -ItemType Directory -Force -Path $ops | Out-Null }
$statusFile = Join-Path $ops 'flywheel_status.json'
$interimLog = Join-Path $ops 'interim_log.md'
$manageLog  = Join-Path $ops 'manage.log'
$py = if ([string]::IsNullOrWhiteSpace($PythonExecutable)) {
  Join-Path $env:LOCALAPPDATA 'gemma4-testenv\venv\Scripts\python.exe'
} else {
  $PythonExecutable
}
$now = Get-Date

# 1) engine liveness (trust the lock PID being a live process, not the task state)
$lockFile = Join-Path $repo 'reports\autonomous_engine.lock'
$lockPid = $null; $alive = $false
if (Test-Path $lockFile) {
  $lockPid = ((Get-Content $lockFile -Raw) -split ',')[0].Trim()
  if ($lockPid) { $alive = [bool](Get-Process -Id ([int]$lockPid) -ErrorAction SilentlyContinue) }
}

# 2) Progress freshness = the newest successful output OR aggregate-only coverage heartbeat.
# A provider outage can yield no completed JSONL row while the runner remains alive and records
# failure counts every 30 seconds. Treating that heartbeat as stale caused destructive restart loops.
$progressSamples = @()
foreach ($f in @(
  'reports\rich_lift\results.jsonl',
  'reports\rich_lift\panel_perdim.jsonl',
  'reports\rich_lift\panel_perdim.coverage.json'
)) {
  $p = Join-Path $repo $f
  if (Test-Path -LiteralPath $p -PathType Leaf) {
    $item = Get-Item -LiteralPath $p
    $age = [math]::Max(0.0, (New-TimeSpan -Start $item.LastWriteTime -End $now).TotalMinutes)
    $progressSamples += [pscustomobject][ordered]@{
      path = $f.Replace('\', '/')
      last_write_utc = $item.LastWriteTimeUtc.ToString('o')
      age_min = [math]::Round($age, 1)
    }
  }
}
$latestProgress = $progressSamples | Sort-Object age_min, path | Select-Object -First 1
$progressAge = if ($latestProgress) { [double]$latestProgress.age_min } else { 999999 }
$progressSource = if ($latestProgress) { [string]$latestProgress.path } else { $null }

$coverageHeartbeat = $null
$coveragePath = Join-Path $repo 'reports\rich_lift\panel_perdim.coverage.json'
if (Test-Path -LiteralPath $coveragePath -PathType Leaf) {
  try {
    $coverageDoc = Get-Content -LiteralPath $coveragePath -Raw | ConvertFrom-Json
    $coverageHeartbeat = [ordered]@{
      status = $coverageDoc.status
      phase = $coverageDoc.phase
      updated_at = $coverageDoc.updated_at
      phase_counts = $coverageDoc.phase_counts
      failure_summary = $coverageDoc.failure_summary
    }
  } catch {
    $coverageHeartbeat = [ordered]@{ status = 'unreadable' }
  }
}

$state = 'healthy'
if (-not $alive) { $state = 'dead' }              # dead-pid restart is the existing watchdog's job
elseif ($progressAge -gt $StallMinutes) { $state = 'stalled' }

# 3) self-heal ONLY the stall case, rate-limited, via the safe checkpoint-resuming restart
$restarted = $false
$lastRestart = $null
if (Test-Path $statusFile) { try { $lastRestart = (Get-Content $statusFile -Raw | ConvertFrom-Json).last_restart } catch {} }
$gapOk = $true
if ($lastRestart) { $gapOk = ((New-TimeSpan -Start ([datetime]$lastRestart) -End $now).TotalMinutes -ge $MinRestartGapMinutes) }
if ($state -eq 'stalled' -and (-not $CheckOnly) -and $gapOk) {
  "$($now.ToString('u'))  STALL detected (progressAge=$progressAge min, progressSource=$progressSource, pid=$lockPid alive) -> autonomous_engine.ps1 -Restart" | Add-Content -Path $manageLog
  try { & (Join-Path $repo 'scripts\autonomous_engine.ps1') -Restart *>> $manageLog; $restarted = $true; $lastRestart = $now.ToString('o') }
  catch { "restart FAILED: $_" | Add-Content -Path $manageLog }
}

# 4) interim-goal dashboard snapshot (read-only; no Ollama)
$interim = ''
if (Test-Path $py) {
  try { $env:PYTHONIOENCODING = 'utf-8'; $interim = (& $py (Join-Path $repo 'scripts\perdim_interim_goals.py') 2>&1 | Out-String) }
  catch { $interim = "interim dashboard error: $_" }
  Add-Content -Path $interimLog -Value ("`n## {0}  state={1} progressAge={2}min restarted={3}`n``````n{4}``````" -f $now.ToString('u'), $state, $progressAge, $restarted, $interim.Trim())
}

# 4b) refresh the dip/valley training-data worklist as the exhaustive sweep grows (read-only)
if (Test-Path $py) {
  try {
    $env:PYTHONIOENCODING = 'utf-8'
    & $py (Join-Path $repo 'scripts\analyze_dips.py') --panel (Join-Path $repo 'reports\rich_lift\panel_perdim.jsonl') --out (Join-Path $ops 'harness_dips.md') *> $null
  } catch {}
}
$headline = (($interim -split "`n") | Where-Object { $_ -match 'lift ' } | Select-Object -First 1)
$headlineTrim = if ($headline) { $headline.Trim() } else { $null }

# 5) status file
[ordered]@{
  checked_at = $now.ToString('o'); state = $state; lock_pid = $lockPid; alive = $alive
  progress_age_min = $progressAge; progress_source = $progressSource
  progress_files = $progressSamples; coverage_heartbeat = $coverageHeartbeat
  stall_threshold_min = $StallMinutes
  restarted_this_pass = $restarted; last_restart = $lastRestart
  interim_headline = $headlineTrim
} | ConvertTo-Json -Depth 8 | ForEach-Object { [System.IO.File]::WriteAllText($statusFile, $_, (New-Object System.Text.UTF8Encoding($false))) }  # BOM-free so naive JSON readers (incl. the 6h check) parse it

"manage_flywheel: state=$state alive=$alive progressAge=${progressAge}min progressSource=$progressSource restarted=$restarted"
if ($headline) { "  interim: $($headline.Trim())" }
