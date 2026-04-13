"""WorkflowRun schema - the authoritative record of a single workflow execution."""

from __future__ import annotations

from datetime import datetime
from pathlib import Path

from pydantic import BaseModel, Field

from duecare.core.enums import TaskStatus
from .agent import AgentOutput


class WorkflowRun(BaseModel):
    """One end-to-end workflow execution. Persisted per run."""

    run_id: str
    workflow_id: str
    git_sha: str
    config_hash: str
    target_model_id: str
    domain_id: str
    started_at: datetime
    ended_at: datetime | None = None
    status: TaskStatus = TaskStatus.PENDING
    agent_outputs: list[AgentOutput] = Field(default_factory=list)
    final_metrics: dict[str, float] = Field(default_factory=dict)
    final_artifacts: dict[str, Path] = Field(default_factory=dict)
    total_cost_usd: float = 0.0
    total_duration_s: float = 0.0
    error: str | None = None

    def summary(self) -> str:
        """One-line human-readable summary."""
        return (
            f"run={self.run_id} workflow={self.workflow_id} "
            f"model={self.target_model_id} domain={self.domain_id} "
            f"status={self.status.value} "
            f"cost=${self.total_cost_usd:.2f} duration={self.total_duration_s:.1f}s"
        )
