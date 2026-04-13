"""Coordinator agent - rule-based DAG walker.

MVP: topological sort + sequential execution. Full implementation uses
Gemma 4 E4B with native function calling to schedule the swarm.
"""

from __future__ import annotations

from datetime import datetime

from duecare.core.enums import AgentRole, TaskStatus
from duecare.core.schemas import AgentContext, AgentOutput, ToolSpec, WorkflowRun
from duecare.agents import agent_registry
from duecare.agents.base import AgentSupervisor, fresh_agent_output, noop_model


class CoordinatorAgent:
    id = "coordinator"
    role = AgentRole.COORDINATOR
    version = "0.1.0"
    model = noop_model()
    tools: list[ToolSpec] = []
    inputs: set[str] = set()
    outputs: set[str] = {"workflow_run"}
    cost_budget_usd = 1.0

    def __init__(self, workflow_id: str = "adhoc", supervisor: AgentSupervisor | None = None) -> None:
        self.workflow_id = workflow_id
        self.supervisor = supervisor or AgentSupervisor()

    def execute(self, ctx: AgentContext) -> AgentOutput:
        out = fresh_agent_output(self.id, self.role)
        try:
            # Execute agents in a predefined order for the rapid_probe workflow
            # In the real workflows package, the DAG is read from YAML
            pipeline = ["scout", "historian"]
            executed: list[str] = []
            for agent_id in pipeline:
                if not agent_registry.has(agent_id):
                    continue
                agent = agent_registry.get(agent_id)
                self.supervisor.run(agent, ctx)
                executed.append(agent_id)

            out.status = TaskStatus.COMPLETED
            out.decision = f"Ran {len(executed)} agents: {', '.join(executed)}"
            out.metrics = self.supervisor.summary()
        except Exception as e:
            out.status = TaskStatus.FAILED
            out.decision = f"failed: {e}"
            out.error = str(e)
        return out

    def run_workflow(self, ctx: AgentContext) -> WorkflowRun:
        output = self.execute(ctx)
        return WorkflowRun(
            run_id=ctx.run_id,
            workflow_id=self.workflow_id,
            git_sha=ctx.git_sha,
            config_hash="",
            target_model_id=ctx.target_model_id,
            domain_id=ctx.domain_id,
            started_at=ctx.started_at,
            ended_at=datetime.now(),
            status=output.status,
            final_metrics=output.metrics,
            total_cost_usd=self.supervisor.total_cost_usd,
        )

    def explain(self) -> str:
        return "Orchestrate the Duecare swarm via rule-based DAG walking."


agent_registry.add("coordinator", CoordinatorAgent())
