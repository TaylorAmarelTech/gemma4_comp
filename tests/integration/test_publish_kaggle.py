"""Integration tests for scripts/publish_kaggle.py.

These tests prove the orchestrator's logic works without needing real
Kaggle credentials by exercising --dry-run mode and by isolating the
auth-check path.

The publishable surface is the active root Kaggle kernels (01, 02, A-00)
plus the optional benchmark kernels (03, 04) -- the same set
``discover_kernel_notebooks(..., include_optional=True)`` returns and that
``publish_kaggle.push_notebooks`` iterates. The legacy ``kaggle/kernels/*``
mirror is no longer the publish target.
"""

from __future__ import annotations

import json
import subprocess
import sys
from pathlib import Path

import pytest

REPO_ROOT = Path(__file__).resolve().parents[2]
SCRIPT = REPO_ROOT / "scripts" / "publish_kaggle.py"
KAGGLE_ROOT = REPO_ROOT / "kaggle"

SCRIPTS_DIR = REPO_ROOT / "scripts"
if str(SCRIPTS_DIR) not in sys.path:
    sys.path.insert(0, str(SCRIPTS_DIR))

import publish_kaggle as publisher  # noqa: E402
from kaggle_notebook_utils import discover_kernel_notebooks  # noqa: E402


def _published_notebooks():
    """The kernels publish_kaggle actually pushes: active + optional root."""
    return discover_kernel_notebooks(KAGGLE_ROOT, include_optional=True)


def _tracked_kernel_count() -> int:
    return len(_published_notebooks())


def _run(
    *args: str, env_overrides: dict[str, str] | None = None
) -> subprocess.CompletedProcess[str]:
    import os

    env = os.environ.copy()
    if env_overrides:
        env.update(env_overrides)
    return subprocess.run(
        [sys.executable, str(SCRIPT), *args],
        capture_output=True,
        text=True,
        check=False,
        env=env,
        cwd=str(REPO_ROOT),
    )


class TestCLI:
    def test_help(self):
        result = _run("--help")
        assert result.returncode == 0
        for cmd in (
            "auth-check",
            "push-notebooks",
            "status-notebooks",
            "publish-dataset",
            "publish-training-dataset",
            "publish-model",
            "publish-all",
        ):
            assert cmd in result.stdout

    def test_missing_subcommand_errors(self):
        result = _run()
        # argparse exits non-zero when required subcommand is missing
        assert result.returncode != 0


class TestDryRun:
    def test_push_notebooks_dry_run(self):
        result = _run("--dry-run", "push-notebooks")
        # Succeeds even without credentials because every run is a no-op print.
        assert result.returncode == 0, result.stderr
        tracked = _tracked_kernel_count()
        assert f"# push-notebooks ({tracked} kernels)" in result.stdout
        assert result.stdout.count("kernels push") == tracked
        for entry in _published_notebooks():
            assert entry.dir_name in result.stdout, (
                f"missing kernel {entry.dir_name} in dry-run output"
            )

    def test_empty_eval_dataset_dry_run_is_blocked(self):
        result = _run("--dry-run", "publish-dataset", "--operation", "create")
        assert result.returncode == 2
        assert "shared-datasets" in result.stderr
        assert "zero payload files" in result.stderr

    def test_metadata_only_model_dry_run_is_blocked(self):
        result = _run("--dry-run", "publish-model")
        assert result.returncode == 2
        assert "model-instance-metadata.json is required" in result.stderr

    def test_publish_all_is_disabled_even_in_dry_run(self):
        result = _run("--dry-run", "publish-all")
        assert result.returncode == 2
        assert "disabled: broad publication" in result.stderr

    def test_push_notebooks_dry_run_limit_and_ids(self):
        # 01 and A-00 both match; sorted by dir name 01 comes first, so
        # --limit 1 keeps only the exploration workbench.
        result = _run("--dry-run", "push-notebooks", "--ids", "01", "A-00", "--limit", "1")
        assert result.returncode == 0, result.stderr
        assert "# push-notebooks (1 kernels)" in result.stdout
        assert "01-duecare-exploration-workbench" in result.stdout
        assert "A-00-omni-experiment-workbench" not in result.stdout

    def test_a00_only_push_remains_available(self):
        result = _run("--dry-run", "push-notebooks", "--ids", "A-00")
        assert result.returncode == 0, result.stderr
        assert "# push-notebooks (1 kernels)" in result.stdout
        assert "A-00-omni-experiment-workbench" in result.stdout
        assert "01-duecare-exploration-workbench" not in result.stdout

    def test_status_notebooks_without_creds_fails_fast(self, tmp_path: Path):
        result = _run(
            "status-notebooks",
            "--limit",
            "1",
            env_overrides={
                "HOME": str(tmp_path),
                "USERPROFILE": str(tmp_path),
                "KAGGLE_API_TOKEN": "",
                "KAGGLE_USERNAME": "",
                "KAGGLE_KEY": "",
            },
        )
        assert result.returncode == 2
        combined = result.stdout + result.stderr
        assert "# auth-check" in result.stdout
        assert "No credentials found" in combined
        assert "You must authenticate before you can call the Kaggle API." not in combined


