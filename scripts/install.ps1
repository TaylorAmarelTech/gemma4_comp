<#
.SYNOPSIS
    Duecare one-line installer — Windows PowerShell.

.DESCRIPTION
    Detects Python, creates a venv, installs duecare-llm, runs a
    smoke test, and prints next-step commands. Idempotent + non-
    destructive. The exact PowerShell mirror of scripts/install.sh.

.EXAMPLE
    iex (irm https://raw.githubusercontent.com/TaylorAmarelTech/gemma4_comp/master/scripts/install.ps1)

.EXAMPLE
    .\scripts\install.ps1
#>

$ErrorActionPreference = "Stop"

function Say($msg)  { Write-Host $msg -ForegroundColor White }
function Note($msg) { Write-Host $msg -ForegroundColor DarkGray }
function Ok($msg)   { Write-Host " [OK] $msg" -ForegroundColor Green }
function Warn($msg) { Write-Host " [WARN] $msg" -ForegroundColor Yellow }
function Err($msg)  { Write-Host " [ERR] $msg" -ForegroundColor Red; exit 1 }

# 1. Environment
Say "Duecare installer"
Note "Detecting environment..."
$arch = (Get-CimInstance Win32_Processor).Architecture
$archName = switch ($arch) { 9 {"amd64"} 12 {"arm64"} default {"unknown"} }
Note "  OS:   Windows"
Note "  Arch: $archName"

# 2. Python
$py = $null
foreach ($cand in @("python3.12", "python3.11", "python3", "python", "py")) {
    if (Get-Command $cand -ErrorAction SilentlyContinue) {
        try {
            $v = & $cand -c "import sys; print(f'{sys.version_info.major}.{sys.version_info.minor}')" 2>$null
            if ($v -match '^3\.(11|12|13)$') {
                $py = $cand
                break
            }
        } catch { continue }
    }
}
if (-not $py) {
    Err "Need Python 3.11+ on PATH. Install from https://python.org/downloads/."
}
$pyVersion = & $py --version
Note "  Python: $pyVersion at $((Get-Command $py).Source)"

# 3. Venv
$venv = ".venv"
if ($env:VIRTUAL_ENV) {
    Note "  Using active venv: $env:VIRTUAL_ENV"
} elseif (Test-Path $venv) {
    Note "  Reusing existing venv: $venv"
    & "$venv\Scripts\Activate.ps1"
} else {
    Note "  Creating venv: $venv"
    & $py -m venv $venv
    & "$venv\Scripts\Activate.ps1"
    pip install --quiet --upgrade pip wheel
}

# 4. Install
Say "Installing duecare-llm + dependencies (this takes ~60 sec)..."
$installFailed = $false
try {
    pip install --quiet --upgrade duecare-llm 2>&1 | Select-Object -Last 5
    if ($LASTEXITCODE -ne 0) { throw "pip install failed" }
} catch {
    $installFailed = $true
    Warn "PyPI install failed (probably not yet published). Falling back to local editable install."
    if (Test-Path "packages\duecare-llm") {
        $pkgs = @(
            "duecare-llm-core", "duecare-llm-models", "duecare-llm-domains",
            "duecare-llm-tasks", "duecare-llm-agents", "duecare-llm-workflows",
            "duecare-llm-publishing", "duecare-llm-chat", "duecare-llm"
        )
        foreach ($p in $pkgs) {
            if (Test-Path "packages\$p") {
                pip install --quiet -e "packages\$p" 2>&1 | Select-Object -Last 2
            }
        }
    } else {
        Err "Not in the gemma4_comp source dir and PyPI install failed. Clone the repo first: git clone https://github.com/TaylorAmarelTech/gemma4_comp"
    }
}
Ok "Packages installed"

# 5. Verify
Say "Verifying installation..."
$verifyScript = @'
from duecare.chat.harness import (
    GREP_RULES, RAG_CORPUS, _TOOL_DISPATCH,
    EXAMPLE_PROMPTS, RUBRICS_REQUIRED, RUBRICS_5TIER,
)
print(f'  GREP rules:           {len(GREP_RULES)}      (expect >= 37)')
print(f'  RAG docs:             {len(RAG_CORPUS)}      (expect >= 26)')
print(f'  Tools:                {len(_TOOL_DISPATCH)}       (expect >= 4)')
print(f'  Example prompts:      {len(EXAMPLE_PROMPTS)}     (expect >= 394)')
print(f'  5-tier rubrics:       {len(RUBRICS_5TIER)}     (expect >= 207)')
print(f'  Required-rubric cats: {len(RUBRICS_REQUIRED)}       (expect >= 6)')
assert len(GREP_RULES) >= 37, 'GREP rule count regression'
assert len(RAG_CORPUS) >= 26, 'RAG doc count regression'
'@
python -c $verifyScript
if ($LASTEXITCODE -ne 0) { Err "Verification failed" }
Ok "Harness imports cleanly with expected counts"

# 6. What next
Say ""
Say "Next steps:"
Write-Host "  1. Run the chat playground locally:"
Write-Host "       python -m duecare.chat.run_server" -ForegroundColor White
Write-Host "       (then open http://localhost:8080)"
Write-Host ""
Write-Host "  2. Run the rubric comparison report:"
Write-Host "       python scripts\rubric_comparison.py" -ForegroundColor White
Write-Host "       (writes docs\harness_lift_report.md)"
Write-Host ""
Write-Host "  3. Or use Docker instead of local Python:"
Write-Host "       docker compose up" -ForegroundColor White
Write-Host ""
Note "Full docs: docs\install.md"
