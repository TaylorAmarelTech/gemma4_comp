from __future__ import annotations

import importlib.util
import sys
from pathlib import Path

import pytest

_ROOT = Path(__file__).resolve().parents[1]
SCRIPT = _ROOT / "scripts" / "build_gemma4_adapter_kaggle_collection.py"
SPEC = importlib.util.spec_from_file_location("build_gemma4_adapter_kaggle_collection", SCRIPT)
assert SPEC and SPEC.loader
MODULE = importlib.util.module_from_spec(SPEC)
sys.modules["build_gemma4_adapter_kaggle_collection"] = MODULE
SPEC.loader.exec_module(MODULE)


def test_resolve_run_directories_splits_existing_and_missing(tmp_path: Path) -> None:
    existing = tmp_path / "gemma4_e2b_grounded_adapter_v3"
    existing.mkdir()
    missing = tmp_path / "gemma4_e2b_regime_rank4_sft_v1"
    resolved, skipped = MODULE.resolve_run_directories([existing, missing])
    assert resolved == [existing.resolve()]
    assert skipped == ["gemma4_e2b_regime_rank4_sft_v1"]


def test_build_collection_fails_clearly_below_two_resolved_runs(tmp_path: Path) -> None:
    only_run = tmp_path / "run-a"
    only_run.mkdir()
    missing = tmp_path / "run-b-missing"
    output = tmp_path / "collection"
    with pytest.raises(MODULE.PackageError) as excinfo:
        MODULE.build_collection(
            [only_run, missing],
            output,
            force=False,
        )
    message = str(excinfo.value)
    assert "at least two completed runs" in message
    assert "run-b-missing" in message
    assert not output.exists()


def test_default_run_list_skips_future_regime_runs_without_error() -> None:
    resolved, skipped = MODULE.resolve_run_directories(MODULE.DEFAULT_RUNS)
    # The two completed adapter runs must resolve wherever the local evidence
    # exists; future regime runs may be absent and must only be skipped.
    assert all(name.startswith("gemma4_e2b_") for name in skipped)
    assert len(resolved) + len(skipped) == len(MODULE.DEFAULT_RUNS)
