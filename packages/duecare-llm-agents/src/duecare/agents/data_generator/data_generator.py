"""DataGenerator agent - synthesize probes.

Minimum viable implementation: copies the domain pack's seed prompts as
the "synthetic" output. A full implementation would call a teacher model
(Claude Haiku / Gemini Flash) to generate N variations per prompt.
"""

from __future__ import annotations

from duecare.core.enums import AgentRole, TaskStatus
from duecare.core.schemas import AgentContext, AgentOutput, ToolSpec
from duecare.agents import agent_registry
from duecare.agents.base import fresh_agent_output, noop_model


class DataGeneratorAgent:
    id = "data_generator"
    role = AgentRole.DATA_GENERATOR
    version = "0.1.0"
    model = noop_model()
    tools: list[ToolSpec] = []
    inputs: set[str] = {"domain_readiness_score"}
    outputs: set[str] = {"synthetic_probes", "graded_examples"}
    cost_budget_usd = 20.0

    def __init__(self, model=None, num_probes: int = 50) -> None:
        if model is not None:
            self.model = model
        self.num_probes = num_probes

    def execute(self, ctx: AgentContext) -> AgentOutput:
        out = fresh_agent_output(self.id, self.role)
        try:
            from duecare.domains import load_domain_pack
            pack = load_domain_pack(ctx.domain_id)

            # MVP: reuse the seed prompts as synthetic probes
            probes = list(pack.seed_prompts())[: self.num_probes]

            ctx.record("synthetic_probes", probes)

            out.status = TaskStatus.COMPLETED
            out.decision = f"Generated {len(probes)} probes (MVP: using seed prompts)"
            out.metrics = {"n_probes": float(len(probes))}
            out.context_updates = {"n_synthetic_probes": len(probes)}
        except Exception as e:
            out.status = TaskStatus.FAILED
            out.decision = f"failed: {e}"
            out.error = str(e)
        return out

    def explain(self) -> str:
        return "Generate synthetic probes and graded response examples (MVP: seed passthrough)."


agent_registry.add("data_generator", DataGeneratorAgent())
