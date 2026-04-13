"""CurriculumDesigner agent - identify failure clusters for the next iteration."""

from __future__ import annotations

from duecare.core.enums import AgentRole, TaskStatus
from duecare.core.schemas import AgentContext, AgentOutput, ToolSpec
from duecare.agents import agent_registry
from duecare.agents.base import fresh_agent_output, noop_model


class CurriculumDesignerAgent:
    id = "curriculum_designer"
    role = AgentRole.CURRICULUM_DESIGNER
    version = "0.1.0"
    model = noop_model()
    tools: list[ToolSpec] = []
    inputs: set[str] = {"evaluation_results"}
    outputs: set[str] = {"next_curriculum"}
    cost_budget_usd = 1.0

    def execute(self, ctx: AgentContext) -> AgentOutput:
        out = fresh_agent_output(self.id, self.role)
        try:
            eval_results = ctx.lookup("evaluation_results") or {}

            # Find tasks with mean_score or grade_exact_match below 0.7
            weak_areas: list[dict] = []
            for task_id, info in eval_results.items():
                metrics = info.get("metrics", {}) if isinstance(info, dict) else {}
                for metric_name in ("mean_score", "grade_exact_match", "citation_rate"):
                    value = metrics.get(metric_name)
                    if value is not None and value < 0.70:
                        weak_areas.append({
                            "task_id": task_id,
                            "metric": metric_name,
                            "value": value,
                            "target": 0.70,
                        })

            curriculum = {
                "focus_tasks": list({w["task_id"] for w in weak_areas}),
                "weak_areas": weak_areas,
                "recommended_num_probes": min(1000, 200 + 100 * len(weak_areas)),
            }
            ctx.record("next_curriculum", curriculum)

            out.status = TaskStatus.COMPLETED
            out.decision = (
                f"Identified {len(weak_areas)} weak areas across "
                f"{len(curriculum['focus_tasks'])} tasks"
            )
            out.metrics = {"n_weak_areas": float(len(weak_areas))}
        except Exception as e:
            out.status = TaskStatus.FAILED
            out.decision = f"failed: {e}"
            out.error = str(e)
        return out

    def explain(self) -> str:
        return "Identify failure clusters and plan the next training curriculum."


agent_registry.add("curriculum_designer", CurriculumDesignerAgent())