class TestValidation:
    def test_every_kernel_metadata_is_valid_json(self):
        """Each published kernel (active + optional root) has a complete,
        parseable kernel-metadata.json whose code_file sibling exists. The
        active kernels install DueCare from GitHub source, so they declare no
        wheels dataset or competition source; the contract here is the
        Kaggle-required metadata shape plus public visibility + keywords."""
        entries = _published_notebooks()
        assert entries, "no publishable kernels discovered"
        for entry in entries:
            meta = entry.dir_path / "kernel-metadata.json"
            assert meta.exists(), f"{entry.dir_path}: missing kernel-metadata.json"
            data = json.loads(meta.read_text(encoding="utf-8"))
            for field in ("id", "title", "code_file", "kernel_type", "language"):
                assert field in data, f"{meta}: missing field {field}"
            nb = entry.dir_path / data["code_file"]
            assert nb.exists(), f"{meta}: code_file {nb} does not exist"
            assert data.get("is_private") is False, f"{meta}: is_private should be false"
            assert data.get("keywords"), f"{meta}: keywords missing"

    def test_dataset_metadata_is_valid(self):
        meta = REPO_ROOT / "kaggle" / "shared-datasets" / "eval-results" / "dataset-metadata.json"
        assert meta.exists()
        data = json.loads(meta.read_text())
        for field in ("id", "title", "licenses"):
            assert field in data

    def test_model_metadata_is_valid(self):
        meta = REPO_ROOT / "kaggle" / "models" / "duecare_safety_harness" / "model-metadata.json"
        assert meta.exists()
        data = json.loads(meta.read_text())
        for field in ("ownerSlug", "title", "slug", "description"):
            assert field in data

    def test_dataset_validator_rejects_metadata_only_directory(self, tmp_path: Path):
        (tmp_path / "dataset-metadata.json").write_text(
            json.dumps(
                {
                    "id": "owner/release",
                    "title": "Verified release",
                    "licenses": [{"name": "CC-BY-SA-4.0"}],
                }
            ),
            encoding="utf-8",
        )
        with pytest.raises(ValueError, match="zero payload files"):
            publisher._validate_dataset_payload(tmp_path)

        (tmp_path / "PLACEHOLDER.txt").write_text("replace me", encoding="utf-8")
        with pytest.raises(ValueError, match="placeholder name"):
            publisher._validate_dataset_payload(tmp_path)

    def test_model_validator_requires_completion_and_real_weights(self, tmp_path: Path):
        (tmp_path / "model-metadata.json").write_text(
            json.dumps(
                {
                    "ownerSlug": "owner",
                    "title": "DueCare adapter",
                    "slug": "duecare-adapter",
                    "description": "Completed DueCare adapter",
                }
            ),
            encoding="utf-8",
        )
        with pytest.raises(ValueError, match=r"model-instance-metadata\.json is required"):
            publisher._validate_model_payload(tmp_path)

        (tmp_path / "model-instance-metadata.json").write_text(
            json.dumps(
                {
                    "owner_slug": "owner",
                    "model_slug": "duecare-adapter",
                    "instance_slug": "transformers",
                    "framework": "transformers",
                }
            ),
            encoding="utf-8",
        )
        (tmp_path / "training_completion_manifest.json").write_text(
            json.dumps(
                {
                    "schema_version": "1.0",
                    "handoff_kind": "duecare.training.completion.v1",
                    "base_model": "google/gemma-4-e4b-it",
                    "base_model_revision": "a" * 40,
                    "completed_at": "2026-07-14T00:00:00+00:00",
                    "executed_stages": ["sft", "dpo"],
                }
            ),
            encoding="utf-8",
        )
        weights = tmp_path / "adapter_model.safetensors"
        weights.write_bytes(b"not weights")
        with pytest.raises(ValueError, match="too small to be credible"):
            publisher._validate_model_payload(tmp_path)
        weights.write_bytes(b"x" * 2048)
        report = publisher._validate_model_payload(tmp_path)
        assert report["weight_files"] == [weights]


