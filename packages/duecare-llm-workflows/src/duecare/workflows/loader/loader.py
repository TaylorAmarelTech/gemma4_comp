"""Load workflow YAML into Pydantic models."""

from __future__ import annotations

from pathlib import Path
from typing import Any

import yaml
from pydantic import BaseModel, Field


class AgentStep(BaseModel):
    id: str
    needs: list[str] = Field(default_factory=list)
    config: dict[str, Any] = Field(default_factory=dict)


class WorkflowBudget(BaseModel):
    max_cost_usd: float = 100.0
    max_wall_clock_hours: float = 12.0
    max_gpu_hours: float = 8.0


class RetryPolicy(BaseModel):
    max_attempts: int = 3
    backoff: str = "exponential"


class FailurePolicy(BaseModel):
    on_validator_harm_flag: str = "abort"
    on_budget_exceeded: str = "snapshot_and_stop"
    on_agent_error: str = "retry_then_skip"


class CoordinatorConfig(BaseModel):
    retry_policy: RetryPolicy = Field(default_factory=RetryPolicy)
    failure_policy: FailurePolicy = Field(default_factory=FailurePolicy)


class Workflow(BaseModel):
    id: str
    description: str = ""
    inputs: dict[str, Any] = Field(default_factory=dict)
    budget: WorkflowBudget = Field(default_factory=WorkflowBudget)
    agents: list[AgentStep] = Field(default_factory=list)
    coordinator: CoordinatorConfig = Field(default_factory=CoordinatorConfig)


def load_workflow(path: Path | str) -> Workflow:
    """Parse a workflow YAML file into a Workflow model."""
    raw = yaml.safe_load(Path(path).read_text(encoding="utf-8"))
    return Workflow(**raw)
