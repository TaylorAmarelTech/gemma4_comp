"""Agent protocol. An autonomous actor in the Duecare swarm."""

from __future__ import annotations

from typing import Protocol, runtime_checkable

from duecare.core.enums import AgentRole
from duecare.core.schemas import AgentContext, AgentOutput, ToolSpec

from .model import Model


@runtime_checkable
class Agent(Protocol):
    """An autonomous actor in the Duecare swarm.

    Agents compose Tasks and Tools into workflows. They call models
    internally via a Model adapter. They make decisions (what to do
    next, what to skip, what to abort), while Tasks only compute.

    Every agent has:
      - a role (from AgentRole)
      - a model it uses for its own LLM calls
      - a set of tools it can call
      - declared inputs + outputs (context keys it reads/writes)
    """

    id: str
    role: AgentRole
    version: str
    model: Model | None          # some agents (Adversary, Curator) are pure
    tools: list[ToolSpec]
    inputs: set[str]
    outputs: set[str]
    cost_budget_usd: float

    def execute(self, ctx: AgentContext) -> AgentOutput: ...
    def explain(self) -> str: ...
