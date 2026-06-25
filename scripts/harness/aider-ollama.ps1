#requires -Version 5.1
<#
.SYNOPSIS
  DueCare coding harness — Aider driven by Ollama-cloud GLM 5.2 (architect) + Kimi K2.6 (editor).

.DESCRIPTION
  No Claude / no Anthropic. Reads OLLAMA_API_KEY from the repo .env and targets the Ollama
  cloud OpenAI-compatible endpoint. Model selection + behavior live in .aider.conf.yml.

.EXAMPLE
  .\scripts\harness\aider-ollama.ps1
  .\scripts\harness\aider-ollama.ps1 path\to\file.py
  .\scripts\harness\aider-ollama.ps1 --message "implement X" file.py
#>
$ErrorActionPreference = 'Stop'
$repo = Split-Path -Parent (Split-Path -Parent $PSScriptRoot)
$envFile = Join-Path $repo '.env'

# Parse OLLAMA_API_KEY (+ optional OLLAMA_OPENAI_BASE) from the repo .env. We do NOT
# blanket-export every var, because .env also holds a real OPENAI_API_KEY.
$ollamaKey = $null
$base = 'https://ollama.com/v1'
if (Test-Path $envFile) {
  foreach ($line in Get-Content $envFile) {
    if ($line -match '^\s*#' -or $line -notmatch '=') { continue }
    $idx = $line.IndexOf('=')
    if ($idx -lt 1) { continue }
    $k = $line.Substring(0, $idx).Trim()
    $v = $line.Substring($idx + 1).Trim().Trim('"').Trim("'")
    switch ($k) {
      'OLLAMA_API_KEY'     { $ollamaKey = $v }
      'OLLAMA_OPENAI_BASE' { if ($v) { $base = $v } }
    }
  }
}
if (-not $ollamaKey) { throw "OLLAMA_API_KEY not set — add it to $envFile" }

# Aider auto-loads the repo .env (with its real OPENAI_API_KEY → 401). Hand it a
# private temp env-file via --env-file so the Ollama key wins. Removed in finally.
$envTmp = [System.IO.Path]::GetTempFileName()
try {
  Set-Content -Path $envTmp -Encoding ascii -Value @(
    "OPENAI_API_BASE=$base",
    "OPENAI_API_KEY=$ollamaKey"
  )
  $env:PYTHONUTF8 = '1'
  $env:PYTHONIOENCODING = 'utf-8'

  # Keep Aider's history out of the repo root (the root-file policy test globs *.md).
  $aiderDir = Join-Path $repo '.aider'
  New-Item -ItemType Directory -Force -Path $aiderDir | Out-Null
  $histArgs = @(
    '--chat-history-file',  (Join-Path $aiderDir 'chat.history.md'),
    '--input-history-file', (Join-Path $aiderDir 'input.history'),
    '--llm-history-file',   (Join-Path $aiderDir 'llm.history')
  )

  # Swap roles without editing .aider.conf.yml, e.g.:
  #   $env:DUECARE_ARCHITECT='kimi-k2.6'; $env:DUECARE_EDITOR='glm-5.2'; .\scripts\harness\aider-ollama.ps1 ...
  $roleArgs = @()
  if ($env:DUECARE_ARCHITECT) { $roleArgs += @('--model',        ('openai/' + ($env:DUECARE_ARCHITECT -replace '^openai/',''))) }
  if ($env:DUECARE_EDITOR)    { $roleArgs += @('--editor-model', ('openai/' + ($env:DUECARE_EDITOR -replace '^openai/',''))) }

  $aider = if ($env:AIDER_BIN) { $env:AIDER_BIN } else { Join-Path $env:USERPROFILE '.local\bin\aider.exe' }
  if (-not (Test-Path $aider)) { $aider = 'aider' }   # fall back to PATH
  & $aider --env-file $envTmp @histArgs @roleArgs @args
}
finally {
  Remove-Item $envTmp -Force -ErrorAction SilentlyContinue
}
