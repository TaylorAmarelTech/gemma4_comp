"""Static and dry-run checks for scripts/refresh_durable_archive.ps1.

The publication path is deliberately not exercised: tests prove its scope and ordering from
the script, while the behavioral test runs only the default read-only mode in a disposable repo.
"""
from __future__ import annotations

import hashlib
import json
import shutil
import subprocess
import sys
from pathlib import Path

import pytest


ROOT = Path(__file__).resolve().parents[1]
SCRIPT = ROOT / "scripts" / "refresh_durable_archive.ps1"


def _source() -> str:
    return SCRIPT.read_text(encoding="utf-8")


def _powershell() -> str | None:
    for name in ("pwsh", "pwsh.exe", "powershell", "powershell.exe"):
        found = shutil.which(name)
        if found:
            return found
    return None


def test_default_is_dry_run_and_publication_requires_explicit_switch():
    text = _source()
    assert "[switch]$Refresh" in text
    assert "[switch]$Publish" in text
    assert "$willRefresh = $Refresh -or $Publish" in text
    assert "if (-not $willRefresh)" in text
    assert "DRY RUN: no archive files, Git objects, refs, commits, or remotes will be changed." in text
    assert "if ($Publish)" in text


def test_archive_source_scope_has_allowlist_and_denies_sensitive_paths():
    text = _source()
    assert '"reports/benchmark/full_promptset.json"' in text
    assert '"reports/rich_lift/results.jsonl"' in text
    assert '"reports/rich_lift/panel_perdim.coverage.json"' in text
    assert '"reports/rich_lift/panel_perdim.jsonl.components.sqlite3"' in text
    assert "^reports/rich_lift/panel" in text
    assert "^reports/multi_judge/" in text
    assert "^reports/training/" in text
    for denied_marker in (
        "credentials?",
        "secrets?",
        "tokens?",
        "logs?",
        "raw[_-]?cases?",
        "pii",
        "adapters?",
        "weights?",
        "safetensors",
    ):
        assert denied_marker in text
    assert "durable_archive.py's JSON content-safety gate" in text


def test_publish_is_isolated_to_data_archive_with_exact_force_with_lease():
    text = _source()
    assert '$RequiredSourceBranch = "master"' in text
    assert '$ArchiveBranch = "data-archive"' in text
    assert '$ArchiveRemote = "origin"' in text
    assert '$ExpectedRepositorySlug = "TaylorAmarelTech/gemma4_comp"' in text
    assert "$env:GIT_INDEX_FILE = $indexPath" in text
    assert '@("read-tree", "--empty")' in text
    assert '@("commit-tree", $tree' in text
    assert '@("ls-tree", "-r", "--name-only", $commit)' in text
    assert '"--force-with-lease=${remoteRef}:$expectedRemote"' in text
    assert '@("push", $lease, $ArchiveRemote, $refspec)' in text
    assert "git checkout" not in text.lower()
    assert "git reset" not in text.lower()
    assert "--force " not in text
    assert "$lockOwned = $false" in text
    assert "$lockOwned = $true" in text
    assert "if ($lockOwned -and" in text


def test_archive_readme_documents_guarded_refresh_and_isolated_publish():
    readme = (ROOT / "archive" / "README.md").read_text(encoding="utf-8")
    assert "pwsh scripts/refresh_durable_archive.ps1` is a read-only" in readme
    assert "pwsh scripts/refresh_durable_archive.ps1 -Refresh" in readme
    assert "pwsh scripts/refresh_durable_archive.ps1 -Publish" in readme
    assert "isolated orphan" in readme
    assert "origin/data-archive" in readme
    assert "exact `--force-with-lease`" in readme
    assert "normal Git index" in readme


def test_refresh_and_verification_precede_commit_and_push_calls():
    text = _source()
    execution = text[text.index("$manifest = Invoke-ArchiveRefresh") :]
    refresh_at = execution.index("$manifest = Invoke-ArchiveRefresh")
    commit_at = execution.index("$commit = New-VerifiedArchiveCommit")
    push_at = execution.index("Publish-VerifiedArchiveCommit -Commit $commit")
    assert refresh_at < commit_at < push_at
    refresh_function = text[text.index("function Invoke-ArchiveRefresh") : text.index("function Get-ExpectedArchiveTreePaths")]
    assert "Invoke-ArchiveVerification" in refresh_function
    assert "Assert-ArchiveManifestScope" in refresh_function


@pytest.mark.skipif(_powershell() is None, reason="PowerShell is not installed")
def test_default_mode_is_read_only_in_disposable_repository(tmp_path):
    scripts = tmp_path / "scripts"
    archive = tmp_path / "archive"
    scripts.mkdir()
    archive.mkdir()
    manifest = archive / "manifest.json"
    manifest.write_text(
        json.dumps(
            {
                "generated": "2026-07-14T00:00:00Z",
                "chunk_bytes": 1024,
                "n_files": 0,
                "total_source_bytes": 0,
                "total_compressed_bytes": 0,
                "files": [],
            },
            indent=2,
            sort_keys=True,
        )
        + "\n",
        encoding="utf-8",
    )
    (archive / "README.md").write_text("# disposable archive\n", encoding="utf-8")
    (scripts / "durable_archive.py").write_text(
        """from __future__ import annotations
import sys
if sys.argv[1:] == ['--verify']:
    print('verify: 0/0 files reassemble to their recorded sha256')
    raise SystemExit(0)
raise SystemExit('test stub only permits --verify')
""",
        encoding="utf-8",
    )

    subprocess.run(["git", "init", "-q", str(tmp_path)], check=True)
    subprocess.run(
        ["git", "-C", str(tmp_path), "symbolic-ref", "HEAD", "refs/heads/master"],
        check=True,
    )
    subprocess.run(
        [
            "git",
            "-C",
            str(tmp_path),
            "remote",
            "add",
            "origin",
            "https://github.com/TaylorAmarelTech/gemma4_comp.git",
        ],
        check=True,
    )
    before_manifest = hashlib.sha256(manifest.read_bytes()).hexdigest()
    before_status = subprocess.run(
        ["git", "-C", str(tmp_path), "status", "--porcelain"],
        check=True,
        capture_output=True,
        text=True,
    ).stdout

    completed = subprocess.run(
        [
            _powershell(),
            "-NoProfile",
            "-NonInteractive",
            "-ExecutionPolicy",
            "Bypass",
            "-File",
            str(SCRIPT),
            "-RepositoryRoot",
            str(tmp_path),
            "-PythonExecutable",
            sys.executable,
        ],
        capture_output=True,
        text=True,
        timeout=30,
    )

    assert completed.returncode == 0, completed.stdout + completed.stderr
    assert "DRY RUN" in completed.stdout
    assert "verify: 0/0" in completed.stdout
    assert hashlib.sha256(manifest.read_bytes()).hexdigest() == before_manifest
    assert not (archive / ".refresh.lock").exists()
    after_status = subprocess.run(
        ["git", "-C", str(tmp_path), "status", "--porcelain"],
        check=True,
        capture_output=True,
        text=True,
    ).stdout
    assert after_status == before_status
