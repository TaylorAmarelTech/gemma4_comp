"""Behavioral tests for training package: dataset builder + trainer + plan."""
from __future__ import annotations

import json
from pathlib import Path

import pytest


def test_training_plan_round_trip() -> None:
    from duecare.training import TrainingPlan
    plan = TrainingPlan(
        training_run_id="run_42",
        base_model="google/gemma-4-E4B-it",
        dataset_train_path="/tmp/train.jsonl",
        dataset_val_path="/tmp/val.jsonl",
        dataset_test_path="/tmp/test.jsonl",
        output_lora_path="/tmp/lora",
        config={"lora_r": 16, "epochs": 2},
        notes="smoke",
    )
    parsed = json.loads(plan.to_json())
    assert parsed["training_run_id"] == "run_42"
    assert parsed["base_model"].startswith("google/gemma-4")
    assert parsed["config"]["lora_r"] == 16
    assert parsed["notes"] == "smoke"


def test_training_plan_defaults() -> None:
    from duecare.training import TrainingPlan
    plan = TrainingPlan(
        training_run_id="x",
        base_model="m",
        dataset_train_path="t",
        dataset_val_path="v",
        dataset_test_path="te",
        output_lora_path="o",
    )
    parsed = json.loads(plan.to_json())
    # config + notes default to empty
    assert parsed["config"] == {}
    assert parsed["notes"] == ""


def test_label_strategies_non_empty() -> None:
    try:
        from duecare.training import LABEL_STRATEGIES
    except ImportError as e:
        pytest.skip(f"training imports unavailable: {e}")
    assert len(LABEL_STRATEGIES) >= 1


class _PlanStore:
    def __init__(self) -> None:
        self.row: dict = {}

    def execute(self, *_args, **_kwargs):
        return None

    def _upsert(self, _table: str, _key: str, row: dict) -> None:
        self.row = row


def _dataset_manifest(path: Path) -> Path:
    path.write_text(
        json.dumps(
            {
                "train_path": "train.jsonl",
                "val_path": "val.jsonl",
                "test_path": "test.jsonl",
                "n_total": 12,
                "n_train": 8,
                "n_val": 2,
                "n_test": 2,
            }
        ),
        encoding="utf-8",
    )
    return path


def test_trainer_default_is_canonical_and_dry_run_is_plan_only(tmp_path: Path) -> None:
    from duecare.training import UnslothTrainer

    store = _PlanStore()
    plan = UnslothTrainer(store).kickoff(
        manifest_path=str(_dataset_manifest(tmp_path / "manifest.json")),
        dry_run=True,
    )

    assert plan.base_model == "google/gemma-4-E4B-it"
    assert store.row["status"] == "dry_run"


def test_trainer_for_real_request_fails_closed_with_active_handoff(tmp_path: Path) -> None:
    from duecare.training import UnslothTrainer

    store = _PlanStore()
    with pytest.raises(
        NotImplementedError,
        match=r"scripts/training_engine\.py --with-gpu",
    ):
        UnslothTrainer(store).kickoff(
            manifest_path=str(_dataset_manifest(tmp_path / "manifest.json")),
            dry_run=False,
        )

    assert store.row["status"] == "handoff_required"
