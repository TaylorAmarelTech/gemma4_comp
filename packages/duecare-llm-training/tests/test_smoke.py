"""Smoke tests for duecare-llm-training."""
from __future__ import annotations

import pytest


def test_training_imports() -> None:
    try:
        from duecare.training import (
            SyntheticLabelGenerator, LabeledExample, LABEL_STRATEGIES,
            ReviewQueue, ReviewItem,
            UnslothDatasetBuilder,
            UnslothTrainer, TrainingPlan,
            TrainingRunsTable,
        )
    except ImportError as e:
        pytest.skip(f"training depends on packages not installed: {e}")
    assert SyntheticLabelGenerator is not None
    assert UnslothDatasetBuilder is not None
    assert UnslothTrainer is not None
    assert isinstance(LABEL_STRATEGIES, (list, tuple, dict, set))


def test_training_plan_to_json() -> None:
    try:
        from duecare.training import TrainingPlan
    except ImportError as e:
        pytest.skip(f"training depends on packages not installed: {e}")
    plan = TrainingPlan(
        training_run_id="train_test_000",
        base_model="google/gemma-4-e4b-it",
        dataset_train_path="/tmp/train.jsonl",
        dataset_val_path="/tmp/val.jsonl",
        dataset_test_path="/tmp/test.jsonl",
        output_lora_path="/tmp/lora",
    )
    import json
    parsed = json.loads(plan.to_json())
    assert parsed["training_run_id"] == "train_test_000"
    assert parsed["base_model"].startswith("google/gemma-4")
