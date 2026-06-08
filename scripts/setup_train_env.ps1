<#
.SYNOPSIS
  Build an isolated CUDA training environment (torch + transformers + peft + trl +
  bitsandbytes) OUTSIDE the OneDrive tree, for the local QLoRA MoE experiments in
  docs/research/moe_negative_result_experiment_design.md.

.DESCRIPTION
  Same rationale as recover_test_env.ps1 (OneDrive corrupts the system Python and any
  package cache it can reach), but this env carries the heavy GPU training stack and a
  model cache (HF_HOME) that MUST also live outside OneDrive or shard files get
  corrupted. Everything lives under %LOCALAPPDATA%\gemma4-trainenv (never synced).

  Steps:
    1. Ensure the standalone `uv` binary (PATH -> cached -> GitHub release).
    2. uv-managed CPython (intact stdlib), default 3.11 (broadest training-wheel support).
    3. Clean venv outside OneDrive.
    4. Install torch from the CUDA wheel index (default cu124), then the training stack.
    5. Point HF_HOME at %LOCALAPPDATA%\hf_home (outside OneDrive).
    6. Verify torch sees the GPU (torch.cuda.is_available() + device name + VRAM).

  Idempotent; -Regenerate nukes and rebuilds. Heavy (~2.5-3 GB torch download).

.PARAMETER Regenerate   Delete and rebuild the venv from scratch.
.PARAMETER PythonVersion  Managed CPython version (default 3.11).
.PARAMETER Cuda         torch CUDA wheel channel: cu124 (default) | cu121 | cpu.
.PARAMETER Verify       Only re-run the GPU verification on an existing venv.

.EXAMPLE
  powershell -ExecutionPolicy Bypass -File scripts/setup_train_env.ps1
  powershell -ExecutionPolicy Bypass -File scripts/setup_train_env.ps1 -Verify
#>
[CmdletBinding()]
param(
  [switch]$Regenerate,
  [string]$PythonVersion = "3.11",
  [ValidateSet("cu126", "cu124", "cu121", "cpu")][string]$Cuda = "cu126",
  [switch]$Verify
)

$ErrorActionPreference = "Stop"
$ProgressPreference = "SilentlyContinue"

function Info($m) { Write-Host "[train-env] $m" -ForegroundColor Cyan }
function Fail($m) { Write-Host "[train-env] ERROR: $m" -ForegroundColor Red; exit 1 }
function Invoke-Native {
  param([string]$Exe, [string[]]$CmdArgs, [string]$What)
  & $Exe @CmdArgs
  if ($LASTEXITCODE -ne 0) { Fail "$What failed (exit $LASTEXITCODE)" }
}

# Keep EVERYTHING outside the OneDrive-synced repo.
$EnvDir   = Join-Path $env:LOCALAPPDATA "gemma4-trainenv"
$UvDir    = Join-Path $EnvDir "uv"
$UvExe    = Join-Path $UvDir "uv.exe"
$VenvDir  = Join-Path $EnvDir "venv"
$VenvPy   = Join-Path $VenvDir "Scripts\python.exe"
$HfHome   = Join-Path $env:LOCALAPPDATA "hf_home"
New-Item -ItemType Directory -Force $EnvDir | Out-Null
New-Item -ItemType Directory -Force $HfHome | Out-Null

$verifyCode = @"
import torch
ok = torch.cuda.is_available()
print('[train-env] torch', torch.__version__, '| cuda build', torch.version.cuda, '| cuda available', ok)
if ok:
    i = torch.cuda.current_device()
    free, total = torch.cuda.mem_get_info(i)
    print('[train-env] GPU:', torch.cuda.get_device_name(i),
          '| VRAM total %.1f GB | free %.1f GB' % (total/1e9, free/1e9))
else:
    print('[train-env] WARNING: no CUDA device visible to torch (CPU-only).')
"@

