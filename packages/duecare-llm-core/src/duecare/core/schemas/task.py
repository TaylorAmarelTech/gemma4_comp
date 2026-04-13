"""TaskConfig + TaskResult + ItemResult schemas."""

from __future__ import annotations

from datetime import datetime
from pathlib import Path
from typing import Any

from pydantic import BaseModel, Field

from duecare.core.enums import Grade, TaskStatus
from .provenance import Provenance


class TaskConfig(BaseModel):
    """Configuration passed to Task.run()."""

    sample_size: int | None = None   # None = use the entire test split
    seed: int = 3407
    max_tokens: int = 1024
    temperature: float = 0.0
    system_prompt: str | None = None
    extra: dict[str, Any] = Field(default_factory=dict)


class ItemResult(BaseModel):
    """One row of a TaskResult: a single test item's outcome."""

    item_id: str
    input: dict = Field(default_factory=dict)
    model_output: str = ""
    expected: dict = Field(default_factory=dict)
    scores: dict[str, float] = Field(default_factory=dict)
    grade: Grade | None = None
    errors: list[str] = Field(default_factory=list)
    latency_ms: int = 0


class TaskResult(BaseModel):
    """Aggregate result from Task.run()."""

    task_id: str
    model_id: str
    domain_id: str
    status: TaskStatus
    started_at: datetime
    ended_at: datetime | None = None
    metrics: dict[str, float] = Field(default_factory=dict)
    per_item: list[ItemResult] = Field(default_factory=list)
    artifacts: dict[str, Path] = Field(default_factory=dict)
    error: str | None = None
    provenance: Provenance

    def summary(self) -> str:
        """One-line human-readable summary."""
        metric_str = ", ".join(f"{k}={v:.3f}" for k, v in self.metrics.items())
        return f"{self.task_id} [{self.status.value}] {metric_str}"
