<#
.SYNOPSIS
Safely refresh and optionally publish DueCare's durable data archive.

.DESCRIPTION
Dry-run is the default. A dry-run validates the repository/branch, the existing
archive manifest allowlist, and every archived checksum without writing files.

Use -Refresh to run scripts/durable_archive.py locally and verify the resulting
archive. Use -Publish for the only network-writing mode: it implies -Refresh,
creates an orphan commit through an isolated temporary Git index, proves that
the commit contains only the verified archive files, and updates only
refs/heads/data-archive on origin with an exact force-with-lease expectation.
It never changes the current branch, normal Git index, or working-tree files
outside archive/.

The selected source allowlist is intentionally narrow: the full prompt set,
judge panels, optional generated responses, autonomous-run ledger, and curated
training JSON/JSONL artifacts. The existing durable_archive.py content gate
rejects populated direct-identifier fields; this wrapper independently rejects
credential, secret, log, raw-case, cache, adapter, and weight paths.

.PARAMETER RepositoryRoot
Repository to validate. Defaults to the parent of this script's scripts folder.

.PARAMETER PythonExecutable
Python executable used for scripts/durable_archive.py. Defaults to python.

.PARAMETER Refresh
Refresh archive/ locally, then verify every entry. No commit or push is made.

.PARAMETER IncludeResponses
Include reports/rich_lift/results.jsonl. This large, volatile response payload
is opt-in and must be explicitly allowed on every refresh/publish that carries it.

.PARAMETER Publish
After refresh and verification, replace origin/data-archive using an orphan
snapshot commit and --force-with-lease. This is the only publishing switch.

.EXAMPLE
pwsh scripts/refresh_durable_archive.ps1

Read-only validation and plan. This is what running the script with no switches does.

.EXAMPLE
pwsh scripts/refresh_durable_archive.ps1 -Refresh -IncludeResponses

Refresh and verify a complete local snapshot, including generated responses.

.EXAMPLE
pwsh scripts/refresh_durable_archive.ps1 -Publish -IncludeResponses

Explicitly refresh, verify, and publish only origin/data-archive.
#>
[CmdletBinding()]
param(
    [string]$RepositoryRoot = "",
    [string]$PythonExecutable = "python",
    [switch]$Refresh,
    [switch]$IncludeResponses,
    [switch]$Publish
)

Set-StrictMode -Version Latest
$ErrorActionPreference = "Stop"

$RequiredSourceBranch = "master"
$ArchiveBranch = "data-archive"
$ArchiveRemote = "origin"
$ExpectedRepositorySlug = "TaylorAmarelTech/gemma4_comp"
$ArchiveManifestRelative = "archive/manifest.json"
$ArchiveReadmeRelative = "archive/README.md"
$ResponseSource = "reports/rich_lift/results.jsonl"

