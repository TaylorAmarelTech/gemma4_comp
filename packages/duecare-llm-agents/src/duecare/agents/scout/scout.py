"""Scout agent - profile the domain pack.

Reads a domain pack and computes a readiness score based on taxonomy
coverage, evidence count, and seed prompt count. Runs fast and cheap
(no LLM calls in this minimum-viable implementation).
"""

from __future__ import annotations

from duecare.core.enums import AgentRole, TaskStatus
from duecare.core.schemas import AgentContext, AgentOutput, ToolSpec
from duecare.agents import agent_registry
from duecare.agents.base import fresh_agent_output, noop_model


class ScoutAgent:
    id = "scout"
    role = AgentRole.SCOUT
    version = "0.1.0"
    model = noop_model()
    tools: list[ToolSpec] = []
    inputs: set[str] = set()
    outputs: set[str] = {"domain_readiness_score", "domain_stats"}
    cost_budget_usd = 0.0

    def execute(self, ctx: AgentContext) -> AgentOutput:
        out = fresh_agent_output(self.id, self.role)
        try:
            from duecare.domains import load_domain_pack
            pack = load_domain_pack(ctx.domain_id)

            taxonomy = pack.taxonomy()
            n_categories = len(taxonomy.get("categories", []))
            n_indicators = len(taxonomy.get("indicators", []))
            n_seed_prompts = sum(1 for _ in pack.seed_prompts())
            n_evidence = sum(1 for _ in pack.evidence())

            # Readiness: weighted score 0..1
            signals = {
                "has_taxonomy": 1.0 if n_categories >= 3 else 0.0,
                "has_indicators": 1.0 if n_indicators >= 3 else 0.0,
                "has_seed_prompts": 1.0 if n_seed_prompts >= 3 else 0.0,
                "has_evidence": 1.0 if n_evidence >= 3 else 0.0,
            }
            readiness = sum(signals.values()) / len(signals)

            stats = {
                "n_categories": n_categories,
                "n_indicators": n_indicators,
                "n_seed_prompts": n_seed_prompts,
                "n_evidence": n_evidence,
            }

            ctx.record("domain_stats", stats)
            ctx.record("domain_readiness_score", readiness)

            out.status = TaskStatus.COMPLETED
            out.decision = (
                f"Domain {pack.id!r} ready (score={readiness:.2f}): "
                f"{n_seed_prompts} prompts, {n_evidence} evidence, "
                f"{n_categories} categories"
            )
            out.metrics = {"readiness_score": readiness, **{k: float(v) for k, v in stats.items()}}
            out.context_updates = {"domain_stats": stats, "domain_readiness_score": readiness}
        except Exception as e:
            out.status = TaskStatus.FAILED
            out.decision = f"failed: {e}"
            out.error = str(e)
        return out

    def explain(self) -> str:
        return "Profile the domain pack and score its completeness."


agent_registry.add("scout", ScoutAgent())
