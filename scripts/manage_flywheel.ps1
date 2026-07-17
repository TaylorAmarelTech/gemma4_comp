<#
.SYNOPSIS
  DueCare flywheel operations manager: detect + self-heal an engine that is running but
  STALLED (the known jam the 15-min -WatchdogRun does not catch, because it only replaces a
  DEAD lock pid), snapshot the large interim-goal dashboard, and write a status file.

  The existing DueCareAutonomousEngine watchdog handles dead-pid restarts. This manager is
  complementary: it only force-restarts when the lock pid is ALIVE but neither grading output
  file has advanced for -StallMinutes (a genuine hang, since healthy grading writes
  panel_perdim.jsonl every few seconds). Restarts are rate-limited and use the documented safe
  path (autonomous_engine.ps1 -Restart, which resumes checkpoints). Read-only with -CheckOnly.

.EXAMPLE
  pwsh scripts/manage_flywheel.ps1 -CheckOnly     # diagnose, never restart
  pwsh scripts/manage_flywheel.ps1                # manage: heal stalls, log interim, write status
#>
[CmdletBinding()]
param(
  [switch]$CheckOnly,
  [int]$StallMinutes = 40,
  [int]$MinRestartGapMinutes = 60
)
$ErrorActionPreference = 'Stop'
$repo = 'C:\Users\amare\OneDrive\Documents\gemma4_comp'
$ops = Join-Path $repo 'reports\ops'
if (-not (Test-Path $ops)) { New-Item -ItemType Directory -Force -Path $ops | Out-Null }
$statusFile = Join-Path $ops 'flywheel_status.json'
$interimLog = Join-Path $ops 'interim_log.md'
$manageLog  = Join-Path $ops 'manage.log'
$py = Join-Path $env:LOCALAPPDATA 'gemma4-testenv\venv\Scripts\python.exe'
$now = Get-Date

# 1) engine liveness (trust the lock PID being a live process, not the task state)
$lockFile = Join-Path $repo 'reports\autonomous_engine.lock'
$lockPid = $null; $alive = $false
if (Test-Path $lockFile) {
  $lockPid = ((Get-Content $lockFile -Raw) -split ',')[0].Trim()
  if ($lockPid) { $alive = [bool](Get-Process -Id ([int]$lockPid) -ErrorAction SilentlyContinue) }
}

# 2) progress freshness = minutes since the most-recent write to either grading output file
$ages = @()
foreach ($f in @('reports\rich_lift\results.jsonl', 'reports\rich_lift\panel_perdim.jsonl')) {
  $p = Join-Path $repo $f
  if (Test-Path $p) { $ages += (New-TimeSpan -Start (Get-Item $p).LastWriteTime -End $now).TotalMinutes }
}
$progressAge = if ($ages.Count) { [math]::Round((($ages | Measure-Object -Minimum).Minimum), 1) } else { 999999 }

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
  "$($now.ToString('u'))  STALL detected (progressAge=$progressAge min, pid=$lockPid alive) -> autonomous_engine.ps1 -Restart" | Add-Content -Path $manageLog
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
$headline = (($interim -split "`n") | Where-Object { $_ -match 'lift ' } | Select-Object -First 1)
$headlineTrim = if ($headline) { $headline.Trim() } else { $null }

# 5) status file
[ordered]@{
  checked_at = $now.ToString('o'); state = $state; lock_pid = $lockPid; alive = $alive
  progress_age_min = $progressAge; stall_threshold_min = $StallMinutes
  restarted_this_pass = $restarted; last_restart = $lastRestart
  interim_headline = $headlineTrim
} | ConvertTo-Json | Set-Content -Path $statusFile -Encoding utf8

"manage_flywheel: state=$state alive=$alive progressAge=${progressAge}min restarted=$restarted"
if ($headline) { "  interim: $($headline.Trim())" }
