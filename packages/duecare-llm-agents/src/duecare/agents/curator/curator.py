"""Curator agent - dedupe, stratify, split.

Takes whatever is on ctx as clean_probes and produces train/val/test
splits using SimHash dedup + stratified sampling.
"""

from __future__ import annotations

import random

from duecare.core.enums import AgentRole, TaskStatus
from duecare.core.provenance import simhash
from duecare.core.schemas import AgentContext, AgentOutput, ToolSpec
from duecare.agents import agent_registry
from duecare.agents.base import fresh_agent_output, noop_model


class CuratorAgent:
    id = "curator"
    role = AgentRole.CURATOR
    version = "0.1.0"
    model = noop_model()
    tools: list[ToolSpec] = []
    inputs: set[str] = {"clean_probes"}
    outputs: set[str] = {"train_jsonl", "val_jsonl", "test_jsonl", "split_stats"}
    cost_budget_usd = 0.0

    def __init__(self, split_ratios: tuple[float, float, float] = (0.8, 0.1, 0.1), seed: int = 3407) -> None:
        self.split_ratios = split_ratios
        self.seed = seed

    def execute(self, ctx: AgentContext) -> AgentOutput:
        out = fresh_agent_output(self.id, self.role)
        try:
            probes = ctx.lookup("clean_probes", [])
            if not probes:
                # Fall back to the domain pack's seed prompts
                from duecare.domains import load_domain_pack
                pack = load_domain_pack(ctx.domain_id)
                probes = list(pack.seed_prompts())

            # SimHash dedupe with Hamming-distance threshold
            seen_hashes: list[int] = []
            deduped: list[dict] = []
            for p in probes:
                h = simhash(p.get("text", ""))
                near_dup = any(bin(h ^ prev).count("1") < 4 for prev in seen_hashes)
                if not near_dup:
                    seen_hashes.append(h)
                    deduped.append(p)

            # Stratified shuffle + split by category
            by_category: dict[str, list[dict]] = {}
            for p in deduped:
                by_category.setdefault(p.get("category", "unknown"), []).append(p)

            rng = random.Random(self.seed)
            train: list[dict] = []
            val: list[dict] = []
            test: list[dict] = []
            for cat, items in by_category.items():
                rng.shuffle(items)
                n = len(items)
                n_train = int(n * self.split_ratios[0])
                n_val = int(n * self.split_ratios[1])
                train.extend(items[:n_train])
                val.extend(items[n_train : n_train + n_val])
                test.extend(items[n_train + n_val :])

            stats = {
                "n_input": float(len(probes)),
                "n_deduped": float(len(deduped)),
                "n_train": float(len(train)),
                "n_val": float(len(val)),
                "n_test": float(len(test)),
                "n_categories": float(len(by_category)),
            }

            ctx.record("train_jsonl", train)
            ctx.record("val_jsonl", val)
            ctx.record("test_jsonl", test)
            ctx.record("split_stats", stats)

            out.status = TaskStatus.COMPLETED
            out.decision = (
                f"Split {len(probes)} probes into "
                f"{len(train)} train / {len(val)} val / {len(test)} test "
                f"({len(deduped)} unique after dedupe, {len(by_category)} categories)"
            )
            out.metrics = stats
            out.context_updates = {"split_stats": stats}
        except Exception as e:
            out.status = TaskStatus.FAILED
            out.decision = f"failed: {e}"
            out.error = str(e)
        return out

    def explain(self) -> str:
        return "Dedupe with SimHash and stratify-split into train/val/test."


agent_registry.add("curator", CuratorAgent())
