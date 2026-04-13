"""Coordinator protocol. The special agent that orchestrates the swarm."""

from __future__ import annotations

from typing import Protocol, runtime_checkable

from duecare.core.schemas import AgentContext, WorkflowRun


@runtime_checkable
class Coordinator(Protocol):
    """The Coordinator is a special agent: it orchestrates the others.

    In a Gemma-native deployment, the Coordinator IS Gemma 4 E4B using
    native function calling to schedule the swarm. In a fallback
    deployment, the Coordinator is a rule-based DAG walker. Both conform
    to this protocol.
    """

    id: str
    version: str
    workflow_id: str

    def run_workflow(self, ctx: AgentContext) -> WorkflowRun: ...
    def explain(self) -> str: ...
