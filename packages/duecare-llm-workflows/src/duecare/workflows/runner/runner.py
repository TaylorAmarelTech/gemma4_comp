"""Walk a workflow DAG and invoke each agent via an AgentSupervisor."""

from __future__ import annotations

from datetime import datetime
from pathlib import Path
from time import perf_counter

from duecare.core.contracts import Model
from duecare.core.enums import TaskStatus
from duecare.core.provenance import generate_run_id, get_git_sha, hash_config
from duecare.core.schemas import AgentContext, WorkflowRun
from duecare.observability.logging import get_logger

from ..dag import topological_sort
from ..loader import Workflow, load_workflow

log = get_logger("duecare.workflows.runner")


class WorkflowRunner:
    """Walks a Workflow DAG and invokes each agent in topological order.

    Uses an AgentSupervisor to enforce retries, budget caps, and abort-
    on-harm policies. Returns a WorkflowRun record with the final
    status and metrics.
    """

    def __init__(self, workflow: Workflow) -> None:
        self.workflow = workflow

    @classmethod
    def from_yaml(cls, path: Path | str) -> "WorkflowRunner":
        return cls(load_workflow(path))

    def run(
        self,
        target_model_id: str,
        domain_id: str,
        target_model_instance: Model | None = None,
    ) -> WorkflowRun:
        from duecare.agents import agent_registry, AgentSupervisor
        from duecare.agents.base import SupervisorPolicy

        started_timer = perf_counter()
        run_id = generate_run_id(self.workflow.id)
        config_hash = hash_config(self.workflow.model_dump())

        ctx = AgentContext(
            run_id=run_id,
            git_sha=get_git_sha(),
            workflow_id=self.workflow.id,
            target_model_id=target_model_id,
            domain_id=domain_id,
            started_at=datetime.now(),
        )
        if target_model_instance is not None:
            ctx.record("target_model_instance", target_model_instance)

        # Topological sort
        dag = [(step.id, step.needs) for step in self.workflow.agents]
        try:
            order = topological_sort(dag)
        except ValueError as e:
            return WorkflowRun(
                run_id=run_id,
                workflow_id=self.workflow.id,
                git_sha=ctx.git_sha,
                config_hash=config_hash,
                target_model_id=target_model_id,
                domain_id=domain_id,
                started_at=ctx.started_at,
                ended_at=datetime.now(),
                status=TaskStatus.FAILED,
                error=f"DAG error: {e}",
            )

        # Execute via supervisor
        policy = SupervisorPolicy(
            max_retries=self.workflow.coordinator.retry_policy.max_attempts - 1,
            hard_budget_usd=self.workflow.budget.max_cost_usd,
        )
        supervisor = AgentSupervisor(policy)

        result_status = TaskStatus.RUNNING
        error: str | None = None
        agent_outputs = []
        skipped_agents: list[str] = []

        for agent_id in order:
            if not agent_registry.has(agent_id):
                log.error("workflow.unknown_agent agent=%s", agent_id)
                error = f"Unknown agent in workflow DAG: {agent_id}"
                result_status = TaskStatus.FAILED
                break
            agent = agent_registry.get(agent_id)
            try:
                out = supervisor.run(agent, ctx)
                agent_outputs.append(out)
                if out.status == TaskStatus.FAILED:
                    error = out.error
                    if self.workflow.coordinator.failure_policy.on_agent_error == "retry_then_skip":
                        log.warning("workflow.agent_failed agent=%s; continuing", agent_id)
                        continue
                    result_status = TaskStatus.FAILED
                    break
                if out.status == TaskStatus.SKIPPED:
                    skipped_agents.append(agent_id)
            except Exception as e:
                log.error("workflow.fatal agent=%s error=%s", agent_id, e)
                error = str(e)
                result_status = TaskStatus.FAILED
                break

        if result_status == TaskStatus.RUNNING:
            if skipped_agents:
                result_status = TaskStatus.SKIPPED
                error = error or f"Skipped required agents: {', '.join(skipped_agents)}"
            else:
                result_status = TaskStatus.COMPLETED

        ended_at = datetime.now()

        return WorkflowRun(
            run_id=run_id,
            workflow_id=self.workflow.id,
            git_sha=ctx.git_sha,
            config_hash=config_hash,
            target_model_id=target_model_id,
            domain_id=domain_id,
            started_at=ctx.started_at,
            ended_at=ended_at,
            status=result_status,
            agent_outputs=agent_outputs,
            final_metrics=ctx.metrics,
            final_artifacts={k: v for k, v in ctx.artifacts.items()},
            total_cost_usd=supervisor.total_cost_usd,
            total_duration_s=perf_counter() - started_timer,
            error=error,
        )
