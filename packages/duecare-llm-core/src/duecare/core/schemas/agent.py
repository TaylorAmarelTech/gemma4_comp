"""AgentContext + AgentOutput schemas."""

from __future__ import annotations

from datetime import datetime
from pathlib import Path
from typing import Any

from pydantic import BaseModel, Field

from duecare.core.enums import AgentRole, TaskStatus


class AgentContext(BaseModel):
    """The shared blackboard across a workflow run.

    Agents read + write this by key. The Coordinator is responsible for
    merging agent outputs into the context in the correct order.
    """

    run_id: str
    git_sha: str
    workflow_id: str
    target_model_id: str
    domain_id: str
    started_at: datetime

    # Mutable shared state
    artifacts: dict[str, Path] = Field(default_factory=dict)
    metrics: dict[str, float] = Field(default_factory=dict)
    decisions: list[str] = Field(default_factory=list)
    budget_used_usd: float = 0.0

    # Arbitrary per-agent outputs keyed by agent role
    outputs_by_agent: dict[str, dict] = Field(default_factory=dict)

    def record(self, key: str, value: Any) -> None:
        """Convenience: store a value under `key` in outputs_by_agent."""
        self.outputs_by_agent[key] = value

    def lookup(self, key: str, default: Any = None) -> Any:
        return self.outputs_by_agent.get(key, default)


class AgentOutput(BaseModel):
    """The structured output of an agent's execute() call."""

    agent_id: str
    agent_role: AgentRole
    status: TaskStatus
    decision: str                       # one-line human explanation
    artifacts_written: dict[str, Path] = Field(default_factory=dict)
    context_updates: dict[str, Any] = Field(default_factory=dict)
    metrics: dict[str, float] = Field(default_factory=dict)
    tokens_used: int = 0
    cost_usd: float = 0.0
    duration_ms: int = 0
    error: str | None = None