class TestTrainingDatasetPublication:
    def _stub_verified_release(self, monkeypatch: pytest.MonkeyPatch, tmp_path: Path) -> None:
        monkeypatch.setattr(
            publisher,
            "verify_release_dir",
            lambda path: {"ok": True, "release_id": "release-fixture"},
        )
        monkeypatch.setattr(
            publisher,
            "_validate_dataset_payload",
            lambda path: {"metadata": {}, "payload_files": [path / "sft_train.jsonl"]},
        )

    @pytest.mark.parametrize("public", [False, True])
    def test_verified_create_defaults_private_and_public_is_explicit(
        self,
        monkeypatch: pytest.MonkeyPatch,
        tmp_path: Path,
        public: bool,
    ):
        self._stub_verified_release(monkeypatch, tmp_path)
        seen: list[list[str]] = []

        def fake_run(cmd, *, dry_run, cwd=None):
            seen.append(cmd)
            return publisher.RunResult(cmd=cmd, returncode=0, stdout="", stderr="")

        monkeypatch.setattr(publisher, "run", fake_run)
        rc = publisher.publish_training_dataset(
            release_dir=tmp_path,
            dry_run=True,
            operation="create",
            public=public,
        )
        assert rc == 0
        assert len(seen) == 1
        assert ("--public" in seen[0]) is public
        assert seen[0][-1] == ("--public" if public else str(tmp_path))

    def test_version_note_is_passed_exactly_once(
        self,
        monkeypatch: pytest.MonkeyPatch,
        tmp_path: Path,
    ):
        self._stub_verified_release(monkeypatch, tmp_path)
        seen: list[list[str]] = []

        def fake_run(cmd, *, dry_run, cwd=None):
            seen.append(cmd)
            return publisher.RunResult(cmd=cmd, returncode=0, stdout="", stderr="")

        monkeypatch.setattr(publisher, "run", fake_run)
        note = "release 2026-07-14; scope=partial; sha=abc123"
        rc = publisher.publish_training_dataset(
            release_dir=tmp_path,
            dry_run=True,
            operation="version",
            version_note=note,
        )
        assert rc == 0
        assert seen[0].count(note) == 1
        assert seen[0][seen[0].index("-m") + 1] == note

    def test_unverified_or_placeholder_release_is_blocked_before_command(
        self,
        monkeypatch: pytest.MonkeyPatch,
        tmp_path: Path,
    ):
        called = False

        def fake_run(cmd, *, dry_run, cwd=None):
            nonlocal called
            called = True
            return publisher.RunResult(cmd=cmd, returncode=0, stdout="", stderr="")

        monkeypatch.setattr(publisher, "run", fake_run)
        rc = publisher.publish_training_dataset(
            release_dir=tmp_path,
            dry_run=True,
            operation="create",
        )
        assert rc == 2
        assert called is False

    def test_public_flag_is_rejected_for_existing_dataset_version(
        self,
        monkeypatch: pytest.MonkeyPatch,
        tmp_path: Path,
    ):
        self._stub_verified_release(monkeypatch, tmp_path)
        rc = publisher.publish_training_dataset(
            release_dir=tmp_path,
            dry_run=True,
            operation="version",
            version_note="exact note",
            public=True,
        )
        assert rc == 2
