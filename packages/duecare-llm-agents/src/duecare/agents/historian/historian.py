"""Historian agent - write the run report.

Reads ctx.outputs_by_agent, ctx.metrics, and ctx.decisions, and emits a
markdown report to ctx.artifacts['run_report']. Pure Python - no LLM
calls in the minimum-viable implementation.
"""

from __future__ import annotations

from datetime import datetime
from pathlib import Path

from duecare.core.enums import AgentRole, TaskStatus
from duecare.core.schemas import AgentContext, AgentOutput, ToolSpec
from duecare.agents import agent_registry
from duecare.agents.base import fresh_agent_output, noop_model


class HistorianAgent:
    id = "historian"
    role = AgentRole.HISTORIAN
    version = "0.1.0"
    model = noop_model()
    tools: list[ToolSpec] = []
    inputs: set[str] = {"*"}
    outputs: set[str] = {"run_report_md"}
    cost_budget_usd = 0.0

    def __init__(self, output_dir: Path | None = None) -> None:
        self.output_dir = output_dir or Path("reports")

    def execute(self, ctx: AgentContext) -> AgentOutput:
        out = fresh_agent_output(self.id, self.role)
        try:
            self.output_dir.mkdir(parents=True, exist_ok=True)
            report_path = self.output_dir / f"{ctx.run_id}.md"
            report_path.write_text(self._render(ctx), encoding="utf-8")

            out.artifacts_written = {"run_report": report_path}
            out.status = TaskStatus.COMPLETED
            out.decision = f"Wrote run report to {report_path}"
            out.context_updates = {"run_report_path": str(report_path)}
        except Exception as e:
            out.status = TaskStatus.FAILED
            out.decision = f"failed: {e}"
            out.error = str(e)
        return out

    def _render(self, ctx: AgentContext) -> str:
        lines: list[str] = []
        lines.append(f"# Duecare Run Report - {ctx.run_id}")
        lines.append("")
        lines.append(f"- **workflow**: `{ctx.workflow_id}`")
        lines.append(f"- **target_model**: `{ctx.target_model_id}`")
        lines.append(f"- **domain**: `{ctx.domain_id}`")
        lines.append(f"- **git_sha**: `{ctx.git_sha}`")
        lines.append(f"- **started_at**: {ctx.started_at.isoformat(timespec='seconds')}")
        lines.append(f"- **budget_used_usd**: ${ctx.budget_used_usd:.4f}")
        lines.append("")
        lines.append("## Decisions")
        lines.append("")
        if ctx.decisions:
            for decision in ctx.decisions:
                lines.append(f"- {decision}")
        else:
            lines.append("- (none recorded)")
        lines.append("")
        lines.append("## Metrics")
        lines.append("")
        if ctx.metrics:
            for k, v in sorted(ctx.metrics.items()):
                lines.append(f"- `{k}` = {v}")
        else:
            lines.append("- (none recorded)")
        lines.append("")
        lines.append("## Per-agent outputs")
        lines.append("")
        for role, output in sorted(ctx.outputs_by_agent.items()):
            lines.append(f"### {role}")
            if isinstance(output, dict):
                for k, v in output.items():
                    lines.append(f"- `{k}`: `{v}`")
            else:
                lines.append(f"- `{output}`")
            lines.append("")
        return "\n".join(lines)

    def explain(self) -> str:
        return "Write the run report from the shared blackboard."


agent_registry.add("historian", HistorianAgent())
