"""Trainer agent - run the Unsloth + LoRA fine-tune.

MVP: a stub that records the intended training config and marks itself
completed without actually training. Full implementation lazy-imports
unsloth and runs SFTTrainer.
"""

from __future__ import annotations

from duecare.core.enums import AgentRole, TaskStatus
from duecare.core.schemas import AgentContext, AgentOutput, ToolSpec
from duecare.agents import agent_registry
from duecare.agents.base import fresh_agent_output, noop_model


class TrainerAgent:
    id = "trainer"
    role = AgentRole.TRAINER
    version = "0.1.0"
    model = noop_model()
    tools: list[ToolSpec] = []
    inputs: set[str] = {"train_jsonl", "val_jsonl"}
    outputs: set[str] = {"lora_adapters", "merged_fp16"}
    cost_budget_usd = 50.0

    def __init__(
        self,
        base_model: str = "unsloth/gemma-4-e4b-bnb-4bit",
        lora_r: int = 16,
        lora_alpha: int = 32,
        num_train_epochs: int = 2,
    ) -> None:
        self.base_model = base_model
        self.lora_r = lora_r
        self.lora_alpha = lora_alpha
        self.num_train_epochs = num_train_epochs

    def execute(self, ctx: AgentContext) -> AgentOutput:
        out = fresh_agent_output(self.id, self.role)
        try:
            train = ctx.lookup("train_jsonl") or []
            val = ctx.lookup("val_jsonl") or []

            # MVP: record the config, don't actually train
            training_config = {
                "base_model": self.base_model,
                "lora_r": self.lora_r,
                "lora_alpha": self.lora_alpha,
                "num_train_epochs": self.num_train_epochs,
                "n_train": len(train),
                "n_val": len(val),
                "mode": "stub",  # flip to "unsloth" when dep is available
            }
            ctx.record("training_config", training_config)

            out.status = TaskStatus.SKIPPED
            out.decision = (
                f"STUB: would train {self.base_model} on {len(train)} samples "
                f"(LoRA r={self.lora_r}, epochs={self.num_train_epochs}). "
                f"Install duecare-llm-models[unsloth] and remove stub guard to run."
            )
            out.metrics = {
                "n_train_samples": float(len(train)),
                "lora_r": float(self.lora_r),
                "num_epochs": float(self.num_train_epochs),
            }
        except Exception as e:
            out.status = TaskStatus.FAILED
            out.decision = f"failed: {e}"
            out.error = str(e)
        return out

    def explain(self) -> str:
        return "Fine-tune the base model with Unsloth + LoRA (stub until unsloth installed)."


agent_registry.add("trainer", TrainerAgent())
