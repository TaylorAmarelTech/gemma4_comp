"""Behavioral tests for training package: dataset builder + trainer + plan."""
from __future__ import annotations

import json
import tempfile
from pathlib import Path

import pytest


def test_training_plan_round_trip() -> None:
    from duecare.training import TrainingPlan
    plan = TrainingPlan(
        training_run_id="run_42",
        base_model="google/gemma-4-e4b-it",
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
