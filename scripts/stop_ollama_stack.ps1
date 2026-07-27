<#
.SYNOPSIS
  Stop the DueCare model/flywheel stack to save costs without publishing anything by default.

.DESCRIPTION
  Writing only the engine stop sentinel is not enough: Hermes and OpenClaw can call a model
  independently, the orchestrator can stay resident, and the stall manager is a separate scheduled
  task. A durable cost stop therefore:
    1. writes stop sentinels for the engine, Hermes, OpenClaw, and the orchestrator,
    2. disables all five recurring DueCare tasks before process termination,
    3. verifies and stops only Python process trees running those four scripts from this repository,
    4. records a privacy-minimized status receipt under reports/.

  Board regeneration is optional with -CaptureBoard. A Git commit and push require the separate,
  explicit -PublishBoard switch; the unattended stop path never publishes repository changes.

  Used by the 30-day auto-stop (one-time task DueCareStop30Day) and runnable by hand to stop early
  (competition winners announced). Inspect without mutation using -Status. Reverse with -Resume,
  which removes the four sentinels and re-enables the recurring tasks but launches nothing directly.
#>
[CmdletBinding()]
param(
    [switch]$Resume,
    [switch]$Status,
    [switch]$CaptureBoard,
    [switch]$PublishBoard
)

$ErrorActionPreference = 'Stop'
$repo = Split-Path -Parent $PSScriptRoot
$reports = Join-Path $repo 'reports'
$sentinels = @(
    Join-Path $reports 'autonomous_engine.stop'
    Join-Path $reports 'hermes\hermes.stop'
    Join-Path $reports 'openclaw\openclaw.stop'
    Join-Path $reports 'orchestrator\orchestrator.stop'
)
$daemonScripts = @(
    Join-Path $repo 'scripts\autonomous_engine.py'
    Join-Path $repo 'scripts\hermes.py'
    Join-Path $repo 'scripts\openclaw_daemon.py'
    Join-Path $repo 'scripts\orchestrator.py'
)
$tasks = @(
    'DueCareAutonomousEngine'
    'DueCareHermes'
    'DueCareOpenClaw'
    'DueCareOrchestrator'
    'DueCareFlywheelManager'
)
$receipt = Join-Path $reports 'cost_stop_status.json'
$operationFailed = $false

if ($PublishBoard) { $CaptureBoard = $true }

function Assert-LastNativeSuccess {
    param([Parameter(Mandatory = $true)][string]$Operation)
    if ($LASTEXITCODE -ne 0) {
        throw "$Operation failed (exit $LASTEXITCODE)"
    }
}

