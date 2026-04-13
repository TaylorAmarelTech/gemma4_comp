"""Exporter agent - convert, quantize, publish."""

from __future__ import annotations

from duecare.core.enums import AgentRole, TaskStatus
from duecare.core.schemas import AgentContext, AgentOutput, ToolSpec
from duecare.agents import agent_registry
from duecare.agents.base import fresh_agent_output, noop_model


class ExporterAgent:
    id = "exporter"
    role = AgentRole.EXPORTER
    version = "0.1.0"
    model = noop_model()
    tools: list[ToolSpec] = []
    inputs: set[str] = {"merged_fp16", "no_harm_certificate"}
    outputs: set[str] = {"gguf_paths", "hf_hub_url"}
    cost_budget_usd = 0.0

    def execute(self, ctx: AgentContext) -> AgentOutput:
        out = fresh_agent_output(self.id, self.role)
        try:
            certificate = ctx.lookup("no_harm_certificate") or {}
            if not certificate.get("passed", True):
                out.status = TaskStatus.SKIPPED
                out.decision = "Skipped export: no-harm certificate did not pass"
                return out

            # MVP: record intended export targets
            out.status = TaskStatus.SKIPPED
            out.decision = (
                "STUB: would convert fp16 -> GGUF q4_k_m/q5_k_m/q8_0 and "
                "upload to HF Hub + Kaggle Models. "
                "Implement in duecare-llm-publishing."
            )
            out.metrics = {}
        except Exception as e:
            out.status = TaskStatus.FAILED
            out.decision = f"failed: {e}"
            out.error = str(e)
        return out

    def explain(self) -> str:
        return "Convert to GGUF/LiteRT and publish to HF Hub + Kaggle Models."


agent_registry.add("exporter", ExporterAgent())