if ($Verify) {
  if (-not (Test-Path $VenvPy)) { Fail "venv not found at $VenvPy -- run without -Verify first." }
  Invoke-Native $VenvPy @("-c", $verifyCode) "GPU verify"
  exit 0
}

# 1. uv
if (-not (Test-Path $UvExe)) {
  $onPath = Get-Command uv -ErrorAction SilentlyContinue
  if ($onPath) { $UvExe = $onPath.Source; Info "using uv on PATH: $UvExe" }
  else {
    Info "downloading standalone uv..."
    New-Item -ItemType Directory -Force $UvDir | Out-Null
    try {
      $rel = Invoke-RestMethod "https://api.github.com/repos/astral-sh/uv/releases/latest" -Headers @{ 'User-Agent' = 'gemma4-train-env' } -TimeoutSec 60
      $asset = $rel.assets | Where-Object { $_.name -eq 'uv-x86_64-pc-windows-msvc.zip' } | Select-Object -First 1
      if (-not $asset) { Fail "no uv windows asset in $($rel.tag_name)" }
      $zip = Join-Path $env:TEMP "uv-train-dl.zip"
      Invoke-WebRequest $asset.browser_download_url -OutFile $zip -TimeoutSec 180
      Expand-Archive $zip -DestinationPath $UvDir -Force
      Info "uv $($rel.tag_name) at $UvExe"
    } catch { Fail "uv download failed: $($_.Exception.Message)" }
  }
}

# 2. managed CPython
Info "ensuring managed CPython $PythonVersion..."
Invoke-Native $UvExe @("python", "install", $PythonVersion) "uv python install"

# 3. clean venv outside OneDrive
if ($Regenerate -and (Test-Path $VenvDir)) { Info "regenerate: removing $VenvDir"; Remove-Item $VenvDir -Recurse -Force }
if (-not (Test-Path $VenvPy)) {
  Info "creating venv at $VenvDir"
  Invoke-Native $UvExe @("venv", $VenvDir, "--python", $PythonVersion, "--python-preference", "only-managed") "uv venv"
}

# 4. torch from the CUDA wheel index, then the training stack from PyPI
if ($Cuda -eq "cpu") {
  Info "installing CPU-only torch (no GPU acceleration)"
  Invoke-Native $UvExe @("pip", "install", "--python", $VenvPy, "torch") "torch (cpu)"
} else {
  $idx = "https://download.pytorch.org/whl/$Cuda"
  Info "installing torch>=2.7 from $idx (heavy ~2.5 GB; >=2.7 needed for transformers 5.x fp8 dtypes)..."
  Invoke-Native $UvExe @("pip", "install", "--python", $VenvPy, "torch>=2.7", "--index-url", $idx) "torch ($Cuda)"
}
Info "installing training stack (transformers/peft/trl/accelerate/bitsandbytes/datasets)..."
Invoke-Native $UvExe @("pip", "install", "--python", $VenvPy,
  "transformers>=4.46", "peft>=0.13", "trl>=0.12", "accelerate>=1.0",
  "datasets>=3.0", "bitsandbytes>=0.44", "sentencepiece", "scipy", "numpy<2") "training stack"

# 5. HF cache outside OneDrive (write a tiny activate helper)
$activate = Join-Path $EnvDir "env.ps1"
@"
# dot-source to use the training env:  . `"$activate`"
`$env:HF_HOME = '$HfHome'
`$env:TRANSFORMERS_NO_ADVISORY_WARNINGS = '1'
Set-Alias trainpy '$VenvPy'
Write-Host '[train-env] HF_HOME=' `$env:HF_HOME '| python: $VenvPy'
"@ | Set-Content -Encoding UTF8 $activate
Info "wrote activate helper: $activate  (HF_HOME -> $HfHome)"

# 6. verify the GPU is visible
Info "verifying torch + GPU..."
$env:HF_HOME = $HfHome
Invoke-Native $VenvPy @("-c", $verifyCode) "GPU verify"

Info "done. Training python: $VenvPy"
Info "next:  . `"$activate`"   then run the QLoRA / routing scripts."
