"""Regression coverage for the legacy-training cleanup."""

from __future__ import annotations

import importlib.util
import random
import sys
from pathlib import Path
from types import SimpleNamespace

import pytest
import yaml

ROOT = Path(__file__).resolve().parents[1]


def _load(name: str, path: Path):
    spec = importlib.util.spec_from_file_location(name, path)
    assert spec is not None and spec.loader is not None
    module = importlib.util.module_from_spec(spec)
    sys.modules[name] = module
    spec.loader.exec_module(module)
    return module


prepare = _load("prepare_training_data_cleanup_test", ROOT / "scripts" / "prepare_training_data.py")
legacy = _load("finetune_unsloth_cleanup_test", ROOT / "scripts" / "finetune_unsloth.py")


def _prompt_ids(rows: list[SimpleNamespace]) -> set[str]:
    return {row.prompt_id for row in rows}


def test_prepare_training_data_splits_complete_prompt_groups() -> None:
    examples = [
        SimpleNamespace(prompt_id=f"P{prompt_index}", grade=grade)
        for prompt_index in range(10)
        for grade in ("best", "good")
    ]
    random.seed(17)
    train, val, test = prepare.split_data(examples)

    train_ids, val_ids, test_ids = map(_prompt_ids, (train, val, test))
    assert train_ids.isdisjoint(val_ids)
    assert train_ids.isdisjoint(test_ids)
    assert val_ids.isdisjoint(test_ids)
    assert len(train) == 16
    assert len(val) == 2
    assert len(test) == 2
    assert prepare.split_prompt_summary(train, val, test) == {
        "strategy": "prompt_id_grouped",
        "prompt_counts": {"train": 8, "val": 1, "test": 1},
        "prompt_overlap_counts": {"train_val": 0, "train_test": 0, "val_test": 0},
        "clean": True,
    }


@pytest.mark.parametrize(
    ("train_ratio", "val_ratio"),
    [(-0.1, 0.1), (1.1, 0.0), (0.8, -0.1), (0.8, 0.3)],
)
def test_prepare_training_data_rejects_invalid_split_ratios(
    train_ratio: float,
    val_ratio: float,
) -> None:
    with pytest.raises(ValueError):
        prepare.split_data([], train_ratio=train_ratio, val_ratio=val_ratio)


def test_legacy_unsloth_entrypoint_fails_closed(capsys: pytest.CaptureFixture[str]) -> None:
    assert legacy.main([]) == 2
    output = capsys.readouterr().out
    assert "disabled" in output
    assert "scripts/training_engine.py --with-gpu" in output
    assert "kaggle/A-00-omni-experiment-workbench" in output


def test_active_model_configs_use_canonical_gemma_refs() -> None:
    registry_path = ROOT / "configs" / "duecare" / "models.yaml"
    registry = yaml.safe_load(registry_path.read_text(encoding="utf-8"))
    refs = {row["id"]: row["model_id"] for row in registry["models"]}
    assert refs["gemma_4_e2b_stock"] == "google/gemma-4-E2B-it"
    assert refs["gemma_4_e4b_stock"] == "google/gemma-4-E4B-it"

    exploration_path = ROOT / "configs" / "phases" / "exploration.yaml"
    exploration = yaml.safe_load(exploration_path.read_text(encoding="utf-8"))
    phase_refs = {row["id"]: row["model_id"] for row in exploration["models"]}
    assert phase_refs["gemma_4_e4b"] == "google/gemma-4-E4B-it"


def test_active_kaggle_kernels_use_canonical_default_ref() -> None:
    kernel_01_path = ROOT / "kaggle" / "01-duecare-exploration-workbench" / "kernel.py"
    kernel_01 = kernel_01_path.read_text(encoding="utf-8")
    kernel_02 = (ROOT / "kaggle" / "02-live-demo" / "kernel.py").read_text(encoding="utf-8")
    assert '"e4b-it":         "google/gemma-4-E4B-it"' in kernel_01
    assert '"e4b-it": "google/gemma-4-E4B-it"' in kernel_02
    assert "google/gemma-4-4b-it" not in kernel_01
    assert "google/gemma-4-4b-it" not in kernel_02


def test_active_training_package_has_no_archived_notebook_handoff() -> None:
    package_root = ROOT / "packages" / "duecare-llm-training"
    text = "\n".join(
        path.read_text(encoding="utf-8")
        for path in package_root.rglob("*")
        if path.is_file() and path.suffix in {".py", ".md"}
    ).lower()
    assert "notebook 530" not in text
    assert "nb 530" not in text
    assert "530_phase3_unsloth_finetune" not in text
