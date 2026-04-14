"""Trainer agent - run the Unsloth + LoRA fine-tune.

Lazy-imports `unsloth` and `trl`. When the extras are installed and
`dry_run=False`, runs `SFTTrainer` for a real LoRA fine-tune. When the
extras are missing OR `dry_run=True`, records the training config and
marks SKIPPED (with a clear "install extras" pointer) — this keeps the
full workflow runnable in CI and on machines without a GPU, while the
same code path does real training on Kaggle GPU.
"""

from __future__ import annotations

from pathlib import Path

from duecare.core.enums import AgentRole, TaskStatus
from duecare.core.schemas import AgentContext, AgentOutput, ToolSpec
from duecare.agents import agent_registry
from duecare.agents.base import fresh_agent_output, noop_model


class TrainerAgent:
    id = "trainer"
    role = AgentRole.TRAINER
    version = "0.2.0"
    model = noop_model()
    tools: list[ToolSpec] = []
    inputs: set[str] = {"train_jsonl", "val_jsonl"}
    outputs: set[str] = {"lora_adapters", "merged_fp16"}
    cost_budget_usd = 50.0

    def __init__(
        self,
        base_model: str = "unsloth/gemma-4-E4B-it-bnb-4bit",
        lora_r: int = 16,
        lora_alpha: int = 32,
        num_train_epochs: int = 2,
        max_seq_length: int = 2048,
        output_dir: str = "./duecare-lora-output",
        dry_run: bool = False,
    ) -> None:
        self.base_model = base_model
        self.lora_r = lora_r
        self.lora_alpha = lora_alpha
        self.num_train_epochs = num_train_epochs
        self.max_seq_length = max_seq_length
        self.output_dir = output_dir
        self.dry_run = dry_run

    def _try_real_training(
        self, train: list, val: list
    ) -> tuple[bool, dict, str | None]:
        """Attempt a real Unsloth + LoRA fine-tune.

        Returns (ran, metrics, error). If unsloth or trl are missing,
        returns (False, {}, install-instructions) without raising so the
        caller can mark SKIPPED cleanly.
        """
        try:
            from datasets import Dataset  # type: ignore
            import torch  # noqa: F401
            from trl import SFTTrainer  # type: ignore
            from transformers import TrainingArguments  # type: ignore
            from unsloth import FastLanguageModel  # type: ignore
        except ImportError:
            return (
                False,
                {},
                "duecare-llm-models[unsloth] is required for real training. "
                "Install with: pip install 'duecare-llm-models[unsloth]'",
            )

        model, tokenizer = FastLanguageModel.from_pretrained(
            model_name=self.base_model,
            max_seq_length=self.max_seq_length,
            dtype=None,  # auto (T4-safe)
            load_in_4bit=True,
        )
        model = FastLanguageModel.get_peft_model(
            model,
            r=self.lora_r,
            lora_alpha=self.lora_alpha,
            lora_dropout=0.05,
            target_modules=[
                "q_proj", "k_proj", "v_proj", "o_proj",
                "gate_proj", "up_proj", "down_proj",
            ],
            bias="none",
            use_gradient_checkpointing="unsloth",
        )

        train_ds = Dataset.from_list(train)
        val_ds = Dataset.from_list(val) if val else None

        args = TrainingArguments(
            output_dir=self.output_dir,
            num_train_epochs=self.num_train_epochs,
            per_device_train_batch_size=4,
            gradient_accumulation_steps=4,
            learning_rate=2e-4,
            warmup_ratio=0.03,
            lr_scheduler_type="cosine",
            fp16=True,  # T4 safety
            logging_steps=5,
            save_strategy="epoch",
            eval_strategy="epoch" if val_ds else "no",
            optim="adamw_8bit",
            report_to="none",
            seed=42,
        )

        trainer = SFTTrainer(
            model=model,
            tokenizer=tokenizer,
            train_dataset=train_ds,
            eval_dataset=val_ds,
            args=args,
            dataset_text_field="text",
            max_seq_length=self.max_seq_length,
            packing=False,
        )

        result = trainer.train()
        trainer.save_model(self.output_dir)

        return (
            True,
            {
                "training_loss": float(result.training_loss),
                "global_step": float(result.global_step),
                "lora_adapter_path": self.output_dir,
            },
            None,
        )

    def execute(self, ctx: AgentContext) -> AgentOutput:
        out = fresh_agent_output(self.id, self.role)
        try:
            train = ctx.lookup("train_jsonl") or []
            val = ctx.lookup("val_jsonl") or []

            training_config = {
                "base_model": self.base_model,
                "lora_r": self.lora_r,
                "lora_alpha": self.lora_alpha,
                "num_train_epochs": self.num_train_epochs,
                "n_train": len(train),
                "n_val": len(val),
                "output_dir": self.output_dir,
                "dry_run": self.dry_run,
            }
            ctx.record("training_config", training_config)

            if self.dry_run:
                out.status = TaskStatus.SKIPPED
                out.decision = (
                    f"DRY RUN: would train {self.base_model} on {len(train)} "
                    f"samples (LoRA r={self.lora_r}, epochs={self.num_train_epochs})."
                )
                out.metrics = {
                    "n_train_samples": float(len(train)),
                    "lora_r": float(self.lora_r),
                    "num_epochs": float(self.num_train_epochs),
                    "mode": 0.0,  # 0 = dry-run
                }
                return out

            ran, metrics, install_hint = self._try_real_training(train, val)
            if ran:
                out.status = TaskStatus.COMPLETED
                out.decision = (
                    f"Trained {self.base_model} on {len(train)} samples. "
                    f"Adapter saved to {self.output_dir}."
                )
                out.metrics = {
                    "n_train_samples": float(len(train)),
                    "lora_r": float(self.lora_r),
                    "num_epochs": float(self.num_train_epochs),
                    "mode": 1.0,  # 1 = real training
                    **metrics,
                }
                ctx.record("lora_adapters", self.output_dir)
            else:
                out.status = TaskStatus.SKIPPED
                out.decision = install_hint or "Training dependencies not available."
                out.metrics = {
                    "n_train_samples": float(len(train)),
                    "mode": -1.0,  # -1 = skipped due to missing deps
                }
        except Exception as e:
            out.status = TaskStatus.FAILED
            out.decision = f"failed: {e}"
            out.error = str(e)
        return out

    def explain(self) -> str:
        return (
            "Unsloth + LoRA fine-tune on DueCare graded training data. "
            "Runs for real when duecare-llm-models[unsloth] is installed; "
            "otherwise records config and skips cleanly."
        )


agent_registry.add("trainer", TrainerAgent())