function Get-CanonicalPath {
    param([Parameter(Mandatory = $true)][string]$Path)
    return [IO.Path]::GetFullPath($Path).TrimEnd([char[]]@('\', '/'))
}

function Test-SamePath {
    param(
        [Parameter(Mandatory = $true)][string]$Left,
        [Parameter(Mandatory = $true)][string]$Right
    )
    $comparison = [StringComparison]::Ordinal
    if ($env:OS -eq "Windows_NT") {
        $comparison = [StringComparison]::OrdinalIgnoreCase
    }
    return [string]::Equals((Get-CanonicalPath $Left), (Get-CanonicalPath $Right), $comparison)
}

function Assert-PathWithin {
    param(
        [Parameter(Mandatory = $true)][string]$Child,
        [Parameter(Mandatory = $true)][string]$Parent,
        [Parameter(Mandatory = $true)][string]$Label
    )
    $childPath = Get-CanonicalPath $Child
    $parentPath = Get-CanonicalPath $Parent
    $comparison = [StringComparison]::Ordinal
    if ($env:OS -eq "Windows_NT") {
        $comparison = [StringComparison]::OrdinalIgnoreCase
    }
    $prefix = $parentPath + [IO.Path]::DirectorySeparatorChar
    if (-not $childPath.StartsWith($prefix, $comparison)) {
        throw "$Label resolves outside the approved directory."
    }
}

function Invoke-NativeChecked {
    param(
        [Parameter(Mandatory = $true)][string]$FilePath,
        [Parameter(Mandatory = $true)][string[]]$Arguments,
        [switch]$Capture
    )
    $output = @(& $FilePath @Arguments 2>&1)
    $exitCode = $LASTEXITCODE
    if ($exitCode -ne 0) {
        foreach ($line in $output) {
            Write-Host ([string]$line)
        }
        throw "$FilePath failed with exit code $exitCode."
    }
    if ($Capture) {
        return (($output | ForEach-Object { [string]$_ }) -join "`n").Trim()
    }
    foreach ($line in $output) {
        Write-Host ([string]$line)
    }
}

function Invoke-GitChecked {
    param(
        [Parameter(Mandatory = $true)][string[]]$Arguments,
        [switch]$Capture
    )
    $allArguments = @("-C", $script:RepoRoot) + $Arguments
    return Invoke-NativeChecked -FilePath $script:GitExecutable -Arguments $allArguments -Capture:$Capture
}

function Resolve-RepositoryContext {
    $candidate = $RepositoryRoot
    if ([string]::IsNullOrWhiteSpace($candidate)) {
        $candidate = Join-Path $PSScriptRoot ".."
    }
    $resolved = (Resolve-Path -LiteralPath $candidate).Path

    $gitCommand = Get-Command git -ErrorAction Stop
    $script:GitExecutable = $gitCommand.Source
    $script:RepoRoot = Get-CanonicalPath $resolved

    $topLevel = Invoke-GitChecked -Arguments @("rev-parse", "--show-toplevel") -Capture
    if (-not (Test-SamePath $topLevel $script:RepoRoot)) {
        throw "RepositoryRoot must be the exact Git top-level directory."
    }

    $branch = Invoke-GitChecked -Arguments @("symbolic-ref", "--quiet", "--short", "HEAD") -Capture
    if ($branch -ne $RequiredSourceBranch) {
        throw "Refusing to run from branch '$branch'; required source branch is '$RequiredSourceBranch'."
    }

    $remote = Invoke-GitChecked -Arguments @("remote", "get-url", $ArchiveRemote) -Capture
    if ([string]::IsNullOrWhiteSpace($remote)) {
        throw "Required Git remote '$ArchiveRemote' is not configured."
    }
    $expectedRemotePattern = '^(?:https://(?:[^/@]+@)?github\.com/|git@github\.com:|ssh://git@github\.com/)' +
        [regex]::Escape($ExpectedRepositorySlug) + '(?:\.git)?/?$'
    if ($remote -notmatch $expectedRemotePattern) {
        throw "Remote '$ArchiveRemote' is not the approved $ExpectedRepositorySlug repository."
    }

    $script:DurableArchive = Join-Path $script:RepoRoot "scripts/durable_archive.py"
    if (-not (Test-Path -LiteralPath $script:DurableArchive -PathType Leaf)) {
        throw "Missing scripts/durable_archive.py in the verified repository."
    }
    $pythonCommand = Get-Command $PythonExecutable -ErrorAction Stop
    $script:PythonPath = $pythonCommand.Source

    $script:ArchiveRoot = Join-Path $script:RepoRoot "archive"
    $script:ManifestPath = Join-Path $script:RepoRoot ($ArchiveManifestRelative -replace '/', [IO.Path]::DirectorySeparatorChar)
    $script:ReadmePath = Join-Path $script:RepoRoot ($ArchiveReadmeRelative -replace '/', [IO.Path]::DirectorySeparatorChar)
    Assert-PathWithin -Child $script:ManifestPath -Parent $script:RepoRoot -Label "archive manifest"
}

function Test-AllowedSourcePath {
    param([Parameter(Mandatory = $true)][string]$Path)
    $normal = $Path.Replace('\', '/')
    if ($normal -match '(^|/)(?:\.env(?:\.|$)|credentials?|secrets?|tokens?|api[_-]?keys?|logs?|raw[_-]?cases?|case[_-]?files?|pii|drive_[^/]*|_reference|curation_cache|adapters?|weights?)(?:/|$)') {
        return $false
    }
    if ($normal -match '(^|/)[^/]*(?:credentials?|secrets?|tokens?|api[_-]?keys?|logs?|raw[_-]?cases?|case[_-]?files?|pii|private[_-]?keys?|drive_[a-z0-9_-]*|_reference|curation_cache|adapters?|weights?)[^/]*(?:/|$)') {
        return $false
    }
    if ($normal -match '\.(?:log|key|pem|p12|pfx|safetensors|gguf|bin|pt|onnx|parquet|arrow)$') {
        return $false
    }
    if ($normal -eq "reports/benchmark/full_promptset.json") {
        return $true
    }
    if ($normal -eq "reports/autonomous_engine_state.json") {
        return $true
    }
    if ($normal -eq $ResponseSource) {
        return $true
    }
    if ($normal -eq "reports/rich_lift/panel_perdim.coverage.json") {
        return $true
    }
    if ($normal -eq "reports/rich_lift/panel_perdim.jsonl.components.sqlite3") {
        return $true
    }
    if ($normal -match '^reports/rich_lift/panel(?:_[a-z0-9._-]+)?\.jsonl$') {
        return $true
    }
    if ($normal -match '^reports/multi_judge/(?:perdim_)?panel\.jsonl$') {
        return $true
    }
    # Curated training rows, metadata manifests, quality audits, and the append-only
    # fine-tune registry all stay behind durable_archive.py's JSON content-safety gate.
    if ($normal -match '^reports/training/[a-z0-9][a-z0-9._-]*\.(?:json|jsonl)$') {
        return $true
    }
    return $false
}

function Read-ArchiveManifest {
    if (-not (Test-Path -LiteralPath $script:ManifestPath -PathType Leaf)) {
        throw "Archive manifest is missing. Use -Refresh to create it."
    }
    try {
        $manifest = Get-Content -LiteralPath $script:ManifestPath -Raw | ConvertFrom-Json
    }
    catch {
        throw "Archive manifest is not valid JSON."
    }
    if ($null -eq $manifest -or $null -eq $manifest.files) {
        throw "Archive manifest must contain a files array."
    }
    return $manifest
}

function Assert-ArchiveManifestScope {
    param(
        [Parameter(Mandatory = $true)]$Manifest,
        [switch]$AllowResponses
    )
    $sourcePaths = New-Object 'System.Collections.Generic.HashSet[string]' ([StringComparer]::Ordinal)
    $chunkPaths = New-Object 'System.Collections.Generic.HashSet[string]' ([StringComparer]::Ordinal)
    foreach ($entry in @($Manifest.files)) {
        $source = ([string]$entry.path).Replace('\', '/')
        if ([string]::IsNullOrWhiteSpace($source) -or $source.Contains("..") -or $source.StartsWith("/")) {
            throw "Archive manifest contains an unsafe source path."
        }
        if (-not (Test-AllowedSourcePath $source)) {
            throw "Archive manifest source is outside the sanitized allowlist: $source"
        }
        if ($source -eq $ResponseSource -and -not $AllowResponses) {
            throw "The response payload is present; rerun with -IncludeResponses to approve it explicitly."
        }
        if (-not $sourcePaths.Add($source)) {
            throw "Archive manifest contains duplicate source paths."
        }
        if ([string]$entry.sha256 -notmatch '^[0-9a-f]{64}$') {
            throw "Archive manifest contains an invalid source checksum."
        }
        if ([int64]$entry.bytes -lt 0 -or [int64]$entry.compressed_bytes -lt 0) {
            throw "Archive manifest contains an invalid byte count."
        }
        $chunks = @($entry.chunks)
        if ($chunks.Count -lt 1) {
            throw "Archive manifest source has no chunks: $source"
        }
        $sourcePattern = '^' + [regex]::Escape($source) + '(?:\.[0-9a-f]{16})?\.gz\.[0-9]{3}$'
        foreach ($chunkValue in $chunks) {
            $chunk = ([string]$chunkValue).Replace('\', '/')
            if ($chunk -notmatch $sourcePattern -or $chunk.Contains("..") -or $chunk.StartsWith("/")) {
                throw "Archive manifest contains an unsafe or mismatched chunk path."
            }
            if (-not $chunkPaths.Add($chunk)) {
                throw "Archive manifest contains a duplicate chunk path."
            }
            $chunkPath = Join-Path $script:ArchiveRoot ($chunk -replace '/', [IO.Path]::DirectorySeparatorChar)
            Assert-PathWithin -Child $chunkPath -Parent $script:ArchiveRoot -Label "archive chunk"
            if (-not (Test-Path -LiteralPath $chunkPath -PathType Leaf)) {
                throw "Archive manifest references a missing chunk: $chunk"
            }
        }
    }
    return $chunkPaths
}

function Invoke-ArchiveVerification {
    Invoke-NativeChecked -FilePath $script:PythonPath -Arguments @($script:DurableArchive, "--verify")
}

function Invoke-ArchiveRefresh {
    $arguments = @($script:DurableArchive)
    if ($IncludeResponses) {
        $arguments += "--include-large"
    }
    Invoke-NativeChecked -FilePath $script:PythonPath -Arguments $arguments
    Invoke-ArchiveVerification
    $manifest = Read-ArchiveManifest
    $null = Assert-ArchiveManifestScope -Manifest $manifest -AllowResponses:$IncludeResponses
    return $manifest
}

function Get-ExpectedArchiveTreePaths {
    param([Parameter(Mandatory = $true)]$Manifest)
    $paths = New-Object 'System.Collections.Generic.HashSet[string]' ([StringComparer]::Ordinal)
    $null = $paths.Add($ArchiveManifestRelative)
    $null = $paths.Add($ArchiveReadmeRelative)
    foreach ($entry in @($Manifest.files)) {
        foreach ($chunk in @($entry.chunks)) {
            $null = $paths.Add("archive/" + ([string]$chunk).Replace('\', '/'))
        }
    }
    return @($paths | Sort-Object)
}

function New-VerifiedArchiveCommit {
    param([Parameter(Mandatory = $true)]$Manifest)
    if (-not (Test-Path -LiteralPath $script:ReadmePath -PathType Leaf)) {
        throw "Archive README is missing after refresh."
    }
    $expected = @(Get-ExpectedArchiveTreePaths -Manifest $Manifest)
    foreach ($relative in $expected) {
        $full = Join-Path $script:RepoRoot ($relative -replace '/', [IO.Path]::DirectorySeparatorChar)
        Assert-PathWithin -Child $full -Parent $script:RepoRoot -Label "archive publication path"
        if (-not (Test-Path -LiteralPath $full -PathType Leaf)) {
            throw "Verified archive publication file is missing: $relative"
        }
    }

    $tempDirectory = Join-Path ([IO.Path]::GetTempPath()) ("duecare-data-archive-" + [Guid]::NewGuid().ToString("N"))
    $null = New-Item -ItemType Directory -Path $tempDirectory
    $indexPath = Join-Path $tempDirectory "index"
    $oldIndex = $env:GIT_INDEX_FILE
    try {
        $env:GIT_INDEX_FILE = $indexPath
        Invoke-GitChecked -Arguments @("read-tree", "--empty")
        foreach ($relative in $expected) {
            Invoke-GitChecked -Arguments @("add", "-f", "--", $relative)
        }
        $tree = Invoke-GitChecked -Arguments @("write-tree") -Capture
        if ($tree -notmatch '^[0-9a-f]{40,64}$') {
            throw "Git did not produce a valid archive tree object."
        }
        $generated = ([string]$Manifest.generated) -replace '[^0-9A-Za-z:_.+\-Z]', '_'
        $commit = Invoke-GitChecked -Arguments @("commit-tree", $tree, "-m", "chore(data): durable archive snapshot $generated") -Capture
        if ($commit -notmatch '^[0-9a-f]{40,64}$') {
            throw "Git did not produce a valid orphan archive commit."
        }

        $treeOutput = Invoke-GitChecked -Arguments @("ls-tree", "-r", "--name-only", $commit) -Capture
        $actual = @($treeOutput -split "`n" | Where-Object { -not [string]::IsNullOrWhiteSpace($_) } | Sort-Object)
        $difference = @(Compare-Object -ReferenceObject $expected -DifferenceObject $actual)
        if ($difference.Count -ne 0) {
            throw "The orphan commit tree differs from the verified archive file set."
        }
        foreach ($relative in $actual) {
            if (-not $relative.StartsWith("archive/", [StringComparison]::Ordinal)) {
                throw "The orphan commit contains a path outside archive/."
            }
        }
        return $commit
    }
    finally {
        $env:GIT_INDEX_FILE = $oldIndex
        foreach ($candidate in @($indexPath + ".lock", $indexPath)) {
            if (Test-Path -LiteralPath $candidate -PathType Leaf) {
                [IO.File]::Delete($candidate)
            }
        }
        if (Test-Path -LiteralPath $tempDirectory -PathType Container) {
            [IO.Directory]::Delete($tempDirectory, $false)
        }
    }
}

function Publish-VerifiedArchiveCommit {
    param([Parameter(Mandatory = $true)][string]$Commit)
    $remoteRef = "refs/heads/$ArchiveBranch"
    $remoteLine = Invoke-GitChecked -Arguments @("ls-remote", "--heads", $ArchiveRemote, $remoteRef) -Capture
    $expectedRemote = ""
    if (-not [string]::IsNullOrWhiteSpace($remoteLine)) {
        $expectedRemote = ($remoteLine -split '\s+')[0]
        if ($expectedRemote -notmatch '^[0-9a-f]{40,64}$') {
            throw "Remote archive branch returned an invalid object id."
        }
    }
    $lease = "--force-with-lease=${remoteRef}:$expectedRemote"
    $refspec = "${Commit}:$remoteRef"
    Write-Host "Publishing verified orphan snapshot to $ArchiveRemote/$ArchiveBranch with an exact lease."
    Invoke-GitChecked -Arguments @("push", $lease, $ArchiveRemote, $refspec)
}

Resolve-RepositoryContext
Write-Host "Repository: $script:RepoRoot"
Write-Host "Source branch: $RequiredSourceBranch"
Write-Host "Archive target: $ArchiveRemote/$ArchiveBranch"

$willRefresh = $Refresh -or $Publish
if (-not $willRefresh) {
    Write-Host "DRY RUN: no archive files, Git objects, refs, commits, or remotes will be changed."
    $existing = Read-ArchiveManifest
    $null = Assert-ArchiveManifestScope -Manifest $existing -AllowResponses:$IncludeResponses
    Invoke-ArchiveVerification
    Write-Host "Dry-run complete. Use -Refresh for a local snapshot or -Publish for the verified data-archive update."
    exit 0
}

$lockPath = Join-Path $script:ArchiveRoot ".refresh.lock"
$lockStream = $null
# Ownership prevents a failed CreateNew call from deleting another refresh process's lock.
$lockOwned = $false
try {
    if (-not (Test-Path -LiteralPath $script:ArchiveRoot -PathType Container)) {
        $null = New-Item -ItemType Directory -Path $script:ArchiveRoot
    }
    $lockStream = [IO.File]::Open($lockPath, [IO.FileMode]::CreateNew, [IO.FileAccess]::Write, [IO.FileShare]::None)
    $lockOwned = $true
    $pidBytes = [Text.Encoding]::UTF8.GetBytes(([string]$PID + "`n"))
    $lockStream.Write($pidBytes, 0, $pidBytes.Length)
    $lockStream.Flush()

    $manifest = Invoke-ArchiveRefresh
    Write-Host "Local durable archive refreshed and verified."
    if ($Publish) {
        # Verification and manifest allowlist checks above are required to complete before
        # an isolated orphan commit can be created or the network-writing push can run.
        $commit = New-VerifiedArchiveCommit -Manifest $manifest
        Publish-VerifiedArchiveCommit -Commit $commit
        Write-Host "Published $ArchiveRemote/$ArchiveBranch at $commit."
    }
    else {
        Write-Host "No commit or push requested; local refresh only."
    }
}
finally {
    if ($null -ne $lockStream) {
        $lockStream.Dispose()
    }
    if ($lockOwned -and (Test-Path -LiteralPath $lockPath -PathType Leaf)) {
        [IO.File]::Delete($lockPath)
    }
}
