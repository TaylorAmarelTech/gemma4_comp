"""Duecare training: synthetic labels + active learning + Unsloth handoff."""
from __future__ import annotations

from duecare.training.labels import (
    SyntheticLabelGenerator,
    LabeledExample,
    LABEL_STRATEGIES,
)
from duecare.training.review import ReviewQueue, ReviewItem
from duecare.training.dataset import UnslothDatasetBuilder
from duecare.training.trainer import UnslothTrainer, TrainingPlan
from duecare.training.runs import TrainingRunsTable

__all__ = [
    "SyntheticLabelGenerator", "LabeledExample", "LABEL_STRATEGIES",
    "ReviewQueue", "ReviewItem",
    "UnslothDatasetBuilder",
    "UnslothTrainer", "TrainingPlan",
    "TrainingRunsTable",
]
