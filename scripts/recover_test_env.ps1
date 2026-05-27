<#
.SYNOPSIS
  Build / recover an isolated, uncorrupted Python interpreter for this repo
  and (optionally) run the grading test suite in it.

.DESCRIPTION
  This repo lives under a OneDrive-synced path. OneDrive sync intermittently
  CORRUPTS the system Python install -- it strips files from site-packages AND
  from the standard library (observed missing: typing_extensions, the compiled
  pydantic_core .pyd, pydantic.main, html.entities). Once the stdlib is
  Swiss-cheesed, the system interpreter cannot import the app or run pytest,
  and shadowing individual packages cannot repair it.

  This script sidesteps the corruption end-to-end:
    1. Ensures the standalone `uv` binary is available (downloads it from the
       official GitHub release if missing). uv does NOT depend on the broken
       system pip.
    2. Has uv download a fresh, MANAGED CPython (intact standard library) --
       never the corrupted system Python.
    3. Creates a clean venv OUTSIDE the OneDrive tree (in %LOCALAPPDATA%, which
       is never synced, so OneDrive cannot re-corrupt it) and installs the
       known-working pinned dependencies from requirements-testenv.txt.
    4. Verifies the interpreter imports a stdlib module the corruption ate
       (html.entities) plus the fastapi/pydantic stack.
    5. With -Run, executes the grading test suite with the duecare PEP 420
       namespace package src roots on PYTHONPATH.

  This is idempotent: re-run any time. -Regenerate nukes and rebuilds the venv
  when it has itself been corrupted. The interpreter, uv, and managed CPython
  all live under %LOCALAPPDATA%\gemma4-testenv, nothing is written into the
  synced repo, and everything can be redownloaded from scratch.

.PARAMETER Regenerate
  Delete and rebuild the venv from scratch (use when it has been corrupted).

.PARAMETER Run
  After setup, run the grading test suite and exit with pytest's code.

.PARAMETER PythonVersion
  CPython version for the managed interpreter (default 3.12).

.PARAMETER Tests
  Override the default grading test paths (array of pytest targets).

.EXAMPLE
  pwsh scripts/recover_test_env.ps1                 # build / refresh the env
  pwsh scripts/recover_test_env.ps1 -Run            # build + run grading tests
  pwsh scripts/recover_test_env.ps1 -Regenerate -Run  # rebuild from scratch + run
#>
[CmdletBinding()]
param(
  [switch]$Regenerate,
  [switch]$Run,
  [string]$PythonVersion = "3.12",
  [string[]]$Tests
)

$ErrorActionPreference = "Stop"
$ProgressPreference = "SilentlyContinue"

function Info($m) { Write-Host "[recover-env] $m" -ForegroundColor Cyan }
function Fail($m) { Write-Host "[recover-env] ERROR: $m" -ForegroundColor Red; exit 1 }
# Native commands do not throw on non-zero exit under $ErrorActionPreference;
# check $LASTEXITCODE explicitly after each uv call.
function Invoke-Native {
  # NB: do not name the array param $Args -- that collides with the
  # automatic $args variable and the splat silently expands to nothing.
  param([string]$Exe, [string[]]$CmdArgs, [string]$What)
  & $Exe @CmdArgs
  if ($LASTEXITCODE -ne 0) { Fail "$What failed (exit $LASTEXITCODE)" }
}

# Repo root = parent of this script's directory.
$RepoRoot = Split-Path -Parent $PSScriptRoot
$Reqs = Join-Path $RepoRoot "requirements-testenv.txt"
if (-not (Test-Path $Reqs)) { Fail "requirements-testenv.txt not found at $Reqs" }

# Keep EVERYTHING outside the OneDrive-synced repo so sync cannot corrupt it.
$EnvDir  = Join-Path $env:LOCALAPPDATA "gemma4-testenv"
$UvDir   = Join-Path $EnvDir "uv"
$UvExe   = Join-Path $UvDir "uv.exe"
$VenvDir = Join-Path $EnvDir "venv"
$VenvPy  = Join-Path $VenvDir "Scripts\python.exe"
New-Item -ItemType Directory -Force $EnvDir | Out-Null