function Get-RepositoryRelativePath {
    param(
        [Parameter(Mandatory = $true)][string]$Repository,
        [Parameter(Mandatory = $true)][string]$Path
    )
    $root = [IO.Path]::GetFullPath($Repository).TrimEnd('\')
    $full = [IO.Path]::GetFullPath($Path)
    $prefix = $root + '\'
    if (-not $full.StartsWith($prefix, [StringComparison]::OrdinalIgnoreCase)) {
        throw "path is outside the repository: $full"
    }
    return $full.Substring($prefix.Length).Replace('\', '/')
}

function Get-VerifiedRepositoryDaemonProcesses {
    param(
        [Parameter(Mandatory = $true)][string]$Repository,
        [Parameter(Mandatory = $true)][string[]]$ExpectedScripts
    )

    $expectedRepo = [IO.Path]::GetFullPath($Repository).TrimEnd('\')
    $normalizedScripts = @($ExpectedScripts | ForEach-Object { [IO.Path]::GetFullPath($_) })
    foreach ($expectedScript in $normalizedScripts) {
        if (-not $expectedScript.StartsWith($expectedRepo + '\', [StringComparison]::OrdinalIgnoreCase)) {
            throw "expected daemon path is outside the repository: $expectedScript"
        }
    }

    foreach ($process in @(Get-CimInstance -ClassName Win32_Process -ErrorAction Stop)) {
        if (-not $process.ExecutablePath -or -not $process.CommandLine) { continue }
        $actualPython = [IO.Path]::GetFullPath([string]$process.ExecutablePath)
        $pythonName = [IO.Path]::GetFileName($actualPython)
        if ($pythonName -notmatch '(?i)^python(?:\d+(?:\.\d+)*)?w?\.exe$') { continue }

        $pythonArg = '(?:"' + [regex]::Escape($actualPython) + '"|' + [regex]::Escape($actualPython) + ')'
        foreach ($expectedScript in $normalizedScripts) {
            $scriptArg = '(?:"' + [regex]::Escape($expectedScript) + '"|' + [regex]::Escape($expectedScript) + ')'
            $daemonCommand = '(?i)^\s*' + $pythonArg + '\s+' + $scriptArg + '(?:\s|$)'
            if ([regex]::IsMatch([string]$process.CommandLine, $daemonCommand)) {
                [pscustomobject][ordered]@{
                    process_id = [int]$process.ProcessId
                    parent_process_id = [int]$process.ParentProcessId
                    script = Get-RepositoryRelativePath -Repository $expectedRepo -Path $expectedScript
                }
                break
            }
        }
    }
}

function Get-CostStopState {
    $taskRows = @(
        foreach ($taskName in $tasks) {
            $task = Get-ScheduledTask -TaskName $taskName -ErrorAction SilentlyContinue
            [pscustomobject][ordered]@{
                name = $taskName
                exists = [bool]$task
                enabled = if ($task) { [bool]$task.Settings.Enabled } else { $null }
                state = if ($task) { [string]$task.State } else { 'missing' }
            }
        }
    )
    $sentinelRows = @(
        foreach ($path in $sentinels) {
            [pscustomobject][ordered]@{
                path = Get-RepositoryRelativePath -Repository $repo -Path $path
                exists = Test-Path -LiteralPath $path -PathType Leaf
            }
        }
    )
    $processRows = @(Get-VerifiedRepositoryDaemonProcesses -Repository $repo -ExpectedScripts $daemonScripts)
    $allTasksDisabled = @($taskRows | Where-Object { -not $_.exists -or $_.enabled }).Count -eq 0
    $allSentinelsPresent = @($sentinelRows | Where-Object { -not $_.exists }).Count -eq 0
    [pscustomobject][ordered]@{
        schema = 'duecare.cost-stop-status.v1'
        checked_at = (Get-Date).ToUniversalTime().ToString('o')
        cost_stop_active = $allTasksDisabled -and $allSentinelsPresent -and $processRows.Count -eq 0
        all_recurring_tasks_disabled = $allTasksDisabled
        all_stop_sentinels_present = $allSentinelsPresent
        verified_daemon_process_count = $processRows.Count
        tasks = $taskRows
        sentinels = $sentinelRows
        verified_daemon_processes = $processRows
    }
}

function Write-CostStopReceipt {
    param([Parameter(Mandatory = $true)]$State)
    $json = $State | ConvertTo-Json -Depth 8
    [IO.File]::WriteAllText($receipt, $json + [Environment]::NewLine, (New-Object Text.UTF8Encoding($false)))
}

if ($Status) {
    $state = Get-CostStopState
    $state | ConvertTo-Json -Depth 8
    if (-not $state.cost_stop_active) {
        throw "DueCare cost stop is incomplete"
    }
    return
}

if ($Resume) {
    foreach ($sentinel in $sentinels) {
        if (Test-Path -LiteralPath $sentinel) { Remove-Item -LiteralPath $sentinel -Force }
    }
    foreach ($t in $tasks) {
        try { Enable-ScheduledTask -TaskName $t -ErrorAction Stop | Out-Null; "enabled $t" }
        catch { $operationFailed = $true; "could not enable $t : $($_.Exception.Message)" }
    }
    if ($operationFailed) {
        throw "DueCare stack resume was incomplete; see task errors above"
    }
    "DueCare stack RE-ENABLED at $(Get-Date -Format o); no process was launched directly."
    return
}

# The mutating stop path starts here. Keep -Status and -Resume free of report
# directory creation so status remains read-only and resume only changes the
# documented sentinels/tasks.
New-Item -ItemType Directory -Force -Path $reports | Out-Null

# 1. Write every daemon sentinel first so no new work starts during shutdown.
foreach ($sentinel in $sentinels) {
    New-Item -ItemType Directory -Force -Path (Split-Path $sentinel) | Out-Null
    Set-Content -LiteralPath $sentinel -Value "DueCare cost stop $(Get-Date -Format o)" -Encoding utf8
    "wrote stop sentinel: $(Get-RepositoryRelativePath -Repository $repo -Path $sentinel)"
}

# 2. Disable every recurring task before terminating live processes, closing the relaunch race.
foreach ($t in $tasks) {
    try { Disable-ScheduledTask -TaskName $t -ErrorAction Stop | Out-Null; "disabled $t" }
    catch { $operationFailed = $true; "could not disable $t : $($_.Exception.Message)" }
}

# 3. Stop only verified process trees running the four exact repository daemon scripts.
try {
    $verified = @(Get-VerifiedRepositoryDaemonProcesses -Repository $repo -ExpectedScripts $daemonScripts)
    $verifiedIds = @($verified | ForEach-Object { [int]$_.process_id })
    $roots = @($verified | Where-Object { $verifiedIds -notcontains [int]$_.parent_process_id })
    foreach ($rootProcess in $roots) {
        & taskkill /PID $rootProcess.process_id /T /F 2>$null | Out-Null
        Assert-LastNativeSuccess "taskkill for verified $($rootProcess.script) PID $($rootProcess.process_id)"
        "stopped verified daemon tree pid=$($rootProcess.process_id) script=$($rootProcess.script)"
    }
} catch {
    $operationFailed = $true
    "verified daemon termination incomplete: $($_.Exception.Message)"
}

# 4. Optionally capture the board. Default and unattended stops do not modify tracked files.
if ($CaptureBoard) { try {
    $py = Join-Path $env:LOCALAPPDATA 'gemma4-testenv\venv\Scripts\python.exe'
    if (-not (Test-Path -LiteralPath $py)) {
        $py = (Get-Command python -CommandType Application -ErrorAction Stop | Select-Object -First 1).Source
    }
    Push-Location $repo
    $locationPushed = $true
    & $py (Join-Path $repo 'scripts\benchmark_leaderboard.py') 2>&1 | Out-Null
    Assert-LastNativeSuccess "benchmark leaderboard generation"
    $boardPaths = @(
        'apps/duecare-ai.com/app/static/benchmark_leaderboard.json',
        'docs/research/benchmark_leaderboard.md',
        'docs/research/rich_harness_lift_100.md'
    )
    $boardStatus = @(& git status --porcelain -- @boardPaths 2>$null)
    Assert-LastNativeSuccess "git status for final board paths"
    if ($boardStatus.Count -eq 0) {
        "regenerated final board; no board changes to commit"
    } elseif (-not $PublishBoard) {
        "regenerated final board; tracked changes were left uncommitted for review"
    } else {
        $branchDelta = ((& git rev-list --left-right --count 'HEAD...@{upstream}' 2>$null) -join '').Trim()
        Assert-LastNativeSuccess "git upstream comparison before final board commit"
        $deltaParts = @($branchDelta -split '\s+' | Where-Object { $_ })
        if ($deltaParts.Count -ne 2 -or $deltaParts[0] -ne '0' -or $deltaParts[1] -ne '0') {
            throw "refusing automatic board commit/push because the branch is not synchronized with upstream ($branchDelta)"
        }
        & git commit --only -m "chore(benchmark): final board at cost-stop (30-day cap / early stop)" `
            -- @boardPaths 2>$null | Out-Null
        Assert-LastNativeSuccess "git commit for final board paths"
        & git push 2>$null | Out-Null
        Assert-LastNativeSuccess "git push for final board commit"
        "regenerated, committed, and pushed final board from the accumulated panel"
    }
} catch {
    $operationFailed = $true
    "board capture/publish incomplete: $($_.Exception.Message)"
} finally {
    if ($locationPushed) { Pop-Location }
}
} else {
    "board capture skipped (default); use -CaptureBoard, plus -PublishBoard only after review"
}

# 5. Record and verify a privacy-minimized receipt. Reports and checkpoints remain untouched.
try {
    $finalState = Get-CostStopState
    Write-CostStopReceipt -State $finalState
    "wrote cost-stop receipt: reports/cost_stop_status.json"
    if (-not $finalState.cost_stop_active) {
        $operationFailed = $true
        "cost-stop verification is incomplete"
    }
} catch {
    $operationFailed = $true
    "cost-stop receipt/verification failed: $($_.Exception.Message)"
}

if ($operationFailed) {
    throw "DueCare stop actions completed with errors; all written stop sentinels remain in place"
}
"DueCare model/flywheel stack STOPPED at $(Get-Date -Format o) -- recurring callers disabled and verified daemons stopped. Resume explicitly with: scripts\stop_ollama_stack.ps1 -Resume"
