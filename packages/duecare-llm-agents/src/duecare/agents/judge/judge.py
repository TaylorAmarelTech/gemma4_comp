"""Judge agent - scores model outputs by running the capability tests.

The Judge delegates to the task_registry: it runs whichever capability
tests are listed in its config against the target model + domain pack.
Real glue code.
"""

from __future__ import annotations

from datetime import datetime

from duecare.core.enums import AgentRole, TaskStatus
from duecare.core.schemas import AgentContext, AgentOutput, TaskConfig, ToolSpec
from duecare.agents import agent_registry
from duecare.agents.base import fresh_agent_output, noop_model


class JudgeAgent:
    id = "judge"
    role = AgentRole.JUDGE
    version = "0.1.0"
    model = noop_model()
    tools: list[ToolSpec] = []
    inputs: set[str] = set()
    outputs: set[str] = {"evaluation_results", "per_category_breakdown"}
    cost_budget_usd = 10.0

    # Which tasks to run by default. Supervisor can override via ctx.
    default_task_ids = ("guardrails",)

    def __init__(self, model=None, task_ids: tuple[str, ...] | None = None) -> None:
        if model is not None:
            self.model = model
        self.task_ids = task_ids or self.default_task_ids

    def execute(self, ctx: AgentContext) -> AgentOutput:
        out = fresh_agent_output(self.id, self.role)
        try:
            from duecare.domains import load_domain_pack
            from duecare.tasks import task_registry

            # The Judge needs a real model to test. If ctx has a
            # target_model_id but no model instance, it's the caller's
            # responsibility to construct one. In minimum-viable mode we
            # try to get one from a context-attached resolver.
            target_model = ctx.lookup("target_model_instance")
            if target_model is None:
                out.status = TaskStatus.SKIPPED
                out.decision = "No target model instance on ctx; Judge skipped"
                return out

            pack = load_domain_pack(ctx.domain_id)
            config = TaskConfig(sample_size=ctx.lookup("sample_size", 3))

            all_metrics: dict[str, float] = {}
            results_by_task: dict[str, dict] = {}

            for task_id in self.task_ids:
                if not task_registry.has(task_id):
                    continue
                task = task_registry.get(task_id)
                result = task.run(target_model, pack, config)
                results_by_task[task_id] = {
                    "status": result.status.value,
                    "metrics": result.metrics,
                    "n_items": len(result.per_item),
                }
                for k, v in result.metrics.items():
                    all_metrics[f"{task_id}.{k}"] = v

            ctx.record("evaluation_results", results_by_task)
            out.status = TaskStatus.COMPLETED
            out.decision = f"Ran {len(results_by_task)} tasks on {target_model.id}"
            out.metrics = all_metrics
            out.context_updates = {"evaluation_results": results_by_task}
        except Exception as e:
            out.status = TaskStatus.FAILED
            out.decision = f"failed: {e}"
            out.error = str(e)
        return out

    def explain(self) -> str:
        return "Score model outputs against the domain rubric via the task registry."


agent_registry.add("judge", JudgeAgent())
