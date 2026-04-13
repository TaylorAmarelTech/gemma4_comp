"""Training dataset + run record schemas.

See docs/architecture.md sections 3 and 11.
"""

from __future__ import annotations

from datetime import datetime

from pydantic import BaseModel, Field


class DatasetSplit(BaseModel):
    """Describes a concrete train/val/test split produced by the prepare step."""

    version: str
    created_at: datetime
    train_path: str
    val_path: str
    test_path: str
    n_train: int
    n_val: int
    n_test: int
    stratified_by: list[str]
    held_out_by: str
    seed: int
    category_distribution: dict[str, int] = Field(default_factory=dict)
    grade_distribution: dict[str, int] = Field(default_factory=dict)
    corridor_distribution: dict[str, int] = Field(default_factory=dict)


class TrainRecord(BaseModel):
    """One fine-tuning run. Persisted to runs/ table for audit + reproducibility."""

    run_id: str
    git_sha: str
    config_hash: str
    dataset_version: str
    base_model: str
    started_at: datetime
    ended_at: datetime | None = None
    status: str  # "running" | "completed" | "failed"
    final_metrics: dict = Field(default_factory=dict)
    artifact_paths: dict[str, str] = Field(default_factory=dict)