# 1. Ensure uv (prefer one already on PATH; else our cached copy; else fetch).
if (-not (Test-Path $UvExe)) {
  $onPath = Get-Command uv -ErrorAction SilentlyContinue
  if ($onPath) {
    $UvExe = $onPath.Source
    Info "using uv on PATH: $UvExe"
  } else {
    Info "downloading standalone uv from GitHub release..."
    New-Item -ItemType Directory -Force $UvDir | Out-Null
    try {
      $rel = Invoke-RestMethod "https://api.github.com/repos/astral-sh/uv/releases/latest" -Headers @{ 'User-Agent' = 'gemma4-recover-env' } -TimeoutSec 60
      $asset = $rel.assets | Where-Object { $_.name -eq 'uv-x86_64-pc-windows-msvc.zip' } | Select-Object -First 1
      if (-not $asset) { Fail "could not find uv windows asset in release $($rel.tag_name)" }
      $zip = Join-Path $env:TEMP "uv-recover-dl.zip"
      Invoke-WebRequest $asset.browser_download_url -OutFile $zip -TimeoutSec 180
      Expand-Archive $zip -DestinationPath $UvDir -Force
      Info "uv $($rel.tag_name) installed at $UvExe"
    } catch {
      Fail "uv download failed: $($_.Exception.Message). Install uv manually (https://docs.astral.sh/uv/) and re-run."
    }
  }
}

# 2. Managed CPython with an intact stdlib (NEVER the corrupted system one).
Info "ensuring managed CPython $PythonVersion (intact stdlib)..."
Invoke-Native $UvExe @("python", "install", $PythonVersion) "uv python install"

# 3. Clean venv outside OneDrive + known-working pinned deps.
if ($Regenerate -and (Test-Path $VenvDir)) {
  Info "regenerate: removing $VenvDir"
  Remove-Item $VenvDir -Recurse -Force
}
if (-not (Test-Path $VenvPy)) {
  Info "creating clean venv at $VenvDir"
  Invoke-Native $UvExe @("venv", $VenvDir, "--python", $PythonVersion, "--python-preference", "only-managed") "uv venv"
}
Info "installing pinned deps from requirements-testenv.txt"
Invoke-Native $UvExe @("pip", "install", "--python", $VenvPy, "-r", $Reqs) "uv pip install"

# 4. Verify the interpreter (stdlib module the corruption ate + the stack).
Info "verifying clean interpreter..."
Invoke-Native $VenvPy @("-c", "import html.entities; from fastapi.testclient import TestClient; import pydantic; print('[recover-env] clean interpreter OK; pydantic ' + pydantic.VERSION)") "interpreter verify"

# 5. Optionally run the grading test suite.
if ($Run) {
  # duecare is a PEP 420 namespace spread across packages/*/src -- put every
  # such src root on PYTHONPATH so the namespace resolves without an install.
  $srcRoots = Get-ChildItem (Join-Path $RepoRoot "packages") -Directory |
    ForEach-Object { Join-Path $_.FullName "src" } |
    Where-Object { Test-Path $_ }
  $env:PYTHONPATH = ($srcRoots -join ";")

  if (-not $Tests) {
    $Tests = @(
      "packages/duecare-llm-chat/tests/test_compare.py",
      "packages/duecare-llm-chat/tests/test_harness_behavior.py",
      "packages/duecare-llm-chat/tests/test_harness_v3_6.py",
      "packages/duecare-llm-chat/tests/test_benchmark.py",
      "packages/duecare-llm-chat/tests/test_design_tooltip_migration.py",
      "tests/test_route_contract.py"
    )
  }
  Info "running grading tests on the clean interpreter..."
  Push-Location $RepoRoot
  try {
    & $VenvPy -m pytest @Tests --timeout=180 -p no:cacheprovider -q
    $code = $LASTEXITCODE
  } finally { Pop-Location }
  Info "pytest exit code: $code"
  exit $code
}

Info "done. Interpreter: $VenvPy"
Info "run the grading suite with:  pwsh scripts/recover_test_env.ps1 -Run"
